#  Slice Author

You create or update a **slice** — the middle tier of the planning hierarchy and the planning cut that groups the PRDs a program lands in one piece.

**This is the attended twin of [`slice:refine`](refine.md)** — the same interview, with you in the room, and it takes a cut that already exists as readily as one that does not. (`slice:edit` is the narrower verb for changing one guarded cell on a row that is otherwise right.)

> **You can hand this back to the fleet at any point.** The page's *open in a terminal
> instead* offer is not a one-way door: press **Shape this** on the entity's own page and
> the fleet dispatches [`slice:refine`](refine.md) on it, picking up from whatever is
> committed — the register row, the detail file, the answers already written down. So you
> are never stuck finishing by hand something you only wanted to start by hand: take the
> rest yourself when the forks need you in the room, and hand it over when they do not.

```
Program  (a result someone gets, or a body of work that lands — /fleet:program:create)  →  a row fragment in the `slot:programs` register (PG-NN)  →  a tracker label
  └─ Slice (a planning cut — this command)                  →  a row fragment in the `slot:slices` register (SL-NNN)  →  a tracker label
       └─ PRD (an agent-shift — /fleet:prd:create)         →  knowledge/prds/NNNN        →  tracker issue
```

**A slice is a register row plus, where the cut needs explaining, a detail file.** Every
structural field — name, kind, the program it serves, `Done when`, its proof, its
dependencies, the components it spans — is a column in ``; prose lives in
`knowledge/slices/SL-NNN.md`, whose filename *is* the join and which carries no frontmatter
but `type: slice-detail`.

A slice is **a planning cut that completes**. Three things make it one:

- a **`Kind`** — `feature` (a whole feature lands), `capability` (one capability lands), or `gap-set` (the gaps that must close for one customer). The kind is what makes the cut's *shape* legible; it is not decoration.
- a **one-sentence completion condition** — the **`Done when` column**. It is a column rather than a paragraph precisely because a paragraph is optional by construction: a cell cannot be skipped, and a cut with nothing to write in it is not a slice yet.
- **no dates at all.** Neither register has a date column — the program tier lost its last one (`Target`) on , when all twelve filled cells turned out to hold the same `2026-Q4`. Order comes from the dependency graph; duration, when anyone asks, is derived from measured throughput and presented as a band.

**It carries no status either, and there is no column for one.** A slice is complete when **every member PRD is terminal *and* its proof has shipped** — that is arithmetic over the PRDs, computed on read, stored nowhere. A slice with every PRD terminal and no green proof reads **awaiting proof**, never complete. Writing a status here is how 33 of 40 containers came to hold a value nobody ever returned to correct.

**It is cut by what ships together — never by which component it touches.** A cut usually spans several components, and that is fine: the components it touches are labels on the work, not the slice's identity. Cutting by component instead produces one slice per component touched, which is how a nine-PRD program became six containers, three of them holding a single PRD.

**`slot:slices` names how many slices may be active at once — check before you cut** (Step 1). Nothing previously bounded work in progress, which is how 40 containers appeared. The ceiling is what makes the delivery view readable by construction and forces sequencing to be a decision rather than an accident.

**The load-bearing rule: if it can never reach "done", it is not a slice.** A durable subsystem is a **component** — register it with ``, which puts nothing on the delivery view. Modelling a permanent thing as a slice is what fills a roadmap with bars that never close. The same failure has a subtler form: a **standing bucket** — an open slice that work keeps accreting into just because it is the one open slice on the right component. Scope is fixed at the cut; new needs cut new slices.

