"""Rich terminal formatting for traceback-ai output."""

from __future__ import annotations

from typing import List, Optional

from rich.columns import Columns
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.text import Text
from rich import box

from .providers.base import AnalysisResult

console = Console(stderr=True)  # Output to stderr to not pollute stdout


def _detect_language(code: Optional[str]) -> str:
    """Guess the language for syntax highlighting."""
    if not code:
        return "python"
    if code.strip().startswith(("$", "#!", "bash", "sh")):
        return "bash"
    return "python"


def print_analysis(
    result: AnalysisResult,
    exc_type: str,
    exc_message: str,
    provider_name: str = "",
    show_fix: bool = True,
) -> None:
    """Print a beautiful AI analysis panel to the terminal.

    Args:
        result: The analysis result from the LLM.
        exc_type: The exception type name (e.g. 'KeyError').
        exc_message: The exception message.
        provider_name: Name of the LLM provider used.
        show_fix: Whether to display the fix code block.
    """
    console.print()

    # Header
    provider_tag = f" [dim]via {escape(provider_name)}[/dim]" if provider_name else ""
    console.print(
        Rule(
            f"[bold cyan] AI Debug Analysis[/bold cyan]{provider_tag}",
            style="cyan",
            align="left",
        )
    )

    # Explanation panel
    explanation_text = Text()
    explanation_text.append(result.explanation)

    console.print(
        Panel(
            explanation_text,
            title=f"[bold red]{escape(exc_type)}[/bold red]: [red]{escape(exc_message[:120])}[/red]",
            border_style="red",
            padding=(1, 2),
        )
    )

    # Causes
    if result.causes:
        console.print()
        console.print("[bold yellow] Likely Causes[/bold yellow]")
        for i, cause in enumerate(result.causes, 1):
            icon = " •" if i > 1 else "[bold] •[/bold]"
            console.print(f"  {icon} {escape(cause)}")

    # Fix description
    if result.fix:
        console.print()
        console.print(f"[bold green] Suggested Fix[/bold green]")
        console.print(f"  {escape(result.fix)}")

    # Fix code
    if show_fix and result.fix_code:
        code = result.fix_code.strip()
        if code and code not in ("None", "null", ""):
            console.print()
            lang = _detect_language(code)
            syntax = Syntax(
                code,
                lang,
                theme="monokai",
                line_numbers=False,
                word_wrap=True,
                padding=(1, 2),
            )
            console.print(Panel(syntax, title="[bold green]Fix Code[/bold green]", border_style="green"))

    # Docs hint
    if result.docs_hint and result.docs_hint not in ("None", "null", ""):
        console.print()
        console.print(f"[dim] Search hint: {escape(result.docs_hint)}[/dim]")

    console.print(Rule(style="cyan"))
    console.print()


def print_followup_answer(question: str, answer: str) -> None:
    """Print a follow-up Q&A exchange."""
    console.print()
    console.print(f"[bold cyan]Q:[/bold cyan] {escape(question)}")
    console.print(
        Panel(
            escape(answer.strip()),
            title="[bold cyan]Answer[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()


def print_error(message: str) -> None:
    """Print an error message (when AI analysis itself fails)."""
    console.print()
    console.print(
        Panel(
            f"[yellow]{escape(message)}[/yellow]",
            title="[bold yellow] traceback-ai[/bold yellow]",
            border_style="yellow",
            padding=(0, 2),
        )
    )
    console.print()


def print_thinking(provider_name: str = "") -> None:
    """Print a 'thinking' status indicator."""
    label = f"Analyzing with {provider_name}..." if provider_name else "Analyzing with AI..."
    console.print(f"\n[dim cyan] {label}[/dim cyan]")


def print_interactive_prompt() -> None:
    """Print the interactive follow-up prompt."""
    console.print(
        "[dim cyan]Ask a follow-up question (or press Enter/type 'exit' to quit):[/dim cyan]"
    )
