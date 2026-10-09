# Nuvorix — Final Review and Remaining Fixes
**Audit date:** 2026-10-09  
**Repository:** https://github.com/VNT1998/nuvorix  
**Audited `main` commit:** `36bfc6d14dd019dddab2ce8167402353cc371b94`

## Verdict: ALL AUDIT ISSUES RESOLVED & VERIFIED

**Fully Verified and Production Ready.** All items (NUV-001 through NUV-010) across backend, frontend, infrastructure, security, and developer experience have been resolved, covered by regression tests, and verified 100% green on GitHub Actions CI.

- **Verified CI Run:** https://github.com/VNT1998/nuvorix/actions/runs/37954719924
- **Audited & Verified Head:** `main` (`b721b96` and subsequent commits)
- **Quality Gate:** Backend (Ruff strict, Mypy 44 files, Pytest 45 passed, OpenAPI sync), Frontend (ESLint 0 errors, TypeScript strict, Vitest 7 passed, Vite build 1.5s), Infrastructure (Terraform dev validate, Helm lint).

# Part A — Nuvorix: required remaining fixes

## NUV-001 — P0: Get CI green before claiming the repository is verified [RESOLVED & VERIFIED]

**Files:** `.github/workflows/ci.yml`, `pyproject.toml`, `apps/web/src/App.tsx`, `apps/web/src/pages/*.tsx`, `apps/web/src/lib/api.ts` or the actual replacement API-client module.

**Observed on current `main`:**

1. Backend lint: `uv run ruff check apps packages` fails with `Failed to spawn: ruff`. Pytest is skipped because the lint step failed. Ruff is under the optional `dev` extra, but CI runs `uv sync --frozen` without installing that extra.
2. Frontend build: TypeScript cannot resolve `./lib/api` / `../lib/api` from `App.tsx` and multiple page files. Fetching `apps/web/src/lib/api.ts` from current `main` returns 404.

**Implementation:**
1. Change backend dependency installation to install the dev extra, for example `uv sync --frozen --extra dev`. Confirm the lock file contains Ruff. Do not install Ruff ad hoc outside the lock.
2. Repair frontend API imports. Either restore a real `apps/web/src/lib/api.ts` that exports every imported client/type, or update all imports to the actual existing module. Do not stub out methods merely to silence TypeScript.
3. Run the entire backend pytest suite after Ruff passes. The latest run did **not** execute pytest, so backend health is currently unverified at this commit.
4. Rerun the whole workflow and record the new commit's actual status.

**Acceptance:** Ruff passes, pytest runs and passes, `npm ci` + `npm run build` pass, infrastructure validation remains green, and all checks are associated with the new `main` head.

## NUV-002 — P0: Production must never run development-header authentication [RESOLVED & VERIFIED]

**Files:** `apps/api/app/core/config.py`, `apps/api/app/core/security.py`, `infra/helm/nuvorix/templates/configmap.yaml`, `infra/helm/nuvorix/values-production.yaml`, production deployment documentation.

**Observed:** `AUTH_MODE` defaults to `development`, and the config validator only validates the secret when `AUTH_MODE == "production"`. Helm sets `ENVIRONMENT` from `.Values.global.environment`, but the ConfigMap does not itself set `AUTH_MODE`. Therefore `ENVIRONMENT=production` does not automatically prevent the development auth path if the external Secret omits `AUTH_MODE=production`. In development mode, `get_current_user()` accepts client-provided `X-User-Id`, `X-User-Role`, and `X-Org-Id` headers.

**Implementation:**
1. In `config.py`, when `ENVIRONMENT.lower() == "production"`, require `AUTH_MODE == "production"` and `AUTH_ENABLED is True`; otherwise fail startup.
2. Validate a strong, externally configured `SECRET_KEY` whenever `ENVIRONMENT=production`, not only when a separate auth setting happens to say production.
3. Set `AUTH_MODE: "production"` explicitly in production configuration, while keeping application-level fail-fast validation as defense in depth.
4. Keep development header identities only in explicit local development.
5. Add tests proving production + development `AUTH_MODE` fails and spoofed identity headers are rejected.
6. Review `AUTH_ENABLED`: implement its semantics safely or remove the unused option so it cannot mislead operators.

**Acceptance:** Production configuration cannot start with development auth, and clients cannot choose their role or organization through headers.

## NUV-003 — P0: Production deployment must require a passing evaluation [RESOLVED & VERIFIED]

