# <!-- home -->Zetify<!-- /home --> PRD — Blueprint (a drafted PRD is designed, on the fleet, just in time)

You turn a **drafted PRD** — `status: prd-drafted`, its job story, requirements, acceptance
criteria and `## Scope ledger` agreed — into a designed one: the journeys and page-specs
refreshed, the architecture audited, the technical and UX design written, the approved
mockup recorded, the requirement register reconciled, the envelope stated, `design.md` and
`ux-design.md` committed, and `status: designed`. That is what [`prd:design`](design.md)
produces with a person at a terminal on `/zetify:prd:design NNNN`, and **this command is that
design, run headless**: the same phases, every fork it would ask through `AskUserQuestion`
asked instead by writing through the fleet's question channel, answered on the PRD's own
page, and landed as one merged PR.

**Before you write a design, journey or decision file, read its docs page** (under `.fleet/docs/`; `read_doc <page>` when Fleet's tools are in the session): `knowledge-base/prds`, `knowledge-base/journeys`, `knowledge-base/decisions`.

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
    "feature-maps", "decisions", "components", "slices", "permissions", "security",
    "runtime-contracts", "process-envelope", "docs"
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
  `/zetify:prd:design NNNN` instead** — it is the same design with you in the room, on the same
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
   (`slot:architecture`), and the security posture (`slot:security`) where the PRD adds or
   changes an interface. Read as `design.md` *Phase 0* and *Phase 0.5* say.

### Step 2: The refusals

By sentinel, before any question, in the form *The headless contract* §9 gives:

- **No PRD folder for the number** → `failed`, a mis-dispatch.
- **`status:` is `stub`** → `failed`: a stub is `prd:fill`'s, and designing one would design
  against requirements nobody has agreed.
- **`status:` is past `designed`** (`planned` or later, or a terminal status) → `failed`: its
  plans bind to the design on record, and re-opening it is a person's call at a terminal.
  **The one exception, and it is narrow: a row whose `requested_for` is `objection`.** A person
  objected to the recorded approach and the fleet asked this run to answer it; on a `planned`
  PRD that objection is accepted here and nowhere wider. An ordinary design is still refused
  past `designed`.
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
  `/zetify:prd:design NNNN`). Cutting siblings mints PRDs nobody asked for, which a headless
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

Each round's brief opens with which round this is of up to three, says in one line what the
PRD lets somebody do once it ships, names one person doing it, and says what this round
settles. **Name no id bare** — a prerequisite is *the export the admin screen needed (PRD
NNNN)*, never the number alone.

