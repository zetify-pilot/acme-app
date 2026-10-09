#!/usr/bin/env python3
"""Where a pull request stands on its way to `main` — with or without a merge queue.

    gh_pr_merge_state.py <pr>                      # read once, print the verdict, exit by it
    gh_pr_merge_state.py <pr> --watch [--interval S] [--timeout S]

WHY THIS EXISTS. A merge queue changes what "armed" and "failed" look like, and every signal
the fleet read before reads wrong under one (rehearsal on a platform lane's `mq-canary`
branch, 2026-09-28):

* **Queued** — `gh pr merge --auto` on a green PR ENQUEUES it, and an enqueued PR reads
  `autoMergeRequest: null`. The only evidence is GraphQL `mergeQueueEntry` / `isInMergeQueue`,
  which `gh pr view --json` does not expose. A queued PR is PENDING — neither done nor failed —
  and its branch is LOCKED: a push is rejected (`GH006` / HTTP 409 "Branches that are queued for
  merging cannot be updated") until the PR is dequeued (`gh_automerge_disarm.py`).
* **Removed from the queue** — the queue builds a `merge_group` commit (the PR on top of the
  queue ahead of it) and runs the required checks THERE. When that run goes red the PR is
  ejected, and afterwards reads OPEN / `mergeStateStatus: CLEAN` / `autoMergeRequest: null` /
  `mergeQueueEntry: null`, with every required check on the PR head still green. Every reading
  the fleet took before says "green, simply not armed". The only evidence is a
  `RemovedFromMergeQueueEvent` on the timeline (its `reason`, e.g. `failed_checks`) and the red
  check-runs on that event's `beforeCommit` — the `merge_group` SHA. `gh pr checks --watch`
  never sees them: they are not on the PR head.

So this script reads the one GraphQL shape that carries all of it and names ONE verdict:

* `merged` (exit 0) — terminal. Done.
* `armed` (exit 10) — pending: auto-merge is armed; GitHub merges (or enqueues) the PR when
  its checks go green. Keep watching.
* `queued` (exit 10) — pending: in the merge queue. Keep watching. NEVER push to it — dequeue
  first. A live `isInMergeQueue`/`mergeQueueEntry` read can lag the timeline while the queue
  completes a merge group (and a successful queue merge emits no removal event), so a PR whose
  LAST queue event is an add — or a removal for the queue's own merge — is still `queued`, never
  `unarmed`.
* `conflicting` (exit 3) — `CONFLICTING` / `DIRTY`: rebase onto `origin/main`, push, re-arm.
* `ejected` (exit 4) — removed from the queue for a reason other than a merge or a manual
  dequeue. Treat it as RED CI: read `failing` (the red `merge_group` checks), fix at the root
  cause, push, re-arm.
* `unarmed` (exit 5) — open with nothing armed and nothing queued: nothing will ever merge
  it. Arm it (`gh_automerge_arm.py`).
* `closed` (exit 6) — closed without merging.
* exit 2 — usage error, or the forge could not be read: never a verdict.

It works identically on a branch with no queue: `queued` and `ejected` simply never occur there.

`--watch` blocks in the foreground, re-reading every `--interval` seconds (default 120, floor
30), and returns on the first verdict that is not pending. Declare the wait first (the
mission's blocked-file protocol) — a queue build runs 30-60 minutes.

Stdlib only; `gh` is the only thing it runs, and no credential ever rides argv (`gh` reads its
own token from the environment).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable
from typing import Any, Final, NamedTuple

MERGED: Final = "merged"
ARMED: Final = "armed"
QUEUED: Final = "queued"
CONFLICTING: Final = "conflicting"
EJECTED: Final = "ejected"
UNARMED: Final = "unarmed"
CLOSED: Final = "closed"

#: Verdicts that mean "nothing to do yet — keep watching".
PENDING: Final = frozenset({ARMED, QUEUED})

EXIT_CODES: Final[dict[str, int]] = {
    MERGED: 0,
    ARMED: 10,
    QUEUED: 10,
    CONFLICTING: 3,
    EJECTED: 4,
    UNARMED: 5,
    CLOSED: 6,
}
EXIT_ERROR: Final = 2

#: `RemovedFromMergeQueueEvent.reason` values that are NOT a failure. `merged` is the queue's
#: own success; `manual` is a person (or `gh_automerge_disarm.py`) dequeuing on purpose — the
#: PR is then simply unarmed. Anything else (`failed_checks`, a merge conflict with the queue
#: ahead of it, a timeout, …) is an ejection, compared case-insensitively.
BENIGN_REMOVALS: Final = frozenset({"merged", "manual"})

#: Check-run conclusions that do not block — mirrors `gh_automerge_arm.PASSING_CONCLUSIONS`.
PASSING_CONCLUSIONS: Final = frozenset({"success", "skipped", "neutral"})

QUERY: Final = (
    "query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){"
    "pullRequest(number:$number){id number state isDraft headRefOid mergeable mergeStateStatus "
    "isInMergeQueue autoMergeRequest{enabledAt mergeMethod} "
    "mergeQueueEntry{state position enqueuedAt} "
    "timelineItems(last:20,itemTypes:[ADDED_TO_MERGE_QUEUE_EVENT,REMOVED_FROM_MERGE_QUEUE_EVENT]){"
    "nodes{__typename ... on AddedToMergeQueueEvent{createdAt} "
    "... on RemovedFromMergeQueueEvent{createdAt reason beforeCommit{oid}}}}}}}"
)

#: The runner every `gh` call goes through; tests inject a scripted fake (stdlib only).
GhRun = Callable[[list[str]], subprocess.CompletedProcess[str]]


def run_gh(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False)


class ForgeReadError(RuntimeError):
    """The PR could not be read. Never a verdict: the caller must not guess either way."""


class Removal(NamedTuple):
    """The last time the queue let go of this PR without merging it."""

    reason: str
    at: str
    merge_group_sha: str


class MergeState(NamedTuple):
    verdict: str
    pr: dict[str, Any]
    removal: Removal | None

    @property
    def node_id(self) -> str:
        return str(self.pr.get("id") or "")

    @property
    def queue(self) -> dict[str, Any] | None:
        entry = self.pr.get("mergeQueueEntry")
        return entry if isinstance(entry, dict) else None


def is_queued(pr: dict[str, Any]) -> bool:
    """Whether the PR sits in a merge queue now. Either field suffices — both are GitHub's."""
    return bool(pr.get("mergeQueueEntry")) or pr.get("isInMergeQueue") is True


