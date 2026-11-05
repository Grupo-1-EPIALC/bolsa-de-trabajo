"""Parámetros de recomendación ajustables por un administrador en tiempo de ejecución."""

from dataclasses import dataclass

from app.domain.errors import InvalidInputError

MIN_LIMIT = 1
MAX_LIMIT = 20  # coincide con `maxItems` de los schemas de salida del agente match_advisor


@dataclass(frozen=True)
class RecommendationSettings:
    """Cuántas ofertas se recomiendan a un estudiante y cuántos candidatos a una empresa.

    Valen para el ranking por reglas y para el análisis de IA (WF-06). Un `limit` pedido por
    quien llama sólo puede achicarlos, nunca superarlos.
    """

    student_jobs_limit: int = 5
    company_candidates_limit: int = 10
    updated_at: str = ""
    updated_by: str = ""

    def __post_init__(self) -> None:
        for name in ("student_jobs_limit", "company_candidates_limit"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise InvalidInputError(f"{name} debe ser un número entero", {"field": name})
            if not MIN_LIMIT <= value <= MAX_LIMIT:
                raise InvalidInputError(
                    f"{name} debe estar entre {MIN_LIMIT} y {MAX_LIMIT}",
                    {"field": name, "min": MIN_LIMIT, "max": MAX_LIMIT, "value": value},
                )

    @staticmethod
    def effective(requested: int | None, configured: int) -> int:
        """`limit` efectivo: el configurado, o uno menor si quien llama lo pide."""
        if requested is None:
            return configured
        if requested < MIN_LIMIT:
            raise InvalidInputError("limit debe ser mayor que 0", {"limit": requested})
        return min(requested, configured)
