#!/usr/bin/env python3
"""Gate: a bug / task / cleanup fix may not merge until Fleet records a verify verdict.

WHY THIS EXISTS. The PRD lane has `prd-verify-gate` in `ci-success.needs`, so a PRD's
implementation cannot merge until `prd:verify` stamps it. The bug/task/cleanup lane — the
lane that carries most of this repo's merges — needs the same hold. On 2026-08-27 six PRs
sat armed for auto-merge with no passing verdict. The only hold that worked was converting
them to draft, which any session undoes with `gh pr ready`.

── WHAT IT KEYS ON ────────────────────────────────────────────────────────────────
FLEET IS THE AUTHORITY. The gate reads the issue and the newest verify verdict through
Fleet's tools API with a CI key (`FLEET_CI_KEY`), never through Linear. Nothing a session
can do to GitHub alone satisfies this gate; only a verify run that recorded a row does.

PASS requires, on a gated kind (`bug` / `task` / `cleanup`):
  * the newest verdict for this pull request is `verified` or `merged`, AND
  * either its `headSha` is the PR's current head, OR the pull request's own change is the
    same at the verified commit X and at the head — matched by
    `git diff $(git merge-base BASE C) C | git patch-id --stable` (empty diffs never match).

An older pass under a newer `incomplete` / `blocked` fails. A post-verdict code commit fails.
A verified commit the checkout cannot fetch after one `git fetch` fails closed and names a
new verify run.

── SHAPES THE RULE WAS NEVER ABOUT (all PASS) ─────────────────────────────────────
  * no `ENG-nnnn` resolvable from head ref / title / body — not lane work,
    **except** an `agent/{fix,task,bug,prd,shape}-*` head ref (fail closed);
  * a body match counts as this PR's issue only under a closing verb;
  * its kind is not gated — `prd` has `PRD Verified`; `audit` / `idea` are not this lane;
  * a knowledge-only planning PR that cites an open gated issue it does not fix;
  * a `NOT-A-VERIFY-LANE-PR=<code>: <reason>` line whose CODE the gate can CHECK;
  * a knowledge-only `agent/shape-*` PR (shaping content only).

── THE ESCAPE MUST PROVE WHAT IT CLAIMS ───────────────────────────────────────────
Shape: `NOT-A-VERIFY-LANE-PR=<code>: <reason>`. Codes are a closed vocabulary; each names a
fact the gate reads off the Fleet issue (kind, position, lane) or off the PR's diff. A
position veto refuses every code while the issue sits at `implementing` / `review` /
`verifying` / `rework`. A `404 not-projected` fails closed, except an `issue-closed` /
`issue-cancelled` disclaimer that `GET /issues?query=<KEY>&include_closed=true` confirms.

── ITS OWN WORKFLOW ───────────────────────────────────────────────────────────────
A required context is a function of the HEAD SHA. The bug/task verify session pushes no
commit, so something must re-evaluate; this gate lives in its own workflow so `gh run
rerun` updates the context directly without re-running all of CI.

Exit 0 = may merge. Exit 1 = blocked, with the remediation flow printed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, NamedTuple

TYPE_BUG = "bug"
TYPE_TASK = "task"
TYPE_CLEANUP = "cleanup"

GATED_KINDS = frozenset({TYPE_BUG, TYPE_TASK, TYPE_CLEANUP})

DISCLAIMER_VETO_POSITIONS = frozenset({"implementing", "review", "verifying", "rework"})

CLOSED_POSITIONS_DONE = frozenset({"done"})
CLOSED_POSITIONS_CANCELLED = frozenset({"canceled", "cancelled", "duplicate"})

PASSING_VERDICTS = frozenset({"verified", "merged"})


def _tracker_prefix() -> str:
    """The issue-key prefix this repository's tracker uses, from its own answer."""
    env = (os.environ.get("LINEAR_KEY_PREFIX") or os.environ.get("TRACKER_KEY_PREFIX") or "").strip().rstrip("-")
    if env:
        return env
    here = os.getcwd()
    while True:
        path = os.path.join(here, "knowledge", "slots", "tracker-identity.md")
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            parent = os.path.dirname(here)
            if parent == here:
                return ""
            here = parent
            continue
        m = re.search(r"\*\*Key prefix\*\*\s*\|[^`\n]*`?([A-Za-z][A-Za-z0-9]*)-`?", text)
        return m.group(1) if m else ""


