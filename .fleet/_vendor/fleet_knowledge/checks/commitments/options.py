"""Every value the commitment checks used to hard-code, as a neutral default a project can set.

The four validators these checks were ported from named one repository throughout: a `v1`
release line, `knowledge/prds/`, `scripts/requirement_register.baseline`, a PRD lifecycle
spelled `stub -> shipped`, ten grandfathered ids from one afternoon. None of that is a
property of the *shape* — it is a property of the corpus that shape was first written for.

**Two layers, and the split is deliberate.**

  * The package's own `Config` (`fleet_knowledge.config`) already names the corpus: which
    registers exist, where the PRDs are, which id namespaces are reserved. Those are read
    STRAIGHT off it under their own names — `requirements_dir`, `prds_dir`, `todos_register`,
    `slices_register`, `components_registry`, `reserved_prefixes`, `baseline_dir` — so a
    project that configures the corpus once has configured it for these checks too. A second
    key meaning the same thing would be a second answer waiting to disagree.
  * What is left is specific to *commitments*: the release line, the PRD lifecycle bands,
    the coverage roots, the ratchets. Those live below with this repo's current value as the
    default, and a project sets any of them by name in its own table:

        [fleet.commitments]
        current_line = "r2"
        coverage_roots = ["contracts/"]

    `Config.commitments` carries that table and `from_config` reads it first, before the
    shared keys off `Config` itself — so a corpus whose commitments live somewhere its other
    checks do not can say so without moving anything else. A misspelled key is refused when
    the config file is read, against this dataclass's own field names.

**Defaults describe the shape, never one corpus's history.** A knowledge base with no
configuration gets the neutral shape: no ids grandfathered, and no prose file outside the
knowledge base. A project that adopted the append-at-end rule with rows already mid-file lists
its own ids, and a project whose prose lives in a root file (Fleet's `CLAUDE.md`, say) names it,
in its own `[fleet.commitments]` table.

What is NOT here: the register's grammar (id shape, Kind/Disposition/Cut vocabularies, the
table's required columns, the `superseded` payload form) and the todo row form. Those belong
to `fleet_knowledge.requirements` and `fleet_knowledge.todos`, which are the ONE reader of each —
a check that carried its own copy would be a second definition of what a row IS.

Stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

# ── the coverage carve-out, by document `type:` ──────────────────────────────
# Reviewed exclusions, each with a REQUIRED reason. Configurable so another corpus can name
# its own index-shaped types; that every entry carries a reason is not, because a silent
# allowance is exactly what the check exists to prevent.
DEFAULT_EXCLUDED_TYPES: dict[str, str] = {
    "readme": "an index — it routes a reader to documents and asserts nothing itself",
    "glossary": (
        "an index of TERMS — same reason as `readme`, in a folder the type system used to "
        "call a `spec`: it routes a reader to the document that defines each entity and "
        "asserts no shall/never of its own. It sat in UNCLAIMED.baseline until the type "
        "existed, and that entry's own `# ack:` named this as the correct burn-down"
    ),
    "template": "a scaffold for a document not yet written",
    "arch-example": (
        "a dated worked example (architecture/examples/**) — describes what a connector or "
        "platform does today, commits to nothing; lowest modal density in the corpus"
    ),
    "audit-checklist": (
        "an operating manual for a review pass — its shall/never sentences are restatements "
        "of commitments owned elsewhere, and each checklist names its own standards source "
        "of truth; it verifies commitments rather than making them"
    ),
}

# The ids already sitting mid-file the day a corpus adopted the append-at-end rule. THIS SET
# MAY ONLY SHRINK — adding to it grandfathers the exact collision the rule exists to prevent.
# EMPTY by default: an id that is not this corpus's history cannot be grandfathered by the
# package, and a project lists its own in `[fleet.commitments] append_order_baseline`.
DEFAULT_APPEND_ORDER_BASELINE: tuple[str, ...] = ()

# Keys read straight off `fleet_knowledge.config.Config` under their own names — the corpus
# shape, configured once for the whole package rather than again for these checks.
SHARED_KEYS = (
    "requirements_dir",
    "todos_register",
    "prds_dir",
    "slices_register",
    "components_registry",
    "decisions_dir",
    "reserved_prefixes",
    "baseline_dir",
)


@dataclass(frozen=True)
class CommitmentsConfig:
    """The corpus shape (mirrored from `Config`) plus the commitment-specific options."""

    # ── mirrored from `fleet_knowledge.config.Config`, same names, same defaults ──
    requirements_dir: str = "requirements"  # corpus-relative
    todos_register: str = "todos.md"  # corpus-relative
    prds_dir: str = "prds"  # corpus-relative
    slices_register: str = "slices.md"  # corpus-relative
    components_registry: str = "specs/architecture/components.md"  # corpus-relative
    # Namespaces a register may NOT claim. A tracker key (`ENG-4813`) is routinely written
    # `[ENG-4813]` inside an acceptance criterion — the exact citation form — so a register
    # with `prefix: ENG` would let an unrelated issue reference silently satisfy coverage.
    reserved_prefixes: tuple[str, ...] = ("ENG",)
    # Where ratchet baselines live, relative to the REPO root: a baseline is a property of
    # the checkout, not of the corpus.
    baseline_dir: str = "."

    # ── commitment-specific: the third orthogonal axis ────────────────────────
    # `Cut` names the release line a row LANDS IN. When v1 ships this becomes "v2" and every
    # `Cut: v2` row goes live with no register edit — the whole reason for that direction.
    current_line: str = "v1"

    # ── ratchets ─────────────────────────────────────────────────────────────
    # Relative to `baseline_dir`.
    register_baseline: str = "scripts/requirement_register.baseline"
    append_order_baseline: tuple[str, ...] = DEFAULT_APPEND_ORDER_BASELINE

    # ── the realisation edge ─────────────────────────────────────────────────
    prd_file: str = "prd.md"
    slice_id_prefix: str = "SL-"
    slice_components_column: int = 7  # 0-based index of the `Components` cell
    components_section: str = "## Components"
    # Where commitments are SETTLED. Exempt from the verbatim-restatement check: the register
    # cites THESE, not the other way round.
    decisions_dir: str = "decisions"  # corpus-relative
    append_only_marker: str = "APPEND ONLY. Next id:"

    # PRD lifecycle bands. A contract binds in the band where the artifact it constrains is
    # committed — which band that is, is a property of the lifecycle, so it is config.
    ac_coverage_enforced: tuple[str, ...] = ("planned", "implementing", "verified", "shipped")
    claim_required: tuple[str, ...] = ("designed", "planned", "implementing", "verified", "shipped")
    claim_presence_enforced: tuple[str, ...] = ("designed", "planned", "implementing")
    claim_history: tuple[str, ...] = ("cancelled",)
    drift_advisory_only: tuple[str, ...] = ("shipped",)
    prd_order: tuple[str, ...] = (
        "stub",
        "prd-drafted",
        "designed",
        "planned",
        "implementing",
        "verified",
        "shipped",
    )
    prd_cancelled: str = "cancelled"

    # ── the prose corpus that may CITE a requirement ─────────────────────────
    prose_extra_dirs: tuple[str, ...] = (".claude", ".fleet")  # repo-relative
    #: Root files outside the knowledge base that may cite a requirement. EMPTY by default: a
    #: root `CLAUDE.md` is one project's convention, so a corpus that has one names it here.
    prose_extra_files: tuple[str, ...] = ()  # repo-relative
    # Pruned DURING the walk, never descended: an agent worktree is a FULL checkout, so
    # descending one reaches a second copy of the corpus and reports everything twice.
    prose_skip_dirs: tuple[str, ...] = ("worktrees",)
    # Pruned at the TOP of `.claude/` only: `.claude/run/<command>/` is a command's own
    # checkout-scoped working state (spine.md → *A command's own state*), gitignored and never
    # the corpus. A knowledge bootstrap's review notes quote statements there by design.
    prose_skip_top_dirs: tuple[str, ...] = ("run",)
    prose_skip_names: tuple[str, ...] = ("prd.md",)  # the PRD claim check owns those ids
    # A generated artifact that lists hundreds of ids by construction would otherwise drown
    # the drift advisory in its own output.
    status_artifact: str = "requirement-status.md"  # corpus-relative
    restatement_min_len: int = 25

    # ── the statement guard (stateless since ENG-12971: no lock file) ────────
    base_ref: str = "origin/main"

    # ── exhaustive commitment coverage ───────────────────────────────────────
    # Corpus-relative roots of the prose that can carry a *"the system shall / never"*.
    coverage_roots: tuple[str, ...] = ("specs/", "decisions/")
    unclaimed_baseline: str = "requirements/UNCLAIMED.baseline"  # corpus-relative
    excluded_types: dict[str, str] | None = None  # None -> DEFAULT_EXCLUDED_TYPES

    # ── the todo register ────────────────────────────────────────────────────
    todo_min_statement_len: int = 25
    # A well-formed issue key: project prefix + a number worth trusting. A bare `\b\d+\b`
    # accepts `XX-1`, a key-shaped placeholder that reads as tracked when it is not.
    issue_key_pattern: str = r"\b[A-Z]{2,5}-\d{3,}\b"

    # ── how the entry points are spelled, for `Finding.command` ──────────────
    # A hint is only runnable if it names the command THIS project ships.
    cmd_validate_requirements: str = "python3 scripts/validate_requirements.py"
    cmd_validate_statements: str = "python3 scripts/validate_requirement_statements.py"
    cmd_validate_coverage: str = "python3 scripts/validate_commitment_coverage.py"
    cmd_validate_todos: str = "python3 scripts/validate_todos.py"
    # Named INSIDE two operator messages rather than only in a hint, so they are options
    # too: the register-components check tells a reader to run the component validator,
    # and the unresolvable-id error names the tool that emits the join key. A message that
    # sends someone to a command their project does not have is worse than no message.
    cmd_validate_components: str = "scripts/validate_components.py"
    cmd_component_of: str = "scripts/component_of.py"

    @property
    def excluded_type_reasons(self) -> dict[str, str]:
        return DEFAULT_EXCLUDED_TYPES if self.excluded_types is None else self.excluded_types

    @classmethod
    def from_config(cls, config: Any) -> CommitmentsConfig:
        """Mirror what `Config` already carries; leave everything else at its default.

        Deliberately tolerant: a `Config` predating a key here is not an error, it is a
        default. Reads the namespaced `commitments` section first — the more specific
        statement wins — then the shared keys off `Config` itself.
        """
        if config is None:
            return cls()
        values: dict[str, Any] = {}
        section = getattr(config, "commitments", None)
        known = {f.name: f for f in fields(cls)}
        for name, f in known.items():
            found = _MISSING
            if section is not None:
                found = _direct(section, name)
            if found is _MISSING and name in SHARED_KEYS:
                found = _direct(config, name)
            if found is _MISSING or found is None:
                continue
            values[name] = tuple(found) if isinstance(found, list) and "tuple" in _type_text(f.type) else found
        return cls(**values)


class _Missing:
    pass


_MISSING = _Missing()


def _direct(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, _MISSING)
    return getattr(obj, key, _MISSING)


def _type_text(declared: Any) -> str:
    """A field's declared type as text — TOML gives lists where a field wants a tuple."""
    return declared if isinstance(declared, str) else str(getattr(declared, "__name__", declared))
