"""Chequeo determinístico de "no inventar": cada término debe aparecer en el texto fuente."""

import re
import unicodedata


def normalize(text: str) -> str:
    """Minúsculas, sin acentos y con espacios simples."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_accents.lower()).strip()


def _contains(haystack: str, needle: str) -> bool:
    if not needle:
        return True
    # Límites de palabra "suaves": permite términos como "c++", "node.js" o ".net".
    pattern = rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])"
    return re.search(pattern, haystack) is not None


def find_ungrounded(terms: list[str], source_text: str) -> list[str]:
    """Devuelve los términos (sin repetir, en orden) que no aparecen en `source_text`."""
    haystack = normalize(source_text)
    seen: set[str] = set()
    missing: list[str] = []
    for term in terms:
        key = normalize(term)
        if key in seen:
            continue
        seen.add(key)
        if not _contains(haystack, key):
            missing.append(term)
    return missing
