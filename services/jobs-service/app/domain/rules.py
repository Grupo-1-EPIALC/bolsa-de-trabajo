"""Reglas de negocio de ofertas: validación, permisos y visibilidad del sueldo."""

import re
from dataclasses import replace
from datetime import UTC, datetime
from enum import StrEnum

from app.domain.auth import Principal, Role
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
from app.domain.errors import ForbiddenError, InvalidInputError
from app.domain.models import CompanySnapshot, JobOpportunity

_COUNTRY_PATTERN = re.compile(r"^[A-Z]{2}$")
_MAX_TITLE = 200
_MAX_DESCRIPTION = 20_000


def _invalid(field: str, message: str) -> InvalidInputError:
    return InvalidInputError(message, {"field": field})


def _require_text(value: str, field: str, max_length: int) -> None:
    if not value or not value.strip():
        raise _invalid(field, f"El campo '{field}' es obligatorio")
    if len(value) > max_length:
        raise _invalid(field, f"El campo '{field}' supera {max_length} caracteres")


def _ensure_member(value: object, enum_type: type[StrEnum], field: str) -> None:
    allowed = {member.value for member in enum_type}
    if value not in allowed:
        raise _invalid(field, f"Valor inválido para '{field}': {value!r}")


def _ensure_members(values: tuple[object, ...], enum_type: type[StrEnum], field: str) -> None:
    for value in values:
        _ensure_member(value, enum_type, field)


def validate_job(job: JobOpportunity, *, now: datetime, check_expiry: bool = False) -> None:
    """Valida las invariantes de negocio que no puede expresar el schema de la API.

    Se ejecuta tanto al crear como al editar y al cargar el seed de demo.
    """
    _require_text(job.title, "title", _MAX_TITLE)
    _require_text(job.description, "description", _MAX_DESCRIPTION)
    _ensure_member(job.status, JobStatus, "status")
    _ensure_member(job.seniority, Seniority, "seniority")

    if not 1 <= job.vacancies <= 1000:
        raise _invalid("vacancies", "La cantidad de vacantes debe estar entre 1 y 1000")

    requirements = job.requirements
    if not requirements.skills:
        raise _invalid("requirements.skills", "La oferta debe tener al menos una competencia")
    if not any(skill.kind is RequirementKind.REQUIRED for skill in requirements.skills):
        raise _invalid(
            "requirements.skills",
            "La oferta debe tener al menos un requisito obligatorio (required)",
        )

    for index, skill in enumerate(requirements.skills):
        prefix = f"requirements.skills[{index}]"
        _require_text(skill.name, f"{prefix}.name", 120)
        _ensure_member(skill.kind, RequirementKind, f"{prefix}.kind")
        if not 1 <= skill.level <= 5:
            raise _invalid(f"{prefix}.level", "El nivel de la competencia debe estar entre 1 y 5")
        if skill.years is not None and skill.years < 0:
            raise _invalid(f"{prefix}.years", "Los años de experiencia no pueden ser negativos")
        if skill.category is not None:
            _ensure_member(skill.category, SkillCategory, f"{prefix}.category")

    for index, language in enumerate(requirements.languages):
        prefix = f"requirements.languages[{index}]"
        _require_text(language.name, f"{prefix}.name", 80)
        _ensure_member(language.level, LanguageLevel, f"{prefix}.level")
        _ensure_member(language.kind, RequirementKind, f"{prefix}.kind")

    for index, education in enumerate(requirements.education):
        prefix = f"requirements.education[{index}]"
        _ensure_member(education.level, EducationLevel, f"{prefix}.level")
        _ensure_member(education.status, EducationStatus, f"{prefix}.status")
        _ensure_member(education.kind, RequirementKind, f"{prefix}.kind")
        if education.progress_percent is not None and not 0 <= education.progress_percent <= 100:
            raise _invalid(f"{prefix}.progress_percent", "El progreso debe estar entre 0 y 100")
        if education.gpa is not None and education.gpa < 0:
            raise _invalid(f"{prefix}.gpa", "El promedio no puede ser negativo")

    experience = requirements.experience
    if experience is not None:
        _ensure_member(experience.kind, RequirementKind, "requirements.experience.kind")
        if not 0 <= experience.min_years <= 60:
            raise _invalid(
                "requirements.experience.min_years",
                "La experiencia mínima debe estar entre 0 y 60 años",
            )

    for index, certification in enumerate(requirements.certifications):
        prefix = f"requirements.certifications[{index}]"
        _require_text(certification.name, f"{prefix}.name", 160)
        _ensure_member(certification.kind, RequirementKind, f"{prefix}.kind")

    academic = requirements.academic
    if academic is not None:
        if academic.min_progress_percent is not None and not (
            0 <= academic.min_progress_percent <= 100
        ):
            raise _invalid(
                "requirements.academic.min_progress_percent",
                "El progreso mínimo debe estar entre 0 y 100",
            )
        if academic.min_current_year is not None and not 1 <= academic.min_current_year <= 10:
            raise _invalid(
                "requirements.academic.min_current_year",
                "El año mínimo debe estar entre 1 y 10",
            )

    if not _COUNTRY_PATTERN.match(job.location.country):
        raise _invalid("location.country", "El país debe usar ISO 3166-1 alfa-2 (ej. AR)")
    _require_text(job.location.province, "location.province", 120)
    _require_text(job.location.city, "location.city", 120)

    _validate_work_conditions(job)

    if job.version < 1:
        raise _invalid("version", "La versión debe ser mayor o igual a 1")

    if check_expiry and job.expires_at is not None:
        expires_at = _as_utc(job.expires_at)
        if expires_at <= now:
            raise _invalid("expires_at", "La fecha de vencimiento debe ser futura")


