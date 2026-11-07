"""Validate the per-domain requirement registers + the PRD `implements:` edge.

The register (`knowledge/requirements/<domain>.md`, `type: requirement-register`)
is the **constraint axis** — off the ladder, durable, one numbered row per
commitment a corpus makes. Its contract lives in
`knowledge/specs/knowledge-model.md` -> "Decisions and requirements"; this file is
the mechanical reading of it. Where the two disagree, the spec wins.

  | ID | Statement | Kind | Disposition | Source |   (+ optional `Cut` and `Needs` columns)

**The load-bearing rule is that an ID is permanent and never reused.** Everything
downstream — a PRD's `implements:`, a spec citing `RUN-078` instead of restating it,
the derived backlog/orphan/drift queries — is a string match on that ID. So a
duplicate, a re-padded alias, or a dangling reference is unambiguous corruption and
fails the commit.

Structural checks (the register itself):

  Ids       — `<PREFIX>-NNN`, prefix == the file's frontmatter `prefix:`,
              zero-padded to >=3 digits with no alias padding (`RUN-0001` is a
              different string for the same number), unique WITHIN and ACROSS
              register files.
  Vocab     — `Kind` in {invariant, requirement, constraint, alternative, accepted}
              and `Disposition` in {adopted, rejected, open, superseded[ by <ID>]}.
              Kind and Disposition are orthogonal: a *rejected constraint* is still
              a constraint, so neither column may borrow the other's vocabulary.
  Legality  — the Kind x Disposition matrix. DELIBERATELY near-empty: the two
              columns are orthogonal by design, so only the pairs that are
              self-contradictory are refused (see ILLEGAL_KIND_DISPOSITION).
  Cut       — the THIRD orthogonal axis: which release line a row's commitment
              lands in. Vocabulary `{v1, v2}` or blank, and legal only on an
              `adopted` row — a rejected or superseded row has no version to be
              cut from. **Tolerant of absence**, exactly like `Needs`.
  Supersede — `superseded by X` resolves to a real row, the supersession graph is
              acyclic (a cycle means neither row is the live one), and a chain may
              not TERMINATE on a `rejected` row (the commitment evaporated: the
              reader following the pointer lands on something we refused).
  Needs     — the 5th DAG: requirement -> requirement build order. Resolves
              (cross-register allowed; ids are globally unique) and stays acyclic,
              matching the four graphs already validated acyclic. **Tolerant of
              absence** — a register with no `Needs` column passes.
  Because   — the premise edge (the event-triggered re-read trigger). A row
              records the premise its decision rested on (`Because: RUN-NNN`); when
              that premise row is superseded or rejected, the row surfaces for
              re-reading — the consumer the `rejected`/`accepted` rows can never get
              from a PRD claim. Discharge is one token, `reaffirmed=YYYY-MM-DD`.
              Reference hygiene (dangling `Because`, a self-loop, a malformed
              `reaffirmed=`) is HARD; the premise-moved surfacing itself is ADVISORY
              — a signal to re-read, not a defect. **Tolerant of absence**, like
              `Needs`.
  Order     — a NEW id is appended at the END of its register, never inserted
              next to the rows it relates to. Ratcheted: the ids already sitting
              mid-file the day this landed are grandfathered and the set may only
              shrink, so the existing register passes unchanged.
  Scope     — TWO checks that used to be one, split by the `Cut` column. A live
              PRD claims a row; that row's `Needs` point somewhere.
                * HARD — the need is CUT from the line being built and the needer
                  is not. The design rests on a mechanism this version does not
                  have: either the edge is wrong or the scope is.
                * ADVISORY — the need is in this line and simply nothing is
                  building it. A question (real work nobody scheduled), not a
                  defect. Distinguishes `(orphaned)` from `(unclaimed)`.
              Before `Cut` existed both were the same string and the whole check
              had to be advisory; see check_claim_scope.
  Closure   — the mechanical half of "superseding a row is a change with a
              closure, not a cell edit": a live row may not need a `superseded`
              or `rejected` one (it would claim a build order through a mechanism
              we replaced or refused), and a dead row may not carry `Needs` of its
              own (there is nothing left to build). Both are residues of a
              supersession nobody propagated — the failure that left ~129 rows
              describing dropped mechanisms. What no validator can see is that a
              design cut the mechanism at all; that judgement is the author's
              (the design command that mints and settles rows).
  Source    — the citation form actually resolves. A quoted fragment
              (`arch §15 "a registry on the data plane"`) must occur EXACTLY ONCE
              inside the section it names; a legacy `arch §N:L` line anchor must fall
              inside that section's span; a `D<n>:L` record anchor must be a line the
              record has. `prd:NNNN "fragment"` and section-less `<tag> "fragment"`
              citations are existence-checked: the PRD path is derived from the number
              and the tag must resolve in the legend. A recognised form whose tag still
              does not resolve is reported as an advisory — never silently skipped.
              The target file for each tag is read from the register's own Source-legend
              table, never hardcoded here.
  Components— the frontmatter `components:` list, if present, resolves to registered
              components. OPTIONAL: it is the join a reader arrives by, not a property
              of the rows, and it will lag the registers for as long as the backfill
              runs. See check_register_components.

Linkage checks (PRD -> register), all reading the realisation edge,
`implements:` in `prd.md`:

  Claims    — every id in `implements:` resolves to a real requirement row. Hard
              for EVERY PRD including terminal ones: unlike a `project:` pointer
              (which may dangle as history once a project is deleted), a
              requirement id is permanent, so a dangling one is a typo or a
              deleted row — never legitimate history.
  Coverage  — every claimed requirement is cited by >=1 acceptance criterion
              (`**[RUN-078]**` / `[RUN-078]` under the PRD's acceptance-criteria
              heading). **One direction only**: an AC citing nothing is legal and
              common; the reverse rule is how traceability programmes die.
              Enforced from `planned` onward (an AC set is a committed artifact by
              then); advisory for `stub`/`prd-drafted`/`designed`, where the claim
              may legitimately precede the ACs.
  Drift     — a live PRD may not claim a `rejected`, `superseded` or `excluded` requirement
              (`excluded` = a capability we decided not to build, so a PRD claiming one is
              building the thing the row refuses):
              either the PRD is building something we refused, or the register is
              stale, and both need a human. Advisory once the PRD is `shipped`
              (being superseded AFTER a ship is the normal life of a requirement,
              not a defect), skipped for `cancelled` (inert history).
              A claim on an `open` row is an advisory everywhere — the PRD settled
              what the register still calls unsettled, so the row wants updating.
   Citations — the corpus-wide half of the same edge. CLAUDE.md mandates citing
               `RUN-078` rather than restating a commitment, and until this check
               existed NOTHING resolved a citation outside a PRD's frontmatter and
               acceptance criteria — a spec, a design or a slash command could point
               at a deleted or refused row forever. Every `.md` under `knowledge/`
               and `.claude/`, plus `CLAUDE.md`, is scanned for ids in a KNOWN
               register prefix (a Linear key like `ENG-4813` is the same shape and is
               deliberately not read as a citation). Unresolvable is hard; citing a
               `rejected`/`superseded` row is advisory, aggregated per id.
               **Registers themselves are exempt from that prose walk** (they define
               the ids), so a second pass — `check_row_statement_citations` — resolves
               every known-prefix id written inside a row's Statement against the
               register set. Needs/Because already resolve; Statement citations did
               not, and a dangling one (RUN-1238 citing a nonexistent DOC-011) passed
               every commit gate until the weekly knowledge-consistency audit found it
               (ENG-17141). Same severity: unresolvable is hard; a live row citing a
               dead one is advisory.
   Restate  — the reverse of the same edge, and the mechanical reading of "prose may
               not restate a commitment, it cites one": a requirement STATEMENT
               reappearing verbatim in prose (a spec, a design, a slash command)
               without that row cited anywhere in the file is a failed citation, and
               fails the commit. Precise by construction — sentence-bounded, whole-
               statement, and exempting a row's own Source target(s) (the wording's
               origin) and decision records (where commitments are SETTLED, which the
               register cites). Only the VERBATIM restatement is detectable this way;
               a paraphrase is a judgement call no validator can make, and stays
               invisible. See check_uncited_restatements.

Severity split follows the siblings: a broken reference or a duplicate id fails the
commit; a judgement call prints as a `note:` so it is seen without being disabled.
Advisories are also written to `$GITHUB_STEP_SUMMARY` when CI sets it — the repo's
existing answer (merge_guard_check.py, submodule_pointer_guard_check.py) to a note
that would otherwise print inside a green job nobody opens.

Three checks are RATCHETED against `scripts/requirement_register.baseline`, because
they found real violations in a corpus that predates them and whose rows this
validator does not own: the Kind x Disposition matrix, supersession terminality, and
the legacy `arch §N:L` anchors. The baseline's only legitimate edit is REMOVAL, and a
NEW violation always fails — the shape `validate_prd_mockup_reference.py` established.
A grandfathered entry that stops being a violation fails for the first two (small,
stable, human-owned rows) and prints as a note for the third, whose violation set is a
function of a moving document; see `apply_ratchet`.

Stdlib only. Prints `file: message` per violation; exits 1 on any.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ... import corpusref
from ... import requirements as kkreq
from .context import Context

# ── the register grammar ──
# BOUND, never restated. `fleet_knowledge.requirements` is the ONE reader of a register
# row, and the vocabulary a row is checked against has to be the same object the parser
# used — or this validator and every viewer over the same corpus would disagree about
# which rows exist. Each constant's argument (why bare `superseded` is sanctioned, why
# `Cut` is a column and not a fifth disposition) is stated on its definition, there.
ID_RE = kkreq.ID_RE
ID_REF_RE = kkreq.ID_REF_RE
PREFIX_RE = kkreq.PREFIX_RE
KINDS = kkreq.KINDS
DISPOSITIONS = kkreq.DISPOSITIONS
SUPERSEDED_RE = kkreq.SUPERSEDED_RE
REAFFIRMED_RE = kkreq.REAFFIRMED_RE
CUT_VALUES = kkreq.CUT_VALUES
REQUIRED_COLUMNS = kkreq.REQUIRED_COLUMNS
SEP_RE = kkreq.SEP_RE
LEGEND_LINK_RE = kkreq.LEGEND_LINK_RE

# The frontmatter, field, id-list and table-cell readers, bound for the same reason —
# most of all `idlist`, which accepts all three YAML spellings because a claim written
# in a form the parser does not see is a claim that silently escapes every check here.
frontmatter = kkreq.frontmatter
field = kkreq.field
idlist = kkreq.idlist
cells = kkreq.cells
source_legend = kkreq.source_legend

# The citation form an acceptance criterion uses. Bracketed on purpose: it is greppable,
# it survives bolding (`**[RUN-078]**`), and prose mentioning a requirement cannot
# produce it by accident. A PRD-claim concern, not part of the register row grammar.
# A repo-qualified claim (`implements: [fleet:FLT-104]`) is cited the same way, qualifier and
# all (`[fleet:FLT-104]`), so the coverage match stays a plain string match.
AC_CITE_RE = re.compile(r"\[((?:[a-z][a-z0-9-]*:)?[A-Z]{2,5}-\d{3,})\]")


def next_id_re(ctx: Context) -> re.Pattern[str]:
    """The append-only counter marker. Not part of the row grammar — it is a property of
    the FILE, and the reader parses rows rather than files, so it lives here."""
    return re.compile(rf"{re.escape(ctx.cfg.append_only_marker)}\s*([A-Z]{{2,5}}-\d+)")


ILLEGAL_KIND_DISPOSITION = {
    ("accepted", "open"): (
        "`accepted` means the cost was already TAKEN, `open` means nothing is settled — "
        "one of the two is wrong (usually the disposition, which wants `adopted`)"
    ),
    ("accepted", "rejected"): (
        "`accepted` means the cost was already TAKEN — a cost we refused to take is a road "
        "not taken, i.e. `alternative | rejected`"
    ),
    ("alternative", "adopted"): (
        "an adopted option is the decision, not the road not taken — retype the row "
        "`invariant`/`requirement`/`constraint`, and keep the alternative row for what we refused"
    ),
    ("excluded", "rejected"): (
        "an exclusion we considered and declined to make is simply not a row — delete it, "
        "or if we DID refuse the capability, the disposition is `adopted` (the exclusion is "
        "in force)"
    ),
    ("excluded", "open"): (
        "an exclusion is in force from the moment it is written — there is no mechanism "
        "coming that would settle it, so it is never born `open` the way a promise is; "
        "`adopted` is the only live disposition for this kind"
    ),
}


def find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    """One cycle as a node path (`[a, b, a]`), else None. White/grey/black DFS.

    Edges to nodes absent from `graph` are skipped — resolution is reported
    separately, so cycle detection stays orthogonal to it.

    ITERATIVE, deliberately, where the sibling validators' identical helper recurses:
    their graphs hold tens of nodes, this one holds a register (644 rows on the day it
    landed) and a long `Needs` chain would blow the recursion limit. That surfaces as a
    RecursionError traceback out of an `always_run: true` pre-commit hook — every commit
    in the checkout blocked, with no message saying what is wrong.
    """
    white, grey, black = 0, 1, 2
    color = dict.fromkeys(graph, white)
    for root in graph:
        if color[root] != white:
            continue
        color[root] = grey
        path = [root]
        stack = [iter(graph.get(root, ()))]
        while stack:
            for m in stack[-1]:
                if m not in color:
                    continue
                if color[m] == grey:
                    return path[path.index(m) :] + [m]
                if color[m] == white:
                    color[m] = grey
                    path.append(m)
                    stack.append(iter(graph.get(m, ())))
                    break
            else:  # this node's edges are exhausted — retreat
                color[path.pop()] = black
                stack.pop()
    return None


def _foreign_dead(record: Any) -> str | None:
    """A sibling corpus's requirement row's dead disposition, as `dead()` words it, or None."""
    if not record:
        return None
    if record.get("superseded"):
        return f"superseded by {record['superseded_by']}" if record.get("superseded_by") else "superseded"
    if record.get("disposition") == "rejected":
        return "rejected"
    return None


def _foreign(ctx: Context, token: str, *, where: str) -> tuple[str | None, corpusref.Resolution | None]:
    """`(local id, None)` for a bare or own-qualified requirement reference; `(None, resolution)`
    for one qualified with another corpus. A foreign reference is NEVER looked up in `rows`."""
    local = ctx.corpora.localize(token)
    if local is not None:
        return local, None
    return None, ctx.corpora.resolve(token, corpusref.REQUIREMENT, where=where)


def check_owned_prefixes(ctx: Context, rows: dict[str, dict[str, Any]]) -> None:
    """A register prefix names ONE register. A local register whose prefix a declared sibling
    owns (`[fleet.planning.corpora] fleet = { prefixes = ["FLT"] }`) is two registers under one
    name, and every bare `FLT-NNN` here would resolve against the sibling, never this file."""
    seen: set[tuple[str, str]] = set()
    for r in rows.values():
        prefix = r["prefix"]
        owner = ctx.corpora.owned.get(prefix)
        if owner is None or (prefix, str(r["file"])) in seen:
            continue
        seen.add((prefix, str(r["file"])))
        ctx.err(
            r["file"],
            f"register prefix `{prefix}` is owned by corpus `{owner}` (`[fleet.planning.corpora]`), "
            "so a bare id in it resolves there, never here — a prefix names one register: rename this "
            "register's prefix, or drop the prefix from the sibling's declaration",
        )


def claim_ids(ctx: Context, fm: str) -> list[str]:
    """A PRD's `implements:` ids in their one canonical spelling — an OWN-corpus qualifier
    dropped (`acme:RUN-002` -> `RUN-002`), a bare id in a prefix a sibling owns qualified with
    its owner (`FLT-104` -> `fleet:FLT-104`) — so every reader of the claim edge keys a local
    row by its local id, and a cross-corpus claim never reads as a dangling local one."""
    return [ctx.corpora.canonical(x) for x in idlist(fm, "implements")]


def load_registers(ctx: Context) -> dict[str, dict[str, Any]]:
    """{id: row} across every register, through the package's ONE reader.

    The reader returns `(rows, findings)` — structural problems (a malformed id, a
    duplicate, a prefix that does not match the register's own, an off-vocabulary Kind or
    Disposition) come back as data rather than as a print, so a validator can fail a build
    on them and a viewer can render what parsed and say so. Recorded here exactly as the
    validator always recorded them.
    """
    rows, findings = kkreq.load_registers(
        ctx.knowledge,
        rel=ctx.rel,
        reserved_prefixes=frozenset(ctx.cfg.reserved_prefixes),
        dir_name=ctx.cfg.requirements_dir,
        own=ctx.corpora.own,
        owned=ctx.corpora.owned,
    )
    for path, msg in findings:
        ctx.err(path, msg)
    return rows


# --- components: the join a reader arrives by ---------------------------------
# A register is addressed by DOMAIN (`knowledge/requirements/<domain>.md`), and nothing a
# reader holds in their hand is a domain. What they hold is a touched path, which
# `scripts/component_of.py` turns into a COMPONENT ID — so until this field existed the
# lookup *component -> register* had no mapping at either end, and every reader that tried
# it (the triage gate most of all) was guessing a filename. The registers that DO exist
# were unreachable, which reads from the outside exactly like ground nobody has covered.
#
# **`components:` is a LABEL, not a partition**, and both directions of that matter: one
# register may govern several components (workload-runtime spans the sandbox, the app
# runtime, its packaging and the harness), and one component may be governed by several
# registers (`rest-api` carries API-surface rules AND a governance invariant). Forcing 1:1
# would make the field a second, worse copy of `owns:`.
#
# Same field NAME as a feature map's `components:` on purpose — one vocabulary for "which
# structural components does this document speak for", so a reader who has learned it once
# has learned it everywhere.
#
# The registry path is resolved from `ctx.knowledge` INSIDE the reader rather than bound to a module
# constant, because the self-tests rebind `vr.K` at a temp tree and a constant captured at
# import time would silently keep reading the real repo.


def registered_components(ctx: Context) -> dict[str, str]:
    """`{component id: layer}` from the component registry's `## Components` table.

    Registry order is preserved (the table groups by layer), because the derived index
    reads better grouped the way the architecture is grouped than sorted alphabetically.
    Shape is validated by `scripts/validate_components.py`; only the id and layer columns
    are read here, so this never becomes a second registry parser to keep in step.
    """
    out: dict[str, str] = {}
    reg = ctx.knowledge / ctx.cfg.components_registry
    if not reg.is_file():
        return out
    in_sec = False
    for line in reg.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_sec = line.strip() == ctx.cfg.components_section
            continue
        if not in_sec or not line.strip().startswith("|"):
            continue
        c = cells(line)
        if not c or c[0].lower() == "id" or not (set(c[0]) - set("-: ")):
            continue
        out[c[0]] = c[2] if len(c) > 2 else ""
    return out


def register_components(ctx: Context) -> dict[str, list[str]]:
    """`{register domain: the component ids its frontmatter declares}`, in file order.

    Absent and empty are the same answer — an undeclared register contributes nothing to
    the index and is legal, because the field will lag the registers for as long as the
    backfill runs and a hard requirement would have meant authoring it blind.
    """
    out: dict[str, list[str]] = {}
    for f in ctx.registers():
        fm = frontmatter(f.read_text(encoding="utf-8"))
        if fm is None:
            continue  # load_registers owns the missing-frontmatter error
        out[f.stem] = idlist(fm, "components")
    return out


def slice_components(ctx: Context) -> dict[str, list[str]]:
    """`{SL-NNN: the component ids its register row's `Components` cell names}`.

    This is the PRD -> register join, and it goes the long way round on purpose. A PRD does
    not declare components (its ground is the cut it belongs to, not a field it repeats),
    a slice does, and a register declares which components it governs. So:

        prd.md `slice:`  ->  slices.md `Components`  ->  requirements/*.md `components:`

    An empty or `—` cell yields `[]`, which reads as *unknown ground*, never as *no ground* —
    every caller treats an unjoinable PRD as uncovered and stays silent rather than guessing.
    """
    out: dict[str, list[str]] = {}
    f = ctx.knowledge / ctx.cfg.slices_register
    if not f.is_file():
        return out
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.startswith(f"| {ctx.cfg.slice_id_prefix}"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) <= ctx.cfg.slice_components_column:
            continue
        sid, comps = cells[0], cells[ctx.cfg.slice_components_column]
        if comps in ("", "—", "-"):
            out[sid] = []
            continue
        out[sid] = [c.strip() for c in comps.split(",") if c.strip()]
    return out


def registers_covering(components: list[str], reg_comps: dict[str, list[str]]) -> list[str]:
    """Which register domains govern any of these components. Order-stable, deduped."""
    hit: list[str] = []
    for domain, owned in reg_comps.items():
        if any(c in owned for c in components) and domain not in hit:
            hit.append(domain)
    return hit


def check_register_components(ctx: Context, declared: dict[str, list[str]], known: dict[str, str]) -> None:
    """Every id in a register's `components:` resolves, and none is listed twice.

    HARD, like every other reference check here: an id that resolves to nothing is a typo
    or a component someone renamed, and either way the register silently drops off the
    index for the component it meant to claim — the same dead lookup this field exists to
    close, just one layer further in.
    """
    if not known:
        if any(declared.values()):
            ctx.notes.append(
                "the component registry (knowledge/specs/architecture/components.md) could not be read, "
                f"so no `components:` declaration was resolved — run {ctx.cfg.cmd_validate_components}"
            )
        return
    base = ctx.register_dir
    for domain, ids in declared.items():
        path = base / f"{domain}.md"
        seen: set[str] = set()
        for cid in ids:
            if cid in seen:
                ctx.err(path, f"components lists `{cid}` twice")
                continue
            seen.add(cid)
            if cid not in known:
                ctx.err(
                    path,
                    f"components `{cid}` does not resolve to a components.md entry — the id is the "
                    f"join key a reader arrives by (`{ctx.cfg.cmd_component_of}` emits it), so an "
                    "unresolvable one claims nothing",
                )


# --- the ratchet -------------------------------------------------------------
# Two checks below found violations in a corpus that predates them, whose rows this
# validator does not own. Grandfathering them keeps the guard live for everything new
# instead of postponing it until someone has time for a content pass.


def load_baseline(path: Path) -> set[tuple[str, str]]:
    """Grandfathered `<check> <ID>` pairs; blank lines and `#` comments ignored."""
    out: set[tuple[str, str]] = set()
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) == 2:
            out.add((parts[0], parts[1]))
    return out


def apply_ratchet(
    ctx: Context,
    check: str,
    live: dict[str, str],
    baseline: set[tuple[str, str]],
    stale_is_hard: bool,
) -> None:
    """`live` is `{id: why}`. A NEW violation always fails; a grandfathered one prints.

    `stale_is_hard` splits the two callers on purpose. For `legality` the grandfathered
    set is small, stable and human-owned, so an entry that stopped being a violation is
    an error — leaving it there would pre-grandfather a future regression of that same
    row (validate_prd_mockup_reference.py's reasoning, verbatim). For `source-anchor` the
    violation set is a function of a MOVING document — an unrelated edit can heal an
    anchor by coincidence — so a shrunk set is reported as a note and the file is
    tidied when convenient. Both directions still ratchet: the floor only ever drops.
    """
    grand = {i for (c, i) in baseline if c == check}
    for rid, why in sorted(live.items()):
        if rid not in grand:
            ctx.errors.append(f"{check}: {rid}: {why}")
    stale = sorted(grand - set(live))
    if stale:
        msg = (
            f"{check}: {len(stale)} baseline entr(y/ies) in {ctx.baseline_path.name} are no longer violations "
            f"({', '.join(stale[:8])}{' …' if len(stale) > 8 else ''}) — delete those lines; "
            "the baseline only ever shrinks"
        )
        (ctx.errors if stale_is_hard else ctx.notes).append(msg)
    if remaining := sorted(grand & set(live)):
        ctx.notes.append(
            f"{check}: {len(remaining)} grandfathered violation(s) still live "
            f"({', '.join(remaining[:8])}{' …' if len(remaining) > 8 else ''}) — fixing one means "
            f"deleting its line from {ctx.baseline_path.name}"
        )


def check_kind_disposition(ctx: Context, rows: dict[str, dict[str, Any]], baseline: set[tuple[str, str]]) -> None:
    """The Kind x Disposition matrix — see ILLEGAL_KIND_DISPOSITION for why it is small."""
    live: dict[str, str] = {}
    for rid, r in rows.items():
        disp = "superseded" if r["superseded"] else r["disposition"]
        if why := ILLEGAL_KIND_DISPOSITION.get((r["kind"], disp)):
            live[rid] = f"`{r['kind']} | {disp}` is not a legal pair — {why}"
    apply_ratchet(ctx, "legality", live, baseline, stale_is_hard=True)


def supersession_terminus(rows: dict[str, dict[str, Any]], rid: str) -> str | None:
    """The row a `superseded by` chain from `rid` finally lands on, or None."""
    seen = {rid}
    cur = rows[rid]["superseded_by"]
    while cur in rows and cur not in seen and rows[cur]["superseded"] and rows[cur]["superseded_by"]:
        seen.add(cur)
        cur = rows[cur]["superseded_by"]
    return cur if cur in rows else None


def check_supersession_terminality(
    ctx: Context, rows: dict[str, dict[str, Any]], baseline: set[tuple[str, str]]
) -> None:
    """A supersession chain must not END on a `rejected` row.

    `superseded by X` is a forwarding pointer: the reader follows it to find the live
    commitment. Landing on a rejection means the commitment did not move — it
    EVAPORATED, and the register says so nowhere. That is the one terminus worth
    failing on.

    Landing on an `open` row is a different animal and is reported as ONE aggregated
    note, not thirteen errors: "the successor is still being decided" is a legitimate
    intermediate state, and the useful signal is *which* open row is holding how many
    superseded rows hostage — settle that row and they all resolve at once.
    """
    live: dict[str, str] = {}
    open_targets: dict[str, list[str]] = {}
    for rid, r in rows.items():
        if not (r["superseded"] and r["superseded_by"]):
            continue
        end = supersession_terminus(rows, rid)
        if end is None:
            continue  # dangling — check_supersession owns that error
        disp = rows[end]["disposition"]
        if disp == "rejected":
            live[rid] = (
                f"its supersession chain ends on `{end}`, which is `rejected` — a reader following "
                "the pointer lands on something we refused, so the commitment evaporated silently; "
                "point it at the row that replaced it, or make this row `rejected` in its own right"
            )
        elif disp == "open":
            open_targets.setdefault(end, []).append(rid)
    apply_ratchet(ctx, "supersession-terminality", live, baseline, stale_is_hard=True)
    if open_targets:
        detail = ", ".join(f"{t} (x{len(v)})" for t, v in sorted(open_targets.items(), key=lambda kv: -len(kv[1])))
        ctx.notes.append(
            f"{sum(len(v) for v in open_targets.values())} supersession chain(s) end on an `open` row: "
            f"{detail} — settling that row settles every chain behind it"
        )


def check_supersession(ctx: Context, rows: dict[str, dict[str, Any]]) -> None:
    """`superseded by X` must resolve, and the supersession graph must be acyclic.

    A cycle (A superseded by B, B superseded by A) means NEITHER row is the live
    one — the reader following the pointer never lands anywhere.
    """
    graph: dict[str, list[str]] = {}
    for rid, r in rows.items():
        target = r["superseded_by"]
        graph[rid] = []
        if not target:
            continue
        local, res = _foreign(ctx, target, where=f"{ctx.rel(r['file'])} {rid} superseded by")
        if res is not None:
            # Another corpus's row: resolved against that corpus, and an opaque node to the
            # cycle check — no local cycle can run through a row this corpus does not hold.
            if res.is_error:
                ctx.err(r["file"], f"{rid}: `superseded by {target}` — {res.message}")
            elif res.record and not res.record.get("superseded") and res.record.get("disposition") == "rejected":
                # The terminality rule, read where the successor lives: a chain that ENDS on a
                # refused row evaporated the commitment, in whichever corpus it ends.
                ctx.err(
                    r["file"],
                    f"{rid}: `superseded by {target}`, which is `rejected` in corpus `{res.ref.corpus}` — a "
                    "reader following the pointer lands on something that corpus refused, so the "
                    "commitment evaporated silently; point it at the row that replaced it, or make this "
                    "row `rejected` in its own right",
                )
            continue
        target = str(local)
        if target not in rows:
            ctx.err(r["file"], f"{rid}: `superseded by {target}` does not resolve to a requirement row")
            continue
        if target == rid:
            ctx.err(r["file"], f"{rid}: is superseded by itself")
            continue
        graph[rid] = [target]
    if cyc := find_cycle(graph):
        ctx.errors.append(f"supersession cycle: {' -> '.join(cyc)} — neither row is the live one")


def dead(r: dict[str, Any]) -> str | None:
    """The row's disposition if it no longer describes something being built.

    `superseded` and `rejected` only: an `open` row is unsettled, not dead — it
    may legitimately be ordered against a mechanism that already exists.
    """
    if r["superseded"]:
        return f"superseded by {r['superseded_by']}" if r["superseded_by"] else "superseded"
    if r["disposition"] == "rejected":
        return "rejected"
    return None


def check_needs(ctx: Context, rows: dict[str, dict[str, Any]]) -> None:
    """The 5th DAG: requirement -> requirement build order (`Needs` column).

    Optional by construction — a register that has not adopted the column yet
    contributes no edges and passes. Once present the same two rules the other
    four graphs carry apply: every reference resolves, and the graph is acyclic
    (a cycle makes the build order undefined).

    Plus the two edges a supersession must not leave behind. They are HARD rather
    than advisory for the same reason a dangling `implements:` is: the register's
    build order is read as fact by whoever plans the work, and an order routed
    through a mechanism we already dropped is not a judgement call — it is a
    reference to something that is no longer there.
    """
    graph: dict[str, list[str]] = {}
    for rid, r in rows.items():
        deps = r["needs"]
        graph[rid] = []
        state = dead(r)
        if deps and state:
            ctx.err(
                r["file"],
                f"{rid}: is `{state}` but still carries Needs ({', '.join(deps)}) — a "
                "superseded or rejected row has nothing left to build; clearing the cell is "
                "part of the supersession, not a follow-up",
            )
        for raw in deps:
            local, res = _foreign(ctx, raw, where=f"{ctx.rel(r['file'])} {rid} Needs")
            if res is not None:
                if res.is_error:
                    ctx.err(r["file"], f"{rid}: Needs `{raw}` — {res.message}")
                elif (target := _foreign_dead(res.record)) and not state:
                    ctx.err(
                        r["file"],
                        f"{rid}: Needs `{raw}`, which is `{target}` in corpus `{res.ref.corpus}` — a live "
                        "row cannot presuppose a mechanism that was replaced or refused; re-point or drop "
                        "the edge",
                    )
                continue
            d = str(local)
            graph[rid].append(d)
            if d == rid:
                ctx.err(r["file"], f"{rid}: Needs itself")
            elif d not in rows:
                ctx.err(r["file"], f"{rid}: Needs `{d}`, which is not a known requirement id")
            elif (target := dead(rows[d])) and not state:
                successor = rows[d]["superseded_by"]
                fix = f"re-point the edge at `{successor}`" if successor else "drop the edge"
                ctx.err(
                    r["file"],
                    f"{rid}: Needs `{d}`, which is `{target}` — a live row cannot presuppose a "
                    f"mechanism we replaced or refused; {fix} in the same change that "
                    "superseded it (knowledge-model.md -> Decisions and requirements)",
                )
    if cyc := find_cycle(graph):
        ctx.errors.append(f"requirement dependency cycle: {' -> '.join(cyc)}")


def check_because(ctx: Context, rows: dict[str, dict[str, Any]]) -> None:
    """The `Because` premise edge — the event-triggered re-read trigger (A2).

    A row records the premise its decision rested on (`Because: RUN-NNN`). When that
    premise row MOVES — is superseded or rejected, i.e. `dead` — the rows resting on it
    surface for re-reading, because a rejection or accepted-cost whose premise has
    expired is the register's most valuable row, and the only thing that can spot it is
    a human being pointed back at it. This is the consumer the structurally-consumerless
    rows (`rejected` + `accepted`) can never get from a PRD `implements:` claim.

    Discharge is one token — `reaffirmed=<date>` on the row — marking that a human
    re-read it and attested it still holds; the advisory then goes quiet. ADVISORY, not
    hard: surfacing is a signal, not a defect — a premise may move while the decision
    still holds, and whether it does is the reader's judgement. What IS hard is the
    reference hygiene (a dangling `Because`, a self-loop, a malformed `reaffirmed=`),
    for the same reason a dangling `implements:` is.
    """
    for rid, r in rows.items():
        because = r.get("because") or ""
        reaffirmed = r.get("reaffirmed") or ""
        if r.get("reaffirmed_malformed"):
            ctx.err(
                r["file"],
                f"{rid}: `reaffirmed=` is present but is not a well-formed `reaffirmed=YYYY-MM-DD` discharge token",
            )
        if not because:
            continue
        local, res = _foreign(ctx, because, where=f"{ctx.rel(r['file'])} {rid} Because")
        if res is not None:
            if res.is_error:
                ctx.err(r["file"], f"{rid}: Because `{because}` — {res.message}")
            elif (premise := _foreign_dead(res.record)) and not reaffirmed:
                ctx.notes.append(
                    f"{rid}: its premise `{because}` is now {premise} in corpus `{res.ref.corpus}` — the "
                    "decision's reason may have expired; re-read it and discharge with `reaffirmed=<date>`"
                )
            continue
        because = str(local)
        if because == rid:
            ctx.err(r["file"], f"{rid}: Because points at itself")
        elif because not in rows:
            ctx.err(r["file"], f"{rid}: Because `{because}`, which is not a known requirement id")
        elif (premise := dead(rows[because])) and not reaffirmed:
            ctx.notes.append(
                f"{rid}: its premise `{because}` is now {premise} — the decision's reason may have "
                "expired; re-read it and discharge with `reaffirmed=<date>`"
            )


# --- claim scope: where a `Needs` target sits relative to the PRD claiming the needer ---
# ONE definition, used by three readers: this validator's advisory, the derived status
# generator, and `scripts/requirement_query.py`. A second copy of this predicate would make
# "is this need satisfied" answerable two ways, which is the failure the register's
# single-parser rule exists to prevent.
#
# **The only machine-readable evidence that a prerequisite is BUILT is a `shipped` PRD
# claiming it.** Nothing else in the corpus asserts builtness: the register stores no
# status by construction, and a row's disposition says what we decided, never what exists.
SATISFIED_SCOPES = frozenset({"same-prd", "built", "scheduled"})


def line_is_cut(current_line: str, cut: str) -> bool:
    """The deferral rule as a pure cell comparison — the ONE definition `is_cut` and the
    status derivation both read, so neither can disagree about which line a row lands in.

    True when `cut` names a release line other than the one being built. Blank is never cut,
    and `Cut: v1` while v1 is being built is legal and simply not cut.
    """
    return bool(cut) and cut != current_line


def is_cut(ctx: Context, row: dict[str, Any]) -> bool:
    """Is this row's commitment OUT of the release line being built?

    True when `Cut` names a line other than `ctx.cfg.current_line`. A blank cell — the norm —
    is never cut, and `Cut: v1` while v1 is being built is legal and simply not cut: the
    row is in this line, and said so explicitly rather than by omission.

    Deliberately a comparison against one constant and not a "non-empty" test, so that
    the day v1 ships and `ctx.cfg.current_line` becomes `v2`, seventy-two rows go live without a
    register edit and the check keeps its meaning instead of inverting it.
    """
    return line_is_cut(ctx.cfg.current_line, row.get("cut") or "")


def need_scope(
    ctx: Context,
    dep: str,
    claimant: str | None,
    claims_by_row: dict[str, list[tuple[str, str]]],
    disproven: set[str] | frozenset[str] | None = None,
) -> str:
    """Where `dep` sits relative to `claimant` (a PRD number, or None for "nobody").

    Ordered most-satisfied first, and the order is the point — a need claimed by the same
    PRD is built *with* the work, one claimed by a shipped PRD is already there, one
    claimed by a live PRD is scheduled, and anything else is not on anybody's plan.

      same-prd   the claiming PRD claims the need too — it builds both halves
      built      a `shipped` PRD claims it, and no live disproof says otherwise
      violated   a shipped claim exists, but a register `## Known violations` entry
                 disproves it (ENG-7534) — not a foundation anything else may rest on
      scheduled  a live (non-cancelled) PRD claims it
      orphaned   every PRD that claimed it was cancelled — it LOOKED scheduled
      unclaimed  no PRD has ever claimed it
    """
    cs = claims_by_row.get(dep, [])
    if claimant is not None and any(p == claimant for p, _ in cs):
        return "same-prd"
    live = [(p, s) for p, s in cs if s not in ctx.cfg.claim_history]
    if any(s == "shipped" for _, s in live):
        # A false ship is not builtness. Disproofs are the rare exception list that
        # demotes a shipped claim without walking the PRD off `shipped` (which the
        # lifecycle forbids). Callers that omit `disproven` keep the pre-ENG-7534
        # reading; the status generator and requirement_query pass the set.
        if disproven is not None and dep in disproven:
            return "violated"
        return "built"
    if live:
        return "scheduled"
    return "orphaned" if cs else "unclaimed"


def load_prd_claims(ctx: Context) -> dict[str, list[tuple[str, str]]]:
    """`{requirement id: [(prd number, prd status), …]}` — the realisation edge, by row."""
    out: dict[str, list[tuple[str, str]]] = {}
    base = ctx.prd_dir
    if not base.is_dir():
        return out
    for d in sorted(base.iterdir()):
        f = d / ctx.cfg.prd_file
        if not (d.is_dir() and f.is_file()):
            continue
        fm = frontmatter(f.read_text(encoding="utf-8"))
        if fm is None:
            continue
        num = field(fm, "prd") or d.name
        status = field(fm, "status") or ""
        for rid in claim_ids(ctx, fm):
            out.setdefault(rid, []).append((str(num).zfill(4) if str(num).isdigit() else str(num), status))
    return out


def check_claim_scope(ctx: Context, rows: dict[str, dict[str, Any]]) -> None:
    """A claimed row's `Needs`, split by `Cut`: HARD if the need is out of this line,
    ADVISORY if the need is in this line and simply unscheduled.

    **The defect this exists for**, 2026-08-14: seven of PRD 0486's sixteen claims carried
    `Needs` edges into the plane-side build tier — the mechanism 0486's own biggest Non-Goal
    deletes. Because those rows are `adopted` and *deferred to v2* rather than superseded,
    `check_needs` (which only refuses edges into a `superseded`/`rejected` row) left them
    intact, and the graph asserted that the critical-path PRD was unsatisfiable until v2
    landed. Nobody noticed until a human interrogated the graph by hand.

    **This started as a proxy and stopped being one when `Cut` landed.** The rule worth
    having is *"a claimed row must not depend on a row that is deferred, or otherwise
    outside the claiming PRD's scope"*, and deferral used to be unreadable: a deferred row
    keeps `Disposition: adopted`, so the only observable was *nothing is building the
    prerequisite* — which fires just as loudly on a prerequisite nobody has got to yet. One
    string, two meanings, so the whole check had to be advisory. `Cut` names the release
    line a row lands in, which separates them, and the two halves now get the severity each
    one actually deserves:

      HARD      the need is cut from the line being built and the needer is not. This is
                not a judgement call — the design is resting on a mechanism this version
                does not have, and either the edge is wrong or the scope is. It is not
                ratcheted either: the set was empty the day it landed (the seven edges above
                were repaired in `3ad63c6d7e`), so it lands as a floor of zero.
      ADVISORY  the need is in this line and nothing is building it. Still a question rather
                than a defect — real work nobody has scheduled — but a SHARPER one than
                before, because "deferred on purpose" no longer hides inside it.

    **A cut row may need another cut row**, and that is why the hard half compares the two
    ends rather than testing the need alone: a v2 PRD claiming v2 rows whose needs are also
    v2 is coherent, and a check that failed it would make the column unusable the moment v1
    ships. The invariant is *a row in this line may not rest on a row that is not*.

    **A program-tier row is claimed by the union of its dependents, not by any one of
    them** (RUN-001, ENG-6062): *"every process the platform spawns is an OCI image"*
    only becomes true once every workload category has migrated, so forcing it into one
    PRD's `implements:` would be a paper fix — no single PRD ever builds the whole
    invariant. Two or more DISTINCT live PRDs already resting claimed work on the same
    unclaimed need is that union actually converging on it; the advisory stays live when
    only one PRD does, which is still an open question rather than a program shape.
    """
    claims_by_row = load_prd_claims(ctx)
    live_claims = [(rid, p) for rid, cs in claims_by_row.items() for p, s in cs if s not in ctx.cfg.claim_history]
    hits: dict[str, list[str]] = {}
    for rid, prd in sorted(set(live_claims)):
        r = rows.get(rid)
        if r is None:
            continue  # check_prd_claims owns the dangling-claim error
        for dep in r["needs"]:
            if dep not in rows:
                continue  # check_needs owns the unresolvable edge
            if is_cut(ctx, rows[dep]):
                # Consistent when both ends sit in the same later line — say nothing.
                if is_cut(ctx, r):
                    continue
                ctx.err(
                    r["file"],
                    f"{rid}: is claimed by PRD {prd} but Needs `{dep}`, which is `Cut: {rows[dep]['cut']}` "
                    f"— cut from `{ctx.cfg.current_line}`, the line being built. A claimed row cannot presuppose a "
                    "mechanism this version does not have: either the edge is wrong (re-point it at what "
                    f"`{ctx.cfg.current_line}` actually provides, or drop it, as the design that cut the mechanism "
                    "should have) or the claim is out of scope",
                )
                continue
            scope = need_scope(ctx, dep, prd, claims_by_row)
            if scope not in SATISFIED_SCOPES:
                hits.setdefault(f"{dep} ({scope})", []).append(f"{prd} claims {rid}")
    for target, why in sorted(hits.items()):
        # A FOURTH case need_scope does not model, surfaced by RUN-001 (ENG-6062): a
        # program-tier row realised by several PRDs TOGETHER, so no single one will ever
        # claim it in `implements:` — forcing a claim onto one would be a paper fix. Two
        # or more DISTINCT live PRDs already resting claimed work on the same unclaimed
        # need is that union actually converging on it, not a scheduling gap; one claimant
        # doing so stays exactly the open question the advisory exists to surface.
        distinct_prds = {w.split(" claims ", 1)[0] for w in why}
        if len(distinct_prds) >= 2:
            continue
        ctx.notes.append(
            f"claim-scope: `{target}` — needed by {', '.join(why)} — but no live PRD is building it. "
            f"The row is NOT cut, so this is not a deferral hiding in prose: it is `{ctx.cfg.current_line}` work "
            "nobody has scheduled, or an edge that should not be there. A question, not a defect"
        )


def check_append_order(ctx: Context, rows: dict[str, dict[str, Any]]) -> None:
    """A new id is APPENDED at the end of its register, never inserted mid-file.

    **The failure this prevents is a clean merge, not a dirty one.** Two agents
    authoring requirements concurrently in separate worktrees both read the same
    register and both allocate `max+1`. Each inserts its row next to the rows it
    relates to — different places in the file — so the two diffs apply cleanly to
    each other and land on `main` carrying one id twice. Each side's pre-commit
    hook passed, because on each side the id really was unique. Appending instead
    puts both rows on the same last line, which git cannot merge silently: the
    conflict is raised at the moment the second author still knows what their row
    means. The duplicate-id check downstream of this one is the net, not the fix —
    by the time it fires the register is already wrong on `main`.

    **Appending to the row's own SECTION does not buy this**, which is why the
    rule is the blunt one: two authors working different subjects append to
    different sections, and those merge as cleanly as two mid-file inserts. Only
    a single append point in the file produces the conflict.

    The cost is accepted, not denied: an appended row lands under whatever
    section heading comes last, which is usually not its subject's. A row filed
    under the wrong heading is a reading cost; a duplicate id on `main` is
    corruption. The cost also expires — a register generated from at-site markers
    groups its own output, and has no stable "next to" to insert into anyway.

    **Ratcheted, deliberately, rather than enforced outright.** A hard "ids are
    monotonic in file order" would fail the register as it stands today (ten rows
    sit mid-file), so the rule would have had to arrive with a ten-row move
    through a table another change owns. The predicate is "is this row placed
    above a lower-numbered one" and only ids outside `APPEND_ORDER_BASELINE` are
    errors — the same shape as `validate_prd_mockup_reference.py`'s grandfathered
    set, and the same reasoning: stop the set growing, do not make the guard's
    existence conditional on retro-fitting.

    A baseline id that is PRESENT and no longer misplaced prints a note (remove
    it, or it pre-grandfathers a future regression of that id). A baseline id
    that is absent entirely prints nothing — ids are permanent, so a missing one
    is already a hard error elsewhere, and noting it here would fire on every
    register that simply is not this one.
    """
    grandfathered = frozenset(ctx.cfg.append_order_baseline)
    by_file: dict[Path, list[tuple[int, str, int]]] = {}
    for rid, r in rows.items():
        by_file.setdefault(r["file"], []).append((r["line"], rid, int(rid.split("-")[1])))

    still_misplaced: set[str] = set()
    for f, seq in by_file.items():
        seq.sort()
        lowest_below: int | None = None  # smallest id number appearing AFTER this row
        for _line, rid, num in reversed(seq):
            if lowest_below is not None and num > lowest_below:
                if rid in grandfathered:
                    still_misplaced.add(rid)
                else:
                    ctx.err(
                        f,
                        f"{rid}: is placed above lower-numbered rows — a new id is appended at the "
                        "END of the register, never inserted next to the rows it relates to. Two "
                        "authors who both allocate `max+1` and both insert mid-file produce diffs "
                        "that merge cleanly into one duplicate id; two appends produce a git "
                        "conflict instead, which is the outcome you want",
                    )
            lowest_below = num if lowest_below is None else min(lowest_below, num)

    for rid in sorted(grandfathered - still_misplaced):
        if rid in rows:
            ctx.notes.append(
                f"{ctx.rel(rows[rid]['file'])}: `{rid}` is grandfathered in APPEND_ORDER_BASELINE but is "
                "no longer placed above a lower-numbered row — drop it from the baseline, or it "
                "pre-grandfathers a future misplacement of that same id"
            )


# --- Source form -------------------------------------------------------------
# A numbered heading: `## 3. One declaration…`, `### 3.1 \`ConsumerApp\``.
NUMBERED_HEADING_RE = re.compile(r"^(#{2,6})\s+(\d+(?:\.\d+)*)\.?\s+")
SOURCE_SEP_RE = re.compile(r"\s+·\s+")
# `arch §15 "a registry on the data plane"` — the durable form.
QUOTE_ANCHOR_RE = re.compile(r'^(\S+)\s+§([\d.]+)\s+"(.+)"$')
# `arch §9.2:2071` — legacy, rots on every insertion above it.
SECTION_LINE_ANCHOR_RE = re.compile(r"^(\S+)\s+§([\d.]+):(\d+)$")
# `D7:74` — a line in a decision record, which has no section numbering.
RECORD_LINE_ANCHOR_RE = re.compile(r"^([A-Za-z]\w*):(\d+)$")
# `prd:0495 "callable with the permissions an ordinary end-user holds"` — a PRD
# citation whose path is derivable from the number (glob `knowledge/prds/0495-*/prd.md`),
# so it needs no legend row and must never fall into the silent skip.
#
# The PRD may be another corpus's: `prd:fleet:0899` (`fleet_knowledge.corpusref`). The optional
# qualifier is matched HERE, before the `<tag>:<line>` record form gets a chance to read
# `fleet:0899` as line 899 of a legend tag called `fleet`. Group 1 is the corpus (or None),
# group 2 the number.
PRD_QUOTE_ANCHOR_RE = re.compile(r'^prd:(?:([a-z][a-z0-9-]*):)?(\d{4})\s+"(.+)"$')
PRD_BARE_ANCHOR_RE = re.compile(r"^prd:(?:([a-z][a-z0-9-]*):)?(\d{4})$")
# `gov "GOV-001 — …"`, `sl-139 "…"` — a quoted fragment without a section, resolved
# through the legend like any other tag (a prose description, not a verbatim anchor,
# so it is existence-checked, never fragment-matched).
BARE_QUOTE_ANCHOR_RE = re.compile(r'^(\S+)\s+"(.+)"$')


def prd_target(ctx: Context, num: str) -> Path | None:
    """The `prd.md` a `prd:NNNN` citation names, or None if no such PRD exists.

    PRD paths are the deterministic `knowledge/prds/NNNN-<slug>/prd.md`, derivable from
    the number alone — which is exactly why the register needs no `prd:` legend row.
    """
    matches = sorted(ctx.prd_dir.glob(f"{num}-*/{ctx.cfg.prd_file}"))
    return matches[0] if matches else None


def section_spans(lines: list[str]) -> dict[str, tuple[int, int]]:
    """`{section number: (first line, last line)}`, 1-based and INCLUSIVE.

    A section runs to the next heading at the same or shallower level, so `§3` contains
    `§3.1` — a citation naming the parent section is satisfied by a line inside a child,
    which is how the corpus actually cites (`arch §3.3:445` lands inside `§3.3.1`).
    """
    heads: list[tuple[str, int, int]] = []
    for i, line in enumerate(lines, 1):
        if m := NUMBERED_HEADING_RE.match(line):
            heads.append((m.group(2), i, len(m.group(1))))
    spans: dict[str, tuple[int, int]] = {}
    for idx, (num, start, level) in enumerate(heads):
        end = len(lines)
        for _num2, start2, level2 in heads[idx + 1 :]:
            if level2 <= level:
                end = start2 - 1
                break
        spans.setdefault(num, (start, end))
    return spans


def check_sources(
    ctx: Context, rows: dict[str, dict[str, Any]], baseline: set[tuple[str, str]]
) -> tuple[int, int, int]:
    """Every anchor in a `Source` cell must actually land where it says.

    Three forms, resolved against the register's own Source legend (`source_legend`):

      `<tag> §N "fragment"`  the durable form — the fragment must appear EXACTLY ONCE
                             inside §N. Zero means the sentence was rewritten and the
                             citation now points at nothing; more than one means the
                             anchor is ambiguous and the next edit picks for you. HARD:
                             this is the form the corpus is moving TO, and it was clean
                             on the day this check landed, so it lands as a floor of zero.
      `<tag> §N:L`           legacy line anchor — line L must fall inside §N. Ratcheted,
                             not converted: these rot whenever anything is inserted
                             above them, and a bulk rewrite of the citation format is
                             deliberately NOT this validator's job. The baseline records
                             the ones already broken; only NEW breakage fails.
      `<tag>:L`              a line in a linked record — L must be a line the file has.
                             Records are append-only, so this is a gross-rot check only.

    Two further forms are existence-checked rather than fragment-matched:

      `prd:NNNN "fragment"`  a PRD citation — the PRD path is derivable from the number
                             (`prd_target`), so no legend row is needed and the citation
                             is checked to name a real PRD document. The quoted phrase is
                             a prose description, not a verbatim anchor, so it is never
                             required to appear word-for-word.
      `<tag> "fragment"`     a quoted fragment without a section (e.g. `gov "…"`,
                             `sl-139 "…"`) — the tag must resolve in the legend; the
                             fragment is a description, so only existence is verified.

    The two new forms above are existence-checked and their unresolved tags are reported
    as an advisory with a count — the silence of exactly this case (eleven `prd:`
    citations in end-user.md that the legend could not resolve) is what let unverified
    citations sit invisible. A token in neither form (`0486 R2`, `0486 AC-3`), or a
    section/record anchor whose tag the legend cannot resolve, is skipped and counted —
    a Source may legitimately point at a PRD requirement id, which is not a location
    this check can verify.
    """
    docs: dict[Path, list[str]] = {}
    spans: dict[Path, dict[str, tuple[int, int]]] = {}

    def load(path: Path) -> tuple[list[str], dict[str, tuple[int, int]]]:
        if path not in docs:
            text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
            docs[path] = text.splitlines()
            spans[path] = section_spans(docs[path])
        return docs[path], spans[path]

    legacy: dict[str, str] = {}
    checked = skipped = 0
    unresolved: dict[str, list[str]] = {}
    for rid, r in sorted(rows.items()):
        legend: dict[str, Path] = r["legend"]
        for token in SOURCE_SEP_RE.split(r["source"]):
            token = token.strip()
            if not token:
                continue
            prd_q = PRD_QUOTE_ANCHOR_RE.match(token)
            prd_b = PRD_BARE_ANCHOR_RE.match(token)
            quoted = QUOTE_ANCHOR_RE.match(token)
            sec_line = SECTION_LINE_ANCHOR_RE.match(token)
            rec_line = RECORD_LINE_ANCHOR_RE.match(token)
            prd_m = prd_q or prd_b
            if prd_m is not None:
                corpus, num = prd_m.group(1), prd_m.group(2)
                if corpus is not None and not ctx.corpora.is_local(corpusref.Ref(corpus, num)):
                    res = ctx.corpora.resolve(
                        corpusref.Ref(corpus, num), corpusref.PRD, where=f"{ctx.rel(r['file'])} {rid} Source"
                    )
                    if res.is_error:
                        ctx.err(r["file"], f"{rid}: Source `{token}` — {res.message}")
                    elif not res.unverified:
                        checked += 1
                    continue
                if prd_target(ctx, num) is None:
                    unresolved.setdefault(f"prd:{num}", []).append(rid)
                    continue
                checked += 1
                continue
            anchor = quoted or sec_line or rec_line
            if anchor is not None:
                target = legend.get(anchor.group(1))
                if target is None or not target.is_file():
                    skipped += 1
                    continue
                lines, sections = load(target)
                checked += 1
            else:
                bare = BARE_QUOTE_ANCHOR_RE.match(token)
                if not bare:
                    skipped += 1
                    continue
                tag = bare.group(1)
                target = legend.get(tag)
                if target is None or not target.is_file():
                    unresolved.setdefault(tag, []).append(rid)
                    continue
                lines, sections = load(target)
                checked += 1
            if quoted:
                sec, fragment = quoted.group(2), quoted.group(3)
                if sec not in sections:
                    ctx.err(
                        r["file"],
                        f"{rid}: Source `{token}` names section §{sec}, which {target.name} does not have",
                    )
                    continue
                start, end = sections[sec]
                hits = "\n".join(lines[start - 1 : end]).count(fragment)
                if hits != 1:
                    whole = "\n".join(lines).count(fragment)
                    where = f"{whole} time(s) elsewhere in the file" if whole else "nowhere in the file"
                    ctx.err(
                        r["file"],
                        f"{rid}: Source `{token}` quotes a fragment that appears {hits} time(s) inside "
                        f"§{sec} of {target.name} ({where}) — a quoted anchor must resolve to exactly "
                        "one place, or it is not an anchor",
                    )
            elif sec_line:
                sec, num = sec_line.group(2), int(sec_line.group(3))
                if sec not in sections:
                    legacy[rid] = f"Source `{token}` names section §{sec}, which {target.name} does not have"
                    continue
                start, end = sections[sec]
                if not (start <= num <= end):
                    legacy[rid] = (
                        f"Source `{token}` points at line {num}, which is outside §{sec} "
                        f"(lines {start}-{end}) of {target.name} — the anchor rotted"
                    )
            elif rec_line:
                num = int(rec_line.group(2))
                if num > len(lines):
                    ctx.err(
                        r["file"],
                        f"{rid}: Source `{token}` points at line {num}, but {target.name} has only {len(lines)} lines",
                    )
    if unresolved:
        total = sum(len(v) for v in unresolved.values())
        tags = ", ".join(sorted(f"`{t}` ({len(v)} row(s))" for t, v in unresolved.items()))
        ctx.notes.append(
            f"{total} Source token(s) name a tag the register's legend cannot resolve ({tags}) — an "
            "unresolved citation is an unverified one. Add a legend row, fix the tag, or the citation "
            "stays invisible"
        )
    apply_ratchet(ctx, "source-anchor", legacy, baseline, stale_is_hard=False)
    return checked, skipped, sum(len(v) for v in unresolved.values())


# --- prose citations ----------------------------------------------------------
# Files whose ids are governed elsewhere or are not citations at all.


def _norm_commitment(text: str) -> str:
    """Canonical form of a commitment for verbatim matching.

    Lowercased, emphasis and strikethrough removed, whitespace collapsed, leading /
    trailing sentence punctuation dropped. `~~superseded~~` and **bold** must not trap
    a match, and "X." / "X" / **X** must all be the same string. The register row and
    the prose both pass through this before comparison.
    """
    t = text.replace("~~", "")
    t = re.sub(r"[*_`]", "", t)
    t = t.lower()
    t = re.sub(r"\s+", " ", t)
    return t.strip().strip(" .·:;,")


