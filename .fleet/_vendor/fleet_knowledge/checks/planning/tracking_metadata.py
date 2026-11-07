"""Validate tracking metadata + roll-up links across the three planning tiers.

Enforces that the plan is well-formed BEFORE anything downstream reads it:

  - **Programs** (a row in the program register): well-formed id, unique and matching the
    append-only counter, valid `Kind`, and a `Verified by` that names no PRD one of its own
    slices already names. A `kind: program` — named for what it BUILDS rather than the result
    it produces — with no proof at all is PRINTED as a finding (it can never complete) rather
    than failing the commit; see the clause below.
  - **Slices** (a row in the slice register): well-formed id, unique and matching the counter,
    valid `Kind`, a `Program` that RESOLVES to a program row, a non-empty `Done when`,
    `Depends on` entries that resolve and form a DAG. May carry its OWN `Verified by`. A slice
    whose member PRDs are ALL terminal must name a proof or be a deliberate waiver in the
    baseline, or the commit fails — the *unproven* cell is honest only while the cut is live.
  - **Detail files** are OPTIONAL prose. Each must name a real register row, and may carry NO
    frontmatter key but `type:` — the register holds all structure, and a second place to
    write it is a second place for it to drift.
  - **PRDs**: required fields including a `slice:` that RESOLVES; valid status; `prd:` matches
    the folder; `depends_on:` resolve; unique; and an optional `lane:` that, when present, names
    a REGISTERED lane (a corpus declares its lanes in `[fleet.planning] lanes`) — a name no lane
    registers is refused rather than silently built in the corpus's own repository (ENG-13263).

Roll-up guarantee: **every PRD has a slice, and every slice has a program** — so every PRD
transitively rolls up to a program. A missing or dangling link fails the commit.

**Only the PRD tier carries `status:`.** A slice's and a program's completion is COMPUTED from
their children, so `status:` is never stored above the PRD and nothing can drift — 33 of 40
stored mid-tier statuses were wrong on the day that model was written. For the same reason
there are **no dates anywhere on the ladder**: order comes from the dependency graph. The
header check below is EXACT, so a deleted column cannot come back: a `Theme`/`Target` pair went
because both were authored once and read by nothing (every filled `Target` held the identical
value), and a `Proof accepted` column went because it gated the computed reading on a human
attestation set on 0 of 13 programs — so the gate had never once opened.

Work-in-progress ceiling: at most `active_slice_ceiling` slices may hold a live (non-terminal)
PRD. Nothing previously bounded WIP, which is how 40 containers appeared.

Both tiers name their proof, and they name different things: a slice's asks *"does this slice
do what it said?"* and is normally one of its own member PRDs; a program's is the composed
thread across its slices and asks *"do these work together for a person?"*. **They may not be
the same PRD** — sharing one collapses the program's completion condition into that slice's.
Both fields are OPTIONAL — absent is the honest *unproven* reading, and a guessed proof would
be worse than none.

**A proof may be a drill record.** A `Verified by` entry `drill:<stem>` names
`<drills_dir>/<stem>.md`, and it is shipped when that record says `verdict: passed`. The gate
refuses an entry whose file is missing, is not `type: drill-record`, or carries no `verdict`;
the disjointness rule above treats a drill entry exactly like a PRD number. A program whose
composed proof is an observation — a failover drill, an estate move — names the record and
stops having to manufacture a proof PRD to close.

**Both tiers carry a second axis, `Disposition`, and it is a decision, never a ship-state.**
`adopted` is the norm; `withdrawn: decisions/<file>.md` cites the record that IS the reason
(the file must exist — a sentence in a cell is a reason nobody can find again); `superseded by
PG-NN` / `SL-NNN` names a successor that must resolve. `delivered`, `closed`, `done` and their
kin are refused by name with the reason: completion is computed from the member PRDs and the
proof, and a word claiming it in a cell is the stored mid-tier status this model deleted,
wearing a decision's clothes. Withdrawal is a register EDIT citing a decision, never a row
deletion — a deleted row takes every citation of its id with it. A withdrawn container that
still holds a live PRD is an ERROR: the register said stop and the PRD did not.

**The proof waiver is per-row at the slice tier and a file at the program tier.** A slice's
deliberate *no proof planned* decision is a reasoned `proof_waiver` on its own row fragment
(ENG-12602) — the former `slices/UNCLAIMED.baseline` was a shared generated file concurrent
branches collided on, and it is gone. A program's is `programs/UNCLAIMED.baseline`, which keeps
the file grammar and ratchet because a program row is far rarer and never the conflict source.
A program with no slice in flight, at least one shipped member somewhere under it, no
`Verified by` and no waiver fails the commit the way an all-terminal unproven slice does — the
*unproven* cell is honest only while something is moving.

**Every waiver states its kind (2026-10-07), with no default.** `excused` — no proof is needed,
and the entity is settled — or `deferred` — the proof is still owed, and the entity (and so its
program) stays open, saying what it waits on, until the proof lands. A deferred waiver names what
is owed. A slice says it on its row (`{"kind": ..., "owed": ..., "reason": ...}`), a program on its
baseline id line (`PG-17 excused`, `PG-30 deferred: <what is owed>`); a waiver stating no kind
fails the commit.

Ported from `scripts/validate_tracking_metadata.py`. Every message and the exit code are
unchanged, with ONE deliberate removal: the original also printed an advisory computing how
many days and hours a PRD had sat at `implementing`/`verified`. That is a duration, which
nothing in this package may emit, and it was advisory-only — it never moved the exit code.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fleet_knowledge import corpusref
from fleet_knowledge.corpusref import Corpora, parse_ref
from fleet_knowledge.planningmode import AREAS
from fleet_knowledge.prddeps import is_issue_key, prd_numbers
from fleet_knowledge.registers import (
    ADOPTED,
    AREAS_SUCCESSOR,
    DRILL_RECORD_TYPE,
    SUPERSEDED,
    SUPERSEDED_RE,
    WITHDRAWN_RE,
    baseline_line,
    drill_stem,
    is_drill,
    waiver_problem,
)
from fleet_knowledge.registers import slice_proof_waivers as _shared_slice_proof_waivers

from . import _registers
from ._api import ADVISORY, ERROR, Report, finding
from ._config import PlanningConfig
from ._markdown import cells, field, find_cycle, frontmatter, listfield, read, rel
from ._slicebase import SliceBase

NAME = "tracking-metadata"

# --- ship-state single-source-of-truth ---
# PRD lifecycle state lives ONLY in each PRD's own frontmatter `status:`. A slice's prose and a
# roadmap hold structure + linkage, never a copy of that state — copies drift. These patterns
# catch a reintroduced copy.
_ST = r"(?:stub|prd-drafted|designed|planned|implementing|verified|shipped|cancelled)"
PRD_LIST_CHECKBOX_RE = re.compile(r"^\s*-\s*\[[ xX~]\]\s*\d{4}\b")
PRD_LIST_STATUS_RE = re.compile(rf"^\s*-\s+\d{{4}}\b.*\(\s*\*{{0,2}}\s*{_ST}\b")
ROADMAP_LINK_STATUS_RE = re.compile(rf"\]\([^)]*\)\s*[—–-]\s*\*{{0,2}}\s*(?i:{_ST})\b")
ROADMAP_PAREN_STATUS_RE = re.compile(rf"\(\s*\*{{0,2}}\s*{_ST}\b")
ROADMAP_CELL_STATUS_RE = re.compile(rf"\|\s*\*{{0,2}}\s*{_ST}\b")

DIFF_LABEL_RE = re.compile(r"^diff:(\d+)-")

# An entry may carry trailing `key: "quoted value"` fields after `by:` — `note:` is a real
# convention. The quoted value is free prose and may itself contain commas, colons and braces,
# so it must be consumed by a quote-aware alternation bounded by the closing (non-escaped)
# quote — never a naive `.*` up to the last `}`, which both over- and under-matches. A trailing
# field may also carry an UNQUOTED scalar (an issue key), a bare token with no whitespace, so
# it must not be wrapped in the alternation that exists to protect free prose. `by:` values are
# stamper names and may be colon-qualified (`prd:design`).
STATUS_ENTRY_RE = re.compile(
    r"^\s*-\s*\{\s*state:\s*([a-z-]+)\s*,\s*at:\s*(\S+?)\s*,\s*by:\s*([a-z:-]+)\s*"
    r'((?:,\s*[a-z_]+:\s*(?:"(?:[^"\\]|\\.)*"|\S+))*)\s*\}'
)


def norm_prd(n: str) -> str:
    """Zero-pad a PRD reference to the canonical 4-digit number (`14` -> `0014`)."""
    return n if n.isdigit() and len(n) == 4 else n.zfill(4)


def norm_proof(entry: str) -> str:
    """One `Verified by` entry in its canonical spelling: a 4-digit PRD number, or `drill:<stem>`.

    The disjointness rule keys on this, so a drill named by a program and by one of its slices
    collides exactly as a shared PRD number does — the same borrowed-proof failure, whichever
    kind of evidence was borrowed.
    """
    return f"drill:{drill_stem(entry)}" if is_drill(entry) else norm_prd(entry)


def status_history(fm: str) -> list[tuple[str, str, str, str]]:
    """Parse `status_history:` into `[(state, at, by, trailing_fields)]` in file order."""
    block = re.search(r"^status_history:\s*$(.*?)(?=^\S|\Z)", fm, re.M | re.S)
    if not block:
        return []
    out = []
    for line in block.group(1).splitlines():
        if m := STATUS_ENTRY_RE.match(line):
            out.append((m.group(1), m.group(2), m.group(3), m.group(4)))
    return out


_FIELD_RE = re.compile(r',\s*([a-z_]+):\s*(?:"((?:[^"\\]|\\.)*)"|(\S+?))\s*(?=,|$)')
_ISO_DAY_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def status_fields(extra: str) -> dict[str, str]:
    """The trailing `key: value` fields of one status_history entry, values unquoted."""
    return {m.group(1): (m.group(2) if m.group(2) is not None else m.group(3)) for m in _FIELD_RE.finditer(extra)}


def owner_acceptance_problem(extra: str) -> str | None:
    """Why an owner-accepted `verified` entry does not stand, or None when it does.

    The form records a different fact from a verify stamp: the accountable person accepted the
    PRD on their own word, and no independent verify pass is claimed. That is honest only when
    the record carries the person's words and their name — without them the entry is an agent
    writing "the owner said so", indistinguishable from self-certification.
    """
    fields = status_fields(extra)
    note = fields.get("note", "").strip()
    who = fields.get("accepted_by", "").strip()
    if not note:
        return "carries no `note:` quoting the person's words"
    if not _ISO_DAY_RE.search(note):
        return "has a `note:` with no date (YYYY-MM-DD) saying when the person gave their word"
    if not who:
        return "carries no `accepted_by:` naming the person who accepted it"
    return None


def is_refutation_revert(
    cfg: PlanningConfig, state: str, by: str, extra: str, seen_verified: bool, seen_shipped: bool
) -> bool:
    """A documented backwards transition after a design was refuted.

    The forward-only rule is right for every ordinary transition, and it had one genuine gap: a
    design that gets REFUTED after it was planned. The lifecycle has no state for "the job story
    stands, the design does not" — `cancelled` is wrong (the PRD is alive) and staying `planned`
    is a lie (there are no valid plans). Silently dropping the entry and flipping `status:` would
    pass every check and is exactly the dishonest fix: the event genuinely happened, and the
    record should say so.

    The exemption is deliberately narrow and cannot manufacture a forward transition. It only
    moves a PRD BACKWARDS into a drafting-stage state — the safe direction, since every gate
    downstream must then be re-earned; it must be stamped by a stage entitled to invalidate its
    own output and carry a `note:` beginning `REVERTED`; and a `verified` or `shipped` entry
    anywhere earlier disqualifies it — a shipped PRD is not re-drafted, it gets a successor.
    """
    if state not in cfg.revert_target_states or by not in cfg.revert_stampers:
        return False
    if seen_verified or seen_shipped:
        return False
    return re.search(r"note:\s*[\"']?REVERTED\b", extra) is not None


class _Run:
    """One pass over one knowledge base. Holds the accumulating findings."""

    def __init__(self, kb: Any) -> None:
        self.kb = kb
        self.root = Path(kb.root)
        self.regs = _registers.of(kb)
        self.cfg = self.regs.cfg
        self.report = Report()
        # The repo-qualified references (`fleet:0899`, `fleet:SL-139`) this corpus may make, and
        # the ones this run could not verify — see `fleet_knowledge.corpusref`.
        self.corpora = Corpora.of(kb)

    # --- recording ---

    def err(self, path: Path, msg: str, **extra: Any) -> None:
        self.report.error_lines.append(f"{rel(path, self.root)}: {msg}")
        self.report.findings.append(finding(ERROR, msg, path=path, **extra))

    def bare(self, msg: str, path: Path | None = None, **extra: Any) -> None:
        """A finding whose printed line carries its own formatting (or names no file)."""
        self.report.error_lines.append(msg)
        self.report.findings.append(finding(ERROR, msg, path=path, **extra))

    def note(self, path: Path, line: int, msg: str, **extra: Any) -> None:
        self.report.notes.append(f"note: {rel(path, self.root)}:{line}: {msg}")
        self.report.findings.append(finding(ADVISORY, msg, path=path, line=line, **extra))

    def row_path(self, row: dict[str, Any], register: Path) -> Path:
        """Where a row's finding belongs: its fragment file when it has one, else the register.

        A row read from a per-row fragment (ENG-12549) names that file, so a message about it
        points at the thing its author edits. A row read from the table names the register.
        """
        return Path(row["source"]) if row.get("source") else register

    def row_where(self, row: dict[str, Any]) -> str:
        """The `line N: \\`ID\\`` prefix a finding prints — or just the id beside a fragment."""
        if row.get("source"):
            return f"`{row['id']}`"
        return f"line {row['line']}: `{row['id']}`"

    # --- register shape ---

    def check_register_shape(
        self,
        path: Path,
        id_re: re.Pattern[str],
        shape: str,
        rows: list[dict[str, Any]],
        columns: tuple[str, ...],
        rows_dir: Path | None = None,
    ) -> bool:
        """Ids well-formed and unique, the append-only counter correct, no ship-state column.

        The counter is what makes an id permanent and therefore safe to cite from a PRD that
        shipped a year ago — the same rule every append-only register follows.

        **When the tier has row fragments, the fragments are the register.** The committed
        table is a generated projection of them (ENG-12549), so the shape checked is the
        fragment directory's: every `*.json` whose stem is an id, ids unique, and no table
        header or counter to validate (the generator and this repository's `--check` gate own
        those). The table itself may be absent — dropping it is the point (ENG-12546).

        Returns whether the header row carries a `Disposition` column. The per-row disposition
        rule needs to know: an empty cell under a header that has the column is a row somebody
        forgot to fill and is refused, while a register with no such column at all has already
        failed the exact-header check above and every row would only repeat that finding. A
        fragment always carries the key, so the fragment branch reads it as present.
        """
        if rows_dir is not None and rows_dir.is_dir() and any(rows_dir.glob("*.json")):
            return self._check_fragment_shape(rows_dir, id_re, shape, rows)
        if not path.is_file():
            self.bare(
                f"{rel(path, self.root)} is missing — it is the register for this tier",
                path=path,
                hint="Create the register — this tier has nowhere to author a row without it.",
            )
            return False
        text = read(path)
        has_disposition = False

        seen: dict[str, int] = {}
        for r in rows:
            if r["id"] in seen:
                self.err(
                    path,
                    f"line {r['line']}: duplicate id `{r['id']}` (also line {seen[r['id']]}) — "
                    "ids are permanent and never reused",
                    line=r["line"],
                    hint="Give the newer row a freshly allocated id; never reuse one.",
                )
            seen[r["id"]] = r["line"]

        # No `Next id:` counter is required (2026-09-29): ids are reserved as claim refs on
        # GitHub (`id_collisions --allocate`), so no mint edits a shared line. A legacy counter
        # left in a register is inert text.

        # The header row is checked rather than trusted: a `Status` column reintroduced here is
        # precisely the stored mid-tier ship-state this model deleted.
        for line in text.splitlines():
            if not line.lstrip().startswith("|"):
                continue
            row = [c.strip().lower() for c in cells(line)]
            if row and row[0] == "id":
                has_disposition = "disposition" in row
                if "status" in row:
                    self.err(
                        path,
                        "a `Status` column is not authored above the PRD tier — completion is "
                        "computed from the member PRDs and the proof; delete the column",
                        hint="Delete the column; ship-state above the PRD tier is computed, never stored.",
                    )
                want_cols = [c.lower() for c in columns]
                if row == want_cols[:-1] and want_cols[-1] == "disposition":
                    # THE MIGRATION WINDOW. A register authored before the `Disposition` axis
                    # existed is the exact shape minus the last column — padded, never shifted,
                    # which is what LAST bought — and it is what every consuming repository
                    # carries on the day this package ships the axis. Refusing it outright made
                    # the package unpinnable by its own consumers until each had migrated, with
                    # the migration and the pin in one commit that no gate could land: every
                    # OTHER fix in that pin waited on a planning decision. So the pre-axis shape
                    # is an ADVISORY naming the migration, and only that shape: one column short
                    # of exact, at the end. Anything else is still the error below.
                    self.note(
                        path,
                        next(i for i, ln in enumerate(text.splitlines(), 1) if ln.lstrip().startswith("|")),
                        f"the register predates the `{columns[-1]}` axis — add the column (LAST; "
                        "`adopted` on every live row) and, for programs, name each finished program's "
                        "proof or waive it; until then every row reads as adopted and the program-tier "
                        "proof rule reports advisories, never errors",
                        hint=f"Add `{columns[-1]}` as the last column; every live row is `adopted`.",
                    )
                elif row != want_cols:
                    self.err(
                        path,
                        f"columns are {row} — expected {want_cols}",
                        hint="Every row is read POSITIONALLY — restore the exact column order.",
                    )
                break

        # A MALFORMED id has to be caught on the RAW table, never on `rows`: the shared reader
        # filters on this same pattern, so a row it rejects never arrives here and the row simply
        # VANISHES — `SL-13` typed for `SL-137` deletes a slice from the register with no
        # complaint, and the only downstream signal is a confusing "does not resolve" against
        # whatever still points at it (or, if nothing does, silence).
        tier = shape.split("-")[0]
        for i, line in enumerate(text.splitlines(), 1):
            if not line.lstrip().startswith("|"):
                continue
            c = cells(line)
            first = c[0].strip() if c else ""
            if first.startswith(f"{tier}-") and not id_re.match(first):
                self.err(
                    path,
                    f"line {i}: `{first}` is not a well-formed `{shape}` id — the row is invisible to "
                    "every reader of this register, so it would otherwise disappear silently",
                    line=i,
                    hint=f"Correct the id to the `{shape}` shape — a malformed row is silently dropped.",
                )
        return has_disposition

    def _check_fragment_shape(
        self,
        rows_dir: Path,
        id_re: re.Pattern[str],
        shape: str,
        rows: list[dict[str, Any]],
    ) -> bool:
        """The fragment-directory reading of `check_register_shape`: ids well-formed and unique.

        No counter to check — the next free id is derived from the fragments, not written — and
        no table header, because the table is a projection the generator owns. What survives is
        the one thing the reader cannot enforce: a fragment whose FILENAME is not a well-formed
        id vanishes from every reader exactly as a malformed table row does, so it is caught on
        the raw glob rather than on `rows`.
        """
        seen: dict[str, Path] = {}
        for r in rows:
            src = self.row_path(r, rows_dir)
            if r["id"] in seen:
                self.err(
                    src,
                    f"duplicate id `{r['id']}` (also {rel(seen[r['id']], self.root)}) — ids are "
                    "permanent and never reused",
                    line=r["line"],
                    hint="Give the newer row a freshly allocated id; never reuse one.",
                )
            seen[r["id"]] = src
        tier = shape.split("-")[0]
        for f in sorted(rows_dir.glob("*.json")):
            if f.stem.startswith(f"{tier}-") and not id_re.match(f.stem):
                self.err(
                    f,
                    f"`{f.stem}` is not a well-formed `{shape}` id — the fragment is invisible to "
                    "every reader of this register, so it would otherwise disappear silently",
                    hint=f"Rename the fragment to the `{shape}` shape — a malformed id is silently dropped.",
                )
        return True

    # --- the decision axis ---

    def check_disposition(
        self,
        path: Path,
        row: dict[str, Any],
        *,
        header_has_column: bool,
        id_re: re.Pattern[str],
        ids: set[str],
        shape: str,
        kind: str,
    ) -> None:
        """One row's `Disposition` cell: on the grammar, and pointing at something real.

        THREE VALUES AND NOTHING ELSE. The refusal for a ship-state word is specific on
        purpose: `delivered` is exactly what somebody reaching for a status column types, and
        a generic "not on the grammar" would send them to the grammar rather than to the reason
        — completion is COMPUTED above the PRD tier, and a cell claiming it is the stored
        mid-tier status this model deleted (33 of 40 were wrong).

        `withdrawn:` must cite a file that exists: the record IS the reason, and a path to a
        file nobody wrote is free text with a colon in it. `superseded by` must name a row in
        THIS register, in this tier's id shape, and not the row itself.
        """
        cfg = self.cfg
        path = self.row_path(row, path)
        raw = str(row.get("disposition_cell", "")).strip().strip("`").strip()
        where = self.row_where(row)
        if not raw or raw in ("—", "–", "-", "n/a"):
            if header_has_column:
                self.err(
                    path,
                    f"{where} has an empty `Disposition` — write `adopted`; the cell says what "
                    "happened to this row as a decision, and an empty one says nobody decided",
                    line=row["line"],
                    hint="Write `adopted` (the norm), `withdrawn: <decision record>` or `superseded by <id>`.",
                )
            return
        if raw == ADOPTED:
            return
        lowered = raw.lower()
        if lowered in cfg.disposition_ship_state_words:
            self.err(
                path,
                f"{where} `Disposition` is `{raw}` — that is a ship-state claim, and ship-state above "
                "the PRD tier is COMPUTED from the member PRDs and the proof, never written. "
                "`Disposition` records a DECISION: `adopted`, `withdrawn: <decision record>` or "
                "`superseded by <id>`. If the work is done, name its proof in `Verified by` and let "
                "the reading say so",
                line=row["line"],
                hint="Delete the word. Completion is derived; write the proof, or a decision, never a status.",
            )
            return
        if m := WITHDRAWN_RE.match(raw):
            target = self.regs.knowledge / m.group(1)
            if not target.is_file():
                self.err(
                    path,
                    f"{where} is `withdrawn: {m.group(1)}` but no such file exists under "
                    f"{rel(self.regs.knowledge, self.root)}/ — the decision record IS the reason, "
                    "and a path to nothing is free text with a colon in it",
                    line=row["line"],
                    hint="Write the decision record first, then cite its corpus-relative path here.",
                )
            return
        if m := SUPERSEDED_RE.match(raw):
            successor = m.group(1)
            if successor == AREAS_SUCCESSOR:
                # A PROGRAM CLOSED INTO FEATURE AREAS (FLT-1283, 2026-10-29): its work went to areas, not to
                # another row. Only a program can be: a slice is the unit an area holds, so a slice that
                # stopped is `withdrawn` with its record, or folded into another slice.
                if kind != corpusref.PROGRAM:
                    self.err(
                        path,
                        f"{where} is `superseded by {AREAS_SUCCESSOR}`, which only a program may be — a slice "
                        "is what a feature area holds",
                        line=row["line"],
                        hint=(
                            "Write `adopted` and name its `area`, `withdrawn: <decision record>`, "
                            "or `superseded by <id>`."
                        ),
                    )
                return
            sref = parse_ref(successor)
            if not self.corpora.is_local(sref):
                # The work moved to ANOTHER corpus (`superseded by fleet:PG-047`): the successor is
                # resolved there, never against this register's ids.
                res = self.corpora.resolve(sref, kind, where=f"{rel(path, self.root)} {row['id']}")
                if res.is_error:
                    self.err(
                        path,
                        f"{where} is `superseded by {successor}` — {res.message}",
                        line=row["line"],
                        hint="Correct the qualified successor, or declare its corpus.",
                    )
                return
            successor = sref.id
            if not id_re.match(successor):
                self.err(
                    path,
                    f"{where} is `superseded by {successor}`, which is not a `{shape}` id — a "
                    "successor is a row in THIS register, in this tier's own shape",
                    line=row["line"],
                    hint=f"Name the `{shape}` row the work folded into.",
                )
            elif successor == row["id"]:
                self.err(
                    path,
                    f"{where} is superseded by itself",
                    line=row["line"],
                    hint="Name the row the work folded into, or write `adopted`.",
                )
            elif successor not in ids:
                self.err(
                    path,
                    f"{where} is `superseded by {successor}`, which is not a row in this register",
                    line=row["line"],
                    hint="Author the successor row first, or correct the id.",
                )
            return
        self.err(
            path,
            f"{where} `Disposition` is `{raw}` — not on the grammar. The cell is one of: `adopted`; "
            "`withdrawn: <corpus-relative path to a decision record>.md`; "
            f"`superseded by <{shape}>`. No free text: a reason lives in the record the cell cites",
            line=row["line"],
            hint="Write `adopted`, `withdrawn: decisions/<file>.md` or `superseded by <id>` — nothing else.",
        )

    def check_supersession_graph(self, path: Path, rows: list[dict[str, Any]]) -> None:
        """`superseded by` edges may not form a cycle — two rows folding into each other fold
        into nothing, and a reader following the chain to the successor would never arrive."""
        graph = {
            r["id"]: [str(r["disposition"]["ref"])]
            for r in rows
            if r["disposition"]["kind"] == SUPERSEDED
            and r["disposition"]["ref"]
            and r["disposition"]["ref"] != AREAS_SUCCESSOR
        }
        if cyc := find_cycle(graph):
            self.bare(
                f"supersession cycle: {' -> '.join(cyc)} — each names the other as its successor, so neither has one",
                path=path,
                hint="Break the cycle: one of these rows is the successor, and the other is superseded by it.",
            )

    def check_detail_files(self, directory: Path, ids: set[str], want_type: str) -> None:
        """A detail file is OPTIONAL prose named for a register row, and holds no structure.

        Two rules, both because the register is meant to be the only place structure lives: the
        filename must name a real row — an orphan detail file is prose nobody can reach from the
        register, which is how a deleted entity's text survives as a ghost; and the frontmatter
        may carry `type:` and nothing else, because any other key would be a second, unread copy
        of a register column.
        """
        if not directory.is_dir():
            return
        for f in sorted(directory.glob("*.md")):
            if f.name in ("README.md", "_TEMPLATE.md"):
                continue
            if f.stem not in ids:
                self.err(
                    f,
                    f"`{f.stem}` is not a row in the register — a detail file is named for its row, "
                    "and the filename is the join",
                    hint="Author the register row, rename the file to a real id, or delete the ghost prose.",
                )
            fm = frontmatter(read(f))
            if fm is None:
                self.err(f, f"missing frontmatter `type: {want_type}`")
                continue
            keys = [m.group(1) for m in re.finditer(r"^([A-Za-z_][\w-]*):", fm, re.M)]
            extra = [k for k in keys if k != "type"]
            if extra:
                self.err(
                    f,
                    f"frontmatter carries {extra} — a detail file holds prose only; every "
                    "structural field belongs in the register, where nothing can shadow it",
                    hint="Move each structural field into the register row and delete it here.",
                )

    # --- PRD status history ---

    def check_status_history(self, f: Path, fm: str) -> None:
        """A PRD's recorded lifecycle must be ordered, and `verified` must be independent.

        `status_history` was written by every stage and read by nothing, so a PRD could go
        `prd-drafted -> shipped` in one edit and pass every hook. Three rules make the field
        load-bearing: transitions move forward, `shipped` is preceded by `verified`, and only the
        independent verify stage may stamp `verified` — with one narrow post-`shipped`
        risk-acceptance exemption, and one owner-acceptance form (`by: owner-accepted`) that
        records a named person's dated word instead of a verify pass and stands only with a
        `note:` quoting that word and an `accepted_by:` naming the person.

        `verified` means nothing when the party that wrote the code also stamps it. Measured
        before this rule: of 267 `verified` stamps, 193 were `by: implement` and 27 by an
        implement-verify hybrid — 82% self-certified — while an independent verify accounted for
        45.

        Deliberately NOT also checked: that `at:` timestamps increase. That looked like a cheap
        win from one forged history until it was checked against the live corpus, where it is
        routine noise — `at:` is a value the authoring session TYPES, not a captured clock
        reading, and several genuinely-verified shipped PRDs record `implementing` before the
        `planned` entry above it. A rule that fires on normal history is worse than no rule: it
        trains everyone to ignore this validator's output.
        """
        cfg = self.cfg
        hist = status_history(fm)
        if not hist:
            return
        prev_rank = -1
        seen_verified = False
        seen_shipped = False
        for state, at, by, extra in hist:
            if state == "cancelled":  # terminal from anywhere
                continue
            if state not in cfg.prd_order:
                continue  # the enum check owns unknown states
            rank = cfg.prd_order.index(state)
            recent = at >= cfg.status_history_cutover
            # A human's post-hoc "this shipped unaudited and I accept that" is the one entry that
            # legitimately reads out of rank order, because the event it records genuinely
            # happened after the ship. Backdating it to sort correctly would be the dishonest fix.
            risk_acceptance = state == "verified" and seen_shipped and by in cfg.risk_acceptance_stampers
            revert = is_refutation_revert(cfg, state, by, extra, seen_verified, seen_shipped)
            if recent and rank < prev_rank and not risk_acceptance and not revert:
                self.err(f, f"status_history goes backwards: `{cfg.prd_order[prev_rank]}` then `{state}` at {at}")
            owner_accepted = state == "verified" and by in cfg.owner_acceptance_stampers
            if state == "verified":
                if owner_accepted and (why := owner_acceptance_problem(extra)):
                    self.err(
                        f,
                        f"`verified` stamped `by: {by}` at {at} {why} — an owner acceptance records that "
                        "a named person accepted the PRD on their own dated word, and without both the "
                        "words and the name it is an agent certifying itself",
                        hint="Write `note: \"Owner accepted <YYYY-MM-DD>: '<their words>'\"` and "
                        '`accepted_by: "<person>"`, or hand off to an independent verify pass.',
                    )
                elif owner_accepted:
                    pass  # a named person's dated word, recorded as exactly that — not a verify pass
                elif risk_acceptance and "note:" not in extra:
                    self.err(
                        f,
                        f"`verified` stamped `by: {by}` at {at} after `shipped` is a retroactive risk "
                        "acceptance and MUST carry a `note:` saying no verify pass ran — an unexplained "
                        "one is indistinguishable from a fabricated audit",
                        hint="Add a `note:` saying, in the record, that no verify pass ran and why that stands.",
                    )
                elif recent and not risk_acceptance and by not in cfg.verified_stampers:
                    self.err(
                        f,
                        f"`verified` stamped `by: {by}` at {at} — only "
                        f"{'/'.join(sorted(cfg.verified_stampers))} may; the party that wrote the "
                        "code cannot certify its own acceptance criteria",
                        hint="Hand off to an independent verify pass and let it write the stamp.",
                        command=cfg.command("prd_verify", prd=f.parent.name.split("-", 1)[0]),
                    )
                seen_verified = True
            if state == "shipped":
                if recent and not seen_verified:
                    self.err(
                        f,
                        f"`shipped` at {at} without a preceding `verified` — nothing independently confirmed it",
                        hint="A ship needs an independent verify entry ahead of it in the record.",
                        command=cfg.command("prd_verify", prd=f.parent.name.split("-", 1)[0]),
                    )
                seen_shipped = True
            # A sanctioned revert genuinely moves the PRD BACK, so it resets the high-water mark
            # rather than advancing it. Without this the exemption is self-defeating: the
            # backwards entry passes, but a `max()` keeps `prev_rank` at the pre-revert peak, so
            # every subsequent forward step reads as backwards — a reverted PRD could never be
            # re-designed, which is the only thing a reverted PRD can do next. The reset is to
            # the revert's OWN rank, never lower, so one revert cannot disable the rule for the
            # rest of the PRD's life.
            prev_rank = rank if revert else max(prev_rank, rank)

    # --- ship-state copies ---

    def check_status_copies(self) -> None:
        """PRD ship-state must not be copied into a slice's prose or the roadmap.

        State lives only in each PRD's own frontmatter `status:`. A slice detail file's PRD list
        and the roadmap hold structure + linkage; a copied status drifts.
        """
        for f in sorted(self.regs.slice_detail_dir.glob("SL-*.md")):
            for i, line in enumerate(read(f).splitlines(), 1):
                if PRD_LIST_CHECKBOX_RE.search(line):
                    self.err(
                        f,
                        f"line {i}: PRD-list checkbox encodes ship-state — drop the `[ ]`/`[x]` "
                        "and read state from the PRD frontmatter `status:`",
                        line=i,
                        hint="Delete the checkbox — state is read from the PRD, never copied.",
                    )
                elif PRD_LIST_STATUS_RE.search(line):
                    self.err(
                        f,
                        f"line {i}: PRD-list `(status)` annotation copies ship-state — remove it "
                        "and read from the PRD frontmatter `status:`",
                        line=i,
                        hint="Delete the annotation — state is read from the PRD, never copied.",
                    )
        rf = self.regs.knowledge / self.cfg.roadmap_file
        # A GENERATED projection renders live status by design and cannot drift (re-derived from
        # frontmatter each run), so the ban applies only to hand-maintained files.
        if rf.is_file() and "generated:" not in (frontmatter(read(rf)) or ""):
            for i, line in enumerate(read(rf).splitlines(), 1):
                if (
                    ROADMAP_LINK_STATUS_RE.search(line)
                    or ROADMAP_PAREN_STATUS_RE.search(line)
                    or ROADMAP_CELL_STATUS_RE.search(line)
                ):
                    self.err(
                        rf,
                        f"line {i}: ship-state attached to a PRD reference — roadmap holds "
                        "structure only; read state from each PRD's frontmatter `status:`",
                        line=i,
                        hint="Drop the state from the reference — the roadmap holds linkage only.",
                    )

    # --- proof disjointness ---

    def check_proof_disjointness(self, programs: list[dict[str, Any]], slices: list[dict[str, Any]]) -> None:
        """A program's `Verified by` must not intersect any of its own slices'.

        The two fields answer deliberately different questions. A slice's asks *"does this slice
        do what it said?"*; a program's asks *"do these slices work together for a person?"* and
        is the composed thread ACROSS them. When one PRD is named by both, the program's
        completion condition collapses into its slice's: the composed reading goes green the
        moment the slice's own proof does, and the program can never say anything the slice did
        not already say. That is the walking-skeleton failure inverted — a whole program claiming
        to be proven by a thread that only ever entered one of its parts.

        FATAL. It shipped ADVISORY for exactly as long as the six live collisions existed, because
        failing the commit then would have blocked every unrelated change behind six product
        decisions nobody had been asked to make. The owner made that call once and it was the same
        one six times: clear the PROGRAM's cell rather than promote a slice-wide run into a
        composed claim. An advisory whose entire justification has been removed is a check that
        rots, so it bites — the borrowed proof cannot come back the way it arrived.
        """
        proofs_by_program: dict[str, list[tuple[str, str]]] = {}
        for s in slices:
            for num in (norm_proof(x) for x in s["verified_by"]):
                proofs_by_program.setdefault(s["program"], []).append((num, s["id"]))
        for p in programs:
            mine = {n for n, _ in proofs_by_program.get(p["id"], [])}
            # `norm_proof`, so a drill record shared between a program and one of its cuts is
            # the same collision as a shared PRD number: the evidence's kind does not change
            # what borrowing it does to the program's completion condition.
            for num in sorted({norm_proof(x) for x in p["verified_by"]} & mine):
                owners = ", ".join(sorted(sid for n, sid in proofs_by_program[p["id"]] if n == num))
                self.err(
                    self.regs.program_register,
                    f"{p['id']} names {num} as its proof, and so does {owners} in "
                    f"{self.regs.slice_register.name} — a program's proof is the composed thread ACROSS "
                    "its slices; sharing one collapses the program's completion condition into "
                    "that slice's (ENG-6025). THE PROGRAM SIDE CHANGES, never the slice's: the "
                    f"slice keeps {num} as its own local proof, and {p['id']} needs a proof that "
                    "drives the composed path — or an empty cell, which reads `unproven`",
                    line=p["line"],
                    hint=(
                        f"Clear {p['id']}'s `Verified by`, or point it at a PRD that drives the "
                        "composed path across its slices."
                    ),
                    command=self.cfg.command("program_decompose", program=p["id"]),
                )


# --- the slice proof waiver, ON THE ROW ----------------------------------------------------
# A slice whose member PRDs are ALL terminal must resolve its proof. `Verified by` is a slice's
# ONLY authored input to its completion reading, and it is OPTIONAL at the cut for the right
# reason — an empty cell is the honest *unproven* reading while the cut is live. But that reading
# has a shelf life. The moment a slice's last live PRD goes terminal, every member is done and the
# cell stops meaning "not proven yet" and starts meaning "will never be proven" — and nothing
# revisits it. That is how 23 all-terminal slices sat at *awaiting proof* forever, silently. So
# the gate fires exactly there, and the waiver is the explicit *"no proof planned, and here is
# why"* value: it distinguishes a waived slice from one genuinely still awaiting a proof it has
# named.
#
# **The waiver lives on the slice's OWN row fragment (ENG-12602), never in a shared baseline
# file.** The former `slices/UNCLAIMED.baseline` was generated and regenerated by every concurrent
# branch, so two branches touched it at once and collided by construction (PRD 0677 / ENG-11933
# was parked twice on exactly that). A per-row field cannot collide: each branch edits only its
# own row. The reason is the field's whole value — a waiver with no reason is a silent
# grandfather — so the repo's binding refuses one under a minimum length. The program tier keeps
# its baseline file: a program's rows are far fewer and its waiver is not the conflict source the
# slice tier was.


def program_proof_baseline_path(kb: Any) -> Path:
    """Where this knowledge base records its deliberate program proof waivers."""
    return Path(kb.knowledge) / PlanningConfig.of(kb).program_proof_baseline


def _read_baseline_lines(p: Path) -> dict[str, tuple[str, str, str]]:
    """`{id: (kind, owed, the id line as written)}` for one waiver file.

    Since 2026-10-07 the id line carries the waiver's KIND — `PG-17 excused`, `PG-30 deferred: <what
    is owed>` — read by `registers.baseline_line`, the board's own reader, so the gate and the board
    cannot disagree about what a line says. A bare id is a waiver with no kind, which the gate refuses.
    """
    if not p.is_file():
        return {}
    out: dict[str, tuple[str, str, str]] = {}
    for line in read(p).splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parsed = baseline_line(s)
        if parsed is not None:
            out[parsed[0]] = (parsed[1], parsed[2], s)
    return out


def _read_baseline(p: Path) -> set[str]:
    """The ids in one waiver file — the first token of every non-blank line that is not a comment."""
    return set(_read_baseline_lines(p))


def program_proof_baseline(kb: Any) -> set[str]:
    """Program ids whose composed proof is explicitly waived — excused or deferred alike."""
    return _read_baseline(program_proof_baseline_path(kb))


def program_proof_baseline_kinds(kb: Any) -> dict[str, tuple[str, str]]:
    """`{program id: (kind, owed)}` for every waiver in the programs baseline."""
    return {k: (kind, owed) for k, (kind, owed, _line) in _read_baseline_lines(program_proof_baseline_path(kb)).items()}


def slice_proof_waivers(slices: list[dict[str, Any]]) -> set[str]:
    """Slice ids carrying a reasoned `proof_waiver` on their own row (ENG-12602) — the shared reader."""
    return _shared_slice_proof_waivers(slices)


#: The program tier's waiver file: which config path, which reader, the noun a message uses, and
#: the word for the members whose terminality freezes the cell.
_BASELINE_HEADER = (
    "# Generated by: python3 scripts/validate_tracking_metadata.py --write-baseline\n"
    "# Every line is a {noun} id whose {members} are ALL terminal but whose `Verified by`\n"
    "# is empty — a {noun} that can never read complete (ENG-8096). A line here is the\n"
    "# explicit *no proof planned, and here is why* waiver: it distinguishes a deliberately\n"
    "# unproven {noun} from one genuinely still awaiting a proof it has named. Burn this\n"
    "# down by naming the proof (backfill) and removing the line here; add a NEW entry only\n"
    "# with an `# ack: <id> <reason>` comment above it. The baseline may shrink, never grow.\n"
    "# Every id line states its kind (2026-10-07): `<id> excused` — no proof is needed, and the\n"
    "# {noun} is settled — or `<id> deferred: <what is owed>` — the proof is still owed, and the\n"
    "# {noun} stays open until it lands. A line with no kind is refused.\n"
)


