from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.site import Site
from app.models.user import User


def get_owned_project(db: Session, project_id: int, user: User) -> Project:
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def get_owned_site(
    db: Session, project_id: int, site_id: int, user: User
) -> Site:
    site = db.scalar(
        select(Site)
        .join(Project, Site.project_id == Project.id)
        .where(
            Site.id == site_id,
            Site.project_id == project_id,
            Project.owner_id == user.id,
        )
    )
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site