TRACKER_PREFIX = _tracker_prefix()
_KEY_SHAPE = re.escape(TRACKER_PREFIX) if TRACKER_PREFIX else r"[A-Z][A-Z0-9]{1,9}"

ISSUE_KEY_RE = re.compile(rf"\b({_KEY_SHAPE})-(\d{{1,6}})\b", re.IGNORECASE)

AGENT_LANE_KIND_RE = re.compile(
    r"^agent/(?:fix|task|bug|prd|shape)(?:[-/]|$)",
    re.IGNORECASE,
)

DISCLAIMER_KEY = "NOT-A-VERIFY-LANE-PR"
DISCLAIMER_RE = re.compile(
    rf"^[ \t]*{DISCLAIMER_KEY}=(?P<code>[a-z][a-z0-9-]{{0,40}}):[ \t]*(?P<reason>\S.*?)[ \t]*$",
    re.MULTILINE,
)
DISCLAIMER_LOOSE_RE = re.compile(rf"^[ \t]*{DISCLAIMER_KEY}\s*=\s*(?P<rest>.*?)[ \t]*$", re.MULTILINE)

KNOWLEDGE_ROOT = "knowledge/"
CITATION_VERB_RE = re.compile(rf"\brefs?\b[^\n]*?\b{_KEY_SHAPE}-\d{{1,6}}\b", re.IGNORECASE)
CLOSING_VERB_RE = re.compile(
    rf"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b[^\n]*?\b{_KEY_SHAPE}-\d{{1,6}}\b", re.IGNORECASE
)

SHAPE_HEAD_REF_RE = re.compile(r"^agent/shape-", re.IGNORECASE)
SHAPE_KNOWLEDGE_PREFIXES = (
    "knowledge/programs/",
    "knowledge/slices/",
    "knowledge/prds/",
    "knowledge/requirements/",
    "knowledge/features/",
    "knowledge/journeys/",
)
SHAPE_KNOWLEDGE_FILES = frozenset({"knowledge/programs.md", "knowledge/slices.md"})

HTTP_TIMEOUT_DEFAULT = 30.0


class PrContext(NamedTuple):
    body: str
    changed_paths: tuple[str, ...]


class FleetIssue(NamedTuple):
    key: str
    kind: str
    position: str
    lane_repo: str | None


class FleetVerdict(NamedTuple):
    id: int
    verdict: str
    head_sha: str


