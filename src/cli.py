"""Command-line interface for traceback-ai."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

console = Console()
err_console = Console(stderr=True)


@click.group()
@click.version_option(package_name="traceback-ai")
def cli() -> None:
    """traceback-ai — AI-powered Python exception debugger.

    \b
    Examples:
        # Analyze a saved traceback from a log file
        tbai analyze error.log

        # Run a Python script with AI debugging enabled
        tbai run my_script.py

        # Check your configuration
        tbai config

        # List available Ollama models
        tbai ollama-models
    """


@cli.command()
@click.argument("file", type=click.Path(exists=True, readable=True))
@click.option(
    "--provider", "-p", default=None, help="LLM provider: openai, anthropic, ollama, auto"
)
@click.option("--model", "-m", default=None, help="Model name")
@click.option("--api-key", default=None, envvar="TBAI_API_KEY", help="API key")
@click.option("--no-fix", is_flag=True, default=False, help="Skip the fix code block")
@click.option("--interactive", "-i", is_flag=True, default=False, help="Ask follow-up questions")
def analyze(
    file: str,
    provider: Optional[str],
    model: Optional[str],
    api_key: Optional[str],
    no_fix: bool,
    interactive: bool,
) -> None:
    """Analyze a saved traceback from a file.

    \b
    FILE can be a .log, .txt, or any file containing a Python traceback.

    \b
    Examples:
        tbai analyze error.log
        tbai analyze crash.txt --provider anthropic
        tbai analyze error.log --interactive
    """
    from .config import configure
    from .context import context_from_string
    from .analyzer import run_analysis, _resolve_provider
    from .formatter import print_analysis, print_thinking, print_error

    updates = {
        k: v
        for k, v in {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "show_fix": not no_fix,
            "interactive": interactive,
        }.items()
        if v is not None
    }
    if updates:
        configure(**updates)

    filepath = Path(file)
    max_bytes = 1 * 1024 * 1024  # 1MB — more than enough for any traceback log
    if filepath.stat().st_size > max_bytes:
        err_console.print(
            f"[red]Error:[/red] File is too large ({filepath.stat().st_size // 1024}KB). "
            f"Maximum allowed size is {max_bytes // 1024}KB."
        )
        sys.exit(1)

    content = filepath.read_text(encoding="utf-8", errors="replace")

    if "Traceback" not in content and "Error" not in content:
        err_console.print(
            f"[yellow]Warning:[/yellow] '{file}' doesn't look like a Python traceback. "
            "Trying anyway..."
        )

    from .config import get_config

    cfg = get_config()

    try:
        ctx = context_from_string(content)
        p = _resolve_provider(cfg)
        print_thinking(p.name)
        result = run_analysis(ctx, config=cfg)
        print_analysis(
            result=result,
            exc_type=ctx.exc_type,
            exc_message=ctx.exc_message,
            provider_name=p.name,
            show_fix=cfg.show_fix,
        )

        if interactive:
            from .handler import _run_interactive_session

            _run_interactive_session(ctx, result, cfg)

    except Exception as e:
        err_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("script", type=click.Path(exists=True, readable=True))
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--provider", "-p", default=None, help="LLM provider")
@click.option("--model", "-m", default=None, help="Model name")
@click.option("--show-locals", is_flag=True, default=False, help="Include local variables")
@click.option("--interactive", "-i", is_flag=True, default=False, help="Ask follow-up questions")
def run(
    script: str,
    args: tuple,
    provider: Optional[str],
    model: Optional[str],
    show_locals: bool,
    interactive: bool,
) -> None:
    """Run a Python script with AI exception debugging enabled.

    \b
    Warning: the script is executed directly in the current process with
    your full environment. Only run scripts you trust.

    \b
    Examples:
        tbai run my_script.py
        tbai run my_script.py -- --my-arg value
        tbai run my_script.py --show-locals --interactive
    """
    import runpy
    import traceback_ai

    updates = {
        k: v
        for k, v in {
            "provider": provider,
            "model": model,
            "show_locals": show_locals or None,
            "interactive": interactive or None,
        }.items()
        if v is not None
    }

    traceback_ai.install(**updates)

    # Patch sys.argv so the script sees its own args
    sys.argv = [script, *args]

    try:
        runpy.run_path(script, run_name="__main__")
    except SystemExit:
        pass  # Let SystemExit propagate normally


@cli.command()
def config() -> None:
    """Show the current traceback-ai configuration."""
    from .config import get_config
    import os

    cfg = get_config()

    console.print("\n[bold cyan]traceback-ai configuration[/bold cyan]\n")

    rows = [
        ("provider", cfg.provider),
        ("model", cfg.model or "[dim](auto)[/dim]"),
        ("context_lines", str(cfg.context_lines)),
        ("show_locals", str(cfg.show_locals)),
        ("show_fix", str(cfg.show_fix)),
        ("interactive", str(cfg.interactive)),
        ("redact_secrets", str(cfg.redact_secrets)),
        ("timeout", f"{cfg.timeout}s"),
        ("max_output_tokens", str(cfg.max_output_tokens)),
    ]

    for key, value in rows:
        console.print(f"  [bold]{key:<22}[/bold] {value}")

    # Show detected API keys (masked)
    console.print()
    console.print("[bold cyan]Detected API keys[/bold cyan]\n")

    for env_var in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GROQ_API_KEY",
        "CEREBRAS_API_KEY",
        "TBAI_API_KEY",
    ):
        val = os.getenv(env_var)
        if val:
            masked = val[:8] + "..." + val[-4:] if len(val) > 12 else "****"
            console.print(f"  [green]✓[/green] {env_var}: {masked}")
        else:
            console.print(f"  [dim]✗ {env_var}: not set[/dim]")

    console.print()


@cli.command("ollama-models")
@click.option("--host", default=None, help="Ollama host URL (default: http://localhost:11434)")
def ollama_models(host: Optional[str]) -> None:
    """List available models in your local Ollama instance."""
    from .providers.ollama import OllamaProvider

    provider = OllamaProvider(base_url=host)
    try:
        models = provider.list_models()
        if models:
            console.print(f"\n[bold]Available Ollama models at {provider._base_url}:[/bold]\n")
            for m in models:
                console.print(f"  • {m}")
            console.print()
        else:
            console.print("[yellow]No models found. Pull one with: ollama pull llama3.2[/yellow]")
    except Exception as e:
        err_console.print(f"[red]Could not connect to Ollama:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
