"""Validate the architecture-doc freshness contract.

Architecture prose — "how subsystem X works" — is hand-written, has no codegen and
no natural update trigger, so it rots silently as the code it describes moves on.
This check makes that rot **mechanical and visible** rather than a matter of memory.

Two kinds of doc carry the contract, and they acquire it differently:

  1. **Opted-in specs** (`<knowledge>/specs/*.md`) — a doc opts in by declaring YAML
     frontmatter

       source_of_truth: [<repo-relative dirs/files/globs the doc describes>]

     and, optionally, `verified_at: planning` to mark a forward-looking doc whose
     paths may not exist yet (exempt from path/freshness/sync checks).

  2. **Component detail docs** (`<knowledge>/specs/architecture/components/<id>.md`)
     — these carry the contract **derived, never authored**: the doc's
     `source_of_truth` IS the `owns:` paths of row `<id>` in the component registry
     (`components.md`). A detail doc gains the contract simply by existing next to a
     registry row that owns code; it declares nothing, and declaring `source_of_truth:`
     in one is a blocking error. This is deliberate: `owns:` is already a path-ownership
     claim, and a second hand-authored copy of it would be a claim to keep in sync
     rather than a reader of the one that exists. Registry paths that do not exist yet
     are filtered out rather than failing — the registry is a TARGET architecture, so a
     row may legitimately own code nobody has written; such a row simply derives less
     (or, with no existing path at all, nothing, and its doc carries no contract).

Reachability is enforced alongside freshness (they are the same registry↔doc join):
every registry row whose `components/<id>.md` exists must **link** it, so the detail
docs are reachable from the structural map instead of only by guessing a filename
from an id; and a detail doc naming no registry row is an error, because nothing —
not this contract, not the architecture diagram — can ever resolve it.

There is no stored `verified_at` SHA. The point a doc was "last verified at" is
**derived from git** — it is the doc file's own last commit. Re-reading a doc and
committing it (even a one-line edit) IS the re-stamp; the commit history is the
record. This removes the single-line merge-conflict hotspot and the
orphaned-SHA-after-squash-merge failure class that an in-file SHA created, while
keeping the freshness signal intact.

The check enforces:

  Shape (BLOCKING)      — frontmatter present; `source_of_truth` is a non-empty
                          list; `verified_at`, if present, is the literal
                          `planning` (a stored SHA/date is rejected with a
                          migration hint). A derived doc is exempt from the
                          `source_of_truth` half and is instead forbidden from
                          authoring one.
  Registry join (BLOCK) — a registry row whose detail doc exists links it; a
                          detail doc resolves to a registry row.
  Path existence (BLOCK)— every `source_of_truth` path resolves in the tree
                          (skipped for `planning` docs, which may name to-be-built
                          paths).
  Freshness (ADVISORY)  — for a real (non-planning) doc, if any `source_of_truth`
                          path changed in git since the doc's own last commit,
                          emit a DRIFT warning naming the doc + drifted paths +
                          commit count. Advisory by default (exit 0 so stale docs
                          never block an unrelated commit); `--strict` promotes
                          drift to a failure for a CI lane that wants teeth.
  PR sync (ADVISORY)    — `--changed-since <base>`: if a change's diff touches a doc's
                          `source_of_truth` path but the doc itself was not edited,
                          emit a SYNC advisory naming the doc and the drifted paths.
                          Always advisory (exit 0); `--strict` does NOT promote sync
                          advisories to failures (only drift warnings are strict-gated).

Separately, any spec anywhere under the specs root that uses the `**Propagation.**`
structured field convention gets a REST-path cross-check:

  REST path (ADVISORY)  — every backtick-quoted `METHOD /path` reference inside a
                          `**Propagation.**` field block must resolve to a real
                          OpenAPI operation (path template + method). Path parameters
                          are matched positionally, not by name, so `{org}` lines up
                          with `{workspaceId}`. Always advisory (exit 0, never
                          `--strict`-gated) — a spec's Propagation field can lag the API
                          by design; the point is to surface the gap, not block on it.
                          Scoping is self-selecting: a doc opts in by adopting the
                          `**Propagation.**` heading, not by a separate frontmatter flag.

Stdlib only. Exit 1 on any blocking error (or any drift warning under `--strict`).
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from fleet_knowledge.config import git_context

from ._kit import Finding, KnowledgeBase, frontmatter, local_kb, option, option_list, rel_to

SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
PLANNING = "planning"
GLOB_CHARS = set("*?[")

# Defaults — the values this repository already had. Every one is a config key.
DEFAULT_SPECS_DIR = "specs"  # knowledge-relative; opt-in docs are its DIRECT children
DEFAULT_ARCH_DIR = "specs/architecture"  # knowledge-relative
# The component registry and its detail docs — the derived half of the contract.
# Both registry tables are read: a `## Proposed components` row owns code that
# exists in the tree by definition, so a detail doc next to one rots exactly the
# same way a registered component's does.
DEFAULT_REGISTRY_NAME = "components.md"
DEFAULT_DETAILS_DIRNAME = "components"
DEFAULT_COMPONENT_TABLES = ("## Components", "## Proposed components")
DEFAULT_OPENAPI_SPEC = "api/openapi.yaml"  # repo-relative
DEFAULT_PROPAGATION_HEADER = "**Propagation.**"

# No trailing `$`: unlike **Storage.**/**Propagation.** (header alone on its own
# line, followed by bullets), **Definition.**/**Non-expressivity.** carry prose
# right after the header on the same line — the header still needs to end the block.
BOLD_FIELD_HEADER_RE = re.compile(r"^\*\*[A-Za-z][\w /-]*\.\*\*")
REST_PATH_RE = re.compile(r"`(GET|POST|PUT|PATCH|DELETE)\s+([^`\s]+)`")
PATH_PARAM_RE = re.compile(r"\{[^}]+\}")
OPENAPI_PATH_RE = re.compile(r"^  (/\S+):\s*$")
OPENAPI_METHOD_RE = re.compile(r"^    (get|post|put|patch|delete):\s*$")


@dataclass
class Doc:
    path: Path
    verified_at: str | None = None
    source_of_truth: list[str] = field(default_factory=list)
    has_frontmatter: bool = False
    # Set for a component detail doc: the registry id its source_of_truth was
    # derived from. `authored_source_of_truth` records that the file ALSO declared
    # one of its own, which is the error the derived model exists to prevent.
    derived_from: str | None = None
    authored_source_of_truth: bool = False


@dataclass
class RegistryRow:
    line_no: int
    id: str
    owns: list[str]
    text: str


def _scalar(fm: str, name: str) -> str | None:
    m = re.search(rf"^{name}:\s*(.+)$", fm, re.M)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'") or None


def _list(fm: str, name: str) -> list[str]:
    """Parse a YAML list, inline (`name: [a, b]`) or block (`name:\\n  - a`)."""
    inline = re.search(rf"^{name}:\s*\[(.*?)\]", fm, re.M)
    if inline:
        return [x.strip().strip('"').strip("'") for x in inline.group(1).split(",") if x.strip()]
    block = re.search(rf"^{name}:\s*$(.*?)(?=^\S|\Z)", fm, re.M | re.S)
    if not block:
        return []
    out: list[str] = []
    for line in block.group(1).splitlines():
        m = re.match(r"\s*-\s*(.+)$", line)
        if m:
            out.append(m.group(1).strip().strip('"').strip("'"))
    return out


def parse_doc(path: Path) -> Doc:
    text = path.read_text(encoding="utf-8")
    fm = frontmatter(text)
    if fm is None:
        return Doc(path=path)
    return Doc(
        path=path,
        verified_at=_scalar(fm, "verified_at"),
        source_of_truth=_list(fm, "source_of_truth"),
        has_frontmatter=True,
    )


def is_planning(doc: Doc) -> bool:
    return doc.verified_at == PLANNING


def path_exists(repo: Path, ref: str) -> bool:
    if any(c in ref for c in GLOB_CHARS):
        return any(repo.glob(ref))
    return (repo / ref).exists()


def registry_rows(registry: Path, tables: Sequence[str] = DEFAULT_COMPONENT_TABLES) -> list[RegistryRow]:
    """Every component-shaped row of the registry -> (line, id, owns, raw line).

    Columns are `id | name | layer | owns | depends_on | description | detail`;
    only `id`, `owns` and the raw line (for the detail-link check) matter here.
    Shape/uniqueness/layer/cycle rules belong to the component-registry check, not
    this one — this is a READER of the registry, never a second claim on it.
    """
    if not registry.is_file():
        return []
    rows: list[RegistryRow] = []
    in_table = False
    for i, line in enumerate(registry.read_text(encoding="utf-8").splitlines(), start=1):
        if line.startswith("## "):
            in_table = line.strip() in tables
            continue
        stripped = line.strip()
        if not in_table or not stripped.startswith("|"):
            continue
        c = [x.strip() for x in stripped.strip("|").split("|")]
        if not c or not c[0] or c[0].lower() == "id":  # header
            continue
        if set("".join(c)) <= set("-: "):  # separator
            continue
        owns = [p.strip() for p in c[3].split(",") if p.strip()] if len(c) > 3 else []
        rows.append(RegistryRow(line_no=i, id=c[0], owns=owns, text=line))
    return rows


def detail_doc_path(details_dir: Path, cid: str) -> Path:
    return details_dir / f"{cid}.md"


def detail_docs(details_dir: Path) -> list[Path]:
    """Every component detail doc on disk (README.md is the directory's own guide)."""
    if not details_dir.is_dir():
        return []
    return sorted(p for p in details_dir.glob("*.md") if p.name != "README.md")


def derived_docs(rows: list[RegistryRow], details_dir: Path, repo: Path) -> list[Doc]:
    """Component detail docs, each carrying its registry row's `owns:` as source_of_truth.

    Paths that do not exist are filtered out rather than reported: the registry is a
    target architecture, so a row may own code nobody has written yet. A row that
    derives nothing (no `owns:`, or none of them on disk) yields no Doc — the doc is
    still perfectly valid prose, it just has no code to drift against.
    """
    out: list[Doc] = []
    for row in rows:
        path = detail_doc_path(details_dir, row.id)
        if not path.is_file():
            continue
        present = [p for p in row.owns if path_exists(repo, p)]
        if not present:
            continue
        doc = parse_doc(path)
        doc.authored_source_of_truth = bool(doc.source_of_truth)
        doc.source_of_truth = present
        doc.derived_from = row.id
        out.append(doc)
    return out


def check_registry_join(
    rows: list[RegistryRow],
    details_dir: Path,
    registry_rel: str,
    details_dirname: str = DEFAULT_DETAILS_DIRNAME,
) -> list[str]:
    """Blocking: the registry row <-> detail doc join is navigable in BOTH directions.

    Row -> doc, because the registry is the structural map every reader is pointed at,
    and a table keyed by id with no links leaves the long-form prose reachable only by
    guessing a filename. Doc -> row, because a detail doc naming no row is resolved by
    nothing — not this contract, not the architecture diagram's modal.
    """
    errs: list[str] = []
    known = set()
    for row in rows:
        known.add(row.id)
        path = detail_doc_path(details_dir, row.id)
        if path.is_file() and f"]({details_dirname}/{row.id}.md)" not in row.text:
            errs.append(
                f"{registry_rel}:{row.line_no}: `{row.id}` has a detail doc "
                f"(architecture/{details_dirname}/{row.id}.md) that the row does not link — put "
                f"`[detail]({details_dirname}/{row.id}.md)` in its `detail` column, or the doc is "
                "reachable only by guessing its filename from the id"
            )
    for path in detail_docs(details_dir):
        if path.stem not in known:
            errs.append(
                f"architecture/{details_dirname}/{path.name}: names no component registry row `{path.stem}` — "
                "a detail doc's filename IS the join key (see specs/architecture/components/README.md). "
                "Rename it to a registered id, or add the row to components.md."
            )
    return errs


def check_shape(doc: Doc) -> list[str]:
    errs: list[str] = []
    if doc.derived_from:
        # A derived doc declares nothing: its contract is its registry row's `owns:`.
        # Authoring a second copy here is the failure mode the derivation removes.
        if doc.authored_source_of_truth:
            errs.append(
                "declares its own `source_of_truth:` — a component detail doc's contract is DERIVED "
                f"from the `owns:` paths of registry row `{doc.derived_from}`. Remove the frontmatter "
                "key and edit components.md instead, so there is one path-ownership claim, not two."
            )
    elif not doc.has_frontmatter:
        errs.append(
            "missing YAML frontmatter — a doc opts into the freshness contract by declaring "
            "`source_of_truth:` (see specs/architecture/README.md)"
        )
        return errs
    # `verified_at` is no longer a stored SHA — freshness is derived from git.
    # The only value still accepted is the literal `planning` (forward-looking docs).
    if doc.verified_at and not is_planning(doc):
        if SHA_RE.match(doc.verified_at):
            errs.append(
                f"`verified_at: {doc.verified_at}` is a stored commit SHA — these are no longer "
                "used. Freshness is derived from the doc's own git history; remove the field "
                "(or set `verified_at: planning` for a forward-looking doc)."
            )
        else:
            errs.append(
                f"`verified_at: {doc.verified_at}` is not a recognized value — the only accepted "
                "value is the literal `planning`; otherwise omit `verified_at` entirely "
                "(freshness comes from git history)."
            )
    if not doc.derived_from and not doc.source_of_truth:
        errs.append("`source_of_truth:` must be a non-empty list of repo-relative paths")
    return errs


def check_paths(doc: Doc, repo: Path) -> list[str]:
    if is_planning(doc):  # planning docs may name to-be-created paths
        return []
    return [
        f"source_of_truth path does not exist: `{ref}`" for ref in doc.source_of_truth if not path_exists(repo, ref)
    ]


def propagation_docs(specs_dir: Path, header: str = DEFAULT_PROPAGATION_HEADER) -> list[Path]:
    """Specs anywhere under the specs root that use the **Propagation.** field
    convention — the self-selecting opt-in for the REST-path cross-check below."""
    if not specs_dir.is_dir():
        return []
    return sorted(p for p in specs_dir.rglob("*.md") if header in p.read_text(encoding="utf-8"))


def propagation_rest_paths(text: str, header: str = DEFAULT_PROPAGATION_HEADER) -> list[tuple[int, str, str]]:
    """(line_no, method, path) for every REST path cited inside a **Propagation.**
    field block — i.e. between that header and the next bold `**Field.**` header
    (or a `---` section divider). Scoping to the block (rather than the whole doc)
    is what keeps this from false-positiving on unrelated prose elsewhere in a spec
    (e.g. a "was X, now Y" migration note in a different section)."""
    out: list[tuple[int, str, str]] = []
    in_block = False
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped == header:
            in_block = True
            continue
        if in_block and (stripped == "---" or BOLD_FIELD_HEADER_RE.match(stripped)):
            in_block = False
        if in_block:
            out.extend((i, method, path) for method, path in REST_PATH_RE.findall(line))
    return out


def normalize_rest_path(path: str) -> str:
    """Collapse path parameters to a positional placeholder so `{org}` lines up
    with `{workspaceId}` — the cross-check is about path *shape*, not param names."""
    return PATH_PARAM_RE.sub("{}", path.rstrip("/"))


def openapi_operations(openapi_path: Path) -> dict[str, set[str]] | None:
    """Map normalized `path template` -> set of HTTP methods declared in the OpenAPI
    spec's `paths:` section. None if the file is unreadable (skip the cross-check
    gracefully rather than fail on a missing/moved spec file). Regex-parsed (stdlib
    only, no YAML dependency) — relies on the generator's stable 2-space path /
    4-space method indentation, bounded to the `paths:` block so a same-named key
    under `components:` can never be mistaken for an operation.
    """
    if not openapi_path.is_file():
        return None
    lines = openapi_path.read_text(encoding="utf-8").splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln == "paths:")
        end = next(i for i, ln in enumerate(lines) if i > start and ln == "components:")
    except StopIteration:
        return None
    ops: dict[str, set[str]] = {}
    current: str | None = None
    for line in lines[start:end]:
        m = OPENAPI_PATH_RE.match(line)
        if m:
            current = normalize_rest_path(m.group(1))
            continue
        m = OPENAPI_METHOD_RE.match(line)
        if m and current is not None:
            ops.setdefault(current, set()).add(m.group(1).upper())
    return ops


