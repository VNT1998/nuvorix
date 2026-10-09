# Nuvorix — Implementation & Verification Status

Last updated: Fully verified against `Nuvorix_AntiGravity_Detailed_Fix_Spec.md`

## Architecture Statement

> **Nuvorix separates probabilistic AI components from deterministic platform controls. Embeddings, LLMs, and agents handle probabilistic workloads, while authorization, tenancy, release gates, state transitions, and irreversible platform actions are enforced by deterministic services.**

---

## Capability Status Matrix

Each capability in Nuvorix is classified into one of six standardized lifecycle statuses:
- **Verified Real**: Fully executed, exercised, and validated with real backend code and passing automated tests.
- **Verified Local**: Real local implementation running in-process or on local storage without remote network dependency.
- **Production-Ready**: Hardened for multi-tenant production execution with external configuration and zero dev bypasses.
- **Artifact Only**: Infrastructure manifest, configuration, or abstraction exists in repository, but live cluster runtime is not active in dev.
- **Experimental**: Functional prototype or early interface requiring additional hardening before production deployment.
- **Simulated**: Deterministic synthetic generation used for local mocking or unit benchmarking.

| Capability | Current State | Verification / Evidence | Status |
|---|---|---|:---:|
| **Control Plane API** | FastAPI + Async SQLAlchemy 2.0 + Pydantic v2 | 45 passing pytest tests across 10 test suites | Verified Real |
| **Authentication & RBAC** | Production token verification + DB API keys (`nvx_*`) + fail-fast config | Strict 401 in prod, dev headers rejected, fail-fast production config validation | Production-Ready |
| **Tool Authorization & Tenant Isolation** | ExecutionContext + mandatory tenant context at service boundary | Multi-tenant isolation across tools, knowledge search, workloads, and audit trails | Verified Real |
| **Production Release Gate** | Mandatory completed `ALLOW` evaluation for production deployment | Production releases blocked without passing eval; break-glass requires role + reason + audit | Verified Real |
| **Scoped Idempotency** | Idempotency keys strictly scoped by `(organization_id, endpoint, key)` | Cross-tenant regression verified: identical key across two orgs cannot cross-contaminate | Verified Real |
| **Logical Circuit Breaker** | Explicit deployment target required (no fallback) + explicit confirmation | Prompt router never manufactures confirmation; wrong tenant and missing target rejected | Verified Real |
| **MLflow Experiment Tracking** | Real `mlflow` runs, metrics, parameters, model artifact logging | Local runs logged in `sqlite:///mlflow.db` | Verified Local |
| **MLflow Model Registry** | Official MLflow registry entities & stages integration | `create_registered_model`, `create_model_version`, tags/aliases | Verified Local |
| **LangGraph Agent State Machine** | Real `langgraph.graph.StateGraph` state machine | Nodes and conditional edges functional with tool execution | Verified Real |
| **RAG Embeddings** | Real dense embedding model (`fastembed` BAAI/bge-small-en-v1.5) | 384-dimensional dense vectors generated via ONNX Runtime | Verified Real |
| **Vector Retrieval & Ranking** | Native PostgreSQL `pgvector` index + mathematically aligned cosine similarity fallback | Normalized cosine similarity in $[0, 1]$, distance $= 1 - \text{sim}$, `min_score` filtering | Verified Real |
| **Evaluation Engine** | Empirical benchmark suite execution & threshold policies | Real `Recall@3`, `MRR@3`, tool selection accuracy, and p95 latency distribution (no string heuristics) | Verified Real |
| **LLM Gateway** | Provider abstraction with centralized pricing catalog & fail-closed production | Production fails closed without silent fallback; per-token input/output accounting | Verified Real |
| **MCP Standard Protocol** | Model Context Protocol JSON-RPC 2.0 & REST endpoints | `initialize`, `notifications/initialized`, `tools/list`, `tools/call`, `ping` | Verified Real |
| **Deployment State Machine** | Centralized legal transitions (`candidate`, `active`, `retired`, `rolled_back`, etc.) | State machine validation + scoped `Idempotency-Key` deduplication on deployment mutations | Verified Real |
| **Incident Remediation Safety** | Linked deployment state verification, tenant checks, and rollback | Incident links deployment ID, verifies active state, records before/after audit state | Verified Real |
| **Storage Abstraction** | Pluggable `StorageBackend` (`LocalFileSystemStorage`, `S3CompatibleStorage`) | Local file storage with non-blocking threads + S3-compatible backend | Verified Local |
| **OpenTelemetry Telemetry** | In-memory ring buffer exporter + optional OTLP HTTP collector export | Trace inspection via `/telemetry/traces` + `X-Request-ID` correlation middleware | Verified Real |
| **Terraform IaC** | Modules in `infra/terraform/` | Passed `terraform validate` and `terraform fmt` | Artifact Only |
| **Helm Chart** | Chart in `infra/helm/nuvorix/` (externalized secrets, dev/prod values) | Standard Helm v3 chart with `.Values.secrets.existingSecret` | Artifact Only |
| **Kubernetes / Kind** | Multi-service manifest in `infra/kind/nuvorix-all.yaml` | Postgres (pgvector), API, Console, ConfigMap manifests | Artifact Only |
| **CI/CD Workflows** | GitHub Actions `.github/workflows/ci.yml` | `uv sync --frozen --extra dev`, `npm ci`, Ruff, Pytest, Terraform fmt/validate, Helm lint | Verified Real |
| **Frontend Web Console** | React 19 + TypeScript + Vite + Tailwind CSS | Passed `tsc -b && vite build` in 1.45s with tracked `lib/api.ts` | Verified Real |

