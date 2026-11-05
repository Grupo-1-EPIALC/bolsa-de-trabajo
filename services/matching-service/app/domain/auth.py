"""Identidad de quien llama al servicio (sin dependencias de frameworks ni de JWT)."""

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    STUDENT = "student"
    COMPANY = "company"
    ADMIN = "admin"
    SERVICE = "service"  # n8n / mcp-tools con X-Service-Token (red interna)


USER_ROLES = frozenset({Role.STUDENT, Role.COMPANY, Role.ADMIN})


@dataclass(frozen=True)
class Principal:
    subject: str  # `sub` del JWT (UUID del usuario) o "service"
    role: Role

    @property
    def is_service(self) -> bool:
        return self.role is Role.SERVICE

    @property
    def sees_everything(self) -> bool:
        return self.role in (Role.SERVICE, Role.ADMIN)


SERVICE_PRINCIPAL = Principal(subject="service", role=Role.SERVICE)
