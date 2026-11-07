"""Fleet's in-product docs: read the pages, check them against their contract, render them for an agent.

**ONE FOLDER, TWO READERS, AND THIS MODULE IS THE ONLY PARSER EITHER OF THEM TRUSTS.** The pages
under `productdocs/` are markdown with a closed catalogue of directive blocks. The web app draws
them as designed pages (`templates/docs.js`), and an agent reads the same file as plain markdown.
Both sides need the same answer to "what is a block, what are its attributes, where does it end",
and a second parser would be a second answer. So the service's routes, the CLI check, the dev
proxy and the agent rendering all come here.

**THE CONTRACT IS `productdocs/README.md`, AND `validate` IS ITS TEETH.** Every rule written there
is checked here: front-matter keys and values, the block catalogue and each block's attributes,
raw HTML, the index against the files, screen routes and their anchors, and every `:term[…]`
resolving against `terms.md` or the loop glossary the caller hands in. A rule the README does not
write is not invented here — with one exception named where it is made (two pages claiming the
same route), because the routes map the app reads can only hold one answer.

**STDLIB ONLY, DELIBERATELY** (the id kinds come from this package's stdlib-only `idkinds`).
`fleet-knowledge` runs under a bare `python3` as a commit gate, and `dev-proxy.py` imports this
file straight off `sys.path` with no environment at all. The YAML is
therefore the small subset the contract allows — scalars, quoted strings, flow lists `[a, b]`,
block lists `- x`, booleans and ints — and anything outside it is an error rather than a guess.

**`load` NEVER RAISES ON A BAD PAGE.** A page with broken front matter still loads (with what
could be read) and the problem is kept on `Docs.problems` for `validate` to report. The service
serves whatever is there; the check is what refuses it. A loader that raised would take the whole
Docs view down over one typo, which is the wrong party to be punished for it.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Protocol

from fleet_knowledge import idkinds

__all__ = [
    "PACKAGED",
    "SCREENS",
    "Docs",
    "Page",
    "Resolver",
    "Section",
    "StaticResolver",
    "bare_commands",
    "contents",
    "index_payload",
    "load",
    "page_payload",
    "parse_blocks",
    "render_agent",
    "render_files",
    "validate",
]

#: The pages as shipped. hatchling carries every file under the package directory, so these
#: `.md` files are in the wheel beside the `commandtree/*.md` files that already ship.
PACKAGED: Final = Path(__file__).resolve().parent / "productdocs"

#: The two files at the root that are not pages in the index. `terms.md` IS a page (it is served
#: at `id=terms`); `README.md` is the contract and nothing else.
INDEX_FILE: Final = "index.md"
TERMS_ID: Final = "terms"
#: The index's named sections. Any other `##` is a plain section of pages, as before jobs.
START_SECTION: Final = "Start here"
JOBS_SECTION: Final = "Jobs"
COMMON_SECTION: Final = "Common tasks"
CONTRACT_FILE: Final = "README.md"

# ── the vocabulary the contract names, spelled once ─────────────────────────

KEYS: Final = frozenset(
    {"title", "kind", "for", "summary", "routes", "sources", "mode", "minutes", "generated", "icon", "group"}
)
REQUIRED: Final = ("title", "kind", "for", "summary")
KINDS: Final = frozenset({"start", "concept", "guide", "troubleshooting", "reference", "job"})
#: The pictures a job card can carry, drawn by `docs.js` (`ICONS`). A job page sets one with `icon:`.
ICONS: Final = frozenset({"understand", "daily", "plan", "knowledge", "sessions", "tools", "team", "quality", "fix"})
#: Where a job sits on the Docs home: `learn` jobs are drawn large, with their picture, above the
#: `use` and `run` rows. A job page sets one with `group:`.
GROUPS: Final = ("learn", "use", "run")
AUDIENCES: Final = frozenset({"owner", "developer", "admin", "everyone"})
MODES: Final = frozenset({"programs", "areas", "any"})
SUMMARY_MAX: Final = 160

#: Which folder holds which kind. `guides/<group>/` is a guide at any depth below `guides/`.
FOLDER_KIND: Final = {
    "start": "start",
    "concepts": "concept",
    "knowledge-base": "concept",
    "guides": "guide",
    "troubleshooting": "troubleshooting",
    "reference": "reference",
    "jobs": "job",
}

CONTAINERS: Final = frozenset({"lede", "steps", "callout", "mode", "compare", "ideas"})
LEAVES: Final = frozenset(
    {"diagram", "live", "screen", "action", "cards", "command", "figure", "path", "pages", "embed"}
)
INLINES: Final = frozenset({"term", "kbd"})

STEP_WHO: Final = frozenset({"you", "fleet", "nobody"})
CALLOUT_KINDS: Final = frozenset({"why", "tip", "careful"})
DIAGRAMS: Final = frozenset({"work-line", "three-questions", "knowledge-folder", "knowledge-map", "fleet-map"})
LIVE_KINDS: Final = ("slice", "area", "prd", "program")
_LIVE_SHAPE: Final = {
    "slice": re.compile(r"SL-\d+"),
    "area": re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*"),
    "prd": re.compile(r"\d{4}"),
    "program": re.compile(r"PG-\d+"),
}

#: `::screen` routes and the anchors each one registers in `templates/docs-screens.js`, with the
#: page's name as the app draws it — the name an agent reads in `On the <Page> page (<url>):`.
#: Adding a route or an anchor is a change to the README's table, this map and that file at once.
SCREENS: Final[dict[str, tuple[str, tuple[str, ...]]]] = {
    "areas": ("Features", ("area", "slices", "prds", "next")),
    "cockpit": ("Cockpit", ("tabs", "views", "filter", "row")),
    "terminals": ("Terminals", ("new", "tile", "layouts", "composer", "dock")),
    "program": ("Program", ("slices", "proof", "levers")),
    "slice": ("Slice", ("done-when", "prds", "levers")),
    "issue": ("Issue", ("position", "actions", "blockers")),
    "queue": ("Queue", ("views", "next", "held")),
    "quality": ("Quality", ("line", "waiting", "ask")),
    "settings:my-mcp": ("My MCP config", ("editor", "save")),
    "settings:secrets": ("Secrets", ("add", "list")),
    "settings:machines": ("Machines", ("machine", "seats", "drain", "add")),
    "settings:repositories": ("Repositories", ("repo", "merge", "verify", "add")),
}

#: Figures registered in `templates/docs-figures.js`. EMPTY ON PURPOSE: the contract reserves
#: `::figure` until one is registered, so every use is an error until a name is added here and
#: there together.
FIGURES: Final[frozenset[str]] = frozenset()

#: `::embed{name}` — a live part of the app drawn inside a page, closed like the diagrams. The web
#: renderer asks the host for it (`ctx.embed(name)`); an agent reads the table of the same facts
#: below. Adding a name is a change to the README's table, this set, the agent rendering and the
#: app's `docsCtx` at once.
EMBEDS: Final = frozenset({"work-line"})

#: THE WORK LINE'S STEPS, for the agent rendering of `::embed{name="work-line"}`: band, step, who
#: has to be there, and the commands that run it. The app draws the same steps from its own table
#: (`WL_STATIONS` in `fleet-service`'s `app.js`), and a fleet-service test holds the two to the
#: same titles and attendance in the same order, so neither can drift alone.
WORK_LINE_BANDS: Final = (
    ("b1", "Decide what to build"),
    ("b2", "Make it buildable"),
    ("b3", "Build it"),
    ("b4", "Close it"),
)
WORK_LINE_ATTENDANCE: Final = {"alone": "runs alone", "asks": "asks you", "call": "your call", "derived": "derived"}
WORK_LINE: Final[tuple[tuple[str, str, str, str], ...]] = (
    ("b1", "File a feature request", "call", "idea:create"),
    ("b1", "Interview the filer", "asks", "intake"),
    ("b1", "Classify and propose", "alone", "route"),
    ("b1", "Accept the proposal", "call", "the idea page"),
    ("b1", "A task or a bug", "call", "task:create, bug:create (skips the ladder)"),
    ("b2", "Author the row or the stub", "asks", "program:create, slice:create, prd:create"),
    ("b2", "Shape the program", "asks", "program:shape (by hand: program:decompose)"),
    ("b2", "Refine the slice", "asks", "slice:refine (by hand: slice:edit)"),
    ("b2", "Draft the PRD", "asks", "prd:fill"),
    ("b2", "Design it", "asks", "prd:design"),
    ("b2", "Plan it", "alone", "prd:plan"),
    ("b3", "The triage gate", "alone", "check (the gate in)"),
    ("b3", "Answer a block", "call", "unblock"),
    ("b3", "Implement", "alone", "prd:implement, bug:fix, task:implement (never merges)"),
    ("b3", "Verify", "alone", "verify, prd:verify (the gate out; the only step that merges)"),
    ("b3", "Merged — the PRD is shipped", "derived", "—"),
    ("b4", "The slice reads complete", "derived", "—"),
    ("b4", "Name the composed proof", "asks", "program:prove"),
    ("b4", "Close the program", "alone", "program:ship"),
)

#: The commands `::command{name}` may name, read off the command tree this package ships.
_COMMANDS_ROOT: Final = Path(__file__).resolve().parent / "commandtree" / "commands"


def _shipped_commands() -> Path:
    """The one namespace folder the packaged command tree holds. Found, never named: the shipped
    namespace is the home repository's, and a customer's install renames it on sync."""
    dirs = sorted(p for p in _COMMANDS_ROOT.iterdir() if p.is_dir()) if _COMMANDS_ROOT.is_dir() else []
    return dirs[0] if dirs else _COMMANDS_ROOT


_ID_SEGMENT: Final = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
#: An app route key as written after `#`, parameter-free: `cockpit`, `settings:my-mcp`. A
#: parameter (`program:PG-40`) fails it by its capitals and digits-with-dash shape, which is the
#: point — the contract writes a parameterised route as its kind only.
_ROUTE_KEY: Final = re.compile(r"[a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?")
#: The settings panes a `settings:<pane id>` route may name — the contract's closed list, which is
#: the `id` column of `SETTINGS_PANES` in `api/static/app.js`.
SETTINGS_PANES: Final = frozenset(
    {
        "set-up",
        "secrets",
        "shared-mcp",
        "api-keys",
        "connect",
        "reports",
        "my-secrets",
        "my-mcp",
        "repositories",
        "models",
        "agents",
        "machines",
        "labels",
        "experimental",
    }
)
_COMMAND_NAME: Final = re.compile(r"[a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)*")


# ── the model ───────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Page:
    """One markdown file: its id, its front matter as data, and the markdown after it.

    `line` is the file line the body starts on, so a problem in the body is reported at the line
    a writer sees in their editor rather than at an offset into a string they never see.
    """

    id: str
    meta: dict[str, Any]
    body: str
    path: Path
    line: int = 1


@dataclass(frozen=True, slots=True)
class Section:
    """One `##` of the index and the page ids under it, in reading order."""

    title: str
    ids: tuple[str, ...]
    labels: tuple[str, ...] = ()


@dataclass(slots=True)
class Docs:
    """Every page, the index's sections, and what `load` could not read."""

    root: Path
    index: list[Section] = field(default_factory=list)
    pages: dict[str, Page] = field(default_factory=dict)
    index_meta: dict[str, Any] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)

    def section(self, title: str) -> Section | None:
        """The index's `## title` section, or None."""
        return next((s for s in self.index if s.title == title), None)

    def jobs(self) -> list[tuple[str, list[str], list[str]]]:
        """Each job the index lists, in order: its page id, its `::path` ids, its `::pages` ids.

        THE JOB PAGE OWNS ITS PAGES. The index lists the nine jobs and nothing under them; which
        pages a job leads to, and in what order, is written once — in the job page's own
        `::path{links}` and `::pages{links}` — so the page an agent reads and the home a person
        reads cannot disagree about it.
        """
        listed = self.section(JOBS_SECTION)
        out: list[tuple[str, list[str], list[str]]] = []
        for job_id in listed.ids if listed else ():
            page = self.pages.get(job_id)
            path: list[str] = []
            more: list[str] = []
            for m in _JOB_LINKS.finditer(page.body if page else ""):
                attrs, _ = _attrs(m.group(2))
                ids = [x.strip() for x in str(attrs.get("links", "")).split(",") if x.strip()]
                (path if m.group(1) == "path" else more).extend(ids)
            out.append((job_id, path, more))
        return out

    def owner(self) -> dict[str, str]:
        """Page id → the id of the job that leads to it (a job page owns itself)."""
        owns: dict[str, str] = {}
        for job_id, path, more in self.jobs():
            owns.setdefault(job_id, job_id)
            for page_id in path + more:
                owns.setdefault(page_id, job_id)
        return owns

    def reading_order(self) -> list[str]:
        """Every reachable page, once: each job, then its path, then its other pages; then the rest.

        Previous and next follow this order, so a reader who keeps pressing Next reads a job end
        to end before the next job's page introduces it. An index without a `## Jobs` section is
        read section by section, as written.
        """
        seen: list[str] = []

        def add(page_id: str) -> None:
            if page_id in self.pages and page_id not in seen:
                seen.append(page_id)

        for job_id, path, more in self.jobs():
            for page_id in [job_id, *path, *more]:
                add(page_id)
        for section in self.index:
            if section.title not in (JOBS_SECTION, START_SECTION, COMMON_SECTION):
                for page_id in section.ids:
                    add(page_id)
        if not self.jobs():
            for section in self.index:
                for page_id in section.ids:
                    add(page_id)
        return seen


