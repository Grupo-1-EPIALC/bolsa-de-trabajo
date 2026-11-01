"""Puertos (Protocols) de profile-service (DIP · AGENTS.md §2.1 y §4.2)."""

from typing import Protocol

from app.domain.models import CvExtractionResult, UploadedCvFile


class CvStoragePort(Protocol):
    """Puerto para almacenar el archivo de CV con nombre aleatorio en CV_STORAGE_PATH."""

    def save(self, extension: str, content: bytes) -> str:
        """Guarda los bytes del CV con nombre aleatorio y devuelve el nombre almacenado."""


class CvWebhookGateway(Protocol):
    """Puerto para enviar el CV al webhook de n8n (`POST /webhook/cv-extract`)."""

    def extract_cv_suggestions(
        self,
        profile_id: str,
        cv_file: UploadedCvFile,
    ) -> CvExtractionResult:
        """Envía el CV al webhook de n8n y devuelve sugerencias estructuradas (`origin='AI'`)."""
