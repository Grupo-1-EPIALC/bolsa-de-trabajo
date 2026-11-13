"""Tests unitarios de subida de CV (síncrona y asíncrona) y webhook n8n en profile-service."""

import json

import pytest

from app.application.upload_cv_use_case import UploadAndExtractCvUseCase
from app.domain.errors import CvJobNotFoundError, InvalidCvFileError, WebhookExtractionError
from app.domain.models import (
    MANUAL_COMPLETION_INDICATOR,
    CvExtractionResult,
    UploadedCvFile,
    normalize_cv_suggestions,
)


class FakeCvStorage:
    def __init__(self) -> None:
        self.saved: list[tuple[str, bytes]] = []

    def save(self, extension: str, content: bytes) -> str:
        self.saved.append((extension, content))
        return f"random-uuid.{extension}"


class FakeCvWebhookGateway:
    def __init__(self, should_fail: bool = False) -> None:
        self.calls: list[tuple[str, UploadedCvFile]] = []
        self._should_fail = should_fail

    def extract_cv_suggestions(
        self,
        profile_id: str,
        cv_file: UploadedCvFile,
    ) -> CvExtractionResult:
        self.calls.append((profile_id, cv_file))
        if self._should_fail:
            raise WebhookExtractionError("Fallo simulado en n8n", status_code=503)
        return CvExtractionResult(
            profile_id=profile_id,
            file={
                "filename": cv_file.original_filename,
                "stored_filename": cv_file.stored_filename,
                "format": cv_file.extension,
                "size_bytes": cv_file.size_bytes,
            },
            cv_suggestions={
                "skills": [{"name": "Python", "level_estimado": 4}],
                "experience": [{"role": "Backend Dev", "company": "TechSur", "years": 2}],
                "education": [],
                "languages": [{"language": "Español", "level": "Nativo"}],
            },
            origin="AI",
            model="nvidia/nemotron-3-ultra-550b-a55b",
            prompt_version="1.0.0",
            generated_at="2026-11-01T00:00:00Z",
            verified=True,
        )


def test_use_case_valid_markdown_cv() -> None:
    storage = FakeCvStorage()
    gateway = FakeCvWebhookGateway()
    use_case = UploadAndExtractCvUseCase(storage=storage, webhook_gateway=gateway, max_size_mb=5)

    res = use_case.execute(
        profile_id="prof-01",
        filename="mi_cv.md",
        content=b"# Ana Gomez\nPython developer",
        mime_type="text/markdown",
    )

    assert res.origin == "AI"
    assert res.profile_id == "prof-01"
    assert res.file["stored_filename"] == "random-uuid.md"
    assert res.cv_suggestions["skills"][0]["name"] == "Python"
    assert len(storage.saved) == 1
    assert len(gateway.calls) == 1


def test_use_case_async_job_lifecycle() -> None:
    storage = FakeCvStorage()
    gateway = FakeCvWebhookGateway()
    use_case = UploadAndExtractCvUseCase(storage=storage, webhook_gateway=gateway, max_size_mb=5)

    snap = use_case.start_async(
        profile_id="prof-async-01",
        filename="cv_ana.md",
        content=b"# Ana\nPython",
        mime_type="text/markdown",
        run_in_background=False,
    )
    assert snap["status"] == "completed"
    assert snap["progress_percent"] == 100
    assert snap["result"]["origin"] == "AI"

    polled = use_case.get_job_status(snap["job_id"])
    assert polled["status"] == "completed"
    assert polled["result"]["profile_id"] == "prof-async-01"

    with pytest.raises(CvJobNotFoundError):
        use_case.get_job_status("cvjob-inexistente")


def test_use_case_async_job_failure() -> None:
    use_case = UploadAndExtractCvUseCase(
        storage=FakeCvStorage(),
        webhook_gateway=FakeCvWebhookGateway(should_fail=True),
    )
    snap = use_case.start_async(
        profile_id="prof-err",
        filename="cv.md",
        content=b"# CV",
        run_in_background=False,
    )
    assert snap["status"] == "failed"
    assert snap["error"]["code"] == "CV_WEBHOOK_ERROR"


