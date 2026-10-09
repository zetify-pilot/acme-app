#!/usr/bin/env python3
"""Query the requirement graph — the questions we have actually had to answer by hand.

    python3 knowledge/scripts/requirement_query.py prd 0486        # what its claims need, and what is unsatisfied
    python3 knowledge/scripts/requirement_query.py startable       # adopted, unclaimed, every need already built
    python3 knowledge/scripts/requirement_query.py row # who claims it, what it needs, what it blocks
    python3 knowledge/scripts/requirement_query.py open 0486       # what is still `open` in the sections it touches
    python3 knowledge/scripts/requirement_query.py neighbours --components access-profiles \
        --statement "a profile may only ever narrow"     # what this would contradict, across ALL registers
    python3 knowledge/scripts/requirement_query.py decided --components access-profiles \
        # rows an ADOPTED DECISION has already invalidated on that ground (reverse coverage)

Every subcommand takes `--json` and prints the same answer as one object, because both
readers matter: a human at a terminal, and an agent that must not have to parse prose.

**Why this exists.** Two failures, one night, on the same table.

The first is a defect the graph asserted and nobody could see: asked *"what must hold
before PRD 0486 can be built?"*, the register answered with four rows describing the
plane-side build — the tier 0486's own biggest Non-Goal deletes. Seven of its sixteen
claims carried `Needs` edges into that tier, so the graph said the critical-path PRD was
unsatisfiable until v2 landed, which was false. It survived because the rows are `adopted`
and *deferred to v2* rather than superseded, so the propagation pass left the edges alone.
Repaired in `3ad63c6d7e`; the advisory that now catches the shape is
`validate_requirements.py` → `check_claim_scope`.

The second is why the first went unseen for as long as it did: **the question could only
be asked by writing a parser.** Four agents in one session wrote their own throwaway
reader for this table and two got the column index wrong — silently producing no rows,
which is indistinguishable from a healthy answer. So this file writes **no parser at
all**: rows come from `gen_requirement_status.load_rows()`, the documented swap point, and
the satisfied/unsatisfied predicate is `validate_requirements.need_scope`, shared with the
validator that enforces it. There is one reader of the register in this repo and one
definition of "satisfied", and this tool is a consumer of both rather than a third copy.

That also makes the tool survive the marker migration
(`knowledge/decisions/2026-08-14-one-register-shape-the-marker-inversion-is-withdrawn.md`):
when the register stops being a hand-written table, `load_rows()` changes and nothing here
does.

Stdlib only. Exit code is 0 for every answer including an empty one — an empty frontier is
a fact, not a failure; callers route on the output.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent

# Reuse, never re-derive. `gen_requirement_status` owns `load_rows()` — the ONE function in
# the repo that knows where a requirement row comes from — and it in turn owns the single
# register parser (`validate_requirements.load_registers`). Importing the generator gets
# both, plus `vr` for the shared scope predicate.
_spec = importlib.util.spec_from_file_location("_rq_grs_reuse", HERE / "gen_requirement_status.py")
assert _spec and _spec.loader
grs: Any = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("_rq_grs_reuse", grs)
sys.modules.setdefault("grs", grs)  # @dataclass resolves its module during the class body
_spec.loader.exec_module(grs)
vr: Any = grs.vr

# How a scope reads to a human, in the order need_scope ranks them.
SCOPE_GLOSS = {
    "same-prd": "built by the same PRD",
    "built": "already shipped",
    "violated": "shipped claim disproven (Known violations)",
    "scheduled": "claimed by a live PRD",
    "orphaned": "every claiming PRD was cancelled",
    "unclaimed": "no PRD claims it",
}


def cut_tag(row: Any) -> str:
    """` · CUT v2` when a row is out of the line being built, else nothing.

    Rendered next to the disposition rather than in a column of its own, because the two
    read as one fact — *what we decided, and which version it lands in* — and a reader
    scanning for "can I start this" must not have to correlate two places.
    """
    cut = getattr(row, "cut", "") or ""
    return f" · CUT {cut}" if cut and cut != vr.CURRENT_LINE else ""


class Graph:
    """The register plus the `implements:` edge, indexed the four ways the queries need."""

    def __init__(self) -> None:
        self.rows: dict[str, Any] = {r.id: r for r in grs.load_rows()}
        self.claims: dict[str, list[tuple[str, str]]] = vr.load_prd_claims()
        # Live disproofs: a shipped claim that a Known-violations entry
        # names is not "built". Loaded once so every need_scope call sees the same set.
        self.disproven: frozenset[str] = frozenset(d.requirement for d in grs.load_disproofs())
        self.blocks: dict[str, list[str]] = {}  # reverse `Needs`: {id: [rows that need it]}
        for rid, r in self.rows.items():
            for dep in r.needs:
                self.blocks.setdefault(dep, []).append(rid)

    def live_claims(self, rid: str) -> list[tuple[str, str]]:
        return [(p, s) for p, s in self.claims.get(rid, []) if s not in vr.CLAIM_HISTORY]

    def scope(self, dep: str, claimant: str | None) -> str:
        return str(vr.need_scope(dep, claimant, self.claims, disproven=self.disproven))

    def cut(self, rid: str) -> str:
        """The row's `Cut` value, or "" — empty for an id that does not resolve."""
        r = self.rows.get(rid)
        return (getattr(r, "cut", "") or "") if r is not None else ""

    def is_cut(self, rid: str) -> bool:
        """Is `rid` out of the release line being built? The validator's own predicate."""
        return bool(vr.is_cut({"cut": self.cut(rid)}))

    def needs_of(self, rid: str, claimant: str | None) -> list[dict[str, Any]]:
        """Each `Needs` target of `rid`, classified against `claimant`'s scope.

        `cut` is carried alongside `scope` rather than folded into it, because they answer
        different questions and a caller needs both: *is anybody building this* and *is it
        even in this version*. A cut need is never satisfied — no amount of scheduling in a
        later line makes it available now — so `satisfied` accounts for it directly.
        """
        out: list[dict[str, Any]] = []
        for dep in self.rows[rid].needs:
            scope = self.scope(dep, claimant)
            cut = self.cut(dep)
            out.append(
                {
                    "id": dep,
                    "scope": scope,
                    "cut": cut,
                    "satisfied": scope in vr.SATISFIED_SCOPES and not self.is_cut(dep),
                    "disposition": self.rows[dep].disposition if dep in self.rows else "?unresolved",
                    "claimed_by": [f"{p} ({s})" for p, s in self.claims.get(dep, [])],
                }
            )
        return out

    def prds(self) -> dict[str, str]:
        """`{prd number: status}` for every PRD that claims anything."""
        return {p: s for cs in self.claims.values() for p, s in cs}


