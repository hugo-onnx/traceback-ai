"""
traceback-ai: AI-powered Python exception debugger.

When your code raises an exception, traceback-ai automatically sends
the exception context to an LLM and displays a beautiful analysis
explaining what went wrong, the root causes, and a concrete fix.

Quick start:
    import traceback_ai
    traceback_ai.install()
    # Now any unhandled exception will be analyzed by AI
    raise ValueError("oops")  # → AI explains and suggests a fix

Advanced:
    traceback_ai.install(
        provider="anthropic",
        model="claude-sonnet-4-6",
        show_locals=True,
        interactive=True,
    )
"""

from ._version import __version__
from .config import Config, configure
from .handler import analyze, install, uninstall

__all__ = [
    "__version__",
    "install",
    "uninstall",
    "analyze",
    "configure",
    "Config",
]
