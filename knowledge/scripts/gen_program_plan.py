#!/usr/bin/env python3
"""Plan backwards from a goal: what must exist for this program to be true?

    python3 knowledge/scripts/gen_program_plan.py <PG-NN>
    python3 knowledge/scripts/gen_program_plan.py --list

The working-backwards chain (knowledge/specs/knowledge-model.md):

    GOAL (a program — a row in knowledge/programs.md)
      `Requires` = the ROOTS of its decomposition — capability ids, authored by
      the `program:decompose` command (mostly gap rows the decomposition created)
        -> transitive closure over capability `Needs` edges (the 4th DAG)
          -> each capability classified: built / unproven / in flight / GAP / retired
            -> gaps ordered by the Needs DAG = the build order
    plus the `## Program-specific work` section of the program's OPTIONAL detail file
    (knowledge/programs/PG-NN.md) — customer/release-specific items that are deliberately
    NOT ledger rows (they are not durable product capabilities).

Everything is derived from the registries, so it cannot drift — re-run it and the
answer is current.

Why roots, not areas: `requires: [agent-apps]` means "everything ever recorded under
this heading" — a lookup into the past, not a decomposition of the goal. Tested on a
real goal it produced "2 gaps" where ground truth was 22 (recall ~5%). Area entries
are still accepted but reported as COARSE — they answer "what does the platform have
here", never "what does this goal need".

Classification is anchor-aware: a row citing a shipped PRD but carrying
`Anchor: UNVERIFIED` is reported as UNPROVEN, not built — the measured false-built
rate on unanchored claims was ~16-33%.

Stdlib only, matching the other knowledge validators.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

REPO = _repo.repo_root()
K = REPO / "knowledge"
REGISTRY = K / "specs" / "architecture" / "components.md"

# One reader for the program register, shared with the validator and the browser.
_KR = Path(__file__).resolve().parent / "knowledge_registers.py"
_spec = importlib.util.spec_from_file_location("_gpp_registers", _KR)
assert _spec and _spec.loader
kr: Any = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("_gpp_registers", kr)
_spec.loader.exec_module(kr)
TERMINAL = {"shipped", "cancelled"}

# Capability ids are OPAQUE since 2026-08-18: `CAP-NNNN`, one flat global namespace,
# encoding nothing (knowledge/capability-aliases.md). Area membership is which file the
# row lives in — never the id.
CAP_ID_RE = re.compile(r"^CAP-\d{4}$")
CAP_REF_RE = re.compile(r"CAP-\d{4}")
PRD_NUM_RE = re.compile(r"\b(\d{4})\b")
# `Ships in` marker vocabulary — see knowledge/features/README.md. The planner reads
# ABSENCE as "build this", so any marker it fails to recognise becomes reported work.
BUILT_RE = re.compile(r"^\((core|shipped)\)", re.I)
RETIRED_RE = re.compile(r"^\(retired\)", re.I)
UNVERIFIED = "UNVERIFIED"
# Split markdown rows on UNESCAPED pipes only — `\|` is a literal pipe in a cell.
CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")

# PRD status -> the command that advances it. Everything before `planned` is
# planning-pipeline work; the PLANNING QUEUE section derives "what to plan next"
# from frontmatter each run, so multi-session planning needs no stored progress —
# the status flip a planning session commits IS the progress.
NEXT_VERB = {
    "stub": "prd:create",
    "prd-drafted": "prd:design",
    "designed": "prd:plan",
}


def cells(line: str) -> list[str]:
    return [c.strip().replace("\\|", "|") for c in CELL_SPLIT_RE.split(line.strip().strip("|"))]


def frontmatter(text: str) -> str:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else ""


def field(fm: str, name: str) -> str:
    m = re.search(rf"^{name}:\s*(.+)$", fm, re.M)
    return m.group(1).strip().strip("\"'") if m else ""


def listfield(fm: str, name: str) -> list[str]:
    m = re.search(rf"^{name}:\s*\[(.*?)\]", fm, re.M)
    if not m or not m.group(1).strip():
        return []
    return [x.strip().strip("\"'") for x in m.group(1).split(",") if x.strip()]


def load_components() -> dict[str, dict[str, Any]]:
    """id -> {layer, owns, depends_on} from the registry's `## Components` table."""
    out: dict[str, dict[str, Any]] = {}
    if not REGISTRY.is_file():
        return out
    in_sec = False
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_sec = line.strip() == "## Components"
            continue
        if not in_sec or not line.strip().startswith("|"):
            continue
        c = cells(line)
        if len(c) < 2 or c[0].lower() == "id" or not (set(c[0]) - set("-: ")):
            continue
        out[c[0]] = {
            "layer": c[1],
            "owns": [p.strip() for p in c[2].split(",") if p.strip()] if len(c) > 2 else [],
            "depends_on": [d.strip() for d in c[3].split(",") if d.strip()] if len(c) > 3 else [],
        }
    return out


