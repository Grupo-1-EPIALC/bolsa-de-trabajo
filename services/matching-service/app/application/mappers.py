"""Traduce el JSON de profile-service / jobs-service al dominio (capa anticorrupción).

Acepta la estructura común de `contracts/profile.md` (anexo) y, por
compatibilidad, la forma "legacy" de los mocks de `mcp-tools` (`requirements` como lista,
`min_years_experience`, `education_level`, `full_name`, etc.).
Los valores `"COMPLETAR_MANUALMENTE"` de la IA se tratan como datos faltantes.
"""

from collections.abc import Iterable, Mapping
from datetime import date
from typing import Any

from app.domain.models import (
    AcademicRequirement,
    AcademicStatus,
    EducationItem,
    ExperienceRequirement,
    HoursRange,
    JobOpportunity,
    LanguageItem,
    Location,
    RequirementKind,
    SalaryRange,
    SkillItem,
    StudentProfile,
    WorkConditions,
)
from app.domain.normalization import SkillNormalizer, is_missing, normalize_text

_SKILL_LEVEL_WORDS = {
    "basico": 2,
    "elemental": 1,
    "intermedio": 3,
    "avanzado": 4,
    "experto": 5,
    "senior": 5,
}
_ONGOING = {"actual", "actualidad", "presente", "present", "current", "hoy"}


# ---------------------------------------------------------------- primitivas ---


def _str(value: object) -> str:
    return "" if is_missing(value) else str(value).strip()


def _float(value: object) -> float | None:
    if is_missing(value) or isinstance(value, bool):
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _int(value: object) -> int | None:
    number = _float(value)
    return None if number is None else int(number)


def _bool(value: object, default: bool = False) -> bool:
    return value if isinstance(value, bool) else default


def _opt_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _dict(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list | tuple) else []


def _set(value: object) -> frozenset[str]:
    if isinstance(value, str):
        return frozenset({value.strip()}) if _str(value) else frozenset()
    return frozenset(_str(v) for v in _list(value) if _str(v))


def _kind(value: object) -> RequirementKind:
    try:
        return RequirementKind(_str(value) or "required")
    except ValueError:
        return RequirementKind.REQUIRED


def _skill_level(value: object) -> int:
    number = _int(value)
    if number is None:
        number = _SKILL_LEVEL_WORDS.get(normalize_text(_str(value)), 1)
    return max(1, min(5, number))


# ------------------------------------------------------------------- bloques ---


def map_location(value: object) -> Location:
    if isinstance(value, str):
        # `cv_standard` trae la ubicación como texto libre: "Ciudad, Provincia, País"
        parts = [p.strip() for p in value.split(",") if p.strip() and not is_missing(p)]
        return Location(
            city=parts[0] if parts else "",
            province=parts[1] if len(parts) > 1 else "",
            country=parts[2] if len(parts) > 2 else "",
        )
    data = _dict(value)
    return Location(
        country=_str(data.get("country")),
        province=_str(data.get("province")),
        city=_str(data.get("city")),
        postal_code=_str(data.get("postal_code")),
        zone=_str(data.get("zone")),
        lat=_float(data.get("lat")),
        lon=_float(data.get("lon")),
    )


def map_salary(value: object) -> SalaryRange | None:
    data = _dict(value)
    if not data:
        return None
    return SalaryRange(
        min=_float(data.get("min")),
        max=_float(data.get("max")),
        currency=_str(data.get("currency")).upper(),
        period=_str(data.get("period")) or "month",
        gross=_bool(data.get("gross"), default=True),
        negotiable=_bool(data.get("negotiable")),
        to_agree=_bool(data.get("to_agree")),
        visibility=_str(data.get("visibility")) or "on_match",
    )


