import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.entities import (
    AuditEvent,
    Deployment,
    Environment,
    EvaluationRun,
    Incident,
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
    LLMUsageLog,
    Model,
    ModelVersion,
    Organization,
    Project,
    User,
    Workload,
)
from apps.api.app.services.rag_service import RAGPlatformService


async def seed_demo_data(db: AsyncSession) -> None:
    # Check if organization exists
    res = await db.execute(select(Organization).limit(1))
    if res.scalar_one_or_none():
        return  # already seeded

    now = datetime.datetime.now(datetime.UTC)

    # 1. Organization
    org = Organization(
        id="org-demo-nuvorix",
        name="Nuvorix AI Platform Engineering",
        created_at=now,
    )
    db.add(org)

    # 2. Users
    admin_user = User(
        id="usr-demo-admin",
        organization_id=org.id,
        email="admin@nuvorix.local",
        name="Platform Administrator",
        role="admin",
        created_at=now,
    )
    ml_user = User(
        id="usr-demo-ml",
        organization_id=org.id,
        email="mle@nuvorix.local",
        name="Lead ML Engineer",
        role="ml_engineer",
        created_at=now,
    )
    db.add(admin_user)
    db.add(ml_user)

    # 3. Project
    project = Project(
        id="proj-customer-intelligence",
        organization_id=org.id,
        name="Enterprise Customer Intelligence",
        description="Unified AI intelligence platform providing knowledge retrieval, agentic customer ops, and predictive churn modeling.",
        created_at=now,
    )
    db.add(project)

    # 4. Environments
    envs = [
        Environment(id="env-dev", project_id=project.id, name="dev", type="dev", created_at=now),
        Environment(id="env-staging", project_id=project.id, name="staging", type="staging", created_at=now),
        Environment(id="env-prod", project_id=project.id, name="production", type="production", created_at=now),
    ]
    for env in envs:
        db.add(env)

    # 5. Workloads
    w_agent = Workload(
        id="w-support-agent",
        project_id=project.id,
        name="Support Orchestrator Agent",
        type="agent",
        status="healthy",
        active_version="v1.2.0",
        created_at=now,
    )
    w_rag = Workload(
        id="w-kb-rag",
        project_id=project.id,
        name="Platform Knowledge RAG",
        type="rag",
        status="healthy",
        active_version="v2.0.0",
        created_at=now,
    )
    w_ml = Workload(
        id="w-churn-predictor",
        project_id=project.id,
        name="Customer Churn Regressor",
        type="ml_model",
        status="healthy",
        active_version="v1.0.0",
        created_at=now,
    )
    db.add(w_agent)
    db.add(w_rag)
    db.add(w_ml)
    await db.flush()

    # 6. ML Model & Versions
    model_entity = Model(
        id="model-churn-ridge",
        workload_id=w_ml.id,
        name="churn_ridge_regressor",
        framework="scikit-learn",
        created_at=now,
    )
    db.add(model_entity)
    await db.flush()

    m_v1 = ModelVersion(
        id="ver-churn-v1",
        model_id=model_entity.id,
        version="v1.0.0",
        artifact_uri="./artifacts/w-churn-predictor/models/churn_ridge_regressor_v1.0.0.joblib",
        metrics_json={"rmse": 0.412, "mae": 0.305, "r2_score": 0.941, "accuracy": 0.932},
        parameters_json={"alpha": 1.0, "max_iter": 1000, "algorithm": "Ridge"},
        status="production",
        created_at=now,
    )
    db.add(m_v1)

    # 7. Knowledge Base & Documents
    kb = KnowledgeBase(
        id="kb-nuvorix-core",
        project_id=project.id,
        name="Nuvorix Architecture & Runbooks",
        description="Comprehensive platform specifications, release policies, SRE runbooks, and API documentation.",
        embedding_model="text-embedding-3-small",
        created_at=now,
    )
    db.add(kb)
    await db.flush()

    doc1_content = """# Nuvorix Architecture & Platform Invariants
Nuvorix provides reusable platform primitives so ML and GenAI engineers can move from experimentation to production without rebuilding experiments, evaluations, release gates, retrieval systems, agent runtimes, or observability pipelines for every project.
The control plane enforces automated release gates before any workload version can be promoted to staging or production.
All LLM and tool calls are captured with high-fidelity latency, token usage, and cost attribution."""

    doc2_content = """# SRE Incident Remediation Runbook
When a candidate deployment demonstrates a degradation in retrieval latency or an increase in error rates, the Incident RCA Agent correlates the telemetry anomaly with recent rollout events.
The platform operator can review the hypothesis and evidence, then execute an automated rollback.
The rollback shifts 100% of traffic back to the previous stable active deployment within milliseconds."""

    doc1 = KnowledgeDocument(
        id="doc-arch-spec",
        knowledge_base_id=kb.id,
        title="Nuvorix Architecture & Platform Invariants",
        source_uri="docs/architecture/overview.md",
        chunk_count=2,
        status="indexed",
        created_at=now,
    )
    doc2 = KnowledgeDocument(
        id="doc-sre-runbook",
        knowledge_base_id=kb.id,
        title="SRE Incident Remediation Runbook",
        source_uri="docs/runbooks/rollback.md",
        chunk_count=2,
        status="indexed",
        created_at=now,
    )
    db.add(doc1)
    db.add(doc2)
    await db.flush()

    # Index chunks
    chunks_data = [
        (doc1.id, 0, doc1_content),
        (doc2.id, 0, doc2_content),
    ]
    for doc_id, c_idx, text in chunks_data:
        emb = RAGPlatformService.generate_embedding(text)
        chunk = KnowledgeChunk(
            document_id=doc_id,
            knowledge_base_id=kb.id,
            chunk_index=c_idx,
            content=text,
            embedding_json=emb,
            metadata_json={"doc_id": doc_id, "title": "Documentation"},
            created_at=now,
        )
        db.add(chunk)

    # 8. Evaluation Runs
    eval1 = EvaluationRun(
        id="eval-agent-v120",
        workload_id=w_agent.id,
        version="v1.2.0",
        status="completed",
        metrics_json={"faithfulness": 0.961, "answer_correctness": 0.934, "tool_selection_accuracy": 0.991, "p95_latency_ms": 1320.0, "cost_per_request": 0.006},
        passed=True,
        decision="ALLOW",
        reasons_json=[],
        started_at=now - datetime.timedelta(hours=2),
        completed_at=now - datetime.timedelta(hours=2, minutes=-1),
    )
    eval2 = EvaluationRun(
        id="eval-agent-v130-canary-fail",
        workload_id=w_agent.id,
        version="v1.3.0-bad-candidate",
        status="completed",
        metrics_json={"faithfulness": 0.682, "answer_correctness": 0.710, "tool_selection_accuracy": 0.740, "p95_latency_ms": 3100.0, "cost_per_request": 0.024},
        passed=False,
        decision="BLOCK",
        reasons_json=[
            "RAG faithfulness (68.2%) is below required threshold (85.0%)",
            "p95 latency (3100.0ms) exceeded maximum threshold (2500.0ms)",
            "Cost per request ($0.0240) exceeded budget ceiling ($0.0100)",
        ],
        started_at=now - datetime.timedelta(minutes=30),
        completed_at=now - datetime.timedelta(minutes=29),
    )
    db.add(eval1)
    db.add(eval2)

    # 9. Deployments
    dep1 = Deployment(
        id="dep-agent-v120-prod",
        workload_id=w_agent.id,
        version="v1.2.0",
        environment="production",
        strategy="blue_green",
        status="active",
        traffic_percentage=100,
        created_at=now - datetime.timedelta(hours=1),
    )
    dep2 = Deployment(
        id="dep-agent-v110-prev",
        workload_id=w_agent.id,
        version="v1.1.0",
        environment="production",
        strategy="blue_green",
        status="retired",
        traffic_percentage=0,
        created_at=now - datetime.timedelta(days=1),
    )
    db.add(dep1)
    db.add(dep2)

    # 10. Incidents
    incident = Incident(
        id="inc-142",
        project_id=project.id,
        severity="HIGH",
        title="Retrieval Latency Regression in Support Agent",
        status="open",
        root_cause="Candidate deployment v1.3.0 introduced unindexed vector parameter causing 312% increase in retrieval span latency.",
        recommendation="Execute automated Blue/Green rollback to active release v1.2.0.",
        confidence=0.92,
        evidence_json=[
            "Retrieval span latency spiked from 380ms to 2410ms post-release",
            "Downstream error rate remained stable at 0.12%",
            "Pod CPU utilization normal at 34%",
            "New embedding configuration introduced in candidate version",
        ],
        created_at=now - datetime.timedelta(minutes=15),
    )
    db.add(incident)

    # 11. LLM Usage Logs (FinOps)
    usage_logs = [
        LLMUsageLog(
            workload_id=w_agent.id,
            provider="openai",
            model="gpt-4o",
            prompt="How to resolve database connection timeout in Nuvorix?",
            completion="Check connection pool exhaustion settings in config.py...",
            input_tokens=140,
            output_tokens=320,
            latency_ms=780.0,
            estimated_cost=0.00355,
            status="success",
            created_at=now - datetime.timedelta(minutes=10),
        ),
        LLMUsageLog(
            workload_id=w_rag.id,
            provider="local",
            model="llama-3-8b-instruct",
            prompt="Summarize SRE incident rollback workflow",
            completion="The SRE rollback shifts traffic back to the previous deployment...",
            input_tokens=220,
            output_tokens=180,
            latency_ms=310.0,
            estimated_cost=0.000058,
            status="success",
            created_at=now - datetime.timedelta(minutes=5),
        ),
    ]
    for u in usage_logs:
        db.add(u)

    # 12. Audit Events
    audit = AuditEvent(
        organization_id=org.id,
        user_id=admin_user.id,
        action="platform:bootstrap",
        resource_type="system",
        resource_id="nuvorix-core",
        metadata_json={"seed": "initial_demo_dataset"},
        created_at=now,
    )
    db.add(audit)

    await db.commit()
