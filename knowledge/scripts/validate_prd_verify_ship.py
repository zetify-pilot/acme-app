#!/usr/bin/env python3
"""Ship-gate for `prd:verify`: may this run bless the carrier PR as the PRD's ship?

. `prd:verify 0564` concluded "verified & merged" and let its Linear
issue reach `Done` on a merge that had announced, machine-readably, that it was NOT that
PRD's implementation: PR #9221's body carries `NOT-IMPLEMENTING-PRD=0564:` — the exact
line `knowledge/scripts/validate_prd_verified_before_merge.py` parses and honours on the merge
side — while the PRD's frontmatter on `main` still read `status: planned`. The verify
session's own comment stated both facts ("PRD stays status: planned", quoting the
disclaimer) and still returned success; a correct `Blocked · action` park written 89
seconds earlier was overwritten. Prose-level caution in the command demonstrably does not
hold against that shape, so the terminal is decided HERE, by exit code, not by the
session's judgement.

What this gate checks, per the issue's direction fork (options 1–3, which are three faces
of one question — "is the merge being certified actually that PRD's ship?"):

  1. FRONTMATTER. The PRD's `status:` at the merge commit must read `shipped`. A PRD at
     `planned` has not shipped; the atomic-ship rule says `status: shipped` rides the PR
     merge, so a merge that left the frontmatter behind is not a ship.
  2. THE STATUS LINE MUST HAVE MOVED. `status:` must have become `shipped` AT this merge
     — already-`shipped` at the merge's parent means this merge carried no ship (an
     unrelated trailing PR must not be blessable as one).
  3. THE DISCLAIMER. If the PR body declares `NOT-IMPLEMENTING-PRD=<this num>:`, the
     merge gate honoured that as a non-implementation — the merge announced the opposite
     of a ship, and the verify side must not bless what the merge side explicitly
     disclaimed. A disclaimer contradicting a genuine status move never occurs
     legitimately (the merge gate refuses a disclaimer over a status flip), so the
     combination fails closed.

Passing candidates: any OPEN carrier (the normal flow — Step 5's flip plus
`push ship` own the ship, and the merge-time gates police the merge), or any
MERGED candidate that proves a genuine atomic ship. Like the daemon's `_shipped_pr_guard`
an issue may carry several merged PRs (a two-PR split: PR 1 apparatus, PR 2
record+ship), so the gate passes if ANY candidate proves the ship — and refuses when none
does. Everything unreadable fails closed: a missing merge commit, an unparseable
frontmatter, an absent `prd.md` at the merge commit — and, since, a parent blob
read that FAILS. `blob_at` returns None only for a path that is genuinely ABSENT at the
ref (the legitimate new-PRD ship shape at the parent) and raises `BlobReadError` for a
read that failed; the gate refuses the latter, never reading a failed read as "absent".

 (wontfix of a PRD-declared terminal PR): a two-PR split does NOT need a
`split:` frontmatter key or a `## Delivery split` section naming which PR ships. The ship
is the merge that moved `status:` to `shipped` with no disclaimer — this gate already
identifies every non-ship by checks 1–3, disclaimer optional on the refusal path
(`test_status_line_not_moved_is_refused_even_without_a_disclaimer`). Design prose (D12 /
 and kin) stays human-facing sequencing. Decision record:
`knowledge/decisions/2026-08-30-two-pr-split-ship-is-the-status-flip-not-a-declared-terminal-pr.md`.

PRD 0582's ship-time check (design D14's closing rule — "**0582 does not flip to
`shipped` while `oracle_diff.json` reads `unproven`**"; AC-4's "*(Leg A + a ship-time
check.)*" element, which verify refutation found existing nowhere as code): on
the OPEN-candidate path — the one whose message says the run may flip the status and ship
— a `0582` verify run re-runs the merge gate's oracle-capture predicate
(`_vpv.pg13_oracle_capture_blocker_working_tree`, judging this checkout's working tree)
BEFORE blessing. A non-None blocker refuses with the same fixed terminal as a merged
non-ship. Merged-candidate grading is NOT changed — the merge gate
(knowledge/scripts/validate_prd_verified_before_merge.py) polices the merge itself. There is
deliberately NO disclaimer-shaped escape on either side: D14's whole point is that
`unproven` must never read as passable under pressure.

On refusal the verify run's terminal is fixed, not negotiable: no `verified & merged`
conclusion, no success sentinel, no Done — the issue stays (or lands) at `Blocked ·
action` per design B10, and the done-sentinel carries `needs-action` with this gate's
output quoted verbatim. The refusal text spells that out so the command can quote it and
the prose and the state write cannot disagree again.

Imported, not run: `prd:verify` executes this before any success terminal
(`python3 knowledge/scripts/validate_prd_verify_ship.py <NNNN> <KEY> --pr <n>`). Stdlib-only, like
the other validate_* scripts.

Exit 0 = the run may bless. Exit 1 = refused, with the terminal contract printed. Exit 2
= bad invocation.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent

USAGE = "validate_prd_verify_ship.py <prd-num> <issue-key> [--pr <number>] [--repo <owner/name>]"

PRD_NUM_RE = re.compile(r"^\d{4}$")

# One source of truth for the disclaimer shape and the frontmatter `status:` parse: the
# merge gate's own constants, loaded by path (scripts/ is not a package). If the merge
# side ever tightens the disclaimer grammar, this side tightens with it — the two must
# never be able to disagree about what "not implementing" means.
_spec = importlib.util.spec_from_file_location(
    "validate_prd_verified_before_merge", HERE / "validate_prd_verified_before_merge.py"
)
assert _spec and _spec.loader
_vpv: Any = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vpv)
DISCLAIMER_RE = _vpv.DISCLAIMER_RE
STATUS_RE = _vpv.STATUS_RE


@dataclass
class Verdict:
    code: int
    lines: list[str] = field(default_factory=list)

    @property
    def message(self) -> str:
        return "\n".join(self.lines)


class BlobReadError(Exception):
    """A `blob_at` read FAILED for a reason other than the path being absent — a
    transient git/object-store failure, an unreadable ref.: absent and
    unreadable are different answers, and only the first may ever read as "the PRD
    did not exist at the parent"; the gate refuses the second (fail closed)."""


