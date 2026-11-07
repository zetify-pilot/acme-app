"""Resolve every path a knowledge doc names.

A knowledge base is a graph held together by references: markdown links, backticked
code paths in prose, and `path:` provenance in frontmatter. A reference that no longer
resolves is a dead edge — the reader follows it and finds nothing, and no other check
sees it, because nothing else reads prose. This check walks every doc and resolves every
reference it can tell apart from ordinary text.

What it deliberately does NOT check is as load-bearing as what it does. A glob is a
pattern, not an assertion. A `**Files:**` entry declares a file the work will CREATE. A
PRD, a decision record or a requirement register names to-be-built code by design, so
those are scanned for their knowledge-internal links only. Each carve-out below is a
config key, so another project re-points them without forking the logic.

Stdlib only. Exit 1 on any violation.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from ._kit import Finding, KnowledgeBase, local_kb, option_list, option_tuple, rel_to

# --------------------------------------------------------------------------------------
# Defaults — the values this repository already had. Every one is a config key.
# --------------------------------------------------------------------------------------
DEFAULT_SCAN_SUFFIXES = (".md", ".yaml", ".yml")

MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
FENCED_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
LINE_SUFFIX_RE = re.compile(r"^(?P<path>.+?):(?P<line>\d+(?:-\d+)?)(?::\d+)?$")
# Matches file:FunctionName / file::FunctionName / file:Receiver.Method
# references used in spec docs to cite a specific symbol in a source file.
# Accepts both the single-colon (`file.go:Symbol`) and the GoDoc-style
# double-colon (`file.go::Symbol`) form, and allows one level of dotting in
# the symbol (`file.go:Receiver.Method`) so audit/bug prose can cite methods
# on a named receiver.
SYMBOL_SUFFIX_RE = re.compile(r"^(?P<path>.+\.(?:go|ts|tsx|py|md)(?:\.\w+)?)::?(?P<symbol>[A-Za-z_]\w*(?:\.\w+)?)$")

# Repo-rooted reference prefixes: a reference starting with one of these resolves from
# the repository root rather than from the doc's own directory.
DEFAULT_ROOT_HINTS = (
    "knowledge/",
    "frontend/",
    "internal/",
    "packages/",
    "api/",
    "db/",
    "contracts/",
    "proto/",
    "cmd/",
    "scripts/",
    "tests/",
    "migrations/",
    "logs/",
    ".claude/",
    ".opencode/",
    ".pre-commit-config.yaml",
    "Makefile",
    "README.md",
    "AGENTS.md",
)

# Not repository paths at all: URLs, anchors, and the product's own URL routes.
DEFAULT_IGNORE_PREFIXES = (
    "http://",
    "https://",
    "mailto:",
    "file://",
    "#",
    "/api/",
    "/dashboard",
    "/changes/",
    "/applications/",
    "/settings/",
    "/agents/",
    "/users",
    "/explore",
    "/tenants",
    "/integrations",
    "/health",
    "/audit-log",
    "/feature-flags",
    "/impersonation",
    "/api/admin/",
)

# Paths that exist only after a build/run, so a fresh checkout and CI never have them.
DEFAULT_IGNORE_PATH_PREFIXES = (
    "migrations/",
    "./migrations/",
    "../migrations/",
    "../website/",
    # Runtime output directory: gitignored, only exists locally after a benchmark run.
    "tests/benchmark/results/",
    # Gitignored runtime output (lint reports, gate logs, dev-service logs) — these
    # files only exist locally after a make/lint/test run, never in the tree.
    "logs/",
)

# Substrings anywhere in a reference that make it unverifiable. `node_modules/` is
# gitignored and absent from a clean checkout, so a doc citing a path under it (e.g. an
# audit finding about a vendored npm package) is not asserting a checked-in repo path.
DEFAULT_IGNORE_SUBSTRINGS = ("node_modules/",)

# Navigation indexes generated on demand and NOT committed (see .gitignore): a link to
# one is valid — it resolves the moment anyone renders it — but the file is absent from a
# fresh checkout and from CI. Matched on the RESOLVED path, not the basename, because
# knowledge/specs/architecture/roadmap.md is a different, hand-authored, committed file
# that must stay checked.
#: A fragment-backed register's committed shell: `<name>.md.tmpl` beside the gitignored
#: `<name>.md` it renders (`gen_knowledge_registers.py` / `gen_knowledge_fragments.py`). A link
#: to the rendered file resolves while it is absent, exactly as the files listed below do.
SHELL_SUFFIX = ".tmpl"

DEFAULT_GENERATED_ON_DEMAND = (
    "knowledge/roadmap.md",
    "knowledge/adr-index.md",
    # ENG-12971: the requirement-status ledger left version control on the same rule — a
    # derived file every register edit rewrote. `gen_requirement_status.py` renders it.
    "knowledge/requirement-status.md",
)

# Files that explicitly describe *planned* (not yet existing) code paths.
# These are roadmaps and forward-looking specs where inline-code path
# references intentionally name directories and files that will be created as
# part of the implementation they describe. Validating them against the current
# tree would produce only false positives.
DEFAULT_PLANNED_PATHS_FILES = (
    # roadmap.md, PRDs, and retros are NOT fully excluded — they are scanned
    # knowledge-only (see knowledge_only_file) so their links to other PRDs/specs
    # are validated while forward-looking code-path references are skipped.
    "verification-harness.md",
    # Architecture planning doc describing future implementation paths
    "70-mvp-deltas.md",
    # Pre-MVP gap analysis referencing historical paths deleted during cleanup
    "2026-05-08-pre-mvp.md",
    # Tracking spec with template placeholder paths like NNNN-<slug>
    "tracking-and-execution.md",
    # API quality audit workstream: references findings files created incrementally
    "api-quality-audit.md",
    # Decision Ledger foundation spec: prior-art appendices cite paths in the
    # *external* Emergence repo and describe to-be-created 0161–0170 tables/packages.
    "decision-ledger.md",
    # agentd demo runbook: its only knowledge/ path reference is to RUNNING.md,
    # a gitignored artifact demoseed writes at runtime (live token, "do not
    # commit") — absent from a clean checkout by construction. Same rationale
    # as verification-harness.md's gitignored runtime-output references.
    "AGENTD.md",
    # The workload-runtime TARGET architecture: its entire subject is the
    # shape we are building toward, so naming files that do not exist yet is
    # the document working as intended, not a broken link. Exactly the
    # category 70-mvp-deltas.md above is exempted for. (Its own header says
    # it describes "an architecture that is not built".)
    "workload-runtime-target-architecture.md",
)

# Top-level knowledge/ directories whose files are forward-looking brainstorms
# rather than validated knowledge. Ideas (knowledge/ideas/<topic>/) propose
# to-be-created structure and freely reference planned dirs and *sibling repos*
# (e.g. ../infra, knowledge/decisions/SOP-<slug>.md) by design, so validating
# their path references against the current tree yields only false positives.
# Same rationale as the planned-files list, applied at the directory level.
DEFAULT_PLANNED_PATHS_DIRS = (
    "ideas",
    # Drills: the README + _TEMPLATE describe the failover drill *record* — a filled,
    # dated artifact produced only when a real drill runs against a live cluster. The
    # docs name the exact record the harness will commit, which is absent from a clean
    # checkout by construction; committing a pre-filled record with no run behind it is
    # precisely the assertion the drill contract forbids.
    "drills",
)

# Subtrees whose references are validated only when they point *inside* the knowledge
# root — see `knowledge_only_file` for why each one is on the list.
DEFAULT_KNOWLEDGE_ONLY_DIRS = ("prds", "retros", "audits", "decisions", "slices", "requirements")
DEFAULT_KNOWLEDGE_ONLY_FILES = ("roadmap.md", "slices.md")
# Link TARGETS a knowledge-only doc never has to resolve: frozen historical provenance
# (ideas migrated to a tracker) that stays cited but is no longer maintained.
DEFAULT_KNOWLEDGE_ONLY_SKIP_TARGET_DIRS = ("ideas",)

# A plan file's `**Files:**` list declares files the plan will CREATE, each a
# forward-looking path commonly suffixed `(new)` — not a link that must already
# resolve. Validating those against the current tree produces false positives on
# exactly the correct work a plan does, and pressures authors to commit stub files just
# to satisfy a checker. Two signals identify a *declared* (not *linked*) path: it is
# immediately suffixed `(new)` / `*(new)*`, or it sits inside a `**Files:**` block.
# Everything else in the document — genuine links to specs, PRDs, and existing code — is
# still fully validated, so the checker stays blind only to declarations, never to
# broken references.
NEW_FILE_SUFFIX_RE = re.compile(r"^\s*\*?\(\s*new\b")
FILES_HEADING = "**Files:**"

# Matches a YAML `- path: <ref>` / `  path: <ref>` entry inside frontmatter.
# The PRD `source_ideas:` provenance field (and friends) record where a doc's
# idea came from as a `path:` — a schema'd reference that must resolve like any
# other link. The validator was historically blind to it, so a deleted knowledge
# doc referenced in frontmatter passed the commit.
FRONTMATTER_PATH_RE = re.compile(r"^\s*[-]?\s*path:\s*(.+?)\s*$")


@dataclass(frozen=True)
class Issue:
    file_path: Path
    line_number: int
    reference: str
    reason: str


# --------------------------------------------------------------------------------------
# Pure helpers
# --------------------------------------------------------------------------------------
def line_number_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def normalize_reference(raw: str) -> str:
    ref = raw.strip()
    if ref.startswith("<") and ref.endswith(">"):
        ref = ref[1:-1].strip()
    if ref.startswith("'") and ref.endswith("'"):
        ref = ref[1:-1].strip()
    if ref.startswith('"') and ref.endswith('"'):
        ref = ref[1:-1].strip()
    if "#" in ref and not ref.startswith("#"):
        ref = ref.split("#", 1)[0]
    line_match = LINE_SUFFIX_RE.match(ref)
    if line_match and "/" in line_match.group("path"):
        ref = line_match.group("path")
    # Strip file:SymbolName suffixes (e.g. tests/foo_test.go:TestFoo).
    symbol_match = SYMBOL_SUFFIX_RE.match(ref)
    if symbol_match and "/" in symbol_match.group("path"):
        ref = symbol_match.group("path")
    return ref.strip()


def strip_fenced_blocks(text: str) -> str:
    return FENCED_BLOCK_RE.sub(lambda match: "\n" * match.group(0).count("\n"), text)


def frontmatter_block(text: str) -> str:
    """Return the YAML frontmatter between the leading `---` fences, or ''."""
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return ""
    return parts[1]


def is_declared_new_file(searchable: str, match_start: int, match_end: int) -> bool:
    """Whether an inline-code / link reference is a *declaration* of a to-be-created
    file rather than a *reference* that must already resolve.

    A declared-new path is one that is explicitly suffixed `(new)` (optionally
    italicised as `*(new)*`, optionally with a parenthetical note like
    `(new — generated, committed)`), or that appears as a list item under a
    `**Files:**` heading. Both appear in plan/PRD/design `**Files:**` lists, where an
    entry names a file the work will create — validating it against the current tree
    is a false positive.
    """
    tail = searchable[match_end : match_end + 32]
    if NEW_FILE_SUFFIX_RE.search(tail):
        return True
    line_start = searchable.rfind("\n", 0, match_start) + 1
    line = searchable[line_start:match_end]
    if not line.lstrip().startswith("-"):
        # Inline `- **Files:** \`path\` (new); …` form puts the declaration on the
        # same line as the heading.
        return FILES_HEADING in line
    # Walk up contiguous `- ` list items to a `**Files:**` heading; the block ends at
    # the first blank or non-list line.
    prev_end = line_start - 1
    while prev_end >= 0:
        prev_start = searchable.rfind("\n", 0, prev_end - 1) + 1
        prev = searchable[prev_start:prev_end]
        stripped = prev.strip()
        if not stripped:
            return False
        if stripped == FILES_HEADING or FILES_HEADING in stripped:
            return True
        if not stripped.startswith("-"):
            return False
        prev_end = prev_start - 1
    return False


def dedupe_issues(issues: list[Issue]) -> list[Issue]:
    seen: set[tuple[str, int, str, str]] = set()
    deduped: list[Issue] = []
    for issue in issues:
        key = (str(issue.file_path), issue.line_number, issue.reference, issue.reason)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    return deduped


# --------------------------------------------------------------------------------------
# The validator
# --------------------------------------------------------------------------------------
class KnowledgePathsValidator:
    """The ported `validate_knowledge_paths` run, bound to one knowledge base."""

    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb
        # Resolved, because every reference is resolved before comparison: an
        # unresolved root (a symlinked temp dir, a relative cwd) makes the
        # "is this target inside the knowledge root" test silently false.
        self.repo_root: Path = kb.root.resolve()
        self.knowledge_root: Path = kb.knowledge.resolve()
        self.scan_suffixes = set(option_list(kb, "paths_scan_suffixes", DEFAULT_SCAN_SUFFIXES))
        self.root_hints = option_tuple(kb, "paths_root_hints", DEFAULT_ROOT_HINTS)
        self.ignore_prefixes = option_tuple(kb, "paths_ignore_prefixes", DEFAULT_IGNORE_PREFIXES)
        self.ignore_path_prefixes = option_tuple(kb, "paths_ignore_path_prefixes", DEFAULT_IGNORE_PATH_PREFIXES)
        self.ignore_substrings = option_tuple(kb, "paths_ignore_substrings", DEFAULT_IGNORE_SUBSTRINGS)
        self.planned_files = frozenset(option_list(kb, "paths_planned_files", DEFAULT_PLANNED_PATHS_FILES))
        self.planned_dirs = frozenset(option_list(kb, "paths_planned_dirs", DEFAULT_PLANNED_PATHS_DIRS))
        self.knowledge_only_dirs = frozenset(option_list(kb, "paths_knowledge_only_dirs", DEFAULT_KNOWLEDGE_ONLY_DIRS))
        self.knowledge_only_files = tuple(option_list(kb, "paths_knowledge_only_files", DEFAULT_KNOWLEDGE_ONLY_FILES))
        self.knowledge_only_skip_target_dirs = frozenset(
            option_list(kb, "paths_knowledge_only_skip_target_dirs", DEFAULT_KNOWLEDGE_ONLY_SKIP_TARGET_DIRS)
        )
        self.generated_on_demand = frozenset(
            (self.repo_root / rel).resolve()
            for rel in option_list(kb, "paths_generated_on_demand", DEFAULT_GENERATED_ON_DEMAND)
        )

    # -- file selection -----------------------------------------------------------
    def iter_knowledge_files(self) -> list[Path]:
        return sorted(
            path
            for path in self.knowledge_root.rglob("*")
            if path.is_file()
            and path.suffix in self.scan_suffixes
            and path.name not in self.planned_files
            and path.relative_to(self.knowledge_root).parts[0] not in self.planned_dirs
            and path.resolve() not in self.generated_on_demand
        )

    def knowledge_only_file(self, path: Path) -> bool:
        """Files whose references are validated only when they point *inside* the
        knowledge root.

        PRDs and the roadmap legitimately cite forward-looking code paths (to-be-created
        files), so we can't tell a broken code-path ref from a planned one — but their
        links to other PRDs / specs / journeys *are* resolvable, and those are the
        navigation edges that matter. So scan these files, but check only
        knowledge-internal links.

        Audit records are the same shape — they cite exact `file:line` findings that the
        fix work they spawn then deletes/moves, and the record itself is superseded by
        the *next* audit run rather than kept perpetually in sync with a moving tree.
        Decision records and slice docs are forward-looking by the same rationale: a
        decision explaining "we'll build a shared loader" and the slice prose tracking
        that work legitimately name to-be-created code paths. Requirement registers are
        forward-looking BY DEFINITION — a register's purpose is "one place that answers
        *what did we decide that is not built yet*", so a row naming a path that does not
        exist is the register doing its job.

        DEBT, and the better fix: a register row carries a disposition, so `adopted` +
        path-absent IS distinguishable from a broken ref — unlike a decision or a slice.
        Teaching the checker that distinction would let registers keep full path
        validation.
        """
        try:
            rel = path.relative_to(self.knowledge_root)
        except ValueError:
            return False  # outside the knowledge root (e.g. a temp file under test)
        return rel.parts[0] in self.knowledge_only_dirs or path.name in self.knowledge_only_files

    # -- reference classification -------------------------------------------------
    def should_check_reference(self, ref: str, is_link: bool = False) -> bool:
        """`is_link` = the ref came from markdown `[text](target)` syntax.

        A link ASSERTS a path; prose in backticks merely names one. So a bare sibling
        reference (`flow-retro.md`, no `./`) is checked when it is a link and ignored
        when it is inline code — otherwise every doc that mentions a filename in passing
        would have to prove it resolves from that doc's own directory.
        """
        if not ref:
            return False
        if any(ref.startswith(prefix) for prefix in self.ignore_path_prefixes):
            return False
        if any(ref.startswith(prefix) for prefix in self.ignore_prefixes):
            return False
        if any(token in ref for token in self.ignore_substrings):
            return False
        if ref.startswith("/"):
            return False
        # Brace-expansion globs (e.g. api/{,admin/}gen/file.go) are prose, not real paths.
        if "{" in ref or "}" in ref:
            return False
        # Log fragments contain whitespace (e.g. "scripts/lint-all.sh: … Killed") — not real paths.
        if any(c.isspace() for c in ref):
            return False
        if ref.startswith("<") and ref.endswith(">"):
            return False
        if "/" in ref:
            last_segment = ref.rsplit("/", 1)[-1]
            if "." in last_segment and not last_segment.startswith("."):
                suffix = Path(last_segment).suffix
                if not suffix:
                    return False
        if ref.startswith(("./", "../")) or ref.startswith(self.root_hints):
            return True
        # Bare sibling link, e.g. [x](flow-retro.md). 701 of these existed unchecked, of
        # which 5 were broken — a real hole, since this is the most natural way to link a
        # file next door.
        if is_link and "/" not in ref and ref.endswith(".md"):
            return True
        # Relative link with a directory segment, e.g. [x](architecture/foo.md) from
        # knowledge/specs/. Ordinary valid relative markdown — not a ROOT_HINT, not bare
        # sibling. The previous bare-sibling branch required "/" not in ref, so these
        # fell through unchecked and a rewrite left 11 dangling with exit 0.
        return bool(is_link and self._is_doc_relative_ref(ref))

    def _is_sibling_ref(self, ref: str) -> bool:
        """A bare filename with no separator, e.g. `permissions.md` — standard markdown
        for "the file next to me". Must resolve against the containing directory, not the
        repo root, or every such link reads as broken.

        Root-hint entries are excluded: `README.md`, `Makefile` and `AGENTS.md` are bare
        names that deliberately denote the repo-root file, so sibling resolution would
        break the very references the hint list exists to resolve."""
        return "/" not in ref and not ref.startswith(self.root_hints)

    def _is_doc_relative_ref(self, ref: str) -> bool:
        """A path with a directory segment that is not repo-rooted via a root hint.

        Markdown `[text](architecture/foo.md)` from knowledge/specs/ resolves next to the
        doc, not at the repo root. Root-hint paths (`internal/…`, `knowledge/…`, …) stay
        repo-absolute. Used for both "should we check this link" and "how do we resolve
        it".

        Requires a file-like last segment (has a suffix) so slash-command targets like
        `arch/reconcile` and bare directory names are not treated as path assertions.
        """
        if not ref or ref.startswith(("/", "./", "../")):
            return False
        if ref.startswith(self.root_hints):
            return False
        if "/" not in ref:
            return False
        last = ref.rsplit("/", 1)[-1]
        if not last or last.startswith(".") or "." not in last:
            return False
        return bool(Path(last).suffix)

    def resolve_reference(self, base_file: Path, ref: str) -> tuple[Path, bool]:
        # `.../` is a rewrite artifact (nested relative arithmetic), not a real path
        # prefix — still resolve relative to the doc so the dangling target is reported
        # rather than silently skipped.
        relative = ref.startswith(("./", "../", ".../")) or self._is_sibling_ref(ref) or self._is_doc_relative_ref(ref)
        target = (base_file.parent / ref).resolve() if relative else (self.repo_root / ref).resolve()
        return target, any(ch in ref for ch in "*?[")

    def _knowledge_only_checkable(self, target: Path, ref: str) -> bool:
        """Whether a reference from a PRD / roadmap is worth validating.

        PRD and roadmap prose is link-noisy: forward-looking code paths, `…`/`...`
        placeholders, line-range suffixes, and frozen historical idea provenance under
        `ideas/inbox/`. We validate only the *navigation backbone* — `.md` docs and
        PRD-folder links that resolve inside the knowledge root, excluding the volatile
        `ideas/` subtree."""
        ts = str(target)
        if not ts.startswith(str(self.knowledge_root)):
            return False  # code / external — may be forward-looking
        if any(tok in ref for tok in ("...", "…", ":", "<", "NNNN")):
            return False  # placeholder or line/col suffix, not a real link
        rel = target.relative_to(self.knowledge_root)
        if rel.parts and rel.parts[0] in self.knowledge_only_skip_target_dirs:
            return False  # frozen historical provenance (ideas migrated to a tracker)
        # a link AT a PRD folder (prds/NNNN-slug), not a code path that happens to sit under one
        is_prd_dir = len(rel.parts) == 2 and rel.parts[0] == "prds" and bool(re.match(r"\d{4}-", rel.parts[1]))
        return ref.rstrip("/").endswith(".md") or is_prd_dir

    def validate_reference(self, base_file: Path, ref: str, knowledge_only: bool = False) -> str | None:
        target, has_glob = self.resolve_reference(base_file, ref)
        if has_glob:
            return None  # a glob is a pattern, not an assertion that it resolves
        if target.resolve() in self.generated_on_demand:
            return None  # rendered by a script, never committed — see the constant
        if target.suffix == ".md" and target.with_name(target.name + SHELL_SUFFIX).is_file():
            return None  # a fragment-backed register: its committed shell renders it on demand
        if knowledge_only and not self._knowledge_only_checkable(target, ref):
            return None
        if target.exists():
            return None
        return "path does not exist"

    # -- collectors ---------------------------------------------------------------
    def collect_markdown_link_issues(self, file_path: Path, text: str) -> list[Issue]:
        issues: list[Issue] = []
        ko = self.knowledge_only_file(file_path)
        searchable = strip_fenced_blocks(text)
        for match in MARKDOWN_LINK_RE.finditer(searchable):
            ref = normalize_reference(match.group(1))
            if not self.should_check_reference(ref, is_link=True):
                continue
            if is_declared_new_file(searchable, match.start(), match.end()):
                continue  # a declared to-be-created file, not a link that must resolve
            reason = self.validate_reference(file_path, ref, ko)
            if reason is None:
                continue
            issues.append(
                Issue(
                    file_path=file_path,
                    line_number=line_number_for_offset(text, match.start(1)),
                    reference=ref,
                    reason=reason,
                )
            )
        return issues

    def collect_inline_code_issues(self, file_path: Path, text: str) -> list[Issue]:
        issues: list[Issue] = []
        ko = self.knowledge_only_file(file_path)
        searchable = strip_fenced_blocks(text)
        for match in INLINE_CODE_RE.finditer(searchable):
            ref = normalize_reference(match.group(1))
            if not self.should_check_reference(ref):
                continue
            if is_declared_new_file(searchable, match.start(), match.end()):
                continue  # a declared to-be-created file, not a link that must resolve
            reason = self.validate_reference(file_path, ref, ko)
            if reason is None:
                continue
            issues.append(
                Issue(
                    file_path=file_path,
                    line_number=line_number_for_offset(searchable, match.start(1)),
                    reference=ref,
                    reason=reason,
                )
            )
        return issues

    def collect_frontmatter_path_issues(self, file_path: Path, text: str) -> list[Issue]:
        """Validate `path:` values declared in a doc's YAML frontmatter.

        `source_ideas: - path: knowledge/strategy/foo.md` records provenance; a
        `path:` naming a file that no longer exists is a dangling reference the
        validator previously could not see. Resolve every frontmatter `path:` value
        like the other reference classes so a deleted knowledge doc fails the commit.
        """
        issues: list[Issue] = []
        fm = frontmatter_block(text)
        if not fm:
            return issues
        ko = self.knowledge_only_file(file_path)
        for line in fm.splitlines():
            m = FRONTMATTER_PATH_RE.match(line)
            if not m:
                continue
            ref = m.group(1).strip().strip("'\"")
            if not self.should_check_reference(ref):
                continue
            reason = self.validate_reference(file_path, ref, ko)
            if reason is None:
                continue
            issues.append(
                Issue(
                    file_path=file_path,
                    line_number=line_number_for_offset(text, text.find(ref)),
                    reference=ref,
                    reason=reason,
                )
            )
        return issues

    # -- the run ------------------------------------------------------------------
    def issues(self) -> list[Issue]:
        all_issues: list[Issue] = []
        for file_path in self.iter_knowledge_files():
            text = file_path.read_text(encoding="utf-8")
            all_issues.extend(self.collect_markdown_link_issues(file_path, text))
            all_issues.extend(self.collect_inline_code_issues(file_path, text))
            all_issues.extend(self.collect_frontmatter_path_issues(file_path, text))
        return dedupe_issues(all_issues)

    def findings(self) -> list[Finding]:
        return [
            Finding(
                level="error",
                message=f"{issue.reference} ({issue.reason})",
                path=issue.file_path,
                line=issue.line_number,
                hint=(
                    "Re-point the reference at the file's new home, delete it, or — if the path is "
                    "deliberately not built yet — declare it under a `**Files:**` heading."
                ),
            )
            for issue in self.issues()
        ]


# --------------------------------------------------------------------------------------
# Check
# --------------------------------------------------------------------------------------
class KnowledgePathsCheck:
    name = "knowledge-paths"
    title = "Link resolution"
    description = (
        "Every path a knowledge doc names — a markdown link, a backticked code path in prose, a "
        "`path:` in frontmatter — resolves in the tree. The corpus is a graph held together by these "
        "references and nothing else reads prose, so a dead edge is invisible until a reader follows "
        "it. Globs, `**Files:**` declarations of to-be-created files, and forward-looking subtrees "
        "(PRDs, decisions, requirement registers) are deliberately exempt: they name what does not "
        "exist yet by design."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        knowledge: Path = kb.knowledge
        return knowledge.is_dir()

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        return KnowledgePathsValidator(kb).findings()


CHECK = KnowledgePathsCheck()


# --------------------------------------------------------------------------------------
# Legacy entry point — byte-identical stdout and exit codes
# --------------------------------------------------------------------------------------
def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    repo = root if root is not None else Path.cwd()
    kb = local_kb(repo)
    if not kb.knowledge.exists():
        print("knowledge/ directory not found", file=sys.stderr)
        return 1

    issues = KnowledgePathsValidator(kb).issues()
    if not issues:
        print("knowledge path validation passed")
        return 0

    print("knowledge path validation failed:")
    for issue in issues:
        print(f"- {rel_to(repo, issue.file_path)}:{issue.line_number}: {issue.reference} ({issue.reason})")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
