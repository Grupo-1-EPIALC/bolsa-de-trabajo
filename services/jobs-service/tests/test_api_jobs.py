"""API de ofertas: auth, validación, permisos, cierre/reapertura y contrato de respuesta."""

from typing import Any

from fastapi.testclient import TestClient

from app.domain.enums import JobStatus, SalaryVisibility
from app.domain.models import WorkConditions
from tests.builders import (
    COMPANY_001,
    COMPANY_002,
    STUDENT_001,
    conditions,
    job,
    salary,
)
from tests.jwt_helpers import ADMIN_001, bearer, make_token


def payload(
    *,
    kind: str = "required",
    level: int = 3,
    expires_at: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "title": "Desarrollador/a Backend Python Jr.",
        "description": "Desarrollo de microservicios REST con Python y PostgreSQL.",
        "seniority": "junior",
        "vacancies": 1,
        "location": {"country": "AR", "province": "CABA", "city": "Buenos Aires"},
        "work_conditions": {
            "work_schedule": ["full_time"],
            "work_modality": ["hybrid"],
            "weekly_hours": {"min": 30, "max": 40},
            "salary": {
                "min": 800000,
                "max": 1000000,
                "currency": "ARS",
                "period": "month",
                "visibility": "public",
            },
        },
        "requirements": {
            "skills": [
                {"name": "Python", "level": level, "kind": kind},
                {"name": "SQL", "level": 3, "kind": kind},
            ],
            "languages": [{"name": "Inglés", "level": "B1", "kind": "required"}],
            "experience": {
                "min_years": 1,
                "area": "desarrollo backend",
                "kind": "required",
            },
        },
    }
    if expires_at is not None:
        body["expires_at"] = expires_at
    return body