class FleetHttpError(Exception):
    """A Fleet read that cannot be treated as a pass."""

    def __init__(self, message: str, *, status: int | None = None, body: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.body = body


def is_agent_lane_ref(head_ref: str) -> bool:
    return bool(AGENT_LANE_KIND_RE.match((head_ref or "").strip()))


def is_shape_content_path(path: str) -> bool:
    p = (path or "").strip()
    if not p or p.startswith("/") or "\\" in p or any(seg in ("..", ".") for seg in p.split("/")):
        return False
    return p in SHAPE_KNOWLEDGE_FILES or p.startswith(SHAPE_KNOWLEDGE_PREFIXES)


def is_knowledge_only_shape_pr(head_ref: str, changed_paths: tuple[str, ...]) -> tuple[bool, str]:
    if not SHAPE_HEAD_REF_RE.match((head_ref or "").strip()):
        return False, ""
    if not changed_paths:
        return False, "the changed-path list is empty or unreadable, so the diff cannot be proven knowledge-only"
    outside = [path for path in changed_paths if not is_shape_content_path(path)]
    if outside:
        shown = ", ".join(f"`{x}`" for x in outside[:5])
        more = f" (+{len(outside) - 5} more)" if len(outside) > 5 else ""
        return False, f"{len(outside)} changed path(s) are not shaping content: {shown}{more}"
    return True, f"`{head_ref}` changes {len(changed_paths)} shaping-content path(s) and nothing else"


def extract_issue_key(head_ref: str, title: str, body: str) -> str | None:
    def key(m: re.Match[str]) -> str:
        return f"{TRACKER_PREFIX}-{m.group(2)}" if TRACKER_PREFIX else m.group(0).upper()

    for source in (head_ref, title):
        m = ISSUE_KEY_RE.search(source or "")
        if m:
            return key(m)
    for m in CLOSING_VERB_RE.finditer(body or ""):
        km = ISSUE_KEY_RE.search(m.group(0))
        if km:
            return key(km)
    return None


def disclaimer_claims(body: str) -> list[tuple[str, str]]:
    return [(m.group("code"), m.group("reason")) for m in DISCLAIMER_RE.finditer(body or "")]


def disclaimer_attempts(body: str) -> list[str]:
    return [m.group("rest") for m in DISCLAIMER_LOOSE_RE.finditer(body or "")]


def _code_not_gated_type(issue: FleetIssue, ctx: PrContext) -> tuple[bool, str]:
    kind = (issue.kind or "").strip().lower()
    if kind in GATED_KINDS:
        return False, (
            f"the linked issue IS kind `{kind}` — the claim contradicts the kind this gate decides scope from"
        )
    return True, f"the linked issue's kind is `{kind or 'unknown'}`, not bug/task/cleanup"


def _code_issue_closed(issue: FleetIssue, ctx: PrContext) -> tuple[bool, str]:
    pos = (issue.position or "").strip().lower()
    if pos in CLOSED_POSITIONS_DONE:
        return True, "the linked issue is already closed out — its lane is over, so this PR is not its pending fix"
    return False, (
        f"the linked issue's position is `{pos or 'unknown'}`, not `done` — it is still open, so a "
        "fix for it may still be in flight and this PR may be it"
    )


def _code_issue_cancelled(issue: FleetIssue, ctx: PrContext) -> tuple[bool, str]:
    pos = (issue.position or "").strip().lower()
    if pos in CLOSED_POSITIONS_CANCELLED:
        return True, "the linked issue was cancelled — there is no fix for `verify` to certify"
    return False, (
        f"the linked issue's position is `{pos or 'unknown'}`, not `canceled`/`duplicate` — it was not cancelled"
    )


def _code_other_repo_lane(issue: FleetIssue, ctx: PrContext) -> tuple[bool, str]:
    this_repo = (os.environ.get("GITHUB_REPOSITORY") or "").strip()
    lane = (issue.lane_repo or "").strip()
    if not lane:
        return False, (
            "the linked issue carries no other-repo lane, so its lane IS this repository — "
            "the claim contradicts the issue"
        )
    if this_repo and lane.lower() == this_repo.lower():
        return False, (
            f"the linked issue's lane is `{lane}`, which IS this repository (`{this_repo}`) — "
            "the claim contradicts the lane"
        )
    return True, f"the linked issue is dispatched to another repo's lane (`{lane}`)"


def _code_knowledge_only_citation(issue: FleetIssue, ctx: PrContext) -> tuple[bool, str]:
    if not ctx.changed_paths:
        return False, (
            "the gate could not read this PR's changed paths from the API, so a knowledge-only "
            "claim cannot be checked. This code's fact is the DIFF; it fails closed rather than "
            "taking the author's word for the scope"
        )
    outside = [path for path in ctx.changed_paths if not path.startswith(KNOWLEDGE_ROOT)]
    if outside:
        shown = ", ".join(f"`{path}`" for path in outside[:5])
        more = f" (+{len(outside) - 5} more)" if len(outside) > 5 else ""
        return False, (
            f"this PR changes {len(outside)} path(s) outside `{KNOWLEDGE_ROOT}` ({shown}{more}) "
            "— the diff contradicts a claim of knowledge-only scope, and a code that let a code "
            "change through on a 'planning' sentence would gut the gate"
        )
    if CLOSING_VERB_RE.search(ctx.body):
        return False, (
            "the PR body claims to FIX the linked issue (`Closes`/`Fixes`/`Resolves` next to an "
            "`ENG-` key). A planning PR cites with `Refs`; a fix is lane work that must go "
            "through `verify`"
        )
    if not CITATION_VERB_RE.search(ctx.body):
        return False, (
            "the PR body does not cite the linked issue with `Refs` — the shape is a planning PR "
            "that references the work an issue waits on, never one that delivers it"
        )
    return True, (
        f"every changed path is under `{KNOWLEDGE_ROOT}` and the body cites the issue with `Refs` "
        "rather than claiming to fix it"
    )


DISCLAIMER_CODES: dict[str, Any] = {
    "not-gated-type": (
        _code_not_gated_type,
        "the linked issue is not kind bug/task/cleanup",
    ),
    "issue-closed": (
        _code_issue_closed,
        "the `ENG-` key is cited, not fixed — that issue is already closed out",
    ),
    "issue-cancelled": (
        _code_issue_cancelled,
        "the linked issue was cancelled — no fix exists to verify",
    ),
    "issue-canceled": (
        _code_issue_cancelled,
        "alias of `issue-cancelled`",
    ),
    "other-repo-lane": (
        _code_other_repo_lane,
        "the fix and its verify verdict live in another repo's lane",
    ),
    "knowledge-only-citation": (
        _code_knowledge_only_citation,
        "a knowledge-only planning PR citing an open gated issue — every changed path under "
        "`knowledge/`, the body using `Refs` not a closing verb",
    ),
}

DISCLAIMER_ADVERTISED = (
    "not-gated-type",
    "issue-closed",
    "issue-cancelled",
    "other-repo-lane",
    "knowledge-only-citation",
)


def check_disclaimer(
    body: str,
    issue: FleetIssue,
    *,
    changed_paths: tuple[str, ...] = (),
) -> tuple[bool, str]:
    """(honoured, note) for the escape against LIVE Fleet issue state."""
    attempts = disclaimer_attempts(body)
    if not attempts:
        return False, ""

    claims = disclaimer_claims(body)
    if not claims:
        return False, (
            f"the PR body has a `{DISCLAIMER_KEY}=` line that is not a coded claim "
            f"({attempts[0][:80]!r}...). Free text is no longer accepted: the escape must "
            f"name a code this gate can CHECK. Required shape: "
            f"`{DISCLAIMER_KEY}=<code>: <reason>`."
        )
    if len(claims) > 1:
        return False, (
            f"the PR body carries {len(claims)} `{DISCLAIMER_KEY}=` claims "
            f"({', '.join(sorted(c for c, _ in claims))}). A PR has ONE reason for being "
            "outside the lane; naming several is a shotgun, not a claim. Keep exactly one."
        )

    code, reason = claims[0]
    entry = DISCLAIMER_CODES.get(code)
    if entry is None:
        return False, (
            f"`{DISCLAIMER_KEY}={code}:` names no code this gate knows. The vocabulary is "
            f"closed: {', '.join(DISCLAIMER_ADVERTISED)}."
        )

    pos = (issue.position or "").strip().lower()
    if pos in DISCLAIMER_VETO_POSITIONS:
        return False, (
            f"the escape is REFUSED outright while the issue is at `{pos}` — that position "
            "asserts a fix for this issue is in flight right now, so "
            f"`{DISCLAIMER_KEY}` cannot be true over it."
        )

    predicate, _meaning = entry
    ctx = PrContext(body=body, changed_paths=tuple(changed_paths))
    ok, why = predicate(issue, ctx)
    if not ok:
        return False, (f"`{DISCLAIMER_KEY}={code}:` is REFUSED — {why}. The stated reason was: {reason}")
    return True, f"`{DISCLAIMER_KEY}={code}:` holds — {why}. Stated reason: {reason}"


def read_changed_paths() -> tuple[str, ...]:
    path = os.environ.get("PR_CHANGED_PATHS_FILE", "").strip()
    if path:
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            return ()
        return tuple(line.strip() for line in text.splitlines() if line.strip())
    return tuple(line.strip() for line in os.environ.get("PR_CHANGED_PATHS", "").splitlines() if line.strip())


def _http_timeout() -> float:
    raw = (os.environ.get("FLEET_HTTP_TIMEOUT") or "").strip()
    if raw:
        try:
            return max(0.1, float(raw))
        except ValueError:
            pass
    return HTTP_TIMEOUT_DEFAULT


def _fleet_get(url: str, key: str) -> tuple[int, dict[str, Any] | None, str]:
    """GET `url` with Bearer auth. Returns (status, json-or-None, raw-body)."""
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=_http_timeout()) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            status = int(getattr(resp, "status", 200) or 200)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        status = int(exc.code)
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise FleetHttpError(f"could not reach Fleet at {url.split('?')[0]} ({reason})") from exc
    except TimeoutError as exc:
        raise FleetHttpError(f"Fleet timed out at {url.split('?')[0]}") from exc
    except OSError as exc:
        raise FleetHttpError(f"could not reach Fleet at {url.split('?')[0]} ({exc})") from exc

    payload: dict[str, Any] | None = None
    if raw.strip():
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                payload = loaded
        except json.JSONDecodeError:
            payload = None
    return status, payload, raw


