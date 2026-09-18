import csv

import pytest

from scripts.import_edgar import EXPECTED_COLUMNS, validate_csv


def write_csv(tmp_path, rows, fieldnames=EXPECTED_COLUMNS):
    path = tmp_path / "edgar.csv"
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def valid_row(**overrides):
    row = {
        "lon_center": "73.05",
        "lat_center": "18.05",
        "co2_tonnes": "12.5",
        "year": "2024",
        "min_lon": "73.0",
        "max_lon": "73.1",
        "min_lat": "18.0",
        "max_lat": "18.1",
    }
    row.update(overrides)
    return row


def test_validate_csv_accepts_actual_shape(tmp_path):
    summary = validate_csv(write_csv(tmp_path, [valid_row()]))

    assert summary["row_count"] == 1
    assert summary["years"] == {2024: 1}
    assert summary["min_lon"] == 73.0
    assert summary["max_lat"] == 18.1


@pytest.mark.parametrize(
    "row, message",
    [
        (valid_row(lon_center="73.2"), "outside bounds"),
        (valid_row(min_lon="73.1"), "Invalid cell bounds"),
        (valid_row(co2_tonnes=""), "null or blank"),
    ],
)
def test_validate_csv_rejects_bad_rows(tmp_path, row, message):
    with pytest.raises(ValueError, match=message):
        validate_csv(write_csv(tmp_path, [row]))


def test_validate_csv_rejects_duplicate_cells(tmp_path):
    with pytest.raises(ValueError, match="Duplicate grid cell"):
        validate_csv(write_csv(tmp_path, [valid_row(), valid_row()]))


def test_validate_csv_rejects_unexpected_columns(tmp_path):
    with pytest.raises(ValueError, match="Unexpected CSV columns"):
        validate_csv(write_csv(tmp_path, [valid_row()], fieldnames=["lon", "lat"]))
