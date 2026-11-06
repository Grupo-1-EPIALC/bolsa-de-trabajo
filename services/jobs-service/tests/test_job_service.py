"""Casos de uso de JobService: creación, edición, cierre, listados y eventos."""

from dataclasses import replace

import pytest

from app.domain.auth import Principal, Role
from app.domain.enums import JobStatus, SalaryVisibility
from app.domain.errors import (
    ForbiddenError,
    InvalidInputError,
    NotFoundError,
    UnauthorizedError,
    UpstreamError,
)
from app.domain.models import SalaryRange, WorkConditions
from tests.builders import (
    ADMIN_001,
    COMPANY_001,
    COMPANY_002,
    NOW,
    STUDENT_001,
    conditions,
    draft,
    job,
    salary,
)
from tests.fakes import FixedClock, RecordingPublisher
from tests.jwt_helpers import COMPANY_001 as JWT_COMPANY_001

COMPANY = Principal(
    subject=COMPANY_001, role=Role.COMPANY, access_token="access-token"  # noqa: S106
)
OTHER_COMPANY = Principal(
    subject=COMPANY_002, role=Role.COMPANY, access_token="other-token"  # noqa: S106
)
STUDENT = Principal(
    subject=STUDENT_001, role=Role.STUDENT, access_token="student-token"  # noqa: S106
)
ADMIN = Principal(subject=ADMIN_001, role=Role.ADMIN)


def test_create_assigns_company_snapshot_and_publishes_event(
    container, repository, directory, publisher
) -> None:
    created = container.jobs.create(COMPANY, draft(), access_token=COMPANY.access_token)

    assert created.id == "job-100"
    assert created.company_id == COMPANY_001
    assert created.status is JobStatus.ACTIVE
    assert created.version == 1
    assert created.published_at == NOW
    assert created.company_snapshot.name == "Empresa de Prueba S.A."
    assert repository.get(created.id) == created
    assert [event.id for event in publisher.jobs] == [created.id]
    assert directory.calls == ["access-token"]


def test_create_uses_company_id_from_principal_not_from_body(container, repository) -> None:
    created = container.jobs.create(COMPANY, draft(), access_token=COMPANY.access_token)
    assert created.company_id == COMPANY_001
    assert repository.get(created.id) is not None


def test_create_without_access_token_is_unauthorized(container) -> None:
    anonymous_company = Principal(subject=COMPANY_001, role=Role.COMPANY)
    with pytest.raises(UnauthorizedError):
        container.jobs.create(anonymous_company, draft(), access_token=None)


def test_student_cannot_create(container) -> None:
    with pytest.raises(ForbiddenError):
        container.jobs.create(STUDENT, draft(), access_token=STUDENT.access_token)


def test_directory_failure_aborts_create(container, repository) -> None:
    broken = Principal(
        subject=COMPANY_001, role=Role.COMPANY, access_token="bad-token"  # noqa: S106
    )
    with pytest.raises(UpstreamError):
        container.jobs.create(broken, draft(), access_token=broken.access_token)
    assert repository.count() == 0


def test_publisher_failure_does_not_break_create(
    container, repository, publisher: RecordingPublisher
) -> None:
    publisher.fail = True
    created = container.jobs.create(COMPANY, draft(), access_token=COMPANY.access_token)
    assert repository.get(created.id) == created


def test_other_company_cannot_edit_offer(container, repository) -> None:
    offer = job(company_id=COMPANY_002)
    repository.add(offer)

    with pytest.raises(ForbiddenError) as error:
        container.jobs.update(COMPANY, offer.id, {"title": "Otro título"})
    assert error.value.details["job_id"] == offer.id
    assert repository.get(offer.id) == offer


def test_owner_can_edit_and_version_increases(container, repository, clock: FixedClock) -> None:
    offer = job()
    repository.add(offer)
    clock.advance(hours=1)

    updated = container.jobs.update(COMPANY, offer.id, {"title": "Python Semi-Senior"})

    assert updated.title == "Python Semi-Senior"
    assert updated.version == 2
    assert updated.updated_at == clock.now()
    assert repository.get(offer.id) == updated


def test_update_without_fields_is_invalid(container, repository) -> None:
    offer = job()
    repository.add(offer)
    with pytest.raises(InvalidInputError):
        container.jobs.update(COMPANY, offer.id, {})


def test_update_rejects_server_managed_fields(container, repository) -> None:
    offer = job()
    repository.add(offer)
    with pytest.raises(InvalidInputError):
        container.jobs.update(COMPANY, offer.id, {"company_id": COMPANY_002})


def test_update_cannot_close_with_patch(container, repository) -> None:
    offer = job()
    repository.add(offer)
    with pytest.raises(InvalidInputError):
        container.jobs.update(COMPANY, offer.id, {"status": "closed"})


def test_update_can_clear_work_conditions(container, repository) -> None:
    offer = job()
    repository.add(offer)

    updated = container.jobs.update(COMPANY, offer.id, {"work_conditions": None})

    assert updated.work_conditions == WorkConditions()


def test_update_rejects_past_expiry(container, repository) -> None:
    offer = job()
    repository.add(offer)
    with pytest.raises(InvalidInputError):
        container.jobs.update(COMPANY, offer.id, {"expires_at": NOW.replace(year=2020)})


def test_close_is_idempotent(container, repository) -> None:
    offer = job()
    repository.add(offer)

    closed = container.jobs.close(COMPANY, offer.id)
    closed_again = container.jobs.close(COMPANY, offer.id)

    assert closed.status is JobStatus.CLOSED
    assert closed.version == 2
    assert closed_again == closed


