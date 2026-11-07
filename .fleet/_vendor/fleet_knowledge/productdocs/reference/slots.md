---
title: "Slots"
kind: reference
for: [everyone]
summary: "Every question a command asks a repository, whether it is required, and who answers it."
sources:
  - packages/fleet-knowledge/src/fleet_knowledge/slot-questions.json
generated: true
---

:::lede
Every question a command may ask a repository about itself. Use it to see which answers your repository owes, and what a command does when one is missing.
:::

A repository answers its own in `knowledge/slots/`; the shared ones ship with Fleet's command tier, the same in every repository. A command refuses to run without a required answer, and an optional one it lacks degrades as the last column says.

## Your repository answers

| Slot | The question it answers | Required | If it is missing | Commands that use it |
|---|---|---|---|---|
| `gate` | How to run lint, build and tests here — by named key — and what green means. | required | — | 36 |
| `git-workflow` | Branch names, who merges, which checks are required, how a PR silently fails to merge. | required | — | 33 |
| `commitments` | What this product has already promised — the input to a scope verdict. | required | — | 20 |
| `decisions` | The forks this project already took — the option chosen, the option refused, and the reason — so a later change cannot silently reverse one. | optional | A design or a triage verdict is made with no record of what was already refused, so a settled fork is reopened and the rejected branch ships as if it were new. | 8 |
| `feature-areas` | The closed set of feature areas an issue can be filed against, and how each maps to the tracker's project for it. | required | — | 20 |
| `languages` | Which language contracts apply, and therefore which implementation lanes run. | required | — | 20 |
| `planning-model` | The planning hierarchy, the durable-vs-versioned rule, the PRD state machine. | optional | The PRD lifecycle commands do not run; bug/task work is unaffected. | 29 |
| `entity-model` | Where each planning entity lives in this repository (the file, register or tracker project for each rung of the shared planning ladder) and local worked examples. What each entity IS, and the order to test for it, ships with the tier as `process-planning-ladder`. | optional | The classifying commands (route, intake, check) still walk the shared planning ladder, but cannot name where each entity lives here or give local examples; the commands that author an entity require it. | 22 |
| `product-vision` | What this product is for, and what differentiates it — the input to a PRD's framing. | optional | prd:create cannot run; nothing else is affected. | 19 |
| `components` | The structural map, for the Component label and path attribution. | optional | The Component label is skipped rather than guessed. | 24 |
| `programs` | The program register and each program's own narrative — the authored rank work inherits, the bar a program is proved against, and the record of what each delivery cycle did. | optional | The Program label is the literal `none`, and a program has nowhere to carry its bar or its delivery log. | 17 |
| `codegen` | What is generated here and which command regenerates it. | optional | No regeneration step runs in the wave gate. | 11 |
| `ui-contracts` | Page structure, the detail-page contract, the taste bar. | optional | The UI conformance gate is skipped. | 13 |
| `mockup-conventions` | Where mockups are written in this repository, which of the two tiers it can mount, how a state is addressed and a flow clicked through, and the design guidelines a mockup here must follow. | optional | The mockup command still runs every generic rule in `process-design-fidelity` — the reference, real tokens, a rendered critique and a human gate — but it has to ask where the files go and cannot promote a round to the product's own components, so an approved mockup stays at the explore tier. | 4 |
| `architecture` | Architecture narratives carrying a freshness contract. | optional | The arch-doc reconcile advisory is skipped. | 13 |
| `feature-maps` | Capability ledgers to reconcile after a code change. | optional | The feature-map reconcile is skipped. | 23 |
| `docs` | Where the product's user-facing documentation lives (one or more homes, each with audience and visibility), what a page must carry, how it is built, published and verified, and which parts are generated. | optional | Docs impact is not asked at design, no docs gate runs at verify, capabilities are not checked for a page, and the docs audit cannot run. | 20 |
| `slices` | The planning cuts inside each program — what ships together as one unit, what each promises, the observation that proves it, and the per-cut narrative carrying its bar. | optional | Work is placed against programs directly: no cut tier, so the active-slice ceiling and the proof edges are not read. | 19 |
| `journeys` | How a persona gets a whole job done end to end, and which surfaces that path crosses. | optional | A PRD is framed from its capability alone, with nothing checking that the whole path still works. | 11 |
| `domain-model` | The meta-model the product's own data obeys — the types, attributes and relations a change has to stay consistent with. | optional | A design may invent domain vocabulary the product already names differently. | 8 |
| `api-contract` | The interface other people depend on, and the rules a new endpoint or method must follow to fit it. | optional | API shape is decided per-PRD, so the surface drifts between authors. | 8 |
| `file-conventions` | Where a new file goes, which types of file exist, and what each type must carry. | optional | A new document lands wherever its author put it, and no validator can type it. | 25 |
| `permissions` | The authorization model — who may do what, where that is enforced, and how a new capability is granted. | optional | A change touching access control is designed without the model it has to fit. | 8 |
| `security` | The security posture a change must keep — transport encryption, authentication (who the caller is and how that is proven), the trust boundaries (what sits behind the gateway and what is reachable directly), where secrets live, and how a new interface is secured before it ships. | optional | A change that adds or alters an interface is built without the transport, authentication and trust-boundary rules it has to meet, so a plaintext or unauthenticated path is found in review or in production. | 9 |
| `resilience` | What the system owes when things fail — the failure behaviour, limits and recovery a change must preserve. | optional | Failure behaviour is not part of a PRD's framing, so it is discovered in production. | 7 |
| `dev-environment` | How to bring the software up locally, know it is up, and drive it — what a reproduction and a browser pass both need before either can start. | optional | A fix is proven by tests alone; nothing is driven, so a surface regression ships green. | 17 |
| `operations` | Where the software runs, how to reach a running instance safely, and where its logs and signals are. | optional | A question about live behaviour cannot be answered from the repo — the run is asked about rather than observed. | 4 |
| `release-artifacts` | How someone outside the project obtains a released artifact, and what a newly published one has to add there before anyone can pull it. | optional | A newly published artifact is listed nowhere a consumer can reach it — the release is announced with no path to obtain it. | 1 |
| `audit-profile` | What an audit of this software checks, where its rolling record is kept, and which ground is next due for one. | optional | audit cannot run: there is no checklist to partition, no record to re-verify against, and nothing that says which area is due. | 9 |
| `runtime-contracts` | The subsystem contracts a change must obey at run time — the engines, plugin SDKs and data paths this software is built around. | optional | A subsystem change is written against its code alone, with no statement of what it must keep true. | 6 |
| `tracker-identity` | Which issue tracker this repo files into: its key prefix, its saved views and their precedence, the state-type grouping it exposes, which lane label means this repo, and how it is reached. | required | — | 22 |
| `retro-corpus` | Where a run retro is written, so the improvement loop has something to harvest. | optional | an execute command finishes without writing a retro, and process:improve has no corpus to read. | 4 |