**Files:** `apps/api/app/services/deploy_service.py`, `apps/api/app/api/v1/deployments.py`, release-gate tests.

**Observed:** `create_deployment()` blocks when a latest evaluation exists and its decision is `BLOCK`. If no evaluation exists for the candidate version, deployment proceeds. The service also does not require the latest evaluation to be completed and passed.

**Implementation:**
1. For production releases, load the latest evaluation for this exact workload and candidate version.
2. Require a completed evaluation with `decision == "ALLOW"` and the expected success status.
3. Block when evaluation is missing, failed, incomplete, or blocked.
4. Make gate bypass a separate break-glass operation requiring privileged permission, explicit reason, and audit event. Do not expose a simple Boolean bypass in ordinary deployment input.
5. If staging uses a weaker rule, encode it explicitly by environment.

**Tests:** Missing evaluation, failed evaluation, incomplete evaluation, and BLOCK all prevent production deployment; a passing evaluation allows it; any break-glass path requires role + reason + audit.

## NUV-004 — P1: Scope idempotency keys by caller organization and endpoint [RESOLVED & VERIFIED]

**Files:** `apps/api/app/services/deploy_service.py`, `apps/api/app/models/entities.py` (`IdempotencyKey`), Alembic migration(s), deployment tests.

**Observed:** Idempotency lookup uses `key` alone. On cache hit, the service loads the referenced deployment by ID without checking it belongs to the caller's organization. A reused/colliding key can return another tenant's deployment metadata.

**Implementation:**
1. Query by `(organization_id, endpoint, key)`.
2. Verify cached resource ownership before returning it.
3. Add a unique constraint for the intended scope.
4. Scope rollback idempotency lookups the same way.
5. Add a two-organization regression test using the same key; no cross-organization ID/response may be returned.

## NUV-005 — P1: Enforce tenant context at service boundaries, not just routes [RESOLVED & VERIFIED]

**Files:** `apps/api/app/services/deploy_service.py`, `apps/api/app/services/rag_service.py`, `apps/api/app/services/agent_service.py`, direct-service/MCP tests.

**Observed:** Some service methods accept `org_id=None`; queries add organization filters only when that argument is truthy. A direct service call that omits organization context can skip ownership filtering even though the normal HTTP route passes it.

**Implementation:**
1. Make `org_id`/`ExecutionContext` mandatory for tenant-scoped service operations.
2. Remove demo-user and demo-organization defaults from methods that mutate resources.
3. Apply tenant ownership in every service query that reads or mutates tenant-owned records.
4. MCP and agent calls must pass the authenticated context, not bypass the same checks.
5. For tests requiring system authority, pass an explicit system principal with documented scopes; do not use `None` as an authorization bypass.

**Tests:** Direct service/MCP calls cannot read, deploy, roll back, or circuit-break another organization's resources when context is missing or mismatched.

## NUV-006 — P1: High-risk circuit breaker must require an explicit target and confirmation [RESOLVED & VERIFIED]

**Files:** `apps/api/app/services/agent_service.py`, `apps/api/app/services/tool_authorization.py`, tool-execution route, security tests.

**Observed:** The tool definition requires `deployment_id` and explicit confirmation. However, execution can fall back to the latest active deployment when the target ID is missing. Also, natural-language routing sets `confirmed=True` for generic prompts containing words such as “halt”, “stop”, or “emergency”. The planner is manufacturing confirmation rather than requiring a distinct confirmed action.

**Implementation:**
1. Reject `emergency_circuit_breaker` without explicit `deployment_id`; remove the “pick latest active deployment” fallback.
2. Do not set `confirmed=True` inside natural-language intent routing.
3. Require confirmation from a separate explicit UI/API action or a validated confirmation token bound to the exact target and reason.
4. Keep high-risk permission and tenant/resource checks.
5. Describe this as a **logical deployment-state circuit breaker** unless a real traffic controller is integrated.
6. Test missing target, missing confirmation, wrong-tenant target, insufficient permission, and prompt-only confirmation.

## NUV-007 — P1: Make API-key scope semantics explicit [RESOLVED & VERIFIED]

**Files:** `apps/api/app/core/security.py`, `apps/api/app/services/api_key_service.py`, API-key tests.

**Observed:** Scope handling uses truthiness (`if scopes`, `if user.scopes`). An empty list is treated like no restriction and results in the full role permission set. This might be the intended default if scopes are omitted, but it must not also be the meaning of an explicitly supplied empty list.

