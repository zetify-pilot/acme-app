#  Program — Prove (name or repair a program's proof)

You decide **which proof counts** for one program, and you write that decision into the one
cell that holds it: `Verified by` in the program's row fragment at
`knowledge/programs/rows/PG-NN.json` (the table `` is generated from the
fragments). On the way there you compose the
observation that cell cannot make — the program's **`## Bar`** — and you author it into
`knowledge/programs/PG-NN.md` before you have opened a single PRD.

**This is a judgement, not an edit.** The edit is one table cell; the work is establishing
that the proof you are about to name actually demonstrates *the composed thread across this
program's slices* — a claim none of those slices makes on its own. Get that wrong and the
program reads `complete` on the strength of a run that only ever entered one of its parts,
which is the exact failure the column exists to prevent.

**Your default answer is "no proof yet".** An empty `Verified by` reads **`unproven`**, and
`unproven` is a *true statement* about a program nobody has demonstrated. A borrowed cell is
a lie, and it is a lie the derivation believes: completion is arithmetic over the named
proof's `status:`, so a wrong cell does not sit there looking wrong — it turns the program
green. **You never write a placeholder.** If the honest outcome is *"this needs a proof PRD
that does not exist yet"*, that is the outcome; say it, and leave the cell alone.

**A proof is a PRD or a drill record, and the cell accepts both.** `Verified by` names a PRD
number, or `drill:<stem>` for `knowledge/drills/<stem>.md` — the harness-produced record of an
observation (a failover drill, an estate move, a Pod-backend proof), which the derivation reads
as shipped exactly when its frontmatter says `verdict: passed`. A program whose composed proof
*is* the observation names the record; it does not manufacture a proof PRD to close, which is
what six programs did in five days when the cell accepted only a PRD. **The
four refusals below apply to a drill record unchanged**: it may not be one a slice under this
program names, it may not be the walking skeleton's own drill, it may not be slice-shaped, and
it must drive the composed path across every surface the program claims.

