#!/usr/bin/env python3
"""Is this knowledge base ready to build on? One verdict for the whole repository.

    python3 knowledge/scripts/kb_readiness.py            # the verdict, what stands in the way, what to describe next
    python3 knowledge/scripts/kb_readiness.py --json     # the same reading, as the Knowledge page receives it

The reading itself is `fleet_knowledge.readiness` — one definition of "ready", shared with the
service, which computes the same reading during every corpus sync and draws it at the top of the
Knowledge page. This script supplies it from the local checkout: the tracked files, `git log` over
the window, `.fleet/fleet.toml`, and — only here — the knowledge bootstrap's progress file, which
adds the parts that changed since they were read and the questions that still wait on a person.

Exit code: 0 when ready, 1 when not (so a step can gate on it), 2 when it could not be read.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402
import kb_inventory as inv  # noqa: E402


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=inv.REPO, capture_output=True, text=True, check=True).stdout


def read(overrides: dict[str, float | None]) -> dict[str, Any]:
    _repo.fleet_knowledge()
    from fleet_knowledge import readiness as rd  # noqa: PLC0415 — after the path insert

    toml_path = inv.REPO / ".fleet" / "fleet.toml"
    fleet_toml = toml_path.read_text(encoding="utf-8") if toml_path.is_file() else None
    pol = rd.policy(fleet_toml, overrides)
    commits: list[tuple[str, Sequence[str]]] = list(rd.parse_log(_git(*rd.log_args(pol["days"]))))
    code = list(inv.tracked_files())
    window = f"last {int(pol['days'])} days"
    tracked = {p for p in code if rd.is_code(p)}
    if rd.code_commits(commits, tracked) < rd.MIN_COMMITS:
        # A quiet repository still gets a sample large enough that one commit does not swing it.
        wide = [a for a in rd.log_args(pol["days"]) if not a.startswith("--since")]
        commits, window = rd.newest(rd.parse_log(_git(*wide, f"-n{rd.MIN_COMMITS * 5}")), tracked), rd.WINDOW_COMMITS
    progress = inv.STATE_LAYOUT["progress"]
    return rd.assess(
        inv.KNOWLEDGE,
        code_paths=code,
        commits=commits,
        window=window,
        head=_git("rev-parse", "--short", "HEAD").strip(),
        fleet_toml=fleet_toml,
        progress=progress.read_text(encoding="utf-8") if progress.is_file() else None,
        read_files=inv.ledger_files(),
        overrides=overrides,
    )


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def render(r: dict[str, Any]) -> str:
    f, pol = r["figures"], r["policy"]
    head = {"ready": "READY TO BUILD", "not-ready": "NOT READY YET", "too-little-history": "NOT ENOUGH HISTORY YET"}[
        r["verdict"]
    ]
    out = [
        f"{head} — {_pct(f['coverage'])} of recent code changes land on described parts "
        f"(ready at {_pct(pol['threshold'])})",
        "",
    ]
    if r["blockers"]:
        out += ["What stands in the way:"] + [f"  - {b['text']}" for b in r["blockers"]] + [""]
    by_id = {p["id"]: p for p in r["parts"]}
    if r["describeNext"]:
        out.append("Describe these next, in this order (share of recent change each adds):")
        for pid in r["describeNext"][:12]:
            p = by_id[pid]
            tag = f"no part, {p['files']} files" if p["unmapped"] else "not described"
            out.append(f"  {pid:<36} +{_pct(p['share']):>4}   {tag}")
        if len(r["describeNext"]) > 12:
            out.append(f"  … and {len(r['describeNext']) - 12} more")
        out.append("")
    q = "not checked (no progress file)" if f["questions"] is None else str(f["questions"])
    out += [
        f"Measured over the {r['window']['label']} ({r['window']['commits']} code commits) at {r['head']}.",
        f"{f['described']} of {f['components']} parts described · {_pct(f['owned'])} of code on the map · "
        f"questions for you: {q} · promises checked: {f['promisesChecked']}",
    ]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--json", action="store_true", help="print the reading as the Knowledge page receives it")
    ap.add_argument("--days", type=float, help="the window, in days (default from fleet.toml, else 90)")
    ap.add_argument("--threshold", type=float, help="share of recent change that must be described")
    ap.add_argument("--hotspot", type=float, help="largest share one undescribed part may carry")
    args = ap.parse_args(argv)
    try:
        r = read({"days": args.days, "threshold": args.threshold, "hotspot": args.hotspot})
    except subprocess.CalledProcessError as exc:
        print(f"could not read this repository's history: {exc.stderr or exc}", file=sys.stderr)
        return 2
    print(json.dumps(r, indent=1) if args.json else render(r))
    return 0 if r["verdict"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
