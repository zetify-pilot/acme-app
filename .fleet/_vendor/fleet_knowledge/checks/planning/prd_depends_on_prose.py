"""Gate: a PRD that is still to be built lists in `depends_on:` every PRD and bug fix its text waits on.

WHY THIS EXISTS. The auto-driver designs, plans and implements a PRD once every entry of its
frontmatter `depends_on:` has shipped, and asks the person when one is planned but not built. It reads
that list and NOTHING ELSE. PRD 0864 carried `depends_on: []` while its own text said it composes with
PRD 0845 (team files) and PRD 0861 (meeting files), both planned and not built, and named a tracker bug
(ENG-16070) as a hard prerequisite, in prose. The driver designed it without asking. A dependency that
lives only in a sentence is invisible to the one reader that acts on it.

WHAT IT CHECKS. For a PRD at `prd-drafted`, `designed` or `planned` (before any code exists, the only
time the edge can still gate anything):

  * a line that carries a DEPENDENCY CUE ("depends on", "prerequisite", "builds on", "branch point",
    "assumes", "blocked by", "waits for", ...) and names another PRD by its four-digit number must see
    that number in `depends_on:`;
  * a line that carries a PREREQUISITE CUE ("depends on", "prerequisite", "once ... has merged",
    "merges first", ...) and names a tracker issue (a key with one of the tracker's prefixes) must see
    that key in `depends_on:` too.

A PRD that already lists THIS one in its own `depends_on:` (directly or through others) is never asked for: it
is built on top of this PRD, and listing it here would be a cycle `tracking-metadata` rejects.

HOW TO SAY "NOT A DEPENDENCY". Three spellings, all already at home in the corpus: list the PRD in the
frontmatter field `related: [0845]`; write `(not a dependency: <reason>)` on the same line; or put the
reference on a `- **Related ...:**` line, which is the corpus's own label for exactly that. The reason
is not optional on the inline form: an empty marker would be the gate's off switch.

SCOPE. Diff-limited like its process-artifact siblings (`_artifact_scope`): only a PRD whose directory
changed in the diff is judged, so the PRDs already in the tree do not red an unrelated change. `--all`
(no base) audits the whole corpus.

SEVERITY: BLOCKING. The signal is a number or a key next to a cue word on one line, and the remedy is a
line in the frontmatter or four words in the text. A PRD that really is independent says so once.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fleet_knowledge.config import git_context
from fleet_knowledge.corpusref import Corpora, find_refs, localize_entry, mask, parse_ref
from fleet_knowledge.prddeps import split_dependencies

from . import _artifact_scope
from ._api import ERROR, Report, finding
from ._config import PlanningConfig
from ._git import is_repository
from ._markdown import frontmatter

NAME = "prd-depends-on-prose"

__all__ = ["CHECK", "NAME", "PrdDependsOnProseCheck", "analyse", "references", "unlisted"]

#: Only before code exists can an edge still hold anything back.
CHECKED_STATUSES = frozenset({"prd-drafted", "designed", "planned"})

_PRD_NUMBER = re.compile(r"(?<![A-Za-z0-9_.])(?:(?P<tag>[A-Za-z]+)-)?(?P<n>\d{4})(?![0-9])")
#: Words that make a sentence about ANOTHER PRD a statement of dependence, not of mention.
_PRD_CUE = re.compile(
    r"\bdepend(?:s|ed|ing|ent)?\b|\bdependenc(?:y|ies)\b|\bprerequisites?\b|\bbuild(?:s|ing)?\s+on\b"
    r"|\bbuilt\s+(?:on|atop)\b|\bbranch\s+points?\b|\bassum(?:e|es|ed|ing)\b|\brel(?:y|ies)\s+on\b"
    r"|\bblocked\s+by\b|\bwaits?\s+(?:on|for)\b|\b(?:ships?|lands?|merges?)\s+first\b"
    r"|\bonce\b[^.]{0,80}\b(?:ships?|shipped|lands?|landed|merged|built)\b|\bcomposes?\s+with\b",
    re.I,
)
#: The narrower cues for a TRACKER issue: a fix that must merge before this starts.
_KEY_CUE = re.compile(
    r"\bdepend(?:s|ed|ing)?\s+on\b|\bdependenc(?:y|ies)\b|\bprerequisites?\b|\bblocked\s+by\b"
    r"|\bwaits?\s+(?:on|for)\b|\b(?:ships?|lands?|merges?)\s+first\b"
    r"|\b(?:once|until|after)\b[^.]{0,80}\b(?:merged|merges|lands|landed|ships|shipped)\b",
    re.I,
)
#: The REVERSE edge — "PRD 0825 depends on this one" says something about 0825, not about this PRD.
_REVERSE_EDGE = re.compile(
    r"(?:\bPRDs?\s*)?\d{4}(?:\s*(?:,|and|&)\s*(?:PRDs?\s*)?\d{4})*\s+(?:\w+\s+)?"
    r"(?:depends?|rel(?:y|ies)|builds?|waits?)\s+on\s+(?:this|it|that)\b",
    re.I,
)
#: How far from a cue word a tracker key still belongs to its sentence.
_KEY_REACH = 100
_NOT_A_DEPENDENCY = re.compile(r"not\s+a\s+dependency\s*:\s*\w", re.I)
_RELATED_LABEL = re.compile(r"^\s*(?:[-*>]\s*)*\**\s*related\b[^:]{0,30}:", re.I)
_FENCE = re.compile(r"^\s*(```|~~~)")


def _entries(fm: str, name: str) -> list[str]:
    """A frontmatter list, inline (`name: [a, b]`) or block (`name:` then `- a` lines)."""
    inline = re.search(rf"^{name}:[ \t]*\[(.*?)\]", fm, re.M)
    if inline:
        return [p.strip().strip("'\"") for p in inline.group(1).split(",") if p.strip()]
    block = re.search(rf"^{name}:[ \t]*\n((?:[ \t]*-[^\n]*\n?)+)", fm, re.M)
    if block:
        return [ln.strip()[1:].strip().strip("'\"") for ln in block.group(1).splitlines() if ln.strip()]
    scalar = re.search(rf"^{name}:[ \t]*([^\[\n#][^\n]*)$", fm, re.M)
    return [scalar.group(1).strip().strip("'\"")] if scalar and scalar.group(1).strip() else []


def _body_lines(text: str) -> Iterator[tuple[int, str]]:
    """`(1-based line, text)` for the lines after the frontmatter, outside fenced code."""
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                start = i + 1
                break
    fenced = False
    for i in range(start, len(lines)):
        if _FENCE.match(lines[i]):
            fenced = not fenced
            continue
        if not fenced:
            yield i + 1, lines[i]


def downstream_of(num: str, graph: dict[str, frozenset[str]]) -> frozenset[str]:
    """Every PRD that depends on `num`, directly or through others: the PRDs built ON TOP of it."""
    found: set[str] = set()
    frontier = [num]
    while frontier:
        cur = frontier.pop()
        for other, deps in graph.items():
            if cur in deps and other not in found and other != num:
                found.add(other)
                frontier.append(other)
    return frozenset(found)


def corpus_graph(root: Path, own: str = "") -> dict[str, frozenset[str]]:
    """`PRD number -> the PRD numbers its `depends_on:` lists`, for every PRD under `root`."""
    graph: dict[str, frozenset[str]] = {}
    for prd in root.iterdir():
        md = prd / "prd.md"
        if prd.is_dir() and prd.name[:4].isdigit() and md.is_file():
            fm = frontmatter(md.read_text(encoding="utf-8", errors="replace")) or ""
            graph[prd.name[:4]] = frozenset(
                p.zfill(4)
                for p in (localize_entry(e, own) for e in split_dependencies(_entries(fm, "depends_on"))[0])
                if p.isdigit()
            )
    return graph


def references(
    text: str,
    *,
    self_num: str,
    known: frozenset[str],
    tracker_prefixes: frozenset[str],
    downstream: frozenset[str] = frozenset(),
    corpora: Corpora | None = None,
    citing: Path | None = None,
) -> list[tuple[str, str, int]]:
    """`(kind, ref, line)` for every PRD (`kind == "prd"`) or tracker issue (`"issue"`) the body names as a
    dependency, first sighting per ref. Lines that declare themselves not-a-dependency are skipped, and so is a
    PRD in `downstream`: one that already depends on this PRD is built ON TOP of it, and listing it would be a cycle.

    A repo-qualified PRD (`depends on fleet:0012`) is reported as `fleet:0012` — what `depends_on:` must carry —
    and only for a corpus `corpora` knows (in prose `localhost:8000` has the same shape). Every qualified
    reference is blanked before the bare-number scan, so `fleet:0012` is never read as this corpus's 0012."""
    key_re = (
        re.compile(r"\b(" + "|".join(sorted(map(re.escape, tracker_prefixes))) + r")-(\d+)\b")
        if tracker_prefixes
        else None
    )
    seen: set[tuple[str, str]] = set()
    found: list[tuple[str, str, int]] = []
    for lineno, line in _body_lines(text):
        if _NOT_A_DEPENDENCY.search(line) or _RELATED_LABEL.match(line):
            continue
        stripped = _REVERSE_EDGE.sub(lambda m: " " * len(m.group(0)), line)
        if corpora is not None:
            stripped = corpora.mask_sibling_links(stripped, citing)
        qualified = find_refs(stripped, known=corpora.names) if corpora is not None else []
        stripped = mask(stripped)
        if _PRD_CUE.search(stripped):
            for ref, _start, _end in qualified:
                if not (ref.id.isdigit() and len(ref.id) == 4):
                    continue
                if corpora is not None and corpora.is_local(ref):
                    if (
                        ref.id != self_num
                        and ref.id in known
                        and ref.id not in downstream
                        and ("prd", ref.id) not in seen
                    ):
                        seen.add(("prd", ref.id))
                        found.append(("prd", ref.id, lineno))
                elif ("prd", str(ref)) not in seen:
                    seen.add(("prd", str(ref)))
                    found.append(("prd", str(ref), lineno))
            for m in _PRD_NUMBER.finditer(stripped):
                num = m.group("n")
                if m.group("tag") and m.group("tag").upper() != "PRD":
                    continue  # `GOV-0150`, `SL-0281`: another register's id, not a PRD number
                if num != self_num and num in known and num not in downstream and ("prd", num) not in seen:
                    seen.add(("prd", num))
                    found.append(("prd", num, lineno))
        if key_re is not None:
            cues = [c.span() for c in _KEY_CUE.finditer(stripped)]
            for m in key_re.finditer(stripped):
                key = f"{m.group(1)}-{m.group(2)}"
                near = any(m.start() >= lo - _KEY_REACH and m.end() <= hi + _KEY_REACH for lo, hi in cues)
                if near and ("issue", key) not in seen:
                    seen.add(("issue", key))
                    found.append(("issue", key, lineno))
    return found


