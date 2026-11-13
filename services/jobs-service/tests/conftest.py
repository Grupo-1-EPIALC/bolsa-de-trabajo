"""Fixtures compartidos: contenedor con dobles y cliente HTTP."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_container
from app.infrastructure.config import JobsSettings
from app.infrastructure.container import Container, build_container
from app.infrastructure.repositories.memory_jobs import InMemoryJobRepository
from app.main import app
from tests.fakes import (
    FakeApplicantDirectory,
    FakeCompanyDirectory,
    FixedClock,
    RecordingPublisher,
    SequentialIds,
)
from tests.jwt_helpers import verifier


@pytest.fixture
def repository() -> InMemoryJobRepository:
    return InMemoryJobRepository()


@pytest.fixture
def directory() -> FakeCompanyDirectory:
    return FakeCompanyDirectory()


@pytest.fixture
def applicants() -> FakeApplicantDirectory:
    return FakeApplicantDirectory()


@pytest.fixture
def publisher() -> RecordingPublisher:
    return RecordingPublisher()


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def ids() -> SequentialIds:
    return SequentialIds()


@pytest.fixture
def container(
    repository: InMemoryJobRepository,
    directory: FakeCompanyDirectory,
    applicants: FakeApplicantDirectory,
    publisher: RecordingPublisher,
    clock: FixedClock,
    ids: SequentialIds,
) -> Container:
    settings = JobsSettings(service_token="svc-token", seed_demo=False)  # noqa: S106
    return build_container(
        settings,
        repository=repository,
        directory=directory,
        applicants=applicants,
        publisher=publisher,
        clock=clock,
        ids=ids,
        tokens=verifier(),
        seed=False,
    )


@pytest.fixture
def client(container: Container) -> Iterator[TestClient]:
    app.dependency_overrides[get_container] = lambda: container
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
