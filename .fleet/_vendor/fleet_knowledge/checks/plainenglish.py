"""Prose a person reads is plain English — an advisory reading of the second writing rule.

The rule is `process/writing.md` → *Use plain English* (the style of ASD-STE100 Simplified
Technical English): most sentences under 15 words, none over 20, none of a short list of words
that sound clever and say little, and the approved word for each term in the rule's term list. This
check reads the markdown in a knowledge base and names the worst offenders. It keeps one length
limit (20) for every sentence: it cannot tell an instruction from a description without guessing.

**Advisory, never an error, by design.** It never fails a run. A long sentence may be the honest
shape of a rule, and a banned word may sit in a quotation. The check points; a person decides.

What it reads: the prose in every markdown file under `knowledge/`. What it skips: frontmatter,
fenced code, inline code, link targets, HTML comments, headings, and the Evidence, Source and
Tested-by columns of a table.

**It is cheap on a change.** When the run is told which commit it compares against (`--base`,
which a pull request or merge-queue run passes), it reads only the markdown files that change
touches, so it adds well under a second to the gate. Without a base, a run by hand or on `main`
reads the whole knowledge base. A large corpus then takes tens of seconds, so that is the reading
to ask for (`fleet check --only plain-english`), never one to wire into a change gate.

Stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from fleet_knowledge.checks.planning._git import changed_paths, git_out
from fleet_knowledge.config import KnowledgeBase, git_context
from fleet_knowledge.runner import Finding
from fleet_knowledge.writingrules import text as writing_rules_text

#: A sentence over this many words is named (the rule says "never go over 20").
MAX_WORDS = 20
#: The most findings listed. The last one says how many there were in all.
MAX_LISTED = 25

#: Words the rule says never to write.
BANNED = (
    "leverage",
    "robust",
    "seamless",
    "delve",
    "utilize",
    "facilitate",
    "streamline",
    "empower",
    "holistic",
    "synergy",
    "cutting-edge",
)
_BANNED = re.compile(r"(?<![\w-])(" + "|".join(re.escape(w) for w in BANNED) + r")(?![\w-])", re.I)

#: One line of the term list in `process/writing.md`: `- **approved** — not: a, b`.
_TERM_LINE = re.compile(r"^\s*-\s+\*\*(?P<ok>[^*]+)\*\*\s+—\s+not:\s+(?P<bad>.+?)\s*$")


def load_terms(rules: str | None = None) -> dict[str, str]:
    """`{avoided word: approved word}` read from the term list in the writing rules (one source).

    An all-capitals word such as `PR` is matched in that case only; any other word in any case.
    """
    out: dict[str, str] = {}
    for line in (writing_rules_text() if rules is None else rules).splitlines():
        m = _TERM_LINE.match(line)
        if m:
            for bad in m.group("bad").split(","):
                if bad.strip():
                    out[bad.strip()] = m.group("ok").strip()
    return out


def _terms_pattern(terms: dict[str, str]) -> re.Pattern[str] | None:
    """One pattern for every avoided word. A word is a whole word; a leading `(?i:` keeps case loose."""
    if not terms:
        return None
    parts = [re.escape(w) if w.isupper() else "(?i:" + re.escape(w) + ")" for w in sorted(terms, key=len, reverse=True)]
    return re.compile(r"(?<![\w-])(" + "|".join(parts) + r")(?![\w-])")


_TERMS = load_terms()
_TERMS_RE = _terms_pattern(_TERMS)
_TERMS_BY_LOWER = {w.lower(): ok for w, ok in _TERMS.items()}

#: A table column whose header says it holds evidence, not prose.
_EVIDENCE_HEADER = re.compile(r"^(evidence|source|sources|tested by|verified by)\b", re.I)

_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n?", re.S)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_FENCE = re.compile(r"^\s*(```|~~~)")
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_EMPHASIS = re.compile(r"[*_]{1,3}(?=\S)|(?<=\S)[*_]{1,3}")
_LIST_MARK = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_ABBREV = re.compile(r"\b(e\.g|i\.e|etc|vs|cf)\.", re.I)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“‘(])")
_WORD = re.compile(r"[\w'’-]+")

HINT = (
    "Split it into shorter sentences or use an everyday word (process/writing.md → Use plain "
    "English). This is advisory: leave it if the long sentence is the honest shape of the rule."
)


@dataclass(frozen=True)
class Hit:
    path: Path
    line: int
    score: int
    message: str


def _clean(text: str) -> str:
    """A unit of prose as a reader sees it: no link targets, no code, no emphasis marks."""
    text = _INLINE_CODE.sub(" ", _LINK.sub(r"\1", text))
    return _EMPHASIS.sub("", text).strip()


def _cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def units(text: str) -> list[tuple[int, str]]:
    """`(line, prose)` for each paragraph, list item and table cell a person reads."""
    text = _FRONTMATTER.sub(lambda m: "\n" * m.group(0).count("\n"), text, count=1)
    text = _COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    out: list[tuple[int, str]] = []
    para: list[str] = []
    start = 0
    fenced = False
    skip_cols: set[int] = set()
    in_table = False

    def flush() -> None:
        nonlocal para
        if para:
            out.append((start, " ".join(para)))
        para = []

    for n, raw in enumerate(text.splitlines(), start=1):
        if _FENCE.match(raw):
            flush()
            fenced = not fenced
            continue
        if fenced:
            continue
        line = raw.rstrip()
        if line.lstrip().startswith("|"):
            flush()
            cells = _cells(line)
            if not in_table:
                in_table = True
                skip_cols = {i for i, c in enumerate(cells) if _EVIDENCE_HEADER.match(_clean(c))}
                continue
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            for i, cell in enumerate(cells):
                if i not in skip_cols and cell:
                    out.append((n, cell))
            continue
        in_table = False
        if not line.strip():
            flush()
            continue
        if line.lstrip().startswith("#"):
            flush()
            continue
        if _LIST_MARK.match(line):
            flush()
            start = n
            para = [_LIST_MARK.sub("", line)]
            continue
        if not para:
            start = n
        para.append(line.strip())
    flush()
    return [(n, p) for n, p in out if p.strip()]


def hits_in(path: Path, text: str) -> list[Hit]:
    out: list[Hit] = []
    for line, unit in units(text):
        prose = _clean(unit)
        for sentence in _SENTENCE_END.split(_ABBREV.sub(lambda m: m.group(1).replace(".", ""), prose)):
            n = len(_WORD.findall(sentence))
            if n > MAX_WORDS:
                out.append(
                    Hit(
                        path,
                        line,
                        n - MAX_WORDS,
                        f"a {n}-word sentence (the rule says at most {MAX_WORDS}): “{sentence[:70].strip()}…”",
                    )
                )
        for m in _BANNED.finditer(prose):
            out.append(Hit(path, line, 5, f"the word “{m.group(1).lower()}” (the rule says never to write it)"))
        if _TERMS_RE:
            for m in _TERMS_RE.finditer(prose):
                ok = _TERMS_BY_LOWER[m.group(1).lower()]
                msg = f"the word “{m.group(1)}”: the approved word is “{ok}” (one word, one meaning)"
                out.append(Hit(path, line, 2, msg))
    return out


class PlainEnglish:
    name = "plain-english"
    title = "Prose a person reads is plain English"
    description = (
        "People who read the knowledge base are often not native English speakers, so its prose "
        "follows the style of ASD-STE100 Simplified Technical English: every sentence has 20 words "
        "or fewer, it avoids a short list of words that sound clever and say little, and it uses "
        "the approved word for each term in the writing rules. Advisory: it lists the worst "
        "sentences and never fails a run."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        return kb.knowledge.is_dir()

    @staticmethod
    def _files(kb: KnowledgeBase) -> list[Path]:
        """The markdown to read: what this change touches when a base is given, else all of it."""
        base = git_context(kb).base
        changed = changed_paths(kb.root, base) if base else None
        if changed is None:
            return sorted(kb.knowledge.rglob("*.md"))
        changed |= {ln for ln in git_out(kb.root, "ls-files", "--others", "--exclude-standard").splitlines() if ln}
        files = (kb.root / rel for rel in sorted(changed) if rel.endswith(".md"))
        return [p for p in files if p.is_file() and kb.knowledge in p.parents]

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        hits: list[Hit] = []
        for path in self._files(kb):
            hits += hits_in(path, path.read_text(encoding="utf-8", errors="ignore"))
        hits.sort(key=lambda h: (-h.score, str(h.path), h.line))
        found = [
            Finding(level="advisory", message=h.message, path=h.path, line=h.line, hint=HINT) for h in hits[:MAX_LISTED]
        ]
        if len(hits) > MAX_LISTED:
            found.append(
                Finding(level="advisory", message=f"{len(hits)} places in all; the {MAX_LISTED} worst are listed above")
            )
        return found


CHECKS = [PlainEnglish()]
