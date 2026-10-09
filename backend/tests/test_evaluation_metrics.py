import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.db.session import AsyncSessionLocal
from backend.app.main import app
from backend.app.models.entities import Workload
from backend.app.services.eval_service import EvaluationEngineService


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers={"X-User-Role": "admin"}
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_rag_and_agent_evaluation_metrics():
    """Verify that evaluation metrics (Recall@3, MRR@3, empirical p95, tool accuracy) are genuinely computed."""
    async with AsyncSessionLocal() as session:
        # Fetch seeded support agent workload
        from sqlalchemy import select

        res = await session.execute(select(Workload).where(Workload.type == "agent"))
        agent_w = res.scalars().first()
        assert agent_w is not None

        result = await EvaluationEngineService.evaluate_workload_version(
            db=session,
            workload_id=agent_w.id,
            version="v1.2.0",
        )

        assert result["status"] == "completed"
        metrics = result["metrics"]

        # 1. Retrieval metrics calculated from actual benchmark suite
        assert "recall_at_3" in metrics
        assert "mrr_at_3" in metrics
        assert "precision_at_3" in metrics
        assert 0.0 <= metrics["recall_at_3"] <= 1.0
        assert 0.0 <= metrics["mrr_at_3"] <= 1.0

        # 2. Tool selection accuracy calculated from prompt router
        assert "tool_selection_accuracy" in metrics
        assert metrics["tool_selection_accuracy"] > 0.70

        # 3. Latency distribution (N=20 repeated observations)
        assert metrics["latency_measurements_count"] >= 20
        assert "min_latency_ms" in metrics
        assert "median_latency_ms" in metrics
        assert "avg_latency_ms" in metrics
        assert "p95_latency_ms" in metrics
        assert "max_latency_ms" in metrics
        assert (
            metrics["min_latency_ms"]
            <= metrics["median_latency_ms"]
            <= metrics["p95_latency_ms"]
            <= metrics["max_latency_ms"]
        )

        # 4. Cost metrics with explicit estimated_local mode
        assert "cost" in metrics
        assert metrics["cost"]["mode"] == "estimated_local"
        assert metrics["cost"]["currency"] == "USD"


@pytest.mark.asyncio
async def test_missing_ml_candidate_artifact_blocks_truthfully():
    """Verify that a missing ML model artifact results in an explicit BLOCK/failure, not silent retraining."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        res = await session.execute(select(Workload).where(Workload.type == "ml_model"))
        ml_w = res.scalars().first()
        assert ml_w is not None

        # Evaluate a non-existent candidate version whose artifact is missing on disk
        result = await EvaluationEngineService.evaluate_workload_version(
            db=session,
            workload_id=ml_w.id,
            version="v99.99.99-nonexistent",
        )

        assert result["passed"] is False
        assert result["decision"] == "BLOCK"
        assert result["status"] == "failed"
        assert any("candidate_artifact_unavailable" in r for r in result["reasons"])


@pytest.mark.asyncio
async def test_policy_gate_allow_and_block_rules(client: AsyncClient):
    """Verify deterministic release gate decisions against strict vs standard thresholds."""
    res_w = await client.get("/api/v1/workloads")
    agent_w = next(w for w in res_w.json() if w["type"] == "agent")

    # 1. Permissive policy -> ALLOW
    allow_resp = await client.post(
        f"/api/v1/workloads/{agent_w['id']}/evaluations",
        json={
            "version": "v1.2.0-eval-test",
            "policy": {
                "min_faithfulness": 0.50,
                "min_answer_correctness": 0.50,
                "max_p95_latency_ms": 10000.0,
            },
        },
    )
    assert allow_resp.status_code == 200
    assert allow_resp.json()["decision"] == "ALLOW"
    assert allow_resp.json()["passed"] is True

    # 2. Impossible latency threshold -> BLOCK with reason
    block_resp = await client.post(
        f"/api/v1/workloads/{agent_w['id']}/evaluations",
        json={
            "version": "v1.2.0-eval-test",
            "policy": {
                "max_p95_latency_ms": 0.0001,
            },
        },
    )
    assert block_resp.status_code == 200
    data = block_resp.json()
    assert data["decision"] == "BLOCK"
    assert data["passed"] is False
    assert any("p95 latency" in r for r in data["reasons"])
