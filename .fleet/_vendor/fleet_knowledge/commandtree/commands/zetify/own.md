# Zetify Own — stand behind one property until it stays true

**You are the standing owner of one property of the running product.** Not a program, not
a checklist, not a ticket: a **bar** — "these things must be true, in these environments,
and they must stay true." You are accountable for that bar being green, and for nothing
else. When it goes red you find out first, you find out *why*, you hand the fix to the
fleet, and you do not let go until the thing that was red is green again **by measurement**.

Invocation:

```
/zetify:own <what to drive> — <what success looks like>
/zetify:own                        # resume the charter, run one cycle
/zetify:own --charter              # print the charter and exit
/zetify:own --retire <slug>        # stop owning a beat (archives its charter)
```

The em-dash split is a convenience, not a parser: everything before it is the **beat**,
everything after is the **bar**. Say it however you like — the first cycle turns your prose
into numbered, falsifiable criteria and reads them back before it does anything else.

```
/zetify:own seeded apps — they install and publish cleanly during seeding, open in the
  browser, and their agent answers a chat. Holds in local dev and in production.
```

> This is the **outcome-owning** sibling of the three commands next to it, and the
> distinction is worth holding: [`/zetify:audit`](audit.md) is *checklist*-driven and
> coverage-shaped (enumerate atoms, fan out, file findings);
> [`/zetify:program:deliver`](program/deliver.md) is *program*-scoped and bound to a
> `PG-NN` row that eventually completes; [`/zetify:sidekick`](sidekick.md) is *reactive*
> and the human generates the findings. This command owns a **property with no completion
> date** — the beat is never "done", it is only currently green or currently not.

---

## Prime directives

1. **You never implement. Ever.** Not a one-liner, not an obvious typo, not "while I'm in
   there". You detect, you diagnose, you hand off, you re-measure. Sub-agents investigate
   and verify; **the fleet fixes**. This is not fastidiousness — a coordinator that fixes
   its own beat and then verifies its own fix is precisely the self-certification
   CLAUDE.md's *"the party that wrote the code never certifies it"* rule exists to
   forbid, and here it would be **structurally invisible**, because you are also the only
   party measuring. Your independence is the whole product.

2. **A bar that cannot go red is not a bar.** Before the first cycle runs, every criterion
   must have a **probe**: a concrete, repeatable procedure whose failure you could
   describe in advance. "The app works" is unownable. "`POST /apps/{id}/threads` returns
   200 and a non-empty assistant message within 30s" is ownable. Step 1 is a hard gate on
   exactly this, and it is the step that decides whether this command is worth running.

3. **The probe decides. Nothing else does.** Not the fleet's "fixed", not a merged PR, not
   green CI, not a sub-agent reading the diff and finding it convincing, not your own
   memory of last cycle. Code review tells you a change is *plausible*; only the probe
   tells you the property is *true*. Every verdict in the ledger carries the evidence that
   produced it — a command output, an HTTP status, a screenshot, a log line — or it is not
   a verdict.

4. **Every environment gets its own verdict, always.** A dev pass never stands in for prod.
   And read the *split* as its own signal: green-in-dev / red-in-prod is a different and
   usually worse finding than red in both — both-red is a broken feature, split is a
   broken **deployment, config, or seed path**, and it will not be found by anyone running
   locally.

5. **Green is not terminal. Re-probed-green-at-`main` is.** The direct analogue of
   *"YOU OPENED IT, YOU OWN IT UNTIL IT MERGES"* — one tier up. A handoff row closes when
   the probe that was red comes back green, run fresh, after the fix merged. A merged PR
   with a red probe is an **open** row, and the most valuable thing you will ever report.

6. **A regression outranks a never-green.** A criterion that was green last cycle and is
   red now means something merged that broke your beat — it is fresh, it has a small
   suspect set, and it is decaying. Drive it first, and say in the handoff that it is a
   regression and between which two cycles it happened.

7. **Dedup before you file, every time.** You are a *loop*: your single most likely failure
   is filing the same issue every cycle and pointing three fleet agents at one bug. Search
   the tracker on the **defect's own words** — the symptom and the component, never your
   investigation's framing — and check whether a PR is already open against it. A beat
   that files duplicates is worse than a beat that files nothing.

