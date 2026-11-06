"""Reglas de dominio: validación, permisos y visibilidad del sueldo."""

from dataclasses import replace
from datetime import timedelta

import pytest

from app.domain.auth import SERVICE_PRINCIPAL, Principal, Role
from app.domain.enums import (
    JobStatus,
    RequirementKind,
    SalaryVisibility,
)
from app.domain.errors import ForbiddenError, InvalidInputError
from app.domain.models import SalaryRange, WeeklyHours
from app.domain.normalization import normalize_text
from app.domain.rules import (
    can_view,
    ensure_owner,
    parse_status_filter,
    public_list_status,
    validate_job,
    with_visible_salary,
)
from tests.builders import (
    ADMIN_001,
    COMPANY_001,
    COMPANY_002,
    NOW,
    STUDENT_001,
    conditions,
    job,
    requirements,
    salary,
    skill,
)

STUDENT = Principal(subject=STUDENT_001, role=Role.STUDENT)
COMPANY = Principal(subject=COMPANY_001, role=Role.COMPANY, access_token="token")  # noqa: S106
OTHER_COMPANY = Principal(
    subject=COMPANY_002, role=Role.COMPANY, access_token="token"  # noqa: S106
)
ADMIN = Principal(subject=ADMIN_001, role=Role.ADMIN)


def test_valid_job_passes_validation() -> None:
    validate_job(job(), now=NOW)


def test_offer_needs_at_least_one_required_skill() -> None:
    only_desired = replace(
        job(), requirements=requirements(skills=(skill("Python", kind=RequirementKind.DESIRED),))
    )
    with pytest.raises(InvalidInputError) as error:
        validate_job(only_desired, now=NOW)
    assert error.value.details["field"] == "requirements.skills"


def test_skill_level_must_be_between_one_and_five() -> None:
    invalid = replace(job(), requirements=requirements(skills=(skill("Python", level=0),)))
    with pytest.raises(InvalidInputError):
        validate_job(invalid, now=NOW)


def test_vacancies_must_be_positive() -> None:
    with pytest.raises(InvalidInputError):
        validate_job(replace(job(), vacancies=0), now=NOW)


def test_salary_min_cannot_exceed_max() -> None:
    invalid = replace(
        job(),
        work_conditions=conditions(job_salary=salary(minimum=2_000, maximum=1_000)),
    )
    with pytest.raises(InvalidInputError):
        validate_job(invalid, now=NOW)


def test_salary_with_amount_requires_currency_and_period() -> None:
    invalid = replace(
        job(),
        work_conditions=conditions(
            job_salary=SalaryRange(min=100, max=200, visibility=SalaryVisibility.PUBLIC)
        ),
    )
    with pytest.raises(InvalidInputError):
        validate_job(invalid, now=NOW)


def test_weekly_hours_min_cannot_exceed_max() -> None:
    invalid = replace(
        job(),
        work_conditions=replace(conditions(), weekly_hours=WeeklyHours(min=40, max=20)),
    )
    with pytest.raises(InvalidInputError):
        validate_job(invalid, now=NOW)


def test_expiry_must_be_future_only_when_requested() -> None:
    expired = replace(job(), expires_at=NOW - timedelta(days=1))
    validate_job(expired, now=NOW)
    with pytest.raises(InvalidInputError):
        validate_job(expired, now=NOW, check_expiry=True)


def test_country_must_be_iso_alpha2() -> None:
    invalid = replace(job(), location=replace(job().location, country="Argentina"))
    with pytest.raises(InvalidInputError):
        validate_job(invalid, now=NOW)


def test_public_salary_is_visible_to_everyone() -> None:
    offer = job()
    assert with_visible_salary(offer, STUDENT).work_conditions.salary is not None
    assert with_visible_salary(offer, OTHER_COMPANY).work_conditions.salary is not None


@pytest.mark.parametrize("visibility", [SalaryVisibility.ON_MATCH, SalaryVisibility.HIDDEN])
def test_private_salary_is_masked_for_third_parties(visibility: SalaryVisibility) -> None:
    offer = job(job_conditions=conditions(job_salary=salary(visibility=visibility)))
    assert with_visible_salary(offer, STUDENT).work_conditions.salary is None
    assert with_visible_salary(offer, OTHER_COMPANY).work_conditions.salary is None
    assert with_visible_salary(offer, COMPANY).work_conditions.salary is not None
    assert with_visible_salary(offer, ADMIN).work_conditions.salary is not None
    assert with_visible_salary(offer, SERVICE_PRINCIPAL).work_conditions.salary is not None


def test_job_without_salary_stays_without_salary() -> None:
    offer = replace(job(), work_conditions=conditions(job_salary=SalaryRange()))
    offer = replace(offer, work_conditions=replace(offer.work_conditions, salary=None))
    assert with_visible_salary(offer, STUDENT).work_conditions.salary is None


def test_closed_offer_is_only_visible_to_owner_admin_or_service() -> None:
    closed = job(status=JobStatus.CLOSED)
    assert not can_view(closed, STUDENT)
    assert not can_view(closed, OTHER_COMPANY)
    assert can_view(closed, COMPANY)
    assert can_view(closed, ADMIN)
    assert can_view(closed, SERVICE_PRINCIPAL)
    assert can_view(job(), STUDENT)


def test_owner_rules() -> None:
    offer = job()
    assert ensure_owner(COMPANY, offer) is None
    with pytest.raises(ForbiddenError):
        ensure_owner(OTHER_COMPANY, offer)
    with pytest.raises(ForbiddenError):
        ensure_owner(STUDENT, offer)


def test_status_filter_rules() -> None:
    assert public_list_status(STUDENT, "active") is JobStatus.ACTIVE
    assert public_list_status(ADMIN, "closed") is JobStatus.CLOSED
    assert public_list_status(SERVICE_PRINCIPAL, "all") is None
    with pytest.raises(ForbiddenError):
        public_list_status(STUDENT, "closed")
    with pytest.raises(InvalidInputError):
        parse_status_filter("draft")


def test_normalization_removes_accents_and_extra_spaces() -> None:
    assert normalize_text("  Inglés   Técnico ") == "ingles tecnico"
