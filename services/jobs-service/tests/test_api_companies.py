"""API de "mis búsquedas": sólo la empresa dueña y filtros por estado."""

from fastapi.testclient import TestClient

from app.domain.enums import JobStatus
from tests.builders import COMPANY_001, COMPANY_002, STUDENT_001, job
from tests.jwt_helpers import bearer


def test_my_searches_defaults_to_active_own_offers(client: TestClient, repository) -> None:
    repository.add(job(job_id="job-001", company_id=COMPANY_001))
    repository.add(job(job_id="job-002", company_id=COMPANY_001, status=JobStatus.CLOSED))
    repository.add(job(job_id="job-003", company_id=COMPANY_002))

    response = client.get("/api/v1/companies/me/searches", headers=bearer(COMPANY_001, "company"))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == ["job-001"]


def test_my_searches_can_filter_closed_and_all(client: TestClient, repository) -> None:
    repository.add(job(job_id="job-001", company_id=COMPANY_001))
    repository.add(job(job_id="job-002", company_id=COMPANY_001, status=JobStatus.CLOSED))
    headers = bearer(COMPANY_001, "company")

    closed = client.get("/api/v1/companies/me/searches?status=closed", headers=headers)
    everything = client.get("/api/v1/companies/me/searches?status=all", headers=headers)

    assert [item["id"] for item in closed.json()["items"]] == ["job-002"]
    assert {item["id"] for item in everything.json()["items"]} == {
        "job-001",
        "job-002",
    }


def test_my_searches_is_only_for_companies(client: TestClient) -> None:
    response = client.get("/api/v1/companies/me/searches", headers=bearer(STUDENT_001, "student"))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_my_searches_rejects_service_token(client: TestClient) -> None:
    response = client.get("/api/v1/companies/me/searches", headers={"X-Service-Token": "svc-token"})
    assert response.status_code == 403


def test_my_searches_paginates(client: TestClient, repository) -> None:
    for index in range(1, 4):
        repository.add(job(job_id=f"job-{index:03d}", company_id=COMPANY_001))

    response = client.get(
        "/api/v1/companies/me/searches?page=2&size=2",
        headers=bearer(COMPANY_001, "company"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["pages"] == 2
    assert len(body["items"]) == 1
