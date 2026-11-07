# <!-- home -->Zetify<!-- /home --> PRD — Fill (a stub becomes a drafted PRD, on the fleet)

You turn a **PRD stub** — a number, a home in a slice, and the idea's brief under `## Brief`,
written by the fleet at `status: stub` with nothing else authored — into a drafted PRD: the
vision check, the slice confirmed, `implements:` claiming its requirement rows, the journey
agreed and written, `## In Plain Words`, the requirements, the acceptance criteria with their
disposition tags, the `## Scope ledger`, a `priority:`, and `status: prd-drafted`. That is
what [`prd:create`](create.md) Phases 0–5 produce with a person at a terminal on
`/zetify:prd:create NNNN`, and **this command is that interview, run headless**: the same
dimensions, asked by writing through the fleet's question channel, answered on the PRD's own
page, and landed as one merged PR. This command never designs: the design is
[`prd:blueprint`](blueprint.md)'s on the fleet once the PRD's prerequisites ship, or
`/zetify:prd:design NNNN` at a terminal, and plan stays attended.

**Before you write a PRD or journey file, read its docs page** (under `.fleet/docs/`; `read_doc <page>` when Fleet's tools are in the session): `knowledge-base/prds`, `knowledge-base/journeys`.

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
  `/zetify:prd:create NNNN` instead** — it is the same interview with you in the room, on the
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
   *this command needs the Fleet tools; create a personal key in Fleet under Settings › Connect your tools* —
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
| **Which slice** — *only when Step 1.2 found two that fit* | the cut this PRD lands in, and so the program it rolls up to | the candidate slices, each named by what it delivers in plain words with its id in parentheses (no id at all on a customer-addressed card), the stub's own recommended |
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
   own entry — never a second `stub` entry, never a second number; `plain_title:` written or refreshed to say what the drafted PRD now promises, to the *Plain titles* rule in `feature-doc-reconcile.md`; `slice:` as confirmed;
   `priority:` from the vision check, deliberately, never the fallback; `implements:` from
   Step 1.4; **`depends_on:` from the text — every PRD it builds on or is a branch point of, and
   every bug fix it waits for as its tracker key (`ENG-NNNNN`), exactly as `create.md`'s
   `depends_on:` rule says; `related:` for a PRD it mentions that is not a dependency; never a PRD that builds on this one (its own `depends_on:` names this PRD), which would be a cycle. The
   driver reads that list and never the prose, and `prd-depends-on-prose` fails the commit
   when they disagree;** `## Brief` kept above `## In Plain Words` as the record the interview started
   from; then the template's required sections in Phase 4's order — `## In Plain Words`
   first, the vision alignment, the source trace, the value justification, the resilience
   block, the scope, the requirements, the acceptance criteria each with a disposition tag
   and a citation on every AC that realises a claimed row, the **`docs_impact`** block
   (`create.md` Phase 0.7 — pages created or changed, each named by page id via `slot:docs`,
   with its audience, page kind and verifying journey; `none` for an internal capability,
   never for a customer-facing one without a reason on the record), `## Open questions` for
   what the rounds left open, `## Scope ledger`, `## Next Steps` naming
   `/zetify:prd:design NNNN`. One proof substrate per PRD: a record-closed criterion the ask
   needs is a second, proof PRD's — say so in `open` rather than mixing it in.
   The PRD prose and its requirements follow the plain-language rule in
   [`process/writing.md`](../../../process/writing.md) → *Write for a reader who does not
   know the code*, exactly as `create.md` says.
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
6. **The trace** — Phase 5: the feature map's row for this capability — **a row already citing
   this PRD's number is the row**: a plan wrote it when it cut this stub, so refresh its wording
   and `Tested by` in place, never a second row beside it, and keep it under the stub's `use:`
   (the use the person planned it for, never re-guessed); otherwise the gap row a
   decomposition left flipped from `—` to this number, never a duplicate; a new row with a
   `CAP` id from the allocator when none exists; `Tested by` pointing at the journey. The
   refreshed row keeps the PRD's title as its name, so the page and the PRD read the same. Every
   row it writes or refreshes, a new register row and a new criterion are worded to [*Wording a promise*](../../../process/knowledge-bootstrap-formats.md#wording-a-promise--every-capability-rule-and-criterion).
   A new row sits under the use it serves, and a map with no brief yet gets one in this change —
   [*Writing a feature brief*](../../../process/feature-doc-reconcile.md#writing-a-feature-brief--every-map-that-is-created-or-edited); headless, a row that fits no use is filed rather than forced, and a brief written here is
   named in the result's summary, because no round confirmed it.
   Nothing appended to the slice; nothing written to the roadmap, which is generated.
7. **Withheld, and reported in `open`** — the idea issues to close or relabel (Phase 5's
   *Source idea*), any mockup the design owes, the proof PRD a mixed substrate needs, the
   bar a promoted AC is waiting on. **No tracker write**: the projection reads the merged
   PRD and creates the issue itself.

Then `{{target:validate-knowledge}}` clean — the scope-ledger, the claim-cites and the
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
  `/zetify:prd:design NNNN` as the next step; on the fleet, [`prd:blueprint`](blueprint.md)
  designs the PRD once its prerequisites ship, and this command never runs either.
- **Headless only.** A terminal is refused in one sentence naming `prd:create`.
