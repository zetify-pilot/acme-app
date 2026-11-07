"""The ONE reader for the per-domain requirement registers.

A requirement register (`<root>/requirements/<domain>.md`) is the place a commitment is
written down exactly once: an invariant, a constraint, an alternative we refused, a thing we
decided not to build. Prose cites the id; it never restates the sentence. Each register
declares the id namespace it owns in its own frontmatter (`prefix: RUN`), which is what lets
a second domain register land without a line of code changing.

**Per-row fragments win when they exist (ENG-12980 / FLT-045).** When
`<root>/requirements/rows/<ID>.json` holds rows for a domain — the same split ENG-12660
landed so two branches editing different commitments no longer collide on a shared table —
those fragments are the source and the committed table body is never opened. The register
file is still read for its frontmatter, source legend, section headings and the
`<!-- rows: <key> -->` markers that name each table's column layout. A corpus that has not
migrated a domain has no fragments for it and reads its table exactly as before, so the same
package serves both ends of the migration (the programs/slices precedent: ENG-12549,
ENG-12661).

**This module reads; it does not judge.** Structural problems — a malformed id, a duplicate,
a prefix that does not match the register's own, an off-vocabulary Kind or Disposition — are
returned as findings alongside the rows, so a *validator* can fail a build on them and a
*viewer* can render what parsed and say so. Splitting the two would give the corpus two
readers that disagree about what a row IS, which is the failure the register format exists
to prevent one level up.

Stdlib only.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from . import corpusref

# ─────────────────────────── the register grammar ───────────────────────────
#
# One definition, here, because every reader of a row has to agree about what a row IS. A
# vocabulary added in one reader and not another produces two views of the same corpus that
# both look authoritative on their own screen — the exact failure the register format exists
# to prevent one level up.

# `{2,5}` keeps the id space wide enough for a five-letter domain prefix while staying narrow
# enough that a bare capitalised word in prose is not mistaken for an id. >=3 digits: a
# register is authored in the hundreds from day one.
ID_RE = re.compile(r"^([A-Z]{2,5})-(\d{3,})$")
ID_REF_RE = re.compile(r"\b[A-Z]{2,5}-\d{3,}\b")  # ids referenced inside a cell (Needs)
PREFIX_RE = re.compile(r"^[A-Z]{2,5}$")

# What the assertion IS.
KINDS = frozenset({"invariant", "requirement", "constraint", "alternative", "accepted", "excluded"})

# The two kinds that record a SETTLED decision rather than work, and so can never be claimed
# by a PRD: `accepted` is a cost we took on purpose, `excluded` a capability we refuse to
# build. Both are outcomes, not backlog — a row of either kind is not work waiting in any
# release line. ONE definition: the status derivation reads it to split a headline that would
# otherwise count them as unscheduled work, and the knowledge model reads it to mark the rows
# that must not carry a call to action.
SETTLED_KINDS = frozenset({"accepted", "excluded"})
# What HAPPENED to it. `superseded` is handled separately — it carries a payload.
DISPOSITIONS = frozenset({"adopted", "rejected", "open"})
# Bare `superseded` (no successor) is sanctioned for a commitment dropped without a
# replacement; refusing it would fail rows a corpus deliberately authored. `(confirmed)` is
# the bare form's own way of being satisfied: an aggregate "N rows carry a bare `superseded`"
# note otherwise re-asks the same question on every run with no way to answer it, even for a
# row whose own Statement already explains the drop. The marker is that answer, recorded
# where a reader is already looking rather than in a column invented for one flag.
#: The successor may be repo-qualified (`superseded by acme:RUN-001`): a row restated in
#: another corpus forwards there, and the token keeps its qualifier.
SUPERSEDED_RE = re.compile(r"^superseded(?:\s+by\s+((?:[a-z][a-z0-9-]*:)?[A-Z]{2,5}-\d{3,})|\s+\(confirmed\))?$")

REQUIRED_COLUMNS = ("ID", "Statement", "Kind", "Disposition", "Source")

# The premise edge's discharge token. A row records the premise its decision rested on
# (`Because: <id>`); when that premise MOVES — is superseded or rejected — the rows resting on
# it surface for re-reading. Discharge is ONE token, `reaffirmed=YYYY-MM-DD`, marking that a
# human re-read the row and attested it still holds. An authored input, never a status: a
# missing one means "not re-read since the premise moved", not "unsettled".
REAFFIRMED_RE = re.compile(r"reaffirmed\s*=\s*(\d{4}-\d{2}-\d{2})")

# The third orthogonal axis. `Kind` says what the assertion IS, `Disposition` says what
# HAPPENED to it, and `Cut` says WHICH RELEASE LINE IT LANDS IN — which the first two cannot
# express, because a deferred row keeps `Disposition: adopted` and so reads identically to a
# row nobody has thought about since it was written.
#
# A COLUMN rather than a fifth `Disposition` value, deliberately: a new column is additive,
# while adding `deferred` to the enum would silently redefine what every existing `adopted`
# row means, since all of them were authored under a vocabulary in which `adopted` already
# covered the deferred case.
#
# **The value names the line the row lands in, never the one it was cut out of.** Blank is the
# norm and stays legal everywhere: it means *this row is in the line being built*. A value is
# legal ONLY on an `adopted` row. Widening this tuple for a further line is a one-line change;
# which line is *current* is a validator's concern, not a reader's.
CUT_VALUES = ("v1", "v2")

SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")
#: A legend row's target: any repository file — a register cites code and tests as often as
#: documents — but never a web address, which no reader can resolve on disk.
LEGEND_LINK_RE = re.compile(r"\]\((?!https?:)([^)\s]+\.[A-Za-z0-9]+)\)")

# Prefixes a register may not claim, because another id namespace already owns that shape in
# the files a reader scans. An issue key (`ENG-4813`) is routinely written `[ENG-4813]` inside
# an acceptance criterion — the exact citation form — so a register with `prefix: ENG` would
# let an unrelated issue reference silently satisfy a coverage check. Cheap to forbid at
# authoring time; invisible later. A project with a different tracker passes its own set.
DEFAULT_RESERVED_PREFIXES = frozenset({"ENG"})

# The corpus-relative directory the registers live in. A default rather than a constant every
# caller repeats: `Config.requirements_dir` is what a project sets, and it reaches the reader
# through `dir_name` below — a config key nothing reads is a config key that lies.
REGISTER_SUBDIR = "requirements"
#: Per-row fragments live under `<root>/requirements/rows/<ID>.json` (ENG-12660). The
#: filename IS the id; the JSON carries `table` (the `<!-- rows: <key> -->` marker), an
#: integer `order`, and `cells` (everything after the id, in header order).
ROWS_SUBDIR = "rows"
#: `<!-- rows: connectors#source-legend -->` — anchors a generated table to its fragment set.
ROWS_MARKER_RE = re.compile(r"^<!-- rows: (\S+) -->$")

# Capability probe for a consuming repo's pin bump (ENG-12980): True iff this package
# reads requirement-register and feature-map row fragments when present, so the
# generated tables can leave git without external readers going dark.
FRAGMENT_BACKED_TABLES = True

# One structural problem: the file it is in, and what is wrong with it. The caller owns
# turning that into a message with its own path convention — which is what keeps this
# module free of any notion of "the repository root".
Finding = tuple[Path, str]


def frontmatter(text: str) -> str | None:
    """The YAML block, or None when the file has no frontmatter at all.

    Deliberately `None` and not `""`: a register WITHOUT frontmatter is a structural error a
    caller must report, and an empty block is not the same fact.
    """
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 else None


def field(fm: str, name: str) -> str | None:
    """A scalar frontmatter value, or None when absent or empty."""
    m = re.search(rf"^{name}:\s*(.+)$", fm, re.M)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'") or None


def idlist(fm: str, name: str) -> list[str]:
    """Ids declared as `name: [A, B]`, bare `name: A`, or a `- A` block.

    All three YAML spellings are accepted deliberately: a claim written in a form this
    parser does not see is a claim that silently escapes every check — the worst possible
    failure mode for a traceability edge.
    """
    inline = re.search(rf"^{name}:\s*\[(.*?)\]", fm, re.M | re.S)
    if inline:
        return [x.strip().strip('"').strip("'") for x in inline.group(1).split(",") if x.strip()]
    block = re.search(rf"^{name}:\s*$(.*?)(?=^\S|\Z)", fm, re.M | re.S)
    if block:
        out = []
        for line in block.group(1).splitlines():
            ls = line.strip()
            if ls.startswith("-"):
                v = ls[1:].strip().strip('"').strip("'")
                if v:
                    out.append(v)
        return out
    v = field(fm, name)
    return [v] if v else []


def id_refs(cell: str, own: str = "", keep: Iterable[str] = ()) -> list[str]:
    """The requirement ids a cell references (`Needs`, `Because`), in written order.

    A repo-qualified reference comes back WITH its qualifier (`fleet:FLT-104`); the bare-id scan
    runs over the cell with every qualified reference masked, so `fleet:FLT-104` is never read
    as this corpus's `FLT-104` (`:` is a word boundary, which is how it used to be).
    """
    # A qualified ref is kept whatever its id looks like: a malformed one (`fleet:flt-104`) must
    # reach the resolver and fail there, never vanish behind the mask. An OWN-qualified ref is
    # the local id (`own`), normalised here so nothing downstream reads it as foreign.
    cell = corpusref.localize_text(cell, own, keep)
    found: list[tuple[int, str]] = [(start, str(ref)) for ref, start, _end in corpusref.find_refs(cell)]
    found.extend((m.start(), m.group(0)) for m in ID_REF_RE.finditer(corpusref.mask(cell)))
    return [tok for _pos, tok in sorted(found)]


def cells(line: str) -> list[str]:
    """Split a markdown table row on UNESCAPED pipes (`\\|` is a literal pipe)."""
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def source_legend(path: Path, text: str) -> dict[str, Path]:
    """`{tag: target file}` from the register's own **Source legend** table.

    A register documents its own citation tags (`arch`, `D1` … `D10`, `0486`) in a
    two-column table whose right cell links the document each tag points at. Reading that
    table is what keeps this reader from hardcoding one project's sources: a second register
    with a different corpus needs no code change. A legend row that links nothing inherits
    the previous row's target, which is how the pair `arch §N "fragment"` / `arch §N:L` (*the
    same document*) is already written.
    """
    out: dict[str, Path] = {}
    prev: Path | None = None
    for line in text.splitlines():
        if not line.strip().startswith("| `"):
            continue
        row = cells(line)
        if len(row) < 2:
            continue
        # `arch §N "fragment"` -> arch;  `D1:L` -> D1;  ``0482 R#` · `0482 D#`` -> 0482
        key = row[0].split("·")[0].strip().strip("`").strip()
        tag = re.split(r"[\s:]", key)[0]
        if not tag:
            continue
        m = LEGEND_LINK_RE.search(row[1])
        target = (path.parent / m.group(1)).resolve() if m else prev
        if target is None:
            continue
        out[tag] = target
        prev = target
    return out


def register_dir(root: Path, dir_name: str = REGISTER_SUBDIR) -> Path:
    """Where the registers live. `Config.requirements_dir` names it; nothing else may."""
    return root / dir_name


SHELL_SUFFIX = ".md.tmpl"


def register_domain(path: Path) -> str:
    """A register file's domain — `fleet` for `fleet.md` and for its shell `fleet.md.tmpl`."""
    name = path.name
    return name[: -len(SHELL_SUFFIX)] if name.endswith(SHELL_SUFFIX) else path.stem


