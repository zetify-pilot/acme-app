#!/usr/bin/env python3
"""Gate: a bug / task / cleanup fix may not merge until Fleet records a verify verdict.

WHY THIS EXISTS. The PRD lane has `prd-verify-gate` in `ci-success.needs`, so a PRD's
implementation cannot merge until `prd:verify` stamps it. The bug/task/cleanup lane — the
lane that carries most of this repo's merges — needs the same hold. On 2026-08-27 six PRs
sat armed for auto-merge with no passing verdict. The only hold that worked was converting
them to draft, which any session undoes with `gh pr ready`.

── WHAT IT KEYS ON ────────────────────────────────────────────────────────────────
FLEET IS THE AUTHORITY. The gate reads the issue and the newest verify verdict through
Fleet's tools API with a CI key (`FLEET_CI_KEY`), never through a tracker client. Nothing a session
can do to GitHub alone satisfies this gate; only a verify run that recorded a row does.

PASS requires, on a gated kind (`bug` / `task` / `cleanup`):
  * the pull request CLAIMS exactly ONE issue — a batch PR that closes several is refused,
    because a verdict is recorded per issue and this gate is one check for the whole PR
    (so a batch fix must be split first); AND
  * the newest verdict for that WORK ITEM on this pull request is `verified` or `merged`
    (read with `workKey`, so a sibling issue's verdict cannot mask it), AND
  * either its `headSha` is the PR's current head, OR the pull request's own change is the
    same at the verified commit X and at the head — matched by
    `git diff $(git merge-base BASE C) C | git patch-id --stable` (empty diffs never match).

An older pass under a newer `incomplete` / `blocked` fails. A post-verdict code commit fails.
A verified commit the checkout cannot fetch after one `git fetch` fails closed and names a
new verify run.

A TRANSIENT READ IS RETRIED. A Fleet read that answers `429` / `502` / `503` / `504`
("Fleet's database is busy … try again in a moment"), or fails on `TimeoutError` / `URLError` /
`OSError`, is retried with exponential backoff and jitter (honouring `Retry-After`) for a
bounded window — 150 s per read, 270 s across the whole run, well inside the step's 8-minute
ceiling — before the gate fails closed, so a contended Fleet no longer fails this
required check and ejects a green, already-verified PR from the merge queue. Each retry is
logged. Every attempt failing still fails closed, with a message that says Fleet was
UNAVAILABLE — never "no verdict", never pass-on-error. A 4xx other than 429 is never retried.

── SHAPES THE RULE WAS NEVER ABOUT (all PASS) ─────────────────────────────────────
  * no `ENG-nnnn` resolvable from head ref / title / body — not lane work,
    **except** an `agent/{fix,task,bug,prd,shape}-*` head ref (fail closed). On a tracker
    whose `tracker-identity` answer says its keys have NO prefix (GitHub Issues) the key is
    `owner/repo#n` (`#n` qualified with this repository) and no `XYZ-n` key is ever read;
    a repository with no readable answer keeps the generic `[A-Z][A-Z0-9]{1,9}-n` shape;
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

import datetime
import email.utils
import json
import os
import random
import re
import subprocess
import time
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


#: The slot line answering "what is the issue-key prefix": the legacy table row
#: (`| **Key prefix** | `XYZ-` … |`) or the `## Answers` bullet the bootstrap writes
#: (`- **key-prefix** — XYZ- …`, or `— none: …` on a tracker whose keys carry no prefix).
#: KEEP IN STEP with `_repo.py`: CI copies this gate ALONE out of the base ref, so it cannot
#: import `_repo`; `test_shipped_tracker_no_key_prefix` holds the two parsers to one table.
_KEY_PREFIX_LINE_RE = re.compile(r"\*\*key[ _-]?prefix\*\*\s*(?:\||—|–|:|-)\s*(?P<value>[^\n|]*)", re.IGNORECASE)
_KEY_PREFIX_VALUE_RE = re.compile(r"(?:^|[\s`])(?P<prefix>[A-Za-z][A-Za-z0-9]*)-(?=[`\s(]|$)")
_NO_KEY_PREFIX_RE = re.compile(r"`?(?:none|no(?:\s+key)?\s+prefix)\b", re.IGNORECASE)


def parse_key_prefix(text: str) -> str | None:
    """A `tracker-identity` answer's key prefix: `"XYZ"`, `""` for an explicit none, None for no answer.

    `""` and None are different facts: `""` is a tracker whose keys have no prefix (GitHub
    Issues, `owner/repo#n`), None is a repository that has not answered.
    """
    for m in _KEY_PREFIX_LINE_RE.finditer(text or ""):
        value = m.group("value").strip()
        if _NO_KEY_PREFIX_RE.match(value):
            return ""
        found = _KEY_PREFIX_VALUE_RE.search(value)
        if found:
            return found.group("prefix")
    return None


def _tracker_prefix_answer() -> str | None:
    """This repository's key prefix (see `parse_key_prefix`): the environment, else its own answer."""
    env = (os.environ.get("TRACKER_KEY_PREFIX") or "").strip().rstrip("-")
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
                return None
            here = parent
            continue
        return parse_key_prefix(text)


