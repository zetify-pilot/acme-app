# Zetify Cancel

Cancel a PRD cleanly: flip its frontmatter `status: cancelled`, record **why**
in `cancelled_reason:`, and append to `status_history:`.
Once the flip merges to `main`, the `prd-projection` pass of the fleet's `corpus-sync`
loop (`fleet-service`) moves the Issue to Canceled within the sync's interval (no live
mirror — the pass is the board's writer for it). This closes the terminal state in the PRD
lifecycle — the tracking validator (`{{target:validate-knowledge}}`)
**requires** a `cancelled_reason:` on any `cancelled` PRD, and this command is the
sanctioned way to produce it.

Doc-only change — no source code touched — but it still ships via a throwaway
branch + PR like every other fleet commit (`main`'s required-check protection
binds every actor, the fleet identity included;
`docs/ci-branch-protection.md` §0). "Doc-only" now means *fast and low-risk*,
not *no branch*.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. `reason` is a hard gate: a cancelled PRD whose reason nobody wrote down is re-proposed within the quarter. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "prd-cancel",
  "sop": "none",
  "needs": "answers",
  "may merge": true,
  "intent": "Cancel a PRD with a recorded reason, reopening whatever capability gap it was closing so the planner sees the ground again.",
  "loads": ["planning-model"],
  "requires": [
    "process-spine", "planning-model", "git-workflow", "gate", "file-conventions"
  ],
  "optional": ["process-interview", "feature-maps", "docs"],
  "steps": [
    {
      "id": "reason",
      "name": "Get the reason \u2014 required, never inferred",
      "kind": "gate",
      "actor": "coordinator",
      "gate": "hard",
      "body": "step-1-get-the-reason"
    },
    {
      "id": "flip",
      "name": "Flip the frontmatter",
      "kind": "io",
      "actor": "coordinator",
      "produces": [
        "status"
      ],
      "body": "step-2-flip-the-frontmatter"
    },
    {
      "id": "reopen-gap",
      "name": "Reopen the capability gap, if any",
      "kind": "io",
      "actor": "coordinator",
      "produces": [
        "feature-map"
      ],
      "body": "step-3-reopen-the-capability-gap"
    },
    {
      "id": "retire-pages",
      "name": "Retire the PRD's pages (docs slot)",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-3b-retire-the-prd-s-pages-slot-docs"
    },
    {
      "id": "tracker",
      "name": "Tracker \u2014 no live mirror, the fleet projects it",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-4-tracker-no-live-mirror-the-fleet-projects-it"
    },
    {
      "id": "commit-pr",
      "name": "Commit and open the doc-only PR",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-5-commit-pr"
    },
    {
      "id": "report",
      "name": "Report",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-6-report"
    },
    {
      "id": "land",
      "name": "Headless: land it, write the landed result",
      "kind": "io",
      "actor": "coordinator",
      "body": "step-7-headless-land-it"
    }
  ]
}
```

## Context to load

Read [`knowledge/specs/tracking-and-execution.md`](../../../../knowledge/specs/tracking-and-execution.md)
first — it owns the PRD status state machine, the `cancelled_reason:` rule, and
the tracker board-sync recipe. Nothing else heavy is needed.

---

## Input

Parse `$ARGUMENTS`: a PRD number (e.g. `0083` or `83`), optionally followed by a
free-text reason. Resolve `knowledge/prds/NNNN-<slug>/`.

- If the PRD doesn't exist → report that and stop (nothing to cancel).
- If `status:` is already `cancelled` → report it's already cancelled (show the
  existing `cancelled_reason:`) and stop.
- If `status:` is `shipped` → **do not silently cancel.** Shipped work is done,
  not cancellable. Ask the user (shaped by the interview card, Step 1)
  whether they really mean to mark a shipped PRD cancelled; default to stopping.

## Step 1: Get the reason (required)

A cancellation must say why — it's validator-enforced and it's what a future
reader needs. If the user supplied a reason in `$ARGUMENTS`, use it. Otherwise
ask **one** question, shaped by the interview card:

<!-- include: process/interview-card.md -->

The question:
"Why is PRD NNNN being cancelled?" with a few likely options (superseded by another
PRD · descoped / no longer needed · approach abandoned · merged into another
PRD) — the tool's "Other" escape carries free text. Capture a
concise one-line reason; if it points at a replacement PRD, name it.

## Step 2: Flip the frontmatter

Edit `knowledge/prds/NNNN-<slug>/prd.md`:

- Set `status: cancelled`.
- Add `cancelled_reason: <one-line reason>` (the validator fails the commit
  without it).
- Append `{ state: cancelled, at: <ISO-8601 timestamp>, by: cancel }` to
  `status_history`.

## Step 3: Reopen the capability gap, if any

`knowledge/roadmap.md` needs nothing from you — it is generated on demand and **not
committed**, so the cancellation propagates the next time anyone renders it.

If the cancellation reopens a customer-facing gap, that belongs in the **feature
capability map** (`knowledge/features/<area>.md`) — clear the PRD number from the
affected capability's **Ships in** cell so the row reads as a delivery gap again. The row stays
under its use, and a map with no brief yet gets one in this change
([*Writing a feature brief*](../../../process/feature-doc-reconcile.md#writing-a-feature-brief--every-map-that-is-created-or-edited), moment 3). The
roadmap carries no capability, sequencing, or gap-list content.

## Step 3b: Retire the PRD's pages (`slot:docs`)

A page this PRD shipped does not get to keep **promising** a capability that is cancelled — a
live how-to for a feature that no longer exists is a page that lies. Retire each page the
PRD's `docs_impact` named:

- **Retire the page** in the home `slot:docs` names, and clear the capability map's
  `Documented in` cell — the sibling of Step 3's `Ships in` edit.
- **Leave a redirect** at the old address, in the redirect shape `slot:docs` names — never a
  second invented convention. A reader who followed an old link must land somewhere that says
  the capability is gone, not on a 404.
- A page the PRD never shipped (cancelled before it wrote one) has nothing to retire — say so
  in one line.
- **Degrade.** When the repository leaves `slot:docs` unfilled there is no home and no redirect
  convention: record that the pages could not be located and do **not** invent a path.

## Step 4: Tracker — no live mirror (the fleet projects it)

Do **not** mirror to the tracker from this command. `cancelled` is a **projected**
transition (see `tracking-and-execution.md` → its tracker-sync section): once the
status flip below merges to `main`, the `prd-projection` pass of the fleet's `corpus-sync`
loop (`fleet-service`) reads the generation that tick stored and moves the Issue to
**Canceled** at full fidelity within the sync's interval — not on merge, and not when CI
runs. Never read tracker state back.

## Step 5: Commit + PR (doc-only, branch + auto-merge)

This is a planning/doc change — no source code — but it still lands via a
throwaway branch + PR, same as code-bearing work (`main`'s required-check
protection binds every actor, with no exemption; nobody has a
direct-push path — `docs/ci-branch-protection.md` §0):

```
chore(NNNN): cancel — <one-line reason>
```

Create the branch `slot:git-workflow` names for a chore (or for the PRD, if its
tracker key is known), stage `prd.md` (and any feature-map or docs-page edit, including the
retirement redirect) — never the delivery
index, which is generated on demand and not committed — commit, and let the pre-commit
hook run `{{target:validate-knowledge}}` (it confirms the `cancelled_reason:` is present) — if
the hook fails, fix and re-commit, never `--no-verify`. Push, open the PR, and arm the
merge with `python3 knowledge/scripts/gh_automerge_arm.py` (delegate to `/zetify:push ship` if convenient).
Doc-only diffs typically clear the required checks quickly.

## Step 6: Report

Print: PRD NNNN cancelled, the reason, the PR URL and merge commit SHA, and that
the tracker issue moves to Canceled when the `prd-projection` pass of the fleet's
`corpus-sync` loop next projects `main` — within the sync's interval, not on merge (no
live mirror). If the
cancellation was because another PRD supersedes it, name that PRD as the
follow-on.

## Step 7: Headless - land it (the fleet runs this command too)

**The fleet dispatches this command when a person says a PRD is "not needed" on its page.** Closing the
tracker issue alone does not stick: the PRD projection re-reads `status:` from git every tick and reopens an
issue that git still reads as live, and no tracker field may decide a git status. So the page asks for this
command, and the cancellation is the pull request. Nobody is attached to a headless run, so:

- **There is nothing to ask.** The reason is the `instruction` of the brief's `## Shaping` block
  (`kind: prd`); use it verbatim as `cancelled_reason:` and skip Step 1. A block with no `instruction`, a
  block whose `kind` is not `prd`, or a PRD that does not exist is a refusal (`needs-decision`, no file, a
  summary a person can act on). A PRD already `cancelled` or `shipped` is a refusal as well: a headless run
  never cancels shipped work.
