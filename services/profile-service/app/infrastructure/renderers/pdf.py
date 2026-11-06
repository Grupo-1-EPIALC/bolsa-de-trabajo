"""CV en PDF: el HTML de Jinja2 impreso con WeasyPrint (texto seleccionable + metadatos).

WeasyPrint se importa al renderizar: necesita las librerías de sistema que instala el
Dockerfile (pango, harfbuzz, fontconfig).
"""

from app.domain.cv_document import CvDocument
from app.domain.ports import RenderedFile
from app.infrastructure.renderers.html import HtmlCvRenderer


class WeasyPrintCvRenderer:
    format = "pdf"

    def __init__(self, html: HtmlCvRenderer) -> None:
        self._html = html

    def render(self, document: CvDocument) -> RenderedFile:
        from weasyprint import HTML  # import diferido: libs de sistema

        content = HTML(
            string=self._html.to_html(document), base_url=str(self._html.templates_dir)
        ).write_pdf(pdf_variant="pdf/ua-1")
        return RenderedFile(bytes(content), "application/pdf", "pdf")
