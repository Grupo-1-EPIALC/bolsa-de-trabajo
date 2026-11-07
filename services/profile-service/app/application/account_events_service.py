"""Reacción de profile-service a los eventos de cuenta de auth-service.

- `account.deleted`: la cuenta se registra como borrada (aunque no tuviera perfil) y su perfil
  de estudiante o de empresa pasa al archivo: deja de verse en `/me`, en los listados, en el
  pool de matching y en las búsquedas de empresas. El logo deja de servirse.
- `account.updated`: se actualiza la copia de sólo lectura de los datos legales de la empresa.
  El email del estudiante no se toca: `personal.email` es un dato de contacto que edita él.

Todo es idempotente: el mismo evento puede llegar dos veces (`contracts/account_events.md`).
"""

import dataclasses
import logging
import threading
from typing import Any

from app.domain.account_events import AccountEvent, AccountEventResult, AccountEventType
from app.domain.auth import Principal, Role
from app.domain.errors import ForbiddenError
from app.domain.ports import (
    Clock,
    CompanyProfileRepository,
    DeletedAccounts,
    LogoStore,
    ProfileRepository,
)

logger = logging.getLogger(__name__)


class AccountEventsService:
    def __init__(
        self,
        *,
        profiles: ProfileRepository,
        companies: CompanyProfileRepository,
        logos: LogoStore,
        deleted_accounts: DeletedAccounts,
        clock: Clock,
    ) -> None:
        self._profiles = profiles
        self._companies = companies
        self._logos = logos
        self._deleted = deleted_accounts
        self._clock = clock
        self._lock = threading.Lock()

    def handle(self, principal: Principal, event: AccountEvent) -> dict[str, Any]:
        if principal.role is not Role.SERVICE:
            raise ForbiddenError("Los eventos de cuenta son internos (X-Service-Token)")
        with self._lock:
            if event.event == AccountEventType.DELETED or event.deleted:
                result = self._delete(event)
            elif event.event == AccountEventType.UPDATED:
                result = self._update(event)
            else:
                result = AccountEventResult.IGNORED
        logger.info("Evento %s de %s: %s", event.event, event.user_id, result.value)
        return {"event": event.event, "user_id": event.user_id, "result": result.value}

    def _delete(self, event: AccountEvent) -> AccountEventResult:
        newly_marked = self._deleted.mark(event.user_id, event.role, event.occurred_at)
        archived = False
        profile = self._profiles.get_by_user(event.user_id)
        if profile is not None:
            archived |= self._profiles.archive(profile.id, event.occurred_at)
        if self._companies.get_by_company(event.user_id) is not None:
            archived |= self._companies.archive(event.user_id, event.occurred_at)
            self._logos.delete(event.user_id)
        if archived:
            return AccountEventResult.ARCHIVED
        return AccountEventResult.UPDATED if newly_marked else AccountEventResult.IGNORED

    def _update(self, event: AccountEvent) -> AccountEventResult:
        if event.company is None or self._deleted.contains(event.user_id):
            return AccountEventResult.IGNORED
        profile = self._companies.get_by_company(event.user_id)
        if profile is None or profile.legal == event.company:
            return AccountEventResult.IGNORED
        self._companies.update(
            dataclasses.replace(
                profile,
                legal=event.company,
                version=profile.version + 1,
                updated_at=self._clock.now(),
            )
        )
        return AccountEventResult.UPDATED