class Resolver(Protocol):
    """What `render_agent` needs from wherever it runs: live knowledge, words, pages, URLs."""

    def live(self, kind: str, id: str) -> dict[str, Any] | None: ...  # noqa: A002

    def term(self, word: str) -> str | None: ...

    def page(self, id: str) -> tuple[str, str] | None: ...  # noqa: A002

    def url(self, route: str) -> str: ...

    def mode(self) -> str: ...

    def command(self, name: str) -> tuple[str, str] | None: ...


# ── front matter: the YAML subset the contract allows ───────────────────────


def _strip_comment(value: str) -> str:
    """Cut a `# comment` that stands outside quotes and after whitespace (or at the start)."""
    quote = ""
    for i, ch in enumerate(value):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or value[i - 1].isspace()):
            return value[:i].rstrip()
    return value.rstrip()


def _scalar(raw: str) -> Any:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        inner = raw[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\") if raw[0] == '"' else inner.replace("''", "'")
    if raw in ("true", "false"):
        return raw == "true"
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    return raw


def _flow_list(raw: str) -> list[Any]:
    inner = raw.strip()[1:-1]
    items: list[str] = []
    cur, quote = "", ""
    for ch in inner:
        if quote:
            cur += ch
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
            cur += ch
        elif ch == ",":
            items.append(cur)
            cur = ""
        else:
            cur += ch
    items.append(cur)
    return [_scalar(item) for item in items if item.strip()]


def _frontmatter(text: str) -> tuple[dict[str, Any], str, int, list[str]]:
    """`(meta, body, body_line, problems)`. Never raises: what cannot be read is a problem."""
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text, 1, ["no front matter: a page starts with a `---` line"]
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, text, 1, ["front matter is never closed with a `---` line"]
    meta: dict[str, Any] = {}
    problems: list[str] = []
    pending: str | None = None
    for n, line in enumerate(lines[1:end], start=2):
        stripped = _strip_comment(line)
        if not stripped.strip():
            continue
        item = re.match(r"^\s*-\s+(.*)$", stripped)
        if item and pending is not None:
            meta[pending].append(_scalar(item.group(1)))
            continue
        pair = re.match(r"^([A-Za-z_][\w-]*):(?:\s+(.*))?$", stripped)
        if not pair or line[:1].isspace():
            problems.append(f"line {n}: cannot read front matter `{line.strip()}`")
            pending = None
            continue
        key, value = pair.group(1), (pair.group(2) or "").strip()
        if key in meta:
            problems.append(f"line {n}: front-matter key `{key}` appears twice")
        if not value:
            meta[key] = []
            pending = key
        elif value.startswith("["):
            if not value.endswith("]"):
                problems.append(f"line {n}: list for `{key}` is never closed with `]`")
            meta[key] = _flow_list(value if value.endswith("]") else value + "]")
            pending = None
        else:
            meta[key] = _scalar(value)
            pending = None
    body_lines = lines[end + 1 :]
    skipped = 0
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)
        skipped += 1
    return meta, "\n".join(body_lines), end + 2 + skipped, problems


# ── loading ─────────────────────────────────────────────────────────────────


def load(root: Path | None = None) -> Docs:
    """Every page under `root` (default: the packaged `productdocs/`) and the index's sections."""
    root = (root or PACKAGED).resolve()
    docs = Docs(root=root)
    if not root.is_dir():
        docs.problems.append(f"{root}: the docs folder does not exist")
        return docs
    index_path = root / INDEX_FILE
    if index_path.is_file():
        _load_index(docs, index_path)
    else:
        docs.problems.append(f"{INDEX_FILE}: the index is missing")
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if rel in (INDEX_FILE, CONTRACT_FILE):
            continue
        page_id = rel[: -len(".md")]
        meta, body, line, problems = _frontmatter(path.read_text(encoding="utf-8"))
        docs.problems.extend(f"{rel}: {p}" for p in problems)
        docs.pages[page_id] = Page(id=page_id, meta=meta, body=body, path=path, line=line)
    return docs


def _load_index(docs: Docs, path: Path) -> None:
    meta, body, first, problems = _frontmatter(path.read_text(encoding="utf-8"))
    docs.index_meta = meta
    docs.problems.extend(f"{INDEX_FILE}: {p}" for p in problems)
    title: str | None = None
    ids: list[str] = []
    labels: list[str] = []
    for n, line in enumerate(body.split("\n"), start=first):
        if not line.strip():
            continue
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        bullet = re.match(r"^[-*]\s+([^\s:]+)(?::\s+(.+?))?\s*$", line)
        if heading:
            if title is not None:
                docs.index.append(Section(title, tuple(ids), tuple(labels)))
            title, ids, labels = heading.group(1), [], []
        elif bullet and title is not None:
            ids.append(bullet.group(1))
            labels.append(bullet.group(2) or "")
        else:
            docs.problems.append(
                f"{INDEX_FILE}:{n}: the index holds only `## Section` headings and `- page/id` bullets under them"
            )
    if title is not None:
        docs.index.append(Section(title, tuple(ids), tuple(labels)))


# ── the HTTP shapes ─────────────────────────────────────────────────────────


def _card(page: Page) -> dict[str, Any]:
    minutes = page.meta.get("minutes")
    audience = page.meta.get("for")
    return {
        "id": page.id,
        "title": page.meta.get("title", page.id),
        "summary": page.meta.get("summary", ""),
        "kind": page.meta.get("kind", ""),
        "for": list(audience) if isinstance(audience, list) else ([audience] if audience else []),
        "minutes": minutes if isinstance(minutes, int) and not isinstance(minutes, bool) else None,
    }


