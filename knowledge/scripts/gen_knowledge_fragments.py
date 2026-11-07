#!/usr/bin/env python3
"""Render the fragment-backed requirement registers and feature maps from one file per row.

Also renders each feature map's `source_of_truth:` frontmatter list from one file per path.

A requirement register (`knowledge/requirements/<domain>.md`) and a feature map
(`knowledge/features/<area>.md`) are tables that every branch adding or editing a commitment or
a capability used to edit in place, so two concurrent PRs touching *different* rows still
collided. Each row now lives in its own fragment and the table is rebuilt from the fragments,
so a branch touches only its own row's file — the same split the program and slice registers
use (`gen_knowledge_registers.py`, a separate generator writing disjoint files).

**The tables are not committed.** Each fragment-backed register or map keeps only its
hand-authored shell in git (`<name>.md.tmpl` — the prose, the table headers and the
`<!-- rows: -->` markers); the `.md` is rendered on demand
(`python3 knowledge/scripts/gen_knowledge_fragments.py`) and is gitignored. **A shell is what
makes a file a target**: every `<name>.md.tmpl` under `knowledge/requirements/` and
`knowledge/features/` is rendered, and nothing else is — a register still authored as a whole
committed table has no shell and is left alone. `--check` re-derives in memory and fails on a
corpus that cannot render (a malformed fragment, a shell missing a marker), on a rendered file
present on disk that disagrees with its fragments, on a row written into a table outside any
generated region (a reader of the fragments would never see it), and on an orphan fragment whose
`<stem>#` names no register at all (it renders nowhere), and — in a git checkout — on a
rendered table git would commit.

```
knowledge/features/rows/CAP-NNNN.json        one capability row
knowledge/features/<area>.md.tmpl            the committed SHELL (prose + markers)
knowledge/features/<area>.md                 table RENDERED from the rows (not committed)
knowledge/requirements/rows/<PFX>-NNN.json   one commitment row
knowledge/requirements/<domain>.md.tmpl      the committed shell
knowledge/requirements/<domain>.md           table RENDERED (not committed)
```

The same split covers a feature map's own `source_of_truth:` list: each path lives in its own
fragment under `knowledge/features/source_of_truth/<area>/<slug>.json`
(`{"order": N, "path": "..."}`, the filename derived from the path so adding one creates a new
file), and the rendered `source_of_truth:` is a YAML block list, one path per line, sorted by
path — two PRs that each add a different path insert at different lines.

Each generated table is anchored by a marker comment on the line immediately above its header:

    <!-- rows: <file-stem>#<table> -->

The marker names the row set; every fragment whose JSON `table` field equals that key belongs
to it. A fragment holds the cells AFTER the id — the id is the filename stem — as plain strings,
exactly as rendered, plus an `order` integer that fixes its place. Order is explicit, not the
id's numeric value: these tables are not append-ordered (an id minted later can sit above an
older one because that is where it belongs topically). A marker with no fragments at all is an
error rather than an empty table: a generated region that loses every row is far more often a
lost set of files than a decision to empty it.

Usage:
    python3 knowledge/scripts/gen_knowledge_fragments.py                # render the tables
    python3 knowledge/scripts/gen_knowledge_fragments.py --check        # fail if any cannot be derived
    python3 knowledge/scripts/gen_knowledge_fragments.py --write-shell  # derive the shells (one-time)
    ... --root <repo>                                                   # another checkout

Stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

#: The two corpus directories whose `<name>.md.tmpl` shells this generator renders.
TARGET_DIRS = ("requirements", "features")
#: The rows directory beside each target dir — one shared `rows/` per directory, keyed by the
#: fragment's `table` (`<file-stem>#<table>`).
ROWS_SUBDIR = "rows"

#: `<!-- rows: <key> -->` — the anchor a generated table hangs off. `\S+` because a key is a
#: bare slug (`connections#browse-the-catalog`), never prose.
MARKER_RE = re.compile(r"^<!-- rows: (\S+) -->$")
#: A data row: `| <ID> | …`. A legend or column table's rows never start with an id, so only
#: real rows are collected.
ROW_RE = re.compile(r"^\|\s*([A-Z]{2,5}-\d{3,})\s*\|")
SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")
#: A capability row in a feature-map shell: `| CAP-NNNN | … |`.
CAP_ROW_RE = re.compile(r"(?m)^[ \t]*\|\s*(CAP-\d{4})\s*\|")

#: A map's `source_of_truth:` frontmatter field: the key line followed by its contiguous
#: `  - <path>` lines. A legacy inline list (`source_of_truth: [a, b]`) still matches. Anchored,
#: so `source_of_truth_broad_ok:` never matches; `[ \t]+` keeps a blank line or the next key
#: from being swallowed.
SOT_LINE_RE = re.compile(r"^source_of_truth:[^\n]*(?:\n[ \t]+-[^\n]*)*", re.M)

#: The hand-authored shell suffix. `<name>.md.tmpl` rather than `.md` so the knowledge
#: validators, which glob `*.md`, never mistake the prose-only shell for a map or register.
SHELL_SUFFIX = ".tmpl"


class RenderError(Exception):
    """A table that cannot be derived from its shell and fragments."""


class Corpus:
    """Where one checkout's fragment-backed tables live. Every path is derived from `repo`."""

    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.knowledge = repo / "knowledge"
        self.features = self.knowledge / "features"
        self.requirements = self.knowledge / "requirements"
        self.sot_dir = self.features / "source_of_truth"

    def show(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.repo))
        except ValueError:
            return str(path)

    def targets(self) -> list[Path]:
        """Every fragment-backed file: each `<name>.md.tmpl` shell's `<name>.md`."""
        out: list[Path] = []
        for name in TARGET_DIRS:
            base = self.knowledge / name
            if base.is_dir():
                shells = sorted(base.glob(f"*.md{SHELL_SUFFIX}"))
                out += [shell.with_name(shell.name[: -len(SHELL_SUFFIX)]) for shell in shells]
        return out

    def feature_maps(self) -> list[Path]:
        """Every feature map (`knowledge/features/<area>.md`), README excluded, discovered
        through its shell too, so a map whose `.md` is a rendered artifact is still seen."""
        if not self.features.is_dir():
            return []
        names = {p.name for p in self.features.glob("*.md")}
        names |= {p.name[: -len(SHELL_SUFFIX)] for p in self.features.glob(f"*{SHELL_SUFFIX}")}
        return [self.features / n for n in sorted(names) if n != "README.md"]

    def sot_targets(self) -> list[Path]:
        """Feature maps whose `source_of_truth:` list the fragments own."""
        out: list[Path] = []
        for p in self.feature_maps():
            source = prose_source(p)
            if source.is_file() and SOT_LINE_RE.search(source.read_text(encoding="utf-8")):
                out.append(p)
        return out

    def all_sources(self) -> list[Path]:
        """Every file this generator owns, once each."""
        sources = self.targets()
        sources += [p for p in self.sot_targets() if p not in sources]
        return sources


