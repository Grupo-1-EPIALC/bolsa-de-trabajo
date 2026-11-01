"""Adaptador de almacenamiento de CVs en disco con nombre aleatorio (AGENTS.md §4.2)."""

import tempfile
import uuid
from pathlib import Path


class FileSystemCvStorage:
    """Guarda los archivos de CV en CV_STORAGE_PATH con un nombre aleatorio UUID."""

    def __init__(self, base_path: str = "/data/cvs") -> None:
        self._base_path = Path(base_path)

    def save(self, extension: str, content: bytes) -> str:
        random_name = f"{uuid.uuid4().hex}.{extension}"
        target_dir = self._base_path
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / random_name
            target_file.write_bytes(content)
        except OSError:
            fallback_dir = Path(tempfile.gettempdir()) / "bolsa_cvs"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            (fallback_dir / random_name).write_bytes(content)
        return random_name
