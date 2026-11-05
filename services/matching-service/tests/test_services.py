"""Casos de uso: rankings por reglas y recomendaciones de IA (persistencia, pedidos, vistas)."""

import pytest

from app.domain.errors import InvalidInputError, NotFoundError
from app.domain.recommendations import RequestStatus
from app.infrastructure.config import MatchingSettings
from app.infrastructure.container import Container, build_container
from tests.fakes import FakeTrigger, ai_batch, fixture_sources

FAKE_TOKEN = "t"  # noqa: S105 (valor ficticio de test)


@pytest.fixture
def trigger() -> FakeTrigger:
    return FakeTrigger()


@pytest.fixture
def container(trigger: FakeTrigger) -> Container:
    profiles, jobs = fixture_sources()
    return build_container(
        MatchingSettings(service_token=FAKE_TOKEN, use_mocks=True),
        profiles=profiles,
        jobs=jobs,
        trigger=trigger,
    )


def test_rank_jobs_for_student_excludes_incompatible(container: Container) -> None:
    ranking = container.matching.rank_jobs_for_student("stu-001")

    # job-003 exige licencia de conducir (condición dura) => queda afuera
    assert [item.job.id for item in ranking.items] == ["job-001", "job-002"]
    assert ranking.evaluated == 3
    assert ranking.excluded_incompatible == 1
    assert all(item.result.conditions_fit.compatible for item in ranking.items)


def test_rank_can_include_incompatible(container: Container) -> None:
    ranking = container.matching.rank_jobs_for_student("stu-002", include_incompatible=True)
    assert len(ranking.items) == 3
    assert ranking.excluded_incompatible == 0
    # compatibles primero
    flags = [item.result.conditions_fit.compatible for item in ranking.items]
    assert flags == sorted(flags, reverse=True)


def test_rank_candidates_for_job(container: Container) -> None:
    ranking = container.matching.rank_candidates_for_job("job-001", limit=2)
    # stu-002 cursa a la mañana (choque de turno) y busca sólo remoto => incompatible
    assert [item.profile.id for item in ranking.items] == ["stu-003", "stu-001"]
    scores = [item.result.score for item in ranking.items]
    assert scores == sorted(scores, reverse=True)


def test_rank_invalid_limit_and_missing_ids(container: Container) -> None:
    with pytest.raises(InvalidInputError):
        container.matching.rank_jobs_for_student("stu-001", limit=0)
    with pytest.raises(NotFoundError):
        container.matching.rank_candidates_for_job("job-999")
    with pytest.raises(InvalidInputError):
        container.matching.compute(" ", "job-001")


def test_excluding_rule_with_mock_data(container: Container) -> None:
    # stu-002 no tiene Python, excluyente en job-003
    result, _, _ = container.matching.compute("stu-002", "job-003")
    assert result.excluding_cap_applied
    assert result.score <= 40


def test_save_single_recommendation_strips_ai_score(container: Container) -> None:
    rec = container.recommendations.save(
        {
            "profile_id": "stu-001",
            "job_id": "job-001",
            "items": [{"type": "course", "skill": "Docker", "text": "...", "score": 99}],
            "origin": "AI",
            "model": "m",
            "prompt_version": "1.0.0",
            "generated_at": "2026-11-04T00:00:00Z",
            "disclaimer": "d",
        }
    )
    assert rec.origin == "AI"
    assert "score" not in rec.items[0]


def test_save_requires_ai_metadata(container: Container) -> None:
    with pytest.raises(InvalidInputError):
        container.recommendations.save({"profile_id": "stu-001", "job_id": "job-001"})
    with pytest.raises(InvalidInputError):
        container.recommendations.save(
            {
                "profile_id": "a",
                "job_id": "b",
                "origin": "RULES",
                "model": "m",
                "prompt_version": "1",
            }
        )
    with pytest.raises(InvalidInputError):
        container.recommendations.save_batch({"mode": "student", "entries": []})
    with pytest.raises(InvalidInputError):
        container.recommendations.save_batch({"mode": "otro", "subject_id": "x", "entries": []})


def test_request_analysis_flow_completed_by_batch(
    container: Container, trigger: FakeTrigger
) -> None:
    def persist(request_id: str, mode: str, subject_id: str) -> None:
        container.recommendations.save_batch(
            ai_batch(
                mode,
                subject_id,
                [{"job_id": "job-001", "fit_reasons": ["Python"], "score": 1, "priority": "alta"}],
                request_id,
            )
        )

    trigger.on_call = persist
    request = container.recommendations.request_analysis("student", "stu-001")
    assert request.status is RequestStatus.PENDING

    done = container.recommendations.run_analysis(request.id, limit=5)
    assert done.status is RequestStatus.COMPLETED
    assert trigger.calls[0]["subject_id"] == "stu-001"

    view = container.recommendations.student_view("stu-001")
    assert view["rule_based"]["origin"] == "RULES"
    ai = view["ai_recommendations"]
    assert ai["origin"] == "AI"
    assert ai["status"] == "ready"
    assert ai["model"] == "nvidia/modelo-ficticio"
    item = ai["items"][0]
    assert item["job_id"] == "job-001"
    assert "score" not in item["content"]
    assert item["content"]["fit_reasons"] == ["Python"]


def test_request_analysis_failure_is_recorded() -> None:
    failing = FakeTrigger(fail=True)
    profiles, jobs = fixture_sources()
    c = build_container(
        MatchingSettings(service_token=FAKE_TOKEN), profiles=profiles, jobs=jobs, trigger=failing
    )
    request = c.recommendations.request_analysis("company", "job-001")

    result = c.recommendations.run_analysis(request.id, limit=3)
    assert result.status is RequestStatus.FAILED
    assert result.error["code"] == "UPSTREAM_ERROR"
    view = c.recommendations.company_view("job-001")
    assert view["ai_recommendations"]["status"] == "failed"


def test_request_without_batch_is_closed_as_completed(container: Container) -> None:
    request = container.recommendations.request_analysis("company", "job-001")
    assert container.recommendations.run_analysis(request.id, 3).status is RequestStatus.COMPLETED


def test_request_analysis_validates_subject(container: Container) -> None:
    with pytest.raises(InvalidInputError):
        container.recommendations.request_analysis("student", "")
    with pytest.raises(NotFoundError):
        container.recommendations.request_analysis("student", "stu-999")
    with pytest.raises(NotFoundError):
        container.recommendations.get_request("req-nope")


def test_company_view_hides_hidden_expected_salary(container: Container) -> None:
    container.recommendations.save_batch(
        ai_batch("company", "job-002", [{"profile_id": "stu-002", "justification": "ok"}])
    )
    view = container.recommendations.company_view("job-002")
    items = view["rule_based"]["items"]
    stu002 = next(i for i in items if i["candidate"]["profile_id"] == "stu-002")
    # stu-002 marcó su pretensión como hidden => la empresa no ve montos
    salary_fit = stu002["match"]["conditions_fit"]["salary_fit"]
    assert salary_fit is None or salary_fit["expected_monthly"] is None
    # El snapshot del candidato no trae datos personales
    assert "personal" not in stu002["candidate"]
    assert "display_name" not in stu002["candidate"]
    assert view["ai_recommendations"]["items"][0]["profile_id"] == "stu-002"


def test_not_requested_status(container: Container) -> None:
    view = container.recommendations.student_view("stu-003")
    assert view["ai_recommendations"]["status"] == "not_requested"
    assert view["ai_recommendations"]["items"] == []
