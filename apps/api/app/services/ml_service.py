import logging
import os
import time
from typing import Any

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.config import settings
from apps.api.app.models.entities import AuditEvent, Model, ModelVersion, Workload

logger = logging.getLogger(__name__)


class MLPlatformService:
    @staticmethod
    def _init_mlflow():
        os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)

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
        cls._init_mlflow()

        # 1. Fetch workload
        res = await db.execute(select(Workload).where(Workload.id == workload_id))
        workload = res.scalar_one_or_none()
        if not workload:
            raise ValueError(f"Workload with id '{workload_id}' not found.")

        # 2. Get or create Model entity
        res_m = await db.execute(
            select(Model).where(Model.workload_id == workload_id, Model.name == model_name)
        )
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

        # 6. Save Local Artifact
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

        # 7. Real MLflow Tracking Run & Model Registry
        experiment_name = f"nuvorix-{workload.name}"
        mlflow.set_experiment(experiment_name)
        mlflow_run_id = None
        mlflow_artifact_uri = None

        try:
            with mlflow.start_run(run_name=f"{model_name}-{version_str}") as run:
                mlflow_run_id = run.info.run_id
                mlflow.log_params(parameters)
                mlflow.log_metrics(metrics)
                mlflow.set_tag("nuvorix.workload_id", workload_id)
                mlflow.set_tag("nuvorix.model_name", model_name)
                mlflow.set_tag("nuvorix.version", version_str)
                mlflow.sklearn.log_model(regressor, name="model")
                mlflow_artifact_uri = run.info.artifact_uri
        except Exception as e:
            logger.warning("MLflow run logging fallback: %s", e)

        # 8. Register in MLflow Model Registry
        mlflow_model_version = None
        if mlflow_run_id and mlflow_artifact_uri:
            try:
                client = mlflow.tracking.MlflowClient()
                try:
                    client.create_registered_model(model_name)
                except Exception as reg_err:
                    logger.debug("Model %s may already be registered: %s", model_name, reg_err)
                mv = client.create_model_version(
                    name=model_name,
                    source=f"{mlflow_artifact_uri}/model",
                    run_id=mlflow_run_id,
                    tags={
                        "version": version_str,
                        "workload_id": workload_id,
                        "stage": "registered",
                    },
                )
                mlflow_model_version = mv.version
            except Exception as e:
                logger.warning("MLflow Model Registry registration fallback: %s", e)

        if mlflow_run_id:
            parameters["mlflow_run_id"] = mlflow_run_id
            parameters["mlflow_experiment"] = experiment_name
            parameters["mlflow_artifact_uri"] = mlflow_artifact_uri
            parameters["mlflow_model_version"] = mlflow_model_version

        # 9. Create ModelVersion
        version_entity = ModelVersion(
            model_id=model_entity.id,
            version=version_str,
            artifact_uri=artifact_path,
            metrics_json=metrics,
            parameters_json=parameters,
            status="registered",
        )
        db.add(version_entity)

        # 10. Record Audit
        audit = AuditEvent(
            organization_id="org-demo-nuvorix",
            user_id=user_id,
            action="models:train",
            resource_type="model_version",
            resource_id=version_entity.id,
            metadata_json={
                "model": model_name,
                "version": version_str,
                "metrics": metrics,
                "mlflow_run_id": mlflow_run_id,
            },
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
            "mlflow_run_id": mlflow_run_id,
            "mlflow_model_version": mlflow_model_version,
        }

    @classmethod
    async def promote_version(
        cls,
        db: AsyncSession,
        version_id: str,
        target_env: str = "staging",
        user_id: str = "usr-demo-admin",
    ) -> dict[str, Any]:
        cls._init_mlflow()

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

        # Update in MLflow Model Registry & runs
        if isinstance(version_entity.parameters_json, dict):
            mlflow_run_id = version_entity.parameters_json.get("mlflow_run_id")
            mlflow_mv = version_entity.parameters_json.get("mlflow_model_version")
            try:
                client = mlflow.tracking.MlflowClient()
                if mlflow_run_id:
                    client.set_tag(mlflow_run_id, "nuvorix.stage", target_env)
                if mlflow_mv:
                    client.set_model_version_tag(model.name, str(mlflow_mv), "stage", target_env)
                    if target_env == "production":
                        client.set_registered_model_alias(model.name, "production", str(mlflow_mv))
                    elif target_env == "staging":
                        client.set_registered_model_alias(model.name, "staging", str(mlflow_mv))
            except Exception as e:
                logger.warning("MLflow Model Registry transition fallback: %s", e)

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

    @classmethod
    def get_runs_for_workload(cls, workload_name: str) -> list[dict[str, Any]]:
        cls._init_mlflow()
        try:
            experiment_name = f"nuvorix-{workload_name}"
            exp = mlflow.get_experiment_by_name(experiment_name)
            if not exp:
                return []
            runs = mlflow.search_runs(experiment_ids=[exp.experiment_id], max_results=20)
            if runs.empty:
                return []
            results = []
            for _, r in runs.iterrows():
                results.append(
                    {
                        "run_id": r.get("run_id"),
                        "status": r.get("status"),
                        "start_time": str(r.get("start_time")),
                        "metrics": {
                            col.replace("metrics.", ""): r[col]
                            for col in runs.columns
                            if col.startswith("metrics.") and not np.isnan(r[col])
                        },
                        "params": {
                            col.replace("params.", ""): r[col]
                            for col in runs.columns
                            if col.startswith("params.")
                        },
                    }
                )
            return results
        except Exception as e:
            logger.warning("MLflow search runs fallback: %s", e)
            return []

    @classmethod
    def get_registered_models_from_mlflow(cls) -> list[dict[str, Any]]:
        cls._init_mlflow()
        try:
            client = mlflow.tracking.MlflowClient()
            reg_models = client.search_registered_models()
            results = []
            for m in reg_models:
                results.append(
                    {
                        "name": m.name,
                        "versions_count": len(m.latest_versions),
                        "latest_versions": [
                            {
                                "version": v.version,
                                "stage": getattr(v, "current_stage", "none"),
                                "run_id": v.run_id,
                            }
                            for v in m.latest_versions
                        ],
                        "aliases": dict(m.aliases) if hasattr(m, "aliases") and m.aliases else {},
                    }
                )
            return results
        except Exception as e:
            logger.warning("MLflow search registered models fallback: %s", e)
            return []