def registers(root: Path, dir_name: str = REGISTER_SUBDIR, *, shells: bool = False) -> list[Path]:
    """Every register file, derived from disk, never a hand list.

    A `README.md` is an index and a `_`-prefixed file is a draft — neither declares a
    `prefix:`, so reading them would produce a frontmatter error for a file that was never
    claiming to be a register.

    `shells`: also a fragment-backed register whose generated `<domain>.md` is ABSENT, through
    its committed `<domain>.md.tmpl` shell — the shell carries the frontmatter, legend and row
    markers, the rows come from `rows/*.json`. What a reader of a corpus it did not render
    (a sibling corpus, a git ref) needs: the rendered `.md` is gitignored and never committed.
    """
    base = register_dir(root, dir_name)
    if not base.is_dir():
        return []
    found = [f for f in base.glob("*.md") if f.name != "README.md" and not f.stem.startswith("_")]
    if shells:
        have = {f.stem for f in found}
        found += [
            f
            for f in base.glob(f"*{SHELL_SUFFIX}")
            if register_domain(f) not in have and not register_domain(f).startswith("_")
        ]
    return sorted(found)


def rows_dir(root: Path, dir_name: str = REGISTER_SUBDIR) -> Path:
    """Where requirement row fragments live: `<root>/<dir_name>/rows`."""
    return register_dir(root, dir_name) / ROWS_SUBDIR