def _validate_work_conditions(job: JobOpportunity) -> None:
    conditions = job.work_conditions
    _ensure_members(conditions.work_schedule, WorkSchedule, "work_conditions.work_schedule")
    _ensure_members(conditions.work_modality, WorkModality, "work_conditions.work_modality")
    _ensure_members(conditions.employment_type, EmploymentType, "work_conditions.employment_type")
    _ensure_members(
        conditions.contract_duration, ContractDuration, "work_conditions.contract_duration"
    )
    _ensure_members(conditions.shifts, Shift, "work_conditions.shifts")

    if conditions.hybrid_onsite_days is not None and not 0 <= conditions.hybrid_onsite_days <= 5:
        raise _invalid(
            "work_conditions.hybrid_onsite_days",
            "Los días presenciales deben estar entre 0 y 5",
        )
    if conditions.availability_start is not None:
        _ensure_member(
            conditions.availability_start,
            AvailabilityStart,
            "work_conditions.availability_start",
        )
    if conditions.travel_availability is not None:
        _ensure_member(
            conditions.travel_availability,
            TravelAvailability,
            "work_conditions.travel_availability",
        )
    if conditions.invoicing_status is not None:
        _ensure_member(
            conditions.invoicing_status, InvoicingStatus, "work_conditions.invoicing_status"
        )
    for index, country in enumerate(conditions.work_authorization):
        if not _COUNTRY_PATTERN.match(country):
            raise _invalid(
                f"work_conditions.work_authorization[{index}]",
                "Cada autorización laboral debe usar ISO 3166-1 alfa-2",
            )
    if conditions.timezone_overlap_hours is not None and not (
        0 <= conditions.timezone_overlap_hours <= 24
    ):
        raise _invalid(
            "work_conditions.timezone_overlap_hours",
            "La superposición horaria debe estar entre 0 y 24",
        )

    hours = conditions.weekly_hours
    if hours is not None:
        if not 0 <= hours.min <= 168 or not 0 <= hours.max <= 168:
            raise _invalid(
                "work_conditions.weekly_hours",
                "Las horas semanales deben estar entre 0 y 168",
            )
        if hours.min > hours.max:
            raise _invalid(
                "work_conditions.weekly_hours",
                "Las horas semanales mínimas no pueden superar a las máximas",
            )

    salary = conditions.salary
    if salary is None:
        return
    if salary.min is not None and salary.min < 0:
        raise _invalid("work_conditions.salary.min", "El sueldo mínimo no puede ser negativo")
    if salary.max is not None and salary.max < 0:
        raise _invalid("work_conditions.salary.max", "El sueldo máximo no puede ser negativo")
    if salary.min is not None and salary.max is not None and salary.min > salary.max:
        raise _invalid(
            "work_conditions.salary",
            "El sueldo mínimo no puede superar al máximo",
        )
    has_amount = salary.min is not None or salary.max is not None
    if has_amount and (salary.currency is None or salary.period is None):
        raise _invalid(
            "work_conditions.salary",
            "Si se informa un monto, la moneda y el período son obligatorios",
        )
    if salary.currency is not None:
        _ensure_member(salary.currency, Currency, "work_conditions.salary.currency")
    if salary.period is not None:
        _ensure_member(salary.period, SalaryPeriod, "work_conditions.salary.period")
    if salary.payment_mode is not None:
        _ensure_member(salary.payment_mode, PaymentMode, "work_conditions.salary.payment_mode")
    if salary.adjustment is not None:
        _ensure_member(salary.adjustment, SalaryAdjustment, "work_conditions.salary.adjustment")
    if salary.visibility is not None:
        _ensure_member(salary.visibility, SalaryVisibility, "work_conditions.salary.visibility")
    for index, variable in enumerate(salary.variable_compensation):
        prefix = f"work_conditions.salary.variable_compensation[{index}]"
        _ensure_member(variable.type, VariableCompensationType, f"{prefix}.type")
        if variable.max_percent is not None and not 0 <= variable.max_percent <= 100:
            raise _invalid(f"{prefix}.max_percent", "El porcentaje debe estar entre 0 y 100")


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def ensure_company_snapshot(snapshot: CompanySnapshot) -> None:
    """Garantía 1 de `contracts/jobs_matching.md` §4: `company_snapshot.name` no vacío.

    Se aplica al crear (data provista por auth-service) y al cargar el seed de demo;
    con esto matching y el front reciben siempre un `company_name` utilizable.
    """
    _require_text(snapshot.name, "company_snapshot.name", 200)


