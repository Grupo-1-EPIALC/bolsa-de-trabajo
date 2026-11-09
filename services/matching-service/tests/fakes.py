"""Dobles de prueba para los puertos de infraestructura."""

import json
from pathlib import Path
from typing import Any

from app.domain.errors import UpstreamError
from app.infrastructure.sources_mock import MockJobSource, MockProfileSource


class FakeTrigger:
    """Simula WF-06: opcionalmente persiste un batch como haría n8n."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, Any]] = []
        self.on_call: Any = None

    def request_analysis(
        self, request_id: str, mode: str, subject_id: str, limit: int, job_id: str = ""
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "request_id": request_id,
                "mode": mode,
                "subject_id": subject_id,
                "limit": limit,
                "job_id": job_id,
            }
        )
        if self.fail:
            raise UpstreamError("n8n no disponible", {"status": 503})
        if self.on_call is not None:
            self.on_call(request_id, mode, subject_id)
        return {"status_code": 200}


def ai_batch(
    mode: str, subject_id: str, entries: list[dict[str, Any]], request_id: str = ""
) -> dict[str, Any]:
    return {
        "mode": mode,
        "subject_id": subject_id,
        "request_id": request_id,
        "summary": "Resumen ficticio",
        "model": "nvidia/modelo-ficticio",
        "prompt_version": "match_advisor@1.0.0",
        "generated_at": "2026-11-04T12:00:00Z",
        "disclaimer": "Sugerencia generada por IA.",
        "verified": True,
        "entries": entries,
    }


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str) -> dict[str, dict[str, Any]]:
    items = json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
    return {str(i["id"]): i for i in items}


def fixture_sources() -> tuple[MockProfileSource, MockJobSource]:
    """Dataset chico y estable para los tests (independiente del pool de demo en app/data/mock)."""
    return (
        MockProfileSource(_load_fixture("profiles.json")),
        MockJobSource(_load_fixture("jobs.json")),
    )
