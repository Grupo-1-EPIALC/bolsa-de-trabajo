"""UT-JOBS-04: postulaciones (estudiante se postula/retira; la empresa ve postulados y contacto)."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.domain.applications import ApplicantContact, ApplicantSnapshot, Application
from app.domain.enums import JobStatus
from app.domain.errors import ProfileRequiredError
from app.infrastructure.applicant_directory import applicant_from_profile
from app.infrastructure.repositories.applications import SqlAlchemyApplicationRepository
from app.infrastructure.repositories.memory_jobs import InMemoryJobRepository
from tests.builders import COMPANY_001, COMPANY_002, STUDENT_001, job
from tests.fakes import FakeApplicantDirectory, FixedClock
from tests.jwt_helpers import ADMIN_001, bearer

STUDENT_002 = "11111111-1111-4111-8111-000000000002"
SERVICE = {"X-Service-Token": "svc-token"}
EVENTS = "/api/v1/jobs/internal/account-events"
MINE = "/api/v1/jobs/applications/me"


def apply_url(job_id: str = "job-001") -> str:
    return f"/api/v1/jobs/{job_id}/applications"


def student(sub: str = STUDENT_001) -> dict[str, str]:
    return bearer(sub, "student")


def company(sub: str = COMPANY_001) -> dict[str, str]:
    return bearer(sub, "company")


@pytest.fixture
def jobs(repository: InMemoryJobRepository) -> InMemoryJobRepository:
    repository.add(job(job_id="job-001"))
    repository.add(job(job_id="job-002", company_id=COMPANY_002))
    repository.add(job(job_id="job-003", status=JobStatus.CLOSED))
    return repository


def test_ut_jobs_04_estudiante_se_postula_y_la_empresa_ve_su_contacto(
    client: TestClient, jobs: InMemoryJobRepository
) -> None:
    created = client.post(apply_url(), headers=student())
    assert created.status_code == 201
    assert created.json()["contact"] == {
        "name": "Persona Ficticia",
        "email": "persona@example.test",
        "phone": "+54 11 5555-0000",
    }

    listed = client.get(apply_url(), headers=company())
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["profile_id"] == "prof-test-001"
    assert item["headline"] == "Estudiante de Sistemas"
    assert item["contact"]["email"] == "persona@example.test"
    assert item["applied_at"].startswith("2026-11-05T12:00:00")


def test_ut_jobs_04_repetir_la_postulacion_es_idempotente_y_refresca_el_contacto(
    client: TestClient,
    jobs: InMemoryJobRepository,
    applicants: FakeApplicantDirectory,
    clock: FixedClock,
) -> None:
    first = client.post(apply_url(), headers=student()).json()
    applicants.phone = "+54 11 4444-0000"
    clock.advance(hours=1)

    again = client.post(apply_url(), headers=student())
    assert again.status_code == 200
    assert again.json()["id"] == first["id"]
    assert again.json()["applied_at"] == first["applied_at"]
    assert again.json()["contact"]["phone"] == "+54 11 4444-0000"
    assert client.get(apply_url(), headers=company()).json()["total"] == 1


def test_ut_jobs_04_estudiante_ve_y_retira_sus_postulaciones(
    client: TestClient, jobs: InMemoryJobRepository
) -> None:
    client.post(apply_url("job-001"), headers=student())
    client.post(apply_url("job-002"), headers=student())

    mine = client.get(MINE, headers=student())
    assert mine.status_code == 200
    assert mine.json()["total"] == 2
    assert {item["job_id"] for item in mine.json()["items"]} == {"job-001", "job-002"}
    assert mine.json()["items"][0]["job"]["title"]
    assert "contact" not in mine.json()["items"][0]

    withdraw = apply_url("job-001") + "/me"
    assert client.delete(withdraw, headers=student()).status_code == 204
    assert client.delete(withdraw, headers=student()).status_code == 204
    assert client.get(apply_url("job-001"), headers=company()).json() == {
        "job_id": "job-001",
        "items": [],
        "total": 0,
    }
    remaining = client.get(MINE, headers=student()).json()
    assert [item["job_id"] for item in remaining["items"]] == ["job-002"]


def test_ut_jobs_04_reglas_de_acceso(client: TestClient, jobs: InMemoryJobRepository) -> None:
    client.post(apply_url(), headers=student())

    # Sólo estudiantes se postulan
    assert client.post(apply_url(), headers=company()).status_code == 403
    assert client.post(apply_url()).status_code == 401
    # Ofertas cerradas o inexistentes: 404 (como el detalle)
    assert client.post(apply_url("job-003"), headers=student()).status_code == 404
    assert client.post(apply_url("nope"), headers=student()).status_code == 404
    # Sólo la empresa dueña, admin o servicios ven a los postulados
    assert client.get(apply_url(), headers=company(COMPANY_002)).status_code == 403
    assert client.get(apply_url(), headers=student(STUDENT_002)).status_code == 403
    assert client.get(apply_url(), headers=bearer(ADMIN_001, "admin")).json()["total"] == 1
    assert client.get(apply_url(), headers=SERVICE).json()["total"] == 1
    assert client.get(apply_url("nope"), headers=company()).status_code == 404
    # "Mis postulaciones" es sólo de estudiantes
    assert client.get(MINE, headers=company()).status_code == 403


def test_ut_jobs_04_sin_perfil_no_puede_postularse(
    client: TestClient, jobs: InMemoryJobRepository, applicants: FakeApplicantDirectory
) -> None:
    applicants.missing_profile = True
    response = client.post(apply_url(), headers=student())
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PROFILE_REQUIRED"


def test_ut_jobs_04_la_empresa_sigue_viendo_postulados_de_una_oferta_cerrada(
    client: TestClient, jobs: InMemoryJobRepository
) -> None:
    client.post(apply_url(), headers=student())
    assert client.delete("/api/v1/jobs/job-001", headers=company()).status_code == 204
    assert client.get(apply_url(), headers=company()).json()["total"] == 1


def test_ut_jobs_04_bajas_de_cuenta_borran_postulaciones(
    client: TestClient, jobs: InMemoryJobRepository
) -> None:
    client.post(apply_url("job-001"), headers=student())
    client.post(apply_url("job-002"), headers=student())
    client.post(apply_url("job-002"), headers=student(STUDENT_002))

    def deleted(user_id: str, role: str) -> dict[str, object]:
        return {
            "event": "account.deleted",
            "user_id": user_id,
            "role": role,
            "deleted": True,
            "occurred_at": "2026-11-06T21:44:40Z",
        }

    by_student = client.post(EVENTS, json=deleted(STUDENT_001, "student"), headers=SERVICE)
    assert by_student.json()["removed_applications"] == 2
    assert by_student.json()["result"] == "archived"
    by_company = client.post(EVENTS, json=deleted(COMPANY_002, "company"), headers=SERVICE)
    assert by_company.json()["removed_applications"] == 1
    assert by_company.json()["archived_jobs"] == 1


def test_ut_jobs_04_el_contacto_sale_del_perfil_sin_marcadores() -> None:
    snapshot = applicant_from_profile(
        {
            "id": "prof-1",
            "headline": "COMPLETAR_MANUALMENTE",
            "personal": {"name": " Ana ", "email": "ana@example.test", "phone": ""},
        }
    )
    assert snapshot == ApplicantSnapshot(
        profile_id="prof-1",
        headline=None,
        contact=ApplicantContact(name="Ana", email="ana@example.test", phone=None),
    )
    with pytest.raises(ProfileRequiredError):
        applicant_from_profile({"id": "prof-1", "personal": {"name": "Ana"}})


def test_ut_jobs_04_repositorio_sql(tmp_path: Path) -> None:
    repo = SqlAlchemyApplicationRepository(f"sqlite:///{tmp_path / 'apps.db'}", schema=None)
    when = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
    contact = ApplicantContact(name="Ana", email="ana@example.test")
    first = Application(
        id="app-1",
        job_id="job-001",
        company_id=COMPANY_001,
        student_id=STUDENT_001,
        applicant=ApplicantSnapshot(profile_id="prof-1", contact=contact),
        applied_at=when,
        updated_at=when,
    )
    assert repo.add(first) is True
    assert repo.add(first) is False
    repo.update(replace(first, applicant=ApplicantSnapshot("prof-1", contact, "Backend")))
    stored = repo.get("job-001", STUDENT_001)
    assert stored is not None
    assert stored.applicant.headline == "Backend"
    assert stored.applied_at == when
    assert [a.id for a in repo.list_for_job("job-001")] == ["app-1"]
    assert [a.id for a in repo.list_for_student(STUDENT_001)] == ["app-1"]
    assert repo.remove_company(COMPANY_002) == 0
    assert repo.remove("job-001", STUDENT_001) is True
    assert repo.remove("job-001", STUDENT_001) is False
    repo.add(first)
    assert repo.remove_student(STUDENT_001) == 1
    repo.dispose()
