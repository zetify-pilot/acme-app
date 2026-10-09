---
type: spec
---

# Autonomous Drive — the shared execute envelope

**Single source of truth** for how an *execute* command drives one unit of work
autonomously to a **merged PR**. The execute commands —
[`/fleet:prd:implement`](#),
[`/fleet:task:implement`](#),
[`/fleet:bug:fix`](#)
— **load this spec** instead of restating the rules. Edit here once; every driver
inherits. Where a command and this spec overlap, this spec wins; where this spec
and [[`implementation.md`](implementation.md)](implementation.md) overlap, the process
contract wins on coordinator/sub-agent mechanics.

> **Scope.** This is the *envelope* (the autonomous rules + the terminal). The
> *body* — how each command actually produces its diff — lives in the command
> itself: `prd:implement` parses a plan into waves; `task:implement` scopes a small
> change inline; `bug:fix` reproduces red→green (TDD). The envelope is identical
> across all three; only the body differs.

---

## What "execute autonomously" means

`<body produces the change>` → verify → fix every gap → commit on a work branch →
open a PR → **auto-merge on green CI** → **ship atomically** — with no further
questions to the user. This is the unattended path the tracker-listening daemon
invokes (`Type:bug → bug:fix`, else → `{prd|task}:implement`), and the same path a
human gets by running the command without `--manual`.

---

## Rules A–F (always on in autonomous mode)

- **A. Never stop to ask.** No `AskUserQuestion`, no proceed-gate, no "stop and
  tell the user". Wherever a step-wise flow would pause for input, choose the most
  defensible default, **append to the Autonomous Decisions Log**, and continue.
  Even a UI change with the dev stack down is not a stop — bring `make dev` up
  yourself (background, poll health). The only hard stops are *preconditions that
  make the run impossible* (e.g. a PRD at `status: stub` with no plan → not
  runnable, report; never implement it).
- **B. Log every judgment call.** Maintain one **Autonomous Decisions Log** across
  all phases: every defaulted choice, collision resolution, ambiguous interpretation,
  withheld action, and **every out-of-scope finding you tracked (Rule G)**. Surface
  it **twice**: verbatim in the **PR body** and as the last thing in the final message.
  **When the log is written into the issue description, it goes under
  `## Implementation notes (<date>)` — never `## Decision (<date>)`**, which is reserved
  for a human's answer to a question the fleet stopped on
  ([`decision-write-back.md`](decision-write-back.md), ).
  The same PR body **MUST** carry a `## Files` scope manifest () — every path
  `git diff --name-only origin/<base>...HEAD` names, as backticked bullets under
  `## Files` (or an equivalent heading). `/fleet:push` composes it; a Linear-keyed PR
  without a parseable manifest fails CI.
- **C. Branch + PR, never direct to `main`.** All commits land on the work branch
  named the way `slot:git-workflow` names it for this kind of work — and
  `<key>` in that name is the issue's *own* identifier as `slot:tracker-identity`
  describes it, never a hardcoded team prefix. **An execute command's terminal is the HANDOFF, not the merge** — it
  opens the PR with [`/fleet:push`](#), drives CI
  green, moves the issue to **`Verify Queue`**, **writes the done-sentinel with `status:
  "handed-off"`**, and stops. **The state move is not the whole terminal: a run that ends
  without the sentinel is a run the daemon reads as stopped short and relaunches — measured
  as sixteen `prd:implement` give-ups with every turn completed cleanly (), and the
  command bodies that omitted it were the tell.** `/fleet:push ship` is the
  terminal of the *verifying* session that follows it
  ([`/fleet:prd:verify`](#) for a PRD,
  [`/fleet:verify`](#) for a bug/task/cleanup),
  because the party that wrote the code cannot merge on the strength of its own
  certification. See the terminal section below.
- **D. Merge only when verify is shippable *and* CI is green.** The PR merge is the
  one hard-to-reverse, outward-facing action, and it belongs to the verifying session.
  It fires **only** if that session's verdict is shippable *and* `push ship` reports CI
  green. Shippable means: for a fix's cause ledger, 100% PASS; for a PRD's criteria
  matrix, **all-PASS or pass-with-follow-up** (every open PARTIAL/FAIL row is non-critical
  under [`prd:verify`](#) Step 4 Path A —
  proof & polish only — each filed as a linked `Type:task` follow-up and named in the
  report). Any **critical** FAIL/PARTIAL still open, or red CI → **withhold the merge**
  (leave the PR open/unmerged) and report the gaps/red checks loudly. Merging known-broken
  code to `main` is never acceptable. **In an execute run, Rule D withholds the HANDOFF**
  — a run that knows its own work is unsound (≥3 failed fix rounds, an unclosed gap)
  leaves the issue in **`Implementing`** rather than sending a verifier to certify
  something it already knows will not certify.
- **E. Bounded fix loop.** The remediation loop is capped at **3 rounds**. If a
  round closes zero gaps, stop early and fall through to Rule D's withhold path.
- **F. Atomic ship — see below.** The PRD `status: shipped` transition MUST ride
  the merge. This is non-negotiable.
- **Shared-checkout fanout.** When this run fans file-editing work across
  parallel sub-agents, obey
  [[`implementation.md`](implementation.md)](implementation.md) §1 "Shared-checkout
  fanout contract" and paste the §2 "Shared-checkout git ban" into every
  shared-checkout sub-agent prompt. `git stash` in a multi-agent shared tree is
  a data-loss vector (); N≥4 concurrent editors must use worktrees or
  serialize — disjoint file sets do not make the global stash safe.

---

## Rule F — ATOMIC SHIP (the merge *is* the status transition)

> **A PRD's `status: shipped` and its PR merge are ONE atomic event. There is no
> "merge, then set status" step — that two-step is exactly the failure mode this
> rule exists to prevent.**

**Why it must be atomic.** If `status: shipped` is written *after* the merge as a
separate commit/push to `main`, any crash, context-loss, or CI/network hiccup in
the gap leaves a **merged PR with a non-`shipped` PRD** (or, reversed, a `shipped`
status with no merge). Both are corrupt states that the resumable model (frontmatter-as-truth) cannot
self-heal — a re-run sees `shipped` and skips, or sees `implementing` and re-does
merged work.

**How atomicity is achieved.** Git/GitHub offer no transaction spanning "merge a
PR" and "modify `main`". The *only* way to make the two atomic is to make the
status change **part of the PR's merged content**:

1. After verify is shippable (Rule D), the **final commit on the work branch** sets
   the PRD frontmatter `status: shipped` (plus `status_history` append; the delivery
   index `python3 knowledge/scripts/gen_roadmap.py` produces re-derives from it), and is **pushed to the PR head**.
2. CI runs on that exact commit and goes green.
3. The PR is **squash-merged**. The squash commit that lands on `main` therefore
   **already contains `status: shipped`**.

The merge commit is the single shipping event: there is no window where the PR is
merged but `status:` isn't `shipped`, and none where `shipped` is on `main`
without the merge. They are the same commit.

**BANNED, always, no exception — for SHIPPING:**
- Squash-merging and *then* committing/pushing a `status: shipped` change to `main`.
- Any "doc-only `chore: status: shipped` commit on `main` after the merge."
- Flipping status on `main` out-of-band from the PR content.

This ban is about the *live shipping act* and stays absolute — the atomic mechanism
above (the status commit rides the PR head, the squash carries it) is the only legal
way to ship. It does **not** ban repairing a stamp that has already gone corrupt —
that is a distinct situation, covered next.

**The narrow exception — repairing an already-corrupt stamp.** Twice now (:
PRDs 0351/0354; : PRD 0373) an implementation PR merged to `main` with the
atomic stamp missed — a bare `gh pr merge` bypassed `push ship`'s final commit — and
left a **merged-but-not-`shipped`** PRD that the resumable, frontmatter-as-truth model
cannot self-heal (a re-run either re-does already-merged work or sits gated forever
behind a dependent's `depends_on`). Re-asserting "banned, always, no exception" against
two real counter-examples already on `main` only guarantees a third escalation, so the
repair is permitted — gated strictly enough that it can never be reached from a live,
in-flight ship:

- **Gate — the merge is already in the past, and nothing else.** The PRD's
  implementation PR has already merged to `main`, and its frontmatter is not
  `shipped`. A PR that has not yet merged goes through the ordinary atomic flow
  (`push ship`) — never this clause. This is the whole of the gate: it is
  unreachable from anything still in flight, because there is no path from "not yet
  merged" into it.
- **Mechanism — a doc-only PR.** Branch + PR like every other change (Rule C);
  never a direct push to `main`.
- **The record must be honest about what happened.** The repair commit cites the
  merge SHA that stranded it, and appends a `status_history` entry that reads as a
  *repair*, not an ordinary transition — e.g. a `note:` naming the stranding merge
  SHA/PR — so the history doesn't imply the atomic flow worked the first time when
  it didn't.

If you encounter process or code that flips status post-merge outside this narrow
repair clause, treat it as a bug (route through `bug:fix`). `push ship` implements
the atomic flow; the execute commands rely on it and must never re-introduce an
uncontrolled post-merge status write.

**Non-PRD work (bug/task).** Bugs and tasks have **no repo frontmatter status** —
their "shipped" state is the tracker issue moving to **Done**, which the **fleet
daemon** does once a merged work-branch PR `_pr_completes_issue` (): a
completing title form (`fix(<key>): …` / `[<key>] …`) **or** a closing keyword
(`Closes`/`Fixes`/`Resolves <key>`) as attribution. Whether the tracker's own
keyword auto-close is live is `slot:tracker-identity`'s answer — where it is
off ( disabled it in the first workspace;  confirmed the keyword alone
completed nothing), the daemon's attribution is the only completion. A bare `<key>` mention
in the body merely *links* the issue — it does not complete it for the daemon. `push ship` / `python3 knowledge/scripts/gh_closing_keyword_ensure.py` still compose and
verify the keyword at arm time () so the daemon's strongest attribution
arm cannot race the merge. Rule F's repo-frontmatter mechanics apply only to
PRDs; for bug/task, simply do not write any separate post-merge status step
either.

---

## Rule G — Track out-of-scope findings, never absorb them

During execution you will discover work that is **not in the current scope** (a
bug unrelated to this PRD/task, an important follow-up). Do **not** fix it inline
(scope creep; for a bug it would also skip the reproduce-first TDD discipline) and
do **not** silently drop it. Instead:

- An **out-of-scope bug** → file it via [`/fleet:bug:create`](#)
  (`Type:bug`, with forensic context + severity, per [`issue-tracking.md`](issue-shape.md)).
- An **important follow-up task** → file it via [`/fleet:task:create`](#)
  (`Type:task`, `depends_on` the current work where relevant).
- A **deliberately deferred integration seam** — a hop you leave unwired with a
  `// deferred follow-up` (or similar) TODO in shipped code — is an out-of-scope finding
  under this rule too. **A seam left only as a code comment is invisible** (PRD 0252 was
  the thing that discovered five such seams by grep, at the most expensive moment). At ship
  time, mint a tracked `Type:task` for each deferred seam (`depends_on` this PRD, naming the
  `file:line` of the TODO), so a downstream capstone inherits a tracked list, not a grep.

**Name the deferral when you file it.** Pass the filing command `<this command> (Rule-G deferral)`
— `--command 'bug:fix (Rule-G deferral)'` to the Fleet tool `file_issue` — so the issue's `Filed by <origin> · <command>` footer says it was deferred out of
this run rather than filed by a person running `bug:create`.

Record each tracked item in the Autonomous Decisions Log (Rule B), then continue.
This honours "no tail commits to in-flight PRDs" — out-of-scope work is sequenced
as its own tracked issue, not bolted onto this branch. The filed issue is later
picked up by the daemon (or a human) and driven through its own execute command —
a self-feeding loop where nothing found is ever lost.

### Naming the blocker when you park or file something a human must handle

**You know why you stopped — say which of three it is.** A single "a human must look
at this" marker made the human queue unusable: it mixed work that gates the entire
fleet with work that gates nothing, so it never reached zero. Vocabulary and views
are owned by [`triage-partition.md`](../registers/triage-partition.md); the
duty here is that **you classify, and you never default silently**:

- The blocker is a **question only a human may answer** → **`Blocked · decision`**.
- The blocker is **something only a human can do** — mint a credential, click a
  console, SSH to a host, merge a guarded PR → **`Blocked · action`**. Write the *runnable
  instructions* into the description, not a description of the problem.
- The blocker is **other work landing first** → **no park at all.** Wire a
  `blockedBy` relation and leave the issue **`Implement Queue`**: the fleet scheduler skips
  on `unmet_blockers`, so the chain self-serializes with no human in the loop. Parking a
  dependency on a human is the most common way runnable work goes dark.
  (*Applies to `Type:prd` too — `compute_plan` ANDs the same the tracker `blockedBy`
  gate onto PRD dispatch, on top of the frontmatter `depends_on:` graph it
  evaluates first (`scheduler.py:150-158`, `ce2ce86`).*)

**When genuinely ambiguous, `Blocked · decision` is the fallback** — a misclassified
action costs one glance; a misclassified decision sits unseen in a queue checked
weekly. Never invent a fourth destination.

**The park reason is the 🙋 comment.** If a description section is wanted, it goes under
**`## Open questions (<date>)`** — **never `## Decision (<date>)`**, which is reserved for
a human's answer to a question the fleet stopped on, not for the questions you are parking
([`decision-write-back.md`](decision-write-back.md), ).

**And give the person the options, not only the prose.** The same two to four options the
interview card already puts in the summary — each with what picking it does, the recommendation
first and marked — go into the [result file](#the-dispatch-envelope--what-the-daemon-supplies-and-where-it-is-defined)
as one structured decision when the mission names one, so the person clearing the park answers
by *picking* on the Fleet page instead of typing. The mission defines the exact form; a run whose
mission names no result file parks on its summary alone, exactly as before.

**And for an action, give the person the steps and ask for what you need back.** A
`Blocked · action` park often needs a value only the person who did the thing can see — the
client id of the app they registered, the thumbprint of the certificate they uploaded — which
the next run or a downstream issue needs and must never guess. List the steps, and name each such
value as a checked field, in the result file as one structured action when the mission names one:
the person follows the steps and hands the values back on the Fleet page, and they land in the
issue description where the next reader finds them. **Fields are for non-secret values only** —
the description is read by everyone with tracker access and by every later run — so a password,
token, key or secret is never a field: tell the person, in a step, to put it in the secret store,
and ask back at most *where* it went. The mission defines the exact form; a run whose mission
names no result file parks on its summary alone, exactly as before.

**Exception — a secondary issue fixed incidentally, not deferred.** Rule G above
assumes you *skip* the out-of-scope item. Sometimes you don't: the Commit
contract's "fix everything, never loosen" policy (`push.md`) forces a genuine fix
to an unrelated pre-existing issue in a file your primary change already touches
— e.g. a pre-commit gate (gofmt, eslint, a knowledge validator) re-validates the whole
touched file and demands a fix to something the primary diff didn't set out to
fix. That issue's root cause **is resolved in this diff** — it must not be
filed-and-left like a normal Rule G finding, or it sits open in an execution state
after merge and gets silently re-dispatched (; the PR body only *mentioned*
the secondary key, so neither the daemon's `_pr_completes_issue` nor — while it still
fired — the tracker's keyword auto-close settled it).

Record it in the Autonomous Decisions Log with the marker **`Fixed incidentally:
<KEY> — <one-line reason>`** — textually distinct from the `Filed as follow-up:
<KEY>` phrasing used for a genuine out-of-scope finding you did *not* touch.
`push`'s PR-body composer (steps 5/5.5) greps the log for this marker and mints
a **closing-keyword line for `<KEY>` too** (`Fixes <KEY>`), exactly as for the
primary key — not just a bare mention or plain link. A finding that's merely
*related* to the current diff but not resolved by it (a blocking dependency,
background context) gets neither marker — mention it in prose only.

---

## Rule H — Scratchpad hygiene: allocate uniquely, verify identity before acting

**The scratchpad path is session-specific — and that is not enough.** The harness
partitions by session id (one directory per session). The gap is that a *session*
is not an *agent*: one interactive session is a coordinator plus N concurrently-
running sub-agents, and **every sibling agent in that session is handed the
identical path string**. A generically-named file there (`commitmsg.txt`,
`notes.md`, a retry script, a fix-marker script) is therefore one file shared by every
agent in the wave, with last-write-wins and no signal at read time.
`git commit -F` does not notice it read a sibling agent's message (;
 measured two further commit-message substitutions the night of
/27 under ~18 concurrent sibling shells in one session — both caught
only by the detective half below). Cross-session and cross-checkout isolation
both hold; do not look for the wrong failure mode.

The  naming-convention remedy (namespace with a per-run id) is the
preventive half that **already shipped and already failed**: fifteen days later a
Rule-H-forbidden `commitmsg.txt` was in live use at the same time as two other
generic commit-message files belonging to different agents. A convention is not
a defence for a shared namespace — the same defect class rejected the same night
for migration ids (), fixed `/tmp` paths (), and a shared
mutable checkout (). Treat the preventive half as necessary but not
sufficient; the detective half is load-bearing.

Two rules — allocate so collisions are rare, then assert so a collision cannot
act:

1. **Allocate every scratchpad file with a genuinely unique path — never a
   shared name.** Preferred, in order:
   - **`mktemp` with a trailing `XXXXXX` template only** —
     `MSG=$(mktemp "${SCRATCHPAD}/commitmsg.XXXXXX")` or
     `MSG=$(mktemp /tmp/commitmsg.XXXXXX)`. The `X`'s **must trail the basename**.
     A mid-name template (`body.XXXXXX.md`, `msg-0541-XXXXXX.txt`) is a silent
     macOS footgun: `mktemp` returns rc=0 and creates a file named *literally*
     `body.XXXXXX.md` (fixed, predictable); a second call with the same template
     fails with `File exists` and empty stdout, so
     `F=$(mktemp …); git commit -F "$F"` gets an empty path. Measured live in the
      scratchpad.
   - **A per-agent subdirectory** under the scratchpad (`mkdir -p
     "$SCRATCHPAD/$$"` or `"$SCRATCHPAD/<agent-id>"`, then write only inside it)
     restores a private namespace so generic basenames are safe again. Keep a
     deliberate shared area only when the coordinator must drop a file for a
     named sub-agent to read.
   - A hand-rolled suffix (`msg-<id>.txt`, PID, worktree name) is acceptable only
     when `mktemp` is unavailable — and still pairs with rule 2.

   Generic shared names are **forbidden**, full stop — `commitmsg.txt`,
   `msg.txt`, `msg2.txt`, `notes.md`, a retry script, a fix-marker script, or anything
   else another sibling agent could plausibly also write.

2. **Assert identity before acting on a scratchpad file — namespacing alone is
   not enough, and this half is what actually caught both  instances.**
   It only prevents *future* collisions when applied; it says nothing about
   whether the file already on disk was swapped before this rule applied to it,
   or whether a concurrent sibling overwrote it between your write and your
   read.
   - Before every `git commit -F <msgfile>`, `grep` the message file for your
     own primary issue key and **fail closed on mismatch** (do not commit).
     Example: `grep -Eiq "\b\b" "$MSGFILE" || { echo "commit msg missing own key" >&2; exit 1; }`.
   - A the tracker-mutation script fails closed unless every target key is in a
     hardcoded expected set **and** the fetched issue's title matches what the
     script's author expected.

   **Re-read immediately before executing, don't just rename.** An agent holding
   an unrun commit/mutation script written a few minutes ago must re-read it
   (and re-run the identity assert) immediately before running it — the file may
   already have been overwritten by a sibling agent; renaming it now says
   nothing about whether its content already changed.

Applies to the coordinator and to every sub-agent this envelope dispatches — the
same fleet-concurrency hazard class as the Shared-checkout fanout rule above, on a
different shared resource (the scratchpad directory, not the git index). The
content contract is pinned by `make validate-knowledge` so the
false cross-session premise ('s original wording) cannot regress.

---

## Rule I — Every comment you leave on an issue starts by naming the command

**The first line is the only line most readers get**, in a notification or in a thread
with twenty comments. Spend it on the two things that identify *this* write: which
command produced it, and what the verdict was.

```
<emoji> `<command> <KEY>` — <VERDICT>
```

`<command>` is the command you *are*, with the key you were dispatched on
(`/fleet:check `), backticked. `<VERDICT>` is **upper-case, from that command's
closed set** — never free prose, never a sentence.

| command | verdicts |
|---|---|
| `/fleet:check` | `RELEASED` · `ESCALATED` · `CLOSED` |
| `/fleet:verify`, `/fleet:prd:verify` | `VERIFIED` · `INCOMPLETE` · `BLOCKED` |
| `/fleet:bug:fix`, `/fleet:task:implement`, `/fleet:prd:implement` | `HANDED OFF` · `BLOCKED` |
| `` | `AUDIT COMPLETE` |

**Why upper-case, when the daemon's own comments are lower-case:** the two are different
kinds of statement and the case is what tells them apart at a glance. **You state a
VERDICT** — a closed value another command dispatches on. The daemon states a **run's
disposition** in prose (`✅ \`/fleet:check \` — triaged`), because it does not
know what you decided and must never guess. An issue thread carries both; they must not
be mistakable for each other.

⚠️ **Never write the actor.** "linear-agent did X", "the agent has completed" — the actor
is the same on every comment on every issue, so it is the one fact that carries no
information. Measured over 3 days of live traffic: 52 of 102 comments named the actor, and
**not one** named the command that produced it.

⚠️ **A drifting verdict is a broken contract, not a style nit.** `/fleet:check` alone was
observed writing `RELEASE`, `RELEASED`, `released`, `release`, `CHECK - released` and
`RELEASED (first pass)` — nine distinct header spellings across fifteen comments — because
this command's own instructions *described* the comment in prose instead of showing it.
The one command that ships a fenced template (``) produced five identical
headers out of five. Copy the template; do not paraphrase it.

---

## Rule J — Never mint your own authorization

**The authorization tier is not yours to write.** An execute run (`prd:implement`,
`bug:fix`, `task:implement`) **never authors or amends** the artifacts that authorize
its own work — not in the work PR, not in a companion one:

- **programmes and slices** — ``, `` and
  `knowledge/slices/` are never created, extended or widened by a run executing an
  issue inside (or justified by) them. Slices are cut by `/fleet:slice:create`,
  programmes by `/fleet:program:create` — commands whose whole job is the objective
  tier, never a side effect of implementation. **Nor narrowed:** a row's `Disposition`
  (`withdrawn:`, `superseded by`), the program proof-waiver baseline
  (``) and a slice's reasoned `proof_waiver` row field
  (`knowledge/slices/rows/SL-NNN.json`; ) are a
  human's decisions, written through `/fleet:slice:edit` and `` —
  a run that withdraws the container its issue sits in, waives the proof its work
  owes, or turns a `deferred` waiver `excused`, has authorised its own stop.
- **a PRD minted as the warrant for the issue being executed** — a run released to
  execute work whose PRD is missing or `status: stub` has hit a Rule A hard stop, not
  an invitation to write the PRD. Authoring one is `/fleet:prd:create`, with its human
  scope gate.
- **requirement-register rows minted as that warrant** — appending register rows so
  the work looks committed is the same defect with a different file extension.

**Why.** The fleet filed a nine-chunk rename programme, `/fleet:check` released it on
a quoted prohibition, and the executing run then wrote the slice, the register and the
PRD that made the whole programme look authorized — inside its own work PR, merged with
zero reviews (: PR #9734 minted , the PSB register and PRD 0574). A
warrant minted by the run it authorizes is indistinguishable from a decision a human
took, and every downstream reader — the next checker included — will treat it as one.
That indistinguishability is the defect.

**Missing authorization is a hard stop, not a gap to fill.** It is Rule A's
*precondition that makes the run impossible*: stop, park the issue in
**`Blocked · decision`** (Rule G's park — the state, never a label), and name exactly which
artifact is missing — never mint it.

**The sanctioned way out is the unblock run with a human attached, never a workaround in
the execute run.** A PRD-sized answer to a parked issue is authorized by
 dispatching `/fleet:slice:create`
and `/fleet:prd:create` **while the human is present**, then handing the *PRD* — never the
task — to the fleet ([`triage-partition.md`](../registers/triage-partition.md) → the
PRD-sized answer row). That is not a run minting its own warrant: the human is in the room
and the authorization is theirs. An execute run that finds the warrant missing still parks;
it never becomes the unblock run to make its own work legal.

**Carve-outs** — the writes an execute run legitimately makes, and the only ones:
Rule F's ship-state stamp on the PRD that **already authorizes** the work; the run's
own flow-retro under `knowledge/retros/`; scope-ledger and status-history bookkeeping
on that same existing PRD.

---

## The terminal: `/fleet:push ship`

**Whose terminal it is.** Not the execute command's — the **verifying** session's. Every
execute command (`prd:implement`, `bug:fix`, `task:implement`) ends at a green PR and a
handoff to the review state; the session that certifies the work is the one that calls
this.

**Comment the handoff, in this shape** (Rule I). An execute run's last write on the issue
names the verifier it is handing to — a reader of the issue must never have to open the PR
to find out whether anything is still owed:

```
🤝 `/fleet:bug:fix ENG-6643` — HANDED OFF

**PR:** {url} · **CI:** green · **Ledger:** {n}/{n} closed
**Next:** `/fleet:verify ENG-6643` — merge is its call, not mine.
```

Substitute your own command and key; `/fleet:prd:implement 0487` hands to
`/fleet:prd:verify 0487` and reports its criteria matrix in place of the ledger. If Rule D
withholds the handoff, the verdict is `BLOCKED` and the body says what is unsound. That split is measured, not stylistic: **82% of PRDs were verified by their own
implementer** before it existed, and on the fix path **~1 in 5 shipped fixes later drew a
follow-up saying the fix was incomplete, while ~1 in 2 did not fully address the issue
they closed** under adversarial re-verification. Those are the **ungated** rates;
**gated**, the verify step turns back **9.3% of the issues that enter it** (53 of 571;
11.2% of 669 gate entries, measured →21) — what the gate caught, a floor under
the defect rate rather than a measure of it — and **12.5%** of the fixes it passes are
still incomplete when adversarially re-verified (4 of 32; 95% CI 5.0–28.1% — far below the
ungated ~1 in 2, but not resolvable finer than that, and the older method is unrecorded, so
part of that gap may be measurement and the gate is not proven to be the cause). An
execute command that calls `ship`
itself has skipped its gate.

The single shared merge primitive. It pushes the branch, opens a PR carrying the
`<key>` tracker issue key **with a verified GitHub closing-keyword line**
(`Closes`/`Fixes`/`Resolves <key>` — the daemon's strongest attribution signal;
a bare mention does not complete, see "Non-PRD work" above / ), waits
for CI, and on green performs the **atomic ship**
(Rule F): the `status: shipped` commit is on the PR head, so the squash-merge
lands it on `main` in one event. **"Waits for CI" now means enabling GitHub
auto-merge (`gh pr merge <pr> --auto --squash` — never `--delete-branch`, which `gh`
refuses under a merge queue) and letting the
required `CI Success` check gate the merge** — as of  `main` carries
required-status-checks branch protection (), so `--auto` merges **only** on
green, never on bare mergeability; the old hand-rolled poll-every-check-to-terminal
loop that raced CI (merging #1912 / #2545 before `CI Success` completed) is retired
(see [``](#) §0/§0.2). For the
**mechanism** of waiting out multi-round CI across turns — a foreground bounded
poll-loop / `setsid nohup … & disown` + poll the log/PID/`git rev-parse`, since
`Monitor`/`ScheduleWakeup`/background-`git` don't reliably buy proportional
wall-clock on this host — see [[`implementation.md`](implementation.md)](implementation.md)
§3 ("When even a foreground commit would exceed the tool's turn ceiling").
Returns the confirmed `origin/main` merge SHA, or
`NOT MERGED — <reason>` (which the caller treats as a withhold, Rule D — never
force-merge). "Shipped" means a `push ship`-confirmed merge SHA — never a log line,
never an assumption; re-establish git ground truth with a foreground `git fetch` /
`git rev-parse origin/main`, never carried-over belief.

---

## The dispatch envelope — what the daemon supplies, and where it is defined

A headless run is handed four things by the control plane that dispatched it. None of them
is a repository fact (no slot answers them) and none is a tool (nothing runs them); they are
the **runtime's** contract, and until this section existed every command that used one
named it without defining it — five commands wrote "the done-sentinel" and not one said what
it was.

| Thing | What it is | Who defines the exact form |
|---|---|---|
| **The dispatch mission** | the system prompt the daemon prepends: the command line it is running, the issue key, and the paths below | the daemon |
| **The result file** | `$FLEET_RESULT_FILE` — one file the run writes its structured output to, when the mission names one | the mission; the command says what goes in it |
| **The done-sentinel** | the last thing a run writes: a small file at the path the mission names, carrying a `status` from a closed vocabulary — `done`, `partial`, `failed`, `needs-decision`, `needs-action`, `verify-failed` — and the `pr` it opened (empty when none). The daemon breaks its relaunch loop the instant it appears; a run without one is a run that never finished | the mission names the path and the keys; the command names the `status` it ends with |
| **The dispatch token** | a secret the daemon places in the environment for a verify dispatch. The verifier embeds it verbatim as a `Dispatch-Token:` git trailer on the verdict commit; `knowledge/scripts/validate_verify_gate.py` recomputes the binding over the issue, plan and PR and refuses a verdict whose token does not match. **The variable's name is the daemon's**, read from the mission, never spelled in a command | the daemon; `knowledge/scripts/validate_verify_gate.py`'s binding is the register's |
| **The heartbeat marker** | a comment the daemon refreshes on the issue while a run is alive; its freshness is the only honest liveness signal | the daemon |

A command that needs one of these says which, links here, and stops. Naming the variable,
the marker text or the file layout in a portable command is naming one control plane's
implementation.

## Flow-retro

Every autonomous run ends by writing a retro into the shared corpus, in the directory
`slot:retro-corpus` names for that kind of run (per [`implementation.md`](implementation.md)
§11): a PRD run writes into `slot:retro-corpus`, task and bug runs into
`slot:retro-corpus` / `slot:retro-corpus`. The file name and frontmatter (`type:`
and the `owner:` that lets the harvester group by the work that produced it) are that slot's
answer too — the record carries the run's own id as its owner, whatever the file is called. Capture what worked, what fought back, and any
recurring friction worth fixing in the process itself. **Record + suggest only — a run
never edits the flow / commands / contracts.** Retros are a **durable learning corpus**
(one home, swept by the harvest loop) — see the **`retro-corpus`** slot.
The harvest loop is **``** (the
[`improve-the-process`](improve-the-process.md) SOP): it reads the corpus and
applies (additive) or proposes (rule-changing) edits to the SOP or command behind each
recurring suggestion.

**Cross-repo runs — the corpus home is the repo the PR lands in ().** A run whose
deliverable PR lives in a different repository from the one it was dispatched from cannot
commit its retro into the dispatching repo's corpus without a second PR there — the exact
strand this section forbids. So the run writes its retro into the **landing repo's own**
`slot:retro-corpus` directory (creating the folder on the work branch if absent) and commits
it there, riding the deliverable PR under the same before-`/fleet:push` order. The harvest
loop (``) sweeps every lane repo's corpus, so the learning still
reaches it. Never open a retro PR in a repo the deliverable did not land in — it is a second
PR, held forever by the daemon ().

**The retro rides the deliverable PR — never a second PR ().** Write and commit
it on the work branch **before** `/fleet:push` / the handoff so it lands in the same
squash-merge as the work (one PR per issue). [`implementation.md`](implementation.md) §11 already
said this; the execute-command terminals (`task/implement`, `bug/fix`, `prd/implement`
D1.5) enforce the order. A post-handoff retro PR is the measured failure mode: it never
reaches push-mode auto-merge arming, the daemon's re-hold drafts and disarms it forever
(head ref carries the issue key; only the verify-token PR is lifted), and `/fleet:verify`
then refuses Done while an open PR still claims the key — parking the issue on
`Blocked · decision` over a mandatory artifact that must never block shipping. Accepted
cost of riding the deliverable: the retro cannot record what happens inside the CI and
verify windows.

---

## `--manual` (opt-out)

The execute commands accept `--manual` to restore the human proceed-gates this
envelope removes (step-wise waves → verify → commit, then stop and hand off to
`prd:verify` + `push`). `--manual` skips Rules A–B's never-stop/auto-default
behaviour and the auto-merge; it does **not** weaken Rule F — when a manual run
*does* ship, the status transition still rides the merge atomically.
