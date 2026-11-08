"""Modelos de dominio de una oferta de trabajo.

No dependen de FastAPI, SQLAlchemy ni de ningún SDK externo (AGENTS.md §2.1).
Los bloques siguen `contracts/profile.md` (anexo).
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import (
    AvailabilityStart,
    ContractDuration,
    Currency,
    EducationLevel,
    EducationStatus,
    EmploymentType,
    InvoicingStatus,
    JobStatus,
    LanguageLevel,
    PaymentMode,
    RequirementKind,
    SalaryAdjustment,
    SalaryPeriod,
    SalaryVisibility,
    Seniority,
    Shift,
    SkillCategory,
    TravelAvailability,
    VariableCompensationType,
    WorkModality,
    WorkSchedule,
)


@dataclass(frozen=True)
class Location:
    country: str
    province: str
    city: str
    postal_code: str | None = None
    zone: str | None = None


@dataclass(frozen=True)
class WeeklyHours:
    min: int
    max: int


@dataclass(frozen=True)
class VariableCompensation:
    type: VariableCompensationType
    description: str | None = None
    max_percent: float | None = None


@dataclass(frozen=True)
class SalaryRange:
    min: float | None = None
    max: float | None = None
    currency: Currency | None = None
    period: SalaryPeriod | None = None
    gross: bool = True
    payment_mode: PaymentMode | None = None
    negotiable: bool = False
    adjustment: SalaryAdjustment | None = None
    variable_compensation: tuple[VariableCompensation, ...] = ()
    visibility: SalaryVisibility | None = None
    to_agree: bool = False
    notes: str | None = None


@dataclass(frozen=True)
class WorkConditions:
    work_schedule: tuple[WorkSchedule, ...] = ()
    work_modality: tuple[WorkModality, ...] = ()
    hybrid_onsite_days: int | None = None
    employment_type: tuple[EmploymentType, ...] = ()
    contract_duration: tuple[ContractDuration, ...] = ()
    weekly_hours: WeeklyHours | None = None
    shifts: tuple[Shift, ...] = ()
    availability_start: AvailabilityStart | None = None
    salary: SalaryRange | None = None
    relocation_support: bool = False
    travel_availability: TravelAvailability | None = None
    driver_license: tuple[str, ...] = ()
    own_vehicle: bool | None = None
    own_equipment: bool | None = None
    invoicing_status: InvoicingStatus | None = None
    work_authorization: tuple[str, ...] = ()
    timezone: str | None = None
    timezone_overlap_hours: int | None = None


@dataclass(frozen=True)
class SkillRequirement:
    name: str
    normalized: str
    level: int
    kind: RequirementKind
    years: float | None = None
    category: SkillCategory | None = None


@dataclass(frozen=True)
class LanguageRequirement:
    name: str
    normalized: str
    level: LanguageLevel
    kind: RequirementKind
    certification: str | None = None


@dataclass(frozen=True)
class EducationRequirement:
    level: EducationLevel
    status: EducationStatus
    kind: RequirementKind
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    progress_percent: int | None = None
    gpa: float | None = None


@dataclass(frozen=True)
class ExperienceRequirement:
    min_years: float
    kind: RequirementKind
    area: str | None = None


@dataclass(frozen=True)
class CertificationRequirement:
    name: str
    kind: RequirementKind


@dataclass(frozen=True)
class AcademicRequirement:
    min_progress_percent: float | None = None
    careers: tuple[str, ...] = ()
    min_current_year: int | None = None


@dataclass(frozen=True)
class Requirements:
    skills: tuple[SkillRequirement, ...]
    languages: tuple[LanguageRequirement, ...] = ()
    education: tuple[EducationRequirement, ...] = ()
    experience: ExperienceRequirement | None = None
    certifications: tuple[CertificationRequirement, ...] = ()
    academic: AcademicRequirement | None = None


@dataclass(frozen=True)
class CompanySnapshot:
    name: str
    industry: str | None = None
    size: str | None = None
    logo_url: str | None = None


@dataclass(frozen=True)
class JobOpportunity:
    id: str
    company_id: str
    company_snapshot: CompanySnapshot
    status: JobStatus
    title: str
    description: str
    responsibilities: tuple[str, ...]
    area: str
    seniority: Seniority
    vacancies: int
    location: Location
    work_conditions: WorkConditions
    requirements: Requirements
    benefits: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    expires_at: datetime | None
    version: int
