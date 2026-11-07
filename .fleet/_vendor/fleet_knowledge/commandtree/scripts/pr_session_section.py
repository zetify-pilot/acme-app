#!/usr/bin/env python3
"""Append the Fleet session's questions and answers to a pull-request note file.

WHY THIS EXISTS. A pull request an agent opens should say why the change happened and who
decided what, and the reviewer reads it on GitHub's own page. The section is composed HERE,
deterministically, from Fleet's tools read of the calling run's session thread, because the
promise is *verbatim*: a model retyping a person's answer is the one way to break that
silently. `push.md` runs this before `pr_scope_manifest.py compose`, so the section lands in
the note file that `compose` places above the generated `## Files` manifest.

WHAT IT IS NOT: no link to the session page, no transcript, no tool calls, no reasoning
(R9). The only URL-shaped text is whatever a person typed.

  python3 knowledge/scripts/pr_session_section.py append --note-file PATH

Inputs come from the environment only — never argv, because argv is world-readable:

  $FLEET_TOOLS_URL    the non-secret tools base, `<origin>/api/tools/v1`
  $FLEET_HEADERS_FILE a 0600 JSON file holding `Authorization`
  $FLEET_RESULT_FILE  set only for a fleet dispatch run; the discriminator for the failure split

The failure split, so neither a person's push nor a fleet run is silent:

  * no headers file, no `$FLEET_RESULT_FILE`        -> a person's push: emit nothing, exit 0
  * no headers file, `$FLEET_RESULT_FILE` set       -> a fleet run missing wiring: exit non-zero
  * a person's push with a headers file             -> query Fleet; a person key answers
                                                       `{"session": null}`, so emit nothing, exit 0
  * a fleet run with no `$FLEET_TOOLS_URL`          -> the same deployment fault
  * a failed read (non-200, timeout, malformed JSON,
    `409 session-unresolved`)                       -> one retry, then exit non-zero naming the cause

`append` is idempotent: an existing `## Session and questions` section is replaced in place
(through the next `## ` heading or EOF), a stale one is removed when the conversation is now
empty, and a missing note file is created. Stdlib only, like every shipped script.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

HEADING = "## Session and questions"
SECTION_ENDPOINT = "/session/questions"
HTTP_TIMEOUT_S = 10.0
RETRY_BACKOFF_S = 0.2
ATTEMPTS = 2

_ISSUE_KEY_RE = re.compile(r"[A-Za-z0-9_-]+\Z")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_ORDERED_START_RE = re.compile(r"^\d+\.")

#: CommonMark structural characters escaped everywhere in a field.
_STRUCTURAL = frozenset("\\`*_[]<>|~#")
#: Characters that would open a list (or a block quote) when they start a field.
_START_STRUCTURAL = frozenset("-+>")


class SectionError(RuntimeError):
    """A read or wiring fault: the section cannot be composed, so the push must stop."""


# ── escaping ─────────────────────────────────────────────────────────────────────


def _inline(text: object) -> str:
    """One field, safe inside the pull-request body, with its words unchanged.

    Every whitespace run (newlines included) collapses to one space; then the CommonMark
    structural characters are backslash-escaped everywhere, plus the characters that only
    open a list or ordered list at the start of a field. No HTML entity rewriting and no
    truncation: what the person wrote is what the reviewer reads.
    """
    collapsed = " ".join(str(text or "").split())
    if not collapsed:
        return ""
    ordered_dot = -1
    match = _ORDERED_START_RE.match(collapsed)
    if match:
        ordered_dot = match.end() - 1
    out: list[str] = []
    for index, char in enumerate(collapsed):
        escape = char in _STRUCTURAL or (index == 0 and char in _START_STRUCTURAL) or index == ordered_dot
        out.append(f"\\{char}" if escape else char)
    return "".join(out)


# ── reading Fleet ───────────────────────────────────────────────────────────────


def _read_authorization(path: str) -> str:
    """The `Authorization` header from the 0600 headers file. The value is never printed."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise SectionError(f"cannot read the headers file {path}: {exc}") from exc
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SectionError(f"the headers file {path} is not valid JSON: {exc.msg}") from exc
    if not isinstance(loaded, dict):
        raise SectionError(f"the headers file {path} does not hold a JSON object")
    value = loaded.get("Authorization")
    if not isinstance(value, str) or not value.strip():
        raise SectionError(f"the headers file {path} carries no Authorization header")
    return value.strip()


