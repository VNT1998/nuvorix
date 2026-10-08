
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import UserSession, get_current_user
from apps.api.app.db.session import get_db
from apps.api.app.models.entities import Deployment
from apps.api.app.schemas.domain import DeploymentCreate, DeploymentResponse, RollbackResponse
from apps.api.app.services.deploy_service import DeploymentPlatformService

router = APIRouter(tags=["Deployments & Rollback"])


@router.post("/workloads/{workload_id}/deployments", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def create_deployment(
    workload_id: str,
    payload: DeploymentCreate,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    try:
        dep = await DeploymentPlatformService.create_deployment(
            db=db,
            workload_id=workload_id,
            version=payload.version,
            environment=payload.environment,
            strategy=payload.strategy,
            user_id=user.user_id,
        )
        return dep
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workloads/{workload_id}/deployments", response_model=list[DeploymentResponse])
async def list_workload_deployments(
    workload_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    res = await db.execute(
        select(Deployment).where(Deployment.workload_id == workload_id).order_by(Deployment.created_at.desc())
    )
    return list(res.scalars().all())


@router.get("/deployments", response_model=list[DeploymentResponse])
async def list_all_deployments(
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    res = await db.execute(select(Deployment).order_by(Deployment.created_at.desc()))
    return list(res.scalars().all())


@router.post("/deployments/{deployment_id}/rollback", response_model=RollbackResponse)
async def rollback_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    try:
        res = await DeploymentPlatformService.rollback_deployment(
            db=db,
            deployment_id=deployment_id,
            user_id=user.user_id,
        )
        return RollbackResponse(**res)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