def unlisted(
    text: str,
    *,
    self_num: str,
    known: frozenset[str],
    tracker_prefixes: frozenset[str],
    downstream: frozenset[str] = frozenset(),
    corpora: Corpora | None = None,
    citing: Path | None = None,
) -> list[tuple[str, str, int]]:
    """The `references` of `text` that neither `depends_on:` nor `related:` carries."""
    fm = frontmatter(text) or ""
    prds, keys = split_dependencies(_entries(fm, "depends_on"))
    listed = {("prd", p.zfill(4)) for p in prds if p.isdigit()} | {("issue", k) for k in keys}
    listed |= {("prd", p.zfill(4)) for p in _entries(fm, "related") if p.isdigit()}
    listed |= {("issue", p) for p in _entries(fm, "related") if not p.isdigit()}
    # A qualified entry (`fleet:0012`) is listed under its qualified spelling, and — when the
    # qualifier is this corpus's own name — under the bare number too.
    for p in (*prds, *_entries(fm, "related")):
        ref = parse_ref(p)
        if ref.qualified:
            listed.add(("prd", str(ref)))
            if corpora is not None and corpora.is_local(ref):
                listed.add(("prd", ref.id.zfill(4)))
    return [
        r
        for r in references(
            text,
            self_num=self_num,
            known=known,
            tracker_prefixes=tracker_prefixes,
            downstream=downstream,
            corpora=corpora,
            citing=citing,
        )
        if (r[0], r[1]) not in listed
    ]


