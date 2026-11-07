# <!-- home -->Zetify<!-- /home --> Route — classify and route

You are the **single entry point for anything the user wants built**. Given "I need
a b c", you orient it against the product vision, place it in the planning model, and
route it to the right pipeline command — program, slice, PRD, component, task, bug,
idea, page improvement, or connector. You never build here; you decide **what kind of
thing it is** and hand off.

**You do NOT write code, PRDs, designs, or plans.** Route and recommend.

> For a pure question or research — <!-- home -->[`/zetify:ask`](ask.md)<!-- /home -->, the read-only front door.
> `build` is for things the user intends to build (or park as an idea).

**Two ways in, told apart by one variable.** At a terminal, `$ARGUMENTS` is a person's
request and the ending is a printed report (Step 4). **When `$FLEET_RESULT_FILE` is set** you
are on the fleet with nobody at a terminal: `$ARGUMENTS` is the issue key naming this work,
the brief carries the **dossier** [`/zetify:intake`](intake.md) wrote, and the ending is a
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
Component  (durable subsystem — never ships)      <!-- home -->/zetify:component:create<!-- /home --> → the `slot:components` registry
Capability / Outcome  (durable, ledger rows)      authored into the `slot:feature-maps` ledger for its area
Theme      (a lens across programs — a word)      prose only: NEVER a tier, a row, or a cell
Decision   (a fork we took + the branch refused)  the `slot:decisions` home · or a PRD's design.md
Requirement("the system shall / never")           a row in the `slot:commitments` register for its domain
PROGRAM    (a result someone GETS — kind: outcome  /zetify:program:create → /zetify:program:decompose
            — or a body of work that LANDS —       ...then recurring: /zetify:program:deliver
            kind: program, which MUST name a       a row fragment in the `slot:programs` register
            Verified by proof on a customer surface)
  └─ Slice (a planning cut that completes —        /zetify:slice:create
            kind: feature | capability | gap-set,   a row fragment in the `slot:slices` register
            one "Done when", no dates, a ceiling)
       └─ PRD (one agent-shift, with UX)          /zetify:prd:create → design → plan → implement → verify → push
Task / Bug / Idea  (tracker-native, no repo file)  /zetify:task:create|implement · /zetify:bug:fix · /zetify:idea:create
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
local homes, never the ladder.<!-- home --> The full model, with its history and the measurements
behind each rule, is [`knowledge-model.md`](../../../knowledge/specs/knowledge-model.md); where it
and the inlined ladder disagree about a size, raise it rather than pick one silently.<!-- /home -->
Do not reconstruct either from this diagram.

**Every new slice names its feature area**<!-- home --> (decision 2026-10-27, amended 2026-10-28, `FLT-1280`)<!-- /home -->:
`python3 knowledge/scripts/planning_mode.py --areas` lists them; propose the area whose feature map owns
the work, say which and why, and in a headless proposal put it in `under` as an `existing` node with id
`area:<slug>`. **The `existing` area must be one `--areas` lists in THIS checkout's repository** — the one the briefing's "About the … repository" line names. A feature map you find under another repository's tree (a submodule, a sibling clone) is not a home the accept can write to: "Create it" writes into the filing's own repository, and the fleet refuses a slice under a feature that repository does not hold. If the work belongs to another repository, still say so — in `whatItIs`, and in `alsoWeighed` as *"belongs in repository X; the filing needs to be moved"* — and the person withdraws the idea and files it against that repository. **Whether it ALSO joins a program depends on the planning mode** —
`python3 knowledge/scripts/planning_mode.py` prints `programs` or `areas` (`.fleet/fleet.toml`
`[fleet.planning] mode`; absent means `programs`):

- **`programs`** — as before: the slice is also placed under the program it serves.
- **`areas`** — no program, existing or new. **Never propose an existing program as the home for new work** in
  this mode — programs take no new slices and drain on their own<!-- home --> (`FLT-1282`)<!-- /home -->. **And never
  propose a new program**: in this mode "program" is not a rung of the ladder at all<!-- home --> (owner, 2026-10-28,
  `FLT-1285`)<!-- /home -->. Work bigger than one slice is **several slices** — in one area, or across areas — ordered by
  each slice's `Depends on` and each PRD's `depends_on`; propose the first slice and describe the others in
  `alsoWeighed`. The shared ladder's section *In a repository that plans by area, "program" is not a rung* has the
  rule and a worked example. A `kind: program` proposal from a repository in this mode is refused by the fleet the
  moment it lands, so it never reaches a person.
