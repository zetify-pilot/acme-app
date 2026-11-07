"""Is a repository's knowledge base ready to build on? One verdict for the whole repository.

A team bootstrapping a knowledge base asks one question — *can we start building yet?* — and it
does not know every part of its product, so the answer cannot be "per area". It is read from where
the team has actually been changing code: the next piece of work most likely lands where the last
ones did, so the knowledge base is ready when most of that recent change lands on parts that are
described. The check gate is blind on code no described part covers: an issue there
is released without being checked against anything the product promised.

**The reading, in four conditions — every one re-measurable from the tree and git:**

1. *Basics* — the commands to test and lint are answered (the fleet cannot verify work without
   them), a product statement exists, and at least 95% of hand-written code files belong to a
   component (the gate resolves an issue's ground through that map).
2. *Recent change* — over the first-parent commits of the last 90 days (or the last 200 code
   commits, when the window holds fewer), each commit counts once, split equally over the parts
   its code files touch; at least 80% of it must land on described parts.
3. *No blind spot* — no single undescribed part carries 5% or more of that change, so an average
   cannot hide one large hole.
4. *Nothing waits on a person* — read only where a bootstrap progress file exists (a local
   checkout): no described part changed since it was read, no review question unanswered.

**What "described" means.** A part is described when at least one LIVE capability points at its
code AND the corpus reaches every code file the part owns: by the rows' own anchors or evidence
paths when they name one, and by the `source_of_truth:` of the feature maps that list it. One
capability anchored in one directory is not a description of a component that also holds five
others — a part read only in part is named with the directories and files nobody read. A
capability is live when it is marked `(shipped)` / `(core)` or ships in a PRD of this repository
whose status is `shipped`. Every live capability was approved by a person when it was written (a
shipped PRD, or a bootstrap review), so the reading needs no second approval. Retired, withdrawn
and planned rows are not promises.

**Shown, never blocking:** promises the Quality desk has checked, and parts with rules or a
journey. QA readiness is the bootstrap's own Phase 5 gate, and a part can honestly have no rules.

This module is pure and stdlib-only: the caller supplies the corpus directory, the tracked code
paths and the commit list. `knowledge/scripts/kb_readiness.py` supplies them from a local
checkout; the service supplies them from its mirror during a corpus sync. One definition of
"ready", two callers.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

#: Bumped when the shape of `assess`'s answer changes; the page refuses a shape it does not know.
SCHEMA = 1

#: The policy, overridable per repository in `.fleet/fleet.toml` → `[fleet.readiness]`.
DEFAULTS: dict[str, float] = {
    # Share of recent change that must land on described parts. Change concentrates: the parts
    # holding most of it are where the next issues land, so they are what the gate must see.
    "threshold": 0.80,
    # No single undescribed part may carry this much: an average must not hide one blind spot.
    "hotspot": 0.05,
    # Basics: share of hand-written code files a component owns.
    "owned": 0.95,
    "days": 90,
}
#: Below this many code commits in the window, read the newest this-many instead.
MIN_COMMITS = 200
#: The `window` a caller passes when it fell back to the newest commits: the label then names the
#: count the reading actually used, so the caller and the reading can never disagree about it.
WINDOW_COMMITS = "commits"
#: Below this many code commits in the whole history, there is nothing honest to say yet.
TOO_FEW_COMMITS = 50
#: The conventional targets the fleet cannot verify work without. `build` is reported, never
#: required: some stacks have no build step, and an honest absence must not read as a failure.
FLOOR_TARGETS = ("test-unit", "lint")

#: The corpus layout, relative to the knowledge directory — the same fixed layout
#: `kb_inventory.py` writes and reads.
REGISTRY = "specs/architecture/components.md"
FEATURES = "features"
REQUIREMENTS = "requirements"
PRDS = "prds"
VISION = "strategy/product-vision.md"
QA_RESULTS = "audits/results/scenario"

#: Source-file extensions that count as code. KEPT EQUAL to `kb_inventory.py`'s `CODE_EXT` keys —
#: a test holds the two together, because a file one counts and the other does not would make the
#: bootstrap's ownership gate and this reading disagree about the same tree.
CODE_EXT = frozenset(
    {
        ".go",
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".java",
        ".kt",
        ".rb",
        ".rs",
        ".cs",
        ".php",
        ".swift",
        ".scala",
        ".sql",
        ".proto",
        ".vue",
        ".zul",
        ".graphql",
        ".graphqls",
        ".gql",
    }
)
#: Generated output and vendored code: never hand-written work, never a part's to describe.
GENERATED = re.compile(
    r"(^|/)(gen|generated|__generated__|__mocks__|mocks?|testdata|fixtures?|testFixtures|vendor|node_modules)/"
    r"|(^|/)[^/]*_mocks/|(^|/)gen_[^/]+$|\.pb\.go$"
    r"|_pb2(_grpc)?\.pyi?$|\.gen\.(go|ts|tsx|py)$|\.min\.js$"
)
LIVE_MARKERS = ("(shipped)", "(core)")
SHIPS_PRD = re.compile(r"(?<![\w:])(\d{3,4})(?!\d)")
PATHISH = re.compile(r"`([\w./-]+/[\w./-]*|[\w-]+\.(?:go|py|ts|tsx|js|jsx|mjs|rs|java|kt|rb|cs|sql|vue))`")


# ───────────────────────────────────── small readers ─────────────────────────────────────


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _frontmatter(text: str) -> str:
    return text.split("---", 2)[1] if text.startswith("---") else ""


def _fm_list(fm: str, key: str) -> list[str]:
    m = re.search(rf"^{key}:\s*\[(.*)\]\s*$", fm, re.M)
    if m:
        return [x.strip().strip("\"'") for x in m.group(1).split(",") if x.strip()]
    m = re.search(rf"^{key}:\s*\n((?:\s+-\s+.+\n?)+)", fm, re.M)
    return [ln.strip()[2:].strip().strip("\"'") for ln in m.group(1).splitlines() if ln.strip()] if m else []


def _table(text: str, section: str) -> list[list[str]]:
    """The body rows of the first markdown table under `## <section>`."""
    m = re.search(rf"^## {re.escape(section)}\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    rows = []
    for line in (m.group(1) if m else "").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if not cells or not set(cells[0]) - set("-: "):
            continue
        rows.append(cells)
    return rows[1:] if rows else []  # the first row is the header


# ─────────────────────────────── the map: who owns what ───────────────────────────────


def component_owns(registry_text: str) -> dict[str, str]:
    """`{owned path prefix: component id}` — the registry's `## Components` table, fourth column."""
    out: dict[str, str] = {}
    for cells in _table(registry_text, "Components"):
        if len(cells) < 4:
            continue
        for p in (x.strip().strip("`") for x in cells[3].split(",") if x.strip()):
            out[p.rstrip("/")] = cells[0]
    return out


