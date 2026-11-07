"""The markdown and YAML-frontmatter primitives every reader in this package shares.

Nothing here knows what a program, a PRD or a capability is — this is the layer that turns
a file into cells, fields and paragraphs, and it is deliberately the ONLY such layer. Two
readers that disagree about what a table row *is* would make every number downstream a
matter of which one you asked; the failures each rule below prevents are recorded on the
rule itself, because each of them actually happened.

Stdlib only.
"""

from __future__ import annotations

import re

# ─────────────────────────── tables ───────────────────────────

# Split a markdown row on UNESCAPED pipes only. `\|` is a literal pipe INSIDE a cell — a
# `Done when` sentence is free prose, and a capability's own description writes things like
# `(\`action\` \| \`gate\`)`. Splitting on those shifts every later column by one, which is
# how a fragment of a capability's prose was read as its `Ships in` cell and a shipped
# capability reported as a delivery gap.
CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")

# An empty cell. Authors reach for all three dashes, and an em-dash means "none".
EMPTY_CELLS = frozenset({"", "-", "–", "—", "n/a"})


def cells(line: str) -> list[str]:
    """One pipe-table row as trimmed cells, with escaped pipes restored as text."""
    return [c.strip().replace("\\|", "|") for c in CELL_SPLIT_RE.split(line.strip().strip("|"))]


def md_rows(body: str) -> list[list[str]]:
    """Every pipe-table row in a markdown block, as trimmed cells."""
    return [cells(line) for line in body.splitlines() if line.lstrip().startswith("|")]


def scalar(cell: str) -> str:
    """A single value, or "" — with the markdown emphasis/code markup stripped."""
    v = cell.strip().strip("`").strip()
    return "" if v.lower() in EMPTY_CELLS else v


def prose(cell: str) -> str:
    """A FREE-PROSE cell, with its markdown left exactly as authored. "" for an empty marker.

    **`scalar` is wrong for a sentence and this is the difference.** That reader strips a
    backtick off each END, which is right for a cell that IS a value — a `Kind` cell written
    `` `feature` `` means the kind `feature`, and the ticks are quoting, not content. A sentence
    that merely BEGINS with a code span is a different thing, and the strip eats half of it.

    Measured, on the corpus this package came from: one of 79 `Done when` cells opens
    `` `orchestrator` no longer exists as an agent definition… ``. Through `scalar` it arrives as
    ``orchestrator` no longer exists…`` — the opening mark eaten, the closing one left standing
    with no partner. Nothing downstream can put that back: a renderer sees one stray tick and
    prints it, which is exactly the punctuation-on-the-page that reading the marks exists to
    stop. The `EMPTY_CELLS` reading stays, because "—" still means none in a prose column too.
    """
    v = cell.strip()
    return "" if v.lower() in EMPTY_CELLS else v


def listcell(cell: str) -> list[str]:
    """A comma-separated cell -> list. Empty markers yield []."""
    v = cell.strip()
    if v.lower() in EMPTY_CELLS:
        return []
    return [x.strip().strip("`") for x in v.split(",") if x.strip() and x.strip().lower() not in EMPTY_CELLS]


# ─────────────────────────── frontmatter ───────────────────────────


def frontmatter(text: str) -> str:
    """The YAML block, or ""."""
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else ""


def strip_frontmatter(text: str) -> str:
    """The document body with its frontmatter block removed."""
    return re.sub(r"^---\n.*?\n---\n?", "", text, count=1, flags=re.S)


_YAML_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", '"': '"', "\\": "\\", "/": "/", " ": " "}


def unquote(raw: str) -> str:
    """A YAML scalar's value: the one place a quoted frontmatter value is decoded.

    A double-quoted scalar takes YAML's backslash escapes (`\\"`, `\\\\`, `\\n`), a single-quoted one only `''`; an
    unquoted value is returned as is. Stripping the quote characters alone left `has no \\"fixed\\" outcome` on every
    surface that showed a PRD's title.
    """
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] == '"':
        return re.sub(r"\\(.)", lambda m: _YAML_ESCAPES.get(m.group(1), m.group(0)), v[1:-1])
    if len(v) >= 2 and v[0] == v[-1] == "'":
        return v[1:-1].replace("''", "'")
    return v.strip('"').strip("'")


def field(fm: str, name: str) -> str:
    """A scalar frontmatter value.

    `[ \\t]*` and not `\\s*`: `\\s` matches a newline, so a greedy `\\s*` walks a key with an
    empty value (`implements:` followed by a block list) onto the next line and returns
    `- DMO-004` as if it were the scalar.
    """
    m = re.search(rf"^{name}:[ \t]*(.+)$", fm, re.M)
    return unquote(m.group(1)) if m else ""


