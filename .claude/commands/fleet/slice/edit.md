#  Slice — Edit (change a cut's proof, its prerequisites, its promise, or its disposition)

You change **one slice**: one of four columns on its register row — `Verified by`,
`Depends on`, `Done when`, `Disposition` — or the `## Bar` in its detail file. Then you land
it as a merged PR.

**This is a guarded edit, not an authoring session — and it is NOT the shaping twin.** The
page's *open in a terminal instead* offer used to point here, under the heading of the
refining interview, and a person who took it got a command that changes one of four cells and
**refuses everything else**: it cannot pick a `Kind`, cannot author the promise rows and
refusals, cannot write the detail file. Four cells is the job; it is a good job and it is not
that one. The attended twin of `slice:refine` is [`slice:create`](create.md), which creates
*or updates* and holds the discovery interview. Come here when the cut is already right and
one cell on it is wrong.

The cut already exists; nobody is being asked what it is for. What this command owes you is the set of refusals a hand-edit to
`` does not have: that the ids resolve, that the dependency graph stays
acyclic, that the proof you name does not collide with the program's, and — the one no
validator can apply — that you are correcting the record rather than retro-fitting it to
what happened. The bar is that last refusal with teeth on it: a slice's bar is digest-bound
to the exact authored bytes of its `Done when` cell, so the sentence and its decomposition
move together in one commit or the `bars` gate fails the next one.

**The register is a contract, not a table.** Its header is compared cell by cell, so a column
that does not exist cannot be added and a column that does cannot be dropped. There is **no
`status:`** and there are **no dates** on either planning tier; both are gone by decision, and
the exact-header check is what keeps them gone.

**There is a second axis, and it is a decision, not a status.** `Disposition` is the last
column on both registers — the same column the requirement register has carried beside its
derived status for years — and it says what *happened* to the cut: `adopted` (the norm),
`withdrawn: decisions/<file>.md` (stopped, and the record IS the reason), or `superseded by
SL-NNN` (folded into a successor). It never says how far along the cut is: `delivered`,
`closed`, `done` and their kin are ship-state claims and the validator refuses them by name.
Withdrawing a cut is an edit to this cell citing a decision record — **never a row deletion**.
 was the precedent this replaces: its row was deleted, and every citation of its id in
every PRD, decision and register that had ever named it went dark with it. A withdrawn row
keeps its id, its history and its members, and reads `withdrawn` on every board.

Read
[`tracking-and-execution.md`](#) →
"Program & Slice register schema" for the column contract, the prose header of
`` for the record of how each column has been got wrong, and
[`knowledge-model.md`](#) → "Slice and PRD" for
what a slice is.

The slice to edit, and what to change: $ARGUMENTS

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)):
> at start, read the `steps` block below and create **one todo per step**, in order; mark
> each `in_progress` on entry and `completed` on exit. A `gate` that fails stays open with
> the residual noted. The prose sections are the authority; this spine indexes them.
>
> **`needs: a decision` · `may merge: true`** — human-invoked, and **not** dispatched by the tracker daemon: headless it interviews nobody and writes nothing, which is what `a decision` names. Two
> of the three columns carry a fork only a human owns (has the promise changed, or is this a
> new cut? is this prerequisite real, or is it decoration?); the fourth editable thing is a
> `## Bar`, which an agent may sharpen but never widen — *a bar an agent can widen can never
> be red* — and a headless lane answering any of those by default is how a register acquires
> plausible content nobody checked.
>
> **No step declares `produces: [status]`.** None of these four things is a status — a
> slice's completion is computed from its member PRDs and its proof, and every one of these
> cells is an *input* to that reading. A bar is no exception: it is a commitment, and the
> verdict it invites is never written down.

