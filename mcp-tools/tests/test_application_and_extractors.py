"""Tests unitarios de `CvParserService`, extractores de texto y `VerificationService`."""

import base64
import io
import json

import pytest
from docx import Document
from pypdf import PdfWriter

from app.application.cv_parser import CvParserService
from app.application.use_cases import VerificationService
from app.domain.errors import InvalidInputError, SchemaNotFoundError, UnsupportedFormatError
from app.infrastructure.extractors import (
    DocTextExtractor,
    DocxTextExtractor,
    MarkdownTextExtractor,
    PdfTextExtractor,
    default_extractors,
)
from app.infrastructure.schemas_json import JsonSchemaValidator
from app.infrastructure.settings_env import EnvSettingsProvider


def _make_docx_bytes(paragraph_text: str, table_cell: str = "Python | Nivel 4") -> bytes:
    doc = Document()
    doc.add_paragraph(paragraph_text)
    table = doc.add_table(rows=1, cols=1)
    table.rows[0].cells[0].text = table_cell
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_blank_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_cv_parser_markdown_and_truncation() -> None:
    provider = EnvSettingsProvider({"CV_MAX_TEXT_CHARS": "25", "CV_MAX_SIZE_MB": "1"})
    parser = CvParserService(provider, default_extractors())
    raw = "# Valentina Gómez\nDesarrolladora Python y FastAPI"
    b64 = "data:text/markdown;base64," + base64.b64encode(raw.encode("utf-8")).decode("ascii")

    res = await parser.parse_base64(b64, filename="cv_valentina.md")
    assert res["format"] == "md"
    assert res["truncated"] is True
    assert len(res["text"]) == 25
    assert res["chars"] == len(raw)


@pytest.mark.asyncio
async def test_cv_parser_docx_pdf_and_doc_fallback() -> None:
    provider = EnvSettingsProvider()
    parser = CvParserService(provider, default_extractors())

    docx_bytes = _make_docx_bytes("Experiencia en FastAPI y PostgreSQL")
    docx_res = await parser.parse_base64(
        base64.b64encode(docx_bytes).decode("ascii"),
        filename="cv.docx",
    )
    assert docx_res["format"] == "docx"
    assert "FastAPI" in docx_res["text"]
    assert "Python" in docx_res["text"]

    pdf_bytes = _make_blank_pdf_bytes()
    pdf_res = await parser.parse_base64(
        base64.b64encode(pdf_bytes).decode("ascii"),
        filename="cv.pdf",
    )
    assert pdf_res["format"] == "pdf"

    # Cabecera OLE2 (.doc) + texto embebido para ejercitar DocTextExtractor
    ole_doc = (
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 16 + b"Ingenieria en Sistemas Python SQL"
    )
    doc_res = await parser.parse_base64(
        base64.b64encode(ole_doc).decode("ascii"),
        filename="legacy.doc",
    )
    assert doc_res["format"] == "doc"
    assert "Ingenieria en Sistemas" in doc_res["text"]


@pytest.mark.asyncio
async def test_cv_parser_rejects_invalid_inputs() -> None:
    provider = EnvSettingsProvider({"CV_MAX_SIZE_MB": "0.00001", "CV_ALLOWED_EXTENSIONS": "pdf"})
    parser = CvParserService(
        provider,
        [PdfTextExtractor(), DocxTextExtractor(), DocTextExtractor(), MarkdownTextExtractor()],
    )

    with pytest.raises(InvalidInputError, match="obligatorio"):
        await parser.parse_base64("   ", "cv.pdf")

    with pytest.raises(InvalidInputError, match="base64 inválido"):
        await parser.parse_base64("%%%no-es-base64%%%", "cv.pdf")

    big_b64 = base64.b64encode(b"x" * 200).decode("ascii")
    with pytest.raises(InvalidInputError, match="supera el máximo"):
        await parser.parse_base64(big_b64, "cv.pdf")

    provider2 = EnvSettingsProvider({"CV_ALLOWED_EXTENSIONS": "pdf"})
    parser2 = CvParserService(provider2, default_extractors())
    md_b64 = base64.b64encode(b"Hola mundo").decode("ascii")
    with pytest.raises(UnsupportedFormatError, match="no habilitado"):
        await parser2.parse_base64(md_b64, "cv.md")


