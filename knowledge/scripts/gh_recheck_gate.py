#!/usr/bin/env python3
"""Re-dispatch the required gate check on a PR's current head and wait for it — `tool:pr-recheck-gate`.

    gh_recheck_gate.py <pr> [--workflow NAME] [--timeout SECONDS]

**Which gate this is comes from `$FLEET_VERIFY_GATE`, and it has two kinds (PRD 0745, design §8).**
On a customer install the control plane posts the verify verdict itself as a check through the
install's App; there is no workflow to re-run, so on `check:<name>` this script prints that and
exits 0 at once. Where the gate is a workflow file, the lease names it `workflow:<file>` and the
script re-dispatches that file. No workflow file name is hard-coded here: the lease names the
gate, so the command tree stays portable. When the variable is unset the lane carries no gate at
all and there is nothing to re-run.

An explicit `--workflow NAME` still wins over the environment, for a caller that knows the file.

The gate for a fix re-reads its verdict from the
tracker, so after the verdict comment lands the check has to be re-run before it can go
green — and it must be re-run with **no auto-merge armed**, or the merge fires on the
stale green. This script does the re-dispatch and the wait; the disarm is the
caller's (`tool:pr-automerge-disarm`), by design — a re-check that disarmed for you would
also re-arm for you, and the arm is the one step a human wants to see happen.

**Mergeability is read before the re-dispatch and on every poll.** GitHub dispatches no
`pull_request` workflow on a PR that conflicts with its base, so the gate on a conflicted PR
never re-reads and a wait on it cannot end. Measured on a lane PR (
2026-09-27): the verdict was posted, `main` moved under the PR, and the session waited past its
own window without once reading `mergeable`. A check that never reports is a conflict until
proven otherwise. `UNKNOWN` means GitHub is still computing the merge commit. It is re-read a
bounded number of times and is never a pass.

Exit codes:

* 0: every required check reports green on the head, and the PR is not conflicted.
* 1: a check reports red, the wait times out, or mergeability never resolves.
* 2: a usage or `gh` failure.
* 3: the PR is CONFLICTING / DIRTY, before the re-dispatch or during the wait. Take the
  caller's DIRTY / CONFLICTING route (`regen_reconcile.py`, then either a fast-forward push and
  a fresh re-check, or the conflict-as-work hand-back). Never keep waiting.

Never merges.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping

#: The lease names the gate here (PRD 0745, design §7/§8): `check:<name>` when the control plane
#: posts the check itself, `workflow:<file>` when the repository's own workflow file gates.
GATE_ENV = "FLEET_VERIFY_GATE"

#: Exit code for a PR that conflicts with its base: the gate cannot re-read, so the wait cannot end.
EXIT_CONFLICT = 3

#: How many times an `UNKNOWN` mergeability is re-read before it is treated as unresolved.
UNKNOWN_READS = 6

#: Seconds between re-reads of an `UNKNOWN` mergeability.
UNKNOWN_PAUSE = 5

#: `mergeable` / `mergeStateStatus` values that mean the PR cannot produce a merge commit.
CONFLICTED = frozenset({"CONFLICTING", "DIRTY"})


def parse_gate(value: str) -> tuple[str, str] | None:
    """`check:<name>` / `workflow:<file>` from the lease, or `None` when it names no gate.

    Total over every shape a value can carry: an empty string, a bare word with no colon, an
    unknown kind and a blank name all fold onto `None` — "no gate this session can act on" —
    rather than inventing a workflow file to re-run.
    """
    text = (value or "").strip()
    if ":" not in text:
        return None
    kind, _, name = text.partition(":")
    kind, name = kind.strip().casefold(), name.strip()
    if kind not in ("check", "workflow") or not name:
        return None
    return kind, name


def gate_from_env(env: Mapping[str, str] | None = None) -> tuple[str, str] | None:
    """The gate `$FLEET_VERIFY_GATE` names, or `None`. Reads `os.environ` unless handed a mapping."""
    source = os.environ if env is None else env
    return parse_gate(source.get(GATE_ENV, ""))


def _gh(*args: str) -> tuple[int, str]:
    p = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _pr(pr: str) -> tuple[dict[str, object] | None, str]:
    """The PR's head, arm and mergeability, re-read past `UNKNOWN`. `None` and a reason on failure."""
    for attempt in range(UNKNOWN_READS):
        code, out = _gh("pr", "view", pr, "--json", "headRefName,autoMergeRequest,mergeable,mergeStateStatus")
        if code != 0:
            return None, f"could not read PR {pr}: {out.strip()}"
        info: dict[str, object] = json.loads(out)
        if info.get("mergeable") != "UNKNOWN":
            return info, ""
        if attempt + 1 < UNKNOWN_READS:
            time.sleep(UNKNOWN_PAUSE)
    return info, "unknown"


