"""Casos de uso de postulaciones (estudiante se postula / retira; empresa ve postulados)."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from app.domain.applications import (
    Application,
    ensure_can_see_applicants,
    require_student,
)
from app.domain.auth import Principal
from app.domain.errors import NotFoundError, UnauthorizedError
from app.domain.models import JobOpportunity
from app.domain.ports import (
    ApplicantDirectory,
    ApplicationRepository,
    Clock,
    IdGenerator,
    JobRepository,
)
from app.domain.rules import can_view


@dataclass(frozen=True)
class ApplyResult:
    application: Application
    created: bool  # False: ya estaba postulado (se refrescó su contacto)


@dataclass(frozen=True)
class StudentApplication:
    """Postulación propia con la oferta (None si la empresa se dio de baja)."""

    application: Application
    job: JobOpportunity | None


class ApplicationService:
    def __init__(
        self,
        *,
        applications: ApplicationRepository,
        jobs: JobRepository,
        directory: ApplicantDirectory,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._applications = applications
        self._jobs = jobs
        self._directory = directory
        self._clock = clock
        self._ids = ids

    def apply(self, principal: Principal, job_id: str, *, access_token: str | None) -> ApplyResult:
        """Postula al estudiante. Idempotente: repetirlo refresca el contacto compartido."""
        require_student(principal)
        if not access_token:
            raise UnauthorizedError("No se pudo identificar al estudiante para postularse")
        # Un estudiante sólo ve ofertas activas: una cerrada da 404, igual que en el detalle.
        job = self._visible_job(principal, job_id)
        existing = self._applications.get(job_id, principal.subject)
        applicant = self._directory.applicant_for(access_token)
        now = self._now()
        if existing is not None:
            refreshed = replace(existing, applicant=applicant, updated_at=now)
            self._applications.update(refreshed)
            return ApplyResult(refreshed, created=False)

        application = Application(
            id=self._ids.new_id(),
            job_id=job.id,
            company_id=job.company_id,
            student_id=principal.subject,
            applicant=applicant,
            applied_at=now,
            updated_at=now,
        )
        if self._applications.add(application):
            return ApplyResult(application, created=True)
        # Otro pedido del mismo estudiante ganó la carrera: devolvemos la que quedó.
        current = self._applications.get(job_id, principal.subject)
        return ApplyResult(current or application, created=False)

    def withdraw(self, principal: Principal, job_id: str) -> None:
        """Retira la postulación. Idempotente (204 aunque no estuviera postulado)."""
        require_student(principal)
        self._applications.remove(job_id, principal.subject)

    def mine(self, principal: Principal) -> list[StudentApplication]:
        require_student(principal)
        return [
            StudentApplication(application, self._jobs.get(application.job_id))
            for application in self._applications.list_for_student(principal.subject)
        ]

    def applicants(self, principal: Principal, job_id: str) -> list[Application]:
        job = self._jobs.get(job_id)
        if job is None:
            raise NotFoundError(f"Oferta '{job_id}' no encontrada", {"job_id": job_id})
        ensure_can_see_applicants(principal, job)
        return self._applications.list_for_job(job_id)

    def _visible_job(self, principal: Principal, job_id: str) -> JobOpportunity:
        job = self._jobs.get(job_id)
        if job is None or not can_view(job, principal):
            raise NotFoundError(f"Oferta '{job_id}' no encontrada", {"job_id": job_id})
        return job

    def _now(self) -> datetime:
        now = self._clock.now()
        return now.replace(tzinfo=UTC) if now.tzinfo is None else now.astimezone(UTC)
