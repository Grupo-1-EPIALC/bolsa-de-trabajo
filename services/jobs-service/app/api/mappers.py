"""Mapeo entre schemas HTTP, comandos de aplicación y respuestas JSON."""

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, cast

from fastapi.encoders import jsonable_encoder

from app.api.schemas import (
    AcademicRequirementIn,
    CertificationRequirementIn,
    EducationRequirementIn,
    ExperienceRequirementIn,
    JobCreate,
    JobUpdate,
    LanguageRequirementIn,
    LocationIn,
    RequirementsIn,
    SalaryRangeIn,
    SkillRequirementIn,
    WorkConditionsIn,
)
from app.application.commands import JobDraft
from app.application.job_service import JobPage
from app.domain.enums import (
    AvailabilityStart,
    ContractDuration,
    Currency,
    EducationLevel,
    EducationStatus,
    EmploymentType,
    InvoicingStatus,
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
from app.domain.errors import InvalidInputError
from app.domain.models import (
    AcademicRequirement,
    CertificationRequirement,
    EducationRequirement,
    ExperienceRequirement,
    JobOpportunity,
    LanguageRequirement,
    Location,
    Requirements,
    SalaryRange,
    SkillRequirement,
    VariableCompensation,
    WeeklyHours,
    WorkConditions,
)
from app.domain.normalization import normalize_text


def to_draft(body: JobCreate) -> JobDraft:
    return JobDraft(
        title=body.title,
        description=body.description,
        seniority=Seniority(body.seniority),
        location=_location(body.location),
        requirements=_requirements(body.requirements),
        responsibilities=tuple(body.responsibilities),
        area=body.area,
        vacancies=body.vacancies,
        work_conditions=_work_conditions(body.work_conditions),
        benefits=tuple(body.benefits),
        expires_at=_utc_or_none(body.expires_at),
    )


def to_patch(body: JobUpdate) -> dict[str, Any]:
    provided = body.model_fields_set
    patch: dict[str, Any] = {}

    if "title" in provided:
        patch["title"] = body.title or ""
    if "description" in provided:
        patch["description"] = body.description or ""
    if "responsibilities" in provided:
        patch["responsibilities"] = tuple(body.responsibilities or ())
    if "area" in provided:
        patch["area"] = body.area or ""
    if "seniority" in provided:
        patch["seniority"] = _required(Seniority(body.seniority) if body.seniority else None)
    if "vacancies" in provided:
        patch["vacancies"] = _required(body.vacancies)
    if "location" in provided:
        patch["location"] = _location(_required(body.location))
    if "work_conditions" in provided:
        patch["work_conditions"] = _work_conditions(body.work_conditions)
    if "requirements" in provided:
        patch["requirements"] = _requirements(_required(body.requirements))
    if "benefits" in provided:
        patch["benefits"] = tuple(body.benefits or ())
    if "expires_at" in provided:
        patch["expires_at"] = _utc_or_none(body.expires_at)
    if "status" in provided and body.status is not None:
        patch["status"] = body.status

    return patch


def job_to_dict(job: JobOpportunity) -> dict[str, Any]:
    return cast(dict[str, Any], jsonable_encoder(asdict(job)))


def page_to_dict(page: JobPage) -> dict[str, Any]:
    return {
        "items": [job_to_dict(job) for job in page.items],
        "total": page.total,
        "page": page.page,
        "size": page.size,
        "pages": page.pages,
    }


def _required(value: Any) -> Any:
    if value is None:
        raise InvalidInputError("El campo no puede ser nulo", {"field": "body"})
    return value


def _location(data: LocationIn) -> Location:
    return Location(
        country=data.country,
        province=data.province,
        city=data.city,
        postal_code=data.postal_code,
        zone=data.zone,
    )


def _salary(data: SalaryRangeIn) -> SalaryRange:
    return SalaryRange(
        min=data.min,
        max=data.max,
        currency=Currency(data.currency) if data.currency else None,
        period=SalaryPeriod(data.period) if data.period else None,
        gross=data.gross,
        payment_mode=PaymentMode(data.payment_mode) if data.payment_mode else None,
        negotiable=data.negotiable,
        adjustment=SalaryAdjustment(data.adjustment) if data.adjustment else None,
        variable_compensation=tuple(
            VariableCompensation(
                type=VariableCompensationType(item.type),
                description=item.description,
                max_percent=item.max_percent,
            )
            for item in data.variable_compensation
        ),
        visibility=SalaryVisibility(data.visibility) if data.visibility else None,
        to_agree=data.to_agree,
        notes=data.notes,
    )


def _work_conditions(data: WorkConditionsIn | None) -> WorkConditions:
    if data is None:
        return WorkConditions()
    return WorkConditions(
        work_schedule=tuple(WorkSchedule(item) for item in data.work_schedule),
        work_modality=tuple(WorkModality(item) for item in data.work_modality),
        hybrid_onsite_days=data.hybrid_onsite_days,
        employment_type=tuple(EmploymentType(item) for item in data.employment_type),
        contract_duration=tuple(ContractDuration(item) for item in data.contract_duration),
        weekly_hours=(
            WeeklyHours(min=data.weekly_hours.min, max=data.weekly_hours.max)
            if data.weekly_hours
            else None
        ),
        shifts=tuple(Shift(item) for item in data.shifts),
        availability_start=(
            AvailabilityStart(data.availability_start) if data.availability_start else None
        ),
        salary=_salary(data.salary) if data.salary else None,
        relocation_support=data.relocation_support,
        travel_availability=(
            TravelAvailability(data.travel_availability) if data.travel_availability else None
        ),
        driver_license=tuple(data.driver_license),
        own_vehicle=data.own_vehicle,
        own_equipment=data.own_equipment,
        invoicing_status=(
            InvoicingStatus(data.invoicing_status) if data.invoicing_status else None
        ),
        work_authorization=tuple(data.work_authorization),
        timezone=data.timezone,
        timezone_overlap_hours=data.timezone_overlap_hours,
    )


def _skills(items: list[SkillRequirementIn]) -> tuple[SkillRequirement, ...]:
    return tuple(
        SkillRequirement(
            name=item.name,
            normalized=normalize_text(item.name),
            level=item.level,
            kind=RequirementKind(item.kind),
            years=item.years,
            category=SkillCategory(item.category) if item.category else None,
        )
        for item in items
    )


def _languages(
    items: list[LanguageRequirementIn],
) -> tuple[LanguageRequirement, ...]:
    return tuple(
        LanguageRequirement(
            name=item.name,
            normalized=normalize_text(item.name),
            level=LanguageLevel(item.level),
            kind=RequirementKind(item.kind),
            certification=item.certification,
        )
        for item in items
    )


def _education(
    items: list[EducationRequirementIn],
) -> tuple[EducationRequirement, ...]:
    return tuple(
        EducationRequirement(
            level=EducationLevel(item.level),
            status=EducationStatus(item.status),
            kind=RequirementKind(item.kind),
            institution=item.institution,
            degree=item.degree,
            field=item.field,
            progress_percent=item.progress_percent,
            gpa=item.gpa,
        )
        for item in items
    )


def _experience(data: ExperienceRequirementIn | None) -> ExperienceRequirement | None:
    if data is None:
        return None
    return ExperienceRequirement(
        min_years=data.min_years,
        kind=RequirementKind(data.kind),
        area=data.area,
    )


def _certifications(
    items: list[CertificationRequirementIn],
) -> tuple[CertificationRequirement, ...]:
    return tuple(
        CertificationRequirement(
            name=str(item.name),
            kind=RequirementKind(item.kind),
        )
        for item in items
    )


def _academic(data: AcademicRequirementIn | None) -> AcademicRequirement | None:
    if data is None:
        return None
    return AcademicRequirement(
        min_progress_percent=data.min_progress_percent,
        careers=tuple(data.careers),
        min_current_year=data.min_current_year,
    )


def _requirements(data: RequirementsIn) -> Requirements:
    return Requirements(
        skills=_skills(data.skills),
        languages=_languages(data.languages),
        education=_education(data.education),
        experience=_experience(data.experience),
        certifications=_certifications(data.certifications),
        academic=_academic(data.academic),
    )


def _utc_or_none(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
