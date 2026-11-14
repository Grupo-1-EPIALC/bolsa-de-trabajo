"""Proveedores de configuración (`SettingsProvider`): desde `.env` hoy, o panel HTTP mañana."""

import os
from collections.abc import Mapping
from typing import Any

import httpx

from app.domain.errors import InvalidInputError, UpstreamError
from app.domain.ports import SettingsProvider
from app.domain.settings import (
    AgentSettings,
    CvSettings,
    NotificationSettings,
    RecommendationSettings,
)

# Primero los modelos rápidos: los grandes (nemotron-3-ultra, deepseek) pueden tardar minutos
# cuando NVIDIA está cargado. Si uno no responde en AGENT_LLM_TIMEOUT_SECONDS, se pasa al siguiente.
DEFAULT_MODELS = (
    "minimaxai/minimax-m3.1-flash",
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "deepseek-ai/deepseek-v4.1-flash",
    "nvidia/nemotron-3-ultra-550b-a55b",
)
DEFAULT_MODELS_CV = DEFAULT_MODELS
DEFAULT_MODELS_VERIFIER = (
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "minimaxai/minimax-m3.1-flash",
    "deepseek-ai/deepseek-v4.1-flash",
    "nvidia/nemotron-3-ultra-550b-a55b",
)


def _flag(raw: str | None, default: bool) -> bool:
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in ("1", "true", "yes", "si", "sí")


def gemini_model(env: Mapping[str, str]) -> str | None:
    """Modelo de Gemini (AI Studio) que va primero en todas las listas, o None si está apagado.

    Se activa con `GEMINI_ENABLED=true` y una `GEMINI_API_KEY` no vacía.
    """
    if not _flag(env.get("GEMINI_ENABLED"), False) or not (env.get("GEMINI_API_KEY") or "").strip():
        return None
    return (env.get("GEMINI_MODEL") or "gemini-2.5-flash").strip()


def _with_first(model: str | None, models: tuple[str, ...]) -> tuple[str, ...]:
    if not model:
        return models
    return (model, *(m for m in models if m != model))


def _split_csv(raw: str | None, fallback: tuple[str, ...]) -> tuple[str, ...]:
    if not raw or not raw.strip():
        return fallback
    items = tuple(
        part.strip().lower() if "." not in part and "/" not in part else part.strip()
        for part in raw.split(",")
        if part.strip()
    )
    return items or fallback


class EnvSettingsProvider:
    """Construye `AgentSettings` leyendo variables de entorno en cada consulta."""

    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        self._env = env if env is not None else os.environ

    async def get(self) -> AgentSettings:
        e = self._env
        try:
            reco = RecommendationSettings(
                max_jobs_per_student=int(e.get("RECO_MAX_JOBS_PER_STUDENT", "5")),
                max_profiles_per_job=int(e.get("RECO_MAX_PROFILES_PER_JOB", "10")),
                max_items_per_job=int(e.get("RECO_MAX_ITEMS_PER_JOB", "5")),
                min_score=float(e.get("RECO_MIN_SCORE", "0")),
            )
            cv = CvSettings(
                max_size_mb=float(e.get("CV_MAX_SIZE_MB", "5")),
                allowed_extensions=tuple(
                    ext.strip().lower().lstrip(".")
                    for ext in e.get("CV_ALLOWED_EXTENSIONS", "pdf,docx,doc,md").split(",")
                    if ext.strip()
                ),
                max_text_chars=int(e.get("CV_MAX_TEXT_CHARS", "40000")),
            )
            notifications = NotificationSettings(
                enabled=_flag(e.get("NOTIFY_ENABLED"), True),
                min_score=float(e.get("NOTIFY_MIN_SCORE", "70")),
                max_per_event=int(e.get("NOTIFY_MAX_PER_EVENT", "10")),
                admin_email=e.get("NOTIFY_ADMIN_EMAIL", "").strip(),
                frontend_url=e.get("FRONTEND_URL", "http://localhost:8080").strip().rstrip("/"),
            )
            first = gemini_model(e)
            models = {
                "default": _with_first(first, _split_csv(e.get("AGENT_MODELS"), DEFAULT_MODELS)),
                "cv": _with_first(first, _split_csv(e.get("AGENT_MODELS_CV"), DEFAULT_MODELS_CV)),
                "verifier": _with_first(
                    first, _split_csv(e.get("AGENT_MODELS_VERIFIER"), DEFAULT_MODELS_VERIFIER)
                ),
            }
            return AgentSettings(
                nvidia_base_url=e.get(
                    "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
                ).rstrip("/"),
                models=models,
                rpm_limit=int(e.get("NVIDIA_RPM_LIMIT", "40")),
                llm_timeout_seconds=int(e.get("AGENT_LLM_TIMEOUT_SECONDS", "60")),
                temperature=float(e.get("AGENT_TEMPERATURE", "0.2")),
                max_verify_retries=int(e.get("AGENT_MAX_VERIFY_RETRIES", "1")),
                verify_strict=_flag(e.get("AGENT_VERIFY_STRICT"), False),
                recommendations=reco,
                cv=cv,
                notifications=notifications,
                source="env",
            )
        except ValueError as exc:
            raise InvalidInputError(f"Variable de entorno numérica inválida: {exc}") from exc


