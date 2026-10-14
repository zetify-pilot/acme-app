#  Program — Shape (a skeleton row becomes a shaped program, on the fleet)

You turn a **program that is only a row** — a name, a kind, `—` in every other cell, no
narrative — into a shaped one: a literal title and a headline with an example, the six
narrative paragraphs, a composed proof named in `Verified by`, the decomposition's gap rows
and `Needs` edges, `Requires` filled with the roots, a decomposition record, and two to four
slices cut by what ships together. That is exactly what
[`program:create`](create.md) Steps 2–3b and [`program:decompose`](decompose.md) Phases 0–7
produce with a person at a terminal, and **this command is those two, run headless**: the
same questions, asked by writing through the fleet's question channel, answered by the person
on the program's own page, and landed as one merged PR.

**You are a composition, not an authority.** Every rule about *what* a program is and *how*
it is written lives in the two commands above and in the entity model `slot:entity-model` names,
and this file cites them rather than restating them: the voice rule is `create.md` →
*Step 2b*, the narrative skeleton is *Step 3b*, the register's columns and refusals are
*Step 3*, the vision gate is `decompose.md` → *Phase 0*, the research is *Phase 3*, the
buckets are *Phase 4*, the write-back and the cuts are *Phase 7*. A sentence copied out of
either into this file is the copy that drifts. What this file owns is the **mapping**: which
of their questions become cards in which round, which the run decides and reports, and which
are withheld.

**Headless only.** The person who wants this attended has a richer command for it — the
seven-phase working-backwards conversation with research fan-outs — and the fleet routes a
mission by command string, so this verb exists for the button and nothing else (Step 0).

