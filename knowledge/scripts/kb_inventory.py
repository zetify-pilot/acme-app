#!/usr/bin/env python3
"""The denominator a knowledge bootstrap is measured against — and the reading against it.

    python3 knowledge/scripts/kb_inventory.py scan       # write .claude/run/knowledge-bootstrap/inventory.json
    python3 knowledge/scripts/kb_inventory.py coverage   # what the corpus claims of it, per component

The knowledge bootstrap command describes an existing code base into the corpus. "Describes it
well" is not a feeling: it is a ratio, and a ratio needs a denominator that the describing agent
did not choose. `scan` enumerates it from the tree, deterministically:

  * **units** — every directory that holds source files, rolled up to the depth a component
    is drawn at (a unit is what a component's `owns:` cell claims);
  * **surfaces** — the things a person or a machine can reach: HTTP operations (API spec
    documents and router registrations), UI routes, CLI entry points, database tables, and declared
    event types.

`coverage` joins it to the corpus as it stands: which units no component owns, which surfaces
no feature map's `surfaces:` / `source_of_truth:` reaches, and which of a component's own
directories its feature maps never claim to have read, per component. It never judges
whether a capability row is *right* — that is the interview's job — only whether the ground was
walked at all. A detector that finds no surfaces is a miss, not an absence: a component is still
measured by the files and directories no feature map's `source_of_truth:` reaches.

Heuristic by necessity — no single parser reads every stack — and honest about it: every
surface records the file and line it was read from, and `scan` prints which detectors fired, so
a repository whose router this does not recognise reads "0 http surfaces" rather than a
confident nothing. Stdlib only, like every sibling script.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

#: `KB_INVENTORY_REPO` points the scan at another checkout, read-only, and `KB_INVENTORY_STATE`
#: moves the run state out of it (measuring a tree without writing a byte into it).
REPO = Path(os.environ["KB_INVENTORY_REPO"]) if os.environ.get("KB_INVENTORY_REPO") else _repo.repo_root()
KNOWLEDGE = REPO / "knowledge"
#: The bootstrap's own working state — its progress ledger, its un-reviewed drafts and its
#: re-derivable inventory snapshot. None of it is product knowledge: it lives in the
#: checkout-scoped run state (`process/spine.md` → "A command's own state"), which git never
#: carries into a commit or a pull request.
STATE = (
    Path(os.environ["KB_INVENTORY_STATE"])
    if os.environ.get("KB_INVENTORY_STATE")
    else (REPO / _repo.RUN_STATE / "knowledge-bootstrap")
)
#: Where each artifact of a bootstrapped corpus lives — the readers' own defaults, relative to
#: the knowledge directory. `layout` prints them, so the procedure that writes them never has to
#: spell a path a repository with a different layout would not have.
LAYOUT = {
    "components": "specs/architecture/components.md",
    "feature-maps": "features/",
    "capability-aliases": "capability-aliases.md",
    "commitments": "requirements/",
    "journeys": "journeys/flows/",
    "product-vision": "strategy/product-vision.md",
    "environments": "environments/",
}
#: The run-state artifacts, relative to the repository. `layout` prints these beside the corpus
#: artifacts, and they are deliberately outside `knowledge/`: the bootstrap must never commit
#: its own notes into the corpus it is describing.
STATE_LAYOUT = {
    "progress": STATE / "progress.md",
    "drafts": STATE / "drafts",
    "inventory": STATE / "inventory.json",
}
STATE_LAYOUT["batches"] = STATE / "batches"
STATE_LAYOUT["ledger"] = STATE / "ledger.json"
OUT = STATE_LAYOUT["inventory"]
#: A sub-agent's share of a component: at most this many files and this many bytes, whichever
#: is hit first, so one batch is read closely in one sitting rather than skimmed.
BATCH_FILES = 40
BATCH_BYTES = 400_000
REGISTRY = KNOWLEDGE / LAYOUT["components"]
FEATURES = KNOWLEDGE / LAYOUT["feature-maps"]

CODE_EXT = {
    ".go": "go",
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".vue": "vue",
    ".java": "java",
    ".kt": "kotlin",
    ".cs": "csharp",
    ".rb": "ruby",
    ".rs": "rust",
    ".php": "php",
    ".swift": "swift",
    ".scala": "scala",
    ".sql": "sql",
    ".proto": "proto",
    ".zul": "zul",
    ".graphql": "graphql",
    ".graphqls": "graphql",
    ".gql": "graphql",
}
#: Paths that are never product code: vendored, generated build output, fixtures of the tooling.
SKIP_RE = re.compile(
    r"(^|/)(node_modules|vendor|dist|build|\.venv|venv|__pycache__|\.git|target|coverage|"
    r"testdata|fixtures?|snapshots?|__snapshots__|\.next|\.turbo)(/|$)"
)
#: Generated code restates a source of truth that is inventoried on its own (an API spec, a
#: schema); counting both would double every surface and credit the copy.
GENERATED_RE = re.compile(r"((^|/)gen/|\.gen\.|(^|/)gen_|_gen\.|\.pb\.go$|(^|/)generated/)")
#: The cross-language convention a generator stamps on its output, whatever the file is called.
GENERATED_HEADER_RE = re.compile(r"(?i)code generated .* do not edit|@generated\b")
TEST_RE = re.compile(r"(_test\.go$|\.test\.[jt]sx?$|\.spec\.[jt]sx?$|(^|/)tests?/|(^|/)test_[^/]+\.py$)")
#: Test source sets and test classes, for the SURFACE scan only (a test registers no endpoint). Gradle
#: names a source set after what it holds - `src/test`, `src/testFixtures`, `src/zatsTest`.
SURFACE_TEST_RE = re.compile(
    TEST_RE.pattern[:-1] + r"|(^|/)src/[A-Za-z]*[Tt]est[A-Za-z]*/|(Test|Tests|IT)\.(java|kt)$)"
)
#: Not product code to be read: mocks, fixtures, test data, generated and vendored files. TESTS ARE
#: NOT HERE - a test says what is promised and proven, so it is read like the code it checks. The
#: single list: `fleet_knowledge/readiness.py` carries an equivalent (`GENERATED`) that a test holds
#: to the same verdicts, so the bootstrap and the readiness page agree.
NOT_READ_RE = re.compile(
    r"((^|/)(__mocks__|mocks?|testdata|fixtures?|testFixtures|generated|__generated__|gen|vendor|node_modules)/"
    r"|(^|/)[^/]*_mocks/|\.min\.js$)"
)

HTTP_ROUTER_RE = re.compile(
    r"""\b(?:r|router|mux|api|app|g|group|e|srv|s)\.(Get|Post|Put|Patch|Delete|Handle|HandleFunc|Route|get|post|put|patch|delete)\(\s*["'`](/[^"'`]*)["'`]"""
)
PY_ROUTE_RE = re.compile(r"""@\w+\.(get|post|put|patch|delete|route|api_route)\(\s*["'](/[^"']*)["']""")
#: A route-table entry. Child routes are declared RELATIVE to their parent (`path: "bugs/:id"`),
#: so the leading slash is optional; a router file is the only place this is read.
UI_ROUTE_RE = re.compile(r"""\bpath\s*[:=]\s*["'`](/?[A-Za-z0-9_\-:{}.*][A-Za-z0-9_\-/:{}.*]*|/)["'`]""")
ROUTER_IMPORT_RE = re.compile(
    r"""from\s+["'](react-router[\w-]*|vue-router|@angular/router|@tanstack/react-router)["']"""
    r"""|\b(?:RouteObject|Routes|createBrowserRouter)\b"""
)
TABLE_RE = re.compile(r"""\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][\w."]*)""", re.I)
SPEC_PATH_RE = re.compile(r"""^  (/[^:\s]*):\s*$""")
SPEC_METHOD_RE = re.compile(r"""^    (get|post|put|patch|delete):\s*$""")
API_SPEC_RE = re.compile(r"^paths:\s*$", re.M)
API_INFO_RE = re.compile(r"^info:\s*$", re.M)
OPERATION_ID_RE = re.compile(r"""^      operationId:\s*["']?(\w+)""")
#: A function definition, by name — what an `operationId` is implemented as.
FUNC_DEF_RE = re.compile(
    r"""^(?:func\s+(?:\([^)]*\)\s*)?|\s*(?:async\s+)?def\s+|export\s+(?:async\s+)?function\s+)(\w+)\s*\("""
)


#: Spring / JAX-RS endpoints (Java and Kotlin): `@GetMapping("/x")`, `@RequestMapping(value = "/x")`, `@Path("/x")`.
JVM_MAPPING_RE = re.compile(
    r"""@(Get|Post|Put|Patch|Delete|Request)Mapping\s*(?:\(\s*(?:(?:value|path)\s*=\s*)?\{?\s*["']([^"']*)["'])?"""
)
#: Only an annotation that STARTS the line (after other bare annotations such as `@GET`) is a
#: resource path; a `@Path("id")` inside a parameter list is a Retrofit URL parameter, not an endpoint.
JAXRS_PATH_RE = re.compile(r"""^\s*(?:@\w+\s+)*@Path\s*\(\s*["']([^"']*)["']""")
#: JVM entry point, scheduled job, JPA entity, servlet registration.
JVM_MAIN_RE = re.compile(r"""\bstatic\s+void\s+main\s*\(|^fun\s+main\s*\(""")
SCHEDULED_RE = re.compile(r"""@Scheduled\s*\(([^)]*)\)""")
JPA_ENTITY_RE = re.compile(r"""^\s*@Entity\b""")
JPA_TABLE_RE = re.compile(r"""@Table\s*\([^)]*?name\s*=\s*["']([\w.]+)["']""")
JPA_CLASS_RE = re.compile(r"""\bclass\s+(\w+)""")
WEB_SERVLET_RE = re.compile(r"""@WebServlet\s*\(([^)]*)\)""")
WEB_XML_SERVLET_RE = re.compile(r"<url-pattern>\s*([^<\s]+)\s*</url-pattern>")
LISTENER_RE = re.compile(r"""@(KafkaListener|JmsListener|RabbitListener|SqsListener)\b""")
#: Ktor routing DSL: `get("/x") {`, `route("/x") {`.
KTOR_ROUTE_RE = re.compile(r"""^\s*(get|post|put|patch|delete|route)\s*\(\s*["'](/[^"']*)["']\s*\)?\s*\{""")
#: GraphQL SDL: every named type is a surface, and so is each field of Query / Mutation / Subscription.
#: (A ZK `.zul` page is its own surface: one file.)
GRAPHQL_TYPE_RE = re.compile(r"^(?:extend\s+)?(type|interface|input|enum|union|scalar)\s+(\w+)")
GRAPHQL_FIELD_RE = re.compile(r"^\s{1,}(\w+)\s*[(:]")


def _graphql_surfaces(text: str) -> list[tuple[str, str, int]]:
    """Named types, and the fields of Query / Mutation / Subscription (also `extend type Query`).

    Descriptions (`\"\"\"` blocks, `#` lines) and multi-line argument lists are skipped, so an
    argument or a sentence of prose is never read as a field.
    """
    out: list[tuple[str, str, int]] = []
    root = ""
    in_doc = False
    depth = 0
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if line.count('"""') % 2 == 1:
            in_doc = not in_doc
            continue
        if in_doc or line.lstrip().startswith(("#", '"')):
            continue
        if depth > 0:
            depth += line.count("(") - line.count(")")
            continue
        if line.startswith("}"):
            root = ""
            continue
        m = GRAPHQL_TYPE_RE.match(line)
        if m and not line.startswith(" "):
            if not line.lstrip().startswith("extend"):
                out.append(("graphql-type", m.group(2), i))
            root = m.group(2) if line.endswith("{") and m.group(2) in ("Query", "Mutation", "Subscription") else ""
            continue
        if root:
            m = GRAPHQL_FIELD_RE.match(line)
            if m:
                out.append(("graphql-field", f"{root}.{m.group(1)}", i))
                depth = max(0, line.count("(") - line.count(")"))
    return out


def tracked_files() -> list[str]:
    """Every file git tracks — the tree as committed, never the developer's scratch."""
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines() if p and not SKIP_RE.search(p) and not p.startswith("knowledge/")]


