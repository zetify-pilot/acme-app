#  Idea — Create

Park an early, exploratory idea as an **idea tracker issue**, filed into
**`intake`** (Intake Queue) — the fleet's front door sweeps it from there into the shaping
interview ([`/fleet:intake`](../intake.md)), then [`/fleet:route`](../route.md), with
any question answered from the Fleet inbox and the verdict (route it, or leave it
parked) given on the Fleet idea page (). It can also resurface a second way,
later: `prd:create` Phase 0.5 surfaces a feature area's remaining open ideas when a PRD
on that ground is scoped. (This is the former capture path of `/fleet:route`, now its
own command. For routing a build-intent request to the right pipeline command, use
[`/fleet:route`](../route.md); for a pure question or research,
.)

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
        "linear-issue"
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
2. **Survey prior art through Fleet.** Call `search_issues` with a query over the idea's
   words and `include_closed: false`. Keep rows whose kind is `idea`. This is a text search
   over Fleet's index — also scan the relevant `knowledge/features/<area>.md` map. **No Fleet
   tools? Stop.** When the session has no Fleet tools, stop with: *this command needs the Fleet tools; create a personal key on Fleet's API keys page*. There is no other survey or filing path — never fall back to a tracker script or a tracker key.
3. **Place it with a body line.** Put `Feature area: <name>` in the body. A feature area is
   durable (covering the whole product, reconciled from ``).
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
### Before you ask a human anything — the interview card

**The person answering has not read the issue, the PRD, the code or any register, and
will not look anything up.** They answer many questions a day from what is in front of
them, and only that. So, every time you ask:

1. **Say what the work is first, in plain words.** One or two sentences on what somebody
   will be able to do that they cannot today. Then **one concrete example** — a named
   person doing it, and what they see. Then **one line on what is undecided**, so the
   question reads as a fork and not a quiz. This goes in the message *before* the first
   question, once per run; later questions inherit it.
2. **Ask with `AskUserQuestion`:** 2–4 options, the one you recommend first and marked
   `(Recommended)`, and on *every* option why it is right and what it costs — not only on
   the one you favour, or the human cannot pick against you.
3. **Every option says what changes for a real person**, not what changes in the code.
   *"The error would read 'this key cannot list agents'"*, not *"return a typed reason from
   the allowlist path."*
4. **No bare ids, no unexplained jargon.** ``, ``, ``, ``,
   `PRD 0242` never appear in an option label, and anywhere else only in parentheses after
   the plain name — *the goal of getting a customer live without an engineer ()*. An
   internal noun (access profile, projection compiler, cause ledger, `blockedBy`) gets half
   a sentence of ordinary English the first time it appears. `file:line` stays, as evidence,
   never as the only statement of the problem.
5. **The test, before you send:** would somebody who has never opened this repo pick the
   same option, for the same reason? If not, rewrite. Being asked to *"explain that again"*
   is a defect in the question, not a preference — re-ask in full, plainer, and hold that
   register for the rest of the run.

6. **A mockup, design or any visual reaches the person ONE way: the fleet's `ask` tool with the mockup attached** (`upload_link` the folder, then `attachments: {bundleId, entry}`). Their browser is on their own machine, not on the box you run on: **never** tell them to open a file path, run `python3 -m http.server` or visit `localhost` / `127.0.0.1`, and never carry a mockup question in the built-in `AskUserQuestion`, which has no attachment. The tool answers with a viewer link; put that link whole in what you say. One authority: `.claude/process/interview.md` → *A mockup reaches a person ONE way*.

7. **The person may not be the one who knows — every question can be answered *"I can't
   answer this"*, and you must plan for that.** The question card carries that choice itself
   (*Can't answer — carry on*); you never add it as an option, and you never invent an answer
   in its place. When it comes back: **carry on with an explicit `Assumption: <what you
   assumed and why>` line, marked unconfirmed by the owner** — or, where the right party is
   the reporter, carry the question to them as an open question — **never ask it again**, and
   list every such item under an **`Unconfirmed assumptions`** heading in what you write, so
   a human can review them later. Downstream, it is an assumption to confirm, not a fact. The
   rule, once: `.claude/process/interview.md` → *"I can't answer this"*.

**Headless — no human attached:** you write all of the above into the escalation instead,
in the same words, so whoever reads it later can answer it as filed.

Full protocol — discovery before forks, acting on the answer, where the decision is
written: `.claude/process/interview.md`.
<!-- /include -->

From here it's the fleet's: `intake` is swept into the interview and route (see
above), and it can still resurface the second way later — `prd:create` Phase 0.5 —
which folds/closes the chosen idea when a PRD on its ground is scoped. No repo file, no
roadmap edit either way.

**If a dispatched run ends on a person's decision** — a fork its brief does not settle — the
park carries the `decision` document, in the card's own fields:

<!-- include: process/decision-document.md -->
### Parking on a person — the `decision` document (headless)

**Every `needs-decision` park writes one `decision` document, and it is the interview card
in fields.** The person clearing `Blocked · decision` reads this card and nothing else —
not the issue, not the PRD, not the register, not your comment thread. The sentinel's
`summary` is only a one-line headline for the park list; everything a person needs to decide
goes here. Write it to `$FLEET_RESULT_FILE` (skip only if that is unset) before the
done-sentinel:

```json
{
  "kind": "decision",
  "brief": {
    "work":    "What somebody will be able to do that they cannot today, in plain words.",
    "example": "One named person doing it, and what they see.",
    "stopped": "What stopped this run, in plain words — the fork, not the log.",
    "stakes":  "What is at stake either way."
  },
  "context": [
    {"ref": "AC-4", "name": "automated comments never reach the customer",
     "quote": "<the criterion's own text, verbatim>", "url": "<optional https link>"}
  ],
  "question": {
    "id": "<short id>",
    "prompt": "The decision, as one question in plain words.",
    "options": [
      {"id": "<short id>", "label": "<what the person picks, no ids>",
       "why": "<why this is right>", "cost": "<what it costs>",
       "then": "<what happens next if picked>", "recommended": true},
      {"id": "…", "label": "…", "why": "…", "cost": "…", "then": "…", "recommended": false}
    ]
  }
}
```

- **Two to four options, the recommended one first** and the only one marked `true`;
  `why`, `cost` and `then` on **every** option.
- **Quote what you cite.** Every acceptance criterion, requirement, issue or PRD the question
  leans on gets a `context` entry whose `quote` is its own text — or, in prose, the plain name
  with the id in parentheses: *the automated-account rule ()*. A bare `AC-4`, ``,
  ``, `PRD 0676`, ``, `PR #123` or `/:…` is refused.
- **Labels carry no ids at all**, and nothing says where the issue was parked — the fleet
  says that, and the person reading is already there.

**Check it before the sentinel** and fix every reason it prints, in this turn:

```bash
python3 knowledge/scripts/validate_decision.py "$FLEET_RESULT_FILE"
```

`0` meets the card; `1` prints every rule broken; `2` means there is no `decision` document at
the path. A park with a missing or refused document still parks — the fleet does not strand a
person's decision over its shape — but the park is recorded as `askRefused` with your reasons,
and that is counted.
<!-- /include -->

## What this is NOT

- Not a PRD, design, plan, or code — the only artifact is the tracker idea-issue.
- Not routing — that's `/fleet:route`.
