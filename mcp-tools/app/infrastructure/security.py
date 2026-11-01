"""Middleware ASGI de autenticación para `/mcp` y `/router` (`X-Service-Token`/`?key=`)."""

import logging
import re
import secrets
import urllib.parse

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class ServiceTokenMiddleware:
    """Protege `/mcp` y `/router` con token compartido; deja `/health` y `/reglas` libres."""

    def __init__(self, app: ASGIApp, expected_token: str) -> None:
        self._app = app
        self._expected_token = expected_token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            self._expected_token
            and scope.get("type") == "http"
            and str(scope.get("path", "")).startswith(("/mcp", "/router"))
        ):
            given = self._extract_token(scope)
            if not given or not secrets.compare_digest(given, self._expected_token):
                resp = JSONResponse(
                    {
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "Token de servicio ausente o inválido (X-Service-Token)",
                            "details": {},
                        }
                    },
                    status_code=401,
                )
                await resp(scope, receive, send)
                return
        await self._app(scope, receive, send)

    @staticmethod
    def _extract_token(scope: Scope) -> str:
        raw_headers: list[tuple[bytes, bytes]] = list(scope.get("headers") or [])
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in raw_headers}
        auth = headers.get("authorization", "")
        bearer = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
        if headers.get("x-service-token"):
            return headers["x-service-token"].strip()
        if headers.get("x-api-key"):
            return headers["x-api-key"].strip()
        if bearer:
            return bearer
        query_raw = scope.get("query_string", b"").decode("latin-1")
        params = urllib.parse.parse_qs(query_raw)
        key_vals = params.get("key") or params.get("token") or []
        return key_vals[0].strip() if key_vals else ""


class MaskKeyLogFilter(logging.Filter):
    """Oculta la clave (`?key=...`) en los logs de acceso de Uvicorn."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(
                re.sub(r'key=[^&\s"]+', "key=***", arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True
