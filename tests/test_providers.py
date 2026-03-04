"""Tests for provider implementations."""

import json
import pytest
from unittest.mock import MagicMock, patch
from traceback_ai.providers.base import AnalysisResult, BaseProvider, validate_base_url
from traceback_ai.providers.openai import OpenAIProvider
from traceback_ai.providers.anthropic import AnthropicProvider
from traceback_ai.providers.ollama import OllamaProvider
from traceback_ai.providers.groq import GroqProvider
from traceback_ai.providers.cerebras import CerebrasProvider

# Each provider imports _http_post into its own namespace via `from base import _http_post`,
# so we must patch within each provider's module namespace for the mock to intercept calls.
_PATCH = {
    "openai": "traceback_ai.providers.openai._http_post",
    "anthropic": "traceback_ai.providers.anthropic._http_post",
    "ollama": "traceback_ai.providers.ollama._http_post",
    "groq": "traceback_ai.providers.groq._http_post",
    "cerebras": "traceback_ai.providers.cerebras._http_post",
}

_VALID_JSON = '{"explanation": "test", "causes": ["c1"], "fix": "f1"}'


# ─── validate_base_url ────────────────────────────────────────────────────────


class TestValidateBaseUrl:
    def test_https_accepted(self):
        assert validate_base_url("https://api.openai.com") == "https://api.openai.com"

    def test_trailing_slash_stripped(self):
        assert validate_base_url("https://api.openai.com/") == "https://api.openai.com"

    def test_http_localhost_allowed_when_permitted(self):
        result = validate_base_url("http://localhost:11434", allow_http_localhost=True)
        assert result == "http://localhost:11434"

    def test_http_localhost_rejected_by_default(self):
        with pytest.raises(ValueError, match="Insecure HTTP"):
            validate_base_url("http://localhost:11434", allow_http_localhost=False)

    def test_http_remote_always_rejected(self):
        with pytest.raises(ValueError, match="Insecure HTTP"):
            validate_base_url("http://api.openai.com", allow_http_localhost=True)

    def test_invalid_scheme_rejected(self):
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            validate_base_url("ftp://example.com")


# ─── AnalysisResult ───────────────────────────────────────────────────────────


class TestAnalysisResult:
    def test_from_valid_json(self):
        data = {
            "explanation": "The key does not exist.",
            "causes": ["Key was never added", "Typo in key name"],
            "fix": "Check if the key exists first.",
            "fix_code": "if 'key' in d:\n    val = d['key']",
            "docs_hint": "dict.get() method",
        }
        result = AnalysisResult.from_json(data)
        assert result.explanation == "The key does not exist."
        assert len(result.causes) == 2
        assert result.fix_code is not None

    def test_from_text_with_markdown_fence(self):
        text = """```json
{
  "explanation": "Test explanation",
  "causes": ["cause 1"],
  "fix": "test fix",
  "fix_code": "x = 1"
}
```"""
        result = AnalysisResult.from_text(text)
        assert result.explanation == "Test explanation"
        assert result.causes == ["cause 1"]

    def test_from_text_fallback_is_safe(self):
        """Fallback must NOT expose raw LLM response (could contain API error details)."""
        raw = "Rate limit exceeded. Your quota is $0.00. Contact billing@openai.com."
        result = AnalysisResult.from_text(raw)
        # Safe generic message — not the raw API error
        assert "Rate limit" not in result.explanation
        assert "billing" not in result.explanation
        # Raw is stored internally for debugging but not shown to user
        assert result.raw_response == raw

    def test_from_text_extracts_embedded_json(self):
        text = """Here is some preamble.
{"explanation": "embedded", "causes": ["c1"], "fix": "f1"}
And some trailing text."""
        result = AnalysisResult.from_text(text)
        assert result.explanation == "embedded"

    def test_null_fields_normalized(self):
        data = {"explanation": "test", "causes": ["c1"], "fix": "f1", "docs_hint": None}
        result = AnalysisResult.from_json(data)
        assert result.docs_hint is None


