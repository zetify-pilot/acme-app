"""Promises are written in one plain sentence — an advisory reading of the wording standard.

Owner decision, 2026-10-28: a capability, a requirement rule and a journey's acceptance criterion
are read by people who did not write the code, many of them not native English speakers, and are
checked by a QA agent from outside the code. So each is one plain sentence in the product's words,
and the code's names — routes, status codes, environment variables, file paths, identifiers —
live in the Evidence (or Source) column, never in the sentence. The standard is the fourth rule of
`process/writing.md` and, in full with examples, *Wording a promise* in
`process/knowledge-bootstrap-formats.md`.

**Advisory, never an error, by design.** Wording is a judgement a reader makes; a regular
expression can only point at the rows most likely to need it. A long sentence may be the honest
shape of a rule with three exceptions, and a token the patterns read as code may be the product's
own word. So this check names each suspect row once, with the reason, and never fails a build.

What it reads, and what it ignores:

  * **requirement register rows** — the statement cell. A trailing *Testable: …* sentence is left
    out of the word count (it is the observation, not the promise) but not out of the code-token
    scan. A struck-through or superseded/rejected row is history and is skipped.
  * **feature-map capability rows** — the capability cell. A `**Name** — sentence` cell is read as
    a name (at most about eight words) and a sentence; a bare cell is read as one sentence.
  * **journey acceptance criteria** — each numbered line under an *Acceptance criteria* heading
    of a journey that is not retired, with its continuation lines. A leading environment tag
    (`` `[dev]` ``) and a struck-through criterion are skipped.
  * **feature map headings** — a map's H1 is the feature's name as people read it on the Features page,
    so an H1 that is only the slug (`# maintenance-core`) or says what the document is
    (`# Maintenance Core — feature capability ledger`) is named. The older ` — Capability Map` suffix,
    which the board reads past by contract, is not.
  * **feature briefs and uses** — a map's `brief:` (`summary`, `problem`, `example`, each `not`
    line) and each use's name and paragraph. A customer reads these first, on the feature's page,
    so they are held to the same words: every sentence at most 20 words, no code in it, and no more
    sentences than the brief's schema gives the field (a summary one, a use paragraph two).
    Whether the brief is well-formed is `feature-briefs`' to judge, not this check's.

Stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from fleet_knowledge.config import KnowledgeBase
from fleet_knowledge.runner import Finding

#: A sentence over this many words is flagged (the standard says "at most 20").
MAX_WORDS = 20
#: A capability name over this many words is flagged (the standard says "at most about 8").
MAX_NAME_WORDS = 10

STANDARD = "process/knowledge-bootstrap-formats.md → Wording a promise"
HINT = (
    "Rewrite it as one plain sentence in the product's words (" + STANDARD + "): move code names, "
    "routes, status codes, environment variables, paths and tunable numbers to the Evidence or "
    "Source column, and keep who, what, when and every exception."
)

# ── reading a cell ────────────────────────────────────────────────────────────

_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_TESTABLE = re.compile(r"\s*(?:\*\*|_|\*)?Testable:(?:\*\*|_|\*)?\s.*\Z", re.S | re.I)
_ENV_TAG = re.compile(r"^(?:\s*`?\[[A-Za-z0-9_-]+\]`?(?!\())+\s*")
_BOLD_NAME = re.compile(r"^\s*\*\*(.+?)\*\*\s*(?:[—–:-]+\s*)?(.*)\Z", re.S)
_EMPHASIS = re.compile(r"[*_]{1,3}(?=\S)|(?<=\S)[*_]{1,3}")
_WORD = re.compile(r"[\w`'’/.:-]*\w[\w`'’/.:-]*")

# ── what reads as code ────────────────────────────────────────────────────────

_SOURCE_EXT = "py|go|ts|tsx|js|jsx|mjs|md|json|ya?ml|toml|sql|sh|rs|java|kt|rb|css|scss|html|proto|tf|ini|cfg|lock"
#: Ordered: the first pattern a cell trips names the reason, so the specific ones come first.
_CODE: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("backticks", re.compile(r"`")),
    ("a route or URL path", re.compile(r"(?<![\w/<.])/(?:api/|[A-Za-z0-9_{}:.-]+/[A-Za-z0-9_{}:.-])")),
    ("a file path", re.compile(rf"(?<![\w])[\w./-]*\w\.(?:{_SOURCE_EXT})\b")),
    (
        "an HTTP status code",
        re.compile(
            r"(?<![\w.,-])(?:HTTP\s*)?(?:40[0-9]|41[0-8]|42[2-9]|431|451|50[0-4])\b"
            r"(?!\s*(?:ms|s|seconds?|minutes?|hours?|days?|rows?|bytes|KB|MB|GB|%|words?|"
            r"characters?|chars|items?|lines?|requests?|calls?|issues?|files?|tokens?)\b)"
            r"(?![.,]\d)"
        ),
    ),
    ("an environment variable", re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]*[A-Z0-9]\b")),
    ("a snake_case identifier", re.compile(r"\b[a-z][a-z0-9]*_[a-z0-9_]*[a-z0-9]\b")),
    ("a dotted identifier", re.compile(r"\b[a-z][a-z0-9_]+(?:\.[a-z_][a-z0-9_]+)+\b")),
)


def _plain(text: str) -> str:
    """The cell as a reader sees it: link text without its target, no emphasis markers."""
    return _EMPHASIS.sub("", _LINK.sub(r"\1", text)).strip()


def words(text: str) -> int:
    """The words a reader reads in `text` — punctuation alone (an em dash) is not a word."""
    return len(_WORD.findall(_plain(text)))


def code_reasons(text: str) -> list[str]:
    """What in `text` reads as the code's words rather than the product's, in pattern order."""
    bare = _LINK.sub(r"\1", text)
    found = [reason for reason, pattern in _CODE if pattern.search(bare)]
    if "a file path" in found and "a dotted identifier" in found:
        # `install.sh` is both; one name for it is enough.
        found.remove("a dotted identifier")
    return found


def split_testable(statement: str) -> tuple[str, str]:
    """`(promise, testable)` — the trailing *Testable: …* sentence split off, or `""`."""
    m = _TESTABLE.search(statement)
    if not m:
        return statement, ""
    return statement[: m.start()], statement[m.start() :]


# ── judging one promise ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class Suspect:
    """One promise the wording standard probably wants rewritten, and why."""

    promise: str
    reasons: tuple[str, ...]
    path: Path | None = None
    line: int | None = None


def judge_statement(statement: str) -> list[str]:
    """Why a requirement statement misses the standard; `[]` when it meets it."""
    promise, _testable = split_testable(statement)
    out: list[str] = []
    n = words(promise)
    if n > MAX_WORDS:
        out.append(f"{n} words (the standard is one sentence of at most 20)")
    out += [f"names {reason} in the sentence" for reason in code_reasons(statement)]
    return out


def judge_capability(cell: str) -> list[str]:
    """Why a capability cell misses the standard; `[]` when it meets it."""
    m = _BOLD_NAME.match(cell)
    name, sentence = (m.group(1), m.group(2)) if m else ("", cell)
    out: list[str] = []
    if name and words(name) > MAX_NAME_WORDS:
        out.append(f"a {words(name)}-word name (the standard is about 8)")
    n = words(sentence)
    if n > MAX_WORDS:
        out.append(f"{n} words (the standard is one sentence of at most 20)")
    out += [f"names {reason} in the sentence" for reason in code_reasons(cell)]
    return out


def judge_criterion(text: str) -> list[str]:
    """Why a journey acceptance criterion misses the standard; `[]` when it meets it."""
    body = _ENV_TAG.sub("", text)
    m = _BOLD_NAME.match(body)
    sentence = m.group(2) if m else body
    out: list[str] = []
    n = words(sentence)
    if n > MAX_WORDS:
        out.append(f"{n} words (the standard is one sentence of at most 20)")
    out += [f"names {reason} in the sentence" for reason in code_reasons(body)]
    return out


#: The most sentences each brief field holds, per the feature-brief schema (`featurebrief`).
BRIEF_SENTENCES: dict[str, int] = {"summary": 1, "problem": 3, "example": 4}
#: The most sentences a `not` line and a use paragraph hold.
NOT_SENTENCES = 1
USE_SENTENCES = 2

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“‘(])")


def sentences(text: str) -> list[str]:
    """The sentences of a short piece of prose, as a reader sees them."""
    return [s for s in _SENTENCE_END.split(_plain(text)) if words(s)]


def judge_prose(text: str, most: int) -> list[str]:
    """Why a brief field, a `not` line or a use paragraph misses the standard; `[]` when it meets it."""
    parts = sentences(text)
    out: list[str] = []
    if len(parts) > most:
        out.append(f"{len(parts)} sentences (the standard is at most {most})")
    longest = max((words(s) for s in parts), default=0)
    if longest > MAX_WORDS:
        out.append(f"a {longest}-word sentence (the standard is at most 20)")
    out += [f"names {reason} in the sentence" for reason in code_reasons(text)]
    return out


def judge_use(name: str, paragraph: str) -> list[str]:
    """Why a use's name or paragraph misses the standard; `[]` when both meet it."""
    out: list[str] = []
    if words(name) > MAX_NAME_WORDS:
        out.append(f"a {words(name)}-word name (the standard is about 8)")
    out += [f"its name names {reason}" for reason in code_reasons(name)]
    return out + judge_prose(paragraph, USE_SENTENCES)