- **`areas`, and no existing area fits** — propose the slice **together with a new feature area**: `kind: slice`
  with the additive `newArea` field (Step 6), argued against the closest existing areas the way `notOtherRungs`
  argues the size<!-- home --> (owner, 2026-10-28, `FLT-1292`)<!-- /home -->. The bar is high: a new area only for a
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

<!-- home -->`knowledge/strategy/product-vision.md`<!-- else -->`slot:product-vision`<!-- /home -->, then render the roadmap index with
`python3 knowledge/scripts/gen_roadmap.py` and read <!-- home -->`knowledge/roadmap.md`<!-- else -->the roadmap it prints<!-- /home --> (generated on demand,
not committed — so it is never stale).
For anything program-shaped, also `python3 knowledge/scripts/gen_program_plan.py --list` — the program
ids (`PG-NN`) that already exist and whether they're decomposed; a single plan is
`gen_program_plan.py PG-NN`.

### Step 2: Scan for what already exists

- Planning tiers: the two registers — <!-- home -->`knowledge/programs.md`<!-- else -->`slot:programs`<!-- /home --> (`PG-NN` rows) and
  <!-- home -->`knowledge/slices.md`<!-- else -->`slot:slices`<!-- /home --> (`SL-NNN` rows), each row a fragment under `rows/` — one row per
  entity, so this is two directories to read, not fifty. **Count the active slices** (any whose member PRDs — the ones naming it in
  `slice:` — include a non-terminal one, or are all terminal but unproven).
  At the ceiling, nothing new gets cut; that changes what you can honestly route.
- The capability ledger: the relevant `knowledge/features/<area>.md` — does the request
  map to an already-named capability, and what does its `Ships in` say?
- The component registry (<!-- home -->`knowledge/specs/architecture/components.md`<!-- else -->`slot:components`<!-- /home -->) when the
  request sounds like a subsystem
