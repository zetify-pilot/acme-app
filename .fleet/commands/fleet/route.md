---
description: "Classify anything the user wants built against the planning ladder and hand it to the one command that builds that kind of thing — never building it here; on the fleet, write that classification as a proposal a person accepts or sends back."
---
# Route — classify and route

You are the **single entry point for anything the user wants built**. Given "I need
a b c", you orient it against the product vision, place it in the planning model, and
route it to the right pipeline command — program, slice, PRD, component, task, bug,
idea, page improvement, or connector. You never build here; you decide **what kind of
thing it is** and hand off.

**You do NOT write code, PRDs, designs, or plans.** Route and recommend.

> For a pure question or research — , the read-only front door.
> `build` is for things the user intends to build (or park as an idea).

**Two ways in, told apart by one variable.** At a terminal, `$ARGUMENTS` is a person's
request and the ending is a printed report (Step 4). **When `$FLEET_RESULT_FILE` is set** you
are on the fleet with nobody at a terminal: `$ARGUMENTS` is the issue key naming this work,
the brief carries the **dossier** [`/fleet:intake`](intake.md) wrote, and the ending is a
**`proposal` document** (Step 6) — the same ladder walk, written down instead of printed,
which a person then accepts or sends back on the idea's page. Nothing about the headless
path re-interviews: the dossier *is* the interview, and one written question (Step 5) is
the whole of what you may still ask.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. `classify` walks the ladder; nothing here builds. Steps named `Headless:` belong to the fleet path and `recommend` to the terminal path — Step 0 decides which, and the other mode's steps are closed as *not this mode* at that moment, never silently skipped. The prose steps below are the authority; this spine indexes them.
>
> **`needs: answers` · `may merge: false`** ([`spine.md`](../../process/spine.md)) — the fleet dispatches this command on an idea, and that run asks **by writing** (Step 5), never by `AskUserQuestion`. Asking is not the same as needing a person in the room, which is why `answers` dispatches and `a decision` does not. The terminal path still interviews; `$FLEET_RESULT_FILE` is what keeps the two apart.

```json
{
  "command": "route",
  "tier": "core",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "intent": "Classify anything the user wants built against the planning ladder and hand it to the one command that builds that kind of thing \u2014 never building it here; on the fleet, write that classification as a proposal a person accepts or sends back.",
  "loads": ["process-planning-ladder", "product-vision", "entity-model"],
  "requires": ["process-spine", "process-planning-ladder", "process-feature-flow", "product-vision"],
  "optional": [
    "entity-model", "components", "programs", "planning-model", "slices", "commitments", "decisions", "process-interview",
    "feature-maps", "feature-areas", "docs"
  ],
  "steps": [
    {
      "id": "mode",
      "name": "Which way in \u2014 a terminal or the fleet \u2014 and which round",
      "kind": "decision",
      "actor": "coordinator",
      "body": "step-0-which-way-in"
    },
    {
      "id": "read-vision",
      "name": "Read the vision and the current state",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-1-read-the-vision"
    },
    {
      "id": "scan-existing",
      "name": "Scan for what already exists",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-2-scan-for-what-already-exists"
    },
    {
      "id": "classify",
      "name": "Classify against the routing ladder",
      "kind": "decision",
      "actor": "coordinator",
      "body": "step-3-classify-the-routing-ladder"
    },
    {
      "id": "recommend",
      "name": "Report and recommend the command that builds it (a person at a terminal)",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-4-report-and-recommend"
    },
    {
      "id": "ask",
      "name": "Headless: at most one written question, then stop",
      "kind": "decision",
      "actor": "coordinator",
      "body": "step-5-headless-ask-at-most-one-question"
    },
    {
      "id": "consume",
      "name": "Headless: consume the answer on resume",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-5-headless-ask-at-most-one-question"
    },
    {
      "id": "proposal",
      "name": "Headless: write the proposal",
      "kind": "author",
      "actor": "coordinator",
      "body": "step-6-headless-write-the-proposal"
    },
    {
      "id": "open-target",
      "name": "Headless: assert every existing program and slice the proposal names still takes new work",
      "kind": "gate",
      "actor": "coordinator",
      "gate": "hard",
      "body": "step-6-headless-write-the-proposal"
    },
    {
      "id": "smaller-rungs",
      "name": "Headless: assert the proposal says why it is not each smaller rung, and a program proposal carries its program tests",
      "kind": "gate",
      "actor": "coordinator",
      "gate": "hard",
      "body": "step-6-headless-write-the-proposal"
    },
    {
      "id": "places-only",
      "name": "Headless: assert the proposal places and names nothing",
      "kind": "gate",
      "actor": "coordinator",
      "gate": "hard",
      "body": "step-6-headless-write-the-proposal"
    },
    {
      "id": "emit",
      "name": "Headless: emit the result file",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-7-headless-the-result-file"
    },
    {
      "id": "sentinel",
      "name": "Headless: write the done-sentinel",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-7-headless-the-result-file"
    }
  ]
}
```

## The planning model you route into

```
Component  (durable subsystem — never ships)       → the `slot:components` registry
Capability / Outcome  (durable, ledger rows)      authored into the `slot:feature-maps` ledger for its area
Theme      (a lens across programs — a word)      prose only: NEVER a tier, a row, or a cell
Decision   (a fork we took + the branch refused)  the `slot:decisions` home · or a PRD's design.md
Requirement("the system shall / never")           a row in the `slot:commitments` register for its domain
PROGRAM    (a result someone GETS — kind: outcome  /fleet:program:create → /fleet:program:decompose
            — or a body of work that LANDS —       ...then recurring: /fleet:program:deliver
            kind: program, which MUST name a       a row fragment in the `slot:programs` register
            Verified by proof on a customer surface)
  └─ Slice (a planning cut that completes —        /fleet:slice:create
            kind: feature | capability | gap-set,   a row fragment in the `slot:slices` register
            one "Done when", no dates, a ceiling)
       └─ PRD (one agent-shift, with UX)          /fleet:prd:create → design → plan → implement → verify → push
Task / Bug / Idea  (tracker-native, no repo file)  /fleet:task:create|implement · /fleet:bug:fix · /fleet:idea:create
```

The right-hand column names slots on purpose: every one of those homes is the receiving
repository's answer (`slot:components`, `slot:feature-maps`, `slot:decisions`,
`slot:commitments`, `slot:programs`, `slot:slices`), and a repository that has not answered
one has no destination for that rung — say so rather than inventing a file.

**Only the PRD carries an authored `status:`.** A slice is complete when every member PRD is
terminal *and* its proof has shipped; a program is complete when every slice is *and* its own
proof has shipped. Both are computed on read, so **never route someone toward "setting the
status" of a program or a slice** — there is no such field, and no command writes one.

**What each entity is, and the order to test for it, is the shared planning ladder**, inlined
at Step 3 — the same text in every repository, so a repository that has not written a word about
its planning still routes by real rules. **Where each entity lives here** — and the local worked
examples — is this repository's `slot:entity-model` answer; a placeholder there costs you the
local homes, never the ladder.
Do not reconstruct either from this diagram.

**Every new slice names its feature area**:
`python3 knowledge/scripts/planning_mode.py --areas` lists them; propose the area whose feature map owns
the work, say which and why, and in a headless proposal put it in `under` as an `existing` node with id
`area:<slug>`. **The `existing` area must be one `--areas` lists in THIS checkout's repository** — the one the briefing's "About the … repository" line names. A feature map you find under another repository's tree (a submodule, a sibling clone) is not a home the accept can write to: "Create it" writes into the filing's own repository, and the fleet refuses a slice under a feature that repository does not hold. If the work belongs to another repository, still say so — in `whatItIs`, and in `alsoWeighed` as *"belongs in repository X; the filing needs to be moved"* — and the person withdraws the idea and files it against that repository. **Whether it ALSO joins a program depends on the planning mode** —
`python3 knowledge/scripts/planning_mode.py` prints `programs` or `areas` (`.fleet/fleet.toml`
`[fleet.planning] mode`; absent means `programs`):

- **`programs`** — as before: the slice is also placed under the program it serves.
- **`areas`** — no program, existing or new. **Never propose an existing program as the home for new work** in
  this mode — programs take no new slices and drain on their own. **And never
  propose a new program**: in this mode "program" is not a rung of the ladder at all. Work bigger than one slice is **several slices** — in one area, or across areas — ordered by
  each slice's `Depends on` and each PRD's `depends_on`; propose the first slice and describe the others in
  `alsoWeighed`. The shared ladder's section *In a repository that plans by area, "program" is not a rung* has the
  rule and a worked example. A `kind: program` proposal from a repository in this mode is refused by the fleet the
  moment it lands, so it never reaches a person.
- **`areas`, and no existing area fits** — propose the slice **together with a new feature area**: `kind: slice`
  with the additive `newArea` field (Step 6), argued against the closest existing areas the way `notOtherRungs`
  argues the size. The bar is high: a new area only for a
  **durable product capability bucket that will keep receiving work** — never for a one-off. The shared ladder's
  section *When no feature area fits* has the test and worked examples. In `programs` mode there is no `newArea`.

## What to do

### Step 0: Which way in, and which round

```bash
printf '%s\n' "${FLEET_RESULT_FILE:-<unset>}"
```

- **Unset** → a person is at the terminal. `$ARGUMENTS` is their request. Run Steps 1–4; the
  headless steps close as *not this mode*.