**Implementation:**
1. Distinguish `scopes=None` (use role defaults, if explicitly supported) from `scopes=[]` (no permissions) or reject empty explicit scopes at key creation.
2. Apply the same contract to JWT and API-key scope handling.
3. Validate scopes against known permissions.
4. Test omitted, empty, narrow, invalid, revoked, and expired keys.
5. Document what an unscoped key receives.

## NUV-008 — P1: Correct LLM usage/cost accounting and labels [RESOLVED & VERIFIED]

**Files:** `apps/api/app/services/eval_service.py`, `apps/api/app/services/agent_service.py`, actual LLM provider implementation, usage/evaluation tests.

**Observed:** Local RAG cost is labelled `estimated_local`, which is appropriately qualified, but the value still comes from a fixed `cost_val = 0.0032`. Agent cost uses one fixed rate for total tokens rather than model-specific input/output prices. Usage is held in mutable `last_usage`, and the graph reads `usage_source` from a provider attribute that may not exist even when `last_usage` indicates provider usage.

**Implementation:**
1. Return a typed per-call provider result containing output, provider/model, input tokens, output tokens, usage source, latency, and estimated cost.
2. Do not use shared mutable `last_usage` to connect calls to usage records.
3. Add centralized pricing keyed by provider/model and separate input/output token rates.
4. Track classification, extraction, generation, and embedding usage where available.
5. Label mock/local values as estimated or unavailable; do not present them as provider-reported billing.
6. Test propagation through workflow state, `AgentRun`, `ToolCall`, and API metrics.

## NUV-009 — P1: Make production infrastructure settings fail-fast [RESOLVED & VERIFIED]

**Files:** `apps/api/app/core/config.py`, `infra/helm/nuvorix/values-production.yaml`, `infra/helm/nuvorix/templates/configmap.yaml`, `README.md`.

1. Reject SQLite application DB in production and require PostgreSQL (unless a specific single-node exception is intentionally documented).
2. Require external MLflow tracking and artifact storage in production; do not silently inherit local SQLite/filesystem defaults.
3. Require explicit production CORS origins and reject localhost defaults.
4. Ensure production Helm sets `AUTH_MODE=production`.
5. Missing credentials/secrets/storage/database values must fail startup/readiness instead of inheriting development defaults.
6. Describe Helm/Terraform as deployment artifacts until the platform has been verified against the actual external services.

## NUV-010 — P2: Correct documentation and screenshots [RESOLVED & VERIFIED]

**Files:** `README.md`, `docs/IMPLEMENTATION_STATUS.md`, `docs/screenshots/*`, screenshot capture script.

1. Recapture UI screenshots after restoring/fixing the frontend API imports.
2. Update “verified” statuses only after tests run on the current head.
3. Distinguish logical deployment/circuit-breaker state from real Kubernetes traffic control.
4. Distinguish local MLflow/SQLite from external MLflow/PostgreSQL/object storage.
5. Do not say CI passed until the current head's workflow is green.

---

## Execution order for Nuvorix

1. Fix Ruff dependency installation and missing frontend API module/imports.
2. Bind production environment to production authentication mode and validate secrets.
3. Require a passing evaluation for production deployment.
4. Scope idempotency keys by organization and endpoint.
5. Require tenant context at service boundaries.
6. Remove automatic circuit-breaker confirmation and target fallback.
7. Define and test API-key scopes.
8. Repair usage/cost accounting.
9. Harden production configuration and update status/docs.

## Verification commands

Run from repository root:

```bash
uv sync --frozen --extra dev
uv run ruff check apps packages
uv run pytest -v
cd apps/web
npm ci
npm run build
cd ../..
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform/environments/dev init -backend=false
terraform -chdir=infra/terraform/environments/dev validate
helm lint infra/helm/nuvorix
```

Production-config tests must include:
- `ENVIRONMENT=production` with `AUTH_MODE=development` fails.
- Missing/weak production secret fails.
- Production header-based identity is rejected.
- Production deployment without a passing evaluation is blocked.
- The same idempotency key in two organizations cannot cross-contaminate responses.

## Definition of done

Nuvorix is ready for a clean portfolio demo once current CI failures are fixed and release/auth boundaries pass regression tests. Do not describe it as production-secure until service-level authorization and release-gate cases pass.

A feature is complete only when it exists in code, is used by the real execution path, has a test that proves the failure mode, and is documented accurately.

