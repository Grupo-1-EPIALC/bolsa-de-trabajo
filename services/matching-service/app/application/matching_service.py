"""Casos de uso por reglas: match puntual, skills faltantes y rankings en ambos sentidos."""

from dataclasses import dataclass, replace

from app.application.mappers import JobMapper, ProfileMapper
from app.domain.engine import MatchingEngine
from app.domain.errors import InvalidInputError
from app.domain.models import JobOpportunity, MatchResult, MissingSkill, StudentProfile
from app.domain.ports import JobSource, ProfileSource, SettingsRepository
from app.domain.settings import RecommendationSettings


@dataclass(frozen=True)
class RankedJob:
    job: JobOpportunity
    result: MatchResult


@dataclass(frozen=True)
class RankedCandidate:
    profile: StudentProfile
    result: MatchResult


@dataclass(frozen=True)
class JobRanking:
    profile: StudentProfile
    items: tuple[RankedJob, ...]
    evaluated: int
    excluded_incompatible: int


@dataclass(frozen=True)
class CandidateRanking:
    job: JobOpportunity
    items: tuple[RankedCandidate, ...]
    evaluated: int
    excluded_incompatible: int


def _sort_key(result: MatchResult, entity_id: str) -> tuple[int, float, str]:
    # Compatibles primero, después mayor score; desempate estable por id.
    return (0 if result.conditions_fit.compatible else 1, -result.score, entity_id)


class MatchingService:
    def __init__(
        self,
        profiles: ProfileSource,
        jobs: JobSource,
        engine: MatchingEngine,
        profile_mapper: ProfileMapper,
        job_mapper: JobMapper,
        settings: SettingsRepository,
    ) -> None:
        self._profiles = profiles
        self._jobs = jobs
        self._engine = engine
        self._profile_mapper = profile_mapper
        self._job_mapper = job_mapper
        self._settings = settings

    def load_profile(self, profile_id: str) -> StudentProfile:
        clean = _require_id(profile_id, "profile_id")
        profile = self._profile_mapper.to_domain(self._profiles.get_profile(clean))
        return profile if profile.id else _with_id(profile, clean)

    def load_job(self, job_id: str) -> JobOpportunity:
        clean = _require_id(job_id, "job_id")
        job = self._job_mapper.to_domain(self._jobs.get_job(clean))
        return job if job.id else _with_job_id(job, clean)

    def compute(
        self, profile_id: str, job_id: str
    ) -> tuple[MatchResult, StudentProfile, JobOpportunity]:
        profile = self.load_profile(profile_id)
        job = self.load_job(job_id)
        return self._engine.match(profile, job), profile, job

    def missing_skills(self, profile_id: str, job_id: str) -> list[MissingSkill]:
        result, _, _ = self.compute(profile_id, job_id)
        return list(result.missing_skills)

    def rank_jobs_for_student(
        self, profile_id: str, limit: int | None = None, include_incompatible: bool | None = None
    ) -> JobRanking:
        rules = self._engine.rules.ranking
        top = RecommendationSettings.effective(limit, self._settings.get().student_jobs_limit)
        keep_incompatible = (
            not rules.exclude_incompatible if include_incompatible is None else include_incompatible
        )
        profile = self.load_profile(profile_id)
        jobs = [
            self._job_mapper.to_domain(raw) for raw in self._jobs.list_active_jobs(rules.max_pool)
        ]
        ranked = [RankedJob(job, self._engine.match(profile, job)) for job in jobs if job.id]
        ranked = [r for r in ranked if r.result.score >= rules.min_score]
        excluded = 0
        if not keep_incompatible:
            excluded = sum(1 for r in ranked if not r.result.conditions_fit.compatible)
            ranked = [r for r in ranked if r.result.conditions_fit.compatible]
        ranked.sort(key=lambda r: _sort_key(r.result, r.job.id))
        return JobRanking(profile, tuple(ranked[:top]), len(jobs), excluded)

    def rank_candidates_for_job(
        self, job_id: str, limit: int | None = None, include_incompatible: bool | None = None
    ) -> CandidateRanking:
        rules = self._engine.rules.ranking
        top = RecommendationSettings.effective(limit, self._settings.get().company_candidates_limit)
        keep_incompatible = (
            not rules.exclude_incompatible if include_incompatible is None else include_incompatible
        )
        job = self.load_job(job_id)
        profiles = [
            self._profile_mapper.to_domain(raw)
            for raw in self._profiles.list_profiles(rules.max_pool)
        ]
        ranked = [
            RankedCandidate(profile, self._engine.match(profile, job))
            for profile in profiles
            if profile.id
        ]
        ranked = [r for r in ranked if r.result.score >= rules.min_score]
        excluded = 0
        if not keep_incompatible:
            excluded = sum(1 for r in ranked if not r.result.conditions_fit.compatible)
            ranked = [r for r in ranked if r.result.conditions_fit.compatible]
        ranked.sort(key=lambda r: _sort_key(r.result, r.profile.id))
        return CandidateRanking(job, tuple(ranked[:top]), len(profiles), excluded)


def _require_id(value: str, name: str) -> str:
    clean = (value or "").strip()
    if not clean:
        raise InvalidInputError(f"{name} es obligatorio", {"field": name})
    return clean


def _with_id(profile: StudentProfile, profile_id: str) -> StudentProfile:
    return replace(profile, id=profile_id)


def _with_job_id(job: JobOpportunity, job_id: str) -> JobOpportunity:
    return replace(job, id=job_id)
