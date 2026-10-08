from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.telemetry import DEPLOYMENT_TOTAL
from apps.api.app.models.entities import AuditEvent, Deployment, EvaluationRun, Workload


class DeploymentPlatformService:
    @classmethod
    async def create_deployment(
        cls,
        db: AsyncSession,
        workload_id: str,
        version: str,
        environment: str = "staging",
        strategy: str = "blue_green",
        bypass_gate: bool = False,
        user_id: str = "usr-demo-admin",
    ) -> Deployment:
        # 1. Verify workload exists
        res_w = await db.execute(select(Workload).where(Workload.id == workload_id))
        workload = res_w.scalar_one_or_none()
        if not workload:
            raise ValueError(f"Workload with id '{workload_id}' not found.")

        # 2. Check quality release gate: look for latest evaluation run
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

        # 3. Transition previous active deployments in this environment to retired
        res_prev = await db.execute(
            select(Deployment).where(
                Deployment.workload_id == workload_id,
                Deployment.environment == environment,
                Deployment.status == "active",
            )
        )
        prev_active = res_prev.scalars().all()
        for p in prev_active:
            p.status = "retired"
            p.traffic_percentage = 0

        # 4. Create new deployment
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

        # 5. Update workload active version if in production or staging
        if environment in ["production", "staging"]:
            workload.active_version = version
            workload.status = "healthy"

        DEPLOYMENT_TOTAL.labels(environment=environment, strategy=strategy, status="active").inc()

        audit = AuditEvent(
            organization_id="org-demo-nuvorix",
            user_id=user_id,
            action="deployments:create",
            resource_type="deployment",
            resource_id=dep.id,
            metadata_json={"version": version, "environment": environment, "strategy": strategy},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(dep)
        return dep

    @classmethod
    async def rollback_deployment(
        cls,
        db: AsyncSession,
        deployment_id: str,
        user_id: str = "usr-demo-admin",
    ) -> dict[str, Any]:
        # 1. Fetch deployment to rollback
        res = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
        target_dep = res.scalar_one_or_none()
        if not target_dep:
            raise ValueError(f"Deployment with id '{deployment_id}' not found.")

        # 2. Find previous successful deployment in same environment
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
            # If no previous found, still mark as rolled back
            target_dep.status = "rolled_back"
            target_dep.traffic_percentage = 0
            await db.commit()
            return {
                "previous_deployment_id": "none",
                "active_version": "none",
                "status": "rolled_back",
                "message": f"Deployment {deployment_id} rolled back, no previous version recorded.",
            }

        # 3. Perform traffic switch
        target_dep.status = "rolled_back"
        target_dep.traffic_percentage = 0

        previous_dep.status = "active"
        previous_dep.traffic_percentage = 100

        # Update workload active version
        res_w = await db.execute(select(Workload).where(Workload.id == target_dep.workload_id))
        workload = res_w.scalar_one()
        workload.active_version = previous_dep.version
        workload.status = "healthy"

        DEPLOYMENT_TOTAL.labels(
            environment=target_dep.environment, strategy=target_dep.strategy, status="rolled_back"
        ).inc()

        audit = AuditEvent(
            organization_id="org-demo-nuvorix",
            user_id=user_id,
            action="deployments:rollback",
            resource_type="deployment",
            resource_id=target_dep.id,
            metadata_json={
                "rolled_back_from": target_dep.version,
                "restored_to": previous_dep.version,
                "environment": target_dep.environment,
            },
        )
        db.add(audit)
        await db.commit()

        return {
            "previous_deployment_id": previous_dep.id,
            "active_version": previous_dep.version,
            "status": "active",
            "message": f"Successfully rolled back from {target_dep.version} to {previous_dep.version} in {target_dep.environment}.",
        }
