from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import UserSession, require_permission
from apps.api.app.db.session import get_db
from apps.api.app.models.entities import EvaluationRun, Project, Workload
from apps.api.app.schemas.domain import EvaluationRunRequest, EvaluationRunResponse
from apps.api.app.services.eval_service import EvaluationEngineService

router = APIRouter(tags=["Evaluation & Quality Gates"])


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


@router.post("/workloads/{workload_id}/evaluations", response_model=EvaluationRunResponse)
async def run_evaluation(
    workload_id: str,
    payload: EvaluationRunRequest,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("evaluations:run")),
):
    await _verify_workload_org(db, workload_id, user.organization_id)
    try:
        res = await EvaluationEngineService.evaluate_workload_version(
            db=db,
            workload_id=workload_id,
            version=payload.version,
            policy=payload.policy,
            user_id=user.user_id,
        )
        return EvaluationRunResponse(
            id=res["id"],
            workload_id=res["workload_id"],
            version=res["version"],
            status=res["status"],
            passed=res["passed"],
            decision=res["decision"],
            metrics=res["metrics"],
            reasons=res["reasons"],
            started_at=res["started_at"],
            completed_at=res["completed_at"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workloads/{workload_id}/evaluations", response_model=list[EvaluationRunResponse])
async def list_workload_evaluations(
    workload_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("workloads:read")),
):
    await _verify_workload_org(db, workload_id, user.organization_id)
    res = await db.execute(
        select(EvaluationRun)
        .where(EvaluationRun.workload_id == workload_id)
        .order_by(EvaluationRun.started_at.desc())
    )
    runs = res.scalars().all()
    return [
        EvaluationRunResponse(
            id=r.id,
            workload_id=r.workload_id,
            version=r.version,
            status=r.status,
            passed=r.passed,
            decision=r.decision,
            metrics=r.metrics_json or {},
            reasons=r.reasons_json or [],
            started_at=r.started_at,
            completed_at=r.completed_at,
        )
        for r in runs
    ]


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationRunResponse)
async def get_evaluation(
    evaluation_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("workloads:read")),
):
    res = await db.execute(
        select(EvaluationRun)
        .join(Workload, EvaluationRun.workload_id == Workload.id)
        .join(Project, Workload.project_id == Project.id)
        .where(EvaluationRun.id == evaluation_id, Project.organization_id == user.organization_id)
    )
    r = res.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return EvaluationRunResponse(
        id=r.id,
        workload_id=r.workload_id,
        version=r.version,
        status=r.status,
        passed=r.passed,
        decision=r.decision,
        metrics=r.metrics_json or {},
        reasons=r.reasons_json or [],
        started_at=r.started_at,
        completed_at=r.completed_at,
    )