def queue_events(pr: dict[str, Any]) -> list[dict[str, Any]]:
    """The PR's merge-queue events, oldest first, as the timeline carries them — or `[]`."""
    items = pr.get("timelineItems")
    nodes = items.get("nodes") if isinstance(items, dict) else None
    if not isinstance(nodes, list):
        return []
    return [n for n in nodes if isinstance(n, dict) and n.get("__typename")]


def still_queue_owned(pr: dict[str, Any]) -> bool:
    """Whether the queue's own durable record still holds the PR, even though the live fields do not.

    A live `isInMergeQueue`/`mergeQueueEntry` read can lag the timeline while the queue builds and
    lands a merge group, and a successful queue merge emits no `RemovedFromMergeQueueEvent` at all
    (measured 2026-10-01: six queued PRs read `unarmed` in one pass and all merged minutes later —
    ). So a PR whose LAST queue event is an `AddedToMergeQueueEvent` (never removed), or a
    `RemovedFromMergeQueueEvent` whose reason is the queue's own merge, is still QUEUED.
    """
    events = queue_events(pr)
    if not events:
        return False
    last = events[-1]
    kind = last.get("__typename")
    if kind == "AddedToMergeQueueEvent":
        return True
    if kind == "RemovedFromMergeQueueEvent":
        return str(last.get("reason") or "").strip().lower() == "merged"
    return False


