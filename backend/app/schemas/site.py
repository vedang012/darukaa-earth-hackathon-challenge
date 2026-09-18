from datetime import datetime
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PolygonGeometry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["Polygon"]
    coordinates: list[list[tuple[float, float]]]

    @field_validator("coordinates")
    @classmethod
    def validate_rings(
        cls, rings: list[list[tuple[float, float]]]
    ) -> list[list[tuple[float, float]]]:
        if not rings:
            raise ValueError("Polygon must contain at least one linear ring")
        for ring in rings:
            if len(ring) < 4:
                raise ValueError("Polygon rings must contain at least four positions")
            if ring[0] != ring[-1]:
                raise ValueError("Polygon rings must be closed")
            for longitude, latitude in ring:
                if not isfinite(longitude) or not isfinite(latitude):
                    raise ValueError("Polygon coordinates must be finite numbers")
                if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
                    raise ValueError("Polygon coordinates must use valid longitude/latitude ranges")
        return rings


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    geometry: PolygonGeometry


class SiteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    geometry: PolygonGeometry | None = None


class SiteResponse(BaseModel):
    id: int
    project_id: int
    name: str
    description: str | None
    geometry: PolygonGeometry
    created_at: datetime
    updated_at: datetime
