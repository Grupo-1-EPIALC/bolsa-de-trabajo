"""Qué ve cada quien del perfil (minimización de datos, AGENTS.md §5.5).

- owner (el estudiante dueño): todo.
- admin: todo menos `inclusion`.
- service (matching / mcp-tools / n8n): sin `inclusion`, teléfono, año de nacimiento,
  archivos ni sugerencias de CV, ni consentimientos. Suma `years_experience`.
- company (perfil público): lo de service, sin email y sin sueldo salvo `visibility=public`.
"""

from typing import Any

from app.domain.completion import COMPLETION_ENGINE_VERSION, Completion
from app.domain.enums import SalaryVisibility
from app.domain.profile import StudentProfile
from app.domain.serialization import drop_none, to_plain


def completion_to_dict(completion: Completion) -> dict[str, Any]:
    return {
        "origin": "RULES",
        "engine_version": COMPLETION_ENGINE_VERSION,
        "percent": completion.percent,
        "status": completion.status.value,
        "can_generate_cv": completion.can_generate_cv,
        "steps": [
            {
                "step": s.step.value,
                "complete": s.complete,
                "missing_required": s.missing_required,
                "missing_recommended": s.missing_recommended,
            }
            for s in completion.steps
        ],
        "missing": [
            {"field": m.field, "step": m.step.value, "required": m.required, "message": m.message}
            for m in completion.missing
        ],
    }


def owner_view(profile: StudentProfile, completion: Completion) -> dict[str, Any]:
    body: dict[str, Any] = drop_none(to_plain(profile))
    body["completion"] = completion_to_dict(completion)
    body["has_cv_suggestions"] = profile.cv_suggestions is not None
    body.pop("cv_suggestions", None)  # se piden aparte: GET /profiles/me/cv-suggestions
    body.pop("cv_design", None)  # se pide aparte: GET /profiles/me/cv-design
    return body


def admin_view(profile: StudentProfile, completion: Completion) -> dict[str, Any]:
    body = owner_view(profile, completion)
    body.pop("inclusion", None)
    return body


def service_view(profile: StudentProfile) -> dict[str, Any]:
    body: dict[str, Any] = drop_none(to_plain(profile))
    for key in ("inclusion", "cv_files", "cv_suggestions", "cv_design", "consents"):
        body.pop(key, None)
    personal = body.get("personal", {})
    personal.pop("phone", None)
    personal.pop("birth_year", None)
    # Años de experiencia calculados por reglas (matching-service los usa tal cual).
    months = sum(e.months or 0 for e in profile.experience)
    body["years_experience"] = round(months / 12, 2)
    # Sólo el permiso de contacto (no el resto de los consentimientos): n8n lo usa para no
    # mandar mails a quien no los aceptó (WF-02/WF-03, contracts/n8n.md §7).
    body["contact_by_email"] = profile.consents.contact_by_email
    return body


def company_view(profile: StudentProfile) -> dict[str, Any]:
    body = service_view(profile)
    body.get("personal", {}).pop("email", None)
    salary = profile.work_conditions.salary
    if salary is not None and salary.visibility is not SalaryVisibility.PUBLIC:
        body.get("work_conditions", {}).pop("salary", None)
    for key in ("version", "created_at", "visibility", "contact_by_email"):
        body.pop(key, None)
    return body
