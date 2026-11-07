"""The derivation layer: completion, dependency waves, chokepoints, gaps.

Nothing here is stored anywhere, and nothing here is authored. A program and a slice carry
no `status:` — their completion is COMPUTED from their member PRDs and their proof, which is
the whole point: a stored mid-tier status is wrong the day after it is written, and the
overwhelming majority of them were.

**Three things this module must never do**, and does not:

  * **Report a count as completeness.** "7 of 7 built" is exactly the reading that calls a
    goal done while its composed path returns 503. Everything built with no green proof is
    `awaiting-proof`, never complete.
  * **Complete a program on its slices alone.** A program's own `Verified by` — the composed
    thread ACROSS those slices — must have shipped. That is the completion condition this
    tier adds to its children's, and without it a program is a label.
  * **Count an unmet dependency that is already done.** Depth and blocking are computed over
    LIVE PRDs only; a shipped dependency is not a wait.

**And one it must never do at all: imply a rate.** There is no date arithmetic here, no
duration, no velocity, no projection and no "what fits" calculation — not because none could
be written, but because a number of that shape is read as a commitment nobody made. Progress
is counts ("3 of 7 slices done"); ordering is the dependency graph or a human's authored
rank. Nothing else.

Stdlib only.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from . import bars
from .corpusref import is_qualified
from .markdown import first_paragraph, strip_frontmatter
from .registers import ADOPTED, DRILL_PASSED, closed_into_areas, drill_stem, is_drill

# A PRD is the only entity whose `status:` is authored; these two values are terminal, and
# everything above the PRD is computed from them.
PRD_TERMINAL = frozenset({"shipped", "cancelled"})

#: `stem -> frontmatter` for the corpus's drill records, the shape `registers.drills` returns.
#: The second kind of proof: a `drill:<stem>` entry in `Verified by` resolves against this
#: rather than against the PRD index. Optional everywhere it is taken — a corpus with no
#: drills directory has none, and a payload from before drills were read looks the same.
Drills = Mapping[str, Mapping[str, Any]]

#: `tier -> the ids in that tier's proof-waiver baseline`, keyed `"slice"` / `"program"`. The
#: authored *"no proof planned, and here is why"* record, which is the ONE input that makes
#: `waived` a different state from `unproven`: the first is a decision somebody wrote down, the
#: second is a cell nobody has looked at.
Waivers = Mapping[str, frozenset[str]]

#: `entity id -> what its DEFERRED proof waiver leaves owed`, across both tiers (a slice id and a
#: program id come from different namespaces, so they cannot collide). The second half of a
#: waiver's reading since 2026-10-07: an id in `Waivers` is EXCUSED — no proof is needed, and the
#: entity is settled by that decision — while an id here has its proof still owed, so it reads
#: `awaiting-proof` and holds its program open, saying what it waits on (`waiting_on`). A caller
#: builds both from `registers.slice_waiver_readings` / the programs baseline; omitted, nothing is
#: owed.
Owed = Mapping[str, str]


def waiting_on(eid: str, owed: str) -> str:
    """The one sentence every surface says for a proof a deferred waiver leaves owed:
    `waiting on SL-188's proof: live measurement on a deployed plane`."""
    return f"waiting on {eid}'s proof: {owed}"


def production_check(eid: str, owed: str, command: str) -> str:
    """The one sentence every surface says for an owed proof only a production check can take (2026-10-08,
    "Keep prod checks with people"): what is owed, that Fleet never runs it, who does, with what, and that
    naming the proof follows in that same attended cycle — so `slice:edit` is never offered as a step of its
    own ahead of a measurement nothing in the fleet will make. `command` is the attended
    `program:deliver <PG>` (its "Read the bar" step runs the slice's live checks); blank, the sentence still
    names the cycle. No closing period: callers append their own.

    `A production check is owed for SL-188 (live measurement on a deployed plane). Fleet has no production
    access, so someone with prod access runs it with /<ns>:program:deliver PG-21; once the check passes,
    that same attended cycle names the proof with slice:edit`.
    """
    run = command.strip() or "an attended program:deliver cycle"
    return (
        f"A production check is owed for {eid} ({owed}). Fleet has no production access, so someone with prod "
        f"access runs it with {run}; once the check passes, that same attended cycle names the proof with slice:edit"
    )


# At most this many slices may hold live work. A default, not a law — exceeded is SHOWN,
# never hidden, because a ceiling nobody is told about is not a ceiling.
#
# ⚠️ This MIRRORS `PlanningConfig.active_slice_ceiling` and is NOT WIRED TO IT: the two are
# separate numbers, and this one sat at 10 (the pre-2026-08-19 value) for five weeks after the
# enforced ceiling became 20. It reads 40 as of 2026-09-25 to agree with the validator. Wiring
# them — `delivery(wip_limit=kb.config.planning["active_slice_ceiling"])` at the caller, or an
# alias here — is the better fix and is deliberately not taken in this change, because
# `rollup` is a pure derivation layer and importing the check family's config into it inverts
# the layering. Until it is wired, a raise must move BOTH.
WIP_LIMIT = 40

# Live PRDs listed on "where should the next hands go".
CHOKE_TOP = 8


def proof_shipped(entry: str, by_num: Mapping[str, Mapping[str, Any]], drills: Drills | None = None) -> bool:
    """Whether ONE `Verified by` entry has shipped — a PRD by its status, a drill by its verdict.

    Two kinds of evidence, one question. A PRD is shipped when its own authored `status:` says
    so; a drill record is "shipped" when the harness that produced it wrote `verdict: passed`
    into its frontmatter. Neither reading is made anywhere else: `all_shipped` below, the
    delivery view and the board all come through here, so a page and a script cannot disagree
    about whether a drill counts. A `drill:` entry with no record behind it, or a record whose
    verdict is anything but `passed`, is False — the same answer an unshipped PRD gives.
    """
    if is_drill(entry):
        record = (drills or {}).get(drill_stem(entry)) or {}
        return str(record.get("verdict", "")).strip().lower() == DRILL_PASSED
    return by_num.get(entry, {}).get("status") == "shipped"


def proof_index(
    prd_rows: Iterable[Mapping[str, Any]], proofs: Mapping[str, Mapping[str, Any]] | None = None
) -> dict[str, Mapping[str, Any]]:
    """`{number: PRD}` for this corpus, plus every declared sibling's PRD under its QUALIFIED key.

    A `Verified by` cell may name a proof in another corpus (`sib:0770`), and the arithmetic
    below looks the entry up verbatim. The reader strips only an OWN-corpus qualifier, so a
    sibling's entry arrives as written and is found only when the sibling's own PRDs are in the
    index under exactly that spelling. `proofs` is those rows — `{"sib:0770": {"status": ...}}` —
    read by the caller, which is the layer that holds a disk (or a register).

    A bare key always wins: a qualified entry and a local number are different keys, so a
    collision would mean the caller indexed something as local that is not, and the local row
    is the one this corpus owns.
    """
    index: dict[str, Mapping[str, Any]] = {str(p["n"]): p for p in prd_rows}
    for entry, record in (proofs or {}).items():
        index.setdefault(str(entry), record)
    return index


def all_shipped(nums: list[str], by_num: Mapping[str, Mapping[str, Any]], drills: Drills | None = None) -> bool:
    """A proof counts only when every entry naming it has actually shipped.

    `[]` is False by the first clause, which is what keeps an entity that names no proof
    from ever reading complete. An entry is a PRD number or a `drill:<stem>` record; see
    `proof_shipped` for how each is read. `by_num` is `proof_index`'s reading, so a qualified
    cross-corpus entry resolves when the caller joined that sibling's PRDs.
    """
    return bool(nums) and all(proof_shipped(x, by_num, drills) for x in nums)


def is_withdrawn(row: Mapping[str, Any]) -> bool:
    """Whether a register row's `Disposition` takes it out of the plan.

    `withdrawn` and `superseded` both do: the second is a withdrawal that names where the work
    went. A row with no `disposition` at all — a payload from before the column, a synthetic
    fixture — is `adopted`, which is the reading the column is additive over.
    """
    disp = row.get("disposition") or {}
    return str(disp.get("kind", ADOPTED)) != ADOPTED


def withdrawn_programs(program_rows: list[dict[str, Any]]) -> frozenset[str]:
    """The ids of every program a decision has taken out of the plan.

    A CUT UNDER ONE IS OUT WITH IT. The register authors a program's withdrawal once, on the
    program's row — the validator reads it as covering every PRD under every slice of it, and
    the roll-up reads it the same way: a cut whose program stopped is `withdrawn` whatever its
    own cell says, exactly as its PRDs may not be live. Anything else would leave a withdrawn
    program's cuts counted as open work on a board that has just said the program is not.

    **Except a program `superseded by areas`** (FLT-1283, 2026-10-29): it closed because its repository
    stopped planning by program, after every live cut left it for a feature area. What still names it is
    history — a finished cut stays finished — so it withdraws nothing with it.
    """
    return frozenset(g["id"] for g in program_rows if is_withdrawn(g) and not closed_into_areas(g))


def is_demonstration(prd: Mapping[str, Any], program_proofs: set[str] | frozenset[str]) -> bool:
    """Whether a member PRD is ONLY its program's composed proof — the demonstration, not the ground.

    A PRD in the program's `Verified by` that claims no commitment (`implements:` empty or not carried).
    **A proof PRD that claims commitments is the cut's own capability work** (ENG-17175, the human's
    decision of 2026-10-12): acme's PG-01 named PRD 0001 as its proof, and the fill made 0001 claim
    SL-002's register rows, so it is that cut's ground as well as the program's demonstration. Read as
    demonstration only, the cut's ground was vacuously met while 0001 was unbuilt, and the drive asked
    for a capability stub that nothing could write. The ONE rule the drive (`autodrive.enrol`), the stub
    offer (`api/candidates._stubbing`) and every ground reading share.
    """
    return str(prd["n"]) in program_proofs and not prd.get("impl")


def capability_ground_met(
    members: list[dict[str, Any]],
    program_proofs: set[str] | frozenset[str],
) -> bool:
    """Whether a slice's *capability ground* is settled — what the slice ORDER reads as "done".

    **Completion and ground answer different questions** (ENG-10184). A slice is `complete`
    only when every member is terminal *and* its named proof has shipped. A *dependent* slice's
    ordering does not wait on that demonstration: it reads the capability ground — every member
    PRD except the parent program's composed proof (`Verified by`). The composed proof is the
    run that shows the ground holds; it is not part of the ground — unless it claims commitments of
    its own (`is_demonstration`, ENG-17175), when it is ground like any other member.

    **Ordering and display only — never dispatch admission** (ENG-10638). A PRD is held by its
    own `depends_on` and `blockedBy`, never by the ground of a cut its slice's `Depends on`
    names. So a cut whose only unshipped member is the program's composed proof has a met
    ground and reads as done to its dependents. An empty cut (no members) has no ground to meet.
    A cut whose members are *only* composed proofs is vacuously met — there is no
    capability work left under it.
    """
    return not ground_open_members(members, program_proofs) and bool(members)


def ground_open_members(
    members: list[dict[str, Any]],
    program_proofs: set[str] | frozenset[str],
) -> list[dict[str, Any]]:
    """The capability members that keep a slice's ground open — non-terminal, non-proof.

    Empty means the ground is met *or* there is no membership to judge (see
    `capability_ground_met`: an empty cut has no ground to meet and reads unmet).
    """
    if not members:
        return []
    ground = [p for p in members if not is_demonstration(p, program_proofs)]
    if not ground:
        return []
    return [p for p in ground if p.get("status") not in PRD_TERMINAL]


def depths(prereqs: Mapping[str, list[str]]) -> dict[str, int]:
    """`node -> longest chain of prerequisites beneath it`, over any dependency graph.

    `prereqs` maps each node to the nodes it waits on; an edge to a node outside the mapping is
    ignored (it is met, dangling, or somebody else's). Wave 0 is a node waiting on nothing.

    **A CYCLE IS FOLDED, NOT CUT.** A cycle is a data bug a validator rejects, but a generator
    must neither hang on one nor answer differently depending on which member it happened to
    visit first — the old `seen` guard did the second, so the same corpus could draw a cycle's
    members in different columns on two readings. Here the strongly connected components are
    found first (Tarjan, iterative — a deep chain must not hit the recursion limit) and every
    member of one component shares one depth: the depth of the component over the acyclic
    graph of components. A self-edge is part of its own component and adds nothing.
    """
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    comp: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    order: list[list[str]] = []  # components, each emitted after every component it waits on
    counter = 0
    for start in sorted(prereqs):
        if start in index:
            continue
        work: list[tuple[str, int]] = [(start, 0)]
        while work:
            node, i = work.pop()
            if i == 0:
                index[node] = low[node] = counter
                counter += 1
                stack.append(node)
                on_stack.add(node)
            edges = [d for d in prereqs[node] if d in prereqs]
            if i < len(edges):
                work.append((node, i + 1))
                nxt = edges[i]
                if nxt not in index:
                    work.append((nxt, 0))
                elif nxt in on_stack:
                    low[node] = min(low[node], index[nxt])
                continue
            if low[node] == index[node]:
                members: list[str] = []
                while True:
                    top = stack.pop()
                    on_stack.discard(top)
                    comp[top] = len(order)
                    members.append(top)
                    if top == node:
                        break
                order.append(members)
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
    depth_of: list[int] = []
    for members in order:
        here = len(depth_of)
        beneath = {comp[d] for m in members for d in prereqs[m] if d in prereqs and comp[d] != here}
        depth_of.append(1 + max(depth_of[c] for c in beneath) if beneath else 0)
    return {n: depth_of[comp[n]] for n in prereqs}


def waves(live: dict[str, dict[str, Any]]) -> dict[str, int]:
    """`prd -> longest chain of unmet dependencies beneath it`. Wave 0 is startable today.

    Expects each live PRD to carry `unmet`. A dependency cycle is folded rather than recursed
    into — see `depths`, which this is over the live PRDs.
    """
    return depths({n: list(p["unmet"]) for n, p in live.items()})


def delivery(
    prd_rows: list[dict[str, Any]],
    slice_rows: list[dict[str, Any]],
    program_rows: list[dict[str, Any]],
    *,
    wip_limit: int = WIP_LIMIT,
    choke_top: int = CHOKE_TOP,
    drills: Drills | None = None,
    waivers: Waivers | None = None,
    owed: Owed | None = None,
    proofs: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Every delivery reading, in one place.

    Computed HERE rather than in a page's JavaScript for one reason: one implementation, so a
    number on a page and a number from a script can never disagree.

    `prd_rows` is mutated in place with `unmet`, `wave` and `blocks` — the caller hands over
    rows it owns, and a viewer wants those fields on the PRD too.

    `drills` resolves `drill:<stem>` proof entries (`proof_shipped`). A withdrawn or superseded
    container reads `withdrawn` at either tier and is outside `active`: it is a decision that
    the work stopped, and counting it as open would be arguing with the register.

    `proofs` is `board()`'s argument of the same name: the PRDs of declared sibling corpora,
    keyed by the qualified entry a `Verified by` cell names them with (`sib:0770`). They resolve
    PROOFS only — a sibling's rows are not this corpus's PRDs, so they never enter the liveness,
    wave or dependency arithmetic here.

    `waivers` is `board()`'s argument of the same name. A cut in the slices baseline with every
    member terminal, something shipped and no proof named reads `waived` here as it does there,
    and a program closes over it exactly as `board()` says (`SETTLED_SLICE_STATES`); omitted,
    nothing is waived. `owed` is `board()`'s too: a cut whose waiver is DEFERRED reads
    `awaiting-proof` here as there, and holds its program open (2026-10-07).
    """
    slice_waivers = (waivers or {}).get(SLICE_TIER, frozenset())
    still_owed: Owed = owed or {}
    by_num = {p["n"]: p for p in prd_rows}
    # PROOFS ONLY. `by_num` above is this corpus's liveness arithmetic, and a sibling's rows are
    # not this corpus's PRDs: they must never join `live`, the waves or the dependency edges.
    proofs_by_num = proof_index(prd_rows, proofs)
    live = {n: p for n, p in by_num.items() if p["status"] not in PRD_TERMINAL}
    for p in live.values():
        p["unmet"] = [d for d in p["dep"] if d in live]
        # A dependency on ANOTHER corpus's PRD (`fleet:0899`) is not in `live` — this corpus
        # holds no status for it — and dropping it would make the PRD read as unencumbered. It
        # is kept visible, unresolved, beside the local edges.
        p["external"] = [d for d in p["dep"] if is_qualified(d)]

    depth = waves(live)
    blocks: Counter[str] = Counter()
    for n, p in live.items():
        p["wave"] = depth[n]
        for x in p["unmet"]:
            blocks[x] += 1
    for n, p in live.items():
        p["blocks"] = blocks[n]

    owner = {p["n"]: p["slice"] for p in prd_rows}
    members: dict[str, list[str]] = defaultdict(list)
    for p in prd_rows:
        members[p["slice"]].append(p["n"])

    stopped = withdrawn_programs(program_rows)
    sl: dict[str, Any] = {}
    for s in slice_rows:
        mine = members.get(s["id"], [])
        mine_live = [n for n in mine if n in live]
        inside = set(mine)
        upstream: dict[str, list[str]] = defaultdict(list)
        for n in mine_live:
            for x in live[n]["unmet"]:
                if x not in inside:
                    upstream[owner.get(x, "?")].append(x)
        ready = [n for n in mine_live if not live[n]["unmet"]]
        proven = all_shipped(s["verified_by"], proofs_by_num, drills)
        if is_withdrawn(s) or s["program"] in stopped:
            state = "withdrawn"
        elif not mine:
            state = "empty"
        elif not mine_live:
            # "Everything built, not complete" has two causes that need opposite actions, and
            # collapsing them makes the largest number unactionable: `unproven` is nobody
            # having authored a `Verified by` (a one-line edit), `awaiting-proof` is a named
            # proof that has not shipped (real work). Same arithmetic, different ask.
            shipped_any = any(by_num[n]["status"] == "shipped" for n in mine)
            if proven:
                state = "complete"
            elif s["verified_by"] or s["id"] in still_owed:
                # A DEFERRED waiver owes the proof as surely as a named one does (2026-10-07).
                state = "awaiting-proof"
            elif s["id"] in slice_waivers and shipped_any:
                state = "waived"
            else:
                state = "unproven"
        else:
            state = "moving" if ready else "blocked"
        sl[s["id"]] = {
            "state": state,
            "proven": proven,
            "total": len(mine),
            "shipped": sum(1 for n in mine if by_num[n]["status"] == "shipped"),
            "cancelled": sum(1 for n in mine if by_num[n]["status"] == "cancelled"),
            "live": sorted(mine_live, key=lambda n: (live[n]["wave"], n)),
            "ready": sorted(ready),
            "upstream": {k: sorted(set(v)) for k, v in upstream.items()},
        }
    # The inverse edge — "finishing this releases N elsewhere" — is the reading a bar chart
    # hides, and it is what says which slice to point hands at.
    for sid, row in sl.items():
        feeds: Counter[str] = Counter()
        for other, o in sl.items():
            if other != sid:
                feeds[other] = len(o["upstream"].get(sid, []))
        row["feeds"] = {k: v for k, v in feeds.items() if v}

    slices_of: dict[str, list[str]] = defaultdict(list)
    for s in slice_rows:
        slices_of[s["program"]].append(s["id"])

    pg: dict[str, Any] = {}
    for g in program_rows:
        mine_slices = slices_of.get(g["id"], [])
        rows = [sl[x] for x in mine_slices if x in sl]
        proven = all_shipped(g["verified_by"], proofs_by_num, drills)
        # `board()`'s rule, read the same way: the cuts the program KEPT, each complete or waived.
        kept = [r for r in rows if r["state"] != "withdrawn"]
        all_done = bool(kept) and all(r["state"] in SETTLED_SLICE_STATES for r in kept)
        any_live = any(r["live"] for r in rows)
        if is_withdrawn(g):
            state = "withdrawn"
        elif not rows:
            state = "empty"
        # `proven` is False for an empty `Verified by`, so a program naming no composed proof
        # can never read complete. That is what keeps this tier's completion condition
        # distinct from its slices': the slices going complete is necessary, never sufficient.
        elif all_done and proven:
            state = "complete"
        elif not any_live:
            # Every member PRD is terminal and something is still unproven. NOT "moving":
            # nothing is moving. Keyed on THIS program's own proof first — asking only whether
            # some slice is awaiting-proof files a program that names an unshipped proof as a
            # paperwork gap, which is its own outstanding work mislabelled as a missing line.
            outstanding = (
                (g["verified_by"] and not proven)
                or g["id"] in still_owed
                or any(r["state"] == "awaiting-proof" for r in rows)
            )
            state = "awaiting-proof" if outstanding else "unproven"
        elif any(r["state"] == "moving" for r in rows):
            state = "moving"
        else:
            state = "blocked"
        pg[g["id"]] = {
            "state": state,
            "proven": proven,
            # An objective-tier program without a proof can never complete — the guard that
            # stops substrate acquiring a roadmap bar. Surfaced, not hidden.
            "unprovable": g["kind"] == "program" and not g["verified_by"],
            "slices": mine_slices,
            "live": sum(len(r["live"]) for r in rows),
            "ready": sum(len(r["ready"]) for r in rows),
            "total": sum(r["total"] for r in rows),
            "shipped": sum(r["shipped"] for r in rows),
            "cancelled": sum(r["cancelled"] for r in rows),
        }

    wave_counts: Counter[int] = Counter(p["wave"] for p in live.values())
    active = [s for s, r in sl.items() if r["live"] and r["state"] != "withdrawn"]
    return {
        "prd": {
            n: {"wave": p["wave"], "blocks": p["blocks"], "unmet": p["unmet"], "external": p["external"]}
            for n, p in live.items()
        },
        "slice": sl,
        "program": pg,
        "waves": [wave_counts.get(i, 0) for i in range(max(wave_counts) + 1)] if wave_counts else [],
        "active": len(active),
        "wipLimit": wip_limit,
        "liveTotal": len(live),
        "readyTotal": sum(1 for p in live.values() if not p["unmet"]),
        # Chokepoints: the live PRDs whose completion unblocks the most. No tier above the
        # PRD can show it.
        "choke": [{"n": n, "blocks": b} for n, b in blocks.most_common(choke_top) if b and n in live],
    }


# ─────────────────────────── the board reading ───────────────────────────
#
# A second, coarser roll-up over the same registers, for a program-first board. It answers a
# different question from `delivery()` — "which programs are moving, and which need a
# decision from a human" rather than "which PRD should be picked up next" — so it names its
# slice states differently on purpose. Both derive from the same three inputs and the same
# `all_shipped` proof rule, so they cannot disagree about what *complete* means.

# THE LEGEND, BOTH TIERS. Six words a program and a slice share, plus the two only a slice can
# be in (a program with no slices is `empty` too, but "abandoned" is a reading over members and
# a program has none of its own):
#
#   complete        every member terminal and the named proof shipped. At the PROGRAM tier: its
#                   own named proof shipped and every cut it kept is complete OR waived
#                   (`SETTLED_SLICE_STATES`) — a waived cut is settled by a written decision
#   flight          a live PRD somewhere under it
#   awaiting-proof  every member terminal, a proof NAMED and not yet shipped — real work. Or
#                   no proof named and a DEFERRED waiver saying the proof is still owed
#                   (2026-10-07): the same outstanding work, with `owed` saying what it is
#   unproven        every member terminal, NO proof named, nobody has said why — a one-line edit
#   waived          every member terminal, no proof named, and an EXCUSED waiver on the record:
#                   *no proof is needed, and here is why*, written down
#   withdrawn       the register's `Disposition` took it out of the plan — `withdrawn:` citing
#                   a decision record, or `superseded by` a named successor
#
# `unproven` and `waived` were ONE state on this board until the baseline reached it, and the
# collapse hid the largest number on the page: a slice somebody had deliberately excused and a
# slice nobody had looked at drew the same chip. `awaiting-proof` was folded into `unproven` for
# the same reason and to the same effect — a named, unshipped proof is outstanding WORK, and a
# blank cell is a missing LINE, and the two need opposite hands.
BOARD_SLICE_STATES = ("complete", "flight", "awaiting-proof", "unproven", "waived", "withdrawn", "empty", "abandoned")
BOARD_PROGRAM_STATES = ("complete", "flight", "awaiting-proof", "unproven", "waived", "withdrawn", "empty")
#: The states that sit OUTSIDE the plan on both tiers: nothing counts them as open, nothing
#: dispatches into them, and a page draws them collapsed at the foot, out of every total. Named
#: once so the three places that make that exclusion — the roll-up, the board's counts and the
#: page — cannot each pick a different pair.
BOARD_PARKED_STATES = frozenset({"waived", "withdrawn"})
#: THE SLICE STATES A PROGRAM MAY CLOSE OVER (the operator's decision, 2026-09-17, narrowed
#: 2026-10-07). A program whose OWN named proof has shipped is finished once every cut it kept reads
#: one of these: `complete`, or `waived` — an EXCUSED waiver, *this proof is not needed*, and
#: nothing live in the cut (a waived cut with live work reads `flight`, so it stays open work).
#:
#: ONLY AN EXCUSED WAIVER SETTLES (2026-10-07). A DEFERRED waiver — *the proof is still owed, to be
#: measured later* — reads `awaiting-proof`, which is not in this set, so the program stays open and
#: says what it waits on (`waiting_on`) until the proof lands. Production's PG-21 closed over SL-188
#: on 2026-10-06 under the old reading, while SL-188's own waiver said its proof was a Bar to be
#: authored "once the driver's live measurements land": owed, not excused. It used
#: to be `complete` alone, and production's PG-13 — proof 0582 shipped, SL-109 proven, SL-111
#: waived — could never read proven: its page offered a `finish` row asking somebody to un-waive a
#: cut a person had already decided would not be proven. A waiver is a decision, and a decision
#: that can never be acted on is not one. A program whose OWN proof is waived is untouched by this:
#: `all_shipped([])` is False, so it never reads `complete` and stays parked as `waived`.
SETTLED_SLICE_STATES = frozenset({"complete", "waived"})
#: A program nothing re-plans: proven, or parked by a written waiver of its proof with nothing left
#: open. `waived` the STATE and never the flag — a waived program with cuts
#: in flight is still being delivered (ENG-10683). Nothing re-plans one of these (ENG-10691).
CLOSED_PROGRAM_STATES = frozenset({"complete", "waived"})


# ─────────────────────────── the bar reading ───────────────────────────
#
# Everything above this line is arithmetic over files: which PRDs are terminal, which named
# proof shipped. That reading is right about artifacts and blind to whether the thing those
# artifacts compose actually works, and it always will be — its inputs are files. A `## Bar`
# is the observation it cannot make: what somebody would have to SEE hold in a running system,
# authored ahead of the work, each condition beside the probe that could refute it.
#
# **A bar is a commitment, and this reads the commitment.** Whether it is met today is an
# observation of one deployment at one instant, true of a moment and false an hour later with
# no file changed. Nothing here computes, stores or returns a verdict, and nothing downstream
# of it should either — three counts and a shape, which is all a board is entitled to say.

#: The two tier names `bars.parse` is told, spelled the same way the commit gate spells them.
#: Which tier carries the digest is the whole asymmetry of the contract: a slice bar decomposes
#: a completion sentence living in ANOTHER file and binds to its bytes; a program bar decomposes
#: a demonstration it authors inside itself and so binds across nothing.
SLICE_TIER = "slice"
PROGRAM_TIER = "program"

#: A probe cell that answers *"there is none"*. Matched on the OPENING rather than on a literal,
#: because both authored forms open the same way and differ after it — `No probe yet. …` and
#: `**No probe exists yet — …**` — and the emphasis a program bar wraps its answer in is stripped
#: first so the markup is not what decides.
_NO_PROBE_RE = re.compile(r"^\**\s*no probe\b", re.I)


def unprobed(probe: str) -> bool:
    """Whether a criterion's probe cell holds no actual probe.

    Two cells count: one that SAYS there is no probe, and one that says nothing at all. Both
    mean the criterion has never been read either way, which is the fact a board is showing.
    They are not the same authoring defect — a stated absence is an answer and a blank is a row
    somebody left half-written — but that difference is a finding the commit gate makes against
    the file, not a distinction a count of unread conditions can carry.
    """
    stripped = probe.strip()
    return not stripped or bool(_NO_PROBE_RE.match(stripped))


def bar_reading(body: str, entity: str, tier: str) -> dict[str, Any] | None:
    """One entity's `## Bar`, as the three numbers a board shows. `None` when it has none.

    `None` and `{"n": 0, …}` are different facts and stay different: the first is an entity that
    authored no bar — the ordinary case, since a bar is optional and monotone — and the second
    is one that authored the heading and put nothing under it.

    `digestOk` says the bar carries a digest EXACTLY WHERE ITS TIER REQUIRES ONE, and no more
    than that. It is deliberately not a claim that the digest still matches what it decomposes:
    the sentence a slice bar binds to lives in the register, this reads shaped rows that have
    already one-lined and clipped that cell, and a match computed from the wrong bytes would
    report a break nobody made. The commit gate holds the binding, against the file.
    """
    bar = bars.parse(body, entity, tier)
    if bar is None:
        return None
    # An empty marker (`sha256:` with nothing after it) names no digest, so it is not one.
    carries = bool(bar.digest)
    return {
        "n": len(bar.criteria),
        "unprobed": sum(1 for c in bar.criteria if unprobed(c.probe)),
        "digestOk": carries == (tier == SLICE_TIER),
    }


#: The ceiling on a derived description. A board row is an index entry and not a paragraph: it
#: shows enough to recognise the program and links to the file for the rest. `clip` prefers a
#: sentence end inside that budget, so the ordinary result is a whole sentence rather than a cut.
DESC_CHARS = 240


def lead_reading(body: str) -> str | None:
    """A program's short description, read out of the opening prose of its detail file.

    **THERE IS NO AUTHORED DESCRIPTION AT THIS TIER AND THIS DOES NOT ADD ONE.** A slice carries
    `Done when` — one checkable sentence, in the register, a column precisely so it cannot be
    skipped. `programs.md` has six columns and none of them is that: `ID | Name | Kind |
    Verified by | Requires | Disposition`. What a program does have is an OPTIONAL detail file, and every one
    of them opens the same way — an H1, then a paragraph saying what somebody gets. That
    paragraph is what this returns. It is a convention being READ, never a field being asked
    for: nothing here requires an author to write anything new, and a file that does not follow
    the convention reads as having no description rather than as having a summary this function
    invented for it. Authoring a real column is a corpus decision and is not one a reader makes.

    **Three answers, and they are three different facts:**

      * `None` — no detail file (or one with no bytes in it). NOTHING WAS READ.
      * `""`   — a file was read and its opening carries no prose: an H1 straight into a `##`,
                 or a lead made only of a list, a table or a quote. That is a finding about
                 that file, and it is not the same fact as a file nobody wrote.
      * text   — the description.

    Collapsing the first two is the defect 0044 names one tier up, in the same shape: it would
    make *"nobody wrote this file"* indistinguishable from *"the file opens wrong"*, and a page
    would then render both as a blank that reads like an authored one.

    The lead is everything before the first `## `, because that is where a file stops introducing
    itself and starts sectioning. Inside it, `first_paragraph` takes the first paragraph that is
    PROSE — skipping a table, a quote and a list. That skip does real work here rather than being
    inherited: the corpus this package came from has one program whose lead opens with a bolded
    aside about the entity's own naming, which is a run-in label rather than a description, and
    the sentence after it is the one a reader wants.
    """
    if not body:
        return None
    text = strip_frontmatter(body)
    h1 = re.search(r"^#\s+.+$", text, re.M)
    if h1:
        text = text[h1.end() :]
    lead = re.split(r"^##\s+", text, flags=re.M)[0]
    return first_paragraph(lead, DESC_CHARS)


def board(
    prd_rows: list[dict[str, Any]],
    slice_rows: list[dict[str, Any]],
    program_rows: list[dict[str, Any]],
    *,
    details: Mapping[str, str] | None = None,
    waivers: Waivers | None = None,
    drills: Drills | None = None,
    summaries: Mapping[str, str] | None = None,
    owed: Owed | None = None,
    loose: list[dict[str, Any]] | None = None,
    proofs: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Programs with their slices, their counts and the flags a human has to act on.

    `loose`, when a list is handed in, receives every slice that rolls up to NO program — an AREA
    slice (2026-10-27, FLT-1280) — read by the same arithmetic as every other cut, in id order. The
    return value stays the program list, so a caller that passes nothing reads exactly as before.

    Every number is a COUNT. There is no percentage of progress, no date and no estimate —
    the bar a viewer draws from these is geometry, and its label is "3 done · 2 in flight".

    `details` is `entity id -> the text of that entity's detail file`, and it is where the
    `## Bar` sections come from. TEXT rather than parsed bars, and an ARGUMENT rather than a
    path: this module is pure over values and reads no filesystem, so the caller does the one
    thing that needs a disk and the reading of what a bar says stays here, in one place, beside
    the completion arithmetic it exists to complement. Omitted, every entity reads as carrying
    no bar — which is what a corpus with none actually looks like.

    `waivers` and `drills` arrive the same way and for the same reason: both are files, and the
    caller opens them. `waivers` is `{"slice": ids, "program": ids}` — the EXCUSED waivers only —
    and it is what makes `waived` a state distinct from `unproven` (see `BOARD_SLICE_STATES`);
    omitted, nothing is waived. `owed` is the other half (2026-10-07): `{id: what is owed}` for every
    DEFERRED waiver at either tier. Such an entity reads `awaiting-proof` with `owed` on its row, its
    program cannot read `complete` over it, and the program's flags say what it waits on. `drills` is
    `registers.drills`'s reading and resolves every `drill:<stem>` proof entry; omitted, such an entry reads unshipped
    — never as a PRD that happens to be missing.

    `summaries` is `{prd number: plain words}` (ENG-12792), carried onto each member row so a
    PRD page can read its own description. It arrives as a value for `details`' reason: the
    convention that derives it lives one layer up, and this module reads no prose off a disk.
    Omitted, every member row carries `""`, which is a corpus whose caller read no summaries
    rather than a PRD with an empty one.

    `proofs` is the PRDs of the DECLARED SIBLING corpora a `Verified by` cell may name with a
    qualifier (`sib:0770`), keyed by exactly that qualified entry. It arrives as a value for
    `details`' reason — reading a sibling is a disk (or a register) the caller holds — and it
    resolves PROOFS only: a sibling's rows never enter this corpus's membership arithmetic.
    Omitted, a qualified entry reads unshipped, which is the old answer for a corpus that
    declares no sibling.
    """
    detail: Mapping[str, str] = details or {}
    plain: Mapping[str, str] = summaries or {}
    waived_ids: Waivers = waivers or {}
    slice_waivers = waived_ids.get(SLICE_TIER, frozenset())
    program_waivers = waived_ids.get(PROGRAM_TIER, frozenset())
    still_owed: Owed = owed or {}
    proofs_by_num = proof_index(prd_rows, proofs)
    members: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in prd_rows:
        if p["slice"]:
            members[p["slice"]].append(p)

    program_proofs = {g["id"]: {str(x) for x in g.get("verified_by") or []} for g in program_rows}
    stopped = withdrawn_programs(program_rows)

    out_sl: dict[str, dict[str, Any]] = {}
    for s in slice_rows:
        mem = sorted(members.get(s["id"], []), key=lambda x: x["n"])
        live = [p for p in mem if p["status"] not in PRD_TERMINAL]
        ship = [p for p in mem if p["status"] == "shipped"]
        proven = all_shipped(s["verified_by"], proofs_by_num, drills)
        cut_proofs = program_proofs.get(s["program"], set())
        ground = capability_ground_met(mem, cut_proofs)
        waived = s["id"] in slice_waivers
        # A DEFERRED waiver (2026-10-07): the proof is still owed. Never also `waived` — an id is
        # excused or deferred, and a caller handing both is read as owing, the conservative side.
        owes = still_owed.get(s["id"]) or ""
        waived = waived and not owes
        # Where that owed proof can only be taken (2026-10-08), off the cut's own waiver row — `""` for a
        # proof the fleet can produce itself, and for a legacy baseline line, which cannot say.
        needs = str(s.get("proof_waiver_needs") or "") if owes else ""
        if is_withdrawn(s) or s["program"] in stopped:
            # THE DECISION AXIS WINS OVER THE ARITHMETIC. A withdrawn cut with a live member is
            # a validator ERROR (the register said stop and the PRD did not), so on a gated
            # corpus this branch never hides live work; on an ungated one it shows the decision
            # rather than a `flight` chip that would argue with it. A cut under a withdrawn
            # PROGRAM is withdrawn with it — see `withdrawn_programs`.
            state = "withdrawn"
        elif live:
            state = "flight"
        elif not mem:
            state = "empty"
        elif not ship:
            # Every member terminal and none shipped: the slice was abandoned, which is a
            # different fact from unproven and must not be shown as one.
            state = "abandoned"
        elif proven:
            state = "complete"
        elif s["verified_by"] or owes:
            # Named and not shipped: outstanding WORK, and the opposite hand from a blank cell. A
            # DEFERRED waiver is the same work with no proof named yet — it is owed, not excused.
            state = "awaiting-proof"
        elif waived:
            # Blank cell, and the baseline says so on purpose. Somebody looked.
            state = "waived"
        else:
            state = "unproven"
        out_sl[s["id"]] = {
            "id": s["id"],
            "name": s["title"],
            "kind": s["kind"],
            "program": s["program"],
            # Its feature area (FLT-1280): a feature map's slug; `""` on a row written before the rule. A slice
            # with no program rolls up into no program row below (`by_prog[""]` is read by none).
            "area": str(s.get("area") or ""),
            "done_when": s["done"],
            "proof": s["verified_by"],
            # Either shape is accepted: `corpus.slice_rows` renames the column to `dep`,
            # a raw `registers.slices` row still calls it `depends_on`.
            "dep": s.get("dep", s.get("depends_on", [])),
            "components": s.get("component", []),
            "state": state,
            "proven": proven,
            # The decision axis, verbatim from the register: `{"kind", "ref"}`. Beside `state`
            # because `withdrawn` is the one state a page has to explain in the register's own
            # words — WHICH decision record, WHICH successor — and the state alone cannot.
            "disposition": dict(s.get("disposition") or {"kind": ADOPTED, "ref": None}),
            # The baseline's word, as a FLAG and not only as a state: a waived cut that still
            # holds live work is `flight`, and the finding that would ask it for a proof has to
            # know it was excused whichever state it is in.
            "waived": waived,
            # What a DEFERRED waiver says is still owed (2026-10-07), `""` for none. Beside `waived`
            # because the two are the two kinds of one record, and a page says "waiting on SL-188's
            # proof: <this>" rather than drawing a deferred cut as a decided one.
            "owed": owes,
            # Where that owed proof can only be taken (2026-10-08): `registers.NEEDS_PRODUCTION` — a check only a person
            # with production access runs (`production_check`) — or `""`, owed work the fleet can produce.
            "owedNeeds": needs,
            # Dependents gate on this, not on `state == complete` (ENG-10184). See
            # `capability_ground_met`.
            "groundMet": ground,
            # What this cut has to be seen doing, or None when nobody has said. Beside `proof`
            # because they answer adjacent questions and neither substitutes for the other: a
            # proof names the artifact that shipped, a bar names the observation.
            "bar": bar_reading(detail.get(s["id"], ""), s["id"], SLICE_TIER),
            "prds": [
                {"n": p["n"], "status": p["status"], "title": p["title"], "summary": plain.get(p["n"], "")} for p in mem
            ],
            "nlive": len(live),
            "nship": len(ship),
            "n": len(mem),
        }

    by_prog: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in out_sl.values():
        by_prog[s["program"]].append(s)
    if loose is not None:
        loose.extend(sorted((s for s in out_sl.values() if not s["program"]), key=lambda x: x["id"]))

    out_pg: list[dict[str, Any]] = []
    for p in program_rows:
        ss = sorted(by_prog.get(p["id"], []), key=lambda x: x["id"])
        c = Counter(s["state"] for s in ss)
        proofok = all_shipped(p["verified_by"], proofs_by_num, drills)
        bar = bar_reading(detail.get(p["id"], ""), p["id"], PROGRAM_TIER)
        owes = still_owed.get(p["id"]) or ""
        waived = p["id"] in program_waivers and not owes
        withdrawn = is_withdrawn(p)
        # A WITHDRAWN CUT IS OUT OF THE PLAN, SO IT IS OUT OF THE COMPLETION ARITHMETIC. The
        # register said that cut stopped, and a program that finished every cut it kept and
        # shipped its composed proof is complete — holding it open for a cut nobody is going to
        # build would be the derivation arguing with the decision. A WAIVED cut closes the same way
        # once the program's OWN proof has shipped (`SETTLED_SLICE_STATES`): the program's proof is
        # what proves the program, and the waiver is a person's written word that this cut will not
        # be proven on its own. The page names the waived cuts beside the proven chip, so the
        # record says what the program closed with.
        kept = [x for x in ss if x["state"] != "withdrawn"]
        complete = bool(kept) and all(x["state"] in SETTLED_SLICE_STATES for x in kept) and proofok
        # THE PROGRAM'S OWN STATE, in the slice tier's legend. The counts below are what the bar
        # draws; this is the one word a list sorts and groups on, and it is derived by the same
        # rule at both tiers so a program and its cuts cannot disagree about what a word means.
        # `awaiting-proof` reads THIS program's cell first (a named, unshipped composed proof is
        # its own outstanding work) and only then its cuts' — `delivery()` makes the same call
        # for the same reason.
        if withdrawn:
            state = "withdrawn"
        elif not ss:
            state = "empty"
        elif complete:
            state = "complete"
        elif c["flight"]:
            state = "flight"
        elif (p["verified_by"] and not proofok) or c["awaiting-proof"] or owes:
            state = "awaiting-proof"
        elif waived:
            state = "waived"
        else:
            state = "unproven"
        # The flags are the whole point of the board: each one names a thing only a human can
        # settle, in the words of the decision rather than the words of the data model. A
        # withdrawn program raises NONE: the decision has been made and written down, and a
        # flag asking somebody to cut slices into a program they stopped is the board arguing
        # with the register.
        flags: list[str] = []
        if withdrawn:
            pass
        elif not ss:
            flags.append("no slices cut — nothing can be dispatched into this")
        elif len(ss) == 1:
            flags.append("only one slice — a program is meant to hold at least two")
        if not withdrawn and ss and p.get("requires") == []:
            # Distinct from "no slices cut": this program HAS children, so nothing upstream
            # reports it as unplanned, yet `gen_program_plan` has no roots to close over. The
            # two states look identical on every count on this row, which is why the flag has
            # to say it.
            #
            # NEVER "cannot be derived" (ENG-10704 item 8). That was true of every program this
            # flag fires on when it was written — no roots meant no build order, full stop — but
            # `board.program_step` has since learned a program can be short of its roots with
            # every slice already cut and driven (production's PG-21: five of six slices done,
            # proof shipped, the sixth in flight, `requires == []` throughout). For a program
            # like that the build order is not missing — it is sitting on the slices themselves,
            # already served — so the flag says the fact without a claim the ladder now
            # sometimes disproves. `program_step`'s own next-step reading is what tells the two
            # apart on the page (a `decompose` To-do row for one, none for the other); this flag
            # is a hygiene fact about the roots either way, worded so it is never wrong.
            flags.append("no decomposition roots named — the build order is read from the slices")
        # WHAT A DEFERRED WAIVER LEAVES OWED, NAMED (2026-10-07): the program's own, then each kept cut's.
        # This is the reason a program that would otherwise read finished stays open, so it is said in
        # the one sentence every surface uses (`waiting_on`).
        waiting = [] if withdrawn else [waiting_on(p["id"], owes)] if owes and not p["verified_by"] else []
        if not withdrawn:
            waiting += [waiting_on(x["id"], x["owed"]) for x in ss if x["owed"] and x["state"] == "awaiting-proof"]
        flags.extend(waiting)
        if withdrawn or (owes and not p["verified_by"]):
            pass
        elif waived and not p["verified_by"]:
            # The baseline is the human's answer to the flag below, so the flag does not fire —
            # but the fact that this can never read complete is still true and still shown,
            # in the words of the decision that was taken rather than the one that is owed.
            flags.append("no proof planned — waived in the programs baseline, so this can never be proven")
        elif not p["verified_by"]:
            flags.append("no proof named — this can never be proven")
        # `c["complete"] == len(ss)` and not `complete + unproven`: the same narrowing, and for
        # the same reason, as `finished` in `board.actions` — an `unproven` cut has a proof of
        # its own outstanding, so "every slice finished" was a claim this flag was not entitled
        # to make. The two are deliberately the same arithmetic: a flag and a finding that
        # disagreed about what *finished* means would put two readings of one program on one
        # page.
        elif not proofok and kept and c["complete"] + c["waived"] == len(kept):
            flags.append("every slice finished, proof not shipped")
        # Only at the objective tier, and only there. A bar is optional across the corpus and
        # flagging every entity without one would put a finding on almost all of them, which
        # teaches a reader to skip the column. A `kind: program` is the one entity that already
        # owes somebody a demonstration, so absence there is a gap rather than a default.
        if not withdrawn and p["kind"] == PROGRAM_TIER and bar is None:
            flags.append("no success criteria written — nothing says what would have to be seen")
        # NOT ON A PROVEN PROGRAM (ENG-10589). Nothing is in flight because nothing is left, and a
        # flag beside the proven chip read as a contradiction on the production board. A flag is
        # a thing somebody could settle; on a finished program there is nothing to settle.
        if not withdrawn and ss and not c["flight"] and not complete:
            flags.append("nothing in flight")
        out_pg.append(
            {
                "id": p["id"],
                "name": p["title"],
                "kind": p["kind"],
                "proof": p["verified_by"],
                # The one word — see above. In `BOARD_PROGRAM_STATES`.
                "state": state,
                # The decision axis, verbatim from the register. See the slice row's.
                "disposition": dict(p.get("disposition") or {"kind": ADOPTED, "ref": None}),
                # The programs baseline's word, as a flag — the slice row's `waived`, one tier up.
                "waived": waived,
                # What the program's own DEFERRED waiver leaves owed, `""` for none — the slice
                # row's `owed`, one tier up (2026-10-07).
                "owed": owes,
                # The composed demonstration this program authors, or None when it has none.
                "bar": bar,
                # The short description, out of the detail file's opening prose. `None` when
                # there is no file to read — DISTINCT from `""`, a file that opens with none.
                # Beside `bar` because both are readings of the same bytes, and neither is a
                # column: this tier's register has no description and this does not add one.
                "desc": lead_reading(detail.get(p["id"], "")),
                # An INPUT to a finding, which makes it as load-bearing as a rendered field:
                # `store.board` recomputes the findings from the projection, so this has to
                # survive a round trip through it (fleet-service 0044). `[]` is a program that
                # names no roots — the finding — and `None` is a reading that never looked.
                "requires": p.get("requires"),
                "sl": ss,
                "proofok": proofok,
                "done": c["complete"],
                "flight": c["flight"],
                # THE BAR'S THIRD SEGMENT KEEPS ITS NAME AND WIDENS ITS MEANING. `awaiting-proof`
                # split out of `unproven` above, and the bar a page draws is four segments —
                # done, in flight, awaiting proof, not started — so both cuts with a proof
                # outstanding land here, and the legend on the row says "awaiting proof", which
                # is true of both. The split is on the slice row, where it is actionable.
                "unproven": c["unproven"] + c["awaiting-proof"],
                # Out of the plan, and out of the bar: a waived or withdrawn cut is not "not
                # started", and drawing it as idle would show a decision as a gap.
                "idle": c["empty"] + c["abandoned"],
                # Two counts and not one: `finished` in `board.actions` needs the withdrawn
                # count alone (a withdrawn cut is out of the arithmetic; a waived one is not),
                # and a page needs both to say what its bar is not drawing.
                "waivedSlices": c["waived"],
                "withdrawnSlices": c["withdrawn"],
                "nsl": len(ss),
                "livePRDs": sum(s["nlive"] for s in ss),
                "complete": complete,
                "flags": flags,
            }
        )
    return out_pg


# ─────────────────────────── the gap queries ───────────────────────────
#
# Four questions the corpus can answer and no single file shows. Each is a SET, never a
# score: "which capabilities have nothing shipping them" is actionable, "83% coverage" is a
# number that moves for reasons nobody can name.


def capability_gaps(features: list[dict[str, Any]], *, include_substrate: bool = False) -> list[dict[str, Any]]:
    """Capabilities with no shipping PRD and no built marker — the real delivery gaps.

    A `(core)`, `(shipped)` or `(retired)` marker is EVIDENCE THE CAPABILITY IS BUILT, not an
    absent PRD. Reading a marker as absence is a measured 75%-false gap signal, and it is the
    single most repeated defect in this class of reader.
    """
    out: list[dict[str, Any]] = []
    for f in features:
        if not include_substrate and f.get("kind", "product") == "substrate":
            continue
        for c in f["caps"]:
            if not c["ships"] and not c["mark"]:
                out.append({"area": f["area"], **c})
    return out


def untested_capabilities(features: list[dict[str, Any]], *, include_substrate: bool = False) -> list[dict[str, Any]]:
    """Capabilities no journey exercises, in either direction of the edge."""
    out: list[dict[str, Any]] = []
    for f in features:
        if not include_substrate and f.get("kind", "product") == "substrate":
            continue
        for c in f["caps"]:
            if not c["tested"]:
                out.append({"area": f["area"], **c})
    return out


def unclaimed_commitments(reqs: list[dict[str, Any]], prd_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Adopted commitments no PRD claims through `implements:`.

    The population is adopted rows ONLY. A rejected or superseded row is not in force and
    therefore cannot be "unclaimed" — counting them was two halves of one ratio measuring
    different sets.
    """
    claimed: set[str] = {rid for p in prd_rows for rid in p["impl"]}
    return [r for r in reqs if r["disp"] == "adopted" and not r["sup"] and r["id"] not in claimed]


def open_decisions(reqs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Register rows still `open` — a commitment written down and never settled."""
    return [r for r in reqs if r["disp"] == "open" and not r["sup"]]