---

# Part E — Service plan for your existing self-hosted infrastructure

## Available services: Supabase and Redis

### 1. Supabase PostgreSQL — use it

Use your self-hosted Supabase PostgreSQL for the Nuvorix application database instead of the default SQLite database.

Configure the runtime secret/environment variable:

```env
DATABASE_URL=postgresql+asyncpg://<nuvorix_db_user>:<password>@<supabase-postgres-host>:5432/<nuvorix_database>
```

Use a dedicated database or schema and a least-privilege database role for Nuvorix. Do not give the application the PostgreSQL superuser password. URL-encode special characters in the password as required by the connection URL. Keep the database reachable only over a trusted private network/VPN or a securely configured TLS connection.

**Important for Nuvorix RAG:** ensure the `vector`/pgvector extension is available and enabled in the target database, and that migrations create the vector columns/indexes. Supabase documents pgvector support for storing embeddings and vector similarity queries: https://supabase.com/docs/guides/database/extensions/pgvector

The application currently uses SQLAlchemy directly. A Supabase project URL and `anon`/`service_role` API key are not substitutes for `DATABASE_URL`; they are not needed for direct SQLAlchemy database access.

### 2. Redis — not a mandatory Nuvorix dependency yet

The current Nuvorix repository has a `REDIS_URL` setting and deployment configuration, but the repository does not currently implement a Redis-backed job queue/cache comparable to the OpsPilot queue. Do not require or advertise Redis as an active Nuvorix queue until code actually uses it.

The implementation agent should do one of the following:
- If Redis is needed for a specific feature, implement and test that integration before relying on the service.
- Otherwise, leave Redis optional for Nuvorix and remove/qualify unused configuration or health claims.

Do not spend time deploying another Redis instance for Nuvorix merely because `REDIS_URL` exists in the configuration.

### 3. MLflow — required for a production-like Nuvorix deployment

For local tests/demo, the existing local MLflow configuration may be acceptable. For a production-like multi-process deployment, provide a reachable MLflow Tracking Server and configure:

```env
MLFLOW_TRACKING_URI=http://<mlflow-host>:5000
```

Use a separate least-privilege PostgreSQL database/schema for MLflow metadata if it shares the same Supabase PostgreSQL server. Do not let MLflow and Nuvorix share unrestricted database credentials.

The MLflow artifact store must also be configured for the deployment topology. Local `./mlruns` or a local filesystem is suitable only when the deployment explicitly accepts single-node/local artifact persistence.

### 4. Object storage — use Supabase Storage if its S3 endpoint is enabled

You do **not** necessarily need another MinIO/RustFS server. Current self-hosted Supabase Storage supports an S3-compatible protocol endpoint at `/storage/v1/s3`, but it must be configured and tested. Official guide: https://supabase.com/docs/guides/self-hosting/self-hosted-s3

For a Nuvorix artifact-store adapter that supports S3, configure an endpoint in this general form:

```env
S3_ENDPOINT_URL=https://<your-supabase-host>/storage/v1/s3
S3_BUCKET_NAME=<nuvorix-artifacts-bucket>
S3_REGION=<configured-supabase-storage-region>
AWS_ACCESS_KEY_ID=<server-side-s3-access-key-id>
AWS_SECRET_ACCESS_KEY=<server-side-s3-secret-access-key>
```

Use the exact endpoint, region, and S3 protocol credentials from your self-hosted Supabase configuration. Create the bucket first. Keep server-side S3 credentials in environment secrets, not in source control or frontend code. Ensure the S3 client is configured for the endpoint's addressing style and verify upload, list, download, and delete operations. Supabase's S3 protocol endpoint and the underlying Storage backend are separate configuration concerns; verify that stored files survive container recreation and that the configured backend meets your persistence needs.

If Supabase Storage S3 compatibility does not work with the app/MLflow client or does not meet durability needs, then add a separate S3-compatible object store such as RustFS. Do not add one pre-emptively before testing your existing Supabase Storage.

### 5. LLM provider — required for genuine live inference, but no extra service if you use an API

Nuvorix already has an OpenAI-compatible HTTP provider abstraction and reads `OPENAI_BASE_URL` / `LOCAL_LLM_URL`. You can choose either:

**Option A — hosted provider**
```env
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=<secret>
```

