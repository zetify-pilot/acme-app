"""Where am I — the one shipped module that knows the layout.

Every script in this directory is materialized by `fleet commands sync` at a FIXED path,
`<repo>/knowledge/scripts/`, in every repository the tier ships to. That fixed path is the
whole contract: a command names `knowledge/scripts/component_of.py` and runs it, with no id
to resolve and no per-repo binding to get wrong. What differs per repository is read from the
repository — its config, its corpus, its git remote — never baked into a copy of the script.

This module resolves the four facts every shipped script needs and nothing else:

  * `repo_root()`   — the checkout, two levels up from `knowledge/scripts/`.
  * `namespace()`   — the command namespace under `.claude/commands/`, read from the tree
                      rather than spelled, so a script's `/{ns}:verify` follows
                      the tree if the namespace ever moves.
  * `org()` / `slug()` — the GitHub org and `org/name` of this checkout, from `origin`, for
                      the scripts that address the forge; a lane label `repo:<x>` resolves to
                      `<org>/<x>` because every lane lives in one org.
  * `fleet_knowledge()` — import the `fleet_knowledge` package: installed, or the submodule
                      at the conventional mount `<repo>/fleet/`. Loud when neither exists,
                      because a gate whose code is absent must fail, never pass quietly.
  * `knowledge_base()` — the package's `KnowledgeBase` over this checkout, carrying the
                      command names a finding prints as its fix — from the tree, not spelled.

Scripts in this directory are generated-and-verified like `.claude/`: edit them in
`fleet-knowledge`'s `commandtree/scripts/`, never here. `fleet commands sync --check` reports
a hand-edit as STALE.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent

#: The repository's answer to the tracker question, where its key prefix and team live.
TRACKER_SLOT = "knowledge/slots/tracker-identity.md"


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """The checkout this script is materialized in.

    `knowledge/scripts/<me>.py` → two levels up. In the authoring tree the same file sits at
    `commandtree/scripts/`, whose grandparent is the package; the caller (a test) sets the
    root explicitly there, and nothing in this directory assumes a corpus exists beside it.
    """
    return HERE.parent.parent


@lru_cache(maxsize=1)
def namespace() -> str:
    """The command namespace — the one directory under `.claude/commands/` that holds `.md`."""
    commands = repo_root() / ".claude" / "commands"
    if commands.is_dir():
        subs = sorted(p.name for p in commands.iterdir() if p.is_dir() and any(p.rglob("*.md")))
        if len(subs) == 1:
            return subs[0]
    raise SystemExit(
        f"no command namespace under {commands} — the tier is not synced here (`fleet commands sync --repo .`)"
    )


def command(name: str) -> str:
    """`/<ns>:<name>` — the form a person types, for messages that tell them what to run."""
    return f"/{namespace()}:{name}"


@lru_cache(maxsize=1)
def slug() -> str:
    """`org/name` of this checkout, from `origin` — never from the directory name."""
    try:
        url = subprocess.run(
            ["git", "-C", str(repo_root()), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    tail = url.rsplit(":", 1)[-1] if url.startswith("git@") else "/".join(url.rstrip("/").split("/")[-2:])
    return tail.removesuffix(".git")


def org() -> str:
    return slug().split("/", 1)[0] if "/" in slug() else ""


def lane_slug(label: str) -> str:
    """`repo:<name>` → `<org>/<name>`: every lane lives in this checkout's org."""
    name = label.removeprefix("repo:")
    return f"{org()}/{name}" if org() else name


def _tracker_answer() -> str:
    """This repository's `tracker-identity` answer, or `""` when it has none.

    Looked for beside the checkout `repo_root()` names first, then under the current
    working directory — the shipped scripts run from a repository root, so the second is
    what a scaffolded repository supplies and the first is what the authoring tree's
    tests do. Nothing is spelled here: the team and the key prefix are the repository's
    answers, never this package's.
    """
    for base in (repo_root(), Path.cwd()):
        path = base / TRACKER_SLOT
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            continue
    return ""


