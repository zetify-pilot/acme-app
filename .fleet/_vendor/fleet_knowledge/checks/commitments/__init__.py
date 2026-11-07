"""Commitment checks: the register, the statement guard, coverage, the todo list.

Four validators that answer one question between them — *what did we decide, does the
corpus still say it, and is anything asserting a commitment nobody has a row for.*

**A family is a DIRECTORY, and `CHECKS` is exported once, here.** `runner.discover`
walks `fleet_knowledge.checks` with `pkgutil.iter_modules`, which yields packages as well as
modules, so a family that outgrows one file keeps working with no registry to edit — which
is the whole reason there is no registry. Exporting `CHECKS` from a submodule as well would
register everything twice under a recursive walk, so `checks.py` names its list
`ALL_CHECKS` and this file is the single export point. The instances are singletons, so a
runner that dedupes by identity and one that dedupes by `name` both get four.

**What a row IS is not decided here.** `fleet_knowledge.requirements` is the one reader of a
register row and `fleet_knowledge.todos` of a todo row; these modules are the JUDGEMENT over
those rows. What the checks resolve for themselves — where the corpus lives, which release
line is being built, the PRD lifecycle bands, the ratchets — goes through
`options.CommitmentsConfig`, whose defaults mirror `fleet_knowledge.config.Config` where it
already names the same thing. A corpus with no registers at all is SKIPPED by `applies()`,
never failed.
"""

from __future__ import annotations

from .checks import ALL_CHECKS, CommitmentCoverage, RequirementRegisters, RequirementStatementGuard, TodoRegister
from .context import Context, context_for, default_context
from .options import CommitmentsConfig

# The one export point the runner reads. Singletons, so a runner that dedupes by identity
# and one that dedupes by `name` both see four checks.
CHECKS = ALL_CHECKS

__all__ = [
    "CHECKS",
    "CommitmentCoverage",
    "CommitmentsConfig",
    "Context",
    "RequirementRegisters",
    "RequirementStatementGuard",
    "TodoRegister",
    "context_for",
    "default_context",
]