def test_cv_standard_headline_from_cv_or_suggested() -> None:
    verifier = VerificationService(JsonSchemaValidator())
    base = {
        "personal": {
            "name": "Ana Ficticia",
            "email": "COMPLETAR_MANUALMENTE",
            "phone": "COMPLETAR_MANUALMENTE",
            "location": "Córdoba",
        },
        "summary": "Estudiante de Contador Público",
        "skills": [],
        "experience": [],
        "education": [],
        "languages": [],
        "certifications": [],
        "links": [],
    }
    suggested = {
        **base,
        "headline": "Estudiante de Contador Público · Administración",
        "headline_source": "suggested",
    }
    assert verifier.validate_json("cv_standard", json.dumps(suggested))["valid"] is True
    # Sigue siendo opcional: una respuesta sin título también es válida.
    assert verifier.validate_json("cv_standard", json.dumps(base))["valid"] is True

    bad_source = {**suggested, "headline_source": "inventado"}
    assert verifier.validate_json("cv_standard", json.dumps(bad_source))["valid"] is False
    too_long = {**suggested, "headline": "x" * 141}
    assert verifier.validate_json("cv_standard", json.dumps(too_long))["valid"] is False


def test_verification_service_schemas_and_grounding() -> None:
    verifier = VerificationService(JsonSchemaValidator())

    valid_cv = {
        "personal": {
            "name": "Valentina Gómez",
            "email": "valentina@example.com",
            "phone": "COMPLETAR_MANUALMENTE",
            "location": "CABA",
        },
        "summary": "Estudiante de Ingeniería",
        "skills": [{"name": "Python", "level": 4}],
        "experience": [],
        "education": [],
        "languages": [{"name": "Inglés", "level": "B2"}],
        "certifications": [],
        "links": [],
        "pending_manual_fields": ["personal.phone"],
        "origin": "AI",
        "model": "deepseek-ai/deepseek-v4.1-flash",
        "prompt_version": "1.0.0",
        "generated_at": "2026-10-31T12:00:00Z",
        "disclaimer": "Sugerencia IA",
    }
    res = verifier.validate_json("cv_standard", json.dumps(valid_cv))
    assert res["valid"] is True
    assert res["errors"] == []

    bad_res = verifier.validate_json("cv_standard", '{"personal": {}}')
    assert bad_res["valid"] is False
    assert len(bad_res["errors"]) > 0

    syntax_res = verifier.validate_json("cv_standard", "{malformed")
    assert syntax_res["valid"] is False

    with pytest.raises(SchemaNotFoundError):
        verifier.validate_json("non_existent_schema", "{}")

    g_ok = verifier.check_grounding(
        terms=["Python", "FastAPI"],
        source_text="Desarrollo con Python y FastAPI.",
        expected_score=82.5,
        reported_score=82.5,
    )
    assert g_ok["grounded"] is True
    assert g_ok["score_tampered"] is False

    g_tampered = verifier.check_grounding(
        terms=["Python"],
        source_text="Desarrollo con Python.",
        expected_score=82.5,
        reported_score=90.0,
    )
    assert g_tampered["grounded"] is False
    assert g_tampered["score_tampered"] is True


async def test_ut_mcp_03_env_notification_settings() -> None:
    cfg = await EnvSettingsProvider(
        {
            "NOTIFY_ENABLED": "false",
            "NOTIFY_MIN_SCORE": "65",
            "NOTIFY_MAX_PER_EVENT": "3",
            "NOTIFY_ADMIN_EMAIL": " admin@bolsa.local ",
            "FRONTEND_URL": "http://localhost:8080/",
        }
    ).get()
    assert cfg.notifications.enabled is False
    assert cfg.notifications.min_score == 65
    assert cfg.notifications.max_per_event == 3
    assert cfg.notifications.admin_email == "admin@bolsa.local"
    assert cfg.notifications.frontend_url == "http://localhost:8080"
    defaults = await EnvSettingsProvider({}).get()
    assert defaults.notifications.enabled is True
    assert defaults.notifications.min_score == 70
