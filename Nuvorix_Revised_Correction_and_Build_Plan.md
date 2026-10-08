# Nuvorix — Revised Correction & Build Plan

## Purpose

This document supersedes the earlier Nuvorix plan and is based on the latest repository review of `VNT1998/nuvorix`.

**Goal:** turn Nuvorix from a strong AI/ML platform prototype into a credible, demonstrable AI Platform Engineering project.

### Target roles

- AI Platform Engineer
- MLOps / ML Platform Engineer
- Backend Engineer — Python / AI
- GenAI / Agentic AI Engineer

---

# 1. Current State

The latest repository now contains real implementations for several capabilities:

| Capability | Current state |
|---|---|
| FastAPI control plane | ✅ Real |
| Async SQLAlchemy | ✅ Real |
| PostgreSQL / SQLite | ✅ Real |
| Redis | ✅ Real integration |
| React/Vite console | ✅ Real |
| CLI | ✅ Real |
| Python SDK | ✅ Real |
| Scikit-learn training | ✅ Real |
| MLflow tracking | ✅ Real |
| LangGraph StateGraph | ✅ Real |
| Prometheus | ✅ Real |
| OpenTelemetry SDK | ✅ Real |
| MCP-shaped interface | 🟡 Needs protocol validation |
| RAG | 🔴 Uses synthetic/hash vectors |
| pgvector | 🔴 Not actually used by retrieval |
| Evaluation | 🔴 Metrics are currently simulated |
| LLM Gateway | 🔴 Provider response is simulated |
| MLflow Model Registry | 🟠 Tracking is real; registry lifecycle needs completion |
| Authentication | 🔴 Header-based development identity |
| Kubernetes | 🟠 Manifests exist; verify on kind |
| Helm | 🟠 Chart exists; verify |
| Terraform | 🟠 Files exist; validate/fix |
| OpenTelemetry backend | 🟡 In-process ring buffer |
| Incident RCA | 🟠 Prototype |
| CI/CD | 🟡 Workflows exist; verify |
| README | 🔴 Some claims are ahead of verified implementation |

**Non-negotiable rule:** a capability is only called implemented when its code, dependencies, execution path, tests and documentation all agree.

---

# 2. Priority Order

Execute in this sequence:

```text
P0 — Replace simulated AI/platform behavior
        ↓
P1 — Make infrastructure executable and verifiable
        ↓
P2 — Harden authentication, RBAC and tenancy
        ↓
P3 — Improve observability and reliability
        ↓
P4 — Build real incident RCA
        ↓
P5 — Final portfolio/documentation polish
```

Do not spend time on visual polish before P0 is finished.

---

# 3. P0 — Real Embeddings + pgvector

## Current problem

`apps/api/app/services/rag_service.py` creates vectors using SHA/MD5 hashing and token/3-gram projections.

This is deterministic, but it is not a semantic embedding model.

## Required architecture

```text
Document
  ↓
Parser
  ↓
Chunker
  ↓
Real Embedding Model
  ↓
PostgreSQL + pgvector
  ↓
Vector Similarity Search
  ↓
Top-K Results
```

## Requirements

Use a real local embedding model, preferably a Hugging Face/Sentence Transformers model.

Record:

- embedding model
- embedding dimension
- ingestion version

Create a real pgvector column.

Use PostgreSQL similarity search rather than:

```text
SELECT all chunks
→ calculate cosine similarity in Python
```

Use a real vector index when appropriate; HNSW is a good starting point.

## Acceptance criteria

- [ ] real embedding model is used
- [ ] model is configurable
- [ ] pgvector extension enabled
- [ ] vector column created
- [ ] similarity query executed in PostgreSQL
- [ ] known relevant document is retrieved
- [ ] source/page metadata is returned
- [ ] tenant isolation is respected

---

# 4. P0 — Replace Simulated Evaluation

## Current problem

`eval_service.py` derives evaluation quality from the version name (`bad`/`fail` style logic).

