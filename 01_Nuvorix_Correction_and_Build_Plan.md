# Nuvorix — Correction & Build Plan

## Purpose
Nuvorix is the flagship AI/ML Platform Engineering project.

> **A self-service platform for building, evaluating, deploying, governing, and operating ML and LLM workloads.**

The objective is to make the repository truthful, runnable, testable, and strongly aligned with AI Platform Engineer, MLOps/ML Platform Engineer, Backend Engineer, and Agentic AI Engineer roles.

---

## 1. Current State

The repository already contains a strong skeleton:

- FastAPI control plane
- PostgreSQL/SQLite support
- Redis integration
- React/Vite frontend
- Python CLI
- project/workload/model concepts
- evaluations API
- deployment and rollback API
- LLM gateway API
- incident API
- Prometheus metrics
- Docker Compose
- seed/demo data

The main issue is **implementation-to-README mismatch**. The README advertises capabilities including MLflow, LangGraph, MCP, OpenTelemetry, Kubernetes, Helm, Terraform, blue/green, and incident RCA, while several of these were not verified in the inspected repository state.

**Rule:** never claim a technology is implemented until the code, dependency, deployment, and verification path exist.

---

# 2. Immediate Corrections

## 2.1 Make the README truthful

Add an explicit implementation-status table.

| Capability | Status |
|---|---|
| FastAPI control plane | Implemented |
| PostgreSQL | Implemented |
| Redis | Implemented |
| CLI | Implemented |
| ML lifecycle | Partial |
| MLflow | Verify/Implement |
| RAG | Verify/Implement |
| LangGraph | Verify/Implement |
| MCP | Verify/Implement |
| Evaluation gates | Verify with real tests |
| Prometheus | Implemented |
| OpenTelemetry | Partial |
| Kubernetes | Partial |
| Helm | Not verified |
| Terraform | Not verified |
| Incident RCA | Prototype/Partial |
| LLM Gateway | Partial/Implemented |
| FinOps | Partial |

Remove any screenshot or prose claim that is not supported by actual code.

---

# 3. Dependency / Packaging Integrity

The root `pyproject.toml` currently includes core backend packages such as FastAPI, SQLAlchemy, sklearn, Prometheus and Click, but the platform README names additional AI/platform capabilities.

When each capability is truly implemented, align dependencies using `uv`:

```bash
uv add <package>
uv lock
uv sync
```

Potential requirements as features become real:

- langgraph
- mlflow
- pgvector-compatible DB integration
- embedding model/provider library
- OpenTelemetry packages
- Redis client
- pytest / pytest-asyncio
- Ruff
- mypy

Never manually edit `uv.lock`.

---

# 4. MLflow Lifecycle

Build a real lifecycle:

```text
Dataset
  ↓
Training
  ↓
MLflow Run
  ↓
Parameters + Metrics + Artifact
  ↓
Model Registry
  ↓
Evaluation
  ↓
Promotion
  ↓
Deployment
  ↓
Rollback
```

Acceptance criteria:

- deterministic dataset
- reproducible training command
- MLflow run created
- parameters recorded
- metrics recorded
- artifact stored
- registered model/version created
- platform metadata linked to version
- promotion updates state
- rollback restores a previously approved version

---

# 5. Real RAG Integration

Implement reusable retrieval infrastructure:

```text
PDF/DOCX/Markdown
       ↓
     Parser
       ↓
    Chunking
       ↓
    Metadata
       ↓
   Embeddings
       ↓
 PostgreSQL + pgvector
       ↓
    Retrieval
       ↓
 Optional reranking
       ↓
     Context
       ↓
       LLM
```

Required metadata:

- document_id
- source
- page
- chunk_id
- embedding_model
- ingestion_version
- created_at

Required API surface:

```text
POST /api/v1/knowledge-bases
POST /api/v1/knowledge-bases/{id}/documents
POST /api/v1/knowledge-bases/{id}/index
POST /api/v1/knowledge-bases/{id}/query
```

Retrieval must return source attribution.

---

# 6. Real LangGraph Agent Runtime

Use actual LangGraph for agent orchestration.

Target:

```text
Request
  ↓
Plan
  ↓
Tool
  ↓
Observation
  ↓
Decision
  ↓
Final Response
```

Persist:

- execution_id
- state
- node transitions
- tool calls
- timestamps
- outcome
- errors

Minimum real tools:

1. knowledge search
2. deployment status
3. read-only platform diagnostics

---

# 7. MCP

Create explicit tool contracts.

Example:

```yaml
name: get_deployment_status
risk: low
permissions:
  - deployment:read
```

Risky actions must pass:

```text
Agent request
 ↓
Authorization
 ↓
Policy
 ↓
Human approval if required
 ↓
Execution
```

Do not claim MCP merely because a Python class or tool registry is named MCP. Use an actual MCP-compatible implementation if the README says MCP.

---

# 8. Evaluation Engine

Separate evaluation into two modes.

### A. Deterministic regression

Use for:

- schema validation
- release policy
- deterministic business logic
- routing
- failure handling
- security rules

