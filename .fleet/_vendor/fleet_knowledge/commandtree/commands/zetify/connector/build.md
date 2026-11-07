# Zetify Connector Builder

Build a new Zetify connector package — or extend an existing one — against the
Python connector SDK in `packages/connector-sdk/`. The command runs in two
strict phases:

1. **Phase 1 — Analysis Report.** Research the source system, propose a full
   design (entities, actions, auth, config, pagination, rate-limit, watermarks,
   error handling, tests), and STOP for user review.
2. **Phase 2 — Implementation.** Only after the user accepts (or amends) the
   plan, scaffold/extend the package, write code + tests, and validate.

The user invocation: `/zetify:connector:build <name> <link-or-description>`

  - `<name>` — short slug (lowercase, snake_case). Becomes `connector_<name>`.
    Example: `github`, `linear`, `pagerduty`.
  - `<link-or-description>` — URL to the source's API docs, or a free-form
    description of the source system + the entities/actions the user wants.

The user's input: $ARGUMENTS

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. `plan-approval` is a **human** gate: Phase 2 does not begin until the user replies `proceed`, and a model's own reading of the plan never substitutes for that reply. The prose steps below are the authority; this spine indexes them.

```json
{
  "command": "connector-build",
  "scope": "product",
  "owner": "zetify",
  "intent": "Build or extend one Python connector — analysis report, then implementation against the SDK — through local validation and the workspace gates a new connector must clear.",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "loads": ["languages", "runtime-contracts"],
  "requires": ["process-spine", "process-interview", "languages", "dev-environment", "runtime-contracts", "release-artifacts"],
  "optional": ["architecture", "file-conventions", "docs"],
  "steps": [
    {"id": "triage",          "name": "Triage — new package or update, and is this even a connector", "kind": "decision", "actor": "coordinator",                 "body": "phase-0-triage"},
    {"id": "analysis",        "name": "Analysis report in the locked structure",   "kind": "author",   "actor": "coordinator", "produces": ["reference"],          "body": "phase-1-analysis-report"},
    {"id": "plan-approval",   "name": "The USER replies `proceed` — Phase 2 starts on nothing else", "kind": "gate", "actor": "user", "gate": "hard",              "body": "phase-2-implementation"},
    {"id": "scaffold",        "name": "Scaffold or extend the package",            "kind": "io",       "actor": "coordinator",                                     "body": "step-1-scaffold-or-extend"},
    {"id": "schemas",         "name": "schemas.py — one pyarrow schema per entity and action", "kind": "author", "actor": "coordinator",                           "body": "step-2-schemas-py"},
    {"id": "transforms",      "name": "transforms.py",                             "kind": "author",   "actor": "coordinator",                                     "body": "step-3-transforms-py"},
    {"id": "connector",       "name": "connector.py",                              "kind": "author",   "actor": "coordinator",                                     "body": "step-4-connector-py"},
    {"id": "manifest",        "name": "manifest.py and manifest.yaml",             "kind": "author",   "actor": "coordinator",                                     "body": "step-5-manifest-py-and-manifest-yaml"},
    {"id": "ontology",        "name": "src/ontology.yaml (mandatory)",             "kind": "author",   "actor": "coordinator",                                     "body": "step-5b-src-ontology-yaml"},
    {"id": "exports",         "name": "__init__.py",                               "kind": "io",       "actor": "coordinator",                                     "body": "step-6-init-py"},
    {"id": "tests",           "name": "Tests — conformance, discover, read, actions, ontology", "kind": "author", "actor": "coordinator", "produces": ["tests"],   "body": "step-7-tests"},
    {"id": "validate-local",  "name": "Validate locally — manifest, bundle, pytest", "kind": "gate",   "actor": "coordinator", "gate": "hard",                     "body": "step-8-validate-locally"},
    {"id": "negative-control","name": "Negative control — plant a defect, assert each test goes red", "kind": "gate", "actor": "coordinator", "gate": "hard", "critique": "negative-control", "consumes": ["tests"], "body": "step-8b-negative-control"},
    {"id": "wire-workspace",  "name": "Wire into the workspace — the six gates outside the package", "kind": "gate", "actor": "coordinator", "gate": "hard",       "body": "step-9-wire-into-the-workspace"},
    {"id": "wrap-up",         "name": "Wrap up",                                   "kind": "io",       "actor": "coordinator",                                     "body": "step-10-wrap-up"}
  ]
}
```

---

## Context to load

- The Python connector SDK surface in `packages/connector-sdk/` and a gold-standard reference connector under `packages/connector-*/` (the canonical structure — read these in Phase 0).
- [`knowledge/specs/python-conventions.md`](../../../../knowledge/specs/python-conventions.md) — the import/dependency rules every `.py` file follows (Phase 2 code must obey these or `ruff` fails).
- [`knowledge/specs/data-plane-architecture.md`](../../../../knowledge/specs/data-plane-architecture.md) — how connectors, `connectord`, and the customer-network ingest path fit together.
- The docs home and page contract `slot:docs` names — the release-images page and the contract test pinned beside it live there (external gates 5–6). Resolve them **through the slot**, never as a literal path: the slot is what moves if the docs home moves, and when it is unfilled the connector's docs edit degrades to a note (the slot's degrade).

---

## CRITICAL RULES

1. **Two phases. Never write code before Phase 2 is unlocked.** End Phase 1
   with `AWAITING REVIEW —` and stop. Do not run any Edit/Write tool calls
   that produce package code until the user explicitly approves or amends.
2. **Use the toolkit.** Subclass `RESTConnector` (or `GraphQLConnector`).
   Do not hand-write `httpx` request loops, pagination, or auth headers
   unless the toolkit genuinely cannot express the source's behavior — and
   if so, justify it in the analysis. When you do write a custom request helper
   (e.g. a GraphQL page-walker), route **every** HTTP call through
   `self._send(client, req)` — it is the only authorised send path, the single
   place auth (`auth.apply`) and `RateLimitPolicy` backoff are applied. Calling
   `client.send()` / `client.get()` / any `client.*` method directly inside a read
   or write helper is a bug: requests ship with no `Authorization` header (→ 401)
   and no rate-limit pacing (→ 429). (ENG-1004) Mechanically enforced by
   `scripts/lint/no_bypass_send.py` (`make lint-connectors` / `make test-conformance`)
   — a justified bypass (e.g. an OAuth2 token-endpoint call) needs a
   `# bypass-send: <reason>` suppression comment, not a silent exception.
