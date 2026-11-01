"""Caso de uso: subir CV, validar formato/tamaño, guardar y disparar webhook n8n."""

import base64
import threading
import time
import uuid
from pathlib import PurePath
from typing import Any

from app.domain.errors import CvJobNotFoundError, InvalidCvFileError, ProfileDomainError
from app.domain.models import (
    ALLOWED_CV_EXTENSIONS,
    ALLOWED_CV_MIMES,
    CvExtractionJobState,
    CvExtractionResult,
    UploadedCvFile,
)
from app.domain.ports import CvStoragePort, CvWebhookGateway


class CvExtractionJobStore:
    """Almacén en memoria thread-safe para seguimiento asíncrono de extracciones de CV."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, CvExtractionJobState] = {}

    def create(
        self,
        profile_id: str,
        filename: str,
        stored_filename: str,
    ) -> CvExtractionJobState:
        job_id = f"cvjob-{uuid.uuid4().hex[:12]}"
        state = CvExtractionJobState(
            job_id=job_id,
            profile_id=profile_id,
            filename=filename,
            stored_filename=stored_filename,
            status="processing",
            stage="Enviando CV al webhook de n8n (WF-01)...",
            started_monotonic=time.monotonic(),
        )
        with self._lock:
            self._jobs[job_id] = state
        return state

    def mark_completed(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.status = "completed"
                job.stage = "Extracción y verificación completadas"
                job.finished_monotonic = time.monotonic()
                job.result = result

    def mark_failed(self, job_id: str, error: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.status = "failed"
                job.stage = "Error en el procesamiento del CV"
                job.finished_monotonic = time.monotonic()
                job.error = error

    def get_snapshot(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise CvJobNotFoundError(job_id)
            end_t = (
                job.finished_monotonic if job.finished_monotonic is not None else time.monotonic()
            )
            elapsed = round(max(0.0, end_t - job.started_monotonic), 1)
            status = job.status
            result = job.result
            error = job.error
            profile_id = job.profile_id
            filename = job.filename
            stored_filename = job.stored_filename

        if status == "completed":
            stage = "Extracción y verificación completadas"
            step_index = 4
            progress = 100
        elif status == "failed":
            stage = "Error en el procesamiento del CV"
            step_index = 0
            progress = 100
        else:
            if elapsed < 3.0:
                stage = "Extrayendo texto documental del CV vía MCP (parse_cv_file)..."
                step_index = 2
                progress = min(30, int(15 + elapsed * 5))
            elif elapsed < 25.0:
                stage = (
                    "Estructurando competencias, experiencia, educación e idiomas "
                    "con Agente IA (Natasha Romanoff · NVIDIA NIM)..."
                )
                step_index = 3
                progress = min(82, int(30 + (elapsed - 3.0) * 2.3))
            else:
                stage = "Verificando JSON Schema y Grounding anti-alucinación (WF-0V)..."
                step_index = 4
                progress = min(95, int(82 + (elapsed - 25.0) * 0.4))

        return {
            "job_id": job_id,
            "status": status,
            "stage": stage,
            "step_index": step_index,
            "progress_percent": progress,
            "elapsed_seconds": elapsed,
            "profile_id": profile_id,
            "filename": filename,
            "stored_filename": stored_filename,
            "result": result,
            "error": error,
        }


class UploadAndExtractCvUseCase:
    """Valida el archivo de CV, lo guarda con nombre aleatorio y consulta el webhook de n8n."""

    def __init__(
        self,
        storage: CvStoragePort,
        webhook_gateway: CvWebhookGateway,
        max_size_mb: int = 5,
        job_store: CvExtractionJobStore | None = None,
    ) -> None:
        self._storage = storage
        self._webhook_gateway = webhook_gateway
        self._max_size_bytes = max(max_size_mb, 1) * 1024 * 1024
        self._job_store = job_store or CvExtractionJobStore()

    def validate_and_store(
        self,
        profile_id: str,
        filename: str,
        content: bytes,
        mime_type: str = "",
    ) -> tuple[str, UploadedCvFile]:
        clean_profile_id = profile_id.strip() or "prof-anonymous"
        clean_filename = PurePath(filename.strip() or "cv.pdf").name
        ext = PurePath(clean_filename).suffix.lower().lstrip(".")

        if ext not in ALLOWED_CV_EXTENSIONS:
            raise InvalidCvFileError(
                f"Extensión '.{ext}' no permitida. Formatos soportados: .pdf, .docx, .doc, .md",
                details={"filename": clean_filename, "allowed": sorted(ALLOWED_CV_EXTENSIONS)},
            )

        normalized_mime = mime_type.split(";")[0].strip().lower()
        if normalized_mime and normalized_mime not in ALLOWED_CV_MIMES:
            raise InvalidCvFileError(
                f"Tipo MIME '{normalized_mime}' no permitido para CV.",
                details={"mime_type": normalized_mime},
            )

        size_bytes = len(content)
        if size_bytes == 0:
            raise InvalidCvFileError(
                "El archivo de CV está vacío.",
                details={"filename": clean_filename},
            )

        if size_bytes > self._max_size_bytes:
            max_mb = self._max_size_bytes // (1024 * 1024)
            raise InvalidCvFileError(
                f"El archivo supera el tamaño máximo permitido ({max_mb} MB).",
                details={"size_bytes": size_bytes, "max_bytes": self._max_size_bytes},
            )

        stored_filename = self._storage.save(extension=ext, content=content)
        content_b64 = base64.b64encode(content).decode("ascii")

        uploaded_cv = UploadedCvFile(
            original_filename=clean_filename,
            stored_filename=stored_filename,
            extension=ext,
            mime_type=normalized_mime or "application/octet-stream",
            size_bytes=size_bytes,
            content_base64=content_b64,
        )
        return clean_profile_id, uploaded_cv

    def execute(
        self,
        profile_id: str,
        filename: str,
        content: bytes,
        mime_type: str = "",
    ) -> CvExtractionResult:
        clean_profile_id, uploaded_cv = self.validate_and_store(
            profile_id=profile_id,
            filename=filename,
            content=content,
            mime_type=mime_type,
        )
        return self._webhook_gateway.extract_cv_suggestions(
            profile_id=clean_profile_id,
            cv_file=uploaded_cv,
        )

    def start_async(
        self,
        profile_id: str,
        filename: str,
        content: bytes,
        mime_type: str = "",
        run_in_background: bool = True,
    ) -> dict[str, Any]:
        clean_profile_id, uploaded_cv = self.validate_and_store(
            profile_id=profile_id,
            filename=filename,
            content=content,
            mime_type=mime_type,
        )
        job = self._job_store.create(
            profile_id=clean_profile_id,
            filename=uploaded_cv.original_filename,
            stored_filename=uploaded_cv.stored_filename,
        )

        def _worker() -> None:
            try:
                res = self._webhook_gateway.extract_cv_suggestions(
                    profile_id=clean_profile_id,
                    cv_file=uploaded_cv,
                )
                self._job_store.mark_completed(job.job_id, res.to_dict())
            except ProfileDomainError as exc:
                self._job_store.mark_failed(
                    job.job_id,
                    {"code": exc.code, "message": exc.message, "details": exc.details},
                )
            except Exception as exc:
                self._job_store.mark_failed(
                    job.job_id,
                    {"code": "INTERNAL_ERROR", "message": str(exc), "details": {}},
                )

        if run_in_background:
            thread = threading.Thread(target=_worker, name=f"cv-extract-{job.job_id}", daemon=True)
            thread.start()
        else:
            _worker()

        return self._job_store.get_snapshot(job.job_id)

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        return self._job_store.get_snapshot(job_id)
