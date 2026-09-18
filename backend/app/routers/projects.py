from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.resources import get_owned_project
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate


router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate, db: DbSession, current_user: CurrentUser
) -> Project:
    project = Project(owner_id=current_user.id, **project_data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectResponse])
def list_projects(db: DbSession, current_user: CurrentUser) -> list[Project]:
    return list(
        db.scalars(
            select(Project)
            .where(Project.owner_id == current_user.id)
            .order_by(Project.created_at, Project.id)
        )
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int, db: DbSession, current_user: CurrentUser
) -> Project:
    return get_owned_project(db, project_id, current_user)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Project:
    project = get_owned_project(db, project_id, current_user)
    for field, value in project_data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: DbSession, current_user: CurrentUser) -> None:
    project = get_owned_project(db, project_id, current_user)
    db.delete(project)
    db.commit()
