# Zetify Page — Improve

Drive a **spec-driven UX improvement** to one web page through to a **green PR handed to the
verify gate** — autonomous by default, and never merged by this session (Step 4). The page's
`<PageName>.spec.md` is the contract: its intent
scopes the work, its _intent → component_ bindings mandate the canonical
canonical catalog components (`slot:ui-contracts`), and the change must leave the page **conformant** (no
hand-rolled or shimmed primitive that has a catalog home).

> To *author the spec* for a page that doesn't have one yet (without changing
> code), use [`/zetify:page:spec`](spec.md) first — or this command will scaffold a
> minimal one inline before improving.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. `classify` branches: a **conformance** change runs straight to `implement` (the page-spec is the standing approval); a **visual** one must pass `mockup-approval` — a HUMAN gate — before any code is written. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "page-improve",
  "intent": "Drive one spec-driven UX improvement to a web page to a green PR, hand it to the verify gate with the page spec as its ledger, and leave the page conformant to the canonical @zetify/ui catalog.",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "loads": ["process-envelope", "process-implementation", "languages", "ui-contracts"],
  "requires": [
    "process-spine", "process-envelope", "process-implementation", "process-interview", "gate", "git-workflow",
    "languages", "ui-contracts", "codegen", "dev-environment",
    "registers-triage-partition"
  ],
  "optional": ["mockup-conventions", "process-design-fidelity", "audit-profile", "file-conventions", "tracker-identity", "docs"],
  "steps": [
    {"id": "continue-or-branch", "name": "Continue an existing PR, else branch",     "kind": "decision", "actor": "coordinator",                                     "body": "continue-an-existing-pr"},
    {"id": "mode-select",     "name": "Select mode (autonomous / manual)",           "kind": "decision", "actor": "coordinator",                                     "body": "modes"},
    {"id": "load-contract",   "name": "Load the page contract, scaffolding one if absent", "kind": "author", "actor": "coordinator", "produces": ["page-spec"],      "body": "step-1-load-the-page-contract"},
    {"id": "bind-canonical",  "name": "Bind every UI pattern to its canonical component", "kind": "gate", "actor": "coordinator", "gate": "hard",                    "body": "step-2-bind-every-ui-pattern"},
    {"id": "classify",        "name": "Classify the change — conformance vs. visual", "kind": "decision", "actor": "coordinator",                                    "body": "step-2b-classify-the-change"},
    {"id": "mockup",          "name": "Visual change — build it as a real-UI mockup", "kind": "author",   "actor": "coordinator", "produces": ["mockup"],             "body": "step-2b-classify-the-change"},
    {"id": "mockup-approval", "name": "Visual change — a HUMAN reacts to before/after at 1440", "kind": "gate", "actor": "user", "gate": "hard", "produces": ["mockup-approved"], "body": "step-2b-classify-the-change"},
    {"id": "implement",       "name": "Implement, re-sync the spec, regenerate",     "kind": "io",       "actor": "coordinator", "produces": ["page-spec"],          "body": "step-3-implement-then-re-sync-the-contract"},
    {"id": "browser-pass",    "name": "Verify in the browser — a UX change is not done unseen", "kind": "gate", "actor": "coordinator", "gate": "hard", "produces": ["screenshots"], "body": "step-3-implement-then-re-sync-the-contract"},
    {"id": "fidelity-loop",   "name": "Design-fidelity build loop against the approved mockup", "kind": "loop", "actor": "coordinator", "critique": "design-fidelity-bar", "loop": {"max_rounds": 4, "exit": "surface clears the approved mockup, then the bar"}, "consumes": ["mockup-approved"], "produces": ["screenshots"], "body": "step-3-implement-then-re-sync-the-contract"},
    {"id": "handoff",         "name": "Green PR, then hand off to verify — spec as ledger", "kind": "io",   "actor": "coordinator",                                     "body": "step-4-open-a-green-pr-then-hand-off-you-do-not-merge-it"}
  ]
}
```

---

## Context to load

- [`../../../process/autonomous-drive.md`](../../../process/autonomous-drive.md) — **load and obey Rules A–G** and the flow-retro. The autonomous execute envelope. **Its `/zetify:push ship` terminal is not yours**: this command's terminal is the handoff (Step 4).
- [`../../../../knowledge/specs/frontend-implementation-contract.md`](../../../../knowledge/specs/frontend-implementation-contract.md) and [`../../../../knowledge/specs/ui-spec.md`](../../../../knowledge/specs/ui-spec.md) — design-system, i18n chain, page archetypes, canonical component rules.
- [`../../../process/implementation.md`](../../../process/implementation.md) — the implement/verify loop (browser pass for UI).
- `slot:ui-contracts` — the canonical catalog's index. **Each leaf's "Used on these pages" section is how you find consistency precedent.**

---

## Continue an existing PR — never open a second one, and settle the subject first

`$ARGUMENTS` names **a page**, and it may also name **a tracker issue key**. Which of the two
you were given decides how Step 4 ends, so settle it here, in one line, before any code is
written:

| You were given | The subject is | Step 4's terminal |
|---|---|---|
| a page **and** an issue key (the fleet released that issue, or a person handed you one) | that issue — it has already been through [`/zetify:check`](../check.md) and carries a priority, a `Component` and a project | **move it to the review state** `slot:registers-triage-partition` names (`slot:tracker-identity`) |
| a page only | **nobody but the person who ran this command** | **hand them the PR** — the link, the spec path, and what to do with it |

**There is no third branch, and in particular this command never files an issue for itself.**
A freshly-filed issue is born in the check-gate state with no priority, and a filer that then
moved it onward would drop it outside the only window the partition guard tolerates a missing
priority in — a **blocking** violation that reds every open PR in the repository. Filing is
[`/zetify:task:create`](../task/create.md)'s job and triage is the checker's; this command
does neither.

Then check whether this page/issue already has an open PR
(`gh pr list --search "<page or KEY>" --state open`). If so, continue on that
branch — never open a second PR for the same work.

---

## Modes

- **Autonomous (default)** — load the spec → improve → verify in the browser → green PR → hand off to the gate.
- **`--manual`** — produce the plan (spec delta + component plan) and **stop**.

---

## Step 1: Load the page contract

1. Resolve `$ARGUMENTS` to a page (a page file where `slot:ui-contracts` says pages live).
2. Read its `<Name>.spec.md`. **If none exists**, scaffold a minimal spec first
   (the [`/zetify:page:spec`](spec.md) shape) so the work is anchored to stated
   intent — don't improve a page blind.
3. Read the page's current **Shared-component conformance** block. Any listed
   violation (a primitive reached via a local re-export shim) is in scope to fix
   as you touch those lines.

---

## Step 2: Bind every UI pattern to its canonical component (the core rule)

For each piece of UI the improvement touches — a list, tabs, a dialog, status
words, counters, an empty/error/loading state:

1. **Find the canonical home.** If the pattern has an catalog leaf, it
   is **mandatory** — never hand-roll an equivalent (no raw `<table>`, no
   `<div role="tablist">`, no hand-colored `Badge`), and never reach it through a
   local re-export shim. Import from the catalog directly.
2. **Consult precedent for consistency.** Open the leaf's **"Used on these pages"**
   list and read 1–2 of those pages. Match the established treatment (variant,
   density, count-suffix convention, drill-in affordance) rather than inventing a
   parallel one. This is the whole point of the reverse-index — use it.
3. If a genuinely new shared pattern is needed (no leaf fits), surface it: propose
   promoting it into the catalog with a sidecar, don't bury a bespoke
   component in the page.

---

## Step 2b: Classify the change — conformance vs. visual

Before writing code, decide which kind of change this is. The two have different
approval requirements, and conflating them is how autonomous UX work ships surfaces
nobody chose.

| Kind | What it is | Approval |
|---|---|---|
| **Conformance** | swap a hand-rolled or shimmed primitive for its canonical catalog equivalent; fix a listed conformance violation; no change to layout, density, or hierarchy. | **None needed — the page-spec is the standing approval.** Proceed autonomously. |
| **Visual** | changes layout, density, information hierarchy, what's on the page, or any **UX decision** recorded in the spec. | **Mock it and get it approved first** (below). |

**A visual change gets the same treatment as a PRD surface**, at page scale
([`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §1.5):