**The bar is the other half, and it used to be thrown away.** Step 2 has always composed the
sentence a bar needs — what a named person does, end to end, across every surface the program
claims — and then spent it on a report. That sentence *is* a program bar's
`**Demonstration.**`, and the reading it survives is exactly the one a bar exists to get past:
**`status: shipped` proves a capability exists, never that it is connected** (PRD 0252 — the
composed path returned 503 across seven `shipped` upstream PRDs). So the sentence is now
written into the program's own file and decomposed into criteria a reader can go and look at.
Read [`tracking-and-execution.md`](#) →
"The `## Bar` contract" before you author one.

> **You can hand this back to the fleet at any point.** The fleet runs this same judgement
> headless as [`program:demonstrate`](demonstrate.md) — for a driven program it is the step that
> names the proof — asking each fork by writing and landing one merged PR. A person who started
> here by hand and would rather the fleet finished it takes the program's own page, and the next
> round picks up from whatever is committed: the bar already written, the cell, the answers
> already given. This command is unchanged and stays the attended path.

---

## Why this command exists, and what it is not

Four commands touch `Verified by` and they are deliberately different jobs:

| Command | What it does with the cell | Why not this one |
|---|---|---|
| [`program:decompose`](decompose.md) Phase 7.4 | **Authors** it at decomposition time, while the outcome is still in your head | It is a whole working-backwards pipeline — vision gate, research fan-out, gap rows, `Requires` rewritten. Re-running it to fill one cell rewrites the decomposition, and for a program whose slices are already finished it is *actively wrong*: it derives gaps, and there are none left |
| [`program:deliver`](deliver.md) §1a | **Consumes** it, and **refuses to run** while it is empty — a cycle over a program with no proof named is a cycle toward no finish line, and its refusal names this command as the one thing to do first | It never writes the cell (its hard rule 4b), and it must not: a driver that named the proof it was driving toward would be choosing the finish line to fit what it was building — the reasoning-backwards failure, from the one seat where it is most tempting |
| [`program:ship`](ship.md) | **Reads** it and refuses a proof that does not drive the composed path; repoints it on a gate-4 failure | It refuses to *author* one on purpose — a program with no proof gets sent back rather than fitted with one at closing time |
| **this command** | **Names** a missing one, or **repairs** a wrong one — and authors the program's `## Bar` from the sentence it has to compose anyway | — |

**This command is the precondition of driving, not only the repair at the end.** Until the
gate above existed, `deliver` ran on any program with a `Requires` or `Verified by` cell
filled, and the board offered *prove* and *deliver* side by side on a program that had no
proof — so the ordinary way here was late, after cycles had already run against an empty
cell, and one of those cycles had dispatched a proof PRD of its own that was then cancelled
as slice-shaped. Now nothing drives a program until its proof is named: the board's one
next step for such a program is this command, and `deliver` says the same in plain words
when asked. So you arrive here at two moments, and the guard below is the same at both — at
the **start**, on a program that was decomposed without its proof (the corpus is small and
the temptation weak), and at the **end**, on a program whose work is done.

**The hazard `ship` names is this command's whole design problem.** *"Choosing the proof
after the work means choosing it to fit what already shipped, which is the reasoning
backwards."* That is exactly the position you are in at the second of those moments: you
arrive at a program whose work is done, and the corpus of shipped PRDs is right there, and
every one of them is green.

**So the order of the steps below is the guard, and it is not negotiable.** You write the
demonstration sentence **from the program's own claim, before you look at a single PRD**
(Step 2), decompose it into criteria (Step 3), and only then search for something that
satisfies it (Step 4). Search-first produces a proof chosen to fit the corpus and dressed up
as a judgement. If you find yourself reading PRDs before you have written the sentence, you
have already failed.

**The bar makes that order physical rather than habitual.** The demonstration is on disk, in
the program's own file, before the corpus has been read: a sentence committed first is one the
corpus has to satisfy, and a sentence written afterwards is one fitted to what shipped. The
two are indistinguishable once written, which is why the order — not the reader's judgement —
has to be the thing carrying the weight.

Read [`knowledge-model.md`](#) → "Program" for
what a program is and what proving one means,
[`tracking-and-execution.md`](#) →
"Program & Slice register schema" for the register contract, and the prose header of
`` — it carries the record of every way this cell has been got wrong.

The program to prove: $ARGUMENTS

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)):
> at start, read the `steps` block below and create **one todo per step**, in order; mark
> each `in_progress` on entry and `completed` on exit. A `gate` that fails is a todo that
> stays open with the residual noted. The prose sections are the authority; this spine
> indexes them.
>
> **`needs: answers` · `may merge: true`** — this command is human-invoked and is **not** dispatched by the
> the tracker daemon. Its central product is a judgement a human owns (Step 6), and its honest
> outcome is frequently *"write nothing"*, which no autonomous lane can be trusted to
> prefer over filling a cell. Its second product — the `## Bar` — is a commitment only a
> human may author, which is why `bar-assent` is a **hard** human gate: a headless run does
> not clear it, and the residual is a bar proposed in the report and written nowhere.
>
> **No step declares a `bar` artifact, because there is none to declare.** The Artifact
> vocabulary in [`spine.md`](../../../process/spine.md) does not
> carry one and invariant 5 fails a step that invents it. A bar is authored prose in the
> program's detail file; the spine indexes the steps that author it, never the section
> itself.
>
> **No step declares `produces: [status]`, and that is deliberate.** `Verified by` is not a
> status — it is the authored *input* to a computed reading, naming *which* proof counts.
> Labelling the register write as producing a `status` would encode in the spine the exact
> confusion the register header exists to refuse.

```json
{
  "command": "program-prove",
  "tier": "core",
  "intent": "Name a missing composed proof for a program, or repair one that does not prove the thing — or establish that no adequate proof exists and leave the cell honestly empty.",
  "sop": "none",
  "needs": "answers",
  "may merge": true,
  "loads": ["programs", "entity-model", "planning-model"],
  "requires": [
    "process-spine", "process-interview", "programs", "gate",
    "git-workflow", "file-conventions", "planning-model", "entity-model"
  ],
  "optional": [
    "slices", "registers-triage-partition", "tracker-identity", "architecture", "feature-areas"
  ],
  "steps": [
    {"id": "resolve",        "name": "Resolve the program and read its claim",       "kind": "io",       "actor": "coordinator",                        "body": "step-1-resolve-the-program-and-read-its-claim"},
    {"id": "demonstration",  "name": "Write the demonstration sentence (before any PRD)", "kind": "author", "actor": "coordinator",                    "body": "step-2-write-the-demonstration-sentence"},
    {"id": "sentence-gate",  "name": "The sentence is not slice-shaped",             "kind": "gate",     "actor": "coordinator", "gate": "hard",        "body": "the-sentence-gate-it-must-say-what-no-single-slice-says"},
    {"id": "author-bar",     "name": "Author the demonstration into the program's `## Bar`", "kind": "author", "actor": "coordinator",              "body": "author-it-into-the-program-s-bar"},
    {"id": "criteria",       "name": "Decompose the demonstration into criteria",    "kind": "author",   "actor": "coordinator",                        "body": "step-3-decompose-the-demonstration-into-criteria"},
    {"id": "tier-gate",      "name": "No criterion a single slice can turn green alone", "kind": "gate", "actor": "coordinator", "gate": "hard",        "body": "the-tier-gate-it-must-be-a-criterion-no-single-slice-can-turn-green"},
    {"id": "bar-assent",     "name": "The human ratifies the bar (headless: propose only)", "kind": "gate", "actor": "user",     "gate": "hard",        "body": "the-bar-is-the-human-s-act"},
    {"id": "find-candidates","name": "Search the PRD corpus for candidates",         "kind": "fanout",   "actor": "subagent", "model": "sonnet", "consumes": ["prd", "acceptance-criteria"], "body": "step-4-search-for-candidates"},
    {"id": "four-refusals",  "name": "The four refusals — a candidate survives all",  "kind": "gate",     "actor": "coordinator", "gate": "hard",        "body": "step-5-the-four-refusals"},
    {"id": "outcome",        "name": "Choose among the three honest outcomes",       "kind": "decision", "actor": "coordinator",                        "body": "step-6-the-three-honest-outcomes"},
    {"id": "interview",      "name": "Put the fork to the human",                    "kind": "gate",     "actor": "user",        "gate": "advisory",    "body": "step-6-the-three-honest-outcomes"},
    {"id": "write-cell",     "name": "Write, repoint or clear the one cell",         "kind": "io",       "actor": "coordinator",                        "body": "step-7-write-repoint-or-clear-the-one-cell"},
    {"id": "validate-land",  "name": "Validate, then branch + PR",                   "kind": "gate",     "actor": "coordinator", "gate": "hard",        "body": "step-8-validate-then-land"},
    {"id": "report",         "name": "Report the verdict",                           "kind": "author",   "actor": "coordinator",                        "body": "step-9-report"}
  ]
}
```

---

## Step 1: Resolve the program and read its claim

Match `$ARGUMENTS` against the program row fragments under `knowledge/programs/rows/` on the `PG-NN` id (accept the `Name` too,
but the id is what resolves). **If the argument is empty**, list the programs whose
`Verified by` cell is `—` — the same set the fleet board draws a terminal **`no proof
named` · *this program can never complete*** node for on the program's own page, and files
*"No proof named. Nothing will ever mark this program complete, and nothing drives it until
one is."* against as its **one** next step (the driver is withheld from that page until the
cell is filled) — and ask which. If it resolves to nothing, stop and say so.

Read, in this order, and read the claim *before* the inventory:

1. **The row** — `Name`, `Kind`, `Verified by`, `Requires`, `Disposition`. **A `withdrawn:`
   or `superseded by` row is out of the plan: stop and say so.** Its proof is nobody's to
   name — the decision record it cites, or its successor, is the answer — and the register's
   other columns are left exactly as they are ([`slice:edit`](#) → "The
   second axis" for what those values mean and how one is written).
2. **The narrative** in `knowledge/programs/PG-NN.md`, if the program has a detail file. The
   text above the first `##` is the customer-facing claim; that is what you are proving.
   Its `## Program-specific work` and `## Decomposition record` sections are mechanism —
   read them for context, never as the claim.
