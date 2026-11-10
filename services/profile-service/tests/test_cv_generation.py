"""UT-PROF-06: CV "IA friendly" generado por reglas (documento, HTML, DOCX y PDF)."""

import copy
import io
from datetime import UTC, datetime

import pytest

from app.domain.auth import Principal
from app.domain.cv_document import CvDocument, CvDocumentBuilder, format_date, format_period
from app.domain.profile import StudentProfile
from app.infrastructure.container import Container
from app.infrastructure.renderers.docx import DocxCvRenderer
from app.infrastructure.renderers.html import HtmlCvRenderer
from tests.conftest import COMPLETE_PROFILE

NOW = datetime(2026, 11, 5, 12, tzinfo=UTC)


@pytest.fixture
def profile(container: Container, student: Principal) -> StudentProfile:
    data = copy.deepcopy(COMPLETE_PROFILE)
    data["experience"].append(
        {"company": "Agencia Ficticia", "role": "Pasante QA", "start": "2023-02", "end": "2024-01"}
    )
    data["projects"] = [
        {"name": "Bolsa demo", "description": "API en FastAPI", "url": "https://github.com/demo/x"}
    ]
    container.profiles.create_mine(student, data)
    found = container.repository.get_by_user(student.subject)
    assert found is not None
    return found


@pytest.fixture
def document(profile: StudentProfile) -> CvDocument:
    return CvDocumentBuilder().build(profile, NOW)


def test_ut_prof_06_formatea_fechas() -> None:
    assert format_date("2023-03") == "mar. 2023"
    assert format_date("actual") == "Actualidad"
    assert format_date("2021") == "2021"
    assert format_date("") == ""
    assert format_period("2023-03", "actual") == "mar. 2023 \u2013 Actualidad"
    assert format_period("2024", "2024") == "2024"
    assert format_period(None, "2020") == "2020"


def test_ut_prof_06_documento_ordenado_y_sin_datos_privados(document: CvDocument) -> None:
    assert document.full_name == "Lucía Fernández"
    assert document.file_stem == "CV_Lucia_Fernandez"
    assert [c.label for c in document.contact] == ["Email", "Teléfono", "Ubicación", "GitHub"]
    assert document.contact[2].value == "San Isidro, Buenos Aires, Argentina"
    assert document.contact[3].value == "github.com/lucia-ficticia"
    # Experiencia: la actual primero.
    assert [e.organization for e in document.experience] == ["FinTech Ficticia", "Agencia Ficticia"]
    assert document.experience[0].bullets == ("APIs REST con FastAPI", "Tests con Pytest")
    assert document.experience[0].period == "mar. 2025 \u2013 Actualidad"
    # Skills agrupadas por categoría y ordenadas por nivel.
    groups = {g.label: [s.name for s in g.skills] for g in document.skill_groups}
    assert groups["Técnicas"] == ["Python", "PostgreSQL"]
    assert "Git" in groups["Herramientas"]
    assert "Trabajo en equipo" in groups["Habilidades interpersonales"]
    assert document.languages[0].level_label == "Nativo"
    assert "4.º año" in document.education[0].details
    assert "Modalidad híbrida o remota" in document.availability
    text = repr(document)
    for private in ("600000", "2002", "Dato privado", "accessibility"):
        assert private not in text
    assert "Inglés" in document.keywords and "Desarrolladora backend" in document.keywords


def test_ut_prof_06_headline_alternativo(profile: StudentProfile) -> None:
    import dataclasses

    no_headline = dataclasses.replace(profile, headline=None)
    assert CvDocumentBuilder().build(no_headline, NOW).headline == "Desarrolladora backend"
    bare = dataclasses.replace(no_headline, target=None, education=())
    doc = CvDocumentBuilder().build(bare, NOW)
    assert doc.headline == "Estudiante de Ingeniería en Sistemas de Información"
    assert doc.education[0].title == "Ingeniería en Sistemas de Información"


def test_ut_prof_06_html_semantico_y_con_metadatos(document: CvDocument) -> None:
    html = HtmlCvRenderer().to_html(document)
    assert '<html lang="es">' in html
    assert '<meta name="keywords" content="Python' in html or "keywords" in html
    for heading in (
        "Perfil profesional",
        "Competencias",
        "Experiencia",
        "Proyectos",
        "Educación",
        "Idiomas",
        "Certificaciones",
    ):
        assert f"<h2>{heading}</h2>" in html
    assert "<table" not in html and "<img" not in html  # sin tablas ni imágenes (ATS)
    assert "letter-spacing: 0.12em" not in html
    # Competencias en texto plano separado por comas (sin chips ni barras de nivel).
    assert "<b>Técnicas:</b> Python (avanzado), PostgreSQL</p>" in html
    assert 'class="chip"' not in html and "(Intermedio)" not in html


def test_ut_prof_06_html_escapa_contenido(document: CvDocument) -> None:
    import dataclasses

    evil = dataclasses.replace(document, summary="<script>alert(1)</script>")
    assert "<script>alert" not in HtmlCvRenderer().to_html(evil)


def test_ut_prof_06_docx_con_estilos_nativos(document: CvDocument) -> None:
    from docx import Document

    rendered = DocxCvRenderer().render(document)
    assert rendered.extension == "docx"
    doc = Document(io.BytesIO(rendered.content))
    headings = [p.text for p in doc.paragraphs if p.style.name == "Heading 1"]
    assert headings[:3] == ["Perfil profesional", "Competencias", "Experiencia"]
    body = "\n".join(p.text for p in doc.paragraphs)
    assert "Lucía Fernández" in body and "Técnicas: Python (avanzado), PostgreSQL" in body
    assert doc.core_properties.author == "Lucía Fernández"
    assert "Python" in doc.core_properties.keywords
    assert not doc.tables


def test_ut_prof_06_pdf_con_texto_extraible(document: CvDocument) -> None:
    try:  # sin pango/harfbuzz (p. ej. runner de CI sin Docker) WeasyPrint tira OSError
        import weasyprint  # noqa: F401
    except (ImportError, OSError) as exc:
        pytest.skip(f"WeasyPrint no disponible: {exc}")
    from app.infrastructure.renderers.pdf import WeasyPrintCvRenderer

    rendered = WeasyPrintCvRenderer(HtmlCvRenderer()).render(document)
    assert rendered.content.startswith(b"%PDF")
    assert rendered.media_type == "application/pdf"
    assert len(rendered.content) > 5000