- **Set** → the fleet dispatched you on an idea. `$ARGUMENTS` is the issue key; the request
  is the **dossier** in the brief — nine fields, the filer's `problem` quoted verbatim, the
  ground intake already read, its provisional tier. Run Steps 1–3, then 5–7; Step 4 closes as
  *not this mode*. **Read what you were given and do not go looking for more of it**: the
  issue is fleet's to write and not yours to read, and the tracker is never opened from this
  path — every move the issue makes is written by fleet from the file you leave.
- **Set, with a `## Request` block whose `kind` is `entity`** → an **attended route of a knowledge
  row**: a person pressed Start on a requirement, capability or component page and is watching this
  session. `$ARGUMENTS` is that row's id. The block names its kind and id; the row is in this
  repository's knowledge base, **not the tracker** — read it from the registers (Step 2) and never
  look the id up as a tracker key. Run Steps 1–4 and **print the report** for the person. Then write
  the proposal (Step 6) to `$FLEET_RESULT_FILE` and the done-sentinel to `$FLEET_AGENT_DONE_FILE`,
  and say where the result is: the session is attended, so no service reads either back, but the
  files are the record beside the report. Do not write a question set; ask the person in the session
  if a fork truly needs an answer, and take the smaller rung when the evidence already points at one.
- **Set, with a `## Request` block and no dossier** → a **pre-placed** request: a new feature
  (`{"kind": "newFeature"}` — the filing's title is its name, its text the person's sentences),
  a new use on a feature (`{"kind": "newUse", "area"}` — the title is the use's name, the text
  its sentence), a plan for a feature's use or the whole feature (`{"kind": "plan", …}`) or the
  brief of a feature that has none (`{"kind": "writeBrief", "area"}` — the text, if any, is the
  person's note). There was no
  interview and there will be none. Run Steps 1–2 for the feature it names (or the closest
  ones, for a new feature), ask **at most two** questions by Step 5's mechanics, and write the
  proposal the feature-flow guidance (below, after Step 3) names for that request: a `kind:
  area` map-only proposal, a `kind: use` carrying `newUse`, a `kind: brief` carrying `featureBrief`, or a `kind: slice`
  carrying `plan`. A proposal that does not answer
  the request is refused as it lands.
- **Set, but no dossier in the brief** → a mis-dispatch. Emit nothing; write the sentinel with
  `status: "failed"` naming what was missing, and stop. Routing a bare sentence is the
  terminal path's job, with a person to ask.

Then, headless only, establish the round — the same three cases as
[`intake`](intake.md) §1, plus the one this command adds:

- **No prior question in the brief** → round one. Go to Step 1.
- **A prior question with its answer, and nothing newer** → you were resumed. The answer is in
  the resume prompt, paired with the question it answers. **Warm** (your own Steps 1–3 are
  still in context): go to Step 5's *consume* half. **Cold** (a fresh session — the transcript
  was pruned, the box rebuilt — with nothing but the brief): run Steps 1–3 again with the
  answer in hand, because `alreadyExists`, `ground` and `vision` are Steps 1–2's findings and
  a successor that skips them writes those fields from nothing. Then Step 6.
- **A prior question with no answer** → re-dispatched before the filer got to it. **Do nothing
  and end the turn.** Re-asking is how a filer receives the same round twice.
- **An instruction newer than the last answer** → the person read your earlier proposal and
  sent the idea back with a sentence saying what to change. **This outranks the resume case**:
  a brief carrying an old answered question *and* a newer instruction is **round one with the
  instruction in hand**, not a resume — run Steps 1–3 again, and expect to supersede the
  proposal on the page (fleet overwrites it with yours). **The one-question budget resets** —
  a re-route is a new walk, and Step 5's ceiling is per walk. The instruction binds the
  reading, not the filer's problem: it never licenses rewriting what they said the problem is.

  On a filing fleet holds without a tracker issue the instructions ride the brief under
  `## Sent back` rather than as comments; read them the same way. **An instruction from `fleet`
  is the service refusing your last placement** — it names the target and why it takes no new
  work; it is not a person's preference to weigh, and the same placement will be refused again.

### Step 1: Read the vision and the current state

`slot:product-vision`, then render the roadmap index with
`python3 knowledge/scripts/gen_roadmap.py` and read the roadmap it prints (generated on demand,
not committed — so it is never stale).
For anything program-shaped, also `python3 knowledge/scripts/gen_program_plan.py --list` — the program
ids (`PG-NN`) that already exist and whether they're decomposed; a single plan is
`gen_program_plan.py PG-NN`.

### Step 2: Scan for what already exists

- Planning tiers: the two registers — `slot:programs` (`PG-NN` rows) and
  `slot:slices` (`SL-NNN` rows), each row a fragment under `rows/` — one row per
  entity, so this is two directories to read, not fifty. **Count the active slices** (any whose member PRDs — the ones naming it in
  `slice:` — include a non-terminal one, or are all terminal but unproven).
  At the ceiling, nothing new gets cut; that changes what you can honestly route.
- The capability ledger: the relevant `knowledge/features/<area>.md` — does the request
  map to an already-named capability, and what does its `Ships in` say?
- The component registry (`slot:components`) when the
  request sounds like a subsystem
- The requirement registers (`slot:commitments`) — does this work realise
  commitments already written down? **Carry the matching IDs into the handoff**: they
  become the PRD's `implements:`, and a requirement no PRD claims is the backlog.
  Resolve the ground through the `## Component index` table in
  `slot:commitments` — the generated
  component→register join, rendered on demand and never committed, so run `python3 knowledge/scripts/gen_requirement_status.py` first — **never by guessing a filename from the request's wording**.
  **An unregistered ground is a routing signal, not a gap to note and move past.** If no
  register covers what the request touches, the product has never written down what this
  area promises, and framing that is [`slice:create`](slice/create.md) Step 3 — which is
  a reason to route at the **slice** tier even when the work itself would fit one PRD.
  Say so in the handoff: *"no register covers `workflow-engine`; the cut frames it."*
- the tracker: open `idea` issues + open issues carrying the involved `Component` labels —
  **at a terminal only.** Headless, everything here is a repo read, as it is for
  [`intake`](intake.md) §3: the dossier's `nearest`, `alreadyPromised` and `displaces` lines
  already carry what intake found on the board, and open pull requests on the ground
  (`gh pr list --state open`) are a git-host read, not a tracker one. **An `entity` request's
  `$ARGUMENTS` is a corpus id, not a tracker key** (a requirement row's id names a row in the
  registers, not an issue): read it from the registers above and never open the tracker for it.
- PRD frontmatter `status:` for anything in flight

### Step 3: Classify — the routing ladder

The user's request is: $ARGUMENTS — at a terminal, their words; on the fleet, the issue key,
and the request is the dossier's `problem` field, quoted, with the other eight fields as
evidence. For an `entity` request it is the row itself: read it from the registers, quote its
statement as the request, and carry its id into the handoff as the thing the new work serves.
**The dossier's `provisionalTier` is intake's guess and not your answer**: walk the
ladder on the evidence and let the rung fall where it falls, then say in the proposal where
you agreed with intake and where you did not.

Walk the ladder below **top-down; first match wins**. When the size is genuinely ambiguous,
ask ONE clarifying question before routing, shaped by the interview card:

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

**Headless, that one question is written, not asked** — a `questions` result document
(Step 5) whose every option is built to the card above, and whose park and resume the fleet
owns. The card's *Headless* line is the rule: the same words, into the document.

**The ladder — shared, the same in every repository:**

<!-- include: process/planning-ladder.md -->
### The planning ladder — which kind of thing is this?

**This ladder is the same in every repository.** It says what each kind of work is and in which
order to test for it. Where each kind *lives* in this repository — the file, the register, the
tracker project — and the local examples are the repository's own answer, `slot:entity-model`.
When the two seem to disagree about what a thing *is*, this ladder wins; when they disagree about
*where* it goes, the slot wins.

