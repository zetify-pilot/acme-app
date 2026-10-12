"""The neuter check — one script the implementer and the verifier both run.

A test nobody has watched fail is not evidence. The check is the same every time: take the
fix away, run the test the claim names, and require it to go **red**; then put the fix back
and require it green again. A test that stays green with its fix reverted closes nothing —
it is a description of a test, not a test.

This is the verifier's V2 (the neuter check) and the implementer's pre-handoff proof, in one
file so the two cannot drift. It used to live only as a bash snippet in the verifier command
and nowhere at all in the implement commands, and the measurement is blunt: of 192 verify
rejections in seven days, **30 were a test that stayed green with the fix reverted**. The
implementer is the one party who can run the check while it is still cheap.

WHAT IT DOES, FROM A LEDGER

  * **Neuter (`tests`)** — for each entry: run the test on the current tree (it must be
    green), reverse-apply the diff for the files the fix landed in, run it again (it must be
    red), restore the diff, run it a third time (it must be green), and assert the tree came
    back byte-for-byte. The three runs are the whole round trip the `negative-control` rubric
    demands: Test, Mutation, Result, Restored.
  * **Count (`scopes`)** — for each scoped claim (*"wherever asserted"*, *"all N references"*),
    find every site the pattern matches, mark which ones the diff touches, and fail on any
    site left uncovered. This is the denominator check: `landed in 2 of 3 sites` is the
    commonest shape of an incomplete fix and it is always a claim nobody counted.

THE LEDGER is JSON, read from `--ledger <file>` or stdin:

    {
      "tests": [
        {"id": "1", "name": "TestPinPrecheckUsesResolvedIdentity",
         "revert": ["internal/pinning/pinning.go"],
         "run": ["make", "test-one", "T=TestPinPrecheckUsesResolvedIdentity"]}
      ],
      "scopes": [
        {"id": "2", "claim": "correct the overclaim wherever asserted",
         "pattern": "supports alpha", "paths": ["docs", "src"],
         "allow": ["docs/legacy.md:12"], "expect": 4}
      ]
    }

`revert` names the FIX files (never the test file: reverting the test removes the test). It is
the pathspec the reverse patch is built from, so a fix spread across files lists them all.
`run` is an argv list, or a string the script splits with shell-like quoting; it runs in the
checkout with the base ref's fix present and absent. `pattern` is an extended regex; `paths`
narrow the search; `expect`, when given, is the denominator the ledger claims, and a mismatch
is a failure.

Exit status is 0 only when every named test was green→red→green and every scoped site is
covered. Any other outcome is a refusal to hand off, named line by line.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2

#: `@@ -old +new @@`, capturing the new-file start and (optionally) length. `--unified=0`
#: gives one hunk per changed run, so a site is covered exactly when its line is in one.
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
#: A `git grep` line: `<path>:<line>:<text>`. The text may contain colons; the path rarely.
_GREP = re.compile(r"^(?P<path>.+?):(?P<line>\d+):(?P<text>.*)$", re.DOTALL)


class LedgerError(ValueError):
    """The ledger is not the shape this check can run — a usage error, not a red test."""


@dataclass(frozen=True)
class TestClaim:
    """One ledger line whose proof is a test: neuter it and watch it go red."""

    id: str
    name: str
    revert: tuple[str, ...]
    run: tuple[str, ...]


@dataclass(frozen=True)
class ScopeClaim:
    """One ledger line whose proof is a count: every matching site must be covered."""

    id: str
    claim: str
    pattern: str
    paths: tuple[str, ...]
    allow: frozenset[str]
    expect: int | None


@dataclass
class Report:
    """The running tally, printed as the check goes and summarized at the end."""

    neutered: list[str]
    stayed_green: list[str]
    failures: list[str]

    def ok(self) -> bool:
        return not self.stayed_green and not self.failures


def _git(root: Path, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 — fixed argv, no shell
        ["git", "-C", str(root), "-c", "core.quotepath=false", *args],
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_argv(argv: tuple[str, ...], root: Path, timeout: int) -> int:
    """A test command's exit status, with a timeout named as its own status."""
    try:
        done = subprocess.run(  # noqa: S603 — argv from the ledger, no shell
            list(argv),
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"    ! could not run {argv!r}: {exc}", file=sys.stderr)
        return 124
    tail = (done.stdout + done.stderr).strip().splitlines()[-5:]
    for line in tail:
        print(f"      | {line}")
    return done.returncode


def _require_clean(root: Path, paths: tuple[str, ...]) -> None:
    """The reverse patch only applies to a tree that still holds the fix; refuse otherwise."""
    status = _git(root, "status", "--porcelain", "--", *paths).stdout.strip()
    if status:
        raise LedgerError(
            f"the worktree is dirty over the paths to neuter ({paths!r}); commit or stash first:\n{status}"
        )