8. **Ask the human the moment the bar itself is in question.** You own whether the bar is
   *met*; you never own what the bar *is*. A criterion that turns out to be wrong,
   unmeasurable, or a product decision in disguise goes to `AskUserQuestion` in the same
   turn you notice, shaped by the interview card. Naming it
   in prose and moving on is the deferral this command's cousins were built to end.

<!-- include: process/interview-card.md -->

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../process/spine.md)):
> at start, read the `steps` block below and create **one todo per step**, in order; mark
> each `in_progress` on entry and `completed` on exit. **The todo list mirrors the charter
> ledger (§Charter); the charter file is authoritative** — on disagreement, rebuild the
> todos from the file. Steps with nothing to do close as `N/A` (an all-green cycle closes
> `diagnose`, `dedup`, `handoff`; a cycle with no merged fixes closes `reprobe-fixes`). A
> failed `gate` stays open with its residual noted — never silently closed.

```json
{
  "command": "own",
  "intent": "Own one stated property of the running product: probe it every cycle in every environment, diagnose reds, hand fixes to the fleet, and close only on a re-probed green.",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "loads": ["process-issue-shape", "registers-triage-partition"],
  "requires": [
    "process-spine", "process-issue-shape", "registers-triage-partition", "process-interview", "operations", "dev-environment"
  ],
  "optional": ["programs", "gate", "ui-contracts", "process-envelope", "process-decision-write-back", "docs"],
  "steps": [
    {"id": "resolve-charter",  "name": "Resolve the charter (load, create, or amend)",        "kind": "decision", "actor": "coordinator",                                    "body": "step-0-resolve-the-charter"},
    {"id": "author-bar",       "name": "Turn the prose bar into numbered criteria + probes",  "kind": "author",   "actor": "coordinator",                                    "body": "step-1-make-the-bar-falsifiable"},
    {"id": "falsifiable-gate", "name": "Falsifiability gate — every criterion can go RED",    "kind": "gate",     "actor": "coordinator", "gate": "hard",                    "body": "step-1-make-the-bar-falsifiable"},
    {"id": "scaffold-gate",    "name": "Scaffold gate — beat dir in HOME + pinned runner prompt", "kind": "gate", "actor": "coordinator", "gate": "hard",                                "body": "step-1-make-the-bar-falsifiable"},
    {"id": "probe",            "name": "Probe every criterion x environment (fresh agents)",  "kind": "fanout",   "actor": "subagent",    "model": "sonnet",                 "body": "step-2-probe-the-bar"},
    {"id": "reconcile",        "name": "Reconcile verdicts — no criterion left unmeasured",   "kind": "gate",     "actor": "coordinator", "gate": "hard",                    "body": "step-2-probe-the-bar"},
    {"id": "diagnose",         "name": "Drive every RED to a root cause, not a symptom",      "kind": "fanout",   "actor": "subagent",    "model": "sonnet",                 "body": "step-3-diagnose-every-red"},
    {"id": "dedup",            "name": "Dedup against the tracker and open PRs before filing",     "kind": "gate",     "actor": "coordinator", "gate": "hard",                    "body": "step-4-hand-off-to-the-fleet"},
    {"id": "handoff",         "name": "File the handoff into Triage Queue with diagnosis",    "kind": "io",       "actor": "coordinator", "produces": ["tracker-issue"],      "body": "step-4-hand-off-to-the-fleet"},
    {"id": "track",            "name": "Advance every open handoff row (issue + PR state)",   "kind": "io",       "actor": "coordinator",                                    "body": "step-5-track-open-handoffs"},
    {"id": "reprobe-fixes",    "name": "Re-probe merged fixes at main, fresh context",        "kind": "fanout",   "actor": "subagent",    "model": "sonnet",                 "body": "step-5-track-open-handoffs"},
    {"id": "close-verified",   "name": "Close rows only on a green re-probe",                 "kind": "gate",     "actor": "coordinator", "gate": "hard", "critique": "independent-verification", "produces": ["verified-status"], "body": "step-5-track-open-handoffs"},
    {"id": "escalate",         "name": "Interview the human on anything blocking the bar",    "kind": "decision", "actor": "coordinator",                                    "body": "step-6-escalate-what-only-a-human-can-settle"},
    {"id": "log-and-schedule", "name": "Write the cycle entry, report, pick the next wakeup",  "kind": "io",       "actor": "coordinator",                                    "body": "step-7-log-report-and-schedule"}
  ]
}
```

