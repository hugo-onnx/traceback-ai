"""Tests for traceback_ai.config module."""

import os
import pytest
from unittest.mock import patch
from traceback_ai.config import Config, configure, get_config


class TestConfig:
    def test_defaults(self):
        with patch.dict(os.environ, {}, clear=False):
            cfg = Config()
            assert cfg.show_fix is True
            assert cfg.redact_secrets is True
            assert cfg.context_lines == 15
            assert cfg.timeout == 30

    def test_env_var_override(self):
        with patch.dict(os.environ, {"TBAI_PROVIDER": "anthropic", "TBAI_CONTEXT_LINES": "30"}):
            cfg = Config()
            assert cfg.provider == "anthropic"
            assert cfg.context_lines == 30

    def test_configure_updates_global(self):
        original_provider = get_config().provider
        configure(context_lines=25)
        assert get_config().context_lines == 25
        # Cleanup
        configure(context_lines=15)

    def test_configure_invalid_key_raises(self):
        with pytest.raises(ValueError, match="Unknown config key"):
            configure(nonexistent_option=True)

    def test_configure_returns_config(self):
        result = configure(show_fix=True)
        assert isinstance(result, Config)
