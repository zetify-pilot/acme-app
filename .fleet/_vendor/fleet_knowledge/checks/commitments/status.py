"""The derived answer to *"what did we decide that is not built yet."* — as DATA.

The requirement register deliberately carries **no Status column and no PRD column**:
whether a commitment is built, and by which PRD, is *derived* from PRDs' `implements:`,
never stored. Its header says so — *"Ask the generator, not the file."*

This module is that derivation, and nothing else. It returns objects; it renders nothing.
The markdown ledger `scripts/gen_requirement_status.py` writes is ONE consumer of it, and
a board that wants the backlog as rows is another — which is the whole reason the queries
moved here. Before, the only way to read them was to read a generated file, so a consumer
that wanted the numbers had to re-derive them and could disagree with the ledger.

Four queries "fall out" of the `implements:` edge, and all four are here:

  Backlog   — an `adopted` row no live PRD claims. THE headline number: a commitment we
              made and have not scheduled.
  Orphans   — a row whose ONLY claiming PRDs were cancelled. It looked scheduled, the
              schedule evaporated, and nothing said so. Also: a claim naming an id that
              no longer resolves — normally impossible, because the register validator
              fails the commit on one, but carried rather than assumed.
  Drift     — a live claim on a `rejected`, `superseded` or `open` row: either the PRD
              builds something we refused, or the register is stale.
  Violations— a claimed row with a live disproof. The route back the lifecycle otherwise
              lacks: a PRD cannot walk off `shipped`, but the row can read `violated`
              until the disproof is discharged. Countable, not invisible.

Plus the query that is not about a row: **Components**. A reader arrives holding a touched
PATH, turns it into a component id, and needs the register(s) that govern it; a register
is addressed by domain, and nothing maps one to the other. So the `components:` a register
declares is transposed here into `component -> register(s)`, plus its inverse — the
registered components no register claims, which is the honest coverage number and the one
that should shrink.

**Per-row status is derived from the claiming PRDs' own `status:` *and* any live
disproof.** The most advanced live claim wins among PRD statuses; a live disproof (a row
in a register's `## Known violations` table) overrides to `violated`, because a PRD's
status records how far the work got, never whether the commitment holds (ENG-7534).
`cancelled` claims are ignored unless they are all there is (that is the orphan case).

Ported from `scripts/gen_requirement_status.py`'s derivation half unchanged; the PRD
lifecycle order and the violations heading are configuration whose defaults are that
file's values.

**Nothing here computes a date, a duration, a rate or a projection.** Counts and
dependency order only.

Stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from ... import requirements as kkreq
from . import registers as vr
from .context import Context

# A live disproof is a row in a register's `## Known violations` table. Issue keys and
# requirement ids share the PREFIX-NNN shape; the tracker's prefix is reserved from the
# register (`CommitmentsConfig.reserved_prefixes`), so the two never collide.
_ID_TOKEN_RE = re.compile(r"\b([A-Z]{2,5}-\d{3,})\b")
# The row cell may name another corpus's row: qualified (`fleet:FLT-104`) or bare in a prefix
# a sibling owns. The qualifier is kept so the id is canonicalised, never read as local.
_ROW_TOKEN_RE = re.compile(r"(?<![\w:])((?:[a-z][a-z0-9-]*:)?[A-Z]{2,5}-\d{3,})\b")
_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")
_KNOWN_VIOLATIONS_HEADING = re.compile(r"^known\s+violations\b", re.I)

TERMINAL_DISPOSITIONS = frozenset({"rejected", "superseded"})


@dataclass(frozen=True)
class Row:
    """The projection of a requirement this derivation is allowed to depend on.

    Deliberately NOT the register row: no `Source`. That column is a property of the
    hand-maintained table and is the one field a marker migration *deletes* rather than
    re-derives (`Source` becomes the marker's own location), so depending on it here would
    harden the format this query is meant to outlive.

    `statement`, `needs` and `cut` carry defaults so a substituted row source may omit
    them — they are here because all three survive the inversion rather than despite it.
    """

    id: str
    register: str  # the register's domain, e.g. "workload-runtime"
    section: str  # the heading the row sits under — the grouping the backlog renders by
    kind: str
    disposition: str  # normalised: bare `superseded`, never `superseded by X`
    statement: str = ""
    needs: tuple[str, ...] = ()  # the 5th DAG: requirement -> requirement build order
    cut: str = ""  # the release line this row lands in; blank = the line being built
    because: str = ""  # the premise edge: the row this decision rested on
    reaffirmed: str = ""  # the re-read discharge token, `YYYY-MM-DD`, or ""


@dataclass(frozen=True)
class Claim:
    prd: str  # zero-padded number, e.g. "0482"
    title: str
    status: str
    requirement: str


@dataclass(frozen=True)
class Disproof:
    """A live witness that a claimed commitment does not hold.

    Sourced from a register's `## Known violations` table — never from a PRD's `status:`,
    which records how far the *work* got and cannot say whether the *commitment* holds
    (ENG-7534). Discharge is removing the table row once the disproving issue closes;
    status stays derived.
    """

    requirement: str
    issues: tuple[str, ...]
    reason: str = ""


def load_rows(ctx: Context, warn: bool = True) -> tuple[list[Row], list[str]]:
    """**THE SWAP POINT.** Every requirement this derivation reports on, in corpus order.

    The only function here that knows where rows COME FROM. Today they are parsed out of
    the markdown tables in the registers, via the register loader — so there is exactly one
    table parser. The expected next step is for the register to become generated from
    terse at-site markers on the sentence that actually makes each commitment, at which
    point *only this function changes* and every query below is unaffected.

    Returns `(rows, structural problems)`. The register validator owns failing the build
    on a malformed register; this returns what it could read and says what it could not,
    so a broken register never silently produces a confident-looking answer.
    """
    ctx.reset()
    raw: dict[str, dict[str, Any]] = vr.load_registers(ctx)
    problems = list(ctx.errors) if warn else []
    out: list[Row] = []
    for rid, r in raw.items():
        out.append(
            Row(
                id=rid,
                register=Path(r.get("register_file") or r["file"]).stem,
                section=r["section"],
                kind=r["kind"],
                disposition="superseded" if r["superseded"] else r["disposition"],
                statement=r["statement"],
                needs=tuple(r["needs"]),
                cut=r.get("cut", ""),
                because=r.get("because", ""),
                reaffirmed=r.get("reaffirmed", ""),
            )
        )
    return out, problems


def load_claims(ctx: Context) -> list[Claim]:
    """Every `implements:` edge, read from the PRD side.

    The edge runs from the PRD and not from the requirement for the reason the knowledge
    model gives: a PRD changes as work happens while a requirement does not, and a claim
    made *by* the work is checkable the moment the work lands.
    """
    out: list[Claim] = []
    base = ctx.prd_dir
    if not base.is_dir():
        return out
    for d in sorted(base.iterdir()):
        f = d / ctx.cfg.prd_file
        if not (d.is_dir() and f.is_file()):
            continue
        fm = vr.frontmatter(f.read_text(encoding="utf-8"))
        if fm is None:
            continue
        claims = vr.claim_ids(ctx, fm)
        if not claims:
            continue
        num = vr.field(fm, "prd") or d.name
        for rid in claims:
            out.append(
                Claim(
                    prd=str(num).zfill(4) if str(num).isdigit() else str(num),
                    title=vr.field(fm, "title") or "",
                    status=vr.field(fm, "status") or "",
                    requirement=rid,
                )
            )
    return out


def load_disproofs(ctx: Context) -> list[Disproof]:
    """Every live disproof, read from register `## Known violations` tables.

    Offline and stdlib-only on purpose: this must stay runnable in CI without a tracker,
    and a hand-maintained *exception list* (rare, dischargeable by deleting a row) is the
    opposite of a hand-maintained status column (one cell per commitment, silently stale).
    A PRD's `status: shipped` is not evidence the commitment holds — that is exactly the
    lie ENG-7534 closes.
    """
    out: list[Disproof] = []
    for f in ctx.registers():
        for d in parse_known_violations(f.read_text(encoding="utf-8")):
            out.append(replace(d, requirement=ctx.corpora.canonical(d.requirement)))
    return out


def is_foreign(rid: str) -> bool:
    """A canonical id naming another corpus's row (`fleet:FLT-104`) — never this corpus's to
    resolve, so never "dangling" here."""
    return ":" in rid


def parse_known_violations(text: str) -> list[Disproof]:
    """Pull Disproof rows out of a register's `## Known violations` section.

    Tolerant of the prose that surrounds the table. First column = requirement id; last
    column = one or more issue keys; middle columns = free-text reason.
    """
    lines = text.splitlines()
    i = 0
    found: list[Disproof] = []
    while i < len(lines):
        hm = _HEADING_RE.match(lines[i])
        if not (hm and _KNOWN_VIOLATIONS_HEADING.match(hm.group(1).strip())):
            i += 1
            continue
        i += 1
        # Consume until the next ## heading (or EOF).
        body: list[str] = []
        while i < len(lines) and not _HEADING_RE.match(lines[i]):
            body.append(lines[i])
            i += 1
        found.extend(_parse_violations_table(body))
    return found


def _parse_violations_table(body: list[str]) -> list[Disproof]:
    rows: list[Disproof] = []
    header_seen = False
    for raw in body:
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip().strip("`") for c in line.strip("|").split("|")]
        if not cells:
            continue
        # Skip the markdown separator and the header row.
        if all(set(c) <= set("-: ") and c for c in cells):
            header_seen = True
            continue
        if not header_seen:
            # Header row itself (Row / Not honoured because / Issue).
            header_seen = True
            continue
        rid_tokens = _ROW_TOKEN_RE.findall(cells[0])
        if not rid_tokens:
            continue
        rid = rid_tokens[0]
        issue_cell = cells[-1] if len(cells) > 1 else ""
        issues = tuple(_ID_TOKEN_RE.findall(issue_cell))
        reason = cells[1].strip() if len(cells) > 2 else ""
        rows.append(Disproof(requirement=rid, issues=issues, reason=reason))
    return rows


def derived_status(ctx: Context, claims: list[Claim], disproofs: list[Disproof] | None = None) -> str:
    """A row's status, derived from claims *and* live disproofs — never stored on the row.

    The most advanced LIVE claim wins among PRD statuses: a requirement is satisfied by
    whichever work actually got furthest, so a second PRD still at `designed` does not
    drag a `shipped` row backwards. If every claim was cancelled the row is `orphaned`.

    A live disproof overrides every claim status (ENG-7534). A PRD's `status:` records how
    far the *work* got; it cannot say whether the *commitment* holds. Without this
    override a false or premature `shipped` is invisible — the opposite of what the
    register exists to make countable. `violated` is distinct from both `shipped` and
    `unclaimed`.
    """
    if disproofs:
        return "violated"
    if not claims:
        return "unclaimed"
    cancelled = ctx.cfg.prd_cancelled
    order = ctx.cfg.prd_order
    live = [c for c in claims if c.status != cancelled]
    if not live:
        return "orphaned"
    ranked = sorted(live, key=lambda c: order.index(c.status) if c.status in order else -1)
    return ranked[-1].status


def current_line_backlog(ctx: Context, rows: list[Row], status: dict[str, str]) -> list[Row]:
    """The subset of the backlog that is real WORK in the line being built — the number that
    moves the day a scope decision marks rows for a later line.

    `StatusReport.backlog` is the headline and keeps every adopted unclaimed row, deliberately:
    it is a number many documents already cite. But two classes of that total are not work in
    the current line, so a reader asking "how much is left to schedule" must not be shown them
    as backlog:

      * a `Kind` that can never be claimed by a PRD at all — `accepted` (a cost taken on
        purpose) and `excluded` (a capability we refuse to build); and
      * a `Cut` naming a release line other than the one being built — a scope decision kept in
        a third column precisely so the row itself does not move.

    Both rules are read from their ONE definition (`requirements.SETTLED_KINDS` and
    `registers.line_is_cut`) rather than re-derived here, so this figure and the checks that
    own those rules cannot drift apart.
    """
    return [
        r
        for r in rows
        if r.disposition == "adopted"
        and status[r.id] == "unclaimed"
        and r.kind not in kkreq.SETTLED_KINDS
        and not vr.line_is_cut(ctx.cfg.current_line, r.cut)
    ]


def component_index(ctx: Context) -> tuple[dict[str, list[str]], dict[str, str]]:
    """`({component id: registers claiming it}, {component id: layer})`.

    The transpose of every register's frontmatter `components:`. Read through the same
    loader the guard uses, so the declaration has ONE parser: a second reader that
    disagreed about what a declaration says would let the index and the guard drift, and
    an index the guard does not cover is the dead lookup all over again.

    Registry order is preserved (the registry groups by layer), and a component with no
    register is present with an empty list — the gap is the point, so it is carried rather
    than filtered here.
    """
    layers: dict[str, str] = vr.registered_components(ctx)
    index: dict[str, list[str]] = {cid: [] for cid in layers}
    for domain, ids in vr.register_components(ctx).items():
        for cid in ids:
            index.setdefault(cid, []).append(domain)
    return index, layers


@dataclass(frozen=True)
class StatusReport:
    """Everything the four queries answer, in one object a caller can render or count."""

    rows: list[Row]
    claims: list[Claim]
    disproofs: list[Disproof]
    status: dict[str, str]  # requirement id -> derived status
    claims_by_row: dict[str, list[Claim]]
    disproofs_by_row: dict[str, list[Disproof]]
    backlog: list[Row]  # `adopted`, claimed by nobody — the headline number
    backlog_current: list[Row]  # the part of `backlog` that is claimable work in the line being built
    unsettled: list[Row]  # `open` — decided nothing yet
    orphans: list[Row]  # every claiming PRD was cancelled
    violated: list[Row]  # a live disproof stands against a claim
    claimed: list[Row]  # some PRD claims it, or a disproof names it
    drift: list[tuple[Row, Claim]]  # a live claim on a terminal or `open` row
    dangling_claims: list[str]  # `implements:` naming an id no register has
    dangling_disproofs: list[str]  # a violations row naming an id no register has
    components: dict[str, list[str]] = field(default_factory=dict)
    component_layers: dict[str, str] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)

    @property
    def registers(self) -> set[str]:
        return {r.register for r in self.rows}

    @property
    def unclaimed_components(self) -> list[str]:
        return [cid for cid, regs in self.components.items() if not regs]


def report(ctx: Context) -> StatusReport:
    """Run every query once. The one entry point a board or a generator calls."""
    rows, problems = load_rows(ctx)
    claims = load_claims(ctx)
    disproofs = load_disproofs(ctx)

    by_row: dict[str, list[Claim]] = {}
    for c in claims:
        by_row.setdefault(c.requirement, []).append(c)
    by_disproof: dict[str, list[Disproof]] = {}
    for d in disproofs:
        by_disproof.setdefault(d.requirement, []).append(d)

    index = {r.id: r for r in rows}
    status = {r.id: derived_status(ctx, by_row.get(r.id, []), disproofs=by_disproof.get(r.id)) for r in rows}
    cancelled = ctx.cfg.prd_cancelled

    comp_index, comp_layers = component_index(ctx)
    return StatusReport(
        rows=rows,
        claims=claims,
        disproofs=disproofs,
        status=status,
        claims_by_row=by_row,
        disproofs_by_row=by_disproof,
        backlog=[r for r in rows if r.disposition == "adopted" and status[r.id] == "unclaimed"],
        backlog_current=current_line_backlog(ctx, rows, status),
        unsettled=[r for r in rows if r.disposition == "open"],
        orphans=[r for r in rows if status[r.id] == "orphaned"],
        violated=[r for r in rows if status[r.id] == "violated"],
        claimed=[r for r in rows if by_row.get(r.id) or by_disproof.get(r.id)],
        drift=[
            (index[c.requirement], c)
            for c in claims
            if c.requirement in index
            and c.status != cancelled
            and index[c.requirement].disposition in TERMINAL_DISPOSITIONS | {"open"}
        ],
        dangling_claims=sorted(
            {c.requirement for c in claims if c.requirement not in index and not is_foreign(c.requirement)}
        ),
        dangling_disproofs=sorted(
            {d.requirement for d in disproofs if d.requirement not in index and not is_foreign(d.requirement)}
        ),
        components=comp_index,
        component_layers=comp_layers,
        problems=problems,
    )
