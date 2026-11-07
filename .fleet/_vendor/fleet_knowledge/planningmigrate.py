"""`fleet planning migrate` — give every live slice its feature area, and optionally take the repository off
programs, by ONE pull request its owner reviews (Step 5 of the planning-without-programs design, FLT-1283).

Three jobs:

  1. **Area backfill**, always: every live slice with no `area` is given one.
  2. **Off programs**, only with `drop_programs`: every live slice's `program` is removed (a fragment keeps it
     as `from_program`, so the history stays on the row); with `flip` the repository's `[fleet.planning] mode`
     is set to `areas` too, and with `require_area` its `require_area = true`.
  3. **Close the programs**, only with `close_programs` (implies `drop_programs`; owner decision 2026-10-29):
     every program still open (`adopted`, not `complete` or `waived`) is marked `superseded by areas`, AFTER its
     live slices left it, so it withdraws nothing with it (`rollup.withdrawn_programs`). Each open PRD its
     `Verified by` names — the program's end-to-end check — becomes ONE area slice of its own, in the area it
     mostly touches: a new slice row (`from_program` names where it came from) that the PRD moves into, unless
     the PRD stays in its live slice, which then carries the check: when it is that slice's only PRD, when
     that slice names no proof of its own (it then names this PRD), or when the PRD's acceptance criteria are
     promoted from that slice's bar (`[ext → SL278-C1]`). A program that
     still holds a live slice the migration cannot place is not closed: closing it would withdraw that slice.

**Which slices.** Live: disposition `adopted`, not finished (board state not `complete`, `waived`,
`abandoned` or `withdrawn`), and its program, if it names one, `adopted` and not finished. A withdrawn or
finished slice, any slice under a withdrawn or finished program, and every program row are never touched,
so every `PG-NN` keeps resolving.

**How an area is proposed**, strongest evidence first: (1) the `area:` its member PRDs agree on; (2) the one
feature map whose `components:` hold every component the slice names. Anything else is `CANNOT PLACE`, with
the candidates, and is left exactly as it is.

A dry run by default: `plan()` reads and decides, `apply()` writes. Stdlib only.
"""

from __future__ import annotations

import contextlib
import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import planningmode
from .markdown import field as fm_field
from .markdown import frontmatter, section
from .registers import AREAS_SUCCESSOR, closed_into_areas

#: A slice in one of these board states is finished or gone: the migration never touches it.
FINISHED_SLICE_STATES = frozenset({"complete", "waived", "abandoned", "withdrawn"})
#: A program in one of these board states takes no rewrite of its slices.
FINISHED_PROGRAM_STATES = frozenset({"complete", "waived", "withdrawn"})

#: A program's composed proof in one of these PRD statuses is finished history: it is never moved.
PRD_TERMINAL = frozenset({"shipped", "cancelled"})
#: The kind of slice a program's end-to-end check becomes: it composes what several cuts built.
PROOF_SLICE_KIND = "feature"

PLACED = "placed"
CANNOT_PLACE = "cannot-place"
UNCHANGED = "unchanged"


@dataclass
class Move:
    """One live slice and what the migration does to it."""

    slice: str
    name: str
    program: str
    area: str  # the area it has, or the one proposed
    outcome: str  # PLACED, CANNOT_PLACE or UNCHANGED
    evidence: str
    candidates: tuple[str, ...] = ()
    drop_program: bool = False
    source: str = ""  # knowledge-relative path of the row's file

    def as_json(self) -> dict[str, Any]:
        return {
            "slice": self.slice,
            "name": self.name,
            "program": self.program,
            "area": self.area,
            "outcome": self.outcome,
            "evidence": self.evidence,
            "candidates": list(self.candidates),
            "dropProgram": self.drop_program,
            "source": self.source,
        }


@dataclass
class Closure:
    """One open program and whether `--close-programs` supersedes it by feature areas."""

    program: str
    name: str
    state: str
    held: str = ""  # why it stays open (a live slice the migration could not place); "" when it closes
    source: str = ""  # knowledge-relative path of the row's fragment, "" for a row in the table

    def as_json(self) -> dict[str, Any]:
        return {"program": self.program, "name": self.name, "state": self.state, "held": self.held}


@dataclass
class ProofSlice:
    """One open program proof PRD, and the area slice that carries its end-to-end check from now on."""

    prd: str
    title: str
    program: str
    area: str  # "" when no area could be found: the PRD then stays where it is
    evidence: str
    from_slice: str  # the slice the PRD sits in today ("" for none)
    in_place: bool = False  # it stays in its live slice, which carries the check from now on
    names_proof: bool = False  # in place, and the slice named no proof of its own: it now names this PRD
    slice_source: str = ""  # knowledge-relative path of the home slice's fragment, "" for a table row
    name: str = ""
    done_when: str = ""
    depends_on: tuple[str, ...] = ()
    components: tuple[str, ...] = ()
    prd_path: str = ""  # knowledge-relative path of the PRD's `prd.md`
    new_id: str = ""  # the slice id `apply` claimed for it

    @property
    def creates(self) -> bool:
        return bool(self.area) and not self.in_place

    def as_json(self) -> dict[str, Any]:
        return {
            "prd": self.prd,
            "title": self.title,
            "program": self.program,
            "area": self.area,
            "evidence": self.evidence,
            "fromSlice": self.from_slice,
            "inPlace": self.in_place,
            "namesProof": self.names_proof,
            "name": self.name,
            "doneWhen": self.done_when,
            "dependsOn": list(self.depends_on),
            "components": list(self.components),
            "newSlice": self.new_id,
        }


