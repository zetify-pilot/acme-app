---
type: spec
---

# Implementation Process (shared) — read before any implement/verify run

This is the **shared process contract** for `/fleet:prd:implement` (autonomous
or `--manual`), `/fleet:prd:verify`, and `/fleet:bug:fix`. It owns the coordinator ↔
sub-agent split, the codegen + verification + commit loop, and the
cross-cutting rules that kept biting multi-agent runs. The **language-specific
lint + coding rules** live in two sibling files — reference the one that
matches the task, not both:

- Every task → the contract `slot:languages` names for its lane.

---

## 1. Roles (coordinator vs sub-agent)

- **The coordinator orchestrates; it does not implement.** It parses plans,
  groups tasks into waves, dispatches sub-agents, runs the per-wave
  coordinator gate, and commits. It does **not** write feature code or tests.
- **Exception — trivial mechanical edits.** When a fix is ≤ ~3 lines, fully
  mechanical, and unambiguous (a string literal replaced by the typed constant it
  names, a missing import, a one-line cast), the coordinator
  **may apply it directly** rather than dispatch. Spawning a sub-agent for a
  3-line edit and waiting ~15 min for it to (often) drop is pure waste. Bigger
  than that → sub-agent.
- **Sub-agents run on Sonnet** (`model: "sonnet"`, `subagent_type:
  "general-purpose"`).
