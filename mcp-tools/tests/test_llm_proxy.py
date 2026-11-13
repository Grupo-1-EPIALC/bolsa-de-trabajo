"""UT-MCP-06: proxy hacia NVIDIA que corta si el modelo no contesta (WF-0R pasa al siguiente)."""

import asyncio
import json
from collections.abc import AsyncIterator

import httpx
import pytest
import respx
from starlette.responses import JSONResponse, Response
from starlette.testclient import TestClient

from app.infrastructure.llm_proxy import LlmProxy, merge_chunks

BASE = "https://nvidia.example.test/v1"
URL = f"{BASE}/chat/completions"
AUTH = {"authorization": "Bearer clave-ficticia", "content-type": "application/json"}
SSE = {"content-type": "text/event-stream"}


def body(model: str = "minimaxai/minimax-m3.1-flash", stream: bool = False) -> bytes:
    return json.dumps({"model": model, "messages": [], "stream": stream}).encode()


def sse(*chunks: dict[str, object]) -> bytes:
    lines = [f"data: {json.dumps(c)}\n\n" for c in chunks]
    return ("".join(lines) + "data: [DONE]\n\n").encode()


def delta(**kw: object) -> dict[str, object]:
    return {"id": "c1", "created": 1, "model": "m", "choices": [{"index": 0, "delta": kw}]}


class Trickle(httpx.AsyncByteStream):
    """Manda fragmentos con pausas: simula un modelo que contesta despacio o se cuelga."""

    def __init__(self, parts: list[bytes], pause: float) -> None:
        self._parts, self._pause = parts, pause

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for part in self._parts:
            await asyncio.sleep(self._pause)
            yield part


def json_of(res: Response) -> dict[str, object]:
    return json.loads(bytes(res.body))  # type: ignore[no-any-return]


async def test_ut_mcp_06_arma_la_respuesta_desde_el_streaming() -> None:
    proxy = LlmProxy(BASE, timeout_seconds=5)
    with respx.mock() as mock:
        route = mock.post(URL).respond(
            200,
            content=sse(delta(role="assistant"), delta(content="Hola "), delta(content="mundo")),
            headers=SSE,
        )
        res = await proxy.chat_completions(body(), {**AUTH, "x-otro": "no se reenvía"})
    assert res.status_code == 200
    data = json_of(res)
    assert data["object"] == "chat.completion"
    assert data["choices"][0]["message"]["content"] == "Hola mundo"  # type: ignore[index]
    sent = route.calls.last.request
    assert json.loads(sent.content)["stream"] is True  # se pide en streaming a NVIDIA
    assert sent.headers["authorization"] == "Bearer clave-ficticia"
    assert "x-otro" not in sent.headers


