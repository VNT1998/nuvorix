# Nuvorix — AI/ML Production Platform
## Agent Build Specification / Master Implementation Plan

> **Purpose:** This document is the source of truth for an autonomous coding agent (for example Antigravity CLI) building Nuvorix.
>
> **Primary objective:** Build a real, deployable AI/ML platform that demonstrates AI Platform Engineering, MLOps, Backend Engineering, GenAI/Agentic AI, Kubernetes, observability, security, CI/CD, and infrastructure-as-code.
>
> **Important:** Build working software in incremental phases. Do not create fake integrations, placeholder dashboards, or documentation claiming features that do not work.

---

# 1. Product Definition

## 1.1 Product name

**Nuvorix**

## 1.2 Product tagline

> **A self-service platform for building, evaluating, deploying, governing, and operating ML and LLM workloads.**

## 1.3 Problem

AI/ML teams repeatedly rebuild infrastructure for:

- experiments
- model tracking
- model/version management
- RAG ingestion and retrieval
- agent orchestration
- deployment
- evaluation
- observability
- secrets
- access control
- release gates
- rollback
- cost monitoring

Nuvorix should provide reusable platform primitives so an ML/AI engineer can move from experimentation to production without rebuilding these capabilities for every project.

## 1.4 Core product statement

Nuvorix should make this workflow possible:

```text
Create workload
    ↓
Develop
    ↓
Register datasets / models / prompts / agent versions
    ↓
Evaluate
    ↓
Apply release policy
    ↓
Deploy
    ↓
Observe
    ↓
Detect regressions/incidents
    ↓
Rollback or remediate
```

---

# 2. Primary Users

## 2.1 AI/ML Engineer

Needs:

- experiments
- datasets
- model versions
- evaluation
- deployment
- monitoring

## 2.2 GenAI Engineer

Needs:

- prompts
- RAG
- embeddings
- agents
- tools
- MCP
- memory
- evaluation
- LLM routing

## 2.3 Platform Engineer

Needs:

- reusable APIs
- CLI
- SDK
- workloads
- environments
- deployment
- observability
- security
- infrastructure automation

## 2.4 Platform/SRE/Operations Engineer

Needs:

- logs
- metrics
- traces
- alerts
- incidents
- RCA
- rollback
- health checks

---

# 3. Design Principles

## 3.1 Build a platform, not a demo

Avoid:

- chatbot-only UI
- hardcoded model providers
- hardcoded credentials
- fake metrics
- fake Kubernetes screens
- fake Terraform modules
- README-only integrations
- unimplemented buttons

Every major UI action should map to a real backend capability.

## 3.2 Prefer composable services

Use clear boundaries:

- control plane
- workload execution
- evaluation
- retrieval
- agent runtime
- gateway
- observability
- deployment

Do not prematurely split every component into a separate microservice. Start as a modular monorepo/application with clear internal boundaries and extract workers/services where useful.

## 3.3 Local-first

The project must run locally using:

- Docker Compose for development
- kind for Kubernetes development

Do not require paid cloud infrastructure to run the core product.

Cloud deployment should be supported as an optional extension.

## 3.4 Production-minded engineering

Include:

- type checking
- validation
- unit tests
- integration tests
- structured logs
- health checks
- idempotent APIs where appropriate
- timeouts
- retries
- configuration management
- secrets handling
- migrations
- graceful failure
- API documentation

## 3.5 Honest observability

Only show metrics actually collected by the platform.

## 3.6 Do not overengineer the MVP

Implement the smallest complete end-to-end path first.

---

# 4. Recommended Technology Stack

Use the following defaults unless there is a strong technical reason not to.

## Backend

- Python 3.12+
- FastAPI
- Pydantic v2
- SQLAlchemy
- PostgreSQL
- Alembic
- Redis
- `uv` for dependency management and execution

**User preference:** always use `uv` instead of pip-oriented workflows.

## ML

- scikit-learn initially
- MLflow
- joblib where appropriate

Later:

- PyTorch
- Hugging Face

## GenAI

- LangGraph
- Pydantic
- MCP/tool interfaces
- configurable model provider abstraction
- Hugging Face embeddings or provider-backed embeddings

## RAG

- PostgreSQL + pgvector initially
- PyMuPDF / Unstructured for document parsing
- embedding model abstraction
- optional reranker

## Observability

- OpenTelemetry
- Prometheus
- Grafana
- Loki (or a clean log collector abstraction)

## Containerization

- Docker
- Docker Compose

## Kubernetes