# ── reading the corpus ────────────────────────────────────────────────────────

_STRUCK = re.compile(r"^\s*(?:\d+\.\s+)?~~")
_AC_HEADING = re.compile(r"^##\s+[^\n]*[Aa]cceptance criteria\b")
_H2 = re.compile(r"^##\s")
_ITEM = re.compile(r"^(\d+)\.\s+(.*)")
_RETIRED = re.compile(r"^status:\s*retired\s*$", re.M)


def _live_row(row: dict[str, object]) -> bool:
    disposition = str(row.get("disposition") or "").lower()
    if row.get("superseded") or disposition.startswith(("superseded", "rejected")):
        return False
    return not _STRUCK.match(str(row.get("statement") or ""))


def register_suspects(kb: KnowledgeBase) -> list[Suspect]:
    """Every live requirement register row whose statement misses the standard."""
    from fleet_knowledge import requirements  # noqa: PLC0415 — heavy, and only this reader needs it

    rows, _findings = requirements.load_registers(kb.knowledge, dir_name=kb.config.requirements_dir)
    out: list[Suspect] = []
    for rid, row in sorted(rows.items()):
        if not _live_row(row):
            continue
        reasons = judge_statement(str(row.get("statement") or ""))
        if reasons:
            line = int(row.get("line") or 0) or None
            out.append(Suspect(rid, tuple(reasons), Path(row["file"]), line))
    return out


