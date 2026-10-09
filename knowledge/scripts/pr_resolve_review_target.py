#!/usr/bin/env python3
"""Resolve the review target for a `verify` session.

WHY THIS EXISTS. A `verify` session identifies its review target by the PR
*head ref* (branch existence). When the PR under review merges while the session is
running, its branch is deleted, so a head-ref lookup finds nothing and the session
reports a spurious failure — *"no merged PR found whose head is <branch>"* — against
work that was actually fine. Branch existence is the wrong identity for a
review target: a PR's **number** and its **merge commit** SHA both survive branch
deletion.

THE FIX IS PR-NUMBER / MERGE-COMMIT IDENTITY. This module owns the decision rules that
resolve an issue to its review target and classify the terminal state, so the verify
command can:
  * resolve by PR number / merge commit rather than by head-ref lookup;
  * treat *"the PR merged while I was running"* as a distinct, **non-failing** terminal
    state (`merged`) — not as a missing-branch error;
  * reserve `none` (no PR ever existed) for a genuine BLOCKED.
The `classify` rules are pure and unit-tested; the `resolve` CLI shells out to `gh`.

a PR *number* is not unique across GitHub orgs/repos. `gh pr view 146` in
the caller's repo can return a foreign merged PR that merely *mentions* the issue key
(`<org>/<platform>` #146 vs `<org>/<apps>` #146). `--repo` selects the lane;
`--pr` still refuses a PR whose head-ref/title is not linked to the key.

a COUPLED change has two review targets. A change authored in the fleet
repository's `commandtree/` reaches a consuming repository as a submodule pin bump, so the
same issue is bound to a fleet PR AND a consuming-repo pin PR. Resolving ONE target merged
the pin against an unmerged fleet PR, leaving the pin at a head fleet `main` never makes
reachable. `classify_coupled` classifies the session's own lane and
reports `bound` while a linked PR in another lane is still open, so a session cannot merge
one half of a coupled change alone.

Scope: deliberately shared — a bug/task/cleanup verify (`verify`) and a PRD
verify both benefit; the identity rule is the same for either.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

# Terminal states a verify session can reach for its review target.
STATE_OPEN = "open"  # an open PR exists — continue the normal review against it
STATE_MERGED = "merged"  # the PR merged (branch gone) — NON-FAILING terminal, work landed
STATE_NONE = "none"  # no PR exists at all — a genuine BLOCKED, never a spurious failure
# A COUPLED change has more than one review target: a change authored in the fleet
# repository's `commandtree/` reaches a consuming repository as a submodule pin bump, so the
# SAME issue is bound to a fleet PR AND a consuming-repo pin PR. While any of those other
# halves is unmerged, this half may not be certified — the coupled change is not whole yet.
STATE_BOUND = "bound"

# A `repo:<name>` label is the lane and resolves to `<org>/<name>` — every lane lives in
# this checkout's GitHub org (`_repo.lane_slug`); absence is the default (caller) repo. The
# fleet's lane table (`fleet-service`'s `lanes.py`) spells the same rule.
REPO_LANE_PREFIX = "repo:"

_PR_JSON_FIELDS = "number,state,headRefName,mergeCommit,title"

USAGE = (
    "usage: pr_resolve_review_target.py resolve <KEY> [--pr <N>] [--repo <owner/name>]...\n"
    "resolves an issue to its review target by PR number / merge commit and\n"
    "prints {state: open|merged|bound|none, pr, head_ref, merge_commit, bound, primary}\n"
    "(a coupled change is `bound` while a linked PR in another lane is unmerged)"
)


class UnlinkedPRError(RuntimeError):
    """`--pr N` resolved a PR that is not linked to the issue key."""


def classify(prs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Resolve an issue to its review target and classify the terminal state.

    `prs` is a list of gh-style PR dicts with keys:
        number, state ("OPEN"|"MERGED"|"CLOSED"), headRefName,
        mergeCommit ({"oid": str} | None)

    Branch existence is deliberately NOT used — a review target's identity is its PR
    number / merge commit, both of which survive branch deletion.

    Returns {"pr", "state", "head_ref", "merge_commit"} with state ∈
    {"open", "merged", "none"}:
      * "open"   — an OPEN PR is the active review target; carry its head ref.
      * "merged" — the PR merged; this is the NON-FAILING terminal state. A verify
                   session must report it as success, never as a missing-branch failure.
      * "none"   — no target exists; a genuine BLOCKED.
    An open PR takes precedence over a merged one (the active review is the open PR).
    """
    open_prs = [p for p in prs if p.get("state") == "OPEN"]
    if open_prs:
        p = open_prs[0]
        return {
            "pr": p.get("number"),
            "state": STATE_OPEN,
            "head_ref": p.get("headRefName"),
            "merge_commit": None,
        }

    merged_prs = [p for p in prs if p.get("state") == "MERGED"]
    if merged_prs:
        # Prefer a merged PR that actually reports a merge commit when several exist.
        with_commit = [p for p in merged_prs if (p.get("mergeCommit") or {}).get("oid")]
        p = (with_commit or merged_prs)[0]
        mc = p.get("mergeCommit") or {}
        return {
            "pr": p.get("number"),
            "state": STATE_MERGED,
            "head_ref": p.get("headRefName"),
            "merge_commit": mc.get("oid"),
        }

    return {"pr": None, "state": STATE_NONE, "head_ref": None, "merge_commit": None}


