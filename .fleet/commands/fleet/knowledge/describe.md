---
description: "Describe ONE part of a repository on the fleet: survey it, read every file it owns through the deterministic batches, draft its capabilities and rules, confirm the promises with a person through the written question channel over at most two rounds, then land knowledge-only files by one merged PR and one landed result."
---
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
  `/fleet:knowledge:bootstrap start <part>` instead** — it is the same description with you in
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
4. **No bare ids, no unexplained jargon.** `PG-NN`, `SL-NNN`, `CAP-NNNN`, `<KEY>`,
   `PRD NNNN` never appear in an option label, and anywhere else only in parentheses after
   the plain name — *the goal of getting a customer live without an engineer*. An
   internal noun gets half
   a sentence of ordinary English the first time it appears. `file:line` stays, as evidence,
   never as the only statement of the problem.
5. **The test, before you send:** would somebody who has never opened this repo pick the
   same option, for the same reason? If not, rewrite. Being asked to *"explain that again"*
   is a defect in the question, not a preference — re-ask in full, plainer, and hold that
   register for the rest of the run.

6. **A mockup, design or any visual reaches the person ONE way: the fleet's `ask` tool with the mockup attached** (`upload_link` the folder, then `attachments: {bundleId, entry}`). Their browser is on their own machine, not on the box you run on: **never** tell them to open a file path, run `python3 -m http.server` or visit `localhost` / `127.0.0.1`, and never carry a mockup question in the built-in `AskUserQuestion`, which has no attachment. The tool answers with a viewer link; put that link whole in what you say. One authority: `.fleet/process/interview.md` → *A mockup reaches a person ONE way*.

