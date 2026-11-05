"""`MissingSkillsAnalyzer`: brechas de skills y de nivel ordenadas por prioridad."""

from app.domain.models import (
    JobOpportunity,
    MatchedSkill,
    MissingSkill,
    Priority,
    RequirementKind,
    StudentProfile,
)

_PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
_KIND_ORDER = {
    RequirementKind.EXCLUDING: 0,
    RequirementKind.REQUIRED: 1,
    RequirementKind.DESIRED: 2,
}


class MissingSkillsAnalyzer:
    """Skill ausente obligatoria/excluyente => alta · deseable ausente => media ·
    brecha de nivel en obligatoria => media · en deseable => baja."""

    def analyze(self, profile: StudentProfile, job: JobOpportunity) -> list[MissingSkill]:
        have = profile.skill_levels()
        gaps: list[MissingSkill] = []
        for req in job.skills:
            current = have.get(req.normalized, 0)
            if current >= req.level:
                continue
            gaps.append(
                MissingSkill(
                    skill=req.name,
                    kind=req.kind,
                    required_level=req.level,
                    current_level=current,
                    gap=req.level - current,
                    priority=self._priority(req.kind, absent=current == 0),
                )
            )
        gaps.sort(key=lambda g: (_PRIORITY_ORDER[g.priority], _KIND_ORDER[g.kind], -g.gap, g.skill))
        return gaps

    def matched(self, profile: StudentProfile, job: JobOpportunity) -> list[MatchedSkill]:
        have = profile.skill_levels()
        return [
            MatchedSkill(
                skill=req.name,
                kind=req.kind,
                profile_level=have[req.normalized],
                required_level=req.level,
            )
            for req in job.skills
            if req.normalized in have
        ]

    @staticmethod
    def _priority(kind: RequirementKind, absent: bool) -> Priority:
        if kind is RequirementKind.DESIRED:
            return Priority.MEDIUM if absent else Priority.LOW
        return Priority.HIGH if absent else Priority.MEDIUM