def classify_coupled(
    prs_by_repo: Mapping[str, Iterable[dict[str, Any]]],
    primary_repo: str,
) -> dict[str, Any]:
    """Resolve a COUPLED change to its review target, refusing to call one half whole.

    A coupled change ships in two repositories: a fleet `commandtree/` change whose PR lives
    in the fleet repository, and the consuming repo's PR that bumps the `fleet/` submodule pin
    to the fleet PR's squash commit. A verify session resolves ONE target, so the two halves
    were merged independently and the pin PR could merge while its fleet PR was still open —
    the exact strand record (7 of the last 8 fleet pins sat off fleet
    `main`). This resolver treats the change as TWO targets: it classifies the session's own
    lane (`primary_repo`) with `classify`, and any OPEN linked PR in another lane is a BOUND
    half. While a bound half is unmerged the whole change is not whole, so `state` is
    `"bound"` — never `open`/`merged` for the local half alone.

    `prs_by_repo` maps a GitHub `owner/name` lane to that lane's linked PR dicts (the same
    shape `classify` takes). Returns the primary classification, extended with:
      * `"bound"`   — the unmerged other halves, each `{repo, pr, head_ref, merged}`;
      * `"primary"` — the local lane's own `classify` result, unaltered;
    and `state == "bound"` whenever `bound` is non-empty. A single-lane call (the normal
    case) has no other lanes, so `bound` is empty and the result is `classify` unchanged.
    """
    primary = classify(prs_by_repo.get(primary_repo, []))
    bound: list[dict[str, Any]] = []
    for repo, prs in prs_by_repo.items():
        if repo == primary_repo:
            continue
        other = classify(prs)
        if other["state"] == STATE_OPEN:
            bound.append(
                {
                    "repo": repo,
                    "pr": other["pr"],
                    "head_ref": other["head_ref"],
                    "merged": False,
                }
            )
    result: dict[str, Any] = dict(primary)
    result["bound"] = bound
    result["primary"] = primary
    if bound:
        result["state"] = STATE_BOUND
    return result


def linked_to_key(pr: dict[str, Any], key: str) -> bool:
    """True iff the PR's head-ref or title carries `key` as a token.

    A body *mention* is not linkage — that is how a foreign same-number PR becomes a
    false `merged` terminal. Matching is case-insensitive and bounded (`` does
    not match ``).
    """
    needle = (key or "").strip()
    if not needle:
        return False
    pat = re.compile(r"\b" + re.escape(needle) + r"\b", re.IGNORECASE)
    return any(pat.search(str(pr.get(field) or "")) for field in ("headRefName", "title"))


def repo_from_lane_labels(labels: Iterable[str]) -> str | None:
    """GitHub `owner/name` for the first `repo:*` lane label, else None (caller repo)."""
    names = lane_names_from_labels(labels)
    return _repo.lane_slug(f"{REPO_LANE_PREFIX}{names[0]}") if names else None


def lane_names_from_labels(labels: Iterable[str]) -> list[str]:
    """Every `repo:*` lane NAME (without the prefix), in label order and deduplicated.

    A coupled change carries more than one lane: the issue is bound to a fleet PR and to the
    consuming repo's pin PR. Returning every lane — not the first — is what lets
    `classify_coupled` see both halves; returning only the first is the shape that merged one
    half of.
    """
    names: list[str] = []
    for name in labels:
        if name.startswith(REPO_LANE_PREFIX):
            lane = name.removeprefix(REPO_LANE_PREFIX).strip()
            if lane and lane not in names:
                names.append(lane)
    return names


def repos_from_lane_labels(labels: Iterable[str]) -> list[str]:
    """Every `repo:*` lane as a GitHub `owner/name` slug, in label order (deduplicated).

    Empty when the issue names no lane, which means "the caller's repo" — the same default
    `repo_from_lane_labels` returns None for.
    """
    return [_repo.lane_slug(f"{REPO_LANE_PREFIX}{name}") for name in lane_names_from_labels(labels)]


