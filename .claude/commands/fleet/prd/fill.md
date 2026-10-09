#  PRD — Fill (a stub becomes a drafted PRD, on the fleet)

You turn a **PRD stub** — a number, a home in a slice, and the idea's brief under `## Brief`,
written by the fleet at `status: stub` with nothing else authored — into a drafted PRD: the
vision check, the slice confirmed, `implements:` claiming its requirement rows, the journey
agreed and written, `## In Plain Words`, the requirements, the acceptance criteria with their
disposition tags, the `## Scope ledger`, a `priority:`, and `status: prd-drafted`. That is
what [`prd:create`](create.md) Phases 0–5 produce with a person at a terminal on
`/fleet:prd:create NNNN`, and **this command is that interview, run headless**: the same
dimensions, asked by writing through the fleet's question channel, answered on the PRD's own
page, and landed as one merged PR. This command never designs: the design is
[`prd:blueprint`](blueprint.md)'s on the fleet once the PRD's prerequisites ship, or
`/fleet:prd:design NNNN` at a terminal, and plan stays attended.

**You are a composition, not an authority.** Every rule about what a PRD is, what it must
carry, how its scope is disciplined and what the template looks like lives in `create.md`,
and this file cites it rather than restating it: the vision check is *Phase 0*, the
placement is *Phase 0.5*, the claim is *Phase 0.6*, the journey is *Phase 0.7*, the framing
and the dimensions are *Phase 1* and *Phase 2*, the scope offer is *Phase 3*, the template
and the ledger are *Phase 4*, the capability trace is *Phase 5*, the stub's shape is
*Phase 6*. Its CRITICAL RULES bind this run in full — the necessity test, the journey before
requirements, requirements not solutions. What this file owns is the **mapping**: which of
its questions become cards in which of the three rounds, which the run decides and reports,
and which are withheld.

**Headless only.** A person at a terminal runs `prd:create` on the stub's number, which
keeps the number and fills the file in place; the fleet routes a mission by command string
and cannot tell that verb on a number from the same verb on a brief, so this one exists for
the button and nothing else (Step 0).

The PRD to fill: $ARGUMENTS

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps`
> block below and create **one todo per step**, in order; mark each `in_progress` on entry and
> `completed` on exit. The interview step is a bounded loop — add one todo per round under it.
> The one `status:` this command writes is the PRD's own — the only authored status in the
> model — and the spine says so with `produces: ["prd", "status"]`; nothing above the PRD is
> touched. The prose steps below are the authority; this spine indexes them.
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
  "command": "prd-fill",
  "tier": "core",
  "sop": "none",
  "needs": "answers",
  "may merge": true,
  "intent": "Fill a PRD stub on the fleet: the job story, the highest-impact dimensions and the scope offer through the fleet's written question channel over at most three rounds, then write the PRD exactly as prd:create Phase 4 would at a terminal — status prd-drafted, its journey, its claims, its ledger — by one merged PR and one landed result; it never designs, and plan stays attended.",
  "loads": ["process-shaping-headless", "product-vision", "planning-model"],
  "requires": [
    "process-spine", "process-interview", "process-shaping-headless", "commitments",
    "rubric-issue-priority", "product-vision", "planning-model", "file-conventions", "slices",
    "gate", "git-workflow", "feature-areas", "journeys"
  ],
  "optional": ["domain-model", "resilience", "entity-model", "feature-maps", "ui-contracts", "components", "programs", "docs"],
  "steps": [
    {"id": "mode",       "name": "Which way in — the fleet, or a terminal (refused)",             "kind": "decision", "actor": "coordinator",                 "body": "step-0-which-way-in"},
    {"id": "read",       "name": "Read the stub, its home, its ground and the vision",             "kind": "io",       "actor": "coordinator", "consumes": ["prd", "requirement-register"], "body": "step-1-read-the-stub"},
    {"id": "refusals",   "name": "The refusals — by sentinel, before any question",               "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "step-2-the-refusals"},
    {"id": "rounds",     "name": "The rounds — the job story, the dimensions, the scope offer",   "kind": "loop",     "actor": "coordinator", "loop": {"max_rounds": 3, "exit": "the person answered the scope offer (or nothing was withheld and the dimensions are settled), or the ceiling was reached and what stands is written with its open items"}, "body": "step-3-the-rounds"},
    {"id": "author",     "name": "Write it — the journey, the PRD, the claims, the ledger, the trace", "kind": "author", "actor": "coordinator", "produces": ["prd", "status", "journey", "feature-map", "requirement-register"], "body": "step-4-write-it"},
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

- **Set** → the fleet dispatched you on a stub the page asked to have filled. `$ARGUMENTS`
  is its number (`NNNN`), the mission's `## Shaping` block carries the requester, any
  instruction and the stub's row as served, and the payload says which round this is —
  *The headless contract* §1. Run Steps 1–6.
