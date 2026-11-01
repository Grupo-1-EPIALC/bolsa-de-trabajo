"""Entidades, normalizador de campos análogos y objetos de valor de profile-service."""

import unicodedata
from dataclasses import dataclass, field
from typing import Any

ALLOWED_CV_EXTENSIONS: frozenset[str] = frozenset({"pdf", "docx", "doc", "md"})

ALLOWED_CV_MIMES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/markdown",
        "text/plain",
        "application/octet-stream",
        "",
    }
)

MANUAL_COMPLETION_INDICATOR = "COMPLETAR_MANUALMENTE"


def _norm_key(key: str) -> str:
    decomposed = unicodedata.normalize("NFD", str(key))
    no_accents = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return "".join(ch for ch in no_accents.lower() if ch.isalnum())


def _pick_analogous(obj: dict[str, Any], candidates: tuple[str, ...]) -> Any:
    if not isinstance(obj, dict):
        return None
    norm_map = {_norm_key(k): v for k, v in obj.items()}
    for cand in candidates:
        if cand in obj and obj[cand] is not None:
            return obj[cand]
        nk = _norm_key(cand)
        if nk in norm_map and norm_map[nk] is not None:
            return norm_map[nk]
    return None


def normalize_cv_suggestions(raw_input: dict[str, Any]) -> dict[str, Any]:
    """Reconoce campos análogos y reemplaza faltantes/null por COMPLETAR_MANUALMENTE o []."""
    raw = raw_input if isinstance(raw_input, dict) else {}
    pending: list[str] = []

    def str_or_manual(val: Any, path: str) -> str:
        if val is None:
            pending.append(path)
            return MANUAL_COMPLETION_INDICATOR
        s = str(val).strip()
        if not s or s.lower() in {
            "null",
            "none",
            "undefined",
            "n/a",
            "na",
            "sin especificar",
            "no especificado",
            MANUAL_COMPLETION_INDICATOR.lower(),
        }:
            pending.append(path)
            return MANUAL_COMPLETION_INDICATOR
        return s

    personal_raw = _pick_analogous(
        raw,
        ("personal", "datos_personales", "contacto", "contact", "informacion_personal"),
    )
    if not isinstance(personal_raw, dict):
        personal_raw = {}

    personal = {
        "name": str_or_manual(
            _pick_analogous(personal_raw, ("name", "nombre", "full_name", "nombre_completo"))
            or _pick_analogous(raw, ("name", "nombre", "full_name", "nombre_completo")),
            "personal.name",
        ),
        "email": str_or_manual(
            _pick_analogous(personal_raw, ("email", "correo", "mail", "correo_electronico"))
            or _pick_analogous(raw, ("email", "correo", "mail")),
            "personal.email",
        ),
        "phone": str_or_manual(
            _pick_analogous(personal_raw, ("phone", "telefono", "celular", "tel", "movil"))
            or _pick_analogous(raw, ("phone", "telefono", "celular")),
            "personal.phone",
        ),
        "location": str_or_manual(
            _pick_analogous(
                personal_raw,
                ("location", "ubicacion", "ciudad", "localidad", "residencia", "pais"),
            )
            or _pick_analogous(raw, ("location", "ubicacion", "ciudad", "localidad")),
            "personal.location",
        ),
    }

    summary = str_or_manual(
        _pick_analogous(
            raw,
            ("summary", "resumen", "perfil", "perfil_profesional", "objetivo", "sobre_mi", "bio"),
        ),
        "summary",
    )

    skills_raw = _pick_analogous(
        raw,
        ("skills", "competencias", "habilidades", "tecnologias", "conocimientos", "aptitudes"),
    )
    skills: list[dict[str, Any]] = []
    if isinstance(skills_raw, list):
        for item in skills_raw:
            if isinstance(item, str) and item.strip():
                idx = len(skills)
                pending.append(f"skills[{idx}].level")
                skills.append({"name": item.strip(), "level": MANUAL_COMPLETION_INDICATOR})
            elif isinstance(item, dict):
                name_val = _pick_analogous(
                    item, ("name", "skill", "nombre", "competencia", "tecnologia")
                )
                clean_name = str(name_val or "").strip()
                if not clean_name or clean_name.lower() == "null":
                    continue
                idx = len(skills)
                lvl_val = _pick_analogous(
                    item, ("level", "level_estimado", "nivel", "nivel_estimado")
                )
                parsed_lvl: int | str = MANUAL_COMPLETION_INDICATOR
                if isinstance(lvl_val, int) and 1 <= lvl_val <= 5:
                    parsed_lvl = lvl_val
                elif isinstance(lvl_val, str) and lvl_val.strip().isdigit():
                    n = int(lvl_val.strip())
                    if 1 <= n <= 5:
                        parsed_lvl = n
                if parsed_lvl == MANUAL_COMPLETION_INDICATOR:
                    pending.append(f"skills[{idx}].level")
                skills.append({"name": clean_name, "level": parsed_lvl})
    if not skills:
        pending.append("skills")

    exp_raw = _pick_analogous(
        raw,
        (
            "experience",
            "experiencia",
            "experiencia_laboral",
            "antecedentes",
            "empleos",
            "trabajos",
            "practicas",
        ),
    )
    experience: list[dict[str, str]] = []
    if isinstance(exp_raw, list):
        for idx, it in enumerate(exp_raw):
            if isinstance(it, dict):
                experience.append(
                    {
                        "company": str_or_manual(
                            _pick_analogous(
                                it, ("company", "empresa", "organizacion", "empleador")
                            ),
                            f"experience[{idx}].company",
                        ),
                        "role": str_or_manual(
                            _pick_analogous(it, ("role", "puesto", "cargo", "rol", "position")),
                            f"experience[{idx}].role",
                        ),
                        "start": str_or_manual(
                            _pick_analogous(
                                it, ("start", "inicio", "fecha_inicio", "desde", "years", "periodo")
                            ),
                            f"experience[{idx}].start",
                        ),
                        "end": str_or_manual(
                            _pick_analogous(it, ("end", "fin", "fecha_fin", "hasta", "actualidad")),
                            f"experience[{idx}].end",
                        ),
                        "description": str_or_manual(
                            _pick_analogous(
                                it, ("description", "descripcion", "tareas", "responsabilidades")
                            ),
                            f"experience[{idx}].description",
                        ),
                    }
                )
    if not experience:
        pending.append("experience")

    edu_raw = _pick_analogous(
        raw,
        ("education", "educacion", "formacion", "formacion_academica", "estudios", "titulos"),
    )
    education: list[dict[str, str]] = []
    if isinstance(edu_raw, list):
        for idx, it in enumerate(edu_raw):
            if isinstance(it, dict):
                education.append(
                    {
                        "institution": str_or_manual(
                            _pick_analogous(
                                it,
                                ("institution", "institucion", "universidad", "colegio", "centro"),
                            ),
                            f"education[{idx}].institution",
                        ),
                        "degree": str_or_manual(
                            _pick_analogous(it, ("degree", "titulo", "carrera", "estudio")),
                            f"education[{idx}].degree",
                        ),
                        "status": str_or_manual(
                            _pick_analogous(it, ("status", "estado", "situacion")),
                            f"education[{idx}].status",
                        ),
                        "start": str_or_manual(
                            _pick_analogous(it, ("start", "inicio", "fecha_inicio", "desde")),
                            f"education[{idx}].start",
                        ),
                        "end": str_or_manual(
                            _pick_analogous(
                                it, ("end", "fin", "fecha_fin", "hasta", "anio", "year")
                            ),
                            f"education[{idx}].end",
                        ),
                    }
                )
    if not education:
        pending.append("education")

    lang_raw = _pick_analogous(raw, ("languages", "idiomas", "lenguajes"))
    languages: list[dict[str, str]] = []
    if isinstance(lang_raw, list):
        for it in lang_raw:
            if isinstance(it, dict):
                name_val = _pick_analogous(it, ("name", "language", "idioma", "nombre"))
                clean_name = str(name_val or "").strip()
                if not clean_name or clean_name.lower() == "null":
                    continue
                idx = len(languages)
                languages.append(
                    {
                        "name": clean_name,
                        "level": str_or_manual(
                            _pick_analogous(it, ("level", "nivel", "fluidez", "proficiency")),
                            f"languages[{idx}].level",
                        ),
                    }
                )
    if not languages:
        pending.append("languages")

    certs_raw = _pick_analogous(
        raw, ("certifications", "certificaciones", "cursos", "capacitaciones")
    )
    certifications: list[str] = []
    if isinstance(certs_raw, list):
        for c in certs_raw:
            val = (
                c
                if isinstance(c, str)
                else _pick_analogous(c, ("name", "nombre", "title", "curso"))
            )
            if val and str(val).strip() and str(val).strip().lower() != "null":
                certifications.append(str(val).strip())
    if not certifications:
        pending.append("certifications")

    links_raw = _pick_analogous(raw, ("links", "enlaces", "redes", "urls", "portfolio"))
    links: list[str] = []
    if isinstance(links_raw, list):
        for lnk in links_raw:
            val = (
                lnk
                if isinstance(lnk, str)
                else _pick_analogous(lnk, ("url", "link", "href", "enlace"))
            )
            if val and str(val).strip() and str(val).strip().lower() != "null":
                links.append(str(val).strip())
    if not links:
        pending.append("links")

    return {
        "personal": personal,
        "summary": summary,
        "skills": skills,
        "experience": experience,
        "education": education,
        "languages": languages,
        "certifications": certifications,
        "links": links,
        "pending_manual_fields": pending,
    }


