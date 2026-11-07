"""What a validator IS here, and how they are found and run.

A check is a small object with a name, a paragraph saying what it enforces and why, a
predicate that says whether it applies to this corpus, and a run method returning findings.
Nothing more: no argv, no exit codes, no printing. That is the runner's job, and keeping it
out of the checks is what lets the same check gate a commit, fill a report and answer a
`--json` query without three copies of it.

**Auto-discovery, and deliberately no registry file.** Every module under
`fleet_knowledge/checks/` exposes a module-level `CHECKS: list[Check]`; the runner walks the
package with `pkgutil.iter_modules` and collects them. A shared `registry.py` would be the one
file every author has to edit, which is a merge conflict by construction the moment more than
one person is adding checks — and the conflict lands on the list that decides what gates the
build, which is the worst possible place for a bad resolution.

**`applies()` is not a formality.** A corpus with no `journeys/` must SKIP the journey checks
with a line saying so, never fail. Preserving fail-the-commit behaviour where the ground
exists while degrading honestly where it does not is the whole point of a portable validator:
a red build over a directory a project deliberately does not have teaches people to pass
`--no-verify`.

Stdlib only.
"""

from __future__ import annotations

import contextlib
import importlib
import pkgutil
import traceback
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .config import KnowledgeBase

# Most severe first. The order IS the vocabulary: `error` fails a build, `warning` is a real
# problem nobody has to fix this minute, `advisory` is a note worth reading once.
LEVELS: tuple[str, ...] = ("error", "warning", "advisory")
FAIL_LEVEL = "error"


def level_rank(level: str) -> int:
    """Severity as a sortable number. An unknown level sorts last rather than throwing."""
    try:
        return LEVELS.index(level)
    except ValueError:
        return len(LEVELS)


@dataclass
class Finding:
    """One thing that is wrong, said once, in a form a person can act on.

    `message` states what is wrong in the present tense. `hint` says how a human fixes it, in
    one sentence. `command` is a runnable line when one exists — a finding that names its own
    fix is the difference between a gate people route around and a gate they use.
    """

    level: str
    message: str
    path: Path | None = None
    line: int | None = None
    hint: str | None = None
    command: str | None = None

    def where(self, relative_to: Path | None = None) -> str:
        """`path:line`, made relative when that is shorter and still unambiguous."""
        if self.path is None:
            return ""
        p = self.path
        if relative_to is not None:
            # A path outside the repo keeps its absolute form rather than raising: a finding
            # about a file somewhere else is still a finding worth printing.
            with contextlib.suppress(ValueError):
                p = p.relative_to(relative_to)
        return f"{p}:{self.line}" if self.line else str(p)

    def as_dict(self, relative_to: Path | None = None) -> dict[str, Any]:
        return {
            "level": self.level,
            "message": self.message,
            "path": self.where(relative_to) or None,
            "line": self.line,
            "hint": self.hint,
            "command": self.command,
        }


@runtime_checkable
class Check(Protocol):
    """A validator over a knowledge base.

    `name` is kebab-case and STABLE — it is what `--only` takes and what a project writes in
    `disabled_checks`.

    `mandatory` is optional, and a check that sets it True cannot be switched off from a
    project's configuration. It exists for the checks whose guarantee is not the project's to
    remove — `tracker-clients` keeps hand-rolled tracker clients out of the command tier in
    every receiving repository.
    """

    name: str
    title: str
    description: str

    def applies(self, kb: KnowledgeBase) -> bool: ...

    def run(self, kb: KnowledgeBase) -> list[Finding]: ...


CHECKS_PACKAGE = "fleet_knowledge.checks"


def discover(package: str = CHECKS_PACKAGE) -> list[Check]:
    """Every check under `package`, sorted by name.

    A module that fails to import is not silently skipped: it comes back as a check whose
    single finding is the import error. A validator that vanishes because of a typo is the
    failure mode this whole layer exists to prevent, and a quiet zero is indistinguishable
    from a clean run.
    """
    try:
        pkg = importlib.import_module(package)
    except ModuleNotFoundError:
        return []
    found: list[Check] = []
    for info in pkgutil.iter_modules(list(getattr(pkg, "__path__", []))):
        if info.name.startswith("_"):
            continue
        module_name = f"{package}.{info.name}"
        try:
            module = importlib.import_module(module_name)
        except Exception:  # noqa: BLE001 — a broken module must be reported, never dropped
            found.append(_BrokenModule(info.name, traceback.format_exc()))
            continue
        checks = getattr(module, "CHECKS", None)
        if not checks:
            continue
        found.extend(checks)
    return sorted(found, key=lambda c: c.name)


