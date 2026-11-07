"""Gate: an acceptance criterion observable only in a real environment is promoted, never deferred.

WHY THIS EXISTS. A PRD's acceptance criteria are verified on the dev stack, and some cannot be:
a live cluster, a third-party credential, a customer network, a second real user. The
convention for those was a tag, `[ext]`, read by the verifier as "N/A until the dependency
exists". The PRD then shipped, the slice it belongs to computed *complete* from that PRD's
`status:`, and the one criterion the slice's `Done when` actually depended on was never run —
and nothing ever came back for it. Measured 2026-09-10 on the corpus this was written against:
49 slices read complete, all 49 on a member PRD's status alone, and 4 of them on a proof PRD
whose live criteria were `[ext]`-deferred; the SRE agent among them had been blind on the
cluster it was moved to for eleven days while every reading said done.

The rule now makes `[ext]` a hand-off rather than an exemption. The criterion is **promoted**
into the owning slice's `## Bar` — the tier whose promise *is* the environment — as a row with a
probe, and the tag cites the row: `[ext → SL162-C3]`. The slice's driver measures the row every
cycle; `prd:verify` passes the criterion on the promotion existing. A bare `[ext]` is the old
valve and is refused.

WHAT IT CHECKS, AND WHY THAT SIGNAL. In every in-scope PRD's `## Acceptance criteria` section,
each `[ext …]` tag must (1) carry a criterion id, (2) name the PRD's own slice (the id prefix
`SL162-C` is the register id `SL-162` with the dash dropped, the shape `bars.expected_prefix`
defines), (3) resolve to a row in that slice detail file's `## Bar`, and (4) that row's Probe
must be an observation rather than the honest placeholder `No probe yet`. Four mechanical facts,
each a place the promotion can be faked by omission. Deliberately NOT checked: whether the probe
is a *good* observation, whether the row really decomposes the `Done when` — the `bars` check
owns the bar's shape and digest, and judgement belongs to the human who ratifies the bar.

SCOPE AND THE CUTOFF. A PRD is gated when its prd.md was ADDED on or after
`ext_promotion_cutoff` (git authorship date), or is not yet committed at all — the sibling
process-artifact gates' machinery exactly, so an uncommitted PRD is in scope at the moment it
most matters and history authored under the older convention is read as history. `stub` and
`cancelled` PRDs are outside: nothing is being promised.

SEVERITY: BLOCKING. The heading is there or it is not; the tag resolves or it does not; the
remediation is one row in one file, and the failure it prevents is a slice reading complete on
a promise nobody ran.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fleet_knowledge import bars as barparse
from fleet_knowledge.config import git_context

from . import _artifact_scope, _git, _registers
from ._api import ERROR, Report, finding
from ._config import PlanningConfig
from ._git import adds_since, head_tree
from ._markdown import extract_section, rel
from .prd_commitments_section import prds_root

NAME = "prd-ext-promotion"

__all__ = ["CHECK", "NAME", "PrdExtPromotionCheck", "analyse", "cli", "violations"]

#: `[ext]`, `[ext → SL162-C3]`, `[ext -> SL162-C3]` — with or without the backticks PRD prose
#: wraps a tag in. Group 1 is the cited criterion id, or None for the bare form.
EXT_TAG_RE = re.compile(r"\[ext(?:\s*(?:→|->)\s*([A-Za-z]+\d+-[A-Za-z]\d+))?\s*\]")
SLICE_RE = re.compile(r"^slice:\s*(\S+)\s*$", re.M)
#: A Probe cell that honestly says the observation cannot be made yet. Allowed on a bar row in
#: general (the contract prefers an honest cell to an absent one); refused on a PROMOTED row,
#: because a criterion nobody can observe is not one a PRD may hand up and call verified.
NO_PROBE_RE = re.compile(r"^\s*no\s+probe\s+yet\b", re.I)
#: Statuses at which nothing is promised: a stub predates authoring, a cancelled PRD is dead.
UNGATED_STATUSES = frozenset({"stub", "cancelled", "canceled"})


def _walk_refusal(cfg: PlanningConfig, root_rel: str, cut: str) -> str:
    return _git.walk_refusal(
        NAME,
        cut,
        f"git log --diff-filter=A --since={_git.date_minus_days(cut, 2)} --format=%x00%aI --name-only -- {root_rel}",
        "A prd.md is gated when `git log --diff-filter=A --since` dates it on or after the "
        f'{cut} cutoff. A failed walk reads as "nothing authored since the cutoff": the gate would '
        "validate nothing and report success while every post-cutoff `[ext]` criterion goes unchecked.",
    )


def _slice_of(prd_md_text: str) -> str | None:
    m = SLICE_RE.search(prd_md_text)
    return m.group(1) if m else None


def _bar_rows(regs: _registers.Registers, sid: str) -> dict[str, barparse.Criterion] | None:
    """The slice's bar rows by id, or None when the detail file carries no `## Bar`."""
    path = regs.slice_detail(sid)
    if not path.is_file():
        return None
    bar = barparse.parse(path.read_text(encoding="utf-8", errors="replace"), sid, "slice")
    if bar is None:
        return None
    return {c.id: c for c in bar.criteria}


