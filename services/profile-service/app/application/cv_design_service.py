"""Casos de uso del diseño del CV (`/profiles/me/cv-design`, `contracts/profile.md` parte A §9).

- `view`: el diseño que rige, la elección por reglas, la última sugerencia de la IA y el catálogo.
- `request_ai`: pide al agente `cv_designer` de n8n (WF-07) que elija, en segundo plano.
- `choose`: el estudiante fija un diseño o vuelve a la elección automática.
- `resolve`: el diseño con el que `ProfileService.generate_cv` arma el PDF, DOCX y HTML.

La IA sólo recibe un resumen del contenido sin datos personales (`CvContentSummary`) y su
respuesta se vuelve a validar contra el catálogo: nunca genera ni modifica el contenido del CV.
"""

import dataclasses
import logging
import threading
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import timedelta
from typing import Any

from app.domain.auth import Principal, Role
from app.domain.completion import ProfileCompletenessPolicy
from app.domain.cv_design import (
    CV_LAYOUTS,
    CvLayout,
    CvLayoutSelector,
    CvSection,
    EffectiveDesign,
    RuleBasedDesign,
    ai_is_current,
    find_layout,
    normalize_section_order,
    resolve_design,
    summarize_content,
)
from app.domain.cv_design_state import AiCvDesign, AiDesignStatus, CvDesignState, UserCvDesign
from app.domain.errors import (
    AiConsentRequiredError,
    ForbiddenError,
    ProfileDomainError,
    ProfileIncompleteError,
    ProfileNotFoundError,
    UnknownCvLayoutError,
)
from app.domain.ports import Clock, CvDesignGateway, ProfileRepository
from app.domain.profile import StudentProfile
from app.domain.serialization import to_plain

logger = logging.getLogger(__name__)

AI_DISCLAIMER = (
    "Diseño sugerido por IA a partir de un resumen de tu perfil, sin datos personales. "
    "Sólo cambia el orden de las secciones: el contenido es el que confirmaste."
)
# Un pedido que sigue "processing" después de esto se da por perdido (p. ej. reinicio).
DEFAULT_PROCESSING_TIMEOUT = timedelta(minutes=10)

Runner = Callable[[Callable[[], None]], None]


def _thread_runner(task: Callable[[], None]) -> None:
    threading.Thread(target=task, name="cv-design", daemon=True).start()


def _layout_view(layout: CvLayout) -> dict[str, Any]:
    return {
        "id": layout.id,
        "name": layout.name,
        "description": layout.description,
        "best_for": layout.best_for,
        "section_order": [s.value for s in layout.section_order],
    }


def _order(sections: tuple[CvSection, ...]) -> list[str]:
    return [s.value for s in sections]