def _acks(p: Path) -> dict[str, list[str]]:
    """The `# ack:` comment block written above each id in an existing baseline, by id.

    The reasons are the baseline's whole value — an id with no `# ack:` above it is a waiver
    nobody argued — and a regeneration that dropped them would turn seventeen argued waivers
    into seventeen bare ids in one hand-off. Only the block directly above an id is kept, and
    only for an id still in the set: the generated header is not an ack, and a reason for a
    waiver that no longer exists is not carried into a file that no longer names it.
    """
    if not p.is_file():
        return {}
    out: dict[str, list[str]] = {}
    pending: list[str] = []
    for line in read(p).splitlines():
        stripped = line.strip()
        if not stripped:
            pending = []
        elif stripped.startswith("#"):
            if stripped.startswith("# ack:") or pending:
                pending.append(line)
        else:
            parsed = baseline_line(stripped)
            if pending and parsed is not None:
                out[parsed[0]] = pending
            pending = []
    return out


def _write_baseline(p: Path, ids: set[str], *, noun: str, members: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    acks = _acks(p)
    # An id line keeps the KIND a person wrote on it (2026-10-07): a regeneration that rewrote
    # `PG-30 deferred: <owed>` as a bare `PG-30` would unclassify every waiver in one hand-off. A
    # NEW id is written bare, and the gate refuses it until somebody says which kind it is.
    lines = {k: line for k, (_kind, _owed, line) in _read_baseline_lines(p).items()}
    body = "".join("".join(f"{c}\n" for c in acks.get(i, [])) + f"{lines.get(i, i)}\n" for i in sorted(ids))
    p.write_text(_BASELINE_HEADER.format(noun=noun, members=members) + body, encoding="utf-8")
    return p


def write_program_proof_baseline(kb: Any, ids: set[str]) -> Path:
    """Regenerate the program waiver baseline.

    The set is the program-tier reading of the rule: every member PRD under every slice
    terminal, at least one of them shipped, no composed proof named, and the row `adopted` —
    a withdrawn program needs neither a proof nor a waiver. There is no slice counterpart since
    ENG-12602: a slice's waiver is a per-row `proof_waiver`, and nothing regenerates it.
    """
    return _write_baseline(program_proof_baseline_path(kb), ids, noun="program", members="slices' member PRDs")


def _live_slice_ids(kb: Any) -> frozenset[str] | None:
    """The live slices, by `fleet planning migrate`'s rule over the board, or None when the board cannot be read.

    None fails safe: every untouched row without an area is then treated as live, which is what the setting
    asked for before liveness was considered. The board is read only when `require_area` has a row to judge.
    """
    from fleet_knowledge import board, planningmigrate  # noqa: PLC0415 — the board is heavy; most runs never need it

    try:
        return planningmigrate.live_slice_ids(board.build(Path(kb.knowledge), config=kb.config))
    except Exception:  # noqa: BLE001 — a corpus too broken to draw is reported by the rest of this check
        return None


def analyse(kb: Any, *, write_baseline: bool = False) -> Report:  # noqa: C901, PLR0912, PLR0915 - one pass, ported whole
    """Every tracking-metadata violation, in the original's order."""
    run = _Run(kb)
    cfg, regs = run.cfg, run.regs
    programs = regs.programs()
    slices = regs.slices()

    prds: dict[str, tuple[Path, str]] = {}
    prd_base = regs.prds_dir
    if prd_base.exists():
        for d in sorted(prd_base.iterdir()):
            if not d.is_dir():
                continue
            f = d / "prd.md"
            if not f.is_file():
                run.err(f, "PRD folder has no prd.md")
                continue
            fm = frontmatter(read(f))
            if fm is None:
                run.err(f, "missing YAML frontmatter")
                continue
            prds[d.name] = (f, fm)

    prd_nums: set[str] = set()
    slices_by_program: dict[str, list[str]] = {}

    # --- programs ---
    pgr = regs.program_register
    pg_has_disp = run.check_register_shape(
        pgr, cfg.re_program_id(), cfg.program_id_shape, programs, cfg.program_columns, regs.program_rows_dir
    )
    program_ids = {p["id"] for p in programs}
    for p in programs:
        where = run.row_where(p)
        rp = run.row_path(p, pgr)
        run.check_disposition(
            pgr,
            p,
            header_has_column=pg_has_disp,
            id_re=cfg.re_program_id(),
            ids=program_ids,
            shape=cfg.program_id_shape,
            kind=corpusref.PROGRAM,
        )
        # There is NO `status` column and there never will be — the header check above rejects
        # one outright. Completion is computed from the slices and the proof. There is no date
        # column at any tier either, and the exact header check is what keeps one from coming back.
        if not p["title"]:
            run.err(rp, f"{where} has no Name", line=p["line"])
        if p["kind"] not in cfg.program_kinds:
            run.err(
                rp,
                f"{where} invalid kind `{p['kind']}` (allowed: {', '.join(sorted(cfg.program_kinds))})",
                line=p["line"],
            )
        # `kind: program` is the escape hatch that lets platform work be named for what it BUILDS
        # rather than the result it produces — and it is also exactly how stranded substrate
        # acquires a roadmap bar. So its proof is not optional: `Verified by` must name the PRD(s)
        # that drive a surface a customer touches.
        #
        # It PRINTS rather than failing the commit. Read together with the collision rule below,
        # a hard version would say: a `kind: program` MUST name a proof, AND that proof may not be
        # one of its slices'. Both are right, and together they make one true state
        # unrepresentable — a substrate program whose composed proof has not been written yet. A
        # required field with no honest value manufactures a borrowed one, which is the exact
        # defect the collision rule removed, so a register that cannot record "no composed proof
        # yet" would just regrow it.
        #
        # Nothing is lost by printing. The guarantee lives where it cannot be satisfied by a
        # string that merely resolves: a program with no `Verified by` can never compute
        # `complete`, and the board says so permanently and in two places — the dependency
        # chain draws a terminal node reading "no proof named · this program can never
        # complete", and `board.actions` raises a standing hygiene finding, "No proof named.
        # Nothing will ever mark this program complete." The hard obligation stays at AUTHORING
        # time, where it can be met honestly.
        # A withdrawn program owes no proof: the decision record is its answer. A drill
        # satisfies the obligation exactly as a PRD does — `verified_by` is non-empty either way.
        if p["kind"] == "program" and not p["verified_by"] and p["disposition"]["kind"] == ADOPTED:
            run.note(
                rp,
                p["line"],
                f"{p['id']} is `kind: program` — named for "
                "what it builds — and names no composed proof, so it can never complete. That is the "
                "finding, not a formatting gap: either its customer-facing surface is missing and "
                "belongs in scope, or it is really a `kind: outcome` whose outcome has not been "
                "stated. Do not write a placeholder to satisfy the reading",
                hint="Name a proof that drives a customer surface, or restate the row as an outcome.",
                command=cfg.command("program_decompose", program=p["id"]),
            )
    run.check_supersession_graph(pgr, programs)
    base = SliceBase(run.kb, cfg.default_diff_base)
    if cfg.mode == AREAS and base.available:
        # NO NEW PROGRAM IN `areas` MODE (owner, 2026-10-28: "in area mode we dont accept programs anymore! we dont
        # want more to migrate later!", FLT-1285): a program row the base commit did not hold is refused, whatever
        # else the change carries — its own slices included. An untouched or edited existing row is fine: existing
        # programs finish (FLT-1282).
        for p in programs:
            if not base.row_existed(p, pgr):
                run.err(
                    run.row_path(p, pgr),
                    f"{run.row_where(p)} is a new program, but this repository plans by area "
                    '(`.fleet/fleet.toml` `[fleet.planning] mode = "areas"`), so it takes no new program',
                    line=p["line"],
                    hint=(
                        "Drop the row and cut the work as slices under their areas (`slice:create`): work bigger "
                        "than one slice is several slices, ordered by their dependencies."
                    ),
                )

    # --- slices ---
    slr = regs.slice_register
    sl_has_disp = run.check_register_shape(
        slr, cfg.re_slice_id(), cfg.slice_id_shape, slices, cfg.slice_columns, regs.slice_rows_dir
    )
    prds_by_slice: dict[str, list[tuple[str, str]]] = {}
    slice_graph: dict[str, list[str]] = {}
    component_ids = regs.component_ids()
    areas = regs.feature_areas()
    if cfg.mode == AREAS and not base.available:
        if base.in_repository:
            # A GIT CHECKOUT THAT CANNOT COMPARE FAILS CLOSED (owner, 2026-10-29, ENG-21061): a shallow CI
            # clone or an unfetched base branch has a base commit one `git fetch` away, so noting the gap
            # let a new program row, or a slice joining a program, pass the areas rule silently. The
            # no-git case below stays a note — a tarball copy has no base to fetch, and git absence is
            # never a violation (`_git`'s rule).
            run.err(
                regs.slice_register,
                "this repository plans by area, but this git checkout has no base commit to compare "
                "against, so whether a program took a new slice, or a new program was added, could not "
                "be checked — fetch the base branch and run the check again",
                line=1,
                hint="Fetch the base branch (for example `git fetch origin main`) and run the check again.",
            )
        else:
            run.note(
                regs.slice_register,
                1,
                "this repository plans by area, and there is no git repository to compare against, so "
                "whether a program took a new slice, or a new program was added, was not checked",
                hint="Run the check in a git checkout with the base branch fetched.",
            )
    slice_ids = {s["id"] for s in slices}
    # Untouched rows with no area under `require_area`: failed below, once liveness is known.
    owe_area: list[tuple[dict[str, Any], Path, str]] = []
    for s in slices:
        where = run.row_where(s)
        rs = run.row_path(s, slr)
        run.check_disposition(
            slr,
            s,
            header_has_column=sl_has_disp,
            id_re=cfg.re_slice_id(),
            ids=slice_ids,
            shape=cfg.slice_id_shape,
            kind=corpusref.SLICE,
        )
        # NO status column, NO dates — completion is computed from the member PRDs, and order
        # comes from `Depends on` rather than from dates set once at the cut and never reconciled.
        if not s["title"]:
            run.err(rs, f"{where} has no Name", line=s["line"])
        if s["kind"] not in cfg.slice_kinds:
            run.err(
                rs,
                f"{where} invalid kind `{s['kind']}` (allowed: {', '.join(sorted(cfg.slice_kinds))})",
                line=s["line"],
            )
        # The one sentence that makes "is it done?" checkable. It was an optional prose paragraph
        # until it became a column, which is to say it was skippable.
        if len(s["done"]) < cfg.done_when_min:
            run.err(
                rs,
                f"{where} `Done when` is {len(s['done'])} chars — state the completion condition "
                "as one checkable sentence, not a topic",
                line=s["line"],
                hint="Write the condition someone could check, not the topic the slice is about.",
            )
        # The structural edge: slice -> the components its work spans. A list, because a slice cut
        # by what ships together crosses whatever components that work touches. Optional.
        for comp in s["component"]:
            if comp not in component_ids:
                run.err(
                    rs,
                    f"{where} component `{comp}` does not resolve to a {Path(cfg.component_registry).name} entry",
                    line=s["line"],
                    hint="Register the component, or correct the id to one that exists.",
                    command=cfg.command("component_create"),
                )
        # THE HOME (2026-10-27, amended 2026-10-28, FLT-1280): every slice names a feature AREA; a PROGRAM
        # — the roll-up edge, authored HERE and nowhere else — is optional, legacy membership. A row naming
        # no area fails when this change wrote it, whatever the setting. An untouched row is only noted, so
        # landing the rule turned no build red — unless the repository asks for it (`require_area`), and then
        # only a LIVE slice fails: a finished or withdrawn one is history, never rewritten, so it can never
        # name an area and is never failed for lacking one. Liveness is `fleet planning migrate`'s own rule
        # (`planningmigrate.live_slice_ids`), decided after this loop because it reads the board.
        area = str(s.get("area") or "")
        if area and not areas:
            # A CORPUS WITH NO FEATURE MAPS YET (a fresh `fleet init`): the area is a name until its map is
            # written, so it is noted, never failed — a feature map needs a component registry, specs and
            # source paths a new repository does not have on its first day.
            run.note(
                rs,
                s["line"],
                f"{where} names area `{area}`, and this corpus has no feature maps yet to check it against",
                hint="Write the feature map for this area under the features directory when the product has one.",
            )
        elif area and area not in areas:
            known = ", ".join(sorted(areas))
            run.err(
                rs,
                f"{where} area `{area}` is not a feature area of this corpus (known: {known})",
                line=s["line"],
                hint="Name the `area:` of a feature map under the features directory, or write that map.",
            )
        elif not area and not s["program"]:
            run.err(
                rs,
                f"{where} names no area — every slice lives under a feature area (`area`)",
                line=s["line"],
                hint="Name the feature area this cut belongs to.",
            )
        elif not area and base.written_here(s, rs):
            run.err(
                rs,
                f"{where} names no area — every new or changed slice names the feature area it belongs to",
                line=s["line"],
                hint="Add `area` (a feature map's slug) beside its program.",
            )
        elif not area and cfg.require_area:
            owe_area.append((s, rs, where))
        elif not area:
            run.note(
                rs,
                s["line"],
                f"{where} needs an area — name the feature area it belongs to",
                hint="Add `area` (a feature map's slug); `fleet planning migrate` proposes one for every live slice.",
            )
        if s["program"] and cfg.mode == AREAS and base.available:
            # STEP 4 (FLT-1282): in `areas` mode a program finishes the slices it holds and takes no new one —
            # a slice may name only the program it already named on the base commit.
            before = base.program_at_base(s, rs)
            # NO SAME-CHANGE EXEMPTION (owner, 2026-10-28, FLT-1285): a program this same change creates is refused
            # on its own row above, and a slice joining it is refused here too. The two reasons #2806 kept the
            # exemption are void — route proposes no program in this mode, and `fleet init` has written none in it
            # since #2815 (a setup pull request opened before that is accepted collateral).
            if before != s["program"]:
                run.err(
                    rs,
                    f"{where} joins program `{s['program']}`, but this repository plans by area "
                    '(`.fleet/fleet.toml` `[fleet.planning] mode = "areas"`), so programs take no new slices',
                    line=s["line"],
                    hint="Drop `program` and keep the slice under its area.",
                )
        if not s["program"]:
            pass  # an area-only slice: no program edge to resolve
        elif (home := run.corpora.localize(s["program"])) is None:
            # A cut that rolls up to ANOTHER corpus's program (`fleet:PG-047`): resolved there.
            res = run.corpora.resolve(s["program"], corpusref.PROGRAM, where=f"{rel(rs, run.root)} {s['id']}")
            if res.is_error:
                run.err(
                    rs,
                    f"{where} program {res.message}",
                    line=s["line"],
                    hint="Correct the qualified program id, or declare its corpus.",
                )
        elif home not in program_ids:
            run.err(
                rs,
                f"{where} program `{s['program']}` does not resolve to a {rel(pgr, run.root)} row",
                line=s["line"],
                hint="Correct the program id, or author the program row it should roll up to.",
            )
        else:
            slices_by_program.setdefault(home, []).append(s["id"])
        # A qualified edge (`fleet:SL-139`) is an opaque external node to the cycle check: no
        # cycle through this register can pass through a slice another corpus holds.
        slice_graph[s["id"]] = [sid for raw in s["depends_on"] if (sid := run.corpora.localize(raw)) is not None]
    run.check_supersession_graph(slr, slices)

    # `require_area` covers LIVE slices only. A finished or withdrawn one is left alone, without even a note:
    # nothing will ever give it an area, so a reminder would be one nobody can act on.
    live_ids = _live_slice_ids(kb) if owe_area else frozenset()
    for s, rs, where in owe_area:
        if live_ids is None or s["id"] in live_ids:
            run.err(
                rs,
                f"{where} names no area — this repository requires every live slice to name its feature area "
                "(`[fleet.planning] require_area = true`)",
                line=s["line"],
                hint="Add `area` (a feature map's slug); `fleet planning migrate` proposes one for every live slice.",
            )

    for s in slices:
        for raw_dep in s["depends_on"]:
            dep = run.corpora.localize(raw_dep)
            if dep is None:
                res = run.corpora.resolve(
                    raw_dep, corpusref.SLICE, where=f"{rel(run.row_path(s, slr), run.root)} {s['id']}"
                )
                if res.is_error:
                    run.err(
                        run.row_path(s, slr),
                        f"{run.row_where(s)} depends_on {res.message}",
                        line=s["line"],
                        hint="Correct the qualified slice id, or declare its corpus.",
                    )
                continue
            if dep not in slice_ids:
                run.err(
                    run.row_path(s, slr),
                    f"{run.row_where(s)} depends_on `{dep}` does not resolve to a slice id",
                    line=s["line"],
                    hint="Correct the id, or author the slice the edge points at.",
                )
    if scyc := find_cycle(slice_graph):
        run.bare(
            f"slice dependency cycle: {' -> '.join(scyc)}",
            path=slr,
            hint="Break the cycle — order comes from this graph, and a cycle makes it unorderable.",
        )

    run.check_detail_files(regs.program_detail_dir, program_ids, "program-detail")
    run.check_detail_files(regs.slice_detail_dir, slice_ids, "slice-detail")

    # --- prds ---
    seen_num: dict[str, str] = {}
    prd_deps: dict[str, tuple[Path, str | None, list[str]]] = {}
    prd_status: dict[str, str] = {}
    prd_graph: dict[str, list[str]] = {}
    for folder, (f, fm) in prds.items():
        for req in ("prd", "title", "status", "slice"):
            if not field(fm, req):
                run.err(f, f"missing required field `{req}`")
        run.check_status_history(f, fm)
        num = field(fm, "prd")
        st = field(fm, "status")
        raw_slice = field(fm, "slice")
        # A PRD whose cut lives in ANOTHER corpus (`slice: acme:SL-302` — a PRD that moved repos
        # but still ships inside the cut it was planned in): resolved there, and it rolls up to
        # nothing in this register. An own-qualified one is the local slice.
        sl = run.corpora.localize(raw_slice) if raw_slice else raw_slice
        if raw_slice and sl is None and st not in cfg.prd_terminal:
            res = run.corpora.resolve(raw_slice, corpusref.SLICE, where=rel(f, run.root))
            if res.is_error:
                run.err(
                    f,
                    f"slice {res.message}",
                    hint="Correct the qualified slice, or declare its corpus.",
                )
        # 0158 / ENG-13263: a PRD may name the lane whose repository its whole build lives in,
        # INSTEAD OF the corpus default. The field is optional and absent on every PRD that is
        # built in its corpus's own lane; when present it must name a REGISTERED lane, checked
        # here against `[fleet.planning] lanes`, and refused BY NAME otherwise — never a silent
        # fall back to the default, which would dispatch the work into the wrong repository.
        lane = field(fm, "lane")
        if lane and lane not in cfg.lanes:
            registered = ", ".join(sorted(cfg.lanes)) or "none"
            run.err(
                f,
                f"lane `{lane}` names no registered lane (registered: {registered}) — register it "
                "in the fleet service's lane table (module `fleet_service.dispatch.lanes`) and "
                "list it in `[fleet.planning] lanes` here, or "
                "correct the PRD's `lane:`",
                hint="Name a lane this corpus registers, or delete the `lane:` field.",
            )
        if st and st not in cfg.prd_statuses:
            run.err(f, f"invalid status `{st}` (allowed: {', '.join(sorted(cfg.prd_statuses))})")
        if num and not folder.startswith(num):
            run.err(f, f"prd `{num}` does not match folder `{folder}`")
        if st == "cancelled" and not field(fm, "cancelled_reason"):
            run.err(f, "status `cancelled` requires `cancelled_reason:`")
        if num:
            if num in seen_num:
                run.err(
                    f,
                    f"duplicate prd number `{num}` (also {seen_num[num]})",
                    hint="Renumber this PRD — a captured number silently inherits another's identity.",
                    command=cfg.command("allocate_ids", prefix="PRD"),
                )
            seen_num[num] = folder
            prd_nums.add(num)
        deps = listfield(fm, "depends_on")
        prd_deps[folder] = (f, st, deps)
        if num:
            prd_status[num] = st or ""
            # A qualified dependency (`fleet:0899`) is an opaque external node: it never enters
            # this corpus's PRD graph, so it can neither close a cycle nor be mistaken for 0899 here.
            prd_graph[num] = [
                norm_prd(local) for raw in prd_numbers(deps) if (local := run.corpora.localize(raw)) is not None
            ]
            if sl:
                prds_by_slice.setdefault(sl, []).append((num, st or ""))
        # the roll-up edge: PRD -> slice (-> program, checked above).
        # HISTORY MAY DANGLE; LIVE MUST RESOLVE: a terminal PRD keeps its original `slice:` as an
        # inert historical pointer even after that slice stopped existing. Only a live PRD needs a
        # real home, and a live one must name it by id.
        if sl and sl not in slice_ids and st not in cfg.prd_terminal:
            run.err(
                f,
                f"slice `{sl}` does not resolve to a {rel(slr, run.root)} row (expected an `{cfg.slice_id_shape}` id)",
                hint="Point the PRD at the slice it ships inside, or cut the slice it belongs to.",
                command=cfg.command("slice_create"),
            )
        # priority: enum-checked whenever present; required across the committed band
        prio = field(fm, "priority")
        if prio and prio not in cfg.priorities:
            run.err(f, f"invalid priority `{prio}` (allowed: {', '.join(sorted(cfg.priorities))})")
        if st in cfg.priority_required and not prio:
            run.err(f, f"status `{st}` requires a `priority:` (one of {', '.join(sorted(cfg.priorities))})")
        # required body sections: a designed-or-later PRD carries the standard template
        if st in cfg.sections_required:
            body = read(f)
            for sec in cfg.required_prd_sections:
                if not re.search(rf"^#{{2,}}\s+.*{re.escape(sec)}", body, re.M):
                    run.err(
                        f,
                        f"status `{st}` requires a `## {sec}` section",
                        command=cfg.command("prd_create", prd=folder.split("-", 1)[0]),
                    )
        # canonical differentiator labels
        for lbl in listfield(fm, "labels"):
            m = DIFF_LABEL_RE.match(lbl)
            if m and (canon := cfg.canonical_differentiator_labels.get(m.group(1))) and lbl != canon:
                run.err(f, f"non-canonical differentiator label `{lbl}` — use `{canon}`")

    for _folder, (f, st, deps) in prd_deps.items():
        for dep in deps:
            dref = parse_ref(dep)
            if not run.corpora.is_local(dref):
                # Another corpus's PRD: resolved against that corpus's index, and — when it is on
                # disk — held to the same cancelled-dependency rule a local edge is.
                res = run.corpora.resolve(dref, corpusref.PRD, where=rel(f, run.root))
                if res.is_error:
                    run.err(f, f"depends_on {res.message}")
                elif res.record and st != "cancelled" and res.record.get("status") == "cancelled":
                    run.err(f, f"depends_on `{dep}` is a cancelled PRD (in corpus `{dref.corpus}`)")
                continue
            dep = dref.id
            if is_issue_key(dep):
                # A tracker issue (`ENG-16070`): a bug fix the PRD waits on. It is the driver's to gate on, not
                # a graph edge; the only thing to refuse is a key the tracker does not own (`GOV-150`).
                if dep.split("-", 1)[0] not in run.cfg.reserved_requirement_prefixes:
                    run.err(
                        f,
                        f"depends_on `{dep}` is not a tracker issue key (tracker prefixes: "
                        f"{', '.join(sorted(run.cfg.reserved_requirement_prefixes))})",
                        hint="A requirement id is cited by an acceptance criterion, never listed as a dependency.",
                    )
                continue
            dn = norm_prd(dep)
            if dn not in prd_nums:
                run.err(f, f"depends_on `{dep}` does not resolve to a PRD number")
            elif st != "cancelled" and prd_status.get(dn) == "cancelled":
                run.err(f, f"depends_on `{dep}` is a cancelled PRD")
    if cyc := find_cycle(prd_graph):
        run.bare(f"PRD dependency cycle: {' -> '.join(cyc)}", path=regs.prds_dir)

    # --- the work-in-progress ceiling ---
    # "Active" is DERIVED: a slice holding at least one live (non-terminal) PRD. Nothing
    # previously bounded work in progress, which is how 40 containers appeared, 33 of them with
    # every member PRD terminal and a `status:` that never caught up. The ceiling is what makes
    # the delivery view readable by construction and forces sequencing to be a decision rather
    # than an accident. Fatal, not advisory — a ceiling nobody enforces is the state this replaced.
    active = sorted(
        sid
        for sid, entries in prds_by_slice.items()
        if sid in slice_ids and any(ps not in cfg.prd_terminal for _n, ps in entries)
    )
    if len(active) > cfg.active_slice_ceiling:
        run.bare(
            f"{len(active)} slices hold a live PRD, ceiling is {cfg.active_slice_ceiling} — "
            f"finish or park work before starting more ({', '.join(active)})",
            path=slr,
            hint="Finish or park a cut before starting another — the ceiling forces sequencing to be a choice.",
        )

    # --- an all-terminal slice must resolve its proof ---
    # The ceiling above bounds WIP. This gate catches what the ceiling is blind to: a slice whose
    # member PRDs are ALL terminal but which names no `Verified by` can never read complete, and
    # nothing says so.
    needs_waiver = {
        s["id"]
        for s in slices
        if (entries := prds_by_slice.get(s["id"]))
        and all(ps in cfg.prd_terminal for _n, ps in entries)
        # A slice of ONLY cancelled PRDs is an abandoned cut, not done work — it needs no proof
        # and no waiver. The gate targets shipped-but-unproven work.
        and any(ps == "shipped" for _n, ps in entries)
        and not s["verified_by"]
        # A withdrawn cut needs neither: the decision record is its answer, and a waiver on top
        # of it would be two records saying the same thing in two grammars.
        and s["disposition"]["kind"] == ADOPTED
    }

    # THE SAME GATE ONE TIER UP. A program whose every slice is terminal — no live PRD anywhere
    # under it, at least one shipped — and which names no composed proof can never read
    # complete either, and until this rule nothing said so: six proof PRDs were manufactured
    # in five days to close programs whose real proof was an observation, and the ones that
    # were not closed that way sat `unproven` forever. A freshly authored program whose cuts
    # hold no PRDs yet is NOT here (nothing shipped, nothing to prove), and neither is one
    # whose every PRD was cancelled — the slice rule's own two carve-outs, for its reasons.
    def _members(pid: str) -> list[tuple[str, str]]:
        return [e for sid in slices_by_program.get(pid, ()) for e in prds_by_slice.get(sid, ())]

    # A program is DELIVERED only when every cut under it is terminal AND every adopted cut has
    # been authored. A cut with no member PRDs is the plan's next slice, cut before its PRDs are
    # written — work outstanding, and the program stays open until that cut too ships or is
    # withdrawn. Reading only authored PRDs made a program whose next PRDs are simply not cut yet
    # look finished the instant its last authored PRD shipped, and hard-failed the commit of that
    # PRD: an implementer, forbidden to make a program-scope decision (name a composed proof ·
    # waive · withdraw the row), was blocked by one (ENG-10259). A withdrawn or superseded cut is
    # out of the plan and owes nothing, so only `adopted` cuts count as outstanding.
    slice_by_id = {s["id"]: s for s in slices}

    def _has_uncut_slice(pid: str) -> bool:
        return any(
            not prds_by_slice.get(sid) and slice_by_id[sid]["disposition"]["kind"] == ADOPTED
            for sid in slices_by_program.get(pid, ())
        )

    program_needs_waiver = {
        p["id"]
        for p in programs
        if (entries := _members(p["id"]))
        and all(ps in cfg.prd_terminal for _n, ps in entries)
        and any(ps == "shipped" for _n, ps in entries)
        and not _has_uncut_slice(p["id"])
        and not p["verified_by"]
        and p["disposition"]["kind"] == ADOPTED
    }
    if write_baseline:
        path = write_program_proof_baseline(kb, program_needs_waiver)
        run.report.notes.append(f"__wrote__programs|{len(program_needs_waiver)}|{rel(path, run.root)}")
        program_waived = set(program_needs_waiver)
    else:
        program_waived = program_proof_baseline(kb)
    # The slice waiver is PER-ROW since ENG-12602: a reasoned `proof_waiver` string on the slice's
    # own fragment. There is no shared slice baseline to read (or regenerate) any more.
    waived = slice_proof_waivers(slices)
    for s in [] if write_baseline else slices:
        if s["id"] not in needs_waiver or s["id"] in waived:
            continue
        run.err(
            run.row_path(s, slr),
            f"{run.row_where(s)} has every member PRD terminal but names no "
            "`Verified by` and carries no `proof_waiver` — it can never read complete. Name "
            "the proof that shows the cut does what it said, or record a reasoned "
            "`proof_waiver` on this slice's own row fragment (ENG-12602)",
            line=s["line"],
            hint="Name the PRD that proves this cut did what it said, or record a reasoned per-row waiver.",
        )
    # EVERY WAIVER STATES ITS KIND (2026-10-07), and a deferred one what it owes. No default: an
    # excused waiver settles its cut and lets the program close, a deferred one holds both open, and
    # a waiver nobody classified must not be read as either by a guess. Read off the row itself
    # (`registers.waiver_problem`), never through `slice_proof_waivers`, which a binding may narrow.
    for s in [] if write_baseline else slices:
        if not str(s.get("proof_waiver", "")).strip():
            continue
        problem = waiver_problem(
            str(s.get("proof_waiver_kind") or ""),
            str(s.get("proof_waiver_owed") or ""),
            str(s.get("proof_waiver_needs") or ""),
        )
        if problem:
            run.err(
                run.row_path(s, slr),
                f"{run.row_where(s)}'s `proof_waiver` {problem}. Write it as "
                '`{"kind": "excused", "reason": ...}` when no proof is needed, or '
                '`{"kind": "deferred", "owed": ..., "reason": ...}` when the proof is still owed '
                '(adding `"needs": "production"` when only a check against production can take it) — '
                "only an excused waiver settles the cut",
                line=s["line"],
                hint="Say whether the proof is excused or deferred; a deferred one names what is owed.",
            )
    # A per-row waiver that no longer needs one should be removed — the gate is absolute.
    for sid in [] if write_baseline else sorted(waived):
        if sid in needs_waiver:
            continue
        s = next(x for x in slices if x["id"] == sid)
        run.note(
            run.row_path(s, slr),
            s["line"],
            f"`{sid}` carries a `proof_waiver` but no longer needs it (it now has a "
            "`Verified by`, a live PRD, or no shipped PRDs) — remove the `proof_waiver` from "
            "its fragment so the record stops excusing settled work (ENG-12602)",
            hint="Remove the marker — a waiver that excuses nothing is stale.",
        )
    program_baseline_rel = rel(program_proof_baseline_path(kb), run.root)
    for p in [] if write_baseline else programs:
        if p["id"] not in program_needs_waiver or p["id"] in program_waived:
            continue
        # The program-tier proof rule arrived with the `Disposition` axis and binds where the
        # axis has been adopted — a register that still predates the column (the migration
        # window `check_register_shape` names) gets the same finding as an advisory, so the
        # debt is visible on every run and gates nothing until the migration lands.
        msg = (
            f"{run.row_where(p)} has no slice in flight and work shipped under it, but "
            "names no `Verified by` and is not waived — it can never read complete. Name the "
            "composed proof (a PRD, or `drill:<stem>` for the record of the observation that "
            f"proves it), record an explicit waiver in `{program_baseline_rel}`, or withdraw the "
            "row citing a decision record (ENG-8096)"
        )
        hint = "Name the composed proof — a PRD or a drill record — or record a deliberate waiver."
        command = cfg.command("write_program_proof_baseline")
        if pg_has_disp:
            run.err(run.row_path(p, pgr), msg, line=p["line"], hint=hint, command=command)
        else:
            run.note(run.row_path(p, pgr), p["line"], msg, hint=hint, command=command)
    program_kinds = {} if write_baseline else program_proof_baseline_kinds(kb)
    for pid in sorted(program_kinds):
        problem = waiver_problem(*program_kinds[pid])
        if problem:
            run.err(
                pgr,
                f"`{pid}`'s line in `{program_baseline_rel}` {problem}. Write `{pid} excused` when no "
                f"composed proof is needed, or `{pid} deferred: <what is owed>` when it is still owed — "
                "only an excused waiver settles the program",
                hint="State the waiver's kind on its id line.",
            )
    for pid in [] if write_baseline else sorted(program_waived):
        if pid not in program_ids:
            run.err(
                pgr,
                f"`{pid}` is waived in `{program_baseline_rel}` but is not a "
                "row in the register — a waiver that names no program weakens the gate",
                hint="Delete the stale line, or correct it to the program id it meant.",
            )
    for pid in [] if write_baseline else sorted(program_waived & program_ids):
        if pid in program_needs_waiver:
            continue
        p = next(x for x in programs if x["id"] == pid)
        run.note(
            run.row_path(p, pgr),
            p["line"],
            f"`{pid}` is in the "
            "proof-waiver baseline but no longer needs it (it now has a `Verified by`, a live "
            "PRD under it, no shipped work, or is withdrawn) — remove the line so the baseline "
            "shrinks (ENG-8096)",
            hint="Remove the line — the baseline may shrink, never grow.",
        )

    # --- a withdrawn container may not hold live work ---
    # The register said stop; a live PRD under it says the work did not. One of the two is
    # wrong, and a board that showed the decision would hide the PRD while one that showed the
    # PRD would argue with the decision — so neither is shown until the corpus agrees with
    # itself. The fix is the PRD's: cancel it (`cancelled_reason` can cite the same record), or
    # move it to a cut that is still in the plan.
    for s in slices:
        if s["disposition"]["kind"] == ADOPTED:
            continue
        live = sorted(n for n, ps in prds_by_slice.get(s["id"], ()) if ps not in cfg.prd_terminal)
        if live:
            run.err(
                run.row_path(s, slr),
                f"{run.row_where(s)} is {s['disposition']['kind']} but still holds live work "
                f"({', '.join(live)}) — a withdrawn cut cannot have PRDs in flight. Cancel them, "
                "citing the same decision record, or move them to a cut that is still in the plan",
                line=s["line"],
                hint="Cancel the live PRDs (citing the decision record) or re-home them; the register said stop.",
            )

    def _cut_is_live(sid: str) -> bool:
        """A slice is live while it is adopted and not every one of its PRDs is terminal.

        A cut with NO PRDs is live too: it is the plan's next cut, authored before its PRDs are
        written (`_has_uncut_slice` counts it the same way one tier down). Reading liveness
        through `_members` alone made such a cut invisible, and a `--close-programs` migration
        merged after the cut never moved it (BUG-3032).
        """
        entries = prds_by_slice.get(sid, ())
        return slice_by_id[sid]["disposition"]["kind"] == ADOPTED and (
            not entries or any(ps not in cfg.prd_terminal for _n, ps in entries)
        )

    for p in programs:
        if p["disposition"]["kind"] == ADOPTED:
            continue
        live = sorted(n for n, ps in _members(p["id"]) if ps not in cfg.prd_terminal)
        live_cuts = sorted(sid for sid in slices_by_program.get(p["id"], ()) if _cut_is_live(sid))
        if not live and not live_cuts:
            continue
        holds = (
            f"its slices still hold live work ({', '.join(live)})"
            if live
            else f"its live cuts still name it ({', '.join(live_cuts)})"
        )
        run.err(
            run.row_path(p, pgr),
            f"{run.row_where(p)} is {p['disposition']['kind']} but {holds} — a withdrawn "
            "program cannot have live work under it. "
            + (
                "It closed into feature areas, so its live cuts leave it: drop each one's `program` "
                "(keep it as `from_program`) and name its `area` — `fleet planning migrate --close-programs` "
                "does both"
                if p["disposition"].get("ref") == AREAS_SUCCESSOR
                else "Cancel them, citing the same decision record, or move their cuts to a program "
                "that is still in the plan"
            ),
            line=p["line"],
            hint="Cancel the live PRDs (citing the decision record) or re-home their cuts; the register said stop.",
        )

    # --- the two tiers must order the same pair of cuts the same way (ENG-10142 / ENG-10184) ---
    #
    # Two graphs, two tiers, one ORDER. The slice register's `Depends on` says which cut comes
    # first — it ranks work (`board.ranks` pulls a prerequisite up behind an urgent dependent) and
    # the board draws it — and each PRD's own `depends_on:` is the only thing the dispatcher
    # actually waits on (`scheduler.compute_plan`). **A slice edge never withholds dispatch**
    # (ENG-10638), so a disagreement here is no longer a deadlock; it is an order that points the
    # wrong way, which ranks a cut's prerequisite behind the work that needs it and draws a
    # dependency the PRDs contradict. That is still wrong data, so it still fails:
    #
    #   slice A depends_on slice B  +  a live *capability* PRD m on B depends_on a live PRD x on A
    #
    # The register says A comes after B; the PRDs say B's own work comes after A's.
    #
    # **ENG-10184 exemption.** A program's composed proof (`Verified by`) sitting as a member of
    # B is *not* part of B's capability ground — it is the demonstration that the ground holds.
    # Dependents of B do not wait on it, so a proof PRD's `depends_on` back into A is harness
    # reuse (0588 → 0590), not sequencing. Walking from that PRD would flag a false cycle and
    # force one of two deliberate edges to be dropped. Skip composed proofs when seeding the
    # walk from the far side.
    #
    # Each tier is separately acyclic — `find_cycle` above clears both — so nothing else catches
    # this. The check walks the PRD graph from each live *ground* PRD on the far side of a slice
    # edge and fails when the walk reaches a live PRD on the near side. Transitive on purpose.
    #
    # Scoped to LIVE PRDs on both ends. THE FIX for a real (capability) conflict is one of the
    # two edges — never a gate. A composed-proof back-edge is not a conflict under ENG-10184.
    program_proofs: dict[str, set[str]] = {p["id"]: {norm_prd(x) for x in p.get("verified_by") or []} for p in programs}
    slice_program = {s["id"]: s["program"] for s in slices}
    live_on: dict[str, list[str]] = {}
    slice_of_live: dict[str, str] = {}
    for sid, entries in prds_by_slice.items():
        if sid not in slice_ids:
            continue  # a dangling slice pointer is its own finding; this gate reads the real graph
        for num, ps in entries:
            if ps not in cfg.prd_terminal:
                live_on.setdefault(sid, []).append(num)
                slice_of_live[num] = sid
    live_edges: dict[str, list[str]] = {
        num: [d for d in prd_graph.get(num, ()) if prd_status.get(d, "") not in cfg.prd_terminal]
        for num in slice_of_live
    }

    def _live_reachable(start: str) -> set[str]:
        seen: set[str] = set()
        frontier = list(live_edges.get(start, ()))
        while frontier:
            cur = frontier.pop()
            if cur in seen:
                continue
            seen.add(cur)
            frontier.extend(live_edges.get(cur, ()))
        return seen

    for s in slices:
        if not live_on.get(s["id"]):
            continue
        for dep in s["depends_on"]:
            if dep == s["id"] or dep not in slice_ids:
                continue  # a self-loop or a dangling edge is the cycle/resolution check's finding
            far_proofs = program_proofs.get(slice_program.get(dep, ""), set())
            against: list[str] = []
            for far in live_on.get(dep, ()):
                if far in far_proofs:
                    # Composed proof on the prerequisite cut: its depends_on is harness-reuse
                    # (ENG-10184), not a sequencing edge that holds dependents of this cut.
                    continue
                hits = sorted(n for n in _live_reachable(far) if slice_of_live.get(n) == s["id"])
                if hits:
                    against.append(f"{far} -> {', '.join(hits)}")
            if against:
                run.err(
                    slr,
                    f"line {s['line']}: `{s['id']}` depends on `{dep}`, but `{dep}`'s live PRD "
                    f"{'; '.join(against)} sit{'s' if len(against) == 1 else ''} on `{s['id']}` itself — "
                    "the slice register and the PRD `depends_on` graphs order these two cuts in opposite "
                    f"directions: the register puts `{s['id']}` after `{dep}`, while `{dep}`'s own "
                    f"capability work waits on `{s['id']}` (ENG-10142)",
                    line=s["line"],
                    hint=(
                        f"Fix one of the two edges so both tiers agree on the order: repoint or drop "
                        f"`{s['id']}` -> `{dep}` in this register, or correct the PRD `depends_on` "
                        f"listing the cross-edge. A composed-proof PRD's depends_on (the parent "
                        f"program's Verified by) is harness-reuse and is not this finding (ENG-10184)."
                    ),
                    command=cfg.command("slice_edit", slice=s["id"]),
                )

    # A slice adds a completion condition its PRDs do not have; one PRD is a PRD. Advisory, never
    # fatal — a live PRD must name a slice, so a genuinely standalone one still needs a home until
    # the next planning cut merges it with what ships beside it. Printed so it cannot sit unnoticed.
    for s in slices:
        live = [n for n, ps in prds_by_slice.get(s["id"], []) if ps not in cfg.prd_terminal]
        if live and len(prds_by_slice.get(s["id"], ())) == 1:
            run.note(
                slr,
                s["line"],
                f"{s['id']} holds 1 PRD — a slice is >=2 that ship together",
                hint="Merge it with what ships beside it at the next planning cut.",
                command=cfg.command("slice_create"),
            )

    # A program spans SEVERAL slices toward one result; one slice is a slice and does not earn a
    # program. Advisory, not fatal — a freshly authored program legitimately holds nothing until
    # the decompose pass cuts its slices, and failing the commit would make authoring one impossible.
    for p in programs:
        # A program out of the plan takes no more cuts, so its size is history, not advice.
        if len(slices_by_program.get(p["id"], ())) == 1 and p["disposition"]["kind"] == ADOPTED:
            run.note(
                pgr,
                p["line"],
                f"{p['id']} holds 1 slice — a program is >=2",
                hint="Cut the rest of the program's slices, or fold this one into a neighbouring program.",
                command=cfg.command("slice_create"),
            )

    # A proof pointer must exist. `Verified by` names the e2e PRD(s) that drive a customer surface,
    # or the drill record(s) of the observation that proves the thing; whether they have SHIPPED
    # (or passed) is the derived completion reading, not a stored one, so all that is checkable
    # here is that the pointer resolves — and, for a drill, that what it resolves to is a record.
    drill_records = regs.drills()
    drills_rel = rel(regs.drills_dir, run.root)

    def _check_proofs(path: Path, row: dict[str, Any]) -> None:
        for entry in row["verified_by"]:
            where = f"line {row['line']}: `{row['id']}` verified_by"
            if not is_drill(entry):
                pref = parse_ref(entry)
                if not run.corpora.is_local(pref):
                    # A composed proof another corpus holds (`fleet:0899`): resolved there.
                    res = run.corpora.resolve(pref, corpusref.PRD, where=f"{rel(path, run.root)} {row['id']}")
                    if res.is_error:
                        run.err(
                            path,
                            f"{where} {res.message}",
                            line=row["line"],
                            hint="Correct the qualified PRD, or declare its corpus.",
                        )
                    continue
                num = norm_prd(pref.id)
                if num not in prd_nums:
                    run.err(
                        path,
                        f"{where} `{num}` does not resolve to a PRD",
                        line=row["line"],
                        hint="Point at a PRD that exists, or clear the cell — an empty cell reads `unproven`.",
                    )
                continue
            stem = drill_stem(entry)
            record = drill_records.get(stem)
            if record is None:
                run.err(
                    path,
                    f"{where} `drill:{stem}` names no file — `{drills_rel}/{stem}.md` does not exist",
                    line=row["line"],
                    hint="Commit the drill record the harness produced, or correct the stem.",
                )
            elif str(record.get("type", "")) != DRILL_RECORD_TYPE:
                run.err(
                    path,
                    f"{where} `drill:{stem}` is not a drill record — `{drills_rel}/{stem}.md` has "
                    f"`type: {record.get('type', '') or '(none)'}`, not `type: {DRILL_RECORD_TYPE}`",
                    line=row["line"],
                    hint="Only a harness-produced `type: drill-record` file is evidence; a note about a drill is not.",
                )
            elif not str(record.get("verdict", "")).strip():
                run.err(
                    path,
                    f"{where} `drill:{stem}` carries no `verdict:` — a record with no verdict proves nothing "
                    "either way",
                    line=row["line"],
                    hint="A drill record's frontmatter says `verdict: passed` or `verdict: failed`; this says neither.",
                )

    for p in programs:
        _check_proofs(pgr, p)
    for s in slices:
        _check_proofs(slr, s)

    run.check_status_copies()
    run.check_proof_disjointness(programs, slices)

    # Never a silent pass: a reference into a declared corpus that is not on disk here is
    # counted and named, once.
    if unverified := run.corpora.summary():
        run.report.notes.append(f"note: {unverified}")
        run.report.findings.append(finding(ADVISORY, unverified))

    run.report.notes.append(
        f"__summary__{len(programs)}|{len(slices)}|{len(prds)}|{len(active)}|{cfg.active_slice_ceiling}"
    )
    return run.report


class TrackingMetadataCheck:
    """Every PRD rolls up to a slice and every slice to a program, and each tier is well-formed."""

    name = NAME
    title = "Tracking metadata"
    description = (
        "The planning ladder is only useful if it is connected: every PRD names a slice, every slice names "
        "a program, and no id in either register is malformed, duplicated or ahead of its append-only "
        "counter. This check enforces that graph — resolution, acyclicity, the exact register column shape "
        "(so a deleted column cannot come back and a `Status` column above the PRD tier is refused outright), "
        "a work-in-progress ceiling on slices holding live PRDs, and the rule that a program's proof may "
        "never BE one of its slices' proofs. It also fires where the ladder rots quietly: a slice or a "
        "program whose every PRD is terminal but which names no proof can never read complete, so it must "
        "name one — a PRD, or the drill record of the observation that proves it — record a deliberate "
        "waiver, or be withdrawn by a `Disposition` citing a decision record. `Disposition` is the second "
        "axis both registers carry: a decision, never a ship-state, and a word claiming one is refused."
    )

    def applies(self, kb: Any) -> bool:
        # `kb.has` is the spine's predicate and the one that reads an option set to "" as
        # "this corpus does not have that" — a plain path check would resolve "" to the
        # corpus directory itself and answer yes.
        return any(kb.has(opt) for opt in ("programs_register", "slices_register", "prds_dir"))

    def run(self, kb: Any) -> list[Any]:
        return analyse(kb).findings


CHECK = TrackingMetadataCheck()


def cli(kb: Any, *, write_baseline: bool = False) -> int:
    """Reproduce `scripts/validate_tracking_metadata.py`'s stdout and exit code exactly.

    The one intentional difference from the original is documented in this module's docstring:
    the `implementing`-staleness advisory computed a duration, and this package emits none.
    """
    report = analyse(kb, write_baseline=write_baseline)

    summary = ""
    for note in report.notes:
        if note.startswith("__summary__"):
            summary = note[len("__summary__") :]
            continue
        if note.startswith("__wrote__"):
            noun, count, path = note[len("__wrote__") :].split("|", 2)
            print(f"wrote {count} {noun} to {path}")
            continue
        print(note)

    if report.error_lines:
        print("tracking metadata validation failed:")
        for line in report.error_lines:
            print(f"- {line}")
        return 1
    n_programs, n_slices, n_prds, n_active, ceiling = summary.split("|")
    print(
        f"tracking metadata OK — {n_programs} programs, {n_slices} slices, "
        f"{n_prds} PRDs; all roll up to a program; {n_active}/{ceiling} "
        "slices active"
    )
    return 0
