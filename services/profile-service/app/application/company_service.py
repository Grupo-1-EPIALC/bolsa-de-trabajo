"""Casos de uso del perfil de empresa.

Flujo (ver `contracts/profile.md` (parte B)):
1. La empresa se registra en auth-service (razón social, CUIT, actividad) y entra con su JWT.
2. `GET /profiles/companies/me` → 404: el front ofrece completar el perfil.
3. `POST /profiles/companies/me` crea el borrador precargado con los datos de auth-service.
4. Completa rubro, ubicación, descripción, contacto, tamaño (`PATCH`) y sube el logo.
5. Los estudiantes ven el perfil público. Las búsquedas de la empresa son de jobs-service
   (el front las pide ahí; este servicio no las guarda ni las consulta).
"""

import dataclasses
import logging
import threading
from collections.abc import Mapping
from typing import Any

from app.application.company_views import owner_view, public_view, service_view
from app.domain.auth import Principal, Role
from app.domain.company import (
    COMPANY_EDITABLE_SECTIONS,
    LOGO_MAX_BYTES,
    CompanyCompletenessPolicy,
    CompanyContact,
    CompanyLegal,
    CompanyProfile,
    CompanyVisibility,
    LogoInfo,
    detect_logo_type,
)
from app.domain.errors import (
    CompanyProfileAlreadyExistsError,
    CompanyProfileNotFoundError,
    ForbiddenError,
    InvalidInputError,
    InvalidLogoError,
    LogoNotFoundError,
)
from app.domain.models import MANUAL_COMPLETION_INDICATOR
from app.domain.ports import (
    AccountDirectory,
    Clock,
    CompanyProfileRepository,
    IdGenerator,
    LogoStore,
    StoredLogo,
)
from app.domain.serialization import DecodeError, from_plain, to_plain

logger = logging.getLogger(__name__)