def _row_origin_files(row: dict[str, Any]) -> set[Path]:
    """The files a row's own `Source` points at (the wording's ORIGIN, not a quote).

    A requirement statement is authored from a decision/spec passage and the register
    row's Source CITIES that passage — so an exact appearance of the statement inside
    one of its own Source targets is the origin, never a restatement. Resolved through
    the register's own Source legend so this never hardcodes a document name.
    """
    out: set[Path] = set()
    for token in SOURCE_SEP_RE.split(row["source"]):
        token = token.strip()
        if not token:
            continue
        tag = re.split(r"[\s:]", token)[0]
        target = row["legend"].get(tag)
        if target is not None and target.is_file():
            out.add(target.resolve())
    return out


def check_uncited_restatements(ctx: Context, rows: dict[str, dict[str, Any]]) -> int:
    """The reverse of the citation edge: a commitment RE-EXPRESSED in prose must cite.

    `check_prose_citations` walks citations -> rows (a cited `RUN-078` resolves and is
    live). It never asks the other question — *does a sentence in prose silently repeat
    a requirement statement it does not cite?* So a spec could quote the 345th
    uncited restatement of some commitment and nothing anywhere says so.

    A restatement is not semantically detectable in general — recognising
    that a sentence asserts the same commitment as a register row is a judgement call,
    and a keyword detector ("the system shall / never") fires on thousands of ordinary
    sentences. The one mechanically falsifiable form is the VERBATIM restatement: a
    requirement statement reappearing word-for-word in prose without that row cited.
    That is caught here, and it is the exact failure the corpus's own one-way citation
    habit produces (a paragraph copied into a design doc with the citation dropped).

    Precise by construction, so it can be a HARD check (a broken citation is hard, and
    this is the same edge read backwards):
      * the whole normalized statement must appear as a sentence-bounded substring —
        a longer ordinary sentence containing it as a subclause does not match;
      * the file must not cite that row's id ANYWHERE (a cited restatement is fine —
        quoting with `[RUN-078]` present is exactly the rule in action);
      * a row's own Source target(s) are exempt (the wording's origin, not a quote);
      * decision records are exempt (they are where commitments are SETTLED — the
        register cites THEM, not the other way round).
    """
    if not rows:
        return 0
    prefixes = sorted({r["prefix"] for r in rows.values()})
    if not prefixes:
        return 0
    id_re = re.compile(rf"\b(?:{'|'.join(prefixes)})-\d{{3,}}\b")  # which ids a file cites
    decisions_dir = ctx.knowledge / ctx.cfg.decisions_dir
    files = [p for p in prose_files(ctx) if decisions_dir not in p.parents]

    # The naive transpose is rows x files (=716 x ~2900) full-text matches — slow for
    # an always_run pre-commit hook. Two cuts make it O(corpus) instead:
    #   1. an inverted word index, and a candidate set that is the INTERSECTION of the
    #      statement's few rarest distinct words' file-sets — `st in nt` implies every
    #      word of `st` is a word of `nt`, so any one missing word rules a file out;
    #   2. each file's normalized text normalised ONCE (pass 1) and held in memory, so
    #      the candidate loop only runs cheap `find`s, never re-normalises whole files.
    word_re = re.compile(r"[a-z0-9]+")
    word_index: dict[str, set[int]] = {}  # word -> file indices containing it
    docfreq: dict[str, int] = {}
    cited_by_idx: dict[int, frozenset[str]] = {}
    nt_by_idx: list[str] = []
    path_by_idx: list[Path] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        idx = len(path_by_idx)
        path_by_idx.append(path)
        nt_by_idx.append(_norm_commitment(text))
        cited_by_idx[idx] = frozenset(id_re.findall(text))
        for w in set(word_re.findall(nt_by_idx[idx])):
            word_index.setdefault(w, set()).add(idx)
    for w, idxs in word_index.items():
        docfreq[w] = len(idxs)

    # resolve each row's Source target files to indices once (origin exemption is rare
    # and cheap; path resolution is the expensive part and must not run per pairing).
    resolved_to_idx = {str(p.resolve()): i for i, p in enumerate(path_by_idx)}

    restated: list[tuple[str, Path, str]] = []  # (rid, prose-file, line)
    for rid, row in sorted(rows.items()):
        st = _norm_commitment(row["statement"])
        if len(st) < ctx.cfg.restatement_min_len:
            continue
        words = sorted(set(word_re.findall(st)), key=lambda w: docfreq.get(w, 0))
        if not words:
            continue
        origin_idxs = {resolved_to_idx[str(o)] for o in _row_origin_files(row) if str(o) in resolved_to_idx}
        candidates: set[int] | None = None
        for w in words[:3]:  # the 3 rarest distinct words; a file must contain each
            hit = word_index.get(w)
            if hit is None or not hit:
                candidates = set()
                break
            if candidates is None:
                candidates = hit
            else:
                candidates &= hit
            if not candidates:
                break
        if not candidates:
            continue
        for idx in candidates:
            if idx in origin_idxs:
                continue  # the row's own Source — the wording's origin, not a quote
            if rid in cited_by_idx.get(idx, ()):
                continue  # the file already cites the row — a quoted restatement is legal
            path = path_by_idx[idx]
            nt = nt_by_idx[idx]
            match = nt.find(st)
            if match < 0:
                continue
            before = nt[match - 1] if match > 0 else " "
            after = nt[match + len(st)] if match + len(st) < len(nt) else " "
            if before not in " .!?;:)'\"":
                continue  # embedded mid-word / mid-sentence — not a standalone commitment
            if after not in " .!?;:(\"'":
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            line = next(
                (i + 1 for i, ln in enumerate(text.splitlines()) if st in _norm_commitment(ln)),
                None,
            )
            restated.append((rid, path, str(line) if line else "?"))
    for rid, path_, lineno in restated:
        ctx.err(
            path_,
            f"{rid} reveals (line {lineno}) the requirement statement quoted verbatim without citing the row — "
            "prose may not restate a commitment, it cites one; add `"
            f"[{rid}]` at (or next to) the restatement so a reader can follow it back",
        )
    return len(restated)


