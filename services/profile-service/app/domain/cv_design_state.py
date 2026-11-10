"""Estado persistido del diseño del CV de un estudiante (va dentro de `StudentProfile`).

Guarda las dos fuentes que pueden pisar la elección por reglas:
- `ai`: la última sugerencia del agente `cv_designer` de n8n (WF-07), con `origin: "AI"`;
- `user`: el diseño que eligió el propio estudiante.

La elección por reglas no se guarda: se recalcula siempre con el perfil vigente
(`app/domain/cv_design.py`).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AiDesignStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class AiCvDesign:
    status: AiDesignStatus
    request_id: str
    requested_at: datetime
    # Huella del contenido que vio la IA: si el perfil cambia, la sugerencia queda vieja.
    fingerprint: str
    layout: str | None = None
    section_order: tuple[str, ...] = ()
    rationale: str = ""
    model: str | None = None
    prompt_version: str | None = None
    generated_at: datetime | None = None
    disclaimer: str = ""
    error: str | None = None


@dataclass(frozen=True)
class UserCvDesign:
    layout: str
    chosen_at: datetime


@dataclass(frozen=True)
class CvDesignState:
    ai: AiCvDesign | None = None
    user: UserCvDesign | None = None
