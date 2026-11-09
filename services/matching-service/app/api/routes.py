"""Endpoints REST de matching-service (`/api/v1/matches`). Controllers delgados.

Acceso:
- Internos (n8n / mcp-tools, `X-Service-Token`): rankings sin IA, missing-skills y guardado de IA.
- Frontend (`Authorization: Bearer <JWT>` de auth-service): vistas, pedidos de análisis y match
  puntual, siempre filtrados por dueño (ver `AccessPolicy`).
- Configuración (`/settings`): la lee un admin o un servicio; sólo un admin la cambia.
"""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import get_container, get_principal, require_service
from app.application.serializers import (
    VIEWER_COMPANY,
    VIEWER_INTERNAL,
    VIEWER_STUDENT,
    candidate_ranking_to_dict,
    job_ranking_to_dict,
    match_to_dict,
    recommendation_to_dict,
)
from app.application.settings_service import settings_to_dict
from app.domain.auth import Principal, Role
from app.domain.recommendations import RecommendationMode, RecommendationRequest
from app.domain.settings import MAX_LIMIT, MIN_LIMIT
from app.infrastructure.container import Container

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])

ContainerDep = Annotated[Container, Depends(get_container)]
PrincipalDep = Annotated[Principal, Depends(get_principal)]
ServiceDep = Annotated[Principal, Depends(require_service)]
# Un `limit` explícito sólo puede achicar el número configurado por el admin.
LimitQuery = Annotated[int | None, Query(ge=MIN_LIMIT, le=MAX_LIMIT)]

_VIEWER_BY_ROLE = {Role.STUDENT: VIEWER_STUDENT, Role.COMPANY: VIEWER_COMPANY}


class MatchRequest(BaseModel):
    profile_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)


class AnalysisRequest(BaseModel):
    # training: formación (cursos, proyectos, consejos) de un estudiante para una oferta.
    mode: Literal["student", "company", "training"]
    profile_id: str | None = None
    job_id: str | None = None
    # Sin `limit` usa el configurado por el admin; con `limit`, el menor de los dos.
    limit: int | None = Field(default=None, ge=MIN_LIMIT, le=MAX_LIMIT)


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_jobs_limit: int | None = Field(default=None, ge=MIN_LIMIT, le=MAX_LIMIT)
    company_candidates_limit: int | None = Field(default=None, ge=MIN_LIMIT, le=MAX_LIMIT)


def _request_to_dict(req: RecommendationRequest) -> dict[str, Any]:
    return {
        "request_id": req.id,
        "mode": req.mode.value,
        "subject_id": req.subject_id,
        "status": req.status.value,
        "created_at": req.created_at,
        "updated_at": req.updated_at,
        "error": dict(req.error) if req.error else None,
        **({"job_id": req.job_id} if req.job_id else {}),
    }


# ------------------------------------------------------------- reglas ---


@router.post("", summary="Calcula la compatibilidad por reglas (origin=RULES)")
def compute_match(
    body: MatchRequest, container: ContainerDep, principal: PrincipalDep
) -> dict[str, Any]:
    container.access.match(principal, body.profile_id, body.job_id)
    result, profile, job = container.matching.compute(body.profile_id, body.job_id)
    viewer = _VIEWER_BY_ROLE.get(principal.role, VIEWER_INTERNAL)
    return match_to_dict(result, profile, job, viewer)


@router.post("/missing-skills", summary="[interno] Skills faltantes y brecha de nivel")
def missing_skills(body: MatchRequest, container: ContainerDep, _: ServiceDep) -> dict[str, Any]:
    result, _profile, _job = container.matching.compute(body.profile_id, body.job_id)
    full = match_to_dict(result)
    return {
        "origin": "RULES",
        "engine_version": result.engine_version,
        "profile_id": result.profile_id,
        "job_id": result.job_id,
        "items": full["missing_skills"],
    }


@router.get(
    "/students/{profile_id}/jobs",
    summary="[interno] Ofertas rankeadas por reglas para un estudiante",
)
def rank_jobs(
    profile_id: str,
    container: ContainerDep,
    _: ServiceDep,
    limit: LimitQuery = None,
    include_incompatible: bool | None = None,
) -> dict[str, Any]:
    ranking = container.matching.rank_jobs_for_student(profile_id, limit, include_incompatible)
    return job_ranking_to_dict(ranking)


