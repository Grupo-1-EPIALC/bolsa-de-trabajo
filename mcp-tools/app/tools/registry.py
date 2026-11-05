"""Registro de herramientas MCP y contenedor de dependencias (Composición SOLID)."""

import os
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from app.application.cv_parser import CvParserService
from app.application.use_cases import (
    DEFAULT_AI_DISCLAIMER,
    AgentSettingsService,
    RecruitmentToolsService,
    RouterService,
    SkillCatalogService,
    VerificationService,
)
from app.domain.errors import DomainError
from app.domain.ports import (
    Clock,
    JobsGateway,
    JsonDict,
    MatchingGateway,
    ProfileGateway,
    RecommendationStore,
)
from app.domain.router import ModelRouter
from app.infrastructure.catalog_json import JsonCourseCatalog
from app.infrastructure.extractors import default_extractors
from app.infrastructure.gateways_http import (
    HttpJobsGateway,
    HttpMatchingGateway,
    HttpProfileGateway,
    HttpRecommendationStore,
)
from app.infrastructure.gateways_mock import (
    MockJobsGateway,
    MockMatchingGateway,
    MockProfileGateway,
    MockRecommendationStore,
)
from app.infrastructure.router_store import FileRouterStateStore, SystemClock
from app.infrastructure.schemas_json import JsonSchemaValidator
from app.infrastructure.settings_env import build_settings_provider
from app.infrastructure.skills_fs import FileSystemSkillRepository


@dataclass(frozen=True)
class ServiceContainer:
    settings: AgentSettingsService
    cv_parser: CvParserService
    recruitment: RecruitmentToolsService
    verification: VerificationService
    router: RouterService
    skills: SkillCatalogService
    clock: Clock


def _error_payload(err: DomainError) -> JsonDict:
    return {
        "ok": False,
        "error": {
            "code": err.code,
            "message": err.message,
            "details": err.details,
        },
    }


async def _run_async(fn: Callable[[], Awaitable[Any]]) -> JsonDict:
    try:
        res = await fn()
        return {"ok": True, "data": res} if not isinstance(res, dict) else {"ok": True, **res}
    except DomainError as err:
        return _error_payload(err)


def _run_sync(fn: Callable[[], Any]) -> JsonDict:
    try:
        res = fn()
        return {"ok": True, "data": res} if not isinstance(res, dict) else {"ok": True, **res}
    except DomainError as err:
        return _error_payload(err)


def _session_from_context(ctx: Context[Any, Any, Any] | None) -> str:
    if ctx is None:
        return "default"
    try:
        req: Any = ctx.request_context.request
        if req is not None and hasattr(req, "query_params"):
            val = req.query_params.get("sesion")
            return str(val) if val else "default"
    except (LookupError, ValueError, AttributeError):
        return "default"
    return "default"


def build_container(env: Mapping[str, str] | None = None) -> ServiceContainer:
    source_env = env if env is not None else os.environ
    settings_provider = build_settings_provider(source_env)
    clock = SystemClock()
    use_mocks = source_env.get("MCP_USE_MOCKS", "true").strip().lower() in ("1", "true", "yes")
    token = source_env.get("SERVICE_TOKEN", "")

    if use_mocks:
        mock_profiles = MockProfileGateway()
        mock_jobs = MockJobsGateway()
        profiles: ProfileGateway = mock_profiles
        jobs: JobsGateway = mock_jobs
        matching: MatchingGateway = MockMatchingGateway(mock_profiles, mock_jobs)
        recommendations: RecommendationStore = MockRecommendationStore()
    else:
        profiles = HttpProfileGateway(
            source_env.get("PROFILE_SERVICE_URL", "http://profile-service:8000"),
            token,
        )
        jobs = HttpJobsGateway(
            source_env.get("JOBS_SERVICE_URL", "http://jobs-service:8000"),
            token,
        )
        matching = HttpMatchingGateway(
            source_env.get("MATCHING_SERVICE_URL", "http://matching-service:8000"),
            token,
        )
        recommendations = HttpRecommendationStore(
            source_env.get("MATCHING_SERVICE_URL", "http://matching-service:8000"),
            token,
        )

    state_path_raw = source_env.get("ROUTER_STATE_PATH", "")
    state_path = Path(state_path_raw) if state_path_raw else None
    model_router = ModelRouter(store=FileRouterStateStore(state_path), clock=clock)

    skills_dir_raw = source_env.get("SKILLS_DIR", "")
    skills_dir = Path(skills_dir_raw) if skills_dir_raw else None

    return ServiceContainer(
        settings=AgentSettingsService(settings_provider),
        cv_parser=CvParserService(settings_provider, default_extractors()),
        recruitment=RecruitmentToolsService(
            settings_provider=settings_provider,
            profiles=profiles,
            jobs=jobs,
            matching=matching,
            courses=JsonCourseCatalog(),
            recommendations=recommendations,
            clock=clock,
        ),
        verification=VerificationService(JsonSchemaValidator()),
        router=RouterService(model_router, settings_provider),
        skills=SkillCatalogService(FileSystemSkillRepository(skills_dir)),
        clock=clock,
    )


