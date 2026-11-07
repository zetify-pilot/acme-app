"""The statement guard: a permanent id must guarantee the MEANING, not just the string.

The register validator parses `Statement` into its row dict and never reads it again. So
the id contract it enforces — *permanent, never reused* — protects the number and nothing
else: `RUN-441` can be silently redefined and every citation in the corpus follows the new
text without a word. Worse, an over-broad invariant can be quietly "narrowed" in place
instead of superseded, which leaves no trace, no successor row, and nothing to count when
someone asks what we walked back.

This closes that, **statelessly**: the registers at the comparison BASE are re-parsed and
every row that existed there is compared with the working tree.

  - unchanged .......... fine.
  - APPENDED to ........ fine, and this is the common case. The corpus corrects by
                         addition — `~~struck~~ **Correction:** …`, `**Deferred to v2**
                         — …` — which is exactly the append-only convention decisions
                         already follow. The old text remaining a PREFIX of the new is
                         the mechanical test for "annotated, not rewritten", and it
                         beats enumerating correction markers: 25 different bold phrases
                         appear inside statements today, most of them ordinary emphasis.
  - REWRITTEN .......... allowed only if the same change either (a) MINTS A NEW ID and
                         points this row at it (`superseded by RUN-NNN`, where that id
                         did not exist at the base) — the supersession the register
                         demands — or (b) touches a row NO PRD CLAIMS, where nothing
                         downstream has been told the old meaning yet.
  - DELETED ............ never allowed. Ids are permanent and never reused, so a row is
                         superseded or rejected in place, never removed.
  - REBOUND ............ never allowed, and it is the ID cell that moved, not the
                         statement: a base row's words now sit under a DIFFERENT id
                         while its own id carries something else (or is gone). ENG-7933 —
                         PRD 0503 allocated `RUN-972..979` in a worktree, `main` meanwhile
                         held `RUN-972..1016` with `RUN-972..982` owned by PRD 0478, and
                         the renumber that resolved it ran `re.sub` over the WHOLE register
                         file, so it renamed 0478's rows too. Afterwards there are no
                         duplicates, every reference resolves, the `APPEND ONLY. Next id:`
                         counter is consistent and the register validator says OK —
                         both of that script's nets against concurrent allocation are blind
                         to it, because neither ever asks whether an id still means what it
                         meant. Renumbering rows YOUR branch added is the normal, expected
                         resolution and stays legal: their statements are not at the base,
                         so this verdict cannot reach them.

**Why there is no lock file any more (ENG-12971, 2026-09-28).** This guard used to keep a
committed `requirements/.statements.lock` — one hash per statement — and a "leg 1" that
compared the tree against it. That file was derived from the registers, so every PR that
touched any register rewrote it, and two unrelated PRs collided on it by construction (243
touches on `main` in 30 days; a conflict in 5 of 11 conflicting open PRs). Everything the
lock proved, the base comparison proves without it: a changed statement is a diff against
the base, a new row is simply absent from the base, and a deleted row is a base id missing
from the tree. The lock's only unique contribution was a comparison that ran with NO git —
and a redefinition guard with nothing to compare against is not a guard.

**Fail closed.** The comparison base is the caller's (`--base <sha>`: in CI the pull
request's or merge group's base commit), or else the merge base of `HEAD` with `base_ref`.
When neither resolves to a commit present in the repository, the guard FAILS rather than
passing on a comparison it never made — a skipped gate that reads green is strictly worse
than a red one.

Normalisation is deliberate and narrow: inline emphasis (`**`, `*`, `` ` ``) and
strikethrough (`~~`) are stripped, and whitespace is collapsed. Striking a statement
through is what supersession DOES to a row, so it must not read as a redefinition; bolding
a word is typography, and failing a commit over it would be the guard crying wolf. Words
are what is guarded.

Stdlib only. Exit 1 on any violation.
"""

from __future__ import annotations

import argparse
import io
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from ... import corpusref
from ... import requirements as kkreq
from . import registers as vr
from .context import Context

