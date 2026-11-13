"""UT-MCP-06: proxy hacia NVIDIA con tiempo máximo (WF-0R pasa al modelo siguiente si corta)."""

import asyncio
import json
from collections.abc import AsyncIterator

import httpx
import pytest
import respx
from starlette.testclient import TestClient

from app.infrastructure.llm_proxy import LlmProxy

BASE = "https://nvidia.example.test/v1"
AUTH = {"authorization": "Bearer clave-ficticia", "content-type": "application/json"}


def body(model: str = "minimaxai/minimax-m3.1-flash", stream: bool = False) -> bytes:
    return json.dumps({"model": model, "messages": [], "stream": stream}).encode()


@pytest.mark.asyncio
async def test_ut_mcp_06_reenvia_la_respuesta_y_la_clave() -> None:
    proxy = LlmProxy(BASE, timeout_seconds=5)
    with respx.mock() as mock:
        route = mock.post(f"{BASE}/chat/completions").respond(200, json={"choices": [1]})
        res = await proxy.chat_completions(body(), {**AUTH, "x-otro": "no se reenvía"})
    assert res.status_code == 200
    assert json.loads(bytes(res.body)) == {"choices": [1]}
    sent = route.calls.last.request
    assert sent.headers["authorization"] == "Bearer clave-ficticia"
    assert "x-otro" not in sent.headers


@pytest.mark.asyncio
async def test_ut_mcp_06_corta_si_el_modelo_no_responde_a_tiempo() -> None:
    async def slow(_request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(200, json={})

    proxy = LlmProxy(BASE, timeout_seconds=0.05)
    with respx.mock(assert_all_called=False) as mock:  # se cancela antes de registrarse
        mock.post(f"{BASE}/chat/completions").mock(side_effect=slow)
        res = await proxy.chat_completions(body("nvidia/nemotron-3-ultra-550b-a55b"), AUTH)
    assert res.status_code == 504
    error = json.loads(bytes(res.body))["error"]
    assert error["code"] == "LLM_TIMEOUT"
    # El router clasifica el fallo como transitorio por el texto "timeout".
    assert error["message"].startswith("timeout:")
    assert "nemotron-3-ultra" in error["message"]


@pytest.mark.asyncio
async def test_ut_mcp_06_timeout_y_errores_de_red_de_httpx() -> None:
    proxy = LlmProxy(BASE, timeout_seconds=5)
    with respx.mock() as mock:
        mock.post(f"{BASE}/chat/completions").mock(side_effect=httpx.ReadTimeout("lento"))
        assert (await proxy.chat_completions(body(), AUTH)).status_code == 504
    with respx.mock() as mock:
        mock.post(f"{BASE}/chat/completions").mock(side_effect=httpx.ConnectError("caído"))
        res = await proxy.chat_completions(body(), AUTH)
    assert res.status_code == 502
    assert json.loads(bytes(res.body))["error"]["code"] == "LLM_UPSTREAM_ERROR"


@pytest.mark.asyncio
async def test_ut_mcp_06_errores_de_nvidia_pasan_tal_cual() -> None:
    proxy = LlmProxy(BASE, timeout_seconds=5)
    with respx.mock() as mock:
        mock.post(f"{BASE}/chat/completions").respond(429, json={"error": "rate limit"})
        res = await proxy.chat_completions(body(), AUTH)
    assert res.status_code == 429


@pytest.mark.asyncio
async def test_ut_mcp_06_stream_y_corte_antes_del_primer_fragmento() -> None:
    proxy = LlmProxy(BASE, timeout_seconds=5)
    with respx.mock() as mock:
        mock.post(f"{BASE}/chat/completions").respond(
            200, content=b"data: hola\n\n", headers={"content-type": "text/event-stream"}
        )
        res = await proxy.chat_completions(body(stream=True), AUTH)
        assert res.status_code == 200
        received = b"".join([chunk async for chunk in _iterate(res)])
    assert received == b"data: hola\n\n"

    async def slow(_request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(200, content=b"")

    proxy = LlmProxy(BASE, timeout_seconds=0.05)
    with respx.mock(assert_all_called=False) as mock:  # se cancela antes de registrarse
        mock.post(f"{BASE}/chat/completions").mock(side_effect=slow)
        res = await proxy.chat_completions(body(stream=True), AUTH)
    assert res.status_code == 504


async def _iterate(response: object) -> AsyncIterator[bytes]:
    async for chunk in response.body_iterator:  # type: ignore[attr-defined]
        yield chunk if isinstance(chunk, bytes) else chunk.encode()


def test_ut_mcp_06_rutas_del_servidor_sin_token_de_servicio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`/llm/v1` queda fuera del middleware: la credencial de n8n manda la clave de NVIDIA."""
    from app import main

    async def fake_chat(_body: bytes, _headers: dict[str, str]) -> httpx.Response:
        from starlette.responses import JSONResponse

        return JSONResponse({"ok": True})  # type: ignore[return-value]

    monkeypatch.setenv("SERVICE_TOKEN", "svc-token")
    monkeypatch.setattr(main.llm_proxy, "chat_completions", fake_chat)
    client = TestClient(main.create_http_app())
    res = client.post("/llm/v1/chat/completions", content=body(), headers=AUTH)
    assert res.status_code == 200
    assert client.post("/router/status").status_code == 401
