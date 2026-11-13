"""Convierte las sugerencias de WF-01 (`cv_suggestions`, forma `cv_standard`) en un borrador
con la estructura del perfil, listo para que el frontend lo muestre en el formulario.

- Lo reconocido se precarga; lo que no se pudo reconocer queda en `"COMPLETAR_MANUALMENTE"`.
- `review_fields` lista esas rutas para que el usuario las complete antes de guardar.
- `suggested_fields` lista lo que la IA no copió del CV sino que sugirió con su contenido
  (hoy, el título `headline` cuando el CV no tiene uno): se precarga, pero hay que revisarlo.
- Nada se guarda en el perfil acá: el usuario confirma con `PATCH /profiles/me`.
- Las skills detectadas en el texto (catálogo + sinónimos) se agregan sólo si aparecen en
  el CV; nunca se inventan (AGENTS.md §5.2).
"""

import re
from collections.abc import Mapping
from typing import Any

from app.domain.enums import DataSource, EducationLevel, EducationStatus, LanguageLevel, LinkType
from app.domain.models import MANUAL_COMPLETION_INDICATOR as TODO
from app.domain.skills import SkillExtractor, normalize_text

_CABA = {"caba", "ciudad autonoma de buenos aires", "capital federal", "ciudad de buenos aires"}
_AR_PROVINCES = {
    "buenos aires": "Buenos Aires",
    "catamarca": "Catamarca",
    "chaco": "Chaco",
    "chubut": "Chubut",
    "cordoba": "Córdoba",
    "corrientes": "Corrientes",
    "entre rios": "Entre Ríos",
    "formosa": "Formosa",
    "jujuy": "Jujuy",
    "la pampa": "La Pampa",
    "la rioja": "La Rioja",
    "mendoza": "Mendoza",
    "misiones": "Misiones",
    "neuquen": "Neuquén",
    "rio negro": "Río Negro",
    "salta": "Salta",
    "san juan": "San Juan",
    "san luis": "San Luis",
    "santa cruz": "Santa Cruz",
    "santa fe": "Santa Fe",
    "santiago del estero": "Santiago del Estero",
    "tierra del fuego": "Tierra del Fuego",
    "tucuman": "Tucumán",
}
_COUNTRIES = {"argentina": "AR", "uruguay": "UY", "chile": "CL", "paraguay": "PY", "brasil": "BR"}
_ONGOING = {"actual", "actualidad", "presente", "present", "current", "hoy", "en curso"}


def _is_todo(value: Any) -> bool:
    return value is None or (isinstance(value, str) and (not value.strip() or value == TODO))


def _text(value: Any) -> str:
    return TODO if _is_todo(value) else str(value).strip()


def _headline(value: Any) -> str:
    """Título del perfil (máx. 140, como `PATCH /profiles/me`); vacío o sin dato = completar."""
    text = _text(value)
    return text if text == TODO else text[:140].strip()


def _optional(value: Any) -> str | None:
    return None if _is_todo(value) else str(value).strip()


# ---------------------------------------------------------------- traducciones ---


def parse_location(value: Any) -> dict[str, str]:
    """`"San Isidro, Buenos Aires, Argentina"` → `{city, province, country}`."""
    if isinstance(value, Mapping):
        return {k: _text(value.get(k)) for k in ("country", "province", "city")}
    parts = [p.strip() for p in str(value or "").split(",") if not _is_todo(p)]
    city = province = country = TODO
    for part in parts:
        key = normalize_text(part)
        if key in _CABA:
            province, country = "CABA", "AR"
            city = "Buenos Aires" if city == TODO else city
        elif key in _COUNTRIES:
            country = _COUNTRIES[key]
        elif key in _AR_PROVINCES and (province == TODO or city != TODO):
            province, country = _AR_PROVINCES[key], "AR"
        elif city == TODO:
            city = part
    return {"country": country, "province": province, "city": city}