@dataclass
class _BrokenModule:
    """A checks module that would not import, surfaced as a failing check of its own."""

    module: str
    detail: str

    def __post_init__(self) -> None:
        self.name = f"broken:{self.module}"
        self.title = f"checks module `{self.module}` does not import"
        self.description = (
            "A module under fleet_knowledge/checks/ raised on import, so whatever it validates "
            "is not being validated. Reported as a failure rather than skipped, because a "
            "validator that disappears looks exactly like a clean run."
        )

    def applies(self, kb: KnowledgeBase) -> bool:
        return True

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        return [
            Finding(
                level="error",
                message=f"checks module `{self.module}` failed to import:\n{self.detail.rstrip()}",
                hint="Fix the import error, or remove the module if it is no longer wanted.",
            )
        ]


@dataclass
class CheckResult:
    """What running one check produced.

    `status` is one of `ok`, `noted`, `failed`, `skipped` or `disabled`. **`noted` and `failed`
    are different questions**: `failed` means something GATES (an error, or a warning under
    `--strict`), `noted` means there are findings worth reading that stop nothing. Collapsing
    the two made every advisory-only check print FAIL beside exit code 0.
    """

    check: Check
    status: str
    findings: list[Finding] = field(default_factory=list)
    reason: str = ""

    @property
    def failed(self) -> bool:
        return any(f.level == FAIL_LEVEL for f in self.findings)

    def as_dict(self, relative_to: Path | None = None) -> dict[str, Any]:
        return {
            "name": self.check.name,
            "title": self.check.title,
            "status": self.status,
            "reason": self.reason or None,
            "findings": [f.as_dict(relative_to) for f in self.findings],
        }


class UnknownCheckError(ValueError):
    """`--only` named a check that does not exist."""


class DisabledCheckError(ValueError):
    """`disabled_checks` names no installed check, or one that may not be switched off."""


def some_are_mandatory(checks: Sequence[Check]) -> set[str]:
    """The names of the checks a project's configuration may not switch off."""
    return {c.name for c in checks if getattr(c, "mandatory", False)}


def validate_disabled(checks: Sequence[Check], disabled: Iterable[str]) -> None:
    """Refuse a `disabled_checks` entry that matches nothing, or that may not be disabled.

    A name that matches no check is a typo or a renamed check, and either way the project
    believes a gate is off while it still runs. Silently ignoring the entry would leave that
    false belief in place, which is the one failure a switch must not have. Mandatory checks
    are refused because the promise they carry is not the project's to remove.
    """
    disabled = list(disabled)
    if not disabled:
        return
    names = {c.name for c in checks}
    mandatory = some_are_mandatory(checks)
    locked = [n for n in disabled if n in mandatory]
    unknown = [n for n in disabled if n not in names]
    problems: list[str] = []
    if locked:
        problems.append(f"{', '.join(locked)} cannot be disabled — it is mandatory and always runs")
    if unknown:
        available = ", ".join(sorted(names)) or "none — no checks are installed"
        problems.append(f"unknown check(s): {', '.join(unknown)}. Available: {available}")
    if problems:
        raise DisabledCheckError("`disabled_checks` in this project's configuration: " + "; ".join(problems))


def select(checks: Sequence[Check], only: Iterable[str] | None) -> list[Check]:
    """The checks `only` names, in the order given. Raises rather than running a subset.

    Silently ignoring an unknown name would let a typo in a CI invocation report success over
    nothing at all.
    """
    if not only:
        return list(checks)
    by_name = {c.name: c for c in checks}
    wanted = list(only)
    missing = [n for n in wanted if n not in by_name]
    if missing:
        known = ", ".join(sorted(by_name)) or "none — no checks are installed"
        raise UnknownCheckError(f"unknown check(s): {', '.join(missing)}. Available: {known}")
    return [by_name[n] for n in wanted]


