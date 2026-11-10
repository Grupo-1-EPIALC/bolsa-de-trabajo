"""Carga `scoring_rules.yaml` y el diccionario de sinónimos de skills."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from app.domain.errors import InvalidRulesError
from app.domain.rules import (
    DEFAULT_CONDITIONS,
    DEFAULT_WEIGHTS,
    ConditionRule,
    ExperienceRules,
    RankingRules,
    SalaryRules,
    ScoringRules,
    TrainingRules,
)
from app.domain.skill_dictionary import SkillDictionary, SkillEntry, SkillGroup, SkillRelation


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def rules_from_mapping(data: Mapping[str, Any]) -> ScoringRules:
    weights = {k: float(v) for k, v in _mapping(data.get("weights")).items()} or dict(
        DEFAULT_WEIGHTS
    )
    raw_conditions = _mapping(data.get("conditions"))
    conditions: dict[str, ConditionRule] = {}
    for name, default_hard in DEFAULT_CONDITIONS.items():
        cfg = _mapping(raw_conditions.get(name))
        conditions[name] = ConditionRule(
            enabled=bool(cfg.get("enabled", True)), hard=bool(cfg.get("hard", default_hard))
        )
    salary = _mapping(data.get("salary"))
    ranking = _mapping(data.get("ranking"))
    defaults_salary = SalaryRules()
    defaults_ranking = RankingRules()
    experience = _mapping(data.get("experience"))
    training = _mapping(data.get("training"))
    defaults_experience = ExperienceRules()
    defaults_training = TrainingRules()
    return ScoringRules(
        version=str(data.get("version", ScoringRules.version)),
        weights=weights,
        excluding_cap=float(data.get("excluding_cap", 40)),
        conditions=conditions,
        salary=SalaryRules(
            tolerance_percent=float(
                salary.get("tolerance_percent", defaults_salary.tolerance_percent)
            ),
            net_to_gross=float(salary.get("net_to_gross", defaults_salary.net_to_gross)),
            weeks_per_month=float(salary.get("weeks_per_month", defaults_salary.weeks_per_month)),
            working_days_per_month=float(
                salary.get("working_days_per_month", defaults_salary.working_days_per_month)
            ),
            salaries_per_year=float(
                salary.get("salaries_per_year", defaults_salary.salaries_per_year)
            ),
            default_weekly_hours=float(
                salary.get("default_weekly_hours", defaults_salary.default_weekly_hours)
            ),
            fx_rates={
                str(k).upper(): float(v) for k, v in _mapping(salary.get("fx_rates")).items()
            },
        ),
        ranking=RankingRules(
            student_jobs_limit=int(
                ranking.get("student_jobs_limit", defaults_ranking.student_jobs_limit)
            ),
            company_candidates_limit=int(
                ranking.get("company_candidates_limit", defaults_ranking.company_candidates_limit)
            ),
            max_pool=int(ranking.get("max_pool", defaults_ranking.max_pool)),
            exclude_incompatible=bool(
                ranking.get("exclude_incompatible", defaults_ranking.exclude_incompatible)
            ),
            min_score=float(ranking.get("min_score", defaults_ranking.min_score)),
        ),
        experience=ExperienceRules(
            reference_years=float(
                experience.get("reference_years", defaults_experience.reference_years)
            ),
            relevance_share=float(
                experience.get("relevance_share", defaults_experience.relevance_share)
            ),
        ),
        training=TrainingRules(
            similar_jobs=int(training.get("similar_jobs", defaults_training.similar_jobs)),
            max_gaps=int(training.get("max_gaps", defaults_training.max_gaps)),
        ),
    )


def load_rules(path: str | Path) -> ScoringRules:
    file = Path(path)
    if not file.is_file():
        raise InvalidRulesError(f"No se encontró el archivo de reglas: {file}")
    try:
        data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise InvalidRulesError(f"scoring_rules.yaml inválido: {exc}") from exc
    return rules_from_mapping(_mapping(data))


def skill_dictionary_from_mapping(data: Mapping[str, Any]) -> SkillDictionary:
    """Arma el diccionario de competencias desde el JSON (`skill_dictionary.json`)."""
    try:
        entries = tuple(
            SkillEntry(
                key=str(raw["key"]),
                name=str(raw.get("name") or raw["key"]),
                category=str(raw.get("category") or ""),
                aliases=tuple(str(a) for a in raw.get("aliases") or ()),
            )
            for raw in data.get("skills") or ()
        )
        groups = tuple(
            SkillGroup(
                kind=SkillRelation(str(raw["kind"])),
                keys=frozenset(str(k) for k in raw["skills"]),
                credit=float(raw.get("credit", 1.0)),
                label=str(raw.get("label") or ""),
            )
            for raw in data.get("groups") or ()
        )
        implies = {
            str(k): frozenset(str(t) for t in targets)
            for k, targets in _mapping(data.get("implies")).items()
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidRulesError(f"skill_dictionary.json inválido: {exc}") from exc
    return SkillDictionary(entries, groups, implies, str(data.get("version") or "0"))


def load_skill_dictionary(path: str | Path) -> SkillDictionary:
    file = Path(path)
    if not file.is_file():
        raise InvalidRulesError(f"No se encontró el diccionario de competencias: {file}")
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InvalidRulesError(f"skill_dictionary.json inválido: {exc}") from exc
    return skill_dictionary_from_mapping(_mapping(data))
