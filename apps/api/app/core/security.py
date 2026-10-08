from fastapi import Header, HTTPException, status
from pydantic import BaseModel


class UserSession(BaseModel):
    user_id: str
    organization_id: str
    name: str
    email: str
    role: str  # admin, platform_engineer, ml_engineer, developer, viewer


ROLE_PERMISSIONS = {
    "admin": {
        "projects:create", "projects:delete", "projects:read",
        "workloads:create", "workloads:delete", "workloads:read",
        "models:train", "models:register", "models:promote",
        "evaluations:run", "evaluations:approve",
        "deployments:create", "deployments:rollback",
        "knowledge:ingest", "knowledge:query",
        "agents:run", "agents:tools:execute_high_risk",
        "incidents:resolve", "incidents:remediate",
        "audit:read",
    },
    "platform_engineer": {
        "projects:read",
        "workloads:create", "workloads:read",
        "evaluations:run", "evaluations:approve",
        "deployments:create", "deployments:rollback",
        "knowledge:query",
        "agents:run", "agents:tools:execute_high_risk",
        "incidents:resolve", "incidents:remediate",
        "audit:read",
    },
    "ml_engineer": {
        "projects:read",
        "workloads:create", "workloads:read",
        "models:train", "models:register", "models:promote",
        "evaluations:run",
        "deployments:create",
        "knowledge:ingest", "knowledge:query",
        "agents:run",
        "audit:read",
    },
    "developer": {
        "projects:read",
        "workloads:create", "workloads:read",
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


def get_current_user(
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    x_user_role: str | None = Header(None, alias="X-User-Role"),
    x_org_id: str | None = Header(None, alias="X-Org-Id"),
) -> UserSession:
    """Extract authenticated user session. In dev mode, defaults to admin."""
    role = x_user_role or "admin"
    if role not in ROLE_PERMISSIONS:
        role = "viewer"
        
    return UserSession(
        user_id=x_user_id or "usr-demo-admin",
        organization_id=x_org_id or "org-demo-nuvorix",
        name="Platform Administrator" if role == "admin" else f"Demo {role.replace('_', ' ').title()}",
        email="admin@nuvorix.local" if role == "admin" else f"{role}@nuvorix.local",
        role=role,
    )


def check_permission(user: UserSession, required_permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(user.role, set())
    return required_permission in perms


def require_permission(permission: str):
    def dependency(user: UserSession = Header(get_current_user)):
        if not check_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' lacks required permission: '{permission}'",
            )
        return user
    return dependency