EMPHASIS_RE = re.compile(r"[*~`]+")
WS_RE = re.compile(r"\s+")

#: Capability marker (ENG-12971). True once this module guards statements against the base
#: alone and reads no lock file. A consuming repository may probe for it before it deletes
#: its committed lock, so the two halves of the coupled change cannot leave a broken window.
STATELESS_STATEMENT_GUARD = True

RowMap = dict[str, dict[str, Any]]


def normalise(statement: str) -> str:
    """The words of a statement, with typography and strike-through removed."""
    return WS_RE.sub(" ", EMPHASIS_RE.sub("", statement)).strip()


def load_tree_rows(ctx: Context) -> RowMap:
    """The registers as the working tree has them.

    Read through the register loader rather than parsing the markdown a second way here:
    two parsers that disagree about what a row IS would make this guard's verdict depend
    on which one saw the file.
    """
    ctx.reset()
    rows: RowMap = vr.load_registers(ctx)
    return rows


def git(ctx: Context, *args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=ctx.root, text=True, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, OSError):
        return None


def git_bytes(ctx: Context, *args: str) -> bytes | None:
    """`git`, for a subcommand whose output is binary — the raw `archive` tar stream."""
    try:
        return subprocess.check_output(["git", *args], cwd=ctx.root, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, OSError):
        return None


def resolve_base(ctx: Context, explicit: str | None) -> str | None:
    """The commit the working tree is compared against, or None when there is none.

    The merge base with the base ref rather than `HEAD`, so a redefinition committed
    EARLIER on the same branch is still caught — the guard should keep firing until the
    branch stops carrying an unsanctioned rewrite, not go quiet after one more commit.

    An explicit base that does not name a commit present in this repository resolves to
    None, and so does an unresolvable merge base: the caller fails closed on it.
    """
    if explicit:
        out = git(ctx, "rev-parse", "--verify", "--quiet", f"{explicit}^{{commit}}")
        return out.strip() if out else None
    if out := git(ctx, "merge-base", "HEAD", ctx.cfg.base_ref):
        return out.strip()
    return None


#: A fragment-backed register's committed shell. The generated `<domain>.md` (frontmatter plus
#: the rendered table body) is gitignored and never committed (ENG-12980 / FLT-045), so at a
#: git ref the shell is the only place its frontmatter, source legend, section headings and
#: `<!-- rows: … -->` markers exist.
SHELL_SUFFIX = ".md.tmpl"


def _materialise_name(rel: str) -> str | None:
    """Where a base-ref file lands in the temp tree, or None when the loader cannot read it.

    The register loader reads a register by `<domain>.md` and its rows by `rows/*.json`. At a
    git ref a fragment-backed register has no `<domain>.md` — it is gitignored and rendered on
    demand — but its committed shell, `<domain>.md.tmpl`, carries everything the loader reads
    for that domain. So the shell is materialised UNDER the `.md` name, and the committed
    `rows/*.json` fragments come through as themselves. Anything else (images, generated
    sources) is dead weight this guard never reads.
    """
    if rel.endswith(SHELL_SUFFIX):
        return rel[: -len(".tmpl")]
    if rel.endswith(".md") or rel.endswith(".json"):
        return rel
    return None


