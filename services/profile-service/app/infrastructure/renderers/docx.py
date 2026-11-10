"""CV en DOCX con python-docx.

Mismo contenido y orden que el PDF, con estilos nativos de Word (Título, Encabezado 1,
Viñetas) en lugar de tablas o cuadros de texto: así lo leen bien los ATS y se puede editar.
"""

import io
from collections.abc import Callable, Sequence
from typing import Any

from docx import Document
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

from app.domain.cv_design import CvSection
from app.domain.cv_document import CvDocument, Entry
from app.domain.ports import RenderedFile

# Misma paleta que el PDF: texto casi negro y un solo acento azul marino.
INK = RGBColor(0x11, 0x18, 0x27)
TEXT = RGBColor(0x1F, 0x29, 0x37)
MUTED = RGBColor(0x4B, 0x55, 0x63)
ACCENT = RGBColor(0x1F, 0x3A, 0x5F)
FONT = "Calibri"
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class DocxCvRenderer:
    format = "docx"

    def render(self, document: CvDocument) -> RenderedFile:
        doc = Document()
        self._setup(doc, document)
        self._header(doc, document)
        sections: dict[CvSection, Callable[[Any, CvDocument], None]] = {
            CvSection.SUMMARY: self._summary,
            CvSection.SKILLS: self._skills,
            CvSection.EXPERIENCE: lambda d, c: self._entries(d, "Experiencia", c.experience),
            CvSection.PROJECTS: lambda d, c: self._entries(d, "Proyectos", c.projects),
            CvSection.EDUCATION: lambda d, c: self._entries(d, "Educación", c.education),
            CvSection.LANGUAGES: self._languages,
            CvSection.CERTIFICATIONS: self._certifications,
            CvSection.VOLUNTEERING: lambda d, c: self._entries(d, "Voluntariado", c.volunteering),
        }
        # Una sola columna, en el orden que decidió el diseño (app/domain/cv_design.py).
        for section in document.sections:
            sections[section](doc, document)

        buffer = io.BytesIO()
        doc.save(buffer)
        return RenderedFile(buffer.getvalue(), DOCX_MEDIA_TYPE, "docx")

    # ------------------------------------------------------------------ secciones ---

    def _summary(self, doc: Any, document: CvDocument) -> None:
        if not document.summary:
            return
        self._heading(doc, "Perfil profesional")
        self._paragraph(doc, document.summary)
        if document.availability:
            p = self._paragraph(doc, "")
            self._run(p, "Disponibilidad: ", bold=True, color=INK)
            self._run(p, document.availability)

    def _skills(self, doc: Any, document: CvDocument) -> None:
        if not document.skill_groups:
            return
        self._heading(doc, "Competencias")
        for group in document.skill_groups:
            p = self._paragraph(doc, "")
            self._run(p, f"{group.label}: ", bold=True, color=INK)
            self._run(p, group.line)

    def _entries(self, doc: Any, title: str, items: Sequence[Entry]) -> None:
        if not items:
            return
        self._heading(doc, title)
        for entry in items:
            self._entry(doc, entry)

    def _languages(self, doc: Any, document: CvDocument) -> None:
        if not document.languages:
            return
        self._heading(doc, "Idiomas")
        for lang in document.languages:
            p = self._paragraph(doc, "")
            self._run(p, lang.name, bold=True, color=INK)
            extra = f" ({lang.certification})" if lang.certification else ""
            self._run(p, f" — {lang.level_label}{extra}")

    def _certifications(self, doc: Any, document: CvDocument) -> None:
        if not document.certifications:
            return
        self._heading(doc, "Certificaciones")
        for cert in document.certifications:
            p = self._paragraph(doc, "")
            self._run(p, cert.name, bold=True, color=INK)
            if cert.detail:
                self._run(p, f" · {cert.detail}", color=MUTED)

    # ------------------------------------------------------------------ bloques ---

    @staticmethod
    def _setup(doc: Any, document: CvDocument) -> None:
        d = doc
        section = d.sections[0]
        section.page_height, section.page_width = Mm(297), Mm(210)
        section.top_margin = section.bottom_margin = Mm(15)
        section.left_margin = section.right_margin = Mm(17)
        normal = d.styles["Normal"]
        normal.font.name = FONT
        normal.font.size = Pt(10)
        normal.font.color.rgb = TEXT
        normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        normal.paragraph_format.space_after = Pt(2)
        heading = d.styles["Heading 1"]
        heading.font.name = FONT
        heading.font.size = Pt(10.5)
        heading.font.bold = True
        heading.font.all_caps = True
        heading.font.color.rgb = ACCENT
        heading.paragraph_format.space_before = Pt(10)
        heading.paragraph_format.space_after = Pt(4)
        props = d.core_properties
        props.title = f"{document.full_name} · CV"
        props.author = document.full_name
        props.subject = document.headline
        props.keywords = ", ".join(document.keywords)
        props.comments = f"Generado por Bolsa de Trabajo (plantilla {document.template_version})"
        props.language = "es-AR"

    def _header(self, doc: Any, document: CvDocument) -> None:
        name = doc.add_paragraph(style="Title")
        self._run(name, document.full_name, bold=True, color=INK, size=24)
        name.paragraph_format.space_after = Pt(0)
        if document.headline:
            p = self._paragraph(doc, "")
            self._run(p, document.headline, bold=True, color=TEXT, size=11)
        if document.contact:
            p = self._paragraph(doc, "")
            for i, item in enumerate(document.contact):
                if i:
                    self._run(p, "  ·  ", color=MUTED, size=9)
                self._run(p, f"{item.label}: ", bold=True, color=INK, size=9)
                self._run(p, item.value, color=TEXT, size=9)

    def _entry(self, doc: Any, entry: Entry) -> None:
        p = self._paragraph(doc, "")
        p.paragraph_format.tab_stops.add_tab_stop(Mm(176), WD_TAB_ALIGNMENT.RIGHT)
        p.paragraph_format.space_before = Pt(4)
        self._run(p, entry.title, bold=True, color=INK)
        if entry.organization:
            self._run(p, f" · {entry.organization}")
        if entry.period:
            self._run(p, f"\t{entry.period}", color=MUTED, size=9)
        if entry.details:
            self._run(self._paragraph(doc, ""), entry.details, color=MUTED, size=9)
        for bullet in entry.bullets:
            doc.add_paragraph(bullet, style="List Bullet")
        if entry.tags:
            p = self._paragraph(doc, "")
            self._run(p, "Tecnologías: ", bold=True, size=9)
            self._run(p, ", ".join(entry.tags), color=MUTED, size=9)
        if entry.url:
            self._run(self._paragraph(doc, ""), entry.url, color=ACCENT, size=9)

    @staticmethod
    def _heading(doc: Any, text: str) -> None:
        doc.add_heading(text, level=1)

    @staticmethod
    def _paragraph(doc: Any, text: str) -> Any:
        return doc.add_paragraph(text)

    @staticmethod
    def _run(
        paragraph: Any,
        text: str,
        *,
        bold: bool = False,
        color: RGBColor | None = None,
        size: float | None = None,
    ) -> None:
        run = paragraph.add_run(text)
        run.bold = bold
        run.font.name = FONT
        if color is not None:
            run.font.color.rgb = color
        if size is not None:
            run.font.size = Pt(size)
