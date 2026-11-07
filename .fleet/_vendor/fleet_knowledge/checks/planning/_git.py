"""Git, scoped to one knowledge base's repository root.

Three of the ported checks are history-dependent — a gate that binds only artifacts authored
on or after a cutoff needs to know when a file was born, and an id-collision gate needs to
compare this branch against `main`'s tip. Every call here is bounded by a root passed in, so
nothing reaches a repository the caller did not name.

**Git absence is never a violation.** A knowledge base checked out of a tarball, a corpus
with no VCS at all — each makes these checks inapplicable, not failing. A shallow clone is
not an absent repository: it is a git checkout whose base commit is missing, so helpers still
degrade here, and a caller that must not fail open (the `areas` planning rule, ENG-21061)
distinguishes the two with `is_repository` and refuses rather than noting the gap. Every
helper degrades to "" / None / False rather than raising, and the checks that need history
say so through `applies()`.

**A failed history walk is not "no history".** The two dating walks return None when the
`git log` itself fails — and None is a third answer, distinct from the empty dict a
successful walk over nothing returns. A check that cannot date its artifacts must refuse
(`walk_refusal` is the refusal text); reading a failed walk as "no dates" has produced both
directions of lie — corpus-wide phantom violations (the plan gate's grandfather emptied) and
silently unchecked corpora (the process-artifact gates' cutoff scope emptied).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

#: Every git invocation is bounded, so a wedged network fetch cannot hang a pre-commit hook.
#:
#: WHY 600 AND NOT 120 — MEASURED, not defensive slack. One invocation is not cheap: git
#: simplifies history once PER PATHSPEC, so the cost of `first_commit_dates` is linear in the
#: number of plan files, and the plan corpus grows by roughly one per PRD. Measured on an idle
#: box at the 2026-09-29 corpus (1,249 plans + 91 cited specs = 1,340 pathspecs):
#:
#:     n=  100   4.4s      n=  400  17.2s      n= 1340  35.0s   (knowledge/prds only)
#:     n=  600   5.7s      n=  800  28.3s      n= 1340 102.7s   (plans + cited specs)
#:
#: ~26-46 ms per path, and the mix matters as much as the count — a pathspec under a large,
#: churny tree costs more than one under a quiet one. That put the walk at 103s against the
#: old 120s ceiling: 86% of it, idle. CI runs this on a shared runner where a lane's wall time
#: varies 2-3x on capacity, so the walk crossed the ceiling and the gate REFUSED — reading as
#: a broken checkout and reported on 4 of the 17 open PRs sampled at 2026-09-29T01:00Z, every
#: one of which had changed nothing the walk reads.
#:
#: The cost is IRREDUCIBLE without a semantic redesign, and the alternatives were measured and
#: rejected — each loses plan files, which is the one direction this module must never fail in:
#:
#:   * a DIRECTORY pathspec (`-- knowledge/prds`) runs in 0.5s and MISSES 97 of 1,340 paths
#:     (7.2%): git prunes a commit whose directory is TREESAME, so a file added on the far
#:     side of a merge never reports as `A`. A missed path dates to NEVER_COMMITTED, reads as
#:     pre-cutover, and is SILENTLY EXEMPTED from the gate — the "silently unchecked corpus"
#:     direction this module's docstring warns about.
#:   * `--full-history`, `-m`, `--diff-merges=on` and `--diff-merges=first-parent` over that
#:     directory recover 1 of the 97. `--no-renames` is 0.66x but re-dates a renamed file to
#:     its rename, making a pre-cutover plan look post-cutover — a false finding.
#:   * chunking is EXACT (6x100 union == one 600-path walk, 0 missing, 0 date differences) but
#:     buys nothing: the cost is linear in paths, not in invocations.
#:
#: So the ceiling is a HANG DETECTOR, and it must sit above the legitimate cost or it is a
#: false-failure generator. 600s is ~6x the idle worst case and still fails a wedged git
#: forever. The plan half of that worst case is now OFF this path: `prd_plans` dates its plans
#: with `first_commit_dates_since`, the ONE-directory, `--since`-bounded walk (0.34s over the
#: 2026-10-01 corpus instead of 29s), and keeps this per-pathspec call for the cited page-specs
#: alone, which are far fewer and must be dated across all history because a spec can predate
#: the cutover. The ceiling still clears the residual specs walk and the other history-dependent
#: checks, so it stays a hang detector rather than a performance target.
GIT_TIMEOUT_SECONDS = 600


def git(root: Path, *args: str) -> str | None:
    """Run git in `root`, returning stdout — or None when it fails or git is absent."""
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
        return None


def git_out(root: Path, *args: str) -> str:
    """`git`, with failure flattened to "" — for callers that treat absence as empty."""
    return git(root, *args) or ""


def is_repository(root: Path) -> bool:
    """True when `root` sits inside a git work tree."""
    return git_out(root, "rev-parse", "--is-inside-work-tree").strip() == "true"


def is_shallow(root: Path) -> bool:
    """True when this checkout cannot support history-dependent dating.

    `--is-shallow-repository` is true whenever `.git/shallow` lists any graft — a depth-1 tip
    fetch, or a long-lived checkout that acquired a graft mid-session. Either shape makes
    `git log --diff-filter=A` date every file to the shallow boundary, so a cutoff-based
    grandfather silently covers nothing.
    """
    return git_out(root, "rev-parse", "--is-shallow-repository").strip() == "true"


def changed_paths(root: Path, base: str) -> set[str] | None:
    """Repo-relative paths differing from `base`, or None if `base` does not resolve.

    The UNION of three views, not the first that answers:

      base...HEAD   committed on the branch (the CI view — merge-base against the PR base)
      base          working tree vs the ref (staged AND unstaged)
      --cached      staged vs HEAD (the pre-commit view: a command stages an artifact and
                    the hook runs BEFORE the commit exists, so no committed range sees it)
    """
    if not git(root, "rev-parse", "--verify", "--quiet", base):
        return None
    out: set[str] = set()
    for args in ((f"{base}...HEAD",), (base,), ("--cached",)):
        out |= {ln for ln in git_out(root, "diff", "--name-only", *args).splitlines() if ln.strip()}
    return out


def head_tree(root: Path, root_rel: str) -> set[str]:
    """Repo-relative paths under `root_rel` present in the HEAD commit.

    A file absent here is STAGED BUT NOT YET COMMITTED — the moment a process-artifact gate
    most wants to fire, and the one no commit-date lookup can see. Empty on an unborn HEAD,
    which correctly makes every path uncommitted.
    """
    return {ln for ln in git_out(root, "ls-tree", "-r", "--name-only", "HEAD", "--", root_rel).splitlines() if ln}


def adds_since(root: Path, cutoff: str, root_rel: str) -> dict[str, str] | None:
    """`{repo-relative path: YYYY-MM-DD}` for files ADDED under `root_rel` since `cutoff`.

    None when the walk itself fails — git absent, a non-zero exit, the timeout expired —
    which is a DIFFERENT answer from `{}`: an empty dict means the walk ran and added
    nothing since the cutoff, and a caller that cannot tell the two apart reads a failed
    walk as "nothing authored recently" and gates nothing. Callers refuse on None.

    ONE `git log` for the whole corpus rather than one per file: the per-path form costs
    seconds in a hook that runs on every commit, and this costs milliseconds because
    `--since` bounds the walk to the commits after the cutoff.

    Three properties make the cheap form correct:
      * `--since` filters on COMMITTER date, never earlier than the author date, so the
        result is a superset of "authored since" — the author date decides, below. A two-day
        slack absorbs timezone skew at the boundary.
      * git's default rename detection reports a moved file as `R`, which `--diff-filter=A`
        excludes — renaming a pre-cutoff directory for a better slug does not make its
        contents read as newly authored.
      * walking newest→oldest and letting later writes win leaves the EARLIEST add per path,
        which is the one that matters for a file deleted and restored.
    """
    since = date_minus_days(cutoff, 2)
    out = git(root, "log", "--diff-filter=A", f"--since={since}", "--format=%x00%aI", "--name-only", "--", root_rel)
    if out is None:
        return None
    dates: dict[str, str] = {}
    current = ""
    for line in out.splitlines():
        if line.startswith("\0"):
            current = line[1:11]
        elif line.strip() and current:
            dates[line.strip()] = current  # newest first — the last write is the earliest add
    return dates


def first_commit_dates_since(root: Path, cutoff: str, root_rel: str) -> dict[str, str] | None:
    """`{repo-relative path: committer day}` for files under `root_rel` born on/after `cutoff`.

    The cutover-bounded cousin of `first_commit_dates` (ENG-13723). `first_commit_dates` takes
    one pathspec per plan plus one per cited page-spec, so its cost is linear in the corpus and
    moves 2-3x with runner capacity; this takes ONE directory pathspec and bounds the walk with
    `--since`, so it costs the same however many plans have accumulated (measured 2026-10-01:
    0.34s over `knowledge/prds` at 1,332 plan files, against 29s for the plan half alone of the
    per-pathspec form, and the 103s the full call cost once its cited specs were added).

    Two deliberate differences from `adds_since`, each required to reproduce
    `first_commit_dates`'s answer for the plans that survive the cutover:

      * RENAMES COUNT. `adds_since` uses `--diff-filter=A`, so git's rename detection reports a
        moved plan as `R` and drops it. That is right where "renamed" must not read as
        "authored", but `first_commit_dates` passes only the NEW path, so git never pairs the
        rename and reports it as `A`, dating the plan to the move. A bounded walk that dropped
        renames would grandfather a plan the full walk checks — silently exempting it, the one
        direction this module must never fail in. So this walks `--diff-filter=AR` and keeps the
        post-move path.
      * COMMITTER DATES. The day is `%cs`, matching `first_commit_dates`, so a surviving plan's
        date cannot shift by a day (101 of 772 surviving plans carried an author date a day
        after their committer date at 2026-10-01) and flip the cutover or the plan-vs-spec
        comparison the additive gate makes.

    None when the walk fails — git absent, a non-zero exit, the timeout expired — which the
    caller REFUSES on, exactly as it does for `first_commit_dates`. `{}` means the walk ran and
    nothing was born since the cutoff. `date_minus_days(cutoff, 2)` widens `--since` so a
    committer date on the far side of a timezone boundary is not dropped; the caller compares
    each returned day against the cutover itself, so the slack never admits a pre-cutover plan.
    """
    since = date_minus_days(cutoff, 2)
    out = git(
        root,
        "log",
        "--diff-filter=AR",
        f"--since={since}",
        "--name-status",
        "-M",
        "--format=%x00%cs",
        "--reverse",
        "--",
        root_rel,
    )
    if out is None:
        return None
    dates: dict[str, str] = {}
    day: str | None = None
    for line in out.split("\n"):
        if line.startswith("\x00"):
            day = line[1:11]
        elif line.strip() and day is not None:
            parts = line.split("\t")
            kind = parts[0][:1]
            # `A\tpath` for an add; `R<score>\told\tnew` for a rename — take the new path.
            if kind == "A":
                dates.setdefault(parts[1], day)
            elif kind == "R" and len(parts) >= 3:
                dates.setdefault(parts[2], day)  # earliest add in the window wins
    return dates


def first_commit_dates(root: Path, paths: list[Path]) -> dict[str, str] | None:
    """First-commit date per path, keyed by repo-relative path string.

    None when the walk itself fails — git absent, a non-zero exit, the timeout expired —
    which is a DIFFERENT answer from `{}`: an empty dict means the walk ran and git found
    no adds for these paths. A caller that cannot tell the two apart reads a failed walk as
    "no path was ever committed", empties every cutover grandfather, and reports the whole
    corpus as phantom violations. Callers refuse on None. (Nothing to date — an empty
    `paths` — is `{}`, not None: there is no question to refuse.)

    ONE `git log` invocation, never one per file: a per-file walk over hundreds of paths
    re-walks the full history each time and took 80+ seconds on an idle box, far worse under
    concurrent CI load. Passing every path as a pathspec keeps git's own history
    simplification per path (so a file introduced via a merge commit is still found) while
    walking history once.

    Callers MUST refuse a shallow clone before invoking this — on a shallow clone every path
    dates to the boundary commit and a cutover grandfather is silently empty.
    """
    if not paths:
        return {}
    rels: list[str] = []
    for p in paths:
        try:
            rels.append(str(p.relative_to(root)))
        except ValueError:
            continue
    if not rels:
        return {}
    out = git(root, "log", "--diff-filter=A", "--name-only", "--format=%x00%cs", "--reverse", "--", *rels)
    if out is None:
        return None
    dates: dict[str, str] = {}
    day: str | None = None
    for line in out.split("\n"):
        if line.startswith("\x00"):
            day = line[1:]
        elif line and day is not None:
            dates.setdefault(line, day)
    return dates


def date_minus_days(iso_day: str, days: int) -> str:
    """`iso_day` shifted back by `days`, as `YYYY-MM-DD`.

    Not a duration computation — it widens a git `--since` window so the committer-date
    filter cannot drop a commit whose author date sits on the far side of a timezone
    boundary. Nothing derived from it is ever reported.
    """
    from datetime import date, timedelta  # noqa: PLC0415 - kept local to this one use

    y, m, d = (int(x) for x in iso_day.split("-"))
    return (date(y, m, d) - timedelta(days=days)).isoformat()


def walk_refusal(gate: str, cutoff: str, walk: str, harm: str) -> str:
    """The refusal text a history-dependent gate emits when its `git log` walk fails.

    The `PLANS_SHALLOW_REFUSAL` shape generalized: the shallow-clone probe catches one way
    for a checkout to be undateable, and this catches the rest — a wedged git, a corrupt
    object store, a walk past the timeout. The cause is named (`git` reports no detail here
    because stderr is suppressed for hook quietness), and so is the repair. `harm` carries the
    direction-specific sentence: what the failure would have been misread as had the gate
    guessed — corpus-wide phantom findings for the plan gate, a silently empty scope for the
    two process-artifact gates.

    `walk` is a LIVENESS PROBE, and the text says so rather than presenting it as the failing
    command. It was previously offered as "run the walk by hand to see git's own error", and it
    is NOT that command: it walks one directory, while the check passes one pathspec per plan
    file and per cited spec. The two differ by ~200x (0.5s vs 103s at 1,340 paths, measured
    2026-09-29), so the probe succeeds on exactly the checkouts where the real walk timed out —
    the reader runs it, sees a clean exit, and is told to look for a git error that was never
    there. A repair instruction that cannot reproduce the condition it repairs is worse than no
    instruction: it certifies the instrument that produced the wrong answer.
    """
    return (
        f"{gate} refused: the `git log` history walk failed in this checkout — git reported an "
        f"error or the {GIT_TIMEOUT_SECONDS}s timeout expired — so nothing can be dated.\n"
        "\n"
        f"{harm}\n"
        "\n"
        "Two causes, and they need different repairs.\n"
        "\n"
        "1. GIT ITSELF RETURNED AN ERROR. Probe liveness with a CHEAPER walk — this is not "
        "the command that failed (it walks one directory where the check passes one pathspec "
        "per artifact, so it can succeed where the real walk did not), but a non-zero exit "
        "here is git's own error, and it is the cause:\n"
        f"  {walk}\n"
        "\n"
        "2. THE WALK WAS TOO SLOW. The real walk simplifies history once per pathspec — one "
        "per plan file plus one per cited page-spec — so its cost grows with the corpus and "
        "with how loaded the box is, and a shared CI runner is several times slower than an "
        "idle one. If the probe above succeeds quickly, the checkout is fine and the ceiling "
        "is the cause; re-run the job rather than repairing the tree.\n"
        "\n"
        "A shallow clone repairs with `git fetch --unshallow`. A corpus with no git repository "
        "at all makes these checks inapplicable: the runner skips them, it never fails them."
    )
