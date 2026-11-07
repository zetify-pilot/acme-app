# Arch-Doc Reconciliation Sweep

Autonomous sweep of the **freshness-contract docs** whose **narrative has actually
drifted**. Detects every `DRIFT` warning produced by `python3 knowledge/scripts/validate_arch_docs.py`,
re-reads each drifted doc against its live `source_of_truth` paths, and — **only for
docs whose prose is now wrong or incomplete** — updates the prose and opens **one
batched PR**. Docs whose code changed only cosmetically (additive / internal /
test-only) are **left untouched**: no re-stamp, no whitespace edit, no near-empty PR.
Safe to run nightly precisely because it produces an artifact only when there is real
work.

**Subject set: whatever `python3 knowledge/scripts/validate_arch_docs.py --list-subjects` prints** —
never a filename pattern, and never a grep. Two kinds of doc are in it: the root specs
that **declare** `source_of_truth:`, and every **component detail doc** (the `slot:architecture`
fill's per-component documents) whose contract is **derived** from its registry row's
`owns:` paths — those declare nothing, so a grep for
`^source_of_truth:` would report them as absent. This command was originally written
against the numbered `NN-*.md` chain, retired on 2026-08-15; it kept working because Step 1
reads the validator's output rather than globbing filenames. See
[`knowledge/specs/architecture/README.md`](../../../../knowledge/specs/architecture/README.md).

Invocation: `/zetify:arch:reconcile`

Run on demand as a slash command, or on whatever schedule the repo gives it (none is
wired by the tier — a repository that wants a nightly sweep schedules one). It is the **single writer** to those docs —
feature PRs never edit them (the CI sync check is advisory only), so this sweep never
races a concurrent doc edit.

---

<!-- include: process/writing.md -->

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. `subject-set` may terminate the command (no subjects → refuse to run); `decide` may terminate it with **no artifact at all**, which is this sweep's designed outcome on a cosmetic-only change. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "arch-reconcile",
  "intent": "Sweep the freshness-contract docs whose narrative has actually drifted, reconcile only those, and open one batched PR with a cleanup issue filed into triage behind it — or nothing.",
  "sop": "none",
  "needs": "nothing",
  "may merge": false,
  "loads": ["architecture"],
  "requires": [
    "process-spine", "process-envelope", "gate", "git-workflow", "architecture",
    "registers-triage-partition", "tracker-identity"
  ],
  "optional": ["components", "file-conventions"],
  "steps": [
    {"id": "subject-set",  "name": "Establish the subject set, or refuse to run", "kind": "gate",     "actor": "coordinator", "gate": "hard", "body": "step-0-establish-the-subject-set"},
    {"id": "detect-drift", "name": "Detect drift from the validator's own output", "kind": "io",      "actor": "coordinator",                 "body": "step-1-detect-drift"},
    {"id": "read-doc",     "name": "Read the current doc",                         "kind": "io",      "actor": "coordinator",                 "body": "2a-read-the-current-doc"},
    {"id": "read-sources", "name": "Read what changed in the source paths",        "kind": "io",      "actor": "coordinator",                 "body": "2b-read-the-changed-source-paths"},
    {"id": "decide",       "name": "Decide: reconcile, or leave it alone",         "kind": "decision", "actor": "coordinator",                "body": "2c-decide-reconcile-or-leave-alone"},
    {"id": "apply",        "name": "Apply prose edits to the drifted docs",        "kind": "author",  "actor": "coordinator",                 "body": "step-3-apply-edits"},
    {"id": "commit-pr",    "name": "Commit and open one batched PR — armed at open", "kind": "io",   "actor": "coordinator",                 "body": "step-4-commit-pr"},
    {"id": "handoff",      "name": "File the cleanup issue into triage, and stop", "kind": "io",      "actor": "coordinator",                 "body": "step-5-hand-off-to-the-gate"}
  ]
}
```

---

## Rules (autonomous — same envelope as autonomous-drive.md)

- **Never stop to ask.** No proceed-gates, no AskUserQuestion. Pick the
  most defensible default, log it, and continue.
- **Log every judgment call** in the Autonomous Decisions Log. Surface it in
  the PR body.
- **Branch + PR** — never direct-to-`main`. Branch:
  `agent/chore-arch-reconcile-{YYYY-MM-DD}` (use today's date; derives from
  `git log --format=%ai -1 HEAD` or `date -u +%Y-%m-%d`).
- **No `status:` flips.** This is maintenance tooling, not a PRD lifecycle step —
  which is a statement about the PRD lifecycle and was never a statement about the
  merge gate. It used to be read as one: this sweep ran its own verify step and called
  the merge its own to pull, on the strength of being maintenance. The
  law it was reading itself out of — *the party that wrote the prose never certifies
  it* — has no exception written into it, for maintenance tooling or for anything
  else. **This command opens a PR and files the issue that carries it into the gate**
  (Step 4): the checker triages what this run had no business guessing, and
  [`/zetify:verify`](../verify.md) — a session that has never seen this one — is what
  eventually releases the merge.
- **🛑 Arming is not certifying — this command ARMS auto-merge at open, and merges
  nothing.** The correction above was once written as a flat prohibition on arming, and
  that phrasing is a defect in its own right (ENG-8780): a mergeable-but-unarmed PR
  carries no red check, no conflict and no queue entry, so it is indistinguishable
  from a healthy one and sits open until a human sweep happens to look — six
  consecutive sweeps each found one. Arming decides **nothing** about whether this
  sweep's prose is true. What decides that is the required fix-gate check
  (`slot:git-workflow` names it), which fails closed on the `Type:cleanup` issue this
  run files until `/zetify:verify` posts its pass: the armed PR reads `BLOCKED`, and
  GitHub does not merge a PR whose required context is failing. So the arm costs this
  sweep no authority it does not have, and its absence was pure merge latency with no
  signal.
- **The arm is safe here *because the cleanup issue key rides this PR* — that link is
  load-bearing, not decoration.** The fix gate resolves its subject from the PR's head
  ref, title and body; a PR that names no issue is read as non-lane work and **passes**
  that gate, which would make an armed PR merge on green with nobody having graded it.
  This sweep's branch carries no key (it is the repo-meta chore form), so the key must
  be in the **title and body** — and it must be there *before* the arm. That is why
  Step 4 files the `Type:cleanup` issue first, composes the PR with its key, and only
  then arms.
- **No artifact without substantive drift** — if no doc has *substantive* drift
  (only cosmetic / additive / test-only changes, or no drift at all), print
  "architecture docs OK — no substantive drift" and exit cleanly with **no branch,
  no PR, no commit, no re-stamp**. A lingering advisory `DRIFT` line for a
  cosmetically-changed doc is expected and fine — never edit a doc just to silence it.
- **An empty subject set is a FAILURE, never health — where the contract is adopted.**
  "No docs drifted" and "no docs are watched" produce identical validator output, so this
  sweep must tell them apart itself (Step 0). If the repo's `slot:architecture` fill
  declares the freshness contract at all and **zero** docs carry one, print
  `arch-reconcile FAILED — the freshness contract has no subjects` and exit **non-zero**.
  Never print the OK line in that case: it is exactly how a silently-shrinking subject set
  masquerades as a clean nightly for months. **A repo whose architecture fill has never
  adopted the contract** (no `source_of_truth:` anywhere, no component registry) is a
  different case: print `arch-reconcile NOT APPLICABLE — this repo declares no freshness
  contract` and exit **zero**. A sweep that fails every night for a contract nobody
  opted into is noise, not a guard.
- **Bounded reconciliation** — cap at 20 drifted docs per run. If more than 20
  drift, reconcile the oldest-by-last-commit first; log the remainder.

---

## Step 0 — Establish the subject set (and refuse to run without one)

Before looking for drift, confirm there is something to watch:

```bash
python3 knowledge/scripts/validate_arch_docs.py --list-subjects
```

One repo-relative doc path per line — the opted-in specs **and** the component detail docs
whose contract is derived from the registry. Do **not** substitute a grep for
`^source_of_truth:`: it cannot see the derived half, so it would under-report the reach by
roughly 5:1 and read as a shrinking subject set.

- **Zero results** → the freshness contract covers nothing. Where the contract is adopted,
  print `arch-reconcile FAILED — the freshness contract has no subjects` and exit
  **non-zero**; where it never was, `NOT APPLICABLE` and exit zero (see the rule above).
  Do not print the OK line, do not open a PR. This is the guard against a shrinking
  subject set reading as a clean run.
- **One or more** → that is the subject set. Note the count; it belongs in the run's
  output so a reader can see the sweep's reach, not just its verdict.

---

## Step 1 — Detect drift

```bash
python3 knowledge/scripts/validate_arch_docs.py
```

Parse stdout for `DRIFT:` lines. Each line has the form:

```
- <doc-path>: DRIFT: `<source-path>` changed in N commit(s) since this doc's last edit — …
```

The doc path is the prefix on each line — a repo-relative path under
`knowledge/specs/`, **not** a filename pattern. Collect:

```
drifted_docs = {
  "<doc path, exactly as the DRIFT line printed it>": [
    ("source/path/", N_commits),
    ...
  ]
}
```

If the dict is empty **and Step 0 found a non-empty subject set** → exit cleanly (see
"no drift" rule above). If Step 0 found nothing, you already failed there.

---

## Step 2 — Understand the drift (per drifted doc)

For each drifted doc, work through these steps in order:

### 2a — Read the current doc

Read the full content of the drifted doc file.

### 2b — Read the changed source paths

For each drifted `source_of_truth` path, collect the relevant changed files
and their recent git history:

```bash
# What changed in this source path since the doc's last commit? The doc path is the one the
# DRIFT line printed — never reconstruct it from a directory you assume.
DOC_SHA=$(git log -1 --format=%H -- "<doc path from the DRIFT line>")
git log --oneline "$DOC_SHA"..HEAD -- "source/path/"
```

Read a sample of the changed files to understand what actually moved:
- For a directory path: scan the changed files within it
- For a specific file: read it directly

Focus on **structural changes** (new types, removed fields, new subsystems,
changed semantics) — not style churn. A one-line variable rename is not worth
a doc update; a new package or removed interface is.

### 2c — Decide: reconcile or leave alone?

Two cases:

| Drift type | Action |
|---|---|
| **Substantive drift** — the code changed in a way that makes the doc's prose incorrect or incomplete (new / removed / renamed subsystem, changed flow, changed invariant, new / removed tool, stale count) | Edit the prose to reflect reality. The edit advances the git baseline. |
| **Cosmetic drift** — the change is additive, internal, test-only, or otherwise leaves what the doc says correct | **Leave the doc completely untouched.** Do **not** re-stamp, add a Status-line note, or make a whitespace edit to "advance the baseline." Log the skip in the Autonomous Decisions Log. The advisory `DRIFT` line persists until a substantive change lands — that is intended; advisory drift is harmless. |

**Default to "cosmetic" when unsure** — a doc edit must be justified by a real
prose correction, never by the mere existence of a `DRIFT` warning. This is what
keeps a nightly cadence silent on days with no real work.

**Never fabricate details.** If the source files are too large or numerous to
read in full, summarize based on what was read and note the limitation in the
Autonomous Decisions Log.

---

## Step 3 — Apply edits

Edit the doc in-place. Focus updates:

- **What the runtime is** sections — fix stale counts, removed features, renamed packages.
- **Key data flows / architecture diagrams (prose)** — reflect structural changes.
- **Status line** — update if the subsystem's stability changed.
- **Cross-references** — fix any `internal/old-path` → `internal/new-path` refs.

Do **not**:
- Rewrite paragraphs that are still accurate.
- Add speculation or forward-looking content.
- Touch docs whose source hasn't actually changed in a load-bearing way.

---

## Step 4 — Commit & PR

After all edits are done. **File the `Type:cleanup` issue FIRST** (the filing contract is
below, and it is unchanged) so its key exists before the PR is composed: the key is what
puts this PR in the gated lane, and the arm at the end of this step is only safe once it is
on the PR. Then:

```bash
# Create branch — from a FRESHLY FETCHED origin/main, never from whatever this checkout
# last saw (<slot:git-workflow>). A stale base carries old submodule gitlinks where the
# repo has them and fails the submodule guard among <slot:git-workflow> over
# work this sweep never touched; no local hook can warn you. Safe with the edits already in
# the tree: this sweep is the single writer to these docs, so origin/main cannot have moved
# them underneath you.
BRANCH="<slot:git-workflow>"   # the chore branch form, slugged arch-reconcile-<date>
git fetch origin
git checkout -b "$BRANCH" origin/main

