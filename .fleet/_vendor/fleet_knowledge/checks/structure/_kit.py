"""Shared plumbing for the structure checks.

Three things live here and nowhere else in this subpackage:

  * **The spine binding.** `Finding`, `Check` and `KnowledgeBase` come from the package
    spine; this module is the single import site for them, so a change there is one
    edit here rather than five.
  * **Config lookup.** `option(kb, key, default)` reads a per-project override off the
    knowledge base's `Config` and returns the default when the key is absent. Every
    hardcoded path, id prefix, filename or baseline location in a ported validator goes
    through it, with the value it has in the originating repository as the default — so
    that repository behaves identically and another one re-points the check with config
    instead of a fork. Options the spine's `Config` already defines are read under THAT
    name (`features_dir`, `capability_prefix`, `coverage_ledger`, …); this family's own
    live in a `[fleet.structure]` table, whose accepted keys are `KNOWN_OPTIONS`
    below. The lookup stays tolerant of a `Config` that has never heard of a key, because
    a check must never fail on a config older than itself.
  * **The reporter.** A ported validator prints `file: message` lines and exits 1; a
    `Check` returns `Finding`s. `Reporter` records both from one call, so the legacy
    stdout stays byte-identical while the structured findings gain hints and commands.

Stdlib only.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fleet_knowledge import registers
from fleet_knowledge.config import Config, KnowledgeBase
from fleet_knowledge.runner import Check, Finding

__all__ = [
    "KNOWN_OPTIONS",
    "OWN_OPTIONS",
    "SPINE_OPTIONS",
    "Check",
    "Finding",
    "KnowledgeBase",
    "Reporter",
    "frontmatter",
    "local_kb",
    "option",
    "programs",
    "rel_to",
    "slices",
]


def local_kb(root: Path, knowledge: Path | None = None, config: Config | Any = None) -> KnowledgeBase:
    """A `KnowledgeBase` for `root` with no config file consulted.

    Used by the `scripts/` shims (whose root is the checkout they sit in) and by the
    tests (whose root is a fixture tree). Every option defaults to the value the
    originating repository already had, so a config-less base behaves exactly as the
    standalone validators did.
    """
    root = root.resolve()
    kdir = (knowledge if knowledge is not None else root / "knowledge").resolve()
    return KnowledgeBase(root=root, knowledge=kdir, config=config if config is not None else Config())


# --------------------------------------------------------------------------------------
# Config lookup
# --------------------------------------------------------------------------------------
_SENTINEL = object()

#: Every key this family's checks read through `option`. THE section's vocabulary: a
#: `[fleet.structure]` table is validated against it, so a misspelled key is refused
#: at config-read time instead of silently resolving to the default and looking like an
#: option that had no effect.
#:
#: Two groups, and the split matters. The first are options the spine's `Config` already
#: models — a structure section may re-state one, and then it wins FOR THIS FAMILY ONLY,
#: which is what a corpus needs when (say) its journeys live somewhere its PRDs do not. The
#: rest are this family's own and exist nowhere else.
#:
#: The list is exhaustive by TEST, not by discipline: `tests/checks/structure/test_options.py`
#: scans this package's sources for every `option(kb, "…")` literal and fails on any
#: difference in either direction. A key added to a check and forgotten here would otherwise
#: be unconfigurable while looking configurable.
SPINE_OPTIONS: frozenset[str] = frozenset(
    {
        "capability_aliases",
        "capability_prefix",
        "components_registry",
        "coverage_ledger",
        "features_dir",
        "journeys_dir",
        "prds_dir",
        "programs_register",
    }
)

OWN_OPTIONS: frozenset[str] = frozenset(
    {
        # the architecture-doc freshness contract
        "arch_component_tables",
        "arch_details_dirname",
        "arch_dir",
        "arch_openapi_spec",
        "arch_propagation_header",
        "arch_registry_name",
        "arch_specs_dir",
        # exhaustive source coverage (journeys)
        "coverage_excluded_leaves",
        "coverage_excluded_roots",
        "coverage_excluded_segments",
        "coverage_extra_pattern",
        "coverage_extra_scan",
        "coverage_generated_leaf_pattern",
        "coverage_roots",
        # the feature-map vocabulary
        "capability_id_digits",
        "feature_briefs_strict",
        "feature_families",
        "feature_family_min_members",
        "feature_kind_default",
        "feature_kinds",
        "feature_tiers",
        # the file-type registry
        "file_types_header_exts",
        "file_types_registry",
        "file_types_universal",
        # cross-subtree hygiene
        "hygiene_arch_audits_dir",
        "hygiene_audits_dir",
        "hygiene_date_triggers",
        "hygiene_doc_parity",
        "hygiene_drift_patterns",
        "hygiene_drift_scope",
        "hygiene_specs_index",
        "hygiene_transient_fields",
        # journeys, features and the surfaces they claim
        "journeys_ac_heading_pattern",
        "journeys_admin_routes",
        "journeys_admin_routes_marker",
        "journeys_banned_markers",
        "journeys_base_ref",
        "journeys_broad_source_root_pattern",
        "journeys_deferral_cues",
        "journeys_dispositions",
        "journeys_flows_subdir",
        "journeys_frontend_scan_roots",
        "journeys_frontend_scan_suffixes",
        "journeys_maps_subdir",
        "journeys_non_route_surfaces",
        "journeys_org_route_prefix",
        "journeys_permissions_contract",
        "journeys_prd_lifecycle_states",
        "journeys_prose_path_roots",
        "journeys_redirect_elements",
        "journeys_retire_ack_cues",
        "journeys_retirement_markers",
        "journeys_surface_skip_prefixes",
        "journeys_unclaimed_baseline",
        "journeys_web_routes",
        "journeys_web_routes_marker",
        "journeys_write_baseline_command",
        # path resolution
        "paths_generated_on_demand",
        "paths_ignore_path_prefixes",
        "paths_ignore_prefixes",
        "paths_ignore_substrings",
        "paths_knowledge_only_dirs",
        "paths_knowledge_only_files",
        "paths_knowledge_only_skip_target_dirs",
        "paths_planned_dirs",
        "paths_planned_files",
        "paths_root_hints",
        "paths_scan_suffixes",
        # shared with hygiene and journeys, owned by neither
        "specs_dir",
    }
)

KNOWN_OPTIONS: frozenset[str] = SPINE_OPTIONS | OWN_OPTIONS


def _probe(holder: Any, key: str) -> Any:
    """One lookup attempt against a config-ish object: attribute, then mapping."""
    value = getattr(holder, key, _SENTINEL)
    if value is not _SENTINEL:
        return value
    if isinstance(holder, Mapping):
        return holder.get(key, _SENTINEL)
    return _SENTINEL


def option(kb: KnowledgeBase, key: str, default: Any) -> Any:
    """The project's value for `key`, or `default`.

    Order: this family's own `structure` section, then the spine's `Config` itself, then the
    older `options`/`extra`/`checks` tables a caller may still be passing. The section is
    consulted FIRST because it is the more specific statement — a project that writes both
    `prds_dir` at the top level and `prds_dir` under `[fleet.structure]` is saying
    "this family reads a different one", and the general value winning would make the
    specific one unwritable.

    Deliberately shape-agnostic below that: a key may sit directly on the object or in a
    mapping it exposes. A check must never fail because a knowledge base's config predates
    one of its keys — an absent key means "the default", which is the value this repository
    already had.
    """
    config = getattr(kb, "config", None)
    if config is None:
        return default
    holders = (
        _probe(config, "structure"),
        config,
        _probe(config, "options"),
        _probe(config, "extra"),
        _probe(config, "checks"),
    )
    for holder in holders:
        if holder is _SENTINEL or holder is None:
            continue
        value = _probe(holder, key)
        if value is not _SENTINEL and value is not None:
            return value
    return default


def option_list(kb: KnowledgeBase, key: str, default: Iterable[str]) -> list[str]:
    """`option` narrowed to a list of strings (the common case for path/prefix sets)."""
    value = option(kb, key, None)
    if value is None:
        return list(default)
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def option_tuple(kb: KnowledgeBase, key: str, default: Iterable[str]) -> tuple[str, ...]:
    """`option_list` as a tuple — for constants used with `str.startswith`/`endswith`."""
    return tuple(option_list(kb, key, default))


# --------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------
def rel_to(base: Path, path: Path) -> str:
    """`path` relative to `base` when it is underneath it, else its own string.

    A validator reports `knowledge/features/x.md: …`; a path outside the base (a temp
    file under test, a doc-parity target that moved) must still be reportable rather
    than raising out of the error path.
    """
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return str(path)


@dataclass
class Reporter:
    """Collects a validator's output in both shapes at once.

    `errors` / `warnings` / `notices` are the legacy `file: message` strings, printed
    verbatim by the `main()` entry points so the pre-commit hooks and CI keep seeing the
    exact stdout they see today. `findings` is the same information as `Finding`
    objects, which is what a `Check` returns.
    """

    base: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def _record(
        self,
        bucket: list[str],
        level: str,
        path: Path | None,
        msg: str,
        line: int | None,
        hint: str | None,
        command: str | None,
        prefix: str | None,
    ) -> None:
        rendered = msg if prefix is None else f"{prefix}: {msg}"
        bucket.append(rendered)
        self.findings.append(Finding(level=level, message=msg, path=path, line=line, hint=hint, command=command))

    def err(
        self,
        path: Path | None,
        msg: str,
        *,
        line: int | None = None,
        hint: str | None = None,
        command: str | None = None,
    ) -> None:
        prefix = None if path is None else rel_to(self.base, path)
        self._record(self.errors, "error", path, msg, line, hint, command, prefix)

    def warn(
        self,
        path: Path | None,
        msg: str,
        *,
        line: int | None = None,
        hint: str | None = None,
        command: str | None = None,
    ) -> None:
        prefix = None if path is None else rel_to(self.base, path)
        self._record(self.warnings, "warning", path, msg, line, hint, command, prefix)

    def note(
        self,
        path: Path | None,
        msg: str,
        *,
        line: int | None = None,
        hint: str | None = None,
        command: str | None = None,
    ) -> None:
        prefix = None if path is None else rel_to(self.base, path)
        self._record(self.notices, "advisory", path, msg, line, hint, command, prefix)

    def raw_err(
        self,
        text: str,
        *,
        path: Path | None = None,
        hint: str | None = None,
        command: str | None = None,
    ) -> None:
        """An error line rendered verbatim — it carries its own prefix, or none at all."""
        self._record(self.errors, "error", path, text, None, hint, command, None)

    def raw_note(
        self,
        text: str,
        *,
        path: Path | None = None,
        hint: str | None = None,
        command: str | None = None,
    ) -> None:
        """An advisory line rendered verbatim — it carries its own prefix, or none at all."""
        self._record(self.notices, "advisory", path, text, None, hint, command, None)


# --------------------------------------------------------------------------------------
# Markdown frontmatter (identical in every ported validator)
# --------------------------------------------------------------------------------------
def frontmatter(text: str) -> str | None:
    """The YAML block between the leading `---` fences, or None."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 else None


# --------------------------------------------------------------------------------------
# Program / slice registers
# --------------------------------------------------------------------------------------
# The journeys check resolves a program's `Requires` and a slice's `Depends on`. Both come
# from the ONE register reader the package already ships — a second parser for the same
# table is how the two drift.


def programs(knowledge: Path, own: str | None = None) -> list[dict[str, Any]]:
    """Program rows: `ID | Name | Kind | Verified by | Requires | Disposition`, read positionally.

    `own` is this corpus's name: an own-qualified reference comes back as the local id."""
    return list(registers.programs(knowledge, own=own))


def slices(knowledge: Path, own: str | None = None) -> list[dict[str, Any]]:
    """Slice rows: `ID | Name | Kind | Program | Done when | Verified by | Depends on | Components | Disposition`."""
    return list(registers.slices(knowledge, own=own))
