#!/usr/bin/env python3
"""Judge one QA scenario's citations before a run records its verdicts.

    python3 knowledge/scripts/qa_scenario_gate.py <scenario-id> --promises <id,id,...>

Every promise the run records — the scenario's own promise and each rider that rides the run —
must have an assertion row in the named scenario, and no row may cite a bare journey id: a
scenario proves a journey STEP (`<journey>#<n>`), because only a step counts on the Quality
desk. The rule is `fleet_knowledge.quality.scenario_citation_problems`, so the gate and
`fleet check`'s `scenario-journey-step` cannot drift.

Only the named scenario is judged, even when another scenario in the corpus breaks the rule:
the run fixes the file it wrote, not somebody else's. `--promises` may be empty, and then only
the bare-journey rule applies.

This is a gate, not a warning: an unreadable `fleet_knowledge`, an unknown scenario id or any
problem exits non-zero, and the problems are printed to stderr.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402


def _promises(raw: str) -> list[str]:
    """The `--promises` value as ids, dropping empty pieces from a trailing or doubled comma."""
    return [part.strip() for part in raw.split(",") if part.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scenario", help="the scenario id to judge (its `id:` frontmatter)")
    parser.add_argument(
        "--promises",
        default="",
        help="the promise and riders this run records, comma-separated (default: none)",
    )
    args = parser.parse_args(argv)
    try:
        _repo.fleet_knowledge()
    except SystemExit as exc:
        print(f"qa_scenario_gate: cannot read fleet_knowledge: {exc}", file=sys.stderr)
        return 1
    from fleet_knowledge import corpus, quality  # noqa: PLC0415 — after the path insert

    root = _repo.repo_root()
    row = next((r for r in quality.read_scenarios(root) if str(r.get("id") or "") == args.scenario), None)
    if row is None:
        print(
            f"qa_scenario_gate: no scenario {args.scenario!r} under {root / 'knowledge' / 'scenarios'}",
            file=sys.stderr,
        )
        return 1
    journey_ids = {path.stem for path, _tier in corpus.journey_files(root / "knowledge")}
    problems = quality.scenario_citation_problems(row, journey_ids, required=_promises(args.promises))
    for problem in problems:
        print(f"qa_scenario_gate: {row.get('file') or args.scenario}: {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
