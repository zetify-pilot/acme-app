"""The todo register — things noticed and not settled.

`<root>/todos.md` holds the questions and doubts raised in passing: not commitments (those
are requirement-register rows with a disposition) and not dispatchable work (those are
issues with an owner). A todo has neither, which is exactly why it needs a surface.

**Why a register rather than markers in prose.** A marker at the sentence that raised each
todo fails where todos actually get written — mid-sentence, while thinking about something
else. A file you can open is complete by construction; a convention is only as complete as
its least careful author. The register also represents a todo attached to no sentence at
all, which a marker cannot.

Stdlib only.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

REGISTER_FILE = "todos.md"
TODO_PREFIX = "TODO"

STATUSES = frozenset({"open", "filed", "done", "dropped"})


def row_pattern(prefix: str = TODO_PREFIX) -> re.Pattern[str]:
    r"""`^\|\s*(Q-\d+)\s*\|(.+)$` for `Q`. `Config.todo_prefix` names the namespace.

    Built from the prefix rather than written out. `todo_prefix` was an option nothing read:
    three patterns here were anchored on `TODO` literally, so a corpus that set it got a
    register every row of which was skipped — a page saying the register is empty, which is
    what an empty register looks like too.
    """
    return re.compile(rf"^\|\s*({re.escape(prefix)}-\d+)\s*\|(.+)$")


def next_pattern(prefix: str = TODO_PREFIX) -> re.Pattern[str]:
    """The append-only counter marker for this namespace."""
    return re.compile(rf"APPEND ONLY\. Next id:\s*{re.escape(prefix)}-(\d+)")


def cite_pattern(prefix: str = TODO_PREFIX) -> re.Pattern[str]:
    """The register's own markdown-bold citation syntax, in this namespace."""
    return re.compile(rf"\*\*\[({re.escape(prefix)}-\d+)\]\*\*")


ROW_RE = row_pattern()
NEXT_RE = next_pattern()
CITE_RE = cite_pattern()


class TodoParseError(ValueError):
    """A row in the register is malformed enough that its content cannot be trusted.

    A parse failure is a hard error: dropping the row silently would lose the very open
    question the register exists to keep.
    """


def register(root: Path, file_name: str = REGISTER_FILE) -> Path:
    """The register file. `Config.todos_register` names it; nothing else may."""
    return root / file_name


def rows(root: Path, file_name: str = REGISTER_FILE, prefix: str = TODO_PREFIX) -> list[dict[str, Any]]:
    """Every todo row, in register order. `[]` when the register does not exist."""
    return read(register(root, file_name), prefix)


def read(path: Path, prefix: str = TODO_PREFIX) -> list[dict[str, Any]]:
    """`rows` against a register file named directly.

    Separate from `rows` because the register is ONE file, and a caller that has its path in
    hand (a validator running against a fixture, a checkout binding that lets the path be
    rebound) must not have to invent a root directory around it.
    """
    if not path.exists():
        return []
    row_re = row_pattern(prefix)
    out: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        m = row_re.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        # The register's OWN name, not the default one. A corpus that calls its register
        # `open-questions.md` was being told to go and fix a line in a `todos.md` it does
        # not have — a message that sends a reader to the wrong file is worse than none.
        where = f"{path.name}:{i}"
        if len(cells) < 5:
            # A row with fewer than the five data columns (Todo, Status, Raised, Where,
            # Refs / Notes) is malformed. Dropping it here would silently lose an open
            # question on an rc-0 path — the exact failure the register exists to prevent.
            raise TodoParseError(
                f"{where}: `{m.group(1)}` has {len(cells)} column(s); expected 5 "
                "(Todo, Status, Raised, Where, Refs / Notes) — a row that fails to parse "
                "must be fixed, never silently dropped"
            )
        out.append(
            {
                "id": m.group(1),
                "todo": cells[0],
                "status": cells[1].lower(),
                "raised": cells[2],
                "where": cells[3],
                "refs": cells[4],
                "line": i,
            }
        )
    return out


def next_id(root: Path, file_name: str = REGISTER_FILE, prefix: str = TODO_PREFIX) -> str:
    """The append-only counter, as written. "" when the marker is missing.

    `file_name` takes `Config.todos_register`, like `rows` and `register` above — a reader
    that took the option in two of three entry points would answer differently depending on
    which one a caller happened to reach for.
    """
    path = register(root, file_name)
    if not path.exists():
        return ""
    m = next_pattern(prefix).search(path.read_text(encoding="utf-8"))
    return f"{prefix}-{m.group(1)}" if m else ""


def _tracked_files(base: Path) -> list[str]:
    """Every git-tracked path under `base`, or every file when this is not a git checkout.

    Git is preferred because it honours `.gitignore` by construction, which keeps a scan
    off build output and vendored trees. The walk is the fallback so this package works on a
    corpus that was copied out of version control — with the same ignore list applied by
    hand, since a `node_modules` sweep would otherwise dominate the run.
    """
    proc = subprocess.run(
        ["git", "-C", str(base), "ls-files"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return proc.stdout.split("\n")
    skip = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".mypy_cache"}
    out: list[str] = []
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        if skip & set(p.relative_to(base).parts):
            continue
        out.append(str(p.relative_to(base)))
    return out


def citations(base: Path, register_path: Path | None = None, prefix: str = TODO_PREFIX) -> dict[str, list[str]]:
    """Every `**[TODO-NNN]**` under `base` -> the files it appears in.

    `base` is the project, not the corpus: a citation stands in for the todo, so a pointer to
    nothing is worse than no pointer — it reads as tracked when it is not — and it has to be
    findable wherever it was written. `register_path` is excluded from the scan, since the
    register naming its own rows is not a citation of them.

    `**[TODO-NNN]**` is the register's own markdown-bold syntax, distinct from code's
    `// TODO`, so a dangling citation cannot be hidden by putting it somewhere the scan does
    not look.
    """
    register_rel = ""
    if register_path is not None:
        try:
            register_rel = str(register_path.relative_to(base))
        except ValueError:
            register_rel = ""
    found: dict[str, list[str]] = {}
    for rel_path in _tracked_files(base):
        if not rel_path or rel_path == register_rel:
            continue
        try:
            text = (base / rel_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for tid in set(cite_pattern(prefix).findall(text)):
            found.setdefault(tid, []).append(rel_path)
    return found