```json
{
  "command": "slice-edit",
  "tier": "core",
  "intent": "Change one slice's Verified by, Depends on, Done when, or the ## Bar in its detail file — with the resolution, disjointness, acyclicity, digest-binding and retro-fit refusals a hand-edit does not have.",
  "sop": "none",
  "needs": "a decision",
  "may merge": true,
  "loads": ["planning-model", "entity-model", "process-interview"],
  "requires": [
    "process-spine", "process-interview", "slices", "gate", "git-workflow", "programs"
  ],
  "optional": ["planning-model", "entity-model"],
  "steps": [
    {"id": "resolve",       "name": "Resolve the slice and read its real state",  "kind": "io",       "actor": "coordinator", "consumes": ["prd"], "body": "step-1-resolve-the-slice-and-read-its-real-state"},
    {"id": "authority",     "name": "Is this command the right authority?",       "kind": "gate",     "actor": "coordinator", "gate": "hard",      "body": "step-2-is-this-command-the-right-authority"},
    {"id": "field-gates",   "name": "The per-field refusals",                     "kind": "gate",     "actor": "coordinator", "gate": "hard",      "body": "step-3-the-per-field-refusals"},
    {"id": "interview",     "name": "Put the fork to the human",                  "kind": "gate",     "actor": "user",        "gate": "advisory",  "body": "step-4-put-the-fork-to-the-human"},
    {"id": "write",         "name": "Write the cell and the bar bound to it",     "kind": "io",       "actor": "coordinator",                      "body": "step-5-write-the-cell"},
    {"id": "validate-land", "name": "Validate, then branch + PR",                 "kind": "gate",     "actor": "coordinator", "gate": "hard",      "body": "step-6-validate-then-land"},
    {"id": "report",        "name": "Report what changed",                        "kind": "author",   "actor": "coordinator",                      "body": "step-7-report"}
  ]
}
```

---

## Step 1: Resolve the slice and read its real state

Match `$ARGUMENTS` against `` on the `SL-NNN` id (accept the `Name`, but
the id resolves). If nothing resolves, stop and say so — **never** create a row here; cutting
a slice is [`slice:create`](create.md), which asks the questions a cut needs.

Read:

1. **The row** — every cell, including the ones you are not changing. `Program`, `Kind` and
   `Done when` are the context for every judgement below.
2. **The detail file** `knowledge/slices/SL-NNN.md`, if it has one — why these PRDs ship
   together, what sequencing the existing `Depends on` encodes, and **whether it carries a
   `## Bar`**. If it does, that bar's digest is bound to the exact authored bytes of the
   `Done when` cell you may be about to change, so the bar is already part of this edit
   before you have decided anything else about it.
3. **The member PRDs.** Membership is authored *only* as `slice: SL-NNN` in each PRD's own
   frontmatter, so that query **is** the member list. Record each one's `status:`.
4. **The program's row** in `` — specifically its `Verified by`. You need
   it for the disjointness refusal, and you need it *before* you name a slice proof, not after
   the validator rejects the commit. Read its `Disposition` too: a cut under a withdrawn or
   superseded program is out of the plan with it, and an edit to its proof or its edges is an
   edit to a record nobody is going to read forward.

Then derive, and state in your report, the three readings that decide what is allowed:

- **Live PRDs** — any member not `shipped`/`cancelled`. A slice with at least one is **active**
  and counts against the active-slice ceiling (`slot:slices`).
- **All-terminal** — every member terminal, at least one `shipped`. This is the state where an
  empty `Verified by` stops meaning *not proven yet* and starts meaning *will never be
  proven*, and where the validator fails the commit ().
- **Abandoned** — every member `cancelled`. Needs neither a proof nor a waiver.

## Step 2: Is this command the right authority?

**Three columns and one prose section are editable here and nothing else**, because the rest
are either the row's identity or an edge with its own authoring command:

| Column or section | Here? | If not, where |
|---|---|---|
| `Verified by` · `Depends on` · `Done when` · `Disposition` | **yes** | — |
| the detail file's `## Bar` | **yes** | — |
| `ID` | never | Permanent and never reused — a PRD that shipped a year ago may still cite it. There is no rename. |
| `Name` · `Kind` · `Components` | no | [`slice:create`](create.md), which creates **or updates** a cut and holds the naming rule and the kind test |
| `Program` | no | Re-parenting a cut is a **re-cut**, not an edit: the roll-up edge is what the slice *is for*. Cut the new slice and let the old one finish or be abandoned |
| a status · a start · a target · a milestone | **no such column** | None of the four exists on either register and none may be added; the header check refuses them, which is the intended answer. `Disposition` is not one of them: it records a decision, and a ship-state word written into it is refused by the validator with the reason |

