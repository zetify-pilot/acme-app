"""Quality-desk checks that gate a corpus at merge time.

Each check here holds a rule the Quality desk's readers serve from but cannot themselves
refuse: a reader renders what a record says, and a malformed record must be caught at the
commit that introduces it.

`CHECKS` is the one export point the runner discovers.
"""

from __future__ import annotations

from fleet_knowledge import corpus
from fleet_knowledge.config import KnowledgeBase
from fleet_knowledge.quality import quarantine_end, read_scenarios, scenario_citation_problems
from fleet_knowledge.runner import Finding

_HINT = (
    "Write both `quarantine_until` (a date such as 2026-10-20) and `quarantine_reason` in the "
    "scenario's frontmatter, or remove the quarantine fields to keep the scenario in the results."
)
_STEP_HINT = (
    "Write the journey step the scenario proves as `<journey>#<n>` — one acceptance criterion of "
    "the journey — instead of the bare journey id."
)


class ScenarioQuarantine:
    name = "scenario-quarantine"
    title = "A scenario quarantine names a reason and an until-date"
    description = (
        "A scenario is taken out of the Quality desk's results by writing a quarantine on its "
        "record. The promise is that a quarantine without a reason or an until-date is refused, "
        "so this check reports every quarantine that omits either field, or whose until-date is "
        "not a date the reader can honour."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        return (kb.root / "knowledge" / "scenarios").is_dir()

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        findings: list[Finding] = []
        for row in read_scenarios(kb.root):
            quarantine = row.get("quarantine")
            if not isinstance(quarantine, dict):
                continue
            until = str(quarantine.get("until") or "").strip()
            reason = str(quarantine.get("reason") or "").strip()
            path = kb.root / str(row.get("file") or "")
            if not until:
                findings.append(
                    Finding(
                        level="error",
                        message="quarantine_until is missing — a quarantine needs an until-date",
                        path=path,
                        hint=_HINT,
                    )
                )
            elif quarantine_end(until) is None:
                findings.append(
                    Finding(
                        level="error",
                        message=f"quarantine_until {until!r} is not a readable date",
                        path=path,
                        hint=_HINT,
                    )
                )
            if not reason:
                findings.append(
                    Finding(
                        level="error",
                        message="quarantine_reason is missing — a quarantine needs a reason",
                        path=path,
                        hint=_HINT,
                    )
                )
        return findings


class ScenarioJourneyStep:
    name = "scenario-journey-step"
    title = "A scenario cites a journey step, never a bare journey"
    description = (
        "A scenario that proves a journey names the step it walks (`<journey>#<n>`), so the "
        "Quality desk counts that criterion on its own row. This check reports every scenario "
        "whose `proves:` list or assertion `Promise` cell names a bare journey id, and — when a "
        "run's promises are given — every promise or rider with no assertion row."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        return (kb.root / "knowledge" / "scenarios").is_dir()

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        journey_ids = {path.stem for path, _tier in corpus.journey_files(kb.root / "knowledge")}
        findings: list[Finding] = []
        for row in read_scenarios(kb.root):
            for problem in scenario_citation_problems(row, journey_ids):
                findings.append(
                    Finding(
                        level="error",
                        message=f"{row['file']} {problem}",
                        path=kb.root / str(row["file"]),
                        hint=_STEP_HINT,
                    )
                )
        return findings


CHECKS = [ScenarioQuarantine(), ScenarioJourneyStep()]

__all__ = ["CHECKS", "ScenarioJourneyStep", "ScenarioQuarantine"]
