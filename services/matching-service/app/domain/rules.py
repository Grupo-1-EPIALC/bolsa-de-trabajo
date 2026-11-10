"""Configuración del motor de reglas (se carga desde `scoring_rules.yaml` en infraestructura)."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from app.domain.errors import InvalidRulesError

# Lo técnico y la experiencia pesan más; las condiciones laborales (modalidad, horario,
# disponibilidad, etc.) suman poco porque son negociables y no hablan de la capacidad.
DEFAULT_WEIGHTS: dict[str, float] = {
    "required_skills": 40.0,
    "desired_skills": 10.0,
    "levels": 10.0,
    "experience": 25.0,
    "education": 5.0,
    "languages": 3.0,
    "conditions": 7.0,
}

# Condiciones laborales (§7.1 del contrato).
# `hard=True` => si no coincide, el match es incompatible. Sólo los requisitos legales
# (licencia de conducir y autorización para trabajar) son duros por defecto.
DEFAULT_CONDITIONS: dict[str, bool] = {
    "work_modality": False,
    "location": False,
    "work_schedule": False,
    "shifts": False,
    "employment_type": False,
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
class ExperienceRules:
    # Sin mínimo pedido en la oferta, se compara contra estos años.
    reference_years: float = 1.0
    # Parte del criterio que mide si la experiencia usó las competencias de la oferta.
    relevance_share: float = 0.4


@dataclass(frozen=True)
class TrainingRules:
    # Ofertas más parecidas al perfil que se usan para calcular qué sumar o mejorar.
    similar_jobs: int = 10
    # Máximo de competencias que se devuelven en `skill_gaps`.
    max_gaps: int = 8


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
    version: str = "2.0.0"
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
    experience: ExperienceRules = field(default_factory=ExperienceRules)
    training: TrainingRules = field(default_factory=TrainingRules)

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
        if self.experience.reference_years <= 0:
            raise InvalidRulesError("experience.reference_years debe ser mayor a 0")
        if not 0 <= self.experience.relevance_share <= 1:
            raise InvalidRulesError("experience.relevance_share debe estar entre 0 y 1")
        if self.training.similar_jobs < 1 or self.training.max_gaps < 1:
            raise InvalidRulesError("training.similar_jobs y training.max_gaps deben ser >= 1")

    def weight(self, criterion: str) -> float:
        return float(self.weights[criterion])

    def condition(self, name: str) -> ConditionRule:
        return self.conditions.get(name, ConditionRule(enabled=True, hard=False))