def component_names(registry_text: str) -> dict[str, tuple[str, str]]:
    """`{component id: (name, description)}`, for the page's rows."""
    out = {}
    for cells in _table(registry_text, "Components"):
        if cells and cells[0]:
            out[cells[0]] = (cells[1] if len(cells) > 1 else cells[0], cells[5] if len(cells) > 5 else "")
    return out


def unassigned(registry_text: str) -> list[str]:
    """`## Unassigned code` — paths deliberately owned by no part, each with a reason."""
    return [c[0].strip("`").rstrip("/") for c in _table(registry_text, "Unassigned code") if c and c[0]]


def owner(path: str, owns: Mapping[str, str]) -> str | None:
    """The component whose owned prefix is the longest one covering `path`."""
    best: tuple[str, str] | None = None
    for prefix, comp in owns.items():
        if (path == prefix or path.startswith(prefix + "/")) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, comp)
    return best[1] if best else None


def is_code(path: str, excluded: Sequence[str] = ()) -> bool:
    """Hand-written code: a source extension, not generated, not deliberately unassigned."""
    if Path(path).suffix not in CODE_EXT or GENERATED.search(path):
        return False
    return not any(path == u or path.startswith(u + "/") for u in excluded)


# ───────────────────────────── the corpus: what is described ─────────────────────────────