- **Shared-checkout fanout contract (coordinator).** When N concurrent
  sub-agents edit the **same** working tree (no per-agent worktree isolation),
  the stash/index/working-tree are a single global resource — one agent's
  `git stash` sweeps every sibling's uncommitted edits ( near-miss ×3
  in one run; also PRD 0276, 0350). Rules:
  1. **Every** shared-checkout sub-agent prompt MUST carry the §2
     "Shared-checkout git ban" block (paste verbatim). Prompt instructions
     alone are not enough if the ban is missing — agents still reach for
     stash as personal scratch.
  2. **N ≤ 3** concurrent editors on disjoint file sets → shared checkout is
     fine (with the ban).
  3. **N ≥ 4** concurrent editors → do **not** share one checkout. Either
     isolate each batch in its own worktree (pin every agent to the **same**
     base SHA — PRD 0221's failure mode was agents on different bases), **or**
     serialize into waves of ≤3 shared-checkout agents. File-set disjointness
     does **not** make stash safe; the stash list is global.
  4. After a shared-checkout wave lands, the coordinator audits `git status`
     for expected-but-missing edits before the next wave (the recovery that
     caught PRD 0276's silent B1 revert).
  5. Never dispatch two agents that edit the **same** file concurrently —
     serialize same-file ownership (PRD 0350).

## 2. Sub-agent prompt preamble (paste verbatim into every implementation sub-agent)

> You are implementing one task in this repository. You will NOT see the
> orchestrator conversation — this prompt is self-contained.
>
> **Read the contract first.** Before writing any code, read this repo's contract for your
> layer IN FULL — the **`languages`** slot names it, one per language the repo builds in. It
> is the canonical lint + coding-standards contract. Code that violates it fails CI and
> forces multi-cycle rework. Also follow the repo's own always-on instructions.
>
> **Do NOT run codegen or the slow gates.** Nothing from the `slot:codegen` answer, and nothing
> from `make lint` or `make test-unit`. Edit the codegen *source* `slot:codegen`
> names and stop — the coordinator runs codegen and the gates once per wave.
>
> **Shared-checkout git ban (load-bearing when siblings edit the same tree).**
> You may be one of several agents editing this checkout in parallel. The
> stash, index, and working tree are **global**, not per-agent. NEVER run:
> `git stash` / `git stash push` / `git stash pop` / `git stash drop` /
> `git stash apply`; `git clean`; `git reset --hard` / `git reset --mixed`;
> `git checkout -- <path>` or `git restore <path>` on any path outside your
> assigned file list; `git checkout <branch>` / `git switch`; `git add -A` /
> `git add .` (stage only your explicit paths, if you stage at all — prefer
> not committing). Also NEVER run a **bare `pkill` / `killall`** — the process
> namespace is shared with every sibling checkout, so `pkill -f go`, `pkill node`
> or `pkill -f make` reaps *their* gates and dev stacks, not just yours. The one
> sanctioned reap is the exact narrow pattern in §4 (`pkill -9 -f` on the process name
> `slot:gate` gives), and only immediately before your own foreground commit.
> These are banned even for your own crash recovery or to
> "see clean main". Safe alternatives scoped to **your assigned files only**:
> `git diff -- <your files> > /tmp/mine-$$.patch` before a risky edit, and
> `git apply /tmp/mine-$$.patch` to restore; to compare against clean main use
> `git show origin/main:<path>` or ask the coordinator for a disposable
> worktree — never stash. If you need a safety net the coordinator did not
> give you, STOP and report rather than reaching for a repo-wide mutator.
>
> **Test-first for behavioral work (red before green).** If your task's
> deliverable is a *behavioral contract* — an endpoint shape/status, a 403
> denial, a projection narrowing, an SSE payload, a state transition — write the
> test BEFORE the implementation, run it, and confirm it **fails for the right
> reason** (the behavior is genuinely absent, not a typo/setup error). Then
> implement until it passes. This proves the test exercises the new behavior
> instead of rubber-stamping code you already wrote. Capture both the failing
> output and the passing output — you report them below. (Pure mechanical tasks
> — a rename, a wiring edit, codegen-source-only changes — are exempt: write the
> test alongside and note "mechanical, no red phase" in the report.)
>
> **Read-path, display-resolution, projection, or backfill defects need a
> pre-existing-row repro, not a fresh one.** Ask first: does this defect depend
> on state created *before* the fix — a row from an old connector install, a
> migration that ran before this code existed, a stale cache/index? If yes, seed
> that pre-existing state first (with the pre-fix shape, e.g. a row missing the
> backfilled column), THEN exercise the code path under test (re-apply, read,
> projection compile), THEN assert. Seeding a fresh row and applying the fix
> proves nothing: a row your test just created is always produced by the
> current (already-fixed) code, so the test is green whether or not the real
> defect — which lives in already-installed/pre-existing rows — was ever
> touched. Worked example, from a backfill fix: the test seeds a record with the
> backfilled field *unset* — modeling one installed before the backfill path existed —
> then runs the backfill and asserts the field
> fires, instead of a fresh end-to-end install. (, , .)
>
> **Never hand-construct the state whose production is your fix's claim.**
> A fix has two halves — *produce the state*, and *act on the state*. A test that
> builds the state by hand and asserts the second half is a real assertion, but it
> is not the one that catches your bug, because a fix's defect is almost always a
> failure to **produce**. Hand-construction looks like: injecting a live run into a
> snapshot, supplying the prop whose population is the claim, mocking the endpoint
> whose response is the claim, pre-setting the field your code is supposed to stamp,
> or taking the code path that already satisfies the guard you added. **Two triggers
> make this checkable — apply them literally:**
>
> 1. **Claim about a rendered surface → one assertion against that rendered
>    surface.** Not the served JSON, not the raw SSE bytes, not `renderHook` with
>    state injected. Mount the thing a customer looks at. (A marker can persist,
>    serve correctly, and still be dropped by a render-time filter — that is how
>    this campaign produced its one false verification.)
> 2. **You added a guard → one test drives that guard from the entry point a
>    customer uses.** Not the path that already engages it. If the UI pre-mints the
>    thread and your test lets the server mint it, you tested the one path where the
>    gate was never in question.
>
> Measured basis, so this is not folklore: across one re-verification range, 3 of 7
> merged fixes failed live in exactly this gap, and the 4 that passed would have
> passed whether the product worked or not (). Roughly half of recent fixes
> already meet this bar without being asked — if yours genuinely does, say so in the
> report and move on. **Honest limit:** no test shape catches a false *claim* in copy
> ( — a caption asserting an enforcement property that was untrue, with every
> assertion passing). This bar does not replace live adversarial verification.
>
> **Verification you run (FAST only):** your language's fast static check over the package
> you touched; ONE targeted test run, narrowed to the case you wrote; and at most the SINGLE
> narrowest lint `make lint` offers for what you wrote. <20 min, ≤4 files, one layer.
> If it's bigger, STOP and report so the coordinator can split it.
>
> **Report back in this exact shape:**
> 1. What you implemented (brief).
> 2. Tests written (files + count).
> 3. **Red→green evidence** — for each behavioral test, its FAILING output
>    before your change, then its PASSING output after. For a mechanical task,
>    write "mechanical, no red phase".
> 4. Verification results (pass/fail per command).
> 5. **Gotchas to propagate** — anything the next sub-agent should know:
>    lints you tripped and how you fixed them, a file you had to touch that
>    wasn't in your list, a shared symbol/signature you changed, an assumption
>    that turned out wrong. Write "none" if none.

## 3. Codegen is the coordinator's job

Running `make generate` inside a sub-agent is the single biggest cause of
socket timeouts, and two sub-agents running it concurrently corrupt each
other's view (the 0074 B1/B2 `runs.go` collision). Sub-agents edit the
*source*; the **coordinator runs `make generate` once at the head of each
wave's gate** and confirms the only diff is generated output. A dirty *source*
diff after codegen means a sub-agent's edit was incomplete → dispatch a fix.

**Shared contract generators (which source → which target).** The source-to-target map is
the repo's own — it names that repo's files, its generators and its output paths — and it
lives in the **`codegen`** slot. Read it there rather than from here; a copy in the shared
tier is a second map that goes stale the first time a repo adds a contract.

What is portable is the discipline around it, and it is where the misses actually happen:

- **Edit the source, never the output.** A generated file edited by hand is reverted by the
  next generator run, silently, usually in someone else's PR.
- **One source can have more than one generator, and the second is the one people skip.** If
  `slot:codegen` names two targets for a source, a change to that source needs both —
  the first typically keeps the compiler happy while the second keeps a freshness gate
  green, so skipping it fails CI rather than the build, long after the edit.
- **Stage every path the run touched.** Enumerate with `git diff --name-only` after
  regenerating and stage all of it. The commonly-missed one is not the file you were
  thinking about: it is the aggregate the generator rewrites alongside it (an index, a
  querier, a union type).
- **Not everything derived is generated.** Some surfaces are hand-written by deliberate
  choice; `slot:codegen` says which, and editing the "generated-looking" file directly
  is right for those.

## 4. The per-wave loop (commit after every wave — let pre-commit be the gate)

Do **not** hand-run the heavy suites repeatedly. After each wave whose tree is
green-and-compilable, **commit** — the pre-commit hook runs the fast,
Docker-free gate (lint + staticcheck + Go **unit** tests + codegen-drift) in
~1–2 min, in parallel, **without `-race`**. One commit per wave localizes any
failure to the wave that caused it.

**The DB-integration and e2e suites are no longer in the local pre-commit gate
— they run isolated in CI** (`make test-db` and `make test-e2e`, as the jobs
`slot:gate` names). They
were unreliable as a local gate on contended dev boxes (false cross-talk
failures, runs overrunning the session window) and were routinely bypassed with
`--no-verify`. **CI is now the authoritative DB/e2e/coverage gate.** So the
integration signal arrives when CI runs your branch — but that does **not** mean push
per wave. **Batch the pushes:** commit each wave locally, and push once at the hand-off
(with the flow-retro and any notes/salvage folded in), plus any corrective push that
fixes a red check. A push while the PR's own CI is in flight cancels the earlier run and
wastes its runner-minutes, and rebasing to be current rewrites every SHA for nothing —
`push.md` Step 2/3 is the authority. Don't conclude "green" from a clean local pre-commit
alone.

**Run `make pre-commit-dry` before the FIRST commit attempt of a wave.** Several
pre-commit failure classes only surface *after* a ~4-min commit cycle —
**gofmt** re-stage, **staticcheck** dead code, and the **Go-unit coverage**
ratchet. `make pre-commit-dry` runs exactly those locally in one pass
(auto-fixing gofmt, reporting the rest); fix what it flags, then commit
once. (Where the repo's `make pre-commit-dry` answer names a fast mode, it skips the slow coverage gate.) This collapses
the repeated reject-cycles that recur across runs.

Per-wave coordinator gate, then commit:

```bash
cd "$(git rev-parse --show-toplevel)"; {
  echo "### GENERATE ###"; make generate;  echo "GENERATE_EXIT=$?"
  echo "### BUILD ###";    make build;          echo "BUILD_EXIT=$?"
  echo "### LINT-FIX ###"; make lint-fix;       echo "LINTFIX_EXIT=$?" # auto-fix mechanical lints first
  echo "### LINT ###";     make lint;           echo "LINT_EXIT=$?"   # the aggregated failure set, not the first
  echo "### DONE ###"
} > logs/gate.log 2>&1
```

- **`make lint-fix` first.** It auto-applies every analyzer's mechanical fix to a
  fixpoint, reconciles imports, and gates each round on `make build`.
  Baseline growth is forbidden, so every violation must be fixed regardless —
  `lint-fix` does the mechanical ones (the import ripple it triggers is work you'd
  do by hand anyway). Review its diff, then run `make lint` to see what remains.
  For the cascading retypes (typedid, incompletecastlint), `LINT_FIX_CASCADE=1
  `make lint-fix`` applies them in one pass; the tree may then not compile (by
  design) — resolve the surfaced type errors to finish the propagation.
- **`make lint` now runs all families in parallel and aggregates EVERY failure
  to ``** (it no longer fail-fasts at the first family).
  Read that file to see the complete failure set in one pass — fix them all,
  then re-run once. Do **not** walk lints one-at-a-time.
- **Never hand-run the race-detector lane** — where `make test-unit`'s answer says
  it carries one, it is slow and memory-pressured and the source of the known flakes.
  The pre-commit hook runs the unit lane without it; the DB-integration + e2e suites run
  in CI. The race detector is a nightly-only concern.
- Then commit the wave (stage by **explicit path** — never blind `git add -A`,
  which would sweep unrelated in-flight working-tree changes). **Never
  `git stash` / `git stash pop`** on a checkout that has (or may have) sibling
  agents' uncommitted work — the stash is global and will scoop every concurrent
  edit (see §1 shared-checkout fanout contract + §2 ban; ). For a
  clean-main comparison use a disposable `git worktree add` or
  `git show origin/main:<path>`, never stash. The pre-commit hook is the
  test/e2e gate; if it fails, read its per-pipeline logs (it writes them to a
  temp `$OUTDIR/*.log` — the failure summary is printed) and fix.

**Commit via the commit contract in [`push.md`](#) — and the load-bearing invariant is the
foreground HEAD-moved verify (§4b), NOT who runs `git commit`.** Default to a commit
sub-agent running the `push.md` commit contract (stage by explicit path →
pre-commit → fix EVERY failing hook, never loosen → retry until green → **verify HEAD
moved** → return the new SHA) — it keeps pre-commit log-reading out of the coordinator's
context. The worst failure of the 0075 run (claiming "shipped" when every commit had been
rejected) was born from *skipping the foreground verify*, not from who typed `git commit`.

**Coordinator-direct commit is an explicit sanctioned alternative** (use it especially once
a commit sub-agent has dropped on this commit). A commit bundles stage + a multi-minute
pre-commit + fix-and-retry into one task — the exact 50+ min drop-prone shape §10 warns
about; in the 0074/0075/0077 runs the *delegated commit was the single most drop-prone
dispatch*. When the coordinator commits directly, run `git commit` in the **FOREGROUND**
(it blocks the turn through the ~3–4 min pre-commit) and **verify HEAD moved (§4b)**:

```bash
# Reap orphaned pre-commit procs from any prior killed attempt FIRST — a leftover
# pre-commit-parallel and its go-test children OOM-contend the next gate (spurious -9/timeouts).
# Safe: no other test run is live mid-commit.
pkill -9 -f '<slot:gate>' 2>/dev/null; sleep 1
BEFORE=$(git rev-parse HEAD)
[ENV...] timeout 600 git commit -F <msgfile> 2>&1 | tail -40; RC=${PIPESTATUS[0]}
AFTER=$(git rev-parse HEAD)   # assert AFTER != BEFORE before claiming committed (RC=0 ≠ commit landed)
```

**Author `<msgfile>` with a genuinely unique path, then assert identity before
`git commit -F`** ([`autonomous-drive.md`](autonomous-drive.md) Rule H /
). Preferred: `MSGFILE=$(mktemp "${SCRATCHPAD:-/tmp}/commitmsg.XXXXXX")`
with a **trailing** `XXXXXX` template only (a mid-name template is a silent
macOS footgun — see Rule H). Write the message with the Write tool into that
path — never pipe a heredoc into `git commit -F -`. A heredoc / `-F -` (stdin)
message cannot be combined with `2>&1 | tail` in the same statement (the pipe
consumes the heredoc and the message is lost) and `-F -` is fragile in the
background / non-interactive shells the daemon runs. **Before every
`git commit -F <msgfile>`, grep the file for this run's own primary issue key
and fail closed on mismatch** — sibling agents in one session share one
scratchpad, and a naming convention alone already failed under live concurrency
(; two commit-message substitutions in one night). Example:
`grep -Eiq "\b<KEY>\b" "$MSGFILE" || { echo "commit msg missing own key" >&2; exit 1; }`.
Do **not** use a bare shared name (`commitmsg.txt`, `msg.txt`) or a
`$RANDOM`-only path without the assert — both are last-write-wins under sibling
fan-out.

**Foreground, NOT background-bash — load-bearing whenever the session can be resumed or torn
down mid-turn, which is ALWAYS true under the headless `linear-agent` daemon (`claude -p`).** A
backgrounded `git commit` is reaped by turn-teardown (~1–2 min) *before* its ~4-min pre-commit
finishes, so HEAD never moves; the daemon then resumes, re-spawns the commit, and the
killed-but-orphaned gates pile up and OOM-contend — the resume-cycle nudge-spiral that cost PRD
0124 **28** resume-cycles (see its retro). A foreground commit blocks the turn (so it
survives) and finishes the ~4-min gate well inside the daemon's idle watchdog; the foreground
`git rev-parse HEAD` is the proof. **Never `--no-verify`** — foreground keeps the full local gate
(CI is not a substitute for it here). Stage by explicit path (never `git add -A`) either way. Run
`make pre-commit-dry` (gofmt auto-fix, staticcheck, Go unit
coverage; `FAST=1` skips coverage) on your changed files **before** the first commit
attempt, so format failures surface in seconds instead of as a rejected
~4-min gate cycle. **A line-keyed lint baseline is invalidated by any diff above it.** Where
`make lint`'s answer names baselines that grandfather existing violations by line number,
a change that shifts those lines silently invalidates the entry — and the fast local
pre-commit typically does not catch it; only the full static-analysis lane does. Re-key the
baseline in the same commit.

**A *sweeping new* line-keyed baseline is a fleet-wide drift magnet — don't create
it, and if you must, freeze the repair.** When a wide-scope checker + baseline first
lands (e.g. 's `ctxscopedlogging`), every in-flight PR that rebases across the
landing commit re-triggers drift in the same one or two baseline files, and multiple
concurrent agents independently rediscover and re-fix the *identical* drift — racing
the same files into merge conflicts and burning rebase/CI cycles for weeks (eng-659
collided with three such agents on two files). Two rules, in priority order: **(1)
prefer not to create the line-keyed baseline at all** — a new sweeping checker should
be self-detecting with zero baseline files wherever possible (the /
direction; the **`languages`** slot's contract for that language
→ "DO NOT add any baseline entry"), because a baseline that does not exist cannot
drift. **(2) If one is genuinely unavoidable, route all of its drift-repair through
one coordinating issue/PR** for the freeze window rather than N ad-hoc fixes; an agent
that hits such drift mid-task still fixes it inline (the commit contract forbids
skipping "not my change"), but takes upstream's already-landed version on conflict
instead of re-litigating, and notes it as transitional baseline churn in the PR body.

The
coordinator's only job around a commit, however it runs, is: hand over the file list +
message, then read back the foreground-verified SHA.

**When even a foreground commit would exceed the tool's turn ceiling** — a
contended host whose pre-commit runs many minutes, or waiting out multi-round CI
across turns — a plain background `git commit &` / `run_in_background` still
loses: turn-teardown reaps it (above), and `Monitor` / `ScheduleWakeup` don't
reliably buy proportional wall-clock. The one detach that **survives** teardown
is a fresh session cut from the turn's stdio, after which you poll the **log file
+ PID (`kill -0 <pid>`) + `git rev-parse HEAD`** across turns for the moved SHA,
never the backgrounded call's own exit. (eng-286, eng-460.)

**`setsid` is Linux-only — the recipe must be portable.** macOS has no `setsid`
(it is util-linux), so `setsid nohup … &` on a Mac dev box exits 127 into the log
and **launches nothing, silently** — a failure that has cost two sessions their
detach. Nor is a bare subshell enough: `( <cmd> … & )` reparents to init but
*stays in the caller's process group* (measured: child `pgid` == the tool shell's
`pgid`), so a tool-call timeout's process-group SIGTERM still reaps it. Use the
portable form, which yields a real session leader on both platforms
(measured on Darwin: child `pgid` == its own pid, `ppid` == 1):

```bash
# Write the branch out in full — do NOT collapse it into `${VAR:-perl ...}`:
# zsh does not word-split a parameter-expansion default, so that form runs a
# single 40-char "command not found" and launches nothing (verified 2026-08-18).
if command -v setsid >/dev/null 2>&1; then
  ( setsid <cmd> > logs/x.log 2>&1 < /dev/null & )
else
  ( perl -MPOSIX -e 'POSIX::setsid(); exec @ARGV' -- <cmd> > logs/x.log 2>&1 < /dev/null & )
fi
```

**Then confirm it actually launched** — capture the pid (`pgrep -n -f
'<distinctive-literal-marker>'`) on the very next call, every time, not only when
something looks wrong. Two failures ride on skipping it: a detach that never
started (above), and three back-to-back relaunch attempts while iterating on the
detach form leaving three concurrent copies of the same `make` pipeline racing
each other. Poll that captured pid with `kill -0 $PID` — never re-run a `pgrep -f`
whose pattern can match the poller's own command line (an alternation like
`pgrep -af 'A|B'` matches the very shell that typed it).

**Serialize commit → next wave (load-bearing).** Do **not** dispatch the next
wave's editing sub-agents until the prior commit sub-agent has returned a
verified SHA. A commit's pre-commit runs lint + Go unit tests (plus gofmt /
codegen-drift, which mutate files) for ~1–2 minutes; if the next wave's agents
edit files during that window, the commit fails on a half-written tree (false
failures, rejected commit). Commit and edit are mutually exclusive — one wave's
commit fully lands before the next wave starts editing.

**Single-owner for shared codegen-source files.** Never let two concurrent
sub-agents edit the same file `slot:codegen` names. Give each shared source file
ONE owning task per wave; if two tasks both need it, serialize them or fold them into one.
(Concurrent edits to one codegen source in the 0075 run appended ~130 duplicate lines and
corrupted the file.)

### 3a. Migrations are timestamp-named — mint the id at implement-time, never count

**Where a repo's migrations carry a timestamp id there is no "next number"** — run the repo's
migration-authoring tool (its README names it) and write your SQL into the file it creates. Never
type a counted number by hand and never renumber on a rebase: timestamp ids cannot clash. The renumbering guidance below applies only to repos that
still count their migrations.

#### Counted-series repos: compute the migration number at implement-time, never trust the plan's

The plan names migrations with a placeholder (`00NNN_<slug>`, per
[`plan.md`](#)). Before dispatching the
migration task, the **coordinator** reserves the real number with
`python3 knowledge/scripts/validate_id_collisions.py --allocate <migration-prefix> 1` — which accounts for open peer branches as well as
the main tip — and briefs the sub-agent with that concrete name. A literal baked at
plan-time goes stale the moment a concurrent branch lands a migration, forcing a renumber
(and often a hand-resolved conflict in whatever list test the repo keeps over its
migrations). On a busy `main`, also expect to renumber on rebase/merge: if CI or the merge
surfaces a collision, bump to the next free prefix and update the migration-list test in
the same commit — it's mechanical, not a regression. Where that list lives in one very long
literal, prefer a small inline script to splice the new filename in rather than
hand-editing the line.
**Always write the full filename in prose, never a bare number.** "migration 01709"
is unsearchable, so the renumber above cannot be done as a mechanical rename and
leaves dangling references; write `01709_<slug>.sql` everywhere — PRD, plan, ADR,
commit message — so `grep` finds every site a renumber has to touch.

Waves that aren't independently green (e.g. a foundation wave whose later waves
fill in behavior) should be designed to compile + pass with no-op defaults so
the wave boundary is committable. If a wave genuinely can't be green alone,
commit it together with the wave that completes it.

## 4b. Status truth — never claim done without a foreground check (load-bearing)

A confident wrong "done" is worse than any slowdown — it destroys trust and
forces re-grounding the whole state. Background-bash and async sub-agent results
in this environment stream back **interleaved and buffered**; a streamed log line
saying "committed" / "pushed" is NOT proof. Every status claim needs a
**foreground** `git` check, captured right before you assert it:

- **"committed"** ⇒ `git rev-parse HEAD` moved vs the pre-commit SHA. If HEAD is
  unchanged, the commit was REJECTED (a hook failed, everything's still staged) —
  it did not land, no matter what the log said.
- **"pushed" (branch)** ⇒ `git rev-parse origin/<branch> == HEAD` after the push,
  i.e. the branch's commits are on the remote. **`Everything up-to-date` after a
  push you believe added commits is a RED FLAG** (0 commits ahead — nothing was
  there to push), not success.
- **"merged" / "shipped"** ⇒ the PR's CI is green AND it merged to `main`: the
  squash commit is on `origin/main` (`git fetch origin && git rev-parse origin/main`
  advanced), and `gh pr view <pr> --json state` reads `MERGED`. Code-bearing work
  ships **only** through a PR merge — never a direct `git push origin HEAD:main`.
- **"verified"** ⇒ the verify matrix is shippable (all-PASS, or pass-with-follow-up per
  `prd:verify` Step 4 Path A), never an assumption from a prior step.

Apparent sub-agent silence ≠ dropped — results often arrive minutes later. Do
**not** re-dispatch on silence; wait for the real result (or a deterministic
file-watcher signal). Re-dispatching a still-running agent wastes its work and
muddies the picture. (See §10 for genuine socket drops.)

## 5. Read results from files + exit codes — never `ls -t` a tee log

Two self-inflicted time sinks to avoid:

- **Trust the captured exit code, not a grep of a log.** Capture
  `make X; echo X_EXIT=$?` and read that. `make lint`'s full output is always
  in ``; the pre-commit's is in its `$OUTDIR/*.log`.
- **Never pick a tee log by `ls -t | head -1`** — it grabs whichever file is newest,
  which is often a *different* run than the one you just executed, so you end up
  investigating stale failures in already-green tests. Use the deterministic report files
  above.

## 6. Learn within the run (feed sub-agent gotchas forward)

The coordinator maintains a short **Run Gotchas** list (cap ~10, deduplicated).
Each sub-agent's report ends with "Gotchas to propagate" (§2). The coordinator:

- Appends genuinely-new, run-specific gotchas to the list (a shared-file
  collision, this PRD's required sqlc override, a signature another wave
  depends on). Skip anything already covered by the contract files — that's
  static knowledge, not a per-run lesson.
- **Injects the current Run Gotchas into every subsequent sub-agent prompt** so
  the next agent doesn't repeat a mistake.
- When a gotcha recurs across *runs* (not just this one), **promote it into the
  contract file** so future runs start clean.

## 7. Integration seams between sub-agents (the bug class that hides)

Sharding work for parallelism creates seams that no single sub-agent owns — the
0074 `AgentKey` regression lived between the seam-placer (B6), the impl (B7),
and the wirer (B13w), and nothing caught it until e2e. Mitigations:

- Give a **cross-cutting seam a single owner** where practical (e.g. "auth
  context assembly" or "runner option wiring" is one task, not split across
  placement/impl/wiring).
- Where it must be split, **CI's end-to-end lane is the integration gate** — it runs
  `make test-e2e` on the pushed branch. The local per-wave commit (unit gate) won't catch
  a cross-agent seam by itself, and the push that surfaces it is the **single batched
  hand-off push** (not a push per wave — see §4). Treat that first CI run as the seam
  gate: read it, fix any seam it finds, and push the fix.

## 8. Don't run `make dev` during DB/e2e tests or a commit

`make dev` runs a live jobrunner/scheduler/ingest against the **shared dev DB**.
Running it concurrently with `test-go-db`, the e2e suite, or a commit's
pre-commit produces false failures in unrelated tests (session/quota/catalog/
sweep) via DB contention. Stop the dev stack before any DB/e2e run; restart it
only for the live-browser pass, and not while a commit is in flight.

**Use `make dev-headless`, not `make dev`, from any agent
session.** The interactive form assumes a TTY and dies without one — which is every
autonomous/daemon-driven session; the headless form is the same stack, same ports, same
seeding, with logs streaming to stdout. **Stop it with `make dev-stop`**
(): that is the one stop path that drains the stack in reverse dependency order
and reaches deep children; it is idempotent. Never start the stack in a mode that removes
its control socket, or every stop path but signal-scavenging goes with it.

**UI PRD + stack down → the COORDINATOR starts it (never stop to ask).** For a
UI PRD's mandatory live-browser pass, if the stack is down, the **coordinator**
starts it itself (background), polls the health endpoints until ready, then runs
the browser probe. **Probe the right ports and the right route:** ports are
per-checkout — `slot:dev-environment` says where to read them, never a default.
The route that proves the API is up is `slot:dev-environment`, and **only**
that route: a health-looking path that falls through to the SPA shell answers 200 on a
dead API, and that shape has sent runs chasing a phantom. Do NOT stop and ask the user
to start it — this is no longer a sanctioned stop. The "sub-agents must not autostart `make dev`" rule still holds: a probe
sub-agent reports "stack down", and the **coordinator** starts it and
re-dispatches. Keep the §8 ordering — start `make dev` only for the browser pass,
and stop it again before any subsequent commit / DB / e2e run.

**`make dev` is not the only contender — quiesce ALL heavy jobs during the pre-commit.**
The pre-commit runs several pipelines in parallel (go-lint, staticcheck, go-unit,
frontend vitest, …) — it can *saturate* the machine by itself (the heavy DB/e2e
testcontainer lanes moved to CI, so it's lighter than before, but vitest + go-unit
still peg the CPU). Anything else heavy
the coordinator has running on top of it over-subscribes and produces false failures in
unrelated tests. In the 0077 run, a still-running dropped commit sub-agent **plus** a
coordinator `make lint`/gate kicked off alongside the commit starved the e2e DB pool (a
resident-source `list documents` 500) and the vitest thread pool (frontend ran **1853 s**
with `Failed to start threads worker`) — two false commit rejections. Before committing:
(a) ensure no other heavy background job is in flight (a dropped/long sub-agent, a parallel
`make build`/`lint`/test gate) — wait for it or kill it; (b) run ONLY the commit. And
(load-bearing) **any pre-commit failure in a heavily-parallel run is a contention suspect
until isolation-confirmed** — re-run the specific failing test/lane *alone* (`-run X` /
`node probe.mjs`) before treating it as a real defect or re-committing. The frontend
vitest config is already tuned for this (`pool: threads`, `maxWorkers = cores/2`,
`testTimeout: 30 s`); honor `VITEST_MAX_WORKERS` to dial it lower in especially contended
lanes rather than assuming a real failure.

## 9. Coordinator self-correction (change strategy when one is failing)

If the same gate fails ≥ 3 times, or sub-agents keep dropping on the same task
shape, **stop repeating** — split the task smaller, apply a trivial fix
directly (§1), or surface the blocker to the user. Re-running an identical slow
gate or re-dispatching into a known drop is the failure mode that turns a 6-hour
run into a 24-hour one.

## 9b. Autonomy in autonomous `/fleet:prd:implement` (default mode) — decide and log, never stop to ask

Autonomous `/fleet:prd:implement` (the default mode) runs unattended. It has **zero** sanctioned reasons to
stop and ask the user — including the one that used to be the exception (a UI PRD
with the dev stack down: now the coordinator starts `make dev` itself, §8).
**Every fork is resolved by picking the most defensible default and recording it
in the Autonomous Decisions Log** — collisions, ambiguous ACs, missing plan
files, verify false-negatives, under-specified details. Each `AskUserQuestion`
gate in this command is a process bug. (In the 0075 run, ~4 needless question
gates were the single biggest time loss the user flagged.) This is the standing
autonomous-mode Rule A; it is restated here because it is load-bearing and
easy to drift from under uncertainty. (The `--manual` mode of `/fleet:prd:implement`,
run interactively, may still surface genuine blockers — this rule is specifically
the autonomous default-mode contract.)

## 10. Socket drops (the delegation tax)

Sub-agents in this environment can hang ~15–23 min then drop with the report
lost. When that happens: (a) **don't trust the lost report** — re-derive what
landed via `git status` / reading the files; (b) if the remainder is trivial,
finish it directly (§1); (c) on re-dispatch, **split smaller** — long tasks
drop more. Enforce the <20-min / ≤4-file / one-layer budget hard; it is the
best predictor of whether an agent survives.

## 11. End-of-run flow retrospective (the mandatory LAST step)

Every `/fleet:prd:implement` run (autonomous or `--manual`) ends — **pass, fail, or withheld** — by
writing a retrospective of *how the run went* (not the feature) into the directory
`slot:retro-corpus` names, under the file name and with the frontmatter that slot
prescribes — the `owner:` is the join the harvester groups by — then committing it. This is a
**record + suggestions only — it does NOT modify the flow, the commands, or the
contracts.** The user reviews these periodically and promotes good suggestions
by hand; a fix that keeps getting re-suggested across PRDs is the signal that
the process (not the PRD) needs to change.

**Author it as the coordinator, from your own run history** — you have what no
sub-agent does: the gate-run count, which lints cascaded, which sub-agents
dropped, how many commit attempts each phase took, the fix-loop rounds, and the
Run-Gotchas list (§6) / Autonomous Decisions Log. **Be candid and self-critical
— this file exists to improve the process, not to justify the run.** Don't
soften "I re-ran the gate 12 times" into "verification was thorough."

**Before writing, skim the 2–3 most recent records in `slot:retro-corpus`.** Any friction or suggestion that *also* appears there is
**recurring** — flag it loudly in the "Recurring across PRDs" section; recurring
means the earlier suggestion was never adopted or didn't work.

Write the file to this template (keep the headings stable so runs are
comparable; fill the metrics from what you actually observed, rough is fine):

```markdown
---
<the `type:` and `owner:` frontmatter `slot:retro-corpus` prescribes for a PRD record>
---

# Flow Retrospective — PRD NNNN <title>

> Auto-written by the implementation flow's final step (#11).
> Records how the RUN went, not the feature. **Suggestions here are NOT applied** —
> review periodically and promote good ones into the flow/contracts by hand.

## Run metrics (rough)
- Command / outcome: <implement (autonomous | --manual)> / <shipped | verified | withheld: gaps …>
- Waves: backend <N> / frontend <M>
- Coordinator gate runs (regenerate / build / lint): ~<X>
- Commit attempts: backend <X> (<Y> failed → <why>), frontend <X> (<Y> failed → <why>)
- Sub-agent dispatches: <N>; socket drops / hangs: <K>
- Lint fix→re-run cycles: <K>   ·   fix-loop rounds: <R>/3
- Rough wall-clock vs expectation: ~<X>h (expected ~<Y>h)

## What went smoothly
- …

## Friction / time sinks (ranked by cost)
| # | What ate time | Rough cost | Category (mechanical / discipline / infra) | New or recurring? |
| - | ------------- | ---------- | ------------------------------------------ | ----------------- |

## Failures encountered (real feature bug vs process artifact)
- <failure> — <real bug | flaky/contention/stale-log/test-fixture> — <how resolved>

## Root-cause synthesis (what was *actually* the problem)
- …

## Suggestions (NOT applied — for later review)
| Suggestion | Lever (mechanical / doc / infra) | Effort | Friction it addresses | Already in the contract/process? |
| ---------- | -------------------------------- | ------ | --------------------- | -------------------------------- |

## Recurring across PRDs (flag loudly)
- <lesson that also appeared in a prior PRD retro — cite which PRD>
```

Commit the retro with the run's final commit (or its own
`chore(NNNN): flow retrospective` commit if the feature is already committed) —
**on the work branch, before `/fleet:push` / the handoff**, so it rides the
deliverable PR. **Never a second PR** (: a post-handoff retro PR is
re-held forever and parks the issue on a human). It is a record, written after
the work is done — it must never block shipping.

## 12. Pre-dispatch budget guard (mechanical — run before EVERY sub-agent dispatch)

The <20-min / ≤4-file / one-layer budget (implement Rule 13, §10) was a *target*
a too-large task could quietly blow past — and over-budget tasks are the top
recurring cause of socket drops in both flow-retros (0074 ranked it #3 and named
"a pre-flight that refuses to dispatch an over-budget task" an unaddressed
residual). Make it a **gate, not a target**: before dispatching any
implementation or fix sub-agent, the coordinator runs this check on the task's
own file-list and STOPS if it fails.

For the task about to be dispatched, count from its explicit **Files to modify**
list (the plan's, or the fix's):

- `N_files` = number of distinct files the task will edit.
- `N_layers` = number of distinct layers spanned, where the layers and the paths
  each owns are `slot:file-conventions`' answer. Codegen *source* edits count
  toward the layer they live in. **Where that slot is unfilled the layer half of this
  gate does not apply and the run says so** — it never evaluates to zero and passes.

**Gate:** if `N_files > 4` OR `N_layers > 1`, do **NOT** dispatch as-is. First
split the task into ≤4-file, single-layer sub-tasks — by file group, by layer,
or by the seam (place shared seams/signatures in one task, fill behavior in
others, per §7) — then dispatch the pieces (parallel if they touch disjoint
files, serial if they share one). A single shared codegen-source file
(any file `slot:codegen` names) must have exactly one owning sub-task per wave (§4).

This is mechanical: it reads the file-list and arithmetic, not judgment. The only
escape is a task that is *genuinely* one indivisible edit spanning 5 files (rare
— e.g. a single rename across its call sites); log it as a deliberate exception
and dispatch with an explicit "this is one atomic edit" note so the sub-agent
doesn't try to scope it down. Everything else over budget gets split. A plan that
keeps producing over-budget tasks is a planning smell — note it in the
flow-retro so `/fleet:prd:plan` can be tightened.
