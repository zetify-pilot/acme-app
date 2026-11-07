#!/usr/bin/env python3
"""Validate the per-domain requirement registers + the PRD `implements:` edge.

**The rules moved to `fleet_knowledge.checks.commitments.registers`; this file is the binding
that keeps this repo's entry point working.** Every check, every message and every severity
is unchanged — the module docstring over there is this one, and it is where to read what is
enforced and why: the id contract, the Kind × Disposition matrix, the supersession and
`Needs` graphs, the append-at-end rule, `Source` anchor resolution, the PRD claim/coverage/
drift edge, and the verbatim-restatement check that reads that edge backwards.

Two layers underneath it, and the split is the point:

  * `fleet_knowledge.requirements` is the ONE reader of a register row — the grammar and the
    parser. Bound below rather than restated, because a row parsed one way here and another
    way in a viewer over the same file is two sources of truth wearing one name.
  * `fleet_knowledge.checks.commitments` is the JUDGEMENT over those rows, reachable as a
    `Check` by the runner and by a board, with every value that used to be hard-coded here
    (the `v1` line, the PRD lifecycle bands, the grandfathered append-order set) now an
    option whose default is exactly what this file used to say.

**The legacy module surface is preserved deliberately.** Four siblings import this file by
path and drive it through its globals — `gen_requirement_status.py` and
`validate_requirement_statements.py` rebind `REPO`/`K` to point the parser at a different
tree, `requirement_query.py` reads `CURRENT_LINE`/`need_scope`/`is_cut`, and the self-test
rebinds `BASELINE` at a temp ratchet. So the globals below are real, mutable, and read at
CALL time: a rebind still moves what the next call reads.

Run: python3 knowledge/scripts/validate_requirements.py
Stdlib only. Prints `file: message` per violation; exits 1 on any.
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
REPO = _repo.repo_root()
from fleet_knowledge import requirements as kkreq  # noqa: E402
from fleet_knowledge.checks.commitments import registers as kkcheck  # noqa: E402
from fleet_knowledge.checks.commitments.context import Context  # noqa: E402
from fleet_knowledge.checks.commitments.options import CommitmentsConfig  # noqa: E402
from fleet_knowledge.config import config_from_table, find_config_file  # noqa: E402


def _config(root: Path) -> CommitmentsConfig:
    """The checkout's config, so `[fleet.commitments]` values reach this script.

    This entry point builds its own binding from a path, so without this it saw the package
    defaults only: a project's `[fleet.commitments]` table was ignored. The config file is
    the nearest one governing `root`, exactly as `fleet check` reads it; a checkout with no
    file gets the neutral defaults.
    """
    found = find_config_file(root)
    if found is None:
        return CommitmentsConfig()
    source, table = found
    return CommitmentsConfig.from_config(config_from_table(table, source))


CONFIG = _config(REPO)

K = REPO / "knowledge"
errors: list[str] = []
notes: list[str] = []
# Rebindable so the self-tests can point at a temp baseline. The ratchet is a property of the
# CHECKOUT, not of the tier: it lives where the package's own default says
# (`<repo>/scripts/requirement_register.baseline`), never beside this shipped copy.
BASELINE = REPO / CONFIG.baseline_dir / CONFIG.register_baseline

# ── the register grammar ──
# BOUND, never restated — each constant's argument (why bare `superseded` is sanctioned, why
# `Cut` is a column and not a fifth disposition, why `ENG` is reserved) lives on its
# definition in `fleet_knowledge.requirements`, the one reader of a register row.
ID_RE = kkreq.ID_RE
ID_REF_RE = kkreq.ID_REF_RE
PREFIX_RE = kkreq.PREFIX_RE
RESERVED_PREFIXES = kkreq.DEFAULT_RESERVED_PREFIXES
KINDS = kkreq.KINDS
DISPOSITIONS = kkreq.DISPOSITIONS
SUPERSEDED_RE = kkreq.SUPERSEDED_RE
REAFFIRMED_RE = kkreq.REAFFIRMED_RE
CUT_VALUES = kkreq.CUT_VALUES
REQUIRED_COLUMNS = kkreq.REQUIRED_COLUMNS
SEP_RE = kkreq.SEP_RE
LEGEND_LINK_RE = kkreq.LEGEND_LINK_RE
frontmatter = kkreq.frontmatter
field = kkreq.field
idlist = kkreq.idlist
cells = kkreq.cells
source_legend = kkreq.source_legend

# ── the check vocabulary ──
# Bound from the check module for the same reason: one definition, wherever it is read.
AC_CITE_RE = kkcheck.AC_CITE_RE
ILLEGAL_KIND_DISPOSITION = kkcheck.ILLEGAL_KIND_DISPOSITION
SATISFIED_SCOPES = kkcheck.SATISFIED_SCOPES
CURRENT_LINE = CONFIG.current_line
APPEND_ORDER_BASELINE = frozenset(CONFIG.append_order_baseline)
AC_COVERAGE_ENFORCED = set(CONFIG.ac_coverage_enforced)
CLAIM_REQUIRED = set(CONFIG.claim_required)
CLAIM_PRESENCE_ENFORCED = set(CONFIG.claim_presence_enforced)
CLAIM_HISTORY = set(CONFIG.claim_history)
DRIFT_ADVISORY_ONLY = set(CONFIG.drift_advisory_only)

# The memo `main()` clears each run — the package's dict, so a caller's `.clear()` still
# reaches the corpus walk it is meant to reset.
_PROSE_FILES_CACHE = kkcheck._PROSE_FILES_CACHE

# Pure helpers: no context, so they pass straight through.
find_cycle = kkcheck.find_cycle
registers_covering = kkcheck.registers_covering
load_baseline = kkcheck.load_baseline
supersession_terminus = kkcheck.supersession_terminus
dead = kkcheck.dead
section_spans = kkcheck.section_spans
emit_step_summary = kkcheck.emit_step_summary


def _ctx() -> Context:
    """A context built from THIS module's globals, freshly on every call.

    That freshness is the contract: `gen_requirement_status.py` and the statement guard both
    rebind `REPO`/`K` between calls, and the self-tests rebind all three. Capturing them once
    at import would silently keep reading the tree the process started in.
    """
    return Context(
        root=REPO,
        knowledge=K,
        cfg=CONFIG,
        errors=errors,
        notes=notes,
        baseline=BASELINE,
        # Resolved through the module global so a caller that swaps it (to count the corpus
        # walks) still sees its own function called.
        claude_prose_files=lambda d: _claude_prose_files(d),
    )


NEXT_ID_RE = kkcheck.next_id_re(Context(root=REPO, knowledge=K, cfg=CONFIG))


def err(path: Path, msg: str) -> None:
    errors.append(f"{rel(path)}: {msg}")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _claude_prose_files(claude_dir: Path) -> list[Path]:
    return kkcheck._claude_prose_files(claude_dir, CONFIG.prose_skip_dirs, CONFIG.prose_skip_top_dirs)


def load_registers() -> dict[str, dict[str, Any]]:
    return kkcheck.load_registers(_ctx())


def registered_components() -> dict[str, str]:
    return kkcheck.registered_components(_ctx())


def register_components() -> dict[str, list[str]]:
    return kkcheck.register_components(_ctx())


def slice_components() -> dict[str, list[str]]:
    return kkcheck.slice_components(_ctx())


def check_register_components(declared: dict[str, list[str]], known: dict[str, str]) -> None:
    kkcheck.check_register_components(_ctx(), declared, known)


def apply_ratchet(check: str, live: dict[str, str], baseline: set[tuple[str, str]], stale_is_hard: bool) -> None:
    kkcheck.apply_ratchet(_ctx(), check, live, baseline, stale_is_hard)


def check_kind_disposition(rows: dict[str, dict[str, Any]], baseline: set[tuple[str, str]]) -> None:
    kkcheck.check_kind_disposition(_ctx(), rows, baseline)


def check_supersession_terminality(rows: dict[str, dict[str, Any]], baseline: set[tuple[str, str]]) -> None:
    kkcheck.check_supersession_terminality(_ctx(), rows, baseline)


def check_supersession(rows: dict[str, dict[str, Any]]) -> None:
    kkcheck.check_supersession(_ctx(), rows)


def check_needs(rows: dict[str, dict[str, Any]]) -> None:
    kkcheck.check_needs(_ctx(), rows)


def check_because(rows: dict[str, dict[str, Any]]) -> None:
    kkcheck.check_because(_ctx(), rows)


def is_cut(row: dict[str, Any]) -> bool:
    return kkcheck.is_cut(_ctx(), row)


def need_scope(
    dep: str,
    claimant: str | None,
    claims_by_row: dict[str, list[tuple[str, str]]],
    disproven: set[str] | frozenset[str] | None = None,
) -> str:
    return kkcheck.need_scope(_ctx(), dep, claimant, claims_by_row, disproven)


def load_prd_claims() -> dict[str, list[tuple[str, str]]]:
    return kkcheck.load_prd_claims(_ctx())


def check_claim_scope(rows: dict[str, dict[str, Any]]) -> None:
    kkcheck.check_claim_scope(_ctx(), rows)


def check_append_order(rows: dict[str, dict[str, Any]]) -> None:
    kkcheck.check_append_order(_ctx(), rows)


def prd_target(num: str) -> Path | None:
    return kkcheck.prd_target(_ctx(), num)


def check_sources(rows: dict[str, dict[str, Any]], baseline: set[tuple[str, str]]) -> tuple[int, int, int]:
    return kkcheck.check_sources(_ctx(), rows, baseline)


def check_uncited_restatements(rows: dict[str, dict[str, Any]]) -> int:
    return kkcheck.check_uncited_restatements(_ctx(), rows)


def prose_files() -> list[Path]:
    return kkcheck.prose_files(_ctx())


def check_prose_citations(rows: dict[str, dict[str, Any]]) -> tuple[int, int]:
    return kkcheck.check_prose_citations(_ctx(), rows)


def ac_citations(body: str) -> set[str]:
    return kkcheck.ac_citations(_ctx(), body)


def check_prd_claims(rows: dict[str, dict[str, Any]]) -> int:
    return kkcheck.check_prd_claims(_ctx(), rows)


def main() -> int:
    return kkcheck.main(_ctx())


if __name__ == "__main__":
    raise SystemExit(main())