@dataclass
class Plan:
    """What `apply` would write: the moves, and whether `.fleet/fleet.toml` flips to `areas`."""

    moves: list[Move] = field(default_factory=list)
    flip: bool = False
    mode: str = planningmode.DEFAULT_MODE
    skipped: int = 0  # finished or withdrawn slices left alone
    require_area: bool = False  # `apply` sets `[fleet.planning] require_area = true`
    closures: list[Closure] = field(default_factory=list)  # the open programs, under `close_programs`
    proofs: list[ProofSlice] = field(default_factory=list)  # their open proof PRDs
    unconverted: list[tuple[str, str, str]] = field(default_factory=list)  # (program, proof entry, why not)

    @property
    def closing(self) -> list[Closure]:
        return [c for c in self.closures if not c.held]

    @property
    def placed(self) -> list[Move]:
        return [m for m in self.moves if m.outcome == PLACED]

    @property
    def unplaced(self) -> list[Move]:
        return [m for m in self.moves if m.outcome == CANNOT_PLACE]

    @property
    def writes(self) -> list[Move]:
        return [m for m in self.moves if m.outcome == PLACED or m.drop_program]

    @property
    def writes_anything(self) -> bool:
        return bool(
            self.writes
            or self.flip
            or self.require_area
            or self.closing
            or any(p.creates or p.names_proof for p in self.proofs)
        )

    def exit_code(self) -> int:
        return 1 if self.unplaced or any(c.held for c in self.closures) else 0

    def as_json(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "flip": self.flip,
            "requireArea": self.require_area,
            "skipped": self.skipped,
            "moves": [m.as_json() for m in self.moves],
            "closures": [c.as_json() for c in self.closures],
            "proofs": [p.as_json() for p in self.proofs],
            "unconverted": [{"program": g, "proof": e, "why": w} for g, e, w in self.unconverted],
        }


def _prd_areas(knowledge: Path, prds_dir: str) -> dict[str, str]:
    """`PRD number -> its frontmatter area`, for every PRD that names one."""
    out: dict[str, str] = {}
    root = knowledge / prds_dir
    if not root.is_dir():
        return out
    for path in sorted(root.glob("*/prd.md")):
        num = path.parent.name.split("-", 1)[0]
        try:
            area = fm_field(frontmatter(path.read_text(encoding="utf-8", errors="replace")), "area")
        except OSError:
            continue
        if area:
            out[num] = area
    return out


def propose_area(
    components: Iterable[str],
    prd_areas: Iterable[str],
    areas: Mapping[str, Iterable[str]],
) -> tuple[str, str, tuple[str, ...]]:
    """`(area, evidence, candidates)` for one slice; `area == ""` when it cannot be placed."""
    named = [a for a in prd_areas if a]
    agreed = sorted(set(named))
    if len(agreed) == 1 and agreed[0] in areas:
        return agreed[0], f"its PRDs name area `{agreed[0]}`", ()
    comps = {c for c in components if c}
    if comps:
        holding = sorted(slug for slug, owned in areas.items() if comps <= set(owned))
        if len(holding) == 1:
            return holding[0], f"the `{holding[0]}` feature map holds its components ({', '.join(sorted(comps))})", ()
        if holding:
            return "", "more than one feature map holds its components", tuple(holding)
        touching = sorted(slug for slug, owned in areas.items() if comps & set(owned))
        if agreed or touching:
            return "", "no single feature map holds all its components", tuple(sorted(set(agreed) | set(touching)))
    if len(agreed) > 1:
        return "", "its PRDs name different areas", tuple(agreed)
    return "", "it names no component and no PRD names an area", ()


def live_slice_ids(board_payload: Mapping[str, Any]) -> frozenset[str]:
    """The ids of the LIVE slices in a board payload (`board.build`): the one liveness rule.

    Live: disposition `adopted`, not finished (board state not in `FINISHED_SLICE_STATES`), and its program,
    if it names one, `adopted` and not finished. Everything else is history, never rewritten. The migration
    places only these slices, and the check's `[fleet.planning] require_area` fails only these, so the two
    agree on which slices owe an area.
    """
    raw = board_payload.get("programs") or []
    programs = raw if isinstance(raw, list) else list(raw.values())
    prog_state = {str(p["id"]): str(p.get("state") or "") for p in programs}
    prog_disp = {str(p["id"]): _disposition_kind(p.get("disposition")) for p in programs}
    live: set[str] = set()
    for sid, s in (board_payload.get("slices") or {}).items():
        program = str(s.get("program") or "")
        if _disposition_kind(s.get("disposition")) != "adopted" or str(s.get("state") or "") in FINISHED_SLICE_STATES:
            continue
        if program and (prog_state.get(program, "") in FINISHED_PROGRAM_STATES or prog_disp.get(program) != "adopted"):
            continue
        live.add(str(sid))
    return frozenset(live)


def stranded_area_slice_ids(board_payload: Mapping[str, Any]) -> frozenset[str]:
    """Adopted, unfinished slices that still name a program already `superseded by areas`.

    `live_slice_ids` reads a slice as live only while its program is `adopted`, so a slice cut
    after `--close-programs` merged — one the migration's base never saw — reads as history, and
    a re-run would refuse to re-home it. That leaves the corpus in exactly the state the
    migration's own rule calls invalid (BUG-3032), and the check's repair hint would name a
    command that declines the work. These slices are the ones `--close-programs` still owes an
    area.
    """
    raw = board_payload.get("programs") or []
    programs = raw if isinstance(raw, list) else list(raw.values())
    closed = {str(p["id"]) for p in programs if closed_into_areas(p)}
    out: set[str] = set()
    for sid, s in (board_payload.get("slices") or {}).items():
        if _disposition_kind(s.get("disposition")) != "adopted" or str(s.get("state") or "") in FINISHED_SLICE_STATES:
            continue
        if str(s.get("program") or "") in closed:
            out.add(str(sid))
    return frozenset(out)


