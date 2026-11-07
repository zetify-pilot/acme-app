"""Exhaustive commitment coverage: prose that can carry a *"the system shall / never"*
must be claimed by some requirement register's `source_of_truth:`.

**The hole this closes (TODO-024).** The rule is *"prose may not assert a commitment — it
cites one"*, and a register declares which prose it is the constraint axis for via
frontmatter `source_of_truth:`. Nothing checked that the declaration was EXHAUSTIVE over
the corpus that carries commitments. Migrating the architecture chain surfaced ~50 real
*shall/never* rules asserted only in prose or in a Go comment, with no register row and
nothing anywhere that noticed — because a spec is only measured against a register once
someone remembers to point a register at it. At the time this landed, **4 of 109 specs and
10 of 120 decision records** were claimed by any register.

**This is the journey validator's ENG-5947 mechanism, applied to prose instead of code** —
deliberately the same shape, not a second invention. Every in-scope document must be

  1. claimed by some register's `source_of_truth:` (exact path, or any prefix directory
     of it), or
  2. excluded by TYPE policy (a reviewed carve-out, never a silent allowance), or
  3. named in the unclaimed baseline — acknowledged debt, which **may shrink, never grow**.

A document in none of the three fails the commit: it is new prose that nobody has decided
is commitment-bearing or not, which is exactly the state that produced TODO-024.

**THE EXCLUSION POLICY, AND HOW IT WAS DERIVED.** Not every document under a spec root
asserts anything, and demanding a register claim on prose that commits to nothing would
make the gate meaningless. The corpus was read by shape rather than file-by-file, using
the type system's own enforced `type:` vocabulary — so the carve-out is a property of a
document KIND, not a list somebody has to maintain. The five excluded types, and the
reason each is excluded, live in `options.DEFAULT_EXCLUDED_TYPES`; the reason is REQUIRED
there for the same purpose it was required here — the map can only ever narrow what is
checked, and only with the reasoning attached.

Everything else stays IN SCOPE and is measured — `spec` (44), `component-detail` (31),
`arch-doc` (5), `arch-reference` (7), `decision` (116). That is **205 of 229 documents,
~90% of the corpus**, so the gate is not vacuous. Two calls inside that are worth stating
because they are the ones a reader will question:

  - **Process specs stay in scope.** They do assert *shall/never* rules — about our
    process rather than the product. Whether that domain gets a register is an open
    question (cf. TODO-025, two product domains with commitments and no register at all),
    and pre-excluding them would answer it silently. The baseline is the right home for an
    unanswered question; the exclusion list is not.
  - **An excluded type may still be CITED as a `Source`.** `GOV-013`'s source is a phrase
    in an audit checklist. Exclusion means the document does not DEMAND a claim, never
    that a register may not point at it.

A doc with no `type:` at all is treated as in scope — fail-safe, the more-things-flagged
direction.

**Leg 2: a claim must resolve.** A `source_of_truth:` entry naming a path that does not
exist claims nothing while looking like coverage — the same class of rot that turned 72
line-anchors into noise in one 19-line insertion. Every declared path must exist on disk.

Ported from `scripts/validate_commitment_coverage.py` unchanged. The coverage roots, the
baseline's location and the excluded types are configuration whose defaults are that
file's values.

Stdlib only. Exit 1 on any violation.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .context import Context

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
TYPE_RE = re.compile(r"^type:\s*([A-Za-z0-9_-]+)\s*$", re.M)
# `source_of_truth:` as a block list (the shape every register uses today) or inline
# `[a, b]` — both accepted, so a register that switches form is not silently unread.
SOT_BLOCK_RE = re.compile(r"^source_of_truth:\s*$((?:\n[ \t]+-[ \t]+\S.*)*)", re.M)
SOT_INLINE_RE = re.compile(r"^source_of_truth:\s*\[([^\]]*)\]\s*$", re.M)
SOT_ITEM_RE = re.compile(r"^[ \t]+-[ \t]+(.*\S)[ \t]*$", re.M)
ACK_RE = re.compile(r"\s*#\s*ack:\s*(\S+)")


def err(ctx: Context, where: str, msg: str) -> None:
    ctx.errors.append(f"{where}: {msg}")


def frontmatter(text: str) -> str | None:
    m = FRONTMATTER_RE.match(text)
    return m.group(1) if m else None


def doc_type(path: Path) -> str | None:
    """The document's declared `type:`, or None when it has no frontmatter/type at all
    (in-scope by fail-safe — the type validator owns making that impossible)."""
    try:
        fm = frontmatter(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    if fm is None:
        return None
    m = TYPE_RE.search(fm)
    return m.group(1) if m else None


def source_of_truth(fm: str) -> list[str]:
    """The `source_of_truth:` entries of one frontmatter block, block or inline form."""
    m = SOT_BLOCK_RE.search(fm)
    if m and m.group(1).strip():
        return [i.strip().strip("\"'") for i in SOT_ITEM_RE.findall(m.group(1))]
    m = SOT_INLINE_RE.search(fm)
    if m:
        return [i.strip().strip("\"'") for i in m.group(1).split(",") if i.strip()]
    return []


def registers(ctx: Context) -> list[Path]:
    """Every requirement register — derived from disk, never a hand list."""
    return ctx.registers()


def baseline_rel(ctx: Context) -> str:
    """The baseline's repo-relative path — how it names itself in every message."""
    return ctx.rel(ctx.unclaimed_baseline_path)


