#!/usr/bin/env python3
"""Resolve repo paths to the component(s) that own them.

    python3 knowledge/scripts/component_of.py internal/auditlog/store.go frontend/apps/admin/src/x.tsx
    python3 knowledge/scripts/component_of.py --list

Reads ownership from the component registry's `owns:` column
(knowledge/specs/architecture/components.md) and answers by LONGEST-prefix match,
one line per input path: `<path>\t<component-id>` (or `-` when nothing claims it).

Why this exists: bugs, tasks and audits are Linear-native — no git file, so nothing
ever connected 81% of issue volume to the component architecture. The issue-creating
commands call this to derive the `Component` label at CREATE time, which is what makes
"all work on the audit log, PRD or not" an answerable query.

Unclaimed is a real answer, not an error: the registry deliberately leaves some code
unassigned (see components.md → "Unassigned code"). Exit code is 0 either way; callers
route on the output, not the exit code.

Stdlib only, like every sibling validator.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

REPO = _repo.repo_root()
REGISTRY = REPO / "knowledge" / "specs" / "architecture" / "components.md"
CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")


def owners() -> dict[str, str]:
    """{owned path prefix -> component id} from the registry table."""
    out: dict[str, str] = {}
    if not REGISTRY.is_file():
        return out
    in_sec = False
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_sec = line.strip() == "## Components"
            continue
        if not in_sec or not line.strip().startswith("|"):
            continue
        c = [x.strip().replace("\\|", "|") for x in CELL_SPLIT_RE.split(line.strip().strip("|"))]
        if len(c) < 4 or c[0].lower() == "id" or not (set(c[0]) - set("-: ")):
            continue
        for p in (x.strip() for x in c[3].split(",") if x.strip()):
            out[p.rstrip("/")] = c[0]
    return out


def component_of(path: str, own: dict[str, str]) -> str | None:
    """Longest-prefix owner of `path`, or None. Exact file claims win over dirs."""
    norm = path.strip().lstrip("./").rstrip("/")
    best: tuple[int, str] | None = None
    for prefix, cid in own.items():
        hit = norm == prefix or norm.startswith(prefix + "/")
        if hit and (best is None or len(prefix) > best[0]):
            best = (len(prefix), cid)
    return best[1] if best else None


def main() -> int:
    args = sys.argv[1:]
    own = owners()
    if not args or args[0] in ("--list", "-l"):
        for prefix, cid in sorted(own.items()):
            print(f"{prefix}\t{cid}")
        return 0
    for path in args:
        resolved = component_of(path, own)
        print(f"{path}\t{resolved or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
