"""Raíz de composición de profile-service (inyección de dependencias)."""

import logging
from dataclasses import dataclass

from app.application.company_service import CompanyProfileService
from app.application.profile_service import ProfileService
from app.application.upload_cv_use_case import CvExtractionJobStore, UploadAndExtractCvUseCase
from app.domain.company import CompanyCompletenessPolicy
from app.domain.completion import ProfileCompletenessPolicy
from app.domain.cv_document import CvDocumentBuilder
from app.domain.ports import (
    AccountDirectory,
    Clock,
    CompanyProfileRepository,
    CvWebhookGateway,
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
from app.infrastructure.renderers.docx import DocxCvRenderer
from app.infrastructure.renderers.html import HtmlCvRenderer
from app.infrastructure.renderers.pdf import WeasyPrintCvRenderer
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
    companies: CompanyProfileService
    cv_upload: UploadAndExtractCvUseCase
    tokens: TokenVerifier
    repository: ProfileRepository
    company_repository: CompanyProfileRepository
    logos: LogoStore


def build_container(
    settings: ProfileSettings,
    *,
    repository: ProfileRepository | None = None,
    company_repository: CompanyProfileRepository | None = None,
    logos: LogoStore | None = None,
    webhook: CvWebhookGateway | None = None,
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
    profiles = ProfileService(
        repository=repository,
        policy=ProfileCompletenessPolicy(),
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
        loaded = seed_profiles(profiles, settings.seed_path)
        loaded_companies = seed_companies(companies, settings.companies_seed_path)
        logger.info("Seed: %s perfiles y %s empresas nuevos", loaded, loaded_companies)
    verifier = tokens or JwtTokenVerifier(
        JwksKeyResolver(settings.jwks_url), settings.jwt_issuer, settings.jwt_audience
    )
    return Container(
        settings, profiles, companies, cv_upload, verifier, repository, company_repository, logos
    )
