# Changelog

All notable changes to traceback-ai will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-03-04

### Added
- `traceback_ai.install()` — one-line global exception hook with AI analysis
- `traceback_ai.analyze()` — manual analysis of caught exceptions
- `traceback_ai.configure()` — global configuration API
- **Providers**: OpenAI, Anthropic, Groq, Cerebras, and Ollama (offline, no API key)
- `auto` provider mode — detects available API keys automatically (Anthropic → OpenAI → Groq → Cerebras → Ollama)
- Rich terminal output with syntax-highlighted fix code
- Interactive follow-up Q&A mode (`interactive=True`)
- `show_locals` — optionally include local variable values in analysis context
- Secret redaction — auto-redacts API keys, tokens, passwords, AWS/Google credentials, JWTs, PEM keys, and nested dict secrets
- IPython/Jupyter integration via custom exception handler
- CLI: `tbai analyze <file>` — analyze saved tracebacks from log files
- CLI: `tbai run <script>` — run a Python script with AI debugging enabled
- CLI: `tbai config` — display current configuration and detected API keys
- CLI: `tbai ollama-models` — list available local Ollama models
- HTTP security: TLS verification, redirect blocking, response size cap, sanitized error messages
- URL validation: rejects plain HTTP for remote hosts across all providers

[0.1.0]: https://github.com/hugo-onnx/traceback-ai/releases/tag/v0.1.0
