---
type: spec
---

# Design-Fidelity Loop (making UI look *good*, not just conformant)

This spec is the process contract that stops the product shipping UI that is **functional
but looks bad**. It carries one taste bar across the whole PRD pipeline —
`design` → `plan` → `implement` → `verify` — and backs the human-judgment gate with
a mechanical regression net.

It does **not** restate the rubric: the checkable taste rubric is single-sourced in
the **`audit-profile`** slot's UI checklist §1b (`Q1–Q6` + the holistic pass),
and the design-system standards live in the **`ui-contracts`** slot. This spec owns the
three things that rubric alone never gave us: a **reference** above our own average,
a **build-time loop** that fixes to the bar instead of grading once at the end, and a
**visual-regression baseline** so drift is caught by a diff, not an eyeball.

---

## Why UI ships bad (the failure mode this closes)

- **Distributional convergence.** An LLM predicts the statistically-safe token, so
  unguided UI regresses to the training-set mean: even spacing, no density decisions,
  no hierarchy, generic cards, no *finish*. The output isn't randomly bad — it is
  systematically **average**, and average passes every lint rule.
- **Conformance ≠ craft.** The repo's UI lint gates (`slot:ui-contracts` names them,
  `no-side-panels`, page-specs, tokens) enforce that a page is built from the *same*
  parts everywhere. That is necessary and we are good at it. It is also structurally
  blind to "sparse, unfinished, ugly" — the UI contract `slot:ui-contracts` names concedes it: *"A page that passes
  every V\* and still looks bad is the exact failure."*
- **The gate was one-shot and late.** Before this spec, the only pre-ship taste
  judgment was `verify` Step 4 (a single LLM eyeballing finished screenshots) and the
  **post-ship** `ui`/`ux` audit (which files tickets, doesn't block). A one-shot
  generator can't converge; **a loop can.** Nothing fixed *to* the bar during the
  build.

Three axes, kept distinct — do not conflate them:

| Axis | Question | Mechanism |
|---|---|---|
| **Consistency** | Uses the design system? | lint + tokens + page-specs (already strong) |
| **Drift** | Did a change break the look? | **visual-regression baselines** (§4) |
| **Craft / taste** | Looks *good* from scratch? | **reference (§1) + bar (§2) + build loop (§3)** |

---

## 1. The reference — beat the mean (design stage)

Distributional convergence is broken by a **target above our own average**. A mockup
built only from our own tokens has our own taste as its ceiling; "match this" beats
"make it nice".

**Every UI PRD names ≥1 concrete high-craft reference before any mockup is drawn.** A
reference is a *real, rendered* surface we would be proud to be mistaken for — a
screenshot of a specific page from a product with strong craft (the tracker, Vercel,
Stripe, Height, an internal exemplar page that already clears the bar), chosen for the
same archetype (list / detail / settings / cockpit) as the surface being built. Store
it in the PRD's mockups directory (alongside the round mockups from `prd:design`
Phase 1 Step 0) as `reference-<archetype>.png`, plus a one-line note on *what* about it
is the target: density, rhythm, restraint, hierarchy.

The reference is not a license to abandon our design system — tokens, components, and
the archetypes `slot:ui-contracts` names still bind (§ styling discipline in `prd:design` Phase 1
Step 0). The reference sets the **craft ceiling**; the system supplies the **parts**.
The mockup, the build loop (§3), and the verify gate (§ verify Step 2b) all measure
against this reference *and* the bar.

---

## 1.5 The mockup — substrate, and the human approval gate

The reference (§1) sets the ceiling; the **mockup** is the concrete thing we commit to
building. Three rules govern it, and each exists because its absence cost us real
rework.

### 1.5-0 The mockup lives IN THE REPO. An external artifact is a viewer, never the mockup.