_PREFIX_ANSWER = _tracker_prefix_answer()
TRACKER_PREFIX = _PREFIX_ANSWER or ""
#: The repository answered that its tracker's keys carry no prefix: an issue is `owner/repo#n`
#: (`#n` inside the repository), the key Fleet's GitHub tracker stores. Such a tracker has no
#: `XYZ-n` key at all, so none is read — a branch name or a slice/program id is never an issue.
NO_KEY_PREFIX = _PREFIX_ANSWER == ""

_GITHUB_REPO = r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}"
if NO_KEY_PREFIX:
    # Not after a word character, `/`, `.`, `&` or `#`: a URL fragment or an HTML entity is no issue.
    _KEY = rf"(?<![\w./&#-])(?:{_GITHUB_REPO})?#\d{{1,7}}\b"
    ISSUE_KEY_RE = re.compile(rf"(?<![\w./&#-])(?P<repo>{_GITHUB_REPO})?#(?P<num>\d{{1,7}})\b")
else:
    _KEY_SHAPE = re.escape(TRACKER_PREFIX) if TRACKER_PREFIX else r"[A-Z][A-Z0-9]{1,9}"
    _KEY = rf"\b{_KEY_SHAPE}-\d{{1,6}}\b"
    ISSUE_KEY_RE = re.compile(rf"\b(?P<prefix>{_KEY_SHAPE})-(?P<num>\d{{1,6}})\b", re.IGNORECASE)


def _this_repository() -> str:
    """`owner/name` of the repository under test: `GITHUB_REPOSITORY`, else `origin`."""
    env = (os.environ.get("GITHUB_REPOSITORY") or "").strip()
    if env:
        return env
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    tail = url.rsplit(":", 1)[-1] if url.startswith("git@") else "/".join(url.rstrip("/").split("/")[-2:])
    tail = tail.removesuffix(".git")
    return tail if re.fullmatch(_GITHUB_REPO, tail) else ""


