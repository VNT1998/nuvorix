from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import UserSession, require_permission
from apps.api.app.db.session import get_db
from apps.api.app.models.entities import Project, Workload
from apps.api.app.schemas.domain import (
    CostSummary,
    GatewayChatRequest,
    GatewayChatResponse,
)
from apps.api.app.services.gateway_service import LLMGatewayService

router = APIRouter(tags=["LLM Gateway & Costs"])


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


@router.post("/workloads/{workload_id}/gateway/chat", response_model=GatewayChatResponse)
async def gateway_chat(
    workload_id: str,
    payload: GatewayChatRequest,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("agents:run")),
):
    await _verify_workload_org(db, workload_id, user.organization_id)
    res = await LLMGatewayService.chat_completion(
        db=db,
        workload_id=workload_id,
        prompt=payload.prompt,
        provider=payload.provider or "local",
        model=payload.model or "llama-3-8b-instruct",
        max_tokens=payload.max_tokens,
        temperature=payload.temperature,
    )
    return GatewayChatResponse(**res)


@router.get("/costs", response_model=CostSummary)
async def get_costs(
    workload_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("workloads:read")),
):
    if workload_id:
        await _verify_workload_org(db, workload_id, user.organization_id)
    summary = await LLMGatewayService.get_cost_summary(db=db, workload_id=workload_id)
    return CostSummary(**summary)
