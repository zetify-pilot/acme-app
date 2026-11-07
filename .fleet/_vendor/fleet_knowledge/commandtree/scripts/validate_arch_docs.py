#!/usr/bin/env python3
"""Validate the architecture-doc freshness contract — thin shim.

The implementation now lives in the standalone `fleet-knowledge` package, as the
auto-discovered `arch-docs` check:
`fleet/packages/fleet-knowledge/src/fleet_knowledge/checks/structure/_arch_docs.py`.

This entry point stays because the pre-commit hooks, `make lint` and CI call it by path
(including with `--strict`, `--changed-since <base>` and `--list-subjects`); it keeps the
same flags, the same exit codes and the same stdout.

Stdlib only. Exit 1 on any blocking error (or any drift warning under `--strict`).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

# `fleet_knowledge` is installed, or lives in the fleet submodule; `_repo` is the one module
# that knows where, and refuses with the repair command when it is absent.
_repo.fleet_knowledge()
from fleet_knowledge.checks.structure._arch_docs import main  # noqa: E402

REPO = _repo.repo_root()

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], REPO))
