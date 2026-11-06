"""Dobles de prueba de los puertos de infraestructura."""

from datetime import UTC, datetime, timedelta

from app.domain.errors import UpstreamError
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