The program to shape: $ARGUMENTS

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps`
> block below and create **one todo per step**, in order; mark each `in_progress` on entry and
> `completed` on exit. The interview step is a bounded loop — add one todo per round under it.
> No step writes a `status:` or a date, and none may be added that does — a program's
> ship-state is derived from its slices. The prose steps below are the authority; this spine
> indexes them.
>
> **`needs: answers` · `may merge: true`** ([`spine.md`](../../../process/spine.md)) — this
> command is dispatched headless and asks **by writing**, which is why `needs: answers` still
> dispatches: the fleet refuses only `needs: a decision`, a command whose whole product is a
> ruling. It must never *block* on a human. **`AskUserQuestion` is not available to
> you and never will be.** Your escalation path is a `questions` result file plus the end of
> your turn, and the answers come back by resumption of this same session — the shared
> contract inlined under *The headless contract* below.

```json
{
  "command": "program-shape",
  "tier": "core",
  "sop": "none",
  "needs": "answers",
  "may merge": true,
  "intent": "Shape a skeleton program on the fleet: ask the framing, the edges and the proof-and-cuts through the fleet's written question channel over at most three rounds, then write the narrative, the gap rows and edges, the roots, the proof and the cuts exactly as program:create and program:decompose would at a terminal — by one merged PR and one landed result, with no status and no dates.",
  "loads": ["process-shaping-headless", "programs", "product-vision", "entity-model"],
  "requires": [
    "process-spine", "process-interview", "process-shaping-headless", "programs", "slices",
    "entity-model", "product-vision", "gate", "git-workflow", "file-conventions"
  ],
  "optional": [
    "planning-model", "feature-maps", "feature-areas", "components", "commitments", "journeys",
    "domain-model", "architecture"
  ],
  "steps": [
    {"id": "mode",       "name": "Which way in — the fleet, or a terminal (refused)",             "kind": "decision", "actor": "coordinator",                 "body": "step-0-which-way-in"},
    {"id": "read",       "name": "Read the program and everything the repository can answer",       "kind": "io",       "actor": "coordinator",                 "body": "step-1-read-the-program"},
    {"id": "refusals",   "name": "The refusals — by sentinel, before any question",               "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "step-2-the-refusals"},
    {"id": "rounds",     "name": "The rounds — framing, edges, proof and cuts",                    "kind": "loop",     "actor": "coordinator", "loop": {"max_rounds": 3, "exit": "the person confirmed the draft in the last round, or the ceiling was reached and what stands is written with its open items"}, "body": "step-3-the-rounds"},
    {"id": "author",     "name": "Write it — the narrative, the rows, the edges, the cuts",        "kind": "author",   "actor": "coordinator", "produces": ["feature-map"], "body": "step-4-write-it"},
    {"id": "land",       "name": "Land it — the branch, the PR, the merge",                        "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "step-5-land-it"},
    {"id": "landed",     "name": "The landed result, then the sentinel",                             "kind": "io",       "actor": "coordinator",                 "body": "step-5-land-it"},
    {"id": "report",     "name": "Report",                                                          "kind": "author",   "actor": "coordinator",                 "body": "step-6-report"}
  ]
}
```

---

## What to do

### Step 0: Which way in

```bash
printf '%s\n' "${FLEET_RESULT_FILE:-<unset>}"
```

- **Set** → the fleet dispatched you on a program the page asked to have shaped.
  `$ARGUMENTS` is its register id (`PG-NN`), the mission's `## Shaping` block carries the
  requester, any instruction and the row as served, and the payload says which round this
  is — *The headless contract* §1. Run Steps 1–6.
- **Unset** → a person is at a terminal, and this is the wrong verb for them. Say exactly
  this and stop, writing nothing: **This command runs only on the fleet. At a terminal, run
  `/fleet:program:decompose PG-NN` instead** — it asks the same questions with you in the
  room, runs `program:create` inline when the row is bare, and researches with real
  fan-outs.
  **And say that the terminal is not a one-way door.** A person who starts by hand and
  would rather the fleet finished it presses **Shape this** on the entity's own page (the
  `start` action — the same button that would have dispatched this command), and the next
  round picks up from whatever is committed: the register row, the detail file, the answers
  already written down. Being sent to a terminal must never read as being sent there *for
  good*.
- **Set, but `$ARGUMENTS` is not a program id, or the block's `kind` is not `program`** → a
  mis-dispatch. Write nothing; sentinel `failed` naming what was wrong; stop.

### Step 1: Read the program

Everything the repository can answer is answered here, before any question, so that no
round spends the person's attention on something a file already says.

1. **The row** — `slot:programs`, every cell: `Name`, `Kind`, `Verified by`, `Requires`,
   `Disposition`. A `withdrawn` or `superseded` row is refused in Step 2. Note which cells
   are `—`: that is what shaping fills.
2. **The detail file**, if one exists (`slot:file-conventions` names its home and its one
   frontmatter key). A narrative already above the first `##` means a person wrote one;
   you sharpen it toward Step 2b's tests and never replace it wholesale. `## Decomposition
   record` present means this program was decomposed once and this run is a
   re-decomposition — `decompose.md`'s *Re-runnable by design* — against what shipped
   since.
3. **The vision** (`slot:product-vision`) — the personas by their labels, the core loop, the
   differentiators. Round 1's persona options are drawn from here, verbatim.
4. **The active-slice count** — `slot:slices` names the ceiling and how a cut counts as
   active; count them the way `/fleet:slice:create` Step 1 does. The number decides Step 2 and
   bounds Round 3.
5. **The ground** — the feature maps (`slot:feature-maps`), the requirement registers
   (`slot:commitments`) and the component registry (`slot:components`) for the area the row's
   name points at: what exists, what is claimed, what is a gap row already. This is
   `decompose.md` Phase 3's exists-check, run in this session sequentially — a fanout is not
   assumed on the seat — and its rule holds unchanged: a verdict cites a line that executes,
   never a document asserting it, and a doc/code disagreement is a finding reported in
   `open`, not a tiebreak.
6. **The title and the headline, decided.** Apply `create.md` → *Step 2b*'s two tests to the
   row's `Name` and draft the headline inside its limit with a concrete example. The title is
   **the run's to decide** — the tests are mechanical — and it is reported in the landing;
   a `Name` that fails them is rewritten in the register row in the same PR, and the
   landing's summary says so.
7. **The kind, proposed.** Read the row's voice against `create.md` Step 2 item 1 and propose
   `outcome` or `program` — proposed, because the kind is the person's (Round 1).

### Step 2: The refusals

By sentinel, before any question, in the form *The headless contract* §9 gives — no branch,
no file, no result document, a summary naming the move that releases it:

- **No row resolves** for the id → `failed`, a mis-dispatch.
- **`Disposition` is not `adopted`** → `needs-decision`: *"this program is withdrawn (or
  superseded); a shaped record for it would be read by nobody — reinstate it in the register
  first, or leave it"*.
- **The vision gate fails** — `decompose.md` Phase 0's check, **decided by the run**: a
  program that serves no persona the vision names and exercises no differentiator is set
  aside, not decomposed. *"Does this belong"* is not a 2–4-option fork, so it is not a card:
  end `needs-decision` with the alignment check written out in the summary, in plain words,
  and the move — *"say which persona and which differentiator, and try again, or withdraw
  it"*.
- **The active-slice ceiling is already reached** → `needs-decision` naming the count and the
  active cuts: *"n of the ceiling are active; nothing can be cut into this program until one
  closes — close a cut and try again"*. Room for fewer cuts than the program needs is not a
  refusal: Round 3 cuts what fits and queues the rest as gap rows, as `decompose.md` Phase 7
  says.

### Step 3: The rounds

Three rounds at most, at most four questions each, every one shaped by the rail in *The
headless contract* §3 — which is the interview card applied to a written medium, and the
card is what the person's reading is graded against:

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

Each round's brief opens with which round this is of up to three, restates what is decided,
and says what this round settles. What follows is the mapping from the attended questions
to cards.

**The aspect each card changes** (*The headless contract* §3): *Kind* → `kind`, *The day it
becomes true* → `outcome`, *Who is stuck* → `whoIsStuck`, *Not doing* and *Scope edge* →
`notDoing`, *Depth bar* → `depth`, *Data reality* → `data`, the *Proof and cuts* card →
`proof`, a borderline bucket → `gaps`. Every round's `draft` carries what is decided so far;
Round 3's carries `proof`, `slices` and `gaps` as briefed and is marked `"confirm": true`.

#### Round 1 — the framing (`create.md` Step 2)

| Card | What it establishes | Options |
|---|---|---|
| **Kind** | whether this is named for the result someone gets or for the thing that lands — `create.md` Step 2 item 1 | two: *a result somebody gets* / *a body of work that lands*; the run's proposal from Step 1.7 recommended, with what each changes for the reader of the board |
| **The day it becomes true** | the observable event that settles it — Step 2 item 4 | three candidate days the run drafts from the row and the vision, one recommended; free text |
| **Who is stuck, in what circumstance** | the persona and the job story — Step 2 item 3 | 2–4 personas from `slot:product-vision`, by their plain labels, one recommended; free text for a person the vision does not name |
| **Not doing** | the explicit no-gos — the *Not doing* paragraph of Step 3b | **zero options**: a discovery question, free text only. Nobody volunteers a non-goal, and a menu here would be the run's guesses |

Then STOP: write the `questions` result, the sentinel `needs-decision`, end the turn.

#### Round 2 — the edges of the outcome (`decompose.md` Phase 1)

On resume, consume Round 1 (*The headless contract* §4), then work backwards in this
session — `decompose.md` Phase 2's *"for that to be true, what must exist?"*, the class
sweep included, **decided by the run from Rounds 1–2 and Step 1's ground read**, with the
result reported in the decomposition record rather than asked one requirement at a time.
What Phase 1 asks is asked now:

| Card | What it establishes | Options |
|---|---|---|
| **Depth bar** | demo-grade, pilot-grade or production-grade — the thing that moves the program-specific list most | three, one recommended from the vision's phase and the row's voice; each says what a customer gets and what it costs in hardening |
| **Data reality** | whose real data, from which systems | the connectors and sources the repository actually carries (Step 1.5), 2–4 of them, one recommended; free text for a system not present |
| **Scope edge** | the adjacent things that are explicitly OUT — the cheapest scoping tool | **zero options**, free text: an edge the run drew would be the run's edge |

Three cards; the fourth slot stays empty unless Round 1's answers left one framing question
genuinely open (a persona the vision does not name, a day nobody can observe) — then that
question is asked first, most-blocking first.

#### Round 3 — the proof and the cuts (`decompose.md` Phases 4, 6 and 7 — draft, then confirm)

On resume, consume Round 2, finish the work-backwards, sort every requirement into the two
buckets of `decompose.md` Phase 4 by its own test, and derive the build order the way Phase 6
does (`python3 knowledge/scripts/gen_program_plan.py` over the rows you *would* write — run it
on a scratch copy, never on a branch: nothing is written before this round's answer). Then
the last round:

- **The brief IS the draft.** It carries: the title and headline as decided; the persona,
  the day and the not-doing as answered; the requirements found, each marked *exists* /
  *gap* / *unsatisfiable* (Phase 3's third category, reported and never passed as a gap);
  the build order; **the proposed slices** — two to four, each with its name (a noun phrase
  for what lands, the naming rule `slot:entity-model` gives), its `Kind`, its one-sentence
  `Done when`, and which gaps it holds — and **the proposed proof**: the composed
  demonstration that shows the slices working together for a person, through every surface
  the program claims. Eight lines is the ceiling; the fuller draft is what Step 4 writes,
  and the brief names what is in it.
- **The proof card** — *Proof and cuts*: accept the proposed proof and the cuts as briefed
  (recommended), or one of at most three alternative composed proofs the run can name; free
  text for a different cut. The answer to this card is the confirmation Step 4 waits for.
  The rule the options obey is `create.md` Step 3's: the proof drives a surface a customer
  touches, and **it is never a proof one of the proposed slices names** — an option that
  would be is not offered.
- **The borderline buckets** — one two-option card per item Phase 4's test leaves genuinely
  open (*a product capability a second customer would benefit from* / *this program's own
  work*), the strongest first, filling the remaining slots of the four. Every item beyond
  that is sorted by the *second customer* tiebreak and the sort is reported in the
  decomposition record.

**At the ceiling — three rounds asked, or an answer missing — write what stands** (Step 4)
and put every unsettled item into `landed.open` verbatim. A proof the person did not accept
is not written: the cell stays `—`, the program reads *unproven* on the board, and `open`
says which proof was proposed.

### Step 4: Write it

Only after Round 3's answer, or at the ceiling. Everything here is authored **exactly as the
attended commands say**, cited, never restated:

1. **The register row** — `create.md` Step 3: `Kind` as answered; `Verified by` as accepted
   (below); `Requires` = the root capability ids from the decomposition, `decompose.md`
   Phase 7 item 1, never areas; `Name` rewritten only when Step 1.6 found it failing its
   tests; `Disposition` untouched. **Never write a status on the program** — there is no
   column, and the validator rejects one being added.
2. **The narrative** — the detail file per `create.md` Step 3b, its skeleton and its
   line-by-line test, in the voice of Step 2b: the headline inside its limit with the
   example, the persona and job story from Round 1, *Today*, *Why now*, *What changes for
   them*, *How we'll know*, *Not doing* from the person's own words. Above the first `##`
   nothing of ours is named.
3. **The decomposition** — `decompose.md` Phase 5: an existing gap row re-adopted before one
   is minted; gap rows appended at the END of their table in the right feature map, ids from
   `python3 knowledge/scripts/validate_id_collisions.py --allocate CAP <n>`; `Needs` edges
   on every gap, `—` written deliberately. A gap with **no component home is reported in
   `open`, never minted**: registering a component is a person's act.
4. **The record** — Phase 7 items 2 and 3: `## Program-specific work` and the
   `## Decomposition record` table in the detail file, where every component, seam and
   research correction lands and the class sweep is shown; the unsatisfiable items sit
   under their own heading there, routed to the component that owns the mechanism.
5. **`Verified by`** — the proof the person accepted. An existing PRD is named by number.
   When no PRD exists to name, the run writes a **stub** for the composed proof in the shape
   `/fleet:prd:create` Phase 6 gives — the number allocated, the home the slice the proof lands
   in, the `## Brief` holding the accepted demonstration sentence, `status: stub` and nothing
   else authored — so the cell resolves and the proof is filled from its own page next;
   `open` says so. Never a placeholder, never a slice's proof (`create.md` Step 3's fatal
   collision), and never a cell filled at the ceiling on the person's behalf.
