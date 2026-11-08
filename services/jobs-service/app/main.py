"""Punto de entrada de jobs-service.

Capas: api/ -> application/ -> domain/ <- infrastructure/ (AGENTS.md §2.1).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.deps import get_container
from app.api.errors import install_error_handlers
from app.api.routes_companies import router as companies_router
from app.api.routes_internal import router as internal_router
from app.api.routes_jobs import router as jobs_router

SERVICE_NAME = "jobs-service"
SERVICE_VERSION = "0.2.1"


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Crea el schema y carga el seed al arrancar (salvo que un test inyecte el contenedor)."""
    if get_container not in application.dependency_overrides:
        get_container()
    yield


# Docs bajo el prefijo del servicio: pasan por el gateway (/api/v1/jobs/) sin rutas nuevas.
app = FastAPI(
    title=SERVICE_NAME,
    version=SERVICE_VERSION,
    docs_url="/api/v1/jobs/docs",
    redoc_url="/api/v1/jobs/redoc",
    openapi_url="/api/v1/jobs/openapi.json",
    lifespan=lifespan,
)
install_error_handlers(app)
app.include_router(internal_router)
app.include_router(jobs_router)
app.include_router(companies_router)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}