def _tag_findings(
    prd_name: str,
    prd_md: Path,
    text: str,
    section: str,
    regs: _registers.Registers,
) -> list[tuple[str, int, str]]:
    """[(prd_dir_name, line, why)] for every `[ext]` tag in `section` that is not a valid promotion."""
    out: list[tuple[str, int, str]] = []
    sid = _slice_of(text)
    # Line numbers are reported against the whole file; the section's offset is found once.
    start = text.find(section) if section else -1
    base_line = text[:start].count("\n") + 1 if start >= 0 else 1
    rows: dict[str, barparse.Criterion] | None = None
    rows_read = False
    for i, line in enumerate(section.splitlines()):
        for m in EXT_TAG_RE.finditer(line):
            cid = m.group(1)
            ln = base_line + i
            if cid is None:
                out.append((prd_name, ln, "bare `[ext]` — the criterion is deferred, not promoted"))
                continue
            if sid is None:
                out.append((prd_name, ln, f"`[ext → {cid}]` but the PRD names no `slice:` to promote into"))
                continue
            want = barparse.expected_prefix(sid)
            if not cid.startswith(want):
                out.append(
                    (
                        prd_name,
                        ln,
                        f"`[ext → {cid}]` names a criterion outside this PRD's slice `{sid}` (expected `{want}n`)",
                    )
                )
                continue
            if not rows_read:
                rows = _bar_rows(regs, sid)
                rows_read = True
            if rows is None:
                out.append(
                    (
                        prd_name,
                        ln,
                        f"`[ext → {cid}]` but `{rel(regs.slice_detail(sid), regs.knowledge.parent)}` "
                        "carries no `## Bar`",
                    )
                )
                continue
            row = rows.get(cid)
            if row is None:
                out.append((prd_name, ln, f"`[ext → {cid}]` resolves to no row in `{sid}`'s `## Bar`"))
                continue
            if not row.probe.strip() or NO_PROBE_RE.match(row.probe):
                out.append(
                    (
                        prd_name,
                        ln,
                        f"`[ext → {cid}]` is promoted onto a row with no probe (`{sid}` bar line {row.line})",
                    )
                )
    return out


def violations(
    kb: Any,
    *,
    base: str | None,
    cutoff: str | None = None,
    prd_root: Path | None = None,
) -> list[tuple[str, int, str]] | None:
    """[(prd_dir_name, line, why)] for in-scope PRDs carrying an unpromoted `[ext]` criterion.

    None when the history walk failed — the sibling gates' contract: an empty list means the
    walk ran and nothing is wrong, while a failed walk would read as "nothing in scope" and
    switch the gate silently OFF. The caller refuses.
    """
    cfg = PlanningConfig.of(kb)
    repo_root = Path(kb.root)
    root = prd_root or prds_root(kb)
    cut = cutoff or cfg.ext_promotion_cutoff
    root_rel = rel(root, repo_root)
    recent = adds_since(repo_root, cut, root_rel)
    if recent is None:
        return None
    committed = head_tree(repo_root, root_rel)
    regs = _registers.of(kb)

    out: list[tuple[str, int, str]] = []
    for prd in _artifact_scope.prds_in_scope(repo_root, root, base):
        status = _artifact_scope.prd_status(prd)
        if status is None or status in UNGATED_STATUSES:
            continue
        target = f"{root_rel}/{prd.name}/prd.md"
        born = recent.get(target)
        in_scope = target not in committed or (born is not None and born >= cut)
        if not in_scope:
            continue
        prd_md = prd / "prd.md"
        text = prd_md.read_text(encoding="utf-8", errors="replace")
        section = extract_section(text, cfg.acceptance_section) or ""
        out.extend(_tag_findings(prd.name, prd_md, text, section, regs))

    if base is not None:
        # A plain title says nothing about an acceptance criterion (owner decision,
        # 2026-11-05). A title-only edit must not re-open this gate over a PRD whose `[ext]`
        # criteria predate the rule; every other edit is still fully checked.
        out = [
            (name, line, why)
            for name, line, why in out
            if not _artifact_scope.plain_title_only_edit(repo_root, f"{root_rel}/{name}/prd.md", base)
        ]
    return out


