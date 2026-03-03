# Contributing to traceback-ai

Thank you for your interest in contributing!

## Setup

```bash
git clone https://github.com/hugo-onnx/traceback-ai
cd traceback-ai
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest                         # Run all tests
pytest -v                      # Verbose output
pytest tests/test_context.py   # Single file
pytest --cov=traceback_ai      # With coverage
```

## Adding a New Provider

1. Create `src/traceback_ai/providers/my_provider.py`
2. Subclass `BaseProvider` and implement `name`, `default_model`, and `complete()`
3. Use `_http_post()` and `validate_base_url()` from `providers/base.py` for all HTTP calls
4. Register it in `analyzer._resolve_provider()`
5. Add it to `providers/__init__.py`
6. Write tests in `tests/test_providers.py` — patch `traceback_ai.providers.my_provider._http_post`

## Code Style

```bash
ruff check .        # Lint
ruff format .       # Format
mypy src/           # Type check
```

## Submitting a PR

- Keep PRs focused on a single change
- Add tests for new functionality
- Update the README and CHANGELOG if adding features
- Run the full test suite before submitting

---

## Publishing to PyPI (maintainers only)

### Prerequisites

```bash
pip install build twine
```

### 1. Bump the version

Update `version` in `pyproject.toml` and `src/traceback_ai/_version.py`, then add a section to `CHANGELOG.md`.

### 2. Build the distribution

```bash
python -m build
```

This creates `dist/traceback_ai-X.Y.Z-py3-none-any.whl` and `dist/traceback_ai-X.Y.Z.tar.gz`.

### 3. Validate metadata

```bash
twine check dist/*
```

All checks must pass before uploading.

### 4. Test on TestPyPI first

```bash
twine upload --repository testpypi dist/*
```

Then install from TestPyPI in a fresh venv and do a smoke test:

```bash
python -m venv /tmp/tbai-test && source /tmp/tbai-test/bin/activate
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ traceback-ai
tbai --version
tbai config
```

### 5. Publish to PyPI

Only after the TestPyPI smoke test passes:

```bash
twine upload dist/*
```

### 6. Tag the release

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

Then create a GitHub Release from the tag and paste the relevant CHANGELOG section as the release notes.
