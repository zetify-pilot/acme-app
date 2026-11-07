"""The ONE reader for the program and slice registers.

A program is a row in `<root>/programs.md`, a slice is a row in `<root>/slices.md`, and the
prose that either tier carries lives in an OPTIONAL detail file named for the row's id
(`<root>/programs/PG-21.md`, `<root>/slices/SL-137.md`). The filename IS the join — there is
no slug, and a detail file carries no structure at all.

**Why a register rather than a folder per entity.** Folders stored, per entity, a
frontmatter block only the validators read plus a member list that duplicated an edge
already authored on the child. Answering "what is in flight" meant opening every file, and
keeping the parent's list equal to the set of children naming it needed a validator whose
whole job was reconciling one fact stored twice. A register makes the fact singular: the
slice row names its program, and nothing else does.

**Ids are permanent and never reused.** Each register carries an
`<!-- APPEND ONLY. Next id: ... -->` counter, which is what makes `SL-137` safe to cite from
a document that shipped a year ago.

What lives WHERE:

  * **Register** — every structural field: name, kind, the roll-up edge, the dependency
    edges, the proof pointers, `Done when`. Anything a script reads.
  * **Detail file** — prose only, and only where prose exists.

Nothing here carries a `status:`. A slice's and a program's completion is COMPUTED from
their member PRDs and their proof (`fleet_knowledge.rollup`). The derivation takes exactly ONE
authored input per tier: `Verified by`.

**Two axes, not one — and the second is a DECISION, never a ship-state.** Completion is derived
and must stay derived (33 of 40 stored statuses were wrong, and the `Proof accepted` attestation
cell was deleted filled on 0 of 13). But a container had no way to say *what happened to it*: a
program whose work was stopped, or folded into another, could only be deleted from the register
— which is how a row that had been cited for months vanished — or sit open forever reading
`unproven`. The requirement register solved exactly this years ago with `Disposition` beside a
derived status, so both tiers carry the same column, LAST, with the same three values:

  * `adopted` — the norm. The container is in force and its completion is the arithmetic's.
  * `withdrawn: decisions/<file>.md` — stopped, and the decision record IS the reason. A relative
    path under the corpus, never free text: a sentence in a cell is a reason nobody can find
    again, a file is one.
  * `superseded by PG-NN` / `superseded by SL-NNN` — folded into a successor, which must resolve.

  Nothing else. `delivered`, `closed`, `done` are ship-state claims wearing a decision's clothes
  and the validator refuses them by name, saying why. A row without the column at all — an older
  corpus, or a commit from before the column existed, which the service reads as history — reads
  `adopted`: the column is additive, never a rewrite of what was authored.

**And a proof may be a drill record, not only a PRD.** `Verified by` accepts `drill:<stem>`,
naming `<root>/drills/<stem>.md`; it counts as shipped when that record's frontmatter says
`verdict: passed`. Before this, a delivered program whose composed proof was an OBSERVATION —
a failover drill, an estate move — had to manufacture a proof PRD to close, or stay open.

Stdlib only.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from . import corpusref, planningmode
from .markdown import cells, frontmatter, listcell, listfield, prose, scalar

PROGRAM_PREFIX = "PG"
SLICE_PREFIX = "SL"

PROGRAM_FILE = "programs.md"
SLICE_FILE = "slices.md"
PROGRAM_DETAIL_SUBDIR = "programs"
SLICE_DETAIL_SUBDIR = "slices"
#: The subdirectory, under a tier's detail directory, that holds the per-row fragments:
#: `<root>/<detail_subdir>/rows/<ID>.json`. The filename IS the row id. When this directory
#: holds fragments the register TABLE is a generated projection of them and every reader below
#: reads the fragments instead — so two branches that each add a row touch two different files
#: and the shared table is never a committed collision point (ENG-12549, ENG-12661).
ROWS_SUBDIR = "rows"
#: Where drill records live, corpus-relative. `Config.drills_dir` is what a project sets.
DRILLS_SUBDIR = "drills"

# ─────────────────────────── the disposition grammar ───────────────────────────
#
# One definition, because every reader of a row has to agree about what a cell MEANS. The
# validator refuses what does not parse; the readers below never do — a reader that judged
# would give the corpus two opinions about one cell.

#: The closed vocabulary of `disposition.kind`. An `Enum` in spirit; a tuple because this module
#: hands back plain dicts a JSON payload carries unchanged.
DISPOSITION_KINDS = ("adopted", "withdrawn", "superseded")
ADOPTED = "adopted"
WITHDRAWN = "withdrawn"
SUPERSEDED = "superseded"

#: `withdrawn: decisions/2026-09-10-why.md` — one path, no spaces, no prose after it.
WITHDRAWN_RE = re.compile(r"^withdrawn:\s*([^\s`|]+\.md)$")
#: `superseded by PG-21` — the successor id, in this register's own namespace — or a
#: repo-qualified one (`superseded by fleet:PG-047`) when the work moved to another corpus. The
#: qualifier stays on the ref (`fleet_knowledge.corpusref`).
#:
#: A PROGRAM may also be `superseded by areas` (FLT-1283, owner decision 2026-10-29): the program closed
#: because the repository stopped planning by program, and its work went to feature areas rather than to
#: another row. Its live slices left it first (`fleet planning migrate --close-programs`), so it withdraws
#: nothing with it: a finished cut under it stays finished (`rollup.withdrawn_programs`). Only the program
#: tier may carry it (`checks.planning.tracking_metadata`).
SUPERSEDED_RE = re.compile(r"^superseded\s+by\s+((?:[a-z][a-z0-9-]*:)?[A-Z]{2,5}-\d+|areas)$")
#: The successor a program closed into feature areas names (`superseded by areas`).
AREAS_SUCCESSOR = "areas"

#: A proof-cell entry naming a drill record rather than a PRD: `drill:<stem>` for
#: `<root>/drills/<stem>.md`.
DRILL_PREFIX = "drill:"
#: What a drill record's frontmatter must declare to be one.
DRILL_RECORD_TYPE = "drill-record"
#: The one verdict that makes a drill count as a shipped proof.
DRILL_PASSED = "passed"


def id_pattern(prefix: str) -> re.Pattern[str]:
    r"""`^OBJ-\d+$` for `OBJ`. The id namespace is the corpus's, not this repository's.

    Built from the prefix rather than written out, because a register's ids are the second
    hardcoded thing here — a corpus whose programs are `OBJ-01` had every row skipped by a
    pattern anchored on `PG`, which reads on a page exactly like a register nobody wrote.

    Deliberately `\d+` rather than the two- and three-digit minimums this repository's own
    registers happen to use: a width is a house style, and refusing `OBJ-1` on a corpus that
    writes it would be this package deciding how another project numbers things.
    """
    return re.compile(rf"^{re.escape(prefix)}-\d+$")


def next_id_pattern(prefix: str) -> re.Pattern[str]:
    """The append-only counter marker for one namespace."""
    return re.compile(rf"APPEND ONLY\. Next id:\s*({re.escape(prefix)}-\d+)")


PROGRAM_ID_RE = id_pattern(PROGRAM_PREFIX)
SLICE_ID_RE = id_pattern(SLICE_PREFIX)
NEXT_PROGRAM_RE = next_id_pattern(PROGRAM_PREFIX)
NEXT_SLICE_RE = next_id_pattern(SLICE_PREFIX)


# Every reader below takes the NAME as a parameter, defaulted to the conventional one, exactly
# as `requirements.register_dir` and `todos.register` already do. `Config.programs_register`,
# `Config.slices_register`, `Config.programs_detail_dir` and `Config.slices_detail_dir` are what
# a project sets, and they reach here through whoever resolved the config — nothing in this
# module imports it. A reader that opened these by hardcoded name is why a corpus that calls
# them something else derived an empty board and nothing said so.


def program_register(root: Path, file_name: str = PROGRAM_FILE) -> Path:
    return root / file_name


def slice_register(root: Path, file_name: str = SLICE_FILE) -> Path:
    return root / file_name


def program_detail(root: Path, pid: str, subdir: str = PROGRAM_DETAIL_SUBDIR) -> Path:
    """Where `PG-21`'s prose lives — whether or not the file exists."""
    return root / subdir / f"{pid}.md"


