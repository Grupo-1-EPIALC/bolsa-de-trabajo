"""Casos de uso de las herramientas MCP (configuración, negocio, verificación y router)."""

import json

from app.domain.errors import InvalidInputError, SchemaNotFoundError
from app.domain.grounding import find_ungrounded
from app.domain.ports import (
    Clock,
    CourseCatalog,
    JobsGateway,
    JsonDict,
    MatchingGateway,
    ProfileGateway,
    RecommendationStore,
    SchemaValidator,
    SettingsProvider,
    SkillRepository,
)
from app.domain.router import ModelRouter

DEFAULT_AI_DISCLAIMER = (
    "Sugerencia generada por IA de forma orientativa. "
    "El puntaje de compatibilidad es calculado exclusivamente por reglas."
)


class AgentSettingsService:
    """Entrega la configuración vigente para los workflows de n8n."""

    def __init__(self, provider: SettingsProvider) -> None:
        self._provider = provider

    async def get_settings(self) -> JsonDict:
        settings = await self._provider.get()
        return settings.to_dict()


class RecruitmentToolsService:
    """Casos de uso de lectura sobre perfiles, ofertas, matching y cursos + guardado de IA."""

    def __init__(
        self,
        settings_provider: SettingsProvider,
        profiles: ProfileGateway,
        jobs: JobsGateway,
        matching: MatchingGateway,
        courses: CourseCatalog,
        recommendations: RecommendationStore,
        clock: Clock,
    ) -> None:
        self._settings = settings_provider
        self._profiles = profiles
        self._jobs = jobs
        self._matching = matching
        self._courses = courses
        self._recommendations = recommendations
        self._clock = clock

    async def get_profile(self, profile_id: str) -> JsonDict:
        clean_id = profile_id.strip()
        if not clean_id:
            raise InvalidInputError("profile_id es obligatorio")
        return await self._profiles.get_profile(clean_id)

    async def list_candidate_profiles(
        self,
        skills: list[str] | None = None,
        limit: int | None = None,
    ) -> list[JsonDict]:
        cfg = await self._settings.get()
        effective_limit = limit if limit and limit > 0 else cfg.recommendations.max_profiles_per_job
        clean_skills = [s.strip() for s in (skills or []) if s and s.strip()]
        return await self._profiles.list_profiles(skills=clean_skills, limit=effective_limit)

    async def get_job(self, job_id: str) -> JsonDict:
        clean_id = job_id.strip()
        if not clean_id:
            raise InvalidInputError("job_id es obligatorio")
        return await self._jobs.get_job(clean_id)

    async def list_active_jobs(self, limit: int | None = None) -> list[JsonDict]:
        cfg = await self._settings.get()
        effective_limit = limit if limit and limit > 0 else cfg.recommendations.max_jobs_per_student
        return await self._jobs.list_active_jobs(limit=effective_limit)

    async def compute_match(self, profile_id: str, job_id: str) -> JsonDict:
        if not profile_id.strip() or not job_id.strip():
            raise InvalidInputError("profile_id y job_id son obligatorios")
        result = await self._matching.compute_match(profile_id.strip(), job_id.strip())
        # Garantiza separación Reglas vs. IA (AGENTS.md §2.2)
        result.setdefault("origin", "RULES")
        result.setdefault("engine_version", "1.0.0")
        return result

    async def missing_skills(self, profile_id: str, job_id: str) -> list[JsonDict]:
        if not profile_id.strip() or not job_id.strip():
            raise InvalidInputError("profile_id y job_id son obligatorios")
        return await self._matching.missing_skills(profile_id.strip(), job_id.strip())

    async def rank_jobs_for_student(self, profile_id: str, limit: int | None = None) -> JsonDict:
        clean_id = profile_id.strip()
        if not clean_id:
            raise InvalidInputError("profile_id es obligatorio")
        result = await self._matching.rank_jobs_for_student(clean_id, _optional_limit(limit))
        result.setdefault("origin", "RULES")
        return result

    async def rank_candidates_for_job(self, job_id: str, limit: int | None = None) -> JsonDict:
        clean_id = job_id.strip()
        if not clean_id:
            raise InvalidInputError("job_id es obligatorio")
        result = await self._matching.rank_candidates_for_job(clean_id, _optional_limit(limit))
        result.setdefault("origin", "RULES")
        return result

    def search_courses(self, skills: list[str], limit: int = 5) -> list[JsonDict]:
        if limit <= 0:
            raise InvalidInputError("limit debe ser mayor que 0")
        clean_skills = [s.strip() for s in skills if s and s.strip()]
        return self._courses.search(skills=clean_skills, limit=limit)

    async def save_recommendation(
        self,
        profile_id: str,
        job_id: str,
        items: list[JsonDict],
        model: str,
        prompt_version: str,
        disclaimer: str = DEFAULT_AI_DISCLAIMER,
    ) -> JsonDict:
        if not profile_id.strip() or not job_id.strip():
            raise InvalidInputError("profile_id y job_id son obligatorios")
        if not model.strip() or not prompt_version.strip():
            raise InvalidInputError("model y prompt_version son obligatorios para resultados de IA")
        cfg = await self._settings.get()
        max_items = cfg.recommendations.max_items_per_job
        payload: JsonDict = {
            "profile_id": profile_id.strip(),
            "job_id": job_id.strip(),
            "items": list(items)[:max_items],
            "origin": "AI",
            "model": model.strip(),
            "prompt_version": prompt_version.strip(),
            "generated_at": self._clock.iso_now(),
            "disclaimer": disclaimer.strip() or DEFAULT_AI_DISCLAIMER,
        }
        return await self._recommendations.save(payload)