def _fleet_message(payload: dict[str, Any] | None, raw: str) -> str:
    if payload:
        for field in ("message", "detail", "error"):
            value = payload.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()
    text = (raw or "").strip()
    return text[:500] if text else "(no body)"


def _require_env(*names: str) -> dict[str, str]:
    out: dict[str, str] = {}
    missing: list[str] = []
    for name in names:
        value = (os.environ.get(name) or "").strip()
        if not value:
            missing.append(name)
        else:
            out[name] = value
    if missing:
        raise FleetHttpError(
            "missing required environment "
            + ", ".join(f"`{n}`" for n in missing)
            + " — the gate cannot read Fleet without them"
        )
    return out


def fetch_issue(base_url: str, ci_key: str, issue_key: str) -> FleetIssue | None:
    """GET /api/tools/v1/issues/{key}. None means 404 not-projected (closed / unknown)."""
    url = f"{base_url.rstrip('/')}/api/tools/v1/issues/{urllib.parse.quote(issue_key, safe='')}"
    status, payload, raw = _fleet_get(url, ci_key)
    if status == 404:
        err = (payload or {}).get("error") if payload else None
        if err in ("not-projected", "unknown-key", "no-verdict") or err is None:
            return None
        raise FleetHttpError(
            f"Fleet refused {issue_key} ({status} {err}): {_fleet_message(payload, raw)}",
            status=status,
            body=raw,
        )
    if status in (401, 403):
        raise FleetHttpError(
            f"Fleet refused the CI key ({status}): {_fleet_message(payload, raw)}",
            status=status,
            body=raw,
        )
    if status >= 500:
        raise FleetHttpError(
            f"Fleet returned {status} reading {issue_key}: {_fleet_message(payload, raw)}",
            status=status,
            body=raw,
        )
    if status != 200 or not payload:
        raise FleetHttpError(
            f"Fleet returned {status} reading {issue_key}: {_fleet_message(payload, raw)}",
            status=status,
            body=raw,
        )
    kind = str(payload.get("kind") or "").strip().lower()
    position = str(payload.get("position") or "").strip().lower()
    lane = payload.get("lane")
    lane_repo: str | None = None
    if isinstance(lane, dict):
        repo = lane.get("repo")
        if isinstance(repo, str) and repo.strip():
            lane_repo = repo.strip()
    return FleetIssue(key=issue_key, kind=kind, position=position, lane_repo=lane_repo)