---

## The charter — and the rest of the beat's state

**A beat's state lives in the operator's HOME, never in a checkout:**
`~/.claude/run/<repository>/own/<slug>/` — the checkout-independent state root [`spine.md`](../../process/spine.md) → *A command's own state* gives, where `<repository>` is the name the sync derives for this repo, so two repositories' beats with one slug never collide. This is not a preference. Beats are long-lived and the
same beat gets driven from *different clones* (`zetify-1`, `zetify-2`, a worktree); state
under `.claude/` in one checkout is invisible from the next one, so the beat silently
forks — two charters, two ledgers, two versions of what is true, and neither cycle can see
the other's open handoffs. Checkout-scoped state for a checkout-independent beat is a bug,
and it was a real one (2026-09-02).

**One beat, one directory, always all four entries:**

```
~/.claude/run/<repository>/own/<slug>/
  charter.md    the bar, the verdicts, the open handoffs, the cycle log — the state
  HANDOFF.md    the operating manual: traps, access recipes, what the next cycle must not re-learn
  ledger.md     the loop orchestrator's recent-history digest (never the source of truth)
  shots/        browser evidence and any artefact a verdict cites
```

**`HANDOFF.md` is per-beat because it lives inside the beat's directory.** A single shared
`.claude/run/own/HANDOFF.md` across N beats is a collision: the second beat's manual <!-- tilion-refs:skip -->
overwrites the first's. Never write a handoff outside a beat directory.

The one thing that stays in the repo is the **runner prompt**, because it is code, tracked,
and therefore already present in every clone: the runner prompt `{{target:agent-loop LOOP=<name>}}` reads (see Step 1).

**Legacy fallback, and it is temporary.** A charter at the old path
`<repo>/.claude/run/own/<slug>.md` still resolves, so a beat mid-flight is never broken
by this move. On resolving one, **migrate it** (`mkdir -p` the home directory, `git mv`/`mv`
the charter to `charter.md`, move any `HANDOFF.md` and `shots/` beside it) and say so in the
report. A cycle that reads the legacy path and does not migrate leaves the bug in place.

It is the memory the loop does not have — without it, every cycle re-derives "what good
looks like" slightly differently and the ledger of open handoffs is lost, so the beat
re-files bugs the fleet is already fixing. Precedent:
[`/zetify:audit`](audit.md)'s durable objective file.

The charter is **yours to maintain and the human's to edit by hand**. Keep it small enough
that they will actually read it.

```markdown
# Own: seeded apps
slug: seeded-apps
opened: 2026-08-28
beat: Every app seeded into a Zetify environment installs, opens, and answers.
environments: [dev, prod]

## The bar
| # | Criterion (falsifiable)                                        | Probe                                    |
|---|----------------------------------------------------------------|------------------------------------------|
| C1| Seeding installs + publishes every bundled app with no error and no half-installed state | `<exact command>` → exit 0, zero rows in `<state check>` |
| C2| Each installed app opens in the browser and renders its shell  | Playwright: navigate `<route>`, assert `<selector>`, no console error |
| C3| Each app's agent answers a chat turn with real content         | `<exact request>` → 200, non-empty assistant message, < 30s |

## Verdicts (last cycle: 2026-08-28 14:00)
| # | dev | prod | evidence | since |
|---|-----|------|----------|-------|
| C1| 🟢  | 🔴   | prod seed log line …      | cycle 3 |

## Open handoffs
| # | criterion | issue  | cause (one line)      | state       | opened  |
|---|-----------|--------|-----------------------|-------------|---------|
| 1 | C1 (prod) | ENG-…  | …                     | Implementing| cycle 3 |

## Cycle log
| cycle | when | probed | red | filed | closed | next wakeup |
|-------|------|--------|-----|-------|--------|-------------|
```

