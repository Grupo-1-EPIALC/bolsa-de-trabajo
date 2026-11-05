"""Entidades del dominio compartidas por perfil, oferta y match.

Siguen `contracts/estructura_comun_perfil_oferta_match.md` (§3 y §4): los mismos bloques
describen lo que el estudiante tiene/busca y lo que la oferta pide/ofrece.
El dominio no depende de FastAPI, ORM ni SDKs externos (AGENTS.md §2.1).
"""

from dataclasses import dataclass, field
from enum import StrEnum


class RequirementKind(StrEnum):
    REQUIRED = "required"
    DESIRED = "desired"
    EXCLUDING = "excluding"


class Priority(StrEnum):
    HIGH = "alta"
    MEDIUM = "media"
    LOW = "baja"


class CheckOutcome(StrEnum):
    MATCH = "match"
    PARTIAL = "partial"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"


class SalaryOutcome(StrEnum):
    MATCH = "match"
    PARTIAL = "partial"
    BELOW_EXPECTATION = "below_expectation"
    UNKNOWN = "unknown"


# ------------------------------------------------------------------ bloques ---


@dataclass(frozen=True)
class Location:
    country: str = ""
    province: str = ""
    city: str = ""
    postal_code: str = ""
    zone: str = ""
    lat: float | None = None
    lon: float | None = None

    @property
    def is_empty(self) -> bool:
        return not (self.country or self.province or self.city)


@dataclass(frozen=True)
class SalaryRange:
    """Sueldo pretendido (perfil) u ofrecido (oferta). Ver §4.2 del contrato."""

    min: float | None = None
    max: float | None = None
    currency: str = ""
    period: str = "month"
    gross: bool = True
    negotiable: bool = False
    to_agree: bool = False
    visibility: str = "on_match"

    @property
    def has_amount(self) -> bool:
        return not self.to_agree and (self.min is not None or self.max is not None)


@dataclass(frozen=True)
class HoursRange:
    min: float
    max: float


@dataclass(frozen=True)
class WorkConditions:
    """Lo que el estudiante busca/acepta o lo que la oferta ofrece (§4.3)."""

    work_schedule: frozenset[str] = frozenset()
    work_modality: frozenset[str] = frozenset()
    hybrid_onsite_days: int | None = None
    employment_type: frozenset[str] = frozenset()
    contract_duration: frozenset[str] = frozenset()
    weekly_hours: HoursRange | None = None
    shifts: frozenset[str] = frozenset()
    availability_start: str = ""
    salary: SalaryRange | None = None
    willing_to_relocate: bool = False
    relocation_support: bool = False
    max_commute_km: float | None = None
    travel_availability: str = ""
    driver_license: frozenset[str] = frozenset()
    own_vehicle: bool | None = None
    work_authorization: frozenset[str] = frozenset()


@dataclass(frozen=True)
class SkillItem:
    name: str
    normalized: str
    level: int = 1
    years: float | None = None
    kind: RequirementKind = RequirementKind.REQUIRED


@dataclass(frozen=True)
class LanguageItem:
    name: str
    normalized: str
    level: str = ""
    kind: RequirementKind = RequirementKind.REQUIRED


@dataclass(frozen=True)
class EducationItem:
    level: str = ""
    status: str = ""
    degree: str = ""
    field: str = ""
    kind: RequirementKind = RequirementKind.REQUIRED


@dataclass(frozen=True)
class ExperienceRequirement:
    min_years: float = 0.0
    area: str = ""
    kind: RequirementKind = RequirementKind.REQUIRED


@dataclass(frozen=True)
class AcademicStatus:
    career: str = ""
    current_year: int | None = None
    progress_percent: float | None = None
    student_shift: frozenset[str] = frozenset()


@dataclass(frozen=True)
class AcademicRequirement:
    min_progress_percent: float | None = None
    min_current_year: int | None = None
    careers: tuple[str, ...] = ()


# ---------------------------------------------------------------- entidades ---


@dataclass(frozen=True)
class StudentProfile:
    id: str
    user_id: str = ""  # `sub` del JWT de auth-service del estudiante dueño del perfil
    display_name: str = ""
    headline: str = ""
    location: Location = field(default_factory=Location)
    work_conditions: WorkConditions = field(default_factory=WorkConditions)
    skills: tuple[SkillItem, ...] = ()
    languages: tuple[LanguageItem, ...] = ()
    education: tuple[EducationItem, ...] = ()
    years_experience: float = 0.0
    academic: AcademicStatus = field(default_factory=AcademicStatus)
    target_roles: tuple[str, ...] = ()

    def skill_levels(self) -> dict[str, int]:
        """Mapa `normalized -> nivel` (si una skill aparece dos veces, gana el mayor nivel)."""
        levels: dict[str, int] = {}
        for skill in self.skills:
            levels[skill.normalized] = max(levels.get(skill.normalized, 0), skill.level)
        return levels


@dataclass(frozen=True)
class JobOpportunity:
    id: str
    title: str = ""
    company_id: str = ""  # = `sub` del JWT de la empresa (Company.user_id en auth-service)
    company_name: str = ""
    status: str = "active"
    seniority: str = ""
    location: Location = field(default_factory=Location)
    work_conditions: WorkConditions = field(default_factory=WorkConditions)
    skills: tuple[SkillItem, ...] = ()
    languages: tuple[LanguageItem, ...] = ()
    education: tuple[EducationItem, ...] = ()
    experience: ExperienceRequirement = field(default_factory=ExperienceRequirement)
    academic: AcademicRequirement = field(default_factory=AcademicRequirement)

    def skills_of(self, *kinds: RequirementKind) -> list[SkillItem]:
        return [s for s in self.skills if s.kind in kinds]


# --------------------------------------------------------------- resultados ---


@dataclass(frozen=True)
class CriterionResult:
    criterion: str
    weight: float
    earned: float
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MissingSkill:
    skill: str
    kind: RequirementKind
    required_level: int
    current_level: int
    gap: int
    priority: Priority


@dataclass(frozen=True)
class MatchedSkill:
    skill: str
    kind: RequirementKind
    profile_level: int
    required_level: int


@dataclass(frozen=True)
class ConditionCheckResult:
    condition: str
    result: CheckOutcome
    hard: bool
    profile_value: object = None
    job_value: object = None
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SalaryFit:
    result: SalaryOutcome
    expected_monthly: HoursRange | None = None
    offered_monthly: HoursRange | None = None
    gap_percent: float | None = None
    currency: str = ""


@dataclass(frozen=True)
class ConditionsFit:
    compatible: bool
    checks: tuple[ConditionCheckResult, ...] = ()
    distance_km: float | None = None
    salary_fit: SalaryFit | None = None


@dataclass(frozen=True)
class MatchResult:
    """Resultado calculado por reglas (`origin = "RULES"`)."""

    profile_id: str
    job_id: str
    score: float
    excluding_cap_applied: bool
    breakdown: tuple[CriterionResult, ...]
    missing_skills: tuple[MissingSkill, ...]
    matched_skills: tuple[MatchedSkill, ...]
    conditions_fit: ConditionsFit
    engine_version: str
    rules_version: str
    computed_at: str