_PROSE_FILES_CACHE: dict[tuple[Path, Path], list[Path]] = {}


def _claude_prose_files(
    claude_dir: Path, skip_dirs: Iterable[str] = (), skip_top_dirs: Iterable[str] = ()
) -> list[Path]:
    """Every `.md` under `.claude/`, with `worktrees/` pruned DURING the walk.

    Agent worktrees are FULL checkouts, so descending one reaches a second copy of
    `knowledge/` and reports every citation twice, attributing violations to paths that
    are not in this tree. That cost a real debugging detour on 2026-08-14 when 154
    findings turned out to be one worktree's reflection.

    The exclusion used to be a filter applied AFTER `claude_dir.rglob("*.md")` had
    already enumerated everything (ENG-8341). With 22 worktrees on disk that walk
    visited 121,786 files in ~39s to keep 45 — 99.96% discarded — and the count grows
    with every worktree an agent creates. Pruning `dirnames` in place (the
    `validate_dockerfile_build_args.py` / ENG-8254 precedent) never enters the subtree
    at all: ~500 files, ~5ms, same 45 kept.

    `git ls-files` (the `validate_journeys.py` / ENG-6005 precedent) would also work
    here, but it would silently change WHAT is validated — a gitignored `.claude/**.md`
    outside `worktrees/` is in scope today — so the walk-pruning precedent is the one
    that fits.
    """
    skip = set(skip_dirs)
    top = set(skip_top_dirs)
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(claude_dir):
        at_top = Path(dirpath) == claude_dir
        dirnames[:] = [d for d in dirnames if d not in skip and not (at_top and d in top)]
        base = Path(dirpath)
        out.extend(base / fn for fn in filenames if fn.endswith(".md"))
    return sorted(out)


