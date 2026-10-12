#!/usr/bin/env python3
"""Generate knowledge/requirement-status.md — the derived answer to *"what did we
decide that is not built yet."*

The requirement register deliberately carries **no Status column and no PRD column**:
whether a commitment is built, and by which PRD, is *derived* from PRDs' `implements:`,
never stored. Its header says so — *"Ask the generator, not the file."* Until this
script existed there was no generator, so the register's whole justification
(knowledge-model.md: *"a prose spec cannot answer 'what did we decide that is not built
yet', and that question is the whole point"*) was a promise nothing kept.

knowledge-model.md names three queries that "fall out" of the `implements:` edge, and
this renders all three plus the per-row status they are computed from:

  Backlog   — an `adopted` row no live PRD claims. THE headline number: a commitment we
              made and have not scheduled. (Rendered per section, because "which part of
              the architecture is unclaimed" is the actionable form of it.) The subset that
              is claimable work in the line being built is reported beside it, so a scope
              decision that marks rows for a later line is visible in the number that day.
  Orphans   — a row whose ONLY claiming PRDs were cancelled. It looked scheduled, the
              schedule evaporated, and nothing said so. Also: a claim naming an id that
              no longer resolves — normally impossible, because validate_requirements.py
              fails the commit on one, but rendered rather than assumed.
  Drift     — a live claim on a `rejected`, `superseded` or `open` row: either the PRD
              builds something we refused, or the register is stale.
  Status    — per row, derived from the claiming PRDs' own `status:` *and* any live
              disproof. The most advanced live claim wins among PRD statuses; a live
              disproof (a row in a register's `## Known violations` table) overrides to
              `violated`, because a PRD's status records how far the work got, never
              whether the commitment holds. `cancelled` claims are ignored
              unless they are all there is (that is the orphan case).
  Violations— a claimed row with a live disproof. The route back the lifecycle otherwise
              lacks: a PRD cannot walk off `shipped`, but the row can read `violated`
              until the disproof is discharged. Countable, not invisible.
  Components— the query that is not about a row. A reader arrives holding a touched PATH,
              turns it into a component id with `knowledge/scripts/component_of.py`, and needs the
              register(s) that govern it; a register is addressed by domain, and nothing
              maps one to the other. So the `components:` a register declares is
              transposed here into `component -> register(s)`, plus its inverse — the
              registered components no register claims, which is the honest coverage
              number and the one that should shrink. `check` §3 reads exactly
              this table.

**Generated on demand, never committed** (2026-09-28), following
gen_decision_ledger.py / gen_roadmap.py. It used to be committed and diff-checked, on the
argument that a generated file nobody can read without first knowing to run a script is
inert. The price of that was the most conflict-prone path in the repository: every PR that
touched a register or a PRD's `implements:` rewrote it, so two unrelated PRs collided on it
by construction (419 touches on `main` in 30 days), and neither a merge driver nor a bot
writer removed the collision — GitHub decides mergeability without either. So the readers
render it instead: every command that reads the `## Component index` runs this script
first, a repository's `make ledgers` renders it for a human, and CI renders it in-run
(`--check`) so a register the derivation cannot read still fails the build.

Run: python3 knowledge/scripts/gen_requirement_status.py           (renders the artifact)
     python3 knowledge/scripts/gen_requirement_status.py --check   (renders in memory; fails if it cannot)
Stdlib only.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

# `fleet_knowledge` is installed, or lives in the fleet submodule; `_repo` is the one module
# that knows where, and refuses with the repair command when it is absent.
_repo.fleet_knowledge()
REPO = _repo.repo_root()

# **The DERIVATION moved to `fleet_knowledge.checks.commitments.status`; what stays here is the
# RENDERING.** The split is the point: the four queries are now readable as DATA by anything
# — a board, a CLI, another generator — so a consumer that wants the backlog no longer has to
# parse the markdown this file writes, which is how a second, disagreeing answer used to get
# made. Every query, every status rule and every field is unchanged.
from fleet_knowledge.checks.commitments import status as kkstatus  # noqa: E402
from fleet_knowledge.checks.commitments.context import Context  # noqa: E402
from fleet_knowledge.checks.commitments.options import CommitmentsConfig  # noqa: E402

# `requirement_query.py` reaches the register grammar and `need_scope` through `grs.vr`, and
# asserts it is the SAME module the validator uses — the one-parser property, tested rather
# than trusted. Kept as an alias of this repo's validator binding.
_VR = Path(__file__).resolve().parent / "validate_requirements.py"
_spec = importlib.util.spec_from_file_location("_grs_vr_reuse", _VR)
assert _spec and _spec.loader
vr: Any = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("_grs_vr_reuse", vr)
_spec.loader.exec_module(vr)

CONFIG = CommitmentsConfig()
K = REPO / "knowledge"
TARGET = K / "requirement-status.md"

# A PRD's lifecycle, least to most advanced. `cancelled` is off the ladder on purpose: it is
# not a stage, it is the absence of one.
PRD_ORDER = CONFIG.prd_order
CANCELLED = CONFIG.prd_cancelled
TERMINAL_DISPOSITIONS = set(kkstatus.TERMINAL_DISPOSITIONS)

Row = kkstatus.Row
Claim = kkstatus.Claim
Disproof = kkstatus.Disproof


def _ctx() -> Context:
    """Built from THIS module's globals on every call — the self-tests rebind `K` at a temp
    tree between cases, and capturing it at import would keep reading the tree the process
    started in."""
    return Context(root=REPO, knowledge=K, cfg=CONFIG)


def load_rows() -> list[Row]:
    """**THE SWAP POINT.** Every requirement this artifact reports on, in corpus order.

    The only place that knows where rows COME FROM lives in the kit now — one table parser
    for the whole repository. A malformed register is reported to stderr and the rest is
    rendered, so a broken register never silently produces a confident-looking artifact.
    """
    rows, problems = kkstatus.load_rows(_ctx())
    if problems:
        print(
            f"warning: {len(problems)} structural problem(s) in the register(s) — "
            "run knowledge/scripts/validate_requirements.py; the rendered status may be incomplete",
            file=sys.stderr,
        )
    return rows


def load_claims() -> list[Claim]:
    """Every `implements:` edge, read from the PRD side."""
    return kkstatus.load_claims(_ctx())


def load_disproofs() -> list[Disproof]:
    """Every live disproof, read from register `## Known violations` tables."""
    return kkstatus.load_disproofs(_ctx())


def derived_status(claims: list[Claim], disproofs: list[Disproof] | None = None) -> str:
    """A row's status, derived from claims *and* live disproofs — never stored on the row."""
    return kkstatus.derived_status(_ctx(), claims, disproofs)


