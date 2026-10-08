import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import UserSession, get_current_user
from apps.api.app.db.session import get_db
from apps.api.app.schemas.domain import (
    AgentRunRequest,
    AgentRunResponse,
    MCPCallToolRequest,
    MCPCallToolResponse,
    MCPContentItem,
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


@router.get("/agents/graph")
async def get_agent_graph(
    user: UserSession = Depends(get_current_user),
):
    """Returns the compiled LangGraph StateGraph topology and Mermaid diagram."""
    mermaid = AgentRuntimeService.get_workflow_mermaid()
    return {
        "engine": "langgraph",
        "nodes": ["planner", "tool_executor", "synthesizer"],
        "edges": [
            {"from": "__start__", "to": "planner"},
            {"from": "planner", "to": "tool_executor", "condition": "has_tool_call"},
            {"from": "planner", "to": "synthesizer", "condition": "direct_response"},
            {"from": "tool_executor", "to": "synthesizer"},
            {"from": "synthesizer", "to": "__end__"},
        ],
        "mermaid": mermaid,
    }


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
            input_schema=t.get("inputSchema", {}),
        )
        for t in tools
    ]


# --- Model Context Protocol (MCP) Standard Endpoints ---

@router.get("/mcp/tools")
async def mcp_list_tools(
    user: UserSession = Depends(get_current_user),
):
    """Standard MCP tools listing format."""
    tools = AgentRuntimeService.list_tools()
    return {
        "tools": [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t.get("inputSchema", {}),
            }
            for t in tools
        ]
    }


@router.post("/mcp/tools/call", response_model=MCPCallToolResponse)
async def mcp_call_tool(
    payload: MCPCallToolRequest,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Standard MCP tool call execution."""
    result = await AgentRuntimeService.execute_tool(
        tool_name=payload.name,
        tool_input=payload.arguments,
        db=db,
        allow_high_risk=payload.allow_high_risk,
    )
    is_error = "error" in result
    return MCPCallToolResponse(
        content=[MCPContentItem(type="text", text=json.dumps(result, indent=2))],
        isError=is_error,
    )


@router.post("/mcp/rpc")
async def mcp_json_rpc(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(get_current_user),
):
    """Standard MCP JSON-RPC 2.0 protocol endpoint."""
    body = await request.json()
    req_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        tools = AgentRuntimeService.list_tools()
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": t["name"],
                        "description": t["description"],
                        "inputSchema": t.get("inputSchema", {}),
                    }
                    for t in tools
                ]
            },
        }

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        result = await AgentRuntimeService.execute_tool(
            tool_name=tool_name,
            tool_input=arguments,
            db=db,
            allow_high_risk=bool(params.get("allow_high_risk", False)),
        )
        is_error = "error" in result
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result)}],
                "isError": is_error,
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method '{method}' not found"},
    }