def sections_of(docs: Docs) -> list[dict[str, Any]]:
    """The contents as sections of page cards: one per job (its page, its path, its other pages),
    then every plain section of the index. What a breadcrumb, a search hit and the help panel
    name as the place a page lives. An index with no jobs is its own sections, as written."""
    out = [
        {
            "title": str(docs.pages[job_id].meta.get("title", job_id)),
            "id": job_id,
            "pages": [_card(docs.pages[i]) for i in dict.fromkeys([job_id, *path, *more]) if i in docs.pages],
        }
        for job_id, path, more in docs.jobs()
        if job_id in docs.pages
    ]
    named = (JOBS_SECTION, START_SECTION, COMMON_SECTION) if out else ()
    out += [
        {"title": s.title, "pages": [_card(docs.pages[i]) for i in s.ids if i in docs.pages]}
        for s in docs.index
        if s.title not in named
    ]
    return out


def index_payload(docs: Docs) -> dict[str, Any]:
    """`GET /api/docs/index`: the home's parts, the contents as sections, and route key → page id.

    THE HOME IS JOBS, NOT A LIST OF PAGES. `start` is the one page a newcomer reads first; `jobs`
    is each job's card with its first three reads and how many pages it leads to; `common` is
    the short list of tasks people come for most, each with the words the home shows; and
    `reference` is the generated pages. `sections` is the same contents as cards per job, for
    whatever needs to say where a page lives.

    A listed id with no file is left out rather than drawn as a dead card; `validate` is where
    that is an error. A route claimed twice goes to the page the index lists first.
    """
    sections = sections_of(docs)
    start = docs.section(START_SECTION)
    common = docs.section(COMMON_SECTION)
    reference = docs.section("Reference")
    jobs = []
    for job_id, path, more in docs.jobs():
        page = docs.pages.get(job_id)
        if page is None:
            continue
        card = _card(page)
        card["icon"] = page.meta.get("icon", "")
        card["count"] = len(dict.fromkeys(i for i in [*path, *more] if i in docs.pages))
        card["group"] = page.meta.get("group", "")
        card["path"] = [_card(docs.pages[i]) for i in path if i in docs.pages]
        jobs.append(card)
    routes: dict[str, str] = {}
    order = docs.reading_order() + sorted(set(docs.pages) - set(docs.reading_order()))
    for page_id in order:
        for route in _as_list(docs.pages[page_id].meta.get("routes")):
            if isinstance(route, str):
                routes.setdefault(route, page_id)
    return {
        "sections": sections,
        "routes": routes,
        "start": next((_card(docs.pages[i]) for i in (start.ids if start else ()) if i in docs.pages), None),
        "jobs": jobs,
        "common": [
            {**_card(docs.pages[i]), "label": label or str(docs.pages[i].meta.get("title", i))}
            for i, label in zip(common.ids, common.labels or ("",) * len(common.ids), strict=False)
            if i in docs.pages
        ]
        if common
        else [],
        "reference": [_card(docs.pages[i]) for i in (reference.ids if reference else ()) if i in docs.pages],
    }


def command_purpose(name: str) -> str | None:
    """A shipped command's one-line purpose (its spine's `intent`), or None when Fleet ships no such
    command. Read from the command tree inside this package — the one `fleet commands sync`
    installs — so a page can name a command on a repository whose own tree is not readable."""
    if not _COMMAND_NAME.fullmatch(name) or not _command_exists(name):
        return None
    text = (_shipped_commands() / Path(*name.split(":"))).with_suffix(".md").read_text(encoding="utf-8")
    for raw in re.findall(r"```json\s*\n(.*?)\n```", text, re.S):
        try:
            block = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(block, dict) and "command" in block:
            return str(block.get("intent") or "")
    return ""


def page_payload(docs: Docs, id: str) -> dict[str, Any] | None:  # noqa: A002
    """`GET /api/docs/page?id=`: one page, with its neighbours in reading order. None is a 404."""
    page = docs.pages.get(id)
    if page is None:
        return None
    order = docs.reading_order()
    prev = nxt = None
    if id in order:
        at = order.index(id)
        prev = order[at - 1] if at > 0 else None
        nxt = order[at + 1] if at + 1 < len(order) else None

    def link(page_id: str | None) -> dict[str, str] | None:
        if page_id is None:
            return None
        return {"id": page_id, "title": str(docs.pages[page_id].meta.get("title", page_id))}

    commands = {}
    for m in re.finditer(r"^\s*::command\{(.*)\}\s*$", page.body, re.M):
        name = _attrs(m.group(1))[0].get("name")
        if isinstance(name, str) and (purpose := command_purpose(name)) is not None:
            commands[name] = purpose
    return {
        "id": page.id,
        "meta": dict(page.meta),
        "body": page.body,
        "prev": link(prev),
        "next": link(nxt),
        # Fleet's own commands this page names, with their purposes, for a repository whose tree
        # the app cannot read (`docs.js` asks the repository's tree first).
        "commands": commands,
    }


_JOB_LINKS: Final = re.compile(r"^\s*::(path|pages)\{(.*)\}\s*$", re.MULTILINE)
_IDEA: Final = re.compile(r"^\s*[-*]\s+\*\*(.+?)\*\*\s*(.*)$")

_MD_NOISE: Final = re.compile(r"[*_`>|]|^\s*(?:[-+]|\d+\.)\s+(?:\[(?:you|fleet|nobody)\]\s*)?|^#+\s*", re.MULTILINE)


def heading_anchor(text: str) -> str:
    """A heading's anchor exactly as `docs.js`'s `slug` derives it, so a search hit lands on it."""
    flat = re.sub(r":(?:term|kbd)\[([^\]]*)\]", r"\1", text.lower())
    flat = re.sub(r"[`*_]", "", flat)
    flat = re.sub(r"[^a-z0-9]+", "-", flat).strip("-")[:60].rstrip("-")
    return "dx-h-" + (flat or "x")


def _search_text(text: str) -> str:
    """A run of page markdown as the words a reader sees: links to their text, inlines to their word."""
    text = _LINK.sub(lambda m: m.group(1), text)
    text = _INLINE.sub(lambda m: m.group(2), text)
    text = re.sub(r"::[a-z][\w-]*\[([^\]]*)\]\{[^}]*\}", r"\1", text)
    return re.sub(r"\s+", " ", _MD_NOISE.sub(" ", text)).strip()


def _flush(sections: list[dict[str, str]], head: str, anchor: str, buf: list[str]) -> None:
    """Close one section of `search_payload`: its heading, its anchor and its words."""
    text = " ".join(t for t in (_search_text(line) for line in buf) if t)
    if text or head:
        sections.append({"h": head, "a": anchor, "t": text})


def search_payload(docs: Docs) -> dict[str, Any]:
    """`GET /api/docs/search`: every listed page cut at its headings into plain-text sections.

    THE BROWSER SEARCHES, NOT THE SERVER. The whole docs set is a few hundred kilobytes of text and
    the same on every deployment, so it is read once and matched as the reader types — no round
    trip per keystroke, and no index to keep in step with the files. Each section carries the
    heading's anchor (`heading_anchor`, the renderer's own derivation) so a hit opens at its place.
    Directive lines (`:::steps`, `::screen{…}`, a closing `:::`) are structure, not words, and are
    left out; the words inside a block are kept.
    """
    out: list[dict[str, Any]] = []
    section_of = {c["id"]: s["title"] for s in sections_of(docs) for c in s["pages"]}
    for page_id in docs.reading_order():
        page = docs.pages.get(page_id)
        if page is None:
            continue
        sections: list[dict[str, str]] = []
        head, anchor = "", ""
        buf: list[str] = []

        fence = False
        for raw in page.body.split("\n"):
            if _FENCE.match(raw):
                fence = not fence
                continue
            m = re.match(r"^(#{2,3})\s+(.+?)\s*$", raw) if not fence else None
            if m:
                _flush(sections, head, anchor, buf)
                head, anchor, buf = _search_text(m.group(2)), heading_anchor(m.group(2)), []
                continue
            if not fence and (
                _OPEN.match(raw)
                or raw.strip() == ":::"
                or (_LEAF.match(raw) and not raw.lstrip().startswith("::action"))
            ):
                continue
            buf.append(raw)
        _flush(sections, head, anchor, buf)
        card = _card(page)
        out.append(
            {
                "id": page.id,
                "title": card["title"],
                "summary": card["summary"],
                "kind": card["kind"],
                "section": section_of.get(page.id, ""),
                "sections": sections,
            }
        )
    return {"pages": out}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return list(value) if isinstance(value, list) else [value]


# ── blocks ──────────────────────────────────────────────────────────────────

_FENCE: Final = re.compile(r"^\s*(```|~~~)")
_OPEN: Final = re.compile(r"^:::([A-Za-z][\w-]*)(?:\{(.*)\})?\s*$")
_CLOSE: Final = re.compile(r"^:::\s*$")
_LEAF: Final = re.compile(r"^\s*::([A-Za-z][\w-]*)(?:\[([^\]]*)\])?(?:\{(.*)\})?\s*$")
_HEADING: Final = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_ATTR: Final = re.compile(r'([A-Za-z][\w-]*)(?:=(?:"([^"]*)"|([^\s"}]+)))?')
_LEGEND: Final = re.compile(r"^\d+\.\s+(.*)$")
_STEP: Final = re.compile(r"^- \[(\w+)\]\s*(.*)$")
_STEP_TITLE: Final = re.compile(r"^\*\*(.+?)\*\*\s*(.*)$")


def _attrs(raw: str | None) -> tuple[dict[str, Any], str | None]:
    """`key="value"`, `key=value` or a bare `flag`. Anything left over is reported, not dropped."""
    if not raw:
        return {}, None
    out: dict[str, Any] = {}
    rest = raw
    for m in _ATTR.finditer(raw):
        key = m.group(1)
        out[key] = m.group(2) if m.group(2) is not None else (m.group(3) if m.group(3) is not None else True)
        rest = rest.replace(m.group(0), " ", 1)
    leftover = rest.strip()
    return out, (f"cannot read attributes `{raw}`" if leftover else None)


