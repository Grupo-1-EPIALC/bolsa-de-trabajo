"""Consulta del perfil de la empresa en auth-service (`GET /api/v1/auth/me`)."""

import json
import urllib.error
import urllib.request
from typing import Any

from app.domain.errors import UpstreamError
from app.domain.models import CompanySnapshot


class HttpCompanyDirectory:
    def __init__(self, base_url: str, timeout_seconds: int = 10) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def snapshot_for(self, access_token: str) -> CompanySnapshot:
        url = f"{self._base_url}/api/v1/auth/me"
        request = urllib.request.Request(  # noqa: S310 - URL interna validada
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            preview = exc.read().decode("utf-8", errors="replace")[:300]
            raise UpstreamError(
                "auth-service rechazó la consulta del perfil de la empresa",
                {"status": exc.code, "body": preview},
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise UpstreamError("No se pudo consultar auth-service") from exc

        try:
            data = json.loads(raw)
        except ValueError as exc:
            raise UpstreamError("auth-service devolvió una respuesta inválida") from exc
        if not isinstance(data, dict):
            raise UpstreamError("auth-service devolvió una respuesta inválida")
        company = data.get("company")
        if not isinstance(company, dict) or not company.get("legal_name"):
            raise UpstreamError(
                "El usuario autenticado no tiene un perfil de empresa",
                {"user_id": data.get("id")},
            )
        return CompanySnapshot(
            name=str(company["legal_name"]),
            industry=_optional_text(company.get("activity")),
            size=None,
            logo_url=None,
        )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
