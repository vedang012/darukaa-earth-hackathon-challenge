# Darukaa.Earth frontend

A React + JavaScript geospatial analytics frontend for the Darukaa.Earth FastAPI/PostGIS backend.

## Setup

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

The frontend defaults to `http://127.0.0.1:8000` for the API. Set these variables in `.env`:

- `VITE_API_BASE_URL`: FastAPI origin, for example `http://127.0.0.1:8000`
- `VITE_MAPBOX_TOKEN`: public Mapbox access token with Styles and Tiles access

The backend CORS configuration must include the Vite origin, normally `http://localhost:5173`.

## Commands

```powershell
npm run dev
npm run build
npm run preview
```

## Architecture

- `src/services/api.js` is the centralized fetch client. It attaches the persisted bearer token, parses FastAPI errors, and handles unauthorized responses.
- `src/context/AuthContext.jsx` owns registration, login, `/auth/me` session restoration, and logout.
- `src/pages/Projects.jsx` consumes project CRUD endpoints and handles project creation/deletion.
- `src/pages/ProjectDashboard.jsx` consumes the batched dashboard endpoint and owns site creation from drawn GeoJSON.
- `src/components/map/ProjectMap.jsx` manages the Mapbox GL JS lifecycle, GeoJSON source/layers, selection, viewport fitting, and Mapbox Draw polygon mode.
- `src/components/analytics/AnalyticsPanel.jsx` consumes site analytics, timeseries, and dataset metadata and renders the Chart.js view.

## API integration

The UI uses the real backend endpoints:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET/POST/DELETE /api/v1/projects`
- `GET /api/v1/projects/{project_id}/dashboard`
- `POST /api/v1/projects/{project_id}/sites`
- `GET /api/v1/sites/{site_id}/analytics`
- `GET /api/v1/sites/{site_id}/analytics/timeseries`
- `GET /api/v1/sites/{site_id}/analytics/details`
- `GET /api/v1/analytics/datasets`

Sites are sent as validated GeoJSON `Polygon` objects with `[longitude, latitude]` coordinate pairs. The frontend does not calculate emissions; analytics remain owned by the backend spatial queries. The chart renders only years returned by the API, including the current single-year 2024 dataset.

## User flow

Register or sign in, create a project, open its dashboard, choose **Add site**, draw a polygon, name it, and select the saved site on the map or in the site list. The analytics panel then loads the backend CO2 metric, available timeseries, and dataset metadata. Protected requests survive refresh through the stored JWT and redirect to login after a 401 response.
