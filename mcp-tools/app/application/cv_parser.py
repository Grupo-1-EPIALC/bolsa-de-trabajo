"""Caso de uso de extracción de texto desde archivos de CV (PDF, DOCX, DOC, MD).

Abierto a extensión (OCP): recibe un diccionario/secuencia de `TextExtractor` registrados por
formato. Agregar un nuevo formato sólo requiere inyectar otro `TextExtractor`.
"""

import base64
import binascii
from collections.abc import Iterable

from app.domain.errors import InvalidInputError, UnsupportedFormatError
from app.domain.ports import JsonDict, SettingsProvider, TextExtractor

_MIME_TO_FORMAT: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "doc",
    "text/markdown": "md",
    "text/plain": "md",
}

_EXT_ALIASES: dict[str, str] = {
    "pdf": "pdf",
    "docx": "docx",
    "doc": "doc",
    "md": "md",
    "markdown": "md",
    "txt": "md",
}


class CvParserService:
    """Valida tamaño/formato y extrae texto plano de un CV codificado en base64."""

    def __init__(
        self,
        settings_provider: SettingsProvider,
        extractors: Iterable[TextExtractor],
    ) -> None:
        self._settings = settings_provider
        self._extractors: dict[str, TextExtractor] = {e.format_name: e for e in extractors}

    async def parse_base64(
        self,
        content_base64: str,
        filename: str,
        mime_type: str = "",
    ) -> JsonDict:
        settings = await self._settings.get()
        cv_cfg = settings.cv

        raw_bytes = self._decode_base64(content_base64)
        if not raw_bytes:
            raise InvalidInputError("El archivo de CV está vacío")
        if len(raw_bytes) > cv_cfg.max_size_bytes:
            raise InvalidInputError(
                f"El archivo supera el máximo permitido de {cv_cfg.max_size_mb} MB",
                {"size_bytes": len(raw_bytes), "max_size_bytes": cv_cfg.max_size_bytes},
            )

        fmt = self._detect_format(filename=filename, mime_type=mime_type, content=raw_bytes)
        if fmt not in cv_cfg.allowed_extensions:
            allowed_str = ", ".join(cv_cfg.allowed_extensions)
            raise UnsupportedFormatError(
                f"Formato '{fmt}' no habilitado. Permitidos: {allowed_str}",
                {"format": fmt, "allowed": list(cv_cfg.allowed_extensions)},
            )

        extractor = self._extractors.get(fmt)
        if extractor is None:
            raise UnsupportedFormatError(
                f"No hay extractor registrado para el formato '{fmt}'",
                {"format": fmt},
            )

        extracted = extractor.extract(raw_bytes).strip()
        total_chars = len(extracted)
        truncated = total_chars > cv_cfg.max_text_chars
        text = extracted[: cv_cfg.max_text_chars] if truncated else extracted

        return {
            "filename": filename or f"cv.{fmt}",
            "format": fmt,
            "chars": total_chars,
            "truncated": truncated,
            "text": text,
        }

    @staticmethod
    def _decode_base64(content_base64: str) -> bytes:
        cleaned = content_base64.strip()
        if not cleaned:
            raise InvalidInputError("El contenido base64 es obligatorio")
        if cleaned.startswith("data:") and "," in cleaned:
            cleaned = cleaned.split(",", 1)[1]
        try:
            return base64.b64decode(cleaned, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise InvalidInputError(f"Contenido base64 inválido: {exc}") from exc

    @staticmethod
    def _detect_format(filename: str, mime_type: str, content: bytes) -> str:
        ext = filename.lower().rsplit(".", 1)[-1].strip() if "." in filename else ""
        norm_mime = mime_type.split(";", 1)[0].strip().lower()

        if content.startswith(b"%PDF-"):
            return "pdf"
        if content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            return "doc"
        if content.startswith(b"PK\x03\x04") and (ext == "docx" or "wordprocessingml" in norm_mime):
            return "docx"
        if ext in _EXT_ALIASES:
            return _EXT_ALIASES[ext]
        if norm_mime in _MIME_TO_FORMAT:
            return _MIME_TO_FORMAT[norm_mime]
        raise UnsupportedFormatError(
            f"No se pudo determinar el formato de '{filename or 'archivo'}'",
            {"filename": filename, "mime_type": mime_type},
        )
