# <!-- home -->Zetify<!-- /home --> Program — Shape (a skeleton row becomes a shaped program, on the fleet)

You turn a **program that is only a row** — a name, a kind, `—` in every other cell, no
narrative — into a shaped one: a literal title and a headline with an example, the six
narrative paragraphs, a composed proof named in `Verified by`, the decomposition's gap rows
and `Needs` edges, `Requires` filled with the roots, a decomposition record, and two to four
slices cut by what ships together. That is exactly what
[`program:create`](create.md) Steps 2–3b and [`program:decompose`](decompose.md) Phases 0–7
produce with a person at a terminal, and **this command is those two, run headless**: the
same questions, asked by writing through the fleet's question channel, answered by the person
on the program's own page, and landed as one merged PR.

**Before you write a program file, read its docs page** (under `.fleet/docs/`; `read_doc <page>` when Fleet's tools are in the session): `knowledge-base/programs`.

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
python3 knowledge/scripts/planning_mode.py
```

**First, the planning mode — it refuses before anything else.** When it prints **`areas`**, this
repository takes no new program, and shaping cuts new slices into one, which a program in this mode
no longer takes<!-- home --> (owner, 2026-10-28, `FLT-1285`, `FLT-1282`)<!-- /home -->. Write nothing and stop:
from the fleet, by sentinel in the form *The headless contract* §9 gives, `failed`, summary
*"This repository plans by area (`.fleet/fleet.toml` `[fleet.planning] mode = "areas"`), so it takes no new program. Cut the work as slices instead: `/zetify:slice:create`, one slice per deliverable, each under its area, ordered by their dependencies."*; at a terminal, say that sentence. An existing program still finishes —
`program:deliver`, `program:prove`, `program:demonstrate` and `program:ship` are unchanged. When it
prints **`programs`**, carry on below.

- **Set** → the fleet dispatched you on a program the page asked to have shaped.
  `$ARGUMENTS` is its register id (`PG-NN`), the mission's `## Shaping` block carries the
  requester, any instruction and the row as served, and the payload says which round this
  is — *The headless contract* §1. Run Steps 1–6.
- **Unset** → a person is at a terminal, and this is the wrong verb for them. Say exactly
  this and stop, writing nothing: **This command runs only on the fleet. At a terminal, run
  `/zetify:program:decompose PG-NN` instead** — it asks the same questions with you in the
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
   active; count them the way `/zetify:slice:create` Step 1 does. The number decides Step 2 and
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
8. **The originating brief.** When the program was made from an idea, the mission carries a
   `## Brief` block beside `## Shaping`: the dossier and the rounds its filer already answered in
   the intake interview (`from` names the filing). Read it whole as evidence the person already
   gave — the way `prd:fill` reads a stub's `## Brief`. No `## Brief` block
   means no idea behind the row; Round 1 then runs as written.

   **Whose words these are.** Only an answered round's text (the filer's own answers) and the
   dossier's `problem` are the filer's words: quote those as "the filer said". Every other dossier
   field (`whoItIsFor`, `whatTheyDoToday`, `displaces`, `howYouWouldKnow` and the rest) is the intake
   agent's synthesis: cite it as "the intake summarised: …", never as the filer's words.

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

**A card the `## Brief` already settles is not asked** (Step 1.8; the filer should never have to
repeat themselves). A card is settled only when the dossier or an answered round states what it
establishes — the persona and job story from `whoItIsFor` and
`whatTheyDoToday`, the no-gos from `displaces` or an answered "not doing" line, the day from
`howYouWouldKnow`. The kind is settled only by the filer saying it outright. For each settled
card: do not build it, **record it as settled from the intake** (the sentence,
and the field or round it came from; quoted as "the filer said" only from an answered round or
`problem`, and cited as "the intake summarised: …" from any other dossier field), and carry the quote into Round 2's brief and the drafts
that Step 3b writes. A card the brief only touches is still asked, and says what the brief gave so
the person corrects rather than restates. If all four are settled, Round 1 does not run: go
straight to Round 2 and say in its brief that the framing came from the intake.

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

- **The brief IS the draft, and the cuts are in it twice — once in prose, once as data.** The
  brief carries: the title and headline as decided; the persona, the day and the not-doing as
  answered; the requirements found, each marked *exists* / *gap* / *unsatisfiable* (Phase 3's
  third category, reported and never passed as a gap); the build order; the proposed slices
  and the proposed proof — the composed demonstration that shows the slices working together
  for a person, through every surface the program claims. **The eight-line ceiling binds the
  summary, never the cuts.** Keep the brief to eight lines if you like, but the cuts and the
  gaps then ride in the structured `draft` below, which the page lays out above the options —
  a cut that exists only as "Cuts: 2 slices" is a question the person cannot answer, because
  the card asks them to approve what it never showed them. Round 3's brief names the cuts by
  name on a `Cuts:` line (never a bare count) and the gaps on a `Gaps:` line.
- **`draft.slices` — the cuts, two to four, required.** An array, one object per cut, each
  written for a person who has read nothing: `name` (a noun phrase for what lands, the naming
  rule `slot:entity-model` gives), `kind`, `lands` (one sentence: what a person can do once it
  lands), `example` (one concrete person doing it), `doneWhen` (the one-sentence `Done when`),
  `closes` (the gaps it holds, by their plain names), and `leavesOut` (what it deliberately
  leaves for the other cut or for later). No id in any of them.
- **`draft.gaps` — the gaps, required when any exist.** An array of `{name, status, says}`:
  the gap named in plain words, `status` one of `exists` / `gap` / `unsatisfiable`, and `says`
  one sentence on what is missing. *"Four product gaps"* with none named is the defect.
  **The service refuses a `confirm: true` Round 3 for a program with no `draft.slices`** (each
  with a `name` and a `lands` sentence), and a brief that says "cuts" with none in the draft.
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
   is minted; gap rows appended at the END of their use's table in the right feature map (a row
   that fits no use, a map with no brief yet: [*Writing a feature brief*](../../../process/feature-doc-reconcile.md#writing-a-feature-brief--every-map-that-is-created-or-edited) — headless, the brief is named in `open` and
   the misfit filed), worded to
   [*Wording a promise*](../../../process/knowledge-bootstrap-formats.md#wording-a-promise--every-capability-rule-and-criterion), ids from
   `python3 knowledge/scripts/validate_id_collisions.py --allocate CAP <n>`; `Needs` edges
   on every gap, `—` written deliberately. A gap with **no component home is reported in
   `open`, never minted**: registering a component is a person's act.
4. **The record** — Phase 7 items 2 and 3: `## Program-specific work` and the
   `## Decomposition record` table in the detail file, where every component, seam and
   research correction lands and the class sweep is shown; the unsatisfiable items sit
   under their own heading there, routed to the component that owns the mechanism.
5. **`Verified by`** — the proof the person accepted. An existing PRD is named by number.
   When no PRD exists to name, the run writes a **stub** for the composed proof in the shape
   `/zetify:prd:create` Phase 6 gives — the number allocated, the home the slice the proof lands
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

Then `{{target:validate-knowledge}}` clean, and `python3 knowledge/scripts/gen_program_plan.py PG-NN`
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
