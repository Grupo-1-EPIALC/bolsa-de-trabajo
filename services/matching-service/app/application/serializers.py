"""Serialización de resultados del dominio a JSON de contrato.

- `match_to_dict`: bloque `rule_based` (`origin = "RULES"`) de §7 del contrato, respetando la
  visibilidad del sueldo según quién mira (`viewer`).
- `profile_snapshot` / `job_snapshot`: vistas sin datos personales sensibles (sin nombre,
  email, teléfono ni dirección; AGENTS.md §5.5). Son las que n8n le pasa al LLM.
"""

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from app.domain.models import (
    ConditionCheckResult,
    HoursRange,
    JobOpportunity,
    MatchResult,
    SalaryFit,
    SalaryRange,
    StudentProfile,
    WorkConditions,
)
from app.domain.recommendations import AiRecommendation

if TYPE_CHECKING:
    from app.application.matching_service import CandidateRanking, JobRanking

JsonDict = dict[str, Any]

VIEWER_STUDENT = "student"
VIEWER_COMPANY = "company"
VIEWER_INTERNAL = "internal"


def _range(value: HoursRange | None) -> JsonDict | None:
    return None if value is None else {"min": value.min, "max": value.max}


def _salary_fit(fit: SalaryFit | None, hide_expected: bool, hide_offered: bool) -> JsonDict | None:
    if fit is None:
        return None
    return {
        "result": fit.result.value,
        "expected_monthly": None if hide_expected else _range(fit.expected_monthly),
        "offered_monthly": None if hide_offered else _range(fit.offered_monthly),
        "gap_percent": fit.gap_percent,
        "currency": fit.currency,
    }


def _check(check: ConditionCheckResult) -> JsonDict:
    details = {k: v for k, v in check.details.items() if k != "salary_fit"}
    return {
        "condition": check.condition,
        "result": check.result.value,
        "hard": check.hard,
        "profile_value": check.profile_value,
        "job_value": check.job_value,
        "details": details,
    }


def _is_hidden(salary: SalaryRange | None) -> bool:
    return salary is not None and salary.visibility == "hidden"


def match_to_dict(
    result: MatchResult,
    profile: StudentProfile | None = None,
    job: JobOpportunity | None = None,
    viewer: str = VIEWER_INTERNAL,
) -> JsonDict:
    """Bloque calculado por reglas. Oculta montos de sueldo que la otra parte marcó `hidden`."""
    p_salary = profile.work_conditions.salary if profile else None
    j_salary = job.work_conditions.salary if job else None
    hide_expected = viewer == VIEWER_COMPANY and _is_hidden(p_salary)
    hide_offered = viewer == VIEWER_STUDENT and _is_hidden(j_salary)
    fit = result.conditions_fit
    return {
        "origin": "RULES",
        "engine_version": result.engine_version,
        "rules_version": result.rules_version,
        "computed_at": result.computed_at,
        "profile_id": result.profile_id,
        "job_id": result.job_id,
        "score": result.score,
        "excluding_cap_applied": result.excluding_cap_applied,
        "breakdown": [
            {
                "criterion": c.criterion,
                "weight": c.weight,
                "earned": c.earned,
                "details": dict(c.details),
            }
            for c in result.breakdown
        ],
        "missing_skills": [
            {
                "skill": m.skill,
                "kind": m.kind.value,
                "required_level": m.required_level,
                "current_level": m.current_level,
                "gap": m.gap,
                "priority": m.priority.value,
            }
            for m in result.missing_skills
        ],
        "matched_skills": [
            {
                "skill": m.skill,
                "kind": m.kind.value,
                "profile_level": m.profile_level,
                "required_level": m.required_level,
            }
            for m in result.matched_skills
        ],
        "conditions_fit": {
            "compatible": fit.compatible,
            "distance_km": fit.distance_km,
            "checks": [_check(c) for c in fit.checks],
            "salary_fit": _salary_fit(fit.salary_fit, hide_expected, hide_offered),
        },
    }


def _conditions_summary(wc: WorkConditions) -> JsonDict:
    return {
        "work_schedule": sorted(wc.work_schedule),
        "work_modality": sorted(wc.work_modality),
        "hybrid_onsite_days": wc.hybrid_onsite_days,
        "employment_type": sorted(wc.employment_type),
        "contract_duration": sorted(wc.contract_duration),
        "weekly_hours": asdict(wc.weekly_hours) if wc.weekly_hours else None,
        "shifts": sorted(wc.shifts),
        "availability_start": wc.availability_start,
        "travel_availability": wc.travel_availability,
    }


