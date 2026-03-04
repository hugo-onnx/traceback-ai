"""Groq provider for traceback-ai."""

from __future__ import annotations

import json
import os

from .base import BaseProvider, _http_post, validate_base_url

_DEFAULT_BASE_URL = "https://api.groq.com/openai"


class GroqProvider(BaseProvider):
    """Calls the Groq chat completions API directly via httpx.

    Groq runs open-source models (Llama, Mixtral, Gemma) on custom LPU hardware,
    delivering significantly faster inference than standard GPU providers.

    Get a free API key at https://console.groq.com
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self._api_key = api_key or os.getenv("GROQ_API_KEY") or ""
        self._base_url = validate_base_url(base_url or _DEFAULT_BASE_URL)

    @property
    def name(self) -> str:
        return "Groq"

    @property
    def default_model(self) -> str:
        return "llama-3.1-8b-instant"

    def complete(self, system: str, user: str, model: str, max_tokens: int, timeout: int) -> str:
        if not self._api_key:
            raise ValueError(
                "Groq API key not found. Set GROQ_API_KEY environment variable "
                "or pass api_key= to traceback_ai.configure(). "
                "Get a free key at https://console.groq.com"
            )

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }

        body = _http_post(
            url=f"{self._base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            payload=payload,
            timeout=timeout,
        )

        try:
            data = json.loads(body)
            return data["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError):
            raise RuntimeError("Unexpected response format from Groq API.") from None