# Stage exactly the docs you edited
git add <each reconciled doc path>

# Commit — the cleanup issue exists by now, so the commit carries its key rather than a
# no-issue marker (<slot:git-workflow>)
git commit -m "chore(arch): [<KEY>] reconcile arch docs — <list of docs>"

# Push and open PR — the cleanup issue key goes in the TITLE and the BODY. The branch
# is the repo-meta chore form and carries no key, so the title/body is the only place
# the fix gate can resolve this PR's subject from; without it the gate reads the PR as
# non-lane work and passes, and the arm below would merge it ungraded.
git push -u origin "$BRANCH"
gh pr create \
  --title "chore(arch): [<KEY>] arch-doc reconciliation sweep — $(date -u +%Y-%m-%d)" \
  --body "..."   # includes a bare `Refs <KEY>` line — never a closing keyword

# Confirm the key actually landed on the PR, then ARM. Self-heal rather than trust the
# composed prompt: a missing key is not cosmetic here, it is the gate's whole subject.
gh pr view <pr> --json headRefName,title,body | grep -q "<KEY>"   # must match

# ARM AUTO-MERGE AT OPEN — the moment the PR exists, not after CI passes (ENG-8780).
# Arming is not certifying: the required fix-gate check fails closed on <KEY> until
# `/zetify:verify` posts its pass, so this PR reads BLOCKED and does not merge. What
# the arm buys is that the PR is never an invisible one — an unarmed PR shows no red
# check, no conflict and no queue entry, and sits until somebody happens to look.
# No `--require-green`: that flag is the verifying session's final re-arm, and a red
# fix-gate check is the EXPECTED state here.
python3 knowledge/scripts/gh_automerge_arm.py <pr>
python3 knowledge/scripts/gh_pr_merge_state.py <pr>   # must read armed / queued / merged — confirm, never assume
# (an ENQUEUED PR reads autoMergeRequest: null, so `gh pr view --json autoMergeRequest` alone calls it unarmed)
```

PR body must include:
- One-sentence summary of what drifted and what was reconciled
- Per-doc table: each reconciled doc → source paths → the prose correction made
  (only substantively-reconciled docs appear in the PR; optionally list any
  cosmetic-drift docs as "left untouched" for transparency)
- Autonomous Decisions Log (verbatim, from Rule B)
- Note: "Opened by the arch-doc reconciliation sweep."
- The **cleanup issue key** this sweep filed for itself (below), on its own line as a
  bare `Refs <KEY>` link — **never** a closing keyword — so the PR and the gate are
  joined by something a reader, and the gate, can follow in either direction.
- **The arm, stated honestly:** "auto-merge is armed; the required fix-gate check holds
  this PR until `/zetify:verify` passes." Never a line claiming this sweep verified
  itself, and never a line claiming the merge is this run's to pull. It is not.

Each run opens its own independent PR — but no longer an *unowned* one. This sweep
used to open a PR with no issue behind it, on the reasoning that a recurring routine
is not a one-shot task; that is also exactly what left it with nothing to hand to and
no queue to sit in, which is how "maintenance tooling" became a merge nobody graded.
**File one cleanup issue per run** (`slot:tracker-identity`) naming the docs
reconciled — **before** composing the PR — and carry its key in the PR title/body the
way `slot:git-workflow` specifies, so the gate has a subject. That key is the gate's
only handle on this PR (the chore branch form carries none), so a run that skips it
does not merely lose a cross-reference: it takes the PR out of the gated lane entirely.

**File it exactly the way every other filer does — through Fleet's `file_issue`.**
Call `file_issue` with `kind: "cleanup"`, `command: "arch:reconcile"`, the title, the body
naming the docs, and `repo` only when the docs live in another checkout. **No priority, no
project, no placement**: birth is `triage` (Triage Queue) by kind, and the filer is the wrong
party to decide the rest. **No Fleet tools? Stop.** When the session has no Fleet tools, stop
with: *this command needs the Fleet tools; create a personal key in Fleet under Settings › Connect your tools*.
There is no other filing path — never fall back to a tracker script.

**Wait for `filing.trackerKey`** — poll `get_issue` / the filing result every 15s, max 10
minutes. On timeout, end **partial** naming the filing id (the PR cannot enter the gated lane
without a key). Once the key exists, open the PR carrying `<KEY>`, then `comment` the PR URL
onto the issue so the checker's prior-art search reads it as this issue's own PR rather than
somebody else's work on the same ground. Two writes, one direction — and the ordering is not
stylistic, it is what keeps the window between "PR exists" and "PR is in the gated lane" at
zero. **This run moves the filing nowhere** — leave it in `triage`.

> ⚠️ **`triage` is the only position a filer may use, and a priority is not a way to buy
> a different one.** The partition guard exempts exactly the check-gate window
> (`slot:registers-triage-partition`); a fresh issue born outside it with no priority is a
> **blocking** partition-guard violation that reds **every open PR in the receiving
> repository**, not just this sweep's — and a sweep that reds the whole board is worse than
> a sweep that never ran. Setting a priority here to dodge that is the same defect wearing
> a workaround: priority is the checker's output, and a maintenance routine that guesses it
> has started triaging itself.

---

## Step 5 — Hand off to the gate, and stop

**🛑 You do not certify this sweep and you do not merge it.** There used to be a
verification step here: re-run the validator, confirm the DRIFT lines you caused are gone,
call it done. That is a self-verification wearing a verify step's name — it asks the
validator whether the *shape* is clean, which it was before the sweep too, and it asks
nobody at all whether the prose now says something true about the code. Those are the two
different questions, and only the second one is why this command exists.

**The PR you leave behind is armed, and that is not a contradiction of the line above.**
Arming says *"merge this when everything that gates it says yes"*; it does not say yes on
anybody's behalf, and it cannot: the required fix-gate check is failing on `<KEY>` from the
moment the issue is filed, so the armed PR reads `BLOCKED` until a session that has never
seen this one posts a pass. What the arm removes is the failure mode where this sweep's PR
is *invisible* — unarmed, un-conflicted, un-queued, and therefore indistinguishable from a
healthy PR nobody needs to look at (ENG-8780). The merge is still not yours to pull, and
you do not wait for it.

**The handoff is the filing, and the gate you hand to is [`/zetify:check`](../check.md).**
With the PR open and CI green, the cleanup issue is already sitting in `Triage Queue` where
Step 4 filed it; **that is where you leave it, and the run ends there.** You move no issue,
here or anywhere. The checker is a fresh session that has never seen this one: it confirms the sweep
is real, sets the priority, the `Component` and the project this run had no business
guessing, and releases the issue — and from there the ordinary path carries the PR to
[`/zetify:verify`](../verify.md), the session that reads the ledger below and pulls the
merge. Four states and two gates, none of them yours.

> **Why the run does not shortcut straight to the review state** — which is what it did on
> the day this step was written, and it is a CI landmine rather than a shortcut. A freshly
> filed issue carries no priority, by design; the check-gate window is the only place the
> partition guard tolerates that, and the guard is **blocking**, inside `ci-success`. An
> issue dropped into the review state with no priority therefore hard-fails CI on **every
> open PR in the repository** until a human moves it back by hand. The handoff a filer owns
> is the one to the checker; the handoff to the verifier is the checker's to arrange, and it
> is not a step this sweep can skip its way to.

**The ledger the verifier grades against is the PR body's per-doc table** — one row per
reconciled doc, naming the source paths that drifted and the prose correction made. Each row
is a claim, exactly as a cause ledger's lines are, and each is checkable at the PR head by a
reader who opens the doc and the diff beside it. Write that table for a stranger, because a
stranger is who reads it.

Leave the validator's own output in the PR body as **evidence, not as a verdict**: run
`python3 knowledge/scripts/validate_arch_docs.py --list-subjects` and paste what it says. DRIFT
should be gone for any doc whose prose you changed (the commit advanced its baseline); docs you
intentionally **left untouched** (cosmetic drift) will still show an advisory `DRIFT` line —
that is expected, and you do **not** re-stamp them to silence it.

---

## Exit conditions

| Condition | Action |
|---|---|
| **Empty subject set** (`python3 knowledge/scripts/validate_arch_docs.py --list-subjects` prints nothing) | Contract adopted: print `arch-reconcile FAILED — the freshness contract has no subjects` and exit **non-zero**, never the OK line. Never adopted: `NOT APPLICABLE`, exit zero |
| No substantive drift (subject set non-empty) | Print "architecture docs OK — no substantive drift" **with the subject count** and exit cleanly (no branch, no PR, no re-stamp) |
| All drifted docs reconciled, PR open | Report PR URL + reconciliation summary + the cleanup issue key, filed in `Triage Queue` and left there for the checker, + `auto-merge armed` (confirmed non-null `autoMergeRequest`; `NOT ARMED — <why>` is a failure to fix before this run is done). **Never** a merge, and never a state move |
| Some docs reconciled, some skipped (cap / unreadable) | PR open with subset; log skipped docs in PR body + Autonomous Decisions Log; hand off as above |
| Validate fails on shape/path error (blocking) | Report the blocking error; do not attempt reconciliation (those errors need human review) |
