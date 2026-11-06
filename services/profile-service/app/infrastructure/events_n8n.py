"""Publicación de `profile.updated` hacia n8n (`POST {N8N_WEBHOOK_BASE_URL}/profile-updated`)."""

import json
import urllib.request

from app.domain.profile import StudentProfile


class HttpN8nProfileEventPublisher:
    """Best-effort: si n8n no responde, el caso de uso lo registra y sigue."""

    def __init__(self, base_url: str, service_token: str, timeout_seconds: int = 3) -> None:
        self._url = base_url.rstrip("/") + "/profile-updated"
        if not self._url.startswith(("http://", "https://")):
            raise ValueError(f"N8N_WEBHOOK_BASE_URL inválida: {base_url!r}")
        self._service_token = service_token
        self._timeout = timeout_seconds

    def profile_updated(self, profile: StudentProfile) -> None:
        body = {
            "event": "profile.updated",
            "occurred_at": profile.updated_at.isoformat(),
            "profile_id": profile.id,
            "user_id": profile.user_id,
            "status": profile.status.value,
            "version": profile.version,
            "searchable": profile.is_searchable,
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._service_token:
            headers["X-Service-Token"] = self._service_token
        request = urllib.request.Request(  # noqa: S310 - URL interna validada
            self._url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
        )
        with urllib.request.urlopen(request, timeout=self._timeout):  # noqa: S310
            return