def check_rest_paths(
    text: str,
    openapi_ops: dict[str, set[str]] | None,
    header: str = DEFAULT_PROPAGATION_HEADER,
    spec_rel: str = DEFAULT_OPENAPI_SPEC,
) -> list[str]:
    """Advisory: a Propagation field cites a REST path/method with no matching
    OpenAPI operation. None openapi_ops (unreadable spec) → skip, not fail."""
    if openapi_ops is None:
        return []
    errs: list[str] = []
    for line_no, method, path in propagation_rest_paths(text, header):
        methods = openapi_ops.get(normalize_rest_path(path))
        if methods is None or method.upper() not in methods:
            errs.append(
                f"line {line_no}: Propagation field cites `{method} {path}`, which has no matching "
                f"operation in {spec_rel} — update the doc to match the real endpoint (or note "
                "that none exists)"
            )
    return errs


@cache
def _is_shallow(repo: Path) -> bool:
    # Cached: git_drift asks once per doc, and the subject set is dozens of docs.
    return (
        subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--is-shallow-repository"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        == "true"
    )


def doc_last_commit(path: Path, repo: Path) -> str | None:
    """The doc file's own last commit SHA — the point it was last verified at.
    None if the file has no commits yet (brand-new / uncommitted)."""
    try:
        rel = str(path.relative_to(repo))
    except ValueError:
        rel = str(path)
    res = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%H", "--", rel],
        capture_output=True,
        text=True,
    )
    return res.stdout.strip() or None


