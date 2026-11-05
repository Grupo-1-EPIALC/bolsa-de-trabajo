"""Normalización de competencias e idiomas (minúsculas, sin acentos, espacios simples)."""

import re
import unicodedata


def normalize_text(text: str) -> str:
    """Devuelve la clave canónica usada por matching para comparar nombres."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_accents.lower()).strip()
