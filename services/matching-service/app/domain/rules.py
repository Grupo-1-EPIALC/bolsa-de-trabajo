"""Configuración del motor de reglas (se carga desde `scoring_rules.yaml` en infraestructura)."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from app.domain.errors import InvalidRulesError

DEFAULT_WEIGHTS: dict[str, float] = {
    "required_skills": 50.0,
    "desired_skills": 15.0,
    "levels": 15.0,
    "experience": 10.0,
    "education": 5.0,
    "languages": 5.0,
}

# Condiciones laborales (§7.1 del contrato).
# `hard=True` => si no coincide, el match es incompatible.
DEFAULT_CONDITIONS: dict[str, bool] = {
    "work_modality": True,
    "location": True,
    "work_schedule": True,
    "shifts": False,
    "employment_type": True,
    "contract_duration": False,
    "availability_start": False,
    "salary": False,
    "travel": False,
    "driver_license": True,
    "work_authorization": True,
    "academic": False,
}


@dataclass(frozen=True)
class ConditionRule:
    enabled: bool = True
    hard: bool = False


@dataclass(frozen=True)
class SalaryRules:
    tolerance_percent: float = 10.0
    net_to_gross: float = 1.21
    weeks_per_month: float = 4.33
    working_days_per_month: float = 21.0
    salaries_per_year: float = 13.0
    default_weekly_hours: float = 40.0
    fx_rates: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class RankingRules:
    # Valores iniciales de RecommendationSettings (un admin los puede cambiar por API)
    student_jobs_limit: int = 5
    company_candidates_limit: int = 10
    max_pool: int = 200
    exclude_incompatible: bool = True
    min_score: float = 0.0


@dataclass(frozen=True)
class ScoringRules:
    version: str = "1.0.0"
    weights: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    excluding_cap: float = 40.0
    conditions: Mapping[str, ConditionRule] = field(
        default_factory=lambda: {
            name: ConditionRule(enabled=True, hard=hard)
            for name, hard in DEFAULT_CONDITIONS.items()
        }
    )
    salary: SalaryRules = field(default_factory=SalaryRules)
    ranking: RankingRules = field(default_factory=RankingRules)

    def __post_init__(self) -> None:
        missing = set(DEFAULT_WEIGHTS) - set(self.weights)
        if missing:
            raise InvalidRulesError(
                "Faltan pesos de criterios en scoring_rules", {"missing": sorted(missing)}
            )
        if any(w < 0 for w in self.weights.values()):
            raise InvalidRulesError("Los pesos no pueden ser negativos")
        total = round(sum(self.weights[name] for name in DEFAULT_WEIGHTS), 6)
        if total != 100.0:
            raise InvalidRulesError("Los pesos de los criterios deben sumar 100", {"total": total})
        if not 0 <= self.excluding_cap <= 100:
            raise InvalidRulesError("excluding_cap debe estar entre 0 y 100")

    def weight(self, criterion: str) -> float:
        return float(self.weights[criterion])

    def condition(self, name: str) -> ConditionRule:
        return self.conditions.get(name, ConditionRule(enabled=True, hard=False))
