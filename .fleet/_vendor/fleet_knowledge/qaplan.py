"""Tonight's plan for the QA agent: which promises it checks, in what order, and where it may not.

The decision record `the-quality-desk-checks-promises-per-release` gives the QA agent a licence
and a work queue (**[FLT-1226]**): for a promise the product has already shipped it writes and
maintains the scenarios that prove it, and the night's run budget is split between **re-checks**
(re-running a scenario whose promise is failing, flaky, can't run or out of date) and **new
coverage** (writing a scenario for a promise with no check yet). This module is the pure half of
that loop — what the night holds and why — and it decides nothing about time, rows or issues:

- `read_qa_config` reads the `qa` table a corpus declares under `[fleet.recurring]` in its own
  `fleet.toml`. Absent, the QA loop is off; present, every field it leaves out takes its default.
- `split_budget` divides the room the nightly cap has left between the two modes.
- `plan_night` ranks the candidates and fills the two budgets, refusing — before anything runs —
  every run the environment guard forbids (**[FLT-1204]**).

### Which promise first

The order is total, so two passes over one reading propose the same night:

1. **risk tier** — the area's authored tier, `core` before `rotation` before `parked`, untiered
   last (`quality.TIER_RANK`, the one ordering the desk already uses);
2. **journey first** — inside a tier, a journey's step (`kind: criterion`, an id shaped
   `<journey>#<n>`) comes before a single rule or capability;
3. **state** — for a re-check, failing before flaky before can't run before out of date; for new
   coverage, no check yet before out of date;
4. **age** — the oldest last pass first, and a promise that never passed before any that did;
5. **id**, so a tie still has one answer.

**Areas are taken in turn inside each (tier, journey-first) group** — the best run of each area,
then each area's second, and so on — so one area with forty open promises cannot take every slot
of a night while another area's tier-1 promise waits. Tiers are never interleaved: a `core`
promise always outranks a `rotation` one, and inside a tier a journey step outranks a rule or
capability.

A run is a **scenario** for a re-check, or a **journey** for new coverage of its steps. A re-check
reruns a scenario, and one scenario usually proves several promises; every promise it proves rides
that run (`also`) instead of spending a slot of its own. A promise proved by several scenarios is
rerun through the one that holds the check which decided its state — a different scenario cannot
clear that check — and through the first runnable scenario only when no scenario holds the
deciding check. New coverage of a journey's open steps likewise folds into one run: the best-ranked
step hosts it and the others ride. A rider spends no slot and may sit in another area or tier,
keeping the host's place in the plan. A run already decided tonight is not planned again, and a
journey with a step on tonight's re-check takes no new-coverage run that night.

### The environment guard (FLT-1204)

Safety is data the scheduler enforces. A run is refused, with its reason, when its environment has
no record, when the record's org is not on the corpus's allow-list (`orgs`; an empty list allows
nothing), when the record is paused, when the scenario names a role no login on the environment
holds, when a new-coverage run's environment declares no login at all (it writes a scenario whose
steps must sign in, and no role it could name would be held, so the slot would only be spent on a
run-time refusal), or when the environment is production and tonight's writing runs there have
reached `production_writes`. A `kind: local` environment is exempt from the org and login checks
— it is a stack on the operator's own machine, with no org and no sign-in — and every other check
still applies. A refused run spends no slot; the next candidate takes it — but a mode
stops after `refusal_limit` refusals **in one night** (counted across every pass of the night
through `refused_tonight`, and sized from the mode's configured slots), so a misconfigured
environment — which refuses every candidate that runs there — records a handful of reasons rather
than one row per open promise, however many times the scheduler plans the night.

Stdlib only; no clock, no I/O.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import PurePosixPath
from typing import Any, Final

from .quality import (
    CANT_RUN,
    FAILING,
    FLAKY,
    NO_CHECK,
    OUT_OF_DATE,
    TIER_RANK,
    UNFINISHED,
    WAIT_APPROVAL,
    WAIT_RELEASE,
    ApprovedVersion,
    quarantine_active,
)

__all__ = [
    "CUSTOMER_KIND",
    "DEFAULT_CONFIG",
    "PRODUCTION_TARGET",
    "NEW",
    "QA_FIELDS",
    "RECHECK",
    "TEST",
    "TEST_TYPES",
    "Budget",
    "Plan",
    "PlanItem",
    "QaConfig",
    "QaSuite",
    "Refusal",
    "environment_refusal",
    "is_production_write",
    "journey_slug",
    "over_cap_problem",
    "plan_night",
    "refusal_limit",
    "read_qa_config",
    "run_of",
    "split_budget",
]

#: The three kinds of QA work a night holds — the `reason` every plan row carries.
NEW: Final = "new"
RECHECK: Final = "recheck"
TEST: Final = "test"

#: The test types a suite may declare, in the desk's own order (PRD 0998, FLT-2447).
TEST_TYPES: Final[tuple[str, ...]] = ("unit", "integration", "end-to-end")

#: The promise states a re-check is for, most urgent first. `disputed` is absent on purpose: a
#: disputed pass is the verifier's to settle, and rerunning the runner's own check would only
#: produce another pass for the verifier to doubt. `quarantined` and `passing` need nothing.
_RECHECK_ORDER: Final[Mapping[str, int]] = {FAILING: 0, FLAKY: 1, CANT_RUN: 2, OUT_OF_DATE: 3, UNFINISHED: 4}

#: The promise states new coverage is for: no check yet, then out of date with no scenario to rerun
#: (its only check is a journey walk or a checklist item the QA agent does not drive).
_NEW_ORDER: Final[Mapping[str, int]] = {NO_CHECK: 0, OUT_OF_DATE: 1}

#: The keys the `qa` table may carry, and no others — an unknown key is a typo reported by name.
QA_FIELDS: Final[frozenset[str]] = frozenset(
    {"rechecks", "new", "production_writes", "orgs", "hosts", "environment", "suites", "tests"}
)

#: The keys one `suites` entry may carry, and no others — PRD 0998 adds its field here.
_SUITE_FIELDS: Final[frozenset[str]] = frozenset({"name", "path", "run", "type"})

#: What a record's `writes` field says when a run there writes nothing.
_READ_ONLY_WRITES: Final[frozenset[str]] = frozenset({"none", "read-only", "readonly", "no", "false"})


@dataclass(frozen=True, slots=True)
class QaSuite:
    """One declared test suite: where QA-written tests go and how the project runs them."""

    name: str
    path: str
    run: str
    type: str = ""


@dataclass(frozen=True, slots=True)
class QaConfig:
    """The `qa` table under `[fleet.recurring]`: the night's split and the guard's data.

    `rechecks` and `new` are the slots each mode may take in one night, out of the room the
    install's nightly cap has left. `production_writes` is how many writing runs one production
    environment may take in one night. `orgs` is the allow-list a run's environment org must be on
    — the e2e guard's list, stated as data the scheduler can enforce. `hosts` is the allow-list a
    run's `base_url` host must be on before the sign-in helper sends a credential there; the
    helper reads it from this table, so it is the one trusted answer to "where may a QA login go".
    `environment` is where new coverage runs when nothing else names one. `suites` are the
    project's test suites and `tests` names the one that takes QA-written tests; `test_suite`
    resolves that name.
    """

    rechecks: int = 2
    new: int = 4
    production_writes: int = 1
    orgs: tuple[str, ...] = ()
    hosts: tuple[str, ...] = ()
    environment: str = ""
    suites: tuple[QaSuite, ...] = ()
    tests: str = ""

    @property
    def test_suite(self) -> QaSuite | None:
        return next((suite for suite in self.suites if suite.name == self.tests), None)


#: The split when the corpus declares `qa = {}` and nothing else.
DEFAULT_CONFIG: Final = QaConfig()


def _count(raw: Mapping[str, Any], key: str, default: int, problems: list[str]) -> int:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        problems.append(f"qa.{key} must be a whole number of runs (0 or more), got {value!r}")
        return default
    return value


def _read_suites(raw: object, problems: list[str]) -> tuple[QaSuite, ...]:
    """The `suites` list, keeping only entries a test could actually be written into."""
    if not isinstance(raw, list):
        problems.append(f"qa.suites must be a list of tables, got {raw!r}")
        return ()
    suites: list[QaSuite] = []
    for index, item in enumerate(raw):
        label = f"qa.suites[{index}]"
        if not isinstance(item, Mapping):
            problems.append(f"{label} must be a table with name, path and run, got {item!r}")
            continue
        unknown = sorted(str(key) for key in item if key not in _SUITE_FIELDS)
        if unknown:
            problems.append(f"{label} names unknown key(s): {', '.join(unknown)} (known: name, path, run, type)")
        fields: dict[str, str] = {}
        bad = bool(unknown)
        for key in ("name", "path", "run"):
            value = item.get(key)
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{label}.{key} must be a non-empty string, got {value!r}")
                bad = True
                continue
            text = value.strip()
            if "\n" in text or "\r" in text:
                problems.append(f"{label}.{key} must be one line, got {value!r}")
                bad = True
                continue
            if "`" in text:
                problems.append(f"{label}.{key} must not contain a backtick, got {value!r}")
                bad = True
                continue
            fields[key] = text
        declared_type = item.get("type", "")
        if "type" in item and (not isinstance(declared_type, str) or declared_type.strip() not in TEST_TYPES):
            problems.append(f"{label}.type must be one of {', '.join(TEST_TYPES)}, got {declared_type!r}")
            declared_type = ""
        test_type = declared_type.strip() if isinstance(declared_type, str) else ""
        path = fields.get("path")
        if path is not None:
            pure = PurePosixPath(path)
            if pure.is_absolute() or path.startswith("/"):
                problems.append(f"{label}.path must be relative, got {path!r}")
                bad = True
            elif ".." in pure.parts:
                problems.append(f"{label}.path must not contain '..', got {path!r}")
                bad = True
        if not bad:
            suites.append(QaSuite(fields["name"], fields["path"], fields["run"], test_type))
    return tuple(suites)


def read_qa_config(raw: object) -> tuple[QaConfig | None, tuple[str, ...]]:
    """`(config, problems)` for the raw `qa` table — `(None, ())` when the corpus declares none.

    A field of the wrong type keeps its default and is reported; an unknown key is reported and
    ignored. A malformed test declaration is reported and leaves `test_suite` as `None`, so a bad
    declaration is the same as none and nothing is guessed. Never raises: a typo in the table must
    not stop the rest of the night's work, and the merge-time `recurring` check turns the same
    problems into findings.
    """
    if raw is None:
        return None, ()
    if not isinstance(raw, Mapping):
        return None, (f"[fleet.recurring] qa must be a table, got {type(raw).__name__}",)
    problems: list[str] = []
    unknown = sorted(str(k) for k in raw if k not in QA_FIELDS)
    if unknown:
        problems.append(f"qa names unknown key(s): {', '.join(unknown)} (known: {', '.join(sorted(QA_FIELDS))})")
    orgs_raw = raw.get("orgs", [])
    orgs: tuple[str, ...] = ()
    if isinstance(orgs_raw, list) and all(isinstance(o, str) and o.strip() for o in orgs_raw):
        orgs = tuple(o.strip() for o in orgs_raw)
    else:
        problems.append(f"qa.orgs must be a list of org ids, got {orgs_raw!r}")
    hosts_raw = raw.get("hosts", [])
    hosts: tuple[str, ...] = ()
    if isinstance(hosts_raw, list) and all(isinstance(h, str) and h.strip() for h in hosts_raw):
        hosts = tuple(h.strip() for h in hosts_raw)
    else:
        problems.append(f"qa.hosts must be a list of host names, got {hosts_raw!r}")
    environment = raw.get("environment", "")
    if not isinstance(environment, str):
        problems.append(f"qa.environment must be an environment id, got {environment!r}")
        environment = ""
    new = _count(raw, "new", DEFAULT_CONFIG.new, problems)
    suites = _read_suites(raw.get("suites", []), problems)
    tests_raw = raw.get("tests", "")
    tests = ""
    if not isinstance(tests_raw, str):
        problems.append(f"qa.tests must name a declared suite, got {tests_raw!r}")
    elif tests_raw.strip():
        tests = tests_raw.strip()
        if tests not in {suite.name for suite in suites}:
            problems.append(f"qa.tests names no declared suite: {tests!r}")
        elif new < 2:
            problems.append(
                f"qa.tests names suite {tests!r}, but qa.new is {new}: no test slot can ever be taken "
                "(qa.new must be at least 2)"
            )
    config = QaConfig(
        rechecks=_count(raw, "rechecks", DEFAULT_CONFIG.rechecks, problems),
        new=new,
        production_writes=_count(raw, "production_writes", DEFAULT_CONFIG.production_writes, problems),
        orgs=orgs,
        hosts=hosts,
        environment=environment.strip(),
        suites=suites,
        tests=tests,
    )
    return config, tuple(problems)


@dataclass(frozen=True, slots=True)
class Budget:
    """How many re-check and new-coverage runs the night may still file."""

    rechecks: int
    new: int

    @property
    def total(self) -> int:
        return self.rechecks + self.new


def over_cap_problem(config: QaConfig, limit: int | None) -> str | None:
    """A sentence when the QA share is at or above the whole nightly cap, else `None`.

    The nightly cap is ONE number shared by people's briefs, the QA agent's share and the
    recurring schedule, and the priority order spends it briefs → QA → schedule. A share whose
    two modes sum to the whole cap (or more) therefore spends every remaining slot itself: each
    due schedule entry waits. That is a WARNING rather than a refusal (BUG-1190) — a corpus may
    deliberately give QA the night, and the cap is an operator-set runtime number the merge-time
    reader cannot see — so this is surfaced where the cap IS known: the pass's journal and the
    plan read. `None` while no limit is set, because with recurring work off there is no cap to
    be at or above.
    """
    if limit is None:
        return None
    share = config.rechecks + config.new
    if share < limit:
        return None
    return (
        f"qa asks for {share} run(s) a night (rechecks {config.rechecks} + new {config.new}), "
        f"at or above the nightly cap of {limit}: every due schedule entry waits while this share stands"
    )


def split_budget(room: int, config: QaConfig) -> Budget:
    """The night's QA slots when the cap has `room` filings left.

    With room for the whole split, the split stands. With less, the room is shared in proportion,
    and each mode the config gives any slots keeps at least one while there are two to share — so a
    tight night still re-checks something AND covers something new, rather than one mode silently
    starving the other. No room is no QA work.
    """
    wanted_r, wanted_n = config.rechecks, config.new
    if room <= 0 or wanted_r + wanted_n == 0:
        return Budget(0, 0)
    if room >= wanted_r + wanted_n:
        return Budget(wanted_r, wanted_n)
    rechecks = (room * wanted_r) // (wanted_r + wanted_n)
    if wanted_r and rechecks == 0 and (room >= 2 or not wanted_n):
        rechecks = 1
    if wanted_n and rechecks == room and room >= 2:
        rechecks = room - 1
    return Budget(rechecks, room - rechecks)


@dataclass(frozen=True, slots=True)
class PlanItem:
    """One run on tonight's plan: the promise, the scenario, and why it is on the plan.

    `scenario` is empty for new coverage — the run writes it. `also` names the other promises a
    re-check's scenario proves that ride the same run.
    """

    promise: str
    scenario: str
    reason: str
    environment: str
    state: str
    area: str
    tier: str
    also: tuple[str, ...] = ()
    version: int = 0
    promises: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "promise": self.promise,
            "scenario": self.scenario,
            "reason": self.reason,
            "environment": self.environment,
            "state": self.state,
            "area": self.area,
            "tier": self.tier,
            "also": list(self.also),
        }
        if self.reason == TEST:
            out["version"] = self.version
        return out


@dataclass(frozen=True, slots=True)
class Refusal:
    """A run the guard refused before it started, with the sentence saying why (FLT-1204)."""

    promise: str
    scenario: str
    reason: str
    environment: str
    why: str

    def to_json(self) -> dict[str, Any]:
        return {
            "promise": self.promise,
            "scenario": self.scenario,
            "reason": self.reason,
            "environment": self.environment,
            "why": self.why,
        }


@dataclass(frozen=True, slots=True)
class Plan:
    """Tonight's plan: the runs in filing order, the runs the guard refused, and the budget."""

    items: tuple[PlanItem, ...] = ()
    refused: tuple[Refusal, ...] = ()
    budget: Budget = field(default_factory=lambda: Budget(0, 0))

    def to_json(self) -> dict[str, Any]:
        return {
            "budget": {"rechecks": self.budget.rechecks, "new": self.budget.new},
            "items": [item.to_json() for item in self.items],
            "refused": [refusal.to_json() for refusal in self.refused],
        }


