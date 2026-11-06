"""Carga el pool de perfiles ficticios (`PROFILE_SEED_DEMO=true`). Idempotente."""

import json
import logging
from pathlib import Path

from app.application.company_service import CompanyProfileService
from app.application.profile_service import ProfileService

logger = logging.getLogger(__name__)


def seed_profiles(service: ProfileService, path: str) -> int:
    file = Path(path)
    if not file.exists():
        logger.warning("No existe el seed de perfiles %s", path)
        return 0
    documents = json.loads(file.read_text(encoding="utf-8"))
    return sum(1 for document in documents if service.import_document(document))


def seed_companies(service: CompanyProfileService, path: str) -> int:
    file = Path(path)
    if not file.exists():
        logger.warning("No existe el seed de empresas %s", path)
        return 0
    documents = json.loads(file.read_text(encoding="utf-8"))
    return sum(1 for document in documents if service.import_document(document))
