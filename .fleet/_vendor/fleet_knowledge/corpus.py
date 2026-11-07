"""The document readers: PRDs, feature maps, journeys, components, the glossary.

Everything here is DERIVED from files a human authored for another reason. Nothing in this
package has a hand-maintained input, and nothing writes back — statuses come from PRD
frontmatter, the ship/test edges from a feature map's own table, a feature area's one-line
description from its own `> **Intent.**`, and a component's architecture layer from the
component registry. Re-reading restates the corpus instead of leaving a stale claim behind.

Every function takes the corpus root. The caps below bound how much prose a *viewer* inlines
— a browser is an index, not a reader: it shows enough of a field to recognise the thing and
links to the file for the rest. Without ceilings the payload is the whole corpus for no
navigational gain.

Stdlib only.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import date as date_type
from datetime import datetime as datetime_type
from datetime import time as time_type
from pathlib import Path
from typing import Any

from . import featurebrief
from .corpusref import localize_entry, localize_text, resolve_own
from .corpusref import mask as mask_qualified
from .featureshell import area_stem, map_files
from .markdown import (
    bullets,
    cells,
    clip,
    field,
    first_paragraph,
    frontmatter,
    listcell,
    listfield,
    md_rows,
    one_line,
    plain,
    section,
    strip_frontmatter,
    unquote_block,
)
from .registers import (
    PROGRAM_DETAIL_SUBDIR,
    PROGRAM_FILE,
    PROGRAM_PREFIX,
    SLICE_DETAIL_SUBDIR,
    SLICE_FILE,
    SLICE_PREFIX,
    program_detail,
    programs,
    slice_detail,
    slices,
)

# ─────────────────────────── the conventional names ───────────────────────────
#
# Every reader below takes the path it reads as a PARAMETER, defaulted to the conventional
# name — the shape `requirements.register_dir` and `todos.register` already use, and for the
# same reason: a project reshapes its corpus by naming files in its `fleet.toml`, and a reader
# that opens one by hardcoded name makes that configuration a lie. It was one here, and the
# failure was silent: a corpus whose registers are called something else derived a whole,
# well-formed, entirely empty board.
#
# `Config` is deliberately NOT imported. These are readers over paths; which paths a project
# uses is resolved one tier up, by whoever built the `KnowledgeBase`, and threaded down.

PRDS_DIR = "prds"
FEATURES_DIR = "features"
#: Per-row capability fragments: `<root>/features/rows/<CAP-NNNN>.json` (ENG-12660). The
#: filename IS the id; JSON carries `table` (`<!-- rows: <area>#<section> -->`), `order`, and
#: `cells` (everything after the id). When present for an area, `features()` reads them and
#: ignores that area's committed table body (ENG-12980 / FLT-045) — the programs/slices
#: precedent (ENG-12661).
FEATURE_ROWS_SUBDIR = "rows"
FEATURE_ROWS_MARKER_RE = re.compile(r"^<!-- rows: (\S+) -->$")

# Same probe as requirements.FRAGMENT_BACKED_TABLES — feature maps are the other half.
FRAGMENT_BACKED_TABLES = True
JOURNEYS_DIR = "journeys"
COMPONENTS_REGISTRY = "specs/architecture/components.md"
GLOSSARY_FILE = "specs/glossary.md"
CAPABILITY_ALIASES = "capability-aliases.md"
COVERAGE_LEDGER = "audits/feature-coverage-ledger.md"
DECISIONS_DIR = "decisions"

# ─────────────────────────── prose ceilings ───────────────────────────

SUMMARY_CHARS = 430  # a PRD's "what this is for" paragraph
TITLE_CHARS = 120
INTENT_CHARS = 600  # a feature area's Intent
STEP_CHARS = 260
JOB_CHARS = 400
PRECONDITION_CHARS = 300
#: A slice's "Done when" is the promise it makes, and a promise cut mid-sentence is not the promise. The longest one
#: authored is under a thousand characters; the cap only stops a pasted essay.
DONE_WHEN_CHARS = 1200
MAX_ACS = 18
MAX_REQUIREMENTS = 14
MAX_NON_GOALS = 10
MAX_OPEN_DECISIONS = 8
MAX_STEPS = 14
COMPONENT_DESC_CHARS = 300  # a component registry row's one-sentence description
# The long-form prose a component's modal resolves to, whichever of the three tiers supplied
# it. Unlike every cap above this one bounds a READING rather than a page: prose is stored per
# component row so the served path never needs a checkout, which puts every component's full
# text into the sync payload at once — 84 components × unbounded detail docs is the payload
# growing for no navigational gain. The modal itself serves ONE component per request, so the
# click path never notices the ceiling; the reading it rides in does.
COMPONENT_PROSE_CHARS = 4000
DECISION_TITLE_CHARS = 200
DECISION_SUMMARY_CHARS = 400  # a decision record's lead paragraph

# Sections of a program/slice detail file a viewer does NOT carry, lowercased. Both are
# member lists, and the register already holds those members — with each PRD's live status.
# The prose copy is a snapshot that was true when somebody typed it; two lists of the same
# members, one of them stale, is worse than one.
DETAIL_SKIP = frozenset({"prds (issues)", "tasks (no prd)"})

# ─────────────────────────── patterns ───────────────────────────

# A capability id — the first column of a feature map's capability table. Deliberately
# OPAQUE: it encodes nothing, and which area a capability belongs to is which file its row
# is in, so a capability moves between areas by moving its row.
CAP_ID_RE = re.compile(r"^CAP-\d{4}$")
CAPABILITY_PREFIX = "CAP"


def cap_id_pattern(prefix: str) -> re.Pattern[str]:
    r"""`^FEAT-\d+$` for `FEAT`. `Config.capability_prefix` names the namespace."""
    return re.compile(rf"^{re.escape(prefix)}-\d+$")


def cap_ref_pattern(prefix: str) -> re.Pattern[str]:
    r"""The same id UNANCHORED — `\bFEAT-\d+\b` — for finding citations inside a cell.

    A separate pattern rather than a flag on the one above, because the two answer opposite
    questions: `cap_id_pattern` asks *is this cell an id* (and a cell that is an id and a
    sentence is not one), and this asks *which ids does this sentence name*.
    """
    return re.compile(rf"\b{re.escape(prefix)}-\d+\b")


PRD_NUM_RE = re.compile(r"\b(\d{4})\b")
# The `Ships in` marker vocabulary: a cell is a PRD number, `(core)`, `(shipped)`,
# `(retired)`, or `—`. The first three are EVIDENCE THE CAPABILITY IS BUILT — not an absent
# PRD — and reading them as absence is a measured 75%-false gap signal.
SHIPS_MARK_RE = re.compile(r"^\((core|shipped|retired)\)", re.I)
# A `Tested by` cell is prose-or-slugs, and the authored slug form is BACKTICKED —
# `` `run-agent` · `agent-setup` `` names two journeys. A raw comma split resolves neither.
BACKTICK_RE = re.compile(r"`([^`]+)`")
H1_RE = re.compile(r"^#\s+(?:PRD\s*\d+[:\s-]*)?(.+)$", re.M)
INTENT_RE = re.compile(r"\*\*Intent\.\*\*\s*(.+?)(?:\n\n|\Z)", re.S)
# A component/layer id in the registry's tables. Anchored on a letter so the `|---|---|`
# rule under a header — which is also all "id characters" — can never read as a row.
LAYER_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")
JOB_RE = re.compile(r"\*\*Job statement:\*\*\s*\*?(.+?)\*?\s*(?:\n\n|$)", re.S)
PRE_RE = re.compile(r"\*\*Preconditions:\*\*\s*(.+?)(?:\n\n|$)", re.S)
STEP_RE = re.compile(r"^\s*(\d+)\.\s+(.*)$")

# ─────────────────────────── a feature area's one-line description ───────────────────────

# The one sentence that stands for a feature area. Read from the map's own `> **Intent.**`
# blockquote — nothing new is authored for it, which is what keeps it from becoming a second
# thing to maintain.
AREA_DESC_CHARS = 250
AREA_INTENT_RE = re.compile(r"^>\s*\*\*Intent\.\*\*\s*(.*?)(?=\n(?!\s*>)|\Z)", re.M | re.S)


def lead_paragraph(body: str, fallback: str, limit: int = AREA_DESC_CHARS) -> str:
    """The first real paragraph, cut on a word boundary."""
    for para in body.split("\n\n"):
        p = " ".join(ln.strip() for ln in para.strip().splitlines() if ln.strip())
        if not p or p.startswith("#"):
            continue
        return p if len(p) <= limit else p[:limit].rsplit(" ", 1)[0]
    return fallback[:limit]


def _drop_fm(text: str) -> str:
    """Frontmatter removed by SPLITTING on the fence, not by matching a line-anchored one.

    Deliberately not `markdown.strip_frontmatter`: the same sentence has to come out of this
    function and out of whatever writes a feature area's description on the project board, or
    an area reads one way there and another way here — exactly the drift both readers exist
    to prevent. Split semantics are what the other reader uses, so they are what is used
    here.
    """
    if text.startswith("---"):
        p = text.split("---", 2)
        if len(p) >= 3:
            return p[2].lstrip("\n")
    return text


def area_description(text: str, fallback: str) -> str:
    """The first sentence of the `> **Intent.**` blockquote, or the lead paragraph."""
    m = AREA_INTENT_RE.search(text)
    if not m:
        return lead_paragraph(_drop_fm(text), fallback)
    intent = unquote_block(m.group(1))
    if (dot := intent.find(". ")) != -1 and dot + 1 <= AREA_DESC_CHARS:
        return intent[: dot + 1]
    if len(intent) <= AREA_DESC_CHARS:
        return intent
    return intent[:AREA_DESC_CHARS].rsplit(" ", 1)[0]


# ─────────────────────────── components ───────────────────────────


def component_layers(root: Path, registry: str = COMPONENTS_REGISTRY) -> tuple[list[dict[str, str]], dict[str, str]]:
    """The architecture layers in DRAWING order, and `component id -> layer`.

    Read out of the component registry (`specs/architecture/components.md`): its `## Layers`
    table is a closed set in drawing order, and every component row names one. `## Proposed
    components` is read too — a feature area may cite a component whose row has not been
    promoted yet, and dropping those would silently move the area to a different group than
    its code sits in.

    Each layer carries its own `description` — the third column, what the layer is *for*.
    Read positionally like `id` and `name` before it, because the three columns are the table's
    whole contract: a registry that renames the column has not changed what a layer is.

    A missing or unparseable registry yields `([], {})`. A viewer degrades; a validator owns
    failing the build.
    """
    path = root / registry
    if not path.is_file():
        return [], {}
    text = path.read_text(encoding="utf-8")
    layers: list[dict[str, str]] = []
    seen: set[str] = set()
    for c in md_rows(section(text, "Layers")):
        if len(c) >= 3 and c[0] not in ("layer", "id") and LAYER_ID_RE.match(c[0]) and c[0] not in seen:
            seen.add(c[0])
            layers.append({"id": c[0], "name": c[1] or c[0], "description": plain(c[2] if len(c) > 2 else "")})
    layer_of: dict[str, str] = {}
    for heading in ("Components", "Proposed components"):
        for c in md_rows(section(text, heading)):
            if len(c) >= 3 and LAYER_ID_RE.match(c[0]) and c[2] in seen:
                layer_of.setdefault(c[0], c[2])
    return layers, layer_of


#: How a component's detail document is found, given the registry's own path. DERIVED rather
#: than configured: the registry names the directory it sits in, and the convention every
#: corpus with one follows is a sibling directory of the same name as the registry's stem.
#: A second `fleet.toml` option would be a second place for the same fact to be wrong.
COMPONENT_DETAIL_SUBDIR = "components"

#: Where the diagram's topology is authored, given the registry's own path. Same derivation as
#: `COMPONENT_DETAIL_SUBDIR`: the registry names the directory it sits in, and the layout file
#: sits beside it — one directory, one architecture, nothing to configure twice.
DIAGRAM_LAYOUT_FILE = "diagram-layout.toml"

#: The component-registry columns this reader takes, by NAME. Read from the header rather
#: than by position, for the reason the requirement register's parser gives: a registry that
#: gains a column anywhere must not shift every reader one cell to the left. `id`, `name` and
#: `layer` are load-bearing; the rest are read when declared and absent when not.
COMPONENT_COLUMNS = ("id", "name", "layer", "owns", "depends_on", "description", "detail")


def _header(cells_: list[str], first: str, also: str) -> bool:
    """Whether this row is the header of the table we are looking for.

    Identified by its COLUMNS rather than by its position under a heading, so a prose table
    that happens to sit in the same section is passed over instead of parsed as data.
    """
    return bool(cells_) and cells_[0].strip().lower() == first and any(c.strip().lower() == also for c in cells_)


def _cell(row: list[str], header: Mapping[str, int], column: str) -> str:
    """One cell of `row` by COLUMN NAME. "" when the table never declared that column.

    The other half of `_header`: a table identified by its columns is read by them too, so an
    optional column that is simply absent reads as absent rather than as whatever sits at that
    index in a table with one fewer column.
    """
    i = header.get(column, -1)
    return row[i] if 0 <= i < len(row) else ""


def _feature_intents(root: Path, features_dir: str) -> dict[str, tuple[str, str]]:
    """`component id -> (the area's Intent prose, the map's corpus-relative path)`, for every
    feature map that names the component under `components:`.

    The SECOND tier of a component's prose — the reasoning behind this helper, and the reason
    it reads only frontmatter and the `> **Intent.**` blockquote: feature areas and components
    are two decompositions of the product and deliberately not 1:1, so an area's Intent is the
    customer-facing story of the subsystem underneath it, usually the same story and never
    guaranteed to be. The regexes are the area parser's OWN — `INTENT_RE` and the same
    `listfield` call `features` makes — applied without the capability-table walk, because a
    second spelling of either would one day disagree with the first about what an Intent is.

    `setdefault`: the first map in filename order wins, which is the stable choice — sorted
    iteration is the one order that does not change when a map is renamed.
    """
    found: dict[str, tuple[str, str]] = {}
    if not features_dir:
        return found
    for f in map_files(root / features_dir):
        if f.name == "README.md" or area_stem(f).startswith("_"):
            continue
        text = f.read_text(encoding="utf-8")
        named = listfield(frontmatter(text), "components")
        if not named:
            continue
        m = INTENT_RE.search(text)
        if not m:
            continue
        prose = " ".join(unquote_block(m.group(1)).split())
        for cid in named:
            found.setdefault(cid, (prose, f"{features_dir}/{f.name}"))
    return found


def components(
    root: Path,
    registry: str = COMPONENTS_REGISTRY,
    detail_subdir: str = COMPONENT_DETAIL_SUBDIR,
    features_dir: str = FEATURES_DIR,
    repo: Path | None = None,
) -> list[dict[str, Any]]:
    """Every registered component: what it is, which layer it is drawn in, whether prose
    describes it, and how much of it exists.

    `## Components` and `## Proposed components` both, for the reason `component_layers`
    reads both: a component whose row has not been promoted yet is still a component a
    feature area may name, and dropping it makes the area's `builtBy` edge point at nothing.
    `proposed` says which side of that line a row fell, because the two are genuinely
    different claims — "we build this" and "we intend to".

    **`documented` is a fact about the FILESYSTEM, not about the `detail` cell.** The cell is
    the registry's claim that prose exists and is validated to match; this reader answers the
    question a finding is raised on — *is there a document to read* — and a claim is not a
    document. The cell rides along under `detail` so a reader can see the two disagree.

    **`present` is the same kind of fact about the tree: which `owns:` paths exist.** The
    registry's own rule is that coverage is derived, never stored, so the reader derives it
    while it holds the tree — never asserting it in prose. `owns:` paths are REPO-relative
    (the validator's rule E), so the derivation needs the REPOSITORY root, which is not the
    corpus root this reader is handed: pass it as `repo` when it is known, and without one the
    field degrades to `[]` — a viewer degrades; the sync is the caller that can answer for a
    commit.

    **`prose` is the long-form text a modal renders, resolved through three tiers**, and
    `prose_kind` names which tier won — the provenance is labelled rather than merged silently,
    because the tiers are three different kinds of writing about the same subsystem:

      1. `component` — the detail document `<registry_dir>/components/<id>.md`, frontmatter
         stripped and its H1 dropped (the modal has its own);
      2. `feature` — the Intent of the first feature map that names the component under
         `components:`;
      3. `registry` — the one-liner, which the row already carries: `prose` stays empty and
         the reader falls back to it.

    `prose_source` is the corpus-relative path of whichever document won, so a reader can
    always name where the words came from — the same relative spelling every other source hint
    in this model uses.

    A missing or unparseable registry yields `[]`. A viewer degrades; a validator owns
    failing the build.
    """
    path = root / registry
    if not registry or not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    detail_dir = path.parent / detail_subdir
    intents = _feature_intents(root, features_dir)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for heading in ("Components", "Proposed components"):
        cols: dict[str, int] = dict.fromkeys(COMPONENT_COLUMNS, -1)
        for c in md_rows(section(text, heading)):
            if _header(c, "id", "name"):
                # The header row is also all id characters, so it matches the row pattern
                # below and would otherwise be stored as a component called `name` in a layer
                # called `layer`. It was, on the first run against the real registry.
                cols = {name.strip().lower(): i for i, name in enumerate(c)}
                continue
            if len(c) < 3 or not LAYER_ID_RE.match(c[0]) or c[0] in seen:
                continue
            seen.add(c[0])
            owns = listcell(_cell(c, cols, "owns"))
            desc = one_line(plain(_cell(c, cols, "description")), COMPONENT_DESC_CHARS)
            prose, prose_kind, prose_source = _component_prose(c[0], intents, detail_dir, root)
            out.append(
                {
                    "id": c[0],
                    "name": _cell(c, cols, "name") or c[0],
                    "layer": _cell(c, cols, "layer"),
                    "owns": owns,
                    "dep": listcell(_cell(c, cols, "depends_on")),
                    "desc": desc,
                    "detail": _cell(c, cols, "detail").strip(),
                    "documented": (detail_dir / f"{c[0]}.md").is_file(),
                    "proposed": heading != "Components",
                    "present": [p for p in owns if (repo / p).exists()] if repo is not None else [],
                    "prose": prose,
                    "prose_kind": prose_kind,
                    "prose_source": prose_source,
                }
            )
    return out


def _component_prose(
    cid: str, intents: Mapping[str, tuple[str, str]], detail_dir: Path, root: Path
) -> tuple[str, str, str]:
    """The three-tier resolution, as `(prose, prose_kind, prose_source)`.

    One function rather than inline branches so the ORDER of the tiers is stated once: the
    detail document beats the feature area's Intent, and the Intent beats the registry's
    one-liner. Longer prose is not better prose — a component with a detail doc is described
    by the document that exists for exactly that purpose.

    The cap is `clip` and not `one_line` on purpose: a detail document is paragraphs, and the
    viewer renders the blank lines it was given — flattening it here would store prose whose
    shape no reader could recover.
    """
    doc = detail_dir / f"{cid}.md"
    if doc.is_file():
        body = strip_frontmatter(doc.read_text(encoding="utf-8")).strip()
        body = re.sub(r"^#\s+.*\n+", "", body).strip()  # the H1 is the modal's own
        source = doc.relative_to(root).as_posix() if doc.is_relative_to(root) else doc.name
        return clip(body, COMPONENT_PROSE_CHARS), "component", source
    if cid in intents:
        prose, source = intents[cid]
        return clip(prose, COMPONENT_PROSE_CHARS), "feature", source
    return "", "registry", ""


# ─────────────────────────── the registry's two narrative tables ───────────────────────────


def _section_under(text: str, prefix: str) -> str:
    """The body under the first `## <prefix…>` heading, up to the next `## `.

    NOT `markdown.section`, and the difference is the registry's own voice: it decorates these
    two headings — `## External — the customer's side of the boundary`,
    `## Outcomes (the narrative axis — NOT components)` — and a heading matched as LITERAL text
    ending the line reads neither. The validator matches the same way, by prefix, so one file
    shape is read one way in this package and in the check beside it.
    """
    pattern = re.compile(rf"^##\s+{re.escape(prefix)}[^\n]*$([\s\S]*?)(?=^##\s|\Z)", re.M)
    if m := pattern.search(text):
        return m.group(1).strip()
    return ""


def externals(root: Path, registry: str = COMPONENTS_REGISTRY) -> list[dict[str, str]]:
    """The registry's `## External` table — the customer's side of the boundary.

    Not components, and deliberately in their own reading: an external system is drawn on the
    architecture's edge and owns nothing in this repository, so folding it into `components()`
    would give every component-derived reading a phantom row with no layer and no code.

    Read by COLUMN NAME through `_table_by_name`, like `components()` reads its own table — an
    optional column that is simply absent reads as absent rather than as whatever sits at that
    index. A missing or unparseable registry yields `[]`. A viewer degrades; a validator owns
    failing the build.
    """
    path = root / registry
    if not registry or not path.is_file():
        return []
    out: list[dict[str, str]] = []
    for row in _table_by_name(_section_under(path.read_text(encoding="utf-8"), "External")):
        out.append(
            {
                "id": row.get("id", ""),
                "name": row.get("name") or row.get("id", ""),
                "description": plain(row.get("description", "")),
            }
        )
    return out


def outcomes(root: Path, registry: str = COMPONENTS_REGISTRY) -> list[dict[str, Any]]:
    """The registry's `## Outcomes` table — the business-value axis.

    Cross-cutting properties that emerge from SEVERAL components working together: an outcome
    owns no code and is never a box in the stack, which is exactly why it is not a component
    row. `realized_by` is the one edge from this narrative axis back into the things that
    exist, and it is the validator's business that it resolves — this reader carries it as
    written, first-seen order preserved.

    Read by COLUMN NAME, like `externals()`. A missing or unparseable registry yields `[]`.
    """
    path = root / registry
    if not registry or not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for row in _table_by_name(_section_under(path.read_text(encoding="utf-8"), "Outcomes")):
        out.append(
            {
                "id": row.get("id", ""),
                "name": row.get("name") or row.get("id", ""),
                "description": plain(row.get("description", "")),
                "realized_by": listcell(row.get("realized_by", "")),
            }
        )
    return out


def _table_by_name(body: str) -> list[dict[str, str]]:
    """Every data row of the pipe table under `body`, keyed by its own header's column names.

    The other half of the same bargain `components()` strikes with its registry: a table
    identified by its columns is read by them, so a column added or reordered shifts nothing.
    Rows before a header are skipped — a table that never declares one has nothing to read BY.
    """
    out: list[dict[str, str]] = []
    cols: dict[str, int] = {}
    for c in md_rows(body):
        if _header(c, "id", "name"):
            cols = {name.strip().lower(): i for i, name in enumerate(c)}
            continue
        if not cols:
            continue
        if all(set(cell) <= set("-: ") for cell in c):
            continue  # the `|---|---|` rule, which is not a row of data
        out.append({name: c[i] for name, i in cols.items() if 0 <= i < len(c)})
    return out


def diagram_layout(root: Path, registry: str = COMPONENTS_REGISTRY) -> dict[str, Any] | None:
    """The parsed `diagram-layout.toml` beside the registry, or `None` when there is none.

    The authored topology: which layers draw as full-width bands, which as the two build-and-run
    columns, which in the rail. Read WHOLE and passed through — the shape is the file's own
    contract (a `[diagram]` table and one ordered `[[placement]]` sequence, whose document
    order is the draw order), and this reader adds no vocabulary of its own to a file the
    validator already judges.

    `None` is the ordinary case for a corpus that has not authored one, and the viewer's
    generic fallback (bands in Layers-table order) is what it means. A MALFORMED file is also
    `None` rather than a raise — a viewer degrades; the validator is where a broken layout
    fails the build, and it parses the file a second time to be the one that says so. Dates,
    TOML's one type JSON has no room for, become their ISO text: a layout that carried one
    would otherwise fail the whole sync on a value nobody can draw.
    """
    path = root / registry
    if not registry or not path.is_file():
        return None
    layout = path.parent / DIAGRAM_LAYOUT_FILE
    if not layout.is_file():
        return None
    try:
        parsed: dict[str, Any] = tomllib.loads(layout.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return None

    def plain_values(node: Any) -> Any:
        if isinstance(node, dict):
            return {k: plain_values(v) for k, v in node.items()}
        if isinstance(node, list):
            return [plain_values(v) for v in node]
        if isinstance(node, (date_type, datetime_type, time_type)):
            return node.isoformat()
        return node

    safe: dict[str, Any] = plain_values(parsed)
    return safe


# ─────────────────────────── decision records ───────────────────────────

#: The line a decision record names the register rows it moves on. AUTHORED, and the only
#: machine-readable edge a record carries — everything else in the file is argument.
COMMITMENTS_RE = re.compile(r"^\*\*Commitments\.\*\*\s*(.+?)(?:\n\n|\Z)", re.M | re.S)
#: A decision record's filename leads with the day it was taken. The id is the whole stem —
#: the date alone is not unique and never was.
DECISION_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
#: A requirement id cited anywhere in the commitments line. Deliberately the same shape the
#: register reader accepts, so "adds **[RUN-1133]**" and "RUN-725, RUN-726" read alike.
DECISION_ID_RE = re.compile(r"\b[A-Z]{2,5}-\d{3,}\b")
#: A decision record's body is a run of LABELLED paragraphs — `**Context.**`, `**Decision.**`,
#: `**Rationale.**` — and the label is markup rather than prose. Matched in the template's own
#: order so the sentence that stands for a record is the decision when it has one.
DECISION_LEAD_LABELS = ("Decision", "Context", "Rationale")
DECISION_LABEL_RE = re.compile(r"^\*\*([A-Za-z ]+)\.\*\*\s*(.+?)(?=\n\n|\Z)", re.M | re.S)


def decision_lead(body: str) -> str:
    """The one sentence that stands for a decision record.

    NOT `first_paragraph`, and the difference is the whole of this function: that reader skips
    a paragraph opening with `*` because in every other document such a line is a bullet or a
    table. In a decision record it is every paragraph there is, so `first_paragraph` returned
    "" for all 161 records on the product corpus — a kind whose every summary was empty.

    The `**Decision.**` paragraph wins over `**Context.**` because a reader scanning a list
    wants what was decided, not what prompted it; the label itself is dropped, since a page
    that printed "Decision. Decision." would be quoting the template rather than the record.
    """
    found = {m.group(1).strip(): " ".join(m.group(2).split()) for m in DECISION_LABEL_RE.finditer(body)}
    for label in DECISION_LEAD_LABELS:
        if found.get(label):
            return clip(found[label], DECISION_SUMMARY_CHARS)
    return first_paragraph(body, DECISION_SUMMARY_CHARS)


def decisions(root: Path, decisions_dir: str = DECISIONS_DIR) -> list[dict[str, Any]]:
    """Every decision record, with the register rows it says it moved.

    **`type: decision` in the frontmatter is the admission test**, not the filename: the
    directory also holds a `_TEMPLATE.md` (`type: template`) and a README, and a reader that
    took every `*.md` would index the template's placeholder prose as a decision the project
    made. Measured on the product corpus: 163 files, 1 template, 1 README, 161 records.

    **Most records carry no such line, and that is the corpus rather than a parse failure.**
    Measured on the product corpus: 17 of 161 records author a `**Commitments.**` line, and 8
    of those name a register id on it. The convention postdates most of the file, so an empty
    `moves` means "this record never said", never "this record moved nothing".

    `moves` is every requirement id the `**Commitments.**` line names — *adds* and
    *supersedes* alike, undifferentiated, because the line is prose and the distinction is
    argued in words rather than marked. The honest reading is "this record is where these
    rows were last argued", which is what the inverse edge (`settledBy`) says.
    """
    out: list[dict[str, Any]] = []
    if not decisions_dir:
        return out
    for f in sorted((root / decisions_dir).glob("*.md")) if (root / decisions_dir).is_dir() else []:
        if f.name == "README.md" or f.stem.startswith("_"):
            continue
        text = f.read_text(encoding="utf-8")
        fm = frontmatter(text)
        if field(fm, "type") != "decision":
            continue
        body = strip_frontmatter(text)
        h1 = re.search(r"^#\s+(.+)$", body, re.M)
        m = COMMITMENTS_RE.search(body)
        date = DECISION_DATE_RE.match(f.stem)
        out.append(
            {
                "id": f.stem,
                "title": (field(fm, "title") or (h1.group(1).strip() if h1 else f.stem))[:DECISION_TITLE_CHARS],
                # `accepted` unless the record says otherwise. Free text on purpose: a corpus
                # writes `superseded-in-part` and `reverted`, and a closed set here would
                # either refuse them or flatten three readings into one.
                "status": field(fm, "status") or "accepted",
                "date": date.group(1) if date else "",
                "moves": list(dict.fromkeys(DECISION_ID_RE.findall(m.group(1)))) if m else [],
                "lead": decision_lead(body[h1.end() :] if h1 else body),
                "supersedes": field(fm, "supersedes"),
            }
        )
    return out


# A ledger data row: `| `area` | family, family | tier | date | depth | notes |`. Six cells,
# and the cell class excludes newlines so the match cannot run past a line into the next. The
# third cell is the AUTHORED `Tier` (`core` / `rotation` / `parked`, or blank): `feature_families`
# and `feature_tiers` project from this one parse (PRD 0776, design D2).
LEDGER_ROW_RE = re.compile(r"^\|\s*`([a-z0-9-]+)`\s*\|([^|\n]*)\|([^|\n]*)\|[^|\n]*\|[^|\n]*\|", re.M)


def feature_families(root: Path, ledger: str = COVERAGE_LEDGER) -> dict[str, list[str]]:
    """`area slug -> [family]`, from the `Family` column of the feature-coverage ledger.

    The second grouping of the feature areas, and the only AUTHORED one. `component_layers`
    gives the structural grouping — where an area's code sits — and that is genuinely not the
    grouping a person reasons in. Both are kept because they answer different questions, and
    neither is derivable from the other. Multi-valued, primary first.

    A missing or unparseable ledger yields `{}`: a viewer then offers only the layer
    grouping.
    """
    path = root / ledger
    if not ledger or not path.is_file():
        return {}
    out: dict[str, list[str]] = {}
    for slug, cell, _tier in LEDGER_ROW_RE.findall(path.read_text(encoding="utf-8")):
        fams = [x.strip() for x in cell.split(",") if x.strip()]
        if fams:
            out.setdefault(slug, fams)
    return out


def feature_tiers(root: Path, ledger: str = COVERAGE_LEDGER) -> dict[str, str]:
    """`area slug -> tier`, from the `Tier` column of the feature-coverage ledger.

    The one AUTHORED importance in the corpus (`core` / `rotation` / `parked`, or blank for an
    area a human has not tiered yet). It is the same column `_knowledge_hygiene` validates, read
    here so a page that orders areas by importance does not re-derive it (PRD 0776, design D2).

    A blank cell is kept as `""` rather than dropped: an untiered area is a real area that sorts
    last, and a reader that could not tell it apart from an absent row would lose it. A missing or
    unparseable ledger yields `{}`.
    """
    path = root / ledger
    if not ledger or not path.is_file():
        return {}
    out: dict[str, str] = {}
    for slug, _family, tier in LEDGER_ROW_RE.findall(path.read_text(encoding="utf-8")):
        out[slug] = tier.strip()
    return out


def capability_aliases(root: Path, file_name: str = CAPABILITY_ALIASES) -> dict[str, str]:
    """`{CAP-NNNN -> the area-prefixed id it used to carry}` from the allocation ledger.

    Capability ids are opaque, which is what lets a capability move between areas. Every
    citation written before that — a shipped PRD's acceptance criteria, a merged audit
    record, an issue body, a test's failure string — still says the old id, and none of those
    were rewritten. So an index carries the old id alongside the new one.
    """
    out: dict[str, str] = {}
    f = root / file_name
    if not file_name or not f.is_file():
        return out
    for line in f.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cols = [c.strip() for c in s.strip("|").split("|")]
        if len(cols) >= 2 and re.fullmatch(r"CAP-\d{4}", cols[0]) and cols[1] not in ("", "—"):
            out[cols[0]] = cols[1]
    return out


# ─────────────────────────── PRDs ───────────────────────────


def prds(root: Path, prds_dir: str = PRDS_DIR, own: str | None = None) -> list[dict[str, Any]]:
    """Every PRD's frontmatter, keyed by its 4-digit number.

    A PRD is the ONLY entity whose `status:` is authored; every tier above it is computed
    from those values.
    """
    # An OWN-qualified reference (`acme:0012` in `acme`) is the local id: normalised here, at
    # parse time, so the roll-up and the board never read it as another corpus's.
    own_name = resolve_own(root, own)
    out: list[dict[str, Any]] = []
    for f in sorted(root.glob(f"{prds_dir}/*/prd.md")):
        text = f.read_text(encoding="utf-8")
        fm = frontmatter(text)
        h1 = H1_RE.search(text)
        out.append(
            {
                "n": f.parent.name.split("-")[0],
                "slug": f.parent.name,
                "title": (field(fm, "title") or (h1.group(1).strip() if h1 else f.parent.name))[:TITLE_CHARS],
                "status": field(fm, "status"),
                # The optional short plain-language title (`plain_title:`); "" when the PRD carries none.
                "plain": field(fm, "plain_title").strip().strip("\"'").strip(),
                "slice": localize_entry(field(fm, "slice") or "", own_name) or field(fm, "slice"),
                "target": field(fm, "target"),
                "priority": field(fm, "priority"),
                "phase": field(fm, "phase"),
                "dep": [localize_entry(d, own_name) for d in listfield(fm, "depends_on")],
                "impl": [localize_entry(i, own_name) for i in listfield(fm, "implements")],
            }
        )
    return out


#: One `status_history:` entry's two leading keys. The map is matched from its OPENING brace so
#: a free-text `note:` later on the line — routinely hundreds of characters, and free to contain
#: braces and the word `at:` — can never be read as either key. `dispatch.prd._fm_state_history`
#: in `fleet-service` reads `state:` the same way for the same reason.
_HISTORY_ENTRY_RE = re.compile(r"^\s*-\s*\{\s*state:\s*([A-Za-z0-9_-]+)\s*,\s*at:\s*([^,}\s]+)")

#: The instant shapes an `at:` is authored in: a date, or a date and a time, with or without
#: seconds, fractions and an offset. Anything else is refused by name rather than passed on —
#: the value is cast to an instant by the database that stores it, and one malformed stamp
#: must cost its own entry, never a whole sync.
_INSTANT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:T(\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)(Z|[+-]\d{2}:?\d{2})?)?$")


def _explicit_instant(raw: str) -> str:
    """`raw` spelled with its zone stated, or `""` when it is not an instant at all.

    A date alone is midnight UTC and a time with no zone is UTC: the corpus writes every stamp
    in UTC (`Z`), and a value with no zone left to the storing session's `TimeZone` would be
    read differently by two databases configured differently. So the zone is written HERE, once,
    and the string that leaves this package is never ambiguous.
    """
    m = _INSTANT_RE.match(raw.strip().strip('"').strip("'"))
    if not m:
        return ""
    day, clock, zone = m.groups()
    return f"{day}T{clock or '00:00'}{zone or 'Z'}"


def prd_status_history(root: Path, prds_dir: str = PRDS_DIR) -> dict[str, list[dict[str, str]]]:
    """Every PRD's `status_history:` — `{n: [{state, at}, ...]}` in file order.

    **The instants are returned as TEXT and nothing here reads them as time.** This package
    derives no date, duration or rate anywhere (`tests/test_rollup.py`'s standing absence), and
    reading a stamp does not need to: it is a recorded fact about when an authored status moved,
    handed on exactly as written, with its zone made explicit. What a consumer derives from two
    of them is that consumer's question and is argued where it is asked.

    A PRD with no history, or whose entries carry no readable `at:`, maps to `[]` rather than
    being dropped, so "this PRD records no moves" and "this PRD was not read" stay different.
    An entry whose `at:` is not an instant is skipped on its own.
    """
    out: dict[str, list[dict[str, str]]] = {}
    for f in sorted(root.glob(f"{prds_dir}/*/prd.md")):
        fm = frontmatter(f.read_text(encoding="utf-8"))
        entries: list[dict[str, str]] = []
        head = re.search(r"^status_history:[ \t]*$", fm, re.M)
        if head:
            for line in fm[head.end() :].splitlines()[1:]:
                if line[:1] not in (" ", "\t"):
                    break  # dedented back to the next frontmatter key — the list is over
                m = _HISTORY_ENTRY_RE.match(line)
                if m and (at := _explicit_instant(m.group(2))):
                    entries.append({"state": m.group(1), "at": at})
        out[f.parent.name.split("-")[0]] = entries
    return out


#: A full git commit id, as `prd:blueprint` writes it into `design.md`'s frontmatter. Only the
#: full form: an abbreviation is ambiguous by construction as history grows, and the value is
#: something a service resolves to the generation it served, not something a person reads.
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def prd_designed_against(root: Path, prds_dir: str = PRDS_DIR) -> dict[str, str]:
    """Every design's `designed_against:` — `{n: commit}` for each PRD that carries a `design.md`.

    The commit of `main` the design's citations were checked at (`prd:blueprint` Step 7). It is
    what lets a consumer tell a design written before a prerequisite shipped from one written
    after it — by mapping the commit to the generation that served it and comparing generations,
    which is that consumer's derivation and not this reader's. **No time is read here.**

    A PRD with a `design.md` whose field is absent or not a full lowercase commit id maps to
    `""`: a design nobody recorded the ground of (every design written by hand before the field
    existed), which is a different answer from a PRD with no design at all — that one is absent.
    """
    out: dict[str, str] = {}
    for f in sorted(root.glob(f"{prds_dir}/*/design.md")):
        value = field(frontmatter(f.read_text(encoding="utf-8")), "designed_against").strip().strip("\"'")
        out[f.parent.name.split("-")[0]] = value if _COMMIT_RE.match(value) else ""
    return out


def prd_detail(
    root: Path,
    prefixes: list[str],
    prds_dir: str = PRDS_DIR,
    owned: Mapping[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Per-PRD body: the problem it solves, its ACs and the requirement ids each AC cites.

    The citation pattern is built from the registers' OWN prefixes, so an issue key of the
    same shape can never be mistaken for a commitment claim — plus the prefixes a sibling
    corpus owns (`owned`, `{prefix: corpus}`), whose bare ids are that corpus's rows and come
    back qualified (`[FLT-104]` -> `fleet:FLT-104`). A repo-qualified citation
    (`[fleet:FLT-104]`) is read with its qualifier, never as a local id.
    """
    owned = dict(owned or {})
    known = sorted(set(prefixes) | set(owned))
    alt = "|".join(re.escape(p) for p in known)
    cite = re.compile(rf"\[((?:[a-z][a-z0-9-]*:)?(?:{alt})-\d+)\]") if known else None
    bold_cite = re.compile(rf"\*\*\[(?:[a-z][a-z0-9-]*:)?(?:{alt})-\d+\]\*\*") if known else None

    def canonical(rid: str) -> str:
        owner = owned.get(rid.split("-", 1)[0]) if ":" not in rid else None
        return f"{owner}:{rid}" if owner else rid

    out: dict[str, dict[str, Any]] = {}
    for f in sorted(root.glob(f"{prds_dir}/*/prd.md")):
        text = f.read_text(encoding="utf-8")
        acs = []
        for b in bullets(section(text, "Acceptance Criteria"), MAX_ACS):
            ids = [canonical(i) for i in cite.findall(b)] if cite else []
            acs.append({"t": (bold_cite.sub("", b).strip() if bold_cite else b), "ids": ids})
        out[f.parent.name.split("-")[0]] = {
            "problem": first_paragraph(section(text, "Problem & Motivation"), SUMMARY_CHARS),
            "acs": acs,
            "reqs": bullets(section(text, "Requirements"), MAX_REQUIREMENTS),
            "nongoals": bullets(section(text, "Non-Goals"), MAX_NON_GOALS),
            "open": bullets(section(text, "Open decisions"), MAX_OPEN_DECISIONS),
        }
    return out


# ─────────────────────────── journeys ───────────────────────────


def journey_files(root: Path, journeys_dir: str = JOURNEYS_DIR) -> list[tuple[Path, str]]:
    """Every journey file with its tier — `flow` first, then `map`.

    **Both tiers are journeys.** A capability's `Tested by` cell may name a MAP as its
    primary tester, so a reader that enumerated flows alone reports map-tested capability
    rows as "no journey tests it". Flow-first matches how a slug shared by both tiers
    resolves.
    """
    seen: set[str] = set()
    out: list[tuple[Path, str]] = []
    if not journeys_dir:
        return out
    for tier, sub in (("flow", "flows"), ("map", "maps")):
        for f in sorted(root.glob(f"{journeys_dir}/{sub}/*.md")):
            if f.name == "README.md" or f.stem.startswith("_") or f.stem in seen:
                continue
            seen.add(f.stem)
            out.append((f, tier))
    return out


def journeys(root: Path, journeys_dir: str = JOURNEYS_DIR) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for f, tier in journey_files(root, journeys_dir):
        h1 = re.search(r"^#\s+(.+)$", f.read_text(encoding="utf-8"), re.M)
        out.append({"slug": f.stem, "title": h1.group(1).strip() if h1 else f.stem, "kind": tier})
    return out


def journey_detail(root: Path, journeys_dir: str = JOURNEYS_DIR) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for f, tier in journey_files(root, journeys_dir):
        text = f.read_text(encoding="utf-8")
        fm = frontmatter(text)
        job = JOB_RE.search(text)
        pre = PRE_RE.search(text)
        steps = []
        for line in section(text, "Happy path").splitlines():
            m = STEP_RE.match(line)
            if m:
                steps.append(m.group(2).strip()[:STEP_CHARS])
        out[f.stem] = {
            "kind": tier,
            "persona": field(fm, "persona"),
            "surfaces": listfield(fm, "surfaces"),
            # A flow names one owning PRD; a map names several, since it spans them.
            "owning_prd": field(fm, "owning_prd") or (listfield(fm, "owning_prds") or [""])[0],
            "used_by": listfield(fm, "used_by"),
            # The map tier's own edge: the journeys it composes. The inverse of a flow's
            # `used_by`, and the one thing that makes a map more than a long flow.
            "composes": listfield(fm, "composes"),
            "covers": listfield(fm, "covers"),
            "job": one_line(job.group(1), JOB_CHARS) if job else "",
            "pre": one_line(pre.group(1), PRECONDITION_CHARS) if pre else "",
            "steps": steps[:MAX_STEPS],
        }
    return out


def covers_inverse(detail: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """`capability id -> the journeys whose own `covers:` names it`.

    The authored edge runs both ways and the two are not always in step: a journey may
    declare it covers a capability while the map's `Tested by` cell for that row still reads
    a prose note. Both are read; the union is what stops a gap being reported that the
    journey catalog has already closed.
    """
    out: dict[str, list[str]] = defaultdict(list)
    for slug, d in detail.items():
        for cap in d.get("covers", []):
            if slug not in out[cap]:
                out[cap].append(slug)
    return dict(out)


def tested_slugs(cell: str, known: set[str]) -> list[str]:
    """The journeys a `Tested by` cell actually names, resolved against the catalog.

    Backticked tokens first, comma split as the fallback, and every candidate checked against
    the real journey set — an unparsed fragment must read as "no journey tests it" rather
    than inflate the coverage number.
    """
    toks = BACKTICK_RE.findall(cell) or cell.split(",")
    return [t for t in dict.fromkeys(x.strip(" `·—-") for x in toks) if t in known]


# ─────────────────────────── feature maps ───────────────────────────


def feature_rows_dir(root: Path, features_dir: str = FEATURES_DIR) -> Path:
    """Where capability row fragments live: `<root>/<features_dir>/rows`."""
    return root / features_dir / FEATURE_ROWS_SUBDIR


def load_feature_row_fragments(
    root: Path, features_dir: str = FEATURES_DIR
) -> dict[str, list[tuple[int, str, list[str], Path]]]:
    """`{table key -> [(order, id, cells, path)]}` across every capability fragment.

    An absent directory is `{}` — every feature map then reads its committed table, which is
    what a corpus that has not migrated yet needs. A fragment whose stem is not a capability
    id, or whose JSON is missing `table`/`order`/`cells`, is skipped (the gate catches it).
    """
    base = feature_rows_dir(root, features_dir)
    if not base.is_dir():
        return {}
    out: dict[str, list[tuple[int, str, list[str], Path]]] = {}
    for f in sorted(base.glob("*.json")):
        if not CAP_ID_RE.match(f.stem):
            # Honour a configured prefix? Fragments always use CAP-NNNN in this layout; a
            # foreign corpus with a different prefix simply has no matching files here and
            # falls back to its tables.
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        table = str(data.get("table") or "")
        order = data.get("order")
        raw_cells = data.get("cells")
        if not table or not isinstance(order, int) or not isinstance(raw_cells, list):
            continue
        out.setdefault(table, []).append((order, f.stem, [str(c) for c in raw_cells], f))
    for _table, rows in out.items():
        rows.sort(key=lambda r: (r[0], int(r[1].split("-", 1)[1])))
    return out


def feature_table_layouts(text: str) -> dict[str, dict[str, int]]:
    """`{table key -> {column name lowercased: index}}` from `<!-- rows: -->` markers + headers."""
    lines = text.splitlines()
    layouts: dict[str, dict[str, int]] = {}
    i = 0
    while i < len(lines):
        m = FEATURE_ROWS_MARKER_RE.match(lines[i].strip())
        if m:
            key = m.group(1)
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].lstrip().startswith("|"):
                header = cells(lines[j])
                if header and _header(header, "id", "capability"):
                    layouts[key] = {name.strip().lower(): idx for idx, name in enumerate(header)}
            i += 1
            continue
        i += 1
    return layouts


def _cell_from(row: list[str], cols: dict[str, int], name: str) -> str:
    """Named cell from a full row (id in slot 0), or empty when the column is absent."""
    idx = cols.get(name)
    if idx is None or idx >= len(row):
        return ""
    return row[idx]


def caps_from_fragments(
    _stem: str,
    text: str,
    domain_frags: dict[str, list[tuple[int, str, list[str], Path]]],
    *,
    cap_re: re.Pattern[str],
    cap_ref: re.Pattern[str],
    alias: dict[str, str],
    journey_slugs: set[str],
    covered_by: dict[str, list[str]],
    own: str = "",
) -> list[dict[str, Any]]:
    """Capability rows for one feature map, assembled from its per-row fragments."""
    layouts = feature_table_layouts(text)
    marker_use = _marker_uses(text)
    caps: list[dict[str, Any]] = []
    for key in sorted(domain_frags):
        cols = layouts.get(key)
        if cols is None:
            # No marker in the shell: assume the four positional columns every map has always
            # carried, which is enough for the fields `features()` always populates.
            cols = {
                "id": 0,
                "capability": 1,
                "ships in": 2,
                "ships in (prd)": 2,
                "tested by": 3,
                "tested by (journey/flow)": 3,
            }
        for _order, cap_id, cell_vals, _src in domain_frags[key]:
            if not cap_re.match(cap_id):
                continue
            full = [cap_id, *cell_vals]
            # Name / ships / tested are positional in every map (indices 1/2/3); optional
            # columns are read by name exactly as the table walk does.
            name = full[1] if len(full) > 1 else ""
            ships_cell = full[2] if len(full) > 2 else ""
            # Header spellings vary: "Tested by" / "Tested by (journey/flow)".
            tested_idx = next((cols[k] for k in ("tested by", "tested by (journey/flow)") if k in cols), 3)
            tested_cell = full[tested_idx] if tested_idx < len(full) else ""
            mark = SHIPS_MARK_RE.match(ships_cell)
            tested = tested_slugs(tested_cell, journey_slugs)
            for slug in covered_by.get(cap_id, []):
                if slug not in tested:
                    tested.append(slug)
            needs_cell = _cell_from(full, cols, "needs")
            caps.append(
                {
                    "id": cap_id,
                    "name": name.strip(),
                    "needs": [
                        x for x in cap_ref.findall(mask_qualified(localize_text(needs_cell, own))) if x != cap_id
                    ],
                    "anchor": plain(_cell_from(full, cols, "anchor")),
                    "plain": _plain_title(_cell_from(full, cols, "plain")),
                    "was": alias.get(cap_id, ""),
                    "ships": list(dict.fromkeys(PRD_NUM_RE.findall(mask_qualified(localize_text(ships_cell, own))))),
                    "mark": mark.group(1).lower() if mark else "",
                    "tested": tested,
                    "shipsRaw": ships_cell.strip(),
                    "testedRaw": tested_cell.strip(),
                    **_use_fields(marker_use.get(key)),
                }
            )
    return caps


def _plain_title(cell: str) -> str:
    """A `Plain` cell as the title it carries: `""` for an empty cell or a bare dash (the map's "none")."""
    value = plain(cell)
    return "" if value in {"—", "–", "-"} else value


def _use_fields(use: featurebrief.Use | None) -> dict[str, Any]:
    """A capability's `use` (the `###` section of `## Capabilities` it sits in) and `misfit` flag.

    A row in `### Misfits (to move)` has no use and is a misfit; a row in `### Retired` has no use and is
    retired; a row outside any use section
    (a map not yet cut into uses, or a table under another `##`) has no use and is not one.
    """
    if use is None:
        return {"use": None, "misfit": False, "retired": False}
    if not use.is_use:
        return {"use": None, "misfit": use.misfit, "retired": use.retired}
    return {"use": use.name, "misfit": False, "retired": False}


def _marker_uses(text: str) -> dict[str, featurebrief.Use | None]:
    """`{table key -> the use whose section holds its `<!-- rows: -->` marker}` for a fragment shell."""
    at = featurebrief.use_of_lines(text)
    out: dict[str, featurebrief.Use | None] = {}
    for i, line in enumerate(text.splitlines()):
        m = FEATURE_ROWS_MARKER_RE.match(line.strip())
        if m:
            out.setdefault(m.group(1), at[i])
    return out


def features(
    root: Path,
    layers: list[dict[str, str]] | None = None,
    layer_of: dict[str, str] | None = None,
    journey_slugs: set[str] | None = None,
    covered_by: dict[str, list[str]] | None = None,
    fam_of: dict[str, list[str]] | None = None,
    tier_of: dict[str, str] | None = None,
    features_dir: str = FEATURES_DIR,
    aliases_file: str = CAPABILITY_ALIASES,
    capability_prefix: str = CAPABILITY_PREFIX,
    own: str | None = None,
) -> list[dict[str, Any]]:
    """Every feature area with its capability rows.

    The optional arguments exist so a caller that already built the journey catalog and the
    component registry does not build them twice; each is derived here when omitted.

    **Fragments win when they exist for an area** (ENG-12980). When
    `<root>/features/rows/` holds fragments whose `table` key starts with `<stem>#`, those
    fragments are the capability source and the committed table body is ignored for that
    map. A map with no such fragments still reads its table, so a corpus mid-migration is
    served correctly (the programs/slices precedent: ENG-12661).
    """
    own_name = resolve_own(root, own)
    if layers is None or layer_of is None:
        layers, layer_of = component_layers(root)
    if fam_of is None:
        fam_of = feature_families(root)
    if tier_of is None:
        tier_of = feature_tiers(root)
    if journey_slugs is None:
        journey_slugs = {j["slug"] for j in journeys(root)}
    if covered_by is None:
        covered_by = covers_inverse(journey_detail(root))
    order = {row["id"]: i for i, row in enumerate(layers)}
    cap_re = cap_id_pattern(capability_prefix)
    cap_ref = cap_ref_pattern(capability_prefix)
    alias = capability_aliases(root, aliases_file)
    out: list[dict[str, Any]] = []
    if not features_dir:
        return out
    all_frags = load_feature_row_fragments(root, features_dir)
    for f in map_files(root / features_dir):
        if f.name == "README.md" or area_stem(f).startswith("_"):
            continue
        text = f.read_text(encoding="utf-8")
        fm = frontmatter(text)
        intent = INTENT_RE.search(text)
        uses = featurebrief.capability_uses(text)
        brief, _brief_problems = featurebrief.parse_brief(fm)
        stem_prefix = area_stem(f) + "#"
        domain_frags = {k: v for k, v in all_frags.items() if k.startswith(stem_prefix)}
        if domain_frags:
            # Fragments win: the committed table body is a generated projection (ENG-12660)
            # and may lag or disagree. Read the fragments; keep the shell for frontmatter.
            caps = caps_from_fragments(
                area_stem(f),
                text,
                domain_frags,
                cap_re=cap_re,
                cap_ref=cap_ref,
                alias=alias,
                journey_slugs=journey_slugs,
                covered_by=covered_by,
                own=own_name,
            )
        else:
            caps = []
            # The most recent capability-table header, as `{column name: index}`. The first four
            # columns are positional in every map and always have been; the OPTIONAL fifth and
            # sixth (`Anchor`, `Needs`) are not, and one map carries a seventh. Reading those two
            # by position would have taken `Anchor` for `Needs` in the ten maps that carry only the
            # first of them — a build-order edge invented out of a surface reference. So the extra
            # columns are read BY NAME and are absent when the table does not declare them.
            cols: dict[str, int] = {}
            use_at = featurebrief.use_of_lines(text, uses)
            for lineno, line in enumerate(text.splitlines()):
                if not line.lstrip().startswith("|"):
                    cols = {}  # a heading or a paragraph ends the table it followed
                    continue
                c = cells(line)
                if _header(c, "id", "capability"):
                    cols = {name.strip().lower(): i for i, name in enumerate(c)}
                    continue
                if len(c) < 4 or not cap_re.match(c[0]):
                    continue

                cap_id, name, ships_cell, tested_cell = c[0], c[1], c[2], c[3]
                mark = SHIPS_MARK_RE.match(ships_cell)
                tested = tested_slugs(tested_cell, journey_slugs)
                for slug in covered_by.get(cap_id, []):
                    if slug not in tested:
                        tested.append(slug)
                caps.append(
                    {
                        "id": cap_id,
                        "name": name.strip(),
                        # The build-order edge between capabilities, when the map declares the
                        # column. Every id the cell names, resolved against the SAME pattern the
                        # first column is matched with — a cell reads `CAP-0527` or
                        # `CAP-0527, CAP-0485`, and one of them is prose around the ids.
                        # A repo-qualified id (`fleet:CAP-1408`) is another corpus's and is masked
                        # out — never read as this corpus's own (`fleet_knowledge.corpusref`).
                        "needs": [
                            x
                            for x in cap_ref.findall(mask_qualified(localize_text(_cell(c, cols, "needs"), own_name)))
                            if x != cap_id
                        ],
                        # Where the capability is surfaced, when the map says. A reference for a
                        # reader, never an edge: nothing resolves it.
                        "anchor": plain(_cell(c, cols, "anchor")),
                        # The short plain-language title, when the map declares a `Plain` column.
                        "plain": _plain_title(_cell(c, cols, "plain")),
                        # The pre-opacity area-prefixed id, so a citation nobody migrated still
                        # resolves. Absent for a capability minted afterwards.
                        "was": alias.get(cap_id, ""),
                        # `Ships in` cites PRDs by number; the cell also carries link markup, so
                        # one PRD is named twice — dedupe, or every count doubles.
                        "ships": list(
                            dict.fromkeys(PRD_NUM_RE.findall(mask_qualified(localize_text(ships_cell, own_name))))
                        ),
                        # `core` / `shipped` / `retired`, or "". The state that says a capability
                        # is BUILT with no single owning PRD — the distinction between a delivery
                        # gap and a delivered thing the pipeline never owned.
                        "mark": mark.group(1).lower() if mark else "",
                        "tested": tested,
                        # Both raw cells ride along so a reader can check the derivation against
                        # what the map actually says, rather than trusting this parse.
                        "shipsRaw": ships_cell.strip(),
                        "testedRaw": tested_cell.strip(),
                        # The use this row serves: the `###` section of `## Capabilities` it sits
                        # in (featurebrief). Structural, like the row's area being its file.
                        **_use_fields(use_at[lineno]),
                    }
                )
        components = listfield(fm, "components")
        # The area's ARCHITECTURE GROUP, derived — never authored. Each `components:` entry
        # resolves to that component's layer, and the layer holding the most of them is the
        # group the area renders under; a tie goes to whichever layer the registry draws
        # first, so the ordering is the architecture's own. The full set rides along with the
        # primary — an area is *placed* by one layer and *reaches* into several.
        spans = Counter(layer_of[c] for c in components if c in layer_of)
        primary = min(spans, key=lambda x: (-spans[x], order.get(x, len(order)))) if spans else ""
        out.append(
            {
                "area": field(fm, "area") or area_stem(f),
                "file": area_stem(f),
                # `product` (the default, and omitted) or `substrate`. A substrate area is
                # real and owned but no customer would name it as a feature, so it must not
                # be counted in a "what can a customer do" reading.
                "kind": field(fm, "kind") or "product",
                "intent": one_line(unquote_block(intent.group(1)), INTENT_CHARS) if intent else "",
                "desc": area_description(text, field(fm, "area") or area_stem(f)),
                "group": primary,
                "groups": sorted(spans, key=lambda x: order.get(x, len(order))),
                "fams": fam_of.get(field(fm, "area") or area_stem(f), []),
                # The authored `Tier` the coverage ledger sets for this area (PRD 0776): `core`
                # / `rotation` / `parked`, or `""` for one a human has not tiered. Read here so
                # a page that orders areas by importance does not parse the ledger twice.
                "tier": tier_of.get(field(fm, "area") or area_stem(f), ""),
                "journeys": listfield(fm, "journeys"),
                "components": components,
                "surfaces": listfield(fm, "surfaces"),
                # The WHOLE `> **Intent.**` paragraph, unbounded — `intent` above is clipped for an
                # index and `desc` is its first sentence; a feature's own page reads all of it.
                "intentFull": unquote_block(intent.group(1)) if intent else "",
                # The newcomer's reading (featurebrief): `None` for a map that carries no brief,
                # never an empty one — "not written" and "written empty" are different facts.
                # Malformed parts are the `feature-briefs` check's to report; what parsed rides.
                "brief": brief,
                # The `###` uses of `## Capabilities`, in order, the misfit section included.
                "uses": [u.row() for u in uses],
                "caps": caps,
            }
        )
    return out


# ─────────────────────────── the glossary ───────────────────────────
#
# The single source for what each entity in the ladder IS. A viewer that carried its own
# copy of those definitions is the same failure the requirement registers exist to prevent:
# two texts, one of them quietly wrong.
#
# The contract: exactly two `##` headings own tables — `## Entities` (the authored ladder)
# and `## Derived views` (computed readings) — every row is 7 cells, `Key | Term | What it is
# | Test | Real example | Industry equivalent | Defined in`, and everything else is prose. An
# ABSENT file is normal, not an error.
GLOSSARY_SECTIONS = ("Entities", "Derived views")
GLOSSARY_COLS = 7
GLOSSARY_KEY_RE = re.compile(r"^[a-z][a-z0-9-]*$")
# Keys may carry RETIRED entity names, kept so the projection is a straight swap with no
# regression. A reader is shown the real names, so the rename happens here.
GLOSSARY_KEY_ALIAS = {"project": "slice", "initiative": "program"}
MERMAID_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.S)


def glossary(root: Path, file_name: str = GLOSSARY_FILE) -> dict[str, Any]:
    """Every glossary term, plus the entity-relationship diagram if one is drawn.

    `{}` when the file is absent — a viewer reads that as "use the built-in definitions",
    which is what lets it ship before the glossary does.
    """
    path = root / file_name
    if not file_name or not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    terms: list[dict[str, str]] = []
    for heading in GLOSSARY_SECTIONS:
        for c in md_rows(section(text, heading)):
            if len(c) != GLOSSARY_COLS:
                continue
            key = plain(c[0])
            if not GLOSSARY_KEY_RE.match(key) or key == "key":
                continue
            terms.append(
                {
                    "k": GLOSSARY_KEY_ALIAS.get(key, key),
                    "term": plain(c[1]),
                    "what": plain(c[2]),
                    "test": plain(c[3]),
                    "example": plain(c[4]),
                    "industry": plain(c[5]),
                    "where": plain(c[6]),
                    "sec": heading,
                }
            )
    if not terms:
        return {}
    m = MERMAID_RE.search(text)
    return {
        "terms": terms,
        # The ERD as SOURCE, not as a rendered picture: a self-contained page has no network
        # access by construction, and pulling in a diagram bundle to draw it would cost more
        # than the diagram is worth.
        "diagram": m.group(1).strip() if m else "",
        # Named relative to the corpus root, never to a repository: the root is a parameter,
        # and a repo-relative path throws the moment the corpus sits somewhere else.
        "source": f"{root.name}/{path.relative_to(root)}",
    }


# ─────────────────────────── program / slice narrative ───────────────────────────


def detail_prose(path: Path) -> dict[str, Any]:
    """A program's or a slice's optional detail file, as narrative a viewer can render.

    The reasoning is the point; the arithmetic is the supporting evidence. A generator that
    stored `is_file()` here left every program page as arithmetic with the argument deleted.

    Returns `{title, lead, sections:[{h, body}]}` — raw markdown, blocked and rendered by the
    viewer. `{}` for an absent file, which is normal: a detail file is optional by design.
    """
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    body = strip_frontmatter(text)
    # The H1 is the file's own headline, and it is routinely better prose than the register's
    # title cell. A viewer shows it when the two differ, so it must not also appear in the
    # lead.
    h1 = re.search(r"^#\s+(.+)$", body, re.M)
    title = h1.group(1).strip() if h1 else ""
    if h1:
        body = body[h1.end() :]
    parts = re.split(r"^(##\s+.+)$", body, flags=re.M)
    sections: list[dict[str, Any]] = []
    for i in range(1, len(parts), 2):
        heading = parts[i].lstrip("#").strip()
        sec = parts[i + 1].strip()
        if not sec or heading.lower() in DETAIL_SKIP:
            continue
        sections.append({"h": heading, "body": sec})
    lead = parts[0].strip()
    if not (title or lead or sections):
        return {}
    return {"title": title, "lead": lead, "sections": sections}


def program_details(root: Path, ids: list[str], subdir: str = PROGRAM_DETAIL_SUBDIR) -> dict[str, dict[str, Any]]:
    """`PG-id -> detail_prose`, for every id whose file exists."""
    return {i: d for i in ids if (d := detail_prose(program_detail(root, i, subdir)))}


def slice_details(root: Path, ids: list[str], subdir: str = SLICE_DETAIL_SUBDIR) -> dict[str, dict[str, Any]]:
    """`SL-id -> detail_prose`, for every id whose file exists."""
    return {i: d for i in ids if (d := detail_prose(slice_detail(root, i, subdir)))}


def detail_body(path: Path) -> str:
    """A detail file's TEXT, unparsed. "" when it does not exist, which is the ordinary case.

    The pair below exists beside `program_details`/`slice_details` rather than replacing them
    because the two readers answer different questions. Those shape a file into the sections a
    viewer renders; this hands back the bytes, for a reader that parses a section of its own —
    `rollup.bar_reading` is the first, and it stays pure by taking text it never had to open.
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def program_bodies(root: Path, ids: list[str], subdir: str = PROGRAM_DETAIL_SUBDIR) -> dict[str, str]:
    """`PG-id -> the detail file's text`, for every id whose file exists."""
    return {i: t for i in ids if (t := detail_body(program_detail(root, i, subdir)))}


def slice_bodies(root: Path, ids: list[str], subdir: str = SLICE_DETAIL_SUBDIR) -> dict[str, str]:
    """`SL-id -> the detail file's text`, for every id whose file exists."""
    return {i: t for i in ids if (t := detail_body(slice_detail(root, i, subdir)))}


# ─────────────────────────── shaped register rows ───────────────────────────


def slice_rows(
    root: Path,
    raw: list[dict[str, Any]] | None = None,
    file_name: str = SLICE_FILE,
    prefix: str = SLICE_PREFIX,
    detail_subdir: str = SLICE_DETAIL_SUBDIR,
    own: str | None = None,
) -> list[dict[str, Any]]:
    """Slice register rows shaped for a viewer: one-lined `Done when`, a numeric sort key."""
    out: list[dict[str, Any]] = []
    for s in raw if raw is not None else slices(root, file_name, prefix, detail_subdir, own):
        out.append(
            {
                "id": s["id"],
                # The numeric part, kept as its own field for a search index's sort key.
                "n": s["id"].split("-")[1],
                "title": s["title"] or s["id"],
                "kind": s["kind"],
                "program": s["program"],
                # Its feature area (FLT-1280): a feature map's slug; `""` on a row written before the rule.
                "area": str(s.get("area") or ""),
                # A slice names its OWN proof — normally a member PRD, answering "does this
                # slice do what it said?". The program's names the composed thread ACROSS
                # slices. Without both, one composed proof would green every slice under it.
                "verified_by": s["verified_by"],
                "done": one_line(s["done"], DONE_WHEN_CHARS),
                "dep": s["depends_on"],
                "component": s["component"],
                # The decision axis, as parsed — `{"kind", "ref"}`. Carried whole rather than
                # flattened so a viewer and a store see the same two facts the register holds.
                "disposition": s["disposition"],
                # The reasoned per-row waiver (ENG-12602), carried so the board reads it through
                # `registers.slice_proof_waivers` — the gate's own reader — and not a retired file.
                "proof_waiver": str(s.get("proof_waiver", "")),
                # Which of the two things that waiver says (2026-10-07) — `excused` settles the
                # cut, `deferred` leaves its proof owed — read by `registers.slice_waiver_readings`.
                "proof_waiver_kind": str(s.get("proof_waiver_kind", "")),
                "proof_waiver_owed": str(s.get("proof_waiver_owed", "")),
                # Where that owed proof can only be taken (2026-10-08): `production`, or `""` for a
                # proof the fleet can produce itself — read by `rollup.board` onto the cut's `owedNeeds`.
                "proof_waiver_needs": str(s.get("proof_waiver_needs", "")),
            }
        )
    return out


def program_rows(
    root: Path,
    raw: list[dict[str, Any]] | None = None,
    file_name: str = PROGRAM_FILE,
    prefix: str = PROGRAM_PREFIX,
    detail_subdir: str = PROGRAM_DETAIL_SUBDIR,
    own: str | None = None,
) -> list[dict[str, Any]]:
    """Program register rows shaped for a viewer."""
    out: list[dict[str, Any]] = []
    for p in raw if raw is not None else programs(root, file_name, prefix, detail_subdir, own):
        out.append(
            {
                "id": p["id"],
                "title": p["title"] or p["id"],
                "kind": p["kind"],
                # The composed thread across this program's slices, and the ONLY authored
                # input to its completion reading.
                "verified_by": p["verified_by"],
                # The roots of the decomposition. Carried because its ABSENCE is a finding:
                # a program holding slices but naming no roots has a plan nobody can replay,
                # and nothing else in the corpus can tell that apart from a program nobody
                # has decomposed yet.
                "requires": p["requires"],
                # The decision axis — see `slice_rows`.
                "disposition": p["disposition"],
            }
        )
    return out


__all__ = [
    "AREA_DESC_CHARS",
    "COMPONENT_PROSE_CHARS",
    "DETAIL_SKIP",
    "DIAGRAM_LAYOUT_FILE",
    "area_description",
    "capability_aliases",
    "component_layers",
    "covers_inverse",
    "detail_body",
    "detail_prose",
    "diagram_layout",
    "externals",
    "feature_families",
    "feature_tiers",
    "features",
    "glossary",
    "journey_detail",
    "journey_files",
    "journeys",
    "outcomes",
    "prd_designed_against",
    "prd_detail",
    "prd_status_history",
    "prds",
    "program_bodies",
    "program_details",
    "program_rows",
    "slice_bodies",
    "slice_details",
    "slice_rows",
    "tested_slugs",
    "clip",
]