def capability_suspects(kb: KnowledgeBase) -> list[Suspect]:
    """Every feature-map capability row whose cell misses the standard."""
    from fleet_knowledge import corpus  # noqa: PLC0415 — heavy, and only this reader needs it

    cfg = kb.config
    areas = corpus.features(
        kb.knowledge,
        features_dir=cfg.features_dir,
        aliases_file=cfg.capability_aliases,
        capability_prefix=cfg.capability_prefix,
    )
    out: list[Suspect] = []
    for area in areas:
        path = kb.knowledge / cfg.features_dir / f"{area['file']}.md"
        for cap in area.get("caps") or ():
            cell = str(cap.get("name") or "")
            if _STRUCK.match(cell):
                continue
            reasons = judge_capability(cell)
            if reasons:
                out.append(Suspect(str(cap.get("id") or ""), tuple(reasons), path))
    return out


def brief_suspects(kb: KnowledgeBase) -> list[Suspect]:
    """Every feature-brief field and use whose words miss the standard, named `<map> <part>`."""
    from fleet_knowledge import featurebrief  # noqa: PLC0415 — only this reader needs it
    from fleet_knowledge.checks.structure._feature_briefs import map_files  # noqa: PLC0415
    from fleet_knowledge.markdown import frontmatter  # noqa: PLC0415

    features = kb.knowledge / kb.config.features_dir
    if not features.is_dir():
        return []
    out: list[Suspect] = []
    for path in map_files(features):
        text = path.read_text(encoding="utf-8", errors="ignore")
        stem = path.name.split(".", 1)[0]
        brief, _problems = featurebrief.parse_brief(frontmatter(text))
        if not brief:
            # A map not yet cut into uses still carries its old `###` sections (build batches,
            # project notes): they are not uses, and `feature-briefs` asks for the re-cut first.
            continue
        for key, most in BRIEF_SENTENCES.items():
            reasons = judge_prose(str(brief.get(key) or ""), most)
            if reasons:
                out.append(Suspect(f"{stem} brief {key}", tuple(reasons), path))
        for n, line in enumerate(brief.get("not") or (), start=1):
            reasons = judge_prose(str(line), NOT_SENTENCES)
            if reasons:
                out.append(Suspect(f"{stem} brief not #{n}", tuple(reasons), path))
        for use in featurebrief.capability_uses(text):
            if not use.is_use:
                continue
            reasons = judge_use(use.name, use.paragraph)
            if reasons:
                out.append(Suspect(f"{stem} use “{use.name}”", tuple(reasons), path, use.start + 1))
    return out


