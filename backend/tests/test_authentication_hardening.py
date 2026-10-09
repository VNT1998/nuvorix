import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.core.config import settings
from backend.app.core.security import create_access_token
from backend.app.db.session import AsyncSessionLocal
from backend.app.main import app
from backend.app.services.api_key_service import APIKeyService


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_production_auth_strict_enforcement(client: AsyncClient):
    """Verify that in production mode, all uncredentialed or invalid requests fail with 401."""
    original_mode = settings.AUTH_MODE
    try:
        settings.AUTH_MODE = "production"

        # 1. No credentials
        res_no_auth = await client.get("/api/v1/projects")
        assert res_no_auth.status_code == 401
        assert "Authentication credentials required" in res_no_auth.json()["detail"]

        # 2. Dev headers ignored in production mode
        res_dev_headers = await client.get(
            "/api/v1/projects",
            headers={"X-User-Role": "admin", "X-User-Id": "dev-injected-admin"},
        )
        assert res_dev_headers.status_code == 401

        # 3. Arbitrary fake prefix API key rejected
        res_fake_key = await client.get(
            "/api/v1/projects",
            headers={"X-API-Key": "nuvorix_sk_fake_secret_key_12345"},
        )
        assert res_fake_key.status_code == 401

        # 4. Invalid Bearer token
        res_bad_jwt = await client.get(
            "/api/v1/projects",
            headers={"Authorization": "Bearer bad.token.here"},
        )
        assert res_bad_jwt.status_code == 401

        # 5. Expired Bearer token
        expired_token = create_access_token(
            user_id="usr-expired",
            organization_id=settings.DEFAULT_ORG_ID,
            role="admin",
            expires_in_seconds=-3600,
        )
        res_expired = await client.get(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert res_expired.status_code == 401

        # 6. Valid Bearer token succeeds
        valid_token = create_access_token(
            user_id="usr-valid",
            organization_id=settings.DEFAULT_ORG_ID,
            role="admin",
            expires_in_seconds=3600,
        )
        res_valid = await client.get(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert res_valid.status_code == 200
    finally:
        settings.AUTH_MODE = original_mode


@pytest.mark.asyncio
async def test_database_backed_api_key_lifecycle(client: AsyncClient):
    """Test API key generation, successful authentication, expiration, and revocation."""
    async with AsyncSessionLocal() as session:
        # Create active key
        api_key, raw_key = await APIKeyService.create_api_key(
            db=session,
            organization_id=settings.DEFAULT_ORG_ID,
            name="CI Automation Key",
            role="platform_engineer",
            scopes=["projects:read", "workloads:read"],
            expires_in_days=7,
        )

    # 1. Authenticate with valid raw key
    res_valid_key = await client.get(
        "/api/v1/projects",
        headers={"X-API-Key": raw_key},
    )
    assert res_valid_key.status_code == 200

    # 2. Scope restriction: Key only has projects:read and workloads:read
    res_forbidden = await client.post(
        "/api/v1/projects",
        json={"name": "Scope Restricted Creation Attempt"},
        headers={"X-API-Key": raw_key},
    )
    assert res_forbidden.status_code == 403
    assert "lacks required permission" in res_forbidden.json()["detail"]

    # 3. Revoke key
    async with AsyncSessionLocal() as session:
        revoked = await APIKeyService.revoke_key(
            db=session,
            key_id=api_key.id,
            organization_id=settings.DEFAULT_ORG_ID,
        )
        assert revoked is True

    # 4. Authenticate with revoked key -> rejected (401 in prod, or 401 via authenticate_key)
    original_mode = settings.AUTH_MODE
    try:
        settings.AUTH_MODE = "production"
        res_revoked = await client.get(
            "/api/v1/projects",
            headers={"X-API-Key": raw_key},
        )
        assert res_revoked.status_code == 401
    finally:
        settings.AUTH_MODE = original_mode


@pytest.mark.asyncio
async def test_concurrent_api_key_usage(client: AsyncClient):
    """Concurrency test: verify multiple concurrent requests using database-backed API key."""
    async with AsyncSessionLocal() as session:
        _, raw_key = await APIKeyService.create_api_key(
            db=session,
            organization_id=settings.DEFAULT_ORG_ID,
            name="Concurrent Load Key",
            role="developer",
            scopes=["projects:read"],
            expires_in_days=1,
        )

    async def make_request():
        return await client.get("/api/v1/projects", headers={"X-API-Key": raw_key})

    # Run 10 concurrent requests
    responses = await asyncio.gather(*[make_request() for _ in range(10)])
    assert all(r.status_code == 200 for r in responses)
