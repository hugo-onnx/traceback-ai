"""Ollama provider for traceback-ai (local, no API key required)."""

from __future__ import annotations

import json
import os

import httpx

from .base import BaseProvider, _http_post, validate_base_url

_DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaProvider(BaseProvider):
    """Calls the local Ollama API — no API key required.

    Ollama must be running locally: https://ollama.ai
    Pull a model first: ollama pull llama3.2

    Security note: Ollama runs on localhost without authentication.
    Do not expose the Ollama port to external networks.
    """

    def __init__(self, base_url: str | None = None) -> None:
        raw_url = base_url or os.getenv("OLLAMA_HOST", _DEFAULT_BASE_URL)
        # Allow http://localhost only; HTTPS is fine for tunneled remote instances
        self._base_url = validate_base_url(raw_url, allow_http_localhost=True)

    @property
    def name(self) -> str:
        return "Ollama (local)"

    @property
    def default_model(self) -> str:
        return "llama3.2"

    def complete(self, system: str, user: str, model: str, max_tokens: int, timeout: int) -> str:
        payload = {
            "model": model,
            "stream": False,
            "options": {"num_predict": max_tokens},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        try:
            body = _http_post(
                url=f"{self._base_url}/api/chat",
                headers={"Content-Type": "application/json"},
                payload=payload,
                timeout=timeout,
            )
        except ConnectionError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self._base_url}. "
                "Make sure Ollama is running: https://ollama.ai\n"
                f"Then pull a model: ollama pull {model}"
            ) from None

        try:
            data = json.loads(body)
            return data["message"]["content"]
        except (json.JSONDecodeError, KeyError):
            raise RuntimeError("Unexpected response format from Ollama.") from None

    def list_models(self) -> list:
        """List available models in the local Ollama instance."""
        with httpx.Client(timeout=10, verify=True, follow_redirects=False) as client:
            response = client.get(f"{self._base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