def _disclaimed_for(prd_num: str, body: str) -> str | None:
    """The disclaimer's declared reason when the body disclaims THIS PRD, else None."""
    found: list[tuple[str, str]] = DISCLAIMER_RE.findall(body or "")
    for num, reason in found:
        if num == prd_num:
            return reason.strip()
    return None


def _grade_merged_candidate(
    cand: dict[str, Any],
    prd_num: str,
    issue_key: str,
    *,
    list_paths_at: Callable[[str], list[str]],
    blob_at: Callable[[str, str], str | None],
) -> Verdict:
    """0 iff this single merged PR proves a genuine atomic ship of PRD `prd_num`.

    `blob_at` is the absent-vs-unreadable seam: None means the path is
    genuinely ABSENT at the ref; a raised exception (the plumbing's own signal is
    `BlobReadError`, but any read failure qualifies) means the read FAILED — and a
    failed read is a refusal here, never an "absent at parent" blessing."""
    sha = cand.get("merge_sha")
    number = cand.get("number", "?")
    head = f"PR #{number}"
    if not sha:
        return Verdict(1, [f"{head} is MERGED but its merge commit is unreadable — fail closed."])
    parent = cand.get("parent_sha")
    if not parent:
        return Verdict(
            1,
            [
                f"{head} is MERGED but its parent commit is unreadable — "
                "cannot prove what the merge changed; fail closed."
            ],
        )

    prd_paths = [p for p in list_paths_at(sha) if re.match(rf"^knowledge/prds/{prd_num}-[^/]+/prd\.md$", p)]
    if not prd_paths:
        return Verdict(
            1,
            [
                f"{head} merged at {sha[:12]} but PRD {prd_num}'s prd.md does not exist there — "
                "a ship must carry the PRD's own frontmatter; fail closed."
            ],
        )
    path = prd_paths[0]

    def status_at(ref: str) -> str | None:
        blob = blob_at(ref, path)
        if blob is None:
            return None
        m = STATUS_RE.search(blob[:4000])
        return m.group(1) if m else None

    try:
        status = status_at(sha)
    except Exception as e:  # any failed read of the merge-side blob fails closed
        return Verdict(
            1,
            [f"{head} merged at {sha[:12]} but {path} could not be read at the merge commit ({e}) — fail closed."],
        )
    if status is None:
        return Verdict(
            1,
            [
                f"{head} merged at {sha[:12]} but {path}'s frontmatter carries no parseable "
                "`status:` line — fail closed."
            ],
        )
    try:
        parent_status = status_at(parent)
    except Exception as e:  # the failed parent read that used to bless as `absent`
        return Verdict(
            1,
            [
                f"{head} merged at {sha[:12]} but PRD {prd_num}'s frontmatter at the merge's parent "
                f"could not be read ({e}) — cannot prove the status moved and was not already "
                "`shipped`; fail closed."
            ],
        )

    disclaimed_reason = _disclaimed_for(prd_num, cand.get("body") or "")
    if status == "shipped":
        if parent_status == "shipped":
            return Verdict(
                1,
                [
                    f"{head} merged at {sha[:12]} but PRD {prd_num} was ALREADY `status: shipped` "
                    "at the merge's parent — this merge carried no ship "
                    "(an unrelated trailing PR is not blessable as one).",
                ],
            )
        if disclaimed_reason is not None:
            return Verdict(
                1,
                [
                    f"{head} moved PRD {prd_num} to `status: shipped` at {sha[:12]} yet its body declares "
                    f"NOT-IMPLEMENTING-PRD={prd_num}: {disclaimed_reason}",
                    "A merge cannot both disclaim a PRD and ship it; the combination never occurs legitimately "
                    "(the merge gate refuses a disclaimer over a status move) — fail closed.",
                ],
            )
        return Verdict(
            0,
            [
                f"{head} merged at {sha[:12]}: PRD {prd_num}'s frontmatter moved "
                f"`{parent_status or 'absent'}` → `shipped` with no disclaimer — "
                "a genuine atomic ship; the run may conclude verified & merged.",
            ],
        )

    # status != shipped: the frontmatter did not ship — the incident shape.
    lines = [
        f"{head} merged at {sha[:12]} but it is NOT PRD {prd_num}'s ship:",
        f"  frontmatter at the merge commit reads `status: {status}` "
        f"(`{parent_status or 'absent'}` at its parent — "
        + ("unchanged by this merge" if parent_status == status else "this merge did not land `shipped`")
        + ").",
    ]
    if disclaimed_reason is not None:
        lines.append(
            f"  the PR body itself declares `NOT-IMPLEMENTING-PRD={prd_num}: {disclaimed_reason}` — "
            "the merge gate (knowledge/scripts/validate_prd_verified_before_merge.py) honoured that as a "
            "non-implementation, so this merge announced the opposite of a ship."
        )
    lines += [
        "",
        "WHAT THIS MEANS FOR THE VERIFY RUN (the terminal is fixed, not negotiable):",
        '  1. Do NOT conclude "verified & merged". Do NOT write a success sentinel. The issue must NOT reach Done.',
        "  2. Do NOT flip the PRD's frontmatter status — no `verified` stamp on this terminal.",
        "  3. Leave the issue parked at `Blocked · action` (design B10) — move it there only if it is not "
        "already parked; the remaining half of the PRD stays driven by that park.",
        "  4. Write the done-sentinel with status `needs-action`, quoting this gate's output verbatim as "
        "the reason and naming what remains.",
    ]
    return Verdict(1, lines)


