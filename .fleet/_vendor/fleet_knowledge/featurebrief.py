"""A feature map's BRIEF and its USES — the newcomer's reading of a map, never a second ledger.

The agreed schema (owner, 2026-10-31): a feature map carries a `brief:` block in its frontmatter
so a newcomer understands the feature in about thirty seconds, and its `## Capabilities` table is
re-cut into `###` USES — each a thing a person can do with the feature, one plain
paragraph of one or two sentences, then that use's rows.

```yaml
brief:
  summary: >-      # one sentence: what it is, and for whom
  problem: >-      # two or three sentences: what goes wrong without it
  example: >-      # three or four sentences: a named person doing a real job with it
  example_from: [journey-slug, ...]   # the journeys the example is drawn from (they must exist)
  not:             # one to three lines: what it is NOT
    - ...
```

**A row's use is the `###` section it sits in.** No list of capability ids is copied anywhere, so
nothing can drift: the same structural rule that makes a row's area the file it sits in. A final
`### Misfits (to move)` section is a recognised TRANSITIONAL home for rows that fit no use of the
feature while they wait to move to the map they belong in; its rows carry no use and a `misfit`
flag. A `### Retired` section is the STANDING home of rows that were retired or withdrawn: it is not a
use either, its rows carry no use and a `retired` flag, and they are out of the use count and of
every progress figure. One use may hold several tables (old sections had different column sets, and
rows move whole): every row under a `###` belongs to it. A `##` after `## Capabilities` (a `## Notes`
section, `## Gaps`) is not part of it.

**How many uses.** At least three, with no ceiling; a small map needs fewer — at least one when it has fewer than three
rows, none when it has no rows. Retired rows are not counted.

What is derived and never authored — who uses the feature (the covering journeys' personas) and
where it lives (`surfaces:`) — is the reader's business, not this module's.

Two parts, deliberately separate:

  * **Reading** (`parse_brief`, `capability_uses`, `use_of_lines`) never raises and never judges:
    a malformed brief still yields what could be read, plus the problems as sentences. A viewer
    degrades.
  * **Judging** (`brief_findings`) is the validator's half — what makes a brief or a use
    MALFORMED, which the `feature-briefs` check reports as errors.

**Stdlib only**, so the brief is read by a small parser for exactly the YAML subset the schema
uses (block and folded scalars, flow and block lists) rather than by a YAML library.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

__all__ = [
    "BRIEF_KEYS",
    "BRIEF_LIST_KEYS",
    "BRIEF_TEXT_KEYS",
    "MIN_USES",
    "MISFIT_HEADING",
    "RESERVED_AREA_SLUGS",
    "RETIRED_HEADING",
    "Use",
    "bare_ids",
    "brief_findings",
    "capability_uses",
    "has_brief",
    "live_rows",
    "loose_rows",
    "new_area_refusal",
    "parse_brief",
    "ship_state_words",
    "structure_of",
    "fewest_uses",
    "use_of_lines",
]

#: The brief's prose fields, in reading order.
BRIEF_TEXT_KEYS: Final = ("summary", "problem", "example")
#: The brief's list fields.
BRIEF_LIST_KEYS: Final = ("example_from", "not")
#: Every key a brief may carry — a closed set, so a misspelt key is a finding rather than a field
#: nothing reads.
BRIEF_KEYS: Final = (*BRIEF_TEXT_KEYS, *BRIEF_LIST_KEYS)

#: The heading of the transitional section for rows that fit no use. Matched case-insensitively.
MISFIT_HEADING: Final = "Misfits (to move)"

#: The heading of the standing section for retired or withdrawn rows. Matched case-insensitively.
RETIRED_HEADING: Final = "Retired"

#: SLUGS NO FEATURE MAY TAKE: `new` is the Features page's own "New feature" route (`#areas:new`), so a feature of
#: that slug would be a page nobody could open (2026-11-01). The map writer and the service's proposal check both read
#: this set.
RESERVED_AREA_SLUGS: Final[frozenset[str]] = frozenset({"new"})

#: The fewest uses a map is cut into (`fewest_uses` lowers the floor for a small map). There is NO ceiling: the owner
#: removed the six-use cap on 2026-11-03, and `tests/test_no_use_cap.py` fails if a count cap comes back.
MIN_USES: Final = 3

#: The heading under which the uses are cut.
CAPABILITIES_HEADING: Final = "Capabilities"

_BRIEF_LINE: Final = re.compile(r"^brief:[ \t]*(.*)$")
_KEY_LINE: Final = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:[ \t]+(.*))?$")
_BLOCK_SCALAR: Final = re.compile(r"^([>|])([+-]?)\s*(?:#.*)?$")
_H2: Final = re.compile(r"^##\s+(.+?)\s*#*\s*$")
_H3: Final = re.compile(r"^###\s+(.+?)\s*#*\s*$")
_ANY_HEADING: Final = re.compile(r"^#{1,6}\s")

#: Ship-state the brief and the use paragraphs may never assert: progress is DERIVED from PRD
#: `status:`, and a sentence that says "shipped" is a claim that never expires.
_SHIP_STATE: Final = re.compile(r"\b(shipped|partly built|planned|still open)\b", re.I)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _unquote(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):  # noqa: PLR2004 — a quoted scalar has two quote marks
        inner = v[1:-1]
        return inner.replace("''", "'") if v[0] == "'" else inner.replace('\\"', '"')
    return v


def _strip_comment(value: str) -> str:
    """A plain scalar's trailing ` # comment` removed — never inside a quoted one."""
    v = value.strip()
    if v[:1] in ("'", '"'):
        return v
    cut = re.search(r"\s#", v)
    return v[: cut.start()].rstrip() if cut else v


