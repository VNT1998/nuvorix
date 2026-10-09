# ADR 0002: LangGraph State Machine for Multi-Tenant Tool Orchestration

## Status
Accepted

## Context
Autonomous agents require structured planning, tool execution, and response synthesis. Linear chaining or unconstrained ReAct loops risk non-terminating loops, unauthenticated tool execution, and side-effects across organizational boundaries.

## Decision
1. Implement a stateful `StateGraph` compiled state machine with three explicit nodes:
   - `planner`: Analyzes intent and determines target tool or directs to synthesizer.
   - `tool_executor`: Executes authorized tools with strict permission checks and side-effect logging.
   - `synthesizer`: Produces grounded, evidence-attributed responses with source citations.
2. Require an explicit `ExecutionContext` bound to the caller's organization ID and permissions for all tool executions.
3. Require high-risk destructive actions (e.g., `emergency_circuit_breaker`) to specify an explicit target ID, provide operator reason logging, and set `confirmed=True`. Intent-matching prompt routers cannot fabricate confirmation.

## Consequences
- **Positive**: Verifiable, deterministic orchestration; fine-grained MCP tool authorization; clear audit trail for compliance.
- **Negative**: Adds state machine overhead compared to simple direct prompt completion.
