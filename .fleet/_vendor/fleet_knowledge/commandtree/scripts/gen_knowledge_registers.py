#!/usr/bin/env python3
"""Render the program and slice register tables from one file per row.

The registers (`knowledge/programs.md`, `knowledge/slices.md`) used to be hand-edited shared
tables: every branch that added a program or a slice edited the same file, so two concurrent
PRs that each added a *different* row still collided. Each row now lives in its own fragment,
and the table is rendered from the fragments, so a branch touches only its own row's file.

```
knowledge/programs/rows/PG-NN.json   one program row  (STRUCTURE)
knowledge/programs.md.tmpl           the committed SHELL: prose + `<!-- GENERATED -->` marker
knowledge/programs.md                the table, RENDERED from the shell + rows/ (not committed)
knowledge/slices/rows/SL-NNN.json    one slice row
knowledge/slices.md.tmpl             the committed shell
knowledge/slices.md                  the table, RENDERED (not committed)
```

**The table is not committed.** A derived file that unrelated changes all edit is generated
where it is read, so the register leaves git and only its hand-authored shell stays. The
`fleet_knowledge` readers read the fragments directly (`fleet_knowledge.registers`: fragments
win), so the rendered table is for a person reading the register and for the tools that still
parse it; render it before reading the corpus with anything else
(`python3 knowledge/scripts/gen_knowledge_registers.py`). `--check` re-derives in memory and
fails on a corpus that cannot render (a malformed fragment, a shell missing its anchor), and on
a rendered register present on disk that disagrees with its fragments.

**An empty register renders.** A corpus that has a shell and no rows yet — a new corpus, or a
tier nobody has cut into — renders the header and no rows. It is a register with nothing in
it, not a broken one. A corpus with neither a shell nor a register has no such tier, and is
skipped.

The fragment filename IS the row id — there is no `id:` field inside it. A fragment is JSON
mapping each column to its cell: a string for a scalar cell, a list of strings for a
comma-list cell. JSON rather than markdown frontmatter so a cell can hold any text and so a
`done_when` that cites a relative link is not re-resolved by the markdown path scanners. The
optional prose detail file (`knowledge/slices/SL-NNN.md`) is untouched and still lives beside
the register; it holds no structure.

The table tail — a `<!-- GENERATED: ... -->` marker line and the table itself — is what this
generator owns. The prose above it is hand-authored and preserved verbatim from the shell. A
legacy `<!-- APPEND ONLY. Next id: ... -->` counter is still accepted as the anchor and
replaced by the marker on the next write: ids are reserved as claim refs
(`knowledge/scripts/validate_id_collisions.py --allocate`), so no shared line names the next
id.

Usage:
    python3 knowledge/scripts/gen_knowledge_registers.py                # render the tables
    python3 knowledge/scripts/gen_knowledge_registers.py --check        # fail if any cannot be derived
    python3 knowledge/scripts/gen_knowledge_registers.py --write-shell  # derive the shells (one-time)
    ... --root <repo>                                                   # another checkout

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

#: The anchor above the generated region: the marker this generator writes, or the legacy
#: `Next id:` counter it replaces.
ANCHOR_RE = re.compile(r"^<!-- (?:APPEND ONLY\. Next id: [A-Z]{2,5}-\d+|GENERATED: [^\n]*?) -->$", re.M)

#: The hand-authored shell that carries a register's prose and its anchor. `programs.md.tmpl`
#: rather than `.md` so the knowledge validators, which glob `*.md`, never mistake the
#: prose-only shell for a register.
SHELL_SUFFIX = ".tmpl"

EMPTY = "—"  # the em-dash the registers use for an empty cell

#: kind -> (register file, rows dir, columns), all knowledge-relative. The column tuple is
#: `(fragment key, table header, is_list)`.
REGISTERS: dict[str, dict[str, Any]] = {
    "program": {
        "register": "programs.md",
        "rows_dir": "programs/rows",
        "columns": (
            ("name", "Name", False),
            ("kind", "Kind", False),
            ("verified_by", "Verified by", True),
            ("requires", "Requires", True),
            ("disposition", "Disposition", False),
        ),
    },
    "slice": {
        "register": "slices.md",
        "rows_dir": "slices/rows",
        "columns": (
            ("name", "Name", False),
            ("kind", "Kind", False),
            ("program", "Program", False),
            ("done_when", "Done when", False),
            ("verified_by", "Verified by", True),
            ("depends_on", "Depends on", True),
            ("components", "Components", True),
            ("disposition", "Disposition", False),
        ),
    },
}


class RenderError(Exception):
    """A register that cannot be derived from its shell and fragments."""


class Corpus:
    """Where one checkout's registers live. Every path is derived from `repo`."""

    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.knowledge = repo / "knowledge"

    def show(self, path: Path) -> str:
        """A path the way a reader can use it — repo-relative when it is inside the repo."""
        try:
            return str(path.relative_to(self.repo))
        except ValueError:
            return str(path)

    def register(self, kind: str) -> Path:
        return self.knowledge / str(REGISTERS[kind]["register"])

    def rows_dir(self, kind: str) -> Path:
        return self.knowledge / str(REGISTERS[kind]["rows_dir"])