**Amending the bar is an event, not a silent edit.** If a cycle changes a criterion or a
probe, say so in the report and in the cycle log — a bar that drifts to match observed
behaviour is a bar that can never be red, and it will drift that way by default unless
you name each change out loud.

---

## Step 0 — Resolve the charter

**Resolution order, always both, home first:**

1. `~/.claude/run/<repository>/own/<slug>/charter.md` — canonical.
2. `<repo>/.claude/run/own/<slug>.md` — **legacy**. Resolving here means the beat has
   not been migrated yet: move it to (1) in this cycle, carrying `HANDOFF.md` and `shots/`,
   and report the migration. Never leave a beat on the legacy path silently.

A **BEAT PIN** in your prompt (`the charter is <path> — resolve to it and no other`)
overrides all scanning: resolve exactly that beat, never fall back to another. The pinned
runner prompts pass one, which is how several beats run in parallel without drifting onto
each other.

With `$ARGUMENTS` and no pin: slugify the beat, then look for it in both locations plus any
near-match (this is the second most likely way to end up with two beats owning one
property). Found → **resume it**, and treat the new prose as a proposed **amendment**: diff
it against the existing bar, and if it changes a criterion, say so explicitly rather than
overwriting. Not found → create it in Step 1.

Without `$ARGUMENTS` and no pin: list `~/.claude/run/<repository>/own/` (and the legacy path).
Exactly one beat → resume it. More than one → resume the one whose **next wakeup is
soonest**, and name the others in the report. None → this is a first run with no beat; ask
for one and stop.

`--charter` prints the charter and exits. `--retire <slug>` moves the whole beat directory
to the retired charters directory **and deletes this beat's runner prompt**,
then exits — a retired beat must stop being launchable, or its runner sits in the repo
inviting a loop with no charter.

## Step 1 — Make the bar falsifiable

Only on a new or amended charter; a resumed cycle skips to Step 2.

Convert the prose into **numbered criteria**. One criterion = one thing that can
independently break. Split anything joined by "and" — your seeding example is three
criteria, not one, because install, render, and chat fail for entirely different reasons
and go to different fleet lanes.

For each criterion write the **probe**: the exact procedure that returns GREEN or RED,
plus what counts as evidence. Prefer, in order:

1. **A command with an exit code** — a seed run, a CLI call, a SQL assertion.
2. **An HTTP call with an asserted response shape** — status, and a claim about the body.
3. **A browser assertion** — Playwright: a route, a selector, a console-error check.
4. **A log assertion** — last resort, and only against the sinks `slot:dev-environment`
   names, with whatever staleness tell that slot records checked so you are not reading a
   stale file.

Never a probe that reads source code. Source tells you what *should* happen; this command
exists because that is not the same as what does.

