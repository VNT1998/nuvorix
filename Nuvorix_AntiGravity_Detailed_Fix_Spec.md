# Nuvorix — Anti-Gravity Agent Fix & Hardening Specification

## Target repository

`VNT1998/nuvorix`

## Baseline reviewed

Current `main` branch, commit:

`696383dfae73d02b15d89556f664d2ae353783d4`

Commit message:

`feat: implement verified AI platform engineering architecture`

## Purpose

This document is the implementation contract for the Anti-Gravity coding agent.

The agent must use this document as a deterministic work order. It should not invent alternative architectures, skip difficult items, or add unrelated features before completing the required fixes.

The goal is to turn the current Nuvorix implementation into a **credible, internally consistent, secure, testable AI/ML platform engineering project**.

The most important principle is:

> Do not make the platform look more production-grade than it actually is. Make the existing behavior correct, secure, observable, and truthful.

---

# 1. EXECUTION RULES FOR THE CODING AGENT

## 1.1 Work in this order

Execute the work in this exact sequence:

1. Security and authentication hardening
2. Tenant/resource isolation at service and tool boundaries
3. Correct RAG vector score handling
4. Remove simulated operational outputs where they claim to represent real system state
5. Make high-risk remediation behavior stateful, authorized, audited, and idempotent
6. Correct evaluation semantics and remove fabricated metrics
7. Production-safe MLflow configuration
8. Production-safe Helm/Kubernetes configuration
9. OpenTelemetry export correctness
10. CI quality/security gates
11. Regression/adversarial tests
12. README and implementation-status truthfulness cleanup

Do not jump to P2 polish while P0 tests are failing.

---

# 2. NON-NEGOTIABLE ARCHITECTURAL RULES

The final implementation must obey these rules.

## Rule A — Authentication is never inferred from arbitrary headers

Development headers may exist only when explicitly running in development mode.

Production mode must require a real authenticated credential.

Never accept:

- arbitrary `nuvorix_sk_*` strings
- arbitrary `X-User-Role`
- arbitrary `X-Org-Id`
- arbitrary `X-User-Id`

as authentication in production.

---

## Rule B — Authorization must exist at the service boundary

A route-level authorization check is not enough.

Every service or tool capable of reading or mutating data must validate:

1. authenticated principal
2. organization / tenant ownership
3. resource ownership
4. required permission
5. risk classification
6. allowed state transition
7. idempotency requirements for side effects

---

## Rule C — An agent never receives implicit admin authority

Do not default any agent execution context to:

```python
role="admin"
```

Do not derive authorization from a boolean such as:

```python
allow_high_risk=True
```

A high-risk action must require a principal that actually has the required permission.

---

## Rule D — Database is authoritative for platform state

The application database is authoritative for logical platform state.

Do not return success unless the intended state transition really happened.

Do not return fake health, fake rollback, fake deployment, fake incident, or fake cost values.

---

## Rule E — Metrics must be measured or explicitly labeled synthetic

Never label a hardcoded number as:

- measured
- empirical
- real-time
- p95
- production latency
- actual cost

unless the implementation truly measures it.

---

## Rule F — Production configuration must not use SQLite for shared state

SQLite is acceptable for local development.

Production/multi-replica configuration must use PostgreSQL for application state and an external MLflow tracking server/backend.

---

# 3. P0-1 — FIX PRODUCTION AUTHENTICATION AND API KEYS

## Files

Primary:

- `apps/api/app/core/security.py`
- `apps/api/app/core/config.py`
- `apps/api/app/schemas/domain.py`

Tests:

- `apps/api/tests/test_security_tenancy_eval.py`
- create a dedicated `apps/api/tests/test_authentication_hardening.py`

Potential seed/config files:

- `apps/api/app/seed.py`
- `.env.example`
- any frontend auth helper that uses role headers

---

## Current problem

The current API-key logic effectively treats arbitrary values matching:

```text
nuvorix_sk_*
```

as valid admin credentials.

That is not acceptable.

The current production configuration also contains a hardcoded secret fallback.

---

## Required implementation

### Step 1 — Replace prefix-based API key acceptance

Remove logic equivalent to:

```python
if x_api_key.startswith("nuvorix_sk_"):
    ...
```

Do not use API-key prefixes as proof of validity.

---

## Step 2 — Implement database-backed API keys

Add an API-key model.

Suggested fields:

```python
class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str]
    organization_id: Mapped[str]
    name: Mapped[str]
    key_prefix: Mapped[str]
    key_hash: Mapped[str]
    role: Mapped[str]
    scopes_json: Mapped[list]
    created_at: Mapped[datetime.datetime]
    expires_at: Mapped[datetime.datetime | None]
    revoked_at: Mapped[datetime.datetime | None]
    last_used_at: Mapped[datetime.datetime | None]
```

Never store the raw API key.

---

## Step 3 — API-key generation

Create a service such as:

```text
apps/api/app/services/api_key_service.py
```

API-key creation flow:

```text
generate random cryptographically secure secret
        ↓
show raw secret exactly once to creator
        ↓
store only hash + non-secret metadata
        ↓
authenticate later by hashing presented key
        ↓
lookup by prefix / identifier
        ↓
constant-time hash comparison
```

