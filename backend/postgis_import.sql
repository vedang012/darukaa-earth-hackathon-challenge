-- Darukaa.Earth: import EDGAR 2024 CO2 grid
-- Reference SQL only. The authoritative Phase 3A path is:
--   uv run alembic upgrade head
--   uv run python -m scripts.import_edgar <csv-path>
-- The migration/importer also enforce a unique grid-cell key and safe reruns.
-- Run after enabling PostGIS:
-- CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS emissions_grid (
    id BIGSERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    lon_center DOUBLE PRECISION NOT NULL,
    lat_center DOUBLE PRECISION NOT NULL,
    co2_tonnes DOUBLE PRECISION NOT NULL,
    geometry GEOMETRY(Polygon, 4326) NOT NULL
);

-- Import the CSV into a staging table first:
CREATE TEMP TABLE edgar_staging (
    lon_center DOUBLE PRECISION,
    lat_center DOUBLE PRECISION,
    co2_tonnes DOUBLE PRECISION,
    year INTEGER,
    min_lon DOUBLE PRECISION,
    max_lon DOUBLE PRECISION,
    min_lat DOUBLE PRECISION,
    max_lat DOUBLE PRECISION
);

-- In psql, run:
-- \copy edgar_staging FROM 'edgar_india_co2_2024_grid.csv' WITH (FORMAT csv, HEADER true);

INSERT INTO emissions_grid (
    year, lon_center, lat_center, co2_tonnes, geometry
)
SELECT
    year,
    lon_center,
    lat_center,
    co2_tonnes,
    ST_MakeEnvelope(
        min_lon, min_lat,
        max_lon, max_lat,
        4326
    )
FROM edgar_staging;

CREATE INDEX IF NOT EXISTS emissions_grid_geometry_idx
ON emissions_grid
USING GIST (geometry);

CREATE INDEX IF NOT EXISTS emissions_grid_year_idx
ON emissions_grid (year);

ANALYZE emissions_grid;

-- Example: find EDGAR cells intersecting a site polygon.
-- Replace the GeoJSON geometry with your actual site geometry.
--
-- WITH site AS (
--   SELECT ST_SetSRID(
--     ST_GeomFromGeoJSON('YOUR_GEOJSON_GEOMETRY_HERE'),
--     4326
--   ) AS geometry
-- )
-- SELECT
--   e.id,
--   e.co2_tonnes,
--   ST_Area(
--     ST_Transform(ST_Intersection(e.geometry, site.geometry), 6933)
--   ) /
--   ST_Area(ST_Transform(e.geometry, 6933)) AS overlap_fraction
-- FROM emissions_grid e
-- CROSS JOIN site
-- WHERE e.year = 2024
--   AND ST_Intersects(e.geometry, site.geometry);