def unit_of(path: str, depth: int) -> str:
    """The directory `depth` levels deep that holds `path` (shallower when the path is)."""
    parts = path.split("/")[:-1]
    return "/".join(parts[:depth]) or "."


def _read(path: str) -> str:
    try:
        return (REPO / path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def scan(depth: int) -> dict[str, Any]:
    files = tracked_files()
    code = [f for f in files if Path(f).suffix in CODE_EXT]
    units: dict[str, Counter[str]] = defaultdict(Counter)
    tests: Counter[str] = Counter()
    for f in code:
        u = unit_of(f, depth)
        units[u][CODE_EXT[Path(f).suffix]] += 1
        if TEST_RE.search(f):
            tests[u] += 1

    surfaces: list[dict[str, Any]] = []
    fired: Counter[str] = Counter()

    def add(kind: str, name: str, f: str, line: int) -> None:
        surfaces.append({"kind": kind, "name": name, "file": f, "line": line, "unit": unit_of(f, depth)})
        fired[kind] += 1

    for f in files:
        if SURFACE_TEST_RE.search(f) or GENERATED_RE.search(f):
            continue
        suffix = Path(f).suffix
        low = f.lower()
        if low.endswith("web.xml"):
            for i, line in enumerate(_read(f).splitlines(), 1):
                m = WEB_XML_SERVLET_RE.search(line)
                if m:
                    add("servlet", m.group(1), f, i)
            continue
        if suffix == ".zul":
            add("zul-page", f, f, 1)
            continue
        if suffix in (".graphql", ".graphqls", ".gql"):
            for kind, name, line_no in _graphql_surfaces(_read(f)):
                add(kind, name, f, line_no)
            continue
        if suffix in (".yaml", ".yml"):
            # An HTTP API description is recognised by its shape — top-level `info:` and
            # `paths:` — never by its file name or its vendor, so any spec dialect is read.
            text = _read(f)
            if API_SPEC_RE.search(text) and API_INFO_RE.search(text):
                current = None
                for i, line in enumerate(text.splitlines(), 1):
                    m = SPEC_PATH_RE.match(line)
                    if m:
                        current = m.group(1)
                        continue
                    m = SPEC_METHOD_RE.match(line)
                    if m and current:
                        add("http", f"{m.group(1).upper()} {current}", f, i)
                        continue
                    m = OPERATION_ID_RE.match(line)
                    if m and surfaces and surfaces[-1]["file"] == f:
                        surfaces[-1]["operation"] = m.group(1)
            continue
        if suffix not in CODE_EXT:
            continue
        text = _read(f)
        if suffix == ".sql" and "migration" not in low:
            for i, line in enumerate(text.splitlines(), 1):
                for m in TABLE_RE.finditer(line):
                    add("table", m.group(1).strip('"'), f, i)
            continue
        if suffix == ".go":
            if re.search(r"^package main\b", text, re.M) and f.endswith("main.go"):
                add("cli", unit_of(f, 99), f, 1)
            for i, line in enumerate(text.splitlines(), 1):
                m = HTTP_ROUTER_RE.search(line)
                if m:
                    add("http-route", f"{m.group(1).upper()} {m.group(2)}", f, i)
        elif suffix == ".py":
            if f.endswith("__main__.py"):
                add("cli", unit_of(f, 99), f, 1)
            for i, line in enumerate(text.splitlines(), 1):
                m = PY_ROUTE_RE.search(line)
                if m:
                    add("http-route", f"{m.group(1).upper()} {m.group(2)}", f, i)
        elif suffix in (".java", ".kt"):
            lines = text.splitlines()
            for i, line in enumerate(lines, 1):
                m = JVM_MAPPING_RE.search(line)
                if m:
                    verb, path = m.group(1).upper(), m.group(2)
                    if path is None and verb == "REQUEST":
                        continue
                    add("http-route", f"{verb if verb != 'REQUEST' else 'ANY'} {path or '/'}", f, i)
                    continue
                m = JAXRS_PATH_RE.search(line)
                if m:
                    add("http-route", f"PATH {m.group(1)}", f, i)
                    continue
                m = KTOR_ROUTE_RE.match(line) if suffix == ".kt" else None
                if m:
                    add("http-route", f"{m.group(1).upper()} {m.group(2)}", f, i)
                    continue
                if JVM_MAIN_RE.search(line):
                    add("cli", f, f, i)
                    continue
                m = SCHEDULED_RE.search(line)
                if m:
                    add("scheduled-job", f"{Path(f).stem}: {m.group(1).strip() or 'scheduled'}", f, i)
                    continue
                m = LISTENER_RE.search(line)
                if m:
                    add("message-listener", f"{m.group(1)} in {Path(f).stem}", f, i)
                    continue
                m = WEB_SERVLET_RE.search(line)
                if m:
                    add("servlet", f"{Path(f).stem}: {m.group(1).strip()}", f, i)
                    continue
                if JPA_ENTITY_RE.match(line):
                    name = ""
                    for look in lines[i - 1 : i + 6]:
                        t = JPA_TABLE_RE.search(look)
                        if t:
                            name = t.group(1)
                            break
                        c = JPA_CLASS_RE.search(look)
                        if c:
                            name = c.group(1)
                            break
                    if not name:
                        continue
                    for back in lines[max(0, i - 4) : i - 1]:
                        t = JPA_TABLE_RE.search(back)
                        if t:
                            name = t.group(1)
                    add("table", name, f, i)
        elif suffix in (".tsx", ".jsx", ".ts", ".js", ".vue") and ROUTER_IMPORT_RE.search(text):
            # A route table lives wherever the router is imported — `main.tsx` as often as
            # `routes.tsx` — so the file is chosen by what it imports, never by its name.
            for i, line in enumerate(text.splitlines(), 1):
                m = UI_ROUTE_RE.search(line)
                if m and len(m.group(1)) > 1 and "." not in m.group(1).split("/")[-1]:
                    add("ui-route", m.group(1), f, i)

    # An operation's handler is where its behaviour lives; the spec only declares it. Resolve each
    # `operationId` to the non-generated function of that name (first letter either case).
    # A web client usually exports a function of the same name that CALLS the operation; the
    # server's definition wins over it, so a server language outranks a browser one.
    rank = {".go": 1, ".py": 1, ".ts": 2, ".js": 2}
    defs: dict[str, tuple[int, str]] = {}
    for f in code:
        suffix = Path(f).suffix
        if TEST_RE.search(f) or GENERATED_RE.search(f) or suffix not in rank:
            continue
        text = _read(f)
        if GENERATED_HEADER_RE.search(text[:600]):
            continue
        for line in text.splitlines():
            m = FUNC_DEF_RE.match(line)
            if m:
                name = m.group(1).lower()
                # A method outranks a plain function: generated server interfaces are
                # implemented as methods, and a seeder or script reusing the name is not.
                r = rank[suffix] - (1 if line.startswith("func (") else 0)
                if name not in defs or r < defs[name][0]:
                    defs[name] = (r, f)
    for s in surfaces:
        op = s.get("operation")
        if op and op.lower() in defs:
            s["handler"] = defs[op.lower()][1]

    # A table declared in a schema file and again in a migration is one table.
    seen: set[tuple[str, str, str]] = set()
    unique = []
    for s in surfaces:
        # A child route repeats a name (`:id`) in every feature; only the same file's repeat is one route.
        key = (s["kind"], s["name"].lower(), s["file"] if s["kind"] == "ui-route" else "")
        if s["kind"] in ("table", "ui-route") and key in seen:
            continue
        seen.add(key)
        unique.append(s)

    return {
        "depth": depth,
        "units": {
            u: {"files": sum(c.values()), "tests": tests[u], "languages": dict(c)} for u, c in sorted(units.items())
        },
        "surfaces": unique,
        "detectors": dict(fired),
    }


# ─────────────────────────────────── the corpus side ───────────────────────────────────


def component_owns() -> dict[str, str]:
    """`{owned path prefix: component id}` from the registry's `## Components` table."""
    out: dict[str, str] = {}
    if not REGISTRY.is_file():
        return out
    section = ""
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if section != "Components" or not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0].lower() == "id" or not set(cells[0]) - set("-: "):
            continue
        for p in (x.strip().strip("`") for x in cells[3].split(",") if x.strip()):
            out[p.rstrip("/")] = cells[0]
    return out


