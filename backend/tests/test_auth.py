import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, text
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL must point to a dedicated PostgreSQL test database",
)


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
        db.execute(delete(User))
        db.commit()


def registration_payload(email: str = "user@example.com") -> dict[str, str]:
    return {"email": email, "password": "strong-password"}


def test_successful_registration(client: TestClient):
    response = client.post("/api/v1/auth/register", json=registration_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user@example.com"
    assert body["is_active"] is True
    assert "hashed_password" not in body


def test_duplicate_registration(client: TestClient):
    client.post("/api/v1/auth/register", json=registration_payload())

    response = client.post("/api/v1/auth/register", json=registration_payload())

    assert response.status_code == 409
    assert "hashed_password" not in response.text


def test_successful_login(client: TestClient):
    client.post("/api/v1/auth/register", json=registration_payload())

    response = client.post("/api/v1/auth/login", json=registration_payload())

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_incorrect_password(client: TestClient):
    client.post("/api/v1/auth/register", json=registration_payload())

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_without_token(client: TestClient):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_valid_token(client: TestClient):
    client.post("/api/v1/auth/register", json=registration_payload())
    login_response = client.post("/api/v1/auth/login", json=registration_payload())
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"
    assert "hashed_password" not in response.json()


def test_me_with_invalid_token(client: TestClient):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
