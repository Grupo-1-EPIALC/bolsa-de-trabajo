"""Eventos de cuenta que publica auth-service (`contracts/auth.md` (parte B)).

auth-service es el dueño de las cuentas: jobs-service sólo reacciona sobre sus ofertas.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AccountEventType(StrEnum):
    UPDATED = "account.updated"
    DELETED = "account.deleted"


class AccountEventResult(StrEnum):
    ARCHIVED = "archived"  # las ofertas de la empresa pasaron al archivo
    REGISTERED = "registered"  # se registró la baja (la cuenta no tenía ofertas)
    IGNORED = "ignored"  # nada que hacer (repetido, edición o tipo desconocido)


@dataclass(frozen=True)
class AccountEvent:
    event: str  # str y no enum: un tipo nuevo se ignora en vez de rechazarse
    user_id: str
    role: str
    deleted: bool
    occurred_at: datetime