def last_removal(pr: dict[str, Any]) -> Removal | None:
    """The live ejection: the LAST queue event, when it is a removal that was not benign.

    An `AddedToMergeQueueEvent` after the removal supersedes it (the PR went back in), so only
    the final queue event counts. `None` when the PR never left the queue badly.
    """
    events = queue_events(pr)
    if not events:
        return None
    last = events[-1]
    if last.get("__typename") != "RemovedFromMergeQueueEvent":
        return None
    reason = str(last.get("reason") or "").strip()
    if reason.lower() in BENIGN_REMOVALS:
        return None
    before = last.get("beforeCommit")
    sha = str(before.get("oid") or "") if isinstance(before, dict) else ""
    return Removal(reason=reason or "unknown", at=str(last.get("createdAt") or ""), merge_group_sha=sha)


def classify(pr: dict[str, Any]) -> MergeState:
    """The one verdict for a GraphQL `pullRequest` node. **PURE.**

    Order matters and is the whole design: a terminal state first, then the pending states
    (a PR that is queued or armed again is no longer "ejected", whatever its history says),
    then a conflict (it can merge nothing), then the ejection, and only then "unarmed".

    A PR whose live queue fields lag the timeline — `isInMergeQueue: false` / no
    `mergeQueueEntry` while the last queue event is an add, or a removal for the queue's own
    merge — is still pending: it reads QUEUED rather than UNARMED, which would otherwise park a
    fix the queue was about to land.
    """
    state = str(pr.get("state") or "").upper()
    if state == "MERGED":
        return MergeState(MERGED, pr, None)
    if state == "CLOSED":
        return MergeState(CLOSED, pr, None)
    if is_queued(pr) or still_queue_owned(pr):
        return MergeState(QUEUED, pr, None)
    if pr.get("mergeable") == "CONFLICTING" or pr.get("mergeStateStatus") == "DIRTY":
        return MergeState(CONFLICTING, pr, last_removal(pr))
    if pr.get("autoMergeRequest"):
        return MergeState(ARMED, pr, None)
    removal = last_removal(pr)
    if removal is not None:
        return MergeState(EJECTED, pr, removal)
    return MergeState(UNARMED, pr, None)


