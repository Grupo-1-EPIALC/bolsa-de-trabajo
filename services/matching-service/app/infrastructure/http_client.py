"""Cliente HTTP interno (stdlib) con `X-Service-Token` y errores del dominio."""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.domain.errors import NotFoundError, UpstreamError


class JsonHttpClient:
    def __init__(self, base_url: str, service_token: str, timeout_seconds: int = 15) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise UpstreamError("Esquema de URL no permitido", {"base_url": base_url})
        self._base_url = base_url.rstrip("/")
        self._token = service_token
        self._timeout = timeout_seconds

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        if self._token:
            headers["X-Service-Token"] = self._token
        req = urllib.request.Request(  # noqa: S310 (esquema validado en __init__)
            url=url, data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise NotFoundError(f"Recurso no encontrado en {path}", {"url": url}) from exc
            preview = exc.read().decode("utf-8", errors="replace")[:300]
            raise UpstreamError(
                f"El servicio respondió HTTP {exc.code} en {path}",
                {"url": url, "upstream_status": exc.code, "upstream_body": preview},
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise UpstreamError(
                f"No se pudo conectar con {url}", {"url": url, "reason": str(exc)}
            ) from exc
        if not raw.strip():
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise UpstreamError(
                f"Respuesta no JSON desde {url}", {"raw_preview": raw[:300]}
            ) from exc


def items_of(data: Any) -> list[dict[str, Any]]:
    """Acepta `{"items": [...]}` o una lista directa."""
    items = data.get("items", []) if isinstance(data, dict) else data
    return [dict(i) for i in items if isinstance(i, dict)] if isinstance(items, list) else []