**The bar is the one editable thing that is not a column**, and it is admitted here for a
plain reason: it is slice-scoped prose in `knowledge/slices/SL-NNN.md`, it has to be
editable by something, and this is the command that owns slice-scoped edits. Authoring one
from nothing is still [`slice:create`](create.md) Step 5c's offer, made at the cut where the
promise is fresh; what lands here is a change to a bar that already exists — most often
because the sentence it decomposes has just moved.

If the ask is one of the refused rows, say which command owns it and stop. **Do not
half-satisfy the request** by editing an adjacent column that happens to be in scope.

## Step 3: The per-field refusals

Run every refusal that applies **before** you write anything, so a refusal lands in
conversation rather than in a rejected commit.

### `Done when` — the promise, and the one edit that can rewrite history

`Done when` is the one sentence that makes *"is it done?"* checkable. It is a column and not
a paragraph precisely so it cannot be skipped, and it is what every downstream reading of the
cut is graded against.

- **All-terminal slice → refuse by default.** Rewriting the completion condition of a cut
  whose work is finished is retro-fitting the promise to what shipped: whatever the sentence
  says afterwards, it is now guaranteed to be satisfied. If the record is genuinely wrong,
  that is worth saying out loud and worth landing — but if the *scope* changed, the honest
  shape is a **new cut** with its own `Done when` and a `Depends on` edge back to this one,
  not a rewritten cell. Put that fork to the human (Step 4); never resolve it silently.
- **Live slice, widening → this is the standing-bucket failure.** Scope is fixed at the cut.
  Work that shows up later because this happens to be the open slice on the right component
  is exactly how a nine-PRD program became six containers. Ask outright: is this a
  **correction** of what the cut always meant, or is it **new work**? New work cuts a new
  slice.
- **Live slice, narrowing or correcting → normally fine**, and normally the reason this
  command was reached for.
- **Shape.** One checkable sentence, not a topic — the validator enforces a minimum length
  because a one-word condition is a subject heading. Escape any literal pipe as `\|`; the
  cell is free prose inside a markdown table.
- **Carries a `## Bar` → re-affirm the bar in the same change. This is a hard rule, not a
  note.** The bar is digest-bound to the cell's exact authored bytes, so **any** edit to the
  sentence — a widening, a narrowing, a typo fix, a re-punctuation — breaks the digest, and
  the `bars` check fails the commit until it is re-affirmed against the sentence as it now
  reads. Re-affirming is not recomputing a hash: **re-read every criterion against the new
  sentence, drop or rewrite the ones the new sentence no longer supports, and only then
  recompute the digest — all in this change.** Landing the sentence without the bar hands a
  broken commit to whoever pushes next, and you are the only person who has the changed
  promise in their head: nobody downstream can reconstruct which criteria the edit
  invalidated, so they will re-bless the hash on its own and the bar will have drifted to
  fit what shipped — the exact failure the digest exists to prevent.

### `## Bar` — the observation, and the digest that stops it drifting

