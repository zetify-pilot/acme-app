#!/usr/bin/env python3
"""Gate: a PRD's implementation may not merge until `prd:verify` has passed.

WHY THIS EXISTS. `prd:implement` opens a PR and hands off; `prd:verify`
runs in a fresh session, refutes the PASSes, stamps `status: verified`, and only then
ships. Until this check existed, every part of that was a CONVENTION IN A PROMPT —
nothing stopped a session from merging its own unverified work, and the only required
check (`CI Success`) knew nothing about it. Measured: of 289 PRDs completed before the
implement→verify split, 0 reached main unverified; of the first 20 completed after it,
4 did (0320, 0334, 0358, 0359) — a 20% leak, silent, and each one also froze every
downstream PRD that depended on it (only `shipped` satisfies a dependent).

The `verified` stamp is committed ON THE WORK BRANCH and merges with the PR (see
verify.md Step 5), so reading it from the PR head is well-defined and needs no
post-merge cooperation from anyone.

Forging the stamp is already blocked elsewhere: validate_tracking_metadata.py enforces
that `shipped` is preceded by `verified` and that only `by: verify` may stamp
`verified`. This check adds the missing half — that the stamp exists BEFORE the merge.

Runs on pull_request events only; a no-op elsewhere (a push to main is a merge that
already happened — that case is caught by the daemon's _arm_verify_from_github alarm).

A legitimately cross-repo PRD is not a special case here and needs no exemption: per
knowledge/decisions/2026-07-22-cross-repo-prd-ac-scope-split-not-partial-ship-status.md,
a same-PRD AC is never cross-repo-only — that AC is split into its own tracked companion
issue at design time, so every PRD this gate sees is, by construction, fully verifiable
and mergeable from this repo alone.

A PR that trips the gate by ACCIDENT has one narrow, explicit escape: a
`NOT-IMPLEMENTING-PRD=<num>: <reason>` line in the PR body (see `DISCLAIMER_RE`). That
escape was DOCUMENTED by this file's own failure message from the day it was written and
IMPLEMENTED only much later — the message told authors to "say so explicitly in the PR
body" while the workflow step passed no `PR_BODY` at all and nothing here ever parsed
one, so every PR that followed the instruction changed nothing and stayed blocked
(found on PR #6844, whose body says so in as many words).

A `verified` stamp is NOT sufficient for a PR that touches the PRD's own directory
(`SHIP_REQUIRED_OK` below) — only `shipped`/`cancelled` may merge there. A PR once
merged a PRD at `verified` by calling `gh pr merge --auto` directly instead of
`push ship`, permanently corrupting its ship-state — nothing short
of a hard gate on the PRD's own merge catches that, since `CI Success` knew nothing
about the distinction between "verified" and "shipped" either.

Exit 0 = may merge. Exit 1 = blocked, with the remediation flow printed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path

PRD_DIR_RE = re.compile(r"^knowledge/prds/(\d{4})-[^/]+/")
PRD_NUM_RE = re.compile(r"(?<!\d)(\d{4})(?!\d)")
STATUS_RE = re.compile(r"^status:\s*([a-z-]+)\s*$", re.MULTILINE)

# Statuses that mean "verification has happened". `shipped` is included because a PR may
# legitimately carry an already-shipped PRD's docs.
VERIFIED_OK = {"verified", "shipped", "cancelled"}

# For a PRD whose OWN DIRECTORY this PR touches — the definitive "this PR IS that PRD's
# work PR" signal (design/plan/implement/verify/ship-repair all edit frontmatter inside
# `knowledge/prds/NNNN-*/`) — `verified` is NOT enough; only `shipped`/`cancelled` may
# merge. `verified` is the audit-passed-but-not-yet-shipped stamp `prd:verify`
# commits LOCALLY; `push ship` immediately supersedes it with the `shipped`
# commit and pushes both together in ONE push (verify.md: "do not push it yourself"), so
# a compliant PR's HEAD never legitimately shows `verified` without `shipped` alongside
# it. PR #4218 merged PRD 0377 by calling `gh pr merge --auto` directly instead of
# `push ship`, landing `main` at `verified` and freezing it there forever with
# no automation to reconcile it — this turns Rule F (autonomous-drive.md,
# "the merge IS the ship") from prose into a gate for the one PR where it's unambiguous
# which PRD is being merged.
#
# Deliberately NOT applied to a PRD referenced only via branch/title text (no directory
# touched) — that is a weaker, over-detectable signal (see `referenced_prds`) and may
# not be this PR's own work at all; the looser `VERIFIED_OK` above still governs it.
SHIP_REQUIRED_OK = {"shipped", "cancelled"}

# ── The non-implementation disclaimer ────────────────────────────────────────────────
# One line per PRD in the PR BODY, each naming ONE four-digit number and a reason:
#
#   NOT-IMPLEMENTING-PRD=0485: adds `implements:` frontmatter only; touches no code 0485 owns
#
# Shape deliberately copied from the repo's existing body-escape,
# `SUBMODULE_REVERT_INTENDED=<path>: <reason>` (submodule_pointer_premerge_check.py): an
# explicit machine token, ONE named target, a MANDATORY reason. Prose is not accepted —
# "this PR does not implement PRD 0482-0487" is a range, and a range is the blanket
# suppression this escape must not be. The reason is required because the escape's only
# real strength is that it puts an attributable claim in the PR record: a false one is a
# written lie, greppable forever, not a silent bypass.
#
# WHY AN ESCAPE IS SAFE HERE AT ALL, given "the party that writes the code does not
# certify it". The gate's three signals are a UNION of one strong and two weak ones
# (`referenced_prds`). The two weak ones — a number in the branch or the title — grant an
# author NOTHING: anyone wanting to merge a PRD's implementation unverified would simply
# not name the number, and the gate never fires. So a disclaimer there removes no
# protection that existed, and is honoured on its own.
#
# The load-bearing signal is `own_dir` — the PRD's own directory, which the DOCUMENTED
# implement flow cannot avoid touching (this file's own remediation text: "Set the PRD's
# frontmatter `status: implementing`"). That is also the leak this gate was built for:
# not a liar, but a compliant session merging its own unverified work (4 of the first 20
# PRDs after the implement->verify split). So over the own-dir signal the disclaimer is
# REFUSED, not honoured, in exactly the states that flow produces:
#
#   • the PR MOVES that PRD's `status:` line (`status_at_base` below) — a PR driving a
#     PRD's lifecycle is that PRD's work PR by construction, whatever its body claims.
#     Includes a PRD this PR CREATES (no status at base -> a change), so a PR cannot
#     author a PRD and disclaim it in the same breath.
#   • the PRD is at `implementing` or `verified` — implementation in flight, or audited
#     and one commit from shipping. "I am not implementing it" is least credible in the
#     two states that assert someone is, and `verified` additionally keeps the frozen-at-verified check
#     (EXPLANATION_SHIP_REQUIRED) completely unescapable: the harm there is landing a PRD
#     on main frozen at `verified`, which a disclaimer does not speak to.
#
# Net: to abuse this, a session must merge a PRD's implementation while leaving that PRD
# parked at a pre-implementation status — i.e. lie in the tracking metadata too, and
# leave `main` visibly inconsistent (a `prd-drafted` PRD whose code is merged). It cannot
# be reached by following the documented flow, which is what the gate actually defends.
#
# What was considered and deliberately NOT built: refusing the escape when the PR touches
# "implementation files the PRD owns". There is no mechanical PRD->files map in this repo
# — frontmatter carries `project:`/`implements:` (requirement IDs), never paths, and 3 of
# the 4 PRDs that motivated this (0485/0486/0487, `prd-drafted`) have no plan document at
# all. Scraping paths out of plan prose would refuse on shared files (a plan naming
# `Makefile`) and still miss the files a real implementation ADDS — a heuristic that
# looks like a bound and is not. An earlier note here said a real ownership map would arrive
# with the at-site-marker direction; that direction was WITHDRAWN the same day (see
# knowledge/decisions/2026-08-14-one-register-shape-the-marker-inversion-is-withdrawn.md), so
# `implements:` stays an id list and no path-level ownership map is coming from it. The
# disclaimer's bound therefore stays exactly as built rather than waiting on a successor.
DISCLAIMER_RE = re.compile(r"^[ \t]*NOT-IMPLEMENTING-PRD=(\d{4}):[ \t]*(\S.*?)[ \t]*$", re.MULTILINE)

# Statuses in which the disclaimer is refused over a PRD's OWN directory — see above.
DISCLAIMER_REFUSED_STATUSES = {"implementing", "verified"}

# Paths that are documentation/tracking rather than implementation. A PR touching ONLY
# these is not an implementation PR, so it is not gated — that keeps a typo fix in a
# shipped PRD, and the prd:create / prd:plan flows, mergeable.
#
# The two design-phase paths are the Lock-tier mockup `prd:design` Step 0b
# requires for every UI-bearing PRD (design-fidelity-loop.md §1.5a): a real fixture
# page and its screenshot spec. Both are non-`knowledge/` files that a `status:
# designed` (not yet `verified`) PRD's design PR necessarily carries, so without this
# exemption every such PR is unmergeable — there is no compliant path.
# Neither can hide real implementation: `frontend/apps/web/src/pages/dev/` is
# `import.meta.env.DEV`-gated and `React.lazy`'d out of the production bundle, and
# `frontend/apps/web/tests/fidelity/` is screenshot specs, test-only by construction.
# The last two entries are what a page-spec MECHANICALLY REQUIRES, added after this
# exact failure recurred a THIRD time (PRD 0396's design PR, #4537). The pattern is the
# one this file's own comments already name twice — the exemption list keeps being
# derived from what the design command *produces* rather than everything producing it
# entails:
#
#   • `scripts/page_specs_allowlist.json` — authoring a spec for a page that had none
#     REMOVES that page's allowlist entry. `validate_page_specs.py` fails otherwise
#     ("55 on the allowlist (target: 0)" is a counter the design command is meant to
#     drive down), so the edit is not optional and cannot be deferred.
#   • `frontend/libs/ui/catalog/` — `make generate-page-specs`, which `prd:design`
#     Phase 0.5 mandates ("run `make generate-page-specs` to populate the conformance
#     block"), regenerates the catalog usage index as a side effect. Skipping the
#     generate leaves the spec without its `composes:generated` block, which
#     `validate_page_specs.py` also rejects.
#
# Neither can hide real implementation: the allowlist is a JSON array of file paths, and
# the catalog is generated output of the same command that writes the spec — a human
# editing either by hand to smuggle code in would be caught by the generator's own
# no-diff-on-rerun check.
#
# FOURTH recurrence, on a new axis — the APP, not the artifact type. The two
# fidelity prefixes above were written as `frontend/apps/web/...` because every
# UI-bearing PRD to date had shipped its Lock-tier mockup in the web app. PRD 0422
# (`/system/build`) is the first ADMIN-app PRD to go through Step 0b, and its design
# PR was blocked for exactly the reason this file's comments already record three
# times: the exemption list keeps being derived from what the design command
# *produces* rather than from everything producing it entails. The admin app's
# fixture directory and fidelity suite have the identical properties that justify
# the web exemptions — `src/pages/dev/` is `import.meta.env.DEV`-gated and
# `React.lazy`'d out of the production bundle (enforced by that directory's
# tree-shaking contract), and `tests/fidelity/` is screenshot specs, test-only by
# construction — so neither can hide real implementation either.
#
# The admin app's dev ROUTES moved to `frontend/apps/admin/src/pages/dev/devRoutes.tsx`
# in the same change, mirroring the web app, so registering a fixture no longer edits
# the (correctly gated) `App.tsx`.
DOC_PREFIXES = (
    "knowledge/",
    "docs/",
    ".claude/commands/",
    ".fleet/commands/",
    "scripts/page_specs_allowlist.json",
    "frontend/libs/ui/catalog/",
)

# Page-specs (`<Page>.spec.md`) are the THIRD design-phase artifact, and they are exempt
# by SUFFIX because — unlike the two paths above — they have no common prefix: a page-spec
# lives next to the `<Page>.tsx` it describes, so it can sit anywhere under
# `frontend/apps/*/src/`.
#
# `prd:design` Phase 0.5 makes authoring/refreshing them MANDATORY ("turn each
# surface that journey touches into a concrete `<Page>.spec.md` … only THEN answer
# data-model / layer / architecture questions"), so a design PR that follows the command
# correctly necessarily carries one. Without this, that PR is unmergeable at `status:
# designed` — the exact unmergeable-PR shape the two prefixes above already fix, and the same
# root cause `pages/dev/devRoutes.tsx`'s header records: the exemption list was derived
# from what the design command *produces* rather than everything it produces. PRD 0389's
# design PR (#4431, `enduser/AppPage.spec.md`) is where the third artifact surfaced.
#
# Cannot hide implementation: `.spec.md` is markdown, and all 70 in the tree are page-specs.
DOC_SUFFIXES = (".spec.md",)

# ── Ship-time checks a project registers for its own PRDs ────────────────────────────
# PRD number -> (predicate, refusal template). A predicate returns None when that PRD may
# ship, else the named reason; the template formats it as `{reason}`. Judged for the PRDs
# this gate is already gating, when the PRD's head status is `shipped` — the PR that carries
# the flip — as an INDEPENDENT violation with no body escape.
#
# The tier as it ships to a customer registers NONE. A check one project wrote for one of
# its own PRDs is keyed by that project's PRD number, and a customer PRD that happens to
# carry the same number must never be judged by it — so a project's own check is registered
# inside a home-only block, which the customer render drops whole.
SHIP_TIME_CHECKS: dict[str, tuple[Callable[[], str | None], str]] = {}


def _is_doc(path: str) -> bool:
    return path.startswith(DOC_PREFIXES) or path.endswith(DOC_SUFFIXES)


def sh(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=False).stdout.strip()


def changed_files(base_sha: str) -> list[str]:
    """Paths this PR itself changes — never paths `main` moved underneath it.

    `actions/checkout` checks out the PR's **merge ref** for a `pull_request`
    event, and GitHub keeps that ref rebuilt against the LIVE tip of the base
    branch. `PR_BASE_SHA` (`github.event.pull_request.base.sha`), by contrast, is
    frozen at PR-creation time. Diffing the frozen base against the live merge
    commit therefore attributes every commit that landed on `main` in between to
    THIS PR — `merge-base(base_sha, merge_ref) == base_sha`, so even the
    three-dot form does not save us.

    On a repo taking ~158 merges/day that is not an edge case, it is the norm:
    a 4-file CI-only PR was blocked as "PRD NNNN ... this PR changes 7
    implementation file(s)" because someone else's work on that PRD merged during the
    ~10 minutes the PR was open. The gate fires at random on whoever is unlucky,
    which is exactly the flaky-gate shape a required check must never have.

    Fix: when HEAD is a merge commit, diff against its FIRST parent — the base-branch
    side of the merge — which by construction contains everything `main` has except
    this PR's own work. Falls back to the frozen base for a non-merge HEAD (a head-sha
    checkout, or a push event), where the three-dot form is already correct.
    """
    out = sh("git", "diff", "--name-only", f"{diff_base(base_sha)}...HEAD")
    return [ln for ln in out.splitlines() if ln]


def diff_base(base_sha: str) -> str:
    """The ref this PR's own changes are measured against — see `changed_files`.

    Split out so the disclaimer's "did this PR move the PRD's `status:` line?" check
    (`status_at_base`) reads the PRD from the SAME baseline the file list comes from. A
    disclaimer judged against the frozen base while the diff is judged against the merge
    parent would flag a status flip that somebody else's merged PR made — the flaky-gate
    shape `changed_files` exists to remove.
    """
    is_merge_head = bool(sh("git", "rev-parse", "--verify", "--quiet", "HEAD^2"))
    return "HEAD^1" if is_merge_head else base_sha


def status_of(num: str) -> tuple[str | None, str | None]:
    """(status, path) for PRD `num` as it exists on the PR head, or (None, None)."""
    for prd_md in sorted(Path("knowledge/prds").glob(f"{num}-*/prd.md")):
        m = STATUS_RE.search(prd_md.read_text(encoding="utf-8", errors="replace")[:4000])
        return (m.group(1) if m else None), str(prd_md)
    return None, None


def status_at_base(base: str, path: str) -> str | None:
    """PRD `path`'s status as of `base`, or None if it did not exist / has no status."""
    m = STATUS_RE.search(sh("git", "show", f"{base}:{path}")[:4000])
    return m.group(1) if m else None


