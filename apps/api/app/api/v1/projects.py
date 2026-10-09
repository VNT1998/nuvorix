from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import UserSession, require_permission
from apps.api.app.db.session import get_db
from apps.api.app.models.entities import AuditEvent, Project
from apps.api.app.schemas.domain import ProjectCreate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("projects:create")),
):
    project = Project(
        organization_id=user.organization_id,
        name=payload.name,
        description=payload.description or "",
    )
    db.add(project)
    await db.flush()

    audit = AuditEvent(
        organization_id=user.organization_id,
        user_id=user.user_id,
        action="projects:create",
        resource_type="project",
        resource_id=project.id,
        metadata_json={"name": payload.name},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("projects:read")),
):
    res = await db.execute(
        select(Project)
        .where(Project.organization_id == user.organization_id)
        .order_by(Project.created_at.desc())
    )
    return list(res.scalars().all())


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("projects:read")),
):
    res = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == user.organization_id,
        )
    )
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("projects:delete")),
):
    res = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == user.organization_id,
        )
    )
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()
