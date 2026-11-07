#!/usr/bin/env python3
"""Compose and gate the `## Files` scope manifest of a keyed PR.

WHY THIS EXISTS. The audit command's Step 6 opens a throwaway record PR on a keyed branch.
The consuming repository's scope-manifest guard fails a tracker-keyed PR **closed** when its
body carries no parseable `## Files` manifest, so such a PR is born red, owned by an audit
issue already moved to Done, and left for a human to repair — six of them on 2026-09-24 alone.

The rule was first added to Step 6 as prose. Audit PRs opened *after* that fix still skipped
it (#12059, #12117): a rule the model must remember is not a rule that binds. The same held
for agent-opened bug/task/PRD PRs (#18037, #18039, #18063, #18065, #18086), which the
`PRD Verified` scope-manifest check failed for the same reason. The manifest has to be
produced mechanically. So the body is composed HERE, from the branch's own diff
(`git diff --name-only <base>...HEAD`), and `gate`/`arm` re-read the LIVE PR body and the
diff and refuse to arm auto-merge unless the manifest it carries matches — arming a
manifest-less PR is not expressible through this script.

  * `compose` — write the full PR body (`Refs <KEY>` + the generated `## Files`
    manifest) to stdout or `--out`.
  * `ensure`  — splice a current `## Files` manifest into ANY body — a local `--body-file`
    or a live `--pr` — replacing a stale section and never duplicating it, so any PR-opening
    step generates the manifest mechanically.
  * `gate`    — read the live PR body via `gh`, compare its manifest with the diff, and
    exit non-zero on a missing or disagreeing manifest.
  * `arm`     — `gate`, then `gh pr merge <pr> --auto --squash` only when it passed.

The parser mirrors the consuming guard's accepted headings and matching rules; the
guard remains the authority and this is its mechanical pre-flight, not a replacement.

Usage:
  python3 knowledge/scripts/pr_scope_manifest.py compose --refs <KEY> [--base origin/main]
  python3 knowledge/scripts/pr_scope_manifest.py ensure  --pr 1234 [--base origin/main]
  python3 knowledge/scripts/pr_scope_manifest.py ensure  --body-file <body> [--out <out>]
  python3 knowledge/scripts/pr_scope_manifest.py gate --pr 1234 [--base origin/main]
  python3 knowledge/scripts/pr_scope_manifest.py arm  --pr 1234 [--base origin/main]

Stdlib only, like every shipped script.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_BASE = "origin/main"

# Headings that open a declared file manifest — the guard's closed set, mirrored so a
# body this passes is a body the guard accepts.
MANIFEST_HEADINGS = frozenset(
    {
        "files",
        "changed files",
        "files changed",
        "files touched",
        "files modified",
        "changed paths",
        "file manifest",
        "scope manifest",
    }
)

_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_BACKTICK_RE = re.compile(r"`([^`]+)`")
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
_EXT_RE = re.compile(r"\.[A-Za-z0-9]+$")
# The tracker teams this workspace uses; the guard's set, kept in step on purpose.
_TEAM_KEY_RE = re.compile(r"\b(?:ENG|ZTE|CUS|ZET)-\d+\b")


class ManifestError(RuntimeError):
    """A prerequisite failed: git/gh could not be read, or its answer was unusable."""


@dataclass
class ScopeResult:
    """What a PR body declared and how the diff disagrees with it."""

    declared: bool
    missing_required: bool = False
    issue: str | None = None
    manifest_entries: list[str] = field(default_factory=list)
    undeclared: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)


# ── reading the body (mirrors scripts/validate_pr_scope_manifest.py) ──────────────


def _sections(body: str) -> list[tuple[str, list[str]]]:
    """(heading_text, following_lines) for every markdown heading in `body`."""
    lines = (body or "").splitlines()
    sections: list[tuple[str, list[str]]] = []
    heading_idx: int | None = None
    heading_text = ""
    for idx, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            if heading_idx is not None:
                sections.append((heading_text, lines[heading_idx + 1 : idx]))
            heading_idx = idx
            heading_text = m.group(2).strip()
        elif heading_idx is None:
            continue
    if heading_idx is not None:
        sections.append((heading_text, lines[heading_idx + 1 :]))
    return sections


def _path_candidates(section_lines: list[str], changed_files: frozenset[str] = frozenset()) -> list[str]:
    """Every plausible path token on the section's declaration lines, deduped.

    Only list items and fenced code blocks count; prose inside the section that merely
    names a path is not a declaration. `changed_files` disambiguates the one shape a
    manifest cannot express on its own: a bare root filename with no extension.
    """
    found: list[str] = []
    seen: set[str] = set()

    def add(raw: str, *, allow_spaces: bool) -> None:
        token = raw.strip().strip("`").strip()
        token = token.rstrip(":`").strip()
        if not token or token.startswith(("/", "#", "!", "http://", "https://")):
            return
        if ".." in token.split("/"):
            return
        token = token.removeprefix("./")
        if not allow_spaces and (" " in token or "\t" in token):
            return
        if "/" not in token and not _EXT_RE.search(token) and token not in changed_files:
            return
        if token in seen:
            return
        seen.add(token)
        found.append(token)

    in_fence = False
    for line in section_lines:
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            for tok in stripped.split():
                add(tok, allow_spaces=False)
            continue
        item = _LIST_ITEM_RE.match(line)
        if not item:
            continue
        for backticked in _BACKTICK_RE.findall(line):
            add(backticked, allow_spaces=True)
        first = item.group(1).strip().split()
        add(first[0] if first else "", allow_spaces=False)
    return found


def parse_manifest(body: str, changed_files: list[str] | None = None) -> list[str] | None:
    """The declared file entries, or None when the body declares no manifest."""
    changed = frozenset(changed_files or ())
    for heading, section_lines in _sections(body):
        if heading.strip().lower() in MANIFEST_HEADINGS:
            entries = _path_candidates(section_lines, changed)
            if entries:
                return entries
    return None


def names_issue(title: str, body: str) -> str | None:
    """The first tracker issue key the PR names, or None. Advisory context only."""
    m = _TEAM_KEY_RE.search(title or "")
    if m:
        return m.group(0)
    m = _TEAM_KEY_RE.search(body or "")
    return m.group(0) if m else None


def _covered(changed: str, entry: str) -> bool:
    """A changed file is covered by an entry: exact match, or a directory prefix."""
    if entry.endswith("/"):
        return changed == entry.rstrip("/") or changed.startswith(entry)
    return changed == entry


def evaluate(title: str, body: str, changed_files: list[str]) -> ScopeResult:
    """Pure verdict: match the declared manifest against the diff, both ways."""
    files = list(changed_files)
    entries = parse_manifest(body, files)
    issue = names_issue(title, body)
    if entries is None:
        return ScopeResult(
            declared=False,
            missing_required=bool(issue),
            issue=issue,
            changed_files=files,
        )
    undeclared = sorted(f for f in files if not any(_covered(f, e) for e in entries))
    stale = sorted(e for e in entries if not any(_covered(f, e) for f in files))
    return ScopeResult(
        declared=True,
        issue=issue,
        manifest_entries=entries,
        undeclared=undeclared,
        stale=stale,
        changed_files=files,
    )


def verdict_failure(result: ScopeResult, issue: str | None) -> str:
    """The refusal text for a gate that must fail closed."""
    ctx = f" (names {issue})" if issue else ""
    if result.missing_required or not result.declared:
        lines = [
            f"PR scope manifest required{ctx}: the PR body carries no parseable `## Files` "
            "manifest, and a tracker-keyed record PR without one is born red<!-- home --> (ENG-11269)<!-- /home -->.",
            "Fix: compose the body with `pr_scope_manifest.py compose --refs <KEY>` instead of writing it by hand.",
        ]
        if result.changed_files:
            lines.append("The diff carries these changed files:")
            lines.extend(f"  - {f}" for f in result.changed_files)
        return "\n".join(lines)
    lines = [f"PR scope manifest{ctx} disagrees with the PR diff:"]
    if result.undeclared:
        lines.append(f"  changed but not declared ({len(result.undeclared)}):")
        lines.extend(f"    - {f}" for f in result.undeclared)
    if result.stale:
        lines.append(f"  declared but not changed ({len(result.stale)}):")
        lines.extend(f"    - {f}" for f in result.stale)
    lines.append("Fix: recompose the body with `pr_scope_manifest.py compose --refs <KEY>`.")
    return "\n".join(lines)


# ── composing the body ────────────────────────────────────────────────────────────


def changed_files(base: str, repo: Path | None = None) -> list[str]:
    """The branch's changed files, three-dot, the way the push command computes them."""
    proc = subprocess.run(  # noqa: S603 — fixed argv, no shell
        ["git", "diff", "--name-only", "-z", f"{base}...HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise ManifestError(f"git diff --name-only {base}...HEAD failed: {proc.stderr.strip()}")
    return [f for f in proc.stdout.split("\0") if f]


def format_manifest(files: list[str]) -> str:
    """The canonical `## Files` block: backticked bullets, one path per line."""
    lines = ["## Files", ""]
    lines.extend(f"- `{f}`" for f in files)
    return "\n".join(lines)


def compose_body(refs: str, files: list[str], note: str = "") -> str:
    """The full record-PR body: a bare `Refs` link (never a closing keyword) + manifest."""
    parts = [f"Refs {refs}"]
    if note.strip():
        parts.extend(["", note.strip()])
    parts.extend(["", format_manifest(files), ""])
    return "\n".join(parts)


def _without_manifest_sections(body: str) -> str:
    """`body` with every declared manifest heading, and its section, removed."""
    lines = (body or "").splitlines()
    out: list[str] = []
    skipping = False
    for line in lines:
        m = _HEADING_RE.match(line)
        if m:
            skipping = m.group(2).strip().lower() in MANIFEST_HEADINGS
            if skipping:
                continue
        if skipping:
            continue
        out.append(line)
    return "\n".join(out)


def ensure_body(body: str, files: list[str]) -> str:
    """`body` carrying a current, canonical `## Files` manifest for `files`.

    Replaces an existing manifest section (never appending a second) or adds one when the
    body has none, leaving the authored prose alone — the deterministic generator an
    unsuspecting PR-opening step runs so a keyed PR is never born manifest-less.
    Idempotent by construction.
    """
    prose = _without_manifest_sections(body).rstrip()
    manifest = format_manifest(files)
    return f"{prose}\n\n{manifest}\n" if prose else f"{manifest}\n"


# ── the `gh` half ────────────────────────────────────────────────────────────────


def read_pr(pr: str) -> tuple[str, str]:
    """The LIVE (title, body) of a PR, re-read from the API through `gh`."""
    proc = subprocess.run(  # noqa: S603 — fixed argv, no shell
        ["gh", "pr", "view", pr, "--json", "title,body"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise ManifestError(f"gh pr view {pr} failed: {(proc.stderr or 'no stderr').strip()[:300]}")
    payload: Any = json.loads(proc.stdout)
    title = payload.get("title") if isinstance(payload, dict) else None
    body = payload.get("body") if isinstance(payload, dict) else None
    if not isinstance(title, str) or not title.strip():
        raise ManifestError(f"gh pr view {pr} returned no non-empty title")
    return title, body if isinstance(body, str) else ""


def gate(pr: str, base: str, repo: Path | None = None) -> ScopeResult:
    """Re-read the PR body and the diff and return the verdict. Raises on a failed read."""
    title, body = read_pr(pr)
    return evaluate(title, body, changed_files(base, repo))


def edit_body(pr: str, body: str) -> None:
    """Write the body via the REST PATCH — not `gh pr edit`.

    `gh pr edit` goes over GraphQL, whose `updatePullRequest` payload carries sub-queries
    (`login`, `name`, `slug`) needing `read:org`, a scope the fleet's keyring token does not
    carry; the REST endpoint needs only `repo`. The body rides stdin — it is long, and argv
    is world-readable. The same reason and shape as `gh_closing_keyword_ensure.edit_body`,
    whose PR-body write needs only `repo` for the same reason.
    """
    payload = json.dumps({"body": body})
    subprocess.run(  # noqa: S603 — fixed argv, no shell
        ["gh", "api", f"repos/{{owner}}/{{repo}}/pulls/{pr}", "-X", "PATCH", "--input", "-"],
        input=payload,
        text=True,
        check=True,
    )


# ── cli ──────────────────────────────────────────────────────────────────────────


def _cmd_compose(args: argparse.Namespace) -> int:
    try:
        files = changed_files(args.base)
    except ManifestError as exc:
        print(f"pr_scope_manifest: {exc}", file=sys.stderr)
        return 2
    if not files:
        print(
            f"pr_scope_manifest: `{args.base}...HEAD` carries no changed file — a record PR "
            "must change the record; refusing to compose a manifest-less body",
            file=sys.stderr,
        )
        return 2
    note = args.note or ""
    if args.note_file:
        try:
            note = Path(args.note_file).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"pr_scope_manifest: cannot read --note-file: {exc}", file=sys.stderr)
            return 2
    body = compose_body(args.refs, files, note)
    if args.out:
        Path(args.out).write_text(body, encoding="utf-8")
        print(f"pr_scope_manifest: composed {len(files)}-file manifest → {args.out}")
    else:
        sys.stdout.write(body)
    return 0


def _cmd_ensure(args: argparse.Namespace) -> int:
    try:
        files = changed_files(args.base)
    except ManifestError as exc:
        print(f"pr_scope_manifest: {exc}", file=sys.stderr)
        return 2
    if not files:
        print(
            f"pr_scope_manifest: `{args.base}...HEAD` carries no changed file — refusing to "
            "write an empty `## Files` manifest",
            file=sys.stderr,
        )
        return 2
    if args.pr and args.body_file:
        print("pr_scope_manifest: pass --pr or --body-file, not both", file=sys.stderr)
        return 2
    if args.pr:
        try:
            _, body = read_pr(args.pr)
        except (ManifestError, json.JSONDecodeError) as exc:
            print(f"pr_scope_manifest: {exc}", file=sys.stderr)
            return 2
        new_body = ensure_body(body, files)
        if new_body == body:
            print(f"PR #{args.pr}: `## Files` manifest already current for {len(files)} changed file(s)")
            return 0
        try:
            edit_body(args.pr, new_body)
        except subprocess.CalledProcessError as exc:
            print(
                f"PR #{args.pr}: PATCH failed: {(exc.stderr or 'no output').strip()[:300]}",
                file=sys.stderr,
            )
            return 1
        # Prove the write landed by re-reading: never report success on the composed text
        # alone (push.md step 5.5's self-heal rule, applied here).
        try:
            _, confirmed = read_pr(args.pr)
        except (ManifestError, json.JSONDecodeError) as exc:
            print(f"PR #{args.pr}: wrote the body but the read-back failed: {exc}", file=sys.stderr)
            return 1
        entries = parse_manifest(confirmed, files) or []
        if sorted(entries) != sorted(files):
            print(
                f"PR #{args.pr}: FAILED — after the edit the live body's `## Files` does not "
                f"match the diff ({len(files)} changed path(s))",
                file=sys.stderr,
            )
            return 1
        print(f"PR #{args.pr}: `## Files` manifest written from {len(files)} changed path(s)")
        return 0
    if args.body_file:
        try:
            body = Path(args.body_file).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"pr_scope_manifest: cannot read --body-file: {exc}", file=sys.stderr)
            return 2
        new_body = ensure_body(body, files)
        if args.out:
            Path(args.out).write_text(new_body, encoding="utf-8")
            print(f"pr_scope_manifest: `## Files` manifest written → {args.out}")
        else:
            sys.stdout.write(new_body)
        return 0
    print("pr_scope_manifest: pass --pr <n> or --body-file <path>", file=sys.stderr)
    return 2


def _report_failure(result: ScopeResult) -> None:
    print(f"pr_scope_manifest: {verdict_failure(result, result.issue)}", file=sys.stderr)


def _cmd_gate(args: argparse.Namespace) -> int:
    try:
        result = gate(args.pr, args.base)
    except (ManifestError, json.JSONDecodeError) as exc:
        print(f"pr_scope_manifest: {exc}", file=sys.stderr)
        return 2
    # The gate is the record-PR contract: a manifest must be present AND match.
    if not result.declared or result.undeclared or result.stale:
        _report_failure(result)
        return 1
    print(f"PR #{args.pr}: `## Files` manifest matches all {len(result.changed_files)} changed file(s) — gate passed")
    return 0


def _cmd_arm(args: argparse.Namespace) -> int:
    try:
        result = gate(args.pr, args.base)
    except (ManifestError, json.JSONDecodeError) as exc:
        print(f"pr_scope_manifest: {exc}", file=sys.stderr)
        return 2
    if not result.declared or result.undeclared or result.stale:
        _report_failure(result)
        print(
            f"PR #{args.pr}: refusing to arm auto-merge — the body carries no manifest "
            "matching the diff<!-- home --> (ENG-12308)<!-- /home -->. Recompose it, then re-run.",
            file=sys.stderr,
        )
        return 1
    proc = subprocess.run(  # noqa: S603 — fixed argv, no shell
        ["gh", "pr", "merge", args.pr, "--auto", "--squash"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(
            f"PR #{args.pr}: `gh pr merge --auto --squash` failed: "
            f"{(proc.stderr or proc.stdout or 'no output').strip()[:300]}",
            file=sys.stderr,
        )
        return 1
    print(f"PR #{args.pr}: manifest matched and auto-merge armed (squash), confirmed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    compose = sub.add_parser("compose", help="write the record-PR body (Refs + ## Files manifest)")
    compose.add_argument("--refs", required=True, help="the tracker issue key, e.g. <KEY>")
    compose.add_argument("--base", default=DEFAULT_BASE, help=f"diff base (default {DEFAULT_BASE})")
    compose.add_argument("--note", default="", help="optional prose between the Refs link and the manifest")
    compose.add_argument("--note-file", default="", help="read the optional prose from a file (never argv)")
    compose.add_argument("--out", default="", help="write the body here instead of stdout")
    compose.set_defaults(func=_cmd_compose)

    ensure_p = sub.add_parser(
        "ensure", help="splice a current `## Files` manifest into ANY PR body (a file or a live PR)"
    )
    ensure_p.add_argument("--pr", default="", help="pull request number to rewrite in place")
    ensure_p.add_argument("--body-file", default="", help="a local body file to transform instead of a live PR")
    ensure_p.add_argument("--out", default="", help="write the transformed body here (default: stdout)")
    ensure_p.add_argument("--base", default=DEFAULT_BASE, help=f"diff base (default {DEFAULT_BASE})")
    ensure_p.set_defaults(func=_cmd_ensure)

    gate_p = sub.add_parser("gate", help="refuse unless the live PR body's manifest matches the diff")
    gate_p.add_argument("--pr", required=True, help="pull request number")
    gate_p.add_argument("--base", default=DEFAULT_BASE, help=f"diff base (default {DEFAULT_BASE})")
    gate_p.set_defaults(func=_cmd_gate)

    arm = sub.add_parser("arm", help="gate, then arm auto-merge (squash) when it passes")
    arm.add_argument("--pr", required=True, help="pull request number")
    arm.add_argument("--base", default=DEFAULT_BASE, help=f"diff base (default {DEFAULT_BASE})")
    arm.set_defaults(func=_cmd_arm)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
