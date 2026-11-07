# <!-- home -->Zetify<!-- /home --> Slice — Refine (a cut from a brief becomes a real one, on the fleet)

You turn a **slice that is only a row** — a name, a kind route placed, a `Done when` lifted
verbatim from an idea's dossier, `—` in `Verified by`, `Depends on` and `Components`, no
detail file, no bar — into a real cut: a `Kind` the person chose, a `Done when` somebody can
go and check, the promise rows and refusals of the ground it touches, a detail file that says
why these things ship together, and — where the promise lives in a running system — a
digest-bound `## Bar`. That is what [`slice:create`](create.md) Steps 2–5c produce with a
person at a terminal, under the refusals [`slice:edit`](edit.md) Step 3 applies to an
existing row, and **this command is that interview, run headless**: the same discovery, the
same forks, asked by writing through the fleet's question channel and answered on the
slice's own page, landed as one merged PR.

**Before you write a slice file, read its docs page** (under `.fleet/docs/`; `read_doc <page>` when Fleet's tools are in the session): `knowledge-base/slices`.

**You are a composition, not an authority.** What a slice is, what its columns mean, how a
promise becomes a register row and how a bar is written all live in the two commands above
and in the entity model `slot:entity-model` names, and this file cites them rather than
restating them: the discovery is `create.md` → *Step 2*, the promise and refusal rows are
*Step 3*, the frame is *Step 4*, the row and the detail file are *Step 5* and *Step 5b*, the
bar is *Step 5c*; the guarded edit's refusals — narrow or correct, never widen; never rewrite
a finished cut's promise; never widen a bar — are `edit.md` → *Step 3*. What this file owns
is the **mapping**: which of their questions become cards in which of the two rounds, which
the run decides and reports, and which are withheld.

**It has a second, quieter mode — the stub.** When the dispatch's `## Shaping` block says
`step: stub`, the cut has *already* been refined and holds no CAPABILITY PRD — none at all, or only
its program's own composed proof (the `Verified by` PRD, which demonstrates the ground rather than
being part of it) when that proof claims no commitment of its own (`implements:` empty) — and the fleet's drive is asking for the one thing the ladder was missing: the
cut's **PRD stub**. That mode asks nothing, runs no round and writes no cell of the slice — it writes
one numbered `status: stub` PRD under the cut, carrying only what the cut already promised, and lands
it by PR (Step 2b). Everything in Steps 3 and 4 is the interview and does not run in that mode.

**And a third — the apply.** When the block says `step: apply`, a person has *already answered* a question about
this cut and the answer is a register edit; the fleet's drive asks you to make it, so the person is not asked
again and no task is parked for them. The block's `before.decision` is the recorded answer. That mode asks
nothing, runs no round and edits **only** the cut's `Verified by` or `Disposition` cell — never its promise
(Step 2c). Steps 3 and 4 do not run in that mode.

**Headless only.** A person at a terminal has `slice:create` — which creates *or updates*, so
it is this same interview whether the cut exists or not — and `slice:edit` for the narrower job
of changing one guarded cell on a row that is already right. The fleet routes a mission by
command string, so this verb exists for the button and nothing else (Step 0).