def map_work_conditions(value: object) -> WorkConditions:
    data = _dict(value)
    hours = _dict(data.get("weekly_hours"))
    h_min, h_max = _float(hours.get("min")), _float(hours.get("max"))
    weekly = None
    if h_min is not None or h_max is not None:
        low = h_min if h_min is not None else h_max
        high = h_max if h_max is not None else h_min
        weekly = HoursRange(min=float(low or 0), max=float(high or 0))
    return WorkConditions(
        work_schedule=_set(data.get("work_schedule")),
        work_modality=_set(data.get("work_modality")),
        hybrid_onsite_days=_int(data.get("hybrid_onsite_days")),
        employment_type=_set(data.get("employment_type")),
        contract_duration=_set(data.get("contract_duration")),
        weekly_hours=weekly,
        shifts=_set(data.get("shifts")),
        availability_start=_str(data.get("availability_start")),
        salary=map_salary(data.get("salary")),
        willing_to_relocate=_bool(data.get("willing_to_relocate")),
        relocation_support=_bool(data.get("relocation_support")),
        max_commute_km=_float(data.get("max_commute_km")),
        travel_availability=_str(data.get("travel_availability")),
        driver_license=_set(data.get("driver_license")),
        own_vehicle=_opt_bool(data.get("own_vehicle")),
        work_authorization=frozenset(c.upper() for c in _set(data.get("work_authorization"))),
    )


def map_skills(items: Iterable[Any], normalizer: SkillNormalizer) -> tuple[SkillItem, ...]:
    skills: list[SkillItem] = []
    for raw in items:
        data = _dict(raw) if not isinstance(raw, str) else {"name": raw}
        name = _str(data.get("name") or data.get("skill"))
        if not name:
            continue
        normalized = normalizer.normalize(_str(data.get("normalized")) or name)
        skills.append(
            SkillItem(
                name=name,
                normalized=normalized,
                level=_skill_level(data.get("level")),
                years=_float(data.get("years")),
                kind=_kind(data.get("kind")),
            )
        )
    return tuple(skills)


def map_languages(items: Iterable[Any]) -> tuple[LanguageItem, ...]:
    result: list[LanguageItem] = []
    for raw in items:
        data = _dict(raw)
        name = _str(data.get("name"))
        if not name:
            continue
        result.append(
            LanguageItem(
                name=name,
                normalized=normalize_text(_str(data.get("normalized")) or name),
                level=_str(data.get("level")),
                kind=_kind(data.get("kind")),
            )
        )
    return tuple(result)


def parse_legacy_education(value: str) -> EducationItem | None:
    """`universitario_en_curso` -> (university, in_progress), `terciario_completo` -> ..."""
    key = normalize_text(value).replace("_", " ")
    level = ""
    for marker, mapped in (
        ("posgrad", "postgraduate"),
        ("univers", "university"),
        ("terciar", "tertiary"),
        ("secundar", "secondary"),
        ("curso", "course"),
    ):
        if marker in key and not (marker == "curso" and "en curso" in key):
            level = mapped
            break
    if not level:
        return None
    if "incomplet" in key:
        status = "incomplete"
    elif "complet" in key:
        status = "completed"
    else:
        status = "in_progress"
    return EducationItem(level=level, status=status)


def map_education(items: Iterable[Any], legacy_level: object = None) -> tuple[EducationItem, ...]:
    result: list[EducationItem] = []
    for raw in items:
        data = _dict(raw)
        level = _str(data.get("level"))
        status = _str(data.get("status"))
        if not level and _str(data.get("degree")):
            parsed = parse_legacy_education(_str(data.get("degree")))
            level = parsed.level if parsed else ""
        result.append(
            EducationItem(
                level=level,
                status=status,
                degree=_str(data.get("degree")),
                field=_str(data.get("field")),
                kind=_kind(data.get("kind")),
            )
        )
    legacy = parse_legacy_education(_str(legacy_level)) if _str(legacy_level) else None
    if legacy is not None:
        result.append(legacy)
    return tuple(result)


def _parse_year_month(value: str, today: date) -> date | None:
    text = normalize_text(value)
    if not text:
        return None
    if text in _ONGOING:
        return today
    parts = text.replace("/", "-").split("-")
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        return date(year, max(1, min(12, month)), 1)
    except ValueError:
        return None


