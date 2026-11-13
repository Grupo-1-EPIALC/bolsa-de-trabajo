"""Proxy compatible con OpenAI hacia NVIDIA NIM que corta cuando el modelo no contesta.

El nodo `lmChatOpenAi` de n8n no respeta su opción `timeout`: si NVIDIA tarda, la llamada queda
colgada y WF-0R nunca pasa al modelo siguiente. La credencial de n8n apunta a este proxy
(`http://mcp-tools:8000/llm/v1`).

"No contesta" = no llega nada de NVIDIA durante `AGENT_LLM_TIMEOUT_SECONDS`: ni el primer
fragmento ni ninguno de los siguientes. Para medirlo, el proxy pide la respuesta a NVIDIA en
streaming aunque n8n la haya pedido entera, y la arma antes de devolverla. Un modelo que va
contestando despacio no se corta (salvo el tope de `max_seconds`). Al cortar responde `504` con
formato de error de OpenAI: el agente de n8n falla y el bucle de WF-0R reporta el fallo al router
y elige otro modelo.

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


class LlmTimeoutError(Exception):
    """NVIDIA no mandó nada durante el tiempo máximo."""


def _error(status: int, code: str, message: str) -> JSONResponse:
    """Error con la forma de OpenAI: el SDK de n8n lo convierte en un error con este mensaje."""
    return JSONResponse(
        {"error": {"message": message, "type": code.lower(), "code": code}},
        status_code=status,
    )


def _parse(body: bytes) -> dict[str, Any] | None:
    try:
        data: Any = json.loads(body or b"{}")
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def merge_chunks(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Arma una respuesta `chat.completion` a partir de los fragmentos del streaming."""
    first = chunks[0] if chunks else {}
    choices: dict[int, dict[str, Any]] = {}
    usage: Any = None
    for chunk in chunks:
        usage = chunk.get("usage") or usage
        for part in chunk.get("choices") or []:
            idx = int(part.get("index") or 0)
            acc = choices.setdefault(
                idx, {"role": "assistant", "content": [], "reasoning": [], "tools": {}, "end": None}
            )
            delta = part.get("delta") or {}
            if delta.get("role"):
                acc["role"] = delta["role"]
            if delta.get("content"):
                acc["content"].append(delta["content"])
            if delta.get("reasoning_content"):
                acc["reasoning"].append(delta["reasoning_content"])
            for call in delta.get("tool_calls") or []:
                slot = acc["tools"].setdefault(
                    int(call.get("index") or 0),
                    {"id": None, "type": "function", "function": {"name": "", "arguments": ""}},
                )
                if call.get("id"):
                    slot["id"] = call["id"]
                fn = call.get("function") or {}
                slot["function"]["name"] += fn.get("name") or ""
                slot["function"]["arguments"] += fn.get("arguments") or ""
            if part.get("finish_reason"):
                acc["end"] = part["finish_reason"]

    out_choices = []
    for idx in sorted(choices):
        acc = choices[idx]
        message: dict[str, Any] = {
            "role": acc["role"],
            "content": "".join(acc["content"]) if acc["content"] else None,
        }
        if acc["reasoning"]:
            message["reasoning_content"] = "".join(acc["reasoning"])
        if acc["tools"]:
            message["tool_calls"] = [acc["tools"][i] for i in sorted(acc["tools"])]
        out_choices.append({"index": idx, "message": message, "finish_reason": acc["end"]})

    result: dict[str, Any] = {
        "id": first.get("id", "chatcmpl-proxy"),
        "object": "chat.completion",
        "created": first.get("created", int(time.time())),
        "model": first.get("model", "?"),
        "choices": out_choices,
    }
    if usage:
        result["usage"] = usage
    return result


