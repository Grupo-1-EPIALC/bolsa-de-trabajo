"""Diccionario de competencias: nombres distintos para la misma skill y skills parecidas.

Cuatro relaciones, de más fuerte a más débil:
- **alias** (`exact`): el mismo nombre escrito distinto (`Postgres` = `PostgreSQL`).
- **implica** (`implied`): saber una supone saber otra más general (`PostgreSQL` ⇒ `SQL`,
  `React` ⇒ `JavaScript`). Es transitiva y vale con el nivel de la skill que la implica.
- **equivalente** (`equivalent`): se usan una por otra (`MySQL` ↔ `MariaDB`). Cuenta completa.
- **similar** (`similar`): herramienta parecida que facilita aprender la pedida
  (`GitHub` ~ `GitLab`, `PostgreSQL` ~ `MySQL`). Suma sólo una parte (`credit`) y la skill
  sigue como faltante, con la similar que ya sabe como "puente" para aprenderla.

Es la fuente de verdad del motor de reglas y de la herramienta `resolver_skills` del agente.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from app.domain.errors import InvalidRulesError
from app.domain.normalization import normalize_text


class SkillRelation(StrEnum):
    EXACT = "exact"
    IMPLIED = "implied"
    EQUIVALENT = "equivalent"
    SIMILAR = "similar"


_STRENGTH = {
    SkillRelation.EXACT: 3,
    SkillRelation.IMPLIED: 2,
    SkillRelation.EQUIVALENT: 1,
    SkillRelation.SIMILAR: 0,
}


@dataclass(frozen=True)
class SkillEntry:
    key: str
    name: str
    category: str = ""
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillGroup:
    kind: SkillRelation  # EQUIVALENT o SIMILAR
    keys: frozenset[str]
    credit: float = 1.0
    label: str = ""


@dataclass(frozen=True)
class Coverage:
    """Cómo cubre el perfil una skill pedida."""

    relation: SkillRelation
    credit: float  # 1 = la tiene; menos de 1 = sólo una parecida
    level: int  # nivel con el que la cubre
    via: str  # clave de la skill del perfil que la cubre

    @property
    def full(self) -> bool:
        return self.credit >= 1.0


@dataclass(frozen=True)
class SkillDictionary:
    entries: tuple[SkillEntry, ...] = ()
    groups: tuple[SkillGroup, ...] = ()
    implies: Mapping[str, frozenset[str]] = field(default_factory=dict)
    version: str = "0"
    _aliases: dict[str, str] = field(default_factory=dict, init=False, repr=False, compare=False)
    _closure: dict[str, frozenset[str]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        keys = {e.key for e in self.entries}
        aliases: dict[str, str] = {}
        for entry in self.entries:
            if entry.key != normalize_text(entry.key):
                raise InvalidRulesError(
                    "La clave de una skill debe estar normalizada", {"key": entry.key}
                )
            for alias in (entry.key, normalize_text(entry.name), *entry.aliases):
                norm = normalize_text(alias)
                if aliases.get(norm, entry.key) != entry.key:
                    raise InvalidRulesError(
                        "Un alias apunta a dos skills distintas",
                        {"alias": alias, "skills": [aliases[norm], entry.key]},
                    )
                aliases[norm] = entry.key
        unknown = {k for g in self.groups for k in g.keys} | set(self.implies)
        unknown |= {k for targets in self.implies.values() for k in targets}
        unknown -= keys
        if unknown:
            raise InvalidRulesError(
                "Hay skills en grupos o implicaciones que no están en el diccionario",
                {"unknown": sorted(unknown)},
            )
        for group in self.groups:
            if group.kind not in (SkillRelation.EQUIVALENT, SkillRelation.SIMILAR):
                raise InvalidRulesError("Un grupo debe ser 'equivalent' o 'similar'")
            if not 0 < group.credit <= 1:
                raise InvalidRulesError("El crédito de un grupo debe estar entre 0 y 1")
        object.__setattr__(self, "_aliases", aliases)
        object.__setattr__(self, "_closure", {k: self._reach(k) for k in self.implies})

    def _reach(self, key: str) -> frozenset[str]:
        seen: set[str] = set()
        stack = list(self.implies.get(key, ()))
        while stack:
            nxt = stack.pop()
            if nxt in seen or nxt == key:
                continue
            seen.add(nxt)
            stack.extend(self.implies.get(nxt, ()))
        return frozenset(seen)

    # ------------------------------------------------------------- nombres ---

    def normalize(self, name: str) -> str:
        """Clave canónica (`Postgres` → `postgresql`); si no la conoce, el texto normalizado."""
        norm = normalize_text(name)
        return self._aliases.get(norm, norm)

    def entry(self, key: str) -> SkillEntry | None:
        return next((e for e in self.entries if e.key == key), None)

    def name(self, key: str) -> str:
        found = self.entry(key)
        return found.name if found else key

    # ------------------------------------------------------------ cobertura ---

    def implied_by(self, key: str) -> frozenset[str]:
        """Skills que, si se tienen, implican `key`."""
        return frozenset(k for k, reach in self._closure.items() if key in reach)

    def coverage(self, have: Mapping[str, int], wanted: str) -> Coverage | None:
        """La mejor forma en que las skills `have` (clave → nivel) cubren `wanted`."""
        options: list[Coverage] = []
        if wanted in have:
            options.append(Coverage(SkillRelation.EXACT, 1.0, have[wanted], wanted))
        for key, level in have.items():
            if wanted in self._closure.get(key, ()):
                options.append(Coverage(SkillRelation.IMPLIED, 1.0, level, key))
        for group in self.groups:
            if wanted not in group.keys:
                continue
            for key in group.keys - {wanted}:
                if key in have:
                    options.append(Coverage(group.kind, group.credit, have[key], key))
        if not options:
            return None
        return max(options, key=lambda c: (c.credit, _STRENGTH[c.relation], c.level, c.via))

    def describe(self, name: str, have: Iterable[str] = ()) -> dict[str, object]:
        """Ficha de una skill para la API y el agente (y si el perfil la cubre)."""
        key = self.normalize(name)
        found = self.entry(key)
        equivalents: set[str] = set()
        similar: list[dict[str, object]] = []
        for group in self.groups:
            if key not in group.keys:
                continue
            others = sorted(group.keys - {key})
            if group.kind is SkillRelation.EQUIVALENT:
                equivalents.update(others)
            else:
                similar.extend(
                    {"skill": self.name(k), "credit": group.credit, "group": group.label}
                    for k in others
                )
        result: dict[str, object] = {
            "input": name,
            "key": key,
            "name": found.name if found else name.strip(),
            "known": found is not None,
            "category": found.category if found else "",
            "aliases": list(found.aliases) if found else [],
            "implies": sorted(self.name(k) for k in self._closure.get(key, ())),
            "implied_by": sorted(self.name(k) for k in self.implied_by(key)),
            "equivalents": sorted(self.name(k) for k in equivalents),
            # Herramientas parecidas: saber una facilita aprender la otra.
            "similar": similar,
        }
        have_keys = [self.normalize(h) for h in have]
        if have_keys:
            cov = self.coverage({k: 1 for k in have_keys}, key)
            result["covered_by"] = (
                None
                if cov is None
                else {
                    "relation": cov.relation.value,
                    "credit": cov.credit,
                    "via": self.name(cov.via),
                    "full": cov.full,
                }
            )
        return result


EXACT_ONLY = SkillDictionary()
