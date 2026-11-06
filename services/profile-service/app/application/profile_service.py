"""Casos de uso del perfil del estudiante.

Flujo del alta (ver `contracts/profile_frontend.md`):
1. El estudiante se registra en auth-service y entra con su JWT.
2. `GET /profiles/me` → 404 `PROFILE_NOT_FOUND`: el front ofrece subir el CV o cargar a mano.
3. Sube el CV (`POST /profiles/me/cv`) → n8n (WF-01) extrae los datos → borrador sugerido.
4. Confirma/corrige los datos (`PATCH /profiles/me`) y completa preferencias y privacidad.
5. Con el perfil listo descarga un CV nuevo en PDF o DOCX (`GET /profiles/me/cv.pdf`).
"""

import dataclasses
import logging
import re
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.application.suggestion_mapper import CvSuggestionMapper
from app.application.upload_cv_use_case import UploadAndExtractCvUseCase
from app.application.views import admin_view, company_view, owner_view, service_view
from app.domain.auth import Principal, Role
from app.domain.completion import Completion, ProfileCompletenessPolicy
from app.domain.cv_document import CvDocumentBuilder
from app.domain.errors import (
    ForbiddenError,
    InvalidInputError,
    ProfileAlreadyExistsError,
    ProfileIncompleteError,
    ProfileNotFoundError,
    SuggestionsNotFoundError,
    UnsupportedFormatError,
)
from app.domain.models import MANUAL_COMPLETION_INDICATOR, UploadedCvFile
from app.domain.ports import (
    AccountDirectory,
    Clock,
    CvRenderer,
    EventPublisher,
    IdGenerator,
    ProfileRepository,
    RenderedFile,
)
from app.domain.profile import EDITABLE_SECTIONS, CvFile, Experience, StudentProfile
from app.domain.serialization import DecodeError, from_plain, to_plain
from app.domain.skills import SkillExtractor, normalize_text

logger = logging.getLogger(__name__)

MAX_SERVICE_PAGE = 200


@dataclass(frozen=True)
class GeneratedCv:
    file: RenderedFile
    filename: str


def _find_placeholders(value: Any, path: str = "") -> list[str]:
    if isinstance(value, Mapping):
        found: list[str] = []
        for key, item in value.items():
            found += _find_placeholders(item, f"{path}.{key}" if path else str(key))
        return found
    if isinstance(value, list | tuple):
        found = []
        for i, item in enumerate(value):
            found += _find_placeholders(item, f"{path}[{i}]")
        return found
    return [path] if value == MANUAL_COMPLETION_INDICATOR else []


def _months_between(start: str, end: str, now_year: int, now_month: int) -> int | None:
    def parse(text: str, default_month: int) -> tuple[int, int] | None:
        if text.strip().lower() in {"actual", "actualidad", "presente"}:
            return now_year, now_month
        match = re.fullmatch(r"(\d{4})(?:-(\d{1,2}))?", text.strip())
        if not match:
            return None
        return int(match.group(1)), int(match.group(2) or default_month)

    first = parse(start, 1)
    last = parse(end, 12)
    if first is None or last is None:
        return None
    months = (last[0] - first[0]) * 12 + (last[1] - first[1]) + 1
    return max(0, months)