def listfield(fm: str, name: str) -> list[str]:
    """A frontmatter list, inline `[a, b]` or block `- a`.

    Values stay STRINGS and keep their zero padding: a PRD's `depends_on: [0217]` is the id
    "0217", and every index in this package keys PRDs by that same 4-char string. Coercing
    to int here is what silently empties every reverse-dependency list.
    """
    inline = re.search(rf"^{name}:\s*\[(.*?)\]", fm, re.M)
    if inline:
        return [unquote(x) for x in inline.group(1).split(",") if x.strip()]
    single = field(fm, name)
    if single:
        return [unquote(x) for x in single.strip("[]").split(",") if x.strip()]
    block = re.search(rf"^{name}:\s*$((?:\n\s+-\s*.*)*)", fm, re.M)
    if block:
        items = re.findall(r"^\s+-\s*(.*)$", block.group(1), re.M)
        return [unquote(x) for x in items if x.strip()]
    return []


# ─────────────────────────── sections and bullets ───────────────────────────


def section(text: str, heading: str) -> str:
    """The body under a `## <heading>`, up to the next `## `.

    The heading is matched as LITERAL text (`re.escape`), so a heading carrying a dash or an
    ampersand cannot silently become a pattern.
    """
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s|\Z)", text, re.M | re.I)
    return m.group(1).strip() if m else ""


BULLET_RE = re.compile(r"^[-*]\s+(.*)$")

# The default ceiling on one inlined bullet. A viewer is an index, not a reader: it shows
# enough of a line to recognise it and links to the file for the rest.
BULLET_CHARS = 520


def bullets(body: str, cap: int, char_limit: int = BULLET_CHARS) -> list[str]:
    """The first `cap` bullet lines of a block, each clipped to `char_limit`."""
    out: list[str] = []
    for line in body.splitlines():
        m = BULLET_RE.match(line.strip())
        if m and m.group(1).strip():
            out.append(m.group(1).strip()[:char_limit])
        if len(out) >= cap:
            break
    return out


# ─────────────────────────── prose ───────────────────────────

# A sentence end, for the summary clip. `(?=\s|$)` is what keeps `org_<uuid>.<table>`,
# `tokens.css` and a version number from reading as the end of a sentence.
SENTENCE_END_RE = re.compile(r"[.?!](?=\s|$)")
TRAILING_PUNCT_RE = re.compile(r"[ ,;:—-]+$")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def clip(text: str, limit: int) -> str:
    """Shorten to ~limit, preferring a sentence boundary.

    Cutting mid-sentence produces a summary that reads as if the author trailed off, so a
    sentence end inside the budget wins even when it costs a third of the text — but only
    if it is not so early that the summary says nothing (a paragraph opening "Today, no."
    would otherwise render as those three words). Below that floor, and only then, fall
    back to a word-boundary cut marked with an ellipsis so the truncation is visible.
    """
    if len(text) <= limit:
        return text
    ends = [m.end() for m in SENTENCE_END_RE.finditer(text) if m.end() <= limit]
    if ends and ends[-1] > limit * 0.45:
        return text[: ends[-1]]
    head = text[:limit]
    space = head.rfind(" ")
    if space > limit * 0.6:
        head = head[:space]
    return TRAILING_PUNCT_RE.sub("", head) + "…"


def first_paragraph(body: str, limit: int) -> str:
    """The first real prose paragraph — skipping tables, quotes and lists."""
    for para in body.split("\n\n"):
        p = " ".join(para.split())
        if p and not p.startswith(("|", ">", "-", "*")):
            return clip(p, limit)
    return ""


def one_line(text: str, limit: int) -> str:
    """Prose joined onto one line and shortened on a WORD boundary.

    A hard `[:limit]` slice lands mid-word — one feature area's Intent ended "…delete
    blocked while a key is bou" — which reads as a corrupt file rather than as a clipped
    one. Same word-boundary tail `clip` uses, ellipsis included.
    """
    s = " ".join(text.split())
    if len(s) <= limit:
        return s
    head = s[:limit]
    space = head.rfind(" ")
    if space > limit * 0.6:
        head = head[:space]
    return TRAILING_PUNCT_RE.sub("", head) + "…"


def unquote_block(raw: str) -> str:
    """Prose out of a `> ` blockquote, joined onto one line.

    The marker is MARKUP, not text: joining the raw lines rendered an Intent as "…contract
    — an > allowed slice of ontology types > with…".
    """
    return " ".join(ln.strip().lstrip(">").strip() for ln in raw.splitlines() if ln.strip(" >"))


def plain(cell: str) -> str:
    """A table cell as prose: links flattened, emphasis and code ticks removed."""
    return MD_LINK_RE.sub(r"\1", cell).replace("**", "").replace("*", "").replace("`", "").strip()
