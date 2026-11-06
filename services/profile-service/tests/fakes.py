"""Dobles de prueba para los puertos de profile-service (datos 100 % ficticios)."""

from datetime import UTC, datetime
from typing import Any

from app.domain.auth import Principal
from app.domain.company import CompanyLegal
from app.domain.models import CvExtractionResult, UploadedCvFile
from app.domain.profile import StudentProfile

CV_SUGGESTIONS: dict[str, Any] = {
    "personal": {
        "name": "Lucía Fernández",
        "email": "COMPLETAR_MANUALMENTE",
        "phone": "COMPLETAR_MANUALMENTE",
        "location": "San Isidro, Buenos Aires, Argentina",
    },
    "summary": "Desarrolladora backend con Python, FastAPI y Docker. Trabajo con Postgres y Git.",
    "skills": [
        {"name": "python3", "level": 4},
        {"name": "FastAPI", "level": 3},
        {"name": "Docker", "level": "COMPLETAR_MANUALMENTE"},
    ],
    "experience": [
        {
            "company": "FinTech Ficticia",
            "role": "Desarrolladora Backend",
            "start": "03/2024",
            "end": "Presente",
            "description": "- Microservicios REST con FastAPI y PostgreSQL\n- Tests con Pytest",
        }
    ],
    "education": [
        {
            "institution": "Universidad Tecnológica Nacional",
            "degree": "Ingeniería en Sistemas de Información",
            "status": "En curso",
            "start": "COMPLETAR_MANUALMENTE",
            "end": "COMPLETAR_MANUALMENTE",
        }
    ],
    "languages": [
        {"name": "Inglés", "level": "Intermedio B2"},
        {"name": "Español", "level": "Nativo"},
    ],
    "certifications": ["Curso de Docker Ficticio"],
    "links": ["https://github.com/lucia-ficticia"],
}


class FakeCvWebhookGateway:
    def __init__(self, should_fail: bool = False, suggestions: dict[str, Any] | None = None):
        self.calls: list[tuple[str, UploadedCvFile]] = []
        self._should_fail = should_fail
        self._suggestions = suggestions if suggestions is not None else CV_SUGGESTIONS

    def extract_cv_suggestions(
        self, profile_id: str, cv_file: UploadedCvFile
    ) -> CvExtractionResult:
        from app.domain.errors import WebhookExtractionError

        self.calls.append((profile_id, cv_file))
        if self._should_fail:
            raise WebhookExtractionError("Fallo simulado en n8n", status_code=503)
        return CvExtractionResult(
            profile_id=profile_id,
            file={"filename": cv_file.original_filename, "format": cv_file.extension},
            cv_suggestions=self._suggestions,
            model="nvidia/modelo-ficticio",
            prompt_version="1.1.0",
            generated_at="2026-11-05T12:00:00+00:00",
        )


class RecordingPublisher:
    def __init__(self, fail: bool = False) -> None:
        self.events: list[StudentProfile] = []
        self._fail = fail

    def profile_updated(self, profile: StudentProfile) -> None:
        if self._fail:
            raise RuntimeError("n8n caído")
        self.events.append(profile)


class FakeAccounts:
    def __init__(
        self,
        email: str | None = "cuenta@example.com",
        fail: bool = False,
        legal: CompanyLegal | None = None,
    ) -> None:
        self._email = email
        self._fail = fail
        self._legal = legal or CompanyLegal(
            legal_name="Empresa Ficticia S.A.", cuit="30000000007", activity="software"
        )

    def email_of(self, principal: Principal) -> str | None:
        if self._fail:
            raise RuntimeError("auth-service caído")
        return self._email

    def company_of(self, principal: Principal) -> CompanyLegal | None:
        if self._fail:
            raise RuntimeError("auth-service caído")
        return self._legal if principal.role.value == "company" else None


class FixedClock:
    def __init__(self, now: datetime | None = None) -> None:
        self.current = now or datetime(2026, 11, 5, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current


class SequentialIds:
    def __init__(self) -> None:
        self._n = 0

    def new_profile_id(self) -> str:
        self._n += 1
        return f"prof-test-{self._n:03d}"

    def new_company_id(self) -> str:
        self._n += 1
        return f"comp-test-{self._n:03d}"
