"""Repositorios: round-trip del documento, filtros y orden."""

from app.domain.enums import JobStatus
from app.infrastructure.repositories.codec import job_from_document, job_to_document
from app.infrastructure.repositories.memory_jobs import InMemoryJobRepository
from app.infrastructure.repositories.sqlalchemy_jobs import (
    SqlAlchemyJobRepository,
    normalize_database_url,
)
from tests.builders import COMPANY_001, COMPANY_002, job


def test_document_roundtrip_preserves_every_block() -> None:
    original = job()
    restored = job_from_document(job_to_document(original))
    assert restored == original


def test_memory_repository_roundtrip_and_update() -> None:
    repository = InMemoryJobRepository()
    original = job()
    repository.add(original)

    assert repository.get(original.id) == original
    assert repository.count() == 1

    updated = job(title="Actualizado", version=2)
    assert repository.update(updated, expected_version=1) is True
    assert repository.get(original.id) == updated


def test_memory_repository_optimistic_lock_rejects_stale_version() -> None:
    """El guard de versión evita el lost-update: la fila se quedó atrás y no se persiste."""
    repository = InMemoryJobRepository()
    original = job()
    repository.add(original)

    stale = job(title="Lento", version=2)
    assert repository.update(stale, expected_version=3) is False
    assert repository.get(original.id) == original

    fresh = job(title="Ganador", version=3)
    assert repository.update(fresh, expected_version=1) is True
    assert repository.get(original.id) == fresh


def test_memory_repository_filters_and_order() -> None:
    repository = InMemoryJobRepository()
    repository.add(job(job_id="job-001", company_id=COMPANY_001))
    repository.add(job(job_id="job-002", company_id=COMPANY_002))
    repository.add(job(job_id="job-003", company_id=COMPANY_001, status=JobStatus.CLOSED))

    active, total = repository.list(status=JobStatus.ACTIVE, company_id=None, offset=0, limit=10)
    own, own_total = repository.list(status=None, company_id=COMPANY_001, offset=0, limit=10)
    page, _ = repository.list(status=None, company_id=None, offset=1, limit=1)

    assert total == 2
    assert [item.id for item in active] == ["job-001", "job-002"]
    assert own_total == 2
    assert [item.id for item in own] == ["job-001", "job-003"]
    assert [item.id for item in page] == ["job-002"]


def test_sqlalchemy_repository_roundtrip() -> None:
    repository = SqlAlchemyJobRepository("sqlite+pysqlite:///:memory:", schema=None)
    try:
        original = job()
        repository.add(original)

        assert repository.get(original.id) == original
        assert repository.count() == 1

        updated = job(title="Actualizado en SQL", version=2)
        assert repository.update(updated, expected_version=1) is True
        assert repository.get(original.id) == updated
        assert repository.get("job-999") is None
    finally:
        repository.dispose()


def test_sqlalchemy_repository_optimistic_lock_rejects_stale_version() -> None:
    """UPDATE con guard de versión: UPDATE ... WHERE version = expected; rowcount → False."""
    repository = SqlAlchemyJobRepository("sqlite+pysqlite:///:memory:", schema=None)
    try:
        original = job()
        repository.add(original)

        rival = job(title="Edición ganadora", version=2)
        assert repository.update(rival, expected_version=1) is True

        perdedor = job(title="Edición perdedora", version=2)
        assert repository.update(perdedor, expected_version=1) is False
        assert repository.get(original.id).title == "Edición ganadora"  # type: ignore[union-attr]
    finally:
        repository.dispose()


def test_sqlalchemy_repository_filters_and_order() -> None:
    repository = SqlAlchemyJobRepository("sqlite+pysqlite:///:memory:", schema=None)
    try:
        repository.add(job(job_id="job-001", company_id=COMPANY_001))
        repository.add(job(job_id="job-002", company_id=COMPANY_002))
        repository.add(job(job_id="job-003", company_id=COMPANY_001, status=JobStatus.CLOSED))

        active, total = repository.list(
            status=JobStatus.ACTIVE, company_id=None, offset=0, limit=10
        )
        own, own_total = repository.list(status=None, company_id=COMPANY_001, offset=0, limit=10)
        page, _ = repository.list(status=None, company_id=None, offset=1, limit=1)

        assert total == 2
        assert [item.id for item in active] == ["job-001", "job-002"]
        assert own_total == 2
        assert {item.id for item in own} == {"job-001", "job-003"}
        assert len(page) == 1
    finally:
        repository.dispose()


def test_database_url_uses_psycopg_driver() -> None:
    assert (
        normalize_database_url("postgresql://user:pass@db:5432/bolsa")
        == "postgresql+psycopg://user:pass@db:5432/bolsa"
    )
    assert (
        normalize_database_url("postgres://user:pass@db:5432/bolsa")
        == "postgresql+psycopg://user:pass@db:5432/bolsa"
    )
    assert (
        normalize_database_url("postgresql+psycopg://user:pass@db:5432/bolsa")
        == "postgresql+psycopg://user:pass@db:5432/bolsa"
    )
    assert normalize_database_url("sqlite+pysqlite:///:memory:") == "sqlite+pysqlite:///:memory:"
