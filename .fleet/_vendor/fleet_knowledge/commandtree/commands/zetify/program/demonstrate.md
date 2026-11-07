# <!-- home -->Zetify<!-- /home --> Program — Demonstrate (a shaped program gets its proof named, or honestly none, on the fleet)

You decide **which proof counts** for one program — or that none does yet — and you write that
decision the way [`program:prove`](prove.md) writes it: the `Verified by` cell of the program's
row, and the program's own **`## Bar`** in its detail file. That is exactly what `prove` produces
with a person at a terminal, and **this command is that judgement, run headless**: the same
demonstration sentence, the same criteria, the same four refusals, the same three honest
outcomes — with every fork it would put to a person asked by writing through the fleet's
question channel, answered on the program's own page, and landed as one merged PR.

**Before you write a program file, read its docs page** (under `.fleet/docs/`; `read_doc <page>` when Fleet's tools are in the session): `knowledge-base/programs`.

**You are a composition, not an authority.** Every rule about *what a proof is* and *how it is
judged* lives in `prove.md`, and this file cites it rather than restating it: the claim you read
is *Step 1*, the demonstration sentence and its sentence gate are *Step 2*, the `## Bar` and its
criteria, its tier gate and its probe rule are *Steps 2–3*, the search is *Step 4*, the four
refusals R1–R4 are *Step 5*, the three honest outcomes are *Step 6*, the one cell is *Step 7*,
the validation is *Step 8*. Its Rules bind this run in full — never manufacture a proof, never
borrow a slice's, the sentence before the search, `No probe yet.` beats an invented probe, a bar
is never widened. What this file owns is the **mapping**: which of its questions become cards in
which of the two rounds, which the run decides and reports, and which are withheld.

**The default is still "no proof yet", and here it is the answer a stalled round gets.** An empty
`Verified by` reads *unproven*, which is true of a program nobody has demonstrated. A proof the
person did not accept is never written, and a cell is never filled to let the program move on.

**Headless only.** A person at a terminal has the richer command — `prove` itself, with a real
search fan-out and the person in the room — and the fleet routes a mission by command string, so
this verb exists for the button and for a driven program, nothing else (Step 0). It is its own
verb and not a mode of `program:prove`, for `prd:fill`'s reason: no verb may be a prefix of
another's, and the attended command must keep working as it does.

The program to prove: $ARGUMENTS

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps`
> block below and create **one todo per step**, in order; mark each `in_progress` on entry and
> `completed` on exit. The interview step is a bounded loop — add one todo per round under it.
> No step writes a `status:` or a date, and none may be added that does — a program's ship-state
> is derived from its slices and its proof. `Verified by` is the authored *input* to that
> derivation and is not a status, so no step declares `produces: [status]`. The prose steps
> below are the authority; this spine indexes them.
>
> **`needs: answers` · `may merge: true`** ([`spine.md`](../../../process/spine.md)) — this
> command is dispatched headless and asks **by writing**, which is why `needs: answers` still
> dispatches: the fleet refuses only `needs: a decision`. It merges its own PR for the reason
> `prove` does: the PR carries one register cell, a bar and, at most, one numbered stub — nothing
> that ships to a customer. It must never *block* on a human. **`AskUserQuestion` is not
> available to you and never will be.** Your escalation path is a `questions` result file plus
> the end of your turn, and the answers come back by resumption of this same session — the
> shared contract inlined under *The headless contract* below.

```json
{
  "command": "program-demonstrate",
  "tier": "core",
  "sop": "none",
  "needs": "answers",
  "may merge": true,
  "intent": "Name the composed proof of a shaped program on the fleet, or establish that none exists yet and leave the cell honestly empty: the demonstration sentence, then the proof and the bar, asked through the fleet's written question channel over at most two rounds, then written exactly as program:prove would at a terminal — the one Verified by cell and the program's bar, at most a numbered proof stub — by one merged PR and one landed result, with no status and no dates.",
  "loads": ["process-shaping-headless", "programs", "entity-model", "planning-model"],
  "requires": [
    "process-spine", "process-interview", "process-shaping-headless", "programs", "slices",
    "entity-model", "planning-model", "gate", "git-workflow", "file-conventions"
  ],
  "optional": ["feature-areas", "architecture"],
  "steps": [
    {"id": "mode",     "name": "Which way in — the fleet, or a terminal (refused)",          "kind": "decision", "actor": "coordinator",                 "body": "step-0-which-way-in"},
    {"id": "read",     "name": "Read the program's claim, its cuts and its bar",             "kind": "io",       "actor": "coordinator",                 "body": "step-1-read-the-claim"},
    {"id": "refusals", "name": "The refusals — by sentinel, before any question",            "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "step-2-the-refusals"},
    {"id": "rounds",   "name": "The rounds — the demonstration, then the proof and the bar", "kind": "loop",     "actor": "coordinator",                 "loop": {"max_rounds": 2, "exit": "the person answered the proof and bar round, or the ceiling was reached and what stands is written with its open items"}, "body": "step-3-the-rounds"},
    {"id": "author",   "name": "Write it — the cell, the bar, at most one stub",             "kind": "author",   "actor": "coordinator",                 "body": "step-4-write-it"},
    {"id": "land",     "name": "Land it — the branch, the PR, the merge",                    "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "step-5-land-it"},
    {"id": "landed",   "name": "The landed result, then the sentinel",                        "kind": "io",       "actor": "coordinator",                 "body": "step-5-land-it"},
    {"id": "report",   "name": "Report",                                                      "kind": "author",   "actor": "coordinator",                 "body": "step-6-report"}
  ]
}
```

---

## What to do

### Step 0: Which way in

```bash
printf '%s\n' "${FLEET_RESULT_FILE:-<unset>}"
```

- **Set** → the fleet dispatched you on a program whose proof is to be named: a person pressed
  the button on its page, or its drive reached this step. `$ARGUMENTS` is its register id
  (`PG-NN`), the mission's `## Shaping` block carries the requester, any instruction and the row
  as served, and the payload says which round this is — *The headless contract* §1. Run
  Steps 1–6.
- **Unset** → a person is at a terminal, and this is the wrong verb for them. Say exactly
  this and stop, writing nothing: **This command runs only on the fleet. At a terminal, run
  `/zetify:program:prove PG-NN` instead** — it does the same judgement with you in the room and
  searches the PRD corpus with a real fan-out. **And say that the terminal is not a one-way
  door.** A person who starts by hand and would rather the fleet finished it presses the
  program's own button, and the next round picks up from whatever is committed: the bar already
  written, the cell, the answers already given. Being sent to a terminal must never read as being
  sent there for good.
- **Set, but `$ARGUMENTS` is not a program id, or the block's `kind` is not `program`** → a
  mis-dispatch. Write nothing; sentinel `failed` naming what was wrong; stop.

### Step 1: Read the claim

`prove.md` → *Step 1*, run here in full and **in its order: the claim before the inventory, and
not one PRD opened.** The row; the narrative above the first `##` of the detail file, which is
what is being proved; the cuts whose `program` is this id, each `Done when` and each cut's own
`Verified by`; whether the program's file names a walking skeleton (write the number down now —
refusal R2 depends on it and nothing automated can see it); whether a `## Bar` already exists.

**Plain words.** The demonstration sentence is read by the people who read the headline, so it is
bound by `create.md` → *Step 2b*, as `prove.md` Step 2 says. Cite, never restate.

### Step 2: The refusals

By sentinel, before any question, in the form *The headless contract* §9 gives — no branch, no
file, no result document, a summary naming the move that releases it:

- **No row resolves** for the id → `failed`, a mis-dispatch.
- **`Disposition` is not `adopted`** → `needs-decision`: *"this program is withdrawn (or
  superseded); its proof is nobody's to name — reinstate it in the register first, or leave
  it"* (`prove.md` Step 1.1).
- **The program has no cut at all** → `needs-decision`: *"nothing is cut yet, so there is no
  proof to compose across cuts — shape the program first"*. A composed proof is a claim about
  what several cuts do together, and a program with none has nothing to compose.
- **The program is already proven and carries a bar** — `Verified by` names a proof that
  survives all four refusals (Step 3, Round 2's check, run here on the named cell) and a `## Bar`
  with a demonstration exists → nothing is owed. Write **no branch, no file and no result
  document**, and end with the sentinel `success`, `pr: ""`, and a summary that says the proof is
  named and the bar is on file. This is the one ending the sentinel table has no row for, and it
  exists so that re-dispatching a finished program changes nothing.

### Step 3: The rounds

Two rounds at most, at most four questions each, every one shaped by the rail in *The headless
contract* §3 — which is the interview card applied to a written medium, and the card is what the
person's reading is graded against:

<!-- include: process/interview-card.md -->

Each round's brief opens with which round this is of up to two, restates what is decided, and
says what this round settles. **The aspect each card changes** (*The headless contract* §3): the
demonstration sentence → `bar`, the proof → `proof`, the bar as a whole → `bar`. Every round's
`draft` carries what is decided so far; Round 2's carries `proof` and `bar` as briefed and is
marked `"confirm": true`.

#### Round 1 — the demonstration (`prove.md` Step 2)

**The order is the guard, and the rounds are what make it physical on the fleet.** This round
asks for the sentence **before a single PRD is opened** — so the sentence cannot have been fitted
to what already shipped. Write each candidate from the program's own claim, gate every one
against every cut's `Done when` (`prove.md` → *The sentence gate*), and **offer only sentences
that pass** — an option a single cut would make true is a slice's condition wearing the program's
name, and it is never offered.

| Card | What it establishes | Options |
|---|---|---|
| **The demonstration** | the one sentence that would be true only if the whole thread runs — what a named person does, end to end, across every surface the program claims, naming a surface a customer touches | two to three candidate sentences the run drafts from the claim, each a different reading of which thread is the composed one, one recommended; free text for a sentence of the person's own. The rationale on each says what the person would see and what a doubter could not wave away |

Nothing else belongs in this round. Two things skip it entirely:

- **A `## Bar` already carries a demonstration** → it is the sentence, verbatim. A rewritten
  demonstration is not a repair, it is a new bar (`prove.md` → *Repairing an existing bar*), and
  a new bar is the person's act — if the existing one is slice-shaped, that goes into
  `landed.open` and the round is not spent rewriting it. Go to Step 3's search with what is on
  file.
- **The claim admits exactly one composed reading** → the run still writes the sentence, and
  Round 1 is folded into Round 2's brief as a line the person confirms there. Asking a
  one-option question is not a fork.

Then STOP: write the `questions` result, the sentinel `needs-decision`, end the turn.

#### Round 2 — the proof and the bar (`prove.md` Steps 3–6 — draft, then confirm)

On resume, consume Round 1 (*The headless contract* §4) and only now open the corpus:

1. **The criteria** — `prove.md` → *Step 3*, including the tier gate: a criterion one cut can turn
   green alone comes off, and **is reported, never written into the cut's file from here**. The
   `Probe` rule holds unchanged — `No probe yet.` beats an invented probe, and the brief says how
   many rows carry a real one and how many do not.
2. **The search and the four refusals** — `prove.md` → *Steps 4 and 5*, run sequentially in this
   session (a fan-out is not assumed on the seat). Drills are searched in the same pass. Every
   candidate gets all four verdicts, R1 to R4, and a verdict cites a line that executes.
3. **The outcome** — `prove.md` → *Step 6*'s three, and there is no fourth: **(a)** a candidate
   survived all four; **(b)** nothing survived but the sentence is real, so a proof is owed;
   **(c)** nothing is demonstrable yet. The run decides which outcome is *true*; the person decides
   what is done about it.

**The brief IS the draft**, eight lines at most: the sentence as confirmed; the program's `Scope`
line; how many criteria, how many with a real probe, what came off as a single cut's; each
candidate and which refusals it survived or failed and why, in plain words; and what each option
below would leave on the page. The fuller bar is what Step 4 writes and the brief says it is in
the draft.

| Card | What it establishes | Options |
|---|---|---|
| **The proof** | what the `Verified by` cell says — `prove.md` Step 6 | **(a) name the candidate** — one option per survivor, at most two, offered **only when it survived all four refusals**, each saying which it survived and how; **(b) cut a proof** — write a numbered proof stub carrying the sentence, and name it now (Step 4.3), so the program's own planning fills and designs it next; **(c) leave it unproven on purpose** — the waiver: the cell stays empty, the program reads *unproven*, and nothing will mark it complete until a proof is named. Recommended: (a) when a survivor exists; else (b) when the sentence is real and no composed path exists yet; else (c). Option (c) is offered whenever it is honest — the sentence cannot be written, the row is really a theme, or no surface a customer touches is in scope — and is **never** the recommendation merely because the work is hard |
| **The bar** | whether the criteria become a commitment on file — the bar is the person's act (`prove.md` → *The bar is the human's act*) | **write it as briefed** (recommended — it lands even when the cell stays empty, because it is what tells the next reader what a proof has to show); **write it with the changes the person names** (free text); **do not write a bar** — the cell decision stands alone. Each option says what the next reader loses or gains |
| **A borderline criterion** | only when `prove.md`'s tier gate leaves one genuinely open (*it needs the whole thread* / *one cut could close it alone*) | two options, the stronger first; one card per such criterion, in the slots the two cards above leave |

**At the ceiling — two rounds asked, or an answer missing — write what stands** (Step 4) and put
every unsettled item into `landed.open` verbatim. **An unanswered proof card writes nothing to the
cell**, which is the honest reading of *no proof yet*; an unanswered bar card writes no bar. Never
fill either on the person's behalf, and never treat a missing answer as a choice of (a).

### Step 4: Write it

Only after Round 2's answer, or at the ceiling. Everything is authored **exactly as `prove.md`
says**, cited and never restated:

1. **The bar** — `prove.md` → *Steps 2–3*: top-level `## Bar` in the program's detail file, the
   `**Scope.**` and the `**Demonstration.**` verbatim as confirmed, the criteria table under
   them, the tier argument under the table. Created with the typed header `slot:file-conventions`
   gives a detail file if none exists. **An existing bar is only ever added to or tightened here**
   — a deletion, a loosened criterion or a softened RED is the person's call and is never slipped
   in; it goes to `open` as a proposal. No digest, no verdict, no date.
2. **The cell** — `prove.md` → *Step 7*, the one `Verified by` cell and nothing else in the
   register (not `Requires`, not `Name`, not `Kind`, not `Disposition`): the candidate the person
   chose under (a), or the stub's number under (b). Under (c), and whenever the proof card went
   unanswered, **the cell is not touched** — and a wrong proof already there is cleared to `—`
   only when the person picked (c) on a card that said so.
3. **The stub, under outcome (b) only** — the shape `prd:create` → *Phase 6* gives: the number
   from `python3 knowledge/scripts/validate_id_collisions.py --allocate PRD 1`, `status: stub`
   and nothing else authored, **placed in the last cut of the build order** (the one where the
   composed thread closes) and never one the program's other cuts already name as their own proof
   (R1). Its `## Brief` holds the confirmed demonstration sentence as the ask, verbatim, and says
   it is the program's composed proof. The cell then names the number, which resolves. A stub
   is live work, so the ceiling `prd:create` → *Phase 6* enforces applies: a cut already at it is
   a refusal by sentinel, `needs-decision`, naming the count and the move — *close a PRD in that
   cut, or pick another cut*.
4. **The finding** — `prove.md` → *Step 7*'s last paragraph: one short prose record in the
   detail file of why this proof is the composed one, or why none exists yet. Prose there,
   structure in the register, never both.
5. **Withheld, and reported in `open`** — the tracker filings `prove.md` Step 6 describes for
   outcomes (b) and (c) (**a headless run makes no tracker write**: the ask they would carry is
   already on disk as the bar and the stub, and the park is the landing's `open` list and the
   page), every cut's own bar, and any criterion taken off the program's bar as one cut's.

Then `{{target:validate-knowledge}}` clean, and `python3 knowledge/scripts/fleet.py check --only bars
--repo .` — `prove.md` → *Step 8*. R1 is enforced there: when it fires, the fix is on the program
side, and the move is to revert the cell and re-decide.

### Step 5: Land it

*The headless contract* §6, unchanged except for two things it names for other commands: the
deterministic branch is **`agent/prove-<key>`** (a shape run already merged `agent/shape-<key>`
under the same program key), and **the prior attempt is found by head branch**, never by the key
alone —

```bash
gh pr list --state open   --head "agent/prove-<key>" --json number,headRefName,url
gh pr list --state merged --head "agent/prove-<key>" --json number,mergedAt,url
```

— because the program's shaping PR carries the same key in its title and would read as *"the work
is already on `main`"* when it is a different piece of work. Every id re-checked against the tip
at push, `gh pr merge --auto --squash` armed the moment the PR opens, and the PR driven to
`state: MERGED` with `python3 knowledge/scripts/gh_pr_merge_state.py <pr> --watch` (`queued` is
pending; `ejected` from the merge queue is red CI) — a generated-ledger conflict taken one side
wholesale with its generator re-run.

Once merged, the `landed` document to `$FLEET_RESULT_FILE`, written whole and read back, in §7's
shape with a program's `changed`:

```json
{"kind": "landed", "landed": {"kind": "program", "id": "PG-NN", "href": "program:PG-NN", "pr": "<the merged PR's URL>", "files": ["<every path the PR changed>"], "summary": "<one plain sentence: what now stands — the proof named and the bar written, or no proof on purpose>", "changed": {"verifiedBy": "NNNN"}, "open": ["<each unsettled or withheld item>"]}}
```

`verifiedBy` is the cell as it now reads — the number, `drill:<stem>`, or `—` when the cell was
left empty on purpose or by the ceiling. **A landing whose only change is a bar, or a waiver that
leaves the cell `—`, is still a landing**: its `files` are the bar and the finding, and its
`summary` says plainly that the program is unproven and why. Then the sentinel: `success` with
the PR URL. A PR that could not be brought to merge in this run is `partial` with the PR URL and
**no `landed` file** — §8's table, and never `done`.

### Step 6: Report

Nine lines, for a human reading the transcript: the id; the rounds asked (`r of 2`); **the
demonstration sentence** (always — it is the run's real product); the candidates with their four
verdicts; the outcome, (a), (b) or (c), and whether the person chose it or the ceiling did; what
was written and what was deliberately not; the bar's criteria count against real probes, and what
came off as one cut's; the PR and its state; the result written (`landed` | `questions` | none —
why) and the sentinel word.

---

## The headless contract (shared)

<!-- include: process/shaping-headless.md -->

---

## Rules

- **Cite, never restate.** The judgement, the four refusals, the tier gate and the probe rule are
  `prove.md`'s; this file maps its questions onto rounds and owns none of its rules. A sentence of
  theirs copied here is the copy that drifts.
- **Never manufacture a proof.** No placeholder, no plausible-looking number, no proof chosen
  because it is the best of a bad set, never a slice's own, never the program's own walking
  skeleton. An empty cell reads *unproven*, which is true; a borrowed one is a lie the
  derivation believes.
- **The sentence before the search, every time.** Round 1 asks for it before a PRD is opened;
  that order is the only structural defence against choosing the proof to fit what shipped.
- **The person decides the sentence, the proof and the bar. The run decides the candidates, the
  verdicts, the stub's number and the file shapes — and reports each.** Nothing is asked that a
  file answers; nothing is decided that a person owns.
- **Every fork is a card with a recommendation — and a waiver is on it where it is honest.** The
  person accepts the recommended answer or argues with it; the card never asks them to invent one,
  and never argues only for the option the run favours.
- **A bar is never widened, and a program's bar is top-level with no digest.** Additions and
  tightenings only; the rest is a proposal in `open`.
- **One cell, one file — plus the bar and at most one numbered stub.** `Requires` belongs to
  `decompose`; no status, no date, no column invented.
- **No tracker write, no `AskUserQuestion`, no cut's bar written from here.** Each is withheld and
  reported in `open`.
- **Headless only.** A terminal is refused in one sentence naming `program:prove`, which is left
  exactly as it was.