class CvDesignService:
    def __init__(
        self,
        *,
        repository: ProfileRepository,
        policy: ProfileCompletenessPolicy,
        gateway: CvDesignGateway,
        clock: Clock,
        lock: AbstractContextManager[Any],
        selector: CvLayoutSelector | None = None,
        runner: Runner = _thread_runner,
        processing_timeout: timedelta = DEFAULT_PROCESSING_TIMEOUT,
    ) -> None:
        self._repo = repository
        self._policy = policy
        self._gateway = gateway
        self._clock = clock
        # El mismo lock que ProfileService: el perfil se lee, modifica y guarda entero.
        self._lock = lock
        self._selector = selector or CvLayoutSelector()
        self._run = runner
        self._timeout = processing_timeout

    # ------------------------------------------------------------- estudiante ---

    def view(self, principal: Principal) -> dict[str, Any]:
        return self._view(self._mine(principal))

    def request_ai(self, principal: Principal) -> dict[str, Any]:
        """Dispara WF-07 en segundo plano. Si ya hay un pedido en curso, no lo repite."""
        with self._lock:
            profile = self._mine(principal)
            if not profile.consents.ai_processing:
                raise AiConsentRequiredError()
            self._require_cv_data(profile)
            state = profile.cv_design or CvDesignState()
            if self._in_progress(state.ai):
                return self._view(profile)
            content = summarize_content(profile)
            rules = self._selector.select(content)
            ai = AiCvDesign(
                status=AiDesignStatus.PROCESSING,
                request_id=f"cvd-{uuid.uuid4().hex[:12]}",
                requested_at=self._clock.now(),
                fingerprint=content.fingerprint(),
            )
            profile = self._save(profile, dataclasses.replace(state, ai=ai))
        payload = {
            "request_id": ai.request_id,
            "profile_id": profile.id,
            "content": to_plain(content),
            "rule_based": self._rules_view(rules),
            "catalog": [_layout_view(layout) for layout in CV_LAYOUTS],
            "sections": [s.value for s in CvSection],
        }
        self._run(lambda: self._complete(profile.id, ai.request_id, payload))
        return self._view(profile)

    def choose(self, principal: Principal, layout_id: str | None) -> dict[str, Any]:
        """Fija el diseño elegido por el estudiante; `None` vuelve a la elección automática."""
        user: UserCvDesign | None = None
        if layout_id is not None:
            layout = find_layout(layout_id)
            if layout is None:
                raise UnknownCvLayoutError(layout_id, [x.id for x in CV_LAYOUTS])
            user = UserCvDesign(layout=layout.id, chosen_at=self._clock.now())
        with self._lock:
            profile = self._mine(principal)
            state = profile.cv_design or CvDesignState()
            profile = self._save(profile, dataclasses.replace(state, user=user))
        return self._view(profile)

    # ---------------------------------------------------- generación del CV ---

    def resolve(self, profile: StudentProfile, override: str | None = None) -> EffectiveDesign:
        if override is not None and find_layout(override) is None:
            raise UnknownCvLayoutError(override, [x.id for x in CV_LAYOUTS])
        content = summarize_content(profile)
        return resolve_design(
            profile.cv_design, self._selector.select(content), content.fingerprint(), override
        )

    # ------------------------------------------------------------- internos ---

    def _complete(self, profile_id: str, request_id: str, payload: dict[str, Any]) -> None:
        """Corre fuera del request: llama a n8n y guarda el resultado (o el error)."""
        try:
            suggestion = self._gateway.suggest_design(payload)
            layout = find_layout(suggestion.layout)
            if layout is None:
                raise UnknownCvLayoutError(suggestion.layout, [x.id for x in CV_LAYOUTS])
            changes: dict[str, Any] = {
                "status": AiDesignStatus.COMPLETED,
                "layout": layout.id,
                "section_order": _order(normalize_section_order(suggestion.section_order, layout)),
                "rationale": suggestion.rationale.strip()[:600],
                "model": suggestion.model,
                "prompt_version": suggestion.prompt_version,
                "generated_at": suggestion.generated_at,
                "disclaimer": suggestion.disclaimer or AI_DISCLAIMER,
                "error": None,
            }
        except ProfileDomainError as exc:
            logger.warning("WF-07 no devolvió un diseño de CV (%s): %s", request_id, exc.message)
            changes = {"status": AiDesignStatus.FAILED, "error": exc.message}
        except Exception:
            logger.exception("Error inesperado al pedir el diseño de CV %s", request_id)
            changes = {"status": AiDesignStatus.FAILED, "error": "Error inesperado"}

        with self._lock:
            profile = self._repo.get(profile_id)
            ai = profile.cv_design.ai if profile and profile.cv_design else None
            if profile is None or profile.cv_design is None or ai is None:
                return  # el perfil se borró o se reinició el diseño mientras tanto
            if ai.request_id != request_id:
                return  # hay un pedido más nuevo: éste ya no cuenta
            self._save(
                profile,
                dataclasses.replace(profile.cv_design, ai=dataclasses.replace(ai, **changes)),
            )

    def _view(self, profile: StudentProfile) -> dict[str, Any]:
        content = summarize_content(profile)
        fingerprint = content.fingerprint()
        rules = self._selector.select(content)
        state = profile.cv_design
        effective = resolve_design(state, rules, fingerprint)
        return {
            "profile_id": profile.id,
            "effective": {
                **_layout_view(effective.layout),
                "section_order": _order(effective.section_order),
                "source": effective.source.value,
            },
            "rule_based": self._rules_view(rules),
            "ai_recommendation": self._ai_view(state.ai if state else None, state, fingerprint),
            "user_choice": (
                {"layout": state.user.layout, "chosen_at": to_plain(state.user.chosen_at)}
                if state and state.user
                else None
            ),
            "catalog": [_layout_view(layout) for layout in CV_LAYOUTS],
        }

    @staticmethod
    def _rules_view(rules: RuleBasedDesign) -> dict[str, Any]:
        return {
            "origin": "RULES",
            "engine_version": rules.engine_version,
            "layout": rules.layout.id,
            "section_order": _order(rules.section_order),
            "reasons": list(rules.reasons),
        }

    def _ai_view(
        self, ai: AiCvDesign | None, state: CvDesignState | None, fingerprint: str
    ) -> dict[str, Any] | None:
        if ai is None:
            return None
        status = ai.status
        error = ai.error
        if status is AiDesignStatus.PROCESSING and not self._in_progress(ai):
            status, error = AiDesignStatus.FAILED, "El pedido tardó demasiado. Probá de nuevo."
        return {
            "origin": "AI",
            "status": status.value,
            "request_id": ai.request_id,
            "requested_at": to_plain(ai.requested_at),
            "layout": ai.layout,
            "section_order": list(ai.section_order),
            "rationale": ai.rationale,
            "model": ai.model,
            "prompt_version": ai.prompt_version,
            "generated_at": to_plain(ai.generated_at),
            "disclaimer": ai.disclaimer or AI_DISCLAIMER,
            # Completa pero sobre un perfil que ya cambió: no rige hasta pedirla de nuevo.
            "stale": status is AiDesignStatus.COMPLETED and not ai_is_current(state, fingerprint),
            "error": error,
        }

    def _in_progress(self, ai: AiCvDesign | None) -> bool:
        return (
            ai is not None
            and ai.status is AiDesignStatus.PROCESSING
            and self._clock.now() - ai.requested_at < self._timeout
        )

    def _require_cv_data(self, profile: StudentProfile) -> None:
        completion = self._policy.evaluate(profile)
        if completion.can_generate_cv:
            return
        missing = [
            {"field": m.field, "step": m.step.value, "message": m.message}
            for m in completion.missing
            if m.required and m.step.value == "cv"
        ]
        raise ProfileIncompleteError("Completá los datos del CV antes de elegir un diseño", missing)

    def _save(self, profile: StudentProfile, state: CvDesignState) -> StudentProfile:
        updated = dataclasses.replace(profile, cv_design=state)
        self._repo.update(updated)
        return updated

    def _mine(self, principal: Principal) -> StudentProfile:
        if principal.role is not Role.STUDENT:
            raise ForbiddenError("Sólo los estudiantes tienen perfil")
        profile = self._repo.get_by_user(principal.subject)
        if profile is None:
            raise ProfileNotFoundError()
        return profile
