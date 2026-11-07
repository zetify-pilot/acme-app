"""`fleet-layout` — Fleet's files are where this release reads them, and nothing of Fleet's is left at the root.

Fleet keeps its configuration in `.fleet/fleet.toml`, beside the tier, and says what each
conventional target runs in that file's `[fleet.targets]` table. Releases before wrote a root
`fleet.toml`, a stub `Makefile` and a `fleet.mk`; `fleet commands sync` migrates all three
(`setupfiles`). This check is what makes a repository that has NOT been migrated loud rather than
quietly half-working — its tier would render every target as a refusal, or still name a Makefile
nobody maintains:

  * a root `fleet.toml` — read for one more release only, then not at all;
  * a `fleet.mk`, or Fleet's stub `Makefile`, or a Makefile still including `fleet.mk`;
  * a repository carrying the command tier whose configuration has no `[fleet.targets]` table, or
    that has no configuration at all. A corpus with no tier runs no target, so it needs no table.

Each names the one change that fixes it. **For this release each is a WARNING (`LAYOUT_LEVEL`)**:
the day an install upgrades, every repository that has not yet merged its Apply Fleet pull request is
in one of these states, and an error would turn every agent's pre-push `validate-knowledge` red over
work it did not touch. They become errors in the release that stops reading a root `fleet.toml`
(`config.LEGACY_CONFIG_REL`). Both configuration files at once stays an error: reading already
refuses it. Applies to a repository that carries a synced tier or a Fleet configuration; a bare
corpus has nothing to migrate.
"""

from __future__ import annotations

from dataclasses import dataclass

from fleet_knowledge import commandsync, legacymake
from fleet_knowledge import config as configmod
from fleet_knowledge.config import KnowledgeBase
from fleet_knowledge.runner import Finding

_SYNC = (
    'merge this repository\'s open "Apply Fleet" pull request, or run `fleet commands sync` as a change of its '
    "own (never inside an unrelated pull request) — it migrates it"
)
#: The level of every transition-window finding below. "error" in the release that drops the root
#: `fleet.toml` read (`config.LEGACY_CONFIG_REL`); until then a repository mid-upgrade must not fail
#: `fleet check` over a migration a person has yet to merge.
LAYOUT_LEVEL = "warning"


@dataclass
class FleetLayout:
    """A repository on the `.fleet/fleet.toml` layout, with its `[fleet.targets]` table."""

    name: str = "fleet-layout"
    title: str = "Fleet's configuration is in .fleet/fleet.toml, with its targets table"
    description: str = (
        "Fleet keeps its configuration in `.fleet/fleet.toml` and what each conventional target runs in "
        "its `[fleet.targets]` table; nothing of Fleet's sits at the repository root. Warns (an error from the "
        "release that drops the root-file read) on a root "
        "`fleet.toml`, a `fleet.mk`, Fleet's stub `Makefile` or its include of `fleet.mk`, and a synced "
        "tier with no targets table — each fixed by `fleet commands sync`."
    )

    def _has_tier(self, kb: KnowledgeBase) -> bool:
        return (kb.root / commandsync.PLUGIN_DIR / commandsync.COMMANDS_SUBDIR).is_dir()

    def applies(self, kb: KnowledgeBase) -> bool:
        root = kb.root
        return self._has_tier(kb) or any(
            (root / rel).is_file() for rel in (configmod.CONFIG_REL, configmod.LEGACY_CONFIG_REL)
        )

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        root = kb.root
        out: list[Finding] = []
        legacy = root / configmod.LEGACY_CONFIG_REL
        new = root / configmod.CONFIG_REL
        if legacy.is_file() and new.is_file():
            out.append(
                Finding(
                    level="error",
                    message=f"both {configmod.CONFIG_REL} and a root {configmod.LEGACY_CONFIG_REL} exist",
                    path=legacy,
                    hint=f"Merge what you need into {configmod.CONFIG_REL} and delete the root file.",
                )
            )
        elif legacy.is_file():
            out.append(
                Finding(
                    level=LAYOUT_LEVEL,
                    message=(
                        f"Fleet's configuration is at the repository root ({configmod.LEGACY_CONFIG_REL}); this "
                        f"release reads it from {configmod.CONFIG_REL}, and the next one reads only that"
                    ),
                    path=legacy,
                    hint=f"To move it and add its `[fleet.targets]` table, {_SYNC}.",
                )
            )
        mk = root / legacymake.FLEET_MK
        if mk.is_file():
            out.append(
                Finding(
                    level=LAYOUT_LEVEL,
                    message=f"{legacymake.FLEET_MK} is left from the layout before `[fleet.targets]`",
                    path=mk,
                    hint=(
                        "`fleet commands sync` folds an unedited one into the table and deletes it; an edited one "
                        "is kept — move its recipes into `[fleet.targets]` by hand and delete it."
                    ),
                )
            )
        makefile = root / "Makefile"
        if makefile.is_file():
            text = makefile.read_text(encoding="utf-8", errors="ignore")
            if legacymake.is_fleet_stub(text):
                out.append(
                    Finding(
                        level=LAYOUT_LEVEL,
                        message="Makefile is the stub an earlier Fleet wrote; `[fleet.targets]` replaces it",
                        path=makefile,
                        hint=f"To delete it, {_SYNC}.",
                    )
                )
            elif legacymake.includes_fleet_mk(text):
                out.append(
                    Finding(
                        level=LAYOUT_LEVEL,
                        message=f"Makefile still carries Fleet's `{legacymake.INCLUDE_LINE}`",
                        path=makefile,
                        hint=f"To take it out (nothing else in the file changes), {_SYNC}.",
                    )
                )
        try:
            located = configmod.find_config_file(root)
        except configmod.ConfigError as exc:
            out.append(Finding(level="error", message=str(exc), path=root, hint="Keep one configuration file."))
            return out
        if located is None:
            if self._has_tier(kb):
                out.append(
                    Finding(
                        level=LAYOUT_LEVEL,
                        message=(
                            f"this repository carries the command tier but no {configmod.CONFIG_REL}, so every "
                            "target the commands name reads as a refusal"
                        ),
                        path=root,
                        hint=f"To write one with its `[fleet.targets]` table, {_SYNC}.",
                    )
                )
            return out
        path, table = located
        if not self._has_tier(kb):
            return out
        if "targets" not in table and path.name != configmod.PYPROJECT_FILENAME and not legacy.is_file():
            out.append(
                Finding(
                    level=LAYOUT_LEVEL,
                    message=(
                        f"{path.relative_to(root) if path.is_relative_to(root) else path} has no `[fleet.targets]` "
                        "table, so every target the commands name reads as a refusal"
                    ),
                    path=path,
                    hint=(
                        f"To add it from what the repository runs today, {_SYNC}; "
                        "then fill in the targets it leaves out."
                    ),
                )
            )
        elif "targets" not in table and path.name == configmod.PYPROJECT_FILENAME:
            out.append(
                Finding(
                    level=LAYOUT_LEVEL,
                    message=(
                        "pyproject.toml's `[tool.fleet]` has no `targets` table, so every target reads as a refusal"
                    ),
                    path=path,
                    hint=(
                        "Add `[tool.fleet.targets]` naming each conventional target's command "
                        "(Fleet never edits pyproject.toml)."
                    ),
                )
            )
        return out


CHECKS = [FleetLayout()]