- kind locally
- Kubernetes Deployments
- Services
- Jobs
- CronJobs
- ConfigMaps
- Secrets
- HPA
- RBAC
- Ingress
- resource requests/limits
- optional NetworkPolicy

## Packaging / deployment

- Helm
- GitHub Actions
- GHCR
- Terraform
- ArgoCD later, not MVP

## Quality

- pytest
- Ruff
- mypy
- optional pre-commit

## Frontend

Use:

- Next.js or React
- TypeScript
- simple professional admin/platform UI

Do not spend disproportionate time on visual polish.

---

# 5. High-Level Architecture

```text
                         ┌──────────────────────┐
                         │      Nuvorix UI      │
                         │     React/Next.js    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       FastAPI        │
                         │     Control Plane    │
                         └──────────┬───────────┘
                                    │
        ┌───────────────────────────┼────────────────────────────┐
        │                           │                            │
        ▼                           ▼                            ▼
  Project/Workload API       Evaluation API              Deployment API
        │                           │                            │
        └───────────────────────────┼────────────────────────────┘
                                    │
                              Orchestration
                                    │
         ┌──────────────────────────┼───────────────────────────┐
         │                          │                           │
         ▼                          ▼                           ▼
     ML Platform             GenAI Platform               Gateway
         │                          │                           │
    Training                 RAG Pipeline                Model Router
    Experiments              Agent Runtime               Usage Metering
    Registry                 MCP Tools                    Cost
    Artifacts                Memory                       Policies
         │                          │                           │
         └──────────────────────────┼───────────────────────────┘
                                    │
                              Release Engine
                                    │
                     ┌──────────────┴─────────────┐
                     ▼                            ▼
                  Staging                     Production
                     │                            │
                     └──────────────┬─────────────┘
                                    ▼
                               Kubernetes
                                    │
                     ┌──────────────┼──────────────┐
                     ▼              ▼              ▼
                  Metrics         Logs           Traces
                     │              │              │
                     └──────────────┼──────────────┘
                                    ▼
                                  Grafana
                                    │
                                    ▼
                              Incident Engine
```

---

# 6. Repository Structure

Create a monorepo with a structure close to:

```text
nuvorix/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── db/
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── services/
│   │   │   └── main.py
│   │   └── tests/
│   ├── worker/
│   │   ├── app/
│   │   └── tests/
│   └── web/
│       ├── app/
│       ├── components/
│       ├── lib/
│       └── tests/
│
├── packages/
│   ├── sdk-python/
│   ├── cli/
│   ├── schemas/
│   ├── evaluation/
│   ├── rag/
│   ├── agents/
│   ├── gateway/
│   ├── observability/
│   └── policy/
│
├── workloads/
│   ├── demo-ml-model/
│   ├── demo-rag-agent/
│   └── demo-medical-agent/
│
├── infra/
│   ├── docker/
│   ├── compose/
│   ├── helm/
│   ├── terraform/
│   └── kind/
│
├── datasets/
│   └── demo-evaluations/
│
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── runbooks/
│   ├── tutorials/
│   └── decisions/
│
├── scripts/
├── .github/
│   └── workflows/
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

The exact directory layout may be adapted, but the logical boundaries must remain clear.

---

# 7. Domain Model

Implement the following core entities.

## 7.1 Organization

```text
id
name
created_at
```

## 7.2 User

```text
id
organization_id
email
name
role
created_at
```

Roles:

- admin
- platform_engineer
- ml_engineer
- developer
- viewer

## 7.3 Project

```text
id
organization_id
name
description
created_at
```

## 7.4 Environment

```text
id
project_id
name
type
```

Examples:

- dev
- staging
- production

## 7.5 Workload

A generic unit representing an ML model, RAG service, or agent.

```text
id
project_id
name
type
status
created_at
```

Types:

- ml_model
- rag
- agent
- llm_service

## 7.6 Model

```text
id
workload_id
name
framework
created_at
```

## 7.7 ModelVersion

```text
id
model_id
version
artifact_uri
metrics_json
parameters_json
status
created_at
```

## 7.8 Dataset

```text
id
project_id
name
version
uri
schema_json
created_at
```

## 7.9 EvaluationRun

```text
id
workload_id
version
status
metrics_json
passed
started_at
completed_at
```

## 7.10 Deployment

```text
id
workload_id
version
environment
strategy
status
created_at
```

## 7.11 Incident

```text
id
project_id
severity
title
status
root_cause
recommendation
confidence
created_at
resolved_at
```

## 7.12 AuditEvent

```text
id
organization_id
user_id
action
resource_type
resource_id
metadata_json
created_at
```

---

# 8. Phase 1 — Control Plane API

## Goal

Create a functional FastAPI control plane.

## Required endpoints

### Projects

```http
POST   /api/v1/projects
GET    /api/v1/projects
GET    /api/v1/projects/{project_id}
DELETE /api/v1/projects/{project_id}
```

### Workloads

```http
POST /api/v1/projects/{project_id}/workloads
GET  /api/v1/projects/{project_id}/workloads
GET  /api/v1/workloads/{workload_id}
```

### Models

```http
POST /api/v1/workloads/{workload_id}/models
GET  /api/v1/workloads/{workload_id}/models
```

### Versions

```http
POST /api/v1/models/{model_id}/versions
GET  /api/v1/models/{model_id}/versions
GET  /api/v1/model-versions/{version_id}
```

### Deployments

```http
POST /api/v1/workloads/{workload_id}/deployments
GET  /api/v1/workloads/{workload_id}/deployments
POST /api/v1/deployments/{deployment_id}/rollback
```

### Health

```http
GET /health
GET /ready
```

Health endpoints must actually check required dependencies for readiness.

---

# 9. Phase 2 — ML Platform

## Goal

Turn the existing learning MLOps concept into a platform capability.

Pipeline:

```text
Dataset
   ↓
