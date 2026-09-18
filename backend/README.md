# Darukaa.Earth Backend

Phase 1 provides the authentication foundation for Darukaa.Earth. Phase 2 adds authenticated project and site CRUD with validated GeoJSON Polygon storage in PostGIS.

EDGAR, environmental analytics, Mapbox frontend work, React, external APIs, deployment, and microservices remain out of scope.

## Phase 2 Architecture

```text
User
 ↓ owns
Project
 ↓ contains
Sites
 ↓ stores
PostGIS Polygon (SRID 4326)
```

Users own projects, and projects own sites. Every project and site query is scoped through the authenticated user. Deleting a project cascades to its sites at the database level. EPSG:4326 is used because the frontend exchanges longitude/latitude GeoJSON coordinates in WGS 84; no area or distance calculations are performed in this phase.

## Tech Stack

- Python 3.11+
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x with psycopg 3
- Pydantic v2 and pydantic-settings
- bcrypt password hashing
- PyJWT access tokens
- GeoAlchemy2, Shapely, and PostGIS
- Alembic migrations
- pytest and FastAPI TestClient

## Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── core/geometry.py
│   ├── dependencies/auth.py
│   ├── dependencies/resources.py
│   ├── models/{user,project,site}.py
│   ├── routers/{auth,projects,sites}.py
│   └── schemas/{auth,project,site}.py
├── alembic/
├── tests/test_auth.py
├── .env.example
├── alembic.ini
├── requirements.txt
└── README.md
```

`config.py` is the single configuration boundary. `database.py` provides request-scoped SQLAlchemy sessions. `security.py` owns password and JWT operations, `get_current_user` owns bearer-token validation, and `dependencies/resources.py` centralizes project/site ownership checks. `core/geometry.py` converts validated GeoJSON into SRID 4326 PostGIS values.

## Setup

From the `backend` directory, create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## PostgreSQL

Create separate development and test databases on a PostgreSQL installation that includes PostGIS. PostGIS must be installed on the PostgreSQL server, not just in the Python environment. On Windows, install PostGIS through the PostgreSQL Stack Builder for your PostgreSQL version; on Ubuntu/Debian, install the matching `postgis` package. A Docker alternative is:

```powershell
docker run --name darukaa-postgis -e POSTGRES_PASSWORD=choose-a-local-password -e POSTGRES_DB=darukaa -p 5432:5432 -d postgis/postgis:16-3.4
```

Create separate development and test databases. For a local PostgreSQL installation:

```sql
CREATE USER darukaa_user WITH PASSWORD 'choose-a-local-password';
CREATE DATABASE darukaa OWNER darukaa_user;
CREATE DATABASE darukaa_test OWNER darukaa_user;
```

Do not use these example credentials in a shared environment.

## Environment Variables

Copy the example file and replace the placeholders:

```powershell
Copy-Item .env.example .env
```

Required variables:

- `DATABASE_URL`: SQLAlchemy PostgreSQL URL, for example `postgresql+psycopg://darukaa_user:password@localhost:5432/darukaa`
- `JWT_SECRET_KEY`: a long random secret, at least 32 characters
- `JWT_ALGORITHM`: normally `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES`: access-token lifetime
- `CORS_ORIGINS`: comma-separated browser origins such as `http://localhost:3000,http://localhost:5173`