3. **Module-level imports only** (project-wide rule from `CLAUDE.md`). No
   `try/except` around imports. No function-level imports. Optional deps
   use `importlib.util.find_spec`.
4. **Both manifests are required.** `manifest.yaml` (runtime advertisement)
   AND `manifest.py` with a top-level `MANIFEST = Manifest(...)` (typed
   daemon enumeration). The two MUST agree on auth strategy, config keys,
   and capabilities.
5. **V1 FieldType set only.** Allowed: `STRING`, `INTEGER`, `NUMBER`,
   `BOOLEAN`, `ENUM`, `OBJECT` (with `nested_fields`), `ARRAY` (with
   primitive `item_type`). `MAP`, `oneOf`, regex, etc. are rejected at
   `ConfigField` construction — do not propose them.
6. **V2 taxonomy axes are mandatory.** Every `ManifestAttribute` must
   declare `data_nature`, `subject_class`, and `confidentiality`. Every
   `ManifestAction` must declare `external_effect`, `decision_class`, and
   `reversibility`. Fields with a personal-family `data_nature` also
   require `lawful_basis`. Omitting axes causes `validate_manifest()` to
   return errors, which will fail `test_ontology.py`.
7. **Tests are mandatory.** Every connector ships `test_conformance.py`
   (calls `assert_conformance()`), `test_discover.py`, `test_read_full.py`,
   and `test_ontology.py` at minimum. Tests use `LocalRunner` from
   `tilion_connector.testing` with its `http_handler` constructor kwarg —
   never patch `_client` directly.
8. **Connectors are stateless.** Watermarks, run state, retries,
   idempotency caches all live on the platform side. Do not propose any
   on-disk state, sqlite cache, etc.
9. **No platform-side code in this command.** This command builds the
   Python connector package only. It does NOT touch
   `internal/connectorhost`, `internal/connectorruntime`, the OpenAPI
   spec, or the **per-workspace ontology stored in Postgres** (the typed
   types/attrs/links/policies that workspace admins author via the API).
   If the source needs a new universal column or new persistence behavior,
   surface that in "Open questions" and stop — that is a separate
   platform change.

   The **connector-shipped ontology bundle** (`src/ontology.yaml`) IS in
   scope for this command and is **mandatory** — see rule #10. The bundle
   declares the default mapping from raw tables to ontology types/links/
   actions and is what the platform consumes (per PRD 0008) to seed a
   workspace ontology when an admin installs the integration. Without
   it, the connector ships data into `org_<uuid>.<table>` rows but
   nothing in the platform knows how to expose that data as types/links
   to agents, MCP, or the projection compiler.

10. **`src/ontology.yaml` is mandatory.** Every connector ships a v1.0
    typed ontology bundle declaring `types[]` (with `mapping.raw_table`
    and fully-classified `attributes[]`), `links[]` (FK mappings with
    `source_type`/`target_type` referencing either bundle types or
    canonical `core:*` types), and `actions[]` (mirrors of every
    `Action` declared in `connector.py`, with V2 axes). Path is
    `packages/connector-<name>/src/ontology.yaml` — both connectord
    (`internal/connectord/capabilities.go`) and the validators resolve to
    this path. Validated by both `go run ./cmd/connectorctl validate-pkg`
    and `uv run connector-cli validate-bundle` as part of Step 8 and
    `make lint-connectors` (already wired into pre-commit via
    `scripts/pre-commit-parallel.sh` whenever any
    `packages/connector-*/*` file changes).

    Canonical rules (mirror `internal/connectorvalidate/ontology_bundle.go`):
    - `version: "1.0"` exactly.
    - All `id` fields are `<connector_name>:<PascalCase>` (e.g.
      `fhir:Patient`, `github:GithubRepository`). Type / link / action
      IDs all share the same namespace, which must match the connector
      name in `manifest.yaml`.
    - `base_type_id` is optional, and **any canonical type in
      `contracts/packs/core.yaml` is valid** — `core:Person`,
      `core:Email`, `core:Account`, and every other type in the pack
      (`internal/connectorvalidate/ontology_bundle.go` derives its set
      from the pack; there is no smaller allowlist). Read the pack rather
      than a copied subset, and omit `base_type_id` when none fit.
    - Every type needs `mapping.raw_table`, `description`, ≥1
      attribute, and ≥1 attribute with `is_identifier: true`.
    - Attribute `datatype` is one of `string | int | bool | timestamp |
      float | json | vector`. Use `int` (not `bigint`) for 64-bit ints.
    - **Attribute names MUST NOT collide with the reserved universal
      columns** — the eight `_`-prefixed columns `connectorhost` injects
      into every per-org raw table: `_source`, `_source_id`,
      `_integration_id`, `_ingestion_run`, `_first_seen_run`,
      `_ingested_at`, `_deleted_at`, `_content_hash`. `id` is NOT among
      them — it is a legal connector attribute, and a source system that
      exposes a natural `id` should declare it as `id` (M013 and U005
      reserve only the `_`-prefixed set). The identifier's name must agree
      with the Arrow schema (`schemas.py`), the manifest.yaml entity
      attribute list, and the `Entity.primary_key` tuple in `connector.py`.
    - Personal-family `data_nature` (`personal`, `sensitive_personal`,
      `medical_record`, `criminal_history`, `child_data`) requires
      `lawful_basis`. Conversely `lawful_basis` set with no
      personal-family signal is rejected (rule O005).
    - `sensitive_subtype` is only valid when `data_nature ==
      sensitive_personal` (rule E41).
    - Links use `source_type` / `target_type` (no `_id` suffix);
      `kind: fk` requires `mapping.source_column` +
      `mapping.target_column`.
    - Legacy `type_mappings:` / `link_mappings:` arrays are rejected —
      mappings are inline on each type/link.

    See `packages/connector-github/src/ontology.yaml`,
    `packages/connector-vercel/src/ontology.yaml`, and
    `packages/connector-github/src/ontology.yaml` for canonical examples.

