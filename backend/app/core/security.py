import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.session import get_db


class ExecutionContext(BaseModel):
    user_id: str
    organization_id: str
    role: str
    permissions: set[str] = Field(default_factory=set)
    request_id: str | None = None
    source: str = "api"


class UserSession(BaseModel):
    user_id: str
    organization_id: str
    name: str
    email: str
    role: str  # admin, platform_engineer, ml_engineer, developer, viewer
    scopes: list[str] | None = None
    actor_type: str = "user"  # user, api_key, system, agent
    request_id: str | None = None

    def to_context(self, request_id: str | None = None, source: str = "api") -> ExecutionContext:
        perms = ROLE_PERMISSIONS.get(self.role, set())
        if self.scopes is not None:
            perms = perms.intersection(set(self.scopes))
        return ExecutionContext(
            user_id=self.user_id,
            organization_id=self.organization_id,
            role=self.role,
            permissions=set(perms),
            request_id=request_id or self.request_id,
            source=source,
        )


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "projects:create",
        "projects:delete",
        "projects:read",
        "workloads:create",
        "workloads:delete",
        "workloads:read",
        "models:train",
        "models:register",
        "models:promote",
        "evaluations:run",
        "evaluations:approve",
        "deployments:create",
        "deployments:rollback",
        "deployments:bypass_gate",
        "knowledge:ingest",
        "knowledge:query",
        "agents:run",
        "agents:tools:execute_high_risk",
        "incidents:resolve",
        "incidents:remediate",
        "audit:read",
    },
    "platform_engineer": {
        "projects:read",
        "workloads:create",
        "workloads:read",
        "evaluations:run",
        "evaluations:approve",
        "deployments:create",
        "deployments:rollback",
        "knowledge:query",
        "agents:run",
        "agents:tools:execute_high_risk",
        "incidents:resolve",
        "incidents:remediate",
        "audit:read",
    },
    "ml_engineer": {
        "projects:read",
        "workloads:create",
        "workloads:read",
        "models:train",
        "models:register",
        "models:promote",
        "evaluations:run",
        "deployments:create",
        "knowledge:ingest",
        "knowledge:query",
        "agents:run",
        "audit:read",
    },
    "developer": {
        "projects:read",
        "workloads:create",
        "workloads:read",
        "evaluations:run",
        "knowledge:query",
        "agents:run",
        "audit:read",
    },
    "viewer": {
        "projects:read",
        "workloads:read",
        "audit:read",
    },
}

ALL_PERMISSIONS: set[str] = {perm for perms in ROLE_PERMISSIONS.values() for perm in perms}


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_access_token(
    user_id: str,
    organization_id: str,
    role: str,
    name: str = "",
    email: str = "",
    scopes: list[str] | None = None,
    expires_in_seconds: int = 86400,
) -> str:
    """Generate an HMAC-SHA256 signed access token."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "org": organization_id,
        "role": role,
        "name": name or f"User {user_id}",
        "email": email or f"{user_id}@nuvorix.local",
        "scopes": scopes if scopes is not None else None,
        "exp": int(time.time()) + expires_in_seconds,
        "iat": int(time.time()),
    }
    header_b64 = _b64url_encode(json.dumps(header).encode())
    payload_b64 = _b64url_encode(json.dumps(payload).encode())
    signature_input = f"{header_b64}.{payload_b64}".encode()
    sig = hmac.new(settings.SECRET_KEY.encode(), signature_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_access_token(token: str) -> dict[str, Any] | None:
    """Verify an HMAC-SHA256 signed access token and return claims if valid."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    header_b64, payload_b64, sig_b64 = parts
    signature_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = hmac.new(settings.SECRET_KEY.encode(), signature_input, hashlib.sha256).digest()
    expected_sig_b64 = _b64url_encode(expected_sig)
    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        return None
    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


async def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    x_user_role: str | None = Header(None, alias="X-User-Role"),
    x_org_id: str | None = Header(None, alias="X-Org-Id"),
    x_request_id: str | None = Header(None, alias="X-Request-ID"),
    db: AsyncSession = Depends(get_db),
) -> UserSession:
    """
    Extract authenticated user session.
    - If Bearer token is provided: verifies cryptographic signature and claims.
    - If X-API-Key is provided: verifies against database API key hashes using constant-time comparison.
    - In 'production' mode: rejects requests lacking valid credentials with 401; ignores dev headers.
    - In 'development' mode: falls back to dev headers or explicit demo user identity.
    """
    is_prod = (settings.ENVIRONMENT.lower() == "production") or (settings.AUTH_MODE == "production")

    # 1. Bearer Token Authentication
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        claims = verify_access_token(token)
        if claims:
            role = claims.get("role", "viewer")
            if role not in ROLE_PERMISSIONS:
                role = "viewer"
            return UserSession(
                user_id=claims.get("sub", "usr-anonymous"),
                organization_id=claims.get("org", settings.DEFAULT_ORG_ID),
                name=claims.get("name", "Authenticated User"),
                email=claims.get("email", "user@nuvorix.local"),
                role=role,
                scopes=claims.get("scopes"),
                actor_type="user",
                request_id=x_request_id,
            )
        elif is_prod:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 2. Database-backed API Key Authentication
    if x_api_key:
        from backend.app.services.api_key_service import APIKeyService

        auth_result = await APIKeyService.authenticate_key(db=db, raw_key=x_api_key)
        if auth_result:
            api_key, claims = auth_result
            role = claims.get("role", "developer")
            if role not in ROLE_PERMISSIONS:
                role = "viewer"
            return UserSession(
                user_id=f"key-{api_key.id}",
                organization_id=claims.get("organization_id", settings.DEFAULT_ORG_ID),
                name=claims.get("name", "API Key"),
                email=f"{api_key.key_prefix}@api-key.nuvorix.local",
                role=role,
                scopes=claims.get("scopes"),
                actor_type="api_key",
                request_id=x_request_id,
            )
        elif is_prod:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 3. Production Enforcement: Dev headers are NEVER accepted in production mode
    if is_prod:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required in production mode",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. Development Mode Fallback
    role = x_user_role or settings.DEFAULT_USER_ROLE
    if role not in ROLE_PERMISSIONS:
        role = "viewer"

    return UserSession(
        user_id=x_user_id or settings.DEFAULT_USER_ID,
        organization_id=x_org_id or settings.DEFAULT_ORG_ID,
        name=f"Demo {role.replace('_', ' ').title()}",
        email=f"{role}@nuvorix.local",
        role=role,
        scopes=None,
        actor_type="user",
        request_id=x_request_id,
    )


def check_permission(user: UserSession | ExecutionContext, required_permission: str) -> bool:
    """Check if the user/context possesses the required permission, respecting API key scope restrictions."""
    if isinstance(user, ExecutionContext):
        return required_permission in user.permissions

    role_perms = ROLE_PERMISSIONS.get(user.role, set())
    if user.scopes is not None:
        effective_perms = role_perms.intersection(set(user.scopes))
        return required_permission in effective_perms
    return required_permission in role_perms


def require_permission(permission: str):
    """FastAPI dependency to enforce RBAC permissions."""

    async def dependency(user: UserSession = Depends(get_current_user)) -> UserSession:
        if not check_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' lacks required permission: '{permission}'",
            )
        return user

    return dependency