Use a cryptographically secure random generator.

Do not use:

- UUID as the secret itself
- predictable strings
- timestamp-based secrets

---

## Step 4 — API-key scopes

The API key must carry explicit permissions.

Example:

```json
{
  "projects:read": true,
  "workloads:read": true,
  "deployments:create": false,
  "deployments:rollback": false
}
```

The effective permission must be:

```text
identity role permissions ∩ API-key scopes
```

Do not allow the API key to escalate beyond its configured role.

---

## Step 5 — Production authentication rules

In `get_current_user()`:

### Production mode

Accept only:

1. valid Bearer token
2. valid database-backed API key

Reject:

- `X-User-Role`
- `X-User-Id`
- `X-Org-Id`

with `401` or ignore those development-only headers.

### Development mode

Development headers may still be supported, but:

- they must be visibly documented as development-only
- they must not execute in production mode

---

## Step 6 — Fail fast on unsafe production configuration

In settings validation:

When:

```text
AUTH_MODE=production
```

require:

```text
SECRET_KEY
```

to be supplied externally.

Reject:

- default value
- empty value
- known example secret
- obviously weak secret

Startup should fail with a clear configuration error.

---

## Required tests

Create tests for:

```text
1. random nuvorix_sk_x value → 401
2. valid stored API key → 200
3. revoked API key → 401
4. expired API key → 401
5. wrong API key → 401
6. API key with read scope cannot deploy
7. API key cannot escalate role
8. X-User-Role ignored in production
9. X-Org-Id ignored in production
10. missing production secret causes configuration failure
11. development headers work only when AUTH_MODE=development
```

---

# 4. P0-2 — REMOVE DEFAULT ADMIN IDENTITY

## Files

- `apps/api/app/core/config.py`
- `apps/api/app/core/security.py`
- `apps/api/app/seed.py`
- tests

---

## Current problem

The application defaults to an admin identity.

This means the development convenience model is too close to a privileged production identity.

---

## Required changes

Do not use:

```python
DEFAULT_USER_ROLE = "admin"
DEFAULT_USER_ID = "usr-demo-admin"
```

as a security fallback.

Instead:

### Development mode

Use a named, explicit demo identity such as:

```text
dev-demo-user
```

and make the role configurable.

Do not let an arbitrary user choose a privileged role from a header unless explicitly running the isolated development mode.

### Production mode

There must be no default user.

No credentials means:

```text
401 Unauthorized
```

---

# 5. P0-3 — FIX TOOL AUTHORIZATION AND TENANT ISOLATION

## Files

- `apps/api/app/services/agent_service.py`
- `apps/api/app/api/v1/agents.py`
- `apps/api/app/services/rag_service.py`
- `apps/api/app/services/deploy_service.py`
- `apps/api/app/services/incident_service.py`
- `apps/api/app/models/entities.py`
- `apps/api/app/core/security.py`

Tests:

- `apps/api/tests/test_security_tenancy_eval.py`
- new `apps/api/tests/test_tool_security.py`

---

## Current problems

### Problem A

Tool metadata declares:

```python
"permissions": [...]
```

but `_execute_tool()` does not enforce those permissions.

### Problem B

`project_deployment_status` queries:

```python
select(Workload)
select(Deployment)
```

without restricting by organization.

### Problem C

Knowledge fallback does:

```python
select(KnowledgeBase).limit(1)
```

without tenant ownership.

### Problem D

The tool executor does not consistently receive the authenticated principal.

---

## Required architecture

Introduce an execution principal.

Suggested structure:

```python
class ExecutionContext(BaseModel):
    user_id: str
    organization_id: str
    role: str
    permissions: set[str]
    request_id: str | None
    source: str
```

Use it everywhere.

---

## Tool metadata

Expand each tool declaration to include:

```python
{
    "name": "...",
    "risk": "low" | "high",
    "required_permissions": [...],
    "side_effect": False | True,
    "allowed_states": [...],
    "requires_explicit_confirmation": True | False,
    "idempotent": True | False,
}
```

---

## Central authorization helper

Create:

```text
apps/api/app/services/tool_authorization.py
```

with helpers such as:

```python
authorize_tool(
    context,
    tool_definition,
)
```

It must verify:

1. tool exists
2. all required permissions are present
3. high-risk policy is satisfied
4. explicit confirmation exists for destructive actions
5. caller has access to target organization/resource

---

## Important

Do not use:

```python
allow_high_risk=True
```

as the authorization itself.

Instead:

```text
principal has deployments:rollback
AND
tool is high-risk
AND
explicit confirmation requested
AND
resource belongs to principal organization
```

---

# 6. P0-4 — MAKE EVERY TOOL TENANT-AWARE

## `knowledge_search`

Never select arbitrary knowledge bases.

Required lookup:

```text
knowledge_base_id
   ↓
KnowledgeBase
   ↓
Project
   ↓
Project.organization_id == context.organization_id
```

If no KB was supplied:

Select a KB belonging to the caller's organization.

Never:

```python
select(KnowledgeBase).limit(1)
```

globally.

---

## `project_deployment_status`

All queries must be tenant-scoped.

Use joins like:

```text
Deployment
→ Workload
→ Project
→ organization_id
```

and filter by the current organization.

---

