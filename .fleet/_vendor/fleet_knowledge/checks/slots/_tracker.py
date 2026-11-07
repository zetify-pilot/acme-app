"""No tracker client ships in the command tree.

After PRD 0818 and 0819, no command calls Linear: agents reach issues through Fleet's own
governed tools (`get_issue`, `search_issues`, `file_issue`, `move_issue`, `triage`). The
remaining tracker scripts were deleted. This check is the lock that keeps them gone.

WHY A `fleet check` AND NOT ONLY A TEST. The same tree ships into every repository the fleet
dispatches into (`commandsync`), so the probe that matters is `fleet check --only tracker-clients
--repo <checkout>` at the pinned tree — exactly SL266-C4. A test proves the authoring tree
clean; the check proves every receiving tree clean, because a receiving repo's corpus sweep runs every
module under `fleet_knowledge/checks/` with no `--only` list.

WHAT IT GATES, at error level and with no baseline:

  * `api.linear.app` — a tracker endpoint spoken to directly.
  * `LINEAR_API_KEY` / `LINEAR_API_URL` — a session's tracker credential or address.
  * `lin_api_…` — a tracker key literal.
  * a deleted tracker client module (`linear_client`, `linear_endpoint`, `linear_issue`,
    `linear_file_issue`, `linear_release_issue`, `linear_quota`, `linear_park_guard`,
    `validate_linear_partition`, `tracker_path`, `filing_dedupe`) as an import, a
    `knowledge/scripts/<name>.py` path, or a bare `<name>.py`.

Scope is the tier only — the commands tree, the shared `process/`, `registers/` and `rubrics/`,
and the scripts directory (`commandtree/scripts` in this package, `knowledge/scripts` in a
receiving repository). A receiving repository's own `scripts/` or `internal/` is not the tier
and is not read.

No baseline, deliberately: a tracker client is not debt to ratchet down, it is a regression.

Stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from fleet_knowledge import commandsync
from fleet_knowledge import slots as slotmod
from fleet_knowledge.checks.slots._portability import _tier_root
from fleet_knowledge.checks.slots._slots import option
from fleet_knowledge.config import KnowledgeBase
from fleet_knowledge.runner import Finding

#: The client modules PRD 0820 deletes, or that PRD 0819 deleted before it. Listed longest
#: first so an alternation never settles on a prefix of a longer name.
DELETED_MODULES: tuple[str, ...] = (
    "validate_linear_partition",
    "linear_release_issue",
    "linear_file_issue",
    "linear_park_guard",
    "linear_endpoint",
    "linear_client",
    "linear_issue",
    "linear_quota",
    "tracker_path",
    "filing_dedupe",
)
_NAMES = "|".join(DELETED_MODULES)
#: A module name reached as an import, a shipped-path mention, or a bare `<name>.py`. The
#: word boundaries keep `tracker_labels`, `linear_issue_shape` and `tracker_paths_doc` legal.
_MODULE = re.compile(
    rf"(?:\b(?:import|from)\s+(?:{_NAMES})\b|(?:knowledge/)?scripts/(?:{_NAMES})\.py|\b(?:{_NAMES})\.py)"
)

#: `(rule, pattern, hint)` in the order a line is judged. A line that matches more than one
#: rule yields one finding per rule — each is a separate reason to fix the line.
_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "tracker-endpoint",
        re.compile(r"api\.linear\.app"),
        "Read the issue with the Fleet tool `get_issue <KEY>`; a session holds no tracker endpoint.",
    ),
    (
        "tracker-key-name",
        re.compile(r"\bLINEAR_API_(?:KEY|URL)\b"),
        "Sessions reach issues through the Fleet tools; no tracker key or address belongs in the tree.",
    ),
    (
        "tracker-key-literal",
        re.compile(r"lin_api_[A-Za-z0-9]"),
        "Never ship a tracker key literal; the Fleet tools take no tracker credential.",
    ),
    (
        "tracker-client",
        _MODULE,
        "Use the Fleet tools (`get_issue`, `search_issues`, `file_issue`, `move_issue`, `triage`); "
        "the tracker client scripts are gone.",
    ),
)


@dataclass
class TrackerClients:
    """No tracker client — script, endpoint or key — ships in the command tier."""

    name: str = "tracker-clients"
    title: str = "no tracker client ships in the command tree"
    description: str = (
        "Agents reach issues only through Fleet's governed tools. This check reads the tier's "
        "commands, shared documents and scripts and fails on a retained tracker endpoint, key "
        "name, key literal or deleted client module, so a tracker client cannot come back "
        "without reddening the build — in this repository and in every repository the command "
        "tree ships into."
    )
    #: A receiving repository may switch off any check except this one: the promise this check
    #: keeps (CAP-1792, FLT-1077) ships into every repository the fleet dispatches into, so a
    #: project's configuration must not be able to remove it.
    mandatory: bool = True

    def _commands_rel(self, kb: KnowledgeBase) -> str:
        return str(option(kb, "commands_dir", slotmod.default_commands_dir(kb.root)))

    def _scripts_dirs(self, kb: KnowledgeBase, tier: Path | None) -> list[Path]:
        """The scripts directory in either layout, without scanning one twice.

        `commandsync` maps the subdir to `knowledge/scripts` in a receiving repository and it
        lives at `commandtree/scripts` in the package source; a checkout that has both (the
        authoring repo after a sync) is read once.
        """
        out: list[Path] = []
        dest = kb.root / commandsync.SCRIPTS_DEST
        if dest.is_dir():
            out.append(dest)
        if tier is not None:
            src = tier / commandsync.SCRIPTS_SUBDIR
            if src.is_dir() and all(src.resolve() != p.resolve() for p in out):
                out.append(src)
        return out

    def applies(self, kb: KnowledgeBase) -> bool:
        commands_rel = self._commands_rel(kb)
        return (kb.root / commands_rel).is_dir() or (kb.root / commandsync.SCRIPTS_DEST).is_dir()

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        commands_rel = self._commands_rel(kb)
        base = kb.root / commands_rel
        tier = _tier_root(base, kb.root) if base.is_dir() else None

        files: list[Path] = []
        if base.is_dir():
            files.extend(sorted(base.rglob("*.md")))
        if tier is not None:
            for d in ("process", "registers", "rubrics"):
                if (tier / d).is_dir():
                    files.extend(sorted((tier / d).rglob("*.md")))
        for scripts in self._scripts_dirs(kb, tier):
            files.extend(sorted(scripts.rglob("*.py")))

        out: list[Finding] = []
        seen: set[Path] = set()
        for path in files:
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                for rule, pattern, hint in _RULES:
                    if pattern.search(line):
                        out.append(
                            Finding(
                                level="error",
                                message=(
                                    f"`{path.name}` names a tracker client ({rule.replace('-', ' ')}) "
                                    "in the shipped command tree"
                                ),
                                path=path,
                                line=lineno,
                                hint=hint,
                            )
                        )
        return out


CHECKS = [TrackerClients()]