The slice to refine: $ARGUMENTS

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps`
> block below and create **one todo per step**, in order; mark each `in_progress` on entry and
> `completed` on exit. The interview step is a bounded loop — add one todo per round under it.
> No step writes a `status:` or a date, and none may be added that does — a slice's
> completion is computed from its member PRDs and its proof. The prose steps below are the
> authority; this spine indexes them.
>
> **`needs: answers` · `may merge: true`** ([`spine.md`](../../../process/spine.md)) — this
> command is dispatched headless and asks **by writing**, which is why `needs: answers` still
> dispatches: the fleet refuses only `needs: a decision`, a command whose whole product is a
> ruling. It must never *block* on a human. **`AskUserQuestion` is not available to
> you and never will be.** Your escalation path is a `questions` result file plus the end of
> your turn, and the answers come back by resumption of this same session — the shared
> contract inlined under *The headless contract* below. `slice:edit` is `needs: a decision`
> because a headless lane answering its forks *by default* is how a register acquires
> plausible content nobody checked; this command answers none of them by default — every one
> is a card the person answers, and an unanswered one stays open.

```json
{
  "command": "slice-refine",
  "tier": "core",
  "sop": "none",
  "needs": "answers",
  "may merge": true,
  "intent": "Refine a slice cut from a brief on the fleet: one discovery round with no options, one fork round — the kind, the sharpened Done when, the promise rows, the bar — through the fleet's written question channel, then write the row, the register rows, the detail file and the bar exactly as slice:create would at a terminal and slice:edit would allow — by one merged PR and one landed result, with no status and no dates.",
  "loads": ["process-shaping-headless", "slices", "planning-model", "entity-model"],
  "requires": [
    "process-spine", "process-interview", "process-shaping-headless", "slices", "programs",
    "commitments", "entity-model", "planning-model", "gate", "git-workflow"
  ],
  "optional": ["product-vision", "components", "feature-areas", "feature-maps", "file-conventions"],
  "steps": [
    {"id": "mode",       "name": "Which way in — the fleet, or a terminal (refused)",           "kind": "decision", "actor": "coordinator",                 "body": "step-0-which-way-in"},
    {"id": "read",       "name": "Read the slice, its program, its members and its ground",     "kind": "io",       "actor": "coordinator", "consumes": ["requirement-register"], "body": "step-1-read-the-slice"},
    {"id": "refusals",   "name": "The refusals — by sentinel, before any question",             "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "step-2-the-refusals"},
    {"id": "stub",       "name": "Stub mode (`step: stub`) — no rounds: one numbered PRD stub under a refined cut", "kind": "author", "actor": "coordinator", "produces": ["prd"], "body": "step-2b-stub-mode"},
    {"id": "apply",      "name": "Apply mode (`step: apply`) — no rounds: carry out the recorded answer by editing the cut's `Verified by` or `Disposition`", "kind": "author", "actor": "coordinator", "produces": ["requirement-register"], "body": "step-2c-apply-mode"},
    {"id": "rounds",     "name": "The rounds — discovery, then the forks",                      "kind": "loop",     "actor": "coordinator", "loop": {"max_rounds": 2, "exit": "the person answered the fork round, or the ceiling was reached and what stands is written with its open items"}, "body": "step-3-the-rounds"},
    {"id": "author",     "name": "Write it — the row, the register rows, the detail file, the bar", "kind": "author", "actor": "coordinator", "produces": ["requirement-register"], "body": "step-4-write-it"},
    {"id": "land",       "name": "Land it — the branch, the PR, the merge",                      "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "step-5-land-it"},
    {"id": "landed",     "name": "The landed result, then the sentinel",                           "kind": "io",       "actor": "coordinator",                 "body": "step-5-land-it"},
    {"id": "report",     "name": "Report",                                                        "kind": "author",   "actor": "coordinator",                 "body": "step-6-report"}
  ]
}
```

---

## What to do

### Step 0: Which way in

```bash
printf '%s\n' "${FLEET_RESULT_FILE:-<unset>}"
```

- **Set** → the fleet dispatched you on a slice the page asked to have refined.
  `$ARGUMENTS` is its register id (`SL-NNN`), the mission's `## Shaping` block carries the
  requester, any instruction and the row as served, and the payload says which round this
  is — *The headless contract* §1. Read the block's `step`: **`stub`** → Steps 1, 2 and 2b, then
  Step 6's report; **`apply`** → Steps 1 and 2c, then Step 6's report (Step 2's refusal of a finished cut does not apply — see 2c); anything else (`shape`, or no `step` — a block written before the field) →
  Steps 1–6 as written, the interview.
- **Unset** → a person is at a terminal, and this is the wrong verb for them. Say exactly
  this and stop, writing nothing: **This command runs only on the fleet. At a terminal, run
  `/zetify:slice:create SL-NNN` instead** — it is this same interview with you in the room,
  on the same cut, and it creates *or updates*, so an existing row is what it expects.
  **Not `slice:edit`**: that changes one guarded cell of a row (`Verified by`, `Depends on`,
  `Done when`, `Disposition`) and refuses the rest, so it cannot pick a `Kind`, cannot write
  the promise rows and refusals, and cannot author the detail file — most of what you were
  dispatched to do. It is a real verb for a real job; it is not this job, and offering it
  here sent people to a narrower command wearing this one's name.
  **And say that the terminal is not a one-way door.** A person who starts by hand and
  would rather the fleet finished it presses **Shape this** on the entity's own page (the
  `start` action — the same button that would have dispatched this command), and the next
  round picks up from whatever is committed: the register row, the detail file, the answers
  already written down. Being sent to a terminal must never read as being sent there *for
  good*.
- **Set, but `$ARGUMENTS` is not a slice id, or the block's `kind` is not `slice`** → a
  mis-dispatch. Write nothing; sentinel `failed` naming what was wrong; stop.

### Step 1: Read the slice

`edit.md` Step 1, exactly — every cell of the row in `slot:slices`, the detail file if one
exists and whether it carries a `## Bar`, the member PRDs (`slice: SL-NNN` in a PRD's own
frontmatter is the only place membership is written) with each one's `status:`, the
program's row in `slot:programs` with its `Verified by` and `Disposition` (a slice with an
`area` and no `program`<!-- home -->, decision 2026-10-27, `FLT-1280`,<!-- /home --> has no program row: read its feature map
instead, and every "program" check below reads as passed). **A row with no `area` gets one in this
run** — the feature map that owns the cut, by its components and Intent; ask when two fit — and derive the
three readings that decide what is allowed: **live**, **all-terminal**, **abandoned**.

Then the ground, so no card asks what a file answers:

1. **The register for this cut** — `create.md` Step 3 items 1–4: resolve the slice's ground
   through the component index `slot:commitments` gives, never guess a filename; read what
   is already promised there; sweep every other register with
   `python3 knowledge/scripts/requirement_query.py neighbours` for conflicts, reading the
   `excluded` hits loudest. **No register covers the ground → the run opens one** (Step 3
   item 2 reverses the old deferral), naming its prefix and domain deliberately, and
   `landed.changed.requirements` says so.
2. **The vision** (`slot:product-vision`) — the personas by label, for Round 1's *who* card.
3. **The proposed sharpening.** From the row's `Done when` — the dossier's own observation,
   verbatim, as the brief wrote it — draft the sentence somebody could go and check. It is a
   *proposal* for Round 2, not a decision: `edit.md` Step 3's rule binds it — narrow or
   correct, never widen — and a sentence that widens the promise is not offered.
4. **Is the promise observable only in a running system?** `create.md` Step 5c's question,
   answered by the run from the sentence: an environment, a live connection, a person doing
   something in the product, a deploy that serves, a signal that is read. The answer decides
   which bar card Round 2 carries.
5. **The originating brief.** When the cut was made from an idea, the mission carries a `## Brief`
   block beside `## Shaping`: the idea's nine-field dossier and the rounds its filer already
   answered in the intake interview (`from` names the filing). It is **evidence the person already
   gave** — read it whole, the way `prd:fill` reads a stub's `## Brief`. The row
   keeps only a name and a `Done when`, so a distinction the filer drew (two things that need
   different settings, say) survives *only* there. No `## Brief` block means the cut came from no
   idea; Round 1 then runs as written.

   **Whose words these are.** Only an answered round's text (the filer's own answers) and the
   dossier's `problem` are the filer's words: quote those as "the filer said". Every other dossier
   field (`whoItIsFor`, `whatTheyDoToday`, `displaces`, `howYouWouldKnow` and the rest) is the intake
   agent's synthesis: cite it as "the intake summarised: …", never as the filer's words.

