from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import UserSession, check_permission, require_permission
from apps.api.app.db.session import get_db
from apps.api.app.models.entities import Deployment, Project, Workload
from apps.api.app.schemas.domain import DeploymentCreate, DeploymentResponse, RollbackResponse
from apps.api.app.services.deploy_service import DeploymentPlatformService

router = APIRouter(tags=["Deployments & Rollback"])


async def _verify_workload_org(db: AsyncSession, workload_id: str, org_id: str) -> Workload:
    res = await db.execute(
        select(Workload)
        .join(Project, Workload.project_id == Project.id)
        .where(Workload.id == workload_id, Project.organization_id == org_id)
    )
    workload = res.scalar_one_or_none()
    if not workload:
        raise HTTPException(status_code=404, detail="Workload not found")
    return workload


@router.post(
    "/workloads/{workload_id}/deployments",
    response_model=DeploymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_deployment(
    workload_id: str,
    payload: DeploymentCreate,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("deployments:create")),
):
    await _verify_workload_org(db, workload_id, user.organization_id)

    if payload.bypass_gate:
        if not check_permission(user, "deployments:bypass_gate"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Break-glass bypass requires 'deployments:bypass_gate' permission",
            )
        if not payload.bypass_reason or not payload.bypass_reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Explicit non-empty bypass_reason is required for break-glass deployment",
            )

    try:
        dep = await DeploymentPlatformService.create_deployment(
            db=db,
            workload_id=workload_id,
            version=payload.version,
            environment=payload.environment,
            strategy=payload.strategy,
            bypass_gate=payload.bypass_gate,
            bypass_reason=payload.bypass_reason,
            user_id=user.user_id,
            org_id=user.organization_id,
            idempotency_key=idempotency_key,
        )
        return dep
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/workloads/{workload_id}/deployments", response_model=list[DeploymentResponse])
async def list_workload_deployments(
    workload_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("workloads:read")),
):
    await _verify_workload_org(db, workload_id, user.organization_id)
    res = await db.execute(
        select(Deployment)
        .where(Deployment.workload_id == workload_id)
        .order_by(Deployment.created_at.desc())
    )
    return list(res.scalars().all())


@router.get("/deployments", response_model=list[DeploymentResponse])
async def list_all_deployments(
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("workloads:read")),
):
    res = await db.execute(
        select(Deployment)
        .join(Workload, Deployment.workload_id == Workload.id)
        .join(Project, Workload.project_id == Project.id)
        .where(Project.organization_id == user.organization_id)
        .order_by(Deployment.created_at.desc())
    )
    return list(res.scalars().all())


@router.post("/deployments/{deployment_id}/rollback", response_model=RollbackResponse)
async def rollback_deployment(
    deployment_id: str,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("deployments:rollback")),
):
    res_dep = await db.execute(
        select(Deployment)
        .join(Workload, Deployment.workload_id == Workload.id)
        .join(Project, Workload.project_id == Project.id)
        .where(Deployment.id == deployment_id, Project.organization_id == user.organization_id)
    )
    if not res_dep.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Deployment not found")

    try:
        res = await DeploymentPlatformService.rollback_deployment(
            db=db,
            deployment_id=deployment_id,
            user_id=user.user_id,
            org_id=user.organization_id,
            idempotency_key=idempotency_key,
        )
        return RollbackResponse(**res)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
