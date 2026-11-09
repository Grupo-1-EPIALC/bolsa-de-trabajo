"""Seed de demo y contrato: 12 ofertas mapeables por matching y OpenAPI coherente."""

import json
from datetime import UTC, datetime
from pathlib import Path

from app.domain.enums import JobStatus, RequirementKind
from app.domain.rules import validate_job
from app.infrastructure.repositories.codec import job_from_document, job_to_document
from app.infrastructure.repositories.memory_jobs import InMemoryJobRepository
from app.infrastructure.seed import load_seed_jobs, seed_repository
from app.main import app

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
SEED_PATH = SERVICE_ROOT / "app" / "infrastructure" / "data" / "jobs_seed.json"
MATCHING_SEED = REPO_ROOT / "services" / "matching-service" / "app" / "data" / "mock" / "jobs.json"
NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


def test_seed_has_the_twelve_demo_offers() -> None:
    jobs = load_seed_jobs(SEED_PATH)
    assert len(jobs) == 12
    assert [job.id for job in jobs] == [f"job-{index:03d}" for index in range(1, 13)]
    assert all(job.status is JobStatus.ACTIVE for job in jobs)


def test_seed_matches_matching_pool_ids() -> None:
    jobs = load_seed_jobs(SEED_PATH)
    matching = json.loads(MATCHING_SEED.read_text(encoding="utf-8"))
    assert [job.id for job in jobs] == [item["id"] for item in matching]
    assert [job.company_id for job in jobs] == [item["company_id"] for item in matching]


def test_seed_passes_business_validation() -> None:
    for offer in load_seed_jobs(SEED_PATH):
        validate_job(offer, now=NOW, check_expiry=False)


def test_seed_has_fields_required_by_matching() -> None:
    for offer in load_seed_jobs(SEED_PATH):
        assert offer.company_snapshot.name
        assert offer.requirements.skills
        assert any(skill.kind is RequirementKind.REQUIRED for skill in offer.requirements.skills)
        assert all(skill.normalized for skill in offer.requirements.skills)
        assert all(1 <= skill.level <= 5 for skill in offer.requirements.skills)
        assert offer.requirements.experience is not None
        assert offer.work_conditions.work_schedule
        assert offer.work_conditions.work_modality


def test_seed_roundtrip_keeps_all_blocks() -> None:
    for offer in load_seed_jobs(SEED_PATH):
        assert job_from_document(job_to_document(offer)) == offer


def test_seed_is_loaded_only_when_repository_is_empty() -> None:
    repository = InMemoryJobRepository()
    assert seed_repository(repository, SEED_PATH) == 12
    assert repository.count() == 12
    assert seed_repository(repository, SEED_PATH) == 0
    assert repository.count() == 12


def test_openapi_declares_all_endpoints() -> None:
    """El OpenAPI vivo (/api/v1/jobs/openapi.json) es la fuente de verdad (contracts/jobs.md)."""
    paths = app.openapi()["paths"]
    assert "/api/v1/jobs" in paths
    assert "/api/v1/jobs/{job_id}" in paths
    assert "/api/v1/companies/me/searches" in paths
    assert "/health" in paths
    assert {"get", "post"} <= set(paths["/api/v1/jobs"])
    assert {"get", "patch", "delete"} <= set(paths["/api/v1/jobs/{job_id}"])


def test_listing_supports_limit_alias() -> None:
    parameters = app.openapi()["paths"]["/api/v1/jobs"]["get"]["parameters"]
    names = {parameter["name"] for parameter in parameters}
    assert {"status", "page", "size", "limit"} <= names
