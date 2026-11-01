"""Configuración de los agentes (modelos, límites y cantidades).

Hoy se arma desde variables de entorno y más adelante desde el panel; el dominio no sabe
de dónde viene: sólo define la forma y las reglas de validación.
"""

from dataclasses import asdict, dataclass, field

from app.domain.errors import InvalidInputError

MODEL_ROLES = ("default", "cv", "verifier")


@dataclass(frozen=True)
class RecommendationSettings:
    max_jobs_per_student: int
    max_profiles_per_job: int
    max_items_per_job: int
    min_score: float


@dataclass(frozen=True)
class CvSettings:
    max_size_mb: float
    allowed_extensions: tuple[str, ...]
    max_text_chars: int

    @property
    def max_size_bytes(self) -> int:
        return int(self.max_size_mb * 1024 * 1024)


@dataclass(frozen=True)
class AgentSettings:
    """Parámetros que usan los workflows de n8n en cada ejecución."""

    nvidia_base_url: str
    models: dict[str, tuple[str, ...]]
    rpm_limit: int
    llm_timeout_seconds: int
    temperature: float
    max_verify_retries: int
    recommendations: RecommendationSettings
    cv: CvSettings
    source: str = field(default="env")

    def __post_init__(self) -> None:
        missing = [role for role in MODEL_ROLES if not self.models.get(role)]
        if missing:
            raise InvalidInputError(f"Faltan modelos configurados para: {', '.join(missing)}")
        positives = {
            "rpm_limit": self.rpm_limit,
            "llm_timeout_seconds": self.llm_timeout_seconds,
            "max_jobs_per_student": self.recommendations.max_jobs_per_student,
            "max_profiles_per_job": self.recommendations.max_profiles_per_job,
            "max_items_per_job": self.recommendations.max_items_per_job,
            "cv.max_size_mb": self.cv.max_size_mb,
            "cv.max_text_chars": self.cv.max_text_chars,
        }
        invalid = [name for name, value in positives.items() if value <= 0]
        if invalid:
            raise InvalidInputError(f"Deben ser mayores que 0: {', '.join(invalid)}")
        if self.max_verify_retries < 0:
            raise InvalidInputError("max_verify_retries no puede ser negativo")
        if not 0 <= self.temperature <= 2:
            raise InvalidInputError("temperature debe estar entre 0 y 2")
        if not self.cv.allowed_extensions:
            raise InvalidInputError("cv.allowed_extensions no puede estar vacío")

    def models_for(self, role: str) -> tuple[str, ...]:
        if role not in MODEL_ROLES:
            raise InvalidInputError(f"Rol de modelo desconocido: {role}. Opciones: {MODEL_ROLES}")
        return self.models[role]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["models"] = {role: list(names) for role, names in self.models.items()}
        data["cv"]["allowed_extensions"] = list(self.cv.allowed_extensions)
        return data
