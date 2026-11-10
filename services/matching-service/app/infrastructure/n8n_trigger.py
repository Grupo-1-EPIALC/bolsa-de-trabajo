"""Dispara WF-06 en n8n (`POST {N8N_WEBHOOK_BASE_URL}/recommendations`)."""

from typing import Any

from app.domain.errors import UpstreamError
from app.domain.ports import JsonDict
from app.infrastructure.http_client import JsonHttpClient


class HttpN8nAnalysisTrigger:
    def __init__(self, client: JsonHttpClient) -> None:
        self._client = client

    def request_analysis(self, request_id: str, mode: str, subject_id: str, limit: int) -> JsonDict:
        body: dict[str, Any] = {"mode": mode, "request_id": request_id, "limit": limit}
        if mode == "company":
            body["job_id"] = subject_id
        else:
            body["profile_id"] = subject_id
        data = self._client.request("POST", "/recommendations", body=body)
        if not isinstance(data, dict):
            raise UpstreamError("WF-06 devolvió una respuesta inválida")
        error = data.get("error")
        if error:
            details = error if isinstance(error, dict) else {"error": error}
            message = str(details.get("message") or "WF-06 no pudo generar las recomendaciones")
            raise UpstreamError(message, details)
        return data