def row_fragment_ids(root: Path, dir_name: str = REGISTER_SUBDIR) -> set[str]:
    """Every requirement id named by a `rows/<ID>.json` fragment, read by filename alone.

    `load_registers` reads a domain's fragments through its register `.md` shell (`fragments
    win when they exist for a domain`, keyed by the register's stem). A fragment-backed domain
    whose shell is committed as `<name>.md.tmpl` — the generated `.md` rendered on demand and
    never committed (ENG-12980 / FLT-045 phase 2) — has no `.md` for `registers()` to match,
    so its fragments are invisible to a reader that only walks the register files. That is
    exactly the tree a git-ref read and an interactive `--allocate` see (no render step runs
    first), and it let allocation hand out `CRD-198` while `rows/CRD-198.json` already
    existed (ENG-14286). The filename IS the id, so the id space is read from the fragments
    themselves, independent of whether their register shell has been rendered.
    """
    base = rows_dir(root, dir_name)
    if not base.is_dir():
        return set()
    return {f.stem for f in base.glob("*.json") if ID_RE.match(f.stem)}


def load_row_fragments(
    root: Path, dir_name: str = REGISTER_SUBDIR
) -> dict[str, list[tuple[int, str, list[str], Path]]]:
    """`{table key -> [(order, id, cells, path)]}` across every fragment, sorted by order then id.

    A fragment whose `table` is empty or whose stem is not a well-formed id is SKIPPED here —
    catching a malformed fragment is the gate's job, not this reader's. An absent directory
    is `{}`, which is what lets `load_registers` fall back to the committed table for every
    domain (the programs/slices shape: ENG-12661).
    """
    base = rows_dir(root, dir_name)
    if not base.is_dir():
        return {}
    out: dict[str, list[tuple[int, str, list[str], Path]]] = {}
    for f in sorted(base.glob("*.json")):
        if not ID_RE.match(f.stem):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        table = str(data.get("table") or "")
        order = data.get("order")
        raw_cells = data.get("cells")
        if not table or not isinstance(order, int) or not isinstance(raw_cells, list):
            continue
        cells_list = [str(c) for c in raw_cells]
        out.setdefault(table, []).append((order, f.stem, cells_list, f))
    for _table, rows in out.items():
        rows.sort(key=lambda r: (r[0], int(r[1].split("-", 1)[1])))
    return out


