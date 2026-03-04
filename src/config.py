"""Global configuration for traceback-ai."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal, Optional

Provider = Literal["openai", "anthropic", "ollama", "groq", "cerebras", "auto"]


@dataclass
class Config:
    """Configuration for traceback-ai.

    All fields can also be set via environment variables with the TBAI_ prefix.
    For example: TBAI_PROVIDER=anthropic, TBAI_MODEL=claude-sonnet-4-6
    """

    provider: Provider = field(default_factory=lambda: os.getenv("TBAI_PROVIDER", "auto"))  # type: ignore[assignment]
    """LLM provider to use. 'auto' selects based on available API keys."""

    model: Optional[str] = field(default_factory=lambda: os.getenv("TBAI_MODEL"))
    """Model name. If None, uses the provider's recommended default."""

    api_key: Optional[str] = field(default_factory=lambda: os.getenv("TBAI_API_KEY"))
    """API key. Falls back to OPENAI_API_KEY / ANTHROPIC_API_KEY if not set."""

    base_url: Optional[str] = field(default_factory=lambda: os.getenv("TBAI_BASE_URL"))
    """Custom base URL (useful for Ollama or compatible APIs)."""

    context_lines: int = field(
        default_factory=lambda: int(os.getenv("TBAI_CONTEXT_LINES", "15"))
    )
    """Number of source code lines to include around the error location."""

    show_locals: bool = field(
        default_factory=lambda: os.getenv("TBAI_SHOW_LOCALS", "false").lower() == "true"
    )
    """Include local variable values in the analysis context."""

    show_fix: bool = field(
        default_factory=lambda: os.getenv("TBAI_SHOW_FIX", "true").lower() != "false"
    )
    """Show the suggested fix code block."""

    interactive: bool = field(
        default_factory=lambda: os.getenv("TBAI_INTERACTIVE", "false").lower() == "true"
    )
    """After analysis, allow asking follow-up questions."""

    redact_secrets: bool = field(
        default_factory=lambda: os.getenv("TBAI_REDACT_SECRETS", "true").lower() != "false"
    )
    """Automatically redact likely secrets/API keys from variable values."""

    timeout: int = field(
        default_factory=lambda: int(os.getenv("TBAI_TIMEOUT", "30"))
    )
    """HTTP request timeout in seconds."""

    max_output_tokens: int = field(
        default_factory=lambda: int(os.getenv("TBAI_MAX_TOKENS", "1024"))
    )
    """Maximum tokens in the LLM response."""

    enabled: bool = True
    """Master switch. Set to False to disable all AI analysis."""


# Module-level singleton
_config = Config()


def configure(**kwargs) -> Config:
    """Update the global configuration.

    Args:
        **kwargs: Any Config field name and value.

    Returns:
        The updated Config instance.

    Example:
        traceback_ai.configure(
            provider="anthropic",
            model="claude-sonnet-4-6",
            show_locals=True,
        )
    """
    global _config
    for key, value in kwargs.items():
        if not hasattr(_config, key):
            raise ValueError(f"Unknown config key: {key!r}. Valid keys: {list(Config.__dataclass_fields__)}")
        setattr(_config, key, value)
    return _config


def get_config() -> Config:
    """Get the current global configuration."""
    return _config
