import datetime
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    users: Mapped[list["User"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="viewer")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    organization: Mapped["Organization"] = relationship(back_populates="users")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    organization: Mapped["Organization"] = relationship(back_populates="projects")
    workloads: Mapped[list["Workload"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    environments: Mapped[list["Environment"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    knowledge_bases: Mapped[list["KnowledgeBase"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Environment(Base):
    __tablename__ = "environments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(64), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)  # dev, staging, production
    type: Mapped[str] = mapped_column(String(64), nullable=False, default="staging")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="environments")


class Workload(Base):
    __tablename__ = "workloads"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(64), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)  # ml_model, rag, agent, llm_service
    status: Mapped[str] = mapped_column(String(64), default="healthy")  # healthy, degraded, deploying, error
    active_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="workloads")
    models: Mapped[list["Model"]] = relationship(back_populates="workload", cascade="all, delete-orphan")
    evaluations: Mapped[list["EvaluationRun"]] = relationship(back_populates="workload", cascade="all, delete-orphan")
    deployments: Mapped[list["Deployment"]] = relationship(back_populates="workload", cascade="all, delete-orphan")
    usage_logs: Mapped[list["LLMUsageLog"]] = relationship(back_populates="workload", cascade="all, delete-orphan")


class Model(Base):
    __tablename__ = "models"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    workload_id: Mapped[str] = mapped_column(String(64), ForeignKey("workloads.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    framework: Mapped[str] = mapped_column(String(64), default="scikit-learn")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    workload: Mapped["Workload"] = relationship(back_populates="models")
    versions: Mapped[list["ModelVersion"]] = relationship(back_populates="model", cascade="all, delete-orphan")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    model_id: Mapped[str] = mapped_column(String(64), ForeignKey("models.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. v1.0.0
    artifact_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    parameters_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(64), default="registered")  # registered, staging, production, archived
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    model: Mapped["Model"] = relationship(back_populates="versions")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(64), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(64), default="v1.0.0")
    uri: Mapped[str] = mapped_column(String(512), default="")
    schema_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="datasets")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    workload_id: Mapped[str] = mapped_column(String(64), ForeignKey("workloads.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="completed")  # running, completed, failed
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    passed: Mapped[bool] = mapped_column(Boolean, default=True)
    decision: Mapped[str] = mapped_column(String(32), default="ALLOW")  # ALLOW or BLOCK
    reasons_json: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workload: Mapped["Workload"] = relationship(back_populates="evaluations")


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    workload_id: Mapped[str] = mapped_column(String(64), ForeignKey("workloads.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    environment: Mapped[str] = mapped_column(String(64), default="staging")  # dev, staging, production
    strategy: Mapped[str] = mapped_column(String(64), default="blue_green")  # direct, blue_green, canary
    status: Mapped[str] = mapped_column(String(64), default="active")  # candidate, active, rolled_back, failed
    traffic_percentage: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    workload: Mapped["Workload"] = relationship(back_populates="deployments")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(64), ForeignKey("projects.id"), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="HIGH")  # LOW, MEDIUM, HIGH, CRITICAL
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="open")  # open, investigating, remediated, resolved
    root_cause: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.90)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="incidents")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(64), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    embedding_model: Mapped[str] = mapped_column(String(128), default="text-embedding-3-small")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="knowledge_bases")
    documents: Mapped[list["KnowledgeDocument"]] = relationship(back_populates="knowledge_base", cascade="all, delete-orphan")
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="knowledge_base", cascade="all, delete-orphan")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    knowledge_base_id: Mapped[str] = mapped_column(String(64), ForeignKey("knowledge_bases.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_uri: Mapped[str] = mapped_column(String(512), default="")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(64), default="indexed")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="documents")
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(64), ForeignKey("knowledge_documents.id"), nullable=False)
    knowledge_base_id: Mapped[str] = mapped_column(String(64), ForeignKey("knowledge_bases.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[list] = mapped_column(JSON, default=list)  # normalized vector coordinates
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    document: Mapped["KnowledgeDocument"] = relationship(back_populates="chunks")
    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="chunks")


class LLMUsageLog(Base):
    __tablename__ = "llm_usage_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    workload_id: Mapped[str] = mapped_column(String(64), ForeignKey("workloads.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)  # openai, anthropic, gemini, local
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, default="")
    completion: Mapped[str] = mapped_column(Text, default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="success")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    workload: Mapped["Workload"] = relationship(back_populates="usage_logs")