def parse_blocks(body: str, line: int = 1) -> list[dict[str, Any]]:
    """The block tree of a page body.

    Nodes are dicts with a `type`:
      * `heading` — `level`, `text`
      * `markdown` — `text`: plain markdown, kept raw, for `Board.mdBlock` or an agent to read
      * `container` — `name`, `attrs`, `body` (raw), `children` (parsed body); a `steps`
        container also carries `items`: `[{who, title, text, children, line}]`
      * `modes` — adjacent `:::mode` containers, merged: `items` (each a `container`)
      * `leaf` — `name`, `label`, `attrs`; a `screen` also carries `legend` (its numbered list)
      * `error` — `message`: something the parser could not take as written
    Every node carries `line`, the file line it starts on when `line` is the body's first line.
    """
    nodes: list[dict[str, Any]] = []
    lines = body.replace("\r\n", "\n").split("\n")
    chunk: list[str] = []
    chunk_at = line
    i = 0

    def flush() -> None:
        nonlocal chunk
        text = "\n".join(chunk).strip("\n")
        if text.strip():
            nodes.append({"type": "markdown", "text": text, "line": chunk_at})
        chunk = []

    def add_chunk(text: str, at: int) -> None:
        nonlocal chunk_at
        if not chunk:
            chunk_at = at
        chunk.append(text)

    while i < len(lines):
        text, at = lines[i], line + i
        if _FENCE.match(text):
            add_chunk(text, at)
            marker = _FENCE.match(text).group(1)  # type: ignore[union-attr]
            i += 1
            while i < len(lines):
                chunk.append(lines[i])
                if lines[i].strip().startswith(marker):
                    break
                i += 1
            i += 1
            continue
        if not text.strip():
            flush()
            i += 1
            continue
        heading = _HEADING.match(text)
        if heading:
            flush()
            nodes.append({"type": "heading", "level": len(heading.group(1)), "text": heading.group(2), "line": at})
            i += 1
            continue
        if _CLOSE.match(text):
            flush()
            nodes.append({"type": "error", "message": "a `:::` closes no open block", "line": at})
            i += 1
            continue
        opened = _OPEN.match(text)
        if opened:
            flush()
            i = _container(lines, i, line, opened, nodes)
            continue
        leaf = _LEAF.match(text)
        if leaf:
            flush()
            node = _leaf_node(leaf, at)
            i += 1
            if node.get("name") == "screen":
                while i < len(lines) and _LEGEND.match(lines[i]):
                    node["legend"].append(_LEGEND.match(lines[i]).group(1))  # type: ignore[union-attr]
                    i += 1
            nodes.append(node)
            continue
        add_chunk(text, at)
        i += 1
    flush()
    return _merge_modes(nodes)


def _leaf_node(m: re.Match[str], at: int) -> dict[str, Any]:
    name = m.group(1)
    if name not in LEAVES:
        return {"type": "error", "message": f"unknown block `::{name}`", "line": at}
    attrs, problem = _attrs(m.group(3))
    node: dict[str, Any] = {"type": "leaf", "name": name, "label": m.group(2), "attrs": attrs, "line": at}
    if problem:
        node["problem"] = problem
    if name == "screen":
        node["legend"] = []
    return node


def _container(lines: list[str], i: int, line: int, opened: re.Match[str], nodes: list[dict[str, Any]]) -> int:
    name, start = opened.group(1), line + i
    body: list[str] = []
    errors: list[dict[str, Any]] = []
    i += 1
    fence: str | None = None
    closed = False
    while i < len(lines):
        text = lines[i]
        fm = _FENCE.match(text)
        if fence is None and fm:
            fence = fm.group(1)
        elif fence is not None and text.strip().startswith(fence):
            fence = None
        elif fence is None and _CLOSE.match(text):
            closed = True
            break
        elif fence is None and _OPEN.match(text):
            errors.append(
                {
                    "type": "error",
                    "message": f"`:::{name}` holds another container; containers do not nest",
                    "line": line + i,
                }
            )
        body.append(text)
        i += 1
    if not closed:
        errors.append({"type": "error", "message": f"`:::{name}` is never closed with `:::`", "line": start})
    if name not in CONTAINERS:
        nodes.append({"type": "error", "message": f"unknown block `:::{name}`", "line": start})
        nodes.extend(errors)
        return i + 1
    attrs, problem = _attrs(opened.group(2))
    raw = "\n".join(body)
    node: dict[str, Any] = {"type": "container", "name": name, "attrs": attrs, "body": raw, "line": start}
    if problem:
        node["problem"] = problem
    if name == "steps":
        node["items"], node["children"] = _steps(body, start + 1), []
    else:
        node["children"] = parse_blocks(raw, start + 1)
    nodes.append(node)
    nodes.extend(errors)
    return i + 1


def _steps(body: list[str], line: int) -> list[dict[str, Any]]:
    """The items of a `:::steps` body. A line that is neither an item nor an indented
    continuation of one becomes an item-less `error` entry, kept so `validate` can name it."""
    items: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    for n, text in enumerate(body, start=line):
        m = _STEP.match(text)
        if m:
            cur = {"who": m.group(1), "lines": [m.group(2)], "line": n}
            items.append(cur)
        elif cur is not None and (text.startswith("  ") or not text.strip()):
            cur["lines"].append(text[2:] if text.startswith("  ") else "")
        elif text.strip():
            items.append(
                {
                    "who": None,
                    "error": f"`{text.strip()}` is not a step (`- [you|fleet|nobody] **Title.** text`)",
                    "line": n,
                }
            )
    out: list[dict[str, Any]] = []
    for item in items:
        if "error" in item:
            out.append(item)
            continue
        first, rest = item["lines"][0], item["lines"][1:]
        tm = _STEP_TITLE.match(first)
        title = tm.group(1) if tm else ""
        text = "\n".join([tm.group(2) if tm else first, *rest]).strip("\n")
        out.append(
            {
                "who": item["who"],
                "title": title,
                "text": text,
                "children": parse_blocks(text, item["line"]),
                "line": item["line"],
            }
        )
    return out


def _merge_modes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for node in nodes:
        if node["type"] == "container" and node["name"] == "mode":
            last = out[-1] if out else None
            if last is not None and last["type"] == "modes":
                last["items"].append(node)
            else:
                out.append({"type": "modes", "items": [node], "line": node["line"]})
        else:
            out.append(node)
    return out


def _walk(nodes: Iterable[dict[str, Any]], parent: str | None = None) -> Iterator[tuple[dict[str, Any], str | None]]:
    """Every node with the name of the container it sits in (`None` at the top level)."""
    for node in nodes:
        yield node, parent
        if node["type"] == "modes":
            yield from _walk(node["items"], parent)
        elif node["type"] == "container":
            yield from _walk(node.get("children", []), node["name"])
            for item in node.get("items", []):
                yield from _walk(item.get("children", []), "steps")


# ── inline text ─────────────────────────────────────────────────────────────

_CODE_SPAN: Final = re.compile(r"`[^`\n]*`")
_INLINE: Final = re.compile(r"(?<![\w:]):([a-z][a-z-]*)\[([^\]]*)\]")
_HTML: Final = re.compile(r"<(?:/?[A-Za-z][\w-]*(?:\s[^<>]*)?/?|!--.*?--)>")
_LINK: Final = re.compile(r"(?<!:)\[([^\]]*)\]\(([^)\s]+)\)")


def _prose_lines(text: str, line: int) -> Iterator[tuple[int, str]]:
    """Each line outside a code fence, with code spans blanked — the text rules apply to."""
    fence: str | None = None
    for n, raw in enumerate(text.split("\n"), start=line):
        fm = _FENCE.match(raw)
        if fence is None and fm:
            fence = fm.group(1)
            continue
        if fence is not None:
            if raw.strip().startswith(fence):
                fence = None
            continue
        yield n, _CODE_SPAN.sub(lambda m: " " * len(m.group(0)), raw)


def _plain(text: str, terms: list[str] | None = None) -> str:
    """An inline directive as an agent reads it: the word, or the keys. Code spans untouched."""

    def swap(m: re.Match[str]) -> str:
        if m.group(1) == "term" and terms is not None and m.group(2).lower() not in (t.lower() for t in terms):
            terms.append(m.group(2))
        return m.group(2) if m.group(1) in INLINES else m.group(0)

    parts = re.split(r"(`[^`\n]*`)", text)
    return "".join(p if p.startswith("`") else _INLINE.sub(swap, p) for p in parts)


# ── validation ──────────────────────────────────────────────────────────────


def terms_of(docs: Docs) -> dict[str, str]:
    """`terms.md`'s words, lowercased, to their one-sentence definitions."""
    page = docs.pages.get(TERMS_ID)
    out: dict[str, str] = {}
    if page is None:
        return out
    for text in page.body.split("\n"):
        m = re.match(r"^- \*\*(.+?)\*\*:\s*(.+)$", text)
        if m:
            out[m.group(1).strip().lower()] = m.group(2).strip()
    return out


def _command_exists(name: str) -> bool:
    parts = name.split(":")
    return (_shipped_commands() / Path(*parts)).with_suffix(".md").is_file()