# ─── OpenAI ───────────────────────────────────────────────────────────────────


class TestOpenAIProvider:
    def test_name(self):
        assert OpenAIProvider(api_key="test-key").name == "OpenAI"

    def test_default_model(self):
        assert "gpt" in OpenAIProvider(api_key="test-key").default_model

    def test_missing_api_key_raises(self):
        provider = OpenAIProvider(api_key="")
        with pytest.raises(ValueError, match="API key"):
            provider.complete("sys", "user", "gpt-4o-mini", 100, 10)

    def test_invalid_base_url_raises(self):
        with pytest.raises(ValueError):
            OpenAIProvider(api_key="sk-test", base_url="http://remote.example.com")

    def test_complete_success(self):
        provider = OpenAIProvider(api_key="sk-test")
        body = json.dumps({"choices": [{"message": {"content": _VALID_JSON}}]})
        with patch(_PATCH["openai"], return_value=body):
            result = provider.complete("sys", "user", "gpt-4o-mini", 100, 10)
        assert "explanation" in result

    def test_complete_sends_json_mode(self):
        provider = OpenAIProvider(api_key="sk-test")
        body = json.dumps({"choices": [{"message": {"content": "{}"}}]})
        with patch(_PATCH["openai"], return_value=body) as m:
            provider.complete("sys", "user", "gpt-4o-mini", 100, 10)
        assert m.call_args.kwargs["payload"]["response_format"]["type"] == "json_object"

    def test_complete_raises_on_malformed_response(self):
        provider = OpenAIProvider(api_key="sk-test")
        with patch(_PATCH["openai"], return_value="not json at all"):
            with pytest.raises(RuntimeError, match="Unexpected response"):
                provider.complete("sys", "user", "gpt-4o-mini", 100, 10)


# ─── Anthropic ────────────────────────────────────────────────────────────────


class TestAnthropicProvider:
    def test_name(self):
        assert AnthropicProvider(api_key="test-key").name == "Anthropic"

    def test_default_model(self):
        assert "claude" in AnthropicProvider(api_key="test-key").default_model

    def test_missing_api_key_raises(self):
        provider = AnthropicProvider(api_key="")
        with pytest.raises(ValueError, match="API key"):
            provider.complete("sys", "user", "claude-haiku-4-5-20251001", 100, 10)

    def test_invalid_base_url_raises(self):
        with pytest.raises(ValueError):
            AnthropicProvider(api_key="test", base_url="http://remote.example.com")

    def test_complete_success(self):
        provider = AnthropicProvider(api_key="test-key")
        body = json.dumps({"content": [{"text": _VALID_JSON}]})
        with patch(_PATCH["anthropic"], return_value=body):
            result = provider.complete("sys", "user", "claude-haiku-4-5-20251001", 100, 10)
        assert "explanation" in result

    def test_uses_correct_api_version_header(self):
        provider = AnthropicProvider(api_key="test-key")
        body = json.dumps({"content": [{"text": "{}"}]})
        with patch(_PATCH["anthropic"], return_value=body) as m:
            provider.complete("sys", "user", "claude-haiku-4-5-20251001", 100, 10)
        assert "anthropic-version" in m.call_args.kwargs["headers"]

    def test_complete_raises_on_malformed_response(self):
        provider = AnthropicProvider(api_key="test-key")
        with patch(_PATCH["anthropic"], return_value="not json"):
            with pytest.raises(RuntimeError, match="Unexpected response"):
                provider.complete("sys", "user", "claude-haiku-4-5-20251001", 100, 10)


# ─── Ollama ───────────────────────────────────────────────────────────────────