def _diff_lines(root: Path, base: str, paths: tuple[str, ...]) -> dict[str, list[tuple[int, int]]]:
    """Per new-file path, the half-open line ranges the diff adds or changes at HEAD."""
    diff = _git(root, "diff", "--unified=0", "--no-color", "--no-ext-diff", f"{base}...HEAD", "--", *paths)
    if diff.returncode != 0:
        raise LedgerError(f"`git diff {base}...HEAD -- {paths}` failed: {diff.stderr.strip()}")
    covered: dict[str, list[tuple[int, int]]] = {}
    current: str | None = None
    for line in diff.stdout.splitlines():
        if line.startswith("+++ b/"):
            current = line[len("+++ b/") :]
            covered.setdefault(current, [])
        elif line.startswith("+++ ") and line[4:].strip() != "/dev/null":
            current = None
        elif current is not None and (match := _HUNK.match(line)):
            start = int(match.group(1))
            length = int(match.group(2) or "1")
            if length:
                covered[current].append((start, start + length - 1))
    return covered


def check_test(root: Path, base: str, claim: TestClaim, timeout: int, report: Report) -> None:
    """The full round trip: green at HEAD, red with the fix reverted, green restored."""
    label = f"test {claim.id}: {claim.name}"
    try:
        _require_clean(root, claim.revert)
        patch = _git(root, "diff", "--binary", "--no-ext-diff", f"{base}...HEAD", "--", *claim.revert).stdout
        if not patch.strip():
            report.failures.append(f"{label}: nothing in {claim.revert!r} differs from `{base}` — nothing to neuter")
            print(f"  FAIL {label}: no diff over {claim.revert!r} against {base}")
            return

        print(f"  .. {label}: baseline (must be green)")
        if _run_argv(claim.run, root, timeout) != 0:
            report.failures.append(f"{label}: the test is not green at HEAD — fix it before neutering")
            print(f"  FAIL {label}: baseline run was not green")
            return

        applied = _git(root, "apply", "-R", input_text=patch)
        if applied.returncode != 0:
            report.failures.append(f"{label}: could not revert the fix: {applied.stderr.strip()}")
            print(f"  FAIL {label}: reverse-apply failed")
            return
        print(f"  .. {label}: neutered (must be red)")
        # The restore runs in `finally` so an interrupt or an error still puts the fix back.
        neutered_rc = 124
        restored: subprocess.CompletedProcess[str]
        try:
            neutered_rc = _run_argv(claim.run, root, timeout)
        finally:
            restored = _git(root, "apply", input_text=patch)
        if restored.returncode != 0:
            report.failures.append(
                f"{label}: COULD NOT RESTORE the fix — run `git apply` by hand: {restored.stderr.strip()}"
            )
            print(f"  FAIL {label}: restore failed; the tree is left neutered", file=sys.stderr)
            return
        still = _git(root, "status", "--porcelain", "--", *claim.revert).stdout.strip()
        if still:
            report.failures.append(f"{label}: the tree did not come back clean:\n{still}")
            print(f"  FAIL {label}: tree not restored")
            return
        if neutered_rc == 0:
            report.stayed_green.append(label)
            print(f"  FAIL {label}: still GREEN with the fix reverted — the test proves nothing")
            return
        if neutered_rc == 124:
            report.failures.append(f"{label}: the neutered run timed out — not a clean red")
            print(f"  FAIL {label}: neutered run timed out")
            return
        print(f"  .. {label}: restored (must be green)")
        if _run_argv(claim.run, root, timeout) != 0:
            report.failures.append(f"{label}: the test is not green again after restoring the fix")
            print(f"  FAIL {label}: restore run was not green")
            return
    except LedgerError as exc:
        report.failures.append(f"{label}: {exc}")
        print(f"  FAIL {label}: {exc}")
        return
    report.neutered.append(label)
    print(f"  PASS {label}: green → red on revert → green restored")


def check_scope(root: Path, base: str, claim: ScopeClaim, report: Report) -> None:
    """Every site the pattern matches must be touched by the diff (or explicitly allowed)."""
    label = f"scope {claim.id}: {claim.claim}"
    grep = _git(root, "grep", "-n", "-E", "-e", claim.pattern, "--", *claim.paths)
    if grep.returncode > 1:
        report.failures.append(f"{label}: grep failed: {grep.stderr.strip()}")
        print(f"  FAIL {label}: grep failed")
        return
    sites: list[tuple[str, int]] = []
    for line in grep.stdout.splitlines():
        if match := _GREP.match(line):
            sites.append((match.group("path"), int(match.group("line"))))
    try:
        covered = _diff_lines(root, base, claim.paths)
    except LedgerError as exc:
        report.failures.append(f"{label}: {exc}")
        print(f"  FAIL {label}: {exc}")
        return

    def is_covered(path: str, line: int) -> bool:
        return any(start <= line <= end for start, end in covered.get(path, []))

    uncovered = [
        f"{path}:{line}" for path, line in sites if not is_covered(path, line) and f"{path}:{line}" not in claim.allow
    ]
    denominator = len(sites)
    covered_n = denominator - len(uncovered)
    print(f"  {'PASS' if not uncovered else 'FAIL'} {label}: {denominator} site(s), {covered_n} covered")
    for site in uncovered:
        print(f"      uncovered: {site}")
    if claim.expect is not None and claim.expect != denominator:
        report.failures.append(f"{label}: ledger claims {claim.expect} site(s); the pattern matches {denominator}")
        print(f"  FAIL {label}: expected {claim.expect}, matched {denominator}")
        return
    if uncovered:
        report.failures.append(f"{label}: {len(uncovered)} uncovered site(s): {', '.join(uncovered)}")
        return
    report.neutered.append(label)