6. **The cuts** — Phase 7 item 7: one row per confirmed slice in `slot:slices`, id from the
   allocator, naming this program, its `Kind`, its `Done when`, `Verified by` where a
   member PRD already answers it and `—` otherwise, `Disposition: adopted`; no dates, no
   status, no list of slices anywhere on the program. Cut only what the ceiling allows; the
   rest stay gap rows with their edges, and `open` names which cut waits on which.
7. **Withheld, and reported in `open`** — Phase 7 item 8's tracker placement of tasks and
   bugs, the component registrations of item 3 above, any slice detail file (the slice's own
   page refines it), and every scope addition the person did not confirm. **A shape run makes
   no tracker write.**

Then `make validate-knowledge` clean, and `python3 knowledge/scripts/gen_program_plan.py PG-NN`
replays without error — the plan is derived, never hand-written; if it looks wrong, fix the
rows and re-derive.

### Step 5: Land it

*The headless contract* §6, unchanged: the prior attempt found with `gh pr list --search`,
the deterministic branch `agent/shape-<key>`, **the PR's identity** (shaping content only; the tracker key in the title
when the entity has one — what the `Verify Gate` reads), every id re-checked against the tip at push,
`gh pr merge --auto --squash` armed the moment the PR opens, and the PR
driven to `state: MERGED` (`queued` is pending, `ejected` from the merge queue is red CI — the contract's `gh_pr_merge_state.py` watch) — a generated-ledger conflict taken one side wholesale with its
generator re-run.

Once merged, the `landed` document to `$FLEET_RESULT_FILE`, written whole and read back —
§7's shape with a program's `changed`:

```json
{"kind": "landed", "landed": {"kind": "program", "id": "PG-NN", "href": "program:PG-NN", "pr": "<the merged PR's URL>", "files": ["<every path the PR changed>"], "summary": "<one plain sentence: what now exists>", "changed": {"narrative": true, "verifiedBy": "NNNN", "requires": ["CAP-NNNN"], "slices": ["SL-NNN"]}, "open": ["<each unsettled or withheld item>"]}}
```

`narrative` is `true` when the detail file's narrative was written or rewritten; `verifiedBy`
is the cell as written (`—` when no proof was accepted); `requires` and `slices` are the ids
as written. Then the sentinel: `success` with the PR URL. A PR that could not be brought to
merge in this run is `partial` with the PR URL and **no `landed` file**, so the next dispatch
resumes the branch — §8's table, and never `done`.

### Step 6: Report

Nine lines, for a human reading the transcript: the id; the rounds asked and questions
spent (`n of 12 across r rounds`); the kind, the day and the persona as answered; the proof
as accepted (or *unproven*, and why); the cuts made and the cuts queued behind the ceiling;
the gap rows minted and re-adopted; what was withheld; the PR and its state; the result
written (`landed` | `questions` | none — why) and the sentinel word.

---

## The headless contract (shared)

<!-- include: process/shaping-headless.md -->
### The headless shaping contract — shared by `program:shape`, `program:demonstrate`, `slice:refine`, `prd:fill` and `prd:blueprint`

**You are on the fleet, and nobody is at a terminal.** A person pressed a button on an
entity's own page — *Shape this program*, *Refine this slice*, *Fill this PRD* — or started a
program's drive, which designs its drafted PRDs as their prerequisites ship — and the fleet offered the entity to this seat under its own register id. `AskUserQuestion` reaches
nobody here and stalls the run. **You ask by writing** a `questions` result and ending the
turn; the person answers on that page, and this same engine session is resumed with the
answers. That is the whole mechanism, and it is the one `intake.md` §5 and
`deliver.md` §5 already run on — not a new rail.

Your product is one merged PR and one `landed` document. Everything below is what the
shaping commands share; each command's own body says *what* is asked in which round
and *what* is written. Where this text and the command disagree, the command is the bug.

#### 1. Which round this is — read the dispatch payload

Everything you were given is already in front of you: the mission's `## Shaping` block
(the kind, the register key, who requested it, an `instruction` when the person sent it
back with a note, and `before` — the entity's row as the page served it), plus every prior
question and answer inlined into this session. **Read what you were given; do not go
looking for more of it.** Then:

- **No prior questions in the payload** → round one. Read the repository, then ask.
- **Prior questions AND their answers** → you were resumed. Consume them (§4) and continue
  where the round plan says you left off.
- **A `## Decided already` block in your system prompt** → a person already answered earlier
  rounds on this entity and the session that asked them is gone, so you are a cold start. The
  block lists, oldest first, every answered question on the entity — the question text and the
  answer verbatim, from this command and from earlier ones (a design inherits the fill's
  answers). **Those are decided: never ask one again, never re-ask it reworded, and do not count
  those rounds against your ceiling.** Plan from them as if you had asked them. Re-open one only
  when the person's own answer says so ("revisit", "ask me again once ...", a send-back
  instruction naming it); the fact that you would have chosen differently, or that the draft
  has since moved, does not. Ask only what the block leaves open.
- **Prior questions with no answers** → re-dispatched before the person got to it. **Do
  nothing at all and end the turn**: write the sentinel as `needs-decision` and stop.
  Re-asking is how a person receives the same round twice and learns to ignore both.
- **An `instruction` in the payload** → the person pressed *Shape it again* or *Try again*
  with a note. It is the newest thing you have: take it as a correction of whatever landed
  before, let it settle what it settles, and never treat it as licence to widen a finished
  cut or rewrite an accepted proof it does not name.
- **A resume whose prompt says *"The person did not answer these questions. They said:"*** →
  the round was **sent back with an instruction**, not answered. The person is telling you the
  ground has moved since you asked, and the checkout is already at the trunk's current head
  (the prompt's first line names it). Re-read the repository at that head — the registers, the
  entity's row, whatever the round was built on — rather than trusting the reading above; act
  on the instruction; then re-ask, as a new round, **only** the questions that still stand
  after that, and count that round as the one it replaces rather than as a further one. A
  send-back answers none of the questions it returned: nothing in §4 applies to them, and a
  draft is never confirmed by one. If nothing still needs the person, continue where the round
  plan says you left off.

**Warm resume is the mechanism; cold restart is the case you must survive.** A transcript
can be pruned and a box rebuilt, and then a fresh session lands here with nothing but the
payload. So every question's `prompt` says what the question is establishing, and every
round's brief restates what has been decided so far — a cold successor reading *"B"* can
tell what B settled without your reasoning attached.

#### 2. Round accounting — what is asked, what the run decides, what is withheld

**At most four questions per round, most-blocking first, and the number of rounds is the
spine's `max_rounds` — three for a program's shape, two for its proof, two for a slice, three for a PRD, three for a
PRD's design.** Count the
round off the payload — the number of prior question sets plus the one you are about to
emit — never off memory, so the count survives a cold restart. **On reaching the ceiling:
stop asking.** Write what stands, put every item still open into the result's `open`
field verbatim, and land it. Never a further round, and never a "quick clarification"
that is a further round wearing a different word.

**The run decides everything the repository can answer**, and asks none of it: which
register governs the ground, which component owns it, what already exists and what is a
gap, which id the allocator reserves, what shape a file takes, whether a title passes its own
tests. A question the repository could have answered is worse than silence — it spends
the one resource this contract exists to protect and teaches the person to skim the next
one.

**The run never decides**: the day the outcome becomes true, the persona, the kind, the
proof, an exclusion, a bar's RED, a scope addition. Each of those is a card, or it is
reported as open — never filled in on the person's behalf.

**Withheld and reported, never done silently**: anything that would write to the tracker
(placing a task, filing a bug, closing an idea), anything that would mint an entity nobody
asked for (a component, a second program, a slice past the ceiling), and every addition to
scope the ask did not name — each goes in `open`, or in the PRD's `## Scope ledger` as
`withheld`, and nowhere else. Scope discipline binds a headless run harder than an
attended one, because nobody is watching the diff grow.

#### 3. The rail — the shape of every question you may emit

The wire shape is `intake.md` §5's, and it is the interview card applied to a written,
asynchronous medium: the person answering has not read the repository and will not look
anything up. One `questions` document per turn:

```json
{
  "kind": "questions",
  "brief": "Round 1 of up to 3 — what I am shaping: …\nFor example: …\nDecided so far: …\nWhat this round settles: …",
  "questions": [
    {
      "id": "q1",
      "prompt": "<the question, in plain words, saying what it establishes>",
      "allowFreeText": true,
      "aspect": "<the aspect this answer changes, from the table below>",
      "options": [
        {"id": "a", "label": "<short, plain, no ids>", "then": "<what changes for a real person · Why · Con>", "recommended": true, "becomes": "<the aspect, as it reads if this is picked>"},
        {"id": "b", "label": "<short, plain, no ids>", "then": "<what changes for a real person · Why · Con>", "recommended": false, "becomes": "<the aspect, as it reads if this is picked>"}
      ]
    }
  ],
  "draft": {"<aspect>": "<how it reads after this round, if every recommended option is taken>"},
  "confirm": false
}
```

Every rule in that shape is load-bearing:

- **2–4 options, exactly one marked `recommended: true`.** Zero marked is a deferral; two
  marked is not a fork.
- **`then` carries a rationale on EVERY option** — what changes for a real person, why it
  works, what it costs. An option whose `then` restates its `label` is a defect: the person
  cannot pick against you if only your pick was argued.
- **`allowFreeText: true` on every question**, without exception. The escape is not
  automatic here, and a question with four wrong options extracts a wrong answer rather than
  no answer.
- **One dimension per question.** Two forks folded into one produce an answer to neither.
- **No planning or tracker id in a `label`, ever**, and nowhere else without the plain name
  it stands for attached the first time — *the goal of getting a customer live without an
  engineer (PG-NN)*. Ids belong in the brief, as evidence.
- **Plain words throughout.** Explain each internal noun in half a sentence of ordinary
  English the first time it appears. Being asked to *"explain that again"* is a defect in
  the question: re-ask in full, plainer, and hold that register for the rest of the run.
- **The brief is mandatory and precedes the first question of every round**, at most eight
  lines: which round this is of how many; what this would let somebody do that they cannot
  today; one worked example with a named person and what they see; what has been decided so
  far; and one line on what this round settles, so the questions read as a fork and not a
  quiz. The last round's brief carries the **draft** the answer confirms (§5).
- **A discovery question may carry zero options — `"options": []` with `allowFreeText:
  true` — and only then.** When you cannot yet say, in one concrete sentence about a real
  person, what somebody does today without this, a menu inverts: your invented options
  become guesses and the person's pick reads downstream as a requirement. Ask it open. The
  service accepts an empty option list **only with free text** allowed; an empty list
  without it is refused at the wire and the round never lands. Never after the person has
  told you.

**What the round changes — the page draws it beside the card.** The person answering is
shown the few aspects that decide the thing being shaped, and how this round changes each,
never the document. That only works if you say it, so every round carries:

- **`aspect` on every question whose answer rewrites one aspect** — the key from the table
  below, exactly as spelled. A discovery question that informs several aspects names none.
- **`becomes` on every option of such a question**: the aspect as it would read if that
  option were picked — the actual sentence or short list you would write, in the person's
  plain register, never a description of it (*"narrower"*) and never an id without its name.
- **`draft`**: every aspect you can already state, as it would read after this round if the
  person took each recommended option — keyed by the table's words, one sentence or a short
  list each (at most 2,000 characters; a register row pasted in is refused). Leave out what
  you cannot state yet; the page says it is not settled. What the entity already says and
  this run will not change needs no entry.
- **`confirm: true` on the round whose answer is the go-ahead to write** (§5) and on no
  other. Its `draft` carries every aspect Step 4 will write.
- **Never restate an aspect's current value in the prompt.** The page shows it struck through
  above what each option makes it, so a prompt that quotes the old sentence in full is the same
  paragraph twice, and the question itself disappears under it. Ask the fork in one line.

| Shaping | Aspects (key — what it is) |
|---|---|
| program | `outcome` — the day it becomes true · `whoIsStuck` — who is stuck, in what circumstance · `kind` — a result somebody gets, or a body of work · `depth` — demo, pilot or production · `data` — whose real data, from which systems · `notDoing` — the explicit no-gos and the scope edge · `proof` — the composed proof · `slices` — the cuts, each with its done-when · `gaps` — what is still to build · `bar` — what proven means |
| slice | `doneWhen` — the promise · `kind` — feature, capability or gap-set · `promises` — the promise rows · `excluded` — what this cut refuses · `bar` — the criteria · `verifiedBy` — the proof |
| prd | `jobStory` — when / I want to / so I can · `whoFor` — the persona · `trigger` — the real starting event · `criteria` — what done means, as the acceptance criteria a person reads · `decisions` — what the run decided unasked, one line each · `scope` — in, out, and withheld · `slice` — the cut it lands in |
| prd design | `decisions` — how it is built, each fork as settled · `mockup` — what the person will see, as approved · `commitments` — the promises the design adds or changes, in plain words · `scope` — admitted, pulled in, withheld · `envelope` — one merge, or the split it needs |

A key outside this table is still rendered, under its own name — but the page's order and
labels are the table's, so invent one only for a thing the table genuinely lacks. All four
fields are optional on the wire and a round without them renders as a plain card; a run
that omits them is legible, and a run that fills them is the one a person can answer well.

**Then STOP — a park, not a pause.** Serialise the complete object, write it to the path in
`$FLEET_RESULT_FILE` in one write, **read it back and parse it** (a half-written file is a
parse failure at the daemon, indistinguishable from a crash), **check the set's shape**, write
the sentinel with `status: "needs-decision"` and `pr: ""`, and end the turn. You do not move any
issue, post anything, or wait in-session; a `questions` result ends the *turn* and not the
*interview*, which resumes into this same session when the answers land.

```bash
python3 knowledge/scripts/validate_questions.py "$FLEET_RESULT_FILE"
```

It exits `0` when the set meets every rule the question table enforces — two to four options
(or none, for an open free-text question), at least one recommended, each option carrying an
`id`, a `label` and a `then` — and exits `1` naming the rule that broke. The service refuses a
set that breaks one *after* the run is over, when this session is gone; correct it here, in the
same turn, and re-run until it is green.

#### 4. Consume the answers on resume

- **Take the person's answer as given.** They are the authority on their own problem, their
  persona and their priorities; a model does not overrule them.
- **A free-text answer beats a picked option**, always — quote it, never normalise it into
  the nearest option you offered.
- **A partial answer is an answer.** Consume what was answered; the unanswered question goes
  into `open` verbatim. **Never re-ask an unanswered question.**
- **An answer of `CAN'T ANSWER` is the person telling you the question was not theirs to
  answer — it is neither an answer nor a refusal.** The page offers it on every card (*Can't
  answer — carry on*), so you never add it as an option. Follow
  [`interview-protocol`](interview.md) → *"I can't answer this"*, which is the one rule and is
  not restated here: **a stated `Assumption: …` line marked unconfirmed, or an open question for
  the reporter; never an invented answer; never the question again; every item under an
  `Unconfirmed assumptions` heading** — here, a `## Unconfirmed assumptions` section in the
  artifact you land (the PRD's `prd.md`, the slice's detail file, the program's narrative), and
  each also in the landed result's `open` list, prefixed `Unconfirmed:`. It settles no aspect:
  the `draft` keeps what it said, and the person's *Approve and write it* still confirms
  everything else. A run that asked nothing (`slice:refine`'s stub mode) has none to carry.
- **An answer that changes the ground sends you back to reading, not to asking.** Re-read the
  registers before the next round; a round built on a stale reading spends the person's
  remaining attention on the wrong fork.

#### 5. Draft, then confirm — nothing is written before the last round's answer

The last round's brief carries the whole draft — the proof and the cuts, the sharpened
promise and its bar, the scope that survived — and the answer to that round is the
confirmation. **Mark that round `"confirm": true` and put the draft in its `draft` too**
(§3): the brief says it in eight lines, the `draft` is what the page lays out aspect by
aspect under *"Does this say what you meant?"*, and the button the person presses reads
*Approve and write it*. **Nothing is written before that answer**: no branch, no file, no row, no
id allocated — with one exception, `prd:blueprint`'s mockup, which is the question's subject and
not its product: it is committed alone to the design branch with **no PR open**, so a cold restart
still finds what the person is looking at, and nothing can merge before the answer. A run that writes first and asks afterwards has authored what nobody saw,
and the page it lands on is a page somebody now has to read *for* mistakes rather than
*with* the person who made the calls.

#### 6. Land it — the branch, the PR, the merge

**First, find the prior attempt.** A run can end between arming the merge and writing
`landed` (a `partial`, a killed session), and the re-dispatch lands here with the earlier
PR still open and armed:

```bash
gh pr list --state open   --search "<key>" --json number,headRefName,url
gh pr list --state merged --search "<key>" --json number,mergedAt,url
```

An open PR carrying the key is the prior attempt — check out its branch and drive *that*
PR, never a second one. A merged PR carrying the key means the work is on `main`: write
the `landed` document from its diff and stop. Neither → branch.

**The branch is deterministic from the key**: `agent/shape-<key>` (`prd:blueprint` uses
`agent/design-<key>`, because a fill already merged the shaping branch under the same PRD key) — the work-item pattern
`slot:git-workflow` gives, with `shape-<key>` as its key segment, the key lowercased, and
nothing per-run (no slug, no box, no date) — so a retry on any box resolves this same
branch, and the PR title carries the key so the search above finds it. Cut it from a
freshly fetched `origin/main`. **Every id you allocate comes from
`python3 knowledge/scripts/validate_id_collisions.py --allocate <prefix> <n>`**, which
reserves each id atomically as a claim ref on GitHub; there is no counter to bump. Run
`make validate-knowledge`, commit with a message that says what the entity now promises
(not which cells moved). **Re-check every allocated id against the tip you are about to
push over** — `git fetch origin main`, then run `python3 knowledge/scripts/validate_id_collisions.py`
(the check, not `--allocate` — re-allocating claims fresh ids and burns the ones you hold); a
finding means a branch took the id while you worked, so allocate a new one, rewrite and amend. Push, open the PR
with the key in its title, and arm the merge the moment it opens:

```bash
gh pr merge --auto --squash   # never --delete-branch: gh refuses it under a merge queue
```

**The PR's identity — what the Verify Gate reads, written at open and never after.** An
`agent/shape-<key>` PR writes knowledge and nothing else, so the repository's required
`Verify Gate` check passes it as *not lane work* when **every changed
path is shaping content** — the program, slice, PRD, requirement, feature-map and journey
files (`knowledge/{programs,slices,prds,requirements,features,journeys}/**`) — and fails it
closed (: *"head ref `agent/shape-…` is an agent lane branch … but no `ENG-nnnn`
resolves … unverifiable lane work"*) the moment one path is anything else: code, `.claude/**`,
`knowledge/scripts/**`, `.github/**`, the `fleet/` submodule, config, a lock file. The
exemption is read off the PR's diff, never off its body, and `NOT-A-VERIFY-LANE-PR=<code>`
neither grants it nor reaches a keyless PR (it is read only after a key has resolved). So:

- **Stay inside shaping content.** A shaping run that finds it must touch anything else
  stops and reports it in `open`; it does not carry it in the same PR.
- **Carry the entity's tracker key when it has one.** A PRD's is the issue titled `[NNNN] …`
  (read-only lookup through the tracker's GraphQL API, the credential from the environment and
  never argv, one instance of the general credentials-never-on-argv rule (CLAUDE.md); the brief's tracker key, when it names one, wins). Put it in the **title** as a
  trailing `(ENG-nnnn)` — never the completing forms `[ENG-nnnn] …` / `fix(ENG-nnnn): …`, and
  never a closing verb in the body: a shaping PR does not complete the issue it shapes
  (`push.md` 5.6). The body then carries `Refs ENG-nnnn` and a `## Files` scope manifest: a PR
  that names a tracker key must declare its changed paths (the repository's scope-manifest
  guard, ), one backticked bullet per `git diff --name-only origin/main...HEAD` path,
  recomputed if a later push adds one.
- **No key resolves** (a program or a slice has no tracker issue of its own, and the brief
  names none): that is fine — no key is needed and the run does **not** end `partial` for it.
  Never invent a key and never cite an unrelated issue; with no key in the title there is no
  manifest obligation either.

Both `gh pr create` and any later `gh pr edit` keep the title key and the manifest when there
is a key: a PR body rewrite that drops either re-runs the gate red.

**Then drive it to `state: MERGED`, not to green.** **Under a merge queue the PR can read green and still not merge.** Watch it with `python3 knowledge/scripts/gh_pr_merge_state.py <pr> --watch`: `armed` and `queued` are pending, `merged` is done, and `ejected` — **removed from the merge queue**, reading OPEN and `CLEAN` with its own checks green and nothing armed — is red CI on the queue's `merge_group` commit (the script names the red checks): fix it, then push — after `python3 knowledge/scripts/gh_automerge_disarm.py <pr>`, because a queued PR's branch rejects every push — and re-arm. A red check is yours to fix. A conflict
in a register is the register's shape (two rows append at the same line): rebase onto
`origin/main`, take the other row *and* yours, re-check the id, force-push with
`--force-with-lease`. A conflict in a **generated ledger** is never hand-merged: take one
side wholesale and re-run its generator. Keep watching until the merge — a PR left green
and unwatched re-conflicts, and auto-merge does not fire through a conflict.

#### 7. The `landed` result — only over a merged PR

Once merged, one file to the path in `$FLEET_RESULT_FILE`, written whole, read back,
parsed. The shape, with a program's values as the worked example:

```json
{
  "kind": "landed",
  "landed": {
    "kind": "program",
    "id": "PG-NN",
    "href": "program:PG-NN",
    "pr": "https://github.com/<org>/<repo>/pull/<n>",
    "files": ["<every repository path the PR changed>"],
    "summary": "Narrative written; proof NNNN named; 3 slices cut; 11 gap rows with Needs edges.",
    "changed": {"narrative": true, "verifiedBy": "NNNN", "requires": ["CAP-NNNN"], "slices": ["SL-NNN"]},
    "open": ["<every item the rounds did not settle, verbatim>"]
  }
}
```

- **`kind`** is `program` | `slice` | `prd`, matching the command (a design is `prd`); **`id`** is the register
  id as the page spells it (`PG-NN`, `SL-NNN`, the four-digit PRD number); **`href`** is the
  fleet's own route to the entity's page — `program:`, `slice:` or `prd:` and the id,
  nothing else.
- **`pr`** is the merged PR's URL; **`files`** is non-empty — a landing that changed no
  file is not a landing.
- **`summary`** is one sentence a person reads on the page's ribbon: what now exists, in
  plain words.
- **`changed`** is per kind, and it is what the page compares against `before` to confirm
  the landing once the corpus syncs: a program's `narrative`, `verifiedBy`, `requires`,
  `slices`; a slice's `doneWhen`, `kind`, `bar`, `requirements`, `verifiedBy`; a PRD's
  `status`, `slice`, `implements`, `acs`; a design's `status`, `designedAgainst`, `mockup`,
  `implements`, `acs`.
- **`open`** carries every item the rounds did not settle and everything withheld (§2),
  each as a sentence a person can act on. An empty list is a claim that nothing is open;
  make it only when it is true.

**If `$FLEET_RESULT_FILE` is unset or empty in a run that got this far, write nothing
anywhere and say so in the sentinel.** Never a scratch path, never the JSON printed as if
printing were delivering, and never a tracker write in its place.

#### 8. The sentinel — the last thing you write, and the four words it may carry

The result file is not the whole deliverable: the done-sentinel is a second obligation.
Your dispatch mission names its path and owns its keys; what a reader here would get wrong:

| Ending | `status` | `pr` | Result file |
|---|---|---|---|
| A round was asked | `needs-decision` | `""` | `questions` |
| A refusal (§9) | `needs-decision` | `""` | none |
| Landed — the `landed` file is written over a **merged** PR | `success` | the PR URL | `landed` |
| A PR opened or armed but not brought to merge in this run | `partial` | the PR URL | **none** — no `landed` file, so the next dispatch resumes the branch rather than minting a second id |
| A mis-dispatch — no result path, a key that resolves to no row, an entity of the wrong shape | `failed` | `""` | none |

**`done` is not a sentinel status.** It names no outcome in the daemon's vocabulary, so a
run that writes it has reported nothing and is nudged until it reports something. A
question round is not a failure and charges no attempt; a `partial` is not a give-up; a
refusal is not a `failed`. Result file first, read back, *then* the sentinel — the state
the entity lands in is decided by the file, and the word only records the run. **Write the
sentinel even when you wrote no result document**: the unset-path case is exactly the one
where it is the only signal anything happened.

#### 9. Refusals — by sentinel, with no result file

Some things the command cannot shape and nobody is there to ask: an entity whose work is
finished, a ceiling already reached, a program the vision does not support, a key that
names nothing. A refusal is written as the sentinel with `status: "needs-decision"`,
`pr: ""`, **no branch, no file, no result document**, and a summary that names **the move
that releases it** in a sentence the person can act on from the page — *"close a cut and
try again"*, *"send it back naming the program"*, *"this cut is finished; a scope change is
a new cut"*. **No result kind carries a refusal**: the closed set of result kinds is
`intake.md` §8's plus `landed`, and a command file may not extend it. A mis-dispatch — the
kind or key does not match this command, the entity is not the shape the command was made
for — is `failed`, in the same form.

#### 10. What a shaping run never does

- Calls `AskUserQuestion`, or waits in-session for a person.
- Writes to the tracker — no issue, no label, no state, no comment. Every move the fleet
  makes is a projection of the file you leave.
- Writes a `status:` on a program or a slice, or a date on any tier. Completion is computed;
  the PRD's `status:` is the one authored status in the model, and only `prd:fill`
  (`prd-drafted`) and `prd:blueprint` (`designed`) write it.
- Widens a bar, softens a RED, rewrites the promise of a finished cut, or fills a proof cell
  with a placeholder or a slice's own proof.
- Writes a second result file in one turn, or the same round twice.
- Adds to scope beyond the ask without a card in the offer round and a ledger row.
<!-- /include -->

---

## Rules

- **Cite, never restate.** The voice rule is `create.md` Step 2b, the skeleton is Step 3b,
  the register is Step 3, the decomposition is `decompose.md` Phases 0–7. This file maps
  their questions onto rounds; it owns none of their rules, and a sentence of theirs copied
  here is the copy that drifts.
- **Never write a status on the program, and never a date on any tier.** Completion is
  computed from the slices and the proof, stored nowhere; the register has no column for
  either and the validator refuses one being added.
- **The person decides the kind, the day, the persona, the not-doing, the depth, the edge,
  the proof and every borderline bucket. The run decides the title, the research, the gap
  rows, the ids and the file shapes — and reports each of them.** Nothing is asked that a
  file answers; nothing is decided that a person owns.
- **Draft, then confirm.** The last round's brief is the draft, and nothing is written
  before its answer. At the ceiling, what stands is written and every open item is named
  in `landed.open` — never filled in on the person's behalf.
- **The proof is composed and never a slice's own; a placeholder is worse than an empty
  cell.** `create.md` Step 3's collision is fatal at the validator, and an unaccepted proof
  leaves the cell `—` and the program *unproven* on the board, which is the honest reading.
- **The active-slice ceiling binds here as it binds `decompose`.** At the ceiling it is a
  refusal by sentinel; short of it, cut what fits and queue the rest as gap rows.
- **No tracker write, no component minted, no `AskUserQuestion`.** Each is withheld and
  reported in `open`.
- **Headless only.** A terminal is refused in one sentence naming `program:decompose`.
