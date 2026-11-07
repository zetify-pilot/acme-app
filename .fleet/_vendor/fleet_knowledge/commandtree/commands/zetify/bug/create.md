# <!-- home -->Zetify<!-- /home --> Bug — Create

File a **bug tracker issue** the right way. This is the create-axis sibling of
[`/zetify:bug:fix`](fix.md) (which *executes* a bug to a merged PR). Creating a bug
does **not** fix it, and — since the check gate landed — it does not *route* it either:
it records the forensic evidence and hands the issue to
[`/zetify:check`](../check.md), which triages it in a fresh session and decides where
it goes.

> **Your job is the evidence, and nothing else.** Priority, area, project, component,
> blockers and fleet-eligibility are all set by the checker. You are the only party
> that can supply the reproduction, the observed-vs-expected, and the log line — so
> spend everything here and let the gate do the rest. Guessing a priority for a defect
> you just found is exactly the self-assessment the gate exists to replace.

---

<!-- include: process/writing.md -->

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. `evidence` is the whole job: the filer is the only party who can supply it, and the only party forbidden from triaging it. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "bug-create",
  "tier": "core",
  "sop": "none",
  "needs": "nothing",
  "may merge": false,
  "intent": "File one bug tracker issue carrying the forensic evidence only the filer can supply \u2014 reproduction, observed vs expected, the log line \u2014 and stop.",
  "loads": ["process-issue-shape"],
  "requires": [
    "process-spine", "process-issue-shape", "registers-triage-partition",
    "tracker-identity"
  ],
  "optional": ["components", "feature-areas"],
  "steps": [
    {
      "id": "evidence",
      "name": "Record the evidence \u2014 repro, observed vs expected, the log line",
      "kind": "author",
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

## Context to load

- [`../../../process/issue-shape.md`](../../../process/issue-shape.md) —
  the canonical "create a well-formed tracker issue" contract.

## What to do

1. Gather the bug context: a one-line title, and **forensic** detail in the body —
   repro steps, observed-vs-expected, stack/log excerpt, suspected `file:line`.
   A bug with no observation and no artifact is not a bug report; the checker closes
   those, so do not file one. Write the title to the plain-language rule in
   [`process/writing.md`](../../../process/writing.md) → *Write for a reader who does not
   know the code*: the title says what is broken in words a person who has never opened
   this repository understands, and the repro steps and `file:line` evidence stay in the
   body.
2. Set **severity** and **source** in the body (the typed fields the issue shape names
   for a bug). Severity is a *description of the
   harm you observed*, not a routing decision — the checker derives the tracker
   priority field from it.
3. **File it through the Fleet tools.** Call `file_issue` with `kind: "bug"`, the title,
   the body, `command: "bug:create"` (or `command: "<that command> (Rule-G deferral)"` when
   another command's Rule G sent you here), and `repo` = the lane named by the
   **`tracker-identity`** slot **only when the work lands in another repository**. The same
   call serves a bug a person reported to you and a defect you found yourself (a red CI
   lane, a broken test, a regression you hit mid-run). For a defect found during other work,
   put provenance in the body as `Found during: <KEY>`.

   **When the work was asked for from a feature** — the person named the feature it is for, or the
   brief's `## Request` carries its `area` — pass that slug as `feature`, and Fleet files the
   issue under it at birth, so nobody links it by hand afterwards. Never choose one yourself:
   with no feature named, omit it, and the checker places the issue.

   A bug filed through the tools is born in **`Triage Queue`** as a bug — no person-confirmed
   reproduce stage, whoever's key the session holds. `/zetify:check` confirms it is real and
   runs the full prior-art search before anything is released, so **run no search of your
   own**. Print the returned `id` and Fleet's `message`; the filing is done when its tracker
   key appears (`get_issue` on the `id`). Never re-file a bug as a `task` to reach Triage.

   **A defect in the fleet itself is not a bug in the repository.** When what you found is a
   defect in the fleet — the control plane, the daemon, or the command tier, rather than the
   `repo` checkout's own code — pass `subject: "fleet"`. The filing is then recorded in the
   install's operator inbox and opens **no tracker issue at all**: on a customer install the
   lane's tracker is the customer's own repository, and a fleet-internal defect opened there
   becomes a public issue in their repo and is handed to their workers. Leave `subject` out
   for a defect in the repository's own code; that one still goes to its tracker.

   **No Fleet tools? Stop.** When the session has no Fleet tools, stop with: *this command needs the Fleet tools; create a personal key in Fleet under Settings › Connect your tools*. There is no other filing path — never fall back to a tracker script or a tracker key, which a machine outside the install's cluster does not have and must not need.

4. Print the created issue key (and Fleet's message).

## What the checker does next, so you don't

Named here only so nobody re-adds it above: `/zetify:check` sets the priority, the
component, the feature area, any blockers, and finally either the **`Implement Queue`**
position (fleet takes it) or **`Blocked · decision`** (the human owns the call). It
re-runs the full prior-art search against the filed report and appends its own record
before releasing.

**This command files and stops; the checker owns the park.** File only;
`/zetify:check` releases it. But if a dispatched filing run
nevertheless ends on a person's decision — a fork its brief does not settle — the park carries
the `decision` document, in the card's own fields:

<!-- include: process/decision-document.md -->

## Invoked by an execute command (Rule G)

When [`autonomous-drive.md`](../../../process/autonomous-drive.md) Rule G
fires — `prd:implement` / `task:implement` / `bug:fix` found a bug **out of the
current scope** — this command files it as an agent-found defect (never fix it inline;
that's scope creep and skips reproduce-first TDD). **Link the new issue back** with
`Found during: <KEY>` in the body, and the caller records it in its Autonomous Decisions Log.

## What this is NOT

- Not a fix — that's `bug:fix`.
- Not triage — that's [`check`](../check.md). Do not set priority, area, project or
  the `Implement Queue` position here — file only; `/zetify:check` releases it.
- Not a repo artifact — bugs live in the tracker, never in `knowledge/`.
