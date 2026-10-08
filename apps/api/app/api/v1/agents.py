
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import UserSession, get_current_user
from apps.api.app.db.session import get_db
from apps.api.app.schemas.domain import (
    AgentRunRequest,
    AgentRunResponse,
    ToolDeclaration,
)
from apps.api.app.services.agent_service import AgentRuntimeService

router = APIRouter(tags=["Agent Runtime & MCP"])


@router.post("/workloads/{workload_id}/agents/run", response_model=AgentRunResponse)
async def run_agent(
    workload_id: str,
    payload: AgentRunRequest,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    try:
        res = await AgentRuntimeService.run_agent_workflow(
            db=db,
            workload_id=workload_id,
            prompt=payload.prompt,
            knowledge_base_id=payload.knowledge_base_id,
            allow_high_risk=payload.allow_high_risk_tools,
            user_id=user.user_id,
        )
        return AgentRunResponse(**res)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agents/tools", response_model=list[ToolDeclaration])
async def list_tools(
    user: UserSession = Depends(get_current_user),
):
    tools = AgentRuntimeService.list_tools()
    return [
        ToolDeclaration(
            name=t["name"],
            description=t["description"],
            risk=t["risk"],
            required_permissions=t["permissions"],
        )
        for t in tools
    ]