# ───────────────────────────── the environment guard ─────────────────────────────


def _roles(environment: Mapping[str, Any]) -> set[str]:
    """Every role a login on the environment holds: `principals[*].role`/`roles`, or top-level `roles`."""
    found: set[str] = set()

    def take(value: Any) -> None:
        if isinstance(value, str) and value.strip():
            found.add(value.strip())
        elif isinstance(value, list):
            for one in value:
                take(one)

    take(environment.get("roles"))
    principals = environment.get("principals")
    if isinstance(principals, Mapping):
        principals = list(principals.values())
    if isinstance(principals, list):
        for principal in principals:
            if isinstance(principal, Mapping):
                take(principal.get("role"))
                take(principal.get("roles"))
    return found


#: The one production environment a WRITING QA run may ever drive (FLT-1204, amended by the owner
#: ruling of 2026-10-29): the e2e test tenant. Any other record marked `production: true` is
#: refused before a writing run starts, whatever `qa.orgs` says — an allow-list typo must never be
#: enough to give the agent write access to a customer's live product. A production environment
#: whose write policy is read-only may be driven under any name the install gives it.
PRODUCTION_TARGET: Final = "e2e-prod"

#: The environment kind whose leftovers hold its next run (FLT-1205).
CUSTOMER_KIND: Final = "customer"

