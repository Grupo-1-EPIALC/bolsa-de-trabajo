"""Errores de dominio de jobs-service.

Cada error lleva `code`, `status_code` y `details` para que la capa API lo traduzca al
formato común `{"error": {"code", "message", "details"}}` (AGENTS.md §2.1.3).
"""

from typing import Any


class JobsError(Exception):
    code = "JOBS_ERROR"
    status_code = 500

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}


class InvalidInputError(JobsError):
    code = "INVALID_INPUT"
    status_code = 422


class NotFoundError(JobsError):
    code = "NOT_FOUND"
    status_code = 404


class AccountDeletedError(JobsError):
    """La cuenta fue dada de baja en auth-service; su access token todavía no venció."""

    code = "ACCOUNT_DELETED"
    status_code = 401

    def __init__(self) -> None:
        super().__init__("La cuenta fue dada de baja")


class ForbiddenError(JobsError):
    code = "FORBIDDEN"
    status_code = 403


class ConflictError(JobsError):
    """Otra escritura ganó la carrera de versiones (lock optimista)."""

    code = "CONFLICT"
    status_code = 409


class UnauthorizedError(JobsError):
    code = "UNAUTHORIZED"
    status_code = 401


class UpstreamError(JobsError):
    code = "UPSTREAM_ERROR"
    status_code = 502


class ProfileRequiredError(JobsError):
    """El estudiante todavía no tiene un perfil con nombre y email para compartir."""

    code = "PROFILE_REQUIRED"
    status_code = 409