**Every mockup MUST exist as a local HTML/CSS file committed under the PRD's
`mockups/` directory. That file is the design contract.** A published/hosted artifact
(a `claude.ai/code/artifact/…` URL, a screenshot pasted in chat, a link in the tracker
comment) is a **delivery mechanism for the human approval gate (§1.5b) and nothing
else**.

**Why this is a hard rule: the people who implement the design cannot open the link.**
A fleet implementer runs headless in a checkout. It has the repo and nothing else — no
browser session, no access to the authoring session's published artifacts, no way to
authenticate to whatever hosted them. A `plan` or `implement` step whose fidelity
target is a URL has a target it can never read, so it does one of two things, both
bad: it builds from the prose description alone (and the mockup did no work), or it
parks on a reference it cannot resolve. The same applies to a human picking the PRD up
six months later, when the link has rotted or the workspace has changed hands.

Consequences, all mandatory:

- **Publish only after the file is committed** — or in the same change. Never publish a
  mockup that exists solely in a scratchpad.
- **Every citation of a mockup in `ux-design.md`, `frontend-plan.md`, an acceptance
  criterion, or a page-spec is a REPO-RELATIVE PATH.** A hosted URL may appear
  *alongside* it as a convenience for the human, never instead of it. An AC that cites
  only a URL is malformed.
- **The approval record names the file, not the link** (§1.5b step 4). "Approved:
  `mockups/round-01-<theme>/index.html`, " — the URL is optional trailing
  context.
- **Self-contained, like the artifact rules require anyway** — inline CSS, no CDN, no
  remote fonts or images. A mockup that renders only online is not in the repo in any
  meaningful sense.

This rule is upstream of the tier split below: **both** tiers are in-repo. Explore is
in-repo HTML; Lock is in-repo React. Neither is ever a hosted link.

### 1.5-0d The RENDER is not an artifact — never commit a mockup screenshot

The rule above says the committed HTML **is** the design contract, and that everything
else is "a delivery mechanism for the human approval gate and nothing else". A PNG
render of that HTML is exactly such a delivery mechanism. **Present it, never commit
it.** Under a PRD's `mockups/` directory the only committed raster is
`reference-<archetype>.png`.

**Why this needed saying.** Nothing forbade committing the render, so we committed all
of them. Measured :

| under `knowledge/prds/**/mockups/` | files | size |
|---|---|---|
| PNG renders | 268 | **41.8 MB** |
| the HTML they are renders **of** | 185 | 3.9 MB |

The views outweighed the contracts they depict by ~11×. And **none of them was ever
displayed**: a tree-wide scan for markdown image embeds (`![…](….png)`) across all of
`knowledge/` returns zero. They were write-only — rendered to show a human at the
approval gate, committed out of habit, then never read again.

**The one carve-out is the whole distinction.** A `reference-*.png` (§1) is a screenshot
of *another product's* surface — Linear, Vercel, Stripe. Nothing here regenerates it,
deleting it destroys the craft ceiling permanently, and
`make validate-knowledge`'s mockup-reference rule requires it. A round render is its opposite on every
axis: reproducible from the sibling HTML, on demand, forever. Keep the irreplaceable
one; regenerate the reproducible one.

**Consequences:**

- **Show the render at the gate** (§1.5b step 1 still requires posting images inline —
  a human must *see* the design). Render it, present it, let it go. Publishing a hosted
  copy is still the right move for getting it in front of someone.
- **Cite the HTML, not the PNG.** An approval record, AC, or plan names
  `mockups/round-01-<theme>/index.html` — the file that regenerates every view of it.
- **A historical record naming a removed render is not a broken reference.** The round
  directory and its HTML still identify exactly which design was approved; only the
  pixels are gone. Do not rewrite shipped approval records to erase the artifact that
  was actually approved.
- **Enforced** by `make validate-knowledge`, ratcheted against its own baseline of
  grandfathered renders.

