from typing import Any

from backend.app.core.security import ExecutionContext

TOOL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "knowledge_search": {
        "name": "knowledge_search",
        "description": "Search platform knowledge base for runbooks, architectural specifications, and invariants.",
        "risk": "low",
        "required_permissions": ["knowledge:query"],
        "side_effect": False,
        "allowed_states": [],
        "requires_explicit_confirmation": False,
        "idempotent": True,
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query keywords"},
                "knowledge_base_id": {"type": "string", "description": "Optional target KB ID"},
            },
            "required": ["query"],
        },
    },
    "project_deployment_status": {
        "name": "project_deployment_status",
        "description": "Inspect deployment health and active versions for project workloads within caller's organization.",
        "risk": "low",
        "required_permissions": ["workloads:read"],
        "side_effect": False,
        "allowed_states": [],
        "requires_explicit_confirmation": False,
        "idempotent": True,
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    "diagnostic_check": {
        "name": "diagnostic_check",
        "description": "Run real-time diagnostics on control plane database latency, memory RSS, and artifact store.",
        "risk": "low",
        "required_permissions": ["workloads:read"],
        "side_effect": False,
        "allowed_states": [],
        "requires_explicit_confirmation": False,
        "idempotent": True,
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    "emergency_circuit_breaker": {
        "name": "emergency_circuit_breaker",
        "description": "Logical deployment-state circuit breaker: cuts traffic to 0% and sets deployment status to circuit_open.",
        "risk": "high",
        "required_permissions": ["deployments:rollback"],
        "side_effect": True,
        "allowed_states": ["active", "candidate"],
        "requires_explicit_confirmation": True,
        "idempotent": True,
        "inputSchema": {
            "type": "object",
            "properties": {
                "deployment_id": {
                    "type": "string",
                    "description": "Target deployment ID to trip circuit on",
                },
                "reason": {
                    "type": "string",
                    "description": "Operational reason for tripping breaker",
                },
            },
            "required": ["deployment_id"],
        },
    },
}


def authorize_tool(
    context: ExecutionContext,
    tool_name: str,
    allow_high_risk: bool = False,
    confirmed: bool = False,
) -> dict[str, Any]:
    """
    Validate caller authorization at the service and tool boundary.
    Enforces tool existence, required permissions, high-risk flags, and explicit confirmation.
    """
    if tool_name not in TOOL_DEFINITIONS:
        raise ValueError(f"Tool '{tool_name}' is not recognized or registered in the platform.")

    tool_def = TOOL_DEFINITIONS[tool_name]
    required_perms = set(tool_def.get("required_permissions", []))

    # Check that caller has all required permissions
    missing_perms = required_perms - context.permissions
    if missing_perms:
        raise PermissionError(
            f"Principal '{context.user_id}' with role '{context.role}' lacks required permissions "
            f"for tool '{tool_name}': {sorted(missing_perms)}"
        )

    # Check high-risk constraints
    if tool_def.get("risk") == "high":
        if "agents:tools:execute_high_risk" not in context.permissions:
            raise PermissionError(
                f"Principal '{context.user_id}' lacks 'agents:tools:execute_high_risk' permission "
                f"required for high-risk tool '{tool_name}'."
            )
        if not allow_high_risk:
            raise PermissionError(
                f"Execution of high-risk tool '{tool_name}' blocked: allow_high_risk flag was not set."
            )
        if tool_def.get("requires_explicit_confirmation") and not confirmed:
            raise PermissionError(
                f"High-risk destructive tool '{tool_name}' requires explicit confirmation (confirmed=True)."
            )

    return tool_def