def load_capabilities() -> dict[str, dict[str, Any]]:
    """Global capability registry: id -> {area, title, prds, built, retired, anchor, needs}."""
    out: dict[str, dict[str, Any]] = {}
    for p in sorted((K / "features").glob("*.md")):
        if p.stem == "README":
            continue
        text = p.read_text(encoding="utf-8")
        comps = listfield(frontmatter(text), "components")
        for line in text.splitlines():
            if not line.lstrip().startswith("|"):
                continue
            cols = cells(line)
            if len(cols) < 3 or not CAP_ID_RE.match(cols[0]):
                continue
            ships = cols[2]
            anchor = (cols[4] if len(cols) > 4 else "").strip().strip("`")
            out[cols[0]] = {
                "area": p.stem,
                "components": comps,
                "title": re.sub(r"\*\*|`|_", "", cols[1]).split("—")[0].strip()[:58],
                "prds": PRD_NUM_RE.findall(ships),
                "built": bool(BUILT_RE.match(ships)),
                "retired": bool(RETIRED_RE.match(ships)),
                "unverified": anchor == UNVERIFIED,
                # a REAL anchor (not blank, not em-dash, not UNVERIFIED) — the only
                # state in which a built-claim is verified against code
                "anchored": bool(anchor) and anchor not in ("—", "-") and anchor != UNVERIFIED,
                "needs": CAP_REF_RE.findall(cols[5]) if len(cols) > 5 else [],
            }
    return out


def load_prd_status() -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted((K / "prds").glob("*/prd.md")):
        fm = frontmatter(p.read_text(encoding="utf-8"))
        if num := field(fm, "prd"):
            out[num.zfill(4)] = field(fm, "status")
    return out


def load_prd_depends() -> dict[str, list[str]]:
    """PRD num -> its own `depends_on:` frontmatter entries (zfilled)."""
    out: dict[str, list[str]] = {}
    for p in sorted((K / "prds").glob("*/prd.md")):
        fm = frontmatter(p.read_text(encoding="utf-8"))
        if num := field(fm, "prd"):
            out[num.zfill(4)] = [d.zfill(4) for d in listfield(fm, "depends_on")]
    return out


def norm_proof(entry: str) -> str:
    """One `Verified by` entry in its canonical spelling.

    A PRD number is zero-padded to four digits; a `drill:<stem>` entry names a record under
    `knowledge/drills/` and is never a PRD — padding it, or looking it up in the PRD status
    map, would report a real proof as `missing`.
    """
    return f"drill:{kr.drill_stem(entry)}" if kr.is_drill(entry) else entry.zfill(4)


def proof_reading(entry: str, pst: dict[str, str], drills: dict[str, dict[str, Any]]) -> str:
    """What one proof entry reads as: a PRD's `status:`, or a drill record's `verdict:`.

    Same rule as `fleet_knowledge.rollup.proof_shipped` — a drill counts only on
    `verdict: passed`; a record that is absent, is not a `drill-record`, or carries no
    verdict reads as such rather than as a PRD that happens to be missing.
    """
    if not kr.is_drill(entry):
        return pst.get(entry, "missing")
    record = drills.get(kr.drill_stem(entry))
    if record is None:
        return "no record"
    if record.get("type") != "drill-record":
        return "not a drill record"
    return str(record.get("verdict") or "no verdict")


