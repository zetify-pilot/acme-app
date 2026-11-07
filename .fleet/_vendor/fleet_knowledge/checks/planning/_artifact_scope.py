"""Which PRD artifacts a process-artifact gate is allowed to judge.

Two gates share this: one proves a design reconciled the requirement register, one proves the
scope offer ran. Both bind *process artifacts*, and both would be wrong to apply to the whole
corpus, for two separate reasons:

**Scope is by git AUTHORSHIP DATE, not a baseline file.** Every artifact in the tree the day
such a rule lands lacks the section, and none of them is in violation — they were authored
under a command that had no such phase. That is a different population from a baseline, which
grandfathers real violations of a rule that DID exist; here the population is bounded by a
date, so a date is the honest instrument and needs no list to maintain.

ONE KNOWN, CHOSEN MISS: a pre-cutoff artifact that is re-authored after it (a design sent back
and put through the pipeline again) keeps its original birth date and stays out of scope, even
though that re-run really did pass through the phase. Catching it would mean scoping on
"modified since" instead of "created since", which re-admits every pre-existing artifact the
moment anyone touches one — a strictly worse trade. The miss shrinks as the corpus turns over.

**Scope is also DIFF-LIMITED.** The gate evaluates only PRDs whose own directory changed in the
diff range — the "this change IS that PRD's work" signal. A whole-corpus blocking check would
red *every* change the moment one artifact landed short; diff-limiting means the offending
change is the one that goes red, and since an artifact can only enter scope by being committed,
there is no leak. `--all` runs the whole corpus for an audit.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import _git
from ._git import changed_paths

#: `knowledge/prds/<NNNN-slug>/...` — the directory whose change means "this is that PRD's work".
PRD_DIR_RE = re.compile(r"^(?P<root>.+)/(?P<dir>\d{4}-[^/]+)/")
STATUS_RE = re.compile(r"^status:\s*([a-z-]+)\s*$", re.M)


def prds_in_scope(repo_root: Path, prd_root: Path, base: str | None) -> list[Path]:
    """PRD directories to evaluate: those touched in the diff range, or all of them."""
    if not prd_root.is_dir():
        return []
    everything = sorted(p for p in prd_root.iterdir() if p.is_dir())
    if base is None:
        return everything
    changed = changed_paths(repo_root, base)
    if changed is None:  # no usable range (shallow clone, no remote) — check everything
        return everything
    try:
        root_rel = str(prd_root.relative_to(repo_root))
    except ValueError:
        root_rel = str(prd_root)
    prefix = f"{root_rel}/"
    touched = {f[len(prefix) :].split("/", 1)[0] for f in changed if f.startswith(prefix) and "/" in f[len(prefix) :]}
    return [p for p in everything if p.name in touched]


def prd_status(prd_dir: Path) -> str | None:
    """The PRD's authored `status:`, or None when there is no readable prd.md."""
    prd_md = prd_dir / "prd.md"
    if not prd_md.is_file():
        return None
    m = STATUS_RE.search(prd_md.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else None


#: The one line a plain-title-only edit adds. Anything else in the diff is a real edit.
PLAIN_TITLE_ADDED_RE = re.compile(r"^plain_title:\s*\S")

#: Diff-header lines that start with `-`/`+` but are not content.
_DIFF_HEADER_PREFIXES = (
    "+++",
    "---",
    "@@",
    "diff ",
    "index ",
    "new file ",
    "deleted file ",
    "old mode ",
    "new mode ",
    "similarity index ",
    "rename from ",
    "rename to ",
)


def plain_title_only_edit(repo_root: Path, rel_path: str, base: str) -> bool:
    """True when `rel_path` differs from `base` only by an added `plain_title:` line.

    A plain title says nothing about scope (owner decision, 2026-11-05). Adding one to a
    shipped artifact must not drag that artifact's whole governance record back through a
    gate, so every diff-scoped PRD gate asks this first.

    Reads the working tree against `base`, so it answers the same way at pre-commit (staged
    and unstaged) and in CI (a clean checkout at the head commit). A file that is new against
    `base` shows its whole body as added and is therefore never title-only — a new artifact
    still owes its full record. A git failure reads as "not title-only": the gate stays on.

    An artifact with NO diff of its own (a design beside a PRD that was only titled) is in
    scope only because its PRD directory moved. It is exempted when that directory's whole
    diff is the one `plain_title:` line. Any other change in the directory keeps it checked.
    """
    diff = _git.git(repo_root, "diff", "-U0", base, "--", rel_path) or ""
    if not diff:
        return _directory_diff_is_title_only(repo_root, Path(rel_path).parent.as_posix(), base)
    return _diff_is_one_plain_title_line(diff)


def _directory_diff_is_title_only(repo_root: Path, prd_dir: str, base: str) -> bool:
    """True when the whole diff under `prd_dir` is one added `plain_title:` line."""
    diff = _git.git(repo_root, "diff", "-U0", base, "--", prd_dir) or ""
    return bool(diff) and _diff_is_one_plain_title_line(diff)


def _diff_is_one_plain_title_line(diff: str) -> bool:
    """True when `diff` adds exactly one `plain_title:` line and removes nothing."""
    added: list[str] = []
    removed = 0
    for line in diff.splitlines():
        if line.startswith(_DIFF_HEADER_PREFIXES):
            continue
        if line.startswith("+"):
            added.append(line[1:])
        elif line.startswith("-"):
            removed += 1
    return removed == 0 and len(added) == 1 and bool(PLAIN_TITLE_ADDED_RE.match(added[0]))
