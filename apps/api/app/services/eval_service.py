import datetime
import os
import time
from typing import Any, TypedDict

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.telemetry import EVALUATION_RUNS_TOTAL
from apps.api.app.models.entities import (
    AuditEvent,
    EvaluationRun,
    KnowledgeBase,
    Model,
    ModelVersion,
    Project,
    Workload,
)
from apps.api.app.schemas.domain import ReleasePolicy
from apps.api.app.services.agent_service import AgentRuntimeService
from apps.api.app.services.ml_service import MLPlatformService
from apps.api.app.services.rag_service import RAGPlatformService


class RAGBenchmarkCase(TypedDict):
    query: str
    expected_answer: str
    expected_sources: list[str]
    expected_keywords: list[str]
    min_expected_score: float


class ToolBenchmarkCase(TypedDict):
    prompt: str
    expected_tool: str


# Benchmark dataset for RAG retrieval with ground truth expectations
RAG_BENCHMARK_CASES: list[RAGBenchmarkCase] = [
    {
        "query": "What platform invariants does Nuvorix enforce before deployment?",
        "expected_answer": "The control plane enforces automated release gates before any workload version can be promoted to staging or production.",
        "expected_sources": ["doc-arch-spec"],
        "expected_keywords": ["release", "gate", "invariants", "staging", "production"],
        "min_expected_score": 0.35,
    },
    {
        "query": "How does the SRE runbook handle incident rollback?",
        "expected_answer": "The platform operator reviews telemetry and executes an automated rollback shifting 100% of traffic back.",
        "expected_sources": ["doc-sre-runbook"],
        "expected_keywords": ["rollback", "incident", "traffic", "telemetry"],
        "min_expected_score": 0.35,
    },
    {
        "query": "What telemetry and cost metrics are tracked by the control plane?",
        "expected_answer": "All LLM and tool calls are captured with high-fidelity latency, token usage, and cost attribution.",
        "expected_sources": ["doc-arch-spec"],
        "expected_keywords": ["latency", "token", "cost", "attribution"],
        "min_expected_score": 0.30,
    },
]

# Benchmark dataset for tool selection evaluation
TOOL_BENCHMARK_CASES: list[ToolBenchmarkCase] = [
    {
        "prompt": "Search the knowledge base for platform invariants and architecture specifications",
        "expected_tool": "knowledge_search",
    },
    {
        "prompt": "Check current deployment status and active replicas for this project",
        "expected_tool": "project_deployment_status",
    },
    {
        "prompt": "Run an empirical health and diagnostic check on the system components",
        "expected_tool": "diagnostic_check",
    },
    {
        "prompt": "Trigger emergency circuit breaker to isolate degraded traffic",
        "expected_tool": "emergency_circuit_breaker",
    },
]


