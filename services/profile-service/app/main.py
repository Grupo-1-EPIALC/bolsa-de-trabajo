"""Punto de entrada de profile-service.

Arquitectura en capas: api/ -> application/ -> domain/ <- infrastructure/ (AGENTS.md §2.1 y §4.2).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.deps import get_container
from app.api.errors import install_error_handlers
from app.api.routes import router as cv_compat_router
from app.api.routes_companies import router as companies_router
from app.api.routes_internal import router as internal_router
from app.api.routes_profiles import router as profiles_router

SERVICE_NAME = "profile-service"
SERVICE_VERSION = "0.4.0"


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
    """Crea el schema y carga el seed al arrancar (salvo que un test inyecte el contenedor)."""
    if get_container not in application.dependency_overrides:
        get_container()
    yield


app = FastAPI(title=SERVICE_NAME, version=SERVICE_VERSION, lifespan=lifespan)
install_error_handlers(app)
# Primero las rutas fijas (`/cv-test`, `/cv-extract/...`, `/companies/...`) y después
# `/{profile_id}` del perfil de estudiante.
app.include_router(cv_compat_router)
app.include_router(companies_router)
app.include_router(internal_router)
app.include_router(profiles_router)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}
