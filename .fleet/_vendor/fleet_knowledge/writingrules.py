"""The writing rules every agent session follows: English for what lasts, plain language for people.

Owner decision, 2026-10-19, from customer feedback: people talk to the fleet's agents in many
languages, and many of the people who read what the agents write are not native English speakers.

**One source, inlined everywhere it is read.** The text lives once, in the command tree, at
`process/writing.md`. Every surface that states it is rendered from that file, never copied:

* the managed rules block in a repository's `CLAUDE.md` / `AGENTS.md` (`setupfiles`, through the
  same include marker the command tier uses);
* the interview card (`process/interview-card.md`), and so every command that inlines the card;
* `.fleet/process/writing.md` itself, shipped to every repository for reading;
* the fleet service's prompt for every dispatched run and the instructions of every interactive
  session (`fleet_service`, which reads `text()` from this module and hands it to the box — the
  daemon holds no copy).

Tests on each side compare those surfaces to `text()`, so an edit anywhere but the source fails.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["SOURCE", "text"]

#: The source file, relative to the command tree (the include marker's own spelling).
SOURCE = "process/writing.md"


def text() -> str:
    """The writing rules as the source writes them, without leading or trailing blank lines."""
    root = Path(__file__).resolve().parent / "commandtree"
    return (root / SOURCE).read_text(encoding="utf-8").strip("\n")
