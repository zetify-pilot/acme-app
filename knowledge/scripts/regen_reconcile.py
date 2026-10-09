#!/usr/bin/env python3
"""A regen-only reconcile is not authoring.

Merge the base branch (`origin/main`) into the current work branch when — and only when —
the merge changes nothing the branch itself wrote. The verifier may run this; the verifier
may not rebase, resolve, or fix up, and this script is what keeps those two sentences from
contradicting each other.

WHY THIS EXISTS. A PR that waits in the verify queue conflicts with `main` "by
construction" on the generated ledgers nearly every knowledge PR touches
(`knowledge/requirement-status.md` above all: 14 of the ~20 distinct conflict events on
the 43 PRDs that passed the verify gate 2026-08-13→09-08 were that one file). Those files
carry a **regen merge driver** — git regenerates them from the merged tree instead of
text-merging — so a local `git merge origin/main` on a checkout with the driver registered
is clean. GitHub's mergeability check cannot run a driver, so the PR reads
`CONFLICTING`, and the verify session, forbidden to author, hands the conflict back to an
implement session: one implement dispatch, one fresh verify dispatch, one rework return
against the PRD's budget, and at the re-entry cap a `Blocked · decision` park — for a
merge whose outcome was never in doubt. Measured on the same 43 PRDs: 9 conflict-rework
briefs and 4 human parks, 3 of the 4 on generated ledgers alone.

THE INVARIANT this script proves, rather than asks anyone to trust: the branch's OWN
work — every `+`/`-` line of its diff against its merge base, over every path that is not
derived — is identical before and after the reconcile. Derived paths are the ones whose
`merge` attribute names a custom driver (the content is produced by a tool, never merged
by hand); a submodule pointer counts as resolved only when one side's commit descends
from the other's. If the invariant does not hold, or any other path conflicts, the merge is
aborted and the tree is exactly as it was: that case IS the conflict-as-work route, and
nothing here pretends otherwise.

Usage:
    python3 knowledge/scripts/regen_reconcile.py [--base origin/main] [--dry-run] [--json]

Exit codes:
    0  reconciled — a merge commit was made (or there was nothing to do). The branch's own
       work is proven unchanged; the new head is a fast-forward push away.
    1  a real conflict, or the invariant did not hold — nothing was changed. The paths are
       listed. Route it as work.
    2  could not run — dirty worktree, detached HEAD, a driver `.gitattributes` names is not
       registered in this checkout (a GENERATED file with no merge driver), or git failed.
       Nothing was changed.

Never pushes. Never force-pushes. Never touches a path that is not derived.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

#: `merge` attribute values that are git's own — a path carrying one of these is TEXT-merged
#: (or deliberately taken from one side) and is the branch's own work, never derived.
_BUILTIN_MERGE = frozenset({"", "unspecified", "unset", "set", "text", "binary", "union", "ours", "theirs"})
_GITLINK_MODE = "160000"


class ReconcileError(Exception):
    """Exit 2: the reconcile could not run at all. Nothing was changed."""


@dataclass
class Outcome:
    result: str  # "reconciled" | "nothing-to-do" | "conflict" | "invariant-broken" | "error"
    base: str = ""
    head_before: str = ""
    head_after: str = ""
    derived_resolved: list[str] = field(default_factory=list)
    gitlinks_resolved: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    detail: str = ""

    @property
    def exit_code(self) -> int:
        if self.result in ("reconciled", "nothing-to-do"):
            return 0
        if self.result in ("conflict", "invariant-broken"):
            return 1
        return 2


class Git:
    def __init__(self, root: Path) -> None:
        self.root = root

    def run(self, *args: str, check: bool = True, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        cp = subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True,
            text=True,
            input=input_text,
            check=False,
        )
        if check and cp.returncode != 0:
            raise ReconcileError(
                f"git {' '.join(args)} failed ({cp.returncode}): {cp.stderr.strip() or cp.stdout.strip()}"
            )
        return cp

    def out(self, *args: str) -> str:
        return self.run(*args).stdout.strip()


def repo_root(start: Path) -> Path:
    cp = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False
    )
    if cp.returncode != 0:
        raise ReconcileError(f"not a git checkout: {start}")
    return Path(cp.stdout.strip())


def derived_paths(git: Git) -> tuple[list[str], dict[str, str]]:
    """Every tracked path whose `merge` attribute names a custom driver, and driver→command.

    A custom driver is the repository saying "this content is produced, not merged" — the
    exact set a reconcile may regenerate. Raises when a named driver is not registered in
    this checkout: without it git text-merges the file silently, and a text-merged ledger
    is the one thing this script must never produce.
    """
    files = git.out("ls-files", "-z").split("\0")
    files = [f for f in files if f]
    if not files:
        return [], {}
    cp = git.run("check-attr", "-z", "--stdin", "merge", input_text="\0".join(files) + "\0")
    fields = cp.stdout.split("\0")
    derived: list[str] = []
    drivers: dict[str, str] = {}
    # -z output is a flat sequence of path, attribute, value triples.
    for i in range(0, len(fields) - 2, 3):
        path, _attr, value = fields[i], fields[i + 1], fields[i + 2]
        if value in _BUILTIN_MERGE:
            continue
        derived.append(path)
        if value not in drivers:
            cmd = git.run("config", "--get", f"merge.{value}.driver", check=False).stdout.strip()
            if not cmd:
                # A path `.gitattributes` routes through a driver is GENERATED — the generator
                # is known. What is missing is the driver that would run it in this checkout, and
                # the message says exactly that: a verifier that reads "unregistered
                # driver" as "hand-authored" parks on the wrong story, and the brief it posts
                # misdescribes the file to the implementer sent to fix it.
                raise ReconcileError(
                    f"`{path}` is a GENERATED file (`.gitattributes` routes it through merge driver "
                    f"`{value}`) but has no merge driver registered in this checkout "
                    f"(`git config merge.{value}.driver` is unset). Run the repository's driver "
                    "registration first — a text merge of a generated file is never correct."
                )
            drivers[value] = cmd
    return sorted(derived), drivers


def gitlink_paths(git: Git) -> list[str]:
    out = git.out("ls-files", "-s", "-z")
    paths: list[str] = []
    for entry in out.split("\0"):
        if not entry:
            continue
        meta, _tab, path = entry.partition("\t")
        if meta.split(" ")[0] == _GITLINK_MODE:
            paths.append(path)
    return sorted(paths)


def own_work_signature(git: Git, base: str, head: str, excluded: list[str]) -> Counter[str]:
    """The work between `base` and `head`: every changed line, keyed by file, no context.

    Line numbers move when `main` edits above a hunk, so hunk headers are dropped; what is
    kept is every `+`/`-` line, prefixed by the file it belongs to. A multiset, because the
    invariant is arithmetic: after the merge the branch's own work is what it was MINUS
    whatever `main` also did (a fix the branch took that main then landed cancels — it is on
    both sides now, and `git diff main HEAD` rightly no longer shows it).
    """
    pathspec = [".", *[f":(exclude){p}" for p in excluded]]
    cp = git.run("diff", "-U0", "--no-color", "--no-ext-diff", base, head, "--", *pathspec)
    sig: Counter[str] = Counter()
    current = ""
    for line in cp.stdout.splitlines():
        if line.startswith("diff --git "):
            current = line.split(" b/", 1)[-1]
        elif line.startswith(("+++ ", "--- ")):
            continue
        elif line.startswith(("+", "-")):
            sig[f"{current}\t{line}"] += 1
    return sig


def conflicted_paths(git: Git) -> list[str]:
    out = git.out("diff", "--name-only", "--diff-filter=U", "-z")
    return sorted(p for p in out.split("\0") if p)


def resolve_gitlink(git: Git, path: str) -> str | None:
    """Resolve a conflicted submodule pointer to the DESCENDANT side, or None if neither
    side descends from the other (a genuine fork of the submodule — work, not mechanics).

    git already fast-forwards a submodule pointer itself when the submodule is checked out
    and the commits are reachable; this arm is for the checkout where it could not tell."""
    ours = git.run("rev-parse", f":2:{path}", check=False).stdout.strip()
    theirs = git.run("rev-parse", f":3:{path}", check=False).stdout.strip()
    if not ours or not theirs:
        return None
    sub = Git(git.root / path)
    if not (git.root / path / ".git").exists():
        return None
    sub.run("fetch", "-q", "--all", check=False)
    for a, b in ((ours, theirs), (theirs, ours)):
        cp = sub.run("merge-base", "--is-ancestor", a, b, check=False)
        if cp.returncode == 0:
            git.run("update-index", "--cacheinfo", f"{_GITLINK_MODE},{b},{path}")
            return b
    return None


def restore(git: Git, head_before: str, moved_gitlinks: list[str] | None = None) -> None:
    """Put the checkout back exactly where it was — whether the merge is mid-flight or committed.

    `reset --hard` restores the gitlink in the index but never a submodule's worktree, so
    the pointers this run moved are re-synced explicitly."""
    if git.run("rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0:
        git.run("merge", "--abort", check=False)
    git.run("reset", "-q", "--hard", head_before)
    for path in moved_gitlinks or []:
        git.run("submodule", "update", "--init", "--", path, check=False)


def reconcile(root: Path, base: str, dry_run: bool) -> Outcome:
    git = Git(root)
    if git.run("symbolic-ref", "-q", "HEAD", check=False).returncode != 0:
        raise ReconcileError("detached HEAD — check out the work branch first")
    if git.out("status", "--porcelain", "--untracked-files=no"):
        raise ReconcileError("the worktree has uncommitted changes to tracked files — commit or stash them first")
    remote = base.split("/", 1)[0] if "/" in base else ""
    if remote:
        git.run("fetch", "-q", remote)

    base_sha = git.out("rev-parse", "--verify", f"{base}^{{commit}}")
    head_before = git.out("rev-parse", "HEAD")
    merge_base = git.out("merge-base", base_sha, head_before)
    out = Outcome(result="nothing-to-do", base=base_sha, head_before=head_before, head_after=head_before)
    if merge_base == base_sha:
        out.detail = f"{base} is already contained in HEAD"
        return out

    derived, _drivers = derived_paths(git)
    gitlinks = gitlink_paths(git)
    excluded = derived + gitlinks
    before = own_work_signature(git, merge_base, head_before, excluded)
    mains_own = own_work_signature(git, merge_base, base_sha, excluded)

    merged = git.run("merge", "--no-ff", "--no-edit", base_sha, check=False)
    if merged.returncode != 0:
        conflicts = conflicted_paths(git)
        if not conflicts:
            restore(git, head_before)
            raise ReconcileError(
                f"git merge failed without conflicts (a hook?): {merged.stderr.strip() or merged.stdout.strip()}"
            )
        real: list[str] = []
        for path in conflicts:
            if path in derived:
                # The driver is registered (derived_paths checked) and still left a conflict —
                # the generator itself failed. Not text-mergeable, not ours to guess.
                restore(git, head_before)
                raise ReconcileError(f"regen driver left `{path}` conflicted — the generator failed; nothing changed")
            if path in gitlinks:
                if resolve_gitlink(git, path) is None:
                    real.append(path)
                continue
            real.append(path)
        if real:
            restore(git, head_before)
            out.result = "conflict"
            out.conflicts = real
            out.detail = "conflicts outside derived paths — this is work, not a reconcile"
            return out
        committed = git.run("commit", "--no-edit", check=False)
        if committed.returncode != 0:
            restore(git, head_before)
            raise ReconcileError(f"could not commit the merge: {committed.stderr.strip() or committed.stdout.strip()}")

    head_after = git.out("rev-parse", "HEAD")
    # Which derived paths the merge actually touched — reported so the reader can see what
    # was regenerated, never guessed at.
    changed = git.out("diff", "--name-only", head_before, head_after, "--", *derived).splitlines() if derived else []
    out.derived_resolved = sorted(p for p in changed if p)
    # Submodule pointers the merge moved — whether git fast-forwarded them itself (it does,
    # when the submodule is checked out and one side descends from the other) or the
    # conflict arm above picked the descendant. Read from the trees, never from bookkeeping.
    for path in gitlinks:
        before_ptr = git.run("rev-parse", f"{head_before}:{path}", check=False).stdout.strip()
        after_ptr = git.run("rev-parse", f"{head_after}:{path}", check=False).stdout.strip()
        if after_ptr and after_ptr != before_ptr:
            out.gitlinks_resolved.append(f"{path}@{after_ptr[:12]}")
            # Bring the submodule worktree to the pointer the tree now carries, so a later
            # `git add -A` cannot stage the stale one back (the submodule-pointer guard's
            # favourite false positive). Best-effort: the merge is right either way.
            git.run("submodule", "update", "--init", "--", path, check=False)

    after = own_work_signature(git, base_sha, head_after, excluded)
    expected = before - mains_own  # Counter subtraction: lines main also did cancel out
    if after != expected:
        restore(git, head_before, [g.split("@", 1)[0] for g in out.gitlinks_resolved])
        out.result = "invariant-broken"
        out.head_after = head_before
        diff_n = sum(((after - expected) + (expected - after)).values())
        out.detail = f"the branch's own work would change ({diff_n} line(s) differ) — not a regen-only reconcile"
        return out

    out.result = "reconciled"
    out.head_after = head_after
    if dry_run:
        restore(git, head_before, [g.split("@", 1)[0] for g in out.gitlinks_resolved])
        out.detail = f"dry run — would merge {base_sha[:12]} into {head_before[:12]}; checkout restored"
        out.head_after = head_before
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--base", default="origin/main", help="the ref to merge in (default: origin/main)")
    ap.add_argument("--dry-run", action="store_true", help="prove the reconcile, then restore the checkout")
    ap.add_argument("--json", action="store_true", help="print the outcome as JSON on the last line")
    ap.add_argument("--root", default=".", help="a path inside the checkout (default: cwd)")
    args = ap.parse_args(argv)
    try:
        root = repo_root(Path(args.root).resolve())
        out = reconcile(root, args.base, args.dry_run)
    except ReconcileError as exc:
        out = Outcome(result="error", detail=str(exc))
    label = {
        "reconciled": "RECONCILED",
        "nothing-to-do": "NOTHING TO DO",
        "conflict": "CONFLICT — route as work",
        "invariant-broken": "REFUSED — own work would change",
        "error": "COULD NOT RUN",
    }[out.result]
    print(f"regen-reconcile: {label}")
    if out.head_before:
        print(f"  head: {out.head_before[:12]} -> {out.head_after[:12]}   base: {out.base[:12]}")
    if out.derived_resolved:
        print(f"  derived paths regenerated: {', '.join(out.derived_resolved)}")
    if out.gitlinks_resolved:
        print(f"  submodule pointers taken forward: {', '.join(out.gitlinks_resolved)}")
    if out.conflicts:
        print(f"  conflicting paths: {', '.join(out.conflicts)}")
    if out.detail:
        print(f"  {out.detail}")
    if args.json:
        print(json.dumps(out.__dict__))
    return out.exit_code


if __name__ == "__main__":
    sys.exit(main())
