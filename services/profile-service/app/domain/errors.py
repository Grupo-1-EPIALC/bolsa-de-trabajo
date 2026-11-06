"""Excepciones de dominio de profile-service."""

from typing import Any


class ProfileDomainError(Exception):
    """Error base del dominio de perfiles."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class InvalidCvFileError(ProfileDomainError):
    """El archivo de CV no cumple formato, MIME o tamaño máximo."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="INVALID_CV_FILE",
            message=message,
            status_code=422,
            details=details,
        )


class WebhookExtractionError(ProfileDomainError):
    """Error al invocar el webhook de extracción de CV en n8n."""

    def __init__(
        self,
        message: str,
        status_code: int = 503,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="CV_WEBHOOK_ERROR",
            message=message,
            status_code=status_code,
            details=details,
        )


class CvJobNotFoundError(ProfileDomainError):
    """No existe la tarea asíncrona de extracción de CV solicitada."""

    def __init__(self, job_id: str) -> None:
        super().__init__(
            code="CV_JOB_NOT_FOUND",
            message=f"No se encontró el trabajo de extracción '{job_id}'.",
            status_code=404,
            details={"job_id": job_id},
        )


class InvalidInputError(ProfileDomainError):
    """Datos de entrada inválidos (enums, rangos, `COMPLETAR_MANUALMENTE` sin reemplazar)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("INVALID_INPUT", message, status_code=422, details=details)


class UnauthorizedError(ProfileDomainError):
    def __init__(self, message: str = "No autenticado", details: dict[str, Any] | None = None):
        super().__init__("UNAUTHORIZED", message, status_code=401, details=details)


class ForbiddenError(ProfileDomainError):
    def __init__(self, message: str = "No tenés permiso", details: dict[str, Any] | None = None):
        super().__init__("FORBIDDEN", message, status_code=403, details=details)


class ProfileNotFoundError(ProfileDomainError):
    """No existe el perfil (o no es visible para quien lo pide: mismo 404)."""

    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            "PROFILE_NOT_FOUND", "No se encontró el perfil", status_code=404, details=details
        )


class ProfileAlreadyExistsError(ProfileDomainError):
    def __init__(self, profile_id: str) -> None:
        super().__init__(
            "PROFILE_ALREADY_EXISTS",
            "El usuario ya tiene un perfil",
            status_code=409,
            details={"profile_id": profile_id},
        )


class ProfileIncompleteError(ProfileDomainError):
    """Faltan datos obligatorios para la operación (p. ej. generar el CV)."""

    def __init__(self, message: str, missing: list[dict[str, Any]]) -> None:
        super().__init__(
            "PROFILE_INCOMPLETE", message, status_code=409, details={"missing": missing}
        )


class SuggestionsNotFoundError(ProfileDomainError):
    def __init__(self) -> None:
        super().__init__(
            "CV_SUGGESTIONS_NOT_FOUND",
            "No hay sugerencias de CV pendientes",
            status_code=404,
        )


class UnsupportedFormatError(ProfileDomainError):
    def __init__(self, fmt: str, allowed: list[str]) -> None:
        super().__init__(
            "UNSUPPORTED_FORMAT",
            f"Formato '{fmt}' no soportado",
            status_code=422,
            details={"format": fmt, "allowed": allowed},
        )


class CompanyProfileNotFoundError(ProfileDomainError):
    """La empresa no tiene perfil (o está oculto para quien lo pide: mismo 404)."""

    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            "COMPANY_PROFILE_NOT_FOUND",
            "No se encontró el perfil de la empresa",
            status_code=404,
            details=details,
        )


class CompanyProfileAlreadyExistsError(ProfileDomainError):
    def __init__(self, company_id: str) -> None:
        super().__init__(
            "COMPANY_PROFILE_ALREADY_EXISTS",
            "La empresa ya tiene un perfil",
            status_code=409,
            details={"company_id": company_id},
        )


class InvalidLogoError(ProfileDomainError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("INVALID_LOGO", message, status_code=422, details=details)


class LogoNotFoundError(ProfileDomainError):
    def __init__(self) -> None:
        super().__init__("LOGO_NOT_FOUND", "La empresa no tiene logo", status_code=404)
