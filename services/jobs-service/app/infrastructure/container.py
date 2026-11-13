"""Raíz de composición de jobs-service."""

from dataclasses import dataclass

from app.application.account_events_service import AccountEventsService
from app.application.application_service import ApplicationService
from app.application.job_service import JobService
from app.domain.ports import (
    ApplicantDirectory,
    ApplicationRepository,
    Clock,
    CompanyDirectory,
    DeletedAccounts,
    EventPublisher,
    IdGenerator,
    JobRepository,
    TokenVerifier,
)
from app.infrastructure.applicant_directory import HttpApplicantDirectory
from app.infrastructure.clock import UtcClock, UuidIdGenerator
from app.infrastructure.company_directory import HttpCompanyDirectory
from app.infrastructure.config import JobsSettings
from app.infrastructure.events.n8n import HttpN8nEventPublisher
from app.infrastructure.jwt_verifier import JwksKeyResolver, JwtTokenVerifier
from app.infrastructure.repositories.applications import (
    InMemoryApplicationRepository,
    SqlAlchemyApplicationRepository,
)
from app.infrastructure.repositories.deleted_accounts import (
    InMemoryDeletedAccounts,
    SqlAlchemyDeletedAccounts,
)
from app.infrastructure.repositories.memory_jobs import InMemoryJobRepository
from app.infrastructure.repositories.sqlalchemy_jobs import SqlAlchemyJobRepository
from app.infrastructure.seed import seed_repository


@dataclass(frozen=True)
class Container:
    settings: JobsSettings
    jobs: JobService
    applications: ApplicationService
    tokens: TokenVerifier
    repository: JobRepository
    account_events: AccountEventsService
    deleted_accounts: DeletedAccounts


def build_container(
    settings: JobsSettings,
    *,
    repository: JobRepository | None = None,
    deleted_accounts: DeletedAccounts | None = None,
    applications: ApplicationRepository | None = None,
    applicants: ApplicantDirectory | None = None,
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

    if deleted_accounts is None:
        deleted_accounts = (
            SqlAlchemyDeletedAccounts(settings.database_url, schema=settings.database_schema)
            if settings.database_url
            else InMemoryDeletedAccounts()
        )

    if applications is None:
        applications = (
            SqlAlchemyApplicationRepository(settings.database_url, schema=settings.database_schema)
            if settings.database_url
            else InMemoryApplicationRepository()
        )

    should_seed = settings.seed_demo if seed is None else seed
    if should_seed:
        seed_repository(repository, settings.seed_path, is_deleted=deleted_accounts.contains)

    current_clock = clock or UtcClock()
    if directory is None:
        directory = HttpCompanyDirectory(settings.auth_service_url, settings.http_timeout_seconds)
    if applicants is None:
        applicants = HttpApplicantDirectory(
            settings.profile_service_url, settings.http_timeout_seconds
        )
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
    application_service = ApplicationService(
        applications=applications,
        jobs=repository,
        directory=applicants,
        clock=current_clock,
        ids=ids,
    )
    account_events = AccountEventsService(
        repository=repository, deleted_accounts=deleted_accounts, applications=applications
    )
    return Container(
        settings=settings,
        jobs=jobs,
        applications=application_service,
        tokens=tokens,
        repository=repository,
        account_events=account_events,
        deleted_accounts=deleted_accounts,
    )
