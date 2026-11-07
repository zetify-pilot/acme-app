# <!-- home -->Zetify<!-- /home --> Idea — Create

Park an early, exploratory idea as an **idea tracker issue**, filed into
**`intake`** (Intake Queue) — the fleet's front door sweeps it from there into the shaping
interview ([`/zetify:intake`](../intake.md)), then [`/zetify:route`](../route.md), with
any question answered from the Fleet inbox and the verdict (route it, or leave it
parked) given on the Fleet idea page (<!-- home -->2026-09-25<!-- /home -->). It can also resurface a second way,
later: `prd:create` Phase 0.5 surfaces a feature area's remaining open ideas when a PRD
on that ground is scoped. (This is the former capture path of `/zetify:route`, now its
own command. For routing a build-intent request to the right pipeline command, use
[`/zetify:route`](../route.md); for a pure question or research,
<!-- home -->[`/zetify:ask`](../ask.md)<!-- /home -->.)

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. One step, and that is the point: this command records and stops — it never triages, prioritises or places what it files. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "idea-create",
  "tier": "core",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "intent": "Park an early exploratory idea as an idea tracker issue, filed into intake so the fleet's intake/route front door shapes and places it.",
  "loads": ["process-issue-shape"],
  "requires": ["process-spine", "process-issue-shape", "registers-triage-partition", "tracker-identity", "process-interview"],
  "optional": [ "feature-areas", "feature-maps", "components"],
  "steps": [
    {
      "id": "file",
      "name": "File the idea into intake and stop",
      "kind": "io",
      "actor": "coordinator",
      "produces": [
        "tracker-issue"
      ],
      "body": "what-to-do"
    }
  ]
}
```

## Context to load

- [`../../../process/issue-shape.md`](../../../process/issue-shape.md) —
  the canonical create-a-tracker-issue contract.

## What to do

1. **Don't force a PRD.** If the request is promising but early ("idea" / "for
   later" / clearly exploratory), capture it here instead of scoping a PRD now.
   Write the title and the body to the plain-language rule in
   [`process/writing.md`](../../../process/writing.md) → *Write for a reader who does not
   know the code*: say what a person could do that they cannot today, in words they
   understand.
2. **Survey prior art through Fleet.** Call `search_issues` with a query over the idea's
   words and `include_closed: false`. Keep rows whose kind is `idea`. This is a text search
   over Fleet's index — also scan the relevant `knowledge/features/<area>.md` map. **No Fleet
   tools? Stop.** When the session has no Fleet tools, stop with: *this command needs the Fleet tools; create a personal key in Fleet under Settings › Connect your tools*. There is no other survey or filing path — never fall back to a tracker script or a tracker key.
3. **Place it with a body line.** Put `Feature area: <name>` in the body. A feature area is
   durable (covering the whole product, reconciled from <!-- home -->`knowledge/features/*.md`<!-- else -->`slot:feature-maps`<!-- /home -->).
   **Default** the area from the idea's ground **only where it resolves to exactly one
   area**; **otherwise ask the user** which area owns it. **This placement is authored,
   not derived, and deliberately so.** For an idea this is the one question worth spending —
   a mis-filed idea is an idea nobody ever sees again. Write no Component label;
   the checker (or intake route) owns architecture edges.
4. **File through Fleet.** Call `file_issue` with `kind: "idea"`, the title, the body
   (including `Feature area:`), `command: "idea:create"`, and `repo` only when the idea
   concerns another repository. It lands in **`intake`** (Intake Queue) — **never** Backlog
   (nothing dispatches Backlog; 54 of 84 ideas ever filed that way never were). Priority is
   none — ideas aren't prioritized. Print the created issue key and Fleet's message.
5. Keep capture lightweight (at most ~2 targeted `question` calls, the area question
   included).

The one question above is put to a person, so it clears the interview card — the bar a
question has to meet before it is asked:

<!-- include: process/interview-card.md -->

From here it's the fleet's: `intake` is swept into the interview and route (see
above), and it can still resurface the second way later — `prd:create` Phase 0.5 —
which folds/closes the chosen idea when a PRD on its ground is scoped. No repo file, no
roadmap edit either way.

**If a dispatched run ends on a person's decision** — a fork its brief does not settle — the
park carries the `decision` document, in the card's own fields:

<!-- include: process/decision-document.md -->

## What this is NOT

- Not a PRD, design, plan, or code — the only artifact is the tracker idea-issue.
- Not routing — that's `/zetify:route`.