A **`## Bar`** is the observation a completion reading cannot make: what somebody would have
to see in a running system to believe the `Done when`. The contract is
[`tracking-and-execution.md`](#) → "The
`## Bar` contract". It is optional and monotone — no bar changes no reading, and a bar can only
ever *withhold* one, never grant it.

- **You may add a criterion, sharpen a RED, replace a `No probe yet.` with a probe that has
  actually been run, and re-affirm a digest. You may not widen.** Loosening a criterion,
  softening a RED until an observation clears it, or deleting one is the human's call and
  nobody else's — mechanically, not ceremonially: *a bar an agent can widen can never be red.*
  Put it to the human in Step 4 exactly as you would a rewritten promise, because it is the
  same act.
- **Never write a verdict into a bar.** A bar is a commitment, of the same class as the
  `Done when` sentence; a verdict is an observation of one deployment at one instant, true now
  and false in an hour with no file changed. `No probe yet.` is an authored answer and stays
  legal; "green when last looked at" is a stored status by another name, and stored mid-tier
  statuses read wrong 33 times in 40.
- **Never invent a probe to fill the column.** A probe nobody has run is worse than the honest
  `No probe yet.` that both existing bars use — and a probe may never be a test file's name or
  a PRD number, because a PRD number is the shipped-artifact fact the bar exists to get past.
- **Shape, which the `bars` check holds an existing bar to:** a `**Scope.**` line saying what
  the criteria are measured against, because a verdict is per-environment; ids of the form
  `SL165-C1` — the slice id with the dash removed, then `-C<n>` — sequential from 1 and unique
  across the whole corpus; a statement and a non-empty probe cell in every row; no
  `**Demonstration.**` line, which is the program tier's form; and a live
  `<!-- done-cell-digest: sha256:... -->` over the `Done when` cell. Renumbering is not
  cosmetic: an id is cited from outside git, so reusing one silently rebinds what an earlier
  citation pointed at.
- **Removing a bar is never a way to clear a stale digest.** The stale digest is the gate asking
  whether the criteria still hold; deleting the section answers it by deleting the question.
  Removal is the human's call, on the same footing as widening.

### `Verified by` — this slice's OWN proof

It answers *"does this slice do what it said?"* — a different question from the program's,
which asks *"do these work together for a person?"*.

- **Every named entry must resolve** — to a real PRD number, or as `drill:<stem>` to a real
  `knowledge/drills/<stem>.md` that is `type: drill-record` and carries a `verdict:`. A drill
  record is a proof on the same terms as a PRD: shipped when its verdict is `passed`,
  outstanding when it is `failed`, and refused when the file is missing, is not a record, or
  says neither.
- **Disjointness is fatal, and here it runs in the other direction ().** If the PRD —
  or the drill record — you are about to name is already this program's `Verified by`, the
  write creates the collision that collapses the program's completion condition into this
  slice's. **The program side changes, never the slice's** — so name the proof on the slice,
  and clear or repoint the *program's* cell with
  [`/fleet:program:prove`](#). Land both in the same PR; a branch that
  fixes one half fails the commit.
- **Prefer a member PRD** — one carrying `slice: SL-NNN`. A proof from outside the cut is
  legal and occasionally right, but it is a smell worth naming in the report: a slice proven
  by work that is not part of it is usually either mis-cut or borrowing.
- **Never guess a proof to clear the  gate.** On an all-terminal slice with no proof
  there are exactly two honest answers, and picking the greenest member PRD is neither:
  1. a **real** proof — a member PRD whose ACs actually demonstrate the `Done when`; or
  2. a **reasoned per-row waiver** — a `proof_waiver` object on this slice's own row fragment
     (`knowledge/slices/rows/SL-NNN.json`), the explicit *"no proof yet, and here is why"*
     (). The marker is read at the row it excuses and can never be a shared file two
     branches collide on, so a new one is a deliberate argued act — put it to the human. Never
     add a placeholder: a blank or token reason falls through to the gate.
     **Every waiver states its kind — there is no default, and the gate refuses one that does not**
     (the operator's decision of ):
     - `{"kind": "excused", "reason": "..."}` — **this proof is not needed** (superseded, covered by
       another cut, will not be built). An excused cut is **settled**: it no longer holds its
       program, which reads `complete` once its own proof ships and is closed by `program:ship`
       with the waived cut named on the record.
     - `{"kind": "deferred", "owed": "<what is owed, in a phrase>", "reason": "..."}` — **the proof
       is still owed**, to be measured or named later ("once the driver's live measurements land",
       "when the second PRD ships"). A deferred cut is **not settled**: it reads *awaiting proof*,
       its program stays open, and every surface says *"waiting on SL-NNN's proof: <owed>"*. When
       the proof lands, this command names it as `Verified by` and **removes the waiver** in the
       same edit; the cut then reads complete.
       - Add `"needs": "production"` when the owed proof is a **check against production** (a Bar
         walked on the live estate, a measurement on a deployed plane) — : *keep prod
         checks with people*. Fleet never touches production, so such a cut is never asked of the
         fleet: every surface reads *"A production check is owed for SL-NNN (<owed>) …"* and points
         at the attended `program:deliver`, whose "Read the bar" runs the check and names the proof
         with this command once it passes. Leave `needs` off for an owed proof the fleet can produce
         itself (a PRD still to ship, a composed proof still to cut). It is the only value; the gate
         refuses any other, and refuses it on an excused waiver.
     If the reason you would write says *later*, *once*, *when … ships* or *until*, the waiver is
     **deferred**. Choosing `excused` for a proof that is still owed closes a program over work
     nobody has proven — the exact defect the kind exists to stop.
- **An empty cell on a live slice is fine** and needs no defence: it is the honest *not proven
  yet* reading, and a guessed proof is worse than none.

### `Disposition` — the decision axis

Three values, and the cell means exactly one of them; the validator refuses everything else.

- **`adopted`** — the norm. Never written *to* from another value as a way of reopening a
  withdrawn cut: that is a new cut with an edge back to this one, for the same reason a
  finished cut's promise is never rewritten.
- **`withdrawn: decisions/<file>.md`** — the cut stopped. The path is corpus-relative, the file
  **must exist**, and the record is the whole reason: a sentence in the cell is a reason nobody
  can find again, so free text is refused. **Every live member PRD must be terminal first** —
  cancel each one citing the same record in its `cancelled_reason:`, or move it to a cut still
  in the plan; a withdrawn cut holding live work fails the commit (the register said stop and
  the PRD did not). A withdrawn cut owes no proof and no waiver: it is out of 's gate,
  out of every open count, and frozen for  — live work may not wait on it, so an edge
  from a live cut onto it fails the commit too.
- **`superseded by SL-NNN`** — the work folded into a successor. The id must be a row in this
  register (never a `PG-NN`, never itself), and two rows may not name each other. Everything
  said of `withdrawn` applies: it reads `withdrawn` on the board, with the successor named.
- **Never `delivered`, `closed`, `done`, `shipped`, `complete`.** Those are readings the
  derivation makes from the members and the proof; written here they are the stored mid-tier
  status this model deleted, and the validator says so by name. If the cut is done, name its
  proof and let the reading say so.
- **Never a deletion.** See the opening — 's row deletion is the precedent this column
  replaces.

**This is the fork Step 4 exists for.** Withdrawing a cut, or folding it into another, is a
scope decision a human owns; an agent proposes it with the decision record drafted and the
member PRDs listed, and writes nothing headless.

### `Depends on` — prerequisites between cuts

Slice ids (`SL-NNN`) only, **never PRD numbers** — PRD-level `depends_on:` is a different edge
living in PRD frontmatter.

- **Each id must resolve** to a row in this register. A typo does not fail loudly on its own:
  `` typed for `` silently points at a different slice.
- **The graph must stay acyclic.** Order comes from this graph; a cycle makes the whole set
  unorderable. Check the edge you are adding against the existing graph *before* writing —
  the validator will find the cycle, but finding it in conversation is cheaper.
- **No self-edge.**
- **Most edges do not need authoring at all, and this is the important one.** An edge is
  derivable whenever a member PRD's `depends_on:` crosses a slice boundary — that edge already
  exists and the graph already reads it. Author one **here** only for an ordering the PRD
  edges do not imply.
- **A mostly-empty `Depends on` column is not, by itself, a defect to be cleared.** `—` means
  *checked, and there is no prerequisite*; the honest meaning of a column nobody has filled is
  *nobody looked*. Those are different states and only the second is a problem — so filling a
  cell is an act of **checking**, one slice at a time, and never a backfill pass that makes
  the wave chart look layered. **The test for a legitimate edge is hard: cut B genuinely
  cannot start until cut A completes.** "A is upstream conceptually", "B reads better after
  A", "they touch the same component" are all *not* edges, and a fabricated one is worse than
  an empty cell — it delays real work by asserting a prerequisite that was never true, and
  nothing downstream can tell it from a real one.

## Step 4: Put the fork to the human

Every field above has at least one fork this command is not entitled to settle: *correction
or new cut?*, *real proof or waiver?*, *real prerequisite or decoration?*, and — whenever a
re-affirmed criterion would end up looser than the one it replaces — *is this criterion
still the promise, or is it being widened to fit?*

Shaped by the interview card — then act on the answer in the same run:

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

**This is a fork round, not a discovery round.** The slice exists and its promise is on the
page; the alternatives are nameable. If you find yourself unable to name them — you do not
know what the cut is for — you are in the wrong command: that conversation belongs to
[`slice:create`](create.md) Step 2.

**Headless, this command interviews nobody and writes nothing.** It is not fleet-dispatched.
Report the refusals, the reading, and the fork you could not settle, and stop.

## Step 5: Write the cell — and the bar bound to it

**One row fragment at `knowledge/slices/rows/SL-NNN.json`** — the table ``
is generated from the fragments () and is never hand-edited. The fragment's keys, in
this order and no other — the generated table's header is compared cell by cell:

```markdown
| ID | Name | Kind | Program | Done when | Verified by | Depends on | Components | Disposition |
```

- An **empty cell is `—`**, which reads as *none* and never as a value. Never blank, never
  `n/a`, never `TBD`. **`Disposition` is the one column that is never empty**: `adopted` is
  written out, because an empty decision cell says nobody decided.
- Multiple values are comma-separated (`0333, 0341`; `, `).
- Touch **only** the cells Step 2 admitted. Do not tidy an adjacent column on the way past —
  a diff that changes three columns when the ask named one is a diff nobody can review.

**Update the detail file in the same change when the edit changed what it says.** A
`Depends on` edit usually does: `knowledge/slices/SL-NNN.md` is where *why these ship
together and in what order* lives, and a sequencing edge with no explanation is an edge the
next reader will delete. The file carries **no frontmatter key but `type: slice-detail`**, and
where it names member PRDs in prose it carries **no `- [ ]` / `- [x]` checkbox and no
`(shipped)` annotation** — ship-state lives only in each PRD's own frontmatter, and the
validator rejects a copy.

**When the edit touched `Done when` and the slice carries a `## Bar`, the bar moves in the
same commit.** Rewrite or drop the criteria the new sentence no longer supports first, then
recompute the digest from the register **after** the new cell is written — never from the
sentence in your head, and never with a hand-rolled `sha256`:

```bash
python3 knowledge/scripts/fleet.py digest -k knowledge <slices-register> SL-NNN
```

Paste the 64 lowercase hex into `<!-- done-cell-digest: sha256:... -->`. That is the same code
the gate digests with, so it agrees by construction; anything else is a hash that disagrees
with the reader for reasons nobody can see.

**Nothing else moves.** Not the row fragment's filename (no row is being added), not any PRD's
frontmatter, and not the program register — except the one
case Step 3 names, where clearing a colliding program proof rides in the same PR.

## Step 6: Validate, then land

1. `make validate-knowledge` — **clean, or the edit is not landed.** It
   is the same check the pre-commit hook runs: header shape, id resolution, the slice DAG's
   acyclicity, the  proof collision, and the  all-terminal proof gate. If it
   fails, **revert the cell and re-decide** — never edit around a validator finding, and never
   reach for a baseline regeneration to make one go away.
2. **The `bars` check, whenever the detail file or the `Done when` cell moved.** It is what
   holds an existing bar to its shape and its digest to the cell as it now reads:

   ```bash
   python3 knowledge/scripts/fleet.py check --only bars --repo .
   ```

   A **stale digest** finding means the sentence moved and the criteria did not: the repair
   is to re-affirm them, never to re-bless the hash on its own. An **absent** bar produces
   nothing here — that is the contract, not an oversight.
3. Branch, commit, PR, auto-merge on green — per
   [`tracking-and-execution.md`](#) →
   "Git workflow". Doc-only still goes through a PR; the fleet identity has no
   direct-to-`main` path. Watch it to `state: MERGED` (`python3 knowledge/scripts/gh_pr_merge_state.py <pr> --watch` — `queued` is pending, and `ejected`, removed from the merge queue while its own checks read green, is red CI); a conflicted PR shows **zero** checks
   rather than failing ones, and this register is touched by nearly every knowledge PR, so a
   second conflict after a confirmed green is normal here.
4. The commit message states what the cut now promises, or what it now waits on, and why —
   not which cell moved.

**Do not touch the tracker.** A slice is a **label**, not a Project; the `prd-projection` pass of the
fleet's `corpus-sync` loop reconciles it once the merge lands on `main`, and nothing here reads tracker state back. Slice-to-slice `Depends on` is not
projected to the tracker at all — the dependency view is the fleet board's **Dependencies** page
(every cut not yet `complete`, in waves, each node stating what it waits on and what waits on it),
and the program page's **"What must ship to prove this"** narrows that same graph to the closure
between one program and its proof. A `Depends on` edit here moves what those two draw on the next
sync and moves nothing the fleet dispatches on — that is still issue-level `blockedBy`.

## Step 7: Report

The slice, each cell's **before → after**, the refusal each edit had to survive, the reading
after the edit (live / all-terminal / abandoned, and the active-slice count `n/<slot:slices>`), whether
the detail file moved, and the PR URL. If the slice carries a `## Bar`, say whether it moved
— and when a `Done when` edit forced a re-affirmation, name every criterion dropped or
rewritten and state that the digest was recomputed from the new cell rather than carried
over. If the run ended in a refusal, name the command that
owns the ask instead. If a `Verified by` edit forced a program-side clear, say which program
and that its reading moved off `complete`.

---

## Rules

- **Four columns and one section, and nothing else.** `Verified by`, `Depends on`,
  `Done when`, `Disposition`, and the `## Bar` in the detail file. Identity and the roll-up
  edge are not editable here; a status, a start and a target are not columns at all.
- **Never create a row.** No row resolves, no edit — cutting a slice is `slice:create`, which
  asks the questions a cut needs and checks the ceiling.
- **Never write a status on a slice**, here or anywhere. Completion is computed — every member
  PRD terminal **and** the proof shipped — every time anyone reads it, which is why no column
  holds one. **No dates either**, at any tier. `Disposition` is a decision — `adopted`,
  `withdrawn: <record>`, `superseded by <id>` — and a ship-state word in it is refused.
- **Withdrawal is an edit citing a decision record, never a deletion.** A deleted row takes
  every citation of its id with it (); a withdrawn one keeps its id and reads
  `withdrawn`. Its live members are cancelled or re-homed first, and it owes no proof after.
- **Never rewrite the promise of a finished cut to fit what shipped.** New scope is a new cut,
  with an edge back to this one — and never re-aim its bar at what shipped instead, which is
  the same act with a hash in front of it.
- **A `Done when` edit re-affirms the bar in the same change.** The digest binds the criteria
  to the cell's exact authored bytes, so any edit to the sentence breaks it: re-read every
  criterion against the new sentence, drop or rewrite what it no longer supports, recompute
  the digest — one commit. Landing the sentence alone is a broken commit for whoever pushes
  next, and only the person editing the sentence has the changed promise in their head.
- **An agent may sharpen a bar, never widen one.** Loosening a criterion, softening a RED,
  deleting one or removing the section is the human's call — a bar an agent can widen can
  never be red. And never write a verdict into a bar: a bar is a commitment, and an
  observation of one deployment at one instant is a stored status by another name.
- **`Depends on` is checked, never backfilled.** An edge is legitimate only when one cut's work
  genuinely builds on the other's. It is **order**: it ranks the prerequisite up behind the cut
  that needs it and the board draws it, but it never holds a PRD back — a PRD dispatches once its
  own `depends_on:` have shipped and its own `blockedBy` is resolved. A fabricated prerequisite
  misorders real work and is indistinguishable from a real one afterwards.
- **The graph stays acyclic and every id resolves.** Both checked before the write, not after
  the commit is rejected.
- **Proof disjointness is fatal, and the program side changes.** A PRD — or a drill record —
  may not be both this slice's proof and its program's (). Fix it with
  [`program:prove`](#), in the same PR.
- **Never guess a proof, and never regenerate the waiver baseline to clear a gate.** On an
  all-terminal slice the answers are a real proof or an argued per-row `proof_waiver` that states
  its kind — `excused` or `deferred` — and the programs baseline may shrink, never grow.
- **Structure in the register, prose in the detail file, never both.** A detail file carries
  no frontmatter but `type: slice-detail`, and no ship-state copied off a PRD.
- **Human-invoked only.** Not dispatched by the tracker daemon, and headless it writes nothing.
- **One source of truth:** the PRDs' frontmatter `status:`. Never read tracker state back.
