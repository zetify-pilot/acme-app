"""Validate journey flows/maps + feature capability maps + their cross-links.

Three file families, one consistent contract:

  - Flows  (`<knowledge>/journeys/flows/*.md`): frontmatter `id`, `kind: flow`,
    `persona`, `surfaces`; optional `owning_prd`, `used_by`, `covers`,
    `depends_on_surfaces`.
  - Maps   (`<knowledge>/journeys/maps/*.md`):  frontmatter `id`, `kind: journey`,
    `persona`, `composes`; optional `owning_prds`, `covers`.
  - Feature maps (`<knowledge>/features/*.md`, excl. README; a FRAGMENT-BACKED map is
    discovered through its committed `<area>.md.tmpl` shell, its rows read from
    `features/rows/*.json` and its `source_of_truth:` list from
    `features/source_of_truth/<area>/*.json`, since its rendered `.md` is generated on
    demand and gitignored — see `load_feature_maps`): frontmatter `area`,
    `components` (required — see `kind:` below), optional `kind` (`product`, the
    default, or `substrate`) and `journeys`/`owning_projects` (legacy); a
    capability table
    `| ID | Capability | Ships in | Tested by | Anchor | Needs | Source of truth |`
    (Anchor/Needs/Source-of-truth all optional per map). A `kind: substrate` map is
    engineering substrate rather than a customer-recognisable feature area, and is the
    only kind allowed to declare `components: []` — some substrate (a repo's CI and test
    lanes) is code the product architecture deliberately does not draw.

**Single source of truth for ship-state.** Maps describe *structure + linkage* only —
never ship-state. Whether a capability is shipped/planned/unshipped is read from its
linked PRD's frontmatter `status:` (via the `Ships in` cell / the AC's owning PRD), never
re-asserted here. So there is **no `Status` column**, **no `[unshipped]` tag**, and **no
ship-state markers** in any map; the `[dev]`/`[ext]` AC dispositions describe the
*verification surface* (how an audit exercises the row), not whether it is built.
Coverage is read from `Tested by` (empty = journey gap); a delivery gap is `Ships in` = `—`.

Checks (all fail the commit, `file: message` per violation):

  Format   — required frontmatter fields; `id` matches filename; `kind` correct;
             every AC line under an acceptance-criteria heading carries a disposition
             tag (`[dev]` / `[ext]`). EVERY matching heading is read, not only the
             exact `## Acceptance criteria` spelling (`journeys_ac_heading_pattern`);
             a variant heading used to leave its rows unchecked (ENG-12154). A
             table-form AC section (`| # | Criterion | Disposition |`) is read row by
             row too — its Disposition cell must carry the tag — so table rows reach
             every AC leg, not only `loose` (class fix for ENG-18302).
  Navigate — every feature map carries a `> **Intent.**` header and the Navigate
             frontmatter (`specs`/`surfaces`/`source_of_truth`); `specs` resolve to
             spec files and `source_of_truth` paths exist in the repo (the freshness
             contract the reconcile workflow watches).
  ShipState— no `Status` column in a feature map; no `[unshipped]` tag and no
             ship-state marker anywhere in a flow/map/feature map; and no
             map/journey *prose* line that asserts a PRD's lifecycle state
             differently from that PRD's own frontmatter `status:` — a PRD
             reference (`PRD NNNN`, a bare `(NNNN)`, a bold `**NNNN**`) or a
             backticked flow id resolved through its `owning_prd:`, on either
             side of which a lifecycle word contradicts the linked PRD (the four
             stale lines ENG-17127 fixed, and the flow-reference / preceding-word
             shapes ENG-18544 found, reached no other leg).
  Resolve  — `composes`/`used_by` resolve to existing flow/map ids AND agree: an edge
             declared on either side must be declared on the other (a map composing a
             flow whose `used_by:` omits it, or a flow `used_by:` a map whose
             `composes:` omits it, is a half-wired link — ENG-18544);
             `owning_prd(s)` + capability `Ships in` numbers resolve to PRD
             folders; a PRD's `journeys:` entries resolve to journey files and an
             AC's `(NNNN)` PRD citation resolves to a PRD folder (both halves of
              the PRD↔journey reference edge, ENG-9450); capability ids match the
              configured id shape and are globally unique (`id-collisions` enforces
              permanence against main tip, open peers and history — ENG-12981;
              `capability-aliases.md` is the frozen historical mapping, not an
              allocation counter).
   AnchorScope — a capability's `Anchor` must resolve within ITS OWN map's
              `source_of_truth:` (map-level ∪ row-level, the same containment as
              `Cover`). An anchor outside its map's own claim is a contradiction — the
              freshness advisory keys off that claim and can never fire for the anchored
              file. Absolute: an out-of-scope anchor is a hard failure; the anchor
              baseline was retired at zero (ENG-12744), so no acknowledged-debt list
              exists to re-grow.
  Linking  — `covers:` ids resolve to a real capability; **two-way**: a
             capability's primary (first) `Tested by` journey must list that
             capability in its `covers:`, and a journey's `covers:` ids must each
             appear in that capability's `Tested by`. Catches half-wired links.
   Route    — a flow's `surfaces:` are resolved against the real route tables in the
              configured web/admin route files, accounting for the org-scoped and
              `/workspaces/{ws}/...` shorthand every flow already uses. A surface
              matching no route at all fails the commit; one that only matches a
              `<Navigate>`/`*Redirect*` route is printed as a non-blocking advisory
              (some redirects are an intentional dual entry point, not drift).
              An `admin: `/`web: ` prefix names the pool the citation resolves
              against, and the two are symmetric (ENG-10175 — skipping `web:` is
              what let an unbuilt surface ship green in ENG-10172); any other
              `<word>:` prefix on a path-shaped citation is refused rather than
              skipped, and a project's non-route vocabulary registers its own
              prefixes in `journeys_surface_skip_prefixes`.
  Depends  — a flow's optional `depends_on_surfaces:` names a route the flow's
             ACs rely on but does not own (reused from another flow/PRD). Same
             resolution as `surfaces:`, but **stricter**: a redirect-only match
             fails the commit too — this is the exact signal a retired-but-undeclared
             UI dependency gave off. Opt-in per flow, so tightening it doesn't
             retroactively break flows that don't declare it.
  ShipCite — an AC tagged `[dev]` (only) that cites a PRD whose frontmatter `status:`
             isn't `shipped`, or one tagged `[ext]` (only) citing a PRD that already
             has, is disposition/citation drift (the tag says one thing, the cited PRD
             says another). The citation is read in every spelling — bare `(NNNN)`,
             `(PRD NNNN)` and the multi-id paren ``(`CAP-1408`, ships in 0655)`` — so a
             cite that used to be invisible no longer is (ENG-12154 class a). Lines
             carrying both tags are an intentional partial disposition and are not checked.
             A `[dev]` AC that defers to the same unshipped PRD it cites ("N/A until PRD
             NNNN ships") is honest and passes; Defer reds it once that PRD ships.
             A tombstone — an AC whose criterion opens struck through, or that carries a
             retire-ack cue in a bold marker — is not a claim and is skipped by ShipCite
             and Defer alike.
   Defer    — an AC that says its criterion is deferred (a `journeys_deferral_cues`
             spelling, e.g. "N/A until PRD NNNN ships") for a PRD whose live
             `status:` is already `shipped` is stale prose, regardless of its tag.
             The deferral must name the PRD it waits on; a dep-only "N/A until <dep>"
             with an owner-PRD suffix is not read as deferring that PRD.
  Index    — every flow/map is listed in the journeys index; every feature map in
             the features index.
   Cover    — exhaustive source_of_truth coverage: every code path under a covered root
             must be claimed by some map's `source_of_truth:` (map-level OR a capability
             row's own `Source of truth` cell), excluded by policy, or named in the
             unclaimed baseline; a map with non-empty `surfaces:` must declare at least
             one frontend path (a row-level frontend path satisfies this too). The gate
             is ABSOLUTE once the baseline is gone (ENG-12738): a missing baseline is
             zero acknowledged debt, never a reason to skip.
  ProsePath — (advisory) a feature map that names a concrete code path in its own prose
             (body, Scope block, capability descriptions, frontmatter comments — not the
             Anchor cell, and not the `source_of_truth:` lines themselves) must have that
             path claimed by *some* map's `source_of_truth:`. Catches the
             grandfathered-baseline blind spot: a map that talks about a file while the
             file sits only in the baseline, so freshness never fires for the map that
             cares. Non-blocking (prose parsing has false-positive risk).
   AcRetired — the reverse (doc -> code) liveness half of the coverage contract. An AC in
              a live flow/map that cites a capability the map explicitly marks retired
              (a `journeys_retirement_markers` spelling: `Ships in: (retired)` /
              `(withdrawn)` / `(superseded)`) is stale prose unless it acknowledges the
              retirement (the annotate-don't-strike convention: "retired"/"withdrawn"/
              "superseded"/a struck `~~` span, `journeys_retire_ack_cues`). A whole flow/map
              marked `status: retired` (or `> **Retired.**`) is a historical record and is
              exempt.
   AcPerm    — every backticked `resource:action` token in an AC whose action verb is in
              the permissions contract's closed action set must resolve to a name in
              `contracts/permissions/permissions.yaml`. Catches a renamed permission the
              corpus still cites (`workspaces:create` after `workspace:create`). Skipped
              when the contract file is absent (a corpus without one).
   AcAbsent  — an AC that asserts a named component is absent ("renders no …", "performs
              no action", …) must not name a testid or PascalCase component the shipped
              frontend tree still mounts. Catches a removal AC left behind after the
              component returned. Skipped when no frontend scan root exists.
   TableShape — every pipe-row in the corpus must sit in a well-formed markdown table
              (header line + `|---|` separator in an unbroken pipe-run). Orphan rows
              render as raw pipe-text and are invisible to readers while (pre-fix) still
              counting as capabilities — refuse both sides.

Every path, id prefix, vocabulary and baseline location below is a config key whose
default is the value this repository already had.

Stdlib only. Exits 1 on any violation.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from ... import corpusref
from ...corpusref import Corpora, find_refs, mask, parse_ref
from ...journeysheet import parse_journey
from ._kit import (
    Finding,
    KnowledgeBase,
    Reporter,
    frontmatter,
    local_kb,
    option,
    option_list,
    option_tuple,
    programs,
    rel_to,
    slices,
)

# --------------------------------------------------------------------------------------
# Defaults — the values this repository already had. Every one is a config key.
# --------------------------------------------------------------------------------------
DEFAULT_JOURNEYS_DIR = "journeys"
DEFAULT_FLOWS_SUBDIR = "flows"
DEFAULT_MAPS_SUBDIR = "maps"
DEFAULT_FEATURES_DIR = "features"
DEFAULT_PRDS_DIR = "prds"
DEFAULT_SPECS_DIR = "specs"
DEFAULT_COMPONENT_REGISTRY = "specs/architecture/components.md"
DEFAULT_CAP_LEDGER = "capability-aliases.md"
DEFAULT_CAP_PREFIX = "CAP"
DEFAULT_CAP_DIGITS = 4
DEFAULT_PROGRAM_REGISTER = "programs.md"

# Fragment-backed feature maps (ENG-12980). A map whose rendered `<area>.md` is a generated,
# gitignored artifact keeps its prose and frontmatter in a committed shell, `<area>.md.tmpl`,
# plus one `features/rows/<CAP-NNNN>.json` per capability row and one
# `features/source_of_truth/<area>/<slug>.json` per claimed `source_of_truth:` path
# (ENG-12782). A reader that globs `*.md` alone sees no map at all on an unrendered checkout,
# so every capability reads as undefined and every claimed path as unclaimed. The layout is
# fixed by the consumer's renderer (`gen_knowledge_fragments`), exactly as `corpus.features`
# and `id_collisions.feature_capability_ids` already read it.
FEATURE_SHELL_SUFFIX = ".md.tmpl"

#: Why a cross-corpus two-way link cannot be checked from a corpus with no name: the sibling
#: would have to name it back with a BARE slug or id, which a same-named document of its own
#: satisfies by coincidence.
_UNNAMED_CORPUS = (
    "this corpus has no name, so the sibling cannot name it back unambiguously — set "
    '`[fleet.planning] corpus = "<name>"` in .fleet/fleet.toml (the lane name)'
)
FEATURE_ROWS_SUBDIR = "rows"
FEATURE_SOT_SUBDIR = "source_of_truth"

DEFAULT_DISPOSITIONS = ("[dev]", "[ext]")  # verification surface, NOT ship-state
# A feature map is a CUSTOMER-recognisable decomposition. Work that is real, owned and
# durable but that no customer would name as a feature ("repo CI", "the service binary's
# config") declares `kind: substrate` so the taxonomy keeps meaning what it says instead
# of becoming a catch-all. Absent = customer-facing, which is the overwhelming default.
DEFAULT_FEATURE_KINDS = ("product", "substrate")
DEFAULT_FEATURE_KIND_DEFAULT = "product"
# ship-state markers — read state from the linked PRD instead
DEFAULT_BANNED_EMOJI = ("🔜", "✅", "❌", "⚠️")

# PRD lifecycle states — the closed set a PRD's frontmatter `status:` is drawn from
# (`knowledge/specs/tracking-and-execution.md`). A map/journey PROSE line that asserts one
# of these of a PRD which has since moved past it (or never reached it) is stale prose:
# four such lines asserted `implementing`/`prd-drafted`/`planned` for PRDs that had already
# shipped, and every validator was green (ENG-17127) because none of them was a `Status`
# column, an AC disposition or a ship-state marker.
DEFAULT_PRD_LIFECYCLE_STATES = (
    "stub",
    "prd-drafted",
    "designed",
    "planned",
    "implementing",
    "verified",
    "shipped",
    "cancelled",
)
# How many word-tokens after a reference a lifecycle word may still be that reference's own
# state; beyond it the word belongs to another clause/reference.
PROSE_STATE_WINDOW = 3
# The backward twin. A leading status word sits at the head of a bold heading and reaches the
# reference across the words that introduce it — `**Planned install journey** — … links
# `install-…` (owning PRD 0518)` puts `Planned` five tokens before the flow reference — so the
# backward window is wider than the forward one while the clause break still bounds it.
PROSE_STATE_BACKWARD_WINDOW = 6
# A backticked journey/flow id on a prose line — the reference shape that names a flow without
# naming its owning PRD (`` `recover-from-a-throttle`, planned ``). It resolves through the
# flow's `owning_prd:` to the PRD whose live `status:` the claim is checked against.
_PROSE_BACKTICK_ID_RE = re.compile(r"`([a-z][a-z0-9-]*)`")

DEFAULT_BASELINE = "knowledge/features/UNCLAIMED.baseline"  # repo-relative
DEFAULT_BASE_REF = "origin/main"

DEFAULT_COVERAGE_ROOTS = (
    "internal/",
    "db/queries/",
    "db/schema.sql",
    "migrations/",
    "frontend/apps/",
    "frontend/libs/",
    "contracts/",
)
# Reviewed carve-outs — a covered path under one of these is exempt by policy, never a
# silent allowance. Tests verify substrate rather than define a feature surface; the
# tooling / CLI / migration / test trees, the generated trees, and vendored or dependency
# code are not feature substrate.
DEFAULT_COVERAGE_EXCLUDED_ROOTS = (
    "internal/tools/",  # a static-analysis suite, not a feature surface
    "cmd/",  # CLI / daemon entry points, not a feature surface
    "scripts/",  # repo tooling
    "tests/",
    "internal/db/",  # generated sqlc output
    "api/gen/",  # generated OpenAPI codegen
)
DEFAULT_COVERAGE_EXCLUDED_SEGMENT = ("/testdata/", "/dist/", "/build/", "/node_modules/")
DEFAULT_COVERAGE_EXCLUDED_LEAF = ("_test.go", "_test.py", ".test.ts", ".test.tsx", ".gen.go", ".gen.ts")
DEFAULT_GEN_LEAF_PATTERN = r"(^|/)(gen_[^/]*\.(go|ts|py)|openapi\.ts)$"
# Top-level spec files that are covered ground without living under a coverage root.
DEFAULT_EXTRA_COVERED_PATTERN = r"api/[^/]+\.yaml"
DEFAULT_EXTRA_COVERED_SCAN = (("api", "*.yaml"),)

# A whole application/package root as `source_of_truth` makes the freshness advisory fire
# on every unrelated change under it — one map claimed the whole of two frontend apps and
# was measured 19-for-19 false-positive over 100 commits. Narrow to what the area actually
# owns, or name the root in `source_of_truth_broad_ok:` as a reviewed exception (never a
# silent allowance).
DEFAULT_BROAD_SOURCE_ROOT_PATTERN = r"^(internal|cmd|frontend)$|^frontend/apps/[^/]+$"
DEFAULT_PROSE_PATH_ROOTS = ("internal", "frontend", "db", "contracts", "api", "migrations", "cmd", "packages", "docs")

# Route resolution (surfaces vs the real frontend router).
DEFAULT_WEB_ROUTES = "frontend/apps/web/src/main.tsx"
DEFAULT_WEB_ROUTES_MARKER = "export const appRoutes = "
DEFAULT_ADMIN_ROUTES = "frontend/apps/admin/src/App.tsx"
DEFAULT_ADMIN_ROUTES_MARKER = "createBrowserRouter("
# Backend/protocol mounts a journey may legitimately cite alongside real UI routes — not
# reachable via browser navigation, so no router entry exists to resolve them against.
DEFAULT_NON_ROUTE_SURFACES = ("/mcp",)
# A surface citation carrying one of these prefixes names something that is not a browser
# route (a REST path, an external product, a CLI), so there is no router entry to resolve
# it against. A project with its own non-route surface vocabulary adds its prefixes here
# rather than teaching the resolver about them.
DEFAULT_SURFACE_SKIP_PREFIXES = ("api:", "external:", "cli:")
DEFAULT_ORG_ROUTE_PREFIX = "/orgs/:orgId"
DEFAULT_REDIRECT_ELEMENTS = ("Navigate", "OrgNavigate")

DEFAULT_WRITE_BASELINE_COMMAND = "python3 scripts/validate_journeys.py --write-baseline"

# Claim-vs-tree legs (ENG-12201). The permissions contract is the closed vocabulary a
# backticked `resource:action` in an AC resolves against; the frontend roots are where a
# testid / PascalCase component an AC claims is absent must not still be mounted.
DEFAULT_PERMISSIONS_CONTRACT = "contracts/permissions/permissions.yaml"
DEFAULT_FRONTEND_SCAN_ROOTS = ("frontend/apps/", "frontend/libs/")
DEFAULT_FRONTEND_SCAN_SUFFIXES = (".tsx", ".ts", ".jsx", ".js")

SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")
PRD_NUM_RE = re.compile(r"\b(\d{4})\b")
AC_LINE_RE = re.compile(r"^(\d+\.\s|-\s+\*\*[A-Z]?\d)")  # `1. …` or `- **A1** …`
STATUS_HEADER_RE = re.compile(r"Tested by\s*\|\s*Status")  # a re-added `Status` column header
# A markdown table separator is pipes/spaces/colons/hyphens only, with >=1 hyphen. Looser
# than strict GFM (3 hyphens/cell) so `| - | --- |` and `|---|:-:|---|` still count as
# intentional separators; the defect we catch is a pipe-run with NO separator at all.
_TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
# Backticked `resource:action` (and multi-segment) tokens — the permission-name shape.
# Only tokens whose final segment is a verb the permissions contract actually uses are
# checked, so `changed:false` / `backend:external` / connector action ids stay prose.
AC_PERMISSION_TOKEN_RE = re.compile(r"`([a-z][a-z0-9_]*(?::[a-z][a-z0-9_]+)+)`")
# An AC that asserts absence of a named surface. The identifiers it names (testid /
# PascalCase component) are then required not to be mounted in the shipped frontend.
AC_ABSENCE_RE = re.compile(
    r"\brenders?\s+no\b|\bdoes\s+not\s+render\b|\bdoesn't\s+render\b|"
    r"\bis\s+absent\b|\bare\s+absent\b|\bnot\s+mounted\b|\bnever\s+mounts\b|"
    r"\bperforms?\s+no\s+action\b|\bdoes\s+nothing\b|\bnot-yet-built\b",
    re.IGNORECASE,
)
# Kebab-case testid in backticks (at least one hyphen — distinguishes from a bare slug).
AC_TESTID_RE = re.compile(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`")
# PascalCase React component name (≥2 humps so `JSON`/`URL`/`CAP` stay out).
AC_COMPONENT_NAME_RE = re.compile(r"\b([A-Z][a-z0-9]+(?:[A-Z][a-zA-Z0-9]+)+)\b")
# data-testid literals and the static prefix of a template literal before `${…}`.
_DATA_TESTID_LIT_RE = re.compile(r"""data-testid\s*=\s*(?:\{\s*)?(?:["'])([^"'${}]+)(?:["'])""")
_DATA_TESTID_TMPL_RE = re.compile(r"""data-testid\s*=\s*\{\s*`([^`$]*?)\$\{""")
# JSX use of a PascalCase component (`<NeedsYouSummary` / `<NeedsYouSummary/>`).
_JSX_COMPONENT_RE = re.compile(r"<(?!/)([A-Z][A-Za-z0-9]*)\b")
# An AC's inline PRD citation. The corpus spells one at least three ways — a bare
# `(NNNN)`, a `(PRD NNNN)`, and a multi-id paren such as ``(`CAP-1408`, ships in 0655)``
# — and the old bare-4-digit matcher saw only the first, so half the citations were
# invisible to the disposition/ship-state cross-check (ENG-12154 class a). A citation is
# a parenthesised run that is itself a bare number or names a PRD/capability/ship target;
# a number glued to `#`/`/`/`-`/`:` (issue and PR numbers, date fragments, `CAP-1408`,
# `ENG-4338`) is never read as one.
AC_CITE_PAREN_RE = re.compile(r"\(([^()]*)\)")
# The number and disposition tags an AC entry opens with (`13. `[ext]` `, `- **A6** `[dev]` `),
# stripped to find where the criterion itself starts (a tombstone opens with `~~`).
_AC_TOMBSTONE_LEAD_RE = re.compile(r"^(?:[-*]\s+)?(?:\*\*[^*]+\*\*\s+|\d+[a-z]?\.\s+)?(?:`\[[a-z]+\]`\s*)*")
_BOLD_SPAN_RE = re.compile(r"\*\*(.+?)\*\*", re.S)
AC_PRD_NUM_RE = re.compile(r"(?<![\w#:/-])(\d{4})(?![\w#:/-])")
AC_CITE_MARKER_RE = re.compile(r"\bships?\s+in\b|\bPRD\b|CAP-\d{4}", re.IGNORECASE)
_AC_BARE_NUM_RE = re.compile(r"\s*\d{4}\s*")
# A map/journey PROSE PRD reference. Three spellings the corpus uses: the explicit
# `PRD NNNN`, the parenthesised `(NNNN)`/`(PRD NNNN)`/multi-id citation the AC reader
# already understands (so a `CAP-NNNN`, an issue key or a date fragment is never one), and
# the corpus's bold `**NNNN**` pointer (106× under `knowledge/features` + `knowledge/journeys`,
# e.g. `*owned by **0149** (Org-Scoped Groups …, prd-drafted):*` — the shape of one of the
# four stale lines ENG-17127 fixed).
PROSE_PRD_TAG_RE = re.compile(r"\bPRD\s+(\d{4})\b", re.IGNORECASE)
_PROSE_PRD_BOLD_RE = re.compile(r"\*\*(\d{4})\*\*")
# A word token — a lifecycle word is matched as a standalone token, never a substring.
_PROSE_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]*")
# Words that introduce a lifecycle word as a MODIFIER of another noun rather than a claim
# about the PRD's own state: an article ("the implementing run"), a possessive
# ("PRD 0590's implementing run" — the run that implemented), or a relative pronoun
# ("(0194) that shipped and was then removed" — an event in the PRD's history). A claim
# reads "… is implementing" / "… now implementing".
_PROSE_STATE_MODIFIERS = frozenset({"the", "a", "an", "that", "which", "who", "whose", "whom"})
# A trailing possessive on the token before a lifecycle word (`…'s implementing run`).
_PROSE_STATE_POSSESSIVE_RE = re.compile(r"['\u2019]s$")
# A sentence/clause break between the reference and the word ends the window: the word is
# then some other clause's, not this reference's state.
_PROSE_CLAUSE_BREAK_RE = re.compile(r"[.;!?]")
# A parenthesised prose note — history, rationale, "(The state this AC named was cut with
# PRD 0157's cancellation. Not re-added here.)" — is not a citation of the criterion's own
# PRD. It is recognised narrowly: the paren OPENS as a sentence (a capitalised word that is
# not itself a citation marker — `PRD`, `Ships in`, `CAP-`) and holds a sentence break.
# `(PRD 0200. Owns this.)` and `(ships in 0200, vs. The old path)` stay citations. A note
# still has to resolve (the dangling-citation leg reads notes too); only its PRD's
# ship-state is not compared with the criterion's disposition tag.
_AC_PROSE_NOTE_OPEN_RE = re.compile(r"[A-Z][a-z]+\b")
_AC_PROSE_NOTE_BREAK_RE = re.compile(r"[.!?]\s+[A-Z]")
# A component named only as a test/story file (`ExplorePage.test.tsx`) is a pointer at a
# pin, not a claim about what the tree mounts; it is dropped before the absence leg reads
# component names.
_AC_TEST_FILENAME_RE = re.compile(r"\b[A-Z][A-Za-z0-9]*(?:\.[A-Za-z0-9_-]+)*\.(?:test|spec|stories)\.[cm]?[jt]sx?\b")
# The acceptance-criteria heading is not always the exact string. The corpus uses three
# spellings — `## Acceptance criteria`, `## Acceptance criteria (→ PRD NNNN)` and
# `## Interaction-level acceptance criteria` — and a variant heading's rows reached no
# check at all because the match was exact (ENG-12154 class e). This matches any `##`
# heading that names "Acceptance criteria"; the hyphenated prose headings (`## The
# acceptance-criteria contract`) deliberately do not match.
DEFAULT_AC_HEADING_PATTERN = r"^##\s+[^\n]*[Aa]cceptance criteria\b[^\n]*$"
# Deferral spellings — an AC that says its criterion is not yet exercisable. The
# disposition is resolved against the cited PRD's live frontmatter `status:`, so a
# deferral of a PRD that has already shipped is stale (ENG-12154 class a).
DEFAULT_DEFERRAL_CUES = (
    "N/A until",
    "N/A(not shipped)",
    "N/A (not shipped)",
    "not yet shipped",
    "not yet built",
    "deferred until",
    "blocked until",
)
# Capability retirement markers (a row's `Ships in` cell). `(retired)` is the
# long-standing spelling; the others are accepted so a retirement cannot be spelled
# unrecognisably and slip past the liveness check.
DEFAULT_RETIREMENT_MARKERS = ("(retired)", "(withdrawn)", "(superseded)")
# An AC acknowledges a retirement with one of these — the annotate-don't-strike
# convention (`retired` / `withdrawn` / `superseded` / a struck `~~` span).
DEFAULT_RETIRE_ACK_CUES = ("retired", "withdrawn", "superseded", "~~")
ROUTE_PATH_RE = re.compile(r'path:\s*"([^"]*)"')
ROUTE_ELEMENT_RE = re.compile(r"element:\s*\(?\s*<\s*([A-Za-z][\w.]*)")
# An UNREGISTERED `<word>: /path` surface citation (ENG-10175): some prefix the resolver
# was never taught, followed by a path-shaped remainder. Refused rather than skipped —
# `web: ` shipped green through exactly this silence. A remainder starting `//` is a URL
# authority (`https://host/x`), not a route, and skips as before.
_SURFACE_PREFIXED_PATH_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(/.+)$")
UNVERIFIED = "UNVERIFIED"

# Bare leaf filename: PascalCase.tsx/.ts or snake_case.go. Resolved only when exactly
# one covered-root file carries that leaf — ambiguous basenames (test.tsx) are ignored.
PROSE_BARE_LEAF_RE = re.compile(
    r"(?<![`/\w.-])"
    r"([A-Z][A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*\.(?:tsx|ts)|[a-z][a-z0-9_]+\.go)"
    r"(?![\w/.-])"
)


# --------------------------------------------------------------------------------------
# Markdown table helpers (pure)
# --------------------------------------------------------------------------------------
def is_pipe_line(line: str) -> bool:
    """A line that looks like a markdown table row (leading `|`, >=2 pipes)."""
    s = line.lstrip()
    return s.startswith("|") and s.count("|") >= 2


def is_table_separator(line: str) -> bool:
    """True if `line` is an intentional markdown table separator row."""
    s = line.strip()
    return bool(_TABLE_SEP_RE.fullmatch(s)) and "-" in s


def iter_md_body_lines(text: str) -> list[tuple[int, str]]:
    """(1-based lineno, line) pairs outside YAML frontmatter, fenced code, HTML comments."""
    lines = text.splitlines()
    out: list[tuple[int, str]] = []
    i = 0
    n = len(lines)
    if lines and lines[0].strip() == "---":
        i = 1
        while i < n and lines[i].strip() != "---":
            i += 1
        if i < n:
            i += 1
    in_fence = False
    in_comment = False
    while i < n:
        line = lines[i]
        ln = i + 1
        if not in_comment and line.lstrip().startswith("```"):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence:
            i += 1
            continue
        if "<!--" in line and "-->" not in line:
            in_comment = True
            i += 1
            continue
        if in_comment:
            if "-->" in line:
                in_comment = False
            i += 1
            continue
        out.append((ln, line))
        i += 1
    return out


def pipe_runs(text: str) -> list[list[tuple[int, str]]]:
    """Unbroken runs of pipe-lines in the markdown body (the table-shape context)."""
    runs: list[list[tuple[int, str]]] = []
    cur: list[tuple[int, str]] = []
    for ln, line in iter_md_body_lines(text):
        if is_pipe_line(line):
            cur.append((ln, line))
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return runs


def is_valid_table_run(run: list[tuple[int, str]]) -> bool:
    """A pipe-run is a real table iff it begins with a header line + separator."""
    return len(run) >= 2 and not is_table_separator(run[0][1]) and is_table_separator(run[1][1])


# ── Acceptance-criteria TABLES (class fix for ENG-18302) ────────────────────────────────
# A flow may write its ACs as a markdown table (`| # | Criterion | Disposition |`) rather
# than a numbered/bulleted list. `AC_LINE_RE` matches none of those rows, so before this the
# whole table landed in `loose` and the disposition/ship-state cross-check ran over zero
# blocks — every row was invisible. Only a table whose header NAMES a Disposition column is
# an AC table; every other pipe-run (an interaction matrix, a findings registry) keeps its
# old `loose` treatment.
_TABLE_TAG_RE = re.compile(r"\[([a-z]+)\]", re.IGNORECASE)
_TABLE_BARE_TAG_RE = re.compile(r"\b(dev|ext)\b", re.IGNORECASE)


def split_table_row(line: str) -> list[str]:
    """The cells of a markdown pipe-row, stripped, with the outer pipes removed."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _normalize_table_header(cell: str) -> str:
    """A header cell reduced to its bare name — emphasis, backticks and case removed."""
    return re.sub(r"[`*_]", "", cell).strip().lower()


def _disposition_column(header_cells: list[str]) -> int | None:
    """Index of the `Disposition` column if this header row is an AC table, else None.

    The Disposition column is what distinguishes an acceptance-criteria table from the
    corpus's many other tables; absent it the rows are not ACs and must not be read as
    claims."""
    for j, cell in enumerate(header_cells):
        if _normalize_table_header(cell) in ("disposition", "dispositions"):
            return j
    return None


def _disposition_tags(cell: str) -> list[str]:
    """The `[dev]`/`[ext]` tag(s) a table's Disposition cell names, bracketed or bare."""
    tags = [m.group(0).lower() for m in _TABLE_TAG_RE.finditer(cell)]
    if tags:
        return tags
    return [f"[{m.group(1).lower()}]" for m in _TABLE_BARE_TAG_RE.finditer(cell)]


def _ac_table_block(cells: list[str], disp_idx: int) -> str:
    """One AC-table data row as a criterion block: every cell but Disposition, then the tag.

    The criterion cell(s) carry the text and any PRD citation; the Disposition cell is
    mapped to its `[dev]`/`[ext]` tag, so the same downstream legs that read a numbered AC
    (citation resolution, disposition/ship-state, deferral, permissions) read a table row."""
    criterion = " ".join(c for j, c in enumerate(cells) if j != disp_idx and c)
    tags = " ".join(_disposition_tags(cells[disp_idx] if disp_idx < len(cells) else ""))
    return f"{criterion} {tags}".strip()


def ac_table_blocks(lines: list[str]) -> list[str]:
    """Every acceptance-criteria table data row in `lines`, as a criterion block.

    A table is an AC table iff its header names a Disposition column; its data rows are then
    one AC entry each. The disposition-presence gate and the cross-check both read this."""
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        if is_pipe_line(lines[i]) and i + 1 < n and is_table_separator(lines[i + 1]):
            disp_idx = _disposition_column(split_table_row(lines[i]))
            if disp_idx is not None:
                j = i + 2
                while j < n and is_pipe_line(lines[j]):
                    out.append(_ac_table_block(split_table_row(lines[j]), disp_idx))
                    j += 1
                i = j
                continue
        i += 1
    return out


def field(fm: str, name: str) -> str | None:
    m = re.search(rf"^{name}:\s*(.+)$", fm, re.M)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'") or None


def listfield(fm: str, name: str) -> list[str]:
    """A frontmatter list, inline (`name: [a, b]`) or block (`name:` then `  - a` lines).

    Both spellings on purpose (ENG-14299): a feature map's `source_of_truth` is now a block
    list, one path per line, sorted — the form that stops two concurrent PRs adding
    different paths from rewriting the one shared line. The inline form is still read so a
    mid-flight branch or an un-migrated file does not silently claim nothing.
    """
    inline = re.search(rf"^{name}:[ \t]*\[(.*?)\]", fm, re.M | re.S)
    if inline:
        return [x.strip().strip('"').strip("'") for x in inline.group(1).split(",") if x.strip()]
    block = re.search(rf"^{name}:[ \t]*$((?:\n[ \t]+-[^\n]*)*)", fm, re.M)
    if not block:
        return []
    return [
        re.sub(r"^[ \t]+-[ \t]*", "", line).strip().strip('"').strip("'")
        for line in block.group(1).splitlines()
        if line.strip()
    ]


def has_field(fm: str, name: str) -> bool:
    """True if the frontmatter declares `name:` at all (empty list included)."""
    return re.search(rf"^{name}:", fm, re.M) is not None


def ac_sections(body: str, heading_re: re.Pattern[str]) -> list[str]:
    """Lines under EVERY acceptance-criteria heading, each up to the next '## ' heading.

    A journey may open more than one AC section — the canonical `## Acceptance criteria`
    plus a variant such as `## Acceptance criteria — <context> (NNNN)` or
    `## Interaction-level acceptance criteria`. The old exact match read only the first,
    so a variant section's rows reached no check at all (ENG-12154 class e); every
    matching section is returned here.
    """
    out: list[str] = []
    for m in heading_re.finditer(body):
        rest = body[m.end() :]
        stop = re.search(r"^##\s", rest, re.M)
        out.extend((rest[: stop.start()] if stop else rest).splitlines())
    return out


def _is_prose_note(inner: str) -> bool:
    """A parenthetical that opens as a sentence and holds a sentence break — see above."""
    body = inner.strip()
    return (
        bool(_AC_PROSE_NOTE_OPEN_RE.match(body))
        and not AC_CITE_MARKER_RE.match(body)
        and bool(_AC_PROSE_NOTE_BREAK_RE.search(body))
    )


def ac_prd_cites(text: str, *, include_notes: bool = False) -> list[str]:
    """Every PRD number an AC block cites in a parenthesised citation.

    Reads the multi-id spelling (`(`CAP-1408`, ships in 0655)`), `(PRD NNNN)` and the
    bare `(NNNN)` alike, while never reading a number glued to an id/path marker
    (`#8821`, `ENG-4338`, `CAP-1408`, a date fragment). See `AC_CITE_PAREN_RE`.

    A parenthesised prose note (it holds a sentence break) is skipped unless
    `include_notes` — a PRD named in a note must still resolve, but it is not the
    criterion's own PRD, so its ship-state is not compared with the disposition tag.
    """
    out: list[str] = []
    for m in AC_CITE_PAREN_RE.finditer(text):
        inner = m.group(1)
        nums = AC_PRD_NUM_RE.findall(inner)
        if not nums:
            continue
        if not include_notes and _is_prose_note(inner):
            continue
        if _AC_BARE_NUM_RE.fullmatch(inner) or AC_CITE_MARKER_RE.search(inner):
            out.extend(nums)
    return out


def ac_qualified_cites(
    text: str, *, include_notes: bool = False, known: frozenset[str] | set[str] | None = None
) -> list[corpusref.Ref]:
    """Every repo-qualified PRD (`fleet:0899`) an AC block cites in a parenthesised citation.

    The same parens `ac_prd_cites` reads — a bare `(fleet:0899)`, or one carrying a citation
    marker (`(PRD fleet:0899)`, `(ships in fleet:0899)`). `known` limits the corpus names read,
    because a parenthesised `(localhost:8000)` has the same shape as a citation.
    """
    out: list[corpusref.Ref] = []
    for m in AC_CITE_PAREN_RE.finditer(text):
        inner = m.group(1)
        refs = [r for r, _s, _e in find_refs(inner, known=known) if r.id.isdigit() and len(r.id) == 4]
        if not refs:
            continue
        if not include_notes and _is_prose_note(inner):
            continue
        if parse_ref(inner).qualified or AC_CITE_MARKER_RE.search(inner):
            out.extend(refs)
    return out


def _ends_ac_block(line: str) -> bool:
    """A column-0 table row, heading or blockquote is never part of a numbered AC entry.

    Only column 0: under a list item an INDENTED `>` / `|` / `#` is still that item's
    content (markdown list rules), so an indented amendment blockquote stays with its
    criterion — and a claim written inside one is still read.
    """
    return line.startswith(("|", "#", ">"))


def ac_partition(lines: list[str]) -> tuple[list[str], list[str]]:
    """Split AC-section lines into (numbered blocks, loose units).

    A numbered block is one AC entry's (often soft-wrapped) lines joined — an inline
    `(NNNN)` PRD citation frequently lands on a continuation line, not the bullet's own
    first line. It ENDS where the entry does: at the next `AC_LINE_RE` bullet, at a
    column-0 table row, heading or blockquote, and at a blank line unless an indented
    continuation of the same list item follows. Without that bound the last numbered AC
    swallowed everything after it — a whole `## Interaction-level acceptance criteria`
    table section, or the next `### … (PRD NNNN)` heading — and one absence cue or PRD
    citation anywhere in it was charged to that criterion.

    Everything else in the section is a loose unit — each non-AC table row and heading on
    its own, each other paragraph joined — so the legs that do not need to know which
    criterion a line belongs to (does this citation resolve? is this capability
    retired?) still read every line of every AC section.

    A table whose header names a `Disposition` column is a table-form AC section: each data
    row is one entry and joins `blocks` (class fix, ENG-18302). Every other table keeps the
    old per-row `loose` treatment.
    """
    blocks: list[str] = []
    loose: list[str] = []
    cur: list[str] | None = None
    para: list[str] = []
    after_blank = False

    def flush_para() -> None:
        if para:
            loose.append(" ".join(para))
            para.clear()

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        # An AC table: header names a Disposition column. Its data rows are entries, so they
        # join `blocks`, not `loose` — the cross-check and disposition gate then read them.
        if is_pipe_line(line) and i + 1 < n and is_table_separator(lines[i + 1]):
            disp_idx = _disposition_column(split_table_row(line))
            if disp_idx is not None:
                flush_para()
                if cur is not None:
                    blocks.append(" ".join(cur))
                    cur = None
                i += 2
                while i < n and is_pipe_line(lines[i]):
                    blocks.append(_ac_table_block(split_table_row(lines[i]), disp_idx))
                    i += 1
                after_blank = False
                continue
        i += 1
        if AC_LINE_RE.match(line):
            flush_para()
            if cur is not None:
                blocks.append(" ".join(cur))
            cur = [line]
            after_blank = False
            continue
        if cur is not None:
            if not line.strip():
                after_blank = True
                continue
            if not (_ends_ac_block(line) or (after_blank and not line[:1].isspace())):
                cur.append(line)
                after_blank = False
                continue
            blocks.append(" ".join(cur))
            cur = None
            after_blank = False
        if not line.strip():
            flush_para()
        elif line.lstrip().startswith(("|", "#")):
            flush_para()
            loose.append(line)
        else:
            para.append(line)
    if cur is not None:
        blocks.append(" ".join(cur))
    flush_para()
    return blocks, loose


def ac_blocks(lines: list[str]) -> list[str]:
    """The numbered AC entries of `ac_partition` — see there for where a block ends."""
    return ac_partition(lines)[0]


def _route_array_text(path: Path, marker: str) -> str | None:
    """Raw source of the `[...]` route-array literal following `marker`."""
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if marker not in text:
        return None
    start = text.index("[", text.index(marker))
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "[":
            depth += 1
        elif text[j] == "]":
            depth -= 1
            if depth == 0:
                return text[start : j + 1]
    return None


def _flatten_routes(
    array_text: str, redirect_elements: Sequence[str] = DEFAULT_REDIRECT_ELEMENTS
) -> list[tuple[str, bool]]:
    """(absolute_path, is_redirect) for every route object with its own literal
    `path:`, walking the router array by brace depth. Not a real JS parser — just
    enough to flatten a fixed, hand-authored route table (nested absolute + relative
    `path:`, index routes, redirect elements).
    """
    frames: list[dict[str, Any]] = []
    out: list[tuple[str, bool]] = []
    i, n = 0, len(array_text)
    while i < n:
        c = array_text[i]
        if c == "{":
            frames.append({"abs": None, "redirect": False})
            i += 1
        elif c == "}":
            if frames:
                frame = frames.pop()
                if frame["abs"] is not None:
                    out.append((frame["abs"], frame["redirect"]))
            i += 1
        elif frames and array_text.startswith("path:", i) and (m := ROUTE_PATH_RE.match(array_text, i)):
            literal = m.group(1)
            frame = frames[-1]
            if literal.startswith("/"):
                frame["abs"] = literal
            else:
                parent = next((f["abs"] for f in reversed(frames[:-1]) if f["abs"]), "")
                frame["abs"] = f"{parent.rstrip('/')}/{literal}"
            i = m.end()
        elif frames and array_text.startswith("element:", i) and (m := ROUTE_ELEMENT_RE.match(array_text, i)):
            name = m.group(1)
            frames[-1]["redirect"] = name in redirect_elements or "redirect" in name.lower()
            i = m.end()
        else:
            i += 1
    return out


def _path_segments(p: str) -> list[str]:
    return [s for s in p.split("/") if s]


#: The PRD statuses that mean code exists or is being written for the row that cites the PRD.
_BUILT_STATUSES: Final = frozenset({"implementing", "verified", "shipped"})
#: A cell that cites nothing: a gap.
_GAP_CELLS: Final = frozenset({"", "—", "-", "–"})


def _no_code_yet(fmap: Mapping[str, Any], prd_status: Mapping[str, str]) -> bool:
    """Whether no capability row of this map cites built work: every `Ships in` is a gap or names only PRDs that are
    not being built or shipped. A cell carrying anything but PRD numbers (`(core)`, a retirement marker) is built."""
    for info in (fmap.get("caps") or {}).values():
        cell = str(info.get("ships") or "").strip()
        if cell in _GAP_CELLS:
            continue
        nums = re.findall(r"\b\d{4}\b", cell)
        rest = re.sub(r"\b\d{4}\b|[,\s]", "", cell)
        if rest or not nums or any(prd_status.get(n, "") in _BUILT_STATUSES for n in nums):
            return False
    return True


def _parse_row_source_of_truth(cell: str) -> list[str]:
    """A row-level `Source of truth` cell: comma-separated code paths, each optionally
    backtick-wrapped. `—`/`-`/empty means the row makes no independent claim — it falls
    back to the map-level `source_of_truth:` list, same as before this column existed."""
    out: list[str] = []
    for p in cell.split(","):
        p = p.strip().strip("`")
        if p and p not in ("—", "-"):
            out.append(p)
    return out


def load_permission_names(path: Path) -> set[str]:
    """Permission names from a `permissions.yaml`-shaped contract (stdlib, no PyYAML).

    The file is an ordered map under a top-level `permissions:` key; each permission is a
    2-space-indented `resource:action:` key. Nested fields sit at 4+ spaces and are ignored.
    A missing or unreadable file yields an empty set — the caller treats that as "no
    contract, skip the leg" rather than "every name is unknown"."""
    if not path.is_file():
        return set()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return set()
    names: set[str] = set()
    in_perms = False
    for line in text.splitlines():
        if re.match(r"^permissions:\s*(?:#.*)?$", line):
            in_perms = True
            continue
        if not in_perms:
            continue
        if line and not line[0].isspace() and not line.lstrip().startswith("#"):
            # Next top-level key ends the map (or a second `permissions:` restarts it).
            if re.match(r"^permissions:\s*(?:#.*)?$", line):
                continue
            in_perms = False
            continue
        m = re.match(r"^  ([a-z][a-z0-9_]*(?::[a-z][a-z0-9_]*)+)\s*:", line)
        if m:
            names.add(m.group(1))
    return names


def _testid_is_mounted(cited: str, mounted: set[str]) -> bool:
    """True when `cited` is a mounted testid or the static prefix of one (template ids)."""
    if cited in mounted:
        return True
    prefix = cited if cited.endswith("-") else cited + "-"
    return any(m.startswith(prefix) or (m.endswith("-") and cited.startswith(m)) for m in mounted)


def scan_frontend_mounts(repo: Path, roots: Sequence[str], suffixes: Sequence[str]) -> tuple[set[str], set[str]]:
    """({mounted testid literals/prefixes}, {PascalCase components used in JSX}) under roots."""
    testids: set[str] = set()
    components: set[str] = set()
    suf = tuple(suffixes)
    for root_rel in roots:
        base = repo / root_rel.rstrip("/")
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in suf:
                continue
            # Skip tests/stories — a testid only asserted in a test is not "mounted".
            name = path.name
            if (
                name.endswith((".test.ts", ".test.tsx", ".test.js", ".test.jsx"))
                or name.endswith((".spec.ts", ".spec.tsx", ".stories.ts", ".stories.tsx"))
                or "/__tests__/" in path.as_posix()
                or "/__mocks__/" in path.as_posix()
            ):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            testids.update(_DATA_TESTID_LIT_RE.findall(text))
            testids.update(_DATA_TESTID_TMPL_RE.findall(text))
            components.update(_JSX_COMPONENT_RE.findall(text))
    return testids, components


#: The customer docs page that defines the journey file layout; named in the section errors.
JOURNEY_DOCS_PAGE: Final = "knowledge-base/journeys"


class JourneysValidator:
    """The ported `validate_journeys` run, bound to one knowledge base."""

    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb
        self.repo: Path = kb.root
        self.k: Path = kb.knowledge
        self.report = Reporter(base=self.repo)

        self.journeys_dir: str = option(kb, "journeys_dir", DEFAULT_JOURNEYS_DIR)
        self.flows_subdir: str = option(kb, "journeys_flows_subdir", DEFAULT_FLOWS_SUBDIR)
        self.maps_subdir: str = option(kb, "journeys_maps_subdir", DEFAULT_MAPS_SUBDIR)
        self.features_dir: str = option(kb, "features_dir", DEFAULT_FEATURES_DIR)
        self.prds_dir: str = option(kb, "prds_dir", DEFAULT_PRDS_DIR)
        self.specs_dir: str = option(kb, "specs_dir", DEFAULT_SPECS_DIR)
        self.component_registry: str = option(kb, "components_registry", DEFAULT_COMPONENT_REGISTRY)
        self.cap_ledger: str = option(kb, "capability_aliases", DEFAULT_CAP_LEDGER)

        # A capability id is OPAQUE, GLOBAL and PERMANENT: one flat namespace across every
        # feature map. It encodes nothing — which area a capability belongs to is *which
        # file its row is in*, and nothing else. An area-prefixed id means a capability
        # cannot MOVE between areas without being renamed, and renaming it breaks every
        # `covers:`, `Needs` edge and PRD citation pointing at it.
        prefix: str = option(kb, "capability_prefix", DEFAULT_CAP_PREFIX)
        digits = int(option(kb, "capability_id_digits", DEFAULT_CAP_DIGITS))
        self.cap_prefix = prefix
        self.cap_digits = digits
        self.cap_id_re = re.compile(rf"^{re.escape(prefix)}-\d{{{digits}}}$")
        self.cap_ref_re = re.compile(rf"{re.escape(prefix)}-\d{{{digits}}}")
        self.program_register: Path = self.k / str(option(kb, "programs_register", DEFAULT_PROGRAM_REGISTER))
        # Repo-qualified references (`fleet:0899`, `fleet:CAP-1408`): resolved against the
        # corpus they name, never this one's (`fleet_knowledge.corpusref`).
        self.corpora = Corpora.of(kb)

        self.dispositions = option_tuple(kb, "journeys_dispositions", DEFAULT_DISPOSITIONS)
        self.feature_kinds = option_tuple(kb, "feature_kinds", DEFAULT_FEATURE_KINDS)
        self.feature_kind_default: str = option(kb, "feature_kind_default", DEFAULT_FEATURE_KIND_DEFAULT)
        self.banned_emoji = option_tuple(kb, "journeys_banned_markers", DEFAULT_BANNED_EMOJI)
        self.prd_lifecycle_states = option_tuple(kb, "journeys_prd_lifecycle_states", DEFAULT_PRD_LIFECYCLE_STATES)
        self._lifecycle_set = {s.strip().lower() for s in self.prd_lifecycle_states if s.strip()}

        # The truth half of the AC contract: every spelling of the AC heading is parsed,
        # a deferral is resolved against the cited PRD's live `status:`, and a capability
        # retirement is spelled with a configured marker (ENG-12154 / ENG-12173).
        self.ac_heading_re = re.compile(
            str(option(kb, "journeys_ac_heading_pattern", DEFAULT_AC_HEADING_PATTERN)), re.M
        )
        self.deferral_cues = option_tuple(kb, "journeys_deferral_cues", DEFAULT_DEFERRAL_CUES)
        # A deferral is only read as such when it names the PRD it waits on — either
        # `N/A until PRD NNNN ships` or `… (PRD NNNN)`. An `— N/A until <dep>` row that
        # appends an owner PRD without a `PRD`/`ships` marker is not a deferral of that PRD.
        cue_alt = "|".join(re.escape(c) for c in self.deferral_cues)
        self.deferral_prd_re = (
            re.compile(
                rf"(?:{cue_alt})[^.\n]{{0,80}}?(?:PRD\s+(\d{{4}})|(\d{{4}})\s+ships)",
                re.IGNORECASE,
            )
            if self.deferral_cues
            else None
        )
        self.retirement_markers = option_tuple(kb, "journeys_retirement_markers", DEFAULT_RETIREMENT_MARKERS)
        ack_alt = "|".join(re.escape(c) for c in option_tuple(kb, "journeys_retire_ack_cues", DEFAULT_RETIRE_ACK_CUES))
        self.retire_ack_re = re.compile(ack_alt, re.IGNORECASE) if ack_alt else None

        self.baseline_rel: str = option(kb, "journeys_unclaimed_baseline", DEFAULT_BASELINE)
        self.base_ref: str = option(kb, "journeys_base_ref", DEFAULT_BASE_REF)

        self.coverage_roots = option_tuple(kb, "coverage_roots", DEFAULT_COVERAGE_ROOTS)
        self.coverage_excluded_roots = option_tuple(kb, "coverage_excluded_roots", DEFAULT_COVERAGE_EXCLUDED_ROOTS)
        self.coverage_excluded_segment = option_tuple(
            kb, "coverage_excluded_segments", DEFAULT_COVERAGE_EXCLUDED_SEGMENT
        )
        self.coverage_excluded_leaf = option_tuple(kb, "coverage_excluded_leaves", DEFAULT_COVERAGE_EXCLUDED_LEAF)
        self.gen_leaf_re = re.compile(str(option(kb, "coverage_generated_leaf_pattern", DEFAULT_GEN_LEAF_PATTERN)))
        self.extra_covered_re = re.compile(str(option(kb, "coverage_extra_pattern", DEFAULT_EXTRA_COVERED_PATTERN)))
        self.extra_covered_scan = [
            (str(d), str(g)) for d, g in option(kb, "coverage_extra_scan", DEFAULT_EXTRA_COVERED_SCAN)
        ]
        self.broad_source_root_re = re.compile(
            str(option(kb, "journeys_broad_source_root_pattern", DEFAULT_BROAD_SOURCE_ROOT_PATTERN))
        )
        prose_roots = option_list(kb, "journeys_prose_path_roots", DEFAULT_PROSE_PATH_ROOTS)
        # Repo-relative path under a known root, optional :symbol, optional backticks. The
        # lookbehind keeps `foo/bar.go` from matching inside a longer path already captured.
        self.prose_path_re = re.compile(
            r"(?<![A-Za-z0-9_./-])"
            r"((?:" + "|".join(re.escape(r) for r in prose_roots) + r")/"
            r"[A-Za-z0-9_./-]+?\.(?:tsx?|go|py|sql|ya?ml|md|json))"
            r"(?::[A-Za-z0-9_.]+)?"
        )

        self.web_main = self.repo / str(option(kb, "journeys_web_routes", DEFAULT_WEB_ROUTES))
        self.web_marker: str = option(kb, "journeys_web_routes_marker", DEFAULT_WEB_ROUTES_MARKER)
        self.admin_app = self.repo / str(option(kb, "journeys_admin_routes", DEFAULT_ADMIN_ROUTES))
        self.admin_marker: str = option(kb, "journeys_admin_routes_marker", DEFAULT_ADMIN_ROUTES_MARKER)
        self.non_route_surfaces = set(option_list(kb, "journeys_non_route_surfaces", DEFAULT_NON_ROUTE_SURFACES))
        self.surface_skip_prefixes = option_tuple(kb, "journeys_surface_skip_prefixes", DEFAULT_SURFACE_SKIP_PREFIXES)
        self.org_route_prefix: str = option(kb, "journeys_org_route_prefix", DEFAULT_ORG_ROUTE_PREFIX)
        self.redirect_elements = option_tuple(kb, "journeys_redirect_elements", DEFAULT_REDIRECT_ELEMENTS)

        self.write_baseline_command: str = option(kb, "journeys_write_baseline_command", DEFAULT_WRITE_BASELINE_COMMAND)

        self.permissions_contract = self.repo / str(
            option(kb, "journeys_permissions_contract", DEFAULT_PERMISSIONS_CONTRACT)
        )
        self.frontend_scan_roots = option_tuple(kb, "journeys_frontend_scan_roots", DEFAULT_FRONTEND_SCAN_ROOTS)
        self.frontend_scan_suffixes = option_tuple(
            kb, "journeys_frontend_scan_suffixes", DEFAULT_FRONTEND_SCAN_SUFFIXES
        )

        self._components: set[str] | None = None
        self._permission_names: set[str] | None = None
        self._permission_actions: set[str] | None = None
        self._frontend_testids: set[str] | None = None
        self._frontend_components: set[str] | None = None
        self._merge_base: str | None = None
        self._merge_base_read = False
        self.counts: dict[str, int] = {}
        self.orphans: list[str] = []

    # -- reporting ----------------------------------------------------------------
    def err(self, path: Path, msg: str, **kw: Any) -> None:
        self.report.err(path, msg, **kw)

    def note(self, path: Path, msg: str, **kw: Any) -> None:
        self.report.note(path, msg, **kw)

    def _deferral_cites(self, block: str) -> list[str]:
        """The PRD numbers an AC block says it is deferred until (`N/A until PRD NNNN ships`)."""
        if self.deferral_prd_re is None:
            return []
        return [m.group(1) or m.group(2) for m in self.deferral_prd_re.finditer(block)]

    def _ac_cites(self, path: Path, block: str, *, include_notes: bool = False, resolve: bool = False) -> list[str]:
        """The LOCAL PRD numbers an AC block cites, own-qualified ones (`acme:0899`) included.

        A citation qualified with ANOTHER corpus (`(fleet:0899)`) used to vanish without a
        word — the bare-number reader refuses a number glued to `:`. With `resolve`, each one is
        resolved against the corpus it names (a miss or an undeclared corpus is an error); its
        ship-state is then compared with the disposition tag exactly as a local one's is.
        """
        out = ac_prd_cites(block, include_notes=include_notes)
        for ref in ac_qualified_cites(block, include_notes=include_notes, known=self.corpora.names):
            if self.corpora.is_local(ref):
                out.append(ref.id)
            elif resolve:
                res = self.corpora.resolve(ref, corpusref.PRD, where=f"{rel_to(self.repo, path)} AC")
                if res.is_error:
                    self.err(path, f"AC cites {res.message}: {block.strip()[:80]}")
        return out

    def _ac_foreign_states(self, block: str) -> list[tuple[str, str]]:
        """`(ref, status)` for each foreign PRD an AC block cites whose corpus is on disk."""
        out: list[tuple[str, str]] = []
        for ref in ac_qualified_cites(block, known=self.corpora.names):
            if self.corpora.is_local(ref):
                continue
            idx = self.corpora.index(str(ref.corpus))
            rec = idx.record(corpusref.PRD, ref.id) if idx is not None else None
            if rec is not None:
                out.append((str(ref), str(rec.get("status") or "")))
        return out

    def _is_tombstone(self, block: str) -> bool:
        """An AC that no longer asserts anything: its criterion OPENS struck through
        (`~~…~~` right after the number and disposition tags), or it carries a retirement
        acknowledgement (`journeys_retire_ack_cues` — the recogniser the capability-
        retirement check uses) inside a **bold marker** (`**N/A (superseded by …)**`,
        `**Withdrawn — …**`). Running prose that merely says "retired", or one struck word
        inside a live criterion, is NOT a tombstone — the skip is scoped to the marker."""
        body = _AC_TOMBSTONE_LEAD_RE.sub("", block.lstrip(), count=1)
        if body.startswith("~~"):
            return True
        if self.retire_ack_re is None:
            return False
        return any(self.retire_ack_re.search(span) for span in _BOLD_SPAN_RE.findall(block))

    # -- prose ship-state (the ShipState family's free-text leg) ------------------
    @staticmethod
    def _prose_prd_refs(line: str) -> list[tuple[str, int, int]]:
        """(PRD number, start, end) for every PRD reference on a prose line.

        Reads the explicit `PRD NNNN`, the parenthesised `(NNNN)`/`(PRD NNNN)`/multi-id
        spellings the AC citation reader already understands, and the corpus's bold
        `**NNNN**` pointer, so a `CAP-NNNN` capability id, an issue key or a date fragment
        is never mistaken for a PRD.
        """
        refs: dict[str, tuple[str, int, int]] = {}
        for m in PROSE_PRD_TAG_RE.finditer(line):
            refs.setdefault(m.group(1), (m.group(1), m.start(), m.end()))
        for m in _PROSE_PRD_BOLD_RE.finditer(line):
            refs.setdefault(m.group(1), (m.group(1), m.start(), m.end()))
        for m in AC_CITE_PAREN_RE.finditer(line):
            inner = m.group(1)
            if not (_AC_BARE_NUM_RE.fullmatch(inner) or AC_CITE_MARKER_RE.search(inner)):
                continue
            for nm in AC_PRD_NUM_RE.finditer(inner):
                refs.setdefault(nm.group(1), (nm.group(1), m.start(), m.end()))
        return sorted(refs.values(), key=lambda r: r[1])

    @staticmethod
    def _state_word_is_adjective(line: str, start: int) -> bool:
        """True when the lifecycle word at `start` modifies a noun ("the implementing run",
        "PRD 0590's implementing run", "(0194) that shipped") rather than being asserted of
        the PRD ("PRD NNNN is implementing")."""
        before = line[:start].rstrip()
        if _PROSE_STATE_POSSESSIVE_RE.search(before):
            return True
        m = re.search(r"([A-Za-z]+)$", before)
        return bool(m and m.group(1).lower() in _PROSE_STATE_MODIFIERS)

    def _prose_refs(self, line: str, owners: dict[str, str]) -> list[tuple[str, int, int]]:
        """(PRD number, start, end) for every reference on a prose line.

        The PRD references `_prose_prd_refs` already reads, PLUS a backticked journey/flow id
        resolved through its `owning_prd:` to that PRD's number. A claim that names only a
        flow — `` `recover-from-a-throttle`, planned `` — carries no PRD number at all, so
        before this it reached the corpus green while the flow's owning PRD had shipped
        (ENG-18544). A backticked id that is not a known journey, or whose journey names no
        owning PRD, is no reference.
        """
        refs = list(self._prose_prd_refs(line))
        if owners:
            for m in _PROSE_BACKTICK_ID_RE.finditer(line):
                num = owners.get(m.group(1))
                if num:
                    refs.append((num, m.start(), m.end()))
        return sorted(refs, key=lambda r: r[1])

    def _following_state_word(self, line: str, end: int, upper: int) -> str | None:
        """The first lifecycle word after a reference that asserts its own state, or None.

        Bounded at `upper` (the next reference's start) and at a clause break, within a short
        token window — or, when the reference opens a parenthetical, inside that
        parenthetical in full: `**0149** (Org-Scoped Groups …, prd-drafted)` states the PRD's
        state inside its own citation.
        """
        tail = line[end:upper]
        paren_close: int | None = None
        pm = re.match(r"\s*\(", tail)
        if pm:
            close = tail.find(")", pm.end())
            if close != -1:
                paren_close = close
        prev = 0
        seen = 0
        for m in _PROSE_TOKEN_RE.finditer(tail):
            if _PROSE_CLAUSE_BREAK_RE.search(tail[prev : m.start()]):
                break
            # A bare 4-digit number the reader did not formally recognise as a citation
            # (`` (predecessor `0594` cancelled) ``) is still a reference: the lifecycle
            # word after it belongs to that number, not to the one this window opened on.
            if AC_PRD_NUM_RE.search(tail[prev : m.start()]):
                break
            if paren_close is not None:
                if m.start() >= paren_close:
                    break
            elif seen >= PROSE_STATE_WINDOW:
                break
            prev = m.end()
            seen += 1
            word = m.group(0).lower()
            if word not in self._lifecycle_set:
                continue
            if self._state_word_is_adjective(line, end + m.start()):
                continue
            return word
        return None

    @staticmethod
    def _leads_phrase(line: str, start: int) -> bool:
        """True when the token at `start` opens a phrase — the line's own start, a bullet,
        a heading, a blockquote, or the open of a bold/italic span — rather than sitting
        mid-sentence after a verb, preposition or conjunction.

        A preceding lifecycle word only asserts the reference's state when it LEADS it
        (`**Planned install journey** …`); `is changed or cancelled before it starts` or
        `verified by PRD NNNN` carry the same word as a verb, and charging those to the
        reference is the false positive this guard exists to stop."""
        return bool(re.fullmatch(r"[\s*_>#\-]*", line[:start]))

    def _preceding_state_word(self, line: str, start: int, lower: int) -> str | None:
        """The nearest lifecycle word before a reference that asserts its own state, or None.

        Reads the shape where the status word LEADS the reference — the heading
        `**Planned install journey** — frontmatter links `install-…` (owning PRD 0518)` —
        which the forward window cannot see. Bounded at `lower` (the previous reference's
        end), at a clause break and by the wider backward window, and sharing the adjective
        guard, so a word of another clause is never charged.
        """
        seg = line[lower:start]
        last_break = 0
        for m in _PROSE_CLAUSE_BREAK_RE.finditer(seg):
            last_break = m.end()
        window = seg[last_break:]
        tokens = list(_PROSE_TOKEN_RE.finditer(window))
        for m in reversed(tokens[-PROSE_STATE_BACKWARD_WINDOW:]):
            word = m.group(0).lower()
            if word not in self._lifecycle_set:
                continue
            pos = lower + last_break + m.start()
            if self._state_word_is_adjective(line, pos):
                continue
            if not self._leads_phrase(line, pos):
                continue
            return word
        return None

    def check_prose_prd_state(
        self,
        path: Path,
        text: str,
        statuses: dict[str, str],
        owners: dict[str, str] | None = None,
    ) -> None:
        """A map/journey/feature-map PROSE line must not assert a PRD's lifecycle state
        differently from that PRD's live frontmatter `status:`.

        The ShipCite/Defer legs police AC dispositions, the `Status` column and the
        ship-state markers — but a Gaps bullet, a blockquote above the ACs or a
        Preconditions line carries the same claim in free prose and reached no check at
        all: four such lines asserted `implementing`/`prd-drafted`/`planned` for PRDs that
        had already shipped while every validator stayed green (ENG-17127). This reads a
        PRD reference — `PRD NNNN`, a `(NNNN)` citation or a bold `**NNNN**` — or a
        backticked flow id resolved through its `owning_prd:`, and the first lifecycle word
        on either side of it (following within a short token window, or, when the reference
        opens a parenthetical, inside that parenthetical; preceding within a wider one),
        failing when the word disagrees with the referenced PRD's `status:`.

        The window and the guards keep the corpus's false positives out — a `CAP-NNNN` id,
        an issue key or a date is no reference; a word introduced by an article, a possessive
        or a relative pronoun modifies another noun; a clause break ends the window; and a
        second reference in the window owns its own word, so a multi-PRD line compares each
        word with the PRD it belongs to. A line that is a tombstone or a retire-ack record
        asserts nothing about the live product and is skipped.
        """
        if not self._lifecycle_set or not statuses:
            return
        owners = owners or {}
        for ln, line in iter_md_body_lines(text):
            if self._is_tombstone(line):
                continue
            refs = self._prose_refs(line, owners)
            for i, (num, start, end) in enumerate(refs):
                live = statuses.get(num)
                if live is None:
                    continue
                # Adjacent references bound each window, so a multi-reference line compares
                # each status word with the reference it actually belongs to.
                lower = refs[i - 1][2] if i > 0 else 0
                upper = refs[i + 1][1] if i + 1 < len(refs) else len(line)
                word = self._following_state_word(line, end, upper)
                if word is None:
                    word = self._preceding_state_word(line, start, lower)
                if word is None or word == live.strip().lower():
                    continue
                self.err(
                    path,
                    f"L{ln}: prose states PRD {num} is `{word}` but its frontmatter "
                    f"`status:` is `{live.strip()}` — ship-state is the PRD's to state: "
                    f"{line.strip()[:80]}",
                    line=ln,
                    hint="Correct the prose to the PRD's live `status:`, or drop the status word from the sentence.",
                )

    # -- corpus readers -----------------------------------------------------------
    def component_ids(self) -> set[str]:
        """Registered component ids from the component registry's `## Components` table.

        Shape is validated by the component-registry check; this only needs the id column
        so a feature map's `components:` can be resolved against it."""
        if self._components is None:
            found: set[str] = set()
            reg = self.k / self.component_registry
            if reg.is_file():
                in_sec = False
                for line in reg.read_text(encoding="utf-8").splitlines():
                    if line.startswith("## "):
                        in_sec = line.strip() == "## Components"
                        continue
                    if not in_sec or not line.strip().startswith("|"):
                        continue
                    first = re.split(r"(?<!\\)\|", line.strip().strip("|"))[0].strip()
                    if first and first.lower() != "id" and set(first) - set("-: "):
                        found.add(first)
            self._components = found
        return self._components

    def permission_names(self) -> set[str]:
        """Closed permission vocabulary from the contract file, or empty when absent."""
        if self._permission_names is None:
            self._permission_names = load_permission_names(self.permissions_contract)
            self._permission_actions = {n.split(":")[-1] for n in self._permission_names}
        return self._permission_names

    def permission_actions(self) -> set[str]:
        """Action verbs the contract uses — filters which `resource:action` tokens to check."""
        if self._permission_actions is None:
            self.permission_names()  # populates both
        assert self._permission_actions is not None
        return self._permission_actions

    def frontend_mounts(self) -> tuple[set[str], set[str]]:
        """({testid literals/prefixes}, {PascalCase JSX components}) scanned once per run."""
        if self._frontend_testids is None:
            tids, comps = scan_frontend_mounts(self.repo, self.frontend_scan_roots, self.frontend_scan_suffixes)
            self._frontend_testids = tids
            self._frontend_components = comps
        assert self._frontend_components is not None
        return self._frontend_testids, self._frontend_components

    def check_ac_permission_names(self, path: Path, ac_blocks_list: list[str]) -> None:
        """Fail when an AC cites a permission-shaped token the contract does not name.

        Only tokens whose final segment is a verb the contract actually uses are checked —
        that is what keeps `changed:false` / `backend:external` / connector action ids out of
        scope without an allow-list. No contract file → leg is silent (a corpus without one).
        """
        names = self.permission_names()
        if not names:
            return
        actions = self.permission_actions()
        for block in ac_blocks_list:
            for tok in AC_PERMISSION_TOKEN_RE.findall(block):
                if tok.split(":")[-1] not in actions:
                    continue
                if tok not in names:
                    rel = (
                        self.permissions_contract.relative_to(self.repo)
                        if self.permissions_contract.is_relative_to(self.repo)
                        else self.permissions_contract
                    )
                    self.err(
                        path,
                        f"AC cites unknown permission `{tok}` (not in {rel}): {block.strip()[:80]}",
                        hint="Use a name from the permissions contract, or drop the token if it is not a permission.",
                    )

    def check_ac_absent_components(self, path: Path, ac_blocks_list: list[str]) -> None:
        """Fail when an AC claims a named component is absent but the tree still mounts it.

        An AC must both carry absence language and name the thing (a kebab testid in
        backticks, or a PascalCase React component). No frontend scan root on disk → silent.
        """
        if not any((self.repo / r.rstrip("/")).is_dir() for r in self.frontend_scan_roots):
            return
        testids, components = self.frontend_mounts()
        if not testids and not components:
            return
        for block in ac_blocks_list:
            if not AC_ABSENCE_RE.search(block):
                continue
            for tid in AC_TESTID_RE.findall(block):
                if _testid_is_mounted(tid, testids):
                    self.err(
                        path,
                        f"AC asserts absence of testid `{tid}` but it is mounted in the shipped frontend: "
                        f"{block.strip()[:80]}",
                        hint="Drop the absence claim, or remove the mount from the tree.",
                    )
            for name in AC_COMPONENT_NAME_RE.findall(_AC_TEST_FILENAME_RE.sub(" ", block)):
                if name in components:
                    self.err(
                        path,
                        f"AC asserts absence of component `{name}` but `<{name}` is mounted in the shipped frontend: "
                        f"{block.strip()[:80]}",
                        hint="Drop the absence claim, or remove the component mount from the tree.",
                    )

    def prd_statuses(self) -> dict[str, str]:
        """{prd number -> its frontmatter `status:`}."""
        out: dict[str, str] = {}
        base = self.k / self.prds_dir
        if not base.exists():
            return out
        for d in base.iterdir():
            f = d / "prd.md"
            if f.is_file() and d.name[:4].isdigit():
                fm = frontmatter(f.read_text(encoding="utf-8"))
                st = field(fm, "status") if fm else None
                if st:
                    out[d.name[:4]] = st
        return out

    def prd_projects(self) -> dict[str, str]:
        """{prd number -> its frontmatter `slice:` slug} (for derived slice edges)."""
        out: dict[str, str] = {}
        base = self.k / self.prds_dir
        if not base.exists():
            return out
        for d in base.iterdir():
            f = d / "prd.md"
            if f.is_file() and d.name[:4].isdigit():
                fm = frontmatter(f.read_text(encoding="utf-8"))
                proj = self.corpora.localize(field(fm, "slice") or "") if fm else None
                if proj:
                    out[d.name[:4]] = proj
        return out

    def prd_folders(self) -> set[str]:
        base = self.k / self.prds_dir
        return {d.name[:4] for d in base.iterdir() if d.is_dir() and d.name[:4].isdigit()} if base.exists() else set()

    def prd_journeys(self) -> dict[str, set[str]]:
        """{prd number -> journey ids declared in that PRD's `journeys:` frontmatter}."""
        out: dict[str, set[str]] = {}
        base = self.k / self.prds_dir
        if not base.exists():
            return out
        for d in base.iterdir():
            f = d / "prd.md"
            if not (f.is_file() and d.name[:4].isdigit()):
                continue
            fm = frontmatter(f.read_text(encoding="utf-8"))
            if fm:
                out[d.name[:4]] = set(listfield(fm, "journeys"))
        return out

    def project_slugs(self) -> set[str]:
        """Every slice id — a row in the slice register, which is where a slice lives."""
        return {s["id"] for s in slices(self.k, own=self.corpora.own)}

    def slice_depends(self) -> dict[str, list[str]]:
        return {s["id"]: s["depends_on"] for s in slices(self.k, own=self.corpora.own)}

    def load_journeys(self, sub: str) -> dict[str, dict[str, Any]]:
        """Return {id: {...}} for each flow/map under `<knowledge>/journeys/<sub>/`."""
        out: dict[str, dict[str, Any]] = {}
        base = self.k / self.journeys_dir / sub
        if not base.exists():
            return out
        for f in sorted(base.glob("*.md")):
            if f.stem.startswith("_"):
                continue
            text = f.read_text(encoding="utf-8")
            fm = frontmatter(text)
            if fm is None:
                self.err(f, "missing YAML frontmatter")
                continue
            out[f.stem] = {
                "path": f,
                "fm": fm,
                "body": text,
                "id": field(fm, "id"),
                "kind": field(fm, "kind"),
                "covers": listfield(fm, "covers"),
            }
        return out

    def _check_journey_sections(self, path: Path, text: str, want_kind: str) -> None:
        """A journey carries the sections the journey page and the Quality desk read.

        Documented in the *Journeys* page (`knowledge-base/journeys`): a flow and a map both open
        with a `**Job statement:**` paragraph, and a flow lists its numbered steps under
        `## Happy path`. A file written in another shape passes every other check and then draws
        a page with no job and no steps, so the absence is an error that names the section.
        """
        parsed = parse_journey(text)
        hint = f"see the docs page `{JOURNEY_DOCS_PAGE}` (How to write a journey) for the layout"
        if not parsed["job"]["text"]:
            self.err(
                path,
                f"{want_kind} journey has no `**Job statement:**` paragraph "
                "(write it as `**Job statement:** *When …, I want to …, so I can ….*`); "
                f"layout: docs page `{JOURNEY_DOCS_PAGE}`",
                hint=hint,
            )
        if want_kind == "flow" and not parsed["steps"]:
            self.err(
                path,
                "flow journey has no numbered steps under a `## Happy path` heading (spell the heading exactly so); "
                f"layout: docs page `{JOURNEY_DOCS_PAGE}`",
                hint=hint,
            )

    def _feature_map_sources(self) -> list[tuple[str, Path, bool]]:
        """(area, readable source, fragment_backed) for every feature map, README excluded.

        The area set is the UNION of `<area>.md` and `<area>.md.tmpl` (the consumer renderer's
        own discovery rule, `gen_knowledge_fragments.feature_maps`). A FRAGMENT-BACKED map
        (`gen_knowledge_fragments.TARGETS`) commits only its `<area>.md.tmpl` shell — the
        rendered `.md` is generated on demand and gitignored — so an unrendered checkout has
        the shell alone; when both exist the rendered map wins, because it is the shell plus
        the generated rows.

        `fragment_backed` is true exactly when the area has a `.md.tmpl` shell, and it is what
        gates reading the area's capability rows and `source_of_truth:` list from fragments:
        a map that is NOT fragment-backed may still have stray fragments under
        `features/rows/` (mid-migration), and its committed `.md` table is the authority for
        it — reading the fragments instead would validate a different corpus than the gate.
        """
        base = self.k / self.features_dir
        if not base.is_dir():
            return []
        sources: dict[str, Path] = {}
        for p in base.glob("*.md"):
            sources[p.stem] = p
        shells: set[str] = set()
        suffix = FEATURE_SHELL_SUFFIX
        for p in base.glob(f"*{suffix}"):
            area = p.name[: -len(suffix)]
            shells.add(area)
            sources.setdefault(area, p)  # the rendered `.md` (inserted first) wins
        return sorted((area, p, area in shells) for area, p in sources.items() if area != "README")

    def _sot_fragment_paths(self, area: str) -> list[str] | None:
        """The map-level `source_of_truth` paths for one area, from
        `features/source_of_truth/<area>/*.json`, or None when the area has no fragment dir.

        Each fragment holds `{"order": N, "path": "<as written in the frontmatter>"}` and the
        fragments own the map's `source_of_truth:` list (ENG-12782) — the shell's own block
        list is a projection that can lag them. `None` is distinct from `[]`: a map with no
        fragment dir is table-backed and reads its frontmatter, a map with one and no valid
        fragment claims nothing.
        """
        base = self.k / self.features_dir / FEATURE_SOT_SUBDIR / area
        if not base.is_dir():
            return None
        paths: list[str] = []
        for f in sorted(base.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            path = str(data.get("path") or "").strip()
            if path:
                paths.append(path)
        return sorted(dict.fromkeys(paths))

    def _feature_row_fragments(self, area: str) -> dict[str, dict[str, Any]]:
        """Capability rows for one fragment-backed map, keyed by id.

        Reads `features/rows/<CAP-NNNN>.json`, keeping only the fragments whose `table` key
        names this area (`<area>#<section>`). Empty when the area has none — the committed
        table is then the source, which a corpus mid-migration needs.
        """
        base = self.k / self.features_dir / FEATURE_ROWS_SUBDIR
        if not base.is_dir():
            return {}
        out: dict[str, dict[str, Any]] = {}
        for f in sorted(base.glob("*.json")):
            if not self.cap_id_re.match(f.stem):
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            table = str(data.get("table") or "")
            cells = data.get("cells")
            if not table.startswith(area + "#") or not isinstance(cells, list):
                continue
            out[f.stem] = self._cap_from_cols([f.stem, *[str(c) for c in cells]])
        return out

    def _cap_from_cols(self, cols: list[str]) -> dict[str, Any]:
        """One capability row's record from its full columns (id in slot 0).

        Shared by the committed-table walk and the fragment read so the two shapes can never
        disagree about which cell a `Tested by` / `Anchor` / `Needs` / `Source of truth` is.
        Columns 5-7 are optional and positional, exactly as the table has always read them. An optional 8th
        column, `Plain` (the short plain-language title), is read by header name by the readers and is ignored here.
        """
        tested = cols[3] if len(cols) > 3 else ""
        journeys: list[str] = []
        # A journey in ANOTHER corpus (`acme:fleet-check-result`): carried apart and resolved
        # there, never read as a local slug; an own-qualified one is the local slug.
        tested_ext: list[str] = []
        first_foreign = False
        for t in re.findall(r"`([^`]+)`", tested):
            name, _sep, slug = t.partition(":")
            if _sep and corpusref.CORPUS_NAME_RE.match(name) and SLUG_RE.match(slug):
                if self.corpora.own and name == self.corpora.own:
                    journeys.append(slug)
                else:
                    first_foreign = first_foreign or not (journeys or tested_ext)
                    tested_ext.append(t)
            elif SLUG_RE.match(t):
                journeys.append(t)
        return {
            # An own-qualified PRD (`acme:0012` in `acme`) is normalised to the local number HERE,
            # so every later reader of the cell — the resolution, the derived-edge advisory —
            # sees it as local; a foreign one stays qualified.
            "ships": corpusref.localize_text(cols[2], self.corpora.own) if len(cols) > 2 else "",
            "tested_cell": tested,
            "tested_journeys": journeys,
            "tested_ext": tested_ext,
            # The primary tester is the FIRST one written, wherever it lives.
            "primary": None if first_foreign else (journeys[0] if journeys else None),
            "primary_ext": tested_ext[0] if first_foreign else None,
            # optional 5th column — see check_anchors()
            "anchor": cols[4] if len(cols) > 4 else "",
            # optional 6th column — capability -> capability dependency edges, the 4th DAG.
            # See check_capability_needs()
            # A qualified edge (`fleet:CAP-1408`) is ANOTHER corpus's capability: it is carried
            # apart in `needs_ext` and never scanned as a local id — `:` is a word boundary, so
            # the unanchored pattern used to read it as this corpus's CAP-1408.
            **self._needs_from(cols[5] if len(cols) > 5 else ""),
            # optional 7th column — this row's OWN source_of_truth claim, falling back to
            # the map-level list when unset.
            "source_of_truth": _parse_row_source_of_truth(cols[6]) if len(cols) > 6 else [],
        }

    def _check_foreign_cover(self, path: Path, jid: str, ref: corpusref.Ref) -> None:
        """A journey here `covers:` a capability in another corpus (`fleet:CAP-1408`): it must
        exist there, and — the two-way link, across corpora — that capability's `Tested by` must
        name this journey back, qualified with this corpus's name (`acme:<journey>`). A sibling
        not on disk is counted as unverified, never passed and never failed."""
        res = self.corpora.resolve(ref, corpusref.CAPABILITY, where=f"{rel_to(self.repo, path)} covers")
        if res.is_error:
            self.err(path, f"covers {res.message}")
            return
        if res.record is None:
            return  # unverified: counted in the corpora summary
        if not self.corpora.own:
            self.err(path, f"covers `{ref}`: {_UNNAMED_CORPUS}")
            return
        back = f"{self.corpora.own}:{jid}"
        if back not in tuple(res.record.get("tested", ())):
            self.err(
                path,
                f"two-way: covers `{ref}` but corpus `{ref.corpus}`'s {ref.id} Tested-by does not list "
                f"`{back}` — name this journey there, qualified with this corpus's name",
            )

    def _check_foreign_tester(self, path: Path, cid: str, token: str, *, primary: bool) -> None:
        """A capability here is `Tested by` a journey in another corpus (`fleet:<slug>`): the
        journey must exist there, and when it is the primary tester its `covers:` must list this
        capability back, qualified with this corpus's name (`acme:CAP-0002`). A sibling not on
        disk is counted as unverified."""
        name, _sep, slug = token.partition(":")
        res = self.corpora.resolve(
            corpusref.Ref(name, slug), corpusref.JOURNEY, where=f"{rel_to(self.repo, path)} {cid}"
        )
        if res.is_error:
            self.err(path, f"{cid} Tested-by `{token}`: {res.message}")
            return
        if res.record is None or not primary:
            return
        if not self.corpora.own:
            self.err(path, f"{cid} Tested-by `{token}`: {_UNNAMED_CORPUS}")
            return
        back = f"{self.corpora.own}:{cid}"
        if back not in tuple(res.record.get("covers", ())):
            self.err(
                path,
                f"two-way: {cid} Tested-by `{token}` but that journey's covers (corpus `{name}`) lacks "
                f"`{back}` — cover it there, qualified with this corpus's name",
            )

    def _needs_from(self, cell: str) -> dict[str, list[str]]:
        """`{"needs": local ids, "needs_ext": foreign qualified refs}` for one `Needs` cell."""
        local = self.cap_ref_re.findall(mask(cell))
        ext: list[str] = []
        for ref, _start, _end in find_refs(cell):
            if self.corpora.is_local(ref):
                local.append(ref.id)
            else:
                ext.append(str(ref))
        return {"needs": local, "needs_ext": ext}

    def _ships_prds(self, path: Path, cid: str, ships: str) -> list[str]:
        """The LOCAL PRD numbers a `Ships in` cell names; each foreign one is resolved here.

        A qualified entry (`fleet:0899`) is resolved against the corpus it names — a miss or an
        undeclared corpus is an error, a cancelled PRD there is the same error a cancelled one
        here is, and a corpus not on disk is counted as unverified. It is never read as 0899.
        """
        local = PRD_NUM_RE.findall(mask(ships))
        for ref, _start, _end in find_refs(ships):
            if self.corpora.is_local(ref):
                local.append(ref.id)
                continue
            res = self.corpora.resolve(ref, corpusref.PRD, where=f"{rel_to(self.repo, path)} {cid} Ships-in")
            if res.is_error:
                self.err(path, f"{cid} Ships-in {res.message}")
            elif res.record and res.record.get("status") == "cancelled":
                self.err(
                    path,
                    f"{cid} Ships-in `{ref}` cites a cancelled PRD — "
                    "re-home onto the PRD's `cancelled_reason` successor(s)",
                )
        return local

    def load_feature_maps(self) -> dict[str, dict[str, Any]]:
        """Return {area: {...}} parsing each feature map's capability table.

        A fragment-backed map (ENG-12980) is discovered through its committed `<area>.md.tmpl`
        shell: its capability rows come from `features/rows/*.json` and its map-level
        `source_of_truth:` list from `features/source_of_truth/<area>/*.json`, so an
        unrendered checkout validates the same corpus as the rendered gate.
        """
        out: dict[str, dict[str, Any]] = {}
        for area, f, fragment_backed in self._feature_map_sources():
            text = f.read_text(encoding="utf-8")
            fm = frontmatter(text)
            if fm is None:
                self.err(f, "missing YAML frontmatter")
                continue
            # SSoT: a feature map carries no ship-state — it's read from the Ships-in PRD.
            if STATUS_HEADER_RE.search(text):
                self.err(
                    f,
                    "feature map must not carry a `Status` column — ship-state is read "
                    "from the Ships-in PRD's frontmatter `status:`",
                    hint="Delete the Status column; the linked PRD's `status:` is the answer.",
                )
            for g in self.banned_emoji:
                if g in text:
                    self.err(
                        f,
                        f"ship-state marker `{g}` is banned in maps — "
                        "read ship-state from the linked PRD's frontmatter `status:`",
                        hint="Remove the marker; ship-state is the linked PRD's to state.",
                    )
                    break
            # Fragments win when the area is fragment-backed (ENG-12980); any other map reads
            # its committed table, so a corpus mid-migration is served correctly.
            caps: dict[str, dict[str, Any]] = self._feature_row_fragments(area) if fragment_backed else {}
            if not caps:
                # Only rows inside a well-formed table (header + separator) count. A capability
                # pipe-line detached by a blank/heading/paragraph renders as raw pipe-text and
                # must not register as a capability.
                for run in pipe_runs(text):
                    if not is_valid_table_run(run):
                        continue
                    for _ln, line in run:
                        if is_table_separator(line):
                            continue
                        # unescaped pipes only — `\|` is a literal pipe in a cell, and a naive
                        # split shreds the row and shifts every column after it
                        cols = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
                        if len(cols) < 4 or not self.cap_id_re.match(cols[0]):
                            continue
                        if cols[0] in caps:
                            self.err(f, f"duplicate capability id `{cols[0]}` within this file")
                        caps[cols[0]] = self._cap_from_cols(cols)
            # The per-path fragments own the map-level `source_of_truth:` list when the area
            # is fragment-backed (ENG-12782); the shell's own block list is read otherwise.
            sot_frags = self._sot_fragment_paths(area) if fragment_backed else None
            source_of_truth = sot_frags if sot_frags is not None else listfield(fm, "source_of_truth")
            out[area] = {
                "path": f,
                "fm": fm,
                "body": text,
                "caps": caps,
                "journeys": listfield(fm, "journeys"),
                "source_of_truth": source_of_truth,
            }
        return out

    # -- route resolution ---------------------------------------------------------
    def _route_pool(self, path: Path, marker: str) -> list[tuple[str, bool]]:
        text = _route_array_text(path, marker)
        return _flatten_routes(text, self.redirect_elements) if text else []

    def _resolve_surface(self, raw: str, web_pool: list[tuple[str, bool]], admin_pool: list[tuple[str, bool]]) -> str:
        """Classify one `surfaces:` citation against the live route pools:
        'ok' | 'redirect' | 'dead' | 'unknown-prefix' | 'skip' (not a browser route,
        or no pool to check against — e.g. this checkout has no frontend tree).

        `admin: ` and `web: ` name the pool the remainder resolves against, and the
        two are symmetric (ENG-10175: the corpus cites real web routes with the
        `web: ` prefix, so skipping every non-`admin:` prefix made those citations
        invisible to this check — the gap an unbuilt surface shipped through in
        ENG-10172). Any OTHER `<word>:` prefix on a path-shaped citation is refused
        ('unknown-prefix'), not skipped: it looks like a routed surface, so silence
        would be a green light on a never-checked claim.
        """
        s = raw.strip()
        admin = s.startswith("admin:")
        web = s.startswith("web:")
        if admin:
            s = s[len("admin:") :]
        elif web:
            s = s[len("web:") :]
        elif s.startswith(self.surface_skip_prefixes):
            return "skip"
        elif (m := _SURFACE_PREFIXED_PATH_RE.match(s)) and not m.group(2).startswith("//"):
            return "unknown-prefix"  # `<word>: /path` — the callers refuse with a hint
        s = re.sub(r"\s*\([^)]*\)\s*$", "", s).split("?", 1)[0].strip()  # trailing "(note)" / "?query"
        if s in self.non_route_surfaces or not s.startswith("/"):
            return "skip"
        s = re.sub(r"\{([^}]+)\}", r":\1", s)  # journeys mix {ws} and :ws param spellings
        pool = admin_pool if admin else web_pool
        if not pool:
            return "skip"
        candidates = [s]
        org_prefix = self.org_route_prefix
        if org_prefix and not admin and not s.startswith(org_prefix.rsplit(":", 1)[0] + ":"):
            candidates.append(f"{org_prefix}{s}")
        cseg_variants = [_path_segments(c) for c in candidates]
        found_real = found_redirect = False
        for abs_path, is_redirect in pool:
            pseg = _path_segments(abs_path)
            if pseg and pseg[-1] == "*":
                continue  # catch-all — not a citable page
            for cseg in cseg_variants:
                if len(cseg) == len(pseg) and all(
                    a == b or (a.startswith(":") and b.startswith(":")) for a, b in zip(cseg, pseg, strict=True)
                ):
                    if is_redirect:
                        found_redirect = True
                    else:
                        found_real = True
        if found_real:
            return "ok"
        if found_redirect:
            return "redirect"
        return "dead"

    # -- table shape --------------------------------------------------------------
    def check_markdown_table_shape(self) -> None:
        """Every pipe-row in the corpus must sit in a well-formed table.

        A row separated from its header by a blank line, heading, or paragraph renders as
        raw pipe-delimited text in every markdown viewer. Feature-map capability parsing
        already refuses such rows; this extends the same shape rule to the rest of the
        corpus so a findings registry cannot go dark.
        """
        if not self.k.exists():
            return
        for f in sorted(self.k.rglob("*.md")):
            text = f.read_text(encoding="utf-8")
            for run in pipe_runs(text):
                if is_valid_table_run(run):
                    continue
                for ln, line in run:
                    if is_table_separator(line):
                        continue
                    # first cell (if any) for a readable diagnostic
                    cols = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
                    head = cols[0] if cols else line.strip()[:40]
                    self.err(
                        f,
                        f"L{ln}: orphan table row `{head}` — not preceded by a header + "
                        f"`|---|` separator in an unbroken pipe-run (renders as raw pipe-text)",
                        line=ln,
                        hint="Give the run a header row and a `|---|` separator, or unbreak the table.",
                    )

    # -- anchors ------------------------------------------------------------------
    def check_anchors(self, features: dict[str, dict[str, Any]]) -> None:
        """A capability's `Anchor` must resolve to code that exists.

        A row claiming "built" by citing a shipped PRD makes a claim that NEVER EXPIRES —
        the PRD stays `shipped` forever, so when the code is deleted the row lies silently.
        Measured on one area before anchoring: only ~82% of built-claims held; four rows
        cited shipped PRDs for code that had been deleted or never existed.

        An anchor inverts that failure mode. It names the narrowest file (or `file:symbol`)
        that IS the implementation, so deleting the capability breaks the build instead of
        quietly falsifying the ledger. The act of writing one is itself the audit: you
        cannot anchor something that does not exist.

        `UNVERIFIED` is permitted and reported as an advisory — it is an honest "we could
        not find this", which is strictly better than a false citation, but it means the
        built-claim is unproven and should be resolved into a real anchor or a `—` gap.
        """
        unverified: list[str] = []
        for area, fmap in features.items():
            for cid, c in fmap["caps"].items():
                anchor = (c.get("anchor") or "").strip().strip("`")
                if not anchor or anchor in ("—", "-"):
                    continue  # column not adopted here, or a declared gap with nothing to anchor
                if anchor == UNVERIFIED:
                    unverified.append(f"{area}:{cid}")
                    continue
                # A row claiming NOT built while pointing at real code is the false-gap
                # direction — it hides work you have already done and invites rebuilding it.
                if c["ships"].strip() in ("—", "-", ""):
                    self.err(
                        fmap["path"],
                        f"{cid} is declared a gap (`Ships in: —`) but carries anchor `{anchor}` — "
                        "a gap points at no code; correct `Ships in` or drop the anchor",
                    )
                    continue
                path_part = anchor.split(":", 1)[0].strip()
                # A submodule has no checkout in CI, so an anchor there would resolve
                # locally and silently pass in the pipeline — the exact false confidence
                # this mechanism exists to remove.
                if path_part.startswith("apps/"):
                    self.err(
                        fmap["path"],
                        f"{cid} anchor `{path_part}` points into the `apps/` submodule, which is not "
                        "checked out in CI — anchor the in-repo provisioning/dataplane file instead",
                    )
                    continue
                if not (self.repo / path_part).exists():
                    self.err(
                        fmap["path"],
                        f"{cid} anchor `{path_part}` does not resolve — capability claims built, code is absent",
                        hint="Re-point the anchor at the file that implements the capability, or mark the row a gap.",
                    )
                    continue
                if ":" in anchor:
                    symbol = anchor.split(":", 1)[1].strip()
                    target = self.repo / path_part
                    if (
                        target.is_file()
                        and symbol
                        and symbol not in target.read_text(encoding="utf-8", errors="ignore")
                    ):
                        self.err(fmap["path"], f"{cid} anchor symbol `{symbol}` not found in `{path_part}`")
        if unverified:
            self.report.raw_note(
                f"capability anchors: {len(unverified)} row(s) marked {UNVERIFIED} — built-claim unproven "
                f"({', '.join(unverified[:6])}{'…' if len(unverified) > 6 else ''})"
            )

    def _baseline_entries(self, rel: str) -> set[str]:
        bl = self.repo / rel
        if not bl.is_file():
            return set()
        return {
            ln.strip()
            for ln in bl.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")
        }

    def check_anchor_source_of_truth(self, features: dict[str, dict[str, Any]]) -> None:
        """A capability's `Anchor` must resolve within ITS OWN map's `source_of_truth:`
        (map-level list ∪ row-level claims, the same containment scoped to one map).

        `check_anchors()` proves the anchor FILE exists on disk; this proves the map that
        names it also DECLARES it. A map anchoring a file it does not claim is a
        contradiction on its face — the freshness advisory (which keys off the map's
        `source_of_truth`) can never fire for the very file the map says implements one of
        its capabilities, so a drift there is invisible until the anchor itself breaks.

        Pure set-containment over one file's frontmatter + table: no git-churn analysis, no
        bounding judgement. Absolute: every out-of-scope anchor is a HARD failure. The anchor
        baseline was retired at zero (ENG-12744), so a missing (or present) baseline is never
        read and debt can never be re-acknowledged here.
        """
        for _area, fmap in features.items():
            claimed = self._map_claimed_paths(fmap)
            for cid, c in fmap["caps"].items():
                anchor = (c.get("anchor") or "").strip().strip("`")
                if not anchor or anchor in ("—", "-") or anchor == UNVERIFIED:
                    continue
                path_part = anchor.split(":", 1)[0].strip()
                if any(path_part == cc or path_part.startswith(cc + "/") for cc in claimed):
                    continue
                self.err(
                    fmap["path"],
                    f"{cid} anchor `{path_part}` is not covered by this map's own `source_of_truth:` — "
                    "a map must declare the file it anchors (or the row claims it); an out-of-scope "
                    "anchor is a hard failure (the acknowledged-debt anchor baseline was retired)",
                    hint="Add the anchored path to this map's `source_of_truth:` (map-level or row-level).",
                )

    # -- capability ledger --------------------------------------------------------
    def check_capability_ledger(self, caps: dict[str, tuple[str, dict[str, Any]]]) -> None:
        """The capability alias file is the HISTORICAL old→new mapping for capability ids.

        An opaque id is only worth anything if it is never reused and never renumbered — a
        citation in a shipped PRD or a tracker issue must still point at the same capability
        in five years. Allocating one no longer edits a shared file (ENG-12981): a capability
        PR mints an id and the STATELESS legs enforce uniqueness and permanence — the
        `id-collisions` check against the trunk tip, every open peer PR and the repository's
        own history, plus the uniqueness rules below on the alias table itself. There is no
        `APPEND ONLY. Next id:` counter to bump and no per-capability row to append, so two
        branches allocating from the same file no longer collide on it (the conflict class
        ENG-7962 recorded).

        The file keeps the pre-migration old→new mapping — a historical fact no current tree
        reproduces — and the rules this check still binds are:

          - every `Old id` aliases exactly one `New id`
          - every `New id` is allocated at most once (ids are never reused)
          - a project that names a ledger keeps it present

        The `Old id` column is the alias half — how a citation in a shipped PRD, a merged
        audit record or a tracker issue still resolves. It is append-only and never
        rewritten; `—` means a capability minted after the migration, which has no old id.
        `caps` is accepted for the caller's symmetry and is deliberately not required to be
        registered here: a post-migration id has no alias and no row.
        """
        # An option set to "" is a project SAYING it keeps no such ledger — not a missing
        # file. The two are different facts and must report differently: a NAMED ledger that
        # is not there is an error, an unnamed one is nothing to check. (Reading `self.k / ""`
        # is the knowledge directory itself, which `exists()` happily confirms and
        # `read_text` then raises `IsADirectoryError` on.)
        if not self.cap_ledger:
            return
        f = self.k / self.cap_ledger
        if not f.is_file():
            self.err(f, "the capability allocation ledger is missing")
            return
        text = f.read_text(encoding="utf-8")

        allocated: dict[str, int] = {}
        aliases: dict[str, str] = {}
        for run in pipe_runs(text):
            if not is_valid_table_run(run):
                continue
            for ln, line in run:
                if is_table_separator(line):
                    continue
                cols = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
                if len(cols) < 3 or not self.cap_id_re.match(cols[0]):
                    continue
                new, old = cols[0], cols[1]
                if new in allocated:
                    self.err(f, f"line {ln}: `{new}` is allocated twice — ids are never reused", line=ln)
                allocated[new] = ln
                if old and old != "—":
                    if old in aliases:
                        self.err(f, f"line {ln}: old id `{old}` already aliases `{aliases[old]}`", line=ln)
                    aliases[old] = new

    # -- capability dependency graph ----------------------------------------------
    def check_capability_needs(self, features: dict[str, dict[str, Any]], prd_projects: dict[str, str]) -> None:
        """The capability dependency graph (`Needs`, the 4th DAG).

        `Needs` is what makes a goal decomposition SEQUENCEABLE: working backwards from a
        goal produces capability rows, and these edges are how "this before that" is
        recorded — without them a decomposition is a flat list with no build order.

        Rules:
          - every referenced id resolves to a real capability (cross-map allowed; ids are
            globally unique)
          - the graph is acyclic — a cycle makes the build order undefined
          - DERIVED-EDGE ADVISORY: if cap A needs cap B and their delivering PRDs live in
            different slices, the slices should carry the matching `depends_on` edge —
            otherwise the rendered arrows contradict the decomposition they claim to show.
        """
        # global registry + edge list
        all_caps: dict[str, tuple[str, dict[str, Any]]] = {}
        for area, fmap in features.items():
            for cid, c in fmap["caps"].items():
                all_caps[cid] = (area, c)

        graph: dict[str, list[str]] = {}
        for _area, fmap in features.items():
            for cid, c in fmap["caps"].items():
                deps = c.get("needs") or []
                graph[cid] = deps
                for d in deps:
                    if d == cid:
                        self.err(fmap["path"], f"{cid} Needs itself")
                    elif d not in all_caps:
                        self.err(fmap["path"], f"{cid} Needs `{d}`, which is not a known capability id")
                # Another corpus's capability: resolved there, and an opaque node to the cycle
                # check below — no cycle through this corpus's graph can pass through it.
                for ext in c.get("needs_ext") or []:
                    res = self.corpora.resolve(
                        ext, corpusref.CAPABILITY, where=f"{rel_to(self.repo, fmap['path'])} {cid}"
                    )
                    if res.is_error:
                        self.err(fmap["path"], f"{cid} Needs {res.message}")

        # cycle detection (white/grey/black DFS)
        white, grey, black = 0, 1, 2
        color = dict.fromkeys(graph, white)
        stack: list[str] = []

        def visit(n: str) -> list[str] | None:
            color[n] = grey
            stack.append(n)
            for m in graph.get(n, []):
                if m not in color:
                    continue
                if color[m] == grey:
                    return stack[stack.index(m) :] + [m]
                if color[m] == white and (cyc := visit(m)):
                    return cyc
            stack.pop()
            color[n] = black
            return None

        for n in list(graph):
            if color[n] == white and (cyc := visit(n)):
                self.report.raw_err(f"capability dependency cycle: {' -> '.join(cyc)}")
                break

        # derived slice edges: cap edge across two slices => slice edge expected
        proj_deps = self.slice_depends()
        missing_edges: set[tuple[str, str, str, str]] = set()
        for cid, deps in graph.items():
            a_prds = PRD_NUM_RE.findall(mask(all_caps[cid][1]["ships"])) if cid in all_caps else []
            for d in deps:
                if d not in all_caps:
                    continue
                b_prds = PRD_NUM_RE.findall(mask(all_caps[d][1]["ships"]))
                for pa in a_prds:
                    for pb in b_prds:
                        proj_a, proj_b = prd_projects.get(pa), prd_projects.get(pb)
                        if proj_a and proj_b and proj_a != proj_b and proj_b not in proj_deps.get(proj_a, []):
                            missing_edges.add((cid, d, proj_a, proj_b))
        for cid, d, proj_a, proj_b in sorted(missing_edges):
            self.report.raw_note(
                f"derived project edge missing: {cid} Needs {d} spans projects "
                f"`{proj_a}` -> `{proj_b}`, but `{proj_a}` does not depends_on `{proj_b}`"
            )

    # -- PRD↔journey reference edges ----------------------------------------------
    def check_prd_journeys(self, all_journey_ids: set[str]) -> None:
        """PRD -> journey half of the PRD↔journey edge: a PRD's `journeys:` frontmatter
        must name real journeys.

        The journey side is checked in `check_journey` (a journey's `owning_prd` must be
        listed back by that PRD), but nothing read the forward arrow: a PRD naming
        `no-such-journey` left every machine gate green, the dangling edge catchable only
        by a human reading the diff (ENG-9450). Resolution only — a PRD may name a
        journey that does not declare it back (one PRD exercising a flow another PRD
        owns), so no bidirectional ownership is asserted here.
        """
        base = self.k / self.prds_dir
        if not base.exists():
            return
        for d in sorted(base.iterdir()):
            f = d / "prd.md"
            if not (f.is_file() and d.name[:4].isdigit()):
                continue
            fm = frontmatter(f.read_text(encoding="utf-8"))
            if not fm:
                continue
            for jname in listfield(fm, "journeys"):
                if jname not in all_journey_ids:
                    self.err(
                        f,
                        f"journeys `{jname}` does not resolve to an existing journey flow/map (knowledge/journeys/*)",
                    )

    # -- claimed-path helpers -----------------------------------------------------
    def _row_source_paths(self, fmap: dict[str, Any]) -> list[tuple[str, str]]:
        """(cid, path) pairs for every row-level `Source of truth` entry in this map."""
        return [(cid, p) for cid, info in fmap["caps"].items() for p in info.get("source_of_truth", [])]

    def _claimed_paths(self, features: dict[str, dict[str, Any]]) -> set[str]:
        """Every code path claimed by ANY map — the map-level `source_of_truth:` list
        UNION every capability row's own claim. A row's claim is additive: it can cover a
        path the map-level list never named, which is what lets a capability be attributed
        precisely instead of only through its map's wholesale directory declaration."""
        claimed = {s.rstrip("/") for fmap in features.values() for s in fmap["source_of_truth"]}
        claimed |= {p.rstrip("/") for fmap in features.values() for _cid, p in self._row_source_paths(fmap)}
        return claimed

    def _map_claimed_paths(self, fmap: dict[str, Any]) -> set[str]:
        """This map's own claims only — map-level `source_of_truth:` UNION its row cells."""
        claimed = {s.rstrip("/") for s in fmap["source_of_truth"]}
        claimed |= {p.rstrip("/") for _cid, p in self._row_source_paths(fmap)}
        return claimed

    @staticmethod
    def _path_claimed_by(rel: str, claimed: set[str]) -> bool:
        """True when `rel` equals or lives under any entry in `claimed` (prefix containment)."""
        return any(rel == c or rel.startswith(c + "/") for c in claimed)

    def _text_for_prose_path_scan(self, text: str) -> str:
        """Strip the structured fields the prose scan must not re-check from a map body.

        - `source_of_truth:` / `source_of_truth_broad_ok:` fields are the claim itself —
          matching them would make every honest map advisory-noise against its own
          frontmatter. The match spans the whole field (ENG-14299): the key line plus any
          block-list `  - <path>` lines, so the paths themselves are not re-read as prose.
        - Capability-table Anchor cells (column 5) are the anchor-scope check's contract.
          This is the *prose* sibling; blanking the cell keeps the two from double-counting
          the same cite.
        """
        scrubbed = re.sub(r"(?m)^source_of_truth(?:_broad_ok)?:[^\n]*(?:\n[ \t]+-[^\n]*)*", "", text)
        out: list[str] = []
        for line in scrubbed.splitlines():
            if is_pipe_line(line) and not is_table_separator(line):
                cols = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
                if len(cols) >= 5 and self.cap_id_re.match(cols[0]):
                    cols[4] = "—"
                    line = "| " + " | ".join(cols) + " |"
            out.append(line)
        return "\n".join(out)

    def _extract_prose_named_paths(self, text: str, leaf_index: dict[str, list[str]]) -> set[str]:
        """Code paths a feature map's prose names — full repo-relative paths, plus bare
        leaf filenames that uniquely resolve under a coverage root."""
        found: set[str] = set()
        for m in self.prose_path_re.finditer(text):
            found.add(m.group(1).rstrip("/"))
        for m in PROSE_BARE_LEAF_RE.finditer(text):
            cands = leaf_index.get(m.group(1), [])
            if len(cands) == 1:
                found.add(cands[0])
        return found

    def _leaf_index(self) -> dict[str, list[str]]:
        """leaf basename -> covered, non-excluded paths carrying that basename."""
        idx: dict[str, list[str]] = {}
        for rel in self._covered_paths():
            if self._coverage_excluded(rel):
                continue
            leaf = rel.rsplit("/", 1)[-1]
            idx.setdefault(leaf, []).append(rel)
        return idx

    def _under_coverage_root(self, rel: str) -> bool:
        """True when `rel` sits under a coverage root (or is an extra covered spec file)."""
        if self.extra_covered_re.fullmatch(rel):
            return True
        return any(rel == r.rstrip("/") or rel.startswith(r) for r in self.coverage_roots)

    def check_prose_named_paths(self, features: dict[str, dict[str, Any]]) -> None:
        """Advisory: prose-named code paths must be claimed by some map.

        A feature map that talks about a concrete file (in its Scope block, capability
        descriptions, frontmatter comments, …) while that file sits only in the unclaimed
        baseline is a freshness blind spot: the map that cares never receives the advisory
        when the file changes, because the baseline is treated as an owner.

        Reported as non-blocking — prose parsing has false-positive risk, and a hard fail
        would force every historical cross-cite to be cleaned before any commit. Cross-map
        cites of a path another map already claims are fine (the freshness contract still
        has an owner); only *nobody-claims-it* is the signal. Anchor cells are excluded.
        """
        global_claimed = self._claimed_paths(features)
        leaf_index = self._leaf_index()
        hits: list[tuple[Path, str]] = []
        for area, fmap in sorted(features.items()):
            scan = self._text_for_prose_path_scan(fmap["path"].read_text(encoding="utf-8"))
            for rel in sorted(self._extract_prose_named_paths(scan, leaf_index)):
                if not (self.repo / rel).exists():
                    continue
                if self._coverage_excluded(rel) or not self._under_coverage_root(rel):
                    continue
                if self._path_claimed_by(rel, global_claimed):
                    continue
                hits.append(
                    (
                        fmap["path"],
                        f"prose names `{rel}` but no feature map's "
                        f"`source_of_truth:` claims it (sits in UNCLAIMED.baseline or is unowned) — "
                        f"claim it on `{area}` (or the owning map) so freshness reaches the map that "
                        f"names it (ENG-6135)",
                    )
                )
        if hits:
            self.report.raw_note(
                f"prose-named unclaimed paths: {len(hits)} cite(s) — a map names a file nobody "
                f"claims (freshness blind spot; ENG-6135)"
            )
            for path, msg in hits:
                self.note(path, msg)

    # -- exhaustive coverage ------------------------------------------------------
    def _coverage_excluded(self, rel: str) -> bool:
        """True when a covered path is a reviewed carve-out (never a silent allowance).

        A path is exempt from exhaustive coverage when it lives under an excluded root
        (tooling, CLI, tests, generated trees), under a generated/test-only subtree
        (testdata, dist, build, node_modules), or is itself a test or generated leaf."""
        for root in self.coverage_excluded_roots:
            if rel == root.rstrip("/") or rel.startswith(root):
                return True
        for seg in self.coverage_excluded_segment:
            if seg in rel:
                return True
        leaf = rel.rsplit("/", 1)[-1]
        if leaf.startswith("test_") or leaf.endswith(self.coverage_excluded_leaf):
            return True
        return bool(self.gen_leaf_re.search(rel))

    def _tracked_paths(self) -> set[str] | None:
        """Repo-relative git-tracked + untracked-but-not-ignored files.

        None means the root isn't a git working tree (the self-tests build a bare temp
        tree) — callers fall back to a raw filesystem walk in that case."""
        try:
            result = subprocess.run(
                ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                cwd=self.repo,
                capture_output=True,
                text=True,
                check=True,
            )
        except (subprocess.CalledProcessError, OSError):
            return None
        return {line for line in result.stdout.splitlines() if line}

    def _covered_paths(self) -> list[str]:
        """Every code path under the coverage roots — gitignored paths are never treated
        as "code" needing feature-map coverage.

        When the root is a real git working tree, this filters `git ls-files` (tracked +
        untracked-but-unignored) down to the coverage roots, so a gitignored build/test
        artifact left on disk under a covered root is never walked at all. Excluded
        carve-outs are re-filtered downstream by every caller. Falls back to a raw
        `os.walk` when the root isn't a git repo; that path still prunes carve-outs during
        the walk to keep it cheap."""
        tracked = self._tracked_paths()
        out: list[str] = []
        for root in self.coverage_roots:
            if not root.endswith("/"):
                if tracked is not None:
                    if root in tracked:
                        out.append(root)
                elif (self.repo / root).is_file():
                    out.append(root)
                continue
            if tracked is not None:
                out.extend(rel for rel in tracked if rel.startswith(root))
                continue
            base = self.repo / root.rstrip("/")
            if not base.is_dir():
                continue
            for dirpath, dirnames, filenames in os.walk(base):
                rel_dir = str(Path(dirpath).relative_to(self.repo))
                kept = []
                for d in dirnames:
                    cand = f"{rel_dir}/{d}"
                    if self._coverage_excluded(cand) or d == "node_modules":
                        continue
                    kept.append(d)
                dirnames[:] = kept
                for fn in filenames:
                    out.append(f"{rel_dir}/{fn}")
        # extra covered files — the top-level spec files only (generated trees excluded above)
        if tracked is not None:
            out.extend(rel for rel in tracked if self.extra_covered_re.fullmatch(rel))
        else:
            for d, pattern in self.extra_covered_scan:
                for p in (self.repo / d).glob(pattern):
                    out.append(str(p.relative_to(self.repo)))
        return out

    def unclaimed_paths(self, features: dict[str, dict[str, Any]]) -> list[str]:
        claimed = self._claimed_paths(features)
        return sorted(
            rel
            for rel in self._covered_paths()
            if not self._coverage_excluded(rel) and not self._path_claimed_by(rel, claimed)
        )

    def check_source_coverage(self, features: dict[str, dict[str, Any]]) -> None:
        """Exhaustive source_of_truth coverage — the inversion.

        Every covered path must be claimed by some map's `source_of_truth:`, excluded as a
        reviewed carve-out, or named in the unclaimed baseline (acknowledged debt). A path
        in none of those is a hard failure.

        The gate is ABSOLUTE (ENG-12738): a missing baseline is ZERO acknowledged debt, not
        a reason to skip. The baseline is a burn-down queue that may shrink, never grow; once
        a corpus reaches zero it deletes the file, and from then on full coverage is
        enforced with no grandfather. An unarmed tree is therefore NOT exempt the way it
        was under the adoption-era dormant path."""
        baseline_file = self.repo / self.baseline_rel
        baseline = self._baseline_entries(self.baseline_rel)
        claimed = self._claimed_paths(features)
        unclaimed: list[str] = []
        for rel in self._covered_paths():
            if self._coverage_excluded(rel):
                continue
            if self._path_claimed_by(rel, claimed):
                continue
            if rel not in baseline:
                unclaimed.append(rel)
        if unclaimed:
            armed = baseline_file.is_file()
            for rel in sorted(unclaimed)[:60]:
                self.err(
                    baseline_file,
                    f"unclaimed code path `{rel}` — covered by no feature map's `source_of_truth:`"
                    + (
                        " and absent from UNCLAIMED.baseline; claim it in a map or add it to the "
                        "baseline as acknowledged debt (the baseline may shrink, never grow)"
                        if armed
                        else "; claim it in the owning feature map's `source_of_truth:` "
                        "(the unclaimed baseline is retired, so the gate is absolute)"
                    ),
                    hint="Claim the path in the owning feature map's `source_of_truth:`.",
                    command=self.write_baseline_command if armed else None,
                )
            if len(unclaimed) > 60:
                self.err(baseline_file, f"...and {len(unclaimed) - 60} further unclaimed paths")
        if baseline:
            self.report.raw_note(
                f"UNCLAIMED.baseline: {len(baseline)} path(s) of acknowledged debt remain to be "
                "claimed (the burn-down queue)",
                path=baseline_file,
            )

    # -- git baseline comparisons -------------------------------------------------
    def merge_base(self) -> str | None:
        """The merge-base of the configured base ref and `HEAD`, computed once per run.

        It is a constant for the whole run; re-forking `git merge-base` for every journey
        file cost 246 byte-identical subprocesses. Returns None when there is no shared
        history yet (the branch that creates the file is exempt) or the call fails."""
        if not self._merge_base_read:
            self._merge_base_read = True
            try:
                self._merge_base = subprocess.check_output(
                    ["git", "merge-base", self.base_ref, "HEAD"],
                    cwd=self.repo,
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
            except Exception:
                self._merge_base = None
        return self._merge_base

    def _base_file(self, path: str) -> str | None:
        """Content of a repo-relative file at the merge-base, or None when it is absent or
        unreadable (the branch that creates the file is exempt)."""
        base = self.merge_base()
        if base is None:
            return None
        try:
            return subprocess.check_output(
                ["git", "show", f"{base}:{path}"], cwd=self.repo, text=True, stderr=subprocess.DEVNULL
            )
        except Exception:
            return None

    def _read_base_files(self, paths: Sequence[str]) -> dict[str, str]:
        """Contents of `paths` (repo-relative) at the merge-base, read in ONE `git ls-tree`
        + ONE `git cat-file --batch` pass instead of a `git show` fork per path.
        A path absent at the base is omitted; its caller treats it as exempt."""
        base = self.merge_base()
        if base is None or not paths:
            return {}
        try:
            tree = subprocess.run(
                ["git", "ls-tree", "-r", "-z", base, "--", *paths],
                cwd=self.repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=True,
            ).stdout
        except Exception:
            return {}
        sha_by_path: dict[str, str] = {}
        for rec in tree.split(b"\0"):
            if not rec:
                continue
            meta, _, rel = rec.partition(b"\t")
            sha_by_path[meta.split()[-1].decode()] = rel.decode()
        if not sha_by_path:
            return {}
        try:
            batch = subprocess.run(
                ["git", "cat-file", "--batch"],
                cwd=self.repo,
                input="\n".join(sha_by_path).encode(),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=True,
            ).stdout
        except Exception:
            return {}
        contents: dict[str, str] = {}
        i = 0
        for sha in sha_by_path:
            nl = batch.find(b"\n", i)
            if nl == -1:
                break
            header = batch[i:nl].split()
            if len(header) < 3 or header[1] != b"blob":
                break
            size = int(header[2])
            start = nl + 1
            contents[sha] = batch[start : start + size].decode("utf-8", errors="replace")
            i = start + size + 1
        return {rel: contents[sha] for sha, rel in sha_by_path.items() if sha in contents}

    def _base_baseline(self, path: str) -> set[str] | None:
        """Baseline entries at the merge-base of the base ref and `HEAD` — what *this
        branch* changed, not what the base's tip currently holds. A commit on the base that
        *shrinks* the baseline must not read every pre-existing branch as having grown it.
        Returns None when there is no shared baseline yet (the creating PR is exempt)."""
        old = self._base_file(path)
        if old is None:
            return None
        return {ln.strip() for ln in old.splitlines() if ln.strip() and not ln.lstrip().startswith("#")}

    def check_covers_shrink(self, journeys: dict[str, dict[str, Any]], caps: set[str]) -> None:
        """Advisory: a journey whose `covers:` lost an entry relative to the merge base.

        The failure this guards: two branches allocating the same capability id text-merge
        the identical token into one entry with no conflict, and the branch's capability is
        silently dropped from the journey's coverage — a loss that survives the merge and
        reads as intended. It is an ADVISORY, never a hard fail, for two reasons. A loss can
        be intended: a PRD re-scoping which journey covers a still-live capability, or
        retiring one, is legitimate, and a blocker would break real PRD work. And the check
        can only compare tokens, not meanings, so it cannot by itself tell a clean-merge
        collapse from a deliberate edit. It exists so a human resolving a journey merge is
        TOLD when coverage shrank relative to the base, and only for capabilities that are
        still defined — a retired capability's removal is unambiguous and stays silent."""
        rel_by_id = {jid: str(d["path"].relative_to(self.repo)) for jid, d in journeys.items()}
        base_files = self._read_base_files(list(rel_by_id.values()))
        for jid, d in journeys.items():
            old = base_files.get(rel_by_id[jid])
            if old is None:
                continue
            fm = frontmatter(old)
            if fm is None:
                continue
            base_covers = set(listfield(fm, "covers"))
            head = set(d["covers"])
            live = sorted(c for c in (base_covers - head) if c in caps)
            if not live:
                continue
            self.note(
                d["path"],
                f"`covers:` lost {', '.join(live)} relative to the merge "
                "base while the capability is still defined — if this is a text-merge collapse "
                "(two branches allocating the same CAP id), restore the entry; if a deliberate "
                "re-scope, this advisory is expected (ENG-7962)",
            )

    def check_composes_used_by(
        self,
        flows: dict[str, dict[str, Any]],
        maps: dict[str, dict[str, Any]],
    ) -> None:
        """A map's `composes:` and a flow's `used_by:` are the two directions of ONE edge.

        The `Resolve` leg only checks that each id names a real journey; it never checks that
        the two authored directions AGREE, so a map could compose a flow while that flow's
        `used_by:` omits the map — or a flow could be `used_by:` a map whose `composes:`
        omits the flow — with every gate green. ENG-18544's `reviewer-evidence-thread` omitted
        `evidence-export` from `composes:` while `evidence-export.md` declared
        `used_by: [reviewer-evidence-thread]`.

        This is the `composes`/`used_by` twin of the `covers:`/`Tested by` `Linking` leg: an
        edge declared on EITHER side must be declared on the other, reported at the side that
        states it, so a half-wired link fails instead of reading as intended. A map that
        composes another MAP has no inverse field on the composed map, so only the
        map->flow edge is required to be reciprocal; both authored directions of a
        flow<->map edge are enforced. An id that resolves to nothing is the `Resolve` leg's
        failure, not this one.
        """
        mrel = {mid: str(m["path"].relative_to(self.repo)) for mid, m in maps.items()}
        frel = {fid: str(f["path"].relative_to(self.repo)) for fid, f in flows.items()}
        for mid, m in maps.items():
            for jid in listfield(m["fm"], "composes"):
                f = flows.get(jid)
                if f is None:
                    continue
                if mid not in listfield(f["fm"], "used_by"):
                    self.err(
                        m["path"],
                        f"composes `{jid}` but `{jid}`'s used_by does not list `{mid}` (one-way composes/used_by edge)",
                        hint=f"Add `{mid}` to {frel[jid]}'s `used_by:`, or drop `{jid}` from "
                        f"{mrel[mid]}'s `composes:`.",
                    )
        for fid, f in flows.items():
            for mid in listfield(f["fm"], "used_by"):
                mp = maps.get(mid)
                if mp is None:
                    continue
                if fid not in listfield(mp["fm"], "composes"):
                    self.err(
                        f["path"],
                        f"used_by `{mid}` but `{mid}`'s composes does not list `{fid}` (one-way composes/used_by edge)",
                        hint=f"Add `{fid}` to {mrel[mid]}'s `composes:`, or drop `{mid}` from "
                        f"{frel[fid]}'s `used_by:`.",
                    )

    def _check_ratchet(self, rel: str, label: str, command: str) -> None:
        """A baseline may shrink, never grow: a change that net-adds baseline lines fails
        unless an equal number is removed in the same diff (burn-down) or the addition is
        explicitly acknowledged with a `# ack: <path> <reason>` comment line. Silently
        regenerating the baseline to absorb new debt would launder the signal, so this is a
        check, not a convention."""
        cur = self.repo / rel
        if not cur.is_file():
            return
        base_entries = self._base_baseline(rel)
        if base_entries is None:
            return  # no baseline at the merge-base yet — the creation PR is exempt
        lines = cur.read_text(encoding="utf-8").splitlines()
        new_entries = {ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")}
        acked = {m.group(1) for m in (re.match(r"\s*#\s*ack:\s*(\S+)", ln) for ln in lines) if m}
        added = new_entries - base_entries
        removed = base_entries - new_entries
        if len(added - acked) > len(removed):
            for p in sorted(added - acked)[:30]:
                self.err(
                    cur,
                    f"{label}: `{p}` added without a matching burn-down — the baseline may shrink, never grow",
                    hint="Claim the path instead of baselining it, or acknowledge it with a `# ack:` line.",
                    command=command,
                )

    # -- the run ------------------------------------------------------------------
    def run(self) -> Reporter:
        flows = self.load_journeys(self.flows_subdir)
        maps = self.load_journeys(self.maps_subdir)
        features = self.load_feature_maps()
        prds = self.prd_folders()
        pj = self.prd_journeys()
        pst = self.prd_statuses()
        projects = self.project_slugs()
        all_journey_ids = set(flows) | set(maps)
        web_pool = self._route_pool(self.web_main, self.web_marker)
        admin_pool = self._route_pool(self.admin_app, self.admin_marker)
        # {journey id -> its owning PRD number}. A prose claim that names only a flow
        # (`` `recover-from-a-throttle`, planned ``) is a claim about the flow's owning PRD;
        # the map is what lets `check_prose_prd_state` resolve it (ENG-18544).
        journey_owners: dict[str, str] = {}
        for jid, d in {**flows, **maps}.items():
            owns = listfield(d["fm"], "owning_prds")
            own = field(d["fm"], "owning_prd") or (owns[0] if owns else None)
            if own:
                journey_owners[jid] = own[:4]

        # PRD -> journey resolution — the forward half of the PRD↔journey edge, before
        # the per-journey checks so a dangling PRD-side entry is reported at its PRD.
        self.check_prd_journeys(all_journey_ids)

        # capability registry: id -> (area, info)
        caps: dict[str, tuple[str, dict[str, Any]]] = {}
        for area, fmap in features.items():
            af = fmap["fm"]
            if not field(af, "area"):
                self.err(fmap["path"], "missing required frontmatter field `area`")
            elif field(af, "area") != area:
                self.err(fmap["path"], f"area `{field(af, 'area')}` does not match filename `{area}`")
            # `kind:` — is this a customer-recognisable feature area, or engineering
            # substrate? A feature map is a CUSTOMER-facing decomposition; "repo CI" is not
            # a feature a customer would name. Substrate work still needs a durable home,
            # so it gets a map — but it must say so, or the taxonomy quietly becomes a
            # catch-all and stops meaning what it says.
            kind = field(af, "kind") or self.feature_kind_default
            if kind not in self.feature_kinds:
                self.err(
                    fmap["path"],
                    f"`kind: {kind}` is not a feature-map kind (allowed: {', '.join(sorted(self.feature_kinds))}); "
                    "omit it for a customer-facing area",
                )
            # The DURABLE link: a feature area is realised by one or more components.
            # `owning_projects:` still validates, but a slice is a *version*, so a map
            # pointing at one goes stale the moment the next version is cut. `components:`
            # is durable-to-durable and is what backward planning chains through.
            #
            # A `kind: substrate` map may declare `components: []`: some substrate is code
            # the product architecture deliberately does not draw, so forcing a component
            # would mean inventing one. The exemption is EXPLICIT, never implicit: a
            # customer-facing area with no component is still the filed defect.
            comps = self.component_ids()
            declared = listfield(af, "components")
            # A FEATURE WITH NO CODE YET (greenfield "New feature", 2026-11-01) names no component and no code path,
            # because there is none: `components: []` and `source_of_truth: []` TOGETHER, on a map no row of which
            # cites built work. The exemption is derived, never declared — the first row citing built work (a
            # `(core)`-style marker, or a PRD being built or shipped) holds the map to both, as every other map.
            unbuilt = (
                not declared
                and has_field(af, "source_of_truth")
                and not fmap["source_of_truth"]
                and _no_code_yet(fmap, pst)
            )
            if not declared and kind != "substrate" and not unbuilt:
                self.err(
                    fmap["path"],
                    "missing required frontmatter field `components` — a feature area must name the "
                    "component(s) that realise it (durable); `owning_projects` points at versions and drifts",
                )
            for c in declared:
                if c not in comps:
                    self.err(fmap["path"], f"components `{c}` does not resolve to a components.md entry")
            for op in listfield(af, "owning_projects"):
                if op not in projects:
                    self.err(fmap["path"], f"owning_projects `{op}` does not resolve to a project slug")
            # Navigate frontmatter + intent header (the audit spine): the links an auditor
            # follows without reading code — why it exists, its invariants, surfaces, code.
            if "> **Intent.**" not in fmap["body"]:
                self.err(
                    fmap["path"],
                    "missing `> **Intent.**` header (value-framed + falsifiable — see features/README.md)",
                )
            for req in ("specs", "surfaces", "source_of_truth"):
                if not has_field(af, req):
                    self.err(fmap["path"], f"missing required Navigate frontmatter field `{req}`")
            if has_field(af, "specs") and not listfield(af, "specs"):
                self.err(fmap["path"], "`specs` must be non-empty — every feature honors at least one invariant spec")
            for spec in listfield(af, "specs"):
                if not (self.k / self.specs_dir / spec).is_file():
                    self.err(fmap["path"], f"specs `{spec}` does not resolve to a knowledge/specs/ file")
            if has_field(af, "source_of_truth") and not fmap["source_of_truth"] and not unbuilt:
                self.err(fmap["path"], "`source_of_truth` must be non-empty — the freshness contract needs code paths")
            broad_ok = {s.rstrip("/") for s in listfield(af, "source_of_truth_broad_ok")}
            for sot in fmap["source_of_truth"]:
                stripped = sot.rstrip("/")
                if not (self.repo / stripped).exists():
                    self.err(fmap["path"], f"source_of_truth `{sot}` does not exist in the repo")
                if self.broad_source_root_re.match(stripped) and stripped not in broad_ok:
                    self.err(
                        fmap["path"],
                        f"source_of_truth `{sot}` is an application/package root — the freshness advisory "
                        "would fire on every unrelated change under it; narrow it to what this area actually "
                        "owns, or add it to `source_of_truth_broad_ok:` as a reviewed exception",
                    )
            # surfaces: resolve against the real route tables, same as a flow's surfaces —
            # this field is identical on both file kinds.
            for surf in listfield(af, "surfaces"):
                status = self._resolve_surface(surf, web_pool, admin_pool)
                if status == "dead":
                    self.err(
                        fmap["path"],
                        f"surfaces `{surf}` does not resolve to any route in main.tsx/App.tsx (dead or renamed)",
                    )
                elif status == "redirect":
                    self.note(
                        fmap["path"],
                        f"surfaces `{surf}` resolves only to a redirect route — "
                        "cite the real destination if one exists",
                    )
                elif status == "unknown-prefix":
                    self.err(
                        fmap["path"],
                        f"surfaces `{surf}` carries an unrecognised `<prefix>:` on a path-shaped citation",
                        hint="cite it as `web: …`/`admin: …` or a bare `/path`, or add the prefix to "
                        "`journeys_surface_skip_prefixes` if it names a non-route surface",
                    )
            # Rule A (first ratchet): a map with UI surfaces must declare at least one
            # frontend path in `source_of_truth:` — otherwise the freshness advisory and the
            # exhaustive-coverage check cannot see its UI substrate, a blind spot with a
            # green light on it. Maps that genuinely ride a generic surface declare
            # `surfaces: []` and are exempt; a map with real routes and no frontend path is
            # the filed defect. A row-level frontend path satisfies this the same as a
            # map-level one — a map may express its UI substrate entirely through row
            # attribution.
            row_sot = self._row_source_paths(fmap)
            all_sot = fmap["source_of_truth"] + [p for _cid, p in row_sot]
            if listfield(af, "surfaces") and not any(s.startswith("frontend/") for s in all_sot):
                self.err(
                    fmap["path"],
                    "map declares `surfaces:` but no `frontend/` path in `source_of_truth:` — a UI surface "
                    "needs a frontend path to be reconciled (ENG-5947)",
                )
            # A row's own `Source of truth` claim is validated exactly like a map-level one
            # — existence, and the same broad-root ratchet via the map's shared
            # `source_of_truth_broad_ok:` bypass.
            for cid, sot in row_sot:
                stripped = sot.rstrip("/")
                if not (self.repo / stripped).exists():
                    self.err(fmap["path"], f"{cid} source_of_truth `{sot}` does not exist in the repo")
                if self.broad_source_root_re.match(stripped) and stripped not in broad_ok:
                    self.err(
                        fmap["path"],
                        f"{cid} source_of_truth `{sot}` is an application/package root — narrow it to the "
                        "files this capability actually owns, or add it to `source_of_truth_broad_ok:` as a "
                        "reviewed exception",
                    )
            for cid, info in fmap["caps"].items():
                if cid in caps:
                    self.err(fmap["path"], f"duplicate capability id `{cid}` (also in {caps[cid][0]})")
                caps[cid] = (area, info)
                # Ships in: every 4-digit number must resolve to a PRD, and — if it does —
                # must not be `status: cancelled` (a cancelled PRD's `cancelled_reason`
                # re-homes its scope elsewhere; the map must follow).
                for num in self._ships_prds(fmap["path"], cid, info["ships"]):
                    if num not in prds:
                        self.err(fmap["path"], f"{cid} Ships-in `{num}` does not resolve to a PRD")
                    elif pst.get(num) == "cancelled":
                        self.err(
                            fmap["path"],
                            f"{cid} Ships-in `{num}` cites a cancelled PRD — "
                            "re-home onto the PRD's `cancelled_reason` successor(s)",
                        )
                # Tested by: backticked slugs must be real journeys
                for j in info["tested_journeys"]:
                    if j not in all_journey_ids:
                        self.err(fmap["path"], f"{cid} Tested-by `{j}` is not a known journey/flow")
                for t in info.get("tested_ext", []):
                    self._check_foreign_tester(fmap["path"], cid, t, primary=t == info.get("primary_ext"))
            for j in fmap["journeys"]:
                if j not in all_journey_ids:
                    self.err(fmap["path"], f"frontmatter journeys lists `{j}` which is not a known journey")
            # A feature map's free prose carries the same ship-state claim a `Status`
            # column or an AC disposition would (ENG-17142).
            self.check_prose_prd_state(fmap["path"], fmap["body"], pst, journey_owners)

        self.check_capability_ledger(caps)

        # --- goals: a program's `Requires` is the entry point of backward planning ---
        # A goal names WHAT IT NEEDS (feature areas, or capability ids where precision
        # matters); the components and the build order are derived from there, never listed
        # by hand.
        for prog in programs(self.k, own=self.corpora.own):
            for req in prog["requires"]:
                rref = parse_ref(req)
                if not self.corpora.is_local(rref):
                    # A root in ANOTHER corpus (`fleet:CAP-1408`): resolved there.
                    res = self.corpora.resolve(
                        rref, corpusref.CAPABILITY, where=f"{rel_to(self.repo, self.program_register)} {prog['id']}"
                    )
                    if res.is_error:
                        self.err(
                            self.program_register,
                            f"line {prog['line']}: `{prog['id']}` requires {res.message}",
                            line=int(prog["line"]),
                        )
                    continue
                req = rref.id
                if req not in features and req not in caps:
                    self.err(
                        self.program_register,
                        f"line {prog['line']}: `{prog['id']}` requires `{req}`, which resolves to neither a "
                        "feature area (knowledge/features/<area>.md) nor a capability id",
                        line=int(prog["line"]),
                    )

        # --- flows + maps: format, kind, id, resolution, AC dispositions ---
        def check_journey(d: dict[str, Any], want_kind: str, deps_field: str, deps_pool: set[str]) -> None:
            f, fm = d["path"], d["fm"]
            for req in ("id", "kind", "persona"):
                if not field(fm, req):
                    self.err(f, f"missing required frontmatter field `{req}`")
            if d["id"] and d["id"] != f.stem:
                self.err(f, f"id `{d['id']}` does not match filename `{f.stem}`")
            if d["kind"] and d["kind"] != want_kind:
                self.err(f, f"kind `{d['kind']}` should be `{want_kind}`")
            self._check_journey_sections(f, d["body"], want_kind)
            # surfaces (flows) / composes (maps)
            if want_kind == "flow" and not listfield(fm, "surfaces"):
                self.err(f, "flow missing `surfaces:`")
            for surf in listfield(fm, "surfaces"):
                status = self._resolve_surface(surf, web_pool, admin_pool)
                if status == "dead":
                    self.err(
                        f, f"surfaces `{surf}` does not resolve to any route in main.tsx/App.tsx (dead or renamed)"
                    )
                elif status == "redirect":
                    self.note(
                        f,
                        f"surfaces `{surf}` resolves only to a redirect route — "
                        "cite the real destination if one exists",
                    )
                elif status == "unknown-prefix":
                    self.err(
                        f,
                        f"surfaces `{surf}` carries an unrecognised `<prefix>:` on a path-shaped citation",
                        hint="cite it as `web: …`/`admin: …` or a bare `/path`, or add the prefix to "
                        "`journeys_surface_skip_prefixes` if it names a non-route surface",
                    )
            # depends_on_surfaces (flows only): a route this flow's ACs rely on but does
            # not own. Stricter than `surfaces:` above — a redirect here IS the retired-
            # dependency signal this field exists to catch, so it fails the commit rather
            # than only advising.
            if want_kind == "flow":
                for dep_surf in listfield(fm, "depends_on_surfaces"):
                    status = self._resolve_surface(dep_surf, web_pool, admin_pool)
                    if status == "dead":
                        self.err(
                            f,
                            f"depends_on_surfaces `{dep_surf}` does not resolve to any route in "
                            "main.tsx/App.tsx (dead or renamed)",
                        )
                    elif status == "redirect":
                        self.err(
                            f,
                            f"depends_on_surfaces `{dep_surf}` resolves only to a redirect route — "
                            "the depended-upon surface has been retired",
                        )
                    elif status == "unknown-prefix":
                        self.err(
                            f,
                            f"depends_on_surfaces `{dep_surf}` carries an unrecognised `<prefix>:` on a "
                            "path-shaped citation",
                            hint="cite it as `web: …`/`admin: …` or a bare `/path`, or add the prefix to "
                            "`journeys_surface_skip_prefixes` if it names a non-route surface",
                        )
            for dep in listfield(fm, deps_field):
                if dep not in deps_pool:
                    self.err(f, f"{deps_field} `{dep}` does not resolve to an existing flow/map")
            # owning PRD(s) — must resolve, and the link must be bidirectional: the owning
            # PRD's `journeys:` frontmatter must name this journey back.
            jid = field(fm, "id") or f.stem
            owners = [v for v in [field(fm, "owning_prd")] if v] + listfield(fm, "owning_prds")
            for v in owners:
                if v[:4] not in prds:
                    self.err(f, f"owning_prd `{v}` does not resolve to a PRD folder")
                elif jid not in pj.get(v[:4], set()):
                    self.err(
                        f,
                        f"owning PRD {v[:4]} does not list this journey in its `journeys:` frontmatter (one-way link)",
                    )
            # AC dispositions — read from EVERY acceptance-criteria section, not only the
            # exact `## Acceptance criteria` heading. A variant heading reached no check at
            # all (ENG-12154 class e).
            ac_lines = ac_sections(d["body"], self.ac_heading_re)
            for line in ac_lines:
                if AC_LINE_RE.match(line) and not any(t in line for t in self.dispositions):
                    self.err(
                        f,
                        f"acceptance-criterion line lacks a disposition tag {self.dispositions}: {line.strip()[:60]}",
                    )
            # A table-form AC row is an entry too: its Disposition column must carry a tag.
            for block in ac_table_blocks(ac_lines):
                if not any(t in block for t in self.dispositions):
                    self.err(
                        f,
                        f"acceptance-criterion table row lacks a disposition tag "
                        f"{self.dispositions}: {block.strip()[:60]}",
                    )
            blocks, loose = ac_partition(ac_lines)
            # Journey -> PRD half of the PRD↔journey edge: an AC's parenthesised PRD
            # citation must resolve to a PRD folder. The status cross-check below silently
            # skips an unresolvable number, so without this gate a dangling citation is
            # invisible to every machine gate (ENG-9450). UNCONDITIONAL — the dual-tag
            # exemption farther down spares a disposition judgement, not a broken link.
            # Read over EVERY unit of the section — tables, `###` headings and prose too — since
            # whether a citation resolves does not depend on which criterion it belongs to.
            for block in blocks + loose:
                for num in self._ac_cites(f, block, include_notes=True, resolve=True):
                    if num not in prds:
                        self.err(
                            f,
                            f"AC cites PRD {num} which does not resolve to a PRD folder "
                            f"(knowledge/{self.prds_dir}/NNNN-*/prd.md): {block.strip()[:80]}",
                        )
            # AC disposition vs owning-PRD ship-state: a `[dev]`-only AC citing a PRD whose
            # status isn't `shipped`, or an `[ext]`-only AC citing one that already has, is
            # disposition/citation drift. A line carrying both tags is an intentional partial
            # disposition — not checked. The citation is read in every spelling (multi-id
            # parens included, ENG-12154 class a) and the block's prose deferral is then
            # resolved against the same live `status:`, even when no disposition tag caught it.
            for block in blocks:
                # A tombstone (struck through, or a bold superseded/withdrawn marker) is not a
                # claim: neither its tag nor a deferral inside it speaks for the live product.
                if self._is_tombstone(block):
                    continue
                has_dev = "[dev]" in block
                has_ext = "[ext]" in block
                cites = self._ac_cites(f, block)
                flagged: set[str] = set()
                # A `[dev]` AC that defers to the very PRD it cites ("N/A until PRD NNNN
                # ships") already says it is not verifiable yet — honest, not drift. Only
                # that same PRD is excused, and the Defer arm below turns the row red the
                # moment it ships, so the skip opens no gap.
                deferred = set(self._deferral_cites(block)) if self.deferral_prd_re is not None else set()
                if has_dev != has_ext:
                    for num in cites:
                        st = pst.get(num)
                        if st is None:
                            continue
                        if has_dev and st != "shipped" and num not in deferred:
                            self.err(
                                f,
                                f"AC tagged `[dev]` cites PRD {num} (status: {st}, not shipped): {block.strip()[:80]}",
                            )
                            flagged.add(num)
                        if has_ext and st == "shipped":
                            self.err(f, f"AC tagged `[ext]` cites PRD {num} which has shipped: {block.strip()[:80]}")
                            flagged.add(num)
                    for ref_s, st in self._ac_foreign_states(block):
                        if has_dev and st != "shipped":
                            self.err(
                                f,
                                f"AC tagged `[dev]` cites PRD {ref_s} (status: {st}, not shipped): "
                                f"{block.strip()[:80]}",
                            )
                        if has_ext and st == "shipped":
                            self.err(f, f"AC tagged `[ext]` cites PRD {ref_s} which has shipped: {block.strip()[:80]}")
                # A row that says its criterion is deferred for a PRD that has already
                # shipped is stale prose regardless of which tag it carries — an
                # "N/A until PRD NNNN ships" line read as fact when the PRD shipped is
                # exactly the class the freshness gate could not see (ENG-12154 class a).
                if self.deferral_prd_re is not None:
                    for num in self._deferral_cites(block):
                        if num in flagged:
                            continue
                        if pst.get(num) == "shipped":
                            self.err(
                                f,
                                f"AC defers to PRD {num}, which has already shipped — "
                                f"the deferral is stale; ship-state is the PRD's to state: {block.strip()[:80]}",
                            )
            # Reverse (doc -> code) liveness: an AC in a LIVE flow/map that cites a
            # capability the map explicitly marks retired is stale prose unless it owns
            # the retirement. Nothing else watches the reverse arrow: `source_of_truth` path
            # existence only fires on paths still declared, and anchors are opt-in — so
            # prose could (and did) keep asserting a capability the code behind it was
            # deleted. A whole flow/map marked retired is a historical record and is exempt:
            # there, citing retired capabilities is the point, not the defect.
            flow_is_retired = (field(fm, "status") or "").strip().lower() == "retired" or bool(
                re.search(r"^>\s*\*\*retired", d["body"], re.M | re.I)
            )
            if not flow_is_retired:
                # Every unit, like the dangling leg: a retired capability in a table row or a
                # heading is as stale as one in a numbered entry; the acknowledgement is read
                # from the same unit (the row, the heading, the paragraph, or the entry).
                for block in blocks + loose:
                    for cid in self.cap_ref_re.findall(block):
                        cinfo = caps.get(cid)
                        if cinfo is None:
                            continue
                        ships = cinfo[1]["ships"].strip()
                        marker = next((m for m in self.retirement_markers if ships.startswith(m)), None)
                        if marker is None:
                            continue
                        if self.retire_ack_re is not None and self.retire_ack_re.search(block):
                            continue
                        self.err(
                            f,
                            f"AC cites retired capability {cid} (`Ships in: {marker}`) without acknowledging "
                            f"the retirement — annotate the row as withdrawn, or drop the citation: "
                            f"{block.strip()[:80]}",
                        )
            # Claim-vs-tree (ENG-12201): permission names resolve; absence claims stay absent.
            # The permission leg is attribution-free, so it reads every unit. The absence leg
            # reads numbered entries only: a table row's absence cue is scoped to one cell's
            # noun, and reading rows as claims is a follow-up, not a bound this check has.
            self.check_ac_permission_names(f, blocks + loose)
            self.check_ac_absent_components(f, blocks)
            # SSoT: no authored ship-state in a journey map.
            if "[unshipped]" in d["body"]:
                self.err(
                    f,
                    "the `[unshipped]` disposition is retired — read ship-state from the AC's "
                    "owning PRD frontmatter `status:` (tag the verification surface with `[dev]`/`[ext]`)",
                )
            for g in self.banned_emoji:
                if g in d["body"]:
                    self.err(
                        f,
                        f"ship-state marker `{g}` is banned in journeys — "
                        "read ship-state from the linked PRD's frontmatter `status:`",
                    )
                    break
            # covers -> capability resolution + reverse two-way link
            for cid in d["covers"]:
                cref = parse_ref(cid)
                if not self.corpora.is_local(cref):
                    self._check_foreign_cover(f, d["id"], cref)
                    continue
                cid = cref.id
                if cid not in caps:
                    self.err(f, f"covers `{cid}` is not a defined capability (knowledge/features/*)")
                elif d["id"] not in caps[cid][1]["tested_journeys"]:
                    self.err(f, f"two-way: covers `{cid}` but `{cid}`'s Tested-by does not list `{d['id']}`")
            # A flow/map's free prose carries the same ship-state claim (ENG-17142).
            self.check_prose_prd_state(f, d["body"], pst, journey_owners)

        for d in flows.values():
            check_journey(d, "flow", "used_by", set(maps))
        for d in maps.values():
            check_journey(d, "journey", "composes", all_journey_ids)

        # --- composes/used_by: the two authored directions of one edge must agree ---
        self.check_composes_used_by(flows, maps)

        # --- forward two-way: a capability's primary tester must cover it ---
        for _area, fmap in features.items():
            jl = set(fmap["journeys"])
            for cid, info in fmap["caps"].items():
                p = info["primary"]
                if p and p in jl:  # in-area primary → must back-reference
                    jd = flows.get(p) or maps.get(p)
                    jcov = jd["covers"] if jd else []
                    if cid not in jcov:
                        self.err(fmap["path"], f"two-way: {cid} Tested-by `{p}` but `{p}`'s covers lacks `{cid}`")

        # --- index completeness ---
        jindex = self.k / self.journeys_dir / "README.md"
        jr = jindex.read_text(encoding="utf-8") if jindex.is_file() else ""
        for fid in flows:
            if f"{self.flows_subdir}/{fid}.md" not in jr:
                self.err(jindex, f"flow `{fid}` is not listed in the journeys index")
        for mid in maps:
            if f"{self.maps_subdir}/{mid}.md" not in jr:
                self.err(jindex, f"map `{mid}` is not listed in the journeys index")
        findex = self.k / self.features_dir / "README.md"
        fr = findex.read_text(encoding="utf-8") if findex.is_file() else ""
        for area in features:
            if f"{area}.md" not in fr:
                self.err(findex, f"feature map `{area}` is not listed in the features index")

        # advisory (non-failing): a capability with no PRD and no journey is a requirement
        # with no home — surfaced for the reconcile/audit passes, not a commit blocker.
        orphans = sorted(
            cid
            for cid, (_a, info) in caps.items()
            if info["ships"].strip() in ("—", "-", "") and not info["tested_journeys"] and not info.get("tested_ext")
        )
        self.orphans = orphans
        if orphans:
            shown = ", ".join(orphans[:20]) + (" …" if len(orphans) > 20 else "")
            self.report.findings.append(
                Finding(
                    level="advisory",
                    message=(
                        f"{len(orphans)} capability(ies) with no PRD and no journey "
                        f"(a requirement with no home): {shown}"
                    ),
                    hint="Give each one a delivering PRD in `Ships in`, or a journey in `Tested by`.",
                )
            )

        self.check_anchors(features)
        self.check_anchor_source_of_truth(features)
        self.check_capability_needs(features, self.prd_projects())
        self.check_source_coverage(features)
        self.check_covers_shrink({**flows, **maps}, set(caps))
        self.check_prose_named_paths(features)
        self._check_ratchet(self.baseline_rel, "baseline grew", self.write_baseline_command)
        self.check_markdown_table_shape()
        # Never a silent pass: every reference into a declared corpus that is not on disk here
        # is counted and named, once.
        if unverified := self.corpora.summary():
            self.report.raw_note(unverified)

        self.counts = {
            "flows": len(flows),
            "maps": len(maps),
            "features": len(features),
            "caps": len(caps),
        }
        return self.report

    # -- baseline regeneration ----------------------------------------------------
    def write_baseline(self) -> int:
        """Regenerate the unclaimed baseline from the current unclaimed set.

        Run by a human/reviewer when the debt picture genuinely changes; the ratchet then
        refuses to let it *grow* on a later change.

        Once the gate is ABSOLUTE (ENG-12738) a missing baseline is zero acknowledged debt,
        so this refuses to re-seed one: a non-empty unclaimed set is an error, not a debt
        list to launder into a fresh baseline, and a zero set leaves the file absent. The
        refusal is what keeps "no committed baseline" meaning "no acknowledged debt" rather
        than reopening the grandfather hole the burn-down closed."""
        features = self.load_feature_maps()
        unclaimed = self.unclaimed_paths(features)
        bl = self.repo / self.baseline_rel
        if not bl.is_file():
            if unclaimed:
                print(
                    f"unclaimed coverage: {len(unclaimed)} code path(s) are covered by no feature "
                    f"map's `source_of_truth:` — refusing to re-seed {self.baseline_rel} (the gate is "
                    "absolute after ENG-12738). Claim each in the owning feature map:\n"
                    + "".join(f"  - {p}\n" for p in unclaimed[:60]),
                    file=sys.stderr,
                )
                if len(unclaimed) > 60:
                    print(f"  ...and {len(unclaimed) - 60} more", file=sys.stderr)
                return 1
            print(f"coverage is absolute — 0 unclaimed; {self.baseline_rel} absent")
            return 0
        bl.parent.mkdir(parents=True, exist_ok=True)
        bl.write_text(
            f"# Generated by: {self.write_baseline_command}\n"
            "# Every line is a code path that no feature map's `source_of_truth:` claims (acknowledged debt).\n"
            "# Burn debt down by claiming the path in a feature map and removing the line here. The baseline\n"
            "# may shrink, never grow: a NEW line is refused unless a `# ack: <path> <reason>` line names it.\n"
            + "".join(f"{p}\n" for p in unclaimed),
            encoding="utf-8",
        )
        print(f"wrote {len(unclaimed)} unclaimed paths to {self.baseline_rel}")
        return 0


# --------------------------------------------------------------------------------------
# Check
# --------------------------------------------------------------------------------------
class JourneysCheck:
    name = "journeys-and-features"
    title = "Journeys & capability maps"
    description = (
        "The product-facing decomposition and its links: capability ids allocated once and never "
        "reused, the `Needs` dependency graph acyclic, `Ships in` resolving to real PRDs, the "
        "PRD↔journey reference edge resolving in BOTH directions (a PRD's `journeys:` entries to "
        "journey files; every AC section's parenthesised PRD citations to PRD folders), journey "
        "`covers:` and capability `Tested by` agreeing in BOTH directions, a map's `composes:` and a "
        "flow's `used_by:` agreeing in BOTH directions (an edge declared on either side must be "
        "declared on the other), every AC disposition and "
        "deferral agreeing with the cited PRD's live `status:` (a cite hidden in a multi-id paren is "
        "read too, and an `N/A until PRD NNNN ships` row for a shipped PRD fails), declared surfaces "
        "resolving to real routes, every code path under a covered root claimed by some map's "
        "`source_of_truth:` or named in the ratcheted baseline (the gate is absolute once that "
        "baseline is retired), AC permission tokens resolving "
        "against the permissions contract, and AC absence claims not naming a testid or component "
        "the shipped frontend still mounts. A map/journey PROSE line that asserts a PRD lifecycle "
        "state (`implementing`, `planned`, …) contradicting the linked PRD's own `status:` fails too "
        "(ENG-17142) — whether it names the PRD directly or only a flow resolved through its "
        "`owning_prd:`, and whether the state word sits before or after the reference; the claim a "
        "stale Gaps bullet or blockquote carries is the one the AC legs "
        "already refuse. Ship-state is never asserted here — it is read from the "
        "linked PRD, so a map cannot go stale by claiming something is built."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        # `journeys_dir = ""` / `features_dir = ""` is a project declaring it has neither, and
        # the empty name must not resolve to the knowledge directory — which IS a directory,
        # so the bare join would answer "applies" for every corpus that opted out.
        v = JourneysValidator(kb)
        return any(rel and (v.k / rel).is_dir() for rel in (v.journeys_dir, v.features_dir))

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        return JourneysValidator(kb).run().findings


CHECK = JourneysCheck()


# --------------------------------------------------------------------------------------
# Legacy entry point — byte-identical stdout and exit codes
# --------------------------------------------------------------------------------------
def report_legacy(v: JourneysValidator, report: Reporter) -> int:
    """Print the standalone validator's stdout and return its exit code.

    Kept separate from `main()` so the tests can drive one validator run and assert on
    the structured report AND the printed text without running the corpus twice.
    """
    if v.orphans:
        shown = ", ".join(v.orphans[:20]) + (" …" if len(v.orphans) > 20 else "")
        print(
            f"advisory — {len(v.orphans)} capability(ies) with no PRD and no journey "
            f"(a requirement with no home): {shown}"
        )
    # advisory (non-failing): a surface that resolves only to a redirect route.
    # Some redirects are an intentional dual entry point, not drift — so this is
    # surfaced, not blocked.
    if report.notices:
        print(f"advisory — {len(report.notices)} note(s):")
        for n in report.notices:
            print(f"- {n}")
    if report.errors:
        print("journey / feature-map validation failed:")
        for e in report.errors:
            print(f"- {e}")
        return 1
    c = v.counts
    print(
        f"journeys OK — {c['flows']} flows, {c['maps']} maps, {c['features']} feature maps, "
        f"{c['caps']} capabilities; links consistent"
    )
    return 0


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    v = JourneysValidator(local_kb(root if root is not None else Path.cwd()))
    if "--write-baseline" in args:
        return v.write_baseline()
    return report_legacy(v, v.run())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