def shell_path(register: Path) -> Path:
    return register.with_name(register.name + SHELL_SUFFIX)


def prose_source(register: Path) -> Path | None:
    """The committed shell when it exists, else the register (a corpus mid-migration), else
    `None`: this corpus has no such tier."""
    shell = shell_path(register)
    if shell.is_file():
        return shell
    return register if register.is_file() else None


def read_fragment(path: Path) -> dict[str, Any]:
    """The row's cells, parsed from a fragment's JSON."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RenderError(f"{path}: not a readable JSON row fragment ({exc})") from exc
    if not isinstance(data, dict):
        raise RenderError(f"{path}: a row fragment is a JSON object of cells, got {type(data).__name__}")
    return cast(dict[str, Any], data)


def _number(stem: str) -> int:
    _, _, digits = stem.partition("-")
    return int(digits) if digits.isdigit() else 0


def rows_for(corpus: Corpus, kind: str) -> list[dict[str, Any]]:
    base = corpus.rows_dir(kind)
    rows: list[dict[str, Any]] = []
    if not base.is_dir():
        return rows
    for path in sorted(base.glob("*.json")):
        row = read_fragment(path)
        row["_id"] = path.stem
        row["_num"] = _number(path.stem)
        rows.append(row)
    rows.sort(key=lambda r: (r["_num"], r["_id"]))
    return rows


def _escape(text: str) -> str:
    """A literal `|` inside a cell is written `\\|` — the markdown table's own escape."""
    return text.replace("|", "\\|")


def _render_cell(value: Any, is_list: bool) -> str:
    if is_list:
        items = [str(v) for v in (value or [])]
        return _escape(", ".join(items)) if items else EMPTY
    text = "" if value is None else str(value)
    return _escape(text) if text else EMPTY


def _cell_value(kind: str, row: dict[str, Any], key: str) -> Any:
    """A fragment's value for one column. A slice's AREA rides in its `Program`
    cell as `area:<slug>`, after the program when there is one (`<program>, area:<slug>`) — the table keeps
    its nine columns and every reader splits it back (`fleet_knowledge.planningmode.split_home_cell`)."""
    if kind == "slice" and key == "program" and row.get("area"):
        return ", ".join(str(x) for x in (row.get("program"), f"area:{row['area']}") if x)
    return row.get(key)


