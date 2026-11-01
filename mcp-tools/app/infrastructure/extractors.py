"""Extractores de texto por formato de archivo (PDF, DOCX, DOC binario, Markdown/Texto)."""

import io
import re
import shutil
import subprocess
from typing import Any

from app.domain.errors import InvalidInputError
from app.domain.ports import TextExtractor


def _decode_text_bytes(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


class PdfTextExtractor:
    """Extrae texto de documentos PDF usando `pypdf`."""

    format_name = "pdf"

    def extract(self, content: bytes) -> str:
        from pypdf import PdfReader

        try:
            reader = PdfReader(io.BytesIO(content))
            pages: list[str] = []
            for idx, page in enumerate(reader.pages, start=1):
                page_text = (page.extract_text() or "").strip()
                if page_text:
                    pages.append(f"--- Página {idx} ---\n{page_text}")
            return "\n\n".join(pages)
        except Exception as exc:
            raise InvalidInputError(f"No se pudo leer el archivo PDF: {exc}") from exc


class DocxTextExtractor:
    """Extrae párrafos y tablas de documentos Word `.docx`."""

    format_name = "docx"

    def extract(self, content: bytes) -> str:
        from docx import Document

        try:
            doc: Any = Document(io.BytesIO(content))
            parts: list[str] = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
                    if cells:
                        parts.append(" | ".join(cells))
            return "\n".join(parts)
        except Exception as exc:
            raise InvalidInputError(f"No se pudo leer el archivo DOCX: {exc}") from exc


class DocTextExtractor:
    """Extrae texto de Word 97-2003 (`.doc`) con `antiword` o fallback de cadenas legibles."""

    format_name = "doc"

    def extract(self, content: bytes) -> str:
        antiword_bin = shutil.which("antiword")
        if antiword_bin:
            try:
                proc = subprocess.run(  # noqa: S603
                    [antiword_bin, "-"],
                    input=content,
                    capture_output=True,
                    timeout=15,
                    check=False,
                )
                if proc.returncode == 0 and proc.stdout:
                    text = _decode_text_bytes(proc.stdout).strip()
                    if text:
                        return text
            except (OSError, subprocess.SubprocessError):
                pass

        # Fallback determinístico cuando el contenedor/entorno no tiene antiword o es un .doc simple
        text = self._extract_printable_strings(content)
        if not text:
            raise InvalidInputError("No se pudo extraer texto legible del archivo .doc")
        return text

    @staticmethod
    def _extract_printable_strings(content: bytes) -> str:
        decoded = content.decode("latin-1", errors="ignore")
        chunks = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü0-9@.,:;()/\-+_\s]{6,}", decoded)
        cleaned = [re.sub(r"\s+", " ", c).strip() for c in chunks]
        filtered = [c for c in cleaned if len(c) >= 6 and any(ch.isalpha() for ch in c)]
        return "\n".join(filtered)


class MarkdownTextExtractor:
    """Extrae texto de archivos Markdown o texto plano (`.md` / `.txt`)."""

    format_name = "md"

    def extract(self, content: bytes) -> str:
        return _decode_text_bytes(content).strip()


def default_extractors() -> list[TextExtractor]:
    return [
        PdfTextExtractor(),
        DocxTextExtractor(),
        DocTextExtractor(),
        MarkdownTextExtractor(),
    ]
