# Tasks

A tiny task-list web service — the pilot repository Fleet works on.

## Install

Requires Python 3.11 or newer (see requires-python in pyproject.toml).

```bash
pip install -e '.[dev]'
```

## Running the tests

```bash
pytest
```

This is the exact command CI runs (see `.github/workflows/ci.yml`). Where `make` is
installed, `make test` runs the same suite.

## Running the app

```bash
uvicorn app.main:app --reload
```

## Project layout

- `app/main.py` — the FastAPI application and its task endpoints
- `tests/` — the pytest suite CI runs
- `knowledge/` — the product knowledge (programs, PRDs) the fleet works from
- `.github/workflows/ci.yml` — the CI workflow that runs the test suite

## Contributing

Run `pytest` and make sure it passes before you open a pull request.
<!-- acceptance probe IMP-1922 -->
