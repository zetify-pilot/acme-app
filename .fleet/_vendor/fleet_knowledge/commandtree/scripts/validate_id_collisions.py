#!/usr/bin/env python3
"""Id-collision detection against main tip AND open peer PRs, plus authoring-time allocation.

The logic lives in `fleet_knowledge.checks.planning.id_collisions`, which is repository-agnostic
and auto-discovered by the kit's runner. This file stays because pre-commit and CI call it by
path; it produces the same stdout and the same exit codes it always did.

Run:
  python3 knowledge/scripts/validate_id_collisions.py                  (check vs main tip + open peers)
  python3 knowledge/scripts/validate_id_collisions.py --tip <REF>      (explicit main tip, e.g. CI base.sha)
  python3 knowledge/scripts/validate_id_collisions.py --allocate RUN 5 (reserve the next 5 RUN ids)
  python3 knowledge/scripts/validate_id_collisions.py --claim (reserve an id already written)
  python3 knowledge/scripts/validate_id_collisions.py --claim-existing (back-fill claims for held ids)
Exit 1 on any collision or (in CI) any unclaimed new id; exit 3 when a claim cannot reach GitHub.

Ids are reserved as `refs/ids/<ID>` on GitHub — an atomic create that answers HTTP 422 to the
second caller — when the corpus sets `[fleet.planning] id_claims = true`. The token comes from
the environment `gh` already reads (GH_TOKEN / GITHUB_TOKEN or its keyring), never from argv.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

_repo.fleet_knowledge()
from fleet_knowledge.checks.planning import id_collisions  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="validate_id_collisions", description=__doc__)
    p.add_argument(
        "--tip",
        help="commit to treat as `origin/main`'s tip (default: origin/main). CI passes the PR base sha",
    )
    p.add_argument(
        "--head",
        help="commit whose ids are THIS branch's (default: the working tree). CI passes the PR "
        "head sha because its checkout sits at the merge ref, not the branch head",
    )
    p.add_argument(
        "--peers",
        help="comma-separated peer head SHAs to treat as open PRs (test/CI escape hatch; "
        "default: `gh pr list --state open`). Self SHA is still excluded.",
    )
    p.add_argument(
        "--allocate",
        nargs=2,
        metavar=("PREFIX", "COUNT"),
        help="reserve the next COUNT free ids under PREFIX (e.g. RUN 5): the floor clears main tip, "
        "open peers, the local tree and every claim ref, then each id is claimed atomically on GitHub "
        "(a taken claim moves to the next number). No tree writes.",
    )
    p.add_argument(
        "--claim",
        nargs="+",
        metavar="ID",
        help="reserve ids already written into this change (offline authoring, or a branch that "
        "allocated before claims existed). A taken claim is reported, not failed.",
    )
    p.add_argument(
        "--claim-existing",
        action="store_true",
        help="back-fill a claim for every id main's tip and every open peer PR already holds; idempotent",
    )
    args = p.parse_args(list(sys.argv[1:] if argv is None else argv))
    kb = _repo.knowledge_base()
    if args.claim:
        return int(id_collisions.cli_claim(kb, ids=list(args.claim), tip=args.tip))
    if args.claim_existing:
        return int(id_collisions.cli_claim_existing(kb, tip=args.tip, peers=args.peers))
    if args.allocate is not None:
        return int(
            id_collisions.cli_allocate(
                kb,
                prefix=str(args.allocate[0]),
                count_raw=str(args.allocate[1]),
                tip=args.tip,
                peers=args.peers,
            )
        )
    return int(id_collisions.cli_check(kb, tip=args.tip, head=args.head, peers=args.peers))


if __name__ == "__main__":
    raise SystemExit(main())