#: The environment kind that is a stack on the operator's own machine. It has no org and no
#: login to hold a role: the local Docker stack is unauthenticated and serves nobody's real
#: workspace, so the org allow-list and the login checks do not apply to it. Everything that
#: protects a real environment (production, paused, a customer's leftovers) still does.
LOCAL_KIND: Final = "local"


def _leftovers(value: Any) -> bool:
    """Whether a record's `leftovers` says objects remain: a positive count (served as text) or a
    non-empty list. Unreadable is not "none": anything else non-empty holds the run."""
    if value is None or value is False or value == "" or value == []:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        text = value.strip()
        return not (text.isdigit() and int(text) == 0) and text.lower() not in ("none", "false", "no")
    return bool(value)


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return isinstance(value, str) and value.strip().lower() in ("true", "yes", "1")


def _has_steps(record: Mapping[str, Any]) -> bool:
    """Whether a record gives the steps that start, seed and stop a fresh copy."""
    return "steps" in record and record.get("steps") is not None


def _writes(environment: Mapping[str, Any]) -> bool:
    """Whether a run on this environment writes — anything but an explicit read-only policy does."""
    policy = environment.get("writes")
    if isinstance(policy, bool):
        return policy
    if isinstance(policy, str):
        return policy.strip().lower() not in _READ_ONLY_WRITES
    if isinstance(policy, Mapping):
        mode = policy.get("mode", policy.get("policy"))
        return not (isinstance(mode, str) and mode.strip().lower() in _READ_ONLY_WRITES)
    return True