def plan(
    knowledge: Path,
    config: Any,
    *,
    drop_programs: bool = False,
    flip: bool = False,
    close_programs: bool = False,
    require_area: bool = False,
    board_payload: Mapping[str, Any] | None = None,
) -> Plan:
    """Read the corpus and decide; writes nothing. `close_programs` implies `drop_programs`."""
    drop_programs = drop_programs or close_programs
    from . import board as board_mod  # noqa: PLC0415 — the board is heavy; only a migration needs it

    planning = getattr(config, "planning", None) or {}
    features_dir = str(getattr(config, "features_dir", "") or "features")
    prds_dir = str(getattr(config, "prds_dir", "") or "prds")
    data = board_payload if board_payload is not None else board_mod.build(knowledge, config=config)
    areas = planningmode.feature_areas(knowledge, features_dir)
    prd_area = _prd_areas(knowledge, prds_dir)
    live = live_slice_ids(data)
    if close_programs:
        # Slices cut after a previous `--close-programs` merged still name the program it closed;
        # a re-run owes them the same re-homing (BUG-3032).
        live = live | stranded_area_slice_ids(data)
    out = Plan(mode=planningmode.mode_of(planning), flip=flip, require_area=require_area)
    for sid in sorted(data["slices"], key=_num):
        s = data["slices"][sid]
        program = str(s.get("program") or "")
        if sid not in live:
            out.skipped += 1
            continue
        have = str(s.get("area") or "")
        drop = bool(drop_programs and program)
        source = _source_of(knowledge, sid)
        if have:
            out.moves.append(
                Move(sid, str(s.get("name") or ""), program, have, UNCHANGED, "already names it", (), drop, source)
            )
            continue
        nums = [str(r.get("n") or "") for r in s.get("prds") or []]
        area, why, cands = propose_area(s.get("components") or [], (prd_area.get(n, "") for n in nums), areas)
        if area:
            out.moves.append(Move(sid, str(s.get("name") or ""), program, area, PLACED, why, (), drop, source))
        else:
            # A slice it cannot place keeps its program: dropping it would leave the slice with no home at all.
            out.moves.append(Move(sid, str(s.get("name") or ""), program, "", CANNOT_PLACE, why, cands, False, source))
    if close_programs:
        programs_dir = str(getattr(config, "programs_detail_dir", "") or "programs")
        _close_programs(out, knowledge, data, live, _prd_index(knowledge, prds_dir), areas, programs_dir)
    return out