class LlmProxy:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
        max_seconds: float | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = float(timeout_seconds)
        # Tope total por si un modelo manda fragmentos sueltos sin terminar nunca.
        self._max = float(max_seconds) if max_seconds else self._timeout * 4
        self._client_factory = client_factory or (
            lambda: httpx.AsyncClient(timeout=httpx.Timeout(self._timeout, connect=10.0))
        )

    @property
    def timeout_seconds(self) -> float:
        return self._timeout

    def _headers(self, headers: dict[str, str]) -> dict[str, str]:
        return {k: v for k, v in headers.items() if k.lower() in _FORWARDED_HEADERS}

    async def chat_completions(self, body: bytes, headers: dict[str, str]) -> Response:
        data = _parse(body)
        if data is None:
            return _error(400, "INVALID_REQUEST", "El cuerpo tiene que ser un objeto JSON")
        model = str(data.get("model") or "?")
        if data.get("stream"):
            return await self._passthrough_stream(body, headers, model)
        return await self._collected(data, headers, model)

    async def _collected(
        self, data: dict[str, Any], headers: dict[str, str], model: str
    ) -> Response:
        """Pedido sin streaming: se pide en streaming a NVIDIA y se devuelve armado."""
        started = time.monotonic()
        payload = json.dumps({**data, "stream": True}).encode()
        try:
            async with self._client_factory() as client:
                request = client.build_request(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    content=payload,
                    headers=self._headers(headers),
                )
                upstream = await self._wait(client.send(request, stream=True), started)
                try:
                    if upstream.status_code != 200:
                        content = await upstream.aread()
                        logger.warning("LLM %s: NVIDIA respondió %s", model, upstream.status_code)
                        return Response(
                            content=content,
                            status_code=upstream.status_code,
                            media_type=upstream.headers.get("content-type", "application/json"),
                        )
                    chunks = await self._read_events(upstream, started)
                finally:
                    await upstream.aclose()
        except (LlmTimeoutError, TimeoutError, httpx.TimeoutException):
            return self._timeout_response(model, started)
        except httpx.HTTPError as exc:
            logger.warning("LLM %s: error de red con NVIDIA (%s)", model, type(exc).__name__)
            return _error(502, "LLM_UPSTREAM_ERROR", f"No se pudo conectar con NVIDIA: {exc}")
        logger.info("LLM %s: respondió en %.1f s", model, time.monotonic() - started)
        return JSONResponse(merge_chunks(chunks))

    async def _read_events(self, upstream: httpx.Response, started: float) -> list[dict[str, Any]]:
        """Lee los eventos SSE; corta si pasa el tiempo máximo sin recibir ninguna línea."""
        chunks: list[dict[str, Any]] = []
        lines = upstream.aiter_lines()
        while True:
            try:
                line = await self._wait(anext(lines), started)
            except StopAsyncIteration:
                break
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if raw == "[DONE]":
                break
            parsed = _parse(raw.encode())
            if parsed is not None:
                chunks.append(parsed)
        return chunks

    async def _wait(self, awaitable: Any, started: float) -> Any:
        """Espera hasta el tiempo máximo sin respuesta, sin pasarse del tope total."""
        remaining = self._max - (time.monotonic() - started)
        if remaining <= 0:
            raise LlmTimeoutError
        try:
            return await asyncio.wait_for(awaitable, min(self._timeout, remaining))
        except TimeoutError as exc:
            raise LlmTimeoutError from exc

    async def _passthrough_stream(
        self, body: bytes, headers: dict[str, str], model: str
    ) -> Response:
        """n8n pidió streaming: se reenvía tal cual con los mismos cortes."""
        started = time.monotonic()
        client = self._client_factory()
        request = client.build_request(
            "POST",
            f"{self._base_url}/chat/completions",
            content=body,
            headers=self._headers(headers),
        )
        try:
            upstream = await self._wait(client.send(request, stream=True), started)
            chunks = upstream.aiter_raw()
            first = await self._wait(anext(chunks, b""), started)
        except (LlmTimeoutError, httpx.TimeoutException):
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
            else:
                logger.info(
                    "LLM %s: respondió en streaming en %.1f s", model, time.monotonic() - started
                )
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
        logger.warning("LLM %s: sin respuesta, se corta a los %.0f s", model, elapsed)
        return _error(
            504,
            "LLM_TIMEOUT",
            f"timeout: el modelo {model} no respondió en {self._timeout:.0f} s",
        )
