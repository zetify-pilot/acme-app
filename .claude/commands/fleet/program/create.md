#  Program Author

You create or update a **program** — the top tier of the planning hierarchy. **A program is either a result someone gets (`kind: outcome`) or a body of platform work that lands (`kind: program`)**; the definition and its tests live in [`knowledge-model.md`](#). It groups **slices** (`/fleet:slice:create`), which in turn group **PRDs** (`/fleet:prd:create`), and it carries the output of `/fleet:program:decompose`.

```
Program  (this command)                              →  a row fragment in the `slot:programs` register (PG-NN)  →  a tracker label
  └─ Slice (a planning cut — /fleet:slice:create)   →  a row fragment in the `slot:slices` register (SL-NNN)   →  a tracker label
       └─ PRD (an agent-shift — /fleet:prd:create)  →  knowledge/prds/NNNN         →  tracker issue
```

**A program is a register row plus, where there is prose to write, a detail file.** Every
structural field — name, kind, proof, theme, target, the decomposition's roots — is a column
in ``; the narrative lives in `knowledge/programs/PG-NN.md`, whose
filename *is* the join. Nothing structural may be restated there: the tracking validator
rejects any frontmatter key but `type:`, so a column cannot acquire a second, unread copy.

## The gate — run the ladder before you write anything

**Read [`knowledge-model.md`](#) and walk its ladder first-match-wins. Apply the Program entity's tests from that spec verbatim — they are not restated here.** This command is correct **only** when the ladder lands on **program**. If it lands anywhere else, write nothing and hand back to `/fleet:route`, which owns rung→command routing. **From a brief this gate closes as *not this mode***: route walked the ladder, wrote the rung into the proposal, and a person accepted it — the placement is theirs, and a hand-back is a terminal move this path has nowhere to make.

**Never author a container program** — a release bucket, a holding tier, an arbitrary grouping. A grouping whose completion condition is nothing more than the union of its children's is a **theme**, and a theme is a word you use in prose — never a tier, never a row, and (since ) not a cell either. **`kind: program` is not the loophole for this**: it exists so technical work can be *named* honestly ("Apps And Connectors Run As Real Containers"), not so a bucket can be given a bar.

Then read [`tracking-and-execution.md`](#) for the mechanics you will write: the register's columns and tracker sync.

**Two ways in, told apart by one variable (Step 0).** At a terminal this frames a program in
one short round and writes its row and its narrative. **When `$FLEET_RESULT_FILE` is set** the
fleet dispatched you on an idea a person has had shaped by [`intake`](../intake.md), placed
by [`route`](../route.md) at the program rung and **accepted**: the brief carries the dossier
and the proposal, nobody is at a terminal, and you write **the one register row** from those
two documents' own words — by PR, with a `created` result file — and nothing else. The
narrative, the proof and the decomposition are the program page's to ask for next.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. No step writes a `status:` or a date, and none may be added that does — a program's ship-state is derived from its slices. Steps named `From the brief:` belong to the fleet path; Step 0 decides the mode, and the other mode's steps are closed as *not this mode* at that moment — `check-exists` runs in both. The prose steps below are the authority; this spine indexes them.
>
> **`needs: answers` · `may merge: true`** ([`spine.md`](../../../process/spine.md)) — the fleet dispatches this command on an accepted proposal, and *that* run asks nothing; the terminal path frames and asks, and carries the card. The terminal path still frames and asks; `$FLEET_RESULT_FILE` is what keeps the two apart.

```json
{
  "command": "program-create",
  "tier": "core",
  "sop": "none",
  "needs": "answers",
  "may merge": true,
  "intent": "Author one program row \u2014 a company-scale objective in plain language \u2014 with no status and no dates, because a program's ship-state is computed and never written; from an accepted proposal on the fleet, the row and nothing else.",
  "loads": ["programs", "entity-model", "planning-model"],
  "requires": [
    "process-spine", "programs", "entity-model", "gate", "git-workflow", "file-conventions"
  ],
  "optional": ["process-interview", "product-vision", "planning-model", "slices"],
  "steps": [
    {
      "id": "mode",
      "name": "Which way in \u2014 a terminal, or the fleet with a brief",
      "kind": "decision",
      "actor": "coordinator",
      "body": "step-0-which-way-in"
    },
    {
      "id": "ladder-gate",
      "name": "Run the ladder before writing anything",
      "kind": "gate",
      "actor": "coordinator",
      "gate": "hard",
      "body": "the-gate-run-the-ladder"
    },
    {
      "id": "check-exists",
      "name": "Check what exists",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-1-check-what-exists"
    },
    {
      "id": "frame",
      "name": "Frame it (one short round if anything is unclear)",
      "kind": "decision",
      "actor": "coordinator",
      "body": "step-2-frame-it"
    },
    {
      "id": "plain-language",
      "name": "Write it in plain language \u2014 the title and the headline",
      "kind": "author",
      "actor": "coordinator",
      "body": "step-2b-write-it-in-plain-language"
    },
    {
      "id": "create-row-fragment",
      "name": "Create the row fragment",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-3-create-the-row-fragment"
    },
    {
      "id": "narrative",
      "name": "Write the narrative into the detail file",
      "kind": "author",
      "actor": "coordinator",
      "body": "step-3b-write-the-narrative"
    },
    {
      "id": "linear",
      "name": "Tracker \u2014 no live mirror, the fleet projects it",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-4-tracker-no-live-mirror-the-fleet-projects-it"
    },
    {
      "id": "confirm",
      "name": "Confirm",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-5-confirm"
    },
    {
      "id": "brief-values",
      "name": "From the brief: the row's values, from the dossier's and the proposal's own words",
      "kind": "author",
      "actor": "coordinator",
      "body": "the-values-and-only-these"
    },
    {
      "id": "brief-row",
      "name": "From the brief: create the row fragment, and nothing else",
      "kind": "io",
      "actor": "coordinator",
      "body": "the-row-by-pr"
    },
    {
      "id": "brief-merged",
      "name": "From the brief: the PR is green, auto-merge fired, the id survived the push",
      "kind": "gate",
      "actor": "coordinator",
      "gate": "hard",
      "body": "the-row-by-pr"
    },
    {
      "id": "brief-created",
      "name": "From the brief: emit the created result, then the done-sentinel",
      "kind": "io",
      "actor": "coordinator",
      "body": "the-created-result-then-the-sentinel"
    }
  ]
}
```

## What to do

### Step 0: Which way in, and what the brief must carry

```bash
printf '%s\n' "${FLEET_RESULT_FILE:-<unset>}"
```

- **Unset** → a person is at the terminal and `$ARGUMENTS` is their words. Run the gate and
  Steps 1–5; the `From the brief:` steps close as *not this mode*.
- **Set** → the fleet dispatched you. `$ARGUMENTS` is the issue key naming this work, and the
  brief must carry, under their own headings, the **dossier** and a **proposal whose `kind` is
  `program`**. Run Step 1, then Step 6; the gate and Steps 2–5 close as *not this mode* — the
  rung is route's and the person accepted it. **You read no tracker and ask no question** —
  the brief is everything you are given.
- **Set, and the brief carries an instruction** — the person sent the idea back at this stage,
  usually answering the refusal in Step 1 (*it is its own program*). It is the newest thing in
  the brief: take it as given, and let it settle what it settles.
- **Set, but no proposal in the brief, or a proposal for another kind** → a mis-dispatch.
  Write nothing in the repo; write the sentinel with `status: "failed"` naming what was
  missing, and stop.

### Step 1: Check what exists

Read the program row fragments under `knowledge/programs/rows/` — one file per program, named for its `PG-NN` id (the table `` is generated from them). If the user's intent matches an existing program, **edit that row's fragment** (and its detail file, if it has one) instead of creating a new one. Only create a fragment if no existing program covers it.

**From a brief, a match is a refusal, not an edit.** Route's `alsoWeighed` already argued the
existing programs away and a person accepted that; if a row nonetheless covers this idea in so
many words, editing it from a brief would change a program nobody put in front of that person.
Write nothing — no row, no branch, no result file; write the sentinel with `status:
"needs-decision"`, `pr: ""`, and a summary naming the row and **the move that releases it**,
which is never *route again* (nothing on the page re-routes an accepted idea; a send-back
re-runs this command): *"this reads as a second name for <the program> (PG-NN) — withdraw it
as already filed, or send it back saying it is its own program, and this run repeats"*. A
brief carrying that instruction (Step 0) is the answer, and the run goes on. No result kind
carries a refusal — the closed set and why it stays closed are [`intake`](../intake.md) §8.

**The refusal is a `Blocked · decision` park, so it carries the `decision` document** — the
row it reads as (by name and id) and the choice the person has (withdraw it as already filed,
or send it back saying it is its own program), in the card's own fields:

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

### Step 2: Frame it (one short round if anything is unclear)

The user's input is: $ARGUMENTS

A program needs only a handful of decisions — be opinionated and converge fast:

1. **Kind** — `outcome` or `program`. *outcome*: named for the result someone gets (*"A Customer's Own Engineer Ships An App"*). *program*: named for the thing that lands (*"Apps And Connectors Run As Real Containers"*). Pick the one that matches how the work is actually discussed; forcing platform work into outcome-voice is what made technical programmes unnameable.
2. **`Name`** — short (≤ ~45 chars), and **literal**. See "Write it in plain language" below: the title is the only thing most readers ever see, so it has to say what the thing *is*, not evoke it.
3. **Who it's for, and the job** — the person in a circumstance, as a job story: *When `<situation>`, I want to `<motivation>`, so I can `<outcome>`.*
4. **The day it becomes true** — the observable event that settles it.
5. **The problem today** — one concrete story of the status quo failing, from their side.
6. **`Verified by`** — the e2e proof PRD(s). **REQUIRED on `kind: program`, and the proof must drive a surface a customer touches** (Step 3). Normally authored by `/fleet:program:decompose`, which is where choosing the proof belongs; if you already know it, write it.
**Not on the list, and never authored here: a status.** A program is complete when every one of its slices is **and** its own proof has shipped — arithmetic over the slices, computed on read, stored nowhere. The register has no `Status` column and the validator rejects one being added. See Step 3.

**Also not on the list: a date, and a theme.** The register carried `Target` and `Theme` columns until  and both were deleted. `Target` was filled twelve times and every cell said `2026-Q4` — a column that cannot tell two programs apart reads like a commitment while carrying no information; if a real external date exists, argue it in the program's detail file (`knowledge/programs/PG-NN.md`), named and sourced. `Theme` was authored once in eight cells, rendered by nothing, and validated only for kebab-case shape. **A theme is still the right classification** when a grouping adds no completion condition its children lack — it just means the grouping is *not an entity*, so you write no row and no cell for it.

**The column list is exact — six cells, no more: `ID`, `Name`, `Kind`, `Verified by`, `Requires`, `Disposition`.** There is no owner, no date, no theme, no slice list; a field you feel is missing is one the model deliberately does not store, so raise it rather than widening the table.

If all of these are obvious from the request, skip the interview and write the row. If one material decision is genuinely open (e.g. is this really program-grade, or a slice?), ask **one** question, shaped by the interview card:

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

### Step 2b: Write it in plain language — the title and the headline

**This section is the voice rule for every program artifact, and the other four program
commands — `decompose`, `prove`, `ship`, `deliver` — cite it rather than restating it.** It exists because the
corpus drifted: on  all 21 program titles and headlines were rewritten because the
owner could not tell from the board what several of his own programs *were*. Titles had
become evocative rather than descriptive — *"The Star Map Stays True On Its Own"*,
*"Containment Survives Their Review"*, *"Stopped Early, And Told Why"* — and not one
headline contained a concrete example, because the rule below used to say "zero mechanism"
and authors read that as "no specifics at all".

**The title is literal.** A reader who has never seen this codebase reads the title alone and
can say what the thing is. Apply both tests:

- **Say it back test.** Could a new hire, having read only the title, paraphrase what the
  program delivers? *"The Star Map Stays True On Its Own"* — no. *"The Business Model Keeps
  Itself Current"* — yes.
- **Metaphor test.** Does any word stand in for the real subject? *Star map*, *room*,
  *colleague*, *survives*, *holds up*, *holds at real scale* — each is a figure of speech doing
  the work a noun should do. Name the subject.

| Instead of | Write |
|---|---|
| The Star Map Stays True On Its Own | The Business Model Keeps Itself Current |
| Containment Survives Their Review | A Security Reviewer Can Check Our Isolation |
| Everyone Lands In Their Own Room |  Splits Into Four Named Places |
| Stopped Early, And Told Why | A Runaway Integration Is Blocked In Seconds |
| Agents Are Colleagues, Not Tools | An Agent Answers In Slack Under Its Own Name |
| Apps That Hold At Real Scale | An App Says When It Couldn't Read Everything |

**The headline must fit in 240 characters, and must carry a concrete example.** That number is
not a style preference: the fleet board clips a program's *first prose paragraph* at 240
characters and shows nothing else — on the program list *and* on the
program's own page. A headline that runs long is a headline whose end nobody reads, and an
example that lands in the second paragraph never reaches the board at all. So the example goes
*inside* the 240, compressed to a clause; the fuller version goes in the `**For example.**`
paragraph directly beneath it, for whoever opens the file.

**Concrete does not mean internal.** "No mechanism" bans *our* vocabulary — component,
package, binary, env var, table, identifier, file path. It does **not** ban specifics. Real
numbers, real quoted sentences, a named role, an amount, a temperature, a page reference are
all things the customer sees, and they are what makes a headline mean something. *"The
purchasing SOP raises its approval limit to €25,000"* is concrete and names nothing of ours.

**Use ordinary words.** Write for someone who does not work here. These are the words the
corpus actually drifted into — each has a plain replacement, and reaching for one is the
signal to stop and say the thing:

> composed · substrate · posture · containment · narrowing · corpus · estate · thread ·
> surface (meaning a page) · admission control · governed-by-construction · walking skeleton ·
> stranded · load-bearing · the ask · orthogonal

Those terms are legitimate *below* the first `##` — a decomposition record is written for
engineers. Above it, they are not.

### Step 3: Create the row fragment

**Location:** one row **fragment** at `knowledge/programs/rows/PG-NN.json` — the filename IS the
id, and the file is JSON mapping each column to its cell (a string per scalar cell, a list per
comma-list cell). The committed table `` is **generated** from these
fragments () and must never be hand-edited — a branch touches only its own row's
fragment, so two branches adding two different rows no longer collide. **Reserve the id with
`python3 knowledge/scripts/validate_id_collisions.py --allocate <program-prefix> 1`** — it
reserves the id atomically as a claim ref on GitHub, so no concurrent session can take it;
the fragment's filename is the id, and there is no counter to bump. An id is permanent, and
permanence is what makes one safe to cite from a PRD that shipped a year ago. Never reuse a
retired id, and never renumber an existing row.

The fragment's keys, in the order `slot:programs` gives and no other — the generated table's
header is compared cell by cell. Whatever the header, the row carries: the id (the filename), the name
(the result someone gets — or, for `kind: program`, the thing that lands), the `Kind`, the
`Verified by` proof, what it `Requires`, and — last — its `Disposition`.

- **`Kind`** — `outcome | program`.
- **`Verified by`** — the e2e proof PRD number(s), comma-separated, or `drill:<stem>` for a
  drill record under `knowledge/drills/` when the composed proof is an observation a harness
  measured. Required on `kind: program`, and the **only** authored input to this program's
  completion reading: it completes when every slice does **and** this proof has shipped — a
  PRD by its `status:`, a drill by its `verdict: passed`. A `Proof accepted` column sat
  between it and `Requires` until , holding a human attestation; it was filled on 0
  of 13 programs and was deleted. Do not re-add it — the header check is exact and rejects it.
- **`Requires`** — the roots of the decomposition, and **not yours to write either**: leave it
  `—` and let `/fleet:program:decompose` author it (the handoff in Step 5).
- **`Disposition`** — **`adopted`**, written out, on every row you author. The decision axis
  both registers carry, with the requirement register's grammar: `adopted` ·
  `withdrawn: decisions/<file>.md` · `superseded by PG-NN`. A ship-state word — `delivered`,
  `closed`, `done` — is refused by the validator with the reason: completion is computed, and
  this cell records what was *decided* about the row. Withdrawing a program later is a register
  edit citing a decision record, never a row deletion — 's row was deleted and every
  citation of its id went dark; that is the precedent this column replaces.
- An **empty cell is `—`**, which reads as *none* and never as a value. A literal pipe inside
  a cell is escaped `\|`, since a `Name` is free prose.

**No `Status` column, and none may be added.** Completion is derived (all slices complete ∧
this program's proof shipped); a stored value is one nobody returns to correct. The register's
header check rejects a reintroduced `Status` outright, and `Disposition` is not a way around
it. See `tracking-and-execution.md` → "Durable vs versioned".

**The register holds no list of this program's slices, deliberately.** A slice names its
program in its own row fragment at `knowledge/slices/rows/SL-NNN.json`, and that edge is authored in exactly one place — so there is
nothing here to keep in sync, and no validator whose job is reconciling one fact stored twice.

**`Verified by` on `kind: program` is a hard requirement, and the proof has to drive a customer-visible surface.** `kind: program` is the escape hatch that lets platform work be named honestly, and it is also exactly how stranded substrate acquires a bar on the roadmap. So a program named for what it builds must name the e2e proof that drives it through a surface a customer touches — browser, API, MCP, or channel — not a component test asserting the substrate in isolation. **If you cannot name such a proof, that is the finding**: either the work has no customer-facing surface yet (which is the stranded-backend failure CLAUDE.md names, and the surface belongs in scope), or this is `kind: outcome` and the outcome has not been stated. Do not write a placeholder to satisfy the validator — leave the cell empty and say the finding out loud. **The empty cell is not a silent one.** Once the program has cuts, the fleet board ends its page's **"What must ship to prove this"** with a terminal node reading *no proof named · **this program can never complete** · `unproven`*, and the board's action list carries the row *"No proof named. Nothing will ever mark this program complete."* over the command that repairs it. Until it has cuts the board says the emptier thing first — that there is nothing to plan into yet — so a program created with neither is not being let off, only asked the earlier question. Node and row both stand until someone answers, and both are silenced only by the program proof-waiver baseline, where a person has written the reason down: the one answer to "no proof named" that is not an omission.

**And the proof may never be one your own slices already name — that one IS fatal ().** A slice's `Verified by` asks *"does this slice do what it said?"*; yours asks *"do these slices work together for a person?"*. Naming one PRD in both collapses your completion condition into that slice's: the program goes green the moment the slice does and can never say anything the slice did not already say — the walking-skeleton failure inverted. Six programs held exactly that on  and all six cells were cleared rather than back-filled (``). **Reaching for a slice's proof is the same reflex as writing a placeholder**, and an empty cell is the honest answer to both.

### Step 3b: Write the narrative into the detail file

**Location:** `knowledge/programs/PG-NN.md` — the filename is the join, so there is no `slug:`
and no frontmatter beyond the type header:

```yaml
---
type: program-detail
---
```

Any other frontmatter key fails the commit, because every structural field already has a
column and a second copy is one that drifts.

**The detail file is optional in the schema and not optional here.** A program's narrative is
the thing being authored — the row holds a name, not a reason — so write it. **From the outside
in: the reader is a customer, a new hire, or an exec, never the implementer.** Everything above
the first `##` is customer narrative; mechanism lives below it (and mostly in the child
slices/PRDs):

```markdown
# <Title — literal, ≤ ~45 chars, no metaphor. Step 2b.>

<Headline — HARD LIMIT 240 characters, because the board clips the first prose paragraph
there and shows nothing else. Two beats: what becomes true in plain words, then a
compressed concrete example with real specifics. It gets quoted on its own — in a
delivery report, a roadmap view, a status conversation — so it has to stand alone with
no title and no context. Count the characters; do not estimate.>

**For example.** <The same example with room to breathe: the situation, what happens
today, what happens after this. Named roles, real numbers, a quoted sentence someone
would actually say. Three to six sentences. This is where a reader who does not know
the product finds out what the program means — it is not a summary of the headline.>

**Who it's for, and when.** <The person, in a circumstance — then the job:
*When <situation>, I want to <motivation>, so I can <outcome>.*>

**Today.** <One concrete story of the status quo failing, told from their side. Not an
abstract complaint, and never "we don't have <component> yet" — that is our problem, not
theirs.>

**Why now.** <What changed, what this unblocks, why this quarter and not next.>

**What changes for them.** <The observable difference in their experience — enough detail
to judge whether it actually solves the problem above, and not one word of how.>

**How we'll know.** <1–3 measures of changed user behaviour or sentiment. Never "X
shipped" — shipping is output, this is outcome.>

**Not doing.** <Explicit no-gos, so scope has a boundary.>
```

**There is no `## Slices` section, and adding one back is a defect.** The slice register's
`Program` column is the single edge; a list here would be the same fact stored twice, which
is exactly the reconciliation the register removed. The sections that *do* belong below the
narrative are the ones holding prose nothing else can hold — `## Decomposition record` and
`## Program-specific work` (written by `/fleet:program:decompose`), and later
`## Delivery log` and `## Findings (off-path)` (appended by `/fleet:program:deliver`).

**The test, applied line by line above the first `##`:** if a sentence names a component,
package, binary, env var, table, identifier, or file path, it is in the wrong place —
move it under `## Decomposition record` or into the owning slice. A reader who
has never seen this codebase must be able to read the whole narrative and understand what
they will be able to do. **The inverse test matters just as much:** if a paragraph could be
about any product, it is too abstract — put the customer's own numbers, roles and sentences
back in. Vagueness is not the same as being free of mechanism, and Step 2b is the rule.

Second test, from Torres: for each stated need, ask *"is there more than one way to
address this?"* If no, you have written a solution wearing a problem's clothes — go up a
level until the answer is yes.

**The narrative skeleton holds for both kinds.** `kind: program` changes the *headline's voice* — it may name the thing that lands — and nothing else: the persona, the problem today, and "what changes for them" are still required, and for `kind: program` they are precisely what `Verified by` has to demonstrate. A program that cannot fill them in is substrate looking for a roadmap bar, which is the thing that clause exists to make impossible. If the thing you are writing resists the skeleton entirely, go back to the ladder.

### Step 4: Tracker — no live mirror (the fleet projects it)

Do **not** mirror to the tracker from this command, and do **not** create a tracker project for the program. Under the current model (`` → its tracker-sync section) the **tracker project is a feature area** — durable, covering the whole product — and a program projects as a **label named for its id** (`PG-NN`). The program tier is **projection-only**: the register row + detail file ship via a throwaway branch + PR (`tracking-and-execution.md` → "Git workflow" — the fleet identity has no direct-to-`main` path), and once that PR merges to `main`, the `prd-projection` pass of the fleet's `corpus-sync` loop (`fleet-service`) reconciles the label within the sync's interval. Never read tracker state back.

### Step 5: Confirm

Report the id assigned (`PG-NN`), the row fragment written, the detail file written, its `kind`,
whether `Verified by` is set (and for `kind: program`, that it names a customer-facing proof),
and the next step:

**→ `/fleet:program:decompose`.** That conversation derives what must be true, authors the
gap capability rows + `Needs` edges, fills `Requires`, names `Verified by`, and leaves a
plan `gen_program_plan.py PG-NN` can replay — including the slices it cuts. Do not hand-write
`Requires` here, and do not cut slices here: both are the decomposition's output.

Once it is decomposed and work is in flight, the recurring verb is
**`/fleet:program:deliver`** (one delivery cycle — releases dispatch-ready work and escalates).

### Step 6: From the brief — the row, by PR, then the result

**One register row, from words two documents already hold.** The framing round (Step 2), the
title and headline work (2b), the narrative (3b) and the proof are the program page's to ask
for next; a run from a brief that writes any of them has authored what nobody saw.

#### The values, and only these

| Column | From |
|---|---|
| `ID` | `python3 knowledge/scripts/validate_id_collisions.py --allocate <program-prefix> 1`, recorded the way the register records reservations — Step 3's rule |
| `Name` | the idea's **title**, as the brief carries it, verbatim. Step 2b's two tests are the page's first refinement, not yours: a title that evokes rather than names is said so in the sentinel summary and never rewritten here |
| `Kind` | `outcome`. Route places an idea at the program rung only as a result somebody gets; `kind: program` is a naming decision for platform work that a person makes with the proof in hand |
| `Verified by` | `—`. The proof is chosen at decomposition, and a guessed proof — or a slice's — is the failure Step 3 names; the row reads *unproven* until the page settles it |
| `Requires` | `—`, as Step 3 already says: the decomposition's output |
| `Disposition` | `adopted`, **when the header carries the column** |

One cell per header column — `Disposition` when the header carries it — in the order
`slot:programs` gives and no other; Step 3's rules on the fragment and the empty cell hold
here. **No detail file**: the narrative is authored from a conversation
Step 2 has, and this run does not have it.

**What the program page asks next, and you say so in the sentinel summary:** the headline
and the example (Step 2b), the narrative (3b), then `/fleet:program:decompose` — which
derives what must be true, cuts the slices, fills `Requires` and names `Verified by`.

#### The row, by PR

**First, find the prior attempt — a retried run must never mint a second id.** A run can end
between arming the merge and writing `created` (a `partial`, a killed session), and the
re-dispatch lands here with the earlier PR still open and armed; the allocator then counts
that PR as a peer claim and hands you the *next* id, and two rows land for one idea. So,
before any branch:

```bash
gh pr list --state open   --search "<issue key>" --json number,headRefName,url
gh pr list --state merged --search "<issue key>" --json number,mergedAt,url
```

- **An open PR carrying the key is the prior attempt.** Check out its branch, re-check the
  id it holds (below), and continue driving *that* PR — never a second branch.
- **A merged PR carrying the key means the row already exists on `main`.** Read the id from
  `gh pr diff <number>` — the one `| PG-NN |` row it appended — write the `created` document
  from it, and stop — there is nothing to allocate.
- **Neither** → this is the first attempt. Branch.

**The branch is deterministic from the key**: `slot:git-workflow`'s pattern for a work item
with `<issue key>` as its key segment and nothing per-run — no slug, no box, no date — so a
retry on any box resolves this same branch; and the PR title carries the key, so the search
above finds it. Cut it from a freshly fetched `origin/main`, create the row fragment, run
`make validate-knowledge`, commit. **Then re-check the id against the
tip you are about to push over**: `git fetch origin main`, re-run the allocator; if it now
prints a different id, the one you hold was taken by a branch that merged while you worked —
rewrite the fragment with the new id and amend. Push, open the PR, and arm the
merge the moment it opens:

```bash
gh pr merge --auto --squash   # never --delete-branch: gh refuses it under a merge queue
```

**Then drive it to `state: MERGED`, not to green.** **Under a merge queue the PR can read green and still not merge.** Watch it with `python3 knowledge/scripts/gh_pr_merge_state.py <pr> --watch`: `armed` and `queued` are pending, `merged` is done, and `ejected` — **removed from the merge queue**, reading OPEN and `CLEAN` with its own checks green and nothing armed — is red CI on the queue's `merge_group` commit (the script names the red checks): fix it, then push — after `python3 knowledge/scripts/gh_automerge_disarm.py <pr>`, because a queued PR's branch rejects every push — and re-arm. A red check is yours to fix; a conflict is
the generated register's shape (two rows regenerate the same table): rebase onto `origin/main`, resolve
by taking the other row *and* yours, re-check the id once more, force-push with
`--force-with-lease`, and keep watching. Until the merge the row exists nowhere a reader can
find it, and a `created` document over an unmerged PR is a claim.

#### The `created` result, then the sentinel

Once merged, one file to the path in `$FLEET_RESULT_FILE`, written whole, read back, parsed:

```json
{"kind": "created", "created": {"kind": "program", "id": "PG-NN", "name": "<the row's Name>", "href": "program:PG-NN", "pr": "<the PR URL>"}}
```

`href` is the fleet's own route to the program's page — `program:` and the id, nothing else.
Fleet reads this file, records the idea as *created*, and closes the issue; you move it
nowhere. **If `$FLEET_RESULT_FILE` is unset in a run that got this far, write nothing
anywhere and say so in the sentinel.**

Then the done-sentinel — your dispatch mission names its path and keys; what a reader here
would get wrong: `"success"` once the `created` file is written over a merged PR, with `pr`
the PR URL; `"partial"` for a PR that could not be brought to merge in this run, naming it,
with **no `created` file**, so the next attempt resumes the branch rather than minting a
second id; `"needs-decision"` for Step 1's refusal; `"failed"` for a mis-dispatch. The result
file decides what fleet does with the idea — the word only records the run.

---

## Rules

- **Two kinds, and neither is a container.** `outcome` names the result; `program` names what lands. A grouping that adds no completion condition beyond the union of its children is a **theme** — which means it is not an entity at all: no row, no cell, no folder. Don't bounce a program to `slice:create` — a slice is a *derived output* of its decomposition, not a substitute for it.
- **Never write a status on a program.** Completion is computed: every slice complete **and** this program's proof shipped. Nothing is stored, so nothing can drift — and there is no column to store it in.
- **`Verified by` is required on `kind: program`, and its proof must drive a customer surface.** This is the walking-skeleton golden rule, and it binds *you*, at authoring time — the validator reports a proofless `kind: program` as a finding rather than refusing the commit, because a required field with no honest value is what manufactures a borrowed one. No placeholder satisfies it, and neither does a slice's proof.
- **A program's proof may never be one of its own slices' — the validator fails the commit ().** Sharing one collapses the program's completion condition into that slice's. Name a genuinely composed thread, or leave the cell empty and let the row read `unproven`.
- **No dates, at any tier.** The program register carried the last one (`Target`) until , when all twelve filled cells turned out to hold the same `2026-Q4`. A real external commitment goes in the program's detail file as an argued sentence — who is holding us to it, and to what — never as a cell.
- **The id comes from the allocator, and the row is a fragment.** Ids are permanent and never reused — a PRD that shipped a year ago may still cite this one. There is no counter to bump: the row lives at `knowledge/programs/rows/PG-NN.json` and the table is generated from it.
- **Structure in the register, prose in the detail file, never both.** A detail file carries no frontmatter but `type: program-detail`; the validator rejects the rest, because a shadow copy of a column is a copy that drifts.
- **The title is literal and the headline carries an example — Step 2b, and it binds every program command.** A title that evokes rather than names, a headline over 240 characters, or a narrative with no concrete example is the defect that made the owner unable to read his own board on . Plain words above the first `##`; our vocabulary below it.
- **Lead with the job, never the mechanism — but never at the cost of being concrete.** The narrative above the first `##` names no component, binary, table, or identifier — it says who is stuck, what they're trying to get done, and what will be different. Amazon built the working-backwards format precisely to break the "skills-forward" habit of describing what we're good at building instead of what someone needs; a program that opens with our components *is* that habit in prose. Mechanism goes under `## Decomposition record` or into the child slice. **What does not go with it is specificity**: real numbers, named roles and quoted sentences are the customer's, not ours, and stripping them is how "no mechanism" turned into prose nobody could act on.
- **Outcomes, not outputs.** "How we'll know" measures a change in user behaviour. "Ship the X service" is an output and belongs to a PRD.
- **One source of truth:** the PRDs' frontmatter `status:`, and nothing above them. Never read tracker state back.
- **Roll-up is load-bearing, and authored downward only:** every slice row names a `Program` that resolves, and every PRD a `slice: SL-NNN`. `make validate-knowledge` (pre-commit) fails the commit on a dangling link. A program never lists its children.
- **Don't** add tracker-url or issue-number fields, or a column for them. The repo is the contract.
- **From a brief: one row, no interview, no narrative, no tracker.** The name is the idea's title, the kind is `outcome`, the proof and the roots are `—`. What a person did not see on the idea's page is not written into a permanent register on their behalf; the program's page asks for it next.