class ProfileService:
    def __init__(
        self,
        *,
        repository: ProfileRepository,
        policy: ProfileCompletenessPolicy,
        extractor: SkillExtractor,
        publisher: EventPublisher,
        accounts: AccountDirectory,
        clock: Clock,
        ids: IdGenerator,
        cv_upload: UploadAndExtractCvUseCase,
        cv_builder: CvDocumentBuilder,
        renderers: Sequence[CvRenderer],
    ) -> None:
        self._repo = repository
        self._policy = policy
        self._extractor = extractor
        self._publisher = publisher
        self._accounts = accounts
        self._clock = clock
        self._ids = ids
        self._cv_upload = cv_upload
        self._cv_builder = cv_builder
        self._renderers = {r.format: r for r in renderers}
        self._mapper = CvSuggestionMapper(extractor)
        # Serializa leer-modificar-guardar: el worker del CV escribe en paralelo al usuario.
        self._lock = threading.RLock()

    # ------------------------------------------------------------ el estudiante ---

    def get_mine(self, principal: Principal) -> dict[str, Any]:
        profile = self._mine(principal)
        return owner_view(profile, self._policy.evaluate(profile))

    def create_mine(
        self, principal: Principal, changes: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        self._require_student(principal)
        with self._lock:
            existing = self._repo.get_by_user(principal.subject)
            if existing is not None:
                raise ProfileAlreadyExistsError(existing.id)
            profile = self._new_profile(principal)
            if changes:
                profile = self._apply(profile, changes)
            profile = self._with_status(profile)
            self._repo.add(profile)
        self._publish(profile)
        return owner_view(profile, self._policy.evaluate(profile))

    def update_mine(self, principal: Principal, changes: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            profile = self._mine(principal)
            updated = self._with_status(self._apply(profile, changes))
            updated = dataclasses.replace(
                updated, version=profile.version + 1, updated_at=self._clock.now()
            )
            self._repo.update(updated)
        self._publish(updated)
        return owner_view(updated, self._policy.evaluate(updated))

    # ---------------------------------------------------------------- CV + IA ---

    def start_cv_extraction(
        self, principal: Principal, *, filename: str, content: bytes, mime_type: str
    ) -> dict[str, Any]:
        """Crea el perfil en borrador si no existe, guarda el archivo y dispara WF-01."""
        self._require_student(principal)
        with self._lock:
            profile = self._repo.get_by_user(principal.subject)
            if profile is None:
                profile = self._with_status(self._new_profile(principal))
                self._repo.add(profile)
        profile_id = profile.id
        account_email = profile.personal.email or None

        def on_stored(file: UploadedCvFile) -> None:
            self._record_cv_file(profile_id, file)

        def on_completed(result: dict[str, Any]) -> dict[str, Any]:
            return self._store_suggestions(profile_id, result, account_email)

        snapshot = self._cv_upload.start_async(
            profile_id=profile_id,
            filename=filename,
            content=content,
            mime_type=mime_type,
            on_stored=on_stored,
            on_completed=on_completed,
        )
        return snapshot

    def get_cv_job(self, principal: Principal, job_id: str) -> dict[str, Any]:
        profile = self._mine(principal)
        if self._cv_upload.job_profile_id(job_id) != profile.id:
            raise ProfileNotFoundError({"job_id": job_id})  # job ajeno → mismo 404
        return self._cv_upload.get_job_status(job_id)

    def get_suggestions(self, principal: Principal) -> dict[str, Any]:
        profile = self._mine(principal)
        if profile.cv_suggestions is None:
            raise SuggestionsNotFoundError()
        return dict(profile.cv_suggestions)

    def discard_suggestions(self, principal: Principal) -> None:
        with self._lock:
            profile = self._mine(principal)
            if profile.cv_suggestions is None:
                raise SuggestionsNotFoundError()
            self._repo.update(dataclasses.replace(profile, cv_suggestions=None))

    def generate_cv(self, principal: Principal, fmt: str) -> GeneratedCv:
        renderer = self._renderers.get(fmt)
        if renderer is None:
            raise UnsupportedFormatError(fmt, sorted(self._renderers))
        profile = self._mine(principal)
        completion = self._policy.evaluate(profile)
        if not completion.can_generate_cv:
            missing = [
                {"field": m.field, "step": m.step.value, "message": m.message}
                for m in completion.missing
                if m.required and m.step.value == "cv"
            ]
            raise ProfileIncompleteError("Completá los datos del CV antes de generarlo", missing)
        document = self._cv_builder.build(profile, self._clock.now())
        rendered = renderer.render(document)
        return GeneratedCv(rendered, f"{document.file_stem}.{rendered.extension}")

    # --------------------------------------------- servicios, admin y empresas ---

    def get_profile(self, principal: Principal, profile_id: str) -> dict[str, Any]:
        profile = self._repo.get(profile_id)
        if profile is None:
            raise ProfileNotFoundError({"profile_id": profile_id})
        if principal.role is Role.SERVICE:
            return service_view(profile)
        if principal.role is Role.ADMIN:
            return admin_view(profile, self._policy.evaluate(profile))
        if principal.role is Role.STUDENT and profile.owned_by(principal.subject):
            return owner_view(profile, self._policy.evaluate(profile))
        if (
            principal.role is Role.COMPANY
            and profile.is_searchable
            and (profile.visibility.value == "public_to_companies")
        ):
            return company_view(profile)
        raise ProfileNotFoundError({"profile_id": profile_id})  # ajeno → mismo 404

    def list_profiles(
        self,
        principal: Principal,
        *,
        skills: Sequence[str] = (),
        limit: int = 50,
        page: int = 1,
        include_all: bool = False,
    ) -> dict[str, Any]:
        """Pool para matching / mcp-tools. Por defecto sólo perfiles buscables."""
        if not principal.sees_everything:
            raise ForbiddenError("El listado de perfiles es interno")
        limit = max(1, min(limit, MAX_SERVICE_PAGE))
        wanted = frozenset(self._extractor.normalize(s) for s in skills if s.strip())
        everything, _total = self._repo.list(offset=0, limit=10_000)
        selected = [
            p
            for p in everything
            if (include_all or p.is_searchable) and (not wanted or p.has_skill(wanted))
        ]
        start = (max(page, 1) - 1) * limit
        chunk = selected[start : start + limit]
        view = service_view if principal.role is Role.SERVICE else self._admin_item
        return {
            "items": [view(p) for p in chunk],
            "total": len(selected),
            "page": max(page, 1),
            "size": limit,
            "pages": (len(selected) + limit - 1) // limit if selected else 0,
        }

    def import_document(self, document: Mapping[str, Any]) -> bool:
        """Carga un perfil completo (seed de demo). No pisa uno existente."""
        try:
            profile = from_plain(StudentProfile, dict(document), "seed")
        except DecodeError as exc:
            raise InvalidInputError(str(exc)) from exc
        with self._lock:
            if self._repo.get(profile.id) or self._repo.get_by_user(profile.user_id):
                return False
            self._check_invariants(profile)
            self._repo.add(self._with_status(self._enrich(profile)))
        return True

    # ------------------------------------------------------------------ privado ---

    def _admin_item(self, profile: StudentProfile) -> dict[str, Any]:
        return admin_view(profile, self._policy.evaluate(profile))

    @staticmethod
    def _require_student(principal: Principal) -> None:
        if principal.role is not Role.STUDENT:
            raise ForbiddenError("Sólo los estudiantes tienen perfil")

    def _mine(self, principal: Principal) -> StudentProfile:
        self._require_student(principal)
        profile = self._repo.get_by_user(principal.subject)
        if profile is None:
            raise ProfileNotFoundError()
        return profile

    def _new_profile(self, principal: Principal) -> StudentProfile:
        now = self._clock.now()
        email = ""
        try:
            email = self._accounts.email_of(principal) or ""
        except Exception:
            logger.warning("No se pudo leer el email de auth-service para %s", principal.subject)
        profile = StudentProfile(
            id=self._ids.new_profile_id(),
            user_id=principal.subject,
            created_at=now,
            updated_at=now,
        )
        if email:
            profile = dataclasses.replace(
                profile, personal=dataclasses.replace(profile.personal, email=email)
            )
        return profile

    def _apply(self, profile: StudentProfile, changes: Mapping[str, Any]) -> StudentProfile:
        unknown = sorted(set(changes) - set(EDITABLE_SECTIONS))
        if unknown:
            raise InvalidInputError("Secciones no editables", {"fields": unknown})
        placeholders = _find_placeholders(dict(changes))
        if placeholders:
            raise InvalidInputError(
                "Hay campos sin completar (COMPLETAR_MANUALMENTE)", {"fields": placeholders}
            )
        consents = changes.get("consents")
        needs_stamp = isinstance(consents, Mapping) and consents.get("data_processing")
        if needs_stamp and isinstance(consents, Mapping) and not consents.get("accepted_at"):
            stamp = to_plain(self._clock.now())
            changes = {**changes, "consents": {**consents, "accepted_at": stamp}}
        document = to_plain(profile)
        for key, value in changes.items():
            document[key] = value
        try:
            candidate = from_plain(StudentProfile, document, "profile")
        except DecodeError as exc:
            raise InvalidInputError(str(exc)) from exc
        self._check_invariants(candidate)
        return self._enrich(candidate)

    @staticmethod
    def _check_invariants(profile: StudentProfile) -> None:
        errors = []
        for i, skill in enumerate(profile.skills):
            if not 1 <= skill.level <= 5:
                errors.append(f"skills[{i}].level debe estar entre 1 y 5")
        hours = profile.work_conditions.weekly_hours
        if hours and not 0 < hours.min <= hours.max <= 80:
            errors.append("work_conditions.weekly_hours debe cumplir 0 < min ≤ max ≤ 80")
        salary = profile.work_conditions.salary
        if salary and salary.min is not None and salary.max is not None and salary.max < salary.min:
            errors.append("work_conditions.salary.max debe ser ≥ min")
        if salary and not salary.to_agree and salary.min is not None and salary.currency is None:
            errors.append("work_conditions.salary.currency es obligatoria si hay monto")
        if errors:
            raise InvalidInputError("Datos inconsistentes", {"errors": errors})

    def _enrich(self, profile: StudentProfile) -> StudentProfile:
        """Datos calculados por reglas: skills normalizadas y meses de experiencia."""
        skills = []
        seen: set[str] = set()
        for skill in profile.skills:
            key = self._extractor.normalize(skill.name)
            if key in seen:
                continue  # skill duplicada: gana la primera
            seen.add(key)
            skills.append(
                dataclasses.replace(
                    skill,
                    name=self._extractor.label(skill.name),  # nombre oficial del catálogo
                    normalized=key,
                    category=skill.category or self._extractor.category(skill.name),
                )
            )
        now = self._clock.now()
        experience: list[Experience] = [
            dataclasses.replace(e, months=_months_between(e.start, e.end, now.year, now.month))
            for e in profile.experience
        ]
        languages = [
            dataclasses.replace(lang, normalized=normalize_text(lang.name))
            for lang in profile.languages
        ]
        return dataclasses.replace(
            profile,
            skills=tuple(skills),
            experience=tuple(experience),
            languages=tuple(languages),
        )

    def _with_status(self, profile: StudentProfile) -> StudentProfile:
        completion: Completion = self._policy.evaluate(profile)
        return dataclasses.replace(profile, status=completion.status)

    def _record_cv_file(self, profile_id: str, file: UploadedCvFile) -> None:
        with self._lock:
            profile = self._repo.get(profile_id)
            if profile is None:
                return
            self._repo.update(
                dataclasses.replace(profile, cv_files=(*profile.cv_files, self._cv_entry(file)))
            )

    def _cv_entry(self, file: UploadedCvFile) -> CvFile:
        return CvFile(
            stored_filename=file.stored_filename,
            original_filename=file.original_filename,
            mime_type=file.mime_type,
            size_bytes=file.size_bytes,
            uploaded_at=self._clock.now(),
        )

    def _store_suggestions(
        self, profile_id: str, result: dict[str, Any], account_email: str | None
    ) -> dict[str, Any]:
        mapped = self._mapper.to_profile_draft(
            result.get("cv_suggestions") or {}, account_email=account_email
        )
        enriched = {
            **result,
            **mapped,
            "received_at": to_plain(self._clock.now()),
        }
        with self._lock:
            profile = self._repo.get(profile_id)
            if profile is not None:
                self._repo.update(dataclasses.replace(profile, cv_suggestions=enriched))
        return enriched

    def _publish(self, profile: StudentProfile) -> None:
        try:
            self._publisher.profile_updated(profile)
        except Exception:
            logger.warning("No se pudo publicar profile.updated para %s", profile.id)
