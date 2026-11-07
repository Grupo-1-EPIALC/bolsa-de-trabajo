"""Repositorio en memoria para tests y para desarrollo sin PostgreSQL."""

from datetime import UTC, datetime
from threading import Lock

from app.domain.enums import JobStatus
from app.domain.models import JobOpportunity


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[str, JobOpportunity] = {}
        self._lock = Lock()

    def add(self, job: JobOpportunity) -> None:
        with self._lock:
            self._jobs[job.id] = job

    def update(self, job: JobOpportunity, *, expected_version: int) -> bool:
        with self._lock:
            current = self._jobs.get(job.id)
            if current is None or current.version != expected_version:
                return False
            self._jobs[job.id] = job
            return True

    def get(self, job_id: str) -> JobOpportunity | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(
        self,
        *,
        status: JobStatus | None,
        company_id: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[JobOpportunity], int]:
        with self._lock:
            jobs = list(self._jobs.values())
        if status is not None:
            jobs = [job for job in jobs if job.status is status]
        if company_id is not None:
            jobs = [job for job in jobs if job.company_id == company_id]
        # Orden estable: primero por id ascendente y después por publicación descendente.
        jobs.sort(key=lambda job: job.id)
        jobs.sort(key=_publication_key, reverse=True)
        return jobs[offset : offset + limit], len(jobs)

    def count(self) -> int:
        with self._lock:
            return len(self._jobs)


def _publication_key(job: JobOpportunity) -> datetime:
    value = job.published_at or job.created_at
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