Validation
   ↓
Training
   ↓
MLflow Run
   ↓
Evaluation
   ↓
Quality Gate
   ↓
Model Registry
   ↓
Promotion
```

## Requirements

1. Dataset metadata registration.
2. Training job execution.
3. MLflow experiment tracking.
4. Parameter logging.
5. Metrics logging.
6. Artifact storage.
7. Model registration.
8. Versioning.
9. Quality thresholds.
10. Promotion to staging/production.
11. Rollback.

## Demo model

Start with a simple sklearn regression model so the platform proves the lifecycle rather than model novelty.

The demo model should support:

- train
- evaluate
- register
- deploy
- predict

Do not spend time searching for a fancy model.

---

# 10. Phase 3 — RAG Platform

## Goal

Create a reusable production-oriented retrieval subsystem.

## Ingestion flow

```text
Document
 ↓
Parse
 ↓
Normalize
 ↓
Chunk
 ↓
Metadata
 ↓
Embed
 ↓
pgvector
```

## Retrieval flow

```text
Query
 ↓
Normalize
 ↓
Vector retrieval
 ↓
Metadata filtering
 ↓
Optional reranking
 ↓
Context assembly
 ↓
LLM
```

## Required APIs

```http
POST /api/v1/knowledge-bases
POST /api/v1/knowledge-bases/{id}/documents
POST /api/v1/knowledge-bases/{id}/index
POST /api/v1/knowledge-bases/{id}/query
GET  /api/v1/knowledge-bases/{id}/documents
```

## Required metadata

Store:

- document_id
- source
- title
- page
- chunk_id
- ingestion_version
- embedding_model
- created_at

## Quality requirements

The retrieval response should include:

```json
{
  "query": "...",
  "results": [
    {
      "chunk_id": "...",
      "score": 0.92,
      "source": "...",
      "page": 4,
      "text": "..."
    }
  ]
}
```

---

# 11. Phase 4 — Agent Runtime

## Goal

Build a reusable agent runtime rather than a single hardcoded agent.

## Architecture

```text
Request
  ↓
Agent Definition
  ↓
LangGraph State
  ↓
Planner/Decision
  ↓
Tool Calls
  ↓
Observation
  ↓
Next Step
  ↓
Final Response
```

## Capabilities

- state
- retries
- timeouts
- tool calling
- structured output
- human approval state
- memory
- tracing
- execution history

## MCP tools

Create at least three demo tools:

1. knowledge search
2. project/deployment status
3. safe read-only diagnostics

Later add:

- GitHub lookup
- Kubernetes diagnostics
- metrics lookup

## Tool permission model

Each tool must declare:

```yaml
name: get_deployment_status
risk: low
permissions:
  - read:deployment
