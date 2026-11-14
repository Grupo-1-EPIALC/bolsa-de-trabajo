"""Diseños del CV legibles por ATS e IA y la elección del más adecuado por reglas.

Todos los diseños del catálogo comparten lo que hace a un CV "IA friendly" (una columna,
texto real, títulos estándar, sin tablas ni gráficos, palabras clave en los metadatos). Lo
único que cambia es el orden de las secciones, para que lo más fuerte del perfil quede arriba.

Quién elige el diseño, de mayor a menor prioridad (`resolve_design`):
1. el estudiante (`user`);
2. la IA (`ai`, agente `cv_designer` de WF-07), si la sugerencia está completa, es del
   catálogo y el perfil no cambió desde que se pidió;
3. las reglas de este módulo (`rules`, `origin: "RULES"`), que siempre tienen una respuesta.

El catálogo de este módulo es la fuente de verdad: el schema `cv_design` y la skill
`diseno-cv` de mcp-tools repiten sus ids y se actualizan en el mismo PR si cambia.
"""

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Protocol

from app.domain.cv_design_state import AiDesignStatus, CvDesignState
from app.domain.experience import total_experience_months
from app.domain.profile import StudentProfile

ENGINE_VERSION = "cv-layout-1.0.0"


class CvSection(StrEnum):
    SUMMARY = "summary"
    SKILLS = "skills"
    EXPERIENCE = "experience"
    PROJECTS = "projects"
    EDUCATION = "education"
    LANGUAGES = "languages"
    CERTIFICATIONS = "certifications"
    VOLUNTEERING = "volunteering"


SECTION_TITLES: dict[CvSection, str] = {
    CvSection.SUMMARY: "Perfil profesional",
    CvSection.SKILLS: "Competencias",
    CvSection.EXPERIENCE: "Experiencia",
    CvSection.PROJECTS: "Proyectos",
    CvSection.EDUCATION: "Educación",
    CvSection.LANGUAGES: "Idiomas",
    CvSection.CERTIFICATIONS: "Certificaciones",
    CvSection.VOLUNTEERING: "Voluntariado",
}

# Orden de la plantilla antes de que existieran los diseños (CV sin diseño elegido).
DEFAULT_SECTION_ORDER: tuple[CvSection, ...] = (
    CvSection.SUMMARY,
    CvSection.SKILLS,
    CvSection.EXPERIENCE,
    CvSection.PROJECTS,
    CvSection.EDUCATION,
    CvSection.LANGUAGES,
    CvSection.CERTIFICATIONS,
    CvSection.VOLUNTEERING,
)


@dataclass(frozen=True)
class CvLayout:
    id: str
    name: str
    description: str
    best_for: str
    section_order: tuple[CvSection, ...]


CHRONOLOGICAL = CvLayout(
    id="cronologico",
    name="Cronológico",
    description="La experiencia laboral va primero, de la más reciente a la más antigua.",
    best_for="Quien ya tiene experiencia laboral relevante. Es el formato que los ATS leen mejor.",
    section_order=(
        CvSection.SUMMARY,
        CvSection.EXPERIENCE,
        CvSection.PROJECTS,
        CvSection.EDUCATION,
        CvSection.SKILLS,
        CvSection.CERTIFICATIONS,
        CvSection.LANGUAGES,
        CvSection.VOLUNTEERING,
    ),
)
FIRST_JOB = CvLayout(
    id="primer_empleo",
    name="Primer empleo",
    description="La formación y los proyectos van primero; la experiencia, después.",
    best_for="Estudiantes o recién recibidos con poca o ninguna experiencia laboral.",
    section_order=(
        CvSection.SUMMARY,
        CvSection.EDUCATION,
        CvSection.PROJECTS,
        CvSection.SKILLS,
        CvSection.EXPERIENCE,
        CvSection.VOLUNTEERING,
        CvSection.CERTIFICATIONS,
        CvSection.LANGUAGES,
    ),
)
SKILLS_BASED = CvLayout(
    id="competencias",
    name="Por competencias",
    description=(
        "Las competencias y los proyectos que las respaldan van primero; la experiencia "
        "sigue en orden cronológico."
    ),
    best_for="Perfiles técnicos con muchas competencias y proyectos o certificaciones.",
    section_order=(
        CvSection.SUMMARY,
        CvSection.SKILLS,
        CvSection.PROJECTS,
        CvSection.EXPERIENCE,
        CvSection.CERTIFICATIONS,
        CvSection.EDUCATION,
        CvSection.LANGUAGES,
        CvSection.VOLUNTEERING,
    ),
)

