"""Reacción de jobs-service a los eventos de cuenta de auth-service.

- `account.deleted`: la baja se registra (rechaza el JWT que todavía no venció) y, si es una
  empresa, todas sus ofertas pasan al archivo: dejan de verse en `GET /jobs`, en el detalle,
  en `/companies/me/searches` y en el matching.
- `account.updated`: se ignora. El `company_snapshot` sale del perfil de empresa
  (profile-service) y se refresca cuando la empresa crea o edita una oferta.

Todo es idempotente: el mismo evento puede llegar dos veces (`contracts/auth.md` (parte B)).
"""

import logging
import threading

from app.domain.account_events import AccountEvent, AccountEventResult, AccountEventType
from app.domain.auth import Principal, Role
from app.domain.errors import ForbiddenError
from app.domain.ports import DeletedAccounts, JobRepository, JsonDict

logger = logging.getLogger(__name__)


class AccountEventsService:
    def __init__(self, *, repository: JobRepository, deleted_accounts: DeletedAccounts) -> None:
        self._repository = repository
        self._deleted = deleted_accounts
        self._lock = threading.Lock()

    def handle(self, principal: Principal, event: AccountEvent) -> JsonDict:
        if principal.role is not Role.SERVICE:
            raise ForbiddenError("Los eventos de cuenta son internos (X-Service-Token)")
        archived = 0
        with self._lock:
            if event.event == AccountEventType.DELETED or event.deleted:
                newly_marked = self._deleted.mark(event.user_id, event.role, event.occurred_at)
                archived = self._repository.archive_company(event.user_id, event.occurred_at)
                if archived:
                    result = AccountEventResult.ARCHIVED
                elif newly_marked:
                    result = AccountEventResult.REGISTERED
                else:
                    result = AccountEventResult.IGNORED
            else:
                result = AccountEventResult.IGNORED
        logger.info("Evento %s de %s: %s", event.event, event.user_id, result.value)
        return {
            "event": event.event,
            "user_id": event.user_id,
            "result": result.value,
            "archived_jobs": archived,
        }
