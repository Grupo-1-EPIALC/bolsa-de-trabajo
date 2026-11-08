"""UT-PROF-09: eventos de cuenta de auth-service (`contracts/auth.md` (parte B))."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.domain.account_events import AccountEvent
from app.domain.auth import SERVICE_PRINCIPAL, Principal, Role
from app.domain.company import CompanyLegal
from app.infrastructure.container import Container
from app.infrastructure.repositories.deleted_accounts import SqlAlchemyDeletedAccounts
from app.infrastructure.repositories.sqlalchemy_companies import (
    SqlAlchemyCompanyProfileRepository,
)
from app.infrastructure.repositories.sqlalchemy_repo import SqlAlchemyProfileRepository
from tests import jwt_helpers
from tests.conftest import COMPLETE_PROFILE, FAKE_JWT, service_headers, student_headers

EVENTS = "/api/v1/profiles/internal/account-events"
COMPANY = Principal(subject=jwt_helpers.COMPANY_001, role=Role.COMPANY, access_token=FAKE_JWT)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
WHEN = "2026-11-06T21:44:40.123Z"


def _when() -> datetime:
    return datetime(2026, 11, 6, 21, 44, tzinfo=UTC)


def event(user_id: str, kind: str = "account.deleted", **extra: Any) -> dict[str, Any]:
    return {
        "event": kind,
        "user_id": user_id,
        "role": extra.pop("role", "student"),
        "deleted": kind == "account.deleted",
        "email": "persona@example.test",
        "actor_id": jwt_helpers.ADMIN_001,
        "occurred_at": WHEN,
        **extra,
    }


def company_headers() -> dict[str, str]:
    return jwt_helpers.bearer(jwt_helpers.COMPANY_001, "company")


def test_ut_prof_09_solo_servicios_pueden_mandar_eventos(client: TestClient) -> None:
    body = event(jwt_helpers.STUDENT_NEW)
    assert client.post(EVENTS, json=body).status_code == 401
    assert client.post(EVENTS, json=body, headers=student_headers()).status_code == 403
    bad = client.post(EVENTS, json=body, headers={"X-Service-Token": "otro"})
    assert bad.status_code == 401


def test_ut_prof_09_borrado_archiva_el_perfil_y_corta_el_token(client: TestClient) -> None:
    created = client.post("/api/v1/profiles/me", json=COMPLETE_PROFILE, headers=student_headers())
    assert created.status_code == 201
    profile_id = created.json()["id"]
    pool = client.get("/api/v1/profiles", headers=service_headers()).json()
    assert profile_id in [p["id"] for p in pool["items"]]

    response = client.post(EVENTS, json=event(jwt_helpers.STUDENT_NEW), headers=service_headers())
    assert response.status_code == 200
    assert response.json()["result"] == "archived"

    pool = client.get("/api/v1/profiles", headers=service_headers()).json()
    assert profile_id not in [p["id"] for p in pool["items"]]
    by_id = client.get(f"/api/v1/profiles/{profile_id}", headers=service_headers())
    assert by_id.status_code == 404
    # El JWT todavía no venció, pero la cuenta ya no existe: ni ver ni volver a crear.
    for method in ("get", "post"):
        mine = client.request(method.upper(), "/api/v1/profiles/me", headers=student_headers())
        assert mine.status_code == 401
        assert mine.json()["error"]["code"] == "ACCOUNT_DELETED"


def test_ut_prof_09_evento_repetido_es_idempotente(client: TestClient) -> None:
    client.post("/api/v1/profiles/me", json=COMPLETE_PROFILE, headers=student_headers())
    body = event(jwt_helpers.STUDENT_NEW)
    first = client.post(EVENTS, json=body, headers=service_headers()).json()
    second = client.post(EVENTS, json=body, headers=service_headers()).json()
    assert (first["result"], second["result"]) == ("archived", "ignored")


def test_ut_prof_09_cuenta_sin_perfil_queda_registrada(client: TestClient) -> None:
    response = client.post(EVENTS, json=event(jwt_helpers.STUDENT_NEW), headers=service_headers())
    assert response.json()["result"] == "updated"
    created = client.post("/api/v1/profiles/me", json=COMPLETE_PROFILE, headers=student_headers())
    assert created.status_code == 401


def test_ut_prof_09_borrado_de_empresa_archiva_perfil_y_logo(container: Container) -> None:
    container.companies.create_mine(COMPANY)
    container.companies.upload_logo(COMPANY, PNG)
    result = container.account_events.handle(
        SERVICE_PRINCIPAL,
        AccountEvent(
            event="account.deleted",
            user_id=jwt_helpers.COMPANY_001,
            role="company",
            deleted=True,
            occurred_at=_when(),
        ),
    )
    assert result["result"] == "archived"
    assert container.company_repository.get_by_company(jwt_helpers.COMPANY_001) is None
    assert container.logos.get(jwt_helpers.COMPANY_001) is None
    listed = container.companies.list_profiles(SERVICE_PRINCIPAL)
    assert listed["total"] == 0


def test_ut_prof_09_edicion_actualiza_datos_legales_de_la_empresa(client: TestClient) -> None:
    assert (
        client.post("/api/v1/profiles/companies/me", json={}, headers=company_headers()).status_code
        == 201
    )
    company = {"legal_name": "Nueva Razón S.R.L.", "cuit": "30712345671", "activity": "Software"}
    body = event(jwt_helpers.COMPANY_001, "account.updated", role="company", company=company)
    response = client.post(EVENTS, json=body, headers=service_headers())
    assert response.json()["result"] == "updated"
    snapshot = client.get(
        f"/api/v1/profiles/companies/{jwt_helpers.COMPANY_001}", headers=service_headers()
    ).json()
    assert "Nueva Razón S.R.L." in str(snapshot)
    # Repetirlo no cambia nada.
    again = client.post(EVENTS, json=body, headers=service_headers()).json()
    assert again["result"] == "ignored"


def test_ut_prof_09_edicion_de_estudiante_y_evento_desconocido_se_ignoran(
    client: TestClient,
) -> None:
    client.post("/api/v1/profiles/me", json=COMPLETE_PROFILE, headers=student_headers())
    for kind in ("account.updated", "account.algo_nuevo"):
        body = event(jwt_helpers.STUDENT_NEW, kind)
        assert (
            client.post(EVENTS, json=body, headers=service_headers()).json()["result"] == "ignored"
        )
    assert client.get("/api/v1/profiles/me", headers=student_headers()).status_code == 200


def test_ut_prof_09_repositorios_sql_archivan_y_registran(
    tmp_path: Path, container: Container
) -> None:
    url = f"sqlite:///{tmp_path / 'acc.db'}"
    profiles = SqlAlchemyProfileRepository(url, schema=None)
    companies = SqlAlchemyCompanyProfileRepository(url, schema=None)
    deleted = SqlAlchemyDeletedAccounts(url, schema=None)
    try:
        student = Principal(jwt_helpers.STUDENT_NEW, Role.STUDENT, FAKE_JWT)
        container.profiles.create_mine(student, COMPLETE_PROFILE)
        profile = container.repository.get_by_user(jwt_helpers.STUDENT_NEW)
        assert profile is not None
        profiles.add(profile)
        container.companies.create_mine(COMPANY)
        company = container.company_repository.get_by_company(jwt_helpers.COMPANY_001)
        assert company is not None
        companies.add(company)

        assert profiles.archive(profile.id, _when()) is True
        assert profiles.archive(profile.id, _when()) is False
        assert profiles.get(profile.id) is None
        assert profiles.list(offset=0, limit=10)[1] == 0
        assert companies.archive(company.company_id, _when()) is True
        assert companies.get_by_company(company.company_id) is None

        assert deleted.mark(jwt_helpers.STUDENT_NEW, "student", _when()) is True
        assert deleted.mark(jwt_helpers.STUDENT_NEW, "student", _when()) is False
        assert deleted.contains(jwt_helpers.STUDENT_NEW)
        assert not deleted.contains(jwt_helpers.STUDENT_001)
    finally:
        profiles.dispose()
        companies.dispose()
        deleted.dispose()


def test_ut_prof_09_datos_legales_iguales_no_reescriben(container: Container) -> None:
    container.companies.create_mine(COMPANY)
    before = container.company_repository.get_by_company(jwt_helpers.COMPANY_001)
    assert before is not None
    result = container.account_events.handle(
        SERVICE_PRINCIPAL,
        AccountEvent(
            event="account.updated",
            user_id=jwt_helpers.COMPANY_001,
            role="company",
            deleted=False,
            occurred_at=_when(),
            company=CompanyLegal(before.legal.legal_name, before.legal.cuit, before.legal.activity),
        ),
    )
    assert result["result"] == "ignored"


def test_ut_prof_09_el_seed_no_resucita_perfiles_borrados(seeded: Container) -> None:
    from app.infrastructure.seed import seed_companies, seed_profiles

    pool = seeded.profiles.list_profiles(SERVICE_PRINCIPAL, include_all=True)["items"]
    profile = seeded.repository.get(pool[0]["id"])
    assert profile is not None
    company_id = seeded.company_repository.list(offset=0, limit=1)[0][0].company_id
    for user_id, role in ((profile.user_id, "student"), (company_id, "company")):
        seeded.account_events.handle(
            SERVICE_PRINCIPAL,
            AccountEvent("account.deleted", user_id, role, True, _when()),
        )

    is_deleted = seeded.deleted_accounts.contains
    assert seed_profiles(seeded.profiles, seeded.settings.seed_path, is_deleted=is_deleted) == 0
    assert seeded.repository.get(profile.id) is None
    companies_path = seeded.settings.companies_seed_path
    assert seed_companies(seeded.companies, companies_path, is_deleted=is_deleted) == 0
    assert seeded.company_repository.get_by_company(company_id) is None
    # Sin el filtro, el seed los volvería a cargar.
    assert seed_profiles(seeded.profiles, seeded.settings.seed_path) == 1
