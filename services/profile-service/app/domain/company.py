"""Perfil público de la empresa (`CompanyProfile`).

Los datos legales (razón social, CUIT y actividad) los administra auth-service (AGENTS.md
§4.1): acá se guarda una copia de lectura en `legal` y no se editan. Lo propio del perfil es
la "marca empleadora": nombre comercial, logo, rubro, tamaño, ubicación, descripción, links,
beneficios y qué perfiles contrata. Las búsquedas (ofertas) son de jobs-service: este
servicio no las guarda ni las consulta; el front las pide a `GET /api/v1/companies/me/searches`.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.domain.completion import CompletenessPolicy, CompletionRule
from app.domain.enums import ProfileStatus, WorkModality
from app.domain.profile import Location


class CompanySize(StrEnum):
    """Mismos valores que `company_snapshot.size` de jobs-service (§6)."""

    S_1_10 = "1-10"
    S_11_50 = "11-50"
    S_51_200 = "51-200"
    S_201_1000 = "201-1000"
    S_1000_PLUS = "1000+"


class CompanyLinkType(StrEnum):
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    X = "x"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    GITHUB = "github"
    OTHER = "other"


class CompanyVisibility(StrEnum):
    PUBLIC = "public"  # visible para estudiantes
    HIDDEN = "hidden"  # sólo la empresa, admin y servicios


class CompanyStep(StrEnum):
    COMPANY = "company"  # datos de la empresa (obligatorios)
    BRANDING = "branding"  # logo, links, beneficios… (recomendados)


@dataclass(frozen=True)
class CompanyLegal:
    """Copia de auth-service. No se edita desde profile-service."""

    legal_name: str = ""
    cuit: str = ""
    activity: str = ""


@dataclass(frozen=True)
class CompanyContact:
    email: str | None = None  # contacto de RR. HH.
    phone: str | None = None
    name: str | None = None
    public: bool = False  # si los estudiantes ven el contacto


@dataclass(frozen=True)
class CompanyLink:
    type: CompanyLinkType
    url: str


@dataclass(frozen=True)
class HiringInfo:
    areas: tuple[str, ...] = ()  # áreas en las que suele contratar
    hires_students: bool = True
    internship_program: bool = False
    internship_agreements: tuple[str, ...] = ()  # universidades con convenio de pasantías


@dataclass(frozen=True)
class InclusiveHiring:
    accepts_disability_certificate: bool = False
    accessible_workplace: bool = False


@dataclass(frozen=True)
class LogoInfo:
    mime_type: str
    size_bytes: int
    uploaded_at: datetime


@dataclass(frozen=True)
class CompanyProfile:
    id: str
    company_id: str  # `sub` de la empresa en auth-service = `company_id` de jobs-service
    created_at: datetime
    updated_at: datetime
    version: int = 1
    status: ProfileStatus = ProfileStatus.DRAFT
    legal: CompanyLegal = field(default_factory=CompanyLegal)
    display_name: str = ""  # nombre comercial
    tagline: str | None = None
    description: str | None = None
    industry: str | None = None  # rubro
    size: CompanySize | None = None
    founded_year: int | None = None
    location: Location | None = None  # sede principal (sin dirección exacta)
    offices: tuple[Location, ...] = ()
    website: str | None = None
    links: tuple[CompanyLink, ...] = ()
    contact: CompanyContact = field(default_factory=CompanyContact)
    work_modalities: tuple[WorkModality, ...] = ()
    benefits: tuple[str, ...] = ()
    values: tuple[str, ...] = ()
    hiring: HiringInfo = field(default_factory=HiringInfo)
    inclusive_hiring: InclusiveHiring | None = None
    logo: LogoInfo | None = None
    visibility: CompanyVisibility = CompanyVisibility.PUBLIC

    def owned_by(self, user_id: str) -> bool:
        return self.company_id == user_id

    @property
    def name(self) -> str:
        """Nombre para mostrar: el comercial o, si falta, la razón social."""
        return self.display_name.strip() or self.legal.legal_name


COMPANY_EDITABLE_SECTIONS: tuple[str, ...] = (
    "display_name",
    "tagline",
    "description",
    "industry",
    "size",
    "founded_year",
    "location",
    "offices",
    "website",
    "links",
    "contact",
    "work_modalities",
    "benefits",
    "values",
    "hiring",
    "inclusive_hiring",
    "visibility",
)


# ------------------------------------------------------------------ completitud ---


def _has(text: str | None) -> bool:
    return bool(text and text.strip())


def _location_ok(c: CompanyProfile) -> bool:
    loc = c.location
    return bool(loc and _has(loc.country) and _has(loc.province) and _has(loc.city))


COMPANY_RULES: tuple[CompletionRule[CompanyProfile], ...] = (
    CompletionRule(
        "display_name", CompanyStep.COMPANY, "Ingresá el nombre comercial", lambda c: _has(c.name)
    ),
    CompletionRule(
        "industry", CompanyStep.COMPANY, "Indicá el rubro de la empresa", lambda c: _has(c.industry)
    ),
    CompletionRule(
        "location",
        CompanyStep.COMPANY,
        "Indicá país, provincia y ciudad de la sede",
        _location_ok,
    ),
    CompletionRule(
        "description",
        CompanyStep.COMPANY,
        "Contá a qué se dedica la empresa y cómo es trabajar ahí",
        lambda c: _has(c.description),
    ),
    CompletionRule(
        "contact.email",
        CompanyStep.COMPANY,
        "Cargá un email de contacto para las búsquedas",
        lambda c: _has(c.contact.email),
    ),
    CompletionRule(
        "size", CompanyStep.COMPANY, "Indicá la cantidad de empleados", lambda c: c.size is not None
    ),
    CompletionRule(
        "logo", CompanyStep.BRANDING, "Subí el logo", lambda c: c.logo is not None, required=False
    ),
    CompletionRule(
        "tagline",
        CompanyStep.BRANDING,
        "Agregá una frase corta que presente a la empresa",
        lambda c: _has(c.tagline),
        required=False,
    ),
    CompletionRule(
        "website",
        CompanyStep.BRANDING,
        "Agregá el sitio web",
        lambda c: _has(c.website),
        required=False,
    ),
    CompletionRule(
        "links",
        CompanyStep.BRANDING,
        "Sumá LinkedIn u otras redes",
        lambda c: bool(c.links),
        required=False,
    ),
    CompletionRule(
        "benefits",
        CompanyStep.BRANDING,
        "Contá qué beneficios ofrecen",
        lambda c: bool(c.benefits),
        required=False,
    ),
    CompletionRule(
        "hiring.areas",
        CompanyStep.BRANDING,
        "Indicá en qué áreas suelen contratar",
        lambda c: bool(c.hiring.areas),
        required=False,
    ),
)


class CompanyCompletenessPolicy(CompletenessPolicy[CompanyProfile]):
    def __init__(self, rules: Sequence[CompletionRule[CompanyProfile]] = COMPANY_RULES) -> None:
        super().__init__(rules, tuple(CompanyStep))


# ------------------------------------------------------------------------ logo ---

LOGO_MAX_BYTES = 1024 * 1024
_SIGNATURES: tuple[tuple[str, bytes, int], ...] = (
    ("image/png", b"\x89PNG\r\n\x1a\n", 0),
    ("image/jpeg", b"\xff\xd8\xff", 0),
    ("image/webp", b"WEBP", 8),  # RIFF....WEBP
)


def detect_logo_type(content: bytes) -> str | None:
    """Tipo real por la firma del archivo (no por la extensión). SVG no: puede traer scripts."""
    for mime, signature, offset in _SIGNATURES:
        if content[offset : offset + len(signature)] == signature:
            if mime == "image/webp" and not content.startswith(b"RIFF"):
                continue
            return mime
    return None
