"""OpenAI provider for traceback-ai."""

from __future__ import annotations

import json
import os

from .base import BaseProvider, _http_post, validate_base_url


class OpenAIProvider(BaseProvider):
    """Calls the OpenAI chat completions API directly via httpx."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY") or ""
        self._base_url = validate_base_url(
            base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
        )

    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def default_model(self) -> str:
        return "gpt-4o-mini"

    def complete(self, system: str, user: str, model: str, max_tokens: int, timeout: int) -> str:
        if not self._api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key= to traceback_ai.configure()."
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
            raise RuntimeError("Unexpected response format from OpenAI API.") from None