**The baseline is design debt, not an exemption.** It grandfathers renders that are the
*only* artifact their PRD has — a `mockups/` directory holding screenshots and no HTML
at all. That missing HTML is itself a §1.5-0 violation: the mockup was never committed
as a file, so the render cannot be regenerated and deleting it would destroy the sole
surviving record of the design. The fix is to land the HTML, at which point the render
goes with it and the baseline line is removed. The baseline may only shrink.

### 1.5a Two-tier substrate — HTML explores, React locks

| Tier | Substrate | Purpose |
|---|---|---|
| **Explore** | standalone `mockups/round-NN-<theme>/index.html` | cheap divergent rounds — 2–3 layout directions, thrown away. Hand-copied tokens are acceptable *here only*, because nothing downstream is held to them. |
| **Lock** | a **real fixture page** in the product's own component substrate — `slot:ui-contracts` says how one is mounted here | the round the human approves. Real catalog components (`slot:ui-contracts`), real tokens (`slot:ui-contracts`), real shell. Screenshot by the harness `slot:ui-contracts` names. |

**The approved round MUST be promoted to the Lock tier before design completes.** An
HTML mockup cannot be clicked, cannot surface a real component's constraints, and its
tokens are a frozen copy that silently rots — two plans declared a brand token under a
comment claiming it was verbatim, months after the real token file had moved on. A mockup
whose colors are a lie is not a design contract.

The Lock-tier pattern has two halves, and both are the repository's answer, not this
document's — `slot:ui-contracts` names them:

- **A dev-only route** in the real app shell, so the fixture inherits the real navigation
  and header, **compiled out of the production bundle** — lazily loaded, so that a static
  import cannot keep it in the shipped entry graph. That is exactly the "mockups bloat the
  shipped app" objection this pattern must stay clear of.
- **A screenshot harness** (`slot:ui-contracts`) that renders the route
  against a mocked API at a fixed viewport, with no backend up, and registers the route
  with whatever warm-up the harness keeps.
- **Fixtures inline** in the fixture page — no dev-tool imports at runtime.

This is *not* the "mockups in the production web dir" pattern that was rejected in
June 2026: that objection was to **shippable** surface. A dev-only, lazily loaded route is
compiled out of the production bundle.

### 1.5b The human approval gate — a model critique is not an approval

**The human must see the mockup and say yes before design completes.** This is a
`kind: gate`, `actor: user`, `gate: hard` spine step producing the `mockup-approved`
artifact (`command-spine.md` §Invariants 3b, mechanically enforced).

Why this is its own rule rather than a line in §2: for months the pipeline had a
rigorous model-graded fidelity loop and **no human gate at all**, while `prd:design`,
`prd:implement`, and `prd:verify` each referenced *"the approved mockup"* — an
artifact no step produced. The bar (§2) proves *something graded it*. Only this gate
proves *the human saw it*. They are not substitutes.

The gate's shape (do not collapse these into one message):

1. **Render and present.** Screenshot the Lock-tier page at 1440 in every meaningful
   state and post the images plus the live `DEV` URL. Never hand over a file path and
   call it shown — a path is not a presentation. **Presenting is not committing:** the
   in-repo file must exist too (§1.5-0). Publishing a hosted copy so the human can
   actually look at it is encouraged and is the *only* legitimate use of one.
2. **Invite reaction first.** Ask an open question — *"anything off in the layout or
   shape before we lock it?"* — and **wait**. Do not attach a multiple-choice in the
   same breath: forcing options collapses the mockup into background context for a
   decision the human never got to challenge. (This is the PRD 0016 failure:
   *"where in the process did you ever ask me about the mockups?"*)
3. **Iterate on pushback**, 2–3 rounds max, re-presenting each time.
4. **Record the approval** in `ux-design.md`: which round, **the repo-relative path of
   the approved mockup file**, which fixture route, the date, and any conditions
   attached. That record is what `plan`, `implement`, and `verify` bind to — and all
   three run headless with only the repo, so a record that names a hosted URL instead
   of a path binds them to nothing (§1.5-0).