def search_closed_issue(base_url: str, ci_key: str, issue_key: str) -> str | None:
    """Position of `issue_key` from include_closed search, or None if absent."""
    qs = urllib.parse.urlencode({"query": issue_key, "include_closed": "true"})
    url = f"{base_url.rstrip('/')}/api/tools/v1/issues?{qs}"
    status, payload, raw = _fleet_get(url, ci_key)
    if status in (401, 403):
        raise FleetHttpError(
            f"Fleet refused the CI key ({status}): {_fleet_message(payload, raw)}",
            status=status,
            body=raw,
        )
    if status >= 500:
        raise FleetHttpError(
            f"Fleet returned {status} searching {issue_key}: {_fleet_message(payload, raw)}",
            status=status,
            body=raw,
        )
    if status != 200 or not payload:
        raise FleetHttpError(
            f"Fleet returned {status} searching {issue_key}: {_fleet_message(payload, raw)}",
            status=status,
            body=raw,
        )
    issues = payload.get("issues")
    if not isinstance(issues, list):
        return None
    want = issue_key.casefold()
    for row in issues:
        if not isinstance(row, dict):
            continue
        row_key = str(row.get("key") or "").strip()
        if row_key.casefold() != want:
            continue
        return str(row.get("position") or "").strip().lower() or None
    return None