def disclaimed_prds(body: str) -> dict[str, str]:
    """PRD number -> declared reason, for every disclaimer line in the PR body."""
    return {num: reason.strip() for num, reason in DISCLAIMER_RE.findall(body or "")}


def disclaimer_refusal(num: str, status: str, path: str, is_own: bool, base: str) -> str | None:
    """None if `num`'s disclaimer is honoured; else the sentence saying why it is not.

    The bounds and the reasoning behind each are recorded at `DISCLAIMER_RE`.
    """
    if not is_own:
        # Branch/title text only. Removes no protection: an author who wanted to hide an
        # implementation would omit the number entirely and never trip the gate.
        return None
    if status in DISCLAIMER_REFUSED_STATUSES:
        return (
            f"this PR touches {num}'s own directory while it is at `status: {status}` — "
            "a PRD whose implementation is in flight (or is audited and awaiting its ship "
            "commit) may not be disclaimed. Land the unrelated change separately."
        )
    before = status_at_base(base, path)
    if before != status:
        moved = f"`{before}` -> `{status}`" if before else f"created at `{status}`"
        return (
            f"this PR moves {num}'s own `status:` line ({moved}) — a PR driving a PRD's "
            "lifecycle is that PRD's work PR, whatever the body claims."
        )
    return None


