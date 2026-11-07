# Zetify Audit

**No Fleet tools? Stop.** When the session has no Fleet tools, stop with: *this command needs the Fleet tools*. There is no other tracker path — never fall back to a tracker script.

Run a **checklist-driven audit** of the product and leave artifacts behind:
a single **rolling** audit record per scope under `knowledge/audits/` (the
latest run, superseding the prior), the previous run's validation result
carried into it, and — depending on finding *nature* — either a direct fix PR
or a small number of **consolidated** tracker issues.

> **SOP:** the automated subset of this repo's SOP for the same job, where it has one.

**One execution model, three options.** Every audit runs the same way: **the coordinator never
does the work.** It resolves the scope, enumerates the atoms the checklist's profile names,
partitions them into **units**, dispatches **one fresh-context sub-agent per unit**, verifies
what comes back, synthesizes across units, triages, files, and keeps the ledger (§2a). It does
not read source to find defects, drive the browser, query the DB, or write a fix — in **any**
configuration. That rule used to be conditional on the execution mode, which is exactly how the
narrowly-scoped path became the one that blew its own context and truncated its coverage ledger.

What varies is **input**, not model:

| Option | Values | Decides |
|---|---|---|
| `type` | `ux` `ui` `feature` `security` `authz` `api` `architecture` `evidence` `eval` `performance` `accessibility` `docs` `product` | which checklist + dimensions the sub-agents receive |
| `scope` | one journey/route/package/handler · an area · the full surface | how many units enumerate yields |
| `--autonomous` | off (default) · loop until stopped | whether the run re-verifies fleet fixes and re-enumerates after filing (§2h) |
| `--objective` | *(set/show only)* a one-line durable campaign goal | writes the objective file `slot:audit-profile` names and exits; an autonomous run reads it and adopts its done-bar (§2h) |

Everything the old three-mode taxonomy encoded is **derived**, not selected: a one-journey scope
is a run with one unit; a full-surface code-correctness run is one whose units are all
parallel-safe; a `ux`/`ui`/`feature` run has a mix of parallel (static) and exclusive (live)
units. **Do not reintroduce a mode selector** — the two axes it conflated (breadth; whether a
unit can run concurrently) are an input and a per-unit property, and neither is a property of
the command. The parallel lane still runs through the reusable
fan-out workflow `slot:audit-profile` names (a repository without one runs every
unit through the serial lane below, and says so), which fans a finder over every unit,
**adversarially refutes** every S1/S2 against the cited source, and runs a **cross-unit
synthesis** pass — the divide-and-conquer that let the 2026-07 API (532 ops) and architecture
(297 packages) sweeps be exhaustive *and* precise (0 refuted).

**This command absorbs the former `/zetify:product-audit` and `/zetify:audit-objective`.** A <!-- tilion-refs:skip -->
continuous whole-product campaign is `/zetify:audit product --autonomous`; a continuous
single-type campaign is `/zetify:audit ux --autonomous`. There is no second command, no second
loop, and no second filing model — which is what the old split kept re-deriving and drifting on.
`product` (§2d) and a multi-line `Type:audit` issue (§2e) remain **orchestration wrappers**:
they sequence whole runs, they are not execution models, and this model does not replace them.

Findings file **guardrail-first** for the correctness/access types (§3d); experiential findings
triage by nature (§3a–c). Every finding first passes the **customer-harm gate** (§3a′).

**Triage rule (applied in Step 3) — gate by nature, not file count.** The old
"< 50 LOC and < 4 files" size gate filed too many tiny tickets (a one-line token
swap spread over four files became its own tracker issue). Classify each finding
instead:

- **Mechanical drift** — a single known-pattern transformation toward a
  *canonical* target, with no design decision: the transformations
  `slot:ui-contracts` names for this repo (token/color swaps, off-scale
  sizes onto the scale, an already-keyed string wrapped for i18n, a bespoke state block
  swapped for the catalog's, a dead value deleted, an inline style onto a utility). **The auditor fixes these in-session and
  batches all of them into one PR — regardless of how many files or LOC they
  span.** A mechanical sweep across 12 files is still one batched fix, not 12
  tickets. (It stops being mechanical — and gets filed — once it needs *new* copy /
  i18n keys, a design decision, an API/contract change, or a real refactor; sanity
  cap ~150 LOC of genuine change per theme.)
- **Judgment / behavioral / broken** — needs a design call, new copy/keys, an API
  change, a refactor, or it fixes broken behavior / a security or access defect.
  **File it** (screenshot + forensic) for `/zetify:bug:fix` /
  `/zetify:task:implement` — never auto-fixed in the audit. **Consolidate before
  filing:** group by fix-surface / root cause and file **one issue per theme**,
  not per file or symptom. A heavy pass files **~1–3 themed issues**, not eight
  per-component tickets. S1/S2 broken-behavior findings always file; the cap
  governs S3/S4 drift themes — surplus themes roll into the record's next-run
  seed, not into tickets.

**Critical-first phase override (check the program phase first).** Read
`slot:audit-profile`. While it declares `critical-first`, the
program hunts **S1/S2 correctness + security** and defers cosmetic polish. It **overrides both
the effort and the filing rules below**: the `ui`/`ux` live lane runs correctness/behavioral/
silent-failure/access dimensions **exhaustively** but cosmetic dimensions (typography/token/
dark-mode) as a **light spot-check** (§2c-live), and filing floors to **S1/S2 + every
security/authz/evidence finding**, with **all** S3/S4 cosmetic drift rolled to the next-run seed
— zero tickets, not the ~3-theme cap (§3c). The free mechanical-fix batch PR (§3b) still runs.
When the phase line reads `phase: exhaustive`, ignore this override and apply the caps as
written.

**Type carve-out (filing model by type).**
- **`ux`/`ui`** (and any narrowly scoped run of them): triage by nature (§3a–c). The in-session
  **mechanical-fix batch** (§3b) is for `ui`/`ux`/`api` cosmetic + convention drift;
  judgment/behavioral findings consolidate by theme and file (§3c).
- **`architecture`/`api`/`security`/`authz`/`evidence`**: file **guardrail-first** (§3d) — every
  finding class ships a preventer, one issue per guardrail. A correctness/access finding is
  never "mechanical polish" the auditor self-merges.
- **`eval`**: file every finding, guardrail = a new frozen eval case (§3d tail).
- **`docs`**: the audit **reports and never edits** (§2g-docs). One finding per stale page,
  filed to the **`triage`** and nowhere else; a fix goes through `/zetify:task:implement`,
  never the auditor. A missing page for a shipped capability is a defect in the **catalogue**;
  a page that promises what the product does not do is a defect in the **page** — correct the
  page, never build the feature to match it. No mechanical-fix batch, no guardrail issue.

This carve-out is keyed on the **type's `fileAs`** (the engine's `FILE_AS` is a per-run flag —
it cannot express a per-finding decision). Re-keying filing on the finding rather than the run
is a worthwhile change and a **separate** one: it needs an engine change, not a prose edit.

The consolidation instinct is the same everywhere: never one issue per symptom/file.

Invocation: `/zetify:audit <type> [scope description] [--autonomous]` · `/zetify:audit
--objective "<goal>"` to set the campaign goal · **or** `/zetify:audit <KEY>` when a
`Type:audit` tracker issue names the audit (the daemon-routed path — `--autonomous` is
**refused** there, see §2h).

- `<type>`: one of the audit types `slot:audit-profile` declares — each with a
  checklist (`slot:audit-profile`). Two are structural and exist everywhere:
  `feature` (**one feature area per run** — intent delivery + capability conformance +
  stranded-backend; with no scope this is the **rotation**, §2i) and `product` (the
  whole-product umbrella — orchestrates the full-scope `feature` + surface passes, then one
  top-level product-health synthesis; §2d). `docs` is the shared documentation type (§2g-docs):
  its enumerate recipe and per-page dimensions ship with the command, and a repository declares
  it by listing it in `slot:audit-profile` and filling `slot:docs` — a repository that does
  neither, or that omits the `docs` checklist, is **refused** with the degradation the slot
  names, never run against pages the command cannot locate. The rest — a UX type, a UI type, an
  access type, an evidence type, an eval type, a security type, an API type, and whatever else
  this product audits — are the repo's.
- `[scope]`: optional narrowing — e.g. "the integrations pages", "the meeting
  wizard", "re-verify closed findings only". Default: the full web app. For `feature` the
  scope is not free text — it is one of exactly four forms: *(blank)* = the rotation ·
  `<area>` · **`family:<name>`** (a product grouping of areas — `family:agents` and friends,
  the `Family` column of
  [`feature-coverage-ledger.md`](../../../knowledge/audits/feature-coverage-ledger.md)) ·
  `all areas`. See Step 0.
- `<KEY>` (e.g. `ENG-456`): a **`Type:audit`** tracker issue — typically a post-ship
  audit follow-up filed by `/zetify:prd:implement` / `:verify` and picked up by the
  fleet daemon. Resolve the type + scope **from the issue** (Step 0), run the
  audit, and — since an audit has no PR — **end the run successfully** when finished
  (Step 6). The run's outcome is how the daemon recognizes success.

Read the user's input: $ARGUMENTS

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. **The todo list mirrors the ledger (§2a); the ledger is authoritative** — on disagreement, rebuild the todos from the file. There is no mode branch: every run takes the same path, and steps with nothing to do close as `N/A` (a run with no live unit closes `dispatch-live`; a one-pass run closes `autonomous-cycle`; `product` additionally takes §2d's orchestration). A failed `gate` (coverage gap) or an exhausted `loop` stays open with its residual noted — never silently closed. The prose Steps below are the authority; this spine indexes them. Note the two dispatch steps are opposite kinds: `dispatch-parallel` is a **`fanout`** (concurrent static finders), `dispatch-live` is a **`loop`** (one browser sub-agent at a time — §2c-live).

```json
{
  "command": "audit",
  "intent": "Checklist-driven audit: partition the ground, fan out one fresh sub-agent per unit, refute, synthesize → rolling record + filed findings.",
  "sop": "none",
  "needs": "answers",
  "may merge": true,
  "loads": ["audit-profile", "process-issue-shape"],
  "requires": [
    "process-spine", "process-issue-shape", "rubric-finding-severity", "rubric-issue-priority",
    "registers-triage-partition", "audit-profile",
    "tracker-identity", "gate", "dev-environment", "git-workflow", "ui-contracts", "process-interview"
  ],
  "optional": [
    "feature-maps", "api-contract", "permissions", "security", "operations", "components", "commitments",
    "journeys", "planning-model", "languages", "file-conventions", "docs"
  ],
  "steps": [
    {"id": "resolve-invocation",  "name": "Resolve invocation (type · scope · autonomous)",   "kind": "decision", "actor": "coordinator", "consumes": ["tracker-issue", "audit-record"], "body": "step-0-resolve-the-invocation"},
    {"id": "open-ledger",         "name": "Open or adopt the run ledger",                     "kind": "gate",     "actor": "coordinator", "gate": "hard",               "body": "2a-the-run-ledger"},
    {"id": "reverify-prologue",   "name": "Rotation: drain ≤3 ripe S1 re-drives, then discover", "kind": "loop",  "actor": "subagent",    "model": "sonnet", "loop": {"exit": "3 drained, or no ripe S1 left"}, "body": "2i-the-feature-rotation"},
    {"id": "enumerate-partition", "name": "Enumerate atoms + partition into units",           "kind": "author",   "actor": "coordinator",                               "body": "2b-enumerate-and-partition"},
    {"id": "env-prep",            "name": "Environment prep (only if a live unit exists)",    "kind": "io",       "actor": "coordinator",                               "body": "step-1-environment-prep"},
    {"id": "dispatch-parallel",   "name": "Dispatch parallel units (engine fan-out)",         "kind": "fanout",   "actor": "subagent",    "model": "sonnet",            "body": "2c-dispatch"},
    {"id": "mint-worklist",       "name": "Static output mints the live worklist",            "kind": "author",   "actor": "coordinator",                               "body": "2c-dispatch"},
    {"id": "dispatch-live",       "name": "Dispatch live units, one at a time",               "kind": "loop",     "actor": "subagent",    "model": "sonnet", "loop": {"exit": "every live unit is done or failed"}, "body": "2c-live"},
    {"id": "coverage-reconcile",  "name": "Reconcile coverage (done == expected)",            "kind": "gate",     "actor": "coordinator", "gate": "hard",               "body": "2c-live"},
    {"id": "verify",              "name": "Verify S1/S2 (adversarial · re-observe)",          "kind": "fanout",   "actor": "subagent",    "model": "sonnet",            "body": "2f-verify"},
    {"id": "synthesize",          "name": "Cross-unit synthesis",                             "kind": "author",   "actor": "subagent",    "model": "sonnet",            "body": "2g-synthesize"},
    {"id": "triage",              "name": "Triage by nature + apply the filing floor",        "kind": "decision", "actor": "coordinator",                               "body": "3a-triage-by-nature"},
    {"id": "fix-batch",           "name": "Batch mechanical fixes into one PR",               "kind": "io",       "actor": "subagent",    "model": "sonnet",            "body": "3b-mechanical-findings"},
    {"id": "file-findings",       "name": "File findings (guardrail-first / by theme)",       "kind": "io",       "actor": "coordinator", "produces": ["tracker-issue"], "body": "3c-judgment-findings"},
    {"id": "autonomous-cycle",    "name": "Autonomous: re-verify fleet fixes, re-enumerate",  "kind": "loop",     "actor": "coordinator", "loop": {"exit": "human stop, the objective done-bar, or two consecutive dry cycles"}, "body": "2h-autonomous-mode"},
    {"id": "render-record",       "name": "Render the record from the ledger + prune",        "kind": "io",       "actor": "coordinator", "produces": ["audit-record"], "body": "step-4-render-the-audit-record"},
    {"id": "close-ledger-row",    "name": "Rotation: close the area's coverage-ledger row",   "kind": "gate",     "actor": "coordinator", "gate": "hard",               "body": "2i-the-feature-rotation"},
    {"id": "retro",               "name": "Retro: improve checklist/spec (if earned)",        "kind": "author",   "actor": "coordinator",                               "body": "step-5-retro"},
    {"id": "write-result",        "name": "Write the run's check-result file",                "kind": "io",       "actor": "coordinator", "produces": ["check-result"], "body": "step-4b-write-the-check-result-file"},
    {"id": "commit-report",       "name": "Commit record + report (run outcome)",           "kind": "io",       "actor": "coordinator", "produces": ["tracker-issue"], "body": "step-6-commit-report"}
  ]
}
```

---

## Context to load (in this order)

1. [`knowledge/audits/README.md`](../../../knowledge/audits/README.md) — the
   program convention: record format, lifecycle, division of labor.
2. The checklist spec for the type: `knowledge/specs/` →
   `{type}-audit-checklist.md` (e.g.
   [`ux-audit-checklist.md`](../../../knowledge/specs/ux-audit-checklist.md)). Its
   **`## Audit profile`** block supplies the
   `atom`/`enumerate`/`partition`/`lanes`/`worklist`/`verify`/`synthesize`/`fileAs` recipe that
   Step 2 executes. It is **required for every type** — there is no mode for it to select.
   **If the checklist doesn't exist** (first audit of this type): author it first —
   research current best practices for that audit type (parallel web-research
   sub-agents), structure it like the ux one (dimensions with IDs, per-item
   protocol, severity scale S1–S4, filing rules) **plus an `## Audit profile`** if it's a
   full-surface code-correctness type, register it in
   `knowledge/specs/README.md`, then proceed. **The shared `docs` type is the one
   exception:** its checklist is the repository's *declaration* of the type, so a missing
   one is the named refusal (§2g-docs), never a checklist this run authors.
3. The scope's **single rolling record** in the record home (`slot:audit-profile`, one directory per type) (the
   latest run — there is exactly one record per scope) — two jobs:
   - **Re-verification list**: every finding whose tracker issue is now
     closed/Done gets re-tested this run; record each verdict in **this** run's
     *previous-run validation* section (Step 4). Do **not** back-annotate the old
     record — it gets deleted this run.
   - **Next-run seed**: its "not audited" rows + environment fixes are your
     default scope when no narrower scope was given.
