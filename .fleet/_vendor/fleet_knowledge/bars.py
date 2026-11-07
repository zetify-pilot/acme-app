"""The `## Bar` section of a program or slice detail file — its criteria, and what binds them.

A completion reading over a corpus is arithmetic over facts in git: every child cut finished,
every named proof artifact shipped. That reading cannot see whether the thing those artifacts
compose actually *works* in a running system, and it never could — its inputs are files. A bar
is the missing observation, authored ahead of the work: what somebody would have to see hold in
a running system to believe the claim, each condition stating its own RED in the same sentence
it makes its claim, and beside each the probe that could refute it.

**A bar is a commitment, never a verdict.** What it holds is the standard; whether the standard
is met today is an observation of a deployment at an instant, true of one moment and false an
hour later with no file changed. This module reads the commitment. Nothing here computes,
stores or returns a verdict, and nothing downstream of it should either.

**Both readers of a bar live outside this module, which is why the parse lives in the spine.**
The check that gates a commit and the reader that renders one need the same answer to "what does
this section say"; two parsers that disagreed about it would make every downstream reading a
matter of which one was asked — the argument `markdown` already makes about what a table row is.

**It parses; it does not judge.** An id in the wrong shape, a digest that is not hex, a
criterion with an empty probe are all read and handed back as authored. Deciding whether that is
well formed belongs to a check, and a parser that quietly dropped a malformed row would make a
whole class of finding unreachable — the row would simply not exist to complain about.

Two shapes, and the asymmetry between them is authored rather than incidental:

  * a **slice** bar decomposes the completion sentence of its register row — text in a DIFFERENT
    file — so it carries a digest over that cell's exact bytes. Edit the sentence and the digest
    breaks, which is the mechanism that stops a bar drifting to match whatever shipped.
  * a **program** bar decomposes a `**Demonstration.**` sentence authored inside the bar itself,
    so it binds across nothing and carries no digest. A digest over bytes in the section it
    guards breaks on nothing and reads to the next author like a check that is running.

**An absent section is legal, and `parse` returns None for it.** A bar is optional and monotone:
a corpus in which nothing carries one is a valid corpus, and adding one asks nothing of anybody.

Stdlib only.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

from .markdown import cells

#: The literal `## <heading>` a bar is authored under, at BOTH tiers. It is a top-level section
#: of the detail file: a bar nested under another `##` section does not nest, it ends that
#: section, and whatever the reader of *that* section derived from its body silently stops.
HEADING = "Bar"

#: The letter a criterion id carries, by the namespace of the entity that owns it. A slice's
#: criteria decompose a completion clause (`SL165-C1`); a program's decompose the demonstration
#: it authors in the bar itself (`PG24-P1`). This table is the whole of that convention — an id
#: is cited from outside git, so the shape has exactly one definition here and nowhere else.
SUFFIX_BY_PREFIX: dict[str, str] = {"SL": "C", "PG": "P"}

#: What an entity from an unrecognised namespace gets. A criterion is the general case.
DEFAULT_SUFFIX = "C"

_HEADING_RE = re.compile(rf"^##\s+{re.escape(HEADING)}\s*$", re.M)
_NEXT_H2_RE = re.compile(r"^##\s")
_ALPHA_PREFIX_RE = re.compile(r"^[A-Za-z]+")

#: The digest marker, matched PERMISSIVELY on purpose: the shape a marker must have (64
#: lowercase hex) is a rule, and a rule a parser enforces by not matching is a rule that reports
#: itself as an absent marker instead of a malformed one. Whatever follows `sha256:` comes back
#: verbatim so a check can say which of the two actually happened.
DIGEST_RE = re.compile(r"<!--\s*done-cell-digest:\s*sha256:\s*([^\s>]*)\s*-->", re.I)

#: The characters a `|---|---|` rule row is made of.
_SEPARATOR_CHARS = frozenset("-: ")

#: First cells that mark the table's header row rather than a criterion.
_HEADER_FIRST_CELLS = frozenset({"#", "id", "no", "no."})


@dataclass(frozen=True)
class Criterion:
    """One row of a bar: a falsifiable claim, and the observation that could refute it.

    `statement` and `probe` are the cells AS AUTHORED — no normalisation beyond the trimming
    and pipe-unescaping every table cell in this package gets, because a reader that tidied
    them would be showing a sentence nobody wrote.
    """

    id: str
    statement: str
    probe: str
    line: int


@dataclass(frozen=True)
class Bar:
    """One `## Bar` section, read as authored.

    `digest` is whatever followed `sha256:` in the marker, or None when the section carries no
    marker at all — the contract's shape (64 lowercase hex) is asserted by a check, not here.
    `scope` and `demonstration` are the paragraphs their bold lead-ins introduce, joined onto
    one line, and "" when the lead-in is absent.
    """

    entity: str
    tier: str
    scope: str
    demonstration: str
    digest: str | None
    criteria: tuple[Criterion, ...]
    line: int


def parse(body: str, entity: str, tier: str) -> Bar | None:
    """The bar in `body`, or None when there is no `## Bar` section at all.

    None is the ordinary answer, not a failure: the section is optional at both tiers.
    """
    located = _locate(body)
    if located is None:
        return None
    heading_line, section = located
    marker = DIGEST_RE.search(section)
    return Bar(
        entity=entity,
        tier=tier,
        scope=_lead(section, "Scope"),
        demonstration=_lead(section, "Demonstration"),
        digest=marker.group(1) if marker else None,
        criteria=tuple(_criteria(section, heading_line)),
        line=heading_line,
    )


def expected_prefix(entity: str) -> str:
    """The criterion-id prefix `entity`'s rows must carry: `SL-165` -> `SL165-C`.

    The dash goes because an id is cited inline in prose and in an issue tracker, where
    `SL-165-C1` reads as three fields rather than one name.
    """
    alpha = _ALPHA_PREFIX_RE.match(entity)
    suffix = SUFFIX_BY_PREFIX.get(alpha.group(0).upper(), DEFAULT_SUFFIX) if alpha else DEFAULT_SUFFIX
    return f"{entity.replace('-', '')}-{suffix}"


# ─────────────────────────── internals ───────────────────────────


def _locate(body: str) -> tuple[int, str] | None:
    """`(1-based line of the `## Bar` heading, the section text below it)`, or None.

    Line-scanned rather than taken from `markdown.section`, which strips its result: a finding
    has to name the line a criterion is authored on, and a stripped body has lost the offset
    that would give it. The extent is the same one that reader uses — up to the next `## `,
    so an `###` inside a bar stays inside it.
    """
    lines = body.splitlines()
    start = next((i for i, line in enumerate(lines) if _HEADING_RE.match(line)), None)
    if start is None:
        return None
    end = next((j for j in range(start + 1, len(lines)) if _NEXT_H2_RE.match(lines[j])), len(lines))
    return start + 1, "\n".join(lines[start + 1 : end])


def _lead(section: str, label: str) -> str:
    """The paragraph a `**<label>.**` lead-in opens, joined onto one line. "" when absent.

    A lead-in's paragraph runs to the next blank line: both of these run several lines, and a
    reader that took only the first would report half a sentence.
    """
    m = re.search(rf"^\*\*{re.escape(label)}\.\*\*[ \t]*([\s\S]*?)(?=\n[ \t]*\n|\Z)", section, re.M)
    return " ".join(m.group(1).split()) if m else ""


def _criteria(section: str, heading_line: int) -> Iterator[Criterion]:
    """Every criterion row of the section's table, with its line in the file.

    **Cells come from `markdown.cells`, and a three-group row regex would be a bug here.** A
    probe is free prose about a running system, so it names shell pipelines: one already reads
    `... --no-headers \\| awk ...`. An escaped pipe is TEXT inside the cell, and a pattern like
    `\\|\\s*([^|]+?)\\s*\\|` splits on it — every column after it shifts by one, the criterion half
    of the row is read as the whole row, and the probe half reads as an absent probe. That is a
    silent wrong answer rather than a parse failure, which is why the shared primitive is
    load-bearing and not merely tidier.

    Rows are yielded WHATEVER their first cell holds, so a typo'd or missing id is a row a check
    can see; only the header and the `|---|` rule are dropped, because neither was a criterion.
    """
    for line_no, line in enumerate(section.splitlines(), start=heading_line + 1):
        if not line.lstrip().startswith("|"):
            continue
        row = cells(line)
        if not row or _is_separator(row) or row[0].lower() in _HEADER_FIRST_CELLS:
            continue
        padded = [*row, "", ""]
        yield Criterion(id=padded[0], statement=padded[1], probe=padded[2], line=line_no)


def _is_separator(row: list[str]) -> bool:
    """True for a `|---|---|` rule row — and for a wholly empty one, which says nothing either."""
    return set("".join(row)) <= _SEPARATOR_CHARS
