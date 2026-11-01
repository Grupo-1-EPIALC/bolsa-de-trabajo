"""Punto de entrada de profile-service.

Arquitectura en capas: api/ -> application/ -> domain/ <- infrastructure/ (AGENTS.md §2.1 y §4.2).
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router as profiles_router
from app.domain.errors import ProfileDomainError

SERVICE_NAME = "profile-service"
SERVICE_VERSION = "0.1.0"

app = FastAPI(title=SERVICE_NAME, version=SERVICE_VERSION)
app.include_router(profiles_router)


@app.exception_handler(ProfileDomainError)
def handle_profile_domain_error(
    _request: Request,
    exc: ProfileDomainError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}