def table_layouts(text: str) -> dict[str, tuple[str, dict[str, int]]]:
    """`{table key -> (section heading, {column name: index})}` from markers + headers.

    Walks the register body the same way the table reader does for section headings, so a
    fragment-backed row lands under the same section a table-backed row would have. A marker
    whose following header is not a register table (no `ID` + `Statement`) is skipped.
    """
    lines = text.splitlines()
    layouts: dict[str, tuple[str, dict[str, int]]] = {}
    section = ""
    in_html_comment = False
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        scan = stripped
        line_in_comment = in_html_comment
        while scan:
            if in_html_comment:
                end = scan.find("-->")
                if end < 0:
                    line_in_comment = True
                    break
                line_in_comment = True
                scan = scan[end + 3 :]
                in_html_comment = False
                continue
            start = scan.find("<!--")
            if start < 0:
                break
            line_in_comment = True
            scan = scan[start + 4 :]
            in_html_comment = True
        # A rows marker IS an HTML comment (`<!-- rows: … -->`). Match it before the
        # comment-tracking would hide it: the marker is structure, not prose-about-a-row.
        m = ROWS_MARKER_RE.match(stripped)
        if m:
            key = m.group(1)
            # Header on the next non-empty line, separator after that.
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].lstrip().startswith("|"):
                header = cells(lines[j])
                if header and header[0] == "ID" and "Statement" in header:
                    layouts[key] = (section, {name: idx for idx, name in enumerate(header)})
            # A same-line `<!-- … -->` leaves in_html_comment False; nothing to reset.
            i += 1
            continue
        if not stripped.startswith("|") and not line_in_comment and stripped.startswith("#"):
            section = stripped.lstrip("#").strip()
        i += 1
    return layouts