def route_claims() -> list[tuple[str, str]]:
    """`[(route prefix, component id)]` from the registry's `## Surface ownership` table.

    A route declared in one shared spec file (one spec document for the whole API) and
    served by one thin handler package belongs to the domain component behind it, which no
    file path says. The registry claims it by prefix instead; longest prefix wins.
    """
    out: list[tuple[str, str]] = []
    if not REGISTRY.is_file():
        return out
    section = ""
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if section != "Surface ownership" or not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() == "component" or not set(cells[0]) - set("-: "):
            continue
        out += [(p.strip().strip("`"), cells[0]) for p in cells[1].split(",") if p.strip()]
    return out


#: The surface kinds a route-prefix claim may place; a table or an entry point is placed by file.
ROUTE_KINDS = frozenset({"http", "http-route", "ui-route"})


def surface_owner(s: dict[str, Any], owns: dict[str, str], claims: list[tuple[str, str]]) -> str | None:
    """A surface's component: a route-prefix claim first, then its handler's file, then its own."""
    if s["kind"] not in ROUTE_KINDS:
        return owner(s.get("handler") or s["file"], owns) or owner(s["file"], owns)
    route = s["name"].split(" ", 1)[-1]
    hits = [(p, c) for p, c in claims if route == p or route.startswith(p.rstrip("*"))]
    if not hits and not route.startswith("/"):
        # A child route is declared relative to its parent (`bugs/:bugId` under `/settings`);
        # it matches a claim whose path ENDS with the child's leading segments.
        head = route.split("/")[0]
        hits = [(p, c) for p, c in claims if p.rstrip("/*").endswith("/" + head)]
    if hits:
        return max(hits, key=lambda x: len(x[0]))[1]
    return owner(s.get("handler") or s["file"], owns) or owner(s["file"], owns)