## Fleet ships the answer

| Slot | The question it answers | Required | If it is missing | Commands that use it |
|---|---|---|---|---|
| `process-envelope` | How an execute command drives one unit of work to a merged PR (Rules A–J). | required | — | 12 |
| `process-implementation` | The coordinator/sub-agent split, the per-wave commit loop, the verification model. | required | — | 6 |
| `process-interview` | How a command asks a human: the interview card (plain words, one example, no bare ids, marked recommendation, rationale on every option) inlined into every command that asks, the `decision` document a headless park writes the card into (checked by `knowledge/scripts/validate_decision.py`), and the long form — discovery, acting on the answer, headless escalation. The card carries the writing rules (`writing.md`: English for everything that lasts, plain language for people), which the rules block and every run's prompt also inline. | required | — | 38 |
| `process-decision-write-back` | What a settled decision looks like when written down, and where the next reader finds it. | required | — | 3 |
| `process-shaping-headless` | How a shaping command runs headless on the fleet: the result-file protocol, round accounting, the question rail, the deterministic branch and the merge, the `landed` result, the sentinel table and refusals by sentinel. | required | — | 6 |
| `process-knowledge-bootstrap` | The shapes a knowledge bootstrap writes into a repository that has no corpus yet — the progress file, the per-component drafts, and the component registry, feature map, requirement register and journey shapes the shipped readers parse. | required | — | 2 |
| `process-spine` | The Command / Step / Artifact vocabulary every spine is written in. | required | — | 46 |
| `process-issue-shape` | What a well-formed issue carries, and which hand writes each field. | required | — | 14 |
| `process-planning-ladder` | Which kind of work a request is: the two state questions (broken is a bug, exploratory is an idea), then the ordered first-match ladder — component, capability or outcome, feature area, theme, task, PRD, slice, program — with the size tests, the program tests (a new program only when no existing open home fits and the work holds at least two slices), the rule that a proposal says why it is not each smaller rung, and worked examples. Inlined into every command that classifies; where each kind lives in a repository stays that repository's `entity-model` answer. | required | — | 3 |
| `process-feature-flow` | The feature flows in a repository that plans by area: a feature request's placement question (the best-matching feature and use, alternatives, a new feature, not a feature) and the dossier's confirmed placement; what route proposes for a feature request, a new feature (its map only) and a plan for a use or a whole feature (one to three named slices with their pieces of work); and what slice:create writes from each. Inlined into every command that runs them. | required | — | 3 |
| `registers-triage-partition` | The workflow-state machine: every state, every legal transition, the parks a human owns. | required | — | 17 |
| `rubric-issue-priority` | How to choose a priority 1–4. Fleet-wide: every lane files into one tracker workspace, so the scale must mean one thing. | required | — | 4 |
| `rubric-finding-severity` | How to grade a finding S1–S4, and how that maps to priority. | required | — | 2 |
| `rubric-architecture-red-team` | The pre-ship adversarial design pass, R1–R7. | optional | prd:design runs without its red-team critique step. | 2 |
| `rubric-docs` | What a user-facing page is graded against: one page is one kind, prerequisites are stated, every how-to ends with a success check, no dead ends, terminology from the repository's own answers, and voice findings that never block. | optional | Docs pages are written with no shared bar: kinds and prerequisites go unstated, a how-to may end without a success check, and nothing routes a voice finding. | 0 |
| `process-design-fidelity` | The taste bar a UI surface is built and verified against: the named high-craft reference, the mockup loop that renders and criticises before a person sees it, the build-time fix loop that fixes to the bar, and the visual-regression baseline. | optional | The PRD pipeline gates UI on correctness alone. A surface that renders without a console error ships however it looks — no reference above our own average, no build-time loop that fixes to a bar, and no screenshot baseline to catch drift — which is the functional-but-ugly page this contract exists to stop. | 7 |
| `process-improvement` | The SOP for turning recurring retro friction into an edit to the procedure that caused it — where the harvest reads from, and the apply-vs-propose rule that decides which fixes an agent may land alone. | required | — | 1 |
| `process-feature-reconcile` | How a code change reconciles the feature capability ledgers it touches, and what the coverage ratchet holds. | required | — | 3 |
| `rubric-negative-control` | What a test has to prove before it counts: it fails when the thing it guards is broken. | required | — | 0 |
| `rubric-independent-verification` | What an independent verification has to show before a status may flip: reachability from a fresh session, not the author's word. | required | — | 1 |
