"""Every per-row fragment file the corpus stores must be readable — the gate the readers rely on.

**The readers degrade, and that degradation is right for one file and wrong for the corpus.** A
fragment that cannot be parsed is skipped by `fleet_knowledge.requirements.load_row_fragments`,
`fleet_knowledge.registers.fragments`, `fleet_knowledge.corpus.load_feature_row_fragments` and
the journey check's own feature-row read, so the OTHER rows still render. But nothing said the
skipped row existed: a merge conflict written into `requirements/rows/RUN-001.json` removed that
promise from the board, the knowledge graph and the Quality desk with no warning on any page.

The render step (`gen_knowledge_fragments.py`, `gen_knowledge_registers.py`) raises on a file it
cannot parse, but it only runs where a corpus renders its tables — a consumer that runs
`fleet check` alone never saw the defect. This check is the missing gate: it reads every
fragment family the corpus stores and refuses one no reader can use.

A fragment is refused for the same three reasons a reader would drop it:

  * the bytes cannot be read, or are not JSON;
  * the JSON is not an object (every reader requires one);
  * the object lacks a key its own reader requires (`table`/`order`/`cells` for a register or
    feature row, `order`/`path` for a `source_of_truth` fragment).

A program or slice fragment is refused only for the first two: its reader takes any object and
lets the column rules judge what is inside it.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ._api import ERROR, finding
from ._config import PlanningConfig

NAME = "knowledge-fragments"

ROWS_SUBDIR = "rows"
SOT_SUBDIR = "source_of_truth"


def _read(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """`(the object, None)` or `(None, why no reader can use it)`."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"cannot be read ({exc.strerror or exc})"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"is not valid JSON ({exc.msg} at line {exc.lineno} column {exc.colno})"
    if not isinstance(data, dict):
        return None, f"is not a JSON object (found {type(data).__name__})"
    return data, None


def _dict_only(_data: dict[str, Any]) -> str | None:
    """A program or slice row: the reader takes any object and judges the columns itself."""
    return None


def _row_problem(data: dict[str, Any]) -> str | None:
    """A register or capability row: the keys `load_row_fragments` requires, or it is skipped."""
    if not str(data.get("table") or "").strip():
        return "has no `table` key"
    if not isinstance(data.get("order"), int):
        return "has no integer `order` key"
    if not isinstance(data.get("cells"), list):
        return "has no `cells` list"
    return None


def _sot_problem(data: dict[str, Any]) -> str | None:
    """A `source_of_truth` fragment: the keys its reader requires, or the claim is dropped."""
    if not isinstance(data.get("order"), int):
        return "has no integer `order` key"
    if not str(data.get("path") or "").strip():
        return "has no `path` key"
    return None


def _families(cfg: PlanningConfig, knowledge: Path) -> list[tuple[Path, Callable[[dict[str, Any]], str | None]]]:
    """`(rows directory, what makes a file there usable)` for every table-fragment family."""
    out: list[tuple[Path, Callable[[dict[str, Any]], str | None]]] = []
    if cfg.requirements_dir:
        out.append((knowledge / cfg.requirements_dir / ROWS_SUBDIR, _row_problem))
    if cfg.program_detail_dir:
        out.append((knowledge / cfg.program_detail_dir / ROWS_SUBDIR, _dict_only))
    if cfg.slice_detail_dir:
        out.append((knowledge / cfg.slice_detail_dir / ROWS_SUBDIR, _dict_only))
    if cfg.features_dir:
        out.append((knowledge / cfg.features_dir / ROWS_SUBDIR, _row_problem))
    return out


def _sot_dirs(cfg: PlanningConfig, knowledge: Path) -> list[Path]:
    """One directory per feature area under `features/source_of_truth/`."""
    if not cfg.features_dir:
        return []
    base = knowledge / cfg.features_dir / SOT_SUBDIR
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if p.is_dir())


def _finding(path: Path, why: str) -> Any:
    return finding(
        ERROR,
        f"`{path.name}` {why} — every reader skips a fragment it cannot use, so what it holds "
        "disappears from the board, the knowledge graph and the Quality desk with no warning",
        path=path,
        hint=(
            "Restore the file to one JSON object in the shape its directory expects (a merge "
            "conflict written into it is the usual cause); a row must never vanish silently."
        ),
    )


class KnowledgeFragmentsCheck:
    """Every per-row fragment the corpus stores is readable, and shaped as its reader expects."""

    name = NAME
    title = "Knowledge fragments are readable"
    description = (
        "Every table the knowledge readers serve — the requirement registers, the program and "
        "slice registers, the capability rows and a feature map's `source_of_truth:` list — is "
        "stored as one JSON file per row. The readers skip a file they cannot parse so the other "
        "rows still render, which is right for one file and silent for the corpus: before this "
        "check a merge conflict written into a row removed that promise from the board, the "
        "knowledge graph and the Quality desk with nothing on any page saying so. This check "
        "reads every fragment family and refuses a file no reader can use — unreadable bytes, "
        "invalid JSON, a value that is not an object, or an object missing the keys its own "
        "reader requires."
    )

    def applies(self, kb: Any) -> bool:
        cfg = PlanningConfig.of(kb)
        knowledge = Path(kb.knowledge)
        return any(d.is_dir() for d, _ in _families(cfg, knowledge)) or bool(_sot_dirs(cfg, knowledge))

    def run(self, kb: Any) -> list[Any]:
        cfg = PlanningConfig.of(kb)
        knowledge = Path(kb.knowledge)
        findings: list[Any] = []
        # A corpus may point two families at one directory; report each broken file once.
        seen: set[Path] = set()
        for directory, problem in _families(cfg, knowledge):
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.json")):
                data, why = _read(path)
                if why is None and data is not None:
                    why = problem(data)
                if why is not None and path not in seen:
                    seen.add(path)
                    findings.append(_finding(path, why))
        for directory in _sot_dirs(cfg, knowledge):
            for path in sorted(directory.glob("*.json")):
                data, why = _read(path)
                if why is None and data is not None:
                    why = _sot_problem(data)
                if why is not None and path not in seen:
                    seen.add(path)
                    findings.append(_finding(path, why))
        return findings


CHECK = KnowledgeFragmentsCheck()
