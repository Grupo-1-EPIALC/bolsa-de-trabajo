"""Escalas ordinales compartidas (idiomas, educación, disponibilidad, viajes)."""

from app.domain.normalization import normalize_text

_LANGUAGE_RANK: dict[str, int] = {
    "a1": 1,
    "a2": 2,
    "b1": 3,
    "b2": 4,
    "c1": 5,
    "c2": 6,
    "native": 7,
    # Valores en texto libre que puede devolver la IA o cargar el usuario
    "nativo": 7,
    "nativa": 7,
    "lengua materna": 7,
    "basico": 2,
    "elemental": 2,
    "intermedio": 3,
    "intermedio alto": 4,
    "avanzado": 5,
    "bilingue": 6,
    "fluido": 5,
}

_EDUCATION_LEVEL_RANK: dict[str, int] = {
    "course": 0,
    "secondary": 1,
    "tertiary": 2,
    "university": 3,
    "postgraduate": 4,
}

_EDUCATION_STATUS_RANK: dict[str, int] = {"incomplete": 0, "in_progress": 1, "completed": 2}

_AVAILABILITY_RANK: dict[str, int] = {"immediate": 0, "within_15_days": 1, "within_30_days": 2}

_TRAVEL_RANK: dict[str, int] = {"none": 0, "occasional": 1, "frequent": 2}


def language_rank(level: str) -> int:
    """0 si el nivel es desconocido."""
    return _LANGUAGE_RANK.get(normalize_text(level), 0)


def education_level_rank(level: str) -> int | None:
    return _EDUCATION_LEVEL_RANK.get(level)


def education_status_rank(status: str) -> int:
    return _EDUCATION_STATUS_RANK.get(status, 0)


def availability_rank(value: str) -> int | None:
    """`None` para `to_agree` o valores desconocidos."""
    return _AVAILABILITY_RANK.get(value)


def travel_rank(value: str) -> int | None:
    return _TRAVEL_RANK.get(value)
