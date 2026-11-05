"""Motor de matching por reglas (`origin = "RULES"`).

Suma los criterios de scoring, aplica la regla excluyente (tope de 40 si falta una skill
`excluding`), calcula skills faltantes y evalúa las condiciones laborales por separado.
"""

from collections.abc import Callable, Sequence

from app.domain.conditions import (
    AcademicCheck,
    AvailabilityStartCheck,
    ConditionCheck,
    ContractDurationCheck,
    DriverLicenseCheck,
    EmploymentTypeCheck,
    LocationCheck,
    SalaryCheck,
    ShiftsCheck,
    TravelCheck,
    WorkAuthorizationCheck,
    WorkModalityCheck,
    WorkScheduleCheck,
)
from app.domain.criteria import (
    DesiredSkillsCriterion,
    EducationCriterion,
    ExperienceCriterion,
    LanguagesCriterion,
    LevelsCriterion,
    RequiredSkillsCriterion,
    ScoringCriterion,
)
from app.domain.missing_skills import MissingSkillsAnalyzer
from app.domain.models import (
    CheckOutcome,
    ConditionsFit,
    JobOpportunity,
    MatchResult,
    RequirementKind,
    SalaryFit,
    StudentProfile,
)
from app.domain.rules import ScoringRules
from app.domain.salary import SalaryComparator

ENGINE_VERSION = "1.0.0"


class MatchingEngine:
    def __init__(
        self,
        criteria: Sequence[ScoringCriterion],
        checks: Sequence[ConditionCheck],
        analyzer: MissingSkillsAnalyzer,
        rules: ScoringRules,
        clock: Callable[[], str],
    ) -> None:
        self._criteria = list(criteria)
        self._checks = list(checks)
        self._analyzer = analyzer
        self._rules = rules
        self._clock = clock

    @property
    def rules(self) -> ScoringRules:
        return self._rules

    def match(self, profile: StudentProfile, job: JobOpportunity) -> MatchResult:
        breakdown = tuple(c.evaluate(profile, job) for c in self._criteria)
        raw_total = sum(r.earned for r in breakdown)

        have = profile.skill_levels()
        missing_excluding = any(
            s.normalized not in have for s in job.skills_of(RequirementKind.EXCLUDING)
        )
        score = min(raw_total, self._rules.excluding_cap) if missing_excluding else raw_total

        return MatchResult(
            profile_id=profile.id,
            job_id=job.id,
            score=round(min(100.0, score), 2),
            excluding_cap_applied=missing_excluding,
            breakdown=breakdown,
            missing_skills=tuple(self._analyzer.analyze(profile, job)),
            matched_skills=tuple(self._analyzer.matched(profile, job)),
            conditions_fit=self._conditions(profile, job),
            engine_version=ENGINE_VERSION,
            rules_version=self._rules.version,
            computed_at=self._clock(),
        )

    def _conditions(self, profile: StudentProfile, job: JobOpportunity) -> ConditionsFit:
        results = tuple(check.evaluate(profile, job) for check in self._checks)
        compatible = not any(r.hard and r.result is CheckOutcome.MISMATCH for r in results)
        distance: float | None = None
        salary_fit: SalaryFit | None = None
        for r in results:
            value = r.details.get("distance_km")
            if isinstance(value, int | float):
                distance = float(value)
            fit = r.details.get("salary_fit")
            if isinstance(fit, SalaryFit):
                salary_fit = fit
        return ConditionsFit(compatible, results, distance, salary_fit)


def build_engine(rules: ScoringRules, clock: Callable[[], str]) -> MatchingEngine:
    """Arma el motor con los criterios y las condiciones habilitadas en `rules`."""
    criteria: list[ScoringCriterion] = [
        RequiredSkillsCriterion(rules.weight("required_skills")),
        DesiredSkillsCriterion(rules.weight("desired_skills")),
        LevelsCriterion(rules.weight("levels")),
        ExperienceCriterion(rules.weight("experience")),
        EducationCriterion(rules.weight("education")),
        LanguagesCriterion(rules.weight("languages")),
    ]
    comparator = SalaryComparator(rules.salary)
    factories: dict[str, Callable[[bool], ConditionCheck]] = {
        "work_modality": WorkModalityCheck,
        "location": LocationCheck,
        "work_schedule": WorkScheduleCheck,
        "shifts": ShiftsCheck,
        "employment_type": EmploymentTypeCheck,
        "contract_duration": ContractDurationCheck,
        "availability_start": AvailabilityStartCheck,
        "salary": lambda hard: SalaryCheck(hard, comparator),
        "travel": TravelCheck,
        "driver_license": DriverLicenseCheck,
        "work_authorization": WorkAuthorizationCheck,
        "academic": AcademicCheck,
    }
    checks = [
        factory(rules.condition(name).hard)
        for name, factory in factories.items()
        if rules.condition(name).enabled
    ]
    return MatchingEngine(criteria, checks, MissingSkillsAnalyzer(), rules, clock)
