# Knowledge Bootstrap — describe an existing code base into the corpus, one step at a time

You turn a repository that has **code but no knowledge base** into one the rest of the command
tier can build on: a component registry, feature maps with capabilities, requirement registers,
journeys — written to the shapes the shipped readers parse, so that new work plans against it
and **the QA Desk can check its promises on the first night**.

**Before you write a knowledge file file, read its docs page** (under `.fleet/docs/`; `read_doc <page>` when Fleet's tools are in the session): `knowledge-base/the-folder`, `knowledge-base/journeys`, `knowledge-base/feature-areas`, `knowledge-base/promises`, `knowledge-base/capabilities-and-components`.

**The one idea that governs every step: the code shows what the product *does*; only a person
can say what it *promises*.** A rule you read off the code is evidence, not a commitment. Write
an observed accident as a promise and the QA Desk will defend the bug forever. So you draft from
the code, and the person confirms — in batches, never one row at a time.

**One invocation advances one step and stops.** A repository of any size is described across
many sessions; the progress file is the only memory between them. It lives in the
checkout-scoped run state (`.claude/run/knowledge-bootstrap/`, `layout` prints it), never in the
corpus and never in a commit: the customer's tree carries only the knowledge it asked for.

**It grows from where the person points, never all at once.** A customer starts with one part
("start with bug tracking"), gets that part described end to end — capabilities, rules, its
area, its journeys, checkable by the QA Desk — and adds the next part days or weeks later, while
the code keeps moving underneath. Every phase therefore works on **the confirmed slice so
far**, every gate is a gate on that slice, and nothing waits for the whole repository:

- **The map is whole; the description is partial.** Phase 1 maps every code file to a component
  (that is cheap and it is the denominator), but only the parts the person has ordered are
  *confirmed*. The rest stay `proposed`: their boundaries are not asked about until they are
  ordered, and the questions they raise wait on their row.
- **Areas and journeys are re-entrant.** Phase 3 and 4 run for the components confirmed so far
  and run again for each component confirmed later, extending an area rather than redrawing it.
- **The coverage gate ratchets.** The journey validator's coverage roots (`[fleet.structure]
  coverage_roots` in `.fleet/fleet.toml`) are exactly the owned paths of the
  confirmed components; each confirmation adds its paths. "Every path of a described part is
  claimed" holds at every step and becomes the whole tree only when every part is described —
  never a baseline file, never a substrate map claiming code nobody read.

```
/zetify:knowledge:bootstrap                 # do the next step the progress file says is ready
/zetify:knowledge:bootstrap start <what>    # first contact: describe only <what> for now (a part, a feature, a directory)
/zetify:knowledge:bootstrap add <id>        # put one more component in the order, later
/zetify:knowledge:bootstrap status          # is it ready to build on yet, and where it stands; change nothing
/zetify:knowledge:bootstrap component <id>  # draft (or review) this component next, out of order
/zetify:knowledge:bootstrap review <id>     # run the batch review for a drafted component
```

The shapes it writes — and the progress file's own — are in
[`knowledge-bootstrap-formats.md`](../../../process/knowledge-bootstrap-formats.md). Read it
before writing anything.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps`
> block below and create **one todo per step**, in order; mark each `in_progress` on entry and
> `completed` on exit. Most invocations run `resume`, **one** phase step, `land` — the phase
> steps that are not the chosen one close as `N/A`. A failed `gate` stays open with its residual
> noted, and the step does not land.

```json
{
  "command": "knowledge-bootstrap",
  "tier": "core",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "intent": "Describe an existing code base into the knowledge corpus one resumable step at a time — survey, components, per-component capabilities and rules, feature areas, journeys — drafting from the code and confirming every promise with a person in batches, so new work builds on it and the QA Desk checks it out of the box.",
  "loads": ["process-interview"],
  "requires": ["process-spine", "process-interview", "process-knowledge-bootstrap", "git-workflow"],
  "optional": ["languages", "gate", "codegen", "dev-environment", "product-vision", "components", "feature-areas", "feature-maps", "journeys", "commitments"],
  "steps": [
    {"id": "resume",        "name": "Resume: read the progress file, check staleness, pick the step",  "kind": "decision", "actor": "coordinator", "body": "step-0-resume"},
    {"id": "survey",        "name": "Phase 0 — survey: slots, inventory, product framing",              "kind": "author",   "actor": "coordinator", "body": "phase-0-survey"},
    {"id": "components",    "name": "Phase 1 — components: registry over the whole tree, order chosen", "kind": "author",   "actor": "coordinator", "body": "phase-1-components"},
    {"id": "ownership-gate","name": "Ownership gate — every code file owned or unassigned with reason", "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "phase-1-components"},
    {"id": "draft",         "name": "Phase 2a — draft one component's capabilities and rules",          "kind": "author",   "actor": "coordinator", "body": "phase-2a-draft-one-component"},
    {"id": "surface-gate",  "name": "Surface gate — every surface it owns is described or excused",    "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "phase-2a-draft-one-component"},
    {"id": "review",        "name": "Phase 2b — batch review with the person; mint what survives",     "kind": "decision", "actor": "coordinator", "body": "phase-2b-review-and-mint"},
    {"id": "areas",         "name": "Phase 3 — feature areas from the confirmed capabilities",         "kind": "author",   "actor": "coordinator", "body": "phase-3-feature-areas"},
    {"id": "journeys",      "name": "Phase 4 — journeys and their acceptance criteria",                "kind": "author",   "actor": "coordinator", "body": "phase-4-journeys"},
    {"id": "qa-readiness",  "name": "Phase 5 — QA readiness: validators green, promises counted",      "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "phase-5-qa-readiness"},
    {"id": "land",          "name": "Update the progress file and land the step",                      "kind": "io",       "actor": "coordinator", "body": "land-the-step"}
  ]
}
```

---

## How you ask

You ask the person through the interview card — always batched, always with your recommendation
first and a reason on every option:

<!-- include: process/interview-card.md -->

**When no person can answer live** (a non-interactive session, a person who said "later"), write
every question into the progress file's `## Open questions` in the same card shape, set the
phase or component to `awaiting-review`, land what you have, and **stop**. The next invocation
reads the answers from the file. A question is never answered by you on the person's behalf —
not with "the recommended option", not with "what the code does".

What is the person's to decide, and what is yours:

| Theirs — always ask | Yours — never ask |
|---|---|
| whether an observed rule is a **promise**, a bug, or an accident | which file a surface lives in, what a test asserts |
| the product's personas and the job each one comes to do | the component a directory belongs to, when imports make it plain |
| the order in which components are described | the noun phrase a capability is written in |
| a merge or split of components the code does not settle | whether a surface is reachable (read the router) |
| the feature-area taxonomy | the shapes, ids, and file layout |

---

## Before Step 0 — start from the default branch as it is now

The bootstrap describes the repository `fleet init` prepared, and the documented order runs
`fleet init` and this command in a row. `fleet init` opens a pull request. Do not build on the
branch that pull request carries: a squash merge rewrites that branch, and a branch cut from it
conflicts as soon as the init pull request lands.

0.1. **Check the base.** Run `python3 knowledge/scripts/kb_base.py`. It fetches `origin`, reads
   the repository's default branch, and checks that `fleet init`'s files are committed there.
0.2. **If it exits `3`, stop.** It prints `merge the `fleet init` pull request first` and names
   the missing files. Tell the person that sentence and the pull request to merge. Do not write a
   knowledge file, and do not start from the branch that pull request carries. Any other
   non-zero exit means the check could not run: report its message and stop. Do not guess a base.
0.3. **If it exits `4`, the checkout is behind.** Rebase onto the ref it prints
   (`git rebase <ref>`) before writing anything, so the step starts from the default branch as it
   is now.
0.4. **When this invocation starts a step, cut its branch from the ref it prints**
   (`git fetch origin && git checkout -b <branch> <ref>`). Never cut from the branch `fleet init`
   left, and never from a checkout made before its pull request merged. When the step already has
   an open pull request, keep its branch and rebase it onto the ref before updating the pull
   request (*Land the step*). With no `origin`, the script prints `no origin`; commit locally, as
   step 3 of *Land the step* says.

## Step 0 — Resume

1. Read the progress file (`kb_inventory.py layout` prints where every artifact lives). **Absent → this is Phase 0.**
2. **Staleness — the code moved since a part was described.** Re-scan the inventory
   (`kb_inventory.py scan`), then for each component with a `Read at`:
   - `git diff --stat <read_at> HEAD -- <its owns paths>` — its own code changed;
   - `kb_inventory.py coverage --component <id>` lists an undescribed surface — something new
     reaches it from code it does not own (a route added to a shared spec or handler package).
   Either marks it `stale`. A stale **confirmed** component is re-read before any new work, and
   only the delta is drafted: new or changed capabilities and rules go to the person as one
   small review; a change that **contradicts an adopted promise** is never applied to the
   register silently — it is put to the person as a proposed supersession (keep the promise and
   file the change as a defect, or supersede the row), because the code changing is not the
   person deciding. Every answer already given stands.
3. **Answered questions first.** An `## Open questions` entry with an answer is applied now —
   move it to `## Answers` with what it changed — before any new work.
4. Pick the step: the argument if one was given; otherwise the first of — a `stale` confirmed
   component (→ re-read), a component left `drafted` whose `## Unread` still names a directory or
   file it owns (→ continue that draft), a component in `awaiting-review` whose questions are
   answered (→ review), a phase that is `ready` for the confirmed slice, the next component in
   the person's order that is `not-started` (→ draft).
   A `drafted` component with unread parts is always continued before any new component is
   started: the next default run reads the parts still named under `## Unread`, never a
   `not-started` component, until the whole component is read. Once `## Unread` no longer names
   a directory or file it owns, the component moves to review instead.
   - Phase 3 is `ready` whenever a confirmed component's capabilities sit in no settled area.
   - Phase 4 is `ready` whenever a settled area has confirmed capabilities no journey covers.
   - Phase 5 is `ready` whenever Phase 3 and 4 have caught up with the confirmed slice.
   So the first ordered component goes all the way to QA-checkable promises before the second
   is drafted — a thin slice that runs end to end, then the next.
   **`start <what>`** on a repository with no progress file records the person's words as the
   first answer and runs Phase 0; Phase 1 then makes the named part (and only it) the order.
   **`add <id>`** appends a component to the order; its row's waiting questions are asked with
   its draft.
5. `status` leads with **the readiness verdict** — `python3 knowledge/scripts/kb_readiness.py`,
   printed as it comes: ready to build or not, what stands in the way, and the parts to describe
   next — then the Phases and Components tables, the open-question count and the coverage line
   (`python3 knowledge/scripts/kb_inventory.py coverage | head -2`), and stops. The same reading
   heads the Knowledge page in Fleet; the script adds what only this checkout knows (the parts
   that changed since they were read, the questions still waiting).

## Phase 0 — Survey

Mostly yours; one round of questions at the end.

1. **Slots.** Run the slot survey (`fleet slots --repo .`, or
   `python3 knowledge/scripts/fleet.py slots --repo .`). For each mechanical slot `fleet init` left as a
   stub — `languages`, `gate`, `codegen`, `dev-environment`, `git-workflow`, `file-conventions` —
   read the answer off the repository (its own build scripts, CI workflows, package manifests,
   generator configs, the README) and write its `## Answers` list. Cite the file each answer came
   from. A slot the repository genuinely does not answer stays a stub, and you say so.
   **Targets.** Then the `[fleet.targets]` table in `.fleet/fleet.toml`: for each conventional
   target stack detection left unset — above all `lint`, `test-unit`, `test-one`, `build`,
   `generate` and `dev` — write the command this repository really runs for it, taken from its CI
   workflow first (what CI runs is what green means), then its build scripts, and run each one
   once to prove it. A target the repository has no command for stays unset — it renders as a
   refusal, which is honest — and you say so; never invent one. Re-sync the tier afterwards
   (`fleet commands sync --repo .`) so the commands name what runs here.
2. **Inventory.** `python3 knowledge/scripts/kb_inventory.py scan`. Read the detector line: a
   stack whose router, schema or CLI the scanner does not recognise reads as zero. **A zero you
   did not expect is a detector miss, not an absence** — find the real route table / schema /
   entry points by hand and list them under `## Manual surfaces` in the progress file, with
   `file:line`, so later phases count them.
3. **Read the framing.** The README, top-level docs, the API spec's descriptions, the UI's
   navigation. Draft a one-paragraph product statement and the personas you can see evidence of
   (login roles, permission names, separate apps).
4. **Ask, once, batched:** confirm or correct the product statement and the persona list (who
   uses it, and the one job each comes to do). Write the answer into
   the product vision (`slot:product-vision`, `layout: product-vision`) — the person's words, not yours.

5. **Seed the files the validators expect** even when empty: the capability alias ledger (`layout: capability-aliases`)
   (a header and an empty alias table — `validate_journeys.py` refuses a corpus without it).

Phase 0 is `done` when the inventory exists, every mechanical slot and gate target is answered or
explained, and the personas are confirmed.

## Phase 1 — Components

1. **Propose layers first** (4–10): the blocks the architecture would be drawn in. Read them off
   the shape of the system — entry surfaces, the domain core, data, integrations, foundation.
2. **Propose components** from the inventory's units. A component passes both tests in
   [the knowledge model](../../../process/knowledge-bootstrap-formats.md#3-component-registry--specsarchitecturecomponentsmd):
   it **owns** nameable code, and it would be **drawn once**. Evidence to use: binary and package
   boundaries, import graphs (who imports whom gives `depends_on`), table prefixes, API tag
   groups, UI route groups. Group by what changes together, not by directory depth — a backend
   package, its SQL queries, its API handlers and its UI page are often **one** component.
   **A UI page belongs to the domain it serves, not to "the web app".** A frontend is a
   directory, not a subsystem: claim each page directory, hook and API client for the component
   whose surfaces it drives, and leave the shared shell (routing, layout, design system) as the
   frontend's own component. A single horizontal `web-app` owning thousands of files hides every
   page from the component that promises its behaviour.
   **A merge is a decision, the same as a split.** When you fold a package that has its own
   noun, its own tables or its own API group into a neighbour (a credential vault into
   integrations, a reasoner into the ontology), list it among the uncertain components and ask —
   never merge silently.
3. **Routes declared centrally are claimed by prefix.** When one spec file or one handler
   package declares the whole API, no file path says which component a route belongs to. Write a
   `## Surface ownership` table in the registry (component · comma-separated route prefixes); the
   inventory counts a route by its longest claimed prefix, then by its handler's file
   (`handler` in the inventory, resolved from the `operationId`). Never count routes by hand.
4. **Every code file is owned** — by a component or by a `## Unassigned code` row with a reason
   (generated output, one-off scripts, vendored tooling). Run
   `python3 knowledge/scripts/kb_inventory.py coverage`; the **ownership gate** passes at ≥ 95% of
   code files owned and every unowned unit listed with a reason.
5. **Ask, once, batched — and only what the ordered parts need:** the layers; a merge or split
   the code does not settle **only where it touches a part the person has ordered** (name both
   readings and what each would mean); and, when no part was named at `start`, **the order** —
   recommend the parts in the order `python3 knowledge/scripts/kb_readiness.py` lists under
   *Describe these next*: ranked by how much of the team's recent code change lands on each, so
   the fewest parts reach the point where the knowledge base is ready to build on. Code the map
   gives no part shows there by its directory; give it a part (or an `## Unassigned code` row
   with its reason) before it can be described. Every other
   uncertain boundary is written on its component's row (`Waiting questions`) and asked when that
   component is ordered, never now: a customer who said "start with bug tracking" is not asked
   about the credential vault. Components outside the order stay `proposed`.
6. Write the registry (`layout: components`), name it as the `components` slot's fill in the
   slot registry, and write the Components table in the progress file (one row
   per component, `Order` from the answer, surfaces counted from the inventory).

## Phase 2a — Draft one component

The loop unit. One component per invocation. **A component is drafted only after the whole of it
has been read**: every file the inventory attributes to it, not only the files that carry a
surface. A component too large for one pass is split into passes: stop at a clean boundary, write
the directories and files still unread under `## Unread` in the progress file, leave the component
`drafted` (never `confirmed`), and the next invocation continues from there. Every capability name
and rule this phase writes follows the plain-language rule in
[`process/writing.md`](../../../process/writing.md) → *Write for a reader who does not know
the code*, as well as *Wording a promise*.

1. **Read the ground — by fan-out, never by sampling.** Reading is a deterministic procedure, not
   a judgement about which files look important. Reading six files of a component of hundreds is a
   failure of this step, whatever the draft then claims.
   1. **Plan.** `python3 knowledge/scripts/kb_inventory.py batches <id>` lists EVERY source file
      the component owns — code, **tests**, ZK pages, GraphQL schemas — minus only mocks, fixtures,
      test data, generated and vendored files, and splits them into batches of at most 40 files
      and 400 KB. It writes the plan to the run state. You do not choose, trim or reorder it.
   2. **Fan out: ONE sub-agent per batch, using the Agent (Task) tool.** Start them in parallel,
      several per message. Give each sub-agent its batch id and its exact file list from the plan,
      and tell it to open and read every file in full, then return (a) the capability and rule
      candidates it found, each with `file:line` evidence and the test that exercises it, the
      suspicious behaviour it saw, and (b) **the exact list of files it opened**, one path per
      line. A sub-agent does not write the corpus and does not read outside its batch.
   3. **Record.** For each returned batch, pipe its file list to `kb_inventory.py record <id>
      <batch-id>` (paths on stdin). A path the batch does not contain is refused and printed; a
      sub-agent that returned fewer files than its batch holds leaves that batch open. Note each
      batch's state (done / open) in the progress file's row for the component.
   4. **Re-dispatch** a sub-agent for every batch still open. Repeat 2-3 until
      `kb_inventory.py coverage --component <id> --gate` exits 0.
   5. **Merge.** Only now do you, the main agent, merge the sub-agents' findings into the
      capabilities, rules and suspicions below, de-duplicating across batches. The findings are
      evidence; the writing, the sizing and the plain-language rule are yours.

   `coverage --component <id>` also lists the surfaces and the directories no feature map reaches.
   **Read the tests as closely as the code** — a test is the strongest evidence that a behaviour is
   intended. A detector that reports 0 surfaces is a detector miss, not an absence: the files are
   still the ground.
2. **Capabilities.** One row per durable thing the product can do, as a noun phrase, sized like
   *"Dense vector search"* — not *"Search works"* (too big), not *"The save button is enabled"*
   (too small), not *"Let an admin narrow a profile"* (a task, and a verb). Several surfaces
   usually make one capability (list, get, create, update of one resource are rarely four). Each
   row names its **evidence** (`file:line` or the surface) and the **test** that exercises it, or
   `—`. Give it a provisional area name — Phase 3 settles areas. Write it as that name plus one
   plain sentence on what a person can do with it, worded to [*Wording a promise*](../../../process/knowledge-bootstrap-formats.md#wording-a-promise--every-capability-rule-and-criterion).
3. **Rules.** Every *"the system shall / never …"* the code enforces: authorization checks,
   validation and its error, uniqueness and integrity constraints, state-machine transitions that
   are refused, limits and quotas, isolation boundaries, idempotency, audit writes. Each with its
   evidence and a **Confidence** of `tested`, `enforced` or `observed`. Prefer fewer, sharper
   rules a QA run could falsify from outside over many restatements of the code. Word each one to
   [*Wording a promise*](../../../process/knowledge-bootstrap-formats.md#wording-a-promise--every-capability-rule-and-criterion): one plain sentence, code names and tunable numbers in Evidence.
   **How to find what the routes do not show** — each of these was a measured miss:
   - **Routes are not the whole surface.** A function of this component that *another*
     component calls is a capability candidate too (an "explain what this reaches" helper, a
     compatibility check another service runs before binding). List the component's exported
     entry points that have callers outside it, and describe the ones with product meaning.
   - **Walk every guard on the request path.** Each early return with a refusal in a handler or
     the functions it maps the request through — screens, rejections, `require…` checks,
     sentinel errors — is a rule candidate. A guard in the handler is as much the component's
     promise as one in its package.
   - **Follow every reader of a policy or setting** before writing the rule it implies: if a
     "changes need approval" switch also gates a second path, the rule names both.
   - **Copy the exceptions out of the predicate.** A rule read off a query carries its filters
     (*"…unless the agent is archived"*); a rule without them is wrong in exactly the case QA
     will hit.
   - **The schema is a rule source.** Every CHECK, UNIQUE and NOT NULL constraint, and every
     length or size limit in the schema or the API spec, is a rule candidate — and a limit on one
     side the other side does not respect (a client that can send more than the server accepts)
     is a suspicion.
   - **Write down what leaves the system.** For every call to an outside system (a tracker, a
     mail provider, a model), list the fields actually sent and write one rule about what never
     leaves (*"nothing identifying the reporter is sent to the tracker"*). For every staff or
     operator view, write down what it deliberately leaves out.
   - **Trace every caller of a data-changing entry point**, including wiring in other packages
     and scheduled jobs. A second path that reaches the same mutation is where a rule quietly
     stops holding.
   - **Read the door before the rooms.** The middleware on the component's mount (who is let
     in, which tenant state is refused, the size cap, an exact-path mount) is the component's
     first set of rules. Then check where each "every call is audited / traced" rule sits in the
     middleware order: a refusal raised *before* the writer is never recorded.
   - **Walk the verbs that skip the main path.** Protocol-level operations — an HTTP DELETE or
     GET on a session, a cancellation, a notification — often bypass the chain the main calls go
     through. For each, find the ownership or scope check the main path relies on; its absence
     is a suspicion.
   - **Check a capability belongs here.** A row whose evidence lives in another component's
     paths is that component's; note it for that component's draft instead.
4. **Not described.** Every surface owned by this component that no capability covers goes under
   `## Not described (with reason)` — debug, internal-only, deprecated, substrate. The **surface
   gate** passes when every surface is covered by a capability or excused there **and**
   `kb_inventory.py coverage --component <id>` lists no unread directory or file for it. A
   hand-listed surface never covers a directory. When the detector reports 0 surfaces, the gate
   is met only by reading the component's files and claiming their paths in the map's
   `source_of_truth:`.
5. **Suspicious.** Behaviour that looks like a bug (a check that contradicts its test, a
   permission missing on one verb of four, a TODO that disables a guard) goes under
   `## Suspicious` — never into a rule. Before filing one:
   - **prove the bad branch can run** under the pinned toolchain and library versions — a
     "fails open on error" whose error the library can no longer return is a misread;
   - where the code has **optimistic concurrency and a pending or approval state**, check the
     version guard covers the pending rows too — two pending changes from one base is the
     classic lost update;
   - a **user-facing message that contradicts a rule** you are drafting (an error text that
     still promises the old behaviour) is a finding of its own.
   - **state the conditions under which it fires** (which status, which role, which window) — a
     suspicion without them is either overstated or unreproducible;
   - **state the least privilege it needs**, through the permission contract to the roles that
     hold it, and — when it needs an identifier — every surface that reveals that identifier and
     who can see it. That is what lets the review rank a suspicion;
   - **close a conditional suspicion from the schema first**: whether a row can carry a value is a
     constraint to read, not a question to file.
6. **Check every anchor** you cite: the file exists, the line exists, the symbol is on it. A
   cited test is checked the same way — by its file and function name, never by recollection.
7. **When the corpus already describes this ground** — a repository with a partial knowledge
   base, or a re-run after the code moved — read every existing capability row, requirement row
   and journey criterion that touches this component and add a `## Against the existing corpus`
   section: each row marked `agrees`, `contradicted` (with the code line that contradicts it) or
   `not found`, and each draft row the corpus lacks. A contradicted row is never edited here; it
   goes to the review as a proposed supersession, because an adopted promise changes only on a
   person's word.
8. Write the draft (`layout: drafts`); set the component `drafted`, its `Read at`, its
   counts. **If any owned directory or file is still unread, write it under `## Unread` in the
   progress file and stop at that clean boundary** — the next invocation continues from there.
   If a person is present, continue straight into 2b; otherwise write the review into
   Open questions and set it `awaiting-review`.

## Phase 2b — Review and mint

1. **One batched review per component.** Present the capabilities and the rules as tables the
   person can mark `keep` / `drop` / an edited statement — rules grouped by Confidence, `observed`
   ones flagged *"likely accidental — keep only if you would call a change here a bug"*. Present
   `Suspicious` separately: each becomes a Finding, or (the person's call) a rule after all.
   **Do not ask about capabilities the evidence makes plain** — list them as "keeping these
   unless you object"; spend the person's attention on the rules and the uncertain rows.
2. **Mint only what survived.** Capabilities into `features/<provisional-area>.md` with fresh
   `CAP-NNNN` ids and `Ships in: (shipped)`; rules into `requirements/<domain>.md` as `adopted`,
   with `Source` citing the evidence and the question that confirmed them. Dropped rows are not
   written anywhere but the draft's Verdict column. Add the component's paths **that were actually
   read** to the area's `source_of_truth:` and its routes to `surfaces:`. A path named under
   `## Unread` is never claimed here: the map says what was read, not what the component contains.
   Every map this writes or touches carries a
   brief and has its rows under its uses, per [*Writing a feature brief*](../../../process/feature-doc-reconcile.md#writing-a-feature-brief--every-map-that-is-created-or-edited) — on a provisional area, drafted from the
   capabilities just confirmed; Phase 3 confirms them.
3. The first time a feature map, a register or a journey is written, name its directory as the
   fill of the `feature-maps`, `commitments` or `journeys` slot in the slot registry, so every
   other command reads the corpus this one writes.
4. Run `python3 knowledge/scripts/validate_requirements.py` and
   `python3 knowledge/scripts/validate_journeys.py`; fix every finding about a file this step
   wrote. **The unclaimed-code-path finding is expected until Phase 5** — `validate_journeys`
   requires every path under its coverage roots to be claimed by some feature map, and a
   half-described repository cannot meet that. Record its count in the progress note (it must
   fall with every confirmed component), and never answer it with a baseline file.
5. **The read gate.** Run `kb_inventory.py coverage --component <id> --gate`. While it exits 1 it
   prints `NOT DONE: N of M files of <id> are unread` — say exactly that to the person, name the
   open batches, and do **not** set the component `confirmed`, call it done, or call it QA-ready.
   Set the component `confirmed` with its counts only when the gate passes. **Never confirm a
   component while `## Unread` names a directory or file it owns.** A partly read component stays
   `drafted` and the next invocation dispatches the open batches.

## Phase 3 — Feature areas

Ready whenever a confirmed component's capabilities sit in no settled area — after the first
component, and again after each later one.

1. Propose the areas **bottom-up from the confirmed capabilities**. When areas already exist,
   place the new capabilities into them first and propose a new area only for what fits none;
   never redraw a settled taxonomy unasked. Each area passes the customer
   test (*would a customer name this when describing what the product does?*). Work that fails it
   is a `kind: substrate` area, said plainly.
2. **Ask, once** (a use is named with a verb first and gets one plain paragraph; a capability that fits no use waits under `### Misfits (to move)` and is named in the question, per *Writing a feature brief* moments 1-3): the taxonomy, with the capabilities each area would hold — and, in the same
   question, each area's one-sentence brief `summary` and its uses with the rows under each.
   Moving a row later is cheap — ids are opaque and global — so recommend the simplest split that
   passes the test.
3. Move rows into their areas and under their uses (a move keeps its id), write each map's
   `Intent` sentence and its brief ([*Writing a feature brief*](../../../process/feature-doc-reconcile.md#writing-a-feature-brief--every-map-that-is-created-or-edited)), and answer the `feature-areas` slot.

## Phase 4 — Journeys

Ready whenever a settled area has confirmed capabilities no journey covers. A later run extends
an existing journey (new criteria are **appended**, never renumbered) or adds a new one.

1. For each confirmed persona, propose the jobs they come to do — each starting from a real
   trigger, not mid-system — and the capabilities each would walk (`covers:`).
2. Draft each journey's happy path from the actual UI and API, and its **acceptance criteria**:
   each one observable from outside the code, each one a promise (`<slug>#<n>`), worded to
   [*Wording a promise*](../../../process/knowledge-bootstrap-formats.md#wording-a-promise--every-capability-rule-and-criterion).
3. **Ask, batched per area:** which journeys are real, and keep / drop / edit per criterion —
   the same promise test as rules. Write the confirmed ones; set `Tested by` on the capabilities
   they cover, and draw each covered map's brief `example` from a confirmed journey, its slug in
   `example_from`.

## Phase 5 — QA readiness

The gate that says the confirmed slice delivers what the bootstrap is for. It runs after the
first part is described and again after each later one.

0. **A part counts as QA-ready only if** `kb_inventory.py coverage --component <id> --gate` exits 0
   for it. Re-run it for every confirmed component here; one that prints `NOT DONE` goes back to
   `drafted`, whatever its counts say.
1. **Ratchet the coverage roots** to the owned paths of every confirmed component
   (`[fleet.structure] coverage_roots` in `.fleet/fleet.toml`), then `validate_requirements.py`
   and `validate_journeys.py` green — including the unclaimed-path gate over those roots: every
   path of a described part is claimed by a feature map's `source_of_truth:`.
2. **Count the promises the QA Desk will see**:
   `python3 knowledge/scripts/count_promises.py`
   — and report them by family (capabilities, register rows, journey criteria).
3. `kb_inventory.py coverage`: owned files, described surfaces and the directories still unread,
   overall and per component. Then `kb_readiness.py`: report the verdict with what stands in the
   way, and when it is not ready, recommend the next part from its *Describe these next* list. A
   part read only in part keeps the verdict "not ready" and names the directories and files
   nobody read. Ready to build is the point the person can start planning work on top of the
   corpus; until then each confirmed part moves the number, and the progress note records it.
4. An environment record for the QA Desk to run against (`knowledge/environments/<id>.json`) —
   ask the person which environment QA may drive and whether it may write there. **Recommend the
   least consequential environment that can prove the promises** — a local or test stack before
   any shared one, and never a production write that reaches a real outside system (a tracker, a
   mailbox) as the default. Name each credential by the secret that holds it, never its value.
5. Write the numbers into the progress file. Phase 5 is `done` **for this slice** only when every
   confirmed component has no unread directories or files; it turns `ready` again when the next
   component is confirmed.

## Land the step

1. Update the progress file: the phase/component state, `At commit` / `Read at`, counts, open
   questions, answers, findings. It lives under `.claude/run/knowledge-bootstrap/` (run
   `kb_inventory.py layout` for the exact path), which git ignores.
2. **Confirm every corpus file the step wrote is tracked** (`git status --porcelain --ignored` on
   them): a repository's ignore rules can swallow a register or a map silently, and an ignored
   promise is one the QA Desk never sees. Add the narrowest exception and say so. This does not
   apply to the progress file, drafts or the inventory: those are the bootstrap's own run state,
   and they must stay untracked.
3. Commit **the corpus files the step wrote** as one commit
   (`docs(knowledge): bootstrap <phase or component>`). Never add the progress file, the drafts
   or the inventory — they are working notes, and a commit or PR that carries them is exactly
   the "useless info" this command must not produce. **Then put the commit on a current base.**
   Run `python3 knowledge/scripts/kb_base.py` again: exit `3` → stop and tell the person to
   merge the `fleet init` pull request; exit `4` → `git rebase <the ref it prints>`. A pull
   request that conflicts never runs its checks, and a branch cut before the `fleet init` pull
   request merged is the conflict this check exists for. With an `origin`, land the commit
   through the repository's `git-workflow` slot — a branch and a PR per step; a small PR per
   component is the unit a reviewer can actually read. With no `origin`, commit locally.
4. Tell the person, in three lines: what this step did, what it asked or is waiting on, and what
   the next invocation will do.

---

## Rules

- **Draft from the code; promise only on a person's word.** No requirement row, journey criterion
  or capability is minted without a review answer. A headless session parks questions; it never
  answers them.
- **One step per invocation**, landed with the corpus files it wrote; its own run state stays in
  `.claude/run/`. Never two components in one run.
- **A component is QA ready only when the whole of it was read.** A pass over part of a large
  component leaves it `drafted` with the unread directories and files named under `## Unread`;
  it never becomes `confirmed`, and the readiness verdict stays "not ready". A detector that
  reports 0 surfaces is a miss, not an absence: hand-listing a few surfaces never covers a
  component.
- **Every number is re-measurable.** Counts come from `kb_inventory.py`, never from your reading
  of how much you covered.
- **Ids are minted at confirmation, never at draft**, and never reused or renumbered.
- **A bug you find is a Finding, never a promise and never silently dropped.**
- **No programs, slices or PRDs.** Those are versioned plans for future work; existing code is
  described as `(shipped)`. The person starts planning on top of the corpus afterwards.
- **No ship-state on anything durable** — no status column on a component, area or journey.