def _prd_status(knowledge: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    root = knowledge / PRDS
    for f in root.glob("*/prd.md") if root.is_dir() else []:
        m = re.search(r"^status:\s*(\S+)", _read(f), re.M)
        if m:
            out[f.parent.name.split("-", 1)[0].lstrip("0") or "0"] = m.group(1)
    return out


def live(ships: str, prds: Mapping[str, str]) -> bool:
    """A capability row is a promise when it shipped: by its own marker, or by a shipped PRD here.

    `(retired)`, `(withdrawn)`, `—` and an unshipped PRD are not. A PRD named for another
    repository (`other-repo:0123`) cannot be resolved from here and is not counted.
    """
    if any(x in ships for x in LIVE_MARKERS):
        return True
    return any(prds.get(n.lstrip("0") or "0") == "shipped" for n in SHIPS_PRD.findall(ships))


def _reaches(paths: Iterable[str], owned: Sequence[str]) -> bool:
    for p in (x.rstrip("/") for x in paths if x):
        for o in owned:
            if p == o or p.startswith(o + "/") or o.startswith(p + "/"):
                return True
    return False


def described_index(knowledge: Path, owns: Mapping[str, str]) -> dict[str, Any]:
    """Per component: live capabilities credited to it, rules, journeys; promise id → components.

    Also returns `reached`: the code paths the corpus claims to have read for each component —
    a live capability's own anchors plus the `source_of_truth:` of the map that lists it. A part
    is fully described only when those paths reach every code file it owns; see `assess`.
    """
    owned_by: dict[str, list[str]] = defaultdict(list)
    for prefix, comp in owns.items():
        owned_by[comp].append(prefix)
    prds = _prd_status(knowledge)
    caps: dict[str, int] = defaultdict(int)
    rules: dict[str, int] = defaultdict(int)
    journeys: dict[str, int] = defaultdict(int)
    reached: dict[str, set[str]] = defaultdict(set)
    promise_comps: dict[str, set[str]] = defaultdict(set)
    feats = knowledge / FEATURES
    for f in sorted(feats.glob("*.md")) if feats.is_dir() else []:
        text = _read(f)
        fm = _frontmatter(text)
        listed = _fm_list(fm, "components")
        source_paths = [p.rstrip("/") for p in _fm_list(fm, "source_of_truth") if p]
        reach = [c for c in listed if _reaches(source_paths, owned_by.get(c, []))]
        for c in reach:
            reached[c].update(source_paths)
        js = _fm_list(fm, "journeys")
        ships_col: int | None = None
        for line in text.splitlines():
            if line.startswith("| ID |"):  # each capability table names its own columns
                hdr = [c.strip().lower() for c in line.strip().strip("|").split("|")]
                ships_col = hdr.index("ships in") if "ships in" in hdr else None
                continue
            m = re.match(r"^\|\s*(CAP-\d+)\s*\|", line)
            if not m:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            ships = cells[ships_col] if ships_col is not None and ships_col < len(cells) else line
            if not live(ships, prds):
                continue
            # A row naming code is credited where that code lives; otherwise to the map's reach.
            anchors = {p.rstrip("/") for p in PATHISH.findall(line)}
            anchored: set[str] = set()
            for p in anchors:
                owner_id = owner(p, owns)
                if owner_id is not None:
                    anchored.add(owner_id)
            credited = (anchored & set(listed)) or anchored or set(reach)
            for c in credited:
                caps[c] += 1
                reached[c].update(p for p in anchors if owner(p, owns) == c)
            promise_comps[m.group(1)].update(c for c in credited if c)
        for c in reach:
            journeys[c] += len(js)
        for j in js:
            promise_comps[j].update(reach)
    # A register is a committed `<domain>.md`, or a fragment-backed `<domain>.md.tmpl` whose rows
    # are `rows/<ID>.json` — read the source, never the on-demand render.
    reg = knowledge / REQUIREMENTS
    fragments: dict[str, set[str]] = defaultdict(set)
    for f in (reg / "rows").glob("*.json") if (reg / "rows").is_dir() else []:
        try:
            table = str(json.loads(_read(f) or "{}").get("table", ""))
        except ValueError:
            continue
        fragments[table.split("#", 1)[0]].add(f.stem)
    registers: dict[str, tuple[list[str], set[str]]] = {}
    for f in sorted(reg.glob("*.md*")) if reg.is_dir() else []:
        domain = f.name.split(".", 1)[0]
        text = _read(f)
        comps = _fm_list(_frontmatter(text), "components")
        rows = set(re.findall(r"^\|\s*([A-Z]{2,5}-\d{3,5})\s*\|", text, re.M)) | fragments.get(domain, set())
        prev = registers.get(domain, ([], set()))
        registers[domain] = (prev[0] or comps, prev[1] | rows)
    for comps, rows in registers.values():
        for c in comps:
            rules[c] += len(rows)
        for r in rows:
            promise_comps[r].update(comps)
    return {
        "caps": caps,
        "rules": rules,
        "journeys": journeys,
        "reached": reached,
        "promise_comps": promise_comps,
    }


def qa_checked(knowledge: Path, promise_comps: Mapping[str, set[str]]) -> tuple[int, set[str]]:
    """Distinct promises with a recorded pass or fail, and the components they belong to."""
    promises: set[str] = set()
    d = knowledge / QA_RESULTS
    for f in d.glob("*.json") if d.is_dir() else []:
        try:
            data = json.loads(_read(f) or "{}")
        except ValueError:
            continue
        for v in data.get("verdicts", []) if isinstance(data, dict) else []:
            if v.get("verdict") not in ("pass", "fail"):
                continue
            if v.get("promise"):
                promises.add(str(v["promise"]))
            if "#" in str(v.get("id", "")):
                promises.add(str(v["id"]).split("#")[0])
    comps: set[str] = set()
    for p in promises:
        comps |= promise_comps.get(p, set())
    return len(promises), comps


def read_progress(text: str | None) -> dict[str, Any] | None:
    """Component states and unanswered questions from a bootstrap progress file, when one exists."""
    if not text:
        return None
    states: dict[str, str] = {}
    for cells in _table(text, "Components"):
        if len(cells) >= 8 and cells[1] and set(cells[1]) - set("-: "):
            states[cells[1]] = cells[-1]
    m = re.search(r"^## Open questions\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    unanswered = len(re.findall(r"^\*\*Answer:\*\*\s*(<[^>]*>)?\s*$", m.group(1), re.M)) if m else 0
    return {"states": states, "unanswered": unanswered}


def policy(fleet_toml: str | None, overrides: Mapping[str, Any] | None = None) -> dict[str, float]:
    p = dict(DEFAULTS)
    if fleet_toml:
        try:
            got = tomllib.loads(fleet_toml).get("fleet", {}).get("readiness", {})
        except tomllib.TOMLDecodeError:
            got = {}
        p.update({k: float(v) for k, v in got.items() if k in DEFAULTS and isinstance(v, (int, float))})
    p.update({k: float(v) for k, v in (overrides or {}).items() if v is not None and k in DEFAULTS})
    return p


def targets(fleet_toml: str | None) -> dict[str, str]:
    if not fleet_toml:
        return {}
    try:
        got = tomllib.loads(fleet_toml).get("fleet", {}).get("targets", {})
    except tomllib.TOMLDecodeError:
        return {}
    return {k: str(v) for k, v in got.items() if v}


# ──────────────────────────────────────── the verdict ────────────────────────────────────────


def bucket(path: str, owns: Mapping[str, str]) -> str:
    """A component id, or `/<dir>/<dir>` for code no component owns (named so the page can say which)."""
    return owner(path, owns) or "/" + "/".join(path.split("/")[:2])


def assess(
    knowledge: Path,
    *,
    code_paths: Iterable[str],
    commits: Sequence[tuple[str, Sequence[str]]],
    window: str,
    head: str = "",
    fleet_toml: str | None = None,
    progress: str | None = None,
    read_files: Iterable[str] = (),
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The reading. `commits` is newest first, `(sha, paths touched)`; `window` says what it spans."""
    pol = policy(fleet_toml, overrides)
    registry = _read(knowledge / REGISTRY)
    owns = component_owns(registry)
    names = component_names(registry)
    excluded = unassigned(registry)
    tracked = {p for p in code_paths if is_code(p, excluded)}
    all_comps = sorted(set(owns.values()))
    blockers: list[dict[str, str]] = []

    # 1. Basics.
    missing = [t for t in FLOOR_TARGETS if not targets(fleet_toml).get(t)]
    vision = len(_read(knowledge / VISION)) > 200
    owned_ratio = sum(1 for f in tracked if owner(f, owns)) / (len(tracked) or 1)
    if missing:
        blockers.append(
            {
                "kind": "targets",
                "text": "No command to "
                + " or ".join({"test-unit": "run the tests", "lint": "lint the code"}[t] for t in missing)
                + ".",
            }
        )
    if not vision:
        blockers.append({"kind": "vision", "text": "No product statement has been written yet."})
    if tracked and owned_ratio < pol["owned"]:
        blockers.append(
            {"kind": "map", "text": f"{owned_ratio:.0%} of the code belongs to a part; {pol['owned']:.0%} is needed."}
        )

    # 2. Recent change on described parts. Paths that no longer exist are skipped: a file that
    #    was moved or deleted would otherwise read as code no part owns, a gap that is not there.
    idx = described_index(knowledge, owns)
    # A part is described only when the WHOLE of it was read. One capability anchored in one
    # directory is not a description of a component that also holds five others — the reported
    # bug was a large component read in part and then called ready. Name what nobody read.
    ledger = set(read_files)  # files the bootstrap's sub-agents recorded as opened (kb_inventory ledger)
    unread: dict[str, list[str]] = {}
    for c in all_comps:
        if idx["caps"].get(c, 0) <= 0:
            continue
        owned = [f for f in tracked if owner(f, owns) == c]
        reached = idx["reached"].get(c, set())
        missing_files = [
            f for f in owned if f not in ledger and not any(f == p or f.startswith(p + "/") for p in reached)
        ]
        if missing_files:
            unread[c] = missing_files
    described = {c for c in all_comps if idx["caps"].get(c, 0) > 0 and c not in unread}
    for c, missing_files in sorted(unread.items()):
        dirs: Counter[str] = Counter()
        for f in missing_files:
            dirs[f.rsplit("/", 1)[0] if "/" in f else "."] += 1
        listed = ", ".join(
            f"{d}/ ({n} file{'s' if n != 1 else ''})" for d, n in sorted(dirs.items(), key=lambda x: (-x[1], x[0]))[:4]
        )
        if len(dirs) > 4:
            more = len(dirs) - 4
            listed += f", and {more} more director{'y' if more == 1 else 'ies'}"
        total_files = sum(1 for f in tracked if owner(f, owns) == c)
        blockers.append(
            {
                "kind": "unread",
                "part": c,
                "text": f"{c} is only partly described: {len(missing_files)} of {total_files} "
                f"files were not read ({listed}).",
            }
        )
    weight: dict[str, float] = defaultdict(float)
    counted = 0
    for _sha, files in commits:
        touched = {bucket(f, owns) for f in files if f in tracked}
        if not touched:
            continue
        counted += 1
        for b in touched:
            weight[b] += 1 / len(touched)
    total = sum(weight.values()) or 1.0
    coverage = sum(w for b, w in weight.items() if b in described) / total
    share = {b: w / total for b, w in weight.items()}
    enough = counted >= TOO_FEW_COMMITS
    gaps = sorted(((b, s) for b, s in share.items() if b not in described), key=lambda x: -x[1])
    hotspots = [(b, s) for b, s in gaps if s >= pol["hotspot"]]
    if not enough:
        blockers.append(
            {
                "kind": "history",
                "text": f"Only {counted} code commits to measure; {TOO_FEW_COMMITS} are needed for an honest reading.",
            }
        )
    else:
        if coverage < pol["threshold"]:
            blockers.append(
                {
                    "kind": "coverage",
                    "text": f"{round(coverage, 3):.0%} of recent code changes land "
                    f"on described parts; {pol['threshold']:.0%} is needed.",
                }
            )
        for b, s in hotspots:
            label = b[1:] if b.startswith("/") else b
            blockers.append(
                {
                    "kind": "blindspot",
                    "part": b,
                    "text": f"{label} takes {s:.0%} of recent changes "
                    + ("and belongs to no part." if b.startswith("/") else "and is not described."),
                }
            )

    # 3. Pending answers — only a local checkout's progress file knows them.
    prog = read_progress(progress)
    stale: list[str] = []
    review: dict[str, str] = {}
    unanswered = None
    if prog:
        stale = sorted(c for c, s in prog["states"].items() if s == "stale")
        review = {c: s for c, s in prog["states"].items() if s in ("awaiting-review", "drafted")}
        unanswered = prog["unanswered"]
        if unanswered:
            blockers.append({"kind": "questions", "text": f"{unanswered} review question(s) wait for an answer."})
        for c in stale:
            blockers.append({"kind": "stale", "part": c, "text": f"{c} changed after it was described."})

    # Shown, never blocking.
    n_qa, qa_comps = qa_checked(knowledge, idx["promise_comps"])

    # The parts, each with its state and its share — the page's list, in the page's order.
    def state_of(b: str) -> str:
        if b.startswith("/"):
            return "unmapped"
        if b in stale:
            return "stale"
        if review.get(b) == "awaiting-review":
            return "review"
        if review.get(b) == "drafted":
            return "drafted"
        if b in described:
            return "described"
        # Capabilities were written but the whole of the part was not read: partly described, not
        # "undescribed" (a part carrying 85 capabilities read "Not described" on the Knowledge page).
        return "partial" if b in unread else "undescribed"

    parts = []
    for b in sorted(set(weight) | set(all_comps), key=lambda x: (-share.get(x, 0.0), x)):
        n_files = sum(1 for f in tracked if bucket(f, owns) == b) if b.startswith("/") else None
        name, desc = names.get(b, (b, ""))
        parts.append(
            {
                "id": b[1:] if b.startswith("/") else b,
                "unmapped": b.startswith("/"),
                "state": state_of(b),
                "share": round(share.get(b, 0.0), 4),
                "description": desc,
                "files": n_files,
                "capabilities": idx["caps"].get(b, 0),
                "unreadFiles": len(unread[b]) if b in unread else 0,
                "rules": idx["rules"].get(b, 0),
            }
        )
    # The fewest undescribed parts that cross the line, every blind spot included.
    nxt, acc = [], coverage
    for b, s in gaps:
        if acc >= pol["threshold"] and all(h != b for h, _ in hotspots):
            break
        nxt.append(b[1:] if b.startswith("/") else b)
        acc += s

    verdict = "ready" if not blockers else ("too-little-history" if not enough and len(blockers) == 1 else "not-ready")
    return {
        "schema": SCHEMA,
        "head": head,
        "verdict": verdict,
        "blockers": blockers,
        "policy": pol,
        "figures": {
            "coverage": round(coverage, 4),
            "described": len(described),
            "components": len(all_comps),
            "owned": round(owned_ratio, 4),
            "questions": unanswered,
            "promisesChecked": n_qa,
        },
        "window": {"label": f"last {counted} code commits" if window == WINDOW_COMMITS else window, "commits": counted},
        "describeNext": nxt,
        "parts": parts,
        "info": {
            "describedWithRules": sum(1 for c in described if idx["rules"].get(c)),
            "describedWithJourney": sum(1 for c in described if idx["journeys"].get(c)),
            "describedWithQa": len(described & qa_comps),
            "targetsMissing": missing,
            "productVision": vision,
            "progressFile": prog is not None,
            "readExcluded": sum(
                1 for f in code_paths if Path(f).suffix in CODE_EXT and GENERATED.search(f) and owner(f, owns)
            ),
        },
    }


def log_args(days: float) -> list[str]:
    """The `git log` arguments every caller reads the window with — one spelling, one meaning."""
    return ["log", "--first-parent", "--no-renames", f"--since={int(days)}.days", "--name-only", "--format=%x00%H"]


def parse_log(out: str) -> list[tuple[str, list[str]]]:
    """`git log ... --format=%x00%H --name-only` → `[(sha, paths)]`, newest first."""
    commits = []
    for block in out.split("\x00")[1:]:
        lines = [x for x in block.strip().splitlines() if x]
        if lines:
            commits.append((lines[0], lines[1:]))
    return commits


def code_commits(commits: Sequence[tuple[str, Sequence[str]]], code: set[str]) -> int:
    """How many of `commits` touched at least one of `code`."""
    return sum(1 for _sha, files in commits if any(f in code for f in files))


def newest(
    commits: Sequence[tuple[str, Sequence[str]]], code: set[str], n: int = MIN_COMMITS
) -> list[tuple[str, Sequence[str]]]:
    """The newest commits up to and including the `n`-th one that touched `code` — the fallback
    window for a repository too quiet to fill its days. One rule, so the script and the service
    trim a quiet history the same way."""
    kept, counted = [], 0
    for sha, files in commits:
        kept.append((sha, files))
        if any(f in code for f in files):
            counted += 1
            if counted >= n:
                break
    return kept