def git_drift(doc: Doc, repo: Path) -> dict[str, int] | None:
    """Commits touching each source_of_truth path since the doc's own last commit.
    None (skip advisory) if history is unavailable: a shallow clone (some CI) or a
    doc with no commits yet (brand-new / uncommitted, so there is no baseline)."""
    if _is_shallow(repo):  # shallow clones can't resolve history → skip
        return None
    since = doc_last_commit(doc.path, repo)
    if since is None:
        return None
    out: dict[str, int] = {}
    for ref in doc.source_of_truth:
        res = subprocess.run(
            ["git", "-C", str(repo), "log", "--oneline", f"{since}..HEAD", "--", ref],
            capture_output=True,
            text=True,
        )
        n = len([ln for ln in res.stdout.splitlines() if ln.strip()])
        if n:
            out[ref] = n
    return out


def drift_by_doc(docs: list[Doc], repo: Path) -> dict[Path, dict[str, int] | None]:
    """git_drift for every subject doc, resolved concurrently.

    Drift costs one `git log` per source_of_truth path, and deriving the contract took
    the subject set from a handful of docs to dozens — serially that is seconds on a hook
    that runs on every commit. The calls are independent and subprocess-bound, so a thread
    pool is the whole fix; the per-path counts are identical to the serial ones.
    """
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(zip([d.path for d in docs], pool.map(lambda d: git_drift(d, repo), docs), strict=True))


