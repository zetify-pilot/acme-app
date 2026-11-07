#!/usr/bin/env python3
"""Write a new feature area's map — the smallest one this repository's checks pass — and list it in the index.

    python3 knowledge/scripts/new_feature_area.py --slug billing --name "Billing" \\
        --sentence "A customer is billed for what they use, and can see why." \\
        --component billing-service --source-of-truth internal/billing/ [--spec architecture/overview.md] \\
        [--use "See what was billed|Read each charge on an invoice and the usage behind it."]

Each `--use "Name|Paragraph"` becomes a `###` section of `## Capabilities` — a thing a person can do with the
feature, its one plain paragraph and an empty table. `--brief-json` is the map's `brief:` as one JSON object —
`{"summary": "...", "problem": "...", "example": "...", "example_from": ["journey-slug"], "not": ["..."]}`; a key
not given is written empty, and the `feature-briefs` check fails a map a change adds until its brief is complete.
An unknown key, a value of the wrong type or JSON that does not parse is refused (exit 2), never guessed.

`slice:create` runs this from an accepted proposal that carries `newArea`: the map and the first slice's
row land in one pull request. It prints each file it wrote, one per line, and exits 0; it exits 2 with one sentence
on stderr when the area cannot be written (a taken slug, no component, a source path that does not exist, a corpus
with no feature map yet) — the sentence the run refuses with, never a map it would have had to invent.

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
    parser.add_argument("--slug", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--sentence", required=True)
    parser.add_argument("--component", action="append", default=[])
    parser.add_argument("--source-of-truth", action="append", default=[], dest="source_of_truth")
    parser.add_argument("--spec", action="append", default=[])
    parser.add_argument("--use", action="append", default=[], help='a use, as "Name|Paragraph" (repeatable)')
    parser.add_argument(
        "--brief-json",
        default="",
        dest="brief_json",
        help='the brief as one JSON object: {"summary", "problem", "example", "example_from": [...], "not": [...]}',
    )
    args = parser.parse_args(argv)
    _repo.fleet_knowledge()
    from fleet_knowledge import config as kb_config  # noqa: PLC0415 — resolved after the path insert
    from fleet_knowledge import featuremap  # noqa: PLC0415

    repo = _repo.repo_root()
    kb = kb_config.resolve(cwd=repo)
    features = str(getattr(kb.config, "features_dir", "") or "features")
    try:
        brief = featuremap.brief_from_json(args.brief_json) if args.brief_json else None
        written = featuremap.write_new_area(
            repo,
            kb.knowledge,
            slug=args.slug,
            name=args.name,
            sentence=args.sentence,
            components=args.component,
            source_of_truth=args.source_of_truth,
            specs=args.spec,
            features_dir=features,
            uses=[(u.partition("|")[0], u.partition("|")[2]) for u in args.use],
            brief=brief,
        )
    except featuremap.NewAreaRefusedError as refused:
        print(str(refused), file=sys.stderr)
        return 2
    for path in written:
        print(path.relative_to(repo) if path.is_relative_to(repo) else path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
