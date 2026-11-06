"""Schemas Pydantic de entrada (los schemas de salida están en el contrato OpenAPI)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RequirementKindLiteral = Literal["required", "desired", "excluding"]
SeniorityLiteral = Literal["no_experience", "trainee", "junior", "semi_senior", "senior"]
LanguageLevelLiteral = Literal["A1", "A2", "B1", "B2", "C1", "C2", "native"]
EducationLevelLiteral = Literal["secondary", "tertiary", "university", "postgraduate", "course"]
EducationStatusLiteral = Literal["in_progress", "completed", "incomplete"]
SkillCategoryLiteral = Literal["hard", "soft", "tool", "methodology"]
CurrencyLiteral = Literal["ARS", "USD"]
SalaryPeriodLiteral = Literal["hour", "day", "month", "year", "project"]
SalaryVisibilityLiteral = Literal["public", "on_match", "hidden"]
SalaryAdjustmentLiteral = Literal["none", "monthly", "quarterly", "semiannual", "by_agreement"]
PaymentModeLiteral = Literal["local", "usd", "usd_paid_in_local"]
VariableCompensationTypeLiteral = Literal["bonus", "commission", "profit_sharing"]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocationIn(ApiModel):
    country: str = Field(pattern=r"^[A-Z]{2}$")
    province: str = Field(min_length=1, max_length=120)
    city: str = Field(min_length=1, max_length=120)
    postal_code: str | None = Field(default=None, max_length=20)
    zone: str | None = Field(default=None, max_length=120)


class VariableCompensationIn(ApiModel):
    type: VariableCompensationTypeLiteral
    description: str | None = Field(default=None, max_length=500)
    max_percent: float | None = Field(default=None, ge=0, le=100)


class SalaryRangeIn(ApiModel):
    min: float | None = Field(default=None, ge=0)
    max: float | None = Field(default=None, ge=0)
    currency: CurrencyLiteral | None = None
    period: SalaryPeriodLiteral | None = None
    gross: bool = True
    payment_mode: PaymentModeLiteral | None = None
    negotiable: bool = False
    adjustment: SalaryAdjustmentLiteral | None = None
    variable_compensation: list[VariableCompensationIn] = Field(default_factory=list)
    visibility: SalaryVisibilityLiteral | None = None
    to_agree: bool = False
    notes: str | None = Field(default=None, max_length=500)


class WeeklyHoursIn(ApiModel):
    min: int = Field(ge=0, le=168)
    max: int = Field(ge=0, le=168)


class WorkConditionsIn(ApiModel):
    work_schedule: list[Literal["full_time", "part_time", "hourly", "flexible"]] = Field(
        default_factory=list
    )
    work_modality: list[Literal["onsite", "remote", "hybrid"]] = Field(default_factory=list)
    hybrid_onsite_days: int | None = Field(default=None, ge=0, le=5)
    employment_type: list[Literal["employee", "freelance", "internship", "trainee"]] = Field(
        default_factory=list
    )
    contract_duration: list[Literal["permanent", "fixed_term", "project", "seasonal"]] = Field(
        default_factory=list
    )
    weekly_hours: WeeklyHoursIn | None = None
    shifts: list[Literal["morning", "afternoon", "evening", "night", "weekend", "rotating"]] = (
        Field(default_factory=list)
    )
    availability_start: (
        Literal["immediate", "within_15_days", "within_30_days", "to_agree"] | None
    ) = None
    salary: SalaryRangeIn | None = None
    relocation_support: bool = False
    travel_availability: Literal["none", "occasional", "frequent"] | None = None
    driver_license: list[str] = Field(default_factory=list)
    own_vehicle: bool | None = None
    own_equipment: bool | None = None
    invoicing_status: (
        Literal["monotributo", "responsable_inscripto", "none", "to_register"] | None
    ) = None
    work_authorization: list[str] = Field(default_factory=list)
    timezone: str | None = Field(default=None, max_length=64)
    timezone_overlap_hours: int | None = Field(default=None, ge=0, le=24)


class SkillRequirementIn(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    level: int = Field(ge=1, le=5)
    kind: RequirementKindLiteral
    years: float | None = Field(default=None, ge=0)
    category: SkillCategoryLiteral | None = None


class LanguageRequirementIn(ApiModel):
    name: str = Field(min_length=1, max_length=80)
    level: LanguageLevelLiteral
    kind: RequirementKindLiteral
    certification: str | None = Field(default=None, max_length=120)


class EducationRequirementIn(ApiModel):
    level: EducationLevelLiteral
    status: EducationStatusLiteral
    kind: RequirementKindLiteral
    institution: str | None = Field(default=None, max_length=200)
    degree: str | None = Field(default=None, max_length=200)
    field: str | None = Field(default=None, max_length=120)
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    gpa: float | None = Field(default=None, ge=0)


class ExperienceRequirementIn(ApiModel):
    min_years: float = Field(ge=0, le=60)
    kind: RequirementKindLiteral
    area: str | None = Field(default=None, max_length=120)


class CertificationRequirementIn(ApiModel):
    name: str = Field(min_length=1, max_length=160)
    kind: RequirementKindLiteral


class AcademicRequirementIn(ApiModel):
    min_progress_percent: float | None = Field(default=None, ge=0, le=100)
    careers: list[str] = Field(default_factory=list)
    min_current_year: int | None = Field(default=None, ge=1, le=10)


class RequirementsIn(ApiModel):
    skills: list[SkillRequirementIn] = Field(min_length=1)
    languages: list[LanguageRequirementIn] = Field(default_factory=list)
    education: list[EducationRequirementIn] = Field(default_factory=list)
    experience: ExperienceRequirementIn | None = None
    certifications: list[CertificationRequirementIn] = Field(default_factory=list)
    academic: AcademicRequirementIn | None = None


class JobCreate(ApiModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20_000)
    responsibilities: list[str] = Field(default_factory=list, max_length=50)
    area: str = Field(default="", max_length=120)
    seniority: SeniorityLiteral
    vacancies: int = Field(default=1, ge=1, le=1000)
    location: LocationIn
    work_conditions: WorkConditionsIn | None = None
    requirements: RequirementsIn
    benefits: list[str] = Field(default_factory=list, max_length=50)
    expires_at: datetime | None = None


class JobUpdate(ApiModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)
    responsibilities: list[str] | None = Field(default=None, max_length=50)
    area: str | None = Field(default=None, max_length=120)
    seniority: SeniorityLiteral | None = None
    vacancies: int | None = Field(default=None, ge=1, le=1000)
    location: LocationIn | None = None
    work_conditions: WorkConditionsIn | None = None
    requirements: RequirementsIn | None = None
    benefits: list[str] | None = Field(default=None, max_length=50)
    expires_at: datetime | None = None
    status: Literal["active"] | None = None