def run_checks(
    kb: KnowledgeBase,
    checks: Sequence[Check] | None = None,
    *,
    only: Iterable[str] | None = None,
    min_level: str = "advisory",
    strict: bool = False,
) -> list[CheckResult]:
    """Run each applicable check and collect its findings.

    A check that raises is reported as a failure naming the traceback rather than taking the
    run down with it: one broken validator must not hide the verdict of the other twenty.
    """
    available = list(checks) if checks is not None else discover()
    validate_disabled(available, kb.config.disabled_checks)
    threshold = level_rank(min_level)
    results: list[CheckResult] = []
    for check in select(available, only):
        if check.name in kb.config.disabled_checks:
            results.append(CheckResult(check, "disabled", reason="turned off in this project's configuration"))
            continue
        try:
            if not check.applies(kb):
                results.append(CheckResult(check, "skipped", reason="not applicable to this knowledge base"))
                continue
            findings = [f for f in check.run(kb) if level_rank(f.level) <= threshold]
        except Exception:  # noqa: BLE001 — one broken check must not hide the other verdicts
            results.append(
                CheckResult(
                    check,
                    "failed",
                    [
                        Finding(
                            level="error",
                            message=f"check `{check.name}` raised:\n{traceback.format_exc().rstrip()}",
                            hint="This is a bug in the check itself, not necessarily in the corpus.",
                        )
                    ],
                )
            )
            continue
        results.append(CheckResult(check, result_status(findings, strict=strict), findings))
    return results


def gates(findings: Iterable[Finding], *, strict: bool = False) -> bool:
    """Does anything here actually stop the build? The one predicate for that question."""
    return any(f.level == FAIL_LEVEL or (strict and f.level == "warning") for f in findings)


def result_status(findings: Sequence[Finding], *, strict: bool = False) -> str:
    """`failed` when something gates, `noted` when there are findings that do not, else `ok`.

    Any finding at all used to read `failed`, so a check emitting only advisories printed
    FAIL while `exit_code` correctly returned 0 - the report contradicted the exit status on
    every clean run. `requirement-registers` alone emits 293 advisories on this corpus, so the
    headline verdict was wrong far more often than it was right.
    """
    if gates(findings, strict=strict):
        return "failed"
    return "noted" if findings else "ok"


def exit_code(results: Sequence[CheckResult], *, strict: bool = False) -> int:
    """0 when nothing gates, 1 when something does. `strict` also gates on warnings."""
    return 1 if any(gates(r.findings, strict=strict) for r in results) else 0


# ─────────────────────────── rendering ───────────────────────────

_MARK = {"ok": "ok", "failed": "FAIL", "noted": "note", "skipped": "skip", "disabled": "off"}


def format_results(results: Sequence[CheckResult], *, relative_to: Path | None = None, verbose: bool = False) -> str:
    """A report a person reads top to bottom: the verdict per check, then what to do.

    Passing, skipped and disabled checks are one line each unless `verbose` — a wall of green
    is how a real failure gets scrolled past.
    """
    lines: list[str] = []
    for r in results:
        mark = _MARK.get(r.status, r.status)
        if r.status in ("ok", "skipped", "disabled") and not verbose:
            suffix = f" — {r.reason}" if r.reason else ""
            lines.append(f"  {mark:<4} {r.check.name}{suffix}")
            continue
        lines.append(f"  {mark:<4} {r.check.name} — {r.check.title}")
        for f in r.findings:
            where = f.where(relative_to)
            head = f"{where}: " if where else ""
            lines.append(f"       [{f.level}] {head}{f.message}")
            if f.hint:
                lines.append(f"              fix: {f.hint}")
            if f.command:
                lines.append(f"              run: {f.command}")
    counts = {s: sum(1 for r in results if r.status == s) for s in ("ok", "failed", "noted", "skipped", "disabled")}
    findings = sum(len(r.findings) for r in results)
    lines.append("")
    lines.append(
        f"{len(results)} check(s): {counts['ok']} passed, {counts['failed']} failed, "
        f"{counts['noted']} noted, {counts['skipped']} skipped, {counts['disabled']} disabled "
        f"— {findings} finding(s)"
    )
    if counts["noted"] and not counts["failed"]:
        lines.append("`noted` = findings that do not gate. Nothing here fails the build.")
    return "\n".join(lines)
