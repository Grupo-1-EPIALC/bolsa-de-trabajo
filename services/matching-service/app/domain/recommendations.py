"""Recomendaciones generadas por IA en n8n (`origin = "AI"`) y pedidos de análisis.

matching-service no llama a ningún LLM (AGENTS.md §4.4): n8n hace el análisis y persiste
acá el resultado; el servicio lo devuelve junto al bloque calculado por reglas.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from app.domain.errors import InvalidInputError

DEFAULT_AI_DISCLAIMER = (
    "Recomendación orientativa generada por IA. El puntaje y el ranking provienen "
    "exclusivamente del motor de reglas."
)


class RecommendationMode(StrEnum):
    STUDENT = "student"  # ofertas recomendadas a un estudiante
    COMPANY = "company"  # candidatos recomendados para una oferta
    TRAINING = "training"  # qué competencias sumar o mejorar, en general (no por oferta)


# `job_id` con el que se guarda la formación general de un estudiante (no es de una oferta).
GENERAL_TRAINING_KEY = "general"


class RequestStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class AiMetadata:
    model: str
    prompt_version: str
    generated_at: str
    disclaimer: str = DEFAULT_AI_DISCLAIMER
    verified: bool = False

    def __post_init__(self) -> None:
        for name in ("model", "prompt_version", "generated_at"):
            if not str(getattr(self, name)).strip():
                raise InvalidInputError(
                    f"'{name}' es obligatorio en resultados de IA", {"field": name}
                )


@dataclass(frozen=True)
class AiRecommendation:
    """Recomendación de IA para un par perfil-oferta."""

    id: str
    mode: RecommendationMode
    profile_id: str
    job_id: str
    content: Mapping[str, object]
    metadata: AiMetadata
    created_at: str
    summary: str = ""
    request_id: str = ""
    items: tuple[Mapping[str, object], ...] = ()
    origin: str = field(default="AI", init=False)

    def __post_init__(self) -> None:
        if not self.profile_id.strip() or not self.job_id.strip():
            raise InvalidInputError("profile_id y job_id son obligatorios")


@dataclass(frozen=True)
class RecommendationRequest:
    id: str
    mode: RecommendationMode
    subject_id: str  # profile_id (student, training) o job_id (company)
    status: RequestStatus
    created_at: str
    updated_at: str
    error: Mapping[str, object] = field(default_factory=dict)
    job_id: str = ""  # en desuso: la formación ya no es por oferta
