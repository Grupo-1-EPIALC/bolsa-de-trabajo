"""JWT de auth-service y acceso por rol/dueño en los endpoints del frontend."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_container
from app.domain.auth import Role
from app.domain.errors import UnauthorizedError
from app.infrastructure.config import MatchingSettings
from app.infrastructure.container import build_container
from app.main import app
from tests.fakes import FakeTrigger, fixture_sources
from tests.jwt_helpers import (
    COMPANY_001,
    COMPANY_002,
    STUDENT_001,
    STUDENT_002,
    bearer,
    make_token,
    verifier,
)

SERVICE = {"X-Service-Token": "svc-token"}


@pytest.fixture
def client() -> Iterator[TestClient]:
    profiles, jobs = fixture_sources()
    container = build_container(
        MatchingSettings(service_token="svc-token"),  # noqa: S106 (valor ficticio)
        profiles=profiles,
        jobs=jobs,
        trigger=FakeTrigger(),
        tokens=verifier(),
    )
    app.dependency_overrides[get_container] = lambda: container
    yield TestClient(app)
    app.dependency_overrides.clear()


# ------------------------------------------------------------ verificador ---


def test_verifier_accepts_auth_service_token() -> None:
    principal = verifier().verify(make_token(STUDENT_001, "student"))
    assert principal.subject == STUDENT_001
    assert principal.role is Role.STUDENT


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": 1},  # expirado
        {"aud": "otra-api"},
        {"iss": "otro-emisor"},
        {"role": "superuser"},
        {"role": "service"},  # nadie puede hacerse pasar por servicio con un JWT
    ],
)
def test_verifier_rejects_invalid_claims(claims: dict[str, object]) -> None:
    with pytest.raises(UnauthorizedError):
        verifier().verify(make_token(STUDENT_001, "student", extra=claims))


def test_verifier_rejects_wrong_signature_and_garbage() -> None:
    with pytest.raises(UnauthorizedError):
        verifier().verify(make_token(STUDENT_001, "student", other_key=True))
    with pytest.raises(UnauthorizedError):
        verifier().verify("no-es-un-jwt")


# --------------------------------------------------------- vista estudiante ---


def test_student_sees_only_own_recommendations(client: TestClient) -> None:
    own = client.get(
        "/api/v1/matches/recommendations/students/stu-001", headers=bearer(STUDENT_001, "student")
    )
    other = client.get(
        "/api/v1/matches/recommendations/students/stu-002", headers=bearer(STUDENT_001, "student")
    )
    as_company = client.get(
        "/api/v1/matches/recommendations/students/stu-001", headers=bearer(COMPANY_001, "company")
    )
    assert own.status_code == 200
    assert own.json()["profile_id"] == "stu-001"
    assert other.status_code == 404  # no revela que el perfil existe
    assert as_company.status_code == 403


def test_company_sees_only_own_jobs(client: TestClient) -> None:
    own = client.get(
        "/api/v1/matches/recommendations/jobs/job-001", headers=bearer(COMPANY_001, "company")
    )
    other = client.get(
        "/api/v1/matches/recommendations/jobs/job-002", headers=bearer(COMPANY_001, "company")
    )
    as_student = client.get(
        "/api/v1/matches/recommendations/jobs/job-001", headers=bearer(STUDENT_001, "student")
    )
    assert own.status_code == 200
    assert other.status_code == 404
    assert as_student.status_code == 403


def test_admin_and_service_see_everything(client: TestClient) -> None:
    admin = bearer("33333333-3333-4333-8333-000000000001", "admin")
    for headers in (admin, SERVICE):
        assert (
            client.get("/api/v1/matches/recommendations/jobs/job-002", headers=headers).status_code
            == 200
        )
        assert (
            client.get(
                "/api/v1/matches/recommendations/students/stu-002", headers=headers
            ).status_code
            == 200
        )


# ---------------------------------------------------------- endpoints internos ---


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/v1/matches/students/stu-001/jobs", None),
        ("GET", "/api/v1/matches/jobs/job-001/candidates", None),
        ("POST", "/api/v1/matches/missing-skills", {"profile_id": "stu-001", "job_id": "job-001"}),
        ("POST", "/api/v1/matches/recommendations/batch", {"mode": "student", "subject_id": "x"}),
        ("POST", "/api/v1/matches/recommendations", {"profile_id": "stu-001", "job_id": "job-001"}),
    ],
)
def test_internal_endpoints_reject_users(
    client: TestClient, method: str, path: str, body: dict[str, str] | None
) -> None:
    resp = client.request(method, path, json=body, headers=bearer(STUDENT_001, "student"))
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


# -------------------------------------------------------- match y pedidos ---


def test_match_visibility_by_role(client: TestClient) -> None:
    body = {"profile_id": "stu-001", "job_id": "job-001"}
    assert (
        client.post(
            "/api/v1/matches", json=body, headers=bearer(STUDENT_001, "student")
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/matches", json=body, headers=bearer(COMPANY_001, "company")
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/matches", json=body, headers=bearer(STUDENT_002, "student")
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/matches", json=body, headers=bearer(COMPANY_002, "company")
        ).status_code
        == 404
    )


def test_company_hides_hidden_student_salary_in_match(client: TestClient) -> None:
    # stu-002 ocultó su pretensión salarial; job-002 es de COMPANY_002
    resp = client.post(
        "/api/v1/matches",
        json={"profile_id": "stu-002", "job_id": "job-002"},
        headers=bearer(COMPANY_002, "company"),
    )
    fit = resp.json()["conditions_fit"]["salary_fit"]
    assert fit is None or fit["expected_monthly"] is None


def test_analysis_request_ownership(client: TestClient) -> None:
    company = bearer(COMPANY_001, "company")
    created = client.post(
        "/api/v1/matches/recommendations/requests",
        json={"mode": "company", "job_id": "job-001"},
        headers=company,
    )
    assert created.status_code == 202
    request_id = created.json()["request_id"]

    path = f"/api/v1/matches/recommendations/requests/{request_id}"
    assert client.get(path, headers=company).status_code == 200
    assert client.get(path, headers=bearer(COMPANY_002, "company")).status_code == 404

    foreign = client.post(
        "/api/v1/matches/recommendations/requests",
        json={"mode": "company", "job_id": "job-002"},
        headers=company,
    )
    assert foreign.status_code == 404
    missing_subject = client.post(
        "/api/v1/matches/recommendations/requests", json={"mode": "student"}, headers=company
    )
    assert missing_subject.status_code == 422


# ------------------------------------------------------------- JWKS real ---


def test_jwks_resolver_reads_auth_service_format() -> None:
    """Mismo formato que `GET /api/v1/auth/.well-known/jwks.json` de auth-service."""
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    from jwt.algorithms import RSAAlgorithm

    from app.infrastructure.jwt_verifier import JwksKeyResolver, JwtTokenVerifier
    from tests.jwt_helpers import AUDIENCE, ISSUER, KID, public_key

    jwk = json.loads(RSAAlgorithm.to_jwk(public_key()))
    body = json.dumps({"keys": [{**jwk, "kid": KID, "use": "sig", "alg": "RS256"}]}).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/v1/auth/.well-known/jwks.json"
        real = JwtTokenVerifier(JwksKeyResolver(url), ISSUER, AUDIENCE)
        assert real.verify(make_token(COMPANY_001, "company")).subject == COMPANY_001
        with pytest.raises(UnauthorizedError):
            real.verify(make_token(COMPANY_001, "company", other_key=True))
    finally:
        server.shutdown()
