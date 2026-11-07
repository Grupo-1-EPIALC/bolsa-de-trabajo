"""Carga del seed de demo (12 ofertas ficticias) y validación previa."""

import json
from pathlib import Path

from app.domain.errors import InvalidInputError
from app.domain.models import JobOpportunity
from app.domain.ports import JobRepository
from app.domain.rules import ensure_company_snapshot, validate_job
from app.infrastructure.repositories.codec import job_from_document


class SeedError(RuntimeError):
    pass


def load_seed_jobs(path: str | Path) -> list[JobOpportunity]:
    seed_path = Path(path)
    try:
        raw = json.loads(seed_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SeedError(f"No se pudo leer el seed {seed_path}: {exc}") from exc
    except ValueError as exc:
        raise SeedError(f"El seed {seed_path} no es JSON válido: {exc}") from exc
    if not isinstance(raw, list):
        raise SeedError("El seed debe ser una lista de ofertas")
    jobs: list[JobOpportunity] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise SeedError(f"El elemento {index} del seed no es un objeto")
        try:
            jobs.append(job_from_document(item))
        except (KeyError, TypeError, ValueError) as exc:
            raise SeedError(f"El elemento {index} del seed es inválido: {exc}") from exc
    return jobs


def validate_seed(jobs: list[JobOpportunity]) -> None:
    for job in jobs:
        try:
            validate_job(job, now=job.updated_at, check_expiry=False)
            ensure_company_snapshot(job.company_snapshot)
        except InvalidInputError as exc:
            raise SeedError(f"La oferta {job.id} del seed es inválida: {exc.message}") from exc


def seed_repository(repository: JobRepository, path: str | Path) -> int:
    """Carga el seed sólo si el repositorio está vacío. Devuelve cuántas cargó.

    Si otra réplica arranca a la vez, el insert del mismo id choca contra la clave
    primaria; en ese caso se salta la oferta (otro proceso la cargó) y el seed queda
    idempotente. Cualquier otro error de arranque se propaga tal como viene.
    """
    if repository.count() > 0:
        return 0
    jobs = load_seed_jobs(path)
    validate_seed(jobs)
    loaded = 0
    for job in jobs:
        try:
            repository.add(job)
        except Exception:
            if repository.get(job.id) is None:
                raise  # No fue una duplicación por carrera con otro seed.
            continue  # Otra réplica llegó primero.
        loaded += 1
    return loaded
