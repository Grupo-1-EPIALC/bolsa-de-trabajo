"""Adaptador HTTP del agente `cv_designer` de n8n (`POST {N8N_WEBHOOK_BASE_URL}/cv-design`, WF-07).

Contrato en `contracts/n8n.md` §WF-07. La respuesta se vuelve a validar en `CvDesignService`.
"""

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

from app.domain.errors import CvDesignGatewayError
from app.domain.ports import CvDesignSuggestion


def _parse_datetime(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class HttpN8nCvDesignGateway:
    def __init__(
        self,
        webhook_base_url: str = "http://n8n:5678/webhook",
        service_token: str = "",
        timeout_seconds: int = 120,
    ) -> None:
        self._url = f"{webhook_base_url.rstrip('/')}/cv-design"
        self._service_token = service_token
        self._timeout = timeout_seconds

    def suggest_design(self, payload: dict[str, Any]) -> CvDesignSuggestion:
        if not self._url.startswith(("http://", "https://")):
            raise CvDesignGatewayError("Esquema de URL de webhook no permitido")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._service_token:
            headers["X-Service-Token"] = self._service_token
        request = urllib.request.Request(  # noqa: S310 - esquema validado arriba
            url=self._url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            raise CvDesignGatewayError(
                f"n8n devolvió HTTP {exc.code} al pedir el diseño del CV",
                {"upstream_status": exc.code, "upstream_body": body},
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise CvDesignGatewayError(
                "No se pudo conectar con n8n para pedir el diseño del CV",
                {"reason": str(exc)},
            ) from exc
        return self.parse(raw)

    @staticmethod
    def parse(raw: str) -> CvDesignSuggestion:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CvDesignGatewayError("n8n devolvió una respuesta que no es JSON") from exc
        if not isinstance(data, dict):
            raise CvDesignGatewayError("n8n devolvió una respuesta inesperada")
        error = data.get("error")
        if error:
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise CvDesignGatewayError(str(message or "El agente no pudo elegir un diseño"))
        design = data.get("design")
        if not isinstance(design, dict) or not design.get("layout"):
            raise CvDesignGatewayError("La respuesta de n8n no trae un diseño")
        order = design.get("section_order")
        return CvDesignSuggestion(
            layout=str(design["layout"]),
            section_order=tuple(str(s) for s in order) if isinstance(order, list) else (),
            rationale=str(design.get("rationale") or ""),
            model=str(data["model"]) if data.get("model") else None,
            prompt_version=str(data.get("prompt_version") or "1.0.0"),
            generated_at=_parse_datetime(data.get("generated_at") or datetime.now(UTC)),
            disclaimer=str(data.get("disclaimer") or ""),
        )
