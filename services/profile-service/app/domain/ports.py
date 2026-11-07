"""Puertos (Protocols) de profile-service (DIP · AGENTS.md §2.1 y §4.2)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.auth import Principal
from app.domain.company import CompanyLegal, CompanyProfile
from app.domain.cv_document import CvDocument
from app.domain.models import CvExtractionResult, UploadedCvFile
from app.domain.profile import StudentProfile


class CvStoragePort(Protocol):
    """Puerto para almacenar el archivo de CV con nombre aleatorio en CV_STORAGE_PATH."""

    def save(self, extension: str, content: bytes) -> str:
        """Guarda los bytes del CV con nombre aleatorio y devuelve el nombre almacenado."""


class CvWebhookGateway(Protocol):
    """Puerto para enviar el CV al webhook de n8n (`POST /webhook/cv-extract`)."""

    def extract_cv_suggestions(
        self,
        profile_id: str,
        cv_file: UploadedCvFile,
    ) -> CvExtractionResult:
        """Envía el CV al webhook de n8n y devuelve sugerencias estructuradas (`origin='AI'`)."""


class ProfileRepository(Protocol):
    def add(self, profile: StudentProfile) -> None: ...

    def update(self, profile: StudentProfile) -> None: ...

    def get(self, profile_id: str) -> StudentProfile | None: ...

    def get_by_user(self, user_id: str) -> StudentProfile | None: ...

    def list(self, *, offset: int, limit: int) -> tuple[list[StudentProfile], int]: ...

    def archive(self, profile_id: str, deleted_at: datetime) -> bool:
        """Mueve el perfil al archivo de cuentas borradas. False si ya no estaba."""


class EventPublisher(Protocol):
    """Avisa a n8n que el perfil cambió (`profile.updated`). Best-effort."""

    def profile_updated(self, profile: StudentProfile) -> None: ...


class AccountDirectory(Protocol):
    """Datos de la cuenta en auth-service (sólo lectura, con el Bearer del usuario)."""

    def email_of(self, principal: Principal) -> str | None: ...

    def company_of(self, principal: Principal) -> CompanyLegal | None:
        """Razón social, CUIT y actividad de la empresa (None si no es empresa)."""


class CompanyProfileRepository(Protocol):
    def add(self, profile: CompanyProfile) -> None: ...

    def update(self, profile: CompanyProfile) -> None: ...

    def get_by_company(self, company_id: str) -> CompanyProfile | None: ...

    def list(self, *, offset: int, limit: int) -> tuple[list[CompanyProfile], int]: ...

    def archive(self, company_id: str, deleted_at: datetime) -> bool:
        """Mueve el perfil de empresa al archivo de cuentas borradas. False si ya no estaba."""


class DeletedAccounts(Protocol):
    """Cuentas dadas de baja en auth-service (soft delete), aunque no tuvieran perfil."""

    def mark(self, user_id: str, role: str, deleted_at: datetime) -> bool:
        """Registra la baja. False si ya estaba registrada (evento repetido)."""

    def contains(self, user_id: str) -> bool: ...


@dataclass(frozen=True)
class StoredLogo:
    mime_type: str
    content: bytes


class LogoStore(Protocol):
    def save(self, company_id: str, logo: StoredLogo) -> None: ...

    def get(self, company_id: str) -> StoredLogo | None: ...

    def delete(self, company_id: str) -> None: ...


class TokenVerifier(Protocol):
    def verify(self, token: str) -> Principal: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_profile_id(self) -> str: ...

    def new_company_id(self) -> str: ...


@dataclass(frozen=True)
class RenderedFile:
    content: bytes
    media_type: str
    extension: str


class CvRenderer(Protocol):
    """Convierte el `CvDocument` (armado por reglas) en un archivo descargable."""

    @property
    def format(self) -> str: ...

    def render(self, document: CvDocument) -> RenderedFile: ...
