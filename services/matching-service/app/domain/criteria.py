"""Criterios de scoring por reglas (un criterio por clase, OCP — AGENTS.md §4.4).

Pesos por defecto: RequiredSkills 40 · DesiredSkills 10 · Levels 10 · Experience 25 ·
Education 5 · Languages 3 · Conditions 7 (configurables en `scoring_rules.yaml`).
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

from app.domain.models import (
    CheckOutcome,
    CriterionResult,
    JobOpportunity,
    RequirementKind,
    StudentProfile,
)
from app.domain.scales import education_level_rank, education_status_rank, language_rank
from app.domain.skill_dictionary import EXACT_ONLY, SkillDictionary

if TYPE_CHECKING:
    from app.domain.conditions import ConditionCheck


class ScoringCriterion(Protocol):
    name: str

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> CriterionResult: ...


def _ratio_result(name: str, weight: float, ratio: float, **details: object) -> CriterionResult:
    bounded = max(0.0, min(1.0, ratio))
    return CriterionResult(
        criterion=name, weight=weight, earned=round(bounded * weight, 2), details=dict(details)
    )


def _skill_credit(
    skills: SkillDictionary, have: dict[str, int], wanted: list[str]
) -> tuple[float, int, int]:
    """Suma de crédito (1 si la tiene, el `credit` del grupo si sabe una similar), cuántas
    cubre del todo y cuántas sólo con una similar."""
    total, full, similar = 0.0, 0, 0
    for key in wanted:
        cov = skills.coverage(have, key)
        if cov is None:
            continue
        total += cov.credit
        if cov.full:
            full += 1
        else:
            similar += 1
    return total, full, similar


class RequiredSkillsCriterion:
    """Proporción de skills obligatorias (`required` y `excluding`) que el estudiante tiene.

    Con el diccionario: un alias, una equivalente o una skill que la implica cuentan entera;
    una herramienta similar cuenta su `credit` (ej. GitHub para GitLab, 0,75).
    """

    name = "required_skills"

    def __init__(self, weight: float, skills: SkillDictionary = EXACT_ONLY) -> None:
        self._weight = weight
        self._skills = skills

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> CriterionResult:
        required = job.skills_of(RequirementKind.REQUIRED, RequirementKind.EXCLUDING)
        if not required:
            return _ratio_result(self.name, self._weight, 1.0, required=0, matched=0)
        keys = [s.normalized for s in required]
        credit, full, similar = _skill_credit(self._skills, profile.skill_levels(), keys)
        return _ratio_result(
            self.name,
            self._weight,
            credit / len(required),
            required=len(required),
            matched=full,
            similar=similar,
        )


class DesiredSkillsCriterion:
    """Proporción de skills deseables cubiertas (mismo criterio). Sin deseables, completo."""

    name = "desired_skills"

    def __init__(self, weight: float, skills: SkillDictionary = EXACT_ONLY) -> None:
        self._weight = weight
        self._skills = skills

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> CriterionResult:
        desired = job.skills_of(RequirementKind.DESIRED)
        if not desired:
            return _ratio_result(self.name, self._weight, 1.0, desired=0, matched=0)
        keys = [s.normalized for s in desired]
        credit, full, similar = _skill_credit(self._skills, profile.skill_levels(), keys)
        return _ratio_result(
            self.name,
            self._weight,
            credit / len(desired),
            desired=len(desired),
            matched=full,
            similar=similar,
        )


class LevelsCriterion:
    """Promedio de `min(1, nivel_estudiante / nivel_pedido)` sobre las skills que cubre del
    todo (la misma, un alias, una equivalente o una que la implica, con el nivel de esa)."""

    name = "levels"

    def __init__(self, weight: float, skills: SkillDictionary = EXACT_ONLY) -> None:
        self._weight = weight
        self._skills = skills

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> CriterionResult:
        if not job.skills:
            return _ratio_result(self.name, self._weight, 1.0, compared=0)
        have = profile.skill_levels()
        ratios = []
        for s in job.skills:
            cov = self._skills.coverage(have, s.normalized)
            if cov is not None and cov.full:
                ratios.append(min(1.0, cov.level / max(1, s.level)))
        if not ratios:
            return _ratio_result(self.name, self._weight, 0.0, compared=0)
        return _ratio_result(
            self.name, self._weight, sum(ratios) / len(ratios), compared=len(ratios)
        )


class ExperienceCriterion:
    """Experiencia: años frente al mínimo pedido y si se usaron las competencias de la oferta.

    - Años: `años / mínimo` (tope 1). Si la oferta no pide mínimo, se compara contra
      `reference_years` y la falta de experiencia resta la mitad de esa parte, no toda.
    - Relevancia (`relevance_share` del criterio): cuántas competencias de la oferta aparecen
      en `skills_used` de la experiencia (con 3 ya es completa). Si hay experiencia sin
      competencias cargadas, cuenta la mitad.
    """

    name = "experience"
    _RELEVANT_SKILLS_FOR_FULL_CREDIT = 3

    def __init__(
        self,
        weight: float,
        reference_years: float = 1.0,
        relevance_share: float = 0.4,
        skills: SkillDictionary = EXACT_ONLY,
    ) -> None:
        self._weight = weight
        self._reference_years = reference_years
        self._relevance_share = relevance_share
        self._skills = skills

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> CriterionResult:
        min_years = job.experience.min_years
        years = profile.years_experience
        if min_years > 0:
            years_fit = min(1.0, years / min_years)
        else:
            years_fit = 0.5 + 0.5 * min(1.0, years / self._reference_years)
        relevance, relevant = self._relevance(profile, job)
        share = self._relevance_share
        return _ratio_result(
            self.name,
            self._weight,
            (1 - share) * years_fit + share * relevance,
            min_years=min_years,
            profile_years=years,
            years_fit=round(years_fit, 3),
            relevance=round(relevance, 3),
            relevant_skills=relevant,
        )

    def _relevance(self, profile: StudentProfile, job: JobOpportunity) -> tuple[float, list[str]]:
        job_skills = {s.normalized: s.name for s in job.skills}
        if profile.years_experience <= 0 and not profile.experience_skills:
            return 0.0, []
        if not job_skills:
            return 1.0, []
        if not profile.experience_skills:
            return 0.5, []
        used = {k: 1 for k in profile.experience_skills}
        relevant = sorted(
            name
            for k, name in job_skills.items()
            if (cov := self._skills.coverage(used, k)) is not None and cov.full
        )
        needed = min(len(job_skills), self._RELEVANT_SKILLS_FOR_FULL_CREDIT)
        return min(1.0, len(relevant) / needed), relevant


class EducationCriterion:
    """Mejor formación del estudiante frente a la mínima pedida (nivel y estado)."""

    name = "education"

    def __init__(self, weight: float) -> None:
        self._weight = weight

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> CriterionResult:
        requirements = [e for e in job.education if education_level_rank(e.level) is not None]
        if not requirements:
            return _ratio_result(self.name, self._weight, 1.0, required=False)
        best = 0.0
        for req in requirements:
            req_rank = education_level_rank(req.level) or 0
            req_status = education_status_rank(req.status or "in_progress")
            for edu in profile.education:
                have_rank = education_level_rank(edu.level)
                if have_rank is None:
                    continue
                if have_rank > req_rank:
                    best = 1.0
                elif have_rank == req_rank:
                    if education_status_rank(edu.status) >= req_status:
                        best = max(best, 1.0)
                    else:
                        best = max(best, 0.5)
        return _ratio_result(self.name, self._weight, best, required=True)


class LanguagesCriterion:
    """Idiomas pedidos: crédito completo si alcanza el nivel, medio si lo tiene por debajo."""

    name = "languages"

    def __init__(self, weight: float) -> None:
        self._weight = weight

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> CriterionResult:
        if not job.languages:
            return _ratio_result(self.name, self._weight, 1.0, required=0)
        have = {lang.normalized: language_rank(lang.level) for lang in profile.languages}
        credit = 0.0
        for req in job.languages:
            if req.normalized not in have:
                continue
            needed = language_rank(req.level)
            credit += 1.0 if have[req.normalized] >= needed else 0.5
        return _ratio_result(
            self.name, self._weight, credit / len(job.languages), required=len(job.languages)
        )


_CONDITION_CREDIT = {CheckOutcome.MATCH: 1.0, CheckOutcome.PARTIAL: 0.5, CheckOutcome.MISMATCH: 0.0}


class ConditionsCriterion:
    """Condiciones laborales (modalidad, horario, ubicación, disponibilidad...) con poco peso.

    Promedio de las condiciones con dato en los dos lados: coincide = 1, parcial = 0,5 y
    no coincide = 0. Las `unknown` no cuentan; sin ninguna comparable, puntaje completo.
    """

    name = "conditions"

    def __init__(self, weight: float, checks: Sequence["ConditionCheck"]) -> None:
        self._weight = weight
        self._checks = list(checks)

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> CriterionResult:
        outcomes = [check.evaluate(profile, job).result for check in self._checks]
        known = [o for o in outcomes if o in _CONDITION_CREDIT]
        if not known:
            return _ratio_result(self.name, self._weight, 1.0, compared=0)
        return _ratio_result(
            self.name,
            self._weight,
            sum(_CONDITION_CREDIT[o] for o in known) / len(known),
            compared=len(known),
            matched=sum(1 for o in known if o is CheckOutcome.MATCH),
            partial=sum(1 for o in known if o is CheckOutcome.PARTIAL),
            mismatched=sum(1 for o in known if o is CheckOutcome.MISMATCH),
        )
