#!/usr/bin/env python3
"""Generate knowledge/adr-index.md — the read-only index of OUR engineering decision records.

Aggregates the two decision homes into one index:
  - standalone records in knowledge/decisions/*.md (type: decision), and
  - PRDs that captured architecture decisions in knowledge/prds/*/design.md
    (a non-empty `## Architecture notes` section).

The index is a *projection*, not a source: re-running regenerates it, so it can never
drift. Hand-edits are forbidden (the file carries a `generated:` marker). This indexes
*where* decisions live for discoverability; the decision text stays in its source.

**Named `adr-index.md`, not `decisions-ledger.md`.** The old name sat one letter away from
`knowledge/features/decision-ledger.md`, which is an unrelated *product* feature area — the
customer-facing record of the decisions an **agent** made. This file is the opposite
direction: an index of the decisions **we** made building the platform. Two documents whose
names differ by a plural cannot be told apart in a search result, a link, or a `type:`
value, so the one that is generated took the unambiguous name.

Run: python3 knowledge/scripts/gen_decision_ledger.py   (writes knowledge/adr-index.md)
     python3 knowledge/scripts/gen_decision_ledger.py --check   (CI/pre-commit staleness gate)
Stdlib only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

REPO = _repo.repo_root()
K = REPO / "knowledge"

DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
ARCH_RE = re.compile(r"^##+\s*Architecture notes\s*$(.*?)(^##\s|\Z)", re.M | re.S)


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


def standalone() -> list[dict[str, str]]:
    base = K / "decisions"
    out: list[dict[str, str]] = []
    if base.exists():
        for f in sorted(base.glob("*.md")):
            if f.name in ("README.md", "_TEMPLATE.md"):
                continue
            m = fm(f)
            md = DATE_RE.match(f.stem)
            out.append(
                {
                    "date": md.group(1) if md else "",
                    "title": m.get("title", f.stem),
                    "status": m.get("status", "accepted"),
                    "path": f"decisions/{f.name}",
                }
            )
    return out


def has_arch_notes(design: Path) -> bool:
    m = ARCH_RE.search(design.read_text(encoding="utf-8"))
    if not m:
        return False
    # Drop angle-bracket placeholders (unfilled template prompts) before the emptiness test.
    body = re.sub(r"<[^>]*>", "", m.group(1)).strip()
    return bool(body)


def prd_decisions() -> list[dict[str, str]]:
    base = K / "prds"
    out: list[dict[str, str]] = []
    if base.exists():
        for d in sorted(base.iterdir()):
            design = d / "design.md"
            if not design.is_file() or not has_arch_notes(design):
                continue
            pm = fm(d / "prd.md") if (d / "prd.md").is_file() else {}
            out.append(
                {
                    "prd": str(pm.get("prd", "")).zfill(4) if pm.get("prd") else d.name,
                    "title": pm.get("title", ""),
                    "path": f"prds/{d.name}/design.md",
                }
            )
    return out


def render() -> str:
    sd = standalone()
    pd = prd_decisions()
    lines: list[str] = []
    lines += ["---", "type: adr-index", "generated: knowledge/scripts/gen_decision_ledger.py", "---", ""]
    lines += ["# ADR Index — engineering decision records", ""]
    lines += [
        "> **Generated** by `knowledge/scripts/gen_decision_ledger.py` — **do not edit by hand; run",
        "> the generator.** A read-only index of every recorded decision **we** made building",
        "> the platform: standalone records in `decisions/` plus PRDs that captured architecture",
        "> decisions in their `design.md`. The decision text stays in its source; this is the",
        "> discoverability index. **Not** [`features/decision-ledger.md`](features/decision-ledger.md),",
        "> which is the unrelated product feature area covering the decisions an *agent* records.",
        "",
        f"**{len(sd)}** standalone · **{len(pd)}** PRDs with architecture decisions.",
        "",
        "## Standalone decisions",
        "",
    ]
    if sd:
        lines += ["| Date | Decision | Status |", "|---|---|---|"]
        for r in sorted(sd, key=lambda x: x["date"], reverse=True):
            lines.append(f"| {r['date']} | [{r['title']}]({r['path']}) | {r['status']} |")
    else:
        lines.append("_None yet._")
    lines += ["", "## PRD architecture decisions", ""]
    if pd:
        lines += ["| PRD | Title | Design |", "|---|---|---|"]
        for r in sorted(pd, key=lambda x: x["prd"]):
            lines.append(f"| {r['prd']} | {r['title']} | [design.md]({r['path']}) |")
    else:
        lines.append("_None yet._")
    lines.append("")
    return "\n".join(ln.rstrip() for ln in lines).rstrip("\n") + "\n"


def main(argv: list[str] | None = None) -> int:
    import sys

    argv = sys.argv[1:] if argv is None else argv
    out = render()
    target = K / "adr-index.md"
    if "--check" in argv:
        current = target.read_text(encoding="utf-8") if target.is_file() else ""
        if current != out:
            print(
                "adr-index.md is STALE — run `python3 knowledge/scripts/gen_decision_ledger.py` "
                "to regenerate (it is a generated index of decisions/ + PRD design.md ADRs)"
            )
            return 1
        print("adr-index.md is up to date")
        return 0
    target.write_text(out, encoding="utf-8")
    print("generated knowledge/adr-index.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
