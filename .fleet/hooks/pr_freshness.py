#!/usr/bin/env python3
"""PR freshness: whenever a pull request is named in a session, show the agent its LIVE state.

One implementation for both engines, so detection and wording cannot drift:

* Claude Code runs it as a `UserPromptSubmit` and `PostToolUse` hook (`pr_freshness.py claude`,
  hook JSON on stdin, `hookSpecificOutput.additionalContext` on stdout).
* The fleet's opencode plugin shells out to it (`pr_freshness.py lines`, `{"texts": [...],
  "cwd": "..."}` on stdin, `{"lines": [{"key": ..., "line": ...}]}` on stdout). `refs` takes the same
  input and answers `{"refs": [["owner/repo#n", ...], ...]}`, one list per text, with no lookup: the
  PR-state guard's question is which PRs a sentence names, and the answer lives only here.

It NEVER blocks or fails a turn: every error (no `gh`, no token, a rate limit, a timeout, a 404
because `#n` was an issue) means no output and exit status 0. The token is read by `gh` from its
own environment (`GH_TOKEN`) or its own login; this file never reads, prints or passes it on argv.
Standard library only, so it runs on any machine with `python3`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

#: The most PRs looked up for one event.
MAX_PRS: Final = 5
#: Seconds one `gh` call may take.
FETCH_TIMEOUT: Final = 5
#: Seconds a fetched line is reused for the same `owner/repo#n`.
CACHE_TTL: Final = 60
#: A bare `#n` that appears more than this many times in one text is an issue list, not a PR.
BARE_LIST_LIMIT: Final = 8
#: Every line starts with this, which is also how a freshness line is recognised and skipped.
MARKER: Final = "[PR live "
MAX_LINE: Final = 200
MAX_TEXT: Final = 400_000

Ref = tuple[str, str, int]

_NAME = r"[A-Za-z0-9][A-Za-z0-9._-]*"
_URL = re.compile(rf"github\.com/({_NAME})/({_NAME})/pull/(\d{{1,7}})(?!\d)")
_FENCE = re.compile(r"```.*?(?:```|\Z)", re.DOTALL)
_QUALIFIED = re.compile(rf"(?<![\w/.#-])({_NAME})/({_NAME})#(\d{{1,7}})(?![\w-])")
_SIBLING = re.compile(rf"(?<![\w/.#&-])({_NAME})#(\d{{1,7}})(?![\w-])")
#: A bare `#n` follows whitespace or an opening bracket, ends on a non-word, and has 1-5 digits
#: (so a six-digit hex colour such as `#123456` is not a PR).
_BARE = re.compile(r"(?:(?<=\s)|(?<=[(\[{,;:>\"'])|(?<=^))#(\d{1,5})(?![\w#-])", re.MULTILINE)
_REMOTE = re.compile(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")

_GRAPHQL = (
    "query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name)"
    "{pullRequest(number:$number){mergeQueueEntry{state position}}}}"
)
_FIELDS = "state,isDraft,mergeable,mergeStateStatus,headRefOid,autoMergeRequest,statusCheckRollup,mergedAt,mergeCommit"


def strip_freshness(text: str) -> str:
    """The text without the freshness lines this tool wrote, so its own output never re-triggers it."""
    return "\n".join(line for line in text.splitlines() if MARKER not in line)


def default_repo(cwd: str | None) -> tuple[str, str] | None:
    """`(owner, repo)` of the session directory's `origin`, or None when it is not on GitHub."""
    if not cwd or shutil.which("git") is None:
        return None
    try:
        done = subprocess.run(
            ["git", "-C", cwd, "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=FETCH_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = _REMOTE.search(done.stdout.strip()) if done.returncode == 0 else None
    return (match.group(1), match.group(2)) if match else None


def detect(text: str, repo: tuple[str, str] | None = None) -> list[Ref]:
    """The pull requests `text` names, in order of first appearance, at most `MAX_PRS`.

    Recognised: `github.com/o/r/pull/n`, `o/r#n`, `r#n` (same owner as `repo`) and a bare `#n`
    (the session's own `repo`). Bare and sibling forms are ignored inside code fences, and a
    text carrying more than `BARE_LIST_LIMIT` bare references is an issue list, not a PR.
    """
    text = strip_freshness(text[:MAX_TEXT])
    found: list[tuple[int, Ref]] = []
    for m in _URL.finditer(text):
        found.append((m.start(), (m.group(1), m.group(2), int(m.group(3)))))
    prose = _FENCE.sub(lambda m: " " * len(m.group(0)), text)
    for m in _QUALIFIED.finditer(prose):
        found.append((m.start(), (m.group(1), m.group(2), int(m.group(3)))))
    if repo is not None:
        owner, name = repo
        found.extend((m.start(), (owner, m.group(1), int(m.group(2)))) for m in _SIBLING.finditer(prose))
        bare = list(_BARE.finditer(prose))
        if len(bare) <= BARE_LIST_LIMIT:
            found.extend((m.start(), (owner, name, int(m.group(1)))) for m in bare)
    seen: set[Ref] = set()
    out: list[Ref] = []
    for _, ref in sorted(found, key=lambda item: item[0]):
        if ref[2] > 0 and ref not in seen:
            seen.add(ref)
            out.append(ref)
    return out[:MAX_PRS]


def _utc(ts: datetime | None = None) -> str:
    return (ts or datetime.now(UTC)).strftime("%H:%MZ")


def _checks(rollup: Any) -> tuple[int, int, int]:
    """`(passed, failed, total)` over a `statusCheckRollup` list."""
    passed = failed = total = 0
    for item in rollup if isinstance(rollup, list) else []:
        if not isinstance(item, dict):
            continue
        total += 1
        status = str(item.get("status") or "").upper()
        verdict = str(item.get("conclusion") or item.get("state") or "").upper()
        if verdict in {"SUCCESS", "NEUTRAL", "SKIPPED"}:
            passed += 1
        elif verdict in {"FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE"}:
            failed += 1
        elif status == "COMPLETED":
            passed += 1
    return passed, failed, total


def format_line(ref: Ref, view: dict[str, Any], queue: dict[str, Any] | None, now: datetime | None = None) -> str:
    """The one-line status for `ref` from `gh pr view --json` data and its merge-queue entry."""
    owner, repo, number = ref
    stamp = _utc(now)
    head = f"{MARKER}{stamp}] {owner}/{repo}#{number}: "
    state = str(view.get("state") or "").upper()
    if state == "MERGED":
        merged = view.get("mergedAt")
        when = _utc(datetime.fromisoformat(merged.replace("Z", "+00:00"))) if isinstance(merged, str) else stamp
        commit = view.get("mergeCommit") or {}
        sha = str(commit.get("oid") or "")[:7] if isinstance(commit, dict) else ""
        # The head's check result rides a merged PR too: `statusCheckRollup` is already in the one
        # `gh pr view` call, so it costs nothing extra.
        passed, failed, total = _checks(view.get("statusCheckRollup"))
        outcome = f"checks {passed}/{total} pass, {failed} failed" if total else "checks none reported"
        return (head + f"merged {when}" + (f" as {sha}" if sha else "") + " · " + outcome)[:MAX_LINE]
    if state == "CLOSED":
        return (head + "closed without merging")[:MAX_LINE]
    passed, failed, total = _checks(view.get("statusCheckRollup"))
    pending = total - passed - failed
    merge_state = str(view.get("mergeStateStatus") or "").upper()
    if str(view.get("mergeable") or "").upper() == "CONFLICTING" or merge_state == "DIRTY":
        verdict = "conflicting — no checks will run until rebased"
    elif merge_state == "CLEAN":
        verdict = "clean"
    elif merge_state == "BLOCKED":
        verdict = "blocked (checks running)" if pending > 0 else "blocked (failed or missing required checks)"
    elif merge_state == "BEHIND":
        verdict = "behind main"
    elif merge_state == "UNSTABLE":
        verdict = "unstable (a check failed)"
    elif merge_state == "DRAFT":
        verdict = "draft"
    else:
        verdict = "mergeability unknown"
    parts = ["draft" if view.get("isDraft") else "open", verdict]
    sha = str(view.get("headRefOid") or "")[:7]
    if sha:
        parts.append(f"head {sha}")
    if total:
        parts.append(f"checks {passed}/{total} pass, {failed} failed")
    else:
        parts.append("checks none reported")
    if queue:
        position = queue.get("position")
        parts.append(
            f"merge queue: {str(queue.get('state') or 'queued').lower()}" + (f" #{position}" if position else "")
        )
    else:
        parts.append("merge queue: none")
    parts.append("auto-merge: " + ("on" if view.get("autoMergeRequest") else "off"))
    return (head + " · ".join(parts))[:MAX_LINE]


def _gh(args: list[str]) -> Any | None:
    """Run `gh` (argv only, never a credential) and return its parsed JSON, or None on any failure."""
    try:
        done = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=FETCH_TIMEOUT, check=False)
        return json.loads(done.stdout) if done.returncode == 0 and done.stdout.strip() else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def fetch(ref: Ref) -> str | None:
    """The freshness line for `ref`, or None when it is not a readable pull request."""
    owner, repo, number = ref
    view = _gh(["pr", "view", str(number), "-R", f"{owner}/{repo}", "--json", _FIELDS])
    if not isinstance(view, dict):
        return None
    queue: dict[str, Any] | None = None
    if str(view.get("state") or "").upper() == "OPEN":
        graph = _gh(
            [
                "api",
                "graphql",
                "-f",
                f"query={_GRAPHQL}",
                "-F",
                f"owner={owner}",
                "-F",
                f"name={repo}",
                "-F",
                f"number={number}",
            ]
        )
        try:
            queue = (graph or {})["data"]["repository"]["pullRequest"]["mergeQueueEntry"]
        except (KeyError, TypeError):
            queue = None
    return format_line(ref, view, queue)


def cache_dir() -> Path:
    base = os.environ.get("FLEET_RUN_DIR") or tempfile.gettempdir()
    return Path(base) / f"fleet-pr-freshness-{os.getuid()}"


def cached_fetch(ref: Ref, directory: Path | None = None, now: float | None = None) -> str | None:
    """`fetch` behind a small file cache: one lookup per `owner/repo#n` per `CACHE_TTL` seconds."""
    directory = directory or cache_dir()
    clock = time.time() if now is None else now
    path = directory / f"{ref[0]}__{ref[1]}__{ref[2]}.json"
    try:
        entry = json.loads(path.read_text(encoding="utf-8"))
        if clock - float(entry["at"]) < CACHE_TTL:
            return str(entry["line"])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    line = fetch(ref)
    if line is not None:
        try:
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            path.write_text(json.dumps({"at": clock, "line": line}), encoding="utf-8")
        except OSError:
            pass
    return line


def lines_for(texts: list[str], cwd: str | None) -> list[tuple[str, str]]:
    """`[(key, line)]` for every PR the texts name (at most `MAX_PRS` in all), looked up in parallel."""
    if shutil.which("gh") is None:
        return []
    repo = default_repo(cwd)
    refs: list[Ref] = []
    for text in texts:
        for ref in detect(text, repo):
            if ref not in refs:
                refs.append(ref)
    refs = refs[:MAX_PRS]
    if not refs:
        return []
    with ThreadPoolExecutor(max_workers=len(refs)) as pool:
        results = list(pool.map(cached_fetch, refs))
    return [(f"{o}/{r}#{n}", line) for (o, r, n), line in zip(refs, results, strict=True) if line]


def refs_for(texts: list[str], cwd: str | None) -> list[list[str]]:
    """`owner/repo#n` for the PRs each text names, one list per text, by the same rules as `detect`.

    No lookup and no network: the PR-state guard asks WHICH pull requests a sentence names, and this
    file is the one place that knows what a reference is.
    """
    repo = default_repo(cwd)
    return [[f"{o}/{r}#{n}" for o, r, n in detect(text, repo)] for text in texts]


def _strings(value: Any, out: list[str], depth: int = 0) -> None:
    if isinstance(value, str):
        out.append(value)
    elif depth < 6 and isinstance(value, dict):
        for item in value.values():
            _strings(item, out, depth + 1)
    elif depth < 6 and isinstance(value, list):
        for item in value:
            _strings(item, out, depth + 1)


def claude(payload: dict[str, Any]) -> dict[str, Any] | None:
    """The hook output for one Claude Code `UserPromptSubmit` / `PostToolUse` event, or None."""
    event = payload.get("hook_event_name")
    if event not in {"UserPromptSubmit", "PostToolUse"}:
        return None
    texts: list[str] = []
    _strings(payload.get("prompt") if event == "UserPromptSubmit" else payload.get("tool_response"), texts)
    found = lines_for(["\n".join(texts)], str(payload.get("cwd") or "") or None)
    if not found:
        return None
    context = "\n".join(line for _, line in found)[:10_000]
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}


def main(argv: list[str]) -> int:
    try:
        mode = argv[1] if len(argv) > 1 else ""
        payload = json.loads(sys.stdin.read() or "{}")
        if mode == "claude":
            out = claude(payload)
        elif mode == "lines":
            found = lines_for([str(t) for t in payload.get("texts", [])], payload.get("cwd"))
            out = {"lines": [{"key": key, "line": line} for key, line in found]} if found else None
        elif mode == "refs":
            out = {"refs": refs_for([str(t) for t in payload.get("texts", [])], payload.get("cwd"))}
        else:
            out = None
        if out is not None:
            sys.stdout.write(json.dumps(out))
    except Exception:  # noqa: BLE001 - a freshness hint must never fail a turn
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