def validate(
    docs: Docs,
    loop_words: Iterable[str] = (),
    *,
    route_keys: Iterable[str] | None = None,
    repo_root: Path | None = None,
) -> list[str]:
    """Every way the folder breaks `productdocs/README.md`, as `path:line: message` strings.

    `loop_words` are the loop glossary's words (`fleet_service/api/glossary.py`), which this
    package may not import — the caller that can see them hands them in. `route_keys`, when
    given, is the app's closed set of route keys; without it a route is checked for shape only.
    `repo_root`, when given, makes every `sources:` path have to exist under it.
    """
    errors = list(docs.problems)
    words = {w.lower() for w in terms_of(docs)} | {w.lower() for w in loop_words}
    known_routes = frozenset(route_keys) if route_keys is not None else None

    def route_ok(route: Any) -> bool:
        return (
            isinstance(route, str)
            and bool(_ROUTE_KEY.fullmatch(route))
            and (not route.startswith("settings:") or route.split(":", 1)[1] in SETTINGS_PANES)
            and (known_routes is None or route in known_routes)
        )

    # the index
    if docs.index_meta.get("kind") != "start":
        errors.append(f"{INDEX_FILE}: front matter must say `kind: start`")
    if not isinstance(docs.index_meta.get("title"), str) or not docs.index_meta.get("title"):
        errors.append(f"{INDEX_FILE}: front matter needs a `title`")
    errors.extend(f"{INDEX_FILE}: unknown front-matter key `{k}`" for k in docs.index_meta if k not in KEYS)
    listed: list[str] = [i for s in docs.index if s.title not in (START_SECTION, COMMON_SECTION) for i in s.ids]
    pointers: list[str] = [i for s in docs.index if s.title in (START_SECTION, COMMON_SECTION) for i in s.ids]
    for page_id in sorted({i for i in listed if listed.count(i) > 1}):
        errors.append(f"{INDEX_FILE}: `{page_id}` is listed more than once")
    for page_id in listed + pointers:
        if page_id == TERMS_ID:
            errors.append(f"{INDEX_FILE}: `terms` is not listed in the index")
        elif page_id not in docs.pages:
            errors.append(f"{INDEX_FILE}: `{page_id}` is listed but there is no `{page_id}.md`")
    jobs = docs.jobs()
    if jobs:
        # A JOB LEADS TO A PAGE, AND EXACTLY ONE DOES: that job is the page's place — its
        # breadcrumb, its previous and next — so a page two jobs claim would have two places.
        claims: dict[str, list[str]] = {}
        for job_id, path, more in jobs:
            if job_id in docs.pages and docs.pages[job_id].meta.get("kind") != "job":
                errors.append(f"{INDEX_FILE}: `{job_id}` is under `## {JOBS_SECTION}` but is not `kind: job`")
            for page_id in dict.fromkeys(path + more):
                claims.setdefault(page_id, []).append(job_id)
        for page_id, by in sorted(claims.items()):
            if len(by) > 1:
                errors.append(f"{page_id}.md: the page is led to by more than one job ({', '.join(by)})")
        reached = set(claims) | {j for j, _, _ in jobs} | set(listed)
        for page_id in pointers:
            if page_id in docs.pages and page_id not in claims:
                errors.append(f"{INDEX_FILE}: `{page_id}` is pointed to but no job leads to it")
    else:
        reached = set(listed)
    for page_id in sorted(docs.pages):
        if page_id != TERMS_ID and page_id not in reached:
            where = "a job's `::path` or `::pages`" if jobs else INDEX_FILE
            errors.append(f"{page_id}.md: the page is not reached from {where}")

    # one route, one page
    claimed: dict[str, str] = {}
    for page_id in sorted(docs.pages):
        for route in _as_list(docs.pages[page_id].meta.get("routes")):
            if isinstance(route, str) and route in claimed:
                errors.append(f"{page_id}.md: route `{route}` is already claimed by `{claimed[route]}`")
            elif isinstance(route, str):
                claimed[route] = page_id

    for page_id in sorted(docs.pages):
        errors.extend(_validate_page(docs, docs.pages[page_id], words, route_ok, repo_root))
    return errors


def _validate_page(docs: Docs, page: Page, words: set[str], route_ok: Any, repo_root: Path | None) -> list[str]:
    rel = f"{page.id}.md"
    errs: list[str] = []
    meta = page.meta

    def at(n: int, msg: str) -> None:
        errs.append(f"{rel}:{n}: {msg}")

    # where it lives and what it is called
    segments = page.id.split("/")
    if not all(_ID_SEGMENT.fullmatch(s) for s in segments):
        errs.append(f"{rel}: file names are lowercase and hyphenated")
    is_terms = page.id == TERMS_ID
    folder = segments[0] if len(segments) > 1 else None
    if not is_terms and folder not in FOLDER_KIND:
        errs.append(f"{rel}: a page lives in one of {', '.join(sorted(FOLDER_KIND))}/")
    if folder == "guides" and len(segments) < 3:
        errs.append(f"{rel}: a guide lives in `guides/<group>/`")

    # front matter
    errs.extend(f"{rel}: unknown front-matter key `{k}`" for k in meta if k not in KEYS)
    # `terms.md` is a reference list, not a card: the contract asks it for a title and a kind only.
    required = ("title", "kind") if is_terms else REQUIRED
    errs.extend(f"{rel}: front matter needs `{k}`" for k in required if k not in meta)
    title, kind, summary = meta.get("title"), meta.get("kind"), meta.get("summary")
    if "title" in meta and (not isinstance(title, str) or not title.strip()):
        errs.append(f"{rel}: `title` is a non-empty string")
    if "kind" in meta and kind not in KINDS:
        errs.append(f"{rel}: `kind` is one of {', '.join(sorted(KINDS))}, not `{kind}`")
    elif folder in FOLDER_KIND and kind != FOLDER_KIND[folder]:
        errs.append(f"{rel}: a page in `{folder}/` is `kind: {FOLDER_KIND[folder]}`, not `{kind}`")
    if kind == "job" and meta.get("icon") not in ICONS:
        errs.append(f"{rel}: a job page needs `icon` = {' | '.join(sorted(ICONS))}")
    elif kind != "job" and "icon" in meta:
        errs.append(f"{rel}: `icon` is for job pages only")
    if kind == "job" and meta.get("group") not in GROUPS:
        errs.append(f"{rel}: a job page needs `group` = {' | '.join(GROUPS)}")
    elif kind != "job" and "group" in meta:
        errs.append(f"{rel}: `group` is for job pages only")
    if "for" in meta:
        audience = meta["for"]
        if not isinstance(audience, list) or not audience:
            errs.append(f"{rel}: `for` is a list, e.g. `[developer]`")
        else:
            errs.extend(
                f"{rel}: `for` holds only {', '.join(sorted(AUDIENCES))}, not `{a}`"
                for a in audience
                if a not in AUDIENCES
            )
    if "summary" in meta:
        if not isinstance(summary, str) or not summary.strip():
            errs.append(f"{rel}: `summary` is a non-empty string")
        elif len(summary) > SUMMARY_MAX:
            errs.append(f"{rel}: `summary` is {len(summary)} characters; at most {SUMMARY_MAX}")
    if "routes" in meta:
        if not isinstance(meta["routes"], list):
            errs.append(f"{rel}: `routes` is a list")
        else:
            errs.extend(
                f"{rel}: `{r}` is not an app route key (a route with a parameter is its kind only)"
                for r in meta["routes"]
                if not route_ok(r)
            )
    if "sources" in meta:
        if not isinstance(meta["sources"], list) or not all(isinstance(s, str) for s in meta["sources"]):
            errs.append(f"{rel}: `sources` is a list of repository paths")
        elif repo_root is not None:
            errs.extend(f"{rel}: source `{s}` does not exist" for s in meta["sources"] if not (repo_root / s).exists())
    if "mode" in meta and meta["mode"] not in MODES:
        errs.append(f"{rel}: `mode` is one of {', '.join(sorted(MODES))}, not `{meta['mode']}`")
    if "minutes" in meta and (
        not isinstance(meta["minutes"], int) or isinstance(meta["minutes"], bool) or meta["minutes"] < 1
    ):
        errs.append(f"{rel}: `minutes` is a whole number of minutes")
    if "generated" in meta:
        if not isinstance(meta["generated"], bool):
            errs.append(f"{rel}: `generated` is `true` or `false`")
        elif kind != "reference" or is_terms:
            errs.append(f"{rel}: `generated` is set only on generated reference pages")
    if folder == "reference" and meta.get("generated") is not True:
        errs.append(f"{rel}: `reference/` is generated; its pages carry `generated: true`")

    if is_terms:
        if title != "Terms" or kind != "reference":
            errs.append(f"{rel}: terms.md has `title: Terms` and `kind: reference`")
        for n, text in enumerate(page.body.split("\n"), start=page.line):
            if text.strip() and not re.match(r"^- \*\*(.+?)\*\*:\s*\S", text):
                at(n, "terms.md holds only `- **word**: one-sentence definition.` lines")
        return errs

    # body text: headings, raw HTML, inline directives, links
    for n, text in _prose_lines(page.body, page.line):
        if _HTML.search(text):
            at(n, f"raw HTML `{_HTML.search(text).group(0)}` is not allowed")  # type: ignore[union-attr]
        for m in _INLINE.finditer(text):
            name, value = m.group(1), m.group(2)
            if name not in INLINES:
                at(n, f"unknown inline `:{name}[…]`")
            elif name == "term" and value.strip().lower() not in words:
                at(n, f"`:term[{value}]` is in neither terms.md nor the loop glossary")
        for m in _LINK.finditer(text):
            target = m.group(2)
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if target.startswith("app:"):
                if not route_ok(target[len("app:") :]):
                    at(n, f"`{target}` names no app route key")
            elif target.split("#", 1)[0] not in docs.pages:
                at(n, f"link `{target}` names no page")

    # blocks
    tree = parse_blocks(page.body, page.line)
    ledes = 0
    seen_h2 = False
    for node, parent in _walk(tree):
        n = node.get("line", page.line)
        kind_ = node["type"]
        if node.get("problem"):
            at(n, node["problem"])
        if kind_ == "error":
            at(n, node["message"])
        elif kind_ == "heading":
            if node["level"] == 1:
                at(n, "never write `#`: the page title comes from front matter")
            elif node["level"] > 3:
                at(n, "headings are `##` and `###`")
            elif node["level"] == 2 and parent is None:
                seen_h2 = True
        elif kind_ == "container":
            if parent is not None:
                at(n, f"`:::{node['name']}` sits inside `:::{parent}`; containers do not nest")
            for problem in _check_container(node):
                if isinstance(problem, tuple):
                    at(*problem)
                else:
                    at(n, problem)
            if node["name"] == "lede":
                ledes += 1
                if ledes > 1:
                    at(n, "at most one `:::lede`")
                if seen_h2:
                    at(n, "`:::lede` comes before the first `##`")
        elif kind_ == "leaf":
            if parent == "lede":
                at(n, f"`::{node['name']}` cannot sit inside `:::lede`")
            errs.extend(f"{rel}:{n}: {m}" for m in _check_leaf(docs, node, route_ok))
    return errs