def prds_root(kb: Any) -> Path:
    return Path(kb.knowledge) / PlanningConfig.of(kb).prds_dir


def analyse(kb: Any, *, base: str | None = None) -> Report:
    cfg = PlanningConfig.of(kb)
    root = prds_root(kb)
    report = Report()
    if not root.is_dir():
        return report
    known = frozenset(p.name.split("-", 1)[0] for p in root.iterdir() if p.is_dir() and p.name[:4].isdigit())
    prefixes = frozenset(cfg.reserved_requirement_prefixes)
    corpora = Corpora.of(kb)
    graph = corpus_graph(root, corpora.own)
    for prd in _artifact_scope.prds_in_scope(Path(kb.root), root, base):
        prd_md = prd / "prd.md"
        if not prd_md.is_file() or _artifact_scope.prd_status(prd) not in CHECKED_STATUSES:
            continue
        num = prd.name.split("-", 1)[0]
        for kind, ref, lineno in unlisted(
            prd_md.read_text(encoding="utf-8", errors="replace"),
            self_num=num,
            known=known,
            tracker_prefixes=prefixes,
            downstream=downstream_of(num, graph),
            corpora=corpora,
            citing=prd_md,
        ):
            if kind == "prd":
                msg = f"the text names PRD {ref} as a dependency but `depends_on:` does not list it"
                hint = (
                    f"Add `{ref}` to `depends_on:` so the driver waits for it, or mark it unrelated: "
                    f"`related: [{ref}]` in the frontmatter, or `(not a dependency: <why>)` on that line."
                )
            else:
                msg = f"the text names tracker issue {ref} as a prerequisite but `depends_on:` does not list it"
                hint = (
                    f"Add `{ref}` to `depends_on:` — the driver holds the PRD until that issue is Done or "
                    f"Cancelled — or mark it unrelated: `related: [{ref}]`, or `(not a dependency: <why>)`."
                )
            report.findings.append(finding(ERROR, f"{msg} (line {lineno})", path=prd_md, line=lineno, hint=hint))
    return report


class PrdDependsOnProseCheck:
    """A PRD still to be built lists, in `depends_on:`, every PRD and bug fix its own text waits on."""

    name = NAME
    title = "PRD depends_on matches its prose"
    description = (
        "The auto-driver waits on a PRD's frontmatter `depends_on:` and on nothing it reads in the text. A PRD "
        "whose body says it builds on, is a branch point of, assumes, or must follow another PRD, or says a "
        "tracker bug fix must merge first, while `depends_on:` omits it, is designed, planned and built "
        "without the wait the author wrote down. This check lists the omission. Bug fixes go in `depends_on:` "
        "as their tracker key (`ENG-16070`). A reference that is not a dependency is marked by the "
        "frontmatter field `related:`, an inline `(not a dependency: <reason>)`, or a `Related ...:` bullet. "
        "Judged only for a PRD at drafted, designed or planned whose directory changed in the diff."
    )

    def applies(self, kb: Any) -> bool:
        return bool(kb.has("prds_dir")) and is_repository(Path(kb.root))

    def run(self, kb: Any) -> list[Any]:
        return analyse(kb, base=git_context(kb).base or PlanningConfig.of(kb).default_diff_base).findings


CHECK = PrdDependsOnProseCheck()