def prd_commits(base: str, path: str) -> list[str]:
    """This PR's own commits (oldest first) that touch `path` — never a commit `main`
    already had, for the same reason `changed_files` uses `diff_base` rather than the
    frozen `PR_BASE_SHA` (see there): `base` here must already BE `diff_base(base_sha)`.
    """
    out = sh("git", "log", "--format=%H", "--reverse", f"{base}..HEAD", "--", path)
    return [ln for ln in out.splitlines() if ln]


# An ADDED (`+`) line only — never a `-` removal or a `+++`/`---` diff file header —
# naming a status_history `state:` of `verified` or `shipped`. Deliberately `state:`,
# never `status:`, so the top-level frontmatter scalar (`status: shipped`) can never
# false-match: only a status_history ENTRY counts.
STATE_ADD_RE = re.compile(r"^\+(?!\+\+).*\bstate:\s*(verified|shipped)\b")


def status_history_states_added(sha: str, path: str) -> set[str]:
    """Which of `verified`/`shipped` commit `sha`'s own diff newly adds to `path`."""
    patch = sh("git", "show", "--format=", "-p", sha, "--", path)
    return {m.group(1) for ln in patch.splitlines() if (m := STATE_ADD_RE.match(ln))}


def same_commit_ship(base: str, own_dir: set[str]) -> list[tuple[str, str, str]]:
    """PRDs (num, path, commit sha) whose `verified` and `shipped` status_history
    entries were both introduced by the SAME commit — see `EXPLANATION_SAME_COMMIT`.

    Scoped to `own_dir` PRDs reaching `shipped` for the FIRST time in this PR (the
    definitive "this PR IS that PRD's ship PR" signal `SHIP_REQUIRED_OK` already uses) —
    a later, unrelated PR that merely touches an already-shipped PRD's directory again
    is not re-checked.
    """
    out: list[tuple[str, str, str]] = []
    for num in sorted(own_dir):
        status, path = status_of(num)
        if status != "shipped" or not path:
            continue
        if status_at_base(base, path) == "shipped":
            continue  # already shipped before this PR — not this PR's transition
        verified_sha = shipped_sha = None
        for sha in prd_commits(base, path):
            states = status_history_states_added(sha, path)
            if "verified" in states and verified_sha is None:
                verified_sha = sha
            if "shipped" in states and shipped_sha is None:
                shipped_sha = sha
        if verified_sha and shipped_sha and verified_sha == shipped_sha:
            out.append((num, path, verified_sha))
    return out


