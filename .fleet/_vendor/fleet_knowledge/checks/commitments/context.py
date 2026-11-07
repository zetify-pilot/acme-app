"""The run context every commitment check threads through its ported functions.

The validators these checks came from carried their state in module globals — `REPO`, `K`,
`errors`, `notes`, `BASELINE` — and their callers rebound those globals to point the same
code at a different tree (the self-tests, the statement guard's base-commit re-parse). That
works exactly once per process and makes two knowledge bases in one run impossible, which
is the first thing a package has to be able to do.

So the globals became this object. Nothing else changed: the functions read `ctx.root`
where they read `REPO`, append to `ctx.errors` where they appended to `errors`, and every
message is byte-for-byte what it was. The legacy `scripts/` entry points rebuild a context
from their own module globals on each call, so rebinding `vr.REPO` still works there.

**Paths only.** What a register row IS — the id shape, the vocabularies, the table's
columns — belongs to `fleet_knowledge.requirements`, and a todo row to `fleet_knowledge.todos`.
This object resolves WHERE to look and collects what was found; it never re-decides what a
row means.

Stdlib only.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ... import requirements as kkreq
from ...corpusref import Corpora
from .options import CommitmentsConfig

#: "Not passed": read the corpus declarations from the config file governing the run's root.
_FROM_FILE = Corpora()


@dataclass
class Context:
    """One knowledge base, one run's accumulated findings."""

    root: Path
    knowledge: Path
    cfg: CommitmentsConfig = field(default_factory=CommitmentsConfig)
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # The register ratchet's location. Overridable so a self-test never reads (or is
    # perturbed by) the real grandfathered set.
    baseline: Path | None = None
    # Same reason: a self-test points the todo register at a temp file rather than at the
    # corpus it is validating from.
    todo_register: Path | None = None
    # A seam, not a feature: `prose_files()` calls this to enumerate the extra prose roots,
    # so a caller can count the calls and prove the walk is memoised.
    claude_prose_files: Callable[[Path], list[Path]] | None = None
    # This corpus's name and the sibling corpora a repo-qualified reference (`fleet:FLT-104`)
    # may name — `[fleet.planning] corpus` / `[fleet.planning.corpora]`. Also where the run's
    # unverified cross-corpus references accumulate for the summary note. Not passed, it is
    # read from the config FILE governing `root` — a script entry point that builds its own
    # context (`validate_requirements.py`, `gen_requirement_status.py`) must see the same
    # siblings and owned prefixes `fleet_knowledge check` does, or every cross-corpus claim
    # reads as a dangling local one.
    corpora: Corpora = field(default_factory=lambda: _FROM_FILE)

    def __post_init__(self) -> None:
        if self.corpora is _FROM_FILE:
            self.corpora = Corpora.at(self.root)
        # A sibling's knowledge dir is repo-relative; a context built without one (a test, a
        # legacy shim) resolves it against this run's root.
        if self.corpora.root == Path():
            self.corpora.root = self.root

    # ── paths ────────────────────────────────────────────────────────────────
    @property
    def register_dir(self) -> Path:
        return kkreq.register_dir(self.knowledge, self.cfg.requirements_dir)

    @property
    def prd_dir(self) -> Path:
        return self.knowledge / self.cfg.prds_dir

    @property
    def baseline_path(self) -> Path:
        if self.baseline is not None:
            return self.baseline
        return self.root / self.cfg.baseline_dir / self.cfg.register_baseline

    @property
    def unclaimed_baseline_path(self) -> Path:
        return self.knowledge / self.cfg.unclaimed_baseline

    @property
    def todo_register_path(self) -> Path:
        if self.todo_register is not None:
            return self.todo_register
        return self.knowledge / self.cfg.todos_register

    @property
    def knowledge_prefix(self) -> str:
        """`knowledge/` — the corpus directory as a repo-relative path prefix.

        The coverage baseline and every register's `source_of_truth:` are written
        repo-relative, so the roots configured corpus-relative are joined through this.
        """
        try:
            return self.knowledge.relative_to(self.root).as_posix().rstrip("/") + "/"
        except ValueError:
            return ""

    def registers(self) -> list[Path]:
        """Every register file — through the one reader, never a second glob."""
        return kkreq.registers(self.knowledge, self.cfg.requirements_dir)

    # ── findings ─────────────────────────────────────────────────────────────
    def rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)

    def err(self, path: Path, msg: str) -> None:
        self.errors.append(f"{self.rel(path)}: {msg}")

    def note(self, msg: str) -> None:
        self.notes.append(msg)

    def reset(self) -> None:
        self.errors.clear()
        self.notes.clear()
        self.corpora.reset()


def default_context(
    root: Path,
    knowledge: Path | None = None,
    cfg: CommitmentsConfig | None = None,
) -> Context:
    return Context(root=root, knowledge=knowledge or (root / "knowledge"), cfg=cfg or CommitmentsConfig())


def context_for(kb: object) -> Context:
    """A `Context` for a `KnowledgeBase` — the shape every `Check` is handed."""
    root = Path(getattr(kb, "root", Path.cwd()))
    knowledge = Path(getattr(kb, "knowledge", root / "knowledge"))
    cfg = CommitmentsConfig.from_config(getattr(kb, "config", None))
    return Context(root=root, knowledge=knowledge, cfg=cfg, corpora=Corpora.of(kb))