def register_tools(mcp: FastMCP, container: ServiceContainer) -> dict[str, Callable[..., Any]]:
    """Registra todas las herramientas en FastMCP y devuelve un mapa para tests directos."""
    registered: dict[str, Callable[..., Any]] = {}

    def _expose(fn: Callable[..., Any]) -> Callable[..., Any]:
        mcp.tool()(fn)
        registered[fn.__name__] = fn
        return fn

    @_expose
    async def get_agent_settings() -> JsonDict:
        """Devuelve la configuración vigente de los agentes (modelos NVIDIA por rol, límites RPM,
        reintentos del verificador, topes de recomendaciones y formatos de CV)."""
        return await _run_async(lambda: container.settings.get_settings())

    @_expose
    def fecha_hora() -> JsonDict:
        """Devuelve la fecha (`today`) y hora actual (`iso_now`) en UTC."""
        return _run_sync(
            lambda: {
                "today": container.clock.today(),
                "iso_now": container.clock.iso_now(),
            }
        )

    @_expose
    def list_skills() -> JsonDict:
        """Lista las skills del proyecto disponibles para leer con `leer_skill`."""
        return _run_sync(lambda: {"skills": container.skills.list_skills()})

    @_expose
    def leer_skill(
        id: str,
        archivo: str = "SKILL.md",
        desde: int = 0,
        ctx: Context[Any, Any, Any] | None = None,
    ) -> JsonDict:
        """Devuelve las instrucciones completas de una skill del proyecto (de tu lista
        'Skills del proyecto'). Leé solo las 1 a 2 más relevantes, una vez cada una, y respondé."""
        session_id = _session_from_context(ctx)
        return _run_sync(
            lambda: container.skills.read_skill(
                skill_id=id,
                file_path=archivo,
                offset=desde,
                session_id=session_id,
            )
        )

    @_expose
    async def parse_cv_file(
        content_base64: str,
        filename: str,
        mime_type: str = "",
    ) -> JsonDict:
        """Convierte un CV en base64 (PDF, DOCX, DOC o MD; máx. configurado en CV_MAX_SIZE_MB)
        a texto plano para estructurar sin inventar información."""
        return await _run_async(
            lambda: container.cv_parser.parse_base64(content_base64, filename, mime_type)
        )

    @_expose
    async def parse_cv_text(
        content_base64: str,
        filename: str = "cv.pdf",
        mime_type: str = "",
    ) -> JsonDict:
        """Alias de `parse_cv_file` compatible con AGENTS.md §4.6: extrae texto plano de un CV."""
        return await _run_async(
            lambda: container.cv_parser.parse_base64(content_base64, filename, mime_type)
        )

    @_expose
    async def leer_archivo(
        contenido_base64: str,
        nombre: str = "cv.pdf",
        mime: str = "",
    ) -> JsonDict:
        """Alias compatible con el nodo MCP Client de n8n (`agentes`): convierte a texto un
        archivo en base64 (PDF, DOCX, DOC o MD) y devuelve `{archivo, tipo, truncado, texto}`."""
        return await _run_async(
            lambda: container.cv_parser.parse_base64(contenido_base64, nombre, mime)
        )

    @_expose
    async def get_profile(profile_id: str) -> JsonDict:
        """Obtiene el perfil completo de un estudiante por su `profile_id`."""
        return await _run_async(lambda: container.recruitment.get_profile(profile_id))

    @_expose
    async def list_candidate_profiles(
        skills: list[str] | None = None,
        limit: int = 0,
    ) -> JsonDict:
        """Lista perfiles de candidatos filtrando opcionalmente por competencias (`skills`)."""
        return await _run_async(
            lambda: container.recruitment.list_candidate_profiles(skills=skills, limit=limit)
        )

    @_expose
    async def get_job(job_id: str) -> JsonDict:
        """Obtiene los detalles y requisitos de una oferta laboral por su `job_id`."""
        return await _run_async(lambda: container.recruitment.get_job(job_id))

    @_expose
    async def list_active_jobs(limit: int = 0) -> JsonDict:
        """Lista las ofertas laborales activas hasta el tope configurado."""
        return await _run_async(lambda: container.recruitment.list_active_jobs(limit=limit))

    @_expose
    async def compute_match(profile_id: str, job_id: str) -> JsonDict:
        """Calcula el puntaje de compatibilidad por reglas (`origin="RULES"`).
        El LLM NUNCA debe recalcular ni modificar este puntaje."""
        return await _run_async(lambda: container.recruitment.compute_match(profile_id, job_id))

    @_expose
    async def rank_jobs_for_student(profile_id: str, limit: int = 0) -> JsonDict:
        """Ranking por reglas (`origin="RULES"`) de las ofertas compatibles para un estudiante,
        ya ordenado y filtrado por condiciones laborales. Cada ítem trae `rank`, el snapshot de
        la oferta (`job`) y el `match` (score, desglose, skills que coinciden y faltan,
        `conditions_fit`). `limit=0` usa la cantidad configurada por el admin. NO reordenes ni
        modifiques los puntajes."""
        return await _run_async(
            lambda: container.recruitment.rank_jobs_for_student(profile_id, limit=limit)
        )

    @_expose
    async def rank_candidates_for_job(job_id: str, limit: int = 0) -> JsonDict:
        """Ranking por reglas (`origin="RULES"`) de los candidatos compatibles para una oferta,
        sin datos personales. Cada ítem trae `rank`, el snapshot del candidato (`candidate`) y el
        `match`. `limit=0` usa la cantidad configurada por el admin. NO reordenes ni modifiques
        los puntajes."""
        return await _run_async(
            lambda: container.recruitment.rank_candidates_for_job(job_id, limit=limit)
        )

    @_expose
    async def missing_skills(profile_id: str, job_id: str) -> JsonDict:
        """Devuelve las competencias faltantes y brechas de nivel entre un perfil y una oferta,
        ordenadas por prioridad (`alta`, `media`, `baja`)."""
        return await _run_async(lambda: container.recruitment.missing_skills(profile_id, job_id))

    @_expose
    def search_courses(skills: list[str], limit: int = 5) -> JsonDict:
        """Busca cursos de formación para cubrir las competencias indicadas en `skills`."""
        return _run_sync(lambda: container.recruitment.search_courses(skills, limit=limit))

    @_expose
    async def save_recommendation(
        profile_id: str,
        job_id: str,
        items: list[dict[str, Any]],
        model: str,
        prompt_version: str,
        disclaimer: str = DEFAULT_AI_DISCLAIMER,
    ) -> JsonDict:
        """Guarda una recomendación generada por IA sellando `origin="AI"`, modelo, versión
        de prompt y fecha. Única herramienta MCP de escritura."""
        return await _run_async(
            lambda: container.recruitment.save_recommendation(
                profile_id=profile_id,
                job_id=job_id,
                items=items,
                model=model,
                prompt_version=prompt_version,
                disclaimer=disclaimer,
            )
        )

    @_expose
    def validate_json_schema(schema_name: str, payload_json: str) -> JsonDict:
        """Valida determinísticamente un JSON contra un schema registrado
        (`cv_standard`, `student_recommendations`, `company_recommendations`)."""
        return _run_sync(lambda: container.verification.validate_json(schema_name, payload_json))

    @_expose
    def check_grounding(
        terms: list[str],
        source_text: str,
        expected_score: float | None = None,
        reported_score: float | None = None,
    ) -> JsonDict:
        """Verifica que cada competencia/término en `terms` exista en `source_text` (no inventar)
        y que `reported_score` coincida con `expected_score` (reglas vs. IA)."""
        return _run_sync(
            lambda: container.verification.check_grounding(
                terms=terms,
                source_text=source_text,
                expected_score=expected_score,
                reported_score=reported_score,
            )
        )

    @_expose
    async def router_reserve(
        role: str = "default",
        tried: list[str] | None = None,
    ) -> JsonDict:
        """Reserva de forma atómica el primer modelo NVIDIA disponible para el rol
        (`default`, `cv`, `verifier`) respetando el límite RPM y los cooldowns."""
        return await _run_async(lambda: container.router.reserve_for_role(role=role, tried=tried))

    @_expose
    def router_report_failure(model: str, error: str) -> JsonDict:
        """Registra el fallo de un modelo NVIDIA y le aplica cooldown exponencial según el error."""
        return _run_sync(lambda: container.router.report_failure(model, error))

    @_expose
    def router_report_success(model: str) -> JsonDict:
        """Limpia los strikes de fallo de un modelo NVIDIA tras una respuesta exitosa."""
        return _run_sync(lambda: container.router.report_success(model))

    @_expose
    def router_status() -> JsonDict:
        """Devuelve el estado actual de usos por minuto/día y cooldowns del router NVIDIA."""
        return _run_sync(lambda: container.router.status())

    return registered
