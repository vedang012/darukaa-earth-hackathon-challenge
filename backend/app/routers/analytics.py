from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsMetric,
    DatasetMetadata,
    ProjectDashboard,
    SiteAnalyticsDetails,
    SiteTimeseriesResponse,
)
from app.services.analytics_service import (
    get_dataset_metadata,
    get_project_dashboard,
    get_site_analytics,
    get_site_details,
    get_site_timeseries,
)


router = APIRouter(tags=["Analytics"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get(
    "/api/v1/sites/{site_id}/analytics",
    response_model=AnalyticsMetric,
    status_code=status.HTTP_200_OK,
    summary="Get environmental analytics for a site",
    description=(
        "Sums the imported EDGAR co2_tonnes values for grid cells that "
        "intersect the authenticated user's site."
    ),
)
def site_analytics(site_id: int, db: DbSession, current_user: CurrentUser) -> AnalyticsMetric:
    return get_site_analytics(db, site_id, current_user)


@router.get(
    "/api/v1/sites/{site_id}/analytics/timeseries",
    response_model=SiteTimeseriesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get available site analytics years",
)
def site_analytics_timeseries(
    site_id: int, db: DbSession, current_user: CurrentUser
) -> SiteTimeseriesResponse:
    return get_site_timeseries(db, site_id, current_user)


@router.get(
    "/api/v1/sites/{site_id}/analytics/details",
    response_model=SiteAnalyticsDetails,
    status_code=status.HTTP_200_OK,
    summary="Get site details with environmental analytics",
)
def site_analytics_details(
    site_id: int, db: DbSession, current_user: CurrentUser
) -> SiteAnalyticsDetails:
    return get_site_details(db, site_id, current_user)


@router.get(
    "/api/v1/projects/{project_id}/dashboard",
    response_model=ProjectDashboard,
    status_code=status.HTTP_200_OK,
    summary="Get a dashboard-ready project summary",
    description="Returns all owned project sites and batched spatial analytics.",
)
def project_dashboard(
    project_id: int, db: DbSession, current_user: CurrentUser
) -> ProjectDashboard:
    return get_project_dashboard(db, project_id, current_user)


@router.get(
    "/api/v1/analytics/datasets",
    response_model=DatasetMetadata,
    status_code=status.HTTP_200_OK,
    summary="List imported environmental datasets",
)
def analytics_datasets(db: DbSession, current_user: CurrentUser) -> DatasetMetadata:
    return get_dataset_metadata(db)