def own_dir_prds(files: list[str]) -> set[str]:
    """PRDs whose OWN directory this PR touches — see `SHIP_REQUIRED_OK`."""
    found: set[str] = set()
    for f in files:
        m = PRD_DIR_RE.match(f)
        if m:
            found.add(m.group(1))
    return found


def referenced_prds(files: list[str], branch: str, title: str) -> set[str]:
    """Which PRDs this PR claims to implement.

    Deliberately a UNION of three signals rather than the branch name alone: the
    `prd-NNNN-*` branch convention is known to be unreliable (it is exactly how the
    verified→shipped flip has been missed before), so a PR that edits a PRD's own
    directory, or names it in the title, counts too. Over-detection is safe here — the
    doc-only escape below keeps it from blocking non-implementation work.
    """
    found: set[str] = own_dir_prds(files)
    # Scan branch AND title unconditionally. An earlier version only scanned text
    # containing "prd" or "/", which silently skipped the real-world title
    # `feat(0334, <issue key>): ...` — the one place that PR carried its PRD number, since
    # its branch (`agent/prd-eng-2532`) carries the tracker key instead. That miss is the
    # whole failure this gate exists to prevent, so scan everything and let the
    # directory-existence filter below reject noise.
    for text in (branch, title):
        if text:
            found.update(PRD_NUM_RE.findall(text))
    # Only keep numbers that actually name a PRD directory. This is what makes the broad
    # scan safe: PRD numbers are zero-padded and dense in the 0000-0999 range, so an
    # incidental number in a title ("bump timeout to 3000") names no directory and drops.
    return {n for n in found if any(Path("knowledge/prds").glob(f"{n}-*/prd.md"))}