def slice_detail(root: Path, sid: str, subdir: str = SLICE_DETAIL_SUBDIR) -> Path:
    """Where `SL-137`'s prose lives — whether or not the file exists."""
    return root / subdir / f"{sid}.md"


def rows_dir(root: Path, detail_subdir: str) -> Path:
    """Where one tier's row fragments live: `<root>/<detail_subdir>/rows`."""
    return root / detail_subdir / ROWS_SUBDIR


def program_rows_dir(root: Path, subdir: str = PROGRAM_DETAIL_SUBDIR) -> Path:
    return rows_dir(root, subdir)


def slice_rows_dir(root: Path, subdir: str = SLICE_DETAIL_SUBDIR) -> Path:
    return rows_dir(root, subdir)


def fragments(root: Path, detail_subdir: str, id_re: re.Pattern[str]) -> list[tuple[str, dict[str, Any], Path]]:
    """Every row fragment in `<root>/<detail_subdir>/rows/*.json`, in register order.

    A fragment is the row's own file — the filename IS the id, and the JSON carries one key
    per column (a string per scalar cell, a list per comma-list cell). Files whose stem is not
    a well-formed id are SKIPPED here, exactly as a malformed table row is skipped by `rows`;
    catching a malformed id on the raw material is the gate's job, not this reader's.

    An absent directory — the shape every corpus has until it migrates — is `[]`, which is
    what lets `programs` / `slices` fall back to the committed table. An empty directory is
    also `[]`: a register with a `rows/` dir the project never filled is not a register whose
    rows all vanished, and reading it as the latter would silently empty the board.
    """
    base = rows_dir(root, detail_subdir)
    if not base.is_dir():
        return []
    out: list[tuple[str, dict[str, Any], Path]] = []
    for f in sorted(base.glob("*.json")):
        if not id_re.match(f.stem):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            # A fragment that cannot be parsed is the gate's finding, not a reason for every
            # other reader to lose the row: skip it here rather than throw on the whole tree.
            continue
        if isinstance(data, dict):
            out.append((f.stem, data, f))
    out.sort(key=lambda t: int(t[0].split("-", 1)[1]))
    return out