---

## Phase 0 — Triage (≤30 seconds, silent)

Before producing the report:

1. **Resolve `<name>`** to `packages/connector-<name>/`. If the directory
   exists, this is an **UPDATE** to an existing connector — read its
   current `connector.py`, `manifest.py`, and `manifest.yaml` so the
   report can frame the work as a delta.
2. **Read the gold-standard reference**: `packages/connector-github/`
   (`connector.py`, `schemas.py`, `transforms.py`, `manifest.py`,
   `manifest.yaml`, `tests/test_github_connector.py`). Mirror its
   structure unless there's a concrete reason to deviate.
3. **Read the SDK surface** to know what the toolkit gives you for free:
   - `packages/connector-sdk/src/tilion_connector/toolkit/__init__.py`
   - `packages/connector-sdk/src/tilion_connector/toolkit/rest.py`
   - `packages/connector-sdk/src/tilion_connector/toolkit/auth.py`
   - `packages/connector-sdk/src/tilion_connector/toolkit/paginators.py`
   - `packages/connector-sdk/src/tilion_connector/manifest.py` — includes `ManifestAttribute`, `ManifestAction`, `Postcondition`, `validate_manifest()`
   - `packages/connector-sdk/src/tilion_connector/types.py`
4. **If `<link-or-description>` is a URL**, fetch the docs index and skim
   the auth, pagination, rate-limit, and resource list pages. If multiple
   pages are needed, run those fetches in parallel.
5. **Detect existing similar connectors** so reusable patterns surface.
   Quick `ls packages/connector-*/src/connector_*/connector.py`.

---

## Phase 1 — Analysis Report (LOCKED STRUCTURE)

Output the report exactly in this structure. Section headers and order
are fixed so the user can scan it predictably across runs.

````markdown
# Connector plan — `<name>` (<vNEW | vN.M → vN.M+1>)

**Mode:** <NEW package | UPDATE existing>
**Source:** <product name + 1-line description>
**Reference docs:** <URL(s) consulted>
**Closest in-tree analogue:** packages/connector-<other> (why)

---

## 1. Source overview

- **API style:** <REST | GraphQL | hybrid>
- **Base URL:** `<https://api.example.com>`
- **Versioning:** <header / path / none>
- **Public docs quality:** <good | sparse | undocumented quirks: ...>
- **Notable quirks:** <enveloped responses, weird 200-with-error bodies,
  undocumented rate limits, etc.>

## 2. Authentication

- **`AuthStrategy`:** <NONE | API_KEY | OAUTH2 | BASIC>
- **Toolkit class:** <NoAuth | BearerToken | APIKeyHeader | BasicAuth>
- **Secret name(s):** `<name>_token` (or named explicitly)
- **Header injection:** `Authorization: Bearer ...` | `<X-API-Key>: ...` | ...
- **Scopes/permissions required on the source side:** <list>
- **Refresh / rotation behavior:** <none required by SDK | OAuth refresh
  is platform-side, not connector-side>
- **Auth-failure surface:** how the source signals invalid creds
  (401 vs. 403 vs. 200-with-error-body) and how `configure()` should
  validate at install time.

## 3. Configuration

| Field | Type (`FieldType`) | Required | Secret | Default | Notes |
|-------|-------------------|----------|--------|---------|-------|
| `org` | STRING | yes | no | — | GitHub org slug |
| `<api_token>` | STRING | yes | yes | — | source bearer token |
| ... | ... | ... | ... | ... | ... |

- **Validation hooks in `configure()`:** <list missing-config / cross-field rules>
- **`manifest.py` MANIFEST snapshot:** include the full `MANIFEST = Manifest(...)`
  block here so the user can review it verbatim.
- **`manifest.yaml` snapshot:** include the full YAML manifest body here.

## 4. Entities (the "types")

For each entity:

### `<EntityName>`

- **HTTP path:** `/v1/...` (`{var}` placeholders if sub-stream)
- **Method:** `GET`
- **Paginator:** <SinglePagePaginator | LinkHeaderPaginator |
  CursorPaginator(...) | OffsetPaginator | PageNumberPaginator>
- **Primary key:** `(id,)` (or composite, e.g. `(repo_full_name, sha)`)
- **Parent:** `<None | OtherEntity>`
- **`parent_extract`:** which fields the parent row contributes to the
  child path (only when parent is set)
- **Watermark field:** `<updated_at | None>` — and the `since_to_params`
  logic ("watermark `cursor.updated_at` → `?since=<iso>`")
- **Error handlers:** <e.g. `{404: SKIP, 409: SKIP}` — explain why each
  status is skip-and-warn rather than raise>
- **Schema (Arrow):**

  | Field | pyarrow type | Nullable | Source field | Notes |
  |-------|--------------|----------|--------------|-------|
  | `id` | `int64` | no | `id` | natural key |
  | `name` | `string` | yes | `name` | |
  | `created_at` | `timestamp("us", tz="UTC")` | yes | `created_at` | parsed via `_to_ts` |
  | ... | ... | ... | ... | ... |

- **Transform notes:** any non-trivial mapping (envelope unwrapping,
  list-of-objects → JSON string column, parent stamping, etc.)

Repeat for every entity. Group root entities first, then sub-streams,
then sub-sub-streams (depth ≥ 3 is allowed but call it out).

## 5. Actions

For each action:

### `<action_name>` → `<ENTITY>`

- **Target entity:** `<EntityRef>` and **`target_id` format**
  (e.g. `"<owner>/<repo>#<number>"` for a PR)
- **HTTP:** `<METHOD>` `<path-template>` (path callable signature)
- **Idempotent:** <true | false> — explain (e.g. `add_comment` is NOT
  idempotent because each call creates a new comment; the runtime caches
  results for non-idempotent actions to short-circuit retries)
- **`affects`:** `(EntityRef(...), ...)` — which entities go stale after
  a successful execution
