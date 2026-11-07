"""Binding a decomposition to the exact bytes of the completion sentence it decomposes.

Two checks now decompose the same cell from two different files — the clause table a proof PRD
writes, and the `## Bar` a slice authors — and both bind to it with a SHA-256 of the cell's
authored bytes. **One implementation, here.** Two copies would be two answers to "what exactly
is being digested", and the day they disagreed one of the two gates would bless a sentence the
other rejects, which is the failure a digest exists to make impossible.

Nothing is normalised on the way in. The digest binds the AUTHORED characters: a reader that
trimmed markup or collapsed whitespace would be blessing a different string from the one on the
page, and the next author would edit the page and see the gate stay green.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

__all__ = ["digest_of", "extract_done_cell"]

#: Cell contents that mean "nothing here" — an empty completion condition, however it is typed.
EMPTY_CELLS = frozenset({"", "—", "-", "–"})

#: The completion-condition column, 0-based, in the slice register's row.
DONE_COLUMN = 4


def digest_of(text: str) -> str:
    """SHA-256 hex of the exact UTF-8 bytes of `text` (no added trailing newline)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


#: The key a slice row fragment (`<slices dir>/rows/SL-NNN.json`) keeps the cell under.
FRAGMENT_DONE_KEY = "done_when"


def _fragment_cell(rows_dir: Path, slice_id: str) -> str | None:
    """The `Done when` cell a row FRAGMENT renders to, or None when there is no fragment.

    A corpus whose register is fragment-backed commits `<register>.md.tmpl` and one JSON file
    per row, and renders `slices.md` on demand (gitignored). The fragment is the authored source
    — the rendered table is derived from it, and may be absent or stale — so it is read first,
    as `Registers.slices()` reads it. The cell is what the renderer writes between the pipes
    (`gen_knowledge_registers._render_cell`: a literal `|` written `\\|`), stripped, so a bar
    blessed against the rendered table and one blessed against the fragment carry one digest.
    """
    frag = rows_dir / f"{slice_id}.json"
    if not frag.is_file():
        return None
    try:
        data = json.loads(frag.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{frag}: not a readable JSON row fragment ({exc})") from exc
    value = data.get(FRAGMENT_DONE_KEY) if isinstance(data, dict) else None
    done = ("" if value is None else str(value)).replace("|", "\\|").strip()
    if done in EMPTY_CELLS:
        raise ValueError(f"{frag}: {slice_id} Done when cell is empty")
    return done


def extract_done_cell(slices_md: Path, slice_id: str, rows_dir: Path | None = None) -> str:
    """The `Done when` cell text for `slice_id`, exactly as written between the pipes.

    Stripped of surrounding whitespace only — no markup stripping, because the digest binds
    the authored characters and a reader that normalised them would bless a different string
    from the one on the page.

    A row fragment wins when there is one: `rows_dir` (default `<register stem>/rows` beside
    the register — `slices/rows/` for `slices.md`) holding `<slice_id>.json`.
    """
    frag_done = _fragment_cell(rows_dir if rows_dir is not None else slices_md.with_suffix("") / "rows", slice_id)
    if frag_done is not None:
        return frag_done
    if not slices_md.is_file():
        raise FileNotFoundError(f"{slices_md} not found")
    needle = f"| {slice_id} |"
    for i, line in enumerate(slices_md.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.lstrip()
        if not stripped.startswith(needle) and not stripped.startswith(f"|{slice_id}|"):
            # Allow either spaced or tight first cell.
            row = [c.strip() for c in stripped.strip("|").split("|")]
            if not row or row[0] != slice_id:
                continue
        else:
            row = [c.strip() for c in stripped.strip("|").split("|")]
        if len(row) < DONE_COLUMN + 1:
            raise ValueError(f"{slices_md}:{i}: {slice_id} row has fewer than {DONE_COLUMN + 1} columns")
        done = row[DONE_COLUMN]
        if done in EMPTY_CELLS:
            raise ValueError(f"{slices_md}:{i}: {slice_id} Done when cell is empty")
        return done
    raise ValueError(f"{slices_md}: no row for {slice_id}")