## `diagnostic_check`

Only return actual measurements.

Do not return static values.

See P0-5 below.

---

## `emergency_circuit_breaker`

Must identify an explicit target resource.

Do not silently act on an unspecified deployment.

---

## Required adversarial tests

Test:

```text
Tenant A can read Tenant A workload
Tenant A cannot read Tenant B workload

Tenant A cannot use MCP tools to retrieve Tenant B data

Tenant A cannot query Tenant B KB

Tenant A cannot rollback Tenant B deployment

Tenant A cannot trigger Tenant B incident remediation
```

Do this through:

1. REST routes
2. direct service call
3. MCP endpoint

The direct service tests matter because route-only security is insufficient.

---

# 7. P0-5 — REMOVE FAKE DIAGNOSTIC OUTPUT

## File

`apps/api/app/services/agent_service.py`

---

## Current problem

The diagnostic tool returns static values like:

```text
database pool = healthy
4ms latency
memory = 42%
telemetry stream = active
```

These values are not actually measured.

---

## Required implementation

Create a diagnostic service:

```text
apps/api/app/services/diagnostic_service.py
```

Return real measurements:

### Database

Measure a simple DB query:

```sql
SELECT 1
```

Capture:

- success/failure
- latency_ms

### Memory

Use a reliable process/system metric library.

Capture:

- process RSS
- optionally host memory utilization

### Artifact storage

Check the configured artifact path is:

- readable
- writable

### Redis

If Redis is configured and required:

- perform `PING`
- measure latency

### MLflow

If MLflow integration is configured:

- test tracking endpoint / client connectivity when appropriate

---

## Output schema

Use a structured response:

```json
{
  "database": {
    "status": "healthy",
    "latency_ms": 3.4
  },
  "redis": {
    "status": "healthy",
    "latency_ms": 1.8
  },
  "memory": {
    "process_rss_mb": 182.3
  },
  "artifact_store": {
    "status": "healthy"
  }
}
```

Do not fabricate missing dependencies.

If Redis is unavailable but optional:

```text
status = "degraded"
```

not:

```text
healthy
```

---

# 8. P0-6 — MAKE THE CIRCUIT BREAKER A REAL STATE TRANSITION

## Files

- `apps/api/app/services/agent_service.py`
- `apps/api/app/services/deploy_service.py`
- `apps/api/app/api/v1/agents.py`
- `apps/api/app/models/entities.py`
- create tests

---

## Current problem

The current emergency tool returns a success object but does not actually mutate platform state.

---

## Important scope rule

Do NOT pretend this is a real Kubernetes traffic controller unless it actually controls Kubernetes traffic.

For the current platform, implement a **logical platform circuit breaker**.

---

## Required behavior

Given:

```text
deployment_id
reason
```

perform:

```text
authorize caller
   ↓
verify deployment belongs to caller organization
   ↓
verify deployment is currently active/candidate
   ↓
set traffic_percentage = 0
   ↓
set deployment status = "circuit_open"
   ↓
set workload status = "degraded" or equivalent
   ↓
create audit event
   ↓
commit transaction
```

Return success only after the DB transaction succeeds.

---

## Idempotency

Calling circuit breaker twice should not create two conflicting states.

Second call should return the already-open state.

---

# 9. P0-7 — FIX PGVECTOR SCORE CORRECTNESS

## File

`apps/api/app/services/rag_service.py`

---

## Current problem

The PostgreSQL path orders by cosine distance but then returns:

```python
"score": 0.95
```

for every result.

This invalidates relevance metrics.

---

## Required behavior

Use:

```python
distance = KnowledgeChunk.embedding.cosine_distance(query_vector)
```

and select the distance alongside the entity.

Convert to cosine similarity consistently.

For normalized vectors:

```text
similarity = 1 - cosine_distance
```

Use the actual value.

---

## Return schema

Each result must contain:

```json
{
  "chunk_id": "...",
  "document_id": "...",
  "score": 0.8734,
  "distance": 0.1266,
  "source": "...",
  "title": "...",
  "text": "..."
}
```

The exact field set may be simplified, but the score must represent the actual database similarity.

---

## Consistency requirement

SQLite fallback and PostgreSQL path must use the same score semantics.

Document the formula.

---

## Required tests

Test:

```text
1. identical query/document has high similarity
2. unrelated document has lower similarity
3. ranking is monotonic
4. PostgreSQL path returns non-constant scores
5. SQLite fallback returns comparable score semantics
6. min_score actually filters results
```

---

# 10. P1 — FIX RAG TENANT FILTERS INSIDE THE SERVICE

## File

`apps/api/app/services/rag_service.py`

The service must not accept a bare `knowledge_base_id` and assume authorization already happened.

Change service signatures to carry organization/context.

Example:

```python
query_knowledge_base(
    db=db,
    knowledge_base_id=...,
    query=...,
    context=execution_context,
)
```

Then verify ownership.

This prevents a future internal caller from bypassing HTTP security.

---

# 11. P1 — CORRECT EVALUATION ENGINE

## File

`apps/api/app/services/eval_service.py`

---

## Current problems

Some metrics are still hardcoded:

```text
tool_selection_accuracy = 0.95
cost_per_req = fixed value
```

