"""Puertos (interfaces) que el dominio y la aplicación usan; la infraestructura los implementa."""

from typing import Any, Protocol

from app.domain.auth import Principal
from app.domain.recommendations import AiRecommendation, RecommendationRequest
from app.domain.settings import RecommendationSettings

JsonDict = dict[str, Any]


class ProfileSource(Protocol):
    """Perfiles de estudiantes (profile-service por REST; nunca su base de datos)."""

    def get_profile(self, profile_id: str) -> JsonDict: ...

    def list_profiles(self, limit: int) -> list[JsonDict]: ...


class JobSource(Protocol):
    """Ofertas de trabajo (jobs-service por REST)."""

    def get_job(self, job_id: str) -> JsonDict: ...

    def list_active_jobs(self, limit: int) -> list[JsonDict]: ...


class RecommendationRepository(Protocol):
    def save(self, recommendation: AiRecommendation) -> AiRecommendation: ...

    def latest_for_profile(self, profile_id: str) -> list[AiRecommendation]:
        """Última recomendación `mode=student` por oferta para el estudiante."""
        ...

    def latest_for_job(self, job_id: str) -> list[AiRecommendation]:
        """Última recomendación `mode=company` por candidato para la oferta."""
        ...

    def latest_training(self, profile_id: str) -> AiRecommendation | None:
        """Última formación general (`mode=training`) del estudiante."""
        ...


class RecommendationRequestRepository(Protocol):
    def save(self, request: RecommendationRequest) -> RecommendationRequest: ...

    def get(self, request_id: str) -> RecommendationRequest | None: ...

    def latest_for(
        self, mode: str, subject_id: str, job_id: str = ""
    ) -> RecommendationRequest | None: ...


class AnalysisTrigger(Protocol):
    """Dispara el análisis de IA en n8n (`POST /webhook/recommendations`, WF-06)."""

    def request_analysis(
        self, request_id: str, mode: str, subject_id: str, limit: int
    ) -> JsonDict: ...


class Clock(Protocol):
    def iso_now(self) -> str: ...


class IdGenerator(Protocol):
    def new_id(self, prefix: str) -> str: ...


class TokenVerifier(Protocol):
    """Valida el JWT de usuario emitido por auth-service (RS256 + JWKS)."""

    def verify(self, token: str) -> Principal: ...


class SettingsRepository(Protocol):
    def get(self) -> RecommendationSettings: ...

    def save(self, settings: RecommendationSettings) -> RecommendationSettings: ...
