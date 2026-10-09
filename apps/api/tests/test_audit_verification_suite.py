import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.app.core.config import Settings, settings
from apps.api.app.core.security import (
    ExecutionContext,
    UserSession,
    check_permission,
    create_access_token,
)
from apps.api.app.db.session import AsyncSessionLocal
from apps.api.app.main import app
from apps.api.app.models.entities import (
    Deployment,
    EvaluationRun,
    Project,
    Workload,
)
from apps.api.app.services.agent_service import AgentRuntimeService
from apps.api.app.services.api_key_service import APIKeyService
from apps.api.app.services.deploy_service import DeploymentPlatformService
from apps.api.app.services.gateway_service import LLMGatewayService
from apps.api.app.services.rag_service import RAGPlatformService


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def test_production_config_validation_invariants():
    """Verify that Settings fail-fast in production if any security/infra setting is insecure."""
    # 1. ENVIRONMENT=production with AUTH_MODE=development must fail
    with pytest.raises(ValueError, match="requires AUTH_MODE='production'"):
        Settings(
            ENVIRONMENT="production",
            AUTH_MODE="development",
            AUTH_ENABLED=True,
            SECRET_KEY="a" * 32,
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
            MLFLOW_TRACKING_URI="http://mlflow-server:5000",
            CORS_ORIGINS=["https://app.nuvorix.io"],
        )

    # 2. ENVIRONMENT=production with AUTH_ENABLED=False must fail
    with pytest.raises(ValueError, match="requires AUTH_ENABLED=True"):
        Settings(
            ENVIRONMENT="production",
            AUTH_MODE="production",
            AUTH_ENABLED=False,
            SECRET_KEY="a" * 32,
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
            MLFLOW_TRACKING_URI="http://mlflow-server:5000",
            CORS_ORIGINS=["https://app.nuvorix.io"],
        )

    # 3. Weak / default SECRET_KEY in production must fail
    with pytest.raises(ValueError, match="requires an externally configured"):
        Settings(
            ENVIRONMENT="production",
            AUTH_MODE="production",
            AUTH_ENABLED=True,
            SECRET_KEY="short-secret",
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
            MLFLOW_TRACKING_URI="http://mlflow-server:5000",
            CORS_ORIGINS=["https://app.nuvorix.io"],
        )

    # 4. SQLite database in production must fail
    with pytest.raises(ValueError, match="requires PostgreSQL database"):
        Settings(
            ENVIRONMENT="production",
            AUTH_MODE="production",
            AUTH_ENABLED=True,
            SECRET_KEY="a" * 32,
            DATABASE_URL="sqlite+aiosqlite:///./test.db",
            MLFLOW_TRACKING_URI="http://mlflow-server:5000",
            CORS_ORIGINS=["https://app.nuvorix.io"],
        )

    # 5. Local SQLite / local MLflow in production must fail
    with pytest.raises(ValueError, match="requires an external MLflow tracking URI"):
        Settings(
            ENVIRONMENT="production",
            AUTH_MODE="production",
            AUTH_ENABLED=True,
            SECRET_KEY="a" * 32,
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
            MLFLOW_TRACKING_URI="sqlite:///mlflow.db",
            CORS_ORIGINS=["https://app.nuvorix.io"],
        )

    # 6. Localhost CORS origins in production must fail
    with pytest.raises(ValueError, match="requires explicit non-localhost CORS_ORIGINS"):
        Settings(
            ENVIRONMENT="production",
            AUTH_MODE="production",
            AUTH_ENABLED=True,
            SECRET_KEY="a" * 32,
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
            MLFLOW_TRACKING_URI="http://mlflow-server:5000",
            CORS_ORIGINS=["http://localhost:3000"],
        )

    # 7. Valid production configuration succeeds
    prod_valid = Settings(
        ENVIRONMENT="production",
        AUTH_MODE="production",
        AUTH_ENABLED=True,
        SECRET_KEY="c" * 36,
        DATABASE_URL="postgresql+asyncpg://user:pass@postgres-host:5432/nuvorix",
        MLFLOW_TRACKING_URI="http://mlflow-host:5000",
        CORS_ORIGINS=["https://console.nuvorix.io"],
    )
    assert prod_valid.ENVIRONMENT == "production"