def resolve_prd(g: Graph, token: str) -> str:
    """Accept `0486`, `486` or a PRD directory name; return the canonical number."""
    known = g.prds()
    for cand in (token, token.zfill(4), token.split("-")[0].zfill(4)):
        if cand in known:
            return cand
    raise SystemExit(
        f"no PRD `{token}` declares `implements:` — known claimants: {', '.join(sorted(known)) or '(none)'}"
    )


def emit(payload: dict[str, Any], lines: list[str], as_json: bool) -> int:
    print(json.dumps(payload, indent=2) if as_json else "\n".join(lines))
    return 0


def short(text: str, width: int = 96) -> str:
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1] + "…"


# --- the five questions -------------------------------------------------------


def q_prd(g: Graph, token: str, as_json: bool) -> int:
    """What a PRD's claims need, and which of those needs nothing is building.

    The unsatisfied list is the answer to *"what must hold before this can be built"* — and
    the one that was wrong on 0486. It now separates the two cases the register could not
    tell apart before `Cut` existed: a need marked `CUT` is out of this release line and is
    a **defect** (`validate_requirements.py` fails the commit on it), while a need that is
    merely unclaimed is a **question** — real work in this line that nobody has scheduled.
    """
    prd = resolve_prd(g, token)
    status = g.prds()[prd]
    claimed = sorted(rid for rid, cs in g.claims.items() if any(p == prd for p, _ in cs))
    items: list[dict[str, Any]] = []
    unsat: list[dict[str, Any]] = []
    for rid in claimed:
        if rid not in g.rows:
            items.append({"id": rid, "resolves": False, "needs": []})
            continue
        r = g.rows[rid]
        needs = g.needs_of(rid, prd)
        items.append(
            {
                "id": rid,
                "resolves": True,
                "kind": r.kind,
                "disposition": r.disposition,
                "cut": r.cut,
                "section": r.section,
                "statement": r.statement,
                "needs": needs,
            }
        )
        unsat += [dict(n, needed_by=rid) for n in needs if not n["satisfied"]]

    lines = [f"PRD {prd} [{status}] — {len(claimed)} claim(s)", ""]
    for it in items:
        if not it["resolves"]:
            lines.append(f"  {it['id']}  !! does not resolve to a requirement row")
            continue
        tag = cut_tag(g.rows[it["id"]])
        lines.append(f"  {it['id']} [{it['kind']} | {it['disposition']}{tag}] {short(it['statement'], 70)}")
        for n in it["needs"]:
            if g.is_cut(n["id"]):
                mark, why = "CUT ", f"cut from {vr.CURRENT_LINE}, lands in {n['cut']}"
            else:
                mark, why = ("ok  " if n["satisfied"] else "GAP "), SCOPE_GLOSS.get(n["scope"], "")
            lines.append(f"      needs {n['id']}  {mark}{n['scope']} — {why}")
        if not it["needs"]:
            lines.append("      needs nothing")
    lines += ["", f"UNSATISFIED NEEDS — {len(unsat)}"]
    if unsat:
        for n in sorted(unsat, key=lambda x: (x["id"], x["needed_by"])):
            mark = f" CUT {n['cut']}" if g.is_cut(n["id"]) else ""
            lines.append(f"  {n['id']} [{n['disposition']}{mark}] ({n['scope']}) — needed by {n['needed_by']}")
            if n["id"] in g.rows:
                lines.append(f"      {short(g.rows[n['id']].statement, 88)}")
        lines += [
            "",
            "  A need marked CUT is a DEFECT: the claim rests on a mechanism this release line does",
            "  not have, and validate_requirements.py fails the commit on it — re-point the edge at",
            "  what this line provides, or drop it. A need that is merely unclaimed is a QUESTION:",
            "  it is in this line, and nobody has scheduled it.",
        ]
    else:
        lines.append("  none — every need is built by this PRD, already shipped, or claimed by live work.")
    return emit({"prd": prd, "status": status, "claims": items, "unsatisfied": unsat}, lines, as_json)


