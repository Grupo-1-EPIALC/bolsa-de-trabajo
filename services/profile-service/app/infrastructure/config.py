"""Configuración desde variables de entorno para profile-service."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileSettings:
    cv_storage_path: str = "/data/cvs"
    cv_max_size_mb: int = 5
    n8n_webhook_base_url: str = "http://n8n:5678/webhook"
    service_token: str = ""

    @classmethod
    def from_env(cls) -> "ProfileSettings":
        return cls(
            cv_storage_path=os.getenv("CV_STORAGE_PATH", "/data/cvs"),
            cv_max_size_mb=int(os.getenv("CV_MAX_SIZE_MB", "5")),
            n8n_webhook_base_url=os.getenv("N8N_WEBHOOK_BASE_URL", "http://n8n:5678/webhook"),
            service_token=os.getenv("SERVICE_TOKEN", ""),
        )
