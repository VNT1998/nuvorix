from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import UserSession, require_permission
from apps.api.app.db.session import get_db
from apps.api.app.models.entities import Model, ModelVersion, Project, Workload
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
    "/workloads/{workload_id}/models",
    response_model=ModelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_model(
    workload_id: str,
    payload: ModelCreate,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("models:register")),
):
    await _verify_workload_org(db, workload_id, user.organization_id)
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
    user: UserSession = Depends(require_permission("workloads:read")),
):
    await _verify_workload_org(db, workload_id, user.organization_id)
    res = await db.execute(select(Model).where(Model.workload_id == workload_id))
    return list(res.scalars().all())


@router.post("/workloads/{workload_id}/train", response_model=TrainModelResponse)
async def train_model(
    workload_id: str,
    payload: TrainModelRequest,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("models:train")),
):
    await _verify_workload_org(db, workload_id, user.organization_id)
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
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/models/{model_id}/versions", response_model=list[ModelVersionResponse])
async def list_model_versions(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("workloads:read")),
):
    res = await db.execute(
        select(ModelVersion)
        .join(Model, ModelVersion.model_id == Model.id)
        .join(Workload, Model.workload_id == Workload.id)
        .join(Project, Workload.project_id == Project.id)
        .where(ModelVersion.model_id == model_id, Project.organization_id == user.organization_id)
        .order_by(ModelVersion.created_at.desc())
    )
    return list(res.scalars().all())


@router.get("/model-versions/{version_id}", response_model=ModelVersionResponse)
async def get_model_version(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("workloads:read")),
):
    res = await db.execute(
        select(ModelVersion)
        .join(Model, ModelVersion.model_id == Model.id)
        .join(Workload, Model.workload_id == Workload.id)
        .join(Project, Workload.project_id == Project.id)
        .where(ModelVersion.id == version_id, Project.organization_id == user.organization_id)
    )
    ver = res.scalar_one_or_none()
    if not ver:
        raise HTTPException(status_code=404, detail="Model version not found")
    return ver


@router.post("/model-versions/{version_id}/promote")
async def promote_model_version(
    version_id: str,
    payload: PromoteVersionRequest,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("models:promote")),
):
    res_v = await db.execute(
        select(ModelVersion)
        .join(Model, ModelVersion.model_id == Model.id)
        .join(Workload, Model.workload_id == Workload.id)
        .join(Project, Workload.project_id == Project.id)
        .where(ModelVersion.id == version_id, Project.organization_id == user.organization_id)
    )
    ver = res_v.scalar_one_or_none()
    if not ver:
        raise HTTPException(status_code=404, detail="Model version not found")

    try:
        res = await MLPlatformService.promote_version(
            db=db,
            version_id=version_id,
            target_env=payload.target_environment,
            user_id=user.user_id,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/workloads/{workload_id}/mlflow-runs")
async def get_workload_mlflow_runs(
    workload_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("workloads:read")),
):
    workload = await _verify_workload_org(db, workload_id, user.organization_id)
    runs = MLPlatformService.get_runs_for_workload(workload.name)
    return {"workload_id": workload_id, "experiment": f"nuvorix-{workload.name}", "runs": runs}


@router.get("/mlflow/registered-models")
async def list_mlflow_registered_models(
    user: UserSession = Depends(require_permission("workloads:read")),
):
    """Retrieve registered models directly from MLflow Model Registry."""
    models = MLPlatformService.get_registered_models_from_mlflow()
    return {"registered_models": models, "count": len(models)}