def _prd_index(knowledge: Path, prds_dir: str) -> dict[str, dict[str, str]]:
    """`PRD number -> {title, status, slice, area, path}` off every `prd.md`'s frontmatter."""
    out: dict[str, dict[str, str]] = {}
    root = knowledge / prds_dir
    if not root.is_dir():
        return out
    for path in sorted(root.glob("*/prd.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm = frontmatter(text)
        h1 = re.search(r"^#\s+(.+)$", text, re.M)
        num = path.parent.name.split("-", 1)[0]
        out[num] = {
            "title": fm_field(fm, "title") or (h1.group(1).strip() if h1 else path.parent.name),
            "status": fm_field(fm, "status"),
            "slice": fm_field(fm, "slice"),
            "area": fm_field(fm, "area"),
            "path": path.relative_to(knowledge).as_posix(),
            "text": text,
        }
    return out


def _program_source(knowledge: Path, pid: str, programs_dir: str) -> str:
    frag = knowledge / programs_dir / "rows" / f"{pid}.json"
    return f"{programs_dir}/rows/{pid}.json" if frag.is_file() else ""


def demonstration(detail: str) -> str:
    """The `**Demonstration.**` sentence of a program detail file's `## Bar`, or `""` — the end-to-end
    observation the program's proof was written against, which becomes the area slice's Done when."""
    bar = section(detail, "Bar")
    m = re.search(r"\*\*Demonstration\.\*\*\s*(.+?)(?:\n\s*\n|\Z)", bar, re.S)
    return " ".join(m.group(1).split()) if m else ""


def _close_programs(
    out: Plan,
    knowledge: Path,
    data: Mapping[str, Any],
    live: frozenset[str],
    prds: Mapping[str, Mapping[str, str]],
    areas: Mapping[str, Iterable[str]],
    programs_dir: str,
) -> None:
    """Decide which programs close and what becomes of each one's open proof PRD."""
    raw = data.get("programs") or []
    programs = raw if isinstance(raw, list) else list(raw.values())
    slices: Mapping[str, Mapping[str, Any]] = data.get("slices") or {}
    area_of = {m.slice: m.area for m in out.moves if m.area}
    held_by: dict[str, list[str]] = {}
    for m in out.unplaced:
        if m.program:
            held_by.setdefault(m.program, []).append(m.slice)
    for g in programs:
        pid = str(g["id"])
        state = str(g.get("state") or "")
        if _disposition_kind(g.get("disposition")) != "adopted" or state in FINISHED_PROGRAM_STATES:
            continue  # withdrawn, superseded, complete or waived: history, never rewritten
        held = ""
        if held_by.get(pid):
            held = f"{', '.join(sorted(held_by[pid], key=_num))} could not be placed in an area"
        name = str(g.get("name") or "")
        out.closures.append(Closure(pid, name, state, held, _program_source(knowledge, pid, programs_dir)))
        mine = sorted(
            (sid for sid, s in slices.items() if str(s.get("program") or "") == pid and sid in live), key=_num
        )
        detail_path = knowledge / programs_dir / f"{pid}.md"
        detail = detail_path.read_text(encoding="utf-8", errors="replace") if detail_path.is_file() else ""
        for entry in [str(x if isinstance(x, str) else x.get("n", x)) for x in g.get("proof") or []]:
            if entry.startswith("drill:"):
                out.unconverted.append((pid, entry, "a drill record, not a PRD: no slice to carry"))
                continue
            if ":" in entry:
                out.unconverted.append((pid, entry, "another corpus's PRD: that corpus places it"))
                continue
            prd = prds.get(entry)
            if prd is None:
                out.unconverted.append((pid, entry, "no such PRD in this corpus"))
                continue
            if prd["status"] in PRD_TERMINAL:
                continue  # a finished proof is history
            ps = _proof_slice(entry, prd, pid, name, mine, slices, live, area_of, areas, detail)
            if ps.names_proof:
                ps.slice_source = _source_of(knowledge, ps.from_slice)
            out.proofs.append(ps)


def _proof_slice(
    num: str,
    prd: Mapping[str, str],
    pid: str,
    program_name: str,
    mine: list[str],
    slices: Mapping[str, Mapping[str, Any]],
    live: frozenset[str],
    area_of: Mapping[str, str],
    areas: Mapping[str, Iterable[str]],
    detail: str,
) -> ProofSlice:
    """The area slice one open proof PRD becomes — or stays in, when it already has a live slice to itself."""
    home = prd.get("slice", "")
    title = prd.get("title", "")
    home_row = slices.get(home) or {}
    members = [str(r.get("n") or "") for r in home_row.get("prds") or []]
    base = ProofSlice(num, title, pid, "", "", home, prd_path=prd.get("path", ""))
    if home in live:
        own_proof = [str(x) for x in home_row.get("proof") or home_row.get("verified_by") or []]
        bound = bool(re.search(rf"\[ext\s*→\s*{re.escape(home.replace('-', ''))}-C\d", prd.get("text", "")))
        why = ""
        if members == [num]:
            why = f"it is the only PRD of {home}"
        elif bound:
            why = f"its acceptance criteria are promoted from {home}'s bar"
        elif not own_proof:
            why = f"{home} names no proof of its own"
        if why:
            base.in_place, base.area = True, area_of.get(home, "")
            base.names_proof = not own_proof
            base.evidence = f"{why}, so {home} carries the check"
            if not own_proof:
                base.evidence += " and names it as its proof"
            return base
    if prd.get("area") and prd["area"] in areas:
        base.area, base.evidence = prd["area"], f"the PRD names area `{prd['area']}`"
    elif area_of.get(home):
        base.area, base.evidence = area_of[home], f"its slice {home} is in `{area_of[home]}`"
    else:
        counted: dict[str, int] = {}
        for sid in mine:
            if area_of.get(sid):
                counted[area_of[sid]] = counted.get(area_of[sid], 0) + 1
        best = sorted(counted.items(), key=lambda kv: (-kv[1], kv[0]))
        if best and (len(best) == 1 or best[0][1] > best[1][1]):
            base.area = best[0][0]
            base.evidence = f"most of {pid}'s live slices are in `{base.area}`"
        else:
            base.evidence = "no area names it: it stays in its slice"
            return base
    comps: list[str] = []
    for sid in mine or ([home] if home else []):
        for c in (slices.get(sid) or {}).get("components") or []:
            if c and c not in comps:
                comps.append(str(c))
    base.name = f"{program_name}, end to end" if program_name else f"{pid}, end to end"
    base.done_when = demonstration(detail) or (
        f"The end-to-end check {pid} named as its composed proof passes: PRD {num}, {title.rstrip('.')}."
    )
    base.depends_on = tuple(sid for sid in mine if sid in live)
    base.components = tuple(comps)
    return base


def _num(sid: str) -> int:
    m = re.search(r"(\d+)$", sid)
    return int(m.group(1)) if m else 0


def _disposition_kind(disp: Any) -> str:
    if isinstance(disp, Mapping):
        return str(disp.get("kind") or "adopted")
    return str(disp or "adopted")


def _source_of(knowledge: Path, sid: str) -> str:
    """The row's fragment, knowledge-relative, or `""` for a row in the positional table."""
    frag = knowledge / "slices" / "rows" / f"{sid}.json"
    return f"slices/rows/{sid}.json" if frag.is_file() else ""


def apply(
    knowledge: Path,
    repo: Path,
    the_plan: Plan,
    *,
    slice_register: str = "slices.md",
    program_register: str = "programs.md",
    slices_dir: str = "slices",
    new_ids: Callable[[int], list[str]] | None = None,
) -> list[Path]:
    """Write the plan into the working tree; returns the files changed. On an existing slice row only `area`
    (and `program` under `drop_programs`) is ever written; `--flip` and `--require-area` edit
    `.fleet/fleet.toml`. Under `close_programs` an open program's `Disposition` becomes `superseded by areas`,
    each converted proof PRD gets a new slice row (ids from `new_ids(count)`: the corpus's claim allocator;
    omitted, the next free numbers on disk) and its `slice:` moves to it. Slices are written BEFORE their
    programs close, so no live slice reads withdrawn at any point of the change."""
    changed: list[Path] = []
    table_edits: dict[str, Move] = {}
    for m in the_plan.writes:
        if m.source:
            path = knowledge / m.source
            path.write_text(
                edit_fragment(path.read_text(encoding="utf-8"), m.area if m.outcome == PLACED else "", m.drop_program),
                encoding="utf-8",
            )
            changed.append(path)
        else:
            table_edits[m.slice] = m
    if table_edits:
        reg = knowledge / slice_register
        lines = reg.read_text(encoding="utf-8").splitlines(keepends=True)
        for i, line in enumerate(lines):
            cells = line.rstrip("\n").split("|")
            if len(cells) < 6:
                continue
            sid = cells[1].strip()
            if sid not in table_edits:
                continue
            m = table_edits[sid]
            program, area = planningmode.split_home_cell(cells[4].strip())
            row = {"program": "" if m.drop_program else program, "area": m.area if m.outcome == PLACED else area}
            cells[4] = f" {planningmode.home_cell(row)} "
            lines[i] = "|".join(cells) + ("\n" if line.endswith("\n") else "")
        reg.write_text("".join(lines), encoding="utf-8")
        changed.append(reg)
    creating = [ps for ps in the_plan.proofs if ps.creates]
    if creating:
        ids = (new_ids or (lambda n: _next_free_slice_ids(knowledge, slice_register, slices_dir, n)))(len(creating))
        if len(ids) != len(creating):
            raise RuntimeError(f"asked for {len(creating)} slice ids, got {len(ids)}")
        for ps, sid in zip(creating, ids, strict=True):
            ps.new_id = sid
            changed.append(_write_slice(knowledge, slice_register, slices_dir, ps))
            prd = knowledge / ps.prd_path
            prd.write_text(move_prd_slice(prd.read_text(encoding="utf-8"), sid), encoding="utf-8")
            changed.append(prd)
    naming = {ps.from_slice: ps for ps in the_plan.proofs if ps.names_proof}
    for ps in naming.values():
        if ps.slice_source:
            path = knowledge / ps.slice_source
            path.write_text(name_proof_fragment(path.read_text(encoding="utf-8"), ps.prd), encoding="utf-8")
            changed.append(path)
    table_proofs = {sid: ps for sid, ps in naming.items() if not ps.slice_source}
    if table_proofs:
        reg = knowledge / slice_register
        lines = reg.read_text(encoding="utf-8").splitlines(keepends=True)
        for i, line in enumerate(lines):
            cells = line.rstrip("\n").split("|")
            if len(cells) < 8 or cells[1].strip() not in table_proofs:
                continue
            cells[6] = f" {table_proofs[cells[1].strip()].prd} "
            lines[i] = "|".join(cells) + ("\n" if line.endswith("\n") else "")
        reg.write_text("".join(lines), encoding="utf-8")
        changed.append(reg)
    table_closures: dict[str, Closure] = {}
    for c in the_plan.closing:
        if c.source:
            path = knowledge / c.source
            path.write_text(supersede_fragment(path.read_text(encoding="utf-8")), encoding="utf-8")
            changed.append(path)
        else:
            table_closures[c.program] = c
    if table_closures:
        reg = knowledge / program_register
        lines = reg.read_text(encoding="utf-8").splitlines(keepends=True)
        for i, line in enumerate(lines):
            cells = line.rstrip("\n").split("|")
            if len(cells) < 4 or cells[1].strip() not in table_closures:
                continue
            cells[-2] = f" superseded by {AREAS_SUCCESSOR} "
            lines[i] = "|".join(cells) + ("\n" if line.endswith("\n") else "")
        reg.write_text("".join(lines), encoding="utf-8")
        changed.append(reg)
    if the_plan.flip or the_plan.require_area:
        toml = repo / ".fleet" / "fleet.toml"
        text = toml.read_text(encoding="utf-8") if toml.is_file() else ""
        if the_plan.flip:
            text = flip_mode(text)
        if the_plan.require_area:
            text = set_require_area(text)
        toml.write_text(text, encoding="utf-8")
        changed.append(toml)
    return list(dict.fromkeys(changed))


def _existing_slice_numbers(knowledge: Path, slice_register: str, slices_dir: str) -> list[int]:
    nums = [_num(f.stem) for f in (knowledge / slices_dir / "rows").glob("SL-*.json")]
    reg = knowledge / slice_register
    if reg.is_file():
        text = reg.read_text(encoding="utf-8")
        nums += [int(n) for n in re.findall(r"^\|\s*SL-(\d+)\s*\|", text, re.M)]
        if m := re.search(r"Next id:\s*SL-(\d+)", text):
            nums.append(int(m.group(1)) - 1)
    return nums


def _next_free_slice_ids(knowledge: Path, slice_register: str, slices_dir: str, count: int) -> list[str]:
    """The next `count` slice ids after the highest on disk — for a corpus that claims no ids."""
    top = max(_existing_slice_numbers(knowledge, slice_register, slices_dir) or [0])
    return [f"SL-{top + i:03d}" for i in range(1, count + 1)]


def _write_slice(knowledge: Path, slice_register: str, slices_dir: str, ps: ProofSlice) -> Path:
    """The new slice's row: its own fragment where the register keeps fragments, else a table row."""
    rows = knowledge / slices_dir / "rows"
    if rows.is_dir() and any(rows.glob("*.json")):
        path = rows / f"{ps.new_id}.json"
        path.write_text(json.dumps(proof_slice_row(ps), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path
    reg = knowledge / slice_register
    text = reg.read_text(encoding="utf-8")
    row = proof_slice_row(ps)
    cells = [
        ps.new_id,
        row["name"],
        row["kind"],
        f"area:{row['area']}",
        row["done_when"],
        ", ".join(row["verified_by"]) or "—",
        ", ".join(row["depends_on"]) or "—",
        ", ".join(row["components"]) or "—",
        row["disposition"],
    ]
    line = "| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |\n"
    text = text if text.endswith("\n") else text + "\n"
    text += line
    if m := re.search(r"Next id:\s*SL-(\d+)", text):
        nxt = max(int(m.group(1)), _num(ps.new_id) + 1)
        text = text[: m.start()] + f"Next id: SL-{nxt:03d}" + text[m.end() :]
    reg.write_text(text, encoding="utf-8")
    return reg


def proof_slice_row(ps: ProofSlice) -> dict[str, Any]:
    """The row a converted proof becomes, key order as every hand-written fragment has it."""
    return {
        "name": ps.name,
        "kind": PROOF_SLICE_KIND,
        "from_program": ps.program,
        "area": ps.area,
        "done_when": ps.done_when,
        "verified_by": [ps.prd],
        "depends_on": list(ps.depends_on),
        "components": list(ps.components),
        "disposition": "adopted",
    }


def move_prd_slice(text: str, sid: str) -> str:
    """A PRD's text with its frontmatter `slice:` set to `sid` (added after `status:` when absent)."""
    end = text.find("\n---", 3) if text.startswith("---") else -1
    if end < 0:
        raise RuntimeError("the PRD has no frontmatter to move")
    head, rest = text[:end], text[end:]
    if re.search(r"^slice:.*$", head, re.M):
        head = re.sub(r"^slice:.*$", f"slice: {sid}", head, count=1, flags=re.M)
    elif re.search(r"^status:.*$", head, re.M):
        head = re.sub(r"^(status:.*)$", rf"\1\nslice: {sid}", head, count=1, flags=re.M)
    else:
        head = head + f"\nslice: {sid}"
    return head + rest


def name_proof_fragment(text: str, prd: str) -> str:
    """A slice fragment whose empty `verified_by` now names `prd` — a line edit when it can be."""
    out, n = re.subn(r'^(\s*"verified_by"\s*:\s*)\[\s*\]', rf'\1["{prd}"]', text, count=1, flags=re.M)
    if n and json.loads(out).get("verified_by") == [prd]:
        return out
    data = json.loads(text)
    if not data.get("verified_by"):
        data["verified_by"] = [prd]
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def supersede_fragment(text: str) -> str:
    """A program fragment with `disposition` set to `superseded by areas` — a line edit when it can be."""
    out, n = re.subn(
        r'^(\s*"disposition"\s*:\s*)"[^"]*"', rf'\1"superseded by {AREAS_SUCCESSOR}"', text, count=1, flags=re.M
    )
    if n and json.loads(out).get("disposition") == f"superseded by {AREAS_SUCCESSOR}":
        return out
    data = json.loads(text)
    data["disposition"] = f"superseded by {AREAS_SUCCESSOR}"
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def set_require_area(text: str) -> str:
    """`.fleet/fleet.toml` with `[fleet.planning] require_area = true` — added under the table, or set."""
    lines = text.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines) if ln.strip() == "[fleet.planning]"), None)
    if start is None:
        sep = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        return text + sep + "[fleet.planning]\nrequire_area = true\n"
    end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("[")), len(lines))
    for i in range(start + 1, end):
        if re.match(r"\s*require_area\s*=", lines[i]):
            lines[i] = "require_area = true\n"
            return "".join(lines)
    at = next((i + 1 for i in range(start + 1, end) if re.match(r"\s*mode\s*=", lines[i])), start + 1)
    lines.insert(at, "require_area = true\n")
    return "".join(lines)


