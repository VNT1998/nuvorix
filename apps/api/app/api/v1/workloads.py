from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import UserSession, get_current_user
from apps.api.app.core.telemetry import ACTIVE_WORKLOADS_GAUGE
from apps.api.app.db.session import get_db
from apps.api.app.models.entities import AuditEvent, Project, Workload
from apps.api.app.schemas.domain import WorkloadCreate, WorkloadResponse

router = APIRouter(tags=["Workloads"])


@router.post("/projects/{project_id}/workloads", response_model=WorkloadResponse, status_code=status.HTTP_201_CREATED)
async def create_workload(
    project_id: str,
    payload: WorkloadCreate,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    res_p = await db.execute(select(Project).where(Project.id == project_id))
    if not res_p.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    workload = Workload(
        project_id=project_id,
        name=payload.name,
        type=payload.type,
        status="healthy",
    )
    db.add(workload)
    await db.flush()
    
    audit = AuditEvent(
        organization_id=user.organization_id,
        user_id=user.user_id,
        action="workloads:create",
        resource_type="workload",
        resource_id=workload.id,
        metadata_json={"name": payload.name, "type": payload.type},
    )
    db.add(audit)
    ACTIVE_WORKLOADS_GAUGE.labels(type=payload.type).inc()
    await db.commit()
    await db.refresh(workload)
    return workload


@router.get("/projects/{project_id}/workloads", response_model=list[WorkloadResponse])
async def list_project_workloads(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    res = await db.execute(
        select(Workload).where(Workload.project_id == project_id).order_by(Workload.created_at.desc())
    )
    return list(res.scalars().all())


@router.get("/workloads", response_model=list[WorkloadResponse])
async def list_all_workloads(
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    res = await db.execute(select(Workload).order_by(Workload.created_at.desc()))
    return list(res.scalars().all())


@router.get("/workloads/{workload_id}", response_model=WorkloadResponse)
async def get_workload(
    workload_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    res = await db.execute(select(Workload).where(Workload.id == workload_id))
    workload = res.scalar_one_or_none()
    if not workload:
        raise HTTPException(status_code=404, detail="Workload not found")
    return workload
