"""Proxy compatible con OpenAI hacia NVIDIA NIM que corta cuando el modelo no contesta.

El nodo `lmChatOpenAi` de n8n no respeta su opción `timeout`: si NVIDIA tarda, la llamada queda
colgada y WF-0R nunca pasa al modelo siguiente. La credencial de n8n apunta a este proxy
(`http://mcp-tools:8000/llm/v1`).

"No contesta" = no llega nada de NVIDIA durante `AGENT_LLM_TIMEOUT_SECONDS` (ni el primer
fragmento ni ninguno de los siguientes) o la respuesta no termina dentro de
`AGENT_LLM_MAX_SECONDS`. Para medirlo, el proxy pide la respuesta a NVIDIA en streaming y la junta
entera antes de devolverla: armada si n8n la pidió entera, o como eventos SSE si la pidió en
streaming. Al cortar responde `504` con formato de error de OpenAI: el agente de n8n falla y el
bucle de WF-0R reporta el fallo al router y elige otro modelo.

Además le pide a NVIDIA que no razone (`chat_template_kwargs`), salvo `AGENT_LLM_THINKING=true`:
los modelos "piensan" miles de tokens antes de contestar y eso es lo que más tarda.

Para NVIDIA el proxy no agrega credenciales: reenvía el `Authorization` que manda n8n. Si está
activo Gemini (AI Studio, endpoint compatible con OpenAI), los pedidos de su modelo van a Google con
`GEMINI_API_KEY`, que sólo vive en el entorno de mcp-tools.
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

_FORWARDED_HEADERS = ("authorization", "content-type", "accept")


@dataclass(frozen=True)
class GeminiProvider:
    """Gemini por su API compatible con OpenAI (`GEMINI_*`)."""

    models: tuple[str, ...]
    api_key: str
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    # "none" apaga el razonamiento de los modelos Flash; vacío = no se manda.
    reasoning_effort: str = "none"

    def handles(self, model: str) -> bool:
        return model in self.models


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
        thinking: bool = False,
        gemini: GeminiProvider | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = float(timeout_seconds)
        # Tope total por modelo: un modelo que contesta pero no termina nunca también se corta.
        self._max = float(max_seconds) if max_seconds else self._timeout * 2
        # Sin razonamiento por defecto: los modelos de NVIDIA "piensan" miles de tokens antes de
        # contestar y eso es lo que más tarda. Para extraer o recomendar no hace falta.
        self._thinking = thinking
        self._gemini = gemini
        self._client_factory = client_factory or (
            lambda: httpx.AsyncClient(timeout=httpx.Timeout(self._timeout, connect=10.0))
        )

    @property
    def timeout_seconds(self) -> float:
        return self._timeout

    def _headers(self, headers: dict[str, str]) -> dict[str, str]:
        return {k: v for k, v in headers.items() if k.lower() in _FORWARDED_HEADERS}

    def _target(self, model: str, headers: dict[str, str]) -> tuple[str, dict[str, str], bool]:
        """URL, headers y si el destino es Gemini."""
        if self._gemini is not None and self._gemini.handles(model):
            forwarded = {
                k: v for k, v in self._headers(headers).items() if k.lower() != "authorization"
            }
            forwarded["Authorization"] = f"Bearer {self._gemini.api_key}"
            return f"{self._gemini.base_url.rstrip('/')}/chat/completions", forwarded, True
        return f"{self._base_url}/chat/completions", self._headers(headers), False

    def _payload(self, data: dict[str, Any], gemini: bool = False) -> bytes:
        """Siempre en streaming (para medir si contesta) y sin razonamiento."""
        payload = {**data, "stream": True}
        if gemini:
            # Gemini no acepta `chat_template_kwargs`; apaga el razonamiento con reasoning_effort.
            payload.pop("chat_template_kwargs", None)
            if not self._thinking and self._gemini and self._gemini.reasoning_effort:
                payload.setdefault("reasoning_effort", self._gemini.reasoning_effort)
            return json.dumps(payload).encode()
        if not self._thinking:
            kwargs = dict(payload.get("chat_template_kwargs") or {})
            kwargs.setdefault("enable_thinking", False)  # nemotron, minimax, qwen
            kwargs.setdefault("thinking", False)  # deepseek
            payload["chat_template_kwargs"] = kwargs
        return json.dumps(payload).encode()

    async def chat_completions(self, body: bytes, headers: dict[str, str]) -> Response:
        """Junta toda la respuesta de NVIDIA antes de devolverla: así, si el modelo no contesta
        o se pasa del tope, puede responder un error limpio (`504`) en lugar de un stream cortado.
        Si n8n pidió streaming, recibe los mismos eventos SSE, todos juntos al final."""
        data = _parse(body)
        if data is None:
            return _error(400, "INVALID_REQUEST", "El cuerpo tiene que ser un objeto JSON")
        model = str(data.get("model") or "?")
        url, forwarded, is_gemini = self._target(model, headers)
        started = time.monotonic()
        try:
            async with self._client_factory() as client:
                request = client.build_request(
                    "POST", url, content=self._payload(data, is_gemini), headers=forwarded
                )
                upstream = await self._wait(client.send(request, stream=True), started)
                try:
                    if upstream.status_code != 200:
                        content = await upstream.aread()
                        logger.warning(
                            "LLM %s: %s respondió %s",
                            model,
                            "Gemini" if is_gemini else "NVIDIA",
                            upstream.status_code,
                        )
                        return Response(
                            content=content,
                            status_code=upstream.status_code,
                            media_type=upstream.headers.get("content-type", "application/json"),
                        )
                    lines, chunks = await self._read_events(upstream, started)
                finally:
                    await upstream.aclose()
        except (LlmTimeoutError, TimeoutError, httpx.TimeoutException):
            return self._timeout_response(model, started)
        except httpx.HTTPError as exc:
            logger.warning("LLM %s: error de red con NVIDIA (%s)", model, type(exc).__name__)
            return _error(502, "LLM_UPSTREAM_ERROR", f"No se pudo conectar con NVIDIA: {exc}")
        logger.info("LLM %s: respondió en %.1f s", model, time.monotonic() - started)
        if data.get("stream"):
            sse = "".join(f"{line}\n\n" for line in lines) + "data: [DONE]\n\n"
            return Response(content=sse.encode(), media_type="text/event-stream")
        return JSONResponse(merge_chunks(chunks))

    async def _read_events(
        self, upstream: httpx.Response, started: float
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Lee los eventos SSE; corta si pasa el tiempo máximo sin recibir ninguna línea o si se
        supera el tope total."""
        lines: list[str] = []
        chunks: list[dict[str, Any]] = []
        source = upstream.aiter_lines()
        while True:
            try:
                line = await self._wait(anext(source), started)
            except StopAsyncIteration:
                break
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if raw == "[DONE]":
                break
            parsed = _parse(raw.encode())
            if parsed is not None:
                lines.append(f"data: {raw}")
                chunks.append(parsed)
        return lines, chunks

    async def _wait(self, awaitable: Any, started: float) -> Any:
        """Espera hasta el tiempo máximo sin respuesta, sin pasarse del tope total."""
        remaining = self._max - (time.monotonic() - started)
        if remaining <= 0:
            raise LlmTimeoutError
        try:
            return await asyncio.wait_for(awaitable, min(self._timeout, remaining))
        except TimeoutError as exc:
            raise LlmTimeoutError from exc

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
            f"timeout: el modelo {model} no respondió a tiempo ({elapsed:.0f} s)",
        )