def fetch_pr(pr: str, run: GhRun | None = None) -> dict[str, Any]:
    """The PR's merge-relevant GraphQL node, for the repo `gh` resolves (cwd or `GH_REPO`)."""
    run = run or run_gh
    try:
        number = int(pr.lstrip("#"))
    except ValueError as exc:
        raise ForgeReadError(f"not a PR number: {pr!r}") from exc
    proc = run(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={QUERY}",
            "-F",
            "owner={owner}",
            "-F",
            "name={repo}",
            "-F",
            f"number={number}",
        ]
    )
    if proc.returncode != 0:
        raise ForgeReadError(f"PR #{number} could not be read: {(proc.stderr or proc.stdout or '').strip()[:300]}")
    try:
        body = json.loads(proc.stdout)
        node = body["data"]["repository"]["pullRequest"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ForgeReadError(f"PR #{number}: unexpected GraphQL answer ({exc})") from exc
    if not isinstance(node, dict):
        raise ForgeReadError(f"PR #{number} not found")
    return node


def read_state(pr: str, run: GhRun | None = None) -> MergeState:
    return classify(fetch_pr(pr, run=run))


def failing_checks(sha: str, run: GhRun | None = None) -> list[str]:
    """The red check-runs on a commit — for an ejection, the `merge_group` SHA the queue built.

    Returns `["<name>: <conclusion> <url>"]`, latest completed run per name. An unreadable
    answer is reported as one line saying so rather than as "nothing failed".
    """
    if not sha:
        return ["(the removal event named no merge_group commit — read the PR timeline by hand)"]
    run = run or run_gh
    proc = run(
        [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/commits/{sha}/check-runs?per_page=100",
            "--jq",
            "[.check_runs[] | {id, name, conclusion, html_url}]",
        ]
    )
    if proc.returncode != 0:
        return [f"(check-runs on {sha[:12]} could not be read: {(proc.stderr or '').strip()[:200]})"]
    try:
        runs = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return [f"(check-runs on {sha[:12]} returned non-JSON)"]
    latest: dict[str, dict[str, Any]] = {}
    for r in runs if isinstance(runs, list) else []:
        if not isinstance(r, dict) or r.get("conclusion") is None:
            continue
        name = str(r.get("name") or "")
        if name and (name not in latest or int(r.get("id") or 0) >= int(latest[name].get("id") or 0)):
            latest[name] = r
    return [
        f"{name}: {r.get('conclusion')} {r.get('html_url') or ''}".rstrip()
        for name, r in sorted(latest.items())
        if r.get("conclusion") not in PASSING_CONCLUSIONS
    ]


def describe(pr: str, ms: MergeState, failing: list[str] | None = None) -> str:
    """One human line (plus the failing checks for an ejection)."""
    p = ms.pr
    if ms.verdict == MERGED:
        return f"PR #{pr}: MERGED."
    if ms.verdict == QUEUED:
        q = ms.queue or {}
        return (
            f"PR #{pr}: QUEUED in the merge queue (entry {q.get('state')}, position {q.get('position')}, "
            f"enqueued {q.get('enqueuedAt')}) — pending. The branch is locked: dequeue "
            "(gh_automerge_disarm.py) before any push."
        )
    if ms.verdict == ARMED:
        return f"PR #{pr}: auto-merge ARMED ({p.get('mergeStateStatus')}) — pending."
    if ms.verdict == CONFLICTING:
        return (
            f"PR #{pr}: CONFLICTING (mergeable={p.get('mergeable')}, mergeStateStatus={p.get('mergeStateStatus')}) "
            "— rebase onto origin/main, push, re-arm."
        )
    if ms.verdict == EJECTED:
        r = ms.removal
        assert r is not None
        lines = [
            f"PR #{pr}: REMOVED FROM THE MERGE QUEUE (reason {r.reason!r} at {r.at}, merge_group commit "
            f"{r.merge_group_sha[:12] or '?'}). The PR's own checks may all read green — the red run is on "
            "the merge_group commit. Treat it as red CI: fix at the root cause (often a semantic clash "
            "with a PR merged ahead of it — rebase onto origin/main first), push, then re-arm."
        ]
        for f in failing or []:
            lines.append(f"  - {f}")
        return "\n".join(lines)
    if ms.verdict == UNARMED:
        return f"PR #{pr}: OPEN with nothing armed and nothing queued — nothing will merge it. Arm it."
    return f"PR #{pr}: CLOSED without merging."


def _as_json(pr: str, ms: MergeState, failing: list[str]) -> str:
    p = ms.pr
    return json.dumps(
        {
            "pr": pr,
            "verdict": ms.verdict,
            "state": p.get("state"),
            "head": p.get("headRefOid"),
            "mergeable": p.get("mergeable"),
            "mergeStateStatus": p.get("mergeStateStatus"),
            "autoMergeRequest": p.get("autoMergeRequest"),
            "mergeQueueEntry": ms.queue,
            "removal": ms.removal._asdict() if ms.removal else None,
            "failing": failing,
        }
    )


def main(
    argv: list[str] | None = None,
    run: GhRun | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("pr", help="the pull request number")
    ap.add_argument("--watch", action="store_true", help="block until the verdict is no longer pending")
    ap.add_argument("--interval", type=int, default=120, help="seconds between reads under --watch (floor 30)")
    ap.add_argument("--timeout", type=int, default=5400, help="seconds before --watch gives up (default 90 min)")
    ap.add_argument("--json", action="store_true", help="also print one JSON line with the whole reading")
    args = ap.parse_args(argv)

    deadline = monotonic() + args.timeout
    while True:
        try:
            ms = read_state(args.pr, run=run)
        except ForgeReadError as exc:
            print(f"gh_pr_merge_state: {exc}", file=sys.stderr)
            return EXIT_ERROR
        if not args.watch or ms.verdict not in PENDING or monotonic() >= deadline:
            break
        sleep(max(30, args.interval))

    failing = failing_checks(ms.removal.merge_group_sha, run=run) if ms.verdict == EJECTED and ms.removal else []
    print(describe(args.pr, ms, failing))
    if args.watch and ms.verdict in PENDING:
        print(f"gh_pr_merge_state: still {ms.verdict} after {args.timeout}s — keep watching", file=sys.stderr)
    if args.json:
        print(_as_json(args.pr, ms, failing))
    return EXIT_CODES[ms.verdict]


if __name__ == "__main__":
    raise SystemExit(main())
