"""
Thin async client around the Ollama HTTP API (the project's locked AI runtime).

Scope is intentionally limited to one call: POST /api/chat with JSON output
requested. The response is STREAMED: a local model produces its answer
token by token over minutes, and without streaming Ollama sends nothing
until the whole answer is finished, so any timeout would have to cover the
entire generation. Streaming lets the read timeout mean "Ollama has gone
silent" instead, while a separate total deadline still bounds the run.

The client only performs the HTTP call and translates transport and
HTTP-status failures into application exceptions. It knows nothing about
repositories, prompts, or the structure of the AI output.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import AIInvalidResponseError, OllamaUnavailableError

logger = logging.getLogger(__name__)


class OllamaClient:
    """Async client for a local Ollama server."""

    def __init__(self, settings: Optional[Settings] = None, transport: Optional[httpx.AsyncBaseTransport] = None) -> None:
        self._settings = settings or get_settings()
        self._base_url = self._settings.ollama_base_url.rstrip("/")
        self._model = self._settings.ollama_model
        self._transport = transport  # test hook only; None in production

    @property
    def model(self) -> str:
        return self._model

    async def chat_json(self, system_prompt: str, user_prompt: str) -> str:
        """Stream one chat request and return the model's complete JSON text."""
        payload = {
            "model": self._model,
            "stream": True,
            "format": "json",
            "options": {
                "temperature": self._settings.ollama_temperature,
                "num_ctx": self._settings.ollama_num_ctx,
                "num_predict": self._settings.ollama_num_predict,
            },
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        logger.info(
            "[AI] Sending request to Ollama (model=%s, prompt_chars=%d, num_ctx=%d)",
            self._model, len(system_prompt) + len(user_prompt), self._settings.ollama_num_ctx,
        )
        started = time.monotonic()
        try:
            content = await asyncio.wait_for(self._stream(payload), timeout=self._settings.ollama_total_timeout_seconds)
        except asyncio.TimeoutError as exc:
            logger.error("[AI] Ollama exceeded the total time limit of %.0fs", self._settings.ollama_total_timeout_seconds)
            raise OllamaUnavailableError(
                "The Ollama model took too long to finish. Try a smaller model or raise OLLAMA_TOTAL_TIMEOUT_SECONDS."
            ) from exc
        logger.info("[AI] Ollama finished in %.1fs", time.monotonic() - started)
        return content

    async def _stream(self, payload: Dict[str, Any]) -> str:
        url = f"{self._base_url}/api/chat"
        # connect/write/pool are short; read is the max silence between chunks.
        timeout = httpx.Timeout(connect=10.0, read=self._settings.ollama_timeout_seconds, write=30.0, pool=10.0)
        parts: List[str] = []
        try:
            async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as client:
                async with client.stream("POST", url, json=payload) as response:
                    self._raise_for_status(response.status_code)
                    async for line in response.aiter_lines():
                        if line.strip():
                            self._consume_chunk(line, parts)
        except httpx.TimeoutException as exc:
            logger.error("[AI] Ollama went silent for %.0fs (model=%s)", self._settings.ollama_timeout_seconds, self._model)
            raise OllamaUnavailableError(
                "Ollama stopped responding. The model may be too slow for this machine or is still loading."
            ) from exc
        except httpx.RequestError as exc:
            logger.error("[AI] Ollama connection error: %s", type(exc).__name__)
            raise OllamaUnavailableError("Could not connect to Ollama. Make sure it is running.") from exc

        content = "".join(parts)
        if not content.strip():
            raise AIInvalidResponseError("Ollama returned an unexpected or empty response.")
        return content

    def _raise_for_status(self, status_code: int) -> None:
        if status_code == 404:
            raise OllamaUnavailableError(
                f"Ollama model '{self._model}' was not found. Pull it with: ollama pull {self._model}"
            )
        if status_code >= 400:
            logger.error("[AI] Ollama returned HTTP %s", status_code)
            raise OllamaUnavailableError(f"Ollama returned an error (HTTP {status_code}).")

    @staticmethod
    def _consume_chunk(line: str, parts: List[str]) -> None:
        try:
            chunk = json.loads(line)
        except ValueError as exc:
            raise AIInvalidResponseError("Ollama returned an unexpected response format.") from exc
        if not isinstance(chunk, dict):
            raise AIInvalidResponseError("Ollama returned an unexpected response format.")
        if chunk.get("error"):
            raise OllamaUnavailableError("Ollama reported an error while generating the response.")
        message = chunk.get("message")
        if isinstance(message, dict):
            parts.append(message.get("content") or "")
        if chunk.get("done"):
            # Token counts make truncation (prompt >= num_ctx) and slow runs visible in the logs.
            logger.info(
                "[AI] Ollama stats: prompt_tokens=%s generated_tokens=%s",
                chunk.get("prompt_eval_count"), chunk.get("eval_count"),
            )
