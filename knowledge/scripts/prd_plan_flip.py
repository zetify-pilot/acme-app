#!/usr/bin/env python3
"""Flip a PRD to `planned` — prd:plan Step 7, as a command instead of a thing to remember.

    python3 knowledge/scripts/prd_plan_flip.py knowledge/prds/NNNN-slug      # or .../prd.md

Sets `status: planned` and appends `- { state: planned, at: <now UTC>, by: plan }` to
`status_history:`, ONLY when the PRD reads `designed`. Already `planned` or later: no-op (a
re-run just refreshes the plan files). `stub` / `prd-drafted`: refuses, the PRD is not designed.

Exit 0 flipped or already past it; 1 refused; 2 cannot read the PRD. Stdlib only.
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

_repo.fleet_knowledge()

from fleet_knowledge.checks.planning._config import PlanningConfig  # noqa: E402


def flip(text: str, now: str) -> tuple[str, str]:
    """Return (new text, outcome) where outcome is `flipped`, `already:<status>` or `refused:<status>`."""
    m = re.match(r"^---\n(.*?)\n---(\n|$)", text, re.S)
    if not m:
        return text, "refused:no-frontmatter"
    fm = m.group(1)
    sm = re.search(r"^status:[ \t]*(\S+)[ \t]*$", fm, re.M)
    status = sm.group(1).strip("\"'") if sm else ""
    order = PlanningConfig().prd_order
    if status == "designed":
        pass
    elif status in order and order.index(status) > order.index("designed"):
        return text, f"already:{status}"
    else:
        return text, f"refused:{status or 'missing'}"
    entry = f"  - {{ state: planned, at: {now}, by: plan }}"
    fm = re.sub(r"^status:[ \t]*\S+[ \t]*$", "status: planned", fm, count=1, flags=re.M)
    # The history block: the key line plus every indented line under it. Append after the last.
    hm = re.search(r"^status_history:[^\n]*(?:\n[ \t]+[^\n]*)*", fm, re.M)
    if hm:
        fm = fm[: hm.end()] + "\n" + entry + fm[hm.end() :]
    else:
        fm = re.sub(r"^status: planned$", "status: planned\nstatus_history:\n" + entry, fm, count=1, flags=re.M)
    return "---\n" + fm + text[m.end(1) :], "flipped"


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    p = Path(argv[0])
    p = p / "prd.md" if p.is_dir() else p
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        print(f"cannot read {p}: {e}")
        return 2
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    new, outcome = flip(text, now)
    if outcome == "flipped":
        p.write_text(new, encoding="utf-8")
        print(f"{p}: designed -> planned")
        return 0
    if outcome.startswith("already:"):
        print(f"{p}: already {outcome.split(':', 1)[1]} - left alone")
        return 0
    print(f"{p}: refused - status is `{outcome.split(':', 1)[1]}`; only a `designed` PRD can be planned")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
