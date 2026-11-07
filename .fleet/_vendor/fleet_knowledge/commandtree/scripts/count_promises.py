#!/usr/bin/env python3
"""Count the promises the QA Desk will see in this checkout's corpus.

    python3 knowledge/scripts/count_promises.py                    # one integer
    python3 knowledge/scripts/count_promises.py --knowledge knowledge

Every id a check result's `promise` may name — each register row, each capability in the
feature maps, each journey criterion not retired — read off the corpus on disk by
`fleet_knowledge.quality.corpus_promise_ids`. `knowledge:bootstrap` reports this number when a
bootstrap finishes.

A shipped script rather than the `python3 -c "from fleet_knowledge …"` one-liner it replaces,
because a one-liner imports the package with whatever bare `python3` the session has and nothing
else. On a packaged worker that is the HOST interpreter (the release `bin/` is LAST on a
session's PATH, so a repository's own tools win over the bundle's), which has no
`fleet_knowledge`; a shipped script goes through
`_repo.fleet_knowledge()`, which finds the package installed, in the `fleet/` submodule, or by
re-executing under the release interpreter the daemon exports as `$FLEET_PYTHON`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--knowledge", default="knowledge", help="the corpus directory (default: knowledge)")
    args = parser.parse_args(argv)
    _repo.fleet_knowledge()
    from fleet_knowledge.quality import corpus_promise_ids  # noqa: PLC0415 — after the path insert

    print(len(corpus_promise_ids(Path(args.knowledge))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
