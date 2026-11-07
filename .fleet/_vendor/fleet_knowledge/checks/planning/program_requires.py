"""A program's `Requires` cell must agree with its own decomposition record.

A program's `Requires` cell in the program register is authored by hand to name the ROOTS of
its decomposition. The ground truth is the program's own detail file — its
`## Decomposition record` table lists every capability the programme presupposes. When the
two drift, the build-order derivation runs from an incomplete root set and capabilities
silently vanish from it.

Fleet-wide by default: every program that carries a decomposition record is checked, so
register and decomposition cannot drift again once reconciled. Programs without a
decomposition record are skipped — there is nothing to reconcile against.

Ported from `scripts/validate_program_requires.py`; messages and exit code unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ... import corpusref
from . import _registers
from ._api import ERROR, Report, finding
from ._config import PlanningConfig
from ._markdown import rel

NAME = "program-requires"


def _decomposition_sections(regs: _registers.Registers, pid: str) -> str | None:
    """The concatenated body of every `## Decomposition record*` section, or None.

    The heading may carry a suffix — one program's is `## Decomposition record — the trace` —
    so the match opens on any line that *starts* with the configured name.
    """
    detail = regs.program_detail(pid)
    if not detail.is_file():
        return None
    body = detail.read_text(encoding="utf-8", errors="replace")
    heading = re.escape(regs.cfg.decomposition_heading)
    sections = re.findall(rf"^{heading}[^\n]*\n(.*?)(?=^##\s|\Z)", body, re.M | re.S)
    return "\n".join(sections) if sections else None


def _corpora(regs: _registers.Registers) -> corpusref.Corpora:
    """This corpus's name and siblings — all a canonical spelling needs (nothing is resolved)."""
    return corpusref.Corpora.from_table(
        {"corpus": regs.cfg.corpus, "corpora": dict(regs.cfg.corpora)}, regs.knowledge.parent
    )


def _qualified_capabilities(regs: _registers.Registers, pid: str) -> tuple[set[str], list[str]]:
    """The capability ids a program's decomposition record derives, and the problems with any
    qualified capability in it that cannot be compared at all.

    A qualified id is read loosely — any case, any qualifier — so a misspelt one is a finding
    rather than an entry that silently vanishes: `fleet:cap-1637` (ids are uppercase) is masked
    from the bare scan and would otherwise fail the capability pattern and be dropped, and
    `Fleet:CAP-1637` (an undeclared corpus) would otherwise surface as a confusing "omits".
    """
    sections = _decomposition_sections(regs, pid)
    if not sections:
        return set(), []
    cap_re = re.compile(regs.cfg.capability_id_pattern)
    loose_cap_re = re.compile(regs.cfg.capability_id_pattern, re.IGNORECASE)
    corpora = _corpora(regs)
    caps: set[str] = set()
    problems: list[str] = []
    for line in sections.split("\n"):
        if line.lstrip().startswith("|"):
            # A capability in another corpus (`fleet:CAP-1637`) is kept qualified, and an
            # own-qualified one is the local id; the bare scan runs with every qualified
            # reference masked, so `fleet:CAP-1637` is never ALSO read as the local CAP-1637.
            for ref, _start, _end in corpusref.find_refs(line):
                if not loose_cap_re.fullmatch(ref.id):
                    continue
                if problem := corpora.qualifier_problem(ref):
                    problems.append(problem)
                elif cap_re.fullmatch(ref.id):
                    caps.add(corpora.canonical(str(ref)))
            caps.update(cap_re.findall(corpusref.mask(line)))
    return caps, problems


def decomposition_capabilities(regs: _registers.Registers, pid: str) -> set[str]:
    """Every capability id the program's decomposition record derives.

    Ground truth is the capability rows of the `## Decomposition record` TABLES, not every
    capability mentioned in the surrounding prose. Research corrections and narrative can
    cite capabilities that are not derived roots — a retired one whose own text says *do not
    re-add*, an existing one referenced in a correction. Reading the whole section invents
    drift; reading only the table rows does not.
    """
    return _qualified_capabilities(regs, pid)[0]


