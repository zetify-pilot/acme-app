"""The PLANNING TIER checks — the program / slice / PRD ladder and the ids that hold it together.

Eight validators ported whole from a repository that grew them one incident at a time, plus
`bars`, which was written here. Read together they enforce one property: **the plan is a
connected, well-formed graph before anything downstream reads it.** Every PRD names a slice,
every slice names a program, every id is permanent and unique, every proof pointer resolves,
and no tier above the PRD stores a ship-state that could drift from what its children say.

`bars` is the one that gates an OPTIONAL section, and it earns the exception by staying silent
on absence: it holds a bar that exists to its shape and to the sentence it decomposes, and
reports nothing at all about an entity that carries none.

`knowledge_fragments` guards the raw material the rest read: every per-row JSON file the corpus
stores must be readable, because the readers skip one they cannot parse and a skipped row is a
promise missing from every view (ENG-21062).

Auto-discovery contract: this package publishes `CHECKS`, and its submodules deliberately do
NOT. A runner that walks `fleet_knowledge/checks/` non-recursively finds this package and reads
the list; a runner that walks recursively finds the submodules too and reads nothing from them.
Either way each check is registered exactly once, which is the property that matters — a
duplicated gate reports every finding twice.

Each submodule also exposes a `cli(kb, ...)` that reproduces its original validator's stdout and
exit code byte for byte, so the `scripts/validate_*.py` entry points a hook or a CI job already
calls keep working while the logic lives here.
"""

from __future__ import annotations

from typing import Any

from . import (
    bars,
    components,
    id_collisions,
    knowledge_fragments,
    prd_commitments_section,
    prd_depends_on_prose,
    prd_ext_promotion,
    prd_plan_status,
    prd_plans,
    prd_scope_ledger,
    program_requires,
    slice_clause_digest,
    tracking_metadata,
)

#: Ordered widest-graph-first, so a reader who fixes them top-down fixes the structural
#: problems before the artifact-level ones that hang off the structure.
CHECKS: list[Any] = [
    knowledge_fragments.CHECK,
    tracking_metadata.CHECK,
    id_collisions.CHECK,
    components.CHECK,
    program_requires.CHECK,
    slice_clause_digest.CHECK,
    bars.CHECK,
    prd_plans.CHECK,
    prd_plan_status.CHECK,
    prd_commitments_section.CHECK,
    prd_scope_ledger.CHECK,
    prd_depends_on_prose.CHECK,
    prd_ext_promotion.CHECK,
]

__all__ = [
    "CHECKS",
    "bars",
    "components",
    "id_collisions",
    "knowledge_fragments",
    "prd_commitments_section",
    "prd_depends_on_prose",
    "prd_ext_promotion",
    "prd_plan_status",
    "prd_plans",
    "prd_scope_ledger",
    "program_requires",
    "slice_clause_digest",
    "tracking_metadata",
]
