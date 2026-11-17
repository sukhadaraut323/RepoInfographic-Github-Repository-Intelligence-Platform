"""Unit tests for OllamaClient (no live Ollama server; httpx MockTransport)."""

import json

import httpx
import pytest

from app.clients.ollama_client import OllamaClient
from app.core.config import Settings
from app.core.exceptions import AIInvalidResponseError, OllamaUnavailableError

SETTINGS = Settings(github_token="t", ollama_base_url="http://ollama.test", ollama_model="test-model")


def make_client(handler) -> OllamaClient:
    return OllamaClient(SETTINGS, transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_sends_configured_model_and_returns_content() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": '{"ok": true}'}})

    assert await make_client(handler).chat_json("sys", "usr") == '{"ok": true}'
    assert seen["url"] == "http://ollama.test/api/chat"
    assert seen["body"]["model"] == "test-model"
    assert seen["body"]["format"] == "json" and seen["body"]["stream"] is True
    assert seen["body"]["options"]["num_ctx"] == SETTINGS.ollama_num_ctx
    assert [m["role"] for m in seen["body"]["messages"]] == ["system", "user"]


@pytest.mark.asyncio
async def test_connection_failure_maps_to_unavailable() -> None:
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(OllamaUnavailableError):
        await make_client(handler).chat_json("s", "u")


@pytest.mark.asyncio
async def test_timeout_maps_to_unavailable() -> None:
    def handler(request):
        raise httpx.ReadTimeout("slow")

    with pytest.raises(OllamaUnavailableError, match="stopped responding"):
        await make_client(handler).chat_json("s", "u")


@pytest.mark.asyncio
async def test_missing_model_gives_actionable_message() -> None:
    with pytest.raises(OllamaUnavailableError, match="ollama pull test-model"):
        await make_client(lambda r: httpx.Response(404, json={})).chat_json("s", "u")


@pytest.mark.asyncio
async def test_server_error_maps_to_unavailable() -> None:
    with pytest.raises(OllamaUnavailableError, match="HTTP 500"):
        await make_client(lambda r: httpx.Response(500)).chat_json("s", "u")


@pytest.mark.asyncio
async def test_unexpected_response_shape_is_invalid_response() -> None:
    with pytest.raises(AIInvalidResponseError):
        await make_client(lambda r: httpx.Response(200, json={"nope": 1})).chat_json("s", "u")


def ndjson(*chunks: dict) -> httpx.Response:
    return httpx.Response(200, content="\n".join(json.dumps(c) for c in chunks).encode())


@pytest.mark.asyncio
async def test_streamed_chunks_are_joined_in_order() -> None:
    reply = ndjson(
        {"message": {"content": '{"a":'}, "done": False},
        {"message": {"content": " 1}"}, "done": False},
        {"message": {"content": ""}, "done": True, "prompt_eval_count": 10, "eval_count": 5},
    )
    assert await make_client(lambda r: reply).chat_json("s", "u") == '{"a": 1}'


@pytest.mark.asyncio
async def test_error_chunk_maps_to_unavailable() -> None:
    with pytest.raises(OllamaUnavailableError):
        await make_client(lambda r: ndjson({"error": "model failed to load"})).chat_json("s", "u")


@pytest.mark.asyncio
async def test_garbage_stream_line_is_invalid_response() -> None:
    with pytest.raises(AIInvalidResponseError):
        await make_client(lambda r: httpx.Response(200, content=b"not json at all")).chat_json("s", "u")


@pytest.mark.asyncio
async def test_total_deadline_stops_a_run_that_never_finishes() -> None:
    import asyncio

    async def slow_handler(request):
        await asyncio.sleep(2)
        return httpx.Response(200, json={"message": {"content": "{}"}})

    settings = Settings(github_token="t", ollama_total_timeout_seconds=0.05)
    client = OllamaClient(settings, transport=httpx.MockTransport(slow_handler))
    with pytest.raises(OllamaUnavailableError, match="too long"):
        await client.chat_json("s", "u")