def require_company(principal: Principal) -> None:
    if principal.role is not Role.COMPANY:
        raise ForbiddenError("Sólo una empresa puede gestionar ofertas")


def ensure_owner(principal: Principal, job: JobOpportunity) -> None:
    require_company(principal)
    if principal.subject != job.company_id:
        raise ForbiddenError(
            "La oferta pertenece a otra empresa",
            {"job_id": job.id},
        )


def sees_unmasked(job: JobOpportunity, principal: Principal) -> bool:
    if principal.sees_everything:
        return True
    return principal.role is Role.COMPANY and principal.subject == job.company_id


def can_view(job: JobOpportunity, principal: Principal) -> bool:
    if job.status is JobStatus.ACTIVE:
        return True
    return sees_unmasked(job, principal)


def with_visible_salary(job: JobOpportunity, principal: Principal) -> JobOpportunity:
    """Oculta el sueldo a terceros cuando la visibilidad no es pública.

    La empresa dueña, un admin y los servicios internos ven el valor completo. Maching recibe
    el sueldo completo con `X-Service-Token` y aplica su propia regla de visibilidad.
    """
    salary = job.work_conditions.salary
    if salary is None or sees_unmasked(job, principal):
        return job
    if salary.visibility is SalaryVisibility.PUBLIC:
        return job
    return replace(job, work_conditions=replace(job.work_conditions, salary=None))


def parse_status_filter(status_filter: str) -> JobStatus | None:
    """Convierte `active|closed|all` al estado del repositorio (`all` -> None)."""
    if status_filter not in {"active", "closed", "all"}:
        raise InvalidInputError(
            "Filtro de estado inválido",
            {"field": "status", "allowed": ["active", "closed", "all"]},
        )
    if status_filter == "all":
        return None
    return JobStatus(status_filter)


def public_list_status(principal: Principal, status_filter: str) -> JobStatus | None:
    """En el listado público, estudiantes y empresas sólo pueden ver ofertas activas."""
    status = parse_status_filter(status_filter)
    if not principal.sees_everything and status is not JobStatus.ACTIVE:
        raise ForbiddenError(
            "Sólo se pueden listar ofertas activas",
            {"status": status_filter},
        )
    return status