def check_freshness(doc: Doc, repo: Path, drift_fn: Callable[[Doc, Path], dict[str, int] | None]) -> list[str]:
    """Advisory drift warnings (returned as strings; never blocking on their own)."""
    if is_planning(doc):
        return []
    drift = drift_fn(doc, repo)
    if not drift:  # None (no baseline / shallow) or {} (no drift) → nothing to warn
        return []
    return [
        f"DRIFT: `{ref}` changed in {n} commit(s) since this doc's last edit — re-read and re-touch the doc"
        for ref, n in sorted(drift.items())
    ]


def git_changed_files(ref: str, repo: Path) -> set[str] | None:
    """Repo-relative paths changed in `ref...HEAD` (merge-base diff). None if git fails."""
    res = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-only", f"{ref}...HEAD"],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        return None
    return {ln.strip() for ln in res.stdout.splitlines() if ln.strip()}


def source_overlap(source_ref: str, changed: set[str]) -> list[str]:
    """Changed files matched by a source_of_truth ref (dir prefix / glob / exact file)."""
    hits: list[str] = []
    for f in changed:
        if any(c in source_ref for c in GLOB_CHARS):
            if fnmatch.fnmatch(f, source_ref):
                hits.append(f)
        elif source_ref.endswith("/"):
            if f.startswith(source_ref):
                hits.append(f)
        elif f == source_ref or f.startswith(source_ref + "/"):
            hits.append(f)
    return hits