def coverage_roots(ctx: Context) -> tuple[str, ...]:
    """The repo-relative roots of the prose corpus that can carry a commitment.

    Deliberately narrow: specs and decisions are the two places a *"the system shall"* is
    authored as a durable rule. A PRD, a retro or an audit finding is versioned work
    product, not a standing commitment.
    """
    prefix = ctx.knowledge_prefix
    return tuple(f"{prefix}{root.lstrip('/')}" for root in ctx.cfg.coverage_roots)


def claimed_paths(ctx: Context) -> set[str]:
    """Every path any register declares as its `source_of_truth:`, trailing slash
    normalised away so a directory claim and a file claim compare the same way."""
    out: set[str] = set()
    for reg in registers(ctx):
        fm = frontmatter(reg.read_text(encoding="utf-8"))
        if fm is None:
            continue
        out |= {s.rstrip("/") for s in source_of_truth(fm)}
    return out


def is_claimed(rel: str, claimed: set[str]) -> bool:
    """A doc is claimed by an exact match or by any directory prefix of it."""
    return any(rel == c or rel.startswith(c + "/") for c in claimed)


def tracked_paths(ctx: Context) -> set[str] | None:
    """Repo-relative git-tracked + untracked-but-not-ignored files, or None when the root
    is not a git working tree (the self-tests build bare temp trees)."""
    try:
        r = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ctx.root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return None
    return {line for line in r.stdout.splitlines() if line}


def covered_docs(ctx: Context) -> list[str]:
    """Every markdown document under the coverage roots. Gitignored paths are never
    treated as corpus (ENG-6005's reasoning): a generated ledger dropped under a covered
    root is not prose anyone authored a commitment into."""
    tracked = tracked_paths(ctx)
    out: list[str] = []
    for root in coverage_roots(ctx):
        if tracked is not None:
            out.extend(rel for rel in tracked if rel.startswith(root) and rel.endswith(".md"))
            continue
        base = ctx.root / root.rstrip("/")
        if not base.is_dir():
            continue
        out.extend(str(p.relative_to(ctx.root)) for p in base.rglob("*.md"))
    return sorted(out)


def excluded(ctx: Context, rel: str) -> str | None:
    """The carve-out reason when this doc's `type:` is excluded by policy, else None."""
    t = doc_type(ctx.root / rel)
    return ctx.cfg.excluded_type_reasons.get(t) if t else None


def read_baseline(ctx: Context) -> set[str]:
    p = ctx.unclaimed_baseline_path
    if not p.is_file():
        return set()
    return {
        ln.strip()
        for ln in p.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    }


def check_claims_resolve(ctx: Context) -> None:
    """Leg 2: a `source_of_truth:` path that does not exist claims nothing while reading
    as coverage. Every declared path must resolve on disk."""
    for reg in registers(ctx):
        fm = frontmatter(reg.read_text(encoding="utf-8"))
        if fm is None:
            continue
        for s in source_of_truth(fm):
            if not (ctx.root / s.rstrip("/")).exists():
                err(
                    ctx,
                    ctx.rel(reg),
                    f"`source_of_truth: {s}` does not exist — a dangling claim covers nothing "
                    "while reading as coverage; fix the path or drop the entry",
                )


