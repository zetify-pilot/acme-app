"""The Makefile and `fleet.mk` releases before `[fleet.targets]` wrote — recognised, never written.

Until the conventional targets moved into `.fleet/fleet.toml`, `fleet init` wrote a stub `Makefile`
at the repository root (a refusal recipe for every target, `validate-knowledge` filled in) and, for
a repository that named its stacks, a `fleet.mk` with their recipes that the Makefile included. No
release writes either any more. This module is what the migration (`setupfiles`) needs to undo
them without touching a byte of a Makefile that is the repository's own:

* **`is_fleet_stub`** — whether a Makefile is Fleet's stub and nothing else: every rule in it is a
  stub refusal or the stub's own `validate-knowledge` recipe. Such a file is deleted. A Makefile
  that began as the stub and gained one real recipe is the repository's, and is kept.
* **`own_targets`** — the conventional targets a Makefile defines for real, which the migrated
  table runs as `make <target>`: that Makefile is the repository's own build tool, not Fleet's.
* **`without_fleet_include`** — a repository-owned Makefile minus Fleet's `-include fleet.mk` block.

Stdlib only.
"""

from __future__ import annotations

import re

from fleet_knowledge import targets as targetsmod

__all__ = [
    "FLEET_MK",
    "HEADER_FIRST_LINE",
    "INCLUDE_LINE",
    "is_fleet_stub",
    "make_value",
    "own_targets",
    "stub_refusals",
    "targets_of",
    "without_fleet_include",
]

FLEET_MK = "fleet.mk"
#: The first line of every stub Makefile a release wrote.
HEADER_FIRST_LINE = "# Conventional targets — what the fleet's commands mean when they say `make <target>`."
INCLUDE_LINE = f"-include {FLEET_MK}"
#: The two comment lines the stub (and the Makefile it told a repository to edit) wrote above the include.
INCLUDE_COMMENT = (
    "# The targets above that refuse are the ones no stack profile renders. The rest are in",
    f"# {FLEET_MK}, rendered by `fleet init --stack`/`--detect` from the stacks this repository builds in.",
)
#: The stub's own `validate-knowledge` recipe lines (it was the one target the stub filled).
FILLED_RECIPE: dict[str, tuple[str, ...]] = {
    "validate-knowledge": (
        "\tpython3 knowledge/scripts/fleet.py check --repo .",
        "\tpython3 knowledge/scripts/validate_requirements.py",
        "\tpython3 knowledge/scripts/validate_id_collisions.py",
    ),
}

_TARGET_LINE = re.compile(r"^([A-Za-z0-9_./-]+)\s*:(?!=)", re.MULTILINE)
_REFUSAL = re.compile(r'^([A-Za-z0-9_./-]+):\n\t@echo "make \1: not configured for this repository', re.MULTILINE)
_INCLUDE = re.compile(r"^[ \t]*-?include[ \t]+fleet\.mk[ \t]*$")
_RULE = re.compile(r"^([A-Za-z0-9_./-]+):[ \t]*$")


def targets_of(text: str) -> frozenset[str]:
    """Every target a Makefile's TEXT defines, by the rule-line grammar `name:` (not `name :=`)."""
    return frozenset(m.group(1) for m in _TARGET_LINE.finditer(text) if m.group(1) != ".PHONY")


def stub_refusals(text: str) -> frozenset[str]:
    """The targets a Makefile's TEXT defines only as the stub's refusal recipe, not for real."""
    return frozenset(m.group(1) for m in _REFUSAL.finditer(text))


def own_targets(text: str | None) -> frozenset[str]:
    """The conventional targets a Makefile defines for real — never the refusals the stub wrote."""
    if text is None or is_fleet_stub(text):
        return frozenset()
    return (targets_of(text) - stub_refusals(text)) & frozenset(targetsmod.TARGETS)


def is_fleet_stub(text: str) -> bool:
    """Whether `text` is a Makefile Fleet wrote and nobody extended: the stub's header first, then
    only comments, `.PHONY`, Fleet's include, refusal recipes and the stub's own filled recipe."""
    lines = text.splitlines()
    if not lines or lines[0] != HEADER_FIRST_LINE:
        return False
    body = [
        line
        for line in lines
        if line.strip()
        and not line.lstrip().startswith("#")
        and not line.startswith(".PHONY:")
        and not _INCLUDE.match(line)
    ]
    i = 0
    while i < len(body):
        rule = _RULE.match(body[i])
        if rule is None:
            return False
        name = rule.group(1)
        following = body[i + 1] if i + 1 < len(body) else ""
        if following.startswith(f'\t@echo "make {name}: not configured for this repository'):
            i += 2
            continue
        filled = FILLED_RECIPE.get(name)
        if filled is not None and tuple(body[i + 1 : i + 1 + len(filled)]) == filled:
            i += 1 + len(filled)
            continue
        return False
    return True


def includes_fleet_mk(text: str) -> bool:
    """Whether a Makefile includes `fleet.mk` on a line of its own (the only form Fleet wrote)."""
    return any(_INCLUDE.match(line) for line in text.splitlines())


def without_fleet_include(text: str) -> str:
    """`text` without Fleet's include of `fleet.mk` and the two comment lines Fleet wrote above it.

    Only those lines: a comment or an include of the repository's own is left exactly as it is, and
    a run of blank lines the removal leaves at the end of the file is trimmed to one newline.
    """
    lines = text.splitlines(keepends=True)
    drop: set[int] = set()
    for i, line in enumerate(lines):
        if not _INCLUDE.match(line.rstrip("\n")):
            continue
        drop.add(i)
        above = [lines[j].rstrip("\n") for j in range(max(0, i - len(INCLUDE_COMMENT)), i)]
        if tuple(above) == INCLUDE_COMMENT:
            drop.update(range(i - len(INCLUDE_COMMENT), i))
    kept = "".join(line for i, line in enumerate(lines) if i not in drop)
    if kept != text:
        kept = kept.rstrip("\n") + "\n" if kept.strip() else ""
    return kept


def make_value(target: str) -> str:
    """What the migrated table runs for a target the repository's own Makefile defines."""
    params = targetsmod.TARGETS[target].params
    return " ".join(["make", target, *(f"{p}={{{p}}}" for p in params)])
