# The fleet.toml file

Every key Fleet reads from a repository's `.fleet/fleet.toml`, table by table, with its default. Look here before changing a setting, or when Fleet refuses a key.

Each table is checked against exactly these names when the file is read, so a misspelled key is refused rather than ignored. A key left out takes the default.

## `[fleet]`

The shape of the knowledge base: where each register lives and which id prefixes it owns. Paths are relative to the knowledge directory unless the key says otherwise; set one to `""` when the knowledge base has no such file, and the checks over it skip.

| Key | Default | What it sets |
|---|---|---|
| `programs_register` | `"programs.md"` | The programs register. |
| `slices_register` | `"slices.md"` | The slices register. |
| `todos_register` | `"todos.md"` | The todo register. |
| `requirements_dir` | `"requirements"` | The folder of requirement registers. |
| `features_dir` | `"features"` | The folder of feature maps. |
| `journeys_dir` | `"journeys"` | The folder of journeys. |
| `prds_dir` | `"prds"` | The folder of PRDs, one folder per PRD. |
| `programs_detail_dir` | `"programs"` | The folder of programs' detail pages. |
| `slices_detail_dir` | `"slices"` | The folder of slices' detail pages. |
| `drills_dir` | `"drills"` | The folder of drill records, the second kind of proof a `Verified by` may name. |
| `components_registry` | `"specs/architecture/components.md"` | The component registry. |
| `decisions_dir` | `"decisions"` | The folder of decision records. |
| `glossary` | `"specs/glossary.md"` | The glossary. |
| `capability_aliases` | `"capability-aliases.md"` | The register of old capability ids and the ids they became. |
| `coverage_ledger` | `"audits/feature-coverage-ledger.md"` | The feature-coverage ledger. |
| `program_prefix` | `"PG"` | The prefix of program ids. |
| `slice_prefix` | `"SL"` | The prefix of slice ids. |
| `capability_prefix` | `"CAP"` | The prefix of capability ids. |
| `todo_prefix` | `"TODO"` | The prefix of todo ids. |
| `requirement_prefixes` | `[]` | Limits the prefixes requirement registers may declare. Empty accepts the `prefix:` each register declares. |
| `reserved_prefixes` | `["ENG"]` | Prefixes no requirement register may claim, because something else writes ids of that shape, such as an issue tracker's team key. |
| `board_guidance` | `""` | The file, from the repository root, that describes this repository's commands to the board. Empty means none, and the board uses neutral words. |
| `linear_enabled` | `false` | Lets the checks that need the issue tracker run. When false they skip. |
| `disabled_checks` | `[]` | Checks this repository does not run. Each is reported as disabled. A name that matches no check is refused, and `tracker-clients` is mandatory. |
| `baseline_dir` | `"."` | Where ratchet baselines live, relative to the repository root. |
| `knowledge_dir` | `"knowledge"` | The knowledge directory, relative to the repository root. |
| `version` | — | The format version of the file itself, which `fleet commands sync` migrates. |

## `[fleet.planning]`

How the planning checks read programs, slices and PRDs: register columns, id shapes, kinds, ceilings and the planning mode.