def check_coverage(ctx: Context) -> None:
    """Leg 1: exhaustive coverage. Dormant until a baseline is committed, so a tree that
    predates the mechanism is never retroactively failed."""
    if not ctx.unclaimed_baseline_path.is_file():
        return
    where = baseline_rel(ctx)
    baseline = read_baseline(ctx)
    claimed = claimed_paths(ctx)
    unclaimed = [
        rel
        for rel in covered_docs(ctx)
        if not is_claimed(rel, claimed) and not excluded(ctx, rel) and rel not in baseline
    ]
    for rel in sorted(unclaimed)[:60]:
        err(
            ctx,
            where,
            f"unclaimed prose `{rel}` — no requirement register's `source_of_truth:` claims it, "
            "its `type:` is not an excluded shape, and it is absent from UNCLAIMED.baseline. "
            "Either claim it from the register that owns its domain, or add it to the baseline "
            "as acknowledged debt (the baseline may shrink, never grow)",
        )
    if len(unclaimed) > 60:
        err(ctx, where, f"...and {len(unclaimed) - 60} further unclaimed documents")
    if baseline:
        ctx.notes.append(
            f"UNCLAIMED.baseline: {len(baseline)} document(s) of acknowledged commitment debt "
            "remain to be claimed (the burn-down queue)"
        )


def check_baseline_ratchet(ctx: Context) -> None:
    """The baseline may shrink, never grow: a diff that net-adds entries fails unless an
    equal number is burned down in the same change, or the addition carries an explicit
    `# ack: <path> <reason>` line. Regenerating the file to absorb new debt would launder
    exactly the signal this exists to keep, so it is a check and not a convention.

    The base side is read at the MERGE BASE of `base_ref` and HEAD, never at the tip of
    `base_ref` (ENG-9394): a burn-down that lands on main after a branch forked must not
    be read as that branch's additions — the branch merely inherited the pre-burn-down
    lines, and only what it adds on top of the shared ancestor ratchets. (The same
    mechanism `_journeys.py` fixed under ENG-7840.)"""
    cur = ctx.unclaimed_baseline_path
    if not cur.is_file():
        return
    where = baseline_rel(ctx)
    try:
        base = subprocess.check_output(
            ["git", "merge-base", ctx.cfg.base_ref, "HEAD"], cwd=ctx.root, text=True, stderr=subprocess.DEVNULL
        ).strip()
        old = subprocess.check_output(
            ["git", "show", f"{base}:{where}"], cwd=ctx.root, text=True, stderr=subprocess.DEVNULL
        )
    except Exception:
        return  # no baseline at the merge base yet — the creation PR is exempt, as in validate_journeys
    text = cur.read_text(encoding="utf-8")
    base_entries = {ln.strip() for ln in old.splitlines() if ln.strip() and not ln.lstrip().startswith("#")}
    new_entries = {ln.strip() for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")}
    acked = {m.group(1) for m in (ACK_RE.match(ln) for ln in text.splitlines()) if m}
    added = new_entries - base_entries
    removed = base_entries - new_entries
    if len(added - acked) > len(removed):
        for p in sorted(added - acked)[:30]:
            err(
                ctx,
                where,
                f"baseline grew: `{p}` added without a matching burn-down — the baseline may "
                "shrink, never grow. Claim the document from a register, burn down an entry in "
                "the same change, or record `# ack: <path> <reason>` above it",
            )


def write_baseline(ctx: Context) -> int:
    """Re-seed the unclaimed baseline from the current unclaimed set. Run by a human when
    the debt picture genuinely changes; the ratchet then refuses to let it grow after."""
    claimed = claimed_paths(ctx)
    unclaimed = [rel for rel in covered_docs(ctx) if not is_claimed(rel, claimed) and not excluded(ctx, rel)]
    p = ctx.unclaimed_baseline_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f"# Generated by: {ctx.cfg.cmd_validate_coverage} --write-baseline\n"
        "# Every line is a spec or decision record that no requirement register's `source_of_truth:`\n"
        "# claims — prose that may assert a commitment nothing has a row for (acknowledged debt).\n"
        "# Burn debt down by claiming the document from the register that owns its domain and\n"
        "# removing the line here. The baseline may shrink, never grow: a NEW entry needs a matching\n"
        "# burn-down in the same change, or an explicit `# ack: <path> <reason>` line above it.\n"
        + "".join(f"{rel}\n" for rel in unclaimed),
        encoding="utf-8",
    )
    print(f"wrote {len(unclaimed)} unclaimed documents to {baseline_rel(ctx)}")
    return 0


def main(ctx: Context) -> int:
    check_claims_resolve(ctx)
    check_coverage(ctx)
    check_baseline_ratchet(ctx)
    for n in ctx.notes:
        print(f"note: {n}")
    if ctx.errors:
        print(f"\ncommitment coverage: {len(ctx.errors)} violation(s)\n")
        for e in ctx.errors:
            print(f"  - {e}")
        return 1
    print("commitment coverage OK — every spec/decision is claimed, excluded by type, or baselined.")
    return 0
