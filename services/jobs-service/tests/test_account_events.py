"""UT-JOBS-03: eventos de cuenta de auth-service (`contracts/account_events.md`)."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.domain.enums import JobStatus
from app.infrastructure.repositories.codec import job_to_document
from app.infrastructure.repositories.deleted_accounts import (
    InMemoryDeletedAccounts,
    SqlAlchemyDeletedAccounts,
)
from app.infrastructure.repositories.memory_jobs import InMemoryJobRepository
from app.infrastructure.repositories.sqlalchemy_jobs import SqlAlchemyJobRepository
from app.infrastructure.seed import seed_repository
from tests.builders import COMPANY_001, COMPANY_002, STUDENT_001, job
from tests.jwt_helpers import ADMIN_001, bearer

EVENTS = "/api/v1/jobs/internal/account-events"
SERVICE = {"X-Service-Token": "svc-token"}
WHEN = datetime(2026, 11, 6, 21, 44, tzinfo=UTC)


def event(user_id: str, kind: str = "account.deleted", role: str = "company") -> dict[str, Any]:
    return {
        "event": kind,
        "user_id": user_id,
        "role": role,
        "deleted": kind == "account.deleted",
        "email": "empresa@example.test",
        "actor_id": ADMIN_001,
        "occurred_at": "2026-11-06T21:44:40.123Z",
    }


def test_ut_jobs_03_solo_servicios_pueden_mandar_eventos(client: TestClient) -> None:
    body = event(COMPANY_001)
    assert client.post(EVENTS, json=body).status_code == 401
    assert client.post(EVENTS, json=body, headers=bearer(COMPANY_001, "company")).status_code == 403
    assert client.post(EVENTS, json=body, headers={"X-Service-Token": "otro"}).status_code == 401


def test_ut_jobs_03_borrar_empresa_archiva_sus_ofertas(
    client: TestClient, repository: InMemoryJobRepository
) -> None:
    repository.add(job(job_id="job-001"))
    repository.add(job(job_id="job-002", status=JobStatus.CLOSED))
    repository.add(job(job_id="job-003", company_id=COMPANY_002))

    response = client.post(EVENTS, json=event(COMPANY_001), headers=SERVICE)
    assert response.status_code == 200
    assert response.json() == {
        "event": "account.deleted",
        "user_id": COMPANY_001,
        "result": "archived",
        "archived_jobs": 2,
    }

    listed = client.get("/api/v1/jobs?status=all", headers=SERVICE).json()
    assert [item["id"] for item in listed["items"]] == ["job-003"]
    assert client.get("/api/v1/jobs/job-001", headers=SERVICE).status_code == 404
    assert set(repository.archived) == {"job-001", "job-002"}


def test_ut_jobs_03_el_jwt_vigente_de_una_cuenta_borrada_se_rechaza(client: TestClient) -> None:
    client.post(EVENTS, json=event(COMPANY_001), headers=SERVICE)
    for path in ("/api/v1/companies/me/searches", "/api/v1/jobs"):
        response = client.get(path, headers=bearer(COMPANY_001, "company"))
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "ACCOUNT_DELETED"
    # Otras cuentas siguen funcionando.
    assert client.get("/api/v1/jobs", headers=bearer(STUDENT_001, "student")).status_code == 200


def test_ut_jobs_03_idempotente_y_eventos_que_se_ignoran(
    client: TestClient, repository: InMemoryJobRepository
) -> None:
    repository.add(job(job_id="job-001"))
    first = client.post(EVENTS, json=event(COMPANY_001), headers=SERVICE).json()
    second = client.post(EVENTS, json=event(COMPANY_001), headers=SERVICE).json()
    assert (first["result"], second["result"]) == ("archived", "ignored")

    student = client.post(EVENTS, json=event(STUDENT_001, role="student"), headers=SERVICE)
    assert student.json()["result"] == "registered"
    for kind in ("account.updated", "account.algo_nuevo"):
        body = event(COMPANY_002, kind)
        assert client.post(EVENTS, json=body, headers=SERVICE).json()["result"] == "ignored"


def test_ut_jobs_03_repositorios_sql_archivan_y_registran(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'acc.db'}"
    repository = SqlAlchemyJobRepository(url, schema=None)
    deleted = SqlAlchemyDeletedAccounts(url, schema=None)
    try:
        repository.add(job(job_id="job-001"))
        repository.add(job(job_id="job-002"))
        repository.add(job(job_id="job-003", company_id=COMPANY_002))
        assert repository.archive_company(COMPANY_001, WHEN) == 2
        assert repository.archive_company(COMPANY_001, WHEN) == 0
        assert repository.get("job-001") is None
        assert repository.count() == 1

        assert deleted.mark(COMPANY_001, "company", WHEN) is True
        assert deleted.mark(COMPANY_001, "company", WHEN) is False
        assert deleted.contains(COMPANY_001)
        assert not deleted.contains(COMPANY_002)
    finally:
        repository.dispose()
        deleted.dispose()


def test_ut_jobs_03_el_seed_no_recarga_empresas_borradas(tmp_path: Path) -> None:
    seed = tmp_path / "seed.json"
    documents = [
        job_to_document(job(job_id="job-001")),
        job_to_document(job(job_id="job-002", company_id=COMPANY_002)),
    ]
    seed.write_text(json.dumps(documents, default=str), encoding="utf-8")
    deleted = InMemoryDeletedAccounts()
    deleted.mark(COMPANY_001, "company", WHEN)
    repository = InMemoryJobRepository()

    assert seed_repository(repository, seed, is_deleted=deleted.contains) == 1
    assert repository.get("job-001") is None
    assert repository.get("job-002") is not None
