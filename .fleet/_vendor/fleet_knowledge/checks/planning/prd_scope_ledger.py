"""Gate: a PRD or design authored after the scope-discipline rule landed carries `## Scope ledger`.

WHY THIS EXISTS. Adding customer-facing functionality is the one call reserved for a human, and
that reservation used to be enforced only at the front door — a `*:create` command files
evidence, a triage gate decides. Once a PRD existed, nothing enforced it again, and two defaults
inside the design command actively pushed the other way: a "fix it now — THE DEFAULT" step swept
quirks out of code the PRD never had to touch, and an "adopt — THE DEFAULT" step folded in a
critic panel's own proposals. Both cited the *craft* rule ("best practice is the default — never
interview to ask permission to follow the standard") as licence over *scope*. It is not one, and
the result was designs that grew surfaces, settings and abstractions nobody asked for — visible
to the human only as a finished mockup, which asks them to veto something that already looks
built.

The rule now draws the line: an addition enters unasked only when an acceptance criterion cannot
pass without it, or when it is a written-rule violation in a file the PRD already modifies.
Everything else is **withheld** and put to the human **once**, as one batched offer.

WHAT IT CHECKS, AND WHY THAT SIGNAL. The `## Scope ledger` section is that rule's deterministic
footprint: both templates write it, listing every addition beyond the ask — **admitted and
withheld alike**. Its presence proves the offer step ran; its contents are a judgement no
validator can grade, and they already have owners. A section reading
`none — <what was considered>` passes and is the *expected* outcome for a well-scoped PRD; an
unfilled one (absent, empty, or still the literal `<...>` template stub) does not.

The one mechanical half this gate does read in the contents: an `admitted` row must name the
acceptance criterion it cannot pass without, or the written-rule violation it fixes (design
Rule 6b — those are the only two grounds an addition may enter unasked). A row admitted on
neither is exactly the "while I was here" addition this rule exists to stop, and it is
detectable without grading whether the citation is *good* — only whether one is there.

Deliberately NOT checked: whether a listed addition really cleared the bar, whether the offer's
options were fairly framed, or whether rows are additions rather than decisions. A gate on a
judgement trains people to route around it.

ONE EXEMPTION, AND ONLY ONE. A change whose only effect on an artifact is an added
`plain_title:` frontmatter line is not a scope edit and is not checked. A plain title says
nothing about what the PRD builds, and re-opening a shipped PRD's scope offer to write one
would fabricate history. The exemption is deliberately narrow: the diff must add exactly that
one line and remove nothing, so any body edit, any second key, and every new artifact are
still fully checked.

SEVERITY: BLOCKING, for the sibling gate's reasons exactly — the heading is there or it is not,
and the remediation is local and cheap. SCOPE, DIFF-LIMITING AND THE CUTOFF all match that
sibling, whose machinery this shares. **Two** artifacts are checked where the sibling checks one,
because scope is settled twice — once at PRD authoring and once at design — and either is a place
an addition can arrive unseen.

Ported from `scripts/validate_prd_scope_ledger.py`; messages and exit code unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fleet_knowledge.config import git_context

from . import _artifact_scope, _git
from ._api import ERROR, Report, finding
from ._config import PlanningConfig
from ._git import adds_since, head_tree
from ._markdown import extract_section, is_placeholder, rel
from .prd_commitments_section import prds_root

NAME = "prd-scope-ledger"

#: `prds_root` is the sibling gate's resolver, re-exported deliberately: both gates read the
#: same tree, and two functions answering "where are the PRDs" is exactly the drift this
#: family exists to prevent. Named here so the re-export is part of the module's surface
#: rather than an accident of the import list.
__all__ = ["CHECK", "NAME", "PrdScopeLedgerCheck", "analyse", "cli", "prds_root", "violations"]


def _walk_refusal(cfg: PlanningConfig, root_rel: str, cut: str) -> str:
    """Why this gate refuses to run over a history it could not read. Sibling's shape, own words."""
    return _git.walk_refusal(
        NAME,
        cut,
        f"git log --diff-filter=A --since={_git.date_minus_days(cut, 2)} --format=%x00%aI --name-only -- {root_rel}",
        "A prd.md or design.md is gated when `git log --diff-filter=A --since` dates it on or after the "
        f'{cut} cutoff. A failed walk reads as "nothing authored since the cutoff": the gate would '
        "validate nothing and report success while every post-cutoff artifact without a filled section "
        "goes unchecked.",
    )


def _artifacts(cfg: PlanningConfig) -> tuple[tuple[str, frozenset[str], str], ...]:
    """(filename, statuses that require the section, the step that writes it).

    `prd.md` is written at `prd-drafted` and every state after it; `cancelled` is dead and
    `stub` predates authoring, so neither buys anything by being blocked. `design.md` follows
    `designed_or_beyond` exactly — a PRD at those states has been through the design template.
    """
    return (
        ("prd.md", frozenset({"prd-drafted"}) | cfg.designed_or_beyond, "the PRD authoring stage's scope offer"),
        ("design.md", cfg.designed_or_beyond, "the design stage's scope offer"),
    )


