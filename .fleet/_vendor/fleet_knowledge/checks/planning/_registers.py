"""The ONE reader for the program and slice registers.

A program is a ROW in the program register, a slice is a row in the slice register, and the
prose that survives the cut lives in an OPTIONAL detail file named for the row's id
(`programs/PG-21.md`, `slices/SL-137.md`). **The filename IS the join** — there is no `slug:`,
and a detail file carries no structure at all.

**Why a register rather than a folder per entity.** The folders stored, per entity, a
frontmatter block only the validators read plus a child list that duplicated an edge already
authored on the child — so keeping a program's list equal to the set of slices naming it
needed a validator whose whole job was reconciling one fact stored twice. A register makes
the fact singular: the slice row names its program, and nothing else does.

**Ids are permanent and never reused.** Each register carries an `APPEND ONLY. Next id:`
counter, which is what makes `SL-137` safe to cite from a PRD that shipped a year ago.

Nothing here carries a `status:`. A slice's and a program's completion is COMPUTED from
their member PRDs and their proof; only the PRD tier authors ship-state.

Every row is read POSITIONALLY, so a column dropped from a register without updating
`PlanningConfig.program_columns` / `slice_columns` silently shifts every field after it —
which is exactly why the shape check in `tracking_metadata` is an EXACT header comparison.

**Both tiers carry a second axis, `Disposition`, and it is the LAST column** — `adopted`,
`withdrawn: <decision record>` or `superseded by <successor>`. A decision about what happened
to the container, never a ship-state; the grammar is `fleet_knowledge.registers.disposition`'s
and is not restated here. Last, so a register from before the column pads rather than shifts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fleet_knowledge.planningmode import feature_areas, split_home_cell
from fleet_knowledge.registers import (
    ROWS_SUBDIR,
    disposition,
    drills,
    fragments,
    localize_rows,
    program_row_from_fragment,
    slice_row_from_fragment,
)

from ._config import PlanningConfig
from ._markdown import as_list, cells, scalar


@dataclass(frozen=True)
class Registers:
    """The two registers of one knowledge base, resolved against its config."""

    knowledge: Path
    cfg: PlanningConfig

    # --- paths ---

    @property
    def program_register(self) -> Path:
        return self.knowledge / self.cfg.program_register

    @property
    def slice_register(self) -> Path:
        return self.knowledge / self.cfg.slice_register

    @property
    def program_detail_dir(self) -> Path:
        return self.knowledge / self.cfg.program_detail_dir

    @property
    def slice_detail_dir(self) -> Path:
        return self.knowledge / self.cfg.slice_detail_dir

    @property
    def program_rows_dir(self) -> Path:
        """Where `PG-NN`'s row fragment lives — `<programs_detail_dir>/rows`. May not exist."""
        return self.program_detail_dir / ROWS_SUBDIR

    @property
    def slice_rows_dir(self) -> Path:
        """Where `SL-NNN`'s row fragment lives — `<slices_detail_dir>/rows`. May not exist."""
        return self.slice_detail_dir / ROWS_SUBDIR

    @property
    def prds_dir(self) -> Path:
        return self.knowledge / self.cfg.prds_dir

    @property
    def drills_dir(self) -> Path:
        return self.knowledge / self.cfg.drills_dir

    @property
    def program_proof_baseline(self) -> Path:
        return self.knowledge / self.cfg.program_proof_baseline

    def program_detail(self, pid: str) -> Path:
        """Where `PG-21`'s prose lives — whether or not the file exists."""
        return self.program_detail_dir / f"{pid}.md"

    def slice_detail(self, sid: str) -> Path:
        """Where `SL-137`'s prose lives — whether or not the file exists."""
        return self.slice_detail_dir / f"{sid}.md"

    # --- rows ---

    def programs(self) -> list[dict[str, Any]]:
        """Every program row, in register order.

        Columns: `ID | Name | Kind | Verified by | Requires | Disposition`.

        `verified_by` is the composed thread ACROSS this program's slices — *"do these work
        together for a person?"*. It is the ONLY authored input to the completion derivation
        and the completion condition this tier adds to its slices'. An entry is a PRD number
        or `drill:<stem>`. `requires` names the ROOTS of the decomposition, not child edges: a
        program's children are its slices, and that edge is authored on the slice.
        `disposition` is the decision axis, parsed; `disposition_cell` is the raw cell, which
        is what the gate refuses off-grammar values from.

        **Fragments win when present.** A corpus that keeps `<programs_detail_dir>/rows/<ID>.json`
        reads its rows from there and never opens the committed table, which is a generated
        projection of those fragments. A corpus that has not migrated has no such directory and
        reads its table exactly as before.
        """
        frags = fragments(self.knowledge, self.cfg.program_detail_dir, self.cfg.re_program_id())
        if frags:
            return localize_rows(
                [program_row_from_fragment(pid, data, src) for pid, data, src in frags], self.cfg.corpus
            )
        out: list[dict[str, Any]] = []
        width = len(self.cfg.program_columns)
        for c, line in _rows(self.program_register, self.cfg.re_program_id(), width):
            out.append(
                {
                    "id": c[0],
                    "title": scalar(c[1]),
                    "kind": scalar(c[2]),
                    "verified_by": as_list(c[3]),
                    "requires": as_list(c[4]),
                    "disposition": disposition(c[5]),
                    "disposition_cell": c[5].strip(),
                    "line": line,
                }
            )
        return localize_rows(out, self.cfg.corpus)

    def slices(self) -> list[dict[str, Any]]:
        """Every slice row, in register order.

        Columns: `ID | Name | Kind | Program | Done when | Verified by | Depends on |
        Components | Disposition`.

        `program` is the roll-up edge, authored HERE and nowhere else. `done` is the
        completion condition in one checkable sentence — a column precisely so it cannot be
        skipped. `verified_by` is the slice's OWN proof and is OPTIONAL: absent is the honest
        *unproven* reading, and a guessed proof is worse than none. `disposition` and
        `disposition_cell` are as on the program row.

        **Fragments win when present**, as on `programs`.
        """
        frags = fragments(self.knowledge, self.cfg.slice_detail_dir, self.cfg.re_slice_id())
        if frags:
            return localize_rows([slice_row_from_fragment(sid, data, src) for sid, data, src in frags], self.cfg.corpus)
        out: list[dict[str, Any]] = []
        width = len(self.cfg.slice_columns)
        for c, line in _rows(self.slice_register, self.cfg.re_slice_id(), width):
            # An area slice writes `area:<slug>` into the `Program` cell, so no column moves (FLT-1280).
            program, area = split_home_cell(scalar(c[3]))
            out.append(
                {
                    "id": c[0],
                    "title": scalar(c[1]),
                    "kind": scalar(c[2]),
                    "program": program,
                    "area": area,
                    "done": scalar(c[4]),
                    "verified_by": as_list(c[5]),
                    "depends_on": as_list(c[6]),
                    "component": as_list(c[7]),
                    "disposition": disposition(c[8]),
                    "disposition_cell": c[8].strip(),
                    "line": line,
                }
            )
        return localize_rows(out, self.cfg.corpus)

    def drills(self) -> dict[str, dict[str, Any]]:
        """Every drill record's frontmatter, by stem — `fleet_knowledge.registers.drills`.

        The package's reader and not a second one, so what the gate calls a drill record and
        what the board resolves a `drill:` proof against are one reading.
        """
        return drills(self.knowledge, self.cfg.drills_dir) if self.cfg.drills_dir else {}

    def feature_areas(self) -> dict[str, tuple[str, ...]]:
        """Every feature area of this corpus (`planningmode.feature_areas`) — what a slice's `area` resolves to."""
        return feature_areas(self.knowledge, self.cfg.features_dir)

    def component_ids(self) -> set[str]:
        """Registered component ids, from the component registry's `## Components` table.

        Shape is validated by the `components` check — this only needs the id column so a
        slice's `Components` cell can be resolved. A missing registry yields an empty set,
        because the cell is optional.
        """
        out: set[str] = set()
        reg = self.knowledge / self.cfg.component_registry
        if not reg.is_file():
            return out
        in_sec = False
        for line in reg.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("## "):
                in_sec = line.strip() == self.cfg.components_heading
                continue
            if not in_sec or not line.strip().startswith("|"):
                continue
            first = line.strip().strip("|").split("|")[0].strip()
            if first and first.lower() != "id" and set(first) - set("-: "):
                out.add(first)
        return out


def of(kb: Any) -> Registers:
    """The registers of `kb`."""
    return Registers(knowledge=Path(kb.knowledge), cfg=PlanningConfig.of(kb))


def _rows(path: Path, id_re: re.Pattern[str], columns: int) -> list[tuple[list[str], int]]:
    """Every table row whose first cell is a well-formed id, with its 1-based line number.

    Anything else in the file — prose, the header row, the `---|---` rule — is skipped, so a
    register can carry as much explanation above its table as it needs. Short rows are PADDED
    rather than dropped: a missing trailing cell is a validator's finding, not a reason for
    every other reader to lose the row.
    """
    if not path.is_file():
        return []
    out: list[tuple[list[str], int]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
        if not line.lstrip().startswith("|"):
            continue
        c = cells(line)
        if not c or not id_re.match(c[0]):
            continue
        c += [""] * (columns - len(c))
        out.append((c, i))
    return out
