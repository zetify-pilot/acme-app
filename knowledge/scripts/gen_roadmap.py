#!/usr/bin/env python3
"""Generate knowledge/roadmap.md from the planning hierarchy.

The roadmap is a *projection*, not a source: program → slice → PRD membership comes from
the two registers (`knowledge/programs.md`, `knowledge/slices.md`) plus each PRD's own
`slice:`, and each PRD's status / priority / target are read live from its frontmatter
(the single source of truth). Re-running regenerates, so the board can never drift.
Hand-edits are forbidden (the file carries a `generated:` marker; the status-copy
validator skips generated files for exactly this reason).

Run: python3 knowledge/scripts/gen_roadmap.py   (writes knowledge/roadmap.md)
Stdlib only.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

REPO = _repo.repo_root()
K = REPO / "knowledge"

_KR = Path(__file__).resolve().parent / "knowledge_registers.py"
_spec = importlib.util.spec_from_file_location("_roadmap_registers", _KR)
assert _spec and _spec.loader
kr: Any = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("_roadmap_registers", kr)
_spec.loader.exec_module(kr)

PRD_STATES = ["stub", "prd-drafted", "designed", "planned", "implementing", "verified", "shipped", "cancelled"]


def fm(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    block = text.split("---", 2)[1]
    out: dict[str, str] = {}
    for line in block.splitlines():
        m = re.match(r"([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


def load(kind: str, fname: str) -> list[tuple[Path, dict[str, str]]]:
    base = K / kind
    out = []
    if base.exists():
        for d in sorted(base.iterdir()):
            f = d / fname
            if f.is_file():
                out.append((f, fm(f)))
    return out


def render() -> str:
    programs = kr.programs()
    slices = kr.slices()
    prds = load("prds", "prd.md")

    # group: program id -> [slices]; slice id -> [prds]
    slice_by_program: dict[str, list[dict[str, Any]]] = {}
    for s in slices:
        slice_by_program.setdefault(s["program"], []).append(s)
    prd_by_slice: dict[str, list[tuple[Path, dict[str, str]]]] = {}
    for pf, m in prds:
        prd_by_slice.setdefault(m.get("slice", ""), []).append((pf, m))

    def pnum(m: dict[str, str]) -> str:
        return str(m.get("prd", "")).zfill(4)

    lines: list[str] = []
    lines.append("---")
    lines.append("type: roadmap")
    lines.append("generated: knowledge/scripts/gen_roadmap.py")
    lines.append("---")
    lines.append("")
    lines.append("# Roadmap")
    lines.append("")
    lines.append("> **Generated** from program / slice / PRD frontmatter by")
    lines.append("> `knowledge/scripts/gen_roadmap.py` — **do not edit by hand; run the generator.** Status,")
    lines.append("> priority, and target are read live from each PRD's frontmatter (the single source")
    lines.append("> of truth), so this board never drifts. Re-run after any status change.")
    lines.append("")

    # status summary
    counts: dict[str, int] = dict.fromkeys(PRD_STATES, 0)
    for _f, m in prds:
        counts[m.get("status", "")] = counts.get(m.get("status", ""), 0) + 1
    lines.append("## Status summary")
    lines.append("")
    lines.append(" · ".join(f"**{counts[s]}** {s}" for s in PRD_STATES if counts.get(s)))
    lines.append("")

    # by program → slice → PRD. Neither container carries a `status:` — completion is
    # computed from the member PRDs, so the only honest thing to render here is the
    # membership and each PRD's own authored state.
    lines.append("## By program")
    lines.append("")
    for im in sorted(programs, key=lambda p: p["id"]):
        # Program rows carry no `target` — the register column was deleted on 2026-08-17.
        # A program's schedule is not authored on the row (durable vs versioned), so the
        # suffix that used to render it is gone. The PRD index below keeps its per-PRD
        # `target` read from PRD frontmatter, which is still valid.
        lines.append(f"### {im['id']} — {im['title']}  ·  {im['kind']}")
        lines.append("")
        for pm in sorted(slice_by_program.get(im["id"], []), key=lambda s: s["id"]):
            members = sorted(prd_by_slice.get(pm["id"], []), key=lambda x: pnum(x[1]))
            lines.append(
                f"**{pm['id']} {pm['title']}** — {pm['kind']}" + (f" ({len(members)} PRDs)" if members else "")
            )
            for f, m in members:
                folder = f.parent.name
                num = pnum(m)
                prio = f" · {m['priority']}" if m.get("priority") else ""
                ms = f"  ·  milestone: {m['milestone']}" if m.get("milestone") else ""
                st = m.get("status", "")
                lines.append(f"- [{num}](prds/{folder}/prd.md) {m.get('title', '')} — **{st}**{prio}{ms}")
            lines.append("")

    # flat PRD index
    lines.append("## PRD index")
    lines.append("")
    lines.append("| PRD | Title | Status | Priority | Slice | Target |")
    lines.append("|---|---|---|---|---|---|")
    for f, m in sorted(prds, key=lambda x: pnum(x[1])):
        folder = f.parent.name
        lines.append(
            f"| [{pnum(m)}](prds/{folder}/prd.md) | {m.get('title', '')} | {m.get('status', '')} "
            f"| {m.get('priority', '')} | {m.get('slice', '')} | {m.get('target', '')} |"
        )
    lines.append("")

    return "\n".join(ln.rstrip() for ln in lines).rstrip("\n") + "\n"


def main(argv: list[str] | None = None) -> int:
    import sys

    argv = sys.argv[1:] if argv is None else argv
    out = render()
    target = K / "roadmap.md"
    if "--check" in argv:
        current = target.read_text(encoding="utf-8") if target.is_file() else ""
        if current != out:
            print(
                "roadmap.md is STALE — run `python3 knowledge/scripts/gen_roadmap.py` to regenerate "
                "(it is a generated projection of PRD/slice/program frontmatter)"
            )
            return 1
        print("roadmap.md is up to date")
        return 0
    target.write_text(out, encoding="utf-8")
    print("generated knowledge/roadmap.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