- **Unset** → a person is at a terminal, and this is the wrong verb for them. Say exactly
  this and stop, writing nothing: **This command runs only on the fleet. At a terminal, run
  `/fleet:prd:create NNNN` instead** — it is the same interview with you in the room, on the
  same stub, keeping the same number.
  **And say that the terminal is not a one-way door.** A person who starts by hand and
  would rather the fleet finished it presses **Shape this** on the entity's own page (the
  `start` action — the same button that would have dispatched this command), and the next
  round picks up from whatever is committed: the register row, the detail file, the answers
  already written down. Being sent to a terminal must never read as being sent there *for
  good*.
- **Set, but `$ARGUMENTS` is not a PRD number, or the block's `kind` is not `prd`** → a
  mis-dispatch. Write nothing; sentinel `failed` naming what was wrong; stop.

### Step 1: Read the stub

Everything the repository can answer is answered here, before any question:

1. **The stub** — `create.md` Phase 6 says what it carries and nothing more: the frontmatter
   (`prd:`, `title:`, `status: stub`, its one `status_history` line, `slice:`, `date:`,
   `author:`), and `## Brief` with the dossier's nine fields in the filer's own words. The
   brief is the interview that already happened; read it as evidence, never as a proposal.
2. **The home** — the slice the stub names, in `slot:slices`, and its program: `Done when`,
   `Kind`, the member PRDs and their `status:`, whether the slice carries a `## Bar`. Phase
   0.5's placement is **decided** here: the stub's `slice:` stands unless a second open
   slice's `Done when` plausibly covers the work too — then, and only then, Round 1 asks.
3. **The vision** (`slot:product-vision`) and the differentiators — Phase 0's alignment
   check, **decided by the run** and written into the PRD; a stub that serves no persona and
   no core-loop step is a refusal in Step 2, because *"does this belong"* is not a fork.
4. **The claim** — Phase 0.6: the register(s) for this ground through the component index
   `slot:commitments` gives; the rows this PRD would realise, their `Disposition` read
   before claiming; a row another PRD already claims noted as an overlap. A register the
   ground lacks is opened with the rows this PRD needs, born `open`, exactly as Phase 0.6
   item 1 says — and `open` reports that the cut skipped its framing.
5. **The parked ideas** — Phase 0.5 item 5, **decided** (*fold* / *spin* / *leave*) from
   `search_issues` over this ground (`include_closed: false`, keep kind `idea`) when Fleet
   tools are present, and reported in the PRD's source trace; without the tools, stop with:
   *this command needs the Fleet tools; create a personal key on Fleet's API keys page* —
   never fall back to a tracker script; if the tools are present but the search fails, the
   PRD says the ground was not surveyed. **No tracker write** in either case — the ideas are
   neither closed nor folded by this run; `open` names the ones a person should fold or close.
6. **The best-practice baseline** — Phase 1 Step 0-pre, **decided**: how best-in-class
   products solve this, written as the one-paragraph baseline the PRD's scope adopts by
   default. The seat carries no browser, so the baseline is what the run can establish from
   the repository, the vision and its own knowledge, and it says so in one clause.
7. **No mockups.** Phase 1 Step 0's browser-rendered mockups need a browser the seat does
   not have, and a PRD-stage mockup is throwaway framing in any case. Visual questions are
   asked text-shaped here, and `## Next Steps` hands the visual pass to `prd:design`, which
   owns it.
8. **The dimensions, drafted.** Phase 1 Step 1's framing — the understanding, the two
   hypotheses, the assumptions, the 3–6 dimensions — drafted from the brief and the vision,
   with each dimension marked *settled by the brief* / *settled by the vision* / *open*.
   Only the open ones can become cards.

