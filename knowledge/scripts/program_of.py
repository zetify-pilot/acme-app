#!/usr/bin/env python3
"""Resolve a component, slice or PRD to the program(s) it rolls up to.

    python3 knowledge/scripts/program_of.py audit-log 0333 internal/auditlog/store.go
    python3 knowledge/scripts/program_of.py --list

One line per input token: `<token>\\t<PG-id[,PG-id...]|->\\t<how it was derived>`.

Why this exists: a program is going to carry an authored priority, and the work
belonging to it inherits that rank. Only PRD issues ever carried a `Program`
label — the git → Linear PRD projection puts one on a PRD via its frontmatter
`slice:` — so the inheritance reached nothing else. Measured on the live board on
2026-09-05: of 57 issues sitting in `Queued`, **zero** carried a `Program` label
(the 15 open issues that did were all PRDs, every one of them in a PRD-lifecycle
state). Bugs, tasks and cleanups — the majority of issue volume, born in Linear
with no git file — had no program association at all, so a program's rank had
nothing to attach to. `check` is the one session that triages those, and
this is what it reads to decide.

**It derives; it never decides.** Program membership is authored in exactly two
places and this module only reads them:

    knowledge/slices.md  `Program` column     -> slice rolls up to program
    knowledge/slices.md  `Components` column  -> slice names components
    knowledge/prds/NNNN-*/prd.md `slice:`     -> PRD rolls up to slice

The PRD edge is byte-for-byte the one the PRD projection walks (now the fleet
service's `prd-projection` pass), deliberately: extending the existing association
to work that has no git file, rather than opening a second place where membership
gets decided.

**Several programs is the normal answer, and it is not a failure.** A component
is routinely named by slices under different programs (`audit-log` sits under
both and ), so this prints every candidate and the triager picks —
the same "enumerate, never recall" rule check.md §5 applies to the Linear
Project. Collapsing to one here would be a guess wearing a derivation's clothes.

**And no program is a real answer, not an error.** Plenty of work legitimately
belongs to no program; it falls through to the ordering keys beneath the program
rank, which is the designed behaviour. The marker is printed in words (`-`) and
the exit code is 0 either way — callers route on the output, never on the exit
code (`component_of.py`'s contract, followed here).

Stdlib only, like every sibling — it must run in a lane checkout where nothing
is installed. Its reads go through the shipped `fleet_knowledge.registers` reader,
which prefers the per-row fragments and so works on a fresh checkout where the
generated register tables are no longer committed; `_repo` resolves the
package from the fleet submodule when it is not installed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

REPO = _repo.repo_root()
PROGRAMS = REPO / "knowledge" / "programs.md"
SLICES = REPO / "knowledge" / "slices.md"

PROGRAM_ID_RE = re.compile(r"^PG-\d+$")
SLICE_ID_RE = re.compile(r"^SL-\d+$")
PRD_NUM_RE = re.compile(r"^\d{4}$")

# The token printed in the id column when nothing claims the input. It is a
# VALUE, not an absence: a reader must be able to tell "the derivation ran and
# found no program" apart from "the derivation never ran".
NO_PROGRAM_MARKER = "-"


def _registers() -> Any:
    """The ONE program/slice register reader — `fleet_knowledge.registers`.

    It prefers the per-row `rows/*.json` fragments when a corpus carries them and falls
    back to the committed table when it does not, which is the whole contract this module
    needs: since the tables are generated on demand and absent from a fresh
    checkout, so reading `programs.md` / `slices.md` directly returns nothing there.

    Resolved lazily so importing this module stays dependency-free; the register package is
    stdlib and ships in the fleet submodule (or an installed `fleet-knowledge`), which
    `_repo.fleet_knowledge()` makes importable or refuses with the repair command.
    """
    _repo.fleet_knowledge()
    from fleet_knowledge import registers  # noqa: PLC0415 — resolved after the path insert

    return registers


def program_ids() -> list[str]:
    """Every program id, in register order — the closed valid set.

    An id absent from here is not a program, however plausible it looks. This is
    the same set `linear_labels.program_label_names()` closes the label group on;
    a new row in the register widens both with no code change.
    """
    return [str(r["id"]) for r in _registers().programs(PROGRAMS.parent, file_name=PROGRAMS.name)]


def program_names() -> dict[str, str]:
    """`{PG-id -> name}` — the readable name the label deliberately does not carry
    (the label is named for the permanent ID; a title-derived slug moves when the
    title does, which is how a retitle once minted a duplicate)."""
    return {str(r["id"]): str(r["title"]) for r in _registers().programs(PROGRAMS.parent, file_name=PROGRAMS.name)}


def slice_rows() -> list[dict[str, Any]]:
    """Every slice as `{id, program, components}` — the two authored edges.

    Read through the register reader, which takes them from the row fragments when the
    corpus has them (the generated table is absent from a fresh checkout) and from the
    committed `Program` / `Components` columns otherwise.
    """
    return [
        {"id": str(s["id"]), "program": str(s["program"]), "components": list(s["component"])}
        for s in _registers().slices(SLICES.parent, file_name=SLICES.name)
    ]


def program_of_slice(sid: str) -> str | None:
    """The program `sid` rolls up to, or None — the slice register's `Program` column."""
    for row in slice_rows():
        if row["id"] == sid:
            return str(row["program"]) or None
    return None


