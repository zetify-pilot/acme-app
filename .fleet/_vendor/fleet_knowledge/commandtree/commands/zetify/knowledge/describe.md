# Knowledge Describe — describe ONE part of a repository, on the fleet, by one merged PR

You describe **one part** — one component of the repository's component registry — into the
knowledge corpus: read **every file it owns**, draft what it does and what it promises, confirm
the promises with a person through the fleet's written question channel, and land the
capabilities, rules, area and journeys as **knowledge-only files** on one pull request that you
arm to merge and watch to `MERGED`. That is what [`knowledge:bootstrap`](bootstrap.md) Phases 2–4
produce for one component with a person in the room, and **this command is that step, run
headless** for the button on the Knowledge page: the same drafting rules, the same promise test,
the same shapes — asked by writing, answered on the page or in the Cockpit, landed as one merged PR.

**Before you write a knowledge file, read its docs page** (under `.fleet/docs/`; `read_doc <page>` when Fleet's tools are in the session): `knowledge-base/the-folder`, `knowledge-base/journeys`, `knowledge-base/feature-areas`, `knowledge-base/promises`, `knowledge-base/capabilities-and-components`.

**The one idea that governs every step: the code shows what the product *does*; only a person
can say what it *promises*.** A rule you read off the code is evidence, not a commitment. You
draft from the code and the person confirms, in batches — never one row at a time, and never by
your own recommendation standing in for their answer.

**You are a composition, not an authority.** Every rule about how to read a component, what a
capability and a rule are, how to word a promise, and the shapes the files take lives in
[`bootstrap.md`](bootstrap.md) (Phases 0–4) and in
[`knowledge-bootstrap-formats.md`](../../../process/knowledge-bootstrap-formats.md); this file
cites them rather than restating them. What this file owns is the **mapping**: which of the
attended steps become which of five steps here, the **deterministic full reading** that makes
"the whole part was read" a measured fact, the two rounds of questions, and the landing.

**Headless only.** A person at a terminal runs `knowledge:bootstrap start <part>`, which keeps
the progress file and the pace of a conversation; the fleet routes a mission by command string
and cannot tell that verb on a part from this one, so this one exists for the button and nothing
else (Step 0).

The part to describe: $ARGUMENTS

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps`
> block below and create **one todo per step**, in order; mark each `in_progress` on entry and
> `completed` on exit. The five steps after the mode check are the five the Knowledge page draws
> as its stepper — survey, read files, draft, check with you, write and open PR — and the run
> reports which one it is on (*The progress*, below). The review step is a bounded loop — add one
> todo per round under it. This command authors knowledge files only and **writes no `status:`
> on anything**: a part is described or it is not, and that is read off the merged corpus.
>
> **`needs: answers` · `may merge: true`** ([`spine.md`](../../../process/spine.md)) — this
> command is dispatched headless and asks **by writing**, which is why `needs: answers` still
> dispatches. It is the **headless path that lands one PR and arms auto-merge** (it merges only
> its own knowledge-only PR, the way [`prd:fill`](../prd/fill.md) merges a stub it filled); the
> attended [`knowledge:bootstrap`](bootstrap.md) stays `may merge: false`, because a person is in
> the room and a person lands what it writes. **`AskUserQuestion` is not available to you and
> never will be.** Your escalation path is a `questions` result file plus the end of your turn,
> and the answers come back by resumption of this same session — the shared contract inlined
> under *The headless contract* below.

```json
{
  "command": "knowledge-describe",
  "tier": "core",
  "sop": "none",
  "needs": "answers",
  "may merge": true,
  "intent": "Describe ONE part of a repository on the fleet: survey it, read every file it owns through the deterministic batches, draft its capabilities and rules, confirm the promises with a person through the written question channel over at most two rounds, then land knowledge-only files by one merged PR and one landed result.",
  "loads": ["process-shaping-headless", "process-interview"],
  "requires": [
    "process-spine", "process-interview", "process-shaping-headless", "process-knowledge-bootstrap",
    "git-workflow"
  ],
  "optional": ["languages", "gate", "codegen", "dev-environment", "product-vision", "components", "feature-areas", "feature-maps", "journeys", "commitments"],
  "steps": [
    {"id": "mode",     "name": "Which way in — the fleet, or a terminal (refused)",                    "kind": "decision", "actor": "coordinator", "body": "step-0-which-way-in"},
    {"id": "survey",   "name": "1 · Survey — the base, the part, its files, the existing corpus",      "kind": "io",       "actor": "coordinator", "body": "step-1-survey"},
    {"id": "read",     "name": "2 · Read files — every file the part owns, one sub-agent per batch",   "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "step-2-read-files"},
    {"id": "draft",    "name": "3 · Draft — capabilities, rules, suspicions, the area and journeys",   "kind": "author",   "actor": "coordinator", "body": "step-3-draft"},
    {"id": "review",   "name": "4 · Check with you — the promises, in at most two rounds",            "kind": "loop",     "actor": "coordinator", "loop": {"max_rounds": 2, "exit": "the person answered the promise review (or nothing needed a person), or the ceiling was reached and what stands is written with its open items"}, "body": "step-4-check-with-you"},
    {"id": "land",     "name": "5 · Write and open PR — the corpus files, the branch, the merge",      "kind": "author",   "actor": "coordinator", "gate": "hard", "produces": ["feature-map", "requirement-register", "journey"], "body": "step-5-write-and-open-pr"},
    {"id": "report",   "name": "Report",                                                               "kind": "author",   "actor": "coordinator", "body": "step-6-report"}
  ]
}
```

---

## What to do

### Step 0: Which way in

```bash
printf '%s\n' "${FLEET_RESULT_FILE:-<unset>}"
```

- **Set** → the fleet dispatched you on a part the Knowledge page asked to have described.
  `$ARGUMENTS` is the component's id, exactly as the registry spells it; the mission's
  `## Shaping` block carries the requester and — on a continued run — `continued`, `filesRead`,
  `filesTotal`, `unread` and `unreadComplete`; the payload says which round this is — *The headless contract* §1. Run Steps 1–6.
- **Unset** → a person is at a terminal, and this is the wrong verb for them. Say exactly this
  and stop, writing nothing: **This command runs only on the fleet. At a terminal, run
  `/zetify:knowledge:bootstrap start <part>` instead** — it is the same description with you in
  the room, over the same registry.
  **And say that the terminal is not a one-way door.** A person who starts by hand and would
  rather the fleet finished it presses **Describe** on the part's row on the Knowledge page, and
  the run picks up from the knowledge already merged. Being sent to a terminal must never read as
  being sent there *for good*.
- **Set, but `$ARGUMENTS` is not a component id the registry holds, or the block's `kind` is not
  `part`** → a mis-dispatch. Write nothing; sentinel `failed` naming what was wrong; stop.

### Step 1: Survey

The base, the part, the ground. Everything the repository can answer is answered here, before
any question.

1. **The base.** Run `python3 knowledge/scripts/kb_base.py` first and obey its exit code, as
   [`bootstrap.md`](bootstrap.md) *Before Step 0* says: exit `3` → refuse with `needs-decision`
   and the sentence it prints (*merge the `fleet init` pull request first*), writing nothing;
   exit `4` → rebase onto the ref it prints before writing anything; any other non-zero exit →
   `failed` with its message. The next part's run starts from a **fresh base** — the previous
   part's pull request has merged — and this check is what proves it.
2. **The full-reading tools.** The deterministic reading below needs
   `python3 knowledge/scripts/kb_inventory.py` with its `batches`, `record` and `coverage`
   subcommands:

   ```bash
   python3 knowledge/scripts/kb_inventory.py --help | grep -q 'batches' || echo MISSING
   ```

   If it prints `MISSING`, stop plainly — **full-reading tools missing** — as a refusal (*The
   headless contract* §9, sentinel `failed`) and write nothing. **Never fall back to reading the
   part partially**: a description written from a part of a component is the one outcome this
   command exists to make impossible.
3. **The part.** Find `$ARGUMENTS` in the component registry (`slot:components`): its owned
   paths, its routes by prefix, its layer, `depends_on`. A component the registry does not hold
   is a mis-dispatch (Step 0). Run `python3 knowledge/scripts/kb_inventory.py scan` so the
   inventory is current.
4. **What the corpus already says.** Read every existing capability row, requirement row and
   journey criterion that touches this component, and the product vision
   (`slot:product-vision`). Draft nothing yet; this is evidence for the *Against the existing
   corpus* section ([`bootstrap.md`](bootstrap.md) Phase 2a item 7).
5. **The files.** `python3 knowledge/scripts/kb_inventory.py batches <component>` writes
   `batches/<component>.json` — every file the part owns minus only mocks, fixtures, testdata,
   generated and vendored files (**tests stay in**), split into sub-agent-sized batches
   `{component, files, batches: [{id, files, bytes}]}`. This is the denominator the next step
   reads against; do not build another list.

6. **A continued run.** When the `## Shaping` block says `continued: true`, an earlier run (a
   time limit, a Stop, a failure) left a ledger, and **this run reads only what that run did
   not**. It is a new run from a cold start, never a session continuation, so this checkout's
   ledger is empty; seed it from the brief, through the same tools, before Step 2:

   ```bash
   printf '%s\n' <the brief's unread paths> | python3 knowledge/scripts/kb_inventory.py carry <component> --total <filesTotal> --read <filesRead>
   ```

   `carry` records every planned file that is **not** in `unread` as read, batch by batch, and
   the coverage gate stays the one judge. It exits `3` with `REFUSED` and records **nothing**
   when the part is no longer the part the earlier run measured (the file count moved) or the
   unread list does not account for the files that were read (`unreadComplete` is `false`: it was
   cut short). Then read the whole part again as a first run does; never record a path to make a
   gate pass. When `unread` is empty the earlier run had read everything: the gate passes
   at once and the run goes on to Step 3. Do not re-read a file the ledger holds.

Report step 1 done (*The progress*).

### Step 2: Read files

**Every file the part owns is read, and the reading is measured, not claimed.** This step is
the gate between the survey and everything that writes.

1. **One sub-agent per batch.** For each batch in `batches/<component>.json`, dispatch one
   sub-agent with its file list. Each reads **every file in its batch** — handlers, tests,
   schema, UI — and returns its findings (capabilities, rules with evidence, suspicions, how the
   files relate) and **the exact list of files it read**. [`bootstrap.md`](bootstrap.md) Phase 2a
   items 1–5 say what to look for; hand each sub-agent that list. A sub-agent that did not read a
   file does not return it.
2. **The coordinator records exactly what was read.** For each batch, pipe the files the
   sub-agent actually returned to the ledger:

   ```bash
   printf '%s\n' <the files the sub-agent returned> | python3 knowledge/scripts/kb_inventory.py record <component> <batch-id>
   ```

   `record` exits `2` and prints `REJECTED` for a path outside the part's batches — never
   record a path to make a gate pass; a rejected path is a finding about the sub-agent's report,
   so re-run that batch.
3. **The coverage gate.**

   ```bash
   python3 knowledge/scripts/kb_inventory.py coverage --component <component> --gate
   ```

   It prints JSON `gate: {component, passed, planned, files, unread_files, unread_count,
   open_batches, message}` and **exits `1` while any file is unread**. While it exits `1`, **Step
   5 is refused**: you do not write the description and you do not open the pull request. Read
   the open batches and run the gate again.
4. **When you cannot finish reading in this run** — the run's time limit is near, or a Stop
   arrives — do **not** write up what you have read. Report the progress (*The progress*) with
   the `unread_files` the gate prints, and end the run **parked at the unread files**: sentinel
   `partial` with no result file (a time limit is a park, not a failed attempt; a later run
   continues from the ledger's unread list and reads only those). If the run cannot read the
   remaining files at all, end `failed` with the summary **`N files unread`**, `N` the gate's
   `unread_count`.

Step 2 is done only when the gate exits `0`. Report it (*The progress*).

### Step 3: Draft

From the findings the sub-agents returned and nothing else, draft — to the shapes
[`bootstrap.md`](bootstrap.md) Phase 2a and the formats document give, and worded to
[*Wording a promise*](../../../process/knowledge-bootstrap-formats.md#wording-a-promise--every-capability-rule-and-criterion):

1. **Capabilities** — one row per durable thing the part can do, as a noun phrase with one plain
   sentence, its evidence and its test (Phase 2a item 2).
2. **Rules** — every *"the system shall / never …"* the code enforces, each with its evidence and
   a **Confidence** of `tested`, `enforced` or `observed` (Phase 2a item 3, with its list of
   where rules hide). Fewer, sharper rules a QA run could falsify from outside.
3. **Not described** and **Suspicious** — surfaces excused with a reason; behaviour that looks
   like a bug is a Finding, never a rule (Phase 2a items 4–5).
4. **The area and the journeys** — place the capabilities into an existing feature area first and
   propose a new one only for what fits none; propose the journeys the capabilities would walk,
   each starting from a real trigger (Phases 3 and 4). Nothing is minted at draft: ids come at
   confirmation.
5. **Against the existing corpus** — each existing row marked `agrees`, `contradicted` (with the
   code line) or `not found` (Phase 2a item 7). A contradicted row is never edited; it goes to
   the review as a proposed supersession.

Write the drafts to the run state (`kb_inventory.py layout` prints where). **They are never
committed.** Report step 3 done (*The progress*).

### Step 4: Check with you

At most **two** rounds, **at most four questions each**, every one shaped by the rail in *The
headless contract* §3 — which is the interview card applied to a written medium:

<!-- include: process/interview-card.md -->

Each round's brief opens with which round this is of up to two, says which part is being
described and how many files were read, and says what this round settles.

**What is theirs to decide, and what is yours** is [`bootstrap.md`](bootstrap.md)'s table, held
exactly: whether an observed rule is a **promise**, a bug or an accident; the part's persona and
the job it serves; the feature-area taxonomy are the person's. Which file a surface lives in,
what a test asserts and the noun phrase a capability is written in are yours — never a card.

**The aspect each card changes** (*The headless contract* §3): the table has no row for a part, so
this command names its own three — a rule card → `promises`, the area card → `area`, a journey card →
`journeys` — and the `draft` carries each as it reads after the round if every recommended option is
taken. Round 2 is marked `"confirm": true`; when it is skipped, Round 1 is the round marked, and its
`draft` carries every aspect Step 5 will write.

#### Round 1 — the promises

Ask the rules, grouped by Confidence, as at most four cards: *keep as a promise* / *an accident,
drop it* / *a bug, file it* per group, with the run's reading recommended and the `observed`
ones flagged *"likely accidental — keep only if you would call a change here a bug"*. Capabilities
the evidence makes plain are listed in the brief as *"keeping these unless you object"*, never
asked. A `Suspicious` item is its own card.

Then STOP: write the `questions` result (with the `progress` object — *The progress*), the
sentinel `needs-decision`, and end the turn.

#### Round 2 — the area and the journeys

On resume, consume Round 1 (*The headless contract* §4) and ask, once, what only a person can
settle: the feature area's taxonomy when a new one is proposed, and which proposed journeys are
real, with keep / drop per criterion. **A round with nothing left that needs a person is
skipped** — say so in one line in the landed `open` list.

**At the ceiling — two rounds asked, or an answer missing — write what stands** (Step 5) and put
every unsettled item into `landed.open` verbatim. An unanswered promise is **not minted**: it
stays in the draft, and `open` names it. A promise is never written on the strength of "the
recommended option".

### Step 5: Write and open PR

**Refused while the coverage gate exits `1`** (Step 2.3): run it again here, immediately before
writing, and stop at its message if it still fails — `failed`, summary `N files unread`.

1. **Mint only what survived.** Capabilities into `features/<area>.md` with fresh `CAP-NNNN` ids
   and `Ships in: (shipped)`; rules into `requirements/<domain>.md` as `adopted`, with `Source`
   citing the evidence and the question that confirmed them; the area's `Intent`, brief and uses;
   the journeys and their criteria — exactly as [`bootstrap.md`](bootstrap.md) Phases 2b, 3 and 4
   say, ids from `python3 knowledge/scripts/validate_id_collisions.py --allocate <PREFIX> <n>`.
   Add to the area's `source_of_truth:` the paths **that were actually read**, which now is every
   file of the part.
2. Run `python3 knowledge/scripts/validate_requirements.py` and
   `python3 knowledge/scripts/validate_journeys.py`; fix every finding about a file this step
   wrote. The unclaimed-code-path finding over the roots of parts not yet described is expected.
3. **Commit knowledge only.** The diff touches `knowledge/{features,journeys,requirements,specs}/**`
   and nothing else — the repository's `Verify Gate` passes a PR as *not lane work* only when every
   changed path is knowledge content. **Never commit the progress file, the drafts, the batches
   or the ledger**: they are the run's own state under `.claude/run/`.
4. **Land it** — *The headless contract* §6, with these differences: the prior attempt is found by
   the **branch** (`gh pr list --state all --head "agent/part-<slug>" --json
   number,state,url,mergedAt` and `git ls-remote --heads origin "agent/part-<slug>"`), the
   deterministic branch is **`agent/part-<slug>`** (`<slug>` the component id; **not**
   `agent/shape-…`), cut from the ref `kb_base.py` printed; the PR title names the part; `gh pr
   merge --auto --squash` is armed the moment the PR opens (never `--delete-branch`); and the PR
   is driven to `state: MERGED` with `python3 knowledge/scripts/gh_pr_merge_state.py <pr> --watch`
   (`queued` is pending; `ejected` from the merge queue is red CI).
5. **The landed result**, only over a merged PR, the document of *The headless contract* §7 with a
   part's fields, whole and read back to `$FLEET_RESULT_FILE`:

   ```json
   {"kind": "landed", "landed": {"kind": "part", "id": "<component id>", "href": "part:<component id>", "pr": "<the merged PR's URL>", "files": ["<every path the PR changed>"], "summary": "<one plain sentence: what the part now promises>", "changed": {"capabilities": 0, "rules": 0, "journeys": 0}, "open": ["<each unsettled item>"], "progress": {"step": 5, "totalFiles": 0, "readFiles": 0, "unread": [], "questions": 0}}}
   ```

   Then the sentinel: `success` with the PR URL. A PR that could not be brought to merge in this
   run is `partial` with the PR URL and **no `landed` file**, so the next dispatch resumes the
   branch — §8's table, and never `done`.

### Step 6: Report

Eight lines, for a human reading the transcript: the part and its owned file count; the batches
read and the gate's final line; the capabilities and rules drafted; the rounds asked and
questions spent (`n of 8 across r rounds`); what was minted and what stayed in the draft; the
suspicions filed as findings; the PR and its state; the result written and the sentinel word.

---

## The progress

The service cannot see this checkout's run state, so the run **reports** it. Every result
document you write (`questions` or `landed`) carries a top-level `progress` object, read off the
coverage gate and your own step:

```json
{"step": 2, "totalFiles": 120, "readFiles": 40, "unread": ["<up to 500 paths, in inventory order>"], "questions": 0}
```

`step` is 1–5 (survey, read files, draft, check with you, write and open PR); `unread` is the
gate's `unread_files`, capped at 500; `questions` is the number of cards in the round you just
wrote. The page draws the stepper from it and a later run continues at the unread files. The
progress file under `.claude/run/knowledge-describe/` holds the same fields for your own resume
and is never committed.

---

## The headless contract (shared)

<!-- include: process/shaping-headless.md -->

---

## Rules

- **Draft from the code; promise only on a person's word.** No requirement row, journey
  criterion or capability is minted without a review answer. A headless session parks its
  questions; it never answers them.
- **The whole part is read, and the gate says so.** The description is written only when
  `kb_inventory.py coverage --component <id> --gate` exits `0`. A run that cannot finish reading
  parks at the unread files, or ends `failed` with `N files unread`; it never writes up a partial
  read, and when the full-reading tools are missing it stops with **full-reading tools missing**.
- **One run describes exactly one part and lands exactly one PR.** The next part starts only
  after this PR merged, from a fresh base (`kb_base.py`).
- **Knowledge-only diff.** Nothing but `knowledge/{features,journeys,requirements,specs}/**` is
  committed; the progress file, the drafts, the batches and the ledger never are.
- **Cite, never restate.** The drafting rules, the promise test and the file shapes are
  [`bootstrap.md`](bootstrap.md)'s and the formats document's; this file maps them onto five
  steps and owns none of them.
- **A bug you find is a Finding, never a promise and never silently dropped.**
- **No programs, slices or PRDs, no ship-state on anything durable, no tracker write, no
  `AskUserQuestion`.** Existing code is described as `(shipped)`.
- **Headless only.** A terminal is refused in one sentence naming `knowledge:bootstrap`.
