"""Punto de entrada de matching-service.

Motor de matching por reglas (`origin = "RULES"`) y almacén de las recomendaciones de IA que
genera n8n (`origin = "AI"`). No llama a ningún LLM (AGENTS.md §4.4).
Capas: api/ -> application/ -> domain/ <- infrastructure/ (AGENTS.md §2.1).
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router as matches_router
from app.domain.errors import MatchingError

SERVICE_NAME = "matching-service"
SERVICE_VERSION = "0.2.1"

# Docs bajo el prefijo del servicio: pasan por el gateway (/api/v1/matches/) sin rutas nuevas.
app = FastAPI(
    title=SERVICE_NAME,
    version=SERVICE_VERSION,
    docs_url="/api/v1/matches/docs",
    redoc_url="/api/v1/matches/redoc",
    openapi_url="/api/v1/matches/openapi.json",
)
app.include_router(matches_router)


def _error(status_code: int, code: str, message: str, details: object) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


@app.exception_handler(MatchingError)
def handle_matching_error(_request: Request, exc: MatchingError) -> JSONResponse:
    return _error(exc.status_code, exc.code, exc.message, exc.details)


@app.exception_handler(RequestValidationError)
def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {
            "loc": list(e.get("loc", [])),
            "msg": str(e.get("msg", "")),
            "type": str(e.get("type", "")),
        }
        for e in exc.errors()
    ]
    return _error(422, "INVALID_INPUT", "Datos de entrada inválidos", {"errors": errors})


_HTTP_CODES = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}


@app.exception_handler(StarletteHTTPException)
def handle_http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """404 de rutas inexistentes, 405, etc. también con el formato común de errores."""
    code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
    return _error(exc.status_code, code, str(exc.detail), {})


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}