# ── Live PR title ───────────────────────────────────────────────────────────
# The title this run judged came from LIVE (an edit made after the run started
# IS visible on a rerun) or FROZEN (it is not). Same shape, same reasoning as
# the live-title fix in validate_pr_doc_claim.py, which itself mirrors the
# live PR-body read: `on: pull_request` has no `edited` type, so a PRD
# reference ADDED to the title after dispatch is invisible to `gh run rerun` —
# the frozen payload alone under-detects.
PAYLOAD_SOURCE_LIVE = "live"
PAYLOAD_SOURCE_FROZEN = "frozen"

DEFAULT_API_URL = "https://api.github.com"
FETCH_TIMEOUT_SECONDS = 10


def fetch_live_pr_title(token: str, repository: str, pr_number: str, api_url: str = DEFAULT_API_URL) -> str:
    """GET /repos/{repository}/pulls/{pr_number} and return its CURRENT title.

    Raises on any missing/invalid input or HTTP failure — every raise means
    "scan the frozen payload's title" to the one caller below. Same auth/env
    convention as `.github/scripts/fetch_pr_body.py` and
    validate_pr_doc_claim.py's fetch; duplicated rather than imported
    because each of these scripts is executed standalone from a TRUSTED BASE SHA
    (`git show <base>:… | python3 -`) and an import from a sibling PR-checkout
    path would not carry that property.
    """
    if not token:
        raise ValueError("GITHUB_TOKEN is not set (refusing to call the API unauthenticated)")
    if not repository:
        raise ValueError("GITHUB_REPOSITORY is not set")
    number = str(pr_number).strip()
    if not number.isdigit() or int(number) <= 0:
        raise ValueError(f"PR_NUMBER is not a positive integer: {pr_number!r}")
    url = f"{api_url.rstrip('/')}/repos/{repository}/pulls/{int(number)}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "prd-verified-gate",
        },
    )
    with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
        payload = json.load(response)
    title = payload.get("title")
    # A PR always has a non-empty title; an empty one would silently DROP a
    # reference (under-detection — the harm here), so treat it as a failed fetch
    # and keep the frozen value instead. Fails toward the stricter input.
    if not isinstance(title, str) or not title.strip():
        raise ValueError("the API response carries no non-empty `title`")
    return title