```

Dangerous operations must require explicit authorization and/or human approval.

---

# 12. Phase 5 — Evaluation Engine

## Goal

Automatically decide whether a workload version is safe to release.

## Evaluation categories

### ML

- accuracy
- RMSE/MAE depending on model
- data/schema validation

### RAG

- retrieval recall
- faithfulness
- answer correctness
- citation correctness

### Agent

- task success
- tool selection correctness
- tool-call validity
- safety checks
- regression rate

### Runtime

- latency
- error rate
- token usage
- cost

## Evaluation API

```http
POST /api/v1/evaluations
GET  /api/v1/evaluations/{id}
POST /api/v1/evaluations/{id}/approve
```

## Evaluation policy example

```yaml
min_faithfulness: 0.92
min_answer_correctness: 0.90
max_p95_latency_ms: 2000
max_cost_per_request: 0.01
max_regression_rate: 0.03
```

## Release decision

Return:

```json
{
  "decision": "BLOCK",
  "reasons": [
    "faithfulness below threshold",
    "latency regression > 25%"
  ],
  "metrics": {}
}
```

Never silently deploy a failed candidate.

---

# 13. Phase 6 — LLM Gateway

## Goal

Provide a provider-agnostic abstraction for LLM requests.

## Responsibilities

- model selection
- routing
- fallback
- timeout
- retries
- usage metering
- cost calculation
- policy enforcement
- request tracing

## Logical architecture

```text
Application
    ↓
Nuvorix Gateway
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

## Usage record

```json
{
  "provider": "...",
  "model": "...",
  "input_tokens": 1234,
  "output_tokens": 321,
  "latency_ms": 802,
  "estimated_cost": 0.0042,
  "status": "success"
}
```

Provider credentials must come from a secret mechanism, never source code.

---

# 14. Phase 7 — Kubernetes

## Goal

Run the platform locally on kind.

## Required Kubernetes resources

- Namespace
- Deployment
- Service
- ConfigMap
- Secret
- Job
- CronJob
- HPA
- Ingress
- ServiceAccount
- Role
- RoleBinding
- Resource requests/limits

## Core workloads

```text
nuvorix-api
nuvorix-worker
nuvorix-evaluator
nuvorix-gateway
nuvorix-agent-runtime
nuvorix-rag-worker
postgres
redis
mlflow
prometheus
grafana
```

Do not claim high availability if running only a single-node kind environment.

---

# 15. Phase 8 — Helm

Create a real Helm chart.

Requirements:

- values-driven configuration
- image tags
- resource configuration
- environment variables
- secret references
- service configuration
- ingress
- HPA configuration

Support:

```bash
helm install nuvorix ./infra/helm/nuvorix
helm upgrade nuvorix ./infra/helm/nuvorix
helm uninstall nuvorix
```

---

# 16. Phase 9 — Terraform

## Goal

Demonstrate infrastructure-as-code.

Start local/dev-friendly.

Modules should conceptually cover:

```text
network
database
storage
kubernetes
observability
```

Environments:

```text
dev
staging
production
```

Each environment should have separate configuration.

Avoid creating fake AWS modules that are never tested.

If cloud infrastructure is added later, implement one real provider end-to-end rather than mentioning multiple clouds without implementation.

---

# 17. Phase 10 — CI/CD

## Pull request pipeline

```text
Checkout
 ↓
Install via uv
 ↓
Lint
 ↓
Type check
 ↓
Unit tests
 ↓
Integration tests
 ↓
Security/dependency scan
```

## Main branch pipeline

```text
Tests
 ↓
Evaluation
 ↓
Docker Build
 ↓
Push image
 ↓
Deploy staging
 ↓
Smoke test
 ↓
Release approval
 ↓
Deploy production
```

The release pipeline must be able to block a deployment when evaluation fails.

---

# 18. Phase 11 — Observability

## OpenTelemetry

Instrument:

- API request
- DB query
- retrieval
- embedding
- LLM call
- tool call
- deployment action
- evaluation run

## Prometheus metrics

At minimum:

```text
nuvorix_http_requests_total
nuvorix_http_request_duration_seconds
nuvorix_errors_total
nuvorix_llm_requests_total
nuvorix_llm_latency_seconds
nuvorix_llm_input_tokens_total
nuvorix_llm_output_tokens_total
nuvorix_llm_cost_total
nuvorix_retrieval_latency_seconds
nuvorix_tool_calls_total
nuvorix_tool_failures_total
nuvorix_evaluation_runs_total
nuvorix_deployment_total
nuvorix_incidents_total
```

## Grafana dashboards

Create at least:

1. Platform health
2. AI/LLM usage
3. RAG performance
4. Deployment health
5. Cost

Do not hardcode dashboard numbers.

---

# 19. Phase 12 — Security

## Authentication

Implement an authentication abstraction that can later support external OAuth/OIDC.

For local development, allow a safe dev mode.

## RBAC

Enforce access server-side.

Example:

```text
admin
platform_engineer
ml_engineer
developer
viewer
```

## Secrets

Support:

- environment configuration locally
- Kubernetes Secret references in cluster
- provider abstraction for future secret managers

## Audit log

Record:

- login
- workload creation
- model registration
- deployment
- rollback
- policy decision
- tool authorization
- secret access where appropriate

