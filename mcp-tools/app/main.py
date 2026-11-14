"""Servidor MCP local (FastMCP) con perfiles por agente + endpoints HTTP del router NVIDIA.

Transporte configurable por entorno:
  - stdio            (desarrollo local, p. ej. desde un cliente MCP)
  - streamable-http  (Docker; endpoint http://mcp-tools:8000/mcp)

Los nodos `@n8n/n8n-nodes-langchain.mcpClientTool` y `@n8n/n8n-nodes-langchain.mcpClient`
se conectan a `/mcp?key=<SERVICE_TOKEN>&sesion=<id>&agente=<id>&perfil=<perfil>&herramientas=<a,b>`.
"""

import logging
import os
from pathlib import Path
from typing import Any, Literal, cast

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.types import Tool
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response

from app.domain.errors import DomainError
from app.infrastructure.llm_proxy import GeminiProvider, LlmProxy
from app.infrastructure.security import MaskKeyLogFilter, ServiceTokenMiddleware
from app.infrastructure.settings_env import gemini_models
from app.tools.registry import build_container, register_tools

Transport = Literal["stdio", "sse", "streamable-http"]

_REGLAS_PATH = Path(__file__).resolve().parent / "data" / "reglas.md"
INSTRUCTIONS = (
    _REGLAS_PATH.read_text(encoding="utf-8")
    if _REGLAS_PATH.is_file()
    else (
        "Herramientas oficiales de Bolsa de Trabajo (MCP). "
        "Nunca calcules ni modifiques el puntaje; usá `compute_match` (origin=RULES)."
    )
)

# Perfiles (?perfil= en la URL): qué herramientas ve cada tipo de agente en n8n.
TOOL_PROFILES: dict[str, set[str]] = {
    "planificador": {"get_agent_settings", "fecha_hora"},
    "cv": {
        "get_agent_settings",
        "resolver_skills",
        "leer_skill",
        "list_skills",
        "validate_json_schema",
        "check_grounding",
        "fecha_hora",
    },
    "postulante": {
        "get_agent_settings",
        "resolver_skills",
        "leer_skill",
        "list_skills",
        "get_profile",
        "get_job",
        "list_active_jobs",
        "compute_match",
        "missing_skills",
        "rank_jobs_for_student",
        "search_courses",
        "save_recommendation",
        "validate_json_schema",
        "check_grounding",
        "fecha_hora",
    },
    "empresa": {
        "get_agent_settings",
        "resolver_skills",
        "leer_skill",
        "list_skills",
        "get_job",
        "get_profile",
        "list_candidate_profiles",
        "compute_match",
        "missing_skills",
        "rank_candidates_for_job",
        "save_recommendation",
        "validate_json_schema",
        "check_grounding",
        "fecha_hora",
    },
    "verificador": {
        "get_agent_settings",
        "resolver_skills",
        "leer_skill",
        "list_skills",
        "validate_json_schema",
        "check_grounding",
        "fecha_hora",
    },
    "adjuntos": {"parse_cv_file", "parse_cv_text", "leer_archivo"},
}


def allowed_tools(perfil: str | None, herramientas: str | None) -> set[str] | None:
    """Herramientas que ve una conexión. `None` = todas.

    - `perfil`: techo por tipo de agente (`TOOL_PROFILES`); uno desconocido no filtra.
    - `herramientas`: lista separada por comas con las que usa ese agente puntual. Sólo achica
      el perfil (nunca agrega una que el perfil no tenga). Vacía = ninguna herramienta.
    """
    allowed = TOOL_PROFILES.get(perfil or "todas")
    if herramientas is None:
        return allowed
    wanted = {name.strip() for name in herramientas.split(",") if name.strip()}
    return wanted if allowed is None else wanted & allowed


class ProfiledFastMCP(FastMCP):
    """Filtra las herramientas según `?perfil=` y `?herramientas=` de la conexión MCP."""

    def _query(self, name: str) -> str | None:
        try:
            ctx = self.get_context()
            req: Any = ctx.request_context.request
            if req is not None and hasattr(req, "query_params"):
                val = req.query_params.get(name)
                return None if val is None else str(val)
        except (LookupError, ValueError, AttributeError):
            return None
        return None

    async def list_tools(self) -> list[Tool]:
        all_tools = await super().list_tools()
        allowed = allowed_tools(self._query("perfil"), self._query("herramientas"))
        if allowed is None:
            return all_tools
        return [t for t in all_tools if t.name in allowed]


mcp = ProfiledFastMCP(
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
            "version": "0.10.0",
            "tools": sorted(REGISTERED_TOOLS.keys()),
            "profiles": sorted(TOOL_PROFILES.keys()),
        }
    )


@mcp.custom_route("/reglas", methods=["GET"])  # type: ignore[untyped-decorator]
async def reglas(_: Request) -> PlainTextResponse:
    return PlainTextResponse(INSTRUCTIONS)


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


# Proxy hacia NVIDIA con tiempo máximo (la credencial de n8n apunta a /llm/v1). Fuera de
# /mcp y /router: n8n manda la clave de NVIDIA como Bearer y el proxy la reenvía tal cual.
llm_proxy = LlmProxy(
    os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    float(os.getenv("AGENT_LLM_TIMEOUT_SECONDS", "60")),
    max_seconds=float(os.getenv("AGENT_LLM_MAX_SECONDS", "120")),
    thinking=os.getenv("AGENT_LLM_THINKING", "false").strip().lower() in ("1", "true", "yes"),
    gemini=(
        GeminiProvider(
            models=_gemini,
            api_key=os.environ["GEMINI_API_KEY"].strip(),
            base_url=os.getenv("GEMINI_BASE_URL")
            or "https://generativelanguage.googleapis.com/v1beta/openai",
            reasoning_effort=os.getenv("GEMINI_REASONING_EFFORT", "none").strip(),
        )
        if (_gemini := gemini_models(os.environ))
        else None
    ),
)


@mcp.custom_route("/llm/v1/chat/completions", methods=["POST"])  # type: ignore[untyped-decorator]
async def http_llm_chat(req: Request) -> Response:
    return await llm_proxy.chat_completions(await req.body(), dict(req.headers))


@mcp.custom_route("/llm/v1/models", methods=["GET"])  # type: ignore[untyped-decorator]
async def http_llm_models(req: Request) -> Response:
    return await llm_proxy.models(dict(req.headers))


def create_http_app() -> ServiceTokenMiddleware:
    service_token = os.getenv("SERVICE_TOKEN", "")
    return ServiceTokenMiddleware(mcp.streamable_http_app(), expected_token=service_token)


def main() -> None:
    transport = cast(Transport, os.getenv("MCP_TRANSPORT", "stdio"))
    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "0.0.0.0")  # noqa: S104
        port = int(os.getenv("MCP_PORT", "8000"))
        logging.getLogger("uvicorn.access").addFilter(MaskKeyLogFilter())
        # Logs del proxy del modelo (qué modelo respondió, en cuánto, o si se cortó).
        proxy_log = logging.getLogger("app.infrastructure.llm_proxy")
        proxy_log.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:     %(message)s"))
        proxy_log.addHandler(handler)
        proxy_log.propagate = False
        uvicorn.run(create_http_app(), host=host, port=port)
    else:
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()
