# <!-- home -->Zetify<!-- /home --> Ask

The light front door. Use this when you have a **question**, want to **research**
something, or **don't yet know** whether what you're describing is a feature, a
bug, or just a thing to understand. It answers and investigates — it does **not**
load the heavy pipeline contracts, and it does **not** write code, PRDs, or
plans. When the answer turns out to be real work, it points you at the command
that does it.

This is the deliberately-minimal entry: a question or research session should
stay cheap. The repository's own instructions file already orients you to the repo — this command needs no
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
| Clearly a defect ("X is broken", a stack trace, a failing test) | **Bug** | Don't debug-and-patch here. Briefly confirm it looks like a bug, then route to `/zetify:bug:fix`. |

If the input is ambiguous, ask **one** clarifying question before answering — don't
guess at a heavy interpretation. Write the question to the plain-language rule in
[`process/writing.md`](../../process/writing.md) → *Write for a reader who does not know
the code*: no PRD or issue id, no "slice", "lane" or "dispatch", no file path, check name or
run id in the question; put an id a person needs on its own references line at the end.
Shaped by the interview card:

<!-- include: process/interview-card.md -->

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
| A promising idea worth parking (not ready to build) | `/zetify:idea:create <desc>` — parks it as the tracker idea-issue in its feature area's tracker project |
| Something to build (any size) | `/zetify:route <desc>` — routes to program (`program:decompose`) / `slice:create` / `prd:create` / `component:create` / task / bug / idea |
| A bug | `/zetify:bug:fix <desc>` — TDD-first reproduce → root-cause fix → green |
| A small scoped task (chore/refactor, no PRD) | `/zetify:task:implement <desc>` |
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
  rationale · consequences.<!-- home --> It joins the ADR index (`knowledge/adr-index.md`), rendered on demand with `python3 knowledge/scripts/gen_decision_ledger.py` (gitignored, so never stale).<!-- /home -->
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

Confirm the decision with the user before writing.<!-- home --> Then run
`python3 knowledge/scripts/gen_decision_ledger.py` so the ADR index stays in sync.<!-- /home -->

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