def _issue_key(m: re.Match[str]) -> str | None:
    """The canonical key an `ISSUE_KEY_RE` match names, or None when it cannot be named.

    A prefix tracker: `XYZ-n`. A no-prefix tracker: `owner/repo#n`, a bare `#n` qualified with
    this repository (None when that is unknown — a key is never guessed).
    """
    if NO_KEY_PREFIX:
        repo = m.group("repo") or _this_repository()
        return f"{repo}#{m.group('num')}" if repo else None
    return f"{TRACKER_PREFIX}-{m.group('num')}" if TRACKER_PREFIX else m.group(0).upper()


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
CITATION_VERB_RE = re.compile(rf"\brefs?\b[^\n]*?{_KEY}", re.IGNORECASE)
CLOSING_VERB_RE = re.compile(rf"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b[^\n]*?{_KEY}", re.IGNORECASE)
#: The verbs that govern a CLAIM, in their third-person present form only (`Closes` / `Fixes`
#: / `Resolves`). The bare and past-participle forms (`close`, `closed`, `fixed`, `resolved`)
#: are NOT claims: in PR prose they are citations of work already done — a sibling described
#: as "same class as closed" (or "resolved") is cited, not claimed — and counting the sibling
#: key beside them refused a one-issue pull request as a batch.
_CLAIM_VERB = r"(?:closes|fixes|resolves)"
_CLAIM_KEY = _KEY
CLAIMED_KEYS_RE = re.compile(
    rf"(?<![/:\w]){_CLAIM_VERB}:?[ \t]+{_CLAIM_KEY}"
    rf"(?:[ \t]*(?:,|&|\band\b)[ \t]*(?:{_CLAIM_VERB}:?[ \t]+)?{_CLAIM_KEY})*",
    re.IGNORECASE,
)

SHAPE_HEAD_REF_RE = re.compile(r"^agent/shape-", re.IGNORECASE)
#: The service-written provenance header at the top of a Fleet-opened pull request names the issue
#: by its own (untrusted) title. A title such as `Resolve ENG-1` must not read as a completing
#: claim, so every body scan sees the body without this fenced block. `place` writes markers
#: inclusive; half a marker is not a block and is left as it is.
_PROVENANCE_START = "<!-- fleet-service:pr-provenance:start -->"
_PROVENANCE_END = "<!-- fleet-service:pr-provenance:end -->"


def strip_provenance(body: str) -> str:
    """The body without the service-written provenance block, markers inclusive."""
    start = body.find(_PROVENANCE_START)
    if start < 0:
        return body
    end = body.find(_PROVENANCE_END, start)
    if end < 0:
        return body
    return body[:start] + body[end + len(_PROVENANCE_END) :]


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

#: How many times a Fleet read is attempted before the gate fails closed. A transient
#: Fleet/network timeout is not a verdict, so the read is retried a bounded number of times
#: with backoff; a green, already-verified PR must not be ejected from the merge queue over
#: one hiccup. Every attempt failing still fails closed — bounded retry, never pass-on-error.
HTTP_RETRY_ATTEMPTS_DEFAULT = 12
#: Base delay (seconds) of the exponential backoff: the n-th retry waits about
#: `base * 2**n`, capped at `HTTP_RETRY_MAX_DELAY`, with jitter so concurrent merge-queue
#: groups do not retry a contended Fleet in lockstep.
HTTP_RETRY_BACKOFF_DEFAULT = 2.0
HTTP_RETRY_MAX_DELAY = 30.0
#: How long one Fleet read keeps retrying a transient failure before it fails closed.
#: Fleet's "database is busy" 503 clears within a minute or two; 150 s rides it out.
HTTP_RETRY_WINDOW_DEFAULT = 150.0
#: The whole run's retry budget across all of its Fleet reads (issue, search, verdict), so
#: three back-to-back outages cannot outlast the workflow step's `timeout-minutes: 8`.
HTTP_RETRY_BUDGET_DEFAULT = 270.0
#: HTTP statuses that mean "Fleet is momentarily unavailable", never an answer about the PR.
TRANSIENT_HTTP_STATUSES = frozenset({429, 502, 503, 504})


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