3. **Its slices** — the slice row fragments under `knowledge/slices/rows/` whose `program` key is this id. That
   edge is authored on the child and nowhere else, so that query *is* the slice list. Read
   every `Done when` and every slice-level `Verified by`; you will need both in Steps 2
   and 4.
4. **Whether the walking skeleton is designated.** If the program's own file names a PRD as
   its first thin thread — *"one vertical thread first, not a horizontal sweep"* — write
   that PRD number down now. Refusal R2 turns on it, and it is invisible to every automated
   check.
5. **Whether the program already carries a `## Bar`.** If it does, Steps 2–3 are a *repair*,
   and the direction you are allowed to move it in is constrained — read "The bar is the
   human's act" before you touch a row. If it does not, Steps 2–3 author one.

**Do not open a PRD in this step.** Membership counts and slice completeness are inputs to
`program:ship`, not to this command; what you need here is the claim.

## Step 2: Write the demonstration sentence

**Write it in plain language.** Everything you author above a detail file's first `##` obeys [``](create.md) → *Step 2b: Write it in plain language* — literal title, headline inside 240 characters carrying a concrete example, ordinary words. That rule is authored once, there; do not restate it and do not drift from it. A demonstration sentence is read by
the same people who read the headline, so it is bound by the same words — name the person and
what they see, in language they would use.

**Before you look at a single PRD**, write one sentence: *what a named person does, end to
end, across every surface this program claims, that would be true only if the whole thread
runs.*

Concrete, in the program's own voice, naming the person and what they see. Not a PRD number,
not a component, not a mechanism. On **`kind: program`** the sentence must name a surface a
**customer** touches — that clause is the only thing standing between "platform work,
honestly named" and "stranded substrate with a roadmap bar", and it is the reason `kind:
program` requires a proof at all.

This sentence is the artifact the rest of the command grades against. Write it down in your
report even when the run ends in *no proof* — a program that cannot have this sentence
written for it has a bigger problem than an empty cell, and that is a finding worth landing
on its own.

### The sentence gate: it must say what no single slice says

Test the sentence against **every** slice's `Done when`:

- If any one slice's `Done when` would make the sentence true on its own, the sentence is
  **slice-shaped**. Rewrite it. A program's completion condition is the one its slices do
  not have; a sentence a single slice satisfies is that slice's condition wearing the
  program's name.
- If the sentence is true only when **two or more** slices have landed *and are connected*,
  it is composed. That "and are connected" is the whole content of the tier — `status:
  shipped` on every part proves each part exists and never that the whole is connected
  (PRD 0252: the composed path returned 503 across seven `shipped` upstream PRDs).

**This gate is hard and it comes before the search.** A slice-shaped sentence will happily
find a slice-shaped proof, and the pair will look completely reasonable.

### Author it into the program's `## Bar`

