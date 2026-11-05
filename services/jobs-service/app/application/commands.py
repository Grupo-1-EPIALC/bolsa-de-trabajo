"""Comandos de entrada de los casos de uso (sin dependencias de FastAPI)."""

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.enums import Seniority
from app.domain.models import Location, Requirements, WorkConditions


@dataclass(frozen=True)
class JobDraft:
    """Datos que una empresa puede enviar al crear una oferta.

    El `company_id`, el estado, la versión y los timestamps los pone el servicio.
    """

    title: str
    description: str
    seniority: Seniority
    location: Location
    requirements: Requirements
    responsibilities: tuple[str, ...] = ()
    area: str = ""
    vacancies: int = 1
    work_conditions: WorkConditions = field(default_factory=WorkConditions)
    benefits: tuple[str, ...] = ()
    expires_at: datetime | None = None
