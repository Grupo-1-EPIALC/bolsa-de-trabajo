"""Normalización de competencias con diccionario + sinónimos (`SkillExtractor`, AGENTS.md §4.2).

Las claves normalizadas son las mismas que usa matching-service (minúsculas, sin acentos,
sinónimos resueltos), así el perfil ya viaja con `skills[].normalized` listo para el motor.
"""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from app.domain.enums import SkillCategory


def normalize_text(value: str) -> str:
    """Minúsculas, sin acentos y con espacios simples."""
    decomposed = unicodedata.normalize("NFD", value or "")
    no_accents = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return " ".join(no_accents.lower().split())


@dataclass(frozen=True)
class CatalogEntry:
    key: str  # clave normalizada (ej. "postgresql")
    label: str  # cómo se muestra (ej. "PostgreSQL")
    category: SkillCategory | None = None
    synonyms: tuple[str, ...] = ()


class SkillCatalog:
    """Catálogo en memoria: alias normalizado → entrada."""

    def __init__(self, entries: Iterable[CatalogEntry]) -> None:
        self._entries: dict[str, CatalogEntry] = {}
        self._aliases: dict[str, str] = {}
        for entry in entries:
            key = normalize_text(entry.key)
            self._entries[key] = entry
            self._aliases[key] = key
            self._aliases[normalize_text(entry.label)] = key
            for synonym in entry.synonyms:
                self._aliases[normalize_text(synonym)] = key

    def resolve(self, name: str) -> str | None:
        return self._aliases.get(normalize_text(name))

    def entry(self, key: str) -> CatalogEntry | None:
        return self._entries.get(key)

    def aliases(self) -> dict[str, str]:
        return dict(self._aliases)


class SkillExtractor:
    """Normaliza nombres de skills y detecta skills del catálogo en texto libre."""

    def __init__(self, catalog: SkillCatalog) -> None:
        self._catalog = catalog
        # Alias más largos primero para que "react native" gane sobre "react".
        aliases = sorted(catalog.aliases().items(), key=lambda item: -len(item[0]))
        self._patterns = [
            (re.compile(rf"(?<![\w+#.]){re.escape(alias)}(?![\w+#])"), key)
            for alias, key in aliases
            if alias
        ]

    def normalize(self, name: str) -> str:
        return self._catalog.resolve(name) or normalize_text(name)

    def label(self, name: str) -> str:
        """Nombre prolijo para mostrar (el del catálogo si existe)."""
        key = self._catalog.resolve(name)
        entry = self._catalog.entry(key) if key else None
        return entry.label if entry else name.strip()

    def category(self, name: str) -> SkillCategory | None:
        key = self._catalog.resolve(name)
        entry = self._catalog.entry(key) if key else None
        return entry.category if entry else None

    def extract(self, text: str) -> list[str]:
        """Claves del catálogo presentes en el texto, en orden de aparición y sin repetir."""
        haystack = normalize_text(text)
        found: list[tuple[int, str]] = []
        taken: list[tuple[int, int]] = []
        for pattern, key in self._patterns:
            for match in pattern.finditer(haystack):
                span = match.span()
                if any(span[0] < end and start < span[1] for start, end in taken):
                    continue
                taken.append(span)
                found.append((span[0], key))
        ordered: list[str] = []
        for _pos, key in sorted(found):
            if key not in ordered:
                ordered.append(key)
        return ordered
