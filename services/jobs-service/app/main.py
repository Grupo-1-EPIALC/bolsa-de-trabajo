"""Punto de entrada de jobs-service.

Esqueleto mínimo: sólo expone /health. La lógica va en las capas
api/ -> application/ -> domain/ <- infrastructure/ (ver AGENTS.md §2.1).
"""

from fastapi import FastAPI

SERVICE_NAME = "jobs-service"
SERVICE_VERSION = "0.0.1"

app = FastAPI(title=SERVICE_NAME, version=SERVICE_VERSION)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}
