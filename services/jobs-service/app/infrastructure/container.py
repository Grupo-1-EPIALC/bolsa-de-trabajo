"""Raíz de composición de jobs-service."""

from dataclasses import dataclass

from app.application.job_service import JobService
from app.domain.ports import (
    Clock,
    CompanyDirectory,
    EventPublisher,
    IdGenerator,
    JobRepository,
    TokenVerifier,
)
from app.infrastructure.clock import UtcClock, UuidIdGenerator
from app.infrastructure.company_directory import HttpCompanyDirectory
from app.infrastructure.config import JobsSettings
from app.infrastructure.events.n8n import HttpN8nEventPublisher
from app.infrastructure.jwt_verifier import JwksKeyResolver, JwtTokenVerifier
from app.infrastructure.repositories.memory_jobs import InMemoryJobRepository
from app.infrastructure.repositories.sqlalchemy_jobs import SqlAlchemyJobRepository
from app.infrastructure.seed import seed_repository


@dataclass(frozen=True)
class Container:
    settings: JobsSettings
    jobs: JobService
    tokens: TokenVerifier
    repository: JobRepository


def build_container(
    settings: JobsSettings,
    *,
    repository: JobRepository | None = None,
    directory: CompanyDirectory | None = None,
    publisher: EventPublisher | None = None,
    clock: Clock | None = None,
    ids: IdGenerator | None = None,
    tokens: TokenVerifier | None = None,
    seed: bool | None = None,
) -> Container:
    if repository is None:
        repository = (
            SqlAlchemyJobRepository(settings.database_url, schema=settings.database_schema)
            if settings.database_url
            else InMemoryJobRepository()
        )

    should_seed = settings.seed_demo if seed is None else seed
    if should_seed:
        seed_repository(repository, settings.seed_path)

    current_clock = clock or UtcClock()
    if directory is None:
        directory = HttpCompanyDirectory(settings.auth_service_url, settings.http_timeout_seconds)
    if publisher is None:
        publisher = HttpN8nEventPublisher(
            settings.n8n_webhook_base_url,
            settings.service_token,
            settings.event_timeout_seconds,
        )
    if ids is None:
        ids = UuidIdGenerator()
    if tokens is None:
        tokens = JwtTokenVerifier(
            JwksKeyResolver(settings.jwks_url),
            settings.jwt_issuer,
            settings.jwt_audience,
        )

    jobs = JobService(
        repository=repository,
        directory=directory,
        publisher=publisher,
        clock=current_clock,
        ids=ids,
    )
    return Container(settings=settings, jobs=jobs, tokens=tokens, repository=repository)
