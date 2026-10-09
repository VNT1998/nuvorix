# ADR 0003: Strict Pre-Release Empirical Evaluation Gates and Break-Glass Bypass

## Status
Accepted

## Context
Deploying ML models and GenAI agents directly to production without empirical performance benchmarks introduces high risks of regression, hallucination, or performance degradation. Previous systems allowed bypasses or relied on subjective developer assertions.

## Decision
1. Candidate workload versions must be evaluated using real empirical benchmark datasets.
   - ML regression: Evaluates RMSE, accuracy, and repeated p95 latency distributions.
   - RAG & Agents: Evaluates Recall@3, MRR@3, faithfulness, and answer correctness against held-out benchmark questions.
2. The control plane release engine (`DeploymentPlatformService`) strictly blocks production deployment creation if candidate evaluations are missing, incomplete, or result in `BLOCK`.
3. An emergency break-glass override requires:
   - Caller possesses `deployments:bypass_gate` permission.
   - Explicit `bypass_gate=True` flag in the deployment request.
   - Non-empty `bypass_reason` explaining the operational necessity.
   - Automatic generation of a high-priority `deployments:break_glass_create` audit event.

## Consequences
- **Positive**: Zero unvetted releases reach production; complete auditability of all bypasses; mathematical guarantees on quality thresholds.
- **Negative**: Adds evaluation step time before deployment creation.