def edit_fragment(text: str, area: str, drop_program: bool) -> str:
    """A row fragment's text with `area` added (when given) and, under `drop_program`, `program` renamed to
    `from_program` — AS A LINE EDIT, so the reviewed diff is the one or two lines that changed and the
    author's own layout stays. Falls back to a re-dump when the file is not laid out one key per line."""
    data = json.loads(text)
    lines = text.splitlines(keepends=True)
    key_line = re.compile(r'^(\s*)"(program|kind)"\s*:')
    if area and "area" not in data:
        at = next((i for i, ln in enumerate(lines) if key_line.match(ln) and '"program"' in ln), None)
        if at is None:
            at = next((i for i, ln in enumerate(lines) if key_line.match(ln)), None)
        found = key_line.match(lines[at]) if at is not None else None
        if at is None or found is None or not lines[at].rstrip().endswith(","):
            return _redump(data, area, drop_program)
        indent = found.group(1)
        lines.insert(at + 1, f"{indent}{json.dumps('area')}: {json.dumps(area, ensure_ascii=False)},\n")
    if drop_program and data.get("program"):
        at = next((i for i, ln in enumerate(lines) if re.match(r'^\s*"program"\s*:', ln)), None)
        if at is None:
            return _redump(data, area, drop_program)
        lines[at] = lines[at].replace('"program"', '"from_program"', 1)
    out = "".join(lines)
    try:
        json.loads(out)
    except ValueError:
        return _redump(data, area, drop_program)
    return out


