
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import UserSession, get_current_user
from apps.api.app.db.session import get_db
from apps.api.app.schemas.domain import (
    CostSummary,
    GatewayChatRequest,
    GatewayChatResponse,
)
from apps.api.app.services.gateway_service import LLMGatewayService

router = APIRouter(tags=["LLM Gateway & Costs"])


@router.post("/workloads/{workload_id}/gateway/chat", response_model=GatewayChatResponse)
async def gateway_chat(
    workload_id: str,
    payload: GatewayChatRequest,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
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
    user: UserSession = Depends(get_current_user),
):
    summary = await LLMGatewayService.get_cost_summary(db=db, workload_id=workload_id)
    return CostSummary(**summary)