# ── CLI ──────────────────────────────────────────────────────────────────────
# `resolve <KEY>`: resolve an issue to its review target via `gh`, using the PR
# number / merge commit identity above. The verify command runs this at Step 1
# (resolve) and Step 3 (checkout) instead of a bare head-ref lookup.
# `--repo` is required: the caller passes `get_issue`'s `lane.repo` (PRD 0819 D5).


def _gh_cmd(args: list[str], repo: str | None) -> list[str]:
    cmd = ["gh", *args]
    if repo:
        cmd += ["--repo", repo]
    return cmd


def _fetch_linked(key: str, pr_number: str | None, repo: str | None) -> list[dict[str, Any]]:
    """Linked PRs for `key` in `repo`: the specific `pr_number` (refused unless linked), or
    every PR whose head-ref/title carries the key."""
    if pr_number:
        out = subprocess.check_output(_gh_cmd(["pr", "view", pr_number, "--json", _PR_JSON_FIELDS], repo))
        pr = json.loads(out)
        if not linked_to_key(pr, key):
            raise UnlinkedPRError(
                f"PR #{pr.get('number')} (head={pr.get('headRefName')!r} "
                f"title={pr.get('title')!r}) is not linked to {key} "
                f"(need {key} in head-ref or title); refusing foreign PR (ENG-9984). "
                f"Pass --repo <owner/name> if the review target lives on another lane."
            )
        return [pr]
    out = subprocess.check_output(
        _gh_cmd(
            ["pr", "list", "--search", key, "--state", "all", "--json", _PR_JSON_FIELDS],
            repo,
        )
    )
    return [p for p in json.loads(out) if linked_to_key(p, key)]


def resolve(key: str, pr_number: str | None = None, repo: str | None = None) -> dict[str, Any]:
    """Resolve `key` (Linear issue) to its review target, preferring `pr_number` when
    the session already knows the specific PR it is reviewing.

    `repo` is a GitHub `owner/name` (the issue's `repo:*` lane). Omitted → the
    caller's repo, which is the default lane.

    Single-lane only; for a coupled change use `resolve_coupled`, which enumerates every lane
    the issue names and refuses a half while another half is unmerged.
    """
    return classify(_fetch_linked(key, pr_number, repo))


def resolve_coupled(
    key: str,
    pr_number: str | None = None,
    primary_repo: str | None = None,
    lane_repos: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Resolve a coupled change: classify `primary_repo` and every other `lane_repos` lane.

    `primary_repo` is the lane whose PR the session is reviewing (the issue's `repo:*` lane
    for its own lane, else the caller repo). `lane_repos` is every lane the issue names; each
    is searched for linked PRs (a specific `pr_number` only applies to `primary_repo`). The
    result is `classify_coupled`'s: `state == "bound"` while a linked PR in another lane is
    still open, with the `bound` halves named, so a session cannot merge this half alone.
    """
    primary = primary_repo or (next(iter(lane_repos), None) if lane_repos else None)
    repos: list[str | None] = [primary]
    for lane in lane_repos or []:
        if lane and lane not in repos:
            repos.append(lane)
    by_repo: dict[str, list[dict[str, Any]]] = {}
    for repo in repos:
        by_repo[repo or ""] = _fetch_linked(key, pr_number if repo == primary else None, repo)
    return classify_coupled(by_repo, primary or "")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pr_resolve_review_target.py",
        usage=USAGE,
        add_help=True,
    )
    parser.add_argument("action", nargs="?", default="")
    parser.add_argument("key", nargs="?", default="")
    parser.add_argument("--pr", default=None)
    # Repeatable: a coupled change names more than one lane, and each is searched for a
    # linked PR so `classify_coupled` can refuse a half while another half is unmerged.
    parser.add_argument("--repo", action="append", default=None)
    args = parser.parse_args()
    if args.action != "resolve" or not args.key:
        print(USAGE, file=sys.stderr)
        return 2
    lane_repos: list[str] = [r for r in (args.repo or []) if r]
    if not lane_repos:
        print(USAGE, file=sys.stderr)
        print("resolve refused: --repo <owner/name> is required (the issue's lane from get_issue).", file=sys.stderr)
        return 2
    primary = lane_repos[0]
    try:
        print(json.dumps(resolve_coupled(args.key, args.pr, primary, lane_repos)))
    except UnlinkedPRError as exc:
        print(f"resolve refused: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"resolve failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