The sentence you just wrote and gated **is** a program bar's `**Demonstration.**`
([`tracking-and-execution.md`](#) → "The
`## Bar` contract"). Write it into `knowledge/programs/PG-NN.md` **now**, before Step 4 opens
a single PRD — the same guard the sentence gate is, made physical.

The section opens with two lines, and Step 3's table goes under them:

    ## Bar

    **Scope.** …what the criteria below are measured against…

    **Demonstration.** …the Step 2 sentence, verbatim…

**The `**Scope.**` line says what the criteria are measured against — and, the load-bearing
half, what a reader may *not* substitute when they go and look.**
A good one reads like *"the whole installed product, carried forward over time — never
against any single part of it on its own"*. Without that
`never` clause every criterion below it can be satisfied by looking at something smaller than
the thing claimed. It is not a restatement of the demonstration.

**Top-level `## Bar`, never nested.** Not inside `## Decomposition record`, not inside
`## Program-specific work`. Markdown does not nest headings, and both of those sections are
parsed as *everything up to the next `##`* —
`make validate-knowledge`
for the decomposition record,
`python3 knowledge/scripts/gen_program_plan.py` for the
program-specific work. A `## Bar` written under either does not sit inside it, it **ends** it,
and everything below the heading silently stops being read: the capability rows stop being
derived roots, and the program-specific work vanishes from the generated plan.

**A program's bar carries no digest, and that is said out loud so nobody adds a decorative
one.** A slice's bar decomposes a `Done when` cell living in a *different* file, so it binds
to that cell's exact authored bytes with a `done-cell-digest` and breaks the moment the
promise is edited. A program has no such cell — the demonstration is authored **inside the
section it guards** — so a digest over it breaks on nothing while reading to the next author
like a check that is running. Do not add one.

If the program has no detail file yet, create it with the frontmatter type `slot:file-conventions` gives a program detail file, and
no other key; it is the same file Step 7 appends the run's finding to.

## Step 3: Decompose the demonstration into criteria

A demonstration is one sentence, and **nobody can go and look at a sentence.** The criteria
are the places a doubter would actually look, written so that looking can come back *no*.
Under the `**Demonstration.**` you just authored:

```
| # | Criterion — states its own RED | Probe |
|---|---|---|
```

**Ids** are the entity id with its dash removed, then `-P<n>`, sequential from 1
(`slot:planning-model` records the form). They are scoped to the entity and
globally unique; a slice's are `-C<n>`, so an id read on its own says which tier committed it. Never reuse a
number and never renumber a row somebody has already looked at.

**A criterion states its own RED in the same sentence it makes its claim.** A row that says
what good looks like and not what would falsify it is a hope, not a criterion — the reader who
doubts it has nowhere to go. Write the RED as a condition somebody can observe, and enumerate
it where the failure has several distinct shapes: `PG24-P2` names three separate ways it goes
red, and the last of them (*"the host they prepared against the published requirements turns
out not to be the host it runs on"*) is precisely the one that would otherwise have been
argued away on the day.

**One criterion per thing a reader would have to go and look at.** Two rows that are always
red together, or always green together, are one row wearing two hats. Three to seven is the
range on the bars that exist; a program bar with a dozen rows has become a checklist of its
slices, which the next gate is about to refuse.

**Under the table, argue the tier.** For each criterion name the slices it spans and what none
of them says alone, and it is what the next
reader checks the tier gate against without re-deriving it.

### The tier gate: it must be a criterion no single slice can turn green

**A criterion belongs to the lowest tier that can turn it green alone.** Take each row and
ask: is there one slice whose `Done when`, closing on its own with nothing else moving, makes
this criterion green? If there is, **it is that slice's criterion and it comes off the
program's bar** — not "also on the program's". Off it.

**This is R1 one level down.** A program may not borrow a slice's `Verified by`, because a
shared proof collapses the program's completion condition into the slice's and the program can
never say anything the slice did not already say . A borrowed *criterion* does
the same thing to the bar: it goes green the day the slice's own work lands, and the composed
claim it was supposed to hold open is gone. **A program's criteria are the composed ones.**

**The gate is hard, and dropping a row is not losing it.** Report which criteria you dropped
and which slice each belongs to. **Do not write it into the slice's file from here** — this
command's writes are the program's cell and the program's detail file, and a slice's bar is
authored where that slice's `Done when` is owned.

### `No probe yet.` is a legitimate probe cell, and often the right one

The `Probe` is the observation that could refute the criterion — **something run against a
running system**. Never a test file's name, and never a PRD number: a PRD number is the
shipped-artifact fact the bar exists to get past.

**When no such observation exists, write `No probe yet.` and stop there. Inventing an
executable probe that has never been run is worse than recording honestly that none exists.**
A fabricated probe reads to the next agent as an observation that *was made*: the criterion
looks measured, so nobody goes and measures it, and the row now certifies the opposite of what
is true. **A bar whose probes are all fabricated is worthless** — it has replaced *"we have
never looked"* with *"we looked and it was fine"*, which is the one substitution the whole
contract exists to stop. 

**An honest empty probe still does work.** Name what the observation would have to be, and why
nothing performs it today. The second half is what tells the next agent the gap is structural rather than a missing
script. `No probe yet.` alone is acceptable; `No probe yet.` plus the shape of the missing
observation is what a later run can pick up.

**Where a probe is real, write it so somebody who was not here can re-run it** — the endpoint
or command, the context it must be pinned to, the assertion, and the trap that ate the last
person.

### The bar is the human's act

**Authoring a bar is committing to a promise, and commitments are the human's** — the same act
as writing a slice's `Done when` or a program's claim
([`tracking-and-execution.md`](#) → "Scope
discipline"). The reason is mechanical rather than ceremonial: **a bar an agent can widen can
never be red.** An agent free to loosen a criterion, delete one, or soften a RED until the
observation clears it is not holding a bar, it is holding a mirror.

So the whole section — the `**Scope.**`, the `**Demonstration.**` and every row — goes to the
human before it lands. Brief first in plain English (what this program claims, what you would
go and look at, what you could not find a probe for), then `AskUserQuestion` — shaped by the
interview card. Act on the answer in the same run.

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

**Repairing an existing bar has a direction.** Adding a criterion, or tightening a RED so it
catches more, can only ever *withhold* a reading — propose either as part of the run. Deleting
a criterion, loosening one, softening a RED, or rewriting the demonstration are the human's
call and nobody else's, and you never slip one in as an aside inside another change: they are
the one direction that turns a bar green with nothing having changed in the product. **A
rewritten demonstration is not a repair, it is a new bar** — every surviving criterion is
re-affirmed against the sentence as it now reads, or it comes off.

**Headless, this command authors no bar.** It already interviews nobody and writes no cell
when no human is attached; a bar is the same class of thing and gets the same answer. Report
the demonstration and the proposed table in full — that is the run's product, and it pastes in
— and write nothing. Absence of a refusal is not permission to author a bar, exactly as it is
not permission to fill a cell.

**The bar and the proof stay independent.** A program may carry a bar and have no proof PRD;
it may name a proof and carry no bar. Authoring a bar does not make outcome (a) reachable and
does not soften outcome (c): the bar records what somebody would have to **see**, `Verified
by` records which PRD **drives** it, and neither is evidence for the other. Steps 4–6 run
exactly as they would have if this step had written nothing — a good bar never talks you into
a cell.

## Step 4: Search for candidates

Only now go looking. Dispatch a sub-agent over the PRD corpus (`knowledge/prds/`) with the
demonstration sentence as the brief, and ask it for PRDs whose **acceptance criteria** drive
that sentence — not PRDs whose titles sound like it. Have it report, for each candidate: the
number, `status:`, `slice:`, and the specific ACs that would demonstrate the sentence, plus
the surfaces those ACs actually touch.

Search widely: the proof is **not** required to be a member of one of this program's slices,
and often cannot be — a composed e2e proof frequently sits outside every cut it crosses.

**Search `knowledge/drills/` in the same pass.** A committed `type: drill-record` whose
measured clauses drive the demonstration sentence is a candidate on the same terms as a PRD —
report its stem, its `verdict:`, its `daemon_sha` and the clauses that would demonstrate the
sentence. A record with `verdict: failed` is a candidate that has not shipped, which is the
same standing as an unshipped PRD; a file that is not a record, or carries no verdict, is not
evidence and the validator refuses the cell that names it.

**Zero candidates is an expected and common result.** It is Step 6's outcome (b), not a
reason to widen the search until something matches.

## Step 5: The four refusals

A candidate is only a proof if it survives **all four**. Run them all and report each
verdict — a reader needs the whole picture, not the first failure.

**R1 — Disjointness. FATAL, and the validator enforces it.** The candidate may not appear in
the `Verified by` of **any** slice under this program. A shared proof collapses the
program's completion condition into that slice's: the composed reading goes green the moment
the slice's own does, and the program can never say anything the slice did not already say. **The program side changes, never the slice's** — the slice keeps
its local proof; you go and find a composed one, or you write nothing.

**R2 — It is not this program's own walking skeleton.** If the program's file designates the
candidate as the first thin vertical thread, it cannot also be the proof that the whole
thread runs. A proof that passes R1 is still refused when it is the program's own walking skeleton. **No automated check can see this** — the disjointness test cannot, and neither
can reading the PRD. Only reading the proof against the program's own claim can, which is
why Step 1.4 makes you write the skeleton down before you have a candidate to be tempted by.

**R3 — It is not slice-shaped.** Grade the candidate's ACs against the Step 2 sentence and
against every slice's `Done when`. A proof that walks one lane well is a **third slice**,
not the thread across them. *"A legal proof can still be slice-shaped, and should then be
refused"* — R1 and R2 passing is necessary and nowhere near sufficient.

**R4 — It drives the composed path across every surface the program claims.** Browser, API,
MCP, channels, as applicable. A component test wearing an e2e title fails here, and so does
a proof that drives three of the four surfaces the program's claim names. On `kind: program`,
at least one of those surfaces is one a customer touches.

> **A note on `status:`.** The candidate does **not** have to be shipped for you to name it —
> naming a proof that has not run yet is the normal, correct state, and it is what the
> walking-skeleton rule asks for (author the proof first, run its thin slice early). The
> derivation reads the proof's own `status:` and holds the program short of `complete` until
> it ships, which is exactly right. **Do not prefer a shipped candidate over a better
> unshipped one** — that preference *is* the reasoning-backwards failure, arriving through
> the side door.

## Step 6: The three honest outcomes

There are three, and there is no fourth.

**(a) Name it.** A real PRD — or a real drill record — survived all four refusals. Write the
cell (Step 7). Report which refusals it survived and *how* — particularly R3 and R4, which
are judgements and must be argued, not asserted.

**(b) Cut it.** Nothing survived, but the demonstration sentence is writable and real. **The
outcome is a new proof PRD, not a cell.** Hand the sentence to
[`/fleet:prd:create`](#) as the ask — it is already written in the form a PRD
needs — and offer to run it **in this session**, so the run ends with the loop closed rather
than with a to-do. `decompose` Phase 7.4 authors the proof PRD in-session for exactly this
reason; the difference here is only that you arrive after the decomposition, not during it.

**The cell is written from the number, and only once the number exists.** If the PRD is
authored now, write the cell in the same PR (it will be unshipped, which is correct — the
derivation holds the program short of `complete` until it ships). If it is not authored now,
**`Verified by` stays `—`**: a cell naming a PRD that has not been written is a placeholder
with a plausible shape, and it is indistinguishable from a real one to everything downstream.
**Declined or headless, the ask is filed, not dropped** — call `file_issue` with
`kind: "task"`, `command: "program:prove"`, body carrying the sentence and a
`Program: <id>` line; it lands in **`triage`** (Triage Queue). The run moves nothing —
the next agent holds the loop instead of this session's report. **No Fleet tools? Stop.**
When the session has no Fleet tools, stop with: *this command needs the Fleet tools; create a personal key on Fleet's API keys page*. There is no other filing path — never fall back to a tracker script.

**And what this outcome leaves behind is what keeps the program from dead-ending, because
`deliver` will refuse it until the number is in the cell.** A program with an empty cell is
not driven — the board withholds the driver and `program:deliver` §1a refuses on its first
step — so an outcome (b) that ended with a sentence in a report and nothing on disk would
leave a program nobody can drive and nobody is told how to unblock. Two things make the
next step findable, and both are already this outcome's product: the **`## Bar`** landed in
the program's detail file (Steps 2–3 — the `**Demonstration.**` line *is* the ask, verbatim),
and the **filed task** carrying the sentence under the program's label. `deliver` reads
exactly those to tell *prove has never run* from *prove has spoken and the PRD is owed*, and
its refusal then names the PRD to author rather than sending the person back here. So land
the bar even when the cell stays empty (it is a commitment on its own, and the guard above
already put it on disk before the search), and file the task in the same session — a bar
with no task is an ask nothing dispatches, and a task with no bar is a sentence the next
reader cannot find in git.

**(c) Leave it unproven, and say why.** The demonstration sentence could not be written, or
it could be written but nothing about this program is demonstrable yet: its slices have not
landed a composed path at all, or the row is really a **theme** (nothing becomes true on a
day), or it is a `kind: program` whose customer surface was never in scope. **The cell stays
empty — and the run files its follow-ups, or it has dead-ended.** A finding whose only home
is a git prose file has no dispatch edge: no state dispatches on a paragraph, no queue holds
the fork, so the next agent never learns the run happened. So outcome (c) ends with two mandatory
filings through `file_issue` with `kind: "task"`, `command: "program:prove"`, and a
  `Program:` body line (born `triage` / Triage Queue; Fleet attaches the dedupe record):

  > ⚠️ **A filer files into the gate and stops; it never moves its own issue out.** The
  > fork issue is a fresh task with **no priority** — priority is the checker's
  > output, not a guess this run makes — and `Blocked · decision` is a position the
  > partition guardrail refuses a work issue in without one. That guardrail is *blocking*
  > inside `ci-success`, so one self-park here reds **every open PR in the repository**
  > until a human moves the issue back by hand. File the fork into `triage` and
  > stop; [`/fleet:check`](../../check.md) is the gate a filer hands to, and its
  > ESCALATE verdict is what sets the priority and applies the `Blocked · decision` park.



- **Bounded repairs the run discovered** — one small `file_issue(kind: "task")` each,
  forensic + fix in the body, with `Program:` (and slice name in prose if known). These are
  not scope calls; filing them is the same release `/fleet:check` performs on uncovered ground.
- **The human fork, when the run hits one** — *build a descoped capability vs narrow the
  claim*, or any decision that gates whether a proof can exist at all: filed into the gate,
  per [`triage-partition.md`](../../../registers/triage-partition.md) →
  "Self-park — needs an ANSWER" (born in `Triage Queue` and **left there** — see the
  guardrail note below; the `Blocked · decision` park is the checker's write, not this
  run's). The issue description states facts the run verified, never an inference; the
  options are argued there, and the human's answer lands there.

A row that is really a **theme** has no follow-ups to file — the finding alone is the
product, appended to the program's detail file (Step 7) as the durable record. The filings
are the dispatch edges, not a substitute for it. The board's *can never complete* node and its
*"No proof named"* row both stay — they are *the finding surfacing correctly*, and clearing
them is never a goal.

**Put the fork to the human.** Which outcome, and — where two candidates both survive, or the
demonstration sentence has a real alternative reading — which sentence. Shaped by the
interview card (Step 5): brief first in plain English (what this program claims, one
concrete example, what is genuinely undecided), then `AskUserQuestion`. Then act on the
answer in the same run.

**Headless, this command interviews nobody and writes no cell — and it still files.** It is
not fleet-dispatched; if no human is attached, report the demonstration sentence, the
candidates and their four verdicts, file outcome (b)'s ask or outcome (c)'s repairs and fork
exactly as written above — the filed fork *is* a headless run's interview, asked through the
check gate instead of the terminal (the checker's ESCALATE verdict applies the
`Blocked · decision` park once a priority exists) — and stop. Absence of a refusal is not
permission to fill a cell.

## Step 7: Write, repoint or clear the one cell

**One column, in one row fragment: `Verified by` in `knowledge/programs/rows/PG-NN.json`.** This command
touches no other register column — not `Requires` (that is `decompose`'s output and rewriting
it here would silently redraw the decomposition), not `Name`, not `Kind`, and no column that
does not exist. Its only other write is the program's own detail file: the `## Bar` from
Steps 2–3, and the run's finding below.

Three writes are possible:

- **Empty → a PRD number, or `drill:<stem>`** (outcome (a)). Comma-separated if the composed
  thread genuinely takes more than one proof; the two kinds may be mixed.
- **A wrong PRD → the right one** (repair). Same authority `program:ship` has on a gate-4
  failure, applied before closing rather than at it. Repointing moves the computed reading
  *off* `complete` until the new proof ships — that is the mechanism working, not a
  regression to explain away.
- **A wrong PRD → `—`** (repair, when no adequate proof exists). A cell that names an
  inadequate proof is worse than an empty one: the derivation is reading it as proof *right
  now*. Clearing it is the correction, and `unproven` is the honest reading it restores.

**Never in the other direction:** never fill a cell to clear a flag, never borrow a slice's
proof, never write a number for a PRD that does not exist, and never invent a column to hold
a verdict. One was tried — `Proof accepted`, deleted after being set on 0 of 13
programs — and the register's exact-header check will fail the commit if anyone re-adds it,
which is the intended answer.

**No status, no date.** Neither column exists on either register and neither may be added.

**And the bar carries no verdict.** A bar is a *commitment* and belongs in git; a verdict is an
observation of a running system at an instant — true of one deployment at one moment and false
an hour later with no file changed. Never write green/red, a date, a "last measured" line or a
probe's output into the section. That is the defect this planning model deleted: measured **33 of 40 stored mid-tier statuses were wrong**, because a value somebody has to
return to and reconcile is a value nobody returns to.

If the run produced a finding worth keeping — the argument for why this proof is the
composed one, or why none exists — append it to the program's detail file
(the program's detail file, where `slot:programs` says one lives; create it with the typed header `slot:file-conventions` gives it and no other
frontmatter key). Prose there, structure in the register, never both.

## Step 8: Validate, then land

1. `make validate-knowledge` — **clean, or the edit is not landed.** R1
   is enforced there and fails the commit on a borrowed proof; when it fires, the fix is
   **always** on the program side, and the move is to revert the cell and re-decide — never
   to edit around the finding. **The `bars` check validates the bar's shape, and nothing
   validates its judgement.** That check reads `## Bar` at both tiers and fails on a
   malformed table, a criterion id that is not `PG-NN`-derived or not sequential, a missing
   `**Scope.**`, a missing `**Demonstration.**` on a program, or a digest on one — run it
   with `python3 knowledge/scripts/fleet.py check --only bars --repo .`. But the rest of `make validate-knowledge`
   says nothing about the section, and **no check anywhere can see the two rules that
   decide whether the bar is worth having**: the tier gate (could one slice close this row
   alone?) and the probe rule (was this observation ever actually made?). A green `bars` run
   means the bar is well formed, never that it is honest. Re-read it against Step 3 before you
   commit it.
2. Branch, commit, PR, auto-merge on green — per
   [`tracking-and-execution.md`](#) →
   "Git workflow". Doc-only still goes through a PR; the fleet identity has no
   direct-to-`main` path. Watch it to `state: MERGED` (`python3 knowledge/scripts/gh_pr_merge_state.py <pr> --watch` — `queued` is pending, and `ejected`, removed from the merge queue while its own checks read green, is red CI) — a conflicted PR shows **zero**
   checks, not failing ones. The cell and the bar ride the **same** PR: one run's product,
   even though neither depends on the other.

**Do not write the program's state into the tracker.** A program is a label; the `prd-projection` pass of the
fleet's `corpus-sync` loop reconciles it once the merge lands on `main`, and nothing here reads tracker state back — the register cell and the
program label stay untouched. **Filing the Step-6 follow-ups is the exception, and it is
mandatory**: a task or a decision park is not program state, it is the dispatch edge that
keeps outcomes (b) and (c) from dead-ending.

## Step 9: Report

The program, the **demonstration sentence** (always — it is the run's real product), the
candidates considered with their four verdicts, the outcome (a/b/c), what was written or
deliberately not written, the PR URL, and **the tracker keys the run filed** (or `none —
nothing to file`, with the reason). If the outcome was (b), name the PRD that needs
cutting and the sentence it would be cut against. If the outcome was (c), name what would
have to become true for this program to be provable at all.

Report the **bar** beside it: whether it landed or was left as a proposal and why, the
`**Scope.**` line, every criterion with its id and its probe, which criteria you **dropped as
slice-tier** and to which slice each went, and the count of real probes against `No probe yet.`
cells. A bar that is three-quarters empty is a true report of where we are; dressing it up as
anything else is the one failure that makes a bar worse than none.

---

## Rules

- **Never manufacture a proof.** No placeholder, no plausible-looking number, no proof
  chosen because it is the best of a bad set. An empty cell reads `unproven`, which is true;
  a borrowed one is a lie the derivation believes.
- **The cell is the precondition of driving, and this command is its only writer.**
  `program:deliver` refuses a program whose cell is empty (its §1a) and the board offers this
  command alone on such a program — so an outcome that leaves the cell empty must leave its
  trace where the driver reads it: the `## Bar` in the detail file and the filed task or
  parked fork. That is what turns *refused* into *here is the next step* instead of *run
  prove again*.
- **The demonstration sentence is written before the search, every time.** The order is the
  only structural defence against choosing the proof to fit what already shipped, and that
  reasoning-backwards failure is the reason `program:ship` refuses to author this cell at all.
- **Never borrow a slice's proof.** Fatal, validator-enforced. **The program side
  changes, never the slice's.**
- **A legal proof can still be wrong.** R1 and R2 are machine-checkable and machine-invisible
  respectively; R3 and R4 are judgements and are the ones that matter. Passing R1 is not a
  verdict.
- **Never write a status on a program or a slice**, here or anywhere — there is no column and
  none may be added. Completion is computed from the slices and the proof. `Proof accepted`
  was the cell a verdict used to want; it was deleted unused and the header check refuses it.
  **`Disposition` is not that column and this command never touches it**: it records a
  decision (`adopted` · `withdrawn: <record>` · `superseded by <id>`), never a ship-state, and
  the validator refuses `delivered`/`closed`/`done` in it by name.
- **No dates.** There is no date column anywhere on the planning ladder.
- **One cell, one file.** `Verified by` in the program row fragment and nothing else **in the
  planning registers** — the Step-6 filings live in the tracker and touch no register row.
  `Requires`
  belongs to `decompose`; the slice register belongs to `slice:create` and
  [`slice:edit`](#).
- **Never re-run `decompose` to fill a cell.** It rewrites the decomposition, and on a program
  whose slices are finished it derives gaps that no longer exist.
- **Human-invoked only.** Not dispatched by the tracker daemon; headless it writes no cell —
  and still files the Step-6 follow-ups, because a finding with no dispatch edge is a dead
  end.
- **The bar is the human's act — you propose it and you never widen it.** Adding a criterion
  or tightening a RED can only withhold a reading; deleting one, loosening one, softening a
  RED or rewriting the demonstration is the human's call, never an aside inside another
  change. **A bar an agent can widen can never be red.** Headless: propose it in the report
  and write nothing.
- **`No probe yet.` beats an invented probe, every time.** A fabricated probe certifies an
  observation nobody made and stops anybody making it.
- **A criterion one slice can turn green alone is not the program's.** R1 one level down: a borrowed criterion collapses the bar into that slice's exactly as a borrowed
  proof collapses completion. Drop it, report it, and do not write it into the slice's file
  from here.
- **A program's bar carries no digest, and `## Bar` is top-level.** There is nothing to bind
  across files — the demonstration is authored inside the section. Nested under
  `## Decomposition record` or `## Program-specific work` it does not nest, it **ends** the
  section, and every row below stops being parsed.
- **The bar and the cell are independent.** A program may carry a bar and no proof, or a proof
  and no bar. Neither is evidence for the other, and a good bar never talks you into outcome
  (a).
- **A drill record is a proof on the same terms as a PRD, and no looser.** All four refusals
  apply to it unchanged; a failed verdict is an unshipped proof, not a reason to clear the
  cell; and a waiver in `` is outcome (c) written down
  with its reason and its kind on the id line — `PG-NN excused` when no composed proof is
  needed, `PG-NN deferred: <what is owed>` when it is still owed (no default; the gate refuses a
  bare id) — never a substitute for a record that exists.
- **An excused slice waiver does not hold the program; a deferred one does, and so does a program
  waiver.** A cut whose `proof_waiver` is `excused` (no member live, no proof of its own)
  is settled by that decision: once the proof this command names ships, the program reads
  `complete` over it and `program:ship` may close it, naming the waived cut. So never name a proof
  merely to "unblock" an excused cut, and never ask for one to be un-waived to let the program close.
  A cut whose waiver is `deferred` still owes its proof: it holds the program open,
  "waiting on SL-NNN's proof: <owed>", until `slice:edit` names that proof — never borrow this
  program's proof for it. A program in `` has no
  proof to ship: an `excused` line parks it, a `deferred` one says what this command still owes it.
- **One source of truth:** the PRDs' frontmatter `status:`. Never read tracker state back.
