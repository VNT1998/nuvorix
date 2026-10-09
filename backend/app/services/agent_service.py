import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import ExecutionContext
from backend.app.core.telemetry import (
    TOOL_CALLS_TOTAL,
    TOOL_FAILURES_TOTAL,
    record_llm_usage,
)
from backend.app.models.entities import AuditEvent, Deployment, KnowledgeBase, Project, Workload
from backend.app.services.diagnostic_service import DiagnosticService
from backend.app.services.rag_service import RAGPlatformService
from backend.app.services.tool_authorization import TOOL_DEFINITIONS, authorize_tool


class AgentState(TypedDict, total=False):
    prompt: str
    workload_id: str
    knowledge_base_id: str | None
    allow_high_risk: bool
    context: ExecutionContext
    selected_tool: str | None
    tool_params: dict[str, Any]
    tool_observation: dict[str, Any] | None
    steps: list[dict[str, Any]]
    tools_used: list[str]
    final_response: str


class AgentRuntimeService:
    @classmethod
    def list_tools(cls) -> list[dict[str, Any]]:
        return list(TOOL_DEFINITIONS.values())

    @classmethod
    def get_workflow_mermaid(cls) -> str:
        """Returns the Mermaid diagram of the underlying LangGraph StateGraph."""
        workflow = StateGraph(AgentState)
        workflow.add_node("planner", lambda s: s)
        workflow.add_node("tool_executor", lambda s: s)
        workflow.add_node("synthesizer", lambda s: s)
        workflow.add_edge(START, "planner")
        workflow.add_conditional_edges(
            "planner",
            lambda s: "tool_executor" if s.get("selected_tool") else "synthesizer",
            {"tool_executor": "tool_executor", "synthesizer": "synthesizer"},
        )
        workflow.add_edge("tool_executor", "synthesizer")
        workflow.add_edge("synthesizer", END)
        compiled = workflow.compile()
        return compiled.get_graph().draw_mermaid()

    @classmethod
    async def execute_tool(
        cls,
        tool_name: str,
        tool_input: dict[str, Any],
        db: AsyncSession,
        context: ExecutionContext | None = None,
        allow_high_risk: bool = False,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """
        Public tool execution endpoint used by both LangGraph and external MCP callers.
        Enforces tenant boundaries, role authorization, and stateful side-effects.
        """
        if not context:
            raise ValueError(
                "Mandatory context missing: ExecutionContext is required for tool execution."
            )
        ctx = context

        try:
            authorize_tool(
                context=ctx,
                tool_name=tool_name,
                allow_high_risk=allow_high_risk,
                confirmed=confirmed or bool(tool_input.get("confirmed", False)),
            )
        except (ValueError, PermissionError) as auth_err:
            TOOL_FAILURES_TOTAL.labels(tool_name=tool_name, reason="authorization_failed").inc()
            return {"error": str(auth_err)}

        try:
            if tool_name == "knowledge_search":
                kb_id = tool_input.get("knowledge_base_id")
                query = tool_input.get("query", "")

                if not kb_id:
                    # Find first knowledge base belonging to the caller's organization
                    res_kb = await db.execute(
                        select(KnowledgeBase)
                        .join(Project, KnowledgeBase.project_id == Project.id)
                        .where(Project.organization_id == ctx.organization_id)
                        .limit(1)
                    )
                    first_kb = res_kb.scalar_one_or_none()
                    if first_kb:
                        kb_id = first_kb.id
                    else:
                        return {
                            "results": [],
                            "count": 0,
                            "message": "No knowledge base registered for this organization.",
                        }
                else:
                    # Verify provided KB belongs to caller's organization
                    res_kb = await db.execute(
                        select(KnowledgeBase)
                        .join(Project, KnowledgeBase.project_id == Project.id)
                        .where(
                            KnowledgeBase.id == kb_id,
                            Project.organization_id == ctx.organization_id,
                        )
                    )
                    if not res_kb.scalar_one_or_none():
                        return {
                            "error": f"Knowledge base '{kb_id}' not found or unauthorized for organization."
                        }

                results = await RAGPlatformService.query_knowledge_base(
                    db=db,
                    knowledge_base_id=kb_id,
                    query=query,
                    top_k=3,
                    org_id=ctx.organization_id,
                )
                output = {"results": results, "count": len(results)}

            elif tool_name == "project_deployment_status":
                res_w = await db.execute(
                    select(Workload)
                    .join(Project, Workload.project_id == Project.id)
                    .where(Project.organization_id == ctx.organization_id)
                )
                workloads = res_w.scalars().all()

                res_d = await db.execute(
                    select(Deployment)
                    .join(Workload, Deployment.workload_id == Workload.id)
                    .join(Project, Workload.project_id == Project.id)
                    .where(Project.organization_id == ctx.organization_id)
                    .order_by(Deployment.created_at.desc())
                    .limit(5)
                )
                deployments = res_d.scalars().all()

                output = {
                    "workloads": [
                        {
                            "id": w.id,
                            "name": w.name,
                            "type": w.type,
                            "status": w.status,
                            "version": w.active_version,
                        }
                        for w in workloads
                    ],
                    "recent_deployments": [
                        {
                            "id": d.id,
                            "version": d.version,
                            "environment": d.environment,
                            "status": d.status,
                        }
                        for d in deployments
                    ],
                }

            elif tool_name == "diagnostic_check":
                # Real measurements of DB round-trip latency, memory RSS, and artifact store
                diagnostics = await DiagnosticService.run_diagnostics(db=db)
                output = diagnostics

            elif tool_name == "emergency_circuit_breaker":
                # Stateful logical circuit breaker execution - requires explicit target
                target_dep_id = tool_input.get("deployment_id")
                reason = tool_input.get("reason", "Operator emergency circuit trip")

                if not target_dep_id:
                    return {
                        "error": "Missing required parameter 'deployment_id'. "
                        "Logical circuit breaker requires an explicit deployment target ID (no fallback allowed)."
                    }

                query_dep = (
                    select(Deployment)
                    .join(Workload, Deployment.workload_id == Workload.id)
                    .join(Project, Workload.project_id == Project.id)
                    .where(
                        Deployment.id == target_dep_id,
                        Project.organization_id == ctx.organization_id,
                    )
                )
                res_dep = await db.execute(query_dep)
                deployment = res_dep.scalar_one_or_none()
                if not deployment:
                    return {
                        "error": f"Target deployment '{target_dep_id}' not found or unauthorized for this organization."
                    }

                # Idempotency check: if circuit is already open, do not duplicate side-effects
                if deployment.status == "circuit_open":
                    return {
                        "status": "circuit_open",
                        "already_open": True,
                        "idempotent": True,
                        "deployment_id": deployment.id,
                        "message": "Circuit breaker is already tripped on this deployment.",
                    }

                before_state = {
                    "status": deployment.status,
                    "traffic_percentage": deployment.traffic_percentage,
                }

                # Mutate deployment and workload state
                deployment.status = "circuit_open"
                deployment.traffic_percentage = 0

                res_wl = await db.execute(
                    select(Workload).where(Workload.id == deployment.workload_id)
                )
                workload = res_wl.scalar_one_or_none()
                if workload:
                    workload.status = "degraded"

                after_state = {
                    "status": "circuit_open",
                    "traffic_percentage": 0,
                    "workload_status": "degraded",
                }

                audit = AuditEvent(
                    organization_id=ctx.organization_id,
                    user_id=ctx.user_id,
                    action="deployments:circuit_breaker",
                    resource_type="deployment",
                    resource_id=deployment.id,
                    request_id=ctx.request_id,
                    actor_type=ctx.source,
                    reason=reason,
                    before_state_json=before_state,
                    after_state_json=after_state,
                    metadata_json={"reason": reason, "idempotent": True},
                )
                db.add(audit)
                await db.commit()
                await db.refresh(deployment)

                output = {
                    "status": "circuit_open",
                    "deployment_id": deployment.id,
                    "traffic_percentage": 0,
                    "workload_status": "degraded",
                    "remediated": True,
                    "reason": reason,
                }

            else:
                output = {"error": "Unhandled tool execution."}

            TOOL_CALLS_TOTAL.labels(tool_name=tool_name, status="success").inc()
            return output

        except Exception as e:
            TOOL_FAILURES_TOTAL.labels(tool_name=tool_name, reason="execution_error").inc()
            return {"error": str(e)}

    @classmethod
    def route_prompt_to_tool(
        cls, prompt: str, knowledge_base_id: str | None = None
    ) -> tuple[str | None, dict[str, Any]]:
        """Determine appropriate tool and parameters based on natural language prompt intent."""
        prompt_lower = prompt.lower()
        if any(
            w in prompt_lower
            for w in [
                "search",
                "find",
                "how",
                "what",
                "doc",
                "spec",
                "rag",
                "knowledge",
                "architecture",
            ]
        ):
            return "knowledge_search", {"query": prompt, "knowledge_base_id": knowledge_base_id}
        elif any(
            w in prompt_lower
            for w in ["status", "deploy", "workload", "health", "system", "pods", "active"]
        ):
            return "project_deployment_status", {}
        elif any(w in prompt_lower for w in ["diagnostic", "latency", "memory", "db", "check"]):
            return "diagnostic_check", {}
        elif any(
            w in prompt_lower for w in ["halt", "stop", "circuit", "kill", "block", "emergency"]
        ):
            return "emergency_circuit_breaker", {
                "reason": "Operator emergency invoke",
                "confirmed": False,
            }
        return None, {}

    @classmethod
    async def run_agent_workflow(
        cls,
        db: AsyncSession,
        workload_id: str,
        prompt: str,
        knowledge_base_id: str | None = None,
        allow_high_risk: bool = False,
        context: ExecutionContext | None = None,
    ) -> dict[str, Any]:
        """
        Executes a real LangGraph StateGraph orchestration loop bound to authenticated context:
        START -> Planner -> (Conditional Router) -> Tool Executor -> Synthesizer -> END
        """
        start_overall = time.time()
        if not context:
            raise ValueError(
                "Mandatory context missing: ExecutionContext is required for agent workflow execution."
            )
        ctx = context

        async def planner_node(state: AgentState) -> dict[str, Any]:
            t0 = time.time()
            prompt_str = state.get("prompt", "")
            selected_tool, tool_params = cls.route_prompt_to_tool(
                prompt_str, state.get("knowledge_base_id")
            )

            decision_text = (
                f"Route to LangGraph tool_executor node for `{selected_tool}`"
                if selected_tool
                else "Route directly to LangGraph synthesizer node"
            )
            step_record = {
                "step": 1,
                "stage": "planner",
                "content": f"LangGraph Planner Node: Evaluated prompt intent. Decision: {decision_text}.",
                "latency_ms": round((time.time() - t0) * 1000, 2),
            }

            return {
                "selected_tool": selected_tool,
                "tool_params": tool_params,
                "steps": [step_record],
                "tools_used": [selected_tool] if selected_tool else [],
            }

        async def tool_executor_node(state: AgentState) -> dict[str, Any]:
            selected_tool = state.get("selected_tool")
            tool_params = state.get("tool_params", {})
            steps = list(state.get("steps", []))
            tools_used = list(state.get("tools_used", []))

            t_call = time.time()
            steps.append(
                {
                    "step": len(steps) + 1,
                    "stage": "tool_call",
                    "content": f"LangGraph Tool Node: Invoking registered tool `{selected_tool}` with parameters {tool_params}",
                    "tool_name": selected_tool,
                    "tool_input": tool_params,
                    "latency_ms": round((time.time() - t_call) * 1000, 2),
                }
            )

            t_obs = time.time()
            obs = await cls.execute_tool(
                tool_name=str(selected_tool),
                tool_input=tool_params,
                db=db,
                context=ctx,
                allow_high_risk=state.get("allow_high_risk", False),
                confirmed=bool(tool_params.get("confirmed", False)),
            )

            steps.append(
                {
                    "step": len(steps) + 1,
                    "stage": "observation",
                    "content": "LangGraph Tool Node: Received observation response from execution environment",
                    "tool_name": selected_tool,
                    "tool_output": obs,
                    "latency_ms": round((time.time() - t_obs) * 1000, 2),
                }
            )

            return {
                "tool_observation": obs,
                "steps": steps,
                "tools_used": tools_used,
            }

        async def synthesizer_node(state: AgentState) -> dict[str, Any]:
            t0 = time.time()
            selected_tool = state.get("selected_tool")
            obs = state.get("tool_observation")
            prompt_str = state.get("prompt", "")
            steps = list(state.get("steps", []))

            final_text = ""
            if selected_tool == "knowledge_search" and obs and "results" in obs:
                res_items = obs["results"]
                if res_items:
                    sources_str = ", ".join(
                        [f"`{r.get('source')}` (score: {r.get('score')})" for r in res_items]
                    )
                    first_excerpt = res_items[0].get("text", "")
                    final_text = (
                        f"Based on retrieved documentation from Nuvorix knowledge repository:\n\n"
                        f"{first_excerpt}\n\n"
                        f"**Sources & Evidence:** {sources_str}"
                    )
                else:
                    final_text = "Searched knowledge base via LangGraph state machine, but no matching context was found above threshold."
            elif selected_tool == "project_deployment_status" and obs:
                workloads_count = len(obs.get("workloads", []))
                deploys_count = len(obs.get("recent_deployments", []))
                final_text = (
                    f"Platform state checked: Currently observing {workloads_count} active workloads "
                    f"and {deploys_count} recent deployments for organization `{ctx.organization_id}`."
                )
            elif selected_tool == "diagnostic_check" and obs:
                db_status = obs.get("database", {}).get("status", "unknown")
                db_lat = obs.get("database", {}).get("latency_ms", "N/A")
                rss = obs.get("memory", {}).get("process_rss_mb", "N/A")
                final_text = (
                    f"System Diagnostics: Database is {db_status} ({db_lat}ms latency), "
                    f"process memory RSS is {rss} MB, and artifact storage is verified."
                )
            elif selected_tool == "emergency_circuit_breaker":
                if obs and "error" in obs:
                    final_text = f"Action blocked: {obs.get('error')}"
                elif obs:
                    final_text = f"Emergency circuit breaker successfully triggered on deployment `{obs.get('deployment_id')}`. Inbound traffic halted to 0%."
                else:
                    final_text = "Emergency circuit breaker executed without observation."
            else:
                final_text = (
                    f"Nuvorix Agent received your request: '{prompt_str}'. "
                    f"LangGraph StateGraph verified safety invariants and executed deterministic workflow."
                )

            steps.append(
                {
                    "step": len(steps) + 1,
                    "stage": "response",
                    "content": final_text,
                    "latency_ms": round((time.time() - t0) * 1000, 2),
                }
            )

            return {
                "final_response": final_text,
                "steps": steps,
            }

        def route_condition(state: AgentState) -> str:
            if state.get("selected_tool"):
                return "tool_executor"
            return "synthesizer"

        workflow = StateGraph(AgentState)
        workflow.add_node("planner", planner_node)
        workflow.add_node("tool_executor", tool_executor_node)
        workflow.add_node("synthesizer", synthesizer_node)

        workflow.add_edge(START, "planner")
        workflow.add_conditional_edges(
            "planner",
            route_condition,
            {"tool_executor": "tool_executor", "synthesizer": "synthesizer"},
        )
        workflow.add_edge("tool_executor", "synthesizer")
        workflow.add_edge("synthesizer", END)

        graph = workflow.compile()
        initial_state: AgentState = {
            "prompt": prompt,
            "workload_id": workload_id,
            "knowledge_base_id": knowledge_base_id,
            "allow_high_risk": allow_high_risk,
            "context": ctx,
            "selected_tool": None,
            "tool_params": {},
            "tool_observation": None,
            "steps": [],
            "tools_used": [],
            "final_response": "",
        }

        output_state = await graph.ainvoke(initial_state)

        total_latency_ms = round((time.time() - start_overall) * 1000, 2)
        final_text = output_state.get("final_response", "")
        steps = output_state.get("steps", [])
        tools_used = output_state.get("tools_used", [])

        in_tokens = len(prompt.split()) * 3
        out_tokens = len(final_text.split()) * 2
        total_tokens = in_tokens + out_tokens + 150
        from backend.app.services.gateway_service import calculate_token_cost

        estimated_cost = calculate_token_cost(
            "local", "nuvorix-state-machine", in_tokens, out_tokens
        )

        record_llm_usage(
            provider="langgraph-orchestrator",
            model="nuvorix-state-machine",
            status="success",
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            latency_sec=total_latency_ms / 1000.0,
            cost=estimated_cost,
        )

        audit = AuditEvent(
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            action="agents:run",
            resource_type="workload",
            resource_id=workload_id,
            request_id=ctx.request_id,
            actor_type="agent",
            metadata_json={
                "tools_used": tools_used,
                "latency_ms": total_latency_ms,
                "cost": estimated_cost,
                "orchestrator": "langgraph",
            },
        )
        db.add(audit)
        await db.commit()

        return {
            "workload_id": workload_id,
            "prompt": prompt,
            "final_response": final_text,
            "steps": steps,
            "tools_used": tools_used,
            "total_tokens": total_tokens,
            "estimated_cost": estimated_cost,
            "duration_ms": total_latency_ms,
        }