def q_startable(g: Graph, as_json: bool, register: str | None, section: str | None, blocking: bool) -> int:
    """Adopted, IN THIS RELEASE LINE, unclaimed, and every `Needs` target already built.

    "Built" means *a shipped PRD claims it* and nothing else — the register stores no status
    by construction, so a claim by shipped work is the only evidence of existence the corpus
    carries. That makes this list conservative in the safe direction: it never calls
    something startable on the strength of a prerequisite that merely got written down.

    **A row cut from this line is not startable, and that filter is why `Cut` is worth a
    column.** Before it, the frontier could not tell a commitment deliberately pushed to v2
    from one nobody had got to, so it offered work that cannot be started — the same
    ambiguity that forced the validator's claim-scope check to be advisory in both halves.
    It applies to a row's needs too: a prerequisite in a later line is unavailable now,
    however well scheduled it looks there.

    Sorted by how much each row unblocks, because the frontier's useful ordering is not
    alphabetical — a startable row that nothing needs is a leaf, and a startable row six
    others need is the one to schedule first.
    """
    out = []
    for rid, r in g.rows.items():
        if r.disposition != "adopted" or g.live_claims(rid) or g.is_cut(rid):
            continue
        if register and r.register != register:
            continue
        if section and section.lower() not in r.section.lower():
            continue
        needs = g.needs_of(rid, None)
        if any(n["scope"] != "built" or g.is_cut(n["id"]) for n in needs):
            continue
        unblocks = sorted(g.blocks.get(rid, []))
        if blocking and not unblocks:
            continue
        out.append(
            {
                "id": rid,
                "kind": r.kind,
                "cut": r.cut,
                "register": r.register,
                "section": r.section,
                "statement": r.statement,
                "needs": [n["id"] for n in needs],
                "unblocks": unblocks,
            }
        )
    out.sort(key=lambda x: (-len(x["unblocks"]), x["id"]))

    lines = [
        f"STARTABLE — {len(out)} adopted `{vr.CURRENT_LINE}` row(s) no live PRD claims, "
        "whose every need is already built",
        "",
    ]
    by_section: dict[str, list[dict[str, Any]]] = {}
    for it in out:
        by_section.setdefault(f"{it['register']} / {it['section'] or '—'}", []).append(it)
    for sec, grp in sorted(by_section.items(), key=lambda kv: (-max(len(i["unblocks"]) for i in kv[1]), kv[0])):
        lines.append(f"  {sec}")
        for it in grp:
            tail = f"  (unblocks {len(it['unblocks'])})" if it["unblocks"] else ""
            lines.append(f"    {it['id']} [{it['kind']}] {short(it['statement'], 64)}{tail}")
        lines.append("")
    if not out:
        lines.append("  none.")
    lines.append("  Startable is not prioritised: it says nothing is in the way, never that it is worth doing.")
    lines.append(f"  Rows cut from `{vr.CURRENT_LINE}` are excluded — they are decided, not startable.")
    return emit({"startable": out, "count": len(out), "line": vr.CURRENT_LINE}, lines, as_json)


