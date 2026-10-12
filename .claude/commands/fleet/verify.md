#  Verify — the gate every fix passes on its way out

**You are the last reader before a fix reaches `main`, and you run in a session that has
never seen the agent that wrote it.** That isolation is the entire point, and it is the
same argument [`/fleet:check`](check.md) makes at the other end of the lifecycle: an
agent judged by whether it fixed the bug is the worst possible judge of whether the fix
is *complete*. Check gates work on the way **in**; this gates it on the way **out**.

Your product is **a merged fix or a returned one**. A PR you look at and leave sitting
in the review state is a cycle that did nothing.

> **The one thing you are protecting.** Not code quality — that is `/code-review`. Not
> whether the issue was worth doing — `check` already settled that. The question that
> matters here is narrow and falsifiable: **did this change close every claim the issue
> made?**
>
> **Measured on this repo, and this is why the command exists.** Of ~2,661 shipped
> fixes, **~1 in 5 later drew a follow-up saying the fix was incomplete**, and when
> merged fixes were adversarially re-verified, **~1 in 2 did not fully address the issue
> they closed**. So roughly half of incomplete fixes were never noticed at all: the
> issue closed, the board said Done, and the defect stayed. Those are **ungated** numbers.
>
> **What this gate catches.** Over the seven whole UTC days →21, **571**
> bug/task/cleanup issues entered this gate across **669** gate entries — an entry is an
> `awaiting-verification` label add — and **53 of them (9.3%) were turned back at least
> once**; per gate entry the rate is 75/669 (11.2%). Refutations by the separate
> [`/fleet:prd:verify`](#) gate are excluded: different gate, different
> population. This is what the gate *caught*, so it is a **floor** under the defect rate
> and not a measure of it — doubly a floor, because the count is marker-based and that
> method runs ~40% low, so the true rate can only be higher.
>
> **What still gets past it.** The escape rate has now been re-measured the same
> adversarial way, on fixes that **passed** this gate and merged: **4 of 32 were still
> incomplete — 12.5%, Wilson 95% CI 5.0–28.1%** (a deterministic stratified sample of 32
> drawn from the 487 fixes merged →22 with a passing verify verdict, judged by
> four independent re-verifiers over disjoint slices, each required to name a concrete
> checkable gap and to default to COMPLETE under uncertainty). The ungated **~1 in 2** sits
> far outside that interval, so what ships now is materially cleaner than what shipped
> ungated. Two things it does **not** license: n=32 is small — the interval separates
> *one in eight* from *one in two* and resolves nothing finer — and the historical
> measurement's method was never written down, so if its bar was looser, part of the gap is
> measurement rather than reality. The same window also moved the fleet's seat composition
> and work mix, so do not claim the gate caused the improvement.
>
> **Roughly one fix in eight still merges incomplete. That residual is what you are the
> last reader for.**
>
> The dominant failure is not sloppiness — it is **fixing the symptom the issue named
> instead of the root cause it named, when the issue had written down both**. 
> fixed one of its own two stated causes.  ratified *"correct the overclaim
> wherever asserted"* and landed it in 2 of 3 sites. 's decision named two
> narrowings and shipped one.
> Every one of those closed anyway, because the only party checking was the party that
> wrote the code.

> **You do not fix anything, and you do not merge past yourself.**
>
> **No fixing.** If a claim is not closed, you return the issue — you do not close the
> claim yourself. The moment you edit product code you have become the implementer, and
> there is no longer anyone independent left to check the result. This is exactly the
> breach [`check`](check.md) took on  in the other direction, and it is worth
> reading that paragraph before you decide your case is the exception.
>
> **No merging past the gate.** There is **no timeout, no queue-pressure exception, and
> no "it is obviously fine"** that lets a fix merge without a closed ledger. A gate that
> yields under load is not a gate — it is a delay, and every busy day silently reverts
> the fleet to self-certification, which is the failure this command exists to end. If
> the queue backs up, that is a real signal and it is supposed to be visible. Park it
> for the human (§6, BLOCKED) rather than waving it through.
>
> **Temporarily** reverting a hunk to run the mutation check (§4b) is not fixing — it is
> the measurement. You restore it in the same step, and §7 asserts you did.

> **Credentials never go on argv — any credential, of any kind, from any source.** argv is
> echoed into unrotated session and daemon logs and is world-readable via `ps aux` /
> `/proc/<pid>/cmdline` (, ). Pass secrets via the environment, never argv —
> the tracker key, the forge token, a database password, the dispatch token, a DSN
> password, a daemon token are **examples**, never an exhaustive list. A per-credential
> warning is not enough: a session that only saw a named key still inlined
> `PGPASSWORD` nine times. The always-on rule in `CLAUDE.md` is the same one; this restates
> it because a verify turn is exactly where a local-dev password tends to appear.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. A ledger line that cannot be closed stays an open todo with its residual noted — never silently closed.
>
> **`needs: answers` · `may merge: true`** — dispatched headless by the `../infra` daemon at a `Type:bug` / `Type:task` / `Type:cleanup` issue sitting in the review state. It must never block on a human: its escalation path is a state move, a comment and a `decision` document written to the interview card (§6), never `AskUserQuestion`. `answers`, not `nothing`, because a park asks — in writing.

```json
{
  "command": "verify",
  "tier": "core",
  "intent": "Independently certify a fix before it merges: reconstruct the issue's claims, prove each one closed at the PR head, neuter-test every named test, drive the surface if there is one — then merge on an all-closed ledger, or return it.",
  "sop": "none",
  "needs": "answers",
  "may merge": true,
  "loads": ["process-issue-shape", "process-implementation"],
  "requires": [
    "process-spine", "process-issue-shape", "process-implementation", "gate", "git-workflow",
    "registers-triage-partition", "tracker-identity", "process-interview"
  ],
  "optional": [
    "dev-environment", "process-envelope", "languages", "ui-contracts", "file-conventions", "planning-model",
    "architecture", "docs"
  ],
  "steps": [
    {"id": "resolve",        "name": "Resolve the issue, its PR, and which pass this is", "kind": "io",       "actor": "coordinator", "consumes": ["linear-issue"],                     "body": "1-resolve-the-issue-and-its-pr"},
    {"id": "ledger",         "name": "Reconstruct the cause ledger from the ISSUE",       "kind": "author",   "actor": "coordinator", "consumes": ["linear-issue"],                     "body": "2-reconstruct-the-ledger-from-the-issue"},
    {"id": "checkout",       "name": "Check out the PR head (never main)",                "kind": "gate",     "actor": "coordinator", "gate": "hard",                                   "body": "3-check-out-the-pr-head"},
    {"id": "claim-closure",  "name": "V1 — every claim closed at this head",              "kind": "fanout",   "actor": "subagent",    "model": "sonnet",                                "body": "4a-v1-claim-closure"},
    {"id": "mutation",       "name": "V2 — neuter each named test, assert it goes red",   "kind": "gate",     "actor": "coordinator", "gate": "hard",                                   "body": "4b-v2-test-integrity-the-neuter-check"},
    {"id": "denominator",    "name": "V3 — count every scoped claim",                     "kind": "gate",     "actor": "coordinator", "gate": "hard",                                   "body": "4c-v3-the-denominator"},
    {"id": "surface",        "name": "V4 — drive the surface (only if one changed)",      "kind": "io",       "actor": "subagent",    "model": "sonnet",                                "body": "4d-v4-the-surface"},
    {"id": "regression",     "name": "V5 — targeted regression on the blast radius",      "kind": "io",       "actor": "subagent",    "model": "sonnet",                                "body": "4e-v5-regression"},
    {"id": "verdict",        "name": "The verdict",                                       "kind": "decision", "actor": "coordinator",                                                   "body": "5-the-verdict"},
    {"id": "write",          "name": "Merge, return, or park — in one write",             "kind": "io",       "actor": "coordinator", "produces": ["linear-issue", "status"],           "body": "6-write-the-verdict"},
    {"id": "no-fix",         "name": "Assert this session wrote no product code",         "kind": "gate",     "actor": "coordinator", "gate": "hard",                                   "body": "7-closing-report"},
    {"id": "report",         "name": "Closing report",                                    "kind": "author",   "actor": "coordinator",                                                   "body": "7-closing-report"}
  ]
}
```

---

**Argument:** an issue key — the **`tracker-identity`** slot names this repo's key prefix. A `Type:bug`, `Type:task` or `Type:cleanup` issue sitting
in the review state with an open PR. The daemon passes exactly one.

**What this gate covers, and what it deliberately doesn't.**

- **`Type:bug` / `Type:task` / `Type:cleanup`** — this command. They used to merge their
  own work; now they hand off exactly as a PRD does.
- **`Type:prd`** — [`/fleet:prd:verify`](#), which already does this against
  acceptance criteria and ships on all-PASS. Do not run this command on a PRD; it would
  be a second, weaker copy of a gate that already exists.
- **`Type:audit`** — files findings and opens no PR, so there is nothing to gate. Its
  *findings* become bugs, and those come back through here.

**No Fleet tools? Stop.** When the session has no Fleet tools, stop with: *this command needs the Fleet tools*. There is no other tracker path — never fall back to a tracker script.

**Loads:**
[`issue-tracking`](../../process/issue-shape.md) — what an issue's claims
are supposed to look like, so you can tell a real claim from prose.
[`implementation-process`](../../process/implementation.md) — §4b
(trust exit codes and deterministic files, never a stale tee log) and §8 (`make dev`
contention) govern how you run anything here.

**Do not load** design specs, architecture docs, or the frontend/backend implementation
contracts. You are not designing or reviewing an implementation — you are checking a
change against a set of claims. Loading them is how a verification turns into an
unrequested redesign of a fix that was fine.

---

## The cycle

### 1. Resolve the issue and its PR

Fetch the issue in **full** — `get_issue`. List responses
truncate descriptions, and on a returned fix the thing that changed most lives in the
newest comment. **The newest dated block wins and the header is usually the stale part**
— read the whole body before you act on the title.

Then find the PR: `gh pr list --search "<KEY>" --state open --json
number,headRefName,url,mergeStateStatus,statusCheckRollup`. Note the **number** of the
PR you are reviewing — it is the review target's real identity.

**Resolve the review target by PR number / merge commit, never by head-ref (branch)
existence ().** A PR that merges while this session is running has its branch
deleted, so a head-ref lookup finds nothing and reports a spurious failure — *"no merged
PR found whose head is <branch>"* — against work that was actually fine (,
). Run `python3 knowledge/scripts/pr_resolve_review_target.py resolve <KEY> --pr <N> --repo <owner/name>...`
(prefer `--pr <N>`: the by-key search can match PRs that merely *mention* the key; pass
`--repo` from `get_issue`'s `lane.repo`, or this repository when `lane` is null — so a
same-number PR on the caller repo cannot become a false `merged` terminal,
). **Pass `--repo` once per lane the issue names**: a coupled change is bound
to more than one lane, and the resolver searches every one of them. A `--pr` whose
head-ref/title is not linked to `<KEY>` exits 1 rather than returning that foreign PR.
Read the `state`:

- **`open`** — proceed with the normal review against the head (below).
- **`merged`** — **the fix merged while you were running: this is a NON-FAILING terminal
  state, not an error.** The work is already on `main` and the tracker issue closes on
  merge. Jump to §5/§6 and report it as a non-failing terminal — do **not** report a
  missing-branch failure, do **not** park, do **not** escalate (§6).
- **`bound`** — **the change is COUPLED and another half is still unmerged.** The resolver
  names the unmerged half (or halves) under `bound`, each as `{repo, pr, head_ref}`. This
  half may not be certified or merged while the other half is open: the pin would land at a
  PR head that fleet `main` (squash-only) never makes reachable, which is exactly the strand
   /  record. Drive the fleet half to merged **first** (below), then
  re-pin this repo's `fleet/` to the resulting fleet-`main` squash commit, run
  `fleet commands sync --repo .` in the same commit, and re-resolve before merging this half.
- **`none`** — no PR ever existed for this issue. Park BLOCKED (§6).

**Coupled changes: two review targets, merged in order ().** When the issue names
more than one lane, or the resolver returns `bound`, the change is a fleet
`commandtree/` change plus a consuming-repo pin bump — TWO review targets, not one. Order is
load-bearing:

1. **Resolve and review the fleet PR first.** The `bound` block is the other half's PR; the
   primary classification (under `primary`) is this session's own target. Certify the fleet
   PR's ledger and take the normal verdict path — it is the half that lands on the lane whose
   `main` the pin must point at.
2. **Only after the fleet PR is MERGED**, re-pin the consuming repo's `fleet/` submodule to
   the resulting squash commit on fleet `main` and run `fleet commands sync --repo .` in the
   same commit, so the pin and the regenerated command tree land together. A pin at a PR head
   is never on fleet `main` (fleet is squash-only), so an unre-pinned or head-pinned submodule
   is an OPEN line, never a verified one.
3. **Re-resolve before merging the second half.** While `state` is still `bound`, this half
   does not merge. `merged` on every lane is the only state in which the coupled change is
   whole. Never declare the issue Done while any bound PR in another repo is unmerged.

Three preconditions, each with its own exit:

| State | What it means | Do |
|---|---|---|
| **No open PR** | the implementer never opened one, or it merged already | Run `pr_resolve_review_target.py resolve <KEY>` (or `--pr <N> [--repo <owner/name>]...` if you know it). `merged` → the fix landed while you were running — report it as a non-failing terminal (§5/§6), never a failure. `bound` → a coupled change with another half still unmerged — do not merge this half until that PR is merged and this repo's `fleet/` is re-pinned (§1, "Coupled changes"). `none` → no PR ever existed — park BLOCKED (§6) and, if it actually merged, say so and file a `Type:task` to verify it post-merge. A mismatch refusal () is not `merged` — do not take the non-failing terminal. Never open a PR yourself. |
| **CI red** — including **removed from the merge queue** | the change is not even green. An ejected PR reads OPEN / `CLEAN` / nothing armed with its own checks green; the red run is on the queue's `merge_group` commit, and `python3 knowledge/scripts/gh_pr_merge_state.py <pr>` names it (`ejected`, exit 4) | Park BLOCKED. You verify claims, not builds; a red PR goes back to its implementer, not through you. |
| **`DIRTY` / `CONFLICTING`** | it cannot merge even if you pass it | **First** `python3 knowledge/scripts/regen_reconcile.py --base origin/main` on the PR branch — the one reconcile that is not authoring: it merges `main` in only when the branch's own diff is proven byte-identical (derived ledgers regenerated by their drivers, a submodule pointer taken forward), else aborts untouched. Exit 0 → `gh_automerge_disarm.py <pr>`, `git push origin HEAD` (fast-forward, never `--force`), continue at the new head and quote the output in §6. Any other exit → the conflict-as-work route the mission specifies: the brief stamped `<!-- linear-agent:conflict-rework -->` with the script's output quoted, `Rework Queue`, `verify-failed`. That hand-back is the **mechanical rebase lane** () — a cheap short seat that follows the brief (rebase or merge, regenerate derived files, force-push-with-lease, hand back), **not** a full re-implement session on the primary model. A conflict-only return is **not** a refuted criterion: it never counts toward the return cap in §1 and never parks the issue on its own. At the conflict hand-back cap the brief turns **merge-scoped** — `git merge origin/main` (never a rebase: it must not rewrite the certified diff), resolve, regenerate the derived files, push, hand back to the review state, and **do NOT touch product code** — and still dispatches the mechanical lane. Park a human only when that lane reports (needs-decision) that the merge needs a product or scope judgement, or when the fix's own lines were rewritten or deleted on `main` so no merge can carry them forward. When a refusal names a generated path, say the file is generated but has no merge driver — never "hand-authored". Do **not** rebase or resolve by hand — that is authoring. Why: 14 of ~20 conflict events on the 43 gated PRDs of →09-08 were `` alone, a regen-driven file. |

Then establish **which pass this is**:

- **No prior `/fleet:verify` header from you** → a first pass. Run §2 onward.
- **A prior comment exists and the branch has new commits since** → a *re-entry* after a
  return. Re-run the **whole** ledger, not only the lines you failed: a second attempt
  that fixes line 2 while breaking line 1 is a shape this repo has produced, and a
  partial re-check cannot see it.
- **A prior comment exists and the branch is unchanged** → the implementer did nothing.
  Do not re-verify identical code and do not re-post; park BLOCKED once and exit.

**The return cap is two, and you count it yourself** from your own prior
`— INCOMPLETE` comments. On what would be a third return, stop returning: park the issue in
**`Blocked · decision`** with the open ledger lines and one line on why two attempts did not
close them. A fix that
has bounced twice is not converging, and a verifier/implementer ping-pong burns fleet
slots that a human glance would clear in a minute.

**A conflict hand-back does not count here** (). Only your own `— INCOMPLETE`
returns — the ones whose cause is an OPEN criterion — spend this cap. A brief stamped
`<!-- linear-agent:conflict-rework -->` is a `main`-moved-under-the-PR return, not a failing
criterion, and counting it against this cap parks a fix whose criteria all pass (:
`Blocked · decision` twice with **13/13** criteria green). Conflict hand-backs are counted on
their own, and at that count still dispatch a merge-scoped **mechanical rebase** ( —
not a full re-implement seat) rather than parking — see the `DIRTY` / `CONFLICTING` row above.

**Re-entry after a mechanical rebase.** When you are re-dispatched and the only change since
your prior closed ledger is a conflict-rebase head move, compare the new head's diff against
the prior certified head. If every touched path is derived (regen driver / generator output)
or otherwise outside the claims you closed, carry those closed rows forward on a smoke check
(CI green + mergeable) and do not re-derive the whole ledger. If any claimed file moved, re-run
the full ledger as a normal re-entry.

### 2. Reconstruct the ledger from the ISSUE

**Build the ledger yourself, from the issue, before you read the PR body.** This is the
single most important step in the command and the order is load-bearing.

The implementer already wrote a closed cause ledger into the PR body
([``](#) Phase 4.5). **Reading it first anchors you to their reading
of the issue — and their reading is the thing under test.** A claim the issue made that
never appears in their ledger is invisible to you the moment you have seen theirs, and
that omission is the highest-yield finding this command produces.

So: copy from the issue, **verbatim and quoted**, every clause that asserts something is
wrong — each **named root cause** (issues routinely name two or three), each
**acceptance criterion**, and each **site** a scoped claim covers (*"wherever the
codebase or docs assert it"*, *"all 50 references across 32 files"*). One numbered line
each, quoted, no paraphrase. Paraphrasing defeats the gate: *"identity resolution was
wrong"* covers two distinct causes loosely enough that fixing either one reads as done.

**Then, and only then, read the PR body's ledger and diff the two.**

```
LEDGER DIFF — <KEY>
issue claims:  3
PR ledger:     2          ← line 3 never appeared: "wherever the codebase or docs assert it"
```

A non-zero diff is not automatically a FAIL — the implementer may have REFUTED a claim,
which is a legitimate disposition. But an *unmentioned* claim has no disposition at all,
and that is an open line by default.

### 3. Check out the PR head

```bash
git fetch origin && git checkout <headRefName> && git rev-parse HEAD
```

**Never verify against `main`.** The change is not there yet — that is the whole point of
a pre-merge gate — so every check you run against `main` is a check of the old code, and
it will pass or fail for reasons that have nothing to do with this fix.

**If the head branch is gone — it merged while you were running — fall back to the merge
commit, never a missing-branch failure ().** Run `python3
`python3 knowledge/scripts/pr_resolve_review_target.py resolve <KEY> --pr <N> [--repo <owner/name>]`; a `merged` target carries
its `merge_commit` SHA. `git fetch origin && git checkout <merge_commit> && git rev-parse
HEAD` and review **that** — the exact content that landed. Record the merge commit as the
head SHA you cite, and treat the session as a non-failing terminal (§5/§6).

Record the head SHA. Every verdict you write cites it; a verdict with no SHA cannot be
re-checked later, and the branch will move.

If the change touches seed data and you are about to observe anything against a live
workspace, re-seed the way `make reseed` says first (it is **not** the same
as `make seed` where the repo distinguishes them) — an already-provisioned
workspace never picks those up from a rebuild alone, and skipping it reproduces the pre-fix symptom and returns a correct fix as
broken ().

### 3b. CI still running on this head — end `verify-awaits-checks`, do not hold the seat

Measured : two Urgent verify runs each held a seat for 45–55 minutes doing nothing but
`gh run watch` on a CI re-run. A seat is for judging, not for waiting. **When — and only when —
the one thing between you and the verdict is the required checks finishing on the head you are
judging**, in a fleet-dispatched run (your dispatch's outcome map teaches `verify-awaits-checks`;
outside the fleet, an interactive session keeps watching), do not poll:

1. **Judge everything that needs no green CI first** — §2's ledger, and V1 (claim closure) and V3
   (the denominator) against the diff. The wait is for the *last* thing you cannot do yet, not a
   reason to skip the rest.
2. **Post the partial ledger** as a `comment` that carries the hidden marker
   `<!-- fleet:verify-partial-ledger -->`, the head SHA, and one line per claim in the ledger's own
   words: `closed` (with the evidence), `open` (with what is missing), or `needs-green-ci`. This
   comment is what the resumed run starts from; a ledger that exists only in your head is lost.
3. **Confirm the head will be judged on the right commit**: the PR's head equals the branch ref
   (`gh api repos/{owner}/{repo}/pulls/<pr> --jq .head.sha` against `git ls-remote origin <branch>`),
   the PR is not `CONFLICTING` / `DIRTY` (a conflicted PR gets no CI — take the §1 conflict row, not
   this), and the checks are dispatched on that head.
4. **Write the done-sentinel** with `status: "verify-awaits-checks"`, `pr` the PR URL and
   **`verifiedSha` the 40-hex head you judged**, a one-sentence `summary` of where the ledger
   stands, and stop. Do not `record_verdict`, do not merge, do not move the issue: the
   service holds it in `Verifying` with your seat free.

**What the service does** (the same checks watcher a coding run uses): required checks all green on
that same head → the issue returns to `Verify Queue` **ahead of every fresh verify, urgent ones
included** (started work goes first) with a comment naming your partial ledger, and a *new verify
run* finishes the verdict; a red check, a conflict, or a head that is no longer your `verifiedSha`
→ `Rework Queue` with the reason; the PR closed → `Blocked · action`.

**The resumed run** reads the newest partial-ledger comment, re-proves only the lines still open
(and any closed line the diff since its head touches — the head can only have moved if the service
let it resume, so normally none), then runs §4 onward as usual. **The verdict is still a verify
run's, and the verifier still never merges past itself** — ending `verify-awaits-checks` certifies
nothing, and never ends a run whose only reason is that the checks are *red*: red is the §1 CI-red row.

### 4. The five checks

Run V1–V3 on **every** change. V4 and V5 are conditional — see each.

#### 4a. V1 — claim closure

One sub-agent per ledger line, dispatched in parallel, each given **one claim and
nothing else**. Give it the quoted claim, the head SHA, and the diff; ask it to return
the artifact that closes the claim, or the reason none exists. Do not give it the
implementer's disposition — you are testing that disposition, and a sub-agent handed the
answer will find it.

Each line comes back as exactly one of:

| | |
|---|---|
| **CLOSED** | names the `file:line` that satisfies it **and** the test that would fail without it |
| **OPEN** | nothing in this diff satisfies it — quote what is missing |
| **DEFERRED** | the implementer deferred it *and filed the follow-up* — **verify the issue key exists and is open**. A deferral whose issue does not exist is an OPEN line, not a deferred one; that is an unfixed cause under a closed ticket. |
| **REFUTED** | the implementer showed the claim itself is wrong **and recorded the refutation as an `implementation-notes` comment** (read via `comments` / `latest_comment` kind=`implementation-notes`, or the PR body's ledger line). The description may still quote the original claim — that is the ledger source, not the correction; no tool rewrites a description ( / G4). If no `implementation-notes` row (and no PR-body ledger line) names the claim and what is true instead, the line is OPEN — the next reader will be sent after a defect that does not exist. |

**A line naming a grant, role, binding, or credential is CLOSED only by the exercise —
never by the configuration that shows the grant exists.** A claim of the shape *"grant X
is bound to principal Y"* is checkable without being meaningful: it passes when the role
is insufficient for the call the grant exists for, when the principal named is not the
one that actually executes at runtime (impersonation makes the runtime caller a
different identity from the one the config names), and when a condition on the grant
never matches. Three failure modes, one green check. So a CLOSED disposition on such a
line cites the **executed call** — performing the call the grant exists for, as the
principal that actually executes at runtime, with the response recorded (the 200 read,
the successful operation) — and never the IAM binding, the role attachment, or the
secret in state. Configuration inspection proves the grant was applied; only the
exercise proves the capability works. The same holds for any capability claim whose
only evidence is provider or IaC state. (, from : `roles/logging.viewer`
carries `logging.views.get`/`logging.views.list` — *that* a log view exists — but not
`logging.views.access`, which reads entries out of one; the binding was verified present
and `entries.list` still 403'd on every tick for ~100 minutes, and a second round of
grants verified present on the runtime's service account changed nothing because the
runtime impersonates a *different* account than the one the grant named.)

#### 4b. V2 — test integrity (the neuter check)

**For every test a CLOSED line names: revert the fix, run that test, and assert it goes
red.** This is the cheapest high-yield check in the command and it is not optional. It is
**one script, `knowledge/scripts/neuter_check.py`, which the implementer ran at its first
handoff too** — the check has a single copy, so the two sessions cannot drift:

```bash
python3 knowledge/scripts/neuter_check.py --base origin/main --ledger /
```

The ledger (`--ledger <file>`, or stdin) names each claim: a `tests` entry carries the test
`run` list and the `revert` pathspec of the files the fix landed in (never the test file);
a `scopes` entry carries the `pattern` and `paths` for V3 below. The script runs each test
green→red→green (the mutation applied and the tree asserted restored byte-for-byte), counts
every scoped site against the diff, and exits non-zero on any test that stayed green, any
test not green at HEAD, or any uncovered site. Build the ledger from the CLOSED ledger
lines; a line with no test and no scope is not a line this can close.

A test that still passes with the fix reverted does not close its line — **you have a
description of a test, not a test.**  shipped exactly this: the test *assigned*
the value it was meant to verify, so planting the exact defect left it green. The guard
was provably inert and nothing caught it, because the only party who could have run this
check was the party who wrote both the test and the fix. The script asserts the restore
even when the run errors out; §7 asserts the tree came back.

A CLOSED line that names **no** test is an open line: "fixed, unproven" is not a
disposition, and it is the shape a regression comes back through in a month.

#### 4c. V3 — the denominator

**A scoped claim is not closed until somebody counted.** *"Wherever asserted"*, *"all N
references"*, *"every call site"* — the `scopes` half of the same `neuter_check.py` ledger
greps the pattern at the head SHA, states the denominator, marks which sites the diff
changed, and exits non-zero on any site left uncovered (name an intentionally-untouched one
in `allow`; assert the count with `expect`):

```bash
python3 knowledge/scripts/neuter_check.py --base origin/main --only scopes --ledger /
```

```
"wherever the codebase or docs assert it"  →  4 site(s), 3 covered  →  OPEN (uncovered: :88)
```

`landed in 2 of 3 sites` is the single most common shape of an incomplete fix in this
repo, and it is always a claim nobody counted. Counting it takes one `grep` and it is the
check that catches the failure mode the measurements at the top of this file describe.

#### 4d. V4 — the surface

**Only when the change touches something a customer can see** — any file under the
surface paths `slot:ui-contracts` names, or a response shape a page reads. Otherwise skip it and say so; do not spin
up a stack to prove a pure-backend refactor.

When it applies: one sub-agent drives the actual surface in a browser, from the
customer's seat, and confirms **the symptom the issue described is gone** — not that the
page renders. Reading the code is a supporting aid to explain a mechanism; it is never
how the symptom is established. A unit suite mocks the rendering substrate, so it can be
fully green while the page crashes on load.

Assert the binary is fresh before you trust anything you see: the API process started
after your checkout's last change **and** the readiness route `slot:dev-environment`
names answers. A hot-reloader can orphan the port so a **stale binary keeps serving**
(), and a verdict written against the old binary is wrong in both directions.

**And the page is part of the surface.** When the change touches a path a page lists in its
`source_of_truth:` (or the page's own home `slot:docs` names), the same driver **follows that
page's steps literally, in the real UI** — a reader who has never done the task types what the
page says and clicks what it names. A step the product no longer matches is a **FAIL**, not a
docs nicety: the page is a claim about the product, and a page that lies is a defect. Route it
(``/fleet:bug:fix`` for a wrong step, `/fleet:task:create` for a missing one) before the
verdict, or turn the PR back. When the repository leaves `slot:docs` unfilled there is no home
to follow — say so and skip this paragraph; that is the slot's degrade, not a skipped check.

#### 4e. V5 — regression

Targeted, not the whole suite — CI already ran that and it is green, which is a
precondition of your even being here. Run the package the fix landed in, plus the nearest
consumer the trace in the issue names. If the fix crossed a boundary (handler → projection
→ raw store; connector → connectord → API), run the consumer on the far side of it.

**A burst of unrelated failures sharing one DB-connection error is a shared-runner infra
flake, not a regression** — do not chase it (eng-460, eng-659).

### 5. The verdict

| Verdict | When | What happens |
|---|---|---|
| **VERIFIED** | every ledger line CLOSED / DEFERRED-with-a-live-issue / REFUTED-with-implementation-notes, every named test neutered red, every scoped claim counted, the surface driven if there was one | merge (§6) |
| **MERGED** | the PR merged while you were running (`python3 knowledge/scripts/pr_resolve_review_target.py resolve` → `merged`) — the fix is already on `main` | a NON-FAILING terminal: report it as landed (§6), never as a missing-branch failure, never escalate |
| **INCOMPLETE** | any line OPEN | return it (§6) — never merge |
| **BLOCKED** | you cannot evaluate it: no PR, red CI, a coupled half whose other half is unmerged (`bound`) — drive the fleet half first and re-pin, do not merge this half, a conflict the merge-scoped implementer reports unresolvable or needing a judgement, an unchanged re-entry, a third return, or a claim that needs a product decision to judge | park for the human (§6) |

**There is no PARTIAL and no "merge with a follow-up".** A follow-up issue for an
un-closed claim is precisely how the ~1-in-2 rate was produced: the ticket closes, the
follow-up is filed, and it competes with everything else on a board that will not
prioritise it. The one legitimate deferral is the implementer's own DEFERRED line with a
filed issue — because that decision was made *with* the root cause in hand, before the
fix was declared done, and it is visible in the ledger the PR carries.

**The merged-while-running terminal is NOT a spurious failure ().** When
`python3 knowledge/scripts/pr_resolve_review_target.py resolve` reports `merged`, the work under review has already landed
on `main` and the tracker issue closes on merge — that is the outcome a verify session
exists to produce, reached by another lane. Report it as landed (§6), file nothing, and
stop. Do **not** report a missing-branch error, do **not** park the issue, and do **not**
escalate.

### 6. Write the verdict

**Every comment below starts by naming this command and its verdict** — Rule I in
[`autonomous-drive.md`](../../process/autonomous-drive.md). Copy the template;
do not paraphrase it. Four comments were observed carrying four different headers, two of
them using a different emoji for the same `INCOMPLETE` verdict.

**VERIFIED — write the verdict FIRST, then merge.** The order below is load-bearing.
**Five steps, in exactly this order:**

1. **`record_verdict(repo, pr_number, head_sha, verdict: verified, ledger, dispatch_token)`.**
   The authority is Fleet's row. Pass `$FLEET_VERIFY_DISPATCH_TOKEN` (the mission names
   the variable). A reconcile push after this verdict needs no new verdict — the gate
   matches by the pull request's own diff.
2. **`comment` kind `verdict`**, the readable note — never a hand-typed `dispatch token`
   line. Put the token in `data.dispatchToken` only:

   ```
   ✅ `/fleet:verify <KEY>` — VERIFIED

   **Ledger:** {n}/{n} closed
   **Head:** `{head sha}`
   **Re-derived:** {one line — what you checked independently of the implementer's claim}
   ```

   with `data: { dispatchToken: <from the environment> }` on the tool call.
3. **Confirm the PR is READY — never merge a draft — then prepare the body. Do NOT
    re-arm yet.** The implementer hands off READY ( retired the  draft
    hold: the required fix-gate check (`slot:git-workflow` names it) is the verify verdict's merge-blocking
    representation, and the daemon's verify-stop comment is the non-pass hold — no repo
    command ever converts a PR to draft as a verify hold). So check what you are holding
    first: `gh pr view <pr> --json isDraft,labels`. A `do-not-merge` label is a stop,
    full stop. A draft here is unexpected — read the timeline
    (`gh api repos/{owner}/{repo}/issues/<number>/timeline`, most recent `convert_to_draft`
    actor) before touching it: a **third-party draft is a deliberate human pause** →
    `BLOCKED`, stop; a legacy draft from the retired  hold (no third-party actor)
    you lift with `gh pr ready <pr>` and confirm `gh pr view <pr> --json isDraft` reads
    `false`. **Then ensure the closing keyword is on the body — before anything that can
    fire a merge ()**: `python3 knowledge/scripts/gh_closing_keyword_ensure.py`
    <pr> <KEY>`, adding every `Fixed incidentally: <KEY2>` key the ledger recorded as an
    extra argument. For a `Type:bug`/`task`/`cleanup` issue this keyword is the ONLY
    merge-close mechanism — the `prd-projection` pass of the fleet's `corpus-sync` loop settles
    PRD issues only — and it used to be composed inside step 4's `push ship` (its step
    5.5), *after* the arm. That order raced: the moment the gate re-read green with
    `CI Success` already green, GitHub squash-merged before the body edit landed — PR
    #10014 merged with `Refs ` and no closing keyword, and the issue stranded in
    `Verifying` (a claimed state that dispatches nothing) until a session closed it by
    hand. The script appends `Closes <KEY>` when the body carries none (`Refs` is a link,
    never a close — ), re-reads to confirm, and no-ops when the keyword is already
    there; step 4's `push ship` 5.5 then confirms it as a no-op.
    **Compose before the arm — the arm is the point from which a merge can fire at any
    second** (`make validate-knowledge` pins this order mechanically).
    **Do not re-arm in this step.** The open-time arm () and any residual arm are
    still live; step 3 disarms them before the fix-gate re-run, and step 4 re-arms only
    after the gate is green ().
 3. **Disarm, then re-trigger the fix-gate check, then wait for green ().**
    **Which gate this is comes from `$FLEET_VERIFY_GATE`, named by the lease (PRD 0745).**
    `check:<name>` — the control plane posts the verdict itself as a GitHub check through the
    install's App, so there is **no workflow to re-run**: skip the re-dispatch below and go
    straight to step 4, which arms while that check is pending. `workflow:<file>` — today's path:
    re-run the named file and wait. Unset — the lane carries no gate, and there is nothing to
    re-run. **Never call a workflow re-run on a `check:` gate**; a customer's repository has no
    such workflow, which is the whole point of the posted check.
    Re-running a required check under a live `--auto` is the  class (check-state
    change while armed). PR #10055 proved the prior "arm then wait for the re-read" order
    is not safe even under the `enforce_admins: true` then in force ( has since set it back to `false` on , so nothing at GitHub enforces the required checks for the admin login the fleet merges through): the session re-armed at 07:33:57Z, the
    re-run was still `in_progress`, and GitHub squash-merged at 07:34:07Z — 18s *before*
    the gate went green. Disarm first, re-run second, confirm green third; never arm
    across the re-run window.

    ```bash
    python3 knowledge/scripts/gh_automerge_disarm.py <pr>
    python3 knowledge/scripts/gh_recheck_gate.py <pr>      # workflow gate only; no-op for check:/unset
    ```
    **Read mergeability before you wait on any check, and a check that never reports is a
    conflict until proven otherwise.** GitHub runs no workflow on a conflicted PR, so a gate
    on one never re-reads. `main` moves while you wait, and it moved under #12606 ()
    after its VERIFIED verdict, which left the session waiting on a gate that could not
    report. The script reads `mergeable,mergeStateStatus` before the re-dispatch and on every
    poll. **Exit 3 is CONFLICTING / DIRTY: stop waiting and take the `DIRTY` / `CONFLICTING`
    row of the §1 preconditions table.** Run `regen_reconcile.py`. On its exit 0, disarm, push
    fast-forward, and re-run this step at the new head. Any other exit is the conflict-as-work
    hand-back to `Rework Queue`. Never re-trigger the gate some other way (a body edit, a
    label, a token of your own); none of them make a conflicted PR run a workflow.
    Confirm the fix gate among `slot:git-workflow` reads `pass` on this
    head (`python3 knowledge/scripts/pr_missing_required_contexts.py` lists what has not reported).
    Its authority is **Fleet's verdict row** () — the rerun only causes a re-read,
    so re-running it before steps 1–2 changes nothing; re-running it *under an armed
    `--auto`* is what  forbids.
5. **Re-arm, then merge.** Only now — the fix gate green on this head — re-arm auto-merge
     through the mechanical gate ( / ), **not** a bare
     `gh pr merge <pr> --auto --squash`:

     **On a `check:` gate (PRD 0745) this is the one place the order differs, and it is
     deliberate.** The gate's own check is still *pending*: the control plane completes it after
     it reads this session's verdict. `gh_automerge_arm.py --require-green` excludes exactly that
     context, so the arm succeeds on the customer's own green checks while the posted check
     waits, the pull request merges only after the control plane turns it green, and the
     done-sentinel ends `merge-pending` with **`verifiedSha` set to the commit you verified**.
     Never re-run a workflow here. When `$FLEET_VERIFY_GATE_REQUIRED` is `false` (the lease read
     the gate as not required), take the ungated path the lane without a required gate takes
     today: merge on your own verdict, and the control plane posts the check afterwards.

     ```bash
     python3 knowledge/scripts/gh_automerge_arm.py <pr> --require-green
     python3 knowledge/scripts/gh_pr_merge_state.py <pr>   # must read armed / queued / merged
     ```

     The arm reads back as `autoMergeRequest` non-null **or** as a merge-queue entry — on a
     branch with a merge queue a green PR is **enqueued** and reads `autoMergeRequest: null`,
     so `gh pr view <pr> --json autoMergeRequest` alone calls a queued PR unarmed.
     The script wraps `gh pr merge <pr> --auto --squash` (never `--delete-branch`, which `gh`
     refuses outright under a merge queue; `delete_branch_on_merge` deletes the branch) and **refuses**
     unless every branch-protection required context is already green on the head — the
     mechanical half of the procedure pin above. PR #10064 () armed over a
     still-red the fix gate 4.5 min after 's text-only fix landed (the session
     had started on a pre-fix checkout); GitHub squash-merged 8s later, 25s before the
     re-run went green. A bare `--auto` is what that session ran; this script is what it
     cannot skip. Open-time arm () deliberately omits `--require-green` because
     a red the fix gate is expected until this step. With every required check already
     green the arm merges immediately (or within GitHub's async worker) — or enqueues it,
     under a merge queue; that is the designed path, not a race. **A queued PR is pending,
     not merged and not failed**, and its branch is locked: any later push needs
     `gh_automerge_disarm.py` first, which dequeues it. A PR the queue **removes** (its
     `merge_group` run went red) reads OPEN / CLEAN / unarmed with its own checks green —
     `gh_pr_merge_state.py` names it `ejected` with the red `merge_group` checks; treat it as
     red CI, never as verified-and-merged. **On the fleet, a queued merge is not yours to wait
     out:** once the verdict is posted and the PR reads `queued` — or `armed` with every required
     check green — end the run with the done-sentinel status `merge-pending` and the PR URL. A
     queue build is 30–60 minutes of somebody else's CI; the fleet's merge watcher holds the issue
     in `Verifying`, moves it to `Done` when the PR merges, routes an ejection or a conflict back
     to `Rework Queue` with the red checks or the conflict brief, and asks a person if it stalls.
     Never end `merge-pending` before the verdict, or over a red, conflicted or ejected PR. Outside
     the fleet (an interactive session), keep watching as below. Then delegate to [`/fleet:push ship`](push.md) with
     the head SHA and the `<KEY>` — it reuses the open PR, re-arms idempotently, and
     watches to `MERGED`. Trust **only** its returned confirmed `origin/main` SHA as
     evidence the merge landed — `NOT MERGED — <reason>` is a withhold, and you report it
     as one. Then post the one-line follow-up naming the merged SHA as `comment` kind `verdict`
     (the gate already holds the row from step 1; a reconcile push needs no new verdict):

   ```
   ✅ `/fleet:verify <KEY>` — verified & merged

   **Merged:** `{confirmed origin/main sha}` · **PR:** {url}
   ```

**Decide the verdict before the terminal transition — the two are mutually exclusive
().** The verdict — including anything a post-merge check could object to (a missing
closing keyword, a title that does not claim to complete the issue, an unexpected merged SHA)
— is settled **before** the merge moves the issue to `Done`. If such an objection is real, it
is a pre-merge finding: the verdict is not VERIFIED — return it (INCOMPLETE) or park it
(BLOCKED) while the issue still sits in a state that dispatches, never merge past it. After
the terminal transition the verdict stands: a residual observation posts as a **plain note**
— no 🙋 marker, no park, no `needs-decision`/`needs-action` sentinel — and anything that
needs work is filed as its own issue (Rule G). A park addressed to a terminal issue can
never be actioned: nothing dispatches on `Done`, so the question reaches no loop and no
queue, and the run contradicts its own passing verdict on the record. The done-sentinel
likewise keeps the verdict's own status after a pass — never a park status.

**Why the order changed ().** This command used to merge first and write the
verdict and the label strip afterwards. Measured over the 58 most recently merged PRs
carrying an `ENG-` key: `awaiting-verification` was stripped **after** the merge on 35 of
36, median ~150s later (range +12s to +917s), and the verdict comment lagged the same way.
So for the whole window in which a merge is decided, a verified fix and an unverified one
looked **identical** to every observer — which is why six PRs sat armed for auto-merge with
no passing verdict, two of them after being explicitly refuted, and #8977 came one push
from merging unverified. A signal written after the merge cannot gate the merge. This
ordering is also strictly safer on its own: under the old order a session that died after
merging left `awaiting-verification` set forever, which is what 22 of those 58 rows are.

A withheld merge is not a VERIFIED with a caveat — it is `BLOCKED`, with `push ship`'s
`NOT MERGED — <reason>` quoted verbatim. If `push ship` withholds after steps 1–2, the
verdict comment already posted stands (it was true of the head you reviewed); say plainly
in the `BLOCKED` comment that the merge, not the verification, is what failed.

**The non-pass hold is the daemon's verify-stop comment — never a draft.** On an
INCOMPLETE or BLOCKED outcome the daemon applies the `🚦 Verification did not pass — PR
stopped` comment (under the daemon's own hidden marker — see the dispatch envelope) and
its PR stop label; the PR stays READY — the required fix gate is what keeps it unmergeable
by every lane while its ledger is open, and the stop marker is what tells the next reader
who owns the pause (a third-party draft would be a *human* pause — the fleet never drafts
its own PRs;  retired the  draft hold). The hold lifts automatically at
the next verify dispatch: the re-dispatched implementer re-pushes onto the still-open PR,
and the next passing verify posts the verdict and merges.

**MERGED — it landed while you were running. Report it as landed, then stop ().**
Do not merge anything and do not park: the work is already on `main` and the issue closes
on merge. **Comment only — nothing is recorded via `record_verdict`**: there is no open
PR head to bind a verdict to (P8). Post:

```
✅ `/fleet:verify <KEY>` — MERGED (landed while verifying)

**Head:** `{merge commit sha}` · **PR:** {url}
**Re-derived:** {one line — what you checked independently}
```

An override of a recorded verdict is `record_verdict` from an allowlisted person's key —
never a tokenless comment from a Linear account.

**A session that merged the PR itself must short-circuit before any escalation path can
fire ().** If *this* session performed the merge (e.g. you stamped the PRD
`shipped` and merged it), stop right there — post the VERIFIED/MERGED result and exit. Do
**not** later move the issue to `Blocked · decision` / `Blocked · action` or make any
other escalation on the same
issue: the work you just completed succeeded, and escalating against your own completed
merge is exactly the false park this fix removes. Escalation is for what is *still open*,
never for work you just finished.

**INCOMPLETE — return it.** Three writes, in this order:

1. Post one comment: the **open lines only**, each quoted, each with what is missing and
   the `file:line` or grep result that shows it. Not a re-derivation of the whole issue —
   the implementer wrote the fix; they need the delta, not a lecture.

   ```
   ❌ `/fleet:verify <KEY>` — INCOMPLETE

   **Open ({n} of {n}):**
   - > {quoted ledger line}
     missing: {what is absent} — `{file:line}` / `{grep result}`
   **Head reviewed:** `{sha}` · **PR:** {url}
   ```
2. **`move_issue` to `rework`.** The daemon routes a rework-position issue back to its implementer with
   your comment as the brief.
3. Write the done-sentinel with `status: "verify-failed"` and the open-line list as the
   summary. **Without the sentinel the daemon re-dispatches *you* against the same
   unchanged code forever** — there is no human in this loop to notice.

**BLOCKED — park it.** End the run with **`needs-decision`** when a human must answer
something (a claim that cannot be judged without a product call, a third return);
**`needs-action`** when a human must *do* something (merge a guarded PR, clear a
credential) — with the decision document. `move_issue` refuses `blocked-decision` by
design; the ending is the park.

```
🙋 `/fleet:verify <KEY>` — BLOCKED (needs-decision | needs-action)

**What I need from you:** {the question to answer, or the action to take — runnable}
**Why I can't settle it:** {one line}
**PR:** {url, or "none"}
```

**A needs-decision park asks in writing, so it is bound to the card.** The 🙋 comment
above keeps its three lines; what the person clearing the park actually reads is the
`decision` document, and it is written to the card below.

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

<!-- include: process/decision-document.md -->
### Parking on a person — the `decision` document (headless)

**Every `needs-decision` park writes one `decision` document, and it is the interview card
in fields.** The person clearing `Blocked · decision` reads this card and nothing else —
not the issue, not the PRD, not the register, not your comment thread. The sentinel's
`summary` is only a one-line headline for the park list; everything a person needs to decide
goes here. Write it to `$FLEET_RESULT_FILE` (skip only if that is unset) before the
done-sentinel:

```json
{
  "kind": "decision",
  "brief": {
    "work":    "What somebody will be able to do that they cannot today, in plain words.",
    "example": "One named person doing it, and what they see.",
    "stopped": "What stopped this run, in plain words — the fork, not the log.",
    "stakes":  "What is at stake either way."
  },
  "context": [
    {"ref": "AC-4", "name": "automated comments never reach the customer",
     "quote": "<the criterion's own text, verbatim>", "url": "<optional https link>"}
  ],
  "question": {
    "id": "<short id>",
    "prompt": "The decision, as one question in plain words.",
    "options": [
      {"id": "<short id>", "label": "<what the person picks, no ids>",
       "why": "<why this is right>", "cost": "<what it costs>",
       "then": "<what happens next if picked>", "recommended": true},
      {"id": "…", "label": "…", "why": "…", "cost": "…", "then": "…", "recommended": false}
    ]
  }
}
```

- **Two to four options, the recommended one first** and the only one marked `true`;
  `why`, `cost` and `then` on **every** option.
- **Quote what you cite.** Every acceptance criterion, requirement, issue or PRD the question
  leans on gets a `context` entry whose `quote` is its own text — or, in prose, the plain name
  with the id in parentheses: *the automated-account rule ()*. A bare `AC-4`, ``,
  ``, `PRD 0676`, ``, `PR #123` or `/:…` is refused.
- **Labels carry no ids at all**, and nothing says where the issue was parked — the fleet
  says that, and the person reading is already there.

**Check it before the sentinel** and fix every reason it prints, in this turn:

```bash
python3 knowledge/scripts/validate_decision.py "$FLEET_RESULT_FILE"
```

`0` meets the card; `1` prints every rule broken; `2` means there is no `decision` document at
the path. A park with a missing or refused document still parks — the fleet does not strand a
person's decision over its shape — but the park is recorded as `askRefused` with your reasons,
and that is counted.
<!-- /include -->

**Post the park comment with `comment`.** On a refusal, **STOP**: do not retry, do not
move the issue, and record the contradiction in the closing report.

**The return is `move_issue` to `rework`; parks are the run's ending.** Read the position
back with `get_issue`.

### 7. Closing report

**First, the `no-fix` gate — run it before you write a line of the report:**

```bash
git status --porcelain && git stash list && git log origin/<headRefName>..HEAD --oneline
```

A restored tree, no stash, and **no commits of your own on the branch**. Anything else
means you authored a fix in a verification session: revert it (`git checkout -- . && git
clean -fd`), drop any commit you made, and say so plainly in the report's `Breach:` line.
Do not quietly leave the change because it looks correct — a fix nobody independently
checked is exactly what this gate exists to stop, and one that came from *here* has no
one left to check it at all.

Six lines, no more:

```
<KEY> — <VERIFIED | INCOMPLETE | BLOCKED>
Head:       <sha> · PR #<n>
Ledger:     <n>/<m> closed · <the open line, quoted, if any>
Neuter:     <n> test(s) went red on revert · <"none named" if that is the finding>
Surface:    <driven: the symptom is gone | n/a — no customer surface changed>
Breach:     <"none" | what you wrote and what you reverted>
Next:       <merged <sha> | returned to implementer | parked <label>>
```

**The `Neuter:` line is the one that compounds.** An inert test is invisible to CI, to
code review, and to the next verifier — this is the only place in the pipeline where one
is detectable, and reporting the count every time is what turns "we think our tests
work" into a number.

---

## What this is NOT

- **Not a code review.** Style, structure, naming, and better approaches are
  `/code-review`'s job. A fix that closes every claim in a way you dislike is VERIFIED.
- **Not a re-triage.** Whether the issue was worth doing was settled by
  [`check`](check.md). Re-litigating scope here is how a merged fix gets held hostage to
  a second opinion nobody asked for.
- **Not a second bug hunt.** Defects you notice outside this issue's claims are filed
  (`/fleet:bug:create`), never folded into this verdict and never fixed here
  ([`autonomous-drive.md`](../../process/autonomous-drive.md) Rule G).
- **Not a place to be helpful.** Closing the last open line yourself, rebasing the
  branch, or nudging a red CI green all feel like unblocking the fleet. Each one ends
  the independence that is the only thing this command contributes.