- **Parameters schema (Arrow):** field list + types
- **`required_parameters`:** `(...)`
- **`validate_local`:** what cheap, side-effect-free checks run before
  the HTTP call (e.g. parse `target_id`)
- **`body` builder:** what the HTTP body looks like
- **Response handling:** default JSON parse | custom `parse_response` |
  full `interpret_response` (for 200-with-`{ok:false}` sources)
- **`parse_validation_errors`:** how 4xx response bodies map to
  `ValidationIssue`s

## 6. Taxonomy / Classification (V2 axes)

> These metadata labels live in `manifest.py` on `ManifestAttribute` and
> `ManifestAction` objects. They are mandatory for every shipped attribute
> and action — omitting them will fail `validate_manifest()`.

### Attributes

| Attribute | `data_nature` | `subject_class` | `confidentiality` | `lawful_basis` (required if personal family) |
|-----------|--------------|-----------------|-------------------|----------------------------------------------|
| `id` | non_personal | not_applicable | internal | — |
| `email` | personal | individual | confidential | legitimate_interest |
| ... | ... | ... | ... | ... |

### Actions

| Action | `external_effect` | `decision_class` | `recipient_class` | `sector` | `reversibility` |
|--------|------------------|-----------------|------------------|----------|----------------|
| `create_issue` | creates_record | informed_decision | internal | technology | reversible |
| ... | ... | ... | ... | ... | ... |

- **Validation rule E41:** `sensitive_subtype` must be empty unless `data_nature == "sensitive_personal"`.
- **Validation rule E42:** `lawful_basis` is required when `data_nature` ∈ {personal, sensitive_personal, medical_record, criminal_history, child_data}.
- If a field is clearly non-personal (IDs, timestamps, boolean flags) leave `data_nature: non_personal` and omit `lawful_basis`.

## 7. Ontology bundle (`src/ontology.yaml`)

> Mandatory. The connector ships a v2 typed ontology bundle that the
> platform consumes (PRD 0008) to seed a workspace ontology when the
> integration is installed. This section is the **full content** of the
> bundle to be written in Step 7b, not "candidate notes for later". Look
> at `packages/connector-github/src/ontology.yaml` and
> `packages/connector-vercel/src/ontology.yaml` for canonical shape.

### 7a. Types

For each entity from §4, declare an ontology type. Type IDs are
namespaced as `<connector_name>:<PascalCase>` (matching `manifest.yaml`'s
`name:` field, e.g. `fhir:Patient`, `github:GithubRepository`). Use a
`base_type_id` ONLY when the type naturally specializes a canonical
type from `contracts/packs/core.yaml`. **Any canonical type in that pack
is valid** — `core:Person`, `core:Email`, `core:Account`, `core:Service`,
and the rest; read the pack rather than a copied subset. Leave
`base_type_id` unset when none fit.

**The natural resource id MAY be named `id`** — `id` is NOT a reserved
universal column; `connectorhost` injects only the eight `_`-prefixed
columns. Declare a source-system `id` as-is rather than renaming it to
`fhir_id`/`github_id`. Whatever name you use must agree with the Arrow
schema in `schemas.py`, the manifest.yaml entity attribute list, and
the `Entity.primary_key` tuple.

```yaml
- id: <connector_name>:<PascalCase>
  name: <Human Name>
  description: <one sentence>
  base_type_id: <any type id from contracts/packs/core.yaml — omit if none fit>
  mapping:
    raw_table: <raw_table_name from §4>
  attributes:
    - name: <column_name>      # MUST NOT be _source/_source_id/... (`id` is allowed)
      datatype: <string | int | bool | timestamp | float | json | vector>
      is_required: <true | false>
      is_identifier: <true for PK | omit>
      description: <one sentence — required, non-empty>
      raw_column: <raw column if different from name; omit if same>
      data_nature: <axis value — must match §6>
      confidentiality: <axis value — must match §6>
      subject_class: <axis value — must match §6>
      lawful_basis: <only when data_nature ∈ personal-family — must match §6>
```

Every attribute's classification axes MUST match the values declared in
§6 — `validate_manifest()` and `validate-bundle` cross-check them.

### 7b. Links

For each ontology link, declare a typed FK. Source/target columns are
real columns in the raw rows (not `id` references unless that's the
real key).

```yaml
- id: <ns>:<PascalCaseLinkName>
  display_name: <Human Name>
  source_type: <ns>:<SourceType>
  target_type: <ns>:<TargetType>
  kind: fk
  cardinality: <one_to_many | many_to_one | one_to_one>
  mapping:
    source_column: <column on source raw table>
    target_column: <column on target raw table — usually the PK column>
  description: <one sentence>
```

Populate one row per relationship from the catalogue below:

| From entity | Field | To entity | Cardinality | Source of truth |
|-------------|-------|-----------|-------------|-----------------|
| Commit | `repo_full_name` | Repository | many-to-one | natural key |
| PullRequest | `repo_full_name` | Repository | many-to-one | natural key |
| PullRequestReview | `pull_request_id` | PullRequest | many-to-one | int FK |
| ... | ... | ... | ... | ... |

### 7c. Actions

Mirror every `Action` from §5 with full V2 axes. Omit this section
entirely (or use `actions: []`) when the connector is read-only.

```yaml
- id: <ns>:<PascalCaseAction>
  action_ref: <module.submodule.handler_name>
  target_type: <ns>:<TargetType>
  default_autonomy: <require_approval | autonomous>
  idempotency_key: "<template with {target.x} and {args.y}>"
  external_effect: <axis>
  decision_class: <axis>
  recipient_class: <axis>
  sector: <axis>
  reversibility: <axis>
  description: <one paragraph — what it does, reversibility, side effects>
  input_schema:
    <arg>:
      type: <text | integer | bool>
      description: <one sentence>
      optional: <true if optional>
      enum: [...] (if enumerated)
  postconditions:
    - kind: <creates | modifies | deletes>
      resource: <ns.resource_name>
  audit:
    retain_input: true
    pii_attributes: []
```

## 8. Pagination strategy

- **Default per-page size:** <100 | source's max>
- **Per-entity overrides:** <none | list>
- **Termination signal:** Link header `rel=next` | cursor `pagination.next`
  null | empty page | total-count comparison
