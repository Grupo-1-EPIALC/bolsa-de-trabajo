"""Puertos (interfaces) que la infraestructura implementa y el dominio/application consumen."""

from datetime import datetime
from typing import Any, Protocol

from app.domain.auth import Principal
from app.domain.enums import JobStatus
from app.domain.models import CompanySnapshot, JobOpportunity

JsonDict = dict[str, Any]


class JobRepository(Protocol):
    def add(self, job: JobOpportunity) -> None: ...

    def update(self, job: JobOpportunity, *, expected_version: int) -> bool:
        """Persiste `job` sólo si la versión guardada es aún `expected_version`.

        Devuelve `False` (no lanza) cuando otra escritura avanzó `version` o la oferta
        ya no existe: así no puede perderse una actualización (lost update) entre
        procesos concurrentes. La aplicación traduce `False` a un 409 `CONFLICT`.
        """
        ...

    def get(self, job_id: str) -> JobOpportunity | None: ...

    def list(
        self,
        *,
        status: JobStatus | None,
        company_id: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[JobOpportunity], int]: ...

    def count(self) -> int: ...


class CompanyDirectory(Protocol):
    def snapshot_for(self, access_token: str) -> CompanySnapshot: ...


class EventPublisher(Protocol):
    def job_created(self, job: JobOpportunity) -> None: ...


class TokenVerifier(Protocol):
    def verify(self, token: str) -> Principal: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self) -> str: ...