4. [`../../process/issue-shape.md`](../../process/issue-shape.md)
   — filing contract (the *:create skills load it too, but you file many
   issues; know it up front).

Do **not** load implementation contracts — you are not changing product code.

---

## Step 0 — Resolve the invocation (type+scope, or a tracker issue key)

`$ARGUMENTS` is one of two forms:

- **`<type> [scope]`** — a human or script naming the audit directly. Use as-is, with **one
  resolution rule**: `feature` with **no scope** is the rotation (§2i) — resolve the scope to
  the single due area from
  [`feature-coverage-ledger.md`](../../../knowledge/audits/feature-coverage-ledger.md), and
  exit reporting "nothing due" if none is. `feature <area>` is a scoped run: it ignores the
  ledger's *selection* but still updates that area's row. **`feature family:<name>`** is a
  scoped run over a **group** of areas — the product grouping authored in that ledger's
  `Family` column (`family:agents`, `family:connectors`, `family:governance`, …), so
  *"audit all agent-related areas"* is one invocation; it expands to the member areas, runs
  each as its own area unit, and updates each row. Resolve the membership with
  `python3 knowledge/scripts/audit.py areas` (it prints the family index) — **never** by guessing from
  a slug's spelling, because ~11 areas sit in two families and several agent-related areas
  are not named `agent-*`. **`feature all areas`** is the whole-catalog pass — the form the
  `product` umbrella runs (§2d), and the only one that can produce the cross-area roll-ups;
  it is never the rotation.
