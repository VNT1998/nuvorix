import datetime
import hashlib
import hmac
import secrets
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.entities import APIKey, utc_now


class APIKeyService:
    @classmethod
    async def create_api_key(
        cls,
        db: AsyncSession,
        organization_id: str,
        name: str,
        role: str = "developer",
        scopes: list[str] | None = None,
        expires_in_days: int | None = 30,
    ) -> tuple[APIKey, str]:
        """
        Generate a cryptographically secure database-backed API key.
        Returns the persistent APIKey record and the raw key string (revealed only once).
        """
        prefix_part = secrets.token_hex(4)  # 8 hex chars
        secret_part = secrets.token_urlsafe(32)
        raw_key = f"nvx_{prefix_part}_{secret_part}"
        key_prefix = f"nvx_{prefix_part}"

        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        expires_at = (
            datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=expires_in_days)
            if expires_in_days
            else None
        )

        if scopes is not None:
            from apps.api.app.core.security import ALL_PERMISSIONS

            for s in scopes:
                if s not in ALL_PERMISSIONS:
                    raise ValueError(f"Invalid scope '{s}'. Must be one of registered permissions.")

        api_key = APIKey(
            organization_id=organization_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            role=role,
            scopes_json=scopes,
            expires_at=expires_at,
        )
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)
        return api_key, raw_key

    @classmethod
    async def authenticate_key(
        cls,
        db: AsyncSession,
        raw_key: str,
    ) -> tuple[APIKey, dict[str, Any]] | None:
        """
        Authenticate an API key against database hashes using constant-time comparison.
        Rejects arbitrary strings, expired keys, or revoked keys.
        """
        if not raw_key or not raw_key.startswith("nvx_"):
            return None

        parts = raw_key.split("_")
        if len(parts) < 3:
            return None

        key_prefix = f"{parts[0]}_{parts[1]}"
        res = await db.execute(
            select(APIKey).where(
                APIKey.key_prefix == key_prefix,
                APIKey.revoked_at.is_(None),
            )
        )
        api_key = res.scalar_one_or_none()
        if not api_key:
            return None

        # Check expiration
        now = datetime.datetime.now(datetime.UTC)
        if api_key.expires_at is not None:
            # Handle timezone-aware comparison
            exp = api_key.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=datetime.UTC)
            if exp < now:
                return None

        # Constant-time hash verification
        computed_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(api_key.key_hash, computed_hash):
            return None

        # Record last used
        api_key.last_used_at = now
        await db.commit()

        claims = {
            "key_id": api_key.id,
            "organization_id": api_key.organization_id,
            "name": api_key.name,
            "role": api_key.role,
            "scopes": api_key.scopes_json,
        }
        return api_key, claims

    @classmethod
    async def revoke_key(cls, db: AsyncSession, key_id: str, organization_id: str) -> bool:
        """Revoke an active API key."""
        res = await db.execute(
            select(APIKey).where(
                APIKey.id == key_id,
                APIKey.organization_id == organization_id,
                APIKey.revoked_at.is_(None),
            )
        )
        api_key = res.scalar_one_or_none()
        if not api_key:
            return False

        api_key.revoked_at = utc_now()
        await db.commit()
        return True