@pytest.mark.asyncio
async def test_production_deployment_release_gate_rules(client: AsyncClient):
    """Verify production deployments strictly enforce completed ALLOW evaluation and break-glass rules."""
    unique_suffix = uuid.uuid4().hex[:6]
    org_id = f"org-release-gate-{unique_suffix}"
    admin_token = create_access_token(
        user_id="usr-gate-admin",
        organization_id=org_id,
        role="admin",
    )
    headers = {"Authorization": f"Bearer {admin_token}"}

    async with AsyncSessionLocal() as session:
        proj = Project(id=f"proj-gate-{unique_suffix}", organization_id=org_id, name="Gate Project")
        session.add(proj)
        await session.flush()

        workload = Workload(
            id=f"wl-gate-{unique_suffix}",
            project_id=proj.id,
            name="Gate Workload",
            type="ml_model",
        )
        session.add(workload)
        await session.commit()

    cand_ver_missing = f"v1.0.0-{unique_suffix}"

    # 1. Missing evaluation: production deployment BLOCKED
    res_missing = await client.post(
        f"/api/v1/workloads/{workload.id}/deployments",
        headers=headers,
        json={"version": cand_ver_missing, "environment": "production"},
    )
    assert res_missing.status_code == 400
    assert "no evaluation exists" in res_missing.json()["detail"]

    # 2. Incomplete evaluation (status='running'): production deployment BLOCKED
    cand_ver_running = f"v1.0.1-{unique_suffix}"
    async with AsyncSessionLocal() as session:
        eval_running = EvaluationRun(
            workload_id=workload.id,
            version=cand_ver_running,
            status="running",
            passed=False,
            decision="ALLOW",  # decision premature before completion
        )
        session.add(eval_running)
        await session.commit()

    res_running = await client.post(
        f"/api/v1/workloads/{workload.id}/deployments",
        headers=headers,
        json={"version": cand_ver_running, "environment": "production"},
    )
    assert res_running.status_code == 400
    assert "evaluation status is 'running'" in res_running.json()["detail"]

    # 3. Failed/BLOCK evaluation: production deployment BLOCKED
    cand_ver_blocked = f"v1.0.2-{unique_suffix}"
    async with AsyncSessionLocal() as session:
        eval_blocked = EvaluationRun(
            workload_id=workload.id,
            version=cand_ver_blocked,
            status="completed",
            passed=False,
            decision="BLOCK",
            reasons_json=["RMSE exceeded budget threshold"],
        )
        session.add(eval_blocked)
        await session.commit()

    res_blocked = await client.post(
        f"/api/v1/workloads/{workload.id}/deployments",
        headers=headers,
        json={"version": cand_ver_blocked, "environment": "production"},
    )
    assert res_blocked.status_code == 400
    assert "Production deployment gate BLOCKED" in res_blocked.json()["detail"]

    # 4. Completed ALLOW evaluation: production deployment SUCCEEDS
    cand_ver_allowed = f"v1.0.3-{unique_suffix}"
    async with AsyncSessionLocal() as session:
        eval_allowed = EvaluationRun(
            workload_id=workload.id,
            version=cand_ver_allowed,
            status="completed",
            passed=True,
            decision="ALLOW",
            reasons_json=[],
        )
        session.add(eval_allowed)
        await session.commit()

    res_allowed = await client.post(
        f"/api/v1/workloads/{workload.id}/deployments",
        headers=headers,
        json={"version": cand_ver_allowed, "environment": "production"},
    )
    assert res_allowed.status_code == 201
    assert res_allowed.json()["status"] == "active"
    assert res_allowed.json()["environment"] == "production"

    # 5. Break-glass bypass: requires deployments:bypass_gate permission and reason
    dev_token = create_access_token(
        user_id="usr-gate-dev",
        organization_id=org_id,
        role="developer",  # lacking deployments:bypass_gate
    )
    res_bypass_forbidden = await client.post(
        f"/api/v1/workloads/{workload.id}/deployments",
        headers={"Authorization": f"Bearer {dev_token}"},
        json={
            "version": cand_ver_blocked,
            "environment": "production",
            "bypass_gate": True,
            "bypass_reason": "Emergency fix for outage INC-1234",
        },
    )
    assert res_bypass_forbidden.status_code == 403

    # Missing bypass reason rejected with 400
    res_bypass_no_reason = await client.post(
        f"/api/v1/workloads/{workload.id}/deployments",
        headers=headers,
        json={
            "version": cand_ver_blocked,
            "environment": "production",
            "bypass_gate": True,
            "bypass_reason": "",
        },
    )
    assert res_bypass_no_reason.status_code == 400

    # Privileged break-glass with reason succeeds and creates audit log
    res_bypass_ok = await client.post(
        f"/api/v1/workloads/{workload.id}/deployments",
        headers=headers,
        json={
            "version": cand_ver_blocked,
            "environment": "production",
            "bypass_gate": True,
            "bypass_reason": "Executive approved hotfix for INC-9999",
        },
    )
    assert res_bypass_ok.status_code == 201