def _unknown(attrs: dict[str, Any], allowed: Iterable[str], block: str) -> list[str]:
    allowed = set(allowed)
    return [f"`{block}` has no attribute `{k}`" for k in attrs if k not in allowed]


def _check_container(node: dict[str, Any]) -> list[str | tuple[int, str]]:
    """What is wrong with one container; a `(line, message)` pair names a line inside it."""
    name, attrs = node["name"], node["attrs"]
    out: list[str | tuple[int, str]] = []
    if name in ("lede", "steps", "compare"):
        out += _unknown(attrs, (), f":::{name}")
    if name == "steps":
        if not node["items"]:
            out.append("`:::steps` holds a list of steps")
        for item in node["items"]:
            if "error" in item:
                out.append((item["line"], item["error"]))
            elif item["who"] not in STEP_WHO:
                out.append((item["line"], f"step badge `[{item['who']}]` is one of you, fleet, nobody"))
            elif not item["title"]:
                out.append((item["line"], "a step starts with `**Title.**`"))
    elif name == "callout":
        out += _unknown(attrs, ("kind", "figure"), ":::callout")
        if attrs.get("kind") not in CALLOUT_KINDS:
            out.append("`:::callout` needs `kind` = why | tip | careful")
        if "figure" in attrs and (attrs["figure"] is True or not str(attrs["figure"]).strip()):
            out.append("`figure` is short text")
    elif name == "mode":
        flags = [k for k in attrs if k in ("programs", "areas")]
        out += _unknown(attrs, ("programs", "areas"), ":::mode")
        if len(flags) != 1 or any(attrs[f] is not True for f in flags):
            out.append("`:::mode` takes exactly one of `programs`, `areas`")
    elif name == "ideas":
        out += _unknown(attrs, (), ":::ideas")
        items = [t for t in node["body"].split("\n") if t.strip()]
        if not 2 <= len(items) <= 4 or not all(_IDEA.match(t) for t in items):
            out.append("`:::ideas` holds 2 to 4 list items, each `- **Name.** text`")
    elif name == "compare":
        rows = [t for t in node["body"].split("\n") if t.strip()]
        if not rows or not all(t.strip().startswith("|") for t in rows):
            out.append("`:::compare` holds a markdown table and nothing else")
        elif len(rows[0].strip().strip("|").split("|")) < 2:
            out.append("`:::compare` needs at least one option column after the first")
    return out


def _check_leaf(docs: Docs, node: dict[str, Any], route_ok: Any) -> list[str]:
    name, attrs, label = node["name"], node["attrs"], node.get("label")
    out: list[str] = []
    if label is not None and name != "action":
        out.append(f"`::{name}` takes no `[label]`")
    if name == "diagram":
        out += _unknown(attrs, ("name", "slice"), "::diagram")
        if attrs.get("name") not in DIAGRAMS:
            out.append(f"`::diagram` needs `name` = {' | '.join(sorted(DIAGRAMS))}")
        elif attrs["name"] == "three-questions":
            if not isinstance(attrs.get("slice"), str) or not _LIVE_SHAPE["slice"].fullmatch(attrs["slice"]):
                out.append('`::diagram{name="three-questions"}` needs `slice="SL-…"`')
        elif "slice" in attrs:
            out.append("`slice` is for `three-questions` only")
    elif name == "live":
        out += _unknown(attrs, (*LIVE_KINDS, "title", "quote"), "::live")
        # THE EXAMPLE IS WRITTEN DOWN TOO. A page shows an item from Fleet's own planning; a
        # reader's repository usually does not hold it, so the block carries what that item says
        # (`title`, and `quote` when it has one) and the card falls back to it, marked as Fleet's
        # example, rather than telling the reader something is missing.
        if not isinstance(attrs.get("title"), str) or not attrs["title"].strip():
            out.append('`::live` needs `title="…"`: what the example says when this repository does not hold it')
        if "quote" in attrs and (not isinstance(attrs["quote"], str) or not attrs["quote"].strip()):
            out.append("`quote` is the example's own words")
        given = [k for k in LIVE_KINDS if k in attrs]
        if len(given) != 1:
            out.append("`::live` takes exactly one of slice, area, prd, program")
        elif not isinstance(attrs[given[0]], str) or not _LIVE_SHAPE[given[0]].fullmatch(attrs[given[0]]):
            out.append(f"`::live` `{given[0]}=` value `{attrs[given[0]]}` is not the right shape")
    elif name == "screen":
        out += _unknown(attrs, ("route", "focus", "pins"), "::screen")
        route = attrs.get("route")
        if route not in SCREENS:
            out.append(f"`::screen` route `{route}` is not one of {', '.join(SCREENS)}")
        else:
            pins = [p.strip() for p in str(attrs.get("pins", "")).split(",") if p.strip()] if "pins" in attrs else []
            anchors = SCREENS[route][1]
            out += [f"`{route}` has no anchor `{p}` (it has {', '.join(anchors)})" for p in pins if p not in anchors]
            if len(node["legend"]) != len(pins):
                out.append(
                    f"`::screen` has {len(pins)} pin(s) and {len(node['legend'])} legend item(s); one each, same order"
                )
        if "focus" in attrs and attrs["focus"] is True:
            out.append("`focus` names an item id")
    elif name == "action":
        out += _unknown(attrs, ("route",), "::action")
        if not label or not label.strip():
            out.append("`::action` needs a `[Label]`")
        if not route_ok(attrs.get("route")):
            out.append(f"`::action` route `{attrs.get('route')}` is not an app route key")
    elif name in ("cards", "path", "pages"):
        out += _unknown(attrs, ("links",), f"::{name}")
        links = (
            [x.strip() for x in str(attrs.get("links", "")).split(",") if x.strip()]
            if isinstance(attrs.get("links"), str)
            else []
        )
        if not links:
            out.append(f"`::{name}` needs `links`")
        out += [f"`::{name}` links to `{x}`, which is no page" for x in links if x not in docs.pages]
    elif name == "command":
        out += _unknown(attrs, ("name",), "::command")
        cmd = attrs.get("name")
        if not isinstance(cmd, str) or not _COMMAND_NAME.fullmatch(cmd) or not _command_exists(cmd):
            out.append(f"`::command` names no command `{cmd}` in the command tree")
    elif name == "embed":
        out += _unknown(attrs, ("name",), "::embed")
        if attrs.get("name") not in EMBEDS:
            out.append(f"`::embed` needs `name` = {' | '.join(sorted(EMBEDS))}")
    elif name == "figure":
        out += _unknown(attrs, ("name", "alt"), "::figure")
        if attrs.get("name") not in FIGURES:
            out.append(f"`::figure` `{attrs.get('name')}` is not registered in templates/docs-figures.js")
        if not isinstance(attrs.get("alt"), str) or not attrs["alt"].strip():
            out.append("`::figure` needs `alt`")
    return out


# ── the agent rendering ─────────────────────────────────────────────────────

_CALLOUT_WORD: Final = {"why": "Why", "tip": "Tip", "careful": "Careful"}


#: A command written with its namespace (`/<ns>:slice:create`, as a command's own purpose may type
#: it). The namespace is matched by shape, never named: an agent reads a command by its bare id.
_NAMESPACED_COMMAND: Final = re.compile(r"(?<![\w./-])/[a-z][a-z0-9-]*:(?=[a-z])")


def bare_commands(text: str) -> str:
    """`text` with every `/<namespace>:` before a command id dropped: `/x:prd:verify` reads `prd:verify`."""
    return _NAMESPACED_COMMAND.sub("", text)


def contents(docs: Docs) -> list[dict[str, Any]]:
    """Every page an agent may read, once, in `Docs.reading_order` — each card with the job it
    belongs to (`job`, `jobTitle`; empty for a page no job owns, such as a reference page). The
    list `list_docs`, `/llms.txt` and the `index.md` written beside the disk copy are drawn from."""
    owner = docs.owner()
    out = []
    for page_id in docs.reading_order():
        card = _card(docs.pages[page_id])
        job = owner.get(page_id, "")
        card["job"] = job
        card["jobTitle"] = str(docs.pages[job].meta.get("title", job)) if job in docs.pages else ""
        out.append(card)
    return out