def evaluate(
    prd_num: str,
    issue_key: str,
    candidates: list[dict[str, Any]],
    *,
    list_paths_at: Callable[[str], list[str]],
    blob_at: Callable[[str, str], str | None],
    pg13_capture_blocker: Callable[[], str | None],
) -> Verdict:
    """0 iff at least one carrier candidate proves the run may bless the merge as the ship.

    `pg13_capture_blocker` is PRD 0582's ship-time predicate (design D14): a
    zero-arg callable returning None when the oracle capture has landed, else the named
    refusal reason. It gates ONLY the OPEN-candidate path below — the decision point
    whose message says the run may flip the status and ship; merged-candidate grading is
    unchanged, because the merge gate polices the merge itself."""
    if not candidates:
        return Verdict(
            1,
            [
                f"No carrier PR resolved for {issue_key} / PRD {prd_num} — nothing proves a ship, fail closed.",
                "prd:verify Step 0.5 exists precisely to guarantee a binding surface before anything is graded; "
                "open it and re-run the gate.",
            ],
        )

    open_candidates = [c for c in candidates if str(c.get("state", "")).upper() == "OPEN"]
    if open_candidates:
        numbers = ", ".join(f"#{c.get('number', '?')}" for c in open_candidates)
        # PRD 0582's ship-time check: an OPEN carrier is normally blessed straight
        # through, but 0582's flip to `shipped` must not be blessable while the oracle
        # capture is unproven — the exact state D14 refuses to let read as shippable.
        if prd_num == _vpv.PG13_COMPOSED_PROOF_PRD:
            blocker = pg13_capture_blocker()
            if blocker is not None:
                return Verdict(
                    1,
                    [
                        f"Carrier PR {numbers} for {issue_key} is OPEN, but PRD {prd_num}'s ship-time check "
                        "refuses — the oracle capture has not landed:",
                        f"  {blocker}",
                        "",
                        "WHAT THIS MEANS FOR THE VERIFY RUN (the terminal is fixed, not negotiable):",
                        '  1. Do NOT conclude "verified & merged". Do NOT write a success sentinel. '
                        "The issue must NOT reach Done.",
                        "  2. Do NOT flip the PRD's frontmatter status — no `shipped` (and no `verified`) stamp on "
                        "this terminal; the flip is exactly what is refused.",
                        "  3. Leave the issue parked at `Blocked · action` (design B10), naming the operator oracle "
                        "re-capture (internal/scenarios/installer/testdata/metro_crab_parity/README.md) as the "
                        "remaining half.",
                        "  4. Write the done-sentinel with status `needs-action`, quoting this gate's output verbatim "
                        "as the reason.",
                    ],
                )
        return Verdict(
            0,
            [
                f"Carrier PR {numbers} for {issue_key} is OPEN — the normal flow applies: the run may flip "
                "the status and ship; the merge-time gates (knowledge/scripts/validate_prd_verified_before_merge.py) "
                "police the merge itself.",
            ],
        )

    merged = [c for c in candidates if str(c.get("state", "")).upper() == "MERGED"]
    if not merged:
        states = ", ".join(f"#{c.get('number', '?')}={c.get('state')}" for c in candidates)
        return Verdict(
            1,
            [
                f"Carrier PR(s) {states} for {issue_key} are neither OPEN nor MERGED — nothing shipped; "
                "no success terminal.",
            ],
        )

    verdicts = [
        (c, _grade_merged_candidate(c, prd_num, issue_key, list_paths_at=list_paths_at, blob_at=blob_at))
        for c in merged
    ]
    for _c, v in verdicts:
        if v.code == 0:
            return v

    # Every merged candidate failed. Refuse with the most informative block: a
    # disclaimed refusal names the machine-readable announcement and outranks a bare
    # frontmatter one; otherwise the first graded candidate's refusal stands.
    disclaimed = next((v for c, v in verdicts if "NOT-IMPLEMENTING-PRD=" in v.message), None)
    refused = disclaimed or verdicts[0][1]
    if len(verdicts) > 1:
        per_candidate = [f"  PR #{c.get('number', '?')}: {v.lines[0]}" for c, v in verdicts]
        return Verdict(
            1,
            ["All merged carrier PR(s) failed the ship check:"]
            + [f"({len(verdicts)} graded)"]
            + per_candidate
            + [""]
            + refused.lines,
        )
    return refused