CV_LAYOUTS: tuple[CvLayout, ...] = (CHRONOLOGICAL, FIRST_JOB, SKILLS_BASED)
_LAYOUTS_BY_ID = {layout.id: layout for layout in CV_LAYOUTS}


def find_layout(layout_id: str | None) -> CvLayout | None:
    return _LAYOUTS_BY_ID.get((layout_id or "").strip())


def normalize_section_order(requested: Iterable[str], layout: CvLayout) -> tuple[CvSection, ...]:
    """Orden válido a partir de lo pedido: sólo secciones conocidas, sin repetir, el perfil
    profesional primero y las que falten al final en el orden base del diseño."""
    known = {s.value for s in CvSection}
    order: list[CvSection] = [CvSection.SUMMARY]
    for key in requested:
        value = str(key).strip().lower()
        if value in known and CvSection(value) not in order:
            order.append(CvSection(value))
    order += [s for s in layout.section_order if s not in order]
    return tuple(order)


# ----------------------------------------------------- resumen del contenido ---

_MAX_ROLES = 6
_MAX_SKILLS = 15


@dataclass(frozen=True)
class CvContentSummary:
    """Lo que hace falta para elegir un diseño. Sin datos personales: ni nombre, ni contacto,
    ni empresas, ni fechas exactas. Es lo único que se le manda a la IA."""

    headline: str
    has_summary: bool
    target_roles: tuple[str, ...]
    experience_count: int
    experience_months: int
    experience_roles: tuple[str, ...]
    projects_count: int
    skills_count: int
    top_skills: tuple[str, ...]
    certifications_count: int
    education_count: int
    career: str
    academic_progress_percent: int | None
    languages_count: int
    volunteering_count: int

    def fingerprint(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def summarize_content(profile: StudentProfile) -> CvContentSummary:
    skills = sorted(profile.skills, key=lambda s: -s.level)
    academic = profile.academic_status
    return CvContentSummary(
        headline=(profile.headline or "").strip(),
        has_summary=bool((profile.summary or "").strip()),
        target_roles=tuple(profile.target.roles) if profile.target else (),
        experience_count=len(profile.experience),
        experience_months=total_experience_months(profile.experience),
        experience_roles=tuple(e.role for e in profile.experience[:_MAX_ROLES] if e.role),
        projects_count=len(profile.projects),
        skills_count=len(profile.skills),
        top_skills=tuple(s.name for s in skills[:_MAX_SKILLS]),
        certifications_count=len(profile.certifications),
        education_count=len(profile.education),
        career=(academic.career or "") if academic else "",
        academic_progress_percent=academic.progress_percent if academic else None,
        languages_count=len(profile.languages),
        volunteering_count=len(profile.volunteering),
    )


# ------------------------------------------------------- elección por reglas ---


@dataclass(frozen=True)
class RuleVerdict:
    layout: CvLayout
    reasons: tuple[str, ...]


class LayoutRule(Protocol):
    """Una regla propone un diseño si el contenido la cumple (OCP: se agregan reglas nuevas)."""

    def evaluate(self, content: CvContentSummary) -> RuleVerdict | None: ...


class ExperiencedProfileRule:
    def __init__(self, min_months: int = 12, min_jobs: int = 2) -> None:
        self._min_months = min_months
        self._min_jobs = min_jobs

    def evaluate(self, content: CvContentSummary) -> RuleVerdict | None:
        if (
            content.experience_months < self._min_months
            and content.experience_count < self._min_jobs
        ):
            return None
        return RuleVerdict(
            CHRONOLOGICAL,
            (
                f"Tenés {content.experience_months} meses de experiencia en "
                f"{content.experience_count} puesto(s): conviene mostrarla primero.",
            ),
        )


class TechnicalProfileRule:
    def __init__(self, min_skills: int = 8, min_evidence: int = 2) -> None:
        self._min_skills = min_skills
        self._min_evidence = min_evidence

    def evaluate(self, content: CvContentSummary) -> RuleVerdict | None:
        evidence = content.projects_count + content.certifications_count
        if content.skills_count < self._min_skills or evidence < self._min_evidence:
            return None
        return RuleVerdict(
            SKILLS_BASED,
            (
                f"Tenés {content.skills_count} competencias respaldadas por {evidence} "
                "proyecto(s) o certificación(es): conviene destacarlas arriba.",
            ),
        )


@dataclass(frozen=True)
class RuleBasedDesign:
    layout: CvLayout
    section_order: tuple[CvSection, ...]
    reasons: tuple[str, ...]
    engine_version: str = ENGINE_VERSION


class CvLayoutSelector:
    """Aplica las reglas en orden; la primera que se cumple decide. Si ninguna, `fallback`."""

    def __init__(
        self,
        rules: Sequence[LayoutRule] | None = None,
        fallback: CvLayout = FIRST_JOB,
    ) -> None:
        self._rules = (
            tuple(rules)
            if rules is not None
            else (ExperiencedProfileRule(), TechnicalProfileRule())
        )
        self._fallback = fallback

    def select(self, content: CvContentSummary) -> RuleBasedDesign:
        for rule in self._rules:
            verdict = rule.evaluate(content)
            if verdict is not None:
                return RuleBasedDesign(
                    verdict.layout, verdict.layout.section_order, verdict.reasons
                )
        return RuleBasedDesign(
            self._fallback,
            self._fallback.section_order,
            (
                "Todavía tenés poca experiencia laboral: conviene mostrar primero tu "
                "formación y tus proyectos.",
            ),
        )


# ---------------------------------------------------------- diseño que rige ---


class DesignSource(StrEnum):
    USER = "user"
    AI = "ai"
    RULES = "rules"


@dataclass(frozen=True)
class EffectiveDesign:
    layout: CvLayout
    section_order: tuple[CvSection, ...]
    source: DesignSource


def ai_is_current(state: CvDesignState | None, fingerprint: str) -> bool:
    ai = state.ai if state else None
    return (
        ai is not None
        and ai.status is AiDesignStatus.COMPLETED
        and ai.fingerprint == fingerprint
        and find_layout(ai.layout) is not None
    )


def resolve_design(
    state: CvDesignState | None,
    rules: RuleBasedDesign,
    fingerprint: str,
    override: str | None = None,
) -> EffectiveDesign:
    """Diseño con el que se genera el CV. `override` es una vista previa puntual."""
    forced = find_layout(override)
    if forced is not None:
        return EffectiveDesign(forced, forced.section_order, DesignSource.USER)
    user_layout = find_layout(state.user.layout) if state and state.user else None
    if user_layout is not None:
        return EffectiveDesign(user_layout, user_layout.section_order, DesignSource.USER)
    if state and state.ai and ai_is_current(state, fingerprint):
        layout = find_layout(state.ai.layout)
        assert layout is not None  # noqa: S101 - garantizado por ai_is_current
        return EffectiveDesign(
            layout, normalize_section_order(state.ai.section_order, layout), DesignSource.AI
        )
    return EffectiveDesign(rules.layout, rules.section_order, DesignSource.RULES)
