"""Servidor MCP local (FastMCP) + endpoints HTTP del router de modelos NVIDIA.

Transporte configurable por entorno:
  - stdio            (desarrollo local, p. ej. desde un cliente MCP)
  - streamable-http  (Docker; endpoint http://mcp-tools:8000/mcp)
"""

import os
from typing import Any, Literal, cast

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.domain.errors import DomainError
from app.infrastructure.security import ServiceTokenMiddleware
from app.tools.registry import build_container, register_tools

Transport = Literal["stdio", "sse", "streamable-http"]

INSTRUCTIONS = (
    "Herramientas oficiales de Bolsa de Trabajo (MCP). "
    "Reglas obligatorias: "
    "1) Nunca calcules ni modifiques el puntaje de compatibilidad; usá siempre `compute_match` "
    "(origin=RULES) y `missing_skills`. "
    "2) No inventes competencias que no figuren en el texto del CV o en el perfil; verificá con "
    "`check_grounding` y `validate_json_schema`. "
    "3) Toda recomendación generada por IA se persiste con `save_recommendation` (origin=AI)."
)

mcp = FastMCP(
    "bolsa-mcp-tools",
    instructions=INSTRUCTIONS,
    host=os.getenv("MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("MCP_PORT", "8000")),
    stateless_http=True,
    json_response=True,
)

container = build_container()
REGISTERED_TOOLS = register_tools(mcp, container)


@mcp.custom_route("/health", methods=["GET"])  # type: ignore[untyped-decorator]
async def health(_: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "service": "mcp-tools",
            "version": "0.1.0",
            "tools": sorted(REGISTERED_TOOLS.keys()),
        }
    )


@mcp.custom_route("/router/reserve", methods=["POST"])  # type: ignore[untyped-decorator]
@mcp.custom_route("/router/reservar", methods=["POST"])  # type: ignore[untyped-decorator]
async def http_router_reserve(req: Request) -> JSONResponse:
    body: dict[str, Any] = await req.json()
    role = str(body.get("role") or "default")
    tried_raw = body.get("tried") or body.get("intentados") or []
    order_raw = body.get("order") or body.get("orden") or None
    rpm_raw = body.get("rpm_limit") or body.get("global_rpm") or None
    try:
        res = await container.router.reserve_for_role(
            role=role,
            tried=[str(x) for x in tried_raw],
            order_override=[str(x) for x in order_raw] if order_raw else None,
            rpm_limit_override=int(rpm_raw) if rpm_raw else None,
        )
        return JSONResponse({"ok": True, **res})
    except DomainError as err:
        return JSONResponse(
            {"ok": False, "error": {"code": err.code, "message": err.message}},
            status_code=400,
        )


@mcp.custom_route("/router/failure", methods=["POST"])  # type: ignore[untyped-decorator]
@mcp.custom_route("/router/fallo", methods=["POST"])  # type: ignore[untyped-decorator]
async def http_router_failure(req: Request) -> JSONResponse:
    body: dict[str, Any] = await req.json()
    model = str(body.get("model") or body.get("modelo") or "")
    error = str(body.get("error") or "")
    try:
        res = container.router.report_failure(model=model, error=error)
        return JSONResponse({"ok": True, **res})
    except DomainError as err:
        return JSONResponse(
            {"ok": False, "error": {"code": err.code, "message": err.message}},
            status_code=400,
        )


@mcp.custom_route("/router/success", methods=["POST"])  # type: ignore[untyped-decorator]
@mcp.custom_route("/router/exito", methods=["POST"])  # type: ignore[untyped-decorator]
async def http_router_success(req: Request) -> JSONResponse:
    body: dict[str, Any] = await req.json()
    model = str(body.get("model") or body.get("modelo") or "")
    try:
        res = container.router.report_success(model=model)
        return JSONResponse({"ok": True, **res})
    except DomainError as err:
        return JSONResponse(
            {"ok": False, "error": {"code": err.code, "message": err.message}},
            status_code=400,
        )


@mcp.custom_route("/router/status", methods=["GET"])  # type: ignore[untyped-decorator]
@mcp.custom_route("/router/estado", methods=["GET"])  # type: ignore[untyped-decorator]
async def http_router_status(_: Request) -> JSONResponse:
    return JSONResponse({"ok": True, **container.router.status()})


def create_http_app() -> ServiceTokenMiddleware:
    service_token = os.getenv("SERVICE_TOKEN", "")
    return ServiceTokenMiddleware(mcp.streamable_http_app(), expected_token=service_token)


def main() -> None:
    transport = cast(Transport, os.getenv("MCP_TRANSPORT", "stdio"))
    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "0.0.0.0")  # noqa: S104
        port = int(os.getenv("MCP_PORT", "8000"))
        uvicorn.run(create_http_app(), host=host, port=port)
    else:
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()
