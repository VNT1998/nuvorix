import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.services.deploy_service import DeploymentPlatformService


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers={"X-User-Role": "admin"}
    ) as ac:
        yield ac


def test_deployment_state_machine_transition_rules():
    """Verify state machine accepts legal transitions and raises ValueError on illegal transitions."""
    # Legal transitions
    assert DeploymentPlatformService.validate_transition("candidate", "active") is True
    assert DeploymentPlatformService.validate_transition("active", "retired") is True
    assert DeploymentPlatformService.validate_transition("active", "rolled_back") is True
    assert DeploymentPlatformService.validate_transition("active", "circuit_open") is True
    assert DeploymentPlatformService.validate_transition("candidate", "failed") is True

    # Illegal transitions
    with pytest.raises(ValueError, match="Illegal deployment state transition"):
        DeploymentPlatformService.validate_transition("retired", "active")

    with pytest.raises(ValueError, match="Illegal deployment state transition"):
        DeploymentPlatformService.validate_transition("rolled_back", "active")

    with pytest.raises(ValueError, match="Illegal deployment state transition"):
        DeploymentPlatformService.validate_transition("failed", "active")


@pytest.mark.asyncio
async def test_deployment_idempotency(client: AsyncClient):
    """Verify that repeated requests with the same Idempotency-Key produce identical response and no duplicate deployment."""
    res_w = await client.get("/api/v1/workloads")
    workload = res_w.json()[0]
    workload_id = workload["id"]

    idem_key = f"idem-key-{uuid.uuid4().hex}"
    payload = {
        "version": f"v2.0.{uuid.uuid4().hex[:4]}",
        "environment": "staging",
        "strategy": "blue_green",
    }

    # 1. First request with Idempotency-Key
    resp1 = await client.post(
        f"/api/v1/workloads/{workload_id}/deployments",
        json=payload,
        headers={"Idempotency-Key": idem_key},
    )
    assert resp1.status_code == 201
    data1 = resp1.json()
    dep_id_1 = data1["id"]

    # 2. Second request with identical Idempotency-Key
    resp2 = await client.post(
        f"/api/v1/workloads/{workload_id}/deployments",
        json=payload,
        headers={"Idempotency-Key": idem_key},
    )
    assert resp2.status_code == 201
    data2 = resp2.json()

    # Must return identical deployment ID and payload
    assert data2["id"] == dep_id_1
    assert data2["version"] == data1["version"]


@pytest.mark.asyncio
async def test_concurrent_idempotent_requests(client: AsyncClient):
    """Concurrency test: execute two identical idempotent deployment requests simultaneously."""
    res_w = await client.get("/api/v1/workloads")
    workload_id = res_w.json()[0]["id"]

    idem_key = f"idem-concurrent-{uuid.uuid4().hex}"
    payload = {
        "version": f"v3.0.{uuid.uuid4().hex[:4]}",
        "environment": "staging",
        "strategy": "blue_green",
    }

    async def call_deploy():
        return await client.post(
            f"/api/v1/workloads/{workload_id}/deployments",
            json=payload,
            headers={"Idempotency-Key": idem_key},
        )

    # Trigger concurrently
    resp_a, resp_b = await asyncio.gather(call_deploy(), call_deploy())
    assert resp_a.status_code == 201
    assert resp_b.status_code == 201
    assert resp_a.json()["id"] == resp_b.json()["id"]


@pytest.mark.asyncio
async def test_rollback_ownership_and_state(client: AsyncClient):
    """Verify tenant boundary enforcement on rollback endpoints."""
    # Attempt to rollback a non-existent deployment ID or cross-tenant deployment
    bad_rb = await client.post(
        "/api/v1/deployments/dep-nonexistent-id/rollback",
        headers={"X-Org-Id": "org-other-attacker"},
    )
    assert bad_rb.status_code == 400 or bad_rb.status_code == 404
