"""Fuentes mock con datos ficticios (`MATCHING_USE_MOCKS=true`).

Mismos IDs que los mocks de `mcp-tools` (`stu-00X`, `job-00X`) pero con la estructura común
completa (ubicación, condiciones laborales, sueldo pretendido/ofrecido).
"""

import copy
import json
from pathlib import Path

from app.domain.errors import NotFoundError
from app.domain.ports import JsonDict
from app.infrastructure.config import DATA_DIR

MOCK_DIR = DATA_DIR / "mock"


def _load(file: Path) -> dict[str, JsonDict]:
    items = json.loads(file.read_text(encoding="utf-8"))
    return {str(item["id"]): item for item in items}


class MockProfileSource:
    def __init__(self, profiles: dict[str, JsonDict] | None = None) -> None:
        self._profiles = copy.deepcopy(
            profiles if profiles is not None else _load(MOCK_DIR / "profiles.json")
        )

    def get_profile(self, profile_id: str) -> JsonDict:
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise NotFoundError(f"Perfil '{profile_id}' no encontrado", {"profile_id": profile_id})
        return copy.deepcopy(profile)

    def list_profiles(self, limit: int) -> list[JsonDict]:
        return [copy.deepcopy(p) for p in self._profiles.values()][:limit]


class MockJobSource:
    def __init__(self, jobs: dict[str, JsonDict] | None = None) -> None:
        self._jobs = copy.deepcopy(jobs if jobs is not None else _load(MOCK_DIR / "jobs.json"))

    def get_job(self, job_id: str) -> JsonDict:
        job = self._jobs.get(job_id)
        if job is None:
            raise NotFoundError(f"Oferta '{job_id}' no encontrada", {"job_id": job_id})
        return copy.deepcopy(job)

    def list_active_jobs(self, limit: int) -> list[JsonDict]:
        active = [j for j in self._jobs.values() if j.get("status", "active") == "active"]
        return [copy.deepcopy(j) for j in active][:limit]
