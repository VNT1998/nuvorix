import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.app.core.security import ExecutionContext
from apps.api.app.db.session import AsyncSessionLocal
from apps.api.app.main import app
from apps.api.app.models.entities import KnowledgeBase, Project
from apps.api.app.services.agent_service import AgentRuntimeService
from apps.api.app.services.tool_authorization import authorize_tool


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_tool_authorization_permission_enforcement():
    """Verify tool authorization gate strictly enforces permissions at the service boundary."""
    # 1. High risk tool without high_risk permission -> PermissionError
    viewer_ctx = ExecutionContext(
        user_id="usr-viewer",
        organization_id="org-alpha",
        role="viewer",
        permissions={"workloads:read", "knowledge:query"},
        source="agent",
    )

    with pytest.raises(PermissionError, match="lacks required permissions"):
        authorize_tool(
            context=viewer_ctx,
            tool_name="emergency_circuit_breaker",
            allow_high_risk=True,
            confirmed=True,
        )

    # 2. High risk tool without allow_high_risk flag -> PermissionError
    admin_ctx = ExecutionContext(
        user_id="usr-admin",
        organization_id="org-alpha",
        role="admin",
        permissions={"agents:tools:execute_high_risk", "deployments:rollback", "workloads:read"},
        source="agent",
    )

    with pytest.raises(PermissionError, match="allow_high_risk flag was not set"):
        authorize_tool(
            context=admin_ctx,
            tool_name="emergency_circuit_breaker",
            allow_high_risk=False,
            confirmed=True,
        )

    # 3. High risk tool without explicit confirmation -> PermissionError
    with pytest.raises(PermissionError, match="requires explicit confirmation"):
        authorize_tool(
            context=admin_ctx,
            tool_name="emergency_circuit_breaker",
            allow_high_risk=True,
            confirmed=False,
        )

    # 4. Valid authorization with confirmed=True and allow_high_risk=True -> succeeds
    tool_meta = authorize_tool(
        context=admin_ctx,
        tool_name="emergency_circuit_breaker",
        allow_high_risk=True,
        confirmed=True,
    )
    assert tool_meta["risk"] == "high"


@pytest.mark.asyncio
async def test_multi_tenant_tool_data_isolation():
    """Verify tools cannot retrieve cross-tenant data even when explicitly queried."""
    unique_suffix = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as session:
        # Create Project in Tenant Beta
        proj_beta = Project(
            id=f"proj-tenant-beta-{unique_suffix}",
            organization_id=f"org-tenant-beta-{unique_suffix}",
            name="Beta Isolated Workspace",
        )
        session.add(proj_beta)
        await session.flush()

        kb_beta = KnowledgeBase(
            id=f"kb-beta-{unique_suffix}",
            project_id=proj_beta.id,
            name="Beta Trade Secrets",
            description="Highly confidential intellectual property",
        )
        session.add(kb_beta)
        await session.commit()

        # Caller in Tenant Alpha attempts to query Tenant Beta's KB
        alpha_ctx = ExecutionContext(
            user_id="usr-alpha",
            organization_id="org-tenant-alpha",
            role="admin",
            permissions={"workloads:read", "knowledge:query", "agents:tools:execute_high_risk"},
            source="agent",
        )

        res = await AgentRuntimeService.execute_tool(
            tool_name="knowledge_search",
            tool_input={"query": "trade secrets", "knowledge_base_id": kb_beta.id},
            db=session,
            context=alpha_ctx,
        )

        # Must fail or return empty/unauthorized without leaking Beta data
        assert "error" in res or res.get("results") == []


@pytest.mark.asyncio
async def test_mcp_cross_tenant_isolation(client: AsyncClient):
    """Verify MCP protocol rejects cross-tenant tool execution attempts with 403 or 404."""
    # Tenant Alpha caller attempts MCP execution targeting a non-owned project
    mcp_resp = await client.post(
        "/api/v1/agents/mcp/tools/call",
        json={
            "name": "project_deployment_status",
            "arguments": {"project_id": "proj-nonexistent-or-other-org"},
        },
        headers={"X-User-Role": "developer", "X-Org-Id": "org-tenant-alpha"},
    )
    # The server strictly denies access (404 Not Found prevents tenant information leakage)
    assert mcp_resp.status_code in (403, 404)
