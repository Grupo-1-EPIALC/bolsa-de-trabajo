"""Genera `app/infrastructure/data/jobs_seed.json` desde el pool de demo de matching.

Uso:
    python scripts/generate_seed.py

El seed conserva los `id` y `company_id` ficticios para que matching pueda seguir usando sus
matches de demo. No se edita a mano: si cambia el pool de matching, se vuelve a ejecutar.
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.domain.normalization import normalize_text  # noqa: E402
from app.domain.rules import validate_job  # noqa: E402
from app.infrastructure.repositories.codec import job_from_document, job_to_document  # noqa: E402

SOURCE = SERVICE_ROOT.parent / "matching-service" / "app" / "data" / "mock" / "jobs.json"
TARGET = SERVICE_ROOT / "app" / "infrastructure" / "data" / "jobs_seed.json"
PUBLISHED_AT = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def transform(raw: dict[str, Any]) -> dict[str, Any]:
    requirements = raw.get("requirements") or {}
    experience = requirements.get("experience") or None
    location = raw.get("location") or {}
    conditions = raw.get("work_conditions") or {}
    salary = conditions.get("salary")

    document: dict[str, Any] = {
        "id": raw["id"],
        "company_id": raw["company_id"],
        "company_snapshot": {
            "name": raw["company_snapshot"]["name"],
            "industry": raw["company_snapshot"].get("industry"),
            "size": raw["company_snapshot"].get("size"),
            "logo_url": None,
        },
        "status": raw.get("status", "active"),
        "title": raw["title"],
        "description": raw.get("description", ""),
        "responsibilities": raw.get("responsibilities", []),
        "area": (experience or {}).get("area") or "",
        "seniority": raw["seniority"],
        "vacancies": raw.get("vacancies", 1),
        "location": {
            "country": location.get("country", "AR"),
            "province": location.get("province", ""),
            "city": location.get("city", ""),
            "postal_code": location.get("postal_code"),
            "zone": location.get("zone"),
        },
        "work_conditions": {
            **conditions,
            "salary": salary,
        },
        "requirements": {
            "skills": [
                {
                    **skill,
                    "normalized": normalize_text(skill["name"]),
                }
                for skill in requirements.get("skills", [])
            ],
            "languages": [
                {
                    **language,
                    "normalized": normalize_text(language["name"]),
                }
                for language in (requirements.get("languages") or [])
            ],
            "education": requirements.get("education") or [],
            "experience": experience,
            "certifications": requirements.get("certifications") or [],
            "academic": requirements.get("academic") or None,
        },
        "benefits": raw.get("benefits", []),
        "created_at": PUBLISHED_AT.isoformat(),
        "updated_at": PUBLISHED_AT.isoformat(),
        "published_at": PUBLISHED_AT.isoformat(),
        "expires_at": None,
        "version": 1,
    }
    return document


def main() -> None:
    raw_jobs = json.loads(SOURCE.read_text(encoding="utf-8"))
    jobs = []
    for item in raw_jobs:
        job = job_from_document(transform(item))
        validate_job(job, now=PUBLISHED_AT, check_expiry=False)
        jobs.append(job_to_document(job))

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        json.dumps(jobs, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Se generaron {len(jobs)} ofertas en {TARGET}")


if __name__ == "__main__":
    main()
