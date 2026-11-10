"""`MissingSkillsAnalyzer`: brechas de skills y de nivel ordenadas por prioridad."""

from app.domain.models import (
    JobOpportunity,
    MatchedSkill,
    MissingSkill,
    Priority,
    RequirementKind,
    StudentProfile,
)
from app.domain.skill_dictionary import EXACT_ONLY, SkillDictionary, SkillRelation

_PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
_KIND_ORDER = {
    RequirementKind.EXCLUDING: 0,
    RequirementKind.REQUIRED: 1,
    RequirementKind.DESIRED: 2,
}


class MissingSkillsAnalyzer:
    """Skill ausente obligatoria/excluyente => alta · deseable ausente => media ·
    brecha de nivel en obligatoria => media · en deseable => baja.

    Con el diccionario, la cubren un alias, una equivalente o una skill que la implica (con su
    nivel). Si sólo sabe una herramienta similar, sigue faltando pero se informa en
    `similar_to` porque le va a facilitar aprenderla.
    """

    def __init__(self, skills: SkillDictionary = EXACT_ONLY) -> None:
        self._skills = skills

    def analyze(self, profile: StudentProfile, job: JobOpportunity) -> list[MissingSkill]:
        have = profile.skill_levels()
        names = _profile_names(profile)
        gaps: list[MissingSkill] = []
        for req in job.skills:
            cov = self._skills.coverage(have, req.normalized)
            current = cov.level if cov is not None and cov.full else 0
            if current >= req.level:
                continue
            similar = cov if cov is not None and cov.relation is SkillRelation.SIMILAR else None
            gaps.append(
                MissingSkill(
                    skill=req.name,
                    kind=req.kind,
                    required_level=req.level,
                    current_level=current,
                    gap=req.level - current,
                    priority=self._priority(req.kind, absent=current == 0),
                    similar_to=names.get(similar.via, similar.via) if similar else "",
                    credit=similar.credit if similar else 0.0,
                )
            )
        gaps.sort(key=lambda g: (_PRIORITY_ORDER[g.priority], _KIND_ORDER[g.kind], -g.gap, g.skill))
        return gaps

    def matched(self, profile: StudentProfile, job: JobOpportunity) -> list[MatchedSkill]:
        have = profile.skill_levels()
        names = _profile_names(profile)
        result: list[MatchedSkill] = []
        for req in job.skills:
            cov = self._skills.coverage(have, req.normalized)
            if cov is None or not cov.full:
                continue
            exact = cov.relation is SkillRelation.EXACT
            result.append(
                MatchedSkill(
                    skill=req.name,
                    kind=req.kind,
                    profile_level=cov.level,
                    required_level=req.level,
                    via="" if exact else names.get(cov.via, cov.via),
                    relation=cov.relation.value,
                )
            )
        return result

    @staticmethod
    def _priority(kind: RequirementKind, absent: bool) -> Priority:
        if kind is RequirementKind.DESIRED:
            return Priority.MEDIUM if absent else Priority.LOW
        return Priority.HIGH if absent else Priority.MEDIUM


def _profile_names(profile: StudentProfile) -> dict[str, str]:
    """Clave normalizada → nombre como lo escribió el estudiante."""
    return {s.normalized: s.name for s in profile.skills}