That is acceptable for a demo trigger, but not for a real evaluation platform.

## Required architecture

```text
Evaluation Dataset
       ↓
Execute Candidate
       ↓
Collect Actual Outputs
       ↓
Evaluate Outputs
       ↓
Aggregate Metrics
       ↓
Policy Gate
       ↓
ALLOW / BLOCK
```

## ML evaluation

Actually run the model on a held-out dataset and calculate:

- RMSE
- MAE
- R²
- latency

## RAG evaluation

Actually run questions and calculate:

- retrieval recall
- context quality
- faithfulness
- answer correctness
- citation correctness
- latency
- token usage
- cost

## Agent evaluation

Actually run tasks and measure:

- task success
- tool selection
- tool success
- final answer correctness
- safety violations
- latency

## Keep deterministic regression tests

These are useful for:

- policy logic
- schema validation
- routing
- security
- failure paths

Name them clearly:

> Deterministic regression suite

Do not mix them with real AI quality measurements.

## Acceptance criteria

- [ ] version name no longer determines metrics
- [ ] evaluator runs the candidate
- [ ] candidate output is captured
- [ ] metrics are calculated from actual output
- [ ] failed candidate is reproducible
- [ ] release gate consumes those real metrics
- [ ] benchmark methodology is documented

---

# 5. P0 — Make LLM Gateway Real

## Current problem

`gateway_service.py` currently constructs a simulated response.

## Required architecture

```text
Client
 ↓
Nuvorix Gateway
 ↓
Policy
 ↓
Budget
 ↓
Router
 ├── Local
 ├── Provider A
 └── Provider B
```

Implement a provider abstraction.

Minimum:

1. mock/local provider
2. one actual remote provider

Useful later:

- second provider
- automatic fallback
- model selection

## Required reliability

- timeout
- retry where safe
- structured error
- fallback where configured
- request id
- usage tracking

## Record

- provider
- model
- workload
- request id
- input tokens
- output tokens
- latency
- estimated/actual cost
- status

## Acceptance criteria

- [ ] actual provider request works
- [ ] actual response returned
- [ ] provider timeout tested
- [ ] provider failure tested
- [ ] usage recorded
- [ ] cost clearly labeled as estimated or actual
- [ ] secrets are externalized

---

# 6. P0 — Upgrade LangGraph into a Real LLM Agent

## Current state

The StateGraph is real and is a good foundation.

The planner, however, currently relies on keyword matching.

## Required architecture

```text
User Request
     ↓
LLM Planner
     ↓
Structured Tool Decision
     ↓
Tool Execution
     ↓
Observation
     ↓
LLM Decision / Next Step
     ↓
Final Response
```

## State

Persist:

- execution id
- request
- plan
- selected tool
- tool arguments
- observations
- messages
- steps
- final result
- error

## Minimum tools

1. knowledge search
2. deployment status
3. diagnostics

Later:

4. metrics query
5. logs query
6. Kubernetes read-only inspection

## Acceptance criteria

- [ ] LLM actually selects tools
- [ ] structured tool args validated
- [ ] tool errors are returned to the workflow
- [ ] multi-step execution works
- [ ] traces expose node transitions
- [ ] high-risk operations require authorization

---

# 7. P0 — Validate Real MCP Support

The repository now exposes MCP-shaped endpoints.

Do not automatically describe this as full MCP support.

## Required

Validate the implementation against the MCP protocol/version actually being targeted.

Prefer a maintained/official MCP implementation/library where practical.

Minimum demonstrated operations:

```text
initialize
tools/list
tools/call
```

## Acceptance

- [ ] valid MCP client can communicate with the server
- [ ] tool schemas are valid
- [ ] errors follow expected protocol behavior
- [ ] authorization applies to tool calls
- [ ] risky tools remain protected

---

# 8. P1 — Complete MLflow Model Registry

## Current state

MLflow tracking is real:

