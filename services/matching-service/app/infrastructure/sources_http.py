"""Adaptadores REST hacia profile-service y jobs-service (nunca a sus bases de datos)."""

from app.domain.errors import UpstreamError
from app.domain.ports import JsonDict
from app.infrastructure.http_client import JsonHttpClient, items_of


class HttpProfileSource:
    def __init__(self, client: JsonHttpClient) -> None:
        self._client = client

    def get_profile(self, profile_id: str) -> JsonDict:
        data = self._client.request("GET", f"/api/v1/profiles/{profile_id}")
        if not isinstance(data, dict):
            raise UpstreamError("profile-service devolvió un perfil inválido")
        return data

    def list_profiles(self, limit: int) -> list[JsonDict]:
        data = self._client.request("GET", "/api/v1/profiles", params={"limit": limit})
        return items_of(data)[:limit]


class HttpJobSource:
    def __init__(self, client: JsonHttpClient) -> None:
        self._client = client

    def get_job(self, job_id: str) -> JsonDict:
        data = self._client.request("GET", f"/api/v1/jobs/{job_id}")
        if not isinstance(data, dict):
            raise UpstreamError("jobs-service devolvió una oferta inválida")
        return data

    def list_active_jobs(self, limit: int) -> list[JsonDict]:
        data = self._client.request(
            "GET", "/api/v1/jobs", params={"status": "active", "limit": limit}
        )
        return [j for j in items_of(data) if j.get("status", "active") == "active"][:limit]