- **A tracker issue key** (`<KEY>`, the daemon-routed `Type:audit` path) — fetch the
  issue (`get_issue`) and derive the **audit type** + **scope**
  from it. Two issue shapes route here, resolved the **same** way — **the body's explicit
  `/zetify:audit <type> [scope]` line is authoritative** for type+scope; the title is a
  human label, not the parse target:
  - **Post-ship PRD audit** (filed by the PRD lifecycle): title
    `Audit: PRD NNNN — <feature> [<type>, <type>, …]`; body is a self-contained brief
    carrying **one `/zetify:audit <type> <scope>` line per type**, the linked PRD, and
    (for ux/ui) the journey / `ux-design.md` for fidelity comparison. Older issues from
    before ENG-3439 use the single-type title `Audit (<type>): PRD NNNN — <feature>
    [<scope>]`; they resolve the same way — one line, one pass.
  - **Recurring scheduled audit** (the standing cadence — see
    [`knowledge/audits/README.md`](../../../knowledge/audits/README.md) → *Recurring
    scheduled audits*): title `Daily/Weekly/Bi-weekly <Type> audit`; body is the thin
    trigger carrying only the `/zetify:audit <type> [scope]` line (no `[scope]` → the
    type's default surface, e.g. the full web app for `ux`/`ui`).

  Set `<type>`/`<scope>` from the `/zetify:audit` line(s), and **keep the issue id** —
  Step 6 ends the run successfully. If the key resolves to a non-`Type:audit` issue, or the body
  names no audit type/scope, **stop and report** — never guess a scope.

  **More than one `/zetify:audit` line → a sequenced multi-type pass (§2e).** Take the
  lines **in the order written** (the filer orders them highest-harm first) and run each
  as its own complete audit. Do not merge them into one pass, and do not re-derive the
  order.

  **The post-ship ground guard (the Post-ship PRD audit shape) — prove the ground is on
  `main` before driving it.** A post-ship PRD audit is defined against the *shipped* product,
  so its preconditions are proven here, in Step 0, before Step 1 — never assumed from the
  filing. Resolve `PRD NNNN` from the issue title/body, then assert **both**:

  1. **The PRD has reached the post-ship gate.** Read the PRD's frontmatter `status:` — the
     same field §2c-live reads ship-state from — and require `verified` or `shipped`. A
     `draft`, `planned`, `implementing`, `blocked` or otherwise pre-ship PRD is not auditable
     ground yet.
  2. **Its named ground exists on `origin/main`.** After `git fetch origin main`, assert every
     scope path the brief's `/zetify:audit` scopes name — and the PRD's own
     `source_of_truth:` paths — exists at `origin/main` (`git cat-file -e origin/main:<path>`).
     A `verified` PRD whose shipping PR is still open passes (1) and fails (2); that is the
     exact case this guard exists for.

  If **either** assertion fails, the audit **does not run**: `comment` on the audit issue
  naming the PRD, its actual `status:`, and each path absent from `origin/main`; `relate` the
  audit issue `blocked-by` the PRD's tracker issue so the PRD's ship releases it; and **end
  the run** with no record, no findings filing and no completion manifest — a park, never a
  completed audit. Never substitute the shipping PR's branch for `main` to make the ground
  appear: auditing an unmerged branch audits a world no customer has, which is the defect this
  guard closes (ENG-19157: PR #18458 open, PRD 0906 `status: planned`, its `internal/skilllib/`
  and `internal/server/workspace_skills.go` absent from `main`).

---

## Step 1 — Environment prep (only when the partition holds a live unit)

Runs **after** §2b assigns concurrency classes — a partition with no `exclusive:live` unit
(`architecture`/`api`/`security`/`authz` are static source reads) never brings up the stack.
Pre-guessing that from the type is the mode selector this command removed.

**Resolve the TARGET first — which environment this run drives.** The default is `dev`: this
checkout's local stack, reached the way `slot:dev-environment` says, and everything below
reads as written. A run MAY instead name a **standing** environment — one of the ones
`slot:operations` enumerates — and then every `slot:dev-environment` reference in this step
(bring-up, readiness, login, log sink) resolves through `slot:operations` instead: its reach,
its identity, its logs, its build. Naming a target is not a mode switch; it is the same run
against a different world, and the distinction is load-bearing:

- A **local** target is one this run may alter — it pulls, rebuilds, restarts and reseeds at
  will. That is exactly what makes §2h step 4's freshness assertion meaningful: *"a process
  started after the pull"*.
- A **standing** target is one this run may **not** alter. It cannot pull, restart or reseed,
  and a verdict written against a build it cannot name is wrong in both directions (ENG-1081).
  So on a standing target the freshness assertion reads **the deployed build, not a local
  process** — and where `slot:operations` cannot report that build, a re-verification verdict
  cannot honestly be written at all. Record that as a coverage gap; never assert a freshness
  the run cannot observe.
- A standing target carries its own safety bound, which `slot:operations` names (here: an
  allowlist plus an `e2e-`-marker check, refusing mutations by default). A read-mostly run
  stays read-mostly, and **never widen a bound to make a journey reachable** — a journey
  bought that way reports on a world that is not the one under audit.

Verify the live stack before opening anything:

```
# Ports are per-checkout — read them the way <slot:dev-environment> says, never a default.
# Probe ONLY the readiness route <slot:dev-environment> names: a health-looking path
# the API does not register answers 200 with the app shell on a dead API, or a JSON 404 on a healthy one.
curl -s -o /dev/null -w '%{http_code}' "<slot:dev-environment>"
```

- Not running → **in an unattended / daemon-driven session (no real TTY)** — the normal way
  this command runs — use `{{target:dev-headless}}`: identical stack/seeding, with
  no dashboard trying to attach to a terminal that is not there. Confirmed 2026-07-15
  (ENG-1610): the interactive form fails outright in this context. *(Local target only: a
  standing target is never brought up by the run — it is already running, and
  `slot:operations` says how to tell that it is up.)*
- **Sign in for real** the way `slot:dev-environment` says — where auth is always-on,
  route-mocking the session endpoint bounces to sign-in. On a standing target that is
  `slot:operations`'s declared identity for it, and the run must not substitute a local one
  (a dev principal sent to a standing environment is a 401 at best).
- Keep the API log sink `slot:dev-environment` names at hand: every 5xx seen in the
  browser gets its server-side cause pulled from there into the finding (grep around the
  timestamp).
- Browser: Playwright MCP, desktop viewport **1440×900**
  (`browser_resize` first). Know the dev-org data state (which connectors
  have real data) so you can tell *data absence* from *broken surface*.

For `api` audits the same stack applies, driven via `curl` against
`api/openapi.yaml` instead of the browser. For `security` audits also load
[`knowledge/specs/permissions.md`](../../../knowledge/specs/permissions.md) and `slot:security`
(transport, authentication, trust boundaries, secrets).

## Step 2 — Execute the audit

**Diff-aware weighting (especially scheduled/nightly runs).** Before the full sweep,
compute what changed since the last record of this type — `git log` / `git diff`
since the prior the record home (`slot:audit-profile`, one directory per type) record, over the checklist's
source-of-truth paths. Run the **full** audit every time, but spend **extra** time on
the changed surfaces — regressions cluster where code just moved. Note the diff range
in the record's `environment` line.

### 2a — The run ledger (open it before anything else)

**The coordinator's memory is not the run's memory.** A long run, and every autonomous run,
will be compacted; a killed session, a dead sub-agent, or a rolled context window must not lose
which units were driven, what was filed, or what is awaiting a fleet fix. The coordinator keeps
a **durable ledger on disk** and treats its own context as a cache of that file.

**The ledger is NOT the record.** It lives at:

```
.claude/run/audit/{run-id}.md          # gitignored; run-id = {type}-{scope-slug}-{started}
```

Step 4 **renders** the deliverable record from it. Do **not** create the record early: two
records for one `(type, scope)` on disk simultaneously hard-fails `{{target:validate-knowledge}}`'s hygiene rule
(`pass_filenames: false, always_run: true`), which blocks **every** commit in the checkout —
including other agents' — for as long as the run lasts.

**Adopt, never supersede.** On entry, before Step 0's prior-record logic: if a ledger exists for
this `(type, scope)` with `status: in-progress`, **adopt it** — do not treat it as a prior run,
do not prune it, do not re-drive its `done` units. Only a `complete`/`partial` *record* under
`knowledge/audits/` is a prior run. Without this, a daemon retry classifies its own
40-minute-old ledger as "the previous run", writes a fabricated previous-run-validation
section, and deletes it.

**Freeze the path at run start.** Post the run-id as a `comment` kind `note` (or echo it in the
first report line for a human-invoked run). Never re-derive it from a date pattern — a run that
crosses midnight otherwise forks its ledger, and the prune deletes day one.

The ledger carries frontmatter (`run_id`, `type`, `scope`, `started`, `status: in-progress`,
`head_sha`) plus these tables.

**Unit table** — written at partition time:

| unit | class | needs | status | batch/run-id | matrix file | findings |
|---|---|---|---|---|---|---|
| `ux-enduser-1` | `exclusive:live` | `setup` | `done` | — | `units/ux-enduser-1.md` | F3, F4 |
| `api-ops-2` | `parallel` | — | `in-flight` | `wf_abc123` | — | — |

`status` ∈ `pending` · `in-flight` · `done` · `failed(reason)`. **Write `in-flight` before
dispatching and the terminal value after returning.** A row still `in-flight` on resume means
the dispatch died — information you cannot reconstruct from a compacted transcript. For parallel
units the engine's `resumeFromRunId` goes in `batch/run-id` as soon as the Workflow surfaces it:
present → resume; absent → re-dispatch.

**`matrix file` is the payload, not the count.** When a unit is recorded `done`, its **full
matrix** (one row per AC / route / atom) is written under `.claude/run/audit/{run-id}/units/`
and referenced here. Storing only a row count means compaction destroys the exhaustiveness
proof, and Step 4 then writes a matrix it cannot substantiate — the exact defect this design
exists to prevent. (Engine finders return `reviewedCount`, not a matrix — `REVIEW_SCHEMA` is
`additionalProperties: false` — so for parallel units the file holds the returned findings +
reviewed count; only live units produce true AC matrices.)

**Findings table:**

| id | sev | predicate | unit | summary | filed | state | verified at |
|---|---|---|---|---|---|---|---|

`state` ∈ `open` · `mechanical` · `fixed(PR)` · `filed` · `fleet-fixed` · `verified-pass` ·
`verified-fail` · `regressed` · `dropped(reason)` · `intermittent` · `sub-floor`. Two
transitions must exist or work is silently lost: **`verified-fail → filed`** (else a re-filed
issue is never re-polled and the fleet's fix is discarded), and **`dropped(reason)`** for an
issue closed Canceled/Duplicate/won't-fix. `verified at` holds the `origin/main` HEAD SHA **and**
the fresh-binary assertion (§2h step 4) the re-drive ran against.

**Cycle log** — one row per autonomous cycle: `cycle | HEAD SHA | units driven | new | filed |
re-verified | sub-floor | outcome`, where outcome ∈ `productive` · `waiting` · `idle` · `dry`.

**Area coverage ledger** — present only when `scope` is the full surface or `type: product`.
This is the cross-cycle memory a campaign needs: one cycle does **not** drive all of the feature
catalog's areas, so coverage rolls.

| area | state | last covered | by cycle | intent graded? | open findings |
|---|---|---|---|---|---|
| `access-profiles` | `covered` | 2026-07-31 | 4 | yes | — |
| `contextual-companion` | `in-progress` | — | 7 | no | F11 |

`state` ∈ `not-started` · `in-progress` · `covered`. **An area is `covered` only when its
capabilities were exercised live and its `source_of_truth:` swept** — never because it was
glanced at. `intent graded?` records whether each clause of the area's `> **Intent.**` was
judged against the shipped product, not merely whether its ACs passed; that is
[`feature-audit-checklist.md`](../../../knowledge/specs/feature-audit-checklist.md) §F1's bar
and it is a campaign's real completion condition. Diff-weight the next cycle's pick by
`git log` over each area's `source_of_truth:` paths.

**The anti-compaction contract:**

1. **Write before you act, write after you learn** — every state transition hits the file at the
   moment it happens, not batched, not at the end of a batch.
2. **Re-read the ledger's tables at the top of every cycle and immediately after any compaction
   or resume.** Never answer "what's left?" from memory. Read the tables, not the unit matrices.
3. **Mirror the unit table into the todo list** (`TaskCreate`/`TaskUpdate`, one task per unit and
   per finding awaiting re-verification, `blockedBy` wired to the `needs` edges). The todo list
   is the human-visible progress view; **the file is authoritative.** On disagreement, rebuild
   the todos from the file.
4. **Never delete a row.** Bound growth instead: matrices live in side files, and the cycle log
   keeps the last 5 rows plus aggregate counters.
5. **The ledger is coordinator-owned and coordinator-write-only.** Sub-agents return results;
   they never touch it. Under worktree isolation a sub-agent writing "the ledger" would create K
   divergent copies at the same relative path, all destroyed at teardown.

### 2b — Enumerate and partition

1. **Enumerate** per the profile's `enumerate` recipe — the atom set **and its exact count**
   (the exhaustiveness backbone) — `slot:audit-profile` names the recipe per type
   (the package list for architecture, the API contract's operation ids for api, the §0 reach
   inventory for the access types, the journeys index for ux, the feature catalog for feature, the
   router's `<Route>` declarations (ui). Write the atom→unit map to a `detailFile` under the
   ledger dir when it is large, and put that path in the unit — the finder reads it.
2. **Partition** per the profile — balanced units. ~15–30 atoms for static work; for live work
   **~5–10, clustered so a unit shares one auth context and seed profile** (persona clusters
   for `ux`, area clusters for `ui`), since a live unit is bounded by what one sub-agent can
   drive in one context. A god-atom over the size threshold drops to sub-units. Give each unit
   a **precise `scope` string** (the exact packages / operations / journeys / routes / sites) —
   the sub-agent reads only that.
3. **Assign each unit a concurrency class.** This is the property the old mode selector was
   really encoding:
   - `parallel` — static source reads, no shared mutable resource. Fan freely.
   - `exclusive:live` — needs the one browser over the one seeded dev org. **Never run two at
     once.** Two live sub-agents share an auth session, a navigation state, and — worst — a
     mutable org: each one's create/archive corrupts the other's ledger.
   - **Escalation (opt-in, expensive):** `exclusive:live` units become `parallel` only when each
     sub-agent gets `isolation: "worktree"` **and** its own stack is actually brought up inside
     that checkout (`{{target:dev-headless}}` + `demoseed dev-extras`, verified against that
     worktree's `.env.checkout`). A worktree alone brings no ports, no PG schema and no seeded
     org — without the bring-up, K agents point at the coordinator's stack and corrupt one
     shared org while the ledger records them as parallel-safe. Log the choice in the cycle row.
4. **Declare dependency edges (`needs`)** and topologically sort on them — never hand-order
   units in prose. Real edges: a **fixture unit** that creates the objects later units drive is
   a hard predecessor of every consumer; on a whole-product run `feature` precedes `ux`/`ui`
   (its stranded-backend map tells them which surfaces are real); under `phase: critical-first`
   `security` precedes everything, so a run that dies partway has still covered the
   highest-harm class. **This sort governs units within a run only** — §2e's filer-supplied
   line order is taken literally and never re-derived.

Only after this does **Step 1's env-prep** run, and only if the partition contains at least one
`exclusive:live` unit. A pure static run (`architecture`/`api`/`security`/`authz`) never brings
up the stack; pre-guessing that from the type is the mode selector this model removes.

### 2c — Dispatch

The coordinator dispatches, awaits, records. It does not audit.

**Parallel units — one engine call, all of them.** Splitting the parallel set into sequential
batches throws away the lane's justification *and* breaks cross-unit synthesis (the engine
synthesizes within one call, so N calls yield N partial syntheses and no global view). Pass
every parallel unit at once, with the full contract — **every argument is load-bearing**, since
omitting `fileAs` defaults it to `guardrail-first` (demanding a guardrail on every cosmetic
finding), omitting `fingerprint` defaults it to `true` (adding a required field to every
finder's schema), and omitting `rubricExtra` audits `api` with no design guide and `security`
with no `permissions.md`:
   ```
   Workflow({ name: '<slot:audit-profile>', args: {
     auditType: '<type>', repo: '<abs repo root>',
     checklist: '<abs path to {type}-audit-checklist.md>',
     rubricExtra: ['<abs paths the profile cites, e.g. server-boundary.md>'],
     dimensions: ['<the checklist dimension IDs>'],
     severityScale: '<the checklist S1–S4 one-liner>',
     units: [ { name, kind, scope, detailFile? }, ... ],   // your partition
     fingerprint: <true for dup-heavy types (architecture/api), else false>,
     synthesize: '<the profile synthesize line>',
     fileAs: '<the profile fileAs: guardrail-first | file-all>'
   }})
   ```
   Returns `{ unitsReviewed, expectedUnits, totalFindings, totalRefuted,
   perUnit:[{unit,reviewed,fingerprint,effective,refuted}],
   synthesis:{crossUnit, conventionDivergences, topFindings} }`.

**Record every returned unit into the ledger** before doing anything else. If the engine dies
mid-run, resume it (`Workflow({name:'<slot:audit-profile>', resumeFromRunId})` — the id is in the unit
rows) — completed finders replay from cache; don't restart from scratch. Carry
`perUnit[].effective` + `synthesis` into §2g (synthesis), §3 (filing) and Step 4 (record); the
record's synthesis table + guardrail-first issue map are the deliverables — see
`knowledge/audits/architecture/2026-09-05-whole-codebase.md` as the worked example.

**Then mint the live worklist.** The parallel lane's output is what *selects* what deserves a
live drive, per the profile's `worklist` rule (`ux` = shipped ∩ reachable ∩ diff-weighted
journeys; `ui` = every route, diff-weighted for depth; `feature` = the graph-flagged features).
**Only now** are `exclusive:live` units created and appended to the unit table. This is what
shrinks the whole journey catalog to a runnable live pass; minting live units at partition time, before any
static finding exists, drives everything or guesses.

### 2c-live — Live dispatch (one sub-agent at a time)

Dispatch each `exclusive:live` unit with the `Agent` tool (it reaches Playwright via
ToolSearch), **awaiting each before the next**. Give it its unit's precise scope, the
checklist's live dimensions **by name** — `ux`: §2a AC matrix + §4 console/network sweep;
`ui`: §1 `V*`/`Q*` + §1b information-design pass + §2 breakpoints + §3 axe + §4 dark-mode — and
the discipline below. It returns a **compact matrix (one row per AC / route) + findings + a
screenshot manifest**, which the coordinator writes to that unit's matrix file *before* the
next dispatch. Its context is then discarded; the coordinator keeps only the ledger.

**AC-exhaustive (the anti-skip contract).** For a journey unit, open its file and treat its
`## Acceptance criteria` block (for a map, **every sub-journey ID in §4**) as the test list.
Emit a verdict for **every** one: `PASS / FAIL / BLOCKED(why) / N/A(why)`, each with in-product
evidence. Walking fewer rows than the journey lists, or "spot-checked", is an audit defect. An
AC you can't reach is `BLOCKED`/`N/A` **with the reason** — never omitted. Read ship-state from
the AC's **owning PRD frontmatter `status:`** (a `planned`/`draft` PRD → `N/A(not shipped)`);
its `[dev]`/`[ext]` disposition tells you only whether it's locally verifiable or needs an
external dep, **not** whether it's built. The **job-map lens** (checklist §2b) runs alongside to
**discover** defects/ACs the list misses; each new one becomes a catalog AC (Step 5) + a
finding. If the journey has no AC list, that's finding #1 and you add the list.

**The verification rule — you are a customer using the product.** A defect is confirmed only by
reproducing it in the running product as a user would hit it (click the button, submit the form,
read the answer, watch the state). A fix is confirmed only by driving the fixed flow live and
seeing it work. **"PASS at source", "the diff looks right", "the test was added", a `Done`
issue, or a green CI run is NOT a PASS.** Source and DB reads are a *supporting aid only* — to
locate a root cause, explain the mechanism behind a live symptom, or ground a ticket with
`file:line` — and they happen **after** the behaviour was seen live, never instead of seeing it.
A sub-agent is usually right about the *symptom* and often wrong about the *root*: use source to
correct the mechanism, never to establish the symptom. Every candidate a static sweep produces
is still **confirmed live** before it is a finding. Distinguish a real symptom from a **stale
binary**, **stale data**, or a **test artifact** by re-driving on a confirmed-fresh binary
(§2h step 4).

Non-negotiable discipline, learned the hard way:

- **Screenshot at observation time, not later.** Evidence vanishes (a reload
  destroyed a 22k-token conversation once). `browser_take_screenshot` with a
  meaningful filename — files land in the **repo root**; you will delete them
  after uploading to the tracker (they are not gitignored).
- **After every page/action**: sweep `browser_console_messages` (level error)
  and `browser_network_requests` filtered to `/api/`. Any 4xx/5xx, React
  warning, or hydration error is a finding. A calm UI over a failing API is a
  **silent failure** — raise severity.
- **Cross-surface data probes**: the same number shown on two surfaces must
  agree (badge vs list count, quota-used vs analytics, tab badge vs row
  count). These probes found the best bugs.
- **A computed-style sweep must enumerate every property that can carry the value** —
  `backgroundImage` (gradients), `borderColor`, `outlineColor`, `boxShadow`, `fill` and `stroke`
  (SVG), not just `color`/`backgroundColor`. A sweep narrower than the property set produces a
  **false absolute**, and an absolute is the one claim a verifier can refute with a single
  counter-example, which discards the true finding underneath it. The 2026-08-15 `branding` run
  reported "the accent paints **0 of 1046** elements"; the refuter found **25** — every one a
  gradient — and the real defect (the accent reaches no *primary action*, a regression against a
  shipped PRD's ACs) nearly died with the overclaim. **Prefer the bounded claim you measured**
  ("no primary action, link or focus ring") over the sweeping one you inferred.
- **Exercise, don't just look**: submit forms empty (validation), complete
  wizards end-to-end (create then archive/unassign to restore state), confirm
  destructive dialogs on reversible test objects, reload after mutations
  (persistence), probe bogus IDs (error states), Escape on modals.
- **Mutations stay reversible**: create → verify → archive/delete your test
  objects; never leave audit clutter in the dev org.
- **Report a finding only on 2-of-3 reproductions across separate sub-agent
  contexts.** One re-drive cannot distinguish a defect from a race. A
  non-reproducing observation is recorded `intermittent` in the ledger and never
  filed — an intermittent surface otherwise produces file → can't-reproduce →
  re-file forever, burning a fleet slot each lap.
- **Known-issue check**: search the tracker (and the product's own bug-report surface, where it has one) for an existing
  issue and report the match with your evidence. **The coordinator files** (§3c) —
  a sub-agent never opens or comments on an issue itself.
- **Don't fix mid-sweep — observe first, fix in Step 3.** Note every finding as
  you go; the triage in Step 3 decides whether it becomes a batched mechanical-fix
  PR (§3b) or a consolidated tracker issue (§3c). Fixing while you sweep loses
  evidence and tangles the coverage ledger.
- **(ui/ux) Coverage is a ledger, not a sample.** Reconcile the surface catalog
  against the router (the app's `<Route>` declarations) before sweeping; render
  **every** route or defer it *with a reason* in the coverage matrix — a route
  silently missing from the matrix is itself a finding. A detail route is a
  distinct surface from its list (render it with a real seeded id). Beyond token
  conformance, run the **information-design / page-quality pass** on each
  rendered surface (the UI checklist's information-design questions + the holistic "would a
  designer ship this?" look): grep finds drift atoms, only eyes find a page that
  reads as unfinished.

**Critical-first phase** (see the Step 3 triage intro): instruct each live sub-agent to run the
correctness / behavioral / silent-failure / access dimensions **exhaustively** (`ux` §2a AC
matrix + §4 console/network sweep; `ui` `V*` broken/access checks + §3 axe) but the **cosmetic**
dimensions (`ui` §1 typography/token depth, §4 dark-mode polish; `ux` §4 visual nits) as a
**light spot-check** — a few representative surfaces, not route-by-route — and to spend the
saved budget on the invariant-sweep classes (silent-error-on-fetch, fail-open-on-error,
stale-after-mutation). Cosmetic drift it does surface still feeds the §3b mechanical batch; it
just isn't hunted exhaustively.

**Coverage reconcile (hard gate).** Gate on **`done == expected`** — *not* "done or failed". A
labelled failure must never satisfy the exhaustiveness backbone. Re-dispatch a `failed` unit; if
it genuinely cannot be driven, record an explicit coverage-gap **finding** and set the ledger
`status: partial`. **Reject any engine unit returning `reviewed: 0` as `failed(no-atoms-read)`**
— a null-returning finder still counts toward `unitsReviewed === expectedUnits`, so a 20-unit
run with 3 timeouts otherwise claims full coverage of atoms nobody read. A worklisted item with
no matrix row is itself a coverage gap. The "0 findings **and** 0 refuted ⇒ the finders
under-scoped" heuristic applies only to runs with at least one `parallel` unit.

### 2d — Product mode (the whole-product umbrella)

`/zetify:audit product` (or a daemon-routed `<KEY>` whose body names it) runs the
**entire-product** audit. It has **no checklist of its own** — it is a thin **orchestration**
over the three full-scope experiential passes, each of which loads its own checklist and
files its own findings per its own profile. Product mode adds only the ordering and the
top-level synthesis; it **files nothing itself**.

1. **Run the constituents at full scope, in this order** (each a normal
   `/zetify:audit <type>` run — parallel lane then live lane, §2b–§2c-live —
   writing its own rolling record and filing its own findings):
   0. **`security`** (full HTTP + MCP surface, vault, data-plane) — **critical-first phase only**
      (when `phase: critical-first`): run it **first**, so the umbrella leads with the highest-harm
      defect class. Omit it when `phase: exhaustive` (security keeps its own standing cadence).
   1. **`feature all areas`** (the whole catalog) — intent delivery + stranded-backend +
      coverage. First of the experiential passes, because its stranded-backend + coverage map
      tells the `ux`/`ui` passes which surfaces are real vs. stranded. **The scope keyword is
      required here**: a bare `/zetify:audit feature` is the rotation (§2i) and would drive a
      single area, silently reducing the umbrella to one area's worth of its scope.
   2. **`ux`** (full app) — journey AC-conformance + IA + silent-failure.
   3. **`ui`** (full app) — visual conformance + information design.
   Each `audit-engine` invocation is independently resumable if it dies; product mode is the
   coordinator that sequences them.
2. **Product-health synthesis (the umbrella deliverable).** Read the three records' synthesis
   sections + findings registries + coverage/AC matrices (do **not** re-open the product — the
   constituents already drove it) and produce, as a synthesis sub-agent or an inline pass:
   - **Stranded-backend roll-up** — every `feature` F3 hit across all areas (the golden-rule
     headline: shipped code, no customer surface).
   - **Journey-coverage map** — the `ux` AC matrices aggregated: which journeys pass
     end-to-end, which fail, which are unshipped/blocked.
   - **Cross-cutting themes** — a defect class that appears in **more than one** constituent
     (e.g. a silent-failure pattern that is also an information-design and a coverage gap),
     ranked by reach × severity. These are the findings no single-type audit could see.
   - **Product-health scorecard** — per-area (feature) · per-journey (ux) · per-route (ui)
     PASS-rate, so the whole product's state reads on one page.
3. **Record.** One rolling **product** record under `knowledge/audits/` in a new `product/`
   folder (created on first run, per the audits README convention), superseding the prior. It
   **links** the three constituent records (never duplicates them) + the umbrella synthesis:

   ```
   <record home>/product/{YYYY-MM-DD}-full.md
   ```
4. **Filing.** Product mode files **no findings** — its constituents already filed theirs
   guardrail-first / by-theme. Its only optional filing is **one** umbrella tracking issue
   when a cross-cutting theme has no owner across the three; default is none. The deliverable
   is the synthesis record + the in-conversation product-health report (Step 6).

### 2e — Sequenced multi-type pass (the post-ship PRD audit)

A single `Type:audit` issue whose body carries **several** `/zetify:audit <type> <scope>`
lines (the post-ship PRD form — see
[`knowledge/audits/README.md`](../../../knowledge/audits/README.md) → *Post-ship audit
follow-ups*) is **N complete audits under one work order**, not one blended audit. Like
product mode (§2d) this is pure orchestration — it adds ordering, and nothing else.

1. **Run each line in the order written**, as a normal `/zetify:audit <type> <scope>` run:
   its own checklist, its own ledger (§2a), its own §3 triage and filing floors,
   its own **record in the record home for its type** (Step 4, unchanged). The filer orders
   them highest-harm first (`security` → `authz` → `api` → `ux` → `ui`), so a run that dies
   partway has still covered the classes that can hurt a customer.
2. **Never blend the types.** No shared findings registry, no merged record, no
   "cross-type synthesis" — those are product mode's job at full scope, not this one's.
   Each type's checklist retro (Step 5) keys off that type's own record; collapsing the
   records breaks the loop that improves the checklists.
3. **Do reuse context across the lines, and say so.** All lines share one PRD, one diff,
   and one live stack. Bring up the environment once (Step 1) and cite an earlier line's
   record instead of re-deriving ground it already covered — exactly as the sibling
   per-type audits already do when they cross-reference each other. Note the reuse in the
   record's `environment:` so a reader can tell reuse from a skipped check.
4. **Completion is all-or-nothing.** Step 6 ends successfully only when **every** line has
   run and written its record. If one type cannot run (its lane is unavailable, its scope
   no longer exists), finish the others, leave the issue open, and report which line is
   outstanding and why — never silently drop a type, and never mark the run successful on a partial pass.

### 2f — Verify

- **Static S1/S2** — adversarially refuted inside the engine against the cited source (a "dead
  surface" claim disproved by finding the live `<Route>`). `totalRefuted > 0` is healthy: it
  means the pass earned its keep.
- **`totalRefuted == 0` on a pass of any size is a verify FAILURE, not a clean bill of health** —
  treat it exactly like §2c-live's `reviewed: 0` coverage gate. A verifier that confirms
  everything is not verifying; it is a rubber stamp costing a sub-agent per finding and
  returning no signal, and it lets the finder's own severity call through unchallenged. The
  2026-08-10 architecture sweep refuted **0 of 413** and recorded it as a strength ("none thrown
  out"); manual re-reading of one bundle then found a finding whose premise was simply false (a
  "magic number" that was already a named constant) plus five whose severity was wrong by two
  levels. Both classes are exactly what a refuter is for. On a zero-refutation pass: **re-run
  verify with the refute-by-default framing** (each verifier is asked to disprove the finding and
  defaults to `refuted: true` when the cited source does not support it), and record the
  before/after counts in the ledger. **Severity adjustment is not refutation** — count them
  separately; a pass that only ever adjusts severity downward has the same defect.
- **Live S1/S2** — re-observed by the finding sub-agent before it returns (re-drive the surface;
  cross-check `logs/api.log` for any silent-failure claim). A finding that will not reproduce is
  dropped.
- **Re-verification of an already-*fixed* finding (§2h) always uses a fresh sub-agent, never the
  one that found it.** ("Never the finder" scopes to §2h only — inline live self-verification
  above is by design.)
- **Perspective-diverse verify** where a finding can fail more than one way: give each verifier a
  distinct lens (correctness · security · does-it-reproduce) rather than N identical refuters.

### 2g-docs — The `docs` type and the docs lane (only when `slot:docs` is filled)

The user-facing documentation is a catalogue like the feature maps, and it drifts the same way: a
release renames a button and a page keeps naming the old one. `docs` is the shared audit type that
finds this — the type is **declared by the repository**, not by this command: it lists `docs` in
its `slot:audit-profile` `types` answer, names its checklist (`{type}-audit-checklist.md`, the
pattern that slot's `checklists` answer gives), and fills `slot:docs` with one or more homes (each
with audience, visibility and page tree) plus the page contract and build/verify recipe. The
checklist's `## Audit profile` supplies the per-run recipe; this section is the shared half every
repository's docs checklist inherits, and it doubles as the **docs lane** a non-`docs` checklist
can name.

**Enumerate.** Per `slot:audit-profile`'s `enumerate` answer the atom set is two-sided: the
feature-map **capabilities** a docs section covers, and the **pages** of the docs homes. Read each
page's contract keys — `covers` (the capability ids the page is for), `verified_by` (the journey
whose how-to is the page's test) and `source_of_truth` (the code paths it describes) — and read
each map's optional `Documented in` cell and a journey's `documented_in:` key as **linkages only,
never ship-state**. Coverage is the docs validator's **computed** report, never a second
implementation: a capability whose area declares a surface which no page, `Documented in` cell or
`docs_impact` names is a coverage finding; a page no capability and no other page links is an
orphan. Write the atom→unit map to a `detailFile` under the ledger dir and put its path in the
unit — the finder reads it.

**Partition by feature area.** One **unit** per feature area (the docs section that area's
capabilities belong to), not one per page: the unit is what one fresh sub-agent can follow end to
end in one browser context. The units are `exclusive:live` — each follows how-tos in the real
seed-checkout product — so they run **one at a time** (§2c-live), each with one auth context. A
section too large for one context drops to sub-units, and a first run may narrow the scope to one
section (the setup section is the common first run). The type is **not** `--autonomous` by
default.

**Per unit, five dimensions.** Each page gets a verdict `PASS / FAIL / BLOCKED(why) / N/A(why)`,
never omitted, and each finding names the page and the step:

- **Coverage** — every capability the section must cover has a page **of the right kind**, and
  every page covers a real capability; a missing page and an orphan page are both findings.
- **Truth against the screen** — follow each how-to **literally, in the real product**, by
  **running the journey the page names in `verified_by`** on a seeded checkout; a step whose
  button, field, route or result does not exist or differs is a finding; a tutorial or how-to with
  no `verified_by` is itself a finding (explanation and reference pages are checked by the audit
  instead, per the rubric's kinds).
- **Truth against the code** — every command-line flag, address path, configuration key,
  permission and event the page names **exists in the source**; the checklist says how each kind
  is resolved, and an item that is absent is a finding.
- **Truth against commitments** — every statement of what the product restricts, keeps or audits
  cites a **requirement row** and that row still says it; prose that promises more than the
  register does is a finding against the page.
- **Freshness** — a code path a page lists in its `source_of_truth:` changed without the page
  being touched is drift (the same advisory `feature-doc-reconcile.md` Layer 4 raises).

Page-quality checks (one page is one kind, prerequisites stated, a success check on every how-to,
no dead ends) are the shared `rubric-docs`'s; the checklist points at it and adds none.

**Reports and never edits.** A stale page yields **one** finding, filed to the **`triage`**
and nowhere else. A missing page for a shipped capability is a defect in the **catalogue**; a page
that promises what the product does not do is a defect in the **page** — correct the page, never a
reason to build the feature. Findings triage through §3 as the type carve-out says: a wrong page is
`Type:bug` (reproduce-first, the page is the artifact), a missing page is `Type:bug`/`Type:task` as
§3a sorts it, and the docs home is named **through the slot**, never as a literal path. The audit
**changes no page**; a fix goes through `/zetify:task:implement`, so the party that found the gap
does not grade its repair.

**Record.** A docs run renders the one rolling record for its `(type, scope)` through Step 4 into
the record home `slot:audit-profile` names — one directory per type, so a `docs` record lands
under that home's `docs` directory (Step 4's `<record home>/{type}/{YYYY-MM-DD}-{scope}.md`) —
carrying per-page per-dimension verdicts, the release or build the run was against, the previous
run's validation and the next-run seed. It is rolling only when a cadence row schedules the scope
(Step 4 → *Retention*); a one-off section is consumed at write time.

**Degrade — the named refusal.** When the repository does not declare the type — `docs` absent
from `slot:audit-profile`'s `types`, no `docs` checklist, or `slot:docs` left unfilled — there is
no home, no page contract, no checklist and no verify recipe. `/zetify:audit docs` **refuses**,
printing the degradation `slot:docs` names (`…the docs audit cannot run.`) and writing it in one
line to the ledger; it never invents a path, never audits pages it cannot locate, and never reads
as a clean pass. A run of **another** type whose checklist names the docs lane hits the same
condition: skip the lane and record why, per the slot's own rule.

### 2g — Synthesize

Dispatch a synthesis sub-agent over the engine's returned `synthesis` **plus** the live
matrices — it synthesizes *across lanes* and never replaces the engine's own pass (which holds
the `fingerprint` conventions and `reusableBlocks` the ledger does not). It does **not** re-open
the product. Output: cross-unit clusters, convention divergences, silent-failure clusters,
IA/nav coherence at catalog scale, coverage holes, and — ranked by **reach × severity** — the
cross-cutting themes no single unit could see. On `scope = all areas` it also produces the
**stranded-backend roll-up** (shipped code, no customer surface — the golden-rule headline), the
**journey-coverage map**, and the **product-health scorecard** (per-area / per-journey /
per-route PASS rate). Fold its output into the ledger before triage.

### 2h — Autonomous mode (`--autonomous`)

**This is the only loop in the audit program.** The former `/zetify:product-audit` is deleted; <!-- tilion-refs:skip -->
its operating model is this section. A campaign is `/zetify:audit <type> --autonomous`, or
`/zetify:audit product --autonomous` for the whole-product form.

**The objective and the done-bar.** If the objective file `slot:audit-profile` names exists, read it
first: it carries a durable, human-set campaign goal and its definition-of-done, and that
done-bar **overrides the default termination** below. The standing bar: **"critical backlog
drained (S1/S2 + security)" ranks ABOVE "coverage complete"** — an area left `not-started` does
not block finishing once the filed critical set is drained, and a complete coverage ledger does
not finish the campaign while S1/S2 findings remain unverified. With no objective file, the
default bar is the two-dry-cycle rule.

**Each cycle is a capped re-verify prologue followed by discovery** — **(a) re-verify**: drain
up to **3** ripe findings from the `fleet-fixed` set, oldest-merged first; then **(b) coverage**:
pick the next `not-started`/`in-progress` area from the area ledger (diff-weighted) and drive it.
Leftover re-verifies roll to the next cycle.

**Discovery is never preempted; re-verification is bounded.** This used to read *"re-verify wins
when both are ripe"*, which was correct when this loop was the **only** adversarial check on a
fleet fix. It no longer is — [`/zetify:verify`](verify.md) now certifies every fix's cause ledger
before it merges (step 5) — and the old tie-break is how a campaign spends 69 ticks re-verifying
while its coverage ledger stays blank. If the cap binds for several cycles running, **say so in
the ledger** rather than silently truncating: a bound cap means fixes are landing faster than
they can be re-driven, which is a real signal, not a rounding error.

**Not dispatchable by issue key.** A fleet daemon session is killed at `session_timeout` (4h)
and that burns an attempt; three burns move the issue to the **`Failed`** state, terminal
until a human resets it. An endless run emits no completion sentinel, so it reaches
terminal failure in ~12h having held one of the fleet's slots throughout. `--autonomous`
**refuses to start** when invoked as `/zetify:audit <KEY>`; it is human-attended or
Routine-scheduled only.

**Isolation precondition.** The loop never mutates a tree it does not own. Abort unless
`HEAD == main` and the tree is clean, or run under `isolation: "worktree"` pinned to
`origin/main`. (A fleet workspace runs `git clean -fd` at the top of every poll — which is
also why the ledger lives under gitignored `.claude/run/` and survives it.)

**Live lock.** Acquire `.claude/run/audit/live.lock` (run-id + pid + acquired-at, with a
stale TTL) before any `exclusive:live` dispatch **and** before any stack restart. Exclusivity is
otherwise enforced only *within* a run, and a concurrent audit of another type will archive your
test objects and restart your stack mid-drive — manufacturing S1 findings in both records.

**File as you go.** Findings that clear the §3a′ gate are filed the moment they are verified,
so the fleet starts fixing while later units are still driving. Set the ledger row to `filed`
with its issue key in the same write.

Each cycle:

1. **Re-read the ledger tables.** Rebuild the todo list from them. Never proceed on memory.
2. **Gate the cycle on an event** — `git ls-remote origin main` (one network call, mutates
   nothing) shows a new SHA, **or** a filed issue changed state. Otherwise sleep and re-poll;
   don't pay for a pull + stack restart to learn nothing. Minimum 15 min, default 30 — anything
   tighter cannot observe a state change the fleet daemon (600s poll) hasn't produced yet.
3. **Checkout `main` first**, then `git pull --rebase origin main`. Without the checkout, cycle 2
   rebases cycle 1's already-merged fix branch onto a main containing it, fills the tree with
   conflict markers, and every live unit then reports fabricated S1s against a broken stack.
   Restart the stack. Re-seed when the diff touches storage or seed data — the way
   `{{target:reseed}}` says, which is **not** `{{target:seed}}` where the
   repo distinguishes them (ENG-1028: a seed-only fix otherwise reproduces the pre-fix symptom
   and files a false regression).
4. **Assert a fresh binary before any verdict is written**: the API process started after
   the pull **and** the readiness route `slot:dev-environment` names answers. A
   hot-reloader can orphan the port so **a stale binary
   keeps serving** (ENG-1081) — without this assertion the ledger's `verified at <SHA>` records
   the *tree's* SHA while the re-drive hit the *old binary*, and it is wrong in both directions
   (a correct fix re-opened; a missing fix certified).
   **On a standing target the assertion is the same in substance and different in source.**
   There is no pull and no process of ours to inspect, so the freshness it asserts is the
   *deployed* build, read the way `slot:operations` says. Where that answer cannot report a
   build, this step cannot run: re-verification is simply unavailable on that target, and the
   ledger records that rather than a `verified at <SHA>` nobody observed. "It is deployed by
   now" is not a freshness assertion — it is the shape of one.
5. **Re-verify — and know what the gate already did for you.** Since the gate-out landed,
   every fix for a finding you filed passed [`/zetify:verify`](verify.md) *before* it
   merged: its cause ledger was re-derived from the issue by a session that did not write
   it, and every test it named was neutered to prove it goes red without the fix. **So do
   not re-litigate claim closure here** — read the ✅ VERIFY comment and take its verdict.
   What that gate does **not** give you is a live drive at *your* audited surface: it
   drives one only when the diff touched a customer surface, and it drives the symptom the
   *issue* described, not the journey AC *you* were walking. That gap is this step's whole
   remaining job.
   One **fresh** sub-agent per `fleet-fixed` finding — never the one that found
   it — re-drives that exact surface as a customer → `verified-pass` / `verified-fail` /
   `regressed`, written with the SHA. A `verified-fail` files a **new issue `related` to the old
   — never a comment on, or a reopen of, a closed one**: the daemon reconstructs its retry budget
   from comment cost-markers, so a reopened issue arrives with attempts already burned. Cap at
   **2 verify failures → `Blocked · decision`**, mirroring the daemon's own `max_verify_failures`.
   **A `verified-fail` on a fix that carries a passing ✅ VERIFY is the single most valuable
   finding this loop produces** — it means the gate certified a ledger that was complete
   and the defect survived anyway, so the issue's *claims* were wrong, not the fix. Say
   that explicitly in the new issue: the next implementer must re-derive the root cause,
   not close the same lines again.
6. **Re-enumerate what is genuinely stale.** A diff touching a **shared** path
   (the shared roots `slot:file-conventions` names — a component library, the server
   core, the generated tree, the contracts) invalidates **all** units,
   not only the one whose scope names it. Otherwise a fix to one shared primitive is verified by
   one unit while a dozen others silently break and the cycle still reads dry.
7. **Dedup on a stable identity** — **`(atom id, checklist dimension id, symptom class)`**: what
   was tested and which check failed, from closed vocabularies (journey AC id / route /
   `operationId` / package; `V*`/`I*`/`G*`). Emit it verbatim into the tracker body as
   `audit-key: ux/end-user-home#AC-11/silent-error`, so dedup is a `search_issues`
   `include_closed` — which also catches issues the fleet filed itself under Rule G and
   would otherwise duplicate.
   **Fix-surface + root cause is the §3c *consolidation* key and must not be reused here**: it
   merges distinct defects by design, and it changes whenever a file moves, which is this loop's
   own core event.
8. **Classify the cycle honestly.** `productive` (new findings or state changes) · `waiting`
   (findings still `filed`/`fleet-fixed` — back off; **never counts toward termination**) ·
   `idle` (zero units driven — never counts) · `dry` (every finding terminal **and** no new
   findings **and** every unit driven at a SHA ≥ the last merge touching this scope).
9. **Admission control.** Do not open a new *discovery* cycle while open filed-and-unfixed
   findings exceed **5**. Re-verify cycles are always allowed — they drain. Without this the
   loop files faster than the fleet can fix and starves its own remediation.

**Termination:** a human stop; the objective's done-bar when an objective file is present; or
**two consecutive `dry` cycles**. Then finalize (Step 4) and report. A run stopped mid-cycle is
complete-as-of-the-ledger by construction — finalize from the file.

**Two hard rules, both learned the hard way:**

- **Never `git pull --rebase` while a browser sub-agent is driving.** It churns the working
  tree, air rebuilds, and the drive goes stale mid-flow — producing findings that describe a
  half-built binary. `git fetch` / `git ls-remote` are safe anytime; the pull happens only
  between dispatches, under the live lock.
- **Sub-agents must NOT kill processes.** Dev-stack recovery (`lsof -ti:<api-port> | xargs kill
  -9`, restart, re-assert freshness) is the coordinator's job alone. A sub-agent that kills a
  port takes down the stack the next unit is midway through driving.

### 2i — The feature rotation (`/zetify:audit feature`, no scope)

**The continuous feature audit is a rotation, not a campaign**: each run takes the **one area**
the [coverage ledger](../../../knowledge/audits/feature-coverage-ledger.md) says is due, drives
it, and closes its row. It is **not** `--autonomous` — it does not loop, it does not hold a
session open, and it terminates after one area. Continuity comes from the ledger plus whatever
fires the run, which is exactly why a killed or skipped run costs nothing: the next one re-reads
the ledger and picks up where the last left off.

**The same tier rule now covers every typed part, not only areas.** A feature area, a component,
a connector and a customer's own system each carry an authored `Tier` (`core` 3 days, `rotation`
14 days, `parked` never; blank = untiered), and `python3 knowledge/scripts/audit.py due` selects
every typed part whose tier is due, reports a part left unchecked with its reason, and names an
untiered part rather than dropping it. It reads the tier where the part is authored — the
coverage ledger's `Tier`/`Notes` cells for an area, the component registry's `tier` column, a
`tier:` on a connector manifest and on a fixture record — and declares no schedule of its own:
re-tier a part and its cadence self-corrects. This section owns the **area** tick; `due` is the
selector a person runs to see the whole rotation.

**Two documents own the parts this section does not restate.** Which area is due — tier,
max-age, the diff gate, the selection order — belongs to
[`feature-coverage-ledger.md`](../../../knowledge/audits/feature-coverage-ledger.md). How the
area is audited — the run's six steps, the Intent bar, the verdict vocabulary, the filing
timing — belongs to
[`feature-audit-checklist.md`](../../../knowledge/specs/feature-audit-checklist.md). This
section owns only the **shape of one tick**.

**A `family:<name>` scope is not the rotation.** `/zetify:audit feature family:agents` is a
**scoped** run over every area in that family — it ignores the ledger's *selection* (no tier,
no age, no diff gate) exactly as a single-area scope does, drives each member as its own area
unit in ledger order, and updates each member's row. It does not loop, and it does not become
`--autonomous` by being plural. Expand the membership with `python3 knowledge/scripts/audit.py areas`,
never from the slugs' spelling: the areas a person means by "agent related" span seven
architecture layers and half of them are not named `agent-*`.

**Locally triggered, by design.** The rotation is fired from a human's own machine, not by the
fleet daemon: it needs a live stack and a browser to reach `live` depth, and the
cadence is a judgment its owner adjusts by re-tiering — not a fleet slot. `--autonomous` remains
refused on the daemon-dispatched `/zetify:audit <KEY>` path for the reasons above.

**One tick, two phases:**

1. **Prologue — drain up to 3 ripe S1 re-drives** (§2h step 5's method, this section's cap),
   oldest-merged first, **for any area regardless of its tier**. Then:
2. **Body — drive the one due area.** Nothing due → **do nothing and exit**, reporting why. An
   audit taken out of turn is pure cost, and a run against a sick stack manufactures findings.

**"Ripe" is a property of the binary, not the board.** A re-drive is ripe when the fix has
merged **and the local stack's SHA is at or past that merge** — never merely because the issue
says Done. A verdict written against a stale binary is wrong in both directions (ENG-1081), so
the freshness assertion in §2h step 4 is a precondition of the prologue, not an optional check.

**The S1 worklist is a tracker query, not a file.** Findings this program files carry
`audit-key:` in the body (§2h step 7), so *"S1s whose fix merged since I last looked"* is a
search. The rotation adds **no** new state: the ledger stays coverage-only.

**Closing the area's coverage is a hard gate, not bookkeeping** — it rides the **same PR** as
the run record, and it is written as the run's **own file**, never as an edit to the shared
ledger table (concurrent audits would collide on it): `python3 knowledge/scripts/audit.py
coverage-write <area> --depth <live|partial|graph|skipped> --notes <residuals> --run-id <id>`
writes `knowledge/audits/coverage/<area>/<utc-timestamp>-<run-id>.json`. `Last audited`,
`Depth` and `Notes` are **derived** from those files (`audit.py coverage` prints the latest
per area; the newest file wins) — the ledger's run columns are no longer hand-appended. Never
`Tier`, which stays the human's. A run that files findings and
leaves the row untouched has erased itself from the coverage history: the next run re-selects the
same area, re-drives it, and re-finds what is already filed, while every other area ages. That is
the rotation's one single-point-of-failure, which is why it is a gate and not a step.

**The rotation is itself the re-verification of everything below S1.** A capability whose fix
did not work resurfaces as a `FAIL` the next time its area comes round — found by an independent
session, with no `fleet-fixed` set to maintain. The tier's max-age *is* that re-verification
latency, which is why re-tiering an area is a real decision and not bookkeeping. S1 is the one
class that does not wait for its area's turn, because three days is too long to leave a customer
blocked.

## Step 3 — Triage findings, then fix mechanical ones or file the rest

### 3a′ — The customer-harm gate (apply this first)

**A finding is filed only if the verifier can name one proving artifact.** Severity letters are
not portable across the checklists — `ux` S1 is falsifiable ("job cannot be completed; 5xx;
silent failure"), while `ui` S2 is "a **real misread**", `architecture` S2 is
"**high**-blast-radius duplication", and `security` S2 is "a hardening gap **with a mitigating
control present**". A floor expressed as a letter means a different thing in every type, which
is why `ui` had to bolt on "WCAG AA failures are floored at S2" — the wording alone would not
have carried a WCAG failure above polish.

| # | Predicate | The artifact that proves it |
|---|---|---|
| 1 | **Blocked task** — a customer following a documented journey AC cannot reach its stated outcome | the AC id + a `FAIL`/`BLOCKED` matrix row + a screenshot at the blocking step |
| 2 | **Wrong data** — a displayed value contradicts the system of record or another surface | two observations, each with the route/query that produced it |
| 3 | **Silent failure** — a success/neutral/empty state renders while the request failed | a captured 4xx/5xx or `logs/api.log` line, timestamped to the observed render |
| 4 | **Governance defect** — an actor saw, acted on, or was granted something their profile forbids, or a check failed open | the request + the identity + the permission that should have narrowed it |
| 5 | **Unrecoverable** — data lost/corrupted, or a state with no back, no retry, and no actionable error | the state + the absence of an exit affordance |

**Predicate 4 files at any severity and is exempt from the floor.** That preserves the existing
`security`/`authz`/`evidence` carve-out and `authz`'s "S1 regardless of exploitability" rule: a
narrowing defect with no user-visible symptom is still the worst bug in the product.

**Two anti-gaming clamps:**

1. **The evidence is the gate, not the adjective.** A justification containing *confusing ·
   inconsistent · unpolished · not obvious · should be · could be clearer · doesn’t feel* and
   **no artifact** is sub-floor by definition. That is greppable, so a verifier who is not the
   finder can enforce it mechanically.
2. **The predicate is assigned by the verify sub-agent, never the finder.** The finder reports
   observation + evidence; the verifier picks a predicate or rejects it. Severity self-assessed
   by the agent whose run is judged by what it found is unfalsifiable by construction — and
   §2h’s termination rule creates exactly that incentive.

**Sub-floor findings are not filed — but they are still fixed and still recorded.** File ≠
record ≠ fix:

1. **Mechanically fixable → fixed, not filed.** Straight into the §3b batch PR. Zero tickets,
   and the highest value-per-token thing the audit does.
2. **Not mechanical → one line in the record**, keyed by its `audit-key`, in the coverage
   matrix / next-run seed. Recorded, greppable, never a ticket.
3. **Recurring across ≥3 runs → promoted once** to a checklist dimension or a lint (Step 5) —
   never to N tickets. A sub-floor class that keeps reappearing is a *preventer* gap, and §3d’s
   rule is that a finding class ships a preventer.

**Publish the ratio.** Every run (and every autonomous cycle row) carries `sub-floor: N ·
filed: M`. `17/2` says the floor is working; `0/9` says it is being gamed upward; `40/0` across
three cycles says downward, to reach a dry cycle. An unobservable floor is not a floor.

### 3a — Triage by nature

Classify each finding (the intro defines both classes):

| Class | Test | Action |
|---|---|---|
| **Mechanical drift** | one known-pattern transform toward a canonical target; no new copy/keys, no design call, no behavior change | Fix in-session; batch into one PR (§3b) — **any file count** |
| **Judgment / behavioral / broken** | needs a design decision, new copy/i18n keys, an API/contract change, a refactor, *or* fixes broken behavior / a security/access defect | Consolidate by theme, file (§3c) |

When uncertain whether a fix is mechanical, treat it as judgment and file it —
but do **not** file a genuinely mechanical multi-file sweep just because it
touches many files (that is the old gate this replaces). Do not split one logical
fix to make a piece "mechanical." For `security`/`authz`/`evidence`/`eval` runs,
every finding is judgment-class (file it) — skip §3b.

### 3b — Mechanical findings: one batched fix PR (ui/ux/api)

Collect **every** mechanical-drift finding across the whole run — no file-count
or LOC ceiling on the batch, only the per-theme ~150-LOC sanity cap from the
intro. Apply all fixes in the working tree, then open a **single PR** via
`/zetify:push`:

- Branch: the chore branch `slot:git-workflow` names, slugged `audit-{type}-{YYYY-MM-DD}-fixes`
- PR title: `fix(audit): {type} audit mechanical fixes — {date}`
- PR body: bullet list of every finding fixed (checklist ref + one-line
  description each). No tracker issues are created for these.
- After the PR is open, note its URL in the audit record (Step 4) under
  **findings registry** (local ID → PR link → severity → summary).

If there are no mechanical findings, skip this sub-step entirely. A `ui` run's
font-size / icon-size / token / `useT()`-wrap (keyed strings) / `@zetify/ui`-
async-state fixes are the canonical batch — they used to spawn most of the tiny
tickets.

### 3c — Judgment findings: consolidate by theme, then file (cap ~3/run)

**Consolidate first.** Group the remaining findings by **fix-surface / root
cause** — one "no async-state primitive adopted" root, one "hardcoded English
strings" root, one "off-scale typography needing scale decisions" root — and file
**one issue per theme**, with every component/page in that theme's roster listed
in the body (the §0/§6 inventory list *is* this roster). Do **not** file one
issue per file or per symptom. Target **~1–3 issues on a heavy pass**:

- **S1/S2 broken-behavior findings always file** — never deferred, never capped.
- The cap governs **S3/S4 drift themes**: after the mechanical batch (§3b) and
  consolidation, if more than ~3 drift themes remain, file the top ones by
  **reach × severity** and roll the rest into the record's **next-run seed**
  (Step 4) as named gaps — not into tickets.
- **Critical-first phase override** (when `phase: critical-first` — see the *Critical-first
  phase override* note in the Step 3 triage intro and
  [`audits/README.md`](../../../knowledge/audits/README.md) → *Program phase*): the S3/S4 cap
  is **zero**, not ~3. File **only S1/S2** (plus every security/authz/evidence finding at any
  severity); roll **all** S3/S4 cosmetic-only drift to the next-run seed. Any S3/S4 finding
  that is actually a **security/access/data-integrity** issue (mis-severitised as "drift") files
  regardless — the floor is on *cosmetic* polish, never on correctness. This is a filing change
  only: still record every S3/S4 in the run's coverage matrix + next-run seed so nothing is lost.

Broken behavior → `/zetify:bug:create`; UX gaps / working-as-built-but-wrong →
`/zetify:task:create`.

> **You no longer route what you file, and that is deliberate.** Every issue you create
> is born in the **`triage`** workflow state and is triaged by a fresh
> [`/zetify:check`](check.md) session — which sets the priority, the `Component`, the
> Project, the blockers, and then either moves it to **`Implement Queue`** (the fleet
> takes it) or **`Blocked · decision`** (the human owns the call). **Never set a routing
> state yourself, and never pass a `priority`.** An audit is judged by what it found, so
> its own severity and urgency are self-assessments — the same reason §3a′ already takes
> the harm predicate away from the finder and gives it to the verifier. This closes the
> last path by which an auditor's opinion about what the product *should* do could reach
> the fleet unreviewed: a finding whose expected behaviour nothing has committed to now
> comes back as a **proposal for the human**, not a merged PR.

Mechanics that still bite:

- The tracker, team and key prefix are `slot:tracker-identity`'s (never a stale one from
  memory), **file in the `triage` workflow state**, label `bug` or `task` (Type group)
  — and no routing labels: retired routers are never a live instruction. That is the whole
  label set — the area is the checker's to set as a project, never the filer's.
- **Evidence is yours and only yours** — the checker cannot reconstruct it. Body carries
  `**Severity:** S1–S4` and
  `**Source:** {type}-audit walkthrough {date} (checklist ref, journey/check ID)`
  plus forensic detail: repro steps, exact status codes, log excerpts,
  observed-vs-expected. Severity stays in the **body** as a description of observed
  harm; the checker derives the tracker `priority` field from it per
  [`issue-priority.md`](../../rubrics/issue-priority.md) — cite that, never restate the ladder.
- **Name the commitment when you can.** If the finding is a defect against a capability
  row in a feature map (`slot:feature-maps`) or a requirement row, cite it in the body. It is not
  required — the checker looks it up either way — but a finding that arrives with its
  commitment already named is released in one pass instead of researched from scratch,
  and citing nothing when something obvious exists is how a real defect gets escalated
  as if it were a feature request.
- Consolidate (the §3c cap): one issue per *fix-surface / root cause*, never per
  symptom or per file; a themed sweep-task lists its whole component/page roster
  in the body, cross-linking related issues. ~1–3 issues for a heavy pass — surplus
  S3/S4 drift themes go to the next-run seed, not to tickets.
- **Screenshots are mandatory on every UI finding.** Upload flow per issue:
  1. `stat -f '%N %z' *.png` — exact byte size required.
  2. `file_issue` `attachments` — carry the evidence on the filing call.
  3. `curl -X PUT --data-binary @file` to the signed URL **with every
     returned header verbatim** — the URL expires in **60s**, so batch at
     most 3–4 prepares before PUTting; a 400 means expired → re-prepare.
  4. Read the attachment URL the tool prints back into the finding.
- After all uploads: `rm` the screenshots from the repo root.

### 3d — Guardrail-first filing (the correctness / access types)

For `architecture`/`api`/`security`/`authz`/`evidence` runs, filing is
**guardrail-first** — §3a–c (mechanical-vs-judgment) is a `ux`/`ui` cosmetic model and does
**not** apply. The rule: **every finding class ships a preventer** — whatever this repo's
static-analysis surface is (its `languages` and `gate` slots name it: a new analyzer, a lint
rule, a hook) or, where there is none to extend, a regression test — and
issues are grouped **one per guardrail**, each bundling *every* finding it prevents plus the
fix. Never one issue per finding.

0. **Split the behaviour changes out FIRST — before any guardrail grouping.** A finding whose
   fix changes what the code *does* (not merely where it lives) is a **bug**: it files on its
   own as `Type:bug` filed in the **`triage`** state, with a reproduction and a
   red-test-first fix plan, and is routed to `/zetify:bug:fix`. It never becomes a line
   item inside a consolidation ticket.
   The test is the fix, not the symptom — **"would this fix alter behaviour for some input?"**
   If yes it is a bug, whatever dimension found it:
   - a guard/gate/validation present on one path and absent on a sibling (an unchecked input, a
     missing rate-limit or lock or permission call);
   - fail-open where the sibling fails closed, or an error class collapsed into the wrong one;
   - a value computed or reported wrongly (a count, a total, a truncation);
   - a race, a leak, or an already-fixed defect reintroduced in a second copy.

   **Why this rule exists:** the 2026-08-10 architecture sweep rated 87% of 413 findings S3/S4
   and bundled them by fix-surface. Manual verification of one bundle found an unauthenticated
   audit-insert amplification, an agent-driven memory wipe, a bypassed serialization lock, a
   wrong governance count, and an error-laundering path — all filed as S3 "duplicated logic,"
   all shipped to a fleet agent as refactor line items where no failing test would ever be
   written for them (ENG-5324…5329). A drifted copy and a broken copy are not the same finding
   class. **Consolidation is for code that is merely in the wrong place; a bug is a bug.**

   The consolidation ticket still keeps the *duplication* finding for the same sites — it just
   stops owning the behavioural fix, and cross-links the bug.

1. **Map findings → guardrail classes.** Use the engine's `synthesis.crossUnit` clusters as
   the spine — each cross-unit cluster is usually one guardrail (the analyzer that catches the
   whole class); fold the matching per-unit `effective` findings into it. A finding with no
   feasible static lint still ships a **regression test** as its guardrail.
2. **One issue per guardrail.** Title = the guardrail to build. Body = (a) the guardrail spec
   (what to detect; template = an existing analyzer in the repo's static-analysis surface; wire into
   `{{target:lint}}`; baseline current debt so it can only shrink), (b) the findings it prevents with
   exact sites, (c) the fixes to land. S1/S2 fixes ride their guardrail issue (e.g. an S1
   auth-narrowing fix + the analyzer that prevents recurrence).

   **No preventer, no ticket.** If you cannot name the analyzer, lint extension or regression
   test in (a), the group is not a guardrail issue — it is a cleanup backlog, and it goes to the
   record's **next-run seed** as named gaps instead of to the tracker. A ticket whose own body says it
   ships no preventer (ENG-5299: *"This ticket is a bounded cleanup backlog, not a
   guardrail-build"*) is this rule being written down and then walked past: the sites will
   re-rot and the next sweep re-finds them, so the ticket buys one PR of churn and no durable
   change. This is not a licence to drop the finding — the seed keeps it visible, and a class
   that recurs across ≥3 runs is itself the preventer gap worth building.
3. **Feature-area Project + labels.** Route to the **tracker project for the guardrail's
   feature area** on Team **Engineering** (`ENG`) — the same authored-not-derived rule as
   §3c: default from the `Component` label where it resolves to exactly one area, **ask the
   user otherwise**, never guess. A guardrail spanning several areas is filed against the
   area where the analyzer/test will live, and names the others in the body. (The old
   sweep-dedicated Projects — `Architecture Anti-Rot`, `API & Service Hardening` — are
   retired by the re-point: a Project is a feature area now, not a workstream bucket.)
   State: **`triage`**; labels: `task`/`bug`. The `Component` label and the tracker
   `priority` are both set by [`/zetify:check`](check.md) — file neither, and never move
   an audit finding to a routing state yourself (`Implement Queue`/`Blocked · decision`
   are the checker's call). (There is no `Area` label any more: retired 2026-08-18.)
   **Put the finding's file paths in the body** (that is what the
   checker resolves the component from, via `python3 knowledge/scripts/component_of.py`): audit
   findings are tracker-native, so that label is their only edge to the component
   architecture, and 13 open arch-debt issues went invisible to every roadmap view for
   want of it. State the severity in the body (S1 → Urgent, flagship + high-reach
   guardrails → High, rest → Medium); the checker turns it into the priority field.
4. **Link the record.** The record's remediation section maps each guardrail issue → the
   findings it bundles (Step 4). Worked example:
   `knowledge/audits/architecture/2026-09-05-whole-codebase.md` Part 4 + issues ENG-9741…9766.

**Critical-first phase** (when `phase: critical-first`): the correctness/access types are mostly unaffected —
`security`/`authz`/`evidence` are pure correctness/access and **always file** guardrail-first, and
critical-first only *raises* their priority (a `security` run leads the cadence and rides every
`product` pass — see [`audits/README.md`](../../../knowledge/audits/README.md) → *Program phase*).
The one deferral: a guardrail whose whole finding class is **pure S4 convention/naming drift** with
no correctness or access impact (an `architecture`/`api` cosmetic-divergence lint) rolls to the
next-run seed rather than shipping a ticket this run; every correctness/access/security guardrail
files as written.

`eval` files **file-all** — each finding → a prompt/tool fix whose guardrail is a **new frozen
eval case** pinning the regression.

### 3e — A park on a person is bound to the card

An audit files; it does not ask. When a finding — or this run — must park at
`Blocked · decision` anyway (the verify-failure cap in §2h, a judgement call no checklist
settles), what it writes is the question a person answers without reading the audit, so it
is written to the card, and a run that ends `needs-decision` writes the `decision` document.

<!-- include: process/interview-card.md -->

<!-- include: process/decision-document.md -->

## Step 4 — Render the audit record (one rolling record per scope)

**The record is rendered from the ledger (§2a), now — not written from memory, and never
created earlier.** Two records for one `(type, scope)` on disk at once hard-fails
`{{target:validate-knowledge}}`'s hygiene rule at every commit in the checkout. Fold
the ledger's unit table, per-unit matrix files, findings table and (autonomous) cycle log into
the sections below; **the cycle log survives into the record** — it is the proof of what was
re-verified and at which SHA. Then prune the prior record for this scope.

Create `<record home>/{type}/{YYYY-MM-DD}-{scope}.md` exactly per the
format in `knowledge/audits/README.md`. Frontmatter — every field, none optional
to omit:

- `type: audit-record`
- `audit_type:` · `date:` · `scope:` · `checklist:` · `environment:` (incl.
  data-state caveats)
- **`providers: llm=<provider:model | mock:test | n/a> embeddings=<provider:model | mock-embed | n/a>`**
  — required on every record. A **live** lens (`ux` / `ui` / `feature` / `eval` /
  `docs` / `product`) names the model it **observed** (never the one it expected); a
  **static** lens (`security` / `authz` / `api` / `architecture` / `evidence`)
  writes `providers: llm=n/a embeddings=n/a`. A live-lens `llm=n/a` needs a
  stated reason on the same line or in `environment:`. This is the honesty
  contract's first question — *what model answered?* — and the one field an
  author following only this step's older field list could silently drop.
- `status: complete | partial` — a run that could not reach the capability its
  lens exists to test is `partial`, never a clean pass over blocked ground
- `previous_run:` optional

Then the sections —
**AC-conformance matrix** (journey-scoped runs only — one row per acceptance
criterion: `AC id | verdict PASS/FAIL/BLOCKED/N/A | evidence`; **every** AC the
journey lists appears, none omitted — this is the exhaustiveness proof),
**coverage matrix** (every surface: audited / partial / not audited, with the
blocking reason — for ui/ux this is **exhaustive over the router**: every route
is a row, audited or deferred-with-reason, never silently absent; for
**architecture** each row is `audited (n/n)`, so the coverage ledger can sum
the matrix and mechanically verify a `status: complete` claim — ENG-6198), **findings
registry** (local ID → the tracker link → severity → summary), **positive patterns**
(what must not regress), **next-run seed** (gaps + blocked items + environment
fixes), and **previous-run validation** (each prior finding you re-tested this
run → `PASS / FAIL / still-open` + the tracker link — carries the superseded run's
result forward; on a scope's first run, `n/a — first run`).

**Pre-authoring gate (hard — before Step 6's commit, before any prune that
deletes the only copy).** After the file is on disk, **re-read its frontmatter**
and confirm `providers:` is present and non-empty, with both `llm=` and
`embeddings=` surfaces filled. Missing → fix the record **now** (one line) and
do not proceed. The honesty contract
([`knowledge/audits/README.md`](../../../knowledge/audits/README.md) →
*`providers:`*) is what push/CI enforces later; catching it here is the only
point where the fix is cheap rather than a rebase-and-rerun cycle. Do not
trust memory that you wrote it — read the file.

Then **prune — keep only the last + the previous run's validation**: after
writing this record **and clearing the pre-authoring gate**, **delete every
older record for this scope** (legacy dated ones included) so exactly one
record per scope survives. Its *previous-run validation* section is the sole
retained trace of the run(s) it replaces — the full history lives in the
tracker (findings) + git (prior commits). Never accumulate a dated pile. Also
update the memory index if the audit changed durable project understanding.

**Then decide whether this record survives its own commit** — see
[`knowledge/audits/README.md`](../../../knowledge/audits/README.md) → *Retention*.
Only a **recurring-cadence scope** (a row in that README's *Recurring scheduled
audits* table) keeps a file. A **non-recurring** scope — **every PRD post-ship
pass**, and any one-off narrow run of a page / journey / subsystem no cadence row
schedules — is **consumed**: you have now rendered it, filed from it, and retro'd
the checklist against it, so **`git rm` it in this same commit**. Nothing comes
back to supersede a scope that never recurs, so a retained file is a permanent
orphan: its *next-run seed* has no next run and its *previous-run validation* is
`n/a — first run` forever. 269 PRD-scoped orphans accumulated this way before the
2026-08-15 sweep, and the hygiene rule passed throughout — it forbids
*two* records for one scope, and can no more see a scope that never returns than
it can see one that never existed.

Carry anything **durable** out before deleting: a rule that should bind future
work → the type's checklist (Step 5) or a `knowledge/requirements/<domain>.md`
row; a rejected approach or accepted risk → a decision record. The record file is
never the home for it.

Gotcha: `{{target:validate-knowledge}}`'s path rule resolves every literal
`knowledge/…` string outside fenced code blocks — write path *patterns* with
`{braces}`, never angle brackets, or split prefix from pattern.

## Step 4b — Write the check-result file (one append-only file per run)

**The record is the run's narrative; the result file is its verdicts as data — and the run
writes both.** PRD 0774 makes every check leave **one append-only JSON result file per run**;
PRD 0771's walk (AC-3) waits on it, because without it the Quality desk's map cannot move and
a briefed check has nothing to show. Before this writer existed, every run produced a record
and no result: `knowledge/audits/results/` held only its README while the reader
(`fleet_knowledge.quality.read_results`) waited for a file nothing produced.

**Write it with the shipped writer, never by hand** — the shape is a contract read by the
Quality desk and enforced by the consuming repository's own commit-time result gate, and a
hand-typed file drifts from it:

```
python3 knowledge/scripts/check_result.py write \
  --kind {type} --target {thing-or-capability-ids} [--scope {scope-slug}] \
  --environment {live|code-only} [--finished|--unfinished] \
  --verdict '{journey-id}#{n}=pass' --verdict '{kind}/{item-id}=fail' \
  --reason '{kind}/{item-id}={why it failed}'
```

- `--kind` is the audit **type** (`security`, `ux`, `api`, …) and becomes the file's parent
  directory — it must be one of the kinds the `audit-profile` slot declares.
- `--target` is the **thing or capability ids the run looked at** — a capability id
  (`CAP-0001`), an area/component/connector/customer-system id (`sync`), or a journey slug —
  comma-separated when the run covered several (`CAP-0001,CAP-0002`). The Quality desk places a
  checklist verdict on exactly these ids; a free-text scope is **not** a target, and the writer
  **refuses** one (a target the desk cannot place is how 18 nightly results left the map empty,
  ENG-17695). Put the run's name for itself in `--scope`, the filename slug (which defaults to
  the target). `--commit` defaults to this checkout's `HEAD`;
  pass it explicitly when the run was against a **standing** target's deployed build (§2h step
  4), so the file names the binary that was actually observed.
- `--environment live` **iff a live unit ran against the running product**. A pure static
  read — the `architecture` / `api` / `security` / `authz` / `evidence` lanes with no browser —
  is `code-only`. Only a **finished, `live`** run's verdicts count as a check on the map; a
  code-only or unfinished run is recorded, never read as a pass.
- `--finished` **iff coverage reconciled `done == expected`** — the same hard gate §2c-live
  sets. A run that could not reach the capability its lens exists to test writes
  `--unfinished`, and its verdicts are the honest record of what it reached.
- One `--verdict` per **acceptance criterion** (`<journey-id>#<n>`, the 1-based ordinal in
  the journey's `## Acceptance criteria` list — the engine's stable id, PRD 0774 D4) or per
  **checklist item** (`<kind>/<item-id>`, e.g. `security/SEC3`, `ui/V0`, `ux/IA1`) or per
  **scenario assertion** (`<scenario-id>#<n>`, kind `scenario`, `--target` the scenario id —
  one verdict for every row of its `## Acceptance criteria` table and no others). A `scenario`
  run drives the environment its `environment:` frontmatter names, applies its `## Setup`
  values exactly, walks its numbered `## Steps` in order, records each row against the
  row's `Promise`, and passes its own run id as `--runner`. The four
  verdicts are `pass`, `fail`, `blocked` (needs `--reason`), `not-applicable` (needs
  `--reason`); an `id` appears at most once. `--verdict-file` takes the whole list as JSON
  when the run has many.

**A live run writes schema version 2 — the evidence, not just the word.** A verdict the
Quality desk can trust names what the run drove and what it saw. Every `live` run that drove an
environment adds:

```
  --environment-id {environment-id} --release {probe-release-field|unknown} \
  --runner {this-session-run-id} [--scenario-version {n}] \
  --promise '{id}={promise-id}' --expected '{id}={short}' --observed '{id}={short}' \
  --request-id '{id}={request-id}' --audit-id '{id}={audit-row-id}' [--snapshot '{id}={hash}'] \
  --attempts '{id}={n}/{m}' [--cause '{id}={product|agent|environment|inconclusive}'] \
  [--ticket '{id}={finding-tracker-key}'] [--new '{id}']
```

- `--environment-id` names the environment record the run drove
  (`knowledge/environments/{id}.json` — its base URL, org, principals and write posture). It
  implies `--environment live`. `--release` is **required** with it: the **`release` field** of
  the record's `version_probe` answer — never its `commit` or build time — read once, **after**
  signing in as the first principal the run signs in as (any principal the record lists when the
  run signs in as nobody), and **before** the first step — a production probe may answer only a
  signed-in caller. When the record has no probe, the probe answered `401`, `403`, `404` or any
  other non-success status, the probe did not answer, or its answer says `isStamped: false` or
  carries no `release`, pass `--release unknown` (a timeout, a refused connection, a `429` or a
  `5xx` only after a few short retries) — the writer then records the run `finished: false`,
  because a verdict against a build nobody can name is recorded and never counted. **The run may
  leave `--release` off:** the daemon exports the deployed release of the environment the box runs
  in as `FLEET_RELEASE` into every dispatched run, and the writer uses it when `--release` is
  absent (ENG-19900). An explicit `--release` always wins over that export; pass one when the probe
  named a build the export cannot.
- `--runner` is **this session's run id**, and it is required with `--environment-id`. Use
  the fleet run id the session was dispatched under, or the session id when run by hand. The
  verifier refuses to review a result whose `runner` equals its own run id, so the session
  that ran a check never certifies it. Pass it on a `code-only` run too; there it is optional.
- `--scenario-version` (kind `scenario` only) is the scenario record's `version:` the run
  walked, so a verdict is never read against steps it did not drive.
- **Evidence is the platform's own ids, collected while driving — never reconstructed.** For
  each assertion record the **request ids** the platform logged for the calls that produced the
  observation (the response's request-id header, or the matching line in the platform's request
  log), and for a **governed action or refusal** the **audit-log row id** that recorded it. A
  snapshot hash (`--snapshot`) stands in only where the observation is a rendered state with no
  request behind it.
- **A pass with no platform evidence is not a pass.** In a v2 file the writer records a `pass`
  carrying no request id, audit id or snapshot as `blocked`, with the reason `no evidence` and
  `cause: inconclusive`. Write it that way yourself rather than leaning on the correction, and
  say in the record which id you could not obtain.
- **Always pass `--expected` and `--observed` for every verdict in a v2 file**, a fail or blocked
  as much as a pass. The writer refuses a v2 verdict that lacks either one (FLT-1211). A
  `scenario` run against an environment must also pass `--scenario-version`. Without it the
  Quality desk can never match the file's verdicts to the scenario table, so its passes would
  silently never count, and the writer refuses the file.
- **Against an environment, three fields are required, not optional.** When
  `--environment-id` is set, every verdict carries `--promise` and `--attempts`, and every
  `fail`/`blocked` carries `--cause`. The writer refuses the file otherwise. Results are
  append-only, so a field left optional now would mean a v3 later.
- `--promise` names the **one** promise the assertion proves (a requirement row id, a
  `CAP-NNNN` or one journey criterion `<journey-id>#<n>` (FLT-1202) — never a bare journey id,
  which counts toward no promise; for a scenario, the row's `Promise` cell). `--expected` /
  `--observed` are one short structured line each (`refused 403 ceiling_exceeded`), never
  narrative.
- `--attempts n/m`: the attempt that produced the verdict out of the attempts made — a pass on
  the third try is `3/3` and reads as flaky, not clean. `--cause` goes only on `fail`/`blocked`:
  `product` (the product is wrong), `agent` (the run drove it wrong), `environment` (the
  environment could not serve the step) or `inconclusive`. `--new` marks a verdict not seen on
  the previous run.
- `--ticket` carries the tracker key of the finding a `fail` filed in §3c (`BUG-1178`, `ENG-12345`),
  so the Quality desk names the ticket beside the failure's cause (FLT-1221). Record it on
  `fail`/`blocked` only; a fail that filed nothing carries none.
- `review` is the verifier's field (`verified|unverified|disputed` with its instant); a run
  never sets it on its own verdicts — absent reads as `unverified`.

Execution is **agent-driven**: the run drives the environment itself and collects these ids as
it goes. There is no deterministic test layer behind a scenario to borrow a verdict from.
`--verdict-file` accepts every one of these keys per entry (`evidence` as
`{request_ids, audit_ids, snapshot}`) when the run has many. A `code-only` run has no
environment and writes v1 exactly as before. **But if a `code-only` run sets any v2 field**
(a `--promise`, an `--expected`, anything per verdict), the file becomes v2. A code-only read
has no request ids or audit ids, so every `pass` in that file that lacks a `--snapshot` is
recorded as `blocked` with the reason "no evidence". Give each such pass a snapshot hash of
what was read, or set no v2 field at all.

It lands at `knowledge/audits/results/{kind}/{YYYY-MM-DD}-{scope-slug}-{HHMMSS}Z.json` and
**rides the Step 6 commit**. The writer validates the whole shape before it writes: a refusal
prints `check_result: …`, writes nothing, and exits non-zero — so a malformed result never
reaches the commit. **The file is append-only: never edit or delete one** (the one permitted
deletion is the 90-day prune, a later PR's job, not this run's).

## Step 5 — Retro: improve the checklist & spec (only when earned)

An audit also tests *its own checklist*. Before committing, ask: **did this run
surface something the checklist or the type's standards spec didn't anticipate?**
Most runs: no — and that's the correct, common answer. Don't invent process work
to look thorough; a bloated checklist is worse than a focused one. Propose a
change only when it would change a *future* run.

Worthy items (durable method gaps, not one-off findings):

- **Finding class with no check ID** — you kept filing a kind of issue the
  dimensions (`I*` / `V*` / `G*`) don't name → add the dimension.
- **Missing standard** — the run repeatedly leaned on a "correct" the type's spec
  (`ui-spec.md`, `api-design-guide.md`, …) never states → add the rule with its
  number/token so the next run cites it instead of improvising.
- **Recurring smell** worth promoting to a named, greppable check.
- **Noisy check** that produced false positives → narrow or qualify it.
- **Catalog / coverage gap** — a real surface the surface/journey catalog omits.
- **Tooling/env gap** — something the run needed (a wired axe pass, a seed
  fixture) that should become a standing prerequisite.
- **Page-spec gaps (two layers)** — V0/G0 audits each page against its
  `<Page>.spec.md`, so the run is also a test of the specs themselves. (a) *Per-page*
  — the page carries load-bearing intent its spec never captured (a real UX decision,
  a data source, a canonical-choice rule): **complete that page's spec this session**
  (re-run `{{target:generate-page-specs}}`); the edit rides the Step 6 doc commit. (b)
  *Contract* — a dimension specs should *always* carry but the format never requires,
  so it's silently missing everywhere (e.g. permissions/visibility, the four states):
  that's a page-spec **contract** gap. Propose promoting it to the required-section set
  (the required-section set `{{target:generate-page-specs}}` enforces, plus the scaffold template
  `slot:ui-contracts` names, plus `/zetify:page:spec`) so every future spec
  carries it. A recurring (b) across runs is exactly what `/zetify:process:improve`
  harvests from the retro corpus — log it there, don't unilaterally rewrite the
  contract.

Then:

- **Apply the clearly-additive, low-risk ones directly** (a new check row, a
  catalog entry, an unambiguous threshold) — they edit the checklist/spec and ride
  the same doc commit (Step 6).
- **Never unilaterally rewrite a standing canonical rule.** If the change alters or
  removes an existing rule, or is a judgment call, *propose* it in the final report
  for a human to ratify — don't edit it in.
- Note applied changes in one line in the record ("Retro: added `V11` …"); if none
  were warranted, say so in the report, not the record.

## Step 6 — Commit & report

- Doc commit — the new record, the **deletions** of the superseded record(s) for
  this scope (Step 4), the **check-result file** this run wrote (Step 4b), and any
  checklist/spec improvements from the retro (Step
  5), in one commit. `main` has no direct-push path for the fleet identity
  (`docs/ci-branch-protection.md` §0), so this still ships via a throwaway branch
  + PR — not a bare push, and not a fire-and-forget one: you own it to merge (below).
  **🛑 Name the branch with the issue key** — `agent/chore-audit-<type>-<eng-key>-<scope-slug>`
  for a daemon-routed run, where `<eng-key>` is the issue's own team prefix +
  number, **lowercased and hyphenated** (`ENG-12042` → `eng-12042`); a human
  `<type> [scope]` run with no issue keeps `agent/chore-audit-<type>-<scope-slug>`.
  The consuming repo's orphaned-PR sweep correlates a PR to an issue *only* through
  the key on the head branch (`extract_issue_key_from_branch`), so a branch with no
  hyphenated key is logged `no ENG id on head branch — not fleet lane work` and is
  never swept — the record PR drifts unowned instead of being closed on the issue's
  state (ENG-12042).
  **🛑 Compose the record PR body with the script — never by hand (ENG-12308).**
  A tracker-keyed PR without a parseable `## Files` manifest fails the consuming
  repo's `validate_pr_scope_manifest` guard **closed**, so a record PR opened
  without one is born red with no owner: six on 2026-09-24, and two more *after*
  ENG-12042's prose fix landed (#12059, #12117). A rule the author must remember
  is not a rule that binds, so the manifest is **produced mechanically**, not
  remembered:

  **One rolling record PR per audit type — append, never open a second.** Before opening,
  look for an open one: `gh pr list --state open --search "head:agent/chore-audit-<type>-"
  --json number,headRefName`. If one exists, check out its branch, merge `origin/main` in,
  commit this run's record + result file onto it, push (disarm first if armed), re-arm, and
  own *that* PR (below). Open a new PR only when none is open for the type.

  **The PR is born green and guard-clean by construction** — each trap below was measured:
  the title carries **no** tracker key (a quoted key in a title forces a `## Files`
  manifest, and a key in the title of a docs PR moves that issue to Done on merge); the key
  lives only in the branch and in the body's `Refs` line (never `Closes`/`Fixes`); the body
  carries a coded `NOT-A-VERIFY-LANE-PR=not-gated-type: audit record, issue kind is audit`
  line (the Verify Gate fires on a bare key in a knowledge PR; an audit issue is not kind
  bug/task/cleanup, which that code checks); and the diff holds **only** paths under
  `knowledge/audits/` (plus checklist/spec edits from Step 5) — a lock file, generated
  file or anything outside `knowledge/` makes a "doc-only" claim false, so make no
  doc-only claim in the body and move any such path out of this PR.

  ```
  printf '%s\n' 'NOT-A-VERIFY-LANE-PR=not-gated-type: audit record, issue kind is audit' \
    > /tmp/audit-record-note.md
  python3 knowledge/scripts/pr_scope_manifest.py compose \
    --refs <KEY> --base origin/main --note-file /tmp/audit-record-note.md \
    --out /tmp/audit-record-body.md
  gh pr create --title "audit: <type> <scope> record" \
    --body-file /tmp/audit-record-body.md
  ```

  `compose` writes a bare `Refs <KEY>` link (never a `Closes`/`Fixes` keyword —
  this throwaway PR is not the completing merge) plus a `## Files` manifest
  generated from `git diff --name-only origin/main...HEAD`, so the body cannot be
  authored without one. Non-ff on the branch → `git pull --rebase origin main`
  first (tree is clean — all screenshots were deleted in Step 3).
  **If any CI-discovered fixup needs a follow-up push to this branch after
  `--auto` is armed, disarm first** (`python3 knowledge/scripts/gh_automerge_disarm.py`
  <pr>`, ENG-3386 — `push.md` step 6) — never push a new commit while
  auto-merge is armed.
  **Pre-authoring gate (hard — before `--auto` is armed).** Arm with the script,
  not a bare `gh pr merge --auto`:

  ```
  python3 knowledge/scripts/pr_scope_manifest.py arm --pr <pr> --base origin/main
  ```

  `arm` **re-reads** the live PR body (`gh pr view`) and the diff back and
  refuses non-zero unless the `## Files` section it carries names every changed
  path — arming a manifest-less record PR is not expressible through it. Missing
  key or manifest → fix it **now**; catching it here is the difference between
  one edit and a red required check remedied by hand-pasting the block the
  failure prints (what the two 2026-09-25 PRs needed).
  **Arm the moment it opens** (the `arm` above, immediately — not after CI): auto-merge is
  what lands the record. **You opened it, you own it until `state: MERGED`** — the issue
  closing does not transfer it, and an unarmed or conflicted record PR is orphaned for good
  (16 sat open on 2026-10-11 with their issues done). Before the run ends, watch it (a
  `Monitor`, not a one-shot check) and handle all of: **conflict** (`mergeStateStatus:
  DIRTY`, zero checks) — merge `origin/main` in, take any generated file from main and
  re-run its generator, never hand-merge it, push, confirm the PR head equals the remote
  ref, **then recompose the body** (`pr_scope_manifest.py compose` + `gh pr edit --body-file`):
  a rebase can drop a file the base already carries, and a `## Files` manifest still naming it
  fails `PRD Verified` as "declared but not changed" (#17768); **red** — read the failing job, fix the cause, disarm, push, re-arm; **ejected from
  the merge queue** — read the `merge_group` run, fix, re-enqueue; **unarmed** — re-arm.
  If it cannot reach `MERGED` inside the run, **file the remaining step** as a tracker
  issue naming the PR number and the exact next action (never leave the PR silently open),
  and list it in the report. The run's *outcome* stays the daemon's success signal, but a
  record PR still open at the end with no filed owner is a defect of the run.
- Final report in-conversation: structural findings first, then
  severity-ordered findings with the tracker links, positive patterns, honest
  coverage gaps, and any **retro proposals deferred for ratification** (Step 5).
  No `status:` flips anywhere — audits don't touch the PRD state machine.
- **Post the run manifest on the audit issue — BEFORE ending.** An audit's whole
  output is *elsewhere*: findings become separate tracker issues, the record becomes
  a commit, mechanical drift becomes a PR. So the work order itself must carry a
  trace of what it produced. A reader of the audit issue must never have to grep git
  to find out what the audit did.

  Comment **one** manifest, in this shape:

  ```
  ✅ `/zetify:audit {KEY}` — AUDIT COMPLETE · {type} · {scope}

  **Filed ({n}):**
  - ENG-6347 — S2 — connector credentials echoed back in the catalog response
  - ENG-6348 — S3 — …
  **Fixed in-session:** {PR link, or "none"}
  **Record:** {path} ({PR link})
  **Coverage:** {n}/{n} atoms · sub-floor: {n} · filed: {n}
  ```

  Two ordering rules, both load-bearing. **Comment first, end the run second** — the
  outcome is the daemon's success signal, so anything after it is racing a supervisor
  that may already be tearing the run down. And **every filed finding carries the
  audit issue's key in its own body** (`Source:` line), so the link is navigable in
  both directions. A `relate` edge is *not* a substitute — it renders nowhere in the
  finding's body, which is what an implementer actually reads.

  **File nothing? Say so explicitly** — `**Filed (0)** — clean pass, {n}/{n} atoms
  covered`. A silent end is indistinguishable from a run that died before filing, and
  a zero-finding pass is the one result this program's own §2f says to distrust.

- **Daemon-routed (`<KEY>`) completion.** When invoked by issue key, after the
  record commits, every finding is filed, and **the manifest above is posted**,
  **success is the run's outcome**. Do not move the issue to a closed position —
  `move_issue` refuses closed positions.
  **On a multi-type issue (§2e) completion is all-or-nothing:** end successfully only
  after *every* `/zetify:audit` line has run and written its record. If a line could not
  run, leave the issue open, say which one and why in the report, and let the next
  dispatch resume it — a partial pass marked complete is a silently skipped audit.

---

## Rules

- **The coordinator never does the work.** In every configuration — one unit or three hundred,
  static or live, one pass or an endless campaign — the coordinator partitions, dispatches
  fresh-context sub-agents, verifies, files and keeps the ledger. It never reads source to find
  defects, drives the browser, queries the DB, or writes a fix. The old "walk mode" exception is
  exactly how a scoped run came to blow its own context and truncate its coverage ledger.
- **The ledger is the run's memory — the coordinator's context is only a cache of it.** Write
  before you act and after you learn; re-read after every compaction or resume; never resolve a
  finding from tracker state alone. A merged PR is a claim; the live re-drive on a confirmed-fresh
  binary is the proof.
- **File only what a proving artifact backs (§3a′).** One of the five customer-harm predicates,
  named by the **verifier**, never by the finder. Governance defects file at any severity.
  Sub-floor findings are still fixed and still recorded — just never ticketed.
- **Observe, triage, then act — gate by nature, not file count.** Mechanical
  drift (a single known-pattern transform — token/size swaps, `useT()` wraps of
  keyed strings, `@zetify/ui` async states) is fixed in-session and batched into
  one PR (ui/ux/api), *whatever the file count*; judgment / behavioral / broken
  findings are consolidated by theme (~1–3 per run) and filed. Never default to
  filing a mechanical fix because it spans many files, and never split one logical
  fix to dodge a class. `security`/`authz`/`evidence`/`eval` file everything.
- **One record per *recurring* scope — keep the last, not the pile; a scope that
  never recurs keeps none.** A recurring-cadence run supersedes and **deletes** the
  prior record for its scope, carrying the re-verify result forward into the new
  record's *previous-run validation*. A **non-recurring** scope (every PRD
  post-ship pass; any one-off narrow run) is **consumed at write time** — rendered,
  filed from, retro'd, then `git rm`'d in the same commit (Step 4 → *Retention*).
  The audit folder is never an append-only dated history (the tracker + git hold the
  full trail).
- **Every run writes exactly one check-result file, through the shipped writer.** The record
  is the narrative; the result file under `knowledge/audits/results/{kind}/` is the
  machine-readable verdicts the Quality desk composes its map from. It is **append-only** —
  written once, never edited or deleted (the 90-day prune is a later PR's) — and it is written
  by `knowledge/scripts/check_result.py`, never by hand, so its shape stays the contract the
  reader (`fleet_knowledge.quality.read_results`) and the consuming validator agree on.
- **`providers:` is frontmatter, not optional prose.** Every record names
  `llm=` and `embeddings=` (static lenses: `n/a` / `n/a`). Step 4's pre-authoring
  gate re-reads the file before the commit; a missing line is fixed there, never
  discovered at push.
- **An audit run writes only files no other run writes.** The record (named by type, date and
  scope), the check-result file (timestamped) and the coverage file (`coverage-write`,
  timestamped plus run id) are unique per run; a run never bumps a counter, never appends a row to
  a shared index or ledger table, and never allocates an id from a `Next id:` line — a shared
  summary is generated from those files at read time, not committed (the repo's
  derived-ledgers-not-committed precedent). Two concurrent audits therefore touch disjoint paths.
- **An audit's record PR is owned to MERGED.** One rolling PR per audit type (append, never
  a second), auto-merge armed on open, watched until merged, the remainder filed if it
  cannot finish. Its title carries no tracker key.
- **An audit's record PR is keyed and manifests its files.** The branch names the
  issue (`agent/chore-audit-<type>-<eng-key>-<scope-slug>`, hyphenated lowercase
  key) so the orphan sweep can correlate it, and the body carries a `## Files`
  section so the scope-manifest guard accepts it. **Both halves are mechanical:**
  `pr_scope_manifest.py compose` writes the body's manifest from the branch diff,
  and `pr_scope_manifest.py arm` re-reads the live body and the diff and refuses to
  arm auto-merge on a missing or disagreeing manifest — a requirement left to prose
  is what let two post-ENG-12042 PRs through (#12059, #12117; ENG-12308).
- **Evidence or it didn't happen**: screenshot + status code + log line per
  finding. UI findings without screenshots are incomplete.
- **Honest coverage**: "not audited" rows with reasons are a deliverable, not
  an admission — they are the next run's scope.
- **Credit what works**: positive patterns are part of the record; an audit
  that only lists defects loses the regression baseline.
- **The checklist learns, sparingly.** A run that exposes a durable method gap
  improves the checklist/spec (Step 5) — but the bar is "this changes a future
  run", not "this looks thorough". Most runs change nothing, and that is fine.
- **Scoped runs still *render* a record** — a one-page audit produces a small
  dated record (and re-verifies prior findings touching that page), never an
  untracked drive-by. It just doesn't **keep** it: rendering is how the run proves
  it was exhaustive; retention is a separate question the scope's recurrence
  answers.
