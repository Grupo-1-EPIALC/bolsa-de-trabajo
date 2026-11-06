"""Reglas de completitud del perfil (calculadas por código, `origin: "RULES"`).

Cada regla es un objeto independiente; para pedir un dato nuevo se agrega una regla a la
lista, sin tocar la política (OCP). Los pasos guían al frontend:

- `cv`: datos que salen del CV (o se cargan a mano) y alcanzan para generar el CV.
- `preferences`: disponibilidad, modalidad, tipo de empleo, sueldo pretendido, etc.
- `privacy`: consentimiento para tratar los datos.

La política es genérica (`CompletenessPolicy[P]`): el perfil de empresa usa la misma mecánica
con sus propias reglas y pasos (`app/domain/company.py`).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.domain.enums import ProfileStatus
from app.domain.profile import StudentProfile

COMPLETION_ENGINE_VERSION = "1.0.0"


class Step(StrEnum):
    CV = "cv"
    PREFERENCES = "preferences"
    PRIVACY = "privacy"


@dataclass(frozen=True)
class CompletionRule[P]:
    field: str  # ruta del dato en el perfil (ej. "work_conditions.work_modality")
    step: StrEnum
    message: str
    is_satisfied: Callable[[P], bool]
    required: bool = True

    @property
    def weight(self) -> int:
        return 2 if self.required else 1


@dataclass(frozen=True)
class MissingField:
    field: str
    step: StrEnum
    message: str
    required: bool


@dataclass(frozen=True)
class StepState:
    step: StrEnum
    complete: bool  # sin faltantes obligatorios
    missing_required: int
    missing_recommended: int


@dataclass(frozen=True)
class Completion:
    percent: int
    status: ProfileStatus
    steps: tuple[StepState, ...]
    missing: tuple[MissingField, ...]
    can_generate_cv: bool = False  # sólo aplica al perfil de estudiante


def _has(text: str | None) -> bool:
    return bool(text and text.strip())


def _location_ok(p: StudentProfile) -> bool:
    loc = p.personal.location
    return bool(loc and _has(loc.country) and _has(loc.province) and _has(loc.city))


def _education_ok(p: StudentProfile) -> bool:
    return bool(p.education) or bool(p.academic_status and _has(p.academic_status.career))


DEFAULT_RULES: tuple[CompletionRule[StudentProfile], ...] = (
    # ---- paso 1: datos del CV
    CompletionRule(
        "personal.name", Step.CV, "Ingresá tu nombre y apellido", lambda p: _has(p.personal.name)
    ),
    CompletionRule(
        "personal.email", Step.CV, "Ingresá un email de contacto", lambda p: _has(p.personal.email)
    ),
    CompletionRule(
        "personal.location",
        Step.CV,
        "Indicá país, provincia y ciudad de residencia",
        _location_ok,
    ),
    CompletionRule(
        "summary", Step.CV, "Escribí un resumen de tu perfil profesional", lambda p: _has(p.summary)
    ),
    CompletionRule(
        "skills",
        Step.CV,
        "Cargá al menos una competencia con su nivel (1 a 5)",
        lambda p: bool(p.skills),
    ),
    CompletionRule(
        "education",
        Step.CV,
        "Cargá tu formación (o la carrera que cursás)",
        _education_ok,
    ),
    CompletionRule(
        "headline",
        Step.CV,
        "Agregá un título corto (ej. «Estudiante de Sistemas · Backend»)",
        lambda p: _has(p.headline),
        required=False,
    ),
    CompletionRule(
        "personal.phone",
        Step.CV,
        "Agregá un teléfono",
        lambda p: _has(p.personal.phone),
        required=False,
    ),
    CompletionRule(
        "experience",
        Step.CV,
        "Sumá experiencia laboral o proyectos propios",
        lambda p: bool(p.experience or p.projects),
        required=False,
    ),
    CompletionRule(
        "languages",
        Step.CV,
        "Cargá los idiomas que manejás",
        lambda p: bool(p.languages),
        required=False,
    ),
    CompletionRule(
        "links",
        Step.CV,
        "Agregá LinkedIn, GitHub o portfolio",
        lambda p: bool(p.links),
        required=False,
    ),
    # ---- paso 2: preferencias de búsqueda
    CompletionRule(
        "work_conditions.work_modality",
        Step.PREFERENCES,
        "Elegí la presencialidad que aceptás (presencial, remota, mixta)",
        lambda p: bool(p.work_conditions.work_modality),
    ),
    CompletionRule(
        "work_conditions.work_schedule",
        Step.PREFERENCES,
        "Elegí la modalidad horaria (full time, part time…)",
        lambda p: bool(p.work_conditions.work_schedule),
    ),
    CompletionRule(
        "work_conditions.employment_type",
        Step.PREFERENCES,
        "Elegí el tipo de empleo (relación de dependencia, freelance, pasantía…)",
        lambda p: bool(p.work_conditions.employment_type),
    ),
    CompletionRule(
        "work_conditions.availability_start",
        Step.PREFERENCES,
        "Indicá cuándo podés empezar",
        lambda p: p.work_conditions.availability_start is not None,
    ),
    CompletionRule(
        "target.roles",
        Step.PREFERENCES,
        "Contá qué puestos buscás",
        lambda p: bool(p.target and p.target.roles),
        required=False,
    ),
    CompletionRule(
        "work_conditions.weekly_hours",
        Step.PREFERENCES,
        "Indicá cuántas horas semanales podés trabajar",
        lambda p: p.work_conditions.weekly_hours is not None,
        required=False,
    ),
    CompletionRule(
        "work_conditions.salary",
        Step.PREFERENCES,
        "Indicá tu sueldo pretendido (o «a convenir»)",
        lambda p: p.work_conditions.salary is not None,
        required=False,
    ),
    # ---- paso 3: privacidad
    CompletionRule(
        "consents.data_processing",
        Step.PRIVACY,
        "Aceptá el tratamiento de tus datos para poder recibir ofertas",
        lambda p: p.consents.data_processing,
    ),
)


class CompletenessPolicy[P]:
    """Evalúa reglas sobre un perfil. `cv_step`: paso que habilita generar el CV (si aplica)."""

    def __init__(
        self,
        rules: Sequence[CompletionRule[P]],
        steps: Sequence[StrEnum],
        cv_step: StrEnum | None = None,
    ) -> None:
        self._rules = tuple(rules)
        self._steps = tuple(steps)
        self._cv_step = cv_step

    def evaluate(self, profile: P) -> Completion:
        missing = [
            MissingField(rule.field, rule.step, rule.message, rule.required)
            for rule in self._rules
            if not rule.is_satisfied(profile)
        ]
        total = sum(rule.weight for rule in self._rules)
        missing_weight = sum(2 if m.required else 1 for m in missing)
        percent = 100 if total == 0 else round(100 * (total - missing_weight) / total)

        steps = []
        for step in self._steps:
            req = sum(1 for m in missing if m.step is step and m.required)
            rec = sum(1 for m in missing if m.step is step and not m.required)
            steps.append(StepState(step, req == 0, req, rec))

        complete = not any(m.required for m in missing)
        cv_ready = self._cv_step is not None and not any(
            m.required and m.step is self._cv_step for m in missing
        )
        return Completion(
            percent=percent,
            status=ProfileStatus.COMPLETE if complete else ProfileStatus.DRAFT,
            can_generate_cv=cv_ready,
            steps=tuple(steps),
            missing=tuple(missing),
        )


class ProfileCompletenessPolicy(CompletenessPolicy[StudentProfile]):
    def __init__(self, rules: Sequence[CompletionRule[StudentProfile]] = DEFAULT_RULES) -> None:
        super().__init__(rules, tuple(Step), cv_step=Step.CV)