def prose_files(ctx: Context) -> list[Path]:
    """Every `.md` that may CITE a requirement: `knowledge/`, `.claude/`, `CLAUDE.md`.

    The registers themselves are exempt (they *define* the ids), and so is the generated
    status artifact, which lists hundreds of ids by construction and would otherwise
    drown the drift advisory in its own output.

    Memoised on `(ctx.root, ctx.knowledge)` — the only globals it reads — because both
    `check_prose_citations` and `check_uncited_restatements` call it, so a run paid the
    tree walk twice (ENG-8341). Keying on the globals rather than `@lru_cache` keeps the
    self-tests correct: they rebind `vr.REPO` / `vr.K` to a fresh temp tree per case.
    """
    key = (ctx.root, ctx.knowledge)
    cached = _PROSE_FILES_CACHE.get(key)
    if cached is not None:
        return list(cached)
    out: list[Path] = []
    if ctx.knowledge.is_dir():
        for p in sorted(ctx.knowledge.rglob("*.md")):
            if p.parent == ctx.register_dir or p.name in ctx.cfg.prose_skip_names:
                continue
            if p == ctx.knowledge / ctx.cfg.status_artifact:
                continue
            out.append(p)
    for extra in ctx.cfg.prose_extra_dirs:
        extra_dir = ctx.root / extra
        if not extra_dir.is_dir():
            continue
        walker = ctx.claude_prose_files
        out.extend(
            walker(extra_dir)
            if walker is not None
            else _claude_prose_files(extra_dir, ctx.cfg.prose_skip_dirs, ctx.cfg.prose_skip_top_dirs)
        )
    for name in ctx.cfg.prose_extra_files:
        extra_file = ctx.root / name
        if extra_file.is_file():
            out.append(extra_file)
    synced = _synced_tier(ctx.root)
    if synced:
        out = [p for p in out if p.resolve() not in synced]
    _PROSE_FILES_CACHE[key] = out
    return list(out)


