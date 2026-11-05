"""Configuración de recomendaciones ajustable por admin (cantidad de ofertas y de candidatos)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_container
from app.domain.errors import InvalidInputError
from app.domain.settings import RecommendationSettings
from app.infrastructure.config import MatchingSettings
from app.infrastructure.container import Container, build_container
from app.main import app
from tests.fakes import FakeTrigger, fixture_sources
from tests.jwt_helpers import COMPANY_001, STUDENT_001, bearer, verifier

ADMIN = bearer("33333333-3333-4333-8333-000000000001", "admin")
SERVICE = {"X-Service-Token": "svc-token"}
URL = "/api/v1/matches/settings"


@pytest.fixture
def trigger() -> FakeTrigger:
    return FakeTrigger()


@pytest.fixture
def container(trigger: FakeTrigger) -> Container:
    profiles, jobs = fixture_sources()
    return build_container(
        MatchingSettings(service_token="svc-token"),  # noqa: S106 (valor ficticio)
        profiles=profiles,
        jobs=jobs,
        trigger=trigger,
        tokens=verifier(),
    )


@pytest.fixture
def client(container: Container) -> Iterator[TestClient]:
    app.dependency_overrides[get_container] = lambda: container
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_settings_domain_validation() -> None:
    with pytest.raises(InvalidInputError):
        RecommendationSettings(student_jobs_limit=0)
    with pytest.raises(InvalidInputError):
        RecommendationSettings(company_candidates_limit=21)
    with pytest.raises(InvalidInputError):
        RecommendationSettings(student_jobs_limit=True)
    assert RecommendationSettings.effective(None, 5) == 5
    assert RecommendationSettings.effective(3, 5) == 3
    assert RecommendationSettings.effective(50, 5) == 5  # nunca supera lo configurado
    with pytest.raises(InvalidInputError):
        RecommendationSettings.effective(0, 5)


def test_defaults_come_from_scoring_rules(client: TestClient) -> None:
    body = client.get(URL, headers=ADMIN).json()
    assert body["student_jobs_limit"] == 5
    assert body["company_candidates_limit"] == 10
    assert body["limits"] == {"min": 1, "max": 20}


def test_only_admin_can_change_settings(client: TestClient) -> None:
    for headers in (bearer(STUDENT_001, "student"), bearer(COMPANY_001, "company"), SERVICE):
        resp = client.patch(URL, json={"student_jobs_limit": 3}, headers=headers)
        assert resp.status_code == 403
    assert client.get(URL, headers=bearer(STUDENT_001, "student")).status_code == 403
    assert client.get(URL, headers=SERVICE).status_code == 200

    ok = client.patch(URL, json={"student_jobs_limit": 3}, headers=ADMIN)
    assert ok.status_code == 200
    body = ok.json()
    assert body["student_jobs_limit"] == 3
    assert body["company_candidates_limit"] == 10
    assert body["updated_by"] == "33333333-3333-4333-8333-000000000001"
    assert body["updated_at"]


@pytest.mark.parametrize(
    "payload",
    [{"student_jobs_limit": 0}, {"company_candidates_limit": 25}, {"otro": 1}, {}],
)
def test_invalid_settings_are_rejected(client: TestClient, payload: dict[str, int]) -> None:
    resp = client.patch(URL, json=payload, headers=ADMIN)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_INPUT"


def test_new_limits_apply_to_rankings_and_ai_requests(
    client: TestClient, trigger: FakeTrigger
) -> None:
    client.patch(URL, json={"student_jobs_limit": 1, "company_candidates_limit": 2}, headers=ADMIN)

    student = client.get(
        "/api/v1/matches/recommendations/students/stu-001", headers=bearer(STUDENT_001, "student")
    ).json()
    assert len(student["rule_based"]["items"]) == 1

    ranking = client.get(
        "/api/v1/matches/jobs/job-001/candidates?include_incompatible=true&limit=20",
        headers=SERVICE,
    ).json()
    assert len(ranking["items"]) == 2  # un limit mayor no supera lo configurado

    request = client.post(
        "/api/v1/matches/recommendations/requests",
        json={"mode": "company", "job_id": "job-001", "limit": 15},
        headers=bearer(COMPANY_001, "company"),
    )
    assert request.status_code == 202
    assert request.json()["limit"] == 2
    assert trigger.calls[-1]["limit"] == 2