@dataclass(frozen=True)
class UploadedCvFile:
    """Archivo de CV validado y almacenado en CV_STORAGE_PATH."""

    original_filename: str
    stored_filename: str
    extension: str
    mime_type: str
    size_bytes: int
    content_base64: str


@dataclass(frozen=True)
class CvExtractionResult:
    """Resultado de sugerencias de perfil extraídas del CV vía webhook n8n (origin='AI')."""

    profile_id: str
    file: dict[str, Any]
    cv_suggestions: dict[str, Any]
    origin: str = "AI"
    model: str | None = None
    prompt_version: str = "1.1.0"
    generated_at: str = ""
    verified: bool = True
    disclaimer: str = (
        "Sugerencias extraídas automáticamente por IA del CV subido. "
        "Los campos con COMPLETAR_MANUALMENTE o listas vacías [] deben completarse manualmente."
    )
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        normalized_suggestions = normalize_cv_suggestions(self.cv_suggestions)
        return {
            "profile_id": self.profile_id,
            "file": self.file,
            "cv_suggestions": normalized_suggestions,
            "origin": "AI",
            "model": self.model or "nvidia/nemotron-3-ultra-550b-a55b",
            "prompt_version": self.prompt_version,
            "generated_at": self.generated_at,
            "verified": self.verified,
            "disclaimer": self.disclaimer,
        }


@dataclass
class CvExtractionJobState:
    """Estado de un proceso asíncrono de extracción de CV."""

    job_id: str
    profile_id: str
    filename: str
    stored_filename: str
    status: str  # "processing" | "completed" | "failed"
    stage: str
    started_monotonic: float
    finished_monotonic: float | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
