"""fleet — read, derive from, and render a file-based knowledge base.

A `knowledge/` directory of markdown registers is a graph that no single file shows: a
program holds slices, a slice holds PRDs, a PRD claims commitments and ships capabilities,
and a capability is tested by a journey. This package is the reader for that graph, the
derivation over it, and two generators that render it.

Three properties are load-bearing, and every module here keeps them:

  * **Stdlib only.** No runtime dependency, so a validator, a hook or a CI step can run it
    with a bare `python3`.
  * **Root-parameterised.** Every reader takes the corpus directory. Nothing assumes a
    repository name, a checkout layout or a project's vocabulary.
  * **No dates, rates or estimates.** Nothing computes a duration, a velocity, a projection
    or a "what fits" number. Progress is a count; ordering is the dependency graph or a
    human's authored rank. **Nothing here emits a date at all** — the one that used to was
    the knowledge browser's generation stamp, and it went with the second renderer.

`README.md` states the corpus shape this package expects — that contract IS its interface.

    from fleet_knowledge import corpus, rollup
    from fleet_knowledge.config import resolve

    kb = resolve()                      # --knowledge-dir > env > .env > toml > discovery
    prds = corpus.prds(kb.knowledge)
    d = rollup.delivery(prds, corpus.slice_rows(kb.knowledge), corpus.program_rows(kb.knowledge))

`fleet_knowledge.config.KnowledgeBase` is the resolved corpus every entry point takes, and
`fleet_knowledge.runner` is the check protocol and its auto-discovering runner — drop a module
under `fleet_knowledge/checks/` exposing `CHECKS` and it is found, with no registry to edit.
"""

from __future__ import annotations

from . import (
    board,
    checks,
    config,
    corpus,
    documents,
    knowledge,
    markdown,
    paths,
    registers,
    release,
    requirements,
    rollup,
    runner,
    todos,
)
from .config import Config, ConfigError, KnowledgeBase, Origin, resolve
from .paths import KnowledgeRootNotFoundError, find_root, resolve_root
from .runner import Check, CheckResult, Finding, discover, run_checks

#: The Fleet release this package is (`release.version`), not the distribution's `0.1.0` placeholder
#: — the version a sync manifest records (ENG-18630). `0+unknown` when nothing names the release.
__version__ = release.version() or "0+unknown"

__all__ = [
    "Check",
    "CheckResult",
    "Config",
    "ConfigError",
    "Finding",
    "KnowledgeBase",
    "KnowledgeRootNotFoundError",
    "Origin",
    "__version__",
    "board",
    "checks",
    "config",
    "corpus",
    "discover",
    "documents",
    "find_root",
    "knowledge",
    "markdown",
    "paths",
    "registers",
    "release",
    "requirements",
    "resolve",
    "resolve_root",
    "rollup",
    "run_checks",
    "runner",
    "todos",
]
