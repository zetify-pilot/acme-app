"""Every value the planning checks used to hardcode, as a neutral default a project can set.

The eight validators these checks were ported from named one repository throughout — a
`knowledge/programs.md`, a `PG-NN` id, a `## Decomposition record` heading, an
`ACTIVE_SLICE_CEILING` of 40. Each of those is a *project's* choice, not a property of the
shape, so each is a field here. **A default describes the shape, never one corpus's history:**
the corpus-shape defaults (register names, prefixes, lifecycle bands) are neutral, and the
values that named Fleet's own slice, PRD, clause ids and browser runner are empty or derived
from the corpus being read. A project — Fleet included — sets its own values in its own
`.fleet/fleet.toml`; an install that configures nothing gets the shape and no home ids.

**Where a value lives is not duplicated here.** Every option the spine's `Config` already
models — which register, which detail directory, which id prefix, which prefixes are reserved
— is READ FROM IT (`PlanningConfig.of`), so a project reshapes its corpus in one place and
these checks follow. The fields below that mirror those names hold the same defaults only so
`PlanningConfig()` is usable on its own; against a real knowledge base the spine's value wins.

What is left is genuinely planning-specific and has nowhere else to live: the register column
lists, the `kind:` vocabularies, the work-in-progress ceiling, the rule cutovers, the section
headings two process gates read, and the command templates a finding names as its fix. Those
are the `[fleet.planning]` table — `Config.planning` carries it, `PlanningConfig.of`
reads it, and a project sets any field below by name:

    [fleet.planning]
    active_slice_ceiling = 8
    slice_kinds = ["feature", "capability"]

A misspelled key there is refused when the config file is READ (`config.section_from_table`
checks the table against this dataclass's own field names), which is where a typo is cheap to
report. `from_overrides` below stays tolerant for the other caller — a project passing a
mapping in code, possibly written for a newer kit than the one running — because a check that
cannot start at all is a worse failure than a key that did nothing.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from dataclasses import field as dataclass_field
from typing import Any, ClassVar

from fleet_knowledge.config import Config

# ─── The register tier ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PlanningConfig:
    """Options for the program / slice / PRD planning checks."""

    #: WHERE NEW SLICES GO (2026-10-27, FLT-1281): `"programs"` — under a program, as always, and what an
    #: absent setting means for every repository that existed before it — or `"areas"`, under a feature
    #: area, which only a fresh `fleet init` writes. It never decides whether a row is valid: both shapes
    #: check in both modes (`fleet_knowledge.planningmode`).
    mode: str = "programs"
    #: EVERY SLICE WITHOUT AN AREA FAILS (2026-10-28, FLT-1280) — not only a new or changed one, which fails
    #: whatever this says; an untouched one is otherwise only noted. Absent means false; a fresh `fleet init`
    #: writes true.
    require_area: bool = False

    # --- where things live (knowledge-relative) ---
    program_register: str = "programs.md"
    slice_register: str = "slices.md"
    program_detail_dir: str = "programs"
    slice_detail_dir: str = "slices"
    prds_dir: str = "prds"
    roadmap_file: str = "roadmap.md"
    capability_ledger: str = "capability-aliases.md"
    component_registry: str = "specs/architecture/components.md"
    #: The program-tier waiver file: programs whose composed proof is deliberately not planned.
    #: Grammar and ratchet as before. The slice tier has NO such file since ENG-12602 — a
    #: slice's waiver is a reasoned `proof_waiver` on its own row fragment, so it can never be
    #: a shared regenerated file two branches collide on.
    program_proof_baseline: str = "programs/UNCLAIMED.baseline"
    #: Where drill records live (knowledge-relative). A `Verified by` entry `drill:<stem>` names
    #: `<drills_dir>/<stem>.md`. Seeded from the spine's `drills_dir`.
    drills_dir: str = "drills"
    #: Where the requirement registers live, knowledge-relative. The id-collision check reads
    #: them to learn which prefixes are already claimed, so it has to be told when a corpus
    #: keeps them somewhere other than `requirements/` — otherwise it allocates an id into a
    #: namespace a register it never saw already owns.
    requirements_dir: str = "requirements"
    #: Where the feature maps live, knowledge-relative. The id-collision check reads their
    #: `CAP-NNNN` rows as the live capability id set, since allocation no longer appends to
    #: `capability-aliases.md` (ENG-12981).
    features_dir: str = "features"
    # Repo-relative (NOT knowledge-relative) — the id-collision check reads them at a git ref.
    migrations_dirs: tuple[str, ...] = ("migrations",)
    #: Id claims (`_claims.py`): every contended id is reserved by creating `refs/ids/<ID>` on
    #: the GitHub repository behind `id_claim_remote` — an atomic create that answers HTTP 422
    #: to the second caller. OFF by default: a corpus with no GitHub remote has no claim
    #: namespace, and a fixture must not reach the network. A project turns it on with
    #: `[fleet.planning] id_claims = true`; `id_claim_repo` (`owner/repo`) overrides the slug
    #: derived from the remote's URL.
    id_claims: bool = False
    id_claim_remote: str = "origin"
    id_claim_namespace: str = "refs/ids/"
    id_claim_repo: str = ""

    # --- id shapes ---
    # Derived from a PREFIX and a digit floor rather than carried as whole regexes, because
    # the prefix is what the spine's `Config` models (`program_prefix`, `slice_prefix`,
    # `capability_prefix`) and a second copy of it as a pattern is a second place to change.
    program_prefix: str = "PG"
    slice_prefix: str = "SL"
    capability_prefix: str = "CAP"
    program_id_digits: int = 2
    slice_id_digits: int = 3
    capability_id_digits: int = 4
    component_id_pattern: str = r"^[a-z0-9]+(-[a-z0-9]+)*$"
    # The append-only counter every register carries. `{2,}` digits, not `{3,}`: program ids
    # are `PG-29` and a three-digit floor silently drops every PG counter (ENG-9192).
    next_id_marker: str = r"APPEND ONLY\. Next id:"
    counter_pattern: str = r"APPEND ONLY\. Next id:\s*`?([A-Z]{2,5}-\d{2,})`?"
    #: The counter shape the register-shape check reads. Narrower than `counter_pattern` on
    #: purpose: that one sweeps a whole corpus for any register's counter, while this one
    #: validates the counter of a register whose id shape is already known.
    register_counter_id_pattern: str = r"[A-Z]{2}-\d+"
    prefixed_id_pattern: str = r"^([A-Z]{2,5})-(\d{2,})$"
    #: Namespaces a requirement register may not claim. Passed straight to the package's
    #: register reader, alongside `requirements_dir` above.
    reserved_requirement_prefixes: frozenset[str] = frozenset({"ENG"})

    # --- register table shape ---
    #: `Disposition` is LAST on both tiers, and that position is the whole additivity argument:
    #: a row read positionally from a register authored before the column existed is padded,
    #: never shifted, so history keeps meaning what it meant. The header check is still exact —
    #: a current register has to carry the column — and `disposition_values` names what the
    #: cell may say.
    program_columns: tuple[str, ...] = ("ID", "Name", "Kind", "Verified by", "Requires", "Disposition")
    slice_columns: tuple[str, ...] = (
        "ID",
        "Name",
        "Kind",
        "Program",
        "Done when",
        "Verified by",
        "Depends on",
        "Components",
        "Disposition",
    )
    #: The words a `Disposition` cell is REFUSED with a reason of their own: each is a claim
    #: about ship-state, which is computed and never written above the PRD tier. Anything else
    #: off the grammar is refused too, with the general message; these get the specific one
    #: because they are exactly what somebody reaching for a status column will type.
    disposition_ship_state_words: frozenset[str] = frozenset(
        {"delivered", "closed", "done", "shipped", "complete", "completed", "finished", "active", "open", "cancelled"}
    )
    program_kinds: frozenset[str] = frozenset({"outcome", "program"})
    slice_kinds: frozenset[str] = frozenset({"feature", "capability", "gap-set"})
    #: A `Done when` shorter than this is a topic, not a completion condition.
    done_when_min: int = 40
    #: At most this many slices may hold a live (non-terminal) PRD.
    #: Raised 20 → 40 on 2026-09-25 (`knowledge/decisions/2026-09-25-raise-the-active-slice-ceiling-to-forty.md`),
    #: which is the second raise the 2026-08-19 record refused in advance. See that record for the cost.
    active_slice_ceiling: int = 40

    # --- the PRD tier ---
    prd_statuses: frozenset[str] = frozenset(
        {"stub", "prd-drafted", "designed", "planned", "implementing", "verified", "shipped", "cancelled"}
    )
    prd_terminal: frozenset[str] = frozenset({"shipped", "cancelled"})
    prd_order: tuple[str, ...] = (
        "stub",
        "prd-drafted",
        "designed",
        "planned",
        "implementing",
        "verified",
        "shipped",
    )
    priorities: frozenset[str] = frozenset({"urgent", "high", "medium", "low"})
    priority_required: frozenset[str] = frozenset({"prd-drafted", "designed", "planned", "implementing", "verified"})
    sections_required: frozenset[str] = frozenset({"designed", "planned", "implementing", "verified"})
    required_prd_sections: tuple[str, ...] = (
        "Vision Alignment",
        "Source Trace",
        "Value Justification",
        "Operational Resilience",
    )
    designed_or_beyond: frozenset[str] = frozenset({"designed", "planned", "implementing", "verified", "shipped"})
    #: The lanes a PRD's frontmatter `lane:` may name (0158 / ENG-13263) — the corpus's read-side
    #: mirror of the fleet's lane table (`fleet-service`'s `dispatch/lanes.py` `LANES`, each row's
    #: `repo:<name>` label). This package cannot import that table (it runs under a bare `python3`
    #: with no dependencies, and the table is per-deployment data), so a corpus declares the lanes
    #: its PRDs may target here and the checker refuses any other name BY NAME rather than let it
    #: fall back to the corpus default. `fleet.toml`:
    #:
    #:     [fleet.planning]
    #:     lanes = ["fleet"]
    #:
    #: Empty (the default) refuses EVERY `lane:` — honest for a corpus that targets only its own
    #: lane and therefore never writes the field, and it keeps a self-hoster from silently routing
    #: work to a lane it never registered.
    lanes: frozenset[str] = frozenset()

    # --- cross-corpus references (`fleet_knowledge.corpusref`) ---
    #: This corpus's own name — the lane name. A reference qualified with it (`acme:0899` in
    #: the `acme` corpus) is local. Empty: the corpus names itself nothing, so EVERY qualified
    #: reference is foreign and must be declared below.
    corpus: str = ""
    #: The sibling corpora a reference may name: `name -> knowledge dir`, repo-relative. A path
    #: that exists is indexed and resolved against; `""` (or a path not on disk) declares the
    #: corpus known but unreadable here, and its references are counted as unverified rather
    #: than passed. `prd`, `drill`, `web`, `admin` and `tag` are reserved and refused.
    #:
    #:     [fleet.planning]
    #:     corpus = "acme"
    #:     [fleet.planning.corpora]
    #:     fleet = "fleet/knowledge"
    #:
    #: An entry may instead be a table that also names the requirement-register prefixes the
    #: sibling OWNS — a bare `FLT-104` then resolves there exactly as `fleet:FLT-104` does, and
    #: the prefix is never allocated or claimed here. Planning-id prefixes are never ownable:
    #:
    #:     fleet = { path = "fleet/knowledge", prefixes = ["FLT"] }
    corpora: Mapping[str, Any] = dataclass_field(default_factory=dict)

    # --- status_history ---
    #: Only these may stamp `verified` — the party that wrote the code never certifies it.
    verified_stampers: frozenset[str] = frozenset({"verify"})
    #: Transitions recorded on or after this day are held to the ordering rules.
    status_history_cutover: str = "2026-07-21"
    risk_acceptance_stampers: frozenset[str] = frozenset({"user"})
    #: A `verified` entry stamped by one of these records that the accountable PERSON accepted
    #: the PRD on their own word, not that a verify pass ran. It stands only with a `note:`
    #: quoting the person's dated words and an `accepted_by:` naming them.
    owner_acceptance_stampers: frozenset[str] = frozenset({"owner-accepted"})
    revert_target_states: frozenset[str] = frozenset({"prd-drafted", "designed"})
    revert_stampers: frozenset[str] = frozenset({"design", "plan"})

    # --- differentiator labels ---
    canonical_differentiator_labels: Mapping[str, str] = dataclass_field(
        default_factory=lambda: dict(DEFAULT_DIFFERENTIATOR_LABELS)
    )

    # --- the component registry ---
    #: The closed set of layers is NOT here: it is the registry's own `## Layers` table, read
    #: through `corpus.component_layers` — the same reader the board draws from — so a corpus
    #: names its architecture once, in the registry, and the check follows. These are the
    #: declared layers that hold no components (drawn from another axis — outcomes, the
    #: customer's own systems); a component placed in one is refused. Empty by default: which
    #: layers those are is a property of one corpus's architecture, not of the shape.
    #:
    #:     [fleet.planning]
    #:     non_component_layers = ["business-value", "customer-data"]
    non_component_layers: frozenset[str] = frozenset()
    components_heading: str = "## Components"
    proposed_components_heading: str = "## Proposed components"
    outcomes_heading_prefix: str = "## Outcomes"
    #: A ship-state-ish column header is the one thing the component registry must never grow.
    banned_component_column_pattern: str = r"^\s*(status|state|shipped|progress|health|done)\s*$"

    # --- the decomposition record (program `Requires`) ---
    decomposition_heading: str = "## Decomposition record"

    # --- PRD plans ---
    plan_filename_pattern: str = r"^(?P<fam>backend-plan|frontend-plan)(?:-(?P<n>\d+))?\.md$"
    plan_cutover: str = "2026-07-21"
    ux_design_file: str = "ux-design.md"
    approved_design_heading: str = r"^#+\s*Approved design\b"
    additive_surface_pattern: str = r"^#+\s*Surface scope:\s*additive to an existing surface\b"
    page_spec_pattern: str = r"`([^`\s]*/[^`\s]*\.spec\.md)`"
    #: The token a frontend plan must carry for its browser-verification row. Empty means the
    #: row is not required: the package cannot know which runner a project uses, and a finding
    #: naming `playwright` in a repository that has never heard of it is a false alarm. A
    #: project that verifies in a browser sets its own token (`playwright`, `cypress`, …).
    browser_verification_token: str = ""

    # --- the two process-artifact gates ---
    commitments_section: str = "Commitments"
    commitments_cutoff: str = "2026-08-14"
    scope_ledger_section: str = "Scope ledger"
    scope_ledger_cutoff: str = "2026-08-27"
    #: The `[ext]` promotion gate (`prd_ext_promotion`): a PRD whose prd.md was added on or
    #: after this date may not carry a bare `[ext]` acceptance criterion — the criterion is
    #: promoted into its slice's `## Bar` and cites the row. Earlier PRDs shipped under the
    #: older convention (an `[ext]` row was N/A'd until its dependency existed) and are read
    #: as history, not re-gated.
    ext_promotion_cutoff: str = "2026-09-10"
    acceptance_section: str = "Acceptance criteria"
    default_diff_base: str = "origin/main"
    #: The remediation each gate prints under its failure list. Held as whole blocks rather
    #: than assembled from parts because the text names one project's commands and phases,
    #: and a project that renames them wants to rewrite the paragraph, not fight a template.
    #: `{section}` and `{cutoff}` are substituted.
    commitments_remediation: str = dataclass_field(default_factory=lambda: DEFAULT_COMMITMENTS_REMEDIATION)
    scope_ledger_remediation: str = dataclass_field(default_factory=lambda: DEFAULT_SCOPE_LEDGER_REMEDIATION)
    plans_shallow_refusal: str = dataclass_field(default_factory=lambda: DEFAULT_PLANS_SHALLOW_REFUSAL)

    # --- the clause digest ---
    #: The one slice whose clause ids a project additionally holds to `clause_required_ids`.
    #: EMPTY by default: every slice detail file carrying a `done-cell-digest` is still bound by
    #: the digest alone, and naming a slice here is a project saying *this* decomposition must
    #: keep every clause. A project names its own slice in its own `.fleet/fleet.toml`.
    clause_digest_slice: str = ""
    #: The heading that opens a clause-decomposition section, however a corpus names the PRD
    #: it decomposes. The generic default is derived from the reader's repo: any
    #: `## Clause decomposition …` heading is read. A project with a different spelling sets
    #: its own pattern.
    clause_digest_heading: str = r"^##\s+Clause decomposition\b.*$"
    #: The same heading as a human reads it — what the "missing section" message names.
    clause_digest_heading_label: str = "## Clause decomposition"
    clause_digest_marker: str = r"<!--\s*done-cell-digest:\s*sha256:([0-9a-f]{64})\s*-->"
    #: The clause-id prefix for the configured slice. EMPTY means derive it from the slice id
    #: (`SL-199` -> `SL199-C`), which is what every other bound slice already uses.
    clause_row_prefix: str = ""
    #: The clause ids the configured slice must carry. EMPTY means no minimum: a decomposition
    #: is complete when it has data rows. A project that names `clause_digest_slice` also names
    #: the ids that slice may not shed.
    clause_required_ids: tuple[str, ...] = ()

    # --- the fix a human runs ---
    #: Templates rendered into `Finding.command`. `{}`-format placeholders are named for the
    #: id they take. A project with no such commands sets a key to "" and the finding carries
    #: a hint alone.
    commands: Mapping[str, str] = dataclass_field(default_factory=lambda: dict(DEFAULT_COMMANDS))

    # ── overrides ────────────────────────────────────────────────────────────────────

    #: `PlanningConfig` field <- `fleet_knowledge.config.Config` field. The spine owns the
    #: answer to "where does this corpus keep X", and this table is the only place that
    #: binding is written down.
    FROM_SPINE: ClassVar[Mapping[str, str]] = {
        "program_register": "programs_register",
        "slice_register": "slices_register",
        "program_detail_dir": "programs_detail_dir",
        "slice_detail_dir": "slices_detail_dir",
        "prds_dir": "prds_dir",
        "capability_ledger": "capability_aliases",
        "component_registry": "components_registry",
        "program_prefix": "program_prefix",
        "slice_prefix": "slice_prefix",
        "capability_prefix": "capability_prefix",
        "reserved_requirement_prefixes": "reserved_prefixes",
        "requirements_dir": "requirements_dir",
        "features_dir": "features_dir",
        "drills_dir": "drills_dir",
    }

    @classmethod
    def of(cls, kb: Any) -> PlanningConfig:
        """This knowledge base's planning options.

        Defaults, then whatever the spine's `Config` says about the shape of this corpus, then
        any `planning` overrides. An option the spine sets to "" is carried through as "" —
        that is a project declaring it does not have that register, and a check's `applies()`
        has to be able to see it.
        """
        spine = getattr(kb, "config", None)
        base = cls()
        seeded: dict[str, Any] = {}
        for mine, theirs in cls.FROM_SPINE.items():
            if spine is None or not hasattr(spine, theirs):
                continue
            seeded[mine] = _coerce(getattr(base, mine), getattr(spine, theirs))
        return cls.from_overrides({**seeded, **dict(_planning_overrides(spine) or {})})

    @classmethod
    def from_overrides(cls, overrides: Mapping[str, Any] | None) -> PlanningConfig:
        base = cls()
        if not overrides:
            return base
        known = {f.name: f for f in fields(cls)}
        patch: dict[str, Any] = {}
        for key, value in overrides.items():
            f = known.get(str(key))
            if f is None:
                continue  # forward compatibility: an unknown key is not an error
            patch[f.name] = _coerce(getattr(base, f.name), value)
        return replace(base, **patch) if patch else base

    # ── compiled shortcuts ────────────────────────────────────────────────────────────

    @property
    def program_id_shape(self) -> str:
        """The id shape a human reads in a message: `PG-NN`."""
        return f"{self.program_prefix}-{'N' * self.program_id_digits}"

    @property
    def slice_id_shape(self) -> str:
        """The id shape a human reads in a message: `SL-NNN`."""
        return f"{self.slice_prefix}-{'N' * self.slice_id_digits}"

    @property
    def capability_id_pattern(self) -> str:
        """A capability id as it appears INSIDE a cell — unanchored, so `findall` works."""
        return rf"{re.escape(self.capability_prefix)}-\d{{{self.capability_id_digits}}}"

    def re_program_id(self) -> re.Pattern[str]:
        return re.compile(rf"^{re.escape(self.program_prefix)}-\d{{{self.program_id_digits},}}$")

    def re_slice_id(self) -> re.Pattern[str]:
        return re.compile(rf"^{re.escape(self.slice_prefix)}-\d{{{self.slice_id_digits},}}$")

    def command(self, key: str, **fmt: object) -> str | None:
        """A runnable fix for `key`, or None when the project defines none."""
        template = self.commands.get(key, "")
        if not template:
            return None
        try:
            return template.format(**fmt)
        except (KeyError, IndexError):
            return template


#: Canonical differentiator-label registry — one slug per numbered differentiator. A PRD's
#: `labels:` must use the canonical form so faceting treats a differentiator as one bucket
#: rather than N aliases. A project with no differentiator axis sets this to `{}`.
DEFAULT_DIFFERENTIATOR_LABELS: Mapping[str, str] = {
    "1": "diff:1-runtime-substrate",
    "2": "diff:2-path-aware",
    "3": "diff:3-protocol-plural",
    "4": "diff:4-ontology-as-contract",
    "5": "diff:5-narrowing",
    "6": "diff:6-customer-hosted",
    "7": "diff:7-policy-near-data",
    "8": "diff:8-actions",
    "9": "diff:9-one-graph",
    "10": "diff:10-compliance",
    "11": "diff:11-evidence",
}

#: What a human is told to do about a missing `## Commitments` section.
#:
#: Deliberately names no command: the package cannot know what a project calls the step that
#: writes the section, and a default that guessed would print a command nobody can run. A
#: consuming project supplies its own text through its binding module, which is the one
#: file in that checkout allowed to know its own command vocabulary.
#: `{section}` and `{cutoff}` are substituted.
DEFAULT_COMMITMENTS_REMEDIATION = (
    "\nThe design stage's commitments step — reconciling the requirement register — is what\n"
    "this section records, and the section is its only evidence. To clear:\n"
    "  1. Run that step, then work the UNSATISFIED list: a need nothing is building is either\n"
    "     an unscheduled gap or an edge into a mechanism this design's Non-Goals cut (the\n"
    "     second wants a supersession).\n"
    "  2. Write the `## {section}` section: the rows this design added or superseded, IDs\n"
    "     only, plus the PRD's refreshed `implements:`.\n"
    '  3. "none" is a legitimate outcome — but only written WITH the candidates examined. An\n'
    "     empty statement is the un-backed conclusion that step exists to prevent.\n"
    "\nA design authored before {cutoff} predates the step and is never flagged; if one here is\n"
    "a genuine pre-rule artifact, move the cutoff rather than exempting the PRD."
)

#: What a human is told to do about a missing `## Scope ledger` section. See above on why it
#: names no command. `{section}` and `{cutoff}` are substituted.
DEFAULT_SCOPE_LEDGER_REMEDIATION = (
    "\nScope discipline says what may enter a PRD unasked, and this section is its only\n"
    "evidence. To clear:\n"
    "  1. Run the scope offer for the artifact — once at PRD authoring, once at design. ONE\n"
    "     batched question over everything you withheld, no recommendation marked. A headless\n"
    "     run makes no offer and takes nothing — it publishes the withheld list as a veto\n"
    "     receipt and moves on.\n"
    "  2. Write the `## {section}` section: one row per addition beyond the ask, ADMITTED AND\n"
    "     WITHHELD ALIKE, with the Basis naming the acceptance criterion that cannot pass\n"
    "     without it, or the already-edited file whose written-rule violation it fixes. An\n"
    "     `admitted` row naming neither is a defect: an addition that traces to neither is\n"
    "     scope nobody authorised.\n"
    '  3. "none" is a legitimate and expected outcome — but written WITH what was considered.\n'
    "     An empty section is not.\n"
    "  4. Rows are ADDITIONS, never decisions. A ledger listing every design fork is the bloat\n"
    "     this rule exists to stop and hides the rows that matter.\n"
    "\nAn artifact authored before {cutoff} predates the rule and is never flagged; if one here\n"
    "is a genuine pre-rule artifact, move the cutoff rather than exempting the PRD."
)

#: Why the plan gate refuses to run on a shallow clone, and how to repair it. `{cutover}`.
DEFAULT_PLANS_SHALLOW_REFUSAL = (
    "PRD plan validation refused: this checkout is a shallow git clone.\n"
    "\n"
    "Each plan is dated via `git log --diff-filter=A` to grandfather plans authored before\n"
    "{cutover}. On a shallow clone that returns the shallow boundary commit as the add-date\n"
    "for every file, so nothing is grandfathered and the entire legacy corpus is validated —\n"
    "hundreds of phantom violations, none of them real.\n"
    "\n"
    "Repair (additive — objects only, no working-tree change):\n"
    "  git fetch --unshallow\n"
)

#: The fixes these checks point at, as `Finding.command` templates keyed by a STABLE name.
#:
#: EMPTY by default, and that is the design rather than an omission: the package cannot know
#: what a project calls the command that cuts a slice or decomposes a program, and a finding
#: carrying a command nobody can run is worse than one carrying only a hint. A project fills
#: this in through its binding module, the one file entitled to know it. The keys a check
#: looks up are: slice_create, slice_edit, program_decompose, program_ship, prd_design,
#: prd_create, prd_plan, prd_verify, page_spec, component_create,
#: write_program_proof_baseline, allocate_ids, unshallow.
DEFAULT_COMMANDS: Mapping[str, str] = {}


def _coerce(current: Any, value: Any) -> Any:
    """Shape an override like the default it replaces (tuple stays tuple, set stays set)."""
    if isinstance(current, frozenset):
        return frozenset(value)
    if isinstance(current, tuple):
        return tuple(value)
    if isinstance(current, bool):
        return bool(value)
    if isinstance(current, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(current, Mapping):
        return dict(value)
    if isinstance(current, str):
        return str(value)
    return value


@dataclass(frozen=True)
class ConfigWithPlanning(Config):
    """A `Config` that carries a `planning` table — now exactly a `Config`.

    The spine's `Config` grew the `planning` key (along with `commitments` and `structure`),
    which is what this subclass existed to anticipate:

        kb = KnowledgeBase(root=root, knowledge=root / "knowledge",
                           config=Config(planning={"commands": {...}}))

    Kept as a name because callers outside this package construct it — `scripts/`'s binding
    shim among them — and because a name that means the same thing costs nothing while a
    removed one costs an afternoon. New code should say `Config`.
    """


def _planning_overrides(config: Any) -> Mapping[str, Any] | None:
    """The `planning` mapping carried on the config object, if it has one."""
    if config is None:
        return None
    table = getattr(config, "planning", None)
    return table if isinstance(table, Mapping) else None