def test_use_case_rejects_invalid_extension() -> None:
    use_case = UploadAndExtractCvUseCase(
        storage=FakeCvStorage(),
        webhook_gateway=FakeCvWebhookGateway(),
    )
    with pytest.raises(InvalidCvFileError) as exc_info:
        use_case.execute(
            profile_id="prof-01",
            filename="script.exe",
            content=b"MZ...",
            mime_type="application/octet-stream",
        )
    assert exc_info.value.code == "INVALID_CV_FILE"


def test_use_case_rejects_invalid_mime() -> None:
    use_case = UploadAndExtractCvUseCase(
        storage=FakeCvStorage(),
        webhook_gateway=FakeCvWebhookGateway(),
    )
    with pytest.raises(InvalidCvFileError):
        use_case.execute(
            profile_id="prof-01",
            filename="cv.pdf",
            content=b"%PDF-1.4",
            mime_type="image/png",
        )


def test_use_case_rejects_empty_or_oversized_file() -> None:
    use_case = UploadAndExtractCvUseCase(
        storage=FakeCvStorage(),
        webhook_gateway=FakeCvWebhookGateway(),
        max_size_mb=1,
    )
    with pytest.raises(InvalidCvFileError):
        use_case.execute(profile_id="prof-01", filename="cv.pdf", content=b"")

    with pytest.raises(InvalidCvFileError):
        use_case.execute(
            profile_id="prof-01",
            filename="cv.pdf",
            content=b"x" * (1024 * 1024 + 10),
        )


def test_webhook_extraction_error_model() -> None:
    err = WebhookExtractionError("Fallo n8n", status_code=503, details={"step": "wf01"})
    assert err.code == "CV_WEBHOOK_ERROR"
    assert err.status_code == 503


def test_normalize_analogous_fields_and_no_nulls() -> None:
    raw = {
        "datos_personales": {"nombre": "Juan Pérez", "correo": None},
        "habilidades": [{"competencia": "Python", "nivel_estimado": None}, "Docker"],
        "experiencia_laboral": [{"empresa": "Acme", "puesto": "Dev"}],
        "estudios": [{"universidad": "UBA", "carrera": "Lic. en Ciencias de la Computación"}],
        "idiomas": [{"idioma": "Inglés", "nivel": None}],
    }
    norm = normalize_cv_suggestions(raw)

    assert norm["personal"]["name"] == "Juan Pérez"
    assert norm["personal"]["email"] == MANUAL_COMPLETION_INDICATOR
    assert norm["personal"]["phone"] == MANUAL_COMPLETION_INDICATOR
    assert norm["summary"] == MANUAL_COMPLETION_INDICATOR
    assert norm["skills"][0] == {"name": "Python", "level": MANUAL_COMPLETION_INDICATOR}
    assert norm["skills"][1] == {"name": "Docker", "level": MANUAL_COMPLETION_INDICATOR}
    assert norm["experience"][0]["company"] == "Acme"
    assert norm["experience"][0]["role"] == "Dev"
    assert norm["experience"][0]["start"] == MANUAL_COMPLETION_INDICATOR
    assert norm["education"][0]["institution"] == "UBA"
    assert norm["education"][0]["degree"] == "Lic. en Ciencias de la Computación"
    assert norm["education"][0]["status"] == MANUAL_COMPLETION_INDICATOR
    assert norm["languages"][0] == {"name": "Inglés", "level": MANUAL_COMPLETION_INDICATOR}
    assert norm["certifications"] == []
    assert norm["links"] == []
    assert "personal.email" in norm["pending_manual_fields"]
    assert "null" not in json.dumps(norm)
    assert norm["headline"] == MANUAL_COMPLETION_INDICATOR
    assert "headline" in norm["pending_manual_fields"]


def test_normalize_keeps_headline_and_its_source() -> None:
    from_cv = normalize_cv_suggestions({"headline": "Docente de Primaria", "headline_source": "cv"})
    assert (from_cv["headline"], from_cv["headline_source"]) == ("Docente de Primaria", "cv")

    suggested = normalize_cv_suggestions(
        {"titular": "Profesorado de Primaria · Tutorías", "headline_source": "suggested"}
    )
    assert suggested["headline"] == "Profesorado de Primaria · Tutorías"
    assert suggested["headline_source"] == "suggested"
    # Un origen desconocido no se trata como "del CV": se revisa como sugerido.
    assert normalize_cv_suggestions({"headline": "X", "headline_source": "?"})[
        "headline_source"
    ] == ("suggested")
