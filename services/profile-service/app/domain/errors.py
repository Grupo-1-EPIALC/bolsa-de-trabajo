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