### Step 2: The refusals

By sentinel, before any question, in the form *The headless contract* §9 gives:

- **No PRD folder for the number** → `failed`, a mis-dispatch.
- **`status:` is not `stub`** → `failed`: this command fills stubs; a drafted PRD is
  `prd:design`'s, and a terminal one is nobody's to reopen.
- **The stub's `slice:` resolves to nothing, or to a slice that reads complete** →
  `needs-decision`: *"send it back naming a live slice, or cut one from the program's
  page"* — Phase 0.5's gate, refused by sentinel because nobody is there to ask.
- **The vision gate fails** (Step 1.3) → `needs-decision` with the alignment check written
  out in the summary, in plain words, and the move: *"say which persona and which step of the
  core loop this serves and try again, or cancel it"*.

### Step 3: The rounds

Three rounds at most, at most four questions each, every one shaped by the rail in *The
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

6. **The person may not be the one who knows — every question can be answered *"I can't
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

Each round's brief opens with which round this is of up to three, restates the brief's
problem in the filer's own words, and says what this round settles.

**The aspect each card changes** (*The headless contract* §3): *Which slice* → `slice`, *The
job story* → `jobStory`, *The trigger* → `trigger`, a Round 2 dimension → whichever of
`criteria`, `scope` or `whoFor` it rewrites, and each scope-offer card → `scope`. From Round 2
on, the `draft` carries `criteria` (the acceptance criteria a person reads, one line each) and
`decisions` (every dimension decided unasked, with its one-line rationale). Round 3 is marked
`"confirm": true`; when it is skipped, the fill writes after Round 2 as before. Every option says what
changes for a real person, never what changes in the code — `create.md` CRITICAL RULE 5
binds the cards as it binds the PRD.

#### Round 1 — the job story (`create.md` Phase 0.5 and Phase 0.7)

| Card | What it establishes | Options |
|---|---|---|
| **Which slice** — *only when Step 1.2 found two that fit* | the cut this PRD lands in, and so the program it rolls up to | the candidate slices, each named by what it delivers in plain words with its id in parentheses, the stub's own recommended |
| **The job story** | *When [situation], I want to [motivation], so I can [outcome]* — one persona, one scenario, solution-free, from the real starting trigger | the run's draft (recommended) and two alternatives that read the brief differently; free text |
| **The trigger** — *only when the brief leaves it unclear* | the real starting event, never a mid-stream system task | 2–4 candidate triggers drawn from *what they do today*, one recommended; free text |

Then STOP: write the `questions` result, the sentinel `needs-decision`, end the turn.

#### Round 2 — the dimensions (`create.md` Phase 1 Step 6 and Phase 2)

On resume, consume Round 1 (*The headless contract* §4), lay the journey's backbone the way
Phase 0.7 items 2–5 say — trigger to outcome, happy path, every step to a surface, the
branch points marked, the walking skeleton found — **decided by the run** from the agreed job
story, and then ask **the four highest-impact dimensions still open** from Phase 2's list,
most-blocking first, one card each in Phase 1 Step 6's shape: 2–4 options, one recommended
with its rationale, a rationale on every other. Every dimension not asked is **decided from
the brief, the journey and the vision**, and the decision is written into the PRD section it
settles — the scope, the requirements, the resilience block — with its one-line rationale, so
a returning reader sees what was chosen and why; never silently. Phase 2's item 13, the
failure domain, is decided and recorded in the resilience block (*N/A — Tier 1 leaf* when it
is) rather than asked.

Then STOP, as before.

#### Round 3 — the scope offer (`create.md` Phase 3, Rule 4b)

On resume, consume Round 2 and run the **necessity test** over the surviving scope, the
inherited requirements included (Rule 4c): what breaks without it, how often it fires;
anything answering neither is deferred by id and the line is reported. Then the offer, in
the one shape the wire allows: **one two-option card per withheld item**, at most four — the
four with the strongest case when the list is longer, the rest recorded `withheld` unoffered —
each naming what it adds and what it costs (another screen, another entity, a bigger
envelope at design), with **leave it out** marked recommended. Phase 3 says *mark no
recommendation*; the written channel requires exactly one marked and has no multi-select,
and the withholding is the recommendation, so *leave it out* carries the mark and the ledger
records that it did. **Zero withheld items → this round is skipped**, the ledger says so in
one line, and the run goes straight to Step 4.