def test_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/jobs")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_rejects_invalid_token(client: TestClient) -> None:
    response = client.get("/api/v1/jobs", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert response.status_code == 401


def test_rejects_expired_token(client: TestClient) -> None:
    expired = make_token(STUDENT_001, "student", extra={"exp": 1})
    response = client.get("/api/v1/jobs", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_student_cannot_create(client: TestClient) -> None:
    response = client.post("/api/v1/jobs", json=payload(), headers=bearer(STUDENT_001, "student"))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_company_can_create(client: TestClient, publisher) -> None:
    response = client.post("/api/v1/jobs", json=payload(), headers=bearer(COMPANY_001, "company"))

    assert response.status_code == 201
    body = response.json()
    assert body["company_id"] == COMPANY_001
    assert body["status"] == "active"
    assert body["version"] == 1
    assert body["company_snapshot"]["name"] == "Empresa de Prueba S.A."
    assert body["requirements"]["skills"][0]["normalized"] == "python"
    assert body["work_conditions"]["salary"]["currency"] == "ARS"
    assert [event.id for event in publisher.jobs] == [body["id"]]


def test_service_token_cannot_create(client: TestClient) -> None:
    response = client.post("/api/v1/jobs", json=payload(), headers={"X-Service-Token": "svc-token"})
    assert response.status_code == 403


def test_create_without_required_skill_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/jobs",
        json=payload(kind="desired"),
        headers=bearer(COMPANY_001, "company"),
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_INPUT"
    assert error["details"]["field"] == "requirements.skills"


def test_create_with_invalid_skill_level_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/jobs",
        json=payload(level=6),
        headers=bearer(COMPANY_001, "company"),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INPUT"


def test_create_with_extra_server_field_returns_422(client: TestClient) -> None:
    body = payload()
    body["company_id"] = COMPANY_002
    response = client.post("/api/v1/jobs", json=body, headers=bearer(COMPANY_001, "company"))
    assert response.status_code == 422


def test_create_with_past_expiry_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/jobs",
        json=payload(expires_at="2020-01-01T00:00:00Z"),
        headers=bearer(COMPANY_001, "company"),
    )
    assert response.status_code == 422


def test_student_list_only_active_and_masked_salary(client: TestClient, repository) -> None:
    repository.add(
        job(
            job_id="job-001",
            job_conditions=conditions(job_salary=salary(visibility=SalaryVisibility.HIDDEN)),
        )
    )
    repository.add(job(job_id="job-002", status=JobStatus.CLOSED))

    response = client.get("/api/v1/jobs", headers=bearer(STUDENT_001, "student"))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == ["job-001"]
    assert body["items"][0]["work_conditions"]["salary"] is None


def test_service_token_can_list_closed_with_full_salary(client: TestClient, repository) -> None:
    repository.add(
        job(
            job_id="job-001",
            job_conditions=conditions(job_salary=salary(visibility=SalaryVisibility.HIDDEN)),
        )
    )
    repository.add(job(job_id="job-002", status=JobStatus.CLOSED))

    response = client.get("/api/v1/jobs?status=all", headers={"X-Service-Token": "svc-token"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert all(item["work_conditions"]["salary"] is not None for item in body["items"])


def test_admin_can_list_closed(client: TestClient, repository) -> None:
    repository.add(job(job_id="job-001", status=JobStatus.CLOSED))
    response = client.get("/api/v1/jobs?status=closed", headers=bearer(ADMIN_001, "admin"))
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_closed_offer_is_404_for_students_but_visible_to_owner(
    client: TestClient, repository
) -> None:
    repository.add(job(job_id="job-001", status=JobStatus.CLOSED))

    student = client.get("/api/v1/jobs/job-001", headers=bearer(STUDENT_001, "student"))
    owner = client.get("/api/v1/jobs/job-001", headers=bearer(COMPANY_001, "company"))

    assert student.status_code == 404
    assert student.json()["error"]["code"] == "NOT_FOUND"
    assert owner.status_code == 200
    assert owner.json()["status"] == "closed"


def test_unknown_offer_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/jobs/job-999", headers=bearer(STUDENT_001, "student"))
    assert response.status_code == 404


def test_other_company_cannot_edit_offer(client: TestClient, repository) -> None:
    """UT-JOBS-02: editar la oferta de otra empresa devuelve 403."""
    repository.add(job(job_id="job-001", company_id=COMPANY_002))

    response = client.patch(
        "/api/v1/jobs/job-001",
        json={"title": "Intento de edición"},
        headers=bearer(COMPANY_001, "company"),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_owner_can_edit_offer(client: TestClient, repository) -> None:
    repository.add(job(job_id="job-001"))

    response = client.patch(
        "/api/v1/jobs/job-001",
        json={"title": "Python Semi-Senior"},
        headers=bearer(COMPANY_001, "company"),
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Python Semi-Senior"
    assert response.json()["version"] == 2


def test_other_company_cannot_close_offer(client: TestClient, repository) -> None:
    repository.add(job(job_id="job-001", company_id=COMPANY_002))

    response = client.delete("/api/v1/jobs/job-001", headers=bearer(COMPANY_001, "company"))

    assert response.status_code == 403


def test_owner_closes_and_reopens_offer(client: TestClient, repository) -> None:
    repository.add(job(job_id="job-001"))
    headers = bearer(COMPANY_001, "company")

    closed = client.delete("/api/v1/jobs/job-001", headers=headers)
    assert closed.status_code == 204
    assert closed.content == b""

    after_close = client.get("/api/v1/jobs/job-001", headers=headers)
    assert after_close.json()["status"] == "closed"
    assert after_close.json()["version"] == 2

    reopened = client.patch("/api/v1/jobs/job-001", json={"status": "active"}, headers=headers)
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "active"
    assert reopened.json()["version"] == 3


def test_patch_cannot_close_offer(client: TestClient, repository) -> None:
    repository.add(job(job_id="job-001"))
    response = client.patch(
        "/api/v1/jobs/job-001",
        json={"status": "closed"},
        headers=bearer(COMPANY_001, "company"),
    )
    assert response.status_code == 422


def test_salary_visibility_for_owner_and_other_company(client: TestClient, repository) -> None:
    repository.add(
        job(
            job_id="job-001",
            company_id=COMPANY_002,
            job_conditions=conditions(job_salary=salary(visibility=SalaryVisibility.ON_MATCH)),
        )
    )

    other = client.get("/api/v1/jobs/job-001", headers=bearer(COMPANY_001, "company"))
    owner = client.get("/api/v1/jobs/job-001", headers=bearer(COMPANY_002, "company"))

    assert other.json()["work_conditions"]["salary"] is None
    assert owner.json()["work_conditions"]["salary"] is not None


def test_list_limit_alias(client: TestClient, repository) -> None:
    for index in range(1, 4):
        repository.add(job(job_id=f"job-{index:03d}"))

    response = client.get("/api/v1/jobs?limit=2", headers=bearer(STUDENT_001, "student"))

    assert response.status_code == 200
    assert response.json()["size"] == 2
    assert len(response.json()["items"]) == 2
    assert response.json()["pages"] == 2


def test_update_can_clear_work_conditions(client: TestClient, repository) -> None:
    repository.add(job(job_id="job-001"))
    response = client.patch(
        "/api/v1/jobs/job-001",
        json={"work_conditions": None},
        headers=bearer(COMPANY_001, "company"),
    )
    assert response.status_code == 200
    assert response.json()["work_conditions"]["salary"] is None
    assert response.json()["work_conditions"]["work_schedule"] == []
    assert isinstance(WorkConditions(), WorkConditions)


def test_create_body_can_omit_optional_blocks(client: TestClient) -> None:
    body = payload()
    body.pop("work_conditions")
    response = client.post("/api/v1/jobs", json=body, headers=bearer(COMPANY_001, "company"))
    assert response.status_code == 201
    assert response.json()["work_conditions"]["salary"] is None
