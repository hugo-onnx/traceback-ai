"""
traceback-ai basic usage examples.

Run with:
    OPENAI_API_KEY=sk-... python examples/basic_usage.py
  or
    ANTHROPIC_API_KEY=sk-ant-... python examples/basic_usage.py
"""

import traceback_ai

# ─── Example 1: Global install (one-liner) ────────────────────────────────────
# After install(), any unhandled exception gets AI analysis automatically.
traceback_ai.install()

# Now this exception will be explained by AI instead of just crashing:
data = {"name": "Alice", "age": 30}
# Uncomment to see the AI analysis:
# print(data["email"])  # KeyError: 'email'


# ─── Example 2: Manual analysis of caught exceptions ─────────────────────────
import sys


def process_user(user_id: int):
    users = {1: "Alice", 2: "Bob"}
    return users[user_id]  # Raises KeyError for unknown IDs


try:
    process_user(999)
except Exception:
    traceback_ai.analyze(*sys.exc_info())


# ─── Example 3: Using as a context manager ────────────────────────────────────
# (Any exception raised inside 'with' is analyzed)
# from traceback_ai import analyze_context
# with analyze_context():
#     risky_operation()


# ─── Example 4: Custom provider ───────────────────────────────────────────────
traceback_ai.install(
    provider="anthropic",
    model="claude-haiku-4-5-20251001",  # Fast and cheap
    show_locals=True,  # Include variable values in analysis
    interactive=True,  # Ask follow-up questions after analysis
)