def _as_str_tuple(value: Any, where: str) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return tuple(value)
    raise LedgerError(f"{where} must be a string or a list of strings")


def _as_argv(value: Any, where: str) -> tuple[str, ...]:
    if isinstance(value, str):
        argv = tuple(shlex.split(value))
        if not argv:
            raise LedgerError(f"{where} is an empty command")
        return argv
    return _as_str_tuple(value, where)


def load_ledger(text: str) -> tuple[list[TestClaim], list[ScopeClaim]]:
    """Parse and validate the ledger — a shape error is usage, not a red check."""
    try:
        raw: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LedgerError(f"the ledger is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise LedgerError("the ledger must be a JSON object with `tests` and/or `scopes`")

    tests: list[TestClaim] = []
    for i, entry in enumerate(raw.get("tests", []) or []):
        if not isinstance(entry, dict):
            raise LedgerError(f"tests[{i}] must be an object")
        tests.append(
            TestClaim(
                id=str(entry.get("id", i + 1)),
                name=str(entry.get("name", "")),
                revert=_as_str_tuple(entry.get("revert"), f"tests[{i}].revert"),
                run=_as_argv(entry.get("run"), f"tests[{i}].run"),
            )
        )
    scopes: list[ScopeClaim] = []
    for i, entry in enumerate(raw.get("scopes", []) or []):
        if not isinstance(entry, dict):
            raise LedgerError(f"scopes[{i}] must be an object")
        expect = entry.get("expect")
        if expect is not None and not isinstance(expect, int):
            raise LedgerError(f"scopes[{i}].expect must be an integer")
        scopes.append(
            ScopeClaim(
                id=str(entry.get("id", i + 1)),
                claim=str(entry.get("claim", "")),
                pattern=str(entry.get("pattern", "")),
                paths=_as_str_tuple(entry.get("paths", []), f"scopes[{i}].paths"),
                allow=frozenset(_as_str_tuple(entry.get("allow", []), f"scopes[{i}].allow")),
                expect=expect,
            )
        )
    if not tests and not scopes:
        raise LedgerError("the ledger names no tests and no scopes — there is nothing to check")
    for claim in tests:
        if not claim.revert:
            raise LedgerError(f"tests {claim.id}: `revert` must name at least one fix path")
    for scoped in scopes:
        if not scoped.pattern:
            raise LedgerError(f"scopes {scoped.id}: `pattern` is required")
    return tests, scopes


def _read_ledger(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise LedgerError(f"cannot read ledger {path!r}: {exc}") from exc


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="neuter_check.py",
        description="Revert the fix, watch every named test go red, restore it, and count every scoped site.",
    )
    parser.add_argument("--base", required=True, help="the ref the fix branches from (e.g. origin/main)")
    parser.add_argument("--ledger", default="-", help="the JSON ledger; `-` (default) reads stdin")
    parser.add_argument("--workdir", default=".", help="the checkout to run in (default: cwd)")
    parser.add_argument("--timeout", type=int, default=900, help="seconds allowed per test run (default: 900)")
    parser.add_argument("--only", choices=("tests", "scopes"), help="run only one half of the ledger")
    parser.add_argument("--json", action="store_true", help="print the verdict as JSON as well")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    root = Path(args.workdir).resolve()
    try:
        tests, scopes = load_ledger(_read_ledger(args.ledger))
    except LedgerError as exc:
        print(f"neuter_check: {exc}", file=sys.stderr)
        return EXIT_USAGE

    if _git(root, "rev-parse", "--git-dir").returncode != 0:
        print(f"neuter_check: {root} is not a git checkout", file=sys.stderr)
        return EXIT_USAGE

    report = Report(neutered=[], stayed_green=[], failures=[])
    if args.only != "scopes":
        for claim in tests:
            check_test(root, args.base, claim, args.timeout, report)
    if args.only != "tests":
        for scope in scopes:
            check_scope(root, args.base, scope, report)

    verdict = "ok" if report.ok() else "fail"
    print(
        f"neuter_check: {len(report.neutered)} checked, {len(report.stayed_green)} stayed green, "
        f"{len(report.failures)} failure(s) — {verdict}"
    )
    if args.json:
        print(
            json.dumps(
                {
                    "verdict": verdict,
                    "checked": report.neutered,
                    "stayed_green": report.stayed_green,
                    "failures": report.failures,
                }
            )
        )
    return EXIT_OK if report.ok() else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