def shell_path(register: Path) -> Path:
    return register.with_name(register.name + SHELL_SUFFIX)


def prose_source(register: Path) -> Path:
    """The committed shell when it exists, else the file itself (a corpus mid-migration)."""
    shell = shell_path(register)
    return shell if shell.is_file() else register


# ─────────────────────────── source_of_truth fragments ───────────────────────────


def sot_slug(path: str) -> str:
    """A stable, collision-resistant filename stem for one `source_of_truth` path.

    Derived from the path itself — never a position — so adding a path creates a *new* file. A
    short hash of the exact string disambiguates paths that sanitise alike.
    """
    stem = re.sub(r"[^A-Za-z0-9]+", "-", path).strip("-").lower()
    stem = stem[:60].rstrip("-")
    digest = hashlib.sha1(path.encode("utf-8")).hexdigest()[:8]
    return f"{stem}-{digest}" if stem else digest


def load_sot_paths(corpus: Corpus, area: str) -> list[str] | None:
    """The `source_of_truth` paths for one map, sorted, or `None` when the map has no
    fragments directory at all (an error for a map whose shell carries the field)."""
    base = corpus.sot_dir / area
    if not base.is_dir():
        return None
    paths: list[str] = []
    seen: set[str] = set()
    for f in sorted(base.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        path = str(data.get("path") or "")
        if not path:
            raise RenderError(f"{corpus.show(f)}: fragment has no `path`")
        if not isinstance(data.get("order"), int):
            raise RenderError(f"{corpus.show(f)}: fragment has no integer `order`")
        if path in seen:
            raise RenderError(f"{corpus.show(f)}: duplicate `source_of_truth` path `{path}`")
        seen.add(path)
        paths.append(path)
    return sorted(paths)


def generate_source_of_truth(corpus: Corpus, text: str, paths: list[str], source: Path) -> str:
    m = SOT_LINE_RE.search(text)
    if not m:
        raise RenderError(f"{corpus.show(source)}: no `source_of_truth:` line to generate")
    block = "source_of_truth:\n" + "\n".join(f"  - {p}" for p in sorted(paths))
    return text[: m.start()] + block + text[m.end() :]


def render_map_sot_text(corpus: Corpus, text: str, source: Path) -> str:
    paths = load_sot_paths(corpus, source.stem)
    if paths is None:
        raise RenderError(
            f"{corpus.show(source)}: has `source_of_truth:` but no fragments under "
            f"{corpus.show(corpus.sot_dir / source.stem)} — migrate it, never hand-edit the line"
        )
    return generate_source_of_truth(corpus, text, paths, source)


# ─────────────────────────── table fragments ───────────────────────────


def render_row(row_id: str, cells: list[str]) -> str:
    return "| " + " | ".join([row_id, *cells]) + " |"


def read_fragment(corpus: Corpus, path: Path) -> tuple[str, str, int, list[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RenderError(f"{corpus.show(path)}: not a readable JSON row fragment ({exc})") from exc
    table = str(data.get("table") or "")
    cells = [str(c) for c in (data.get("cells") or [])]
    if not table:
        raise RenderError(f"{corpus.show(path)}: fragment has no `table` key")
    order = data.get("order")
    if not isinstance(order, int):
        raise RenderError(f"{corpus.show(path)}: fragment has no integer `order` key")
    return path.stem, table, order, cells


def _number(row_id: str) -> int:
    _, _, digits = row_id.partition("-")
    return int(digits) if digits.isdigit() else 0


def load_rows(corpus: Corpus, rows_dir: Path) -> dict[str, list[tuple[str, list[str]]]]:
    """`{table key -> [(row id, cells)]}`, in the order the `order` fields fix; the tie-break
    is the id's number, so two branches that appended at the same position still agree."""
    out: dict[str, list[tuple[int, str, list[str]]]] = {}
    if not rows_dir.is_dir():
        return {}
    for path in sorted(rows_dir.glob("*.json")):
        row_id, table, order, cells = read_fragment(corpus, path)
        out.setdefault(table, []).append((order, row_id, cells))
    return {
        table: [(row_id, cells) for _, row_id, cells in sorted(rows, key=lambda r: (r[0], _number(r[1]), r[1]))]
        for table, rows in out.items()
    }


def generate(corpus: Corpus, text: str, rows_by_table: dict[str, list[tuple[str, list[str]]]], source: Path) -> str:
    """Rebuild every marked table from its fragments, preserving all other text verbatim."""
    lines = text.split("\n")
    out: list[str] = []
    seen: set[str] = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = MARKER_RE.match(line)
        i += 1
        if not m:
            continue
        key = m.group(1)
        seen.add(key)
        if key not in rows_by_table:
            raise RenderError(f"{corpus.show(source)}: marker `{key}` has no row fragments")
        if i + 1 >= len(lines) or not lines[i].startswith("|"):
            raise RenderError(f"{corpus.show(source)}: marker `{key}` is not followed by a table header")
        header, separator = lines[i], lines[i + 1]
        if not SEP_RE.match(separator.strip()):
            raise RenderError(f"{corpus.show(source)}: marker `{key}` is not followed by a header separator")
        out.append(header)
        out.append(separator)
        i += 2
        # Consume the stale data rows (contiguous `|`-starting lines) and replace them. A
        # fragment reproduces its row's cells exactly, including a row whose cell count differs
        # from the header's: the readers read columns by name and tolerate both.
        while i < len(lines) and lines[i].startswith("|"):
            i += 1
        for row_id, cells in rows_by_table[key]:
            out.append(render_row(row_id, cells))
    orphans = set(rows_by_table) - seen
    if orphans:
        raise RenderError(f"{corpus.show(source)}: row fragments for unknown table(s): {sorted(orphans)}")
    return "\n".join(out)


def render_register(corpus: Corpus, source: Path) -> str:
    """The full register or map: prose from the committed shell, then the generated tables and
    — for a feature map — its generated `source_of_truth:` list, in one pass."""
    text = prose_source(source).read_text(encoding="utf-8")
    if shell_path(source).is_file():
        # The rows dir is shared by every file in the directory, keyed `<file-stem>#<table>`; a
        # file's table set is its own key prefix and the rest belong to its siblings.
        prefix = source.stem + "#"
        rows = {k: v for k, v in load_rows(corpus, source.parent / ROWS_SUBDIR).items() if k.startswith(prefix)}
        text = generate(corpus, text, rows, source)
    if source.parent == corpus.features and SOT_LINE_RE.search(text):
        text = render_map_sot_text(corpus, text, source)
    return text


def unmarked_rows(corpus: Corpus) -> list[str]:
    """Every row written into a requirement register OUTSIDE a generated table.

    The readers read a fragment-backed register's rows from `requirements/rows/<ID>.json`, so a
    row typed straight into a table with no `<!-- rows: -->` marker in such a register is
    invisible to every reader — its id stops resolving. A register with no shell (still a whole
    committed table) is its own source, and its rows are read from the table, so it is not
    flagged.
    """
    base = corpus.requirements
    out: list[str] = []
    if not base.is_dir():
        return out
    for path in sorted(base.glob("*.md")):
        if path.name == "README.md" or path.stem.startswith("_") or not shell_path(path).is_file():
            continue
        in_marked = False
        for n, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            if MARKER_RE.match(line):
                in_marked = True
                continue
            if not line.startswith("|"):
                in_marked = False
                continue
            m = ROW_RE.match(line)
            if m and not in_marked:
                out.append(
                    f"{corpus.show(path)}:{n}: `{m.group(1)}` is a row written into the register's table, "
                    "outside any `<!-- rows: -->` generated table — every requirement row is a file under "
                    "`knowledge/requirements/rows/<ID>.json`; add it there and run "
                    "`python3 knowledge/scripts/gen_knowledge_fragments.py`"
                )
    return out


def unmarked_feature_rows(corpus: Corpus) -> list[str]:
    """Every capability row written inline in a feature-map SHELL with no row fragment.

    A capability row typed straight into the shell reaches a read of the rendered tree but not a
    read of the committed tree (which sees the fragments alone), so its id reads as both minted
    here and already in history — a false collision the introducing change cannot see.
    """
    rows_dir = corpus.features / ROWS_SUBDIR
    fragments = {p.stem for p in rows_dir.glob("CAP-*.json")} if rows_dir.is_dir() else set()
    out: list[str] = []
    if not corpus.features.is_dir():
        return out
    for path in sorted(corpus.features.glob(f"*{SHELL_SUFFIX}")):
        for cid in sorted(set(CAP_ROW_RE.findall(path.read_text(encoding="utf-8"))) - fragments):
            out.append(
                f"{corpus.show(path)}: `{cid}` is a capability row written inline in a feature-map shell with "
                f"no `knowledge/features/rows/{cid}.json` fragment — a read of the committed tree cannot see "
                f"it. Move it to `knowledge/features/rows/{cid}.json` behind a `<!-- rows: -->` marker and run "
                "`python3 knowledge/scripts/gen_knowledge_fragments.py`"
            )
    return out


def orphan_fragments(corpus: Corpus) -> list[str]:
    """Every row fragment whose `table` key names a register that does not exist at all.

    A fragment keyed `<stem>#<table>` belongs to `<stem>.md`: rendered from `<stem>.md.tmpl`, or a
    whole committed `<stem>.md` whose readers take the fragments over its table. With neither — a
    shell never written, or a register deleted while its rows stayed — the row renders nowhere and
    no reader of any register ever sees it.
    """
    out: list[str] = []
    for name in TARGET_DIRS:
        base = corpus.knowledge / name
        rows_dir = base / ROWS_SUBDIR
        if not rows_dir.is_dir():
            continue
        for path in sorted(rows_dir.glob("*.json")):
            try:
                table = str(json.loads(path.read_text(encoding="utf-8")).get("table") or "")
            except (OSError, json.JSONDecodeError, AttributeError):
                continue  # an unreadable fragment is reported by the render it breaks
            stem = table.split("#", 1)[0]
            register = base / f"{stem}.md"
            if stem and not shell_path(register).is_file() and not register.is_file():
                out.append(
                    f"{corpus.show(path)}: an orphan row — its table `{table}` names "
                    f"`{name}/{stem}.md`, which has neither a `{stem}.md.tmpl` shell nor a committed table, so it "
                    "renders nowhere; add the shell or move the row to the register it belongs to"
                )
    return out


def unignored_renders(corpus: Corpus) -> list[str]:
    """Every rendered target (a `.md` beside its `.md.tmpl` shell) that git would commit.

    The rendered table is derived and must stay out of git, or the next `git add -A` commits a
    table that two branches adding different rows collide on. Outside a git work tree there is
    nothing to commit and nothing is reported.
    """
    targets = corpus.targets()
    if not targets:
        return []
    rels = [corpus.show(t) for t in targets]
    try:
        proc = subprocess.run(
            ["git", "-C", str(corpus.repo), "check-ignore", "--no-index", "--stdin"],
            input="\n".join(rels) + "\n",
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    if proc.returncode not in (0, 1):
        return []  # not a git work tree
    ignored = set(proc.stdout.split())
    return [
        f"{rel}: the rendered table is not gitignored — add `{rel}` to .gitignore; it is generated "
        "from its shell and fragments and must never be committed"
        for rel in rels
        if rel not in ignored
    ]


def check(corpus: Corpus) -> int:
    """Every table and `source_of_truth:` list renders; a rendered copy on disk agrees."""
    failed = False
    for problem in (
        *unmarked_rows(corpus),
        *unmarked_feature_rows(corpus),
        *orphan_fragments(corpus),
        *unignored_renders(corpus),
    ):
        print(problem, file=sys.stderr)
        failed = True
    for source in corpus.all_sources():
        try:
            expected = render_register(corpus, source)
        except RenderError as exc:
            print(exc, file=sys.stderr)
            failed = True
            continue
        if not source.is_file():
            continue
        current = source.read_text(encoding="utf-8")
        if current == expected:
            continue
        failed = True
        for n, (want, got) in enumerate(zip(expected.splitlines(), current.splitlines(), strict=False), 1):
            if want != got:
                print(
                    f"{corpus.show(source)}:{n}: STALE — render it from its fragments, never hand-edit it:\n"
                    f"  expected: {want}\n"
                    f"  on disk:  {got}",
                    file=sys.stderr,
                )
                break
        else:
            print(
                f"{corpus.show(source)}: length differs from the rendered table (a row or a "
                "`source_of_truth:` line was added or removed by hand)",
                file=sys.stderr,
            )
    return 1 if failed else 0


def write(corpus: Corpus) -> int:
    for source in corpus.all_sources():
        try:
            expected = render_register(corpus, source)
        except RenderError as exc:
            print(exc, file=sys.stderr)
            return 1
        if not source.is_file() or source.read_text(encoding="utf-8") != expected:
            source.write_text(expected, encoding="utf-8")
            print(f"wrote {corpus.show(source)}")
    return 0


def _strip_rows(text: str) -> str:
    """The shell: the prose, markers and table headers, with the generated data rows removed."""
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        if not MARKER_RE.match(line):
            continue
        for _ in range(2):  # the header and its separator
            if i < len(lines):
                out.append(lines[i])
                i += 1
        while i < len(lines) and lines[i].startswith("|"):
            i += 1
    return "\n".join(out)


def write_shell(corpus: Corpus, names: list[str]) -> int:
    """Derive the prose-only shell of each named register (`requirements/<domain>.md`,
    `features/<area>.md`, knowledge-relative) from its current table. One-time migration."""
    if not names:
        print("--write-shell names the registers to split, e.g. requirements/<domain>.md", file=sys.stderr)
        return 2
    for name in names:
        source = corpus.knowledge / name
        if not source.is_file():
            print(f"{corpus.show(source)}: no register to derive a shell from", file=sys.stderr)
            return 1
        shell = shell_path(source)
        shell.write_text(_strip_rows(source.read_text(encoding="utf-8")), encoding="utf-8")
        print(f"wrote {corpus.show(shell)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=None, help="the checkout to render (default: this one)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="fail if any table cannot be derived or is stale")
    mode.add_argument(
        "--write-shell",
        nargs="*",
        metavar="REGISTER",
        dest="write_shell",
        help="derive the named registers' prose-only shells from their current tables (one-time migration)",
    )
    args = parser.parse_args(argv)
    corpus = Corpus((args.root or _repo.repo_root()).resolve())
    if args.write_shell is not None:
        return write_shell(corpus, list(args.write_shell))
    return check(corpus) if args.check else write(corpus)


if __name__ == "__main__":
    raise SystemExit(main())
