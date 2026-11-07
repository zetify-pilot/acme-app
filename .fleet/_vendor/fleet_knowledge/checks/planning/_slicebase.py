"""Which slice rows THIS change wrote, against the base commit — for the area rollout (FLT-1280).

The owner's 2026-10-28 rule: every slice must name an area, and turning that on must never turn a
customer's build red. So a row this change ADDED or CHANGED without an area fails, and a row it left
untouched is only noted. That needs the one fact this module answers: was this row written here?

The base is the commit the history-dependent checks already compare against (`kb.git.base`, the PR
base in CI), else `PlanningConfig.default_diff_base` (`origin/main`). **No base, no answer**
(`available` is False): every row then reads as untouched, which is the side that never fails a build
— git absence is never a violation (`_git`'s rule).

`in_repository` says which kind of "no answer" this is. A corpus with no git at all (a tarball copy)
can never compare, so a caller that needs the comparison must stay advisory. A git checkout whose
base commit is missing (a shallow CI clone, an unfetched base branch) COULD compare if the base were
fetched, so the `areas` planning rule fails closed there instead of noting the gap (ENG-21061).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fleet_knowledge.config import git_context
from fleet_knowledge.planningmode import split_home_cell

from ._git import changed_paths, git, git_out, is_repository


class SliceBase:
    """The base commit's view of the slice register, read once per check run."""

    def __init__(self, kb: Any, default_base: str) -> None:
        self.root = Path(kb.root)
        #: Whether this root sits inside a git work tree. Distinguishes "no git at all" (stay
        #: advisory) from "a git checkout whose base is missing" (the `areas` rule fails closed).
        self.in_repository = is_repository(self.root)
        base = git_context(kb).base or default_base
        changed = changed_paths(self.root, base) if base else None
        self.base = base if changed is not None else ""
        self._changed: set[str] = set(changed or ())
        if self.base:
            # A fragment nobody has staged yet is a row this change wrote, too: `git diff` cannot see it.
            self._changed |= {
                ln for ln in git_out(self.root, "ls-files", "--others", "--exclude-standard").splitlines() if ln
            }
        self._base_text: dict[str, str | None] = {}

    @property
    def available(self) -> bool:
        return bool(self.base)

    def _rel(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.root.resolve()))
        except ValueError:
            return str(path)

    def text_at_base(self, path: Path) -> str | None:
        """`path`'s text on the base commit, or None when it did not exist there."""
        rel = self._rel(path)
        if rel not in self._base_text:
            self._base_text[rel] = git(self.root, "show", f"{self.base}:{rel}") if self.base else None
        return self._base_text[rel]

    def written_here(self, row: dict[str, Any], register: Path) -> bool:
        """Whether this change added or edited `row`. False whenever there is no base to compare."""
        if not self.base:
            return False
        source = row.get("source")
        if isinstance(source, Path):
            return self._rel(source) in self._changed
        if self._rel(register) not in self._changed:
            return False
        # A table row: changed when its own line is not on the base commit, byte for byte.
        try:
            line = register.read_text(encoding="utf-8").splitlines()[int(row.get("line") or 0) - 1]
        except (OSError, IndexError, ValueError):
            return True
        before = self.text_at_base(register)
        return before is None or line not in before.splitlines()

    def program_at_base(self, row: dict[str, Any], register: Path) -> str | None:
        """The program `row` named on the base commit: `""` for none, None when the row was not there
        (or there is no base). Step 4 (FLT-1282) compares it: in `areas` mode a program takes no slice it
        did not already hold."""
        if not self.base:
            return None
        source = row.get("source")
        if isinstance(source, Path):
            text = self.text_at_base(source)
            if text is None:
                return None
            try:
                data = json.loads(text)
            except ValueError:
                return None
            return str(data.get("program") or "").strip() if isinstance(data, dict) else None
        text = self.text_at_base(register)
        if text is None:
            return None
        for line in text.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and cells[0] == row.get("id") and len(cells) > 3:
                return split_home_cell(cells[3].strip("`"))[0]
        return None

    def row_existed(self, row: dict[str, Any], register: Path) -> bool:
        """Whether a program (or any) row was already on the base commit: its fragment existed there, or its
        id opened a row of the register there. False with no base."""
        if not self.base:
            return False
        source = row.get("source")
        if isinstance(source, Path):
            return self.text_at_base(source) is not None
        text = self.text_at_base(register)
        rid = str(row.get("id") or "")
        return bool(text) and any(
            [c.strip() for c in ln.strip().strip("|").split("|")][:1] == [rid] for ln in (text or "").splitlines()
        )
