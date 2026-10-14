#  Ask

The light front door. Use this when you have a **question**, want to **research**
something, or **don't yet know** whether what you're describing is a feature, a
bug, or just a thing to understand. It answers and investigates — it does **not**
load the heavy pipeline contracts, and it does **not** write code, PRDs, or
plans. When the answer turns out to be real work, it points you at the command
that does it.

This is the deliberately-minimal entry: a question or research session should
stay cheap. `CLAUDE.md` already orients you to the repo — this command needs no
further heavy context up front.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. This command **writes no code, PRD or plan** — `escalate` names the command that would, and stops. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "ask",
  "tier": "core",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "intent": "Answer a question or investigate something without loading the pipeline contracts \u2014 and, when the answer turns out to be real work, name the command that does it rather than starting it.",
  "loads": [],
  "requires": ["process-spine"],
  "optional": [
    "process-interview", "entity-model", "product-vision", "decisions", "commitments", "planning-model", "dev-environment", "docs"
  ],
  "steps": [
    {
      "id": "classify",
      "name": "Classify the intent",
      "kind": "decision",
      "actor": "coordinator",
      "body": "step-1-classify-the-intent"
    },
    {
      "id": "answer",
      "name": "Answer or investigate",
      "kind": "author",
      "actor": "coordinator",
      "body": "step-2-answer-or-investigate"
    },
    {
      "id": "escalate",
      "name": "Escalate if it is actually work",
      "kind": "decision",
      "actor": "coordinator",
      "body": "step-3-escalate"
    },
    {
      "id": "capture-decision",
      "name": "Capture a decision, if one was made",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-3-5-capture-a-decision"
    }
  ]
}
```

## What NOT to load

**Do not pre-load the implementation/design/planning specs** (the
`*-implementation-contract.md`, [`implementation.md`](../../process/implementation.md), `ui-spec.md`,
`api-design-guide.md`, etc.). They're for the doing-commands. If the question is
about the codebase, read the *relevant source files* on demand; if it's about
product direction, you may skim the product vision (`slot:product-vision`). Nothing
else by default.

---

## Step 1: Classify the intent

Read the user's input: $ARGUMENTS

Decide which kind of session this is — it determines how you answer and where
(if anywhere) you hand off:

| Signal | Kind | How to handle |
|---|---|---|
| "how does X work", "where is Y", "why does Z" | **Codebase question** | Read the relevant source on demand and answer with `file:line` references. No specs, no strategy docs. |
| "how do I…", "where do I click to…" — a user asking how to **use** the product | **How-to question** | Answer from the page the `docs` slot names (`slot:docs`), not from the code: the user-facing page is the product's own answer. A page that disagrees with the product is a **docs defect** — route it (Step 3), don't paper over it here. When the slot is unfilled, say the docs home is unknown (the slot's degrade) and answer from the code with a caveat. |
| "what's the best way to…", "compare…", "what do others do for…" | **Research** | Investigate. For a deep, multi-source, fact-checked answer, hand off to the `deep-research` skill. For a quick one, answer directly with sources. |
| "should we…", "is X worth doing", "I have an idea but…" | **Exploration / unsure** | Discuss it against the product vision (`slot:product-vision`). Do **not** start the pipeline — at the end, recommend the right command (see Step 3) if it's worth pursuing. |
| Clearly a defect ("X is broken", a stack trace, a failing test) | **Bug** | Don't debug-and-patch here. Briefly confirm it looks like a bug, then route to `/fleet:bug:fix`. |

If the input is ambiguous, ask **one** clarifying question before answering — don't
guess at a heavy interpretation. Shaped by the interview card:

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

---

## Step 2: Answer or investigate

- **Codebase questions:** locate and read the relevant files, then answer
  concretely with `file:line` pointers. Prefer the dev logs in `logs/` for
  runtime behaviour over speculation.
- **How-to questions:** read the page the `docs` slot names and answer with it — quote the
  step and the page id. If the page and the product disagree, that is a finding: answer from
  the product and recommend the docs fix in Step 3.
- **Research:** if it warrants depth, invoke the `deep-research` skill with the
  refined question; otherwise answer directly and cite sources.
- **Exploration:** think with the user. Frame the idea against the product
  vision (persona, core loop step, differentiation) honestly — including "this
  doesn't seem to fit, here's why."

Stay read-only. This command never edits files, never writes a PRD/design/plan,
and never flips a status — the one sanctioned write is the optional decision record
(Step 3.5), and only for a genuine decision the user confirms.

---

## Step 3: Escalate if it's actually work

If the conversation concludes that this is real work, **don't do it here** —
recommend the next command and stop:

| It turns out to be… | Recommend |
|---|---|
| A promising idea worth parking (not ready to build) | `/fleet:idea:create <desc>` — parks it as the tracker idea-issue in its feature area's tracker project |
| Something to build (any size) | `/fleet:route <desc>` — routes to program (`program:decompose`) / `slice:create` / `prd:create` / `component:create` / task / bug / idea |
| A bug | `/fleet:bug:fix <desc>` — TDD-first reproduce → root-cause fix → green |
| A small scoped task (chore/refactor, no PRD) | `/fleet:task:implement <desc>` |
| Just an answer | Nothing — you're done. |

Keep the handoff to one line: what you found, and the single command to run next.

---

## Step 3.5: Capture a decision (if one was made)

If the discussion reached a **load-bearing decision** — one that changes a direction,
rules an approach in or out, or that a future reader will ask "why did we go this way?"
about — record it before ending. This is the **one** thing this command may write, and
only for a real decision (skip it for ordinary Q&A):

- **Owned by a PRD/slice?** Put it where that work lives — the PRD's `design.md`
  `## Architecture notes`, or a comment on the tracker issue. Don't duplicate it here.
- **Not owned by any PRD** (a discussion / ops / standards call)? Capture a standalone
  record where `slot:decisions` says, from its template: context · options · decision ·
  rationale · consequences.
- **If that decision moves a commitment, the register rows move in the SAME change.** A
  decision that adopts a new *"the system shall / never"*, fixes a number, or knowingly
  accepts a cost adds a row citing this record as its `Source`; a decision that **replaces a
  mechanism** supersedes the rows describing the old one — with the closure that entails
  (the dead row's own `Needs` cleared, every edge pointing at it re-derived, every claiming
  PRD re-pointed), owned by
  the entity model (`slot:entity-model`) → *Decisions and requirements* and not restated
  here; the rows are the `slot:commitments` register's. Skipping it is how this corpus got its worst rot: a
  decision replaced its predecessor, nothing carried the change into the rows, and they went
  on describing a mechanism we had already dropped. Name the IDs under the record's
  **Commitments** line, so the record and the rows read as one change.

Confirm the decision with the user before writing.

---

## Rules

- **Read-only.** No code, no PRDs, no plans, no status flips, no commits. The *one*
  exception is the optional decision record in Step 3.5 (a genuine, user-confirmed decision)
  **and the requirement rows that decision moves** — those are one change with the record,
  not a second write.
- **Stay light.** Don't pull in the pipeline contracts; read source/strategy
  only as the question demands.
- **Be concise.** A question deserves an answer, not a project plan.
- **Hand off, don't do.** When it's work, name the one command — don't start it.
