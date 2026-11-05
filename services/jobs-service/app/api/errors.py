"""Handlers de errores: todo responde con `{"error": {code, message, details}}`."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.errors import JobsError


def _error(status_code: int, code: str, message: str, details: object) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(JobsError)
    def handle_jobs_error(_request: Request, exc: JobsError) -> JSONResponse:
        return _error(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "loc": list(item.get("loc", [])),
                "msg": str(item.get("msg", "")),
                "type": str(item.get("type", "")),
            }
            for item in exc.errors()
        ]
        return _error(422, "INVALID_INPUT", "Datos de entrada inválidos", {"errors": errors})

    http_codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}

    @app.exception_handler(StarletteHTTPException)
    def handle_http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = http_codes.get(exc.status_code, "HTTP_ERROR")
        return _error(exc.status_code, code, str(exc.detail), {})
