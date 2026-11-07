#!/usr/bin/env python3
"""Check a `questions` result document against 0071's rules before a run ends its turn.

    python3 knowledge/scripts/validate_questions.py path/to/result.json
    python3 knowledge/scripts/validate_questions.py            # $FLEET_RESULT_FILE

A session that needs a person writes a `questions` document to `$FLEET_RESULT_FILE` and
stops. Until this script existed nothing upstream of the database checked the inside of that
array — two to four options, at least one recommended, every option shaped — so a malformed
set was accepted by every layer the session could reach and refused only by 0071's CHECKs on
the service, after the run was over and the session that wrote it was gone. The agent lost its
question and no surface told anybody.

This is the box's half of the fix: run it against the document BEFORE writing the sentinel,
and a violation is a reason the same session can read and correct in the same turn. It calls
the one predicate the service also uses (`fleet_knowledge.questions.validate_questions_shape`),
so the prose, the script and 0071 cannot disagree about the rules.

Exit 0 when the set meets every rule. Exit 1 when it breaks one — the reason is printed, and
it names the constraint (`fleet_question_offers_two_to_four_options`, …). Exit 2 when there is
nothing to check: no path, an unreadable file, or a document that is not `kind: "questions"`.

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

from fleet_knowledge.questions import validate_questions_shape  # noqa: E402


def main() -> int:
    args = sys.argv[1:]
    path = args[0] if args else os.environ.get("FLEET_RESULT_FILE", "")
    if not path:
        print(
            "usage: validate_questions.py <result-file.json>  (or set $FLEET_RESULT_FILE)",
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
    if not isinstance(document, dict) or document.get("kind") != "questions":
        print(f'{path} is not a `questions` result document (no `"kind": "questions"`)', file=sys.stderr)
        return 2
    reason = validate_questions_shape(document)
    if reason is not None:
        print(reason, file=sys.stderr)
        return 1
    print("the question set meets 0071's rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