7. **The person may not be the one who knows — every question can be answered *"I can't
   answer this"*, and you must plan for that.** The question card carries that choice itself
   (*Can't answer — carry on*); you never add it as an option, and you never invent an answer
   in its place. When it comes back: **carry on with an explicit `Assumption: <what you
   assumed and why>` line, marked unconfirmed by the owner** — or, where the right party is
   the reporter, carry the question to them as an open question — **never ask it again**, and
   list every such item under an **`Unconfirmed assumptions`** heading in what you write, so
   a human can review them later. Downstream, it is an assumption to confirm, not a fact. The
   rule, once: `.fleet/process/interview.md` → *"I can't answer this"*.

8. **A card a customer will read is written in their product's words.** When the person who
   can answer is on a customer install — their own people, not our team — the card says
   `"audience": "customer"`, asks each check about their own running product with **Yes / No /
   Can't check (why)**, and names **no slash command, no program or slice id and none of Fleet's
   own nouns** ("bar", "delivery cycle", "delivery log"). A park whose action is a
   Fleet-internal step — run our command, fix our tooling, mint a token, change our
   infrastructure — belongs to the install's operator, never to the customer; when the only
   missing thing is the customer's observation in their app, ask for that observation instead.
   `validate_questions.py` and `validate_decision.py` refuse a customer-addressed card that
   breaks this rule, and Fleet refuses it again at its ask boundary.

<!-- include: process/writing.md -->
### Writing for people — five rules for every session

- **Write everything that lasts in English.** Whatever language a person writes to you in,
  your live conversation with them may follow it: your questions and your replies. Everything
  that is kept is written in English: the knowledge base, plans and decisions, commit messages,
  pull request titles and descriptions, code comments, and the issues you write. When you record
  what a person said in another language, translate it into English. Keep their exact words as
  a quote only where the wording itself matters.
- **Use plain English.** Write in the style of ASD-STE100 Simplified Technical English. Many
  readers are not native English speakers. Write so that a busy reader with B1–B2 English
  understands every sentence on the first read. This holds for everything a person reads:
  questions, replies, issues, pull requests, plans, summaries and docs. Simpler words do not mean
  vaguer content. Keep every fact, number and name that matters. The points below are Fleet's
  own use of that style.
  - *Sentences.* One idea per sentence. Keep most sentences under 15 words. If "and", "which"
    or a colon joins two ideas, split the sentence. Use active voice: "She sets a limit", not "A
    limit is set". Use the simple tenses: present, past and future. Avoid forms like "would have
    been". Use a verb, not an "-ing" form used as a noun: "Check the input", not "Do the input
    checking". If you need a hard tense, keep that sentence short.
  - *Instructions and descriptions.* An instruction is a step that a person or an agent must do.
    Write it in the imperative, with one action per sentence, at most 20 words. Put the
    condition first: "If the check fails, run the fix command." A description says what
    something is or does. Write it in at most 25 words, with one topic per paragraph. A promise
    stays at 20 words (the last rule).
  - *Words.* Use everyday words: "use", not "utilize"; "help", not "facilitate"; "start", not
    "initiate". Never write leverage, robust, seamless, delve, utilize, facilitate, streamline,
    empower, holistic, synergy or cutting-edge. Prefer a verb to a noun made from a verb: "she
    checks", not "she performs a check". Name the concrete thing: "error message", not "the
    refusal"; "script", not "the loop". Use a technical term only if the reader needs it, and
    explain it in a few plain words the first time. Use the same word for the same thing every
    time. Do not switch between "limit", "cap" and "allowance".
  - *Clarity.* Every "it", "this" and "they" must point to one thing. If in doubt, repeat the
    noun. Put the main point first, then the details. Give a concrete example instead of an
    abstract description. Cut filler: "in order to", "it is important to note that",
    "basically", "actually".
  - *Structure.* Keep paragraphs to 2–4 sentences. Use bullet lists for steps or options, not
    for an explanation that flows.
  - *One word, one meaning.* Use one approved word for one thing, in every document. Do not
    use the words on its right for that thing. Words in code, in quotes and in a customer's own
    wording stay as they are.
    - **issue** — not: ticket
    - **person** — not: user, human
    - **machine** — not: host, node
    - **pull request** — not: PR
    - **repository** — not: repo
    - **agent** — not: bot
    - **customer** — not: client
    - **sign in** — not: log in, login
    - **limit** — not: cap, allowance
    - **mockup** — not: wireframe, prototype
    - **knowledge base** — not: wiki
  - *Examples.*
    "We leverage the cache in order to facilitate faster lookups." → "The cache makes lookups
    faster."
    "A limit is enforced on a per-key basis." → "Each key has its own limit."
    "The update was performed after validation of the input, which can fail." → "The worker
    checks the input first. If the check fails, nothing is updated."
    "It was rejected." → "The check rejected the pull request."
  - *Final check.* Before you send, reread each sentence. Is it within its length limit? Does it hold
    one idea? Would a non-native reader know every word? Does it use the approved words? If not, rewrite it.
- **Never write a real customer's name.** Not the company, and not its hosts, organisations,
  repositories, people or install names. This holds for code, comments, tests,
  commit messages, pull request text and release notes. When you record where a problem was
  seen, write "a customer install". When an example or a test needs a name, use a made-up one
  such as `acme` or `example.com`.
- **Write for a reader who does not know the code.** Pull request descriptions, issue titles,
  questions, feature descriptions and requirement text are read by people who never opened this
  repository. Keep our internal names out of the sentence: no PRD or issue id (a `PRD` number,
  an issue key), no process word ("slice", "lane", "dispatch"), no file path, check name or run
  id (`tests/e2e/specs/…`, `CI / e2e - browser suite`, `run 0253bb04`). Say what the thing is in
  the product's words, and name the effect on a person, not the mechanism. An id or path a
  reader needs — to link an issue, to point at evidence — goes on its own references line or in
  a references section at the end, never in the sentence a person reads first; a linking key a
  tool requires stays as a label at the start. Before you send: would somebody who has never
  opened this repository understand it? If not, rewrite it.
- **Write a promise in one plain sentence.** A capability, a requirement rule and a journey's
  acceptance criterion are read by people who did not write the code and checked by a QA agent
  from outside it. Write each as one sentence of at most 20 words, in the product's words:
  pages, buttons, issues, keys, workers. Code names, routes, status codes, environment variables,
  setting keys and file paths go in the Evidence column, never in the sentence. Keep who, what,
  when and every exception. Write a limit someone may tune as "a time limit"; keep the number
  only when the number is the promise. Say who acts: an operator, a person, an agent, a worker.
  The same words hold for what a customer reads about a feature: its brief, each use's name and
  paragraph, and a plan's slices and pieces of work. A person's own words are reworded to this
  standard before they are proposed, never written as they came.
  The full standard, with examples, is *Wording a promise* in `process/knowledge-bootstrap-formats.md`.
<!-- /include -->

**Headless — no human attached:** you write all of the above into the escalation instead,
in the same words, so whoever reads it later can answer it as filed.

Full protocol — discovery before forks, acting on the answer, where the decision is
written: `.fleet/process/interview.md`.
<!-- /include -->

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
question and answer inlined into this session — **and, when the entity was cut from an idea,
the originating `## Brief`**: that idea's dossier and the rounds its filer answered in the
intake interview. The brief is part of what you were given, as evidence: a question it
already answers is **not asked again** — record it as settled from the intake and carry it into the
draft. **Only an answered round's text and the dossier's `problem` are the filer's words**; every
other dossier field is the intake agent's summary and is cited as "the intake summarised: …", never
quoted as the filer. (A question it only touches is still
asked, saying what it gave.) **Read what you were given; do not go looking for more of it.**
Then:

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
  cannot pick against you if only your pick was argued. An option may also carry `why` and
  `cost` as fields of their own; the page then shows `why`, `cost` and `then` in full, so write
  each as complete sentences, never trailing off.
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
- **A card that asks for approval of cuts shows the cuts.** For a program, `draft.slices`
  and `draft.gaps` are the two exceptions to "one sentence" — **arrays of objects**, which the
  page lays out as named cuts (name, what lands, an example, the gaps it closes, what it
  leaves out) and a plain list of gaps (name, exists / gap / unsatisfiable). The eight-line
  brief ceiling does not squeeze them out; the service refuses the confirming round without
  them. The field-by-field shape is `program/shape.md` Round 3, and the wording is the
  interview card's (`process/interview-card.md`).
- **A card that asks for approval of checks shows the checks.** `draft.bar` is an **array of
  strings**, one check per entry (at most eight; each a plain sentence naming its RED and probe),
  on a question whose `aspect` is `bar`. The page numbers them in the card's box; the prompt
  asks the fork in one line and does not carry the checks. An option that leaves some out names
  them in its `label` and `becomes`. A `bar` sent as one sentence still works, but the page then
  cannot show a person what they are accepting.
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
`(python3 knowledge/scripts/fleet.py check --repo . && python3 knowledge/scripts/validate_requirements.py && python3 knowledge/scripts/validate_id_collisions.py)`, commit with a message that says what the entity now promises
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
closed (*"head ref `agent/shape-…` is an agent lane branch … but no `ENG-nnnn`
resolves … unverifiable lane work"*) the moment one path is anything else: code, `.claude/**`,
`knowledge/scripts/**`, `.github/**`, the `fleet/` submodule, config, a lock file. The
exemption is read off the PR's diff, never off its body, and `NOT-A-VERIFY-LANE-PR=<code>`
neither grants it nor reaches a keyless PR (it is read only after a key has resolved). So:

- **Stay inside shaping content.** A shaping run that finds it must touch anything else
  stops and reports it in `open`; it does not carry it in the same PR.
- **Carry the entity's tracker key when it has one.** A PRD's is the issue titled `[NNNN] …`
  (read-only lookup through the tracker's GraphQL API, the credential from the environment and
  never argv, one instance of the general credentials-never-on-argv rule (the repository's always-on rules); the brief's tracker key, when it names one, wins). Put it in the **title** as a
  trailing `(ENG-nnnn)` — never the completing forms `[ENG-nnnn] …` / `fix(ENG-nnnn): …`, and
  never a closing verb in the body: a shaping PR does not complete the issue it shapes
  (`push.md` 5.6). The body then carries `Refs ENG-nnnn` and a `## Files` scope manifest: a PR
  that names a tracker key must declare its changed paths (the repository's scope-manifest
  guard). **Generate it with the script, never by hand
 ** — `python3 knowledge/scripts/pr_scope_manifest.py ensure --pr <pr>`
  splices a current manifest into the live body (`ensure --body-file <path> --out <path>` before
  `gh pr create`), one backticked bullet per `git diff --name-only origin/main...HEAD` path,
  replacing a stale section rather than duplicating it.
- **No key resolves** (a program or a slice has no tracker issue of its own, and the brief
  names none): that is fine — no key is needed and the run does **not** end `partial` for it.
  Never invent a key and never cite an unrelated issue; with no key in the title there is no
  manifest obligation either.

Both `gh pr create` and any later `gh pr edit` keep the title key and the manifest when there
is a key: a PR body rewrite that drops either re-runs the gate red — after any `gh pr edit`,
re-run `python3 knowledge/scripts/pr_scope_manifest.py ensure --pr <pr>` to restore it.

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
