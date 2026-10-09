#!/usr/bin/env python3
"""Ensure the GitHub closing keyword for <KEY> is on a PR's body BEFORE auto-merge is armed.

WHY THIS EXISTS. For a `Type:bug`/`task`/`cleanup` PR the de-facto closer is the fleet
daemon (`_pr_completes_issue` title-shape + closing-keyword attribution → `_drive_to_done`);
the fleet service's `prd-projection` pass converges PRD issues only, and
Linear↔GitHub keyword auto-close is dead. A closing keyword
(`Closes`/`Fixes`/`Resolves <KEY>`) is the daemon's **strongest attribution signal** — the
sibling arm of the completing-title forms `fix(ENG-N): …` / `[ENG-N] …`. `verify` §6
used to compose that keyword inside the merge path (step 4's `push ship`, whose step 5.5
self-heal runs after step 2's re-arm), so once `Verify Gate` re-read green with `CI Success`
already green, GitHub squash-merged before the body edit landed: PR #10014 merged with
`Refs ` and no closing keyword, and stranded in `Verifying` — a claimed
state that dispatches nothing — until the daemon (or a hand move) settled it. The fix is
ordering, not a new closer: the keyword is composed and verified HERE, at arm time, before
`gh pr merge --auto`, so no merge can win the race and `push ship` step 5.5 becomes the
confirming no-op it always claimed to be. `scripts/validate_automerge_arming.py` pins the
ordering mechanically; `scripts/validate_bug_close_contract.py` pins that prose never
re-claims Linear keyword auto-close as the live closer.

A bare `<KEY>` mention (`Refs <KEY>`) is deliberately NOT recognized as a closing keyword
(/ push.md Step 0): the compose never strips or "upgrades" a `Refs` line — it
appends `Closes <KEY>` beside it. Composing is safe here and only here because §6 step 2
runs after step 1's VERIFIED verdict: this is the completing merge, the only party push.md
Step 0 allows to author a closing keyword.

Usage: python3 knowledge/scripts/gh_closing_keyword_ensure.py <pr> <KEY> [<KEY>...]
       (extra keys: every `Fixed incidentally: <KEY2>` the verify ledger recorded)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import Any

# The same keyword set push.md step 5.5 greps for — a GitHub-recognized closing keyword
# followed by the key. `Refs`/`Relates to`/`See` are links, never closes.
_CLOSING_RE_TMPL = r"\b(close[sd]?|fix(e[sd])?|resolve[sd]?)[ \t]+{key}\b"


def has_closing_keyword(body: str, key: str) -> bool:
    """True iff the body already carries a GitHub closing keyword for `key`."""
    if not body:
        return False
    return re.search(_CLOSING_RE_TMPL.format(key=re.escape(key)), body, re.IGNORECASE) is not None


def missing_closing_keywords(body: str, keys: list[str]) -> list[str]:
    """The keys whose closing keyword the body does not carry yet, in the given order."""
    return [k for k in keys if not has_closing_keyword(body, k)]


def with_closing_keywords(body: str, keys: list[str]) -> str:
    """The body with one `Closes <KEY>` line appended per key."""
    lines = "".join(f"Closes {k}\n" for k in keys)
    base = body.rstrip("\n")
    return f"{base}\n\n{lines}" if base else lines


def decide(view: dict[str, Any], keys: list[str]) -> tuple[str, list[str]]:
    """Pure decision for a `gh pr view --json body,isDraft,state` result and its keys.

    Returns (action, missing) where action is one of
      "edit"   — append the closing lines for `missing` (non-empty by construction)
      "noop"   — every key already carries its closing keyword
      "skip"   — the PR is not OPEN (merged/closed): nothing to ensure, nothing to edit
      "refuse" — a draft: a third-party pause is never edited (verify.md §6 BLOCKEDs on
                 it first; reaching this script with a draft means one landed in between)
    """
    if str(view.get("state") or "") != "OPEN":
        return "skip", []
    if view.get("isDraft"):
        return "refuse", []
    missing = missing_closing_keywords(str(view.get("body") or ""), keys)
    if not missing:
        return "noop", []
    return "edit", missing


def fetch_pr_view(pr: str) -> dict[str, Any]:
    out = subprocess.check_output(["gh", "pr", "view", pr, "--json", "body,isDraft,state"])
    result: dict[str, Any] = json.loads(out)
    return result


def edit_body(pr: str, body: str) -> None:
    """Write the body via the REST PATCH — `gh pr edit` goes over GraphQL, whose
    `updatePullRequest` payload carries sub-queries (`login`, `name`, `slug`) needing
    `read:org`, a scope the fleet's keyring token does not carry; the REST
    endpoint needs only `repo`. The body rides stdin — it is long, and argv is
    world-readable."""
    payload = json.dumps({"body": body})
    subprocess.run(
        ["gh", "api", f"repos/{{owner}}/{{repo}}/pulls/{pr}", "-X", "PATCH", "--input", "-"],
        input=payload,
        text=True,
        check=True,
    )


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: gh_closing_keyword_ensure.py <pr> <KEY> [<KEY>...]", file=sys.stderr)
        return 2
    pr = sys.argv[1]
    keys = sys.argv[2:]
    view = fetch_pr_view(pr)
    action, missing = decide(view, keys)
    if action == "skip":
        print(f"PR #{pr}: state is {view.get('state')!r} — nothing to ensure (the merge-close race window has passed).")
        return 0
    if action == "refuse":
        print(
            f"PR #{pr}: REFUSING — the PR is a draft. A third-party draft is a deliberate "
            "human pause and is never edited; verify.md §6 BLOCKEDs on it before this call.",
            file=sys.stderr,
        )
        return 1
    if action == "noop":
        print(f"PR #{pr}: closing keyword already on the body for {', '.join(keys)} — no edit.")
        return 0
    # edit — then prove the compose landed by re-reading: never report done without the
    # check passing (push.md step 5.5's self-heal rule, applied at arm time now).
    edit_body(pr, with_closing_keywords(str(view.get("body") or ""), missing))
    confirm = fetch_pr_view(pr)
    still = missing_closing_keywords(str(confirm.get("body") or ""), keys)
    if still:
        print(
            f"PR #{pr}: FAILED — after the edit the body still lacks a closing keyword for: {', '.join(still)}",
            file=sys.stderr,
        )
        return 1
    print(
        f"PR #{pr}: Closes {', '.join(missing)} appended and confirmed on the body — safe to arm auto-merge (ENG-9634)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
