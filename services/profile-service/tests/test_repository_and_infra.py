"""Repositorio SQLAlchemy (SQLite en archivo), JWT y adaptadores HTTP."""

import copy
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.domain.auth import Principal, Role
from app.domain.errors import UnauthorizedError
from app.domain.profile import StudentProfile
from app.infrastructure.account_directory import HttpAccountDirectory
from app.infrastructure.events_n8n import HttpN8nProfileEventPublisher
from app.infrastructure.repositories.sqlalchemy_repo import (
    SqlAlchemyProfileRepository,
    normalize_database_url,
)
from tests import jwt_helpers

NOW = datetime(2026, 11, 5, tzinfo=UTC)


@pytest.fixture
def repo(tmp_path: Path) -> Iterator[SqlAlchemyProfileRepository]:
    repository = SqlAlchemyProfileRepository(f"sqlite:///{tmp_path / 'p.db'}", schema=None)
    yield repository
    repository.dispose()


def test_repositorio_sqlalchemy_crud(repo: SqlAlchemyProfileRepository) -> None:
    import dataclasses

    profile = StudentProfile(id="p1", user_id="u1", created_at=NOW, updated_at=NOW)
    repo.add(profile)
    repo.add(StudentProfile(id="p2", user_id="u2", created_at=NOW, updated_at=NOW))
    assert repo.get("p1") == profile
    assert repo.get_by_user("u2") is not None and repo.get("nada") is None
    repo.update(dataclasses.replace(profile, summary="nuevo", version=2))
    assert repo.get("p1").summary == "nuevo"  # type: ignore[union-attr]
    items, total = repo.list(offset=1, limit=5)
    assert total == 2 == repo.count() and [p.id for p in items] == ["p2"]


def test_normaliza_url_de_postgres() -> None:
    assert normalize_database_url("postgresql://u:p@h/db").startswith("postgresql+psycopg://")
    assert normalize_database_url("postgres://u:p@h/db").startswith("postgresql+psycopg://")
    assert normalize_database_url("sqlite:///x.db") == "sqlite:///x.db"


def test_jwt_valido_y_rechazos() -> None:
    verifier = jwt_helpers.verifier()
    principal = verifier.verify(jwt_helpers.make_token("u1", "student"))
    assert principal.role is Role.STUDENT and principal.access_token
    for token in (
        jwt_helpers.make_token("u1", "student", other_key=True),
        jwt_helpers.make_token("u1", "superuser"),
        jwt_helpers.make_token("u1", "student", extra={"exp": 1}),
        jwt_helpers.make_token("u1", "student", extra={"aud": "otra-api"}),
    ):
        with pytest.raises(UnauthorizedError):
            verifier.verify(token)


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


def test_directorio_de_cuentas(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: int) -> _FakeResponse:
        seen["auth"] = request.headers["Authorization"]
        seen["url"] = request.full_url
        return _FakeResponse(json.dumps({"email": "cuenta@example.com"}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    accounts = HttpAccountDirectory("http://auth-service:3000/")
    student = Principal("u1", Role.STUDENT, access_token="abc")  # noqa: S106
    assert accounts.email_of(student) == "cuenta@example.com"
    assert seen == {"auth": "Bearer abc", "url": "http://auth-service:3000/api/v1/auth/me"}
    assert accounts.email_of(Principal("u1", Role.STUDENT)) is None
    with pytest.raises(ValueError):
        HttpAccountDirectory("ftp://x")


def test_publicador_de_eventos(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: int) -> _FakeResponse:
        sent["url"] = request.full_url
        sent["token"] = request.headers.get("X-service-token")
        sent["body"] = json.loads(request.data)
        return _FakeResponse(b"{}")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    publisher = HttpN8nProfileEventPublisher("http://n8n:5678/webhook/", "svc")
    publisher.profile_updated(StudentProfile(id="p1", user_id="u1", created_at=NOW, updated_at=NOW))
    assert sent["url"] == "http://n8n:5678/webhook/profile-updated"
    assert sent["token"] == "svc"  # noqa: S105
    assert sent["body"]["event"] == "profile.updated" and sent["body"]["searchable"] is False
    assert "email" not in sent["body"]
    with pytest.raises(ValueError):
        HttpN8nProfileEventPublisher("file:///x", "svc")


def test_seed_no_tiene_marcadores_ni_datos_reales() -> None:
    from app.infrastructure.config import ProfileSettings

    seed = json.loads(Path(ProfileSettings().seed_path).read_text(encoding="utf-8"))
    raw = json.dumps(seed, ensure_ascii=False)
    assert "COMPLETAR_MANUALMENTE" not in raw
    assert all(p["personal"]["email"].endswith("@example.com") for p in copy.deepcopy(seed))


def test_directorio_lee_datos_legales_de_empresa(monkeypatch: pytest.MonkeyPatch) -> None:
    payloads = [
        {
            "id": "c1",
            "email": "rrhh@example.com",
            "role": "company",
            "company": {
                "legal_name": "Ficticia S.A.",
                "cuit": "30000000007",
                "activity": "software",
            },
        },
        {"id": "s1", "email": "s@example.com", "role": "student"},
    ]

    def fake_urlopen(request: Any, timeout: int) -> _FakeResponse:
        return _FakeResponse(json.dumps(payloads.pop(0)).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    accounts = HttpAccountDirectory("http://auth-service:3000")
    company = Principal("c1", Role.COMPANY, access_token="abc")  # noqa: S106
    legal = accounts.company_of(company)
    assert legal is not None and legal.cuit == "30000000007"
    assert accounts.company_of(company) is None  # alumno: sin bloque company