**A round after the first opens by saying how it follows the one before — in the brief, after
the round number, before anything new.** *"Following your answers in round 1: you chose X; you
approved Y."* — each earlier answer that shapes this round, in the person's own words, and one
line naming what is **already settled and not asked again**. The same goes for an earlier
*command's* answers (the fill's, the PRD's): a card that touches ground the PRD or a previous
answer already settled is allowed only when the code as merged contradicts it, and then its
prompt **quotes the earlier answer and names the evidence that re-opens it** (*"you chose the
lifetime optional; the service refuses a part without one"*) — never the bare question again,
which a person reads as being asked twice. What a round asks is only what the earlier answers
left open.

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
| **The look and its approval, one card** — *only with a mockup that has not carried over* | the mockup is approved — the `mockup-approved` gate, `design.md` *Phase 1 Step 0c* item 4 — or sent back. The question is *"Approve this layout, or tell me what's off"*: one question, never a reaction first and an approval after, because a person reads those as the same question asked twice | *Approve — lock this mockup* (recommended) / *Something is off — I say what in my own words*; free text is change requests; the mockup attached |

**A look that a fork in the same round can change is not asked in that round.** The mockup was
drawn on the recommended default of every open fork (*Step 3*), so a fork whose options change
what the surface shows — a field required or optional, a control present or absent, a list
column, a message — decides what the person would be approving. If any open fork is of that kind,
Round 1 asks the forks **without the look card**, and the look and its approval is Round 2's
first card, on a mockup re-drawn on the answers — the first time the person sees it. Putting
both in one round makes a non-default pick void the approval beside it, and the person is then
shown the same mockup twice (measured on a customer's PRD: the required-lifetime fork and the approval
of a mockup that showed the lifetime required, in one round; the pick was *optional*, the
approval *yes*, and Round 2 put the whole mockup to him again). Forks that change nothing the
mockup shows leave the look in Round 1 as above.

Most-blocking first, four at most; a fork beyond the four is decided on its recommended
default and named in the brief as decided. Then STOP: the `questions` result, the park, end
the turn.

#### Round 2 — the look, the offer and the go-ahead

On resume, consume Round 1 (*The headless contract* §4): a picked non-default re-derives the
layers it touches and re-runs Step 5 over them. The Round 1 look card answered *Approve* — or
any equivalent such as "nothing off" — **is the approval**: record `mockup-approved` and never
asks to approve the same unchanged mockup again. A change request reworks the mockup through
Step 4 (bar, Lock tier, render, amended branch) and the next round asks for approval of the
changed mockup only — and **only the change is put to the person**: the approval card's prompt
names what changed in one line, the rendered-states attachment holds **only the states that are
new or changed** (each state a person already approved and that did not change stays out of it,
and the caption says so: *"the other states are as you approved them in round 1"*), and the
clickable mockup is attached as the whole. Then ask,
at most four cards, marked `"confirm": true` when written directly:

| Card | What it establishes | Options |
|---|---|---|
| **The approval** — *only with a mockup that was not approved in Round 1, has not carried over, or changed since Round 1* | the mockup is approved — the `mockup-approved` gate, `design.md` *Phase 1 Step 0c* item 4 | *Approve — lock this mockup* (recommended) / *Request changes*; free text; the rendered states and the mockup attached |
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

Only when the approval (Round 1's look card or Round 2's) was answered *Request changes* (or a free-text answer that is
not an approval): rework the mockup through Step 4, then ask the approval card again, with any
offer card left unanswered, and the go-ahead folded into it.

**At the ceiling without an approval, nothing lands.** An un-approved mockup is a blocked
design, not a design with a caveat (`design.md` *Phase 1 Step 0c*): no status flip, no PR, no
`landed` file. Sentinel `needs-decision`, summary naming the move: *"the look was not settled
in three rounds — finish it at a terminal with `/zetify:prd:design NNNN`, or send it back with
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

   **`## Approach` is REQUIRED, in three parts** (a design objection): `### What will change`, `### How`
   and `### Why this way`, the last naming the alternative the agent rejected in one labelled line,
   `**The alternative it rejected:** <the road not taken and why>`. A person reads
   it on the PRD's Design page before any code exists and may object to it. **Refuse to land a
   design whose `## Approach` lacks any of the three, or whose `### Why this way` has no
   `**The alternative it rejected:**` line with words after the label** — say which part is missing
   and stop `failed`; an approach a person cannot review is not a design the fleet may build from.
2. **`ux-design.md`** — *Phase 2b*'s output, with `## Approved design` recording what *Phase 1
   Step 0c* item 5 asks — the round, the **repo-relative path** of the approved mockup file,
   the fixture route, the date — and the approval as it was given here: *answered on the PRD's
   page through the fleet's question channel*, the question, the option picked, and the
   person's own words when they gave any. A carried-over approval names the round and date it
   was first given and says the surface is unchanged since. A backend-only design writes no
   approval block.
3. **The journeys, page-specs, feature map and register rows** — *Phases 0.5, 4c and 6.5*, in
   the same commit; new rows' ids from
   `python3 knowledge/scripts/validate_id_collisions.py --allocate <PREFIX> <n>`. Every
   capability, register row and criterion it writes or rewords is worded to [*Wording a promise*](../../../process/knowledge-bootstrap-formats.md#wording-a-promise--every-capability-rule-and-criterion).
   A feature map this touches follows [*Writing a feature brief*](../../../process/feature-doc-reconcile.md#writing-a-feature-brief--every-map-that-is-created-or-edited): rows under their uses, a brief written in this commit
   when the map has none (named in the result's summary), a row that fits no use filed rather
   than forced.
4. **The ledger** — `## Scope ledger` in `design.md`, every addition with its disposition:
   *admitted* (with the AC it cannot pass without), *pulled in* (the round it was pulled in),
   *withheld* (offered and left out, or beyond the offer), and `none — <what was considered>`
   when nothing was added.
5. **The status** — *Phase 7*, its gate first (`implements:` non-empty on covered ground, no
   claimed row still `open`): from `prd-drafted`, `status: designed` with
   `{ state: designed, at: <the timestamp, in the form the PRD's own lines use>, by: fleet:prd:blueprint }`
   appended to `status_history:`; a re-design leaves `designed` and its history as they are. A
   missing `## In Plain Words` is written as *Phase 7* item 2 says.

   **An objection answered by a CHANGED approach on a `planned` PRD writes the status back**:
   `status: designed`, with `{ state: designed, at: …, by: fleet:prd:blueprint }` appended to
   `status_history:`. The plan was derived from the approach the person objected to, and Fleet's
   confirmation of this landing retires that plan row so the plan lane offers the PRD again. A
   **reasoned refusal writes nothing back**: the approach stands, so the plan stands too.
6. **Withheld, and reported in `open`** — deferred quirks and the issues they need, companion
   work in another repository, ideas to close, anything on the withheld list. **No tracker
   write**: the fleet projects the tracker from the merged PRD.

**Plan is dispatched by the fleet too (0209).** *Phase 8* dispatches `prd:plan` as a
sub-agent at a terminal; a headless run does the same through the plan lane — once this design
lands and the corpus shows `designed`, the fleet's plan mission runs [`prd:plan`](plan.md)
headlessly with no operator in the loop, so `## Next steps` still names `/zetify:prd:plan
NNNN` as the step a person would run by hand.

Then `{{target:validate-knowledge}}` clean — the scope ledger, the claim citations, the mockup record
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
{"kind": "landed", "landed": {"kind": "prd", "id": "NNNN", "href": "prd:NNNN", "pr": "<the merged PR's URL>", "files": ["<every path the PR changed>"], "summary": "<one plain sentence: what the design builds, for whom>", "changed": {"status": "designed", "designedAgainst": "<the 40-character commit>", "mockup": "approved", "implements": ["<each claimed row id>"], "acs": 0, "answers": {"kind": "revised | refused", "words": "<the answer in one plain paragraph>", "recordedAt": "<ISO instant>", "designedAgainst": "<the 40-character commit>"}}, "open": ["<each unsettled or withheld item>"]}}
```

`status` is the frontmatter as written; `designedAgainst` is `design.md`'s field, verbatim;
`mockup` is `approved` (picked in this run), `carried` (an earlier approval stands) or
`not-needed` (no surface to approve); `implements` the claim as it stands; `acs` the count of
acceptance criteria.

**`answers` is the objection's answer, and it is written in TWO places or not at all** (PRD
a design objection, design D7): the same words go into `design.md`'s `## Approach` (a revision rewrites the
part the person disagreed with; a refusal states its reason there) AND into this landing key.
The fleet shows it on the Design page only once the design is confirmed, so a landing that says
`answered` over a design the corpus has not changed is never served. A run that was not asked
to answer an objection writes no `answers` key at all. Then the sentinel: `success` with the PR URL. A PR that could not be
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