def owner(path: str, owns: dict[str, str]) -> str | None:
    best = None
    for prefix, comp in owns.items():
        covers = path == prefix or path.startswith(prefix + "/")
        if covers and (best is None or len(prefix) > len(best[0])):
            best = (prefix, comp)
    return best[1] if best else None


def feature_claims() -> tuple[list[str], list[str]]:
    """Every `source_of_truth:` path and every `surfaces:` entry across the feature maps."""
    paths: list[str] = []
    named: list[str] = []
    if not FEATURES.is_dir():
        return paths, named
    for f in sorted(FEATURES.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        fm = text.split("---", 2)[1]
        m = re.search(r"^surfaces:\s*\[(.*)\]\s*$", fm, re.M)
        if m:
            named += [x.strip().strip("\"'") for x in m.group(1).split(",") if x.strip()]
        block = re.search(r"^source_of_truth:\s*\n((?:\s+-\s+.+\n?)+)", fm, re.M)
        if block:
            paths += [ln.strip()[2:].strip().rstrip("/") for ln in block.group(1).splitlines() if ln.strip()]
    return paths, named


def excused_surfaces() -> set[str]:
    """Every surface a draft deliberately leaves undescribed, by name.

    A draft's `## Not described` section lists, in backticks, the surfaces the person agreed no
    capability covers (a debug route, a legacy redirect). They count as accounted for — never as
    "undescribed" — or every confirmed component would read stale forever.
    """
    out: set[str] = set()
    drafts = STATE_LAYOUT["drafts"]
    if not drafts.is_dir():
        return out
    for f in drafts.glob("*.md"):
        m = re.search(r"^## Not described[^\n]*\n(.*?)(?=^## |\Z)", f.read_text(encoding="utf-8"), re.M | re.S)
        if m:
            out |= {tok.strip() for tok in re.findall(r"`([^`]+)`", m.group(1))}
    return out


def coverage() -> dict[str, Any]:
    if not OUT.is_file():
        sys.exit("no inventory — run `kb_inventory.py scan` first")
    inv = json.loads(OUT.read_text(encoding="utf-8"))
    owns = component_owns()
    claims = route_claims()
    claimed_paths, named = feature_claims()
    excused = excused_surfaces()
    ledgered = ledger_files()  # files a sub-agent reported opening

    per: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"files": 0, "surfaces": 0, "described": 0, "read": 0, "excluded": 0, "unread": Counter()}
    )
    # Ownership is read per FILE, never per unit: a component may claim one page directory inside
    # a unit another component owns, and a unit-level reading would hide every such move.
    unowned_by_unit: Counter[str] = Counter()
    files = [f for f in tracked_files() if Path(f).suffix in CODE_EXT]
    for f in files:
        comp = owner(f, owns)
        if comp is None:
            unowned_by_unit[unit_of(f, inv["depth"])] += 1
            comp = "(unowned)"
        per[comp]["files"] += 1
        if comp == "(unowned)":
            continue
        # Mocks, fixtures and generated code carry no promise: counted, never in the denominator.
        if NOT_READ_RE.search(f) or GENERATED_RE.search(f):
            per[comp]["excluded"] += 1
            continue
        # A directory is read only when a feature map's `source_of_truth:` reaches the file. A
        # hand-listed surface is not a path, so it never stands in for reading the directory.
        if f in ledgered or any(f == p or f.startswith(p + "/") for p in claimed_paths):
            per[comp]["read"] += 1
        else:
            per[comp]["unread"][f.rsplit("/", 1)[0] if "/" in f else "."] += 1
    unowned: list[dict[str, Any]] = [{"unit": u, "files": n} for u, n in unowned_by_unit.items()]

    def reached(s: dict[str, Any]) -> bool:
        bare = s["name"].split(" ", 1)[-1]
        if s["name"] in excused or bare in excused:
            return True
        if any(
            f == p or f.startswith(p + "/") for f in (s["file"], s.get("handler") or "") if f for p in claimed_paths
        ):
            return True
        bare = s["name"].split(" ", 1)[-1]
        # A child route is recorded relative to its parent; a map names the full path.
        return bare in named or (not bare.startswith("/") and any(n.endswith("/" + bare) for n in named))

    undescribed = defaultdict(list)
    for s in inv["surfaces"]:
        comp = surface_owner(s, owns, claims) or "(unowned)"
        per[comp]["surfaces"] += 1
        if reached(s):
            per[comp]["described"] += 1
        else:
            undescribed[comp].append(f"{s['kind']} {s['name']} ({s['file']}:{s['line']})")

    total_files = len(files) or 1
    total_surf = len(inv["surfaces"]) or 1
    for v in per.values():
        v["unread"] = [
            {"unit": unit, "files": n} for unit, n in sorted(v["unread"].items(), key=lambda x: (-x[1], x[0]))
        ]
    return {
        "owned_file_ratio": round(1 - sum(x["files"] for x in unowned) / total_files, 3),
        "described_surface_ratio": round(sum(v["described"] for v in per.values()) / total_surf, 3),
        "excluded_from_read": sum(v["excluded"] for v in per.values()),
        "per_component": dict(sorted(per.items())),
        "unowned_units": sorted(unowned, key=lambda x: -x["files"]),
        "undescribed": dict(sorted(undescribed.items())),
    }