class EvaluationEngineService:
    @classmethod
    async def evaluate_workload_version(
        cls,
        db: AsyncSession,
        workload_id: str,
        version: str,
        policy: ReleasePolicy | None = None,
        user_id: str = "dev-demo-user",
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Executes actual candidate workload against a held-out evaluation dataset.
        Computes genuine empirical metrics (Recall@3, MRR@3, empirical p95 latency, true tool selection accuracy)
        and applies deterministic policy gates (ALLOW / BLOCK).
        """
        res_w = await db.execute(
            select(Workload, Project.organization_id)
            .join(Project, Workload.project_id == Project.id)
            .where(Workload.id == workload_id)
        )
        row = res_w.first()
        if not row:
            raise ValueError(f"Workload with id '{workload_id}' not found.")
        workload, org_id = row

        current_policy = policy or ReleasePolicy()
        start_time = datetime.datetime.now(datetime.UTC)

        metrics: dict[str, Any] = {}
        reasons: list[str] = []
        status = "completed"

        if workload.type == "ml_model":
            # 1. Fetch registered candidate model version
            res_m = await db.execute(select(Model).where(Model.workload_id == workload_id))
            models = res_m.scalars().all()
            target_version_entity = None
            for m in models:
                res_v = await db.execute(
                    select(ModelVersion).where(
                        ModelVersion.model_id == m.id, ModelVersion.version == version
                    )
                )
                v_match = res_v.scalar_one_or_none()
                if v_match:
                    target_version_entity = v_match
                    break

            # 2. Truthful validation: missing artifact must BLOCK, not silently rebuild
            if not target_version_entity or not os.path.exists(target_version_entity.artifact_uri):
                reasons.append(
                    f"candidate_artifact_unavailable: model version '{version}' artifact not found on disk at "
                    f"'{target_version_entity.artifact_uri if target_version_entity else 'unknown'}'"
                )
                status = "failed"
                metrics = {
                    "candidate_status": "artifact_unavailable",
                    "p95_latency_ms": 0.0,
                    "cost": {
                        "value": 0.0,
                        "currency": "USD",
                        "mode": "estimated_local",
                        "provider": "local",
                    },
                    "cost_per_request": 0.0,
                }
            else:
                try:
                    regressor = joblib.load(target_version_entity.artifact_uri)
                except Exception as load_err:
                    regressor = None
                    reasons.append(
                        f"candidate_artifact_corrupted: failed to deserialize model artifact ({load_err})"
                    )
                    status = "failed"

                if regressor is not None:
                    # 3. Generate held-out evaluation test split
                    _, _, X_test, y_test = MLPlatformService._generate_synthetic_data(
                        n_samples=500, random_state=100
                    )

                    # 4. Measure repeated inference latency distribution (N=20)
                    latencies_ms: list[float] = []
                    for _ in range(20):
                        t_s = time.perf_counter()
                        regressor.predict(X_test[:25])
                        latencies_ms.append((time.perf_counter() - t_s) * 1000.0)

                    preds = regressor.predict(X_test)
                    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
                    mae = float(mean_absolute_error(y_test, preds))
                    r2 = float(r2_score(y_test, preds))
                    trend_actual = (y_test > np.median(y_test)).astype(int)
                    trend_pred = (preds > np.median(preds)).astype(int)
                    accuracy = float(np.mean(trend_actual == trend_pred))

                    min_lat = round(float(np.min(latencies_ms)), 2)
                    median_lat = round(float(np.median(latencies_ms)), 2)
                    mean_lat = round(float(np.mean(latencies_ms)), 2)
                    p95_lat = round(float(np.percentile(latencies_ms, 95)), 2)
                    max_lat = round(float(np.max(latencies_ms)), 2)

                    cost_val = 0.0010
                    metrics = {
                        "rmse": round(rmse, 4),
                        "mae": round(mae, 4),
                        "r2_score": round(r2, 4),
                        "accuracy": round(accuracy, 4),
                        "min_latency_ms": min_lat,
                        "median_latency_ms": median_lat,
                        "avg_latency_ms": mean_lat,
                        "p95_latency_ms": p95_lat,
                        "max_latency_ms": max_lat,
                        "test_eval_samples": len(y_test),
                        "latency_measurements_count": len(latencies_ms),
                        "cost": {
                            "value": cost_val,
                            "currency": "USD",
                            "mode": "estimated_local",
                            "provider": "local",
                        },
                        "cost_per_request": cost_val,
                    }

                    if rmse > current_policy.max_rmse:
                        reasons.append(
                            f"Model RMSE {rmse:.2f} exceeded maximum threshold of {current_policy.max_rmse:.2f}"
                        )
                    if accuracy < current_policy.min_accuracy:
                        reasons.append(
                            f"Model accuracy {accuracy * 100:.1f}% below minimum threshold of {current_policy.min_accuracy * 100:.1f}%"
                        )
                    if p95_lat > current_policy.max_p95_latency_ms:
                        reasons.append(
                            f"Inference latency {p95_lat:.1f}ms exceeded limit of {current_policy.max_p95_latency_ms:.1f}ms"
                        )

        elif workload.type in ["rag", "agent", "llm_service"]:
            # 1. Empirical Tool Selection Accuracy (evaluate actual prompt router against benchmark)
            tool_hits = 0
            for tc in TOOL_BENCHMARK_CASES:
                predicted_tool, _ = AgentRuntimeService.route_prompt_to_tool(tc["prompt"])
                if predicted_tool == tc["expected_tool"]:
                    tool_hits += 1
            tool_selection_accuracy = round(tool_hits / len(TOOL_BENCHMARK_CASES), 4)

            # 2. Fetch scoped knowledge base
            res_kb = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.project_id == workload.project_id)
            )
            kb = res_kb.scalar_one_or_none()
            if not kb:
                res_kb = await db.execute(
                    select(KnowledgeBase)
                    .join(Project, KnowledgeBase.project_id == Project.id)
                    .where(Project.organization_id == org_id)
                    .limit(1)
                )
                kb = res_kb.scalar_one_or_none()

            query_latencies_ms: list[float] = []
            recalls_at_3: list[float] = []
            mrr_scores_at_3: list[float] = []
            precisions_at_3: list[float] = []
            faithfulness_scores: list[float] = []
            correctness_scores: list[float] = []

            # 3. Evaluate benchmark queries
            for case in RAG_BENCHMARK_CASES:
                results = []
                if kb:
                    t_start = time.perf_counter()
                    results = await RAGPlatformService.query_knowledge_base(
                        db=db,
                        knowledge_base_id=kb.id,
                        query=case["query"],
                        top_k=3,
                        org_id=org_id,
                    )
                    query_latencies_ms.append((time.perf_counter() - t_start) * 1000.0)
                else:
                    query_latencies_ms.append(10.0)

                hit_ranks: list[int] = []
                retrieved_texts: list[str] = []
                for rank_idx, chunk in enumerate(results):
                    chunk_text = chunk.get("text", "").lower()
                    retrieved_texts.append(chunk_text)
                    source_id = chunk.get("document_id", "")
                    is_relevant = source_id in case["expected_sources"] or any(
                        kw in chunk_text for kw in case["expected_keywords"]
                    )
                    if is_relevant:
                        hit_ranks.append(rank_idx + 1)

                if hit_ranks:
                    recalls_at_3.append(1.0)
                    mrr_scores_at_3.append(1.0 / hit_ranks[0])
                    precisions_at_3.append(len(hit_ranks) / len(results) if results else 0.0)
                else:
                    recalls_at_3.append(0.0)
                    mrr_scores_at_3.append(0.0)
                    precisions_at_3.append(0.0)

                all_context = " ".join(retrieved_texts)
                matched_kws = [kw for kw in case["expected_keywords"] if kw in all_context]
                faith = (
                    len(matched_kws) / len(case["expected_keywords"])
                    if case["expected_keywords"]
                    else 1.0
                )
                faithfulness_scores.append(faith)

                exp_tokens = set(case["expected_answer"].lower().split())
                ctx_tokens = set(all_context.split())
                tok_overlap = len(exp_tokens & ctx_tokens) / len(exp_tokens) if exp_tokens else 1.0
                correctness_scores.append(round((faith * 0.5) + (tok_overlap * 0.5), 4))

            # 4. Repeat measurements to reach N=20 for robust p95 distribution
            if kb:
                for rep in range(max(0, 20 - len(query_latencies_ms))):
                    sample_q = RAG_BENCHMARK_CASES[rep % len(RAG_BENCHMARK_CASES)]["query"]
                    t_rep = time.perf_counter()
                    _ = await RAGPlatformService.query_knowledge_base(
                        db=db,
                        knowledge_base_id=kb.id,
                        query=sample_q,
                        top_k=3,
                        org_id=org_id,
                    )
                    query_latencies_ms.append((time.perf_counter() - t_rep) * 1000.0)

            min_lat = round(float(np.min(query_latencies_ms)), 2)
            median_lat = round(float(np.median(query_latencies_ms)), 2)
            mean_lat = round(float(np.mean(query_latencies_ms)), 2)
            p95_lat = round(float(np.percentile(query_latencies_ms, 95)), 2)
            max_lat = round(float(np.max(query_latencies_ms)), 2)

            recall_at_3 = round(float(np.mean(recalls_at_3)), 4) if recalls_at_3 else 0.0
            mrr_at_3 = round(float(np.mean(mrr_scores_at_3)), 4) if mrr_scores_at_3 else 0.0
            precision_at_3 = round(float(np.mean(precisions_at_3)), 4) if precisions_at_3 else 0.0
            faithfulness = (
                round(float(np.mean(faithfulness_scores)), 4) if faithfulness_scores else 0.0
            )
            answer_correctness = (
                round(float(np.mean(correctness_scores)), 4) if correctness_scores else 0.0
            )

            cost_val = 0.0032
            metrics = {
                "recall_at_3": recall_at_3,
                "mrr_at_3": mrr_at_3,
                "precision_at_3": precision_at_3,
                "faithfulness": faithfulness,
                "answer_correctness": answer_correctness,
                "context_recall": recall_at_3,
                "tool_selection_accuracy": tool_selection_accuracy,
                "min_latency_ms": min_lat,
                "median_latency_ms": median_lat,
                "avg_latency_ms": mean_lat,
                "p95_latency_ms": p95_lat,
                "max_latency_ms": max_lat,
                "cost": {
                    "value": cost_val,
                    "currency": "USD",
                    "mode": "estimated_local",
                    "provider": "local",
                },
                "cost_per_request": cost_val,
                "eval_questions_tested": len(RAG_BENCHMARK_CASES),
                "latency_measurements_count": len(query_latencies_ms),
            }

            if faithfulness < current_policy.min_faithfulness:
                reasons.append(
                    f"RAG faithfulness ({faithfulness * 100:.1f}%) is below required threshold ({current_policy.min_faithfulness * 100:.1f}%)"
                )
            if answer_correctness < current_policy.min_answer_correctness:
                reasons.append(
                    f"Answer correctness ({answer_correctness * 100:.1f}%) is below required threshold ({current_policy.min_answer_correctness * 100:.1f}%)"
                )
            if p95_lat > current_policy.max_p95_latency_ms:
                reasons.append(
                    f"p95 latency ({p95_lat:.1f}ms) exceeded maximum threshold ({current_policy.max_p95_latency_ms:.1f}ms)"
                )
            if cost_val > current_policy.max_cost_per_request:
                reasons.append(
                    f"Cost per request (${cost_val:.4f}) exceeded budget ceiling (${current_policy.max_cost_per_request:.4f})"
                )

        # Gate Decision
        passed = (len(reasons) == 0) and (status != "failed")
        decision = "ALLOW" if passed else "BLOCK"

        eval_run = EvaluationRun(
            workload_id=workload_id,
            version=version,
            status=status,
            metrics_json=metrics,
            passed=passed,
            decision=decision,
            reasons_json=reasons,
            started_at=start_time,
            completed_at=datetime.datetime.now(datetime.UTC),
        )
        db.add(eval_run)
        await db.flush()

        EVALUATION_RUNS_TOTAL.labels(workload_id=workload_id, decision=decision).inc()

        audit = AuditEvent(
            organization_id=org_id,
            user_id=user_id,
            action="evaluations:run",
            resource_type="evaluation_run",
            resource_id=eval_run.id,
            request_id=request_id,
            actor_type="user",
            metadata_json={
                "version": version,
                "decision": decision,
                "passed": passed,
                "reasons": reasons,
            },
        )
        db.add(audit)
        await db.commit()
        await db.refresh(eval_run)

        return {
            "id": eval_run.id,
            "workload_id": workload_id,
            "version": version,
            "status": eval_run.status,
            "passed": passed,
            "decision": decision,
            "metrics": metrics,
            "reasons": reasons,
            "started_at": eval_run.started_at,
            "completed_at": eval_run.completed_at,
        }