- experiments
- params
- metrics
- artifacts
- tags

The platform's own database status field must not be confused with the MLflow Model Registry.

## Required lifecycle

```text
Train
 ↓
MLflow Run
 ↓
Registered Model
 ↓
Model Version
 ↓
Evaluate
 ↓
Promote
 ↓
Production
```

Use real MLflow registry entities.

## Acceptance

- [ ] registered model exists in MLflow
- [ ] model version exists
- [ ] version linked to platform record
- [ ] evaluation linked to version
- [ ] promotion is reflected in registry state
- [ ] rollback restores prior approved version

---

# 9. P1 — Authentication + RBAC + Tenant Isolation

## Current problem

Development identity can come from:

```text
X-User-Id
X-User-Role
X-Org-Id
```

A caller can potentially claim an admin role by setting the header.

That is not authentication.

## Required architecture

```text
JWT / OIDC
   ↓
Verified Identity
   ↓
Organization
   ↓
Role
   ↓
Permission
   ↓
Resource Ownership
```

## Roles

- admin
- platform_engineer
- ml_engineer
- developer
- viewer

## Development mode

Header-based identity may remain only behind:

```text
AUTH_MODE=development
```

Production mode must fail closed.

## Tenant tests

Create Tenant A and Tenant B.

Verify:

- A cannot read B data
- A cannot query B knowledge
- A cannot deploy B workload
- A cannot invoke B protected tools

---

# 10. P1 — Actually Enforce Permissions

A permission map existing in code is not enough.

Every sensitive endpoint must enforce authorization server-side.

Examples:

```text
POST /deployments
→ deployments:create
```

```text
POST /rollback
→ deployments:rollback
```

```text
POST /models/{id}/promote
→ models:promote
```

The frontend must never be the security boundary.

---

# 11. P1 — Kubernetes Validation

The repository has kind manifests.

Actually verify them.

## Required

```bash
kind create cluster --name nuvorix
kubectl apply -f infra/kind/nuvorix-all.yaml
kubectl get pods -n nuvorix
kubectl get svc -n nuvorix
kubectl get deployments -n nuvorix
kubectl get hpa -n nuvorix
```

Verify:

- readiness
- liveness
- resource requests/limits
- ConfigMaps
- Secrets
- ServiceAccounts
- RBAC

Use accurate wording:

> Kubernetes deployment validated locally on kind.

Do not call it production cloud deployment.

---

# 12. P1 — Helm

Run:

```bash
helm lint ./infra/helm/nuvorix
helm template nuvorix ./infra/helm/nuvorix
```

Then install on kind:

```bash
helm upgrade --install nuvorix ./infra/helm/nuvorix   --namespace nuvorix   --create-namespace
```

Fix:

- chart references
- service names
- config/secret wiring
- storage assumptions
- HPA
- ingress assumptions

Do not document a Helm chart as “production ready” until it is actually installable and tested.

---

# 13. P1 — Terraform

Terraform is a good addition, but it must be real.

Current direction:

```text
Kubernetes provider
Helm provider
local/dev environment
```

Validate:

```bash
terraform fmt -check
terraform init
terraform validate
terraform plan
```

Make sure the local Helm chart is passed as a local chart path rather than incorrectly treated as a remote Helm repository.

Use honest wording:

> Terraform automates the local/dev Kubernetes environment and Nuvorix Helm deployment.

Only claim cloud infrastructure after implementing and testing a real cloud environment.

---

# 14. P2 — OpenTelemetry Upgrade

## Current state

The OTel SDK and ring-buffer exporter are real.

That is useful for a demo console but is not yet a distributed telemetry backend.

## Target

```text
Nuvorix
 ↓
OpenTelemetry SDK
 ↓
OTel Collector
 ↓
Trace Backend
 ↓
Grafana
```

Prioritize:

- HTTP
- agent run
- tool call
- retrieval
- LLM call
- evaluation
- deployment

Keep Prometheus for metrics.

---