1. **Call [`/zetify:mockup`](../mockup.md) at lock tier.** The page already exists, so the
   mockup is the *proposed* page rendered in the project's own substrate — a dev-only fixture
   route beside the current one, or a screenshot of a local branch — and explore-tier HTML is
   not sufficient for a page that already ships. The command picks the reference, **renders and
   critiques the proposer to the bar**, and brings it to the person; it does not restate those
   rules here ([`process/mockup-loop.md`](../../../process/mockup-loop.md)).
2. **Then present before/after at 1440 and wait for a reaction** — the command's own approval
   step, and the open question comes first: say what changed for the person using the page, in
   plain words, before asking what they think. No multiple-choice in the same message (§1.5b).

<!-- include: process/interview-card.md -->
3. Record the approval in the page's `<Name>.spec.md` under `UX decisions`, naming the
   **repo-relative path** of the fixture route / mockup file — never a hosted artifact
   URL ([`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md)
   §1.5-0). Publishing a hosted copy is the right way to get it in front of the human in
   step 2; it is never the thing the record points at, because the agent that later
   implements or verifies against that record has the repo and nothing else.

**Autonomous mode does not exempt this gate — it bounds it.** Under
[`autonomous-drive.md`](../../../process/autonomous-drive.md) Rule A you
never stop to ask about *implementation* judgment calls; but a visual change with no
approved design is not a judgment call the command owns. If a visual change is needed
and no human is available, **stop and park it in `Blocked · decision`**, or narrow the work to
the conformance half and file the visual half as a follow-up. Do not self-approve a
new look. A page whose appearance changed because an agent thought it looked better is
exactly the outcome this command must not produce.

If the change turns out to be net-new capability or a major workflow, it is PRD-shaped
— stop and route to [`/zetify:prd:create`](../prd/create.md).

---

## Step 3: Implement, then re-sync the contract

1. Make the change. Honor the spec's **UX decisions (do not silently regress)** —
   if the improvement deliberately changes one, update that decision (with the
   reason + date) in the same commit; never silently flip it.
2. Update the spec's authored intent (Layout / Canonical-choice rules / UX
   decisions) to match the new reality — the spec ships **with** the code.
3. Run **`{{target:generate-page-specs}}`**. The page's conformance block must end **✓**
   for the primitives it composes (or the PR explicitly justifies residual drift
   slated for a follow-up). The reverse-index refreshes automatically.
4. **Verify in the browser** (per [`implementation.md`](../../../process/implementation.md) — Playwright/real
   app, not just unit tests). A UX change is not done until you've seen it render.
5. **For a visual change, run the design-fidelity build loop**
   ([`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md)
   §3, `MAX_LOOP = 4`): render at 1440 in every state, critique against **the approved
   mockup first**, then the bar, fix the single highest-impact defect, re-render.
   Never loosen the bar to exit; a surface that can't clear it in four rounds means the
   approved design under-specified it — track the residual, don't ship it silently.
