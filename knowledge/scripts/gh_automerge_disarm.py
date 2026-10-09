#!/usr/bin/env python3
"""Disarm GitHub auto-merge — and DEQUEUE a merge-queued PR — before pushing to an open PR.

PR #4185 merged into `main` while its force-pushed head SHA's required
`CI Success` check had no check-run at all yet — `merge-guard.yml` caught the
violation after the fact. `gh pr merge --auto`'s completion runs on an
asynchronous GitHub-side worker with a confirmed real-world gap (cli/cli#8514;
community reports of the async auto-merge completion path not reliably
re-validating required-status-check state before completing a merge). We
can't fix GitHub's worker — the fix on our side is to never let a force-push
land while `--auto` is armed: disarm first, push, then re-run the full
mergeable-precondition -> enable-auto-merge -> watch sequence
(the `push` command, step 6) from the top.

MERGE QUEUE (rehearsal on `mq-canary`, 2026-09-28). A PR in a merge queue reads
`autoMergeRequest: null`, so the old check printed "not armed — safe to push" on a PR at
queue position 3. And `gh pr merge --disable-auto` on a queued PR prints "already queued to
merge", exits 0 and does NOT dequeue. A queued PR's branch is LOCKED — every push is rejected
(`GH006` / HTTP 409 "Branches that are queued for merging cannot be updated") — so the push
this script clears the way for would fail. The only way out is GraphQL
`dequeuePullRequest(input:{id})`, which this script now runs, then re-reads: it never reports
"safe to push" while `mergeQueueEntry` is set. Identical behaviour on a branch with no queue.

Exit codes: 0 safe to push (nothing armed, nothing queued — confirmed by a re-read); 1 the PR
is still armed or queued after the attempt, or it already MERGED (never push onto a merged
PR's branch — open a new one); 2 usage / the PR could not be read.

Usage: python3 knowledge/scripts/gh_automerge_disarm.py <pr-number>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gh_pr_merge_state as mq  # noqa: E402 — the sibling shipped script, beside this one

DEQUEUE_MUTATION = "mutation($id:ID!){dequeuePullRequest(input:{id:$id}){clientMutationId}}"


def needs_disarm(pr_view: dict[str, Any]) -> bool:
    """True iff the PR is armed for auto-merge OR sits in a merge queue.

    A PR with no auto-merge request set reports `autoMergeRequest: null` (or the key may be
    absent entirely) — both mean nothing to disarm. But an ENQUEUED PR also reads
    `autoMergeRequest: null`, so the GraphQL `mergeQueueEntry` / `isInMergeQueue` fields are
    read too when present.
    """
    return bool(pr_view.get("autoMergeRequest")) or mq.is_queued(pr_view)


def dequeue(node_id: str, run: mq.GhRun | None = None) -> tuple[bool, str]:
    """Run `dequeuePullRequest` for the PR's node id. `(ok, detail)`."""
    run = run or mq.run_gh
    proc = run(["gh", "api", "graphql", "-f", f"query={DEQUEUE_MUTATION}", "-F", f"id={node_id}"])
    detail = (proc.stderr or proc.stdout or "").strip()[:300]
    if proc.returncode != 0:
        return False, detail
    try:
        errors = json.loads(proc.stdout or "{}").get("errors")
    except (json.JSONDecodeError, AttributeError):
        errors = None
    return not errors, detail


def disarm(pr: str, run: mq.GhRun | None = None) -> int:
    """Dequeue and/or disarm, then prove it with a re-read. Returns the exit code."""
    run = run or mq.run_gh
    try:
        state = mq.read_state(pr, run=run)
    except mq.ForgeReadError as exc:
        print(f"PR #{pr}: {exc} — NOT safe to push (state unknown).", file=sys.stderr)
        return 2
    if state.verdict == mq.MERGED:
        print(f"PR #{pr}: already MERGED — do not push onto its branch; open a new PR.", file=sys.stderr)
        return 1
    if not needs_disarm(state.pr):
        print(f"PR #{pr}: auto-merge not armed and not in a merge queue — safe to push.")
        return 0

    acted: list[str] = []
    if mq.is_queued(state.pr):
        ok, detail = dequeue(state.node_id, run=run)
        if not ok:
            print(f"PR #{pr}: dequeuePullRequest failed: {detail}", file=sys.stderr)
        acted.append("dequeued from the merge queue")
    if state.pr.get("autoMergeRequest"):
        proc = run(["gh", "pr", "merge", pr, "--disable-auto"])
        if proc.returncode != 0:
            print(f"PR #{pr}: --disable-auto failed: {(proc.stderr or '').strip()[:300]}", file=sys.stderr)
        acted.append("auto-merge disarmed")

    try:
        after = mq.read_state(pr, run=run)
    except mq.ForgeReadError as exc:
        print(f"PR #{pr}: could not confirm the disarm ({exc}) — NOT safe to push.", file=sys.stderr)
        return 1
    if after.verdict == mq.MERGED:
        print(f"PR #{pr}: MERGED before it could be disarmed — do not push; open a new PR.", file=sys.stderr)
        return 1
    if needs_disarm(after.pr):
        still = "still QUEUED" if mq.is_queued(after.pr) else "still ARMED"
        print(f"PR #{pr}: {still} after the attempt — NOT safe to push. Retry, or dequeue by hand.", file=sys.stderr)
        return 1
    print(
        f"PR #{pr}: WAS {'queued' if mq.is_queued(state.pr) else 'armed'} — {' and '.join(acted)} before push. "
        "Re-run the full precondition -> enable-auto-merge -> watch sequence after pushing."
    )
    return 0


def main(argv: list[str] | None = None, run: mq.GhRun | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: gh_automerge_disarm.py <pr-number>", file=sys.stderr)
        return 2
    return disarm(args[0], run=run)


if __name__ == "__main__":
    raise SystemExit(main())