def check_changed_since(doc: Doc, repo: Path, changed: set[str]) -> list[str]:
    """Advisory sync notice: if this change touches code the doc describes but the doc was not touched."""
    if is_planning(doc):
        return []
    if str(doc.path.relative_to(repo)) in changed:  # reconciled / re-touched here → satisfied
        return []
    overlapped = sorted({p for p in doc.source_of_truth if source_overlap(p, changed)})
    if not overlapped:
        return []
    return [
        "this change touches source it describes ("
        + ", ".join(f"`{p}`" for p in overlapped)
        + ") but the doc was not updated — reconcile it against the change and re-touch the doc "
        "(its commit becomes the new freshness baseline; a re-read + small edit suffices)"
    ]


def changed_since_ref(args: list[str]) -> str | None:
    for i, a in enumerate(args):
        if a == "--changed-since" and i + 1 < len(args):
            return args[i + 1]
        if a.startswith("--changed-since="):
            return a.split("=", 1)[1]
    return None


class ArchDocsValidator:
    """The ported `validate_arch_docs` run, bound to one knowledge base."""

    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb
        self.repo: Path = kb.root
        self.k: Path = kb.knowledge
        self.specs_dir: Path = self.k / str(option(kb, "arch_specs_dir", DEFAULT_SPECS_DIR))
        self.arch: Path = self.k / str(option(kb, "arch_dir", DEFAULT_ARCH_DIR))
        self.registry_name: str = option(kb, "arch_registry_name", DEFAULT_REGISTRY_NAME)
        self.details_dirname: str = option(kb, "arch_details_dirname", DEFAULT_DETAILS_DIRNAME)
        self.component_tables = tuple(option_list(kb, "arch_component_tables", DEFAULT_COMPONENT_TABLES))
        self.openapi_spec: str = option(kb, "arch_openapi_spec", DEFAULT_OPENAPI_SPEC)
        self.propagation_header: str = option(kb, "arch_propagation_header", DEFAULT_PROPAGATION_HEADER)

    @property
    def registry(self) -> Path:
        return self.arch / self.registry_name

    @property
    def details_dir(self) -> Path:
        return self.arch / self.details_dirname

    def registry_rows(self) -> list[RegistryRow]:
        return registry_rows(self.registry, self.component_tables)

    def subject_docs(self) -> list[Doc]:
        """Every doc the contract covers: opted-in root specs + derived component detail docs.

        Opt-in is deliberately NON-recursive over `specs/*.md` — a doc nested under
        `architecture/` gets the contract by being a component detail doc (derived), not by
        hand-declaring a second copy of a path claim the registry already makes.
        """
        opt_in = [doc for doc in map(parse_doc, sorted(self.specs_dir.glob("*.md"))) if doc.source_of_truth]
        derived = derived_docs(self.registry_rows(), self.details_dir, self.repo)
        return opt_in + derived


