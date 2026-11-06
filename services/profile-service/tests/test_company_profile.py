"""UT-PROF-08: perfil de empresa (datos legales de auth, completitud, logo, vistas y búsquedas)."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.domain.auth import SERVICE_PRINCIPAL, Principal, Role
from app.domain.company import detect_logo_type
from app.domain.errors import (
    CompanyProfileAlreadyExistsError,
    CompanyProfileNotFoundError,
    ForbiddenError,
    InvalidInputError,
    InvalidLogoError,
    LogoNotFoundError,
)
from app.infrastructure.container import Container
from tests import jwt_helpers
from tests.conftest import FAKE_JWT, service_headers

COMPANY = Principal(subject=jwt_helpers.COMPANY_001, role=Role.COMPANY, access_token=FAKE_JWT)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 32
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'

COMPLETE: dict[str, Any] = {
    "display_name": "PampaTech",
    "tagline": "Software a medida desde Buenos Aires",
    "description": "Desarrollamos productos digitales y formamos talento joven.",
    "industry": "software",
    "size": "51-200",
    "location": {"country": "AR", "province": "CABA", "city": "Buenos Aires"},
    "website": "https://pampatech.example.com",
    "links": [{"type": "linkedin", "url": "https://linkedin.com/company/pampatech-ficticia"}],
    "contact": {"email": "rrhh@pampatech.example.com", "phone": "+54 11 4000-0000"},
    "work_modalities": ["hybrid", "remote"],
    "benefits": ["prepaga", "días de estudio"],
    "hiring": {"areas": ["desarrollo backend"], "internship_program": True},
}


def test_ut_prof_08_detecta_formato_real_del_logo() -> None:
    assert detect_logo_type(PNG) == "image/png"
    assert detect_logo_type(JPEG) == "image/jpeg"
    assert detect_logo_type(WEBP) == "image/webp"
    assert detect_logo_type(SVG) is None
    assert detect_logo_type(b"GIF89a....") is None
    assert detect_logo_type(b"XXXX\x00\x00\x00\x00WEBP") is None


def test_ut_prof_08_alta_precargada_desde_auth(container: Container) -> None:
    svc = container.companies
    with pytest.raises(CompanyProfileNotFoundError):
        svc.get_mine(COMPANY)
    body = svc.create_mine(COMPANY)
    assert body["company_id"] == jwt_helpers.COMPANY_001
    assert body["legal"] == {
        "legal_name": "Empresa Ficticia S.A.",
        "cuit": "30000000007",
        "activity": "software",
    }
    assert body["name"] == body["display_name"] == "Empresa Ficticia S.A."
    assert body["industry"] == "software"
    assert body["contact"]["email"] == "cuenta@example.com"
    assert body["status"] == "draft"
    missing = {m["field"] for m in body["completion"]["missing"] if m["required"]}
    assert missing == {"location", "description", "size"}
    assert "active_searches" not in body  # las búsquedas son de jobs-service
    with pytest.raises(CompanyProfileAlreadyExistsError):
        svc.create_mine(COMPANY)


def test_ut_prof_08_solo_empresas(container: Container) -> None:
    student = Principal("s1", Role.STUDENT)
    with pytest.raises(ForbiddenError):
        container.companies.create_mine(student)
    with pytest.raises(ForbiddenError):
        container.companies.get_mine(SERVICE_PRINCIPAL)


def test_ut_prof_08_completar_y_validar(container: Container) -> None:
    container.companies.create_mine(COMPANY)
    body = container.companies.update_mine(COMPANY, copy.deepcopy(COMPLETE))
    assert body["status"] == "complete" and body["version"] == 2
    assert body["name"] == "PampaTech"
    assert body["legal"]["legal_name"] == "Empresa Ficticia S.A."  # la razón social no cambia
    recommended = {m["field"] for m in body["completion"]["missing"]}
    assert recommended == {"logo"}
    for bad in ({"legal": {"cuit": "1"}}, {"size": "enorme"}, {"tagline": "COMPLETAR_MANUALMENTE"}):
        with pytest.raises(InvalidInputError):
            container.companies.update_mine(COMPANY, bad)


def test_ut_prof_08_logo(container: Container) -> None:
    svc = container.companies
    svc.create_mine(COMPANY, copy.deepcopy(COMPLETE))
    body = svc.upload_logo(COMPANY, PNG)
    assert body["logo"]["mime_type"] == "image/png"
    assert body["logo_url"].startswith(
        f"/api/v1/profiles/companies/{jwt_helpers.COMPANY_001}/logo?v="
    )
    assert body["completion"]["percent"] == 100
    assert svc.get_logo(jwt_helpers.COMPANY_001).content == PNG
    for content in (SVG, b"", b"\x89PNG\r\n\x1a\n" + b"x" * (1024 * 1024)):
        with pytest.raises(InvalidLogoError):
            svc.upload_logo(COMPANY, content)
    svc.delete_logo(COMPANY)
    with pytest.raises(LogoNotFoundError):
        svc.get_logo(jwt_helpers.COMPANY_001)
    with pytest.raises(LogoNotFoundError):
        svc.delete_logo(COMPANY)


def test_ut_prof_08_vistas(container: Container) -> None:
    svc = container.companies
    svc.create_mine(COMPANY, copy.deepcopy(COMPLETE))
    svc.upload_logo(COMPANY, JPEG)
    student = Principal("s1", Role.STUDENT)

    public = svc.get_profile(student, jwt_helpers.COMPANY_001)
    assert public["name"] == "PampaTech" and public["legal_name"] == "Empresa Ficticia S.A."
    assert "legal" not in public and "cuit" not in json.dumps(public)
    assert "contact" not in public  # contact.public = false
    assert public["logo_url"] and "active_searches" not in public

    svc.update_mine(COMPANY, {"contact": {"email": "rrhh@pampatech.example.com", "public": True}})
    assert svc.get_profile(student, jwt_helpers.COMPANY_001)["contact"] == {
        "email": "rrhh@pampatech.example.com"
    }

    service = svc.get_profile(SERVICE_PRINCIPAL, jwt_helpers.COMPANY_001)
    assert service["snapshot"]["name"] == "PampaTech"
    assert service["snapshot"]["size"] == "51-200"
    assert service["snapshot"]["logo_url"].endswith(service["logo_url"].split("/logo")[1])
    assert service["legal"]["cuit"] == "30000000007"

    admin = svc.get_profile(Principal("a1", Role.ADMIN), jwt_helpers.COMPANY_001)
    assert "completion" in admin

    svc.update_mine(COMPANY, {"visibility": "hidden"})
    with pytest.raises(CompanyProfileNotFoundError):
        svc.get_profile(student, jwt_helpers.COMPANY_001)
    assert svc.get_profile(SERVICE_PRINCIPAL, jwt_helpers.COMPANY_001)["visibility"] == "hidden"
    with pytest.raises(CompanyProfileNotFoundError):
        svc.get_profile(student, "no-existe")


def test_ut_prof_08_seed_y_listado(seeded: Container) -> None:
    listing = seeded.companies.list_profiles(SERVICE_PRINCIPAL, limit=50)
    assert listing["total"] == 10
    first = listing["items"][0]
    assert first["company_id"] == jwt_helpers.COMPANY_001
    assert first["snapshot"]["name"] == "PampaTech S.A." and first["status"] == "complete"
    with pytest.raises(ForbiddenError):
        seeded.companies.list_profiles(Principal("s1", Role.STUDENT))
    from app.infrastructure.seed import seed_companies

    assert seed_companies(seeded.companies, seeded.settings.companies_seed_path) == 0
    assert seed_companies(seeded.companies, "/no/existe.json") == 0


def test_ut_prof_08_api(client: TestClient) -> None:
    h = jwt_helpers.bearer(jwt_helpers.COMPANY_001, "company")
    base = "/api/v1/profiles/companies"
    missing = client.get(f"{base}/me", headers=h)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "COMPANY_PROFILE_NOT_FOUND"
    created = client.post(f"{base}/me", headers=h, json=COMPLETE)
    assert created.status_code == 201 and created.json()["status"] == "complete"
    bad = client.patch(f"{base}/me", headers=h, json={"cuit": "30000000007"})
    assert bad.status_code == 422

    up = client.put(f"{base}/me/logo", headers=h, files={"file": ("logo.png", PNG, "image/png")})
    assert up.status_code == 200, up.text
    fake = client.put(f"{base}/me/logo", headers=h, files={"file": ("logo.png", SVG, "image/png")})
    assert fake.status_code == 422 and fake.json()["error"]["code"] == "INVALID_LOGO"
    huge = client.put(
        f"{base}/me/logo",
        headers=h,
        files={"file": ("l.png", PNG + b"x" * 1024 * 1024, "image/png")},
    )
    assert huge.status_code == 422

    logo = client.get(f"{base}/{jwt_helpers.COMPANY_001}/logo")  # sin token: es público
    assert logo.status_code == 200 and logo.content == PNG
    assert logo.headers["content-type"] == "image/png"
    assert logo.headers["x-content-type-options"] == "nosniff"
    assert client.get(f"{base}/otra/logo").status_code == 404

    student = jwt_helpers.bearer(jwt_helpers.STUDENT_001, "student")
    public = client.get(f"{base}/{jwt_helpers.COMPANY_001}", headers=student)
    assert public.status_code == 200 and public.json()["name"] == "PampaTech"
    assert client.get(f"{base}/{jwt_helpers.COMPANY_001}").status_code == 401
    assert client.get(f"{base}/me", headers=student).status_code == 403
    assert client.get(base, headers=service_headers()).json()["total"] == 1
    assert client.get(base, headers=student).status_code == 403
    assert client.delete(f"{base}/me/logo", headers=h).status_code == 204


def test_repositorios_sql_de_empresa(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from app.domain.company import CompanyProfile
    from app.domain.ports import StoredLogo
    from app.infrastructure.repositories.sqlalchemy_companies import (
        SqlAlchemyCompanyProfileRepository,
        SqlAlchemyLogoStore,
    )

    url = f"sqlite:///{tmp_path / 'c.db'}"
    repo = SqlAlchemyCompanyProfileRepository(url, schema=None)
    logos = SqlAlchemyLogoStore(url, schema=None)
    now = datetime(2026, 11, 6, tzinfo=UTC)
    profile = CompanyProfile(id="comp-1", company_id="c1", created_at=now, updated_at=now)
    repo.add(profile)
    assert repo.get_by_company("c1") == profile and repo.get_by_company("x") is None
    import dataclasses

    repo.update(dataclasses.replace(profile, display_name="Nueva", version=2))
    items, total = repo.list(offset=0, limit=10)
    assert total == 1 and items[0].display_name == "Nueva"
    logos.save("c1", StoredLogo("image/png", PNG))
    logos.save("c1", StoredLogo("image/jpeg", JPEG))
    assert logos.get("c1") == StoredLogo("image/jpeg", JPEG)
    logos.delete("c1")
    assert logos.get("c1") is None
    repo.dispose()
    logos.dispose()
