"""Dobles de prueba de los puertos de infraestructura."""

from datetime import UTC, datetime, timedelta

from app.domain.applications import ApplicantContact, ApplicantSnapshot
from app.domain.enums import JobStatus
from app.domain.errors import ProfileRequiredError, UpstreamError
from app.domain.models import CompanySnapshot, JobOpportunity


class FakeCompanyDirectory:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.snapshot = CompanySnapshot(
            name="Empresa de Prueba S.A.",
            industry="software",
            size="11-50",
            logo_url=None,
        )

    def snapshot_for(self, access_token: str) -> CompanySnapshot:
        self.calls.append(access_token)
        if access_token == "bad-token":  # noqa: S105 - valor ficticio de prueba
            raise UpstreamError("auth-service no disponible")
        return self.snapshot


class FakeApplicantDirectory:
    """profile-service ficticio: el contacto depende del token (datos ficticios)."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.phone: str | None = "+54 11 5555-0000"
        self.missing_profile = False

    def applicant_for(self, access_token: str) -> ApplicantSnapshot:
        self.calls.append(access_token)
        if self.missing_profile:
            raise ProfileRequiredError("Completá tu perfil antes de postularte")
        return ApplicantSnapshot(
            profile_id="prof-test-001",
            headline="Estudiante de Sistemas",
            contact=ApplicantContact(
                name="Persona Ficticia", email="persona@example.test", phone=self.phone
            ),
        )


class RecordingPublisher:
    def __init__(self) -> None:
        self.jobs: list[JobOpportunity] = []
        self.fail = False

    def job_created(self, job: JobOpportunity) -> None:
        if self.fail:
            raise UpstreamError("n8n no disponible")
        self.jobs.append(job)


class FixedClock:
    def __init__(self, current: datetime | None = None) -> None:
        self.current = current or datetime(2026, 11, 5, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs: int) -> None:
        self.current = self.current + timedelta(**kwargs)


class SequentialIds:
    def __init__(self, values: list[str] | None = None) -> None:
        self._values = values or [f"job-{index:03d}" for index in range(100, 200)]
        self._cursor = 0

    def new_id(self) -> str:
        value = self._values[self._cursor]
        self._cursor += 1
        return value


class RaceLoserRepository:
    """Repositorio que simula un escritor concurrente que gana la carrera de versiones.

    La primera lectura devuelve la versión que el servicio conoce; toda escritura
    falla (`update(...) -> False`), como cuando otro proceso avanzó la fila antes.
    Si se pasa `replacement`, cada lectura posterior devuelve esa versión nueva
    (el otro actor ya persistió su cambio).
    """

    def __init__(self, base: JobOpportunity, *, replacement: JobOpportunity | None = None) -> None:
        self._base = base
        self._replacement = replacement
        self._reads = 0

    def get(self, job_id: str) -> JobOpportunity | None:
        if job_id != self._base.id:
            return None
        self._reads += 1
        if self._replacement is not None and self._reads > 1:
            return self._replacement
        return self._base

    def add(self, job: JobOpportunity) -> None:
        return None

    def update(self, job: JobOpportunity, *, expected_version: int) -> bool:
        return False

    def list(
        self,
        *,
        status: JobStatus | None,
        company_id: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[JobOpportunity], int]:
        return [], 0

    def count(self) -> int:
        return 0

    def archive_company(self, company_id: str, deleted_at: datetime) -> int:
        return 0
