---
type: spec
---

# Command Spine (the structure of our `/:*` commands)

This spec is a **structural convention over the command tree**, a sibling of the typed-files
rule a repo states in its `file-conventions` slot, and of the SOP↔command two-tier model. It
defines the small vocabulary we use to describe *how a command runs* — its ordered **steps**
and their metadata — so those steps become inspectable, enforceable, and todo-trackable
instead of implicit prose.

> **Not a product's ontology.** "Ontology" is a **product** word in some of the repositories
> this tier ships into — a workspace meta-model of types, attributes, links and row policies
> describing a *customer's* data, which a repo names in its `domain-model` slot. This spec is
> about *our dev commands*. No shared vocabulary, deliberately — which is why it is a
> **spine**, not an ontology.

## Where it sits

Two tiers already exist: an **SOP** is the human-readable procedure; a **`/:*` command**
is its automated subset. What was
missing is the layer *below* the command — the ordered **steps** it runs, and their
metadata (which model, coordinator or sub-agent, is this a hard gate, what does it
produce). This spec adds that layer. It does not replace the command's prose; the prose
stays the authority a human/agent reads at runtime. The **spine** is a structured
table-of-contents over that prose: enough to generate a todo list, enforce cross-command
policy, and answer "which steps are gates?" as a query.

---

## The vocabulary (three entities + one enum)

### Command

One `/:*` command (equivalently, the automated subset of one SOP). A command
**owns an ordered list of steps**.

| Field | Meaning |
|---|---|
| `command` | stable id, kebab-case, matches the command path (`prd-design`, `prd-plan`). |
| `intent` | one line — what running it accomplishes. |
| `scope` | `portable` (the default, and omitted) \| `product` — see **Scope** below. |
| `owner` | the one repository a `scope: product` command belongs to. Required with it, meaningless without. |
| `sop` | `none`, or the `slug:` of a shared-tier document this command automates (a register or a process doc). Resolved by `command-contracts`; a repository's own SOP is not the tier's to name. |
| `needs` | what the command needs **from a person** to complete: `nothing` \| `answers` \| `a decision` — see **What a command needs, and what it may merge** below. |
| `may merge` | `true` if this command is permitted to merge its own work, else `false`. The JSON key carries the space — `"may merge"`, not `may_merge` — so the field is spelled the same here, in the spine an author types, and in the reader. |
| `loads` | **slot ids** the command force-loads IN FULL at start, as opposed to consulting when a step needs them. Must be a subset of `requires` ∪ `optional`. |
| `requires` | **slot ids** the repo MUST have filled for this command to run. A command whose repo leaves one empty does not run here — see the repo's own slot registry. |
| `optional` | **slot ids** the command uses when present and degrades without, in the way that slot's `degrade` field names. |
| `steps` | the ordered `Step` list (below). |

**`loads` names slots, not files.** It used to name documents — `product-vision`,
`tracking-and-execution`, `backend-implementation-contract` — which are one repository's
filenames, in the one block of a command that is supposed to be machine-readable and
portable. Three lists then said overlapping things about the same command and nothing kept
them in step. Now `loads` is a *subset* of the two slot lists, carrying the one extra fact
neither of them holds: which of the declared slots is read cover-to-cover before step 1,
rather than opened when a step reaches for it.

### What a command needs, and what it may merge

**These were one boolean, and one boolean could not be right.** `autonomous: true|false`
was read as *the fleet dispatches this* and written as *this does not ask* and used as
*this is allowed to finish the job*, and those are three different claims about a command.
So thirty-seven spines carried a flag that was **wrong in both directions at once**:
`slice:create` said `true` while carrying the interview card and asking; `prd:plan` said
`false` while containing no question at all; `prd:design` (eleven question points) and
`program:ship` (four mechanical gates that ask nobody anything) said the same word. A field
whose value you cannot predict from the command's own text is not a declaration, it is a
label, and the fleet was keying dispatch on a label.

Two fields, because there are two independent facts:

**`needs` — what a person has to supply before this command can finish.** Read it off the
command's own body, never off what the old flag said.

