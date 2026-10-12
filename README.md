# Tasks

A tiny task-list web service — the pilot repository Fleet works on.

## Install

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
Acceptance note R222: this line was added by the fleet on 2026-10-12.
