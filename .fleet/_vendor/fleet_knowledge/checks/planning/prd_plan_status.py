"""Gate: a PRD that carries plan files has been flipped to `planned` (or later).

WHY THIS EXISTS. `prd:plan` Step 7 flips the PRD's frontmatter `status:` to `planned` in
the SAME commit as the plan files. That flip is the only thing the fleet's projection reads: a
PRD left at `designed` keeps its tracker issue at "Needs Plan" however many plan files sit beside
it. PRD 0852's plan PR added `backend-plan.md` and `frontend-plan.md` and left `prd.md` at
`designed`; the issue sat in "Needs Plan" for hours until the flip was made by hand. Step 7 was
prose, so nothing failed when it was forgotten.

WHAT IT CHECKS. For every PRD directory, if any plan file exists (the same family
`prd_plans.discover_plans` finds), `prd.md`'s `status:` must sit at `planned` on the PRD status
ladder or beyond it. The ladder is `PlanningConfig.prd_order` — read, never restated. `cancelled`
is off the ladder and is accepted: a PRD cancelled after it was planned keeps its plans as a
record. A `prd.md` with no readable `status:` is skipped; the tracking-metadata check owns that
defect.

NOT history-bound and not cutover-bound: the property is a plain fact about the tree at HEAD, so
it needs no git walk and works in a shallow clone.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ._api import ERROR, Report, finding
from ._config import PlanningConfig
from ._markdown import field, frontmatter, read, rel
from .prd_plans import discover_plans

NAME = "prd-plan-status"

__all__ = ["CHECK", "NAME", "PrdPlanStatusCheck", "analyse", "cli"]

#: The ladder rung a PRD with plans must have reached.
REQUIRED = "planned"


def analyse(kb: Any) -> Report:
    cfg = PlanningConfig.of(kb)
    root = Path(kb.root)
    report = Report()
    order = cfg.prd_order
    floor = order.index(REQUIRED)

    by_prd: dict[Path, list[Path]] = {}
    for plan in discover_plans(kb):
        by_prd.setdefault(plan.parent, []).append(plan)

    for prd_dir in sorted(by_prd):
        prd_md = prd_dir / "prd.md"
        fm = frontmatter(read(prd_md))
        status = field(fm, "status") if fm else ""
        if not status or status == "cancelled":
            continue
        if status in order and order.index(status) >= floor:
            continue
        names = ", ".join(sorted(p.name for p in by_prd[prd_dir]))
        number = prd_dir.name.split("-", 1)[0]
        report.findings.append(
            finding(
                ERROR,
                f"PRD {number} carries {names} but prd.md is `status: {status}` — a planned PRD "
                f"reads `{REQUIRED}`, and the fleet's projection keeps a PRD below `{REQUIRED}` in "
                '"Needs Plan" however many plan files exist',
                path=prd_md,
                hint=(
                    f"In {rel(prd_md, root)} frontmatter set `status: {REQUIRED}` and append "
                    f"`- {{ state: {REQUIRED}, at: <ISO-8601 UTC>, by: plan }}` to `status_history:`, "
                    "in the same commit as the plan files (prd:plan Step 7)."
                ),
                command=cfg.command("prd_plan", prd=number),
            )
        )
    return report


class PrdPlanStatusCheck:
    """A PRD with plan files reads `planned` or later."""

    name = NAME
    title = "PRDs with plans are flipped to planned"
    description = (
        "prd:plan Step 7 flips the PRD to `planned` in the same commit as its plan files, and the "
        "fleet's projection reads only that flip: plans beside a `designed` PRD leave its tracker "
        'issue in "Needs Plan". Any PRD directory holding a plan file must read `planned` or later on '
        "the status ladder (`cancelled` excepted); the failure names the PRD, the files and the exact "
        "frontmatter edit."
    )

    def applies(self, kb: Any) -> bool:
        return bool(discover_plans(kb))

    def run(self, kb: Any) -> list[Any]:
        return analyse(kb).findings


CHECK = PrdPlanStatusCheck()


def cli(kb: Any) -> int:
    errors = analyse(kb).errors
    if errors:
        print("PRD plan status validation failed:")
        for e in errors:
            print(f"- {e.message}\n    fix: {e.hint}")
        return 1
    print("PRD plan status OK")
    return 0
