"""Configuración desde variables de entorno para profile-service."""

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
    return int(raw) if raw and raw.strip() else default


@dataclass(frozen=True)
class ProfileSettings:
    cv_storage_path: str = "/data/cvs"
    cv_max_size_mb: int = 5
    n8n_webhook_base_url: str = "http://n8n:5678/webhook"
    service_token: str = ""
    database_url: str = ""
    database_schema: str = "profile"
    auth_service_url: str = "http://auth-service:3000"
    logo_max_kb: int = 1024
    jwks_url: str = "http://auth-service:3000/api/v1/auth/.well-known/jwks.json"
    jwt_issuer: str = "bolsa-auth"
    jwt_audience: str = "bolsa-api"
    seed_demo: bool = True
    seed_path: str = field(default_factory=lambda: str(DATA_DIR / "profiles_seed.json"))
    companies_seed_path: str = field(default_factory=lambda: str(DATA_DIR / "companies_seed.json"))
    skills_catalog_path: str = field(default_factory=lambda: str(DATA_DIR / "skills_catalog.json"))
    http_timeout_seconds: int = 5
    event_timeout_seconds: int = 3
    cv_webhook_timeout_seconds: int = 300

    @classmethod
    def from_env(cls) -> "ProfileSettings":
        return cls(
            cv_storage_path=os.getenv("CV_STORAGE_PATH", "/data/cvs"),
            cv_max_size_mb=_int_env("CV_MAX_SIZE_MB", 5),
            n8n_webhook_base_url=os.getenv("N8N_WEBHOOK_BASE_URL", "http://n8n:5678/webhook"),
            service_token=os.getenv("SERVICE_TOKEN", ""),
            database_url=os.getenv("DATABASE_URL", ""),
            database_schema=os.getenv("PROFILE_DB_SCHEMA", "profile"),
            auth_service_url=os.getenv("AUTH_SERVICE_URL", "http://auth-service:3000"),
            logo_max_kb=_int_env("LOGO_MAX_SIZE_KB", 1024),
            jwks_url=os.getenv(
                "JWKS_URL", "http://auth-service:3000/api/v1/auth/.well-known/jwks.json"
            ),
            jwt_issuer=os.getenv("JWT_ISSUER") or "bolsa-auth",
            jwt_audience=os.getenv("JWT_AUDIENCE") or "bolsa-api",
            seed_demo=_bool_env("PROFILE_SEED_DEMO", True),
            seed_path=os.getenv("PROFILE_SEED_PATH", str(DATA_DIR / "profiles_seed.json")),
            companies_seed_path=os.getenv(
                "COMPANY_SEED_PATH", str(DATA_DIR / "companies_seed.json")
            ),
            skills_catalog_path=os.getenv(
                "SKILLS_CATALOG_PATH", str(DATA_DIR / "skills_catalog.json")
            ),
            http_timeout_seconds=_int_env("PROFILE_HTTP_TIMEOUT", 5),
            event_timeout_seconds=_int_env("PROFILE_EVENT_TIMEOUT", 3),
            cv_webhook_timeout_seconds=_int_env("CV_WEBHOOK_TIMEOUT", 300),
        )