### Step 2: The refusals

By sentinel, before any question, in the form *The headless contract* §9 gives:

- **No row resolves** for the id → `failed`, a mis-dispatch. Cutting a slice is
  `/zetify:slice:create`; this command never creates a row.
- **All-terminal** — every member PRD terminal, at least one shipped → `needs-decision`:
  **this cut is finished; a scope change is a new cut**, with a `Depends on` edge back to
  this one — `edit.md` Step 4's fork, which a headless run does not settle and does not
  need to: *"cut the new slice from the program's page; this one keeps the promise it was
  finished against"*.
- **The program's `Disposition` is not `adopted`**, or the slice's own is not →
  `needs-decision`: *"this cut is out of the plan with its program; reinstate it first, or
  leave it"*.
- **Abandoned** — every member cancelled → `needs-decision`: *"every PRD in this cut was
  cancelled; withdraw the cut citing a decision record, or cut afresh"*.

A live slice, or one with no member yet — the ordinary case for a cut from a brief — goes on.

### Step 2c: Apply mode — a recorded answer carried out (no rounds)

**Only when the block says `step: apply`.** A person answered a question about this cut (`before.decision`:
`question`, `answer`, `then` — what the answer says happens —, `answeredAt`, `answeredBy`, `owed` — what the cut's
proof still owes), and the program's board still reads the cut as a step only a person can take. The answer is the
decision; **you carry it out and ask nothing**. Never ask the decision again, and never write a card: the whole
point of this mode is that an answer already given is not asked for twice.

