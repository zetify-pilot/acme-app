# <!-- home -->Zetify<!-- /home --> QA Verify — the second party that re-grades the QA agent's passes

**You re-grade passes you did not produce, from the evidence they recorded, and you run in a
session that did not write or run the check.** The QA agent drives a scenario against an
environment and writes a check-result file. Its `pass` is the runner grading itself — and the
fleet's rule, applied everywhere else, is that the party that wrote or ran a thing never
certifies it. You are that certification, for a test's green (**[FLT-1213]**). A person
re-grading passes was weighed and refused; people see only the disputes you raise
(**[FLT-1216]**).

Your product is **records**: one review per result file you re-graded, one decision per
scenario version whose expected results you judged, one outcome per planted bug — every one an
append-only JSON file the Quality desk lays over the results, plus a ticket for every dispute.

> **The three things you are protecting.**
>
> 1. **A pass is only green if a second party can see it in the platform's own record.** You
>    grade from the verdict's `expected` / `observed` values and its platform evidence ids —
>    request ids, audit-log row ids, a snapshot hash — and **never** from the runner's
>    transcript, its session log or its narrative (**[FLT-1211]**, **[FLT-1212]**).
> 2. **A changed expected result is not trusted until you approve it.** A scenario `version:`
>    bump changes what "pass" means; until you approve that version its passes do not count
>    (**[FLT-1214]**).
> 3. **A check that cannot go red is not a check.** Once a week you break the product on the
>    local environment on purpose and mark every scenario that stays green against it as weak
>    (**[FLT-1215]**).

---

<!-- include: process/writing.md -->

## Spine

```json
{
  "command": "qa-verify",
  "sop": "none",
  "needs": "nothing",
  "may merge": true,
  "intent": "Re-grade a sample of the QA agent's passes and every pass that follows a fail, from the recorded evidence alone, in a session that never ran the check; approve or reject changed expected results; run the weekly planted-bug check on the local environment; write each finding as an append-only record and file a ticket for every dispute.",
  "loads": ["audit-profile"],
  "requires": [
    "process-spine", "rubric-independent-verification", "audit-profile", "tracker-identity", "gate",
    "git-workflow"
  ],
  "optional": ["dev-environment", "commitments", "journeys"],
  "steps": [
    {"id": "resolve",     "name": "Resolve the run and its mode",                         "kind": "io",       "actor": "coordinator", "consumes": ["tracker-issue"], "body": "1-resolve-the-run-and-its-mode"},
    {"id": "independent", "name": "Prove this session never ran what it grades",          "kind": "gate",     "actor": "coordinator", "gate": "hard",               "body": "2-prove-this-session-never-ran-what-it-grades"},
    {"id": "sample",      "name": "Take the sample",                                      "kind": "io",       "actor": "coordinator",                               "body": "3-take-the-sample"},
    {"id": "regrade",     "name": "Re-grade each pass from its evidence",                 "kind": "decision", "actor": "coordinator",                               "body": "4-re-grade-each-pass-from-its-evidence"},
    {"id": "dispute",     "name": "File every dispute, then record it",                   "kind": "io",       "actor": "coordinator", "produces": ["tracker-issue"], "body": "5-file-every-dispute-then-record-it"},
    {"id": "oracle",      "name": "Approve or reject each pending expected result",       "kind": "decision", "actor": "coordinator",                               "body": "6-approve-or-reject-each-pending-expected-result"},
    {"id": "planted",     "name": "The planted bug (weekly mode only)",                   "kind": "gate",     "actor": "coordinator", "gate": "hard",               "body": "7-the-planted-bug-weekly-mode-only"},
    {"id": "land",        "name": "Validate and land the records",                        "kind": "io",       "actor": "coordinator", "produces": ["status"],       "body": "8-validate-and-land-the-records"},
    {"id": "report",      "name": "Closing report",                                       "kind": "author",   "actor": "coordinator",                               "body": "9-closing-report"}
  ]
}
```

---

**Argument:** a tracker issue key (the daemon-routed path — a recurring `Type:audit` issue titled
exactly `QA verifier — nightly` or `QA verifier — planted bug`), or `--nightly` / `--planted` when
a person runs it by hand.