# ───────────────────────── the read plan and the ledger ─────────────────────────


def owned_files(comp: str) -> list[str]:
    """EVERY file `comp` owns that is source to be read: code, ZK pages, GraphQL schemas — tests
    included — minus only mocks, fixtures, test data, generated and vendored files."""
    owns = component_owns()
    return sorted(
        f
        for f in tracked_files()
        if Path(f).suffix in CODE_EXT
        and owner(f, owns) == comp
        and not NOT_READ_RE.search(f)
        and not GENERATED_RE.search(f)
    )


def plan_batches(
    files: list[str], max_files: int = BATCH_FILES, max_bytes: int = BATCH_BYTES, size: Any = None
) -> list[dict[str, Any]]:
    """Split `files` (kept in path order, so a batch is a neighbourhood) into batches of at most
    `max_files` files and `max_bytes` bytes. A file over the byte cap gets a batch of its own."""
    measure = size or (lambda f: len(_read(f).encode("utf-8", errors="ignore")))
    out: list[dict[str, Any]] = []
    cur: list[str] = []
    cur_bytes = 0
    for f in files:
        n = int(measure(f))
        if cur and (len(cur) >= max_files or cur_bytes + n > max_bytes):
            out.append({"files": cur, "bytes": cur_bytes})
            cur, cur_bytes = [], 0
        cur.append(f)
        cur_bytes += n
    if cur:
        out.append({"files": cur, "bytes": cur_bytes})
    for i, b in enumerate(out, 1):
        b["id"] = f"b{i:03d}"
    return out