- The requirement registers (<!-- home -->`knowledge/requirements/*.md`<!-- else -->`slot:commitments`<!-- /home -->) — does this work realise
  commitments already written down? **Carry the matching IDs into the handoff**: they
  become the PRD's `implements:`, and a requirement no PRD claims is the backlog.
  Resolve the ground through the `## Component index` table in
  <!-- home -->[`requirement-status.md`](../../../knowledge/requirement-status.md)<!-- else -->`slot:commitments`<!-- /home --> — the generated
  component→register join, rendered on demand and never committed, so run `python3 knowledge/scripts/gen_requirement_status.py` first — **never by guessing a filename from the request's wording**.
  **An unregistered ground is a routing signal, not a gap to note and move past.** If no
  register covers what the request touches, the product has never written down what this
  area promises, and framing that is [`slice:create`](<!-- home -->slice/create.md<!-- else -->#<!-- /home -->) Step 3 — which is
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

**Headless, that one question is written, not asked** — a `questions` result document
(Step 5) whose every option is built to the card above, and whose park and resume the fleet
owns. The card's *Headless* line is the rule: the same words, into the document.

**The ladder — shared, the same in every repository:**

<!-- include: process/planning-ladder.md -->

**In a repository that plans by area, the feature flows bind every headless walk**: a dossier
carrying `placement` is placed exactly there, a new feature is proposed as its map only, a new
use as that one use, and a
plan is one to three named slices with their pieces of work. The shapes and the one exception
to the third gate (a plan names its slices and writes their `Done when`) are in the shared
guidance:

<!-- include: process/feature-flow.md -->

The two state questions route straight away: **broken** → `/zetify:bug:fix` (or `bug:create` to
just file it); **early or exploratory** → `/zetify:idea:create` (parks the tracker `Type:idea`
issue).

**A docs request is classified through `slot:docs` before the ladder, and it has two
shapes.** *A page is missing or wrong for a capability that already ships* is a **defect** —
route it to `/zetify:bug:fix` (or `bug:create`) to correct the page where the docs live; it is
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
| **component** | <!-- home -->`/zetify:component:create`<!-- else -->a component registration (`slot:components`)<!-- /home --> (a label; it never becomes a slice) |
| **capability** / **outcome** | a ledger row in the area's feature map (`slot:feature-maps`) — never a folder. An outcome earns **slices** while being built. |
| **feature area** | a feature map (`slot:feature-maps`) — **and note that it is also the tracker project** (`slot:feature-areas`) any task/bug/finding on this ground gets filed into |
| **theme** | **nothing gets written.** Say it in prose where it helps a reader; there is no theme row, folder or cell to file it in, and a theme is never a new program. |
| **decision** — *can you name the option we rejected?* | a dated, append-only record where `slot:decisions` says, from its template, or the owning PRD's `design.md`. **Not work — never sized.** |
| **requirement** — *can you write it as "the system shall / never", and observe a violation?* | one numbered row in the domain's register (`slot:commitments`). **Not work — never sized.** |
| **task** | `/zetify:task:create` or `task:implement` |
| **PRD** | `/zetify:prd:create` (Phase 0.5 places it in a slice) |
| **slice** | `/zetify:slice:create` (named for what ships, with a `kind:` and a "Done when" — no dates, and refused past `slot:slices`) |
| **program** | `/zetify:program:create` → `/zetify:program:decompose` — **only when every program test passes**, the fifth included: no existing open home fits and the work holds at least two slices. **Do not route its pieces yourself** — that is the decomposition's job, with better evidence. **Never in a repository that plans by area** (`planning_mode.py` prints `areas`): there the work is several slices, and route proposes the first one — both program commands refuse in that mode. |
| **a program already in execution** | `/zetify:program:deliver` — one cycle: release dispatch-ready work, triage, escalate. Recur it via `/loop` or a schedule. |
| **a program whose work is all done** | `/zetify:program:ship` — gates on proof and lands the closing record as a merged PR. There is no status to flip; it refuses to certify if the proof does not hold. |

**The last two are the constraint axis, and route names them without authoring them.**
Neither is on the ladder and neither is work, so there is no pipeline command to hand
them to — which is exactly why they get mis-routed into a PRD or vanish. Route owes them
two things instead:

1. **Name it**, so a *"the system shall never …"* is not handed to a build pipeline that
   then builds the wrong thing.
2. **Ask who claims it.** A requirement's status is derived from PRDs' `implements:`, so
   *no claiming PRD* is the backlog signal, not an absence of information. If the user
   wants it built now, **walk the ladder again on the work that would satisfy it** — that
   lands normally (usually a PRD) and carries the requirement ID into `/zetify:prd:create`,
   which sets `implements:` and cites it from an acceptance criterion.

The row or record itself is authored **where the commitment was settled** — the decision
record, the PRD's design, the audit finding, the corpus-extraction pass — because a row's
`Source` is load-bearing and a routing conversation settles nothing. A *"shall"* with no
source is not a requirement yet; it is an unsettled fork, and that is an interview
([`interview-protocol.md`](../../process/interview.md)), not a
hand-off.

Then the non-tier routes: small scoped change → `/zetify:task:create` or `task:implement`;
UX change to an existing page → <!-- home -->`/zetify:page:improve`<!-- else -->a page-improvement task<!-- /home -->; connector work → <!-- home -->`/zetify:connector:build`<!-- else -->a connector task<!-- /home -->.

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

**Recommended next step:** /zetify:<command> — <the requester's own words, verbatim>
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
triage queue, where [`/zetify:check`](check.md) is the one gate with a *close* verdict, and
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

**`onAccept.command` is exact**, because fleet runs it: `/zetify:program:create <issue key>` ·
`/zetify:slice:create <issue key>` · `/zetify:prd:create <issue key>` — and for a task or a
bug `/zetify:task:create <issue key>` · `/zetify:bug:create <issue key>`, which the service
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
    "onAccept": {"command": "/zetify:slice:create <KEY>", "lands": "an SL-NNN row fragment under knowledge/slices/rows/, by PR", "next": "refine the cut on the slice's page"}
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
  *"decompose <!-- home -->PG-14<!-- /home -->"* is unanswerable by the one person entitled to answer it. Ids belong
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
  `## Implementation notes (<date>)` ([`decision-write-back.md`](../../process/decision-write-back.md), <!-- home -->ENG-10710<!-- /home -->).
- **Mixed lists get split** — classify each item; don't force one route onto three kinds.
- **Ambiguous size → one question**, shaped by the interview card (Step 3), then route.
- **Be concise.** 30 seconds to read, not 5 minutes.