#: A heading's suffix that names the DOCUMENT rather than the feature — "ledger" or "feature map" after a dash. The
#: older " — Capability Map" is the projection's own contract (`area_name` strips it) and is left alone.
_DOCUMENT_WORDS = re.compile(r"\s[—–-]+\s+.*\b(?:ledger|feature\s+map)\b", re.I)
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+")


def judge_heading(h1: str, slug: str) -> list[str]:
    """Why a feature map's H1 is not the feature's name as a person says it; `[]` when it is."""
    name = h1.strip()
    out: list[str] = []
    if name == slug or _SLUG.fullmatch(name):
        out.append("the heading is the slug; write the feature's name as people say it")
    if _DOCUMENT_WORDS.search(name):
        out.append("the heading says what the document is; write only the feature's name")
    return out


def heading_suspects(kb: KnowledgeBase) -> list[Suspect]:
    """Every feature map whose H1 is not the feature's name, named `<map> heading`."""
    from fleet_knowledge.checks.structure._feature_briefs import map_files  # noqa: PLC0415
    from fleet_knowledge.markdown import strip_frontmatter  # noqa: PLC0415

    features = kb.knowledge / kb.config.features_dir
    if not features.is_dir():
        return []
    out: list[Suspect] = []
    for path in map_files(features):
        text = path.read_text(encoding="utf-8", errors="ignore")
        stem = path.name.split(".", 1)[0]
        h1 = re.search(r"^#\s+(.+)$", strip_frontmatter(text), re.M)
        reasons = judge_heading(h1.group(1) if h1 else "", stem) if h1 else []
        if reasons:
            line = text[: text.find(h1.group(0))].count("\n") + 1 if h1 else None
            out.append(Suspect(f"{stem} heading", tuple(reasons), path, line))
    return out


def criteria(text: str) -> list[tuple[int, int, str]]:
    """`(ordinal, line, text)` for each numbered criterion under an acceptance-criteria heading.

    The ordinal counts every numbered line in file order, struck ones included, because that is
    how a criterion id `<slug>#<n>` is minted; a continuation line (indented, not a new item) is
    joined to the criterion it continues.
    """
    out: list[tuple[int, int, str]] = []
    inside = False
    n = 0
    for i, raw in enumerate(text.splitlines(), start=1):
        if _H2.match(raw):
            inside = bool(_AC_HEADING.match(raw))
            continue
        if not inside:
            continue
        item = _ITEM.match(raw)
        if item:
            n += 1
            out.append((n, i, item.group(2).strip()))
        elif out and raw.startswith((" ", "\t")) and raw.strip():
            ordinal, line, body = out[-1]
            out[-1] = (ordinal, line, f"{body} {raw.strip()}")
    return out


def criterion_suspects(kb: KnowledgeBase) -> list[Suspect]:
    """Every live journey acceptance criterion that misses the standard."""
    from fleet_knowledge import corpus  # noqa: PLC0415 — heavy, and only this reader needs it
    from fleet_knowledge.markdown import frontmatter  # noqa: PLC0415

    out: list[Suspect] = []
    for path, _tier in corpus.journey_files(kb.knowledge, kb.config.journeys_dir):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if _RETIRED.search(frontmatter(text)):
            continue
        for ordinal, line, body in criteria(text):
            if body.startswith("~~"):
                continue
            reasons = judge_criterion(body)
            if reasons:
                out.append(Suspect(f"{path.stem}#{ordinal}", tuple(reasons), path, line))
    return out


class PromiseWording:
    name = "promise-wording"
    title = "Promises are written in one plain sentence"
    description = (
        "A capability, a requirement rule and a journey's acceptance criterion are read by people "
        "who did not write the code and checked from outside it, so each is one plain sentence in "
        "the product's words, with code names, routes, status codes, environment variables and "
        "paths in the Evidence column. A feature's brief and its uses, which a customer reads first, "
        "are held to the same words. Advisory: it names the rows most likely to need rewording."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        return any(kb.has(option) for option in ("requirements_dir", "features_dir", "journeys_dir"))

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        suspects: list[Suspect] = []
        if kb.has("requirements_dir"):
            suspects += register_suspects(kb)
        if kb.has("features_dir"):
            suspects += capability_suspects(kb)
            suspects += brief_suspects(kb)
            suspects += heading_suspects(kb)
        if kb.has("journeys_dir"):
            suspects += criterion_suspects(kb)
        return [
            Finding(
                level="advisory",
                message=f"{s.promise}: {'; '.join(s.reasons)}",
                path=s.path,
                line=s.line,
                hint=HINT,
            )
            for s in suspects
        ]


CHECKS = [PromiseWording()]
