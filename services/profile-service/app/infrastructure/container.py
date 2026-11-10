"""Raíz de composición de profile-service (inyección de dependencias)."""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.application.account_events_service import AccountEventsService
from app.application.company_service import CompanyProfileService
from app.application.cv_design_service import CvDesignService
from app.application.profile_service import ProfileService
from app.application.upload_cv_use_case import CvExtractionJobStore, UploadAndExtractCvUseCase
from app.domain.company import CompanyCompletenessPolicy
from app.domain.completion import ProfileCompletenessPolicy
from app.domain.cv_document import CvDocumentBuilder
from app.domain.ports import (
    AccountDirectory,
    Clock,
    CompanyProfileRepository,
    CvDesignGateway,
    CvWebhookGateway,
    DeletedAccounts,
    EventPublisher,
    IdGenerator,
    LogoStore,
    ProfileRepository,
    TokenVerifier,
)
from app.domain.skills import SkillExtractor
from app.infrastructure.account_directory import HttpAccountDirectory
from app.infrastructure.catalog import load_skill_catalog
from app.infrastructure.config import ProfileSettings
from app.infrastructure.events_n8n import HttpN8nProfileEventPublisher
from app.infrastructure.jwt_verifier import JwksKeyResolver, JwtTokenVerifier
from app.infrastructure.n8n_client import HttpN8nCvWebhookGateway
from app.infrastructure.n8n_cv_design import HttpN8nCvDesignGateway
from app.infrastructure.renderers.docx import DocxCvRenderer
from app.infrastructure.renderers.html import HtmlCvRenderer
from app.infrastructure.renderers.pdf import WeasyPrintCvRenderer
from app.infrastructure.repositories.deleted_accounts import (
    InMemoryDeletedAccounts,
    SqlAlchemyDeletedAccounts,
)
from app.infrastructure.repositories.memory import InMemoryProfileRepository
from app.infrastructure.repositories.memory_companies import (
    InMemoryCompanyProfileRepository,
    InMemoryLogoStore,
)
from app.infrastructure.repositories.sqlalchemy_companies import (
    SqlAlchemyCompanyProfileRepository,
    SqlAlchemyLogoStore,
)
from app.infrastructure.repositories.sqlalchemy_repo import SqlAlchemyProfileRepository
from app.infrastructure.seed import seed_companies, seed_profiles
from app.infrastructure.storage_fs import FileSystemCvStorage
from app.infrastructure.system import UtcClock, UuidIdGenerator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Container:
    settings: ProfileSettings
    profiles: ProfileService
    cv_designs: CvDesignService
    companies: CompanyProfileService
    cv_upload: UploadAndExtractCvUseCase
    tokens: TokenVerifier
    repository: ProfileRepository
    company_repository: CompanyProfileRepository
    logos: LogoStore
    account_events: AccountEventsService
    deleted_accounts: DeletedAccounts


def build_container(
    settings: ProfileSettings,
    *,
    repository: ProfileRepository | None = None,
    company_repository: CompanyProfileRepository | None = None,
    logos: LogoStore | None = None,
    deleted_accounts: DeletedAccounts | None = None,
    webhook: CvWebhookGateway | None = None,
    cv_design_gateway: CvDesignGateway | None = None,
    cv_design_runner: Callable[[Callable[[], None]], None] | None = None,
    publisher: EventPublisher | None = None,
    accounts: AccountDirectory | None = None,
    tokens: TokenVerifier | None = None,
    clock: Clock | None = None,
    ids: IdGenerator | None = None,
    seed: bool | None = None,
) -> Container:
    if repository is None:
        repository = (
            SqlAlchemyProfileRepository(settings.database_url, schema=settings.database_schema)
            if settings.database_url
            else InMemoryProfileRepository()
        )
    if company_repository is None:
        company_repository = (
            SqlAlchemyCompanyProfileRepository(
                settings.database_url, schema=settings.database_schema
            )
            if settings.database_url
            else InMemoryCompanyProfileRepository()
        )
    if logos is None:
        logos = (
            SqlAlchemyLogoStore(settings.database_url, schema=settings.database_schema)
            if settings.database_url
            else InMemoryLogoStore()
        )
    if deleted_accounts is None:
        deleted_accounts = (
            SqlAlchemyDeletedAccounts(settings.database_url, schema=settings.database_schema)
            if settings.database_url
            else InMemoryDeletedAccounts()
        )
    accounts = accounts or HttpAccountDirectory(
        settings.auth_service_url, settings.http_timeout_seconds
    )
    clock = clock or UtcClock()
    ids = ids or UuidIdGenerator()
    cv_upload = UploadAndExtractCvUseCase(
        storage=FileSystemCvStorage(base_path=settings.cv_storage_path),
        webhook_gateway=webhook
        or HttpN8nCvWebhookGateway(
            webhook_base_url=settings.n8n_webhook_base_url,
            service_token=settings.service_token,
            timeout_seconds=settings.cv_webhook_timeout_seconds,
        ),
        max_size_mb=settings.cv_max_size_mb,
        job_store=CvExtractionJobStore(),
    )
    html = HtmlCvRenderer()
    policy = ProfileCompletenessPolicy()
    lock = threading.RLock()  # compartido: perfil, extracción de CV y diseño del CV
    design_options: dict[str, Any] = {"runner": cv_design_runner} if cv_design_runner else {}
    cv_designs = CvDesignService(
        repository=repository,
        policy=policy,
        gateway=cv_design_gateway
        or HttpN8nCvDesignGateway(
            webhook_base_url=settings.n8n_webhook_base_url,
            service_token=settings.service_token,
            timeout_seconds=settings.cv_design_timeout_seconds,
        ),
        clock=clock,
        lock=lock,
        **design_options,
    )
    profiles = ProfileService(
        repository=repository,
        policy=policy,
        extractor=SkillExtractor(load_skill_catalog(settings.skills_catalog_path)),
        publisher=publisher
        or HttpN8nProfileEventPublisher(
            settings.n8n_webhook_base_url, settings.service_token, settings.event_timeout_seconds
        ),
        accounts=accounts,
        clock=clock,
        ids=ids,
        cv_upload=cv_upload,
        cv_builder=CvDocumentBuilder(),
        renderers=(html, WeasyPrintCvRenderer(html), DocxCvRenderer()),
        designs=cv_designs,
        lock=lock,
    )
    companies = CompanyProfileService(
        repository=company_repository,
        logos=logos,
        policy=CompanyCompletenessPolicy(),
        accounts=accounts,
        clock=clock,
        ids=ids,
        logo_max_bytes=settings.logo_max_kb * 1024,
    )
    if settings.seed_demo if seed is None else seed:
        is_deleted = deleted_accounts.contains
        loaded = seed_profiles(profiles, settings.seed_path, is_deleted=is_deleted)
        loaded_companies = seed_companies(
            companies, settings.companies_seed_path, is_deleted=is_deleted
        )
        logger.info("Seed: %s perfiles y %s empresas nuevos", loaded, loaded_companies)
    verifier = tokens or JwtTokenVerifier(
        JwksKeyResolver(settings.jwks_url), settings.jwt_issuer, settings.jwt_audience
    )
    account_events = AccountEventsService(
        profiles=repository,
        companies=company_repository,
        logos=logos,
        deleted_accounts=deleted_accounts,
        clock=clock,
    )
    return Container(
        settings,
        profiles,
        cv_designs,
        companies,
        cv_upload,
        verifier,
        repository,
        company_repository,
        logos,
        account_events,
        deleted_accounts,
    )
