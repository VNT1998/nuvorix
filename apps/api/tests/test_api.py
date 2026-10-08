import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.app.db.session import AsyncSessionLocal, init_db
from apps.api.app.main import app
from apps.api.app.seed import seed_demo_data


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_demo_data(session)


@pytest.mark.asyncio
async def test_health_and_ready():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["database"] == "healthy"

        # 2. Ready check
        resp_ready = await client.get("/ready")
        assert resp_ready.status_code == 200
        assert resp_ready.json()["ready"] is True

        # 3. Metrics check
        resp_metrics = await client.get("/metrics")
        assert resp_metrics.status_code == 200
        assert "nuvorix_http_requests_total" in resp_metrics.text


@pytest.mark.asyncio
async def test_projects_and_workloads_crud():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create project
        resp = await client.post(
            "/api/v1/projects",
            json={"name": "Test Platform Project", "description": "Automated verification test"},
        )
        assert resp.status_code == 201
        proj_data = resp.json()
        proj_id = proj_data["id"]
        assert proj_data["name"] == "Test Platform Project"

        # List projects
        resp_list = await client.get("/api/v1/projects")
        assert resp_list.status_code == 200
        assert any(p["id"] == proj_id for p in resp_list.json())

        # Create workload
        resp_w = await client.post(
            f"/api/v1/projects/{proj_id}/workloads",
            json={"name": "Test Regressor Workload", "type": "ml_model"},
        )
        assert resp_w.status_code == 201
        w_data = resp_w.json()
        w_id = w_data["id"]
        assert w_data["type"] == "ml_model"

        # Get workload
        resp_gw = await client.get(f"/api/v1/workloads/{w_id}")
        assert resp_gw.status_code == 200
        assert resp_gw.json()["name"] == "Test Regressor Workload"


@pytest.mark.asyncio
async def test_ml_model_training_and_promotion():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Fetch seeded ml workload
        res_ws = await client.get("/api/v1/workloads")
        ml_workload = next(w for w in res_ws.json() if w["type"] == "ml_model")

        # Train model
        train_resp = await client.post(
            f"/api/v1/workloads/{ml_workload['id']}/train",
            json={
                "model_name": "performance_regressor",
                "hyperparameters": {"alpha": 0.5, "max_iter": 500},
            },
        )
        assert train_resp.status_code == 200
        t_data = train_resp.json()
        assert "rmse" in t_data["metrics"]
        assert "r2_score" in t_data["metrics"]
        assert t_data["metrics"]["rmse"] > 0
        assert t_data["status"] == "registered"

        # Promote to staging
        promote_resp = await client.post(
            f"/api/v1/model-versions/{t_data['version_id']}/promote",
            json={"target_environment": "staging"},
        )
        assert promote_resp.status_code == 200
        assert promote_resp.json()["status"] == "staging"


@pytest.mark.asyncio
async def test_rag_ingest_and_retrieval():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List knowledge bases
        res_kb = await client.get("/api/v1/knowledge-bases")
        kb = res_kb.json()[0]

        # Ingest new document
        doc_resp = await client.post(
            f"/api/v1/knowledge-bases/{kb['id']}/documents",
            json={
                "title": "Automated Deployment Safety",
                "content": "Automated deployment safety requires policy checks, health verification, and instant rollback capability in case of degradation.",
                "source_uri": "docs/safety.md",
            },
        )
        assert doc_resp.status_code == 201
        assert doc_resp.json()["chunk_count"] >= 1

        # Query knowledge base
        q_resp = await client.post(
            f"/api/v1/knowledge-bases/{kb['id']}/query",
            json={"query": "What is required for deployment safety and rollback?", "top_k": 2},
        )
        assert q_resp.status_code == 200
        q_data = q_resp.json()
        assert len(q_data["results"]) > 0
        assert q_data["results"][0]["score"] > 0.0
        assert "score" in q_data["results"][0]
        assert "text" in q_data["results"][0]