# ── GitHub / git plumbing ─────────────────────────────────────────────────────────────


def sh(*args: str, cwd: Path | None = None) -> tuple[int, str]:
    r = subprocess.run(args, capture_output=True, text=True, check=False, cwd=cwd)
    return r.returncode, (r.stdout or r.stderr or "").strip()


def gh_json(args: list[str], repo: str | None) -> tuple[int, Any]:
    cmd = ["gh", *args]
    if repo:
        cmd += ["--repo", repo]
    code, out = sh(*cmd)
    if code != 0:
        return code, out
    try:
        return 0, json.loads(out)
    except json.JSONDecodeError:
        return 1, f"unparseable gh output: {out[:200]}"


def resolve_candidates(issue_key: str, pr_number: int | None, repo: str | None) -> tuple[int, Any]:
    """(code, candidates|message) — candidates sorted OPEN-first, then merged."""
    fields = ["number", "state", "body", "mergeCommit"]
    if pr_number is not None:
        code, data = gh_json(["pr", "view", str(pr_number), "--json", ",".join(fields)], repo)
        if code != 0:
            return 1, f"gh pr view {pr_number} failed: {data}"
        return 0, [data]
    candidates: list[dict[str, Any]] = []
    for state in ("open", "merged"):
        code, data = gh_json(
            ["pr", "list", "--search", issue_key, "--state", state, "--json", ",".join(fields), "--limit", "10"], repo
        )
        if code != 0:
            return 1, f"gh pr list --state {state} failed: {data}"
        candidates.extend(data)
    return 0, candidates


