"""Qué competencias sumar o mejorar, en general (`origin = "RULES"`).

No mira una oferta sola: junta las competencias que faltan (o con nivel bajo) en las ofertas
activas más parecidas al perfil y las ordena por cuántas de esas ofertas las piden y con qué
peso. Es la base que la IA (`training_advisor`) usa para proponer formación.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.models import MatchResult, Priority, RequirementKind
from app.domain.normalization import normalize_text

_PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
_MUST = (RequirementKind.REQUIRED, RequirementKind.EXCLUDING)
# Una competencia es "frecuente" si la pide al menos esta parte de las ofertas parecidas.
FREQUENT_SHARE = 0.5


@dataclass(frozen=True)
class SimilarJob:
    job_id: str
    title: str
    score: float


@dataclass(frozen=True)
class SkillGap:
    skill: str
    status: str  # "missing" (no la tiene) | "improve" (la tiene con nivel menor al pedido)
    jobs_count: int  # en cuántas de las ofertas parecidas falta o queda corta
    share: float  # jobs_count / ofertas parecidas
    required_in: int  # en cuántas es obligatoria o excluyente
    current_level: int
    required_level: int  # el nivel más alto que piden esas ofertas
    priority: Priority


@dataclass(frozen=True)
class SkillGapsReport:
    profile_id: str
    similar_jobs: tuple[SimilarJob, ...]
    gaps: tuple[SkillGap, ...]
    evaluated: int  # ofertas activas evaluadas
    engine_version: str
    rules_version: str
    computed_at: str


@dataclass
class _Acc:
    skill: str
    jobs: int = 0
    required_in: int = 0
    current: int = 0
    required_level: int = 0


class SkillGapAggregator:
    """Prioridad: `alta` si es obligatoria en al menos la mitad de las ofertas parecidas;
    `media` si es obligatoria en alguna o deseable en al menos la mitad; si no, `baja`."""

    def aggregate(self, results: Sequence[MatchResult], max_gaps: int) -> list[SkillGap]:
        total = len(results)
        if not total:
            return []
        acc: dict[str, _Acc] = {}
        for result in results:
            seen: set[str] = set()
            for miss in result.missing_skills:
                key = normalize_text(miss.skill)
                if key in seen:
                    continue
                seen.add(key)
                item = acc.setdefault(key, _Acc(skill=miss.skill))
                item.jobs += 1
                item.required_in += 1 if miss.kind in _MUST else 0
                item.current = max(item.current, miss.current_level)
                item.required_level = max(item.required_level, miss.required_level)
        gaps = [self._gap(item, total) for item in acc.values()]
        gaps.sort(
            key=lambda g: (_PRIORITY_ORDER[g.priority], -g.jobs_count, -g.required_in, g.skill)
        )
        return gaps[:max_gaps]

    @staticmethod
    def _gap(item: _Acc, total: int) -> SkillGap:
        share = item.jobs / total
        required_share = item.required_in / total
        if required_share >= FREQUENT_SHARE:
            priority = Priority.HIGH
        elif item.required_in or share >= FREQUENT_SHARE:
            priority = Priority.MEDIUM
        else:
            priority = Priority.LOW
        return SkillGap(
            skill=item.skill,
            status="improve" if item.current > 0 else "missing",
            jobs_count=item.jobs,
            share=round(share, 2),
            required_in=item.required_in,
            current_level=item.current,
            required_level=item.required_level,
            priority=priority,
        )