For tests, set `TEST_DATABASE_URL` to the separate `darukaa_test` database:

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://darukaa_user:password@localhost:5432/darukaa_test"
```

Never commit `.env` or real secrets.

## Migrations

Run migrations from the `backend` directory:

```powershell
alembic upgrade head
```

To roll back the initial migration:

```powershell
alembic downgrade -1
```

The application does not call `Base.metadata.create_all()`. Alembic is the production schema initialization and migration mechanism. The test fixture may create and remove tables in the dedicated test database for isolation.

## Run the API

```powershell
uvicorn app.main:app --reload
```

Open Swagger UI at <http://127.0.0.1:8000/docs>.

## API Endpoints

### `POST /api/v1/auth/register`

Request:

```json
{"email":"user@example.com","password":"strong-password"}
```

Returns `201` with the user ID, email, active status, and timestamps. Duplicate emails return `409`.

### `POST /api/v1/auth/login`

Returns `200` with an access token:

```json
{"access_token":"...","token_type":"bearer"}
```

Invalid credentials return `401`.

### `GET /api/v1/auth/me`

Requires `Authorization: Bearer <token>`. Returns the authenticated user, or `401` for a missing, invalid, expired, unknown, or inactive token.

### Projects

- `POST /api/v1/projects` creates an authenticated user's project.
- `GET /api/v1/projects` lists only the current user's projects.
- `GET /api/v1/projects/{project_id}` retrieves an owned project.
- `PATCH /api/v1/projects/{project_id}` updates `name` and `description`.
- `DELETE /api/v1/projects/{project_id}` deletes the project and its sites.

### Sites

- `POST /api/v1/projects/{project_id}/sites` creates a Polygon site.
- `GET /api/v1/projects/{project_id}/sites` lists sites for an owned project.
- `GET /api/v1/projects/{project_id}/sites/{site_id}` retrieves an owned site.
- `PATCH /api/v1/projects/{project_id}/sites/{site_id}` updates site fields or geometry.
- `DELETE /api/v1/projects/{project_id}/sites/{site_id}` deletes a site.

Site geometry must be a valid, closed GeoJSON Polygon. Example:

```json
{
	"type": "Polygon",
	"coordinates": [[[73.70, 18.55], [73.78, 18.62], [73.90, 18.58], [73.94, 18.48], [73.82, 18.43], [73.70, 18.55]]]
}
```

Responses use GeoJSON through PostGIS `ST_AsGeoJSON`; raw WKB/WKT is never exposed.

## Password and Token Security

Passwords are never stored as plaintext. A database leak containing plaintext passwords would immediately expose users' credentials, which are often reused elsewhere. bcrypt stores a deliberately expensive one-way hash instead, so the application can verify a password without being able to recover it.

JWTs contain the user ID in `sub` and an expiration timestamp in `exp`. The secret, algorithm, and lifetime are loaded from environment configuration.

## Tests

With PostgreSQL running and `TEST_DATABASE_URL` set:

```powershell
pytest -q
```

The test suite covers authentication plus project/site CRUD, ownership isolation, cascade deletion, GeoJSON round-tripping, invalid geometry, SRID 4326, and the spatial index where PostgreSQL is available.

## Phase 2 Migration Commands

```powershell
alembic upgrade head
alembic current
alembic downgrade 20260918_0001
```

Migration `20260918_0002` enables PostGIS, creates `projects` and `sites`, adds cascading foreign keys, and creates the `sites_geometry_idx` GiST index.

## EDGAR Dataset

Darukaa.Earth uses the preprocessed 2024 India EDGAR CO2 grid as its environmental emissions reference dataset. The supplied CSV contains 105,600 rows with `lon_center`, `lat_center`, `co2_tonnes`, `year`, and explicit cell bounds: `min_lon`, `max_lon`, `min_lat`, and `max_lat`.

The data is imported once into the PostGIS `emissions_grid` table. Each CSV row becomes a Polygon built from its supplied bounds and stored with SRID 4326. Runtime analytics will query these indexed grid cells spatially against stored site polygons. The raw EDGAR/NetCDF source is not processed during API startup or every request, and this phase does not calculate emissions analytics.

Preprocessing was chosen so runtime requests can use indexed spatial queries instead of repeatedly processing large scientific data files.

### EDGAR Schema

```text
emissions_grid
├── id BIGINT PRIMARY KEY
├── year SMALLINT
├── lon_center NUMERIC(8,5)
├── lat_center NUMERIC(7,5)
├── co2_tonnes DOUBLE PRECISION
└── geometry POLYGON SRID 4326
```

The migration also creates a unique `(year, lon_center, lat_center)` constraint, a year index, and the `emissions_grid_geometry_idx` GiST index.

### Import EDGAR

Run the migration first, then import the CSV from its local path. The importer validates the header, numeric values, bounds, center locations, blank values, and duplicate cells. It uses PostgreSQL `COPY` into a temporary staging table, replaces only the source years, and is safe to rerun.

```powershell
uv run alembic upgrade head
uv run python -m scripts.import_edgar C:\Users\vedan\Downloads\edgar_india_co2_2024_grid.csv
```

To verify intersections with an existing site already stored in the database:

```powershell
uv run python -m scripts.import_edgar C:\Users\vedan\Downloads\edgar_india_co2_2024_grid.csv --site-id <existing-site-id>
```

The command reports row count, coordinate bounds, years, null values, invalid geometries, SRID, geometry type, spatial-index existence, and the first ten grid cells intersecting the selected site. It does not expose an HTTP import endpoint.

## Spatial Analytics

Analytics uses database-side PostGIS queries. For each owned site, the service joins `sites` to `emissions_grid` with `ST_Intersects` and aggregates `SUM(emissions_grid.co2_tonnes)` and `COUNT(emissions_grid.id)` by year. The EDGAR import stores one `co2_tonnes` value per grid cell, so this phase treats that value as the annual total for the cell and does not multiply it by area or apply overlap weighting. This interpretation preserves the imported column and unit; it is not an emissions-density calculation.

The current database contains only 2024, so timeseries responses expose only 2024. Historical years are not fabricated. Future imported years will automatically appear in the same database-side grouped query.

### Analytics Endpoints

- `GET /api/v1/sites/{site_id}/analytics` returns the site's year, CO2 metric, tonnes unit, aggregate value, and intersecting grid-cell count.
- `GET /api/v1/sites/{site_id}/analytics/timeseries` returns available yearly aggregates only.
- `GET /api/v1/sites/{site_id}/analytics/details` returns site/project information, GeoJSON geometry, analytics, and available years.
- `GET /api/v1/projects/{project_id}/dashboard` returns project information and all owned sites with batched analytics. Sites without intersecting data remain present with `analytics: null`.
- `GET /api/v1/analytics/datasets` reports the datasets and years actually present in the database.

All analytics endpoints require JWT authentication and enforce the existing owner-only project/site behavior. A nonexistent or inaccessible site/project returns `404`; a site with no intersecting EDGAR data returns `404` with `No environmental data intersects this site` for site analytics endpoints.

## Swagger Manual Checklist

1. Register a user and confirm the response is `201` and contains no password hash.
2. Register the same email again and confirm `409`.
3. Log in and copy the returned access token.
4. Use Swagger's **Authorize** control with `Bearer <token>`.
5. Call `/api/v1/auth/me` and confirm the safe user response.
6. Clear authorization and confirm `/me` returns `401`.
7. Authorize with an altered token and confirm `/me` returns `401`.
8. Create a project.
9. Create a site with the example GeoJSON Polygon.
10. Retrieve the project and its sites.
11. Retrieve the individual site and confirm the geometry is GeoJSON.
12. Update the site name or geometry.
13. Delete the site, then delete the project.
