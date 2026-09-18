import json
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dependencies.resources import get_owned_project
from app.models.emissions_grid import EmissionsGrid
from app.models.project import Project
from app.models.site import Site
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsMetric,
    DashboardSite,
    DatasetMetadata,
    ProjectSummary,
    ProjectDashboard,
    SiteAnalyticsDetails,
    SiteTimeseriesResponse,
    TimeseriesPoint,
)
from app.schemas.site import PolygonGeometry


@dataclass(frozen=True)
class SiteAggregate:
    year: int
    value: float
    grid_cells: int


def get_owned_site(db: Session, site_id: int, user: User) -> Site:
    site = db.scalar(
        select(Site)
        .join(Project, Site.project_id == Project.id)
        .where(Site.id == site_id, Project.owner_id == user.id)
    )
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


def _aggregates_for_site(db: Session, site: Site) -> list[SiteAggregate]:
    rows = db.execute(
        select(
            EmissionsGrid.year,
            func.sum(EmissionsGrid.co2_tonnes).label("value"),
            func.count(EmissionsGrid.id).label("grid_cells"),
        )
        .where(func.ST_Intersects(site.geometry, EmissionsGrid.geometry))
        .group_by(EmissionsGrid.year)
        .order_by(EmissionsGrid.year)
    ).all()
    return [
        SiteAggregate(year=row.year, value=float(row.value), grid_cells=row.grid_cells)
        for row in rows
    ]


def _require_aggregate(db: Session, site: Site) -> tuple[list[SiteAggregate], SiteAggregate]:
    aggregates = _aggregates_for_site(db, site)
    if not aggregates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No environmental data intersects this site",
        )
    return aggregates, aggregates[-1]


def _metric(site_id: int, aggregate: SiteAggregate) -> AnalyticsMetric:
    # EDGAR's imported co2_tonnes value is treated as an annual total for its
    # grid cell. We sum intersecting cells and do not area-weight or multiply
    # by cell area because the source table stores cell totals, not densities.
    return AnalyticsMetric(
        site_id=site_id,
        year=aggregate.year,
        value=aggregate.value,
        grid_cells=aggregate.grid_cells,
    )


def get_site_analytics(db: Session, site_id: int, user: User) -> AnalyticsMetric:
    site = get_owned_site(db, site_id, user)
    _, aggregate = _require_aggregate(db, site)
    return _metric(site.id, aggregate)


def get_site_timeseries(db: Session, site_id: int, user: User) -> SiteTimeseriesResponse:
    site = get_owned_site(db, site_id, user)
    aggregates, _ = _require_aggregate(db, site)
    return SiteTimeseriesResponse(
        site_id=site.id,
        data=[
            TimeseriesPoint(
                year=aggregate.year,
                value=aggregate.value,
                grid_cells=aggregate.grid_cells,
            )
            for aggregate in aggregates
        ],
        available_years=[aggregate.year for aggregate in aggregates],
    )


def _site_geometry(db: Session, site_id: int) -> PolygonGeometry:
    geometry_json = db.scalar(
        select(func.ST_AsGeoJSON(Site.geometry)).where(Site.id == site_id)
    )
    if geometry_json is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored site geometry could not be read",
        )
    return PolygonGeometry.model_validate(json.loads(geometry_json))


def get_site_details(db: Session, site_id: int, user: User) -> SiteAnalyticsDetails:
    site = get_owned_site(db, site_id, user)
    aggregates, aggregate = _require_aggregate(db, site)
    project = db.get(Project, site.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Site project could not be read",
        )
    return SiteAnalyticsDetails(
        site_id=site.id,
        site_name=site.name,
        project_id=project.id,
        project_name=project.name,
        geometry=_site_geometry(db, site.id),
        analytics=_metric(site.id, aggregate),
        available_years=[item.year for item in aggregates],
    )


def get_project_dashboard(db: Session, project_id: int, user: User) -> ProjectDashboard:
    project = get_owned_project(db, project_id, user)
    rows = db.execute(
        select(
            Site.id,
            Site.name,
            func.ST_AsGeoJSON(Site.geometry).label("geometry_json"),
            EmissionsGrid.year,
            func.sum(EmissionsGrid.co2_tonnes).label("value"),
            func.count(EmissionsGrid.id).label("grid_cells"),
        )
        .select_from(Site)
        .outerjoin(
            EmissionsGrid,
            func.ST_Intersects(Site.geometry, EmissionsGrid.geometry),
        )
        .where(Site.project_id == project.id)
        .group_by(Site.id, Site.name, Site.geometry, EmissionsGrid.year)
        .order_by(Site.id, EmissionsGrid.year)
    ).all()

    site_rows: dict[int, dict[str, Any]] = {}
    for row in rows:
        site_entry = site_rows.setdefault(
            row.id,
            {
                "id": row.id,
                "name": row.name,
                "geometry": PolygonGeometry.model_validate(json.loads(row.geometry_json)),
                "analytics": None,
            },
        )
        if row.year is not None:
            site_entry["analytics"] = AnalyticsMetric(
                site_id=row.id,
                year=row.year,
                value=float(row.value),
                grid_cells=row.grid_cells,
            )

    return ProjectDashboard(
        project=ProjectSummary(
            id=project.id,
            name=project.name,
            description=project.description,
        ),
        sites=[DashboardSite.model_validate(site) for site in site_rows.values()],
    )


def get_dataset_metadata(db: Session) -> DatasetMetadata:
    years = db.scalars(
        select(EmissionsGrid.year).distinct().order_by(EmissionsGrid.year)
    ).all()
    return DatasetMetadata(
        dataset_name="EDGAR India CO2 grid",
        source="EDGAR preprocessed India grid CSV",
        years=list(years),
        geographic_resolution="0.1 degree by 0.1 degree grid cells",
        description=(
            "Imported EDGAR grid-cell CO2 values stored as PostGIS Polygons. "
            "Available years reflect the rows currently imported into the database."
        ),
    )