@pytest.mark.asyncio
async def test_agent_execution_with_tools():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check tools list
        tools_resp = await client.get("/api/v1/agents/tools")
        assert tools_resp.status_code == 200
        tools = tools_resp.json()
        tool_names = [t["name"] for t in tools]
        assert "knowledge_search" in tool_names
        assert "project_deployment_status" in tool_names
        assert "diagnostic_check" in tool_names

        # Run agent query triggering knowledge search tool
        res_ws = await client.get("/api/v1/workloads")
        agent_w = next(w for w in res_ws.json() if w["type"] == "agent")

        agent_resp = await client.post(
            f"/api/v1/workloads/{agent_w['id']}/agents/run",
            json={"prompt": "Search the knowledge base for platform invariants and architecture."},
        )
        assert agent_resp.status_code == 200
        a_data = agent_resp.json()
        assert len(a_data["steps"]) >= 3
        assert "knowledge_search" in a_data["tools_used"]
        assert a_data["estimated_cost"] > 0


@pytest.mark.asyncio
async def test_evaluation_quality_gate_allow_and_block():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_ws = await client.get("/api/v1/workloads")
        agent_w = next(w for w in res_ws.json() if w["type"] == "agent")

        # 1. Good candidate -> should ALLOW
        allow_resp = await client.post(
            f"/api/v1/workloads/{agent_w['id']}/evaluations",
            json={"version": "v1.2.5-stable"},
        )
        assert allow_resp.status_code == 200
        assert allow_resp.json()["decision"] == "ALLOW"
        assert allow_resp.json()["passed"] is True

        # 2. Bad candidate -> should BLOCK with reasons
        block_resp = await client.post(
            f"/api/v1/workloads/{agent_w['id']}/evaluations",
            json={"version": "v1.3.0-bad-canary"},
        )
        assert block_resp.status_code == 200
        b_data = block_resp.json()
        assert b_data["decision"] == "BLOCK"
        assert b_data["passed"] is False
        assert len(b_data["reasons"]) > 0


@pytest.mark.asyncio
async def test_deployment_and_rollback():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_ws = await client.get("/api/v1/workloads")
        agent_w = next(w for w in res_ws.json() if w["type"] == "agent")

        # Deploy v1.2.0 to staging
        dep_resp = await client.post(
            f"/api/v1/workloads/{agent_w['id']}/deployments",
            json={"version": "v1.2.0", "environment": "staging", "strategy": "blue_green"},
        )
        assert dep_resp.status_code == 201
        dep_id = dep_resp.json()["id"]
        assert dep_id is not None

        # Deploy v1.2.5 to staging
        dep2_resp = await client.post(
            f"/api/v1/workloads/{agent_w['id']}/deployments",
            json={"version": "v1.2.5", "environment": "staging", "strategy": "blue_green"},
        )
        assert dep2_resp.status_code == 201
        dep2_id = dep2_resp.json()["id"]

        # Rollback v1.2.5 back to v1.2.0
        rb_resp = await client.post(f"/api/v1/deployments/{dep2_id}/rollback")
        assert rb_resp.status_code == 200
        rb_data = rb_resp.json()
        assert rb_data["active_version"] == "v1.2.0"
        assert rb_data["status"] == "active"


@pytest.mark.asyncio
async def test_incident_remediation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        incidents = await client.get("/api/v1/incidents")
        assert incidents.status_code == 200
        inc_list = incidents.json()
        assert len(inc_list) > 0
        inc = inc_list[0]
        assert inc["status"] in ["open", "resolved"]

        # Remediate incident
        rem_resp = await client.post(f"/api/v1/incidents/{inc['id']}/remediate", json={"action": "rollback"})
        assert rem_resp.status_code == 200
        assert rem_resp.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_gateway_chat_and_finops():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_ws = await client.get("/api/v1/workloads")
        w = res_ws.json()[0]

        chat_resp = await client.post(
            f"/api/v1/workloads/{w['id']}/gateway/chat",
            json={"prompt": "Explain platform latency budget enforcement."},
        )
        assert chat_resp.status_code == 200
        c_data = chat_resp.json()
        assert c_data["estimated_cost"] > 0
        assert "response" in c_data

        costs_resp = await client.get("/api/v1/costs")
        assert costs_resp.status_code == 200
        cost_data = costs_resp.json()
        assert cost_data["total_requests"] > 0
        assert cost_data["total_cost"] > 0