def resolve_pr_title(frozen_title: str, pr_number: str) -> tuple[str, str]:
    """(title text to scan, source) — the FROZEN and LIVE titles UNIONed on a
    real `pull_request` run, else the frozen one.

    The UNION, not live-replaces-frozen: this gate's failure direction is
    under-detection, and its own design (`referenced_prds`) treats
    over-detection as safe — the body disclaimer sorts false positives out and
    is honoured for exactly the text-only-reference case (and is itself
    live-read since the PR-body fix). Union can therefore never detect LESS than the
    pre-fix scan, and a reference REMOVED from the title post-dispatch stays
    clearable through the auditable disclaimer escape instead of silently
    clearing on a retitle. (The title guard replaces live for frozen because
    ITS harm is the opposite direction — a stale claim blocking a PR.)

    The event-name condition mirrors resolve_pr_metadata and the
    PR-body live read: a merge_group / push / schedule run has no PR
    to re-read.
    """
    if os.environ.get("GITHUB_EVENT_NAME", "").strip() != "pull_request" or not pr_number:
        return frozen_title, PAYLOAD_SOURCE_FROZEN
    try:
        live = fetch_live_pr_title(
            os.environ.get("GITHUB_TOKEN", ""),
            os.environ.get("GITHUB_REPOSITORY", ""),
            pr_number,
            os.environ.get("GITHUB_API_URL", "").strip() or DEFAULT_API_URL,
        )
    except Exception as exc:  # any failure means "scan the frozen payload's title"
        # urllib errors carry the URL, never the request headers — the token
        # cannot leak through this message.
        print(
            "WARNING: live PR-title fetch failed — scanning the FROZEN "
            "event payload's title only; a PRD reference ADDED to the title after "
            "this run started is NOT visible to it, and `gh run rerun` replays the "
            "same frozen payload. Re-run once the fetch succeeds (or push a commit, "
            f"which captures a fresh payload). Detail: {type(exc).__name__}: {str(exc)[:300]}",
            file=sys.stderr,
        )
        return frozen_title, PAYLOAD_SOURCE_FROZEN
    print(
        "PRD-reference source: PR title read LIVE from the API; "
        "the frozen payload's title is scanned too (over-detection is safe here)"
    )
    return f"{frozen_title}\n{live}" if frozen_title else live, PAYLOAD_SOURCE_LIVE