class StaticResolver:
    """`Resolver` for a reading with no repository behind it: the copy `fleet commands sync` writes.

    Nothing is live (a `::live` card names its example and says it is Fleet's own), the mode is
    unknown (every tab is read as a condition), a term is `terms.md`'s, an app page is its hash
    route in the Fleet app, and a command is the shipped tree's.
    """

    def __init__(self, docs: Docs) -> None:
        self._docs = docs
        self._terms = terms_of(docs)

    def live(self, kind: str, id: str) -> dict[str, Any] | None:  # noqa: A002, ARG002
        return None

    def term(self, word: str) -> str | None:
        return self._terms.get(word.strip().lower())

    def page(self, id: str) -> tuple[str, str] | None:  # noqa: A002
        found = self._docs.pages.get(id)
        return None if found is None else (str(found.meta.get("title", id)), str(found.meta.get("summary", "")))

    def url(self, route: str) -> str:
        return f"#{route}"

    def mode(self) -> str:
        return "any"

    def command(self, name: str) -> tuple[str, str] | None:
        purpose = command_purpose(name)
        return None if purpose is None else (name, purpose)


def render_files(docs: Docs) -> dict[str, str]:
    """`{relative path: text}`: every page in `contents` rendered for an agent with `StaticResolver`
    (`<id>.md`), `terms.md`, and an `index.md` listing them in reading order under their jobs.

    What `fleet commands sync` writes to `.fleet/docs/`: the agent reading, never the source, so a
    session reads the same text `read_doc` answers — minus the live facts a committed file cannot
    hold — and no directive, front matter or source path of Fleet's own reaches the checkout.
    """
    resolver = StaticResolver(docs)
    cards = contents(docs)
    out = {f"{c['id']}.md": render_agent(docs.pages[c["id"]], resolver) for c in cards}
    if TERMS_ID in docs.pages:
        out[f"{TERMS_ID}.md"] = render_agent(docs.pages[TERMS_ID], resolver)
    lines = [f"# {docs.index_meta.get('title') or 'Fleet docs'}", ""]
    if docs.index_meta.get("summary"):
        lines += [str(docs.index_meta["summary"]), ""]
    lines.append(
        "Fleet's own docs, one file per page, in reading order under the job each belongs to. Live facts "
        "(this repository's slices, areas and PRDs) are filled in only by the `read_doc` tool."
    )
    heading = None
    for c in cards:
        group = c["jobTitle"] or "Reference"
        if group != heading:
            heading = group
            lines += ["", f"## {group}", ""]
        lines.append(f"- [{c['title']}]({c['id']}.md)" + (f": {c['summary']}" if c["summary"] else ""))
    if TERMS_ID in docs.pages:
        lines += ["", "## Terms", "", f"- [Terms]({TERMS_ID}.md): the planning words the pages mark as terms"]
    out["index.md"] = "\n".join(lines) + "\n"
    return out


#: A planning id as a page writes one: one of the product's own id kinds (`idkinds.prefixes`:
#: `SL-250`, `REQ-004`, `PG-01`), or a PRD number (`PRD 0502`). Any other capitals-dash-number —
#: `UTF-8`, `SHA-256`, `ISO-8601`, `RFC-9110` — is not an id and is left as written.
def _example_id() -> re.Pattern[str]:
    kinds = "|".join(sorted(idkinds.prefixes(), key=len, reverse=True))
    return re.compile(
        rf"\b({kinds})-(\d+)\b"  # SL-138
        rf"|\b({kinds})(\d+)(-[A-Z]\d*)\b"  # SL138-C1: a criterion of that id, written dash-less
        rf"|\b(PRDs?) (\d{{3,5}})\b"  # PRD 0502
    )


_EXAMPLE_ID: Final = _example_id()

#: A URL is left exactly as written, ids and all: rewriting one would break the address.
_URL: Final = re.compile(r"[a-z][a-z0-9+.-]*://[^\s)>\]`\"']+")

#: The letter each made-up id is written in, by the order its real id first appears on the page:
#: the first slice the page names reads `SL-XXX`, a second one `SL-YYY`. Not `N`, which is how a
#: page writes an id's SHAPE (`SL-NNN`): an example has to read as an example, not as the format.
_EXAMPLE_DIGITS: Final = "XYZWVUTSRQPMK"

#: A leaf whose attributes the resolver reads: kept as written, so a repository that does hold the
#: id still gets its live card (`_neutral_live` neutralises it when nobody does).
_RESOLVED_LEAF: Final = re.compile(r"^\s*::(?:live|diagram)\b")

#: The home project's tool and subsystem names the customer-render scanner refuses
#: (`commandtree/internal_denylist.txt`, the one list). A page may name one where it states a real
#: default (`reference/fleet-toml`); the web keeps it, and the agent reading says whose it is.
_INTERNAL_DENYLIST: Final = _COMMANDS_ROOT.parent / "internal_denylist.txt"
_HOME_TOKEN_READS: Final = "Fleet's own value (set your own)"


def _home_tokens() -> re.Pattern[str] | None:
    if not _INTERNAL_DENYLIST.is_file():
        return None
    words = sorted(
        (
            w.strip()
            for w in _INTERNAL_DENYLIST.read_text(encoding="utf-8").splitlines()
            if w.strip() and not w.lstrip().startswith("#")
        ),
        key=len,
        reverse=True,
    )
    if not words:
        return None
    alt = "|".join(re.escape(w) for w in words)
    # The quotes a default's value is written in go too: what replaces it is a statement, not a value.
    return re.compile(rf"([\"']?)(?<![\w.-])(?:{alt})(?![\w-])\1", re.IGNORECASE)


_HOME_TOKEN: Final = _home_tokens()


class _Examples:
    """Fleet's own planning ids, as the agent reading names them: made up, stable, and plainly not
    the reader's. The web docs keep their real examples; an agent — on a customer's box above all —
    would take `SL-250` for an id in its own repository, look it up, and find nothing or the wrong
    thing. So every id of the product's own kinds a page writes is rewritten into a placeholder of
    the same length (`SL-250` → `SL-XXX`, `PG-01` → `PG-XX`, `PRD 0502` → `PRD XXXX`): the same id
    always reads the same on one page, a second id of the same kind reads differently (`SL-YYY`),
    and a placeholder carries no digit, so no reader can mistake it for a real id. A URL is left
    alone, and a home tool name a real default carries reads `Fleet's own value (set your own)`, unquoted.
    """

    def __init__(self) -> None:
        self._seen: dict[str, dict[str, str]] = {}

    def _one(self, prefix: str, number: str, sep: str) -> str:
        kind = self._seen.setdefault(prefix, {})
        if number not in kind:
            kind[number] = _EXAMPLE_DIGITS[min(len(kind), len(_EXAMPLE_DIGITS) - 1)] * len(number)
        return f"{prefix}{sep}{kind[number]}"

    def sub(self, text: str) -> str:
        """`text` with every id made up and every home tool name said as Fleet's own — outside URLs."""
        out, at = [], 0
        for url in _URL.finditer(text):
            out += [self._plain(text[at : url.start()]), url.group(0)]
            at = url.end()
        out.append(self._plain(text[at:]))
        return "".join(out)

    def _plain(self, text: str) -> str:
        text = _EXAMPLE_ID.sub(self._match, text)
        return _HOME_TOKEN.sub(_HOME_TOKEN_READS, text) if _HOME_TOKEN is not None else text

    def _match(self, m: re.Match[str]) -> str:
        if m.group(1):
            return self._one(m.group(1), m.group(2), "-")
        if m.group(3):
            # The dash-less criterion form shares the id's placeholder: `SL138-C1` beside `SL-138`
            # reads `SLXXX-C1` beside `SL-XXX`.
            return self._one(m.group(3), m.group(4), "") + m.group(5)
        return self._one(m.group(6), m.group(7), " ")

    def body(self, text: str) -> str:
        """The page's own text with every id made up, except in a leaf the resolver reads."""
        return "\n".join(line if _RESOLVED_LEAF.match(line) else self.sub(line) for line in text.split("\n"))


def _neutral_live(tree: list[dict[str, Any]], resolver: Resolver, examples: _Examples) -> None:
    """A `::live` card, or a `three-questions` diagram's slice, that the resolver cannot answer is
    Fleet's own example: its id, title and quote are made up like the rest of the page's text. One
    the resolver answers is the reader's own, and stays exactly as its repository writes it."""
    for node, _parent in _walk(tree):
        if node.get("type") != "leaf":
            continue
        attrs = node.get("attrs") or {}
        if node.get("name") == "live":
            kind = next((k for k in LIVE_KINDS if k in attrs), "")
            if kind and resolver.live(kind, str(attrs.get(kind, ""))) is None:
                for key in (kind, "title", "quote"):
                    if isinstance(attrs.get(key), str):
                        attrs[key] = examples.sub(attrs[key])
        elif node.get("name") == "diagram" and attrs.get("name") == "three-questions":
            ref = str(attrs.get("slice", ""))
            if resolver.live("slice", ref) is None:
                attrs["slice"] = examples.sub(ref)


def render_agent(page: Page, resolver: Resolver) -> str:
    """The page as plain markdown, live blocks resolved now — the contract's last column. Fleet's own
    example ids are made up (`_Examples`); a live block the resolver answers keeps the reader's."""
    terms: list[str] = []
    examples = _Examples()
    tree = parse_blocks(examples.body(page.body), page.line)
    _neutral_live(tree, resolver, examples)
    out = [f"# {examples.sub(str(page.meta.get('title', page.id)))}"]
    lede = next((n for n in tree if n["type"] == "container" and n["name"] == "lede"), None)
    if lede is not None:
        out.append(_plain(lede["body"].strip(), terms))
    out.extend(part for node in tree if node is not lede and (part := _agent_node(node, resolver, terms)))
    text = "\n\n".join(out)
    defined = [(w, d) for w in terms if (d := resolver.term(w))]
    if defined:
        text += "\n\n---\n" + "\n".join(f"- **{w}**: {d}" for w, d in defined)
    return text + "\n"