def _redump(data: dict[str, Any], area: str, drop_program: bool) -> str:
    if area and "area" not in data:
        data = _with_area(data, area)
    if drop_program and data.get("program"):
        data = {("from_program" if k == "program" else k): v for k, v in data.items()}
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _with_area(data: dict[str, Any], area: str) -> dict[str, Any]:
    """`data` with `area` set right after `program` (or `kind`), so the diff reads as one added line."""
    out: dict[str, Any] = {}
    placed = False
    for k, v in data.items():
        if k == "area":
            continue
        out[k] = v
        if k in ("program", "kind") and not placed and ("program" not in data or k == "program"):
            out["area"] = area
            placed = True
    if not placed:
        out["area"] = area
    return out


def flip_mode(text: str) -> str:
    """`.fleet/fleet.toml` with `[fleet.planning] mode = "areas"` — the table added, or its `mode` line set.
    Nothing else in the file moves."""
    lines = text.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines) if ln.strip() == "[fleet.planning]"), None)
    if start is None:
        sep = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        return text + sep + '[fleet.planning]\nmode = "areas"\n'
    end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("[")), len(lines))
    for i in range(start + 1, end):
        if re.match(r"\s*mode\s*=", lines[i]):
            lines[i] = 'mode = "areas"\n'
            return "".join(lines)
    lines.insert(start + 1, 'mode = "areas"\n')
    return "".join(lines)