| value | means | the test |
|---|---|---|
| `nothing` | it can finish unattended. Nobody has to be there, and nothing is parked waiting for a person. | Could this run to its terminal state at 3am with no human awake? |
| `answers` | it stops and interviews. It runs, gets somewhere, and needs a person's words to go further — at a terminal through `AskUserQuestion`, headless through the written question channel. | Does it ask a person anything, in any mode? |
| `a decision` | it cannot proceed without a human **ruling**. The product of the command IS the human's call; with nobody attached there is nothing to do but print the queue and stop. | With no human, does it have *any* work? |

**`needs: answers` is not `needs: a decision`.** The fleet dispatches a command that asks
— it runs, it parks the question where a person will find it, and it resumes on the answer.
What the fleet will not dispatch is a command whose whole product is a ruling, because a
headless run of one is a session that starts, finds nobody, and ends. That distinction is
what the boolean could not hold, and it is why the fleet's attendance policy now reads this
field: **a step the fleet declines to run unattended is a stated choice, in the command's
own spine, rather than an absence from a list somewhere in the service.**

**A command carrying the interview card cannot say `needs: nothing`.** The card
(`<!-- include: process/interview-card.md -->`) is the bar a question has to clear before
it is put to a person; a command that inlines it is a command that asks. That is the exact
defect class that produced the wrong flags, so it is checked rather than remembered.

**`may merge` — whether this command may merge its own work.** The law is *the party that
wrote the code never certifies it*, so the answer is `false` for every command that
produces work, and `true` only for:

- **the verify gates** — `verify` and `prd:verify`, whose whole job is the certification the
  merge rides on, and `push`, which is the mechanism they merge *through* and is called by
  them rather than by an implementer;
- **the document-authoring commands** that open a PR carrying only their own written
  artifact and self-merge it. A register row, a PRD stub, a spec: there is no code to
  certify and no second party the law was written to protect.

Everything else **hands off** — it opens a green PR and stops, leaving the merge to somebody
who did not write it. Which handoff depends on what the run has: an issue it was given goes to
the review state and the fleet dispatches a verifier at it; an issue it filed itself stays in
the check-gate state, because a filer sets no priority and moving one out of that window reds
every open PR on the partition guard; and a run with no issue at all hands the **person who
started it** the PR link and says plainly that nothing is armed.

`arch:reconcile`, `page:improve` and `sidekick` are the three that used to merge their own
work and no longer do. **The list above is closed, and it stayed closed**: `sidekick` was the
one real candidate for an exception — it fixes contained findings in a worktree with the human
sitting right there — and the ruling was that this is not an exception at all. The writer
stops and a person decides; a human in the room is what makes stopping *cheap*, never what
makes self-certifying safe. So no command produces work and merges it, and a `may merge: true`
that a command's own recipe never exercises is the same untruth in the other direction — take
the permission away rather than leave it standing for the next author to spend.

### Scope

Most commands are **portable**: the same procedure, running against whatever the receiving
repository answered. A few are not, and pretending otherwise is worse than saying so.

- **`scope: portable`** (the default) — the procedure must reach every repo-specific answer
  through a slot. Naming a repository's own script, make target, corpus path or product
  vocabulary in one is an error, because the command ships into repositories where none of
  those exist.
- **`scope: product`** with an **`owner`** — the procedure is *about* one product and could
  not be meaningfully run anywhere else. `connector:build` is the case that forced the field:
  880 lines about one product's connector SDK, which was being written into all six lane
  repositories, five of which can never run a line of it.

A product command is **not synced outside its owner**. `fleet commands sync` skips it, so an
agent reading `.claude/` in another repository does not find a procedure it cannot run, and a
repo bootstrapped by `fleet init` starts with a tree that is entirely applicable to it.

The declaration is what earns the exemption. `scope: product` without an `owner` is an error,
not a wildcard: a command that claims to belong to one repository has to say which.

**`owner` is the repository's name as `fleet commands sync` derives it: the last path segment
of `git remote get-url origin`, minus `.git` — never the checkout directory.** The repository
this tree was written in is cloned as `-5` on the machine that authored it and is
`` to the sync; an owner written from the directory name would match no repository and
the command would be synced nowhere, silently. There is one worked value in the tree
(`connector:build` → `owner: ""`); copy its derivation, not its spelling.

### Running a script or a gate — the fixed layout

A command may need the repo to *run* something. It names the thing it runs **outright**,
because the layout is fixed and the tooling ships with the tier:

- **A shipped script** lives at `knowledge/scripts/<name>.py` in every repository the tier
  syncs into — the same files, at the same path, generated-and-verified like `.claude/`. A
  command spells the whole invocation: `python3 knowledge/scripts/component_of.py <path>`.
  What differs per repository is read by the script from the repository (its remote, its
  config, its corpus), never spelled in the command.
- **A gate or a lifecycle action** — lint, the unit lane, codegen, bringing the stack up — is
  a **conventional `make` target**: `make lint`, `make test-unit`, `make generate`, `make dev`.
  Every repository the tier ships into implements the targets it can (`fleet init` scaffolds
  the stub); a target a repository lacks fails loudly with `No rule to make target`, which
  is the honest outcome — a command that needs it cannot run there. The full list is
  `command-portability`'s (`MAKE_TARGETS`); a target outside it is an error.

The first version of this layer named tools by id and resolved them through a register, a
per-repository binding and a dispatcher — four hops to reach one script, and the hop that
went wrong (five of twenty-nine bindings) was invisible to every check because every check
was about the *shape* of the binding, not the thing bound. A convention has no binding to get
wrong, and a reader sees what runs.

A path the shipped layout does not provide — a repository's own script directory, a bare
script basename, a `make` target outside the convention — is an error in a portable command.

### A command's own state

Some commands keep durable state between runs — an `own` beat's charter, an audit
campaign's ledger, a ride-along's session log. That state is **not a slot** (the repo does
not answer it) and it must not be invented per command: three commands independently chose
three homes, two of them inside a directory the receiving repository reserves as its own,
all keyed on one product's retired name. The convention:

- **Checkout-scoped state** lives under `.claude/run/<command>/…` in the checkout, and the
  command creates the directory. A repository ignores `.claude/run/` in git; the tier never
  commits into it.
- **Checkout-independent state** — a charter that must survive a fresh clone — lives under
  `~/.claude/run/<repository>/<command>/…`, where `<repository>` is the name
  `fleet commands sync` derives (the same rule as `owner`), so two repositories' beats with
  one slug never collide.

A command names its state root with those two forms and nothing else.

### Citing a slot

A command may need one answer the repository owns — *how branches are named*, *the readiness
route*, *the retro directory for a task*. It names the **slot**, and the reader opens the
repository's fill for it (`knowledge/slots/README.md` says where each lives):

> The branch name follows `` `slot:git-workflow` ``. Probe the readiness route
> `` `slot:dev-environment` `` names before the browser pass.

Inside a fence the same placeholder convention applies: `<slot:dev-environment>`. A slot
the questionnaire does not define is an error. Anything a slot used to answer that a repo
*runs* — the lint command, the unit lane, the stack — is a `make` target now (above), never
a slot: a reader should never have to open a document to learn what to type.

### Step

One ordered unit of a command. The `body` anchor points into the command's own prose,
which remains the full instruction — the step record is metadata, not a rewrite.

| Field | Meaning | Required when |
|---|---|---|
| `id` | stable kebab-case slug, unique within the command. | always |
| `name` | human label. | always |
| `kind` | one of the **Step kinds** below. | always |
| `actor` | `coordinator` or `subagent` — who does the work. | always |
| `model` | `inherit` \| `sonnet` \| `opus` \| … — the model the actor runs on. | when `actor: subagent` or `kind: fanout` |
| `gate` | `hard` \| `advisory` — does failing it block, or just warn. | when `kind: gate` |
| `critique` | rubric id this step grades against (e.g. `design-fidelity-bar`). | optional; `gate` or `loop` only |
| `produces` / `consumes` | `Artifact` ids this step writes / reads. | optional |
| `loop` | `{ max_rounds: N, exit: "<condition>" }`. | when `kind: loop` |
| `body` | anchor into the command prose (`#phase-1-step-0`). | always |

### Artifact

A named work product a step reads or writes. Controlled vocabulary — extend it here, in
one place, so `produces`/`consumes` edges stay a closed set the validator can check:

`prd` · `design` · `ux-design` · `backend-plan` · `frontend-plan` · `reference` ·
`mockup` · `mockup-approved` · `page-spec` · `screenshots` · `baseline` · `journey` ·
`feature-map` · `acceptance-criteria` · `requirement-register` · `linear-issue` ·
`status` · `audit-record` · `check-result` · `tests` · `verified-status`.