RAG faithfulness/correctness is not a proper evaluation.

---

## Required design

Separate metrics into:

### A. Retrieval metrics

Calculate from a benchmark dataset with known expected source IDs.

Implement:

```text
Recall@K
Precision@K
MRR
```

At minimum use:

```text
Recall@3
MRR@3
```

---

### B. Answer correctness

Every benchmark case should define:

```json
{
  "query": "...",
  "expected_answer": "...",
  "expected_sources": ["doc-id-or-chunk-id"]
}
```

The evaluator should compare the system result against this expected answer.

For the local deterministic mode, use a deterministic scorer.

Do not call keyword presence “faithfulness” unless the metric is explicitly named as keyword coverage.

---

### C. Faithfulness

For a non-LLM deterministic regression suite:

Use a deterministic supported-context check.

Example:

```text
all factual answer claims must map to retrieved evidence fields
```

For live evaluation:

Use actual model output + explicit evaluator/judge when configured.

---

### D. Tool-selection accuracy

Do not hardcode.

Create evaluation cases:

```text
prompt → expected_tool
```

Run the planner/router and compare actual selected tool.

Compute:

```text
correct / total
```

---

# 12. P1 — REMOVE HARD-CODED COST FROM EVALUATION

## File

`apps/api/app/services/eval_service.py`

The cost metric must come from actual gateway/provider usage when the workload executes through the gateway.

For deterministic local execution:

Make the response explicit:

```text
cost_mode = "estimated_local"
```

Do not claim cloud provider billing.

---

## Recommended schema

```json
{
  "cost": {
    "value": 0.0032,
    "currency": "USD",
    "mode": "estimated",
    "provider": "local"
  }
}
```

For remote providers using real usage metadata:

```text
mode = "provider_reported"
```

---

# 13. P1 — FIX REAL P95 LATENCY

## Files

- `apps/api/app/services/eval_service.py`
- `apps/api/app/core/telemetry.py`

---

## Current problem

One measured operation is stored as a p95.

That is not a p95 distribution.

---

## Required implementation

For benchmark evaluation:

Run N repeated measurements.

Recommended local benchmark count:

```text
N = 20
```

Record every observation.

Then compute:

```python
p95 = np.percentile(latencies, 95)
```

Also expose:

```text
min
median
mean
p95
max
```

---

# 14. P1 — MAKE ML EVALUATION FALLBACK TRUTHFUL

## File

`apps/api/app/services/eval_service.py`

Current behavior can train a new fallback model if the artifact is missing.

That can make the evaluation appear to evaluate a registered candidate when it is actually evaluating a newly created model.

---

## Required behavior

Preferred order:

```text
registered candidate artifact exists
        ↓
load exact artifact
        ↓
evaluate exact candidate
```

If missing:

Return an explicit evaluation failure:

```text
status = failed
reason = "candidate_artifact_unavailable"
decision = BLOCK
```

Do not silently train another model unless the evaluation mode explicitly says:

```text
mode = "synthetic_rebuild"
```

and the output clearly indicates that.

---

# 15. P1 — FIX MLflow PRODUCTION ARCHITECTURE

## Files

- `apps/api/app/core/config.py`
- `apps/api/app/services/ml_service.py`
- `infra/helm/nuvorix/values.yaml`
- `infra/helm/nuvorix/templates/*`
- `docker-compose.yml`

---

## Development

SQLite is allowed:

```text
sqlite:///mlflow.db
```

---

## Production

Use:

```text
MLflow Tracking Server
        ↓
PostgreSQL backend store
        +
S3/MinIO artifact store
```

Nuvorix API must not pretend that a local SQLite MLflow file is a multi-replica production registry.

---

## Configuration

Add explicit configuration:

```text
MLFLOW_TRACKING_URI
MLFLOW_BACKEND_STORE_URI
MLFLOW_ARTIFACT_ROOT
```

Do not hardcode credentials in code or Helm templates.

---

# 16. P1 — REMOVE HARDCODED SECRETS FROM HELM

## File

`infra/helm/nuvorix/templates/configmap.yaml`

Current chart contains a secret-like static value.

Remove:

```text
SECRET_KEY: "...change-me..."
```

---

## Required production mechanism

The chart should reference a Kubernetes Secret supplied externally.

Preferred patterns:

```text
existingSecret
```

or:

```text
secretRef
```

Example values:

```yaml
secrets:
  existingSecret: ""
```

Then:

```yaml
envFrom:
  - secretRef:
      name: ...
```

Do not generate or commit real secrets inside the repository.

---

# 17. P1 — FIX HELM PRODUCTION DEFAULTS

## File

`infra/helm/nuvorix/values.yaml`

Current production configuration is internally inconsistent because it enables multiple replicas while defaulting to SQLite and disabling Redis/PostgreSQL.

---

## Required configuration split

Create:

```text
values.yaml
values-dev.yaml
values-production.yaml
```

### `values.yaml`

Safe neutral defaults.

### `values-dev.yaml`

Allows:

- local SQLite if needed
- local development convenience
- minimal replicas

### `values-production.yaml`

Must specify:

```text
PostgreSQL enabled / external
Redis enabled / external
external MLflow
external secret reference
multiple API replicas
persistent artifact storage
```

---

