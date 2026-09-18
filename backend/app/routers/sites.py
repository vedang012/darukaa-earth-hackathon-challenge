import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.geometry import polygon_to_postgis
from app.dependencies.auth import get_current_user
from app.dependencies.resources import get_owned_project, get_owned_site
from app.models.project import Project
from app.models.site import Site
from app.models.user import User
from app.schemas.site import SiteCreate, SiteResponse, SiteUpdate


router = APIRouter(prefix="/api/v1/projects/{project_id}/sites", tags=["Sites"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def serialize_site(db: Session, site: Site) -> SiteResponse:
    geometry_json = db.scalar(
        select(func.ST_AsGeoJSON(Site.geometry)).where(Site.id == site.id)
    )
    if geometry_json is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored site geometry could not be read",
        )
    return SiteResponse(
        id=site.id,
        project_id=site.project_id,
        name=site.name,
        description=site.description,
        geometry=json.loads(geometry_json),
        created_at=site.created_at,
        updated_at=site.updated_at,
    )


def set_geometry(site: Site, geometry) -> None:
    try:
        site.geometry = polygon_to_postgis(geometry)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
def create_site(
    project_id: int,
    site_data: SiteCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> SiteResponse:
    project = get_owned_project(db, project_id, current_user)
    site = Site(
        project_id=project.id,
        name=site_data.name,
        description=site_data.description,
    )
    set_geometry(site, site_data.geometry)
    db.add(site)
    db.commit()
    db.refresh(site)
    return serialize_site(db, site)


@router.get("", response_model=list[SiteResponse])
def list_sites(
    project_id: int, db: DbSession, current_user: CurrentUser
) -> list[SiteResponse]:
    project = get_owned_project(db, project_id, current_user)
    sites = list(
        db.scalars(
            select(Site)
            .where(Site.project_id == project.id)
            .order_by(Site.created_at, Site.id)
        )
    )
    return [serialize_site(db, site) for site in sites]


@router.get("/{site_id}", response_model=SiteResponse)
def get_site(
    project_id: int, site_id: int, db: DbSession, current_user: CurrentUser
) -> SiteResponse:
    site = get_owned_site(db, project_id, site_id, current_user)
    return serialize_site(db, site)


@router.patch("/{site_id}", response_model=SiteResponse)
def update_site(
    project_id: int,
    site_id: int,
    site_data: SiteUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> SiteResponse:
    site = get_owned_site(db, project_id, site_id, current_user)
    updates = site_data.model_dump(exclude_unset=True)
    if "geometry" in updates:
        set_geometry(site, updates.pop("geometry"))
    for field, value in updates.items():
        setattr(site, field, value)
    db.commit()
    db.refresh(site)
    return serialize_site(db, site)


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(
    project_id: int, site_id: int, db: DbSession, current_user: CurrentUser
) -> None:
    site = get_owned_site(db, project_id, site_id, current_user)
    db.delete(site)
    db.commit()
