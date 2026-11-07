"""The recurring-work schedule family: `[fleet.recurring]`, its reader, and its check.

A watched repository declares the work Fleet should file on a cadence in its own
`fleet.toml`:

    [fleet.recurring]
    entries = [
      { name = "nightly-audit", kind = "audit", cadence = "daily" },
      { name = "weekly-feature", kind = "prd", cadence = "weekly:mon", target = "frontend" },
    ]

Two consumers read that table and they must agree exactly. The Fleet service's scheduler
reads it to decide what is due and files one issue per due window; this package's check
reads it at merge time so a mistyped cadence is caught in review rather than discovered on
a silent wrong night. **The cadence vocabulary is one object here** — `read_schedule` and
`validate_cadence` — because a second copy is a second answer waiting to disagree. The
Fleet service duplicates it in its own pure module by design (that package is stdlib-only
too, and may not import this one); a fleet-service test cross-checks the two.

**A bad entry never raises.** It is reported as a `BadEntry` and skipped, so the entries
around it still parse — a schedule with one typo must still file the work that is right,
and the merge-time check turns the same `BadEntry` into an error finding.

Stdlib only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from fleet_knowledge.config import KnowledgeBase
from fleet_knowledge.qaplan import read_qa_config
from fleet_knowledge.runner import Finding

# The options inside `[fleet.recurring]`: the entries array, and the `qa` table that turns on the
# QA agent's nightly loop and splits its budget (`fleet_knowledge.qaplan`, FLT-1226).
KNOWN_OPTIONS: frozenset[str] = frozenset({"entries", "qa"})

# The work kinds a schedule entry may name. Duplicated from the Fleet service's routed set
# by the same design note as the cadence vocabulary.
KINDS: frozenset[str] = frozenset({"prd", "bug", "task", "cleanup", "audit"})

# The keys an entry may carry. `name`, `kind` and `cadence` are required; `target` is the
# optional free-form pointer the scheduler passes through (an area, a component, a repo).
ENTRY_KEYS: frozenset[str] = frozenset({"name", "kind", "cadence", "target"})

# The day names `<day>` may take in `weekly:<day>` / `biweekly:<day>`.
DAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

# The plain-word cadences, one per shape. `.format` fields are the only variable parts.
DAILY = "daily"
WEEKDAYS = "weekdays"
WEEKLY = "weekly:{day}"
BIWEEKLY = "biweekly:{day}"
MONTHLY = "monthly:{n}"

# The closed set a person reads in an error message.
CADENCES: tuple[str, ...] = (DAILY, WEEKDAYS, WEEKLY, BIWEEKLY, MONTHLY)


def validate_cadence(cadence: Any) -> str | None:
    """`None` when `cadence` is one of the closed plain-word set, else a message naming it.

    The vocabulary is `daily | weekdays | weekly:<day> | biweekly:<day> | monthly:<n>`,
    where `<day>` is one of mon..sun and `<n>` is 1..28. A cron expression is refused like
    any other unknown word: the scheduler cannot validate it against the window and cap
    semantics, and its failure mode is a silent wrong night. The returned message always
    carries the offending word, so both the filing-time reader and the merge-time check can
    say exactly which token to fix.
    """
    if not isinstance(cadence, str) or not cadence.strip():
        return f"cadence must be a non-empty string, got {cadence!r}"
    word = cadence.strip()
    if word in (DAILY, WEEKDAYS):
        return None

    expected = f"expected one of {', '.join(CADENCES)}"
    for prefix, day_shaped in (("weekly:", True), ("biweekly:", True), ("monthly:", False)):
        if not word.startswith(prefix):
            continue
        value = word[len(prefix) :]
        if day_shaped:
            if value not in DAYS:
                return f"unknown cadence `{word}` — `<day>` must be one of {', '.join(DAYS)}"
            return None
        if not value.isdigit():
            return f"unknown cadence `{word}` — `<n>` must be a number 1..28, got {value!r}"
        if not 1 <= int(value) <= 28:
            return f"unknown cadence `{word}` — `<n>` must be between 1 and 28"
        return None

    return f"unknown cadence `{word}` — {expected}"


@dataclass(frozen=True)
class Entry:
    """One valid schedule entry, in the shape the scheduler files from."""

    name: str
    kind: str
    cadence: str
    target: str = ""


@dataclass(frozen=True)
class BadEntry:
    """One entry that could not be used, and why — reported and skipped, never raised."""

    name: str
    reason: str


def read_schedule(raw: Sequence[Mapping[str, Any]] | None) -> tuple[tuple[Entry, ...], tuple[BadEntry, ...]]:
    """Validate `raw` entry tables, returning `(entries, bad_entries)`.

    Every entry is checked independently: required `name`/`kind`/`cadence`, `kind` inside
    `KINDS`, `cadence` inside the closed set, and no keys outside `ENTRY_KEYS`. A failure is
    collected as a `BadEntry` naming the entry and the problem, and the remaining entries
    still parse — the caller files what is right and reports what is not. An absent or empty
    schedule is `((), ())`, not an error.
    """
    if not raw:
        return (), ()
    entries: list[Entry] = []
    bad: list[BadEntry] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            bad.append(BadEntry(f"entry[{index}]", "must be a table of keys"))
            continue
        name = item.get("name")
        label = name.strip() if isinstance(name, str) and name.strip() else f"entry[{index}]"
        problems: list[str] = []

        if not isinstance(name, str) or not name.strip():
            problems.append("missing required key `name`")
        unknown = sorted(set(item) - ENTRY_KEYS)
        if unknown:
            problems.append(f"unknown key(s) {', '.join(unknown)} — known keys are {', '.join(sorted(ENTRY_KEYS))}")

        kind = item.get("kind")
        if not isinstance(kind, str) or not kind.strip():
            problems.append("missing required key `kind`")
        elif kind not in KINDS:
            problems.append(f"unknown kind `{kind}` — expected one of {', '.join(sorted(KINDS))}")

        if "cadence" not in item:
            problems.append("missing required key `cadence`")
        else:
            reason = validate_cadence(item.get("cadence"))
            if reason is not None:
                problems.append(reason)

        target = item.get("target", "")
        if not isinstance(target, str):
            problems.append(f"`target` must be a string, got {target!r}")

        if problems:
            bad.append(BadEntry(label, "; ".join(problems)))
            continue
        assert isinstance(name, str) and isinstance(kind, str)  # narrowed: no `problems` above
        entries.append(Entry(name=name, kind=kind, cadence=item["cadence"], target=target))
    return tuple(entries), tuple(bad)


@dataclass
class RecurringSchedule:
    """The merge-time guard: an invalid `[fleet.recurring]` entry refuses the merge."""

    name: str = "recurring"
    title: str = "recurring schedule — the [fleet.recurring] entries are well-formed"
    description: str = (
        "A watched repository declares the work Fleet files on a cadence in its own "
        "fleet.toml under [fleet.recurring]. This check runs the same reader the scheduler "
        "files from and reports every entry whose cadence is outside the closed plain-word "
        "set, whose kind is not routed, or which is missing a required key — so a mistyped "
        "schedule is caught in review rather than on a silent wrong night."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        return bool(kb.config.section("recurring"))

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        section = kb.config.section("recurring")
        return [*self._entries(section.get("entries", [])), *self._qa(section.get("qa"))]

    def _qa(self, raw: Any) -> list[Finding]:
        """The `qa` table, read by the SAME reader the scheduler plans the night from — each
        problem it reports is one error, so a typo is caught in review rather than as a night the
        QA loop quietly ran on its defaults."""
        _, problems = read_qa_config(raw)
        return [
            Finding(
                level="error",
                message=f"recurring schedule: {problem}",
                hint=(
                    "Fix the `qa` table in [fleet.recurring]: rechecks, new and production_writes "
                    "are whole numbers, orgs is a list of org ids, hosts is a list of host names, "
                    "environment is an environment id, "
                    "suites is a list of { name, path, run, type } tables, type is unit, integration "
                    "or end-to-end, and tests names one of those suites."
                ),
            )
            for problem in problems
        ]

    def _entries(self, raw: Any) -> list[Finding]:
        if not isinstance(raw, list):
            return [
                Finding(
                    level="error",
                    message=(
                        f"recurring schedule: `entries` must be a list of tables, got "
                        f"{type(raw).__name__} — write `entries = [{{ name = …, kind = …, cadence = … }}]`"
                    ),
                    hint="A single table is not a schedule; wrap it in a list.",
                )
            ]
        _, bad = read_schedule(raw)
        return [
            Finding(
                level="error",
                message=f"recurring schedule: entry `{entry.name}` is invalid — {entry.reason}",
                hint=(
                    "Fix the entry in [fleet.recurring]; cadence is one of daily, weekdays, "
                    "weekly:<day>, biweekly:<day> or monthly:<n>."
                ),
            )
            for entry in bad
        ]


# The one export point the runner reads; a package under `checks/` is auto-discovered.
CHECKS = [RecurringSchedule()]

__all__ = [
    "BIWEEKLY",
    "CADENCES",
    "CHECKS",
    "DAILY",
    "DAYS",
    "ENTRY_KEYS",
    "KINDS",
    "KNOWN_OPTIONS",
    "MONTHLY",
    "WEEKDAYS",
    "WEEKLY",
    "BadEntry",
    "Entry",
    "RecurringSchedule",
    "read_schedule",
    "validate_cadence",
]