def _conflicted(info: dict[str, object]) -> bool:
    return info.get("mergeable") in CONFLICTED or info.get("mergeStateStatus") in CONFLICTED


def _say_conflict(pr: str, info: dict[str, object], when: str) -> int:
    print(
        f"gh_recheck_gate: CONFLICT {when}: PR {pr} is mergeable={info.get('mergeable')} "
        f"mergeStateStatus={info.get('mergeStateStatus')}. GitHub runs no workflow on a conflicted PR, "
        "so the gate cannot re-read and this wait cannot end. Take the DIRTY / CONFLICTING route: "
        "regen_reconcile.py, then a fast-forward push and a fresh re-check, or the conflict-as-work hand-back.",
        file=sys.stderr,
    )
    return EXIT_CONFLICT


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pr", help="the pull request number")
    ap.add_argument(
        "--workflow",
        default="",
        help=f"re-run this workflow file, overriding ${GATE_ENV} (a workflow gate)",
    )
    ap.add_argument("--timeout", type=int, default=1800, help="seconds to wait for the checks (default 1800)")
    args = ap.parse_args(argv)

    # WHICH GATE, FROM THE LEASE (PRD 0745, design §8). `--workflow` is the explicit override;
    # otherwise the environment names it. Unset means the lane carries no gate and there is
    # nothing to re-run — a clean no-op, never a guessed workflow file.
    gate = ("workflow", args.workflow) if args.workflow else gate_from_env()
    if gate is None:
        print(
            f"gh_recheck_gate: no verify gate is configured (${GATE_ENV} is unset); nothing to re-run",
        )
        return 0
    kind, name = gate
    if kind == "check":
        # The control plane posts this gate through the install's App; re-running a workflow is
        # exactly the customer-repository assumption this PRD removes. Nothing to dispatch here.
        print(f"gh_recheck_gate: {GATE_ENV}=check:{name} — the control plane posts this gate; nothing to re-run")
        return 0
    args.workflow = name

    info, why = _pr(args.pr)
    if info is None:
        print(f"gh_recheck_gate: {why}", file=sys.stderr)
        return 2
    if _conflicted(info):
        return _say_conflict(args.pr, info, "before the re-dispatch")
    if why:
        print(
            f"gh_recheck_gate: PR {args.pr}'s mergeability stayed UNKNOWN across {UNKNOWN_READS} reads; "
            "not re-dispatching a gate that may never report",
            file=sys.stderr,
        )
        return 1
    if info.get("autoMergeRequest"):
        print(
            "gh_recheck_gate: auto-merge is ARMED on this PR — disarm first (tool:pr-automerge-disarm), then re-check",
            file=sys.stderr,
        )
        return 2
    branch = str(info["headRefName"])

    code, out = _gh(
        "run", "list", "--workflow", args.workflow, "--branch", branch, "--limit", "1", "--json", "databaseId"
    )
    runs = json.loads(out) if code == 0 and out.strip() else []
    if runs:
        rid = str(runs[0]["databaseId"])
        code, out = _gh("run", "rerun", rid)
        if code != 0:
            print(f"gh_recheck_gate: rerun of {rid} failed: {out.strip()}", file=sys.stderr)
            return 2
        print(f"re-dispatched {args.workflow} run {rid} on {branch}")
    else:
        code, out = _gh("workflow", "run", args.workflow, "--ref", branch)
        if code != 0:
            print(f"gh_recheck_gate: could not dispatch {args.workflow} on {branch}: {out.strip()}", file=sys.stderr)
            return 2
        print(f"dispatched {args.workflow} on {branch} (no prior run to re-run)")

    deadline = time.monotonic() + args.timeout
    time.sleep(10)
    while time.monotonic() < deadline:
        # `main` moves during the wait. A PR that conflicts now will never report, whatever it did
        # when the gate was re-dispatched.
        now, _why = _pr(args.pr)
        if now is not None and _conflicted(now):
            return _say_conflict(args.pr, now, "during the wait")
        code, out = _gh("pr", "checks", args.pr, "--json", "name,state,bucket")
        if code == 0 and out.strip():
            checks = json.loads(out)
            pending = [c for c in checks if c.get("bucket") == "pending"]
            failed = [c for c in checks if c.get("bucket") == "fail"]
            if failed:
                print("red: " + ", ".join(c["name"] for c in failed), file=sys.stderr)
                return 1
            if not pending:
                print("green: " + ", ".join(c["name"] for c in checks))
                return 0
        time.sleep(15)
    print("gh_recheck_gate: timed out waiting for the checks to report", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