# --------------------------------------------------------------------------------------
# Check
# --------------------------------------------------------------------------------------
class ArchDocsCheck:
    name = "arch-docs"
    title = "Architecture-doc freshness"
    description = (
        "Architecture prose has no codegen and no natural update trigger, so it rots silently as the "
        "code it describes moves on. A doc opts into the contract by declaring `source_of_truth:` (a "
        "component detail doc DERIVES it from its registry row's `owns:` instead, so the path-ownership "
        "claim exists once). Shape, the registry↔doc join, and path existence are blocking; drift "
        "against git history is advisory, because a stale doc must never block an unrelated commit."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        validator = ArchDocsValidator(kb)
        return validator.specs_dir.is_dir() and bool(validator.subject_docs())

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        v = ArchDocsValidator(kb)
        findings: list[Finding] = []
        rows = v.registry_rows()
        try:
            registry_rel = str(v.registry.relative_to(v.repo))
        except ValueError:
            registry_rel = v.registry_name
        for e in check_registry_join(rows, v.details_dir, registry_rel, v.details_dirname):
            findings.append(
                Finding(
                    level="error",
                    message=e,
                    path=v.registry,
                    hint="Link the detail doc from its registry row, or give the doc a registered id.",
                )
            )
        subjects = v.subject_docs()
        drift = drift_by_doc(subjects, v.repo)
        # The PR sync leg, and only when a caller named the commit this change is measured
        # against — it asks "did THIS change touch code a doc describes", which has no answer
        # without a diff range. ADVISORY, permanently and on purpose: reconciliation is a
        # scheduled single-writer sweep, and gating feature PRs on a shared doc turned it into
        # a merge-conflict hotspot. `--strict` does not promote these either.
        since = git_context(kb).base
        changed = git_changed_files(since, v.repo) if since else None
        if since and changed is None:
            findings.append(
                Finding(
                    level="advisory",
                    message=f"could not resolve base `{since}` — PR sync advisory skipped",
                    hint="Fetch the base commit, or drop --base; the rest of the contract still ran.",
                )
            )
        for doc in subjects:
            if changed is not None:
                for a in check_changed_since(doc, v.repo, changed):
                    findings.append(
                        Finding(
                            level="advisory",
                            message=a,
                            path=doc.path,
                            hint="Reconcile the doc against this change and re-touch it.",
                        )
                    )
            for e in check_shape(doc) + check_paths(doc, v.repo):
                findings.append(
                    Finding(
                        level="error",
                        message=e,
                        path=doc.path,
                        hint="Fix the frontmatter, or re-point `source_of_truth:` at a path that exists.",
                    )
                )
            for w in check_freshness(doc, v.repo, lambda d, _r: drift[d.path]):
                findings.append(
                    Finding(
                        level="warning",
                        message=w,
                        path=doc.path,
                        hint="Re-read the doc against the change and re-touch it — its commit is the new baseline.",
                    )
                )
        openapi_ops = openapi_operations(v.repo / v.openapi_spec)
        for path in propagation_docs(v.specs_dir, v.propagation_header):
            text = path.read_text(encoding="utf-8")
            for e in check_rest_paths(text, openapi_ops, v.propagation_header, v.openapi_spec):
                findings.append(
                    Finding(
                        level="advisory",
                        message=e,
                        path=path,
                        hint="Update the Propagation field to the real endpoint, or note that none exists yet.",
                    )
                )
        return findings


CHECK = ArchDocsCheck()


# --------------------------------------------------------------------------------------
# Legacy entry point — byte-identical stdout and exit codes
# --------------------------------------------------------------------------------------
def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    repo = root if root is not None else Path.cwd()
    kb = local_kb(repo)
    v = ArchDocsValidator(kb)
    strict = "--strict" in args
    since = changed_since_ref(args)
    if "--list-subjects" in args:
        # The subject set, one repo-relative path per line — what a reconcile sweep
        # counts. A grep for `^source_of_truth:` cannot see the derived half.
        for doc in v.subject_docs():
            print(rel_to(v.repo, doc.path))
        return 0
    errors: list[str] = []
    warnings: list[str] = []
    # Sync advisories are always non-blocking — --strict does NOT promote them.
    sync_advisories: list[str] = []

    changed = git_changed_files(since, v.repo) if since else None
    if since and changed is None:
        sync_advisories.append(f"(global): could not resolve --changed-since `{since}` — PR sync advisory skipped")

    # Two sources, one contract:
    #   • opt-in  — a root spec that declares `source_of_truth:` itself
    #   • derived — a component detail doc, from its registry row's `owns:` paths
    rows = v.registry_rows()
    subjects = v.subject_docs()
    derived = [d for d in subjects if d.derived_from]
    opt_in = [d for d in subjects if d.derived_from is None]
    try:
        registry_rel = str(v.registry.relative_to(v.repo))
    except ValueError:
        registry_rel = v.registry_name
    errors.extend(check_registry_join(rows, v.details_dir, registry_rel, v.details_dirname))

    drift = drift_by_doc(subjects, v.repo)
    for doc in subjects:
        rel = rel_to(v.repo, doc.path)
        for e in check_shape(doc):
            errors.append(f"{rel}: {e}")
        for e in check_paths(doc, v.repo):
            errors.append(f"{rel}: {e}")
        if changed is not None:
            for a in check_changed_since(doc, v.repo, changed):
                sync_advisories.append(f"{rel}: {a}")
        for w in check_freshness(doc, v.repo, lambda d, _r: drift[d.path]):
            warnings.append(f"{rel}: {w}")

    # REST-path cross-check: independent of the source_of_truth contract above —
    # scoped to any spec using the **Propagation.** field convention, wherever it lives
    # under the specs root.
    restpath_advisories: list[str] = []
    openapi_ops = openapi_operations(v.repo / v.openapi_spec)
    for path in propagation_docs(v.specs_dir, v.propagation_header):
        rel = rel_to(v.repo, path)
        for e in check_rest_paths(path.read_text(encoding="utf-8"), openapi_ops, v.propagation_header, v.openapi_spec):
            restpath_advisories.append(f"{rel}: {e}")

    if sync_advisories:
        print("architecture-doc sync advisory (non-blocking — reconcile when convenient):")
        for a in sync_advisories:
            print(f"- {a}")
    if restpath_advisories:
        print("architecture-doc REST-path advisory (non-blocking — reconcile when convenient):")
        for a in restpath_advisories:
            print(f"- {a}")
    if warnings:
        label = "architecture-doc drift (advisory" + (", strict → failing)" if strict else ")")
        print(f"{label}:")
        for w in warnings:
            print(f"- {w}")
    if errors:
        print("architecture-doc validation failed:")
        for e in errors:
            print(f"- {e}")
    if errors or (strict and warnings):
        return 1
    print(
        f"architecture docs OK — {len(derived)} component detail docs (derived from the registry) "
        f"+ {len(opt_in)} opted-in specs carry a source_of_truth contract (freshness from git)"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
