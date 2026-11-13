"""Proxy compatible con OpenAI hacia NVIDIA NIM con un tiempo máximo de respuesta.

El nodo `lmChatOpenAi` de n8n no respeta su opción `timeout`: si NVIDIA tarda, la llamada queda
colgada y WF-0R nunca pasa al modelo siguiente. La credencial de n8n apunta a este proxy
(`http://mcp-tools:8000/llm/v1`); si el modelo no termina de responder en
`AGENT_LLM_TIMEOUT_SECONDS`, el proxy corta y devuelve `504` con formato de error de OpenAI. El
agente de n8n falla y el bucle de WF-0R reporta el fallo al router y elige otro modelo.

El proxy no agrega credenciales: reenvía el `Authorization` que manda n8n (la clave de NVIDIA).
"""

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
from starlette.responses import JSONResponse, Response, StreamingResponse

logger = logging.getLogger(__name__)

_FORWARDED_HEADERS = ("authorization", "content-type", "accept")


def _error(status: int, code: str, message: str) -> JSONResponse:
    """Error con la forma de OpenAI: el SDK de n8n lo convierte en un error con este mensaje."""
    return JSONResponse(
        {"error": {"message": message, "type": code.lower(), "code": code}},
        status_code=status,
    )


def _model_of(body: bytes) -> tuple[str, bool]:
    try:
        data: Any = json.loads(body or b"{}")
    except ValueError:
        return "?", False
    if not isinstance(data, dict):
        return "?", False
    return str(data.get("model") or "?"), bool(data.get("stream"))


class LlmProxy:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = float(timeout_seconds)
        self._client_factory = client_factory or (
            lambda: httpx.AsyncClient(timeout=httpx.Timeout(self._timeout, connect=10.0))
        )

    @property
    def timeout_seconds(self) -> float:
        return self._timeout

    def _headers(self, headers: dict[str, str]) -> dict[str, str]:
        return {k: v for k, v in headers.items() if k.lower() in _FORWARDED_HEADERS}

    async def chat_completions(self, body: bytes, headers: dict[str, str]) -> Response:
        model, stream = _model_of(body)
        if stream:
            return await self._stream(body, headers, model)
        started = time.monotonic()
        url = f"{self._base_url}/chat/completions"
        try:
            async with self._client_factory() as client:
                upstream = await asyncio.wait_for(
                    client.post(url, content=body, headers=self._headers(headers)),
                    timeout=self._timeout,
                )
        except (TimeoutError, httpx.TimeoutException):
            return self._timeout_response(model, started)
        except httpx.HTTPError as exc:
            logger.warning("LLM %s: error de red con NVIDIA (%s)", model, type(exc).__name__)
            return _error(502, "LLM_UPSTREAM_ERROR", f"No se pudo conectar con NVIDIA: {exc}")
        logger.info("LLM %s: %s en %.1f s", model, upstream.status_code, time.monotonic() - started)
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            media_type=upstream.headers.get("content-type", "application/json"),
        )

    async def _stream(self, body: bytes, headers: dict[str, str], model: str) -> Response:
        """Con `stream=true`: el primer fragmento tiene que llegar antes del tiempo máximo y
        después ninguna pausa entre fragmentos puede superarlo."""
        started = time.monotonic()
        client = self._client_factory()
        request = client.build_request(
            "POST",
            f"{self._base_url}/chat/completions",
            content=body,
            headers=self._headers(headers),
        )
        try:
            upstream = await asyncio.wait_for(client.send(request, stream=True), self._timeout)
            chunks = upstream.aiter_raw()
            first = await asyncio.wait_for(anext(chunks, b""), self._timeout)
        except (TimeoutError, httpx.TimeoutException):
            await client.aclose()
            return self._timeout_response(model, started)
        except httpx.HTTPError as exc:
            await client.aclose()
            return _error(502, "LLM_UPSTREAM_ERROR", f"No se pudo conectar con NVIDIA: {exc}")

        async def relay() -> AsyncIterator[bytes]:
            try:
                if first:
                    yield first
                async for chunk in chunks:  # el `read` del cliente corta las pausas largas
                    yield chunk
            except httpx.TimeoutException:
                logger.warning("LLM %s: el stream se cortó por inactividad", model)
            finally:
                await upstream.aclose()
                await client.aclose()

        return StreamingResponse(
            relay(),
            status_code=upstream.status_code,
            media_type=upstream.headers.get("content-type", "text/event-stream"),
        )

    async def models(self, headers: dict[str, str]) -> Response:
        """`GET /models`: lo usa n8n para probar la credencial."""
        try:
            async with self._client_factory() as client:
                upstream = await client.get(
                    f"{self._base_url}/models", headers=self._headers(headers)
                )
        except httpx.HTTPError as exc:
            return _error(502, "LLM_UPSTREAM_ERROR", f"No se pudo conectar con NVIDIA: {exc}")
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            media_type=upstream.headers.get("content-type", "application/json"),
        )

    def _timeout_response(self, model: str, started: float) -> JSONResponse:
        elapsed = time.monotonic() - started
        logger.warning("LLM %s: sin respuesta en %.0f s, se corta", model, elapsed)
        return _error(
            504,
            "LLM_TIMEOUT",
            f"timeout: el modelo {model} no respondió en {self._timeout:.0f} s",
        )
