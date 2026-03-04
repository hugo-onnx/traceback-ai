# traceback-ai

**AI-powered Python exception debugger.** When your code crashes, get an instant explanation, root cause analysis, and a concrete fix — right in your terminal.

[![PyPI version](https://img.shields.io/pypi/v/traceback-ai.svg)](https://pypi.org/project/traceback-ai/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/hugo-onnx/traceback-ai/actions/workflows/test.yml/badge.svg)](https://github.com/hugo-onnx/traceback-ai/actions/workflows/test.yml)

---

## What does it do?

When your Python script crashes, you normally see this:

```
Traceback (most recent call last):
  File "app.py", line 42, in process_order
    price = item["price"] * quantity
KeyError: 'price'
```

😩 *What dict? Which line? Why? How do I fix it?*

With `traceback-ai`, the same crash looks like this:

```
Traceback (most recent call last):
  File "app.py", line 42, in process_order
    price = item["price"] * quantity
KeyError: 'price'

─── AI Debug Analysis ─────────────────────────────────── via Anthropic ───

╭─ KeyError: 'price' ────────────────────────────────────────────────────╮
│                                                                        │
│  You're trying to access 'price' from a dictionary, but that key       │
│  doesn't exist. This happens when the item dictionary was created      │
│  without a 'price' field, or the key was stored under a different name │
│  (e.g. 'unit_price' or 'cost').                                        │
│                                                                        │
╰────────────────────────────────────────────────────────────────────────╯

 Likely Causes
  • The item came from an API that returns 'unit_price' instead of 'price'
  • Items without prices are not being filtered before processing
  • A recent schema change renamed the field

 Suggested Fix
  Use .get() with a default, or validate the schema before processing

╭─ Fix Code ─────────────────────────────────────────────────────────────╮
│                                                                        │
│  # Safe access with default                                            │
│  price = item.get("price", 0.0)                                        │
│                                                                        │
│  # Or validate and handle missing prices                               │
│  if "price" not in item:                                               │
│      raise ValueError(f"Item {item.get('id')} has no price")           │
│  price = item["price"] * quantity                                      │
│                                                                        │
╰────────────────────────────────────────────────────────────────────────╯

 Search hint: Python dict KeyError safe access .get() default value
──────────────────────────────────────────────────────────────────────────
```

---

## Getting Started

### Step 1 — Install the package

Open your terminal and run:

```bash
pip install traceback-ai
```

Verify it installed correctly:

```bash
tbai --version
```

---

### Step 2 — Get an API key

`traceback-ai` uses an AI model to analyze your errors. You need an API key from one of the supported providers. **If you want a completely free and offline option, skip to [Ollama (no key required)](#option-e-ollama-no-api-key-100-offline) below.**

#### Option A — Anthropic (recommended)

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Navigate to **API Keys** → **Create Key**
4. Copy the key (starts with `sk-ant-...`)

#### Option B — OpenAI

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Navigate to **API Keys** → **Create new secret key**
4. Copy the key (starts with `sk-...`)

#### Option C — Groq (free tier available)

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up for free
3. Navigate to **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)

#### Option D — Cerebras (free tier available)

1. Go to [cloud.cerebras.ai](https://cloud.cerebras.ai)
2. Sign up for free
3. Navigate to **API Keys** → **Create new key**
4. Copy the key (starts with `csk_...`)

#### Option E — Ollama (no API key, 100% offline)

Ollama runs AI models locally on your machine — no account, no key, no data sent anywhere.

1. Download and install Ollama from [ollama.com](https://ollama.com)
2. Pull a model:
   ```bash
   ollama pull llama3.2
   ```
3. Skip Step 3 — no environment variable needed. Use it like this:
   ```python
   traceback_ai.install(provider="ollama", model="llama3.2")
   ```

---

### Step 3 — Set your API key

You have two options: a `.env` file (recommended for projects) or a system environment variable (recommended for global use).

#### Option 1 — .env file (recommended for projects)

A `.env` file keeps your keys in your project folder without hardcoding them in your code.

**1. Install `python-dotenv`:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**3. Load it at the top of your script, before calling `traceback_ai.install()`:**

```python
from dotenv import load_dotenv
load_dotenv()

import traceback_ai
traceback_ai.install()
```

**4. Add `.env` to your `.gitignore` so you never accidentally commit your keys:**

```
echo ".env" >> .gitignore
```

> **Use the variable name for your chosen provider:**
> ```
> ANTHROPIC_API_KEY=sk-ant-...
> OPENAI_API_KEY=sk-...
> GROQ_API_KEY=gsk_...
> CEREBRAS_API_KEY=csk_...
> ```

---

#### Option 2 — System environment variable (global, persists across projects)

Use this if you want the key available in every project without repeating the setup.

**macOS / Linux** — add to your shell config (`~/.zshrc` or `~/.bashrc`):

```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

Then reload your terminal:

```bash
source ~/.zshrc   # or source ~/.bashrc
```

**Windows** — open Command Prompt and run:

```cmd
setx ANTHROPIC_API_KEY "sk-ant-your-key-here"
```

Restart your terminal for the change to take effect. For the current session only, use PowerShell:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-your-key-here"
```

---

### Step 4 — Add one line to your script

```python
import traceback_ai
traceback_ai.install()

# Your code below — any unhandled exception now gets AI analysis
data = {}
print(data["missing_key"])
```

That's it. The next time your script crashes, you'll get a full AI-powered explanation automatically.

---

## Usage

### Auto-hook (most common)

Install once at the top of your script and forget about it:

```python
import traceback_ai
traceback_ai.install()
```

Every unhandled exception from this point on will be analyzed automatically.

### Analyze caught exceptions

If you're catching exceptions with `try/except` and want to analyze them manually:

```python
import sys
import traceback_ai

try:
    do_something_risky()
except Exception:
    traceback_ai.analyze(*sys.exc_info())
```

### Interactive mode — ask follow-up questions

Enable `interactive=True` to ask follow-up questions after the initial analysis:

```python
traceback_ai.install(interactive=True)
```

After each analysis you'll see a prompt:

```
Ask a follow-up question (or press Enter to quit):
  > Why does dict.get() return None instead of raising KeyError?
```

### Full configuration options

```python
traceback_ai.install(
    provider="anthropic",        # which AI provider to use (see Providers section)
    model="claude-haiku-4-5",    # override the default model
    show_locals=True,            # include local variable values (off by default)
    interactive=True,            # ask follow-up questions after analysis
    context_lines=20,            # how many lines of source code to include
    redact_secrets=True,         # hide API keys / passwords (default: True)
)
```

### Configure via environment variables

Instead of passing options in code, you can set these environment variables:

```bash
TBAI_PROVIDER=anthropic
TBAI_MODEL=claude-haiku-4-5
TBAI_SHOW_LOCALS=true
TBAI_INTERACTIVE=true
TBAI_CONTEXT_LINES=20
```

---

## Providers

| Provider | API Key Env Var | Default Model | Speed | Cost |
|---|---|---|---|---|
| `anthropic` | `ANTHROPIC_API_KEY` | claude-haiku-4-5 | Fast | Low |
| `openai` | `OPENAI_API_KEY` | gpt-4o-mini | Fast | Low |
| `groq` | `GROQ_API_KEY` | llama-3.1-8b-instant | Very fast | Free tier |
| `cerebras` | `CEREBRAS_API_KEY` | llama3.1-8b | Very fast | Free tier |
| `ollama` | *(none)* | llama3.2 | Medium | Free, offline |
| `auto` | Detects available | — | — | — |

**`auto` is the default.** It automatically picks the first provider for which a key is set, in this order: Anthropic → OpenAI → Groq → Cerebras → Ollama.

---

## CLI Commands

`traceback-ai` also ships a command-line tool called `tbai`:

```bash
# Analyze a saved traceback from a log file
tbai analyze error.log
tbai analyze crash.txt --provider anthropic --interactive

# Run a Python script with AI debugging enabled
tbai run my_script.py
tbai run my_script.py --show-locals

# Show your current configuration
tbai config

# List available Ollama models installed on your machine
tbai ollama-models
```

---

## Features

- **Zero boilerplate** — one line to install, works immediately
- **5 providers** — OpenAI, Anthropic, Groq, Cerebras, and Ollama (100% offline)
- **Rich terminal output** — clean panels with syntax-highlighted fix code
- **Structured analysis** — explanation, root causes, fix description, and runnable fix code
- **Interactive mode** — ask follow-up questions after each analysis
- **Privacy-first** — `show_locals` is off by default; secrets are auto-redacted when enabled
- **Jupyter support** — works in notebooks out of the box
- **CLI tool** — analyze saved tracebacks from log files
- **Type-safe** — fully typed, mypy strict compatible

---

## Jupyter Notebooks

Works out of the box — just install at the top of your notebook:

```python
import traceback_ai
traceback_ai.install()
```

IPython's exception handler is patched automatically.

---

## Privacy

**`show_locals` is `False` by default** — local variable values are never sent to the AI unless you explicitly opt in. This prevents accidental exposure of secrets, PII, or sensitive business data in your tracebacks.

When you enable `show_locals=True`, `redact_secrets=True` (also on by default) automatically scrubs values that look like secrets — API keys, tokens, passwords, AWS credentials, JWTs, PEM keys, and secrets nested inside dicts — before anything leaves your machine.

You can inspect exactly what would be sent before enabling:

```python
from traceback_ai.context import build_context
import sys

try:
    my_bad_code()
except Exception:
    ctx = build_context(*sys.exc_info(), show_locals=True, redact_secrets=True)
    print(ctx.to_prompt_text(show_locals=True))  # review before sending
```

---

## Programmatic API

Access the structured analysis result directly in your code:

```python
from traceback_ai.context import build_context
from traceback_ai.analyzer import run_analysis
import sys

try:
    risky()
except Exception:
    ctx = build_context(*sys.exc_info())
    result = run_analysis(ctx)

    print(result.explanation)   # str  — plain-English explanation
    print(result.causes)        # list — likely root causes
    print(result.fix)           # str  — suggested fix description
    print(result.fix_code)      # str  — runnable fix code (if available)
    print(result.docs_hint)     # str  — search hint for documentation
```

---

## Troubleshooting

**`tbai: command not found`**
The `tbai` command isn't on your PATH. Try running with `python -m traceback_ai` instead, or reinstall with `pip install --user traceback-ai` and add `~/.local/bin` to your PATH.

**`No provider configured`**
No API key was found. If you're using a `.env` file, make sure `load_dotenv()` is called before `traceback_ai.install()`. If you set a system environment variable, restart your terminal. Run `tbai config` to see what traceback-ai detects.

**`AuthenticationError` or `401 Unauthorized`**
Your API key is invalid or expired. Double-check it on your provider's dashboard and update your environment variable.

**Analysis doesn't appear / only the regular traceback shows**
Make sure `traceback_ai.install()` is called before the code that raises the exception. If you're in a Jupyter notebook, run the install cell first.

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