**Sizing is decided by the ladder in [`knowledge-model.md`](#) — walk it first-match-wins rather than judging by feel.** This command is correct only when it lands on **slice**; anything else, hand back to `/fleet:route`. **From a brief, that walk is not re-run**: route walked it, wrote the rung into the proposal, and a person accepted it — the placement is theirs, and a hand-back is a terminal move this path has nowhere to make.

Read [``](#) → "Durable vs versioned" before writing.

**Two ways in, told apart by one variable (Step 0).** At a terminal this is an interview that
ends in a row, a detail file and an offered bar. **When `$FLEET_RESULT_FILE` is set** the
fleet dispatched you on an idea a person has already had shaped by [`intake`](../intake.md),
placed by [`route`](../route.md) and **accepted**: the brief carries the dossier and the
proposal, nobody is at a terminal, and you write **the one register row** from those two
documents' own words — by PR, with a `created` result file — and nothing else. The interview
does not run from a brief: the dossier is the interview that already happened, and every
refinement the row still needs is asked on the slice's own page afterwards.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. `understand` asks open questions **before** offering any options, which is the one ordering an interview cannot recover from getting wrong. Steps named `From the brief:` belong to the fleet path; Step 0 decides the mode, and the other mode's steps are closed as *not this mode* at that moment — `room` runs in both. The prose steps below are the authority; this spine indexes them.
>
> **`needs: answers` · `may merge: true`** ([`spine.md`](../../../process/spine.md)) — the fleet dispatches this command on an accepted proposal, and *that* run asks nothing; the terminal path is an interview and carries the card, so the command as a whole asks. The old spine said `autonomous: true` on the strength of the fleet path alone while the card sat 240 lines below it — the exact mismatch the two fields replaced. The terminal path still interviews; `$FLEET_RESULT_FILE` is what keeps the two apart.

```json
{
  "command": "slice-create",
  "tier": "core",
  "sop": "none",
  "needs": "answers",
  "may merge": true,
  "intent": "Author one planning cut inside a program \u2014 what it promises, what it refuses, and the observation that will prove it \u2014 with no status and no dates; from an accepted proposal on the fleet, the one register row and nothing else.",
  "loads": ["planning-model", "entity-model"],
  "requires": [
    "process-spine", "planning-model", "entity-model", "process-interview", "slices", "programs",
    "gate", "git-workflow", "commitments"
  ],
  "optional": ["product-vision", "components", "feature-areas", "feature-maps"],
  "steps": [
    {
      "id": "mode",
      "name": "Which way in \u2014 a terminal, or the fleet with a brief",
      "kind": "decision",
      "actor": "coordinator",
      "body": "step-0-which-way-in"
    },
    {
      "id": "room",
      "name": "Is there room, and which program does it serve?",
      "kind": "gate",
      "actor": "coordinator",
      "gate": "hard",
      "body": "step-1-is-there-room"
    },
    {
      "id": "understand",
      "name": "Understand what is being asked for \u2014 open questions before any options",
      "kind": "author",
      "actor": "coordinator",
      "body": "step-2-understand-what-is-being-asked-for"
    },
    {
      "id": "promise",
      "name": "Frame what this cut promises, and what it refuses",
      "kind": "author",
      "actor": "coordinator",
      "body": "step-3-frame-what-this-cut-promises"
    },
    {
      "id": "frame-cut",
      "name": "Frame the cut (converge in one to two rounds)",
      "kind": "decision",
      "actor": "coordinator",
      "body": "step-4-frame-the-cut"
    },
    {
      "id": "create-row-fragment",
      "name": "Create the row fragment",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-5-create-the-row-fragment"
    },
    {
      "id": "detail-file",
      "name": "Write the detail file when the cut needs explaining",
      "kind": "author",
      "actor": "coordinator",
      "body": "step-5b-write-the-detail-file"
    },
    {
      "id": "author-bar",
      "name": "The bar \u2014 required for a running-system cut, offered otherwise",
      "kind": "author",
      "actor": "coordinator",
      "body": "step-5c-the-bar"
    },
    {
      "id": "tracker",
      "name": "Tracker \u2014 the slice is a label, not a project; nothing is written here",
      "kind": "decision",
      "actor": "coordinator",
      "body": "step-6-tracker"
    },
    {
      "id": "confirm",
      "name": "Confirm",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-7-confirm"
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

- **Unset** → a person is at the terminal and `$ARGUMENTS` is their words. Run Steps 1–7; the
  `From the brief:` steps close as *not this mode*.
- **Set** → the fleet dispatched you. `$ARGUMENTS` is the issue key naming this work, and the
  brief must carry, under their own headings, the **dossier** and a **proposal whose `kind` is
  `slice`**. Run Step 1 (the ceiling, and the program), then Step 8; Steps 2–7 close as *not
  this mode*, and so does the ladder walk in the header — the rung is route's and the person
  accepted it. **You read no tracker and ask no question** — the brief is everything you are
  given, and the one interview this idea gets has already happened.
- **Set, and the brief carries an instruction** — the person sent the idea back at this stage,
  usually answering a refusal below (*cut anyway*, a program named). It is the newest thing in
  the brief: take it as given, and let it settle what it settles.
- **Set, but no proposal in the brief, or a proposal for another kind** → a mis-dispatch.
  Write nothing in the repo; write the sentinel with `status: "failed"` naming what was
  missing, and stop.

### Step 1: Is there room, and which program does it serve?

- **Which PRDs land as part of it?** Name them at the cut. Scope is fixed here; a PRD that shows up later because it happened to be open is the standing-bucket failure.
- **Count the active slices — the ceiling is a hard gate.** Read `` and, for each row, the frontmatter `status:` of the PRDs naming it (`slice: SL-NNN` is the only place that edge is written). A slice is **active** when it holds at least one **live (non-terminal) PRD** — the ceiling bounds work in progress, and the validator enforces exactly this reading. A slice whose PRDs are all terminal is *not* active, whether it reads *complete*, *awaiting proof* (a proof named but unshipped), or *waived* (): none of those is being built, so none counts against the ceiling. **If forty or more are already active, do not cut a forty-first** — report the count, list the active slices, and ask the user which one closes (or which cut waits) per [`interview-protocol.md`](../../../process/interview.md). The validator enforces this ceiling; checking it here means the refusal lands in conversation rather than in a rejected commit.
- Read the register's `Done when` column top to bottom — one file, one sentence per slice, which is what makes this check cheap enough to actually do. If an **open slice's completion condition already covers** this work, add to it. Otherwise cut a new one. **Never place work in a slice merely because it is open.**
- **If the thing is durable and never finishes, stop.** It is a **component** — run ``, which registers it and puts nothing on the delivery view. Do not model it as a slice. (At a terminal only: from a brief the rung is not re-litigated — Step 0.)
- Read ``. **Every slice row must name a `Program` that resolves** — the roll-up edge the validator enforces, authored here and nowhere else (the program tier keeps no list of its slices). There is **no holding tier** — a slice with no program to serve is a signal the program has not been written, not a reason to park it. If no existing program covers this cut, stop and tell the user to run `/fleet:program:create` first.

**From a brief, the same gate refuses by sentinel, because nobody is there to ask.** The
program is the `existing` node directly above the `new slice` in the proposal's `under`
walk — or the one an instruction in the brief names, which outranks it — and it must
resolve to a row. Three refusals, each written as the done-sentinel with
`status: "needs-decision"`, `pr: ""`, and **no row, no branch, no result file** — the idea
stays at its *creating* stage, the issue parks on the person who accepted, and the summary
is what they read, so it names **the move that actually releases it**, which is never
*route again* (nothing on the page re-routes an accepted idea; a send-back re-runs this
command): the ceiling → *"n of the ceiling are active — <the active ids>; close one, or
withdraw this idea, and this run repeats"*; a program id that resolves to nothing → *"send
it back naming the program, or withdraw it"*; an open slice whose `Done when` already
covers this work in so many words → *"<the cut>, by name and id, already promises this —
withdraw it as already filed, or send it back saying cut anyway"*. A brief carrying that
instruction (Step 0) is the answer, and the run goes on. No result kind carries a refusal —
the closed set and why it stays closed are [`intake`](../intake.md) §8.

**Each refusal is a `Blocked · decision` park, so it carries the `decision` document** — the
ceiling count or the slice it reads as (by name and id), and the choice the person has (close
a cut, send it back naming the program or saying cut anyway, or withdraw it), in the card's
own fields:

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

### Step 2: Understand what is being asked for (open questions, before any options)

The user's input is: $ARGUMENTS

**Start in the open, not with a menu.** This step exists because its absence has a measured
shape: a routing session produced a complete, confident `Done when` whose persona, review
workflow and fail-closed refusal rule were lifted from an unrelated PRD's journey and had
**never been stated by the requester**. Nothing downstream caught it, because a fluent
invented sentence reads exactly like a fluent reported one. You cannot write a durable
promise from a request you have only classified.

Ask these first, in the open — per
[`interview-protocol.md`](../../../process/interview.md) → *The
discovery round*, which is the question shape for this step (the 2–4-option shape is for
Step 4, where the alternatives are real):

- **What happens today?** What does somebody actually do when they need this, and what does
  it cost them. One concrete sentence about a real person.
- **Who hits it, and how often?** The persona is an answer, never an assumption. Naming one
  the requester did not name is the single most common way this step goes wrong.
- **What is this deliberately NOT doing?** Ask it outright. A model never volunteers a
  non-goal, and an exclusion nobody asked about is one nobody writes down — which is how
  ~354 out-of-scope statements ended up as prose nothing can cite. These answers become
  `excluded` rows in Step 3, not a paragraph.
- **What will people assume it does, that it will not?** The gap between those two is where
  the next argument comes from.

**The test for leaving this step:** you can say what somebody does today without this, in
their words rather than yours. Until then keep asking — a forced-choice question here
converts your guess into their decision, and Step 3 then writes that guess down as a
permanent row.

### Step 3: Frame what this cut promises — and what it refuses

**A `Done when` says the cut is finished. It does not say what the product now promises
forever, nor what it has decided never to do.** Those are different sentences with different lifetimes — the cut is versioned and
completes; the promise is durable and outlives it. This step writes the second one, and it is
the **only** place in the pipeline where a capability's promise set gets framed as a whole.
Everywhere else it is framed one PRD at a time, months apart, and the fragments never get read
together.

The full model — why rows are born `open`, and why that state is the legitimate human-input
marker — is [`knowledge-model.md`](#) →
[*The claim spine*](#).
Do not restate it here; do this:

1. **Find the register for the ground this cut touches.** `ls knowledge/requirements/`, then
   resolve the slice's `Components` through the `## Component index` table in
   [`requirement-status.md`](#) — the generated
   component→register join, rendered on demand and never committed, so run `python3 knowledge/scripts/gen_requirement_status.py` first. **Never guess a register filename from the slice's name.**

2. **If no register covers it, open one — do not defer.** The frontmatter
   `slot:commitments` gives a register (its type, domain, id prefix, the
   components it governs, its sources of truth) plus the first rows. **This reverses the old instruction**, which sent the author to "carry the
   assertion in the PRD's design and extract the register properly later". That later never
   came: 36 of 65 components carry no register, and the promises that should be in them are
   sitting in PRD prose where nothing can count them. The cheapest moment to open a register is
   the moment you are already having the conversation; every later moment is a reconstruction
   of intent, which is a guess. **The prefix and domain are permanent**, so name them
   deliberately — but name them.

3. **Read what is already promised there** and say so out loud. Half of what a new cut "needs"
   is usually already a row, and a cut that re-promises an existing row has just discovered it
   overlaps work someone else owns.

4. **Sweep every OTHER register for conflicts — `python3 knowledge/scripts/requirement_query.py`
   neighbours --components <ids> --statement "<draft>" …`** Step 3 above reads the one register
   this cut lands on; a contradiction rarely lives there. The sweep returns rows across all
   registers whose components overlap or whose statement shares distinctive terms, and it
   surfaces **`excluded` rows separately and loudly** — a cut that does what an `excluded` row
   says we will not do is the one conflict nothing else in the pipeline can catch. Read the
   hits and say which you are consistent with, which you supersede, and which you are about to
   contradict. **It is a forced read, not a validator**: semantic conflict is a judgement call
   no checker can make, which is exactly why a human has to look.

5. **Interview for what is new** — shaped by the interview card:

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

   Ask about **promises, not mechanisms**: *"must a refused request state its retry time, or may it simply fail?"* is this
   step's question; *"token bucket or sliding window?"* is `prd:design`'s and must not be asked
   here. One round is usually enough; two is the ceiling.

   **Interview for what is refused, too.** Step 2 asked what this is deliberately not doing;
   this is where the answer becomes a row rather than a paragraph. Ask it again explicitly if
   Step 2 produced nothing — an author who names no exclusion has usually not been asked, not
   found none.

6. **Append the rows as `Disposition: open`, taking each id from
   `python3 knowledge/scripts/validate_id_collisions.py --allocate <PREFIX> <N>`**, which
   reserves it atomically as a claim ref (`refs/ids/<ID>` on GitHub) — there is no counter to
   bump. Never a number read off the last row — two branches doing that allocate the same id
   and only find out at merge, and CI refuses an id that carries no claim. Not `adopted` — nothing is settled yet, there is
   no mechanism and often no number, and `open` is precisely the state that says so. `Source`
   cites this slice's own detail file by **quoted phrase, never a line number**. Write the
   `Needs` edges with the rows, per the register's own rule; `—` means *startable now, and that
   was checked*, and a blank cell means nobody looked.

   **An exclusion is a row of its own: `Kind: excluded`, `Disposition: adopted`** — *"we will
   not build this"*, in force from the moment it is written, so it is not `open` the way a
   promise is (there is no mechanism coming that would settle it). Its test is in
   [`knowledge-model.md`](#) → *Requirement*:
   if a violation would show up in the running system it is an `invariant`; if it shows up in
   **the backlog** — someone cutting a slice for it — it is `excluded`. Do not file a refused
   *mechanism* here: that is `Kind: alternative`, `Disposition: rejected`, and it belongs to
   `prd:design`.

7. **Report the count back — both halves.** *"This cut promises 6 new things, re-uses 3, and refuses 2."* That number is a
   real input to whether the cut is the right size — a cut promising thirty things is a program
   wearing a slice's clothes, and a cut promising nothing new is probably an existing slice's
   work.

**What this step never does:** settle a row. `open` → `adopted` is a design act and belongs to
[`prd:design`](#) Phase 4c, which has the mechanism in hand and can write a real
`Source`. A slice author who finds themselves choosing an algorithm has left this step.

### Step 4: Frame the cut (converge in 1–2 rounds)

Steps 2 and 3 are the inputs to this one: the cut is derived from what it promises,
never the reverse. Decisions a slice needs — be opinionated, recommend, converge:

1. **`Kind`** — `feature | capability | gap-set`. *feature*: a whole customer-recognisable feature lands. *capability*: one capability lands, on its own, because that is the honest unit. *gap-set*: the set of gaps that must close for one customer or one engagement. Pick the one that describes the cut you actually made; do not pick `feature` because it sounds bigger.
2. **`Done when`** — the one-sentence completion condition, written straight into the column. It is the test for everything else here: anything that doesn't serve it belongs in another slice. **Write it as a sentence somebody could go and check** — Step 5c offers to decompose exactly this cell into a `## Bar`, and a conjunct nobody can observe is a conjunct nobody can hold you to.
3. **`Verified by`** — OPTIONAL: this slice's **own** proof, normally one of its member PRDs, answering *"does this slice do what it said?"* — a different question from the program's, which asks *"do these work together for a person?"*. Choose it at the cut, for the same reason the program does: choosing a proof after the work means choosing it to fit what shipped. An empty cell is the honest *unproven* reading, and a guessed proof is worse than none. **The empty cell has a shelf life ():** the moment a slice's last live PRD goes terminal, the validator fails the commit unless a `Verified by` names the proof or the slice carries a reasoned `proof_waiver` on its own row fragment (`knowledge/slices/rows/SL-NNN.json`; , never a shared baseline file) — so cut with the proof in mind, and revisit the cell when the slice's work lands, with [`/fleet:slice:edit`](edit.md) (which carries the refusals that write needs: the id resolves, and the proof may not be this program's).
4. **`Components`** — OPTIONAL list, each resolving to an id in `components.md`. It records what the cut spans; it does not define the slice, and a slice that touches none registered yet is still a slice.
5. **`Name`** — a **noun phrase for the thing that lands**, per the naming rule in [`knowledge-model.md`](#) → "Slice and PRD". Two traps it names, both seen in practice: `<Component>: <theme>` (says where the code lives, not what lands) and a **sentence asserting the outcome** — program-voice carried down from the decomposition you just wrote.
6. **`Program`** — the `PG-NN` id of the program this cut serves. It must already exist.
7. **Summary + overview** — one value-led sentence (≤ ~200 chars) and a few short paragraphs: the problem, the shape of the solution, the customer outcome. This is the detail file, and it is what a reader opens when they want to know what this cut is for — make it readable.
8. **`Depends on`** — other **slice ids** (`SL-NNN`), never PRD numbers. An edge is legitimate when one cut's work genuinely builds on the other's. It is **order**, not a gate: it ranks and draws the dependency, and never holds a PRD back — a PRD dispatches once its own `depends_on:` have shipped and its own `blockedBy` is resolved, so a hard prerequisite belongs on the PRD. Most edges do not need writing by hand — they are derivable from the PRD graph, lifting every PRD `depends_on:` that crosses a slice boundary. Author one here only for an ordering the PRD edges don't already imply.
9. **PRDs that roll up** — name them at the cut, but write the edge nowhere here: each of those PRDs carries `slice: SL-NNN` in its own frontmatter, and that is the only place the membership exists.

**Not on the list, and never authored here: a status, a start, a target.** Completion is computed from the member PRDs; a slice has no dates by construction, and the register has no column for any of the three. If you catch yourself reaching for one, that is the old model — see the header.

If a material decision is open, ask **one** question per round, shaped by the interview card (Step 2, item 5).

**The interview skips on provenance, never on polish.** Skip it only when the input arrived from a [`program:decompose`](#) gap row, or in the human's own words in this session. **Never skip because the request reads complete** — the old test was *"skip when the request already pins everything down"*, which keys on how finished the input sounds, and a fabricated `Done when` sounds exactly as finished as a reported one. A routing handoff carries a classification and the requester's verbatim words; if it arrives carrying an authored `Done when`, `Kind` or `Name`, that is the signal to interview, not to skip.

### Step 5: Create the row fragment

**Location:** one row **fragment** at `knowledge/slices/rows/SL-NNN.json` — the filename IS the
id, and the file is JSON mapping each column to its cell (a string per scalar cell, a list per
comma-list cell; `done_when` carries the sentence). The committed table
`` is **generated** from these fragments () and must never be
hand-edited — a branch touches only its own row's fragment, so two branches adding two
different rows no longer collide. **Reserve the id with
`python3 knowledge/scripts/validate_id_collisions.py --allocate <slice-prefix> 1`** — it
reserves the id atomically as a claim ref on GitHub, so no concurrent session can take it,
which is the collision a hand-read of the last row cannot see; the fragment's filename is the
id, and there is no counter to bump. An id is permanent: permanence is what lets a PRD that
shipped a year ago still name the slice it rolled up to. Never reuse a retired id, and never
renumber an existing row.

The fragment's keys, in the order `slot:slices` gives and no other — the generated table's
header is compared cell by cell. Whatever the header, the row carries: the id (the filename),
the name, the `Kind` (`feature` | `capability` | `gap-set`), the owning program, the
one-sentence `Done when`, the `Verified by` proof, the `Depends on` cuts, the components it
touches, and — last — its `Disposition`.

- **`Program`** — a `PG-NN` id that must resolve. This is the roll-up edge, and it is
  authored here and nowhere else.
- **`Done when`** — one sentence that becomes unambiguously true the moment this is finished.
  Free prose, so escape any literal pipe as `\|`.
- **`Verified by`** / **`Depends on`** / **`Components`** — optional; an **empty cell is `—`**,
  which reads as *none* and never as a value. A `Verified by` entry is a PRD number or
  `drill:<stem>`, the record of an observation under `knowledge/drills/`.
- **`Disposition`** — **`adopted`**, written out, on every row you cut. It is the decision axis
  the requirement register has always carried: `adopted` · `withdrawn: decisions/<file>.md` ·
  `superseded by SL-NNN`, and nothing else — `delivered`, `closed`, `done` are ship-state
  claims and the validator refuses them by name. A new cut is `adopted` by definition;
  withdrawing one later is [`slice:edit`](edit.md)'s register edit citing a decision record,
  never a row deletion.

**No status, no start, no target — there are no such columns** and none may be added; all three
are gone by decision, not by omission. Completion is derived from the member PRDs plus the
proof; there are no dates below the program. `Disposition` is not a status: it never says how
far along a cut is, only whether the cut is still in the plan.

**The register carries no PRD list.** Membership is the PRD's own `slice: SL-NNN`, and the
slice's completion is computed from the PRDs that name it — so adding a PRD to this cut is one
edit, in that PRD's frontmatter, and there is nothing here to keep in step with it.

### Step 5b: Write the detail file when the cut needs explaining

**Location:** `knowledge/slices/SL-NNN.md` — the filename is the join, so there is no `slug:`
and no frontmatter beyond the type header:

```yaml
---
type: slice-detail
---
```

Any other frontmatter key fails the commit: every structural field already has a column, and a
second copy is one that drifts.

**Write one whenever the cut is not self-evident from its row** — why these PRDs ship together,
what sequencing the `Depends on` edges encode, what the cut deliberately excludes. The
delivery view is only as good as the slice content, and a row alone rarely carries why.

```markdown
# <Name>

<One-sentence summary — value-led, ≤ ~200 chars.>

<A few short paragraphs: the problem, the solution shape, the customer outcome.>
```

> **If prose here happens to name member PRDs, no checkbox and no `(status)` — validator-enforced.**
> `make validate-knowledge` rejects `- [ ] NNNN …` / `- [x] NNNN …` and `- NNNN … (shipped)`
> in a detail file: ship-state lives **only** in the PRD's own frontmatter `status:`,
> because a copy anywhere else drifts (`slot:planning-model` records the invariant).
> A **not-yet-numbered** placeholder under a "Later (to draft)" heading may still use
> `- [ ] <Title>` — the ban keys on a four-digit PRD number, not on the checkbox itself.

### Step 5c: The bar — required where the promise lives in a running system, offered elsewhere

**Ask first whether the `Done when` you just wrote can be observed only in a running system.**
A cut whose completion sentence names an environment, a live connection, a person doing
something in the product, a deploy that serves, a signal that is read — anything that is true
of a deployment at an instant and not of a file in git — **carries a bar, and this step writes
it now.** Its completion would otherwise be arithmetic over its member PRDs' `status:`, and
that arithmetic cannot see the one thing the sentence promises. Measured : 49
slices read complete, all 49 from a member PRD's `status:` alone, and 4 of them on a proof
whose live criteria had been deferred as `[ext]` and never run. A cut whose sentence is
observable in the corpus itself — a register reconciled, a model renamed, a document that
exists — is **offered** one and may decline. The obligation is on the shape of the promise,
never on the kind of cut.

**Offer it here, once, and take "not now" for an answer — for a corpus-observable cut.** A
slice's completion is arithmetic
over its member PRDs and its proof, and the golden rule names what that arithmetic cannot
see: `status: shipped` proves a capability *exists*, never that it is *connected*. A
**`## Bar`** is the missing observation — what somebody would have to see in a running system
to believe the `Done when` you just wrote. The contract is
[`tracking-and-execution.md`](#) → "The
`## Bar` contract", and it is **optional and monotone**: with no bar every reading behaves
exactly as it does today, and with one the bar can only ever *withhold* a reading, never grant
one. A green bar over an unfinished slice says nothing at all.

**This is the best moment there will ever be, and every later one is worse.** Asked
afterwards, a bar gets reconstructed from whatever shipped — the one condition under which it
is guaranteed to be worthless, and the reason the contract was written ahead of its parser.
Right now the promise is in the author's head and nothing has been built for it to bend
toward.

**Never widen one, and never fabricate one.** Authorship is the human's for a mechanical
reason rather than a ceremonial one: *a bar an agent can widen can never be red.* You may
propose criteria and draft rows — for a running-system cut you **must**, and the human
ratifies them here — but softening a RED condition, deleting a criterion, or writing a section
to have written one is not yours. A fabricated bar is strictly worse than no bar — so for a
corpus-observable cut whose author says "not now", say the cut can carry one later
([`slice:edit`](edit.md) owns that edit) and move on with no residual noted. For a
running-system cut "not now" is not an answer this step accepts: a promise nobody can go and
look at is a promise the delivery loop will read as kept the day its last PRD ships. Say what
would have to be seen; a criterion whose probe cannot exist yet says so in its Probe cell
(`No probe yet — <what has to exist first>`), which is honest, where an absent bar is not.

**Who measures it, and when.** A slice's bar is run by its driver —
[`/fleet:program:deliver PG-NN --slice SL-NNN`](#), every cycle — and by
the program's own loop for any slice without a driver of its own. A red criterion is filed as
an issue citing its id; the slice reads *met* only while no such issue is open. Acceptance
criteria a member PRD can observe only in that environment are **promoted** into this bar
(`[ext → SLnnn-Cn]`, [`prd:create`](#) Phase 4) rather than deferred, so the
rows grow as the PRDs are written and the promise is never left to a criterion nobody runs.

If the offer is taken, append this to `knowledge/slices/SL-NNN.md` — writing the detail file
first if Step 5b decided against one, because a bar is prose and there is no column for it:

```markdown
## Bar

Decomposes this slice's `Done when` cell in [`slices.md`](#), bound to its exact
authored bytes by the digest below.

<!-- done-cell-digest: sha256:<64 lowercase hex> -->

**Scope.** <What these criteria are measured against — which plane, cell or deployment, and
which list they are scored over. A criterion read against an unnamed environment is red here
and green there with nothing saying which one was the standard.>

| # | Criterion — states its own RED | Probe |
|---|---|---|
| SL165-C1 | **<The claim.>** RED if <the condition that refutes it, in the same sentence as the claim>. | <The observation against a running system that could refute it.> |
| SL165-C2 | **<The claim.>** RED if <...>. | No probe yet. <Why nothing measured speaks to this conjunct.> |
```

- **`## Bar` is a top-level section** of the detail file, beside the prose and never nested
  inside another section.
- **Ids are the slice's id with the dash removed, then `-C<n>`, sequential from 1**
  (`slot:planning-model` records the criterion-id form). They are cited from outside git (an issue, a report, a
  conversation), so a gap reads as a criterion somebody deleted and a reused id silently
  rebinds what an earlier citation pointed at.
- **A criterion states its own RED in the sentence it makes its claim.** Falsifiable or it is
  not a criterion: a reader who doubts it has to know precisely what to go and look at.
- **`No probe yet.` is a legitimate probe cell, and often the honest one.** It records that the
  criterion has never been read either way, which is worth far more than a probe invented to
  fill the column — the bars already in this repo's corpus use it (read one from the
  `slot:slices` register's detail files as the worked example). What a probe may **never** be is a
  test file's name or a PRD number: a PRD number is the shipped-artifact fact the bar exists to
  get past.
- **Rows are table cells, never list items.** The `- [ ] 0475 ...` / `- 0475 ... (shipped)` ban
  the Step 5b note names anchors on a list bullet; a table row matches neither pattern, so
  keeping the bar in the table keeps that trap from firing.
- **No `**Demonstration.**` line** — that is the program tier's form. A slice's criteria
  decompose the `Done when` cell, and the digest is what binds them to it.

**Compute the digest with the repo's own implementation, never by hand.** The bar binds to the
*exact authored bytes* of the cell you wrote in Step 5, so compute it from the register
after that row is written, substituting this slice's id:

```bash
python3 knowledge/scripts/fleet.py digest -k knowledge <slices-register> SL-NNN
```

Paste the 64 lowercase hex into the marker. That is the same code the `bars` gate digests
with, so it agrees by construction; a hand-rolled hash over what you *think* the cell says is
the one reliable way to produce a digest that disagrees with the reader.

### Step 6: Tracker — the slice is a label, not a project

Do **not** mirror to the tracker from this command, and do **not** create a tracker project for the slice. Under the current model ([``](#) → its tracker-sync section) the **tracker project is a feature area** — durable, covering the whole product, reconciled from `knowledge/features/` — and a slice projects as a **label named for its id** (`SL-NNN`) on the issues it contains. The register row + detail file ship via a throwaway branch + PR (→ "Git workflow" — the fleet identity has no direct-to-`main` path), and once that PR merges to `main`, the `prd-projection` pass of the fleet's `corpus-sync` loop (`fleet-service`) reconciles the label within the sync's interval. Never read tracker state back.

Slice-to-slice `Depends on` is **not** projected: the tracker has no place left to draw it. The dependency view is the fleet board's **Dependencies** page, which lays every cut not yet `complete` out in waves and states on each node what it waits on and what waits on it; a program's own page narrows that same graph to **"What must ship to prove this"** — the closure standing between that program and its proof, which is why it draws cuts belonging to other programs too. Drawing the graph is not sequencing it: the fleet still dispatches on issue-level `blockedBy`.

### Step 7: Confirm

Report the id assigned (`python3 knowledge/scripts/validate_id_collisions.py --allocate` reserved it), whether a detail file was written, its `Kind`, the program it rolls up to, any dependencies set, whether a `## Bar` was offered and taken (a declined offer is a legitimate answer and not a residual — say so), the **active-slice count after this cut** (`n/40`), and the next step: draft or attach PRDs with `/fleet:prd:create` (each will set `slice: SL-NNN`).

### Step 8: From the brief — the row, by PR, then the result

**One register row, from words two documents already hold, and nothing you would have to
invent.** The interview (Steps 2–4), the requirement rows (Step 3), the detail file (5b) and
the bar (5c) are the slice page's to ask for next; a run from a brief that writes any of them
has authored what nobody saw.

#### The values, and only these

| Column | From |
|---|---|
| `ID` | `python3 knowledge/scripts/validate_id_collisions.py --allocate <slice-prefix> 1`, recorded the way the register records reservations — Step 5's rule |
| `Name` | the idea's **title**, as the brief carries it, verbatim. Not a rewrite: a title that is not yet a noun phrase for what lands is the page's first refinement, and you say so in the sentinel summary |
| `Kind` | the `meta` of the proposal's `new slice` node when it is `feature`, `capability` or `gap-set`; otherwise `feature` |
| `Program` | the `existing` node directly above the `new slice` in `under` — Step 1 checked it resolves |
| `Done when` | the dossier's `howYouWouldKnow`, **verbatim** — a literal pipe escaped, nothing else touched. If it is more than one sentence, the **first** sentence, and the sentinel summary says so. No judgement is spent here: a tightened observation is an authored one |
| `Verified by` · `Depends on` · `Components` | `—` — each is a decision the page asks for; a guessed proof is worse than none |
| `Disposition` | `adopted`, **when the header carries the column** |

One cell per header column, in the order `slot:slices` gives and no other, exactly as Step 5
says; Step 5's rules on the fragment, the empty cell and the escaped pipe all hold here.

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
  `gh pr diff <number>` — the one `SL-NNN.json` row fragment it created — write the `created` document
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
the generated register's shape (two cuts regenerate the same table): rebase onto `origin/main`, resolve
by regenerating the table from both fragments, re-check the id once more, force-push with
`--force-with-lease`, and keep watching. Until the merge the row exists nowhere a reader can
find it, and a `created` document over an unmerged PR is a claim.

#### The `created` result, then the sentinel

Once merged, one file to the path in `$FLEET_RESULT_FILE`, written whole, read back, parsed:

```json
{"kind": "created", "created": {"kind": "slice", "id": "SL-NNN", "name": "<the row's Name>", "href": "slice:SL-NNN", "pr": "<the PR URL>"}}
```

`href` is the fleet's own route to the slice's page — `slice:` and the id, nothing else — and
it is where the person is sent next. Fleet reads this file, records the idea as *created*,
and closes the issue; you move it nowhere. **If `$FLEET_RESULT_FILE` is unset in a run that
got this far, write nothing anywhere and say so in the sentinel.**

Then the done-sentinel — your dispatch mission names its path and keys; what a reader here
would get wrong: `"success"` once the `created` file is written over a merged PR, with `pr`
the PR URL; `"partial"` for a PR that could not be brought to merge in this run, naming it,
with **no `created` file**, so the next attempt resumes the branch rather than cutting a
second row; `"needs-decision"` for the three Step 1 refusals; `"failed"` for a mis-dispatch.
The result file decides what fleet does with the idea — the word only records the run.

---

## Rules

- **A slice must be able to finish.** If it can never reach completion it is a **component**, not a slice. This is the rule the whole model rests on.
- **Never write a status on a slice.** Completion is computed — every member PRD terminal **and** the proof shipped — and it is computed every time anyone reads it, so it cannot drift. A stored value can only ever be wrong later, which is why no column holds one.
- **Never write a start or a target on a slice.** No dates on either register — the exact-header check refuses a `Start`/`Target` column on both tiers.
- **The id comes from the allocator, and the row is a fragment.** Ids are permanent and never reused — a shipped PRD may still cite this one. There is no counter to bump: the row lives at `knowledge/slices/rows/SL-NNN.json` and the table is generated from it.
- **Structure in the register, prose in the detail file, never both.** A detail file carries no frontmatter but `type: slice-detail`; the validator rejects the rest.
- **Progress is gated on proof.** "7 of 7 built" is exactly the reading that reported a program complete while its composed path returned 503 (PRD 0252). Every PRD terminal with no green proof is **awaiting proof**, not done.
- **The active-slice ceiling (`slot:slices`).** Cutting one past it is refused here, not negotiated. The ceiling is what forces sequencing to be a decision.
- **Closing is a matched pair.** A live PRD may not name a completed slice; and a slice cannot read complete while any PRD naming it is still live — which, since completion is derived, happens by construction. **Finish or move the work** — the next need cuts the next slice. Never reopen a closed slice to take new work.
- **`Kind` is required and describes the cut you made** — `feature`, `capability` or `gap-set`. It is what tells a reader why these PRDs are together.
- **Every slice rolls up:** `Program` must resolve. The pre-commit validator (`make validate-knowledge`) fails the commit otherwise.
- **`Components` entries must resolve** to ``. Components are durable and carry no ship-state. The column records what the cut spans — it never defines it.
- **Dependencies are between slices** (`Depends on` = `SL-NNN` ids). PRD-level `depends_on:` (PRD numbers) lives in the PRD frontmatter and is a different edge.
- **`Done when` is never left thin, and prose is written where the cut isn't obvious.** The delivery view is only as good as the slice content; a one-word completion condition and no detail file is an empty slice with a row around it.
- **The bar is offered at the cut, never forced.** A `## Bar` is optional and monotone — no bar changes no reading — but the cut is the last moment its criteria can be written *from the promise* instead of reconstructed from what shipped. Offer it once (Step 5c), take "not now" without argument, and never widen or soften a criterion: authorship is the human's, because a bar an agent can widen can never be red.
- **One source of truth:** the PRDs' frontmatter `status:`. Never read tracker state back. No tracker-url / `gh_issue:` fields.
- **From a brief: one row, no interview, no tracker.** The name is the idea's title, the `Done when` is the dossier's own observation, the kind and the program are route's placement, and every other cell is `—`. What a person did not see on the idea's page is not written into a permanent register on their behalf; the slice's page asks for it next.