## Guardrails

At minimum:

- prompt injection detection hook
- sensitive data detection hook
- tool authorization
- dangerous action approval
- output policy validation

Do not claim regulatory compliance. The system can be designed with security/audit controls without claiming compliance certification.

---

# 20. Phase 13 — Deployment Strategies

## Blue/Green

Implement a demonstrable workflow:

```text
Blue = current
Green = candidate

Test Green
 ↓
Health
 ↓
Smoke tests
 ↓
Evaluation
 ↓
Switch traffic
```

## Canary

Implement later:

```text
95% → stable
5%  → candidate
```

Monitor:

- error rate
- latency
- evaluation score
- cost

Automatic rollback should be guarded by explicit policy.

---

# 21. Phase 14 — Cost / FinOps

Track costs at:

- organization
- project
- workload
- agent
- model
- request
- environment

Calculate:

```text
LLM cost
Embedding cost
Compute estimate
Storage estimate
Network estimate
Total workload cost
```

Expose:

```http
GET /api/v1/costs
GET /api/v1/projects/{id}/costs
GET /api/v1/workloads/{id}/costs
```

UI should show:

- total spend
- daily trend
- cost per request
- cost by model
- cost by workload

Cost numbers must clearly identify whether they are actual provider charges or estimates.

---

# 22. Phase 15 — Incident Detection and RCA Agent

## Goal

Demonstrate AI-assisted platform operations.

Trigger:

- error-rate spike
- latency spike
- pod crash loop
- deployment regression
- retrieval degradation

Incident workflow:

```text
Signal
 ↓
Incident
 ↓
Collect evidence
    ├── metrics
    ├── logs
    ├── traces
    ├── deployments
    ├── git commits
    └── Kubernetes state
 ↓
Agent analysis
 ↓
Root cause hypothesis
 ↓
Recommended action
 ↓
Human approval
 ↓
Execution
 ↓
Verification
```

Example result:

```text
Incident #142

Severity: HIGH

Finding:
Candidate deployment v27 correlates with a 312% increase in retrieval latency.

Evidence:
- retrieval span latency increased after deployment
- error rate stable
- pod CPU normal
- new embedding configuration introduced in v27

Recommendation:
Rollback to v26.

Confidence: 0.92
```

The agent must distinguish:

- observed evidence
- inference
- recommendation

Never pretend certainty when evidence is weak.

---

# 23. Phase 16 — Demo Workloads

Create three example workloads.

## 23.1 Demo ML workload

Simple sklearn model.

Shows:

- train
- evaluate
- register
- serve
- promote
- rollback

## 23.2 Demo RAG Agent

Example domain:

customer support / technical knowledge.

Shows:

- document ingestion
- embeddings
- retrieval
- reranking if implemented
- LangGraph
- MCP
- evaluation
- deployment
- tracing

## 23.3 Demo Medical AI workload

Use a safe demonstration workload with synthetic/publicly usable data.

Potential flow:

```text
Clinical-style document
 ↓
structured extraction
 ↓
retrieval
 ↓
model inference
 ↓
evidence-backed summary
```

Important:

- clearly label as a technical demonstration
- do not present it as medical diagnosis
- do not claim clinical validation
- do not claim compliance certification

The medical workload exists mainly to demonstrate that the platform can support high-stakes AI workloads with evaluation, auditability and guardrails.

---

# 24. CLI Requirements

Create a Python CLI.

Examples:

```bash
nuvorix init my-agent
nuvorix project create support-platform
nuvorix workload create support-agent --type agent
nuvorix dataset register eval-set.jsonl
nuvorix evaluate support-agent
nuvorix deploy support-agent --env staging
nuvorix status support-agent
nuvorix logs support-agent
nuvorix rollback support-agent
```

Commands should call actual APIs.

Do not create commands that only print fake success messages.

---

# 25. Python SDK

Provide a basic SDK:

```python
from nuvorix import NuvorixClient

client = NuvorixClient(base_url="http://localhost:8000")

project = client.projects.create(
    name="support-ai",
    description="Customer support AI workload",
)
```

SDK modules:

```text
projects
workloads
models
datasets
evaluations
deployments
costs
incidents
```

The SDK should be versioned separately from the API schema where practical.

---

# 26. Web UI

Build a practical platform console.

## Dashboard

Show:

- projects
- active workloads
- deployments
- evaluations
- incidents
- cost

## Project page

Show:

- workloads
- models
- evaluations
- deployments
- recent activity

## Workload page

Tabs:

- Overview
- Versions
- Evaluations
- Deployments
- Traces
- Costs
- Logs