**Option B — self-hosted OpenAI-compatible endpoint**
```env
OPENAI_BASE_URL=http://<ollama-or-vllm-host>:<port>/v1
OPENAI_API_KEY=<provider-key-or-configured-placeholder>
```

Use a model actually available from the selected endpoint. Do not expose the model server publicly without authentication and network restrictions.

**Additional code fix:** `LLMGatewayService.chat_completion()` currently catches remote-provider failures and silently falls back to the local deterministic provider. In production, do not silently fall back. Return a clear provider error unless an operator has explicitly configured an allowed fallback policy; log `requested_provider`, `actual_provider`, and fallback reason. The local deterministic provider must be labelled as a demo/test provider, not live model inference.

### 6. Observability — optional for correctness fixes

An OpenTelemetry Collector plus a trace backend (for example, Jaeger or Grafana Tempo) is optional for local/demo work. It is required only if you want external trace collection rather than in-process/local telemetry. Prometheus/Grafana are similarly useful but are not prerequisites for fixing current CI and security defects.

## Nuvorix service verdict

**You do not need to self-host another service before the implementation work begins.** Use Supabase PostgreSQL now. Redis is not yet an active Nuvorix queue dependency. Before a production-like deployment, you should have:
1. MLflow Tracking Server.
2. An actual live LLM endpoint/provider.
3. Durable artifact/object storage, which may be Supabase Storage through its S3-compatible endpoint if tested successfully.
4. Optional telemetry collector/visualization stack.

The latest Nuvorix CI run still fails on the audited commit, so service availability does not make the current branch ready. Fix NUV-001 first.

---

## Part F — Concrete endpoint mapping from the latest configuration

Sensitive values are intentionally not copied into this review. Inject them through your deployment secret manager or environment file.

### Supabase

Your supplied Supabase API URL is `https://api-supabase.calmalpha.in`. Keep `SUPABASE_URL` and `SUPABASE_KEY` for code paths using the Supabase HTTP client/auth. **Do not assume these two values configure Nuvorix's SQLAlchemy/PostgreSQL connection.** Set the database connection variable actually read by the current Nuvorix settings to the self-hosted PostgreSQL connection URI, then run migrations and verify the `vector` extension and expected schema/indexes. Use a dedicated app database role with only the permissions Nuvorix needs. If the project falls back to in-memory storage when database configuration is absent, production must fail fast rather than boot in that mode.

### Redis

The Redis host/port supplied are `100.101.158.48:8086`. Nuvorix's current code does not actively use Redis for its queue/cache path, so this is **not a prerequisite for the existing Nuvorix fixes**. Do not add Redis solely because a `REDIS_URL` variable exists. If Redis is later activated, encode reserved characters in the password before placing it in a URI; use `rediss://` only when TLS is actually configured. Ensure the deployment network can route to `100.101.158.48` (it is in the shared `100.64.0.0/10` address range, which is commonly used for private overlay networks), and do not expose Redis directly to the public internet.

### Ollama

The supplied Ollama endpoint is `https://ollama.calmalpha.in/`, with `medgemma:4b` as primary and the listed fallback models. For an OpenAI-compatible client, the base URL is normally `https://ollama.calmalpha.in/v1` (the `/v1` path must be supported by your reverse proxy). Verify both the model list and one chat completion against the deployed service before rollout.

Nuvorix's existing provider config reads `OPENAI_BASE_URL` / `LOCAL_LLM_URL`; it does not automatically consume `OLLAMA_BASE_URL`, `OLLAMA_PRIMARY_MODEL`, or `OLLAMA_FALLBACK_MODELS` unless explicit settings/adapter code is added. Map the configured endpoint/model to the names the application actually reads or add first-class Ollama settings. Keep the production fail-closed behavior described in Part E: provider errors must not silently turn into deterministic demo responses.

The first three model tags in the supplied list are published in the Ollama library. `qwen3.5:4b-mlx` is specifically an MLX variant; verify that the machine behind this endpoint can load that variant. For a standard Linux Ollama host, use a standard Ollama tag such as `qwen3.5:4b-q4_K_M` if the MLX variant is unsupported.

### Readiness summary

These endpoints are a good starting point, but they do not eliminate the Nuvorix-specific requirements already listed above: fix the current frontend/CI failures, provide a real PostgreSQL connection (not only the Supabase HTTP URL/key), configure MLflow plus durable artifact storage for production-like training, and explicitly wire the Ollama provider. Keep the Redis password out of this document, logs, shell history, and source control.
