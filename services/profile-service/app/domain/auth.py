"""Identidad de quien llama a profile-service (sin dependencias de frameworks)."""

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    STUDENT = "student"
    COMPANY = "company"
    ADMIN = "admin"
    SERVICE = "service"  # matching-service / mcp-tools / n8n con X-Service-Token


USER_ROLES = frozenset({Role.STUDENT, Role.COMPANY, Role.ADMIN})


@dataclass(frozen=True)
class Principal:
    """Usuario o servicio autenticado.

    `access_token` se guarda sólo para usuarios: al crear el perfil se consulta `/auth/me`
    con el Bearer original para precargar el email.
    """

    subject: str
    role: Role
    access_token: str | None = None

    @property
    def is_student(self) -> bool:
        return self.role is Role.STUDENT

    @property
    def sees_everything(self) -> bool:
        return self.role in (Role.ADMIN, Role.SERVICE)


SERVICE_PRINCIPAL = Principal(subject="service", role=Role.SERVICE)
