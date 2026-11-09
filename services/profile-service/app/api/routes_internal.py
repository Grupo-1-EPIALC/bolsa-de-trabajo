"""Endpoints internos (sólo `X-Service-Token`; el gateway borra ese header en lo externo)."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import ContainerDep, PrincipalDep
from app.domain.account_events import AccountEvent
from app.domain.company import CompanyLegal

router = APIRouter(prefix="/api/v1/profiles/internal", tags=["internal"])


class AccountEventCompanyIn(BaseModel):
    legal_name: str = Field(max_length=200)
    cuit: str = Field(max_length=11)
    activity: str = Field(max_length=160)


class AccountEventIn(BaseModel):
    """Cuerpo de `contracts/auth.md` (parte B) (los campos extra se ignoran)."""

    event: str = Field(max_length=64)
    user_id: str = Field(min_length=1, max_length=64)
    role: str = Field(max_length=16)
    deleted: bool = False
    occurred_at: datetime
    company: AccountEventCompanyIn | None = None

    def to_domain(self) -> AccountEvent:
        company = (
            CompanyLegal(self.company.legal_name, self.company.cuit, self.company.activity)
            if self.company
            else None
        )
        return AccountEvent(
            event=self.event,
            user_id=self.user_id,
            role=self.role,
            deleted=self.deleted,
            occurred_at=self.occurred_at,
            company=company,
        )


@router.post(
    "/account-events",
    summary="[interno] Evento de cuenta de auth-service (borrado o edición). Idempotente",
)
def receive_account_event(
    body: AccountEventIn, principal: PrincipalDep, container: ContainerDep
) -> dict[str, Any]:
    return container.account_events.handle(principal, body.to_domain())
