"""Serialización de la oferta a/desde el documento JSON persistido."""

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, cast

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
from app.domain.models import (
    AcademicRequirement,
    CertificationRequirement,
    CompanySnapshot,
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


def job_to_document(job: JobOpportunity) -> dict[str, Any]:
    return cast(dict[str, Any], _plain(job))


def job_from_document(data: Mapping[str, Any]) -> JobOpportunity:
    return JobOpportunity(
        id=str(data["id"]),
        company_id=str(data["company_id"]),
        company_snapshot=_company_snapshot(data.get("company_snapshot")),
        status=_enum(JobStatus, data["status"]),
        title=str(data["title"]),
        description=str(data["description"]),
        responsibilities=tuple(str(item) for item in _seq(data.get("responsibilities"))),
        area=str(data.get("area") or ""),
        seniority=_enum(Seniority, data["seniority"]),
        vacancies=int(data.get("vacancies") or 1),
        location=_location(data.get("location")),
        work_conditions=_work_conditions(data.get("work_conditions")),
        requirements=_requirements(data.get("requirements")),
        benefits=tuple(str(item) for item in _seq(data.get("benefits"))),
        created_at=_datetime(data["created_at"]),
        updated_at=_datetime(data["updated_at"]),
        published_at=_datetime_or_none(data.get("published_at")),
        expires_at=_datetime_or_none(data.get("expires_at")),
        version=int(data.get("version") or 1),
    )


# ------------------------------------------------------------------ salida ---


def _plain(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, (list, tuple, set)):
        return [_plain(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    return value


def _iso(value: datetime) -> str:
    current = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return current.isoformat()


# ------------------------------------------------------------------ entrada ---


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _seq(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple)):
        return list(value)
    return []


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _float_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    number = _float_or_none(value)
    return None if number is None else int(number)


def _enum[E: Enum](enum_type: type[E], value: Any) -> E:
    return enum_type(value)


def _enum_or_none[E: Enum](enum_type: type[E], value: Any) -> E | None:
    if value is None or value == "":
        return None
    return enum_type(value)


def _enum_tuple[E: Enum](enum_type: type[E], value: Any) -> tuple[E, ...]:
    return tuple(enum_type(item) for item in _seq(value))


def _datetime(value: Any) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _datetime_or_none(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    return _datetime(value)


def _company_snapshot(value: Any) -> CompanySnapshot:
    data = _mapping(value)
    return CompanySnapshot(
        name=_text(data.get("name")),
        industry=_text_or_none(data.get("industry")),
        size=_text_or_none(data.get("size")),
        logo_url=_text_or_none(data.get("logo_url")),
    )


def _location(value: Any) -> Location:
    data = _mapping(value)
    return Location(
        country=_text(data.get("country")),
        province=_text(data.get("province")),
        city=_text(data.get("city")),
        postal_code=_text_or_none(data.get("postal_code")),
        zone=_text_or_none(data.get("zone")),
    )


def _salary(value: Any) -> SalaryRange | None:
    data = _mapping(value)
    if not data:
        return None
    variable = tuple(
        VariableCompensation(
            type=_enum(VariableCompensationType, item.get("type")),
            description=_text_or_none(item.get("description")),
            max_percent=_float_or_none(item.get("max_percent")),
        )
        for item in (_mapping(entry) for entry in _seq(data.get("variable_compensation")))
    )
    return SalaryRange(
        min=_float_or_none(data.get("min")),
        max=_float_or_none(data.get("max")),
        currency=_enum_or_none(Currency, data.get("currency")),
        period=_enum_or_none(SalaryPeriod, data.get("period")),
        gross=bool(data.get("gross", True)),
        payment_mode=_enum_or_none(PaymentMode, data.get("payment_mode")),
        negotiable=bool(data.get("negotiable", False)),
        adjustment=_enum_or_none(SalaryAdjustment, data.get("adjustment")),
        variable_compensation=variable,
        visibility=_enum_or_none(SalaryVisibility, data.get("visibility")),
        to_agree=bool(data.get("to_agree", False)),
        notes=_text_or_none(data.get("notes")),
    )


def _weekly_hours(value: Any) -> WeeklyHours | None:
    data = _mapping(value)
    if not data:
        return None
    return WeeklyHours(
        min=_int_or_none(data.get("min")) or 0,
        max=_int_or_none(data.get("max")) or 0,
    )


def _work_conditions(value: Any) -> WorkConditions:
    data = _mapping(value)
    return WorkConditions(
        work_schedule=_enum_tuple(WorkSchedule, data.get("work_schedule")),
        work_modality=_enum_tuple(WorkModality, data.get("work_modality")),
        hybrid_onsite_days=_int_or_none(data.get("hybrid_onsite_days")),
        employment_type=_enum_tuple(EmploymentType, data.get("employment_type")),
        contract_duration=_enum_tuple(ContractDuration, data.get("contract_duration")),
        weekly_hours=_weekly_hours(data.get("weekly_hours")),
        shifts=_enum_tuple(Shift, data.get("shifts")),
        availability_start=_enum_or_none(AvailabilityStart, data.get("availability_start")),
        salary=_salary(data.get("salary")),
        relocation_support=bool(data.get("relocation_support", False)),
        travel_availability=_enum_or_none(TravelAvailability, data.get("travel_availability")),
        driver_license=tuple(str(item) for item in _seq(data.get("driver_license"))),
        own_vehicle=_bool_or_none(data.get("own_vehicle")),
        own_equipment=_bool_or_none(data.get("own_equipment")),
        invoicing_status=_enum_or_none(InvoicingStatus, data.get("invoicing_status")),
        work_authorization=tuple(str(item) for item in _seq(data.get("work_authorization"))),
        timezone=_text_or_none(data.get("timezone")),
        timezone_overlap_hours=_int_or_none(data.get("timezone_overlap_hours")),
    )


def _bool_or_none(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _requirements(value: Any) -> Requirements:
    data = _mapping(value)
    skills = tuple(
        SkillRequirement(
            name=_text(item.get("name")),
            normalized=_text(item.get("normalized")) or normalize_text(_text(item.get("name"))),
            level=_int_or_none(item.get("level")) or 0,
            kind=_enum(RequirementKind, item.get("kind")),
            years=_float_or_none(item.get("years")),
            category=_enum_or_none(SkillCategory, item.get("category")),
        )
        for item in (_mapping(entry) for entry in _seq(data.get("skills")))
    )
    languages = tuple(
        LanguageRequirement(
            name=_text(item.get("name")),
            normalized=_text(item.get("normalized")) or normalize_text(_text(item.get("name"))),
            level=_enum(LanguageLevel, item.get("level")),
            kind=_enum(RequirementKind, item.get("kind")),
            certification=_text_or_none(item.get("certification")),
        )
        for item in (_mapping(entry) for entry in _seq(data.get("languages")))
    )
    education = tuple(
        EducationRequirement(
            level=_enum(EducationLevel, item.get("level")),
            status=_enum(EducationStatus, item.get("status")),
            kind=_enum(RequirementKind, item.get("kind")),
            institution=_text_or_none(item.get("institution")),
            degree=_text_or_none(item.get("degree")),
            field=_text_or_none(item.get("field")),
            progress_percent=_int_or_none(item.get("progress_percent")),
            gpa=_float_or_none(item.get("gpa")),
        )
        for item in (_mapping(entry) for entry in _seq(data.get("education")))
    )
    experience_data = _mapping(data.get("experience"))
    experience = (
        ExperienceRequirement(
            min_years=_float_or_none(experience_data.get("min_years")) or 0.0,
            kind=_enum(RequirementKind, experience_data.get("kind")),
            area=_text_or_none(experience_data.get("area")),
        )
        if experience_data
        else None
    )
    certifications = tuple(
        CertificationRequirement(
            name=_text(item.get("name")),
            kind=_enum(RequirementKind, item.get("kind")),
        )
        for item in (_mapping(entry) for entry in _seq(data.get("certifications")))
    )
    academic_data = _mapping(data.get("academic"))
    academic = (
        AcademicRequirement(
            min_progress_percent=_float_or_none(academic_data.get("min_progress_percent")),
            careers=tuple(str(item) for item in _seq(academic_data.get("careers"))),
            min_current_year=_int_or_none(academic_data.get("min_current_year")),
        )
        if academic_data
        else None
    )
    return Requirements(
        skills=skills,
        languages=languages,
        education=education,
        experience=experience,
        certifications=certifications,
        academic=academic,
    )
