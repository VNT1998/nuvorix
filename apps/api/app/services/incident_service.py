import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.telemetry import INCIDENTS_TOTAL
from apps.api.app.models.entities import AuditEvent, Deployment, Incident, Project, Workload
from apps.api.app.services.deploy_service import DeploymentPlatformService


class IncidentRCAService:
    @classmethod
    async def get_all_incidents(
        cls,
        db: AsyncSession,
        project_id: str | None = None,
        org_id: str | None = None,
    ) -> list[Incident]:
        query = select(Incident).order_by(Incident.created_at.desc())
        if project_id:
            query = query.where(Incident.project_id == project_id)
        if org_id:
            query = query.join(Project, Incident.project_id == Project.id).where(
                Project.organization_id == org_id
            )
        res = await db.execute(query)
        return list(res.scalars().all())

    @classmethod
    async def create_incident(
        cls,
        db: AsyncSession,
        project_id: str,
        severity: str,
        title: str,
        root_cause: str,
        recommendation: str,
        confidence: float,
        evidence: list[str],
    ) -> Incident:
        inc = Incident(
            project_id=project_id,
            severity=severity,
            title=title,
            status="open",
            root_cause=root_cause,
            recommendation=recommendation,
            confidence=confidence,
            evidence_json=evidence,
        )
        db.add(inc)
        INCIDENTS_TOTAL.labels(severity=severity, status="open").inc()
        await db.commit()
        await db.refresh(inc)
        return inc

    @classmethod
    async def remediate_incident(
        cls,
        db: AsyncSession,
        incident_id: str,
        action: str = "rollback",
        user_id: str = "usr-demo-admin",
        org_id: str | None = None,
    ) -> dict[str, Any]:
        query = select(Incident).where(Incident.id == incident_id)
        if org_id:
            query = query.join(Project, Incident.project_id == Project.id).where(
                Project.organization_id == org_id
            )
        res = await db.execute(query)
        incident = res.scalar_one_or_none()
        if not incident:
            raise ValueError(f"Incident with id '{incident_id}' not found.")

        # Find project to get organization_id for audit
        res_p = await db.execute(select(Project).where(Project.id == incident.project_id))
        proj = res_p.scalar_one_or_none()
        audit_org = proj.organization_id if proj else (org_id or "org-demo-nuvorix")

        # Find latest active deployment in this project's workloads to trigger rollback
        res_w = await db.execute(select(Workload).where(Workload.project_id == incident.project_id))
        workloads = res_w.scalars().all()
        
        rollback_info = None
        for w in workloads:
            res_d = await db.execute(
                select(Deployment)
                .where(Deployment.workload_id == w.id, Deployment.status == "active")
                .order_by(Deployment.created_at.desc())
            )
            active_dep = res_d.scalars().first()
            if active_dep:
                rollback_info = await DeploymentPlatformService.rollback_deployment(
                    db=db, deployment_id=active_dep.id, user_id=user_id
                )
                break

        incident.status = "resolved"
        incident.resolved_at = datetime.datetime.now(datetime.UTC)

        audit = AuditEvent(
            organization_id=audit_org,
            user_id=user_id,
            action="incidents:remediate",
            resource_type="incident",
            resource_id=incident.id,
            metadata_json={"action": action, "rollback_result": rollback_info},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(incident)

        return {
            "incident_id": incident.id,
            "status": incident.status,
            "action_taken": action,
            "rollback_details": rollback_info,
            "resolved_at": incident.resolved_at,
        }
