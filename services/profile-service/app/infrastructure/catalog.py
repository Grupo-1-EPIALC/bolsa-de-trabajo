"""Carga `data/skills_catalog.json` (diccionario de competencias + sinónimos)."""

import json
from pathlib import Path

from app.domain.enums import SkillCategory
from app.domain.skills import CatalogEntry, SkillCatalog


def load_skill_catalog(path: str) -> SkillCatalog:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = [
        CatalogEntry(
            key=str(item["key"]),
            label=str(item.get("label") or item["key"]),
            category=SkillCategory(item["category"]) if item.get("category") else None,
            synonyms=tuple(str(s) for s in item.get("synonyms") or ()),
        )
        for item in data.get("skills", [])
    ]
    return SkillCatalog(entries)