def q_row(g: Graph, rid: str, as_json: bool) -> int:
    """One row: who claims it, what it needs, and what it blocks (the reverse edges).

    The reverse direction is the half the table cannot show. `Needs` is written on the
    needing row, so "what breaks if this slips" is invisible without walking all 699 — which
    is the walk that got hand-written four times in one session.
    """
    rid = rid.upper()
    if rid not in g.rows:
        raise SystemExit(f"`{rid}` does not resolve to a requirement row (ids are permanent — typo, or deleted?)")
    r = g.rows[rid]
    needs = g.needs_of(rid, None)
    blocks = []
    for other in sorted(g.blocks.get(rid, [])):
        o = g.rows[other]
        blocks.append(
            {
                "id": other,
                "disposition": o.disposition,
                "claimed_by": [f"{p} ({s})" for p, s in g.claims.get(other, [])],
                "statement": o.statement,
            }
        )
    claimed_by = [f"{p} ({s})" for p, s in g.claims.get(rid, [])]
    payload = {
        "id": rid,
        "kind": r.kind,
        "disposition": r.disposition,
        "cut": r.cut,
        "register": r.register,
        "section": r.section,
        "statement": r.statement,
        "claimed_by": claimed_by,
        "needs": needs,
        "blocks": blocks,
    }
    unscheduled = (
        f"  nobody — and this row is cut from `{vr.CURRENT_LINE}`, so that is the plan, not a gap"
        if g.is_cut(rid)
        else "  nobody — this row is unscheduled"
    )
    lines = [
        f"{rid} [{r.kind} | {r.disposition}{cut_tag(r)}] — {r.register} / {r.section or '—'}",
        f"  {short(r.statement, 110)}",
        "",
        f"CLAIMED BY — {len(claimed_by)}",
        *(f"  {c}" for c in claimed_by),
        *([] if claimed_by else [unscheduled]),
        "",
        f"NEEDS — {len(needs)}",
    ]
    for n in needs:
        mark = "CUT " if g.is_cut(n["id"]) else ("ok  " if n["satisfied"] else "GAP ")
        lines.append(f"  {n['id']} [{n['disposition']}] {mark}{n['scope']}")
    if not needs:
        lines.append("  nothing — no prerequisite in the build order")
    lines += ["", f"BLOCKS — {len(blocks)} row(s) name this one in their Needs"]
    for b in blocks:
        who = ", ".join(b["claimed_by"]) or "unclaimed"
        lines.append(f"  {b['id']} [{b['disposition']}] ({who}) {short(b['statement'], 56)}")
    if not blocks:
        lines.append("  nothing — no row's build order depends on this")
    return emit(payload, lines, as_json)