def goal_specific_work(body: str) -> list[str]:
    """Items under the program's `## Program-specific work` section — work that is
    deliberately NOT ledger rows (customer/release-specific, not durable product
    capability). It reaches the delivery view as PRDs/tasks in the program's own slice."""
    m = re.search(r"^##\s+Program-specific work\s*$(.*?)(?=^##\s|\Z)", body, re.M | re.S)
    if not m:
        return []
    return [ln.strip()[2:].strip() for ln in m.group(1).splitlines() if ln.strip().startswith("- ")]


def classify(c: dict[str, Any], pst: dict[str, str]) -> str:
    """A built-claim is only `built` when its Anchor verifies it against code.

    An anchorless claim is `unanchored`, NOT built: the measured false-built rate on
    unverified claims is 16-33%, and counting them as built would punish the honest
    UNVERIFIED marker while rewarding the blank cell — the exact inversion that made
    an earlier plan report "2 gaps" against a ground truth of 22."""
    if c["retired"]:
        return "retired"
    if c["built"] or any(pst.get(n) == "shipped" for n in c["prds"]):
        if c["anchored"]:
            return "built"
        return "unproven" if c["unverified"] else "unanchored"
    if c["prds"]:
        return "in-flight"
    return "gap"


def toposort(ids: set[str], needs_of: dict[str, list[str]]) -> list[str]:
    """Dependencies first; name-stable."""
    order: list[str] = []
    seen: set[str] = set()

    def visit(n: str, stack: frozenset[str]) -> None:
        if n in seen or n in stack:
            return
        for d in sorted(needs_of.get(n, [])):
            if d in ids:
                visit(d, stack | {n})
        seen.add(n)
        order.append(n)

    for n in sorted(ids):
        visit(n, frozenset())
    return order


