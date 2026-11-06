"""Entidad `StudentProfile` y sus bloques (§4 y §5 de la estructura común).

Sólo dataclasses inmutables y enums: sin FastAPI, SQLAlchemy ni SDKs (AGENTS.md §2.1).
Los cambios se hacen con `dataclasses.replace` desde los casos de uso.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

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
    ProfileStatus,
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


@dataclass(frozen=True)
class Location:
    """Ciudad, provincia y país. Nunca la dirección exacta (AGENTS.md §5.5)."""

    country: str
    province: str
    city: str
    postal_code: str | None = None
    zone: str | None = None


@dataclass(frozen=True)
class PersonalInfo:
    name: str = ""
    email: str = ""
    phone: str | None = None
    birth_year: int | None = None  # sólo para validar pasantías; no va al CV ni a matching
    location: Location | None = None


@dataclass(frozen=True)
class AcademicStatus:
    institution: str | None = None
    career: str | None = None
    current_year: int | None = None
    progress_percent: int | None = None
    expected_graduation: str | None = None  # YYYY-MM
    student_shift: tuple[Shift, ...] = ()


@dataclass(frozen=True)
class Target:
    roles: tuple[str, ...] = ()
    areas: tuple[str, ...] = ()
    seniority: Seniority | None = None


@dataclass(frozen=True)
class WeeklyHours:
    min: int
    max: int


@dataclass(frozen=True)
class SalaryExpectation:
    """Sueldo pretendido (§4.2). `visibility` decide quién ve el monto."""

    min: float | None = None
    max: float | None = None
    currency: Currency | None = None
    period: SalaryPeriod | None = None
    gross: bool = True
    payment_mode: PaymentMode | None = None
    negotiable: bool = False
    visibility: SalaryVisibility = SalaryVisibility.ON_MATCH
    to_agree: bool = False
    notes: str | None = None


@dataclass(frozen=True)
class WorkPreferences:
    """Lo que el estudiante busca o acepta (`work_conditions` del perfil, §4.3)."""

    work_schedule: tuple[WorkSchedule, ...] = ()
    work_modality: tuple[WorkModality, ...] = ()
    hybrid_onsite_days: int | None = None
    employment_type: tuple[EmploymentType, ...] = ()
    contract_duration: tuple[ContractDuration, ...] = ()
    weekly_hours: WeeklyHours | None = None
    shifts: tuple[Shift, ...] = ()
    availability_start: AvailabilityStart | None = None
    salary: SalaryExpectation | None = None
    willing_to_relocate: bool = False
    max_commute_km: int | None = None
    travel_availability: TravelAvailability | None = None
    driver_license: tuple[str, ...] = ()
    own_vehicle: bool | None = None
    own_equipment: bool | None = None
    invoicing_status: InvoicingStatus | None = None
    work_authorization: tuple[str, ...] = ()
    timezone: str | None = None


@dataclass(frozen=True)
class Skill:
    name: str
    level: int  # 1 a 5
    normalized: str = ""
    years: float | None = None
    category: SkillCategory | None = None
    last_used: str | None = None  # YYYY
    source: DataSource = DataSource.MANUAL
    confirmed: bool = True


@dataclass(frozen=True)
class Experience:
    company: str
    role: str
    start: str  # YYYY o YYYY-MM
    end: str = "actual"  # YYYY, YYYY-MM o "actual"
    description: str = ""
    area: str | None = None
    employment_type: EmploymentType | None = None
    work_modality: WorkModality | None = None
    skills_used: tuple[str, ...] = ()
    months: int | None = None  # calculado por reglas


@dataclass(frozen=True)
class Education:
    institution: str
    degree: str
    level: EducationLevel
    status: EducationStatus
    field: str | None = None
    start: str | None = None
    end: str | None = None
    progress_percent: int | None = None
    current_year: int | None = None
    gpa: float | None = None


@dataclass(frozen=True)
class Language:
    name: str
    level: LanguageLevel
    normalized: str = ""
    certification: str | None = None


@dataclass(frozen=True)
class Certification:
    name: str
    issuer: str | None = None
    year: int | None = None
    url: str | None = None


@dataclass(frozen=True)
class Project:
    name: str
    description: str = ""
    url: str | None = None
    skills_used: tuple[str, ...] = ()


@dataclass(frozen=True)
class Link:
    type: LinkType
    url: str


@dataclass(frozen=True)
class Volunteering:
    organization: str
    role: str
    start: str | None = None
    end: str | None = None
    description: str = ""


@dataclass(frozen=True)
class Consents:
    data_processing: bool = False
    ai_processing: bool = False
    contact_by_email: bool = False
    accepted_at: datetime | None = None


@dataclass(frozen=True)
class Inclusion:
    """Dato privado y opcional: nunca sale del dueño ni entra a prompts de IA (§2.4)."""

    disability_certificate: bool = False
    accessibility_needs: str | None = None


@dataclass(frozen=True)
class CvFile:
    stored_filename: str
    original_filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime


@dataclass(frozen=True)
class StudentProfile:
    id: str
    user_id: str  # `sub` del JWT de auth-service
    created_at: datetime
    updated_at: datetime
    version: int = 1
    status: ProfileStatus = ProfileStatus.DRAFT
    personal: PersonalInfo = field(default_factory=PersonalInfo)
    headline: str | None = None
    summary: str | None = None
    academic_status: AcademicStatus | None = None
    target: Target | None = None
    work_conditions: WorkPreferences = field(default_factory=WorkPreferences)
    skills: tuple[Skill, ...] = ()
    experience: tuple[Experience, ...] = ()
    education: tuple[Education, ...] = ()
    languages: tuple[Language, ...] = ()
    certifications: tuple[Certification, ...] = ()
    projects: tuple[Project, ...] = ()
    links: tuple[Link, ...] = ()
    volunteering: tuple[Volunteering, ...] = ()
    references_available: bool = False
    visibility: ProfileVisibility = ProfileVisibility.PUBLIC_TO_COMPANIES
    job_search_status: JobSearchStatus = JobSearchStatus.ACTIVE
    consents: Consents = field(default_factory=Consents)
    inclusion: Inclusion | None = None
    cv_files: tuple[CvFile, ...] = ()
    # Última extracción de WF-01 (origin="AI"). Es una sugerencia: nunca pisa lo confirmado.
    cv_suggestions: dict[str, Any] | None = None

    def owned_by(self, user_id: str) -> bool:
        return self.user_id == user_id

    @property
    def is_searchable(self) -> bool:
        """Puede aparecer en rankings de matching."""
        return (
            self.status is ProfileStatus.COMPLETE
            and self.visibility is not ProfileVisibility.HIDDEN
            and self.job_search_status is not JobSearchStatus.NOT_LOOKING
        )

    def has_skill(self, normalized_names: frozenset[str]) -> bool:
        return any(skill.normalized in normalized_names for skill in self.skills)


# Secciones que el usuario puede editar (PATCH reemplaza la sección completa).
EDITABLE_SECTIONS: tuple[str, ...] = (
    "personal",
    "headline",
    "summary",
    "academic_status",
    "target",
    "work_conditions",
    "skills",
    "experience",
    "education",
    "languages",
    "certifications",
    "projects",
    "links",
    "volunteering",
    "references_available",
    "visibility",
    "job_search_status",
    "consents",
    "inclusion",
)