def _fold(lines: Sequence[str], style: str, chomp: str) -> str:
    """A block scalar's text: `>` folds lines into one (a blank line is a paragraph break), `|` keeps them."""
    body = [ln.strip() for ln in lines]
    while body and not body[-1]:
        body.pop()
    if style == "|":
        text = "\n".join(body)
    else:
        paras: list[str] = []
        current: list[str] = []
        for ln in body:
            if ln:
                current.append(ln)
            else:
                paras.append(" ".join(current))
                current = []
        paras.append(" ".join(current))
        text = "\n".join(paras)
    return text if chomp == "+" else text.strip()


def _flow_list(value: str) -> list[str]:
    inner = value.strip()[1:-1]
    return [_unquote(x) for x in inner.split(",") if x.strip()]


def has_brief(fm: str) -> bool:
    """Whether the frontmatter declares a `brief:` key at all."""
    return any(_BRIEF_LINE.match(line) for line in fm.splitlines())


def parse_brief(fm: str) -> tuple[dict[str, Any] | None, list[str]]:
    """`(brief, problems)` from a frontmatter block — `(None, [])` when it declares no `brief:`.

    The brief always carries every key in `BRIEF_KEYS` (`""` / `[]` when absent), so a reader never
    has to ask. `problems` are sentences naming what is malformed: an unknown or repeated key, a list
    field written as a scalar, a line that is not a `key: value`. Whatever could be read is still
    returned beside them.
    """
    lines = fm.splitlines()
    start = next((i for i, line in enumerate(lines) if _BRIEF_LINE.match(line)), None)
    if start is None:
        return None, []
    problems: list[str] = []
    match = _BRIEF_LINE.match(lines[start])
    inline = _strip_comment(match.group(1)) if match else ""
    brief: dict[str, Any] = dict.fromkeys(BRIEF_TEXT_KEYS, "") | {k: [] for k in BRIEF_LIST_KEYS}
    if inline and inline != "{}":
        problems.append("`brief:` must be a block of `key: value` lines, not a value on the same line.")
        return brief, problems
    block: list[str] = []
    for line in lines[start + 1 :]:
        if line.strip() and _indent(line) == 0:
            break
        block.append(line)
    seen: set[str] = set()
    child = next((_indent(ln) for ln in block if ln.strip() and not ln.strip().startswith("#")), 0)
    i = 0
    while i < len(block):
        line = block[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        if _indent(line) != child:
            problems.append(f"`brief:` line {line.strip()!r} is not indented like the keys around it.")
            i += 1
            continue
        km = _KEY_LINE.match(line.strip())
        if not km:
            problems.append(f"`brief:` line {line.strip()!r} is not a `key: value` line.")
            i += 1
            continue
        key, raw = km.group(1), (km.group(2) or "")
        i += 1
        nested: list[str] = []
        while i < len(block) and (not block[i].strip() or _indent(block[i]) > child):
            nested.append(block[i])
            i += 1
        value = _value(raw, nested)
        if key not in BRIEF_KEYS:
            problems.append(f"`brief:` has an unknown key `{key}` — the keys are {', '.join(BRIEF_KEYS)}.")
            continue
        if key in seen:
            problems.append(f"`brief:` names `{key}` twice.")
            continue
        seen.add(key)
        if key in BRIEF_LIST_KEYS:
            if isinstance(value, str):
                if value:
                    problems.append(f"`brief.{key}` must be a list (`[a, b]` or `- a` lines), not a sentence.")
                brief[key] = [value] if value else []
            else:
                brief[key] = value
        elif isinstance(value, list):
            problems.append(f"`brief.{key}` must be prose, not a list.")
            brief[key] = " ".join(value)
        else:
            brief[key] = value
    return brief, problems


def _value(raw: str, nested: Sequence[str]) -> str | list[str]:
    """One key's value from its own line's remainder and the deeper-indented lines under it."""
    value = _strip_comment(raw)
    block = _BLOCK_SCALAR.match(value)
    if block:
        return _fold(nested, block.group(1), block.group(2))
    if value.startswith("["):
        return _flow_list(value) if value.endswith("]") else [_unquote(value.strip("[]"))]
    content = [ln for ln in nested if ln.strip()]
    if not value and content and content[0].lstrip().startswith("-"):
        # EACH ITEM IS READ AS A SCALAR OF ITS OWN, exactly like a key's value: an item written `- >-` over indented
        # lines was once joined raw, so every "What it is not" line read ">- Not …" (owner, 2026-11-05). Blank lines
        # stay with their item, so a folded item keeps its paragraph break.
        items: list[tuple[str, list[str]]] = []
        item_indent = _indent(content[0])
        for ln in nested:
            stripped = ln.strip()
            if stripped and _indent(ln) == item_indent and stripped.startswith("-"):
                items.append((stripped[1:].strip(), []))
            elif items:
                items[-1][1].append(ln)
        return [x for x in (_scalar(head, body) for head, body in items) if x]
    return _scalar(value, content)


def _scalar(raw: str, nested: Sequence[str]) -> str:
    """One scalar — a key's value or a list item — from its first line's remainder and its deeper lines."""
    value = _strip_comment(raw)
    block = _BLOCK_SCALAR.match(value)
    if block:
        return _fold(nested, block.group(1), block.group(2))
    # A plain (or quoted) scalar, possibly continued on deeper lines: YAML folds those with spaces.
    joined = " ".join([value, *(ln.strip() for ln in nested if ln.strip())]).strip()
    return _unquote(_strip_comment(joined))


# ─────────────────────────── uses ───────────────────────────


@dataclass(frozen=True, slots=True)
class Use:
    """One `###` section under `## Capabilities`: a thing a person can do with the feature."""

    name: str
    #: The plain paragraph under the heading, joined onto one line; `""` when none was written.
    paragraph: str
    #: Its order among the map's uses, from 0.
    position: int
    #: Whether this is the transitional `### Misfits (to move)` section.
    misfit: bool
    #: The 0-based line span `[start, end)` of the section in the map's text.
    start: int
    end: int
    #: Whether this is the standing `### Retired` section.
    retired: bool = False

    @property
    def is_use(self) -> bool:
        """Whether this section is a USE — neither the misfit section nor the retired one."""
        return not (self.misfit or self.retired)

    def row(self) -> dict[str, Any]:
        """The serialisable reading: name, paragraph, position, misfit, retired."""
        return {
            "name": self.name,
            "paragraph": self.paragraph,
            "position": self.position,
            "misfit": self.misfit,
            "retired": self.retired,
        }


def _is_misfit(name: str) -> bool:
    return name.strip().lower() == MISFIT_HEADING.lower()


def _is_retired(name: str) -> bool:
    return name.strip().lower() == RETIRED_HEADING.lower()


def fewest_uses(rows: int) -> int:
    """The fewest uses a map with `rows` live capability rows should be cut into. There is no most."""
    if rows <= 0:
        return 0
    return 1 if rows < MIN_USES else MIN_USES


def _paragraph(lines: Sequence[str]) -> str:
    """The first plain paragraph of a section body: contiguous prose lines before any table, marker,
    blockquote, list or heading. A section that opens with its table has no paragraph."""
    out: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            if out:
                break
            continue
        if s.startswith(("|", "<!--", ">", "- ", "* ", "```")) or _ANY_HEADING.match(s):
            break
        out.append(s)
    return " ".join(out)


def capability_uses(text: str) -> list[Use]:
    """Every `###` section of the map's `## Capabilities`, in order — `[]` when it has none.

    Read from the whole document (frontmatter included, so line numbers are the file's own). A
    `###` under any other `##` is not a use: `## Gaps` and `## The minimal journey set` carry
    `###` sections of their own.
    """
    lines = text.splitlines()
    uses: list[Use] = []
    in_caps = False
    current: tuple[str, int] | None = None
    in_fence = False

    def close(end: int) -> None:
        nonlocal current
        if current is not None:
            name, begin = current
            uses.append(
                Use(
                    name=name,
                    paragraph=_paragraph(lines[begin + 1 : end]),
                    position=len(uses),
                    misfit=_is_misfit(name),
                    start=begin,
                    end=end,
                    retired=_is_retired(name),
                )
            )
            current = None

    body_start = _body_start(lines)
    for i, line in enumerate(lines):
        if i < body_start:
            continue
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        h2 = _H2.match(line)
        if h2 and not line.startswith("###"):
            close(i)
            in_caps = h2.group(1).strip().lower() == CAPABILITIES_HEADING.lower()
            continue
        if line.startswith("# "):
            close(i)
            in_caps = False
            continue
        h3 = _H3.match(line)
        if h3 and in_caps:
            close(i)
            current = (h3.group(1).strip(), i)
    close(len(lines))
    return uses


def _body_start(lines: Sequence[str]) -> int:
    """The first line after the frontmatter fence, or 0 when there is none."""
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return i + 1
    return 0


def use_of_lines(text: str, uses: Sequence[Use] | None = None) -> list[Use | None]:
    """For each line of `text`, the use whose section holds it, or `None`."""
    found = capability_uses(text) if uses is None else uses
    out: list[Use | None] = [None] * len(text.splitlines())
    for use in found:
        for i in range(use.start, min(use.end, len(out))):
            out[i] = use
    return out


# ─────────────────────────── judging ───────────────────────────


def ship_state_words(text: str) -> list[str]:
    """The ship-state words a sentence asserts ("shipped", "partly built", "planned", "still open")."""
    return list(dict.fromkeys(m.group(1).lower() for m in _SHIP_STATE.finditer(text)))


def bare_ids(text: str, prefixes: Iterable[str] = ("PG", "SL", "ENG", "CAP")) -> list[str]:
    """The internal ids a sentence names bare (`PG-38`, `SL-173`, `ENG-1234`, `CAP-0042`)."""
    alternatives = "|".join(sorted({re.escape(p) for p in prefixes if p}))
    if not alternatives:
        return []
    return list(dict.fromkeys(re.findall(rf"\b(?:{alternatives})-\d+\b", text)))


def loose_rows(text: str, cap_prefix: str = "CAP", uses: Sequence[Use] | None = None) -> list[int]:
    """The 1-based lines of capability rows (and fragment `<!-- rows: -->` markers) that sit under no use —
    outside every `###` section of `## Capabilities`. A row in the misfit section is reported as the misfit
    section, not again here."""
    at = use_of_lines(text, uses)
    row = re.compile(rf"^\|\s*{re.escape(cap_prefix)}-\d+\s*\|")
    marker = re.compile(r"^<!-- rows: \S+ -->$")
    out: list[int] = []
    for i, line in enumerate(text.splitlines()):
        s = line.strip()
        if (row.match(s) or marker.match(s)) and at[i] is None:
            out.append(i + 1)
    return out


def live_rows(
    text: str,
    cap_prefix: str = "CAP",
    uses: Sequence[Use] | None = None,
    fragments: Mapping[str, int] | None = None,
) -> int:
    """How many capability rows the map holds outside `### Retired`: its table rows, plus — for a fragment
    shell — the row fragments each `<!-- rows: <key> -->` marker stands for (`fragments`, `{key: count}`)."""
    at = use_of_lines(text, uses)
    row = re.compile(rf"^\|\s*{re.escape(cap_prefix)}-\d+\s*\|")
    marker = re.compile(r"^<!-- rows: (\S+) -->$")
    n = 0
    for i, line in enumerate(text.splitlines()):
        s = line.strip()
        use = at[i]
        if use is not None and use.retired:
            continue
        if row.match(s):
            n += 1
        elif (m := marker.match(s)) and fragments:
            n += fragments.get(m.group(1), 0)
    return n


def structure_of(text: str, cap_prefix: str = "CAP") -> tuple[Any, ...]:
    """What a STRUCTURAL edit changes, and nothing a cell edit does: the brief, each `###` section of
    `## Capabilities` (name and paragraph), which section every capability row (by id) and every fragment
    marker sits in. Two texts with the same structure differ only in row cells or in prose outside these.

    The feature-briefs ratchet bites on a structural edit only, so a run that records a shipping PRD in a
    `Ships in` cell is never made to author a whole brief.
    """
    brief, _problems = parse_brief(_frontmatter_block(text))
    uses = capability_uses(text)
    at = use_of_lines(text, uses)
    row = re.compile(rf"^\|\s*({re.escape(cap_prefix)}-\d+)\s*\|")
    marker = re.compile(r"^<!-- rows: (\S+) -->$")
    placed: list[tuple[str, str | None]] = []
    for i, line in enumerate(text.splitlines()):
        s = line.strip()
        m = row.match(s) or marker.match(s)
        if m:
            use = at[i]
            placed.append((m.group(1), None if use is None else use.name))
    brief_key = None if brief is None else tuple((k, str(brief[k])) for k in sorted(brief))
    return (brief_key, tuple((u.name, u.paragraph) for u in uses), tuple(sorted(placed, key=lambda p: p[0])))


def _frontmatter_block(text: str) -> str:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else ""


def brief_findings(
    brief: Mapping[str, Any] | None,
    problems: Sequence[str],
    uses: Sequence[Use],
    *,
    journey_slugs: Iterable[str] | None,
    id_prefixes: Iterable[str] = ("PG", "SL", "ENG", "CAP"),
    required: bool = False,
    loose: Sequence[int] = (),
    rows: int | None = None,
) -> list[tuple[str, str, int | None]]:
    """`(level, message, line)` for one map. `line` is the 1-based line it is about, else `None`.

    **Malformed is an error everywhere**: a malformed brief (`problems`), an `example_from` naming a journey
    that does not exist, and ship-state words or bare internal ids in the brief or a use paragraph.

    **Complete is a RATCHET** (owner, 2026-10-31). `required` says the map must be complete — the change being
    validated wrote it, or the repository turned the rule on for every map. Then a missing brief, an empty
    prose field, a use with no paragraph, a capability row under no use (`loose`, from `loose_rows`) and a use
    count outside the bounds are ERRORS. Otherwise each is ADVISORY, so a map nobody touched never turns a build
    red. Rows waiting in `### Misfits (to move)` and an empty `example_from` are advisory on every map.

    On a map that is neither required nor carries a brief, the use paragraphs are not judged at all: the
    brief is the opt-in, and a map not yet re-cut keeps whatever prose its old `###` sections carried.
    `journey_slugs` is `None` when the corpus has no journey catalog to resolve against. `rows` is the map's
    live (not retired) capability row count, which sets how many uses it should have (`fewest_uses`); `None`
    skips that count.
    """
    gap = "error" if required else "advisory"
    out: list[tuple[str, str, int | None]] = []
    if brief is None:
        out.append((gap, "has no `brief:` — a newcomer has nothing to read before the ledger.", None))
        if not required:
            return out
    out.extend(("error", p, None) for p in problems)
    prefixes = tuple(id_prefixes)
    given = brief or {}
    if brief is not None:
        for key in BRIEF_TEXT_KEYS:
            if not str(given.get(key) or "").strip():
                out.append((gap, f"`brief.{key}` is empty.", None))
    prose: list[tuple[str, str, int | None]] = [
        (f"`brief.{k}`", str(given.get(k) or ""), None) for k in BRIEF_TEXT_KEYS
    ]
    prose += [(f"`brief.not` line {n}", str(line), None) for n, line in enumerate(given.get("not") or [], 1)]
    prose += [(f"use “{u.name}”", u.paragraph, u.start + 1) for u in uses]
    for where, text, line in prose:
        words = ship_state_words(text)
        if words:
            out.append(
                (
                    "error",
                    f"{where} states ship-state ({', '.join(words)}) — progress is read from PRD `status:`, "
                    "never written.",
                    line,
                )
            )
        ids = bare_ids(text, prefixes)
        if ids:
            out.append(("error", f"{where} names internal ids bare ({', '.join(ids)}) — say it in plain words.", line))
    if journey_slugs is not None:
        known = set(journey_slugs)
        unknown = [s for s in given.get("example_from") or [] if s not in known]
        if brief is not None and not given.get("example_from"):
            # Advisory: a new area with no journey yet draws its example from the work that creates it.
            out.append(("advisory", "`brief.example_from` names no journey the example is drawn from.", None))
        if unknown:
            out.append(("error", f"`brief.example_from` names journeys that do not exist: {', '.join(unknown)}.", None))
    if rows is not None:
        fewest = fewest_uses(rows)
        n = sum(1 for u in uses if u.is_use)
        if n < fewest:
            out.append(
                (
                    gap,
                    f"is cut into {n} use(s); a map with {rows} capability row(s) takes at least {fewest}.",
                    None,
                )
            )
    for u in uses:
        if u.retired:
            continue
        if u.misfit:
            # ADVISORY on every map, even a required one: a headless run that adds a row fitting no use parks it
            # here and files a task, and it must still be able to commit (owner, 2026-10-31).
            out.append(
                (
                    "advisory",
                    f"capability rows wait in “{MISFIT_HEADING}” to move to the map they belong in.",
                    u.start + 1,
                )
            )
        elif not u.paragraph:
            out.append((gap, f"use “{u.name}” has no paragraph saying what a person does with it.", u.start + 1))
    if loose:
        out.append(
            (
                gap,
                f"{len(loose)} capability row(s) sit under no `###` use of `## Capabilities` "
                f"(first at line {loose[0]}).",
                loose[0],
            )
        )
    return out


def _blank(value: object) -> bool:
    return not isinstance(value, str) or not value.strip()


def new_area_refusal(area: Mapping[str, Any]) -> str:
    """`''` when a proposed new area's `brief` and `uses` are absent or ones the card can show and the map can carry,
    else why — the proposal parser's judge for them, handed in at the edge (`dispatch` imports nothing outside the
    standard library, so it cannot reach this reader itself).

    Both optional (a proposal written before them is what it was), and when present judged by this module, the map's
    own reader: the brief is `{summary, problem, example, example_from, not}`, the uses a list of `{name, paragraph}`,
    and neither may state ship-state or name an internal id bare — the person accepts the brief they read on the card,
    so it is held to the rule the map will be. Whether `example_from`'s journeys exist is the repository's, and
    `slice:create` refuses one that does not."""
    brief = area.get("brief")
    uses = area.get("uses", [])
    if brief is not None:
        if not isinstance(brief, dict) or sorted(set(brief) - set(BRIEF_KEYS)):
            return f"`newArea.brief` must be an object with only the keys {', '.join(BRIEF_KEYS)}."
        if any(not isinstance(brief.get(k, ""), str) for k in BRIEF_TEXT_KEYS) or any(
            not isinstance(brief.get(k, []), list) or any(_blank(x) for x in brief.get(k, [])) for k in BRIEF_LIST_KEYS
        ):
            return (
                "`newArea.brief`: summary, problem and example are strings; example_from and not are lists of strings."
            )
    if not isinstance(uses, list) or not all(isinstance(u, dict) and not _blank(u.get("name")) for u in uses):
        return "`newArea.uses` is optional, but when present it is a list of {name, paragraph} with a non-blank name."
    cut = [
        Use(str(u["name"]), str(u.get("paragraph") or ""), i, misfit=False, start=0, end=0) for i, u in enumerate(uses)
    ]
    said = [
        msg
        for level, msg, _line in brief_findings(brief if isinstance(brief, dict) else {}, (), cut, journey_slugs=None)
        if level == "error"
    ]
    return f"`newArea`: {said[0]}" if said else ""