def fetch_verdict(base_url: str, ci_key: str, repository: str, pr_number: str) -> FleetVerdict | None:
    """GET /api/tools/v1/verdicts?repository=&pr=&gate=verify (no sha). None = no-verdict."""
    qs = urllib.parse.urlencode({"repository": repository, "pr": pr_number, "gate": "verify"})
    url = f"{base_url.rstrip('/')}/api/tools/v1/verdicts?{qs}"
    status, payload, raw = _fleet_get(url, ci_key)
    if status == 404:
        err = (payload or {}).get("error") if payload else None
        if err == "verdicts-disabled":
            raise FleetHttpError(
                "Fleet verdict recording is off on this deployment (`FLEET_VERDICTS_V1` / "
                f"verdicts-disabled): {_fleet_message(payload, raw)}",
                status=status,
                body=raw,
            )
        if err in ("no-verdict", None):
            return None
        raise FleetHttpError(
            f"Fleet returned 404 reading verdicts: {_fleet_message(payload, raw)}",
            status=status,
            body=raw,
        )
    if status in (401, 403):
        raise FleetHttpError(
            f"Fleet refused the CI key ({status}): {_fleet_message(payload, raw)}",
            status=status,
            body=raw,
        )
    if status >= 500:
        raise FleetHttpError(
            f"Fleet returned {status} reading verdicts: {_fleet_message(payload, raw)}",
            status=status,
            body=raw,
        )
    if status != 200 or not payload:
        raise FleetHttpError(
            f"Fleet returned {status} reading verdicts: {_fleet_message(payload, raw)}",
            status=status,
            body=raw,
        )
    verdict = str(payload.get("verdict") or "").strip().lower()
    head_sha = str(payload.get("headSha") or payload.get("head_sha") or "").strip().lower()
    try:
        vid = int(payload.get("id") or 0)
    except (TypeError, ValueError):
        vid = 0
    if not verdict or not head_sha:
        return None
    return FleetVerdict(id=vid, verdict=verdict, head_sha=head_sha)


def _git(*args: str, check: bool = False, stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603 — fixed argv list, never shell
        ["git", *args],
        input=stdin,
        capture_output=True,
        check=check,
    )


def ensure_commit(sha: str) -> None:
    """Make sure `sha` is present locally; one shallow fetch if not (P6)."""
    probe = _git("cat-file", "-e", f"{sha}^{{commit}}")
    if probe.returncode == 0:
        return
    _git("fetch", "--no-tags", "--depth=1", "origin", sha)
    again = _git("cat-file", "-e", f"{sha}^{{commit}}")
    if again.returncode != 0:
        raise FleetHttpError(
            f"verified commit `{sha}` is unfetchable from origin after one "
            f"`git fetch --no-tags --depth=1 origin {sha}` — a new verify run is needed"
        )


def patch_id(base: str, commit: str) -> str | None:
    """Stable patch-id of the change from merge-base(base, commit)..commit. None if empty."""
    ensure_commit(commit)
    mb = _git("merge-base", base, commit)
    if mb.returncode != 0 or not mb.stdout.strip():
        return None
    merge_base = mb.stdout.strip().decode()
    diff = _git("diff", merge_base, commit)
    if diff.returncode != 0:
        return None
    if not diff.stdout.strip():
        return None
    pid = _git("patch-id", "--stable", stdin=diff.stdout)
    if pid.returncode != 0 or not pid.stdout.strip():
        return None
    # `git patch-id` prints: <hash> <commit-ish>\n
    first = pid.stdout.strip().split(None, 1)[0].decode()
    return first or None


def verdict_covers_head(
    *,
    verdict: FleetVerdict,
    head_sha: str,
    base_sha: str,
) -> tuple[bool, str]:
    """Whether the recorded verdict covers the PR's current head (exact or same patch-id)."""
    if verdict.verdict not in PASSING_VERDICTS:
        return False, (
            f"the newest `verify` verdict is `{verdict.verdict}` (id {verdict.id}) — "
            "an older pass does not survive a later refutation"
        )
    head = head_sha.strip().lower()
    verified = verdict.head_sha.strip().lower()
    if verified == head:
        return True, f"`verify` returned `{verdict.verdict}` at head `{head[:12]}` (exact match)"
    try:
        vid = patch_id(base_sha, verified)
        hid = patch_id(base_sha, head)
    except FleetHttpError:
        raise
    if vid is None or hid is None:
        return False, (
            f"the newest `{verdict.verdict}` verdict is at `{verified[:12]}`, not the current "
            f"head `{head[:12]}`, and one side has an empty diff so patch-id cannot match — "
            "a new verify run is needed"
        )
    if vid == hid:
        return True, (
            f"`verify` returned `{verdict.verdict}` at `{verified[:12]}`; the pull request's "
            f"own change matches the current head `{head[:12]}` by patch-id"
        )
    return False, (
        f"the newest `{verdict.verdict}` verdict is at `{verified[:12]}`, not the current head "
        f"`{head[:12]}`, and the pull request's own change differs (patch-id mismatch) — "
        "a new verify run is needed"
    )