def check_program(kb: Any, pid: str) -> Report:
    """One program's `Requires`-vs-decomposition reconciliation."""
    regs = _registers.of(kb)
    cfg = regs.cfg
    report = Report()
    programs = {p["id"]: p for p in regs.programs()}
    prog = programs.get(pid)
    if not prog:
        report.findings.append(
            finding(
                ERROR,
                f"no program `{pid}` in the register",
                path=regs.program_register,
                hint="Check the id — a program is a row in the register, and the id is the join.",
            )
        )
        return report
    derived, problems = _qualified_capabilities(regs, pid)
    for problem in problems:
        report.findings.append(
            finding(
                ERROR,
                f"`{pid}` decomposition record: {problem}",
                path=regs.program_detail(pid),
                hint="Correct the reference — it cannot be compared with the `Requires` cell as written.",
            )
        )
    if not derived and not problems:
        report.findings.append(
            finding(
                ERROR,
                f"`{pid}` has no `{cfg.decomposition_heading}` to check against",
                path=regs.program_detail(pid),
                hint="Work the program backwards into capabilities before asking whether its roots agree.",
                command=cfg.command("program_decompose", program=pid),
            )
        )
        return report
    # Both sides in one spelling: `acme:CAP-1` is `CAP-1` in `acme`, and `fleet:CAP-1637` is
    # never the local CAP-1637 (capability ids are not prefix-owned, so a bare one is local).
    corpora = _corpora(regs)
    for entry in prog["requires"]:
        if cell_problem := corpora.qualifier_problem(corpusref.parse_ref(entry)):
            report.findings.append(
                finding(
                    ERROR,
                    f"`{pid}` Requires cell: {cell_problem}",
                    path=regs.program_register,
                    line=prog["line"],
                    hint="Correct the reference — it cannot cover a derived capability as written.",
                )
            )
    missing = sorted(derived - {corpora.canonical(r) for r in prog["requires"]})
    if missing:
        src = f"{rel(regs.program_register, Path(kb.root))} line {prog['line']}"
        report.findings.append(
            finding(
                ERROR,
                f"`{pid}` Requires cell ({src}) omits capabilities its decomposition derives: " + ", ".join(missing),
                path=regs.program_register,
                line=prog["line"],
                hint=f"Add {', '.join(missing)} to the `Requires` cell, or drop the row from the record.",
                command=cfg.command("program_decompose", program=pid),
            )
        )
    return report


def analyse(kb: Any, program_ids: list[str] | None = None) -> Report:
    """Every drifted program, in register order.

    With no ids, checks every program whose decomposition derives at least one capability.
    Skips the rest — whether because there is no `## Decomposition record` section at all or
    the section explicitly says *not yet decomposed*: there is nothing to reconcile against
    until the decomposition exists.
    """
    regs = _registers.of(kb)
    report = Report()
    if program_ids:
        for pid in (p.upper() for p in program_ids):
            report.findings.extend(check_program(kb, pid).findings)
        return report
    for p in regs.programs():
        if not any(_qualified_capabilities(regs, p["id"])):
            continue
        report.findings.extend(check_program(kb, p["id"]).findings)
    return report


class ProgramRequiresCheck:
    """Every program's `Requires` cell covers every capability its decomposition record derives."""

    name = NAME
    title = "Program requires vs decomposition"
    description = (
        "A program's `Requires` cell names the ROOTS its build-order derivation closes over; its detail "
        "file's `## Decomposition record` is where those roots were actually worked out. When the two "
        "drift, the derivation silently runs from an incomplete root set and capabilities vanish from the "
        "plan with no error anywhere. This check reconciles them fleet-wide, reading only the record's "
        "TABLE rows — prose in the same section legitimately cites capabilities that are not roots, and "
        "reading it would invent drift that is not there."
    )

    def applies(self, kb: Any) -> bool:
        if not kb.has("programs_register"):
            return False
        regs = _registers.of(kb)
        return any(decomposition_capabilities(regs, p["id"]) for p in regs.programs())

    def run(self, kb: Any) -> list[Any]:
        return analyse(kb).findings


CHECK = ProgramRequiresCheck()


def cli(kb: Any, program_ids: list[str] | None = None) -> int:
    """Reproduce `scripts/validate_program_requires.py`'s stdout and exit code exactly."""
    report = analyse(kb, program_ids)
    for e in report.findings:
        print(f"ERROR  {e.message}")
    if report.findings:
        cfg = PlanningConfig.of(kb)
        decompose = (cfg.command("program_decompose", program="") or "the decomposition command").strip()
        print(
            f"\nRun {decompose} (or fix the register cell by hand) so the "
            "`Requires` cell matches the decomposition record."
        )
        return 1
    print("OK — every program's `Requires` cell covers its decomposition record.")
    return 0
