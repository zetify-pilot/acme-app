#!/usr/bin/env python3
"""Which required status checks have NO check-run on a PR's head SHA.

A required context that has never reported on the head blocks the merge
FOREVER, and it is invisible: `mergeable: MERGEABLE`, `mergeStateStatus:
BLOCKED`, and zero *failing* checks. It looks exactly like "CI is still
running", so nobody looks.

WHY IT HAPPENS. GitHub dispatches a `pull_request` workflow only on that PR's
own events (`opened` / `synchronize` / `reopened`). A workflow that became
REQUIRED after the head's last such event has never run on that SHA and never
will — nothing re-dispatches it on its own. `main` runs
`required_status_checks.strict = false`, so no PR is ever forced up to date
either; a stale-base head simply sits there.

Observed 2026-08-27: `Workflow Size Guard` (required 03:50Z) and `No
GitHub-hosted runners (runs-on guard)` (required 04:52Z) stranded 14 of the 25
open PRs at once, including PRs that were verified and armed for auto-merge.
Auto-merge does not fire through it and never reports why.

THE POINT OF DETECTING IT SEPARATELY. The remedy — an empty commit, so a fresh
`synchronize` dispatches every currently-required workflow — must be
CONDITIONAL. In steady state every head is pushed after the requirement already
exists and reports normally, so this returns "nothing missing" and costs
nothing. Pushing an empty commit unconditionally would buy one full CI cycle
per verified PR on a 4-runner heavy pool in exchange for nothing.

Deliberately narrow: this asks only whether a check-run for the context EXISTS
on the head. A context that is present and pending, failing, or skipped is a
different problem with a different fix (wait, or fix the build) — never an
empty commit.

WHY AN EMPTY COMMIT, AND NOT THE TWO CHEAPER-LOOKING LEVERS.

`workflow_dispatch` on the guard, dispatched against the PR head, WOULD work
mechanically — that was measured, not assumed. Run 33027144305 (event
`workflow_dispatch`, branch `agent/fix-eng-8321`) produced a check-run named
`CI Success`, conclusion `success`, app_id 15368, on head SHA 0fa3b853, and
GitHub itself linked the run to PR #8963. Branch protection matches a required
context by (app_id, context name) on the head SHA and applies no event filter,
so a dispatched run does satisfy a required context.

It is rejected anyway, on correctness. A `pull_request` run checks out
`refs/pull/N/merge` — the POST-merge tree. A `workflow_dispatch` run checks out
the branch head — the PRE-merge tree. `workflow-size-guard.yml`'s rule 2 says
in as many words that it must measure the post-merge file, "because two
branches that each land under budget can sum to over it", and ci.yml sits ~1.3
KB under the 510,000-byte hard fail today. A dispatch-satisfied Workflow Size
Guard would therefore green-light exactly the PR the guard exists to stop, and
would hand every agent a way to satisfy a required check with a strictly weaker
evaluation than the required one. That is making the check non-required wearing
a disguise.

Close-and-reopen is the other lever that leaves the head SHA untouched, and
`reopened` is in `pull_request`'s default type set, so it re-dispatches the
guards with the correct merge-ref checkout. It costs the same as an empty
commit — ci.yml is also `on: pull_request` with default types, so it reruns
either way — while adding a side effect an empty commit does not have: closing
a PR is a state change the GitHub<->Linear integration reacts to, on issues
this fleet's dispatch depends on.

So the empty commit wins on being the only option that changes nothing except
which workflows get dispatched. Its one cost — a full CI cycle — is bounded by
making it CONDITIONAL (see above); in steady state it never fires.

Usage: python3 knowledge/scripts/pr_missing_required_contexts.py <pr-number> [base-branch]

Exit 0 — nothing to self-heal: either every required context has a check-run,
         or the head has not settled yet and the honest answer is "wait".
Exit 1 — one or more required contexts structurally cannot arrive; each is
         printed, one per line, to stdout. This is the empty-commit case.
Exit 2 — usage error.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any


def rollup_context_names(rollup: list[dict[str, Any]]) -> set[str]:
    """The context names present on the head, whatever their state.

    `statusCheckRollup` mixes two shapes: a CheckRun (GitHub Actions, keyed by
    `name`) and a StatusContext (the legacy commit-status API, keyed by
    `context`). Both can satisfy a required context, so both are collected.
    """
    names: set[str] = set()
    for node in rollup:
        name = node.get("name") or node.get("context")
        if name:
            names.add(str(name))
    return names


def missing_contexts(required: list[str], rollup: list[dict[str, Any]]) -> list[str]:
    """Required contexts with no check-run at all on the head, sorted.

    Raw set difference, not a state judgement — see the module docstring on why
    a present-but-pending context is deliberately NOT reported here. Callers
    that are about to ACT on the answer want `actionable_missing()`, which adds
    the two guards that keep this from firing on a head CI has merely not
    caught up with yet.
    """
    present = rollup_context_names(rollup)
    return sorted(c for c in required if c not in present)


def _settled(node: dict[str, Any]) -> bool:
    """Has this rollup node reached a terminal state?

    Three shapes reach this, and reading the wrong field on any of them is a
    silent wrong answer:

    * **`gh pr view --json statusCheckRollup` CheckRun** — `status` is
      QUEUED / IN_PROGRESS / COMPLETED and `conclusion` is the **empty string**
      until it completes. NOT null. An `is not None` test on `conclusion`
      therefore reads every queued job as finished — which is precisely how the
      first cut of this script reported 21 of 25 live PRs as stranded while
      their CI was merely still running.
    * **StatusContext** (legacy commit statuses) — carries `state`, PENDING or
      EXPECTED while in flight.
    * **REST `/check-runs`** — carries both `status` and a genuinely null
      `conclusion`.

    Checked in that order, falling through to a truthiness test on
    `conclusion`, so an empty string can never be mistaken for a verdict.
    """
    status = node.get("status")
    if status:
        return str(status).upper().startswith("COMPLETED")
    state = node.get("state")
    if state:
        return str(state).upper() not in {"PENDING", "EXPECTED"}
    return bool(node.get("conclusion"))


def actionable_missing(required: list[str], rollup: list[dict[str, Any]]) -> list[str]:
    """Missing required contexts that an empty-commit self-heal should act on.

    Two guards separate the shape from things that merely LOOK like
    it, because acting on either of those would push a pointless commit (and,
    on a verified PR, a pointless full CI cycle):

    1. **At least one required context must already be present.** A head pushed
       seconds ago has no check-runs at all, so a bare set difference reports
       *every* requirement as missing. That is the "mergeable but zero checks"
       case `push.md` step 6 already handles by waiting or re-dispatching
       ci.yml — a different symptom with a different fix.
    2. **Every node in the rollup must have settled — not merely the required
       ones.** This is the guard that matters, and the narrower version of it
       is wrong: `CI Success` is ci.yml's terminal aggregating job, so it has
       no check-run at all while the ~40 jobs it waits on are still running.
       Judging only the *required* contexts, a PR mid-CI reads as "the fast
       `Workflow Size Guard` settled, therefore `CI Success` can never
       arrive" — which is false for every PR in flight. Measured on the live
       board 2026-08-27: that narrower rule flagged 21 of 25 open PRs as
       stranded on `CI Success`, all but one of them simply mid-run.

    Only when the whole head has gone quiet AND a required context still has no
    check-run is that context structurally unable to arrive.
    """
    missing = missing_contexts(required, rollup)
    if not missing:
        return []
    if not any((n.get("name") or n.get("context")) in set(required) for n in rollup):
        return []
    if not all(_settled(n) for n in rollup):
        return []
    return missing


def fetch_required_contexts(base: str) -> list[str]:
    out = subprocess.check_output(
        [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/branches/{base}/protection",
            "--jq",
            ".required_status_checks.contexts[]?",
        ]
    )
    return [line for line in out.decode().splitlines() if line.strip()]


def fetch_rollup(pr: str) -> list[dict[str, Any]]:
    out = subprocess.check_output(["gh", "pr", "view", pr, "--json", "statusCheckRollup"])
    parsed: dict[str, Any] = json.loads(out)
    return list(parsed.get("statusCheckRollup") or [])


def main() -> int:
    if not 2 <= len(sys.argv) <= 3:
        print("usage: pr_missing_required_contexts.py <pr-number> [base-branch]", file=sys.stderr)
        return 2
    pr = sys.argv[1]
    base = sys.argv[2] if len(sys.argv) == 3 else "main"

    missing = actionable_missing(fetch_required_contexts(base), fetch_rollup(pr))
    if not missing:
        return 0
    for context in missing:
        print(context)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
