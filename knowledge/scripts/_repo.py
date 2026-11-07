"""Where am I — the one shipped module that knows the layout.

Every script in this directory is materialized by `fleet commands sync` at a FIXED path,
`<repo>/knowledge/scripts/`, in every repository the tier ships to. That fixed path is the
whole contract: a command names `knowledge/scripts/component_of.py` and runs it, with no id
to resolve and no per-repo binding to get wrong. What differs per repository is read from the
repository — its config, its corpus, its git remote — never baked into a copy of the script.

This module resolves the facts every shipped script needs and nothing else:

  * `repo_root()`   — the checkout, two levels up from `knowledge/scripts/`.
  * `run_state()`   — the checkout-scoped state root for one command
                      (`process/spine.md` → "A command's own state"), which git never commits;
                      `ensure_run_state_ignored()` keeps it out of a tree that ignores it not.
  * `namespace()`   — the command namespace under `.fleet/commands/`, read from the tree
                      rather than spelled, so a script's `/{ns}:verify` follows
                      the tree if the namespace ever moves.
  * `org()` / `slug()` — the GitHub org and `org/name` of this checkout, from `origin`, for
                      the scripts that address the forge; a lane label `repo:<x>` resolves to
                      `<org>/<x>` because every lane lives in one org.
  * `fleet_knowledge()` — import the `fleet_knowledge` package: installed, or its source in
                      this checkout (the `fleet/` submodule mount, this repository's own
                      `packages/fleet-knowledge/src`, or the copy `fleet commands sync`
                      writes in `.fleet/_vendor/`), or — on a packaged worker — by re-executing
                      under the release interpreter `$FLEET_PYTHON`.
                      Loud when none answers, because a gate whose code is absent must fail,
                      never pass quietly.
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

#: The release interpreter a packaged worker's daemon exports into every session — the one
#: `python3` that has `fleet_knowledge`. The daemon's `versiondir.FLEET_PYTHON_ENV` names the same
#: variable; this file is materialized into repositories that cannot import the daemon.
FLEET_PYTHON_ENV = "FLEET_PYTHON"
#: Set on the one hand-over to `$FLEET_PYTHON` and consumed by the process it starts, so an
#: interpreter that cannot import the package either refuses instead of handing over again.
FLEET_PYTHON_REEXEC_ENV = "FLEET_PYTHON_REEXEC"

#: The oldest interpreter these scripts run on — the same floor the package declares in its
#: `pyproject.toml`. The package's first `import tomllib` (and `datetime.UTC`) is 3.11, and a
#: customer checkout runs the scripts with whatever `python3` is on PATH: macOS ships 3.9 at
#: `/usr/bin/python3`, where the import escaped as a raw traceback. Refuse in one plain
#: sentence instead, after the `$FLEET_PYTHON` hand-over has had its chance.
MINIMUM_PYTHON = (3, 11)

#: The repository's answer to the tracker question, where its key prefix and team live.
TRACKER_SLOT = "knowledge/slots/tracker-identity.md"

#: Where a checkout can carry the package's importable source, as repo-relative directories that
#: hold a `fleet_knowledge/` package. Three layouts exist: a customer checkout carries it as the
#: `fleet/` submodule mount; Fleet's own checkout — which AUTHORS the package — carries it at
#: `packages/fleet-knowledge/src` with no submodule beside it; and a repository that receives
#: only the synced tier carries the copy `fleet commands sync` writes at
#: `.fleet/_vendor/`, because it has neither of the first two and installs nothing.
#: Reading only the first is why every knowledge validator refused in Fleet's own repository on
#: a source install, and reading only the first two is why it refused in a customer checkout.
_PACKAGE_SOURCES = (
    ("fleet", "packages", "fleet-knowledge", "src"),
    ("packages", "fleet-knowledge", "src"),
    (".fleet", "_vendor"),
)


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """The checkout this script is materialized in.

    `knowledge/scripts/<me>.py` → two levels up. In the authoring tree the same file sits at
    `commandtree/scripts/`, whose grandparent is the package; the caller (a test) sets the
    root explicitly there, and nothing in this directory assumes a corpus exists beside it.
    """
    return HERE.parent.parent


#: The tier's checkout-scoped run state — `process/spine.md` → "A command's own state". A
#: command's working notes belong here, never in the corpus it describes, and git must never
#: carry them into a commit or a pull request.
RUN_STATE = ".claude/run"
#: The line `fleet init` writes into a repository's `.gitignore`. A checkout that was not
#: initialised gets it in `.git/info/exclude` instead, so a command's notes stay out of the
#: tree even there.
RUN_STATE_IGNORE = RUN_STATE + "/"


def run_state(command: str) -> Path:
    """This checkout's state root for one command (the caller creates it when it writes)."""
    return repo_root() / RUN_STATE / command


