"""Slots — what does this repo supply to the commands, and do the commands ask portably?

Three checks, two directions of the same interface. `slots` asks whether the REPO answers
what the commands need; `command-portability` asks whether the COMMANDS only ask for things
the fixed layout provides, and `command-contracts` whether what they name in the tree
resolves — a slot to its question, a `sop` to a slug, a rubric to its spec. They fail for
unrelated reasons and a reader should not have to disentangle them.

The family. It is its own family rather than a member of `structure/` because it asks a
different question: `structure` asks whether the corpus holds together as a graph, this
asks whether the corpus is a complete *interface* to a portable command tree. The two
fail for unrelated reasons and a reader should not have to disentangle them.

Its options live in a `[fleet.slots]` table — `registry` (where the registry file sits,
relative to the knowledge directory) and `commands_dir` (where the command tree sits,
relative to the repository root).
"""

from __future__ import annotations

from ._contracts import CommandContracts
from ._layout import FleetLayout
from ._portability import CommandPortability
from ._render import CommandRender
from ._slots import KNOWN_OPTIONS, SlotsCheck, option, summary_lines
from ._tracker import TrackerClients

CHECKS = [SlotsCheck(), CommandPortability(), CommandContracts(), CommandRender(), TrackerClients(), FleetLayout()]

__all__ = [
    "CHECKS",
    "KNOWN_OPTIONS",
    "CommandContracts",
    "CommandPortability",
    "CommandRender",
    "FleetLayout",
    "SlotsCheck",
    "TrackerClients",
    "option",
    "summary_lines",
]
