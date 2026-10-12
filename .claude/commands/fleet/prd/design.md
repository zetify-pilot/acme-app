#  Design

A comprehensive feature design workflow that produces both technical design and (optionally) UX design, grounded in an existing PRD. The user provides a PRD number or feature description. Before producing any design, engage in a thorough discovery conversation. Only after confirmation, produce the structured design document.

> **You can hand this back to the fleet at any point.** Designing by hand is not a one-way
> door: once the PRD's program is driven, the fleet runs [`prd:blueprint`](blueprint.md) on a
> drafted PRD whose prerequisites have shipped — this same design, asked through the PRD's
> page — and picks up from whatever is committed: the journey, the page-specs, a `design.md`
> already on `main`. Take it yourself when the forks need you in the room, and leave it to the
> fleet when they do not.

---

## Command spine (machine-readable)

> **Runtime contract** ([`spine.md`](../../../process/spine.md)): at start, read the `steps` block below and create **one todo per step**, in order; mark each `in_progress` on entry and `completed` on exit. A failed `gate` or exhausted `loop` stays open with its residual noted — never silently closed. The prose phases below are the authority; this spine indexes them.

```json
{
  "command": "prd-design",
  "tier": "core",
  "intent": "Technical + UX design grounded in a PRD; produces design.md (+ optional ux-design.md).",
  "sop": "none",
  "needs": "answers",
  "may merge": false,
  "loads": ["product-vision", "ui-contracts", "architecture", "process-design-fidelity"],
  "requires": [
    "process-spine", "process-interview", "planning-model", "file-conventions", "commitments",
    "architecture", "gate", "codegen",
    "rubric-architecture-red-team", "process-design-fidelity", "languages", "git-workflow",
    "journeys"
  ],
  "optional": [
    "product-vision", "ui-contracts", "domain-model", "api-contract", "resilience", "entity-model",
    "feature-maps", "decisions", "components", "slices", "permissions", "runtime-contracts",
    "process-envelope", "docs"
  ],
  "steps": [
    {"id": "load-context",      "name": "Load context",                     "kind": "author", "actor": "coordinator", "consumes": ["prd"],                      "body": "phase-0-load-context"},
    {"id": "journeys-specs",    "name": "Journeys & page-specs",            "kind": "gate",   "actor": "coordinator", "gate": "hard", "produces": ["page-spec", "journey"], "body": "journeys-page-specs"},
    {"id": "mockup-fidelity",   "name": "Reference + iterate mockup to the bar", "kind": "loop", "actor": "coordinator", "critique": "design-fidelity-bar", "loop": {"max_rounds": 3, "exit": "mockup clears the design-fidelity bar"}, "produces": ["reference", "mockup"], "body": "browser-mockups"},
    {"id": "mockup-lock",       "name": "Promote chosen round to a real-UI fixture page", "kind": "io", "actor": "coordinator", "produces": ["mockup", "screenshots"], "body": "promote-the-chosen-round"},
    {"id": "mockup-approval",   "name": "Human approves the mockup",         "kind": "gate", "actor": "user", "gate": "hard", "produces": ["mockup-approved"], "body": "human-approval-gate"},
    {"id": "discovery",         "name": "Discovery conversation",           "kind": "author", "actor": "coordinator", "consumes": ["prd"],                      "body": "discovery-conversation"},
    {"id": "arch-audit",        "name": "Architecture audit",               "kind": "gate",   "actor": "coordinator", "gate": "hard",                           "body": "architecture-audit"},
    {"id": "integration-trace", "name": "Integration reality check",        "kind": "gate",   "actor": "coordinator", "gate": "hard",                           "body": "integration-reality-check"},
    {"id": "technical-design",  "name": "Technical design",                 "kind": "author", "actor": "coordinator",                                           "body": "technical-design"},
    {"id": "ux-design",         "name": "UX design (opt-in)",               "kind": "author", "actor": "coordinator", "produces": ["ux-design", "reference"],   "body": "ux-design-opt-in"},
    {"id": "red-team-critique", "name": "Independent design critic panel",  "kind": "fanout", "actor": "subagent",    "model": "opus",                          "body": "dispatch-the-critic-panel"},
    {"id": "red-team-gate",     "name": "Disposition red-team findings",    "kind": "gate",   "actor": "coordinator", "gate": "hard", "critique": "architecture-red-team", "body": "disposition-each-finding"},
    {"id": "reuse-analysis",    "name": "Reuse analysis",                   "kind": "author", "actor": "coordinator",                                           "body": "reuse-analysis"},
    {"id": "gaps-improvements", "name": "Gaps & improvements",              "kind": "author", "actor": "coordinator",                                           "body": "gaps-improvements"},
    {"id": "commitments",       "name": "Reconcile the requirement register","kind": "io",    "actor": "coordinator", "consumes": ["requirement-register"], "produces": ["requirement-register"], "body": "phase-4c-commitments"},
    {"id": "cross-repo-scope",  "name": "Cross-repo scope check",           "kind": "gate",   "actor": "coordinator", "gate": "hard",                           "body": "phase-4-5-cross-repo-scope-check-mandatory-do-not-skip"},
    {"id": "impl-order",        "name": "Implementation order",             "kind": "author", "actor": "coordinator",                                           "body": "implementation-order"},
    {"id": "scope-offer",       "name": "Scope offer — withheld additions, once",  "kind": "gate",   "actor": "user",        "gate": "hard",                           "body": "scope-offer"},
    {"id": "envelope",          "name": "Envelope — fits one merge, or split", "kind": "gate",  "actor": "coordinator", "gate": "hard",                           "body": "phase-5-5-the-envelope-one-prd-must-fit-in-one-merge-hard-gate"},
    {"id": "output",            "name": "Write design.md",                  "kind": "io",     "actor": "coordinator", "produces": ["design"],                   "body": "phase-6-output"},
    {"id": "journey-coverage",  "name": "Journey & capability coverage",    "kind": "gate",   "actor": "coordinator", "gate": "hard", "produces": ["journey", "feature-map"], "body": "journey-capability-coverage"},
    {"id": "flip-status",       "name": "Flip PRD status to designed",      "kind": "io",     "actor": "coordinator", "produces": ["status"],   "body": "flip-prd-status"},
    {"id": "dispatch-plan",     "name": "Dispatch prd:plan without blocking", "kind": "fanout", "actor": "subagent",   "model": "opus", "produces": ["backend-plan", "frontend-plan"], "body": "phase-8-dispatch-the-plan-do-not-stop-and-wait"}
  ]
}
```

---

## CRITICAL RULES

**Unconfirmed assumptions are assumptions to confirm, not facts.** A PRD's `## Unconfirmed
assumptions` section lists what its interview could not settle because the owner marked a question
*"I can't answer this"* and the run carried on ([`interview-protocol`](../../../process/interview.md)
→ *"I can't answer this"*). Never cite one as a decision, never promote one into an acceptance
criterion or a requirement row on your own authority, and when a design choice turns on one, put
that question to the person who can answer it — the reporter included — before building on it.

1. **Read the PRD first.** This command requires an existing PRD. If none exists, tell the user to run `/fleet:prd:create` first.
2. **Read the product vision.** Check `` for persona and principle alignment.
3. **Discovery before design.** Do NOT skip Phase 1. Do NOT produce the design document until the user confirms the summary.
4. **No code.** This command produces design documents, not implementation.
4a. **The Phase 2c critic panel is dispatched as sub-agents via the `Agent` tool — your own reasoning never satisfies it.** The spine declares that step `kind: fanout`, `actor: subagent`, and the point is **independence**, not parallelism: the reviewer must not have authored the design under review, which you cannot supply about your own work at any level of effort. If you cannot spawn — the harness forbids it, or a **session-level instruction conflicts** — the step **FAILS**: leave its todo open, report that the panel did not run, and do **not** write a self-review into *Architecture notes* as though it had. **Disclosing a substitution is not performing the step**, and a disclosed weak check silently downgrades every gate downstream that was entitled to assume an independent one ran. Same standard as Rule 4b: a gate is cleared by the mechanism it names, or it is open. Authority: [`spine.md`](../../../process/spine.md) → *"`actor: subagent` means a real sub-agent"*.
4b. **A UI mockup is approved ONLY by an explicit `AskUserQuestion` answer — NEVER by a prose reply.** Every UI mockup MUST be sent to the human for approval as a structured question with explicit options (*approve* / *request changes*) **that carries the mockup itself: the fleet's `ask` tool with the mockup attached** (interview.md → *A mockup reaches a person ONE way* — never a file path, `http.server` or `localhost`, which the person cannot open). `AskUserQuestion` takes the answer only once the fleet viewer link is in the question. A chat message — "ok", "yes", "sure", "go ahead", "continue", a thumbs-up, or any approval buried inside a paragraph — does **NOT** count and MUST NEVER be treated as sign-off. Until an `AskUserQuestion` answer approving the mockup is on record, the mockup gate is **OPEN** and the design is **BLOCKED**: you may not finalize the design, flip `status:`, or open a PR. This is because a question buried in prose does not reliably reach the human — only a structured question does, and only the fleet's ask puts the mockup in front of them. See **Step 0c**, which this rule makes non-negotiable.
5. **UX design is mandatory for any customer-facing capability — think UX-first.** 's value is what a user can *see, drive, and understand* through the product, not the substrate beneath. If a customer or operator ever touches this capability, you MUST produce the UX design — do **not** ask whether it's "needed," and never defer the surface as "backend now, UI later." Skip the UX design *only* for genuinely backend-only / internal-plumbing work with no human user; when in doubt, it has a user. The surface that lets someone leverage the capability is part of the deliverable.
5b. **Journeys & page-specs before architecture.** Start from the PRD's **agreed journey** (read + update the journey files it cites), turn each surface that journey touches into an authored/refreshed `<Page>.spec.md`, and only THEN answer data-model / layer / architecture questions. Design and requirements are *derived from* the journey and the page it lives on — never the reverse. See **Phase 0.5**.
6. **Clean architecture is the default — and so is fixing it, without asking.** If you encounter ANY architectural quirk, smell, inconsistency, leaky abstraction, or pattern that contradicts CLAUDE.md / the specs in `knowledge/specs/` while studying the affected layers, you MUST explicitly call it out in Phase 1.5 and disposition it there. **`fix` is the default and you take it yourself** — asking permission to follow a rule we already wrote down is the thing CLAUDE.md's golden rule forbids. `defer` is yours to choose too, but only with a tracked issue minted in the same run. Only **`perpetuate`** — a conscious decision to keep carrying debt — and any finding that would change a `**[XXX-NNN]**` promise reach a human. Never silently inherit a quirk into the new design, and never silently *widen* one either: a proposed deviation that adds or alters a commitment is scope, and scope is escalated (Phase 1.5 Step 3).
6b. **Craft is yours; scope is the human's — and Rule 6 above is a *craft* licence.** Rule 6 lets you fix a quirk without asking; Rule 8 lets you adopt the state of the art without asking. **Neither is a licence to decide what gets built.** A *craft* call is how well the asked-for thing gets built (which mechanism, which error envelope, which existing helper, how deep the tests go) — yours, always, and interviewing about one is the deferral CLAUDE.md forbids. A *scope* call is what will **exist** when this PRD ships that would not otherwise — a surface, a control, a setting, a table, an event, a permission, a flag, a new abstraction, or a cleanup in code this PRD does not otherwise touch — and that is the human's, always. An addition enters this design unasked only when **a PRD acceptance criterion cannot pass without it** (not "is better with" — *cannot pass*), or when it is a **written-rule violation in a file this design already has open**. Everything else is **withheld** — not adopted, not filed as a ticket, not argued for — and offered to the human **exactly once**, as one batched multi-select, in **Phase 5.4**. Every addition, admitted and withheld alike, lands in the `## Scope ledger` (Phase 6), which `make validate-knowledge` blocks the commit over. Rules 6 and 2c's adopt-defaults are bounded by this rule, not the reverse. One authority: [`tracking-and-execution.md`](#) → *Scope discipline*.
6c. **Before designing a mechanism, price it — the PRD's own scope is not exempt.** Rule 6b polices additions to the design; it assumes the PRD's requirements are worth building. Sometimes they are not, and design is the last cheap place to find out. So in discovery, for the central mechanism and for every requirement that carries real cost: **what breaks if we do not build it**, and **how often does it actually fire** — bounded concretely, from the code, not from the PRD's prose. A mechanism whose live window turns out to be narrow and whose absence nobody has noticed is one to say so about **before** designing it, not after. **If the answer is that it is not worth building, say that and stop** — reporting "this PRD's scope does not survive the necessity test, here is why" is a successful design run, not a failed one, and it is far cheaper than a design that survives its own red team. **Inheritance is provenance, not justification:** a requirement moved here from a stub, a split or a predecessor takes the same test. Authority: [`tracking-and-execution.md`](#) → *The necessity test*.
7. **Argue for the best design, not the proposed one** (truth-seeking golden rule). Discovery exists to find the strongest technical solution, not to ratify the approach the user walked in with. Challenge weak assumptions, surface better alternatives with the reasoning that beats the option on the table, and when a choice trades correctness or durability for speed, name that tradeoff out loud instead of letting the easy path pass as the default. Concede fast when the user's call is the right one.
7b. **Prose may not assert a commitment — it cites one** (CLAUDE.md golden rule). **Design is where a new commitment is actually born**: the PRD claimed what already existed, and then this command settles the forks the PRD left open. Every *"the system shall / never"*, ceiling, knowingly-accepted cost, and refused option this design produces is **one row in a requirement register**, cited from the design by ID — and a design that cuts a mechanism moves the rows describing it, with the closure that entails. That is **Phase 4c**, and it runs before the design is written out so `design.md` cites rows rather than restating them.
8. **Industry best practice is the default — do it right, no hacks** (CLAUDE.md golden rule). Before resolving any design dimension, establish the **state-of-the-art / best-practice** approach for the mechanism it turns on (Phase 1 **Step 0-pre**) and adopt it **by default, without asking** — the standard is the best technical solution, never the easiest or the fastest to unblock. A hack / stopgap / "bridge for now" is never the default; if one is taken under a real constraint, name it as debt with the best-practice path it displaces. **Only deviate — and only after surfacing why — when our case is genuinely special** (governance-in-the-data-path, the customer-network data plane, an existing load-bearing invariant). Do **not** interview the user to ask permission to follow the standard; interview only to choose between genuinely-competing best-practice options, or to confirm a special-case deviation. A proven in-repo precedent is best-practice evidence — a new surface matches how the nearest analogous thing is already done well (e.g. connectors package as sealed `uv` projects), it does not invent a lesser path.

