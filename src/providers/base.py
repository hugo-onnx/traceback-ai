"""Base provider interface and shared HTTP utilities for traceback-ai."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

SYSTEM_PROMPT = """\
You are an expert Python debugger helping a developer understand and fix an exception.
Be concise, practical, and specific. Avoid generic advice.
Always respond with valid JSON matching the schema provided.\
"""

ANALYSIS_PROMPT_TEMPLATE = """\
A Python program raised an exception. Analyze it and help the developer fix it.

{context}

Respond ONLY with a JSON object in this exact format:
{{
  "explanation": "Clear explanation of what went wrong in 2-3 sentences. Be specific about the actual error.",
  "causes": [
    "Most likely cause",
    "Second possible cause (if applicable)",
    "Third possible cause (if applicable)"
  ],
  "fix": "One-sentence description of how to fix it",
  "fix_code": "# Working Python code that fixes the issue\\n...",
  "docs_hint": "Optional: relevant Python docs or Stack Overflow search terms"
}}

Rules:
- causes: 1-3 items, most likely first
- fix_code: minimal, runnable code snippet (not the full program)
- docs_hint: null if not applicable
- All strings must be valid JSON (escape special characters)\
"""

FOLLOWUP_PROMPT_TEMPLATE = """\
The developer has a follow-up question about this Python exception:

{context}

Previous analysis:
{previous_analysis}

Developer's question:
{question}

Answer concisely and practically. Focus on actionable advice.\
"""

# Maximum response body size to read from LLM APIs (4MB)
_MAX_RESPONSE_BYTES = 4 * 1024 * 1024


def validate_base_url(url: str, allow_http_localhost: bool = False) -> str:
    """Validate a provider base URL and return the normalized form.

    Args:
        url: The URL to validate.
        allow_http_localhost: If True, allow plain HTTP for localhost (Ollama use case).

    Returns:
        Normalized URL with trailing slash removed.

    Raises:
        ValueError: If the URL scheme is insecure for a non-localhost host.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()

    if scheme == "https":
        return url.rstrip("/")

    if scheme == "http":
        if allow_http_localhost and host in ("localhost", "127.0.0.1", "::1", ""):
            return url.rstrip("/")
        raise ValueError(
            f"Insecure HTTP URL not allowed for remote host {host!r}. "
            "Use HTTPS, or tunnel the remote service to localhost."
        )

    raise ValueError(
        f"Invalid URL scheme {scheme!r} in {url!r}. Use https:// (or http://localhost for Ollama)."
    )


def _http_post(
    url: str,
    headers: dict[str, str],
    payload: dict,
    timeout: int,
) -> str:
    """Make a secure HTTP POST to an LLM API and return the response body.

    Security properties enforced:
    - SSL verification always enabled (verify=True)
    - Redirects never followed (prevents API-key exfiltration via redirects)
    - HTTP errors translated to safe messages (no raw response body leaked)
    - Response size capped at _MAX_RESPONSE_BYTES

    Args:
        url: Full endpoint URL (must be HTTPS or localhost HTTP).
        headers: Request headers dict (Authorization, Content-Type, etc.).
        payload: Request body as a dict (will be JSON-encoded).
        timeout: Request timeout in seconds.

    Returns:
        Response body as a string.

    Raises:
        PermissionError: On 401/403 (auth failure).
        RuntimeError: On other HTTP errors or malformed responses.
        TimeoutError: On request timeout.
        ConnectionError: If the host is unreachable.
    """
    with httpx.Client(
        timeout=timeout,
        verify=True,  # Always verify TLS certificates
        follow_redirects=False,  # Never follow redirects (SSRF / key-exfil prevention)
    ) as client:
        try:
            response = client.post(
                url,
                headers=headers,
                content=json.dumps(payload),
            )
        except httpx.TimeoutException:
            raise TimeoutError(f"Request timed out after {timeout}s. Try increasing timeout.") from None
        except httpx.ConnectError as exc:
            host = urlparse(url).netloc
            raise ConnectionError(f"Cannot connect to {host}.") from exc

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code == 401:
            raise PermissionError("Authentication failed — check your API key.") from exc
        if code == 403:
            raise PermissionError("Forbidden — your API key may lack required permissions.") from exc
        if code == 429:
            raise RuntimeError("Rate limited — wait a moment and try again.") from exc
        if code >= 500:
            raise RuntimeError(f"Provider server error (HTTP {code}) — try again later.") from exc
        raise RuntimeError(f"API request failed (HTTP {code}).") from exc

    # Guard against absurdly large responses
    body = response.text
    if len(body.encode()) > _MAX_RESPONSE_BYTES:
        raise RuntimeError("Provider response exceeded maximum allowed size.")

    return body


@dataclass
class AnalysisResult:
    """Structured result from the LLM analysis."""

    explanation: str
    causes: list[str]
    fix: str
    fix_code: str | None = None
    docs_hint: str | None = None
    raw_response: str = ""

    @classmethod
    def from_json(cls, data: dict, raw: str = "") -> AnalysisResult:
        return cls(
            explanation=data.get("explanation", ""),
            causes=data.get("causes", []),
            fix=data.get("fix", ""),
            fix_code=data.get("fix_code") or None,
            docs_hint=data.get("docs_hint") or None,
            raw_response=raw,
        )

    @classmethod
    def from_text(cls, text: str) -> AnalysisResult:
        """Parse a JSON response, handling common LLM formatting quirks."""
        raw = text

        # Strip markdown code blocks
        text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text.strip(), flags=re.MULTILINE)

        # Find first JSON object in the response
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            text = match.group(0)

        try:
            data = json.loads(text)
            return cls.from_json(data, raw=raw)
        except json.JSONDecodeError:
            # Do NOT expose the raw LLM response — it may contain error details
            # from the API (rate-limit messages, auth hints, etc.)
            return cls(
                explanation=(
                    "The AI provider returned an unexpected response format. "
                    "Check your API key and model name, then try again."
                ),
                causes=["API response was not valid JSON"],
                fix="Verify your API key and model name are correct.",
                raw_response=raw,  # Kept for debugging, not shown to user by default
            )


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model identifier for this provider."""
        ...

    @abstractmethod
    def complete(self, system: str, user: str, model: str, max_tokens: int, timeout: int) -> str:
        """Send a completion request and return the response text.

        Args:
            system: System prompt.
            user: User message.
            model: Model identifier.
            max_tokens: Maximum response tokens.
            timeout: Request timeout in seconds.

        Returns:
            The model's response text.
        """
        ...

    def analyze(
        self,
        context_text: str,
        model: str | None = None,
        max_tokens: int = 1024,
        timeout: int = 30,
    ) -> AnalysisResult:
        """Analyze an exception context and return structured results."""
        user_prompt = ANALYSIS_PROMPT_TEMPLATE.format(context=context_text)
        response = self.complete(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            model=model or self.default_model,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        return AnalysisResult.from_text(response)

    def followup(
        self,
        context_text: str,
        previous_analysis: str,
        question: str,
        model: str | None = None,
        max_tokens: int = 512,
        timeout: int = 30,
    ) -> str:
        """Answer a follow-up question about the exception."""
        user_prompt = FOLLOWUP_PROMPT_TEMPLATE.format(
            context=context_text,
            previous_analysis=previous_analysis,
            question=question,
        )
        return self.complete(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            model=model or self.default_model,
            max_tokens=max_tokens,
            timeout=timeout,
        )
