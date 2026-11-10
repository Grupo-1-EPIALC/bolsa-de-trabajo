"""Raíz de composición: arma las dependencias concretas detrás de los puertos."""

from dataclasses import dataclass

from app.application.access_policy import AccessPolicy
from app.application.mappers import JobMapper, ProfileMapper
from app.application.matching_service import MatchingService
from app.application.recommendation_service import RecommendationService
from app.application.settings_service import SettingsService
from app.domain.engine import build_engine
from app.domain.ports import AnalysisTrigger, JobSource, ProfileSource, TokenVerifier
from app.domain.rules import ScoringRules
from app.domain.settings import RecommendationSettings
from app.domain.skill_dictionary import EXACT_ONLY, SkillDictionary
from app.domain.skill_gaps import SkillGapAggregator
from app.infrastructure.config import MatchingSettings
from app.infrastructure.http_client import JsonHttpClient
from app.infrastructure.jwt_verifier import JwksKeyResolver, JwtTokenVerifier
from app.infrastructure.n8n_trigger import HttpN8nAnalysisTrigger
from app.infrastructure.repositories_memory import (
    InMemoryRecommendationRepository,
    InMemoryRecommendationRequestRepository,
    InMemorySettingsRepository,
)
from app.infrastructure.rules_loader import load_rules, load_skill_dictionary
from app.infrastructure.sources_http import HttpJobSource, HttpProfileSource
from app.infrastructure.sources_mock import MockJobSource, MockProfileSource
from app.infrastructure.system import UtcClock, UuidIdGenerator


@dataclass(frozen=True)
class Container:
    settings: MatchingSettings
    rules: ScoringRules
    matching: MatchingService
    recommendations: RecommendationService
    access: AccessPolicy
    tokens: TokenVerifier
    settings_admin: SettingsService
    skills: SkillDictionary = EXACT_ONLY


def build_container(
    settings: MatchingSettings,
    profiles: ProfileSource | None = None,
    jobs: JobSource | None = None,
    trigger: AnalysisTrigger | None = None,
    tokens: TokenVerifier | None = None,
) -> Container:
    rules = load_rules(settings.rules_path)
    skills = load_skill_dictionary(settings.skills_path)
    clock = UtcClock()
    limits = InMemorySettingsRepository(
        RecommendationSettings(
            student_jobs_limit=rules.ranking.student_jobs_limit,
            company_candidates_limit=rules.ranking.company_candidates_limit,
        )
    )

    if profiles is None:
        profiles = (
            MockProfileSource()
            if settings.use_mocks
            else HttpProfileSource(
                JsonHttpClient(
                    settings.profile_service_url,
                    settings.service_token,
                    settings.http_timeout_seconds,
                )
            )
        )
    if jobs is None:
        jobs = (
            MockJobSource()
            if settings.use_mocks
            else HttpJobSource(
                JsonHttpClient(
                    settings.jobs_service_url,
                    settings.service_token,
                    settings.http_timeout_seconds,
                )
            )
        )
    if trigger is None:
        trigger = HttpN8nAnalysisTrigger(
            JsonHttpClient(
                settings.n8n_webhook_base_url,
                settings.service_token,
                settings.webhook_timeout_seconds,
            )
        )

    matching = MatchingService(
        profiles=profiles,
        jobs=jobs,
        engine=build_engine(rules, clock.iso_now, skills),
        profile_mapper=ProfileMapper(skills),
        job_mapper=JobMapper(skills),
        settings=limits,
        gaps=SkillGapAggregator(skills),
    )
    recommendations = RecommendationService(
        matching=matching,
        repository=InMemoryRecommendationRepository(),
        requests=InMemoryRecommendationRequestRepository(),
        trigger=trigger,
        clock=clock,
        ids=UuidIdGenerator(),
        settings=limits,
        max_items_per_entry=settings.max_items_per_entry,
    )
    if tokens is None:
        tokens = JwtTokenVerifier(
            JwksKeyResolver(settings.jwks_url), settings.jwt_issuer, settings.jwt_audience
        )
    return Container(
        settings,
        rules,
        matching,
        recommendations,
        AccessPolicy(matching),
        tokens,
        SettingsService(limits, clock),
        skills,
    )
