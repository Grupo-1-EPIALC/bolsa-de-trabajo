"""Schemas de entrada (Pydantic). Validan forma, enums y rangos antes de llegar al dominio.

`PATCH /profiles/me` reemplaza **cada sección enviada completa** (no hace merge profundo):
si mandás `personal`, mandá todos sus campos.
"""

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import (
    AvailabilityStart,
    ContractDuration,
    Currency,
    DataSource,
    EducationLevel,
    EducationStatus,
    EmploymentType,
    InvoicingStatus,
    JobSearchStatus,
    LanguageLevel,
    LinkType,
    PaymentMode,
    ProfileVisibility,
    SalaryPeriod,
    SalaryVisibility,
    Seniority,
    Shift,
    SkillCategory,
    TravelAvailability,
    WorkModality,
    WorkSchedule,
)

Text = Annotated[str, Field(min_length=1, max_length=200)]
LongText = Annotated[str, Field(max_length=4000)]
Period = Annotated[str, Field(pattern=r"^\d{4}(-(0[1-9]|1[0-2]))?$")]
PeriodOrNow = Annotated[str, Field(pattern=r"^(\d{4}(-(0[1-9]|1[0-2]))?|actual)$")]
Url = Annotated[str, Field(pattern=r"^https?://\S+$", max_length=300)]
Email = Annotated[str, Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=320)]
Country = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LocationIn(StrictModel):
    country: Country
    province: Text
    city: Text
    postal_code: Annotated[str, Field(max_length=10)] | None = None
    zone: Annotated[str, Field(max_length=100)] | None = None


class PersonalIn(StrictModel):
    name: Annotated[str, Field(min_length=2, max_length=120)]
    email: Email
    phone: Annotated[str, Field(pattern=r"^[0-9+()\-\s]{6,30}$")] | None = None
    birth_year: Annotated[int, Field(ge=1940, le=2015)] | None = None
    location: LocationIn | None = None


class AcademicStatusIn(StrictModel):
    institution: Text | None = None
    career: Text | None = None
    current_year: Annotated[int, Field(ge=1, le=8)] | None = None
    progress_percent: Annotated[int, Field(ge=0, le=100)] | None = None
    expected_graduation: Period | None = None
    student_shift: list[Shift] = Field(default_factory=list, max_length=6)


class TargetIn(StrictModel):
    roles: list[Text] = Field(default_factory=list, max_length=5)
    areas: list[Text] = Field(default_factory=list, max_length=5)
    seniority: Seniority | None = None


class WeeklyHoursIn(StrictModel):
    min: Annotated[int, Field(ge=1, le=80)]
    max: Annotated[int, Field(ge=1, le=80)]

    @model_validator(mode="after")
    def _order(self) -> "WeeklyHoursIn":
        if self.max < self.min:
            raise ValueError("max debe ser ≥ min")
        return self


class SalaryIn(StrictModel):
    min: Annotated[float, Field(ge=0)] | None = None
    max: Annotated[float, Field(ge=0)] | None = None
    currency: Currency | None = None
    period: SalaryPeriod | None = None
    gross: bool = True
    payment_mode: PaymentMode | None = None
    negotiable: bool = False
    visibility: SalaryVisibility = SalaryVisibility.ON_MATCH
    to_agree: bool = False
    notes: Annotated[str, Field(max_length=300)] | None = None

    @model_validator(mode="after")
    def _consistent(self) -> "SalaryIn":
        if self.to_agree:
            return self
        if self.min is None:
            raise ValueError("Indicá un monto mínimo o marcá to_agree=true")
        if self.currency is None or self.period is None:
            raise ValueError("currency y period son obligatorios si hay monto")
        if self.max is not None and self.max < self.min:
            raise ValueError("max debe ser ≥ min")
        return self


class WorkConditionsIn(StrictModel):
    work_schedule: list[WorkSchedule] = Field(default_factory=list, max_length=4)
    work_modality: list[WorkModality] = Field(default_factory=list, max_length=3)
    hybrid_onsite_days: Annotated[int, Field(ge=0, le=5)] | None = None
    employment_type: list[EmploymentType] = Field(default_factory=list, max_length=4)
    contract_duration: list[ContractDuration] = Field(default_factory=list, max_length=4)
    weekly_hours: WeeklyHoursIn | None = None
    shifts: list[Shift] = Field(default_factory=list, max_length=6)
    availability_start: AvailabilityStart | None = None
    salary: SalaryIn | None = None
    willing_to_relocate: bool = False
    max_commute_km: Annotated[int, Field(ge=0, le=500)] | None = None
    travel_availability: TravelAvailability | None = None
    driver_license: list[Annotated[str, Field(max_length=10)]] = Field(default_factory=list)
    own_vehicle: bool | None = None
    own_equipment: bool | None = None
    invoicing_status: InvoicingStatus | None = None
    work_authorization: list[Country] = Field(default_factory=list)
    timezone: Annotated[str, Field(max_length=60)] | None = None