def is_production_write(environment: Mapping[str, Any] | None) -> bool:
    """Whether a run on `environment` counts against its night's production write limit."""
    return environment is not None and _truthy(environment.get("production")) and _writes(environment)


def environment_refusal(
    environment_id: str,
    environments: Mapping[str, Mapping[str, Any]],
    config: QaConfig,
    *,
    roles: Iterable[str] = (),
    production_used: int = 0,
    new_coverage: bool = False,
) -> str | None:
    """The sentence refusing a run on `environment_id`, or `None` when the guard allows it.

    Checked in this order, and the first failure is the reason: a missing environment id, a missing
    record, a record with steps that says production (a copy Fleet starts is never production), a
    production environment that writes and is not `e2e-prod` (refused whatever `qa.orgs` says; a
    production environment whose write policy is read-only passes this check under any name), an org
    off the allow-list, a record still holding an earlier run's objects (a customer's, or any record
    with steps; FLT-1205), a paused record, a role no login holds, and a production environment whose
    writing runs tonight have reached `production_writes`.

    **A `kind: local` record is exempt from the org and login checks**, and only those: the local
    Docker stack is the QA desk's own machine, has no org to be on an allow-list and no sign-in
    to hold a role. Production, paused and a customer's leftovers still refuse it.

    `roles` are the roles the run signs in as — read from the scenario, so a re-check names them.
    New coverage has no scenario yet to name one (`new_coverage`), but it writes one whose every
    step signs in as some role; when the record declares no login at all, no role it could name is
    held, so the run is refused here rather than at run time after a slot is spent.
    """
    if not environment_id:
        return "no environment is named — the scenario names none and `qa.environment` is unset"
    record = environments.get(environment_id)
    if record is None:
        return f"environment {environment_id!r} has no record under knowledge/environments/"
    if _has_steps(record) and _truthy(record.get("production")):
        return (
            f"environment {environment_id!r} gives start steps and says production: "
            "a copy Fleet starts is never production"
        )
    if _truthy(record.get("production")) and _writes(record) and environment_id != PRODUCTION_TARGET:
        return (
            f"environment {environment_id!r} is production and writes, and {PRODUCTION_TARGET!r} "
            "is the only production environment a writing QA run may drive (a production "
            "environment whose write policy is read-only may run under any name)"
        )
    kind = str(record.get("kind") or "").strip()
    local = kind == LOCAL_KIND
    org = str(record.get("org") or "").strip()
    # A LOCAL STACK HAS NO ORG AND NO LOGIN, and both checks exist to protect a real one. The
    # org allow-list says whose workspace a run may touch; a stack on the operator's own machine
    # touches nobody's. The role check says a scenario can sign in; the local stack has no
    # sign-in at all, so every role it names is held by the one unauthenticated visitor. Skipping
    # them is what lets the QA desk drive the environment it chose (2026-10-28) instead of
    # refusing every run for a fact that is not true there.
    if not local and (not org or org not in config.orgs):
        allowed = ", ".join(config.orgs) or "(none — declare qa.orgs)"
        return (
            f"environment {environment_id!r} serves org {org or '(none)'!r}, which is not on the allow-list: {allowed}"
        )
    if (_has_steps(record) or str(record.get("kind") or "").strip() == CUSTOMER_KIND) and _leftovers(
        record.get("leftovers")
    ):
        if _has_steps(record):
            return (
                f"environment {environment_id!r} still holds objects an earlier run left; "
                "its next run waits until they are gone"
            )
        return (
            f"customer environment {environment_id!r} still holds objects an earlier run created; "
            "its next run waits until they are gone"
        )
    if _truthy(record.get("paused")):
        return f"environment {environment_id!r} is paused"
    missing = sorted({r.strip() for r in roles if r.strip()} - _roles(record))
    if missing and not local:
        return f"the scenario signs in as {', '.join(missing)}, which no login on {environment_id!r} holds"
    if new_coverage and not _roles(record) and not local:
        return (
            f"cannot run: environment {environment_id!r} declares no login, so a new scenario there "
            "has no principal for the role it must sign in as"
        )
    if is_production_write(record) and production_used >= config.production_writes:
        return (
            f"{environment_id!r} is production and tonight's writing runs there have reached "
            f"qa.production_writes ({config.production_writes})"
        )
    return None


