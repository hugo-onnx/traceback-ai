"""Tests for traceback_ai.analyzer module."""

import sys
import pytest
from unittest.mock import MagicMock, patch

from traceback_ai.config import Config
from traceback_ai.context import build_context
from traceback_ai.analyzer import run_analysis, run_followup, _resolve_provider
from traceback_ai.providers.base import AnalysisResult


def _make_ctx():
    try:
        raise KeyError("user_id")
    except KeyError:
        exc_type, exc_value, exc_tb = sys.exc_info()
    return build_context(exc_type, exc_value, exc_tb)


class TestResolveProvider:
    def test_auto_selects_anthropic_when_key_set(self):
        import os

        cfg = Config()
        cfg.provider = "auto"
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            # Remove OpenAI key to ensure Anthropic is picked
            env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
            env["ANTHROPIC_API_KEY"] = "test-key"
            with patch.dict(os.environ, env, clear=True):
                provider = _resolve_provider(cfg)
                assert provider.name == "Anthropic"

    def test_auto_selects_openai_when_key_set(self):
        import os

        cfg = Config()
        cfg.provider = "auto"
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "TBAI_API_KEY")
        }
        env["OPENAI_API_KEY"] = "sk-test"
        with patch.dict(os.environ, env, clear=True):
            provider = _resolve_provider(cfg)
            assert provider.name == "OpenAI"

    def test_auto_falls_back_to_ollama(self):
        import os

        cfg = Config()
        cfg.provider = "auto"
        env = {
            k: v
            for k, v in os.environ.items()
            if k
            not in (
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "GROQ_API_KEY",
                "CEREBRAS_API_KEY",
                "TBAI_API_KEY",
            )
        }
        with patch.dict(os.environ, env, clear=True):
            provider = _resolve_provider(cfg)
            assert "Ollama" in provider.name

    def test_explicit_provider(self):
        cfg = Config()
        cfg.provider = "ollama"
        provider = _resolve_provider(cfg)
        assert "Ollama" in provider.name

    def test_auto_selects_groq_when_key_set(self):
        import os

        cfg = Config()
        cfg.provider = "auto"
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "TBAI_API_KEY")
        }
        env["GROQ_API_KEY"] = "gsk_test"
        with patch.dict(os.environ, env, clear=True):
            provider = _resolve_provider(cfg)
            assert provider.name == "Groq"

    def test_auto_selects_cerebras_when_key_set(self):
        import os

        cfg = Config()
        cfg.provider = "auto"
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY", "TBAI_API_KEY")
        }
        env["CEREBRAS_API_KEY"] = "csk_test"
        with patch.dict(os.environ, env, clear=True):
            provider = _resolve_provider(cfg)
            assert provider.name == "Cerebras"

    def test_explicit_groq(self):
        cfg = Config()
        cfg.provider = "groq"
        provider = _resolve_provider(cfg)
        assert provider.name == "Groq"

    def test_explicit_cerebras(self):
        cfg = Config()
        cfg.provider = "cerebras"
        provider = _resolve_provider(cfg)
        assert provider.name == "Cerebras"

    def test_unknown_provider_raises(self):
        cfg = Config()
        cfg.provider = "unknown_provider"  # type: ignore
        with pytest.raises(ValueError, match="Unknown provider"):
            _resolve_provider(cfg)


class TestRunAnalysis:
    def test_returns_analysis_result(self):
        ctx = _make_ctx()
        cfg = Config()
        cfg.provider = "openai"
        cfg.model = "gpt-4o-mini"

        mock_provider = MagicMock()
        mock_provider.analyze.return_value = AnalysisResult(
            explanation="KeyError: key not found",
            causes=["Key was never added"],
            fix="Check if key exists before accessing",
            fix_code="value = d.get('user_id')",
        )

        with patch("traceback_ai.analyzer._resolve_provider", return_value=mock_provider):
            result = run_analysis(ctx, config=cfg)

        assert isinstance(result, AnalysisResult)
        assert result.explanation == "KeyError: key not found"
        assert mock_provider.analyze.called

    def test_uses_global_config_when_none(self):
        ctx = _make_ctx()
        mock_provider = MagicMock()
        mock_provider.analyze.return_value = AnalysisResult(
            explanation="test", causes=[], fix="test"
        )
        with patch("traceback_ai.analyzer._resolve_provider", return_value=mock_provider):
            result = run_analysis(ctx, config=None)
        assert isinstance(result, AnalysisResult)


class TestRunFollowup:
    def test_returns_string(self):
        ctx = _make_ctx()
        initial = AnalysisResult(explanation="test", causes=[], fix="test")
        cfg = Config()
        cfg.provider = "openai"

        mock_provider = MagicMock()
        mock_provider.followup.return_value = "You should use dict.get() instead."

        with patch("traceback_ai.analyzer._resolve_provider", return_value=mock_provider):
            answer = run_followup(ctx, initial, "How do I prevent this?", config=cfg)

        assert isinstance(answer, str)
        assert "dict.get()" in answer