def table(the_plan: Plan) -> str:
    """The dry run, as the Markdown a person reviews (and the PR body's core)."""
    out = [
        f"Planning mode: `{the_plan.mode}`" + (" -> `areas` (this PR flips it)" if the_plan.flip else ""),
        "",
        f"Slices placed ({len(the_plan.placed)})",
        "",
        "| Slice | Program | Proposed area | Why this area |",
        "|---|---|---|---|",
    ]
    out += [
        f"| {m.slice} {m.name} | {m.program or '-'}{' (leaves it)' if m.drop_program else ''} "
        f"| `{m.area}` | {m.evidence} |"
        for m in the_plan.placed
    ]
    out += [
        "",
        f"Needs your call ({len(the_plan.unplaced)})",
        "",
        "| Slice | Program | Why it could not be placed | Candidates |",
        "|---|---|---|---|",
    ]
    out += [
        f"| {m.slice} {m.name} | {m.program or '-'} | {m.evidence} | {', '.join(m.candidates) or '-'} |"
        for m in the_plan.unplaced
    ]
    dropped = [m for m in the_plan.moves if m.outcome == UNCHANGED and m.drop_program]
    if dropped:
        out += ["", f"Leaving their program ({len(dropped)}): " + ", ".join(m.slice for m in dropped)]
    if the_plan.closures:
        out += [
            "",
            f"Programs closed, superseded by feature areas ({len(the_plan.closing)})",
            "",
            "| Program | Its reading today |",
            "|---|---|",
        ]
        out += [f"| {c.program} {c.name} | {c.state} |" for c in the_plan.closing]
        held = [c for c in the_plan.closures if c.held]
        if held:
            out += ["", f"Programs left open ({len(held)})", "", "| Program | Why it stays open |", "|---|---|"]
            out += [f"| {c.program} {c.name} | {c.held} |" for c in held]
    if the_plan.proofs:
        out += [
            "",
            f"Open program proofs, each now one area slice ({len(the_plan.proofs)})",
            "",
            "| PRD | Program | Slice | Area | Why this area |",
            "|---|---|---|---|---|",
        ]
        for ps in the_plan.proofs:
            if ps.creates:
                where = f"new {ps.new_id or 'slice'} ({ps.name}), from {ps.from_slice or 'no slice'}"
            else:
                where = f"stays in {ps.from_slice or 'no slice'}" + (", now its proof" if ps.names_proof else "")
            out.append(f"| {ps.prd} {ps.title} | {ps.program} | {where} | `{ps.area or '-'}` | {ps.evidence} |")
    if the_plan.unconverted:
        out += ["", "Program proofs not converted: " + "; ".join(f"{g} {e} ({w})" for g, e, w in the_plan.unconverted)]
    out += [
        "",
        f"Not touched: {the_plan.skipped} finished or withdrawn slices"
        + (
            ", and every finished, waived or withdrawn program row."
            if the_plan.closures
            else ", and every program row."
        ),
    ]
    return "\n".join(out) + "\n"


PR_TITLE = "Place the live slices in feature areas"
CLOSE_TITLE = "Close the programs into feature areas"
SWITCH_TITLE = "Plan by feature area"


def moves_nothing(the_plan: Plan) -> bool:
    """True when the plan touches no slice, program or proof PRD: only `.fleet/fleet.toml` changes."""
    return not (the_plan.moves or the_plan.closures or the_plan.proofs or the_plan.unconverted)


def pr_title(the_plan: Plan) -> str:
    """The pull request's title, naming what it actually does."""
    if the_plan.closing:
        return CLOSE_TITLE
    return SWITCH_TITLE if moves_nothing(the_plan) else PR_TITLE


def _switch_body(the_plan: Plan) -> str:
    """The description of a PR that only changes the planning settings."""
    sets = []
    if the_plan.flip:
        sets.append('`mode = "areas"`')
    if the_plan.require_area:
        sets.append("`require_area = true`")
    what = (
        "No program is open and no live slice moves, so this PR changes no slice, program or PRD. "
        + (f"It only sets {' and '.join(sets)} under `[fleet.planning]` in `.fleet/fleet.toml`. " if sets else "")
        + "From now on, new work is planned by feature area."
    )
    return (
        f"**What this does.** {what}\n\n"
        f"Planning mode: `{the_plan.mode}`" + (" -> `areas`" if the_plan.flip else "") + "\n\n"
        f"Not touched: {the_plan.skipped} finished or withdrawn slices, and every program row.\n\n"
        "**How to undo.** Close this PR, or revert it after merging.\n\n"
        "Opened by `fleet planning migrate --pr`. Review it like any knowledge change; it does not merge itself.\n"
    )


