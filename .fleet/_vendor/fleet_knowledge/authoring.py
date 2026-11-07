"""Which docs page says what goes into a knowledge file, and the agent entry point built on it.

An agent about to write a journey, a PRD or a decision has to find the page that describes that
file before it writes. Fleet's docs already describe each file type (`productdocs/knowledge-base/`),
but nothing in a repository told an agent to look, so a session without Fleet's MCP tools, or one
that did not think to look, wrote the file from memory and met the `knowledge-types` check instead.

This module is the one table that closes that gap, and three readers use it:

* `.fleet/instructions.md`, the primer every engine loads, ends with this table (`render_table_section`),
  filled in by `fleet commands sync` so `--check` covers it;
* the `knowledge-types` check names the page for the type it expected (`page_for_type`), so an
  agent that got it wrong is told where to read;
* the authoring commands each cite the page for the type they write
  (`tests/test_authoring_pages.py` holds `COMMAND_PAGES` against the command text).

The table cannot drift from the registry it describes: a test holds every type in Fleet's own
`knowledge/FILE-TYPES.md` to exactly one row here and each row's `lives_at` to the registry's
homes, so adding a type without placing it here fails the suite.

Stdlib only, like the rest of this package.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

__all__ = [
    "FALLBACK_PAGE",
    "KINDS",
    "FileKind",
    "docs_path",
    "page_for_type",
    "render_table_section",
]

#: Where the entry point lands: the tier's root, beside `instructions.md`.
AGENTS_SOURCE: Final = "AGENTS.md"
AGENTS_REL: Final = f".fleet/{AGENTS_SOURCE}"

#: The page that lists every type, for a type no row below places.
FALLBACK_PAGE: Final = "reference/knowledge-file-types"


@dataclass(frozen=True)
class FileKind:
    """One kind of knowledge file: the registry types it covers, where they live, the page to read."""

    label: str
    types: tuple[str, ...]
    lives_at: str
    page: str


#: Every type in Fleet's own registry appears in exactly one row. Rows lead with what an agent
#: authors by hand; the last rows hold what is generated, hand-kept infrastructure, and records.
KINDS: Final[tuple[FileKind, ...]] = (
    FileKind(
        "Journey",
        ("journey-flow", "journey-map"),
        "`journeys/flows/*.md`, `journeys/maps/*.md`",
        "knowledge-base/journeys",
    ),
    FileKind(
        "PRD and its design, plans and mockups",
        ("prd", "prd-design", "prd-ux-design", "prd-plan", "prd-note", "mockup"),
        "`prds/<NNNN-slug>/`",
        "knowledge-base/prds",
    ),
    FileKind(
        "Feature map (a feature area, its uses and capabilities)",
        ("feature-map", "feature-source-of-truth-fragment", "feature-coverage-baseline"),
        "`features/*.md`",
        "knowledge-base/feature-areas",
    ),
    FileKind(
        "Requirement (a numbered promise)",
        ("requirement-register", "requirement-row-fragment"),
        "`requirements/*.md`, `requirements/rows/*.json`",
        "knowledge-base/promises",
    ),
    FileKind("Decision record", ("decision",), "`decisions/*.md`", "knowledge-base/decisions"),
    FileKind(
        "Slice",
        ("slice-register", "slice-row", "slice-detail"),
        "`slices.md`, `slices/rows/*.json`, `slices/*.md`",
        "knowledge-base/slices",
    ),
    FileKind(
        "Program",
        ("program-register", "program-row", "program-detail", "program-proof-baseline"),
        "`programs.md`, `programs/rows/*.json`, `programs/*.md`",
        "knowledge-base/programs",
    ),
    FileKind(
        "Component",
        ("component-registry", "capability-alias-register"),
        "`specs/architecture/components.md`",
        "knowledge-base/capabilities-and-components",
    ),
    FileKind("Slot (this repository's answer to a command)", ("slot",), "`slots/*.md`", "knowledge-base/slots"),
    FileKind(
        "Record (audit, retro, check result)",
        (
            "audit-record",
            "audit-objective",
            "retro-prd",
            "retro-task",
            "retro-bug",
            "negative-control-transcript",
            "negative-control-ledger",
            "check-result",
        ),
        "`audits/`, `retros/`",
        "knowledge-base/records",
    ),
    FileKind(
        "Generated table or fragment (never hand-edited)",
        ("register-shell", "fragment-dir-keep", "shipped-script"),
        "`**/*.md.tmpl`, `**/rows/`, `scripts/*.py`",
        "knowledge-base/generated-tables",
    ),
    FileKind(
        "Anything else (spec, SOP, product vision, README, environment)",
        (
            "readme",
            "file-type-registry",
            "spec",
            "spec-asset",
            "audit-checklist",
            "product-vision",
            "sop",
            "environment-record",
        ),
        "`specs/`, `sops/`, `strategy/`, `environments/`",
        "knowledge-base/the-folder",
    ),
)


def docs_path(page: str) -> str:
    """The checkout path of a docs page id: `knowledge-base/prds` is `.fleet/docs/knowledge-base/prds.md`."""
    return f".fleet/docs/{page}.md"


def page_for_type(type_id: str) -> str:
    """The docs page id that describes files of registry type `type_id`; the full list when none does."""
    for kind in KINDS:
        if type_id in kind.types:
            return kind.page
    return FALLBACK_PAGE


def render_table_section() -> str:
    """The section of `.fleet/instructions.md` the sync generates: which page to read before a file."""
    rows = "\n".join(f"| {k.label} | {k.lives_at} | `{docs_path(k.page)}` |" for k in KINDS)
    return f"""# Before you create or change a file under `knowledge/`

Read the docs page for that file's type first. It says what the file is, what it must carry and
what not to put in it, and the `knowledge-types` check refuses a file that does not match.

| File | Lives under `knowledge/` | Read |
|---|---|---|
{rows}

A type not listed here is on `{docs_path(FALLBACK_PAGE)}`, which names every type, where it lives
and the front matter it needs. Before you add a new journey, slice, program or PRD, sort out what
kind of thing it is with `{docs_path("knowledge-base/what-is-it")}`.
"""
