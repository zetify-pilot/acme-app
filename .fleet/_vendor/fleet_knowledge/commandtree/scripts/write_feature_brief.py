#!/usr/bin/env python3
"""Write the brief of an existing feature and sort its capability rows into uses — "Write the brief" on its page.

    python3 knowledge/scripts/write_feature_brief.py --area payments \\
        --brief-json '{"summary": "...", "problem": "...", "example": "...", "example_from": [], "not": ["..."]}' \\
        --uses-json '[{"name": "Pay an invoice", "paragraph": "...", "rows": ["<row id>", "<row id>"]}]'

The brief goes into the map's frontmatter (replacing one that was there). Each use becomes a `###` section of
`## Capabilities` holding exactly the rows it names: rows are regrouped, never reworded, renumbered or dropped, and
every live row of the map goes in exactly one use. `### Misfits (to move)` and `### Retired` stay as they are, and any
note that sat between the old tables moves whole to a `## Notes` section after `## Capabilities`.

`slice:create` runs this from an accepted proposal of kind `brief` (it carries `featureBrief`). It prints the file it
wrote and exits 0; it exits 2 with one sentence on stderr when the brief cannot be written (no such feature, a row named
twice or not at all, a row the map does not hold, a use count the map's check refuses, a brief that states ship-state or
names an internal id bare) — the sentence the run refuses with, never a map it would have had to invent.

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
    parser.add_argument(
        "--brief-json",
        required=True,
        dest="brief_json",
        help='the brief as one JSON object: {"summary", "problem", "example", "example_from": [...], "not": [...]}',
    )
    parser.add_argument(
        "--uses-json",
        required=True,
        dest="uses_json",
        help='the uses as a JSON list: [{"name", "paragraph", "rows": ["<row id>", ...]}, ...]',
    )
    args = parser.parse_args(argv)
    _repo.fleet_knowledge()
    from fleet_knowledge import config as kb_config  # noqa: PLC0415 — resolved after the path insert
    from fleet_knowledge import featuremap  # noqa: PLC0415

    repo = _repo.repo_root()
    kb = kb_config.resolve(cwd=repo)
    features = str(getattr(kb.config, "features_dir", "") or "features")
    prefix = str(getattr(kb.config, "capability_prefix", "") or "CAP")
    try:
        written = featuremap.write_brief(
            kb.knowledge,
            slug=args.area,
            brief=featuremap.brief_from_json(args.brief_json),
            uses=featuremap.uses_from_json(args.uses_json),
            features_dir=features,
            cap_prefix=prefix,
        )
    except featuremap.NewAreaRefusedError as refused:
        print(str(refused), file=sys.stderr)
        return 2
    for path in written:
        print(path.relative_to(repo) if path.is_relative_to(repo) else path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