def main() -> int:
    args = sys.argv[1:]
    programs = {p["id"]: p for p in kr.programs()}

    if not args or args[0] in ("--list", "-l"):
        print("goals (programs):\n")
        for pid, p in programs.items():
            mark = f"{len(p['requires'])} requires" if p["requires"] else "no `Requires` (not yet decomposed)"
            print(f"  {pid:<7} {p['kind']:<9} {mark:<34} {p['title']}")
        print("\nusage: gen_program_plan.py <PG-NN>")
        return 0

    pid = args[0].upper()
    if pid not in programs:
        print(f"no program `{args[0]}`. Try --list.")
        return 2

    prog = programs[pid]
    requires = prog["requires"]
    verified_by = [norm_proof(v) for v in prog["verified_by"]]
    # The PRD half of the proof — the only entries the PRD status map and the planning
    # queue can say anything about. A drill is read from its own record below.
    proof_prds = [v for v in verified_by if not kr.is_drill(v)]
    # `## Program-specific work` lives in the OPTIONAL detail file; a program with no prose
    # simply has none, which the report below already says out loud.
    detail = kr.program_detail(pid)
    itext = kr.detail_body(detail)
    if not requires:
        print(f"`{pid}` declares no `Requires` — run {_repo.command('program:decompose')} first:")
        print("a goal names the capability ids its decomposition produced; the plan is derived.")
        return 2

    caps = load_capabilities()
    comps = load_components()
    pst = load_prd_status()
    pdeps = load_prd_depends()
    areas = {c["area"] for c in caps.values()}

    # roots: capability ids (the decomposition); area names accepted but coarse
    roots: set[str] = set()
    coarse: list[str] = []
    unresolved: list[str] = []
    for r in requires:
        if CAP_ID_RE.match(r) and r in caps:
            roots.add(r)
        elif r in areas:
            coarse.append(r)
            roots.update(cid for cid, c in caps.items() if c["area"] == r)
        else:
            unresolved.append(r)

    # transitive closure over Needs
    closure, queue = set(roots), list(roots)
    while queue:
        for d in caps.get(queue.pop(), {}).get("needs", []):
            if d in caps and d not in closure:
                closure.add(d)
                queue.append(d)
    pulled = len(closure) - len(roots)

    needs_of = {cid: caps[cid]["needs"] for cid in closure}
    by_class: dict[str, list[str]] = {
        "gap": [],
        "in-flight": [],
        "unproven": [],
        "unanchored": [],
        "built": [],
        "retired": [],
    }
    for cid in closure:
        by_class[classify(caps[cid], pst)].append(cid)

    print(f"GOAL  {pid}  {prog['title']}   [kind: {prog['kind']}]")
    src = f"knowledge/programs.md line {prog['line']}"
    print(f"      {src}" + (f"  ·  {detail.relative_to(REPO)}" if detail.is_file() else "") + "\n")

    print(f"ROOTS ({len(roots)} capabilities from `Requires`)")
    if coarse:
        print(f"  COARSE: {', '.join(coarse)} — area names expand to everything recorded there.")
        print("  That answers 'what does the platform have', not 'what does this goal need'.")
        print(f"  Decompose to capability ids ({_repo.command('program:decompose')}).")
    for u in unresolved:
        print(f"  UNRESOLVED: {u}")
    print(f"  +{pulled} pulled in transitively via Needs = {len(closure)} in scope\n")

    n = by_class
    print(
        f"STATUS  built(anchored) {len(n['built'])} · unanchored {len(n['unanchored'])} · "
        f"unproven {len(n['unproven'])} · in flight {len(n['in-flight'])} · GAP {len(n['gap'])}"
        + (f" · retired {len(n['retired'])}" if n["retired"] else "")
    )

    if n["gap"]:
        print("\nBUILD ORDER  (gaps, dependencies first — this is the backward plan)")
        for i, cid in enumerate((g for g in toposort(closure, needs_of) if g in set(n["gap"])), 1):
            c = caps[cid]
            dep = ", ".join(d for d in c["needs"]) or "—"
            print(f"  {i:>2}. {cid:<8} {c['area']:<22} needs: {dep:<22} {c['title']}")

    if n["unproven"]:
        print("\nUNPROVEN  — cited PRD shipped, but Anchor is UNVERIFIED: existence not established")
        for cid in sorted(n["unproven"]):
            print(f"    {cid:<8} {caps[cid]['area']:<22} {caps[cid]['title']}")

    if n["unanchored"]:
        shown = sorted(n["unanchored"])[:12]
        more = len(n["unanchored"]) - len(shown)
        print("\nUNANCHORED  — claims built, but no Anchor verifies it (measured false rate 16-33%)")
        for cid in shown:
            print(f"    {cid:<8} {caps[cid]['area']:<22} {caps[cid]['title']}")
        if more > 0:
            print(f"    … +{more} more — anchor these rows to make the built-claims trustworthy")

    if n["in-flight"]:
        print("\nIN FLIGHT")
        for cid in sorted(n["in-flight"]):
            sts = ", ".join(f"{p}[{pst.get(p, '?')}]" for p in caps[cid]["prds"])
            print(f"    {cid:<8} {caps[cid]['area']:<22} {sts}")

    involved = sorted({comp for cid in closure for comp in caps[cid]["components"] if comp in comps})
    if involved:
        print(f"\nCOMPONENTS INVOLVED  {', '.join(involved)}")

    # A goal is FINISHED only when proven e2e through every relevant surface
    # (browser, API, MCP, channels). Completion is DERIVED from these, never stored,
    # and the validator requires the field outright on a `kind: program`.
    if verified_by:
        print("\nPROOF  — the program is complete only when these ship (derived, never stored)")
        drills = kr.drills()
        for num in verified_by:
            print(f"    {num}  [{proof_reading(num, pst, drills)}]")
    else:
        print("\nPROOF  — NONE DECLARED. Capabilities existing is not the goal working:")
        print("  add `verified_by:` naming the e2e proof PRD/task (browser + API + MCP +")
        print("  every relevant surface). Without it this program can never read complete.")

    # PLANNING QUEUE — the multi-session planning entry point: every PRD this goal
    # cites (Ships-in + proof) that is not yet implementable, with the exact next
    # verb, dependencies first. Gap rows are not repeated here (BUILD ORDER owns
    # them); a one-line pointer keeps the two sections coherent.
    topo_pos = {cid: i for i, cid in enumerate(toposort(closure, needs_of))}
    pq: dict[str, dict[str, Any]] = {}
    for cid in closure:
        for p in caps[cid]["prds"]:
            if pst.get(p) in NEXT_VERB:
                q = pq.setdefault(p, {"status": pst[p], "cited_by": [], "pos": len(topo_pos), "proof": False})
                q["cited_by"].append(cid)
                q["pos"] = min(q["pos"], topo_pos.get(cid, len(topo_pos)))
    for num in proof_prds:
        if pst.get(num) in NEXT_VERB:
            q = pq.setdefault(num, {"status": pst[num], "cited_by": [], "pos": len(topo_pos), "proof": False})
            q["proof"] = True
    planned = sorted(
        {p for cid in closure for p in caps[cid]["prds"] if pst.get(p) == "planned"}
        | {v for v in proof_prds if pst.get(v) == "planned"}
    )
    # A `planned` PRD is dispatch-ready when its OWN `depends_on:` entries have all reached a
    # terminal state — an unshipped/uncancelled dependency means the PRD is built on a
    # foundation that isn't there yet. An unknown dependency (missing from pst)
    # blocks too — fail closed, not open. (Its own Linear `blockedBy` is the tracker's half.)
    #
    # NOTHING TRANSITIVE. The slice its PRD sits on, and the cuts that slice's
    # `Depends on` names, are order — they never make a PRD whose own dependencies are met
    # read BLOCKED. That reading held PRD 0612 back for a PRD added later to another cut.
    blockers: dict[str, list[str]] = {p: [d for d in pdeps.get(p, []) if pst.get(d) not in TERMINAL] for p in planned}
    ready = [p for p in planned if not blockers[p]]
    blocked = [p for p in planned if blockers[p]]
    if pq or n["gap"] or planned:
        print("\nPLANNING QUEUE  — cited PRDs not yet implementable; the next verb per artifact")
        for num, q in sorted(pq.items(), key=lambda kv: (kv[1]["pos"], kv[0])):
            tags = ", ".join(sorted(q["cited_by"])[:3] + (["proof"] if q["proof"] else []))
            print(f"    {num} [{q['status']:<11}] → {_repo.command(NEXT_VERB[q['status']]):<19} ({tags})")
        if not pq:
            print("    (no cited PRD is mid-pipeline)")
        if n["gap"]:
            create = _repo.command("prd:create")
            print(f"  plus {len(n['gap'])} gap row(s) in BUILD ORDER above — each begins with {create}.")
        for num in ready:
            implement = _repo.command("prd:implement")
            print(f"  READY  {num} [planned] — {implement} (dispatch still needs `agent-eligible`)")
        for num in blocked:
            print(f"  BLOCKED {num} [planned] — waiting on {', '.join(blockers[num])} to ship")

    gsw = goal_specific_work(itext)
    if gsw:
        print(f"\nGOAL-SPECIFIC WORK  ({len(gsw)} items — not ledger rows; PRDs/tasks in the program's own slice)")
        for item in gsw:
            print(f"    - {item}")
    else:
        print("\nGOAL-SPECIFIC WORK  none recorded — if this goal is a customer/release")
        print("  engagement, that is almost certainly wrong: add a `## Program-specific work`")
        print("  section (tenant, provisioning, data, config are rarely zero).")

    print("\n  THE PLANNER ONLY SEES WHAT THE DECOMPOSITION WROTE DOWN. A need nobody")
    print("  captured as a capability row or goal-specific item is invisible here and")
    print("  reads as 'no gaps'. Decomposition is the human+agent step; this replays it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
