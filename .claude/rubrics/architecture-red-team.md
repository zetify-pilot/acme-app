---
type: spec
---

# Design Critique — the pre-ship architecture red-team

This spec defines the **`architecture-red-team`** critique rubric: an adversarial pass
over a *proposed* design, run **before** the design is finalized, whose job is to argue
the design is **wrong** and to surface a materially stronger alternative. It is the
operational form of the golden rule — *"actively hunt for a better design than the one
proposed; the goal is always the best technical solution, never the easiest."* A rule in
CLAUDE.md that lives only as an exhortation gets skipped under deadline pressure; this
turns it into a **named step with a rubric and a disposition gate**.

It is the design-time sibling of [`design-fidelity-loop.md`](../process/design-fidelity-loop.md):
that spec makes UI *look* good against a reference; this one makes the *architecture*
right against a skeptic.

## When it runs — and how it differs from the Phase 1.5 audit

`prd:design` already has an architecture pass — **Phase 1.5**, which audits the
**surrounding, already-shipped code** the feature will touch and dispositions the quirks
it inherits. The red-team is the mirror image:

| | Phase 1.5 (Architecture Audit) | Phase 2c (Design red-team — this rubric) |
|---|---|---|
| Target | the **existing** code around the feature | the **new** design we're about to commit to |
| Question | "what quirks am I inheriting?" | "is the thing I'm proposing actually right?" |
| Failure it catches | silently inheriting drift | shipping a plausible-but-wrong design |

They are complementary, not redundant: 1.5 looks backward at what exists, 2c looks forward
at what we're adding. The red-team runs **after** the technical design has taken shape
(Phase 2 / 2b) — you need a concrete design to attack — and **before** reuse/gaps/output.

## The rubric (`architecture-red-team`)

An independent critic grades the proposed design against seven questions. Each names a
specific failure mode, not a generic "is it good?" — and where a question asks about
*this* product's invariants, the invariants come from the repo's `slot:commitments` and
`slot:runtime-contracts`, never from this page:

- **R1 — Simplest thing that works?** Does the design add a table, service, event, cache,
  abstraction, or generality the PRD doesn't need *yet*? Name the simpler design and say
  why it was rejected. (over-engineering — the most common failure)
- **R2 — Or under-built?** Does it ignore a **load-bearing invariant** that will force a
  rewrite — the ones `slot:commitments` and `slot:resilience` name for this repo
  (replica safety, narrowing-only reads, a sole-writer rule, idempotency, failure/retry,
  scale — whichever of those this product actually holds)? (under-engineering)
- **R3 — Consistent, or a parallel pattern?** Does it match the closest existing pattern,
  or invent a second way to do the same thing? A divergence must be justified **in
  writing**, or it is drift the next reader will copy.
- **R4 — Right boundaries?** Is each responsibility in the layer that owns it (the layers
  `slot:architecture` names; generated vs hand-written), or does the design leak
  logic across a boundary?
- **R5 — Is there a materially stronger alternative?** The critic MUST name at least one
  concrete alternative design and argue it — then either concede it wins, or say why the
  chosen one still does. **"No alternative considered" is not an acceptable answer** for a
  load-bearing design.
- **R6 — Blast radius if wrong?** Is this a **one-way door** — a schema, wire contract,
  permission model, or interface others will build on — or is it cheaply reversible? A
  one-way door with weak justification is the **highest-priority** finding.
- **R7 — Commitments: contradicted, dropped, or created and unrecorded?** Trace the rows
  this design claims (`implements:`) and the `Needs` edges hanging off them, and ask the
  three questions no script can answer: does the design **contradict** a commitment we still
  carry; does it **silently drop** one — cut the mechanism a live row describes without
  superseding that row; and has it **created** a commitment (a ceiling, a refused option, a
  cost taken knowingly) it failed to record? The motivating case: **PRD 0486 claimed 16 rows,
  and seven of those claims declared `Needs` edges into the plane-side build tier that
  0486's own biggest Non-Goal deletes** — *"the build does not happen on the plane — the
  single biggest cut."* Because the needed rows are `adopted`-and-deferred rather than
  superseded, the edges survived the cut, and the graph asserted the critical-path PRD was
  unsatisfiable until v2. `python3 knowledge/scripts/requirement_query.py prd <n>` will list the unsatisfied
  needs and `make validate-knowledge`'s claim-scope rule will raise the shape as an
  advisory; **neither can tell you the edge should not exist at all.** That judgement is
  what this lens buys, and it is the only one of the seven that reads the design against
  what the product has already promised rather than against itself.

## The protocol

1. **Dispatch an independent critic.** Spawn a sub-agent that did **not** author the design
   and task it explicitly to *argue the design is wrong* and produce the strongest
   alternative — default posture is skepticism, not ratification. For a **high-blast-radius**
   design (an R6 one-way door), use a small **panel** with distinct lenses — one on
   simplicity (R1/R3), one on the invariants and the commitments (R2/R7), one whose only job
   is R5 (find the better design) — because a single generalist critic misses failure modes a
   diverse panel catches.

   **R7 is a lens on this panel, never a panel of its own.** One more question for a critic
   who has already read the design closely enough to attack it is nearly free; a second,
   commitments-only panel would double the cost of *every* design to ask something the
   sitting panel is already positioned to answer. R7 rides with R2 for the same reason it
   exists: a dropped commitment is an invariant leaving the building without anyone
   recording that it left.
2. **Disposition every finding — hard gate.** The coordinator walks each finding with the
   user (design is interactive) and records one of: **adopt** (fold the change into the
   design) or **reject-with-reason**. This mirrors Phase 1.5's fix / defer / perpetuate
   discipline — **do not advance to output until every red-team finding has an explicit
   decision.** A "reject" is legitimate (the critic can be wrong), but the reason goes on
   the record in the design's **Architecture notes**, exactly like a "perpetuate", so a
   future reader sees the alternative was considered and consciously declined.
3. **Adopt ≠ redo.** A finding that changes the design loops back into Phase 2 for that
   layer only — it does not restart discovery.

The gate is **hard** in the "must-disposition" sense (no un-decided finding), **not** in
the "must-adopt" sense — the critic surfaces and argues; the human decides. That is the
honest teeth: it forces the alternative onto the table where the golden rule wants it,
without letting a skeptic veto a design the author can defend.

## How it's wired (the command spine)

Registered in [`spine.md`](../process/spine.md)'s `critique_rubrics` as
`architecture-red-team`, with a coverage rule `{produces: ["design"], requires:
"architecture-red-team"}`. Because `prd:design`'s `output` step **produces** the `design`
artifact, the command-spine validator now **fails** `design.md` unless it carries a gate
or loop critiquing against this rubric — the red-team can no longer be quietly dropped.
`prd:design` satisfies it with **Phase 2c**: a `fanout` step (the independent critic
panel, on the strongest model the harness offers) feeding a hard `gate` step (`disposition each finding`).

## Related

- [`spine.md`](../process/spine.md) — the critique-coverage map this rubric plugs into
  (invariant 2); adding *this* rule was the first extension beyond the UI taste gate.
- [`design-fidelity-loop.md`](../process/design-fidelity-loop.md) — the UI-craft sibling (make it
  *look* right); this one makes the architecture *be* right.
- the **`audit-profile`** slot's architecture checklist — the **post-ship**,
  whole-codebase anti-rot audit; the red-team is its **pre-ship, single-design** counterpart.
- `prd:design` Phase 1.5 — the surrounding-code audit this pass complements.