**The brief of this round is the draft**: the final decisions in Phase 3's form — problem,
customer value, differentiation, scope, personas — in at most eight lines, so the answer to
the offer is also the confirmation of what will be written. Nothing is written before it.

**At the ceiling — three rounds asked, or an answer missing — write what stands** (Step 4)
and put every unsettled item into `landed.open` verbatim. An unanswered offer card leaves
its item `withheld`; an unanswered dimension is decided from the brief and named in `open`
as decided without an answer.

### Step 4: Write it

Only after Round 3's answer, or after Round 2's when nothing was withheld, or at the
ceiling. Everything here is authored **exactly as `create.md` says**, cited, never restated:

1. **The journey** — Phase 0.7 item 7: the flow or map file refreshed in place or added for a
   genuinely new job, per the catalog's own template and README; the screen inventory named,
   each surface marked to author or refresh at design.
2. **The PRD** — Phase 4, on the stub's own number and folder: the frontmatter widened to the
   full set, `status: prd-drafted`, the `status_history` line appended as
   `{ state: prd-drafted, at: <the timestamp, in the form the stub's own line uses>, by: fleet:prd:fill }` beneath the stub's
   own entry — never a second `stub` entry, never a second number; `slice:` as confirmed;
   `priority:` from the vision check, deliberately, never the fallback; `implements:` from
   Step 1.4; `## Brief` kept above `## In Plain Words` as the record the interview started
   from; then the template's required sections in Phase 4's order — `## In Plain Words`
   first, the vision alignment, the source trace, the value justification, the resilience
   block, the scope, the requirements, the acceptance criteria each with a disposition tag
   and a citation on every AC that realises a claimed row, the **`docs_impact`** block
   (`create.md` Phase 0.7 — pages created or changed, each named by page id via `slot:docs`,
   with its audience, page kind and verifying journey; `none` for an internal capability,
   never for a customer-facing one without a reason on the record), `## Open questions` for
   what the rounds left open, `## Scope ledger`, `## Next Steps` naming
   `/fleet:prd:design NNNN`. One proof substrate per PRD: a record-closed criterion the ask
   needs is a second, proof PRD's — say so in `open` rather than mixing it in.
3. **The promotions** — an AC observable only against a real environment is promoted into
   the slice's `## Bar` as Phase 4 says, **when the slice carries a bar** (a PRD may add rows
   to one, never loosen it). When it carries none, that criterion is **not written as an
   AC**: a bare `[ext]` is refused at the commit, and a bar written by this run to have
   somewhere to point would be a bar nobody ratified. It goes under `## Open questions` as
   the observation the slice's bar must carry, and `open` says the slice needs its bar
   first — `slice:refine` writes one from the slice's page, and `prd:design` promotes the
   criterion once it exists.
4. **The claims** — Phase 0.6 items 4–5 and Phase 4's two rules: every claimed row cited by
   at least one AC in the citation form; the body cites ids and never restates a row's text;
   a new assertion is a new row with its `Needs` edges, id from
   `python3 knowledge/scripts/validate_id_collisions.py --allocate <PREFIX> <n>`, which
   reserves it as a claim ref — there is no counter to bump.
5. **The ledger** — `## Scope ledger`, mandatory, three dispositions: *admitted* (with its
   basis — a round, a journey step), *withheld* (offered in Round 3 and declined, or beyond
   the four), and `none — <what was considered>` when nothing was added. Rows are additions,
   never decisions.
6. **The trace** — Phase 5: the feature map's row for this capability — the gap row a
   decomposition left flipped from `—` to this number, never a duplicate; a new row with a
   `CAP` id from the allocator when none exists; `Tested by` pointing at the journey.
   Nothing appended to the slice; nothing written to the roadmap, which is generated.
7. **Withheld, and reported in `open`** — the idea issues to close or relabel (Phase 5's
   *Source idea*), any mockup the design owes, the proof PRD a mixed substrate needs, the
   bar a promoted AC is waiting on. **No tracker write**: the projection reads the merged
   PRD and creates the issue itself.

Then `make validate-knowledge` clean — the scope-ledger, the claim-cites and the
placement rules are all in it.

### Step 5: Land it