class FleetTransientError(FleetHttpError):
    """A Fleet read that failed transiently (network error, timeout, or 429/502/503/504) —
    retried before failing closed.

    Subclasses `FleetHttpError` so every existing `except FleetHttpError` still catches it once
    the retries are exhausted; the distinct type is what marks it retryable in `_fleet_get`."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        body: str = "",
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, status=status, body=body)
        self.retry_after = retry_after


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
    for source in (head_ref, title):
        m = ISSUE_KEY_RE.search(source or "")
        if m and (k := _issue_key(m)):
            return k
    for m in CLOSING_VERB_RE.finditer(body or ""):
        km = ISSUE_KEY_RE.search(m.group(0))
        if km and (k := _issue_key(km)):
            return k
    return None


def claimed_issue_keys(head_ref: str, title: str, body: str) -> list[str]:
    """Every issue key this pull request CLAIMS to fix, in order, de-duplicated.

    A claim is:
    - every key in the head ref (the fleet mints `agent/fix-<key>` with exactly one),
    - in the title: keys a closing keyword GOVERNS (`Fixes A and B`), else at most the
      *first* key (the subject — `[KEY-1] … after KEY-2 landed` cites KEY-2, it does not
      claim it),
    - in the body: keys a closing keyword GOVERNS (`Closes KEY`, `Fixes: KEY`,
      `Resolves KEY, KEY and KEY`). Only the third-person form (`Closes` / `Fixes` /
      `Resolves`) governs a claim; the past participle (`closed` / `fixed` / `resolved`)
      is a citation of work already done and never claims the key beside it.

    A key that merely shares a line with the word "fix" is a citation, not a claim — "the
    posture KEY-1's fix took", a cause-ledger `**FIXED**` row, a quoted `/…:bug:fix KEY`
    command, or "same class as closed KEY-2". Reading every key on such a line (or every
    key in a title) refused one-issue pull requests as batches.

    **A PR that claims more than one issue cannot be certified where it stands.** A verify verdict
    is recorded per WORK ITEM (the issue), so a batch PR — one commit per issue, one shared head —
    needs a verdict for each issue, while this gate is a single check for the whole pull request.
    The first session to record does not decide the rest, and the gate cannot name which issue its
    one passing verdict is about. Such work must be split: one pull request per issue.
    """
    seen: list[str] = []

    def remember(m: re.Match[str]) -> None:
        k = _issue_key(m)
        if k and k.casefold() not in {s.casefold() for s in seen}:
            seen.append(k)

    for m in ISSUE_KEY_RE.finditer(head_ref or ""):
        remember(m)

    title_s = title or ""
    title_claims = list(CLAIMED_KEYS_RE.finditer(title_s))
    if title_claims:
        for claim in title_claims:
            for m in ISSUE_KEY_RE.finditer(claim.group(0)):
                remember(m)
    else:
        first = ISSUE_KEY_RE.search(title_s)
        if first:
            remember(first)

    for claim in CLAIMED_KEYS_RE.finditer(body or ""):
        for m in ISSUE_KEY_RE.finditer(claim.group(0)):
            remember(m)
    return seen


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


def _http_retry_attempts() -> int:
    raw = (os.environ.get("FLEET_HTTP_RETRY_ATTEMPTS") or "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return HTTP_RETRY_ATTEMPTS_DEFAULT


def _http_retry_backoff() -> float:
    raw = (os.environ.get("FLEET_HTTP_RETRY_BACKOFF") or "").strip()
    if raw:
        try:
            return max(0.0, float(raw))
        except ValueError:
            pass
    return HTTP_RETRY_BACKOFF_DEFAULT


def _env_seconds(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if raw:
        try:
            return max(0.0, float(raw))
        except ValueError:
            pass
    return default


def _http_retry_window() -> float:
    return _env_seconds("FLEET_HTTP_RETRY_WINDOW", HTTP_RETRY_WINDOW_DEFAULT)


def _http_retry_budget() -> float:
    return _env_seconds("FLEET_HTTP_RETRY_BUDGET", HTTP_RETRY_BUDGET_DEFAULT)


#: Indirections the tests replace with a fake clock, so a 150 s window runs in milliseconds.
_monotonic = time.monotonic
_sleep = time.sleep
_jitter = random.uniform

#: Seconds this process has already spent retrying Fleet reads — the run-wide budget's ledger.
_retry_spent = 0.0


def _parse_retry_after(value: str | None) -> float | None:
    """`Retry-After` as seconds: delta-seconds or an HTTP-date; None when absent/unparseable."""
    text = (value or "").strip()
    if not text:
        return None
    try:
        return max(0.0, float(text))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    return max(0.0, (when - datetime.datetime.now(datetime.timezone.utc)).total_seconds())


def _fleet_get_once(url: str, key: str) -> tuple[int, dict[str, Any] | None, str]:
    """One GET `url` with Bearer auth. Returns (status, json-or-None, raw-body)."""
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
        if status in TRANSIENT_HTTP_STATUSES:
            retry_after = _parse_retry_after(exc.headers.get("Retry-After") if exc.headers else None)
            detail = raw.strip()
            try:
                loaded = json.loads(raw) if detail else None
            except json.JSONDecodeError:
                loaded = None
            message = _fleet_message(loaded if isinstance(loaded, dict) else None, raw)
            raise FleetTransientError(
                f"Fleet returned {status} at {url.split('?')[0]}: {message}",
                status=status,
                body=raw,
                retry_after=retry_after,
            ) from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise FleetTransientError(f"could not reach Fleet at {url.split('?')[0]} ({reason})") from exc
    except TimeoutError as exc:
        raise FleetTransientError(f"Fleet timed out at {url.split('?')[0]}") from exc
    except OSError as exc:
        raise FleetTransientError(f"could not reach Fleet at {url.split('?')[0]} ({exc})") from exc

    payload: dict[str, Any] | None = None
    if raw.strip():
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                payload = loaded
        except json.JSONDecodeError:
            payload = None
    return status, payload, raw


def _fleet_get(url: str, key: str) -> tuple[int, dict[str, Any] | None, str]:
    """GET `url`, riding out a transient Fleet failure with bounded backoff, then failing closed.

    A Fleet 429/502/503/504 ("database is busy … try again in a moment"), a timeout or a network
    error is not a verdict: retrying it keeps a required check from failing (and a green PR from
    being ejected from the merge queue) over a moment of contention. The
    n-th retry waits `base * 2**n` (capped, jittered), or the server's `Retry-After` when that is
    longer, until the per-read window or the run-wide budget runs out. Then the gate fails
    closed with a message that says Fleet was UNAVAILABLE — a transient failure is never read
    as "no verdict" and never as a pass. Any other status (a 4xx answer, a 500) returns at once.
    """
    global _retry_spent
    attempts = _http_retry_attempts()
    base = _http_retry_backoff()
    window = _http_retry_window()
    budget = _http_retry_budget()
    path = url.split("?")[0]
    start = _monotonic()
    last: FleetTransientError | None = None
    made = 0
    try:
        for attempt in range(attempts):
            made = attempt + 1
            try:
                return _fleet_get_once(url, key)
            except FleetTransientError as exc:
                last = exc
            if attempt >= attempts - 1:
                break
            elapsed = _monotonic() - start
            remaining = min(window - elapsed, budget - _retry_spent - elapsed)
            if remaining <= 0:
                break
            delay = min(HTTP_RETRY_MAX_DELAY, base * (2**attempt))
            delay = _jitter(delay / 2, delay) if delay > 0 else 0.0
            if last.retry_after is not None:
                delay = max(delay, last.retry_after)
            delay = min(delay, remaining)
            print(
                f"Verify Gate: Fleet transiently unavailable on attempt {made} ({last}); "
                f"retrying in {delay:.1f}s ({elapsed:.0f}s of {window:.0f}s window used)",
                flush=True,
            )
            _sleep(delay)
    finally:
        if last is not None:
            _retry_spent += _monotonic() - start
    assert last is not None
    elapsed = _monotonic() - start
    raise FleetHttpError(
        f"Fleet was unavailable — {made} attempt(s) over {elapsed:.0f}s reading {path} all failed "
        f"transiently; the last: {last}. This is NOT a missing verdict: nothing about this pull "
        "request was read. Re-run the check (or re-enqueue the PR) once Fleet recovers.",
        status=last.status,
        body=last.body,
    ) from last


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


def fetch_verdict(
    base_url: str, ci_key: str, repository: str, pr_number: str, work_key: str = ""
) -> FleetVerdict | None:
    """GET /api/tools/v1/verdicts?repository=&pr=&gate=verify[&workKey=] (no sha). None = no-verdict.

    `work_key` scopes the read to the issue this PR is about, so a batch PR's other issues cannot
    mask the one being gated.
    """
    params = {"repository": repository, "pr": pr_number, "gate": "verify"}
    if work_key:
        params["workKey"] = work_key
    qs = urllib.parse.urlencode(params)
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


AUDIT_CLOSED_RE = re.compile(
    r"\bis an? audit issue\b.*(?:"
    r"\bnot on Fleet's board\b"
    r"|\bindex holds closed\b.*\ba person['\u2019]s close stays theirs\b"
    r")",
    re.IGNORECASE | re.DOTALL,
)


def is_closed_audit_carrier(exc: FleetHttpError, changed_paths: tuple[str, ...]) -> bool:
    """A 403 that says "audit issue ... closed", whether Fleet's census never boarded it or a
    person closed it.

    An audit carrier has no verify run by design (`audit` is not bug/task/cleanup), and Fleet
    answers 403 once the issue is closed and off the board, so reading it raised before any
    escape line was evaluated and ejected armed record PRs from the merge queue. Only that
    answer — whether in the older "not on Fleet's board" wording or the newer person-closed
    "index holds closed ... a person's close stays theirs" wording — and only for a PR whose
    every changed path is under `knowledge/`, is a non-lane PR; any other 401/403 stays a hard
    failure.
    """
    if exc.status != 403 or not AUDIT_CLOSED_RE.search(str(exc)):
        return False
    return bool(changed_paths) and all(p.startswith("knowledge/") for p in changed_paths)


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
    body = strip_provenance(os.environ.get("PR_BODY", ""))

    shape_changed = read_changed_paths()
    exempt, shape_note = is_knowledge_only_shape_pr(head_ref, shape_changed)
    if exempt:
        print(f"Verify Gate: PASS — knowledge-only shaping PR, not lane work: {shape_note}.")
        return 0

    claimed = claimed_issue_keys(head_ref, title, body)
    if len(claimed) > 1:
        shown = ", ".join(f"`{k}`" for k in claimed[:6]) + (" …" if len(claimed) > 6 else "")
        return fail(
            f"this pull request claims {len(claimed)} issues ({shown}) — a verify verdict is "
            f"recorded per issue, but this gate is ONE check for the whole pull request and cannot "
            f"certify a batch issue by issue. Split it into one pull request per issue; each then "
            f"carries its own verdict."
        )

    key = claimed[0] if claimed else extract_issue_key(head_ref, title, body)
    if not key:
        if is_agent_lane_ref(head_ref):
            return fail(
                f"head ref `{head_ref}` is an agent lane branch "
                f"(`agent/fix|task|bug|prd|shape-…`) but no `ENG-nnnn` resolves from the "
                f"head ref, title, or a closing body verb. That is unverifiable lane work, "
                f"not a pass. Rename the branch to carry the issue key "
                f"(e.g. `agent/task-<key>`), or put the key in the title / a "
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

    changed_paths = read_changed_paths()

    try:
        issue = fetch_issue(fleet_url, ci_key, key)
    except FleetHttpError as exc:
        if is_closed_audit_carrier(exc, changed_paths):
            print(f"Verify Gate: PASS — {key} is a closed audit carrier (no verify run by design): {exc}")
            return 0
        return fail(str(exc))

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
        verdict = fetch_verdict(fleet_url, ci_key, repository, pr_number, work_key=key)
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