**Approval artifacts** (`approval_artifacts` in the schema — today: `mockup-approved`)
are a distinct class: they record that a *human* signed off, and only a
`kind: gate`, `actor: user`, `gate: hard` step may produce one. A model's own critique
is never an approval, however rigorous the rubric.

The `produces`/`consumes` edges are the quiet payoff: a command that `produces` a
customer-facing artifact but no `ui`/`page-spec`, or an `acceptance-criteria` no step
`consumes`, is a queryable structural smell — the same class as our two recurring
failures (capability with no UX; shipped-but-not-connected).

### Step kinds (the enum — covers everything the commands actually do)

| kind | What it is | Typical fields |
|---|---|---|
| `author` | produce content interactively (design questions, plan tasks, PRD prose). | `produces` |
| `gate` | a pass/fail check that can stop the command. | `gate`, `critique` |
| ↳ *human gate* | a `gate` with `actor: user` — the command **stops and waits** for the human. Produces an `approval_artifact`. Never satisfied by a model self-critique. | `gate: hard`, `produces` |
| `fanout` | dispatch parallel sub-agents and synthesize. | `model` (required), `actor: subagent` |
| `loop` | bounded iterate-to-convergence (fix loop, fidelity loop). | `loop.max_rounds`, `loop.exit`, `critique` |
| `io` | a side-effect: commit, status-flip, file write, tracker mirror. | `produces: [status]` |
| `decision` | a branch (mode select, collision resolve) with a recorded choice. | — |

### `actor: subagent` means a real sub-agent — the coordinator doing it itself does not satisfy the step

The symmetric half of the human-gate rule above, and it is stated here because it was
**not** stated anywhere and a run duly skipped it. `actor: subagent` is a declaration
about **who**, not a hint about parallelism: the step is satisfied only by **dispatching
the work to a sub-agent via the `Agent` tool**. A coordinator that reasons through the
step inline and writes the same section has **not** performed it, however good the
reasoning — and must not mark it `completed`.

**The property being bought is independence, not speed.** For every critique-bearing
fanout (`red-team-critique`, `refute-passes`, `verify`), the whole point is that the
reviewer *did not author the thing under review*. A coordinator grading its own output is
exactly the arrangement CLAUDE.md's *"the party that wrote the code never certifies it"*
rule exists to forbid, and the measured cost of ignoring it is on the record: **82% of
PRDs were self-verified** before the split, and adversarial re-verification found **~1 in
2 shipped fixes did not fully address the issue they closed** — ungated. Gated, a `verify`
fanout turns back **9.3%** of what reaches it (53 of 571, measured →21), which is
what it caught and not what was there. A self-review substituted
for a panel reproduces that failure while looking like it did the work.

**If the sub-agent cannot be dispatched** — the harness forbids it, the tool is
unavailable, a session-level instruction conflicts — the step **fails**: its todo stays
open with the residual noted, exactly like a failed `gate`. Report it as *not performed*.
Do **not** substitute the coordinator's own pass and record it as done, and do not treat
the disclosure of a substitution as equivalent to performing the step; a disclosed weak
check is still a weak check, and it silently downgrades every gate downstream that was
entitled to assume an independent one ran. **A session-level "don't spawn agents"
instruction is a reason to stop and say so, never a licence to self-certify.**

---

## Runtime contract — materialize the spine as todos

Every command, at the moment it starts, **reads its own `steps` block and creates one
todo per step** (via the todo tool), in order, then marks each `in_progress` on entry
and `completed` on exit. A `gate` that fails or a `loop` that exhausts its rounds is a
todo that stays open with the residual noted — never silently closed. This makes the run
observable step-by-step (the reason we piloted on the human-driven PRD commands: you can
watch the todo list track the spine). Commands carry a one-line pointer to this contract
next to their spine; they do not restate it.

---

## Invariants

Two enforcers, because two different people fix what they find. The **repo-side** rules
(1–7 below) are enforced by the receiving repository's corpus validators — `make validate-knowledge` —
over the tree it received. The **tier-side** rules — spine lists (`loads ⊆ requires ∪ optional`,
unknown ids, `scope`/`owner`), tool-citation grammar, slot keys, `sop` and rubric resolution —
are enforced by `fleet check --only command-portability,command-contracts` over the tree as
authored, and gate every change to it.

