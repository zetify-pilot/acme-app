"""Every document under a knowledge root, typed by FILE-TYPES.md when present.

This is the index the Knowledge tab's Documents browser needs: one row per file that is not
already a richer surface (a capability map, a journey, a PRD, a slot registry, …). The type
taxonomy is the corpus's own `FILE-TYPES.md` JSON block when that file exists; when it does not,
the walker still lists what is on disk and leaves type/lifecycle empty — never an empty browser
and never a crash. The registry is a SUPERSET of what any one lane may hold, so the browser is
driven by disk, never by the type list alone.

**Store no bodies here.** A list row is a path, a title, one clipped sentence and facets. Prose
is a separate request on the served side, exactly as `knowledge.Entity` keeps statements off the
list shape.

Stdlib only.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import markdown as md

__all__ = [
    "DEFAULT_REGISTRY",
    "Document",
    "EXCLUDE_DIRS",
    "EXCLUDE_FILES",
    "SENTENCE_CHARS",
    "TypeSpec",
    "load_types",
    "read",
    "walk",
]

DEFAULT_REGISTRY = "FILE-TYPES.md"

#: How long a LIST sentence may be — same order as `knowledge.SENTENCE_CHARS`.
SENTENCE_CHARS = 300

#: Directories already reachable as richer surfaces (or tooling), relative to the knowledge root.
#: A second copy would drift; the walker skips the whole tree.
EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        "slots",
        "scripts",
        "features",
        "journeys",
        "requirements",
        "decisions",
        "programs",
        "slices",
        "prds",
    }
)

#: Single files already reachable elsewhere, knowledge-relative.
EXCLUDE_FILES: frozenset[str] = frozenset(
    {
        "specs/glossary.md",
        "specs/architecture/components.md",
        "capability-aliases.md",
        # Board registers — already the Programs board's source, not a second list.
        "programs.md",
        "slices.md",
    }
)

#: Filename stems / suffixes that are never browsable documents.
_TEMPLATE_NAME = "_TEMPLATE.md"
_MOCKUP_DIR = "mockups"

_H1_RE = re.compile(r"^#\s+(.+)$", re.M)
_JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)```", re.S)


@dataclass(frozen=True, slots=True)
class TypeSpec:
    """One entry from FILE-TYPES.md's `types` array."""

    type: str
    home: tuple[str, ...]
    exclude: tuple[str, ...]
    lifecycle: str
    required: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Document:
    """One browsable file: identity, type, and the list-row fields. Never a body."""

    path: str
    type: str
    lifecycle: str
    title: str
    home: str
    summary: str
    facets: Mapping[str, str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "type": self.type,
            "lifecycle": self.lifecycle,
            "title": self.title,
            "home": self.home,
            "summary": self.summary,
            "facets": dict(self.facets),
        }


def load_types(knowledge: Path, registry_name: str = DEFAULT_REGISTRY) -> tuple[TypeSpec, ...]:
    """The type taxonomy from FILE-TYPES.md, or () when the registry is absent or unreadable.

    Absence degrades to "no type facets", never to an empty browser — the walker still lists
    what is on disk. A malformed block is the same degradation: the structure check is the gate
    that hears about a broken registry, and a sync must not refuse a whole generation for it.
    """
    path = knowledge / registry_name
    if not path.is_file():
        return ()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ()
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        return ()
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return ()
    raw = payload.get("types") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        return ()
    out: list[TypeSpec] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        tid = str(entry.get("type") or "").strip()
        if not tid:
            continue
        homes = entry.get("home") or []
        excludes = entry.get("exclude") or []
        if not isinstance(homes, list):
            homes = []
        if not isinstance(excludes, list):
            excludes = []
        required = entry.get("required") or []
        if not isinstance(required, list):
            required = []
        out.append(
            TypeSpec(
                type=tid,
                home=tuple(str(p) for p in homes if str(p).strip()),
                exclude=tuple(str(p) for p in excludes if str(p).strip()),
                lifecycle=str(entry.get("lifecycle") or "").strip(),
                required=tuple(str(r) for r in required if str(r).strip()),
            )
        )
    return tuple(out)


def _glob_files(knowledge: Path, pattern: str) -> set[Path]:
    """Glob under the knowledge root; trailing `**` means recursive files (3.12-safe)."""
    if pattern == "**" or pattern.endswith("/**"):
        pattern = pattern + "/*"
    return {p for p in knowledge.glob(pattern) if p.is_file()}


def _type_index(knowledge: Path, types: Sequence[TypeSpec]) -> dict[Path, list[TypeSpec]]:
    """Path → matching TypeSpecs, computed ONCE for the whole walk.

    `_classify` used to re-glob every type's home/exclude for every file. A live knowledge tree
    with ~70 types of multi-pattern `**` homes and ~3k listed files made that tens of minutes
    of pure filesystem work per advanced corpus sync (ENG-12253: ~15 s → ~46 min after
    ENG-10916 landed the walker). Membership does not depend on which file is being labeled, so
    the globs run once and the walk is a dict lookup.
    """
    index: dict[Path, list[TypeSpec]] = {}
    for spec in types:
        matched: set[Path] = set()
        for pat in spec.home:
            matched |= _glob_files(knowledge, pat)
        for pat in spec.exclude:
            matched -= _glob_files(knowledge, pat)
        for path in matched:
            index.setdefault(path, []).append(spec)
    return index


