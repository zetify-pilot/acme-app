"""The markdown primitives the planning checks read with.

Most of them come straight from `fleet_knowledge.markdown` and `fleet_knowledge.requirements` and
are re-exported here so the family has one import site — two readers that disagreed about what
a table row IS would make every finding downstream a matter of which one you asked.

Three things are defined here rather than taken from the spine, and each is a deliberate
divergence the ported validators depend on:

  * **`frontmatter` / `field` return `None`, not `""`.** A document WITHOUT frontmatter is a
    structural error a check must report; an empty block is not the same fact. That is the
    contract `fleet_knowledge.requirements` already keeps, so those two are taken from there
    rather than from `fleet_knowledge.markdown`, whose readers want the empty-string form.
  * **`listfield` reads the INLINE form only.** The tracking validator's `depends_on:` and
    `labels:` parsing has always been `name: [a, b]`; the spine's richer `listfield` also
    accepts a block list and a bare scalar, and widening the port's parser would change which
    documents fail.
  * **`find_cycle`** has no home in the spine yet, and three of these checks need it.
"""

from __future__ import annotations

import re
from pathlib import Path

from fleet_knowledge.markdown import cells, scalar
from fleet_knowledge.markdown import listcell as as_list
from fleet_knowledge.paths import rel
from fleet_knowledge.requirements import field, frontmatter

__all__ = [
    "as_list",
    "cells",
    "extract_section",
    "field",
    "find_cycle",
    "frontmatter",
    "is_placeholder",
    "is_separator",
    "listfield",
    "read",
    "rel",
    "scalar",
]

#: The characters a `|---|---|` rule row is made of.
SEPARATOR_CHARS = frozenset("-: ")
HEADING_RE = re.compile(r"^##\s+(\S.*)$")


def is_separator(row: list[str]) -> bool:
    """True for a `|---|---|` rule row."""
    return bool(row) and set("".join(row)) <= SEPARATOR_CHARS


def listfield(fm: str, name: str) -> list[str]:
    """An INLINE-list frontmatter field (`name: [a, b]`) -> list. See the module docstring."""
    m = re.search(rf"^{name}:\s*\[(.*?)\]", fm, re.M)
    if not m or not m.group(1).strip():
        return []
    return [x.strip().strip('"').strip("'") for x in m.group(1).split(",") if x.strip()]


def read(path: Path) -> str:
    """A file's text, or "" when it is not there. Never raises on a missing document."""
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def extract_section(text: str, heading_prefix: str) -> str | None:
    """Body of the first `## <heading_prefix>...` section, or None if absent.

    Prefix-matched and case-insensitive so `## Commitments (register)` still counts — the
    section is the evidence, not its exact suffix.
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m and m.group(1).strip().lower().startswith(heading_prefix.lower()):
            start = i + 1
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end]).strip()


def is_placeholder(section_text: str | None) -> bool:
    """True if a section is absent, empty, or still the unfilled template `<...>` line."""
    if not section_text:
        return True
    stripped = section_text.strip()
    return stripped.startswith("<") and stripped.endswith(">")


def find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    """One dependency cycle as a node path (e.g. `[a, b, a]`), else None.

    White/grey/black DFS. Edges to nodes absent from `graph` (dangling deps) are skipped —
    those have their own resolution check, so cycle detection stays orthogonal to them.
    """
    white, grey, black = 0, 1, 2
    color = dict.fromkeys(graph, white)
    path: list[str] = []

    def visit(n: str) -> list[str] | None:
        color[n] = grey
        path.append(n)
        for m in graph.get(n, []):
            if m not in color:
                continue  # dangling — the resolution check owns this
            if color[m] == grey:
                return path[path.index(m) :] + [m]
            if color[m] == white and (found := visit(m)):
                return found
        path.pop()
        color[n] = black
        return None

    for node in graph:
        if color[node] == white and (found := visit(node)):
            return found
    return None