The spine earns its keep only because something *reads* it. The validator parses the
spine block of every command — every command carries one — and fails the commit on:

1. **Model declared where it runs.** Every `fanout` step, and every `actor: subagent`
   step, declares a `model`. (Turns the buried "sub-agents run on Sonnet" prose into an
   enforced field.)
2. **Critique coverage — producing an artifact requires critiquing it.** Driven by the
   **critique-coverage map** (schema below): each rule says *producing any of these
   artifacts requires a critique step — a `gate` or a build `loop` — carrying this
   rubric*. Four rules are active: **rendered** UI artifacts (`mockup` / `screenshots`)
   require `design-fidelity-bar` (design **loops** to it, implement **loops** to it,
   verify **gates** on it); the `design` artifact requires `architecture-red-team` (design
   **gates** on it via the Phase 2c red-team); `tests` require `negative-control` (a test
   that cannot fail proves nothing); `verified-status` requires
   `independent-verification` (a status flip needs a reader with no stake in it).
   **`page-spec` is deliberately NOT in the fidelity rule**, though it once was: the bar
   grades a *render* against a design, and a page spec is intent→component prose with
   nothing to render, so the rule could only ever be satisfied there theatrically — and a
   gate that can only be faked is worse than no gate, because it teaches the next reader
   that the coverage map means nothing. Nothing loosens: `prd:design` authors a `page-spec`
   *and* produces `mockup` + `screenshots`, so the rule still binds it by the artifacts it
   was written for. **This is the generalization of the taste
   gate:** adding a rule (e.g. a new `agent` artifact ⇒ an eval rubric) is a **one-line map
   entry** — which is how the by-hand *missing-critique-gate* audit (architecture, API,
   agents) becomes a lint. Every `critique:` on a step must name a rubric registered in
   `critique_rubrics`.
3. **Gates are typed.** Every `kind: gate` declares `gate: hard|advisory`.
3b. **Approval coverage — producing a human-owned artifact requires a human gate.**
   Driven by the **approval-coverage map**: a command that `produces` a `mockup` must
   also `produce` `mockup-approved`, from a `kind: gate` / `actor: user` / `gate: hard`
   step. **This is the generalization of the taste gate's missing half.** Critique
   coverage (invariant 2) proves *something graded it*; approval coverage proves *the
   human saw it*. They are not substitutes: the design pipeline shipped for months with
   a model-graded fidelity loop and no human gate, while three downstream commands
   referenced "the approved mockup" that no step ever produced. A dangling approval is
   now a commit failure, not a recurring retro item.
4. **Anchors resolve.** Every `body` anchor points at a real heading in the command.
5. **Artifacts are in-vocabulary.** Every `produces`/`consumes` id is one of the
   Artifact set above.
6. **Ids are unique** within a command, and `kind`/`actor` are in-enum.
7. **Completeness — no prose↔spine drift.** Every prose `## Phase …` / `## Step …`
   section is indexed by at least one spine step (a step may index a *sub*-heading, so a
   finer step like a mid-phase gate still counts). A phase added to the prose but not the
   spine fails the commit. The spine may be finer than the prose, never sparser.
