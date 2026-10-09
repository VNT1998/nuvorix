from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import UserSession, require_permission
from backend.app.db.session import get_db
from backend.app.models.entities import Project
from backend.app.schemas.domain import IncidentResponse, RemediateIncidentRequest
from backend.app.services.incident_service import IncidentRCAService

router = APIRouter(tags=["Incidents & Root Cause Analysis"])


@router.get("/projects/{project_id}/incidents", response_model=list[IncidentResponse])
async def list_project_incidents(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("projects:read")),
):
    res_p = await db.execute(
        select(Project).where(
            Project.id == project_id, Project.organization_id == user.organization_id
        )
    )
    if not res_p.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    incidents = await IncidentRCAService.get_all_incidents(db=db, project_id=project_id)
    return [
        IncidentResponse(
            id=i.id,
            project_id=i.project_id,
            severity=i.severity,
            title=i.title,
            status=i.status,
            root_cause=i.root_cause,
            recommendation=i.recommendation,
            confidence=i.confidence,
            evidence=i.evidence_json or [],
            created_at=i.created_at,
            resolved_at=i.resolved_at,
        )
        for i in incidents
    ]


@router.get("/incidents", response_model=list[IncidentResponse])
async def list_all_incidents(
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("projects:read")),
):
    incidents = await IncidentRCAService.get_all_incidents(db=db, org_id=user.organization_id)
    return [
        IncidentResponse(
            id=i.id,
            project_id=i.project_id,
            severity=i.severity,
            title=i.title,
            status=i.status,
            root_cause=i.root_cause,
            recommendation=i.recommendation,
            confidence=i.confidence,
            evidence=i.evidence_json or [],
            created_at=i.created_at,
            resolved_at=i.resolved_at,
        )
        for i in incidents
    ]


@router.post("/incidents/{incident_id}/remediate")
async def remediate_incident(
    incident_id: str,
    payload: RemediateIncidentRequest,
    db: AsyncSession = Depends(get_db),
    user: UserSession = Depends(require_permission("incidents:remediate")),
):
    try:
        res = await IncidentRCAService.remediate_incident(
            db=db,
            incident_id=incident_id,
            action=payload.action,
            user_id=user.user_id,
            org_id=user.organization_id,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
