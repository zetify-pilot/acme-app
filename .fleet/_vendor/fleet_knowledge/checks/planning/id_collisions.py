"""Id-collision detection against main's TIP and open peer PRs, plus authoring-time allocation.

**CLAIMS FIRST (2026-09-29).** Allocation is no longer a snapshot. When a corpus configures
`[fleet.planning] id_claims = true`, `--allocate` reserves each id by creating
`refs/ids/<ID>` on GitHub — an atomic create that returns HTTP 422 to every later caller — and
walks to the next number on a 422 (`_claims.py`). The check then requires that **every id this
change introduces has a claim ref**: an ERROR in CI (and an ERROR when CI cannot reach GitHub —
a gate that cannot see the claim set fails closed), a WARNING in a local hook, where an offline
commit must still work. Everything below stays as the BACKSTOP: the main-tip and history legs
catch a real duplicate whatever the claims say, and the open-peer-PR scan runs for an overlap
period while branches allocated by the old scan drain.

**OVERLAP — REMOVE LATER.** The open-peer-PR leg (`list_open_peer_heads` and its use in
`analyse` and, only for a claims-less corpus, `allocate`) exists only because branches minted
before claims existed hold ids no ref reserves. Once every open branch predates the claims
cutover by a week, it is pure cost (a full-depth fetch and an archive per open PR) and should be
deleted; the claim leg subsumes it. **Allocation stopped paying that cost first (ENG-13595):**
with claims configured the claim refs ARE the peer reservation set, so `allocate` skips the
per-peer materialise + collect (one `git archive` of the corpus and a full parse per open PR,
~21 s each). Only `analyse` still scans peers, and only a corpus without claims still scans them
to allocate.

Every other id gate fires AFTER a branch has minted an id and written it into a dozen files.
None compares the ids THIS BRANCH introduces against the trunk's TIP — the merge base cannot
see ids the trunk minted after the branch diverged, which is exactly the collision class
(three in 48 hours the week this was written).

An id is a COLLISION when it is present in BOTH this branch's tree AND the trunk's tip but was
NOT present at the merge base: both sides minted it independently after diverging. **A git
text-merge cannot see this** — append-only registers merge cleanly with the id duplicated, and
the number silently captures one branch's identity.

Four id spaces are covered:

  - requirement registers (`RUN-NNN`, `AGT-NNN`, …) — the rows the register reader admits
  - capability ids (`CAP-NNNN`)                    — the capability ledger
  - PRD numbers (`NNNN`)                           — each PRD's own frontmatter
  - migration versions (`NNNNN`)                   — `<dir>/NNNNN_<slug>.sql`

The fourth is the one contended ordinal space the first three miss: a duplicate version is
cheap to catch WITHIN one tree, but each branch holds exactly one and is green on its own; the
duplicate materialises on the trunk after both land, as a red trunk that blocks every push.
Migration directories are independent namespaces with independent counters, so a version is
keyed by its directory and cannot alias one in another.

**PEER OPEN-PR SCAN.** The main-tip leg alone is not enough: four concurrent branches each read
free-on-main, minted overlapping blocks, and only found out at rebase (one renumber touched 148
references). A captured id produces NO merge conflict — the single-line `Next id:` counter
resolves cleanly and one branch's row silently inherits an identity another already published.
So detection also runs against open peer PR heads — the live claim set, not the hundred stale
remote-tracking refs a long-lived checkout carries. The self-PR is excluded so a branch never
reds against itself, and the scan degrades to a NOTE when the PR host CLI is unavailable rather
than failing closed: offline commits must still work.

**STACKED PRs ARE ONE ALLOCATION.** A branch that spawns a stacked child PR re-presents its
ids on the child's head by construction — the child descends from the parent, so it inherits
every id the parent minted. An id present in a merge base of the two heads is shared ancestry,
not a capture, and flagging it would block every commit on an id-minting branch the moment it
spawns a child (ENG-13188). So the peer leg skips an id whose peer shares it through a merge
base; only an id absent from EVERY base was minted independently on both sides. Every base is
read (`git merge-base --all`): a criss-cross history — each side merged the other's pre-merge
head, which is what a sibling PR that merged this branch into itself produces — has more than
one, and the single base `git merge-base` returns arbitrarily can be the one that does NOT hold
the shared id.

**SELF-PR EXCLUSION BY PUSH DESTINATION.** Excluding the self-PR by head SHA or head ref name
misses the normal shape of working on someone else's in-flight PR — a fetched PR head in a
renamed worktree branch matches neither, so the self-PR reads as a peer and every id the branch
legitimately owns is flagged as a capture, inviting a renumber that would corrupt the branch's
own ids. The push DESTINATION ref is the stable identity, and it is what excludes the self-PR.

**THE ON-DEMAND PEER FETCH MUST NOT GRAFT THE CHECKOUT SHALLOW.** Any `--depth` fetch writes
`.git/shallow` and flips the repository shallow-wide, so every LATER history-dependent consumer
in the same hook chain refuses — on a checkout THIS hook broke mid-chain. The fetch is
full-depth: no depth means no shallow negotiation, so the shallowness state is left as found.

**THE ALLOCATION RECORD, NOT THE FILE'S TEXT.** A held id means ALLOCATED, and a ledger's
other prose is not an allocation: its `Next id:` counter line names the next FREE id, and its
reservation comments quote other branches' live ids to explain why the counter skipped them
(ENG-8935). ENG-9321: a whole-text sweep read the counter into every tree's held set, so when
main's counter jumped past a token, every open branch based before the jump failed at once
against every peer — "minted by THIS branch" for an id no branch ever minted. The register
space reads table rows (`load_registers`); the ledger gets the same discipline: an id is held
where it heads a table row, and nowhere else. The counter stays read as a counter
(`counters_in`), which is what allocation's floor needs.

A rebase resolves the text while leaving a capture in place, so this must re-run after EVERY
rebase onto the trunk, and after every peer merge that lands new ids.

A second, earlier signal: when this branch mints a new row into a register whose local
`Next id:` counter is BELOW the trunk's, anything it mints in that range collides on merge.
That is a WARNING; the exact collision above is the hard red.

**SCRATCH HYGIENE.** Each materialisation writes a tree the size of the corpus's own
`knowledge/` + `migrations/` subtrees into the default temp location (caller-provided via
`TMPDIR` — the same knob a CI lane points at a runner-cleaned directory). The temp trees
live for the process by design, so a run killed HARD (job timeout/cancel — SIGKILL, no
interpreter exit, no finalizers) leaks its materialisations onto the box it ran on. Three
defenses keep that bounded instead of unbounded:

  - the scratch is SMALL: the archive is streamed straight into the extraction — no
    intermediate tarball ever lands on disk — and only the member types the readers consume
    (`*.md`, `*.sql`) are extracted, not the whole subtree;
  - every materialisation is NAMED as this check's (`fleet-idcoll-XXXX` under `TMPDIR`), and
    every check start SWEEPS the ones the running user owns that are over an hour old, so a
    hard-killed run's leak is gone by the next run rather than forever. Name+owner+age scoping
    is what makes the sweep safe on shared boxes: no run lives an hour, and another seat's
    scratch is another user's. The anonymous `tmp`-named dirs a release before the prefix left
    are still reclaimed by content shape, after a day;
  - the sweep is best-effort by contract: it never raises, and a sweep that cannot run never
    fails the check.

Ported from `scripts/validate_id_collisions.py`; messages and exit codes unchanged.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fleet_knowledge.config import git_context
from fleet_knowledge.corpusref import owned_prefixes
from fleet_knowledge.requirements import load_registers, row_fragment_ids

from ._api import ERROR, WARNING, Report, finding
from ._claims import (
    NETWORK_TIMEOUT_S,
    ClaimStore,
    ClaimsUnavailableError,
    GitHubClaims,
    claim_mode,
    claim_name,
    highest,
)
from ._config import PlanningConfig
from ._git import git, is_repository
from ._markdown import frontmatter

NAME = "id-collisions"

PRD_FM_RE = re.compile(r"^prd:\s*(\d{4})", re.M)
#: A goose-style migration filename is `NNNNN_<slug>.sql`; the runner keys on the numeric
#: version, not the filename, so two differently-named files sharing a prefix are ONE id.
MIGRATION_FILE_RE = re.compile(r"^(\d+)_.*\.sql$")

#: Temp trees stay alive for the process — a materialised ref is read lazily by the caller.
#: A hard-killed process leaks whatever this list held at the time; the sweep at check start
#: reclaims those (see `sweep_stale_materializations`).
_TMP: list[tempfile.TemporaryDirectory[str]] = []

#: A `tempfile` default name — the `tmpXXXX` shape every interpreter's scratch uses. The sweep
#: matches the name AND the materialised content shape; a name alone never identifies a leak.
_TMPNAME_RE = re.compile(r"^tmp[a-z0-9_]{8,}$")
#: The per-subtree tarballs the pre-streaming materialiser wrote beside the extracted tree and
#: unlinked after. A hard kill between archive and extract left one behind; the sweep tolerates
#: that remnant when attributing an old dir to this check.
_STALE_TAR_RE = re.compile(r"^tree\d+\.tar$")

#: How old a scratch dir must be, in seconds (one day), before the sweep will attribute it to
#: a dead run. No run of this check lives that long; a live concurrent run on a shared box is
#: hours old at most, so the age is the guard that makes deletion safe without locks or
#: liveness probes.
SWEEP_AGE_S = 24 * 60 * 60

#: THIS CHECK'S OWN SCRATCH NAME. Every materialisation is made as `<TMPDIR>/fleet-idcoll-XXXX`,
#: so a leak is attributable by its NAME — no content-shape guess — and the sweep can reclaim it
#: within the hour rather than the day the anonymous `tmpXXXX` shape needs. Measured on a fleet box
#: (2026-10-08): a target repo's pre-commit runs this check on every commit, a hook killed by the agent's
#: Bash ceiling leaked 45-57 MB per run, and `fleetd` held 96 `tmp*` dirs, 8.5 GB, on a 16 GB
#: `/tmp` tmpfs shared with every seat on the box. `TMPDIR` still decides WHERE (`tempfile`).
MATERIALIZE_PREFIX = "fleet-idcoll-"

#: How old one of THIS check's own prefixed dirs must be before the sweep removes it: an hour. No
#: run of the check lives that long — it reads a handful of refs and exits — so a prefixed dir
#: older than this belongs to a run that was killed. Only dirs the sweeping user OWNS qualify: on
#: a box where several seats share `/tmp`, one user's sweep never reaches another's live run.
OWN_SWEEP_AGE_S = 60 * 60

#: The dot file the sweep touches in each scanned root to read "now" — a fresh mtime on the
#: very clock the candidates' mtimes are stored in. The package carries no wall clock (the
#: planning contract's no-date/no-duration rule keeps rate-and-projection prose out of check
#: findings), and an mtime-vs-mtime comparison is the one that cannot drift.
_SWEEP_SENTINEL = ".id-collisions-sweep-now"

#: The member types the readers consume (`collect` walks `*.md`, `migration_versions_in`
#: walks `*.sql`, and a tier's `rows/*.json` fragments carry the PG/SL ids). A feature map's
#: committed `<name>.md.tmpl` shell is read too: its rendered `.md` is gitignored, so at a ref
#: the shell is the only place a capability row written literally in it exists — dropping it
#: here made every git snapshot blind to rows the working tree (and history) still saw.
#: Everything else in the archived subtrees — images, generated sources — is dead weight for
#: this check and is not extracted.
_EXTRACT_SUFFIXES = (".md", ".md.tmpl", ".sql", ".json")


@dataclass(frozen=True)
class PeerHead:
    """One open PR head that may hold ids this branch must not capture."""

    number: int
    sha: str
    ref: str


@dataclass(frozen=True)
class Snapshot:
    """The four id spaces plus the counters, as one tree holds them."""

    registers: set[str]
    capabilities: set[str]
    prds: set[str]
    migrations: set[str]
    counters: dict[str, int]


def archive_paths(kb: Any) -> tuple[str, ...]:
    """The subtrees materialised out of a ref.

    Archived independently, and a path missing at the ref is SKIPPED rather than failing the
    whole materialisation: a ref that carries the knowledge tree but no migrations (an old
    commit, a test fixture) must still yield the id spaces it does have, and a hard failure
    would silently disable the entire leg rather than one id space.
    """
    cfg = PlanningConfig.of(kb)
    knowledge_name = Path(kb.knowledge).name
    return (knowledge_name, *cfg.migrations_dirs)


def id_archive_paths(kb: Any) -> tuple[str, ...]:
    """The id-bearing files this check reads, and nothing else.

    `archive_paths` carries the WHOLE `knowledge/` tree, because the tip and the branch head
    also feed the counter-staleness leg, which reads a `Next id:` counter from any `.md` in
    the corpus. The merge-base and open-PR legs need only the four id SETS (registers,
    capability ledger, PRD frontmatter, migrations), and `collect(..., with_counters=False)`
    reads exactly those — so they materialise only the files that can hold them.

    This is the fix for the cost that scales with the fleet's open-PR count (ENG-12481): the
    peer leg reads one tree PER OPEN PR, and reading a PR's whole `knowledge/` tree costs ~2s,
    of which the `knowledge/prds` subtree alone is ~70% for files this check never looks at
    (design docs, plans, mockups). The narrow set — the register directory, each PRD's own
    `prd.md`, the capability ledger, and the migration dirs — is the same input at a fraction
    of the bytes, so the per-commit cost stops tracking the whole corpus.
    """
    cfg = PlanningConfig.of(kb)
    knowledge_name = Path(kb.knowledge).name
    return (
        f"{knowledge_name}/{cfg.requirements_dir}",
        f"{knowledge_name}/{cfg.features_dir}",
        f"{knowledge_name}/{cfg.prds_dir}/*/prd.md",
        f"{knowledge_name}/{cfg.capability_ledger}",
        # The per-row fragments hold the PG/SL ids when a tier has migrated (ENG-12549); a
        # tier still on its committed table holds them in the register `.md`, which the first
        # entry above does not cover — `counters_in` reads it from the full-tree legs, and the
        # narrow legs read the fragments here. Missing dirs are skipped by `git archive`.
        f"{knowledge_name}/{cfg.program_detail_dir}/rows",
        f"{knowledge_name}/{cfg.slice_detail_dir}/rows",
        *cfg.migrations_dirs,
    )


def resolve_tip(root: Path, explicit: str | None, default_ref: str) -> str | None:
    """The trunk's tip — the commit that can see ids minted after the branch diverged."""
    if explicit:
        return explicit if git(root, "rev-parse", "--verify", f"{explicit}^{{commit}}") else None
    out = git(root, "rev-parse", "--verify", default_ref)
    return out.strip() if out else None