def _synced_tier(root: Path) -> frozenset[Path]:
    """The files the command sync wrote into a CUSTOMER repository — never read for citations.

    A customer render (any declared `[fleet.commands] namespace`) is text the repository did not
    author and may not edit: its id-shaped examples are illustrations, and reading them against
    the repository's own registers reported "dangling citations" in files nobody there can fix
    (a customer `REQ` register against the core set's `REQ-090` example, 2026-10-16). The home
    render (no namespace declared) is the home project's own tier, whose citations ARE its own
    rows, so it stays in scope. Files under the tier root the sync did not write — a
    repository's own skills, say — stay in scope too: they are the repository's prose.
    """
    from ... import commandsync  # noqa: PLC0415 — the sync module is heavier than this check needs eagerly

    try:
        namespace, _ = commandsync.commands_config(root)
    except Exception:  # noqa: BLE001 — a malformed fleet.toml is another check's finding, not this one's
        return frozenset()
    if not namespace:
        return frozenset()
    return frozenset((root / rel).resolve() for rel in commandsync.read_manifest(root))


def _known_prefix_cite_re(rows: dict[str, dict[str, Any]], owned: Iterable[str] = ()) -> re.Pattern[str] | None:
    """Matcher for ids in a KNOWN register prefix — the shape citations use.

    Scoped to known prefixes on purpose. A Linear key (`ENG-4813`) is the same shape and
    appears everywhere; reading it as a citation would bury the real signal. Known means a
    local register's prefix, or one a declared sibling corpus owns (`owned`).
    """
    prefixes = sorted({r["prefix"] for r in rows.values()} | set(owned))
    if not prefixes:
        return None
    return re.compile(rf"\b(?:{'|'.join(re.escape(p) for p in prefixes)})-\d{{3,}}\b")


