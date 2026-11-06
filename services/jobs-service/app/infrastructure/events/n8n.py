"""Publicación de eventos de jobs-service hacia n8n."""

import json
import urllib.error
import urllib.request

from app.domain.errors import UpstreamError
from app.domain.models import JobOpportunity


class HttpN8nEventPublisher:
    """`POST {N8N_WEBHOOK_BASE_URL}/job-created`. Best-effort: el caso de uso decide."""

    def __init__(self, base_url: str, service_token: str, timeout_seconds: int = 3) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_token = service_token
        self._timeout = timeout_seconds

    def job_created(self, job: JobOpportunity) -> None:
        body = {
            "event": "job.created",
            "occurred_at": job.created_at.isoformat(),
            "job_id": job.id,
            "company_id": job.company_id,
            "title": job.title,
            "status": job.status.value,
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._service_token:
            headers["X-Service-Token"] = self._service_token
        request = urllib.request.Request(  # noqa: S310 - URL interna validada
            f"{self._base_url}/job-created",
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout):  # noqa: S310
                return
        except urllib.error.HTTPError as exc:
            raise UpstreamError(
                "n8n rechazó el evento job.created",
                {"status": exc.code},
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise UpstreamError("No se pudo publicar job.created en n8n") from exc