**Never self-approve.** If the command is running with no human available, it does not
get to skip the gate — it stops with the mockup presented and the gate open. An
un-approved mockup is a blocked design, not a design with a caveat.

### 1.5c Scope — the gate protects *surfaces*, not every field that lands on one

§1.5a/§1.5b apply to a **new or materially-changed surface**: a new page or route, a
restructured layout, a new interaction model, a new primitive. They do **not** apply to a
change that is purely **additive to a page that already shipped** — one read-only field, a
status badge on an existing row, a sentence under an existing card.

This is a scope rule, not a loophole, and it was added because the absence of one had a
cost of its own: PRD 0426's surface is a single read-only posture badge on an existing
integrations row, and the only way to plan it was to build a `DEV`-gated fixture page in
the product tree for one badge. That is the gate charging surface-sized ceremony for a
field-sized change — and when the fixture was (reasonably) declined, the PRD could not
reach `planned` at all. A gate that blocks correct work teaches people to route around it.

**The instrument for an additive change is the page-spec, not a mockup.**
`<Page>.spec.md` is already the durable, in-repo, headless-readable contract for a shipped
surface (the UI contract `slot:ui-contracts` names, ``), and it is where an additive change belongs
anyway. So a `frontend-plan.md` may stand without an `## Approved design` record **iff**:

1. it carries the heading **`## Surface scope: additive to an existing surface`**,
   asserting no new route and no new page;
2. it cites the target page's `<Page>.spec.md` by repo-relative path as its fidelity
   target — and that spec is **updated in the same change** to carry the new element's
   layout slot, states and canonical-choice rule; and
3. the `playwright` verification row stays mandatory, exactly as for any other UI plan.

**Checked, not trusted.** `make validate-knowledge` enforces all three, and closes
the obvious dodge: the cited page-spec must **exist** and must **predate the plan in git
history**. A spec authored in the same change as the plan describes a page that is new,
so the mockup gate applies to it in full. Same-day (equal date) fails closed.

An Explore-tier mockup round is still worth committing for an additive change when the
element's shape is genuinely open (0426 has one, and it is what the page-spec update was
written from) — it is simply no longer a *gate*, because there is no new surface for a
human to be shown.

---

## 2. The design-fidelity bar — the shared acceptance bar

One bar, referenced by every stage. A surface **clears the bar** when all of the
following hold in a real 1440 render (+ its empty / loading / error states):

1. **Reference fidelity.** The surface reads as a sibling of the named reference (§1)
   — comparable density, rhythm, and finish — not a generic default.
2. **Information design — `Q1–Q6`** (the **`audit-profile`** slot's UI checklist
   §1b, the canonical list): no dead canvas (`Q1`), no value-as-label (`Q2`), every
   number earns its place and drills in (`Q3`), human-first identifiers (`Q4`), no
   redundant adjacency (`Q5`), complete header (`Q6`).
