"""Criterios de scoring por reglas (un criterio por clase, OCP — AGENTS.md §4.4).

Pesos por defecto: RequiredSkills 50 · DesiredSkills 15 · Levels 15 · Experience 10 ·
Education 5 · Languages 5 (configurables en `scoring_rules.yaml`).
"""

from typing import Protocol

from app.domain.models import (
    CriterionResult,
    JobOpportunity,
    RequirementKind,
    StudentProfile,
)
from app.domain.scales import education_level_rank, education_status_rank, language_rank


class ScoringCriterion(Protocol):
    name: str

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> CriterionResult: ...


def _ratio_result(name: str, weight: float, ratio: float, **details: object) -> CriterionResult:
    bounded = max(0.0, min(1.0, ratio))
    return CriterionResult(
        criterion=name, weight=weight, earned=round(bounded * weight, 2), details=dict(details)
    )


class RequiredSkillsCriterion:
    """Proporción de skills obligatorias (`required` y `excluding`) que el estudiante tiene."""

    name = "required_skills"

    def __init__(self, weight: float) -> None:
        self._weight = weight

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> CriterionResult:
        required = job.skills_of(RequirementKind.REQUIRED, RequirementKind.EXCLUDING)
        if not required:
            return _ratio_result(self.name, self._weight, 1.0, required=0, matched=0)
        have = profile.skill_levels()
        matched = [s.normalized for s in required if s.normalized in have]
        return _ratio_result(
            self.name,
            self._weight,
            len(matched) / len(required),
            required=len(required),
            matched=len(matched),
        )


class DesiredSkillsCriterion:
    """Proporción de skills deseables cubiertas. Sin deseables, puntaje completo."""

    name = "desired_skills"

    def __init__(self, weight: float) -> None:
        self._weight = weight

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> CriterionResult:
        desired = job.skills_of(RequirementKind.DESIRED)
        if not desired:
            return _ratio_result(self.name, self._weight, 1.0, desired=0, matched=0)
        have = profile.skill_levels()
        matched = [s.normalized for s in desired if s.normalized in have]
        return _ratio_result(
            self.name,
            self._weight,
            len(matched) / len(desired),
            desired=len(desired),
            matched=len(matched),
        )


class LevelsCriterion:
    """Promedio de `min(1, nivel_estudiante / nivel_pedido)` sobre las skills que coinciden."""

    name = "levels"

    def __init__(self, weight: float) -> None:
        self._weight = weight

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> CriterionResult:
        if not job.skills:
            return _ratio_result(self.name, self._weight, 1.0, compared=0)
        have = profile.skill_levels()
        ratios = [
            min(1.0, have[s.normalized] / max(1, s.level))
            for s in job.skills
            if s.normalized in have
        ]
        if not ratios:
            return _ratio_result(self.name, self._weight, 0.0, compared=0)
        return _ratio_result(
            self.name, self._weight, sum(ratios) / len(ratios), compared=len(ratios)
        )


class ExperienceCriterion:
    """Años de experiencia del estudiante frente al mínimo pedido."""

    name = "experience"

    def __init__(self, weight: float) -> None:
        self._weight = weight

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> CriterionResult:
        min_years = job.experience.min_years
        if min_years <= 0:
            return _ratio_result(self.name, self._weight, 1.0, min_years=0)
        return _ratio_result(
            self.name,
            self._weight,
            profile.years_experience / min_years,
            min_years=min_years,
            profile_years=profile.years_experience,
        )


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
