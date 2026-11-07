#!/usr/bin/env python3
"""Remove one use from a feature and keep its history — "Remove this use…" on the feature's page.

    python3 knowledge/scripts/remove_feature_use.py --area payments --name "Refund a payment" \\
        --reason "Refunds now go through the bank, not through us."

The use's `###` section leaves the map's `## Capabilities`, and every capability table it held moves whole, byte for
byte, to the map's `### Retired` section: what is built stays on the page as retired, and nothing is deleted. Every
plan the use's rows cite (or that names the use as its `use:`) and that is not built yet is cancelled the way
`prd:cancel` cancels it, with the reason as its `cancelled_reason:`. A shipped plan, an already-cancelled one, and one
another use still cites are left as they are.

`slice:create` runs this from an accepted removal (`kind: removal` carrying `removeUse`). It prints each file it wrote,
then one JSON line `{"retired": [row ids], "cancelled": [plan numbers], "kept": [plan numbers]}`, and exits 0. It
exits 2 with one sentence on stderr when the use cannot be removed (no such feature or use, a map rendered from
templates, a feature that would be left with too few uses), and 3 when work under the use is being built right now:
that is the person's call, and `--stop-work-being-built` is passed only once they have said to stop it.

Stdlib only, like every sibling: the writing is `fleet_knowledge.featuremap`'s.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--area", required=True, help="the feature's slug")
    parser.add_argument("--name", required=True, help="the use's name, as the feature page shows it")
    parser.add_argument("--reason", required=True, help="the person's reason, kept with every plan it cancels")
    parser.add_argument(
        "--stop-work-being-built", action="store_true", help="the person said to stop the work being built under it"
    )
    args = parser.parse_args(argv)
    _repo.fleet_knowledge()
    from fleet_knowledge import config as kb_config  # noqa: PLC0415 — resolved after the path insert
    from fleet_knowledge import featuremap  # noqa: PLC0415

    repo = _repo.repo_root()
    kb = kb_config.resolve(cwd=repo)
    features = str(getattr(kb.config, "features_dir", "") or "features")
    prds = str(getattr(kb.config, "prds_dir", "") or "prds")
    try:
        done = featuremap.remove_use(
            kb.knowledge,
            slug=args.area,
            name=args.name,
            reason=args.reason,
            features_dir=features,
            prds_dir=prds,
            stop_work_being_built=args.stop_work_being_built,
        )
    except featuremap.WorkBeingBuiltError as building:
        print(str(building), file=sys.stderr)
        return 3
    except featuremap.NewAreaRefusedError as refused:
        print(str(refused), file=sys.stderr)
        return 2
    for path in done.written:
        print(path.relative_to(repo) if path.is_relative_to(repo) else path)
    print(json.dumps({"retired": done.retired, "cancelled": done.cancelled, "kept": done.kept}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
