"""The shared ground the docs checks read: what a docs home is, and where its pages live.

A repository opts into the docs tooling by answering the `docs` slot — the same optional,
repo-tier question every other ground in this package answers. `fill.docs` names one or more
**docs-home documents**, each a markdown file whose frontmatter declares the audience and
visibility of a page tree, the tree's own directory, an optional coverage baseline and any
generated pages. That is the whole trigger: a repository that never answered the slot has no
homes, and nothing in this subpackage runs.

The home document carries the answer, not this package's code, because where a repository
keeps its user-facing docs and who may read them is the repository's business — the same
argument `slots.py` makes for every other repo-tier answer. What ships here is the READER.

Stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from fleet_knowledge import corpus
from fleet_knowledge import slots as slotmod
from fleet_knowledge.config import KnowledgeBase
from fleet_knowledge.markdown import cells, field, frontmatter, listfield
from fleet_knowledge.runner import Finding

#: The four doks kinds a page may be, from the shared `rubric-docs`. One page is one kind;
#: a page that is two is two pages.
PAGE_KINDS: tuple[str, ...] = ("tutorial", "how-to", "reference", "explanation")

#: What a home's frontmatter may declare for `visibility`. A `public` home is the one the
#: secret/internal-hostname rules bind; an `internal` home is not held to them.
VISIBILITIES: tuple[str, ...] = ("public", "internal")

#: The literal `kind` a docs-home document declares. A file the `docs` fill names that does
#: not say this is not a home, and saying so is better than reading its frontmatter as one.
HOME_KIND = "docs-home"

_MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)


@dataclass(frozen=True)
class Home:
    """One answered docs home, read from its home document."""

    doc: Path
    audience: str
    visibility: str
    pages_dir: Path
    baseline: Path | None
    generated: tuple[tuple[str, str], ...]

    @property
    def public(self) -> bool:
        return self.visibility == "public"


def _resolve(root: Path, pattern: str) -> list[Path]:
    """Paths in `root` matching one `fill` pattern. A literal path is checked directly."""
    if any(ch in pattern for ch in "*?["):
        return sorted(p for p in root.glob(pattern) if p.exists())
    p = root / pattern
    return [p] if p.exists() else []


def slot_fill_paths(kb: KnowledgeBase) -> list[Path]:
    """The paths the repo's `docs` slot answer resolves to. Empty when it is unfilled.

    An unfilled optional slot is dropped from the resolved registry (`slots._merge`), so a
    repository that never answered the question has no row here at all. A row whose patterns
    all match nothing is surveyed as unfilled, and this returns nothing for it too — the
    honest reading of "the home this names is not here".
    """
    registry = slotmod.read_registry(kb.root, kb.knowledge)
    slot = registry.by_id().get("docs")
    if slot is None or not slot.fill:
        return []
    return [p for pattern in slot.fill for p in _resolve(kb.root, pattern)]


def _generated(fm: str) -> tuple[tuple[str, str], ...]:
    """`generated:` entries, each authored `source -> page`.

    A line that does not carry the arrow is not a mapping and is dropped; the entries that do
    survive are then resolved by the page check, which is where a dangling end is reported.
    """
    out: list[tuple[str, str]] = []
    for entry in listfield(fm, "generated"):
        if "->" in entry:
            source, page = entry.split("->", 1)
            out.append((source.strip(), page.strip()))
    return tuple(out)


def load_homes(kb: KnowledgeBase) -> tuple[list[Home], list[Finding]]:
    """Every valid docs home the `docs` slot names, plus what was wrong with the rest.

    A home document that does not parse is reported as an error and produces no `Home`: the
    pages it would have owned are not silently skipped, they are exactly what the reader is
    told it could not reach.
    """
    homes: list[Home] = []
    findings: list[Finding] = []
    for path in slot_fill_paths(kb):
        if not path.is_file():
            findings.append(
                Finding(
                    level="error",
                    message=f"docs home `{path}` is not a file",
                    path=path,
                    hint="A `docs` slot answer names docs-home markdown files, not a directory.",
                )
            )
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        fm = frontmatter(text)
        if not fm:
            findings.append(
                Finding(
                    level="error",
                    message="docs home has no YAML frontmatter",
                    path=path,
                    hint="Declare `kind: docs-home`, `audience`, `visibility` and `pages`.",
                )
            )
            continue
        kind = field(fm, "kind")
        if kind != HOME_KIND:
            findings.append(
                Finding(
                    level="error",
                    message=f"docs home declares `kind: {kind or '(none)'}`, not `{HOME_KIND}`",
                    path=path,
                    hint="The `docs` fill names docs-home documents; mark it as one.",
                )
            )
            continue
        audience = field(fm, "audience")
        visibility = field(fm, "visibility")
        pages = field(fm, "pages")
        if not audience or visibility not in VISIBILITIES or not pages:
            findings.append(
                Finding(
                    level="error",
                    message=(
                        f"docs home is missing a valid `audience`, `visibility` ({'/'.join(VISIBILITIES)}) "
                        "or `pages` directory"
                    ),
                    path=path,
                    hint="All three are required: a home with no audience or visibility cannot be a page tree.",
                )
            )
            continue
        pages_dir = (kb.root / pages).resolve()
        if not pages_dir.is_dir():
            findings.append(
                Finding(
                    level="error",
                    message=f"docs home names `pages: {pages}`, which is not a directory",
                    path=path,
                    hint="Point `pages` at the repository directory holding this home's markdown.",
                )
            )
            continue
        baseline_rel = field(fm, "baseline")
        baseline = (kb.root / baseline_rel).resolve() if baseline_rel else None
        homes.append(
            Home(
                doc=path,
                audience=audience,
                visibility=visibility,
                pages_dir=pages_dir,
                baseline=baseline,
                generated=_generated(fm),
            )
        )
    return homes, findings


def pages(home: Home) -> list[Path]:
    """Every page in a home, sorted. `README.md` and `_`-prefixed files are not pages."""
    return sorted(p for p in home.pages_dir.rglob("*.md") if p.name != "README.md" and not p.name.startswith("_"))


def links(text: str) -> list[str]:
    """Every markdown link target in `text`, in authored order."""
    return [m.group(1) for m in _MD_LINK.finditer(text)]


def resolves_link(page: Path, target: str) -> bool:
    """Whether an internal link target resolves. External/anchored links resolve by definition."""
    if target.startswith("#") or _SCHEME.match(target):
        return True
    clean = target.split("#", 1)[0].split("?", 1)[0]
    if not clean:
        return True
    return (page.parent / clean).exists()


@dataclass(frozen=True)
class Area:
    """One feature area, and the capability rows a coverage reading needs from it."""

    name: str
    path: Path
    surfaces: tuple[str, ...]
    caps: tuple[str, ...]
    documented: dict[str, tuple[str, ...]]


def feature_areas(kb: KnowledgeBase) -> list[Area]:
    """Every feature map's capabilities, surfaces and optional `Documented in` linkage.

    `Documented in` is read BY NAME and only when the table declares it — it is an optional
    seventh-ish column, never positional — and its values are page paths. It is a LINKAGE,
    never a ship-state: nothing here reads a capability's state from it.
    """
    features_dir = kb.config.features_dir
    if not features_dir:
        return []
    cap_re = corpus.cap_id_pattern(kb.config.capability_prefix)
    out: list[Area] = []
    for f in sorted(kb.glob(f"{features_dir}/*.md")):
        if f.name == "README.md" or f.stem.startswith("_"):
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        fm = frontmatter(text)
        caps: list[str] = []
        documented: dict[str, tuple[str, ...]] = {}
        cols: dict[str, int] = {}
        for line in text.splitlines():
            if not line.lstrip().startswith("|"):
                cols = {}
                continue
            row = cells(line)
            low = [c.strip().lower() for c in row]
            if "id" in low and any("capab" in c for c in low):
                cols = {name: i for i, name in enumerate(low)}
                continue
            if not row or not cap_re.match(row[0]):
                continue
            cap = row[0]
            caps.append(cap)
            idx = cols.get("documented in")
            if idx is not None and idx < len(row):
                documented[cap] = tuple(_split_links(row[idx]))
        out.append(
            Area(
                name=field(fm, "area") or f.stem,
                path=f,
                surfaces=tuple(listfield(fm, "surfaces")),
                caps=tuple(caps),
                documented=documented,
            )
        )
    return out


def _split_links(cell: str) -> list[str]:
    """A `Documented in` cell as page paths.

    A cell may name its pages as markdown links (`[The guide](docs/guide.md)`) or as bare
    paths separated by commas; the link target wins where one is present, because the label
    is prose and the target is the path. Backticks and list markup are stripped.
    """
    target_re = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
    if target_re.search(cell):
        return [m.group(1).split("#", 1)[0] for m in target_re.finditer(cell)]
    return [x.strip().strip("`[]") for x in cell.split(",") if x.strip().strip("`[]")]


def journey_slugs(kb: KnowledgeBase) -> set[str]:
    """Every journey slug in the corpus — the ids a page's `verified_by` resolves against."""
    return {j["slug"] for j in corpus.journeys(kb.knowledge, kb.config.journeys_dir)}


def journey_documented_in(kb: KnowledgeBase) -> list[tuple[Path, str]]:
    """`(journey file, page path)` for every `documented_in:` a journey declares."""
    out: list[tuple[Path, str]] = []
    for path, _tier in corpus.journey_files(kb.knowledge, kb.config.journeys_dir):
        fm = frontmatter(path.read_text(encoding="utf-8", errors="ignore"))
        for target in listfield(fm, "documented_in"):
            out.append((path, target))
    return out


def prd_ids(kb: KnowledgeBase) -> set[str]:
    """Every PRD number, as a zero-padded string — the other id `verified_by` may name."""
    if not kb.config.prds_dir:
        return set()
    return {p.parent.name[:4] for p in kb.glob(f"{kb.config.prds_dir}/*/prd.md")}