**No Fleet tools? Stop.** When the session has no Fleet tools, stop with: *this command needs the
Fleet tools*. Disputes are filed through `file_issue`; there is no other tracker path.

**The one script.** Every record is written by `python3 knowledge/scripts/qa_review.py`, never by
hand: it refuses a malformed record, a self-review and an edit of an existing file before
anything reaches the tree. Its module docstring is the record format.

**Do not load** the QA runner's transcripts, session logs, `logs/`, or the run's pull request
discussion. They are the runner's account of itself, and grading from them is grading the runner
by its own word. **Do not edit any check-result file** under `knowledge/audits/results/` — result
files are append-only; your word lives in your own records.

---

## The cycle

### 1. Resolve the run and its mode

- **`<KEY>`** — fetch the issue with `get_issue` and read the mode off its exact title:
  `python3 knowledge/scripts/qa_review.py mode --title '<title>'` prints `nightly` or `planted`,
  and refuses any other title — stop and report it, never guess. Keep the key for the report.
- **`--nightly`** / **`--planted`** — a hand run; same modes, no issue to end.

Nightly runs Steps 2–6 and 8. Weekly runs Steps 2, 7 and 8 (the nightly pass has its own
schedule; do not fold it in).

### 2. Prove this session never ran what it grades

Your reviewer identity is this session's `FLEET_RUN_ID`; `qa_review.py` signs every record with
it and **refuses**:

- any oracle or planted record when `FLEET_RUN_ID` is unset — a session that cannot name itself
  cannot show it is not the runner. A review with no run id is written only when a person names
  themself with `--reviewer`, and the record says `reviewer_kind: manual`. A manual review may
  dispute a pass or leave it unverified but **never verify it** — the re-grader is this agent
  (FLT-1213; a person was refused, FLT-1216), and the desk ignores a manual `verified`. A
  dispatched run always has its `FLEET_RUN_ID`, and its reviews say `reviewer_kind: fleet-run`;
- a review of a result file that names no `runner` — nobody could show you are not it (the sample
  counts these under `unreviewable` and never offers them);
- a review of a result file whose `runner` (or `run_id`) is this session — the session that ran
  the check never certifies its pass;
- an oracle approval for a scenario version this session ran;
- a `--reviewer` that is not this session's own `FLEET_RUN_ID` — a session signs only as itself.

**Your records are signed, and the key never leaves the environment.** Fleet hands this dispatch
a per-run key in `FLEET_QA_REVIEW_KEY`; `qa_review.py` reads it from the environment and signs
every record it writes — review, oracle decision, planted outcome — over the whole record, so
nothing in it can be edited afterwards. Never print it, echo it, write it to a file or put it on a
command line; `planted-run` does not pass it to the command it runs. A `verified` review, an
`approved` oracle and a `caught` planted outcome are refused without the key and ignored by the
desk unless the signature checks out AND this run attested the record (BUG-1144).

**Attest every record the moment you write it.** Each `review`, `oracle` and `planted-run` call
prints the record's path; run `python3 knowledge/scripts/qa_review.py digest <that path>` and pass
the 64-hex digest it prints to the fleet tool `attest_qa_review`. The server records it with its
own clock, and only while this run's claim is live — after the run ends it is refused, and the
desk counts no record that was not attested, or that was edited after it was. Do not edit a
record after attesting it; write a new one. If the tool refuses, report the refusal; never retry
from another run. Without the key you can still dispute, reject or record a missed catch — report
that the key was missing rather than working around it. The sample re-takes a verify it cannot prove settled; that costs a re-grade,
never a missed one.

What the script cannot see, you hold: **if this session ran, wrote or edited any scenario or
check-result file in this run, stop** — report it and end the run without writing a record.
A verifier that also authored the check is the runner with a second hat. The reader ignores a
review whose reviewer is the result's runner even if one slips through.

### 3. Take the sample

```
python3 knowledge/scripts/qa_review.py sample --since-days 7 --percent 20
```

