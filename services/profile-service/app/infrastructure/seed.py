"""Carga el pool de perfiles ficticios (`PROFILE_SEED_DEMO=true`). Idempotente.

Los perfiles de cuentas dadas de baja (`is_deleted`) no se vuelven a cargar: si no, el seed
los resucitaría en cada arranque después de que `account.deleted` los archivó.
"""

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.application.company_service import CompanyProfileService
from app.application.profile_service import ProfileService

logger = logging.getLogger(__name__)


def _never_deleted(_user_id: str) -> bool:
    return False


def _documents(path: str, kind: str) -> list[dict[str, Any]]:
    file = Path(path)
    if not file.exists():
        logger.warning("No existe el seed de %s %s", kind, path)
        return []
    documents: list[dict[str, Any]] = json.loads(file.read_text(encoding="utf-8"))
    return documents


def seed_profiles(
    service: ProfileService, path: str, *, is_deleted: Callable[[str], bool] = _never_deleted
) -> int:
    return sum(
        1
        for document in _documents(path, "perfiles")
        if not is_deleted(str(document.get("user_id", ""))) and service.import_document(document)
    )


def seed_companies(
    service: CompanyProfileService,
    path: str,
    *,
    is_deleted: Callable[[str], bool] = _never_deleted,
) -> int:
    return sum(
        1
        for document in _documents(path, "empresas")
        if not is_deleted(str(document.get("company_id", ""))) and service.import_document(document)
    )