def _frag_list(value: Any) -> list[str]:
    """A fragment's list cell as the reader's own list: JSON lists and comma strings both read."""
    if value is None:
        return []
    if isinstance(value, str):
        return listcell(value)
    if isinstance(value, list):
        return [v for v in (scalar(str(x)) for x in value) if v]
    return listcell(str(value))


def _frag_cell(value: Any) -> str:
    """A fragment's scalar cell as the reader's own string (`""` for a missing key)."""
    return "" if value is None else str(value).strip()


def _disposition_from(cell: str) -> tuple[dict[str, Any], str]:
    return disposition(cell), cell.strip()


def disposition(cell: str) -> dict[str, Any]:
    """`{"kind": adopted|withdrawn|superseded, "ref": <path or id or None>}` for one cell.

    READS, NEVER JUDGES. An empty cell and a missing column both read `adopted`, which is what
    makes the column additive: a register authored before it existed, or a commit the service
    reads as history, means exactly what it meant when it was written. A cell that matches none
    of the three shapes also reads `adopted`, and that is the conservative reading rather than a
    lenient one — the commit gate (`checks.planning.tracking_metadata`) refuses such a cell by
    name before it can be committed, so the only reader that ever meets one is looking at a tree
    the gate has not seen, and dropping a container off the board on a typo would be a worse
    answer than keeping it there. The raw cell rides beside this on the row as `disposition_cell`,
    which is what the gate reads.
    """
    v = scalar(cell)
    if not v or v == ADOPTED:
        return {"kind": ADOPTED, "ref": None}
    if m := WITHDRAWN_RE.match(v):
        return {"kind": WITHDRAWN, "ref": m.group(1)}
    if m := SUPERSEDED_RE.match(v):
        return {"kind": SUPERSEDED, "ref": m.group(1)}
    return {"kind": ADOPTED, "ref": None}


def closed_into_areas(row: Mapping[str, Any]) -> bool:
    """Whether a register row is `superseded by areas`: a program closed because its repository plans by
    feature area now. Out of the plan like any superseded row, but it takes no cut with it."""
    disp = row.get("disposition") or {}
    return isinstance(disp, Mapping) and disp.get("kind") == SUPERSEDED and disp.get("ref") == AREAS_SUCCESSOR


def is_drill(entry: str) -> bool:
    """Whether a `Verified by` entry names a drill record rather than a PRD."""
    return entry.startswith(DRILL_PREFIX)