## Deployment page

Show:

- candidate
- current
- rollout state
- health
- metrics
- rollback button

## Incident page

Show:

- severity
- signals
- evidence
- root cause
- recommendation
- approval action

---

# 27. Evaluation Dataset

Create a deterministic demo evaluation set.

For RAG:

```json
{
  "question": "...",
  "expected_answer": "...",
  "expected_sources": ["doc-1"]
}
```

For agents:

```json
{
  "task": "...",
  "expected_tools": ["search_knowledge"],
  "expected_outcome": "..."
}
```

Create enough examples to detect regressions.

Do not report invented benchmark performance.

---

# 28. Testing Strategy

## Unit tests

Test:

- schemas
- business rules
- release policy
- cost calculations
- tool authorization
- evaluation decisions

## Integration tests

Test:

- API + PostgreSQL
- API + Redis
- RAG indexing
- retrieval
- MLflow interaction
- deployment state transitions

## End-to-end test

The most important test:

```text
Create project
 ↓
Create workload
 ↓
Run evaluation
 ↓
Pass
 ↓
Deploy
 ↓
Observe
 ↓
Rollback
```

## Failure tests

Also test:

- invalid workload
- missing model
- evaluation failure
- provider timeout
- vector DB unavailable
- Redis unavailable
- unauthorized tool
- failed deployment
- rollback failure

---

# 29. Reliability Requirements

Every external call should have:

- timeout
- error handling
- retry where appropriate
- structured failure reason

Avoid retry storms.

Use idempotency keys for operations that may be retried.

Examples:

```text
deployment creation
promotion
rollback
evaluation execution
artifact registration
```

---

# 30. Data / Database Requirements

Use PostgreSQL migrations via Alembic.

Never change production schema manually.

Create seed data for:

- demo organization
- users
- projects
- workloads
- sample versions

Seed data must be obviously demo data.

---

# 31. Configuration

Provide:

```text
.env.example
```

Never commit secrets.

Configuration categories:

```text
DATABASE_URL
REDIS_URL
MLFLOW_TRACKING_URI
OTEL_ENDPOINT
PROMETHEUS_ENDPOINT
LLM_PROVIDER
LLM_API_KEY
EMBEDDING_PROVIDER
EMBEDDING_API_KEY
```

Use typed settings.

---

# 32. Local Development

The full core stack must start with something like:

```bash
uv sync
docker compose up -d
uv run alembic upgrade head
uv run pytest
uv run python -m ...
```

Provide a single documented bootstrap command/script where practical.

For Kubernetes:

```bash
kind create cluster --name nuvorix
helm install ...
```

---

# 33. Docker Requirements

Every deployable service must have a Dockerfile.

Use:

- slim base images where practical
- non-root user
- pinned dependencies/lockfile
- health checks where applicable
- multi-stage builds where useful

Do not run containers as root unless there is a documented reason.

---

# 34. CI/CD Requirements

GitHub Actions workflows:

```text
ci.yml
release.yml
```

CI should run:

```bash
uv sync --frozen
uv run ruff check .
uv run mypy .
uv run pytest
```

Build container images and push to GHCR only from trusted workflows.

Do not expose long-lived registry credentials if avoidable.

---

# 35. Documentation Requirements

Create:

## README.md

Include:

- what Nuvorix is
- architecture
- quick start
- demo
- screenshots
- API overview
- development
- deployment
- roadmap

## docs/architecture/

Include:

- system architecture
- request lifecycle
- RAG lifecycle
- agent lifecycle
- evaluation lifecycle
- deployment lifecycle

## docs/runbooks/

At least:

- API unhealthy
- database unavailable
- Redis unavailable
- deployment rollback
- model rollback
- high latency
- high LLM cost
- failed evaluation
- vector search degradation

## docs/decisions/

Use ADRs for major decisions.

---

# 36. Security Rules for the Coding Agent

The implementation agent must:

1. Never commit secrets.
2. Never print secret values in logs.
3. Never hardcode provider API keys.
4. Never disable authentication as a permanent shortcut.
5. Never bypass RBAC in backend logic.
6. Never implement dangerous tools without authorization.
7. Never claim regulatory compliance.
8. Never fabricate performance metrics.
9. Never claim cloud/GPU deployment unless tested.
10. Never mark incomplete features as production-ready.

---

# 37. MVP Definition

The MVP is complete only when all of the following are true:

## Control plane

- [ ] Projects work
- [ ] Workloads work
- [ ] Models/versioning work
- [ ] Deployments work
- [ ] PostgreSQL persistence works
- [ ] OpenAPI docs work

