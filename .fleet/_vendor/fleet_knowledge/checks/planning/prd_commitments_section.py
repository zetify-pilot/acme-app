"""Gate: a design authored after the commitments phase landed must carry its `## Commitments` section.

WHY THIS EXISTS. The design command's commitments phase is declared MANDATORY, and it is the
only step in the pipeline that reconciles a PRD's `implements:`, records the rows a design
*creates*, and supersedes the rows a design's Non-Goals *kill*. Skipping it is not a small
debt: two designs landed without it and a later pass found ~129 register rows still describing
mechanisms that had already been dropped.

Until this check, **nothing proved the phase ran.** A command-structure validator checks that
a command *declares* a step producing the artifact, not that it *executed*. A MANDATORY phase
whose only enforcement is prose gets skipped under deadline pressure.

WHAT IT CHECKS, AND WHY THAT SIGNAL AND NOT A BETTER ONE. The design template writes a
`## Commitments` section; a PRD at `designed` or beyond has, by definition, been through it. So
the section's presence is the phase's deterministic footprint. It is deliberately a check on the
*footprint*, not on the content: whether the rows named are the right rows is a judgement, and
it already has an owner (the design-critique register lens). A section reading
`none — <the candidates examined>` PASSES and is a legitimate outcome; an *unfilled* one
(absent, empty, or still the literal `<...>` template stub) does not.

Because it reads a heading and nothing about how a commitment is spelled, it survives changes
to the register's own format unchanged — it never opens the register at all.

SEVERITY: BLOCKING, and the split from advisory siblings is principled. An advisory check is
one whose signal is a *heuristic* — a gate on a guess trains people to route around it. This
signal is not a guess: the heading is there or it is not, and the remediation is local and
cheap (run the phase; write the section, "none" included).

Ported from `scripts/validate_prd_commitments_section.py`; messages and exit code unchanged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fleet_knowledge.config import git_context

from . import _artifact_scope, _git
from ._api import ERROR, Report, finding
from ._config import PlanningConfig
from ._git import adds_since, head_tree
from ._markdown import extract_section, is_placeholder, rel

NAME = "prd-commitments-section"

__all__ = ["CHECK", "NAME", "PrdCommitmentsSectionCheck", "analyse", "cli", "prds_root", "violations"]


def prds_root(kb: Any) -> Path:
    return Path(kb.knowledge) / PlanningConfig.of(kb).prds_dir


def _walk_refusal(cfg: PlanningConfig, root_rel: str, cut: str) -> str:
    """Why this gate refuses to run over a history it could not read."""
    return _git.walk_refusal(
        NAME,
        cut,
        f"git log --diff-filter=A --since={_git.date_minus_days(cut, 2)} --format=%x00%aI --name-only -- {root_rel}",
        "A design is gated when `git log --diff-filter=A --since` dates it on or after the "
        f'{cut} cutoff. A failed walk reads as "nothing authored since the cutoff": the gate '
        "would validate nothing and report success while every post-cutoff design without a "
        "filled section goes unchecked.",
    )


def violations(
    kb: Any,
    *,
    base: str | None,
    cutoff: str | None = None,
    prd_root: Path | None = None,
) -> list[tuple[str, str]] | None:
    """[(prd_dir_name, why)] for in-scope designs missing a filled `## Commitments`.

    None when the history walk itself failed. That is a third answer, distinct from `[]`:
    an empty list means the walk ran and nothing is in scope, while a failed walk reads as
    "nothing authored since the cutoff" and turns the gate silently OFF. The caller refuses.
    """
    cfg = PlanningConfig.of(kb)
    repo_root = Path(kb.root)
    root = prd_root or prds_root(kb)
    cut = cutoff or cfg.commitments_cutoff
    root_rel = rel(root, repo_root)
    recent = adds_since(repo_root, cut, root_rel)
    if recent is None:
        return None
    committed = head_tree(repo_root, root_rel)

    out: list[tuple[str, str]] = []
    for prd in _artifact_scope.prds_in_scope(repo_root, root, base):
        design_md = prd / "design.md"
        if not (prd / "prd.md").is_file() or not design_md.is_file():
            # No design.md at a designed-or-beyond status is a real defect, but a different
            # one, with a different owner — this check is about a design's contents.
            continue
        status = _artifact_scope.prd_status(prd)
        if status is None or status not in cfg.designed_or_beyond:
            continue
        body = design_md.read_text(encoding="utf-8", errors="replace")
        if not is_placeholder(extract_section(body, cfg.commitments_section)):
            continue
        target = f"{root_rel}/{prd.name}/design.md"
        if target not in committed:
            out.append((prd.name, f"status `{status}`, design.md not committed yet"))
        elif (born := recent.get(target)) and born >= cut:
            out.append((prd.name, f"status `{status}`, design.md authored {born}"))
    return out


def analyse(kb: Any, *, base: str | None = None, cutoff: str | None = None) -> Report:
    cfg = PlanningConfig.of(kb)
    root = prds_root(kb)
    report = Report()
    if not root.is_dir():
        report.refusal = f"{NAME} OK — no {rel(root, Path(kb.root))}/ to check"
        return report
    cut = cutoff or cfg.commitments_cutoff
    bad = violations(kb, base=base, cutoff=cut)
    if bad is None:
        report.refusal = _walk_refusal(cfg, rel(root, Path(kb.root)), cut)
        return report
    for name, why in bad:
        report.findings.append(
            finding(
                ERROR,
                f"design authored on/after {cut} reached `designed` or beyond with no filled "
                f"`## {cfg.commitments_section}` section ({why})",
                path=root / name / "design.md",
                hint=(
                    f"Run the design command's commitments phase and write the `## {cfg.commitments_section}` "
                    'section — "none — <candidates examined>" is a legitimate and expected outcome.'
                ),
                command=cfg.command("prd_design", prd=name.split("-", 1)[0]),
            )
        )
    return report


class PrdCommitmentsSectionCheck:
    """A design at `designed` or beyond carries the filled `## Commitments` section its phase writes."""

    name = NAME
    title = "PRD design commitments section"
    description = (
        "The design pipeline's commitments phase is the only step that reconciles what a PRD claims to "
        "realise against the requirement register — recording the rows the design creates and superseding "
        "the ones its Non-Goals kill. Nothing else proves it ran, so this gate reads its deterministic "
        "footprint: the `## Commitments` section the design template writes. It grades presence, never "
        'content — a section reading "none, and here is what was examined" passes; an absent or '
        "still-templated one does not. Scope is bounded by git authorship date and by the diff, so designs "
        "written before the phase existed are never in violation and one short design reds only its own change. "
        "A history walk that fails refuses with its cause rather than reading as an empty scope — the silent "
        "gate-off that failure would otherwise be."
    )

    def applies(self, kb: Any) -> bool:
        from ._git import is_repository  # noqa: PLC0415 - only this check's applies() needs git

        return bool(kb.has("prds_dir")) and is_repository(Path(kb.root))

    def run(self, kb: Any) -> list[Any]:
        # The caller's base beats the configured trunk ref. On a pull request they are not
        # the same commit: `origin/main` has moved on since this branch forked, so scoping to
        # it drags in every PRD the trunk changed meanwhile and reds this change for someone
        # else's artifact.
        report = analyse(kb, base=git_context(kb).base or PlanningConfig.of(kb).default_diff_base)
        if report.refusal:
            # The runner protocol carries findings only, and a refusal must never collapse
            # into a clean pass — that collapse IS the silent gate-off this refuses to be.
            return [finding(ERROR, report.refusal)]
        return report.findings


CHECK = PrdCommitmentsSectionCheck()


def cli(kb: Any, *, base: str | None, cutoff: str | None = None, prd_root: Path | None = None) -> int:
    """Reproduce `scripts/validate_prd_commitments_section.py`'s stdout and exit code exactly."""
    cfg = PlanningConfig.of(kb)
    root = prd_root or prds_root(kb)
    section = cfg.commitments_section
    cut = cutoff or cfg.commitments_cutoff
    if not root.is_dir():
        print(f"prd-commitments-section OK — no {rel(root, Path(kb.root))}/ to check")
        return 0

    bad = violations(kb, base=base, cutoff=cut, prd_root=root)
    if bad is None:
        # Before the `not bad` OK branch: None is a refusal, and `not None` would print the
        # OK line over a history the gate never read.
        print(_walk_refusal(cfg, rel(root, Path(kb.root)), cut))
        return 1
    if not bad:
        print(
            "prd-commitments-section OK — every in-scope design carries a filled "
            f"`## {section}` (designs authored before {cut} are out of scope)"
        )
        return 0

    print(
        f"prd-commitments-section FAILED: {len(bad)} design(s) authored on/after "
        f"{cut} reached `designed` or beyond with no filled `## {section}` section:"
    )
    root_rel = rel(root, Path(kb.root))
    for name, why in bad:
        print(f"  - {root_rel}/{name}/design.md  ({why})")
    print(cfg.commitments_remediation.format(section=section, cutoff=cut))
    return 1
