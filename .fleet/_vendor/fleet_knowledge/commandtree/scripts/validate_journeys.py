#!/usr/bin/env python3
"""Validate journey flows/maps + feature capability maps + their cross-links — thin shim.

The implementation now lives in the standalone `fleet-knowledge` package, as the
auto-discovered `journeys-and-features` check:
`fleet/packages/fleet-knowledge/src/fleet_knowledge/checks/structure/_journeys.py`.

This entry point stays because the pre-commit hooks, `make lint` and CI call it by path
(including `--write-baseline`); it keeps the same flags, the same exit codes and the same
stdout. The anchor baseline was retired at zero, so `--write-anchor-baseline`
is gone.

Stdlib only. Exits 1 on any violation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

# `fleet_knowledge` is installed, or lives in the fleet submodule; `_repo` is the one module
# that knows where, and refuses with the repair command when it is absent.
_repo.fleet_knowledge()
from fleet_knowledge.checks.structure._journeys import JourneysValidator, report_legacy  # noqa: E402
from fleet_knowledge.checks.structure._kit import local_kb  # noqa: E402
from fleet_knowledge.config import Config, find_config_file, section_from_table  # noqa: E402

REPO = _repo.repo_root()


def _kb() -> Any:  # the package's KnowledgeBase, typed there
    """This checkout's knowledge base, with its own `[fleet.structure]` and `[fleet.planning]`
    tables honoured.

    Only those tables are read — the same narrowing `_repo.knowledge_base` applies to
    `[fleet.planning]` — so an option a repository sets for the journeys check (its
    `coverage_roots` above all, which a bootstrap ratchets as parts are described) means the
    same thing here as to `python3 -m fleet_knowledge check`. Without it the two disagreed:
    the check passed on a described part while this script reported the whole tree unclaimed.
    """
    sections: dict[str, dict[str, Any]] = {"structure": {}, "planning": {}}
    found = find_config_file(REPO)
    if found is not None:
        source, table = found
        for name in sections:
            raw = table.get(name)
            if raw is not None:
                sections[name] = dict(section_from_table(name, raw, source))
    # `[fleet.planning]` too: its `corpus` / `corpora` are what a repo-qualified reference
    # (`<corpus>:NNNN` in Ships-in, `<corpus>:CAP-NNNN` in `covers:` or a program's `requires`)
    # resolves against. Without it every such reference read "declared corpora: none".
    return local_kb(REPO, config=Config(structure=sections["structure"], planning=sections["planning"]))


if __name__ == "__main__":
    v = JourneysValidator(_kb())
    if "--write-baseline" in sys.argv[1:]:
        raise SystemExit(v.write_baseline())
    raise SystemExit(report_legacy(v, v.run()))