def rows_at(ctx: Context, ref: str) -> RowMap | None:
    """Re-parse the registers as they were at `ref`.

    The register files are materialised into a temp tree and handed to the SAME loader the
    working tree goes through, rather than parsing the markdown a second way here. Two
    parsers that disagree about what a row is would make this guard's verdict depend on
    which one saw the file.

    **The material is the whole register, not just the committed `.md`.** Since ENG-12980 a
    fragment-backed corpus keeps each row in `requirements/rows/<ID>.json` and commits its
    shell as `<domain>.md.tmpl`; the generated `<domain>.md` is gitignored and rendered on
    demand. So a base ref holds almost no `.md` at all, and materialising only `.md` compared
    every row-backed register against an almost-empty base — the rewrite, narrowing and
    deletion the guard exists to catch went unseen (ENG-20115). `_materialise_name` maps the
    shell under its `.md` name and carries the fragments through unchanged, so the base is read
    exactly like the working tree.

    **One git process, not one per row (ENG-20358).** This used to list the base with
    `ls-tree` and then run `git show` once for every fragment — ~3,000 spawns over the
    corpus — so a loaded CI runner multiplied each spawn into the sweep's wall time until
    the `Knowledge Corpus` job crossed its ceiling and ejected green PRs. A single
    `git archive` pass streams the same blobs in one process, so the cost stays flat as the
    corpus grows instead of scaling with the row count.
    """
    register_dir = f"{ctx.knowledge_prefix}{ctx.cfg.requirements_dir}"
    archive = git_bytes(ctx, "archive", "--format=tar", ref, "--", register_dir)
    if archive is None:
        # A pathspec that matches nothing is not an error condition for this guard: treat it
        # as a register set with no files, as the `ls-tree` read did. Files that DO exist but
        # could not be archived are a base we cannot trust, so still fail closed.
        listing = git(ctx, "ls-tree", "-r", "--name-only", ref, "--", register_dir)
        if listing is None or listing.strip():
            return None
        archive = b""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / register_dir).mkdir(parents=True)
        if archive:
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
                for member in tar:
                    if not member.isfile():
                        continue
                    dest = _materialise_name(member.name)
                    if dest is None:
                        continue
                    handle = tar.extractfile(member)
                    if handle is None:
                        return None  # a listed blob that cannot be read is a base we cannot trust
                    path = root / dest
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(handle.read())
        # A SECOND context rather than a rebind of this one: two knowledge bases in one
        # run is exactly what the global-rebinding original could not express.
        at_ref = Context(
            root=root, knowledge=root / (ctx.knowledge_prefix.rstrip("/") or "."), cfg=ctx.cfg, corpora=ctx.corpora
        )
        rows: RowMap = vr.load_registers(at_ref)
        return rows


def claimed_ids(ctx: Context) -> set[str]:
    """Requirement ids some PRD's `implements:` points at — claimed meanings."""
    out: set[str] = set()
    base = ctx.prd_dir
    if not base.is_dir():
        return out
    for d in sorted(base.iterdir()):
        f = d / ctx.cfg.prd_file
        if not (d.is_dir() and f.is_file()):
            continue
        fm = vr.frontmatter(f.read_text(encoding="utf-8"))
        if fm:
            out.update(vr.claim_ids(ctx, fm))
    return out


def by_statement(rows: RowMap) -> dict[str, set[str]]:
    """{normalised statement: the ids carrying it} — the index the rebind check reads
    backwards. A set, not an id: nothing forbids two rows from wording a commitment
    identically, and a pre-existing pair like that must not read as a rebind."""
    out: dict[str, set[str]] = {}
    for rid, row in rows.items():
        out.setdefault(normalise(row["statement"]), set()).add(rid)
    return out