@lru_cache(maxsize=1)
def tracker_team() -> str:
    """The tracker team this repository files into: `LINEAR_TEAM_NAME`, else its answer.

    No built-in team: a package cannot know a customer's tracker, and a default is a
    wrong-team lookup that reads as a credential failure. Empty when neither the
    environment nor the repository names one, so the caller fails loudly.
    """
    env = (os.environ.get("LINEAR_TEAM_NAME") or "").strip()
    if env:
        return env
    text = _tracker_answer()
    m = re.search(r"\|[^|\n]*\*\*Tracker\*\*[^|\n]*\|[^|\n]*team\s*\*\*([^*|]+)\*\*", text)
    return m.group(1).strip() if m else ""


@lru_cache(maxsize=1)
def tracker_prefix() -> str:
    """The issue-key prefix this repository's tracker uses (`ENG`), or `""`.

    Overridable by `LINEAR_KEY_PREFIX` for an operator who needs it before the answer
    exists; otherwise read from the repository's `tracker-identity` answer. `""` means
    the repository has not answered, and a caller that composes issue ids must refuse
    rather than reserve some other workspace's prefix.
    """
    env = (os.environ.get("LINEAR_KEY_PREFIX") or "").strip().rstrip("-")
    if env:
        return env
    text = _tracker_answer()
    m = re.search(r"\*\*Key prefix\*\*\s*\|[^`\n]*`?([A-Za-z][A-Za-z0-9]*)-`?", text)
    return m.group(1) if m else ""


#: What a planning finding names as its runnable fix, keyed by the name a check looks up.
#: Command keys resolve through `command()`; `{program}` / `{prd}` / `{prefix}` are filled by
#: the check with the id the finding is about. Only fixes the shipped layout provides belong
#: here — a repository's own scripts are added by its own configuration.
_FIX_COMMANDS = {
    "slice_create": "slice:create",
    "slice_edit": "slice:edit {slice}",
    "program_decompose": "program:decompose {program}",
    "program_ship": "program:ship {program}",
    "prd_design": "prd:design {prd}",
    "prd_create": "prd:create {prd}",
    "prd_plan": "prd:plan {prd}",
    "prd_verify": "prd:verify {prd}",
    "page_spec": "page:spec",
    "component_create": "component:create",
}
_FIX_SCRIPTS = {
    "allocate_ids": "python3 knowledge/scripts/validate_id_collisions.py --allocate {prefix} 1",
    "unshallow": "git fetch --unshallow",
}


def fix_commands() -> dict[str, str]:
    """`key → invocation` for every fix the tree can name here."""
    named = {key: f"/{namespace()}:{verb}" for key, verb in _FIX_COMMANDS.items()}
    return {**named, **_FIX_SCRIPTS}


def knowledge_base(root: Path | None = None) -> Any:
    """A `KnowledgeBase` over this checkout, whose findings name the tree's own commands.

    The checkout's own `[fleet.planning]` table (in `fleet.toml`) is honoured, so a planning
    option a project sets — `id_claims` above all, which decides whether `--allocate` reserves
    ids on GitHub — means the same thing to these scripts as to `python3 -m fleet_knowledge
    check`. Only that table is read; the rest of the file keeps its existing resolution path.
    """
    fleet_knowledge()
    from fleet_knowledge.checks.planning._api import make_kb  # noqa: PLC0415 — after the path insert
    from fleet_knowledge.config import Config, find_config_file, section_from_table  # noqa: PLC0415

    base = root or repo_root()
    planning: dict[str, Any] = {}
    found = find_config_file(base)
    if found is not None:
        source, table = found
        raw = table.get("planning")
        if raw is not None:
            planning = dict(section_from_table("planning", raw, source))
    planning["commands"] = fix_commands()
    return make_kb(base, Config(planning=planning))


def fleet_knowledge() -> None:
    """Make `fleet_knowledge` importable, or refuse with the command that fixes it."""
    try:
        import fleet_knowledge  # noqa: F401

        return
    except ModuleNotFoundError:
        pass
    src = repo_root() / "fleet" / "packages" / "fleet-knowledge" / "src"
    if (src / "fleet_knowledge").is_dir():
        sys.path.insert(0, str(src))
        return
    raise SystemExit(
        "fleet_knowledge is not importable: install the `fleet-knowledge` package, or check out the "
        f"fleet submodule at {src.parent.parent.parent} (`git submodule update --init fleet`)."
    )
