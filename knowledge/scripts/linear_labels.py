#!/usr/bin/env python3
"""Canonical Linear label + view vocabulary — the SINGLE SOURCE OF TRUTH.

Every label string the agent pipeline reasons about is defined **here, once**, as
a code constant. Nothing else — no slash command, no LLM, no ad-hoc script — may
free-type a routing label: they import from this module (Python) or copy the exact
string from the table the SOP renders out of it
(`.claude/registers/triage-partition.md`). A free-typed `agent_eligible` or
`Agent-Eligible` silently creates a NEW Linear label and mis-routes the issue; the
`near_miss()` guard below exists to catch exactly that class of drift.

This module is pure + stdlib-only so a guardrail and
`validate_tracking_metadata.py`'s siblings can all import it without a dependency.
It mirrors the `CANONICAL_DIFF` registry pattern already in
`validate_tracking_metadata.py`. The one register read, `program_label_names`,
resolves the shipped `fleet_knowledge.registers` reader at call time (it prefers the
per-row fragments, so it works where the generated table is not committed) rather
than at import, so that dependency-free import contract still holds.

The daemon (`../infra/.../linear_agent/config.py`) reads the SAME strings from env
with these as defaults — its `LINEAR_*_LABEL` defaults MUST equal the constants
here. They are not shared at runtime (separate repos); the live workspace both
sides act on is the common ground.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

# ---------------------------------------------------------------------------
# Routing labels — the mutually-exclusive "what happens to this issue" decision.
# The invariant (see the SOP): on any OPEN issue AT MOST ONE of
#   { AGENT_ELIGIBLE, NEEDS_DECISION, NEEDS_ACTION, AGENT_FAILED,
#     AWAITING_HUMAN_MERGE, <Parked state> }
# is set. AGENT_RUNNING / AGENT_RETRY are transient sub-states of AGENT_ELIGIBLE
# (a claimed/queued issue keeps AGENT_ELIGIBLE), not independent routing markers.
#
# ── Why there are TWO human markers ──────────────────────────────
# `needs-human` used to carry three unrelated meanings at once — "decide this",
# "do this", and "wait for this" — so one view mixed work that gates the whole
# fleet with work that gates nothing. Measured on the 2026-07-21 drain: of 8
# parked issues only 4 were fleet-blocking; the rest were actions and holds
# sitting at the same apparent urgency. The split is by WHAT CLEARS THE BLOCKER:
#
#   NEEDS_DECISION  → a human answers a question   → cleared by an answer
#   NEEDS_ACTION    → a human does something no agent can (mint a credential,
#                     click a console, SSH somewhere) → cleared by them doing it
#   (a dependency)  → NO label. Use a `blockedBy` relation; the fleet scheduler
#                     already skips on `unmet_blockers`, so the chain
#                     self-serializes. See UNBLOCKED_BY_RELATION below.
# ---------------------------------------------------------------------------
AGENT_ELIGIBLE = "agent-eligible"  # durable human approval "agents may run this" ⇔ Agent Backlog
AGENT_RUNNING = "agent-running"  # daemon owns it now (transient; daemon-managed)
AGENT_RETRY = "agent-retry"  # soft retry between attempts (transient; daemon-managed)
AGENT_FAILED = "agent-failed"  # terminal: crashed / gave up after MAX_ATTEMPTS — needs a human
NEEDS_DECISION = "needs-decision"  # terminal: blocked on a human ANSWER — gates the fleet, drain to 0
NEEDS_ACTION = "needs-action"  # terminal: blocked on a human DOING something an agent cannot
# terminal success: green PR, a ratified guard bars the agent from merging it itself —
# a merge click is an ACTION, so this rides in the action queue alongside NEEDS_ACTION.
AWAITING_HUMAN_MERGE = "awaiting-human-merge"

# ── The 2026-08-27 lifecycle-in-workflow-state migration: workflow STATE names ──
# The daemon's lifecycle POSITION lives in the Linear workflow state now, not these
# labels. The label constants above are RETIRED as routers; they are kept for the
# historical/cost layer until the closed-issue tail is retired. Agents write STATES —
# the strings below are the CANONICAL names: what the ENG board spells today.
#
# The scheme (operator-decided): `X Queue` = waiting, unclaimed; `Xing` =
# an agent is on it. `Rework Queue` claims into `Implementing`, never into a
# `Reworking` — a re-fix IS an implement run.
#
# THREE positions are claims, not two, and the third is the one this repo shipped
# without: the check gate claims into `Triaging` exactly as implement claims into
# `Implementing`. It was live on the board for a week while nothing here
# declared it, so every issue a checker held read as "not a lifecycle state" and
# reddened the partition guardrail on every open PR at once. The lesson is the
# reverse of the alias layer below: an ADDED state has no second spelling to fold,
# so only reading the live roster and asking what code lacks can catch it —
# Label ensure now asks that direction too.
#
# ⚠️ NO CROSS-REPO IDENTITY IS CLAIMED HERE, and the retired claim is the lesson.
# These constants used to carry a comment asserting exact string equality with
# `Position` in `infra/.../linear_agent/lifecycle.py`. Nothing in this repo could
# check that — separate checkout, no import, no test could read it — so when
# renamed the four unclaimed states the claim simply went wrong in place, and it is
# *deliberately* wrong now: the operator decision leaves infra's frozen copy on the
# old spelling. An equality nothing can verify is not documentation, it is prose that
# rots silently. The enforcement replaces it: the label ensure
# --ensure-labels` reconciles `LIFECYCLE_STATES` against the LIVE workspace, and
# `validate_state_name_vocabulary.py` keeps every other module importing from here.
#
# Each is the workflow-state NAME on the ENG team, with its Linear `type`.
STATE_INTAKE = "Intake Queue"  # unstarted — filed by a person, awaiting its shaping interview
STATE_TRIAGE = "Triage Queue"  # unstarted — filed, never checked; the checker owns re-entry
STATE_TRIAGING = "Triaging"  # started — claimed for the triage half
STATE_QUEUED = "Implement Queue"  # unstarted — runnable, unclaimed
STATE_IMPLEMENTING = "Implementing"  # started — claimed for the implement half
STATE_REVIEW = "Verify Queue"  # started — green PR, verifier owed, unclaimed
STATE_VERIFYING = "Verifying"  # started — claimed for the verify half
STATE_REWORK = "Rework Queue"  # started — refuted, back to the implementer
STATE_BLOCKED_DECISION = "Blocked · decision"  # started — a human must ANSWER
STATE_BLOCKED_ACTION = "Blocked · action"  # started — a human must DO something
# started — the FILER owes an answer to a question an agent asked them.
# ⚠️ NOT a park, and deliberately NOT `Blocked · decision`. A `Blocked · decision` issue is
# one the fleet WAS driving and stopped on: a run is in flight behind it, so the queue gates
# the fleet and its target is zero. `Needs answer` is the opposite shape — the interview
# reached the end of its turn on purpose, nothing is running behind it, and no agent is
# waiting. It rides in the same VIEW because the person who owes the answer is the person
# who drains that view (operator decision), never because it means the same thing.
STATE_NEEDS_ANSWER = "Needs answer"
# started — a shaped idea whose dossier is complete (or whose proposal is on the page), waiting
# for the verdict a PERSON gives on the fleet's idea page. ⚠️ NOT `Blocked · decision`, and for
# the same OWNER reason `Needs answer` is not: that queue means the fleet is stuck mid-work and a
# human drains it from a terminal, and its target is zero because everything behind it is stopped.
# A finished dossier has nothing in flight behind it and no box is waiting on it, so `Intake ·
# decision` is the honest position — the next move belongs to a person, on the page, and the
# dispatch gate refuses it by NAME (the shape), never by type.
STATE_INTAKE_DECISION = "Intake · decision"
STATE_FAILED = "Failed"  # started — gave up after MAX_ATTEMPTS
STATE_AWAITING_MERGE = "Awaiting merge"  # started — green PR, merge click withheld
STATE_HUMAN_WIP = "Human WIP"  # started — a person deliberately owns it
# State TYPES for the above (Linear's `type` field — NOT to be keyed on by dispatch).
STATE_TYPES = {
    STATE_INTAKE: "unstarted",
    STATE_TRIAGE: "unstarted",
    STATE_TRIAGING: "started",
    STATE_QUEUED: "unstarted",
    STATE_IMPLEMENTING: "started",
    STATE_REVIEW: "started",
    STATE_VERIFYING: "started",
    STATE_REWORK: "started",
    STATE_BLOCKED_DECISION: "started",
    STATE_BLOCKED_ACTION: "started",
    STATE_NEEDS_ANSWER: "started",
    STATE_INTAKE_DECISION: "started",
    STATE_FAILED: "started",
    STATE_AWAITING_MERGE: "started",
    STATE_HUMAN_WIP: "started",
}

# Every lifecycle state the migration owns, by canonical name. Named as a set so
# a label ensure can reconcile it against the LIVE workspace roster —
# the check that replaces the deleted byte-identity prose. Before only
# `PARKED_STATE` and `PRD_PIPELINE_STATES` were reconciled, which is exactly why a
# rename of these could land in the settings UI and break dispatch with
# nothing going red. The reconciliation runs BOTH ways now: a state the
# board carries and this set does not is equally invisible, and cost six PRs a red
# merge gate before anyone looked at the roster.
LIFECYCLE_STATES = frozenset(STATE_TYPES)

# ── The alias layer: a rename must be deployable in EITHER order ──
#
# Every state in this repo is resolved STRICT BY NAME against the live roster —
# deliberately, so a near-miss refuses instead of
# riding a null into the board. But strict-by-name against ONE spelling
# makes a workspace rename undeployable in both directions at once:
#
#   • rename the board first → every running script goes blind (nothing resolves,
#     every filing and release refuses) until the merge lands;
#   • merge first → the new vocabulary resolves nothing until someone clicks.
#
# There is no third ordering. The fleet repo paid two outages on 2026-09-06 for
# exactly this before landing `dispatch/ownership.py::acceptable_names`, which this
# mirrors. Accepting the alias removes the ordering entirely: whichever end moves
# first, the other still resolves, and a rename becomes an ordinary deploy.
#
# THE DIRECTION MATTERS. Historical spellings fold in **beneath** the canonical names
# and never over them — the canonical name is always tried FIRST, so a board holding
# both spellings can never let the dead one win, and an alias only ever answers a name
# the live vocabulary does not claim. `test_no_alias_shadows_a_live_state_name` holds
# that invariant; without it a resurrected name would be silently re-pointed.
#
# THIS IS THE ACCEPT SIDE ONLY. Nothing here is ever WRITTEN to Linear: what resolution
# yields is a state **id**, and an id is the one thing a rename does not touch. An
# alias also never becomes a canonical name by seniority — when the fleet stops seeing
# a spelling on any live board, its row is deleted from this table, not promoted.
#
# Adding a row is the whole cost of the next rename: put the OLD name on the left,
# the new constant on the right, and both vocabularies work through the transition.
STATE_ALIASES: dict[str, str] = {
    # (2026-09-06) — the four unclaimed states gained a ` Queue` suffix.
    # `../infra`'s frozen dispatcher copy still writes these, by operator decision,
    # so this is a LIVE second vocabulary, not merely a historical courtesy.
    "Triage": STATE_TRIAGE,
    "Queued": STATE_QUEUED,
    "Review": STATE_REVIEW,
    "Rework": STATE_REWORK,
}


def acceptable_state_names(canonical: str) -> tuple[str, ...]:
    """Every name `canonical` will ACCEPT on a board, **canonical first**.

    Order is the safety property, not presentation: the first name that matches the
    live roster wins, so a workspace mid-rename (holding both spellings) always
    resolves to the live state and never to the dead one."""
    aliases = tuple(old for old, target in STATE_ALIASES.items() if target == canonical and old != canonical)
    return (canonical, *aliases)


def canonical_state_name(name: str) -> str:
    """The READ direction — a board's state name folded onto the constant code compares on.

    An unrecognised name passes through **unchanged**, deliberately: the caller's own
    strict comparison must still be able to refuse it. Guessing here would convert a
    typo or a genuinely new state into a silent match, which is the failure
    wearing the alias layer as a disguise.

    A name the LIVE vocabulary claims is never re-pointed by an alias — live wins."""
    if name in STATE_TYPES:
        return name
    return STATE_ALIASES.get(name, name)


def state_id_from_roster(roster: Mapping[str, str], canonical: str) -> str | None:
    """Resolve `canonical` to a state id against a live `{state name -> id}` roster.

    `None` when the board carries no acceptable spelling — the caller raises. The
    alias layer widens the vocabulary this accepts; it never invents a fallback, so
    a genuinely missing state still refuses rather than landing the issue nowhere."""
    for name in acceptable_state_names(canonical):
        sid = roster.get(name)
        if sid:
            return str(sid)
    return None


# The exact set of STATES an agent command may WRITE directly, and what each means:
# - filing an issue → STATE_TRIAGE
# - `check` RELEASE → STATE_QUEUED; ESCALATE → STATE_BLOCKED_DECISION (re-entry is
#   Triage Queue, never Implement Queue); ACTION → STATE_BLOCKED_ACTION (operator
# hands — no re-entry;)
# - implement handoff (green PR opened) → STATE_REVIEW
# - verify refute → STATE_REWORK; verify success → the daemon marks Done itself
# - a give-up a human must judge → STATE_BLOCKED_DECISION / STATE_BLOCKED_ACTION
# - a green PR the agent may not merge → STATE_AWAITING_MERGE
AGENT_WRITABLE_STATES = frozenset(
    {
        STATE_TRIAGE,
        STATE_QUEUED,
        STATE_REVIEW,
        STATE_REWORK,
        STATE_BLOCKED_DECISION,
        STATE_BLOCKED_ACTION,
        STATE_AWAITING_MERGE,
    }
)

# ── The pre-flight gate: `to-be-checked` (the checker's admission ticket) ────
# NOT a routing marker, and that omission is the load-bearing part of the design.
#
# Every issue an agent files is born `to-be-checked` and carries NO priority, NO
# `agent-eligible`, and no project/component placement — because the filer is the
# wrong party to decide any of that. `check` runs in a FRESH daemon-dispatched
# session (the only way to guarantee it does not inherit the filer's reasoning — the
# same lesson the audit checklist already learned about self-assessed severity), does
# the triage, and decides one of three things: release it to the fleet, park it for a
# human, or close it.
#
# WHY IT COEXISTS WITH THE HUMAN MARKERS instead of being mutually exclusive with
# them. The checker's escalation path is `+needs-decision` while KEEPING this label.
# That single choice buys the whole re-entry loop with no daemon state and no webhook:
#   • `to-be-checked` + `needs-decision` → the daemon's own human-marker veto already
#     bars dispatch, and `classify()`'s precedence already routes it to Needs My
#     Decision. Nothing new is needed for the park.
#   • the human answers (via `unblock`) → `-needs-decision`, label KEPT →
#     the daemon re-dispatches `check`, which reads the answer and finishes
#     the triage it started.
# Modelling it as a routing marker would have forced the park to strip it, and then
# nothing on the issue would remember that the CHECKER — not the fleet — owns
# re-entry. `agent-running`/`agent-retry` are the existing precedent for a lifecycle
# label that rides alongside rather than competing.
#
# THE INVARIANT: this label is removed exactly ONCE, by the checker, at the moment it
# clears the issue. Its presence therefore means "never cleared" — there is no other
# way to lose it, so the gate cannot be silently skipped.
TO_BE_CHECKED = "to-be-checked"

# ── The post-flight gate: `awaiting-verification` (the gate OUT) ─────────────
# The symmetric half of `to-be-checked`, and NOT a routing marker either. A
# bug/task/cleanup implement run no longer merges its own work: it opens a green PR,
# moves the issue to In Review, and stops. The daemon then stamps this label and
# dispatches `verify` in a fresh session, which certifies the fix against the
# issue's own cause ledger and merges only on an all-closed ledger.
#
# WHY THE LABEL EXISTS AT ALL, given the STATE already says "awaiting verification".
# It is an anti-forgery mark, not a router. Linear's GitHub integration bounces a Done
# issue back into a started state whenever ANY other PR mentions its key, so
# the review state alone can never be trusted to mean "a verifier is owed" — admitting
# on that bounce would re-dispatch the verifier at already-merged work, forever. A PRD
# is discriminated by its own frontmatter instead (its precondition check refuses one
# already `verified`/`shipped`); a bug has no frontmatter, so it needs a mark a webhook
# cannot write. Hence: written by the DAEMON, only after it has proven the run actually
# moved the issue into review, and stripped on every terminal path.
#
# Do not add it to ROUTING_MARKERS. The issue must keep `agent-eligible` while it waits,
# or nothing dispatches the verifier — same coexistence as `to-be-checked`.
AWAITING_VERIFICATION = "awaiting-verification"

# The gate out's REFUSAL mark: `verify` writes it (with a comment listing the
# open ledger lines) when a fix does not close the issue it claims to, and the daemon
# routes a `verify-failed` issue back to the implement command rather than merging it
# (the `verify` command). Spelling therefore matters for routing, which is
# why it belongs here rather than free-typed at each site — it was free-typed until
# , where a script that could not name it closed an issue straight over one.
#
# Deliberately NOT a ROUTING_MARKER: a refuted fix legitimately carries `verify-failed`
# alongside a human marker (`needs-decision` once the daemon parks it at the refutation
# cap — live shape), and making the pair an at-most-one violation would red
# the partition guardrail on correct data.
VERIFY_FAILED = "verify-failed"

# ── Migration bridge, not back-compat ────────────────────────────
# The `../infra` daemon still writes `needs-human` on self-park until its own PR
# lands (that repo is human-merge-guarded on daemon.py, so the two sides cannot
# flip atomically). Until then this label must still CLASSIFY, or a daemon-parked
# issue would fall through to "Assign to Agents" and be silently re-dispatched.
# It resolves to NEEDS_MY_DECISION — the ratified fail-safe default: a
# misclassified action costs one glance, a misclassified decision would sit
# unseen in a queue checked weekly.
# REMOVE THIS CONSTANT once the daemon emits the two markers and no open issue
# carries `needs-human` (both conditions are reportable).
NEEDS_HUMAN_LEGACY = "needs-human"

# The five park labels the states replaced. Retired as routers with everything else
# above; retained as a NAMED SET because the closed-issue history layer still queries
# on it (`sweep_closed_human_markers.py`, and the guardrail's informational count of
# vestigial labels on the closed tail). Nothing routes on it.
HUMAN_MARKERS = frozenset({NEEDS_DECISION, NEEDS_ACTION, AGENT_FAILED, AWAITING_HUMAN_MERGE, NEEDS_HUMAN_LEGACY})

# ── The opt-out, and why it is POSITIVE ──────────────────────────
# `human-wip` = "a human is deliberately driving this; keep it out of the triage
# queue". It is NOT a HUMAN_MARKER: those mean "a human must do something" and feed
# the two human queues. This one means the opposite — nothing is owed, leave it be.
#
# It exists because the rule it replaces was a NEGATIVE test. `classify()` used to
# read a started issue with no fleet label as human-owned WIP, inferring intent from
# the ABSENCE of a routing label. But absence-of-a-routing-label is also the exact
# signature of a STRANDED issue, so the carve-out swallowed the very failure it
# should have surfaced: on 2026-07-24 two Urgent PRDs sat in
# `In Review` carrying only `prd` — invisible to the fleet (which fetches on
# AGENT_ELIGIBLE) and to every human view — for ~9h. Zero routing markers is not a
# routing decision; it is the absence of one, and that belongs in ASSIGN_TO_AGENTS
# where a human makes it.
#
# The rejected alternative was to treat the ASSIGNEE as the signal. It was checked
# against live data and does not work: carried the same human `assignee`
# continuously — while the fleet drove it AND throughout the 9h it was stranded — so
# an assignee-based rule would have stayed silent on the incident that motivated it.
HUMAN_WIP = "human-wip"

# ── The routing markers are RETIRED as routers (lifecycle migration, P4.2) ──
# There is no `ROUTING_MARKERS` set any more, and its absence IS the design. That set
# existed to express "at most one of these may be set" — an invariant a label store can
# only ever CHECK after the fact, because coexistence stays representable. The position
# is a workflow STATE now: an issue has exactly one, always, so at-most-one is true by
# construction and there is nothing left to check. `VIEW_BY_STATE` is what replaced it.
#
# The label CONSTANTS stay, and are not dead code. They are still carried by ~4,000
# closed issues, deliberately: `linear-agent costs` reaches recorded historical spend
# through `agent-eligible` on finished issues, so the closed tail is never bulk-mutated
# (design §8.6 / P4.7). `near_miss()` also needs the canonical spellings to keep
# catching a free-typed impostor.
RETIRED_ROUTING_LABELS = frozenset(
    {
        AGENT_ELIGIBLE,
        AGENT_RUNNING,
        AGENT_FAILED,
        NEEDS_DECISION,
        NEEDS_ACTION,
        NEEDS_HUMAN_LEGACY,
        AWAITING_HUMAN_MERGE,
        HUMAN_WIP,
        TO_BE_CHECKED,
        AWAITING_VERIFICATION,
        VERIFY_FAILED,
    }
)

# The subset whose presence on an OPEN issue means a writer nobody accounted for is
# still writing routing labels — reported by `migration_warnings()`, never fatal. Two
# deliberate omissions, both of which would otherwise warn on correct data:
#   • AGENT_RETRY is not in RETIRED_ROUTING_LABELS at all — it is a PRIORITY signal,
#     not a position, and it stays exactly as it was (design §4.4).
#   • VERIFY_FAILED is retired as a ROUTER only. Design §4.5 keeps it available as a
#     DIAGNOSTIC on a refuted issue, so warning on it would be noise on correct data —
#     which is precisely how a guardrail earns a permanent `--warn-only`.
VESTIGIAL_ROUTING_LABELS = RETIRED_ROUTING_LABELS - {VERIFY_FAILED}

# The Linear relation that expresses "wait for this". Named here so no command or
# script invents a label for it: a dependency is a GRAPH EDGE, never a marker.
# NOTE the PRD case, because this rule reads as universal and the PRD nuance has
# been stated wrongly before (the class of stale claim): `Type:prd` issues
# ARE blocker-gated too — `gate_workitems` / `selection._blocked` refuse a live
# Linear `blockedBy` for every kind including PRDs, in every position (
# earlier ce2ce86 folded the check into `compute_plan`'s readiness string, and the
# finishing exemption then skipped it). Frontmatter `depends_on:` remains the
# source of truth for PRD→PRD readiness sequencing; the Linear edges mirror it for
# the board and carry the one edge frontmatter cannot express — a bug/task
# blocking a PRD (see .claude/process/issue-shape.md → "blockedBy relations").
UNBLOCKED_BY_RELATION = "blockedBy"

# ---------------------------------------------------------------------------
# Linear-only description headings — the SINGLE source of truth for which `## …`
# sections live ONLY on the Linear issue and must survive a PRD description rebuild
# by the git → Linear projection (interview-protocol / `unblock` write-backs have no
# git file). Consumed by:
#   * the fleet service's `prd-projection` pass — what a rebuild re-appends (what
#     survives); it reads this tuple, never a copy of it;
#   * the park release path              — which answer-shaped headings clear a park.
# Adding a heading HERE puts it on both sides at once. Before this existed the two
# lists drifted: `Resolved` was added to the validator but never the sync, so every
# `## Resolved (<date>)` section was silently destroyed (— third occurrence
# of the class, which is why it is a shared list, not a fourth
# copy). Keep tuple order stable: the projection renders it into an alternation.
# ---------------------------------------------------------------------------
LINEAR_ONLY_DESCRIPTION_HEADINGS = ("Decision", "Resolved", "Action required")

# ---------------------------------------------------------------------------
# Type labels — the routing KIND, children of the "Type" parent label in Linear.
# `Type:idea` / `Type:customer-bug` are NOT agent work kinds (see WORK_KINDS in the
# daemon) — ideas need planning first, customer-bugs are a separate shadow track.
# ---------------------------------------------------------------------------
TYPE_PRD = "prd"
TYPE_BUG = "bug"
TYPE_TASK = "task"
TYPE_CLEANUP = "cleanup"
TYPE_AUDIT = "audit"
TYPE_IDEA = "idea"
TYPE_CUSTOMER_BUG = "customer-bug"

WORK_KINDS = frozenset({TYPE_PRD, TYPE_BUG, TYPE_TASK, TYPE_CLEANUP, TYPE_AUDIT})
NON_WORK_KINDS = frozenset({TYPE_IDEA, TYPE_CUSTOMER_BUG})
ALL_TYPE_KINDS = WORK_KINDS | NON_WORK_KINDS

# The kinds the check gate covers (check.md: "`Type:bug`, `Type:task` and `Type:cleanup`
# — everything an agent can file that the fleet will then build"). These are born in
# `Triage Queue` and may never REST in `Backlog`. Deliberately absent: `Type:prd`
# (a stub PRD legitimately rests in `Backlog` — the PRD projection maps `stub` →
# `Backlog`) and `Type:audit` (filed by the PRD lifecycle, outside the check gate, and
# recurring audits park in `Backlog` by design — 8 of them on the live board).
GATED_KINDS = frozenset({TYPE_BUG, TYPE_TASK, TYPE_CLEANUP})

#: a `GATED_KINDS` issue resting in `Backlog` filed before this date is
# grandfathered — its filer could not have known the rule. The date is the first day
# the rule is LIVE on `main` for filers (the merge happens during the previous UTC
# day). Same cutoff mechanics as the scope-ledger gate.
BACKLOG_MISFILE_CUTOFF = "2026-09-04"

# ---------------------------------------------------------------------------
# Source labels — WHERE a filing came from, as opposed to what kind it is. One member
# today, `source:product`, and it is the SHARED CONTRACT between the product (PRD 0702,
# ) and the fleet: the product files a builder's feature request onto the team's
# board in a resting, backlog-kind state, and the fleet finds it by THIS label alone, in
# any open state — never by a state name, because the product's admin picks the state and
# the label is the one thing both sides agree on (the product side is admin-configured;
# the label is the contract; `source:product` may not be renamed by an admin, only
# included).
#
# It is declared here so `near_miss()` catches the free-typed variants (`Source:Product`,
# `source_product`, `Source › product`) that would otherwise read as an unknown, parentless
# label no reader authenticates. It is NOT a routing marker: a `source:product` issue does
# not become dispatchable by carrying it, and the fleet flags one that finds its way into a
# state a lane dispatches (— see `fleet-service`'s `api/product.py`).
# ---------------------------------------------------------------------------
SOURCE_PRODUCT = "source:product"
SOURCE_LABELS = frozenset({SOURCE_PRODUCT})
#: The family prefix, like `repo:`. Only the members in `SOURCE_LABELS` are canonical, but the
#: prefix is recognised so a free-typed `source_product` / `Source-Product` is a near-miss that
#: names the canonical spelling rather than passing as an unknown, parentless label.
SOURCE_PREFIX = "source:"


def is_source_label(label: str) -> bool:
    return label.startswith(SOURCE_PREFIX)


def source_labels(labels: frozenset[str] | set[str]) -> frozenset[str]:
    """The `source:*` labels among `labels`."""
    return frozenset(label for label in labels if is_source_label(label))


# ---------------------------------------------------------------------------
# Repo-lane labels — which checkout/daemon lane executes an issue, NOT
# whether it's eligible. Orthogonal to the routing markers above: an issue carries
# AT MOST one of these; absence means the default lane (the platform repo — every
# issue filed before this axis existed already satisfies that by omission). A lane
# label is `repo:<name>` and resolves to `<org>/<name>` in this checkout's GitHub org.
# The SET of lanes is the fleet's lane table (`fleet-service`'s `lanes.py`); this module
# knows only the family, which is all a partition guard needs — recognising one and
# counting them.
#
# ⚠️ NOTHING CREATES A LANE'S LABEL. This comment used to say the lane table "also creates
# a lane's label when the lane is added", and that is false in both directions: there is no
# `repo:*` entry in `CANONICAL_LABELS`, so a label ensure mints
# none; and `fleet-service`'s `tracker/linear.py` says outright that "`ensure_label` does not
# exist here, and its absence is the point" — a typo in a label silently CREATES a real one
# and mis-routes the issue, so that client resolves names once at boot and never creates.
# The only `issueLabelCreate` in fleet-service belongs to the PRD board projection.
#
# So ADDING A LANE IS THREE SEPARATE ACTS, and nowhere else states them together:
#   1. a `Lane` row in `fleet-service`'s `dispatch/lanes.py`;
#   2. a checkout directory named for `Lane.name` on every box that should serve it —
#      `can_run_lane` is `cloned and push_state != "no"` and selection filters on it BEFORE
#      dispatch, so a box without one can never be sent the work that would make it clone.
# **This act has a mechanism since **: the service sends its lane table on the
#      hello answer (`api/box.lane_catalog`) and `fleet_daemon.Runner.reconcile_lanes` creates
#      any missing checkout between runs. A lane added to the table therefore reaches every
#      box with no hand ritual, and no box has to be re-provisioned per lane. Provisioning
#      (`deploy/fleet-daemon/provision.sh` → `clone_lanes`) still creates them at build time,
#      but it is no longer the only path that can;
#   3. the Linear label itself, created BY HAND, spelled exactly as `Lane.label`.
# Do all three or the lane is silently unreachable. Measured 2026-09-12 while renaming a
# lane: the stale wording sent two separate passes looking for a registry that has never
# existed here.
# ---------------------------------------------------------------------------
REPO_LANE_PREFIX = "repo:"


def is_repo_lane(label: str) -> bool:
    return label.startswith(REPO_LANE_PREFIX)


def repo_lanes(labels: frozenset[str] | set[str]) -> frozenset[str]:
    """The `repo:*` labels among `labels` — at most one is legal."""
    return frozenset(label for label in labels if is_repo_lane(label))


# The check gate's WINDOW: filed-but-unchecked (`Triage Queue`) and being-checked
# (`Triaging`). Named as a set because the exemption below is about the window, and
# a one-state comparison already lost half of it once.
CHECK_GATE_STATES = frozenset({STATE_TRIAGE, STATE_TRIAGING})

# The states where the priority rule does not bite — the check WINDOW, extended by the
# fleet's own give-up park. `Failed` is written by the DAEMON, never a producer: when a
# check run exhausts its budget or its box goes silent it is parked at `Failed` BEFORE
# check produced a priority (then, each hard-failing the
# mis-birth rule and reddening the partition guardrail). A `Failed` issue that HAD been
# checked already carries a priority, so exempting the state masks no real mis-birth — the
# rule still bites everywhere past the gate.
PRIORITY_EXEMPT_STATES = CHECK_GATE_STATES | {STATE_FAILED}


def requires_priority(labels: frozenset[str], *, state_name: str = "") -> bool:
    """Every created issue MUST carry a priority — with two exemptions, both of which
        are "nobody has committed to this yet", never "we forgot".

        `Type:idea` — a parked idea is uncommitted, so priority 0/None is the correct,
        deliberate value (see issue-tracking.md).

        The pre-flight gate — `Triage Queue` **and `Triaging`**, plus the retired
        `to-be-checked` label they replaced. Priority is an OUTPUT of `check`, not
        an input the filer guesses. Without this exemption the guardrail hard-fails every
        issue in the window between filing and its check run, i.e. exactly the state the
        pipeline creates on purpose. The rule the exemption protects is unchanged and in
        fact strengthened: an issue that has LEFT the gate must carry a priority, and a
        fresh session sets it rather than the agent that happened to notice the problem.

        ⚠️ The exemption is a WINDOW, not a state —. Written as the single state
        `Triage Queue` it silently excluded the second half of its own window: claiming an
        issue into `Triaging` moves it out of the exempt STATE without moving it out of the
        period before the check has produced anything, so every issue a checker box picked
        up hard-failed the mis-birth rule for the duration of its own run, and the report
        blamed the producer for a write the daemon had made correctly (observed on
        the moment `Triaging` was declared here). Add the claimed half of any future gate
        to this test, not just its queue.

        ⚠️ The window also ENDS in a state the daemon writes: a check run that exhausts its
        budget or goes silent is parked at `Failed` before check ever produced a priority
    . `Failed` is therefore in `PRIORITY_EXEMPT_STATES` beside the gate pair —
        a `Failed` issue that HAD been checked already carries a priority, so the exemption
        hides no real mis-birth.

        ⚠️ `state_name` is not optional in practice, only in signature. The gate is the
        `Triage Queue` STATE now; the label is stripped from every open issue. A caller that omits
        it re-fails every freshly-filed issue — the exemption would read as removed when it
        was only unreachable.
    """
    if state_name in PRIORITY_EXEMPT_STATES:
        return False
    return TYPE_IDEA not in labels and TO_BE_CHECKED not in labels


# Every canonical label whose EXACT spelling matters for routing. The retired `Area`
# values are deliberately absent — they never routed, and republishing the word list
# here is what would let a producer copy the mandate back in (see RETIRED_LABEL_GROUPS).
# `NEEDS_HUMAN_LEGACY` is deliberately absent: `--ensure-labels` must not re-create
# it, and `near_miss()` must not "helpfully" normalize a new label onto it. It is
# recognised by `classify()` for the migration window only.
CANONICAL_LABELS = frozenset(
    {
        AGENT_ELIGIBLE,
        AGENT_RUNNING,
        AGENT_RETRY,
        AGENT_FAILED,
        NEEDS_DECISION,
        NEEDS_ACTION,
        AWAITING_HUMAN_MERGE,
        HUMAN_WIP,  # `--ensure-labels` must create it: an opt-out nobody can find is not an opt-out
        TO_BE_CHECKED,  # a free-typed `to_be_checked` would file straight past the gate
        AWAITING_VERIFICATION,  # the daemon's admission mark for the gate out — a misspelling strands the fix
        VERIFY_FAILED,  # a misspelling reads as "verification never refuted this" — see
    }
    | ALL_TYPE_KINDS
    | SOURCE_LABELS
)

# ---------------------------------------------------------------------------
# Component labels — children of the "Component" parent group, one per row of the
# component registry (knowledge/specs/architecture/components.md). NOT routing
# labels: they are the attribution edge that connects Linear-native work (bugs,
# tasks, audits — the majority of issue volume, which has no git file) back to the
# component architecture. Applied at issue CREATE by the issue-creating commands,
# derived from touched paths via knowledge/scripts/component_of.py.
#
# The child set is dynamic (it IS the registry), so unlike the constants above it
# is read from components.md at call time — the registry stays the single source
# of truth and the label group can never drift from it silently.
# ---------------------------------------------------------------------------
COMPONENT_PARENT = "Component"


def component_label_names(repo_root: str | None = None) -> frozenset[str]:
    """Component ids from the registry — the canonical child-label names."""
    import re
    from pathlib import Path

    root = Path(repo_root) if repo_root else _repo.repo_root()
    reg = root / "knowledge" / "specs" / "architecture" / "components.md"
    if not reg.is_file():
        return frozenset()
    ids: set[str] = set()
    in_sec = False
    for line in reg.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_sec = line.strip() == "## Components"
            continue
        if not in_sec or not line.strip().startswith("|"):
            continue
        first = re.split(r"(?<!\\)\|", line.strip().strip("|"))[0].strip()
        if first and first.lower() != "id" and set(first) - set("-: "):
            ids.add(first)
    return frozenset(ids)


# ---------------------------------------------------------------------------
# Program labels — children of the "Program" parent group, one per row of the
# program register (knowledge/programs.md). NOT routing labels: they are the
# roll-up edge that says which program's work an issue belongs to, and a program
# carries an authored rank the work under it inherits.
#
# The group already existed for PRDs — the git → Linear projection (now the fleet
# service's `prd-projection` pass) creates one child per program-register row and
# puts one on a PRD issue via its frontmatter `slice:`. What it never reached was Linear-born work
# (bug/task/cleanup — the majority of issue volume, which has no git file to
# carry a `slice:`), so the inheritance had nothing to attach to. Measured on the
# live board 2026-09-05: 0 of the 57 issues in `Queued` carried one; all 15 open
# issues that did were PRDs. `check` is the session that triages the
# rest, and the ship step's `move_issue` (with the program's label) is where it lands one.
#
# The child set is dynamic (it IS the register), exactly like the component set
# above — a program added to `knowledge/programs.md` widens the valid set with no
# code change here, and an id the register does not carry is not a program
# however plausible it looks. Every other writer of this group names the parent
# through the constant below, so the string is defined exactly once.
# ---------------------------------------------------------------------------
PROGRAM_PARENT = "Program"

# The literal a triager passes to say **"I looked, and this work belongs to no
# program"** — a decision, not a missing argument.
#
# It exists because those two facts must never collapse. Most work legitimately
# has no program and falls through to the ordering keys beneath the program rank
# (which itself only breaks ties between equal priorities);
# that is the designed behaviour, not a failure to be forced or warned about. But
# an issue with no program label is ALSO what an un-triaged issue looks like, and
# an absence rendering as a zero is a defect this estate has shipped more than
# once. So the release mechanism makes the answer MANDATORY and this is the value
# that says "none": the flag cannot be omitted, and a released issue therefore
# always carries an answered question, whichever way it was answered.
NO_PROGRAM = "none"

PROGRAM_ID_PATTERN = r"^PG-\d+$"


def program_label_names(repo_root: str | None = None) -> frozenset[str]:
    """Program ids from the register — the canonical child-label names.

    Read at call time through the shipped `fleet_knowledge.registers` reader for the same
    reason `component_label_names` re-reads the component registry: the register is the
    single source of truth and a code-side copy would drift silently. That reader prefers the
    per-row `rows/*.json` fragments and so yields the id set on a fresh checkout where the
    generated register table is no longer committed; it falls back to the committed
    `knowledge/programs.md` for a corpus that has not migrated. Keyed on the ID's shape
    rather than a section heading, so a malformed fragment is skipped and never reads as
    "no programs exist".

    The register package is imported here, not at module import: this module stays
    dependency-free for every consumer that only needs the label vocabulary, exactly as its
    docstring promises.
    """
    root = Path(repo_root) if repo_root else _repo.repo_root()
    _repo.fleet_knowledge()
    from fleet_knowledge import registers  # noqa: PLC0415 — resolved after the path insert

    return frozenset(str(r["id"]) for r in registers.programs(root / "knowledge"))


# ---------------------------------------------------------------------------
# RETIRED — the `Area` label group (2026-08-18).
#
# `Area` was the engineering-discipline axis (`frontend`/`backend`/`connector`/
# `agents`/`infra`), written by `check` at triage. It is retired: no command
# sets it, no spec requires it, and nothing here defines its vocabulary. The live
# labels STAY on the ~3,960 issues that already carry one — retirement means "no
# longer set, no longer required", never "erased", and a bulk mutation over closed
# history would buy nothing a reader wants.
#
# WHY, measured against the live workspace before anything was touched:
#   • **Nothing consumed it.** Not one of the 7 saved views' `filterData` references
#     an Area value; no script in this repo reads one; the `../infra` daemon names it
#     only in comments. It was write-only metadata.
#   • **It was already optional in practice.** 51 of 125 open issues carried no Area
#     label at all and nothing broke — including the partition, which routes on the
#     markers above and never on this.
#   • **Attribution is already carried, twice, and DERIVED rather than guessed.**
#     `Component` (above) resolves from touched paths via `knowledge/scripts/component_of.py`
#     and reconciles against the component registry; the Linear **Project** is the
#     feature area, projected from the map's H1 in `knowledge/features/`.
#     Area was a third axis, hand-picked per issue, that no reader consumed.
#   • **It had already drifted, invisibly.** An un-ratified sixth value `agentd`
#     reached 36 issues with nothing to catch it, because Area was excluded from
#     `CANONICAL_LABELS`/`near_miss()` along with the rest of the non-routing
#     vocabulary — so the group was never closed in fact, only in prose.
#   • **And `agents` named two things.** `Area › agents` (a discipline) sat one glance
#     from the Linear **Project** `Agents` (a feature area); 7 issues carried both.
#     Renaming was weighed first and rejected: every candidate collided worse —
#     `agent-runtime` is already a live **Component** label — because `agents` is a
#     *subsystem* in a group whose other four members are *layers* (`internal/agents/`
#     is Go, i.e. `backend`). That no discipline-shaped name was free is what showed
#     the axis itself was wrong, not the one value.
#
# Full record: knowledge/decisions/2026-08-18-retire-the-area-label-group.md
#
# NO VOCABULARY CONSTANT LIVES HERE, ON PURPOSE. Naming the five values — even only
# to report drift — is what a producer greps for and copies, and a retired axis that
# still ships its own word list invites exactly the quiet return this comment exists
# to prevent. The guard is static instead:
# a retired-group check fails if
# any command or spec starts mandating an Area label again.
# ---------------------------------------------------------------------------
RETIRED_LABEL_GROUPS = frozenset({"Area"})

# ---------------------------------------------------------------------------
# States. Linear workflow-state *types* group the named states. "Parked" is a
# distinct named state of the `backlog` type — so the daemon's OPEN_STATE_TYPES
# gate (triage/backlog/unstarted) would still pick a Parked issue up UNLESS its
# AGENT_ELIGIBLE label is removed. That removal is the load-bearing park rule.
# ---------------------------------------------------------------------------
PARKED_STATE = "Parked"  # canonical name of the park state (backlog-type)

# PRD pipeline states — the DRAFTING-phase workflow states that ONLY `Type:prd`
# issues may occupy. Linear scopes workflow states per TEAM, not per issue type,
# so in a shared tracker team nothing native stops a task being dragged
# into `Needs Design`; this vocabulary + `invariant_violations()` below IS the
# enforcement (guardrail detection + revert, not a wall). The states are
# projected from PRD frontmatter `status:` by the fleet service's `prd-projection`
# pass (these constants are the single source of the names), and every projection
# pass stomps them back: for a `Type:prd` issue the board state is a READ-ONLY
# projection.
#
# **`Spec` WAS THE THIRD AND IS GONE.** It held a PRD whose frontmatter said
# `planned` — fully authored, waiting for somebody to release it — and nothing
# ever did: the projection's `WRITABLE_STATES` deliberately excludes every
# execution state, the label that used to release a PRD (`agent-eligible`) is
# RETIRED, and no daemon dispatches on `Spec`. A planned PRD now projects
# straight into `Implement Queue` (the runnable pool, `STATE_QUEUED`), so there
# is no authored-but-unreleased position left. `Implement Queue` is deliberately
# NOT a PRD-pipeline state: every kind rests there, so a "non-PRD in a
# PRD-pipeline state" invariant over it would red on ordinary work.
NEEDS_DESIGN_STATE = "Needs Design"  # status: prd-drafted — prd.md exists, design.md doesn't
NEEDS_PLAN_STATE = "Needs Plan"  # status: designed — design.md exists, plans don't
PRD_PIPELINE_STATES = frozenset({NEEDS_DESIGN_STATE, NEEDS_PLAN_STATE})
# Terminal state types — an issue here is in NO view. `duplicate` is a real Linear
# state type (the "Duplicate" state) and is terminal like completed/canceled: a
# duplicate is resolved, never agent work. Omitting it wrongly counts duplicates as
# live triage debt (35 of them on the ENG board).
CLOSED_STATE_TYPES = frozenset({"completed", "canceled", "duplicate"})
UNSTARTED_STATE_TYPES = frozenset({"triage", "backlog", "unstarted"})
STARTED_STATE_TYPE = "started"

# State NAMES. `classify()` keys on state *types*, but a Linear saved view can only
# enumerate state *names* — there is no state-type predicate in the view editor. That
# asymmetry is a blind spot: a view can omit a name and go silently un-reachable for a
# whole class of issue while every label check still passes. It is exactly how
# stayed invisible — "Assign to Agents" listed only the un-started names, so a stranded
# `In Review` issue could never have appeared there no matter what `classify()` decided.
# Named here so `expected_view_filters()` can assert the live status filters too.
BACKLOG_STATE = "Backlog"
# Linear's stock unstarted state. The ENG team does not use it (the lifecycle states
# replaced it), but the sibling teams do and the importance board reads across them —
# so it is named here rather than free-typed at the one site that needs it.
TODO_STATE = "Todo"
IN_PROGRESS_STATE = "In Progress"
IN_REVIEW_STATE = "In Review"
UNSTARTED_STATE_NAMES = frozenset({BACKLOG_STATE}) | PRD_PIPELINE_STATES
STARTED_STATE_NAMES = frozenset({IN_PROGRESS_STATE, IN_REVIEW_STATE})
# Every non-terminal state name. `Parked` is open too — it is a backlog-type state.
OPEN_STATE_NAMES = UNSTARTED_STATE_NAMES | STARTED_STATE_NAMES | {PARKED_STATE}

# ── The states each saved view claims (2026-08-27 lifecycle migration, P4.3) ──
# The lifecycle position lives in the workflow STATE now, so a view's predicate is a
# set of state NAMES — positive, with no exclusion list. The states are disjoint by
# construction (an issue has exactly one), which is what retires the hand-maintained
# `-needs-decision -human-wip …` lists the label world needed. Those lists are not
# merely redundant now, they are wrong: they encoded a coexistence that can no longer
# happen, so a label later re-added as a DIAGNOSTIC (design §4.5 keeps that option
# open for `verify-failed`) would silently empty the queue that still excluded it.
#
# `In Progress` / `In Review` are deliberately absent from every set below. They are
# retired (design P4.6), and the three ENG git-automation rules that were their only
# other writer are deleted, so nothing can put an ENG issue back into them.
# `Triaging` is here for the same reason `Implementing` is: it is a CLAIM, and the
# state IS the claim, so no second box can take an issue another is driving. It is
# deliberately absent from `AGENT_WRITABLE_STATES` below — a claim is the daemon's
# write, never a session's — and `WATCHDOG_NEVER_CLOSE_STATES` picks it up from
# here, because a sweep may not close an issue a checker box is holding.
#
# `Intake Queue` is here for the reason `Triage Queue` is: an agent command — the shaping
# interview, `intake` — owns an item while it rests here, so it is fleet-owned work
# and not a human's to route. The item leaves for `Triage Queue` when the dossier lands.
# (What dispatches on this position is the daemon's configuration, in `../infra`, and is
# deliberately not asserted from here — this module owns the vocabulary, never the routing
# table that reads it.)
AGENT_POOL_STATES = frozenset(
    {
        STATE_INTAKE,
        STATE_TRIAGE,
        STATE_TRIAGING,
        STATE_QUEUED,
        STATE_IMPLEMENTING,
        STATE_REVIEW,
        STATE_VERIFYING,
        STATE_REWORK,
    }
)
# `Failed` rides with `Blocked · decision`: retry-vs-rescope-vs-kill is a judgement,
# which is this queue's definition — and where `agent-failed` routed before.
DECISION_STATES = frozenset({STATE_BLOCKED_DECISION, STATE_FAILED})
# `Awaiting merge` rides with `Blocked · action`: a merge click IS an action.
ACTION_STATES = frozenset({STATE_BLOCKED_ACTION, STATE_AWAITING_MERGE})
# A question an agent asked the person who filed the item, waiting on their reply.
#
# Kept as its OWN set rather than folded into `DECISION_STATES`, and the separation is the
# point: `DECISION_STATES` means *the fleet is stopped and a run is in flight behind this*,
# which is what earns that queue its zero target and its "gates the fleet" reading. A
# `Needs answer` item stops nothing — the interview ended its turn deliberately and is
# resumed when the answer lands. Folding the two together would quietly restate every
# fleet-gating claim `DECISION_STATES` carries about a state that gates nothing, and would
# make the zero target unreachable for a reason that is not a stall.
#
# It routes to the SAME view because the operator drains that view and the question is
# theirs to answer — a view assignment, never an equivalence.
ANSWER_STATES = frozenset({STATE_NEEDS_ANSWER})

# THE TWO LOOPS an issue can be in, and the line a state write may not carry an idea across.
#
# The intake loop is where a `Type:idea` lives — the interview's queue and its two parks. The
# work loop is every state where the check / implement / verify halves dispatch or hold a
# claim, and every one of them refuses a non-work kind (the fleet's `non-work-kind` gate). An
# idea leaves the intake loop only by the verdict that RE-KINDS it (the fleet's idea page),
# never by a hand release —: an unblock-command release moved an answered idea
# `Needs answer -> Implement Queue` and it stranded there, refused by every implement command.
INTAKE_LOOP_STATES = frozenset({STATE_INTAKE, STATE_NEEDS_ANSWER, STATE_INTAKE_DECISION})
WORK_LOOP_STATES = frozenset(
    {STATE_TRIAGE, STATE_TRIAGING, STATE_QUEUED, STATE_IMPLEMENTING, STATE_REVIEW, STATE_VERIFYING, STATE_REWORK}
)


def loop_crossing_refusal(
    *, key: str, label_names: frozenset[str], current_state: str, target_state: str
) -> str | None:
    """Why moving `key` from `current_state` to `target_state` would strand it, or `None`.

    The one refusal: a `Type:idea` written into the work loop. The sentence names where the
    item goes instead, read off where it sits — an answered `Needs answer` returns to `Intake
    Queue` (the interview resumes with the answer), a dossier at `Intake · decision` is decided
    on the fleet's idea page. Every other move — a work kind anywhere, an idea to a park, a
    deferral or a close — is not this function's business and passes.
    """
    target = canonical_state_name(target_state)
    if target not in WORK_LOOP_STATES or TYPE_IDEA not in label_names:
        return None
    current = canonical_state_name(current_state)
    if current == STATE_NEEDS_ANSWER:
        instead = (
            f"An answered `{STATE_NEEDS_ANSWER}` item goes back to the loop that asked: write the answer "
            f"into the description, then move it to `{STATE_INTAKE}`, where the interview resumes with it."
        )
    elif current == STATE_INTAKE_DECISION:
        instead = (
            "Its verdict is given on the fleet's idea page (route, create, withdraw) — that is what "
            "re-kinds it before it may enter the work loop."
        )
    else:
        instead = f"Return it to `{STATE_INTAKE}`, or give the verdict that re-kinds it on the fleet's idea page."
    return (
        f"refused: {key} is a `Type:idea` at {current_state or 'an unread state'!r}, and {target!r} is in "
        f"the work loop, which refuses an idea by kind — it would strand there (ENG-12413). {instead}"
    )


# What the `Needs My Decision` view holds — the one place the two sets above are unioned,
# so the view's membership is written once and `expected_view_filters()` and
# `_build_view_by_state()` cannot disagree about it.
NEEDS_MY_DECISION_STATES = DECISION_STATES | ANSWER_STATES
HUMAN_HOLD_STATES = NEEDS_MY_DECISION_STATES | ACTION_STATES | {STATE_HUMAN_WIP}
# Un-routed: nobody has decided whether the fleet may take it. This was equal to
# UNSTARTED_STATE_NAMES until `Intake · decision` arrived, and the two diverge
# exactly as this comment always said they would: that park is `started` by type (the
# same owner reason `Needs answer` is) but un-routed by INTENT — a shaped idea whose next
# move belongs to a person on the fleet page, which is what the `Assign to Agents` view is
# for. Deriving the state's view from here, rather than seeding it into `Ideas` by hand, is
# what gives a misfiled non-idea a HOME: the `Ideas` view is kind-filtered on
# `Type:idea`, so a bug dragged into the idea park would otherwise be claimed by a view that
# cannot show it — the invisibility, one state later. Now it surfaces in `Assign
# to Agents` and `invariant_violations()` reds the gate, the `Needs Design`-without-`prd`
# shape on the kind axis.
UNROUTED_STATES = UNSTARTED_STATE_NAMES | {STATE_INTAKE_DECISION}
# The idea inventory spans everything open except the two human QUEUES and Parked,
# each of which owns its issue in its own view. `Human WIP` stays IN: a held idea is
# still an idea, and that is the pre-migration behaviour — the old Ideas view
# excluded the human markers but never `human-wip`.
#
# `Intake · decision` is in it through UNROUTED_STATES: a shaped idea waiting
# for its verdict on the fleet page is still an idea, and the `Ideas` view is where the
# page's inventory of them lives. It is deliberately NOT listed here by name — every
# inventory state is claimed by exactly one kind-agnostic view (un-routed, the agent pool,
# `Human WIP`) and `Ideas` overrides on `Type:idea` on top; a state that lived ONLY in this
# set would have no view for a non-idea.
IDEA_INVENTORY_STATES = UNROUTED_STATES | AGENT_POOL_STATES | {STATE_HUMAN_WIP}
# Every open state, derived INDEPENDENTLY of the view sets above — from the migration
# states (`STATE_TYPES`) plus the four that predate them — so the "no open state is
# invisible" test is a real check rather than a tautology. Building it out of
# AGENT_POOL_STATES et al. would make dropping a state from a view also drop it from
# the thing that verifies the view, which is the class wearing a new hat.
OPEN_LIFECYCLE_STATE_NAMES = frozenset(STATE_TYPES) | UNSTARTED_STATE_NAMES | {PARKED_STATE}

# The three terminal positions, by NAME. They already existed on the ENG team, so the
# migration neither created nor renamed them; they are named here only so the lifecycle
# enumeration below can be TOTAL. `Duplicate` is a state of its own type, not a flavour
# of `Canceled` — see CLOSED_STATE_TYPES.
DONE_STATE = "Done"
CANCELED_STATE = "Canceled"
DUPLICATE_STATE = "Duplicate"
TERMINAL_STATE_NAMES = frozenset({DONE_STATE, CANCELED_STATE, DUPLICATE_STATE})

# EVERY position an agent-managed issue can be in, and the enumeration a fail-CLOSED
# gate is built against. This used to describe itself as an exact mirror of
# the dispatcher's `lifecycle.Position` — see the note on the state constants above
# for why no such cross-repo claim is made any more: it was unverifiable from here
# and made it wrong. What holds is checked instead, against the live board
# (a label ensure).
#
# A gate written as "hold these positions" fails OPEN for a position added later, and
# has already done so once: `linear_sync.rewinds_live_state` short-circuited on the
# state TYPE, so `Implement Queue` and `Triage Queue` (both `unstarted`) were projected back onto
# `Spec` on every push to main — silently emptying the fleet's runnable pool, because
# neither the sync nor the daemon logs a position it merely declined to look at. A gate
# written as "these are the positions I OWN, hold every other" cannot fail that way, and
# a test that asserts its table covers this set cannot be extended without a verdict for
# the new position. `In Progress` / `In Review` are deliberately absent: they are the
# retired pre-migration execution states and no longer exist on the ENG team at all.
ALL_LIFECYCLE_STATE_NAMES = OPEN_LIFECYCLE_STATE_NAMES | TERMINAL_STATE_NAMES

# ── What an automated sweep may close (the watchdogs' fail-CLOSED allowlist) ──
# A nightly watchdog files a bare tracking issue, then closes it when its lane
# recovers. It owns that close ONLY while the issue is still the bare alert it
# filed — and "still where I left it" is a statement about the lifecycle
# POSITION, never about the state `type`.
#
# The type is what the guard used to read (`state_type not in
# UNSTARTED_STATE_TYPES`), and the migration turned that into a live hazard: the
# two new pre-execution positions `Triage Queue` and `Implement Queue` are BOTH `unstarted`, so
# an alert issue that `check` had triaged and RELEASED INTO THE FLEET'S
# POOL read as un-owned, and the sweep could flip live queued work to `Done`.
#
# Stated as an allowlist rather than a blocklist for the same reason
# `ALL_LIFECYCLE_STATE_NAMES` exists: a blocklist fails OPEN for a position added
# later, which is how this bug shipped twice. A position nobody has classified
# yet holds the close, which costs at most a comment the watchdog would have
# skipped — the safe direction, and the one this module already chose for the
# sync's `SYNC_WRITABLE_STATES`.
#
#: watchdogs file into `Triage Queue` (the only birth state `check`
# sweeps). Filing into Triage Queue is NOT the handoff — the handoff markers
# are re-label / project / PR / start (`ownership_blockers`). A bare alert still
# resting in Triage Queue must self-close on recovery, or every recovered lane leaks
# an open issue. `Backlog` stays for any legacy bare alert the pre-
# filer left there. `Implement Queue` and every claimed position remain un-closable.
WATCHDOG_CLOSABLE_STATES = frozenset({BACKLOG_STATE, STATE_TRIAGE})

# The rule the watchdogs enforce, asserted rather than commented: an issue the
# fleet has *released or claimed* is NEVER closable by an automated sweep.
# Triage Queue is in AGENT_POOL_STATES (check dispatches there) but is also the birth
# state of a bare alert, so it is carved out of the never-close set.
WATCHDOG_NEVER_CLOSE_STATES = AGENT_POOL_STATES - {STATE_TRIAGE}
assert not (WATCHDOG_CLOSABLE_STATES & WATCHDOG_NEVER_CLOSE_STATES), (
    f"a watchdog may not close a position the fleet owns: "
    f"{sorted(WATCHDOG_CLOSABLE_STATES & WATCHDOG_NEVER_CLOSE_STATES)}"
)
assert WATCHDOG_CLOSABLE_STATES <= ALL_LIFECYCLE_STATE_NAMES, (
    "the watchdogs' allowlist must name real lifecycle positions: "
    f"{sorted(WATCHDOG_CLOSABLE_STATES - ALL_LIFECYCLE_STATE_NAMES)}"
)

# ---------------------------------------------------------------------------
# The seven views, in PRECEDENCE order (first match wins). Linear saved views are
# independent filters with no native precedence, so `classify()` is the canonical
# arbiter and the SOP renders each view's filter WITH the exclusions that encode
# this same precedence. Keep the two in lockstep.
#
# NEEDS_MY_DECISION is the ONLY human view that gates the fleet. MY_ACTION_QUEUE
# holds a context switch (a GCP console, an SSH session, a merge review) and blocks
# no agent, but the unblock drain takes both to zero: every item handled, or its
# runnable instructions in the human's hands.
# ---------------------------------------------------------------------------
NEEDS_MY_DECISION = "Needs My Decision"
MY_ACTION_QUEUE = "My Action Queue"
PARKED = "Parked"
IDEAS = "Ideas"
AGENT_BACKLOG = "Agent Backlog"
ASSIGN_TO_AGENTS = "Assign to Agents"
#: the `human-wip` inventory view — a deliberate hold must be VISIBLE, not
# just distinguishable from a dropped label. It is the one view with no routing
# intent (nothing is owed), so it is deliberately last in precedence.
HUMAN_WIP_VIEW = "My WIP"
VIEWS = (NEEDS_MY_DECISION, MY_ACTION_QUEUE, PARKED, IDEAS, AGENT_BACKLOG, ASSIGN_TO_AGENTS, HUMAN_WIP_VIEW)

# A `human-wip` hold is a deliberate pause, but a pause with no timer is an
# abandonment in disguise (harm: PRs sat held until they re-conflicted).
# This is the staleness threshold for the My WIP inventory's signal: a hold whose
# last update is this many days old reads as abandoned and is flagged in `--list`.
HUMAN_WIP_STALE_DAYS = 3


@dataclass(frozen=True)
class ViewFilter:
    """What one live Linear saved view's filter must reference to still implement
    the partition. A *subset* contract, not equality: the live view may reference
    more (a stale label nobody has cleaned up costs nothing), but never less."""

    include: frozenset[str]  # labels the filter must positively match ("has one of these")
    exclude: frozenset[str]  # labels it must exclude ("has none of these") — this is how precedence is encoded
    states: frozenset[str]  # workflow-state NAMES its status filter must cover


def expected_view_filters() -> dict[str, ViewFilter]:
    """What each of the seven partition views' LIVE Linear saved-view filter MUST
    reference, for a saved-view drift check
     — built from the SAME constants the pipeline routes on, so a
    vocabulary change here is caught the moment the live views aren't updated to
    match, instead of the views silently going stale.

    Three incidents shaped this, and they are three different failure modes:
      • labels (2026-07-24) — the `needs-human` split landed here and in
        `classify()` while the saved views kept filtering on the retired label, so
        14 issues needing a human became invisible in every view;
      • states (2026-07-24) — "Assign to Agents" enumerated only the
        un-started state names, so routing a stranded `In Review` issue there in
        `classify()` would have changed nothing on the board. The check saw labels
        only and was structurally blind to it, which is why `states` exists;
      • the migration (2026-08-27, design P4.3) — the lifecycle moved into the
        workflow state and the backfill stripped all 11 routing labels from every
        open issue. Every view keyed on one then matched NOTHING: four of the
        seven — both human queues among them — silently returned zero while the
        board itself was healthy. Same class as, one vocabulary later.

    **The predicate is the STATE now, and it is POSITIVE.** No view carries a
    lifecycle exclusion list any more: the states are disjoint by construction, so
    there is no coexistence left to exclude. The only exclusions that survive are
    `Type` labels (`idea`, `customer-bug`) — an orthogonal axis, a KIND rather than
    a position, untouched by the migration (design §4.4).

    Mirrors the view table in .claude/registers/triage-partition.md — keep the
    two in lockstep.
    """
    return {
        NEEDS_MY_DECISION: ViewFilter(frozenset(), frozenset(), NEEDS_MY_DECISION_STATES),
        MY_ACTION_QUEUE: ViewFilter(frozenset(), frozenset(), ACTION_STATES),
        PARKED: ViewFilter(frozenset(), frozenset(), frozenset({PARKED_STATE})),
        IDEAS: ViewFilter(frozenset({TYPE_IDEA}), frozenset(), IDEA_INVENTORY_STATES),
        # The fleet-owned pool. `Triage Queue` belongs here because the daemon dispatches
        # `check` on a Triage Queue issue ITSELF — it is agent work, not a human's
        # to route. The label world got that wrong for a structural reason: a
        # `to-be-checked` issue carried no `agent-eligible`, so it could only fall
        # through to the human catch-all. `Intake Queue` joins on the same test: a
        # dispatched command owns the item while it rests there.
        AGENT_BACKLOG: ViewFilter(frozenset(), frozenset({TYPE_IDEA}), AGENT_POOL_STATES),
        # The deliberate-hold inventory. It needs no label predicate at
        # all now — `Human WIP` IS the hold — and no precedence exclusions, because
        # an issue in that state is in no other view's state set.
        HUMAN_WIP_VIEW: ViewFilter(frozenset(), NON_WORK_KINDS, frozenset({STATE_HUMAN_WIP})),
        # Un-routed work a human must decide on. It no longer needs the started
        # states, and that is being CLOSED rather than forgotten: stranding
        # — a started issue carrying no routing marker — is unrepresentable once
        # every issue has exactly one state, and every started state is claimed by
        # exactly one view above.
        ASSIGN_TO_AGENTS: ViewFilter(frozenset(), NON_WORK_KINDS, UNROUTED_STATES),
    }


def _build_view_by_state() -> dict[str, str]:
    """The state → view lookup, built from the SAME sets `expected_view_filters()`
    hands the live saved views. Keying the one table both ways is what makes
    `classify()` and the board unable to disagree (lockstep, now free).

    Built by a loop with a duplicate check rather than written as a dict literal, and
    that is not style. A state claimed by two view sets would silently lose one binding
    in a `{**a, **b}` merge — the loser being whichever was written first — which is a
    routing change nobody wrote and nobody can see in review. Here it raises at import.

    `Ideas` is deliberately absent: it is the one view that filters on the KIND axis
    (`Type:idea`) and therefore cuts ACROSS the lifecycle rather than claiming a
    position of its own. `classify()` applies it as an override, not as a row here.
    (briefly seeded `Intake · decision` → `Ideas` here as the one exception;
     undid that — a non-idea in the park was then claimed by a view whose own
    filter could not show it. The park is un-routed by intent and rides `UNROUTED_STATES`.)
    """
    out: dict[str, str] = {}
    for view, states in (
        (NEEDS_MY_DECISION, NEEDS_MY_DECISION_STATES),
        (MY_ACTION_QUEUE, ACTION_STATES),
        (PARKED, frozenset({PARKED_STATE})),
        (AGENT_BACKLOG, AGENT_POOL_STATES),
        (ASSIGN_TO_AGENTS, UNROUTED_STATES),
        (HUMAN_WIP_VIEW, frozenset({STATE_HUMAN_WIP})),
    ):
        for st in states:
            if st in out:
                raise AssertionError(
                    f"workflow state {st!r} is claimed by both {out[st]!r} and {view!r} — "
                    "the lifecycle states must be disjoint (design §4.1)"
                )
            out[st] = view
    return out


# Every open lifecycle state → the single view that owns it. This IS the partition:
# one lookup, no precedence cascade, because an issue has exactly one state.
VIEW_BY_STATE: dict[str, str] = _build_view_by_state()


@dataclass(frozen=True)
class IssueView:
    """The single view an open issue belongs to, or a deliberate carve-out."""

    view: str | None  # one of VIEWS, or None when the issue is in NO view
    reason: str  # why — human-readable, for the guardrail report


def classify(
    *,
    state_name: str,
    state_type: str,
    labels: frozenset[str],
    has_unmet_blockers: bool = False,
) -> IssueView:
    """The deterministic partition function — every open issue → exactly one view.

        **A lookup, not a cascade.** The lifecycle position is the workflow STATE, an issue
        has exactly one, and every open state is claimed by exactly one view
        (`VIEW_BY_STATE`), so the view falls out of a single dict read. The six-level
        precedence cascade this replaced existed only to arbitrate between labels that could
        all be set at once; with the coexistence gone, so is the arbitration.

        Two things still sit ON TOP of the lookup, and both are the KIND axis, not the
        position axis — `Type:` stays a label deliberately (design §4.4):

          • `Type:idea` overrides wherever the Ideas view claims the state
            (`IDEA_INVENTORY_STATES` — un-routed, the agent pool, and `Human WIP`). Where it
            does NOT claim it (the two human queues, `Parked`) the state wins, so an idea a
            human must answer still lands in the decision queue.
          • `Type:customer-bug` is a separate track, so it is carved OUT of exactly the two
            views whose live filters exclude it (`Assign to Agents`, `My WIP`). It is NOT
            carved out of the agent pool: a customer bug the fleet is actually running is
            agent work, and the pre-migration classifier agreed — `agent-eligible` outranked
            this carve-out there too.

        `has_unmet_blockers` is whether any `blockedBy` relation points at a still-open
        issue. It suppresses ONLY the action queue, never the decision queue — a deliberate
        asymmetry: a decision is cheap, forward-looking and usually what unblocks the chain,
        so it surfaces early; an action costs a context switch and is worthless before its
        dependency lands, so it surfaces only when runnable.

        **Stranding is gone, not forgotten**. The old classifier had
        two stranding branches because "zero routing labels" was a representable state that
        meant nothing at all, and the carve-out that used to swallow it inferred human
        ownership from a MISSING label. Neither shape exists now: absence is unrepresentable
        in a state field. What replaces them is an unrecognised STATE — and that is routed to
        `Assign to Agents` AND reported by `invariant_violations()`, because the ENG state
        vocabulary is the routing table, so a state outside it is a vocabulary fault rather
        than an undecided issue. The lesson those incidents taught survives as its own rule:
        never infer a position from something absent.

        **Closed issues are out of the partition entirely**, and that is a change from
    . A closed issue that still carries `needs-decision` used to route to the
        decision queue, because the label was then the ONLY store of "a human owes an
        answer" and closure hid it. It is not the store any more: the park is a STATE, and
        `Done` and `Blocked · decision` are the same field — so "closed while a human
        question was outstanding" is no longer a coexistence to detect, it is a state that
        was overwritten. The residue on the closed tail is inert history the design
        deliberately keeps (§8.6 / P4.7). The signal itself is not dropped: it is carried by
        the COMMENT-derived detector (`unanswered_closed_parks`), which never depended on a
        label and is now the complete detector rather than a residual.

        Pure: same inputs → same output. This is what makes routing reproducible and
        LLM-independent — the classifier decides, not a prompt.
    """
    # Fold a pre-rename board spelling onto this repo's vocabulary before any
    # comparison — every consumer of the partition arrives through
    # here, so folding at the entry point beats folding at each call site.
    state_name = canonical_state_name(state_name)
    if state_type in CLOSED_STATE_TYPES:
        return IssueView(None, "closed (done/canceled/duplicate) — in no lifecycle view")

    view = VIEW_BY_STATE.get(state_name)
    if view is None:
        # Not a lifecycle state. `In Progress` / `In Review` are the live examples —
        # retired by the migration and archived once empty (P4.6), so an issue landing
        # in one means a writer that was supposed to be gone is still writing. Route it
        # somewhere a human looks; `invariant_violations()` reds the guardrail besides,
        # which is the louder half and the reason this fall-through is never silent.
        return IssueView(
            ASSIGN_TO_AGENTS,
            f"in `{state_name}`, which is not a lifecycle state — reported as an invariant violation",
        )

    if TYPE_IDEA in labels and state_name in IDEA_INVENTORY_STATES:
        return IssueView(IDEAS, f"`Type:{TYPE_IDEA}` in `{state_name}`")
    if TYPE_CUSTOMER_BUG in labels and view in (ASSIGN_TO_AGENTS, HUMAN_WIP_VIEW):
        return IssueView(None, f"`Type:{TYPE_CUSTOMER_BUG}` — separate Customer Bugs track")
    if view == MY_ACTION_QUEUE and has_unmet_blockers:
        return IssueView(None, f"in `{state_name}` but blocked — surfaces when its blocker closes")
    return IssueView(view, f"in `{state_name}`")


def invariant_violations(
    *,
    state_name: str,
    state_type: str,
    labels: frozenset[str],
    created_on: str = "",
) -> list[str]:
    """Data-integrity problems on an OPEN issue. Fatal — this is what reds the gate.

    The set shrank hard in the lifecycle migration, and every removal is a fault that
    became UNREPRESENTABLE rather than one that stopped being checked:

      • *"N routing markers coexist"* — the at-most-one rule. An issue has exactly one
        state, so at-most-one is now true by construction. This is the check whose
        triviality is what lets the guardrail afford to block on every PR (design P4.5).
      • *`to-be-checked` + `agent-eligible`* — the half-done check release. It existed
        because clearing the gate meant writing a whole label array in ONE `save_issue`
        (Linear replaces the entire set), so two writes or a miscomputed array left the
        issue at the gate while the board called it fleet work. A transition is one
        field write now; there is no half-written state to land in.
      • *`Parked` + `agent-eligible`* —, the daemon grabbing a deliberately
        deferred issue because `Parked` is a `backlog`-TYPE state. The label is inert, so
        it can no longer make anything grab anything. ⚠️ The lesson is NOT retired and is
        the more important half: the dispatch gate must key on the state NAME, never the
        type (design §4.2). That belongs in a dispatch-path test, not here.
      • *closed + a human marker* —. See `classify()`: a closed issue's
        routing labels are inert history the design deliberately preserves so
        `linear-agent costs` can still reach recorded spend (§8.6 / P4.7), and the live
        signal is comment-derived now. Failing on the tail would red every PR in the repo
        over ~4,000 issues nobody may touch.

    What survives is what a state field does NOT make impossible — an orthogonal-axis
    label conflict, a state outside the vocabulary, and a free-typed spelling.
    """
    # Fold a pre-rename board spelling onto this repo's vocabulary before any
    # comparison — every consumer of the partition arrives through
    # here, so folding at the entry point beats folding at each call site.
    state_name = canonical_state_name(state_name)
    out: list[str] = []

    # Closed issues are out of the partition (see the docstring + classify()). Return
    # before near_miss() too: the closed tail carries retired spellings on purpose.
    if state_type in CLOSED_STATE_TYPES:
        return out

    # The ENG state vocabulary IS the routing table now, so a state outside it routes
    # nothing and appears in no saved view — the shape in the new field. Named
    # loudly rather than guessed at: `In Progress` / `In Review` are retired (P4.6) and
    # an issue in one means a writer we believed gone is still writing.
    if state_name not in OPEN_LIFECYCLE_STATE_NAMES:
        out.append(
            f"in `{state_name}`, which is not a lifecycle state — no saved view can show it "
            f"(the ENG state vocabulary is the routing table; add it to linear_labels.py and to a "
            f"view, or move the issue onto one of {sorted(OPEN_LIFECYCLE_STATE_NAMES)})"
        )

    # A repo-lane label says WHERE agent work runs, not whether it's eligible — orthogonal
    # to the lifecycle, but an issue can only be dispatched to ONE checkout, so at most one
    # `repo:*` label may be present (absence = the default lane).
    lanes_present = repo_lanes(labels)
    if len(lanes_present) > 1:
        out.append(f"{len(lanes_present)} repo-lane labels coexist: {sorted(lanes_present)} (invariant: at most 1)")

    # The pre-flight gate on a kind the gate can never run —, re-expressed
    # for the state. `Triage Queue` means "a checker owes this a triage"; `Type:idea` /
    # `Type:customer-bug` mean "never dispatched". The pair is a contradiction nothing
    # resolves, and it is still INVISIBLE to every other guard here:
    #   • `classify()` MASKS it — the Ideas override fires on `Triage Queue` (it is an agent-pool
    #     state), so the issue sits in the Ideas view and never reaches a checker's queue.
    #   • `requires_priority()` exempts it twice — once for the idea, once for the gate.
    # The two issues that taught this sat in the shape for 9 days with `updatedAt` never
    # moving off `createdAt`, and no box logged a word about either. Either the type is
    # wrong (real work needing a work kind) or the state is (a genuine idea waiting on a
    # check that can never be dispatched); both are dirty data to fix at the source.
    parked_kinds = NON_WORK_KINDS & labels
    if state_name == STATE_TRIAGE and parked_kinds:
        out.append(
            f"in `{STATE_TRIAGE}` with {sorted(f'`Type:{k}`' for k in parked_kinds)}, which is "
            f"never dispatched — no daemon can run the check it is waiting for; give it a work kind "
            f"({', '.join(sorted(WORK_KINDS))}) or move it out of `{STATE_TRIAGE}`"
        )

    # A non-PRD in a PRD-pipeline state. Pipeline states project PRD frontmatter
    # `status:` (git-owned, stomped by every sync); for any other type the state is
    # meaningless and was set by hand — Linear can't scope states per issue type,
    # so this invariant is the only thing keeping the pipeline PRD-only.
    if state_name in PRD_PIPELINE_STATES and TYPE_PRD not in labels:
        out.append(
            f"in PRD-pipeline state `{state_name}` without `{TYPE_PRD}` — pipeline states are "
            "projected from PRD frontmatter and only PRDs may hold them; move it back to Backlog"
        )

    # The same rule on the kind axis. `Intake · decision` is where a SHAPED IDEA
    # waits for a person's verdict on the fleet page, and the intake command is
    # idea-only by a hard gate — so anything else resting here was dragged by hand. It is
    # visible (`classify()` routes it to `Assign to Agents` like every un-routed state), and
    # this is what makes the misfiling fatal rather than merely odd.
    if state_name == STATE_INTAKE_DECISION and TYPE_IDEA not in labels:
        out.append(
            f"in `{STATE_INTAKE_DECISION}` without `Type:{TYPE_IDEA}` — that park holds only a shaped "
            f"idea awaiting its verdict on the fleet page; give it `Type:{TYPE_IDEA}` or move it to "
            f"`{STATE_TRIAGE}`"
        )

    #: a gated work kind may never REST in `Backlog`. `Backlog` is the birth
    # state of ideas and the projection of a stub PRD; agent-filed work is born in
    # `Triage Queue`, and `Backlog` dispatches nothing — so a gated kind resting here skipped
    # the check gate entirely. That is exactly the misfiling class:
    # filed into `Backlog`, never checked, one stayed a live duplicate for 2h, and both
    # reddened every PR in the repo through the priority rule alone. Unconditional on
    # purpose (same doctrine as the priority rule): partition dirt is fatal whoever
    # created it, and the fix — move it to `Triage Queue` — is the same either way. Audits
    # are exempt (outside the check gate; recurring audits park in `Backlog` by
    # design), and filings before BACKLOG_MISFILE_CUTOFF are grandfathered.
    if state_name == BACKLOG_STATE and (kinds := labels & GATED_KINDS):
        if created_on and created_on[:10] < BACKLOG_MISFILE_CUTOFF:
            pass  # grandfathered — the rule did not exist when this was filed
        else:
            out.append(
                f"in `{BACKLOG_STATE}` with {sorted(f'`Type:{k}`' for k in kinds)}, which is "
                f"agent-filed work that never rests here — `{BACKLOG_STATE}` dispatches nothing, so "
                f"the check gate never ran (ENG-9323/ENG-9336); move it to `{STATE_TRIAGE}`"
            )

    out.extend(near_miss(labels))
    return out


def migration_warnings(*, state_type: str, labels: frozenset[str]) -> list[str]:
    """Reported, never fatal — findings a reader of a red CI run cannot clear right now.

    Distinct from `invariant_violations()` on purpose: a violation is dirty data someone
    can fix right now, whereas these findings start an investigation — hunting an
    unknown writer is not a fix a reader can land from inside a red CI run. Hard-failing
    on one would redden CI for a condition the person reading the failure is not able to
    clear — which trains people to pass `--warn-only` permanently, and that is how a
    guardrail dies. This distinction is what makes the gate safe to flip blocking
    (design P4.5): everything that is not a right-now fix lands HERE, and only here.

    The retired routing labels: the P4.1 dual-write era is OVER. proved the
    last real writer was THIS repo's audit filer (`knowledge/scripts/audit.py`, fixed by
    ) — not the sibling repo's daemon — and nothing stamps the labels any more.
    Every open issue was stripped in the backfill, so a label reappearing on one means
    a writer nobody accounted for: worth seeing, never worth blocking, and worth a
    fresh hunt in THIS repo first.
    """
    if state_type in CLOSED_STATE_TYPES:
        return []
    out: list[str] = []
    vestigial = VESTIGIAL_ROUTING_LABELS & labels
    if vestigial:
        out.append(
            f"carries retired routing label(s) {sorted(vestigial)} — the lifecycle position is the "
            f"workflow state now; nothing routes on these. Harmless in itself, but a label back on an "
            f"OPEN issue means an UNKNOWN writer: the P4.1 dual-write era is over (ENG-9800 proved "
            f"the last real writer was this repo's audit filer, now fixed) — hunt this repo first"
        )
    return out


def near_miss(labels: frozenset[str]) -> list[str]:
    """Flag labels that normalize to a canonical routing label but aren't it exactly
        — i.e. an LLM free-typed `agent_eligible` / `Agent-Eligible` / `needs_human`.
        Case- and separator-insensitive; the only accepted spelling is the exact one.

    `Type:bug` is the repo's *notation* for "the `bug` label under the
        `Type` parent" — not a real label name. An agent that passes the notation as the
        literal string to `save_issue.labels` mints a flat, parentless label whose
        `parent` is `None`, which the daemon's parent-group routing gate cannot see.
        `norm()` strips a leading `type:` / `type › ` / `type-` prefix so the impostor
        reports as a near-miss of its canonical bare kind instead of passing clean.
    """

    def norm(s: str) -> str:
        n = s.lower().replace("_", "-").replace(" ", "-")
        if len(n) > 4 and n.startswith("type") and n[4] in (":", "-", "›"):
            n = n[4:].lstrip(":-›")
        return n

    canon_by_norm = {norm(c): c for c in CANONICAL_LABELS}
    out: list[str] = []
    for lb in labels:
        if lb in CANONICAL_LABELS:
            continue
        # The lane family is a prefix, not a closed set, so a near-miss is judged on the
        # prefix: `Repo:Apps` / `repo_infra` normalise to `repo:…` / `repo-…` and are
        # a free-typed lane, which the dispatcher's table (`repo:<name>`, exact) cannot see.
        n = norm(lb)
        if not is_repo_lane(lb) and (n.startswith(REPO_LANE_PREFIX) or n.startswith("repo-")):
            spelled = REPO_LANE_PREFIX + n.split(":", 1)[-1] if ":" in n else REPO_LANE_PREFIX + n[len("repo-") :]
            out.append(f"non-canonical lane label `{lb}` — a lane is `repo:<name>`, lowercase: `{spelled}`")
            continue
        # The source family is a prefix too (one canonical member today), so a free-typed
        # `source_product` / `Source-Product` names `source:product` rather than passing as an
        # unknown label the fleet would never match a request on.
        if not is_source_label(lb) and (n.startswith(SOURCE_PREFIX) or n.startswith("source-")):
            spelled = SOURCE_PREFIX + (n.split(":", 1)[-1] if ":" in n else n[len("source-") :])
            out.append(f"non-canonical source label `{lb}` — a source is `source:<name>`, lowercase: `{spelled}`")
            continue
        c = canon_by_norm.get(norm(lb))
        if c is not None:
            out.append(
                f"non-canonical label `{lb}` — the canonical spelling is `{c}` (see knowledge/scripts/linear_labels.py)"
            )
    return out


def human_wip_age(updated_at: str, *, now: str | None = None) -> tuple[str, bool]:
    """Age + staleness of a `human-wip` hold, for the `My WIP` inventory.

    Returns `(age, stale)` where `age` is a short human string (`"5h"`, `"2d"`) and
    `stale` is True once the hold has sat without an update past
    `HUMAN_WIP_STALE_DAYS`. `updated_at` is Linear's timestamp (the last
    mutation — applying the hold updates it, so it is the best available proxy for
    "how long held"); `now` is injectable so callers/tests are deterministic.

    Pure + stdlib-only so it can live next to the classifier.
    """
    from datetime import datetime

    def _parse(ts: str) -> datetime:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)

    then = _parse(updated_at)
    ref = _parse(now) if now else datetime.now(UTC)
    delta = ref - then
    days = delta.days
    if days >= HUMAN_WIP_STALE_DAYS:
        return f"{days}d", True
    if days >= 1:
        return f"{days}d", False
    hours = int(delta.total_seconds() // 3600)
    return f"{hours}h", False


if __name__ == "__main__":
    # Tiny self-test / human-readable dump of the registry.
    print("Canonical routing labels:", ", ".join(sorted(CANONICAL_LABELS)))
    print("Parked state:", PARKED_STATE)
    print("Views (precedence):", " > ".join(VIEWS))
