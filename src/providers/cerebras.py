"""Cerebras provider for traceback-ai."""

from __future__ import annotations

import json
import os
from typing import Optional

from .base import BaseProvider, _http_post, validate_base_url

_DEFAULT_BASE_URL = "https://api.cerebras.ai"


class CerebrasProvider(BaseProvider):
    """Calls the Cerebras inference API directly via httpx.

    Cerebras runs models on Wafer-Scale Engine chips, delivering very fast
    inference with a free tier available.

    Get a free API key at https://cloud.cerebras.ai
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self._api_key = api_key or os.getenv("CEREBRAS_API_KEY") or ""
        self._base_url = validate_base_url(base_url or _DEFAULT_BASE_URL)

    @property
    def name(self) -> str:
        return "Cerebras"

    @property
    def default_model(self) -> str:
        return "llama3.1-8b"

    def complete(self, system: str, user: str, model: str, max_tokens: int, timeout: int) -> str:
        if not self._api_key:
            raise ValueError(
                "Cerebras API key not found. Set CEREBRAS_API_KEY environment variable "
                "or pass api_key= to traceback_ai.configure(). "
                "Get a free key at https://cloud.cerebras.ai"
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
            raise RuntimeError("Unexpected response format from Cerebras API.")