def violations(
    kb: Any,
    *,
    base: str | None,
    cutoff: str | None = None,
    prd_root: Path | None = None,
) -> list[tuple[str, str, str]] | None:
    """[(prd_dir_name, artifact filename, why)] for in-scope artifacts with a scope-ledger defect.

    None when the history walk itself failed — the sibling gate's contract exactly: an empty
    list means the walk ran and nothing is in scope, while a failed walk reads as "nothing
    authored since the cutoff" and turns the gate silently OFF. The caller refuses.
    """
    cfg = PlanningConfig.of(kb)
    repo_root = Path(kb.root)
    root = prd_root or prds_root(kb)
    cut = cutoff or cfg.scope_ledger_cutoff
    root_rel = rel(root, repo_root)
    recent = adds_since(repo_root, cut, root_rel)
    if recent is None:
        return None
    committed = head_tree(repo_root, root_rel)

    out: list[tuple[str, str, str]] = []
    for prd in _artifact_scope.prds_in_scope(repo_root, root, base):
        status = _artifact_scope.prd_status(prd)
        if status is None:
            continue

        for name, statuses, _writer in _artifacts(cfg):
            path = prd / name
            if status not in statuses or not path.is_file():
                # A missing design.md at a designed-or-beyond status is a real defect with a
                # different owner; this gate is about an artifact's contents.
                continue
            body = extract_section(path.read_text(encoding="utf-8", errors="replace"), cfg.scope_ledger_section)
            target = f"{root_rel}/{prd.name}/{name}"
            in_scope = target not in committed or ((born := recent.get(target)) and born >= cut)
            if not in_scope:
                continue
            if is_placeholder(body):
                if target not in committed:
                    out.append((prd.name, name, f"status `{status}`, {name} not committed yet"))
                else:
                    out.append((prd.name, name, f"status `{status}`, {name} authored {recent[target]}"))
                continue
            why = _unbacked_admitted_row(body or "")
            if why is not None:
                out.append((prd.name, name, why))

    if base is not None:
        # A plain title says nothing about scope (owner decision, 2026-11-05). Adding one to a
        # shipped PRD must not drag that PRD's whole scope ledger back through the offer, so a
        # change whose ONLY effect on the artifact is the added `plain_title:` line is not this
        # gate's business. Every other edit — a body change, a second frontmatter key, a
        # removal — is a real edit and stays fully checked.
        out = [
            (name, artifact, why)
            for name, artifact, why in out
            if not _artifact_scope.plain_title_only_edit(repo_root, f"{root_rel}/{name}/{artifact}", base)
        ]
    return out


#: An `admitted` scope-ledger row whose `Basis` names no acceptance criterion and no
#: written-rule violation. Every real admitted addition traces to one of those two (design
#: Rule 6b); a row that traces to neither is an addition nobody authorised. The `Basis` text
#: is free prose, so this reads for a *citation* (`AC-3`, `AC 3`, an `[ext → …]` promotion id,
#: or an explicit "written-rule violation"/"rule violation"), not for a judgement.
_AC_CITATION_RE = re.compile(r"\bAC[-\s]?\d+\b|\bSL\d+-C\d+\b", re.I)
_RULE_BASIS_RE = re.compile(r"written[-\s]rule|rule violation|fixes? (the|a) (violation|lint)", re.I)
#: The ledger table's data-row shape: `| # | Addition | Disposition | Basis |`.
_LEDGER_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|(?P<rest>.+)$", re.M)


def _unbacked_admitted_row(section: str) -> str | None:
    """The first `admitted` row with neither an AC citation nor a rule-violation basis, or None."""
    for m in _LEDGER_ROW_RE.finditer(section):
        cells = [c.strip() for c in m.group("rest").split("|")]
        if len(cells) < 3:
            continue
        _addition, disposition, basis = cells[0], cells[1], cells[2]
        if disposition.lower() != "admitted":
            continue
        if _AC_CITATION_RE.search(basis) or _RULE_BASIS_RE.search(basis):
            continue
        return (
            f"has an `admitted` scope-ledger row (`{_addition}`) whose Basis names no acceptance "
            "criterion and no written-rule violation"
        )
    return None


