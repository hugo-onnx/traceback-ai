"""Tests for traceback_ai.context module."""

import sys
import pytest
from traceback_ai.context import (
    build_context,
    context_from_string,
    ExceptionContext,
    FrameInfo,
    _is_secret,
    _format_value,
)


def _raise_and_catch(msg="test error", exc_class=ValueError):
    """Helper to create real exception info."""
    try:
        raise exc_class(msg)
    except exc_class:
        return sys.exc_info()


class TestBuildContext:
    def test_basic_exception(self):
        exc_type, exc_value, exc_tb = _raise_and_catch("test message")
        ctx = build_context(exc_type, exc_value, exc_tb)

        assert ctx.exc_type == "ValueError"
        assert ctx.exc_message == "test message"
        assert "ValueError" in ctx.traceback_str
        assert len(ctx.frames) > 0

    def test_key_error(self):
        try:
            d = {}
            _ = d["missing_key"]
        except KeyError:
            exc_type, exc_value, exc_tb = sys.exc_info()

        ctx = build_context(exc_type, exc_value, exc_tb)
        assert ctx.exc_type == "KeyError"

    def test_chained_exception(self):
        try:
            try:
                raise ValueError("original")
            except ValueError as e:
                raise RuntimeError("wrapped") from e
        except RuntimeError:
            exc_type, exc_value, exc_tb = sys.exc_info()

        ctx = build_context(exc_type, exc_value, exc_tb)
        assert ctx.exc_type == "RuntimeError"
        assert ctx.chained_cause is not None
        assert ctx.chained_cause.exc_type == "ValueError"

    def test_error_frame_is_user_code(self):
        exc_type, exc_value, exc_tb = _raise_and_catch()
        ctx = build_context(exc_type, exc_value, exc_tb)
        frame = ctx.error_frame
        # The error frame should be in this test file
        assert frame is not None
        assert "test_context" in frame.filename or "conftest" in frame.filename

    def test_to_prompt_text_contains_exception_info(self):
        exc_type, exc_value, exc_tb = _raise_and_catch("specific message")
        ctx = build_context(exc_type, exc_value, exc_tb)
        text = ctx.to_prompt_text()

        assert "ValueError" in text
        assert "specific message" in text

    def test_to_prompt_text_with_locals(self):
        try:
            my_var = "hello"  # noqa: F841
            raise ValueError("test")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()

        ctx = build_context(exc_type, exc_value, exc_tb, show_locals=True)
        text = ctx.to_prompt_text(show_locals=True)
        # Local variable should appear in the prompt
        assert "my_var" in text or "hello" in text

    def test_secrets_redacted(self):
        import os

        # Use os.getenv so the secret doesn't appear in the source-code context line
        secret = os.getenv("_TBAI_TEST_SECRET_NOT_SET_", "sk-supersecretkey123")
        try:
            api_key = secret  # noqa: F841
            raise ValueError("test")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()

        ctx = build_context(exc_type, exc_value, exc_tb, show_locals=True, redact_secrets=True)
        # The locals dict entry must be redacted
        error_frame = ctx.error_frame
        assert error_frame is not None
        assert error_frame.locals.get("api_key") == "[REDACTED]", (
            f"Expected [REDACTED], got: {error_frame.locals.get('api_key')}"
        )
        assert error_frame.locals.get("secret") == "[REDACTED]", (
            f"secret variable should also be redacted: {error_frame.locals.get('secret')}"
        )

    def test_none_traceback(self):
        ctx = build_context(ValueError, ValueError("test"), None)
        assert ctx.exc_type == "ValueError"
        assert ctx.frames == []


class TestContextFromString:
    def test_basic_traceback(self):
        tb_text = """Traceback (most recent call last):
  File "app.py", line 42, in main
    result = process(data)
  File "app.py", line 17, in process
    return data["key"]
KeyError: 'user_id'
"""
        ctx = context_from_string(tb_text)
        assert ctx.exc_type == "KeyError"
        assert "user_id" in ctx.exc_message
        assert ctx.traceback_str == tb_text

    def test_type_error(self):
        tb_text = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        ctx = context_from_string(tb_text)
        assert ctx.exc_type == "TypeError"

    def test_plain_text_fallback(self):
        ctx = context_from_string("something went wrong")
        assert ctx.exc_type is not None  # Should not crash


class TestIsSecret:
    def test_password_name(self):
        assert _is_secret("password", "mysecret123") is True

    def test_api_key_name(self):
        assert _is_secret("api_key", "somevalue") is True
        assert _is_secret("API_KEY", "somevalue") is True

    def test_openai_prefix(self):
        assert _is_secret("my_key", "sk-abcdef123") is True

    def test_safe_variable(self):
        assert _is_secret("user_name", "alice") is False
        assert _is_secret("count", "42") is False

    def test_github_token(self):
        assert _is_secret("token", "ghp_xxx") is True

    def test_aws_key_value_prefix(self):
        assert _is_secret("key_id", "AKIA1234567890ABCDEF") is True

    def test_pem_key_prefix(self):
        assert _is_secret("cert", "-----BEGIN RSA PRIVATE KEY-----") is True

    def test_nested_dict_password(self):
        # A variable named 'config' containing a secret dict key
        assert _is_secret("config", "{'host': 'db', 'password': 'hunter2'}") is True

    def test_nested_dict_api_key(self):
        assert _is_secret("settings", '{"api_key": "sk-abc", "model": "gpt-4"}') is True

    def test_nested_dict_safe(self):
        assert _is_secret("data", "{'user': 'alice', 'count': 42}") is False

    def test_jwt_prefix(self):
        assert _is_secret("header", "eyJhbGciOiJIUzI1NiJ9.abc.def") is True


class TestFrameInfo:
    def test_user_code_detection(self):
        user_frame = FrameInfo(
            filename="/home/user/project/my_script.py",
            lineno=10,
            function="my_func",
            code_context="",
        )
        assert user_frame.is_user_code is True

    def test_site_packages_not_user_code(self):
        lib_frame = FrameInfo(
            filename="/usr/lib/python3.11/site-packages/requests/api.py",
            lineno=10,
            function="get",
            code_context="",
        )
        assert lib_frame.is_user_code is False

    def test_stdin_not_user_code(self):
        frame = FrameInfo(
            filename="<stdin>",
            lineno=1,
            function="<module>",
            code_context="",
        )
        assert frame.is_user_code is False