## ML

- [ ] Demo model trains
- [ ] MLflow run is created
- [ ] Model is registered
- [ ] Evaluation runs
- [ ] Release gate works

## RAG

- [ ] Documents ingest
- [ ] Embeddings are created
- [ ] pgvector stores vectors
- [ ] Retrieval works
- [ ] Source metadata is returned

## Agent

- [ ] LangGraph workflow works
- [ ] At least 3 tools work
- [ ] MCP-compatible tool interface exists
- [ ] Tool authorization works
- [ ] Execution state is persisted

## Deployment

- [ ] Docker build works
- [ ] Kubernetes deployment works on kind
- [ ] Health checks work
- [ ] Rollback works

## Observability

- [ ] Prometheus metrics are real
- [ ] OpenTelemetry traces exist for key paths
- [ ] Grafana dashboard shows real metrics

## CI

- [ ] Tests run in CI
- [ ] Image builds
- [ ] Evaluation gate can block release

## UI

- [ ] Project dashboard works
- [ ] Workload page works
- [ ] Evaluation results visible
- [ ] Deployment state visible
- [ ] Logs/traces/cost visible

---

# 38. V2 Definition

After MVP:

- [ ] Terraform
- [ ] Helm production hardening
- [ ] RBAC UI
- [ ] Audit events
- [ ] LLM Gateway
- [ ] Cost tracking
- [ ] Blue/green deployment
- [ ] Canary deployment
- [ ] better OpenTelemetry coverage
- [ ] policy-as-code integration
- [ ] optional ArgoCD

---

# 39. V3 Definition

Later:

- [ ] Incident RCA agent
- [ ] automated rollback
- [ ] GPU scheduling
- [ ] model autoscaling
- [ ] advanced cost optimization
- [ ] multi-cloud
- [ ] policy engine/OPA
- [ ] advanced model routing
- [ ] fine-tuning workflow
- [ ] distributed workload scheduling

---

# 40. Demo Script

The final demo should tell a coherent story.

## Scenario

Deploy a knowledge-support agent.

### Step 1

Create project:

```bash
nuvorix project create support-ai
```

### Step 2

Create workload:

```bash
nuvorix workload create support-agent --type agent
```

### Step 3

Ingest knowledge:

```bash
nuvorix knowledge upload ./docs/
```

### Step 4

Run evaluation:

```bash
nuvorix evaluate support-agent
```

### Step 5

Show:

```text
Faithfulness: 96.1%
Answer correctness: 93.4%
Tool success: 99.1%
p95 latency: 1.32s
Cost/request: $0.006
```

Only show metrics actually produced by the evaluation system.

### Step 6

Deploy:

```bash
nuvorix deploy support-agent --env staging
```

### Step 7

Show Kubernetes pods.

### Step 8

Open Grafana.

### Step 9

Show trace:

```text
API
 ├─ retrieval
 ├─ embedding
 ├─ LLM
 └─ tool call
```

### Step 10

Introduce an intentionally bad candidate version.

### Step 11

Run evaluation.

### Step 12

Show release blocked.

### Step 13

Fix candidate.

### Step 14

Deploy.

### Step 15

Show successful rollout.

This is the primary portfolio story.

---

# 41. Interview Discussion Points

The implementation should make it possible to discuss:

## Why PostgreSQL?

Metadata, transactional state, audit logs, deployment state, users, projects.

## Why Redis?

Caching, short-lived state, queue coordination, rate limiting.

## Why MLflow?

Experiment and model lifecycle rather than inventing another registry.

## Why pgvector?

Start simple and unified with Postgres; decouple retrieval layer so another vector database can be added later.

## Why LangGraph?

Explicit stateful orchestration for multi-step agent workflows.

## Why MCP?

Standardized tool interfaces and permission boundaries.

## Why Kubernetes?

Scheduling, isolation, scaling, deployment primitives.

## Why Terraform?

Environment reproducibility and infrastructure lifecycle.

## Why OpenTelemetry?

Portable traces/telemetry across platform components.

## Why release gates?

Prevent candidate versions from reaching production without evidence.

## How to handle LLM failure?

Timeouts, retries where safe, fallback routing, circuit breakers, structured errors.

## How to control cost?

Usage metering, budgets, routing, caching, model selection and alerts.

## How to secure tools?

RBAC + policy checks + explicit permission scopes + human approval for high-risk actions.

## How to debug incidents?

Correlate deployment, logs, metrics and traces before proposing remediation.

---

# 42. Non-Goals

Do NOT prioritize these during the initial build:

