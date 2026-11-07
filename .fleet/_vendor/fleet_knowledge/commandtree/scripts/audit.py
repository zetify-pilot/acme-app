#!/usr/bin/env python3
"""Dispatch product audits to the fleet — the scheduling half of the audit program.

**What this replaces.** `audit <type> [scope]` takes a free-text `scope`, so a
run's subject is a sentence: five `ux` records on disk carry `scope:` fields that are
paragraphs, one of them six lines long. A sentence cannot be validated, deduplicated,
sized, or counted — which is why finding the never-audited journeys once meant reading
79 prior records and counting occurrences.

Here the subject is an **ID that already exists in the knowledge base**, and everything
else is derived from it:

  unit   — a feature area (`knowledge/features/<area>.md`, or its `.md.tmpl` shell).
           Authored, and REJECTED if it does not resolve. The valid set is the folder; there
           is no second list.
           `family:<name>` names a GROUP of areas — the product grouping authored in the
           `Family` column of `knowledge/audits/feature-coverage-ledger.md` — and expands
           to its members, so "audit everything agent-related" is one word.
  lens   — an audit type, i.e. a checklist (`knowledge/specs/<lens>-audit-checklist.md`).
           Authored. The valid set is that glob.
  scope  — DERIVED. The map's frontmatter already declares `journeys:`, `surfaces:`,
           `source_of_truth:` and `components:`, and its body carries the `> **Intent.**`
           clause. The lens selects which edge it follows; nobody writes a scope.

**Why a script and not a slash command.** Everything here is mechanical — resolve names,
reject typos, render a brief, POST it. Spending an agent session to do that is pure
overhead. `audit` stays for the part that genuinely needs judgment: running one
audit against the live product.

Usage:

    python3 knowledge/scripts/audit.py areas                      # what can be dispatched (+ families)
    python3 knowledge/scripts/audit.py brief agents --lens ux     # render the issue, touch nothing
    python3 knowledge/scripts/audit.py dispatch agents connections --lens ux,ui
    python3 knowledge/scripts/audit.py dispatch family:agents --lens feature   # a whole family
    python3 knowledge/scripts/audit.py dispatch agents --lens ux --apply
    python3 knowledge/scripts/audit.py due                        # every typed part whose Tier is due

`dispatch` is a **dry run by default** — it prints exactly what it would file and exits
non-zero on any validation failure. It is a DRY RUN: the fleet files through its own tools,
because this mints work for the fleet and that should never be one typo away.

`due` is the part rotation (FLT-1170). Every typed part — a feature area, a component, a
connector and a customer's own system — carries an authored `Tier` (`core`/`rotation`/`parked`,
blank = untiered); `due` selects the ones whose tier's max age has passed (3 days / 14 days /
never), reports a parked part with its reason and an untiered part by name, and never declares a
schedule of its own — re-tier a part and its cadence self-corrects.
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import glob
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _repo  # noqa: E402

REPO = str(_repo.repo_root())
FEATURES = os.path.join(REPO, "knowledge", "features")
SPECS = os.path.join(REPO, "knowledge", "specs")
JOURNEYS = os.path.join(REPO, "knowledge", "journeys")
LEDGER = os.path.join(REPO, "knowledge", "audits", "feature-coverage-ledger.md")

# ---------------------------------------------------------------------------
# The one thing not derivable from the knowledge base: which edge of a feature
# map each lens follows. The checklists' `## Audit profile` blocks name an `atom`
# ("one journey", "one route/surface", "one OpenAPI operation") but only as prose,
# so it cannot be read mechanically today.
#
# This table is the interim home. The audit-program restructure moves it into each
# checklist's Audit profile as a machine-readable `unit:` field, at which point this
# dict is deleted and derived instead. Until then it is 12 explicit lines in one
# greppable place rather than a rule restated across ten specs.
#
#   value = the feature-map frontmatter field the lens reads, or None when the lens
#           reads the map's body (Intent + capability rows) and so always applies.
#
# Only lenses that HAVE a checklist belong here. `audit`'s option table also
# lists `performance` and `accessibility`, but neither has a checklist yet, and the
# command's own rule is that the first audit of a type authors one before it runs.
# Naming them here would render two columns nobody can dispatch — `audit_test.py`
# pins that direction (every LENS_EDGE key must resolve to a real checklist).
# ---------------------------------------------------------------------------
LENS_EDGE: dict[str, str | None] = {
    "ux": "journeys",
    "ui": "surfaces",
    "feature": None,
    "security": "source_of_truth",
    "authz": "source_of_truth",
    "api": "source_of_truth",
    "architecture": "source_of_truth",
    "evidence": "source_of_truth",
    "eval": "source_of_truth",
}

# Tracker issue priority per lens (1=Urgent 2=High 3=Medium 4=Low).
#
# Required, not cosmetic: `tracker_labels.requires_priority()` exempts only `Type:idea`
# and `to-be-checked`, so a `Type:audit` issue filed at priority 0 is refused
# ("every process MUST set one"). This is NOT the rule that a finding's priority
# belongs to `check` — that governs the issues an audit FILES, never the work
# order that runs one.
#
# Weights are the audits README's post-ship table (*Which types the issue must carry*),
# which is the only place the program has ever ranked its own types; anything it does not
# rank takes the board's Medium default rather than a number invented here.
# `ux` is High, not Low. The post-ship table ranked it Low when the only question was
# "how much does a shipped PRD still owe"; as a standing sweep it is the highest-yield
# lens we have. Measured 2026-08-16: ux 6 findings / 8 runs (0.75) against feature's
# 0.2, and its findings were the ones a customer hits first — "file attach always fails
# with 400". Owner's standing judgement agrees: ux is where the bugs are.
#
# MEDIUM IS THE FLOOR — an audit is never filed at Low (4). The daemon claims strictly by
# priority, and arriving bugs land at High/Medium continuously, so a Low audit loses every
# dispatch contest it ever enters: measured 2026-08-17, all 32 audits filed at Low were
# still unstarted ~10h later behind a 69-deep queue, while every Medium sibling had run.
# Low is not "later" here, it is "never", so the scale's bottom rung is not ours to use.
# `enforce_priority_floor()` is the single gate — `--priority 4` is refused there too.
LENS_PRIORITY: dict[str, int] = {
    "ux": 2,
    "security": 3,
    "authz": 3,
    "api": 3,
    "ui": 3,
}
DEFAULT_LENS_PRIORITY = 3  # Medium — the same default the PRD projection gives an unranked issue
PRIORITY_FLOOR = 3  # Medium. Nothing this script files may sort below it — see above.


def enforce_priority_floor(priority: int | None, lens: str) -> int:
    """The dispatch priority for `lens`, clamped to `PRIORITY_FLOOR`.

    `None` means the caller passed no `--priority`, so the lens weight applies. A caller
    that explicitly asks for Low is clamped rather than refused: the request is to run the
    audit, and the only thing Low would change is that it never runs. Priority 0 ("No
    priority" in the tracker, not Urgent) sorts below Low and is clamped for the same reason.
    """
    chosen = LENS_PRIORITY.get(lens, DEFAULT_LENS_PRIORITY) if priority is None else priority
    if chosen == 0 or chosen > PRIORITY_FLOOR:
        return PRIORITY_FLOOR
    return chosen


# What the derived scope is called in the brief, per edge.
EDGE_LABEL = {
    "journeys": "Journeys to walk (acceptance criteria are the test list)",
    "surfaces": "Routes to render",
    "source_of_truth": "Code in scope",
}


# ---------------------------------------------------------------------------
# Knowledge-base readers
# ---------------------------------------------------------------------------
def frontmatter(text: str) -> str:
    """The frontmatter block, or '' when the file has none.

    Mirrors `validate_journeys.frontmatter`. Kept local rather than imported: a
    dispatch tool should not take a build dependency on a pre-commit validator.
    """
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 else ""


def listfield(fm: str, name: str) -> list[str]:
    """A frontmatter list, inline (`name: [a, b]`) or block (`name:` then `  - a` lines).

    Deliberately regex, not YAML: 14 of the 45 maps do not parse as YAML because route
    parameters go unquoted (`surfaces: [/agents/{id}]` — `{` opens a flow mapping). The
    repo's own `validate_journeys` reads them the same tolerant way, so this matches the
    corpus as it actually is rather than as it should be. Quoting them is a precondition
    tracked separately; until then a strict parser would silently drop a third of the
    catalog, which is the worst possible failure for an exhaustiveness tool.

    The block form is a feature map's `source_of_truth`, now one path per line,
    sorted; both spellings are read so a mid-flight branch is not read as claiming nothing.
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


def field(fm: str, name: str) -> str:
    m = re.search(rf"^{name}:\s*(.+)$", fm, re.M)
    return m.group(1).strip().strip('"').strip("'") if m else ""


INTENT_RE = re.compile(r"^>\s*\*\*Intent\.\*\*\s*(.*?)(?=\n(?!\s*>)|\Z)", re.M | re.S)


def intent(text: str) -> str:
    """The map's `> **Intent.**` blockquote as one paragraph, or ''.

    This is the bar the `feature` lens grades against — the clause a capability can pass
    row by row while still failing as a whole. Same extraction as the feature area's
    tracker project description (`fleet_knowledge.corpus.area_description`), but
    unabridged: the tracker *project* description is capped at 255 chars, an audit
    brief is not.
    """
    m = INTENT_RE.search(text)
    if not m:
        return ""
    return " ".join(ln.strip().lstrip(">").strip() for ln in m.group(1).splitlines() if ln.strip(" >"))


def title_of(text: str, fallback: str) -> str:
    """The area's display name — the map H1 with the ` — Capability Map` suffix removed."""
    m = re.search(r"^#\s+(.+)$", text, re.M)
    name = m.group(1).strip() if m else fallback
    suffix = " — Capability Map"
    if name.endswith(suffix):
        name = name[: -len(suffix)].strip()
    return name or fallback


#: A feature map whose `<area>.md` is a generated, gitignored artifact keeps its prose and
#: frontmatter in a committed shell, `<area>.md.tmpl`, rendered on demand by the shipped
#: `knowledge/scripts/gen_knowledge_fragments.py`. Same suffix, same rule as its `Corpus.feature_maps()`.
SHELL_SUFFIX = ".tmpl"


def feature_map_paths() -> list[str]:
    """Every feature map's readable source, one per area, sorted by map name.

    The area set is the union of `<area>.md` and `<area>.md.tmpl` — the shipped renderer's
    own discovery rule (`gen_knowledge_fragments.Corpus.feature_maps`: "an untracked map is still
    discovered through its committed shell"), so the two can never disagree about which areas
    exist. An unrendered checkout has only the shell; when both exist the rendered map wins,
    because it is the shell plus the generated rows.
    """
    names = {os.path.basename(p) for p in glob.glob(os.path.join(FEATURES, "*.md"))}
    names |= {
        os.path.basename(p)[: -len(SHELL_SUFFIX)] for p in glob.glob(os.path.join(FEATURES, f"*.md{SHELL_SUFFIX}"))
    }
    out: list[str] = []
    for name in sorted(names):
        rendered = os.path.join(FEATURES, name)
        out.append(rendered if os.path.isfile(rendered) else rendered + SHELL_SUFFIX)
    return out


def areas() -> dict[str, dict[str, Any]]:
    """`{slug -> {slug, name, path, intent, journeys, surfaces, source_of_truth, components}}`.

    The valid area set IS `feature_map_paths()`. Adding a feature map (or its shell) makes the
    area auditable with no second registration; there is nothing to keep in sync.
    """
    out: dict[str, dict[str, Any]] = {}
    for path in feature_map_paths():
        stem = os.path.basename(path).removesuffix(SHELL_SUFFIX)[:-3]
        if stem == "README" or stem.startswith("_"):
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        fm = frontmatter(text)
        slug = field(fm, "area") or stem
        out[slug] = {
            "slug": slug,
            "name": title_of(text, slug),
            "path": os.path.relpath(path, REPO),
            "intent": intent(text),
            "journeys": listfield(fm, "journeys"),
            "surfaces": listfield(fm, "surfaces"),
            "source_of_truth": listfield(fm, "source_of_truth"),
            "components": listfield(fm, "components"),
        }
    return out


# ---------------------------------------------------------------------------
# Families — the PRODUCT grouping of feature areas
#
# The 45 areas are a flat set, and the only grouping anything derives is structural:
# an area's `components:` → their `layer` in the component registry. That is a real
# grouping and it is not the one a person reasons in — the ten areas anyone would call
# "agent related" land in SEVEN different layers, so "audit all agent-related areas" was
# not expressible at all.
#
# `Family` is that second axis. It is authored in ONE place — the `Family` column of
# knowledge/audits/feature-coverage-ledger.md, next to `Tier`, under the same
# human-writes-it-and-no-run-does rule — and read here. Multi-valued (comma-separated),
# because ~11 areas honestly sit in two at once; a filename prefix cannot express that,
# which is one of the two reasons renaming the maps was rejected (the other: past runs
# stamped `unit-key: <lens>/<area-slug>` into tracker issue bodies, outside git and
# unmigratable, so a rename breaks the dedup key of every historical finding).
#
# The closed vocabulary is NOT restated here: `validate_knowledge_hygiene.py` owns it
# (FEATURE_FAMILIES) and fails the commit on an unknown word or a family holding fewer
# than two areas. This function reads whatever the ledger says, so a family the human
# adds there is dispatchable the same minute — and a typo is caught by the validator
# rather than silently becoming a one-area scope.
# ---------------------------------------------------------------------------
FAMILY_PREFIX = "family:"
_LEDGER_ROW_RE = re.compile(r"^\|\s*`([a-z0-9-]+)`\s*\|([^|\n]*)\|([^|\n]*)\|[^|\n]*\|[^|\n]*\|", re.M)


def families(path: str | None = None) -> dict[str, list[str]]:
    """`{family -> [area slug]}` from the coverage ledger's `Family` column, in table order.

    Table order, not sorted: the ledger is alphabetical by area, so a family's members come
    out in the order a reader of that file would list them, and a dispatch batch is
    reproducible run to run.
    """
    out: dict[str, list[str]] = {}
    try:
        with open(path or LEDGER, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return out
    for slug, family_cell, _tier in _LEDGER_ROW_RE.findall(text):
        for fam in (x.strip() for x in family_cell.split(",")):
            if fam and slug not in out.setdefault(fam, []):
                out[fam].append(slug)
    return out


def lenses() -> list[str]:
    """Every audit type that has a checklist. The checklist is what makes a lens runnable,
    so its existence is the definition — not a hardcoded type list that can drift from it."""
    out = []
    for path in sorted(glob.glob(os.path.join(SPECS, "*-audit-checklist.md"))):
        out.append(os.path.basename(path)[: -len("-audit-checklist.md")])
    return out


# ---------------------------------------------------------------------------
# Validation — reject, never guess
# ---------------------------------------------------------------------------
class InvalidNameError(Exception):
    """A name that does not resolve. Carries the suggestion, so the caller prints once."""


def resolve_areas(
    names: list[str], known: dict[str, dict[str, Any]], fams: dict[str, list[str]] | None = None
) -> list[dict[str, Any]]:
    """Resolve a scope list to area records. A name is either an area slug or `family:<name>`.

    A family expands to its member rows in ledger order, so one word covers the ten-odd
    areas a person means by "agent related". Expansion is deduplicated ACROSS the whole
    list — `family:agents agents` and two overlapping families each dispatch an area once,
    never twice; a doubled area would file a duplicate audit issue per lens.

    Unknown names are REJECTED, never guessed, on both axes: a typo'd family that silently
    resolved to nothing would report a clean sweep of an empty set.
    """
    fams = families() if fams is None else fams
    bad: list[str] = []
    ordered: list[str] = []
    for n in names:
        if n.startswith(FAMILY_PREFIX):
            fam = n[len(FAMILY_PREFIX) :]
            if fam not in fams:
                near = difflib.get_close_matches(fam, sorted(fams), n=3, cutoff=0.6)
                hint = f" — did you mean family:{', family:'.join(near)}?" if near else ""
                bad.append(f"  {n!r} is not a family{hint}")
                continue
            for slug in fams[fam]:
                if slug not in known:
                    bad.append(
                        f"  family {fam!r} names `{slug}`, which is not a feature area — the "
                        "coverage ledger has a stale row"
                    )
                elif slug not in ordered:
                    ordered.append(slug)
            continue
        if n not in known:
            near = difflib.get_close_matches(n, sorted(known), n=3, cutoff=0.6)
            hint = f" — did you mean {', '.join(near)}?" if near else ""
            bad.append(f"  {n!r} is not a feature area{hint}")
        elif n not in ordered:
            ordered.append(n)
    if bad:
        raise InvalidNameError(
            "unknown scope(s):\n"
            + "\n".join(bad)
            + f"\n\n{len(known)} valid areas (from knowledge/features/*.md and *.md.tmpl):\n  "
            + "\n  ".join(sorted(known))
            + f"\n\n{len(fams)} valid families (from the Family column of "
            + "knowledge/audits/feature-coverage-ledger.md):\n  "
            + "\n  ".join(f"family:{f} ({len(fams[f])} areas)" for f in sorted(fams))
        )
    return [known[n] for n in ordered]


def resolve_lenses(names: list[str]) -> list[str]:
    known = lenses()
    bad = []
    for n in names:
        if n not in known:
            near = difflib.get_close_matches(n, known, n=3, cutoff=0.6)
            hint = f" — did you mean {', '.join(near)}?" if near else ""
            bad.append(f"  {n!r} has no checklist{hint}")
        elif n not in LENS_EDGE:
            bad.append(
                f"  {n!r} has a checklist but no entry in LENS_EDGE — add one (see this file's header) "
                "so the brief knows which edge of the feature map it reads"
            )
    if bad:
        raise InvalidNameError(
            "unknown lens(es):\n"
            + "\n".join(bad)
            + "\n\nvalid lenses (from knowledge/specs/*-audit-checklist.md):\n  "
            + "\n  ".join(known)
        )
    return names


# ---------------------------------------------------------------------------
# Journey ownership — exactly one area walks each journey
# ---------------------------------------------------------------------------
# 20 of the 81 referenced journeys are listed by MORE THAN ONE feature map, so
# dispatching those areas together sends two agents down the same flow. That is not
# theoretical: (`ux/retrieval`) and (`ux/agent-tools-mcp`) are the same
# defect, filed minutes apart, both walking `upload-and-ask` AC2. One was closed as a
# Duplicate — a wasted fleet slot, a wasted triage, and a second record claiming coverage
# of ground already covered.
#
# `unit-key` cannot catch this: it is `ux/<area>`, and the two runs ARE different units.
# The collision is at the *journey*, so the fix has to be there too.
#
# Ownership is DERIVED, not a new registry to author. A journey's frontmatter already
# declares `covers:` — the capability IDs it exercises — and every capability ID belongs
# to exactly one feature map's capability table. So the area contributing the most covered
# capabilities is the journey's natural owner, and the answer is grounded in authored data
# rather than invented: `upload-and-ask` covers 3 `agent-tools-mcp` caps, 2 `retrieval`,
# 1 `agents` — and agent-tools-mcp is indeed where file-attach-through-the-tool-surface
# belongs. 16 of the 20 resolve with a clear winner this way.
#
# Two escape hatches, in precedence order:
#   1. `audit_owner: <area>` in the journey's own frontmatter — the human override, and
#      the only thing that settles a genuine tie.
#   2. A tie with no override falls to the alphabetically-first claimant and is REPORTED,
#      never silently resolved. Coverage must not drop just because ownership is unclear:
#      dropping the journey from every claimant would be a silent hole, which is the one
#      failure this whole tool exists to prevent.
_cap_owner: dict[str, str] | None = None


def capability_owner() -> dict[str, str]:
    """`{capability id -> area slug}` from every feature map's capability tables.

    First declaration wins. A capability ID appearing in two maps is itself a defect, but
    it is `validate_journeys`' to report — this tool must not fail on it.
    """
    global _cap_owner
    if _cap_owner is None:
        _cap_owner = {}
        for path in sorted(glob.glob(os.path.join(FEATURES, "*.md"))):
            stem = os.path.basename(path)[:-3]
            if stem == "README" or stem.startswith("_"):
                continue
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            slug = field(frontmatter(text), "area") or stem
            for m in re.finditer(r"^\|\s*(CAP-\d{4})\s*\|", text, re.M):
                _cap_owner.setdefault(m.group(1), slug)
    return _cap_owner


def journey_path(jid: str) -> str | None:
    for sub in ("flows", "maps"):
        p = os.path.join(JOURNEYS, sub, f"{jid}.md")
        if os.path.isfile(p):
            return p
    return None


def journey_owner(jid: str, claimants: list[str]) -> tuple[str, bool]:
    """`(owning area, was_a_tie)` for one journey among the areas that list it."""
    if len(claimants) == 1:
        return claimants[0], False
    path = journey_path(jid)
    if path:
        with open(path, encoding="utf-8") as fh:
            fm = frontmatter(fh.read())
        declared = field(fm, "audit_owner")
        if declared and declared in claimants:
            return declared, False
        tally: dict[str, int] = {}
        owner = capability_owner()
        for cap in listfield(fm, "covers"):
            a2 = owner.get(cap)
            if a2 in claimants:
                tally[a2] = tally.get(a2, 0) + 1
        if tally:
            best = max(tally.values())
            winners = sorted(k for k, v in tally.items() if v == best)
            return winners[0], len(winners) > 1
    return sorted(claimants)[0], True


def journey_claims(known: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """`{journey id -> the areas listing it}`."""
    out: dict[str, list[str]] = {}
    for slug, d in known.items():
        for j in d["journeys"]:
            out.setdefault(j, []).append(slug)
    return out


def owned_journeys(area: dict[str, Any], known: dict[str, dict[str, Any]]) -> tuple[list[str], list[str], list[str]]:
    """`(owned, referenced_elsewhere, ties)` for this area's journey list."""
    claims = journey_claims(known)
    owned, elsewhere, ties = [], [], []
    for j in area["journeys"]:
        who, tie = journey_owner(j, claims.get(j, [area["slug"]]))
        if who == area["slug"]:
            owned.append(j)
            if tie:
                ties.append(j)
        else:
            elsewhere.append(f"{j} → {who}")
    return owned, elsewhere, ties


def applicable(area: dict[str, Any], lens: str, known: dict[str, dict[str, Any]] | None = None) -> str:
    """'' when this (area, lens) pair is dispatchable, else why it is not.

    A pair is refused rather than filed with an empty scope: `ux` over an area with no
    `journeys:` would dispatch an agent to walk nothing, and it would come back with a
    clean record that means the opposite of what it says.
    """
    edge = LENS_EDGE[lens]
    if edge is None:
        return ""
    if not area[edge]:
        return f"map declares no `{edge}:` — nothing for the {lens} lens to read"
    if edge == "journeys":
        owned, elsewhere, _ = owned_journeys(area, known if known is not None else areas())
        if not owned:
            return (
                f"every journey it lists is owned by another area ({', '.join(elsewhere)}) — "
                "walking them here would duplicate that area's run"
            )
    return ""


# ---------------------------------------------------------------------------
# The brief
# ---------------------------------------------------------------------------
def brief(area: dict[str, Any], lens: str) -> tuple[str, str]:
    """`(title, body)` for one `(area, lens)` pair.

    The body is **self-contained**: the agent that picks this up reads the issue, not the
    audits README (`knowledge/audits/README.md` → *Trigger-issue body*). It carries the
    `audit` line the command parses in Step 0, the derived scope, and the run
    trailer — and deliberately restates no filing policy, which is what went stale on the
    security trigger when a body tried to.
    """
    edge = LENS_EDGE[lens]
    checklist = f"knowledge/specs/{lens}-audit-checklist.md"

    lines = [
        f"Run `{_repo.command('audit')} {lens} {area['slug']}`. Follow the audit command end to end — it loads",
        f"`{checklist}` + the prior record and selects the lanes and the",
        "filing model from that checklist's `## Audit profile`.",
        "",
        f"**Unit:** `{area['slug']}` (feature area) · **Lens:** `{lens}`",
        f"unit-key: {lens}/{area['slug']}",
        "",
        f"**Map:** [`{area['path']}`]({area['path']}) — the scope below is derived from it, not authored here.",
        f"**Checklist:** `{checklist}`",
        "",
    ]

    if area["intent"]:
        lines += [
            "**Intent — the bar this area is graded against:**",
            "",
            f"> {area['intent']}",
            "",
        ]

    if edge == "journeys":
        owned, elsewhere, ties = owned_journeys(area, areas())
        lines += [f"**{EDGE_LABEL[edge]} ({len(owned)}):**", ""]
        lines += [f"- `{x}`" + ("  ⚠ owner is a tie — confirm before walking" if x in ties else "") for x in owned]
        lines += [""]
        if elsewhere:
            # Naming them matters: without this the auditor sees the map list 7 journeys and
            # the brief list 4, and reads the gap as a coverage hole to re-open rather than
            # as ground another run already has.
            lines += [
                f"**Not yours ({len(elsewhere)})** — listed by this map but owned by another area, "
                "which audits them. Do **not** walk these; a duplicate finding costs a fleet slot "
                "and a triage (ENG-6383):",
                "",
            ]
            lines += [f"- `{x}`" for x in elsewhere]
            lines += [""]
    elif edge:
        items = area[edge]
        lines += [f"**{EDGE_LABEL.get(edge, edge)} ({len(items)}):**", ""]
        lines += [f"- `{x}`" for x in items]
        lines += [""]
    else:
        lines += [
            "**Scope:** every capability row in the map, plus the Intent clause above — "
            "intent delivery, capability conformance, and stranded backend.",
            "",
        ]

    if area["components"]:
        lines += [f"**Components:** {', '.join(f'`{c}`' for c in area['components'])}", ""]

    lines += [
        "---",
        "",
        f"- Diff-aware: weight what changed since the last `knowledge/audits/{lens}/` record",
        "  (`git diff` since its commit); full sweep, extra time on changed surfaces.",
        f"- Doc-only, no code review: land the record under `knowledge/audits/{lens}/` via a",
        "  throwaway branch + PR, auto-merged on green CI (the fleet identity has no direct-push",
        "  path to main).",
        "- On completion, set this issue to Done (the daemon's success signal).",
    ]
    return f"Audit: {area['name']} [{lens}]", "\n".join(lines)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_areas(_args: argparse.Namespace) -> int:
    known, ls_ = areas(), lenses()
    unruled = [x for x in ls_ if x not in LENS_EDGE]
    print(f"{len(known)} feature areas · {len(ls_)} lenses (checklists)\n")
    width = max(len(a) for a in known)
    ordered = [x for x in ls_ if x in LENS_EDGE]
    print(" " * (width + 2) + "  ".join(f"{x[:4]:>4}" for x in ordered))
    for slug in sorted(known):
        cells = []
        for lens in ordered:
            cells.append(f"{('·' if applicable(known[slug], lens) else '✓'):>4}")
        print(f"{slug:<{width}}  " + "  ".join(cells))
    print("\n✓ dispatchable · '·' the map declares no edge for that lens")
    print("legend: " + " · ".join(f"{x[:4]}={x}" for x in ordered))
    if unruled:
        print(f"\n⚠ checklist(s) with no LENS_EDGE rule (not dispatchable): {', '.join(unruled)}")
    fams = families()
    if fams:
        print(f"\n{len(fams)} families (the `Family` column of knowledge/audits/feature-coverage-ledger.md)")
        print("  — usable as `family:<name>` wherever an area is:\n")
        fwidth = max(len(f) for f in fams)
        for fam in sorted(fams):
            print(f"  family:{fam:<{fwidth}}  {len(fams[fam]):>2} areas  {', '.join(fams[fam])}")
        unplaced = sorted(set(known) - {s for v in fams.values() for s in v})
        if unplaced:
            print(f"\n⚠ area(s) in no family (invisible to every grouped scope): {', '.join(unplaced)}")
    return 0


def cmd_brief(args: argparse.Namespace) -> int:
    known = areas()
    try:
        resolved = resolve_areas([args.area], known)
        lens = resolve_lenses([args.lens])[0]
    except InvalidNameError as e:
        print(f"[audit] {e}", file=sys.stderr)
        return 2
    # `brief` renders ONE issue body, so a family here would silently print the first of
    # its N members and look like the whole answer. Refuse instead — `dispatch --lens X`
    # (a dry run by default) is the form that takes a family.
    if len(resolved) != 1:
        print(
            f"[audit] {args.area!r} expands to {len(resolved)} areas — `brief` renders one issue "
            f"body. Use `dispatch {args.area} --lens {args.lens}` (dry run) to see them all, or "
            f"name a single area.",
            file=sys.stderr,
        )
        return 2
    area = resolved[0]
    if why := applicable(area, lens):
        print(f"[audit] {area['slug']} / {lens}: {why}", file=sys.stderr)
        return 2
    title, body = brief(area, lens)
    print(f"# {title}\n\n{body}")
    return 0


def cmd_dispatch(args: argparse.Namespace) -> int:
    known = areas()
    try:
        resolved = resolve_areas(args.areas, known)
        lens_list = resolve_lenses([x.strip() for x in args.lens.split(",") if x.strip()])
    except InvalidNameError as e:
        print(f"[audit] {e}", file=sys.stderr)
        return 2

    pairs: list[tuple[dict[str, Any], str]] = []
    skipped: list[tuple[dict[str, Any], str]] = []
    for area in resolved:
        for lens in lens_list:
            (skipped if applicable(area, lens) else pairs).append((area, lens))

    for area, lens in skipped:
        print(f"[skip] {area['slug']} / {lens}: {applicable(area, lens)}")
    if not pairs:
        print("[audit] nothing dispatchable.", file=sys.stderr)
        return 1

    # DRY RUN ONLY (PRD 0820, FLT-1039). The fleet is the only party that talks to the tracker:
    # a session files through the Fleet tool `file_issue`, never a tracker client shipped here.
    # `--apply` is gone, and the argument parser refuses it rather than silently ignoring it.
    print(f"\nDRY RUN — {len(pairs)} issue(s) would be filed; file them with the Fleet tool `file_issue`.\n")
    for area, lens in pairs:
        title, _ = brief(area, lens)
        print(f"  P{enforce_priority_floor(args.priority, lens)}  {title}")
    print("\n(see the full body with: python3 knowledge/scripts/audit.py brief <area> --lens <lens>)")
    return 0


# ---------------------------------------------------------------------------
# Coverage state — one append-only file per run, never a shared table row
# ---------------------------------------------------------------------------
COVERAGE_DIR = Path("knowledge/audits/coverage")
DEPTHS = ("live", "partial", "graph", "skipped")


def coverage_write(root: Path, area: str, depth: str, notes: str, run_id: str, when: str) -> Path:
    """Write ONE coverage fact as its own file: `coverage/<area>/<when>-<run_id>.json`.

    The name is unique per run (timestamp + run id), so two concurrent audits write disjoint
    files and cannot conflict; nothing here edits a shared table or bumps a counter. The
    ledger's run-written columns (`Last audited` / `Depth` / `Notes`) are DERIVED from these
    files by `coverage_latest`, the way derived ledgers are generated on demand and never
    committed (decisions/2026-09-28-derived-ledgers-not-committed).
    """
    if depth not in DEPTHS:
        raise ValueError(f"depth must be one of {DEPTHS}, got {depth!r}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", area) or not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise ValueError("area must be a slug and run_id a plain token")
    if not re.fullmatch(r"\d{8}T\d{6}Z", when):
        raise ValueError("when must be YYYYMMDDTHHMMSSZ")
    out = root / COVERAGE_DIR / area / f"{when}-{run_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "area": area,
        "last_audited": f"{when[:4]}-{when[4:6]}-{when[6:8]}",
        "depth": depth,
        "notes": notes,
        "run_id": run_id,
    }
    with out.open("x", encoding="utf-8") as fh:  # "x": never overwrite another run's file
        fh.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return out


def coverage_latest(root: Path) -> dict[str, dict[str, Any]]:
    """Newest fact per area (by filename, which sorts by time) — the derived ledger view."""
    latest: dict[str, dict[str, Any]] = {}
    base = root / COVERAGE_DIR
    if not base.is_dir():
        return latest
    for d in sorted(base.iterdir()):
        files = sorted(d.glob("*.json")) if d.is_dir() else []
        if files:
            latest[d.name] = json.loads(files[-1].read_text(encoding="utf-8"))
    return latest


def cmd_coverage_write(args: argparse.Namespace) -> int:
    when = args.when or datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        out = coverage_write(Path("."), args.area, args.depth, args.notes, args.run_id, when)
    except (ValueError, FileExistsError) as e:
        print(f"[audit] {e}", file=sys.stderr)
        return 2
    print(out)
    return 0


def cmd_coverage(_args: argparse.Namespace) -> int:
    for area, f in sorted(coverage_latest(Path(".")).items()):
        print(f"{area}\t{f['last_audited']}\t{f['depth']}\t{f['notes']}")
    return 0


# ---------------------------------------------------------------------------
# The part rotation — a typed part's Tier sets its check depth and cadence
#
# FLT-1170. The feature rotation already derives a feature area's cadence from its
# authored `Tier` (`core` 3 days, `rotation` 14 days, `parked` never). Since PRD 0885
# every typed part — a feature area, a component, a connector and a customer's own
# system — carries the same closed vocabulary, authored where the part is authored:
# the coverage ledger's `Tier` column for an area, the component registry's `tier`
# column for a component, a `tier:` on a connector manifest and on a fixture record.
# This is the selector that turns those tiers into depth and cadence for EVERY typed
# part, not just the areas. Nothing here declares a schedule: re-tier a part and its
# cadence self-corrects, because the clock is the tier's own max age.
#
# A blank or absent tier reads UNTIERED: never auto-selected, and reported every run
# until a person sets it. A part left unchecked is `parked` WITH ITS REASON — the shape
# the coverage ledger's `Notes` column already uses — never a silent omission.
# ---------------------------------------------------------------------------

#: A tier's max age in days: the age at which the part is due for its next check.
#: `parked` and a blank tier are absent on purpose — never auto-selected (FLT-1182).
TIER_MAX_AGE_DAYS: dict[str, int] = {"core": 3, "rotation": 14}

#: The check depth a tier drives. A `parked` or untiered part is never run, so it reads
#: `skipped` — the coverage vocabulary's own word for a part no run reaches (DEPTHS).
TIER_DEPTH: dict[str, str] = {"core": "live", "rotation": "partial", "parked": "skipped", "": "skipped"}

#: What a parked part reports when no reason was authored anywhere.
NO_REASON = "parked — no reason recorded"

#: The five kinds a typed part may be, matching `validate_things_under_test.py`'s selectors.
PART_KINDS = ("area", "component", "connector", "customer-system")

COMPONENTS_DOC = os.path.join(REPO, "knowledge", "specs", "architecture", "components.md")
FIXTURES_DIR = os.path.join(REPO, "knowledge", "fixtures")
CONNECTOR_GLOB = os.path.join(REPO, "packages", "connector-*", "manifest.yaml")

#: A coverage-ledger data row's six cells: ``area | family | tier | date | depth | notes``.
#: The notes cell is a parked part's reason, carried the way the ledger already writes it.
_LEDGER_ROW6_RE = re.compile(r"^\|\s*`([a-z0-9-]+)`\s*\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|", re.M)
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

#: The component registry's two component tables — the canonical reader's own pair
#: (`fleet_knowledge.corpus.components`). `## Layers` is an `id`/`name` legend whose rows are
#: not components, and the heading scopes it out exactly as the canonical reader scopes it.
_REGISTRY_HEADINGS = ("Components", "Proposed components")


def _read(path: str) -> str:
    """A file's text, or `""` when it cannot be read — a missing source is the empty set."""
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _scalar_line(text: str, key: str) -> str:
    """The first top-level ``key: value`` scalar in a manifest-shaped file, unquoted."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{key}:"):
            value = stripped.partition(":")[2].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                return value[1:-1]
            return value
    return ""


def ledger_tiers() -> tuple[dict[str, str], dict[str, str]]:
    """`(area -> tier, area -> reason)` from the coverage ledger's `Tier` and `Notes` columns.

    An area with no ledger row keeps a blank tier (reported as untiered), never dropped.
    A missing ledger yields two empty maps — every area then reads untiered, which is the
    honest answer for a corpus that has not been tiered yet.
    """
    tiers: dict[str, str] = {}
    reasons: dict[str, str] = {}
    for slug, _family, tier, _date, _depth, notes in _LEDGER_ROW6_RE.findall(_read(LEDGER)):
        tiers[slug] = tier.strip()
        reasons[slug] = notes.strip()
    return tiers, reasons


def _registry_section(text: str, heading: str) -> str:
    """The body under a `## <heading>`, up to the next `## ` — the canonical reader's own rule."""
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s|\Z)", text, re.M | re.I)
    return m.group(1) if m else ""


def _table_cells(line: str) -> list[str]:
    """One pipe-table row as trimmed cells, escaped pipes restored — the corpus reader's rule."""
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def _registry_rows(text: str) -> list[tuple[str, str]]:
    """`[(component id, tier)]` from the registry's component tables, read BY COLUMN NAME.

    The SAME way the canonical reader reads this registry (`fleet_knowledge.corpus.components`
    and its `_cell`): the header row names each column and the `tier` cell is taken by name, so
    a registry that gains a column anywhere shifts no reader and — the case that mattered — a
    registry that declares no `tier` column at all still yields EVERY row, its tier blank.

    Reading `tier` by POSITION is what silently dropped the whole set: an eight-cell pattern
    matched nothing in the seven-column registry this repository ships and in every corpus
    written before PRD 0885, so every component vanished instead of being reported untiered.
    Only the two component headings are read, so the `## Layers` legend — also an `id`/`name`
    table — is never mistaken for components.
    """
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for heading in _REGISTRY_HEADINGS:
        cols: dict[str, int] = {}
        for line in _registry_section(text, heading).splitlines():
            if not line.lstrip().startswith("|"):
                continue
            row = _table_cells(line)
            if not row:
                continue
            if row[0].strip().lower() == "id" and any(c.strip().lower() == "name" for c in row):
                cols = {c.strip().lower(): i for i, c in enumerate(row)}
                continue
            cid = row[0].strip()
            if not cols or cid in seen or not _SLUG_RE.match(cid):
                continue
            seen.add(cid)
            i = cols.get("tier", -1)
            out.append((cid, row[i].strip() if 0 <= i < len(row) else ""))
    return out


def component_tiers() -> list[tuple[str, str]]:
    """`[(component id, tier)]` from the component registry's `## Components` table rows.

    The `tier` cell is read BY COLUMN NAME; a blank reads untiered. A registry with no `tier`
    column (a corpus written before PRD 0885 — including this repository's own registry)
    yields a blank tier for EVERY row, the honest "not tiered yet" rather than a dropped
    component. A missing registry yields nothing.
    """
    return _registry_rows(_read(COMPONENTS_DOC))


def connector_tiers() -> list[tuple[str, str]]:
    """`[(connector id, tier)]` from `packages/connector-*/manifest.yaml` (the manifest's `name:`).

    A manifest outside a `connector-*` package is not enumerated here and never was: the set
    is the glob, so `connector-sdk` and `connector-image`, which carry no manifest, are simply
    not connectors. The id falls back to the directory name when the manifest names no `name:`.
    """
    out: list[tuple[str, str]] = []
    for manifest in sorted(glob.glob(CONNECTOR_GLOB)):
        text = _read(manifest)
        cid = _scalar_line(text, "name") or os.path.basename(os.path.dirname(manifest))[len("connector-") :]
        out.append((cid, _scalar_line(text, "tier")))
    return out


def fixture_tiers() -> list[tuple[str, str]]:
    """`[(part id, tier)]` from `knowledge/fixtures/*.json` (a customer's own system).

    The part is the record's `part` id, or the filename stem when it carries none; the tier is
    the record's `tier`. A home that does not exist yet degrades to the empty set, never a refusal.
    """
    out: list[tuple[str, str]] = []
    for path in sorted(glob.glob(os.path.join(FIXTURES_DIR, "*.json"))):
        try:
            record = json.loads(_read(path) or "null")
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        part = str(record.get("part") or os.path.basename(path)[: -len(".json")]).strip()
        tier = record.get("tier")
        out.append((part, tier.strip() if isinstance(tier, str) else ""))
    return out


def typed_parts() -> list[dict[str, Any]]:
    """Every typed part, each with its authored `Tier` and (for an area) its parked reason.

    The four sources are the ones `validate_things_under_test.py` derives (PRD 0885): feature
    areas, the component registry, the connector manifests and the per-part fixture records.
    The feature area's tier and reason live in the coverage ledger, the one authored table areas
    use; a component's, connector's and fixture's tier live where the part itself is authored.
    """
    tiers, reasons = ledger_tiers()
    parts: list[dict[str, Any]] = [
        {"kind": "area", "id": slug, "tier": tiers.get(slug, ""), "reason": reasons.get(slug, "")} for slug in areas()
    ]
    parts += [{"kind": "component", "id": cid, "tier": tier, "reason": ""} for cid, tier in component_tiers()]
    parts += [{"kind": "connector", "id": cid, "tier": tier, "reason": ""} for cid, tier in connector_tiers()]
    parts += [{"kind": "customer-system", "id": pid, "tier": tier, "reason": ""} for pid, tier in fixture_tiers()]
    return parts


def _as_date(value: Any) -> datetime.date | None:
    """A stored `last_audited` (`YYYY-MM-DD`) as a date, or `None` when it is absent/unreadable."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def select_due(
    parts: list[dict[str, Any]],
    checked: dict[str, dict[str, Any]],
    today: datetime.date,
) -> dict[str, list[dict[str, Any]]]:
    """The typed parts whose `Tier` makes them due, plus those left unchecked and untiered.

    Pure: `today` is handed in, so two calls over one reading agree. A `core` part is due at 3
    days and a `rotation` part at 14; a part never checked is due immediately. A `parked` part is
    never selected and is reported under `unchecked` WITH its reason; a blank or unknown tier is
    reported under `untiered`. Nothing is silently dropped. `due` is ordered never-checked first,
    then most overdue first, then by kind and id — a total order.
    """
    due: list[dict[str, Any]] = []
    unchecked: list[dict[str, Any]] = []
    untiered: list[dict[str, Any]] = []
    for part in parts:
        kind = str(part.get("kind") or "")
        pid = str(part.get("id") or "")
        raw = str(part.get("tier") or "")
        tier = raw.strip().lower()
        cadence = TIER_MAX_AGE_DAYS.get(tier)
        if cadence is None:
            if tier == "parked":
                unchecked.append(
                    {
                        "kind": kind,
                        "id": pid,
                        "tier": tier,
                        "reason": str(part.get("reason") or "").strip() or NO_REASON,
                    }
                )
            else:
                untiered.append({"kind": kind, "id": pid, "tier": raw})
            continue
        last = _as_date((checked.get(pid) or {}).get("last_audited"))
        depth = TIER_DEPTH.get(tier, "skipped")
        if last is None:
            due.append(
                {
                    "kind": kind,
                    "id": pid,
                    "tier": tier,
                    "depth": depth,
                    "last_checked": None,
                    "overdue_days": cadence,
                    "never_checked": True,
                }
            )
            continue
        age = (today - last).days
        if age >= cadence:
            due.append(
                {
                    "kind": kind,
                    "id": pid,
                    "tier": tier,
                    "depth": depth,
                    "last_checked": last.isoformat(),
                    "overdue_days": age - cadence,
                    "never_checked": False,
                }
            )
    due.sort(key=lambda d: (not d["never_checked"], -d["overdue_days"], d["kind"], d["id"]))
    unchecked.sort(key=lambda u: (u["kind"], u["id"]))
    untiered.sort(key=lambda u: (u["kind"], u["id"]))
    return {"due": due, "unchecked": unchecked, "untiered": untiered}


def cmd_due(_args: argparse.Namespace) -> int:
    """Print every typed part whose Tier makes it due, and the ones left unchecked/untiered.

    A tick that finds nothing due does nothing but say so, exactly as the feature rotation does.
    Exit 0 whether or not anything is due — this is a query a person runs, not a gate.
    """
    parts = typed_parts()
    result = select_due(parts, coverage_latest(Path(".")), datetime.date.today())
    for d in result["due"]:
        when = d["last_checked"] or "never"
        print(f"DUE\t{d['kind']}:{d['id']}\t{d['tier']}\t{d['depth']}\t{when}\t{d['overdue_days']}d")
    for u in result["unchecked"]:
        print(f"UNCHECKED\t{u['kind']}:{u['id']}\tparked\t{u['reason']}")
    for u in result["untiered"]:
        print(f"UNTIERED\t{u['kind']}:{u['id']}")
    if not result["due"]:
        print(f"nothing due — {len(parts)} part(s) considered, {len(result['untiered'])} untiered")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        prog="audit.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("areas", help="print the dispatchable (area × lens) matrix and the family index").set_defaults(
        fn=cmd_areas
    )

    cw = sub.add_parser("coverage-write", help="record one run's coverage of an area as its own file")
    cw.add_argument("area")
    cw.add_argument("--depth", required=True, choices=DEPTHS)
    cw.add_argument("--notes", default="")
    cw.add_argument("--run-id", required=True)
    cw.add_argument("--when", default="", help="YYYYMMDDTHHMMSSZ (default: now, UTC)")
    cw.set_defaults(fn=cmd_coverage_write)
    sub.add_parser("coverage", help="print the derived per-area coverage view").set_defaults(fn=cmd_coverage)

    sub.add_parser(
        "due",
        help="print every typed part whose Tier makes it due (core 3d, rotation 14d, parked never)",
    ).set_defaults(fn=cmd_due)

    b = sub.add_parser("brief", help="render one issue body without touching the tracker")
    b.add_argument("area", help="one feature area (a `family:<name>` expands to many — use dispatch)")
    b.add_argument("--lens", required=True)
    b.set_defaults(fn=cmd_brief)

    d = sub.add_parser("dispatch", help="file Type:audit issues for the fleet")
    d.add_argument(
        "areas",
        nargs="+",
        metavar="AREA_OR_FAMILY",
        help="feature area slugs and/or `family:<name>` groups (see `audits areas` for both lists); "
        "families expand to their members and the whole list is deduplicated",
    )
    d.add_argument("--lens", required=True, help="comma-separated, e.g. ux,ui")
    d.add_argument(
        "--priority",
        type=int,
        choices=[1, 2, 3],
        help="override the lens default (1=Urgent 2=High 3=Medium). Use to rank one batch against "
        "another — e.g. re-runs of known-unreliable verdicts above first-ever breadth coverage. "
        "Low is not offered: it never dispatches (see PRIORITY_FLOOR).",
    )
    d.set_defaults(fn=cmd_dispatch)

    args = p.parse_args()
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