# ───────────────────────────── the plan ─────────────────────────────


def refusal_limit(slots: int) -> int:
    """How many refusals one mode may record in a night before it stops looking: enough to show
    the desk why the night is short, never one row per open promise."""
    return max(3, 2 * slots)


@dataclass(frozen=True, slots=True)
class _Candidate:
    promise: str
    scenario: str
    reason: str
    state: str
    area: str
    tier: str
    group: int
    key: tuple[Any, ...]
    also: tuple[str, ...] = ()


def journey_slug(promise: str) -> str:
    """The journey slug of a criterion id shaped `<journey>#<n>`, else the empty string."""
    slug, sep, step = promise.rpartition("#")
    return slug if sep and slug and step.isdigit() else ""


def run_of(reason: str, scenario: str, promise: str) -> tuple[str, str]:
    """The run a promise belongs to tonight: a scenario for a re-check, else a journey or one promise.

    A re-check reruns one scenario, so every promise that scenario proves shares the run
    `("scenario", scenario)`. New coverage of a journey step (`<journey>#<n>`) shares the run
    `("journey", <slug>)`; new coverage of anything else is a run of its own, `("promise", id)`.
    """
    if reason == RECHECK:
        return ("scenario", scenario)
    slug = journey_slug(promise)
    return ("journey", slug) if slug else ("promise", promise)