def batch_plan_path(comp: str) -> Path:
    return STATE_LAYOUT["batches"] / f"{comp}.json"


def load_ledger() -> dict[str, dict[str, Any]]:
    """`{component: {batch id: {"files": [...], "at": iso}}}` — the files a sub-agent REPORTED opening."""
    p = STATE_LAYOUT["ledger"]
    if not p.is_file():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    return cast("dict[str, dict[str, Any]]", data.get("components", {}))


def ledger_files() -> set[str]:
    return {f for batches in load_ledger().values() for b in batches.values() for f in b["files"]}


def record_read(comp: str, batch_id: str, files: list[str]) -> tuple[int, list[str]]:
    """Write `files` into the ledger under the batch. Returns (recorded, rejected): a path that is
    not in that batch's plan is rejected, never recorded."""
    plan = batch_plan_path(comp)
    if not plan.is_file():
        sys.exit(f"no batch plan for {comp} — run `kb_inventory.py batches {comp}` first")
    batches = {b["id"]: b for b in json.loads(plan.read_text(encoding="utf-8"))["batches"]}
    if batch_id not in batches:
        sys.exit(f"{comp} has no batch {batch_id}; its batches are {', '.join(sorted(batches))}")
    allowed = set(batches[batch_id]["files"])
    ok = sorted({f for f in files if f in allowed})
    bad = sorted({f for f in files if f not in allowed})
    ledger = load_ledger()
    entry = ledger.setdefault(comp, {}).setdefault(batch_id, {"files": []})
    entry["files"] = sorted(set(entry["files"]) | set(ok))
    entry["at"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    STATE_LAYOUT["ledger"].parent.mkdir(parents=True, exist_ok=True)
    STATE_LAYOUT["ledger"].write_text(
        json.dumps({"components": ledger}, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return len(ok), bad


def carry_read(comp: str, total: int, read: int, unread: list[str]) -> tuple[int, str]:
    """Seed the ledger with what an EARLIER run read, so a continued run reads only the rest.

    The earlier run reported how many files the part had (`total`), how many it had read (`read`) and the
    files it had not (`unread`). The files read are the plan MINUS `unread` - recorded batch by batch exactly as
    `record` would, so the coverage gate stays the one judge. That is sound only while the plan still IS the
    plan the earlier run measured: if the file count moved, or the unread list does not account for the files
    that were read (it was cut short), a file the earlier run never saw would be taken as read. Then nothing is
    recorded and the reason is returned; the run reads the part again, whole. Returns (files carried, reason)
    with a reason of `""` when the ledger was seeded."""
    plan = batch_plan_path(comp)
    if not plan.is_file():
        sys.exit(f"no batch plan for {comp} — run `kb_inventory.py batches {comp}` first")
    batches = json.loads(plan.read_text(encoding="utf-8"))["batches"]
    planned = [f for b in batches for f in b["files"]]
    left = set(unread) & set(planned)
    if len(planned) != total:
        return 0, f"the part has {len(planned)} files now and the earlier run measured {total}"
    if len(planned) - len(left) != read:
        return 0, f"the earlier run's unread list names {len(left)} files, not the {total - read} it had left"
    carried = 0
    for b in batches:
        done = [f for f in b["files"] if f not in left]
        if done:
            got, _bad = record_read(comp, b["id"], done)
            carried += got
    return carried, ""


def gate(comp: str) -> dict[str, Any]:
    """Whether `comp` may be called done: every file of its plan must be read (ledger, or claimed
    by a feature map's `source_of_truth:`). No plan is itself a failure when files are unread."""
    claimed, _ = feature_claims()
    done = ledger_files()

    def is_read(f: str) -> bool:
        return f in done or any(f == p or f.startswith(p + "/") for p in claimed)

    plan = batch_plan_path(comp)
    if not plan.is_file():
        files = owned_files(comp)
        unread = [f for f in files if not is_read(f)]
        return {
            "component": comp,
            "passed": not unread,
            "planned": False,
            "files": len(files),
            "unread_files": unread,
            "open_batches": [],
        }
    batches = json.loads(plan.read_text(encoding="utf-8"))["batches"]
    open_b: list[str] = []
    unread = []
    for b in batches:
        miss = [f for f in b["files"] if not is_read(f)]
        if miss:
            open_b.append(b["id"])
            unread.extend(miss)
    return {
        "component": comp,
        "passed": not unread,
        "planned": True,
        "files": sum(len(b["files"]) for b in batches),
        "unread_files": unread,
        "open_batches": open_b,
    }


def gate_message(g: dict[str, Any]) -> str:
    if g["passed"]:
        return f"READ GATE PASSED: all {g['files']} files of {g['component']} are read."
    how = (
        f"Batches still open: {', '.join(g['open_batches'])}."
        if g["planned"]
        else f"No read plan exists; run `kb_inventory.py batches {g['component']}`."
    )
    return (
        f"NOT DONE: {len(g['unread_files'])} of {g['files']} files of {g['component']} are unread. "
        f"{how} Do not mark this component done or QA-ready until every batch's files are recorded."
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("layout", help="print where each artifact of the corpus is written")
    s = sub.add_parser("scan", help="enumerate units and surfaces into the run-state inventory")
    s.add_argument("--depth", type=int, default=2, help="directory depth a unit is rolled up to (default 2)")
    b = sub.add_parser("batches", help="plan EVERY file of a component into sub-agent-sized batches")
    b.add_argument("component")
    b.add_argument("--files", type=int, default=BATCH_FILES, help=f"max files per batch (default {BATCH_FILES})")
    b.add_argument("--bytes", type=int, default=BATCH_BYTES, help=f"max bytes per batch (default {BATCH_BYTES})")
    r = sub.add_parser("record", help="record the files a sub-agent read for one batch (paths on stdin)")
    r.add_argument("component")
    r.add_argument("batch")
    k = sub.add_parser(
        "carry", help="seed the ledger with what an earlier run read (its unread paths on stdin), for a continued run"
    )
    k.add_argument("component")
    k.add_argument("--total", type=int, required=True, help="files the earlier run measured the part at")
    k.add_argument("--read", type=int, required=True, help="files the earlier run had read")
    c = sub.add_parser("coverage", help="join the inventory to the corpus")
    c.add_argument("--gate", action="store_true", help="with --component: exit 1 while any file is unread")
    c.add_argument("--component", help="only this component's undescribed surfaces")
    c.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "layout":
        _repo.ensure_run_state_ignored()
        for key, rel in LAYOUT.items():
            print(f"{key:20} {(KNOWLEDGE / rel).relative_to(REPO)}")
        for key, path in STATE_LAYOUT.items():
            print(f"{key:20} {path.relative_to(REPO)}")
        return 0

    if args.cmd == "scan":
        if not os.environ.get("KB_INVENTORY_STATE"):  # a read-only measurement touches nothing in the tree
            _repo.ensure_run_state_ignored()
        inv = scan(args.depth)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(inv, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        where = OUT.relative_to(REPO) if OUT.is_relative_to(REPO) else OUT
        print(f"{len(inv['units'])} units, {len(inv['surfaces'])} surfaces → {where}")
        print("detectors fired: " + (", ".join(f"{k}={v}" for k, v in sorted(inv["detectors"].items())) or "none"))
        return 0

    if args.cmd == "batches":
        files = owned_files(args.component)
        if not files:
            sys.exit(f"{args.component} owns no source files (check the registry's `owns:` cell)")
        plan = plan_batches(files, args.files, args.bytes)
        path = batch_plan_path(args.component)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"component": args.component, "files": len(files), "batches": plan}, indent=1) + "\n",
            encoding="utf-8",
        )
        print(f"{args.component}: {len(files)} files in {len(plan)} batches -> {path}")
        for bt in plan:
            print(f"  {bt['id']}  {len(bt['files']):>3} files  {bt['bytes']:>8} bytes  {bt['files'][0]} ...")
        return 0

    if args.cmd == "record":
        got, bad = record_read(args.component, args.batch, [ln.strip() for ln in sys.stdin if ln.strip()])
        print(f"recorded {got} files for {args.component} {args.batch}")
        if bad:
            print(f"REJECTED {len(bad)} paths not in this batch: {', '.join(bad[:10])}")
            return 2
        return 0

    if args.cmd == "carry":
        carried, why = carry_read(args.component, args.total, args.read, [ln.strip() for ln in sys.stdin if ln.strip()])
        if why:
            print(f"REFUSED to carry the earlier reading: {why}. Read the whole part again.")
            return 3
        print(f"carried {carried} files already read into the ledger for {args.component}")
        return 0

    cov = coverage()
    if args.gate and not args.component:
        sys.exit("--gate needs --component")
    if args.component:
        g = gate(args.component)
        g["unread_count"] = len(g["unread_files"])
        g["message"] = gate_message(g)
        cov = {
            "undescribed": cov["undescribed"].get(args.component, []),
            "per_component": {args.component: cov["per_component"].get(args.component)},
            "gate": g,
        }
        print(json.dumps(cov, indent=1))
        if args.gate and not g["passed"]:
            print(g["message"], file=sys.stderr)
            return 1
        return 0
    if args.json:
        print(json.dumps(cov, indent=1))
        return 0
    print(f"excluded from read (mocks, fixtures, generated, vendored): {cov['excluded_from_read']}")
    print(f"owned files: {cov['owned_file_ratio']:.1%}   described surfaces: {cov['described_surface_ratio']:.1%}")
    print(f"{'component':32} {'files':>6} {'read':>6} {'excl.':>6} {'surfaces':>8} {'described':>9}")
    for comp, v in cov["per_component"].items():
        print(f"{comp:32} {v['files']:>6} {v['read']:>6} {v['excluded']:>6} {v['surfaces']:>8} {v['described']:>9}")
        for u in v.get("unread", []):
            print(f"  unread: {u['unit']} ({u['files']} files)")
    if cov["unowned_units"]:
        print("\nlargest unowned units:")
        for u in cov["unowned_units"][:15]:
            print(f"  {u['files']:>5}  {u['unit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
