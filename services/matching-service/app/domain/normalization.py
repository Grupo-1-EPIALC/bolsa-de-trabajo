"""Normalización de textos y competencias (minúsculas, sin acentos, sinónimos)."""

import re
import unicodedata
from collections.abc import Mapping

MANUAL_PLACEHOLDER = "COMPLETAR_MANUALMENTE"


def normalize_text(text: str) -> str:
    """Minúsculas, sin acentos y con espacios simples."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_accents.lower()).strip()


def is_missing(value: object) -> bool:
    """`True` si el valor está vacío o es el marcador de completado manual de la IA."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip() or value.strip() == MANUAL_PLACEHOLDER
    return False


class SkillNormalizer:
    """Lleva un nombre de competencia a su clave canónica usando un diccionario de sinónimos."""

    def __init__(self, synonyms: Mapping[str, str] | None = None) -> None:
        self._synonyms = {
            normalize_text(alias): normalize_text(canonical)
            for alias, canonical in (synonyms or {}).items()
        }

    def normalize(self, name: str) -> str:
        key = normalize_text(name)
        return self._synonyms.get(key, key)