def check_redefinitions(tree: RowMap, base: RowMap, claimed: set[str]) -> tuple[list[str], list[str]]:
    """Was every change to a base row allowed? Returns (errors, notes).

    Two questions off one comparison. The first is "did this ID's statement change?" and its
    verdicts are unchanged / appended / rewritten / deleted. The second (ENG-7933) is the same
    rows read backwards — "did this STATEMENT's id change?" — and it has one verdict, rebound,
    because an id that existed at the base has no legitimate reason to move.
    """
    errs: list[str] = []
    # Aggregated, not one line per row: a healthy edit to this corpus touches dozens of
    # statements by appending a correction, and 40 lines of "this was fine" is how a real
    # finding gets scrolled past.
    allowed: dict[str, list[str]] = {}
    base_ids_of, tree_ids_of = by_statement(base), by_statement(tree)
    for rid, old in sorted(base.items()):
        new = tree.get(rid)
        before = normalise(old["statement"])
        after = normalise(new["statement"]) if new is not None else None
        # The meaning still sits on its own number (verbatim, or annotated in place) — the
        # id was not rebound, whatever else this goes on to say about the text.
        if after is None or not (after == before or after.startswith(before)):
            # `- base_ids_of[before]` is what keeps a pre-existing duplicate statement from
            # reading as a rebind: only an id that did NOT carry these words at the base
            # counts as somewhere they MOVED to.
            moved = sorted(tree_ids_of.get(before, set()) - base_ids_of.get(before, set()))
            if moved:
                errs.append(
                    f"{rid}: its ID cell was REWRITTEN — the statement this id carried at the base "
                    f"now sits under {', '.join(moved)}, and {rid} "
                    f"{'is gone' if after is None else 'carries different words'}. A renumber may "
                    "only move rows YOUR branch added; rewriting the id of a row that existed at "
                    "the base hands that permanent number to another meaning, and leaves no "
                    "duplicate, no dangling reference and no counter drift behind for "
                    "`validate_requirements.py` to trip on. Renumber your own rows only — and if a "
                    "meaning must move, mint a new row and supersede this one into it."
                    f"\n      {rid} was: {before[:160]}"
                    f"\n      {rid} now: {'(no row carries this id)' if after is None else after[:160]}"
                )
                continue
        if new is None or after is None:
            errs.append(
                f"{rid}: present at the base, but no longer present in any register — ids are "
                "PERMANENT and never reused, so a row is superseded or rejected in place, never deleted"
            )
            continue
        if before == after:
            continue
        if after.startswith(before):
            allowed.setdefault("appended to (a correction, not a rewrite)", []).append(rid)
            continue
        successor = new["superseded_by"]
        if successor and successor not in base:
            allowed.setdefault("rewritten while superseding into a newly minted id", []).append(rid)
            continue
        if rid not in claimed:
            allowed.setdefault("rewritten while unclaimed by any PRD", []).append(rid)
            continue
        errs.append(
            f"{rid}: its statement was REWRITTEN, not appended to, while a PRD claims it. A "
            "permanent id has to guarantee the meaning, or every citation silently follows the new "
            "text. Mint a new row and set this one `superseded by <new id>`, or — if the wording "
            "genuinely never carried the old meaning — say so in the commit and drop the claim first."
            f"\n      was: {before[:160]}"
            f"\n      now: {after[:160]}"
        )
    notes = [
        f"{len(ids)} statement(s) {why}: {', '.join(ids[:8])}{' …' if len(ids) > 8 else ''}"
        for why, ids in sorted(allowed.items())
    ]
    return errs, notes


def no_base_error(ctx: Context, explicit: str | None) -> str:
    """The fail-closed refusal: no comparison was made, so no pass may be reported."""
    if explicit:
        return (
            f"comparison base `{explicit}` is not a commit in this repository — the statement guard "
            "cannot classify any change without it and refuses to pass unchecked. Fetch the base "
            "(CI: check out with full history) and re-run"
        )
    return (
        f"no comparison base: `git merge-base HEAD {ctx.cfg.base_ref}` did not resolve — the "
        "statement guard cannot classify any change without it and refuses to pass unchecked. "
        f"Fetch `{ctx.cfg.base_ref}` or pass `--base <commit>`, and re-run"
    )


def _check(ctx: Context, args: argparse.Namespace) -> tuple[RowMap, list[str], list[str], str | None, RowMap | None]:
    """Compare the working tree's registers against the base.

    Returns (rows, errors, notes, base_ref, base_rows). `base_rows` is None only when the
    base could not be read — and then `errors` says so: this guard never reports a pass it
    did not compute.
    """
    rows = load_tree_rows(ctx)
    explicit = getattr(args, "base", None)
    base_ref = resolve_base(ctx, explicit)
    if base_ref is None:
        return rows, [no_base_error(ctx, explicit)], [], None, None
    base_rows = rows_at(ctx, base_ref)
    if base_rows is None:
        return rows, [no_base_error(ctx, base_ref)], [], base_ref, None
    compared, claimed, moved_notes = with_moved_rows(ctx, rows, base_rows, claimed_ids(ctx))
    errors, notes = check_redefinitions(compared, base_rows, claimed)
    return rows, errors, [*notes, *moved_notes], base_ref, base_rows


