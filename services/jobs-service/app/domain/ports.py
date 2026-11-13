"""Puertos (interfaces) que la infraestructura implementa y el dominio/application consumen."""

from datetime import datetime
from typing import Any, Protocol

from app.domain.applications import ApplicantSnapshot, Application
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

    def archive_company(self, company_id: str, deleted_at: datetime) -> int:
        """Mueve todas las ofertas de la empresa al archivo. Devuelve cuántas movió."""
        ...


class ApplicationRepository(Protocol):
    """Postulaciones: una por estudiante y oferta (`job_id`, `student_id` únicos)."""

    def add(self, application: Application) -> bool:
        """Guarda una postulación nueva. False si el estudiante ya estaba postulado."""
        ...

    def update(self, application: Application) -> None: ...

    def get(self, job_id: str, student_id: str) -> Application | None: ...

    def remove(self, job_id: str, student_id: str) -> bool:
        """Borra la postulación. False si no existía."""
        ...

    def list_for_job(self, job_id: str) -> list[Application]:
        """Postulaciones de la oferta, de la más reciente a la más vieja."""
        ...

    def list_for_student(self, student_id: str) -> list[Application]:
        """Postulaciones del estudiante, de la más reciente a la más vieja."""
        ...

    def remove_student(self, student_id: str) -> int:
        """Borra todas las postulaciones del estudiante. Devuelve cuántas borró."""
        ...

    def remove_company(self, company_id: str) -> int:
        """Borra las postulaciones a ofertas de la empresa. Devuelve cuántas borró."""
        ...


class ApplicantDirectory(Protocol):
    def applicant_for(self, access_token: str) -> ApplicantSnapshot:
        """Contacto y título del estudiante autenticado (perfil de profile-service).

        Lanza `ProfileRequiredError` si no tiene perfil o le falta nombre o email.
        """
        ...


class DeletedAccounts(Protocol):
    """Cuentas dadas de baja en auth-service (soft delete)."""

    def mark(self, user_id: str, role: str, deleted_at: datetime) -> bool:
        """Registra la baja. False si ya estaba registrada (evento repetido)."""
        ...

    def contains(self, user_id: str) -> bool: ...


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
