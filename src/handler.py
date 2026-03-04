"""Exception hook integration for traceback-ai.

This module installs a custom sys.excepthook that automatically
analyzes unhandled Python exceptions with AI.
"""

from __future__ import annotations

import sys
from types import TracebackType

from .config import Config, get_config
from .context import ExceptionContext, build_context

# Save the original excepthook so we can restore it
_original_excepthook = sys.excepthook
_installed = False


def _handle_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType | None,
    config: Config | None = None,
) -> None:
    """The core exception handler — called on unhandled exceptions."""
    cfg = config or get_config()

    # Always print the original traceback first
    _original_excepthook(exc_type, exc_value, exc_tb)

    # Skip if disabled or for keyboard interrupts / system exits
    if not cfg.enabled:
        return
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit, BrokenPipeError)):
        return

    # Lazy imports to keep startup fast
    from .analyzer import _resolve_provider, run_analysis
    from .formatter import (
        print_analysis,
        print_error,
        print_thinking,
    )

    try:
        ctx = build_context(
            exc_type=exc_type,
            exc_value=exc_value,
            exc_tb=exc_tb,
            context_lines=cfg.context_lines,
            show_locals=cfg.show_locals,
            redact_secrets=cfg.redact_secrets,
        )

        provider = _resolve_provider(cfg)
        print_thinking(provider.name)
        result = run_analysis(ctx, config=cfg)
        print_analysis(
            result=result,
            exc_type=exc_type.__name__,
            exc_message=str(exc_value),
            provider_name=provider.name,
            show_fix=cfg.show_fix,
        )

        if cfg.interactive:
            _run_interactive_session(ctx, result, cfg)

    except KeyboardInterrupt:
        pass
    except Exception as analysis_error:
        # Never crash the user's program due to our own error.
        # Truncate and sanitize the error message so internal API details
        # (rate-limit headers, auth hints, etc.) are not exposed verbatim.
        err_msg = str(analysis_error)
        if len(err_msg) > 300:
            err_msg = err_msg[:300] + "…"
        print_error(f"traceback-ai could not analyze this exception: {err_msg}")


def _run_interactive_session(
    ctx: ExceptionContext,
    initial_result,
    config: Config,
) -> None:
    """Run an interactive Q&A session after the initial analysis."""
    from .analyzer import run_followup
    from .formatter import (
        print_error,
        print_followup_answer,
        print_interactive_prompt,
    )

    print_interactive_prompt()

    while True:
        try:
            question = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not question or question.lower() in ("exit", "quit", "q", "bye"):
            break

        try:
            answer = run_followup(ctx, initial_result, question, config=config)
            print_followup_answer(question, answer)
            print_interactive_prompt()
        except Exception as e:
            print_error(f"Could not get answer: {e}")
            break


def install(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    context_lines: int | None = None,
    show_locals: bool | None = None,
    show_fix: bool | None = None,
    interactive: bool | None = None,
    redact_secrets: bool | None = None,
    timeout: int | None = None,
) -> None:
    """Install the AI exception handler.

    After calling this, any unhandled Python exception will be automatically
    analyzed by AI, printing an explanation and suggested fix to the terminal.

    Args:
        provider: LLM provider ('openai', 'anthropic', 'ollama', 'auto').
        model: Model name (e.g. 'gpt-4o', 'claude-sonnet-4-6').
        api_key: API key (or set OPENAI_API_KEY / ANTHROPIC_API_KEY env vars).
        base_url: Custom API base URL (useful for custom endpoints or Ollama).
        context_lines: Lines of source code to include around the error.
        show_locals: Include local variable values in the analysis.
        show_fix: Display the suggested fix code block.
        interactive: After analysis, prompt for follow-up questions.
        redact_secrets: Redact likely secrets from variable values.
        timeout: HTTP request timeout in seconds.

    Example:
        import traceback_ai
        traceback_ai.install()  # Uses OPENAI_API_KEY or ANTHROPIC_API_KEY

        # Advanced:
        traceback_ai.install(provider="anthropic", interactive=True)
    """
    global _installed

    # Apply any provided settings to the global config
    updates = {
        k: v
        for k, v in {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "base_url": base_url,
            "context_lines": context_lines,
            "show_locals": show_locals,
            "show_fix": show_fix,
            "interactive": interactive,
            "redact_secrets": redact_secrets,
            "timeout": timeout,
        }.items()
        if v is not None
    }

    if updates:
        from .config import configure

        configure(**updates)

    sys.excepthook = _handle_exception
    _installed = True

    # IPython integration
    _try_install_ipython()


def uninstall() -> None:
    """Remove the AI exception handler and restore the original excepthook."""
    global _installed
    sys.excepthook = _original_excepthook
    _installed = False


def analyze(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType | None,
) -> None:
    """Manually analyze an exception (without installing the global hook).

    This is useful for analyzing exceptions caught in try/except blocks.

    Args:
        exc_type: The exception class.
        exc_value: The exception instance.
        exc_tb: The traceback object.

    Example:
        import traceback_ai
        try:
            risky_operation()
        except Exception:
            import sys
            traceback_ai.analyze(*sys.exc_info())
    """
    _handle_exception(exc_type, exc_value, exc_tb)


def _try_install_ipython() -> None:
    """Install a custom exception handler in IPython if running in one."""
    try:
        ip = get_ipython()  # type: ignore[name-defined]  # noqa: F821
        if ip is None:
            return

        cfg = get_config()

        def ipython_handler(self, etype, value, tb, tb_offset=None):
            self.showtraceback()
            _handle_exception(etype, value, tb, config=cfg)

        ip.set_custom_exc((Exception,), ipython_handler)
    except (NameError, Exception):
        pass  # Not in IPython, that's fine
