"""A `## Bar` says what somebody would have to SEE — and stays bound to what it decomposes.

A completion reading is arithmetic over artifacts in git: every child cut finished, every named
proof shipped. It can be entirely right on a day the promise is broken in the running product,
because a shipped artifact proves a capability EXISTS and never that it is CONNECTED. A bar is
the observation that reading cannot make: conditions authored in advance, each stating its own
RED, each with the probe that could refute it. This check does not run the probes and does not
record a verdict — a verdict is true of one deployment at one instant and belongs nowhere in a
corpus. It checks that the commitment is well formed and still bound to what it decomposes.

**An absent `## Bar` produces NOTHING here — not an error, not a warning, not an advisory.**
That is the single most load-bearing line in this module, and it is a design decision rather
than an omission. The contract makes a bar optional and monotone: a corpus in which no program
and no slice carries one is a valid corpus, and adding the contract asks nothing of anybody. A
check that punished absence would make "optional" a lie, and people would write bars to silence
it — reconstructed after the fact from whatever shipped, which is the one condition under which
a bar is guaranteed to be worthless. The whole point of authoring a bar early is that it says
what would have to be true *before* anyone knows what got built; a gate that manufactures bars
manufactures exactly the worthless kind. So absence is silence, and only a bar that EXISTS is
held to anything.

What a bar that exists is held to:

  * **Every row is a criterion.** An id, a statement, and a probe cell that says something —
    including `"No probe yet."`, which is a real answer: it says the criterion has never been
    read either way, which is worth far more than a probe invented to fill the column.
  * **The bar says what its criteria are measured against.** A `**Scope.**` line, at both tiers.
    A verdict is per-environment, so a criterion whose bar does not name the plane it is read on
    yields an observation nobody can act on — red here and green there, with nothing saying
    which was the standard.
  * **Ids are the entity's own, sequential, and globally unique.** A criterion id is cited from
    outside git — an issue, a report, a conversation — so a reused id silently rebinds what an
    earlier citation pointed at, and nothing about the citation looks wrong afterwards.
  * **A slice bar carries a live digest of its `Done when` cell.** This is the anti-drift teeth.
    The sentence lives in a different file; without the digest a bar can be quietly re-aimed at
    what shipped, which is the same act as rewriting a finished cut's promise to fit the code
    that arrived. Edit the sentence and this fails until every criterion has been re-affirmed
    against the sentence as it now reads.
  * **A program bar carries no digest and does carry a `**Demonstration.**`.** It binds across
    no file, so a digest there breaks on nothing while reading to the next author like a check
    that is running; and its criteria decompose a demonstration sentence that has to exist for
    them to decompose anything.

The parse itself is `fleet_knowledge.bars`, in the spine, because a reader that renders a bar
needs the same answer this gate uses.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fleet_knowledge import bars as barparse

from . import _registers
from ._api import ERROR, Report, finding
from ._config import PlanningConfig
from ._digest import digest_of, extract_done_cell
from ._markdown import read

NAME = "bars"

#: The digest shape the contract fixes. Lowercase is part of it: a digest is compared as a
#: string by every reader of it, and two spellings of one value would compare unequal.
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

#: A well-formed criterion id: the entity's prefix and a positive integer, no padding.
COUNTER_RE = re.compile(r"[1-9]\d*$")

#: The two tier names, spelled once. Which tier carries the digest and which authors the
#: demonstration is the whole asymmetry of the contract, so the names say which is which.
DIGEST_TIER = "slice"
DEMONSTRATION_TIER = "program"


def _read_bars(regs: _registers.Registers) -> list[tuple[barparse.Bar, Path]]:
    """Every bar in the corpus, in a stable order: programs, then slices, each by filename.

    A detail file whose name is not a well-formed entity id is skipped — a README or a baseline
    beside the details is not an entity, and reading one would invent a bar nobody authored.
    """
    out: list[tuple[barparse.Bar, Path]] = []
    for tier, directory, id_re in (
        (DEMONSTRATION_TIER, regs.program_detail_dir, regs.cfg.re_program_id()),
        (DIGEST_TIER, regs.slice_detail_dir, regs.cfg.re_slice_id()),
    ):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            if not id_re.match(path.stem):
                continue
            bar = barparse.parse(read(path), path.stem, tier)
            if bar is not None:
                out.append((bar, path))
    return out


def analyse(kb: Any) -> Report:
    """Every finding over every bar the corpus carries. A corpus with none yields none."""
    regs = _registers.of(kb)
    report = Report()
    claimed: dict[str, str] = {}
    for bar, path in _read_bars(regs):
        _scope(bar, path, report)
        _rows(bar, path, report, claimed)
        if bar.tier == DIGEST_TIER:
            _slice_form(bar, path, regs, report)
        else:
            _program_form(bar, path, report)
    return report


# ── what the criteria are measured against ────────────────────────────────────────────


def _scope(bar: barparse.Bar, path: Path, report: Report) -> None:
    """Both tiers open with a `**Scope.**` line, and it is load-bearing rather than ceremonial.

    Every criterion here is read against a RUNNING system, and a running system is always some
    particular one: a plane, a cell, a deployment. A bar that does not say which produces
    observations nobody can act on — red on one environment and green on another, with the
    reader unable to tell which of those was the standard. The `Done when` sentence and the
    demonstration say WHAT must be true; the scope says WHERE it is read.
    """
    if bar.scope:
        return
    report.findings.append(
        finding(
            ERROR,
            f"`{bar.entity}` bar has no `**Scope.**`",
            path=path,
            line=bar.line,
            hint=(
                "Say what these criteria are measured against — the plane, cell or deployment. "
                "A criterion read against an unnamed environment yields an observation nobody can act on."
            ),
        )
    )


# ── the table ─────────────────────────────────────────────────────────────────────────


def _rows(bar: barparse.Bar, path: Path, report: Report, claimed: dict[str, str]) -> None:
    """Row shape, id shape, id sequence, and id uniqueness across the whole corpus."""
    prefix = barparse.expected_prefix(bar.entity)
    if not bar.criteria:
        report.findings.append(
            finding(
                ERROR,
                f"`{bar.entity}` has a `## {barparse.HEADING}` section with no criterion rows",
                path=path,
                line=bar.line,
                hint=(
                    "Name the conditions somebody would have to see hold in a running system, "
                    "or drop the section — an empty bar withholds nothing and says nothing."
                ),
            )
        )
        return

    for n, c in enumerate(bar.criteria, start=1):
        _id_shape(bar, c, n, prefix, path, report)
        _cells(bar, c, path, report)
        _uniqueness(bar, c, path, report, claimed)


def _id_shape(bar: barparse.Bar, c: barparse.Criterion, n: int, prefix: str, path: Path, report: Report) -> None:
    if not c.id:
        report.findings.append(
            finding(
                ERROR,
                f"`{bar.entity}` bar row {n} carries no criterion id",
                path=path,
                line=c.line,
                hint=f"Number the row `{prefix}{n}` — a criterion is cited by id from outside this file.",
            )
        )
        return
    if not (c.id.startswith(prefix) and COUNTER_RE.fullmatch(c.id[len(prefix) :])):
        report.findings.append(
            finding(
                ERROR,
                f"`{bar.entity}` bar criterion id `{c.id}` is not of the form `{prefix}<n>`",
                path=path,
                line=c.line,
                hint=f"Criterion ids are scoped to the entity that owns them: rename it `{prefix}{n}`.",
            )
        )
        return
    if c.id != f"{prefix}{n}":
        report.findings.append(
            finding(
                ERROR,
                f"`{bar.entity}` bar criterion ids are not sequential from 1 — row {n} is `{c.id}`, "
                f"and `{prefix}{n}` is the id that position takes",
                path=path,
                line=c.line,
                hint=(
                    f"Renumber from `{prefix}1` down the table. A gap reads as a criterion somebody "
                    "deleted, which is a thing only a human may do."
                ),
            )
        )


def _cells(bar: barparse.Bar, c: barparse.Criterion, path: Path, report: Report) -> None:
    """A criterion states its claim and names its probe. Both cells carry text or this fails.

    An empty probe is NOT the same fact as a probe that says there is none: `No probe yet.` is
    an authored answer — the criterion has never been read either way — and it is accepted
    exactly as written. Nothing here inspects what a probe says, only that the author answered.
    """
    label = c.id or "an unnumbered row"
    if not c.statement:
        report.findings.append(
            finding(
                ERROR,
                f"`{bar.entity}` bar criterion `{label}` states nothing",
                path=path,
                line=c.line,
                hint="A criterion names the condition under which it is RED in the sentence it makes its claim.",
            )
        )
    if not c.probe:
        report.findings.append(
            finding(
                ERROR,
                f"`{bar.entity}` bar criterion `{label}` has an empty `Probe` cell",
                path=path,
                line=c.line,
                hint=(
                    "Name the observation that could refute it — and where there is none, say so "
                    "(`No probe yet.`), which is an answer rather than a blank."
                ),
            )
        )


def _uniqueness(bar: barparse.Bar, c: barparse.Criterion, path: Path, report: Report, claimed: dict[str, str]) -> None:
    """A criterion id is claimed once in the whole corpus, and never released."""
    if not c.id:
        return
    owner = claimed.get(c.id)
    if owner is None:
        claimed[c.id] = bar.entity
        return
    where = f"used twice in `{bar.entity}`" if owner == bar.entity else f"claimed by both `{owner}` and `{bar.entity}`"
    report.findings.append(
        finding(
            ERROR,
            f"criterion id `{c.id}` is {where}",
            path=path,
            line=c.line,
            hint=(
                "Give one of them a fresh number. An id is cited from outside git, so reusing one "
                "silently rebinds what an earlier citation pointed at."
            ),
        )
    )


# ── the two tier forms ────────────────────────────────────────────────────────────────


def _slice_form(bar: barparse.Bar, path: Path, regs: _registers.Registers, report: Report) -> None:
    """A slice bar binds to its completion sentence, and never authors a demonstration."""
    if bar.demonstration:
        report.findings.append(
            finding(
                ERROR,
                f"`{bar.entity}` bar carries a `**Demonstration.**`, which is the program form",
                path=path,
                line=bar.line,
                hint=(
                    "A slice's criteria decompose its `Done when` cell, and the digest is what binds "
                    "them to it — drop the demonstration and let the cell be the sentence."
                ),
                command=regs.cfg.command("slice_edit", slice=bar.entity),
            )
        )
    _digest(bar, path, regs, report)


def _digest(bar: barparse.Bar, path: Path, regs: _registers.Registers, report: Report) -> None:
    """The anti-drift teeth: the stored digest is live against the cell as it now reads."""
    cfg: PlanningConfig = regs.cfg
    fix = cfg.command("slice_edit", slice=bar.entity)
    if bar.digest is None:
        report.findings.append(
            finding(
                ERROR,
                f"`{bar.entity}` bar carries no `<!-- done-cell-digest: sha256:... -->`",
                path=path,
                line=bar.line,
                hint=(
                    "Nothing then binds these criteria to the `Done when` sentence they decompose, and "
                    "the bar can be re-aimed at whatever shipped. Digest the cell's exact bytes."
                ),
                command=fix,
            )
        )
        return
    if not HEX64_RE.match(bar.digest):
        report.findings.append(
            finding(
                ERROR,
                f"`{bar.entity}` bar digest `{bar.digest}` is not 64 lowercase hex",
                path=path,
                line=bar.line,
                hint="Store the SHA-256 of the cell's exact UTF-8 bytes, lowercase — it is compared as a string.",
                command=fix,
            )
        )
        return
    try:
        done = extract_done_cell(regs.slice_register, bar.entity, regs.slice_rows_dir)
    except (FileNotFoundError, ValueError) as e:
        report.findings.append(
            finding(
                ERROR,
                f"`{bar.entity}` bar cannot be bound to a completion condition: {e}",
                path=path,
                line=bar.line,
                hint="A bar decomposes the cell on the entity's own register row; that row has to be readable.",
            )
        )
        return
    expected = digest_of(done)
    if bar.digest != expected:
        report.findings.append(
            finding(
                ERROR,
                f"`{bar.entity}` bar digest is stale — the `Done when` cell now digests to "
                f"sha256:{expected}, the bar stores sha256:{bar.digest}",
                path=path,
                line=bar.line,
                hint=(
                    "Re-read the sentence as it now stands and re-affirm every criterion against it, "
                    "then re-bless the digest. Widening a criterion to fit is a human's call."
                ),
                command=fix,
            )
        )


def _program_form(bar: barparse.Bar, path: Path, report: Report) -> None:
    """A program bar authors its own sentence, and binds across nothing."""
    if bar.digest is not None:
        report.findings.append(
            finding(
                ERROR,
                f"`{bar.entity}` bar carries a done-cell digest, and a program has no `Done when` cell for it to bind",
                path=path,
                line=bar.line,
                hint=(
                    "The demonstration it decomposes is authored inside the bar itself, so the digest is "
                    "over bytes in the section it guards: it breaks on nothing and reads to the next "
                    "author like a check that is running. Remove it."
                ),
            )
        )
    if not bar.demonstration:
        report.findings.append(
            finding(
                ERROR,
                f"`{bar.entity}` bar has no `**Demonstration.**`",
                path=path,
                line=bar.line,
                hint=(
                    "A program's criteria decompose a demonstration sentence authored in the bar; without "
                    "one they decompose nothing. Write what a person would do, end to end, and see work."
                ),
            )
        )


# ── the check ─────────────────────────────────────────────────────────────────────────


class BarsCheck:
    """A bar that exists is well formed and still bound to what it decomposes. Absence is silent."""

    name = NAME
    title = "Bars are well formed and bound"
    description = (
        "A completion reading is arithmetic over artifacts in git, so it can read complete on a day the "
        "promise is broken in the running product — a shipped artifact proves a capability exists, never "
        "that it is connected. A bar is the observation that reading cannot make: conditions authored in "
        "advance, each stating its own RED, each with the probe that could refute it. This check holds a "
        "bar that EXISTS to its shape — a `**Scope.**` naming what the criteria are measured against, "
        "because a verdict is per-environment; criterion ids scoped to the entity, sequential, and unique "
        "across the corpus because they are cited from outside git; a statement and a probe in every row "
        "— and, on a slice, keeps its digest live against the exact bytes of the `Done when` cell it "
        "decomposes, which is what stops a bar being quietly re-aimed at whatever shipped. An ABSENT bar "
        "produces nothing at all: the contract makes it optional, and a gate that punished absence would "
        "have people write bars to silence it, reconstructed from what shipped, which is the one kind of "
        "bar guaranteed to be worthless."
    )

    def applies(self, kb: Any) -> bool:
        return bool(kb.has("programs_detail_dir") or kb.has("slices_detail_dir"))

    def run(self, kb: Any) -> list[Any]:
        return analyse(kb).findings


CHECK = BarsCheck()


def cli(kb: Any) -> int:
    """Print the findings the way this family's ported validators print theirs."""
    regs = _registers.of(kb)
    report = analyse(kb)
    if report.errors:
        print("validate_bars: FAILED")
        for f in report.errors:
            print(f"- {f.message}")
        return 1
    found = _read_bars(regs)
    criteria = sum(len(bar.criteria) for bar, _ in found)
    print(f"validate_bars: OK — {len(found)} bar(s), {criteria} criteria")
    return 0