def _scenario_index(scenarios: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(s.get("id") or ""): s for s in scenarios if s.get("id")}


def _age_key(last_pass: Any) -> tuple[int, str]:
    """Never passed first, then the oldest pass — RFC3339 instants sort lexically by time."""
    return (0, "") if not last_pass else (1, str(last_pass))


def _rerun_helps(row: Mapping[str, Any], target: Mapping[str, Any] | None) -> bool:
    """Whether re-running an `unfinished` promise can make it count, on `target` — the record of
    the environment the RE-RUN will go to (its scenario's, else `qa.environment`), not the one the
    old pass ran on.

    Not while its pass awaits ONLY the verifier's first approval — the approval flips it with no
    run; a pass that also did not finish is re-run. Not while it waits for a release and the target
    environment's `version_probe` is null (every run there is unfinished by construction) — nor
    when the target has no record at all, whose probe nobody can read. Neither hold is for ever: an
    unfinished reading falls back to out of date after its freshness window
    (`quality._unfinished_of`), and out of date is re-checked like any other.
    """
    evidence = row.get("evidence")
    waits = set(evidence.get("waiting") or ()) if isinstance(evidence, Mapping) else set()
    if waits == {WAIT_APPROVAL}:
        return False
    return not (WAIT_RELEASE in waits and (target is None or not target.get("version_probe")))


def _deciding_scenario(row: Mapping[str, Any], runnable: list[str]) -> str:
    """The runnable scenario that holds the check which decided the promise's state.

    A promise is usually proved by several scenarios. Its `evidence` names the check that decided
    the state (`quality._evidence_of`), and re-running any other scenario cannot change that
    check. The deciding scenario is the evidence's `target` when the run was a scenario, else the
    scenario named by the check id (`<scenario>#<n>`). A promise decided by a check no scenario
    holds — a journey criterion or a checklist item — keeps the old answer: the first runnable
    scenario.
    """
    evidence = row.get("evidence")
    if isinstance(evidence, Mapping):
        target = str(evidence.get("target") or "")
        if str(evidence.get("kind") or "") == "scenario" and target in runnable:
            return target
        check = str(evidence.get("id") or "")
        head, sep, _ = check.partition("#")
        if sep and head in runnable:
            return head
    return runnable[0]