### B. Real AI evaluation

Use for:

- faithfulness
- answer correctness
- retrieval quality
- agent task success
- tool selection
- safety

Example release policy:

```yaml
min_faithfulness: 0.92
min_answer_correctness: 0.90
max_p95_latency_ms: 2000
max_cost_per_request: 0.01
max_regression_rate: 0.03
```

A failed evaluation must block release.

Never fabricate benchmark results.

---

# 9. LLM Gateway

Implement provider abstraction:

```text
Client
 ↓
Gateway
 ↓
Policy
 ↓
Budget
 ↓
Router
 ├── Provider A
 ├── Provider B
 └── Local Model
```

Capture:

- provider
- model
- input tokens
- output tokens
- latency
- status
- cost estimate
- workload
- version metadata

Provider credentials must come from secret configuration.

---

# 10. Kubernetes

Run the platform on kind and verify actual pods.

Minimum workloads:

```text
nuvorix-api
nuvorix-worker
nuvorix-evaluator
nuvorix-agent-runtime
nuvorix-gateway
postgres
redis
prometheus
grafana
```

Use:

- Namespace
- Deployment
- Service
- ConfigMap
- Secret
- ServiceAccount
- RBAC
- Job
- HPA
- resource requests/limits
- Ingress where needed

Phrase local support honestly as:

> Kubernetes deployment validated locally on kind.

Do not call that production cloud deployment.

---

# 11. Helm

Create a real chart:

```text
infra/helm/nuvorix/
├── Chart.yaml
├── values.yaml
└── templates/
```

Validate with:

```bash
helm lint
helm template .
helm install
helm upgrade
```

Configuration should cover:

- images
- replicas
- resources
- ports
- env
- secrets
- HPA

---

# 12. Terraform

Implement real IaC, not placeholder files.

Recommended structure:

```text
infra/terraform/
├── modules/
│   ├── postgres/
│   ├── redis/
│   ├── kubernetes/
│   └── observability/
└── environments/
    └── dev/
```

At minimum verify:

```bash
terraform fmt
terraform validate
terraform plan
```

Do not claim AWS/Azure/GCP support unless at least one real environment is implemented and tested.

---

# 13. OpenTelemetry

Prometheus metrics already exist in the inspected code. Add traces for:

- HTTP request
- DB operations where practical
- retrieval
- embeddings
- LLM request
- agent run
- tool call
- evaluation
- deployment

Example trace:

```text
HTTP Request
 ├── Retrieval
 ├── LLM
 └── Tool
```

---

# 14. Security

Implement and test:

### Authentication
Token-based API access.

### RBAC

- admin
- platform_engineer
- ml_engineer
- developer
- viewer

### Audit

Record:

- actor
- action
- resource
- timestamp
- result

### Secrets

- env vars for local development
- Kubernetes Secrets in-cluster
- no hardcoded API keys

---

# 15. CI/CD

PR pipeline:

```text
uv sync --frozen
 ↓
Ruff
 ↓
Mypy
 ↓
Pytest
 ↓
Security/dependency checks
```

Main pipeline:

```text
CI
 ↓
Evaluation
 ↓
Docker build
 ↓
Push image
 ↓
Staging
 ↓
Smoke tests
```

Failed AI regression/evaluation must be able to block a release.

---

# 16. Testing

### Unit

- release policy
- auth
- RBAC
- cost calculations
- schemas
- agent state transitions

### Integration

- PostgreSQL
- Redis
- RAG
- MLflow
- LLM gateway

### End-to-end

```text
Create project
 ↓
Create workload
 ↓
Evaluate
 ↓
Pass
 ↓
Deploy
 ↓
Observe
 ↓
Rollback
```

Also test failures such as:

- DB unavailable
- Redis unavailable
- provider timeout
- invalid model
- failed evaluation
- unauthorized tool
- deployment failure
- rollback failure

---

# 17. Final Demo

The strongest interview walkthrough is:

```text
Create workload
 ↓
Register knowledge
 ↓
Run LangGraph agent
 ↓
Use tool
 ↓
Capture trace
 ↓
Evaluate
 ↓
Pass release gate
 ↓
Deploy to Kubernetes
 ↓
Observe
 ↓
Introduce regressed candidate
 ↓
Release blocked
 ↓
Rollback
```

---

# 18. Definition of Done

- [ ] README matches implementation
- [ ] `uv sync` works
- [ ] tests pass
- [ ] Docker Compose works
- [ ] API works
- [ ] CLI works
- [ ] MLflow lifecycle works
- [ ] RAG works
- [ ] LangGraph agent works
- [ ] MCP compatibility is real if claimed
- [ ] evaluation gate works
- [ ] Kubernetes works on kind
- [ ] Prometheus metrics are real
- [ ] OpenTelemetry traces work or are explicitly marked pending
- [ ] RBAC/security is enforced
- [ ] CI passes
- [ ] benchmark claims are reproducible

## Non-Negotiable Rule

**Do not add technology just to increase README badge count.** A smaller set of real integrations is more valuable than a large list of unverified claims.