def q_open(g: Graph, token: str, as_json: bool) -> int:
    """What is still `open` in the sections a PRD's claims sit in.

    `open` means *nothing was decided* — no mechanism, or no number — so an open row in a
    section a PRD is building is a fork that PRD is about to hit, whether or not it claims
    the row. This is the neighbourhood read the design phase needs and the claim list alone
    cannot give: a PRD claims what it realises, never the undecided rows next to it.
    """
    prd = resolve_prd(g, token)
    claimed = {rid for rid, cs in g.claims.items() if any(p == prd for p, _ in cs)}
    sections = sorted({(g.rows[r].register, g.rows[r].section) for r in claimed if r in g.rows})
    items = []
    for rid, r in g.rows.items():
        if r.disposition != "open" or (r.register, r.section) not in sections:
            continue
        items.append(
            {
                "id": rid,
                "kind": r.kind,
                "register": r.register,
                "section": r.section,
                "statement": r.statement,
                "claimed_by_this_prd": rid in claimed,
                "blocks": sorted(g.blocks.get(rid, [])),
            }
        )
    items.sort(key=lambda x: x["id"])
    lines = [
        f"OPEN ROWS in the {len(sections)} section(s) PRD {prd} touches — {len(items)}",
        "",
    ]
    for it in items:
        tag = " [claimed by this PRD]" if it["claimed_by_this_prd"] else ""
        lines.append(f"  {it['id']} [{it['kind']}] {it['register']} / {it['section'] or '—'}{tag}")
        lines.append(f"      {short(it['statement'], 96)}")
        if it["blocks"]:
            lines.append(f"      blocks {', '.join(it['blocks'])}")
    if not items:
        lines.append("  none — every row in those sections is settled.")
    else:
        lines += ["", "  `open` is not backlog: nothing was decided, so there is nothing to schedule yet."]
    return emit({"prd": prd, "sections": [f"{a} / {b}" for a, b in sections], "open": items}, lines, as_json)


# --- neighbours: the conflict sweep -------------------------------------------
#
# The one question the register could not answer. `validate_requirements.py` carries
# thirteen checks and every one is STRUCTURAL — the id counter, component resolution,
# kind/disposition legality, supersession closure, Needs/Because edges, claim scope,
# append order, source anchors, restatements, prose citations, PRD claims. None of them
# compares two statements, so "does this contradict something we already promised" had
# exactly one implementation: a human reading the one register their cut happened to land
# on. A contradiction rarely lives there.
#
# This is deliberately a FORCED READ, not a validator. Semantic conflict is a judgement
# call — knowledge-model.md says so outright about paraphrase ("a judgement call no
# validator can make and stays invisible") — so the honest ceiling is to put the rows a
# human should look at in front of them, ranked, and let them decide. It never fails a
# build and never exits non-zero.

# Terms that carry no discriminating signal in a corpus of "the system shall" sentences.
_STOP = frozenset(
    [
        "about",
        "above",
        "after",
        "again",
        "against",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "cannot",
        "could",
        "does",
        "doing",
        "done",
        "down",
        "during",
        "each",
        "either",
        "else",
        "even",
        "ever",
        "every",
        "from",
        "further",
        "have",
        "having",
        "here",
        "hers",
        "into",
        "itself",
        "just",
        "less",
        "like",
        "made",
        "make",
        "many",
        "more",
        "most",
        "much",
        "must",
        "never",
        "next",
        "none",
        "nor",
        "not",
        "once",
        "only",
        "onto",
        "other",
        "over",
        "own",
        "rather",
        "same",
        "shall",
        "should",
        "since",
        "some",
        "such",
        "than",
        "that",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "under",
        "until",
        "upon",
        "very",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "will",
        "with",
        "within",
        "without",
        "would",
        "your",
    ]
)


def terms(text: str) -> set[str]:
    """Distinctive tokens of a statement — lowercase, >=4 chars, not a stopword.

    Deliberately crude and dependency-free: the ranking below is a reading order for a
    human, not a similarity claim, so precision here buys nothing a person would notice.
    """
    out, cur = set(), []
    for ch in text.lower():
        if ch.isalnum() or ch in "_-":
            cur.append(ch)
        elif cur:
            out.add("".join(cur))
            cur = []
    if cur:
        out.add("".join(cur))
    return {t.strip("-_") for t in out if len(t.strip("-_")) >= 4 and t not in _STOP}


