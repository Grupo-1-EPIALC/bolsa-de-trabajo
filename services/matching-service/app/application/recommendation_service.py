"""Casos de uso de recomendaciones: n8n analiza (IA) y matching-service guarda y devuelve.

Flujo:
1. El frontend (o un workflow) pide un análisis: `request_analysis` crea un pedido `pending`.
2. En segundo plano `run_analysis` dispara WF-06 en n8n con el `request_id`.
3. WF-06 consulta el ranking por reglas de este servicio, ejecuta al agente y guarda el
   resultado con `save_batch` (`origin = "AI"`), que marca el pedido como `completed`.
4. `student_view` / `company_view` devuelven el bloque por reglas recalculado en el momento
   junto a la última recomendación de IA, siempre en bloques separados (AGENTS.md §2.2).

El LLM nunca fija el score: cualquier `score` que venga en el contenido de IA se descarta y
el valor mostrado sale siempre del motor de reglas.
"""

from collections.abc import Mapping
from typing import Any

from app.application.matching_service import MatchingService
from app.application.serializers import (
    candidate_ranking_to_dict,
    job_ranking_to_dict,
    recommendation_to_dict,
)
from app.domain.errors import InvalidInputError, MatchingError, NotFoundError
from app.domain.ports import (
    AnalysisTrigger,
    Clock,
    IdGenerator,
    RecommendationRepository,
    RecommendationRequestRepository,
    SettingsRepository,
)
from app.domain.recommendations import (
    DEFAULT_AI_DISCLAIMER,
    AiMetadata,
    AiRecommendation,
    RecommendationMode,
    RecommendationRequest,
    RequestStatus,
)
from app.domain.settings import RecommendationSettings

JsonDict = dict[str, Any]

# Claves que el LLM no puede aportar: el score y el ranking son de reglas.
_FORBIDDEN_AI_KEYS = frozenset({"score", "rank", "breakdown", "origin"})


def _mode(value: object) -> RecommendationMode:
    try:
        return RecommendationMode(str(value or "student").strip().lower())
    except ValueError as exc:
        raise InvalidInputError("mode debe ser 'student' o 'company'", {"mode": value}) from exc


def _clean_content(content: object) -> JsonDict:
    if not isinstance(content, Mapping):
        return {}
    return {str(k): v for k, v in content.items() if str(k) not in _FORBIDDEN_AI_KEYS}


def _items(value: object, max_items: int) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(_clean_content(i) for i in value if isinstance(i, Mapping))[:max_items]


