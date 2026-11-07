"""Validators over a knowledge base — one module per family, auto-discovered.

**There is no registry here, and there must never be one.** Drop a module in this directory
exposing a module-level `CHECKS: list[Check]` and the runner finds it
(`fleet_knowledge.runner.discover`). A shared list would be the single file every author has to
edit, and a merge conflict on the list that decides what gates the build is the worst place
for a bad resolution — someone silently loses a check.

A module looks like this, and nothing else is required of it:

    from fleet_knowledge.config import KnowledgeBase
    from fleet_knowledge.runner import Finding

    class SliceProgramEdge:
        name = "slice-program-edge"          # kebab-case and STABLE: --only and
        title = "Every slice names a program" # disabled_checks address it by this
        description = (
            "The roll-up edge is authored on the slice and nowhere else. A slice naming no "
            "program is invisible to every reading above it."
        )

        def applies(self, kb: KnowledgeBase) -> bool:
            return kb.has("slices_register")   # False -> SKIPPED, never failed

        def run(self, kb: KnowledgeBase) -> list[Finding]:
            return [Finding(level="error", message="...", hint="...")]

    CHECKS = [SliceProgramEdge()]

Two rules earn their emphasis:

  * **`applies` before `run`.** A corpus without journeys must skip the journey checks with a
    line saying so. A red build over ground a project deliberately does not have is how people
    learn to pass `--no-verify`.
  * **A finding names its own fix.** `hint` in one sentence, `command` when a runnable one
    exists. The difference between a gate people use and a gate people route around is almost
    always whether it said what to do next.
"""

from __future__ import annotations