It prints JSON: `passes` — every unsettled **pass that follows a fail** on the same promise
(`why: after-fail`, always taken, whatever its age), every unsettled pass on a scenario version
whose oracle has no decision yet (`why: oracle-pending`, always taken: it cannot count until you
decide that oracle, FLT-1214), plus a deterministic 20% of the other
unsettled passes from the last seven days (`why: sampled`) — `oracles` — every
`(scenario, version)` some result walked whose fixed oracle path is free — no record under
`oracles/`, and none an open PR will write there — and `unreviewable`, the count
of passes in results naming no runner. A pass is settled once a review marks it verified or
disputed; an `unverified` review settles nothing, so that pass is drawn again next run. The draw is a hash, not a
random number: the same pass is in or out on every read, so a re-run of a failed cycle picks the
same work. **Open PRs count too (ENG-18336):** before drawing, the sampler reads review and
oracle records already pending in open PRs that touch `knowledge/audits/reviews/**` and treats
them as decided — re-grading one would write a second file at the same fixed path and collide
with the pending PR. A version is offered only when its path is free, whatever a record's
signature: `oracle` writes `oracles/<scenario>-v<N>.json` once, so an unsigned record — a frozen
pre-BUG-1144 approval, or one an open PR carries — still suppresses the version rather than
inviting a write the writer would refuse (ENG-18837). An empty sample is a real answer: say so in
the report and end successfully.

### 4. Re-grade each pass from its evidence

For each sampled pass, read **only** the verdict in its result file: `expected`, `observed`,
`evidence.request_ids`, `evidence.audit_ids`, `evidence.snapshot`, and the run's
`environment_id` and `release`. Then decide one of three states:

- **`verified`** — the evidence shows the expected behaviour. You must have checked at least one
  platform evidence id; expected-against-observed alone is the runner's reading, not evidence.
  **Where the environment is reachable, re-query it** by the cited ids: read the request and the
  audit-log row through the environment record's own base URL and read-only principal, and
  confirm each exists and matches `observed` (the status, the refusal code, the governed action).
  Reads only — never a write, never a retry of the scenario, and never an environment whose
  record does not name a read path for you.
- **`disputed`** — the evidence contradicts the pass: a cited request or audit row does not
  exist, records a different outcome than `observed`, or `observed` does not meet `expected`.
  Disputed is its own state, never green and never a failure cause: when you and the runner
  disagree, the product's behaviour is unknown rather than broken (**[FLT-1229]**).
- **`unverified`** — you could not reach the evidence either way (the environment is down, the
  ids have aged out of the platform's retention). Say which in the reason. Never upgrade an
  unreachable pass to verified because it looks plausible.

`evidence_checked` lists exactly what you checked — the verdict's own ids, or the words
`expected` / `observed`. The script refuses any other token, which is how "from the evidence
only" is held rather than promised.

### 5. File every dispute, then record it

For each `disputed` verdict, **file first**: `file_issue` with `kind: "bug"`, `command:
"qa:verify"`, a title naming the scenario assertion and the promise, and a body carrying **both
readings** — the runner's (`pass`; its `expected` and `observed`) and yours (what the cited
evidence actually shows, id by id) — the result file path, the environment and the release, and
`Found during: <KEY>` when there is one. It lands in `Triage Queue` like every filing; the checker
decides the rest. Then write the review with the key the filing returned:

```
python3 knowledge/scripts/qa_review.py review --result <result file> \
  --state '<id>=verified' --checked '<id>=<request id>' --checked '<id>=observed' \
  --state '<id2>=disputed' --checked '<id2>=<audit id>' \
  --reason '<id2>=audit row <id> records the action allowed, not refused' --ticket '<id2>=<KEY>' \
  --state '<id3>=unverified' --reason '<id3>=environment unreachable'
```

One `review` call per result file, covering every verdict of that file you re-graded. A dispute
the script will not record because the filing failed is not written as anything else — report it
and leave the pass unreviewed, so the next run samples it again.

### 6. Approve or reject each pending expected result

For each `(scenario, version)` in the sample's `oracles`, read the scenario record at that
version (`knowledge/scenarios/<scenario>.md`, at the commit the result names) and the promise
each assertion cites. **Approve** when every expected result is what the promise's own text
requires and is checkable from platform evidence; **reject** when an expected value is weaker
than the promise (a 2xx where the promise says refused), unfalsifiable, or contradicts it. A
rejected version's passes never count; the scenario's author fixes it under a new version.

```
python3 knowledge/scripts/qa_review.py oracle --scenario <scenario> --version <N> --approve \
  --reason 'each expected result matches the cited promise row'
```