def parse_language_level(value: Any) -> str:
    if _is_todo(value):
        return TODO
    text = normalize_text(str(value or ""))
    match = re.search(r"\b([abc][12])\b", text)
    if match:
        return LanguageLevel(match.group(1).upper()).value
    words = (
        (("nativ", "materno", "native", "mother"), LanguageLevel.NATIVE),
        (("bilingue", "bilingual", "dominio", "proficient"), LanguageLevel.C2),
        (("avanzado", "advanced", "fluido", "fluent"), LanguageLevel.C1),
        (("intermedio alto", "upper"), LanguageLevel.B2),
        (("intermedio", "intermediate"), LanguageLevel.B1),
        (("basico", "elemental", "basic", "elementary"), LanguageLevel.A2),
        (("inicial", "beginner", "principiante"), LanguageLevel.A1),
    )
    for keys, level in words:
        if any(k in text for k in keys):
            return level.value
    return TODO


def parse_education_status(value: Any) -> str:
    if _is_todo(value):  # "COMPLETAR_MANUALMENTE" contiene "complet": no confundir
        return TODO
    text = normalize_text(str(value or ""))
    if any(k in text for k in ("curso", "cursando", "progress", "actual", "avanzad")):
        return EducationStatus.IN_PROGRESS.value
    if any(k in text for k in ("incomplet", "abandon", "trunc")):
        return EducationStatus.INCOMPLETE.value
    if any(k in text for k in ("complet", "finaliz", "egres", "gradu", "recib", "titul")):
        return EducationStatus.COMPLETED.value
    return TODO


def guess_education_level(degree: str, institution: str) -> str:
    text = normalize_text(f"{degree} {institution}")
    rules = (
        (
            ("maestr", "master", "posgrado", "doctor", "especializacion", "mba"),
            EducationLevel.POSTGRADUATE,
        ),
        (
            ("ingenier", "licenci", "universi", "abogac", "contador", "arquitect"),
            EducationLevel.UNIVERSITY,
        ),
        (("tecnicatura", "terciari", "profesorado", "instituto"), EducationLevel.TERTIARY),
        (("secundari", "bachiller", "perito", "escuela", "colegio"), EducationLevel.SECONDARY),
        (("curso", "bootcamp", "taller"), EducationLevel.COURSE),
    )
    for keys, level in rules:
        if any(k in text for k in keys):
            return level.value
    return TODO


def normalize_period(value: Any, *, end: bool = False) -> str:
    text = str(value or "").strip()
    if _is_todo(text):
        return "actual" if end else TODO
    if normalize_text(text) in _ONGOING:
        return "actual"
    match = re.search(r"(\d{1,2})[/-](\d{4})", text)
    if match:
        return f"{match.group(2)}-{int(match.group(1)):02d}"
    match = re.search(r"(\d{4})(?:-(\d{1,2}))?", text)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}" if match.group(2) else match.group(1)
    return TODO


def link_type(url: str) -> str:
    low = url.lower()
    if "linkedin." in low:
        return LinkType.LINKEDIN.value
    if "github." in low or "gitlab." in low:
        return LinkType.GITHUB.value
    if any(k in low for k in ("behance", "dribbble", "portfolio", "vercel.app", "netlify.app")):
        return LinkType.PORTFOLIO.value
    return LinkType.OTHER.value


def _review_paths(value: Any, path: str = "") -> list[str]:
    if isinstance(value, Mapping):
        out: list[str] = []
        for key, item in value.items():
            out += _review_paths(item, f"{path}.{key}" if path else str(key))
        return out
    if isinstance(value, list):
        out = []
        for i, item in enumerate(value):
            out += _review_paths(item, f"{path}[{i}]")
        return out
    return [path] if value == TODO else []


# --------------------------------------------------------------------- mapper ---