def try_closed_disclaimer(
    body: str,
    *,
    base_url: str,
    ci_key: str,
    issue_key: str,
) -> tuple[bool, str]:
    """On 404 not-projected: honour issue-closed/cancelled only when the closed index confirms."""
    claims = disclaimer_claims(body)
    attempts = disclaimer_attempts(body)
    if not attempts:
        return False, ""
    if not claims:
        return False, (
            f"the PR body has a `{DISCLAIMER_KEY}=` line that is not a coded claim "
            f"({attempts[0][:80]!r}...). Free text is no longer accepted."
        )
    if len(claims) > 1:
        return False, (f"the PR body carries {len(claims)} `{DISCLAIMER_KEY}=` claims — keep exactly one.")
    code, reason = claims[0]
    if code not in ("issue-closed", "issue-cancelled", "issue-canceled"):
        return False, (
            f"`{DISCLAIMER_KEY}={code}:` cannot be checked because Fleet does not hold "
            f"`{issue_key}` on the board (not-projected), and only `issue-closed` / "
            f"`issue-cancelled` may be confirmed via the closed-issue index."
        )
    position = search_closed_issue(base_url, ci_key, issue_key)
    if position is None:
        return False, (
            f"`{DISCLAIMER_KEY}={code}:` is REFUSED — Fleet's closed-issue search returned no "
            f"row for `{issue_key}`. Stated reason: {reason}"
        )
    if code == "issue-closed":
        if position in CLOSED_POSITIONS_DONE:
            return True, (
                f"`{DISCLAIMER_KEY}={code}:` holds — closed-issue search has `{issue_key}` at "
                f"`{position}`. Stated reason: {reason}"
            )
        return False, (
            f"`{DISCLAIMER_KEY}={code}:` is REFUSED — closed-issue search has `{issue_key}` at "
            f"`{position}`, not `done`. Stated reason: {reason}"
        )
    if position in CLOSED_POSITIONS_CANCELLED:
        return True, (
            f"`{DISCLAIMER_KEY}={code}:` holds — closed-issue search has `{issue_key}` at "
            f"`{position}`. Stated reason: {reason}"
        )
    return False, (
        f"`{DISCLAIMER_KEY}={code}:` is REFUSED — closed-issue search has `{issue_key}` at "
        f"`{position}`, not `canceled`/`duplicate`. Stated reason: {reason}"
    )


def fail(msg: str, disclaimer_note: str = "") -> int:
    print(f"::error::Verify Gate: {msg}")
    print("")
    print("─" * 78)
    print("A `bug` / `task` / `cleanup` fix may not merge until `verify` has recorded a")
    print("passing verdict on Fleet for this pull request. The party that wrote the code")
    print("never certifies it.")
    print("")
    print(f"BLOCKED: {msg}")
    print("")
    print("To clear it:")
    print("  1. The implementer hands off — it does NOT merge its own work.")
    print("  2. A fresh `verify <KEY>` session rebuilds the cause ledger, neuters every")
    print("     named test, and records its verdict through Fleet (`record_verdict`).")
    print("  3. On a pass it re-triggers this gate and merges.")
    print("")
    if disclaimer_note:
        print("ESCAPE ATTEMPTED, NOT HONOURED:")
        print(f"  {disclaimer_note}")
        print("")
    print("If this PR is not lane work at all, put ONE line in the PR body:")
    print(f"     {DISCLAIMER_KEY}=<code>: <why this PR is not a verify-lane fix>")
    print("")
    print("  <code> is one of these, and the gate CHECKS each one:")
    for _code in DISCLAIMER_ADVERTISED:
        print(f"     · {_code:<16} {DISCLAIMER_CODES[_code][1]}")
    print("  No code is honoured while the issue is at implementing / review / verifying /")
    print("  rework — those say a fix is in flight for it right now.")
    print("─" * 78)
    return 1


