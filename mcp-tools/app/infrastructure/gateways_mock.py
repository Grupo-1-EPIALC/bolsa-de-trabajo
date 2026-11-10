"""Adaptadores Mock determinísticos con datos ficticios (`MCP_USE_MOCKS=true`).

Implementan exactamente los mismos puertos que los adaptadores HTTP, permitiendo probar
los flujos de n8n y las herramientas MCP de punta a punta mientras se desarrollan los
microservicios REST de negocio.
"""

import copy
from typing import Any

from app.domain.errors import NotFoundError
from app.domain.grounding import normalize
from app.domain.ports import JsonDict

MOCK_ENGINE_VERSION = "mock-rules-0.1.0"

_MOCK_PROFILES: dict[str, JsonDict] = {
    "stu-001": {
        "id": "stu-001",
        "full_name": "Valentina Gómez",
        "career": "Ingeniería en Sistemas de Información",
        "years_experience": 1,
        "education_level": "universitario_en_curso",
        "skills": [
            {"name": "Python", "level": 4},
            {"name": "SQL", "level": 3},
            {"name": "Git", "level": 4},
            {"name": "FastAPI", "level": 3},
        ],
        "languages": [
            {"name": "Español", "level": "nativo"},
            {"name": "Inglés", "level": "B2"},
        ],
        "summary": "Estudiante avanzada con interés en desarrollo backend Python y APIs REST.",
    },
    "stu-002": {
        "id": "stu-002",
        "full_name": "Mateo Fernández",
        "career": "Licenciatura en Ciencias de la Computación",
        "years_experience": 2,
        "education_level": "universitario_en_curso",
        "skills": [
            {"name": "TypeScript", "level": 4},
            {"name": "React", "level": 4},
            {"name": "Node.js", "level": 3},
            {"name": "Git", "level": 4},
            {"name": "Docker", "level": 2},
        ],
        "languages": [
            {"name": "Español", "level": "nativo"},
            {"name": "Inglés", "level": "C1"},
        ],
        "summary": "Desarrollador fullstack junior con foco en React y TypeScript.",
    },
    "stu-003": {
        "id": "stu-003",
        "full_name": "Camila Sosa",
        "career": "Tecnicatura Universitaria en Programación",
        "years_experience": 3,
        "education_level": "terciario_completo",
        "skills": [
            {"name": "Python", "level": 5},
            {"name": "FastAPI", "level": 4},
            {"name": "Docker", "level": 4},
            {"name": "PostgreSQL", "level": 4},
            {"name": "SQL", "level": 4},
            {"name": "Git", "level": 5},
        ],
        "languages": [
            {"name": "Español", "level": "nativo"},
            {"name": "Inglés", "level": "B2"},
        ],
        "summary": "Desarrolladora backend Python con experiencia en microservicios y Docker.",
    },
}

_MOCK_JOBS: dict[str, JsonDict] = {
    "job-001": {
        "id": "job-001",
        "title": "Desarrollador/a Backend Python Jr.",
        "company_name": "PampaTech S.A.",
        "status": "active",
        "min_years_experience": 1,
        "education_level": "universitario_en_curso",
        "requirements": [
            {"skill": "Python", "level": 3, "kind": "required"},
            {"skill": "FastAPI", "level": 3, "kind": "required"},
            {"skill": "SQL", "level": 3, "kind": "required"},
            {"skill": "Docker", "level": 3, "kind": "desired"},
            {"skill": "Testing", "level": 2, "kind": "desired"},
        ],
        "languages": [{"name": "Inglés", "level": "B1"}],
        "description": "Desarrollo de microservicios REST con Python, FastAPI y PostgreSQL.",
    },
    "job-002": {
        "id": "job-002",
        "title": "Desarrollador/a Frontend React + TypeScript",
        "company_name": "Andes Digital S.R.L.",
        "status": "active",
        "min_years_experience": 1,
        "education_level": "universitario_en_curso",
        "requirements": [
            {"skill": "React", "level": 3, "kind": "required"},
            {"skill": "TypeScript", "level": 3, "kind": "required"},
            {"skill": "Git", "level": 3, "kind": "required"},
            {"skill": "Node.js", "level": 2, "kind": "desired"},
        ],
        "languages": [{"name": "Inglés", "level": "B2"}],
        "description": "Construcción de interfaces accesibles en React 18 y TypeScript.",
    },
    "job-003": {
        "id": "job-003",
        "title": "Ingeniero/a de Datos y Automatización",
        "company_name": "Río Plata Analytics S.A.",
        "status": "active",
        "min_years_experience": 2,
        "education_level": "universitario_en_curso",
        "requirements": [
            {"skill": "Python", "level": 4, "kind": "excluding"},
            {"skill": "SQL", "level": 4, "kind": "required"},
            {"skill": "Docker", "level": 3, "kind": "required"},
            {"skill": "Linux", "level": 3, "kind": "desired"},
        ],
        "languages": [{"name": "Inglés", "level": "B2"}],
        "description": "Pipelines de datos en Python y SQL sobre contenedores Docker.",
    },
}


