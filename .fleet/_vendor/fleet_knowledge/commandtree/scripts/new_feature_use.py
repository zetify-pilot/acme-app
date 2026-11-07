#!/usr/bin/env python3
"""Add a new thing an existing feature does — one use — to the feature's map, with an empty table.

    python3 knowledge/scripts/new_feature_use.py --area payments --name "Refund a payment" \\
        --paragraph "Give a customer their money back when a payment was wrong, and see the refund settle."

The use becomes a `###` section of the map's `## Capabilities`, after the feature's last use: its name, its one plain
paragraph and an empty capability table. No row is written — the use's work arrives with the plan made for it from
the feature's page.

`slice:create` runs this from an accepted proposal that carries `newUse`. It prints the file it wrote and exits 0; it
exits 2 with one sentence on stderr when the use cannot be added (no such feature, a name the feature already has, a
paragraph that states ship-state or names an internal id bare, a feature that already does as many things as one
takes) — the sentence the run refuses with, never a use it would have had to invent.

Stdlib only, like every sibling: the writing is `fleet_knowledge.featuremap`'s.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--area", required=True, help="the feature's slug")
    parser.add_argument("--name", required=True, help="the use's name, as the feature page shows it")
    parser.add_argument("--paragraph", required=True, help="one plain paragraph: what a person does with it")
    args = parser.parse_args(argv)
    _repo.fleet_knowledge()
    from fleet_knowledge import config as kb_config  # noqa: PLC0415 — resolved after the path insert
    from fleet_knowledge import featuremap  # noqa: PLC0415

    repo = _repo.repo_root()
    kb = kb_config.resolve(cwd=repo)
    features = str(getattr(kb.config, "features_dir", "") or "features")
    try:
        written = featuremap.add_use(
            kb.knowledge, slug=args.area, name=args.name, paragraph=args.paragraph, features_dir=features
        )
    except featuremap.NewAreaRefusedError as refused:
        print(str(refused), file=sys.stderr)
        return 2
    for path in written:
        print(path.relative_to(repo) if path.is_relative_to(repo) else path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
