"""Identidad de quien llama a jobs-service (sin dependencias de frameworks)."""

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    STUDENT = "student"
    COMPANY = "company"
    ADMIN = "admin"
    SERVICE = "service"  # n8n / mcp-tools / matching con X-Service-Token


USER_ROLES = frozenset({Role.STUDENT, Role.COMPANY, Role.ADMIN})


@dataclass(frozen=True)
class Principal:
    """Usuario o servicio autenticado.

    `access_token` sólo se guarda para las peticiones de usuario: la creación de una oferta
    necesita consultar el perfil de la empresa en auth-service con el Bearer original.
    """

    subject: str
    role: Role
    access_token: str | None = None

    @property
    def is_service(self) -> bool:
        return self.role is Role.SERVICE

    @property
    def sees_everything(self) -> bool:
        return self.role in (Role.ADMIN, Role.SERVICE)


SERVICE_PRINCIPAL = Principal(subject="service", role=Role.SERVICE)
