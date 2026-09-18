import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, text
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models.project import Project
from app.models.site import Site
from app.models.user import User
from app.models.emissions_grid import EmissionsGrid


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL must point to a dedicated PostgreSQL test database",
)


POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [73.70, 18.55],
            [73.78, 18.62],
            [73.90, 18.58],
            [73.94, 18.48],
            [73.82, 18.43],
            [73.70, 18.55],
        ]
    ],
}


@pytest.fixture(scope="session")
def test_engine():
    assert TEST_DATABASE_URL is not None
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client(test_engine):
    test_session_factory = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_db():
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

    with test_session_factory() as db:
        db.execute(delete(EmissionsGrid))
        db.execute(delete(Site))
        db.execute(delete(Project))
        db.execute(delete(User))
        db.commit()


def register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "strong-password"},
    )
    assert response.status_code == 201
    return response.json()


def login(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "strong-password"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_project(client: TestClient, token: str, name: str = "Carbon Project") -> dict:
    response = client.post(
        "/api/v1/projects",
        headers=auth_headers(token),
        json={"name": name, "description": "A test project"},
    )
    assert response.status_code == 201
    return response.json()


def create_site(client: TestClient, token: str, project_id: int, geometry=POLYGON) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/sites",
        headers=auth_headers(token),
        json={"name": "Pune Site", "description": "A test site", "geometry": geometry},
    )
    assert response.status_code == 201
    return response.json()


def seed_emissions(test_engine, rows: list[tuple[int, float, float, float, float, float, float, float]]):
    with test_engine.begin() as connection:
        for year, lon_center, lat_center, co2, min_lon, min_lat, max_lon, max_lat in rows:
            connection.execute(
                text(
                    "INSERT INTO emissions_grid "
                    "(year, lon_center, lat_center, co2_tonnes, geometry) "
                    "VALUES (:year, :lon_center, :lat_center, :co2, "
                    "ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))"
                ),
                {
                    "year": year,
                    "lon_center": lon_center,
                    "lat_center": lat_center,
                    "co2": co2,
                    "min_lon": min_lon,
                    "min_lat": min_lat,
                    "max_lon": max_lon,
                    "max_lat": max_lat,
                },
            )


def test_unauthenticated_project_request_is_rejected(client: TestClient):
    response = client.get("/api/v1/projects")

    assert response.status_code == 401


def test_user_can_create_list_retrieve_update_and_delete_project(client: TestClient):
    user = register(client, "owner@example.com")
    token = login(client, user["email"])
    project = create_project(client, token)

    listed = client.get("/api/v1/projects", headers=auth_headers(token))
    retrieved = client.get(
        f"/api/v1/projects/{project['id']}", headers=auth_headers(token)
    )
    updated = client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=auth_headers(token),
        json={"name": "Updated Project"},
    )

    assert [item["id"] for item in listed.json()] == [project["id"]]
    assert retrieved.status_code == 200
    assert updated.json()["name"] == "Updated Project"
    assert client.delete(
        f"/api/v1/projects/{project['id']}", headers=auth_headers(token)
    ).status_code == 204
    assert client.get(
        f"/api/v1/projects/{project['id']}", headers=auth_headers(token)
    ).status_code == 404


def test_user_sees_only_owned_projects_and_cannot_modify_another_users_project(
    client: TestClient,
):
    owner = register(client, "owner@example.com")
    other = register(client, "other@example.com")
    owner_token = login(client, owner["email"])
    other_token = login(client, other["email"])
    project = create_project(client, owner_token)

    listed = client.get("/api/v1/projects", headers=auth_headers(other_token))
    retrieve = client.get(
        f"/api/v1/projects/{project['id']}", headers=auth_headers(other_token)
    )
    update = client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=auth_headers(other_token),
        json={"name": "Hijacked"},
    )
    delete_response = client.delete(
        f"/api/v1/projects/{project['id']}", headers=auth_headers(other_token)
    )

    assert listed.json() == []
    assert retrieve.status_code == update.status_code == delete_response.status_code == 404


