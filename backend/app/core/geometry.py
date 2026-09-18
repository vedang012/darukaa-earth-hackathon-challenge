import json

from geoalchemy2.shape import from_shape
from shapely.geometry import shape

from app.schemas.site import PolygonGeometry


def polygon_to_postgis(geometry: PolygonGeometry):
    if isinstance(geometry, dict):
        geometry = PolygonGeometry.model_validate(geometry)
    polygon = shape(geometry.model_dump())
    if polygon.geom_type != "Polygon" or polygon.is_empty or not polygon.is_valid:
        raise ValueError("Geometry must be a valid Polygon")
    return from_shape(polygon, srid=4326)


def geojson_to_response(value: str | dict) -> PolygonGeometry:
    geometry = json.loads(value) if isinstance(value, str) else value
    return PolygonGeometry.model_validate(geometry)
