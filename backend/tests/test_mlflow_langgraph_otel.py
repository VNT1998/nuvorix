import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.core.telemetry import get_recent_spans
from backend.app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers={"X-User-Role": "admin"}
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_opentelemetry_spans_recorded(client: AsyncClient):
    # Make a few API requests to generate spans
    res = await client.get("/health")
    assert res.status_code == 200

    res = await client.get("/ready")
    assert res.status_code == 200

    # Query telemetry traces endpoint
    res_traces = await client.get("/telemetry/traces")
    assert res_traces.status_code == 200
    data = res_traces.json()
    assert "spans" in data
    assert data["count"] > 0

    # Check span attributes
    spans = get_recent_spans()
    span_names = [s["name"] for s in spans]
    assert any("GET /health" in name or "GET /ready" in name for name in span_names)


@pytest.mark.asyncio
async def test_langgraph_agent_and_topology(client: AsyncClient):
    # Test LangGraph topology endpoint
    res_graph = await client.get("/api/v1/agents/graph")
    assert res_graph.status_code == 200
    graph_data = res_graph.json()
    assert graph_data["engine"] == "langgraph"
    assert "planner" in graph_data["nodes"]
    assert "tool_executor" in graph_data["nodes"]
    assert "synthesizer" in graph_data["nodes"]
    assert "graph TD" in graph_data["mermaid"]

    # Test LangGraph execution with knowledge search intent
    res_workloads = await client.get("/api/v1/workloads")
    workloads = res_workloads.json()
    workload_id = workloads[0]["id"]

    run_payload = {
        "prompt": "How does the search architecture and RAG work?",
        "allow_high_risk_tools": False,
    }
    res_run = await client.post(f"/api/v1/workloads/{workload_id}/agents/run", json=run_payload)
    assert res_run.status_code == 200
    run_data = res_run.json()
    assert run_data["workload_id"] == workload_id
    assert len(run_data["steps"]) >= 3
    assert any(step["stage"] == "planner" for step in run_data["steps"])
    assert any(step["stage"] == "response" for step in run_data["steps"])
    assert "knowledge_search" in run_data["tools_used"]


@pytest.mark.asyncio
async def test_mcp_standard_protocol(client: AsyncClient):
    # 1. MCP Tools Listing
    res_mcp_tools = await client.get("/api/v1/mcp/tools")
    assert res_mcp_tools.status_code == 200
    mcp_tools = res_mcp_tools.json()
    assert "tools" in mcp_tools
    tool_names = [t["name"] for t in mcp_tools["tools"]]
    assert "knowledge_search" in tool_names
    assert "diagnostic_check" in tool_names
    assert "emergency_circuit_breaker" in tool_names

    # Check MCP inputSchema
    diag_tool = next(t for t in mcp_tools["tools"] if t["name"] == "diagnostic_check")
    assert "inputSchema" in diag_tool

    # 2. MCP Tool Execution Call
    res_call = await client.post(
        "/api/v1/mcp/tools/call",
        json={"name": "diagnostic_check", "arguments": {}},
    )
    assert res_call.status_code == 200
    call_data = res_call.json()
    assert call_data["isError"] is False
    assert len(call_data["content"]) > 0
    assert "healthy" in call_data["content"][0]["text"]

    # 3. MCP JSON-RPC 2.0
    # Ping
    res_rpc_ping = await client.post(
        "/api/v1/mcp/rpc",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}},
    )
    assert res_rpc_ping.status_code == 200
    assert res_rpc_ping.json()["result"] == {}

    # Tools list via RPC
    res_rpc_list = await client.post(
        "/api/v1/mcp/rpc",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )
    assert res_rpc_list.status_code == 200
    assert "tools" in res_rpc_list.json()["result"]


@pytest.mark.asyncio
async def test_mlflow_training_and_run_registration(client: AsyncClient):
    res_workloads = await client.get("/api/v1/workloads")
    workload = res_workloads.json()[0]
    workload_id = workload["id"]

    train_payload = {
        "model_name": "performance_regressor",
        "hyperparameters": {"alpha": 0.5, "max_iter": 500},
    }
    res_train = await client.post(f"/api/v1/workloads/{workload_id}/train", json=train_payload)
    assert res_train.status_code == 200
    data = res_train.json()
    assert data["model_id"] is not None
    assert "rmse" in data["metrics"]
    assert data["status"] == "registered"

    # Query MLflow runs endpoint
    res_runs = await client.get(f"/api/v1/workloads/{workload_id}/mlflow-runs")
    assert res_runs.status_code == 200
    runs_data = res_runs.json()
    assert runs_data["workload_id"] == workload_id
    assert "experiment" in runs_data
    assert isinstance(runs_data["runs"], list)