def main() -> int:
    # evaluate on merge_group too so a queue SHA re-checks the stamp.
    # Without PR identity env (number/title/body/head_ref) the gate still no-ops
    # safely further down; the workflow populates what it can.
    if os.environ.get("GITHUB_EVENT_NAME") not in ("pull_request", "merge_group"):
        print("not a pull_request/merge_group event — PRD verification gate skipped")
        return 0

    base_sha = os.environ.get("PR_BASE_SHA") or ""
    branch = os.environ.get("PR_HEAD_REF") or ""
    title = os.environ.get("PR_TITLE") or ""
    body = os.environ.get("PR_BODY") or ""
    # re-read the title LIVE (unioned with the frozen one) so a PRD
    # reference added to the title after this run started is judged on a rerun.
    title, title_source = resolve_pr_title(title, os.environ.get("PR_NUMBER", ""))
    if not base_sha:
        print("PR_BASE_SHA not set — cannot compute the diff; refusing to pass blindly", file=sys.stderr)
        return 1

    files = changed_files(base_sha)
    if not files:
        print("no changed files — nothing to gate")
        return 0

    impl_files = [f for f in files if not _is_doc(f)]
    prds = referenced_prds(files, branch, title)
    if not prds:
        # Name the payload the title came from: this no-op is the
        # under-detection surface, and the retitle-plus-rerun remedy is only
        # followable when the reader knows which title was judged.
        print(f"no PRD referenced by this PR — gate not applicable (title source: {title_source})")
        return 0
    if not impl_files:
        print(f"PRD(s) {', '.join(sorted(prds))} referenced, but this PR changes only docs/tracking — not gated")
        return 0

    own_dir = own_dir_prds(files)
    disclaimed = disclaimed_prds(body)
    base = diff_base(base_sha)
    used: set[str] = set()
    honoured: set[str] = set()
    blocked: list[tuple[str, str, str, bool]] = []
    # A registered ship-time refusal (`SHIP_TIME_CHECKS`) — an INDEPENDENT violation,
    # like `same_commit` below, so it blocks even when `blocked` stays empty.
    ship_time_blockers: list[str] = []
    for num in sorted(prds):
        status, path = status_of(num)
        if status is None:
            continue  # no parseable status; validate_tracking_metadata.py owns that error
        # The ship-time check MUST sit before the `status in required` continue below:
        # `shipped` is the one status that continue skips on — and the one state the
        # check exists to gate (design D14: the flip itself is what is refused).
        ship_time_check = SHIP_TIME_CHECKS.get(num)
        if ship_time_check is not None and status == "shipped":
            reason = ship_time_check[0]()
            if reason is not None:
                ship_time_blockers.append(reason)
                print(ship_time_check[1].format(reason=reason), file=sys.stderr)
        is_own = num in own_dir
        required = SHIP_REQUIRED_OK if is_own else VERIFIED_OK
        if status in required:
            continue
        if num in disclaimed:
            used.add(num)
            refusal = disclaimer_refusal(num, status, path or "", is_own, base)
            if refusal is None:
                # Printed loudly and always: an honoured escape must be visible in the CI
                # log of the run that merged, not inferrable only from the PR body.
                honoured.add(num)
                print(f"ALLOWED (declared non-implementation): PRD {num} at `status: {status}`")
                print(f"    Reason: {disclaimed[num]}")
                continue
            print(f"REFUSED disclaimer for PRD {num} — {refusal}", file=sys.stderr)
        blocked.append((num, status, path or "", is_own))

    # A disclaimer for a PRD that never blocked is noise, not an error: statuses move
    # under an open PR (PR #6844 disclaimed six, of which two reached `shipped` on main
    # while it was open), and failing on the redundant ones would make the gate flaky.
    for num in sorted(set(disclaimed) - used):
        print(f"note: disclaimer for PRD {num} was not needed — it does not gate this PR")

    # PRD 0514: `verified` satisfies SHIP_REQUIRED_OK for a `shipped` PRD (it's
    # not in `blocked` above), yet a single commit stamping BOTH is exactly the shape a
    # self-certifying implement session produces — no independent `prd:verify`
    # session had to run for the textual gate to pass. Checked unconditionally, not only
    # when `blocked` is empty: it is an independent violation, not an alternate reading of
    # one already caught above.
    same_commit = same_commit_ship(base, own_dir)
    for num, path, sha in same_commit:
        print(EXPLANATION_SAME_COMMIT.format(num=num, path=path, sha=sha[:10]), file=sys.stderr)

    if not blocked and not same_commit and not ship_time_blockers:
        # A disclaimed PRD is NOT reported as verified — the escape says the gate does not
        # apply to it, never that anybody audited it.
        cleared = sorted(prds - honoured)
        if cleared:
            print(f"PRD verification gate OK — {', '.join(cleared)} verified on this branch")
        if honoured:
            print(f"PRD verification gate OK — {', '.join(sorted(honoured))} explicitly disclaimed (not verified)")
        return 0
    if not blocked:
        return 1

    for num, status, path, is_own in blocked:
        if is_own and status == "verified":
            print(EXPLANATION_SHIP_REQUIRED.format(num=num, path=path, files=len(impl_files)), file=sys.stderr)
        else:
            print(EXPLANATION.format(num=num, status=status, path=path, files=len(impl_files)), file=sys.stderr)
    return 1


