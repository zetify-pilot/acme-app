# <!-- home -->Zetify<!-- /home --> Mockup — make the design, look at it, then ask

Make a **mockup** for one surface and hand back something a person has already looked at and
approved. One run does the whole loop: pick a reference above the project's own average, build
the round in the project's real parts, **render it headless in every state, critique it against
the bar, fix it**, and only then put it in front of a person.

This is the command that owns the mockup. Other commands call it rather than restating how to
draw: <!-- home -->[`/zetify:prd:design`](prd/design.md), [`/zetify:prd:create`](prd/create.md) and
[`/zetify:page:improve`](page/improve.md)<!-- else -->the PRD design and create steps, and page
improvement<!-- /home -->.

`$ARGUMENTS` — the surface to mock, and optionally its tier (`explore` or `lock`) and where it
belongs. *"the dependencies page, lock tier"*, *"two directions for the queue filter bar"*, or
nothing at all when a caller is invoking this as one step of its own work.

> **The procedure is generic; the project's facts are slots.** Every rule below that could differ
> between projects reads `slot:ui-contracts` and `slot:mockup-conventions`. Nothing here names one
> repository's paths, tokens or browser harness. The full procedure is
> [`process/mockup-loop.md`](../../process/mockup-loop.md); the taste bar it measures against is
> [`process/design-fidelity-loop.md`](../../process/design-fidelity-loop.md) §2.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. `critique` is the loop that makes this command different from drawing a picture — it does not exit until the render clears the bar or the rounds run out. `approve` is a HUMAN gate: nothing is "done" until a person answered. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "mockup",
  "tier": "core",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "intent": "Make a mockup for one surface and hand back one a person has seen and approved: pick a reference, build it in the project's real parts, render and critique it to the bar, then ask.",
  "loads": ["process-design-fidelity", "ui-contracts"],
  "requires": ["process-spine", "process-interview", "process-design-fidelity", "ui-contracts", "languages", "git-workflow"],
  "optional": ["mockup-conventions", "dev-environment", "audit-profile", "file-conventions", "product-vision", "decisions", "gate"],
  "steps": [
    {
      "id": "classify",
      "name": "Decide whether this is a visual question at all, and which tier",
      "kind": "decision",
      "actor": "coordinator",
      "body": "step-1-decide-whether-this-is-a-visual-question"
    },
    {
      "id": "reference",
      "name": "Name the reference above the project's own average",
      "kind": "author",
      "actor": "coordinator",
      "produces": ["reference"],
      "body": "step-2-name-the-reference"
    },
    {
      "id": "explore",
      "name": "Build the round in the project's own parts",
      "kind": "author",
      "actor": "coordinator",
      "produces": ["mockup"],
      "body": "step-3-build-the-round"
    },
    {
      "id": "critique",
      "name": "Render every state, critique, fix, re-render",
      "kind": "loop",
      "actor": "subagent",
      "model": "sonnet",
      "critique": "design-fidelity-bar",
      "loop": {"max_rounds": 3, "exit": "the render clears the bar, or a round fixes nothing"},
      "consumes": ["mockup"],
      "produces": ["screenshots"],
      "body": "step-4-render-critique-and-fix"
    },
    {
      "id": "lock",
      "name": "Promote the chosen round to the product's own components",
      "kind": "io",
      "actor": "coordinator",
      "produces": ["mockup"],
      "body": "step-5-promote-to-the-lock-tier"
    },
    {
      "id": "present",
      "name": "Present it — the person's browser, not your box",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-6-present-it"
    },
    {
      "id": "approve",
      "name": "A HUMAN approves the mockup",
      "kind": "gate",
      "actor": "user",
      "gate": "hard",
      "produces": ["mockup-approved"],
      "body": "step-7-the-human-approval-gate"
    },
    {
      "id": "record",
      "name": "Record what was approved, by file",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-8-record-what-was-approved"
    }
  ]
}
```

## Context to load

- `slot:process-design-fidelity` — the loop this command runs, and the bar it measures against.
  Read [`process/mockup-loop.md`](../../process/mockup-loop.md) first.
- `slot:ui-contracts` — **the single source of the project's design system**: where tokens live,
  how a page is structured, what the components and controls are, how a page is checked, and
  whether this project mounts a page in its own substrate or not.
- `slot:mockup-conventions` — the few facts only this project knows: the mockups directory, the
  tier it can mount, how a state is addressed. **If it is unanswered**, ask the person where the
  files should go (one question, in their words) and stay at the explore tier.
- `slot:dev-environment` — only for the lock tier: how to bring the app up so a real page renders.
- `slot:audit-profile` — the UI checklist `Q1–Q6` the critique uses, where the project has one.

---

## Step 1: Decide whether this is a visual question at all, and which tier

**A question about the UI is not automatically a visual question.** Ask: *would a person
understand this better seeing it than reading it?* A layout, a density decision, a comparison of
two directions: yes. *"Which permission gates this view?"*, *"should this be a field or a
relation?"*: no — those are text-shaped, and a drawn picture makes them slower, not clearer.

**If it is not visual, stop.** Say what you would have mocked and why it does not need one, and
return to the caller. Do not produce a mockup to look thorough; a mockup nobody needed is the
same waste as a question nobody asked.

**Then pick the tier** (`process/mockup-loop.md` → *The two tiers*):

- **explore** — framing the problem, or choosing between directions. Throwaway rounds.
- **lock** — the round a person will approve. Requires `slot:mockup-conventions` to name how the
  project mounts a page, and `slot:dev-environment` to bring the app up. **If the project cannot
  mount one**, this is the case where the explore file *is* the lock: say so plainly, once, and
  carry on at explore tier rather than pretending to a promotion that cannot happen.

A caller may fix the tier <!-- home -->(`/zetify:prd:create`'s rounds are always explore)<!-- else -->where
its own procedure says which tier it needs<!-- /home -->. Respect it.

## Step 2: Name the reference

Before drawing anything, name **at least one real rendered surface of the same archetype**
(list / detail / settings / cockpit) that this design would be proud to be mistaken for, and write
one line on **what about it** is the target: density, rhythm, restraint, hierarchy.

- Prefer an **internal exemplar** — a page in this project that already clears the bar. It is the
  strongest evidence there is, and it costs no third-party screenshot.
- Otherwise a specific page from a product with strong craft, named precisely (*"a tracker's My
  Issues list"*, not *"a tracker"*).
- Where the project commits a reference image, put it at `reference-<archetype>.png` in the round
  directory — the one raster that belongs there (`process/mockup-loop.md` → *What a mockup
  directory contains*).

The reference sets the **ceiling**; the project's own tokens and components supply the **parts**.
Naming a reference is not permission to leave the design system.

## Step 3: Build the round

Use [`process/mockup-loop.md`](../../process/mockup-loop.md) steps 3–5, in this project's
answers:

1. **Read the parts now.** Open the token file, the page structure and the controls
   `slot:ui-contracts` names, and copy what is **actually there today**. Never from memory, from an
   older mockup, or from a command body — a hand-copied token is a frozen snapshot that lies about
   the colours.
2. **Write the files under the mockups directory** `slot:mockup-conventions` names. One
   self-contained `index.html` per round (inline CSS, no CDN, no remote fonts or images) plus
   whatever sits beside it. **Never in a scratchpad**; the committed file is the design contract,
   because every downstream agent runs headless with the repository and nothing else.
3. **Make every state reachable and the flow clickable.** Populated, empty, loading, error, and
   each dialog or sheet — each addressable by `?state=<name>` or its own linked page, wired with
   ordinary `<a href>` elements. No `href="#"`, no dead control.
4. **Match the project's posture** — its light/dark default, its system font stack, its density.
   If the project ships no custom font, the mockup uses none.

For **explore**, build 2–3 genuinely divergent directions as separate rounds. Convergence is the
enemy here: three variations of the same card is one direction drawn three times.

## Step 4: Render, critique, and fix

**This is the step whose absence the whole command exists to close.** Do not skip it, do not
"visualise" it, and do not hand a person anything before it has run.

1. **Render.** Open the mockup in a real browser — the project's browser harness, or a
   <!-- home -->a Playwright/Chromium run<!-- else -->a headless-browser run<!-- /home --> — at **1440×900 in
   every state**, and at phone width where the project
   has one. Capture each state. A render is a delivery mechanism: write it to a scratch location
   and **do not commit it** (`process/mockup-loop.md` → *What a mockup directory contains*).
2. **Critique, ranked and concrete.** Grade the screenshots against, in order: the reference
   (Step 2), the bar (`process/design-fidelity-loop.md` §2 and the `Q1–Q6` checklist where the
   project has one), and this project's own structure and tokens. Emit a **ranked defect list**,
   highest impact first — *"hero card is ~60% empty at 1440"*, *"three type sizes in the header"*,
   *"the primary action is a ghost button lost against the toolbar"*. Never *"make it nicer"*, and
   never a list of ten equal findings: the loop fixes the top one next.
3. **Fix the single highest-impact defect.** Re-render, re-critique. One at a time.
4. **Exit** at `MAX_ROUNDS = 3`, or when a round fixes nothing, or when the critique is clean.
   **Never loosen the bar to exit.** If it will not clear the bar, that is a finding: the design
   is underspecified — say so, and route the remainder as follow-up work rather than shipping
   "good enough".

Delegate the critique to a **subagent that did not write the mockup** where the harness allows it:
an author grading their own drawing sees their intention, not the pixels.

## Step 5: Promote to the lock tier

Applies only when the run is at **lock** tier and the project can mount one.

Rebuild the chosen round in the project's **real substrate** — the real components, real tokens,
real shell — mounted the way `slot:ui-contracts` says this project mounts a page. This is not
ceremony: an HTML mockup cannot be clicked through against a real component's constraints, and its
tokens are a copy that rots.

Then **re-render the lock-tier page in every state** and critique it again. Promotion can change
the design — a real component refuses a shape the hand-drawn one allowed — and the person should
see the promoted page, not the sketch it came from.

## Step 6: Present it

**A mockup reaches a person ONE way: the fleet's `ask` tool with the mockup attached.** Upload the
round folder with `upload_link`, then ask with `attachments: {bundleId, entry}`. One authority:
[`interview.md`](../../process/interview.md) → *A mockup reaches a person ONE way*.

- The person's browser is on **their own machine**. Never tell them to open a file path, run
  `python3 -m http.server`, or visit `localhost` / `127.0.0.1`. A path is not a presentation.
- Never carry a mockup question in the built-in `AskUserQuestion` alone — it has no attachment.
- Name the states the render covers, briefly, so they know what they are looking at.

## Step 7: The human approval gate

**A model's critique is not an approval, and neither is a chat message.** This is a hard gate.

1. **Invite reaction first.** Ask an open question — *"anything off in the layout or shape before
   we lock it?"* — and **wait**. Do not attach a multiple-choice in the same breath: forcing
   options collapses the mockup into background for a decision they never got to challenge.
2. **Iterate on their words** — back to Step 3/Step 4, re-presenting. A round that fixes nothing
   reconfirms rather than re-asks.
3. **Confirm they actually saw it.** If the reply does not reference the mockup, or is a bare
   *"ok"* / *"continue"*, do not infer they saw it. Ask, with the mockup attached, whether it is
   visible.
4. **Collect the approval as an explicit answer**: *"Approve — lock this mockup"* /
   *"Request changes"*. A prose *"yes"* buried in a paragraph does not clear this gate.
5. **Never self-approve.** If no person answers, the command **stops** with the mockup presented
   and the gate **open**. An unapproved mockup is a blocked design, not a design with a caveat.

<!-- include: process/interview-card.md -->

## Step 8: Record what was approved

Where this project records design decisions (`slot:decisions`, or the calling command's own
document — `ux-design.md` under `## Approved design` for a PRD), record:

- which round and **the repo-relative path of the approved file** — not the viewer link, which a
  later headless agent cannot reach;
- the tier it was approved at, and the reference it was measured against;
- the date, and any conditions the person attached.

Then hand back to the caller. This command **does not merge and does not open a PR** on its own;
it returns an approved artifact. A calling command that owns a document writes it.

---

## What this is NOT

- **Not a picture.** A static image of an idea is a sketch; this command produces a rendered,
  clickable, self-critiqued candidate.
- **Not a design review substitute.** The bar catches craft, not intent. A mockup that clears the
  bar can still be the wrong design — that is what the person's answer at Step 7 is for.
- **Not a place to invent a design system.** If the project has no token file or no components,
  that is a `slot:ui-contracts` gap: say so, and mock with what exists rather than inventing a
  second system the product will never match.
- **Not a gate on every field.** A read-only badge on a shipped page is an `additive` change
  (`process/design-fidelity-loop.md` §1.5c): the instrument there is the page-spec, and a mockup
  is optional. Do not charge surface-sized ceremony for a field-sized change.