def test_project_delete_cascades_to_sites(client: TestClient):
    user = register(client, "owner@example.com")
    token = login(client, user["email"])
    project = create_project(client, token)
    site = create_site(client, token, project["id"])

    assert client.delete(
        f"/api/v1/projects/{project['id']}", headers=auth_headers(token)
    ).status_code == 204
    response = client.get(
        f"/api/v1/projects/{project['id']}/sites/{site['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_user_can_create_list_retrieve_update_and_delete_site(client: TestClient):
    user = register(client, "owner@example.com")
    token = login(client, user["email"])
    project = create_project(client, token)
    site = create_site(client, token, project["id"])

    listed = client.get(
        f"/api/v1/projects/{project['id']}/sites", headers=auth_headers(token)
    )
    retrieved = client.get(
        f"/api/v1/projects/{project['id']}/sites/{site['id']}",
        headers=auth_headers(token),
    )
    updated = client.patch(
        f"/api/v1/projects/{project['id']}/sites/{site['id']}",
        headers=auth_headers(token),
        json={"name": "Updated Site", "geometry": POLYGON},
    )
    deleted = client.delete(
        f"/api/v1/projects/{project['id']}/sites/{site['id']}",
        headers=auth_headers(token),
    )

    assert listed.status_code == retrieved.status_code == 200
    assert listed.json()[0]["geometry"]["type"] == "Polygon"
    assert retrieved.json()["geometry"]["coordinates"] == POLYGON["coordinates"]
    assert updated.json()["name"] == "Updated Site"
    assert deleted.status_code == 204


def test_site_analytics_sums_intersecting_grid_cells(client: TestClient, test_engine):
    user = register(client, "analytics@example.com")
    token = login(client, user["email"])
    project = create_project(client, token)
    site = create_site(client, token, project["id"])
    seed_emissions(
        test_engine,
        [
            (2024, 73.75, 18.50, 10.5, 73.70, 18.50, 73.80, 18.60),
            (2024, 73.85, 18.50, 20.25, 73.80, 18.50, 73.90, 18.60),
            (2024, 80.05, 20.05, 999.0, 80.00, 20.00, 80.10, 20.10),
        ],
    )

    response = client.get(
        f"/api/v1/sites/{site['id']}/analytics",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json() == {
        "site_id": site["id"],
        "year": 2024,
        "metric": "co2",
        "unit": "tonnes",
        "value": 30.75,
        "grid_cells": 2,
    }


def test_site_analytics_timeseries_returns_only_available_years(
    client: TestClient, test_engine
):
    user = register(client, "timeseries@example.com")
    token = login(client, user["email"])
    project = create_project(client, token)
    site = create_site(client, token, project["id"])
    seed_emissions(
        test_engine,
        [(2024, 73.75, 18.50, 10.5, 73.70, 18.50, 73.80, 18.60)],
    )

    response = client.get(
        f"/api/v1/sites/{site['id']}/analytics/timeseries",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["available_years"] == [2024]
    assert response.json()["data"] == [
        {"year": 2024, "value": 10.5, "grid_cells": 1}
    ]


def test_site_analytics_details_returns_geojson_and_project_info(
    client: TestClient, test_engine
):
    user = register(client, "details@example.com")
    token = login(client, user["email"])
    project = create_project(client, token, "Analytics Project")
    site = create_site(client, token, project["id"])
    seed_emissions(
        test_engine,
        [(2024, 73.75, 18.50, 10.5, 73.70, 18.50, 73.80, 18.60)],
    )

    response = client.get(
        f"/api/v1/sites/{site['id']}/analytics/details",
        headers=auth_headers(token),
    )
    body = response.json()

    assert response.status_code == 200
    assert body["project_name"] == "Analytics Project"
    assert body["geometry"]["type"] == "Polygon"
    assert body["analytics"]["value"] == 10.5


def test_analytics_rejects_missing_and_unauthorized_sites(client: TestClient):
    owner = register(client, "analytics-owner@example.com")
    other = register(client, "analytics-other@example.com")
    owner_token = login(client, owner["email"])
    other_token = login(client, other["email"])
    project = create_project(client, owner_token)
    site = create_site(client, owner_token, project["id"])

    missing_auth = client.get(f"/api/v1/sites/{site['id']}/analytics")
    unauthorized = client.get(
        f"/api/v1/sites/{site['id']}/analytics",
        headers=auth_headers(other_token),
    )
    missing_site = client.get(
        "/api/v1/sites/999999/analytics",
        headers=auth_headers(owner_token),
    )

    assert missing_auth.status_code == 401
    assert unauthorized.status_code == 404
    assert missing_site.status_code == 404


def test_site_without_intersecting_data_returns_not_found(
    client: TestClient, test_engine
):
    user = register(client, "no-data@example.com")
    token = login(client, user["email"])
    project = create_project(client, token)
    outside_polygon = {
        "type": "Polygon",
        "coordinates": [[[120.0, 40.0], [120.1, 40.0], [120.1, 40.1], [120.0, 40.0]]],
    }
    site = create_site(client, token, project["id"], outside_polygon)
    seed_emissions(
        test_engine,
        [(2024, 73.75, 18.50, 10.5, 73.70, 18.50, 73.80, 18.60)],
    )

    response = client.get(
        f"/api/v1/sites/{site['id']}/analytics",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No environmental data intersects this site"


def test_project_dashboard_and_dataset_metadata(client: TestClient, test_engine):
    user = register(client, "dashboard@example.com")
    token = login(client, user["email"])
    project = create_project(client, token, "Dashboard Project")
    site = create_site(client, token, project["id"])
    seed_emissions(
        test_engine,
        [(2024, 73.75, 18.50, 10.5, 73.70, 18.50, 73.80, 18.60)],
    )

    dashboard = client.get(
        f"/api/v1/projects/{project['id']}/dashboard",
        headers=auth_headers(token),
    )
    metadata = client.get(
        "/api/v1/analytics/datasets",
        headers=auth_headers(token),
    )

    assert dashboard.status_code == 200
    assert dashboard.json()["project"]["name"] == "Dashboard Project"
    assert dashboard.json()["sites"][0]["id"] == site["id"]
    assert dashboard.json()["sites"][0]["analytics"]["value"] == 10.5
    assert metadata.status_code == 200
    assert metadata.json()["years"] == [2024]
    assert metadata.json()["unit"] == "tonnes"


def test_project_dashboard_supports_project_with_no_sites(client: TestClient):
    user = register(client, "empty-dashboard@example.com")
    token = login(client, user["email"])
    project = create_project(client, token, "Empty Dashboard Project")

    response = client.get(
        f"/api/v1/projects/{project['id']}/dashboard",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["sites"] == []


def test_site_geometry_uses_srid_4326_and_spatial_index_exists(
    client: TestClient, test_engine
):
    user = register(client, "owner@example.com")
    token = login(client, user["email"])
    project = create_project(client, token)
    site = create_site(client, token, project["id"])

    with test_engine.connect() as connection:
        srid = connection.execute(
            text("SELECT ST_SRID(geometry) FROM sites WHERE id = :site_id"),
            {"site_id": site["id"]},
        ).scalar_one()
        index_exists = connection.execute(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM pg_indexes "
                "WHERE tablename = 'sites' AND indexname = 'sites_geometry_idx'"
                ")"
            )
        ).scalar_one()

    assert srid == 4326
    assert index_exists is True


def test_user_cannot_access_sites_belonging_to_another_users_project(client: TestClient):
    owner = register(client, "owner@example.com")
    other = register(client, "other@example.com")
    owner_token = login(client, owner["email"])
    other_token = login(client, other["email"])
    project = create_project(client, owner_token)
    site = create_site(client, owner_token, project["id"])

    list_response = client.get(
        f"/api/v1/projects/{project['id']}/sites", headers=auth_headers(other_token)
    )
    site_response = client.get(
        f"/api/v1/projects/{project['id']}/sites/{site['id']}",
        headers=auth_headers(other_token),
    )

    assert list_response.status_code == site_response.status_code == 404


@pytest.mark.parametrize(
    "geometry",
    [
        {"type": "Point", "coordinates": [73.7, 18.55]},
        {"type": "Polygon", "coordinates": [[[73.7, 18.55], [73.8, 18.6]]]},
        {
            "type": "Polygon",
            "coordinates": [
                [[73.7, 18.55], [73.8, 18.6], [73.9, 18.5], [73.7, 18.55]]
            ],
        },
        {
            "type": "Polygon",
            "coordinates": [
                [
                    [73.7, 18.55],
                    [73.9, 18.65],
                    [73.7, 18.65],
                    [73.9, 18.55],
                    [73.7, 18.55],
                ]
            ],
        },
    ],
)
def test_invalid_geojson_is_rejected(client: TestClient, geometry: dict):
    user = register(client, "owner@example.com")
    token = login(client, user["email"])
    project = create_project(client, token)

    response = client.post(
        f"/api/v1/projects/{project['id']}/sites",
        headers=auth_headers(token),
        json={"name": "Invalid Site", "geometry": geometry},
    )

    assert response.status_code == 422