class RecommendationService:
    def __init__(
        self,
        matching: MatchingService,
        repository: RecommendationRepository,
        requests: RecommendationRequestRepository,
        trigger: AnalysisTrigger,
        clock: Clock,
        ids: IdGenerator,
        settings: SettingsRepository,
        max_items_per_entry: int = 5,
    ) -> None:
        self._matching = matching
        self._repo = repository
        self._requests = requests
        self._trigger = trigger
        self._clock = clock
        self._ids = ids
        self._settings = settings
        self._max_items = max_items_per_entry

    # ------------------------------------------------------------- escritura ---

    def _metadata(self, payload: Mapping[str, Any]) -> AiMetadata:
        origin = str(payload.get("origin") or "AI")
        if origin != "AI":
            raise InvalidInputError("Las recomendaciones guardadas deben tener origin='AI'")
        return AiMetadata(
            model=str(payload.get("model") or ""),
            prompt_version=str(payload.get("prompt_version") or ""),
            generated_at=str(payload.get("generated_at") or self._clock.iso_now()),
            disclaimer=str(payload.get("disclaimer") or DEFAULT_AI_DISCLAIMER),
            verified=bool(payload.get("verified", False)),
        )

    def save(self, payload: Mapping[str, Any]) -> AiRecommendation:
        """Guarda una recomendación individual (contrato de `save_recommendation` en MCP)."""
        recommendation = AiRecommendation(
            id=self._ids.new_id("rec"),
            mode=_mode(payload.get("mode")),
            profile_id=str(payload.get("profile_id") or ""),
            job_id=str(payload.get("job_id") or ""),
            content=_clean_content(payload.get("content")),
            items=_items(payload.get("items"), self._max_items),
            summary=str(payload.get("summary") or ""),
            request_id=str(payload.get("request_id") or ""),
            metadata=self._metadata(payload),
            created_at=self._clock.iso_now(),
        )
        return self._repo.save(recommendation)

    def save_batch(self, payload: Mapping[str, Any]) -> list[AiRecommendation]:
        """Guarda el resultado completo de WF-06 (una entrada por oferta o por candidato)."""
        mode = _mode(payload.get("mode"))
        subject_id = str(payload.get("subject_id") or "").strip()
        if not subject_id:
            raise InvalidInputError("subject_id es obligatorio", {"field": "subject_id"})
        entries = payload.get("entries")
        if not isinstance(entries, list):
            raise InvalidInputError("entries debe ser una lista", {"field": "entries"})

        metadata = self._metadata(payload)
        request_id = str(payload.get("request_id") or "")
        summary = str(payload.get("summary") or "")
        saved: list[AiRecommendation] = []
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            if mode is RecommendationMode.STUDENT:
                profile_id, job_id = subject_id, str(entry.get("job_id") or "")
            else:
                profile_id, job_id = str(entry.get("profile_id") or ""), subject_id
            content = _clean_content(entry.get("content", entry))
            content.pop("job_id", None)
            content.pop("profile_id", None)
            saved.append(
                self._repo.save(
                    AiRecommendation(
                        id=self._ids.new_id("rec"),
                        mode=mode,
                        profile_id=profile_id,
                        job_id=job_id,
                        content=content,
                        items=_items(entry.get("items"), self._max_items),
                        summary=summary,
                        request_id=request_id,
                        metadata=metadata,
                        created_at=self._clock.iso_now(),
                    )
                )
            )
        # Si WF-06 se disparó desde otro lado (sin pedido registrado), sólo se guarda.
        if request_id and self._requests.get(request_id) is not None:
            self._update_request(request_id, RequestStatus.COMPLETED)
        return saved

    # ------------------------------------------------------- pedidos a n8n ---

    def request_analysis(self, mode: object, subject_id: str) -> RecommendationRequest:
        parsed = _mode(mode)
        clean = (subject_id or "").strip()
        if not clean:
            field = "profile_id" if parsed is RecommendationMode.STUDENT else "job_id"
            raise InvalidInputError(f"{field} es obligatorio", {"field": field})
        # Falla rápido (404) si el perfil o la oferta no existen.
        if parsed is RecommendationMode.STUDENT:
            self._matching.load_profile(clean)
        else:
            self._matching.load_job(clean)
        now = self._clock.iso_now()
        request = RecommendationRequest(
            id=self._ids.new_id("req"),
            mode=parsed,
            subject_id=clean,
            status=RequestStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        return self._requests.save(request)

    def analysis_limit(self, mode: RecommendationMode, requested: int | None) -> int:
        """Cantidad de ítems que analiza la IA: la configurada por el admin (o menos)."""
        current = self._settings.get()
        configured = (
            current.student_jobs_limit
            if mode is RecommendationMode.STUDENT
            else current.company_candidates_limit
        )
        return RecommendationSettings.effective(requested, configured)

    def run_analysis(self, request_id: str, limit: int | None = None) -> RecommendationRequest:
        """Se ejecuta en segundo plano: llama a WF-06 y actualiza el estado del pedido."""
        request = self.get_request(request_id)
        limit = self.analysis_limit(request.mode, limit)
        self._update_request(request.id, RequestStatus.PROCESSING)
        try:
            self._trigger.request_analysis(
                request_id=request.id,
                mode=request.mode.value,
                subject_id=request.subject_id,
                limit=limit,
            )
        except MatchingError as exc:
            return self._update_request(
                request.id,
                RequestStatus.FAILED,
                {"code": exc.code, "message": exc.message, "details": exc.details},
            )
        current = self.get_request(request.id)
        if current.status is RequestStatus.PROCESSING:
            # WF-06 respondió OK; si no llegó a persistir con request_id, igual se cierra.
            return self._update_request(request.id, RequestStatus.COMPLETED)
        return current

    def get_request(self, request_id: str) -> RecommendationRequest:
        request = self._requests.get(request_id)
        if request is None:
            raise NotFoundError(
                f"Pedido de recomendación '{request_id}' no encontrado",
                {"request_id": request_id},
            )
        return request

    def _update_request(
        self,
        request_id: str,
        status: RequestStatus,
        error: Mapping[str, object] | None = None,
    ) -> RecommendationRequest:
        current = self._requests.get(request_id)
        if current is None:
            raise NotFoundError(
                f"Pedido de recomendación '{request_id}' no encontrado",
                {"request_id": request_id},
            )
        updated = RecommendationRequest(
            id=current.id,
            mode=current.mode,
            subject_id=current.subject_id,
            status=status,
            created_at=current.created_at,
            updated_at=self._clock.iso_now(),
            error=dict(error or {}),
        )
        return self._requests.save(updated)

    # --------------------------------------------------------------- lectura ---

    def _ai_block(
        self, mode: RecommendationMode, subject_id: str, recs: list[AiRecommendation]
    ) -> JsonDict:
        request = self._requests.latest_for(mode.value, subject_id)
        latest = max(recs, key=lambda r: r.created_at) if recs else None
        if request is not None and request.status in (
            RequestStatus.PENDING,
            RequestStatus.PROCESSING,
        ):
            status = request.status.value
        elif latest is not None:
            status = "ready"
        elif request is not None:
            status = request.status.value
        else:
            status = "not_requested"
        block: JsonDict = {
            "origin": "AI",
            "status": status,
            "request_id": request.id if request else "",
            "error": dict(request.error) if request and request.error else None,
            "summary": latest.summary if latest else "",
            "model": latest.metadata.model if latest else "",
            "prompt_version": latest.metadata.prompt_version if latest else "",
            "generated_at": latest.metadata.generated_at if latest else "",
            "disclaimer": latest.metadata.disclaimer if latest else DEFAULT_AI_DISCLAIMER,
            "verified": latest.metadata.verified if latest else False,
        }
        return block

    def student_view(self, profile_id: str, limit: int | None = None) -> JsonDict:
        """Ofertas recomendadas a un estudiante: ranking por reglas + recomendaciones IA."""
        ranking = self._matching.rank_jobs_for_student(profile_id, limit)
        recs = self._repo.latest_for_profile(ranking.profile.id)
        by_job = {r.job_id: r for r in recs}
        ai = self._ai_block(RecommendationMode.STUDENT, ranking.profile.id, recs)
        ai["items"] = [
            {"job_id": item.job.id, **recommendation_to_dict(by_job[item.job.id])}
            for item in ranking.items
            if item.job.id in by_job
        ]
        return {
            "profile_id": ranking.profile.id,
            "rule_based": job_ranking_to_dict(ranking),
            "ai_recommendations": ai,
        }

    def company_view(self, job_id: str, limit: int | None = None) -> JsonDict:
        """Candidatos recomendados para una oferta: ranking por reglas + recomendaciones IA."""
        ranking = self._matching.rank_candidates_for_job(job_id, limit)
        recs = self._repo.latest_for_job(ranking.job.id)
        by_profile = {r.profile_id: r for r in recs}
        ai = self._ai_block(RecommendationMode.COMPANY, ranking.job.id, recs)
        ai["items"] = [
            {"profile_id": item.profile.id, **recommendation_to_dict(by_profile[item.profile.id])}
            for item in ranking.items
            if item.profile.id in by_profile
        ]
        return {
            "job_id": ranking.job.id,
            "rule_based": candidate_ranking_to_dict(ranking),
            "ai_recommendations": ai,
        }