# 18. P1 — HORIZONTAL SCALING SAFETY

With:

```text
api.replicaCount > 1
```

the application must not depend on:

- in-process memory queues
- local SQLite for shared state
- local ephemeral model registry
- in-memory-only circuit state

Shared state belongs in:

```text
PostgreSQL
Redis
object storage
external telemetry backend
```

---

# 19. P1 — OPEN TELEMETRY EXPORTER CORRECTNESS

## File

`apps/api/app/core/telemetry.py`

Current OTel implementation is a real SDK span pipeline, but it stores spans in a process-local ring buffer.

That is acceptable for local inspection.

---

## Required improvements

Keep the ring buffer for local `/telemetry/traces`.

Add optional external export.

Configuration:

```text
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://...
```

If endpoint is configured:

```text
FastAPI/service spans
        ↓
OTLP exporter
        ↓
OTel Collector
```

Do not claim distributed external tracing when the collector exporter is disabled.

---

## Required spans

At minimum:

```text
HTTP request
RAG query
embedding generation
LLM call
agent workflow
tool call
evaluation run
deployment operation
incident remediation
```

---

# 20. P1 — LLM GATEWAY: MAKE PROVIDER/COST SEMANTICS PRECISE

## File

`apps/api/app/services/gateway_service.py`

---

## Current architecture

The remote HTTP provider is useful and should remain.

---

## Required changes

### Provider identity

Do not report:

```text
provider=anthropic
```

when the code actually calls an OpenAI-compatible endpoint unless the configured endpoint/provider genuinely represents Anthropic semantics.

Store:

```text
requested_provider
actual_provider
model
endpoint_class
```

when useful.

---

## Token counts

Preferred:

```text
provider-reported usage
```

Fallback:

```text
estimated token count
```

and expose:

```text
usage_source = "provider"
```

or:

```text
usage_source = "estimated"
```

Never silently mix them.

---

## Cost

Expose:

```text
cost_mode
pricing_source
```

Use a centralized pricing configuration.

Do not scatter prices across arbitrary service code.

---

# 21. P1 — CENTRALIZE DEPLOYMENT STATE TRANSITIONS

## File

`apps/api/app/services/deploy_service.py`

Create a clear deployment state machine.

Recommended states:

```text
candidate
active
retired
rolled_back
failed
circuit_open
```

Define allowed transitions.

Example:

```text
candidate → active
active → retired
active → rolled_back
active → circuit_open
candidate → failed
```

Reject illegal transitions.

---

# 22. P1 — DEPLOYMENT IDEMPOTENCY

Add an idempotency key for deployment mutation endpoints.

For example:

```text
Idempotency-Key
```

Store request result in a database table.

Repeated request with same key:

```text
same response
no duplicate deployment
```

Also consider concurrency protection when two operators deploy simultaneously.

---

# 23. P1 — INCIDENT REMEDIATION SAFETY

## File

`apps/api/app/services/incident_service.py`

Before remediation:

```text
authenticate
→ authorize
→ verify incident ownership
→ verify target deployment ownership
→ verify target deployment state
→ perform remediation
→ audit
→ commit
```

Do not blindly choose the first active workload in a project.

The incident should identify the affected deployment/workload.

---

# 24. P1 — AUDIT TRAIL IMPROVEMENT

## Files

- `apps/api/app/models/entities.py`
- `apps/api/app/api/v1/audit.py`
- all mutating services

Add fields where appropriate:

```text
request_id
workflow_id
before_state
after_state
reason
actor_type
created_at
```

Never put full secrets into audit logs.

Never put API keys into logs.

Avoid full raw LLM prompts/responses for sensitive workloads unless explicitly configured.

---

# 25. P1 — REQUEST CORRELATION

Add middleware support for:

```text
X-Request-ID
```

Behavior:

```text
incoming X-Request-ID
       ↓
reuse
```

otherwise:

```text
generate UUID
```

Propagate into:

- HTTP logs
- OTel spans
- agent runs
- tool calls
- evaluations
- deployment operations
- audit events

---

# 26. P1 — DATABASE FINANCIAL PRECISION

For money-like values use Decimal/Numeric rather than Float.

Review any models containing:

```text
cost
price
amount
currency values
```

Replace:

```python
Float
```

with appropriate:

```python
Numeric(precision, scale)
```

where the value is financial.

Keep floating point for non-financial telemetry where appropriate.

---

# 27. P1 — DATABASE CONSTRAINTS AND INDEXES

Add appropriate constraints.

At minimum review:

```text
organization-scoped uniqueness
workload + version
deployment uniqueness where logically required
API key prefix uniqueness
```

Add indexes for frequent tenant queries:

```text
Project.organization_id
Workload.project_id
Deployment.workload_id
KnowledgeBase.project_id
KnowledgeChunk.knowledge_base_id
EvaluationRun.workload_id
AuditEvent.organization_id
```

Do not create uniqueness constraints that incorrectly prevent legitimate versioning.

---

# 28. P1 — REMOVE LOCAL-ONLY STORAGE ASSUMPTIONS

If model/artifact storage is intended to be production-capable:

Introduce a storage abstraction such as:

```text
apps/api/app/services/storage/base.py
apps/api/app/services/storage/local.py
apps/api/app/services/storage/s3.py
```