*The headless contract* §6, unchanged: the prior attempt found with `gh pr list --search`,
the deterministic branch `agent/shape-<key>`, **the PR's identity** (shaping content only; the tracker key in the title
when the entity has one — what the `Verify Gate` reads), every allocated id re-checked against the tip
at push, `gh pr merge --auto --squash` armed the moment the PR opens, and
the PR driven to `state: MERGED` (`queued` is pending, `ejected` from the merge queue is red CI — the contract's `gh_pr_merge_state.py` watch) — a generated-ledger conflict taken one side wholesale with
its generator re-run.

Once merged, the `landed` document to `$FLEET_RESULT_FILE`, written whole and read back —
§7's shape with a PRD's `changed`:

```json
{"kind": "landed", "landed": {"kind": "prd", "id": "NNNN", "href": "prd:NNNN", "pr": "<the merged PR's URL>", "files": ["<every path the PR changed>"], "summary": "<one plain sentence: what the PRD now promises>", "changed": {"status": "prd-drafted", "slice": "SL-NNN", "implements": ["<each claimed row id>"], "acs": 0}, "open": ["<each unsettled or withheld item>"]}}
```

`status` is the frontmatter as written; `slice` the home as confirmed; `implements` the
claim; `acs` the count of acceptance criteria written. Then the sentinel: `success` with the
PR URL. A PR that could not be brought to merge in this run is `partial` with the PR URL and
**no `landed` file**, so the next dispatch resumes the branch — §8's table, and never
`done`.

### Step 6: Report

Nine lines, for a human reading the transcript: the number and its slice; the rounds asked
and questions spent (`n of 12 across r rounds`); the job story as agreed; the dimensions
asked and the dimensions decided; the necessity-test line (*N requirements, M deferred —
ids*); the offer's outcome (*k offered, j admitted*, or *nothing withheld*); what was
withheld; the PR and its state; the result written and the sentinel word.

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

- **An `Unconfirmed assumptions` section in the stub is a list of claims, not facts.** Keep the
  section in the PRD you author — each line still marked unconfirmed — and put each one that a
  criterion would turn on to the person who can answer it, in a round of its own. Whatever the
  owner marks *"I can't answer this"* again is carried the same way (the one rule:
  [`interview-protocol`](../../../process/interview.md) → *"I can't answer this"*).
- **Cite, never restate.** The vision check, the placement, the claim, the journey, the
  dimensions, the offer, the template, the ledger and the trace are `create.md`'s Phases 0–5;
  the stub is its Phase 6. This file maps its questions onto three rounds; it owns none of
  its rules, and every CRITICAL RULE of `create.md` binds this run.
- **A customer-facing capability carries a `docs_impact`; a `none` carries a reason.** Seed it
  from the coverage rule `slot:docs` names, as `create.md` Phase 0.7 says. When the repo leaves
  the slot unfilled, write `docs_impact: unknown` and say the slot's degrade — never invent a
  docs home.
- **The PRD's `status:` is the one authored status in the model, and `prd-drafted` is the
  only value this command writes** — on the stub's own number, with its history appended,
  never a second entry and never a second number. Nothing above the PRD carries a status,
  and nothing here touches the slice or the program.
- **Journey before requirements, requirements not solutions, one persona × one scenario.**
  Round 1 agrees the job; the backbone is derived from it; every requirement and AC traces to
  a step and its surface.
- **The run decides what the brief, the journey and the vision already settle, and writes
  each decision into the section it settles with its rationale.** It asks only the
  dimensions that are genuinely open, at most four, and never one a file answers.
- **The offer is two-option cards with *leave it out* recommended**, at most four, and the
  ledger records every disposition — admitted, withheld, offered-and-declined. Zero withheld
  is the expected outcome for a well-scoped ask, not a skipped step.
- **No tracker write, no mockup, no `AskUserQuestion`.** Ideas to close, the visual pass and
  a proof PRD are reported in `open`; the projection creates the issue from the merged PRD.
- **This command never designs, and plan stays attended.** The landing names
  `/fleet:prd:design NNNN` as the next step; on the fleet, [`prd:blueprint`](blueprint.md)
  designs the PRD once its prerequisites ship, and this command never runs either.
- **Headless only.** A terminal is refused in one sentence naming `prd:create`.