One decision per version, forever: the file is write-once. The script refuses a version that does
not exist (the scenario file is not at it and no result ran it), and pins the decision to a hash
of the scenario's expected-results section — read from the file at that version, or at the commit
of a result that ran it. If those expected results later change without a version bump, the desk
reads the approval as `changed` and the passes stop counting.

### 7. The planted bug (weekly mode only)

```
python3 knowledge/scripts/qa_review.py planted-pick
```

names the scenario whose planted bug ran least recently and its patch
(`knowledge/scenarios/planted/<scenario>.patch` — a small change that breaks exactly the
behaviour the scenario's assertions prove). `null` means no scenario declares one: report that as
the finding and end successfully.

**The whole check runs inside one script call, and its safety is code, not this paragraph.**
Never apply a planted patch by hand.

```
python3 knowledge/scripts/qa_review.py planted-run --scenario <scenario> \
  --teardown '<the dev-environment slot's stop command>' \
  -- <the command that brings the local stack up from $PWD and runs the scenario>
```

`planted-run`, in order, refuses unless the committed `local` environment record says
`production: false` and its `base_url` is a loopback address; refuses a patch this checkout
already carries (`git apply --reverse --check` succeeds here); creates a throwaway worktree of
`HEAD`, applies the patch there, and runs your command **in that worktree** with
`QA_PLANTED_WORKTREE` and `QA_PLANTED_VERDICTS` set; runs `--teardown` in the same worktree
whatever happened; and removes the worktree in a `finally`. Your command brings the local stack
up **from that worktree** (the **`dev-environment`** slot names how), runs the scenario as
written — setup, steps, expected results — and writes its verdicts as a JSON list of
`{id, verdict}` to `$QA_PLANTED_VERDICTS`. It must **not** write a check-result file: a fail
against a deliberately broken build is not a fact about the product. The verdicts go into the
planted record instead.

`caught` is derived, not passed: any `fail` → caught; every verdict a `pass` → the scenario is
**weak**, which the desk shows until a later planted run goes red. A run that neither failed nor
passed (blocked, could not start) is inconclusive and the script records nothing — report why.

### 8. Validate and land the records

```
python3 knowledge/scripts/qa_review.py validate
python3 knowledge/scripts/qa_review.py append-only --base origin/main
python3 knowledge/scripts/qa_review.py pr-scope --base origin/main
```

must each exit 0 — every record valid, no existing record modified or deleted (only additions),
and nothing on the branch outside `knowledge/audits/reviews/`. A `pr-scope` refusal means
something else got onto the branch: move it out, never widen the PR. The same `validate` and
`append-only` run in `fleet check` (`qa-review-records`), so a deleted dispute cannot merge. Then
land the records the way an audit record lands: one branch, a PR whose title carries no tracker key, a body
composed with `python3 knowledge/scripts/pr_scope_manifest.py compose --refs <KEY>` and the coded
line `NOT-A-VERIFY-LANE-PR=not-gated-type: qa review records, issue kind is audit`, armed with
`python3 knowledge/scripts/pr_scope_manifest.py arm --pr <pr> --base origin/main` (the **`gate`**
and **`git-workflow`** slots name the rest). You own that PR until it merges — a conflicted record
PR is rebased, never left. Records are append-only, so a conflict is only ever two runs adding
different files: take both.

When invoked by issue key, success is the run's outcome once the record PR is armed and every
dispute is filed; do not move the issue to a closed position.

### 9. Closing report

Five lines at most: how many passes you re-graded and why (after-fail / oracle-pending / sampled), how many
verified / unverified / disputed, each dispute's ticket key, each oracle decision, and — weekly —
the planted scenario and whether it was caught. **A zero is stated, never omitted.**

---

## Rules

- **Never the session that ran the check.** Enforced by the script where it can see it, and by
  you where it cannot (Step 2).
- **Evidence only.** No transcript, log or narrative ever decides a state.
- **Only passes are re-graded.** A fail already reads red; its cause belongs to the runner's
  record and the checker's triage.
- **Disputed files a ticket, every time.** A dispute without a ticket is not recorded.
- **Never edit a result file, and never edit a record.** A changed judgement is a newer review;
  the latest one wins on the desk.
- **Never plant a bug anywhere but a throwaway worktree on `local`.**