def analyse(kb: Any, *, base: str | None = None, cutoff: str | None = None) -> Report:
    cfg = PlanningConfig.of(kb)
    root = prds_root(kb)
    report = Report()
    if not root.is_dir():
        report.refusal = f"{NAME} OK — no {rel(root, Path(kb.root))}/ to check"
        return report
    cut = cutoff or cfg.ext_promotion_cutoff
    bad = violations(kb, base=base, cutoff=cut)
    if bad is None:
        report.refusal = _walk_refusal(cfg, rel(root, Path(kb.root)), cut)
        return report
    for name, line, why in bad:
        report.findings.append(
            finding(
                ERROR,
                f"prd.md authored on/after {cut} carries an `[ext]` acceptance criterion that is not promoted: {why}",
                path=root / name / "prd.md",
                line=line,
                hint=(
                    "Write the criterion as one row of the owning slice's `## Bar` (knowledge/slices/SL-NNN.md) "
                    "with a real probe, and cite it: `[ext → SLnnn-Cn]`. A criterion only a real environment "
                    "can show is measured by the slice's driver every cycle — never N/A'd until the "
                    "dependency exists."
                ),
                command=cfg.command("prd_create", prd=name.split("-", 1)[0]),
            )
        )
    return report


class PrdExtPromotionCheck:
    """An `[ext]` acceptance criterion is promoted into its slice's `## Bar`, never deferred."""

    name = NAME
    title = "PRD [ext] promotion"
    description = (
        "A criterion observable only against a real environment used to be tagged `[ext]` and N/A'd until "
        "the dependency existed; the PRD shipped over it and its slice computed complete from that status, "
        "with the one thing the slice's promise needed never run. Now `[ext]` is a promotion: the criterion "
        "sits as a probed row in the owning slice's `## Bar`, the tag cites the row (`[ext → SL162-C3]`), "
        "and the slice's driver measures it every cycle. This gate reads the four mechanical facts a "
        "promotion can fake by omission — id present, slice matches, row exists, probe is real — on every "
        "PRD authored on or after the cutoff. A history walk that fails refuses with its cause rather than "
        "reading as an empty scope."
    )

    def applies(self, kb: Any) -> bool:
        from ._git import is_repository  # noqa: PLC0415 - only this check's applies() needs git

        return bool(kb.has("prds_dir")) and is_repository(Path(kb.root))

    def run(self, kb: Any) -> list[Any]:
        report = analyse(kb, base=git_context(kb).base or PlanningConfig.of(kb).default_diff_base)
        if report.refusal:
            return [finding(ERROR, report.refusal)]
        return report.findings


CHECK = PrdExtPromotionCheck()


def cli(kb: Any, *, base: str | None, cutoff: str | None = None, prd_root: Path | None = None) -> int:
    """A `scripts/`-shaped entry point: one line per violation, exit 1 on any."""
    cfg = PlanningConfig.of(kb)
    root = prd_root or prds_root(kb)
    cut = cutoff or cfg.ext_promotion_cutoff
    if not root.is_dir():
        print(f"{NAME} OK — no {rel(root, Path(kb.root))}/ to check")
        return 0
    bad = violations(kb, base=base, cutoff=cut, prd_root=root)
    if bad is None:
        print(_walk_refusal(cfg, rel(root, Path(kb.root)), cut))
        return 1
    if not bad:
        print(f"{NAME} OK — every in-scope `[ext]` criterion is promoted (PRDs authored before {cut} are out of scope)")
        return 0
    print(f"{NAME} FAILED: {len(bad)} unpromoted `[ext]` criterion(s) in prd.md files authored on/after {cut}:")
    root_rel = rel(root, Path(kb.root))
    for name, line, why in bad:
        print(f"  - {root_rel}/{name}/prd.md:{line}  ({why})")
    print(
        "Promote each: one row in the owning slice's `## Bar` (knowledge/slices/SL-NNN.md) with a real probe, "
        "cited as `[ext → SLnnn-Cn]`. A bare `[ext]` is the escape valve this gate closes."
    )
    return 1
