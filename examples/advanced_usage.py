"""
traceback-ai advanced usage examples.

Demonstrates: Ollama (offline), custom config, pandas errors, async.
"""

# ─── Example 1: Offline mode with Ollama ─────────────────────────────────────
# No API key needed! Just have Ollama running: https://ollama.ai
# Then: ollama pull llama3.2
import traceback_ai

traceback_ai.install(
    provider="ollama",
    model="llama3.2",  # or "codellama", "mistral", etc.
    context_lines=20,  # More code context
)

# ─── Example 2: Fine-tuned for data science ──────────────────────────────────
traceback_ai.configure(
    provider="openai",
    model="gpt-4o",  # Use the powerful model for complex pandas/numpy errors
    show_locals=True,  # See df.shape, dtypes, etc. in the analysis
    context_lines=25,
    redact_secrets=True,
    interactive=True,  # Ask: "how do I vectorize this?"
)

# ─── Example 3: CI/CD mode (disable interactive, minimal output) ─────────────
import os

if os.getenv("CI"):
    traceback_ai.configure(
        interactive=False,
        show_locals=False,  # Don't log variable values in CI
        timeout=15,
    )

# ─── Example 4: Programmatic analysis (returns structured data) ──────────────
import sys
from traceback_ai.context import build_context
from traceback_ai.analyzer import run_analysis

try:
    result = 1 / 0
except Exception:
    exc_type, exc_value, exc_tb = sys.exc_info()
    ctx = build_context(exc_type, exc_value, exc_tb)
    analysis = run_analysis(ctx)

    # Use the structured result in your own way
    print(f"Error type:   {ctx.exc_type}")
    print(f"Explanation:  {analysis.explanation}")
    print(f"Root causes:  {analysis.causes}")
    print(f"Fix:          {analysis.fix}")
    if analysis.fix_code:
        print(f"Fix code:\n{analysis.fix_code}")


# ─── Example 5: Web app integration (Flask/FastAPI) ──────────────────────────
# In development, log AI analysis instead of just the traceback:
#
# from flask import Flask
# import traceback_ai, logging
#
# app = Flask(__name__)
# traceback_ai.install(
#     provider="anthropic",
#     show_fix=True,
#     interactive=False,
# )
#
# @app.errorhandler(Exception)
# def handle_error(e):
#     import sys
#     traceback_ai.analyze(*sys.exc_info())
#     return {"error": str(e)}, 500
