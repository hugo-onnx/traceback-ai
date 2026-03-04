"""Extract rich context from Python exceptions for LLM analysis."""

from __future__ import annotations

import linecache
import re
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, List, Optional

# Variable name patterns that suggest the value is a secret
_SECRET_PATTERNS = re.compile(
    r"(password|passwd|secret|api[_-]?key|token|auth|credential|private[_-]?key"
    r"|access[_-]?key|refresh[_-]?token|jwt|certificate|cert|dsn"
    r"|connection[_-]?string|database[_-]?url|db[_-]?url|db[_-]?pass)",
    re.IGNORECASE,
)

# Value prefixes that reliably indicate a secret (checked against the raw string value)
_SECRET_VALUE_PATTERNS = re.compile(
    r"^(sk-|xoxb-|xoxp-|ghp_|ghs_|glpat-|eyJ|AKIA|AIza|-----BEGIN)",
    # OpenAI, Slack (bot/user), GitHub (PAT/app), GitLab, JWT, AWS key, Google API key, PEM
)

# Pattern to detect secrets nested inside dict/object reprs, e.g. {'password': 'hunter2'}
_SECRET_DICT_KEY_PATTERNS = re.compile(
    r"""['"](password|passwd|secret|api[_-]?key|token|auth|credential|private[_-]?key"""
    r"""|access[_-]?key|refresh[_-]?token|jwt|certificate|cert|dsn"""
    r"""|connection[_-]?string|database[_-]?url|db[_-]?url|db[_-]?pass)['"]\s*:""",
    re.IGNORECASE,
)


@dataclass
class FrameInfo:
    """Information about a single stack frame."""

    filename: str
    lineno: int
    function: str
    code_context: str
    locals: Dict[str, str] = field(default_factory=dict)

    @property
    def is_user_code(self) -> bool:
        """True if this frame is in user code (not stdlib/site-packages)."""
        p = Path(self.filename)
        parts = p.parts
        return not any(
            part in ("site-packages", "dist-packages", "lib", "<frozen")
            for part in parts
        ) and self.filename not in ("<stdin>", "<string>", "<console>")


@dataclass
class ExceptionContext:
    """Complete context for an exception, ready for LLM analysis."""

    exc_type: str
    exc_message: str
    traceback_str: str
    frames: List[FrameInfo]
    chained_cause: Optional["ExceptionContext"] = None

    @property
    def error_frame(self) -> Optional[FrameInfo]:
        """The innermost user-code frame where the error occurred."""
        for frame in reversed(self.frames):
            if frame.is_user_code:
                return frame
        return self.frames[-1] if self.frames else None

    def to_prompt_text(self, show_locals: bool = False, redact_secrets: bool = True) -> str:
        """Format the context as a prompt-friendly string."""
        parts: List[str] = []

        # Exception summary
        parts.append(f"## Exception\n**Type:** `{self.exc_type}`\n**Message:** {self.exc_message}")

        # Chained cause
        if self.chained_cause:
            parts.append(
                f"\n## Caused By\n**Type:** `{self.chained_cause.exc_type}`\n"
                f"**Message:** {self.chained_cause.exc_message}"
            )

        # Full traceback
        parts.append(f"\n## Full Traceback\n```\n{self.traceback_str.strip()}\n```")

        # Code context at the error frame
        error_frame = self.error_frame
        if error_frame:
            parts.append(
                f"\n## Error Location\n"
                f"**File:** `{error_frame.filename}` **Line:** {error_frame.lineno} "
                f"**Function:** `{error_frame.function}`\n\n"
                f"```python\n{error_frame.code_context.strip()}\n```"
            )

            if show_locals and error_frame.locals:
                local_lines = []
                for name, value in error_frame.locals.items():
                    # Values are already redacted at extraction time if redact_secrets was set
                    local_lines.append(f"  {name} = {value}")
                if local_lines:
                    parts.append("\n## Local Variables\n```python\n" + "\n".join(local_lines) + "\n```")

        return "\n".join(parts)


def _is_secret(name: str, value: str) -> bool:
    """Heuristic: is this variable likely a secret?

    Checks:
    1. Variable name matches known secret naming conventions.
    2. Value starts with a known secret prefix (e.g. sk-, AKIA, eyJ).
    3. Value's repr contains a dict key that looks like a secret field.
    """
    if _SECRET_PATTERNS.search(name):
        return True
    if _SECRET_VALUE_PATTERNS.match(value):
        return True
    # Catch nested secrets in dicts/objects: {'password': '...', 'api_key': '...'}
    if _SECRET_DICT_KEY_PATTERNS.search(value):
        return True
    return False


