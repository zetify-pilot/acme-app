"""Structure checks — does the corpus hold together as a graph?

Six checks, five of them ports of a standalone validator, each answering one question about
the shape of a knowledge base rather than the content of any one document:

  * `knowledge-types`       — every file matches exactly one type from the project's own
                              registry, and declares it.
  * `knowledge-paths`       — every path a doc names resolves.
  * `knowledge-hygiene`     — the cross-subtree rules no single register owns.
  * `arch-docs`             — the architecture-doc freshness contract.
  * `journeys-and-features` — capability ids, the `Needs` DAG, journey↔capability links
                              in both directions, and exhaustive source coverage.
  * `feature-briefs`        — each feature map's brief and `###` uses: malformed is an
                              error, incomplete is an error on a map this change writes.

Each declares an honest `applies()`: a knowledge base with no `journeys/`, no
`features/`, no `specs/` or no type registry is SKIPPED with a clear "not applicable"
line, never failed. That is what makes the set portable — this repository keeps every
gate it had, and a different corpus runs only the checks its own shape supports.

`CHECKS` is exported here rather than from the individual modules so the runner finds
each check exactly once whether it walks this package recursively or not.
"""

from __future__ import annotations

from ._arch_docs import ArchDocsCheck
from ._feature_briefs import FeatureBriefs
from ._journeys import JourneysCheck
from ._kit import Check
from ._knowledge_hygiene import KnowledgeHygieneCheck
from ._knowledge_paths import KnowledgePathsCheck
from ._knowledge_types import KnowledgeTypesCheck

CHECKS: list[Check] = [
    KnowledgeTypesCheck(),
    KnowledgePathsCheck(),
    KnowledgeHygieneCheck(),
    ArchDocsCheck(),
    JourneysCheck(),
    FeatureBriefs(),
]

__all__ = [
    "CHECKS",
    "ArchDocsCheck",
    "FeatureBriefs",
    "JourneysCheck",
    "KnowledgeHygieneCheck",
    "KnowledgePathsCheck",
    "KnowledgeTypesCheck",
]