---

## Phase 0: Load Context

1. Parse the argument: $ARGUMENTS — this should be a PRD number (e.g., "0003") or a feature description.
2. If it's a number, read `knowledge/prds/NNNN-*/prd.md`. If not found, tell the user to create it first with `/fleet:prd:create`.
3. If it's a description, search `knowledge/prds/*/prd.md` for a match. If no match, suggest `/fleet:prd:create` first.
4. Read `` for context.
5. Check if a `design.md` already exists in the PRD directory. If so, inform the user and use `AskUserQuestion` to ask if they want to revise it or start fresh.
6. **Read the PRD's `## Open decisions` section — it was written *for you*, and until now nothing read it.** 41 PRDs carry that section; the string appeared **zero** times in this command. A handoff nobody receives is not a handoff, and the cost is that design re-derives (or re-asks) forks the PRD author already argued.

   Each entry normally arrives already shaped as an answer: an option marked **(Recommended)**, a *why*, and a *cost* — the [`interview-protocol.md`](../../../process/interview.md) shape. So **the recommendation is the default and you take it without asking.** CLAUDE.md's golden rule is explicit that you never interview the user for permission to follow the standard; a fork already argued on the record, with the cost stated, is settled unless you find something that was not known when it was written.

   Disposition **every** entry, in the design's `## Open decisions — dispositioned` section, as exactly one of:

   | | When | Human? |
   |---|---|---|
   | **Adopt** | the recommendation still holds — the normal case | no |
   | **Deviate** | your Step 0-pre best-practice pass, the architecture audit, or the critic panel produced evidence the author did not have. Name the evidence | no — but say it out loud in the design |
   | **Escalate** | choosing between the options would **add or change a promise** — a new `**[XXX-NNN]**` row, or settling one the register still calls `open`. That is scope, and scope is the human's | **yes** — `AskUserQuestion`, and the answer lands in the **register row**, not only here |

   **A PRD with no `## Open decisions` section** (older format — 0438 and 0442 among them) does not get a free pass: enumerate the forks *you* face, write them into that section of the PRD in the same shape, and disposition them with the same three outcomes. Never silently invent an answer to a fork the PRD never named.
7. **Tell the fleet you are designing this PRD — before any other work.** If the fleet session tools are connected (the `hold_planning` tool), call `hold_planning(prd="NNNN", step="design", where="<your branch>")`. Without it the fleet may auto-start its own design of the same PRD under a driven program and later write it over yours — measured on PRD 0817 (), where your branch reached GitHub 77 minutes after the fleet's run began, so nothing else could have told it. The hold lapses by itself when the PRD's status moves. A refusal or a missing tool is not a blocker: say so in one line and continue. If you abandon the design, call it again with `release=true`.

---

## Phase 0.5: Journeys & Page-Specs (MANDATORY — before the design questions)

Design owns the customer's end-to-end experience, so it starts by re-grounding in the
**agreed journey** the PRD carries and turning each surface that journey touches into a
concrete **page-spec** — *before* any data-model / layer / architecture question. Design
and requirements are derived from the journey and the page it lives on, never the reverse.

1. **Read the PRD's journey files.** The PRD (via `create` Phase 0.7) cites journey ID(s)
   in `knowledge/journeys/`. Read each (`flows/<id>.md` / `maps/<id>.md`). Confirm the
   journey still holds for the design you're about to do; if the design surfaces a change
   to the flow (a new step, a re-ordered surface, a split), **update the journey file in
   place** — it is a living doc, not write-once. If the PRD carries no journey (an older
   PRD), enumerate + agree one now per `create` Phase 0.7 before continuing.
2. **Build / confirm the screen inventory.** Every backbone step maps to a surface — list
   them. For each: an **existing page** (refresh its spec) or a **new page** (author one)?
   A journey step with no surface is a gap to resolve here, not in implementation.
3. **Author / refresh each `<Page>.spec.md`.** For every surface in the inventory, produce
   or update the page-spec next to `<Page>.tsx` using the `` discipline
   (load ``, `frontend-implementation-contract.md`, and
   ``): `Purpose` (the job step it serves) · `Data sources`
   · `Layout (top → bottom)` · **`Canonical-choice rules`** (intent → `@/ui` component
   bindings) · **`States`** (empty / loading / error / success, each with copy + actions) ·
   `UX decisions (do not silently regress)` · `i18n` · key `data-testid`s. **READ an existing
   spec and refresh it — never overwrite authored intent.** New pages get a new spec; run
   `make generate-page-specs` to populate the conformance block. When a genuinely visual
   question arises, mock it in the browser with real tokens (Phase 1 Step 0) — the mockup
   informs the spec; the spec is the durable artifact.
4. **Only now proceed to Phase 1** (understanding) and the layer / architecture design.
   Every design decision and acceptance criterion must trace to a journey step + its
   page-spec.