def _format_value(value: Any) -> str:
    """Safely format a variable value for display."""
    try:
        s = repr(value)
    except Exception:
        return "<unrepresentable>"
    # Truncate long values
    if len(s) > 200:
        s = s[:200] + "..."
    return s


def _get_source_context(filename: str, lineno: int, context_lines: int) -> str:
    """Get source code lines around a given line number."""
    if filename in ("<stdin>", "<string>", "<console>", "<ipython-input>"):
        return ""

    start = max(1, lineno - context_lines)
    end = lineno + context_lines

    lines = []
    for ln in range(start, end + 1):
        line = linecache.getline(filename, ln)
        if not line:
            continue
        marker = "→ " if ln == lineno else "  "
        lines.append(f"{marker}{ln:4d} │ {line.rstrip()}")

    return "\n".join(lines)


def _extract_frames(
    tb: TracebackType,
    context_lines: int,
    show_locals: bool,
    redact_secrets: bool,
) -> List[FrameInfo]:
    """Walk a traceback and extract frame information."""
    frames: List[FrameInfo] = []

    extracted = traceback.extract_tb(tb)
    # Walk tb to get frame locals
    tb_frame = tb
    frame_locals_list: List[Dict[str, Any]] = []
    while tb_frame is not None:
        frame_locals_list.append(tb_frame.tb_frame.f_locals.copy())
        tb_frame = tb_frame.tb_next

    for i, frame_summary in enumerate(extracted):
        code_context = _get_source_context(frame_summary.filename, frame_summary.lineno, context_lines)

        locals_dict: Dict[str, str] = {}
        if show_locals and i < len(frame_locals_list):
            for name, value in frame_locals_list[i].items():
                if not name.startswith("__"):
                    # Check secret against the raw value (before repr) to catch e.g. "sk-..." strings
                    if redact_secrets and _is_secret(name, str(value)):
                        locals_dict[name] = "[REDACTED]"
                    else:
                        locals_dict[name] = _format_value(value)

        frames.append(
            FrameInfo(
                filename=frame_summary.filename,
                lineno=frame_summary.lineno,
                function=frame_summary.name,
                code_context=code_context,
                locals=locals_dict,
            )
        )

    return frames


def build_context(
    exc_type: type,
    exc_value: BaseException,
    exc_tb: Optional[TracebackType],
    context_lines: int = 15,
    show_locals: bool = False,
    redact_secrets: bool = True,
) -> ExceptionContext:
    """Build a complete ExceptionContext from a Python exception.

    Args:
        exc_type: The exception class.
        exc_value: The exception instance.
        exc_tb: The traceback object.
        context_lines: Lines of source code to include around the error.
        show_locals: Whether to include local variable values.
        redact_secrets: Whether to redact likely secrets from locals.

    Returns:
        A fully populated ExceptionContext.
    """
    # Format the traceback string
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
    traceback_str = "".join(tb_lines)

    frames: List[FrameInfo] = []
    if exc_tb is not None:
        frames = _extract_frames(exc_tb, context_lines, show_locals, redact_secrets)

    # Handle chained exceptions (__cause__ or __context__)
    chained: Optional[ExceptionContext] = None
    cause = exc_value.__cause__ or (
        exc_value.__context__ if not exc_value.__suppress_context__ else None
    )
    if cause is not None and cause is not exc_value:
        cause_type = type(cause)
        cause_tb = cause.__traceback__
        cause_frames: List[FrameInfo] = []
        if cause_tb:
            cause_frames = _extract_frames(cause_tb, context_lines, show_locals, redact_secrets)
        chained = ExceptionContext(
            exc_type=cause_type.__name__,
            exc_message=str(cause),
            traceback_str="".join(traceback.format_exception(cause_type, cause, cause_tb)),
            frames=cause_frames,
        )

    return ExceptionContext(
        exc_type=exc_type.__name__,
        exc_message=str(exc_value),
        traceback_str=traceback_str,
        frames=frames,
        chained_cause=chained,
    )


def context_from_string(traceback_text: str) -> ExceptionContext:
    """Parse an ExceptionContext from a raw traceback string (e.g., from a log file).

    This is used by the CLI to analyze saved tracebacks.
    """
    lines = traceback_text.strip().splitlines()

    exc_type = "UnknownError"
    exc_message = traceback_text

    # Try to parse the last line as "ExcType: message"
    for line in reversed(lines):
        line = line.strip()
        if line and not line.startswith("File ") and not line.startswith("Traceback"):
            if ":" in line:
                parts = line.split(":", 1)
                exc_type = parts[0].strip()
                exc_message = parts[1].strip()
            else:
                exc_type = line
                exc_message = ""
            break

    return ExceptionContext(
        exc_type=exc_type,
        exc_message=exc_message,
        traceback_str=traceback_text,
        frames=[],
    )