def analyse(kb: Any, *, base: str | None = None, cutoff: str | None = None) -> Report:
    cfg = PlanningConfig.of(kb)
    root = prds_root(kb)
    report = Report()
    if not root.is_dir():
        report.refusal = f"{NAME} OK — no {rel(root, Path(kb.root))}/ to check"
        return report
    cut = cutoff or cfg.scope_ledger_cutoff
    writers = {name: writer for name, _statuses, writer in _artifacts(cfg)}
    bad = violations(kb, base=base, cutoff=cut)
    if bad is None:
        report.refusal = _walk_refusal(cfg, rel(root, Path(kb.root)), cut)
        return report
    for name, artifact, why in bad:
        missing_section = why.startswith("status `")
        if missing_section:
            message = (
                f"{artifact} authored on/after {cut} reached a status that requires a filled "
                f"`## {cfg.scope_ledger_section}` section and has none ({why})"
            )
            hint = (
                f"Run {writers[artifact]}, then write the section — one row per addition beyond the "
                'ask, admitted AND withheld alike. "none — <what was considered>" is expected.'
            )
        else:
            message = (
                f"{artifact} authored on/after {cut} {why} — an admitted addition must trace to an "
                "acceptance criterion or a written-rule violation"
            )
            hint = (
                "Either name the AC the row cannot pass without (e.g. `AC-3 cannot pass without it`) or "
                "the written-rule violation it fixes, or make the row `withheld` — an addition no AC "
                "requires belongs on the withheld list, not in the change."
            )
        report.findings.append(
            finding(
                ERROR,
                message,
                path=root / name / artifact,
                hint=hint,
                command=cfg.command("prd_create" if artifact == "prd.md" else "prd_design", prd=name.split("-", 1)[0]),
            )
        )
    return report


class PrdScopeLedgerCheck:
    """A PRD and its design each carry the filled `## Scope ledger` the scope offer writes."""

    name = NAME
    title = "PRD scope ledger"
    description = (
        "Scope is the human's call, and it stays the human's after a PRD exists — craft licence covers how "
        "well the asked-for thing gets built, never what gets built. The `## Scope ledger` is that rule's "
        "only evidence: every addition beyond the ask, admitted AND withheld, so nothing arrives unseen. "
        'This gate reads the section, not a judgement — "none, and here is what was considered" passes and '
        "is the expected outcome; an absent or still-templated section does not, and an `admitted` row "
        "whose Basis names no acceptance criterion and no written-rule violation does not either, because "
        "an addition that traces to neither is scope nobody authorised. Two artifacts are checked because "
        "scope is settled twice, at PRD authoring and again at design, and either is a place an addition "
        "can slip in. A history walk that fails refuses with its cause rather than reading as an empty "
        "scope — the silent gate-off that failure would otherwise be."
    )

    def applies(self, kb: Any) -> bool:
        from ._git import is_repository  # noqa: PLC0415 - only this check's applies() needs git

        return bool(kb.has("prds_dir")) and is_repository(Path(kb.root))

    def run(self, kb: Any) -> list[Any]:
        # The caller's base beats the configured trunk ref — see the sibling gate in
        # `prd_commitments_section` for why the two differ on a pull request.
        report = analyse(kb, base=git_context(kb).base or PlanningConfig.of(kb).default_diff_base)
        if report.refusal:
            # The runner protocol carries findings only, and a refusal must never collapse
            # into a clean pass — that collapse IS the silent gate-off this refuses to be.
            return [finding(ERROR, report.refusal)]
        return report.findings


CHECK = PrdScopeLedgerCheck()


def cli(kb: Any, *, base: str | None, cutoff: str | None = None, prd_root: Path | None = None) -> int:
    """Reproduce `scripts/validate_prd_scope_ledger.py`'s stdout and exit code exactly."""
    cfg = PlanningConfig.of(kb)
    root = prd_root or prds_root(kb)
    section = cfg.scope_ledger_section
    cut = cutoff or cfg.scope_ledger_cutoff
    if not root.is_dir():
        print(f"prd-scope-ledger OK — no {rel(root, Path(kb.root))}/ to check")
        return 0

    bad = violations(kb, base=base, cutoff=cut, prd_root=root)
    if bad is None:
        # Before the `not bad` OK branch: None is a refusal, and `not None` would print the
        # OK line over a history the gate never read.
        print(_walk_refusal(cfg, rel(root, Path(kb.root)), cut))
        return 1
    if not bad:
        print(
            f"prd-scope-ledger OK — every in-scope prd.md/design.md carries a filled `## {section}` "
            f"(artifacts authored before {cut} are out of scope)"
        )
        return 0

    print(
        f"prd-scope-ledger FAILED: {len(bad)} artifact(s) authored on/after {cut} has a `## {section}` "
        "defect (missing filled section, or an admitted addition with no AC and no rule violation):"
    )
    root_rel = rel(root, Path(kb.root))
    for name, artifact, why in bad:
        print(f"  - {root_rel}/{name}/{artifact}  ({why})")
    print(cfg.scope_ledger_remediation.format(section=section, cutoff=cut))
    return 1
