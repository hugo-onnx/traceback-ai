"""Core analysis logic — selects provider and runs the LLM."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .config import Config, get_config
from .context import ExceptionContext
from .providers.base import AnalysisResult, BaseProvider

if TYPE_CHECKING:
    pass


def _resolve_provider(config: Config) -> BaseProvider:
    """Instantiate the correct provider based on config and available API keys."""
    from .providers.anthropic import AnthropicProvider
    from .providers.cerebras import CerebrasProvider
    from .providers.groq import GroqProvider
    from .providers.ollama import OllamaProvider
    from .providers.openai import OpenAIProvider

    provider_name = config.provider
    api_key = config.api_key
    base_url = config.base_url

    if provider_name == "auto":
        # Auto-detect: Anthropic → OpenAI → Groq → Cerebras → Ollama
        if api_key or os.getenv("ANTHROPIC_API_KEY"):
            provider_name = "anthropic"
        elif os.getenv("OPENAI_API_KEY"):
            provider_name = "openai"
        elif os.getenv("GROQ_API_KEY"):
            provider_name = "groq"
        elif os.getenv("CEREBRAS_API_KEY"):
            provider_name = "cerebras"
        else:
            provider_name = "ollama"

    if provider_name == "openai":
        return OpenAIProvider(api_key=api_key or os.getenv("OPENAI_API_KEY"), base_url=base_url)
    elif provider_name == "anthropic":
        return AnthropicProvider(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"), base_url=base_url
        )
    elif provider_name == "groq":
        return GroqProvider(api_key=api_key or os.getenv("GROQ_API_KEY"), base_url=base_url)
    elif provider_name == "cerebras":
        return CerebrasProvider(api_key=api_key or os.getenv("CEREBRAS_API_KEY"), base_url=base_url)
    elif provider_name == "ollama":
        return OllamaProvider(base_url=base_url)
    else:
        raise ValueError(
            f"Unknown provider: {provider_name!r}. "
            "Valid options: 'openai', 'anthropic', 'groq', 'cerebras', 'ollama', 'auto'"
        )


def run_analysis(
    ctx: ExceptionContext,
    config: Config | None = None,
) -> AnalysisResult:
    """Run the full LLM analysis on an exception context.

    Args:
        ctx: The exception context to analyze.
        config: Configuration overrides (uses global config if None).

    Returns:
        An AnalysisResult with explanation, causes, fix, and code.

    Raises:
        Various exceptions if the LLM call fails.
    """
    if config is None:
        config = get_config()

    provider = _resolve_provider(config)
    context_text = ctx.to_prompt_text(
        show_locals=config.show_locals,
        redact_secrets=config.redact_secrets,
    )

    return provider.analyze(
        context_text=context_text,
        model=config.model,
        max_tokens=config.max_output_tokens,
        timeout=config.timeout,
    )


def run_followup(
    ctx: ExceptionContext,
    previous: AnalysisResult,
    question: str,
    config: Config | None = None,
) -> str:
    """Ask a follow-up question after an initial analysis.

    Args:
        ctx: The original exception context.
        previous: The previous analysis result.
        question: The developer's follow-up question.
        config: Configuration overrides.

    Returns:
        The model's answer as plain text.
    """
    if config is None:
        config = get_config()

    provider = _resolve_provider(config)
    context_text = ctx.to_prompt_text(
        show_locals=config.show_locals,
        redact_secrets=config.redact_secrets,
    )
    previous_summary = f"{previous.explanation}\n\nSuggested fix: {previous.fix}"

    return provider.followup(
        context_text=context_text,
        previous_analysis=previous_summary,
        question=question,
        model=config.model,
        max_tokens=config.max_output_tokens,
        timeout=config.timeout,
    )