def check_prose_citations(ctx: Context, rows: dict[str, dict[str, Any]]) -> tuple[int, int]:
    """A `RUN-078` written in prose must still resolve, and should still be live.

    The rule CLAUDE.md states — *prose may not assert a commitment, it cites one* — had
    no mechanical reading outside a PRD's frontmatter and acceptance criteria. So a spec,
    a design or a slash command could cite a row that was deleted, refused or replaced,
    and nothing anywhere said so; the worked example in CLAUDE.md itself was one.

    Registers themselves are exempt (they *define* the ids); row-statement citations are
    `check_row_statement_citations`.
    """
    cite_re = _known_prefix_cite_re(rows, ctx.corpora.owned)
    known = ctx.corpora.names
    if cite_re is None and not known:
        return 0, 0
    dead: dict[str, set[str]] = {}
    seen = 0
    files = prose_files(ctx)
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            local_ids: list[str] = []
            # A repo-qualified citation (`acme:FLT-104`) first — and only for a corpus this
            # one knows, because in prose `localhost:8000` has the same shape. Then the bare
            # scan over the line with every qualified reference blanked, so the qualified id is
            # never ALSO read as this corpus's own.
            refs = [ref for ref, _start, _end in corpusref.find_refs(line, known=known)]
            if cite_re is not None:
                # A bare id in a prefix a sibling owns (`FLT-104`) is that sibling's row.
                refs.extend(corpusref.Ref(None, rid) for rid in cite_re.findall(corpusref.mask(line)))
            for ref in refs:
                if not ID_RE.match(ref.id):
                    continue
                if (kind := ctx.corpora.kind_of(ref.id)) != corpusref.REQUIREMENT:
                    # `fleet:CAP-1408` shares a requirement id's shape but names a capability
                    # (program, slice): resolved as what it is, and never this check's local row.
                    if not ctx.corpora.is_local(ref):
                        res = ctx.corpora.resolve(ref, kind, where=f"{ctx.rel(path)}:{i}")
                        if res.is_error:
                            ctx.err(path, f"line {i}: cites {res.message}")
                    continue
                if ctx.corpora.is_local(ref):
                    local_ids.append(ref.id)
                    continue
                seen += 1
                res = ctx.corpora.resolve(ref, corpusref.REQUIREMENT, where=f"{ctx.rel(path)}:{i}")
                if res.is_error:
                    ctx.err(path, f"line {i}: cites {res.message}")
                elif (state := _foreign_dead(res.record)) is not None:
                    dead.setdefault(f"{ref} ({res.record and res.record.get('kind')} | {state})", set()).add(
                        ctx.rel(path)
                    )
            for rid in local_ids:
                seen += 1
                row = rows.get(rid)
                if row is None:
                    ctx.err(
                        path,
                        f"line {i}: cites `{rid}`, which does not resolve to a requirement row — "
                        "ids are permanent, so this is a typo or a row someone deleted",
                    )
                    continue
                disp = row["disposition"]
                if row["superseded"] or disp == "rejected":
                    dead.setdefault(f"{rid} ({row['kind']} | {disp})", set()).add(ctx.rel(path))
    for key, citing in sorted(dead.items()):
        shown = sorted(citing)
        ctx.notes.append(
            f"prose cites `{key}` — a dead row — in {len(shown)} file(s): "
            f"{', '.join(shown[:5])}{' …' if len(shown) > 5 else ''}; a citation stands in for the "
            "live commitment, so re-point it or say in the text that the example is historical"
        )
    return seen, len(files)


