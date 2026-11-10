"""Adaptadores HTTP hacia los microservicios REST internos (`X-Service-Token`)."""

from typing import Any

import httpx

from app.domain.errors import NotFoundError, UpstreamError
from app.domain.ports import JsonDict


class _BaseHttpGateway:
    def __init__(self, base_url: str, service_token: str, timeout: float = 15.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = service_token
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"X-Service-Token": self._token}

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: JsonDict | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.request(
                    method=method,
                    url=url,
                    headers=self._headers(),
                    params=params,
                    json=json_body,
                )
        except httpx.HTTPError as exc:
            raise UpstreamError(f"Error de red al llamar a {url}: {exc}") from exc

        if resp.status_code == 404:
            raise NotFoundError(f"Recurso no encontrado en {path}", {"url": url})
        if resp.status_code >= 400:
            raise UpstreamError(
                f"El servicio respondió {resp.status_code} en {path}: {resp.text[:300]}",
                {"status_code": resp.status_code, "url": url},
            )
        try:
            return resp.json()
        except ValueError as exc:
            raise UpstreamError(f"Respuesta no es JSON válido desde {url}") from exc


class HttpProfileGateway(_BaseHttpGateway):
    async def get_profile(self, profile_id: str) -> JsonDict:
        data = await self._request("GET", f"/api/v1/profiles/{profile_id}")
        return dict(data)

    async def list_profiles(self, skills: list[str], limit: int) -> list[JsonDict]:
        params: dict[str, Any] = {"limit": limit}
        if skills:
            params["skills"] = ",".join(skills)
        data = await self._request("GET", "/api/v1/profiles", params=params)
        items = data.get("items", data) if isinstance(data, dict) else data
        return [dict(item) for item in items][:limit]


class HttpJobsGateway(_BaseHttpGateway):
    async def get_job(self, job_id: str) -> JsonDict:
        data = await self._request("GET", f"/api/v1/jobs/{job_id}")
        return dict(data)

    async def list_active_jobs(self, limit: int) -> list[JsonDict]:
        params: dict[str, Any] = {"status": "active", "limit": limit}
        data = await self._request("GET", "/api/v1/jobs", params=params)
        items = data.get("items", data) if isinstance(data, dict) else data
        return [dict(item) for item in items][:limit]


class HttpMatchingGateway(_BaseHttpGateway):
    async def compute_match(self, profile_id: str, job_id: str) -> JsonDict:
        data = await self._request(
            "POST",
            "/api/v1/matches",
            json_body={"profile_id": profile_id, "job_id": job_id},
        )
        return dict(data)

    async def missing_skills(self, profile_id: str, job_id: str) -> list[JsonDict]:
        data = await self._request(
            "POST",
            "/api/v1/matches/missing-skills",
            json_body={"profile_id": profile_id, "job_id": job_id},
        )
        items = data.get("items", data) if isinstance(data, dict) else data
        return [dict(item) for item in items]

    async def rank_jobs_for_student(self, profile_id: str, limit: int | None) -> JsonDict:
        params = {"limit": limit} if limit else None
        data = await self._request(
            "GET", f"/api/v1/matches/students/{profile_id}/jobs", params=params
        )
        return dict(data)

    async def rank_candidates_for_job(self, job_id: str, limit: int | None) -> JsonDict:
        params = {"limit": limit} if limit else None
        data = await self._request(
            "GET", f"/api/v1/matches/jobs/{job_id}/candidates", params=params
        )
        return dict(data)

    async def resolve_skills(self, skills: list[str], profile_skills: list[str]) -> JsonDict:
        data = await self._request(
            "POST",
            "/api/v1/matches/skills/resolve",
            json_body={"skills": skills, "profile_skills": profile_skills},
        )
        return dict(data)


class HttpRecommendationStore(_BaseHttpGateway):
    async def save(self, recommendation: JsonDict) -> JsonDict:
        data = await self._request(
            "POST",
            "/api/v1/matches/recommendations",
            json_body=recommendation,
        )
        return dict(data)