8. **The interview card is inlined, never cited.** A command that can put a question to a
   human — a step with `actor: user`, or `process-interview` in `requires`/`optional` —
   carries [`interview-card.md`](interview-card.md) **verbatim**, between
   `<!-- include: process/interview-card.md -->` and `<!-- /include -->`, at the point its
   first question is asked; and a command carrying the card declares the slot, so the
   declaration and the text cannot drift apart. `fleet commands sync` writes the block out
   of the one source copy; the validator fails a command that paraphrases it, edits it in
   place, or points at the protocol instead. **Why verbatim:** every summary of the
   protocol ever written into a command ("options, marked recommendation, rationale on
   every option") dropped the plain-words half, and the summary — not the file it cited —
   is what a model follows at ask-time. Measured: the rule was re-added by hand four times
   in four weeks while questions to the human stayed built from bare ids.

Invariant 2 is the whole reason this exists: it turns *"which commands are missing a
critique gate?"* — a question we answered by hand across architecture, API, and agents —
into a lint. Today the map guards UI; **each new coverage rule extends the same guarantee
to another dimension**, so a gap can never again be discovered six months late.

### Adding a critique rule (closing a missing-critique gap)

To make producing an artifact require a critique: (1) register the rubric in
`critique_rubrics` (`id → the spec/checklist that defines it`); (2) add a rule to
`critique_coverage` (`{produces: […], requires: <rubric>}`); (3) add a `gate` or `loop`
step carrying that `critique:` to each command that produces the artifact — the validator
then fails any such command that lacks it. The `design` ⇒ **architecture-red-team** rule
([`architecture-red-team.md`](../rubrics/architecture-red-team.md) — an independent critic argues the design is
wrong / names a stronger one) was the first extension beyond the UI taste gate, closing the
first row of the by-hand command-critique audit. **Candidate rules, not yet active** (the
rest of that audit): `backend-plan` ⇒ **API-ergonomics** (`api-quality-concerns.md`, which
already exists); an `agent-definition` artifact — not yet in the vocabulary — ⇒ **answer-quality** (the `audit-profile`
slot's eval checklist, today post-ship only). Each is a real run-cost — add where badness is both
likely and expensive, not reflexively.

---

## Machine-readable schema

`make validate-knowledge` reads this block as its schema (json, so the
stdlib-only verifier can parse it — same rationale as the typed-files rule); the tables above
are its prose companion. Keep the two in sync (the arch-docs freshness lesson — one file,
validated together).

```json
{
  "step_kinds": ["author", "gate", "fanout", "loop", "io", "decision"],
  "actors": ["coordinator", "subagent", "user"],
  "models": ["inherit", "sonnet", "opus", "haiku"],
  "gate_levels": ["hard", "advisory"],
  "artifacts": [
    "prd", "design", "ux-design", "backend-plan", "frontend-plan", "reference",
    "mockup", "mockup-approved", "page-spec", "screenshots", "baseline", "journey",
    "feature-map", "acceptance-criteria", "requirement-register", "linear-issue",
    "status", "audit-record", "check-result", "tests", "verified-status"
  ],
  "step_required": ["id", "name", "kind", "actor", "body"],
  "required_when": {
    "model": ["kind==fanout", "actor==subagent"],
    "gate":  ["kind==gate"],
    "loop":  ["kind==loop"]
  },
  "critique_rubrics": {
    "design-fidelity-bar": {"spec": ".claude/process/design-fidelity-loop.md §The design-fidelity bar"},
    "architecture-red-team": {"spec": ".claude/rubrics/architecture-red-team.md"},
    "independent-verification": {"spec": ".claude/rubrics/independent-verification.md"},
    "negative-control": {"spec": ".claude/rubrics/negative-control.md"}
  },
  "critique_coverage": [
    {"produces": ["mockup", "screenshots"], "requires": "design-fidelity-bar"},
    {"produces": ["design"], "requires": "architecture-red-team"},
    {"produces": ["verified-status"], "requires": "independent-verification"},
    {"produces": ["tests"], "requires": "negative-control"}
  ],
  "approval_artifacts": ["mockup-approved"],
  "approval_coverage": [
    {"produces": ["mockup"], "requires_artifact": "mockup-approved"}
  ]
}
```

## How to add a spine to a command

1. Add a `## Command spine (machine-readable)` section near the top of the command,
   holding a fenced ```json block (JSON, not YAML — so the stdlib-only validator parses
   it): `command`, `intent`, `sop`, `needs`, `may merge`, `loads`, `requires`, `optional`, the
   ordered `steps`, and — only where the command is bound to one repository —
   `scope: product` with its `owner`. Each step's `body` anchors an existing heading — the prose is
   unchanged; you are indexing it, not rewriting it.
2. Add the one-line runtime-contract pointer above the spine.
3. Run the repo's `` `make validate-knowledge` `` until clean.

## Related

- The repo's `file-conventions` slot — the sibling convention this mirrors (types over
  files; this is steps over commands).
- `knowledge/scripts/` — the shipped tooling a step names outright, generated-and-verified
  like this directory.
- The repo's SOP corpus — the SOP↔command two-tier model this extends.
- [`design-fidelity-loop.md`](design-fidelity-loop.md) — the `design-fidelity-bar`
  rubric that invariant 2 enforces the presence of (UI craft).
- [`architecture-red-team.md`](../rubrics/architecture-red-team.md) — the `architecture-red-team` rubric, the
  second coverage rule invariant 2 enforces (design correctness).
