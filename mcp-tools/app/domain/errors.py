"""Errores de dominio. Las herramientas MCP los traducen a mensajes legibles para el LLM."""


class DomainError(Exception):
    """Error esperado con código estable y mensaje en español."""

    code = "domain_error"

    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidInputError(DomainError):
    code = "invalid_input"


class UnsupportedFormatError(DomainError):
    code = "unsupported_format"


class NotFoundError(DomainError):
    code = "not_found"


class UpstreamError(DomainError):
    """Otro servicio no respondió o respondió con error."""

    code = "upstream_error"


class SchemaNotFoundError(DomainError):
    code = "schema_not_found"