def program_of_prd(num: str) -> str | None:
    """The program PRD `num` rolls up to, via its frontmatter `slice:`.

    The PRD -> slice -> program chain the PRD projection walks to label a PRD issue.
    A bug filed against a PRD's work reaches that PRD's program through here, which
    is the case this whole module was asked for.
    """
    hits = sorted((REPO / "knowledge" / "prds").glob(f"{num}-*/prd.md"))
    if not hits:
        return None
    for line in hits[0].read_text(encoding="utf-8").splitlines()[:60]:
        if line.startswith("slice:"):
            sid = line.split(":", 1)[1].strip().strip("\"'")
            return program_of_slice(sid) if sid else None
    return None


def programs_of_component(cid: str) -> list[str]:
    """Every program whose slices name component `cid`, sorted and de-duplicated.

    Several is normal (a component is worked on under more than one program) and
    none is normal (most components are not currently under a program at all).
    """
    hits = {str(r["program"]) for r in slice_rows() if cid in r["components"] and r["program"]}
    return sorted(hits)


def _component_of_path(path: str) -> str | None:
    """The component that owns `path`, via the component registry — reusing
    `component_of.py` rather than re-deriving ownership here."""
    try:
        import component_of  # noqa: PLC0415
    except ImportError:  # pragma: no cover - sibling script is always present
        return None
    return component_of.component_of(path, component_of.owners())


def resolve(token: str) -> tuple[list[str], str]:
    """`(candidate program ids, how it was derived)` for one input token.

    The derivation string is never empty, including when nothing resolves: it is
    the record that the lookup HAPPENED. An empty second element would make "no
    program" indistinguishable from "never asked" the moment it is printed.
    """
    t = token.strip()
    if PROGRAM_ID_RE.match(t):
        known = t in program_ids()
        return ([t] if known else [], f"program {t}" + ("" if known else " — not in knowledge/programs.md"))
    if SLICE_ID_RE.match(t):
        pid = program_of_slice(t)
        return ([pid] if pid else [], f"slice {t}" + ("" if pid else " — names no program"))
    if PRD_NUM_RE.match(t):
        hits = sorted((REPO / "knowledge" / "prds").glob(f"{t}-*/prd.md"))
        if not hits:
            return ([], f"prd {t} — no such PRD directory")
        sid = ""
        for line in hits[0].read_text(encoding="utf-8").splitlines()[:60]:
            if line.startswith("slice:"):
                sid = line.split(":", 1)[1].strip().strip("\"'")
                break
        if not sid:
            return ([], f"prd {t} — frontmatter names no slice")
        pid = program_of_slice(sid)
        return ([pid] if pid else [], f"prd {t} -> slice {sid}" + ("" if pid else " — names no program"))
    if "/" in t or t.endswith((".go", ".py", ".ts", ".tsx", ".md", ".sql", ".yaml", ".yml", ".sh")):
        cid = _component_of_path(t)
        if not cid:
            return ([], f"path {t} — no component owns it")
        pids = programs_of_component(cid)
        return (pids, f"path {t} -> component {cid}" + ("" if pids else " — no slice names it"))
    pids = programs_of_component(t)
    return (pids, f"component {t}" + ("" if pids else " — no slice names it"))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "--list":
        names = program_names()
        for pid in program_ids():
            print(f"{pid}\t{names.get(pid, '')}")
        return 0
    for token in args:
        pids, via = resolve(token)
        print(f"{token}\t{','.join(pids) if pids else NO_PROGRAM_MARKER}\t{via}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