def _agent_markdown(text: str, resolver: Resolver, terms: list[str]) -> str:
    text = _LINK.sub(
        lambda m: f"[{m.group(1)}]({resolver.url(m.group(2)[4:])})" if m.group(2).startswith("app:") else m.group(0),
        text,
    )
    return _plain(text, terms)


def _agent_nodes(nodes: list[dict[str, Any]], resolver: Resolver, terms: list[str]) -> str:
    return "\n\n".join(part for n in nodes if (part := _agent_node(n, resolver, terms)))


def _agent_node(node: dict[str, Any], resolver: Resolver, terms: list[str]) -> str:
    kind = node["type"]
    if kind == "markdown":
        return _agent_markdown(node["text"], resolver, terms)
    if kind == "heading":
        return "#" * int(node["level"]) + " " + _plain(str(node["text"]), terms)
    if kind == "modes":
        mode = resolver.mode()
        chosen = [m for m in node["items"] if m["attrs"].get(mode) is True]
        # A reader that cannot know the repository's mode (`StaticResolver`, the copy on disk) reads
        # every tab, each said as the condition it is rather than as a fact about this repository.
        lead = "This repository plans" if chosen else "If this repository plans"
        parts = []
        for m in chosen or node["items"]:
            which = next((k for k in ("programs", "areas") if m["attrs"].get(k) is True), mode)
            parts.append(f"({lead} by {which}.)\n" + _agent_nodes(m["children"], resolver, terms))
        return "\n\n".join(parts)
    if kind == "container":
        name = node["name"]
        if name == "steps":
            lines = []
            for j, item in enumerate((i for i in node["items"] if "error" not in i), start=1):
                body = _agent_nodes(item["children"], resolver, terms)
                body = "\n".join(("   " + ln) if ln.strip() else "" for ln in body.split("\n")).lstrip()
                lines.append(f"{j}. [{item['who']}] **{_plain(item['title'], terms)}** {body}".rstrip())
            return "\n".join(lines)
        if name == "callout":
            word = _CALLOUT_WORD.get(str(node["attrs"].get("kind")), "Note")
            figure = node["attrs"].get("figure")
            body = _agent_nodes(node["children"], resolver, terms)
            head = f"**{word}:** " + (f"{figure} " if isinstance(figure, str) and figure else "")
            return "\n".join("> " + line if line else ">" for line in (head + body).split("\n"))
        if name == "compare":
            return _plain(node["body"].strip(), terms)
        if name == "ideas":
            return _agent_markdown(node["body"].strip(), resolver, terms)
        if name == "lede":
            return _plain(node["body"].strip(), terms)
        return _agent_nodes(node["children"], resolver, terms)
    if kind == "leaf":
        return _agent_leaf(node, resolver, terms)
    return ""


def _field(live: dict[str, Any], *labels: str) -> str | None:
    for label, value in live.get("fields") or []:
        if str(label).lower() in labels:
            return str(value)
    return None


def _agent_leaf(node: dict[str, Any], resolver: Resolver, terms: list[str]) -> str:
    name, attrs = node["name"], node["attrs"]
    if name == "live":
        kind = next((k for k in LIVE_KINDS if k in attrs), "")
        ref = str(attrs.get(kind, ""))
        live = resolver.live(kind, ref)
        if live is None:
            lines = [f"An example from Fleet's own planning: **{attrs.get('title') or ref}** ({ref})"]
            if attrs.get("quote"):
                lines.append(str(attrs["quote"]))
            return "\n".join("> " + line for line in lines)
        lines = [f"**{live.get('title') or ref}** ({ref})"]
        if live.get("quote"):
            lines.append(str(live["quote"]))
        lines += [f"{label}: {value}" for label, value in live.get("fields") or []]
        if live.get("commit"):
            lines.append(f"Read from commit {live['commit']}.")
        return "\n".join("> " + line for line in lines)
    if name == "diagram":
        return _agent_diagram(attrs, resolver)
    if name == "embed":
        return _agent_embed(attrs)
    if name == "screen":
        route = str(attrs.get("route", ""))
        title = SCREENS.get(route, (route, ()))[0]
        legend = "\n".join(f"{j}. {_plain(t, terms)}" for j, t in enumerate(node["legend"], start=1))
        return f"On the {title} page ({resolver.url(route)}):" + (f"\n{legend}" if legend else "")
    if name == "action":
        return f"[{node.get('label') or 'Open'}]({resolver.url(str(attrs.get('route', '')))})"
    if name == "cards":
        links = [x.strip() for x in str(attrs.get("links", "")).split(",") if x.strip()]
        named = []
        for page_id in links:
            found = resolver.page(page_id)
            named.append(f"{found[0]} ({page_id})" if found else page_id)
        return "Next: " + " · ".join(named)
    if name in ("path", "pages"):
        links = [x.strip() for x in str(attrs.get("links", "")).split(",") if x.strip()]
        rows = []
        for j, page_id in enumerate(links, start=1):
            found = resolver.page(page_id)
            title, summary = found if found else (page_id, "")
            mark = f"{j}." if name == "path" else "-"
            rows.append(f"{mark} **{title}** ({page_id})" + (f": {summary}" if summary else ""))
        return "\n".join(rows)
    if name == "command":
        found = resolver.command(str(attrs.get("name", "")))
        cmd, purpose = found if found else (str(attrs.get("name", "")), "")
        return f"`{bare_commands(cmd)}`" + (f" — {bare_commands(purpose)}" if purpose else "")
    if name == "figure":
        return str(attrs.get("alt", ""))
    return ""


def _agent_embed(attrs: dict[str, Any]) -> str:
    """An embed as a plain table of the same facts. The live counts are the app's; an agent reads
    the order and who attends each step, which is what the counts hang on."""
    if attrs.get("name") == "work-line":
        bands = {key: f"{n} · {name}" for n, (key, name) in enumerate(WORK_LINE_BANDS, start=1)}
        rows = [
            f"| {bands[band]} | {step} | {WORK_LINE_ATTENDANCE[att]} | {cmds} |" for band, step, att, cmds in WORK_LINE
        ]
        return (
            "| Band | Step | Who has to be there | Run by |\n|---|---|---|---|\n"
            + "\n".join(rows)
            + "\n\nAlongside bands 3 and 4, `program:deliver` runs one Delivery Lead cycle: it releases"
            " what is ready into triage, detects stalls and asks you about everything blocking."
            " A change verify refutes goes back to the builder (`rework`) until every line of the"
            " verifier's ledger closes."
        )
    return ""


def _agent_diagram(attrs: dict[str, Any], resolver: Resolver) -> str:
    """A diagram as the table of the same facts. Only `three-questions` reads live knowledge."""
    name = attrs.get("name")
    if name == "three-questions":
        ref = str(attrs.get("slice", ""))
        live = resolver.live("slice", ref) or {}
        area = _field(live, "area", "feature area") or "—"
        prd = _field(live, "prd", "proven by") or "—"
        return (
            "| Question | Name | Finishes? | Here |\n|---|---|---|---|\n"
            f"| Where does it belong? | Feature | never | {area} |\n"
            f"| What will be true when we're done? | Slice | yes | {live.get('title') or ref} |\n"
            f"| What does one agent build? | PRD | yes | {prd} |"
        )
    if name == "work-line":
        return (
            "| Step | What it is | Who moves it |\n|---|---|---|\n"
            "| Idea | A wish, filed and shaped by questions | you |\n"
            "| Slice | One sentence that will be true when the work is done | you |\n"
            "| PRD | A piece one agent session can build, with checks it must pass | fleet |\n"
            "| Pull request | The built change, checked by a session that did not write it | fleet |\n"
            "| Merged | The slice reads complete once its sentence is shown to hold | nobody |"
        )
    if name == "knowledge-folder":
        return (
            "| In the knowledge folder | Holds |\n|---|---|\n"
            "| Features | The parts of the product a customer would name; they never finish |\n"
            "| Slices | Sentences that will be true when a piece of work is done |\n"
            "| PRDs | What one agent session builds, with its acceptance checks |\n"
            "| Requirements | Numbered commitments the product has made |"
        )
    if name == "knowledge-map":
        return (
            "| In the knowledge folder | Part | Holds |\n|---|---|---|\n"
            "| Planning: what is changing | Features | Parts of the product a customer names; never finish |\n"
            "| | Slices | One sentence each that will be true when a piece of work is done |\n"
            "| | PRDs | What one agent session builds, with the checks it must pass |\n"
            "| | Programs (optional) | A larger result several slices add up to |\n"
            "| The product: what is true | Capabilities and components | What someone can do; what is built |\n"
            "| | Journeys | How a person gets a whole job done |\n"
            "| Commitments: what must stay true | Promises | Numbered requirements, never deleted |\n"
            "| | Decisions | Why a choice was made, so it outlives the conversation |\n"
            "| About your repository | Slots | Your answers to the questions the commands ask |\n"
            "| | Records | Check results, audits and retros |\n"
            "| | Generated tables | Rendered from files, never edited by hand |"
        )
    if name == "fleet-map":
        return (
            "| Step | What happens | Who |\n|---|---|---|\n"
            "| File | You file an idea, a bug or a task, and answer Fleet's questions | you |\n"
            "| Build | A machine's session builds it and opens a pull request | fleet |\n"
            "| Verify | A fresh session that did not write it proves each claim, or sends it back | fleet |\n"
            "| Merge | The change merges; what it promised is checked from then on | nobody |\n\n"
            "Under all four: the knowledge base (what the product is and promised), machines and seats "
            "(where sessions run, and how many at once), and your own tools (MCP servers, secrets, API keys)."
        )
    return ""
