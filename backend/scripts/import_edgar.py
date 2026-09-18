"""Bulk-import a preprocessed EDGAR grid CSV into PostGIS."""

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from app.core.config import settings


EXPECTED_COLUMNS = [
    "lon_center",
    "lat_center",
    "co2_tonnes",
    "year",
    "min_lon",
    "max_lon",
    "min_lat",
    "max_lat",
]


def validate_csv(path: Path) -> dict[str, Any]:
    row_count = 0
    null_fields = 0
    duplicate_cells: set[tuple[int, float, float]] = set()
    years: Counter[int] = Counter()
    min_lon = float("inf")
    max_lon = float("-inf")
    min_lat = float("inf")
    max_lat = float("-inf")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != EXPECTED_COLUMNS:
            raise ValueError(
                f"Unexpected CSV columns. Expected {EXPECTED_COLUMNS}, "
                f"received {reader.fieldnames}"
            )

        for line_number, row in enumerate(reader, start=2):
            row_count += 1
            null_fields += sum(value is None or value.strip() == "" for value in row.values())
            if any(value is None or value.strip() == "" for value in row.values()):
                raise ValueError(f"The EDGAR CSV contains a null or blank field on line {line_number}")
            try:
                lon_center = float(row["lon_center"])
                lat_center = float(row["lat_center"])
                float(row["co2_tonnes"])
                year = int(row["year"])
                row_min_lon = float(row["min_lon"])
                row_max_lon = float(row["max_lon"])
                row_min_lat = float(row["min_lat"])
                row_max_lat = float(row["max_lat"])
            except (AttributeError, TypeError, ValueError) as exc:
                raise ValueError(f"Invalid numeric value on CSV line {line_number}") from exc

            if not row_min_lon < row_max_lon or not row_min_lat < row_max_lat:
                raise ValueError(f"Invalid cell bounds on CSV line {line_number}")
            if not row_min_lon <= lon_center <= row_max_lon:
                raise ValueError(f"Longitude center is outside bounds on line {line_number}")
            if not row_min_lat <= lat_center <= row_max_lat:
                raise ValueError(f"Latitude center is outside bounds on line {line_number}")

            key = (year, lon_center, lat_center)
            if key in duplicate_cells:
                raise ValueError(f"Duplicate grid cell on CSV line {line_number}: {key}")
            duplicate_cells.add(key)
            years[year] += 1
            min_lon = min(min_lon, row_min_lon)
            max_lon = max(max_lon, row_max_lon)
            min_lat = min(min_lat, row_min_lat)
            max_lat = max(max_lat, row_max_lat)

    if row_count == 0:
        raise ValueError("The EDGAR CSV contains no data rows")
    if null_fields:
        raise ValueError(f"The EDGAR CSV contains {null_fields} null or blank fields")

    return {
        "row_count": row_count,
        "years": dict(years),
        "min_lon": min_lon,
        "max_lon": max_lon,
        "min_lat": min_lat,
        "max_lat": max_lat,
    }


def import_csv(path: Path, database_url: str) -> dict[str, Any]:
    summary = validate_csv(path)
    engine = create_engine(database_url)
    connection = engine.raw_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TEMP TABLE edgar_import_staging (
                lon_center DOUBLE PRECISION NOT NULL,
                lat_center DOUBLE PRECISION NOT NULL,
                co2_tonnes DOUBLE PRECISION NOT NULL,
                year SMALLINT NOT NULL,
                min_lon DOUBLE PRECISION NOT NULL,
                max_lon DOUBLE PRECISION NOT NULL,
                min_lat DOUBLE PRECISION NOT NULL,
                max_lat DOUBLE PRECISION NOT NULL
            ) ON COMMIT DROP
            """
        )
        with path.open("rb") as file, cursor.copy(
            "COPY edgar_import_staging FROM STDIN WITH (FORMAT csv, HEADER true)"
        ) as copy:
            while chunk := file.read(1024 * 1024):
                copy.write(chunk)

        cursor.execute(
            """
            DELETE FROM emissions_grid
            WHERE year IN (SELECT DISTINCT year FROM edgar_import_staging)
            """
        )
        cursor.execute(
            """
            INSERT INTO emissions_grid (
                year, lon_center, lat_center, co2_tonnes, geometry
            )
            SELECT
                year,
                lon_center,
                lat_center,
                co2_tonnes,
                ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
            FROM edgar_import_staging
            """
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
        engine.dispose()

    return summary


def verify_import(database_url: str, site_id: int | None = None) -> None:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        checks = {
            "row_count": connection.execute(
                text("SELECT COUNT(*) FROM emissions_grid")
            ).scalar_one(),
            "bounds": connection.execute(
                text(
                    "SELECT MIN(lon_center), MAX(lon_center), "
                    "MIN(lat_center), MAX(lat_center) FROM emissions_grid"
                )
            ).one(),
            "years": connection.execute(
                text("SELECT DISTINCT year FROM emissions_grid ORDER BY year")
            ).scalars().all(),
            "null_values": connection.execute(
                text(
                    "SELECT COUNT(*) FROM emissions_grid "
                    "WHERE geometry IS NULL OR co2_tonnes IS NULL"
                )
            ).scalar_one(),
            "invalid_geometries": connection.execute(
                text("SELECT COUNT(*) FROM emissions_grid WHERE NOT ST_IsValid(geometry)")
            ).scalar_one(),
            "srid": connection.execute(
                text("SELECT ST_SRID(geometry) FROM emissions_grid LIMIT 1")
            ).scalar_one(),
            "geometry_types": connection.execute(
                text("SELECT DISTINCT ST_GeometryType(geometry) FROM emissions_grid")
            ).scalars().all(),
            "spatial_index": connection.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM pg_indexes "
                    "WHERE tablename = 'emissions_grid' "
                    "AND indexname = 'emissions_grid_geometry_idx')"
                )
            ).scalar_one(),
        }
        print("EDGAR validation:")
        for name, value in checks.items():
            print(f"  {name}: {value}")

        if site_id is not None:
            intersections = connection.execute(
                text(
                    "SELECT e.id, e.co2_tonnes "
                    "FROM emissions_grid e "
                    "JOIN sites s ON ST_Intersects(e.geometry, s.geometry) "
                    "WHERE s.id = :site_id AND e.year = 2024 "
                    "ORDER BY e.id"
                ),
                {"site_id": site_id},
            ).all()
            print(f"Spatial intersection for site_id={site_id}:")
            print(f"  intersecting_cells: {len(intersections)}")
            for row in intersections[:10]:
                print(f"  cell id={row.id}, co2_tonnes={row.co2_tonnes}")

    engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--site-id", type=int, help="Existing sites.id for ST_Intersects verification")
    args = parser.parse_args()

    summary = import_csv(args.csv_path, settings.database_url)
    print(f"Imported {summary['row_count']} rows from {args.csv_path}")
    print(f"Years: {summary['years']}")
    print(
        "Bounds: "
        f"lon {summary['min_lon']}..{summary['max_lon']}, "
        f"lat {summary['min_lat']}..{summary['max_lat']}"
    )
    verify_import(settings.database_url, args.site_id)


if __name__ == "__main__":
    main()
