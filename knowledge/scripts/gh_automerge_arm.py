#!/usr/bin/env python3
"""Arm GitHub auto-merge, optionally only when required checks are already green.

WHY THIS EXISTS.
`gh pr merge --auto` completion runs on an asynchronous GitHub-side worker that
does not reliably re-validate required-status-check state before completing a
merge (cli/cli#8514). Two measured escapes on this repo:

  * / PR #4185 — force-push under a live `--auto` (new head, no
    check-run yet). Closed procedurally by `gh_automerge_disarm.py` before push.
  * / PR #10055 — re-arm then re-trigger the required `Verify Gate`;
    GitHub squash-merged 18s before the re-run went green. Closed procedurally
    by verify.md §6 (disarm → re-run → confirm green → re-arm).
  * / PR #10064 — same class ~4.5 min after fix landed: the
    verify session for armed at 08:38:36Z while the latest completed
    `Verify Gate` was still `failure`, and GitHub merged at 08:38:44Z — 25s
    before the re-run went green. The session had started before the procedure
    fix was on its checkout, so the text-only pin did not bind it.

A procedure the agent must follow is not a gate the agent cannot skip. This
script is the mechanical half: the final re-arm after `verify` (and any
other caller that opts in) refuses to arm unless every branch-protection
required context already reads green on the head SHA. Open-time arm
deliberately arms over a red `Verify Gate` and must NOT pass `--require-green`.

"every branch-protection required context" is resolved LIVE from the
target repo's own policy — this script runs from a platform-repo checkout
against whatever repo `GH_REPO`/cwd point at, and the hardcoded platform list
refused on every non-platform lane whose head was already green (live on
a secondary lane's PR, 2026-09-08). `resolve_required_contexts()` reads the repo's
branch protection (and any enforced repo-level rulesets); the static
`PROTECTION_REQUIRED_CONTEXTS` below is only the fail-closed offline fallback.

MERGE QUEUE (2026-09-28 rehearsal). The arm is `gh pr merge <pr> --auto --squash` — never
`--delete-branch`, which `gh` refuses outright on a queued branch — and it is CONFIRMED by
`gh_pr_merge_state.py`: armed, queued (an enqueued PR reads `autoMergeRequest: null`) or
merged. Works identically on a branch without a queue.

Usage:
  python3 knowledge/scripts/gh_automerge_arm.py <pr-number>              # arm unconditionally
  python3 knowledge/scripts/gh_automerge_arm.py <pr-number> --require-green
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gh_pr_merge_state as mq  # noqa: E402 — the sibling shipped script, beside this one

# OFFLINE FALLBACK: the required contexts on the platform repo's `main`
# (docs/ci-branch-protection.md §0). `resolve_required_contexts()` reads the
# target repo's live policy first and degrades to this list — fail closed — only
# when that read fails; on the platform repo the fallback is exactly the live
# set, so the pure gate function keeps this as its default and its offline test
# set. The merge-guard REQUIRED_CONTEXTS remains a deliberate SUPERSET
# (lane-level defense-in-depth) and is the wrong list for an arm gate: a
# doc-only PR legitimately skips Frontend.
#
#: `No GitHub-hosted runners (runs-on guard)` was RETIRED 2026-10-01
# (docs/ci-branch-protection.md §0 now names four contexts; merge_guard_check.py's
# own comment records the retirement) and no workflow job carries that name any
# more, so a static list still demanding it blocked 100% of arms whenever the
# live read degraded. Drop it.
#
# PRD 0745: the gate's own context is NOT hard-coded here. A workflow-gated
# repository names its file in `$FLEET_VERIFY_GATE` and a check-gated one names
# the check; the fallback listens to that environment (`_gate_from_env`) instead
# of carrying a platform repository's gate literal, which meant nothing on a
# customer's repository.
PROTECTION_REQUIRED_CONTEXTS = [
    "CI Success",
    "Workflow Size Guard",
    "PRD Verified",
]

# Mirror merge_guard_check.PASSING_CONCLUSIONS / ci-success aggregator semantics.
PASSING_CONCLUSIONS = {"success", "skipped", "neutral"}

#: The lease names the verify gate here (PRD 0745, design §7/§8): `check:<name>` when the control
#: plane posts the check itself, `workflow:<file>` when the repository's own workflow gates. Only
#: the check kind carries a required-context NAME; a workflow's context is the workflow's own job
#: name, which this variable does not spell.
GATE_ENV = "FLEET_VERIFY_GATE"


def parse_gate(value: str) -> tuple[str, str] | None:
    """`check:<name>` / `workflow:<file>` from the lease, or `None` when it names no gate."""
    text = (value or "").strip()
    if ":" not in text:
        return None
    kind, _, name = text.partition(":")
    kind, name = kind.strip().casefold(), name.strip()
    if kind not in ("check", "workflow") or not name:
        return None
    return kind, name


def _gate_from_env(env: Mapping[str, str] | None = None) -> tuple[str, str] | None:
    """The gate `$FLEET_VERIFY_GATE` names, or `None`. Reads `os.environ` unless handed a mapping."""
    source = os.environ if env is None else env
    return parse_gate(source.get(GATE_ENV, ""))


# The runner the gh subprocesses go through; tests inject a fake serving canned
# responses (stdlib only — no mock framework).
GhRun = Callable[[list[str]], subprocess.CompletedProcess[str]]


def _gh_run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True)


class RequireGreenResult(NamedTuple):
    reasons: list[str]
    required: list[str]
    source: str


def latest_completed_by_name(check_runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Latest completed check-run per name (highest id), ignoring in-flight re-runs.

    Same selection rule as `merge_guard_check.evaluate`: a non-completed
    re-dispatch does not retract an earlier completed verdict on the same SHA.
    """
    completed: dict[str, dict[str, Any]] = {}
    for run in check_runs:
        if run.get("conclusion") is None:
            continue
        name = run.get("name")
        if not isinstance(name, str) or not name:
            continue
        prev = completed.get(name)
        if prev is None or run.get("id", 0) >= prev.get("id", 0):
            completed[name] = run
    return completed