- **The branch is `agent/cancel-<key>`**, not `agent/shape-<key>` or `agent/design-<key>`: the PRD's fill
  and design may have merged under those names, and their merged PRs would read as this run's prior attempt.
  Find the prior attempt by the branch itself (`gh pr list --state all --head "agent/cancel-<key>"`
  and `git ls-remote --heads origin "agent/cancel-<key>"`); an open PR is the prior attempt, drive it.
- **Steps 2 to 5 are unchanged**: flip the frontmatter, reopen the capability gap, retire the pages, then
  commit and open the PR with the PRD's number and the word *cancel* in the title, and arm the merge the
  moment it opens (`gh pr merge --auto --squash`, never `--delete-branch`). Drive it to `state: MERGED`,
  not to green.
- **The `landed` result document** is written only over the merged PR, as `prd:plan` Step 8 writes it:
  `{kind: prd, id, href, pr, files, summary, changed: {status: cancelled}, open}`. The fleet confirms the
  cancellation when the served PRD reads `cancelled`, and the tracker issue closes from that, not from you.
  Write no tracker state.

A run that cannot bring its PR to merge is `partial`, and the next dispatch resumes the branch.

---

## Rules

- **A reason is mandatory** — never write `status: cancelled` without
  `cancelled_reason:` (the validator rejects it, and so should you).
- **Doc-only, but still a branch + PR** — cancellation carries no code, but it
  still ships via a throwaway branch + `gh pr merge --auto` like every other
  fleet commit; there is no direct-to-`main` path for the fleet identity.
- **Don't cancel `shipped` work** without explicit confirmation.
- **Cancelling is terminal** — to revive the idea later, write a *new* PRD with
  the next free number rather than un-cancelling this one.