class PanelSettingsProvider:
    """Obtiene la configuración de agentes desde un panel HTTP con fallback opcional a env."""

    def __init__(
        self,
        panel_url: str,
        service_token: str,
        fallback: SettingsProvider | None = None,
        timeout: float = 5.0,
    ) -> None:
        self._url = panel_url.rstrip("/")
        self._token = service_token
        self._fallback = fallback
        self._timeout = timeout

    async def get(self) -> AgentSettings:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    self._url,
                    headers={"X-Service-Token": self._token},
                )
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            if self._fallback is not None:
                return await self._fallback.get()
            raise UpstreamError(f"No se pudo leer la configuración del panel: {exc}") from exc

        reco_raw = data.get("recommendations") or {}
        notif_raw = data.get("notifications") or {}
        cv_raw = data.get("cv") or {}
        models_raw = data.get("models") or {}
        return AgentSettings(
            nvidia_base_url=str(
                data.get("nvidia_base_url", "https://integrate.api.nvidia.com/v1")
            ).rstrip("/"),
            models={
                "default": tuple(models_raw.get("default") or DEFAULT_MODELS),
                "cv": tuple(models_raw.get("cv") or DEFAULT_MODELS_CV),
                "verifier": tuple(models_raw.get("verifier") or DEFAULT_MODELS_VERIFIER),
            },
            rpm_limit=int(data.get("rpm_limit", 40)),
            llm_timeout_seconds=int(data.get("llm_timeout_seconds", 60)),
            temperature=float(data.get("temperature", 0.2)),
            max_verify_retries=int(data.get("max_verify_retries", 1)),
            verify_strict=bool(data.get("verify_strict", False)),
            recommendations=RecommendationSettings(
                max_jobs_per_student=int(reco_raw.get("max_jobs_per_student", 5)),
                max_profiles_per_job=int(reco_raw.get("max_profiles_per_job", 10)),
                max_items_per_job=int(reco_raw.get("max_items_per_job", 5)),
                min_score=float(reco_raw.get("min_score", 0)),
            ),
            cv=CvSettings(
                max_size_mb=float(cv_raw.get("max_size_mb", 5.0)),
                allowed_extensions=tuple(
                    cv_raw.get("allowed_extensions") or ("pdf", "docx", "doc", "md")
                ),
                max_text_chars=int(cv_raw.get("max_text_chars", 40000)),
            ),
            notifications=NotificationSettings(
                enabled=bool(notif_raw.get("enabled", True)),
                min_score=float(notif_raw.get("min_score", 70)),
                max_per_event=int(notif_raw.get("max_per_event", 10)),
                admin_email=str(notif_raw.get("admin_email", "")).strip(),
                frontend_url=str(notif_raw.get("frontend_url", "http://localhost:8080")).rstrip(
                    "/"
                ),
            ),
            source="panel",
        )


def build_settings_provider(env: Mapping[str, str] | None = None) -> SettingsProvider:
    source_env = env if env is not None else os.environ
    env_provider = EnvSettingsProvider(source_env)
    source = source_env.get("AGENT_SETTINGS_SOURCE", "env").strip().lower()
    if source == "panel":
        panel_url = source_env.get("AGENT_SETTINGS_PANEL_URL", "")
        if not panel_url:
            raise InvalidInputError(
                "AGENT_SETTINGS_SOURCE=panel requiere definir AGENT_SETTINGS_PANEL_URL"
            )
        return PanelSettingsProvider(
            panel_url=panel_url,
            service_token=source_env.get("SERVICE_TOKEN", ""),
            fallback=env_provider,
        )
    return env_provider
