#!/usr/bin/env python3
"""Where new slices go in this repository, and the feature areas a slice may live under.

    python3 knowledge/scripts/planning_mode.py            # prints `programs` or `areas`
    python3 knowledge/scripts/planning_mode.py --areas    # one line per area: `<slug>\\t<components>`

Every slice names a feature area (`area`); a program (`program`) is optional, older membership. The
repository's `.fleet/fleet.toml` says whether NEW work also joins a program:

    [fleet.planning]
    mode = "areas"        # absent means "programs"
    require_area = true   # every LIVE slice without an area fails the check (finished and withdrawn
                          # slices never do); absent: only a new or changed slice without one fails

Absent means `programs`, so every repository set up before the setting behaves exactly as it always
did; only a fresh `fleet init` writes either key. `route` and the slice commands read this to decide
where a new slice goes; neither key ever makes an existing row unreadable.

It derives; it never decides. Exit 0 either way; callers route on the output.
Stdlib only, like every sibling: the reading is `fleet_knowledge.planningmode`'s.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    _repo.fleet_knowledge()
    from fleet_knowledge import config as kb_config  # noqa: PLC0415 — resolved after the path insert
    from fleet_knowledge import planningmode  # noqa: PLC0415

    repo = _repo.repo_root()
    kb = kb_config.resolve(cwd=repo)
    if "--areas" in args:
        features = str(getattr(kb.config, "features_dir", "") or "features")
        for slug, components in sorted(planningmode.feature_areas(kb.knowledge, features).items()):
            print(f"{slug}\t{', '.join(components) or '-'}")
        return 0
    print(planningmode.mode_of(kb.config.planning))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
