from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.analytics import router as analytics_router
from app.routers.projects import router as projects_router
from app.routers.sites import router as sites_router


app = FastAPI(
    title="Darukaa.Earth API",
    description="Backend foundation for Darukaa.Earth.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(analytics_router)
app.include_router(projects_router)
app.include_router(sites_router)