- consumer-facing chatbot
- fancy landing-page animations
- multi-cloud implementation
- custom LLM training from scratch
- custom vector database
- custom Kubernetes operator
- complex billing
- social features
- excessive microservices
- generic AI chat UI
- premature service mesh
- real healthcare production claims

---

# 43. Agent Execution Rules

The coding agent MUST follow this process.

## Step 1 — Inspect

Before writing code:

- inspect repository
- identify existing files
- detect existing services
- preserve useful work
- check dependency management
- check Docker/K8s availability

## Step 2 — Plan

Create/maintain:

```text
docs/IMPLEMENTATION_STATUS.md
```

Track:

- completed
- in progress
- blocked
- not started

## Step 3 — Implement one vertical slice

Do not create dozens of disconnected modules.

Preferred sequence:

```text
API
 ↓
DB
 ↓
Business logic
 ↓
Test
 ↓
UI
```

Then add the next capability.

## Step 4 — Verify

After every meaningful phase:

- run tests
- run type checks
- run lint
- build container
- run smoke test

## Step 5 — Update documentation

Documentation must reflect actual implementation status.

## Step 6 — Commit logically

Use focused commits such as:

```text
feat: add workload control plane
feat: add mlflow model lifecycle
feat: add rag ingestion service
feat: add langgraph agent runtime
feat: add evaluation gates
feat: add kubernetes deployment
feat: add observability
```

---

# 44. Quality Gate for Each Phase

A phase is not complete just because source files exist.

It is complete when:

1. feature works locally
2. feature is tested
3. feature has error handling
4. feature is documented
5. feature is integrated with the platform
6. feature is observable where appropriate
7. feature can be demonstrated

---

# 45. Final Acceptance Criteria

The final MVP should support this complete path:

```text
Developer
   ↓
CLI / UI
   ↓
Create Project
   ↓
Create Agent
   ↓
Register Knowledge Base
   ↓
Ingest Documents
   ↓
Build RAG index
   ↓
Run LangGraph agent
   ↓
Call MCP tools
   ↓
Capture traces
   ↓
Run evaluation
   ↓
Pass release gate
   ↓
Build container
   ↓
Deploy to Kubernetes
   ↓
Observe with Prometheus/Grafana
   ↓
Track cost
   ↓
Rollback when needed
```

If this end-to-end path works, Nuvorix is already a strong portfolio project.

---

# 46. Portfolio Positioning

## Resume

**Nuvorix — AI/ML Production Platform**

> Built a self-service AI/ML platform for developing, evaluating, deploying, governing and operating ML/LLM workloads, integrating MLflow model lifecycle management, production RAG, LangGraph/MCP agent orchestration, automated evaluation gates, Kubernetes deployment, CI/CD, observability, RBAC and cost monitoring.

Only include technologies/features that are actually implemented.

## GitHub

The repository should show:

- professional README
- architecture diagram
- quick start
- screenshots
- demo GIF/video if available
- API docs
- deployment instructions
- technical decisions
- test coverage/report where meaningful
- roadmap

---

# 47. Priority Matrix

| Feature | Priority |
|---|---:|
| FastAPI control plane | P0 |
| PostgreSQL | P0 |
| MLflow lifecycle | P0 |
| RAG / pgvector | P0 |
| LangGraph agent | P0 |
| MCP tools | P0 |
| Evaluation gates | P0 |
| Docker | P0 |
| Kubernetes | P0 |
| Basic Prometheus/Grafana | P0 |
| CLI | P1 |
| Python SDK | P1 |
| CI/CD | P1 |
| Helm | P1 |
| Terraform | P1 |
| RBAC | P1 |
| Secrets | P1 |
| LLM gateway | P1 |
| Cost tracking | P1 |
| OpenTelemetry deep integration | P1 |
| Blue/green | P2 |
| Canary | P2 |
| Incident RCA agent | P2 |
| ArgoCD | P2 |
| OPA/policy-as-code | P2 |
| GPU workflows | P3 |
| Fine-tuning pipeline | P3 |
| Multi-cloud | P3 |

---

# 48. Final Instruction to the Coding Agent

Build Nuvorix as a **real, testable, locally deployable AI/ML platform**.

Do not optimize for number of technologies.

Optimize for:

1. working end-to-end workflows
2. clear architecture
3. reusable platform abstractions
4. production-minded engineering
5. observability
6. security
7. reproducibility
8. demonstrable AI capabilities
9. excellent developer experience
10. truthful documentation

The highest-priority outcome is:

> **A developer can create an AI workload, evaluate it, deploy it to Kubernetes, observe it, and safely roll it back using Nuvorix.**

Everything else is secondary.
