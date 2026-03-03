# traceback-ai

**AI-powered Python exception debugger.** When your code crashes, get an instant explanation, root cause analysis, and a concrete fix — right in your terminal.

[![PyPI version](https://img.shields.io/pypi/v/traceback-ai.svg)](https://pypi.org/project/traceback-ai/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/hugo-onnx/traceback-ai/actions/workflows/test.yml/badge.svg)](https://github.com/hugo-onnx/traceback-ai/actions/workflows/test.yml)

---

## Before traceback-ai

```
Traceback (most recent call last):
  File "app.py", line 42, in process_order
    price = item["price"] * quantity
KeyError: 'price'
```

😩 *What dict? Which line? Why? How do I fix it?*

## After traceback-ai

```
Traceback (most recent call last):
  File "app.py", line 42, in process_order
    price = item["price"] * quantity
KeyError: 'price'

─── AI Debug Analysis ─────────────────────────────────── via Anthropic ───

╭─ KeyError: 'price' ────────────────────────────────────────────────────╮
│                                                                         │
│  You're trying to access 'price' from a dictionary, but that key       │
│  doesn't exist. This happens when the item dictionary was created      │
│  without a 'price' field, or the key was stored under a different name │
│  (e.g. 'unit_price' or 'cost').                                        │
│                                                                         │
╰─────────────────────────────────────────────────────────────────────────╯

 Likely Causes
  • The item came from an API that returns 'unit_price' instead of 'price'
  • Items without prices are not being filtered before processing
  • A recent schema change renamed the field

 Suggested Fix
  Use .get() with a default, or validate the schema before processing

╭─ Fix Code ──────────────────────────────────────────────────────────────╮
│                                                                         │
│  # Safe access with default                                             │
│  price = item.get("price", 0.0)                                        │
│                                                                         │
│  # Or validate and handle missing prices                                │
│  if "price" not in item:                                                │
│      raise ValueError(f"Item {item.get('id')} has no price")           │
│  price = item["price"] * quantity                                       │
│                                                                         │
╰─────────────────────────────────────────────────────────────────────────╯

 Search hint: Python dict KeyError safe access .get() default value
──────────────────────────────────────────────────────────────────────────
```

---

## Installation

```bash
pip install traceback-ai
```

## Quickstart

```python
import traceback_ai
traceback_ai.install()

# That's it. Now any unhandled exception gets AI analysis.
data = {}
print(data["missing_key"])  # → AI explains and suggests a fix
```

Set your API key via environment variable (pick any one):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # Recommended
export OPENAI_API_KEY="sk-..."
export GROQ_API_KEY="gsk_..."           # Free tier available
export CEREBRAS_API_KEY="csk_..."       # Free tier available
# No key needed for Ollama (local)
```

`auto` mode (the default) detects whichever key is set and uses it automatically.

---

## Features

- **Zero boilerplate** — one line to install, works immediately
- **5 providers** — OpenAI, Anthropic, Groq, Cerebras, and **Ollama** (100% offline, no API key!)
- **Rich terminal output** — beautiful panels with syntax-highlighted fix code
- **Structured analysis** — explanation, root causes, fix description, and runnable fix code
- **Interactive mode** — ask follow-up questions after the initial analysis
- **Privacy-first** — `show_locals` is off by default; secrets auto-redacted when enabled
- **Jupyter support** — works in notebooks out of the box
- **CLI tool** — analyze saved tracebacks from log files
- **Type-safe** — fully typed, mypy strict compatible

---

## Usage

### Global exception hook (most common)

```python
import traceback_ai
traceback_ai.install()
```

### Analyze caught exceptions

```python
import sys, traceback_ai

try:
    do_something_risky()
except Exception:
    traceback_ai.analyze(*sys.exc_info())
```

### Configuration

```python
traceback_ai.install(
    provider="anthropic",   # 'openai' | 'anthropic' | 'groq' | 'cerebras' | 'ollama' | 'auto'
    model="claude-sonnet-4-6",     # Override the default model
    show_locals=True,              # Include local variable values (off by default)
    interactive=True,              # Ask follow-up questions
    context_lines=20,              # Source code lines around the error
    redact_secrets=True,           # Hide API keys / passwords (default: True)
)
```

Or via environment variables:

```bash
TBAI_PROVIDER=anthropic
TBAI_MODEL=claude-haiku-4-5-20251001
TBAI_SHOW_LOCALS=true
TBAI_INTERACTIVE=true
TBAI_CONTEXT_LINES=20
```

### Ollama (100% offline, no API key)

```bash
# Install Ollama: https://ollama.ai
ollama pull llama3.2
```

```python
traceback_ai.install(provider="ollama", model="llama3.2")
```

### Groq or Cerebras (very fast, free tier)

```python
traceback_ai.install(provider="groq")      # uses GROQ_API_KEY
traceback_ai.install(provider="cerebras")  # uses CEREBRAS_API_KEY
```

Get free API keys: [Groq](https://console.groq.com) · [Cerebras](https://cloud.cerebras.ai)

### Interactive mode

```
─── AI Debug Analysis ────────────────────────────────── via OpenAI ───
...analysis...
──────────────────────────────────────────────────────────────────────

Ask a follow-up question (or press Enter to quit):
  > Why does dict.get() return None instead of raising KeyError?
```

---

## CLI

```bash
# Analyze a saved traceback from a log file
tbai analyze error.log
tbai analyze crash.txt --provider anthropic --interactive

# Run a Python script with AI debugging
tbai run my_script.py
tbai run my_script.py --show-locals

# Check your configuration
tbai config

# List available Ollama models
tbai ollama-models
```

---

## Providers

| Provider | API Key | Default Model | Speed | Cost |
|----------|---------|---------------|-------|------|
| `anthropic` | `ANTHROPIC_API_KEY` | claude-haiku-4-5 | Fast | Low |
| `openai` | `OPENAI_API_KEY` | gpt-4o-mini | Fast | Low |
| `groq` | `GROQ_API_KEY` | llama-3.1-8b-instant | **Very fast** | Low (free tier) |
| `cerebras` | `CEREBRAS_API_KEY` | llama3.1-8b | **Very fast** | Low (free tier) |
| `ollama` | **None** | llama3.2 | Medium | **Free** |
| `auto` | Detects available | — | — | — |

`auto` (default) picks the first provider with a key set: Anthropic → OpenAI → Groq → Cerebras → Ollama.

---

## Programmatic API

```python
from traceback_ai.context import build_context
from traceback_ai.analyzer import run_analysis
import sys

try:
    risky()
except Exception:
    ctx = build_context(*sys.exc_info())
    result = run_analysis(ctx)

    # Access structured data:
    print(result.explanation)   # str
    print(result.causes)        # List[str]
    print(result.fix)           # str
    print(result.fix_code)      # Optional[str]
    print(result.docs_hint)     # Optional[str]
```

---

## Jupyter Notebooks

```python
import traceback_ai
traceback_ai.install()
# Works automatically — IPython's exception handler is patched
```

---

## Privacy

**`show_locals` is `False` by default** — local variable values are never sent to the LLM unless you explicitly opt in. This prevents accidental exposure of secrets, PII, or sensitive business data in your tracebacks.

When you do enable `show_locals=True`, `redact_secrets=True` (also on by default) automatically redacts values that look like secrets — API keys, tokens, passwords, AWS credentials, JWTs, PEM keys, and secrets nested inside dicts — before anything is sent.

You can always review exactly what would be sent before enabling:

```python
from traceback_ai.context import build_context
import sys

try:
    my_bad_code()
except Exception:
    ctx = build_context(*sys.exc_info(), show_locals=True, redact_secrets=True)
    print(ctx.to_prompt_text(show_locals=True))  # Inspect before sending
```

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
git clone https://github.com/hugo-onnx/traceback-ai
cd traceback-ai
pip install -e ".[dev]"
pytest
```

---

## License

MIT — see [LICENSE](LICENSE).
