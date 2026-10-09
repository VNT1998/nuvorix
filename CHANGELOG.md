# Changelog

All notable changes to the Nuvorix platform are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-10-09

### Added
- **Multi-Tenant Control Plane**: FastAPI async application with PostgreSQL/SQLite persistence, OpenTelemetry request tracing, and Prometheus metrics export.
- **Automated Quality Gates**: Evaluation engine calculating empirical RAG metrics (Recall@3, MRR@3, faithfulness, correctness) and ML model metrics (RMSE, accuracy, p95 latency) with automated ALLOW/BLOCK policy gating.
- **Production Gate Enforcement**: Strict blocking of production deployments unless candidate evaluations are completed with ALLOW decision; break-glass bypass with audit logging.
- **Stateful Agent Runtime**: LangGraph StateGraph orchestration loop (`planner -> tool_executor -> synthesizer`) with multi-tenant MCP tool permissions and stateful logical circuit breakers.
- **LLM Gateway & FinOps**: Provider-agnostic routing (OpenAI, Anthropic, Gemini, Ollama, local), centralized token pricing catalog, and fail-closed security in production.
- **React 19 Web Console**: Modern, professional white/slate interface built with Vite, TypeScript, Tailwind CSS, and Lucide icons across 10 functional studio views.
- **Python SDK & CLI**: Dedicated client library (`nuvorix`) and command-line interface (`nuvorix_cli`) for programmatic workloads, evaluations, and rollouts.
- **Cloud-Native Infrastructure**: Terraform environments (`dev`), Helm charts, and Docker Compose configurations with healthcheck probes.
- **Automated Verification Suites**: Comprehensive pytest regression suite covering security tenancy, tool authorization, MLflow tracking, and deployment state invariants.

### Security Hardening
- Enforced cryptographic token validation and database-backed API key hashes (`nvx_`) with constant-time comparison.
- Prohibited development header authentication fallbacks in production environments.
- Enforced composite uniqueness constraints `(organization_id, endpoint, key)` on idempotency keys.
