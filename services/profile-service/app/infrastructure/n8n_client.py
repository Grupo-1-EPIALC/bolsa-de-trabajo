"""Adaptador HTTP para invocar el webhook de extracción de CV en n8n (`WF-01`)."""

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

from app.domain.errors import WebhookExtractionError
from app.domain.models import CvExtractionResult, UploadedCvFile


class HttpN8nCvWebhookGateway:
    """Envía el CV al webhook `POST {N8N_WEBHOOK_BASE_URL}/cv-extract` de n8n."""

    def __init__(
        self,
        webhook_base_url: str = "http://n8n:5678/webhook",
        service_token: str = "",
        timeout_seconds: int = 300,
    ) -> None:
        self._base_url = webhook_base_url.rstrip("/")
        self._service_token = service_token
        self._timeout = timeout_seconds

    def extract_cv_suggestions(
        self,
        profile_id: str,
        cv_file: UploadedCvFile,
    ) -> CvExtractionResult:
        url = f"{self._base_url}/cv-extract"
        payload = {
            "profile_id": profile_id,
            "filename": cv_file.original_filename,
            "stored_filename": cv_file.stored_filename,
            "mime_type": cv_file.mime_type,
            "content_base64": cv_file.content_base64,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._service_token:
            headers["X-Service-Token"] = self._service_token

        if not url.startswith(("http://", "https://")):
            raise WebhookExtractionError(
                "Esquema de URL de webhook no permitido",
                status_code=500,
                details={"webhook_url": url},
            )

        req = urllib.request.Request(  # noqa: S310
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
                raw_body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            err_text = exc.read().decode("utf-8", errors="replace")
            raise WebhookExtractionError(
                f"El webhook de n8n devolvió HTTP {exc.code}",
                status_code=502,
                details={
                    "webhook_url": url,
                    "upstream_status": exc.code,
                    "upstream_body": err_text[:500],
                },
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise WebhookExtractionError(
                "No se pudo conectar con el webhook de n8n para procesar el CV",
                status_code=503,
                details={"webhook_url": url, "reason": str(exc)},
            ) from exc

        try:
            data: dict[str, Any] = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise WebhookExtractionError(
                "El webhook de n8n devolvió una respuesta que no es JSON válido",
                status_code=502,
                details={"raw_preview": raw_body[:300]},
            ) from exc

        if "error" in data and data.get("error"):
            err_obj = data["error"]
            msg = (
                err_obj.get("message", "Error en el workflow de extracción de CV")
                if isinstance(err_obj, dict)
                else str(err_obj)
            )
            status = int(data.get("status_code", 502))
            raise WebhookExtractionError(
                msg,
                status_code=status if 400 <= status < 600 else 502,
                details=err_obj if isinstance(err_obj, dict) else {"error": err_obj},
            )

        file_info = dict(data.get("file") or {})
        file_info.setdefault("filename", cv_file.original_filename)
        file_info["stored_filename"] = cv_file.stored_filename
        file_info["size_bytes"] = cv_file.size_bytes
        file_info.setdefault("format", cv_file.extension)

        return CvExtractionResult(
            profile_id=str(data.get("profile_id") or profile_id),
            file=file_info,
            cv_suggestions=dict(
                data.get("cv_suggestions")
                or {"skills": [], "experience": [], "education": [], "languages": []}
            ),
            origin="AI",
            model=data.get("model"),
            prompt_version=str(data.get("prompt_version") or "1.0.0"),
            generated_at=str(data.get("generated_at") or datetime.now(UTC).isoformat()),
            verified=bool(data.get("verified", True)),
            disclaimer=str(
                data.get("disclaimer")
                or "Sugerencias extraídas automáticamente por IA del CV subido. "
                "Revisá, editá o descartá cada ítem antes de guardar tu perfil."
            ),
        )