async def test_ut_mcp_06_corta_si_no_llega_nada_a_tiempo() -> None:
    async def slow(_request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(200, content=b"")

    proxy = LlmProxy(BASE, timeout_seconds=0.05)
    with respx.mock(assert_all_called=False) as mock:  # se cancela antes de registrarse
        mock.post(URL).mock(side_effect=slow)
        res = await proxy.chat_completions(body("nvidia/nemotron-3-ultra-550b-a55b"), AUTH)
    assert res.status_code == 504
    error = json_of(res)["error"]
    assert error["code"] == "LLM_TIMEOUT"  # type: ignore[index]
    # El router clasifica el fallo como transitorio por el texto "timeout".
    assert error["message"].startswith("timeout:")  # type: ignore[index]
    assert "nemotron-3-ultra" in error["message"]  # type: ignore[index]


async def test_ut_mcp_06_un_modelo_que_contesta_despacio_no_se_corta() -> None:
    """Cada fragmento llega antes del tiempo máximo aunque el total lo supere."""
    parts = [f"data: {json.dumps(delta(content=str(i)))}\n\n".encode() for i in range(5)]
    parts.append(b"data: [DONE]\n\n")
    proxy = LlmProxy(BASE, timeout_seconds=0.2, max_seconds=5)
    with respx.mock() as mock:
        mock.post(URL).respond(200, stream=Trickle(parts, pause=0.06), headers=SSE)
        res = await proxy.chat_completions(body(), AUTH)
    assert res.status_code == 200
    assert json_of(res)["choices"][0]["message"]["content"] == "01234"  # type: ignore[index]


async def test_ut_mcp_06_corta_si_se_cuelga_a_mitad_o_supera_el_tope() -> None:
    hung = [b"data: " + json.dumps(delta(content="a")).encode() + b"\n\n", b"data: [DONE]\n\n"]
    proxy = LlmProxy(BASE, timeout_seconds=0.1)
    with respx.mock() as mock:
        mock.post(URL).respond(200, stream=Trickle(hung, pause=0.3), headers=SSE)
        assert (await proxy.chat_completions(body(), AUTH)).status_code == 504

    many = [f"data: {json.dumps(delta(content='x'))}\n\n".encode() for _ in range(20)]
    proxy = LlmProxy(BASE, timeout_seconds=0.1, max_seconds=0.3)
    with respx.mock() as mock:
        mock.post(URL).respond(200, stream=Trickle(many, pause=0.05), headers=SSE)
        assert (await proxy.chat_completions(body(), AUTH)).status_code == 504


async def test_ut_mcp_06_errores_de_nvidia_y_de_red() -> None:
    proxy = LlmProxy(BASE, timeout_seconds=5)
    with respx.mock() as mock:
        mock.post(URL).respond(429, json={"error": "rate limit"})
        assert (await proxy.chat_completions(body(), AUTH)).status_code == 429
    with respx.mock() as mock:
        mock.post(URL).mock(side_effect=httpx.ReadTimeout("lento"))
        assert (await proxy.chat_completions(body(), AUTH)).status_code == 504
    with respx.mock() as mock:
        mock.post(URL).mock(side_effect=httpx.ConnectError("caído"))
        res = await proxy.chat_completions(body(), AUTH)
    assert res.status_code == 502
    assert json_of(res)["error"]["code"] == "LLM_UPSTREAM_ERROR"  # type: ignore[index]
    assert (await proxy.chat_completions(b"[1]", AUTH)).status_code == 400


async def test_ut_mcp_06_stream_pedido_por_n8n_llega_entero_al_final() -> None:
    proxy = LlmProxy(BASE, timeout_seconds=5)
    with respx.mock() as mock:
        mock.post(URL).respond(200, content=sse(delta(content="hola")), headers=SSE)
        res = await proxy.chat_completions(body(stream=True), AUTH)
    assert res.status_code == 200
    assert res.media_type == "text/event-stream"
    text = bytes(res.body).decode()
    assert '"content": "hola"' in text
    assert text.endswith("data: [DONE]\n\n")

    many = [f"data: {json.dumps(delta(content='x'))}\n\n".encode() for _ in range(20)]
    proxy = LlmProxy(BASE, timeout_seconds=0.1, max_seconds=0.3)
    with respx.mock() as mock:
        mock.post(URL).respond(200, stream=Trickle(many, pause=0.05), headers=SSE)
        # Contesta sin parar pero no termina: con streaming también se corta limpio.
        assert (await proxy.chat_completions(body(stream=True), AUTH)).status_code == 504


async def test_ut_mcp_06_pide_que_no_razone_salvo_que_se_active() -> None:
    def sent_kwargs(proxy: LlmProxy, extra: dict[str, object]) -> object:
        return json.loads(proxy._payload({"model": "m", **extra}))["chat_template_kwargs"]

    proxy = LlmProxy(BASE, timeout_seconds=5)
    assert sent_kwargs(proxy, {}) == {"enable_thinking": False, "thinking": False}
    assert sent_kwargs(proxy, {"chat_template_kwargs": {"enable_thinking": True, "x": 1}}) == {
        "enable_thinking": True,
        "thinking": False,
        "x": 1,
    }
    thinking = LlmProxy(BASE, timeout_seconds=5, thinking=True)
    assert "chat_template_kwargs" not in json.loads(thinking._payload({"model": "m"}))


def test_ut_mcp_06_arma_razonamiento_herramientas_y_uso() -> None:
    merged = merge_chunks(
        [
            delta(role="assistant", reasoning_content="pienso"),
            delta(
                tool_calls=[
                    {"index": 0, "id": "t1", "function": {"name": "get_", "arguments": '{"a"'}}
                ]
            ),
            delta(tool_calls=[{"index": 0, "function": {"name": "job", "arguments": ":1}"}}]),
            {
                "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
                "usage": {"total_tokens": 9},
            },
        ]
    )
    message = merged["choices"][0]["message"]
    assert message["content"] is None
    assert message["reasoning_content"] == "pienso"
    assert message["tool_calls"] == [
        {"id": "t1", "type": "function", "function": {"name": "get_job", "arguments": '{"a":1}'}}
    ]
    assert merged["choices"][0]["finish_reason"] == "tool_calls"
    assert merged["usage"] == {"total_tokens": 9}


def test_ut_mcp_06_rutas_del_servidor_sin_token_de_servicio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`/llm/v1` queda fuera del middleware: la credencial de n8n manda la clave de NVIDIA."""
    from app import main

    async def fake_chat(_body: bytes, _headers: dict[str, str]) -> Response:
        return JSONResponse({"ok": True})

    async def fake_models(_headers: dict[str, str]) -> Response:
        return JSONResponse({"data": []})

    monkeypatch.setenv("SERVICE_TOKEN", "svc-token")
    monkeypatch.setattr(main.llm_proxy, "chat_completions", fake_chat)
    monkeypatch.setattr(main.llm_proxy, "models", fake_models)
    client = TestClient(main.create_http_app())
    assert client.post("/llm/v1/chat/completions", content=body(), headers=AUTH).status_code == 200
    assert client.get("/llm/v1/models", headers=AUTH).status_code == 200
    assert client.post("/router/status").status_code == 401
