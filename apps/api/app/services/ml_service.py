import os
import time
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.config import settings
from apps.api.app.models.entities import AuditEvent, Model, ModelVersion, Workload


class MLPlatformService:
    @staticmethod
    def _generate_synthetic_data(n_samples: int = 500, random_state: int = 42):
        np.random.seed(random_state)
        # 5 input features: e.g. latency, batch_size, tokens, cpu, memory
        X = np.random.rand(n_samples, 5) * 10
        weights = np.array([2.5, -1.2, 0.8, 3.4, -0.5])
        noise = np.random.normal(0, 0.5, size=n_samples)
        y = np.dot(X, weights) + 4.2 + noise
        
        split = int(n_samples * 0.8)
        return X[:split], y[:split], X[split:], y[split:]

    @classmethod
    async def train_and_register_model(
        cls,
        db: AsyncSession,
        workload_id: str,
        model_name: str = "performance_regressor",
        alpha: float = 1.0,
        max_iter: int = 1000,
        user_id: str = "usr-demo-admin",
    ) -> dict[str, Any]:
        # 1. Fetch workload
        res = await db.execute(select(Workload).where(Workload.id == workload_id))
        workload = res.scalar_one_or_none()
        if not workload:
            raise ValueError(f"Workload with id '{workload_id}' not found.")

        # 2. Get or create Model entity
        res_m = await db.execute(select(Model).where(Model.workload_id == workload_id, Model.name == model_name))
        model_entity = res_m.scalar_one_or_none()
        if not model_entity:
            model_entity = Model(
                workload_id=workload_id,
                name=model_name,
                framework="scikit-learn",
            )
            db.add(model_entity)
            await db.flush()

        # 3. Determine new semantic version
        res_v = await db.execute(
            select(ModelVersion).where(ModelVersion.model_id == model_entity.id)
        )
        existing_versions = res_v.scalars().all()
        version_num = len(existing_versions) + 1
        version_str = f"v{version_num}.0.0"

        # 4. Train Scikit-Learn Model
        start_time = time.time()
        X_train, y_train, X_test, y_test = cls._generate_synthetic_data()
        regressor = Ridge(alpha=alpha, max_iter=max_iter)
        regressor.fit(X_train, y_train)
        training_duration = time.time() - start_time

        # 5. Evaluate Metrics
        preds = regressor.predict(X_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        mae = float(mean_absolute_error(y_test, preds))
        r2 = float(r2_score(y_test, preds))

        # 6. Save Artifact
        artifact_dir = os.path.join(settings.ARTIFACT_STORE_PATH, workload_id, "models")
        os.makedirs(artifact_dir, exist_ok=True)
        artifact_path = os.path.join(artifact_dir, f"{model_name}_{version_str}.joblib")
        joblib.dump(regressor, artifact_path)

        metrics = {
            "rmse": round(rmse, 4),
            "mae": round(mae, 4),
            "r2_score": round(r2, 4),
            "training_duration_sec": round(training_duration, 4),
            "test_samples": len(y_test),
        }
        parameters = {
            "alpha": alpha,
            "max_iter": max_iter,
            "features_count": 5,
            "algorithm": "Ridge",
        }

        # 7. Create ModelVersion
        version_entity = ModelVersion(
            model_id=model_entity.id,
            version=version_str,
            artifact_uri=artifact_path,
            metrics_json=metrics,
            parameters_json=parameters,
            status="registered",
        )
        db.add(version_entity)

        # 8. Record Audit
        audit = AuditEvent(
            organization_id="org-demo-nuvorix",
            user_id=user_id,
            action="models:train",
            resource_type="model_version",
            resource_id=version_entity.id,
            metadata_json={"model": model_name, "version": version_str, "metrics": metrics},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(version_entity)

        return {
            "model_id": model_entity.id,
            "version_id": version_entity.id,
            "version": version_str,
            "metrics": metrics,
            "parameters": parameters,
            "artifact_uri": artifact_path,
            "status": version_entity.status,
        }

    @classmethod
    async def promote_version(
        cls,
        db: AsyncSession,
        version_id: str,
        target_env: str = "staging",
        user_id: str = "usr-demo-admin",
    ) -> dict[str, Any]:
        res = await db.execute(select(ModelVersion).where(ModelVersion.id == version_id))
        version_entity = res.scalar_one_or_none()
        if not version_entity:
            raise ValueError(f"Version with id '{version_id}' not found.")

        version_entity.status = target_env
        
        # update workload active version if production
        res_m = await db.execute(select(Model).where(Model.id == version_entity.model_id))
        model = res_m.scalar_one()
        res_w = await db.execute(select(Workload).where(Workload.id == model.workload_id))
        workload = res_w.scalar_one()
        if target_env == "production":
            workload.active_version = version_entity.version

        audit = AuditEvent(
            organization_id="org-demo-nuvorix",
            user_id=user_id,
            action="models:promote",
            resource_type="model_version",
            resource_id=version_entity.id,
            metadata_json={"target_environment": target_env, "version": version_entity.version},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(version_entity)

        return {
            "version_id": version_entity.id,
            "version": version_entity.version,
            "status": version_entity.status,
            "environment": target_env,
        }