- **Edge cases:** <empty pages mid-sequence, 422 on huge offsets, etc.>

## 9. Rate limiting

- **Source headers:** `<X-RateLimit-Remaining / X-RateLimit-Reset>`
- **`RateLimitPolicy(...)`:** exact dataclass init the connector will use
- **Threshold rationale:** why this number (e.g. "100 leaves a cushion
  for nested sub-streams that issue many requests sequentially")
- **429 handling:** Retry-After honored by the policy; no per-entity
  retry loop in the connector.

## 10. Watermarks & incremental

| Entity | `watermark_field` | `since_to_params` | Incremental supported? |
|--------|-------------------|-------------------|------------------------|
| Repository | `updated_at` | `?since=<iso>` | yes |
| Issue | `updated_at` | `?since=<iso>` | yes |
| Branch | — | — | full-sync only (no source-side delta) |
| ... | ... | ... | ... |

- **Initial-run behavior:** the SDK passes a zero-value watermark on
  first read; either map that to "no `since=` param" (full pull) or
  reject and require a backfill window — state which.

## 11. Error handling

- **Per-entity `error_handlers`:** which status codes are SKIP vs RAISE,
  and why (e.g. "404 on `/repos/{r}/actions/workflows` for repos that
  don't have Actions enabled — skip and warn").
- **Auth errors:** 401 always raises (re-enrollment needed); 403 is
  source-specific.
- **Body-encoded errors (200-with-`{ok:false}`):** which actions need
  `interpret_response` to translate to `ActionResult.ok = false`.

## 12. Test plan

Mirror the reference connector test layout (one file per concern):

| File | Contents |
|------|----------|
| `test_conformance.py` | `assert_conformance(connector, config={...}, secrets={...})` — **mandatory, always present** |
| `test_discover.py` | Entity refs appear in `discover()`; `get_schema()` returns correct primary key + field types; no duplicates |
| `test_read_full.py` | Full-sync read per entity via `LocalRunner(..., http_handler=...)`: row count, field values, no watermark param emitted |
| `test_read_incremental.py` | Incremental entities: watermark cursor → `since=` query param; multi-page flow; `initial_watermark()` returns zero-value cursor |
| `test_actions.py` | Happy-path execute → `ActionResult.ok=True`; `validate_local` rejection without HTTP; `parse_validation_errors` on 4xx |
| `test_<name>_transforms.py` | Pure-function unit tests for any transform helper with non-trivial logic (optional, add when `transforms.py` has edge-case logic) |
| `test_ontology.py` | `validate_manifest()` returns no errors; `ManifestAttribute`/`ManifestAction` axes satisfy E41/E42 rules; `validate_ontology_bundle_dict(yaml.safe_load(open("src/ontology.yaml")))` returns no errors |

Per-entity requirements:

- **Discover test:** entity ref appears in `runner.discover()`.
- **Schema test:** primary key fields + a representative field present in `EntitySchema`.
- **Read test:** 1–2-page fixture, assert row count + transformed field values.
- **Pagination test:** at least one entity exercises multi-page Link/cursor flow.
- **Error-handler test:** at least one SKIP status code exercised.
- **`configure()` test:** missing required secret → `missing_secret` issue; missing config field → `missing_config` issue.

## 13. Files to create / modify

```
packages/connector-<name>/
  pyproject.toml                              [create | unchanged]
  manifest.yaml                               [create | UPDATE]
  src/
    ontology.yaml                             [create | UPDATE]  ← mandatory (PRD 0008)
  src/connector_<name>/
    __init__.py                               [create | unchanged]
    manifest.py                               [create | UPDATE]
    schemas.py                                [create | UPDATE]
    transforms.py                             [create | UPDATE]
    connector.py                              [create | UPDATE]
  tests/
    __init__.py                               [create | unchanged]
    test_conformance.py                       [create | UPDATE]  ← mandatory
    test_discover.py                          [create | UPDATE]
    test_read_full.py                         [create | UPDATE]
    test_read_incremental.py                  [create] (only if incremental entities exist)
    test_actions.py                           [create] (only if actions exist)
    test_ontology.py                          [create | UPDATE]  ← validate_manifest() AND validate_ontology_bundle_dict()
    test_<name>_transforms.py                 [create] (optional, non-trivial transform logic)
```

Workspace-level edits (only when adding a NEW package) — every row is
required; the six external gates are invisible to the package's own tests
(see Phase 2 Step 9 for the exact shape + enforcing symbol of each):

```
pyproject.toml                                          [UPDATE]  #0 workspace member + uv.sources
.github/workflows/ci.yml                                [UPDATE]  #1 publish-connectors matrix row
.github/workflows/publish.yml                           [UPDATE]  #2 publish-connectors matrix row (+ imageRef)
internal/rawstoreredact/token_coverage_test.go          [UPDATE]  #3 connectorTokenShapes entry (secret-bearing only)
internal/rawstoreredact/rawstoreredact.go                [UPDATE]  #4 RawStoreTablePrefixRE / RawStoreTableExactRE
the release-images page in the docs home `slot:docs` names  [UPDATE]  #5 docker pull line + prose connector count
the doc test pinned beside it                            [UPDATE]  #6 require.Len(t, matches, N) bump
```

No install-stub YAML to write anywhere — a `connectors-installed/<name>.yaml`
would be read by nothing. An integration is installed through the platform
(see Phase 2 Step 9, "Local install path").

## 14. Open questions / risks

- <List anything the user must answer before Phase 2, e.g. "source's
  rate limit is undocumented — propose threshold = 50 RPS as a guess">
- <List items that need a separate platform-side change and therefore
  fall outside this command>

---

**AWAITING REVIEW — reply `proceed` to start Phase 2, or list amendments
(e.g. "drop the `Issue` entity", "use `cursor.created_at` instead of
`updated_at` for `WorkflowRun`", "add an `assign_pr` action").**
````

Stop here. Do not start any Edit/Write of package files yet.

The review block above is a question to a human, and the open items in it are forks —
so it is written to the interview card: plain words, one concrete example of what the
connector will do for somebody, and every open item stated with the options and what
each costs, never as a bare "needs a decision":

<!-- include: process/interview-card.md -->

---

## Phase 2 — Implementation (only after user approval)

Once the user replies with `proceed` (or amendments — apply them, then
proceed), execute these steps in order. Use TaskCreate to track them so
progress is visible.

### Step 1 — Scaffold or extend

- **NEW connector:** run
  ```
  uv run connector-cli new --name <name> --kind rest
  ```
  (or `--kind graphql`). This creates the directory layout + stub files.
- **UPDATE connector:** skip scaffolding; edit existing files in place.

### Step 2 — `schemas.py`

- One `pyarrow.schema(...)` per entity, named `<ENTITY>_SCHEMA` in
  `SCREAMING_SNAKE`.
- One `pyarrow.schema(...)` per action's parameters, named
  `<ACTION>_PARAMS`.
- Use `pa.timestamp("us", tz="UTC")` for all timestamp fields.
- Mark natural-key fields `nullable=False`.
- **`id` is a legal column name** — it is NOT a reserved universal column;
  connectorhost injects only the eight `_`-prefixed columns. Declare the
  natural source resource id as `id` when that is the source's own name,
  and rename it only when the source calls it something else. The
  identifier's name must appear in `manifest.yaml`'s `source_id_field`,
  `manifest.py`'s `ATTRIBUTES` list, `Entity.primary_key`, and
  `ontology.yaml`'s `attributes[].name` for the identifier.
- Keep all schema definitions in this file — do not inline them in
  `connector.py`.

### Step 3 — `transforms.py`

- One pure function per entity: `<entity>_row(raw, *parent_keys) -> dict`.
- Pure: no I/O, no logging, no global state. Receives the raw JSON dict
  + parent-derived keys; returns a dict matching the Arrow schema field
  order.
- Date parsing helpers (e.g. `_to_ts(s)`) live here.
- Action `target_id` parsers (e.g. `parse_pr_target`) live here too.

### Step 4 — `connector.py`

- Subclass `RESTConnector` (or `GraphQLConnector`).
- Class attrs: `name`, `version`, `base_url`, `auth`, `rate_limit` (if
  any), `supported_predicate_ops`.
- `entities = [Entity(...), ...]` — declarative list per the report.
- `actions = [Action(...), ...]` — declarative list per the report.
- Override `configure(self, config)` only for cross-field validation
  beyond the manifest's `required` markers.
- Override `read()` ONLY when a sub-stream needs parent-vars injection
  the SDK doesn't already provide (the GitHub connector's `_read_team`
  is the canonical example — replicate that pattern when needed).
- Bottom of file: `connector = <ClassName>Connector()`.

### Step 5 — `manifest.py` and `manifest.yaml`

- `manifest.py` — `MANIFEST = Manifest(...)` matching exactly the
  spec from the report's section 3. Make sure
  `manifest.py.MANIFEST.config_fields` and `manifest.yaml.config` agree
  on field names, types, and `required` lists — drift here will surface
  as confusing "field missing" errors at install time on the daemon.
- `manifest.yaml` — capabilities list, auth strategies, JSON-Schema
  config, predicate_ops, rate_limits.

### Step 5b — `src/ontology.yaml` (mandatory)

Write the connector-shipped ontology bundle exactly per §7 of the
Phase 1 report. Three sections:

- `types[]` — one entry per Entity from §4. `mapping.raw_table` matches
  the entity name; `attributes[]` carry full V2 classification axes
  matching §6. Use `base_type_id` only when the type naturally
  specializes a canonical type from `contracts/packs/core.yaml` (any
  canonical type in that pack is valid) — leave unset otherwise.
- `links[]` — one entry per relationship from §7b. FK kind, real source
  and target columns (typically the parent's PK column), explicit
  cardinality.
- `actions[]` — mirror every `Action` from §5/`connector.py` with
  `external_effect`, `decision_class`, `recipient_class`, `sector`,
  `reversibility`, `input_schema`, `postconditions`, and `audit`.
  Read-only connectors: write `actions: []` (or omit the key).

The bundle is what the platform (per PRD 0008) reads at integration
install time to seed the workspace ontology — so the type/link/action
identifiers chosen here become the ontology surface that agents, MCP
tools, and the projection compiler see. Pick stable, descriptive IDs.

### Step 6 — `__init__.py`

- Single line: `from connector_<name>.connector import connector` plus
  `__all__ = ["connector"]`. Do not export the class — the daemon
  enumerates instances.

### Step 7 — Tests

Mirror the reference connector (`connector-github`) test layout:

- `test_conformance.py` — **mandatory**. Call `assert_conformance(connector, config={...}, secrets={...})` from `tilion_connector.conformance`. This is the baseline gate; if it fails, nothing else matters.
- `test_discover.py` — entity refs, schema fields, primary keys, no duplicates.
- `test_read_full.py` — one test per entity using `LocalRunner(connector, ..., http_handler=handler)`. Assert row count + field values.
- `test_read_incremental.py` — one test per incremental entity; assert watermark cursor → `since=` param. Skip file if no incremental entities.
- `test_actions.py` — happy-path execute + `validate_local` rejection per action. Skip file if no actions.
- `test_ontology.py` — call `validate_manifest(attributes=[...], actions=[...])` and assert empty error list.
- `test_<name>_transforms.py` (optional) — pure-function unit tests for helpers with non-trivial logic.

Mock pattern (always use this — pass `http_handler` into `LocalRunner`, never patch `_client` directly):

```python
import httpx
from tilion_connector.testing import LocalRunner

def handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=[...], headers={...})

runner = LocalRunner(
    <Class>Connector(),
    config={...},
    secrets={...},
    http_handler=handler,
)
rows = runner.read_rows("<EntityName>")
result = runner.execute_action("<action_name>", target_id="...", input={...})
```

### Step 8 — Validate locally

Run, in order, and surface output:

```
uv run connector-cli validate-manifest packages/connector-<name>/manifest.yaml
uv run connector-cli validate-bundle packages/connector-<name>
uv sync --all-packages
uv run pytest packages/connector-<name>
```

`validate-bundle` walks `src/ontology.yaml` and reports unknown
`base_type_id`s, link target types that aren't declared, missing
classification axes, and other structural errors. Fix violations
before pytest — they will also block install on the daemon.

Also confirm programmatic manifest validation passes (this is what `test_ontology.py` exercises — run it explicitly if any classification axes were added or changed):

```python
from tilion_connector.manifest import validate_manifest
from connector_<name>.manifest import MANIFEST

errors = validate_manifest(
    attributes=MANIFEST.attributes,
    actions=MANIFEST.actions,
)
assert errors == [], errors
```

If `pytest` fails: fix the connector or the test, do NOT loosen assertions to make them pass.

### Step 8b — Negative control (prove the tests can fail)

**A green suite proves nothing until you have watched it go red.** Every test written in
Step 7 was written by the same session that wrote the code it checks, which is the exact
arrangement that produced ENG-6199 — a guard that *assigned* the value it was meant to
verify, so planting the defect left it green, and nothing caught it because the only party
who could run this check was the party who wrote both halves.

So plant a defect and assert the test notices. Four, one per class of thing a connector
gets wrong, each reverted immediately:

| Break this | Then this must go red |
|---|---|
| a field mapping in `transforms.py` (return a constant, drop a key) | `test_read_full.py` |
| a `nullable=False` natural-key field in `schemas.py`, or rename a column | `test_discover.py` |
| the `since=` watermark param (emit nothing, or a fixed value) | `test_read_incremental.py` |
| a required entry in `MANIFEST.attributes` / `actions` | `test_ontology.py` |

```bash
# One at a time. Edit, run the ONE named test, assert failure, restore, assert restored.
uv run pytest packages/connector-<name>/tests/test_read_full.py   # MUST fail
git checkout -- packages/connector-<name>/src                     # restore, always
git diff --quiet && echo "tree restored"                          # assert it
```

**A test that stays green with its subject broken is not a test — it is a description of
one.** Fix it before Step 9; a connector whose suite cannot fail ships a source of truth
nobody is checking, and the failure surfaces as wrong customer data months later. Skipping
a row because "that entity has no incremental mode" is fine and expected — say so; skipping
one because it is inconvenient is the defect this step exists to catch.

Restore the tree even when a run errors out.

### Step 9 — Wire into the workspace (NEW connectors only)

A new connector is **not** done when its package tests pass. Six gates
outside the package fire on every new connector; four of them live entirely
outside `packages/connector-*` (release workflows, a docs contract test, a
pre-commit hook) and are invisible to `pytest packages/connector-<name>` and
`make lint-connectors`. Hit every row below **before** opening the PR —
each was discovered one CI cycle at a time on PR #9842
(`packages/connector-happy_buttons`) because Step 9 used to stop at the
workspace member.

There is no install-stub YAML to write — a `connectors-installed/<name>.yaml`
file would be read by nothing (that mechanism was removed in 2026-05; the
platform DB is the single source of installed integrations). Installation
goes through the platform (see the bottom of this step).

#### Workspace + six external gates

| # | What to edit | Exact shape | Enforced by |
|---|--------------|-------------|-------------|
| 0 | root `pyproject.toml` | add `packages/connector-<name>` to `[tool.uv.workspace] members` (and `[tool.uv.sources]` the way `connector-github` is registered). Then `uv sync --all-packages`. | workspace resolution; gates 1–2 derive their "surviving connector" set directly from this list (`survivingConnectorModules` reads these members). Gates 5–6 do **not** read it — they derive their set from publish.yml's `imageRef:` lines, which is the same set only transitively, because gates 1–2 force every member into that matrix |
| 1 | `.github/workflows/ci.yml` → `publish-connectors` matrix | one `include:` row: `image: zetify-connector-<name>`, `dockerfile: packages/connector-image/Dockerfile`, `buildArg: CONNECTOR_MODULE=connector_<name>` | `TestJointGate_BakeAbsenceAndDigestCompleteness_RUN717` in `internal/connectorruntime/runner/bake_absence_test.go` |
| 2 | `.github/workflows/publish.yml` → `publish-connectors` matrix | the **same** row shape **plus** `imageRef: ghcr.io/zetifyai/zetify-connector-<name>` — the `v*` release lane a self-installed operator pulls from is a different channel from the trunk lane; both must list the connector | **Lead:** `TestJointGate_BakeAbsenceAndDigestCompleteness_RUN717` in `internal/connectorruntime/runner/bake_absence_test.go` (its publish.yml half) — that is the gate that goes red when this row is missing ("surviving connector module %q … must have a zetify-connector- row in publish.yml's publish-connectors job"). `TestReleaseOrder_PublishConnectorsBeforeDaemon_RUN1162` in `internal/connectorruntime/runner/release_order_test.go` reads `ci.yml` only — it enforces this row's ci.yml twin and the publish-daemon ordering, not this file. Neither gate asserts the connector row's `imageRef:` key (RUN717's publish.yml half reads it only to locate the daemon row for the ordering assertion); a row missing `imageRef:` surfaces instead as row 6's `require.Len` count mismatch plus the doc-join requiring every `imageRef:` to appear in the release doc |
| 3 | `internal/rawstoreredact/token_coverage_test.go` → `connectorTokenShapes` | **only if** `manifest.yaml` declares any `format: secret` config field. Add a map entry keyed by the manifest's top-level `name:` that pins an example token value and claims the redaction net that catches it (`netPrefix` / `netAssignment` / residual). A prefix-shaped token also needs its prefix on `credentialTokenRE`. Skip for secret-free fixtures. | `TestConnectorTokenCoverage_DerivedFromConnectorManifests` in the same file |
| 4 | `internal/rawstoreredact/rawstoreredact.go` → `RawStoreTablePrefixRE` (or `RawStoreTableExactRE`) | the connector's **entity table namespace(s)** — the prefix of every `entities[].name` in `manifest.yaml`, which often differs from the connector id (e.g. `imap_email` → `email_`, `m365` → `m365_` but also `sharepoint_`/`onedrive_` for `sharepoint_file`/`onedrive_file`). Add the prefix to the regex alternation, or the full singleton name to `RawStoreTableExactRE` when the first token is too generic to prefix-match. Without this, a non-canonical pg error naming the raw table leaks to the LLM. | `TestRawStorePrefixCoverage_DerivedFromConnectorManifests` in `internal/errsanitize/manifest_coverage_test.go` |
| 5 | the **release-images page** in the docs home `slot:docs` names | (a) one `docker pull ghcr.io/zetifyai/zetify-connector-<name>:vX` line next to the other connector pulls (tag = the doc's current-release marker); (b) bump the prose counts that name the connector set — today the family bullet ("the N connector images") and the credential section ("twenty-N release packages" = 5 core + N connectors). Copy the existing connector-pull lines for shape. Resolve the page's home **through `slot:docs`**, never as a literal path — the slot is what moves if the docs home moves. | `validate-release-contract` pre-commit hook (`scripts/ci/validate_release_contract.py`) — **not** a CI lane; it fires on commit |
| 6 | the **doc test pinned beside the release-images page** (`slot:docs` names the docs home; the test lives with it) → `publishMatrixImageRefs` | bump the hardcoded `require.Len(t, matches, N)` on publish.yml's `imageRef` count by 1, and update the failure-message comment that enumerates the set. The pull-line count in `TestObtainingReleaseImages_Contract` is already derived from publish.yml; the imageRef ceiling is not. | `TestObtainingReleaseImages_Contract` in the same file |

**How to verify the six without waiting on CI:**

```
go test ./internal/connectorruntime/runner/ -run 'TestJointGate_BakeAbsence|TestReleaseOrder_PublishConnectors'
go test ./internal/rawstoreredact/ -run TestConnectorTokenCoverage_DerivedFromConnectorManifests
go test ./internal/errsanitize/ -run TestRawStorePrefixCoverage_DerivedFromConnectorManifests
go test ./docs/ -run TestObtainingReleaseImages_Contract
python3 scripts/ci/validate_release_contract.py
```

Only gates 3 and 4 are reachable from the connector package's own tests
(they derive their requirement set from `packages/connector-*/manifest.yaml`).
Gates 1, 2, 5, 6 live entirely outside the package — nothing in
`pytest packages/connector-<name>` or `make lint-connectors` points at them.

**Count-based failure messages are a trap.** Gates 5 and 6 fail with an
arithmetic complaint ("should have 24 item(s), but has 25" / "the N connector
images") rather than naming the connector. When you see a bare count
mismatch after adding a connector, the missing edit is almost always this
step's rows 5–6 — work backwards from the number to the connector you just
added, not the other way around.

#### Local install path (after the gates above)

- With the dev stack up (`{{target:dev}}` + `make dev-connectord`), the daemon
  enumerates every connector package in the workspace venv at startup and
  advertises it to the platform on connect; `GET /api/connectors/catalog`
  lists what the org's connectord knows about (start/restart the daemon
  after `uv sync` so the new package is picked up).
- Install with `POST /api/integrations` — the web UI's connection flow
  issues the same call: `{connectorId, version, config}`. Config is
  validated against the manifest schema, and secret-flagged fields are
  stored in the vault (`internal/vault`, AES-GCM at rest) — secrets are
  supplied in the API call, never in a file. The platform pushes the
  install to connectord over the channel, which spawns the worker by
  module name.
- Demo bundles install the same REST-only way via `demoseed apply`.

### Step 10 — Wrap up

- Print a summary: files added/modified, test count, any deferred TODOs
  from "Open questions" that still apply.
- Do NOT commit. The user runs `/zetify:push` when they're ready (it commits, then opens a PR).

---

## Reference: SDK building blocks (cheat sheet)

| Need | Use |
|------|-----|
| No auth | `NoAuth()` |
| Bearer token | `BearerToken(secret_name="<name>_token")` |
| Header API key | `APIKeyHeader(header="X-API-Key", secret_name="<name>_key")` |
| Basic auth | `BasicAuth(username_secret=..., password_secret=...)` |
| Single-page response | `SinglePagePaginator()` |
| GitHub-style Link header | `LinkHeaderPaginator()` |
| Cursor in body | `CursorPaginator(body_key="pagination.next", param_name="cursor", page_size=100, page_size_param="limit")` |
| Offset/limit | `OffsetPaginator(...)` |
| `?page=1, ?page=2` | `PageNumberPaginator(...)` |
| Rate limit headers | `RateLimitPolicy(remaining_header=..., reset_header=..., retry_after_header=..., threshold=N)` |
| Skip 404 sub-streams | `error_handlers={404: ErrorAction.SKIP}` |
| Sub-stream of parent | `parent="ParentName", parent_extract=lambda row: {...}` |
| Incremental `since=` | `watermark_field="updated_at", since_to_params=lambda wm: {"since": wm.cursor["updated_at"]}` |
| Partition by field | `partition_keys=("repo_full_name",)` on Entity |
| Dynamic base params | `base_params_factory=lambda config: {"org": config["org"]}` on Entity (use over `base_params` when value comes from config) |
| 200-with-`{ok:false}` | custom `interpret_response=...` on the action |
| Cheap pre-flight check | `validate_local=lambda req: [...]` returning `ValidationIssue`s |

**Capability protocols** (use `isinstance` checks in capability tests):

| Protocol | Key methods added |
|----------|------------------|
| `Discoverable` | `discover()`, `get_schema()` |
| `FullReader` | `read()`, `supported_predicates()` |
| `IncrementalReader` | extends `FullReader` + `initial_watermark(entity)` |
| `ActionExecutor` | `list_actions()`, `validate()`, `execute()` |
| `WebhookHandler` | `handle_webhook(headers, body)` |

`RESTConnector` implements all protocols its `entities`/`actions` lists imply — declare only capabilities you actually ship.

---

## Tone

- Phase 1 is an architectural review, not a sales pitch. Be specific
  about tradeoffs (sub-stream depth vs. rate-budget; full-sync entities
  vs. incremental).
- When the source's docs are ambiguous or missing, say so in
  "Open questions" rather than guessing into code.
- When a request would expand the platform contract (new universal
  column, new capability, persistence change), STOP and surface it —
  do not silently adapt the connector to a half-supported behavior.
