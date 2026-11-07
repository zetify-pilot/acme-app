"""The docs checks — silent until a repository answers the `docs` slot.

Two checks, one shared trigger. A repository with no `docs` answer has no docs home, no
page tree and no docs program, and both checks SKIP with a reason rather than failing over
ground it deliberately does not have. See `_harness` for the home contract every reader
here shares.

`CHECKS` is exported from this package, and its submodules deliberately do not export one,
so the runner finds each check exactly once whether it walks this package recursively or not.
"""

from __future__ import annotations

from fleet_knowledge.runner import Check

from .checks import DocsCoverageCheck, DocsPagesCheck

CHECKS: list[Check] = [DocsPagesCheck(), DocsCoverageCheck()]

__all__ = [
    "CHECKS",
    "DocsCoverageCheck",
    "DocsPagesCheck",
]