@pytest.mark.asyncio
async def test_idempotency_cross_tenant_isolation(client: AsyncClient):
    """Verify identical Idempotency-Key in two different organizations cannot cross-contaminate."""
    suffix = uuid.uuid4().hex[:6]
    org_a = f"org-tenant-a-{suffix}"
    org_b = f"org-tenant-b-{suffix}"

    token_a = create_access_token(user_id="usr-a", organization_id=org_a, role="admin")
    token_b = create_access_token(user_id="usr-b", organization_id=org_b, role="admin")

    async with AsyncSessionLocal() as session:
        proj_a = Project(id=f"proj-a-{suffix}", organization_id=org_a, name="Project A")
        proj_b = Project(id=f"proj-b-{suffix}", organization_id=org_b, name="Project B")
        session.add_all([proj_a, proj_b])
        await session.flush()

        wl_a = Workload(id=f"wl-a-{suffix}", project_id=proj_a.id, name="Workload A", type="ml_model")
        wl_b = Workload(id=f"wl-b-{suffix}", project_id=proj_b.id, name="Workload B", type="ml_model")
        session.add_all([wl_a, wl_b])
        await session.commit()

    shared_idem_key = f"shared-idem-key-{suffix}"

    # Org A initiates deployment with shared_idem_key
    res_a = await client.post(
        f"/api/v1/workloads/{wl_a.id}/deployments",
        headers={"Authorization": f"Bearer {token_a}", "Idempotency-Key": shared_idem_key},
        json={"version": "v1.0.0-a", "environment": "staging"},
    )
    assert res_a.status_code == 201
    dep_a_id = res_a.json()["id"]

    # Org B uses the exact same Idempotency-Key
    res_b = await client.post(
        f"/api/v1/workloads/{wl_b.id}/deployments",
        headers={"Authorization": f"Bearer {token_b}", "Idempotency-Key": shared_idem_key},
        json={"version": "v1.0.0-b", "environment": "staging"},
    )
    assert res_b.status_code == 201
    dep_b_id = res_b.json()["id"]

    # Org B must receive its OWN deployment, NOT Org A's deployment
    assert dep_b_id != dep_a_id
    assert res_b.json()["workload_id"] == wl_b.id
    assert res_b.json()["version"] == "v1.0.0-b"


@pytest.mark.asyncio
async def test_service_tenant_context_mandatory():
    """Verify service methods enforce tenant context and reject None/missing org context."""
    async with AsyncSessionLocal() as session:
        # 1. DeploymentPlatformService.create_deployment
        with pytest.raises(ValueError, match="Mandatory tenant context missing"):
            await DeploymentPlatformService.create_deployment(
                db=session,
                workload_id="any-wl",
                version="v1.0.0",
                org_id=None,
                user_id="usr-test",
            )

        # 2. DeploymentPlatformService.rollback_deployment
        with pytest.raises(ValueError, match="Mandatory tenant context missing"):
            await DeploymentPlatformService.rollback_deployment(
                db=session,
                deployment_id="any-dep",
                org_id=None,
                user_id="usr-test",
            )

        # 3. RAGPlatformService.ingest_document
        with pytest.raises(ValueError, match="Mandatory tenant context missing"):
            await RAGPlatformService.ingest_document(
                db=session,
                knowledge_base_id="any-kb",
                title="Doc",
                content="Text",
                org_id=None,
                user_id="usr-test",
            )

        # 4. RAGPlatformService.query_knowledge_base
        with pytest.raises(ValueError, match="Mandatory tenant context missing"):
            await RAGPlatformService.query_knowledge_base(
                db=session,
                knowledge_base_id="any-kb",
                query="Text",
                org_id=None,
            )

        # 5. AgentRuntimeService.execute_tool
        with pytest.raises(ValueError, match="Mandatory context missing"):
            await AgentRuntimeService.execute_tool(
                tool_name="project_deployment_status",
                tool_input={},
                db=session,
                context=None,
            )

        # 6. AgentRuntimeService.run_agent_workflow
        with pytest.raises(ValueError, match="Mandatory context missing"):
            await AgentRuntimeService.run_agent_workflow(
                db=session,
                workload_id="any-wl",
                prompt="status",
                context=None,
            )