**Why it exists.** A router that judged size by feel turned a bug ("a session ignores new
messages while it waits on a long pull-request watch"), a one-page screen change and a request
for documentation into three new programs in one day. Each of them failed a test below that
nobody ran. Run the tests; do not judge by how big the request sounds.

#### First, two questions about the situation

These are about the request, not about an entity. Ask them before anything else.

| Ask | If yes |
|---|---|
| **Is something broken?** Something that used to work, or that the product already says it does, does not. A wrong or missing documentation page for something that ships counts. | **bug** — however large the fix turns out to be |
| **Is it early or exploratory** — "for later", not ready to build, nobody can yet say what done looks like? | **idea** — parked, not sized |

A bug stays a bug when the fix is big. A big fix is a reason for the bug to name a slice or a PRD
later; it is never a reason to make the bug a program.

#### Then the ladder — top down, the first match wins

The order is what removes the doubt: things that never finish are caught before anything is sized
as work, and the small work rungs are tested before the large ones.

| # | Ask | If yes |
|---|---|---|
| **1** | Can you point at the code it owns — a directory, a service, a set of tables? | **component** (built, never finished) |
| **2** | Is it a lasting property of the product? *One sentence a person can check* → | **capability** |
| | *…it emerges from several components and owns no code* → | **outcome** |
| **3** | Would a customer name it when describing what the product does, and does it group several capabilities? | **feature area** |
| **4** | Is it only a way to *filter* things that each already stand alone (security, onboarding, a release)? | **theme** — a label, never a container |
| **5** | Is it small, scoped work that needs no design decision and gives nobody a new thing to see or use? | **task** |
| **6** | Can one agent build it end to end in one working session, with acceptance criteria and a change a person can see or use? | **PRD** |
| **7** | Is it one deliverable — one feature, one capability and what it needs, or one set of gaps — with a "Done when" that none of its PRDs proves alone? | **slice** |
| **8** | Do **all** the program tests below pass? **Never in a repository that plans by area** — see below. | **program** |

**If nothing matches, you have not finished thinking.** (In a repository that plans by area, rung 8
never matches: work bigger than one slice is several slices.) The two usual landings: something that
never finishes but owns no code is an **outcome** (rung 2); something that finishes but holds one
deliverable is a **slice** (rung 7), not a program.

Components, capabilities, outcomes, feature areas and themes are **durable**: they never finish
and carry no status. Tasks, PRDs, slices and programs are work that finishes.

**A use is not a rung — and it is how a customer-facing feature is cut.** The customer page is *Features, uses and capabilities* (`knowledge-base/feature-areas`). A request is a **capability** when a use already covers its ground, a **use** when it is a main thing people do that no use says and it is not already one of them, a **feature** only when it passes the sub-feature test below; a row that fits none waits under `### Misfits (to move)` (*Writing a feature brief*, moment 2). A feature area's capabilities are grouped under its three to six **uses** —
the main things a person does with it (*Sign in with SAML* under sign-in) — so a request a customer
calls a "sub-feature" lands at rung 3 as an existing area plus a use, never as an area of its own.
It becomes its own feature area only when it needs its own brief or owner (*Writing a feature
brief*, feature-doc reconcile process document).

#### The size tests, smallest first

Each rung is the smallest one whose test the work passes. Test them in this order and stop at the
first pass.

- **Task** — scoped work that needs no design: a dependency bump, a configuration change, a
  refactor with no visible change, a wording fix. If two people
  could disagree about how it should look or behave, it needs a design, and it is not a task.
- **PRD** — one agent, one working session, one surface a person touches (a page, a control, an
  API behaviour, a command). It carries acceptance criteria that can each be shown to pass. One
  new screen is a PRD, however important it is.
- **Slice** — one deliverable that finishes, with a "Done when" a person can observe on the
  running product, which none of its PRDs carries alone. A slice usually holds two or more PRDs;
  a one-PRD slice is allowed but worth a second look, because it is often a PRD that has not yet
  found what ships beside it.
- **Program** — only when the work holds **at least two slices** under one result that neither
  slice delivers alone. **One deliverable is a slice, not a program**, however large it is.
  **In a repository that plans by area there is no program rung at all** (next section).

#### In a repository that plans by area, "program" is not a rung

Run `python3 knowledge/scripts/planning_mode.py`. It prints `programs` or `areas` (the setting is
`[fleet.planning] mode` in `.fleet/fleet.toml`; no setting means `programs`).

**When it prints `areas`, the ladder stops at rung 7. No new program is ever proposed or created**. Programs that already exist keep running until their slices finish; nothing new joins
them.

Work that is bigger than one slice does not become a program. It becomes **several slices**:

- **Each deliverable is its own slice**, with its own "Done when", under the **feature area** that
  owns it. Two deliverables in one area are two slices in that area; deliverables that belong to
  different areas are slices in different areas.
- **The order between them is written as dependencies, not as a container.** A slice that cannot
  start before another finishes says so in its `Depends on`; a PRD that builds on another PRD says
  so in its own `depends_on`. That is all the grouping the work needs.
- **The program tests still help you think** — a literal title, a person who notices, a day it
  becomes true — but what they describe is the *set* of slices. Nothing is created for the set itself.
- **When you route such a request, propose the first slice** (the one the others depend on), and
  describe the other slices in plain words in `alsoWeighed`, so the person who accepts sees the whole
  shape of the work. Each further slice is its own proposal, when its turn comes.

**Worked example (areas mode).** *"A new customer account is set up and served without an engineer
in the loop."* In a repository that plans by program this is the program in the worked examples
below. In a repository that plans by area it becomes two slices:

1. *Accounts are provisioned from the sign-up form, with no engineer* — a slice in the
   `accounts` area. Done when a sign-up creates a working account on the running product.
2. *A first run that needs no help* — a slice in the `onboarding` area, with `Depends on:` the
   first slice. Done when a new account finishes the first run without a support ticket.

Route proposes slice 1 and names slice 2 in `alsoWeighed`; when slice 1 is accepted, slice 2 is
proposed in its turn. No program row is written, so there is nothing to migrate later.

#### When no feature area fits: a new area, with its first slice

In a repository that plans by area every slice names a **feature area** (`planning_mode.py --areas` lists them).
When the request fits none of them, route proposes the slice **together with a new feature area**, and the one
accept creates both: the area's feature map and the slice, in one pull request, with the person who accepted as the
area's first owner. In a repository that plans by program
this does not happen: new work goes under an open program.

**The bar is high, because every new area is one more place every filing must choose between.** Propose a new area
only when all of these hold:

1. **No existing area fits — and you can say why for each close one.** Name the closest existing areas and, for
   each, why the work does not belong there, as evidence from the request. If you cannot write the reason for an
   area, the slice goes under that area. This is the same check as *Say why it is not each smaller rung*, applied
   to areas.
2. **A customer would name it** when describing what the product does (rung 3's test), and it groups capabilities.
3. **It will keep receiving work.** You can name at least two more capabilities it will hold after this first slice.
   A one-off — a single feature, a migration, one customer's list of gaps, a cleanup — is never a new area: put it
   under the closest existing area and say plainly that the fit is weak.

The new area's sentence says what a person can do there, for as long as the area exists; it is never the first
slice's "Done when". The proposal also carries the new map's **feature brief** and its **uses** — the
things a person will do in the area, written to *Writing a feature brief* in the feature-doc reconcile process document.
An area you cannot cut into three uses fails test 3.

**Worked examples (areas mode).**

| Request | Existing areas | Lands on | Why |
|---|---|---|---|
| *"Customers get an invoice each month for what they used."* | accounts, sessions, board | **slice, in a new area `billing`** | Charging for use is a job a customer names on its own ("billing"). Not *accounts*: that is who may sign in. Not *sessions*: that runs the work, it does not charge for it. Billing will keep receiving work: payment methods, refunds, spending limits. |
| *"Show the session's cost next to its duration."* | accounts, sessions, board | **slice (or PRD) in `sessions`** | One more fact on a page that already exists. Even if cost later belongs to billing, this one change does not make a new area. |
| *"Migrate the old export files to the new format."* | accounts, sessions, board | **task, under the area that owns the export** | A one-off. Nothing will keep arriving in a "migration" area. |

#### The program tests — every one must pass

1. **The title is literal.** Someone who reads only the title can say what will be delivered. A
   title that reads well and says nothing fails ("Make it great", "Interrupt PR polling").
2. **A person or a surface.** Either name a person, in a situation, who is stuck today — *when
   `<situation>`, I want to `<motivation>`, so I can `<outcome>`* — or name the thing that lands and
   the customer surface it shows up on. "Runtime work" names neither.
3. **A day it becomes true, and somebody notices.** "A new customer account is set up and
   served without an engineer in the loop" has such a day. "Scalability" does not: a program that
   cannot be shown false on a day is a **theme**.
4. **At least two slices.** Describe the two (or more) deliverables in plain words, each one
   finishing on its own. If you can describe only one, it is a slice.
5. **No existing open home fits.** Create a **new** program only when no existing open home can
   take the work **and** the work holds at least two slices. Joining a home that already exists is
   always the first thing to check.

#### Homes: prefer an existing open one

A **home** is the existing container new work goes into. Before you propose anything new, look for
an existing open home that the work genuinely serves.

- **A home is open when it still takes new work.** One that is withdrawn, or complete, is closed.
- **A closed home is never stretched to fit.** New work for a finished slice is new work: it needs
  an open home of its own. Name the closed home you passed over, and why, so the reader sees it.
- **Never invent a container to give a small piece of work somewhere to go.** A one-deliverable
  request with no good home is still one deliverable; say plainly that the fit is weak and let the
  person who accepts decide.

#### Say why it is not each smaller rung

Whatever rung you land on, write one line for **each smaller work rung** saying why it is not that
rung: a program says why it is not a bug, a task, a PRD or a slice; a slice why it is not a bug, a
task or a PRD; a PRD why it is not a bug or a task; a task why it is not a bug. The line is
evidence from the request, not a restatement of the rung's name. **If you cannot write the line
for a smaller rung, the work is that smaller rung.** This is the check that makes a wrong size
visible to the person who accepts it.

#### Worked examples

| Request | Lands on | Why |
|---|---|---|
| *"A session ignores new messages while it waits on a long PR watch."* | **bug** | Something is broken. A big fix does not change that. |
| *"Maybe one day we support single sign-on with more providers."* | **idea** | Nobody can say yet what done looks like. |
| *"The setup guide is missing the step that creates the API key."* | **bug** | The page is wrong for something that already ships: a docs defect, corrected where the docs live. |
| *"Bump the HTTP client library to the current version."* | **task** (5) | No design, nothing new for anyone to see. |
| *"Add a page listing filings that are still waiting for an answer."* | **PRD** (6) | One screen, one session, testable acceptance criteria. Important is not the same as large. |
| *"Add CSV export to the audit log."* | **PRD** (6) | One agent-session, one surface. |
| *"A reviewer can read the audit record and act on it."* | **slice** (7) | One capability with a "Done when" none of its PRDs proves alone. |
| *"Everything still missing for the acme pilot."* | **slice** (7) | One set of gaps for one customer; the members share nothing else. |
| *"A new customer account is set up and served without an engineer in the loop."* | **program** (8) | A named person notices on a day, and it holds at least two separate deliverables (provisioning, and a first-run that needs no help). **In a repository that plans by area: two slices**, in their own areas, the second depending on the first (see above). |
| *"Rate limiting."* | **component** (1) | You can name the directory. A mechanism is never a planning level. |
| *"Scalability."* | **outcome** (2) | No code owns it and it never finishes; it earns slices while it is being built. |
| *"Security."* | **theme** (4) | A filter across work that already stands alone. Never a new program. |

#### Smell tests

- **A program with one deliverable** is a slice wearing a program's name.
- **A program created from a single request on the day it was filed** almost always failed test 4
  or test 5. Look again.
- **A program whose title describes a defect** ("X ignores Y") is a bug.
- **A slice you cannot write "Done when" for** is not a small slice; it is a label (a theme).
- **A "task" that needs a mockup or an argument about behaviour** is a PRD.
<!-- /include -->

**In a repository that plans by area, the feature flows bind every headless walk**: a dossier
carrying `placement` is placed exactly there, a new feature is proposed as its map only, a new
use as that one use, and a
plan is one to three named slices with their pieces of work. The shapes and the one exception
to the third gate (a plan names its slices and writes their `Done when`) are in the shared
guidance:

<!-- include: process/feature-flow.md -->
# The feature flows — new feature, new use, plan, the brief, removing a use, and where a feature request goes

> The one guidance doc for the six front doors a repository that **plans by area** offers
> (`planning_mode.py` prints `areas`). `intake`, `route` and `slice:create` each read the part
> that names them; none restates it. The shapes are enforced by the fleet as the result lands
> (`dispatch.results`), so a document that breaks one is refused and never reaches a person.
> In a repository that plans by program none of this applies: there is no feature to place in.

**The person reads every card these flows produce, and they are a customer.** Every question,
option, brief and plan names the **feature and the use in words** — never an id (no program,
slice, issue, capability or PRD number; the fleet refuses a card that carries one), never a
command, never Fleet's internal steps. Address it to them: a question these flows ask goes to
the person who filed, never to "the fleet's operators". A **feature** is a feature map; a
**use** is one `###` section of its `## Capabilities` — a thing a person can do with it.

**No flow here creates or names a program.** A plan is one to three slices under the feature;
work bigger than that is more slices, ordered by `Depends on`.

## The requests

The filing's brief says which one it is: a pre-placed filing carries a `## Request` block, and
every intake or route dispatch in this mode carries a `## Features` block — each feature as
`### <slug> · <name> — <summary>`, then each use as `- <name> — <paragraph>`. **Match and
offer only what `## Features` lists**: it is what the feature pages show, and an option naming
a feature or use it does not list is refused.

| request | how it arrives | who runs | what route proposes |
|---|---|---|---|
| **feature request** (no `## Request`) | the person typed what the product should let them do | `intake`, then `route` | per the confirmed `placement` (below) |
| **new feature** (`{"kind": "newFeature"}`) | a name (the filing's title) and two or three sentences, from the Features page | `route` directly — no interview | `kind: area`: the feature's map only |
| **new use** (`{"kind": "newUse", "area"}`) | "+ Add something this feature should do" on a feature's page: a name (the filing's title) and one sentence | `route` directly — no interview | `kind: use` carrying `newUse`: one new use on that feature's map |
| **plan** (`{"kind": "plan", "area", "use"}`, `use` null = the whole feature) | "Plan this" on a use, or "Plan the whole feature"; and Fleet itself, once, when an accepted new use lands | `route` directly — no interview | `kind: slice` carrying `plan` |
| **remove a use** (`{"kind": "removeUse", "area", "use"}`) | "Remove this use…" on a use already on a feature's page; the text is the person's reason | `slice:create` directly — Fleet accepts the removal for the person, who already confirmed it with the reason | nothing: there is no proposal to check |
| **write the brief** (`{"kind": "writeBrief", "area"}`) | "Write the brief" on a feature whose map has no brief or no uses; the text, when there is any, is the person's note (it may name one more thing the feature should do) | `route` directly — no interview | `kind: brief` carrying `featureBrief`: the brief, and the map's rows sorted into uses |

A new feature, a new use, a plan and a brief are **pre-placed**: the person already said where the work goes, so
there is no interview and no placement question. Route may ask **at most two** questions across
the run (instead of its usual one), each one the person could not have answered by pressing the
button they pressed — never "is this really a new feature?".

## Feature request: the placement question comes first

**`intake`'s round one is always the placement question**, before any other question, and it
does not count toward the eight-question ceiling or the round limit — it is Fleet's question,
not a gap the filer left. One question in the set, `"kind": "placement"`:

```json
{"id": "placement", "kind": "placement", "prompt": "Where does this go?", "allowFreeText": true,
 "options": [
   {"id": "p1", "label": "Extends <Feature> → <Use>", "then": "Fleet shapes your request inside <Use>.", "recommended": true,
    "placement": {"choice": "extends", "area": "<slug>", "areaName": "<Feature>", "use": "<Use>",
                  "useParagraph": "<the use's paragraph>", "fit": "strong", "why": "Why here: <evidence from their words>."}},
   {"id": "use", "label": "A new thing <Feature> does: <drafted name>", "then": "Fleet adds it to <Feature>, ready to plan.", "recommended": false,
    "placement": {"choice": "newUse", "area": "<slug>", "areaName": "<Feature>",
                  "newUse": {"name": "<drafted use name>", "paragraph": "<one or two plain sentences>"}, "why": "<why this feature>"}},
   {"id": "new", "label": "A new feature: <drafted name>", "then": "Fleet drafts the new feature for you to check.", "recommended": false,
    "placement": {"choice": "new", "newFeature": {"name": "<name>", "summary": "<one sentence>", "uses": ["<use>", "..."]},
                  "whyNot": [{"area": "<slug>", "areaName": "<Feature>", "why": "<why it does not fit>"}]}},
   {"id": "not", "label": "Not a feature: it's broken", "then": "It goes to the bug sheet with your words.", "recommended": false,
    "placement": {"choice": "bug", "why": "<what you read that says so>"}}
 ]}
```

- **Options, in this order:** the best-matching feature → use; **at most one** "A new thing
  <Feature> does" (`newUse`) — when the best feature plainly fits but none of its uses does,
  drafted as a use name and one or two plain sentences; **up to two** alternative feature → use
  pairs (with the new thing, at most three options name an existing feature); **at most one**
  "A new feature"; **exactly one** "Not a feature" — a `bug` ("it's broken") or a `task`
  ("it's a small change"), whichever the words read as. Two to five options; this is the only
  question allowed a fifth. When the card is full, the new thing takes "A new feature"'s place
  only when that feature clearly fits; otherwise it takes an alternative's.
- **Matching:** read the top candidates' summaries and each use's paragraph; a feature's
  `brief.not` lines name its siblings on purpose and break ties. `fit: strong` when the
  request plainly does what the use's paragraph says; else `weak`.
- **Which one is `recommended`:** the best match when its fit is strong; the new thing when the
  feature fits strongly and no use does. When none is strong,
  "A new feature" — but only after the new-feature gate below: if you cannot write a `whyNot`
  for a close feature, the request goes under that feature and that option is recommended.
  When the words describe a defect or a small change to something that exists, "Not a feature".
- **The `brief`** says in two plain sentences what you read the request to be and that nothing
  is created yet. **A repository with no feature map** asks no placement question at all.

**On resume**, copy the answer into the dossier as `placement`:
`{"choice", "area"?, "areaName"?, "use"?, "newUse"?, "newFeature"?, "confirmedBy"}` — the option they
picked; free text ("somewhere else") is re-matched against `## Features` and asked once more
only if it still fits nothing. Then:

- **`extends`** — shape the rest of the interview inside that feature and use; ask nothing the
  use's paragraph already answers.
- **`newUse`** — ask nothing more and write the dossier; route turns it into the new-use
  proposal below, its name and paragraph the option's draft.
- **`new`** — ask at most one more question about the new feature itself, then write the
  dossier; route turns it into flow 1's map-only proposal and the request becomes one of its uses.
- **`bug` / `task`** — emit the `handback` with that `looksLike`, quoting their own words.

## What route proposes, by request

**Route is bound by the confirmed `placement` and by the `## Request`.** A proposal that
contradicts either is refused as it lands (`proposal-placement-mismatch`) and route is sent
back once with the reason.

- **placement `extends`** — `under` names `area:<slug>` (`existing`); add the optional
  `"use": "<Use>"`. Size it as usual (slice, PRD, task), never a new feature.
- **placement `newUse`, or a new-use request** — **`kind: "use"`** carrying **`newUse`**:
  `{"area", "areaName", "name", "paragraph"}`, `under` naming `area:<slug>` (`existing`) then
  the use as `{"id": "new use", "name": "<name>", "meta": "use", "status": "new"}`, and nothing
  else — no slice, no piece of work. Draft it by *Writing a feature brief* → moment 5 (*Taking
  in what a person adds*, `feature-doc-reconcile.md`): a thing a person does, named in a few
  words with a verb first ("Reserve parts for a repair"), and one or two plain sentences saying
  what they do with it and why — the person's own words where they are plain, from a placement
  the option's draft. Never ship-state words ("shipped", "planned", "partly built", "still open"
  — the map's check refuses them, so write "a booked repair", not "a planned repair").
  **Flag a near-duplicate, not only an exact name**: when an existing use's name or paragraph
  already says this in other words, a new-use request spends its question on it ("This reads
  like *Book a repair*, which the feature already does — add it there, or add it as a new
  thing?"), and the placement card offers that use as `extends` instead of a new thing. The
  fleet refuses only an exact name (case folded); the near-duplicate is yours to catch.
  **Every option of that question carries its `placement`** — `{"choice": "extends", "area",
  "use"}` on "add it there", `{"choice": "newUse", "area", "newUse": {"name"}}` on "a new
  thing" — because **the person's answer outranks the request**: the fleet reads the picked
  option's `placement` off the held, answered question and judges the proposal by it. Answered
  `extends`, propose as for **placement `extends`** above (inside that use, never a new use —
  a new use is refused as it lands); answered `newUse`, the new use.
  `onAccept.command` is `slice:create`, which adds the use to the map. However many uses
  the feature already has, a new one is added the same way.
- **placement `new`, or a new-feature request** — **`kind: "area"`** carrying `newArea`
  (`slug`, `name`, `sentence`, `whyNoExistingArea`, `brief`, `uses` — the same shape and the
  same fourth gate a `newArea` on a slice carries), `under` holding exactly the new
  `area:<slug>` node, and **no slice**. Draft the brief to the feature-brief schema
  (`summary`, `problem`, `example`, `example_from`, `not`) and **uses**, each a
  thing a person does, with one plain paragraph — every word by *Writing a feature brief* →
  moment 5. `onAccept.command` is `slice:create`, which writes the map. Derive the slug and name from the person's name for it.
  **Numbered requirements are the person's own and none may vanish.** When the filing's text
  holds lines numbered `R1`, `R2` and so on, every such number goes on the use that delivers it,
  as `covers` (`{"name", "paragraph", "covers": ["R2", "R5"]}`). A requirement you cannot place
  on any use stays out of every `covers`: the Handbook shows it to the person, who adds it or
  leaves it out. Never drop one silently, and never list a number on a use that does not deliver it.
- **a plan request** — `kind: "slice"` carrying **`plan`**:
  `{"area", "areaName", "use" (null for the whole feature), "slices": [{"name", "delivers",
  "doneWhen", "prds": [{"title", "sentence"}]}]}`, one to three slices in build order, each
  with one to six pieces of work. `under` names `area:<slug>` (`existing`) then the slices as
  `new`. **This is the one proposal that names its new entities and writes a `Done when`**:
  the person asked for a plan, and a plan is exactly those words. Each slice is still a cut
  that completes — `delivers` is what a person can do once it is done, `doneWhen` one
  observable sentence — and holds the work the ladder puts in a slice (two or more pieces,
  unless the use is genuinely one piece of work). A plan for the whole feature covers every
  use that has open ground, in the order a person would want them. Its words — `delivers`,
  `doneWhen`, each piece's title and sentence — follow *Writing a feature brief* → moment 5, and
  a piece an existing capability row already covers is named, never planned twice.

- **a write-the-brief request** — **`kind: "brief"`** carrying **`featureBrief`**:
  `{"area", "areaName", "brief": {"summary", "problem", "example", "example_from", "not"},
  "uses": [{"name", "paragraph", "rows": ["<row id>", ...]}]}`, `under` naming `area:<slug>`
  (`existing`) then `{"id": "brief", "name": "The brief and its uses", "meta": "brief", "status":
  "new"}`, and nothing else. Read the feature's map: its Intent, its existing brief and use
  paragraphs where it has them, and every capability row. Draft the brief to the feature-brief
  schema and **sort every live row** (each row outside `### Misfits (to move)` and `### Retired`)
  **into uses** — fewer for a small map: one or two when it has fewer than three rows,
  none needed when it has none — each a thing a person does, with one plain paragraph, every word by
  *Writing a feature brief* → moment 5. **Rows are only regrouped**: name each by its id, every live
  row in exactly one use; never reword, renumber, add or drop one — the fleet refuses a sort that
  misses, repeats or invents a row. A use that fits an existing `###` keeps its name. When the
  person's note names something the feature should also do that no row covers, add it as one more
  use with `"rows": []`. `onAccept.command` is `slice:create`, which writes the brief into the map.

**The person may edit before accepting** — the new feature's name, sentence, brief and uses,
the new use's name and paragraph, the brief and the uses of a feature's brief (including which
use a row sits in), or the plan's slices — and the accepted proposal carries their words. Write from the proposal
the brief carries, never from your memory of the draft.

## What `slice:create` writes from an accepted proposal

- **`kind: "area"`** — **only the feature map**: run `new_feature_area.py` with `--brief-json`
  and one `--use` per use, exactly as for a `newArea` on a slice, and write **no slice row**. A
  feature with no code yet passes no component and no code path (slice:create's writer notes).
  Land it by one merged PR and report `created`:
  `{"kind": "area", "id": "<slug>", "name": "<name>", "href": "areas:<slug>", "pr": "<url>"}`.
- **`kind: "use"`** — **only the new use**: run
  `python3 knowledge/scripts/new_feature_use.py --area "<newUse.area>" --name "<newUse.name>"
  --paragraph "<newUse.paragraph>"`, which adds it to the map as a `###` section with an empty
  table, and write **no slice row and no capability row** — its work arrives with the plan made
  for it from the feature's page. Land it by one merged PR and report `created`:
  `{"kind": "use", "id": "<area>", "name": "<newUse.name>", "href": "areas:<area>", "pr": "<url>"}`.
- **`kind: "brief"`** — **only the brief and the uses**: run
  `python3 knowledge/scripts/write_feature_brief.py --area "<featureBrief.area>" --brief-json
  '<featureBrief.brief as JSON>' --uses-json '<featureBrief.uses as JSON>'`, which writes the brief
  into the map's frontmatter and moves each row, byte for byte, into the use that names it (notes
  that sat between the old tables move to a `## Notes` section). Write **no slice row and no new
  capability row**. Land it by one merged PR and report `created`:
  `{"kind": "brief", "id": "<area>", "name": "<areaName>", "href": "areas:<area>", "pr": "<url>"}`.
- **`kind: "removal"`** (a remove-a-use request; Fleet wrote the proposal, `removeUse`: `{"area", "areaName",
  "use", "why"}`) — **only the removal**: run `python3 knowledge/scripts/remove_feature_use.py --area
  "<removeUse.area>" --name "<removeUse.use>" --reason "<removeUse.why>"`. It takes the use's `###` section off the
  map and moves every table it held, byte for byte, to `### Retired` (built work stays on the page, retired; nothing
  is deleted), and cancels each plan under the use that is not built yet the way `prd:cancel` Step 2 does, with the
  person's reason. Write nothing else: no row, no slice, no reworded line. Its last stdout line says what it retired,
  cancelled and kept; put that in the PR description in words. **When it exits 3**, work under the use is being built
  right now: ask the person **one** question — stop that work and remove the use, or keep the use (withdraw the
  removal) — and on "stop it" run it again with `--stop-work-being-built`. **When it exits 2**, end the run with its
  sentence as the summary, a question to the person; their note, or withdrawing the request, is the answer. Land it by
  one merged PR and report `created`:
  `{"kind": "removal", "id": "<area>", "name": "<removeUse.use>", "href": "areas:<area>", "pr": "<url>"}`.
- **`kind: "slice"` with `plan`** — one slice row per `plan.slices` entry, in order, each in
  `plan.area`, `Depends on` chaining them in build order, `Done when` the entry's `doneWhen`
  verbatim; and under each, one **PRD stub** per `prds` entry, written the way `prd:create`
  writes a stub from an accepted proposal (`status: stub`, the entry's title and sentence as
  the brief, the slice and area named, nothing else) — and it **records the use in the stub's
  frontmatter as `use:`** (the use `plan.use` names; for a whole-feature plan, the use that
  slice serves). **And one capability row per piece of work** in the area's map, under that use's
  `###` section: a fresh `CAP` id from the allocator, the capability cell
  `**<title>** — <sentence>`, reworded only to meet the standard, `Ships in` the piece's PRD stub number, `Tested by` `—`. That row is what
  makes the use read as planned work, with its slices under it, the moment the PR merges — and
  stops the page offering "Plan this" again. One merged PR for all of it; report `created` for the first slice with the rest under `"also":
  [{"id", "name", "href"}]`. The pieces of work then go through the usual fill, design and
  build.
<!-- /include -->

The two state questions route straight away: **broken** → `/fleet:bug:fix` (or `bug:create` to
just file it); **early or exploratory** → `/fleet:idea:create` (parks the tracker `Type:idea`
issue).

**A docs request is classified through `slot:docs` before the ladder, and it has two
shapes.** *A page is missing or wrong for a capability that already ships* is a **defect** —
route it to `/fleet:bug:fix` (or `bug:create`) to correct the page where the docs live; it is
not new work. *A page promises something the product does not do* is **also a docs defect**,
and the page is corrected — it is **never** a request to build the promised feature. The page
describes scope; it does not set it, so do not let its prose smuggle a build request through
the ladder. If the promised capability is genuinely wanted, that is a **separate new** request
and walks the ladder on its own evidence. When the repository leaves `slot:docs` unfilled the
home is unknown: route the fix anyway and say so (the slot's degrade) rather than inventing one.

**Then read the rung the ladder landed on and map it with this table.** Routing is the only
thing this command owns; the ladder, its size and program tests, and its worked examples are
the shared ladder's, and it wins if they ever disagree. `slot:entity-model` tells you where the
rung's entity lives in this repository, and its local examples beside the shared ones.

| Ladder rung lands on | Route to |
|---|---|
| **component** | a component registration (`slot:components`) (a label; it never becomes a slice) |
| **capability** / **outcome** | a ledger row in the area's feature map (`slot:feature-maps`) — never a folder. An outcome earns **slices** while being built. |
| **feature area** | a feature map (`slot:feature-maps`) — **and note that it is also the tracker project** (`slot:feature-areas`) any task/bug/finding on this ground gets filed into |
| **theme** | **nothing gets written.** Say it in prose where it helps a reader; there is no theme row, folder or cell to file it in, and a theme is never a new program. |
| **decision** — *can you name the option we rejected?* | a dated, append-only record where `slot:decisions` says, from its template, or the owning PRD's `design.md`. **Not work — never sized.** |
| **requirement** — *can you write it as "the system shall / never", and observe a violation?* | one numbered row in the domain's register (`slot:commitments`). **Not work — never sized.** |
| **task** | `/fleet:task:create` or `task:implement` |
| **PRD** | `/fleet:prd:create` (Phase 0.5 places it in a slice) |
| **slice** | `/fleet:slice:create` (named for what ships, with a `kind:` and a "Done when" — no dates, and refused past `slot:slices`) |
| **program** | `/fleet:program:create` → `/fleet:program:decompose` — **only when every program test passes**, the fifth included: no existing open home fits and the work holds at least two slices. **Do not route its pieces yourself** — that is the decomposition's job, with better evidence. **Never in a repository that plans by area** (`planning_mode.py` prints `areas`): there the work is several slices, and route proposes the first one — both program commands refuse in that mode. |
| **a program already in execution** | `/fleet:program:deliver` — one cycle: release dispatch-ready work, triage, escalate. Recur it via `/loop` or a schedule. |
| **a program whose work is all done** | `/fleet:program:ship` — gates on proof and lands the closing record as a merged PR. There is no status to flip; it refuses to certify if the proof does not hold. |

**The last two are the constraint axis, and route names them without authoring them.**
Neither is on the ladder and neither is work, so there is no pipeline command to hand
them to — which is exactly why they get mis-routed into a PRD or vanish. Route owes them
two things instead:

1. **Name it**, so a *"the system shall never …"* is not handed to a build pipeline that
   then builds the wrong thing.
2. **Ask who claims it.** A requirement's status is derived from PRDs' `implements:`, so
   *no claiming PRD* is the backlog signal, not an absence of information. If the user
   wants it built now, **walk the ladder again on the work that would satisfy it** — that
   lands normally (usually a PRD) and carries the requirement ID into `/fleet:prd:create`,
   which sets `implements:` and cites it from an acceptance criterion.

The row or record itself is authored **where the commitment was settled** — the decision
record, the PRD's design, the audit finding, the corpus-extraction pass — because a row's
`Source` is load-bearing and a routing conversation settles nothing. A *"shall"* with no
source is not a requirement yet; it is an unsettled fork, and that is an interview
([`interview-protocol.md`](../../process/interview.md)), not a
hand-off.

Then the non-tier routes: small scoped change → `/fleet:task:create` or `task:implement`;
UX change to an existing page → a page-improvement task; connector work → a connector task.

When the user hands you "a b c" as a *list*, run the ladder on each item separately — lists
usually mix kinds, and mixed kinds is the single most common way work lands at the wrong tier.

### Step 4: Report and recommend (a person at a terminal)

The interactive ending. Headless, this step closes as *not this mode* — the proposal document
(Step 6) carries the same content, field by field, to the idea's page.

```
## Build request: <name>

**Vision alignment:** persona · customer value · differentiator (one line each;
  if it aligns with none, SAY SO — it may not belong on the roadmap)

**What it is:** program | component | slice | PRD | task | bug | idea | decision | requirement
  <one sentence: which test it passed>

**Why not smaller:** <one line per smaller work rung — bug · task · PRD · slice — saying why it
  is not that rung; for a program, also the two or more deliverables it holds, in plain words>

**What already exists:** <capability rows + their Ships-in · in-flight PRDs ·
  related ideas/issues · the component(s) involved>

**Recommended next step:** /fleet:<command> — <the requester's own words, verbatim>
  <1-2 sentences why. For multi-item requests: one row per item.>
```

**In-flight state shortcuts** (when the request matches an existing PRD): route by its
`status:` — `prd-drafted`→`prd:design` · `designed`→`prd:plan` · `planned`→`prd:implement`
· `implementing`→continue or `prd:verify` · `verified`→`push` · `shipped`→"appears
complete — iterate?" · `cancelled`→new PRD number.

### Step 5: Headless — ask at most one question, then stop

**Only when the size is genuinely ambiguous after Steps 1–3** — two rungs fit the evidence
and the dossier does not settle which. Anything the repo could have answered is not a
question; anything intake already asked is not a question; a question asked to look
thorough is the defect. **One question, one round, never a second**: if the answer still
leaves two rungs, take the smaller one, say so in `alsoWeighed`, and go on.

**A round is a `questions` result file and the end of your turn.** Write it to
`$FLEET_RESULT_FILE` (Step 7 owns the mechanics), write the sentinel, stop. Fleet moves the
issue to its answer queue, renders the question on the idea's page under *Route asked you*,
and resumes **this same engine session** when the answer lands.

```json
{
  "kind": "questions",
  "brief": "What I am placing: …\nFor example: …\nWhat is undecided: …",
  "questions": [
    {
      "id": "q1",
      "prompt": "<the fork, in plain words, saying what it settles — so a cold successor reading the answer alone knows what was decided>",
      "allowFreeText": true,
      "options": [
        {"id": "a", "label": "<short, plain, no ids>", "then": "<what changes for a real person · Why · Con>", "recommended": true},
        {"id": "b", "label": "<short, plain, no ids>", "then": "<what changes for a real person · Why · Con>", "recommended": false}
      ]
    }
  ]
}
```

- **`questions` holds exactly one entry.** Two is a second round wearing one file. (A
  pre-placed request may ask a second question, in a second round, when the first answer left
  one more fork only the person can settle — never more.)
- **2–4 options, exactly one `recommended: true`, a `then` on every one**, `allowFreeText:
  true` — the shape [`intake`](intake.md) §5 pins, and every rule there is load-bearing here.
- **The `brief` says what the idea is before the fork appears** — the filer has not read the
  dossier's ground; they read this and nothing else.
- **No planning id in a `label`, ever.** The measured failure this command produced was a
  four-option question built from bare ids. Ids belong in the proposal, as evidence.

**Consume — on resume.** The answer arrives paired with your question, in the resume prompt.
Take it as given (a free-text answer beats a picked option), re-run Step 3 with the rung it
settles — **Steps 1–3 if this is a cold session** (Step 0) — and go to Step 6. **Never
re-ask** — an unanswered question is an open item, and the proposal says so in
`alsoWeighed`.

### Step 6: Headless — write the proposal

**One document, every field, every time.** A person accepts or sends back from this and
nothing else, so a field left empty is the one they needed. The fields, in the order the page
shows them:

| Field | What goes in it |
|---|---|
| `kind` | `program` · `slice` · `prd` · `task` · `bug` — the rung the ladder landed on. **Never `program` in a repository that plans by area**: there the ladder stops at the slice, and the fleet refuses a `program` proposal on arrival |
| `whatItIs` | one sentence, plain: *"A new cut inside a program that already exists."* |
| `test` | the entity test it passed, in the ladder's words — the rung's size or program test from the shared planning ladder (Step 3), applied to this evidence |
| `under` | the walk, top-down, from the nearest **existing** tier to the one **new** node — see below |
| `notOtherRungs` | one `{rung, why}` per rung it is *not* — **required, never empty**: one entry for **every smaller work rung** (`bug` · `task` · `prd` · `slice`, those below `kind`), plus any larger rung a reader would reach for. For a `bug`, the `task` a reader might call it, and why it is broken rather than new. See the second gate |
| `alreadyExists` | one line each: the capability rows and their `Ships in`, the in-flight PRDs, the related issues, the components — Step 2's findings, with ids in parentheses after the plain name |
| `ground` | what the requirement registers say about this ground — the adopted rows that cover it, or *"no register covers `<component>` — the cut frames it"* |
| `vision` | `{aligned, persona, value, differentiator}` — Step 1's check; `aligned: false` is a legitimate answer and flags the idea rather than hiding it |
| `alsoWeighed` | `{option, whyNot}` for each placement you considered and did not take — an existing cut it could join, a second program it could serve — or `[]` |
| `onAccept` | `{command, lands, next}` — what fleet runs, what appears where, and what the person does on the new thing's page |
| `newArea` | **`kind: slice` in `areas` mode only, and only when no existing area fits** (an additive field; omit the key otherwise): `{slug, name, sentence, whyNoExistingArea: [{area, why}], components?}` — `slug` the new map's file name (`knowledge/features/<slug>.md`: lower-case, digits, `-`), `name` what the board shows, `sentence` the area's one-sentence Intent (what a customer can do there, durable — no deliverable, no date), `whyNoExistingArea` **at least one entry**: the closest existing areas from `planning_mode.py --areas`, each with why it does not fit, `components` the registered components that will realise it when you can name them, `brief` the new map's feature brief `{summary, problem, example, example_from, not}` and `uses` its **uses** `[{name, paragraph}]` — both written to [*Writing a feature brief*](../../process/feature-doc-reconcile.md#writing-a-feature-brief--every-map-that-is-created-or-edited), so the person accepts what a newcomer will read first. See the fourth gate |
| `programTests` | **`kind: program` only, and then required** (an additive field: the page shows it under *Also carried*): `{literal, personOrSurface, dayItBecomesTrue, slices, noOpenHome}` — one sentence each for the ladder's program tests 1–3 and 5, and `slices` a list of **at least two** deliverables described in plain words, each one finishing on its own. Described, never named, never given a `Done when`: the decomposition cuts them. Omit the key for every other kind |

**`kind` is a closed set of five, and the ladder has more rungs than that.** When Step 3
lands on a rung the document cannot name, `kind` is the **work that rung implies**, walked
again as Step 3 already does for a requirement: registering a component, or recording a
decision or a requirement row where it was settled, is a `task`; a **capability** or a
feature-area row lands with the work that ships it, so walk again on that work — one
agent-shift → `prd`, more than one → `slice` with `meta: capability` (the ladder's own
`kind: capability` cut); a page improvement is a `task` naming the page. When **nothing would be built** — a theme, or an idea aligned with no
persona — say exactly that in `whatItIs` and `vision`, propose `task` as the smallest honest
kind, and say in `next` that the triage gate may close it: a task is re-kinded into the
triage queue, where [`/fleet:check`](check.md) is the one gate with a *close* verdict, and
the person routing can withdraw the idea instead of creating anything. Never stretch such an
idea into a slice to give it somewhere to go.

**`under` is a walk, not a tree.** Top-down, one node per line, from the nearest tier that
exists to the one node that does not:

```json
"under": [
  {"id": "PG-NN", "name": "Customers Get Answers Without Waiting For Support", "meta": "outcome · in execution", "status": "existing"},
  {"id": "new slice", "name": "unnamed — slice:create names it", "meta": "feature", "status": "new"},
  {"id": "expected PRD", "name": "receiving mail on a customer-controlled subdomain", "meta": "not authored", "status": "expected"}
]
```

- **Exactly one `new` node; every node above it is `existing`, with its real id and plain
  name** — with one exception: a slice that creates its area (`newArea`) walks
  `{"id": "area:<slug>", "name": "<newArea.name>", "meta": "feature area", "status": "new"}`, then
  the `new slice`, then any `expected` PRDs. The fleet refuses a `newArea` the walk does not show. For a **program** the walk is one line — `new program`, `meta: outcome` — and
  **no slices under it**: outcomes route to decompose, never to pieces you invent. For a **slice**, the existing
  program then `new slice`, with **`expected` PRDs** after it — each described in the filer's
  terms (*"receiving mail on a customer-controlled subdomain"*), never titled, never numbered.
  For a **PRD**, program → slice → `new PRD`, no children — and **the slice must exist**: a
  PRD whose home cut does not is a **`slice` proposal with that PRD as its `expected`
  child** (Step 2 already says an uncovered ground routes at the slice tier), never a walk
  with two `new` nodes. For a **task** or **bug**, the nearest existing thing — the feature
  area (which is also its tracker project) or the component — then `new task` / `new bug`.
- **`name` on the `new` node is `unnamed — <kind>:create names it`.** The create command
  takes the name from the idea's own title; you do not write one.
- **`meta` on the `new` node carries the one word the ladder already produced and nothing
  more**: `outcome` for a program; `feature` · `capability` · `gap-set` for a slice **when the
  dossier makes the shape plain** (*everything one customer needs* is a `gap-set`; *one
  capability lands on its own* is a `capability`), else empty and the create command writes
  `feature`. It is not a `Kind` you chose — it is the ladder's finding, and the person
  accepts the proposal with it in view.

**`onAccept.command` is exact**, because fleet runs it: `/fleet:program:create <issue key>` ·
`/fleet:slice:create <issue key>` · `/fleet:prd:create <issue key>` — and for a task or a
bug `/fleet:task:create <issue key>` · `/fleet:bug:create <issue key>`, which the service
performs itself by re-kinding the issue; name it anyway, so the page can show what happens.
`lands` says what appears where (*"an SL-NNN row in `slot:slices`, by PR"* · *"a numbered
stub with `status: stub`, by PR"* · *"the issue itself, re-kinded and sent to triage"*);
`next` is the person's first move on the new thing's page (*"refine the cut"* · *"decompose
it"* · *"run the PRD interview on the stub"*).

**The first gate, and it is hard — every `existing` home is open.** A program or slice named
`existing` in `under` is where the new thing goes, and one that takes no new work makes the
proposal one fleet will refuse the moment it lands. So, before emitting, for every `existing`
`PG-NN` and `SL-NNN` in the walk:

- **It is not under `## Closed to new work` in the brief.** Fleet lists there every program and
  slice the served board reads as `withdrawn` or `complete` — a derivation the checkout cannot
  make, so the list is the authority, not the register's prose.
- **With no such block in the brief** (a terminal run, or an older fleet), check it yourself:
  a withdrawn row's `Disposition` says `withdrawn`; a slice is complete when every PRD naming it
  in `slice:` is terminal *and* its proof has shipped; a program when every slice is.
- **A closed home is never stretched to fit.** A PRD whose slice is complete is new work there —
  propose a **`slice`** under the (open) program with the PRD as its `expected` child; a slice
  under a proven or withdrawn program goes under an open program, or is a **`program`** only
  when it passes every program test in the ladder (two slices or more) **and** the repository
  plans by program — in `areas` mode it is a slice under its area. Record
  the closed home you passed over in `alsoWeighed`, with its state as the `whyNot`.

**When no open program fits a one-deliverable request**, do not make it a program to give it a
home: a one-slice program fails the program tests. Propose the `slice` under the open program
whose result it most directly serves, say in `alsoWeighed` that the fit is weak and why, and let
the person who accepts send it back.

**The second gate, and it is hard — the size is argued, not asserted.** Before emitting:

- **`notOtherRungs` holds an entry for every smaller work rung.** For `program`: `bug`, `task`,
  `prd` and `slice`. For `slice`: `bug`, `task`, `prd`. For `prd`: `bug`, `task`. For `task`:
  `bug`. For `bug`: `task`. Each `why` is evidence from the dossier, not the rung's name restated.
  **If you cannot write the `why` for a smaller rung, the proposal is that smaller rung** — re-walk
  Step 3 and propose it.
- **A `program` carries `programTests`**, every sentence non-blank, `slices` at least two entries,
  and `noOpenHome` naming the open programs it considered (or saying there is none). A program
  proposal that fails any line becomes the `slice` (or smaller) the evidence supports.
- **No `program` at all when the repository plans by area.** If `planning_mode.py` printed
  `areas` and the walk landed on `program`, the proposal is the **first slice** of the work, under
  its area, with the other slices described in `alsoWeighed` — never a `kind: program` document.

**The fourth gate, and it is hard — a new area is argued, not assumed** (`newArea`, `areas` mode
only). Areas are the closed set every issue is filed against, so one more is a cost every
filer pays from then on. Before emitting a `newArea`:

- **Every existing area was read**, from `planning_mode.py --areas` and each map's Intent, and
  `whyNoExistingArea` names **the closest ones — at least one** — each with a `why` that is
  evidence (*"Sessions owns running an agent's work; nothing in it is about charging for
  it"*), never the area's name restated. **If you cannot write the `why` for an area, the slice
  goes under that area** — the same rule the second gate applies to sizes.
- **It is a durable product capability bucket that will keep receiving work**: a customer would
  name it when describing what the product does, and you can name at least two further
  capabilities it will hold after this slice. **Never for a one-off** — a single feature, a
  migration, a customer's punch list or a cleanup goes under the closest existing area, with
  the weak fit said in `alsoWeighed`.
- **The slug is free**: no existing area has it. The fleet refuses a taken slug, a comparison
  against an area that does not exist, and any `newArea` from a repository that plans by
  program, the moment the proposal lands.
- **`sentence` is durable** — what the area lets a person do, true for as long as the area
  exists. Never this slice's `Done when`, which the third gate forbids anyway.
- **`brief` and `uses` describe the area, not this slice** — plain words, no ship-state, no
  bare ids, the example a named person doing a real job (`example_from` names only journeys
  that exist; `[]` when none covers the area yet). The uses are what a person will do in the
  area — this slice's work sits under one of them, and the two further capabilities you named
  above sit under them too. If you cannot cut three uses, the area is not a bucket: it goes
  under the closest existing area.

**The third gate, and it is hard — the proposal places and names nothing** (except a **plan**,
which the person asked for by name: its slices carry their names, `delivers`, `doneWhen` and
pieces of work, per the feature-flow guidance — and nothing else in it is drafted):

- **No `Done when`.** Not in `under`, not in `whatItIs`, not in `next`. Quoting an
  *existing* cut's `Done when` to say which cut you mean is evidence; writing one for the
  new node is the authorship this command exists not to do.
- **No name for the new entity.** `unnamed — …` is the only value the `new` node's `name`
  takes. The one exception is a new feature area: its `name`, `sentence`, `brief` and `uses`
  are part of what the person accepts, so they are written in `newArea` — the slice under it
  stays unnamed.
- **No acceptance criterion, no drafted artifact** — no register row, no PRD prose, no
  requirement text. `expected` PRDs are described, not drafted.
- **Every id carries its plain name the first time it appears**, in `alreadyExists`,
  `ground` and `under` alike. A bare slice id is the failure Step 3's card was written
  against, and the page shows this document to the same person.
- **Every field present, none empty, none `TBD`**; `alsoWeighed` may be `[]` and says so.

A document that fails any line is not emitted — fix it and re-check.

### Step 7: Headless — the result file, then the done-sentinel

**One file, to the path in `$FLEET_RESULT_FILE`, once, whole.** Serialise the complete
object, write it in a single write, read it back and parse it — a half-written file is a
parse failure at the daemon, indistinguishable from a crash. Two kinds end this command:

```json
{"kind": "questions", "brief": "…", "questions": [ {"id": "q1", "prompt": "…", "allowFreeText": true, "options": [ … ]} ]}
```

```json
{
  "kind": "proposal",
  "proposal": {
    "kind": "slice",
    "whatItIs": "A new cut inside a program that already exists.",
    "test": "It spans at least two agent-shifts … and adds a completion condition neither proves alone.",
    "under": [ … ],
    "notOtherRungs": [{"rung": "bug", "why": "…"}, {"rung": "task", "why": "…"}, {"rung": "prd", "why": "…"}, {"rung": "program", "why": "…"}],
    "alreadyExists": ["The inbound channel is provider-generic by construction (CAP-NNNN)"],
    "ground": "No requirement register covers collaborative-messaging — the cut frames it.",
    "vision": {"aligned": true, "persona": "…", "value": "…", "differentiator": "…"},
    "alsoWeighed": [{"option": "A second cut of the existing slice (SL-NNN)", "whyNot": "…"}],
    "onAccept": {"command": "/fleet:slice:create <KEY>", "lands": "an SL-NNN row fragment under knowledge/slices/rows/, by PR", "next": "refine the cut on the slice's page"}
  }
}
```

****A slice that creates its feature area** (`areas` mode, no existing area fits) carries the walk
and `newArea` — the rest of the document is unchanged:

```json
{
  "kind": "proposal",
  "proposal": {
    "kind": "slice",
    "whatItIs": "A new feature area, Billing, with its first slice: a customer receives an invoice for last month's usage.",
    "under": [
      {"id": "area:billing", "name": "Billing", "meta": "feature area", "status": "new"},
      {"id": "new slice", "name": "unnamed — slice:create names it", "meta": "feature", "status": "new"},
      {"id": "expected PRD", "name": "the monthly invoice a customer receives", "meta": "not authored", "status": "expected"}
    ],
    "newArea": {
      "slug": "billing",
      "name": "Billing",
      "sentence": "A customer is charged for what they used and can see why each charge is there.",
      "whyNoExistingArea": [
        {"area": "sessions", "why": "Sessions owns running an agent's work; nothing in it is about charging for that work."},
        {"area": "accounts", "why": "Accounts owns who may sign in; prices, invoices and payment methods are a different job a customer names separately."}
      ],
      "components": ["usage-metering"],
      "brief": {
        "summary": "Billing is how a customer is charged for what their team used, and how they check each charge.",
        "problem": "Without it a customer gets a total they cannot explain, and disputes it. Every dispute costs a support call and some trust.",
        "example": "Dana runs finance at a small agency. At the start of the month she opens last month's invoice, sees each charge with the usage behind it, and downloads the invoice for her accountant.",
        "example_from": [],
        "not": ["Not who may sign in or what they may do; that is Accounts."]
      },
      "uses": [
        {"name": "Read an invoice", "paragraph": "See each charge on a month's invoice and the usage that produced it."},
        {"name": "Pay", "paragraph": "Keep a payment method on file and see which invoices are paid."},
        {"name": "Watch usage before it is billed", "paragraph": "See this month's usage so far, before it becomes an invoice."}
      ]
    },
    "…": "every other field, exactly as above"
  }
}
```

If `$FLEET_RESULT_FILE` is unset or empty in a run that reached this step, emit nothing —
nowhere — and say so in the sentinel.** Never a scratch path, never a tracker comment: nothing
in this loop reads either, and fleet would go on projecting the issue's moves from a file it
never received.

**An `entity` request writes the same proposal and stops there.** No service reads the files back
(a person is in the session), but the brief names both paths, so write the proposal to
`$FLEET_RESULT_FILE` and the done-sentinel to `$FLEET_AGENT_DONE_FILE` with `status: "success"` and
the result path in `summary`. Print the report, name the result path in your reply, and end the turn.

**Then check the set if the kind is `questions`, before the sentinel.** Run

```bash
python3 knowledge/scripts/validate_questions.py "$FLEET_RESULT_FILE"
```

It exits `0` when the set meets every rule the question table enforces — two to four options
(or none, for an open free-text question), at least one recommended, each option carrying an
`id`, a `label` and a `then` — and exits `1` naming the rule that broke. A set that breaks a
rule is refused by the service after the run is over, when this session is gone and can no
longer fix it; fix what it names, re-run it, then write the sentinel and stop.

**Exactly one result file per turn, and both kinds end the run.** A `questions` file does
not hold your seat — the daemon releases the claim the moment the sentinel exists, and the
interview resumes into this session on the item's next dispatch. Emit, pass the gate below,
write the sentinel, stop.

**The no-build gate**, because a headless run has nobody watching:

```bash
git status --porcelain && git branch --show-current && git stash list
```

A clean tree, the branch you started on, no stash. Anything else is work a routing session
did — revert it (`git checkout -- . && git clean -fd`), delete any branch, and say so in the
sentinel summary.

**Then the sentinel — the last thing you write.** Your dispatch mission names its path and
owns the exact keys; what a reader of this section alone would get wrong:

- **`status` is `"needs-decision"` for both endings.** A question round and a proposal each
  end with a person owing something — an answer, or the call to create. Neither is a failure
  and neither charges an attempt. `"partial"` only for a walk genuinely cut short that another
  attempt could finish; `"failed"` for not having been able to run at all.
- **`pr` is always an empty string.** Route opens no PR in either mode.
- **Result file first, read back, then the sentinel.** Which state the item lands in is
  decided by the file, not by that word — a `questions` file parks it on the filer, a
  `proposal` parks it on the person who routes.
- **Write it even when you wrote no result file** — the unset-path case above is exactly the
  one where the sentinel is the only signal anything happened.

> **The nudge you get for omitting it reads like an instruction to re-ask, and it is not.** If
> a result file is already written this turn, *continue* means write the sentinel and stop —
> never a second file, never the same question again.

---

## Rules

- **Route, never build — and the handoff is where that rule actually gets broken.** One command recommendation per item, with the reason, and **the arguments are the requester's own words plus your classification. Never a field the next command authors** — no `Done when`, no `Kind`, no `Name`, no acceptance criterion. A slice's `Done when` *is* a commitment, so a routing report that drafts one has authored a promise from a conversation that settled nothing. Measured: a route session emitted a complete `Done when` whose persona, review workflow and refusal rule came from an unrelated PRD's journey and had never been stated by the requester; `slice:create` read it as pinned-down input and skipped the interview that would have caught it. If you cannot hand off without writing the artifact, the answer is a shorter handoff, not a better draft. **Headless, the proposal document is that boundary** (Step 6's gate): no `Done when`, no name, no acceptance criterion, no drafted artifact — and the one word `meta` may carry on the `new` node is the ladder's own finding, accepted by a person with it in view, never a `Kind` you settled for them.
- **Headless: one written question at most, and never a second round.** The dossier already spent up to eight of the filer's questions; a ninth is yours only when two rungs genuinely fit, and a tenth does not exist. Ambiguity that survives the answer resolves to the smaller rung, named in `alsoWeighed`.
- **Headless: no tracker, no repo write, no PR.** The brief is everything you are given; the result file and the sentinel are everything you produce. A routing session that branched, committed or commented has left the contract, however correct the content.
- **Route reads in ids and asks in plain words.** Every register this command opens is
  id-dense (`PG-NN`, `SL-NNN`, `CAP-NNNN`), which makes carrying that register straight
  into the interview the failure this command is most prone to — an option labelled
  *"decompose "* is unanswerable by the one person entitled to answer it. Ids belong
  in the **report**, as evidence; the **question** names the thing in words — the
  interview card's item 4, inlined at Step 3.
- **Never skip the vision check**; an unaligned request is flagged, not silently routed.
- **A program is the last rung, not the label for something that sounds big.** It needs every
  program test, the two-slice count and *no existing open home* among them, and its proposal
  argues each smaller rung away in writing. One deliverable is a slice; a defect is a bug however
  large the fix. **In a repository that plans by area it is not a rung at all** — work bigger than
  one slice is several slices.
- **Outcomes route to decompose, not to pieces you invent — slices included** — hand-routing an
  outcome's pieces is how requirements get missed (measured: ~5% recall vs a real
  decomposition).
- **A decision or a requirement is named, never sized** — and never authored here. Say
  which register/record it belongs to, say whether any PRD claims it, and route the *work*
  that would satisfy it as its own ladder walk. **Never write a `## Decision (<date>)`
  section into an issue description** — that heading is reserved for a human's answer to a
  question the fleet stopped on, so an agent's own record goes under
  `## Implementation notes (<date>)` ([`decision-write-back.md`](../../process/decision-write-back.md)).
- **Mixed lists get split** — classify each item; don't force one route onto three kinds.
- **Ambiguous size → one question**, shaped by the interview card (Step 3), then route.
- **Be concise.** 30 seconds to read, not 5 minutes.
