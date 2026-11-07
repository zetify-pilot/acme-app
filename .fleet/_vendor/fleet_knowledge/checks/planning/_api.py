"""What the planning checks share with the package around them.

`Finding`, `Check`, `KnowledgeBase` and `Config` belong to the package spine and are simply
re-exported here, so the whole family binds to them through ONE import site rather than eight.
Everything else in this module is local scaffolding the ported validators need and the spine
has no opinion about: a `Report` that keeps a validator's exact stdout alongside the modelled
findings, and a `make_kb` for the `scripts/` shims and the fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fleet_knowledge.config import Config, KnowledgeBase
from fleet_knowledge.runner import Check, Finding

__all__ = [
    "ADVISORY",
    "ERROR",
    "WARNING",
    "Check",
    "Config",
    "Finding",
    "KnowledgeBase",
    "Report",
    "finding",
    "make_kb",
]

ERROR = "error"
WARNING = "warning"
ADVISORY = "advisory"


@dataclass
class Report:
    """What one ported validator produced in a single pass.

    `findings` are the modelled verdict the runner and the board read; `notes` are the
    advisory lines the original printed but never failed on; `error_lines` are the exact
    failure lines it printed.

    The last of those is kept alongside `findings` rather than derived from them because a
    couple of the ported messages carry their own path formatting ("`X` is missing — …"
    rather than "X: …"), and a renderer that reconstructed the line from the model would
    quietly change what a pre-commit hook prints. The whole point of the port is that this
    repository's gates behave identically after it.
    """

    findings: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    error_lines: list[str] = field(default_factory=list)
    #: Set when the validator could not run at all (no git, a shallow clone, a missing root).
    refusal: str | None = None

    @property
    def errors(self) -> list[Finding]:
        """The findings that gate. What a `cli()` prints under its FAILED header."""
        return [f for f in self.findings if f.level == ERROR]


def finding(
    level: str,
    message: str,
    *,
    path: Path | None = None,
    line: int | None = None,
    hint: str | None = None,
    command: str | None = None,
) -> Finding:
    """One finding. A thin constructor so every call site reads the same way."""
    return Finding(level=level, message=message, path=path, line=line, hint=hint, command=command)


def make_kb(root: Path, config: Config | None = None) -> KnowledgeBase:
    """A `KnowledgeBase` over `root`, whose corpus is `root/knowledge`.

    The `scripts/` shims and the fixtures are the only callers: production resolution is
    `fleet_knowledge.config.resolve`, and a second answer to "where is the knowledge base" is
    exactly what that function exists to prevent. This one is handed the answer.
    """
    from fleet_knowledge.paths import DEFAULT_DIR_NAME  # noqa: PLC0415 - one use, kept local

    return KnowledgeBase(root=root, knowledge=root / DEFAULT_DIR_NAME, config=config or Config())
