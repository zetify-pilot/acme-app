---
type: spec
---

# Docs — the rubric a user-facing page is graded against

This spec defines the **`rubric-docs`** critique rubric: what a page in the product's
user-facing documentation has to hold to be worth shipping. It is graded by the page
commands (`page:spec`, `page:improve`) and read by every step that admits a docs change, so
one taxonomy means one thing wherever a page is written.

It is the docs sibling of [`architecture-red-team.md`](architecture-red-team.md): that rubric
makes the design right, this one makes the page usable. Both are instructions a reviewer
grades against, and neither is a gate that can be faked — see
[`spine.md`](../process/spine.md) for how a rubric attaches to a step.

## One page is one kind

Every page is exactly one of four kinds, and a page that reads as two is two pages. The kind
is the reader's *intent* when they arrive, never the page's length.

| Kind | The reader arrived to… | Success looks like |
|---|---|---|
| **tutorial** | learn by doing, from a known start | they finished a working thing without a detour |
| **how-to** | get one real task done | the task is done, and they know it is |
| **reference** | look one fact up | the answer is found and correct |
| **explanation** | understand why | the reader can decide something they could not before |

A tutorial holds the reader's hand and may take its time. A how-to is goal-first and does not
teach. A reference is looked up, never read start to finish. An explanation has no steps.

## The rules

| # | Rule | Severity |
|---|---|---|
| D1 | One page is one kind; the kind is stated where a reader can see it. | medium |
| D2 | Prerequisites are stated before the steps, not assumed. | medium |
| D3 | Every how-to ends with a **success check** — how the reader knows it worked. | high |
| D4 | No dead ends: a page that is one step of a longer path links to what comes next. | medium |
| D5 | Terminology comes from the repository's own answers, never invented here. | medium |
| D6 | Voice and tone findings are real but never block: a page ships with them open. | low |

**D6 is the one that separates this rubric from a gate.** A page that is accurate, complete
and followable but reads poorly is a page with a finding, not a page that fails; routing a
voice nit through the same gate as a broken step is how people learn to route around the gate.

## Grading

Each rule is recorded as a finding against the page, with the line it fires on. D3 and D4 gate
the docs step: a how-to with no success check, or a step that strands the reader, is not
complete. D1, D2 and D5 are findings the author fixes in the same pass. D6 is recorded and
left open.

The coverage rule this rubric pairs with — *a capability with a customer surface has a page* —
is computed by the docs validator, never restated here. This rubric grades a page that exists;
it does not decide which pages must.