EXPLANATION = """
================================================================================
BLOCKED: PRD {num} may not merge — it has not been verified.

  {path}
  status: {status}          (this PR changes {files} implementation file(s))

WHY: the party that writes the code does not certify it. `prd:verify` runs in
a FRESH session, refutes its own PASSes, and only then stamps `verified`. Merging
before that has shipped unaudited code AND frozen every downstream PRD that depends on
this one — a dependent is only released by `status: shipped`, which requires
`verified` first.

WHAT TO DO NOW — you are the implementer, so do NOT flip the status yourself
(validate_tracking_metadata.py rejects a `verified` stamp that is not `by: verify`,
so hand-editing it will fail CI too):

  1. Make sure the PR is open and CI is green. Leave it OPEN. Do not merge.
  2. Set the PRD's frontmatter `status: implementing` if it is not already, and move
     the tracker issue to "In Review". That is the handoff signal — a PRD sitting in
     the review state is what dispatches the verifier.
  3. STOP. Your job ends here. Write the done-sentinel and exit; do not wait for the
     verifier and do not merge.

The verifier then runs `prd:verify {num}` in its own session and either:
  - ALL PASS  -> stamps `status: verified` on this branch, this gate goes green, and
                 it ships the PR (`push ship`).
  - ANY FAIL  -> leaves the PR open and the status at `implementing`, and routes the
                 remediation: `prd:implement {num}` for a MISSING criterion,
                 `bug:fix` for a BROKEN one. Fix it, then verification re-runs.

If this PR genuinely does not implement PRD {num} — the number matched by accident, or
it edits that PRD's docs/frontmatter as part of unrelated work — add ONE LINE PER PRD to
the PR BODY (not a comment), each naming ONE number and why:

  NOT-IMPLEMENTING-PRD={num}: <why this PR is not that PRD's implementation>

It clears exactly the number it names: no ranges, no lists, no blanket "docs only", and
prose does not count. It is REFUSED where this PR is plausibly {num}'s own work — if it
moves {num}'s `status:` line, or if {num} is at `implementing`/`verified` and this PR
touches its directory — so a compliant implementation PR can never disclaim its way out.
The honoured line is echoed into this job's log.

Delivery: this step reads the PR body LIVE via the API, but a PR-body edit
does not re-trigger CI. After adding the line, re-run the failed jobs:
`gh run rerun <run-id> --failed` (failed jobs AND their dependents re-run; passed jobs
keep their results).
================================================================================
"""

EXPLANATION_SHIP_REQUIRED = """
================================================================================
BLOCKED: PRD {num} may not merge — verified, but not yet shipped.

  {path}
  status: verified          (this PR IS {num}'s own work — its directory is touched)

WHY: `status: shipped` and the PR merge are ONE atomic event (Rule F,
autonomous-drive.md — "the merge IS the ship"). `prd:verify` stamps
`verified`; only `push ship` may append the `shipped` commit that actually
authorizes a merge. Merging now (e.g. `gh pr merge --auto` called directly, skipping
`push ship`) would freeze this PRD at `verified` forever, with nothing to
reconcile it afterward — a corruption that has happened, and had to be repaired by hand.

WHAT TO DO NOW: run `push ship <sha> {num}` (or, if verification already
passed and this is a ship-time retry, the ship-only-retry path in
`prd:verify {num}` Step 0) on this branch. It stamps `status: shipped` as the
final commit — that is what this check requires before GitHub may merge.

There is deliberately NO body escape from this one. `NOT-IMPLEMENTING-PRD=` is refused
for a PRD at `verified` whose directory this PR touches: the harm here is not unaudited
code but landing {num} on `main` frozen at `verified` with nothing to reconcile it, and
disclaiming authorship of the code does not make that safe. If this PR really is not
{num}'s ship PR, leave {num}'s directory out of it.
================================================================================
"""

EXPLANATION_SAME_COMMIT = """
================================================================================
BLOCKED: PRD {num} may not merge — `verified` and `shipped` landed in the SAME commit.

  {path}
  commit {sha} adds BOTH the `verified` and `shipped` status_history entries

WHY: the documented flow always produces TWO commits. `prd:verify` Step 5 commits
`verified` alone ("do not push it yourself"); only `push ship`'s own, LATER commit
may append `shipped`. A single commit stamping both at once is exactly the shape of a
session self-certifying its own work with no independent `prd:verify` session ever
having run — the textual check that only `by: verify` may stamp `verified` cannot tell a
real audit from a session that just typed the compliant string, but it CAN tell that the
two-commit structure the real command always produces is missing (a PR has merged with
both stamped by one commit, "status shipped — atomic ship stamp").

WHAT TO DO NOW: if this PRD's acceptance criteria genuinely were audited, re-run
`prd:verify {num}` for real — it commits `verified` on its own, separate commit,
then ships in a second. Never hand-craft a `status_history` block that collapses the two;
CI cannot distinguish that from self-certification, so it refuses both alike.
================================================================================
"""


if __name__ == "__main__":
    sys.exit(main())