def component_index() -> tuple[dict[str, list[str]], dict[str, str]]:
    """`({component id: registers claiming it}, {component id: layer})`."""
    return kkstatus.component_index(_ctx())


def generated_blockquote() -> list[str]:
    """The header blockquote, rendered verbatim at the top of the artifact.

    A named function rather than an inline list so a test can assert the sentence that says
    *why the file is not committed* without standing up a whole corpus. That rationale has to
    travel with the artifact, not live only in `knowledge-model.md` (put it here;
     reversed what it says).
    """
    return [
        "> **Generated** by `knowledge/scripts/gen_requirement_status.py` — **do not edit by hand; run the",
        "> generator.** Every number here is derived from three things and nothing else: a register",
        "> row's `Disposition`, the `implements:` edge PRDs declare, and any live disproof listed in a",
        "> register's `## Known violations` table. The register carries no status column on purpose —",
        '> a hand-maintained one goes stale silently, and a stale "shipped" is worse than no answer.',
        "> See [`knowledge-model.md`](specs/knowledge-model.md) → *Decisions and requirements*.",
        "",
        "> **It is not committed** (ENG-12971): every register or `implements:` edit rewrote it, so",
        "> unrelated changes collided on it by construction. Its `## Component index` is read **as",
        "> data** by `check` / `route` / `prd:create` / `slice:create` — the only component→register",
        "> join — and each of them renders this file first; nothing reads a stored copy.",
        "",
    ]