class VerificationService:
    """Validación determinística de JSON Schema, grounding (no inventar) e integridad de score."""

    def __init__(self, validator: SchemaValidator) -> None:
        self._validator = validator

    def validate_json(self, schema_name: str, payload: str | JsonDict) -> JsonDict:
        available = self._validator.available()
        if schema_name not in available:
            raise SchemaNotFoundError(
                f"Schema '{schema_name}' no encontrado. Disponibles: {', '.join(available)}",
                {"schema": schema_name, "available": available},
            )
        if isinstance(payload, str):
            try:
                doc: object = json.loads(payload)
            except json.JSONDecodeError as exc:
                return {
                    "valid": False,
                    "schema": schema_name,
                    "errors": [f"JSON inválido: {exc.msg} (línea {exc.lineno}, col {exc.colno})"],
                }
        else:
            doc = payload
        errors = self._validator.validate(schema_name, doc)
        return {"valid": len(errors) == 0, "schema": schema_name, "errors": errors}

    @staticmethod
    def check_grounding(
        terms: list[str],
        source_text: str,
        expected_score: float | None = None,
        reported_score: float | None = None,
    ) -> JsonDict:
        ungrounded = find_ungrounded(terms, source_text)
        score_tampered = (
            expected_score is not None
            and reported_score is not None
            and round(float(expected_score), 2) != round(float(reported_score), 2)
        )
        return {
            "grounded": len(ungrounded) == 0 and not score_tampered,
            "ungrounded_terms": ungrounded,
            "score_tampered": score_tampered,
        }


class RouterService:
    """Coordina el `ModelRouter` con la lista de modelos de `AgentSettings` por rol."""

    def __init__(self, router: ModelRouter, settings_provider: SettingsProvider) -> None:
        self._router = router
        self._settings = settings_provider

    async def reserve_for_role(
        self,
        role: str = "default",
        tried: list[str] | None = None,
        order_override: list[str] | None = None,
        rpm_limit_override: int | None = None,
    ) -> JsonDict:
        cfg = await self._settings.get()
        order = list(order_override) if order_override else list(cfg.models_for(role))
        rpm_limit = (
            rpm_limit_override if rpm_limit_override and rpm_limit_override > 0 else cfg.rpm_limit
        )
        res = self._router.reserve(order=order, tried=list(tried or []), rpm_limit=rpm_limit)
        return {
            **res,
            "role": role,
            "nvidia_base_url": cfg.nvidia_base_url,
            "temperature": cfg.temperature,
            "timeout_seconds": cfg.llm_timeout_seconds,
        }

    def report_failure(self, model: str, error: str) -> JsonDict:
        if not model.strip():
            raise InvalidInputError("model es obligatorio")
        return self._router.report_failure(model.strip(), error)

    def report_success(self, model: str) -> JsonDict:
        if not model.strip():
            raise InvalidInputError("model es obligatorio")
        return self._router.report_success(model.strip())

    def status(self) -> JsonDict:
        return self._router.status()


class SkillCatalogService:
    """Lectura de skills del proyecto (`leer_skill`) con anti-bucle por sesión."""

    def __init__(self, repo: SkillRepository) -> None:
        self._repo = repo

    def list_skills(self) -> list[JsonDict]:
        return self._repo.list_skills()

    def read_skill(
        self,
        skill_id: str,
        file_path: str = "SKILL.md",
        offset: int = 0,
        session_id: str = "default",
    ) -> JsonDict:
        return self._repo.read_skill(
            skill_id=skill_id,
            file_path=file_path,
            offset=offset,
            session_id=session_id,
        )


def _optional_limit(limit: int | None) -> int | None:
    """`None`/0 => usar la cantidad configurada por el admin en matching-service."""
    if limit is None or limit == 0:
        return None
    if limit < 0:
        raise InvalidInputError("limit no puede ser negativo")
    return limit
