"""Configuración de jobs-service desde variables de entorno."""

import os
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "si", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


@dataclass(frozen=True)
class JobsSettings:
    service_token: str = ""
    database_url: str = ""
    database_schema: str = "jobs"
    auth_service_url: str = "http://auth-service:3000"
    n8n_webhook_base_url: str = "http://n8n:5678/webhook"
    seed_demo: bool = True
    seed_path: str = field(default_factory=lambda: str(DATA_DIR / "jobs_seed.json"))
    http_timeout_seconds: int = 10
    event_timeout_seconds: int = 3
    jwks_url: str = "http://auth-service:3000/api/v1/auth/.well-known/jwks.json"
    jwt_issuer: str = "bolsa-auth"
    jwt_audience: str = "bolsa-api"

    @classmethod
    def from_env(cls) -> "JobsSettings":
        return cls(
            service_token=os.getenv("SERVICE_TOKEN", ""),
            database_url=os.getenv("DATABASE_URL", ""),
            database_schema=os.getenv("JOBS_DB_SCHEMA", "jobs"),
            auth_service_url=os.getenv("AUTH_SERVICE_URL", "http://auth-service:3000"),
            n8n_webhook_base_url=os.getenv("N8N_WEBHOOK_BASE_URL", "http://n8n:5678/webhook"),
            seed_demo=_bool_env("JOBS_SEED_DEMO", True),
            seed_path=os.getenv("JOBS_SEED_PATH", str(DATA_DIR / "jobs_seed.json")),
            http_timeout_seconds=_int_env("JOBS_HTTP_TIMEOUT", 10),
            event_timeout_seconds=_int_env("JOBS_EVENT_TIMEOUT", 3),
            jwks_url=os.getenv(
                "JWKS_URL", "http://auth-service:3000/api/v1/auth/.well-known/jwks.json"
            ),
            jwt_issuer=os.getenv("JWT_ISSUER") or "bolsa-auth",
            jwt_audience=os.getenv("JWT_AUDIENCE") or "bolsa-api",
        )
