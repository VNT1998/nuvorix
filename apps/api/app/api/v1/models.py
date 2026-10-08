
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import UserSession, get_current_user
from apps.api.app.db.session import get_db
from apps.api.app.models.entities import Model, ModelVersion
from apps.api.app.schemas.domain import (
    ModelCreate,
    ModelResponse,
    ModelVersionResponse,
    PromoteVersionRequest,
    TrainModelRequest,
    TrainModelResponse,
)
from apps.api.app.services.ml_service import MLPlatformService

router = APIRouter(tags=["ML Models & Registry"])


@router.post("/workloads/{workload_id}/models", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    workload_id: str,
    payload: ModelCreate,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    model = Model(
        workload_id=workload_id,
        name=payload.name,
        framework=payload.framework,
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


@router.get("/workloads/{workload_id}/models", response_model=list[ModelResponse])
async def list_workload_models(
    workload_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    res = await db.execute(select(Model).where(Model.workload_id == workload_id))
    return list(res.scalars().all())


@router.post("/workloads/{workload_id}/train", response_model=TrainModelResponse)
async def train_model(
    workload_id: str,
    payload: TrainModelRequest,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    try:
        alpha = float(payload.hyperparameters.get("alpha", 1.0))
        max_iter = int(payload.hyperparameters.get("max_iter", 1000))
        result = await MLPlatformService.train_and_register_model(
            db=db,
            workload_id=workload_id,
            model_name=payload.model_name,
            alpha=alpha,
            max_iter=max_iter,
            user_id=user.user_id,
        )
        return TrainModelResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/models/{model_id}/versions", response_model=list[ModelVersionResponse])
async def list_model_versions(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    res = await db.execute(
        select(ModelVersion).where(ModelVersion.model_id == model_id).order_by(ModelVersion.created_at.desc())
    )
    return list(res.scalars().all())


@router.get("/model-versions/{version_id}", response_model=ModelVersionResponse)
async def get_model_version(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    res = await db.execute(select(ModelVersion).where(ModelVersion.id == version_id))
    ver = res.scalar_one_or_none()
    if not ver:
        raise HTTPException(status_code=404, detail="Model version not found")
    return ver


@router.post("/model-versions/{version_id}/promote")
async def promote_model_version(
    version_id: str,
    payload: PromoteVersionRequest,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    try:
        res = await MLPlatformService.promote_version(
            db=db,
            version_id=version_id,
            target_env=payload.target_environment,
            user_id=user.user_id,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workloads/{workload_id}/mlflow-runs")
async def get_workload_mlflow_runs(
    workload_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    from apps.api.app.models.entities import Workload
    res = await db.execute(select(Workload).where(Workload.id == workload_id))
    workload = res.scalar_one_or_none()
    if not workload:
        raise HTTPException(status_code=404, detail="Workload not found")
    runs = MLPlatformService.get_runs_for_workload(workload.name)
    return {"workload_id": workload_id, "experiment": f"nuvorix-{workload.name}", "runs": runs}