@pytest.mark.asyncio
async def test_circuit_breaker_explicit_target_and_intent_routing():
    """Verify prompt router never manufactures confirmed=True and circuit breaker requires explicit target."""
    # 1. Natural language intent routing does NOT manufacture confirmed=True
    tool, params = AgentRuntimeService.route_prompt_to_tool("Emergency halt and trip circuit breaker now!")
    assert tool == "emergency_circuit_breaker"
    assert params.get("confirmed") is False

    suffix = uuid.uuid4().hex[:6]
    org_id = f"org-cb-{suffix}"
    admin_ctx = ExecutionContext(
        user_id="usr-cb-admin",
        organization_id=org_id,
        role="admin",
        permissions={"agents:tools:execute_high_risk", "deployments:rollback", "workloads:read"},
        source="agent",
    )

    async with AsyncSessionLocal() as session:
        # 2. Tool execution without deployment_id is rejected (no fallback to latest active)
        res_no_target = await AgentRuntimeService.execute_tool(
            tool_name="emergency_circuit_breaker",
            tool_input={"reason": "Testing no target"},
            db=session,
            context=admin_ctx,
            allow_high_risk=True,
            confirmed=True,
        )
        assert "error" in res_no_target
        assert "Missing required parameter 'deployment_id'" in res_no_target["error"]

        # 3. Target in different organization is rejected
        proj_other = Project(id=f"proj-other-{suffix}", organization_id="org-other", name="Other")
        session.add(proj_other)
        await session.flush()
        wl_other = Workload(id=f"wl-other-{suffix}", project_id=proj_other.id, name="Other WL", type="agent")
        session.add(wl_other)
        await session.flush()
        dep_other = Deployment(id=f"dep-other-{suffix}", workload_id=wl_other.id, version="v1.0.0", status="active")
        session.add(dep_other)
        await session.commit()

        res_wrong_tenant = await AgentRuntimeService.execute_tool(
            tool_name="emergency_circuit_breaker",
            tool_input={"deployment_id": dep_other.id, "reason": "Attack target"},
            db=session,
            context=admin_ctx,
            allow_high_risk=True,
            confirmed=True,
        )
        assert "error" in res_wrong_tenant
        assert "not found or unauthorized" in res_wrong_tenant["error"]


@pytest.mark.asyncio
async def test_api_key_scopes_explicit_semantics():
    """Verify explicit scope semantics: None inherits defaults, [] grants no permissions, invalid scope is rejected."""
    async with AsyncSessionLocal() as session:
        # 1. Invalid scope rejected at creation
        with pytest.raises(ValueError, match="Invalid scope 'invalid:scope:fake'"):
            await APIKeyService.create_api_key(
                db=session,
                organization_id="org-test",
                name="Bad Scope Key",
                scopes=["invalid:scope:fake"],
            )

        # 2. scopes=None inherits role permissions
        _key_unscoped, raw_unscoped = await APIKeyService.create_api_key(
            db=session,
            organization_id="org-test",
            name="Unscoped Key",
            role="developer",
            scopes=None,
        )
        _, claims_unscoped = await APIKeyService.authenticate_key(session, raw_unscoped)
        sess_unscoped = UserSession(
            user_id="key-1",
            organization_id="org-test",
            name="Key",
            email="key@test",
            role="developer",
            scopes=claims_unscoped["scopes"],
        )
        assert check_permission(sess_unscoped, "workloads:read") is True

        # 3. scopes=[] grants NO permissions (empty set)
        _key_empty, raw_empty = await APIKeyService.create_api_key(
            db=session,
            organization_id="org-test",
            name="Empty Scope Key",
            role="admin",  # even admin role!
            scopes=[],
        )
        _, claims_empty = await APIKeyService.authenticate_key(session, raw_empty)
        sess_empty = UserSession(
            user_id="key-2",
            organization_id="org-test",
            name="Key",
            email="key@test",
            role="admin",
            scopes=claims_empty["scopes"],
        )
        assert check_permission(sess_empty, "projects:read") is False
        assert check_permission(sess_empty, "deployments:create") is False


@pytest.mark.asyncio
async def test_llm_gateway_production_fail_closed():
    """Verify LLM Gateway in production does not silently fall back to local demo provider."""
    original_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        async with AsyncSessionLocal() as session:
            # Calling remote provider with unconfigured / failing endpoint in production fails fast
            with pytest.raises(ValueError, match="Fallback to deterministic local demo provider is disabled in production"):
                await LLMGatewayService.chat_completion(
                    db=session,
                    workload_id="wl-test",
                    prompt="Production prompt",
                    provider="openai",
                    model="gpt-4o",
                )
    finally:
        settings.ENVIRONMENT = original_env