def _candidates(
    promises: Iterable[Mapping[str, Any]],
    scenarios: Mapping[str, Mapping[str, Any]],
    taken: Collection[str],
    now: str,
    environments: Mapping[str, Mapping[str, Any]] | None = None,
    default_environment: str = "",
) -> tuple[list[_Candidate], list[_Candidate]]:
    """`(rechecks, new)` — every promise tonight could act on, each with its total ranking key."""
    rechecks: list[_Candidate] = []
    new: list[_Candidate] = []
    for row in promises:
        pid = str(row.get("id") or "")
        if not pid or pid in taken:
            continue
        state = str(row.get("state") or "")
        tier = str(row.get("tier") or "")
        area = str(row.get("area") or "")
        group = 0 if str(row.get("kind") or "") == "criterion" else 1
        runnable = sorted(
            s
            for s in (str(x) for x in row.get("scenarios") or ())
            if s in scenarios and not quarantine_active(scenarios[s].get("quarantine"), now)
        )
        if state == UNFINISHED:
            chosen = _deciding_scenario(row, runnable) if runnable else ""
            target = str(scenarios[chosen].get("environment") or "").strip() if chosen else ""
            if not runnable or not _rerun_helps(row, (environments or {}).get(target or default_environment)):
                continue
        if state in _RECHECK_ORDER and runnable:
            key = (TIER_RANK.get(tier, 3), group, _RECHECK_ORDER[state], _age_key(row.get("last_pass")), pid)
            rechecks.append(_Candidate(pid, _deciding_scenario(row, runnable), RECHECK, state, area, tier, group, key))
        elif state in _NEW_ORDER and not runnable:
            key = (TIER_RANK.get(tier, 3), group, _NEW_ORDER[state], _age_key(row.get("last_pass")), pid)
            new.append(_Candidate(pid, "", NEW, state, area, tier, group, key))
    return rechecks, new


def _fold(candidates: Iterable[_Candidate]) -> list[_Candidate]:
    """Merge candidates that name the same run: the best-keyed one hosts it, the rest ride."""
    by_run: dict[tuple[str, str], list[_Candidate]] = {}
    for one in candidates:
        by_run.setdefault(run_of(one.reason, one.scenario, one.promise), []).append(one)
    folded: list[_Candidate] = []
    for group in by_run.values():
        ordered = sorted(group, key=lambda c: c.key)
        host, riders = ordered[0], ordered[1:]
        folded.append(replace(host, also=tuple(rider.promise for rider in riders)) if riders else host)
    return folded


def _round_robin(candidates: list[_Candidate]) -> list[_Candidate]:
    """Strict tier and journey-group order; inside each, each area's best run in turn."""
    out: list[_Candidate] = []
    by_group: dict[tuple[int, int], list[_Candidate]] = {}
    for one in sorted(candidates, key=lambda c: c.key):
        by_group.setdefault((int(one.key[0]), int(one.key[1])), []).append(one)
    for group_key in sorted(by_group):
        queues: dict[str, list[_Candidate]] = {}
        for one in by_group[group_key]:  # already in key order, so each queue is too
            queues.setdefault(one.area, []).append(one)
        lanes = sorted(queues.values(), key=lambda q: q[0].key)
        while lanes:
            for lane in lanes:
                out.append(lane.pop(0))
            lanes = [lane for lane in lanes if lane]
    return out


def _roles_of(scenario: Mapping[str, Any] | None) -> tuple[str, ...]:
    if scenario is None:
        return ()
    raw = scenario.get("roles")
    if isinstance(raw, str):
        return (raw,)
    return tuple(str(r) for r in raw) if isinstance(raw, list) else ()