# 15. P2 — Real Incident RCA

Current incident functionality should evolve from prototype to evidence-driven diagnosis.

## Trigger

Use actual metrics/anomalies.

```text
Latency anomaly
 ↓
Incident
 ↓
Evidence collection
```

Collect:

- Prometheus metrics
- OTel traces
- logs
- deployment history
- Kubernetes status
- Git change metadata

Then:

```text
Evidence
 ↓
Hypotheses
 ↓
Ranked root cause
 ↓
Recommendation
```

Output must distinguish:

```text
Observed evidence
Inference
Recommendation
Confidence
```

Never present fabricated telemetry as real.

---

# 16. P2 — Real Blue/Green Behavior

Current database state transitions are not enough to claim actual traffic switching.

Target:

```text
Service
 ├── Stable deployment
 └── Candidate deployment
```

Required demo:

```text
100% stable
 ↓
candidate health checks
 ↓
evaluation gate
 ↓
switch traffic
 ↓
monitor
 ↓
rollback
```

Later:

```text
95% stable
5% candidate
```

---

# 17. P2 — Cost / FinOps

Current cost calculations should be labeled as estimates unless they come from provider billing.

Track:

- organization
- project
- workload
- model
- request
- tokens
- estimated cost

Dashboard:

- request count
- input/output tokens
- cost/request
- cost/model
- cost/workload

Use the term:

> estimated cost

when provider billing data is unavailable.

---

# 18. CI/CD Corrections

Current CI is a good start but contains fallback behavior:

```bash
uv sync --frozen || uv sync
npm ci || npm install
```

This undermines reproducibility.

Use:

```bash
uv sync --frozen
```

and:

```bash
npm ci
```

with committed lockfiles.

## CI pipeline

```text
Lint
 ↓
Type Check
 ↓
Unit Tests
 ↓
Integration Tests
 ↓
AI Regression Evaluation
 ↓
Build
 ↓
Docker
```

Failed evaluation must be able to block release.

---

# 19. Security / Secret Cleanup

Search the repository for:

```text
password
secret
api_key
token
SECRET_KEY
DATABASE_URL
```

Required:

- no production secrets
- no hardcoded provider keys
- `.env.example` contains placeholders only
- Kubernetes Secrets for cluster configuration
- production mode fails if required secrets are missing

---

# 20. Testing Strategy

## Unit

Test:

- release policies
- RBAC
- tenant isolation
- tool permissions
- model promotion
- rollback
- cost calculation
- RAG retrieval
- agent routing

## Integration

Test:

- PostgreSQL
- Redis
- pgvector
- MLflow
- LLM provider
- MCP

## E2E

```text
Create project
 ↓
Create workload
 ↓
Create knowledge base
 ↓
Index
 ↓
Run agent
 ↓
Retrieve
 ↓
Evaluate
 ↓
ALLOW
 ↓
Deploy
 ↓
Observe
 ↓
Rollback
```

## Failure cases

Test:

- database unavailable
- Redis unavailable
- provider timeout
- invalid model
- failed evaluation
- unauthorized tool
- deployment failure
- rollback failure

---

# 21. README Rewrite After Implementation

Only rewrite final claims after verification.

Recommended status table:

| Capability | Status |
|---|---|
| FastAPI control plane | ✅ Implemented |
| MLflow tracking | ✅ Implemented |
| MLflow registry | ✅/🟡 based on actual verification |
| LangGraph | ✅ Implemented |
| LLM-driven planning | ✅/🟡 based on actual verification |
| MCP | ✅/🟡 based on protocol validation |
| RAG | ✅ after real embeddings |
| pgvector | ✅ after DB-backed vector search |
| Evaluation | ✅ after real candidate execution |
| LLM Gateway | ✅ after real provider integration |
| OpenTelemetry | ✅ SDK / 🟡 external backend |
| Kubernetes | ✅ kind validated |
| Helm | ✅ validated |
| Terraform | ✅ validated |
| RBAC | ✅ enforced |
| Tenant isolation | ✅ tested |
| Incident RCA | 🟡 prototype until evidence-driven |
| FinOps | ✅ estimated cost |

