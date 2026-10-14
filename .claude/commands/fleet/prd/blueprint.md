#  PRD — Blueprint (a drafted PRD is designed, on the fleet, just in time)

You turn a **drafted PRD** — `status: prd-drafted`, its job story, requirements, acceptance
criteria and `## Scope ledger` agreed — into a designed one: the journeys and page-specs
refreshed, the architecture audited, the technical and UX design written, the approved
mockup recorded, the requirement register reconciled, the envelope stated, `design.md` and
`ux-design.md` committed, and `status: designed`. That is what [`prd:design`](design.md)
produces with a person at a terminal on `/fleet:prd:design NNNN`, and **this command is that
design, run headless**: the same phases, every fork it would ask through `AskUserQuestion`
asked instead by writing through the fleet's question channel, answered on the PRD's own
page, and landed as one merged PR.

**Just in time is the point.** The fleet designs a PRD on its own only once every PRD this one
`depends_on` has shipped, and again when a prerequisite ships after the design was written.
When a prerequisite is **planned but not built**, the fleet does not decide for the person: it
dispatches this command to ask one card — *design now from the plan, or wait?* (Step 0b) — and
a person who answers *now* gives **recorded permission** (`fromPlan` in the `## Shaping` block)
to design from that prerequisite's plan. Otherwise the design is read off **the code as merged
on `main` now**, never off what the prerequisites' PRDs promised — and the commit it was read against is recorded in the design's
own frontmatter (`designed_against:`, Step 7), which is what lets the fleet tell a design that
predates a prerequisite's shipping from one that does not.

**You are a composition, not an authority.** Every rule about what a design is, what it must
carry, how its scope is disciplined and what the output looks like lives in `design.md`, and
this file cites it rather than restating it: the context and the open decisions are *Phase
0*, the journeys and page-specs *Phase 0.5*, the baseline, the mockup, its promotion and its
approval gate *Phase 1* (Steps 0-pre, 0, 0b, 0c), the necessity test *Phase 1 Step 1*, the
audit *Phase 1.5*, the integration trace and the existence-claim citations *Phase 1.6*, the
layers *Phase 2*, the UX design *Phase 2b*, the red team *Phase 2c*, reuse and gaps *Phases 3
and 4*, the commitments *Phase 4c*, the cross-repo check *Phase 4.5*, the order *Phase 5*, the
offer *Phase 5.4*, the envelope *Phase 5.5*, the template *Phase 6*, the coverage *Phase 6.5*,
the status flip *Phase 7*. Its CRITICAL RULES bind this run in full — craft is yours and scope
is the human's, price a mechanism before designing it, argue for the best design, prose cites
a commitment. What this file owns is the **mapping**: which of its questions become cards in
which of the three rounds, which the run decides and reports, and which are withheld.

**The mockup approval gate stays, and it stays the person's.** `design.md` Rule 4b makes a
mockup approved only by an explicit answer, never by prose and never by the model's own
critique. Here that answer is a card on the PRD's page — *Approve — lock this mockup* — and
**the design does not land, the status does not flip and no PR opens until the person has
picked it.** A design with no surface to approve still waits for the person's go-ahead on its
draft (`design.md` Rule 3).

**Headless only.** A person at a terminal runs `prd:design` on the number, which is this same
design with them in the room; the fleet routes a mission by command string, so this verb
exists for the fleet and nothing else (Step 0).