class TestOllamaProvider:
    def test_name(self):
        assert "Ollama" in OllamaProvider().name

    def test_default_model(self):
        assert OllamaProvider().default_model != ""

    def test_localhost_http_allowed(self):
        provider = OllamaProvider(base_url="http://localhost:11434")
        assert "localhost" in provider._base_url

    def test_remote_http_rejected(self):
        with pytest.raises(ValueError, match="Insecure HTTP"):
            OllamaProvider(base_url="http://remote-server.example.com:11434")

    def test_connection_error_gives_helpful_message(self):
        provider = OllamaProvider(base_url="http://localhost:11434")
        with patch(_PATCH["ollama"], side_effect=ConnectionError("refused")):
            with pytest.raises(ConnectionError, match="Ollama"):
                provider.complete("sys", "user", "llama3.2", 100, 10)

    def test_complete_success(self):
        provider = OllamaProvider()
        body = json.dumps({"message": {"content": _VALID_JSON}})
        with patch(_PATCH["ollama"], return_value=body):
            result = provider.complete("sys", "user", "llama3.2", 100, 10)
        assert result != ""


# ─── Groq ─────────────────────────────────────────────────────────────────────


class TestGroqProvider:
    def test_name(self):
        assert GroqProvider(api_key="test").name == "Groq"

    def test_default_model(self):
        assert "llama" in GroqProvider(api_key="test").default_model

    def test_missing_api_key_raises(self):
        provider = GroqProvider(api_key="")
        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            provider.complete("sys", "user", "llama-3.1-8b-instant", 100, 10)

    def test_invalid_base_url_raises(self):
        with pytest.raises(ValueError):
            GroqProvider(api_key="gsk_test", base_url="http://remote.example.com")

    def test_complete_success(self):
        provider = GroqProvider(api_key="gsk_test")
        body = json.dumps({"choices": [{"message": {"content": _VALID_JSON}}]})
        with patch(_PATCH["groq"], return_value=body):
            result = provider.complete("sys", "user", "llama-3.1-8b-instant", 100, 10)
        assert "explanation" in result

    def test_uses_groq_base_url(self):
        provider = GroqProvider(api_key="gsk_test")
        body = json.dumps({"choices": [{"message": {"content": "{}"}}]})
        with patch(_PATCH["groq"], return_value=body) as m:
            provider.complete("sys", "user", "llama-3.1-8b-instant", 100, 10)
        assert "groq.com" in m.call_args.kwargs["url"]

    def test_sends_json_mode(self):
        provider = GroqProvider(api_key="gsk_test")
        body = json.dumps({"choices": [{"message": {"content": "{}"}}]})
        with patch(_PATCH["groq"], return_value=body) as m:
            provider.complete("sys", "user", "llama-3.1-8b-instant", 100, 10)
        assert m.call_args.kwargs["payload"]["response_format"]["type"] == "json_object"


# ─── Cerebras ─────────────────────────────────────────────────────────────────


class TestCerebrasProvider:
    def test_name(self):
        assert CerebrasProvider(api_key="test").name == "Cerebras"

    def test_default_model(self):
        assert CerebrasProvider(api_key="test").default_model != ""

    def test_missing_api_key_raises(self):
        provider = CerebrasProvider(api_key="")
        with pytest.raises(ValueError, match="CEREBRAS_API_KEY"):
            provider.complete("sys", "user", "llama3.1-8b", 100, 10)

    def test_invalid_base_url_raises(self):
        with pytest.raises(ValueError):
            CerebrasProvider(api_key="csk_test", base_url="http://remote.example.com")

    def test_complete_success(self):
        provider = CerebrasProvider(api_key="csk_test")
        body = json.dumps({"choices": [{"message": {"content": _VALID_JSON}}]})
        with patch(_PATCH["cerebras"], return_value=body):
            result = provider.complete("sys", "user", "llama3.1-8b", 100, 10)
        assert "explanation" in result

    def test_uses_cerebras_base_url(self):
        provider = CerebrasProvider(api_key="csk_test")
        body = json.dumps({"choices": [{"message": {"content": "{}"}}]})
        with patch(_PATCH["cerebras"], return_value=body) as m:
            provider.complete("sys", "user", "llama3.1-8b", 100, 10)
        assert "cerebras.ai" in m.call_args.kwargs["url"]