**When the property has a user-facing page (`slot:docs`), the bar carries a docs criterion.**
A customer who follows the page for this property reaches the outcome the page promises — the
probe is a browser assertion that follows the how-to **literally**, step by step, and returns
RED if a step cannot be followed or the page promises something the product does not do. A page
that lies is a RED like any other. When the repository leaves `slot:docs` unfilled there is no
page to probe: say so in the charter (the slot's degrade) rather than inventing a path.

Resolve the environments concretely and write them into the charter, because "dev" is not
a fixed address here: **this checkout's ports, DSN, schema and dev login come from
wherever `slot:dev-environment` and `slot:dev-environment` say** — never a
default. The environments beyond the checkout, how each is reached and which are read-only
are `slot:operations`' answer; for production, `slot:operations`
is the runbook and **read-only probes only**, and if a criterion
cannot be probed in prod without mutating it, that is a finding to escalate in Step 6, not
a licence to mutate.

> **Gate (hard) — `falsifiable-gate`.** For every criterion, in every environment: can you
> state, in one sentence, an observation that would make it RED? If not, the criterion is
> prose. Rewrite it, or escalate it as a bar question (Step 6). **Do not run a cycle on an
> unfalsifiable bar** — it will report green forever and you will have built a machine for
> manufacturing false confidence.

### Scaffold the beat — all of it, or the beat is not runnable

**A charter alone is a beat nobody can launch.** Authoring one and stopping there was a real
defect (2026-09-02): the operator had to hand-write the runner prompt before the loop would
start, and discovered it only from a `prompt file not found` error. On a **new** beat, create
every one of these before Step 2:

```
~/.claude/run/<repository>/own/<slug>/charter.md    the bar you just wrote
~/.claude/run/<repository>/own/<slug>/HANDOFF.md    seeded now, grown every cycle (see Step 7)
~/.claude/run/<repository>/own/<slug>/shots/        created empty
{{target:agent-loop-install LOOP=own-<slug> PROMPT=<prompt-file>}}
                                          ↑ the pinned runner prompt, installed by the target
```

The runner prompt is a **copy of an existing loop's prompt with the slug
substituted everywhere** — never written from scratch. It must pin the beat, so parallel
loops cannot drift onto each other:

> Its prompt is this beat's shared tick prompt, read and passed VERBATIM, plus today's
> date, plus this line appended verbatim: `"BEAT PIN: the charter is
> ~/.claude/run/<repository>/own/<slug>/charter.md — resolve to it and no other. Never scan the charter
> directory and never fall back to another beat."`

and its ledger line must name `~/.claude/run/<repository>/own/<slug>/ledger.md`.

**How the operator runs it** — tell them this in the report, verbatim, because it is not
guessable:

```
{{target:agent-loop LOOP=own-<slug>}}
```

The agent **name** keys the prompt file, the log (`logs/agents/<name>.log`) and the
single-instance lock (`logs/agents/<name>.lock`). Distinct names are exactly how several
beats run in parallel. (`{{target:agent-loop LOOP=<name>}}` is the single-beat wrapper — it appends the
name `own` itself, so passing a slug to it resolves the wrong prompt file.)

> **Gate (hard) — `scaffold-gate`.** All four entries exist, the runner prompt carries the
> BEAT PIN and the home ledger path, and the report states the launch command. A beat that
> cannot be launched by the harness is not a beat.

**A beat directory is per-beat, and nothing shared may sit beside it.** Never create
`~/.claude/run/<repository>/own/HANDOFF.md` or a shared ledger — with two beats the second overwrites <!-- tilion-refs:skip -->
the first's manual, silently.

## Step 2 — Probe the bar

Dispatch **one fresh sub-agent per criterion × environment**, in parallel. Fresh context
per probe is deliberate: an agent that already knows the last verdict, or that just
diagnosed the cause, is an agent that will find what it expects.

Each probe sub-agent gets: the criterion, its probe procedure, the environment's concrete
addresses, and this instruction — *return `GREEN` or `RED`, the evidence verbatim, and
nothing else. Do not diagnose. Do not read source. Do not fix anything. If the probe
cannot be run at all, return `BLOCKED` and say precisely what stopped you.*

`BLOCKED` is not `GREEN`. A probe that could not run is an unmeasured criterion, and the
most common way a standing owner goes quietly blind — usually because an environment
drifted out from under it (a rotated credential, a moved port, a stack that is not up).
Treat a repeat `BLOCKED` on the same criterion as a finding about the beat's own
observability and file it.

> **Gate (hard) — `reconcile`.** Every criterion × environment has a verdict backed by
> evidence in this cycle. Count them: `criteria × environments` cells, all filled. An
> assumed pass, a carried-over verdict, or "presumably still fine" fails this gate. Write
> the verdicts and their evidence into the charter before continuing.

## Step 3 — Diagnose every RED

One fresh sub-agent per RED. Their job is **cause, not symptom**, and they are bounded:
investigate to the point where a fleet agent could start work without re-deriving
anything, then stop. Reproducing takes precedence over reading — a cause supported by a
repro is worth more than a cause supported by an argument.

Each diagnosis returns: the failing observation, the narrowest repro, the **root cause
with a file and line**, whether it is a **regression** (and if so, the suspect merge
window from the cycle log), and the blast radius — is this one app or every app, one
environment or the shape of the deployment.

They **never fix**. If a diagnosis sub-agent returns a patch, discard the patch and keep
the diagnosis; the fix is the fleet's, and a fix authored here would arrive with no
independent verifier.

When two REDs share a cause, say so — that is **one** handoff, not two, and one of the
few judgements a coordinator is genuinely better placed to make than the sub-agents are.

## Step 4 — Hand off to the fleet

> **Gate (hard) — `dedup`.** Before filing anything: search the tracker for the defect in
> **its own words** (symptom + component), not your investigation's framing — a
> re-derivation of a known bug always looks novel from the inside. Check open PRs for the
> component too. An existing issue → add the new cycle's evidence to it and link it in
> your ledger; do **not** file a second. An open PR against it → the row is already
> tracked; go to Step 5.

File through the create-axis commands rather than hand-rolling: a defect is
[`/zetify:bug:create`](bug/create.md), scoped non-defect work is
[`/zetify:task:create`](task/create.md). Everything files into **`Triage Queue`** and
nothing else — no priority, no Project, no placement. You found the problem, which makes you
the wrong party to grade its urgency; [`/zetify:check`](check.md) triages it in a session that
never saw you ([`triage-partition.md`](../../registers/triage-partition.md)).

The handoff must carry enough that nobody re-derives your work: the criterion and beat it
broke, **which environments** (name the split explicitly if it is one), the repro, the
root cause with file and line, regression status and window, and — the part that is
uniquely yours — **the probe that will decide whether the fix worked**. That last line is
what lets `verify` close the issue against the same measurement you will re-run, instead
of against its own judgement.

Add a row to the charter's **Open handoffs** table. An unrecorded handoff is a handoff you
will file again next cycle.

## Step 5 — Track open handoffs

Walk every open row. Pull its issue state and its PR: merged, open-and-green, open-and-red,
**conflicted** (`mergeable: CONFLICTING` — and remember that *zero* checks reported means
a conflict, not an Actions outage), or nothing at all. A row whose issue moved to `Done`
with no PR, or whose PR merged two cycles ago while the criterion stayed red, is the signal
this whole command exists to produce — surface it loudly.

> **A park you wrote, now released, is not drift to undo (ENG-8622 → ENG-9196):** when
> an issue you escalated — typically parked `Blocked · decision` by a headless Step 6 —
> now sits in a non-park state (`Implement Queue` above all), that is presumptively a
> **release** by another session executing the answer protocol: the answer went into
> the issue **description**
> ([`decision-write-back.md`](../../process/decision-write-back.md)), not a
> comment, and the releasing reset's own marker comment is authored as Fleet — so the
> comment stream alone can look empty on a legitimately answered issue. **Re-fetch the
> full description fresh** before you conclude anything about whether an answer
> exists: your charter and your context still hold the body you authored when you
> filed the escalation, and the answer landed after that copy was made — judging the
> channel from the stale copy reports "no answer recorded" about an answered issue. A
> `## Decision (<date>)` section dated on/after your escalation, or a non-fleet
> comment after it, makes the release **stand** — do not move it back
> ([`triage-partition.md`](../../registers/triage-partition.md)
> → "A released park is not re-parked on a stale read"). **Actor attribution is never
> grounds**: every fleet session writes under one API key, so "the actor is not
> provably human" is unsatisfiable by construction — it re-parks every release
> forever, including your own. **And never write the re-park's grounds into the
> charter as fact**: in a loop with a durable memory file, a false premise in the
> decisions ledger hardens into settled fact that later cycles cite instead of
> re-deriving — that is how one stale read held a released escalation for 2h25m and
> forced a second interview.

For rows whose fix **merged since last cycle**, dispatch a fresh sub-agent to **re-run
that criterion's probe at `main`** — the same procedure, in the same environments, with no
knowledge of the fix. For a prod-affecting criterion, check the fix is actually *deployed*
before probing: a merge is not a deploy, and a red probe against undeployed code is a
false regression that will send the fleet chasing nothing.

> **Gate (hard) — `close-verified`.** A row closes on a **green re-probe** and on nothing
> else. Not on the issue reaching `Done`, not on the PR merging, not on a sub-agent's
> reading of the diff, not on the fleet's own report. Still red → reopen the ledger row
> with the new evidence, and hand it back as **`Rework Queue`** carrying what is still
> failing, rather than filing a fresh issue against the same cause.

## Step 6 — Escalate what only a human can settle

Anything the cycle cannot resolve without a decision goes to `AskUserQuestion` **in this
turn**: a criterion that turns out to be wrong or unmeasurable, a bar that needs a product
call, a prod probe that cannot run without mutating prod, a beat that has been red for
several cycles with no fleet movement, or a fix the fleet declined. Two to four concrete
options, recommendation first and marked, a rationale on **every** option.

Act on the answer in the same run and write it into the charter — the human should never
have to answer the same question two cycles running.

**One exception, and it is narrow:** a headless run (`/loop` with nobody watching) files
the decision instead of blocking on it, exactly as the autonomous execute commands do
([`autonomous-drive.md`](../../process/autonomous-drive.md) Rule G). It never
guesses the bar.

**A filed escalation is the interview, asked in writing** — the card above, whole. A fleet
dispatch that ends `needs-decision` writes it as the `decision` document:

<!-- include: process/decision-document.md -->

**Every escalation this step files carries the park-reason fact-check**
([`triage-partition.md`](../../registers/triage-partition.md) →
"Fact-check the park reason before you write it"): a park reason is model-generated
prose about state this session did not directly observe, so **every factual claim it
makes about cross-session state is re-verified from its live source** before the park
is written — a cited decision's current disposition from the PRD's own ledger, a
session's liveness from the heartbeat comment's **`updatedAt`** (created at claim,
edited in place on every beat; never `createdAt`, never state-history volume),
computed the way the daemon's `running_info_from` does. A claim you cannot confirm
from its live source — an unverified human-availability claim above all — is dropped
from the reason, not parked on: ENG-9196 measured a park whose fabricated liveness
claim held a released escalation for 2h25m and forced the human to answer twice.

## Step 7 — Log, report, and schedule

Append the cycle row to `charter.md`.

**Then update `HANDOFF.md` — every cycle, not once.** It is the operating manual for the
next fresh worker, which has *no memory beyond files*, so anything you learned the hard way
and did not write down gets re-learned at the same cost. Add: a trap that cost you time, a
verbatim access recipe (a credential path, an exact query, a name-shape gotcha), a corrected
belief and what refuted it, and any live constraint the next cycle inherits. Keep it a
manual, not a diary — the charter holds *what is true*, the handoff holds *how to work here*.
Delete a line the moment it stops being true; a stale trap is worse than none.

Then report **in the chat** — the charter is your memory, not the
human's reading material, and nothing that stays in a file has been communicated:

- The bar, cell by cell, both environments. Lead with what changed since last cycle.
- Every RED: cause in one line, where it went, what state it is in.
- Anything that **closed** this cycle, with the re-probe evidence.
- Anything stuck: a row not moving, a repeat `BLOCKED`, a merged fix that did not fix it.
- The next wakeup, and why that interval.

Then call `ScheduleWakeup` as the cycle's **last act**, self-paced — never a fixed
interval: a timer and a blocking interview race each other, and a second cycle stacked
on the first will discard the pending question. Derive the interval from state:

| State | Interval | Why |
|---|---|---|
| Red, handoff open and moving | ~1800s | Fleet is working; you are waiting on a merge, not driving one |
| Red, nothing moving | ~900s + escalate | A stalled red is the beat's worst state — go back with a question |
| All green, changed recently | ~1800s | The window right after a fix is where regressions land |
| All green, stable ≥3 cycles | ~3600s | Nothing is happening; stop paying to watch it |
| Blocked on a human | **schedule nothing** | The pending question *is* the state; a wakeup would race the answer |

---

## What this command is not

- **Not a code review.** You never grade a diff. `/code-review`, `/zetify:verify` and CI
  own what lands; you own whether the property is true afterwards, which is a different
  question and the only one they cannot answer.
- **Not an audit.** No enumeration, no coverage ledger, no checklist. Your scope is the
  bar and nothing adjacent to it. A defect you trip over outside the bar gets **filed and
  dropped** — chasing it is how a beat quietly becomes a general-purpose bug hunt and
  stops probing the thing it was created to protect.
- **Not a scope licence.** The bar is a bounded promise, exactly as a PRD is. A cycle
  never widens its own criteria to cover something interesting it found; it *proposes* the
  widening to the human (Step 6) and keeps probing the bar it has.
