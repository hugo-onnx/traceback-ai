"""Anthropic provider for traceback-ai."""

from __future__ import annotations

import json
import os

from .base import BaseProvider, _http_post, validate_base_url


class AnthropicProvider(BaseProvider):
    """Calls the Anthropic Messages API directly via httpx."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or ""
        self._base_url = validate_base_url(base_url or "https://api.anthropic.com")

    @property
    def name(self) -> str:
        return "Anthropic"

    @property
    def default_model(self) -> str:
        return "claude-haiku-4-5-20251001"

    def complete(self, system: str, user: str, model: str, max_tokens: int, timeout: int) -> str:
        if not self._api_key:
            raise ValueError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key= to traceback_ai.configure()."
            )

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [
                {"role": "user", "content": user},
            ],
        }

        body = _http_post(
            url=f"{self._base_url}/v1/messages",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            payload=payload,
            timeout=timeout,
        )

        try:
            data = json.loads(body)
            return data["content"][0]["text"]
        except (json.JSONDecodeError, KeyError, IndexError):
            raise RuntimeError("Unexpected response format from Anthropic API.") from None