def _http_failure(status: int, raw: str) -> str:
    """A sentence naming an HTTP failure, from Fleet's own message when it gave one."""
    detail = ""
    loaded: Any = None
    if raw.strip():
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            loaded = None
    if isinstance(loaded, dict):
        message = loaded.get("message") or loaded.get("error")
        if isinstance(message, str) and message.strip():
            detail = f": {message.strip()}"
    elif raw.strip():
        detail = f": {raw.strip()[:200]}"
    if status == 409:
        return f"Fleet refused the read (HTTP 409 session-unresolved{detail})"
    return f"Fleet answered HTTP {status}{detail}"


def _fetch(url: str, authorization: str) -> dict[str, Any]:
    """GET the session read, retrying once. Raises `SectionError` naming the cause."""
    last = "no response"
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(RETRY_BACKOFF_S)
        request = urllib.request.Request(
            url,
            headers={"Authorization": authorization, "Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_S) as response:
                raw = response.read().decode("utf-8", errors="replace")
                status = int(getattr(response, "status", 200) or 200)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            last = _http_failure(int(exc.code), raw)
            continue
        except TimeoutError:
            last = f"the request timed out after {HTTP_TIMEOUT_S:g}s"
            continue
        except urllib.error.URLError as exc:
            last = f"could not reach Fleet ({getattr(exc, 'reason', exc)})"
            continue
        except OSError as exc:
            last = f"could not reach Fleet ({exc})"
            continue
        if status != 200:
            last = _http_failure(status, raw)
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            last = "Fleet answered with malformed JSON"
            continue
        if not isinstance(payload, dict):
            last = "Fleet answered with JSON that is not an object"
            continue
        return payload
    raise SectionError(f"the Fleet read failed after {ATTEMPTS} attempts: {last}")


# ── rendering ───────────────────────────────────────────────────────────────────


def _count_phrase(count: int) -> str:
    if count == 1:
        return "one question"
    if count == 2:
        return "two questions"
    return f"{count} questions"


def _answer(question: Mapping[str, Any]) -> str:
    """The recorded answer: the picked option's label, or the typed text as stored."""
    picked = str(question.get("pickedOptionId") or "")
    if picked:
        for option in question.get("options") or []:
            if isinstance(option, dict) and str(option.get("id") or "") == picked:
                label = str(option.get("label") or "").strip()
                if label:
                    return label
    return str(question.get("answerText") or "")


def _answerer_line(one: Mapping[str, Any]) -> str:
    """`— <answeredBy>, <YYYY-MM-DD>`, the date alone when no identity was recorded."""
    identity = str(one.get("answeredBy") or "").strip()
    match = _DATE_RE.match(str(one.get("answeredAt") or "").strip())
    date = match.group(0) if match else ""
    if identity and date:
        return f"— {_inline(identity)}, {date}"
    if date:
        return f"— {date}"
    if identity:
        return f"— {_inline(identity)}"
    return ""


def _render_round(one: Mapping[str, Any], questions: list[Any]) -> list[str]:
    instruction = str(one.get("instruction") or "")
    blocks: list[str] = []
    for question in questions:
        if not isinstance(question, dict):
            raise SectionError("Fleet returned a question that is not an object")
        block = f"**Q:** {_inline(question.get('prompt'))}"
        answer = _answer(question)
        if instruction:
            if answer:
                block += f"\n**A:** Before sending it back they had picked: {_inline(answer)}"
        elif answer:
            block += f"\n**A:** {_inline(answer)}"
        blocks.append(block)
    if instruction:
        blocks.append(f"Sent back with: {_inline(instruction)}")
    answerer = _answerer_line(one)
    if answerer:
        blocks.append(answerer)
    return blocks


def render(payload: Mapping[str, Any]) -> str:
    """The frozen `## Session and questions` section, or `""` when there is nothing to say."""
    session = payload.get("session")
    if session is None:
        return ""
    if not isinstance(session, dict):
        raise SectionError("Fleet returned a session that is not an object")
    thread = str(session.get("thread") or "")
    issue_key = str(session.get("issueKey") or "")
    try:
        uuid.UUID(thread)
    except (ValueError, AttributeError, TypeError):
        raise SectionError(f"Fleet returned a session thread that is not a UUID: {thread!r}") from None
    if not _ISSUE_KEY_RE.fullmatch(issue_key):
        raise SectionError(f"Fleet returned an issue key that is not a safe identifier: {issue_key!r}")

    rounds = payload.get("rounds")
    if rounds is None:
        rounds = []
    if not isinstance(rounds, list):
        raise SectionError("Fleet returned rounds that are not a list")
    if not rounds:
        return ""

    prepared: list[tuple[Mapping[str, Any], list[Any]]] = []
    total = 0
    for one in rounds:
        if not isinstance(one, dict):
            raise SectionError("Fleet returned a round that is not an object")
        questions = one.get("questions")
        if questions is None:
            questions = []
        if not isinstance(questions, list):
            raise SectionError("Fleet returned questions that are not a list")
        total += len(questions)
        prepared.append((one, questions))

    blocks = [f"Session `{thread}` on {issue_key} — {_count_phrase(total)} put to a person."]
    for one, questions in prepared:
        blocks.extend(_render_round(one, questions))
    return f"{HEADING}\n\n" + "\n\n".join(blocks)


# ── idempotent append ───────────────────────────────────────────────────────────


def apply_section(existing: str, section: str) -> str | None:
    """`existing` with its session section replaced, appended, or removed.

    `None` means "leave the file alone": there is no section to add and none to remove.
    An existing section is replaced in place — heading through the next `## ` heading or
    EOF — never duplicated, and a now-empty conversation removes it.
    """
    lines = existing.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == HEADING:
            start = index
            break
    if start is None:
        if not section:
            return None
        base = existing.rstrip()
        return f"{base}\n\n{section}\n" if base else f"{section}\n"

    end = start + 1
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    before = "\n".join(lines[:start]).rstrip()
    after = "\n".join(lines[end:]).lstrip("\n")
    parts = [part for part in (before, section, after) if part.strip()]
    rendered = "\n\n".join(parts)
    return f"{rendered}\n" if rendered else ""


# ── cli ─────────────────────────────────────────────────────────────────────────


def _cmd_append(args: argparse.Namespace) -> int:
    note_path = Path(args.note_file)
    headers_path = (os.environ.get("FLEET_HEADERS_FILE") or "").strip()
    result_file = (os.environ.get("FLEET_RESULT_FILE") or "").strip()
    tools_url = (os.environ.get("FLEET_TOOLS_URL") or "").strip()

    if not headers_path:
        if result_file:
            print(
                "pr_session_section: deployment fault — this fleet run has no "
                "$FLEET_HEADERS_FILE, so its session's questions cannot be read",
                file=sys.stderr,
            )
            return 2
        return 0
    if not tools_url:
        if result_file:
            print(
                "pr_session_section: deployment fault — this fleet run has no "
                "$FLEET_TOOLS_URL, so its session's questions cannot be read",
                file=sys.stderr,
            )
            return 2
        return 0

    try:
        authorization = _read_authorization(headers_path)
        payload = _fetch(tools_url.rstrip("/") + SECTION_ENDPOINT, authorization)
        section = render(payload)
    except SectionError as exc:
        print(f"pr_session_section: {exc}", file=sys.stderr)
        return 2

    try:
        existing = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
    except OSError as exc:
        print(f"pr_session_section: cannot read the note file {note_path}: {exc}", file=sys.stderr)
        return 2
    updated = apply_section(existing, section)
    if updated is None:
        return 0
    try:
        note_path.write_text(updated, encoding="utf-8")
    except OSError as exc:
        print(f"pr_session_section: cannot write the note file {note_path}: {exc}", file=sys.stderr)
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    append = sub.add_parser("append", help="append the session section to a note file")
    append.add_argument("--note-file", required=True, help="the note file the PR body is composed from")
    append.set_defaults(func=_cmd_append)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