def blocking_reasons(
    check_runs: list[dict[str, Any]],
    required: list[str] = PROTECTION_REQUIRED_CONTEXTS,
) -> list[str]:
    """Return one reason string per required context that is not green on the head.

    Pure and offline — the gate the `--require-green` path enforces. A missing
    check-run is a block (shape); a non-passing conclusion is a block;
    only success/skipped/neutral pass.
    """
    completed = latest_completed_by_name(check_runs)
    reasons: list[str] = []
    for name in required:
        matched = completed.get(name)
        if matched is None:
            reasons.append(f"{name}: no completed check-run on head")
            continue
        conclusion = matched.get("conclusion")
        if conclusion not in PASSING_CONCLUSIONS:
            reasons.append(f"{name}: conclusion={conclusion!r} (status={matched.get('status')!r})")
    return reasons


def _http_status(stderr: str) -> int | None:
    m = re.search(r"HTTP (\d{3})", stderr or "")
    return int(m.group(1)) if m else None


def _contexts_from_protection_body(body: Any) -> list[str] | None:
    """Extract the context list from a required_status_checks payload.

    Accepts either the canonical `{contexts: [...], checks: [...]}` shape or the
    embedded summary's; returns None when the shape is unreadable (fail closed
    upstream — an unreadable required set must not read as an empty one).
    """
    if not isinstance(body, dict):
        return None
    contexts = body.get("contexts")
    if contexts is None:
        checks = body.get("checks")
        if isinstance(checks, list):
            contexts = [c.get("context") for c in checks if isinstance(c, dict)]
    if not isinstance(contexts, list):
        return None
    if not all(isinstance(c, str) and c for c in contexts):
        return None
    return list(dict.fromkeys(contexts))


def _static_fallback(reason: str) -> tuple[list[str], str]:
    """The fail-closed degradation: unknown live policy → the static platform list plus the gate.

    Refusing on a list that is at worst the platform's is safe; arming on an
    under-read is the race with a blindfold. The warning is loud so a
    degraded gate is never mistaken for a live one. **The gate's own context
    comes from `$FLEET_VERIFY_GATE`, not a literal** (PRD 0745): on a
    check-gated repository it is the name the control plane posts, and it is
    the one context `--require-green` must NOT demand (the arm is deliberately
    made while it is pending). A workflow gate names a file, not a context, so
    nothing is added for it — the live read carries the workflow's own job name.
    """
    fallback = list(PROTECTION_REQUIRED_CONTEXTS)
    gate = _gate_from_env()
    if gate is not None and gate[0] == "check" and gate[1] not in fallback:
        fallback.append(gate[1])
    print(
        f"[gh_automerge_arm] WARNING: live required-context read unavailable ({reason}) — "
        f"failing CLOSED to the static platform fallback {fallback} "
        "(ENG-10051). On a non-platform repo this may refuse although the head is green: "
        "retry, or fix the credential/read failure.",
        file=sys.stderr,
    )
    return fallback, "static-fallback"


