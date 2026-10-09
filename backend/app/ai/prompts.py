"""Nuvorix Versioned Prompt Templates Catalog.

Centralized prompt assets ensuring reproducible, audited prompts across LLM gateway,
evaluation benchmark harnesses, and agent workflows.
"""

from typing import Any

from pydantic import BaseModel


class PromptTemplate(BaseModel):
    name: str
    version: str
    description: str
    template: str
    input_variables: list[str]
    metadata: dict[str, Any] = {}

    def format(self, **kwargs: Any) -> str:
        return self.template.format(**kwargs)


# 1. Platform Invariants System Prompt
PLATFORM_INVARIANTS_PROMPT = PromptTemplate(
    name="platform_invariants",
    version="1.0.0",
    description="Grounding system prompt outlining architectural invariants and deployment safety gates.",
    template=(
        "Nuvorix Platform Architecture Invariants:\n"
        "1. All workloads require quality gate validation (ALLOW/BLOCK) prior to promotion.\n"
        "2. Distributed traces are captured across all control plane operations.\n"
        "3. Invariant breaches immediately trigger automated rollback to the last verified active deployment.\n"
        "Context: {context}"
    ),
    input_variables=["context"],
)

# 2. Agent Orchestration Planner Prompt
AGENT_PLANNER_PROMPT = PromptTemplate(
    name="agent_planner",
    version="1.1.0",
    description="Planner prompt instructing the LangGraph supervisor on tool selection and parameter extraction.",
    template=(
        "You are the Nuvorix Agent Supervisor. Analyze the user request and determine the single best tool "
        "to invoke among the registered MCP tools, or synthesize a direct answer.\n"
        "User Request: {prompt}\n"
        "Available Tools: {tools}\n"
        "Organization: {org_id}"
    ),
    input_variables=["prompt", "tools", "org_id"],
)

# 3. Diagnostic Reasoning Prompt
DIAGNOSTIC_REASONING_PROMPT = PromptTemplate(
    name="diagnostic_reasoning",
    version="1.0.0",
    description="Synthesizes system diagnostic metrics (latency, memory, pool health) into an operator summary.",
    template=(
        "System Diagnostics:\n"
        "- Database Status: {db_status} (Latency: {db_latency_ms}ms)\n"
        "- Process RSS Memory: {rss_mb} MB\n"
        "- Artifact Storage Status: {artifact_status}\n"
        "Generate a concise operational health assessment."
    ),
    input_variables=["db_status", "db_latency_ms", "rss_mb", "artifact_status"],
)

# 4. Release Evaluation Benchmark Cases
BENCHMARK_PROMPTS = [
    {
        "id": "bench-01",
        "category": "architecture",
        "prompt": "What platform invariants does Nuvorix enforce before deployment?",
    },
    {
        "id": "bench-02",
        "category": "sre",
        "prompt": "How does the SRE runbook handle incident rollback?",
    },
    {
        "id": "bench-03",
        "category": "finops",
        "prompt": "What telemetry and cost metrics are tracked by the control plane?",
    },
]
