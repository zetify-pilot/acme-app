# Tasks

A tiny task-list web service — the pilot repository Fleet works on.

## Install

```bash
pip install -e '.[dev]'
```

## Running the tests

```bash
pytest -q
```

This is the exact command CI runs (see `.github/workflows/ci.yml`). Where `make` is
installed, `make test` runs the same suite.

## Running the app

```bash
uvicorn app.main:app --reload
```