def _embedded_required_contexts(base: str, gh: Callable[[str], subprocess.CompletedProcess[str]]) -> list[str] | None:
    """Required contexts from the embedded `branches/<base>` `.protection` summary.

    The non-admin-readable disambiguator (docs/ci-branch-protection.md §0's own
    prescribed path): the canonical protection endpoint 404s both for a
    genuinely unprotected branch AND for a non-admin credential with protection
    live, and this field answers for both. Returns [] when protection is
    disabled (nothing required — live truth, not a failure); None when the
    field cannot answer (`protected: true` with the deprecated summary gone or
    an unreadable shape) so the caller fails closed.
    """
    proc = gh(f"repos/{{owner}}/{{repo}}/branches/{base}")
    if proc.returncode != 0:
        return None
    try:
        body = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(body, dict):
        return None
    protection = body.get("protection")
    if not isinstance(protection, dict):
        # `protected: true` without an embedded protection object: GitHub has
        # dropped the deprecated field — the required set is unknowable here.
        return None
    if not protection.get("enabled"):
        return []
    return _contexts_from_protection_body(protection.get("required_status_checks"))


_HEADS = "refs/heads/"


def _branch_of(ref: str) -> str:
    """`refs/heads/<name>` → `<name>`; a bare name is returned unchanged."""
    return ref[len(_HEADS) :] if ref.startswith(_HEADS) else ref


def _ref_targets_base(include: list[Any], exclude: list[Any], base: str) -> bool:
    """Whether a ruleset's ref_name conditions cover the PR's base branch.

    `~DEFAULT_BRANCH` and `~ALL` are treated as covering ANY base (over-reading
    is the safe direction for an arm gate); other patterns are exact or
    fnmatch-style globs, matching GitHub's ref-name conditions closely enough.

    GitHub writes a ruleset's branch patterns as FULL refs (`refs/heads/main`,
    `refs/heads/release/*`) while the PR names its base as a bare branch
    (`main`). Both sides are normalised to the bare name before comparing —
    before that, a `refs/heads/<base>` include never matched, so every
    ruleset-defined required check was invisible and `--require-green` read
    "(none — gate is vacuous)" (merge-queue rehearsal on `mq-canary`,
    2026-09-28; the bug holds with or without a queue).
    """
    branch = _branch_of(base)

    def matches(patterns: list[Any]) -> bool:
        for p in patterns:
            if not isinstance(p, str):
                raise ValueError(f"non-string ref pattern {p!r}")
            if p in ("~ALL", "~DEFAULT_BRANCH"):
                return True
            pattern = _branch_of(p)
            if pattern == branch or fnmatch.fnmatch(branch, pattern):
                return True
        return False

    return matches(include) and not matches(exclude)


def _required_from_ruleset(detail: Any, base: str) -> list[str]:
    """The `required_status_checks` contexts a ruleset enforces on `base`.

    Raises ValueError on an unreadable ruleset — the caller fails closed rather
    than silently under-reading what the merge will be gated on.
    """
    if not isinstance(detail, dict):
        raise ValueError("ruleset detail is not an object")
    conditions = (detail.get("conditions") or {}).get("ref_name")
    if not isinstance(conditions, dict) or not conditions.get("include"):
        raise ValueError("ruleset has no readable ref_name conditions")
    include = conditions.get("include")
    exclude = conditions.get("exclude") or []
    if not isinstance(include, list) or not isinstance(exclude, list):
        raise ValueError("ruleset ref_name include/exclude are not lists")
    if not _ref_targets_base(include, exclude, base):
        return []
    out: list[str] = []
    for rule in detail.get("rules") or []:
        if not isinstance(rule, dict) or rule.get("type") != "required_status_checks":
            continue
        checks = (rule.get("parameters") or {}).get("required_status_checks") or []
        if not isinstance(checks, list):
            raise ValueError("required_status_checks parameters are not a list")
        for c in checks:
            name = c.get("context") if isinstance(c, dict) else None
            if isinstance(name, str) and name:
                out.append(name)
    return out