| Key | Default |
|---|---|
| `mode` | `"programs"` |
| `require_area` | `false` |
| `program_register` | `"programs.md"` |
| `slice_register` | `"slices.md"` |
| `program_detail_dir` | `"programs"` |
| `slice_detail_dir` | `"slices"` |
| `prds_dir` | `"prds"` |
| `roadmap_file` | `"roadmap.md"` |
| `capability_ledger` | `"capability-aliases.md"` |
| `component_registry` | `"specs/architecture/components.md"` |
| `program_proof_baseline` | `"programs/UNCLAIMED.baseline"` |
| `drills_dir` | `"drills"` |
| `requirements_dir` | `"requirements"` |
| `features_dir` | `"features"` |
| `migrations_dirs` | `["migrations"]` |
| `id_claims` | `false` |
| `id_claim_remote` | `"origin"` |
| `id_claim_namespace` | `"refs/ids/"` |
| `id_claim_repo` | `""` |
| `program_prefix` | `"PG"` |
| `slice_prefix` | `"SL"` |
| `capability_prefix` | `"CAP"` |
| `program_id_digits` | `2` |
| `slice_id_digits` | `3` |
| `capability_id_digits` | `4` |
| `component_id_pattern` | `"^[a-z0-9]+(-[a-z0-9]+)*$"` |
| `next_id_marker` | `'APPEND ONLY\. Next id:'` |
| `counter_pattern` | `'APPEND ONLY\. Next id:\s*…` in full below |
| `register_counter_id_pattern` | `'[A-Z]{2}-\d+'` |
| `prefixed_id_pattern` | `'^([A-Z]{2,5})-(\d{2,})$'` |
| `reserved_requirement_prefixes` | `["ENG"]` |
| `program_columns` | `["ID", "Name", "Kind", "Veri…` in full below |
| `slice_columns` | `["ID", "Name", "Kind", "Prog…` in full below |
| `disposition_ship_state_words` | `["active", "cancelled", "clo…` in full below |
| `program_kinds` | `["outcome", "program"]` |
| `slice_kinds` | `["capability", "feature", "gap-set"]` |
| `done_when_min` | `40` |
| `active_slice_ceiling` | `40` |
| `prd_statuses` | `["cancelled", "designed", "i…` in full below |
| `prd_terminal` | `["cancelled", "shipped"]` |
| `prd_order` | `["stub", "prd-drafted", "des…` in full below |
| `priorities` | `["high", "low", "medium", "urgent"]` |
| `priority_required` | `["designed", "implementing",…` in full below |
| `sections_required` | `["designed", "implementing",…` in full below |
| `required_prd_sections` | `["Vision Alignment", "Source…` in full below |
| `designed_or_beyond` | `["designed", "implementing",…` in full below |
| `lanes` | `[]` |
| `corpus` | `""` |
| `corpora` | `{}` |
| `verified_stampers` | `["verify"]` |
| `status_history_cutover` | `"2026-07-21"` |
| `risk_acceptance_stampers` | `["user"]` |
| `owner_acceptance_stampers` | `["owner-accepted"]` |
| `revert_target_states` | `["designed", "prd-drafted"]` |
| `revert_stampers` | `["design", "plan"]` |
| `canonical_differentiator_labels` | a table, in full below |
| `non_component_layers` | `[]` |
| `components_heading` | `"## Components"` |
| `proposed_components_heading` | `"## Proposed components"` |
| `outcomes_heading_prefix` | `"## Outcomes"` |
| `banned_component_column_pattern` | `'^\s*(status…` in full below |
| `decomposition_heading` | `"## Decomposition record"` |
| `plan_filename_pattern` | `'^(?P<fam>backend-plan…` in full below |
| `plan_cutover` | `"2026-07-21"` |
| `ux_design_file` | `"ux-design.md"` |
| `approved_design_heading` | `'^#+\s*Approved design\b'` |
| `additive_surface_pattern` | `'^#+\s*Surface scope:\s*addi…` in full below |
| `page_spec_pattern` | in full below |
| `browser_verification_token` | `""` |
| `commitments_section` | `"Commitments"` |
| `commitments_cutoff` | `"2026-08-14"` |
| `scope_ledger_section` | `"Scope ledger"` |
| `scope_ledger_cutoff` | `"2026-08-27"` |
| `ext_promotion_cutoff` | `"2026-09-10"` |
| `acceptance_section` | `"Acceptance criteria"` |
| `default_diff_base` | `"origin/main"` |
| `commitments_remediation` | `"\nThe design stage's commit…` in full below |
| `scope_ledger_remediation` | `"\nScope discipline says wha…` in full below |
| `plans_shallow_refusal` | `"PRD plan validation refused…` in full below |
| `clause_digest_slice` | `""` |
| `clause_digest_heading` | `'^##\s+Clause decomposition\b.*$'` |
| `clause_digest_heading_label` | `"## Clause decomposition"` |
| `clause_digest_marker` | `'<!--\s*done-cell-digest:\s*…` in full below |
| `clause_row_prefix` | `""` |
| `clause_required_ids` | `[]` |
| `commands` | `{}` |

The long defaults in full, as they would be written in the file:

```toml
[fleet.planning]
counter_pattern = 'APPEND ONLY\. Next id:\s*`?([A-Z]{2,5}-\d{2,})`?'
program_columns = ["ID", "Name", "Kind", "Verified by", "Requires", "Disposition"]
slice_columns = [
  "ID", "Name", "Kind", "Program", "Done when", "Verified by", "Depends on",
  "Components", "Disposition",
]
disposition_ship_state_words = [
  "active", "cancelled", "closed", "complete", "completed", "delivered",
  "done", "finished", "open", "shipped",
]
prd_statuses = [
  "cancelled", "designed", "implementing", "planned", "prd-drafted",
  "shipped", "stub", "verified",
]
prd_order = [
  "stub", "prd-drafted", "designed", "planned", "implementing", "verified",
  "shipped",
]
priority_required = ["designed", "implementing", "planned", "prd-drafted", "verified"]
sections_required = ["designed", "implementing", "planned", "verified"]
required_prd_sections = [
  "Vision Alignment", "Source Trace", "Value Justification",
  "Operational Resilience",
]
designed_or_beyond = ["designed", "implementing", "planned", "shipped", "verified"]
banned_component_column_pattern = '^\s*(status|state|shipped|progress|health|done)\s*$'
plan_filename_pattern = '^(?P<fam>backend-plan|frontend-plan)(?:-(?P<n>\d+))?\.md$'
additive_surface_pattern = '^#+\s*Surface scope:\s*additive to an existing surface\b'
page_spec_pattern = '`([^`\s]*/[^`\s]*\.spec\.md)`'
commitments_remediation = '''

The design stage's commitments step — reconciling the requirement register — is what
this section records, and the section is its only evidence. To clear:
  1. Run that step, then work the UNSATISFIED list: a need nothing is building is either
     an unscheduled gap or an edge into a mechanism this design's Non-Goals cut (the
     second wants a supersession).
  2. Write the `## {section}` section: the rows this design added or superseded, IDs
     only, plus the PRD's refreshed `implements:`.
  3. "none" is a legitimate outcome — but only written WITH the candidates examined. An
     empty statement is the un-backed conclusion that step exists to prevent.

A design authored before {cutoff} predates the step and is never flagged; if one here is
a genuine pre-rule artifact, move the cutoff rather than exempting the PRD.'''
scope_ledger_remediation = '''

Scope discipline says what may enter a PRD unasked, and this section is its only
evidence. To clear:
  1. Run the scope offer for the artifact — once at PRD authoring, once at design. ONE
     batched question over everything you withheld, no recommendation marked. A headless
     run makes no offer and takes nothing — it publishes the withheld list as a veto
     receipt and moves on.
  2. Write the `## {section}` section: one row per addition beyond the ask, ADMITTED AND
     WITHHELD ALIKE, with the Basis naming the acceptance criterion that cannot pass
     without it, or the already-edited file whose written-rule violation it fixes. An
     `admitted` row naming neither is a defect: an addition that traces to neither is
     scope nobody authorised.
  3. "none" is a legitimate and expected outcome — but written WITH what was considered.
     An empty section is not.
  4. Rows are ADDITIONS, never decisions. A ledger listing every design fork is the bloat
     this rule exists to stop and hides the rows that matter.

An artifact authored before {cutoff} predates the rule and is never flagged; if one here
is a genuine pre-rule artifact, move the cutoff rather than exempting the PRD.'''
plans_shallow_refusal = '''
PRD plan validation refused: this checkout is a shallow git clone.

Each plan is dated via `git log --diff-filter=A` to grandfather plans authored before
{cutover}. On a shallow clone that returns the shallow boundary commit as the add-date
for every file, so nothing is grandfathered and the entire legacy corpus is validated —
hundreds of phantom violations, none of them real.

Repair (additive — objects only, no working-tree change):
  git fetch --unshallow