def drill_stem(entry: str) -> str:
    """`drill:0527-machine-loss` -> `0527-machine-loss`. "" for an entry that is not one."""
    return entry[len(DRILL_PREFIX) :].strip() if is_drill(entry) else ""


def drills_dir(root: Path, subdir: str = DRILLS_SUBDIR) -> Path:
    return root / subdir


def drill_record(root: Path, stem: str, subdir: str = DRILLS_SUBDIR) -> Path:
    """Where `drill:<stem>`'s record lives — whether or not the file exists."""
    return drills_dir(root, subdir) / f"{stem}.md"


def drills(root: Path, subdir: str = DRILLS_SUBDIR) -> dict[str, dict[str, Any]]:
    """Every markdown file under the drills directory, `stem -> its frontmatter fields`.

    EVERY `.md`, not only the well-formed records, and every frontmatter, not only the fields a
    proof reading needs: the validator has to be able to say *"that file is not a drill record"*
    and *"that record carries no verdict"*, which it cannot if this reader has already dropped
    the file. `README.md` and `_TEMPLATE.md` are the two files that live there and are not
    records of anything, and they are skipped by name — the same rule the detail-file reader
    applies. A file with no frontmatter reads as `{}`.

    The frontmatter contract (from the corpus this package came from): `type: drill-record`,
    `verdict: passed|failed`, `daemon_sha`, `ran_at`, `scope`, `drill`, and a `source_of_truth`
    list. Scalars come back as strings; `source_of_truth` as a list. Nothing here interprets a
    verdict — `rollup.all_shipped` does that, in one place.
    """
    base = drills_dir(root, subdir)
    if not base.is_dir():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for f in sorted(base.glob("*.md")):
        if f.name in ("README.md", "_TEMPLATE.md"):
            continue
        fm = frontmatter(f.read_text(encoding="utf-8", errors="replace"))
        fields: dict[str, Any] = {}
        for m in re.finditer(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$", fm, re.M):
            key, value = m.group(1), m.group(2).strip()
            fields[key] = value.strip("\"'")
        if "source_of_truth" in fields:
            fields["source_of_truth"] = listfield(fm, "source_of_truth")
        out[f.stem] = fields
    return out


def rows(path: Path, id_re: re.Pattern[str], columns: int) -> list[tuple[list[str], int]]:
    """Every table row whose first cell is a well-formed id, with its 1-based line number.

    Anything else in the file — prose, the header row, the `---|---` rule — is skipped, so a
    register can carry as much explanation above its table as it needs.
    """
    if not path.is_file():
        return []
    out: list[tuple[list[str], int]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if not line.lstrip().startswith("|"):
            continue
        c = cells(line)
        if not c or not id_re.match(c[0]):
            continue
        # Pad short rows rather than dropping them: a missing trailing cell is a validator's
        # finding, not a reason for every other reader to lose the row.
        c += [""] * (columns - len(c))
        out.append((c, i))
    return out


def program_row_from_fragment(pid: str, data: dict[str, Any], source: Path) -> dict[str, Any]:
    cell = _frag_cell(data.get("disposition"))
    disp, raw = _disposition_from(cell)
    return {
        "id": pid,
        "title": _frag_cell(data.get("name")),
        "kind": _frag_cell(data.get("kind")),
        "verified_by": _frag_list(data.get("verified_by")),
        "requires": _frag_list(data.get("requires")),
        "disposition": disp,
        "disposition_cell": raw,
        # A fragment knows which file it is, not a row number inside a generated table. The
        # gate cites the file; the `line` is kept at 1 so a finding payload still carries the
        # field a table row does.
        "line": 1,
        "source": source,
    }


def slice_row_from_fragment(sid: str, data: dict[str, Any], source: Path) -> dict[str, Any]:
    cell = _frag_cell(data.get("disposition"))
    disp, raw = _disposition_from(cell)
    return {
        "id": sid,
        "title": _frag_cell(data.get("name")),
        "kind": _frag_cell(data.get("kind")),
        "program": _frag_cell(data.get("program")),
        # ITS FEATURE AREA (FLT-1280): a feature map's slug; every slice names one, and `program` is optional,
        # older membership. `""` on a row written before the rule — `tracking-metadata` notes it, and fails
        # only a new or changed one (or every live one, under `require_area`; a finished or withdrawn one never).
        "area": _frag_cell(data.get("area")),
        "done": prose(_frag_cell(data.get("done_when"))),
        "verified_by": _frag_list(data.get("verified_by")),
        # The reasoned *no proof planned, and here is why* waiver (ENG-12602) — read off the
        # row so the waiver lives beside the cut it excuses, never in a shared regenerated
        # baseline file two branches collide on. Empty on a row that names a proof or that has
        # a live member PRD; the check reads it in `tracking_metadata`.
        #
        # Since 2026-10-07 the waiver also says WHICH of two things it is (`proof_waiver_kind`):
        # `excused` — no proof is needed — or `deferred` — the proof is still owed, and
        # `proof_waiver_owed` says what it is. Only an excused waiver settles the cut. See
        # `waiver_of`; a legacy string carries no kind and the gate refuses it.
        **_waiver_fields(data.get("proof_waiver")),
        "depends_on": _frag_list(data.get("depends_on")),
        "component": _frag_list(data.get("components")),
        "disposition": disp,
        "disposition_cell": raw,
        "line": 1,
        "source": source,
    }


def slice_proof_waivers(slices: Iterable[Mapping[str, Any]]) -> set[str]:
    """Slice ids carrying a reasoned `proof_waiver` on their own row (ENG-12602).

    THE one reader of that field: the commit gate (`checks.planning.tracking_metadata`) and the board
    (`board.build`) both call it, so they cannot disagree about which cuts are waived. A blank value is
    READ AS ABSENT, so a half-written waiver falls through to the gate rather than reading as one. A row
    read from a legacy committed table has no such key at all — a table-only corpus cannot carry a
    per-row waiver and must migrate to fragments to waive.
    """
    return {str(s["id"]) for s in slices if str(s.get("proof_waiver", "")).strip()}


# ─────────────────────────── the waiver's kind ───────────────────────────
#
# A proof waiver says one of TWO things (the operator's decision, 2026-10-07), and they need
# opposite readings:
#
#   * `excused`  — this proof is not needed: superseded, covered elsewhere, will not be built.
#                  The cut is SETTLED by the waiver, and a program may close over it (the
#                  2026-09-17 rule, which this narrows rather than retires).
#   * `deferred` — the proof is still OWED, to be measured or named later. The cut stays OPEN,
#                  reading `awaiting-proof` with what is owed, and so does its program, until
#                  the proof lands and the waiver is removed.
#
# The 2026-09-17 rule read every waiver as the first. Production's PG-21 then closed over
# SL-188, whose waiver says its proof is a Bar "authored by slice:edit once the driver's live
# measurements land" — a proof owed, not excused.
#
# A slice row's `proof_waiver` is an object: `{"kind": "excused", "reason": "..."}` or
# `{"kind": "deferred", "owed": "<what is owed, in a phrase>", "reason": "..."}`. A program's is
# its baseline id line: `PG-17 excused` or `PG-30 deferred: <what is owed>`. THERE IS NO DEFAULT:
# a waiver that does not say its kind is refused by the gate (`waiver_problem`), and a reader
# that meets one anyway reads it as DEFERRED — the conservative reading, because settling a
# program on a waiver nobody classified is the exact mistake this split exists to stop.

WAIVER_EXCUSED = "excused"
WAIVER_DEFERRED = "deferred"
#: The closed vocabulary of a waiver's kind.
WAIVER_KINDS = (WAIVER_EXCUSED, WAIVER_DEFERRED)
#: What an unclassified waiver is read as owing, so a page never shows an empty reason.
UNSTATED_OWED = "its waiver does not say whether the proof is still owed"

# ─────────────────────────── what a deferred proof needs ───────────────────────────
#
# A DEFERRED waiver may also say WHERE its owed proof can only be taken (the operator's decision,
# 2026-10-08: "Keep prod checks with people"). `needs: production` means the proof is a check run
# against production — SL-188's "live measurement on a deployed plane" — and Fleet never touches
# production, so no run the fleet dispatches will ever make that proof land. Such a cut is a
# PERSON'S step of a different kind: someone with production access runs the attended
# `program:deliver` cycle, whose "Read the bar" step runs the slice's live checks and names the
# proof with `slice:edit` once they pass. A deferred waiver with no `needs` is owed work the fleet
# can produce itself (a PRD still to ship, a composed proof still to cut), and keeps its reading.
#
# The field is STRUCTURED, never read off the `owed` prose: "live measurement", "the live estate"
# and "a real Microsoft tenant" are three phrasings of one fact, and a string match would route
# whichever phrasing it missed back to a step nothing will take.

#: `needs: production` — the owed proof is a check against production, which only a person runs.
NEEDS_PRODUCTION = "production"
#: The closed vocabulary of a deferred waiver's `needs`; absent means the fleet can produce the proof.
WAIVER_NEEDS = (NEEDS_PRODUCTION,)


def _waiver_fields(value: Any) -> dict[str, str]:
    """`proof_waiver` / `proof_waiver_kind` / `proof_waiver_owed` off one fragment's raw value.

    The REASON stays in `proof_waiver`, as the one string every older reader takes it to be, so
    `slice_proof_waivers` and the commit gate keep reading presence exactly as before: a waiver with
    no reason is no waiver, whatever its kind, and falls through to the gate. A legacy bare string is
    a waiver with no kind (`""`), which the gate refuses.
    """
    if isinstance(value, Mapping):
        return {
            "proof_waiver": _frag_cell(value.get("reason")),
            "proof_waiver_kind": _frag_cell(value.get("kind")),
            "proof_waiver_owed": _frag_cell(value.get("owed")),
            "proof_waiver_needs": _frag_cell(value.get("needs")),
        }
    return {
        "proof_waiver": _frag_cell(value),
        "proof_waiver_kind": "",
        "proof_waiver_owed": "",
        "proof_waiver_needs": "",
    }


def waiver_owed(kind: str, owed: str) -> str | None:
    """What a waiver of this kind leaves OWED — `None` when it settles the entity.

    `excused` settles (`None`). `deferred` owes its stated `owed`, or `UNSTATED_OWED` when it
    states none. Anything else — no kind, a misspelt one — is read as deferred: the gate refuses
    it, and a reader in the meantime keeps the entity open rather than closing it on a guess.
    """
    if kind == WAIVER_EXCUSED:
        return None
    return owed.strip() or UNSTATED_OWED


def waiver_problem(kind: str, owed: str, needs: str = "") -> str:
    """Why a waiver is malformed, in one clause — `""` for a well-formed one.

    A waiver must state its kind (no default), and a deferred one must say what it owes: the
    page reads "waiting on SL-188's proof: <owed>", and a blank there is a promise nobody can
    check. `needs`, when given, is from `WAIVER_NEEDS` and only on a deferred waiver — an excused
    one owes nothing, so nothing it owes can need production.
    """
    if not kind:
        return (
            f"states no kind — say `{WAIVER_EXCUSED}` (no proof is needed) or `{WAIVER_DEFERRED}` "
            "(the proof is still owed)"
        )
    if kind not in WAIVER_KINDS:
        return f"names kind `{kind}`, which is neither `{WAIVER_EXCUSED}` nor `{WAIVER_DEFERRED}`"
    if kind == WAIVER_DEFERRED and not owed.strip():
        return "is deferred but does not say what proof is owed — state it in `owed`"
    if needs and needs not in WAIVER_NEEDS:
        return f"names needs `{needs}`, which is not `{NEEDS_PRODUCTION}`"
    if needs and kind != WAIVER_DEFERRED:
        return f"says it needs `{needs}` but is not deferred — only a proof still owed can need anything"
    return ""


def slice_waiver_readings(slices: Iterable[Mapping[str, Any]]) -> tuple[frozenset[str], dict[str, str]]:
    """`(excused ids, {deferred id: what is owed})` over the slice rows carrying a waiver.

    THE one place a slice waiver's kind is read for a roll-up, so the board and `delivery()` cannot
    disagree about which cuts a waiver settles. A row with no waiver is in neither.
    """
    excused: set[str] = set()
    owed: dict[str, str] = {}
    for s in slices:
        if not str(s.get("proof_waiver", "")).strip():
            continue
        left = waiver_owed(str(s.get("proof_waiver_kind") or ""), str(s.get("proof_waiver_owed") or ""))
        if left is None:
            excused.add(str(s["id"]))
        else:
            owed[str(s["id"])] = left
    return frozenset(excused), owed


#: A baseline id line: `PG-30`, `PG-17 excused`, `PG-30 deferred: the composed drill record`.
BASELINE_LINE_RE = re.compile(r"^(?P<id>\S+)(?:\s+(?P<kind>[A-Za-z-]+))?(?:\s*:\s*(?P<owed>.*))?$")


def baseline_line(line: str) -> tuple[str, str, str] | None:
    """`(id, kind, owed)` for one waiver-baseline line, `None` for a blank or comment line.

    The program tier's waiver lives in a ratcheted baseline file rather than on a row, so its
    kind rides on the id line itself — `PG-17 excused`, `PG-30 deferred: <what is owed>` — and a
    bare `PG-30` is a waiver with no kind. A `#` ends the line's content, as it always has.
    """
    body = line.split("#")[0].strip()
    if not body:
        return None
    m = BASELINE_LINE_RE.match(body)
    if not m:
        return body.split()[0], "", ""
    return m.group("id"), (m.group("kind") or "").strip(), (m.group("owed") or "").strip()


def localize_rows(rows: list[dict[str, Any]], own: str) -> list[dict[str, Any]]:
    """Drop an OWN-corpus qualifier from every reference a register row carries, in place.

    `acme:SL-302` in the `acme` corpus is the local `SL-302`; normalised HERE, at parse time, so
    no comparison downstream (a cycle walk, a roll-up, a board) ever meets the qualified
    spelling and reads it as foreign (`fleet_knowledge.corpusref`). A foreign qualifier stays.
    """
    if not own:
        return rows
    for row in rows:
        for key in ("verified_by", "requires", "depends_on"):
            if key in row:
                row[key] = [corpusref.localize_entry(str(x), own) for x in row[key]]
        if row.get("program"):
            row["program"] = corpusref.localize_entry(str(row["program"]), own)
        disp = row.get("disposition")
        if isinstance(disp, dict) and disp.get("kind") == SUPERSEDED and disp.get("ref"):
            disp["ref"] = corpusref.localize_entry(str(disp["ref"]), own)
    return rows


def programs(
    root: Path,
    file_name: str = PROGRAM_FILE,
    prefix: str = PROGRAM_PREFIX,
    detail_subdir: str = PROGRAM_DETAIL_SUBDIR,
    own: str | None = None,
) -> list[dict[str, Any]]:
    """Every program row, in register order.

    Columns: `ID | Name | Kind | Verified by | Requires | Disposition`. **Every row is read
    POSITIONALLY**, so a reader that is not updated alongside a dropped column silently
    shifts every field after it. `Disposition` is LAST precisely so a register authored before
    it existed still reads: a short row is padded, and an empty sixth cell is `adopted`.

    **Fragments win when they exist.** When `<root>/<detail_subdir>/rows/` holds row fragments
    the rows are read from them, and the committed table is never opened — it is a generated
    projection of these fragments (ENG-12549), kept only until a corpus drops it (ENG-12546).
    A corpus that has not migrated has no such directory and reads its table exactly as before,
    so the same package serves both ends of the migration.
    """
    own_name = corpusref.resolve_own(root, own)
    frags = fragments(root, detail_subdir, id_pattern(prefix))
    if frags:
        return localize_rows([program_row_from_fragment(pid, data, src) for pid, data, src in frags], own_name)
    out: list[dict[str, Any]] = []
    for c, line in rows(program_register(root, file_name), id_pattern(prefix), 6):
        out.append(
            {
                "id": c[0],
                "title": scalar(c[1]),
                "kind": scalar(c[2]),
                # The composed thread across this program's slices — "do these work together
                # for a person?". The ONLY authored input to the completion derivation, and
                # the completion condition this tier adds to its slices'. An entry is a PRD
                # number or `drill:<stem>` — see `is_drill`.
                "verified_by": listcell(c[3]),
                # The roots of the decomposition. Not a child edge: a program's children are
                # its slices, and that edge is authored on the slice.
                "requires": listcell(c[4]),
                # What HAPPENED to this program, as a decision — the second axis. Never a
                # ship-state; see the module docstring.
                "disposition": disposition(c[5]),
                "disposition_cell": c[5].strip(),
                "line": line,
            }
        )
    return localize_rows(out, own_name)


def slices(
    root: Path,
    file_name: str = SLICE_FILE,
    prefix: str = SLICE_PREFIX,
    detail_subdir: str = SLICE_DETAIL_SUBDIR,
    own: str | None = None,
) -> list[dict[str, Any]]:
    """Every slice row, in register order.

    Columns: `ID | Name | Kind | Program | Done when | Verified by | Depends on | Components |
    Disposition`. The last column is the decision axis and is read exactly as the program
    tier's is — see `programs`. Fragments win when they exist, as on `programs`.
    """
    own_name = corpusref.resolve_own(root, own)
    frags = fragments(root, detail_subdir, id_pattern(prefix))
    if frags:
        return localize_rows([slice_row_from_fragment(sid, data, src) for sid, data, src in frags], own_name)
    out: list[dict[str, Any]] = []
    for c, line in rows(slice_register(root, file_name), id_pattern(prefix), 9):
        # An area slice writes `area:<slug>` into the `Program` cell, so no column moves (FLT-1280).
        program, area = planningmode.split_home_cell(scalar(c[3]))
        out.append(
            {
                "id": c[0],
                "title": scalar(c[1]),
                "kind": scalar(c[2]),
                # The roll-up edge, authored HERE and nowhere else. The program tier holds no
                # list of its slices; one fact, one place.
                "program": program,
                "area": area,
                # The completion condition, in one checkable sentence. A register column
                # precisely so it cannot be skipped.
                #
                # `prose`, NOT `scalar`, and the difference is one cell in every corpus that has
                # one: this column is a SENTENCE, and `scalar` strips a backtick off each end —
                # correct for `Kind`, where the ticks quote a value, and destructive here, where
                # a sentence opening with a code span loses its opening mark and keeps the
                # orphaned closing one. See `markdown.prose`.
                "done": prose(c[4]),
                # A slice's OWN proof. OPTIONAL: absent is the honest *unproven* reading, and
                # a guessed proof is worse than none.
                "verified_by": listcell(c[5]),
                "depends_on": listcell(c[6]),
                "component": listcell(c[7]),
                "disposition": disposition(c[8]),
                "disposition_cell": c[8].strip(),
                "line": line,
            }
        )
    return localize_rows(out, own_name)


def fragment_next_id(root: Path, detail_subdir: str, prefix: str) -> str:
    """The next free id implied by a tier's fragments, or "" when there are none.

    The register table's `Next id:` counter was the one place that made a register file
    collision-prone even with per-row fragments: two branches that each add a fragment bump the
    same counter line. Deriving the next id from the fragments removes that shared line — the
    highest id on disk plus one, in the width the fragments already use.
    """
    frags = fragments(root, detail_subdir, id_pattern(prefix))
    if not frags:
        return ""
    highest = max(int(pid.split("-", 1)[1]) for pid, _, _ in frags)
    width = max(len(pid.split("-", 1)[1]) for pid, _, _ in frags)
    return f"{prefix}-{highest + 1:0{width}d}"


def next_ids(
    root: Path,
    program_file: str = PROGRAM_FILE,
    slice_file: str = SLICE_FILE,
    program_prefix: str = PROGRAM_PREFIX,
    slice_prefix: str = SLICE_PREFIX,
    program_detail_subdir: str = PROGRAM_DETAIL_SUBDIR,
    slice_detail_subdir: str = SLICE_DETAIL_SUBDIR,
) -> tuple[str, str]:
    """The two next-free ids: from the fragments when present, else the counters as written.

    `("", "")` when neither source yields a marker — a corpus with no register at all.
    """
    pg = fragment_next_id(root, program_detail_subdir, program_prefix)
    sl = fragment_next_id(root, slice_detail_subdir, slice_prefix)
    pgf, slf = program_register(root, program_file), slice_register(root, slice_file)
    if not pg and pgf.is_file():
        m = next_id_pattern(program_prefix).search(pgf.read_text(encoding="utf-8"))
        pg = m.group(1) if m else ""
    if not sl and slf.is_file():
        m = next_id_pattern(slice_prefix).search(slf.read_text(encoding="utf-8"))
        sl = m.group(1) if m else ""
    return pg, sl


def detail_body(path: Path) -> str:
    """A detail file's prose, with the `type:` header stripped. "" when there is none."""
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n.*?\n---\n?", text, re.S)
    return (text[m.end() :] if m else text).strip()