def main() -> int:
    if os.environ.get("GITHUB_EVENT_NAME") not in (None, "", "pull_request", "merge_group"):
        print("Verify Gate: not a pull_request/merge_group event — nothing to gate.")
        return 0

    head_ref = os.environ.get("PR_HEAD_REF", "")
    title = os.environ.get("PR_TITLE", "")
    body = os.environ.get("PR_BODY", "")

    shape_changed = read_changed_paths()
    exempt, shape_note = is_knowledge_only_shape_pr(head_ref, shape_changed)
    if exempt:
        print(f"Verify Gate: PASS — knowledge-only shaping PR, not lane work: {shape_note}.")
        return 0

    key = extract_issue_key(head_ref, title, body)
    if not key:
        if is_agent_lane_ref(head_ref):
            return fail(
                f"head ref `{head_ref}` is an agent lane branch "
                f"(`agent/fix|task|bug|prd|shape-…`) but no `ENG-nnnn` resolves from the "
                f"head ref, title, or a closing body verb. That is unverifiable lane work, "
                f"not a pass (ENG-14453). Rename the branch to carry the issue key "
                f"(e.g. `agent/task-eng-1234`), or put the key in the title / a "
                f"`Fixes`/`Closes`/`Resolves` body line, so this gate can read the issue's "
                f"verify verdict. Armed auto-merge must not ship agent lane work the "
                f"verifier has never looked at."
            )
        print("Verify Gate: PASS — no `ENG-nnnn` in head ref, title or body; not lane work.")
        return 0

    try:
        env = _require_env("FLEET_URL", "FLEET_CI_KEY", "PR_HEAD_SHA", "PR_BASE_SHA", "GITHUB_REPOSITORY")
    except FleetHttpError as exc:
        return fail(str(exc))

    fleet_url = env["FLEET_URL"]
    ci_key = env["FLEET_CI_KEY"]
    head_sha = env["PR_HEAD_SHA"].lower()
    base_sha = env["PR_BASE_SHA"].lower()
    repository = env["GITHUB_REPOSITORY"]
    pr_number = (os.environ.get("PR_NUMBER") or "").strip()
    if not pr_number:
        return fail("missing required environment `PR_NUMBER` — the gate cannot bind a verdict to this pull request")

    try:
        issue = fetch_issue(fleet_url, ci_key, key)
    except FleetHttpError as exc:
        return fail(str(exc))

    changed_paths = read_changed_paths()

    if issue is None:
        try:
            honoured, note = try_closed_disclaimer(body, base_url=fleet_url, ci_key=ci_key, issue_key=key)
        except FleetHttpError as exc:
            return fail(str(exc))
        if honoured:
            print(f"Verify Gate: PASS — {key}: {note}")
            return 0
        return fail(
            f"{key} is not in Fleet's projection (not-projected / unknown), so the lane state "
            "cannot be read. An undeterminable verdict is not a pass." + (f" Escape note: {note}" if note else ""),
            disclaimer_note=note,
        )

    honoured, disclaimer_note = check_disclaimer(body, issue, changed_paths=changed_paths)
    if honoured:
        print(f"Verify Gate: PASS — {key}: {disclaimer_note}")
        return 0

    if issue.kind not in GATED_KINDS:
        if disclaimer_note:
            print(f"Verify Gate: note — {disclaimer_note}")
        print(f"Verify Gate: PASS — {key}: kind `{issue.kind or 'unknown'}` is not bug/task/cleanup — not this lane")
        return 0

    try:
        verdict = fetch_verdict(fleet_url, ci_key, repository, pr_number)
    except FleetHttpError as exc:
        return fail(f"{key}: {exc}", disclaimer_note=disclaimer_note)

    if verdict is None:
        return fail(
            f"{key}: no verdict recorded for this pull request — nothing has independently checked this fix",
            disclaimer_note=disclaimer_note,
        )

    try:
        ok, why = verdict_covers_head(verdict=verdict, head_sha=head_sha, base_sha=base_sha)
    except FleetHttpError as exc:
        return fail(f"{key}: {exc}", disclaimer_note=disclaimer_note)

    if not ok:
        return fail(f"{key}: {why}", disclaimer_note=disclaimer_note)

    if disclaimer_note:
        print(f"Verify Gate: note — {disclaimer_note}")
    print(f"Verify Gate: PASS — {key}: {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