def ensure_run_state_ignored(root: Path | None = None) -> None:
    """Make git leave `.claude/run/` out of every commit, even in a checkout that ignores it not.

    `fleet init` writes the line into `.gitignore`; a repository bootstrapped without it would
    otherwise commit the command's own notes. The fallback is `.git/info/exclude` — local to
    this checkout, which is the scope the state itself has, and never a file a customer owns.
    """
    base = root or repo_root()
    probe = subprocess.run(
        ["git", "-C", str(base), "check-ignore", "-q", f"{RUN_STATE_IGNORE}probe"],
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        return
    try:
        git_dir = subprocess.run(
            ["git", "-C", str(base), "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return
    exclude = Path(git_dir)
    if not exclude.is_absolute():
        exclude = base / exclude
    exclude = exclude / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    text = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
    if RUN_STATE_IGNORE in text.splitlines():
        return
    with exclude.open("a", encoding="utf-8") as fh:
        if text and not text.endswith("\n"):
            fh.write("\n")
        fh.write(f"{RUN_STATE_IGNORE}\n")


@lru_cache(maxsize=1)
def namespace() -> str:
    """The command namespace — the one directory under `.fleet/commands/` that holds `.md`."""
    commands = repo_root() / ".fleet" / "commands"
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
    """The tracker team this repository files into: `TRACKER_TEAM_NAME`, else its answer.

    No built-in team: a package cannot know a customer's tracker, and a default is a
    wrong-team lookup that reads as a credential failure. Empty when neither the
    environment nor the repository names one, so the caller fails loudly.
    """
    env = (os.environ.get("TRACKER_TEAM_NAME") or "").strip()
    if env:
        return env
    text = _tracker_answer()
    m = re.search(r"\|[^|\n]*\*\*Tracker\*\*[^|\n]*\|[^|\n]*team\s*\*\*([^*|]+)\*\*", text)
    return m.group(1).strip() if m else ""


#: The slot line answering "what is the issue-key prefix": the legacy table row
#: (`| **Key prefix** | `XYZ-` … |`) or the `## Answers` bullet the bootstrap writes
#: (`- **key-prefix** — XYZ- …`, or `— none: …` on a tracker whose keys carry no prefix).
#: KEEP IN STEP with `validate_verify_gate.py`: CI copies that gate ALONE out of the base ref,
#: so it cannot import this module; `test_shipped_tracker_no_key_prefix` holds both to one table.
_KEY_PREFIX_LINE_RE = re.compile(r"\*\*key[ _-]?prefix\*\*\s*(?:\||—|–|:|-)\s*(?P<value>[^\n|]*)", re.IGNORECASE)
_KEY_PREFIX_VALUE_RE = re.compile(r"(?:^|[\s`])(?P<prefix>[A-Za-z][A-Za-z0-9]*)-(?=[`\s(]|$)")
_NO_KEY_PREFIX_RE = re.compile(r"`?(?:none|no(?:\s+key)?\s+prefix)\b", re.IGNORECASE)


def parse_key_prefix(text: str) -> str | None:
    """A `tracker-identity` answer's key prefix: `"XYZ"`, `""` for an explicit none, None for no answer.

    `""` and None are different facts: `""` is a tracker whose keys have no prefix (GitHub
    Issues, `owner/repo#n`), None is a repository that has not answered.
    """
    for m in _KEY_PREFIX_LINE_RE.finditer(text or ""):
        value = m.group("value").strip()
        if _NO_KEY_PREFIX_RE.match(value):
            return ""
        found = _KEY_PREFIX_VALUE_RE.search(value)
        if found:
            return found.group("prefix")
    return None


def tracker_key_prefix() -> str | None:
    """The key prefix (`ENG`), `""` when the tracker's keys have none, None when unanswered.

    Overridable by `TRACKER_KEY_PREFIX` for an operator who needs it before the answer
    exists; otherwise read from the repository's `tracker-identity` answer (see
    `parse_key_prefix`).
    """
    env = (os.environ.get("TRACKER_KEY_PREFIX") or "").strip().rstrip("-")
    if env:
        return env
    return parse_key_prefix(_tracker_answer())


@lru_cache(maxsize=1)
def tracker_prefix() -> str:
    """The issue-key prefix this repository's tracker uses (`ENG`), or `""`.

    `""` means there is no prefix to compose with — the repository has not answered, or its
    tracker's keys carry none (`tracker_key_prefix` tells the two apart) — and a caller that
    composes issue ids must refuse rather than reserve some other workspace's prefix.
    """
    return tracker_key_prefix() or ""


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


def require_python() -> None:
    """Refuse in one plain sentence when this interpreter is older than `MINIMUM_PYTHON`.

    The package needs 3.11 (its first `import tomllib`, and `datetime.UTC`). A script that uses
    one of those itself calls this before its own import, so an older interpreter gets the same
    one sentence a package-importing script gets, never a raw traceback. A script that can run on
    an older interpreter (stdlib only) never calls this, so it still runs.
    """
    if tuple(sys.version_info[:2]) >= MINIMUM_PYTHON:
        return
    needed = ".".join(str(part) for part in MINIMUM_PYTHON)
    running = ".".join(str(part) for part in sys.version_info[:2])
    raise SystemExit(
        f"these knowledge scripts need Python {needed} or newer, but this interpreter is "
        f"Python {running}; run them with python{needed} or newer."
    )


def fleet_knowledge() -> None:
    """Make `fleet_knowledge` importable, or refuse with the command that fixes it.

    Three answers, in order: the package is installed in this interpreter; this checkout carries
    its source, either as the `fleet/` submodule, at its own `packages/fleet-knowledge/src`, or
    at the copy `fleet commands sync` writes into `.fleet/_vendor/`; or this is a packaged
    worker's session, where the daemon exported the release interpreter as `$FLEET_PYTHON` and
    the script is re-executed under it.

    The second answer's layouts are all real checkouts of the package: a customer checkout
    mounts it as the `fleet/` submodule; Fleet's own checkout — where the package is authored —
    carries it in the monorepo with no submodule; and a repository that received only the synced
    tier has the copy the sync wrote into `.fleet/_vendor/`. Reading only the submodule refused
    every knowledge validator in Fleet itself on a source install; reading only the submodule and
    the monorepo refused every one of them in a customer checkout, which has neither and installs
    nothing.

    The third exists because of where a packaged worker puts its `bin/` on a session's PATH:
    LAST (`fleet_daemon.versiondir.child_path`) — the bundled Node once shadowed a repository's
    pinned Node, so the bundle became a fallback. Every command names a bare
    `python3 knowledge/scripts/…`, which on such a box is the HOST's interpreter — a system
    Python on the worker that reported it — with no `fleet_knowledge`, so every knowledge
    validator refused although `/opt/fleet/current/bin/python3` would have run it. Moving the
    bundle first again would re-break the Node fix for `python3`; the rule `child_path` states —
    Fleet's own tools reach their bundled runtime by absolute path, never through PATH — is what
    this follows instead.

    The hand-over happens at most once per chain. The realpath comparison is not enough to stop
    a loop: the release `bin/python3` is a wrapper script, whose realpath is never the
    interpreter it execs. So the hand-over sets `FLEET_PYTHON_REEXEC`, and the process it starts
    pops it on entry — a second refusal is then final, and the marker never reaches a child
    the script itself spawns, which may need its own hand-over.

    `MINIMUM_PYTHON` is the floor the package declares, and the one answer left when the
    interpreter is too old: macOS ships 3.9 at `/usr/bin/python3`, where the package's first
    `import tomllib` is a traceback. The hand-over gets its chance first, so a worker whose
    release interpreter is new still runs; otherwise the refusal is one plain sentence.
    """
    handed_over = os.environ.pop(FLEET_PYTHON_REEXEC_ENV, None) is not None
    try:
        import fleet_knowledge  # noqa: F401

        return
    except ModuleNotFoundError:
        pass
    src = _checkout_package_source()
    # An older interpreter cannot run the package's source at all: its first `import tomllib` is
    # 3.11. Inserting the path there would only turn a plain refusal into a traceback, so hand
    # over to the worker's release interpreter first when one is exported, then refuse in words.
    too_old = tuple(sys.version_info[:2]) < MINIMUM_PYTHON
    if src is not None and not too_old:
        sys.path.insert(0, str(src))
        return
    if not handed_over:
        _reexec_under_fleet_python()
    require_python()
    tried = f" — FLEET_PYTHON={os.environ.get(FLEET_PYTHON_ENV, '')} could not import it either" if handed_over else ""
    submodule = repo_root().joinpath(*_PACKAGE_SOURCES[0])
    raise SystemExit(
        "fleet_knowledge is not importable: install the `fleet-knowledge` package, check out the "
        f"fleet submodule at {submodule.parent.parent.parent} (`git submodule update --init fleet`), "
        f"carry its source at {repo_root().joinpath(*_PACKAGE_SOURCES[1])} or "
        f"{repo_root().joinpath(*_PACKAGE_SOURCES[2])} (`fleet commands sync` writes the second), "
        "or, on a packaged Fleet worker, let the daemon export the release interpreter as "
        f"`FLEET_PYTHON` (or run the script with `/opt/fleet/current/bin/python3`){tried}."
    )


def _checkout_package_source() -> Path | None:
    """This checkout's own `fleet_knowledge` source directory, or None when it carries none.

    Every layout `_PACKAGE_SOURCES` names is real: the customer submodule mount, Fleet's own
    monorepo, and the vendored copy a synced customer checkout receives. The package's presence
    is judged by a `fleet_knowledge/` directory, never by the layout path alone, so an unrelated
    `packages/` tree is not mistaken for the package.
    """
    for parts in _PACKAGE_SOURCES:
        src = repo_root().joinpath(*parts)
        if (src / "fleet_knowledge").is_dir():
            return src
    return None


def _reexec_under_fleet_python() -> None:
    """Replace this process with the same script under `$FLEET_PYTHON`, when that can help.

    Returns (so the caller refuses) when the variable is unset, does not name an executable,
    names the interpreter already running, or this process was not started as a script file
    (`python3 -c …`, an import from a test), where there is no argv to hand over.
    """
    target = (os.environ.get(FLEET_PYTHON_ENV) or "").strip()
    if not target or not os.path.isfile(target) or not os.access(target, os.X_OK):
        return
    if os.path.realpath(target) == os.path.realpath(sys.executable):
        return
    script = sys.argv[0] if sys.argv else ""
    if not script or not os.path.isfile(script):
        return
    sys.stdout.flush()
    sys.stderr.flush()
    os.environ[FLEET_PYTHON_REEXEC_ENV] = "1"
    os.execv(target, [target, os.path.abspath(script), *sys.argv[1:]])