'''
clause_digest_marker = '<!--\s*done-cell-digest:\s*sha256:([0-9a-f]{64})\s*-->'

[fleet.planning.canonical_differentiator_labels]
1 = "diff:1-runtime-substrate"
2 = "diff:2-path-aware"
3 = "diff:3-protocol-plural"
4 = "diff:4-ontology-as-contract"
5 = "diff:5-narrowing"
6 = "diff:6-customer-hosted"
7 = "diff:7-policy-near-data"
8 = "diff:8-actions"
9 = "diff:9-one-graph"
10 = "diff:10-compliance"
11 = "diff:11-evidence"
```

## `[fleet.commitments]`

How the requirement registers, the todo register and commitment coverage are read.

| Key | Default |
|---|---|
| `requirements_dir` | `"requirements"` |
| `todos_register` | `"todos.md"` |
| `prds_dir` | `"prds"` |
| `slices_register` | `"slices.md"` |
| `components_registry` | `"specs/architecture/components.md"` |
| `reserved_prefixes` | `["ENG"]` |
| `baseline_dir` | `"."` |
| `current_line` | `"v1"` |
| `register_baseline` | `"scripts/requirement_register.baseline"` |
| `append_order_baseline` | `[]` |
| `prd_file` | `"prd.md"` |
| `slice_id_prefix` | `"SL-"` |
| `slice_components_column` | `7` |
| `components_section` | `"## Components"` |
| `decisions_dir` | `"decisions"` |
| `append_only_marker` | `"APPEND ONLY. Next id:"` |
| `ac_coverage_enforced` | `["planned", "implementing",…` in full below |
| `claim_required` | `["designed", "planned", "imp…` in full below |
| `claim_presence_enforced` | `["designed", "planned", "implementing"]` |
| `claim_history` | `["cancelled"]` |
| `drift_advisory_only` | `["shipped"]` |
| `prd_order` | `["stub", "prd-drafted", "des…` in full below |
| `prd_cancelled` | `"cancelled"` |
| `prose_extra_dirs` | `[".claude", ".fleet"]` |
| `prose_extra_files` | `[]` |
| `prose_skip_dirs` | `["worktrees"]` |
| `prose_skip_top_dirs` | `["run"]` |
| `prose_skip_names` | `["prd.md"]` |
| `status_artifact` | `"requirement-status.md"` |
| `restatement_min_len` | `25` |
| `base_ref` | `"origin/main"` |
| `coverage_roots` | `["specs/", "decisions/"]` |
| `unclaimed_baseline` | `"requirements/UNCLAIMED.baseline"` |
| `excluded_types` | — |
| `todo_min_statement_len` | `25` |
| `issue_key_pattern` | `'\b[A-Z]{2,5}-\d{3,}\b'` |
| `cmd_validate_requirements` | `"python3 scripts/validate_re…` in full below |
| `cmd_validate_statements` | `"python3 scripts/validate_re…` in full below |
| `cmd_validate_coverage` | `"python3 scripts/validate_co…` in full below |
| `cmd_validate_todos` | `"python3 scripts/validate_todos.py"` |
| `cmd_validate_components` | `"scripts/validate_components.py"` |
| `cmd_component_of` | `"scripts/component_of.py"` |

The long defaults in full, as they would be written in the file:

```toml
[fleet.commitments]
ac_coverage_enforced = ["planned", "implementing", "verified", "shipped"]
claim_required = ["designed", "planned", "implementing", "verified", "shipped"]
prd_order = [
  "stub", "prd-drafted", "designed", "planned", "implementing", "verified",
  "shipped",
]
cmd_validate_requirements = "python3 scripts/validate_requirements.py"
cmd_validate_statements = "python3 scripts/validate_requirement_statements.py"
cmd_validate_coverage = "python3 scripts/validate_commitment_coverage.py"
```

## `[fleet.structure]`

Options of the structure checks: architecture docs, journeys, feature maps and file types.

| Key |
|---|
| `arch_component_tables` |
| `arch_details_dirname` |
| `arch_dir` |
| `arch_openapi_spec` |
| `arch_propagation_header` |
| `arch_registry_name` |
| `arch_specs_dir` |
| `capability_aliases` |
| `capability_id_digits` |
| `capability_prefix` |
| `components_registry` |
| `coverage_excluded_leaves` |
| `coverage_excluded_roots` |
| `coverage_excluded_segments` |
| `coverage_extra_pattern` |
| `coverage_extra_scan` |
| `coverage_generated_leaf_pattern` |
| `coverage_ledger` |
| `coverage_roots` |
| `feature_briefs_strict` |
| `feature_families` |
| `feature_family_min_members` |
| `feature_kind_default` |
| `feature_kinds` |
| `feature_tiers` |
| `features_dir` |
| `file_types_header_exts` |
| `file_types_registry` |
| `file_types_universal` |
| `hygiene_arch_audits_dir` |
| `hygiene_audits_dir` |
| `hygiene_date_triggers` |
| `hygiene_doc_parity` |
| `hygiene_drift_patterns` |
| `hygiene_drift_scope` |
| `hygiene_specs_index` |
| `hygiene_transient_fields` |
| `journeys_ac_heading_pattern` |
| `journeys_admin_routes` |
| `journeys_admin_routes_marker` |
| `journeys_banned_markers` |
| `journeys_base_ref` |
| `journeys_broad_source_root_pattern` |
| `journeys_deferral_cues` |
| `journeys_dir` |
| `journeys_dispositions` |
| `journeys_flows_subdir` |
| `journeys_frontend_scan_roots` |
| `journeys_frontend_scan_suffixes` |
| `journeys_maps_subdir` |
| `journeys_non_route_surfaces` |
| `journeys_org_route_prefix` |
| `journeys_permissions_contract` |
| `journeys_prd_lifecycle_states` |
| `journeys_prose_path_roots` |
| `journeys_redirect_elements` |
| `journeys_retire_ack_cues` |
| `journeys_retirement_markers` |
| `journeys_surface_skip_prefixes` |
| `journeys_unclaimed_baseline` |
| `journeys_web_routes` |
| `journeys_web_routes_marker` |
| `journeys_write_baseline_command` |
| `paths_generated_on_demand` |
| `paths_ignore_path_prefixes` |
| `paths_ignore_prefixes` |
| `paths_ignore_substrings` |
| `paths_knowledge_only_dirs` |
| `paths_knowledge_only_files` |
| `paths_knowledge_only_skip_target_dirs` |
| `paths_planned_dirs` |
| `paths_planned_files` |
| `paths_root_hints` |
| `paths_scan_suffixes` |
| `prds_dir` |
| `programs_register` |
| `specs_dir` |

## `[fleet.slots]`

Options of the slot registry check.

| Key |
|---|
| `commands_dir` |
| `registry` |

## `[fleet.recurring]`

Work Fleet files on a cadence for this repository, and the QA agent's nightly loop.

| Key |
|---|
| `entries` |
| `qa` |

Each item of `entries` takes these keys:

| Key | Values |
|---|---|
| `cadence` | `daily`, `weekly:<day>` or `biweekly:<day>`, where `<day>` is one of `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun` |
| `kind` | `audit`, `bug`, `cleanup`, `prd`, `task` |
| `name` | a name for the entry |
| `target` | optional: an area, a component or a repository, passed through as written |

## `[fleet.commands]`

How `fleet commands sync` writes the command tier into this repository.

| Key | What it sets |
|---|---|
| `layout` | Where the command tier is written. Only `plugin`, the `.fleet/` folder, is accepted. |
| `namespace` | The prefix this repository's commands are typed under, as in `/<namespace>:prd:create`. |
| `set` | `core` to receive only the core commands, or `all`, which is what leaving it out means. |

## `[fleet.setup]`

Setup files `fleet commands sync` leaves alone in this repository.

| Key | What it sets |
|---|---|
| `skip` | Setup files, such as the agent instructions file or the CI template, that `fleet commands sync` leaves alone. |

## `[fleet.session]`

What a worker runs before it opens a session for this repository.

| Key | What it sets |
|---|---|
| `setup` | A script in the repository that installs the extra tools the build needs, run before each session. |
| `timeout_seconds` | How long that script may run. |

## `[fleet.targets]`

The command each conventional target runs in this repository, which commands name instead of a literal `make` line.

| Target | What a command means by it |
|---|---|
| `lint` | the static checks a commit must pass |
| `lint-fix` | the mechanical auto-fixes, run before hand-fixing lints |
| `lint-ci` | the static checks CI runs, where they exceed lint |
| `typecheck` | the type checker over the whole tree |
| `build` | compile or bundle every artifact |
| `test` | every suite, the CI equivalent |
| `test-unit` | the fast unit lane, no services |
| `test-db` | the lane that needs a database up |
| `test-e2e` | the full-stack lane |
| `test-one` | one test by name (takes `T`) |
| `coverage` | the unit lane with the coverage gate |
| `pre-commit-dry` | the commit hooks over the working tree, writing nothing |
| `preflight` | the lane's fast mechanical guards, run before the first push — the same checks CI runs |
| `validate-knowledge` | the corpus validators (fleet check and the shipped validate scripts) |
| `generate` | regenerate everything derived from a source of truth |
| `generate-page-specs` | regenerate the surface specs' derived sections |
| `dev` | the full stack with hot reload, in the foreground |
| `dev-headless` | the full stack, backgrounded, for a browser pass |
| `dev-services` | only the backing services (a database, a queue) |
| `dev-stop` | stop whatever dev started |
| `seed` | seed the running stack |
| `reseed` | reset and seed the running stack |
| `agent-loop` | run a named agent loop (takes `LOOP`) |
| `agent-loop-install` | install a named agent loop's prompt (takes `LOOP`, `PROMPT`) |
