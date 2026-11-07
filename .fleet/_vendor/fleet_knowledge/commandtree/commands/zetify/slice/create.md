# <!-- home -->Zetify<!-- /home --> Slice Author

You create or update a **slice** — the middle tier of the planning hierarchy and the planning cut that groups the PRDs a program lands in one piece.

**Before you write a slice file, read its docs page** (under `.fleet/docs/`; `read_doc <page>` when Fleet's tools are in the session): `knowledge-base/slices`.

**This is the attended twin of [`slice:refine`](refine.md)** — the same interview, with you in the room, and it takes a cut that already exists as readily as one that does not. (`slice:edit` is the narrower verb for changing one guarded cell on a row that is otherwise right.)

> **You can hand this back to the fleet at any point.** The page's *open in a terminal
> instead* offer is not a one-way door: press **Shape this** on the entity's own page and
> the fleet dispatches [`slice:refine`](refine.md) on it, picking up from whatever is
> committed — the register row, the detail file, the answers already written down. So you
> are never stuck finishing by hand something you only wanted to start by hand: take the
> rest yourself when the forks need you in the room, and hand it over when they do not.

```
Program  (a result someone gets, or a body of work that lands — /zetify:program:create)  →  a row fragment in the `slot:programs` register (PG-NN)  →  a tracker label
  └─ Slice (a planning cut — this command)                  →  a row fragment in the `slot:slices` register (SL-NNN)  →  a tracker label
       └─ PRD (an agent-shift — /zetify:prd:create)         →  knowledge/prds/NNNN<!-- home -->-slug/prd.md<!-- else -->-<slug>/prd.md<!-- /home -->        →  tracker issue
```

**A slice is a register row plus, where the cut needs explaining, a detail file.** Every
structural field — name, kind, the program it serves, `Done when`, its proof, its
dependencies, the components it spans — is a column in <!-- home -->`knowledge/slices.md`<!-- else -->`slot:slices`<!-- /home -->; prose lives in
`knowledge/slices/SL-NNN.md`, whose filename *is* the join and which carries no frontmatter
but `type: slice-detail`.

A slice is **a planning cut that completes**. Three things make it one:

- a **`Kind`** — `feature` (a whole feature lands), `capability` (one capability lands), or `gap-set` (the gaps that must close for one customer). The kind is what makes the cut's *shape* legible; it is not decoration.
- a **one-sentence completion condition** — the **`Done when` column**. It is a column rather than a paragraph precisely because a paragraph is optional by construction: a cell cannot be skipped, and a cut with nothing to write in it is not a slice yet.
- **no dates at all.** Neither register has a date column — the program tier lost its last one (`Target`)<!-- home --> on 2026-08-17<!-- /home --> when all twelve filled cells turned out to hold the same `2026-Q4`. Order comes from the dependency graph; duration, when anyone asks, is derived from measured throughput and presented as a band.

**It carries no status either, and there is no column for one.** A slice is complete when **every member PRD is terminal *and* its proof has shipped** — that is arithmetic over the PRDs, computed on read, stored nowhere. A slice with every PRD terminal and no green proof reads **awaiting proof**, never complete. Writing a status here is how 33 of 40 containers came to hold a value nobody ever returned to correct.

**It is cut by what ships together — never by which component it touches.** A cut usually spans several components, and that is fine: the components it touches are labels on the work, not the slice's identity. Cutting by component instead produces one slice per component touched, which is how a nine-PRD program became six containers, three of them holding a single PRD.

**`slot:slices` names how many slices may be active at once — check before you cut** (Step 1). Nothing previously bounded work in progress, which is how 40 containers appeared. The ceiling is what makes the delivery view readable by construction and forces sequencing to be a decision rather than an accident.

**The load-bearing rule: if it can never reach "done", it is not a slice.** A durable subsystem is a **component** — register it with <!-- home -->`/zetify:component:create`<!-- else -->a component registration (`slot:components`)<!-- /home -->, which puts nothing on the delivery view. Modelling a permanent thing as a slice is what fills a roadmap with bars that never close. The same failure has a subtler form: a **standing bucket** — an open slice that work keeps accreting into just because it is the one open slice on the right component. Scope is fixed at the cut; new needs cut new slices.

**Sizing is decided by the ladder in <!-- home -->[`knowledge-model.md`](../../../../knowledge/specs/knowledge-model.md)<!-- else -->`slot:entity-model`<!-- /home --> — walk it first-match-wins rather than judging by feel.** This command is correct only when it lands on **slice**; anything else, hand back to `/zetify:route`. **From a brief, that walk is not re-run**: route walked it, wrote the rung into the proposal, and a person accepted it — the placement is theirs, and a hand-back is a terminal move this path has nowhere to make.

Read [<!-- home -->`knowledge/specs/tracking-and-execution.md`<!-- else -->`slot:planning-model`<!-- /home -->](<!-- home -->../../../../knowledge/specs/tracking-and-execution.md<!-- else -->#<!-- /home -->) → "Durable vs versioned" before writing.

**Two ways in, told apart by one variable (Step 0).** At a terminal this is an interview that
ends in a row, a detail file and an offered bar. **When `$FLEET_RESULT_FILE` is set** the
fleet dispatched you on an idea a person has already had shaped by [`intake`](../intake.md),
placed by [`route`](../route.md) and **accepted**: the brief carries the dossier and the
proposal, nobody is at a terminal, and you write **the one register row** from those two
documents' own words — by PR, with a `created` result file — and nothing else, except the
**new feature area's map** when the proposal carries `newArea` (Step 8). The interview
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
  "intent": "Author one planning cut inside a program \u2014 what it promises, what it refuses, and the observation that will prove it \u2014 with no status and no dates; from an accepted proposal on the fleet, the one register row \u2014 and the new feature area\u2019s map when the proposal creates one \u2014 and nothing else.",
  "loads": ["planning-model", "entity-model"],
  "requires": [
    "process-spine", "planning-model", "entity-model", "process-interview", "process-feature-flow", "slices",
    "programs", "gate", "git-workflow", "commitments"
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
- **Set, and the proposal's `kind` is `area` or `use`, or it carries `plan`** → an accepted **new
  feature** (its map only, no row), an accepted **new use** (one `###` section on an existing
  feature's map, no row) or an accepted **plan** (one row per planned slice, with its
  pieces of work as PRD stubs). A plan, a new use or a new feature filed from a feature's page carries a
  `## Request` block and **no dossier** — that is not a mis-dispatch: the plan's own words
  replace the dossier's. Run Step 1, then Step 8's *The feature flows*.
- **Set, and the brief carries an instruction** — the person sent the idea back at this stage,
  usually answering a refusal below (*cut anyway*, a program named). It is the newest thing in
  the brief: take it as given, and let it settle what it settles.
- **Set, but no proposal in the brief, or a proposal for another kind** → a mis-dispatch.
  Write nothing in the repo; write the sentinel with `status: "failed"` naming what was
  missing, and stop.

### Step 1: Is there room, and which program does it serve?

- **Which PRDs land as part of it?** Name them at the cut. Scope is fixed here; a PRD that shows up later because it happened to be open is the standing-bucket failure.
- **Count the active slices — the ceiling is a hard gate.** Read <!-- home -->`knowledge/slices.md`<!-- else -->`slot:slices`<!-- /home --> and, for each row, the frontmatter `status:` of the PRDs naming it (`slice: SL-NNN` is the only place that edge is written). A slice is **active** when it holds at least one **live (non-terminal) PRD** — the ceiling bounds work in progress, and the validator enforces exactly this reading. A slice whose PRDs are all terminal is *not* active, whether it reads *complete*, *awaiting proof* (a proof named but unshipped), or *waived* (<!-- home -->ENG-8096<!-- /home -->): none of those is being built, so none counts against the ceiling. **If forty or more are already active, do not cut a forty-first** — report the count, list the active slices, and ask the user which one closes (or which cut waits) per [`interview-protocol.md`](../../../process/interview.md). The validator enforces this ceiling; checking it here means the refusal lands in conversation rather than in a rejected commit.
- Read the register's `Done when` column top to bottom — one file, one sentence per slice, which is what makes this check cheap enough to actually do. If an **open slice's completion condition already covers** this work, add to it. Otherwise cut a new one. **Never place work in a slice merely because it is open.**
- **If the thing is durable and never finishes, stop.** It is a **component** — run <!-- home -->`/zetify:component:create`<!-- else -->a component registration (`slot:components`)<!-- /home -->, which registers it and puts nothing on the delivery view. Do not model it as a slice. (At a terminal only: from a brief the rung is not re-litigated — Step 0.)
- **Every slice names its feature area**<!-- home --> (decision 2026-10-27, amended 2026-10-28, `FLT-1280`)<!-- /home -->: the `area:` slug of the feature map that owns the work — `python3 knowledge/scripts/planning_mode.py --areas` lists them with their components. Choose by the map's components and Intent; when two fit, ask, never guess. No map fits → stop and say which area is missing; at a terminal a new feature map is its own change. **From a brief whose proposal carries `newArea`** (areas mode only<!-- home -->, `FLT-1292`<!-- /home -->), the area does not exist yet and **this run creates it**, in the same pull request as the row — Step 8's *A new feature area*; a map with that slug already on `main` is a refusal, below. **A slice without an area is refused at commit.**
- **Then read the planning mode: `python3 knowledge/scripts/planning_mode.py`** prints `programs` or `areas` (`.fleet/fleet.toml` `[fleet.planning] mode`; absent means `programs`<!-- home -->, `FLT-1281`<!-- /home -->). It decides whether the new slice ALSO joins a program:
  - **`areas`:** it names **no program**. **Programs take no new slices in this mode**<!-- home --> (`FLT-1282`)<!-- /home -->: if the request names a program as the home, refuse it — *"This repository plans by area (`.fleet/fleet.toml` `[fleet.planning] mode = "areas"`), so programs take no new slices. Put the slice under the area it belongs to: `area: <suggested area>`."* — and offer the area instead.
  - **`programs`:** as before — the bullet below — with the area beside the program.
- Read <!-- home -->`knowledge/programs.md`<!-- else -->`slot:programs`<!-- /home --> (`programs` mode). **Every slice row in this mode also names a `Program` — the roll-up edge the validator enforces, authored here and nowhere else (the program tier keeps no list of its slices). There is **no holding tier** — a slice with no program to serve is a signal the program has not been written, not a reason to park it. If no existing program covers this cut, stop and tell the user to run `/zetify:program:create` first.

**From a brief, the same gate refuses by sentinel, because nobody is there to ask.** The
program is the `existing` node directly above the `new slice` in the proposal's `under`
walk — or the one an instruction in the brief names, which outranks it — and it must
resolve to a row. Three refusals, each written as the done-sentinel with
`status: "needs-decision"`, `pr: ""`, and **no row, no branch, no result file** — the idea
stays at its *creating* stage, the issue parks on the person who accepted, and the summary
is what they read, so it follows the card's summary rules below (one or two plain sentences,
titles never ids, what each answer does) and names **the move that actually releases it**,
which is never *route again* (nothing on the page re-routes an accepted idea; a send-back
re-runs this command): the ceiling → *"Too many plans are being built at once to start this
one. Wait for one to finish, or withdraw this request."*; a program that resolves to nothing →
*"Fleet could not tell which goal this plan serves. Send it back naming the goal, or withdraw
this request."*; an open cut whose `Done when` already covers this work in so many words →
*"This already has a plan, '<the cut's title>', accepted <when>. Withdraw this request, or send
it back if you want a second plan anyway."*; a proposal whose `newArea` cannot be written
(Step 8's *A new feature area*: its slug is already a feature area on `main`, the proposal
carries no feature brief or no uses, or the map writer refuses) → *"The new
feature '<name>' cannot be added: <the writer's reason, in plain words>. Send it back naming
the feature it belongs to, or withdraw this request."* A brief carrying that
instruction (Step 0) is the answer, and the run goes on. No result kind carries a refusal —
the closed set and why it stays closed are [`intake`](../intake.md) §8.

**Each refusal is a `Blocked · decision` park, so it carries the `decision` document** — the
ceiling count or the slice it reads as (by name, its id quoted in `context`), and the choice the person has (close
a cut, send it back naming the program or saying cut anyway, or withdraw it), in the card's
own fields:

<!-- include: process/decision-document.md -->

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
marker — is <!-- home -->[`knowledge-model.md`](../../../../knowledge/specs/knowledge-model.md)<!-- else -->`slot:entity-model`<!-- /home --> →
[*The claim spine*](<!-- home -->../../../../knowledge/specs/knowledge-model.md#the-claim-spine--one-identity-from-commitment-to-test<!-- else -->#<!-- /home -->).
Do not restate it here; do this:

1. **Find the register for the ground this cut touches.** `ls knowledge/requirements/` (a register
   whose rows are fragments keeps only its `<domain>.md.tmpl` shell in git — render the tables with
   `python3 knowledge/scripts/gen_knowledge_fragments.py` before reading one), then
   resolve the slice's `Components` through the `## Component index` table in
   <!-- home -->[`requirement-status.md`](../../../../knowledge/requirement-status.md)<!-- else -->`slot:commitments`<!-- /home --> — the generated
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
   was checked*, and a blank cell means nobody looked. Word each `Statement` to
   [*Wording a promise*](../../../process/knowledge-bootstrap-formats.md#wording-a-promise--every-capability-rule-and-criterion).

   **An exclusion is a row of its own: `Kind: excluded`, `Disposition: adopted`** — *"we will
   not build this"*, in force from the moment it is written, so it is not `open` the way a
   promise is (there is no mechanism coming that would settle it). Its test is in
   <!-- home -->[`knowledge-model.md`](../../../../knowledge/specs/knowledge-model.md)<!-- else -->`slot:entity-model`<!-- /home --> → *Requirement*:
   if a violation would show up in the running system it is an `invariant`; if it shows up in
   **the backlog** — someone cutting a slice for it — it is `excluded`. Do not file a refused
   *mechanism* here: that is `Kind: alternative`, `Disposition: rejected`, and it belongs to
   `prd:design`.

7. **Report the count back — both halves.** *"This cut promises 6 new things, re-uses 3, and refuses 2."* That number is a
   real input to whether the cut is the right size — a cut promising thirty things is a program
   wearing a slice's clothes, and a cut promising nothing new is probably an existing slice's
   work.

**What this step never does:** settle a row. `open` → `adopted` is a design act and belongs to
[`prd:design`](<!-- home -->../prd/design.md<!-- else -->#<!-- /home -->) Phase 4c, which has the mechanism in hand and can write a real
`Source`. A slice author who finds themselves choosing an algorithm has left this step.

### Step 4: Frame the cut (converge in 1–2 rounds)

Steps 2 and 3 are the inputs to this one: the cut is derived from what it promises,
never the reverse. Decisions a slice needs — be opinionated, recommend, converge:

1. **`Kind`** — `feature | capability | gap-set`. *feature*: a whole customer-recognisable feature lands. *capability*: one capability lands, on its own, because that is the honest unit. *gap-set*: the set of gaps that must close for one customer or one engagement. Pick the one that describes the cut you actually made; do not pick `feature` because it sounds bigger.
2. **`Done when`** — the one-sentence completion condition, written straight into the column. It is the test for everything else here: anything that doesn't serve it belongs in another slice. **Write it as a sentence somebody could go and check** — Step 5c offers to decompose exactly this cell into a `## Bar`, and a conjunct nobody can observe is a conjunct nobody can hold you to.
3. **`Verified by`** — OPTIONAL: this slice's **own** proof, normally one of its member PRDs, answering *"does this slice do what it said?"* — a different question from the program's, which asks *"do these work together for a person?"*. Choose it at the cut, for the same reason the program does: choosing a proof after the work means choosing it to fit what shipped. An empty cell is the honest *unproven* reading, and a guessed proof is worse than none. **The empty cell has a shelf life (<!-- home -->ENG-8096<!-- /home -->):** the moment a slice's last live PRD goes terminal, the validator fails the commit unless a `Verified by` names the proof or the slice carries a reasoned `proof_waiver` on its own row fragment (`knowledge/slices/rows/SL-NNN.json`; <!-- home -->ENG-12602<!-- /home -->, never a shared baseline file) — so cut with the proof in mind, and revisit the cell when the slice's work lands, with [`/zetify:slice:edit`](edit.md) (which carries the refusals that write needs: the id resolves, and the proof may not be this program's).
4. **`Components`** — OPTIONAL list, each resolving to an id in `components.md`. It records what the cut spans; it does not define the slice, and a slice that touches none registered yet is still a slice.
5. **`Name`** — a **noun phrase for the thing that lands**, per the naming rule in <!-- home -->[`knowledge-model.md`](../../../../knowledge/specs/knowledge-model.md)<!-- else -->`slot:entity-model`<!-- /home --> → "Slice and PRD". Two traps it names, both seen in practice: `<Component>: <theme>` (says where the code lives, not what lands) and a **sentence asserting the outcome** — program-voice carried down from the decomposition you just wrote.
6. **`Program`** — the `PG-NN` id of the program this cut serves. It must already exist.
7. **Summary + overview** — one value-led sentence (≤ ~200 chars) and a few short paragraphs: the problem, the shape of the solution, the customer outcome. This is the detail file, and it is what a reader opens when they want to know what this cut is for — make it readable.
8. **`Depends on`** — other **slice ids** (`SL-NNN`), never PRD numbers. An edge is legitimate when one cut's work genuinely builds on the other's. It is **order**, not a gate: it ranks and draws the dependency, and never holds a PRD back — a PRD dispatches once its own `depends_on:` have shipped and its own `blockedBy` is resolved, so a hard prerequisite belongs on the PRD. Most edges do not need writing by hand — they are derivable from the PRD graph, lifting every PRD `depends_on:` that crosses a slice boundary. Author one here only for an ordering the PRD edges don't already imply.
9. **PRDs that roll up** — name them at the cut, but write the edge nowhere here: each of those PRDs carries `slice: SL-NNN` in its own frontmatter, and that is the only place the membership exists.

**Not on the list, and never authored here: a status, a start, a target.** Completion is computed from the member PRDs; a slice has no dates by construction, and the register has no column for any of the three. If you catch yourself reaching for one, that is the old model — see the header.

If a material decision is open, ask **one** question per round, shaped by the interview card (Step 2, item 5).

**The interview skips on provenance, never on polish.** Skip it only when the input arrived from a [`program:decompose`](<!-- home -->../program/decompose.md<!-- else -->#<!-- /home -->) gap row, or in the human's own words in this session. **Never skip because the request reads complete** — the old test was *"skip when the request already pins everything down"*, which keys on how finished the input sounds, and a fabricated `Done when` sounds exactly as finished as a reported one. A routing handoff carries a classification and the requester's verbatim words; if it arrives carrying an authored `Done when`, `Kind` or `Name`, that is the signal to interview, not to skip.

### Step 5: Create the row fragment

**Location:** one row **fragment** at `knowledge/slices/rows/SL-NNN.json` — the filename IS the
id, and the file is JSON mapping each column to its cell (a string per scalar cell, a list per
comma-list cell; `done_when` carries the sentence). The committed table
<!-- home -->`knowledge/slices.md`<!-- else -->`slot:slices`<!-- /home --> is **generated** from these fragments (<!-- home -->ENG-12549<!-- /home -->) and must never be
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

- **`area`** — REQUIRED on every slice: a feature map's slug, `"area": "<slug>"` in the row fragment
  (in a table-only corpus the `Program` cell carries `area:<slug>`, after the program when there is one).
- **`Program`** — a `PG-NN` id that must resolve, in `programs` mode only. This is the roll-up edge, and
  it is authored here and nowhere else. In `areas` mode the fragment carries no `program` key.
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
> `{{target:validate-knowledge}}` rejects `- [ ] NNNN …` / `- [x] NNNN …` and `- NNNN … (shipped)`
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
that arithmetic cannot see the one thing the sentence promises. Measured <!-- home -->2026-09-10<!-- /home -->: 49
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
<!-- home -->[`tracking-and-execution.md`](../../../../knowledge/specs/tracking-and-execution.md)<!-- else -->`slot:planning-model`<!-- /home --> → "The
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
[`/zetify:program:deliver PG-NN --slice SL-NNN`](<!-- home -->../program/deliver.md<!-- else -->#<!-- /home -->), every cycle — and by
the program's own loop for any slice without a driver of its own. A red criterion is filed as
an issue citing its id; the slice reads *met* only while no such issue is open. Acceptance
criteria a member PRD can observe only in that environment are **promoted** into this bar
(`[ext → SLnnn-Cn]`, [`prd:create`](<!-- home -->../prd/create.md<!-- else -->#<!-- /home -->) Phase 4) rather than deferred, so the
rows grow as the PRDs are written and the promise is never left to a criterion nobody runs.

If the offer is taken, append this to `knowledge/slices/SL-NNN.md` — writing the detail file
first if Step 5b decided against one, because a bar is prose and there is no column for it:

```markdown
## Bar

Decomposes this slice's `Done when` cell in <!-- home -->[`slices.md`](../../../../knowledge/slices.md)<!-- else -->`slot:slices`<!-- /home -->, bound to its exact
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

Do **not** mirror to the tracker from this command, and do **not** create a tracker project for the slice. Under the current model ([<!-- home -->`knowledge/specs/tracking-and-execution.md`<!-- else -->`slot:planning-model`<!-- /home -->](<!-- home -->../../../../knowledge/specs/tracking-and-execution.md<!-- else -->#<!-- /home -->) → its tracker-sync section) the **tracker project is a feature area** — durable, covering the whole product, reconciled from `knowledge/features/` — and a slice projects as a **label named for its id** (`SL-NNN`) on the issues it contains. The register row + detail file ship via a throwaway branch + PR (→ "Git workflow" — the fleet identity has no direct-to-`main` path), and once that PR merges to `main`, the `prd-projection` pass of the fleet's `corpus-sync` loop (`fleet-service`) reconciles the label within the sync's interval. Never read tracker state back.

Slice-to-slice `Depends on` is **not** projected: the tracker has no place left to draw it. The dependency view is the fleet board's **Dependencies** page, which lays every cut not yet `complete` out in waves and states on each node what it waits on and what waits on it; a program's own page narrows that same graph to **"What must ship to prove this"** — the closure standing between that program and its proof, which is why it draws cuts belonging to other programs too. Drawing the graph is not sequencing it: the fleet still dispatches on issue-level `blockedBy`.

### Step 7: Confirm

Report the id assigned (`python3 knowledge/scripts/validate_id_collisions.py --allocate` reserved it), whether a detail file was written, its `Kind`, the program it rolls up to, any dependencies set, whether a `## Bar` was offered and taken (a declined offer is a legitimate answer and not a residual — say so), the **active-slice count after this cut** (`n/40`), and the next step: draft or attach PRDs with `/zetify:prd:create` (each will set `slice: SL-NNN`).

### Step 8: From the brief — the row, by PR, then the result

**One register row, from words two documents already hold, and nothing you would have to
invent.** The interview (Steps 2–4), the requirement rows (Step 3), the detail file (5b) and
the bar (5c) are the slice page's to ask for next; a run from a brief that writes any of them
has authored what nobody saw.

#### The feature flows: a new feature alone, a new use, a feature's brief, a plan, or removing a use

When the accepted proposal is `kind: area`, `kind: use`, `kind: brief` or `kind: removal`, or carries `plan`, **this subsection replaces the
values table below**: what is written, and the `created` document reported, are the shared
guidance's *What `slice:create` writes*. A new feature is the map alone (the writer below, with
no row); a new use is `new_feature_use.py` alone (no row of any kind); a feature's brief is
`write_feature_brief.py` alone (the brief and its rows sorted into uses, no row added); removing a use is
`remove_feature_use.py` alone (the use off the list, its rows under `### Retired`, its unbuilt plans cancelled); a plan is its slices, each `Done when` the plan's `doneWhen` verbatim, `Name` the
slice's `name`, `area` the plan's area, `Depends on` chaining them in order, a PRD stub per
piece of work carrying the use as `use:` in its frontmatter, and one capability row per piece of
work under that use in the area's map, its `Ships in` the stub's number, and a `Plain` title on the row and a `plain_title:` on the stub (the rule is [*Plain titles*](../../process/feature-doc-reconcile.md#plain-titles--every-capability-row-and-every-prd-that-is-created-or-changed)) — so the feature page
shows the use as planned the moment the PR merges. Every word is the accepted proposal's — the person may have edited them, and
what they accepted is what is written.

<!-- include: process/feature-flow.md -->

#### The values, and only these

| Column | From |
|---|---|
| `ID` | `python3 knowledge/scripts/validate_id_collisions.py --allocate <slice-prefix> 1`, recorded the way the register records reservations — Step 5's rule |
| `Name` | the idea's **title**, as the brief carries it, verbatim. Not a rewrite: a title that is not yet a noun phrase for what lands is the page's first refinement, and you say so in the sentinel summary |
| `Kind` | the `meta` of the proposal's `new slice` node when it is `feature`, `capability` or `gap-set`; otherwise `feature` |
| `Program` | the `existing` node directly above the `new slice` in `under` — Step 1 checked it resolves. The fragment also carries `area` — the area node in `under` (`area:<slug>`), or, when the proposal names none, the one Step 1 chooses. In `areas` mode the node above is the area and there is no `program`; a program node there is refused by Step 1's sentence. **When the proposal carries `newArea`**, `area` is `newArea.slug` — the `new` area node in `under` — and the map is written first (below) |
| `Done when` | the dossier's `howYouWouldKnow`, **verbatim** — a literal pipe escaped, nothing else touched. If it is more than one sentence, the **first** sentence, and the sentinel summary says so. No judgement is spent here: a tightened observation is an authored one |
| `Verified by` · `Depends on` · `Components` | `—` — each is a decision the page asks for; a guessed proof is worse than none |
| `Disposition` | `adopted`, **when the header carries the column** |

One cell per header column, in the order `slot:slices` gives and no other, exactly as Step 5
says; Step 5's rules on the fragment, the empty cell and the escaped pipe all hold here.

#### A new feature area, when the proposal carries `newArea`

<!-- home -->`FLT-1292` (owner, 2026-10-28): in<!-- else -->In<!-- /home --> a repository that plans by area, route proposes a
**new feature area together with its first slice** when no existing area fits, and the one
accept creates both. The proposal's `newArea` is `{slug, name, sentence, whyNoExistingArea,
components?, brief, uses}`; the person read all of it on the card. **Same branch, same pull request as the
row**, the map first:

```bash
python3 knowledge/scripts/new_feature_area.py --slug "<newArea.slug>" --name "<newArea.name>" \
  --sentence "<newArea.sentence>" --component <id> [--component <id> …] \
  --source-of-truth <path> [--source-of-truth <path> …] \
  --use "<uses[0].name>|<uses[0].paragraph>" [--use "<name>|<paragraph>" …] \
  --brief-json '<newArea.brief as one JSON object>'
```

- **`--slug`, `--name`, `--sentence`** — `newArea`'s own words, verbatim. The sentence is the
  map's `> **Intent.**`; it is not rewritten here.
- **`--component`** — `newArea.components` when the proposal names them; otherwise the
  component that owns each source path below (`python3 knowledge/scripts/component_of.py
  <path>`). Never a component the registry does not hold.
- **`--source-of-truth`** — the **narrowest existing path(s)** the slice's first work extends:
  the code the proposal's `alreadyExists` and the dossier name. A file or a directory that
  exists on `main` today, **never a package root**. A new area whose code is not written yet
  still starts from the code it grows out of when there is such code.
- **A feature with no code yet** (a new product, or a feature nothing in the repository grows
  into — the documents name no path and `component_of.py` finds no owner for anything they
  describe): pass **neither** `--component` nor `--source-of-truth`. The writer then writes
  `components: []` and `source_of_truth: []`, which the checks accept until the first row
  citing built work lands — that change names them. Never invent a component or point at an
  unrelated path to fill them.
- **`--spec`** — omit it: the writer takes the spec the repository's existing maps cite most.
- **`--use`** — one per entry of `newArea.uses`, in order, verbatim.
- **`--brief-json`** — `newArea.brief`, verbatim, as one JSON object:
  `{"summary": "…", "problem": "…", "example": "…", "example_from": ["<journey>"], "not": ["…"]}`
  ([*Writing a feature brief*](../../../process/feature-doc-reconcile.md#writing-a-feature-brief--every-map-that-is-created-or-edited)).
  The writer writes it into the map's `brief:` and refuses (exit `2`) an unknown key, a wrong
  type, ship-state or a bare id in it, or an `example_from` journey that does not exist; never
  hand-edit the brief afterwards. A proposal with no `brief`, or with fewer than three or more
  than six `uses`, is the refusal below: a new map without them fails the repository's check,
  and a brief the person never saw on the card is not written on their behalf.

The writer writes the map (frontmatter with the `brief:`, `# <name>`, the Intent, one
`###` section per use with its paragraph and an **empty** table — capabilities arrive with the
work that ships them) and lists it in the features index. It
prints the files it wrote and exits `0`; it exits `2` with one sentence when the area cannot
be written — a slug that is already an area, no component, a path that does not exist, a
corpus with no feature map yet. **On `2`, write nothing else**: no row, no branch left
behind, and Step 1's `newArea` refusal is the sentinel, carrying the writer's sentence.

Then the row, with `area` set to the new slug, and **`{{target:validate-knowledge}}` over
both together** — the map passes the repository's own checks on day one (its coverage gates
and the freshness contract) or the commit does not land. A red that only a person can settle
(a path the coverage gate wants claimed that the documents never named) is the same refusal.
**Write no owner anywhere**: when the `created` result lands over the merged PR, Fleet makes
the person who accepted the area's first owner itself.

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

**The branch is deterministic from the key**: `agent/shape-<key>`, the key lowercased and
nothing per-run — no slug, no box, no date — so a retry on any box resolves this same branch.
It is the shaping branch, not `slot:git-workflow`'s work-item pattern (an
`agent/<kind>-<key>` branch): a create merges its own planning-only PR, and Fleet's verify check
accepts every create-mission head — `agent/shape-<key>`, `agent/slice-<key>`,
`agent/program-<key>` and `agent/prd-<key>` — so a branch from a command synced before this one
still merges; the run is still gated if the diff touches anything but planning documents. The PR
title carries the key, so the search above finds it. Cut it from a freshly fetched `origin/main`,
create the row fragment, run
`{{target:validate-knowledge}}`, commit. **Then re-check the id against the
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

The same document when the run also created a feature area — the area is the proposal's, which
Fleet already holds, so nothing about it is added here.

`href` is the fleet's own route to the slice's page — `slice:` and the id, nothing else — and
it is where the person is sent next. **What happens next is on that page:** a slice under a program that nobody drives carries a **Start** for just this slice (`POST /api/drive/slice/<id>`), and nothing is built until someone presses it or its program is driven; until then Fleet lists the slice on Needs you as *not started*. Say so in the sentinel summary, so the person is not left waiting on a run that was never asked for. Fleet reads this file, records the idea as *created*,
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
- **The id comes from the allocator, and the row is a fragment.** Ids are permanent and never reused — a shipped PRD may still cite this one. There is no counter to bump: the row lives at `knowledge/slices/rows/SL-NNN.json` and the table is generated from it — `python3 knowledge/scripts/gen_knowledge_registers.py` renders it, and it is never hand-edited.
- **Structure in the register, prose in the detail file, never both.** A detail file carries no frontmatter but `type: slice-detail`; the validator rejects the rest.
- **Progress is gated on proof.** "7 of 7 built" is exactly the reading that reported a program complete while its composed path returned 503<!-- home --> (PRD 0252)<!-- /home -->. Every PRD terminal with no green proof is **awaiting proof**, not done.
- **The active-slice ceiling (`slot:slices`).** Cutting one past it is refused here, not negotiated. The ceiling is what forces sequencing to be a decision.
- **Closing is a matched pair.** A live PRD may not name a completed slice; and a slice cannot read complete while any PRD naming it is still live — which, since completion is derived, happens by construction. **Finish or move the work** — the next need cuts the next slice. Never reopen a closed slice to take new work.
- **`Kind` is required and describes the cut you made** — `feature`, `capability` or `gap-set`. It is what tells a reader why these PRDs are together.
- **Every slice names an area** that resolves, and, in `programs` mode, its `Program` must resolve. The pre-commit validator (`{{target:validate-knowledge}}`) fails the commit otherwise.
- **`Components` entries must resolve** to <!-- home -->`knowledge/specs/architecture/components.md`<!-- else -->`slot:components`<!-- /home -->. Components are durable and carry no ship-state. The column records what the cut spans — it never defines it.
- **Dependencies are between slices** (`Depends on` = `SL-NNN` ids). PRD-level `depends_on:` (PRD numbers) lives in the PRD frontmatter and is a different edge.
- **`Done when` is never left thin, and prose is written where the cut isn't obvious.** The delivery view is only as good as the slice content; a one-word completion condition and no detail file is an empty slice with a row around it.
- **The bar is offered at the cut, never forced.** A `## Bar` is optional and monotone — no bar changes no reading — but the cut is the last moment its criteria can be written *from the promise* instead of reconstructed from what shipped. Offer it once (Step 5c), take "not now" without argument, and never widen or soften a criterion: authorship is the human's, because a bar an agent can widen can never be red.
- **One source of truth:** the PRDs' frontmatter `status:`. Never read tracker state back. No tracker-url / `gh_issue:` fields.
- **From a new feature (`kind: area`): one feature map, no row, in one PR. From a new use (`kind: use`): one `###` section on the feature's map, no row, in one PR. From a removal (`kind: removal`): the use off the map, its rows retired and its unbuilt plans cancelled, nothing deleted, in one PR. From a plan: its rows and their PRD stubs, in one PR.** The words are the accepted proposal's; nothing is invented beyond them.
- **From a brief with `newArea`: one feature map and one row, in one PR.** The map is the writer's minimal one plus the proposal's own feature brief and uses — no capability, no journey, no surface invented — and the area is real only once that PR merges.
- **From a brief: one row, no interview, no tracker.** The name is the idea's title, the `Done when` is the dossier's own observation, the kind and the program are route's placement, and every other cell is `—`. What a person did not see on the idea's page is not written into a permanent register on their behalf; the slice's page asks for it next.