class MockProfileGateway:
    def __init__(self, initial: dict[str, JsonDict] | None = None) -> None:
        self._profiles = copy.deepcopy(initial if initial is not None else _MOCK_PROFILES)

    async def get_profile(self, profile_id: str) -> JsonDict:
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise NotFoundError(f"Perfil '{profile_id}' no encontrado", {"profile_id": profile_id})
        return copy.deepcopy(profile)

    async def list_profiles(self, skills: list[str], limit: int) -> list[JsonDict]:
        wanted = {normalize(s) for s in skills if s.strip()}
        results: list[JsonDict] = []
        for profile in self._profiles.values():
            if wanted:
                have = {normalize(str(s["name"])) for s in profile.get("skills", [])}
                if not (wanted & have):
                    continue
            results.append(copy.deepcopy(profile))
        return results[:limit]


class MockJobsGateway:
    def __init__(self, initial: dict[str, JsonDict] | None = None) -> None:
        self._jobs = copy.deepcopy(initial if initial is not None else _MOCK_JOBS)

    async def get_job(self, job_id: str) -> JsonDict:
        job = self._jobs.get(job_id)
        if job is None:
            raise NotFoundError(f"Oferta '{job_id}' no encontrada", {"job_id": job_id})
        return copy.deepcopy(job)

    async def list_active_jobs(self, limit: int) -> list[JsonDict]:
        active = [
            copy.deepcopy(job)
            for job in self._jobs.values()
            if job.get("status", "active") == "active"
        ]
        return active[:limit]


# Diccionario chico para el modo mock (el real vive en matching-service).
_MOCK_ALIASES = {
    "postgres": "postgresql",
    "psql": "postgresql",
    "reactjs": "react",
    "js": "javascript",
}
_MOCK_IMPLIES = {
    "postgresql": {"sql"},
    "mysql": {"sql"},
    "mariadb": {"sql"},
    "react": {"javascript"},
}
_MOCK_EQUIVALENT = [{"mysql", "mariadb"}]
_MOCK_SIMILAR = [
    ({"github", "gitlab", "bitbucket"}, 0.75),
    ({"postgresql", "mysql", "mariadb"}, 0.5),
]


def _mock_key(name: str) -> str:
    key = normalize(name)
    return _MOCK_ALIASES.get(key, key)


def _mock_coverage(have: set[str], key: str) -> JsonDict | None:
    if key in have:
        return {"relation": "exact", "credit": 1.0, "via": key, "full": True}
    for h in sorted(have):
        if key in _MOCK_IMPLIES.get(h, set()):
            return {"relation": "implied", "credit": 1.0, "via": h, "full": True}
    for group in _MOCK_EQUIVALENT:
        if key in group and have & (group - {key}):
            via = sorted(have & (group - {key}))[0]
            return {"relation": "equivalent", "credit": 1.0, "via": via, "full": True}
    for group, credit in _MOCK_SIMILAR:
        if key in group and have & (group - {key}):
            via = sorted(have & (group - {key}))[0]
            return {"relation": "similar", "credit": credit, "via": via, "full": False}
    return None