def pr_body(the_plan: Plan) -> str:
    """The pull request's description: what it does, the table, what does not change, and how to undo it."""
    if moves_nothing(the_plan):
        return _switch_body(the_plan)
    off = any(m.drop_program for m in the_plan.moves)
    closing = bool(the_plan.closing)
    what = (
        "Every live slice names the feature area it belongs to. This PR gives each live slice that has none an area"
        + (", and takes the live slices off their programs" if off else "")
        + (
            ", turns each open program proof into an area slice, and marks every open program `superseded by areas`"
            if closing
            else ""
        )
        + (', and sets `[fleet.planning] mode = "areas"`' if the_plan.flip else "")
        + (" and `require_area = true`" if the_plan.require_area else "")
        + (". Nothing is built by merging it." if closing else ". Nothing is built or closed by merging it.")
    )
    return (
        f"**What this does.** {what}\n\n"
        + table(the_plan)
        + (
            "\n**What does not change.** Program rows stay, closed: a closed program withdraws no slice with it, "
            "so a finished slice under it stays finished. "
            if closing
            else "\n**What does not change.** Program rows stay; each program closes as usual once its slices "
            "are done. "
        )
        + "Finished and withdrawn slices and programs are not touched, so every `PG-NN` keeps resolving"
        + ("; a slice taken off its program keeps it as `from_program`" if off else "")
        + (
            ". A converted proof PRD only moves to its new slice (`slice:`); no other PRD, task or bug changes.\n\n"
            if closing
            else ". No PRD, task or bug changes.\n\n"
        )
        + "**Slices it could not place** are left exactly as they are: name their area in a review comment, or edit "
        "the row on this branch.\n\n"
        "**How to undo.** Close this PR, or revert it after merging: both shapes of a slice row stay valid.\n\n"
        "Opened by `fleet planning migrate --pr`. Review it like any knowledge change; it does not merge itself.\n"
    )


def _run(args: list[str], cwd: Path) -> str:
    import subprocess  # noqa: PLC0415

    done = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise RuntimeError(f"`{' '.join(args[:3])} …` failed: {(done.stderr or done.stdout).strip()[:400]}")
    return done.stdout.strip()


def open_pr(
    repo: Path,
    *,
    base: str,
    branch: str,
    drop_programs: bool,
    flip: bool,
    workdir: Path,
    close_programs: bool = False,
    require_area: bool = False,
    claim_ids: bool = True,
) -> tuple[Plan, str]:
    """`--pr`: the migration on a NEW branch in a temporary worktree off `base` — never the caller's checkout
    — committed, pushed and opened as one pull request. Returns the plan and the PR's URL (`""` when there was
    nothing to write). It never merges."""
    from . import config as kb_config  # noqa: PLC0415

    remote, _, ref = base.partition("/")
    if ref:
        _run(["git", "fetch", "-q", remote, ref], repo)
    tree = workdir / "fleet-planning-migrate"
    _run(["git", "worktree", "add", "-q", "-b", branch, str(tree), base], repo)
    try:
        kb = kb_config.resolve(cwd=tree, env={})
        the_plan = plan(
            kb.knowledge,
            kb.config,
            drop_programs=drop_programs,
            flip=flip,
            close_programs=close_programs,
            require_area=require_area,
        )
        if not the_plan.writes_anything:
            return the_plan, ""
        changed = apply(
            kb.knowledge, tree, the_plan, new_ids=slice_allocator(kb) if claim_ids else None, **registers_of(kb.config)
        )
        title = pr_title(the_plan)
        _run(["git", "add", "--", *(str(p) for p in changed)], tree)
        _run(["git", "commit", "-q", "-m", title], tree)
        _run(["git", "push", "-q", "-u", remote or "origin", branch], tree)
        body = workdir / "fleet-planning-migrate-body.md"
        body.write_text(pr_body(the_plan), encoding="utf-8")
        url = _run(
            [
                "gh",
                "pr",
                "create",
                "--base",
                ref or base,
                "--head",
                branch,
                "--title",
                title,
                "--body-file",
                str(body),
            ],
            tree,
        )
        return the_plan, url
    finally:
        with contextlib.suppress(RuntimeError):
            _run(["git", "worktree", "remove", "--force", str(tree)], repo)


def registers_of(config: Any) -> dict[str, str]:
    """The register paths `apply` writes, off a corpus's config (the defaults when it names none)."""
    return {
        "slice_register": str(getattr(config, "slices_register", "") or "slices.md"),
        "program_register": str(getattr(config, "programs_register", "") or "programs.md"),
        "slices_dir": str(getattr(config, "slices_detail_dir", "") or "slices"),
    }


def slice_allocator(kb: Any) -> Callable[[int], list[str]]:
    """`count -> ids` through the corpus's own id allocator: claimed as `refs/ids/<ID>` where the corpus
    configures claims, so a new slice id cannot collide with one an open branch already holds."""

    def allocate(count: int) -> list[str]:
        from .checks.planning import id_collisions  # noqa: PLC0415 — only a write that mints ids needs it

        prefix = str(getattr(kb.config, "slice_prefix", "") or "SL")
        ids, _, _ = id_collisions.allocate(kb, prefix=prefix, count=count)
        return ids

    return allocate