class SkillIn(StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=60)]
    level: Annotated[int, Field(ge=1, le=5)]
    years: Annotated[float, Field(ge=0, le=50)] | None = None
    category: SkillCategory | None = None
    last_used: Annotated[str, Field(pattern=r"^\d{4}$")] | None = None
    source: DataSource = DataSource.MANUAL
    confirmed: bool = True


class ExperienceIn(StrictModel):
    company: Text
    role: Text
    start: Period
    end: PeriodOrNow = "actual"
    description: LongText = ""
    area: Text | None = None
    employment_type: EmploymentType | None = None
    work_modality: WorkModality | None = None
    skills_used: list[Annotated[str, Field(max_length=60)]] = Field(default_factory=list)


class EducationIn(StrictModel):
    institution: Text
    degree: Text
    level: EducationLevel
    status: EducationStatus
    field: Text | None = None
    start: Period | None = None
    end: Period | None = None
    progress_percent: Annotated[int, Field(ge=0, le=100)] | None = None
    current_year: Annotated[int, Field(ge=1, le=8)] | None = None
    gpa: Annotated[float, Field(ge=0, le=10)] | None = None


class LanguageIn(StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=40)]
    level: LanguageLevel
    certification: Annotated[str, Field(max_length=80)] | None = None


class CertificationIn(StrictModel):
    name: Text
    issuer: Text | None = None
    year: Annotated[int, Field(ge=1980, le=2100)] | None = None
    url: Url | None = None


class ProjectIn(StrictModel):
    name: Text
    description: LongText = ""
    url: Url | None = None
    skills_used: list[Annotated[str, Field(max_length=60)]] = Field(default_factory=list)


class LinkIn(StrictModel):
    type: LinkType
    url: Url


class VolunteeringIn(StrictModel):
    organization: Text
    role: Text
    start: Period | None = None
    end: PeriodOrNow | None = None
    description: LongText = ""


class ConsentsIn(StrictModel):
    data_processing: bool
    ai_processing: bool = False
    contact_by_email: bool = False
    accepted_at: datetime | None = None


class InclusionIn(StrictModel):
    disability_certificate: bool = False
    accessibility_needs: Annotated[str, Field(max_length=500)] | None = None


class ProfilePatch(StrictModel):
    """Secciones editables del perfil. Las que no se envían no cambian."""

    personal: PersonalIn | None = None
    headline: Annotated[str, Field(max_length=140)] | None = None
    summary: Annotated[str, Field(max_length=2000)] | None = None
    academic_status: AcademicStatusIn | None = None
    target: TargetIn | None = None
    work_conditions: WorkConditionsIn | None = None
    skills: list[SkillIn] | None = Field(default=None, max_length=60)
    experience: list[ExperienceIn] | None = Field(default=None, max_length=30)
    education: list[EducationIn] | None = Field(default=None, max_length=20)
    languages: list[LanguageIn] | None = Field(default=None, max_length=10)
    certifications: list[CertificationIn] | None = Field(default=None, max_length=30)
    projects: list[ProjectIn] | None = Field(default=None, max_length=20)
    links: list[LinkIn] | None = Field(default=None, max_length=10)
    volunteering: list[VolunteeringIn] | None = Field(default=None, max_length=10)
    references_available: bool | None = None
    visibility: ProfileVisibility | None = None
    job_search_status: JobSearchStatus | None = None
    consents: ConsentsIn | None = None
    inclusion: InclusionIn | None = None

    def changes(self) -> dict[str, Any]:
        """Sólo las secciones enviadas, en tipos JSON (enums como texto)."""
        return self.model_dump(mode="json", exclude_unset=True)


class LegacyCvExtractRequest(BaseModel):
    """Cuerpo de los endpoints `cv-extract` (compatibilidad con la página de prueba)."""

    profile_id: str = "prof-estudiante-01"
    filename: str = "cv.pdf"
    mime_type: str = ""
    content_base64: str
