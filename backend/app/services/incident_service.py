import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.telemetry import INCIDENTS_TOTAL
from backend.app.models.entities import AuditEvent, Deployment, Incident, Project, Workload
from backend.app.services.deploy_service import DeploymentPlatformService


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
        deployment_id: str | None = None,
    ) -> Incident:
        inc = Incident(
            project_id=project_id,
            deployment_id=deployment_id,
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
        user_id: str = "dev-demo-user",
        org_id: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Remediate incident safely:
        1. Verify incident ownership and tenancy
        2. Identify target affected deployment explicitly
        3. Verify target deployment ownership and active state
        4. Execute rollback transition via deploy service
        5. Record complete audit trail with before/after state
        """
        query = select(Incident).where(Incident.id == incident_id)
        if org_id:
            query = query.join(Project, Incident.project_id == Project.id).where(
                Project.organization_id == org_id
            )
        res = await db.execute(query)
        incident = res.scalar_one_or_none()
        if not incident:
            raise ValueError(f"Incident with id '{incident_id}' not found.")

        # Find project to verify organization ownership
        res_p = await db.execute(select(Project).where(Project.id == incident.project_id))
        proj = res_p.scalar_one_or_none()
        if not proj:
            raise ValueError(f"Project '{incident.project_id}' associated with incident not found.")
        audit_org = proj.organization_id

        if incident.status == "resolved":
            return {
                "incident_id": incident.id,
                "status": "resolved",
                "action": action,
                "message": f"Incident '{incident_id}' is already resolved.",
            }

        before_status = incident.status
        target_dep = None

        # 1. If incident explicitly links affected deployment, verify it
        if incident.deployment_id:
            res_d = await db.execute(
                select(Deployment)
                .join(Workload, Deployment.workload_id == Workload.id)
                .where(
                    Deployment.id == incident.deployment_id,
                    Workload.project_id == incident.project_id,
                )
            )
            target_dep = res_d.scalar_one_or_none()
            if not target_dep:
                raise ValueError(
                    f"Deployment '{incident.deployment_id}' referenced by incident '{incident_id}' not found in project '{incident.project_id}'."
                )
            if target_dep.status != "active":
                raise ValueError(
                    f"Deployment '{target_dep.id}' is not in active state (current status: '{target_dep.status}'). Cannot rollback."
                )

        # 2. If no deployment linked, find active deployment in project workloads
        if not target_dep:
            res_w = await db.execute(
                select(Workload).where(Workload.project_id == incident.project_id)
            )
            workloads = res_w.scalars().all()
            for w in workloads:
                res_d = await db.execute(
                    select(Deployment)
                    .where(Deployment.workload_id == w.id, Deployment.status == "active")
                    .order_by(Deployment.created_at.desc())
                )
                active_candidate = res_d.scalars().first()
                if active_candidate:
                    target_dep = active_candidate
                    incident.deployment_id = target_dep.id
                    break

        if not target_dep:
            raise ValueError(
                f"No active deployment found in project '{incident.project_id}' to rollback."
            )

        # 3. Perform remediation rollback
        rollback_info = await DeploymentPlatformService.rollback_deployment(
            db=db,
            deployment_id=target_dep.id,
            user_id=user_id,
            org_id=audit_org,
        )

        incident.status = "resolved"
        incident.resolved_at = datetime.datetime.now(datetime.UTC)

        # 4. Record audit event
        audit = AuditEvent(
            organization_id=audit_org,
            user_id=user_id,
            action="incidents:remediate",
            resource_type="incident",
            resource_id=incident.id,
            request_id=request_id,
            actor_type="user",
            reason=f"Incident remediation via {action}",
            before_state_json={
                "status": before_status,
                "deployment_id": target_dep.id,
                "deployment_status": "active",
            },
            after_state_json={
                "status": "resolved",
                "action": action,
                "remediated_deployment_id": target_dep.id,
            },
            metadata_json={"action": action, "rollback_result": rollback_info},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(incident)

        return {
            "incident_id": incident.id,
            "status": incident.status,
            "action_taken": action,
            "target_deployment_id": target_dep.id,
            "rollback_details": rollback_info,
            "resolved_at": incident.resolved_at,
        }