5. **Docs impact (`slot:docs`) — resolve the PRD's seeded block into a designed section.**
   The PRD arrives with `docs_impact` (from `create.md` Phase 0.7); here it becomes the
   design's **`## Docs impact`** section. For every capability an acceptance criterion commits,
   name the **pages created or changed**, each by **page id and home via `slot:docs`** (never a
   literal path), with its **audience**, its **page kind** per the slot's page contract, and the
   **journey** that will verify the page. (Design owns the *pages*; `prd:plan` turns each page
   id into a task and `prd:implement` writes it.)
   - A page an AC needs a customer to be able to **follow** is **required**, and is **admitted**
     in the `## Scope ledger` with its basis (the AC / capability it documents).
   - A page beyond that (extra depth, a spin-off how-to nobody's AC needs) is **withheld** —
     never adopted here — and offered **exactly once** at **Phase 5.4**, then recorded
     `withheld` in the ledger if declined.
   - A page the `docs` slot marks **generated** is produced by the generated-reference target
     the slot names, never hand-authored.
   - `docs_impact: none` for an internal capability stands; a customer-facing one still owes a
     page (or the reason it does not).

**Guardrail:** the *journey-shape* agreement is a *guideline gate, not a rigid
stage-gate* — "the journey and the surfaces it touches are agreed and spec'd enough to
design against", not "every pixel final". But do not answer data-model / API / layer
questions until the journey + its page-specs are on the table; that ordering is the
whole point. (Phase 6.5 already requires journey/capability coverage at output time —
this pulls the same discipline to the *front*, where it shapes the design instead of
validating it after the fact.)

**One thing here is NOT a guideline — it's a hard deliverable:** for every *new or
materially-changed* UI surface, the design must land (a) a **named high-craft
reference** and (b) a **mockup that clears the design-fidelity bar** (Phase 1 Step 0 +
[`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §1–§2).
"Functional but looks bad" is a design failure before it is an implementation failure —
a surface whose approved mockup doesn't clear the bar hands the `implement` build loop
(§3) a target it can't hit, and the badness ships. Set the ceiling here.

---

## Phase 1: Discovery conversation (MANDATORY — do NOT skip)

**Do NOT proceed to Phase 2 until the user explicitly confirms the summary is correct.**

### Step 0-pre: Establish the best-practice baseline (MANDATORY — before any dimension)

Before framing dimensions or asking anything, establish **how the industry solves this class of problem well today** — the state-of-the-art / best practice for the mechanism the design turns on (packaging, auth, transport, storage, migration, SDK delivery, dependency resolution, isolation, whatever it is). Use the `deep-research` skill and read comparable systems; and **check how *this* codebase already does the nearest analogous thing** — a proven in-repo pattern is the strongest best-practice evidence (e.g. connectors already ship as sealed `uv` projects; a new Python surface matches that, it does not hand-roll a lesser path). Write a short **Best-practice baseline** note: the standard approach, ≥1 concrete reference (a named product/system or an in-repo precedent), and why it is the standard.

**This baseline is the default the design adopts — you do NOT ask the user whether to follow best practice.** Surface a fork to the user only when (a) two best-practice-grade options genuinely compete, or (b) our situation is **special** — a real, stated reason the standard is wrong *for us* (governance-in-the-data-path, the customer-network data plane, an existing load-bearing invariant) — in which case present the deviation and its reason for an explicit call. A design that departs from the established best practice **without a special-case reason on the record is a design bug** — the same standard as a Phase 1.5 "perpetuate." Record the baseline in `design.md` → **Architecture notes**, and let it drive the red-team's R5 ("is there a materially stronger alternative"). If the best practice implies substrate that does not exist yet, that is a **Gap / dependency** (Phase 4a) — never a reason to hack around it in this design.

### Step 0: Browser mockups in real app styling (default-on for UI work)

If the design touches the Web UI layer (2.11) or involves visual workflows / page layouts — and *only* then — **produce real browser-rendered mockups in the existing app styling whenever a question is genuinely visual.** Do NOT ask the user whether to use mockups; they have already opted in for all UI PRDs. Skip mockups when the design is backend-only or the question is text-shaped (data-model decisions, scope refinements, permission choices).

Per question, decide `would the user understand this better seeing it than reading it?` Use the browser for layouts, wireframes, side-by-side visual designs, mockup comparisons. Use the terminal for conceptual choices, scope refinements, data model decisions, configuration options, anything text-shaped. A question about the UI layer is *not* automatically a visual question — "should we use a tab or a drawer here?" benefits from a sketch; "what permission gates this view?" does not.

**THE MOCKUP IS A FILE IN THE REPO. A published artifact/link is a viewer, never the mockup** ([`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §1.5-0). Every mockup is committed as local, self-contained HTML/CSS under `knowledge/prds/NNNN-<slug>/mockups/` **before or with** any publish. Publishing a hosted copy (a `claude.ai/code/artifact/…` URL) so the human can actually look at it is encouraged and is its *only* legitimate use. **The reason is hard: the agents that plan, implement and verify this PRD run headless with the repo and nothing else — they cannot open your link.** A fidelity target that is a URL is a target no implementer can read, so it either gets ignored (and the mockup did no work) or parks the run. Therefore: **every citation of a mockup — in `ux-design.md`, `frontend-plan.md`, an acceptance criterion, a page-spec — is a repo-relative path.** A URL may sit beside it for the human; never instead of it. Never leave a mockup in a scratchpad directory.

**Styling discipline (load-bearing) — same rules as `/fleet:prd:create` Phase 1 Step 0.1:**

0. **Anchor to a high-craft reference FIRST — beat the mean** ([`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §1). A mockup built only from our own tokens has our own average taste as its ceiling, and an LLM left to defaults regresses to the training-set mean (generic cards, no density decisions, no finish). Before drawing, **name ≥1 concrete high-craft reference** — a real rendered surface of the *same archetype* (list / detail / settings / cockpit) from a product with strong craft (Linear, Vercel, Stripe, Height, or an internal exemplar page that already clears the bar) that we'd be proud to be mistaken for. Save it as `knowledge/prds/NNNN-<slug>/mockups/reference-<archetype>.png` with a one-line note on *what* about it is the target (density / rhythm / restraint / hierarchy). **This is the only PNG that belongs in `mockups/`** — it is an external surface nothing in this repo can regenerate, which is exactly why it is committed while round renders are not (§1.5-0d). The reference sets the craft **ceiling**; the tokens/components below supply the **parts** — it is not license to leave the design system. Every mockup round is measured against this reference *and* the design-fidelity bar (§2).
1. **Read the token file `slot:ui-contracts` names** (single source of truth for color, light + dark, brand, status, badge, sidebar tokens) **at the moment you write the mockup, and copy what is actually there.** Do not reproduce token values from memory, from an older PRD's mockup, or from this document — the file has changed color space before (older mockups still carry stale values under comments claiming they are verbatim). A hand-copied token is a frozen snapshot and is the reason Explore-tier mockups are throwaway.
2. **Read the type-scale and radius tokens the same slot names.**
3. **Match the existing app's mode posture** as `slot:ui-contracts` describes it. Mirror whichever mode the user is currently working in if known; otherwise default to the app's default with a small preview of the other.
4. **Reuse real component shapes.** Read 1–2 existing relevant components from `slot:ui-contracts` and reuse their structure (eyebrow + title pattern, pill shape, actor-tone color convention) instead of inventing parallel shapes.
5. **System font stack only**, unless the app already loads custom fonts. No Google Fonts `@import` in the mockup if the app doesn't ship them.
6. **Brand color is whatever the tokens say.** No bespoke accents unless a product-specific tokenised color exists for the affordance.

Save Explore-tier mockups under `knowledge/prds/NNNN-<slug>/mockups/round-NN-<theme>/index.html`. Each new round must continue to use real tokens — don't backslide into bespoke styling. **The chosen mockup is a real deliverable, not a sketch: it must clear the design-fidelity bar** ([`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §2 — reference fidelity, the `Q1–Q6` information-design rubric, surface hierarchy, one primary action, scale discipline, and the holistic "would a designer ship this?"). A mockup that doesn't clear the bar under-specifies the surface and will cost rounds in the `implement` build loop (§3) — resolve it here, where it's cheap.

Cap the Explore tier at **3 rounds**. If three rounds haven't converged on a direction, the problem is the brief, not the pixels — go back to the discovery questions.

If the design is backend-only (no Web UI layer touched), skip this step and Steps 0b/0c entirely and proceed to Step 1.

### Step 0b: Promote the chosen round

**The round you converge on MUST be promoted to the Lock tier before design completes** ([`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §1.5a): a **real React fixture page** on an `import.meta.env.DEV` route inside `AppShell`, built from real `@/ui` components and the real `tokens.css` — not an HTML file.

This is not ceremony. An HTML mockup can't be clicked, can't surface a real component's constraints, and its tokens are a copy that rots. The Lock tier is the version you can actually challenge, and it is what every downstream stage binds to.

Follow the existing pattern — both halves already ship, do not reinvent them:

1. **Fixture page** — `frontend/apps/web/src/pages/dev/Dev<Thing>Page.tsx`, real `@/ui` imports, fixture data inlined, every state addressable by a URL param (`?state=empty`) so the approval screenshots can be captured deterministically.
2. **Route** — a `import.meta.env.DEV`-gated entry in ``, as a child of the `AppShell` route block so it inherits the real sidebar + header. **`React.lazy` the component** — a static import keeps it in the production entry graph even though the route tree-shakes.
3. **Screenshot spec** — `frontend/apps/web/tests/fidelity/<slug>.spec.ts` against `` (Vite alone, no backend, per-spec `page.route()` mocks, 1440×900). Register the route in `FIDELITY_ROUTES` in ``.

Worked example to copy: `` + ``.

### Step 0c: Human approval gate (HARD — the command STOPS here)

**The mockup is approved ONLY by an explicit `AskUserQuestion` answer. A prose reply is NEVER valid approval** (see Critical Rule 4b). This is a hard gate producing the `mockup-approved` artifact; your own fidelity-bar critique does **not** satisfy it, and neither does any chat message — only a tool-answer does ([`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §1.5b, enforced by `make validate-knowledge`). Until that tool-answer is on record the design is **BLOCKED** — no status flip, no PR.

Run it in this exact order:

1. **Present.** Screenshot the Lock-tier page at 1440 in every meaningful state (empty / loading / error / populated) and present them through the fleet's `ask` tool with the mockup attached (**a file path, a `localhost` URL or an `http.server` is not presenting** — the person cannot reach the box), plus the live `DEV` URL. The user must not have to go open anything to form a first reaction. **Render, present, and let the images go — never commit them** (§1.5-0d): the committed mockup HTML *is* the design contract and regenerates every one of these views on demand, so a committed PNG is a duplicate view that outweighed its own contract ~11x before the rule (268 renders / 41.8 MB vs 185 HTML / 3.9 MB, none ever embedded in a doc). Write them to your scratchpad, not the PRD directory — `make validate-knowledge` reds the build otherwise. The sole committed raster is the §1 `reference-<archetype>.png` craft target.
2. **Invite an open reaction, then WAIT.** Ask an open question — *"anything off in the layout or the shape?"* — with **no options attached yet**, so the user reacts freely, and stop. Iterate on pushback (2–3 rounds max), re-presenting each time. (An open reaction is for *iteration*; it is **not** approval.)
3. **Confirm they actually saw it.** If anything suggests the images may not have rendered — the reply doesn't reference the mockup, or is a bare "ok/continue" — do **not** infer they saw it. Ask, via the fleet's `ask` tool with the mockup attached, whether the mockup is visible (offer to re-send it) before seeking approval. A gate cleared without the human having *seen* the rendered mockup is a hollow gate — the exact failure that triggered this rule. **Publishing a hosted copy is the right move here** — it is what gets the design in front of a human reliably. It does **not** replace the committed file, and the record in step 5 names the file (§1.5-0).
4. **Collect approval via `AskUserQuestion` — the ONLY valid approval.** Once they are satisfied, call the fleet's `ask` tool (mockup attached; `AskUserQuestion` only with the viewer link in its text) with a single question that names the mockup, options **"Approve — lock this mockup"** (recommended-first) / **"Request changes"** (+ any real variants). The gate is cleared **only** by an *approve* answer to THIS tool. "Request changes" → loop back to step 1. **Never read a prose "yes / ok / go ahead" as clearing this gate** — this exact miss (a mockup "approved" by a one-word chat reply the human never tied to the image) is why the rule exists.
5. **Record the approval** in `ux-design.md` under `## Approved design`: the round, **the repo-relative path of the approved mockup file**, the fixture route, the date, and the `AskUserQuestion` approval (what was asked, what they chose, any conditions). `plan`, `implement`, and `verify` bind to it — headlessly, from the repo — so a record naming only a hosted URL binds them to nothing (§1.5-0). A hosted link may be appended as trailing context for the human.

**Never self-approve.** If no human answers the `AskUserQuestion`, the command STOPS with the mockup presented and this gate OPEN. An un-approved mockup is a blocked design, not a design with a caveat.

### Step 1: Initial understanding

Based on the PRD, respond with:

**Step 0-nec: run the necessity test before framing anything (Rule 6c).** For the PRD's central
mechanism, state — from the code, not from the PRD's prose — **how often it fires** (what a
customer does to reach it, and how often) and **what breaks if it is never built**. Put both in
the Phase 1 summary. If neither has a concrete answer, do **not** proceed to design: report that
the scope does not survive the test, name what would have to be true for it to, and stop. This
step exists because a design that reaches its red team before anyone asks whether the mechanism is
worth building has already spent the expensive half of the run.

1. **Your understanding** — summarize the feature from the PRD in 2-3 sentences.
2. **Design scope** — every layer `slot:architecture` names, marked Yes/No/Unknown.
3. **Key dimensions to resolve** — identify 5-8 design decision areas:
   - Scope refinements: Anything in the PRD that's ambiguous for design?
   - Data & state: What lifecycle/status transitions exist?
   - Edge cases: What happens when things go wrong?
   - Integration points: How does this interact with existing features?
   - Constraints: Performance, security, or compatibility concerns?
   - API surface changes
   - UI/UX approach
   - Configuration model

4. **First question** — pick the highest-impact unresolved dimension and ask it with `AskUserQuestion`, shaped by the interview card. This is the first question of the run: you have read the PRD and the human has not, and a fork inside a piece of work is unanswerable to someone who does not know what the work is.

<!-- include: process/interview-card.md -->
### Before you ask a human anything — the interview card

**The person answering has not read the issue, the PRD, the code or any register, and
will not look anything up.** They answer many questions a day from what is in front of
them, and only that. So, every time you ask:

1. **Say what the work is first, in plain words.** One or two sentences on what somebody
   will be able to do that they cannot today. Then **one concrete example** — a named
   person doing it, and what they see. Then **one line on what is undecided**, so the
   question reads as a fork and not a quiz. This goes in the message *before* the first
   question, once per run; later questions inherit it.
2. **Ask with `AskUserQuestion`:** 2–4 options, the one you recommend first and marked
   `(Recommended)`, and on *every* option why it is right and what it costs — not only on
   the one you favour, or the human cannot pick against you.
3. **Every option says what changes for a real person**, not what changes in the code.
   *"The error would read 'this key cannot list agents'"*, not *"return a typed reason from
   the allowlist path."*
4. **No bare ids, no unexplained jargon.** ``, ``, ``, ``,
   `PRD 0242` never appear in an option label, and anywhere else only in parentheses after
   the plain name — *the goal of getting a customer live without an engineer ()*. An
   internal noun (access profile, projection compiler, cause ledger, `blockedBy`) gets half
   a sentence of ordinary English the first time it appears. `file:line` stays, as evidence,
   never as the only statement of the problem.
5. **The test, before you send:** would somebody who has never opened this repo pick the
   same option, for the same reason? If not, rewrite. Being asked to *"explain that again"*
   is a defect in the question, not a preference — re-ask in full, plainer, and hold that
   register for the rest of the run.

6. **A mockup, design or any visual reaches the person ONE way: the fleet's `ask` tool with the mockup attached** (`upload_link` the folder, then `attachments: {bundleId, entry}`). Their browser is on their own machine, not on the box you run on: **never** tell them to open a file path, run `python3 -m http.server` or visit `localhost` / `127.0.0.1`, and never carry a mockup question in the built-in `AskUserQuestion`, which has no attachment. The tool answers with a viewer link; put that link whole in what you say. One authority: `.claude/process/interview.md` → *A mockup reaches a person ONE way*.

7. **The person may not be the one who knows — every question can be answered *"I can't
   answer this"*, and you must plan for that.** The question card carries that choice itself
   (*Can't answer — carry on*); you never add it as an option, and you never invent an answer
   in its place. When it comes back: **carry on with an explicit `Assumption: <what you
   assumed and why>` line, marked unconfirmed by the owner** — or, where the right party is
   the reporter, carry the question to them as an open question — **never ask it again**, and
   list every such item under an **`Unconfirmed assumptions`** heading in what you write, so
   a human can review them later. Downstream, it is an assumption to confirm, not a fact. The
   rule, once: `.claude/process/interview.md` → *"I can't answer this"*.

**Headless — no human attached:** you write all of the above into the escalation instead,
in the same words, so whoever reads it later can answer it as filed.

Full protocol — discovery before forks, acting on the answer, where the decision is
written: `.claude/process/interview.md`.
<!-- /include -->

### <Dimension name>

<Why this matters for the design>

1. **<Option A>** — <1-sentence rationale>
2. **<Option B>** — <1-sentence rationale>
3. **<Option C>** — <1-sentence rationale>

**Recommended: Option X** — <2-3 sentences explaining why>

### Step 2: Iterate

After each user response:

1. **Acknowledge** — confirm the decision and note implications.
2. **Update the decisions tracker:**

### Decisions so far
1. **<Dimension>:** <chosen option> — <brief rationale>
2. **<Dimension>:** <chosen option> — <brief rationale>
...

3. **Next question** — move to the next unresolved dimension. Always use `AskUserQuestion` and the numbered-options-with-recommendation format.

### Step 3: Confirm

When all key dimensions are resolved, present the **feature summary** and use `AskUserQuestion` to ask for confirmation before proceeding.

```
## Feature Summary: <name>

**What:** <1-2 sentences>
**Who:** <persona from vision doc>
**Why:** <problem from PRD>
**Scope:** <V1 boundaries>
**Key design decisions:**
- <decision 1>
- <decision 2>
```

---

## Phase 1.5: Architecture Audit (MANDATORY — do NOT skip)

**Goal:** Before locking in a per-layer design, audit the existing architecture in the areas this feature will touch and surface anything that doesn't match a clean, consistent baseline. This is the moment to catch quirks — not after the design doc is written, and not during implementation.

### Step 1: Survey the affected surface

Based on the layers marked Yes/Unknown in Phase 1, read the existing code in those areas. For each layer the feature touches:

- Read the most-similar existing handler / service / table / page / agent / job / event.
- Compare it against the conventions in `CLAUDE.md` and the specs under `knowledge/specs/`.
- Note whether the surrounding code follows those conventions cleanly, or deviates.

### Step 2: Identify quirks and improvement opportunities

Catalog every finding. A "quirk" is anything in the following non-exhaustive list:

- **Convention drift** — code that violates an explicit rule in CLAUDE.md or in the contracts `slot:languages` names (an unsupervised goroutine where the contract forbids one, raw SQL where the query layer is generated, an untyped field where a typed override is required, a hardcoded prompt where definitions are declarative, an untyped event publish).
- **Leaky abstractions** — a layer reaching past its boundary (a handler doing business logic, a storage query embedded in a handler, the frontend bypassing the API prefix, hand-written code importing what only generated code should).
- **Inconsistencies** — two existing implementations of the same concept that diverge (different error envelopes, different pagination shapes, different naming for the same field, different patterns for soft-delete or audit logging).
- **Missing primitives** — a helper or shared utility that *should* exist for clean reuse but doesn't, so each call site reinvents it.
- **Resilience hazards** — the ones `slot:resilience` names: in-memory state without invalidation events, unsupervised background work, non-idempotent webhook/job handlers.
- **Permission/authz gaps** — handlers that bypass the permission check, operations missing the permission annotation `slot:api-contract` requires, any path on the governed read path (`slot:permissions`) that could widen rather than narrow.
- **Generated/hand-written confusion** — edits to generated files, or hand-written code in a place that should be regenerated.
- **Test gaps in the surrounding code** — error paths not exercised, mocks where integration tests are required.
- **Naming/typing weakness** — strings where the repo's typed identifiers should be used; magic constants; ids typed as bare strings.

For every finding, write one line:

> **[Layer X.Y]** `:NN` — <what's wrong> — *contradicts <which CLAUDE.md/spec rule, or "internal inconsistency with <other path>">*.

### Step 3: Disposition each one — **fix is the default *inside the diff you already have open*, and you do not ask for it**

A quirk finding is an **engineering judgement**, not a scope decision. CLAUDE.md's golden rule
settles it: *industry best practice is the default — adopt it without asking; never interview
the user to ask permission to follow the standard.* Asking a human to approve "should we fix
the thing that contradicts our own written rule" spends the one resource the pipeline cannot
manufacture, on the one question whose answer was never in doubt.

**But that licence is bounded by the files this design already opens** (Rule 6b). A survey
that reads the whole surrounding surface will find quirks in code this PRD had no reason to
touch, and sweeping those in is how a PRD triples in size without anyone choosing it. **So
split the findings by that line before dispositioning anything:**

- **In a file this design already modifies** → the four outcomes below apply, fix-first.
- **Outside one** → it is not this PRD's work. **File it** (`Type:bug` or `Type:task`, in
  the **`Triage Queue`** workflow state), cite the key in *Architecture decisions*, and
  leave it out of the design.
  `/fleet:check` grades it in a session with no stake in this PRD — which is the point, since
  the session that found the quirk cannot grade its own scope.

For a finding **inside the diff**, the outcomes are:

1. **Fix it now — THE DEFAULT.** Take it. Include the cleanup in this design's scope, record
   it in *Architecture decisions* with a one-line rationale, and move on. No `AskUserQuestion`.
2. **Defer as tracked follow-up** — you may choose this **yourself** when the fix is genuinely
   out of scope and would balloon the PRD. It is not free: **mint the tracked issue in this
   run** (`Type:task`, in the **`Triage Queue`** workflow state) and cite its key in the
   design. A "deferred" finding with no issue is a finding you deleted — the exact shape
   that produced PRD 0252's untracked integration seams.
3. **Consciously perpetuate** — this one **escalates**. Choosing to keep contradicting a
   written rule is a decision to carry debt, and CLAUDE.md reserves that for a human: *"if a
   hack is ever taken, name it out loud as debt alongside the best-practice path it
   displaces."* One `AskUserQuestion`, naming the rule being perpetuated and the cost.

**A "missing primitive" is not a quirk — it is an addition.** The one bullet in Step 2 that
routes differently from the rest: *"a helper or shared utility that should exist but doesn't"*
describes something that would **exist** after this PRD that does not now, so it is scope, not
craft. Extract it only when a PRD acceptance criterion cannot pass without it (Rule 6b clause
1) or when this design's own call sites would otherwise duplicate it; a primitive built for
call sites this PRD does not write is speculative generality — **withhold it** for Phase 5.4.

**Escalate regardless of outcome when the finding touches scope** — a fix that would add or
change a `**[XXX-NNN]**` promise, or that reaches into the governed read path, auth, or the
customer-network data plane. Those are not quirks; they are commitments wearing a quirk's
clothes, and the register is where the answer belongs
([*The claim spine*](#)).

**Do not proceed to Phase 2 until every finding has an explicit disposition** — but a
disposition you made yourself, on the record, is an explicit disposition. Track them:

### Architecture decisions
1. **<Quirk 1>:** <chosen option> — <rationale>
2. **<Quirk 2>:** <chosen option> — <rationale>
...

### Step 4: Proposed deviations from existing patterns

Separately, list anything in the planned new design that would deviate from the existing-but-clean baseline (e.g., introducing a new abstraction, a new table shape, a new event-naming convention). Each must be explicitly approved via `question` before Phase 2. The default is "match the existing clean pattern" — deviations require justification.

---

## Phase 1.6: Integration reality check — runtime execution trace (MANDATORY for integration / capstone PRDs; the existence-claim citation sub-step below is MANDATORY for every PRD)

**When the full trace applies.** Any PRD whose value is that already-built pieces *connect* end to
end rather than a net-new mechanism — a reference app, an "e2e proof", or any design that
would conclude "pure composition / reuse-only / no new mechanism". For these, the
composition **is** the deliverable, so it must be verified at design time — never assumed.

**Why (learned the hard way — PRD 0252).** Seven upstream PRDs read `status: shipped` while
the composed path returned 503 the entire time: each shipped its own layer with fakes and
deferred the integration seam as an untracked in-code TODO. The capstone was the first thing
to ever run the real path and discovered nothing connected — the most expensive place to
find out. **`status: shipped` proves a capability *exists*, never that it is *connected*.**

**Do this before Phase 2:**

1. **Trace the full runtime path, hop by hop.** For the PRD's central end-to-end flow
   (e.g. `upload → sandbox → governed write → queryable row`), name each hop and **cite the
   `file:line` that actually executes it in `main` today** — grep for the callee being
   *called* in production wiring, not merely *defined*. A hop you cannot cite a live
   executing line for is **not** "already shipped": it is a **Gap** (Phase 4a), regardless
   of any upstream PRD's `status: shipped`.
2. **No un-backed "composition" conclusion.** "Pure composition / gaps: none / no quirks
   found" is **forbidden as a Phase 4 conclusion unless the hop-by-hop trace backs every
   hop.** For an integration PRD, "no gaps" *without* a trace is a red flag, not a green
   light — it is the exact shape of the 0252 miss.
3. **Every hop must be testable at its real seam.** If an acceptance criterion claims to
   exercise a hop, the test path must drive the **real** seam — no fake/stub standing in for
   the very seam under test (0252's fullstack harness faked the write path it was meant to
   prove). If the shared test harness cannot yet drive a hop for real, that is a **Gap** to
   file, not a seam to fake.

Record the result in the design's **"Integration trace"** output section (Phase 6). Every
un-citable hop becomes a Phase 4a Gap with an owner before this design advances.

### Existence-claim citations (MANDATORY for every PRD, not just integration/capstone ones)

**When this applies.** Any acceptance criterion — new or revised — whose satisfaction rests on
"the capability already exists" (e.g. "no new tool", "already has", "already carries", "the way
its memory already is"), and any task this design proposes cutting on the rationale that an
existing capability already covers it. This is narrower and far cheaper than the full hop-by-hop
trace above — a **one-line citation**, not a walk of an entire flow — and unlike the trace, it
fires on **every** PRD design, integration/capstone or not.

**Why ().** PRD 0414's design revision (D7) asserted the companion "still knows the user"
using "the memory it already has" and cut task B9 on that premise. No stage — design, plan, or
verify — ever named the executing code path for the claim. The claim was false: the companion is
a definition-keyed built-in, never a `RuntimeAgentKindInstance` row, and the memory write tools it
was assumed to already hold are granted only to instance agents. A `shipped` PRD and a live
journey AC ended up asserting a capability the product structurally could not have — caught six
days later by an audit, not by this design or its verify pass.

1. For every AC (new or revised by this design) whose justification is an existence claim, cite
   the `file:line` in `main` today that actually executes the claimed capability — grep for the
   thing being *used* in production wiring, not merely *defined*. Citing another planning
   document (a PRD, an earlier design section, a decision record) that itself repeats the same
   claim is **not** a citation — it must resolve to running code.
2. For every task this design proposes cutting on an existence-claim rationale, the same
   citation backs the cut.
3. **If you cannot cite a live line, the claim is unverified.** Do not write the AC as satisfied
   by the existing system and do not cut the task on that basis — file a Phase 4a Gap instead.
4. Record the citation inline, next to the AC or the cut-task note it backs — not in a separate
   ledger.

**Enumeration recipe** (spot-check already-shipped PRDs for this pattern while in the area):
`rg -n 'already (has|have|carries)|the .* it already' knowledge/prds/*/prd.md`

---

## Phase 2: Technical Design — Layer Breakdown

**The layers are the repository's, not this command's.** `slot:architecture` names
the layers a change can touch here — a shared-contract tier, storage, an API surface, the
handlers behind it, background work, an agent runtime, an event bus, configuration, a web
UI, a test suite, mail, an audit log, authorization, secrets — whatever *this* product is
built from, and in the order it builds. Read that list first. **For every layer it names,
mark Yes / No / Unknown**, and for every Yes write the design for it. An "Unknown" is a
question for Phase 1.5, never a layer silently skipped. **Apply the architecture decisions
from Phase 1.5** — if the user approved a fix, fold it into the relevant layer's design; if
deferred, note it in the Improvements section.

**Ordering note:** start with whichever layer the others derive from — where the repo has
a shared-contract tier (`slot:codegen`), that one — because a change there
regenerates into the rest.

### What a layer's design section must contain

The same five things, whatever the layer:

- **What is new or changed** — the concrete artifacts: a table and its queries, an
  operation and its schemas, a handler and its dependencies, a definition file, an event
  type, a page and its components, a permission constant, a secret's home.
- **What it reuses** — the existing helper, pattern or component it builds on, named. A
  layer with nothing to reuse is a layer the repo has not built before; say so.
- **The conventions it obeys** — cited, never restated: the contract
  `slot:languages` names for the layer's language; `slot:api-contract` for an
  operation; `slot:permissions` for anything on the governed path; `slot:codegen`
  for what must regenerate and `slot:codegen` for what must not be touched.
- **The hazards it must design for** — the ones `slot:resilience` names for this
  repo. Where that slot names a **multi-replica** posture (`slot:resilience`),
  background work and in-memory state run on every replica: exactly-once work needs a lock
  or leader election, caches need an invalidation path, in-process events only reach one
  replica's clients, and anything delivered more than once must be idempotent.
- **How it is tested** — the lane `slot:gate` runs for this layer, and the error paths the
  test must cover.

### Storage

New tables or columns follow the repo's naming, key and timestamp conventions; every new
query is listed by name and shape; a migration is **numbered at implement time**
(`python3 knowledge/scripts/validate_id_collisions.py --allocate`), never in the design.

### API

A new operation names its path, method, id, auth and permission annotations, and its
request/response schemas, all per `slot:api-contract`. The pre-check `prd:plan` runs is
cheaper the more of it is decided here.

### Background work

Choose between the in-process async pattern and the periodic job pattern the repo has —
`slot:architecture` names both where they exist — and apply the multi-replica rules
above to whichever you choose.

### Web UI

**Always read the UI contract `slot:ui-contracts` names first.** It is the design-system
baseline — all UI decisions follow the page structures, component patterns and
interaction conventions documented there. Do not invent a structural pattern when an
existing one applies.

**The surface is the journey's surface — nothing more (Rule 6b).** Rule 5 makes the UX
*mandatory*; it does not make it *large*. Every screen, panel, control, setting, toggle, filter,
bulk action, secondary view and empty-state variant is a scope addition, and the ask that
licenses it is the **agreed journey from Phase 0.5** plus the PRD's acceptance criteria — not
your sense of what a complete product would have. Design the surface each journey step needs
and stop there. Anything else you can see is **withheld for Phase 5.4**, where the human either
pulls it in or does not.

**The mockup gate is not where this gets decided.** Rule 4b sends every mockup to the human for
approval, and it is tempting to read that as covering additions too — it does not. A mockup
arrives as a finished picture with the extras already drawn into it, which asks the human to
veto something that already looks built. That is approval by fait accompli, and it is precisely
how a surface nobody chose gets shipped with a sign-off on the record. **Keep the extras out of
the mockup and put them on the Phase 5.4 list**, where each one is a line with a cost next to
it, and where "no" is the default rather than an objection the human has to raise.

**When this layer is affected, ask the user** (shaped by the interview card, Phase 1):

> "This feature involves [new pages / significant workflow changes / new interaction patterns]. Would you like me to do a full UX design? This will produce a separate `ux-design.md` with screen-by-screen intent audit, content design, story arc, and AI-first pattern analysis. For minor UI changes, I can include the UI approach in the main design doc instead."

**If the user wants a full UX design**, run the UX Design sub-phase (see Phase 2b below).

**If not**, include a brief UI section in the main design doc:
- Pages/components affected
- Key interactions
- API calls from the UI
- SSE subscriptions needed
- Component patterns used (reference `@` — e.g., "Card layout from § Component Patterns", "Tab structure from § Tabs")

### Testing

The lanes `slot:gate` names, per layer touched. Every handler tests its error paths
against the repo's mocking pattern for the storage layer.

### Authorization, audit, secrets

New permission constants and their role assignments, and the annotation the API contract
requires per operation (`slot:permissions`); which mutations the audit log
records (action, resource, scope); credentials go where `slot:permissions` says secrets
live — never in configuration, never in code.

---

## Phase 2b: UX Design (opt-in)

Only run this if the user requested it in Phase 2.11.

### UX Discover

1. **Read ``** — this is the design system baseline. All UX decisions must follow the page structures, component patterns, and interaction conventions from this file.
2. **Problem summary** — who, trigger, goal, current pain, constraints.
3. **Clarifying questions** (only if genuinely ambiguous — max 4 questions about user needs, not design preferences, shaped by the interview card, Phase 1).

### UX Research & Recommend

Present ONE recommended approach with:
1. **The recommendation** — interaction model, layout, key patterns
2. **Why this approach** — cite UX principles (Nielsen heuristics, JTBD, WCAG, Fitts's Law, Hick's Law)
3. **Alternatives considered** — 1-2 rejected approaches with reasoning
4. **Known trade-offs**

### UX Detailed Design

For every screen/state:

**Four Questions test:**
1. Where am I? (headline, breadcrumbs, navigation context)
2. How did I get here? (logical flow)
3. What can I do? (visible, labeled actions)
4. Why should I do it? (value proposition)

**Content design:**
- Headlines & subtitles (name the thing, not the page)
- Button labels (verb + noun)
- Empty states (headline + description, no button inside — action in page header)
- Error messages (what went wrong + how to fix)
- Success messages (what happened + what's next)
- Confirmation dialogs (action title + consequence)

**AI-first patterns** (for AI-related features):
- How is AI output presented? (streaming, confidence, citations)
- How does the user correct/refine AI output?
- What happens when AI fails?
- Automation level (manual → suggested → auto)

**Story arc:** Setup → Trigger → Rising action → Crisis → Resolution → End

**Convention compliance (refer to `` for full details):**
- Page layout, headings, and section structure
- Component patterns: cards, tables, tabs, accordions, alerts, buttons
- Empty states, loading states, error states
- Modals: Dialog for edits, AlertDialog for destructive confirmation
- Permission gating: PermissionGated* components
- Breadcrumbs: detail pages only

**Self-Determination Theory check:** Autonomy, Competence, Relatedness

### UX Output

Produce `knowledge/prds/NNNN` with the full UX design document, opening
with the `prd-ux-design` frontmatter header (same [`FILE-TYPES.md`](#)
requirement and CI gate as `design.md` above — ):

```markdown
---
type: prd-ux-design
---

# UX Design: <feature name>
```

The document must reference `` as its design system baseline — use the documented page structures and component patterns, don't invent new ones. It must **also**, per surface, record the **named high-craft reference** (Phase 1 Step 0 / [`design-fidelity-loop.md`](../../../process/design-fidelity-loop.md) §1) and state that the screen's mockup **clears the design-fidelity bar** (§2). `plan`, `implement`, and `verify` all read `ux-design.md` as the fidelity target — the reference and the bar must travel with it, or the taste standard is lost the moment design ends.

---

## Phase 2c: Design red-team (MANDATORY — argue the design is wrong)

Phase 1.5 audited the **surrounding code** you're inheriting. This phase turns the same
skepticism on the **design you just produced** — before it's elaborated into reuse/gaps
and written out. It is the operational form of the golden rule ("actively hunt for a
better design than the one proposed; the goal is the *best* technical solution, never the
easiest"), made a step so it can't be skipped under pressure. Grade against the
**`architecture-red-team` rubric** ([`design-critique.md`](../../../rubrics/architecture-red-team.md)):
R1 simplest-thing-that-works · R2 or under-built (a load-bearing invariant ignored —
multi-replica, narrowing-only, `connectord`-sole-writer, idempotency) · R3 consistent vs a
parallel pattern · R4 right boundaries · R5 is there a materially stronger alternative ·
R6 blast radius if wrong (one-way door) · R7 commitments contradicted, silently dropped, or
created and unrecorded.

### Dispatch the critic panel

**This step is performed by calling the `Agent` tool. Reasoning through it yourself does
not perform it** ([`spine.md`](../../../process/spine.md) →
*"`actor: subagent` means a real sub-agent"*), and the spine says so too: this step is
`kind: fanout`, `actor: subagent`. The property being bought is that **the reviewer did
not author the thing under review** — you cannot supply that about your own design at any
level of effort, which is the whole reason the step exists rather than an instruction to
"be skeptical here". If you cannot dispatch (the harness forbids it, a session-level
instruction conflicts), the step **FAILS**: leave its todo open, say plainly that the
panel did not run, and do **not** write a self-review into *Architecture notes* as though
it had. Disclosing a substitution is not performing the step.

Spawn an **independent critic** — a sub-agent that did **not** author this design — and
task it explicitly to *argue the design is wrong* and to produce the strongest concrete
alternative. Default posture is skepticism, not ratification; "looks fine" is not a useful
return. For a **high-blast-radius** design (an R6 one-way door — a new schema, wire
contract, permission model, or interface others will build on), dispatch a small **panel**
with distinct lenses (simplicity/consistency · invariants+commitments · find-the-better-design)
rather than one generalist critic — a diverse panel catches failure modes redundancy
misses. **R7 is one more lens on that panel, never a second panel** — the reason is the
rubric's, not restated here. The critic reads `design.md`-in-progress (+ `ux-design.md` if
present) and returns findings keyed to R1–R7, each with a specific claim and, for R5, a
named alternative. R7's raw material is Phase 4c's own tooling — run
`python3 knowledge/scripts/requirement_query.py prd <NNNN>` and hand the critic its output alongside
the design, so the lens starts from the claimed rows and their `Needs` rather than
rediscovering them.

### Disposition each finding (adopt / reject-with-reason)

For EACH finding, **you** decide — exactly as Phase 1.5 dispositions quirks, and with the same
default and the same bound. A critic finding is an engineering judgement; it reaches a human
only when it turns into a scope question.

**First sort the finding by direction, because the panel produces both and they are not
symmetric.** A critic's job is to argue the design is *wrong*, and it returns two kinds of
finding:

- **Subtractive / corrective** — R1 (you built more than the PRD needs), R2 (a load-bearing
  invariant is ignored), R3 (this is a second way to do an existing thing), R4 (wrong layer),
  R7 (a commitment contradicted or dropped). These change **how** the asked-for thing is
  built, or make it smaller. **Craft. Adopt by default, no `AskUserQuestion`.** R1 in
  particular is the most common finding in the rubric *because* over-building is the most
  common failure — adopting an R1 finding is the cheapest scope reduction in the pipeline, so
  take it.
- **Additive** — R5's "materially stronger alternative", or any finding whose remedy is a new
  surface, control, table, event, permission, flag or abstraction the PRD never named. These
  change **what gets built**, so Rule 6b governs: adopt only if a PRD acceptance criterion
  cannot pass without it, and otherwise **withhold it for Phase 5.4**. A critic is an
  excellent source of good ideas, and a good idea nobody asked for is still scope. Note that
  R5 is answered by *arguing* the alternative and recording the outcome — conceding it wins
  when it does is craft; **bolting it on top of the existing design is not adopting it, it is
  building both.**

Then, per finding:

1. **Adopt — THE DEFAULT for a subtractive/corrective finding.** Fold the change into the
   design; loop back into the relevant Phase 2 layer for that change only (it does not restart
   discovery). No `AskUserQuestion`.
2. **Reject-with-reason** — the critic can be wrong, and you may say so yourself. Record the
   reason in the design's **Architecture notes** (Phase 6), so a future reader sees the
   alternative was considered and consciously declined.
3. **Withhold — THE DEFAULT for an additive finding that no AC requires.** It goes on the
   Phase 5.4 offer list with a one-line cost, and into the `## Scope ledger` as `withheld`.
   Not adopted, not filed, not argued for further.
4. **Escalate** — `AskUserQuestion` *now* rather than at Phase 5.4, and **only** when adopting
   the finding would add or change a `**[XXX-NNN]**` promise or settle a row the register
   still calls `open`. Those block Phase 4c, so they cannot wait for the batched offer. A
   finding that merely alters a **surface the customer sees** is additive scope like any
   other — it goes to Phase 5.4 with the rest, and if it is pulled in there it re-enters the
   mockup gate (Rule 4b) before the design is final.

**Hard gate — but on disposition, not adoption.** Do not advance to Phase 3 until every
red-team finding has an explicit adopt / reject / withhold decision on the record. The gate forces the
alternative onto the table where the golden rule wants it; it does **not** let a skeptic
veto a design the author can defend. Record the panel's findings and their dispositions in
the design's **Architecture notes** alongside the Phase 1.5 decisions.

---

## Phase 3: Reuse Analysis

Summarize what existing code and patterns to reuse:

| Capability | Reuse? | How |
|------------|--------|-----|
| <one row per layer `slot:architecture` names> | ... | ... |

---

## Phase 4: Gaps & Improvements

Two distinct lists. Both must be explicit; neither may be silently assumed.

### 4a. Gaps — missing capabilities the feature needs

Anything not yet available that this feature requires (a new helper, a new event type, a new
permission, an external integration, etc.).

**"Needs" is the whole word, and it is load-bearing.** Every row here is something that will
**exist** after this PRD and does not now — which makes each one a scope addition under Rule
6b, not a neutral consequence of the design. State, per row, **the acceptance criterion that
cannot pass without it**. A gap you cannot tie to an AC is not a gap this PRD has: it is an
idea, and it belongs on the Phase 5.4 offer list and in the `## Scope ledger` as `withheld`.

The two shapes that get mis-filed here most often, both of which look like gaps and are not:

- **A generality with one call site** — a config knob, a strategy interface, a pluggable
  backend, a flag, an extension point — where this PRD writes the only caller. Build the one
  case; the second caller is what earns the abstraction (this is the red-team's R1 lens
  arriving early).
- **A capability the design would be *nicer* with** — an export, a bulk action, a filter, a
  preference, a secondary view. Nice is not *cannot pass*.

### 4b. Improvements — quirks/cleanups identified in Phase 1.5

Echo every Phase 1.5 finding here with its decision:

| # | Quirk / Improvement | Location | Phase 1.5 decision | Owner / when |
|---|---------------------|----------|--------------------|--------------|
| 1 | <description>       | `path:NN`| Fix now / Defer / Perpetuate | <this PRD / new ticket / N/A> |

**Anything marked "Fix now" must already appear in the relevant Phase 2 layer's design.** Anything marked "Defer" must have a clear owner — either a follow-up PRD number, an issue link, or "needs filing." Anything marked "Perpetuate" must include the user's explicit reason on the record so future readers know it was a conscious choice.

---

## Phase 4c: Commitments — reconcile the requirement register (MANDATORY)

**`/fleet:prd:create` Phase 0.6 could only *read* commitments that already existed. This
command *makes* them** — a design settles the forks the PRD left open, and every fork it
settles either takes a commitment we already carry, adds one, or kills one. That is why this
step lives here and not at write-time: run it **before Phase 6 writes `design.md`**, so the
document cites row IDs instead of restating them.

The model — the six `Kind`s, the four `Disposition`s, `Needs`, `implements:`, and what a
supersession drags with it — is owned by
[`knowledge-model.md`](#) → *Decisions and
requirements*, and it wins over anything written here. `make validate-knowledge`
reads the result at pre-commit.

1. **Re-read the PRD's claims — with the query tool, never by reading the table.**
   `python3 knowledge/scripts/requirement_query.py prd <NNNN>` prints every claim, what each one
   `Needs`, and which of those needs **no live PRD is building**; `--json` if you are
   feeding it to something. `implements:` was provisional at Phase 0.6 and scope has moved
   since: drop what this design no longer realises, add what it now does, and refresh the
   frontmatter in the **same commit** as `design.md`. Reconciling this by reading the
   register is what the tool replaces — the table is 699 rows, and hand-parsing it has
   silently produced empty answers that read exactly like clean ones.
   **The UNSATISFIED list is this step's real work, and it is a question, not a verdict.**
   A need nothing is building is either real work nobody has scheduled (fine — note it as
   a Phase 4a Gap) **or an edge into a mechanism this design's own Non-Goals cut**, which
   is step 4's closure arriving one step early. The second is not hypothetical: seven of
   PRD 0486's sixteen claims declared needs into the tier its biggest Non-Goal deletes, so
   the graph asserted the critical-path PRD was unsatisfiable until v2 — repaired in
   `3ad63c6d7e`. Nothing detects that automatically, because a deferred row stays `adopted`
   with the deferral in its prose; `make validate-knowledge`'s claim-scope rule raises
   the shape as an advisory and **you** are the one who says which of the two it is.
   `requirement_query.py open <NNNN>` lists the still-undecided rows in the sections you
   are building in — the forks this design is about to hit whether or not it claims them.
1a. **Reverse coverage — surface adopted decisions that already invalidated a requirement
    on the ground this design touches (MANDATORY, and the gate 0543 missed).** `drift`
    (validate_requirements.py) only fires when a PRD CLAIMS a superseded/rejected row; a
    PRD that reaches into a surface an adopted decision retired WITHOUT claiming the row —
    the  shape, where PRD 0543 promoted grant-conversions to top-level nav the day
    after  made them dead — claims nothing that would trip it. For **every component
    and surface this design is about to touch** — the declared area *and* any other
    component it reaches into — run:
    `python3 knowledge/scripts/requirement_query.py decided --components <comma,separated>`
    It lists the rows an adopted decision has already invalidated on that ground
    (superseded/rejected/excluded) and the decision that did it. Read them **before**
    committing to build. If one invalidates a requirement this design builds, drop or
    re-scope that requirement (it is dead on arrival), and if the decision binds beyond
    this PRD record why in **Architecture notes** — never build it and name the
    inconsistency afterwards, which is exactly the deferral that shipped 0543's R7.
2. **Every fork you settled is a decision, and the rejected branch is the half that rots.**
   Record it in **Architecture notes** (Phase 6) with the option refused *and its reason* —
   that section is this PRD's decision record and the generated ledger indexes it. A fork
   that outlives this PRD (a platform-wide call that binds work beyond it) goes to a
   standalone dated record in [`knowledge/decisions/`](../../../../knowledge/decisions/)
   instead. Those two are the only homes.
3. **A durable commitment inside that decision is a row, not a paragraph.** This design has
   already generated the candidates — walk them: **Step 0-pre** (a deviation from the
   best-practice baseline → `accepted`, with the standard it displaces as `alternative` /
   `rejected`), **Phase 1.5 "perpetuate" / "defer"** (→ `accepted` — a cost taken
   knowingly), **Phase 2c reject-with-reason** (→ `alternative` + its disposition), and
   **any number this design fixes** — a timeout, a ceiling, a floor (→ `constraint`). Each
    becomes a row: **the id from `python3 knowledge/scripts/validate_id_collisions.py --allocate <PREFIX> <N>`,
    which reserves it atomically as a claim ref on GitHub, written into the register** — there
    is no counter to bump, and never a number you picked by reading the last row, which is how
    `..719` came to be allocated twice on  and how four concurrent branches
    collided seven times on . CI refuses an id this change introduces without a
    claim; the same script's collision check must still re-run after every rebase (a rebase
    resolves the text while leaving a capture in place);
   its **`Needs`** edges written with it; and a
   `Source` naming this design plus the **quoted phrase** that settles it, in the form the
   target register's *Source legend* defines (add a legend row if a PRD design is a new kind
   of source there) — **never a line number**. The quote has to survive: write that sentence
   into the **Architecture notes** draft as you write the row, so Phase 6 carries it
   verbatim rather than paraphrasing it out from under the citation.
   *Not every line in those lists is a row.* The test is the model's own: would a reader
   outside this PRD ever need to re-read the reason? A local build choice is a design
   detail; a property the system must hold afterwards is a row.
4. **A design that cuts a mechanism supersedes the rows describing it — in this same
   change.** The closure that entails (the dead row's own `Needs` cleared, every edge
   pointing at it re-derived, every claiming PRD re-pointed) is the model's rule and is not
   restated here; the validator fails the commit on each residue. **What the validator
   cannot see is that you cut the mechanism at all** — so name the rows this design
   invalidated while you still remember why. Skipping it is not a small debt: two designs
   landed without it and a later pass found ~129 rows still describing mechanisms we had
   already dropped.
5. **Cite the ID; never restate the row.** Where the argument genuinely needs the words,
   **quote** the row — a paraphrase mints a second assertion that drifts from the first.
6. **Each claimed row gets an acceptance criterion that would fail if it were not met**,
   in the citation form `**[]**`, in Phase 6's *Acceptance criteria*. **One direction
   only** — most ACs cite nothing. Advisory at `designed`; `/fleet:prd:plan` gates on it
   **hard** before flipping to `planned`, so a claim you cannot write an AC for is a claim
   to drop *here*.
7. **Settle every `open` row this design touches — this is the human-input moment, and the
   only one that is about scope.** A row is born `open` at
   [`slice:create`](#) Step 3 ("named, but no mechanism and no number
   yet"), and settling it is a *design* act: you are the first command with the mechanism in
   hand. `requirement_query.py open <NNNN>` lists them.

   For each: if the design settles it, flip `Disposition` to `adopted`, write the mechanism
   and the real `Source`, and claim it in `implements:`. **If settling it means choosing
   what the product promises** — not how it is built — that is the escalation:
   `AskUserQuestion`, shaped by the interview card (Phase 1).

   **The answer is written into the register row, not only into `design.md`.** A human
   decision recorded in one design document is consumed once; the same decision recorded as
   a settled row is read by every PRD that follows on that ground. This is the difference
   between spending the human's attention and capitalising it, and it is the whole reason
   `open` exists as a disposition
   ([*The claim spine*](#)).

   A row you could not settle stays `open` and **blocks the flip to `designed`** — an
   unsettled promise means the design does not yet know what it is building.

8. **No register covers the domain? Open one — do not defer.** The old instruction here
   ("do not open one mid-design to hold a single row… carry the assertion in Architecture
   notes") is **withdrawn**, for the same reason as
   [`prd:create`](create.md) Phase 0.6: that deferral is why 36 of 65 components carry no
   register and their commitments sit in prose nothing can count. A register's domain and ID
   prefix are permanent, so name them deliberately — but name them, and say in your report
   that the owning slice skipped its Step 3 framing so the rest of that promise set gets
   written before the next PRD repeats this.

**No un-backed "nothing new" conclusion.** A design that resolved dimensions, dispositioned a
red team, and took a best-practice deviation has produced commitments. "No register change"
is a legitimate outcome — but only stated with the candidates you examined, exactly as
Phase 1.6 forbids an un-backed "pure composition".

**This phase is provable, and the proof is the `## Commitments` section Phase 6 writes.**
`make validate-knowledge` **blocks** the commit and the PR when a design
authored on or after its `PHASE_4C_CUTOFF` reaches `designed` or beyond without a filled one
— including the unfilled `<…>` template stub. It checks the footprint, never the content:
whether the rows are the *right* rows is R7's job on the Phase 2c panel, not a validator's.

---

## Phase 4.5: Cross-repo scope check (MANDATORY — do NOT skip)

**Why ( — hit twice in one session, PRDs 0320 and 0331).** `` → "Cross-repo scope" and the Phase 6 output template both already say a same-PRD AC is never cross-repo-only — but that lived as a footnote easy to skim past under time pressure. Both PRDs reached `status: implementing` with an AC buildable only in another repo still sitting in their own list, so `knowledge/scripts/validate_verify_gate.py` blocked every subsequent implementation PR against that PRD indefinitely — the PRD could never independently reach `verified`, discovered only at ship time, per-PRD, by hand. Catch it here instead.

**Do this before Phase 5, over the AC list as it stands after Phase 2 (PRD ACs + any layer-specific criteria this design added):**

1. **Walk every AC and classify it**: can it be independently coded, tested, and merged
   **from this repo alone**? Same test as
   [`tracking-and-execution.md`](#) →
   "Cross-repo scope" — a mention of a companion repo's *name* in an AC's prose is not
   itself disqualifying; what matters is where the AC's own implementation and tests live.
2. **Any AC that fails that test is not this PRD's AC.** Do not list it in Phase 6's
   Acceptance Criteria. Instead, in this same session:
   - File it as its own Rule-G-tracked companion issue (`Type:task`, `repo:<lane>` label —
     the shape  and
      used) now — do not defer the
     filing to implementation.
   - **NEVER title it `[NNNN] …`. That prefix is reserved for the PRD's OWN issue** and is
     the join key the `prd-projection` pass of the fleet's `corpus-sync` loop resolves on (`^\[(\d{4})\]`).
     Title a companion **`[NNNN companion · <repo>] <what it delivers>`** — the form
      uses (`[0331 companion ·
     -apps] …`). **This is not cosmetic.** The index binds a number to whichever
     matching issue it sees first (`idx.setdefault`), so a second `[NNNN]` issue silently
     captures the PRD's identity: on  a companion titled `[0487] …` took PRD
     0487's projection — its description was overwritten with the PRD's, the real PRD issue
     went stale for hours, and every push to `main` re-projected `planned → Spec` onto the
     companion while the fleet moved it back to `Done`.
   - Name it in the design's **"Delivery notes (cross-repo)"** section (Phase 6) with the
     companion repo, the exact AC(s) it carries, and its tracking issue.
   - Link it from the owning **slice's** PRDs/dependency list.
3. **No un-backed "all in-repo" conclusion.** State explicitly, in the Acceptance Criteria
   section itself, that this check ran (e.g. "no cross-repo ACs" or a pointer to the
   Delivery notes table) — an AC list with no such statement is incomplete, the same way a
   Phase 1.6 integration trace with no hop citations is incomplete. `make validate-knowledge`
   (CI, non-blocking) backstops this heuristically, but it is not a substitute for doing the
   check here — it only catches what this step missed.

Skipping this phase is exactly how 0320 and 0331 reached `implementing` un-split. It is not
conditional on the PRD "looking" single-repo — check anyway; the cost is one pass over an AC
list you already have.

---

## Phase 5: Implementation Order

Suggested order (tests alongside each layer): **the order `slot:architecture`
lists them in**, which is the order the product builds — contracts and anything that
regenerates into the rest first (`make generate` after each), then storage, then
permissions, then services, then the surfaces (API, events, UI), then the cross-cutting
layers (audit, mail). A layer the repo does not have is simply absent from the list.

---

## Phase 5.4: Scope offer — put the withheld additions to the human, once (HARD GATE)

**Every phase above has been withholding.** Phase 1.5 withheld the missing primitives and
routed the out-of-diff quirks to their own issues; Phase 2c withheld the additive critic
findings; Phase 4a withheld the gaps no acceptance criterion needs; Phase 2/2b withheld the
surfaces and controls that were nice rather than necessary; **Phase 0.5 withheld the docs pages
no acceptance criterion needs** (the required ones were admitted to the ledger). **This is the
one place all of it is put to the human, and it is the only place.**

**Why here and nowhere else.** Late enough that the full set is visible and each item can be
priced honestly against a settled design; early enough that pulling one in costs a paragraph in
a Phase 2 layer plus an envelope re-measure, not a rewrite of a written document. And **once**,
because a rule that interrupts per finding gets the same answer eight times and stops being
read — the batch is what keeps the gate meaningful.

### The offer

If the withheld list is empty, say so in one line and move on — an empty list is the expected
outcome for a well-scoped PRD, not a sign the step was skipped.

Otherwise, **one `AskUserQuestion`, `multiSelect: true`**, one option per withheld item. Per
the interview card (Phase 1) every option carries its own rationale — and here the rationale is **symmetric by construction**, because
you are not arguing for these: each option's `description` names *what it adds*, *what it
costs* (files, lines, test mass, envelope impact), and *why it did not clear the bar on its
own*. **Do not mark a recommendation.** The recommendation is already on the record — you
withheld it, which is the "no" — and marking one here converts a restraint gate into a sales
pitch.

Keep it short. If the list runs past four items, the design added too much to describe: take
the four with the strongest case and record the rest as `withheld` without offering them. A
ten-item offer is the failure this phase exists to catch, not a thorough one.

### Act on the answer in the same run

- **Pulled in** → fold it into the relevant Phase 2 layer (and `ux-design.md` if it has a
  surface), re-run the **mockup gate** (Rule 4b) if it changes what the customer sees,
  re-measure the **envelope** in Phase 5.5 with it included, and mark it `pulled in` in the
  ledger. A pulled-in item is now part of the ask — it needs no further justification.
- **Not pulled in** → `withheld` in the ledger. **Do not file it as an issue** and do not
  re-raise it in `prd:plan` or `prd:implement`. The ledger row is its record; a human who
  wants it later has it in front of them.

### Headless runs make no offer

Under [`autonomous-drive.md`](../../../process/autonomous-drive.md) there is no
human attached. **Withhold everything on the list, record every item in the ledger, make no
offer, and take nothing.** Absence of a refusal is not an admission — a headless run that
adopts its own withheld ideas because nobody was there to say no has defeated the entire gate.
Note in the ledger that no offer was made (`withheld — headless run, no offer made`) so the
next reader knows the list was never seen rather than seen and declined.

---

## Phase 5.5: The envelope — one PRD must fit in one merge (HARD GATE)

**State the envelope here, and split here if it busts — not at plan time.** A PRD that
is too big is cheapest to fix now, while the only artifact is a design. `prd:plan`'s
Step 6.6 still checks the envelope, but by then a full task breakdown exists and
splitting means throwing it away, which is exactly the moment a gate gets waved through.

From the layer breakdown (Phase 2) and the order above, state one line in `design.md`:

```
Envelope: ~14 files, ~900 lines added, fits one run.
```

An estimate you would defend, not a number that makes the gate pass.

**Measure hand-written work only.** Generated output (everything `slot:codegen`
names) carries thousands of lines nobody authors or reviews — exclude it from the envelope
estimate, so a PRD touching a codegen source is not priced by output it never writes. The `prd:plan` Step
6.6 gate excludes generated output from both of its ceilings; this estimate must use the
same hand-written-only measure or the design-time and plan-time readings disagree.

**The envelope here is the per-PR ceiling — the whole PRD, all its runs.** Above ~40 files
or ~10,000 hand-written added lines, this is not one PRD. Split it. This is the
**reviewability** ceiling — `slot:planning-model` records the figure this repo
calibrated it against, so large PRDs stay visible as large without manufacturing a waiver
at plan time.

A PRD is **not** bounded per-run at design time. A PRD executes as one `prd:implement` run
per plan file, and **run survival is priced per plan file at plan time** — `prd:plan` Step
6.6 enforces the separate per-run ceiling (~2,000 hand-written lines per plan file), and a
run-ceiling bust is answered by splitting plan files, not by splitting the PRD. If this
design is so large it will split into siblings, that is a **PR-ceiling** bust and happens
here.

**Test mass stays off the table — under both ceilings.** Test mass is the dominant term in
every measurement of this repo's PRDs, and shaving it is not an acceptable response to
either ceiling. A tighter number is never licence to cut tests, and the next run must not
read a tighter number as permission to.

**Price frontend test mass at design time — don't guess it.** The envelope line above is a
hand-authored `~N files, ~M lines added`, and the term that decides whether a UI-bearing
PRD fits one merge is frontend test mass: the `playwright` row that `prd:plan` Step 4
mandates for **every user-visible AC and every new/changed UI surface** (plus the
design-fidelity AC and the `vitest` supplement for pure-function and store-logic
coverage). Those spec files are hand-written and count toward the ceiling — generated-output
exclusion does not touch them. Frontend test mass is the dominant term in every measured
PRD, and a design-time guess prices it ~2-3x **low**; that underpricing is precisely how a
PRD that should split at design time sails through this gate and only busts the per-PR
ceiling at plan Step 6.6, after a full task breakdown exists to throw away.

So when the design has any customer-facing surface, **enumerate frontend test mass, don't
eyeball it.** Count the user-visible ACs and the new/changed UI surfaces the frontend plan
will probe, and add a frontend test-mass line to the envelope — one `playwright` probe spec
(plus supporting `vitest`) per AC and per surface, priced at the **measured ~2-3x
reality factor** rather than the naive per-line estimate. A design that prices that term
honestly and still fits the per-PR ceiling is one that will actually stay whole; a design
that does not price it is deferring the split to plan time. If the priced total busts the
per-PR ceiling, **split here** — the backend/frontend seam (below) is the preferred cut
precisely because it isolates the test-mass-dominant frontend side into its own sibling
PRD.

### Why the PR ceiling is what it is — measured, not chosen

This design-time ceiling is the **reviewability** number: the cost of an oversized PR is
paid entirely by someone other than the author — the reviewer, the bisecting debugger, and
every PRD queued behind the merge. It is calibrated against what this repo actually merges
(0401, 0484, 0437 above), not against "what an agent could theoretically finish".

The **run-survival** ceiling — how long a run survives — is a separate number, priced
**per plan file** at `prd:plan` Step 6.6, not here. A fleet daemon restart — any deploy, any
maintenance — issues a graceful stop, and the  drain only nudges a run toward its
**ship step**. A run that is hours from shipping cannot be drained to anything, so it is
stopped and everything but a salvage branch is discarded.

PRD 0486 is the worked example: **22 tasks, 19 ACs, 146 files, +12,915 lines.** Its final
run died at **2h44m / 168 tools** to a daemon restart, having made no progress for the
last four minutes. That happened **six times in two days** — none of them a failed attempt
(each was correctly logged `operator stop, freed for retry (no attempt consumed)`), so no
retry cap ever fired and no human was ever asked. It blocked 8 issues throughout.

**The run-survival question is therefore not "can an agent do this?" but "does this plan
file finish before something restarts the daemon?"** A plan file near its ship step
survives a restart. One 22 tasks deep never is. That question is answered at plan time,
against each plan file; at design time it is folded into the PR estimate only insofar as a
PRD too large to ever finish as one merge is already over the PR ceiling above.

### Splitting: siblings, not increments

**If it needs to land in more than one merge, it is not one PRD — it is a slice with
several.** Do not invent increments inside a PRD:
[`knowledge-model.md`](#)'s master rule already
settles this — a tier holds at least two of the tier beneath it and adds a completion
condition its children lack — and a PRD ships **atomically** (`status: shipped` rides the
merge, [`autonomous-drive.md`](../../../process/autonomous-drive.md) Rule F), so
"a PRD that merges three times" has no representation in the status model at all.

So: cut the work into 2–4 **sibling PRDs under the same slice**, each one
independently shippable and independently useful. The seams that work, in order of
preference:

1. **A vertical slice a customer can use** — the walking-skeleton cut. First PRD runs one
   real thread end to end; the rest widen it.
2. **A contract boundary** — the PRD that lands the API/schema/proto surface, then the
   PRDs that consume it. The first unblocks the others in parallel.
3. **Backend / frontend** — only when the backend genuinely ships something usable alone
   (an API another surface already consumes). Never a bare "backend now, UI later" split:
   that manufactures the stranded-backend failure CLAUDE.md's golden rule forbids.

Each sibling gets its own row, its own `Verified by`, and its own envelope line. Wire
`blockedBy` between them so the fleet runs them in dependency order rather than racing.

**What is NOT a legitimate reason to skip the split:** the design is already written; the
work "feels cohesive"; the tasks share files. Sharing files is an argument for *ordering*
the siblings, not for merging them into one un-shippable lump.

If it genuinely cannot be cut — one indivisible migration, a single generated artifact —
say so **in the envelope line itself**, naming what makes it indivisible. That is a
recorded, arguable decision rather than a silent default.

---

## Phase 6: Output

Save the design document to `knowledge/prds/NNNN`. It **must** open with
the `prd-design` frontmatter header below — [``](#)
requires it, and a missing header fails `make validate-knowledge` (: this was
being omitted intermittently, breaking the Knowledge Validators CI gate for unrelated PRs):

```markdown
---
type: prd-design
---

# Design: <feature name>

## Summary
<1 paragraph: what, who, why — from PRD>

## Vision alignment
- Persona: <from PRD>
- Core loop step: <from PRD>

## Layers affected
<one line per layer `slot:architecture` names, Yes/No>

## Docs impact
<from Phase 0.5 step 5 — for every capability an AC commits: the pages created or changed,
each by page id via `slot:docs` (never a literal path), its audience, its page kind, and the
journey that verifies it. Required pages (an AC needs the customer to follow them) are admitted
in the Scope ledger; any page beyond that was offered once at Phase 5.4 and recorded there.
`none — <why the capability is internal>` is legitimate; a customer-facing capability with an
unreasoned `none` is not. When `slot:docs` is unfilled, say so and write
`docs_impact: unknown` — no docs gate runs at verify (the slot's degrade).>

## Architecture notes
<from Phase 1.5 — every quirk found, with the user's chosen disposition (Fix now / Defer / Perpetuate) and rationale. Also list any approved deviations from existing patterns. **This section is this PRD's decision record** (the generated ledger indexes it), so each fork settled here names the option refused and its reason.>

## Commitments
<from Phase 4c — the requirement rows this design **added** or **superseded**, IDs only (the
row is the assertion, never repeated here), plus the PRD's refreshed `implements:`. Write
"none — <the candidates examined>" when the design settled no durable commitment; an empty
statement with no candidates is the un-backed conclusion Phase 4c forbids.>

## Integration trace
<for integration / capstone PRDs (Phase 1.6): the central end-to-end flow with each hop cited to the `file:line` that executes it in `main` today; any un-citable hop listed as a Gap below. Omit only if Phase 1 shows this PRD introduces a net-new mechanism rather than composing already-shipped ones.>

## Design details
<per-layer details from Phase 2>

## Reuse
<table from Phase 3>

## Gaps & Improvements
<both lists from Phase 4>

## Scope ledger
<from Phase 5.4 — EVERY addition beyond what the PRD asked for, admitted and withheld alike.
One row each; the `Basis` for an admitted row names the AC that cannot pass without it, or the
already-edited file whose written-rule violation it fixes. `none — <what was considered and
cleared the ask>` is a legitimate and expected value; an empty section is not. **Rows are
additions, never decisions** — the dozens of forks this design settled about *how* to build the
asked-for thing belong in *Architecture notes*, not here. Blocking gate:
`make validate-knowledge`.

| # | Addition | Disposition | Basis |
|---|----------|-------------|-------|
| 1 | <what would exist that the ask never named> | admitted | AC-3 cannot pass without it |
| 2 | <...> | withheld | offered YYYY-MM-DD, not pulled in |
| 3 | <...> | pulled in | human pulled it in at the Phase 5.4 offer, YYYY-MM-DD |

## Implementation order
<from Phase 5>

## Acceptance criteria
<from PRD + layer-specific criteria — split out any AC achievable only in another repo per
`` → "Cross-repo scope"; never list it here>

## Delivery notes (cross-repo)
<name each companion repo, the exact AC(s) it delivers, and its tracking issue (filed under Rule
G — `Type:task`, `repo:<lane>` label). Omit only if every AC is buildable and mergeable from this
repo alone.>

## Next steps
`/fleet:prd:plan NNNN` produces the implementation plans. **This command dispatches it itself**
(Phase 8) rather than asking a human to — the line above is what `design.md` tells a human
reader, not a licence for the command to stop here.
```

If a UX design was produced, note: "UX design saved to `knowledge/prds/NNNN`."

## Phase 6.5: Journey & Capability Coverage (MANDATORY — do NOT skip)

Design defines the customer's end-to-end experience, so it owns keeping the **journey catalog** and the **feature capability map** honest. In the **same commit** as `design.md`:

1. **Journeys.** For every capability this PRD ships, ensure a journey/flow in [`knowledge/journeys/`](../../../../knowledge/journeys/) **tests** it. Enrich the closest existing flow first — **"with/without X" variants are dispositioned AC rows inside one flow, never new files** (find the *minimal* meaningful set; don't proliferate flows). Add a new flow/map only for a genuinely new reusable job. Each flow/map declares `covers: [<ID>, …]` for the capability ids it exercises.
2. **Feature map.** Update [`knowledge/features/<area>.md`](../../../../knowledge/features/) so each capability's **Tested by** cell points at that journey/flow (and **Ships in** at this PRD). An empty *Tested by* is a coverage gap the design must close or explicitly defer with a reason.
3. **Restate as ACs.** Each journey this PRD owns becomes an acceptance criterion; a UI capability's AC is browser-verifiable (Phase 2.12 / the Playwright probe).

If the feature area has no capability map yet (`/fleet:prd:create` Phase 5 should have created it), create it now per [``](#).

## Phase 7: Flip PRD status to `designed`

**Gate — `implements:` may not be empty, and no claimed row may still be `open`.** Check both
before writing anything, and refuse the flip rather than flipping with a caveat:

- **Empty `implements:` where a register covers this PRD's ground** is not "this PRD realises
  no commitments" — it is *nobody looked*, and the two are indistinguishable to every
  downstream gate, which is exactly why autonomy stalls here. Resolve the ground through the
  `## Component index` in [`requirement-status.md`](#) (rendered on demand and never committed, so run `python3 knowledge/scripts/gen_requirement_status.py` first);
  if a register covers it, Phase 4c owed you claims. Go back and write them.
  (Genuinely uncovered ground is legal *only* after Phase 4c step 8 — you opened the register.)
- **A claimed row still carrying `Disposition: open`** means a promise this design is building
  was never settled. Settle it (Phase 4c step 7) or drop the claim; do not flip past it.

`make validate-knowledge` enforces both from `designed` onward, so a flip that skips
this fails the commit rather than the review.

In the **same commit** as `design.md`:

1. In `knowledge/prds/NNNN` frontmatter, set `status: designed` and append `- { state: designed, at: < timestamp>, by: design }` to `status_history:`. Only advance from `prd-drafted`; if already further along, leave it (a re-run just refreshes the design).
2. **If `prd.md` has no `## In Plain Words` section, write one now** — as its first section, above `## Vision Alignment`. PRDs authored before that convention existed don't have it, and this command is the first pipeline stage after `create` that reads the whole PRD, so it is where the gap gets closed. 2–5 plain-language paragraphs plus one concrete example, per [``](#) → "`## In Plain Words` is what the tracker shows". Write it from the **PRD**, not from the design you just produced: it says what the user ends up able to do, never how it is built. Until it exists the tracker issue shows an auto-derived stand-in, which is a placeholder, not a summary.
3. Nothing to stage for the roadmap: `` is generated on demand and **not committed** (it is gitignored — it took 133 commits in 14 days and conflicted by construction), and reads status live from the frontmatter flip above. Regenerate it with `python3 knowledge/scripts/gen_roadmap.py` when you want to read it.

**Tracker: no live mirror — the fleet projects it.** Do **not** mirror to the tracker from this command; design is a drafting-stage transition and those are **projection-only** (see [``](#) → its tracker-sync section). Once this commit reaches `main`, the `prd-projection` pass of the fleet's `corpus-sync` loop (`fleet-service`) re-projects the Issue within the sync's interval and keeps it in **Needs Plan** (`designed`). Note the Issue carries the PRD's `## In Plain Words` summary + a pointer footer **only** — `design.md` is *not* folded into the description (it is listed in the footer as a path). Never read tracker state back.

---

## Phase 8: Dispatch the plan — do NOT stop and wait

**When the design lands and nothing is blocking, start `/fleet:prd:plan NNNN` immediately, as
a background sub-agent. Do not end the turn by telling a human to run it.**

The design is finished the moment `status: designed` is committed. Everything `prd:plan` needs
is then on disk — `prd.md`, `design.md`, `ux-design.md`, the claimed requirement rows, the
approved mockup. Handing that back as a suggestion buys nothing and costs a human round-trip on
work with no open question in it. The pipeline's job is to keep moving; a stage that stops
because the *next* stage exists is a stall wearing a handoff's clothes.

**Dispatch it as ONE sub-agent, not a fan-out.** Every step in `prd:plan`'s spine is
`actor: coordinator`, and two of them — `cross-plan-deps` and the two-ceiling `envelope-recheck`
— need the backend and frontend plans in one head. Splitting backend and frontend across
independent agents breaks the command's own gates. Fan out only where a command's spine actually
declares `actor: subagent`.

**Brief it properly.** A background agent has no human to ask, so the dispatch must carry:

- the input paths, and an instruction to read `prd:plan`'s command file **in full** and follow it;
- **every sequencing constraint the design discovered** — especially anything that must land in
  one plan file because splitting it opens a window of broken behaviour. This is the design's
  knowledge and the plan cannot re-derive it;
- the envelope numbers, and which ceiling applies (per-PR here, per-plan-file there);
- which requirement rows are claimed, and any deliberately **not** claimed, so the hard
  `requirement-cover` gate is not fought;
- **no interviews** — it must settle its own forks, record the call and its rationale in the
  plan, and write down anything genuinely undecidable rather than stalling;
- the branch + PR + arm-auto-merge + watch-to-merged loop, and the "never hand-merge a generated
  file" rule.

**Do not dispatch when something real is blocking**, and say which:

- the mockup approval gate is open (no `AskUserQuestion` approval on record);
- the red-team panel did not run, so a hard gate is open;
- a claimed requirement row is still `open`, or `implements:` is empty on covered ground;
- the design depends on a sibling PRD that has not shipped, and planning against it would plan
  against a contract that does not exist yet;
- the design PR is still open **and** the plan would conflict with it beyond the generated
  ledgers — otherwise branch from the design branch and say so.

Report the dispatch in the closing summary: what was sent, and what it is blocked on if it was
not sent. A dispatch that did not happen is a fact to state, never a silence.
