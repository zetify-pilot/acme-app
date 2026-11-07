"""What a PRD's `depends_on:` may hold: other PRD numbers, and tracker issue keys.

A PRD can wait on two kinds of thing. Most of the time it is another PRD (`0845`). Sometimes it is a
**bug fix filed in the tracker** (`ENG-16070`) that is not, and should not become, a PRD: the
workspace-boundary defect PRD 0864 sat behind was named in prose only, so the driver, which reads
`depends_on` and nothing else, designed it without waiting. One list carries both because the PRD
already has exactly one place a reader looks for "what must be true before this starts".

This module is the single reading of that list. A consumer that walks the PRD graph wants the numbers
(`prd_numbers`); the one that gates on the tracker wants the keys (`issue_keys`); nobody should split
the list by hand, because a half-split is how a key ends up `zfill`ed into a PRD number.

Pure: no I/O, no clock.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

__all__ = ["ISSUE_KEY_RE", "is_issue_key", "issue_keys", "prd_numbers", "split_dependencies"]

#: A tracker key: team prefix, dash, number. Requirement ids (`GOV-150`) share the shape, which is why a
#: caller that SCANS PROSE must pass the prefixes the tracker owns; a `depends_on:` entry is authored, so
#: here the shape alone decides.
ISSUE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}-\d+$")


def is_issue_key(entry: str) -> bool:
    """Whether one `depends_on:` entry names a tracker issue rather than a PRD."""
    return bool(ISSUE_KEY_RE.match(entry.strip()))


def split_dependencies(entries: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """`(PRD entries, tracker keys)`, each in authored order, entries stripped and empties dropped."""
    prds: list[str] = []
    keys: list[str] = []
    for raw in entries:
        entry = str(raw).strip()
        if not entry:
            continue
        (keys if is_issue_key(entry) else prds).append(entry)
    return tuple(prds), tuple(keys)


def prd_numbers(entries: Iterable[str]) -> tuple[str, ...]:
    """The PRD entries of `entries` — what a graph walk reads."""
    return split_dependencies(entries)[0]


def issue_keys(entries: Iterable[str]) -> tuple[str, ...]:
    """The tracker keys of `entries` — what the tracker gate reads."""
    return split_dependencies(entries)[1]