**What you may write — two cells, and only to say what the answer says.**
- `Verified by`: name the proof the answer chose (a PRD number, a `drill:<stem>`), record that it is owed
  until a reading is taken (the register's `owed:` spelling), or record why none is needed — exactly as
  `edit.md` Step 3 allows, with its refusals: **narrow or correct, never widen**.
- `Disposition`: waived, withdrawn or excused, citing the decision record when the register's guard asks for one.

**What you never write:** `Done when`, `Depends on`, the promise rows, the bar, a `Kind`. Those make or change a
promise, and an agent may never promise something new. If the answer can only be carried out by editing one of
them, write nothing and say so (below). The cut's finished promise is never rewritten to fit what shipped.

**What the answer cannot do — and the two endings that are not an edit.** Tell them apart by the answer's own
*condition* ("close once an operator has taken the readings", "name the proof after the drill"):

- **The condition is NOT met, and meeting it needs a person's hands** — a live production reading no agent can take,
  a drill on a real deployment. Not an edit: write nothing, land with `changed.applied: []` and the exact steps in
  `open`, each a sentence a person can act on without reading anything else. The fleet files that as the cut's
  `Blocked · action` ticket. **Check first that it is not already met**: read the tickets and landings that carry
  the reading (the cut's detail file, the issues the drive filed for it, their comments) before you call it open.
- **The condition IS met, and the outcome contradicts what the answer assumed** — the readings were taken and came
  back RED, the drill failed, the proof named no longer exists. Nobody is owed an action: the person's part is done,
  and what is open is a **decision given the evidence**. Do not edit, do not write `open` steps, and **never ask the
  person to do again what they did**. End `needs-decision` with ONE `questions` result (the fleet's written
  channel), its question carrying `about: ["SL-NNN"]` and, in the prompt, **the evidence in plain words** — what
  was measured, when, by whom, and what that result means for this cut — then two to four options with your
  recommendation first and marked (fix and re-take; close on a written waiver citing the result; leave it open). The
  answer is a card in the person's cockpit; when they pick, you resume in this same session and make the edit the pick
  says.

**The refusals, by sentinel, with no result file.** Step 2's refusal of an **all-terminal or finished** cut does *not* apply here: a finished cut that owes a proof is exactly what this mode is for, and the promise it was finished against stands untouched. A **withdrawn**, **abandoned** or **closed** cut (its program is) is refused as Step 2 refuses it, `failed` naming which. This mode adds: the block carries no
`before.decision` → `failed` ("an apply was asked for with no recorded answer"); the answer contradicts the row as
it now stands (the cut is already complete, or the proof it names does not exist) → `needs-decision`, the
contradiction in one sentence, because a stale decision is a new question and not yours to settle.

**Land it** as Step 2b lands a stub, with these differences. The branch is `agent/apply-<key, lowercased>`; the PR
title carries the key and says it carries out a recorded decision, naming its date and who gave it; and the PR body
quotes the answer verbatim and says in one sentence why it needs no human before it merges: **it makes the edit a
person already chose, adds no customer-facing functionality, and touches only `Verified by` or `Disposition`.** Then
the `landed` document, a slice's, with this mode's one `changed` key:

```json
{"kind": "landed", "landed": {"kind": "slice", "id": "SL-NNN", "href": "slice:SL-NNN", "pr": "<the merged PR's URL>", "files": ["<the register file edited>"], "summary": "<one sentence: the edit, and the answer it carries out>", "changed": {"applied": ["verifiedBy"]}, "open": []}}
```

`changed.applied` lists the cells written (`verifiedBy`, `disposition`); `[]` with a non-empty `open` is the
"needs a person's hands" ending above.

### Step 2b: Stub mode — a refined cut with no PRD (no rounds)

**Only when the block says `step: stub`.** The fleet asked for this because a driven program
holds a cut that was refined and has no CAPABILITY PRD — none at all, or only the program's composed
proof — and the next steps of the pipeline —
`prd:fill`, then `prd:blueprint` and `prd:plan` — need a stub to start from. **You ask no
question, run no round, and write no cell of the slice, no register row and no bar.** The
commitment was made when the cut was refined and the program started: this run decomposes what
the cut already promised into its first PRD and adds **no customer-facing functionality**
(the repository's always-on rules: an agent may build what the product already promised, and may never promise
something new). A number, a home and a brief — `prd:create` Phase 6's own rule for what a stub
is, and nothing else.

**The refusals, by sentinel, with no result file** (*The headless contract* §9) — Step 2's all
still apply, and these three are this mode's:

- **The cut already has a capability member PRD, of any status** → nothing to write, and that is not a
  failure: sentinel `success`, `pr: ""`, **no result file**, the summary saying which PRD is
  there. The fleet records the settled landing itself. Never a second stub for a cut. **The program's
  own composed proof is NOT a capability member while it claims nothing** — its number is the program
  row's `Verified by`, and a cut holding only that PRD (and no other) with an empty (or absent)
  `implements:` is exactly the case this mode is for, so it is stubbed. **A composed proof whose
  `implements:` names any commitment IS the cut's capability member**: it is
  doing the cut's work as well as demonstrating the program, so nothing is written, as above. The fleet
  does not ask for a stub over such a cut, so meeting one here means the corpus moved after the ask.
- **The cut was never refined** (its row has no `Done when`, or its detail file has neither a
  `## Bar` nor any refine's text) → `needs-decision`: *"this cut has not been refined; refine
  it before a PRD is cut for it"* — a stub for an unrefined cut is a PRD invented from a
  sentence nobody sharpened.
- **The active count is already at the ceiling** → `needs-decision`, as `prd:create` Phase 6
  refuses it, in the same sentence (close a cut, or withdraw this one): a stub is live, so this
  cut would be the one over.

**The number.** `python3 knowledge/scripts/validate_id_collisions.py --allocate PRD 1` — it
reserves the number atomically as a claim ref, which a hand-read of the highest folder cannot.
Never a number you picked.

**The file** — `knowledge/prds/NNNN-<slug>/prd.md`, the slug from the title: the frontmatter
`prd:create` Phase 6 gives (`type`, `prd`, `title`, `status: stub`, one `status_history` line
with `by: prd`, `slice: SL-NNN`, `date`, `author`, `source_ideas: []`) and **no other key** —
no `implements:`, no `priority:`; those are the fill's to decide. The `title` is the slice's
`Name` verbatim and `author` is `fleet`. The body is Phase 6's: a title line, the one status
note, and a `## Brief` **assembled from the cut's own files and quoted, never paraphrased** — a
stub that smooths its evidence has pre-empted the interview that reads it:

- **Done when** — the slice row's cell, verbatim.
- **Bar** — each criterion of the detail file's `## Bar`, one line each, verbatim; *none
  authored* when it has none.
- **Already promised** — every register row whose `Source` cites this cut's detail file (find
  them by searching the registers `slot:commitments` names for the slice id, then
  `python3 knowledge/scripts/requirement_query.py row <ID>`), as the id and its statement in
  quotes; *none* when no row cites the cut. **This is how the stub carries the requirements the
  cut promised: the ids ride in the Brief and the fill claims them in `implements:`** — a stub's
  frontmatter has no such key.
- **Excluded** — the cut's `Kind: excluded` rows, the same way.
- **The detail file** — its path, so the fill reads the cut's own reasoning.

Nothing else: no requirement of your own, no acceptance criterion, no journey, no scope ledger,
no feature-map row, and **no second stub** — one PRD for the cut. A cut whose promise plainly
wants two PRDs is split by the fill and the design, where the interview is. Anything you notice
that the cut did not promise goes in the landing's `open` list, never into the stub.

**Land it** as Step 5 lands a refine, with these differences. **The prior attempt is found by
branch, not by key** — the key also names the refine that merged earlier, and reading that as
*"the work is on `main`"* would end the run with nothing written:

```bash
gh pr list --state all --head "agent/stub-<key, lowercased>" --json number,state,url
```

**The branch is `agent/stub-<key, lowercased>`**, the PR title carries the key and says it is a
stub, and the allocated number is re-checked at push (Step 5's check). **The PR body says in one
sentence each why it needs no human before it merges:** it adds no customer-facing functionality
— it decomposes the promise the cut already makes — so it is not the commitment `check` reserves
for a person; and it is a `status: stub` file, which the scope validators exempt by
construction. Then the `landed` document, a slice's, with this mode's one `changed` key and the
stub's path in `files`:

```json
{"kind": "landed", "landed": {"kind": "slice", "id": "SL-NNN", "href": "slice:SL-NNN", "pr": "<the merged PR's URL>", "files": ["knowledge/prds/NNNN-<slug>/prd.md"], "summary": "<one sentence: the PRD stub now under the cut>", "changed": {"prds": ["NNNN"]}, "open": ["<each thing noticed and withheld>"]}}
```

The sentinel is `success` with the PR URL; `partial` with no `landed` file when the PR could not
be brought to merge in this run, so the next dispatch resumes the branch rather than minting a
second number (§8).

### Step 3: The rounds

**Not in stub mode** — Step 2b runs no round. Two rounds at most, at most four questions each, every one shaped by the rail in *The
headless contract* §3 — which is the interview card applied to a written medium:

<!-- include: process/interview-card.md -->

Each round's brief opens with which round this is of up to two, restates what the row
already says in plain words, and says what the round settles.

**The aspect each card changes** (*The headless contract* §3): Round 1's discovery cards name
none, except *What this is deliberately NOT doing* → `excluded`. In Round 2, *`Done when`* →
`doneWhen`, the bar card → `bar`, *`Kind`* → `kind`, each promise card → `promises`, and
*`Verified by`* → `verifiedBy`. Round 2 is the last round, so it is the one marked
`"confirm": true`, and its `draft` carries every cell Step 4 will write.

#### Round 1 — discovery, with no options (`create.md` Step 2)

`create.md` Step 2 exists because its absence has a measured shape — a confident `Done when`
lifted from an unrelated journey and never stated by the requester — and the interview
protocol's discovery rule says a menu inverts here. So Round 1 is **discovery**: three of
its four cards carry `"options": []` and `allowFreeText: true`, which the service accepts
only in that pairing, and the one that names personas offers them only because the vision
already names them — with free text for anyone it does not. The four questions are Step 2's,
in its order:

| Card | What it establishes | Options |
|---|---|---|
| **What happens today** | what somebody actually does when they need this, and what it costs them — one concrete sentence about a real person | **zero** — free text |
| **Who hits it, and how often** | the persona, which is an answer and never an assumption | 2–4 personas from `slot:product-vision` by their plain labels, one recommended from the brief's own *who it is for*; free text for a person the vision does not name |
| **What this is deliberately NOT doing** | the exclusions that become `Kind: excluded` rows in Step 4 rather than a paragraph nobody can cite | **zero** — free text |
| **What people will assume it does, that it will not** | the gap the next argument comes from | **zero** — free text |

**A card the `## Brief` already settles is not asked** (Step 1.5; the filer should never have to
repeat themselves). A card counts as settled only when the dossier or an answered round states
what that card establishes — *what happens today* from `whatTheyDoToday`,
*who* from `whoItIsFor`, the exclusions from `displaces` or an answered "not doing" line. For each
settled card: do not build it, **record it as settled from the intake** (the
sentence, and which field or round it came from; quoted as "the filer said" only from an answered round or
`problem`, and cited as "the intake summarised: …" from any other dossier field), and carry the quote into the Round 2 brief and
`draft` so Step 4 writes it (the problem in the person's words, the `excluded` rows). A card the
brief only touches, or answers in a way that contradicts the row, is still asked — and says what the
brief gave so the person corrects rather than restates. If all four are settled, **Round 1 does not
run**: go straight to Round 2, and say in its brief that the discovery came from the intake. The
`## Brief` never replaces the fork round: the forks are decisions the intake did not make.

Then STOP: write the `questions` result, the sentinel `needs-decision`, end the turn. **The
test for leaving this round is Step 2's**: you can say what somebody does today without
this, in their words. If the answers do not give you that, the fork round still runs —
there is no third round — and the cards it cannot honestly build are not built; what they
would have settled goes to `open`.

#### Round 2 — the forks (`create.md` Steps 3.5, 4 and 5c; `edit.md` Step 3)

On resume, consume Round 1 (*The headless contract* §4). Now the alternatives are real, and
each card is a fork — 2–4 options, one recommended, rationale on each. Four slots; they are
filled in this priority, and what does not fit is decided by the run's default below and
named in `open`:

1. **`Done when`** — the sharpened sentence from Step 1.3, corrected by what Round 1 said:
   *accept it* (recommended), *one alternative* the run can name, free text. `edit.md`
   Step 3's rule on every option: narrow or correct, never widen, and the current cell's
   exact bytes are shown so the person sees what moves.
2. **The bar** — one card, and which one Step 1.4 decided:
   - **the promise lives in a running system** → the run **must** propose criteria
     (`create.md` Step 5c: this is the best moment there will ever be), and the card is
     *ratify the bar*: the criteria named in the card, each stating its own RED and its
     probe (or *No probe yet* and why) — *accept them as drafted* (recommended) / *edit
     them* in free text. *"Not now"* is not an option Step 5c accepts for this shape of cut,
     so it is not offered.
   - **corpus-observable** → *bar now / not now*, **not now recommended**, because a bar
     reconstructed later is worthless but a bar written to have written one is worse.
   The run never widens a criterion and never invents a probe.
   **The checks ship as a list, never as a sentence.** The bar card's `draft.bar` is an **array of
   strings**, one check per entry, each stating its own RED and probe — that array is what the page
   numbers under "The checks you are approving". Never leave them only as a semicolon run inside
   `prompt`: a person asked to "accept all four" must be able to find the four. An option that
   drops some of them (*accept three and leave the conversation out*) **names which ones in its
   `label` and `becomes`**, quoting the dropped check's own words, never "the last one".
3. **`Kind`** — `feature` / `capability` / `gap-set`, one recommended — **only when Round 1's
   answers contradict the cell** route placed. Otherwise the cell stands and the run says
   so; a card that asks a person to re-confirm what the brief already settled is a card
   that teaches them to skim.
4. **The promise rows** — `create.md` Step 3 item 5, *promises, not mechanisms*: each
   candidate promise the ground read and Round 1 surfaced is a **two-option card** —
   *promise it* (recommended) / *not this cut* — the strongest first, filling the slots
   that remain of the four. Every candidate beyond that lands `Disposition: open` unasked
   (that state is exactly *not settled yet*) and is named in `open`. Exclusions come from
   Round 1's own words and need no second card.

**`Verified by`** is a card only when a member PRD exists to name — the ordinary cut from a
brief has none, the cell stays `—`, which is the honest *unproven* reading, and no proof is
guessed. **`Depends on`** is never asked: `edit.md` Step 3 says an edge is checked, never
backfilled, and the run writes one only for an ordering a member PRD's own `depends_on:`
already implies.

**At the ceiling — two rounds asked, or an answer missing — write what stands** (Step 4).
An unanswered `Done when` card leaves the cell as it was; an unanswered bar card writes no
bar and, for a running-system cut, says in `open` that the promise is unobserved; an
unanswered promise card lands its row `open`.

### Step 4: Write it

Only after Round 2's answer, or at the ceiling. Everything here is authored **exactly as the
attended commands say**, cited, never restated:

1. **The row fragment** — `create.md` Step 5's fragment at
   `knowledge/slices/rows/SL-NNN.json`, `edit.md` Step 5's discipline: touch only the
   cells this run settled — `Kind` if answered, `Done when` as accepted (a literal pipe
   escaped), `Verified by` only if a member proof was named; `Depends on`, `Components`,
   `Program`, `Name` and `Disposition` untouched, and `area` only ADDED to a row that has none — never changed. **Never write a status on a slice** —
   completion is computed, and no column holds one; never a date either.
2. **The register rows** — `create.md` Step 3 item 6: every accepted promise appended as
   `Disposition: open` with its id from the register's counter, bumped in the same change;
   `Source` citing the detail file by quoted phrase, never a line number; `Needs` edges
   written with the rows; each `Statement` worded to
   [*Wording a promise*](../../../process/knowledge-bootstrap-formats.md#wording-a-promise--every-capability-rule-and-criterion).
   Every exclusion the person named as a row of its own,
   `Kind: excluded`, `Disposition: adopted`. A register the ground lacked, opened as Step 3
   item 2 says. Report both halves of the count in the landing's summary — *promises n new
   things, re-uses m, refuses k*.
3. **The detail file** — `create.md` Step 5b: the name, one value-led sentence, a few short
   paragraphs — the problem in the person's Round 1 words, the shape, the outcome, and what
   the cut deliberately excludes. No frontmatter but the type header `slot:file-conventions`
   gives; no checkbox and no `(status)` beside any PRD number it happens to name.
4. **The bar** — when the person ratified one: `create.md` Step 5c's shape, appended to the
   detail file (written first if item 3 decided against one), the criteria **as the person
   accepted or edited them** — never widened on the way in — and the digest computed with
   the repository's own implementation after the row is written, never by hand:

   ```bash
   python3 knowledge/scripts/fleet.py digest -k knowledge <slices-register> SL-NNN
   ```

   A `Done when` that moved and a bar that already existed move together, in this change,
   as `edit.md` Step 3 requires — every criterion re-read against the new sentence, then
   the digest recomputed.
5. **Withheld, and reported in `open`** — a `Depends on` edge nobody checked, a component
   this cut spans that the registry does not carry, a proof for a cut with no member PRD,
   and every promise the four cards could not hold. No tracker write of any kind: the slice
   is a label the projection reconciles after the merge.

Then `{{target:validate-knowledge}}` clean, and — whenever the detail file or the `Done when` cell
moved — the `bars` check clean too:

```bash
python3 knowledge/scripts/fleet.py check --only bars --repo .
```

A stale-digest finding is never cleared by re-blessing the hash: re-affirm the criteria.

### Step 5: Land it

*The headless contract* §6, unchanged: the prior attempt found with `gh pr list --search`,
the deterministic branch `agent/shape-<key>`, **the PR's identity** (shaping content only; the tracker key in the title
when the entity has one — what the `Verify Gate` reads), every register id re-checked against the tip
at push, `gh pr merge --auto --squash` armed the moment the PR opens, and the
PR driven to `state: MERGED` (`queued` is pending, `ejected` from the merge queue is red CI — the contract's `gh_pr_merge_state.py` watch) — the slice register is touched by nearly every knowledge PR,
so a second conflict after a confirmed green is normal here and is resolved by taking the
other row and yours.

Once merged, the `landed` document to `$FLEET_RESULT_FILE`, written whole and read back —
§7's shape with a slice's `changed`:

```json
{"kind": "landed", "landed": {"kind": "slice", "id": "SL-NNN", "href": "slice:SL-NNN", "pr": "<the merged PR's URL>", "files": ["<every path the PR changed>"], "summary": "<one plain sentence: what the cut now promises>", "changed": {"doneWhen": "<the cell as written>", "kind": "<feature | capability | gap-set>", "bar": true, "requirements": ["<each register id appended>"], "verifiedBy": "—"}, "open": ["<each unsettled or withheld item>"]}}
```

`bar` is `true` only when a `## Bar` was written or re-affirmed; `requirements` lists every
row appended, exclusions included; `verifiedBy` is the cell as written. Then the sentinel:
`success` with the PR URL. A PR that could not be brought to merge in this run is `partial`
with the PR URL and **no `landed` file**, so the next dispatch resumes the branch — §8's
table, and never `done`.

### Step 6: Report

Nine lines, for a human reading the transcript: the id and its program; the reading (live /
all-terminal / abandoned, and the active count `n/<ceiling>`); the rounds asked and
questions spent (`n of 8 across r rounds`); each cell's before → after; the promise count in
both halves; whether a bar was ratified, declined or not applicable — a declined offer on a
corpus-observable cut is a legitimate answer and not a residual; what was withheld; the PR and
its state; the result written and the sentinel word.

---

## The headless contract (shared)

<!-- include: process/shaping-headless.md -->

---

## Rules

- **Cite, never restate.** The discovery is `create.md` Step 2, the promise rows Step 3, the
  frame Step 4, the row and the detail file Steps 5 and 5b, the bar Step 5c; the refusals are
  `edit.md` Step 3. This file maps their questions onto two rounds; it owns none of their
  rules.
- **Never write a status on a slice, and never a date.** Completion is computed — every
  member PRD terminal and the proof shipped — every time anyone reads it.
- **Discovery before forks, and the discovery has no menu.** Round 1's cards carry zero
  options; a fork offered before the person has said what happens today is the run's guess
  laundered into a requirement.
- **Narrow or correct, never widen** — the `Done when`, and the bar. A finished cut's
  promise is never rewritten: that is a new cut, refused by sentinel. An agent may sharpen a
  bar and never loosen one; a bar the person did not ratify is not written.
- **Promise rows are born `open`; exclusions are rows, not paragraphs.** A candidate the
  cards could not hold still lands `open` and is named in `open` — that state is the
  legitimate *not settled yet*.
- **Never guess a proof, never backfill an edge, never mint a component.** Each is withheld
  and reported.
- **No tracker write, no `AskUserQuestion`.** The slice is a label the projection reconciles
  after the merge.
- **Headless only.** A terminal is refused in one sentence naming `slice:create`, the attended
  twin — never `slice:edit`, which is one cell, not this interview.
