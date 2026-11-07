#!/usr/bin/env python3
"""The ONE reader for the program and slice registers — this checkout's binding of it.

**The implementation moved to `fleet/packages/fleet-knowledge`** (`fleet_knowledge.registers`), which
is root-parameterised and knows nothing about this repository. This module is the thin
binding every `scripts/` consumer already imports: it holds the *paths* — which corpus, which
files — and delegates every parse.

Why the binding stays a module with mutable globals rather than becoming a function call:
`use_root()` is the contract four validators and their self-tests already use to point this
reader at a temp knowledge tree, and a consumer that rebound only its OWN `K` would leave
this module reading the real repository. That first surfaced as an error reported against the
real `knowledge/programs.md` from inside a temp-tree test, which is worse than a failure
because it reads as a finding about the actual corpus.

Both tiers stopped being folders on 2026-08-14. A program is a row in
`knowledge/programs.md`, a slice is a row in `knowledge/slices.md`, and the prose that
survived the cut lives in an OPTIONAL detail file named for the row's id
(`knowledge/programs/PG-NN.md`, `knowledge/slices/SL-NNN.md`). The filename IS the join.
Nothing here carries a `status:`: a slice's and a program's completion is COMPUTED from their
member PRDs and their `Verified by` proof (`fleet_knowledge.rollup`). A proof entry is a PRD
number or `drill:<stem>` for `knowledge/drills/<stem>.md`, shipped iff its `verdict: passed`.
What HAPPENED to a row as a decision is the last column, `Disposition` — `adopted`,
`withdrawn: <decision record>`, `superseded by <id>` — and it is a decision, never a status.

The full model — why a register rather than a folder, what lives in the register versus the
detail file, why ids are permanent — is on `fleet_knowledge.registers` and in that package's
README, stated once.

Stdlib only, like every sibling knowledge reader.
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
from fleet_knowledge import registers as _kk  # noqa: E402
from fleet_knowledge.markdown import cells, section  # noqa: E402

REPO = _repo.repo_root()
K = REPO / "knowledge"

PROGRAM_REGISTER = K / "programs.md"
SLICE_REGISTER = K / "slices.md"
PROGRAM_DETAIL_DIR = K / "programs"
SLICE_DETAIL_DIR = K / "slices"

PROGRAM_ID_RE = _kk.PROGRAM_ID_RE
SLICE_ID_RE = _kk.SLICE_ID_RE
NEXT_PROGRAM_RE = _kk.NEXT_PROGRAM_RE
NEXT_SLICE_RE = _kk.NEXT_SLICE_RE

detail_body = _kk.detail_body
is_drill = _kk.is_drill
drill_stem = _kk.drill_stem

__all__ = [
    "K",
    "PROGRAM_DETAIL_DIR",
    "PROGRAM_REGISTER",
    "SLICE_DETAIL_DIR",
    "SLICE_REGISTER",
    "cells",
    "detail_body",
    "drill_stem",
    "drills",
    "is_drill",
    "next_ids",
    "program_detail",
    "programs",
    "section",
    "slice_detail",
    "slices",
    "use_root",
]


def use_root(knowledge_dir: Path) -> None:
    """Point every path in this module at `knowledge_dir`.

    Production never calls this — the constants above are correct in a checkout. It exists
    because the validators run `main()` against a temp knowledge tree.
    """
    global K, PROGRAM_REGISTER, SLICE_REGISTER, PROGRAM_DETAIL_DIR, SLICE_DETAIL_DIR
    K = knowledge_dir
    PROGRAM_REGISTER = K / "programs.md"
    SLICE_REGISTER = K / "slices.md"
    PROGRAM_DETAIL_DIR = K / "programs"
    SLICE_DETAIL_DIR = K / "slices"


def programs() -> list[dict[str, Any]]:
    """Every program row, in register order.

    Columns: `ID | Name | Kind | Verified by | Requires | Disposition`. `verified_by` entries
    are PRD numbers or `drill:<stem>`; `disposition` is `{"kind", "ref"}`.
    """
    return _kk.programs(K)


def slices() -> list[dict[str, Any]]:
    """Every slice row, in register order.

    Columns: `ID | Name | Kind | Program | Done when | Verified by | Depends on | Components |
    Disposition`.
    """
    return _kk.slices(K)


def drills() -> dict[str, dict[str, Any]]:
    """Every drill record under `knowledge/drills/`, `stem -> frontmatter fields`.

    What a `drill:<stem>` proof entry resolves to. Nothing here reads the verdict —
    `fleet_knowledge.rollup.proof_shipped` does, in one place.
    """
    return _kk.drills(K)


def next_ids() -> tuple[str, str]:
    """The two append-only counters, as written. `("", "")` when a marker is missing."""
    return _kk.next_ids(K)


def program_detail(pid: str) -> Path:
    """Where `PG-NN`'s prose lives — whether or not the file exists."""
    return _kk.program_detail(K, pid)


def slice_detail(sid: str) -> Path:
    """Where `SL-NNN`'s prose lives — whether or not the file exists."""
    return _kk.slice_detail(K, sid)