Support:

```text
local filesystem
S3-compatible object storage
```

Store:

```text
artifact URI
checksum
content type
size
created_at
```

Do not store important production artifacts only on container-local disk.

---

# 29. P2 — CI HARDENING

## File

`.github/workflows/ci.yml`

Keep:

```text
uv sync --frozen
pytest
ruff
npm ci
npm build
```

Add:

```text
terraform fmt -check
terraform validate
helm lint
```

Add static/security checks where compatible:

```text
mypy
dependency audit
secret scanning
container vulnerability scan
```

Do not make live-provider API tests mandatory for standard CI unless secrets are intentionally configured.

---

# 30. P2 — TEST MATRIX

The final suite should cover at least these categories.

## Authentication

```text
production no auth
production invalid token
production expired token
production valid token
valid API key
revoked API key
expired API key
invalid API key
dev headers only in development
```

## Authorization

```text
viewer cannot deploy
developer cannot rollback
role cannot exceed permissions
high-risk tool cannot execute without permission
high-risk tool requires explicit authorization
```

## Multi-tenancy

```text
project isolation
workload isolation
deployment isolation
KB isolation
evaluation isolation
audit isolation
tool isolation
MCP isolation
incident isolation
```

## RAG

```text
real embedding dimensions
actual PostgreSQL score
SQLite score
threshold filtering
ranking
tenant filtering
```

## Evaluation

```text
metric correctness
tool accuracy
Recall@K
MRR
p95
strict threshold BLOCK
passing threshold ALLOW
missing artifact BLOCK
estimated cost labeling
```

## Deployment

```text
illegal transition
duplicate deployment request
rollback ownership
circuit breaker
repeat circuit breaker
```

## Observability

```text
request ID
span creation
LLM usage
tool metrics
RAG latency
deployment metrics
incident metrics
```

---

# 31. P2 — ADD CONCURRENCY TESTS

These are particularly important.

Write tests that concurrently execute:

```text
two deployment creations
two rollbacks
two circuit-breaker calls
two API-key uses
two identical idempotent requests
```

Verify no invalid state occurs.

Use database locking/transaction handling where required.

---

# 32. P2 — READINESS CHECK MUST REPRESENT REAL DEPENDENCIES

## File

`apps/api/app/api/v1/health.py`

Distinguish:

```text
liveness
readiness
```

### Liveness

The process is alive.

### Readiness

Critical dependencies are usable.

Example:

```text
DB healthy
required Redis healthy
required storage healthy
```

Do not report readiness as healthy when the application cannot actually fulfill configured production responsibilities.

---

# 33. P2 — README CORRECTIONS

## Files

- `README.md`
- `docs/IMPLEMENTATION_STATUS.md`

---

## Remove or rewrite claims that are not literally true

Do not say:

```text
production-grade Kubernetes blue/green
```

unless actual Kubernetes traffic is controlled.

Do not say:

```text
real-time incident detection
```

unless telemetry events are actually ingested and analyzed.

Do not say:

```text
immutable audit trail
```

unless immutability/tamper resistance is technically implemented.

Do not say:

```text
distributed tracing
```

if only an in-process ring buffer is enabled.

Do not say:

```text
real-time cloud cost
```

if the platform uses a static pricing table and estimates.

---

# 34. REWRITE FEATURE STATUS MATRIX

Use only these statuses:

```text
Verified Real
Verified Local
Production-Ready
Artifact Only
Experimental
Simulated
```

Do not mark an artifact as production-ready merely because files exist.

---

# 35. REQUIRED README ARCHITECTURE STATEMENT

Use a statement conceptually equivalent to:

> Nuvorix separates probabilistic AI components from deterministic platform controls. Embeddings, LLMs, and agents handle probabilistic workloads, while authorization, tenancy, release gates, state transitions, and irreversible platform actions are enforced by deterministic services.

This should become one of the core architecture messages.

---

# 36. REQUIRED DOCUMENTATION OF LOCAL VS PRODUCTION MODES

Add a table:

| Capability | Local Development | Production |
|---|---|---|
| App DB | SQLite allowed | PostgreSQL |
| Vector DB | SQLite fallback allowed | pgvector |
| MLflow | local file/SQLite | MLflow server + PostgreSQL + object store |
| Queue | single-process fallback if explicitly documented | Redis-backed/durable |
| Storage | local filesystem | S3-compatible |
| Auth | development headers | signed token/API key |
| OTel | ring buffer optional | OTLP collector |
| Scaling | single replica | multi-replica |
| Secrets | `.env` placeholders | external secret manager/K8s Secret |

Only include queue/storage rows that are truly implemented after this plan. Do not claim Redis durability unless the application actually uses Redis for queue semantics.

---

# 37. CRITICAL: DO NOT INVENT DURABILITY

There is currently Redis infrastructure, but infrastructure being present is not the same as Redis-backed durable jobs.

Therefore:

If a Redis job queue is not implemented in this pass, document:

```text
Queue durability: not yet implemented
```

Do not write:

```text
durable distributed queue
```

in the README.

The same principle applies to:

- ArgoCD
- real Kubernetes traffic shifting
- external MLflow server
- S3
- external OTel
- GPU workflows

---