def q_neighbours(g: Graph, statements: list[str], components: list[str], limit: int, as_json: bool) -> int:
    """Rows a draft commitment should be read against, before it is appended.

    Three buckets, because they are read for different reasons:
      * `excluded` — what we decided NOT to build. Shown FIRST and in full for the ground
        this cut touches, term overlap or not: a cut that does what an excluded row refuses
        is the one conflict nothing else in the pipeline can catch, and it does not
        announce itself with shared vocabulary.
      * same ground — rows in the register(s) that govern these components.
      * elsewhere — rows in every other register sharing distinctive terms. This is the
        bucket the one-register read structurally cannot produce.
    """
    draft = set()
    for st in statements:
        draft |= terms(st)

    reg_comps = vr.register_components()
    covering = set(vr.registers_covering(components, reg_comps)) if components else set()

    # Inverse document frequency, so "workspace" ranks below "monotonic".
    df: dict[str, int] = {}
    row_terms: dict[str, set[str]] = {}
    for rid, r in g.rows.items():
        t = terms(r.statement)
        row_terms[rid] = t
        for term in t:
            df[term] = df.get(term, 0) + 1
    n = max(len(g.rows), 1)

    def score(rid: str) -> float:
        shared = draft & row_terms[rid]
        # A term in half the corpus says nothing; one in three rows says a lot.
        return round(sum(1.0 / df[t] for t in shared) * n / 10, 2) if shared else 0.0

    def entry(rid: str) -> dict[str, Any]:
        r = g.rows[rid]
        return {
            "id": rid,
            "register": r.register,
            "kind": r.kind,
            "disposition": r.disposition,
            "score": score(rid),
            "shared": sorted(draft & row_terms[rid]),
            "statement": r.statement,
        }

    excluded, same, elsewhere = [], [], []
    for rid, r in g.rows.items():
        on_ground = r.register in covering
        sc = score(rid)
        if r.kind == "excluded" and (on_ground or sc > 0):
            excluded.append(entry(rid))
        elif on_ground and sc > 0:
            same.append(entry(rid))
        elif sc > 0:
            elsewhere.append(entry(rid))
    for bucket in (excluded, same, elsewhere):
        bucket.sort(key=lambda e: (-e["score"], e["id"]))
    same, elsewhere = same[:limit], elsewhere[:limit]

    payload = {
        "query": {"statements": statements, "components": components, "registers": sorted(covering)},
        "excluded": excluded,
        "same_ground": same,
        "elsewhere": elsewhere,
        "note": "a reading order, not a verdict — semantic conflict is a judgement call",
    }
    lines: list[str] = []
    if components and not covering:
        lines.append(f"no register governs {', '.join(components)} — this ground is unclaimed, so nothing here is a")
        lines.append("conflict check. Opening a register is slice:create Step 3.2.\n")

    def block(title: str, items: list[dict[str, Any]], empty: str) -> None:
        lines.append(title)
        if not items:
            lines.append(f"  {empty}")
        for e in items:
            tag = f"{e['kind']}/{e['disposition']}"
            lines.append(f"  {e['id']:<10} {tag:<26} score {e['score']:>6}")
            lines.append(f"             {short(e['statement'], 92)}")
            if e["shared"]:
                lines.append(f"             shared: {', '.join(e['shared'][:8])}")
        lines.append("")

    block(
        "WE DECIDED NOT TO BUILD THIS — read before anything else",
        excluded,
        "(none on this ground — but an absent exclusion is not a cleared one)",
    )
    block("SAME GROUND — the register(s) governing these components", same, "(no term overlap)")
    block("ELSEWHERE — other registers sharing distinctive terms", elsewhere, "(no term overlap)")
    lines.append("Say which of these you are consistent with, which you supersede, and which you")
    lines.append("contradict. This tool ranks; it does not decide.")
    return emit(payload, lines, as_json)