def test_other_company_cannot_close(container, repository) -> None:
    offer = job(company_id=COMPANY_002)
    repository.add(offer)
    with pytest.raises(ForbiddenError):
        container.jobs.close(COMPANY, offer.id)


def test_owner_can_reopen_a_closed_offer(container, repository, clock: FixedClock) -> None:
    offer = job()
    repository.add(offer)
    container.jobs.close(COMPANY, offer.id)
    clock.advance(hours=2)

    reopened = container.jobs.update(COMPANY, offer.id, {"status": "active"})

    assert reopened.status is JobStatus.ACTIVE
    assert reopened.version == 3
    assert reopened.published_at == clock.now()


def test_reopen_active_offer_is_a_noop(container, repository) -> None:
    offer = job()
    repository.add(offer)

    same = container.jobs.update(COMPANY, offer.id, {"status": "active"})

    assert same == offer
    assert repository.get(offer.id) == offer


def test_closed_offer_is_hidden_from_students(container, repository) -> None:
    offer = job(status=JobStatus.CLOSED)
    repository.add(offer)

    with pytest.raises(NotFoundError):
        container.jobs.get(STUDENT, offer.id)
    assert container.jobs.get(COMPANY, offer.id).status is JobStatus.CLOSED


def test_get_unknown_offer(container) -> None:
    with pytest.raises(NotFoundError):
        container.jobs.get(STUDENT, "job-999")


def test_list_jobs_masks_salary_and_hides_closed(container, repository) -> None:
    hidden = job(
        job_id="job-001",
        job_conditions=conditions(job_salary=salary(visibility=SalaryVisibility.HIDDEN)),
    )
    closed = job(job_id="job-002", status=JobStatus.CLOSED)
    repository.add(hidden)
    repository.add(closed)

    page = container.jobs.list_jobs(STUDENT)

    assert page.total == 1
    assert page.items[0].id == "job-001"
    assert page.items[0].work_conditions.salary is None


def test_admin_can_list_all_statuses_and_see_salary(container, repository) -> None:
    hidden = job(
        job_id="job-001",
        job_conditions=conditions(job_salary=salary(visibility=SalaryVisibility.HIDDEN)),
    )
    closed = job(job_id="job-002", status=JobStatus.CLOSED)
    repository.add(hidden)
    repository.add(closed)

    page = container.jobs.list_jobs(ADMIN, status_filter="all")

    assert page.total == 2
    assert all(item.work_conditions.salary is not None for item in page.items)


def test_student_cannot_list_closed(container) -> None:
    with pytest.raises(ForbiddenError):
        container.jobs.list_jobs(STUDENT, status_filter="closed")


def test_my_searches_only_returns_own_offers(container, repository) -> None:
    repository.add(job(job_id="job-001", company_id=COMPANY_001))
    repository.add(job(job_id="job-002", company_id=COMPANY_001, status=JobStatus.CLOSED))
    repository.add(job(job_id="job-003", company_id=COMPANY_002))

    active = container.jobs.list_my_searches(COMPANY)
    closed = container.jobs.list_my_searches(COMPANY, status_filter="closed")
    everything = container.jobs.list_my_searches(COMPANY, status_filter="all")

    assert [item.id for item in active.items] == ["job-001"]
    assert [item.id for item in closed.items] == ["job-002"]
    assert {item.id for item in everything.items} == {"job-001", "job-002"}


def test_my_searches_requires_company_role(container) -> None:
    with pytest.raises(ForbiddenError):
        container.jobs.list_my_searches(STUDENT)


def test_pagination_metadata(container, repository) -> None:
    for index in range(1, 6):
        repository.add(job(job_id=f"job-{index:03d}"))
    page = container.jobs.list_jobs(STUDENT, page=2, size=2)
    assert page.total == 5
    assert page.page == 2
    assert page.size == 2
    assert page.pages == 3
    assert len(page.items) == 2


def test_limit_alias_is_applied_by_api(container, repository, client) -> None:
    for index in range(1, 4):
        repository.add(job(job_id=f"job-{index:03d}"))
    response = client.get("/api/v1/jobs?limit=2", headers={"Authorization": _bearer(STUDENT_001)})
    assert response.status_code == 200
    assert response.json()["size"] == 2
    assert len(response.json()["items"]) == 2


def _bearer(subject: str) -> str:
    # Import diferido para no acoplar los tests de servicio al helper de JWT.
    from tests.jwt_helpers import make_token

    return f"Bearer {make_token(subject, 'student')}"


def test_create_then_get_returns_full_offer(container) -> None:
    created = container.jobs.create(COMPANY, draft(), access_token=COMPANY.access_token)
    assert container.jobs.get(STUDENT, created.id).id == created.id


def test_offer_from_seed_shape_can_be_updated(container, repository) -> None:
    offer = replace(job(), version=3)
    repository.add(offer)
    updated = container.jobs.update(COMPANY, offer.id, {"vacancies": 2})
    assert updated.version == 4
    assert updated.vacancies == 2
    assert updated.work_conditions.salary == offer.work_conditions.salary


def test_company_id_constant_matches_jwt_helper() -> None:
    assert COMPANY_001 == JWT_COMPANY_001


def test_salary_helper_defaults_are_public() -> None:
    assert salary().visibility is SalaryVisibility.PUBLIC
    assert isinstance(salary(minimum=None, maximum=None), SalaryRange)