def render() -> str:
    rows = load_rows()
    claims = load_claims()
    disproofs = load_disproofs()
    by_row: dict[str, list[Claim]] = {}
    for c in claims:
        by_row.setdefault(c.requirement, []).append(c)
    by_disproof: dict[str, list[Disproof]] = {}
    for d in disproofs:
        by_disproof.setdefault(d.requirement, []).append(d)
    index = {r.id: r for r in rows}
    status = {r.id: derived_status(by_row.get(r.id, []), disproofs=by_disproof.get(r.id)) for r in rows}

    backlog = [r for r in rows if r.disposition == "adopted" and status[r.id] == "unclaimed"]
    backlog_current = kkstatus.current_line_backlog(_ctx(), rows, status)
    backlog_current_ids = {r.id for r in backlog_current}
    unsettled = [r for r in rows if r.disposition == "open"]
    orphans = [r for r in rows if status[r.id] == "orphaned"]
    violated = [r for r in rows if status[r.id] == "violated"]
    dangling = sorted({c.requirement for c in claims if c.requirement not in index})
    dangling_disproofs = sorted({d.requirement for d in disproofs if d.requirement not in index})
    drift = [
        (index[c.requirement], c)
        for c in claims
        if c.requirement in index
        and c.status != CANCELLED
        and index[c.requirement].disposition in TERMINAL_DISPOSITIONS | {"open"}
    ]
    claimed = [r for r in rows if by_row.get(r.id) or by_disproof.get(r.id)]

    lines: list[str] = []
    lines += ["---", "type: requirement-status", "generated: knowledge/scripts/gen_requirement_status.py", "---", ""]
    lines += ["# Requirement status — derived, never stored", ""]
    lines += generated_blockquote()
    lines += [
        f"**{len(rows)}** requirements across **{len({r.register for r in rows})}** register(s) · "
        f"**{len(claims)}** claim(s) from **{len({c.prd for c in claims})}** PRD(s) · "
        f"**{len(backlog)}** adopted rows no PRD claims · "
        f"**{len(backlog_current)}** of them claimable work in the `{CONFIG.current_line}` line"
        + (f" · **{len(violated)}** violated" if violated else "")
        + ".",
        "",
    ]

    comp_index, comp_layers = component_index()
    comp_claimed = [cid for cid, regs in comp_index.items() if regs]
    comp_unclaimed = [cid for cid, regs in comp_index.items() if not regs]
    lines += [
        "## Component index — which register governs which component",
        "",
        "**The join a reader actually arrives by.** A register is addressed by *domain*, and",
        "nobody holds a domain: they hold a touched path, which `knowledge/scripts/component_of.py` turns",
        "into a component id. This transposes every register's frontmatter `components:` so that",
        "id resolves to the register(s) whose rows govern it — the lookup",
        "the `check` command's §3 runs before judging any issue.",
        "",
        "It is a **label, not a partition**: a register may govern several components, and a",
        "component may be governed by several registers.",
        "",
        f"**{len(comp_claimed)}** of **{len(comp_index)}** registered components are claimed by a register.",
        "",
    ]
    if comp_claimed:
        lines += ["| Component | Layer | Register(s) |", "|---|---|---|"]
        for cid, regs in comp_index.items():
            if regs:
                lines.append(f"| {cid} | {comp_layers.get(cid, '—')} | {', '.join(sorted(regs))} |")
    else:
        lines.append("_No register declares `components:` yet._")
    lines.append("")

    lines += [
        "### Claimed by no register",
        "",
        "The honest coverage number, and the one that should shrink. A component here is not a",
        "defect — the registers are backfilled domain by domain — but work landing on it is",
        "judged against no written commitment, which is a fact worth being able to count.",
        "",
    ]
    if comp_unclaimed:
        lines += [f"- {cid} ({comp_layers.get(cid, '—')})" for cid in comp_unclaimed]
    else:
        lines.append("_Every registered component is claimed by at least one register._")
    lines.append("")

    lines += [
        "## Coverage",
        "",
        "Backlog is the column that matters: an `adopted` row is a commitment we made, so an",
        "unclaimed one is work we decided on and have not scheduled. **In line** is the part of",
        "that backlog that is real work in the release line being built: it subtracts rows whose",
        "`Kind` can never be claimed (`accepted`, `excluded`) and rows whose `Cut` names a later",
        "line. Backlog keeps both on purpose — it is the total many documents already cite — while",
        "In line is the number that moves the day a scope decision defers a batch.",
        "",
        f"| Register | Section | Rows | Adopted | Claimed | Backlog | In line (`{CONFIG.current_line}`) |",
        "|---|---|---|---|---|---|---|",
    ]
    seen_sections: list[tuple[str, str]] = []
    for r in rows:
        if (r.register, r.section) not in seen_sections:
            seen_sections.append((r.register, r.section))
    for reg, sec in seen_sections:
        grp = [r for r in rows if r.register == reg and r.section == sec]
        adopted = [r for r in grp if r.disposition == "adopted"]
        lines.append(
            f"| {reg} | {sec or '—'} | {len(grp)} | {len(adopted)} | "
            f"{sum(1 for r in grp if by_row.get(r.id))} | "
            f"{sum(1 for r in adopted if status[r.id] == 'unclaimed')} | "
            f"{sum(1 for r in adopted if status[r.id] == 'unclaimed' and r.id in backlog_current_ids)} |"
        )
    lines.append("")

    lines += ["## Claimed rows", "", "The derived status of every row a PRD has claimed.", ""]
    if claimed:
        lines += ["| ID | Kind | Disposition | Derived status | Claimed by |", "|---|---|---|---|---|"]
        for r in claimed:
            cs = sorted(by_row.get(r.id, []), key=lambda c: c.prd)
            who = ", ".join(f"{c.prd} ({c.status})" for c in cs) if cs else "—"
            lines.append(f"| {r.id} | {r.kind} | {r.disposition} | **{status[r.id]}** | {who} |")
    else:
        lines.append("_No PRD claims a requirement yet._")
    lines.append("")

    lines += [
        "## Violations — a live disproof says the commitment does not hold",
        "",
        "A PRD's `status: shipped` records how far the *work* got, never whether the *commitment*",
        "holds. A row here is claimed (often by a shipped PRD) **and** named in a register's",
        "`## Known violations` table pointing at the issue that disproves it. That is the route",
        "back the lifecycle otherwise lacks: the PRD cannot walk off `shipped`, but the row's",
        "derived status can read `violated` until the disproof is discharged (the table row is",
        "removed when the issue closes). Countable, not invisible — ENG-7534.",
        "",
    ]
    if violated:
        lines += ["| ID | Kind | Claimed by | Disproven by | Reason |", "|---|---|---|---|---|"]
        for r in violated:
            cs = sorted(by_row.get(r.id, []), key=lambda c: c.prd)
            who = ", ".join(f"{c.prd} ({c.status})" for c in cs) if cs else "—"
            ds = by_disproof[r.id]
            issues = ", ".join(sorted({i for d in ds for i in d.issues})) or "—"
            reason = next((d.reason for d in ds if d.reason), "") or "—"
            lines.append(f"| {r.id} | {r.kind} | {who} | {issues} | {reason} |")
    else:
        lines.append("_None._")
    lines.append("")
    if dangling_disproofs:
        lines += [
            "**Disproofs naming an id that does not resolve** — a Known-violations row whose",
            "requirement id is not in any register:",
            "",
        ]
        lines += [f"- {rid}" for rid in dangling_disproofs]
        lines.append("")

    lines += [
        "## Backlog — adopted, and no PRD claims it",
        "",
        "Not a to-do list: a row here is deferred, forgotten or quietly withdrawn, and those",
        "three look identical until the gap is visible. Grouped by the section that made the",
        "commitment, so the unclaimed part of the architecture reads as a shape rather than a",
        "list of numbers.",
        "",
    ]
    if backlog:
        for reg, sec in seen_sections:
            grp = [r for r in backlog if r.register == reg and r.section == sec]
            if not grp:
                continue
            lines += [f"### {sec or reg}", ""]
            lines += [f"- {r.id} ({r.kind})" for r in grp]
            lines.append("")
    else:
        lines += ["_Every adopted requirement is claimed by a PRD._", ""]

    lines += [
        "## Unsettled — `open` rows",
        "",
        "Not backlog: nothing was decided, so there is nothing to schedule. A row here needs a",
        "mechanism or a number before a PRD can claim it.",
        "",
    ]
    if unsettled:
        lines += [f"- {r.id} ({r.kind}) — {r.section}" for r in unsettled]
    else:
        lines.append("_Nothing open._")
    lines.append("")

    lines += [
        "## Re-read due — a decision whose premise has moved",
        "",
        "The `Because` premise edge (A2): a row records the premise its decision rested on.",
        "When that premise row is now `rejected` or `superseded`, the decision's reason may have",
        "expired — a rejection or accepted cost is only valuable while its rationale still holds,",
        "and nothing but a human being pointed back at it can check that. A row here is *not* a",
        "defect and nothing fails: it is the register's own most valuable row asking for a second",
        "look. Re-read it, and discharge with one token, `reaffirmed=YYYY-MM-DD`, on the row. The",
        "trigger is an event (the premise moving), never a calendar — a sweep is calibrated to the",
        "tail and misses the moment the harm is greatest.",
        "",
    ]
    reread = [
        r
        for r in rows
        if r.because in index and index[r.because].disposition in TERMINAL_DISPOSITIONS and not r.reaffirmed
    ]
    if reread:
        lines += ["| ID | Kind | Disposition | Premise | Section |", "|---|---|---|---|---|"]
        for r in sorted(reread, key=lambda r: r.id):
            lines.append(
                f"| {r.id} | {r.kind} | {r.disposition} | {r.because} ({index[r.because].disposition}) | {r.section} |"
            )
    else:
        lines.append("_No row rests on a premise that has moved._")
    lines.append("")

    lines += [
        "## Orphans",
        "",
        "A row whose every claiming PRD was cancelled: it looked scheduled, the schedule",
        "evaporated, and the register cannot say so because it stores no status.",
        "",
    ]
    if orphans:
        for r in orphans:
            was = ", ".join(sorted(c.prd for c in by_row[r.id]))
            lines.append(f"- {r.id} — was claimed by {was} (all cancelled)")
    else:
        lines.append("_None._")
    lines.append("")
    if dangling:
        lines += [
            "",
            "**Claims naming an id that does not resolve** — `validate_requirements.py` fails the",
            "commit on these, so seeing one here means the validator was bypassed:",
            "",
        ]
        lines += [f"- {rid}" for rid in dangling]
        lines.append("")

    lines += [
        "## Drift",
        "",
        "A live PRD claiming a row the register calls `rejected`, `superseded` or `open`: either",
        "the work builds something we refused, or the register is stale. Both need a human.",
        "",
    ]
    if drift:
        lines += ["| ID | Disposition | Claimed by | PRD status |", "|---|---|---|---|"]
        for r, c in sorted(drift, key=lambda rc: (rc[0].id, rc[1].prd)):
            lines.append(f"| {r.id} | {r.disposition} | {c.prd} | {c.status} |")
    else:
        lines.append("_No live claim points at a withdrawn or unsettled row._")
    lines.append("")

    return "\n".join(ln.rstrip() for ln in lines).rstrip("\n") + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    out = render()
    if "--check" in argv:
        # Nothing is committed to compare against: the gate is that the derivation RUNS over
        # this tree. A register it cannot read raises before this line.
        print(f"knowledge/requirement-status.md renders ({len(out.splitlines())} lines) — not written (--check)")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(out, encoding="utf-8")
    print(f"generated {TARGET.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
