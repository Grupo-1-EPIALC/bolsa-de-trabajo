"""Endpoints REST: formato de errores y contratos de respuesta (acceso como servicio)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_container
from app.infrastructure.config import MatchingSettings
from app.infrastructure.container import build_container
from app.main import app
from tests.fakes import FakeTrigger, ai_batch, fixture_sources
from tests.jwt_helpers import verifier

TOKEN = "token-de-prueba"  # noqa: S105 (valor ficticio de test)
HEADERS = {"X-Service-Token": TOKEN}


@pytest.fixture
def client() -> Iterator[TestClient]:
    profiles, jobs = fixture_sources()
    container = build_container(
        MatchingSettings(service_token=TOKEN, use_mocks=True),
        profiles=profiles,
        jobs=jobs,
        trigger=FakeTrigger(),
        tokens=verifier(),
    )
    app.dependency_overrides[get_container] = lambda: container
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_is_public(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"


def test_requires_credentials(client: TestClient) -> None:
    resp = client.post("/api/v1/matches", json={"profile_id": "stu-001", "job_id": "job-001"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"
    wrong = client.post(
        "/api/v1/matches",
        json={"profile_id": "stu-001", "job_id": "job-001"},
        headers={"X-Service-Token": "otro"},
    )
    assert wrong.status_code == 401


def test_service_token_is_not_accepted_as_bearer(client: TestClient) -> None:
    # El gateway borra X-Service-Token de afuera; el token interno no puede entrar por Bearer.
    resp = client.post(
        "/api/v1/matches",
        json={"profile_id": "stu-001", "job_id": "job-001"},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert resp.status_code == 401


def test_compute_match_contract(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/matches", json={"profile_id": "stu-001", "job_id": "job-001"}, headers=HEADERS
    )
    body = resp.json()
    assert body["origin"] == "RULES"
    assert body["engine_version"]
    assert 0 <= body["score"] <= 100
    assert {c["criterion"] for c in body["breakdown"]} >= {"required_skills", "languages"}
    assert "compatible" in body["conditions_fit"]
    assert body["conditions_fit"]["salary_fit"]["result"] == "match"


def test_missing_skills_endpoint(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/matches/missing-skills",
        json={"profile_id": "stu-001", "job_id": "job-001"},
        headers=HEADERS,
    )
    items = resp.json()["items"]
    assert resp.status_code == 200
    assert items[0]["skill"] == "Docker"
    assert {"skill", "kind", "required_level", "current_level", "gap", "priority"} <= set(items[0])


def test_rankings(client: TestClient) -> None:
    jobs = client.get("/api/v1/matches/students/stu-001/jobs?limit=5", headers=HEADERS).json()
    cands = client.get(
        "/api/v1/matches/jobs/job-001/candidates?include_incompatible=true", headers=HEADERS
    ).json()
    assert jobs["origin"] == "RULES"
    assert jobs["items"][0]["rank"] == 1
    assert "job" in jobs["items"][0] and "match" in jobs["items"][0]
    assert len(cands["items"]) == 3


def test_not_found_and_validation_errors(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/matches", json={"profile_id": "stu-999", "job_id": "job-001"}, headers=HEADERS
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"
    bad = client.post("/api/v1/matches", json={"profile_id": ""}, headers=HEADERS)
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "INVALID_INPUT"


def test_recommendation_endpoints(client: TestClient) -> None:
    single = client.post(
        "/api/v1/matches/recommendations",
        json={
            "profile_id": "stu-001",
            "job_id": "job-001",
            "items": [],
            "origin": "AI",
            "model": "m",
            "prompt_version": "1.0.0",
            "generated_at": "2026-11-04T00:00:00Z",
            "disclaimer": "d",
        },
        headers=HEADERS,
    )
    assert single.status_code == 201
    assert single.json()["origin"] == "AI"

    req = client.post(
        "/api/v1/matches/recommendations/requests",
        json={"mode": "company", "job_id": "job-001", "limit": 3},
        headers=HEADERS,
    )
    assert req.status_code == 202
    request_id = req.json()["request_id"]

    batch = client.post(
        "/api/v1/matches/recommendations/batch",
        json=ai_batch(
            "company", "job-001", [{"profile_id": "stu-001", "justification": "x"}], request_id
        ),
        headers=HEADERS,
    )
    assert batch.status_code == 201
    assert batch.json()["saved"] == 1

    status = client.get(f"/api/v1/matches/recommendations/requests/{request_id}", headers=HEADERS)
    assert status.json()["status"] == "completed"

    view = client.get("/api/v1/matches/recommendations/jobs/job-001", headers=HEADERS).json()
    assert view["rule_based"]["origin"] == "RULES"
    assert view["ai_recommendations"]["origin"] == "AI"
    assert view["ai_recommendations"]["items"][0]["profile_id"] == "stu-001"

    student = client.get("/api/v1/matches/recommendations/students/stu-001", headers=HEADERS).json()
    assert student["ai_recommendations"]["status"] in {"ready", "not_requested"}


def test_unknown_route_and_method_use_common_error_format(client: TestClient) -> None:
    missing = client.get("/api/v1/matches/no-existe/ruta", headers=HEADERS)
    wrong_method = client.delete("/api/v1/matches", headers=HEADERS)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"
    assert wrong_method.status_code == 405
    assert wrong_method.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