#: loud marker naming the unresolved source class. Org-level rulesets
# need `admin:org` on the fleet's gh credential (verified absent 2026-09-08);
# without it the gate that closes the `gh --auto` completion race is silently
# blind if the org ever adopts them. Emitted on every LIVE resolution (never on
# static-fallback, which already screams its own degradation). Remediation:
# grant `admin:org` (or a read-only org-rulesets equivalent) to the arm
# credential, then extend `_with_rulesets` to union `GET /orgs/{org}/rulesets`
# the same way it unions repo-level ones.
ORG_RULESET_BLINDNESS_MARKER = (
    "DEGRADED: org-level rulesets unresolved — require-green cannot see org ruleset "
    "required contexts (credential lacks admin:org; verified 2026-09-08). If the org "
    "adopts org-ruleset required checks, this gate is blind to them. Remediation: "
    "grant admin:org (or org rulesets read) to the arm credential and extend "
    "_with_rulesets to union GET /orgs/{org}/rulesets (ENG-10112)."
)


def _emit_org_ruleset_blindness() -> None:
    """Print the degraded-mode marker to stderr (live resolution only)."""
    print(ORG_RULESET_BLINDNESS_MARKER, file=sys.stderr)


def _with_rulesets(
    contexts: list[str],
    source: str,
    base: str,
    gh: Callable[[str], subprocess.CompletedProcess[str]],
) -> tuple[list[str], str]:
    """Union enforced repo-level rulesets' required checks into the resolved set.

    ANY ruleset read failure degrades the whole resolution to the static list:
    a half-read gate (protection known, rulesets unknown) could arm on an
    under-read, which is the dangerous direction. ORG-level rulesets are NOT
    resolved here — the org listing needs the `admin:org` scope the fleet's gh
    credential does not hold (verified 2026-09-08); if the org adopts them,
    extend the credential scope or the fallback covers the platform lane only.
    A live (non-fallback) return always emits ORG_RULESET_BLINDNESS_MARKER so
    the unresolved source class is never silent.
    """
    proc = gh("repos/{owner}/{repo}/rulesets?per_page=100")
    if proc.returncode != 0:
        return _static_fallback(f"rulesets read failed: {(proc.stderr or 'no stderr').strip()[:200]}")
    try:
        rulesets = json.loads(proc.stdout)
        if not isinstance(rulesets, list):
            raise ValueError("rulesets response is not a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        return _static_fallback(f"rulesets read returned an unexpected shape ({e})")
    extra: list[str] = []
    for entry in rulesets:
        if not isinstance(entry, dict):
            return _static_fallback("rulesets list contains a non-object entry")
        if entry.get("enforcement") != "active":
            continue  # "evaluate" is dry-run, "disabled" is off — neither blocks a merge
        rid = entry.get("id")
        if rid is None:
            return _static_fallback("ruleset list entry without an id")
        detail_proc = gh(f"repos/{{owner}}/{{repo}}/rulesets/{rid}")
        if detail_proc.returncode != 0:
            return _static_fallback(f"ruleset {rid} detail read failed")
        try:
            extra.extend(_required_from_ruleset(json.loads(detail_proc.stdout), base))
        except (json.JSONDecodeError, ValueError) as e:
            return _static_fallback(f"ruleset {rid} unreadable ({e})")
    # Live resolution succeeded (repo protection and/or repo rulesets). Org-level
    # rulesets remain unread — name that class loudly before returning.
    _emit_org_ruleset_blindness()
    if not extra:
        return contexts, source
    return list(dict.fromkeys(contexts + extra)), f"{source}+rulesets"


def resolve_required_contexts(
    base: str = "main",
    run: GhRun | None = None,
) -> tuple[list[str], str]:
    """Resolve the PR base branch's required status-check contexts from live policy.

    Sources, unioned:
      * branch protection — `GET repos/{owner}/{repo}/branches/<base>/protection/
        required_status_checks` (admin-scoped; a 200 is authoritative). On any
        canonical read failure — 404 is ambiguous between "not protected" and a
        non-admin credential, and the fleet's GitHub App installation token gets
        a 403 `Resource not accessible by integration` — the embedded
        `branches/<base>` `.protection` summary disambiguates before the static
        fallback is reached.
      * repo-level rulesets, enforced and ref-targeted to <base> (see
        `_with_rulesets` for the org-level limitation).

    Any remaining read failure degrades the WHOLE resolution to the static
    PROTECTION_REQUIRED_CONTEXTS with a loud stderr warning (fail closed). An
    empty union is live truth (no protection, no rulesets — two lanes were in
    that state on 2026-09-08) and passes vacuously; the caller prints the
    resolved set so a vacuous pass is visible, never silent.

    Returns (contexts, source) with source "branch-protection", "embedded
    branch-protection", either "+rulesets", or "static-fallback".
    """
    run = run or _gh_run

    def gh(path: str) -> subprocess.CompletedProcess[str]:
        return run(["gh", "api", path])

    proc = gh(f"repos/{{owner}}/{{repo}}/branches/{base}/protection/required_status_checks")
    if proc.returncode == 0:
        try:
            contexts = _contexts_from_protection_body(json.loads(proc.stdout))
        except json.JSONDecodeError as e:
            fail_reason = f"protection read returned non-JSON ({e})"
        else:
            if contexts is not None:
                return _with_rulesets(contexts, "branch-protection", base, gh)
            fail_reason = "protection read shape unexpected"
    else:
        status = _http_status(proc.stderr)
        detail = (proc.stderr or proc.stdout or "no output").strip()[:200]
        # 404 is ambiguous (unprotected OR non-admin); a 403 is what the fleet's
        # GitHub App token actually gets. Neither proves the head is un-gated, so
        # both fall through to the embedded summary.
        prefix = f"protection read failed (HTTP {status})" if status is not None else "protection read failed"
        fail_reason = f"{prefix}: {detail}"

    #: try the readable embedded summary on ANY canonical failure — not
    # only a 404 — before failing closed to the (now correct) static list.
    embedded = _embedded_required_contexts(base, gh)
    if embedded is not None:
        return _with_rulesets(embedded, "embedded branch-protection", base, gh)
    return _static_fallback(f"{fail_reason} and the embedded .protection field could not answer")


def require_green_block_reasons(
    pr: str,
    head: str,
    base: str,
    run: GhRun | None = None,
) -> RequireGreenResult:
    """The `--require-green` gate, against the repo's LIVE required set.

    Resolves the base branch's required contexts (`resolve_required_contexts`),
    reads the head SHA's check-runs, and returns one blocking reason per
    required context that is not green. Prints the resolved set and its source
    so the caller sees what was enforced — a vacuous pass (no required contexts
    at all) must be visible, never look like a green-by-checks arm.
    """
    required, source = resolve_required_contexts(base, run=run)
    # PRD 0745 / design §8: on a check-gated repository the gate's own check is PENDING at the
    # moment this arm runs — the control plane turns it green after it reads the session's
    # verdict — so demanding it here would refuse the one arm the design calls for. Exclude only
    # the gate this lease named; every context the customer's own CI requires stays enforced.
    gate = _gate_from_env()
    if gate is not None and gate[0] == "check":
        required = [c for c in required if c != gate[1]]
    print(
        f"PR #{pr}: --require-green evaluating against required contexts "
        f"from {source}: {required or '(none — gate is vacuous)'}",
        file=sys.stderr,
    )

    # Paginate explicitly: gh --paginate with a jq filter that returns an
    # array emits one array per page, and a naive json.loads of the whole
    # stdout would fail on the second page.
    run = run or _gh_run
    check_runs: list[dict[str, Any]] = []
    page = 1
    while True:
        proc = run(
            [
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/commits/{head}/check-runs?per_page=100&page={page}",
                "--jq",
                "[.check_runs[] | {id, name, status, conclusion}]",
            ]
        )
        if proc.returncode != 0:
            raise SystemExit(f"gh_automerge_arm: check-runs fetch failed: {(proc.stderr or 'no stderr').strip()[:200]}")
        page_runs = json.loads(proc.stdout)
        if not page_runs:
            break
        check_runs.extend(page_runs)
        if len(page_runs) < 100:
            break
        page += 1

    reasons = blocking_reasons(check_runs, required=required)
    return RequireGreenResult(reasons, required, source)


#: The arm invocation. NO `--delete-branch`: `gh` refuses `-d`/`--delete-branch` outright on a
#: branch with a merge queue ("Cannot use `-d` or `--delete-branch` when merge queue enabled",
#: exit 1, nothing armed), and every fleet repo has `delete_branch_on_merge` on, so GitHub
#: deletes the head branch itself. `--squash` is only downgraded to a warning under a queue.
ARM_ARGV = ["gh", "pr", "merge", "{pr}", "--auto", "--squash"]

#: How many times the arm is read back before it is declared unconfirmed, and how far apart:
#: GitHub records an enqueue a beat after `gh pr merge` returns.
CONFIRM_READS = 3
CONFIRM_PAUSE_SECONDS = 2.0

#: Verdicts (`gh_pr_merge_state`) that confirm an arm. Under a merge queue a green PR is
#: ENQUEUED rather than armed and reads `autoMergeRequest: null` — the queue entry is the
#: confirmation; a PR that already merged needed no arm at all.
CONFIRMED_VERDICTS = frozenset({mq.ARMED, mq.QUEUED, mq.MERGED})


def confirm_armed(pr: str, run: GhRun | None = None, sleep: Callable[[float], None] = time.sleep) -> tuple[bool, str]:
    """Read the PR back until the arm shows: armed, queued or merged. `(ok, the last verdict)`."""
    verdict = "unread"
    for attempt in range(CONFIRM_READS):
        if attempt:
            sleep(CONFIRM_PAUSE_SECONDS)
        try:
            verdict = mq.read_state(pr, run=run).verdict
        except mq.ForgeReadError as exc:
            verdict = f"unreadable ({exc})"
            continue
        if verdict in CONFIRMED_VERDICTS:
            return True, verdict
    return False, verdict


def main(
    argv: list[str] | None = None,
    run: GhRun | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pr", help="pull request number")
    parser.add_argument(
        "--require-green",
        action="store_true",
        help=(
            "refuse to arm unless every branch-protection required context is "
            "already green on the PR head (ENG-9680 final re-arm). Open-time arm "
            "must NOT pass this flag."
        ),
    )
    args = parser.parse_args(argv)
    pr = args.pr
    run = run or _gh_run

    if args.require_green:
        view_proc = run(["gh", "pr", "view", pr, "--json", "headRefOid,baseRefName"])
        if view_proc.returncode != 0:
            print(f"PR #{pr}: could not read the PR: {(view_proc.stderr or '').strip()[:200]}", file=sys.stderr)
            return 1
        view = json.loads(view_proc.stdout)
        head = view.get("headRefOid")
        base = view.get("baseRefName") or "main"
        if not head:
            print(f"PR #{pr}: no headRefOid — cannot evaluate required checks", file=sys.stderr)
            return 1
        result = require_green_block_reasons(pr, head, base, run=run)
        if result.reasons:
            print(
                f"PR #{pr}: refusing to arm auto-merge — required check(s) not green "
                f"(ENG-9680 / ENG-9668; required contexts resolved from {result.source}). "
                f"Fix or wait, then re-run:",
                file=sys.stderr,
            )
            for r in result.reasons:
                print(f"  - {r}", file=sys.stderr)
            return 1

    arm = run([a.replace("{pr}", pr) for a in ARM_ARGV])
    if arm.returncode != 0:
        print(
            f"PR #{pr}: `gh pr merge {pr} --auto --squash` failed (exit {arm.returncode}): "
            f"{(arm.stderr or arm.stdout or '').strip()[:300]}",
            file=sys.stderr,
        )
        return 1
    for line in (arm.stdout or "").strip(), (arm.stderr or "").strip():
        if line:
            print(line, file=sys.stderr)
    ok, verdict = confirm_armed(pr, run=run, sleep=sleep)
    if not ok:
        print(
            f"PR #{pr}: arm command landed but neither autoMergeRequest nor a merge-queue entry "
            f"read back (last reading: {verdict}) — NOT confirmed",
            file=sys.stderr,
        )
        return 1
    mode = "require-green" if args.require_green else "unconditional"
    what = {mq.ARMED: "auto-merge armed", mq.QUEUED: "enqueued in the merge queue", mq.MERGED: "already merged"}
    print(f"PR #{pr}: {what[verdict]} ({mode}), confirmed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