class MockMatchingGateway:
    """Calcula compatibilidad determinística con pesos 50/15/15/10/5/5 y regla excluyente."""

    def __init__(
        self,
        profiles: MockProfileGateway,
        jobs: MockJobsGateway,
    ) -> None:
        self._profiles = profiles
        self._jobs = jobs

    async def compute_match(self, profile_id: str, job_id: str) -> JsonDict:
        profile = await self._profiles.get_profile(profile_id)
        job = await self._jobs.get_job(job_id)

        student_skills: dict[str, int] = {
            normalize(str(s["name"])): int(s.get("level") or 1) for s in profile.get("skills", [])
        }
        reqs: list[dict[str, Any]] = list(job.get("requirements", []))
        required = [r for r in reqs if r.get("kind") in ("required", "excluding")]
        desired = [r for r in reqs if r.get("kind") == "desired"]
        excluding = [r for r in reqs if r.get("kind") == "excluding"]

        req_hits = sum(1 for r in required if normalize(str(r["skill"])) in student_skills)
        req_score = (req_hits / len(required) * 50.0) if required else 50.0

        des_hits = sum(1 for r in desired if normalize(str(r["skill"])) in student_skills)
        des_score = (des_hits / len(desired) * 15.0) if desired else 15.0

        level_ratios: list[float] = []
        for r in reqs:
            key = normalize(str(r["skill"]))
            if key in student_skills:
                target = max(1, int(r.get("level") or 1))
                level_ratios.append(min(1.0, student_skills[key] / target))
        level_score = (sum(level_ratios) / len(level_ratios) * 15.0) if level_ratios else 0.0

        min_exp = int(job.get("min_years_experience") or 0)
        stu_exp = int(profile.get("years_experience") or 0)
        exp_score = 10.0 if min_exp <= 0 else min(1.0, stu_exp / min_exp) * 10.0

        edu_score = 5.0 if profile.get("education_level") else 2.5

        stu_langs = {normalize(str(lang["name"])) for lang in profile.get("languages", [])}
        job_langs = [normalize(str(lang["name"])) for lang in job.get("languages", [])]
        lang_hits = sum(1 for lang in job_langs if lang in stu_langs)
        lang_score = (lang_hits / len(job_langs) * 5.0) if job_langs else 5.0

        raw_total = req_score + des_score + level_score + exp_score + edu_score + lang_score
        missing_excluding = any(normalize(str(r["skill"])) not in student_skills for r in excluding)
        final_score = round(min(raw_total, 40.0) if missing_excluding else raw_total, 2)

        return {
            "profile_id": profile_id,
            "job_id": job_id,
            "score": final_score,
            "excluding_Rule_applied": missing_excluding,
            "breakdown": {
                "required_skills": round(req_score, 2),
                "desired_skills": round(des_score, 2),
                "skill_levels": round(level_score, 2),
                "experience": round(exp_score, 2),
                "education": round(edu_score, 2),
                "languages": round(lang_score, 2),
            },
            "origin": "RULES",
            "engine_version": MOCK_ENGINE_VERSION,
        }

    async def missing_skills(self, profile_id: str, job_id: str) -> list[JsonDict]:
        profile = await self._profiles.get_profile(profile_id)
        job = await self._jobs.get_job(job_id)

        student_skills: dict[str, int] = {
            normalize(str(s["name"])): int(s.get("level") or 1) for s in profile.get("skills", [])
        }
        priority_map = {"excluding": "alta", "required": "alta", "desired": "media"}
        priority_order = {"alta": 0, "media": 1, "baja": 2}
        gaps: list[JsonDict] = []

        for req in job.get("requirements", []):
            skill_name = str(req["skill"])
            req_level = int(req.get("level") or 1)
            kind = str(req.get("kind") or "required")
            curr_level = student_skills.get(normalize(skill_name), 0)
            if curr_level < req_level:
                prio = priority_map.get(kind, "baja") if curr_level == 0 else "media"
                gaps.append(
                    {
                        "skill": skill_name,
                        "kind": kind,
                        "required_level": req_level,
                        "current_level": curr_level,
                        "gap": req_level - curr_level,
                        "priority": prio,
                    }
                )

        gaps.sort(key=lambda g: (priority_order.get(str(g["priority"]), 3), -int(g["gap"])))
        return gaps

    # Mismos valores iniciales que matching-service (scoring_rules.yaml → ranking)
    DEFAULT_STUDENT_JOBS = 5
    DEFAULT_COMPANY_CANDIDATES = 10

    async def _match_block(self, profile_id: str, job_id: str) -> JsonDict:
        match = await self.compute_match(profile_id, job_id)
        missing = await self.missing_skills(profile_id, job_id)
        return {
            "origin": "RULES",
            "engine_version": match["engine_version"],
            "profile_id": profile_id,
            "job_id": job_id,
            "score": match["score"],
            "excluding_cap_applied": match["excluding_Rule_applied"],
            "breakdown": [{"criterion": k, "earned": v} for k, v in match["breakdown"].items()],
            "missing_skills": missing,
            "matched_skills": [],
            # Los mocks no modelan condiciones laborales: todo es compatible.
            "conditions_fit": {
                "compatible": True,
                "distance_km": None,
                "checks": [],
                "salary_fit": None,
            },
        }

    @staticmethod
    def _candidate_snapshot(profile: JsonDict) -> JsonDict:
        """Sin nombre ni contacto (mismo criterio que matching-service)."""
        return {
            "profile_id": profile["id"],
            "headline": profile.get("summary", ""),
            "years_experience": profile.get("years_experience", 0),
            "skills": profile.get("skills", []),
            "languages": profile.get("languages", []),
            "academic_status": {"career": profile.get("career", "")},
        }

    @staticmethod
    def _job_snapshot(job: JsonDict) -> JsonDict:
        return {
            "job_id": job["id"],
            "title": job.get("title", ""),
            "company_name": job.get("company_name", ""),
            "requirements": {"skills": job.get("requirements", [])},
        }

    async def rank_jobs_for_student(self, profile_id: str, limit: int | None) -> JsonDict:
        profile = await self._profiles.get_profile(profile_id)
        jobs = await self._jobs.list_active_jobs(limit=1000)
        ranked = [(job, await self._match_block(profile_id, job["id"])) for job in jobs]
        ranked.sort(key=lambda pair: (-float(pair[1]["score"]), pair[0]["id"]))
        top = ranked[: limit or self.DEFAULT_STUDENT_JOBS]
        return {
            "origin": "RULES",
            "profile_id": profile_id,
            "profile": self._candidate_snapshot(profile),
            "engine_version": MOCK_ENGINE_VERSION,
            "evaluated": len(jobs),
            "excluded_incompatible": 0,
            "items": [
                {"rank": pos, "job": self._job_snapshot(job), "match": match}
                for pos, (job, match) in enumerate(top, start=1)
            ],
        }

    async def rank_candidates_for_job(self, job_id: str, limit: int | None) -> JsonDict:
        job = await self._jobs.get_job(job_id)
        profiles = await self._profiles.list_profiles(skills=[], limit=1000)
        ranked = [(p, await self._match_block(p["id"], job_id)) for p in profiles]
        ranked.sort(key=lambda pair: (-float(pair[1]["score"]), pair[0]["id"]))
        top = ranked[: limit or self.DEFAULT_COMPANY_CANDIDATES]
        return {
            "origin": "RULES",
            "job_id": job_id,
            "job": self._job_snapshot(job),
            "engine_version": MOCK_ENGINE_VERSION,
            "evaluated": len(profiles),
            "excluded_incompatible": 0,
            "items": [
                {"rank": pos, "candidate": self._candidate_snapshot(p), "match": match}
                for pos, (p, match) in enumerate(top, start=1)
            ],
        }

    async def resolve_skills(self, skills: list[str], profile_skills: list[str]) -> JsonDict:
        have = {_mock_key(s) for s in profile_skills}
        items: list[JsonDict] = []
        for name in skills:
            key = _mock_key(name)
            item: JsonDict = {
                "input": name,
                "key": key,
                "name": name.strip(),
                "implies": sorted(_MOCK_IMPLIES.get(key, set())),
                "equivalents": sorted(k for g in _MOCK_EQUIVALENT if key in g for k in g - {key}),
                "similar": [
                    {"skill": k, "credit": credit}
                    for g, credit in _MOCK_SIMILAR
                    if key in g
                    for k in sorted(g - {key})
                ],
            }
            if profile_skills:
                item["covered_by"] = _mock_coverage(have, key)
            items.append(item)
        return {"origin": "RULES", "dictionary_version": "mock", "items": items}


class MockRecommendationStore:
    def __init__(self) -> None:
        self._saved: list[JsonDict] = []

    async def save(self, recommendation: JsonDict) -> JsonDict:
        record = {
            "id": f"rec-{len(self._saved) + 1:03d}",
            **copy.deepcopy(recommendation),
        }
        self._saved.append(record)
        return copy.deepcopy(record)

    def all_saved(self) -> list[JsonDict]:
        return copy.deepcopy(self._saved)
