from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# --- Health & Status ---
class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    timestamp: datetime


class ReadyResponse(BaseModel):
    ready: bool
    dependencies: dict[str, str]


# --- Projects ---
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = ""


class ProjectResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Workloads ---
class WorkloadCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: str = Field("agent", description="ml_model, rag, agent, or llm_service")


class WorkloadResponse(BaseModel):
    id: str
    project_id: str
    name: str
    type: str
    status: str
    active_version: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Models & Versions ---
class ModelCreate(BaseModel):
    name: str
    framework: str = "scikit-learn"


class ModelResponse(BaseModel):
    id: str
    workload_id: str
    name: str
    framework: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelVersionCreate(BaseModel):
    version: str
    artifact_uri: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)


class ModelVersionResponse(BaseModel):
    id: str
    model_id: str
    version: str
    artifact_uri: str
    metrics_json: dict[str, Any]
    parameters_json: dict[str, Any]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainModelRequest(BaseModel):
    model_name: str = "linear_regressor"
    dataset_name: str | None = "california_housing_demo"
    hyperparameters: dict[str, Any] = Field(default_factory=lambda: {"alpha": 1.0, "max_iter": 1000})


class TrainModelResponse(BaseModel):
    model_id: str
    version_id: str
    version: str
    metrics: dict[str, float]
    artifact_uri: str
    status: str


class PromoteVersionRequest(BaseModel):
    target_environment: str = Field("staging", description="staging or production")


# --- Knowledge Base & RAG ---
class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str | None = ""
    embedding_model: str = "text-embedding-3-small"


class KnowledgeBaseResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: str
    embedding_model: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentIngestRequest(BaseModel):
    title: str
    content: str
    source_uri: str | None = "manual_upload"


class DocumentResponse(BaseModel):
    id: str
    knowledge_base_id: str
    title: str
    source_uri: str
    chunk_count: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RetrievalChunk(BaseModel):
    chunk_id: str
    document_id: str
    score: float
    source: str
    title: str
    text: str


class QueryRequest(BaseModel):
    query: str
    top_k: int = 4
    min_score: float = 0.0


class QueryResponse(BaseModel):
    query: str
    knowledge_base_id: str
    results: list[RetrievalChunk]


# --- Agent Runtime & MCP ---
class AgentRunRequest(BaseModel):
    prompt: str
    knowledge_base_id: str | None = None
    allow_high_risk_tools: bool = False


class AgentStepTrace(BaseModel):
    step: int
    stage: str  # planner, tool_call, observation, response
    content: str
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: dict[str, Any] | None = None
    latency_ms: float = 0.0


class AgentRunResponse(BaseModel):
    workload_id: str
    prompt: str
    final_response: str
    steps: list[AgentStepTrace]
    tools_used: list[str]
    total_tokens: int
    estimated_cost: float
    duration_ms: float


class ToolDeclaration(BaseModel):
    name: str
    description: str
    risk: str  # low, high
    required_permissions: list[str]


# --- Evaluation Engine ---
class ReleasePolicy(BaseModel):
    min_faithfulness: float = 0.85
    min_answer_correctness: float = 0.80
    max_p95_latency_ms: float = 2500.0
    max_cost_per_request: float = 0.05
    min_accuracy: float = 0.80
    max_rmse: float = 1.0


class EvaluationRunRequest(BaseModel):
    version: str
    policy: ReleasePolicy | None = None


class EvaluationRunResponse(BaseModel):
    id: str
    workload_id: str
    version: str
    status: str
    passed: bool
    decision: str  # ALLOW or BLOCK
    metrics: dict[str, Any]
    reasons: list[str]
    started_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Deployments ---
class DeploymentCreate(BaseModel):
    version: str
    environment: str = "staging"
    strategy: str = "blue_green"


class DeploymentResponse(BaseModel):
    id: str
    workload_id: str
    version: str
    environment: str
    strategy: str
    status: str
    traffic_percentage: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RollbackResponse(BaseModel):
    previous_deployment_id: str
    active_version: str
    status: str
    message: str


# --- Incidents & RCA ---
class IncidentResponse(BaseModel):
    id: str
    project_id: str
    severity: str
    title: str
    status: str
    root_cause: str
    recommendation: str
    confidence: float
    evidence: list[str]
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RemediateIncidentRequest(BaseModel):
    action: str = Field("rollback", description="rollback or restart")


# --- LLM Gateway & Costs ---
class GatewayChatRequest(BaseModel):
    prompt: str
    provider: str | None = "local"
    model: str | None = "llama-3-8b-instruct"
    max_tokens: int = 512
    temperature: float = 0.7


class GatewayChatResponse(BaseModel):
    id: str
    provider: str
    model: str
    response: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    estimated_cost: float
    status: str


class CostSummary(BaseModel):
    total_cost: float
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    breakdown_by_model: dict[str, float]
    breakdown_by_provider: dict[str, float]
    breakdown_by_workload: dict[str, float]


# --- Audit Logs ---
class AuditEventResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    action: str
    resource_type: str
    resource_id: str | None = None
    metadata: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
