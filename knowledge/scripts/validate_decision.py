#!/usr/bin/env python3
"""Check a `decision` result document against the interview card before a run parks on a person.

    python3 knowledge/scripts/validate_decision.py path/to/result.json
    python3 knowledge/scripts/validate_decision.py            # $FLEET_RESULT_FILE

A run that cannot continue without a person's ruling ends `needs-decision` and writes ONE
`decision` document to `$FLEET_RESULT_FILE`: a brief (what the work is, one concrete example,
what stopped the run, what is at stake), the context the question leans on (each acceptance
criterion, requirement or issue it names, quoted), and two to four options — the recommended one
first, each with why, cost and then. The person clearing `Blocked · decision` reads that card and
nothing else; they have not opened the issue, the PRD or any register.

The service checks the same document when the run reports, with the same predicate
(`fleet_knowledge.decisions.decision_refusals`), and records every broken rule on the park as
`askRefused` — but by then the session that could have fixed it is gone. Run this BEFORE the
done-sentinel and every reason is one the same session can fix in the same turn.

Exit 0 when the document meets the card. Exit 1 when it breaks a rule — every reason is printed,
one per line, each naming its rule (`decision-bare-id`, …). Exit 2 when there is nothing to check:
no path, an unreadable file, or a document that is not `kind: "decision"`.

Stdlib only, like every sibling script.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

_repo.fleet_knowledge()

from fleet_knowledge.decisions import decision_refusals  # noqa: E402


def main() -> int:
    args = sys.argv[1:]
    path = args[0] if args else os.environ.get("FLEET_RESULT_FILE", "")
    if not path:
        print(
            "usage: validate_decision.py <result-file.json>  (or set $FLEET_RESULT_FILE)",
            file=sys.stderr,
        )
        return 2
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"cannot read {path}: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"{path} is not JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(document, dict) or document.get("kind") != "decision":
        print(f'{path} is not a `decision` result document (no `"kind": "decision"`)', file=sys.stderr)
        return 2
    reasons = decision_refusals(document)
    if reasons:
        for reason in reasons:
            print(f"- {reason}", file=sys.stderr)
        return 1
    print("the decision meets the interview card")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