def plan_night(
    promises: Sequence[Mapping[str, Any]],
    scenarios: Sequence[Mapping[str, Any]],
    environments: Sequence[Mapping[str, Any]],
    config: QaConfig,
    budget: Budget,
    *,
    now: str,
    taken: Collection[str] = (),
    production_used: Mapping[str, int] | None = None,
    refused_tonight: Mapping[str, int] | None = None,
    decided: Collection[tuple[str, str]] = (),
    candidates: Sequence[ApprovedVersion] = (),
    tested: Collection[tuple[str, int]] = (),
    tests_tonight: int = 0,
) -> Plan:
    """Fill `budget` from the promise rows, in ranking order, refusing what the guard forbids.

    `promises` are `quality_promises`' rows (`id`, `state`, `tier`, `area`, `kind`, `last_pass`,
    `scenarios`); `scenarios` the served scenario rows (`id`, `environment`, `roles`,
    `quarantine`); `environments` the served environment records. `taken` names promises already
    decided tonight, which are never planned twice; `decided` names tonight's decided RUNS (see
    `run_of`), which are never planned again — including new coverage of a journey already on a
    re-check; `refused_tonight` counts tonight's refusals per reason, which the night's refusal cap
    includes; `production_used` counts the writing runs already filed tonight per production
    environment, which the guard adds to. `now` (RFC3339) decides whether a scenario's quarantine
    still holds — a quarantined scenario is never rerun.

    `candidates` are the approved scenario versions a test may be written for; `tested` names the
    `(scenario, version)` pairs already filed, and `tests_tonight` how many were filed earlier
    tonight. Tests are planned after re-checks and before new coverage, out of the new-coverage
    share, and drive no environment, so the guard never sees them. Pure and total.
    """
    by_scenario = _scenario_index(scenarios)
    by_env = {str(e.get("id") or ""): e for e in environments if e.get("id")}
    used = dict(production_used or {})
    rechecks, new = _candidates(promises, by_scenario, set(taken), now, by_env, config.environment)
    decided_runs = set(decided)
    decided_journeys = {value for kind, value in decided_runs if kind == "journey"}
    planned_journeys: set[str] = set()
    items: list[tuple[tuple[int, int, int], PlanItem]] = []
    refused: list[Refusal] = []
    already = dict(refused_tonight or {})
    filled = 0
    # THE NIGHT'S refusals, not this call's: the pass plans the night on every tick, and a cap
    # that reset per call would let a misconfigured environment add a handful of rows each time.
    refusals = already.get(RECHECK, 0)
    cap = refusal_limit(config.rechecks)
    for one in _round_robin(_fold(rechecks)):
        if filled >= budget.rechecks or refusals >= cap:
            break
        run = run_of(one.reason, one.scenario, one.promise)
        if run in decided_runs:
            continue
        scenario = by_scenario.get(one.scenario) if one.scenario else None
        environment = str((scenario or {}).get("environment") or "").strip() or config.environment
        why = environment_refusal(
            environment,
            by_env,
            config,
            roles=_roles_of(scenario),
            production_used=used.get(environment, 0),
            new_coverage=scenario is None,
        )
        if why is not None:
            refused.append(Refusal(one.promise, one.scenario, one.reason, environment, why))
            refusals += 1
            continue
        if is_production_write(by_env.get(environment)):
            used[environment] = used.get(environment, 0) + 1
        items.append(
            (
                (0, TIER_RANK.get(one.tier, 3), one.group),
                PlanItem(
                    one.promise,
                    one.scenario,
                    one.reason,
                    environment,
                    one.state,
                    one.area,
                    one.tier,
                    one.also,
                ),
            )
        )
        filled += 1
        for pid in (one.promise, *one.also):
            slug = journey_slug(pid)
            if slug:
                planned_journeys.add(slug)

    tested_pairs = set(tested)
    planned_scenarios = {item.scenario for _key, item in items if item.scenario}
    planned_promises = {promise for _key, item in items for promise in (item.promise, *item.also)}
    tests_filled = 0
    if config.test_suite is not None:
        test_slots = max(0, min(config.new // 2 - tests_tonight, budget.new // 2))
        for candidate in candidates:
            if tests_filled >= test_slots:
                break
            if (candidate.scenario, candidate.version) in tested_pairs:
                continue
            if candidate.scenario in planned_scenarios:
                continue
            first = candidate.promises[0] if candidate.promises else ""
            if first in taken or first in planned_promises:
                continue
            items.append(
                (
                    (1, TIER_RANK.get("", 3), 0),
                    PlanItem(
                        first,
                        candidate.scenario,
                        TEST,
                        "",
                        "",
                        "",
                        "",
                        version=candidate.version,
                        promises=candidate.promises,
                    ),
                )
            )
            planned_scenarios.add(candidate.scenario)
            if first:
                planned_promises.add(first)
            tests_filled += 1

    new_slots = max(0, budget.new - tests_filled)
    filled = 0
    refusals = already.get(NEW, 0)
    cap = refusal_limit(config.new)
    for one in _round_robin(_fold(new)):
        if filled >= new_slots or refusals >= cap:
            break
        run = run_of(one.reason, one.scenario, one.promise)
        if run in decided_runs:
            continue
        if run[0] == "journey" and (run[1] in decided_journeys or run[1] in planned_journeys):
            continue
        scenario = by_scenario.get(one.scenario) if one.scenario else None
        environment = str((scenario or {}).get("environment") or "").strip() or config.environment
        why = environment_refusal(
            environment,
            by_env,
            config,
            roles=_roles_of(scenario),
            production_used=used.get(environment, 0),
            new_coverage=scenario is None,
        )
        if why is not None:
            refused.append(Refusal(one.promise, one.scenario, one.reason, environment, why))
            refusals += 1
            continue
        if is_production_write(by_env.get(environment)):
            used[environment] = used.get(environment, 0) + 1
        items.append(
            (
                (2, TIER_RANK.get(one.tier, 3), one.group),
                PlanItem(
                    one.promise,
                    one.scenario,
                    one.reason,
                    environment,
                    one.state,
                    one.area,
                    one.tier,
                    one.also,
                ),
            )
        )
        filled += 1
    items.sort(key=lambda pair: pair[0])
    return Plan(items=tuple(item for _key, item in items), refused=tuple(refused), budget=budget)