The PRD to design: $ARGUMENTS

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps`
> block below and create **one todo per step**, in order; mark each `in_progress` on entry and
> `completed` on exit. The interview step is a bounded loop — add one todo per round under it.
> The one `status:` this command writes is the PRD's own — the only authored status in the
> model — and the spine says so with `produces: ["status"]`; nothing above the PRD is touched.
> The prose steps below are the authority; this spine indexes them.
>
> **`needs: answers` · `may merge: true`** ([`spine.md`](../../../process/spine.md)) — this
> command is dispatched headless and asks **by writing**, exactly as [`prd:fill`](fill.md)
> does, and merges its own PR for the same reason: the PR carries the design it authored and
> nothing that ships to a customer. It must never *block* on a human. **`AskUserQuestion` is
> not available to you and never will be.** Your escalation path is a `questions` result plus
> the end of your turn, and the answers come back by resumption of this same session — the
> shared contract inlined under *The headless contract* below.

```json
{
  "command": "prd-blueprint",
  "tier": "core",
  "sop": "none",
  "needs": "answers",
  "may merge": true,
  "intent": "Design a drafted PRD on the fleet, just in time — discovery, technical and UX design read off the PRD and the code as merged on main after its prerequisites shipped; every fork, the mockup approval and the scope offer asked through the fleet's written question channel over at most three rounds; then design.md written exactly as prd:design would at a terminal, status designed and the commit it was designed against recorded, by one merged PR that never opens before the person approved the mockup; plan stays attended.",
  "loads": ["process-shaping-headless", "product-vision", "ui-contracts", "architecture", "process-design-fidelity"],
  "requires": [
    "process-spine", "process-interview", "process-shaping-headless", "planning-model",
    "file-conventions", "commitments", "architecture", "gate", "codegen",
    "rubric-architecture-red-team", "process-design-fidelity", "languages", "git-workflow",
    "journeys"
  ],
  "optional": [
    "product-vision", "ui-contracts", "domain-model", "api-contract", "resilience", "entity-model",
    "feature-maps", "decisions", "components", "slices", "permissions", "runtime-contracts",
    "process-envelope", "docs"
  ],
  "steps": [
    {"id": "mode",              "name": "Which way in — the fleet, or a terminal (refused)",               "kind": "decision", "actor": "coordinator", "body": "step-0-which-way-in"},
    {"id": "read",              "name": "Read the PRD, its prerequisites and the code as merged",           "kind": "io",       "actor": "coordinator", "consumes": ["prd", "requirement-register"], "body": "step-1-read-the-prd"},
    {"id": "refusals",          "name": "The refusals — by sentinel, before any question",                  "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "step-2-the-refusals"},
    {"id": "settle",            "name": "Design what the repository settles — on the recommended defaults", "kind": "author",   "actor": "coordinator", "produces": ["page-spec", "journey"], "body": "step-3-design-what-the-repository-settles"},
    {"id": "mockup-fidelity",   "name": "Reference + mockup, held to the bar",                               "kind": "gate",     "actor": "coordinator", "gate": "hard", "critique": "design-fidelity-bar", "produces": ["reference", "mockup"], "body": "step-4-the-mockup"},
    {"id": "mockup-lock",       "name": "Promote it to the Lock tier and render it",                        "kind": "io",       "actor": "coordinator", "produces": ["mockup", "screenshots"], "body": "the-lock-tier-and-the-render"},
    {"id": "red-team-critique", "name": "Independent design critic panel",                                  "kind": "fanout",   "actor": "subagent",    "model": "opus", "body": "step-5-the-red-team"},
    {"id": "red-team-gate",     "name": "Disposition the red-team findings",                                "kind": "gate",     "actor": "coordinator", "gate": "hard", "critique": "architecture-red-team", "body": "step-5-the-red-team"},
    {"id": "rounds",            "name": "The rounds — the forks, the look, the offer and the go-ahead",     "kind": "loop",     "actor": "coordinator", "loop": {"max_rounds": 3, "exit": "the person approved the mockup (or the design has no surface to approve) and answered the go-ahead; or the ceiling was reached, and then nothing lands"}, "body": "step-6-the-rounds"},
    {"id": "mockup-approval",   "name": "The person approves the mockup — on the card, never by prose",     "kind": "gate",     "actor": "user",        "gate": "hard", "produces": ["mockup-approved"], "body": "round-2-the-look-the-offer-and-the-go-ahead"},
    {"id": "author",            "name": "Write it — the design, the approval, the commitments, the status", "kind": "author",   "actor": "coordinator", "produces": ["design", "ux-design", "status", "journey", "feature-map", "requirement-register"], "body": "step-7-write-it"},
    {"id": "land",              "name": "Land it — the branch, the PR, the merge",                          "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "step-8-land-it"},
    {"id": "landed",            "name": "The landed result, then the sentinel",                             "kind": "io",       "actor": "coordinator", "body": "step-8-land-it"},
    {"id": "report",            "name": "Report",                                                           "kind": "author",   "actor": "coordinator", "body": "step-9-report"}
  ]
}
```

---

## What to do

### Step 0: Which way in

```bash
printf '%s\n' "${FLEET_RESULT_FILE:-<unset>}"
```

- **Set** → the fleet dispatched you on a PRD whose prerequisites have shipped — or, with
  `askFirst` or `fromPlan` in the block, on one whose prerequisites are planned but not built
  (Step 0b). `$ARGUMENTS` is its number (`NNNN`), the mission's `## Shaping` block carries the
  kind (`design`), who or what requested it (`the fleet` for an auto-enrolled run), any
  instruction — a re-design names the prerequisite that shipped since — and the PRD's row as
  served (`before`); the payload says which round this is (*The headless contract* §1). Run
  Step 0b, then Steps 1–9.
- **Unset** → a person is at a terminal, and this is the wrong verb for them. Say exactly
  this and stop, writing nothing: **This command runs only on the fleet. At a terminal, run
  `/fleet:prd:design NNNN` instead** — it is the same design with you in the room, on the same
  PRD.
  **And say that the terminal is not a one-way door.** A design started by hand can be left
  to the fleet: once its program is driven, the fleet designs every drafted PRD whose
  prerequisites have shipped, and picks up from whatever is committed — the journey, the
  page-specs, a `design.md` already on `main`. Being sent to a terminal must never read as
  being sent there *for good*.
- **Set, but `$ARGUMENTS` is not a PRD number, or the block's `kind` is not `design`** → a
  mis-dispatch. Write nothing; sentinel `failed` naming what was wrong; stop.

### Step 0b: Design now, or wait — the one card the fleet asks first

The fleet never decides on its own to design from a plan. When a prerequisite is planned but
not built, it writes the question into the ask, and this run is how the question reaches the
person — on the program page and under *Needs you*, like every card this command asks.

- **`askFirst` in the block, and no prior question in the payload** → put `askFirst` **exactly
  as written** as this turn's `questions` result — the same `brief`, the same question `id`
  (`design-from-plan`), the same option ids (`now`, `wait`); the fleet reads the answer back by
  those words — then the sentinel `needs-decision` and stop. Read nothing else first, ask
  nothing else with it, write nothing anywhere. This card is not one of the three rounds.
  **Exception:** `git fetch origin main` and read the `status:` of every PRD in
  `before.askedAbout`; if every one of them is `shipped` by now, the question is moot — skip it
  and run Steps 1–9 as a normal design.
- **Resumed with that card answered `now`** — or **`fromPlan` in the block** (the fleet records
  the answer there, with who gave it, so a cold restart carries it too) → you have **recorded
  permission to design from the plan** of each prerequisite `fromPlan.prerequisites` names (or
  `before.askedAbout`, when the answer came on resume). Run Steps 1–9; Step 1 item 3 and Step 2
  say what changes.
- **Resumed with that card answered `wait`** → write nothing; sentinel `needs-decision`, summary
  *"waiting for the prerequisites to be built, as chosen — the fleet designs this
  automatically once they are"*, and stop. (The fleet normally holds the design on that answer
  before any run resumes; this is the cold case.)

### Step 1: Read the PRD, its prerequisites and the code as merged

Everything the repository can answer is answered here, before any question.

1. **The trunk, fresh.** `git fetch origin main`, then read everything below at
   `origin/main` — never at a checkout's stale head. Note the commit:

   ```bash
   git rev-parse origin/main   # the commit this reading is taken at
   ```

   It is the first candidate for `designed_against:`; Step 7 settles the final value.
2. **The PRD** — `design.md` *Phase 0* items 1–4 and 6: the frontmatter, the job story, the
   requirements, the acceptance criteria and their tags, `implements:`, the `## Scope ledger`
   the fill wrote, and every entry of `## Open decisions`, each dispositioned *adopt* /
   *deviate* / *escalate* exactly as that item says. An *escalate* is a Round 1 card, never a
   choice you make.
3. **The prerequisites, as built.** For each PRD in `depends_on`: its `status:`, and — the
   reason this command runs late — **the code it shipped**: the files its merged PR changed,
   the contracts it landed (the codegen sources `slot:codegen` names, the storage, the API
   surface), read at `origin/main`. Where the drafted PRD assumed a contract that shipped
   differently, the shipped one wins and the difference is a line in *Architecture notes*.
   **A prerequisite the permission covers (Step 0b)** is not built, so read **its plan** instead
   — its `plan*.md` and `design.md` at `origin/main` — as the contract it will ship, and say so
   in *Architecture notes*: *designed from PRD NNNN's plan, before it was built, with
   <chosenBy>'s recorded permission*. Its plan binds this design; where it is silent, choose
   the reading its design already committed to and name it.
4. **A design already on `main`.** `design.md` *Phase 0* item 5 asks whether to revise or
   start fresh; here it is **decided**: an existing design is **revised in place** — every
   decision it recorded stands unless the code merged since its `designed_against:` moved
   under it, and each one that moved is re-derived and named in *Architecture notes* as
   *re-designed against the newer commit: what shipped, what changed*. Read the change with
   `git log --oneline <its designed_against>..origin/main -- <the paths its layers touch>`.
   An approved mockup on record **carries over** when the surface it shows is unchanged by
   the re-design — the person already approved it, and `design.md` re-runs the gate only when
   what the customer sees changes (*Phase 5.4*, *Act on the answer*).
5. **The ground** — the vision (`slot:product-vision`), the slice and its program
   (`slot:slices`), the registers (`slot:commitments`), the components (`slot:components`),
   the journeys (`slot:journeys`), the UI contract (`slot:ui-contracts`), the architecture
   (`slot:architecture`). Read as `design.md` *Phase 0* and *Phase 0.5* say.

### Step 2: The refusals

By sentinel, before any question, in the form *The headless contract* §9 gives:

- **No PRD folder for the number** → `failed`, a mis-dispatch.
- **`status:` is `stub`** → `failed`: a stub is `prd:fill`'s, and designing one would design
  against requirements nobody has agreed.
- **`status:` is past `designed`** (`planned` or later, or a terminal status) → `failed`: its
  plans bind to the design on record, and re-opening it is a person's call at a terminal.
- **A prerequisite has not shipped** — a `depends_on` PRD whose `status:` is not `shipped`,
  and not `verified` with its PR merged into `main`, **and not covered by the recorded
  permission of Step 0b** (`fromPlan`, or a `now` answer in this session) → `needs-decision`:
  *"this PRD waits on <the prerequisite, by name>; designing now would design against a
  contract that does not exist yet — it is designed automatically once that ships"*. The fleet
  reads this refusal as a hold, never a failure, and asks again once the prerequisite ships. A
  covered prerequisite is read from its plan (Step 1 item 3) and is no refusal. A **cancelled**
  prerequisite is the same refusal with the move *"point this PRD at what replaces it, or drop
  the dependency"*.
- **The necessity test fails** (`design.md` *Phase 1 Step 1*, Rule 6c) — neither *how often it
  fires* nor *what breaks without it* has a concrete answer from the code → **ask it, as a
  card**, never a bare refusal: a refusal with no question reaches nobody, and the fleet counts
  it as a run that landed nothing. One question, id `necessity`, the finding in plain words in
  the brief, free text on, two options — `breaks` *"Here is what breaks without it"* (the
  person's text is the answer; on resume, take it as the necessity evidence and go on to
  Step 3) and `leave` *"Leave it undesigned"* (on resume, write nothing and end `needs-decision`
  saying the PRD waits for a person to narrow or cancel it). Then the sentinel
  `needs-decision`. It counts as Round 1.
- **The envelope busts** (`design.md` *Phase 5.5*) — measured after Step 3, before any round
  → **ask it, as a card**: one question, id `envelope`, the proposed sibling split and its seam
  in the brief, options `narrow` *"Narrow it to the first part, as named"* (on resume, design
  that part and name the rest in `open`) and `split` *"Split it by hand at a terminal"* (on
  resume, write nothing and end `needs-decision` saying it waits for
  `/fleet:prd:design NNNN`). Cutting siblings mints PRDs nobody asked for, which a headless
  run never does (*The headless contract* §2). It counts as Round 1.

### Step 3: Design what the repository settles

Everything `design.md` settles without a person is settled here, **on the recommended
default of every fork still open** — so the draft the person reads in the rounds is a real
design, not a list of blanks — and nothing is committed yet:

1. **Journeys and page-specs** — *Phase 0.5*, in full: the journey files refreshed, the screen
   inventory, each surface's `<Page>.spec.md` authored or refreshed, the docs impact resolved.
2. **The best-practice baseline** — *Phase 1 Step 0-pre*, **decided**: established from the
   repository, the nearest in-repo precedent and your own knowledge, and saying so in one
   clause when the seat could not research further.
3. **The understanding and the dimensions** — *Phase 1 Step 1*: the necessity test first, then
   the dimensions, each marked *settled by the PRD*, *settled by the baseline*, *settled by the
   code* or *open*. Open means **two best-practice-grade options genuinely compete, or the
   standard is wrong for us for a stated reason** (Rule 8) — never "I would like permission to
   follow the standard". Only the open ones can become cards.
4. **The audit and the trace** — *Phase 1.5* and *Phase 1.6*, every existence claim cited to a
   `file:line` at the commit Step 1 recorded. A `fix` is yours; a `defer` needs a tracked issue,
   which this run may not file — so it is **withheld** and named in `open`; a `perpetuate`, and
   any finding that would change a promise, is a Round 1 card.
5. **The layers, the UX design, reuse, gaps, commitments, cross-repo scope, order** —
   *Phases 2, 2b, 3, 4, 4c, 4.5, 5*, as written there. Cross-repo companion work is named in
   *Delivery notes* and in `open`; **no tracker write** files it.
6. **The withheld list** — every addition *Phase 5.4* would offer, gathered from every phase
   above. Nothing on it is adopted.
7. **The envelope** — *Phase 5.5*, measured now; a bust is Step 2's refusal.

### Step 4: The mockup

Only when the design adds or materially changes a customer-facing surface (`design.md`
*Phase 1 Step 0*); a change purely additive to a shipped page is the page-spec's, not a
mockup's ([`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §1.5c), and a
backend-only design skips Step 4 entirely.

The reference and the Explore-tier rounds are *Phase 1 Step 0* in full — a named high-craft
reference, the token file read at the moment you write, real component shapes, the mockup a
file in the PRD's own `mockups/` folder, at most three rounds — and the chosen round must
**clear the design-fidelity bar** before any person sees it
([`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §2). Your own critique
grades it; it never approves it.

#### The Lock tier and the render

*Phase 1 Step 0b*, in full: the chosen round promoted to a real fixture page on the dev-only
route `slot:ui-contracts` names, with its screenshot spec, every state addressable. Then
render every meaningful state with that harness into the checkout-scoped run folder
`.claude/run/prd-blueprint/<NNNN>/approval/`, beside a one-page `index.html` that shows the
images in order with a caption each — that folder is what the person will open. **Renders are
never committed** (§1.5-0d); the committed mockup file is the contract.

**A seat that cannot run the harness cannot present what it asks approval on** → sentinel
`failed`, naming that this seat cannot render the fixture page. Approving a design nobody
could see is the hollow gate §1.5b exists to forbid, and a routing fault is not the person's
to answer.

**Commit the mockup before you ask about it — the one write ahead of the go-ahead.** The
mockup is the question's subject, and a cold restart must find the thing the person is
looking at. So commit **only** the mockup folder, the reference and the fixture page on the
deterministic branch (Step 8's name), push the branch, and **open no PR**: nothing can merge,
and nothing lands before the answer. Every later round amends that same branch.

### Step 5: The red team

*Phase 2c*, in full, **after Step 3 and before any round** — so the draft a person is asked
to confirm is one an independent critic already argued against. The panel is dispatched as
sub-agents; a seat that cannot spawn them fails the step, and then **nothing lands**: sentinel
`failed`, naming that the critic panel could not run on this seat (Rule 4a). Each finding is
dispositioned there; one that would add scope joins the withheld list, one that would change
a promise becomes a Round 1 card.

When an answer in the rounds moves the design off a recommended default, re-run the panel
over the layers that answer changed before Step 7 — a design is red-teamed as written, not as
first drafted.

### Step 6: The rounds

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

Each round's brief opens with which round this is of up to three, says in one line what the
PRD lets somebody do once it ships, names one person doing it, and says what this round
settles. **Name no id bare** — a prerequisite is *the export the admin screen needed (PRD
NNNN)*, never the number alone.

**How a round is sent.** A round that shows the person a mockup is asked through the session
tools' `ask` tool (the fleet's MCP server; the engine names it after its config key), giving
the approval folder and the mockup folder as the question's `attachments`: it uploads each
folder, writes the same `questions` document to `$FLEET_RESULT_FILE`, and parks the run — the
park marker it drops stands in for the sentinel, so **stop the moment it answers `parked`**.
`ask` carries no `draft` and no `confirm`, so on that round the brief carries the draft in
its eight lines. With no session tools on the seat, a round that must show a mockup cannot be
sent → sentinel `failed`, naming that this seat has no session tools. Every other round is
written to the file directly, exactly as §3 says, with `draft` and `confirm`.

**The aspect each card changes** (*The headless contract* §3, the `prd design` row): a fork
→ `decisions` when it settles how, `commitments` when it settles a promise; the look →
`mockup`; each offer card → `scope`; a split or an envelope question → `envelope`.

#### Round 1 — the forks and the first look

Skipped when nothing is open and there is no surface to show; the run goes to Round 2.

| Card | What it establishes | Options |
|---|---|---|
| **Each open fork** — *Step 3.3* | the design decision two best-practice options genuinely compete on, or a special-case deviation | the options, recommended first, each `then` naming what a real person sees differently and what it costs; free text |
| **Each escalation** — *Phase 0* item 6, *Phase 1.5* `perpetuate`, a red-team finding that changes a promise | a promise added, changed or knowingly left broken | the choice, with what the promise would say either way; free text |
| **The first look** — *only with a mockup* | anything off in the layout or the shape, before the details are settled on it (§1.5b step 2: a reaction first, approval later) | *Nothing is off — settle the details on this layout* (recommended) / *Something is off — I say what in my own words*; free text; the mockup attached |

Most-blocking first, four at most; a fork beyond the four is decided on its recommended
default and named in the brief as decided. Then STOP: the `questions` result, the park, end
the turn.

#### Round 2 — the look, the offer and the go-ahead

On resume, consume Round 1 (*The headless contract* §4): a picked non-default re-derives the
layers it touches and re-runs Step 5 over them; a reaction to the look reworks the mockup
through Step 4 (bar, Lock tier, render, amended branch) before it is shown again. Then ask,
at most four cards, marked `"confirm": true` when written directly:

| Card | What it establishes | Options |
|---|---|---|
| **The approval** — *only with a mockup that has not carried over* | the mockup is approved — the `mockup-approved` gate, `design.md` *Phase 1 Step 0c* item 4 | *Approve — lock this mockup* (recommended) / *Request changes*; free text; the rendered states and the mockup attached |
| **Each withheld addition** — *Phase 5.4* | whether it is pulled in | *Leave it out* (recommended) / *Pull it in*, each `then` naming what it adds, what it costs (files, test mass, envelope) and why it did not clear the bar alone |
| **The go-ahead** — *only when there is no approval card* | the draft is what gets written (`design.md` Rule 3) | *Write this design* (recommended) / *Hold it — I say what is wrong*; free text |

**The offer is `prd:fill`'s shape, for `prd:fill`'s reason**: `design.md` *Phase 5.4* asks for
one multi-select with no recommendation; the written channel has no multi-select and requires
exactly one marked, and the withholding is the recommendation, so *leave it out* carries the
mark and the ledger records that it did. More than three withheld items beside an approval
card (four without one): offer those with the strongest case, record the rest `withheld`
unoffered.

**The brief of this round is the draft**, in at most eight lines: what the design builds and
for whom, the decisions that shape it, the surface, the commitments it adds, the envelope.
Nothing is written before its answer.

#### Round 3 — only when the look was sent back

Only when Round 2's approval was answered *Request changes* (or a free-text answer that is
not an approval): rework the mockup through Step 4, then ask the approval card again, with any
offer card left unanswered, and the go-ahead folded into it.

**At the ceiling without an approval, nothing lands.** An un-approved mockup is a blocked
design, not a design with a caveat (`design.md` *Phase 1 Step 0c*): no status flip, no PR, no
`landed` file. Sentinel `needs-decision`, summary naming the move: *"the look was not settled
in three rounds — finish it at a terminal with `/fleet:prd:design NNNN`, or send it back with
what the page must show"*. The pushed branch stays for whoever picks it up.

**Every other gap at the ceiling is written as it stands**: an unanswered fork is decided on
its recommended default and named in `open` as decided without an answer; an unanswered offer
card leaves its item `withheld`.

### Step 7: Write it

Only after the go-ahead: the approval picked (or carried over, or no surface to approve) and
the round's other cards consumed. Everything is authored **exactly as `design.md` says**,
cited, never restated:

1. **`design.md`** — *Phase 6*'s template in full, with **one frontmatter field this command
   adds**:

   ```markdown
   ---
   type: prd-design
   designed_against: <the full 40-character commit of origin/main the design was read against>
   ---
   ```

   **`designed_against:` is the commit whose tree every citation in the design was checked
   at** — the tip the branch is rebased onto in Step 8, never the commit the reading started
   at when the trunk has moved since. So before committing, `git fetch origin main`; when the
   tip moved, re-check the design's existence-claim citations and integration trace against the
   new tip, re-derive anything a prerequisite changed, and record the new tip. The fleet maps
   the commit to the generation it served and compares generations — never two clocks — to
   tell whether a prerequisite shipped after the design was written. A re-design replaces the
   value; it never appends a second one.
2. **`ux-design.md`** — *Phase 2b*'s output, with `## Approved design` recording what *Phase 1
   Step 0c* item 5 asks — the round, the **repo-relative path** of the approved mockup file,
   the fixture route, the date — and the approval as it was given here: *answered on the PRD's
   page through the fleet's question channel*, the question, the option picked, and the
   person's own words when they gave any. A carried-over approval names the round and date it
   was first given and says the surface is unchanged since. A backend-only design writes no
   approval block.
3. **The journeys, page-specs, feature map and register rows** — *Phases 0.5, 4c and 6.5*, in
   the same commit; new rows' ids from
   `python3 knowledge/scripts/validate_id_collisions.py --allocate <PREFIX> <n>`.
4. **The ledger** — `## Scope ledger` in `design.md`, every addition with its disposition:
   *admitted* (with the AC it cannot pass without), *pulled in* (the round it was pulled in),
   *withheld* (offered and left out, or beyond the offer), and `none — <what was considered>`
   when nothing was added.
5. **The status** — *Phase 7*, its gate first (`implements:` non-empty on covered ground, no
   claimed row still `open`): from `prd-drafted`, `status: designed` with
   `{ state: designed, at: <the timestamp, in the form the PRD's own lines use>, by: fleet:prd:blueprint }`
   appended to `status_history:`; a re-design leaves `designed` and its history as they are. A
   missing `## In Plain Words` is written as *Phase 7* item 2 says.
6. **Withheld, and reported in `open`** — deferred quirks and the issues they need, companion
   work in another repository, ideas to close, anything on the withheld list. **No tracker
   write**: the fleet projects the tracker from the merged PRD.

**Plan is dispatched by the fleet too (0209).** *Phase 8* dispatches `prd:plan` as a
sub-agent at a terminal; a headless run does the same through the plan lane — once this design
lands and the corpus shows `designed`, the fleet's plan mission runs [`prd:plan`](plan.md)
headlessly with no operator in the loop, so `## Next steps` still names `/fleet:prd:plan
NNNN` as the step a person would run by hand.

Then `make validate-knowledge` clean — the scope ledger, the claim citations, the mockup record
and the file types are all in it.

### Step 8: Land it

*The headless contract* §6, with **two differences this command needs**:

- **The branch is `agent/design-<key>`**, not `agent/shape-<key>`: the fill that drafted this
  PRD already used the shaping branch under the same key, and its merged PR would read as this
  run's prior attempt. Find the prior attempt by the branch itself:

  ```bash
  gh pr list --state all --head "agent/design-<key>" --json number,state,url,mergedAt
  git ls-remote --heads origin "agent/design-<key>"
  ```

  An open PR is the prior attempt — drive it. A branch with no PR is this run's mockup commit
  (Step 4) — check it out and continue on it. A **merged** PR counts as this dispatch's landing
  only when `main`'s `design.md` now carries a `designed_against:` other than the one `before`
  served (or `before` served none and the PRD now reads `designed`); otherwise it is an
  earlier design this dispatch is re-doing, and the branch starts fresh.
- **The PR opens only after the go-ahead** — and with a mockup, only after the approval card
  was picked. Rebase the branch onto the freshly fetched tip Step 7 recorded, squash the
  mockup commits into the design commit, re-check every allocated id against that tip, push
  with `--force-with-lease`, open the PR with the PRD's key and the word *design* in its
  title, and arm `gh pr merge --auto --squash` the moment it opens. Drive it to `state: MERGED`
  with `gh_pr_merge_state.py --watch`, exactly as §6 says.

Once merged, the `landed` document to `$FLEET_RESULT_FILE`, written whole and read back —
§7's shape with a design's `changed`:

```json
{"kind": "landed", "landed": {"kind": "prd", "id": "NNNN", "href": "prd:NNNN", "pr": "<the merged PR's URL>", "files": ["<every path the PR changed>"], "summary": "<one plain sentence: what the design builds, for whom>", "changed": {"status": "designed", "designedAgainst": "<the 40-character commit>", "mockup": "approved", "implements": ["<each claimed row id>"], "acs": 0}, "open": ["<each unsettled or withheld item>"]}}
```

`status` is the frontmatter as written; `designedAgainst` is `design.md`'s field, verbatim;
`mockup` is `approved` (picked in this run), `carried` (an earlier approval stands) or
`not-needed` (no surface to approve); `implements` the claim as it stands; `acs` the count of
acceptance criteria. Then the sentinel: `success` with the PR URL. A PR that could not be
brought to merge in this run is `partial` with the PR URL and **no `landed` file**, so the
next dispatch resumes the branch — §8's table, and never `done`.

### Step 9: Report

Nine lines, for a human reading the transcript: the number and its slice; the commit it was
designed against, and whether this was a first design or a re-design (and what shipped to
cause it); the rounds asked and questions spent (`n of 12 across r rounds`); the forks asked
and the forks decided; the necessity-test line; the mockup's outcome (*approved in round r*,
*carried*, *not needed*); the offer's outcome (*k offered, j pulled in*, or *nothing
withheld*); the envelope; the PR and its state, the result written and the sentinel word.

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

- **Cite, never restate.** Every phase of the design is `design.md`'s; this file maps its
  questions onto three rounds and owns none of its rules, and every CRITICAL RULE of
  `design.md` binds this run.
- **The code as merged is the ground truth, and the design names the commit it read.**
  `designed_against:` in `design.md`'s frontmatter is the full commit every citation was
  checked at; a re-design replaces it and says in *Architecture notes* what shipped since.
- **The mockup is approved only by the person's pick on the card.** Not by free text that
  reads like a yes, not by silence at the ceiling, not by your own critique. Without it nothing
  lands; an approval carries over only when the surface is unchanged.
- **The run decides everything the repository settles**, and asks only the forks two
  best-practice options genuinely compete on, the escalations that change a promise, the look,
  the offer and the go-ahead — never permission to follow the standard.
- **The offer is two-option cards with *leave it out* recommended**, and the ledger records
  every disposition. Nothing on the withheld list is adopted because nobody was there to say no.
- **The one authored status this command writes is `designed`** — from `prd-drafted`, with
  its history line — and nothing above the PRD carries a status.
- **No tracker write, no plan dispatch, no `AskUserQuestion`.** Deferred quirks, companion
  work and ideas to close are reported in `open`; plan stays attended.
- **Headless only.** A terminal is refused in one sentence naming `prd:design`.