def _accept_row(
    rid: str,
    row: list[str],
    cols: dict[str, int],
    *,
    prefix: str,
    section: str,
    legend: dict[str, Path],
    file: Path,
    line: int,
    register: Path,
    rows: dict[str, dict[str, Any]],
    rel: Callable[[Path], str],
    err: Callable[[Path, str], None],
    own: str = "",
    keep: frozenset[str] = frozenset(),
) -> None:
    """Validate one row's cells and record it, or append a finding and skip."""
    m = ID_RE.match(rid)
    if not m:
        err(file, f"line {line}: row id `{rid}` is not a well-formed `{prefix}-NNN` id")
        return
    rp, digits = m.group(1), m.group(2)
    if rp != prefix:
        err(file, f"line {line}: `{rid}` uses prefix `{rp}`, but this register declares `prefix: {prefix}`")
        return
    if str(int(digits)).zfill(3) != digits:
        canon = f"{rp}-{str(int(digits)).zfill(3)}"
        err(file, f"line {line}: `{rid}` is not canonically zero-padded (expected `{canon}`)")
        return
    if rid in rows:
        prior = rows[rid]
        where = f"{rel(prior['file'])}:{prior['line']}"
        err(
            file,
            f"line {line}: duplicate requirement id `{rid}` (also {where}) — ids are permanent and never reused",
        )
        return

    kind = row[cols["Kind"]] if cols["Kind"] < len(row) else ""
    disp = row[cols["Disposition"]] if cols["Disposition"] < len(row) else ""
    if kind not in KINDS:
        err(file, f"{rid}: unknown Kind `{kind}` (allowed: {', '.join(sorted(KINDS))})")
    sup: str | None = None
    sm = SUPERSEDED_RE.match(disp)
    if sm:
        sup = corpusref.localize_entry(sm.group(1), own, keep) if sm.group(1) else sm.group(1)
    elif disp not in DISPOSITIONS:
        err(
            file,
            f"{rid}: unknown Disposition `{disp}` (allowed: {', '.join(sorted(DISPOSITIONS))}, "
            "`superseded by <ID>`, bare `superseded`, or `superseded (confirmed)`)",
        )
    needs_idx = cols.get("Needs")
    needs = id_refs(row[needs_idx], own, keep) if needs_idx is not None and needs_idx < len(row) else []
    because_idx = cols.get("Because")
    because_cell = row[because_idx] if because_idx is not None and because_idx < len(row) else ""
    bec = id_refs(because_cell, own, keep)
    because = bec[0] if bec else ""
    reaff = ""
    reaff_malformed = False
    if because_cell:
        rm = REAFFIRMED_RE.search(because_cell)
        if rm:
            reaff = rm.group(1)
        elif "reaffirmed=" in because_cell:
            reaff_malformed = True
    cut_idx = cols.get("Cut")
    cut = row[cut_idx].strip() if cut_idx is not None and cut_idx < len(row) else ""
    if cut and cut not in CUT_VALUES:
        err(file, f"{rid}: unknown Cut `{cut}` (allowed: {', '.join(CUT_VALUES)}, or blank)")
        cut = ""
    if cut and (sm is not None or disp != "adopted"):
        err(
            file,
            f"{rid}: carries `Cut: {cut}` but its Disposition is `{disp}` — a version line "
            "is a property of a commitment we are still making; a rejected or superseded "
            "row has no version to be cut from, so leave the cell blank",
        )
        cut = ""
    rows[rid] = {
        "file": file,
        "line": line,
        # The register this row BELONGS to — never derived from `file`: a row read from a
        # per-row fragment has `file` = `rows/<ID>.json`, whose stem is the row's own id, so
        # every consumer that took `Path(file).stem` as the domain filed each fragment row
        # under itself ("GOV-001") instead of its register ("governance").
        "register_file": register,
        "prefix": prefix,
        "section": section,
        "statement": row[cols["Statement"]] if cols["Statement"] < len(row) else "",
        "source": row[cols["Source"]] if cols["Source"] < len(row) else "",
        "legend": legend,
        "kind": kind,
        "disposition": disp,
        "superseded_by": sup,
        "superseded": sm is not None,
        "superseded_confirmed": sm is not None and sup is None and disp.endswith("(confirmed)"),
        "cut": cut,
        "needs": needs,
        "has_needs_column": needs_idx is not None,
        "has_cut_column": cut_idx is not None,
        "because": because,
        "reaffirmed": reaff,
        "reaffirmed_malformed": reaff_malformed,
    }


