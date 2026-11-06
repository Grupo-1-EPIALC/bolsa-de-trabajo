"""Lee la cuenta en auth-service (`GET /api/v1/auth/me` con el Bearer del usuario).

El JWT sólo trae `sub` y `role`. De `/me` se toman el email (para precargar perfiles) y,
en las empresas, `company.legal_name`, `company.cuit` y `company.activity`.
"""

import json
import urllib.error
import urllib.request
from typing import Any

from app.domain.auth import Principal
from app.domain.company import CompanyLegal


class HttpAccountDirectory:
    def __init__(self, auth_service_url: str, timeout_seconds: int = 5) -> None:
        if not auth_service_url.startswith(("http://", "https://")):
            raise ValueError(f"AUTH_SERVICE_URL inválida: {auth_service_url!r}")
        self._url = auth_service_url.rstrip("/") + "/api/v1/auth/me"
        self._timeout = timeout_seconds

    def email_of(self, principal: Principal) -> str | None:
        email = self._me(principal).get("email")
        return str(email) if email else None

    def company_of(self, principal: Principal) -> CompanyLegal | None:
        company = self._me(principal).get("company")
        if not isinstance(company, dict) or not company.get("legal_name"):
            return None
        return CompanyLegal(
            legal_name=str(company.get("legal_name") or ""),
            cuit=str(company.get("cuit") or ""),
            activity=str(company.get("activity") or ""),
        )

    def _me(self, principal: Principal) -> dict[str, Any]:
        if not principal.access_token:
            return {}
        request = urllib.request.Request(  # noqa: S310 - URL interna validada
            self._url,
            headers={
                "Authorization": f"Bearer {principal.access_token}",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as resp:  # noqa: S310
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}