def check_row_statement_citations(ctx: Context, rows: dict[str, dict[str, Any]]) -> int:
    """A requirement id cited inside another row's Statement must still resolve.

    `check_prose_citations` deliberately skips the registers (they define the ids), and
    Needs/Because already resolve as graph edges. What nothing resolved was a citation
    *inside a Statement cell* — the direction a dangling id travelled when RUN-1238
    cited a nonexistent DOC-011 and every commit gate stayed green (ENG-17141). Same
    known-prefix scope and severity as the prose pass: unresolvable is hard; citing a
    dead row is advisory. A row naming its own id is not a citation.
    """
    cite_re = _known_prefix_cite_re(rows, ctx.corpora.owned)
    known = ctx.corpora.names
    if cite_re is None and not known:
        return 0
    dead_cites: dict[str, set[str]] = {}
    seen = 0
    for rid, r in sorted(rows.items()):
        stmt = r.get("statement") or ""
        if not stmt:
            continue
        cited_ids: list[str] = []
        refs = [ref for ref, _start, _end in corpusref.find_refs(stmt, known=known)]
        if cite_re is not None:
            refs.extend(corpusref.Ref(None, cid) for cid in cite_re.findall(corpusref.mask(stmt)))
        for ref in refs:
            if not ID_RE.match(ref.id):
                continue
            if (kind := ctx.corpora.kind_of(ref.id)) != corpusref.REQUIREMENT:
                if not ctx.corpora.is_local(ref):
                    res = ctx.corpora.resolve(ref, kind, where=f"{ctx.rel(r['file'])} {rid} statement")
                    if res.is_error:
                        where = f"line {r['line']}: " if r.get("line") else ""
                        ctx.err(r["file"], f"{where}{rid}: statement cites {res.message}")
                continue
            if ctx.corpora.is_local(ref):
                cited_ids.append(ref.id)
                continue
            seen += 1
            res = ctx.corpora.resolve(ref, corpusref.REQUIREMENT, where=f"{ctx.rel(r['file'])} {rid} statement")
            if res.is_error:
                where = f"line {r['line']}: " if r.get("line") else ""
                ctx.err(r["file"], f"{where}{rid}: statement cites {res.message}")
            elif not dead(r) and (state := _foreign_dead(res.record)) is not None:
                dead_cites.setdefault(f"{ref} ({res.record and res.record.get('kind')} | {state})", set()).add(rid)
        for cited in cited_ids:
            if cited == rid:
                continue
            seen += 1
            target = rows.get(cited)
            if target is None:
                where = f"line {r['line']}: " if r.get("line") else ""
                ctx.err(
                    r["file"],
                    f"{where}{rid}: statement cites `{cited}`, which does not resolve to a "
                    "requirement row — ids are permanent, so this is a typo or a row someone deleted",
                )
                continue
            # A dead row's Statement often names the premise it refused or replaced — that is
            # history, not a live commitment standing on a dropped one. Only a LIVE row citing
            # a dead target is the drift the prose pass surfaces.
            if dead(r):
                continue
            disp = target["disposition"]
            if target["superseded"] or disp == "rejected":
                dead_cites.setdefault(f"{cited} ({target['kind']} | {disp})", set()).add(rid)
    for key, citing in sorted(dead_cites.items()):
        shown = sorted(citing)
        ctx.notes.append(
            f"row statement cites `{key}` — a dead row — from {len(shown)} row(s): "
            f"{', '.join(shown[:5])}{' …' if len(shown) > 5 else ''}; a citation stands in for the "
            "live commitment, so re-point it or say in the text that the example is historical"
        )
    return seen


def ac_citations(ctx: Context, body: str) -> set[str]:
    """Requirement ids cited under any acceptance-criteria heading of a PRD.

    PRDs spell the heading a dozen ways (`## Acceptance criteria`, `## 11.
    Acceptance criteria`, `## Journeys & Scenarios (-> Acceptance Criteria)`), so
    the heading is matched loosely and every matching section is unioned. Loose
    matching can only ever ADD a region citations are read from, which is the safe
    direction for a one-directional coverage check.
    """
    out: set[str] = set()
    lines = body.splitlines()
    depth = 0  # heading level of the AC section currently open; 0 = none
    for line in lines:
        if m := re.match(r"^(#{2,6})\s+(.*)$", line):
            level = len(m.group(1))
            if re.search(r"acceptance criteri", m.group(2), re.I):
                depth = level
                continue
            if depth and level <= depth:
                depth = 0
            continue
        if depth:
            out.update(AC_CITE_RE.findall(line))
    return out


