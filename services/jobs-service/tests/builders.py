"""Constructores de ofertas ficticias para tests (sin datos personales reales)."""

from datetime import UTC, datetime

from app.application.commands import JobDraft
from app.domain.enums import (
    Currency,
    EducationLevel,
    EducationStatus,
    JobStatus,
    LanguageLevel,
    RequirementKind,
    SalaryPeriod,
    SalaryVisibility,
    Seniority,
    WorkModality,
    WorkSchedule,
)
from app.domain.models import (
    CompanySnapshot,
    EducationRequirement,
    ExperienceRequirement,
    JobOpportunity,
    LanguageRequirement,
    Location,
    Requirements,
    SalaryRange,
    SkillRequirement,
    WeeklyHours,
    WorkConditions,
)
from app.domain.normalization import normalize_text

COMPANY_001 = "22222222-2222-4222-8222-000000000001"
COMPANY_002 = "22222222-2222-4222-8222-000000000002"
STUDENT_001 = "11111111-1111-4111-8111-000000000001"
ADMIN_001 = "33333333-3333-4333-8333-000000000001"
NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


def skill(
    name: str = "Python",
    *,
    level: int = 3,
    kind: RequirementKind = RequirementKind.REQUIRED,
) -> SkillRequirement:
    return SkillRequirement(
        name=name,
        normalized=normalize_text(name),
        level=level,
        kind=kind,
    )


def requirements(
    skills: tuple[SkillRequirement, ...] | None = None,
) -> Requirements:
    return Requirements(
        skills=skills if skills is not None else (skill("Python"), skill("SQL")),
        languages=(
            LanguageRequirement(
                name="Inglés",
                normalized="ingles",
                level=LanguageLevel.B1,
                kind=RequirementKind.REQUIRED,
            ),
        ),
        education=(
            EducationRequirement(
                level=EducationLevel.UNIVERSITY,
                status=EducationStatus.IN_PROGRESS,
                kind=RequirementKind.REQUIRED,
                field="sistemas",
            ),
        ),
        experience=ExperienceRequirement(
            min_years=1,
            kind=RequirementKind.REQUIRED,
            area="desarrollo backend",
        ),
    )


def location() -> Location:
    return Location(country="AR", province="CABA", city="Buenos Aires")


def salary(
    *,
    visibility: SalaryVisibility = SalaryVisibility.PUBLIC,
    minimum: float | None = 800_000,
    maximum: float | None = 1_000_000,
) -> SalaryRange:
    return SalaryRange(
        min=minimum,
        max=maximum,
        currency=Currency.ARS,
        period=SalaryPeriod.MONTH,
        visibility=visibility,
        to_agree=minimum is None and maximum is None,
    )


def conditions(*, job_salary: SalaryRange | None = None) -> WorkConditions:
    return WorkConditions(
        work_schedule=(WorkSchedule.FULL_TIME,),
        work_modality=(WorkModality.HYBRID,),
        hybrid_onsite_days=2,
        weekly_hours=WeeklyHours(min=30, max=40),
        salary=job_salary if job_salary is not None else salary(),
    )


def draft(
    *,
    title: str = "Desarrollador/a Backend Python Jr.",
    description: str = "Desarrollo de microservicios REST con Python y PostgreSQL.",
    job_requirements: Requirements | None = None,
    job_conditions: WorkConditions | None = None,
) -> JobDraft:
    return JobDraft(
        title=title,
        description=description,
        seniority=Seniority.JUNIOR,
        location=location(),
        requirements=job_requirements or requirements(),
        work_conditions=job_conditions or conditions(),
    )


def job(
    *,
    job_id: str = "job-001",
    company_id: str = COMPANY_001,
    status: JobStatus = JobStatus.ACTIVE,
    title: str = "Desarrollador/a Backend Python Jr.",
    description: str = "Desarrollo de microservicios REST con Python y PostgreSQL.",
    job_requirements: Requirements | None = None,
    job_conditions: WorkConditions | None = None,
    version: int = 1,
    published_at: datetime | None = NOW,
    expires_at: datetime | None = None,
    company_name: str = "PampaTech S.A.",
) -> JobOpportunity:
    return JobOpportunity(
        id=job_id,
        company_id=company_id,
        company_snapshot=CompanySnapshot(name=company_name, industry="software", size="51-200"),
        status=status,
        title=title,
        description=description,
        responsibilities=(),
        area="software",
        seniority=Seniority.JUNIOR,
        vacancies=1,
        location=location(),
        work_conditions=job_conditions or conditions(),
        requirements=job_requirements or requirements(),
        benefits=("capacitación",),
        created_at=NOW,
        updated_at=NOW,
        published_at=published_at,
        expires_at=expires_at,
        version=version,
    )