6. **Reconcile the page's how-to (`slot:docs`).** When the spec links a user-facing page
   (its how-to), a change to a step's wording, a control's label, a screenshot or an order
   makes that page stale. Update the page in the **same change** so the how-to still matches
   what the product does; a page that tells a customer to click something that is not there
   is a defect, not a docs nicety. When the repository leaves `slot:docs` unfilled there is
   no home to reconcile — say so in the PR body and move on.

---

## Step 4: Open a green PR, then hand off — you do not merge it

Drive to a **green PR** under [`autonomous-drive.md`](../../../process/autonomous-drive.md)
Rules A–G — branch the deterministic branch `slot:git-workflow` names (UX polish without a PRD
is task-shaped), green CI, and then **stop**. Never `/zetify:push ship`. How the PR is opened
depends on the subject below: an issue-keyed run goes through `/zetify:push` (open-PR-and-stop);
a page-only run opens the PR the way [`/zetify:sidekick`](../sidekick.md) does — ready, not draft,
and **not armed**. Log any out-of-scope follow-ups (Rule G →
[`/zetify:task:create`](../task/create.md)).

**🛑 THIS COMMAND DOES NOT MERGE ITS OWN WORK.** It used to — `/zetify:push ship`, green CI,
done, with no session between the author and `main`. A UX change is the *easiest* kind to
self-certify, because the author is the one person who has already decided the surface looks
right; the browser pass in Step 3 is this run's own reading of its own screenshots, and the law
the whole fleet runs on is that the party that wrote the code never certifies it. It had no
exception written into it for pages, and it does not get one now.