@router.get(
    "/jobs/{job_id}/candidates", summary="[interno] Candidatos rankeados por reglas para una oferta"
)
def rank_candidates(
    job_id: str,
    container: ContainerDep,
    _: ServiceDep,
    limit: LimitQuery = None,
    include_incompatible: bool | None = None,
) -> dict[str, Any]:
    ranking = container.matching.rank_candidates_for_job(job_id, limit, include_incompatible)
    return candidate_ranking_to_dict(ranking)


# -------------------------------------------------- recomendaciones IA ---


@router.post(
    "/recommendations",
    status_code=status.HTTP_201_CREATED,
    summary="[interno] Guarda una recomendación de IA (save_recommendation de MCP)",
)
def save_recommendation(
    body: dict[str, Any], container: ContainerDep, _: ServiceDep
) -> dict[str, Any]:
    return recommendation_to_dict(container.recommendations.save(body))


@router.post(
    "/recommendations/batch",
    status_code=status.HTTP_201_CREATED,
    summary="[interno] Guarda el resultado completo de WF-06 (n8n)",
)
def save_recommendation_batch(
    body: dict[str, Any], container: ContainerDep, _: ServiceDep
) -> dict[str, Any]:
    saved = container.recommendations.save_batch(body)
    return {"saved": len(saved), "ids": [r.id for r in saved]}


@router.post(
    "/recommendations/requests",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Pide a n8n (WF-06) un análisis de IA; responde enseguida con request_id",
)
def request_recommendations(
    body: AnalysisRequest,
    background: BackgroundTasks,
    container: ContainerDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    subject = (body.job_id if body.mode == "company" else body.profile_id) or ""
    if subject:
        container.access.subject(principal, body.mode, subject)
    job_id = (body.job_id or "") if body.mode == "training" else ""
    request = container.recommendations.request_analysis(body.mode, subject, job_id)
    limit = container.recommendations.analysis_limit(RecommendationMode(body.mode), body.limit)
    background.add_task(container.recommendations.run_analysis, request.id, limit)
    return {**_request_to_dict(request), "limit": limit}


@router.get("/recommendations/requests/{request_id}", summary="Estado de un pedido de análisis")
def get_recommendation_request(
    request_id: str, container: ContainerDep, principal: PrincipalDep
) -> dict[str, Any]:
    request = container.recommendations.get_request(request_id)
    container.access.subject(principal, request.mode.value, request.subject_id)
    return _request_to_dict(request)


@router.get(
    "/recommendations/students/{profile_id}",
    summary="Ofertas recomendadas a un estudiante (reglas + IA en bloques separados)",
)
def student_recommendations(
    profile_id: str, container: ContainerDep, principal: PrincipalDep, limit: LimitQuery = None
) -> dict[str, Any]:
    container.access.student_profile(principal, profile_id)
    return container.recommendations.student_view(profile_id, limit)


@router.get(
    "/recommendations/students/{profile_id}/training/{job_id}",
    summary="Formación sugerida por IA para encajar en una oferta (+ match por reglas)",
)
def training_recommendations(
    profile_id: str, job_id: str, container: ContainerDep, principal: PrincipalDep
) -> dict[str, Any]:
    container.access.student_profile(principal, profile_id)
    return container.recommendations.training_view(profile_id, job_id)


@router.get(
    "/recommendations/jobs/{job_id}",
    summary="Candidatos recomendados para una oferta (reglas + IA en bloques separados)",
)
def company_recommendations(
    job_id: str, container: ContainerDep, principal: PrincipalDep, limit: LimitQuery = None
) -> dict[str, Any]:
    container.access.company_job(principal, job_id)
    return container.recommendations.company_view(job_id, limit)


# -------------------------------------------------------- configuración ---


@router.get("/settings", summary="Configuración de recomendaciones (admin o servicio)")
def get_settings(container: ContainerDep, principal: PrincipalDep) -> dict[str, Any]:
    return settings_to_dict(container.settings_admin.get(principal))


@router.patch("/settings", summary="Ajusta cuántas ofertas y candidatos se recomiendan (admin)")
def update_settings(
    body: SettingsUpdate, container: ContainerDep, principal: PrincipalDep
) -> dict[str, Any]:
    changes = body.model_dump(exclude_none=True)
    return settings_to_dict(container.settings_admin.update(principal, changes))
