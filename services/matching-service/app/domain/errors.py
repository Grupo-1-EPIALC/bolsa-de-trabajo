"""Errores de dominio de matching-service.

Cada error lleva `code`, `status_code` y `details` para que la capa API lo traduzca al
formato común `{"error": {"code", "message", "details"}}` (AGENTS.md §2.1.3).
"""

from typing import Any


class MatchingError(Exception):
    code = "MATCHING_ERROR"
    status_code = 500

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}


class InvalidInputError(MatchingError):
    code = "INVALID_INPUT"
    status_code = 422


class NotFoundError(MatchingError):
    code = "NOT_FOUND"
    status_code = 404


class UpstreamError(MatchingError):
    code = "UPSTREAM_ERROR"
    status_code = 502


class InvalidRulesError(MatchingError):
    code = "INVALID_RULES"
    status_code = 500


class UnauthorizedError(MatchingError):
    code = "UNAUTHORIZED"
    status_code = 401


class ForbiddenError(MatchingError):
    code = "FORBIDDEN"
    status_code = 403