3. **Surface hierarchy.** One dominant surface; Flat/Raised/Internal correct; no cards
   -in-cards, no nested bordered shells (the UI contract's surface-hierarchy rule).
4. **One primary action per view**, placed where sibling pages place it; dialog footer
   cancel→primary (`V6`).
5. **Scale discipline.** Spacing on the 4/8 scale, ≤3 type sizes from the `--text-*`
   tokens, motion on-scale (≤300ms) with `--animate-*` only, tokens (never raw
   palette/hex) everywhere (`V3`/`V4`/`V12`). This is the craft floor lint half-covers.
6. **Holistic — would a designer ship this?** Look at the whole 1440 screenshot and
   answer honestly. Gestalt "reads as unfinished" is a legitimate fail even when no
   single row above catches it (the UI checklist `slot:audit-profile` names, holistic pass).

This is the **same** bar the post-ship `ui` audit grades against — by construction, so
pre-ship and post-ship never diverge. `plan` turns it into acceptance criteria (§ plan
Step 4); `implement` fixes *to* it in the loop (§3); `verify` gates on it (Step 2b/4);
`audit` re-runs it as a fresh-eyes pass.

---

## 3. The build-time critique-and-fix loop — the core (implement stage)

The single highest-leverage change: fix *to* the bar **during the build**, not once at
the end. Runs in `prd:implement` Phase A2d for every UI surface the PRD adds or
changes, before that surface is considered done. The coordinator orchestrates it like
the Phase-C fix loop; the browser sub-agent produces the critique, fix sub-agents close
the defects.

For each surface, `MAX_LOOP = 4`, `round = 0`:

1. **Render** the surface live at 1440 in each meaningful state (empty / loading /
   error / populated) against real seed data.
2. **Screenshot** each state.
3. **Critique** the screenshots against, in priority order, the **approved mockup
   (§1.5)**, the **reference (§1)**, and the **bar (§2)**. Feed a vision-capable agent
   **the approved mockup's own screenshots first** — it is the design the human signed
   off on and therefore the primary target — then the reference and the bar. Have it
   emit a **ranked, concrete** defect list, highest-impact first, with
   *divergences from the approved mockup ranked above generic taste defects*:
   *"mockup groups the four stats in one strip; shipped page stacks them in separate
   cards", "hero card is ~60% empty at 1440", "three type sizes in the header",
   "primary CTA is a ghost button lost against the toolbar"* — not "make it nicer".

   **Do not critique against the reference alone.** The reference is a third-party
   surface chosen for its craft ceiling (the tracker, Stripe); the mockup is what we
   actually agreed to build. A loop that optimizes toward the reference while ignoring
   the mockup will converge on something defensible that nobody approved — which is
   precisely how "the implementation just ignored the design" happens, and it is not a
   discipline failure but an input-set failure.
4. **Fix the single highest-impact defect.** One at a time — a loop converges; a batch
   of simultaneous edits doesn't, and can't attribute the improvement.
5. **Re-render, re-screenshot, re-critique.**
6. **Exit** when the critique clears the bar, or a round fixes zero defects, or
   `round == MAX_LOOP`.

**Bound + escalation (never loosen the bar to exit).** If a surface can't clear the bar
in `MAX_LOOP` rounds, that is a **design** gap, not an implement gap — the loop found
that the approved mockup/reference under-specifies the surface. Record it (autonomous:
Decisions Log; manual: raise it) and route the residual to a follow-up
(`` or a `/fleet:task:create`). Do **not** ship bad-but-done, and
do **not** widen the bar to make the loop terminate. This is the aesthetic analogue of
the bug-fix discipline's "never loosen the failing assertion".

---

## 4. Visual-regression baselines — mechanical drift (implement + verify + CI)

The bar (§2) and the loop (§3) make a page *good*; baselines keep it good. They are
**not** the taste fix — pixel diffing catches *drift* ("this button grew 4px and broke
the row"), never *ugliness* ("this was always bland"). Their second value: a **diff
image** is a concrete artifact a vision agent can reason about, which beats asking an
LLM to spatially compare two screenshots in its head.

- **Mechanism.** The screenshot harness `slot:ui-contracts` names, with
  baselines committed to git and configured for determinism (animations disabled, caret
  hidden, a small pixel-ratio tolerance); mask dynamic regions (timestamps, seeded ids)
  rather than disabling the assertion.
- **Placement (matters — read before wiring the first one).** A baseline assertion belongs
  in a **self-contained spec per surface** (navigate → seed → assert the shot), kept
  **out of** any intentionally-serial, order-dependent end-to-end flow — a fidelity
  baseline must not depend on what an earlier flow left behind. The browser *probes* the
  verify pass drives are a different tool and cannot make this assertion. Standing up that
  spec harness (seed + routing per surface) is the one piece the harness config does not
  supply; the first plan to adopt it establishes the pattern.
- **When a baseline is written.** Only once a surface has cleared the loop (§3) — the
  baseline captures the *good* state. `implement` A2d commits the baseline PNG with the
  surface. **Never regenerate a baseline to make a diff pass** — a red diff is either a
  real regression (fix the code) or an intended change (update the baseline
  *deliberately*, reviewing the diff first).
- **Where it runs.** The `implement` browser pass and CI compare against the committed
  baseline; `verify` treats an unexplained diff as a defect for that surface. On
  failure, feed the agent the generated diff image, not the raw test log.
- **Scope, honestly.** Baseline the PRD's *own* new/changed surfaces, not the whole
  app — silent full-coverage is a lie. Log which surfaces got baselines and which were
  skipped and why.
- **Baselines are platform-specific — never commit the ones your laptop generates.**
  Committed baselines are the ones CI's runner platform produces. Running the suite on a
  different platform finds no baseline for it, **writes one, and fails that run**; the
  next run then passes against the file it just invented. So a local red-then-green is
  not a fix, and the locally generated baseline files are junk — delete them before
  committing (`slot:ui-contracts` names where they land).
- **The gate is blind to small glyphs — pin those with a unit assertion instead.**
  `maxDiffPixelRatio: 0.01` over a 1440x900 viewport is a 12,960-pixel budget, so
  anything smaller than roughly **114x114px** cannot fail this gate no matter how
  wrong it renders. Measured: a 14px marker glyph moves 52 pixels — ~250x under
  tolerance — so  (its gradient rendering fully transparent) was invisible to
  the baselines in *both* directions, before and after the fix. A baseline therefore
  never proves a small glyph is correct; assert the glyph itself in a unit test.
- **Do not baseline a Lock-tier mockup fixture** (§1.5a). A mockup is iterated on
  purpose; a regression gate over it goes red for every design round, and the mockup
  has no product behavior to regress. Mockup specs *capture* screenshots for the
  approval gate (§1.5b) and assert the surface rendered without console errors. The
  §4 baseline belongs to the **real** surface, written in `implement` A2d once it has
  cleared the bar. `slot:ui-contracts` names a worked example where the repo has one.

---

## 5. Where each piece acts (pipeline map)

| Stage | Command | Owns |
|---|---|---|
| **Design** | `prd:design` Phase 1 Step 0 | Name the **reference** (§1); mock against it; promote the chosen round to the **Lock tier** and carry it through the **human approval gate** (§1.5); the mockup must clear the **bar** (§2). |
| **Plan** | `prd:plan` Step 4 | Emit the **bar** as browser-verifiable acceptance criteria — one design-fidelity AC per UI surface, citing **the approved mockup** and the reference. |
| **Implement** | `prd:implement` Phase A2d | Run the **build loop** (§3) to convergence **against the approved mockup first**; commit **visual-regression baselines** (§4) for surfaces that cleared it. |
| **Verify** | `prd:verify` Step 2b/4 | Gate on the **bar** vs the **approved mockup** and the **reference**; a material fail FAILs the surface; unexplained baseline diff = defect. |
| **Page work** | `page:improve` | Same chain at page scale: mock the change, get it approved, fix to the bar. |
| **Audit** | `audit ui` / `audit ux` | Post-ship fresh-eyes re-run of the **same bar** (the UI checklist's holistic pass) over the journey. |

The taste standard is defined once (§2 + the UI checklist's holistic pass) and applied at
every stage — so a surface cannot pass the build loop against one bar and fail verify
against a different one.

**The approved mockup (§1.5) is threaded through every stage below design.** It is an
input to the plan's ACs, to the build loop's critique, and to the verify gate — not a
document that gets written once and consulted last. The single most common way UI work
goes wrong here is not that someone disobeyed the design; it is that the design was
never placed in front of the thing doing the building.
