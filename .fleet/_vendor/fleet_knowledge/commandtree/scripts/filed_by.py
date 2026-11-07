"""Who filed this issue — the one footer every filing carries, defined once.

    Filed by <origin> · <command>

**Why.** The fleet's tracker account is shared: dispatched runs, interactive sessions on a
person's machine and CI automation all create issues as the same user, so the tracker's own
"created by" cannot answer *who filed this?*. On one day of about 290 new issues, 128 of the 172
the shared account created carried no marker of their source at all. The footer is that answer,
written mechanically at the birth write, so no caller can forget it.

**`<origin>` is read from the environment the filer runs in, never passed by a caller:**

  * a GitHub Actions job (`GITHUB_ACTIONS=true`) — `GitHub Actions <workflow>#<run id>`;
  * a dispatched fleet run (`FLEET_RUN_ID`, exported by the fleet daemon into every session it
    starts) — `fleet run <run id> on <box>`, the box from `FLEET_BOX_ID`, else the host name;
  * anything else is an interactive session on someone's machine —
    `local session <host> <session id>`, the session id from `CLAUDE_CODE_SESSION_ID` (or
    `CLAUDE_SESSION_ID`), else `local session <host> pid <pid>`.

**`<command>` is the caller's, and it is required.** The command (slash command) or script doing the
filing (`bug:create`, `task:create`, `bug:fix (Rule-G deferral)`, `audit`, `own`, a CI alert's
purpose …). A blank one raises `MissingCommandError` — a default here would be a footer that
answers *who* with *somebody*, which is the defect this module exists to remove.

**Exactly one footer.** `stamp()` drops any line already shaped like a footer before appending
its own, so a body that is re-filed, or that quotes an earlier filing, still ends with ONE.

**Never a credential.** Only the identity variables named above are read; no token, key or
URL with userinfo can reach the line. Every value is reduced to a short, single-line,
conservative character set before it is written. Stdlib only.
"""

from __future__ import annotations

import os
import re
import socket
from collections.abc import Mapping

#: The fixed opening of the line — what a reader (and `footers()`) recognises it by.
PREFIX = "Filed by "
#: Between origin and command. A middle dot, so neither half has to avoid a hyphen or a colon.
SEPARATOR = " · "

#: One footer line, anchored: `Filed by <origin> · <command>` and nothing else on the line.
FOOTER_RE = re.compile(r"^Filed by (?P<origin>[^\n·]+?) · (?P<command>[^\n·]+)$", re.MULTILINE)

#: What survives into an origin or command token. Conservative on purpose: a value that is
#: neither an id, a host name, a workflow name nor a command name loses the rest.
_UNSAFE = re.compile(r"[^A-Za-z0-9 ._:/@#()+-]")
_MAX_TOKEN = 80


class MissingCommandError(ValueError):
    """A filing named no command. The footer refuses to be written without one."""


def _clean(value: str, *, cap: int = _MAX_TOKEN) -> str:
    one_line = " ".join(str(value).split())
    return " ".join(_UNSAFE.sub("", one_line).split())[:cap].strip()


def origin(env: Mapping[str, str] | None = None) -> str:
    """Where this filing comes from — CI, a dispatched run, or a local session (see module doc)."""
    e = os.environ if env is None else env
    if e.get("GITHUB_ACTIONS") == "true":
        workflow = _clean(e.get("GITHUB_WORKFLOW", "")) or "unknown-workflow"
        run = _clean(e.get("GITHUB_RUN_ID", "")) or "unknown-run"
        return f"GitHub Actions {workflow}#{run}"
    run_id = _clean(e.get("FLEET_RUN_ID", ""))
    if run_id:
        box = _clean(e.get("FLEET_BOX_ID", "") or socket.gethostname()) or "unknown-box"
        return f"fleet run {run_id} on {box}"
    host = _clean(socket.gethostname()) or "unknown-host"
    session = _clean(e.get("CLAUDE_CODE_SESSION_ID", "") or e.get("CLAUDE_SESSION_ID", ""))
    if session:
        return f"local session {host} {session}"
    return f"local session {host} pid {os.getpid()}"


def footer(command: str, *, origin_text: str | None = None, env: Mapping[str, str] | None = None) -> str:
    """The footer line for `command`. `origin_text` is for a filer that knows its origin from a
    credential rather than an environment (the fleet service names a run from its own records);
    every other caller leaves it out and gets `origin()`."""
    name = _clean(command or "")
    if not name:
        raise MissingCommandError(
            "a filing must name the command or script that filed it (e.g. `bug:create`, `audit`, "
            "a CI alert's purpose) — the `Filed by` footer has no default for it"
        )
    where = _clean(origin_text, cap=160) if origin_text is not None else origin(env)
    if not where:
        raise ValueError("a filing's origin resolved to nothing")
    return f"{PREFIX}{where}{SEPARATOR}{name}"


def footers(body: str) -> list[tuple[str, str]]:
    """Every well-formed footer in `body`, as `(origin, command)` pairs, in order."""
    return [(m.group("origin"), m.group("command")) for m in FOOTER_RE.finditer(body or "")]


def stamp(body: str, command: str, *, origin_text: str | None = None, env: Mapping[str, str] | None = None) -> str:
    """`body` ending in exactly one footer for `command`: any footer-shaped line already in it is
    dropped, then this filing's own is appended after a blank line."""
    line = footer(command, origin_text=origin_text, env=env)
    kept = FOOTER_RE.sub("", body or "").rstrip()
    return f"{kept}\n\n{line}" if kept else line
