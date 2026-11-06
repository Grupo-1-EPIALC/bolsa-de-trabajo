"""Fixtures comunes: contenedor con dobles, cliente HTTP y un perfil completo de ejemplo."""

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_container
from app.domain.auth import Principal, Role
from app.infrastructure.config import ProfileSettings
from app.infrastructure.container import Container, build_container
from app.infrastructure.repositories.memory import InMemoryProfileRepository
from app.main import app
from tests import jwt_helpers
from tests.fakes import (
    FakeAccounts,
    FakeCvWebhookGateway,
    FixedClock,
    RecordingPublisher,
    SequentialIds,
)

SERVICE_TOKEN = "token-de-servicio-de-prueba"  # noqa: S105 - ficticio
FAKE_JWT = "jwt-ficticio"


@pytest.fixture
def publisher() -> RecordingPublisher:
    return RecordingPublisher()


@pytest.fixture
def webhook() -> FakeCvWebhookGateway:
    return FakeCvWebhookGateway()


@pytest.fixture
def container(
    tmp_path: Path,
    publisher: RecordingPublisher,
    webhook: FakeCvWebhookGateway,
) -> Container:
    settings = ProfileSettings(cv_storage_path=str(tmp_path / "cvs"), service_token=SERVICE_TOKEN)
    return build_container(
        settings,
        repository=InMemoryProfileRepository(),
        webhook=webhook,
        publisher=publisher,
        accounts=FakeAccounts(),
        tokens=jwt_helpers.verifier(),
        clock=FixedClock(),
        ids=SequentialIds(),
        seed=False,
    )


@pytest.fixture
def seeded(tmp_path: Path, publisher: RecordingPublisher) -> Container:
    settings = ProfileSettings(cv_storage_path=str(tmp_path / "cvs"), service_token=SERVICE_TOKEN)
    return build_container(
        settings,
        repository=InMemoryProfileRepository(),
        webhook=FakeCvWebhookGateway(),
        publisher=publisher,
        accounts=FakeAccounts(),
        tokens=jwt_helpers.verifier(),
        clock=FixedClock(),
        ids=SequentialIds(),
        seed=True,
    )


@pytest.fixture
def client(container: Container) -> Iterator[TestClient]:
    app.dependency_overrides[get_container] = lambda: container
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def student() -> Principal:
    return Principal(subject=jwt_helpers.STUDENT_NEW, role=Role.STUDENT, access_token=FAKE_JWT)


def student_headers() -> dict[str, str]:
    return jwt_helpers.bearer(jwt_helpers.STUDENT_NEW, "student")


def service_headers() -> dict[str, str]:
    return {"X-Service-Token": SERVICE_TOKEN}


def wait_job(fetch: Any, job_id: str, timeout: float = 5.0) -> dict[str, Any]:
    """Espera a que termine el worker del CV (el doble de n8n responde al instante)."""
    deadline = time.monotonic() + timeout
    while True:
        snapshot: dict[str, Any] = fetch(job_id)
        if snapshot["status"] != "processing" or time.monotonic() > deadline:
            return snapshot
        time.sleep(0.02)


COMPLETE_PROFILE: dict[str, Any] = {
    "personal": {
        "name": "Lucía Fernández",
        "email": "lucia.ficticia@example.com",
        "phone": "+54 11 5555-0000",
        "birth_year": 2002,
        "location": {"country": "AR", "province": "Buenos Aires", "city": "San Isidro"},
    },
    "headline": "Estudiante de Sistemas · Backend Python",
    "summary": "Desarrolladora backend en formación, con foco en APIs REST y bases de datos.",
    "academic_status": {
        "institution": "UTN FRBA",
        "career": "Ingeniería en Sistemas de Información",
        "current_year": 4,
        "progress_percent": 70,
        "student_shift": ["evening"],
    },
    "target": {"roles": ["Desarrolladora backend"], "seniority": "junior"},
    "work_conditions": {
        "work_schedule": ["part_time"],
        "work_modality": ["hybrid", "remote"],
        "employment_type": ["employee", "internship"],
        "weekly_hours": {"min": 20, "max": 30},
        "availability_start": "immediate",
        "salary": {
            "min": 600000,
            "max": 750000,
            "currency": "ARS",
            "period": "month",
            "visibility": "on_match",
        },
    },
    "skills": [
        {"name": "python3", "level": 4},
        {"name": "Postgres", "level": 3},
        {"name": "Git", "level": 3},
        {"name": "Trabajo en equipo", "level": 4},
    ],
    "experience": [
        {
            "company": "FinTech Ficticia",
            "role": "Desarrolladora Backend",
            "start": "2025-03",
            "end": "actual",
            "description": "- APIs REST con FastAPI\n- Tests con Pytest",
            "skills_used": ["FastAPI", "Pytest"],
        }
    ],
    "education": [
        {
            "institution": "UTN FRBA",
            "degree": "Ingeniería en Sistemas de Información",
            "level": "university",
            "status": "in_progress",
            "start": "2022",
        }
    ],
    "languages": [{"name": "Inglés", "level": "B2"}, {"name": "Español", "level": "native"}],
    "certifications": [
        {"name": "Curso de Docker Ficticio", "issuer": "Academia Demo", "year": 2025}
    ],
    "links": [{"type": "github", "url": "https://github.com/lucia-ficticia"}],
    "consents": {"data_processing": True, "ai_processing": True},
    "inclusion": {"disability_certificate": True, "accessibility_needs": "Dato privado"},
}
