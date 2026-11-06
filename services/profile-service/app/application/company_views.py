"""Qué ve cada quien del perfil de empresa.

- owner (la empresa) y admin: todo, más completitud.
- public (estudiantes y otras empresas): sin CUIT ni datos internos; contacto sólo si
  `contact.public = true`.
- service (jobs-service, matching, n8n): todo más `snapshot`, con la forma de
  `company_snapshot` de jobs-service.
"""

from typing import Any

from app.application.views import completion_to_dict
from app.domain.company import CompanyProfile
from app.domain.completion import Completion
from app.domain.serialization import drop_none, to_plain

LOGO_PATH = "/api/v1/profiles/companies/{company_id}/logo"


def logo_url(profile: CompanyProfile) -> str | None:
    if profile.logo is None:
        return None
    stamp = int(profile.logo.uploaded_at.timestamp())
    return LOGO_PATH.format(company_id=profile.company_id) + f"?v={stamp}"


def snapshot(profile: CompanyProfile) -> dict[str, Any]:
    """Forma de `company_snapshot` en jobs-service."""
    body = {
        "name": profile.name,
        "industry": profile.industry,
        "size": profile.size.value if profile.size else None,
        "logo_url": logo_url(profile),
    }
    result: dict[str, Any] = drop_none(body)
    return result


def _base(profile: CompanyProfile) -> dict[str, Any]:
    body: dict[str, Any] = drop_none(to_plain(profile))
    body["name"] = profile.name
    url = logo_url(profile)
    if url:
        body["logo_url"] = url
    return body


def owner_view(profile: CompanyProfile, completion: Completion) -> dict[str, Any]:
    body = _base(profile)
    body["completion"] = completion_to_dict(completion)
    return body


def service_view(profile: CompanyProfile) -> dict[str, Any]:
    body = _base(profile)
    body["snapshot"] = snapshot(profile)
    return body


def public_view(profile: CompanyProfile) -> dict[str, Any]:
    body = _base(profile)
    for key in ("version", "created_at", "status", "visibility", "logo"):
        body.pop(key, None)
    legal = body.pop("legal", {})
    if legal.get("legal_name"):
        body["legal_name"] = legal["legal_name"]  # la razón social es pública; el CUIT no
    if not profile.contact.public:
        body.pop("contact", None)
    else:
        body["contact"].pop("public", None)
    return body