# 38. FILE-BY-FILE IMPLEMENTATION CHECKLIST

The agent must check every relevant file after implementation.

## Security

- [ ] `apps/api/app/core/config.py`
- [ ] `apps/api/app/core/security.py`
- [ ] `.env.example`
- [ ] `apps/api/app/seed.py`

## Agent/tooling

- [ ] `apps/api/app/services/agent_service.py`
- [ ] `apps/api/app/api/v1/agents.py`
- [ ] add tool authorization helper
- [ ] add diagnostic service

## RAG

- [ ] `apps/api/app/services/rag_service.py`
- [ ] `apps/api/app/api/v1/knowledge.py`
- [ ] `apps/api/app/models/entities.py`

## Evaluation

- [ ] `apps/api/app/services/eval_service.py`
- [ ] benchmark fixtures/data
- [ ] evaluation tests

## Deployment/incident

- [ ] `apps/api/app/services/deploy_service.py`
- [ ] `apps/api/app/services/incident_service.py`
- [ ] `apps/api/app/api/v1/deployments.py`
- [ ] `apps/api/app/api/v1/incidents.py`

## Gateway

- [ ] `apps/api/app/services/gateway_service.py`
- [ ] `apps/api/app/models/entities.py`

## Observability

- [ ] `apps/api/app/core/telemetry.py`
- [ ] `apps/api/app/main.py`
- [ ] health/readiness implementation

## Infrastructure

- [ ] `docker-compose.yml`
- [ ] `infra/helm/nuvorix/values.yaml`
- [ ] `infra/helm/nuvorix/templates/*`
- [ ] `infra/terraform/*`
- [ ] `.github/workflows/ci.yml`

## Documentation

- [ ] `README.md`
- [ ] `docs/IMPLEMENTATION_STATUS.md`

---

# 39. REQUIRED NEW FILES

Create these only when their responsibilities are actually implemented:

```text
apps/api/app/services/api_key_service.py
apps/api/app/services/tool_authorization.py
apps/api/app/services/diagnostic_service.py
apps/api/app/services/storage/base.py
apps/api/app/services/storage/s3.py
```

Also add dedicated tests:

```text
apps/api/tests/test_authentication_hardening.py
apps/api/tests/test_tool_security.py
apps/api/tests/test_rag_retrieval_correctness.py
apps/api/tests/test_evaluation_metrics.py
apps/api/tests/test_deployment_state.py
```

Names can be adjusted to match existing project conventions, but responsibilities must remain.

---

# 40. MIGRATION REQUIREMENTS

Because new database models/columns/constraints are being introduced, do not rely on `create_all()` as the only migration mechanism for production.

Create proper migration support for schema changes.

If the project is intentionally not using Alembic yet:

1. add Alembic
2. configure metadata
3. create initial migration covering the current schema if necessary
4. create incremental migration(s) for new API keys, constraints, indexes, audit fields, etc.

Do not manually mutate production schema in application startup.

---

# 41. VALIDATION COMMANDS

After implementation, run these from repository root.

## Python environment

```bash
uv sync --frozen
```

---

## Formatting / lint

```bash
uv run ruff check apps packages
```

If formatting is introduced:

```bash
uv run ruff format --check apps packages
```

---

## Tests

```bash
uv run pytest -v
```

The full suite must pass.

---

## Frontend

```bash
cd apps/web
npm ci
npm run build
cd ../..
```

---

## Terraform

For each Terraform environment:

```bash
terraform fmt -check -recursive
terraform validate
```

---

## Helm

From the chart directory:

```bash
helm lint infra/helm/nuvorix
```

If environment values exist:

```bash
helm template nuvorix infra/helm/nuvorix \
  --values infra/helm/nuvorix/values-production.yaml
```

The rendered output must not contain literal production secret values.

---

## Security smoke tests

Run tests that prove:

```text
random API key rejected
cross-tenant access rejected
MCP cross-tenant access rejected
high-risk tool unauthorized rejected
production dev headers rejected
```

---

# 42. REQUIRED ACCEPTANCE CRITERIA

The work is not complete until every item below is true.

## Security acceptance

- [ ] No arbitrary `nuvorix_sk_*` string authenticates.
- [ ] No default admin authentication exists in production.
- [ ] Production requires external secret configuration.
- [ ] Development headers cannot authorize production requests.
- [ ] Tool permissions are enforced at service boundary.
- [ ] High-risk tools require actual permissions.
- [ ] Cross-tenant tool access is impossible.

## RAG acceptance

- [ ] PostgreSQL retrieval returns real cosine-based scores.
- [ ] SQLite and PostgreSQL score semantics are documented.
- [ ] Tenant filtering occurs inside the RAG service.
- [ ] `min_score` works.
- [ ] Retrieval ranking tests pass.

## Agent acceptance

- [ ] Diagnostic values are measured.
- [ ] Circuit breaker performs a real logical state transition.
- [ ] Circuit breaker is tenant-safe.
- [ ] Circuit breaker is idempotent.
- [ ] Tool execution carries caller context.

## Evaluation acceptance

