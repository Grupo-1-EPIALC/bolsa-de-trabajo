"""Documento de CV "IA friendly" armado por reglas a partir del perfil confirmado.

Es un modelo de presentación neutro: los renderers (HTML/PDF/DOCX) sólo lo dibujan.
Pensado para que lo lean bien los ATS y los modelos de IA que filtran CVs:

- una sola columna, títulos de sección estándar y en orden convencional;
- todo es texto real (sin íconos ni imágenes con información);
- fechas uniformes, niveles explícitos y palabras clave en los metadatos del archivo.

No incluye datos sensibles ni privados: año de nacimiento, inclusión, sueldo pretendido.
No usa IA: sólo reordena y da formato a lo que el estudiante confirmó (`origin: "RULES"`).
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.domain.cv_design import DEFAULT_SECTION_ORDER, CvSection
from app.domain.enums import (
    AvailabilityStart,
    EducationStatus,
    EmploymentType,
    LanguageLevel,
    LinkType,
    SkillCategory,
    WorkModality,
    WorkSchedule,
)
from app.domain.profile import Education, Experience, StudentProfile

CV_TEMPLATE_VERSION = "1.2.0"  # 1.1.0: orden según el diseño · 1.2.0: competencias en texto
EN_DASH = "\u2013"  # raya de rangos de fechas

_MONTHS = (
    "ene.",
    "feb.",
    "mar.",
    "abr.",
    "may.",
    "jun.",
    "jul.",
    "ago.",
    "sep.",
    "oct.",
    "nov.",
    "dic.",
)
_ONGOING = {"actual", "actualidad", "presente", "present", "current", "hoy"}
_COUNTRIES = {
    "AR": "Argentina",
    "UY": "Uruguay",
    "CL": "Chile",
    "PY": "Paraguay",
    "BR": "Brasil",
    "BO": "Bolivia",
    "PE": "Perú",
    "MX": "México",
    "ES": "España",
    "US": "Estados Unidos",
}

SKILL_LEVEL_LABELS = {1: "Inicial", 2: "Básico", 3: "Intermedio", 4: "Avanzado", 5: "Experto"}
# Desde este nivel se aclara entre paréntesis; los niveles bajos no suman en un CV.
HIGHLIGHT_SKILL_LEVEL = 4
LANGUAGE_LEVEL_LABELS = {
    LanguageLevel.A1: "A1 · Inicial",
    LanguageLevel.A2: "A2 · Básico",
    LanguageLevel.B1: "B1 · Intermedio",
    LanguageLevel.B2: "B2 · Intermedio alto",
    LanguageLevel.C1: "C1 · Avanzado",
    LanguageLevel.C2: "C2 · Dominio pleno",
    LanguageLevel.NATIVE: "Nativo",
}
_SKILL_GROUPS = (
    (SkillCategory.HARD, "Técnicas"),
    (SkillCategory.TOOL, "Herramientas"),
    (SkillCategory.METHODOLOGY, "Metodologías"),
    (SkillCategory.SOFT, "Habilidades interpersonales"),
)
_EDU_STATUS = {
    EducationStatus.IN_PROGRESS: "En curso",
    EducationStatus.COMPLETED: "Completo",
    EducationStatus.INCOMPLETE: "Incompleto",
}
_MODALITY = {
    WorkModality.ONSITE: "presencial",
    WorkModality.REMOTE: "remota",
    WorkModality.HYBRID: "híbrida",
}
_SCHEDULE = {
    WorkSchedule.FULL_TIME: "full time",
    WorkSchedule.PART_TIME: "part time",
    WorkSchedule.HOURLY: "por horas",
    WorkSchedule.FLEXIBLE: "horario flexible",
}
_EMPLOYMENT = {
    EmploymentType.EMPLOYEE: "relación de dependencia",
    EmploymentType.FREELANCE: "freelance",
    EmploymentType.INTERNSHIP: "pasantía",
    EmploymentType.TRAINEE: "programa trainee",
}
_START = {
    AvailabilityStart.IMMEDIATE: "inicio inmediato",
    AvailabilityStart.WITHIN_15_DAYS: "inicio en 15 días",
    AvailabilityStart.WITHIN_30_DAYS: "inicio en 30 días",
    AvailabilityStart.TO_AGREE: "inicio a convenir",
}
_LINK_LABELS = {
    LinkType.LINKEDIN: "LinkedIn",
    LinkType.GITHUB: "GitHub",
    LinkType.PORTFOLIO: "Portfolio",
    LinkType.OTHER: "Web",
}


@dataclass(frozen=True)
class ContactItem:
    label: str
    value: str
    url: str | None = None


@dataclass(frozen=True)
class Entry:
    """Ítem de experiencia, educación, proyecto o voluntariado."""

    title: str
    organization: str
    period: str
    details: str = ""  # línea secundaria (estado, modalidad, área)
    bullets: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    url: str | None = None


@dataclass(frozen=True)
class SkillChip:
    name: str
    level: int
    level_label: str

    @property
    def display(self) -> str:
        """`Python (avanzado)` sólo si el nivel suma (4 o 5); si no, el nombre solo."""
        if self.level >= HIGHLIGHT_SKILL_LEVEL and self.level_label:
            return f"{self.name} ({self.level_label.lower()})"
        return self.name


@dataclass(frozen=True)
class SkillGroup:
    label: str
    skills: tuple[SkillChip, ...]

    @property
    def line(self) -> str:
        """Una línea separada por comas: el formato que mejor leen los ATS (sin barras ni chips)."""
        return ", ".join(skill.display for skill in self.skills)


@dataclass(frozen=True)
class LanguageLine:
    name: str
    level_label: str
    certification: str | None = None


@dataclass(frozen=True)
class CertificationLine:
    name: str
    detail: str
    url: str | None = None


@dataclass(frozen=True)
class CvDocument:
    full_name: str
    headline: str
    contact: tuple[ContactItem, ...]
    summary: str
    availability: str
    experience: tuple[Entry, ...]
    education: tuple[Entry, ...]
    projects: tuple[Entry, ...]
    skill_groups: tuple[SkillGroup, ...]
    languages: tuple[LanguageLine, ...]
    certifications: tuple[CertificationLine, ...]
    volunteering: tuple[Entry, ...]
    keywords: tuple[str, ...]
    generated_at: datetime
    template_version: str = CV_TEMPLATE_VERSION
    # Diseño (app/domain/cv_design.py): id y orden en que los renderers dibujan las secciones.
    layout: str = ""
    sections: tuple[CvSection, ...] = DEFAULT_SECTION_ORDER

    @property
    def file_stem(self) -> str:
        """`CV_Nombre_Apellido` sin acentos ni símbolos, apto para nombre de archivo."""
        plain = unicodedata.normalize("NFKD", self.full_name).encode("ascii", "ignore").decode()
        slug = re.sub(r"[^A-Za-z0-9]+", "_", plain).strip("_") or "Perfil"
        return f"CV_{slug}"


# ------------------------------------------------------------------ helpers ---


def format_date(value: str | None) -> str:
    """`2023-03` → `mar. 2023`, `2023` → `2023`, `actual` → `Actualidad`."""
    text = (value or "").strip()
    if not text:
        return ""
    if text.lower() in _ONGOING:
        return "Actualidad"
    match = re.fullmatch(r"(\d{4})-(\d{1,2})(?:-\d{1,2})?", text)
    if match and 1 <= int(match.group(2)) <= 12:
        return f"{_MONTHS[int(match.group(2)) - 1]} {match.group(1)}"
    return text


def format_period(start: str | None, end: str | None) -> str:
    first, last = format_date(start), format_date(end)
    if first and last:
        return first if first == last else f"{first} {EN_DASH} {last}"
    return first or last


def _sort_key(value: str | None) -> str:
    text = (value or "").strip().lower()
    if not text or text in _ONGOING:
        return "9999-99"
    match = re.fullmatch(r"(\d{4})(?:-(\d{1,2}))?.*", text)
    if not match:
        return "0000-00"
    return f"{match.group(1)}-{int(match.group(2) or 0):02d}"


def split_bullets(text: str) -> tuple[str, ...]:
    """Líneas de una descripción (acepta guiones, viñetas o saltos de línea)."""
    lines = [re.sub(r"^\s*[-•*·]\s*", "", line).strip() for line in (text or "").splitlines()]
    return tuple(line for line in lines if line)


def _join_options(values: Sequence[str]) -> str:
    items = [v for v in values if v]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " o " + items[-1]


def _display_url(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", url).rstrip("/")


# ------------------------------------------------------------------ builder ---


class CvDocumentBuilder:
    """Arma el `CvDocument` a partir del perfil. Reglas puras y deterministas."""

    def build(
        self,
        profile: StudentProfile,
        generated_at: datetime,
        *,
        layout: str = "",
        sections: Sequence[CvSection] = DEFAULT_SECTION_ORDER,
    ) -> CvDocument:
        return CvDocument(
            layout=layout,
            sections=tuple(sections),
            full_name=profile.personal.name.strip(),
            headline=self._headline(profile),
            contact=self._contact(profile),
            summary=(profile.summary or "").strip(),
            availability=self._availability(profile),
            experience=self._experience(profile.experience),
            education=self._education(profile),
            projects=tuple(
                Entry(
                    title=p.name,
                    organization="",
                    period="",
                    bullets=split_bullets(p.description),
                    tags=p.skills_used,
                    url=p.url,
                )
                for p in profile.projects
            ),
            skill_groups=self._skills(profile),
            languages=tuple(
                LanguageLine(lang.name, LANGUAGE_LEVEL_LABELS[lang.level], lang.certification)
                for lang in sorted(profile.languages, key=lambda x: _language_rank(x.level))
            ),
            certifications=tuple(
                CertificationLine(
                    c.name,
                    " · ".join(str(x) for x in (c.issuer, c.year) if x),
                    c.url,
                )
                for c in sorted(profile.certifications, key=lambda c: -(c.year or 0))
            ),
            volunteering=tuple(
                Entry(
                    title=v.role,
                    organization=v.organization,
                    period=format_period(v.start, v.end),
                    bullets=split_bullets(v.description),
                )
                for v in profile.volunteering
            ),
            keywords=self._keywords(profile),
            generated_at=generated_at,
        )

    @staticmethod
    def _headline(profile: StudentProfile) -> str:
        if profile.headline and profile.headline.strip():
            return profile.headline.strip()
        if profile.target and profile.target.roles:
            return " · ".join(profile.target.roles[:2])
        academic = profile.academic_status
        if academic and academic.career:
            return f"Estudiante de {academic.career}"
        return ""

    @staticmethod
    def _contact(profile: StudentProfile) -> tuple[ContactItem, ...]:
        items: list[ContactItem] = []
        personal = profile.personal
        if personal.email:
            items.append(ContactItem("Email", personal.email, f"mailto:{personal.email}"))
        if personal.phone:
            items.append(ContactItem("Teléfono", personal.phone))
        loc = personal.location
        if loc:
            country = _COUNTRIES.get(loc.country.upper(), loc.country)
            parts = [loc.city, loc.province if loc.province != loc.city else "", country]
            items.append(ContactItem("Ubicación", ", ".join(p for p in parts if p)))
        for link in profile.links:
            items.append(ContactItem(_LINK_LABELS[link.type], _display_url(link.url), link.url))
        return tuple(items)

    @staticmethod
    def _availability(profile: StudentProfile) -> str:
        wc = profile.work_conditions
        parts = [
            _join_options([_SCHEDULE[s] for s in wc.work_schedule]).capitalize(),
            (
                ("Modalidad " + _join_options([_MODALITY[m] for m in wc.work_modality]))
                if wc.work_modality
                else ""
            ),
            _join_options([_EMPLOYMENT[e] for e in wc.employment_type]).capitalize(),
            _START[wc.availability_start].capitalize() if wc.availability_start else "",
        ]
        if wc.willing_to_relocate:
            parts.append("Disponibilidad para mudarse")
        return " · ".join(p for p in parts if p)

    @staticmethod
    def _experience(items: Sequence[Experience]) -> tuple[Entry, ...]:
        ordered = sorted(items, key=lambda e: (_sort_key(e.end), _sort_key(e.start)), reverse=True)
        entries = []
        for exp in ordered:
            details = [
                _EMPLOYMENT[exp.employment_type].capitalize() if exp.employment_type else "",
                _MODALITY[exp.work_modality].capitalize() if exp.work_modality else "",
                exp.area or "",
            ]
            entries.append(
                Entry(
                    title=exp.role,
                    organization=exp.company,
                    period=format_period(exp.start, exp.end),
                    details=" · ".join(d for d in details if d),
                    bullets=split_bullets(exp.description),
                    tags=exp.skills_used,
                )
            )
        return tuple(entries)

    @staticmethod
    def _education(profile: StudentProfile) -> tuple[Entry, ...]:
        academic = profile.academic_status
        entries = []
        items: list[Education] = sorted(
            profile.education, key=lambda e: (_sort_key(e.end), _sort_key(e.start)), reverse=True
        )
        for edu in items:
            details = [_EDU_STATUS[edu.status]]
            is_current_career = bool(
                academic
                and edu.status is EducationStatus.IN_PROGRESS
                and academic.career
                and academic.career.lower() == edu.degree.lower()
            )
            year = edu.current_year or (
                academic.current_year if is_current_career and academic else None
            )
            progress = edu.progress_percent or (
                academic.progress_percent if is_current_career and academic else None
            )
            if year:
                details.append(f"{year}.º año")
            if progress:
                details.append(f"{progress} % de la carrera aprobada")
            entries.append(
                Entry(
                    title=edu.degree,
                    organization=edu.institution,
                    period=format_period(edu.start, edu.end),
                    details=" · ".join(details),
                )
            )
        if not entries and academic and academic.career:
            details = ["En curso"]
            if academic.current_year:
                details.append(f"{academic.current_year}.º año")
            if academic.progress_percent:
                details.append(f"{academic.progress_percent} % de la carrera aprobada")
            entries.append(
                Entry(
                    title=academic.career,
                    organization=academic.institution or "",
                    period=(
                        f"Egreso estimado: {format_date(academic.expected_graduation)}"
                        if academic.expected_graduation
                        else ""
                    ),
                    details=" · ".join(details),
                )
            )
        return tuple(entries)

    @staticmethod
    def _skills(profile: StudentProfile) -> tuple[SkillGroup, ...]:
        groups = []
        for category, label in _SKILL_GROUPS:
            chips = [
                SkillChip(s.name, s.level, SKILL_LEVEL_LABELS.get(s.level, ""))
                for s in sorted(profile.skills, key=lambda s: (-s.level, s.name.lower()))
                if (s.category or SkillCategory.HARD) is category
            ]
            if chips:
                groups.append(SkillGroup(label, tuple(chips)))
        return tuple(groups)

    @staticmethod
    def _keywords(profile: StudentProfile) -> tuple[str, ...]:
        words: list[str] = []
        sources = [s.name for s in sorted(profile.skills, key=lambda s: -s.level)]
        sources += list(profile.target.roles if profile.target else ())
        sources += [lang.name for lang in profile.languages]
        for word in sources:
            if word and word.lower() not in {w.lower() for w in words}:
                words.append(word)
        return tuple(words)


def _language_rank(level: LanguageLevel) -> int:
    order = [
        LanguageLevel.NATIVE,
        LanguageLevel.C2,
        LanguageLevel.C1,
        LanguageLevel.B2,
        LanguageLevel.B1,
        LanguageLevel.A2,
        LanguageLevel.A1,
    ]
    return order.index(level)