def _classify(path: Path, index: Mapping[Path, Sequence[TypeSpec]]) -> tuple[str, str]:
    """`(type_id, lifecycle)` for one file, or `("", "")` when nothing matches / ambiguous."""
    hits = index.get(path) or ()
    if len(hits) != 1:
        # Zero or ambiguous: still list the file; leave type empty rather than guess.
        return "", ""
    return hits[0].type, hits[0].lifecycle


def _rel(path: Path, knowledge: Path) -> str:
    return path.relative_to(knowledge).as_posix()


def _excluded(rel: str) -> bool:
    """Whether this knowledge-relative path is already a richer surface or tooling."""
    if rel in EXCLUDE_FILES:
        return True
    name = Path(rel).name
    if name == _TEMPLATE_NAME or name.startswith("_TEMPLATE"):
        return True
    parts = rel.split("/")
    if _MOCKUP_DIR in parts:
        return True
    return bool(parts and parts[0] in EXCLUDE_DIRS)


def _home_of(rel: str) -> str:
    """The directory bucket a facet menu groups by — first path segment, or '' at the root."""
    if "/" not in rel:
        return ""
    return rel.split("/", 1)[0]


def _title_of(text: str, rel: str, fields: Mapping[str, str]) -> str:
    titled = (fields.get("title") or "").strip()
    if titled:
        return titled
    match = _H1_RE.search(md.strip_frontmatter(text))
    if match:
        return match.group(1).strip()
    stem = Path(rel).stem
    return stem.replace("-", " ").replace("_", " ") or rel


def _summary_of(text: str) -> str:
    body = md.strip_frontmatter(text)
    # Drop a leading H1 so the summary is the first prose, not the title again.
    body = re.sub(r"^#\s+.+\n+", "", body.lstrip(), count=1)
    return md.first_paragraph(body, SENTENCE_CHARS)


def _facets_of(fields: Mapping[str, str], *, doc_type: str, lifecycle: str, home: str) -> dict[str, str]:
    """Frontmatter scalars worth filtering on, plus the three structural facets.

    `type` / `lifecycle` / `home` are always present when known so a menu derived over the whole
    set never has to re-read columns. Other frontmatter keys (status, owner, …) ride through as
    written, excluding the title (already a column) and empty values.
    """
    out: dict[str, str] = {}
    if doc_type:
        out["type"] = doc_type
    if lifecycle:
        out["lifecycle"] = lifecycle
    if home:
        out["home"] = home
    skip = {"type", "title", "lifecycle", "home"}
    for key, value in fields.items():
        if key in skip or not value:
            continue
        out[key] = value
    return out


def _frontmatter_fields(text: str) -> dict[str, str]:
    """Top-level scalar frontmatter fields — same shape the type check already uses."""
    block = md.frontmatter(text)
    if not block:
        return {}
    out: dict[str, str] = {}
    for line in block.splitlines():
        match = re.match(r"([A-Za-z_][\w-]*):\s*(.*)$", line)
        if match:
            out[match.group(1)] = md.unquote(match.group(2))
    return out


def _is_text_document(path: Path) -> bool:
    """Markdown and plain text only — assets type by folder but are not a list the browser opens."""
    return path.suffix.lower() in {".md", ".markdown", ".txt", ".rst"}


def walk(
    knowledge: Path,
    *,
    registry_name: str = DEFAULT_REGISTRY,
    types: Sequence[TypeSpec] | None = None,
) -> list[Document]:
    """Every browsable document under `knowledge`, sorted by path.

    Driven by what is on disk. The registry only labels; an empty or absent registry still
    yields every non-excluded text file.
    """
    if not knowledge.is_dir():
        return []
    specs = tuple(types) if types is not None else load_types(knowledge, registry_name)
    # ONE pass of globs for the whole tree — never per file (ENG-12253).
    index = _type_index(knowledge, specs) if specs else {}
    lifecycle_by_type = {spec.type: spec.lifecycle for spec in specs}
    out: list[Document] = []
    for path in sorted(p for p in knowledge.rglob("*") if p.is_file()):
        if not _is_text_document(path):
            continue
        try:
            rel = _rel(path, knowledge)
        except ValueError:
            continue
        if _excluded(rel):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fields = _frontmatter_fields(text)
        doc_type, lifecycle = _classify(path, index)
        # Prefer the file's own `type:` when the registry agreed or when there is no registry hit.
        declared = (fields.get("type") or "").strip()
        if declared and (not doc_type or declared == doc_type):
            doc_type = declared
        if declared and not lifecycle:
            lifecycle = lifecycle_by_type.get(declared, "")
        home = _home_of(rel)
        title = _title_of(text, rel, fields)
        summary = _summary_of(text)
        out.append(
            Document(
                path=rel,
                type=doc_type,
                lifecycle=lifecycle,
                title=title,
                home=home,
                summary=summary,
                facets=_facets_of(fields, doc_type=doc_type, lifecycle=lifecycle, home=home),
            )
        )
    return out


def read(root: Path, *, registry_name: str = DEFAULT_REGISTRY) -> list[dict[str, Any]]:
    """`walk` as plain dicts — the shape `sync` stamps into `registers.documents`."""
    return [doc.as_dict() for doc in walk(root, registry_name=registry_name)]
