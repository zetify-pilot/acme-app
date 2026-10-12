#  Slice — Refine (a cut from a brief becomes a real one, on the fleet)

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
  Step 6's report; anything else (`shape`, or no `step` — a block written before the field) →
  Steps 1–6 as written, the interview.
- **Unset** → a person is at a terminal, and this is the wrong verb for them. Say exactly
  this and stop, writing nothing: **This command runs only on the fleet. At a terminal, run
  `/fleet:slice:create SL-NNN` instead** — it is this same interview with you in the room,
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
program's row in `slot:programs` with its `Verified by` and `Disposition` — and derive the
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

### Step 2: The refusals

By sentinel, before any question, in the form *The headless contract* §9 gives:

- **No row resolves** for the id → `failed`, a mis-dispatch. Cutting a slice is
  `/fleet:slice:create`; this command never creates a row.
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

### Step 2b: Stub mode — a refined cut with no PRD (no rounds)

**Only when the block says `step: stub`.** The fleet asked for this because a driven program
holds a cut that was refined and has no CAPABILITY PRD — none at all, or only the program's composed
proof — and the next steps of the pipeline —
`prd:fill`, then `prd:blueprint` and `prd:plan` — need a stub to start from. **You ask no
question, run no round, and write no cell of the slice, no register row and no bar.** The
commitment was made when the cut was refined and the program started: this run decomposes what
the cut already promised into its first PRD and adds **no customer-facing functionality**
(CLAUDE.md: an agent may build what the product already promised, and may never promise
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
   `Program`, `Name` and `Disposition` untouched. **Never write a status on a slice** —
   completion is computed, and no column holds one; never a date either.
2. **The register rows** — `create.md` Step 3 item 6: every accepted promise appended as
   `Disposition: open` with its id from the register's counter, bumped in the same change;
   `Source` citing the detail file by quoted phrase, never a line number; `Needs` edges
   written with the rows. Every exclusion the person named as a row of its own,
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

Then `make validate-knowledge` clean, and — whenever the detail file or the `Done when` cell
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
