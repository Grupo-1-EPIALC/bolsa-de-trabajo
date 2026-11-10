"""CV en HTML con Jinja2 (`app/templates/cv.html`). Es la base del PDF y sirve de vista previa."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.domain.cv_document import CvDocument
from app.domain.ports import RenderedFile

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
# Un solo acento sobrio (azul marino, contraste 11:1 sobre blanco) para títulos y líneas.
DEFAULT_ACCENT = "#1f3a5f"


class HtmlCvRenderer:
    format = "html"

    def __init__(
        self,
        templates_dir: Path = TEMPLATES_DIR,
        accent: str = DEFAULT_ACCENT,
    ) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._accent = accent
        self.templates_dir = templates_dir

    def to_html(self, document: CvDocument) -> str:
        template = self._env.get_template("cv.html")
        return template.render(doc=document, accent=self._accent)

    def render(self, document: CvDocument) -> RenderedFile:
        return RenderedFile(
            self.to_html(document).encode("utf-8"), "text/html; charset=utf-8", "html"
        )