def load_registers(
    root: Path,
    *,
    rel: Callable[[Path], str] = str,
    reserved_prefixes: frozenset[str] = DEFAULT_RESERVED_PREFIXES,
    dir_name: str = REGISTER_SUBDIR,
    own: str | None = None,
    owned: Iterable[str] = (),
    shells: bool = False,
) -> tuple[dict[str, dict[str, Any]], list[Finding]]:
    """`({id: row}, findings)` across every `<root>/requirements/*.md` register.

    A row is `{file, line, prefix, section, statement, source, legend, kind, disposition,
    superseded_by, superseded, superseded_confirmed, cut, needs, has_needs_column,
    has_cut_column, because, reaffirmed, reaffirmed_malformed, register_file}`. When the row
    came from a per-row fragment its `file` is that fragment and `line` is 0; `register_file`
    is always the register `.md` the row belongs to — the domain is its stem, never `file`'s.

    **Fragments win when they exist for a domain.** A domain whose `rows/*.json` fragments
    use its stem as the table-key prefix (`connectors#…`) is read from those fragments; the
    committed table body is ignored for that domain. A domain with no such fragments still
    reads its table, so a corpus mid-migration is served correctly.

    `rel` renders a path inside a message (a caller with a repository in hand makes those
    repo-relative); `reserved_prefixes` names the id namespaces something else already owns.
    `owned` names the prefixes a sibling corpus owns: an own-qualified id in one keeps its
    qualifier, so the resolver can refuse it rather than read it as a local id.
    """
    keep = frozenset(owned)
    rows: dict[str, dict[str, Any]] = {}
    findings: list[Finding] = []
    own_name = corpusref.resolve_own(root, own)
    fragments = load_row_fragments(root, dir_name)

    def err(path: Path, msg: str) -> None:
        findings.append((path, msg))

    for f in registers(root, dir_name, shells=shells):
        text = f.read_text(encoding="utf-8")
        fm = frontmatter(text)
        if fm is None:
            err(f, "missing YAML frontmatter")
            continue
        prefix = field(fm, "prefix")
        if not prefix:
            err(f, "missing required frontmatter field `prefix:` (the id namespace this register owns)")
            continue
        if not PREFIX_RE.match(prefix):
            err(f, f"prefix `{prefix}` is not 2-5 uppercase letters")
            continue
        if prefix in reserved_prefixes:
            err(
                f,
                f"prefix `{prefix}` is reserved — a Linear issue key of that shape is written "
                "`[ENG-4813]` inside acceptance criteria and would silently satisfy the "
                "coverage check; pick a domain prefix of your own",
            )
            continue

        legend = source_legend(f, text)
        stem_prefix = register_domain(f) + "#"
        domain_frags = {k: v for k, v in fragments.items() if k.startswith(stem_prefix)}
        if domain_frags:
            layouts = table_layouts(text)
            for key, frag_rows in domain_frags.items():
                layout = layouts.get(key)
                if layout is None:
                    # No marker in the shell: fall back to the required columns plus the
                    # optional ones a 6-cell fragment carries (Cut, Needs before Source).
                    default_header = ["ID", "Statement", "Kind", "Disposition", "Cut", "Needs", "Source"]
                    layout = ("", {name: idx for idx, name in enumerate(default_header)})
                frag_section, frag_cols = layout
                missing = [c for c in REQUIRED_COLUMNS if c not in frag_cols]
                if missing:
                    err(f, f"table `{key}` is missing column(s) {', '.join(missing)}")
                    continue
                for _order, rid, cell_vals, src in frag_rows:
                    full = [rid, *cell_vals]
                    _accept_row(
                        rid,
                        full,
                        frag_cols,
                        prefix=prefix,
                        section=frag_section,
                        legend=legend,
                        file=src,
                        line=0,
                        register=f,
                        rows=rows,
                        rel=rel,
                        err=err,
                        own=own_name,
                        keep=keep,
                    )
            continue

        lines = text.splitlines()
        cols: dict[str, int] | None = None  # column name -> index, for the table being read
        section = ""  # most recent heading — the grouping a status generator renders by
        # HTML comments are prose ABOUT a row (allocation notes, next-id markers). A
        # multi-line comment whose continuation begins with `#` (e.g. a PR number written
        # `#10182`) is not a markdown heading — treating it as one replaces the real
        # section title in the derived ledger (ENG-9831). Track open comments across lines.
        in_html_comment = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Walk comment delimiters left-to-right so a same-line `<!-- … -->` and a
            # multi-line open/close both leave `in_html_comment` correct for *this* line's
            # heading check (a line is "inside a comment" if any span of it is).
            scan = stripped
            line_in_comment = in_html_comment
            while scan:
                if in_html_comment:
                    end = scan.find("-->")
                    if end < 0:
                        line_in_comment = True
                        break
                    line_in_comment = True
                    scan = scan[end + 3 :]
                    in_html_comment = False
                    continue
                start = scan.find("<!--")
                if start < 0:
                    break
                line_in_comment = True
                scan = scan[start + 4 :]
                in_html_comment = True
            if not stripped.startswith("|"):
                # A real markdown heading is outside HTML comments. ATX headings are `#` at
                # the start of the stripped line; a comment continuation that happens to
                # begin with `#10182` must not steal the section.
                if not line_in_comment and stripped.startswith("#"):
                    cols = None  # a heading ends the table it followed
                    section = stripped.lstrip("#").strip()
                continue
            if SEP_RE.match(stripped):
                continue
            row = cells(line)
            is_header = i + 1 < len(lines) and SEP_RE.match(lines[i + 1].strip())
            if is_header:
                # A register table is identified by its columns, not its position, so a
                # `Needs` column can be added anywhere without this parser shifting.
                if row and row[0] == "ID" and "Statement" in row:
                    cols = {name: idx for idx, name in enumerate(row)}
                    missing = [c for c in REQUIRED_COLUMNS if c not in cols]
                    if missing:
                        err(f, f"line {i + 1}: register table is missing column(s) {', '.join(missing)}")
                        cols = None
                else:
                    cols = None  # some other table (the source legend, a prose table)
                continue
            if cols is None:
                continue

            rid = row[cols["ID"]] if cols["ID"] < len(row) else ""
            _accept_row(
                rid,
                row,
                cols,
                prefix=prefix,
                section=section,
                legend=legend,
                file=f,
                line=i + 1,
                register=f,
                rows=rows,
                rel=rel,
                err=err,
                own=own_name,
                keep=keep,
            )
    return rows, findings
