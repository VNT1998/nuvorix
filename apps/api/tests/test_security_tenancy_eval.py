import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from apps.api.app.core.config import settings
from apps.api.app.core.security import create_access_token
from apps.api.app.db.session import AsyncSessionLocal
from apps.api.app.main import app
from apps.api.app.models.entities import KnowledgeChunk


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_production_auth_mode_rejection_and_token_acceptance(client: AsyncClient):
    original_mode = settings.AUTH_MODE
    try:
        settings.AUTH_MODE = "production"

        # 1. Unauthenticated request in production mode -> 401 Unauthorized
        res_no_auth = await client.get("/api/v1/projects")
        assert res_no_auth.status_code == 401
        assert "Authentication credentials required" in res_no_auth.json()["detail"]

        # 2. Invalid bearer token in production mode -> 401 Unauthorized
        res_bad_token = await client.get(
            "/api/v1/projects",
            headers={"Authorization": "Bearer invalid.token.payload"},
        )
        assert res_bad_token.status_code == 401

        # 3. Valid signed token in production mode -> 200 OK
        token = create_access_token(
            user_id="usr-test-verified",
            organization_id=settings.DEFAULT_ORG_ID,
            role="admin",
        )
        res_valid = await client.get(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_valid.status_code == 200
        assert isinstance(res_valid.json(), list)
    finally:
        settings.AUTH_MODE = original_mode


@pytest.mark.asyncio
async def test_rbac_server_side_enforcement(client: AsyncClient):
    # Fetch existing workload
    res_ws = await client.get("/api/v1/workloads")
    assert res_ws.status_code == 200
    workload = res_ws.json()[0]
    workload_id = workload["id"]

    # 1. Viewer role attempting deployment creation -> 403 Forbidden
    res_viewer_dep = await client.post(
        f"/api/v1/workloads/{workload_id}/deployments",
        json={"version": "v1.0.0", "environment": "staging", "strategy": "direct"},
        headers={"X-User-Role": "viewer"},
    )
    assert res_viewer_dep.status_code == 403
    assert "lacks required permission: 'deployments:create'" in res_viewer_dep.json()["detail"]

    # 2. Viewer role attempting project creation -> 403 Forbidden
    res_viewer_proj = await client.post(
        "/api/v1/projects",
        json={"name": "Disallowed Project"},
        headers={"X-User-Role": "viewer"},
    )
    assert res_viewer_proj.status_code == 403
    assert "lacks required permission: 'projects:create'" in res_viewer_proj.json()["detail"]

    # 3. Developer role attempting rollback -> 403 Forbidden
    res_dev_rb = await client.post(
        "/api/v1/deployments/dep-fake-id/rollback",
        headers={"X-User-Role": "developer"},
    )
    assert res_dev_rb.status_code == 403
    assert "lacks required permission: 'deployments:rollback'" in res_dev_rb.json()["detail"]

    # 4. Platform engineer role attempting deployment creation -> succeeds (201)
    res_pe_dep = await client.post(
        f"/api/v1/workloads/{workload_id}/deployments",
        json={"version": "v1.9.9", "environment": "staging", "strategy": "direct"},
        headers={"X-User-Role": "platform_engineer"},
    )
    assert res_pe_dep.status_code == 201
    assert res_pe_dep.json()["version"] == "v1.9.9"


@pytest.mark.asyncio
async def test_high_risk_tool_permission_gate(client: AsyncClient):
    res_ws = await client.get("/api/v1/workloads")
    workload_id = res_ws.json()[0]["id"]

    # Developer role attempting high-risk tool execution -> 403 Forbidden
    res_dev = await client.post(
        f"/api/v1/workloads/{workload_id}/agents/run",
        json={
            "prompt": "Execute emergency circuit breaker",
            "allow_high_risk_tools": True,
        },
        headers={"X-User-Role": "developer"},
    )
    assert res_dev.status_code == 403
    assert "lacks required permission: 'agents:tools:execute_high_risk'" in res_dev.json()["detail"]

    # Platform engineer attempting high-risk tool execution -> permitted (200)
    res_pe = await client.post(
        f"/api/v1/workloads/{workload_id}/agents/run",
        json={
            "prompt": "Execute emergency circuit breaker",
            "allow_high_risk_tools": True,
        },
        headers={"X-User-Role": "platform_engineer"},
    )
    assert res_pe.status_code == 200


@pytest.mark.asyncio
async def test_multi_tenant_isolation(client: AsyncClient):
    org_a = "org-tenant-alpha"
    org_b = "org-tenant-beta"

    # 1. Tenant A creates a Project
    res_proj_a = await client.post(
        "/api/v1/projects",
        json={"name": "Alpha Confidential Project", "description": "Isolated to Alpha"},
        headers={"X-Org-Id": org_a, "X-User-Role": "admin"},
    )
    assert res_proj_a.status_code == 201
    proj_a_id = res_proj_a.json()["id"]

    # Tenant A creates a Workload in that project
    res_wl_a = await client.post(
        f"/api/v1/projects/{proj_a_id}/workloads",
        json={"name": "Alpha Workload", "type": "rag"},
        headers={"X-Org-Id": org_a, "X-User-Role": "admin"},
    )
    assert res_wl_a.status_code == 201
    wl_a_id = res_wl_a.json()["id"]

    # 2. Tenant B lists projects -> Project A MUST NOT appear
    res_list_b = await client.get(
        "/api/v1/projects",
        headers={"X-Org-Id": org_b, "X-User-Role": "admin"},
    )
    assert res_list_b.status_code == 200
    b_project_ids = [p["id"] for p in res_list_b.json()]
    assert proj_a_id not in b_project_ids

    # 3. Tenant B tries to fetch Project A directly by ID -> 404 Not Found
    res_get_a_by_b = await client.get(
        f"/api/v1/projects/{proj_a_id}",
        headers={"X-Org-Id": org_b, "X-User-Role": "admin"},
    )
    assert res_get_a_by_b.status_code == 404

    # 4. Tenant B tries to inject workload into Project A -> 404 Not Found
    res_cross_inject = await client.post(
        f"/api/v1/projects/{proj_a_id}/workloads",
        json={"name": "Injected Workload", "type": "rag"},
        headers={"X-Org-Id": org_b, "X-User-Role": "admin"},
    )
    assert res_cross_inject.status_code == 404

    # 5. Tenant B tries to access Workload A -> 404 Not Found
    res_get_wl_by_b = await client.get(
        f"/api/v1/workloads/{wl_a_id}",
        headers={"X-Org-Id": org_b, "X-User-Role": "admin"},
    )
    assert res_get_wl_by_b.status_code == 404

    # 6. Audit Trail Isolation
    res_audit_b = await client.get(
        "/api/v1/audit-events",
        headers={"X-Org-Id": org_b, "X-User-Role": "admin"},
    )
    assert res_audit_b.status_code == 200
    b_audits = res_audit_b.json()
    assert not any(a.get("resource_id") == proj_a_id for a in b_audits)


@pytest.mark.asyncio
async def test_fastembed_dense_vector_embeddings():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(KnowledgeChunk).limit(5))
        chunks = res.scalars().all()
        assert len(chunks) > 0
        for chunk in chunks:
            # Check 384-dimensional vector
            embedding = chunk.embedding_json or chunk.embedding
            assert embedding is not None
            assert len(embedding) == 384
            # Verify coordinates are non-trivial floats
            assert all(isinstance(val, (float, int)) for val in embedding[:10])
            magnitude = sum(x * x for x in embedding)
            assert magnitude > 0.0


@pytest.mark.asyncio
async def test_mlflow_model_registry_integration(client: AsyncClient):
    # Retrieve registered models from MLflow
    res_reg = await client.get("/api/v1/mlflow/registered-models")
    assert res_reg.status_code == 200
    reg_data = res_reg.json()
    assert "registered_models" in reg_data
    assert "count" in reg_data
