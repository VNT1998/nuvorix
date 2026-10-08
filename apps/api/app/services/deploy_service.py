from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.telemetry import DEPLOYMENT_TOTAL
from apps.api.app.models.entities import (
    AuditEvent,
    Deployment,
    EvaluationRun,
    IdempotencyKey,
    Project,
    Workload,
)

VALID_STATES: set[str] = {
    "candidate",
    "active",
    "retired",
    "rolled_back",
    "failed",
    "circuit_open",
}

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "candidate": {"active", "failed"},
    "active": {"retired", "rolled_back", "circuit_open"},
    "circuit_open": {"active", "retired"},
    "retired": set(),
    "rolled_back": set(),
    "failed": set(),
}


class DeploymentPlatformService:
    @staticmethod
    def validate_transition(current_state: str, target_state: str) -> bool:
        """Enforces legal deployment state transitions."""
        if target_state not in VALID_STATES:
            raise ValueError(f"Invalid target deployment state: '{target_state}'")
        allowed = ALLOWED_TRANSITIONS.get(current_state, set())
        if target_state not in allowed:
            raise ValueError(
                f"Illegal deployment state transition from '{current_state}' to '{target_state}'. "
                f"Allowed target states: {sorted(allowed)}"
            )
        return True

    @classmethod
    async def create_deployment(
        cls,
        db: AsyncSession,
        workload_id: str,
        version: str,
        environment: str = "staging",
        strategy: str = "blue_green",
        bypass_gate: bool = False,
        user_id: str = "dev-demo-user",
        org_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Deployment:
        # 1. Idempotency check
        if idempotency_key:
            res_idem = await db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.key == idempotency_key,
                )
            )
            cached = res_idem.scalar_one_or_none()
            if cached and "deployment_id" in cached.response_json:
                res_existing = await db.execute(
                    select(Deployment).where(Deployment.id == cached.response_json["deployment_id"])
                )
                existing = res_existing.scalar_one_or_none()
                if existing:
                    return existing

        # 2. Verify workload exists and belongs to caller's organization
        query_w = select(Workload).join(Project, Workload.project_id == Project.id).where(Workload.id == workload_id)
        if org_id:
            query_w = query_w.where(Project.organization_id == org_id)
        res_w = await db.execute(query_w)
        workload = res_w.scalar_one_or_none()
        if not workload:
            raise ValueError(f"Workload with id '{workload_id}' not found or unauthorized.")

        res_p = await db.execute(select(Project).where(Project.id == workload.project_id))
        proj = res_p.scalar_one_or_none()
        audit_org = proj.organization_id if proj else (org_id or "org-demo-nuvorix")

        # 3. Check quality release gate: look for latest evaluation run
        res_e = await db.execute(
            select(EvaluationRun)
            .where(EvaluationRun.workload_id == workload_id, EvaluationRun.version == version)
            .order_by(EvaluationRun.started_at.desc())
        )
        latest_eval = res_e.scalars().first()

        if not bypass_gate and latest_eval and latest_eval.decision == "BLOCK":
            DEPLOYMENT_TOTAL.labels(environment=environment, strategy=strategy, status="blocked").inc()
            raise ValueError(
                f"Release Policy Gate BLOCKED version '{version}': "
                f"{'; '.join(latest_eval.reasons_json)}"
            )

        # 4. Transition previous active deployments in this environment to retired
        res_prev = await db.execute(
            select(Deployment).where(
                Deployment.workload_id == workload_id,
                Deployment.environment == environment,
                Deployment.status == "active",
            )
        )
        prev_active = res_prev.scalars().all()
        for p in prev_active:
            cls.validate_transition(p.status, "retired")
            p.status = "retired"
            p.traffic_percentage = 0

        # 5. Create new deployment
        dep = Deployment(
            workload_id=workload_id,
            version=version,
            environment=environment,
            strategy=strategy,
            status="active",
            traffic_percentage=100,
        )
        db.add(dep)
        await db.flush()

        # 6. Update workload active version if in production or staging
        if environment in ["production", "staging"]:
            workload.active_version = version
            workload.status = "healthy"

        DEPLOYMENT_TOTAL.labels(environment=environment, strategy=strategy, status="active").inc()

        audit = AuditEvent(
            organization_id=audit_org,
            user_id=user_id,
            action="deployments:create",
            resource_type="deployment",
            resource_id=dep.id,
            before_state_json={"workload_active_version": workload.active_version},
            after_state_json={"status": "active", "traffic_percentage": 100, "version": version},
            metadata_json={"version": version, "environment": environment, "strategy": strategy},
        )
        db.add(audit)

        # Record idempotency key if requested
        if idempotency_key:
            target_org = org_id or audit_org
            idem_record = IdempotencyKey(
                key=idempotency_key,
                organization_id=target_org,
                endpoint="POST /deployments",
                response_code=201,
                response_json={"deployment_id": dep.id, "version": dep.version, "status": dep.status},
            )
            db.add(idem_record)

        try:
            await db.commit()
            await db.refresh(dep)
            return dep
        except Exception:
            await db.rollback()
            if idempotency_key:
                res_idem = await db.execute(
                    select(IdempotencyKey).where(
                        IdempotencyKey.key == idempotency_key,
                    )
                )
                cached = res_idem.scalar_one_or_none()
                if cached and "deployment_id" in cached.response_json:
                    res_existing = await db.execute(
                        select(Deployment).where(Deployment.id == cached.response_json["deployment_id"])
                    )
                    existing = res_existing.scalar_one_or_none()
                    if existing:
                        return existing
            raise

    @classmethod
    async def rollback_deployment(
        cls,
        db: AsyncSession,
        deployment_id: str,
        user_id: str = "dev-demo-user",
        org_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        # 1. Idempotency check
        if idempotency_key:
            res_idem = await db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.key == idempotency_key,
                )
            )
            cached = res_idem.scalar_one_or_none()
            if cached and "active_version" in cached.response_json:
                return cached.response_json

        # 2. Fetch deployment to rollback with tenant check
        query = select(Deployment).where(Deployment.id == deployment_id)
        if org_id:
            query = (
                query.join(Workload, Deployment.workload_id == Workload.id)
                .join(Project, Workload.project_id == Project.id)
                .where(Project.organization_id == org_id)
            )
        res = await db.execute(query)
        target_dep = res.scalar_one_or_none()
        if not target_dep:
            raise ValueError(f"Deployment with id '{deployment_id}' not found or unauthorized.")

        # Find project organization
        res_p = await db.execute(
            select(Project)
            .join(Workload, Project.id == Workload.project_id)
            .where(Workload.id == target_dep.workload_id)
        )
        proj = res_p.scalar_one_or_none()
        audit_org = proj.organization_id if proj else (org_id or "org-demo-nuvorix")

        # 3. Validate state transition for target deployment
        cls.validate_transition(target_dep.status, "rolled_back")

        # 4. Find previous successful deployment in same environment
        res_prev = await db.execute(
            select(Deployment)
            .where(
                Deployment.workload_id == target_dep.workload_id,
                Deployment.environment == target_dep.environment,
                Deployment.id != target_dep.id,
                Deployment.status.in_(["retired", "active"]),
            )
            .order_by(Deployment.created_at.desc())
        )
        previous_dep = res_prev.scalars().first()

        if not previous_dep:
            # If no previous found, still transition target to rolled_back
            target_dep.status = "rolled_back"
            target_dep.traffic_percentage = 0
            await db.commit()
            result = {
                "previous_deployment_id": "none",
                "active_version": "none",
                "status": "rolled_back",
                "message": f"Deployment {deployment_id} rolled back, no previous version recorded.",
            }
            return result

        # 5. Perform traffic switch
        target_dep.status = "rolled_back"
        target_dep.traffic_percentage = 0

        # Create new deployment record representing the restored active release
        restored_dep = Deployment(
            workload_id=target_dep.workload_id,
            version=previous_dep.version,
            environment=target_dep.environment,
            strategy=target_dep.strategy,
            status="active",
            traffic_percentage=100,
        )
        db.add(restored_dep)
        await db.flush()

        # Update workload active version
        res_w = await db.execute(select(Workload).where(Workload.id == target_dep.workload_id))
        workload = res_w.scalar_one()
        workload.active_version = restored_dep.version
        workload.status = "healthy"

        DEPLOYMENT_TOTAL.labels(
            environment=target_dep.environment, strategy=target_dep.strategy, status="rolled_back"
        ).inc()

        audit = AuditEvent(
            organization_id=audit_org,
            user_id=user_id,
            action="deployments:rollback",
            resource_type="deployment",
            resource_id=target_dep.id,
            before_state_json={"status": "active", "version": target_dep.version},
            after_state_json={"status": "rolled_back", "restored_version": restored_dep.version},
            metadata_json={
                "rolled_back_from": target_dep.version,
                "restored_to": restored_dep.version,
                "environment": target_dep.environment,
            },
        )
        db.add(audit)

        response_payload = {
            "previous_deployment_id": restored_dep.id,
            "active_version": restored_dep.version,
            "status": "active",
            "message": f"Successfully rolled back from {target_dep.version} to {restored_dep.version} in {target_dep.environment}.",
        }

        if idempotency_key:
            target_org = org_id or audit_org
            idem_record = IdempotencyKey(
                key=idempotency_key,
                organization_id=target_org,
                endpoint=f"POST /deployments/{deployment_id}/rollback",
                response_code=200,
                response_json=response_payload,
            )
            db.add(idem_record)

        try:
            await db.commit()
            return response_payload
        except Exception:
            await db.rollback()
            if idempotency_key:
                res_idem = await db.execute(
                    select(IdempotencyKey).where(
                        IdempotencyKey.key == idempotency_key,
                    )
                )
                cached = res_idem.scalar_one_or_none()
                if cached and "active_version" in cached.response_json:
                    return cached.response_json
            raise