def render_region(corpus: Corpus, kind: str) -> str:
    """The marker comment plus the table — everything from the marker to end of file."""
    cfg = REGISTERS[kind]
    columns: tuple[tuple[str, str, bool], ...] = cfg["columns"]
    headers = ["ID"] + [h for _, h, _ in columns]
    lines = [
        f"| {' | '.join(headers)} |",
        "|" + "---|" * len(headers),
    ]
    for row in rows_for(corpus, kind):
        cells = [row["_id"]] + [_render_cell(_cell_value(kind, row, key), is_list) for key, _, is_list in columns]
        lines.append(f"| {' | '.join(cells)} |")
    marker = f"<!-- GENERATED: one row per file in {cfg['rows_dir']}/ — edit a fragment, never this table -->"
    return f"{marker}\n\n" + "\n".join(lines) + "\n"


def render(corpus: Corpus, kind: str) -> str | None:
    """The full register file — the hand-authored prefix plus the generated region — or
    `None` when this corpus has no such register at all."""
    source = prose_source(corpus.register(kind))
    if source is None:
        return None
    current = source.read_text(encoding="utf-8")
    m = ANCHOR_RE.search(current)
    if not m:
        raise RenderError(f"{corpus.show(source)}: no `<!-- GENERATED: ... -->` marker above the table")
    return current[: m.start()] + render_region(corpus, kind)


def check(corpus: Corpus) -> int:
    """Every register renders from its shell and fragments; a rendered copy on disk agrees."""
    failed = False
    for kind in REGISTERS:
        target = corpus.register(kind)
        try:
            expected = render(corpus, kind)
        except RenderError as exc:
            print(exc, file=sys.stderr)
            failed = True
            continue
        if expected is None or not target.is_file() or not shell_path(target).is_file():
            continue
        current = target.read_text(encoding="utf-8")
        if current == expected:
            continue
        failed = True
        for i, (want, got) in enumerate(zip(expected.splitlines(), current.splitlines(), strict=False), 1):
            if want != got:
                print(
                    f"{corpus.show(target)}:{i}: table is STALE — render it, never hand-edit it:\n"
                    f"  expected: {want}\n"
                    f"  on disk:  {got}",
                    file=sys.stderr,
                )
                break
        else:
            print(
                f"{corpus.show(target)}: length differs from the rendered table (a row was added or removed by hand)",
                file=sys.stderr,
            )
    return 1 if failed else 0


def write(corpus: Corpus) -> int:
    for kind in REGISTERS:
        target = corpus.register(kind)
        try:
            text = render(corpus, kind)
        except RenderError as exc:
            print(exc, file=sys.stderr)
            return 1
        if text is None:
            continue
        if not shell_path(target).is_file():
            # A corpus that has not split its register keeps the committed table as the source;
            # rewriting it in place would make the source a generated file.
            continue
        if not target.is_file() or target.read_text(encoding="utf-8") != text:
            target.write_text(text, encoding="utf-8")
            print(f"wrote {corpus.show(target)}")
    return 0


def write_shell(corpus: Corpus) -> int:
    """Write each register's prose-only shell from the current register (one-time migration)."""
    for kind in REGISTERS:
        target = corpus.register(kind)
        if not target.is_file():
            print(f"{corpus.show(target)}: no register to derive a shell from", file=sys.stderr)
            return 1
        current = target.read_text(encoding="utf-8")
        m = ANCHOR_RE.search(current)
        if not m:
            print(f"{corpus.show(target)}: no `<!-- GENERATED: ... -->` marker above the table", file=sys.stderr)
            return 1
        shell = shell_path(target)
        shell.write_text(current[: m.start()] + m.group(0) + "\n", encoding="utf-8")
        print(f"wrote {corpus.show(shell)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=None, help="the checkout to render (default: this one)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="fail if a register cannot be derived or is stale")
    group.add_argument("--write", action="store_true", help="render the register tables (default)")
    group.add_argument(
        "--write-shell",
        action="store_true",
        dest="write_shell",
        help="derive each register's prose-only shell from its current table (one-time migration)",
    )
    args = parser.parse_args(argv)
    corpus = Corpus((args.root or _repo.repo_root()).resolve())
    if args.write_shell:
        return write_shell(corpus)
    return check(corpus) if args.check else write(corpus)


if __name__ == "__main__":
    raise SystemExit(main())
