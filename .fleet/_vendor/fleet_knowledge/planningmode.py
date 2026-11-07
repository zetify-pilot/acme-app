"""Where a slice lives: under a feature area, optionally also in a program — and where new work goes.

Decided by the owner on 2026-10-27 and amended live on 2026-10-28
(`docs/design/2026-10-27-planning-without-programs.md`,
`knowledge/decisions/2026-10-27-planning-without-programs.md`):

  * **Every slice names an `area`** (a feature map's slug); a `program` is optional, legacy
    membership **[FLT-1280]**. A row that names only a program reads exactly as before — whether it is
    a finding is `tracking-metadata`'s, and an untouched one is only noted.
  * `[fleet.planning] mode` in `.fleet/fleet.toml` says where NEW work goes **[FLT-1281]**:
    absent or `"programs"` (every existing repository: nothing changes) or `"areas"` (programs take no
    new slices).
  * `[fleet.planning] require_area = true` makes every LIVE slice without an area fail the check, not
    only a new or changed one. Live is `fleet planning migrate`'s rule (`planningmigrate.live_slice_ids`):
    a finished or withdrawn slice is history, never rewritten, so it is never failed for lacking an area.
    Absent means false.

Only a fresh `fleet init` writes either key. Neither ever makes an old row unreadable, so turning a key
back is a complete revert.

**The one parser of the positional table's home cell.** A corpus that has not moved to row fragments
keeps the nine-column `slices.md`, whose fourth column is `Program`. The area rides in that cell as
`area:<slug>`, after the program when there is one (`PG-04, area:board`), so no column moves and no
positional reader shifts.

Stdlib only.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .featureshell import area_stem, map_files
from .markdown import field, frontmatter, listfield

PROGRAMS = "programs"
AREAS = "areas"
MODES = (PROGRAMS, AREAS)
#: What an absent setting means — every repository that existed before the setting did.
DEFAULT_MODE = PROGRAMS

#: The `Program` cell of the positional table carries an area as `area:<slug>`.
AREA_CELL_PREFIX = "area:"


def split_home_cell(cell: str) -> tuple[str, str]:
    """`(program, area)` from a table's `Program` cell: `PG-04, area:board` -> `("PG-04", "board")`."""
    program, area = [], ""
    for part in (cell or "").split(","):
        text = part.strip()
        if text.lower().startswith(AREA_CELL_PREFIX):
            area = text[len(AREA_CELL_PREFIX) :].strip()
        elif text:
            program.append(text)
    return ", ".join(program), area


def home_cell(row: Mapping[str, Any]) -> str:
    """The table's `Program` cell for a parsed slice row — the inverse of `split_home_cell`."""
    program = str(row.get("program") or "").strip()
    area = str(row.get("area") or "").strip()
    return ", ".join(x for x in (program, f"{AREA_CELL_PREFIX}{area}" if area else "") if x)


def home_of(row: Mapping[str, Any]) -> str:
    """One string naming a slice's home, for a reader that groups by it: `PG-40` or `area:fleet-board`.

    `""` for a row naming neither (a finding of its own). A reader grouping by PROGRAM reads
    `row["program"]` instead and skips `""` — an area slice has no program to roll up to."""
    program = str(row.get("program") or "").strip()
    if program:
        return program
    area = str(row.get("area") or "").strip()
    return f"{AREA_CELL_PREFIX}{area}" if area else ""


def is_area_slice(row: Mapping[str, Any]) -> bool:
    """Whether a parsed slice lives ONLY under an area — no program — and so is driven on its own."""
    return bool(str(row.get("area") or "").strip()) and not str(row.get("program") or "").strip()


def mode_of(planning: Mapping[str, Any] | None) -> str:
    """The mode a `[fleet.planning]` table declares; `DEFAULT_MODE` when it says nothing.

    An unknown value is refused where the file is READ (`check_mode`); here it reads as the default,
    because a reader that cannot start is a worse failure than a setting that did nothing."""
    value = str((planning or {}).get("mode") or "").strip().lower()
    return value if value in MODES else DEFAULT_MODE


def require_area_of(planning: Mapping[str, Any] | None) -> bool:
    """Whether every slice without an area fails the check (`require_area = true`). Absent means False."""
    return (planning or {}).get("require_area") is True


def check_require_area(value: Any) -> str:
    """`""` when `value` is a valid `require_area`, else the sentence refusing it."""
    return "" if isinstance(value, bool) else f"`require_area` must be true or false, got {value!r}"


def check_mode(value: Any) -> str:
    """`""` when `value` is a valid `mode`, else the sentence refusing it."""
    if isinstance(value, str) and value.strip().lower() in MODES:
        return ""
    return f'`mode` must be "{PROGRAMS}" or "{AREAS}", got {value!r} — leave it out to plan by programs'


def feature_areas(knowledge: Path, features_dir: str = "features") -> dict[str, tuple[str, ...]]:
    """Every feature area this corpus carries, `slug -> the components its map lists`.

    An area is a feature map: `<knowledge>/<features_dir>/*.md` with `type: feature-map`, named by its
    `area:` (falling back to the file's stem). The components are what the migration (Step 5) matches a
    slice's own components against. `{}` for a corpus with no feature maps — where an area slice can
    resolve to nothing, which is a finding of its own."""
    root = knowledge / features_dir if features_dir else knowledge
    out: dict[str, tuple[str, ...]] = {}
    if not root.is_dir():
        return out
    for path in map_files(root):
        try:
            fm = frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if field(fm, "type") != "feature-map":
            continue
        slug = field(fm, "area") or area_stem(path)
        out[slug] = tuple(listfield(fm, "components"))
    return out
