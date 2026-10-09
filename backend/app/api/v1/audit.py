from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import UserSession, require_permission
from backend.app.db.session import get_db
from backend.app.models.entities import AuditEvent
from backend.app.schemas.domain import AuditEventResponse

router = APIRouter(prefix="/audit-events", tags=["Audit Trail"])


@router.get("", response_model=list[AuditEventResponse])
async def list_audit_events(
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("audit:read")),
):
    res = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.organization_id == user.organization_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(100)
    )
    events = res.scalars().all()
    return [
        AuditEventResponse(
            id=e.id,
            organization_id=e.organization_id,
            user_id=e.user_id,
            action=e.action,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            metadata=e.metadata_json or {},
            created_at=e.created_at,
        )
        for e in events
    ]