class CvSuggestionMapper:
    def __init__(self, extractor: SkillExtractor) -> None:
        self._skills = extractor

    def to_profile_draft(
        self, suggestions: Mapping[str, Any], *, account_email: str | None = None
    ) -> dict[str, Any]:
        """Devuelve `{"profile_draft", "review_fields", "suggested_fields"}`."""
        personal = suggestions.get("personal") or {}
        email = _optional(personal.get("email")) or account_email
        draft: dict[str, Any] = {
            "personal": {
                "name": _text(personal.get("name")),
                "email": email or TODO,
                "phone": _text(personal.get("phone")),
                "location": parse_location(personal.get("location")),
            },
            "headline": _headline(suggestions.get("headline")),
            "summary": _text(suggestions.get("summary")),
        }

        experience = [self._experience(item) for item in suggestions.get("experience") or []]
        education = [self._education(item) for item in suggestions.get("education") or []]
        draft["experience"] = experience
        draft["education"] = education
        draft["skills"] = self._skill_list(suggestions, experience)
        draft["languages"] = [
            {
                "name": _text(item.get("name")),
                "normalized": normalize_text(str(item.get("name") or "")),
                "level": parse_language_level(item.get("level")),
            }
            for item in suggestions.get("languages") or []
            if not _is_todo(item.get("name"))
        ]
        draft["certifications"] = [
            {"name": str(name).strip()}
            for name in suggestions.get("certifications") or []
            if not _is_todo(name)
        ]
        draft["links"] = [
            {"type": link_type(str(url)), "url": str(url).strip()}
            for url in suggestions.get("links") or []
            if not _is_todo(url)
        ]
        academic = self._academic(education)
        if academic:
            draft["academic_status"] = academic
        suggested = (
            ["headline"]
            if draft["headline"] != TODO and suggestions.get("headline_source") != "cv"
            else []
        )
        return {
            "profile_draft": draft,
            "review_fields": _review_paths(draft),
            "suggested_fields": suggested,
        }

    def _experience(self, item: Mapping[str, Any]) -> dict[str, Any]:
        description = _optional(item.get("description")) or ""
        found = self._skills.extract(f"{item.get('role') or ''} {description}")
        return {
            "company": _text(item.get("company")),
            "role": _text(item.get("role")),
            "start": normalize_period(item.get("start")),
            "end": normalize_period(item.get("end"), end=True),
            "description": description,
            "skills_used": [self._skills.label(key) for key in found],
        }

    @staticmethod
    def _education(item: Mapping[str, Any]) -> dict[str, Any]:
        degree = _text(item.get("degree"))
        institution = _text(item.get("institution"))
        out: dict[str, Any] = {
            "institution": institution,
            "degree": degree,
            "level": guess_education_level(degree, institution),
            "status": parse_education_status(item.get("status")),
        }
        for key in ("start", "end"):
            value = normalize_period(item.get(key))
            if value != TODO:
                out[key] = value
        return out

    def _skill_list(
        self, suggestions: Mapping[str, Any], experience: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        skills: list[dict[str, Any]] = []
        seen: set[str] = set()

        def add(name: str, level: Any) -> None:
            key = self._skills.normalize(name)
            if not key or key in seen:
                return
            seen.add(key)
            category = self._skills.category(name)
            skill: dict[str, Any] = {
                "name": self._skills.label(name),
                "normalized": key,
                "level": level if isinstance(level, int) and 1 <= level <= 5 else TODO,
                "source": DataSource.CV_AI.value,
                "confirmed": False,
            }
            if category:
                skill["category"] = category.value
            skills.append(skill)

        for item in suggestions.get("skills") or []:
            if isinstance(item, Mapping) and not _is_todo(item.get("name")):
                add(str(item["name"]), item.get("level"))
        # Skills nombradas en la experiencia o el resumen que la IA no listó.
        texts = [str(suggestions.get("summary") or "")] + [e["description"] for e in experience]
        for key in self._skills.extract(" ".join(texts)):
            add(key, None)
        return skills

    @staticmethod
    def _academic(education: list[dict[str, Any]]) -> dict[str, Any] | None:
        for edu in education:
            if edu["status"] == EducationStatus.IN_PROGRESS.value and edu["level"] in (
                EducationLevel.UNIVERSITY.value,
                EducationLevel.TERTIARY.value,
            ):
                return {"institution": edu["institution"], "career": edu["degree"]}
        return None
