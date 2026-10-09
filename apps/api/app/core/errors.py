"""Nuvorix Custom Exception Hierarchy.

Provides typed, domain-specific exceptions mapped to HTTP status codes and structured
problem responses across control plane services.
"""

from typing import Any


class NuvorixError(Exception):
    """Base exception for all Nuvorix platform errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class EntityNotFoundError(NuvorixError):
    """Raised when an entity is not found in the tenant's scope."""

    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(
            message=f"{entity_type} with ID '{entity_id}' not found or unauthorized.",
            error_code="NOT_FOUND",
            status_code=404,
            details={"entity_type": entity_type, "entity_id": entity_id},
        )


class AuthorizationError(NuvorixError):
    """Raised when an operation violates role or scope permissions."""

    def __init__(self, message: str, required_permission: str | None = None):
        details = {"required_permission": required_permission} if required_permission else {}
        super().__init__(
            message=message,
            error_code="FORBIDDEN",
            status_code=403,
            details=details,
        )


class AuthenticationRequiredError(NuvorixError):
    """Raised when valid credentials are required but missing or expired."""

    def __init__(self, message: str = "Authentication credentials required"):
        super().__init__(
            message=message,
            error_code="UNAUTHORIZED",
            status_code=401,
        )


class PolicyViolationError(NuvorixError):
    """Raised when an automated quality gate or invariant fails."""

    def __init__(self, message: str, reasons: list[str] | None = None):
        super().__init__(
            message=message,
            error_code="POLICY_VIOLATION",
            status_code=400,
            details={"reasons": reasons or []},
        )


class TenantContextError(NuvorixError):
    """Raised when mandatory organization or tenant context is missing."""

    def __init__(self, message: str = "Mandatory tenant organization context missing"):
        super().__init__(
            message=message,
            error_code="TENANT_CONTEXT_MISSING",
            status_code=400,
        )


class ProviderUnavailableError(NuvorixError):
    """Raised when an external LLM provider fails or is unconfigured in production."""

    def __init__(self, provider: str, reason: str):
        super().__init__(
            message=f"LLM Provider '{provider}' unavailable: {reason}",
            error_code="PROVIDER_UNAVAILABLE",
            status_code=502,
            details={"provider": provider, "reason": reason},
        )
