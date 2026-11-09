"""Eventos de cuenta que publica auth-service (`contracts/auth.md` (parte B)).

auth-service es el dueño de las cuentas: profile-service sólo reacciona sobre sus propios datos.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.domain.company import CompanyLegal


class AccountEventType(StrEnum):
    UPDATED = "account.updated"
    DELETED = "account.deleted"


class AccountEventResult(StrEnum):
    ARCHIVED = "archived"  # el perfil pasó al archivo de cuentas borradas
    UPDATED = "updated"  # se actualizó la copia de los datos de la cuenta
    IGNORED = "ignored"  # nada que hacer (evento repetido, sin perfil o tipo desconocido)


@dataclass(frozen=True)
class AccountEvent:
    event: str  # str y no enum: un tipo nuevo se ignora en vez de rechazarse
    user_id: str
    role: str
    deleted: bool
    occurred_at: datetime
    company: CompanyLegal | None = None