Remove phrases such as:

> Production Ready

unless a specific component has genuinely been verified to that standard.

---

# 22. Critical Metrics Rule

Never publish a number only because it looks good.

Every benchmark must state:

```text
Metric
Dataset size
Execution mode
Model/provider
Environment
Measurement method
Result
```

Especially avoid unsupported claims such as:

```text
100% accuracy
100% safety
sub-millisecond LLM latency
```

---

# 23. Final MVP

The credible Nuvorix MVP is:

```text
Nuvorix Control Plane
        ↓
Real MLflow lifecycle
        ↓
Real embeddings + pgvector
        ↓
Real LLM Gateway
        ↓
Real LLM-driven LangGraph agent
        ↓
Real MCP interface
        ↓
Real evaluation
        ↓
Release Gate
        ↓
Kubernetes
        ↓
Prometheus + OpenTelemetry
        ↓
Rollback
```

Do not add more technologies until this path works end-to-end.

---

# 24. Agent Execution Order

The coding agent MUST execute in this order:

### Step 1
Inspect current code and create/update:

```text
docs/IMPLEMENTATION_STATUS.md
```

### Step 2
Replace synthetic RAG embeddings with a real embedding model.

### Step 3
Implement PostgreSQL pgvector storage and search.

### Step 4
Replace simulated evaluation metrics with actual candidate execution.

### Step 5
Implement a real LLM provider in the gateway.

### Step 6
Convert LangGraph planner from keyword routing to LLM-driven structured decisions.

### Step 7
Validate MCP with a real client/protocol test.

### Step 8
Complete MLflow Model Registry lifecycle.

### Step 9
Implement real authentication and enforce tenant isolation.

### Step 10
Validate Kubernetes on kind.

### Step 11
Validate/fix Helm.

### Step 12
Validate/fix Terraform.

### Step 13
Upgrade OpenTelemetry.

### Step 14
Make incident RCA consume real telemetry.

### Step 15
Run the complete test suite.

### Step 16
Rewrite the README so every claim reflects verified code.

---

# 25. Definition of Portfolio Ready

Nuvorix is portfolio-ready only when:

- [ ] real embeddings
- [ ] pgvector search
- [ ] actual evaluation execution
- [ ] real LLM provider
- [ ] LLM-driven LangGraph agent
- [ ] validated MCP
- [ ] real MLflow registry lifecycle
- [ ] real authentication or clearly isolated development mode
- [ ] tenant isolation tested
- [ ] Kubernetes works on kind
- [ ] Helm passes lint/template/install
- [ ] Terraform passes validate/plan
- [ ] Prometheus metrics are real
- [ ] OTel traces are real
- [ ] CI passes deterministically
- [ ] no hardcoded secrets
- [ ] benchmark methodology documented
- [ ] README matches actual implementation

---

# 26. Interview Demo

The recommended five-minute demo:

```text
1. Create workload
2. Add knowledge base
3. Run LangGraph agent
4. Agent selects a tool through the LLM
5. Tool executes through policy
6. Show RAG evidence
7. Show trace
8. Run evaluation
9. Show ALLOW
10. Deploy to kind
11. Show Kubernetes
12. Show Prometheus/OTel
13. Introduce a genuinely regressed candidate
14. Evaluation produces real failing metrics
15. Release is BLOCKED
16. Roll back
```

The intended interview message is:

> **Nuvorix demonstrates how an AI/ML workload moves from development through evaluation, governance, deployment, observability, and rollback.**

---

# 27. Final Engineering Principle

Do not optimize for the number of technologies in the README.

Optimize for:

> **One complete, truthful, reproducible AI/ML production lifecycle.**

A smaller system that genuinely works is stronger than a larger system filled with simulated integrations.