def profile_snapshot(profile: StudentProfile) -> JsonDict:
    return {
        "profile_id": profile.id,
        "headline": profile.headline,
        "location": {
            "city": profile.location.city,
            "province": profile.location.province,
            "country": profile.location.country,
        },
        "years_experience": profile.years_experience,
        "skills": [{"name": s.name, "level": s.level} for s in profile.skills],
        "languages": [{"name": lang.name, "level": lang.level} for lang in profile.languages],
        "education": [
            {"level": e.level, "status": e.status, "degree": e.degree, "field": e.field}
            for e in profile.education
        ],
        "academic_status": {
            "career": profile.academic.career,
            "current_year": profile.academic.current_year,
            "progress_percent": profile.academic.progress_percent,
        },
        "target_roles": list(profile.target_roles),
        "work_conditions": _conditions_summary(profile.work_conditions),
    }


def job_snapshot(job: JobOpportunity) -> JsonDict:
    return {
        "job_id": job.id,
        "title": job.title,
        # Para abrir el perfil público de la empresa (GET /profiles/companies/{company_id}).
        "company_id": job.company_id,
        "company_name": job.company_name,
        "seniority": job.seniority,
        "location": {
            "city": job.location.city,
            "province": job.location.province,
            "country": job.location.country,
        },
        "requirements": {
            "skills": [
                {"name": s.name, "level": s.level, "kind": s.kind.value} for s in job.skills
            ],
            "languages": [
                {"name": lang.name, "level": lang.level, "kind": lang.kind.value}
                for lang in job.languages
            ],
            "experience": {"min_years": job.experience.min_years, "area": job.experience.area},
            "academic": {
                "careers": list(job.academic.careers),
                "min_progress_percent": job.academic.min_progress_percent,
                "min_current_year": job.academic.min_current_year,
            },
        },
        "work_conditions": _conditions_summary(job.work_conditions),
    }


def recommendation_to_dict(rec: AiRecommendation) -> JsonDict:
    return {
        "id": rec.id,
        "origin": rec.origin,
        "mode": rec.mode.value,
        "profile_id": rec.profile_id,
        "job_id": rec.job_id,
        "request_id": rec.request_id,
        "summary": rec.summary,
        "content": dict(rec.content),
        "items": [dict(i) for i in rec.items],
        "model": rec.metadata.model,
        "prompt_version": rec.metadata.prompt_version,
        "generated_at": rec.metadata.generated_at,
        "disclaimer": rec.metadata.disclaimer,
        "verified": rec.metadata.verified,
        "created_at": rec.created_at,
    }


def job_ranking_to_dict(ranking: "JobRanking") -> JsonDict:
    """Ofertas rankeadas por reglas para un estudiante (vista del estudiante)."""
    return {
        "origin": "RULES",
        "profile_id": ranking.profile.id,
        "profile": profile_snapshot(ranking.profile),
        "engine_version": ranking.items[0].result.engine_version if ranking.items else "",
        "rules_version": ranking.items[0].result.rules_version if ranking.items else "",
        "evaluated": ranking.evaluated,
        "excluded_incompatible": ranking.excluded_incompatible,
        "items": [
            {
                "rank": pos,
                "job": job_snapshot(item.job),
                "match": match_to_dict(item.result, ranking.profile, item.job, VIEWER_STUDENT),
            }
            for pos, item in enumerate(ranking.items, start=1)
        ],
    }


def candidate_ranking_to_dict(ranking: "CandidateRanking") -> JsonDict:
    """Candidatos rankeados por reglas para una oferta (vista de la empresa)."""
    return {
        "origin": "RULES",
        "job_id": ranking.job.id,
        "job": job_snapshot(ranking.job),
        "engine_version": ranking.items[0].result.engine_version if ranking.items else "",
        "rules_version": ranking.items[0].result.rules_version if ranking.items else "",
        "evaluated": ranking.evaluated,
        "excluded_incompatible": ranking.excluded_incompatible,
        "items": [
            {
                "rank": pos,
                "candidate": profile_snapshot(item.profile),
                "match": match_to_dict(item.result, item.profile, ranking.job, VIEWER_COMPANY),
            }
            for pos, item in enumerate(ranking.items, start=1)
        ],
    }