def check_prd_claims(ctx: Context, rows: dict[str, dict[str, Any]]) -> int:
    """The realisation edge: `implements:` in a PRD, read back by the register.

    Returns the number of (PRD, requirement) claims seen, for the summary line.
    """
    total = 0
    base = ctx.prd_dir
    if not base.exists():
        return 0
    sl_comps = slice_components(ctx)
    reg_comps = register_components(ctx)
    for d in sorted(base.iterdir()):
        f = d / ctx.cfg.prd_file
        if not (d.is_dir() and f.is_file()):
            continue
        text = f.read_text(encoding="utf-8")
        fm = frontmatter(text)
        if fm is None:
            continue  # validate_tracking_metadata owns the missing-frontmatter error
        claims = idlist(fm, "implements")
        status = field(fm, "status") or ""
        if not claims:
            # "Realises no commitment" and "nobody looked" are the same empty field, and
            # every downstream gate has to guess between them. Once a PRD is `designed` it
            # has been through the command that mints rows, so on ground a register already
            # governs the empty field is a hole, not an answer. Uncovered ground stays
            # silent: there is nothing to have claimed.
            if status in ctx.cfg.claim_required and status not in ctx.cfg.claim_history:
                comps = sl_comps.get(corpusref.localize_entry(field(fm, "slice") or "", ctx.corpora.own), [])
                covering = registers_covering(comps, reg_comps)
                if covering:
                    msg = (
                        f"`implements:` is empty at status `{status}`, but "
                        f"{'/'.join(covering)} governs this PRD's ground "
                        f"({', '.join(comps)}) — claim the rows this work realises, or "
                        "state in the design why none applies (prd:design Phase 4c)"
                    )
                    if status in ctx.cfg.claim_presence_enforced:
                        ctx.err(f, msg)
                    else:
                        ctx.notes.append(f"{ctx.rel(f)}: {msg} (advisory: already terminal — backfill)")
            continue
        cited = {ctx.corpora.canonical(c) for c in ac_citations(ctx, text)}
        for claim in claims:
            total += 1
            local, res = _foreign(ctx, claim, where=f"{ctx.rel(f)} implements")
            if res is not None:
                # Another corpus's row (`fleet:FLT-104`): resolved THERE, never against `rows`.
                if res.is_error:
                    ctx.err(f, f"implements {res.message}")
                    continue
                if status in ctx.cfg.claim_history:
                    continue
                # Coverage is a LOCAL rule — this PRD's own acceptance criteria — and holds
                # whether or not the sibling is on disk to say what the row is.
                if ctx.corpora.canonical(claim) not in cited:
                    msg = (
                        f"implements `{claim}` but no acceptance criterion cites it — add "
                        f"`[{claim}]` to the AC that would fail if the requirement were not met"
                    )
                    if status in ctx.cfg.ac_coverage_enforced:
                        ctx.err(f, msg)
                    else:
                        ctx.notes.append(f"{ctx.rel(f)}: {msg} (advisory at status `{status}`; hard from `planned`)")
                if res.unverified:
                    continue
                state = _foreign_dead(res.record)
                if state or (res.record and res.record.get("kind") == "excluded"):
                    msg = (
                        f"implements `{claim}`, whose disposition in corpus `{res.ref.corpus}` is "
                        f"`{state or 'excluded'}` — either the PRD builds something that corpus refused, "
                        "or its register is stale"
                    )
                    if status in ctx.cfg.drift_advisory_only:
                        ctx.notes.append(f"{ctx.rel(f)}: {msg} (advisory: the PRD already shipped)")
                    else:
                        ctx.err(f, msg)
                continue
            rid = str(local)
            row = rows.get(rid)
            # HARD for every status, terminal included: a requirement id is permanent,
            # so unlike a `project:` pointer it can never dangle as legitimate history.
            if row is None:
                ctx.err(
                    f,
                    f"implements `{rid}` does not resolve to a requirement row "
                    "(ids are permanent — check for a typo or a deleted row)",
                )
                continue
            if status in ctx.cfg.claim_history:
                continue  # cancelled: inert history, not re-litigated
            # Coverage — one direction only (a requirement a PRD claims must be
            # verified by something; an AC citing nothing stays legal).
            if ctx.corpora.canonical(claim) not in cited:
                msg = (
                    f"implements `{rid}` but no acceptance criterion cites it — add "
                    f"`[{rid}]` to the AC that would fail if the requirement were not met"
                )
                if status in ctx.cfg.ac_coverage_enforced:
                    ctx.err(f, msg)
                else:
                    ctx.notes.append(f"{ctx.rel(f)}: {msg} (advisory at status `{status}`; hard from `planned`)")
            # Drift — the PRD and the register disagree about whether we are doing this.
            disp = row["disposition"]
            if row["superseded"] or disp == "rejected" or row["kind"] == "excluded":
                what = (
                    "an `excluded` row — a capability we decided not to build"
                    if row["kind"] == "excluded"
                    else f"whose register disposition is `{disp}`"
                )
                msg = (
                    f"implements `{rid}`, {what} — either the PRD builds something we refused, or the register is stale"
                )
                if status in ctx.cfg.drift_advisory_only:
                    ctx.notes.append(f"{ctx.rel(f)}: {msg} (advisory: the PRD already shipped)")
                else:
                    ctx.err(f, msg)
            elif disp == "open":
                msg = (
                    f"implements `{rid}`, which the register still calls `open` "
                    "(no mechanism, or no number) — settle the row now that a PRD is building it"
                )
                # Hard from `designed`: an unsettled promise the design is already building
                # means the design does not yet know what it is building, and `open` is the
                # one disposition that legitimately demands a human
                # (knowledge-model.md -> The claim spine). Advisory below that, because
                # claiming at `prd-drafted` is explicitly provisional.
                if status in ctx.cfg.claim_required:
                    ctx.err(f, msg + " (prd:design Phase 4c), or drop the claim")
                else:
                    ctx.notes.append(f"{ctx.rel(f)}: {msg}")
    return total


def emit_step_summary(lines: list[str]) -> None:
    """Mirror the advisories into `$GITHUB_STEP_SUMMARY` when CI provides it.

    An advisory printed inside a job that goes green is an advisory nobody reads. The
    repo already solved this once — merge_guard_check.py, submodule_pointer_guard_check.py
    and two siblings append to the step summary, which renders on the run's own page —
    so this reuses that channel rather than inventing a third.
    """
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path or not lines:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("## Requirement register — advisories\n\n")
            for line in lines:
                fh.write(f"- {line}\n")
            fh.write(
                "\nAdvisories never fail the build. They mean the register and the corpus around it "
                "have drifted apart — see `knowledge/specs/knowledge-model.md` → *Decisions and "
                "requirements*.\n"
            )
    except OSError:
        pass  # a summary we cannot write is never worth failing a validator over


@dataclass(frozen=True)
class RegisterRun:
    """Everything one full pass produced, for a caller that renders rather than prints.

    The counts are here because the summary line is the ONLY place a reader learns the
    guard actually looked at something — `references resolve` over 0 registers and over
    1700 rows are the same sentence otherwise.
    """

    rows: dict[str, dict[str, Any]]
    registers: list[Path]
    declared_components: dict[str, list[str]]
    known_components: dict[str, str]
    by_disposition: dict[str, int]
    anchors_checked: int
    anchors_skipped: int
    anchors_unresolved: int
    citations: int
    citation_files: int
    uncited_restatements: int
    prd_claims: int


def run_all(ctx: Context) -> RegisterRun:
    """Run every check against `ctx`, filling `ctx.errors` / `ctx.notes`. Prints nothing.

    `main()` is this plus the printing; a board is this plus its own rendering. Splitting
    them is what keeps the two from drifting into two different verdicts.
    """
    # Per-run memo (ENG-8341): the prose corpus is walked once and reused by both
    # citation checks. Cleared here so a run never inherits a previous run's tree —
    # the self-tests rebind ctx.root/ctx.knowledge to a fresh temp dir per case.
    _PROSE_FILES_CACHE.clear()
    rows = load_registers(ctx)
    check_owned_prefixes(ctx, rows)
    baseline = load_baseline(ctx.baseline_path)
    known_components = registered_components(ctx)
    declared_components = register_components(ctx)
    check_register_components(ctx, declared_components, known_components)
    check_supersession(ctx, rows)
    check_supersession_terminality(ctx, rows, baseline)
    check_needs(ctx, rows)
    check_because(ctx, rows)
    check_claim_scope(ctx, rows)
    check_append_order(ctx, rows)
    check_kind_disposition(ctx, rows, baseline)
    anchors_checked, anchors_skipped, anchors_unresolved = check_sources(ctx, rows, baseline)
    cites, cite_files = check_prose_citations(ctx, rows)
    cites += check_row_statement_citations(ctx, rows)
    uncited = check_uncited_restatements(ctx, rows)
    claims = check_prd_claims(ctx, rows)

    registers = sorted({r.get("register_file") or r["file"] for r in rows.values()})
    by_disp: dict[str, int] = {}
    for r in rows.values():
        key = "superseded" if r["superseded"] else r["disposition"]
        by_disp[key] = by_disp.get(key, 0) + 1
    unconfirmed_bare = sorted(
        rid for rid, r in rows.items() if r["superseded"] and not r["superseded_by"] and not r["superseded_confirmed"]
    )
    # Never a silent pass: every reference into a declared corpus that is not on disk here
    # (`[fleet.planning.corpora] name = ""`) is counted and named, once.
    if unverified := ctx.corpora.summary():
        ctx.notes.append(unverified)
    if unconfirmed_bare:
        ctx.notes.append(
            f"{len(unconfirmed_bare)} row(s) carry a bare `superseded` with no successor and no "
            f"`(confirmed)` marker ({', '.join(unconfirmed_bare[:8])}{' …' if len(unconfirmed_bare) > 8 else ''}) "
            "— the commitment was dropped rather than replaced; if that is still intended, set "
            "Disposition to `superseded (confirmed)`"
        )
    return RegisterRun(
        rows=rows,
        registers=registers,
        declared_components=declared_components,
        known_components=known_components,
        by_disposition=by_disp,
        anchors_checked=anchors_checked,
        anchors_skipped=anchors_skipped,
        anchors_unresolved=anchors_unresolved,
        citations=cites,
        citation_files=cite_files,
        uncited_restatements=uncited,
        prd_claims=claims,
    )


def main(ctx: Context) -> int:
    run = run_all(ctx)
    rows = run.rows
    registers = run.registers
    by_disp = run.by_disposition
    declared_components, known_components = run.declared_components, run.known_components
    anchors_checked, anchors_skipped, anchors_unresolved = (
        run.anchors_checked,
        run.anchors_skipped,
        run.anchors_unresolved,
    )
    cites, cite_files, uncited, claims = run.citations, run.citation_files, run.uncited_restatements, run.prd_claims

    if ctx.notes:
        print(f"advisory — {len(ctx.notes)} note(s):")
        for n in ctx.notes:
            print(f"- {n}")
        emit_step_summary(ctx.notes)

    if ctx.errors:
        print("requirement register validation failed:")
        for e in ctx.errors:
            print(f"- {e}")
        return 1

    disp_summary = ", ".join(f"{n} {k}" for k, n in sorted(by_disp.items(), key=lambda kv: -kv[1]))
    needs_edges = sum(len(r["needs"]) for r in rows.values())
    cut = sum(1 for r in rows.values() if is_cut(ctx, r))
    claimed_components = {c for ids in declared_components.values() for c in ids}
    print(
        f"requirements OK — {len(registers)} register(s), {len(rows)} requirements"
        f"{f' ({disp_summary})' if disp_summary else ''}; "
        f"{cut} cut from `{ctx.cfg.current_line}`; "
        f"{needs_edges} Needs edge(s), {claims} PRD claim(s); "
        f"{len(claimed_components)}/{len(known_components)} component(s) claimed by a register; "
        f"{anchors_checked} source anchor(s) resolved ({anchors_skipped} not location-shaped"
        f"{f', {anchors_unresolved} unresolvable — see advisory' if anchors_unresolved else ''}); "
        f"{cites} prose citation(s) across {cite_files} file(s); references resolve"
        f"{f'; {uncited} uncited verbatim restatement(s)' if uncited else ''}"
    )
    return 0