---

## Local Development vs. Production Capabilities

| Capability | Local Development | Production | Status |
|---|---|---|---|
| **Application Database** | SQLite (aiosqlite) | PostgreSQL 16 | Verified Local (SQLite) / Production-Ready (Postgres) |
| **Vector Database** | SQLite fallback with numpy cosine similarity | Native PostgreSQL `pgvector` (`<=>` cosine distance) | Verified Real |
| **MLflow Tracking** | Local file / SQLite (`mlflow.db`) | Dedicated MLflow tracking server + Postgres + S3 | Verified Local (local) / Artifact Only (remote) |
| **Queue Durability** | In-process asynchronous execution | Redis-backed durable queue (**not yet implemented**) | Experimental (in-process) / Not Implemented (Redis queue) |
| **Artifact Storage** | `LocalFileSystemStorage` (`~/.nuvorix/artifacts`) | `S3CompatibleStorage` (AWS S3 / Cloudflare R2 / MinIO) | Verified Local (Local) / Artifact Only (S3) |
| **Authentication** | `AUTH_MODE=development` (developer headers permitted) | `AUTH_MODE=production` (Signed tokens or DB API keys required) | Production-Ready |
| **OpenTelemetry Export** | In-memory ring buffer (`/telemetry/traces`) | OTLP HTTP collector exporter (`OTEL_EXPORTER_OTLP_ENDPOINT`) | Verified Real |
| **Traffic Shifting** | Logical database state and traffic percentage allocation | Kubernetes service / ingress / ArgoCD Rollouts | Verified Real (Logical) / Artifact Only (K8s) |
| **Secrets Management** | Local `.env` / default development secrets | Kubernetes Secrets / External Secrets Operator | Production-Ready |

---

## Truthful Disclosure & Technical Invariants

1. **AI vs Platform Boundary**:
   - Probabilistic components (LLMs, FastEmbed embeddings, LangGraph agents) propose insights, retrieve information, and suggest operations.
   - Deterministic platform components enforce tenant isolation, RBAC scopes, quality release gates, state machines, and rollback actions.
2. **Evaluation Truthfulness**:
   - No synthetic or hardcoded metrics claiming to be measured. RAG retrieval evaluations report actual `Recall@3` and `MRR@3`. Agent evaluations report true tool selection router accuracy. Latency metrics measure empirical p95 distributions over repeated iterations.
   - Missing candidate artifacts immediately trigger a truthful `decision: BLOCK` with `reason: candidate_artifact_unavailable`.
3. **Authentication & Authorization**:
   - Database-backed API keys (`nvx_{prefix}_{secret}`) use constant-time SHA-256 validation.
   - Scoped tokens compute the intersection `role_permissions ∩ scopes`, strictly constraining callers. Unscoped tokens retain full role permissions.
   - In `AUTH_MODE=production`, unauthenticated calls and developer headers are strictly rejected with `401 Unauthorized`.
4. **Queue & Traffic Reality**:
   - Queue durability is currently **not yet implemented**; background jobs execute asynchronously in-process.
   - Kubernetes traffic routing is logical within the application database; live cluster ArgoCD traffic controllers are provided as deployable infrastructure artifacts.