**The page's own spec IS the ledger.** What a verifier grades against is
**`<PageName>.spec.md` at the PR head**: its authored intent, its UX decisions, and its
intent→canonical-component bindings are the claims this change asserts, one line at a time,
exactly as a cause ledger's lines are. So the spec has to be **true of the merged code before
you hand off** — Step 3.2 is not bookkeeping, it is the writing of the thing you are about to
be graded on. A spec left describing the old surface is a ledger of claims the verifier will
find open, and the PR comes back to you in the rework state.

**How you open the PR and hand off depends on which subject you resolved at the start**, and
both endings are real ones — what neither of them is, is walking away from a green PR nobody
owns:

1. **You were given an issue key.** Open via `/zetify:push` (open-PR-and-stop — it arms at
   open; the required fix-gate check fails closed on this key until an independent
   [`/zetify:verify`](../verify.md) passes, so the arm cannot merge). Then move that issue to
   the review state `slot:registers-triage-partition` names (`slot:tracker-identity`). That
   state move is the handoff: the fleet dispatches a fresh verifying session at it. The issue
   came through the checker, so it already carries the priority that state requires — you set
   none, and you move nothing else.
2. **You were given a page only, so the person who ran this command is the owner.** You have
   no issue to move and you do not create one. **Open the PR. Do not arm it, and do not merge
   it — hand them the link.** `main` is branch-protected (`slot:git-workflow`), so there is no
   direct push; open a ready (not draft) PR, let CI run, and then give them the URL, the head
   SHA, `<PageName>.spec.md` as the ledger to grade it against, the before/after screenshots,
   and one plain sentence — *nothing is armed; this needs a second pair of eyes before it
   merges.* They merge it. `python3 knowledge/scripts/gh_automerge_arm.py` is **not** this
   path's to call: case 2 carries no tracker issue key, so Verify Gate passes the PR as
   not-lane-work and an armed one would merge on green CI with no verifier (the same shape
   the sidekick no-arm ruling closed — ENG-10786 / ENG-10790). They are attached to this run
   by definition (the mockup gate in Step 2b is theirs), so handing it to them is a handoff
   to a person, not an abandonment.

Either way, name the spec file and the PR head SHA, so the verifier — an agent or a human —
grades the contract this change actually shipped rather than whichever revision it reads later.

---

## What this is NOT

- Not a way to hand-roll UI — if a primitive has a catalog leaf, you **must** use it.
- Not spec authoring from scratch — that's [`/zetify:page:spec`](spec.md).
- Not for net-new capabilities or major workflows — those are PRD-shaped (`/zetify:prd:create`).
