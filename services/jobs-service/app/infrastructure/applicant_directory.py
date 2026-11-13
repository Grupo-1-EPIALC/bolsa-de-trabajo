"""Contacto del estudiante que se postula: `GET /api/v1/profiles/me` en profile-service.

Se consulta con el Bearer del propio estudiante (como `HttpCompanyDirectory` con auth-service):
jobs-service nunca lee la base de profile-service (AGENTS.md §2.1.4).
"""

import json
import urllib.error
import urllib.request
from typing import Any

from app.domain.applications import ApplicantContact, ApplicantSnapshot
from app.domain.errors import ProfileRequiredError, UpstreamError

_PLACEHOLDER = "COMPLETAR_MANUALMENTE"
_PROFILE_MISSING = (
    "Completá tu perfil (nombre y email) antes de postularte: es lo que ve la empresa"
)


class HttpApplicantDirectory:
    def __init__(self, base_url: str, timeout_seconds: int = 10) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def applicant_for(self, access_token: str) -> ApplicantSnapshot:
        request = urllib.request.Request(  # noqa: S310 - URL interna validada
            f"{self._base_url}/api/v1/profiles/me",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise ProfileRequiredError(_PROFILE_MISSING) from exc
            preview = exc.read().decode("utf-8", errors="replace")[:300]
            raise UpstreamError(
                "profile-service rechazó la consulta del perfil del estudiante",
                {"status": exc.code, "body": preview},
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise UpstreamError("No se pudo consultar profile-service") from exc

        try:
            data = json.loads(raw)
        except ValueError as exc:
            raise UpstreamError("profile-service devolvió una respuesta inválida") from exc
        if not isinstance(data, dict):
            raise UpstreamError("profile-service devolvió una respuesta inválida")
        return applicant_from_profile(data)


def applicant_from_profile(data: dict[str, Any]) -> ApplicantSnapshot:
    """Arma la copia que ve la empresa desde la `ProfileView` (contracts/profile.md, A §4)."""
    personal = data.get("personal")
    personal = personal if isinstance(personal, dict) else {}
    name = _text(personal.get("name"))
    email = _text(personal.get("email"))
    profile_id = _text(data.get("id"))
    if not (name and email and profile_id):
        raise ProfileRequiredError(_PROFILE_MISSING)
    return ApplicantSnapshot(
        profile_id=profile_id,
        headline=_text(data.get("headline")),
        contact=ApplicantContact(name=name, email=email, phone=_text(personal.get("phone"))),
    )


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text and text != _PLACEHOLDER else None