- [ ] No hardcoded tool-selection accuracy.
- [ ] No hardcoded latency pretending to be p95.
- [ ] No hardcoded “empirical” accuracy.
- [ ] Missing candidate artifacts cause BLOCK/failure rather than silent replacement.
- [ ] Benchmark dataset contains expected sources/answers.
- [ ] Retrieval metrics are computed from actual benchmark outcomes.

## Infrastructure acceptance

- [ ] Helm production values do not default to SQLite.
- [ ] Production secret is externalized.
- [ ] Local and production configuration are clearly separated.
- [ ] README does not claim unavailable production capabilities.

## Observability acceptance

- [ ] Request IDs propagate.
- [ ] OTel spans are real.
- [ ] External OTLP export is optional and truthful.
- [ ] LLM usage source is identifiable.
- [ ] Costs are labeled actual/provider-reported vs estimated.

---

# 43. DEFINITION OF DONE FOR ANTI-GRAVITY

The agent should report the work as complete only after producing all of the following.

## A. Code

All required fixes are implemented.

## B. Tests

A complete test run passes.

## C. Security evidence

The agent must provide a short table:

| Test | Result |
|---|---|
| arbitrary API key rejected | PASS |
| cross-tenant REST read | PASS |
| cross-tenant tool read | PASS |
| cross-tenant MCP read | PASS |
| high-risk unauthorized | PASS |
| production dev-header bypass | PASS |

## D. RAG evidence

Provide:

```text
PostgreSQL score example:
top result score = <actual measured value>

SQLite score example:
top result score = <actual measured value>
```

Do not fabricate the values; run the test.

## E. Evaluation evidence

Provide real benchmark output:

```text
total cases
passed
blocked
Recall@3
MRR@3
tool selection accuracy
mean latency
p95 latency
cost mode
```

## F. Infrastructure evidence

Show:

```text
helm lint
terraform validate
pytest
ruff
frontend build
```

and state actual results.

---

# 44. IMPORTANT AGENT BEHAVIOR

While implementing:

### Do not

- add fake values to satisfy tests
- weaken a test to make CI green
- delete a failing test because behavior changed
- change the README to hide a failed feature
- label simulated behavior as real
- hardcode test outputs
- add fake migrations
- silently swallow authorization errors
- convert all failures into fallback success

### Do

- fail closed for security
- fail explicitly for missing production dependencies
- keep local development ergonomics
- preserve backward compatibility only when it is safe
- add regression tests for every bug fixed
- keep provider abstractions clean
- separate local/demo implementations from production implementations
- document limitations truthfully

---

# 45. RECOMMENDED IMPLEMENTATION ORDER IN SMALL COMMITS

Use small focused commits.

Suggested sequence:

```text
1. security: replace insecure api-key acceptance
2. security: enforce production auth defaults
3. security: introduce execution context and tool permissions
4. security: enforce tenant ownership inside tools/services
5. rag: return real pgvector similarity scores
6. platform: implement real diagnostic measurements
7. platform: implement logical circuit breaker state transition
8. eval: remove synthetic hardcoded metrics
9. eval: add proper retrieval metrics and p95
10. mlflow: separate local and production tracking configuration
11. helm: externalize secrets and separate env values
12. observability: add request correlation and OTLP export
13. ci: add terraform/helm/security validation
14. tests: add adversarial/concurrency regression suite
15. docs: reconcile README and implementation status
```

Do not combine every change into one giant commit.

---

# 46. FINAL PORTFOLIO POSITIONING AFTER THESE FIXES

After successful implementation, position Nuvorix as:

> **A self-service AI/ML platform control plane that provides reusable primitives for model lifecycle, RAG, agent orchestration, evaluation gates, deployment state management, governance, observability, and cost-aware LLM operations.**

Use the following architecture story in interviews:

```text
Developer
   ↓
Nuvorix API / SDK / CLI
   ↓
Control Plane
   ├── Workload & Project Management
   ├── Model / MLflow Lifecycle
   ├── RAG / pgvector
   ├── LangGraph Agent Runtime
   ├── MCP Tool Gateway
   ├── Evaluation & Release Gates
   ├── Deployment State Machine
   ├── LLM Gateway / FinOps
   └── Observability / Audit
            ↓
   Deterministic policy & authorization boundary
            ↓
   PostgreSQL / pgvector / Redis / object storage / MLflow / Kubernetes
```

The most valuable interview sentence is:

> **I designed Nuvorix so that probabilistic AI components can propose and reason, but deterministic platform services remain responsible for authorization, tenancy, release policy, state transitions, and irreversible actions.**

---

# 47. FINAL AGENT INSTRUCTION

Implement the changes in this document against the current repository.

Before changing anything:

1. inspect the current implementation
2. preserve existing working behavior where safe
3. add tests before or alongside fixes
4. make each security boundary explicit
5. run the relevant tests after every major subsystem
6. run the complete suite at the end
7. update documentation only after implementation is verified

The final result must be:

```text
secure
tenant-safe
measurable
testable
locally runnable
production-minded
truthful
```

Do not optimize for the number of technologies.

Optimize for:

```text
correctness
security
reusability
operability
observability
reproducibility
clear architecture
```

The ultimate success condition is:

> A developer can use Nuvorix to manage an AI workload while the platform reliably enforces tenant boundaries, authorization, evaluation policy, operational state transitions, and auditability without pretending that simulated components are production infrastructure.