def make_plumbing(repo: str | None) -> tuple[Callable[[str], list[str]], Callable[[str, str], str | None]]:
    """`git ls-tree` / `git show` callables, fetching an unreadable merge commit once
    (squash merges are reachable from `main`; a non-squash merge commit may need a
    direct fetch on shallow-enough clones). `blob_at` distinguishes ABSENT (returns
    None — the path is genuinely not in the ref's tree) from FAILED (raises
    `BlobReadError` — the ref could not be read, transient or otherwise;):
    a failed `git show` must never read as "the PRD did not exist at the parent",
    which is the one absent-shape the gate legitimately blesses. Absence is decided
    with `git ls-tree` on the exact path — it exits 0 with no output for a path the
    tree does not have, and fails only when the ref itself is unreadable — so a
    present-but-unreadable blob cannot masquerade as an absent one."""

    def ensure_commit(ref: str) -> None:
        code, _ = sh("git", "cat-file", "-e", f"{ref}^{{commit}}")
        if code == 0:
            return
        sh("git", "fetch", "--no-tags", "origin", ref, *(["--repo", repo] if repo else []))

    def list_paths_at(ref: str) -> list[str]:
        ensure_commit(ref)
        code, out = sh("git", "ls-tree", "-r", "--name-only", ref, "--", "knowledge/prds/")
        return [ln for ln in out.splitlines() if ln] if code == 0 else []

    def blob_at(ref: str, path: str) -> str | None:
        """Content at `ref:path`; None iff the path is genuinely absent there;
        `BlobReadError` when the read fails for any other reason."""
        ensure_commit(ref)
        code, listing = sh("git", "ls-tree", "--name-only", ref, "--", path)
        if code != 0:
            raise BlobReadError(f"git ls-tree {ref} -- {path} failed: {listing[:300]}")
        if not listing.strip():
            return None  # the tree does not have this path — genuinely absent
        code, out = sh("git", "show", f"{ref}:{path}")
        if code != 0:
            raise BlobReadError(f"git show {ref}:{path} failed: {out[:300]}")
        return out

    return list_paths_at, blob_at


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    opts = argv[1:]
    pr_number: int | None = None
    repo: str | None = None
    if "--pr" in opts:
        i = opts.index("--pr")
        if i + 1 >= len(opts):
            print(f"usage: {USAGE}", file=sys.stderr)
            return 2
        try:
            pr_number = int(opts[i + 1])
        except ValueError:  # a usage error prints the usage line; it is not a traceback
            print(f"usage: {USAGE}", file=sys.stderr)
            print(f"--pr expects an integer (got {opts[i + 1]!r})", file=sys.stderr)
            return 2
    if "--repo" in opts:
        i = opts.index("--repo")
        if i + 1 >= len(opts):
            print(f"usage: {USAGE}", file=sys.stderr)
            return 2
        repo = opts[i + 1]
    if len(args) < 2:
        print(f"usage: {USAGE}", file=sys.stderr)
        return 2
    prd_num, issue_key = args[0], args[1]
    if not PRD_NUM_RE.match(prd_num):
        print(f"prd-num must be a zero-padded four-digit PRD number (got {prd_num!r})", file=sys.stderr)
        return 2

    code, resolved = resolve_candidates(issue_key, pr_number, repo)
    if code != 0:
        print(f"SHIP-GATE REFUSED (fail closed): {resolved}", file=sys.stderr)
        return 1
    candidates = resolved
    for c in candidates:
        sha = (c.get("mergeCommit") or {}).get("oid")
        c["merge_sha"] = sha
        c["parent_sha"] = None
        if sha:
            pc, parent = sh("git", "rev-parse", f"{sha}^")
            c["parent_sha"] = parent if pc == 0 else None

    list_paths_at, blob_at = make_plumbing(repo)
    v = evaluate(
        prd_num,
        issue_key,
        candidates,
        list_paths_at=list_paths_at,
        blob_at=blob_at,
        # PRD 0582's ship-time check (design D14): the same working-tree
        # predicate the merge gate runs, judged at this session's decision point.
        pg13_capture_blocker=_vpv.pg13_oracle_capture_blocker_working_tree,
    )
    print(v.message)
    return v.code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
