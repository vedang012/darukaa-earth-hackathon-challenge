from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.site import PolygonGeometry


class AnalyticsMetric(BaseModel):
    site_id: int
    year: int
    metric: Literal["co2"] = "co2"
    unit: Literal["tonnes"] = "tonnes"
    value: float = Field(ge=0)
    grid_cells: int = Field(ge=0)


class TimeseriesPoint(BaseModel):
    year: int
    value: float = Field(ge=0)
    grid_cells: int = Field(ge=0)


class SiteTimeseriesResponse(BaseModel):
    site_id: int
    metric: Literal["co2"] = "co2"
    unit: Literal["tonnes"] = "tonnes"
    data: list[TimeseriesPoint]
    available_years: list[int]


class SiteAnalyticsDetails(BaseModel):
    site_id: int
    site_name: str
    project_id: int
    project_name: str
    geometry: PolygonGeometry
    analytics: AnalyticsMetric
    available_years: list[int]


class ProjectSummary(BaseModel):
    id: int
    name: str
    description: str | None


class DashboardSite(BaseModel):
    id: int
    name: str
    geometry: PolygonGeometry
    analytics: AnalyticsMetric | None


class ProjectDashboard(BaseModel):
    project: ProjectSummary
    sites: list[DashboardSite]


class DatasetMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_name: str
    source: str
    years: list[int]
    metric: Literal["co2"] = "co2"
    unit: Literal["tonnes"] = "tonnes"
    geographic_resolution: str
    description: str
