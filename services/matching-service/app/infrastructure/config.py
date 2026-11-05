"""Configuración de matching-service desde variables de entorno."""

import os
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "si", "on"}


@dataclass(frozen=True)
class MatchingSettings:
    service_token: str = ""
    profile_service_url: str = "http://profile-service:8000"
    jobs_service_url: str = "http://jobs-service:8000"
    n8n_webhook_base_url: str = "http://n8n:5678/webhook"
    use_mocks: bool = True
    rules_path: str = str(DATA_DIR / "scoring_rules.yaml")
    synonyms_path: str = str(DATA_DIR / "skill_synonyms.json")
    http_timeout_seconds: int = 15
    webhook_timeout_seconds: int = 300
    max_items_per_entry: int = 5
    # JWT de usuarios (auth-service, RS256). Mismos valores que JWT_ISSUER / JWT_AUDIENCE del .env
    jwks_url: str = "http://auth-service:3000/api/v1/auth/.well-known/jwks.json"
    jwt_issuer: str = "bolsa-auth"
    jwt_audience: str = "bolsa-api"

    @classmethod
    def from_env(cls) -> "MatchingSettings":
        return cls(
            service_token=os.getenv("SERVICE_TOKEN", ""),
            profile_service_url=os.getenv("PROFILE_SERVICE_URL", "http://profile-service:8000"),
            jobs_service_url=os.getenv("JOBS_SERVICE_URL", "http://jobs-service:8000"),
            n8n_webhook_base_url=os.getenv("N8N_WEBHOOK_BASE_URL", "http://n8n:5678/webhook"),
            # Mientras profile-service y jobs-service no exponen GET de perfiles/ofertas.
            use_mocks=_bool_env("MATCHING_USE_MOCKS", True),
            rules_path=os.getenv("MATCHING_RULES_PATH", str(DATA_DIR / "scoring_rules.yaml")),
            synonyms_path=os.getenv(
                "MATCHING_SYNONYMS_PATH", str(DATA_DIR / "skill_synonyms.json")
            ),
            http_timeout_seconds=int(os.getenv("MATCHING_HTTP_TIMEOUT", "15")),
            webhook_timeout_seconds=int(os.getenv("MATCHING_WEBHOOK_TIMEOUT", "300")),
            max_items_per_entry=int(os.getenv("MATCHING_MAX_ITEMS_PER_ENTRY", "5")),
            jwks_url=os.getenv(
                "JWKS_URL", "http://auth-service:3000/api/v1/auth/.well-known/jwks.json"
            ),
            jwt_issuer=os.getenv("JWT_ISSUER") or "bolsa-auth",
            jwt_audience=os.getenv("JWT_AUDIENCE") or "bolsa-api",
        )