def years_from_experience(items: Iterable[Any], today: date | None = None) -> float:
    """Suma la duración de cada experiencia (usa `months` si viene calculado)."""
    ref = today or date.today()
    months = 0.0
    for raw in items:
        data = _dict(raw)
        explicit = _float(data.get("months"))
        if explicit is not None:
            months += max(0.0, explicit)
            continue
        start = _parse_year_month(_str(data.get("start")), ref)
        end = _parse_year_month(_str(data.get("end")), ref) or ref
        if start is not None and end >= start:
            months += (end.year - start.year) * 12 + (end.month - start.month)
    return round(months / 12, 2)


# ------------------------------------------------------------------ entidades ---


class ProfileMapper:
    def __init__(self, normalizer: SkillNormalizer) -> None:
        self._normalizer = normalizer

    def to_domain(self, data: Mapping[str, Any], today: date | None = None) -> StudentProfile:
        personal = _dict(data.get("personal"))
        academic = _dict(data.get("academic_status"))
        target = _dict(data.get("target"))
        explicit_years = _float(data.get("years_experience") or data.get("experience_years"))
        experience = _list(data.get("experience"))
        return StudentProfile(
            id=_str(data.get("id") or data.get("profile_id")),
            user_id=_str(data.get("user_id")),
            display_name=_str(personal.get("name") or data.get("full_name")),
            headline=_str(data.get("headline") or data.get("summary")),
            location=map_location(personal.get("location") or data.get("location")),
            work_conditions=map_work_conditions(data.get("work_conditions")),
            skills=map_skills(_list(data.get("skills")), self._normalizer),
            languages=map_languages(_list(data.get("languages"))),
            education=map_education(_list(data.get("education")), data.get("education_level")),
            years_experience=(
                explicit_years
                if explicit_years is not None
                else years_from_experience(experience, today)
            ),
            academic=AcademicStatus(
                career=_str(academic.get("career") or data.get("career")),
                current_year=_int(academic.get("current_year")),
                progress_percent=_float(academic.get("progress_percent")),
                student_shift=_set(academic.get("student_shift")),
            ),
            target_roles=tuple(_str(r) for r in _list(target.get("roles")) if _str(r)),
        )


class JobMapper:
    def __init__(self, normalizer: SkillNormalizer) -> None:
        self._normalizer = normalizer

    def to_domain(self, data: Mapping[str, Any]) -> JobOpportunity:
        raw_req = data.get("requirements")
        if isinstance(raw_req, list):  # forma legacy: lista de skills
            req: Mapping[str, Any] = {
                "skills": raw_req,
                "languages": data.get("languages"),
                "education": data.get("education"),
            }
        else:
            req = _dict(raw_req)
        experience = _dict(req.get("experience"))
        academic = _dict(req.get("academic"))
        company = _dict(data.get("company_snapshot"))
        min_years = _float(experience.get("min_years"))
        if min_years is None:
            min_years = _float(data.get("min_years_experience")) or 0.0
        return JobOpportunity(
            id=_str(data.get("id") or data.get("job_id")),
            title=_str(data.get("title")),
            company_id=_str(data.get("company_id")),
            company_name=_str(data.get("company_name") or company.get("name")),
            status=_str(data.get("status")) or "active",
            seniority=_str(data.get("seniority")),
            location=map_location(data.get("location")),
            work_conditions=map_work_conditions(data.get("work_conditions")),
            skills=map_skills(_list(req.get("skills")), self._normalizer),
            languages=map_languages(_list(req.get("languages") or data.get("languages"))),
            education=map_education(_list(req.get("education")), data.get("education_level")),
            experience=ExperienceRequirement(
                min_years=min_years,
                area=_str(experience.get("area")),
                kind=_kind(experience.get("kind")),
            ),
            academic=AcademicRequirement(
                min_progress_percent=_float(academic.get("min_progress_percent")),
                min_current_year=_int(academic.get("min_current_year")),
                careers=tuple(_str(c) for c in _list(academic.get("careers")) if _str(c)),
            ),
        )