def with_moved_rows(ctx: Context, tree: RowMap, base: RowMap, claimed: set[str]) -> tuple[RowMap, set[str], list[str]]:
    """The tree to compare against, with every row that MOVED to a sibling corpus filled in.

    A base row whose prefix a declared sibling OWNS (`[fleet.planning.corpora] fleet =
    { prefixes = ["FLT"] }`) and that is gone from this tree was moved, not deleted: its id and
    meaning live on in the sibling's register. So it is compared against the sibling's row of
    the same id — read from the sibling's committed shell and row fragments, never a rendered
    table — and a moved row rewritten on the way, or one the sibling does not hold, is still
    caught. A sibling not on disk cannot be compared: those rows are named in a note, never
    passed silently and never failed as deletions. Returns `(tree, claimed, notes)`: the claim
    set also keyed by the bare id of a claim on a moved row (`fleet:FLT-104` -> `FLT-104`), and
    joined by the sibling's OWN claims, so a moved row claimed only there keeps its protection.
    """
    corpora = ctx.corpora
    gone = sorted(rid for rid in base if rid not in tree and corpora.owner_of(rid))
    if not gone:
        return tree, claimed, []
    out = dict(tree)
    keyed = set(claimed)
    unverified: dict[str, list[str]] = {}
    sibling_rows: dict[str, RowMap] = {}
    for rid in gone:
        name = str(corpora.owner_of(rid))
        knowledge = corpora.path_of(name)
        if knowledge is None:
            unverified.setdefault(name, []).append(rid)
            continue
        if name not in sibling_rows:
            rows, _findings = kkreq.load_registers(
                knowledge,
                reserved_prefixes=frozenset(ctx.cfg.reserved_prefixes),
                dir_name=ctx.cfg.requirements_dir,
                own=corpusref.own_corpus(knowledge),
                shells=True,
            )
            sibling_rows[name] = rows
            # The claims that protect a moved row's meaning may live in the sibling now: a PRD
            # THERE implementing it makes a rewrite as refusable as a claim here would.
            sibling_own = corpusref.own_corpus(knowledge)
            keyed |= claimed_ids(
                Context(
                    root=knowledge.parent,
                    knowledge=knowledge,
                    cfg=ctx.cfg,
                    corpora=corpusref.Corpora(own=sibling_own, root=knowledge.parent),
                )
            )
        if (row := sibling_rows[name].get(rid)) is not None:
            out[rid] = row
    for cid in claimed:
        ref = corpusref.parse_ref(cid)
        if ref.corpus is not None and corpora.owner_of(ref.id) == ref.corpus:
            keyed.add(ref.id)
    notes = [
        f"{len(ids)} row(s) moved to corpus `{name}` (it owns their prefix) could not be compared — "
        f"`{name}` is declared but not on disk here: {', '.join(ids[:8])}{' …' if len(ids) > 8 else ''}"
        for name, ids in sorted(unverified.items())
    ]
    for ids in unverified.values():
        for rid in ids:
            out[rid] = base[rid]  # nothing to compare against: neither a deletion nor a pass
    return out, keyed, notes


def main(ctx: Context, argv: list[str] | None = None, doc: str | None = None) -> int:
    p = argparse.ArgumentParser(prog="validate_requirement_statements", description=doc or __doc__)
    p.add_argument(
        "--base",
        help=f"commit to compare statements against (default: merge-base of HEAD with {ctx.cfg.base_ref}); "
        "an unresolvable base FAILS the guard",
    )
    args = p.parse_args(argv)

    rows, errors, notes, base_ref, _base_rows = _check(ctx, args)
    if notes:
        print(f"statement guard — {len(notes)} note(s):")
        for n in notes:
            print(f"- {n}")
    if errors:
        print("requirement statement guard FAILED:")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"statement guard OK — {len(rows)} statement(s); compared against {(base_ref or '')[:12]}")
    return 0
