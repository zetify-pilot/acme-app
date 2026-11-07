"""The repository's always-on rules file — the standing instructions an agent starts from.

A coding-engine session begins by loading the repository's always-on rules: the golden rules
that bind whatever task brought the agent there (reproduce before you fix, never certify your
own work, credentials never on the command line). A repository scaffolded by `fleet init` /
the Set up pull request gets a generic one, so its agents do not start from nothing — and the
shipped commands, which tell an agent to follow "the repository's always-on rules", point at
a file that exists.

The names are the engine's, not ours: `CLAUDE.md` is the name the engine reads today, and
`AGENTS.md` is the cross-engine name the same engine also reads. Both are written with the
same generic content; either satisfies readiness. This is a tiny module of its own so the
scaffold and the readiness check share ONE list of names rather than two that drift.

Stdlib only.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "RULES_FILES",
    "RULES_SECTION",
    "RULES_TEMPLATE",
    "has_rules_file",
    "rules_file",
]

#: The names the coding engine reads, in the order a scaffold writes them. `CLAUDE.md` is the
#: shipped template's own name; `AGENTS.md` is the same generic rules under the cross-engine
#: name.
RULES_FILES: tuple[str, ...] = ("CLAUDE.md", "AGENTS.md")

#: The file under `templates/scaffold/` the generic rules are rendered from. ONE source for
#: both names, so the two files cannot drift apart.
RULES_TEMPLATE = "CLAUDE.md"

#: The heading that marks where a repository writes its own rules. A scaffolded file carries
#: it; an existing file that lacks it is reported with the lines to add, never edited.
RULES_SECTION = "## This repository's own rules"


def rules_file(root: Path) -> Path | None:
    """The repository's always-on rules file, or `None` when it has none.

    Either name satisfies the repository: a repository that ships its own `AGENTS.md` is not
    asked to accept a `CLAUDE.md` it did not write.
    """
    for name in RULES_FILES:
        path = root / name
        if path.is_file():
            return path
    return None


def has_rules_file(root: Path) -> bool:
    """Whether the repository carries an always-on rules file under either name."""
    return rules_file(root) is not None
