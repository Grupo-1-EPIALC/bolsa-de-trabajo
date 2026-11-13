"""Persistencia de configuración y recomendaciones entre instancias del servicio."""

from pathlib import Path

import pytest

from app.domain.auth import Principal, Role
from app.infrastructure.config import MatchingSettings
from app.infrastructure.container import Container, build_container
from tests.fakes import FakeTrigger, ai_batch, fixture_sources
from tests.jwt_helpers import verifier

ADMIN = Principal(subject="admin-001", role=Role.ADMIN)


def _container(database_url: str) -> Container:
    profiles, jobs = fixture_sources()
    return build_container(
        MatchingSettings(
            service_token="svc-token",  # noqa: S106 (valor ficticio de test)
            database_url=database_url,
            database_schema="",
            use_mocks=True,
        ),
        profiles=profiles,
        jobs=jobs,
        trigger=FakeTrigger(),
        tokens=verifier(),
    )


def test_settings_requests_and_recommendations_survive_restart(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'matching.sqlite'}"
    first = _container(database_url)
    assert first.persistence is not None

    updated = first.settings_admin.update(
        ADMIN,
        {"student_jobs_limit": 3, "company_candidates_limit": 4},
    )
    assert updated.student_jobs_limit == 3

    request = first.recommendations.request_analysis("student", "stu-001")
    first.recommendations.save_batch(
        ai_batch(
            "student",
            "stu-001",
            [{"job_id": "job-001", "justification": "Primera versión"}],
            request.id,
        )
    )
    first.recommendations.save_batch(
        ai_batch(
            "student",
            "stu-001",
            [{"job_id": "job-001", "justification": "Versión actualizada"}],
        )
    )
    first.recommendations.save_batch(
        ai_batch(
            "company",
            "job-001",
            [{"profile_id": "stu-001", "justification": "Candidato recomendado"}],
        )
    )
    first.recommendations.save_batch(
        ai_batch(
            "training",
            "stu-001",
            [{"items": [{"type": "skill", "skill": "Docker", "text": "Practicar Docker"}]}],
        )
    )
    first.persistence.dispose()

    second = _container(database_url)
    assert second.persistence is not None
    try:
        settings = second.settings_admin.get(ADMIN)
        assert settings.student_jobs_limit == 3
        assert settings.company_candidates_limit == 4

        persisted_request = second.recommendations.get_request(request.id)
        assert persisted_request is not None
        assert persisted_request.status.value == "completed"

        student = second.recommendations.student_view("stu-001")
        assert student["ai_recommendations"]["items"][0]["content"]["justification"] == (
            "Versión actualizada"
        )

        company = second.recommendations.company_view("job-001")
        assert company["ai_recommendations"]["items"][0]["content"]["justification"] == (
            "Candidato recomendado"
        )

        training = second.recommendations.training_view("stu-001")
        assert training["ai_recommendations"]["items"][0]["skill"] == "Docker"
    finally:
        second.persistence.dispose()


def test_real_sources_require_database_url() -> None:
    with pytest.raises(ValueError, match="DATABASE_URL es obligatorio"):
        build_container(MatchingSettings(use_mocks=False))