class CompanyProfileService:
    def __init__(
        self,
        *,
        repository: CompanyProfileRepository,
        logos: LogoStore,
        policy: CompanyCompletenessPolicy,
        accounts: AccountDirectory,
        clock: Clock,
        ids: IdGenerator,
        logo_max_bytes: int = LOGO_MAX_BYTES,
    ) -> None:
        self._repo = repository
        self._logos = logos
        self._policy = policy
        self._accounts = accounts
        self._clock = clock
        self._ids = ids
        self._logo_max_bytes = logo_max_bytes
        self._lock = threading.RLock()

    # --------------------------------------------------------------- la empresa ---

    def get_mine(self, principal: Principal) -> dict[str, Any]:
        profile = self._mine(principal)
        return self._owner(profile, principal)

    def create_mine(
        self, principal: Principal, changes: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        self._require_company(principal)
        with self._lock:
            existing = self._repo.get_by_company(principal.subject)
            if existing is not None:
                raise CompanyProfileAlreadyExistsError(existing.company_id)
            profile = self._new_profile(principal)
            if changes:
                profile = self._apply(profile, changes)
            profile = self._with_status(profile)
            self._repo.add(profile)
        return self._owner(profile, principal)

    def update_mine(self, principal: Principal, changes: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            profile = self._mine(principal)
            legal = self._legal_of(principal) or profile.legal
            updated = self._apply(dataclasses.replace(profile, legal=legal), changes)
            updated = dataclasses.replace(
                self._with_status(updated),
                version=profile.version + 1,
                updated_at=self._clock.now(),
            )
            self._repo.update(updated)
        return self._owner(updated, principal)

    def upload_logo(self, principal: Principal, content: bytes) -> dict[str, Any]:
        if not content:
            raise InvalidLogoError("El archivo del logo está vacío")
        if len(content) > self._logo_max_bytes:
            raise InvalidLogoError(
                f"El logo supera el máximo de {self._logo_max_bytes // 1024} KB",
                {"max_bytes": self._logo_max_bytes, "size_bytes": len(content)},
            )
        mime = detect_logo_type(content)
        if mime is None:
            raise InvalidLogoError(
                "Formato de logo no permitido: usá PNG, JPEG o WebP",
                {"allowed": ["image/png", "image/jpeg", "image/webp"]},
            )
        with self._lock:
            profile = self._mine(principal)
            now = self._clock.now()
            self._logos.save(profile.company_id, StoredLogo(mime, content))
            updated = self._with_status(
                dataclasses.replace(
                    profile,
                    logo=LogoInfo(mime_type=mime, size_bytes=len(content), uploaded_at=now),
                    version=profile.version + 1,
                    updated_at=now,
                )
            )
            self._repo.update(updated)
        return self._owner(updated, principal)

    def delete_logo(self, principal: Principal) -> None:
        with self._lock:
            profile = self._mine(principal)
            if profile.logo is None:
                raise LogoNotFoundError()
            self._logos.delete(profile.company_id)
            self._repo.update(
                self._with_status(
                    dataclasses.replace(
                        profile,
                        logo=None,
                        version=profile.version + 1,
                        updated_at=self._clock.now(),
                    )
                )
            )

    # ------------------------------------------------------------------ lectura ---

    def get_logo(self, company_id: str) -> StoredLogo:
        """Público (se usa en `<img>` y en `company_snapshot.logo_url` de las ofertas)."""
        logo = self._logos.get(company_id)
        if logo is None:
            raise LogoNotFoundError()
        return logo

    def get_profile(self, principal: Principal, company_id: str) -> dict[str, Any]:
        profile = self._repo.get_by_company(company_id)
        if profile is None:
            raise CompanyProfileNotFoundError({"company_id": company_id})
        if principal.role is Role.SERVICE:
            return service_view(profile)
        if principal.role is Role.ADMIN or profile.owned_by(principal.subject):
            return owner_view(profile, self._policy.evaluate(profile))
        if profile.visibility is CompanyVisibility.HIDDEN:
            raise CompanyProfileNotFoundError({"company_id": company_id})
        return public_view(profile)

    def list_profiles(
        self, principal: Principal, *, limit: int = 50, page: int = 1
    ) -> dict[str, Any]:
        if not principal.sees_everything:
            raise ForbiddenError("El listado de empresas es interno")
        limit = max(1, min(limit, 200))
        items, total = self._repo.list(offset=(max(page, 1) - 1) * limit, limit=limit)
        return {
            "items": [service_view(p) for p in items],
            "total": total,
            "page": max(page, 1),
            "size": limit,
            "pages": (total + limit - 1) // limit if total else 0,
        }

    def import_document(self, document: Mapping[str, Any]) -> bool:
        """Carga un perfil de empresa (seed de demo). No pisa uno existente."""
        try:
            profile = from_plain(CompanyProfile, dict(document), "seed")
        except DecodeError as exc:
            raise InvalidInputError(str(exc)) from exc
        with self._lock:
            if self._repo.get_by_company(profile.company_id) is not None:
                return False
            self._repo.add(self._with_status(profile))
        return True

    # ------------------------------------------------------------------ privado ---

    @staticmethod
    def _require_company(principal: Principal) -> None:
        if principal.role is not Role.COMPANY:
            raise ForbiddenError("Sólo las empresas tienen perfil de empresa")

    def _mine(self, principal: Principal) -> CompanyProfile:
        self._require_company(principal)
        profile = self._repo.get_by_company(principal.subject)
        if profile is None:
            raise CompanyProfileNotFoundError()
        return profile

    def _owner(self, profile: CompanyProfile, principal: Principal) -> dict[str, Any]:
        return owner_view(profile, self._policy.evaluate(profile))

    def _legal_of(self, principal: Principal) -> CompanyLegal | None:
        try:
            return self._accounts.company_of(principal)
        except Exception:
            logger.warning("No se pudieron leer los datos legales de %s", principal.subject)
            return None

    def _new_profile(self, principal: Principal) -> CompanyProfile:
        now = self._clock.now()
        legal = self._legal_of(principal) or CompanyLegal()
        email: str | None = None
        try:
            email = self._accounts.email_of(principal)
        except Exception:
            email = None
        return CompanyProfile(
            id=self._ids.new_company_id(),
            company_id=principal.subject,
            created_at=now,
            updated_at=now,
            legal=legal,
            display_name=legal.legal_name,
            industry=legal.activity or None,
            contact=CompanyContact(email=email),
        )

    def _apply(self, profile: CompanyProfile, changes: Mapping[str, Any]) -> CompanyProfile:
        unknown = sorted(set(changes) - set(COMPANY_EDITABLE_SECTIONS))
        if unknown:
            raise InvalidInputError("Secciones no editables", {"fields": unknown})
        if MANUAL_COMPLETION_INDICATOR in repr(dict(changes)):
            raise InvalidInputError("Hay campos sin completar (COMPLETAR_MANUALMENTE)")
        document = to_plain(profile)
        document.update(changes)
        try:
            return from_plain(CompanyProfile, document, "company")
        except DecodeError as exc:
            raise InvalidInputError(str(exc)) from exc

    def _with_status(self, profile: CompanyProfile) -> CompanyProfile:
        return dataclasses.replace(profile, status=self._policy.evaluate(profile).status)
