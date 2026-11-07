# <!-- home -->Zetify<!-- /home --> Task — Create

File a **`Type:task` tracker issue** the right way — a small, scoped engineering task
to be done later. This is the create-axis sibling of
[`/zetify:task:implement`](implement.md) (which *executes* a task to a merged PR).
This command records the task and **stops** — no plan, no branch, no repo file, and
since the check gate landed, **no triage**: [`/zetify:check`](../check.md) does that in
a fresh session and decides where the task goes.
(This is the former `<!-- home -->/zetify:task<!-- /home --> capture` mode, now its own command.) <!-- home --><!-- tilion-refs:skip --><!-- /home -->

> **Your job is to say what the work is, clearly enough that someone else can judge
> it.** Priority, area, project, component, blockers and fleet-eligibility are the
> checker's. The one judgement that is genuinely yours is *what happened / what is
> missing*, because you are the only party that saw it.

---

<!-- include: process/writing.md -->

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. `hands-off` is a real gate, not a note: the filer setting a priority or a Project is the defect this command exists to prevent. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "task-create",
  "tier": "core",
  "sop": "none",
  "needs": "nothing",
  "may merge": false,
  "intent": "File one well-formed Type:task tracker issue saying what the work is, and stop \u2014 the checker decides everything else.",
  "requires": [
    "process-spine", "registers-triage-partition",
    "tracker-identity"
  ],
  "optional": ["components", "feature-areas"],
  "steps": [
    {
      "id": "file",
      "name": "Say what the work is, and file it through Fleet",
      "kind": "io",
      "actor": "coordinator",
      "produces": [
        "tracker-issue"
      ],
      "body": "what-to-do"
    },
    {
      "id": "hands-off",
      "name": "Leave priority, area, project and blockers to the checker",
      "kind": "gate",
      "actor": "coordinator",
      "gate": "hard",
      "body": "what-the-checker-does-next"
    },
    {
      "id": "rule-g",
      "name": "Invoked by an execute command (Rule G)",
      "kind": "io",
      "actor": "coordinator",
      "body": "invoked-by-an-execute-command"
    }
  ]
}
```

## What to do

1. Capture a concise title + a short description of the task: what should change, and
   **why it is worth doing** — the checker judges the second half against what the
   product has already committed to, so a task body that says only *what* leaves it
   guessing. Write the title and the description to the plain-language rule in
   [`process/writing.md`](../../../process/writing.md) → *Write for a reader who does not
   know the code*: the title says what should change and the body says why it is worth
   doing, in words a person who has never opened this repository understands.
2. **File it through the Fleet tools.** Call the `file_issue` tool with `kind: "task"`,
   the title, a body that says what should change and why it is worth doing, and
   `command: "task:create"` — or, when this filing comes from another command's Rule G,
   `command: "<that command> (Rule-G deferral)"` (e.g. `bug:fix (Rule-G deferral)`); Fleet
   ends the body with the one `Filed by <origin> · <command>` line from it, so never write
   that line yourself. When this filing comes from a run under Rule G, put the originating
   issue key in the body too. Pass `repo` = the lane named by the **`tracker-identity`** slot **only when the
   work lands in another repository**; omit it otherwise. Fleet searches for prior art
   on every filing and attaches the dedupe record to the mint, so **run no search of
   your own**. Print the returned `id`, Fleet's `message`, and the `dedupe` record it
   returned. `/zetify:check` re-runs the full prior-art search before anything is
   released.
   **When the work was asked for from a feature** — the person named the feature it is for, or the
   brief's `## Request` carries its `area` — pass that slug as `feature`, and Fleet files the
   issue under it at birth, so nobody links it by hand afterwards. Never choose one yourself:
   with no feature named, omit it, and the checker places the issue.
3. **Push back if it's a feature in disguise** — PRD-worthy work goes through
   `prd:create`, not here. A task is small, single-stream work. (The checker is a
   second net for this, not the first one: a feature filed as a task comes back as a
   proposal for the human, which is slower than routing it right the first time.)
4. **No Fleet tools? Stop.** When the session has no Fleet tools, stop with: *this command needs the Fleet tools; create a personal key in Fleet under Settings › Connect your tools*. There is no other filing path — never fall back to a tracker script or a tracker key, which a machine outside the install's cluster does not have and must not need.

## What the checker does next, so you don't

Named here only so nobody re-adds it above: `/zetify:check` sets the priority, the
`Component` label, the tracker project (the feature area), any `blockedBy`
relations, and finally either the **`Implement Queue`** state or **`Blocked · decision`**.
It re-runs the full prior-art search against the filed report and appends its own record
before releasing (<!-- home -->ENG-9336<!-- /home -->), which is the safety net under Fleet's own title-only search.

**This is where the old "leave `agent-eligible` OFF by default" rule went.** No create
command writes routing labels at all any more — only the checker moves an issue to
`Implement Queue` — so the rule is structural rather than remembered.

**This command files and stops; the checker owns the park.** But if a dispatched filing run
nevertheless ends on a person's decision — a fork its brief does not settle — the park carries
the `decision` document, in the card's own fields:

<!-- include: process/decision-document.md -->

## Invoked by an execute command (Rule G)

When [`autonomous-drive.md`](../../../process/autonomous-drive.md) Rule G
fires — an execute command found an **important follow-up task** out of scope — this
command files it (don't bolt it onto the in-flight branch). **Put the originating issue
key in the body**; the run's `filed_from` records it, and the checker sets any blocker.
The caller logs it in its Autonomous Decisions Log. If the step-4 refusal fires inside an
execute command, the caller records the follow-up in its own Autonomous Decisions Log and
carries on, rather than failing its run.

## What this is NOT

- Not execution — that's `task:implement`.
- Not triage — that's [`check`](../check.md).
- Not a PRD — heavier work is `prd:create`.
- Not a repo artifact — tasks live in the tracker, never in `knowledge/`.