def resolve_head(root: Path, explicit: str | None) -> str | None:
    """The commit whose ids are THIS branch's.

    CI passes the PR head sha explicitly, because its working tree is checked out at the merge
    ref, not the branch head — a merged tree has already resolved (or silently dropped) a
    collision, so it must not be the thing we diff. Locally, None means the working tree.
    """
    if not explicit:
        return None
    return explicit if git(root, "rev-parse", "--verify", f"{explicit}^{{commit}}") else None


def merge_base(root: Path, a: str | None, b: str | None) -> str | None:
    if not a or not b:
        return None
    out = git(root, "merge-base", a, b)
    return out.strip() if out else None


def merge_bases(root: Path, a: str | None, b: str | None) -> list[str]:
    """EVERY common ancestor of `a` and `b` (`git merge-base --all`).

    A criss-cross history has more than one: each side merged the other's pre-merge head, so
    no single commit dominates the shared ancestry. `git merge-base` returns just one of them,
    and which one is arbitrary — a caller that asks "is this id shared ancestry?" must read
    every base, or an id that sits only in the base it did not pick reads as a second mint
    (the criss-cross sibling-PR false positive). Empty when either ref is missing or the two
    share no ancestor.
    """
    if not a or not b:
        return []
    out = git(root, "merge-base", "--all", a, b)
    if not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def merge_head(root: Path) -> str | None:
    """The other parent of an in-progress merge, if any.

    For the common "merge the trunk into the branch" it IS the tip being compared against, so
    using it as the base during a merge stops the leg from reporting the trunk's own new rows
    as this branch's: the merge has already applied them to the working tree while HEAD is
    still the pre-merge commit, which would make a merge-base against HEAD predate them.

    `MERGE_HEAD` may be stale or unresolvable (a leftover from a completed or aborted merge, a
    ref that no longer exists), so the value is validated before use — otherwise it poisons
    `merge-base` into the unresolvable, fail-closed path.
    """
    gd = git(root, "rev-parse", "--git-dir")
    if not gd:
        return None
    p = Path(gd.strip())
    if not p.is_absolute():
        p = root / p
    mh = p / "MERGE_HEAD"
    if not mh.is_file():
        return None
    lines = [ln.strip() for ln in mh.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return None
    if not git(root, "rev-parse", "--verify", f"{lines[0]}^{{commit}}"):
        return None
    return lines[0]


def materialize(root: Path, ref: str, paths: tuple[str, ...]) -> Path | None:
    """`paths` at `ref` in a fresh temp tree; None if none of them could be read.

    ONE `git archive` per subtree rather than a `git show` per file — materialising three refs
    each holding hundreds of documents was spawning a subprocess per file and taking ~70s.

    The archive is STREAMED into the extraction (`tarfile` mode `r|`) and filtered to
    `_EXTRACT_SUFFIXES` on the way through: no intermediate tarball is ever written to disk,
    and the extracted tree holds only what `collect` reads. A subtree whose archive fails or
    truncates contributes nothing — its partial extraction is removed and the path is skipped,
    exactly the shape the "missing subtree" contract below asks for; a write error mid-extract
    (a full disk) still raises, as it always has.
    """
    td = tempfile.TemporaryDirectory(prefix=MATERIALIZE_PREFIX)
    _TMP.append(td)
    out = Path(td.name)
    got = False
    for path in paths:
        try:
            proc = subprocess.Popen(
                ["git", "archive", "--format=tar", ref, path],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            continue
        ok = False
        try:
            assert proc.stdout is not None  # guaranteed by stdout=PIPE
            with proc.stdout, tarfile.open(fileobj=proc.stdout, mode="r|") as tar:
                for member in tar:
                    if member.isfile() and member.name.endswith(_EXTRACT_SUFFIXES):
                        tar.extract(member, out, filter="data")
                # `tarfile`'s stream mode stops at the tar end-of-archive marker, but git
                # pads the archive out to its blocking factor and is still writing when the
                # reader stops. Closing the pipe there kills git with SIGPIPE (rc -13), and
                # the `ok` check below then discards a subtree that was extracted in full —
                # leaving an EMPTY register set that reports the whole register as colliding
                # (ENG-15525). Drain to EOF so git finishes and `wait()` reports its real
                # status; the trailing bytes are padding, not archive members.
                proc.stdout.read()
            ok = proc.wait() == 0
        except (tarfile.TarError, OSError):
            # Truncated or empty stream (a bad ref, a path absent at the ref, git dying
            # mid-archive). Close the pipe so git cannot block on a full buffer, reap it, and
            # treat the subtree as unread.
            proc.kill()
            proc.wait()
            ok = False
        if not ok:
            shutil.rmtree(out / path, ignore_errors=True)
            continue
        got = True
    return out if got else None


_BLOB_MODES = frozenset({"100644", "100755"})


def _read_blobs(root: Path, shas: Sequence[str]) -> dict[str, bytes] | None:
    """Blob contents for `shas` through ONE `git cat-file --batch` process; None on any failure."""
    wanted = list(dict.fromkeys(shas))
    if not wanted:
        return {}
    try:
        proc = subprocess.run(
            ["git", "cat-file", "--batch"],
            cwd=root,
            input=("\n".join(wanted) + "\n").encode(),
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout
    pos = 0
    blobs: dict[str, bytes] = {}
    for sha in wanted:
        nl = out.find(b"\n", pos)
        if nl < 0:
            return None
        header = out[pos:nl].split()
        if len(header) != 3 or header[1] != b"blob":
            return None
        size = int(header[2])
        blobs[sha] = out[nl + 1 : nl + 1 + size]
        pos = nl + 1 + size + 1
    return blobs


def _store(out: Path, rel: str, data: bytes) -> None:
    dest = out / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def materialize_batch(root: Path, ref: str, paths: tuple[str, ...]) -> Path | None:
    """`paths` at `ref` (only the files the readers consume) in a fresh temp tree.

    Two git processes in total — `git ls-tree -r` and one `git cat-file --batch` — however many
    subtrees `paths` names, where `materialize` spawns a `git archive` per subtree. None when
    the ref cannot be listed (a bad ref); a path absent at the ref contributes nothing.
    """
    # `ls-tree` takes literal path prefixes, not pathspec globs: list the glob-free prefix of
    # each path and apply the glob here, with git's own pathspec meaning (`*` crosses `/`).
    prefixes = sorted({p.split("*", 1)[0].rsplit("/", 1)[0] if "*" in p else p for p in paths})
    matchers = [
        re.compile("^" + ".*".join(re.escape(part) for part in p.split("*")) + ("$" if "*" in p else "(/|$)"))
        for p in paths
    ]
    try:
        listing = subprocess.run(
            ["git", "ls-tree", "-r", "-z", ref, "--", *prefixes],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if listing.returncode != 0:
        return None
    entries: list[tuple[str, str]] = []
    for rec in listing.stdout.split(b"\0"):
        if not rec:
            continue
        meta, _, name = rec.decode("utf-8", "surrogateescape").partition("\t")
        mode, _kind, sha = meta.split()
        if mode in _BLOB_MODES and name.endswith(_EXTRACT_SUFFIXES) and any(m.match(name) for m in matchers):
            entries.append((sha, name))
    blobs = _read_blobs(root, [sha for sha, _ in entries])
    if blobs is None:
        return None
    td = tempfile.TemporaryDirectory(prefix=MATERIALIZE_PREFIX)
    _TMP.append(td)
    out = Path(td.name)
    for sha, name in entries:
        _store(out, name, blobs[sha])
    return out


@contextlib.contextmanager
def delta_applied(
    root: Path, ref: str, paths: tuple[str, ...], anchor_ref: str, anchor_dir: Path
) -> Iterator[bool | None]:
    """Turn `anchor_dir` (`paths` at `anchor_ref`) into `paths` at `ref` FOR THE BLOCK, in place.

    Reads only what `ref` changed relative to the anchor: one `git diff-tree` restricted to
    `paths` and one `git cat-file --batch` for the changed blobs. Yields False when nothing
    id-bearing differs (the directory is the anchor, untouched), True when the changes are
    applied, and None when the delta cannot be applied (a bad ref, a path that changed kind) —
    the caller then falls back to a full read. Whatever the block does, the anchor is restored on
    exit, so the next ref starts from the anchor again.

    In place and not a copy because a copy PER REF is what dominated the run: copying a ~8,000
    file id tree and then deleting it again cost ~4 s + ~6 s per open PR, ~14 minutes for 56.
    """
    try:
        diff = subprocess.run(
            ["git", "diff-tree", "-r", "-z", "--raw", "--no-renames", "--no-commit-id", anchor_ref, ref, "--", *paths],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError:
        yield None
        return
    if diff.returncode != 0:
        yield None
        return
    tokens = diff.stdout.decode("utf-8", "surrogateescape").split("\0")
    touched: list[str] = []
    written: list[tuple[str, str]] = []
    i = 0
    while i + 1 < len(tokens) and tokens[i].startswith(":"):
        _om, nm, _osha, nsha, _status = tokens[i][1:].split()
        name = tokens[i + 1]
        i += 2
        if not name.endswith(_EXTRACT_SUFFIXES):
            continue
        touched.append(name)
        if nm in _BLOB_MODES:
            written.append((nsha, name))
    if not touched:
        yield False
        return
    blobs = _read_blobs(root, [sha for sha, _ in written])
    if blobs is None or any((anchor_dir / name).is_dir() for name in touched):
        yield None
        return
    saved: dict[str, bytes | None] = {}
    for name in touched:
        target = anchor_dir / name
        saved[name] = target.read_bytes() if target.is_file() else None
    try:
        for name in touched:
            (anchor_dir / name).unlink(missing_ok=True)
        for sha, name in written:
            _store(anchor_dir, name, blobs[sha])
    except OSError:
        applied = False
    else:
        applied = True
    try:
        yield True if applied else None
    finally:
        for name, original in saved.items():
            target = anchor_dir / name
            if original is None:
                target.unlink(missing_ok=True)
            else:
                _store(anchor_dir, name, original)


def sweep_stale_materializations(
    allowed: set[str],
    *,
    age_s: int = SWEEP_AGE_S,
    own_age_s: int = OWN_SWEEP_AGE_S,
    roots: Sequence[Path] | None = None,
) -> int:
    """Delete this check's own hard-kill leaks; return how many trees were removed.

    TWO KINDS, by name. A `fleet-idcoll-*` dir (`MATERIALIZE_PREFIX`) is this check's by
    construction: it goes once it is `own_age_s` (an hour) old, when the sweeping user owns it.
    The anonymous `tmpXXXX` shape below is what a release before the prefix made, and keeps its
    content-shape attribution and its day — those leaks still sit on boxes until it reaps them.

    The dirs a hard-killed run leaves behind are indistinguishable from every other
    interpreter's `tmpXXXX` scratch by NAME alone, so attribution needs the content shape: a
    candidate's every top-level child must be one of the top-level names this check
    materialises — the first segment of each `allowed` path, since `db/migrations` materialises
    under a `db/` dir — or a `tree<N>.tar` remnant from the pre-streaming shape. And the dir
    must be at least `age_s` old: no run of this check lives that long, so an old shape-matched
    dir cannot belong to a live concurrent run on a shared box.

    Best-effort by contract: entries owned by other users, vanished mid-sweep, or unreadable
    are skipped, and an unscannable root is skipped whole — the sweep never raises, so
    hygiene can never fail the check that runs it.
    """
    top_level = {path.split("/", 1)[0] for path in allowed}
    scanned: set[str] = set()
    removed = 0
    for base in roots if roots is not None else (Path(tempfile.gettempdir()), Path("/tmp")):
        sentinel = base / _SWEEP_SENTINEL
        try:
            key = os.path.realpath(base)
            if key in scanned:
                continue
            scanned.add(key)
            sentinel.touch()
        except OSError:
            continue
        entries: list[os.DirEntry[str]] = []
        try:
            now = sentinel.stat().st_mtime
            cutoff = now - age_s
            own_cutoff = now - own_age_s
            entries = list(os.scandir(base))
        except OSError:
            entries = []
        finally:
            with contextlib.suppress(OSError):
                sentinel.unlink()
        uid = os.getuid() if hasattr(os, "getuid") else None
        for entry in entries:
            try:
                if entry.name.startswith(MATERIALIZE_PREFIX):
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    st = entry.stat(follow_symlinks=False)
                    if (uid is not None and st.st_uid != uid) or st.st_mtime > own_cutoff:
                        continue  # another user's, or young enough to be a live run's
                    shutil.rmtree(entry.path, ignore_errors=True)
                    if not os.path.exists(entry.path):
                        removed += 1
                    continue
                if not _TMPNAME_RE.fullmatch(entry.name) or not entry.is_dir(follow_symlinks=False):
                    continue
                if entry.stat(follow_symlinks=False).st_mtime > cutoff:
                    continue  # young — a live run's scratch, possibly this very process's
                children = {child.name for child in os.scandir(entry.path)}
                if not children or not all(name in top_level or _STALE_TAR_RE.fullmatch(name) for name in children):
                    continue  # not this check's shape — never a candidate for deletion
            except OSError:
                continue
            shutil.rmtree(entry.path, ignore_errors=True)
            if not os.path.exists(entry.path):
                removed += 1
    return removed


def counters_in(knowledge: Path, cfg: PlanningConfig) -> dict[str, int]:
    """`{prefix: the highest `Next id:` number}` across every document in the knowledge tree.

    Counters live wherever an append-only register does — a requirement domain, a capability
    ledger, a slice or program register, a todo register, and any future one. Scanning a
    hard-coded pair of locations made allocation claim `-001` against dozens of existing rows
    with `floor: empty` reading as "nothing yet". Walking the whole tree means the next register
    added in a third location is discoverable without another one-off.
    """
    out: dict[str, int] = {}
    if not knowledge.is_dir():
        return out
    counter_re = re.compile(cfg.counter_pattern)
    for f in sorted(knowledge.rglob("*.md")):
        if f.name == "README.md" or f.stem.startswith("_"):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in counter_re.finditer(text):
            # PREFIX-NNN… — split once so a future multi-hyphen form cannot IndexError.
            head, _, digits = m.group(1).partition("-")
            if head and digits.isdigit():
                n = int(digits)
                if head not in out or n > out[head]:
                    out[head] = n
    return out


def migration_versions_in(root: Path, cfg: PlanningConfig) -> set[str]:
    """Migration versions under each configured directory, keyed by their namespace.

    A migration is keyed by its numeric version, not its filename, so `01919_a.sql` and
    `01919_b.sql` are ONE id. Each directory is an independent namespace with its own counter,
    so the version is prefixed with its directory: `migrations/ingest-pg/00003` never aliases
    `migrations/00003`.
    """
    out: set[str] = set()
    for rel_dir in cfg.migrations_dirs:
        base = root / rel_dir
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.sql")):
            m = MIGRATION_FILE_RE.match(f.name)
            if not m:
                continue
            ns = f.parent.relative_to(root).as_posix()
            out.add(f"{ns}/{int(m.group(1)):05d}")
    return out


def capability_ledger_ids(text: str, cfg: PlanningConfig) -> set[str]:
    """Capability ids ALLOCATED in a ledger — its row table, never the file's whole text.

    ENG-9321: the ledger's `Next id:` counter line names the next FREE id (the opposite of an
    allocation) and its reservation comments quote other branches' live ids to explain why the
    counter skipped them. A whole-text sweep read both into every tree's held set, so every
    branch based before a counter jump held every token the file ever printed, and the peer
    leg failed all open branches at once against all peers. The register reader reads table
    ROWS (`load_registers`); the ledger gets the same discipline: an id is held where it heads
    a table row, and nowhere else.

    Since ENG-12981 the ledger is the frozen historical old→new mapping, not the allocation
    record: a capability PR no longer appends a row, so the LIVE id set is the feature maps'
    (`feature_capability_ids`). This reader stays because the pre-migration mapping rows are
    still allocated ids and must never be captured.
    """
    row_re = re.compile(
        rf"^[ \t]*\|\s*({re.escape(cfg.capability_prefix)}-\d{{{cfg.capability_id_digits}}})\s*\|",
        re.M,
    )
    return set(row_re.findall(text))


def feature_capability_ids(knowledge: Path, cfg: PlanningConfig) -> set[str]:
    """Capability ids held by the FEATURE MAPS — the live allocation set (ENG-12981).

    Allocation no longer appends a row to `capability-aliases.md`, so that file is no longer a
    complete claim set: the ids a branch holds are the ones in its feature maps. A row heads a
    table line (`| CAP-NNNN | … |`) and a migrated row is a fragment file named for the id, so
    both shapes are read — the same pair the feature-map reader itself admits.

    A table line is read from the committed `<name>.md.tmpl` shell of a fragment-backed map as
    well as from any `.md`. The rendered `.md` is gitignored and exists only where a render ran
    (the working tree, after the pre-commit hook), so a row written literally in the shell was
    held by the working tree and by history but by NO git snapshot — and the permanence leg
    read `tree - base` as a fresh mint of an id the base already held. Every reader must see the
    same claim set whatever shape the row takes; the union with a rendered `.md` is harmless,
    since that file is a function of the shell and the fragments.
    """
    out: set[str] = set()
    cap_re = re.compile(
        rf"^[ \t]*\|\s*({re.escape(cfg.capability_prefix)}-\d{{{cfg.capability_id_digits}}})\s*\|", re.M
    )
    base = knowledge / cfg.features_dir
    if not base.is_dir():
        return out
    for f in sorted([*base.glob("*.md"), *base.glob("*.md.tmpl")]):
        try:
            out |= set(cap_re.findall(f.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    rows = base / "rows"
    if rows.is_dir():
        id_re = re.compile(rf"^{re.escape(cfg.capability_prefix)}-\d{{{cfg.capability_id_digits}}}$")
        for f in sorted(rows.glob("*.json")):
            if id_re.match(f.stem):
                out.add(f.stem)
    return out


def capability_ids_ever_used(root: Path, knowledge_name: str, cfg: PlanningConfig, base: str | None) -> set[str]:
    """Every capability id present in `base`'s ancestry, read from the feature maps.

    `base` is the change's comparison commit. Only its ANCESTORS are walked (`git log <base>`),
    so an id this branch just minted is not in the set and cannot flag itself. Returns an EMPTY
    set when there is no base or the walk fails — permanence is enforced beside the other
    fail-open legs, never as a corpus-wide phantom (a walk that cannot run must never report
    every id in the tree as reused).

    The walk is a single streamed `git log -p`, ~1s on this corpus (1567 commits over the
    feature maps), and it is the only source of a BURNED id: a capability deleted from every
    map leaves no row and no current file, so without history a later author could silently
    reuse its number.
    """
    if not base:
        return set()
    features = f"{knowledge_name}/{cfg.features_dir}"
    out = git(root, "log", "-p", "--format=", base, "--", features)
    if out is None:
        return set()
    return set(re.findall(cfg.capability_id_pattern, out))


def register_fragment_ids(knowledge: Path, cfg: PlanningConfig) -> set[str]:
    """Program and slice ids held by per-row fragments, across both tiers.

    A migrated corpus keeps each PG/SL row in `<tier_detail_dir>/rows/<ID>.json` and no longer
    in the register table, so the table rows and the `Next id:` counters this check used to
    read for those id spaces are gone (ENG-12549, ENG-12661). The fragment filename is the id,
    and it is the same claim a table row made — so it feeds both collision detection and the
    allocation floor exactly as a row did.
    """
    out: set[str] = set()
    prefixed = re.compile(cfg.prefixed_id_pattern)
    for detail_dir, prefix in ((cfg.program_detail_dir, cfg.program_prefix), (cfg.slice_detail_dir, cfg.slice_prefix)):
        base = knowledge / detail_dir / "rows"
        if not base.is_dir():
            continue
        for f in sorted(base.glob("*.json")):
            m = prefixed.match(f.stem)
            if m and m.group(1) == prefix:
                out.add(f.stem)
    return out


def collect(root: Path, knowledge_name: str, cfg: PlanningConfig, *, with_counters: bool = True) -> Snapshot:
    """Every id space one repository tree holds.

    `with_counters=False` skips the whole-tree `Next id:` walk. The collision predicate reads
    only the four id sets, so the peer leg — one tree per open PR — does not need the counters
    and should not pay a 7000-file read for each one. The counter-staleness warning and
    `--allocate` do need them, and keep the default.
    """
    knowledge = root / knowledge_name

    caps: set[str] = set()
    ledger = knowledge / cfg.capability_ledger
    if ledger.is_file():
        caps = capability_ledger_ids(ledger.read_text(encoding="utf-8", errors="replace"), cfg)
    # The live claim set is the feature maps (ENG-12981): allocation no longer appends to the
    # ledger, so reading only the ledger would leave every new id unchecked.
    caps |= feature_capability_ids(knowledge, cfg)

    prds: set[str] = set()
    pbase = knowledge / cfg.prds_dir
    if pbase.is_dir():
        for d in sorted(pbase.iterdir()):
            f = d / "prd.md"
            if not (d.is_dir() and f.is_file()):
                continue
            fm = frontmatter(f.read_text(encoding="utf-8", errors="replace"))
            m = PRD_FM_RE.search(fm) if fm else None
            if m:
                prds.add(m.group(1))

    # The register reader is the package's own (`fleet_knowledge.requirements`): this leg needs
    # the id SET and nothing else, and a second parser would eventually disagree with it about
    # which rows are real — which is the one way an id-collision gate can be quietly wrong.
    # Structural findings are discarded here on purpose; the requirement checks own reporting.
    rows, _structural = load_registers(
        knowledge,
        reserved_prefixes=frozenset(cfg.reserved_requirement_prefixes),
        dir_name=cfg.requirements_dir,
    )

    # The register reader matches a domain's fragments to its register `.md`, which is absent
    # from this tree for a fragment-backed domain whose shell is a committed `<name>.md.tmpl`
    # (the generated `.md` is rendered on demand and never committed — ENG-12980). The fragment
    # filename IS the id, so the rows are read directly and independently of the shell, or an
    # interactive `--allocate` (which renders nothing first) hands out an id a fragment already
    # holds (ENG-14286).
    return Snapshot(
        registers=set(rows) | register_fragment_ids(knowledge, cfg) | row_fragment_ids(knowledge, cfg.requirements_dir),
        capabilities=caps,
        prds=prds,
        migrations=migration_versions_in(root, cfg),
        counters=counters_in(knowledge, cfg) if with_counters else {},
    )


def _current_branch(root: Path) -> str | None:
    out = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if not out:
        return None
    name = out.strip()
    return None if not name or name == "HEAD" else name


def _current_head_sha(root: Path) -> str | None:
    out = git(root, "rev-parse", "HEAD")
    return out.strip() if out else None


def _push_dest_refs() -> set[str]:
    """The remote head refs THIS push targets — the stable identity of "the PR I am pushing to".

    A pre-push hook runner exports git's destination ref as `PRE_COMMIT_REMOTE_BRANCH` (full
    form `refs/heads/<name>`); the PR host CLI names the same ref bare, so it is normalised
    here. Empty outside a pre-push hook — there the SHA and local-branch-name matchers remain
    the only self-exclusions.
    """
    raw = os.environ.get("PRE_COMMIT_REMOTE_BRANCH", "").strip()
    if not raw:
        return set()
    bare = raw.removeprefix("refs/heads/")
    return {bare} if bare else set()


def _fetch_peer_head(root: Path, number: int) -> bool:
    """Fetch one open PR head on demand, full-depth and time-bounded.

    The full-depth form is load-bearing: a `--depth` fetch writes `.git/shallow` and makes
    every later history walk in the same hook chain refuse. The timeout is the other half:
    this runs once per open PR, so one wedged fetch left unbounded multiplies across the
    whole board — the "hangs silently" failure ENG-13806 reports. A fetch that does not
    complete is a peer this run cannot check, not a reason to hang; the caller skips it.
    """
    try:
        proc = subprocess.run(
            ["git", "fetch", "--no-tags", "origin", f"pull/{number}/head"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=NETWORK_TIMEOUT_S,
            env=os.environ.copy(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def list_open_peer_heads(
    root: Path,
    *,
    explicit: list[str] | None = None,
    self_sha: str | None = None,
    self_ref: str | None = None,
    dest_refs: set[str] | None = None,
) -> list[PeerHead]:
    """Open PR heads that may hold ids this branch must not capture.

    Excludes THIS branch's own PR — matched by head SHA, head ref name, or the push destination
    ref — so a push never reds against itself, including from a worktree whose local branch was
    fetched under a different name. `explicit` is a test/CI escape hatch of raw SHAs; the
    production path uses the PR host CLI and degrades to `[]` when it is missing or
    unauthenticated, so offline commits still work. A peer head that is not locally reachable is
    fetched on demand — FULL-DEPTH, never `--depth`.
    """
    if explicit is not None:
        out: list[PeerHead] = []
        self_sha = self_sha or _current_head_sha(root)
        for i, raw in enumerate(explicit):
            sha = raw.strip()
            if not sha or (self_sha and sha == self_sha):
                continue
            if not git(root, "rev-parse", "--verify", f"{sha}^{{commit}}"):
                continue
            out.append(PeerHead(number=i + 1, sha=sha, ref=sha[:12]))
        return out

    dest_refs = _push_dest_refs() if dest_refs is None else dest_refs
    self_sha = self_sha or _current_head_sha(root)
    self_ref = self_ref if self_ref is not None else _current_branch(root)
    try:
        raw_json = subprocess.check_output(
            ["gh", "pr", "list", "--state", "open", "--limit", "200", "--json", "number,headRefOid,headRefName"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
            env=os.environ.copy(),
            timeout=60,
        )
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
        return []
    try:
        rows = json.loads(raw_json or "[]")
    except json.JSONDecodeError:
        return []
    peers: list[PeerHead] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        sha = str(row.get("headRefOid") or "").strip()
        ref = str(row.get("headRefName") or "").strip()
        try:
            num = int(row.get("number") or 0)
        except (TypeError, ValueError):
            num = 0
        if not sha or not num:
            continue
        if self_sha and sha == self_sha:
            continue
        if self_ref and ref and ref == self_ref:
            continue
        # The PR whose head ref IS the push destination is the PR being pushed to — its ids are
        # this branch's own by construction, however the local branch is named. Excluded
        # silently: the correct response to "these ids are on the PR you are pushing to" is
        # nothing.
        if dest_refs and ref and ref in dest_refs:
            continue
        if not git(root, "rev-parse", "--verify", f"{sha}^{{commit}}"):
            # Fetch the PR head on demand so a local pre-push still sees peers whose branches
            # were never checked out here. Fail open on fetch errors/timeouts, and NEVER
            # shallow-fetch.
            if not _fetch_peer_head(root, num):
                continue
            if not git(root, "rev-parse", "--verify", f"{sha}^{{commit}}"):
                continue
        peers.append(PeerHead(number=num, sha=sha, ref=ref or sha[:12]))
    return peers


def claim_store(kb: Any) -> ClaimStore:
    """The production claim store for this knowledge base's repository."""
    cfg = PlanningConfig.of(kb)
    return GitHubClaims(
        Path(kb.root),
        remote=cfg.id_claim_remote,
        namespace=cfg.id_claim_namespace,
        repo=cfg.id_claim_repo,
    )


def claimable_ids(snap: Snapshot) -> set[str]:
    """Every id in `snap` that a claim reserves, as its claim name.

    Registers (requirement rows and PG/SL fragments), capabilities and PRD numbers. Migration
    versions are NOT claimed: they are allocated by timestamp, and the duplicate-version leg is
    their gate.
    """
    return (
        {claim_name("REG", c) for c in snap.registers}
        | {claim_name("CAP", c) for c in snap.capabilities}
        | {claim_name("PRD", c) for c in snap.prds}
    )


def _owned_refusal(prefix: str, owner: str) -> str:
    return (
        f"prefix `{prefix}` is owned by corpus `{owner}` (`[fleet.planning.corpora]`) — its ids are "
        f"minted in that corpus's register, never here; allocate it from the `{owner}` corpus"
    )


def format_id(prefix: str, n: int) -> str:
    """Render a claimed id in `prefix`'s own id shape.

    PRD numbers are bare four-digit numbers in a PRD's frontmatter — a `PRD-NNNN` form would be
    a shape no register uses. Every other prefix is a prefixed id.
    """
    if prefix == "PRD":
        return f"{n:04d}"
    width = 4 if prefix == "CAP" else 3
    return f"{prefix}-{n:0{width}d}"


def allocate(
    kb: Any,
    *,
    prefix: str,
    count: int,
    tip: str | None = None,
    peers: list[PeerHead] | None = None,
    claims: ClaimStore | None = None,
    progress: Callable[[str], None] | None = None,
) -> tuple[list[str], str, list[str]]:
    """`(claimed_ids, next_free, claim_sources)` for `count` new ids under `prefix`.

    The floor is the max of: every id already on the trunk tip, the local working tree, any
    legacy `Next id:` counter among those trees, and — when the corpus configures claims —
    every claim ref already on GitHub. With claims configured the open-peer heads are NOT
    scanned: the claim refs already name every id an open branch reserved, so the per-peer
    `git archive` + `collect` (the O(open PRs × corpus) cost, ENG-13595) would only repeat what
    the claims say. A corpus without claims keeps the snapshot peer scan, where it is the only
    guard. Sources name which claimant pushed the floor up. Does not mutate the tree; the caller
    writes the rows.

    With claims configured the ids are RESERVED, not merely computed: the whole block is
    created in ONE batched ref push (`git push` of `refs/ids/<ID>` per id, not one `gh api`
    round trip each — ENG-13806), and a 422 on any one of them moves past the block to the next
    number, so the returned ids may skip a number a peer holds. Without a reachable GitHub this
    raises `ClaimsUnavailableError` rather than hand out an unreserved id — an offline author
    writes a placeholder and allocates before pushing. Without claims configured it is the old
    snapshot, which two concurrent allocations can still race.

    `progress` is called with a short line at each phase; it is how `--allocate` reports what
    it is doing instead of printing nothing for minutes (ENG-13806).
    """
    if count < 1:
        raise ValueError("count must be >= 1")
    if not re.fullmatch(r"[A-Z]{2,5}", prefix):
        raise ValueError(f"prefix must be 2–5 uppercase letters, got {prefix!r}")

    def say(message: str) -> None:
        if progress is not None:
            progress(message)

    cfg = PlanningConfig.of(kb)
    if owner := owned_prefixes(cfg.corpora).get(prefix):
        raise ValueError(_owned_refusal(prefix, owner))
    root = Path(kb.root)
    knowledge_name = Path(kb.knowledge).name
    paths = archive_paths(kb)
    sweep_stale_materializations(set(paths))
    tip_sha = resolve_tip(root, tip, cfg.default_diff_base)
    floor = 0
    # One source line per claimant, rewritten whenever that claimant raises the floor — avoids
    # a line per id on a thousand-row register.
    source_by_label: dict[str, str] = {}

    def raise_floor(n: int, label: str, detail: str) -> None:
        nonlocal floor
        if n > floor:
            floor = n
            source_by_label[label] = f"{label} {detail} → floor {format_id(prefix, n)}"

    def consider(tree: Path | None, label: str) -> None:
        if tree is None:
            return
        snap = collect(tree, knowledge_name, cfg)
        high = 0
        high_detail = ""
        if prefix == "PRD":
            # PRD numbers are bare four-digit ids in their own set — in neither the register nor
            # the capability space, and no `Next id:` counter keys them, so a reader that only
            # looked at those would discard the set and claim `-001` with `floor: empty` against
            # hundreds of existing PRDs.
            for pid in snap.prds:
                n = int(pid)
                if n > high:
                    high = n
                    high_detail = f"holds prd {pid}"
        else:
            prefixed = re.compile(cfg.prefixed_id_pattern)
            for cid in snap.registers | snap.capabilities:
                m = prefixed.match(cid)
                if not m or m.group(1) != prefix:
                    continue
                n = int(m.group(2))
                if n > high:
                    high = n
                    high_detail = f"holds {cid}"
        c = snap.counters.get(prefix)
        if c is not None and c - 1 > high:
            # The counter is the NEXT free id, so the highest claimed is c-1.
            high = c - 1
            high_detail = f"counter Next id: {prefix}-{c}"
        if high > 0:
            raise_floor(high, label, high_detail)

    if tip_sha:
        say(f"reading main tip {tip_sha[:12]}")
        consider(materialize(root, tip_sha, paths), f"main tip {tip_sha[:12]}")
    say("reading the local tree")
    consider(root, "local tree")
    if prefix == cfg.capability_prefix:
        # Capability ids are PERMANENT (ENG-12981): a burned id — deleted from every map — is
        # only in the repository's history, so the floor has to clear it too or the allocator
        # hands out a number the collision check then rejects.
        say("reading capability history")
        for base_ref, label in ((tip_sha, "main tip history"), ("HEAD", "local history")):
            ever = capability_ids_ever_used(root, knowledge_name, cfg, base_ref)
            high = max((int(cid.split("-")[1]) for cid in ever), default=0)
            if high:
                raise_floor(high, label, f"burned {format_id(prefix, high)}")
    # ENG-13595: the per-peer tree scan — one `git archive` of the whole knowledge tree plus a
    # full `collect` per open PR, ~21 s each and linear in the fleet's open-PR count — is
    # skipped when claims are configured. The claim refs ARE the peer reservation set (an open
    # branch's allocated id is a `refs/ids/<ID>` once the corpus is on claims), so the atomic
    # create already refuses a number a peer holds; scanning every peer tree again adds nothing
    # but cost. A corpus with no claims namespace keeps the snapshot scan, which is then its only
    # guard — and its author is warned the ids are unreserved.
    claims_enabled = claims is not None or cfg.id_claims
    if not claims_enabled:
        say("listing open peer PRs")
        if peers is None:
            peers = list_open_peer_heads(root)
        for peer in peers:
            say(f"reading open PR #{peer.number} ({peer.ref})")
            consider(materialize(root, peer.sha, paths), f"open PR #{peer.number} ({peer.ref})")

    if claims is None and cfg.id_claims:
        claims = claim_store(kb)
    if claims is None:
        start = floor + 1
        ids = [format_id(prefix, start + i) for i in range(count)]
        return ids, format_id(prefix, start + count), list(source_by_label.values())

    space = "PRD" if prefix == "PRD" else "REG"
    say("reading the claim refs")
    held = claims.claimed()  # raises ClaimsUnavailableError — never read as "nothing claimed"
    high = highest(held, "PRD" if prefix == "PRD" else prefix)
    if high:
        raise_floor(high, "claim refs", f"hold {format_id(prefix, high)}")
    # The claim must point at a commit GitHub already has; the trunk tip always is one.
    target = tip_sha or (git(root, "rev-parse", "HEAD") or "").strip()

    # Reserve the contiguous block in ONE batched ref push — the "single batched ref push for N
    # ids" the issue asks for (ENG-13806). The per-id `gh api` create was one HTTP round trip
    # per id, so reserving a slice's ids was N network calls.
    block = [format_id(prefix, i) for i in range(floor + 1, floor + count + 1)]
    say(f"reserving {count} {prefix} id(s) in one batched push")
    created = claims.claim_batch({claim_name(space, cid): target for cid in block})
    got = [cid for cid in block if claim_name(space, cid) in created]
    # A block id another session took between the floor read and the push is a gap: walk PAST
    # the block with the atomic per-id create until `count` ids are held. Bounded — a run of
    # taken ids this long means something other than a race is wrong.
    lost = [cid for cid in block if claim_name(space, cid) not in created]
    n = floor + count
    while len(got) < count and n - floor < count + 1000:
        n += 1
        cid = format_id(prefix, n)
        if claims.claim(claim_name(space, cid), target):
            got.append(cid)
        else:
            lost.append(cid)
    if len(got) < count:
        above = format_id(prefix, floor)
        raise ClaimsUnavailableError(f"gave up after {len(lost)} consecutive taken claims above {above}")
    sources = list(source_by_label.values())
    if lost:
        sources.append(f"claim refs taken while allocating (skipped): {', '.join(lost)}")
    return got, format_id(prefix, n + 1), sources


def _check_claim_leg(
    report: Report,
    tree: Snapshot,
    base_snap: Snapshot | None,
    *,
    kb: Any,
    cfg: PlanningConfig,
    claims: ClaimStore | None,
    mode: str | None,
) -> None:
    """Every id this change introduces must carry a claim ref.

    `base_snap=None` means the merge base could not be established (a shallow CI checkout, no
    `origin/main`, no shared ancestor, an unmaterialisable tree). The ids this change INTRODUCES
    cannot then be told from the ones it inherited, so every id in the tree is checked: a gate
    that cannot see the comparison set still refuses an unclaimed id (ENG-21060). This leg needs
    neither the trunk tip nor the merge base, which is why it must never be skipped along with
    the collision comparison.
    """
    mode = mode or claim_mode(cfg.id_claims)
    inherited = claimable_ids(base_snap) if base_snap is not None else set()
    new_ids = claimable_ids(tree) - inherited
    n_claimed = 0
    if base_snap is None and new_ids:
        report.notes.append(
            "id claims: the merge base could not be established, so every id in this tree was "
            f"checked for a claim ({len(new_ids)} id(s))"
        )
    if mode != "off" and new_ids:
        store = claims if claims is not None else claim_store(kb)
        severity = ERROR if mode == "require" else WARNING
        try:
            held = store.claimed()
        except ClaimsUnavailableError as e:
            held = None
            msg = (
                f"id claims: could not read the claim refs ({e}) — {len(new_ids)} new id(s) "
                f"unverified: {', '.join(sorted(new_ids))}"
            )
            if mode == "require":
                report.findings.append(
                    finding(
                        ERROR,
                        msg + " — failing closed: a gate that cannot see the claim set cannot pass the change",
                        hint="Re-run once GitHub is reachable; the check needs `git ls-remote` on the remote.",
                        command=None,
                    )
                )
            else:
                report.notes.append(msg + " (local run: not blocking; CI will check)")
        if held is not None:
            for cid in sorted(new_ids - held):
                if base_snap is None:
                    text = (
                        f"id `{cid}`: present in this tree but never claimed — no `refs/ids/{cid}` exists, "
                        "and with no merge base the check cannot tell it was inherited, so it must be reserved"
                    )
                else:
                    text = (
                        f"id `{cid}`: introduced by THIS change but never claimed — no `refs/ids/{cid}` exists, "
                        "so nothing stops another branch from minting the same number"
                    )
                report.findings.append(
                    finding(
                        severity,
                        text,
                        hint=(
                            "Allocate ids with `--allocate PREFIX N`, which claims them atomically. For an id "
                            "already written, `--claim ID` reserves it; if that reports it taken, renumber."
                        ),
                        command=cfg.command("allocate_ids", prefix=cid.split("-", 1)[0]),
                    )
                )
                if mode != "require":
                    report.notes.append(text + " (warning here; an error in CI)")
            n_claimed = len(new_ids & held)

    if n_claimed:
        if base_snap is None:
            report.notes.append(f"id claims: {n_claimed} id(s) in this tree, each claimed")
        else:
            report.notes.append(f"id claims: {n_claimed} new id(s) introduced by this change, each claimed")


def analyse(
    kb: Any,
    *,
    tip: str | None = None,
    head: str | None = None,
    peers: str | None = None,
    claims: ClaimStore | None = None,
    mode: str | None = None,
) -> Report:
    """Every captured id and every unclaimed new id, plus the stale-counter warnings and notes.

    `mode` is the claim leg's (`off` / `warn` / `require`); None reads it from the corpus
    config and the environment (`_claims.claim_mode`). `claims` defaults to GitHub.
    """
    cfg = PlanningConfig.of(kb)
    root = Path(kb.root)
    knowledge_name = Path(kb.knowledge).name
    paths = archive_paths(kb)
    # The merge-base and peer legs read only the four id sets and never the counters, so they
    # materialise only the id-bearing files — the whole tree per open PR is what made a commit
    # cost track the fleet's open-PR count (ENG-12481).
    id_paths = id_archive_paths(kb)
    report = Report()
    swept = sweep_stale_materializations(set(paths))
    if swept:
        report.notes.append(
            f"hygiene: swept {swept} stale materialisation tmpdir(s) (this check's own, left by a killed run)"
        )

    tip_sha = resolve_tip(root, tip, cfg.default_diff_base)
    head_sha = resolve_head(root, head)

    # Collect THIS branch's tree FIRST. The claim leg below needs it and must run even when a
    # collision comparison cannot, so no early return may leave before it (ENG-21060).
    tree: Snapshot | None = None
    base: str | None = None
    if head_sha is not None:
        head_root = materialize(root, head_sha, paths)
        if head_root is None:
            report.refusal = f"id-collision check — could not materialise branch head {head_sha[:12]}; skipping"
        else:
            tree = collect(head_root, knowledge_name, cfg)
            if tip_sha is not None:
                base = merge_base(root, head_sha, tip_sha)
    else:
        tree = collect(root, knowledge_name, cfg)
        if tip_sha is not None:
            base = merge_base(root, merge_head(root) or "HEAD", tip_sha)

    if tree is None:
        # The named branch head could not be read; the working tree is the best source for the
        # claim leg (and in a CI merge-ref checkout it holds the change). The collision
        # comparison stays skipped — the refusal above already says so.
        tree = collect(root, knowledge_name, cfg)

    if tip_sha is None:
        report.refusal = (
            "id-collision check — no main tip resolved "
            f"(no `{cfg.default_diff_base}` and no `--tip`); nothing to compare against"
        )
        _check_claim_leg(report, tree, None, kb=kb, cfg=cfg, claims=claims, mode=mode)
        return report

    if report.refusal:
        _check_claim_leg(report, tree, None, kb=kb, cfg=cfg, claims=claims, mode=mode)
        return report

    tip_root = materialize(root, tip_sha, paths)
    if tip_root is None:
        report.refusal = f"id-collision check — could not materialise `main` tip {tip_sha[:12]}; skipping"
        _check_claim_leg(report, tree, None, kb=kb, cfg=cfg, claims=claims, mode=mode)
        return report
    tip_snap = collect(tip_root, knowledge_name, cfg)

    base_root = materialize(root, base, id_paths) if base else None
    if base_root is None:
        # An unresolvable merge base is no basis to judge collisions — it means the base could
        # not be found (no common ancestor, a grafted clone, an unresolvable ref) or its tree
        # could not be materialised. Degrading to an empty base set reports the ENTIRE register
        # as colliding. Fail OPEN, symmetric with the two unresolvable inputs above — but the
        # claim leg does not need the base and still runs, failing closed on an unclaimed id.
        report.refusal = "id-collision check — could not establish a merge base; id-collision leg skipped"
        _check_claim_leg(report, tree, None, kb=kb, cfg=cfg, claims=claims, mode=mode)
        return report
    base_snap = collect(base_root, knowledge_name, cfg, with_counters=False)

    spaces = (
        (tree.registers, tip_snap.registers, base_snap.registers, "requirement register", "REG"),
        (tree.capabilities, tip_snap.capabilities, base_snap.capabilities, "capability", "CAP"),
        (tree.prds, tip_snap.prds, base_snap.prds, "PRD number", "PRD"),
        (tree.migrations, tip_snap.migrations, base_snap.migrations, "migration version", ""),
    )
    for ids_h, ids_t, ids_m, label, alloc_prefix in spaces:
        for cid in sorted(ids_h & ids_t - ids_m):
            report.findings.append(
                finding(
                    ERROR,
                    f"{label} id `{cid}`: minted by THIS branch AND already on `main` (both "
                    "allocated it after the branch diverged) — renumber this branch's id before push",
                    hint="Renumber this branch's id (allocate a fresh one) and update every reference.",
                    command=cfg.command("allocate_ids", prefix=alloc_prefix or "RUN"),
                )
            )

    # A capability id is PERMANENT: a branch may not reintroduce an id the repository burned.
    # Since ENG-12981 allocation no longer appends to `capability-aliases.md`, so a capability
    # deleted from every map leaves no row and no current file — HISTORY is the only record
    # that its number ever existed. `new` = ids this branch introduces; `ever` = ids in the
    # base's ancestry; the intersection is a reuse.
    ever = capability_ids_ever_used(root, knowledge_name, cfg, base)
    for cid in sorted((tree.capabilities - base_snap.capabilities) & ever):
        report.findings.append(
            finding(
                ERROR,
                f"capability id `{cid}`: minted by THIS branch but already allocated in this "
                "repository's history — capability ids are permanent and are never reused; mint "
                "a fresh id that has never existed",
                hint=(
                    "Mint a fresh `CAP-NNNN` absent from `main`'s tip, every open peer PR and the repository's history."
                ),
                command=cfg.command("allocate_ids", prefix="CAP"),
            )
        )

    # The claim leg: every id this change introduces must be reserved by a claim ref. This is
    # the gate that makes the atomic allocator binding — an id picked by hand, or by the old
    # snapshot allocator, has no ref, and nothing else stops a peer claiming the same number.
    _check_claim_leg(report, tree, base_snap, kb=kb, cfg=cfg, claims=claims, mode=mode)

    # The peer leg (OVERLAP — remove once every open branch postdates the claims cutover): an
    # id this branch holds that also lives on an open sibling PR and is NOT yet
    # on the trunk is a silent capture waiting to happen. The predicate is
    # `tree ∩ peer − tip`, not `− base`: the tip is the published claim set, and anything only on
    # a peer is a reservation this branch must not take. The merge base then splits the finding
    # in two (ENG-9321): an id absent at the base was MINTED by this branch's diff — renumber;
    # one already at the base was merely HELD — the branch mints nothing there, the tip's own
    # regeneration dropped the id, and the honest remedy is reconcile with the moved tip.
    peers_arg: list[str] | None = None
    # `is not None` so an explicit empty `--peers ''` disables the live path rather than falling
    # through to a listing.
    if peers is not None:
        peers_arg = [s for s in str(peers).split(",") if s.strip()]
    self_head = head_sha or _current_head_sha(root)
    peer_heads = list_open_peer_heads(
        root,
        explicit=peers_arg,
        self_sha=self_head,
        self_ref=_current_branch(root),
    )
    peer_notes: list[str] = []
    if peers_arg is None and not peer_heads:
        # The live path returned nothing reachable. Soft note only — offline commits and a quiet
        # board are both legitimate, and failing closed would block every push.
        peer_notes.append(
            "open-PR peer scan returned no reachable heads (no open PRs, gh unavailable, "
            "or peer SHAs not fetched) — sibling collisions against unpublished PRs are unchecked"
        )
    # A STACKED branch re-presents its parent's ids BY CONSTRUCTION: the parent minted them and
    # the child inherited them, so the id sits in the merge base of the two heads. That is ONE
    # allocation shared through the stack, not a capture, and reporting it as "minted by THIS
    # branch" false-positives on every commit an id-minting branch makes once it spawns a child
    # PR (ENG-13188). An id in the peer's merge base is shared ancestry; only an id ABSENT there
    # was minted independently on both sides and is a real collision. Every merge base is read,
    # not one: a criss-cross history (each side merged the other's pre-merge head) has several,
    # `git merge-base` returns one arbitrarily, and the shared allocation can sit in a base it
    # did not pick — the false positive this closes. The snapshot is cached by merge-base sha —
    # many peers stack on the same parent, so each base tree is read once.
    #
    # PERF (the open-PR scan): every peer and every stack base is read as a DELTA from the trunk
    # tip — the id-bearing files at the tip are read once (two git processes), then each ref costs
    # one `git diff-tree` restricted to the id paths plus one `cat-file --batch` for the blobs it
    # changed, applied in place to that one tree for the length of a read; a ref that changed no
    # id-bearing file reuses the tip's snapshot outright.
    # `git archive` per subtree per peer (56 peers x ~9 subtrees x 2 trees) did not finish in 15
    # minutes on a developer machine. Snapshots are cached per sha for the whole run.
    stack_base_cache: dict[str, Snapshot | None] = {}
    snap_cache: dict[str, Snapshot | None] = {}
    anchor_dir: Path | None = None
    anchor_snap: Snapshot | None = None
    if peer_heads:
        anchor_dir = materialize_batch(root, tip_sha, id_paths)
        if anchor_dir is not None:
            anchor_snap = collect(anchor_dir, knowledge_name, cfg, with_counters=False)

    def id_snapshot(sha: str) -> Snapshot | None:
        """The four id sets at `sha`; None when it cannot be read."""
        if sha in snap_cache:
            return snap_cache[sha]
        snap: Snapshot | None
        snap = None
        done = False
        if anchor_dir is not None and anchor_snap is not None:
            with delta_applied(root, sha, id_paths, tip_sha, anchor_dir) as changed:
                if changed is False:
                    snap, done = anchor_snap, True
                elif changed:
                    snap, done = collect(anchor_dir, knowledge_name, cfg, with_counters=False), True
        if not done:
            tree_dir = materialize(root, sha, id_paths)
            snap = collect(tree_dir, knowledge_name, cfg, with_counters=False) if tree_dir is not None else None
        snap_cache[sha] = snap
        return snap

    def stack_base_ids(peer: PeerHead) -> set[str]:
        shared: set[str] = set()
        for base in merge_bases(root, self_head, peer.sha):
            if base not in stack_base_cache:
                stack_base_cache[base] = id_snapshot(base)
            snap = stack_base_cache[base]
            if snap is not None:
                shared |= snap.registers | snap.capabilities | snap.prds | snap.migrations
        return shared

    # The peer leg reads one tree PER OPEN PR but only needs the four id sets, so it
    # materialises the id-bearing files alone and skips the whole-tree counter walk.
    for peer in peer_heads:
        peer_snap = id_snapshot(peer.sha)
        if peer_snap is None:
            peer_notes.append(f"open PR #{peer.number}: could not materialise {peer.sha[:12]}; skipped")
            continue
        # Lazy: the stack's merge bases are read only for a peer that actually shares an id with
        # this branch that the trunk does not hold — nearly none do, and each base is a tree read.
        shared_cache: list[set[str]] = []

        def shared_of(peer: PeerHead = peer, cache: list[set[str]] = shared_cache) -> set[str]:
            if not cache:
                cache.append(stack_base_ids(peer))
            return cache[0]

        for ids_h, ids_p, ids_t, ids_b, label, alloc_prefix in (
            (
                tree.registers,
                peer_snap.registers,
                tip_snap.registers,
                base_snap.registers,
                "requirement register",
                "REG",
            ),
            (
                tree.capabilities,
                peer_snap.capabilities,
                tip_snap.capabilities,
                base_snap.capabilities,
                "capability",
                "CAP",
            ),
            (tree.prds, peer_snap.prds, tip_snap.prds, base_snap.prds, "PRD number", "PRD"),
            (tree.migrations, peer_snap.migrations, tip_snap.migrations, base_snap.migrations, "migration version", ""),
        ):
            for cid in sorted(ids_h & ids_p - ids_t):
                if cid in ids_b:
                    # Held, not minted (ENG-9321): the id was already in this branch's base
                    # tree, so the diff mints nothing here and "renumber" points at nothing.
                    # The tree still disagrees with the moved tip, whose own regeneration
                    # dropped the id — and the merge must reconcile with it first.
                    report.findings.append(
                        finding(
                            ERROR,
                            f"{label} id `{cid}`: held by THIS branch (inherited from its base — "
                            "this branch's diff mints nothing here) AND on open PR "
                            f"#{peer.number} (`{peer.ref}`) while `origin/main`'s tip no longer "
                            "holds it — reconcile with the moved tip before push: rebase/merge "
                            "onto `origin/main` and take the regenerated ledger wholesale "
                            "(never hand-edit a generated file)",
                            hint=(
                                "Rebase/merge onto `origin/main`, take the regenerated ledger "
                                "wholesale (never hand-edit a generated file), and re-push; "
                                "nothing here needs renumbering."
                            ),
                            command=None,
                        )
                    )
                    continue
                if cid in shared_of():
                    # Shared through the stack's merge base (ENG-13188): the peer and this
                    # branch descend from the same allocation of `cid`, so there is no second
                    # mint to renumber. The trunk is the only authority on whether it landed.
                    continue
                report.findings.append(
                    finding(
                        ERROR,
                        f"{label} id `{cid}`: minted by THIS branch AND already on open PR "
                        f"#{peer.number} (`{peer.ref}`) — renumber this branch's id before push "
                        "(a captured id produces no merge conflict; the peer's identity wins silently)",
                        hint="Renumber this branch's id before the peer merges and takes the identity.",
                        command=cfg.command("allocate_ids", prefix=alloc_prefix or "RUN"),
                    )
                )

    new_regs = tree.registers - base_snap.registers
    for prefix, local_n in sorted(tree.counters.items()):
        tip_n = tip_snap.counters.get(prefix)
        if tip_n is None or local_n >= tip_n:
            continue
        minted = {cid for cid in new_regs if cid.startswith(prefix + "-")}
        if minted:
            report.notes.append(
                f"register `{prefix}`: this branch's `Next id:` counter ({prefix}-{local_n:03d}) "
                f"is behind `{cfg.default_diff_base}` ({prefix}-{tip_n:03d}) and this branch minted "
                f"{len(minted)} new id(s) from the stale counter — they may collide on merge"
            )
            report.findings.append(
                finding(
                    WARNING,
                    f"register `{prefix}`: this branch minted {len(minted)} id(s) from a counter that is "
                    f"behind the trunk's — they may collide on merge",
                    hint="Rebase, re-read the counter, then renumber what this branch minted below it.",
                    command=cfg.command("allocate_ids", prefix=prefix),
                )
            )
    report.notes.extend(peer_notes)
    report.notes.append(
        f"__summary__{len(tree.registers)}|{len(tree.capabilities)}|{len(tree.prds)}|"
        f"{len(tree.migrations)}|{tip_sha[:12]}|{len(peer_heads)}"
    )
    return report


class IdCollisionsCheck:
    """No id this branch minted is already claimed by the trunk or by an open peer PR."""

    name = NAME
    title = "Id collisions"
    description = (
        "Ids in an append-only register are permanent identities, and two branches can mint the same one "
        "without producing a single merge conflict — the counter line resolves cleanly and one branch's row "
        "silently inherits the other's identity. This check compares the ids THIS branch introduces against "
        "the trunk's TIP (not the merge base, which cannot see what the trunk minted after the branch "
        "diverged) and against every open peer PR head, across four contended ordinal spaces: requirement "
        "registers, capability ids, PRD numbers and migration versions. The comparison legs fail OPEN on "
        "every unresolvable input — no trunk, no merge base, no PR host — because a check that cannot see "
        "the comparison set must never report the whole register as colliding. The claim leg does not need "
        "that set: it still runs when the comparison is skipped, and fails CLOSED on an id with no claim ref."
    )

    def applies(self, kb: Any) -> bool:
        return is_repository(Path(kb.root))

    def run(self, kb: Any) -> list[Any]:
        # `head` and `tip` are taken from the caller when it has them, and this is the check
        # that most needs them. A CI working tree is built from the MERGE ref, which has already
        # absorbed the trunk: inferred from it, `tree` contains everything `tip` contains and the
        # merge base is the trunk itself, so `tree & tip - base` is empty by construction and the
        # check reports a clean pass over a corpus it never compared. Silent, not red — which is
        # exactly the failure this check exists to prevent, turned on itself.
        ctx = git_context(kb)
        report = analyse(kb, tip=ctx.tip or None, head=ctx.head or None)
        findings = list(report.findings)
        if report.refusal:
            # The runner protocol carries findings only, so a refusal dropped here is silent:
            # `fleet check` then reports a clean pass over a comparison it never made. Say it —
            # as a warning, because the collision leg stays fail-open on an unresolvable input.
            # The claim leg ran regardless and its unverified ids are gating errors above.
            findings.insert(0, finding(WARNING, report.refusal))
        return findings


CHECK = IdCollisionsCheck()


def cli_check(kb: Any, *, tip: str | None, head: str | None, peers: str | None) -> int:
    """Reproduce `scripts/validate_id_collisions.py`'s check-mode stdout and exit code.

    A refusal used to return 0 before the claim leg's errors were even read, so a shallow
    checkout passed an unclaimed id it had never compared (ENG-21060). The refusal is printed,
    and any error still gates.
    """
    report = analyse(kb, tip=tip, head=head, peers=peers)
    if report.refusal:
        print(report.refusal)
    summary = ""
    for note in report.notes:
        if note.startswith("__summary__"):
            summary = note[len("__summary__") :]
            continue
        print(f"id-collision note — {note}")
    errors = report.errors
    if errors:
        # The header names no remedy on purpose (ENG-9321): the remedy depends on WHY the id
        # collided — renumber a mint, reconcile with the tip a hold — and each finding below
        # carries its own.
        print("id-collision check FAILED — resolve the id conflicts below before push:")
        for e in errors:
            print(f"- {e.message}")
        return 1
    if report.refusal:
        return 0
    n_regs, n_caps, n_prds, n_migs, tip_short, n_peers = summary.split("|")
    print(
        f"id-collision check OK — {n_regs} register id(s), {n_caps} capability "
        f"id(s), {n_prds} PRD number(s), {n_migs} migration version(s); "
        f"compared against {tip_short} + {n_peers} open peer PR(s)"
    )
    return 0


def cli_allocate(
    kb: Any,
    *,
    prefix: str,
    count_raw: str,
    tip: str | None,
    peers: str | None,
    claims: ClaimStore | None = None,
) -> int:
    """`--allocate PREFIX N`: reserve the next N free ids and print them.

    Exit 0 with the ids, 2 on bad input, 3 when claims are configured but GitHub cannot be
    reached — an unreserved id is exactly what the claim gate exists to refuse, so it is never
    printed as if it were one.

    Progress goes to STDERR, line by line and flushed, so a run that is slow (or wedged on the
    network) is visible while it is running instead of silent until it exits (ENG-13806).
    """
    import sys  # noqa: PLC0415 - the only stderr write in this package

    def progress(message: str) -> None:
        print(f"id-allocate: {message}", file=sys.stderr, flush=True)

    cfg = PlanningConfig.of(kb)
    root = Path(kb.root)
    prefix = prefix.upper()
    try:
        count = int(count_raw)
    except (TypeError, ValueError):
        print(f"id-allocate — count must be an integer, got {count_raw!r}", file=sys.stderr)
        return 2
    peers_arg: list[str] | None = None
    if peers is not None:
        peers_arg = [s for s in str(peers).split(",") if s.strip()]
    claimed = claims is not None or cfg.id_claims
    # ENG-13595: with claims configured the peer heads are unnecessary — the claim refs are the
    # reservation set — so `--allocate` does not even list them. Listing them was itself ~4 s on
    # a 42-PR board, and the per-peer materialise + collect that followed was the >5 min.
    peer_heads = [] if claimed else list_open_peer_heads(root, explicit=peers_arg)
    try:
        ids, _next_free, sources = allocate(
            kb, prefix=prefix, count=count, tip=tip, peers=peer_heads, claims=claims, progress=progress
        )
    except ValueError as e:
        print(f"id-allocate — {e}", file=sys.stderr)
        return 2
    except ClaimsUnavailableError as e:
        print(
            f"id-allocate — could not reserve {prefix} ids on GitHub: {e}\n"
            "  Allocation reserves each id as a claim ref and needs the network. Offline, write a "
            "placeholder and run this before you push; CI refuses an id with no claim.",
            file=sys.stderr,
        )
        return 3
    print(f"id-allocate {prefix} × {count}")
    print(f"  claim: {', '.join(ids)}")
    if claimed:
        print(f"  reserved on GitHub as {', '.join(cfg.id_claim_namespace + claim_name(prefix, i) for i in ids)}")
    if sources:
        print("  floor raised by:")
        for s in sources:
            print(f"    - {s}")
    else:
        print("  floor: empty (no prior ids found)")
    if prefix == "PRD":
        prd_dir = f"{Path(kb.knowledge).name}/{cfg.prds_dir}"
        print(
            f"  PRD numbers are bare four-digit ids (frontmatter `prd: {ids[0]}` at {prd_dir}/{ids[0]}-<slug>/prd.md)."
        )
    if claimed:
        print(
            "  The claim refs ARE the reservation: write each id into its row — there is no counter to "
            "bump and no shared line to edit. An id you drop stays a gap, which is free."
        )
    else:
        print(
            "  UNRESERVED: this corpus configures no id claims (`[fleet.planning] id_claims`), so this is "
            "a snapshot two concurrent allocations can race. Open the PR promptly and re-run the check "
            "after every rebase."
        )
    # Print the ids LAST (ENG-13595): the explanatory footer used to sit below them, so
    # `--allocate SL 1 | tail -3` dropped the one line the author came for. The ids are the
    # output; a copy on the final stdout line survives any tail.
    print(f"id-allocate {prefix} {count}: {', '.join(ids)}")
    return 0


def cli_claim(kb: Any, *, ids: Sequence[str], tip: str | None, claims: ClaimStore | None = None) -> int:
    """`--claim ID...`: reserve ids already written into a change (offline authoring, or a branch
    that allocated before claims existed).

    A 422 is reported, not failed: the ref may be this author's own earlier claim, and a real
    capture is still caught by the tip and peer legs. Exit 3 when GitHub cannot be reached.
    """
    import sys  # noqa: PLC0415 - the only stderr write in this package

    cfg = PlanningConfig.of(kb)
    owned = owned_prefixes(cfg.corpora)
    for raw in ids:
        cid = raw.strip().upper()
        if owner := owned.get(cid.split("-", 1)[0]):
            print(f"id-claim — `{cid}`: {_owned_refusal(cid.split('-', 1)[0], owner)}", file=sys.stderr)
            return 2
    root = Path(kb.root)
    store = claims if claims is not None else claim_store(kb)
    target = resolve_tip(root, tip, cfg.default_diff_base) or ""
    if not target:
        print(f"id-claim — no `{cfg.default_diff_base}` to point the claims at; fetch it first", file=sys.stderr)
        return 3
    for raw in ids:
        cid = raw.strip().upper()
        name = claim_name("PRD", cid) if re.fullmatch(r"\d{4}", cid) else cid
        try:
            created = store.claim(name, target)
        except ClaimsUnavailableError as e:
            print(f"id-claim — {name}: could not reach GitHub: {e}", file=sys.stderr)
            return 3
        if created:
            print(f"id-claim {name}: claimed ({cfg.id_claim_namespace}{name})")
        else:
            print(
                f"id-claim {name}: ALREADY CLAIMED — if it was not you, another branch holds this id: "
                "allocate a fresh one and renumber"
            )
    return 0


def cli_claim_existing(kb: Any, *, tip: str | None, peers: str | None, claims: ClaimStore | None = None) -> int:
    """`--claim-existing`: back-fill a claim for every id the trunk tip (and every open peer PR)
    already holds. Idempotent — an id already claimed is skipped.

    Run once when a corpus turns claims on, so the allocator's floor sees the whole id space
    through the claim namespace and the open PRs minted by the old allocator stay green. Every
    claim — tip-held or peer-only — points at the trunk tip. The tip is already on origin, so
    the push carries no new commits and pre-push hooks are a no-op; pointing a peer-held id at
    that peer's head would push the peer commit and run validators against the peer tree
    (ENG-13191).
    """
    import sys  # noqa: PLC0415 - the only stderr write in this package

    cfg = PlanningConfig.of(kb)
    root = Path(kb.root)
    knowledge_name = Path(kb.knowledge).name
    id_paths = id_archive_paths(kb)
    tip_sha = resolve_tip(root, tip, cfg.default_diff_base)
    tip_root = materialize(root, tip_sha, id_paths) if tip_sha else None
    if not tip_sha or tip_root is None:
        print(f"id-claim-existing — could not read `{cfg.default_diff_base}`; nothing claimed", file=sys.stderr)
        return 3
    targets = dict.fromkeys(claimable_ids(collect(tip_root, knowledge_name, cfg, with_counters=False)), tip_sha)
    on_tip = len(targets)
    peers_arg: list[str] | None = None
    if peers is not None:
        peers_arg = [s for s in str(peers).split(",") if s.strip()]
    for peer in list_open_peer_heads(root, explicit=peers_arg, self_ref=""):
        peer_root = materialize(root, peer.sha, id_paths)
        if peer_root is None:
            continue
        for cid in claimable_ids(collect(peer_root, knowledge_name, cfg, with_counters=False)):
            targets.setdefault(cid, tip_sha)
    store = claims if claims is not None else claim_store(kb)
    try:
        held = store.claimed()
        created = store.claim_many({c: s for c, s in targets.items() if c not in held})
    except ClaimsUnavailableError as e:
        print(f"id-claim-existing — could not reach GitHub: {e}", file=sys.stderr)
        return 3
    print(
        f"id-claim-existing — {len(targets)} id(s) held ({on_tip} on {tip_sha[:12]}, "
        f"{len(targets) - on_tip} on open PRs only); {len(set(targets) & held)} already claimed; "
        f"{created} claim(s) created"
    )
    return 0