# --- decided: the reverse-coverage sweep (adopted decisions that invalidated) --
#
# The reverse of the `drift` check. `validate_requirements.py`'s drift reads a PRD's
# `implements:` edge back against the register and fails when a live PRD CLAIMS a
# superseded/rejected/excluded row — but a PRD that reaches into a surface a decision
# retired WITHOUT claiming the row (the / PRD 0543 shape: a nav PRD promoting
# grant-conversions that had just made dead) claims nothing that would trip it.
# `drift` is a claim check; this is a ground check. Given the components a design is about
# to touch, it surfaces every row an adopted decision has already invalidated on that
# ground — the superseded/rejected/excluded rows — so a designer sees the adopted
# decision before (re)building the thing it retired. Same contract as `neighbours`: a
# forced read, never a verdict, never fails a build.
def q_decided(g: Graph, components: list[str], as_json: bool) -> int:
    reg_comps = vr.register_components()
    covering = set(vr.registers_covering(components, reg_comps)) if components else set()
    decided_rows: list[dict[str, str]] = []
    rank = {"superseded": 0, "rejected": 1, "excluded": 2}
    for rid, r in g.rows.items():
        if r.register not in covering:
            continue
        disp = "excluded" if r.kind == "excluded" else r.disposition
        if disp not in rank:
            continue
        decided_rows.append(
            {
                "id": rid,
                "register": r.register,
                "kind": r.kind,
                "disposition": r.disposition,
                "statement": r.statement,
            }
        )
    decided_rows.sort(key=lambda e: (rank.get(e["disposition"], 9), e["id"]))

    payload = {
        "query": {"components": components, "registers": sorted(covering)},
        "decided": decided_rows,
        "note": (
            "rows an adopted decision has invalidated on this ground — read before "
            "building; this is a forced read, not a verdict"
        ),
    }
    lines: list[str] = []
    if components and not covering:
        lines.append(f"no register governs {', '.join(components)} — this ground is unclaimed, so no")
        lines.append("adopted decision invalidates a requirement here by construction. Opening a register")
        lines.append("is slice:create Step 3.2.\n")
    lines.append("ADOPTED DECISIONS THAT HAVE INVALIDATED A REQUIREMENT ON THIS GROUND")
    if not decided_rows:
        lines.append("  (none — but an absent retirement is not a cleared one: read the live rows too)")
    for e in decided_rows:
        tag = f"{e['kind']}/{e['disposition']}"
        lines.append(f"  {e['id']:<10} {tag:<26} ({e['register']})")
        lines.append(f"             {short(e['statement'], 92)}")
    lines.append("")
    lines.append("Read these before building on this ground: a decision already retired or refused a")
    lines.append("requirement here, and a PRD that (re)builds it ships something dead on arrival.")
    return emit(payload, lines, as_json)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="requirement_query.py",
        description="Query the requirement graph: claims, needs, reverse edges, the startable frontier.",
    )
    p.add_argument("--json", action="store_true", help="emit the answer as one JSON object")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("prd", help="what a PRD's claims need, and which needs nothing is building")
    sp.add_argument("prd")

    ss = sub.add_parser("startable", help="adopted, unclaimed, every need already built")
    ss.add_argument("--register", help="restrict to one register domain (e.g. workload-runtime)")
    ss.add_argument("--section", help="substring match on the section heading")
    ss.add_argument("--blocking", action="store_true", help="only rows that unblock at least one other")

    sr = sub.add_parser("row", help="one row: claims, needs, and what it blocks")
    sr.add_argument("id")

    so = sub.add_parser("open", help="what is still `open` in the sections a PRD touches")
    so.add_argument("prd")

    sn = sub.add_parser("neighbours", help="what a draft commitment would contradict, across ALL registers")
    sn.add_argument(
        "--statement",
        action="append",
        default=[],
        metavar="TEXT",
        help="a draft statement; repeat for each row the cut would append",
    )
    sn.add_argument(
        "--components",
        default="",
        metavar="a,b",
        help="the cut's components — resolves to the register(s) governing this ground",
    )
    sn.add_argument("--limit", type=int, default=8, help="rows per ranked bucket (default 8)")

    sd = sub.add_parser(
        "decided",
        help="rows an adopted decision has invalidated on a PRD's ground (reverse coverage)",
    )
    sd.add_argument(
        "--components",
        default="",
        metavar="a,b",
        help="the ground the design is about to touch — resolves to the register(s) governing it",
    )

    a = p.parse_args(argv)
    g = Graph()
    if a.cmd == "prd":
        return q_prd(g, a.prd, a.json)
    if a.cmd == "startable":
        return q_startable(g, a.json, a.register, a.section, a.blocking)
    if a.cmd == "row":
        return q_row(g, a.id, a.json)
    if a.cmd == "neighbours":
        comps = [c.strip() for c in a.components.split(",") if c.strip()]
        if not a.statement and not comps:
            raise SystemExit("neighbours needs at least one --statement or --components")
        return q_neighbours(g, a.statement, comps, a.limit, a.json)
    if a.cmd == "decided":
        comps = [c.strip() for c in a.components.split(",") if c.strip()]
        if not comps:
            raise SystemExit("decided needs at least one --component")
        return q_decided(g, comps, a.json)
    return q_open(g, a.prd, a.json)


if __name__ == "__main__":
    raise SystemExit(main())
