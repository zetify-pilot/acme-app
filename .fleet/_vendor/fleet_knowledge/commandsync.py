"""The shared command tier, and putting it where a repository's agent will find it.

A slash command is a **portable procedure**; a repository is a set of filled-in slots
(`slots.py`). That claim was true on paper and false in practice, because the procedures
themselves lived in exactly one repository's `.claude/` directory and a second repository
could obtain them only by copying — which is the failure this project has already paid for
once at code scale. `fleet_agents/lanes.py` was a byte-identical second copy of the lane
table with nothing pinning the two together, and `repo:fleet` spent a day known to one and
unknown to the other. A 1.3 MB copy of thirty-four procedures, edited in two places by two
fleets, is the same bug with a longer fuse.

So the tier SHIPS WITH THE PACKAGE, under `commandtree/`, and this module writes it into a
target repository's `.claude/`. The version of the procedure a repository is on is then its
`fleet-knowledge` version — a question with an answer — rather than "whenever somebody last
remembered to copy".

**Why materialize at all, rather than read it in place.** The agent harness reads files in
the repository, not a package or a submodule. Every distribution shape therefore ends in the
same step — real files in the checkout — so the only real choice is what those files are a
copy OF, and a versioned package pin beats a hand-copy.

**Where they land: `.fleet/`, as a Claude Code plugin** (`layout = "plugin"`). The tier used
to land in `.claude/`, and everything under `.claude/commands` loads into EVERY session opened
in the repository — each engineer's own Claude, not only the fleet's. A customer objected to
exactly that. `.fleet/` is a directory no harness scans by itself: the fleet launches its
sessions with `--plugin-dir .fleet`, an engineer who wants the commands opts in the same way,
and the files stay ordinary tracked files anyone can read and change. The plugin manifest
points `commands` at `commands/<namespace>/`, so the tree under `.fleet/` has exactly the shape
it had under `.claude/` — command names and every relative link are unchanged — and prose that
names a tier path (`.claude/process/x.md`) is rendered to the new one. It is the ONLY layout:
`layout = "claude"` (the old `.claude/` home) is refused by name, and a repository still
carrying the old tree has it deleted by its next sync, because a `.claude/commands` copy left
behind would SHADOW the plugin's same-named commands (the repository copy wins, measured on
Claude Code 2.1.300). `CLAUDE_DIR` survives only so that sync can find what to delete.

**`--check` is the half that makes it a contract.** A materialized tree nobody compares is a
copy again by the next commit. `verify()` reports drift as data, so CI can fail on it and a
person can see which files moved before anything is overwritten.

Stdlib only, like the rest of this package.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import subprocess
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from fleet_knowledge import authoring, docsmd, textdiff
from fleet_knowledge import commands as commandmod
from fleet_knowledge import config as configmod
from fleet_knowledge import release as releasemod
from fleet_knowledge import targets as targetsmod

if TYPE_CHECKING:
    from fleet_knowledge.setupfiles import Inputs, SetupPlan

__all__ = [
    "CUSTOMER_NAMESPACE",
    "DEFAULT_LAYOUT",
    "DOCS_REL",
    "DOCS_SUBDIR",
    "LAYOUTS",
    "LEGACY_MANIFEST_REL",
    "LEGACY_VOCABULARY_REL",
    "LOCAL_DIR",
    "RETIRED_LAYOUTS",
    "SANCTIONED_DOCS_URLS_FILE",
    "MANIFEST_FORMAT",
    "MANIFEST_NAME",
    "ManifestRecord",
    "PLUGIN_DIR",
    "MARKETPLACE_NAME",
    "MARKETPLACE_REL",
    "PLUGIN_MANIFEST_REL",
    "optin_settings",
    "SCRIPTS_DEST",
    "SYNC_DIRS",
    "TIER_DIRS",
    "VOCABULARY_REL",
    "VOCABULARY_SOURCE",
    "SyncReport",
    "blob_sha",
    "command_description",
    "command_frontmatter",
    "keep_at",
    "commands_config",
    "declared_commands_config",
    "commands_layout",
    "commands_targets",
    "core_commands",
    "docs_source",
    "manifest_bytes",
    "manifest_path",
    "manifest_record_bytes",
    "parse_manifest",
    "read_manifest",
    "read_manifest_record",
    "repo_name",
    "render_docs",
    "render_file",
    "render_tree",
    "sanctioned_docs_urls",
    "shipped_verbs",
    "source_namespace",
    "source_root",
    "sync",
    "tree_modes",
    "verify",
    "without_command_prefix",
]

#: A repository's command namespace (PRD 0746 D1). At least two characters and lower-case
#: alphanumeric-plus-hyphen, so it cannot collide with the source namespace's own shape and
#: cannot be a single letter a person reads as a typo.
NAMESPACE_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")

#: THE CUSTOMER DEFAULT IS THE TREE'S OWN NAMESPACE (owner decision 2026-10-15): the company
#: that authors the tree ships the fleet, so a customer's commands are typed under the same prefix
#: its own are. `fleet init`, the setup page's pull request and the service's dispatch default all
#: read `CUSTOMER_NAMESPACE` (bound at the end of this module, once `source_namespace` exists); a
#: repository may still declare its own.
#:
#: Being the source namespace is NOT what makes a render the home's: a repository that DECLARES
#: any namespace, this one included, gets the customer render (home text dropped). Only a
#: repository that declares none gets the home render — see `render`.
#:
#: The prefix is also THE ONE VENDOR-NAMED STRING a customer render may carry, in exactly three
#: shapes, lower-case (`<ns>` being this namespace):
#:
#:   * `/<ns>:` — the slash form, as typed (`/<ns>:check`) or as a bare prefix literal;
#:   * `<ns>:<verb>` — the colon key a board or a vocabulary names a command by, with a
#:     lower-case letter after the colon so a port (`<ns>:443`) is not one;
#:   * the line `namespace = "<ns>"` — the `[fleet.commands]` declaration that chose it.
#:
#: Neither form may be glued to a longer name: `<Org>/<ns>:docs`, `<ns>-k8s`, `<ns>.ai`, a
#: capitalised `<Ns>:` and a bare `<ns>` all survive `without_command_prefix` and are still
#: caught by every deny-list that runs after it.


def _command_prefix(namespace: str) -> re.Pattern[str]:
    ns = re.escape(namespace)
    return re.compile(
        rf"(?<![A-Za-z0-9_./-])(?:/{ns}:|{ns}:(?=[a-z]))"
        rf'|^[ \t]*namespace[ \t]*=[ \t]*"{ns}"[ \t]*$',
        re.MULTILINE,
    )


def without_command_prefix(text: str) -> str:
    """`text` with every sanctioned command-prefix occurrence blanked, ready for a deny-list.

    Blanked to spaces of the same length, not deleted, so a line or column a scanner reports
    afterwards still points at the original text. Anything else naming the vendor survives.
    """
    return _COMMAND_PREFIX.sub(lambda m: " " * len(m.group(0)), text)


#: The command set a repository receives (PRD 0746 D3): `core` is the generic work loop and
#: what it names; `all` is every command the tree carries.
SETS: tuple[str, ...] = ("core", "all")

#: The directories that make up the shared tier, relative to `commandtree/` and to `.claude/`.
#:
#: `commands` is in the list and that is the whole point — the procedures are the portable
#: thing. `process`, `registers` and `rubrics` ride along because the commands CITE them: a
#: command whose `requires:` names `process-envelope` and whose prose links
#: `../../../process/autonomous-drive.md` is broken in a repository that received the command
#: and not the document. Shipping a subset would reproduce the broken-reference class this
#: layer exists to detect.
TIER_DIRS: tuple[str, ...] = ("process", "registers", "rubrics", "commands")

#: Where a target repository keeps them (see the module docstring): `.fleet`, as a plugin.
#: `.claude` is the retired home — named here only so a sync can delete a copy left there, and
#: `"claude"` in `LAYOUTS` only as the layout of that copy; `commands_layout` refuses it.
CLAUDE_DIR = ".claude"
PLUGIN_DIR = ".fleet"
LAYOUTS: tuple[str, ...] = ("claude", "plugin")
DEFAULT_LAYOUT = "plugin"
RETIRED_LAYOUTS: frozenset[str] = frozenset({"claude"})
#: The plugin manifest Claude Code reads from `--plugin-dir`. Rendered, not copied: it names the
#: repository's namespace. Its report name, like `VOCABULARY_SOURCE`, is not a source path.
PLUGIN_MANIFEST_SOURCE = ".claude-plugin/plugin.json"
PLUGIN_MANIFEST_REL = f"{PLUGIN_DIR}/{PLUGIN_MANIFEST_SOURCE}"
#: A one-plugin MARKETPLACE beside it, so a person's session can opt in through settings rather than
#: a flag: `--plugin-dir` is the fleet's way and works headless, but an interactive `claude` cannot be
#: handed a flag by a repository. With this file, `.claude/settings.json` (a team) or
#: `.claude/settings.local.json` (one person) loads the tier — see `optin_settings`. Measured on
#: Claude Code 2.1.301: the commands appear in an interactive session from settings alone, and vanish
#: when the setting is removed. Headless `claude -p` does not load a settings-enabled plugin.
MARKETPLACE_SOURCE = ".claude-plugin/marketplace.json"
MARKETPLACE_REL = f"{PLUGIN_DIR}/{MARKETPLACE_SOURCE}"
#: The marketplace's name, the half after `@` in `enabledPlugins` — `<namespace>@fleet`.
MARKETPLACE_NAME = "fleet"


def tier_root(layout: str = DEFAULT_LAYOUT) -> str:
    """The directory the tier (all but the scripts) lands under for `layout`."""
    return PLUGIN_DIR if layout == "plugin" else CLAUDE_DIR


#: The shipped tooling: the scripts the commands run, materialized at a FIXED path in every
#: repository (`knowledge/scripts/`). A command names `knowledge/scripts/component_of.py`
#: and that is the whole contract — no id, no register, no per-repo binding. The first
#: version of this layer abstracted the tooling behind ids and a mapping, and the mapping
#: was where five of twenty-nine bindings went wrong while every check passed; a convention
#: has no mapping to get wrong. Repository-specific behaviour lives INSIDE these scripts,
#: read from the repo's own config (`.env`, `fleet.toml`, the corpus) — never in a per-repo
#: copy of the script, which is why they are generated-and-verified like the tier.
SCRIPTS_SUBDIR = "scripts"
SCRIPTS_DEST = "knowledge/scripts"

#: THE PACKAGE TRAVELS WITH THE TIER. A script in `knowledge/scripts/` is a thin shim over
#: `fleet_knowledge`; in a customer checkout there is no `fleet/` submodule and no installed
#: package, so the sync writes the package's own source under `.fleet/_vendor/`.
#: `_repo.fleet_knowledge()` finds it at this fixed path. The authors' own checkout is skipped:
#: it carries the source tree the scripts should read, and a stale copy would shadow an edit.
VENDOR_SUBDIR = "_vendor"
VENDOR_DEST = f"{PLUGIN_DIR}/{VENDOR_SUBDIR}"
VENDOR_PACKAGE = f"{VENDOR_DEST}/fleet_knowledge"
#: The one package file that is the authors' own debt, not the customer's: the portability
#: baseline names findings in THIS repository's command tree, and shipping it would hand each
#: repository a list of somebody else's unfinished work. The check reads it only for the home
#: render, which a customer checkout never is.
VENDOR_EXCLUDE = frozenset({"portability.baseline"})


def dest_dir(d: str, layout: str = DEFAULT_LAYOUT) -> str:
    """Where tier directory `d` lands in a repository, relative to its root."""
    return SCRIPTS_DEST if d == SCRIPTS_SUBDIR else f"{tier_root(layout)}/{d}"


#: Every directory the sync carries, in order: the tier under `.claude/`, then the scripts.
SYNC_DIRS: tuple[str, ...] = (*TIER_DIRS, SCRIPTS_SUBDIR)

#: The manifest recording every repo-relative path the last sync WROTE. It is what lets a pin
#: bump tell the tier's own stale output from a repository's own addition: a file a previous
#: sync wrote, that the pinned package no longer ships, is deleted without `--prune`, because
#: the sync is on record as the one that put it there. A dotfile at the tier's own home, so a
#: walk of the tier never mistakes it for content and `.claude/` stays a place a repository may
#: keep its own settings. It lives BESIDE the tier rather than inside a scanned directory.
MANIFEST_NAME = ".fleet-sync-manifest.json"
MANIFEST_REL = f"{PLUGIN_DIR}/{MANIFEST_NAME}"
#: Where the retired layout kept it — what a sync deletes from a repository moving off `.claude/`.
LEGACY_MANIFEST_REL = f"{CLAUDE_DIR}/{MANIFEST_NAME}"


def manifest_rel(layout: str = DEFAULT_LAYOUT) -> str:
    return f"{tier_root(layout)}/{MANIFEST_NAME}"


#: THE BOARD VOCABULARY RIDES WITH THE TIER (ENG-17173). The board names a repository's commands
#: from the document its `fleet.toml` points at (`board_guidance`): the catalogue, the per-view
#: boxes, the command each finding and each PRD status hands over, the shaping buttons. A tier
#: shipped without one left a freshly set-up repository's board naming none of the commands it
#: had just received — no driver on a program, "No command" on every to-do, no Fill box on a stub
#: — and nothing but chart comments said the key existed. So the source sits beside the tier
#: (outside `SYNC_DIRS`: it is rendered, not copied) and lands at a fixed path, rewritten to the
#: repository's namespace and narrowed to the commands its set carries, by the same sync and the
#: same drift check as everything else here.
VOCABULARY_SOURCE = "board-guidance.json"
VOCABULARY_REL = f"{PLUGIN_DIR}/{VOCABULARY_SOURCE}"
LEGACY_VOCABULARY_REL = f"{CLAUDE_DIR}/{VOCABULARY_SOURCE}"


def vocabulary_rel(layout: str = DEFAULT_LAYOUT) -> str:
    return f"{tier_root(layout)}/{VOCABULARY_SOURCE}"


#: FLEET'S OWN DOCS RIDE WITH THE TIER, AS FILES A SESSION CAN READ. The product docs
#: (`fleet_knowledge/productdocs/`, contract in its `README.md`) are how to use Fleet and how a
#: knowledge base is built — what a session on a box needs open beside the commands that cite the
#: same words. The service answers them through `read_doc`, but a session reads its checkout before
#: it reaches for a tool, so they land at `.fleet/docs/` as the AGENT READING (`docsmd.render_files`):
#: plain markdown, one file per page at its id (`docs/knowledge-base/slices.md`), an `index.md` in
#: reading order under each page's job, and `terms.md`. Never the source: a directive an agent cannot
#: resolve, front matter and Fleet's own source paths have no place in a customer's checkout, and the
#: live facts the service fills in are left to `read_doc`, because a committed file cannot hold them.
#: Same sync, same manifest, same `--check` as every tier file: a page the package stops shipping is
#: RETIRED by the next sync, a file a person added under `.fleet/docs/` is FOREIGN, a hand-edit is
#: STALE. The source sits beside `commandtree/` (it is this package's, not the tier's), and only the
#: plugin layout carries it — the retired `.claude/` home never had it.
DOCS_SUBDIR = "docs"
DOCS_REL = f"{PLUGIN_DIR}/{DOCS_SUBDIR}"

#: THE VENDOR-NAMED URLS THE PRODUCT DOCS MAY CARRY, held as data beside the tree. `fleet-knowledge`
#: is not on an index and will not be, so a person who needs the `fleet` command must copy the
#: supported install command's repository URL; the customer install guides already allow the same
#: repository (`deploy/docs/names.toml`). They are sanctioned ONLY in the product-docs reading
#: (`.fleet/docs/`) and in the agent reading of those pages, never in a command render — see
#: `checks/slots/_render.scan_rendered`. The strings are data, like the vendor deny-list, so this
#: package's modules carry no product name of their own.
SANCTIONED_DOCS_URLS_FILE = "sanctioned_docs_urls.txt"


def sanctioned_docs_urls() -> tuple[str, ...]:
    """The vendor-named URLs the product-docs reading may carry, from the shipped data file.

    Empty when the file is absent, so a package that predates the file refuses every vendor name
    rather than failing to load. The caller blanks these exact strings before a vendor scan; a
    command render never does.
    """
    path = source_root() / SANCTIONED_DOCS_URLS_FILE
    if not path.is_file():
        return ()
    return tuple(
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


#: FLEET'S OWN INSTRUCTIONS, SHIPPED UNDER `.fleet/` (ENG-22456). The primer ENG-21998 added
#: lived only in the managed block of `CLAUDE.md`/`AGENTS.md` and in the MCP instructions. A
#: repository whose own rules file predates Fleet never receives the block, so a session there
#: reads the customer's rules and never learns what Fleet is. The sync now writes the primer at
#: the tier's root, and each engine loads it without touching that file:
#:
#: * opencode — the daemon lists this path in the session config's `instructions`;
#: * Claude Code — the plugin's `hooks/hooks.json` prints it at `SessionStart`, and a session
#:   loads the plugin with `--plugin-dir .fleet` (Fleet's own sessions) or the settings opt-in.
INSTRUCTIONS_SOURCE = "AGENTS.md"
INSTRUCTIONS_REL = f"{PLUGIN_DIR}/{INSTRUCTIONS_SOURCE}"
HOOKS_SOURCE = "hooks/hooks.json"
HOOKS_REL = f"{PLUGIN_DIR}/{HOOKS_SOURCE}"
#: PR FRESHNESS: the script behind the `UserPromptSubmit` / `PostToolUse` hooks (and the opencode
#: plugin, which shells out to the same file), so a PR named in a session arrives with its live
#: state. Authored beside `commandtree/`'s other files and copied byte for byte.
PR_FRESHNESS_SOURCE = "hooks/pr_freshness.py"
PR_FRESHNESS_REL = f"{PLUGIN_DIR}/{PR_FRESHNESS_SOURCE}"


#: Files an earlier release wrote at the tier's root under a name it no longer uses. The sync
#: deletes one only when its manifest records it, so a file a person put there stays.
LEGACY_PLUGIN_FILES = (f"{PLUGIN_DIR}/instructions.md",)


def render_instructions(*, namespace: str = "", src: Path | None = None) -> bytes:
    """`.fleet/AGENTS.md`: Fleet's primer for the repository's namespace, plus the generated file-type table."""
    primer = render(
        src or source_root(),
        Path(INSTRUCTIONS_SOURCE),
        namespace=namespace,
        layout=DEFAULT_LAYOUT,
    )
    # The file-type table is generated from `authoring.KINDS`, so it cannot drift from the registry.
    return primer.rstrip(b"\n") + b"\n\n" + authoring.render_table_section().encode("utf-8")


def render_hooks(*, namespace: str = "", src: Path | None = None) -> bytes:
    """`.fleet/hooks/hooks.json`: the Claude Code `SessionStart` hook that prints the primer.

    A plugin's `hooks/hooks.json` loads wherever the plugin does, so a Fleet session and an
    engineer who opted into the tier both start from Fleet's instructions. The command reads the
    file at session start, never a copy, so a newer sync reaches the next session.
    """
    del namespace, src
    doc = {
        "description": "Fleet's own instructions, loaded at the start of every session.",
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f'cat "${{CLAUDE_PLUGIN_ROOT}}/{INSTRUCTIONS_SOURCE}"',
                        }
                    ]
                }
            ],
            "UserPromptSubmit": [_freshness_group()],
            "PostToolUse": [_freshness_group()],
        },
    }
    return (json.dumps(doc, indent=2) + "\n").encode("utf-8")


def _freshness_group() -> dict[str, object]:
    """The hook group that runs the PR-freshness script (30 s ceiling; the script's own is ~5 s)."""
    return {
        "hooks": [
            {
                "type": "command",
                "command": f'python3 "${{CLAUDE_PLUGIN_ROOT}}/{PR_FRESHNESS_SOURCE}" claude',
                "timeout": 30,
            }
        ]
    }


def render_pr_freshness(*, namespace: str = "", src: Path | None = None) -> bytes:
    """`.fleet/hooks/pr_freshness.py`: the shipped script, byte for byte."""
    del namespace
    return ((src or source_root()) / PR_FRESHNESS_SOURCE).read_bytes()


def docs_source(src: Path | None = None) -> Path:
    """The packaged docs beside the tier `src` (`<package>/productdocs`); absent for a bare tree."""
    return (src or source_root()).parent / "productdocs"


def render_docs(src: Path | None = None) -> dict[str, bytes]:
    """`{repo-relative path: bytes}`: the packaged docs as an agent reads them, under `.fleet/docs/`."""
    root = docs_source(src)
    if not (root / docsmd.INDEX_FILE).is_file():
        return {}
    files = docsmd.render_files(docsmd.load(root))
    return {f"{DOCS_REL}/{rel}": text.encode("utf-8") for rel, text in sorted(files.items())}


#: THE REPOSITORY'S OWN OVERRIDES (`.fleet/local/`). The sync never writes, deletes or reports a
#: file under it. A file there at a tier path — `commands/<namespace>/check.md`,
#: `process/x.md`, `registers/…`, `rubrics/…`, or `scripts/x.py` for `knowledge/scripts/x.py` —
#: is what the sync writes AT that path instead of the shipped file (an override), or beside the
#: shipped ones when the release has no such file (an extension). Materialised, rather than left
#: for a loader to find: every reader of the tier — the daemon expanding a command for an
#: opencode run, a Claude Code session loading the plugin, a command following a link to a
#: process document, a hook running a script — reads the path the tier says, and none of them
#: knows an overlay exists. So the file at the tier path is always the one that runs, `--check`
#: compares against it, and the manifest records it; deleting the override restores the shipped
#: file on the next sync. `.fleet/local/` itself is not a directory the plugin loader scans (it
#: loads `commands/` at the plugin root), so an override is never loaded twice.
LOCAL_DIR = f"{PLUGIN_DIR}/local"


def keep_at(path: str) -> str | None:
    """Where an override of the synced file `path` goes (`.fleet/local/…`), or `None` if none can."""
    if path.startswith(f"{VENDOR_DEST}/"):
        return None
    if path.startswith(f"{SCRIPTS_DEST}/"):
        return f"{LOCAL_DIR}/{SCRIPTS_SUBDIR}/{path[len(SCRIPTS_DEST) + 1 :]}"
    head = f"{PLUGIN_DIR}/"
    rest = path[len(head) :] if path.startswith(head) else ""
    if rest.split("/", 1)[0] in TIER_DIRS:
        return f"{LOCAL_DIR}/{rest}"
    return None


def _overlay(repo: Path, namespace: str, layout: str) -> tuple[dict[str, bytes], list[str]]:
    """`({tier path: the override's bytes}, [files under .fleet/local/ that map to no tier path])`."""
    base = repo / LOCAL_DIR
    if layout != "plugin" or not base.is_dir():
        return {}, []
    target_ns = namespace or source_namespace()
    out: dict[str, bytes] = {}
    ignored: list[str] = []
    for rel in _files(base):
        parts = rel.parts
        local = f"{LOCAL_DIR}/{rel.as_posix()}"
        if len(parts) < 2 or parts[0] not in SYNC_DIRS or (parts[0] == COMMANDS_SUBDIR and parts[1] != target_ns):
            ignored.append(local)
            continue
        dest = (
            f"{SCRIPTS_DEST}/{Path(*parts[1:]).as_posix()}"
            if parts[0] == SCRIPTS_SUBDIR
            else f"{PLUGIN_DIR}/{rel.as_posix()}"
        )
        out[dest] = (base / rel).read_bytes()
    return out, ignored


def manifest_path(repo: Path, layout: str | None = None) -> Path:
    """Where the sync records the paths it wrote: `<repo>/<tier root>/.fleet-sync-manifest.json`.
    `layout` defaults to the repository's own (`commands_layout`)."""
    return repo / manifest_rel(layout if layout is not None else commands_layout(repo))


#: The manifest's current shape (ENG-18630): `{"format": 2, "version": <release>, "files": {path: blob id}}`.
#: Format 1 — the bare sorted list of paths every repository synced before it holds — stays readable
#: and is still accepted by `--check`; the next `sync` rewrites it in this shape.
MANIFEST_FORMAT = 2


def blob_sha(data: bytes) -> str:
    """Git's own object id for a blob of `data` — what `git hash-object` prints for the same bytes.

    The manifest records this per file, rather than any other digest, because it is the id a git
    tree already carries: a caller that holds only a tree (the service, reading GitHub) can tell a
    file the sync wrote from one a person changed without downloading it.
    """
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


@dataclass(frozen=True)
class ManifestRecord:
    """What the previous sync recorded: its format, its release, and each path it wrote.

    `format` is `0` when there is no readable record, `1` for the paths-only list (every hash
    `None`, the version `""` — unknown), and `2` for a record with the release and a blob id per
    file. `version` is `""` whenever the writer did not know its release.
    """

    format: int = 0
    version: str = ""
    files: dict[str, str | None] = field(default_factory=dict)
    #: What the sync recorded about the setup files beyond the tier (`setupfiles`): `{"files":
    #: {path: blob id of Fleet's part}, "stacks": [...], "ciRunner": ...}`; `{}` for none.
    setup: dict[str, object] = field(default_factory=dict)
    #: The command namespace and set the previous sync rendered (`{"namespace": ..., "set": ...}`).
    #: `{}` for a record written before this key existed. It is what lets an undeclared kept
    #: `fleet.toml` keep the namespace `fleet init` chose instead of reverting to the home copy on
    #: the next plain sync (ENG-21055): the manifest is Fleet's own record of what it wrote.
    commands: dict[str, object] = field(default_factory=dict)


def parse_manifest(data: bytes) -> ManifestRecord:
    """A manifest's bytes as a record. Never raises: anything unreadable is format `0`, empty.

    A corrupt or hand-edited manifest must not brick the sync that exists to fix the tree, and an
    empty record is the safe direction — no file is deleted on the strength of a manifest this
    process could not parse.
    """
    try:
        doc = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return ManifestRecord()
    if isinstance(doc, list):
        return ManifestRecord(format=1, files={item: None for item in doc if isinstance(item, str)})
    if not isinstance(doc, dict):
        return ManifestRecord()
    files = doc.get("files")
    if not isinstance(files, dict):
        return ManifestRecord()
    version = doc.get("version")
    setup = doc.get("setup")
    commands = doc.get("commands")
    return ManifestRecord(
        format=MANIFEST_FORMAT,
        version=releasemod.normalize(version) if isinstance(version, str) else "",
        files={path: sha for path, sha in files.items() if isinstance(path, str) and isinstance(sha, str)},
        setup=setup if isinstance(setup, dict) else {},
        commands=commands if isinstance(commands, dict) else {},
    )


def read_manifest_record(repo: Path, layout: str | None = None) -> ManifestRecord:
    """The previous sync's record (`parse_manifest`), or an empty one when there is none."""
    path = manifest_path(repo, layout)
    if not path.is_file():
        return ManifestRecord()
    try:
        return parse_manifest(path.read_bytes())
    except OSError:
        return ManifestRecord()


def read_manifest(repo: Path, layout: str | None = None) -> set[str]:
    """The repo-relative paths the previous sync wrote. `set()` when absent or unreadable."""
    return set(read_manifest_record(repo, layout).files)


def manifest_bytes(paths: set[str]) -> bytes:
    """A FORMAT 1 manifest: the sorted paths, one JSON string per line.

    No sync writes this shape any more (`manifest_record_bytes` does); it is what every repository
    synced before ENG-18630 holds, kept so a test or a tool can produce one.
    """
    return (json.dumps(sorted(paths), indent=0) + "\n").encode("utf-8")


def manifest_record_bytes(
    files: Mapping[str, bytes],
    *,
    version: str | None = None,
    setup: Mapping[str, object] | None = None,
    commands: Mapping[str, object] | None = None,
) -> bytes:
    """The manifest a sync writes over `files` (`{repo-relative path: the bytes written}`).

    The release (`release.version()` unless given) and each file's `blob_sha`, the paths sorted and
    one per line, so a pin bump's diff names exactly the files that entered, left or changed.
    `setup` is the record of the setup files (`setupfiles.SetupPlan.record`), written only when
    there is one — a reader that predates it ignores the key. `commands` records the namespace and
    set this render used, so a later plain sync over a kept `fleet.toml` that declares neither can
    keep them (ENG-21055).
    """
    doc: dict[str, object] = {
        "format": MANIFEST_FORMAT,
        "version": releasemod.version() if version is None else version,
        "files": {path: blob_sha(files[path]) for path in sorted(files)},
    }
    if setup:
        doc["setup"] = dict(setup)
    if commands:
        doc["commands"] = dict(commands)
    return (json.dumps(doc, indent=0) + "\n").encode("utf-8")


def manifest_stale(
    record: ManifestRecord, expected: Mapping[str, bytes], setup: Mapping[str, object] | None = None
) -> bool:
    """Whether `record` fails to describe a sync that wrote `expected` (`{path: bytes}`).

    The paths must match in either format; a format 2 record's hashes must match too, and so must
    its setup record when the caller passes the one this sync would write. The release line is
    never compared: it is provenance, not drift, and a tree written from a checkout one commit
    away reads the same.
    """
    if record.format == 0 or set(record.files) != set(expected):
        return True
    if setup is not None and dict(setup) != record.setup:
        return True
    if record.format < MANIFEST_FORMAT:
        return False
    return any(record.files[path] != blob_sha(data) for path, data in expected.items())


#: The include marker: `<!-- include: process/interview-card.md -->` alone on a line, naming a
#: file relative to the tier root. Rendering replaces the marker (and any block it already
#: carries) with the marker, the named file's text, and `INCLUDE_CLOSE` — so the SOURCE holds
#: the text once and the MATERIALIZED tree holds it where it is read.
#:
#: Why inline at sync time rather than point: a pointer is a sentence saying "read that file",
#: and nothing in any harness honours it — `loads:` in a spine is metadata, `@file` and
#: `` !`cat` `` are Claude Code preprocessing that the daemon's `expand_slash_command` never
#: runs for another engine, and both need a permission grant to not abort the invocation. The
#: interview protocol's plain-words rule was pointed at from ten commands and re-added by hand
#: four times in four weeks while the questions stayed id-dense; the failure was the pointer,
#: not the rule. Materialized text needs no runtime and cannot be skipped, and `--check` still
#: catches a hand-edit inside the block because it compares against the rendered source.
#:
#: Included text is rendered the same way, so a shared document may itself include one — the
#: interview card carries the writing rules (`process/writing.md`), and every command that inlines
#: the card carries them too. A file that includes itself, directly or through another, is refused.
#: A block already carried is found by BALANCING its markers (`_block_end`), never by the first
#: close after it, so a rendered file with nested blocks still re-renders to itself.
_INCLUDE_LINE = re.compile(r"^<!-- include: (\S+) -->\n\Z")
_INCLUDE = re.compile(
    r"^<!-- include: (\S+) -->\n(?:.*?\n)??<!-- /include -->\n|^<!-- include: (\S+) -->\n",
    re.M | re.S,
)
INCLUDE_CLOSE = "<!-- /include -->"


def include_open(rel: str) -> str:
    """The opening marker for `rel` — what a source file writes to pull `rel` in."""
    return f"<!-- include: {rel} -->"


#: The home-only segment markers (PRD 0746 D2): text that belongs to the tree's own home
#: (the home project's issue keys, requirement ids, dated incidents, paths into its documents)
#: is wrapped so a foreign render keeps the generic alternative and a home render keeps the
#: home text. Rendered OUT in both directions, so a home render is byte-identical to the text
#: as if the markers were never written.
HOME_OPEN = "<!-- home -->"
HOME_ELSE = "<!-- else -->"
HOME_CLOSE = "<!-- /home -->"
_HOME = re.compile(
    rf"{re.escape(HOME_OPEN)}(.*?)(?:{re.escape(HOME_ELSE)}(.*?))?{re.escape(HOME_CLOSE)}",
    re.S,
)
_MARKER_LEFTOVER = (HOME_OPEN, HOME_ELSE, HOME_CLOSE)

#: `../../../process/autonomous-drive.md`, `registers/triage-partition.md` — a link into the
#: shared tier, which every repository receiving the core set must also receive.
_SHARED_LINK = re.compile(r"(?:\.\./)*(process|registers|rubrics)/([A-Za-z0-9_./-]+\.md)")
#: A shipped script a command or document runs, cited at its fixed layout path.
_SCRIPT_REF = re.compile(r"knowledge/scripts/([A-Za-z0-9_./-]+\.py)")
#: A tier path named in prose (`.claude/process/x.md`, `.claude/commands/<ns>/check.md`) — the
#: spelling the source is authored in, rewritten to `.fleet/…` by a plugin-layout render. Only the
#: tier's own names: `.claude/settings.json`, `.claude/run/` and the rest are a repository's own
#: harness configuration and stay where they are.
_TIER_PATH = re.compile(
    r"\.claude/(process|registers|rubrics|commands|board-guidance\.json|\.fleet-sync-manifest\.json)\b"
)
#: A bare sibling import inside a shipped script (`import _repo`, `from linear_client import …`).
_PY_IMPORT = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
#: A sibling a script loads BY PATH — `importlib.util.spec_from_file_location(..., HERE / "x.py")`
#: or `Path(__file__).resolve().parent / "x.py"` — because `scripts/` is not a package (ENG-18194).
#: `_PY_IMPORT` never saw these, so a `set = "core"` repository received the script and not the
#: module it opens on import: the PRD verify ship gate died with `FileNotFoundError` there.
_PY_PATH_SIBLING = re.compile(r"""/\s*["']([A-Za-z_][A-Za-z0-9_]*)\.py["']""")


#: What a customer render leaves where a home segment with no `else` text was: a HOLE. It is a
#: control character no authored text carries, so every tidying rule below can be keyed on it
#: and touch only syntax a removal produced — never an empty `()` or a `` `` `` written on purpose.
_HOLE = "\x00"
#: A code span whose whole content was home text. Kept apart from a bare hole because a span is
#: usually the OBJECT of a sentence (`the daemon dispatches ``.`): tidying it away would leave
#: "dispatches ." — still broken, and now invisible — so outside a parenthetical it is put back
#: as a visible empty span for the `command-render` check to refuse.
_SPAN_HOLE = "\x01"
_H = f"[{_HOLE}{_SPAN_HOLE}]"
#: A link whose target was home-only (`[text](<home>../x.md<else>#</home>)`) after the render.
_DEAD_LINK = re.compile(rf"\[([^\]\n]*)\]\({_HOLE}\)")
#: A code span holding nothing but holes.
_EMPTY_SPAN = re.compile(rf"(?<!`)`[ {_HOLE}]*{_HOLE}[ {_HOLE}]*`(?!`)")
#: A parenthetical holding nothing but holes, separators and connectives, with its leading space.
_PAREN_FILL = rf"(?:{_H}|[\s,;/&+·—–-]|\band\b|\bor\b|\be\.g\.)"
_EMPTY_PAREN = re.compile(rf" ?\({_PAREN_FILL}*{_H}{_PAREN_FILL}*\)")
#: A parenthetical (one line, not nested) that still holds a hole once its lists are tidied:
#: the clause lost the thing it was about, so the whole parenthetical goes.
_HOLED_PAREN = re.compile(rf" ?\([^()\n]*{_H}[^()\n]*\)")
_TIDY: tuple[tuple[re.Pattern[str], str], ...] = (
    # `**ENG-1**` -> nothing
    (re.compile(rf"\*\*{_H}+\*\*"), _HOLE),
    # a list of holes collapses to one: `ENG-1 / ENG-2`, `ENG-1, ENG-2`
    (re.compile(rf"{_H}(?:\s*[,/;]\s*{_H})+"), _HOLE),
    # a date range whose start was home text: `2026-08-15→21`, `2026-09-20..09-26`, `…/27`
    (re.compile(rf"({_H})(?:→|\.\.|/)[0-9-]+\b"), r"\1"),
    # a measurement that lost its date keeps the word: `Measured 2026-09-10:` -> `Measured:`
    (re.compile(rf"\b([Mm]easured)(?: on| over| across)? {_HOLE}+(?=[\s:,.;)])"), r"\1"),
    # a citation that led a parenthetical's explanation: `(ENG-9: why)` -> `(why)`
    (re.compile(rf"\(\s*{_H}+\s*(?:[:—–;,]|\s-)\s*"), "("),
    # an item at the start / end / middle of a parenthetical list
    (re.compile(rf"\(\s*{_H}+\s*[,;]\s*"), "("),
    (re.compile(rf"\s*[,;]\s*{_H}+\s*\)"), ")"),
    (re.compile(rf"\s*[—–]\s*{_H}+\s*\)"), ")"),
    (re.compile(rf",\s*{_H}+(?=\s*,)"), ""),
)


def _tidy_holes(text: str) -> str:
    """Remove what a customer render's holes leave behind, and only that.

    Every rule is anchored on a hole, so text no marker produced is never rewritten. What a
    rule cannot settle safely — a hole that is the object of a sentence — is left visible
    (an empty code span, a space before punctuation) for the `command-render` check to fail,
    which is how the source gets an `<!-- else -->` instead of a guess.
    """
    if _HOLE not in text:
        return text
    text = _DEAD_LINK.sub(lambda m: m.group(1) or _HOLE, text)
    text = _EMPTY_SPAN.sub(_SPAN_HOLE, text)
    for _ in range(4):
        before = text
        for pattern, repl in _TIDY:
            text = pattern.sub(repl, text)
        text = _EMPTY_PAREN.sub("", text)
        if text == before:
            break
    text = _HOLED_PAREN.sub("", text)
    # A title or a word that lost its neighbour keeps one space, not two.
    text = re.sub(rf"^(#+ ){_H}+ +", r"\1", text, flags=re.M)
    text = re.sub(rf"(?<=\S) {_HOLE}+ (?=\S)", " ", text)
    text = re.sub(rf"(?<=\S) {_HOLE}+$", "", text, flags=re.M)
    text = text.replace(_SPAN_HOLE, "``")
    return text.replace(_HOLE, "")


def _render_home(text: str, rel: Path, *, home: bool, src: Path | None = None, namespace: str = "") -> str:
    """Resolve the home-only markers: keep the home text (home render) or the `else` part.

    `home` is True for the identity render. Nested or unbalanced markers are refused by name
    rather than silently dropped — a marker that renders to nothing is a passage that vanished
    from one repository's copy with nothing to explain it.

    A customer render resolves a segment with no `else` (or an `else` of `#`, the dead-link
    spelling) to a hole and then tidies the syntax the hole left (`_tidy_holes`): an empty
    `()`, a dangling list separator, a title's second space, a link pointing at `#`. A link
    whose home target is a `tier: core` command keeps resolving instead — every customer
    install receives that file, at the same relative path.
    """
    if HOME_OPEN not in text and HOME_ELSE not in text and HOME_CLOSE not in text:
        return text

    if rel.suffix != ".md":
        # A script marks whole lines, each marker alone on a comment line: the marker line
        # (and the blank lines above it) goes with the marker, so neither render leaves a
        # stray `#` or a run of blank lines a formatter would refuse.
        text = _SCRIPT_MARKER_LINE.sub(r"\1", text)
    if not home and src is not None:
        text = _HOME_LINK.sub(lambda m: _core_link(m, src, rel), text)

    def pick(m: re.Match[str]) -> str:
        if home:
            return (m.group(1) or "") + _SEAM
        alt = m.group(2)
        return (_HOLE if alt is None or alt.strip() in ("", "#") else alt) + _SEAM

    rendered = _HOME.sub(pick, text)
    for marker in _MARKER_LEFTOVER:
        if marker in rendered:
            raise ValueError(f"{rel}: unbalanced or nested home markers near {marker!r}")
    # A segment that closes a line takes the whitespace before its seam with it: `ENG-1517,
    # <!-- /home -->` (home) and `) <!-- home -->…<!-- /home -->` (customer) otherwise both end
    # their line in a space every receiving repository's trailing-whitespace hook refuses.
    rendered = _SEAM_TRAILING_WS.sub("", rendered).replace(_SEAM, "")
    if home:
        return rendered
    # Tidying reads markdown syntax; in a shipped script a parenthesis is a call, so a hole
    # there is simply removed (a script marks whole lines, in comments, never a clause).
    return _tidy_holes(rendered) if rel.suffix == ".md" else rendered.replace(_HOLE, "")


#: Where a resolved home segment ended, kept only until trailing whitespace is settled: a
#: control character no authored text carries, like `_HOLE`.
_SEAM = "\x02"
#: Whitespace a resolved segment left at the end of its line: before the seam, with at most
#: holes (and further seams) between it and the newline.
_SEAM_TRAILING_WS = re.compile(r"[ \t]+(?=[\x00\x01]*\x02[\x00\x01\x02]*(?:\n|\Z))")


_SCRIPT_MARKER_LINE = re.compile(
    rf"(?:^[ \t]*\n)*^[ \t]*#[ \t]*({re.escape(HOME_OPEN)}|{re.escape(HOME_ELSE)}|{re.escape(HOME_CLOSE)})[ \t]*\n",
    re.M,
)
#: `[text](<!-- home -->path<!-- else -->#<!-- /home -->)` — a link whose target is home-only.
_HOME_LINK = re.compile(rf"\]\({re.escape(HOME_OPEN)}([^\s()<>]+){re.escape(HOME_ELSE)}#{re.escape(HOME_CLOSE)}\)")


def _core_link(m: re.Match[str], src: Path, rel: Path) -> str:
    """Keep a home-only link target that names a `tier: core` command, else leave it dead.

    Only a link FROM a command: the path between two files under `commands/<namespace>/` is
    the same in every layout and every namespace, and every customer install receives a core
    command. The target is resolved inside the tier, so `../bug/fix.md` and the
    `../../.claude/commands/<ns>/bug/fix.md` spelling resolve alike.
    """
    if rel.parts[0] != COMMANDS_SUBDIR:
        return m.group(0)
    path = m.group(1).split("#", 1)[0]
    tiered = re.sub(r"^(?:\.\./)*\.claude/", "", posixpath.normpath(posixpath.join(rel.parent.as_posix(), path)))
    source = source_namespace(src)
    inside = tiered.removeprefix(f"{COMMANDS_SUBDIR}/")
    if not source or not inside.startswith(f"{source}/") or not (src / tiered).is_file():
        return m.group(0)
    if commandmod.tiers(src / COMMANDS_SUBDIR).get(inside) != "core":
        return m.group(0)
    return "](" + posixpath.relpath(tiered, rel.parent.as_posix()) + ")"


def source_namespace(src: Path | None = None) -> str:
    """The namespace the tree's own commands are authored under.

    Read from the single subdirectory of `commandtree/commands/` rather than written as a
    constant, for the same reason `commands.namespace_of` reads the basename: the directory IS
    the namespace, and a constant here would be right in the repository it was written for and
    silently wrong in the next. `""` when the tree has no command directory or more than one.
    """
    base = (src or source_root()) / COMMANDS_SUBDIR
    dirs = sorted(p.name for p in base.iterdir() if p.is_dir()) if base.is_dir() else []
    return dirs[0] if len(dirs) == 1 else ""


def _command_verbs(src: Path) -> tuple[str, ...]:
    """Every command id the tree contains, longest first, for a foreign render's substitution.

    The id is the path below `commands/<source-namespace>/` as a person types it — `bug:fix`,
    `prd:create` — deliberately WITHOUT the namespace, because a foreign render rewrites the
    namespace and keeps the verb. Longest first so `/home:prd:create` cannot match as the
    prefix `/home:prd`.
    """
    source = source_namespace(src)
    base = src / COMMANDS_SUBDIR
    verbs: set[str] = set()
    if base.is_dir():
        for path in base.rglob("*.md"):
            parts = path.relative_to(base).with_suffix("").parts
            if len(parts) >= 2 and parts[0] == source:
                verbs.add(":".join(parts[1:]))
    return tuple(sorted(verbs, key=len, reverse=True))


def _rewrite_namespace(text: str, verbs: tuple[str, ...], source: str, target: str) -> str:
    """`/<source>:<known verb>` -> `/<target>:<known verb>`; an unknown id is left alone.

    The bare prefix a sentence uses to mean "any command" — `/<source>:*`, `/<source>:<command>`,
    `/<source>:…` — is the namespace itself, not an id, and is rewritten too.
    """
    if not verbs or not source:
        return text
    alt = "|".join(re.escape(v) for v in verbs)
    pattern = re.compile(rf"/{re.escape(source)}:({alt})(?![A-Za-z0-9_:-])")
    text = pattern.sub(lambda m: f"/{target}:{m.group(1)}", text)
    return re.sub(rf"/{re.escape(source)}:(?=[*<…`\s]|$)", f"/{target}:", text, flags=re.M)


def render(
    src: Path,
    rel: Path,
    *,
    namespace: str = "",
    layout: str = DEFAULT_LAYOUT,
    targets: Mapping[str, str] | None = None,
) -> bytes:
    """The bytes `rel` materializes as: includes expanded, markers resolved, namespace rewritten,
    every conventional-target token replaced by this repository's command.

    Byte-identical to the source when `namespace` is unset and the file carries no include and
    no home marker, so a repository that declares no namespace cannot change under a version
    bump of this function. ANY declared `namespace` is a customer render — the source's own
    included, since that is the customer default (`CUSTOMER_NAMESPACE`) — and keeps each home
    segment's `else` text; a namespace other than the source's also rewrites every known
    command reference. Home-ness is decided by WHETHER a namespace is declared, never by which:
    keying it on the name handed the home project's issue keys and incidents to every customer
    that chose the default. The `plugin` layout rewrites
    every tier path named in a document (`_TIER_PATH`) to its `.fleet/` home; a shipped script is
    never rewritten — it finds the tier itself, in either layout (`_repo.py`).

    `targets` is the repository's `[fleet.targets]` table (`commands_targets`). EVERY render
    substitutes the tokens — the home copy as much as a customer's — so the procedure an agent
    reads names what runs in that repository, and a target it has not configured reads as a
    refusal (`targets.render_text`). A shipped script carries no token and is never rewritten.
    """
    raw = (src / rel).read_bytes()
    source = source_namespace(src)
    customer = bool(namespace)
    foreign = customer and namespace != source
    has_include = b"<!-- include: " in raw
    # Decided on the RENDERED text, not the raw: an include can bring a tier path in.
    relocate = layout == "plugin" and rel.parts[0] != SCRIPTS_SUBDIR
    tokens = rel.parts[0] != SCRIPTS_SUBDIR and targetsmod.TOKEN_OPEN.encode() in raw
    plain = not has_include and not tokens and not (relocate and b".claude/" in raw)
    if not customer and plain and not any(m.encode() in raw for m in _MARKER_LEFTOVER):
        return raw

    text = raw.decode("utf-8")
    if has_include:
        text = render_includes(src, rel, text)
    text = _render_home(text, rel, home=not customer, src=src)
    if foreign:
        text = _rewrite_namespace(text, _command_verbs(src), source, namespace)
    if rel.parts[0] != SCRIPTS_SUBDIR:
        # After the includes and the home markers: either can bring a token in.
        text = targetsmod.render_text(text, targets, where=str(rel))
    if relocate:
        text = _TIER_PATH.sub(lambda m: f"{PLUGIN_DIR}/{m.group(1)}", text)
    return text.encode("utf-8")


def render_file(
    src: Path,
    rel: Path,
    *,
    namespace: str = "",
    layout: str = DEFAULT_LAYOUT,
    targets: Mapping[str, str] | None = None,
) -> bytes:
    """The bytes the sync writes for `rel`: `render`, plus a plugin command's `description:` frontmatter.

    In the plugin layout a command file is a Claude Code plugin command, which the model's Skill
    listing shows only when the file carries a `description:` frontmatter field. Kept out of
    `render` so that stays a pure text transform; this is the one function that writes files.
    """
    out = render(src, rel, namespace=namespace, layout=layout, targets=targets)
    if layout == "plugin" and rel.parts[0] == COMMANDS_SUBDIR and rel.suffix == ".md":
        text = out.decode("utf-8")
        if not _has_description(text):
            out = (command_frontmatter(rel, text) + text).encode("utf-8")
    return out


def _has_description(text: str) -> bool:
    """Whether `text` already opens with a frontmatter block carrying `description:` (a rendered file re-read)."""
    if not text.startswith("---\n"):
        return False
    end = text.find("\n---\n", 3)
    return end != -1 and any(line.startswith("description:") for line in text[4:end].splitlines())


def command_description(rel: Path, text: str) -> str:
    """A command's `description` for the plugin listing: its spine's `intent`, whitespace-folded.

    Raises `ValueError` when the command has no spine or an empty intent. This is the ratchet:
    a command that rendered without a description would be invocable by exact name yet absent
    from the model's Skill listing, so agents conclude it does not exist. No command is exempt.
    """
    spine = commandmod._spine(text)
    intent = " ".join(str(spine.get("intent", "")).split()) if spine else ""
    if not intent:
        raise ValueError(
            f"{rel}: the command has no spine `intent`, so it would render without a `description:` "
            "and be invisible in the Skill listing; add a non-empty `intent` to its spine"
        )
    return intent


def command_frontmatter(rel: Path, text: str) -> str:
    """The YAML frontmatter block (`---` / `description: "<intent>"` / `---`) a plugin command opens with.

    A JSON string is a valid YAML double-quoted scalar, so the intent is quoted by `json.dumps`.
    """
    return f"---\ndescription: {json.dumps(command_description(rel, text), ensure_ascii=False)}\n---\n"


def _block_end(lines: Sequence[str], start: int) -> int | None:
    """The index just past the block the marker at `start` already carries, or `None` for a bare
    marker. Balanced: each open marker inside counts up and each close counts down, so a nested
    block's close is never taken for its parent's. A marker no close balances is bare."""
    depth = 1
    for i in range(start + 1, len(lines)):
        if _INCLUDE_LINE.match(lines[i]):
            depth += 1
        elif lines[i] == INCLUDE_CLOSE + "\n":
            depth -= 1
            if depth == 0:
                return i + 1
    return None


def render_includes(src: Path, rel: Path, text: str, *, _within: tuple[str, ...] = ()) -> str:
    """Expand every include marker in `text` (the body of `rel`), nested includes too, loudly."""

    def expand(name: str) -> str:
        target = src / name
        if not target.is_file():
            # Loud, not silent: a marker that renders to nothing would ship a command with a
            # hole exactly where the text it was written for belongs.
            raise FileNotFoundError(f"{rel}: include target {name!r} is not in the tier ({target})")
        if name in _within or Path(name) == rel:
            raise ValueError(f"{rel}: include cycle through {name!r} ({' -> '.join((*_within, name))})")
        body = target.read_text(encoding="utf-8").strip("\n")
        if "<!-- include: " in body:
            body = render_includes(src, Path(name), body + "\n", _within=(*_within, name)).strip("\n")
        return f"{include_open(name)}\n{body}\n{INCLUDE_CLOSE}\n"

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        m = _INCLUDE_LINE.match(lines[i])
        if m is None:
            out.append(lines[i])
            i += 1
            continue
        out.append(expand(m.group(1)))
        end = _block_end(lines, i)
        i = end if end is not None else i + 1
    return "".join(out)


#: Which tier directory holds the commands, so scope filtering knows where to look.
COMMANDS_SUBDIR = "commands"


def repo_name(repo: Path) -> str:
    """What this repository is CALLED, for the purpose of owning a product command.

    Taken from origin's URL rather than the directory name, because the directory name is
    an accident of how somebody cloned: a worktree, a numbered second checkout, a CI
    runner's scratch path. A product command keyed off that would ship into some checkouts
    of its owner and not others — the same procedure present or absent depending on a path,
    which is the least debuggable form of "why is this command missing".

    Falls back to the directory name when there is no remote, which is the honest answer for
    a tree that is not a clone of anything.
    """
    try:
        done = subprocess.run(  # noqa: S603 — fixed argv, no interpolation
            ["git", "-C", str(repo), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return repo.name
    url = done.stdout.strip()
    if done.returncode != 0 or not url:
        return repo.name
    return url.rstrip("/").removesuffix(".git").replace(":", "/").rsplit("/", 1)[-1] or repo.name


def declared_commands_config(repo: Path) -> tuple[str | None, str | None]:
    """`(namespace, set)` exactly as the repository's `[fleet.commands]` declares them.

    `None` for a value the repository leaves out — which is NOT the same as a declared default.
    `commands_config` fills those defaults for a sync; a caller that carries its own value for
    the gap (`fleet init --namespace`, whose kept file may predate the namespace) needs the
    difference, or it cannot tell "the repository chose the default" from "nobody chose".
    """
    located = configmod.find_config_file(repo)
    if located is None:
        return (None, None)
    _, table = located
    raw = table.get("commands")
    section = raw if isinstance(raw, dict) else {}
    namespace = str(section.get("namespace") or "") or None
    if namespace is not None and not NAMESPACE_RE.fullmatch(namespace):
        raise configmod.ConfigError(
            f"{located[0]}: `[fleet.commands] namespace = {namespace!r}` is invalid — a "
            "namespace is `[a-z][a-z0-9-]{1,30}` (lower-case, two characters or more)"
        )
    set_name = str(section.get("set") or "") or None
    if set_name is not None and set_name not in SETS:
        raise configmod.ConfigError(
            f"{located[0]}: `[fleet.commands] set = {set_name!r}` is not one of {', '.join(SETS)}"
        )
    return (namespace, set_name)


def commands_config(repo: Path) -> tuple[str, str]:
    """`(namespace, set)` from the repository's own `[fleet.commands]`.

    `("", "all")` when the repository declares neither, which is the identity (home) render. A
    declared namespace is a customer render, so an undeclared set defaults to `core` there — the
    generic work loop — never to the depth commands that still carry home ids (ENG-21056). A
    declared namespace is returned as declared, the source's own included: declaring it is a
    customer choosing the default prefix, not a claim to be the home (`render`).
    """
    namespace, set_name = declared_commands_config(repo)
    # A customer render (a declared namespace) defaults to the generic core loop; only the home
    # render keeps the depth set. `set = "all"` remains an explicit choice (ENG-21056).
    return (namespace or "", set_name or ("core" if namespace else "all"))


def commands_targets(repo: Path) -> dict[str, str]:
    """The repository's `[fleet.targets]` table, checked (`targets.read_table`); `{}` for none.

    `{}` is not a degraded answer the render papers over: every target then renders as its
    refusal, `validate-knowledge` aside, and `fleet check` names the missing table
    (`fleet-layout`)."""
    located = configmod.find_config_file(repo)
    if located is None:
        return {}
    raw = located[1].get("targets")
    if raw is None:
        return {}
    try:
        return targetsmod.read_table(raw, located[0])
    except targetsmod.TargetError as exc:
        raise configmod.ConfigError(str(exc)) from exc


def commands_layout(repo: Path) -> str:
    """`[fleet.commands] layout`: `"plugin"` (`.fleet/`), the only layout, and the default.

    `"claude"` is the retired `.claude/` home and is refused by name with the way out: delete the
    line, and the next sync moves the tier and deletes the old copy. Anything else is refused as
    unknown."""
    located = configmod.find_config_file(repo)
    if located is None:
        return DEFAULT_LAYOUT
    raw = located[1].get("commands")
    layout = str((raw if isinstance(raw, dict) else {}).get("layout") or DEFAULT_LAYOUT)
    if layout in RETIRED_LAYOUTS:
        raise configmod.ConfigError(
            f"{located[0]}: `[fleet.commands] layout = {layout!r}` is retired — the tier lives in "
            f"`{PLUGIN_DIR}/` as a Claude Code plugin. Delete the line (or set `layout = "
            f'"{DEFAULT_LAYOUT}"`); the next `fleet commands sync` moves the tier and deletes the '
            f"`{CLAUDE_DIR}/` copy. See docs/command-tier.md."
        )
    if layout not in LAYOUTS:
        raise configmod.ConfigError(
            f"{located[0]}: `[fleet.commands] layout = {layout!r}` is not a layout — the only one is {DEFAULT_LAYOUT!r}"
        )
    return layout


def render_plugin_manifest(*, namespace: str = "", src: Path | None = None) -> bytes:
    """`.fleet/.claude-plugin/plugin.json`: the plugin is named for the namespace, so a command is
    `/<namespace>:<verb>` exactly as under `.claude/commands/<namespace>/`, and `commands` points
    into that directory so the tree keeps the shape every relative link in it was written for."""
    target = namespace or source_namespace(src)
    doc = {
        "name": target,
        "description": "The fleet command tier for this repository, written by `fleet commands sync`.",
        "commands": f"./{COMMANDS_SUBDIR}/{target}",
    }
    return (json.dumps(doc, indent=2) + "\n").encode("utf-8")


def render_marketplace(*, namespace: str = "", src: Path | None = None) -> bytes:
    """`.fleet/.claude-plugin/marketplace.json`: one plugin, the tier itself (`source: "./"`)."""
    target = namespace or source_namespace(src)
    doc = {
        "name": MARKETPLACE_NAME,
        "owner": {"name": "fleet"},
        "plugins": [{"name": target, "source": "./"}],
    }
    return (json.dumps(doc, indent=2) + "\n").encode("utf-8")


def optin_settings(namespace: str) -> dict[str, object]:
    """The settings that load the tier into an interactive session: merge into `.claude/settings.json`
    to give a whole team the commands, or `.claude/settings.local.json` for one person."""
    return {
        "extraKnownMarketplaces": {MARKETPLACE_NAME: {"source": {"source": "directory", "path": f"./{PLUGIN_DIR}"}}},
        "enabledPlugins": {f"{namespace}@{MARKETPLACE_NAME}": True},
    }


#: The plugin layout's rendered files that are not tier documents: `{report name: (repo path, render)}`.
_PLUGIN_FILES = {
    PLUGIN_MANIFEST_SOURCE: (PLUGIN_MANIFEST_REL, render_plugin_manifest),
    MARKETPLACE_SOURCE: (MARKETPLACE_REL, render_marketplace),
    INSTRUCTIONS_SOURCE: (INSTRUCTIONS_REL, render_instructions),
    HOOKS_SOURCE: (HOOKS_REL, render_hooks),
    PR_FRESHNESS_SOURCE: (PR_FRESHNESS_REL, render_pr_freshness),
}


def core_commands(src: Path | None = None) -> tuple[str, ...]:
    """The `tier: core` command files, as tier-relative paths (`commands/<ns>/…`).

    The membership half of the core closure, exposed so a caller that needs only WHICH
    commands are core — `slots.required_for` enumerating the slots they require, the
    `command-render` check — does not re-derive it from the spine and drift. `_core_closure`
    is the other half: what those commands drag in.
    """
    tree = (src or source_root()) / COMMANDS_SUBDIR
    tiers = commandmod.tiers(tree)
    return tuple(sorted(f"{COMMANDS_SUBDIR}/{rel}" for rel, tier in tiers.items() if tier == "core"))


def _core_closure(src: Path) -> tuple[set[str], set[str]]:
    """The shared documents and scripts the `tier: core` commands need, tier-relative.

    Closed under include targets, links into `process/`/`registers/`/`rubrics/`, the scripts a
    command runs, and the sibling scripts those scripts import — so a `set = "core"` repository
    receives a command and everything it would otherwise name and not find.

    **The WHOLE shared tier ships** (`process/`, `registers/`, `rubrics/`), not only the
    documents a core command happens to link. The shared slots in the questionnaire — several
    of them mandatory — fill from these documents, and a repository that answered all its own
    repo-tier questions would still read a broken shared tier (a `slots` error naming a
    document that "ships WITH the command tree") if the set dropped them. The shared tier is
    the vocabulary, not depth; `set = "core"` narrows the COMMANDS, never the interface they
    are documented against. Home-only *commands* and their run scripts are still dropped.
    """
    base = src / COMMANDS_SUBDIR
    tiers = commandmod.tiers(base)
    core_rels = [rel for rel, tier in tiers.items() if tier == "core"]
    shared: set[str] = set()
    scripts: set[str] = set()
    todo = [(src / COMMANDS_SUBDIR / rel) for rel in sorted(core_rels)]
    seen: set[Path] = set(todo)

    while todo:
        path = todo.pop()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in _INCLUDE.finditer(text):
            name = m.group(1) or m.group(2)
            target = src / name
            if target.is_file() and target not in seen:
                seen.add(target)
                shared.add(name)
                todo.append(target)
        for m in _SHARED_LINK.finditer(text):
            name = f"{m.group(1)}/{m.group(2)}"
            target = src / name
            if target.is_file() and target not in seen:
                seen.add(target)
                shared.add(name)
                todo.append(target)
        for m in _SCRIPT_REF.finditer(text):
            scripts.add(str(Path(SCRIPTS_SUBDIR) / Path(m.group(1)).name))

    # A script imports its siblings by bare module name, or loads them by path; carry those too.
    scripts_dir = src / SCRIPTS_SUBDIR
    frontier = list(scripts)
    while frontier:
        name = frontier.pop()
        spath = scripts_dir / Path(name).name
        if not spath.is_file():
            continue
        body = spath.read_text(encoding="utf-8", errors="ignore")
        for m in (*_PY_IMPORT.finditer(body), *_PY_PATH_SIBLING.finditer(body)):
            sibling = f"{SCRIPTS_SUBDIR}/{m.group(1)}.py"
            if (src / sibling).is_file() and sibling not in scripts:
                scripts.add(sibling)
                frontier.append(sibling)

    # The WHOLE shared tier, added after the link/script walk so it widens the documents a
    # `set = "core"` repository receives without dragging in scripts only the home-only depth
    # documents name (the walk above stops at the closure). See the docstring.
    for d in ("process", "registers", "rubrics"):
        d_dir = src / d
        if not d_dir.is_dir():
            continue
        for path in sorted(d_dir.rglob("*.md")):
            shared.add(path.relative_to(src).as_posix())
    return shared, scripts


def _shipped_for(src: Path, *, namespace: str, set_name: str, name: str) -> set[str]:
    """The packaged files this repository is entitled to, tier-relative.

    Everything, minus the product commands another repository owns, and minus — when the
    repository declares `[fleet.commands] set = "core"` — the home-only depth commands and
    the shared documents and scripts the core closure never names. A product command is a
    procedure ABOUT one product; writing it everywhere put an 880-line connector-SDK manual
    into five repositories that cannot run a line of it, where the agent reading `.claude/`
    had no way to tell it was inapplicable. See `spine.md` -> Scope.

    The namespace, set and repository name are taken as arguments rather than read here, because
    `render_tree` decides the same thing for a repository that is not on disk (the setup pull
    request is built from a bare tree) and `fleet init` may fill a value the kept config leaves
    out — one place decides what a `set = "core"` repository receives.
    """
    del namespace  # filter for the closure and product scope only; the namespace is a render arg
    core_shared: set[str] = set()
    core_scripts: set[str] = set()
    if set_name == "core":
        core_shared, core_scripts = _core_closure(src)
    out: set[str] = set()
    for d in SYNC_DIRS:
        s_dir = src / d
        if not s_dir.is_dir():
            continue
        if d == COMMANDS_SUBDIR:
            tiers = commandmod.tiers(s_dir)
            scoped = commandmod.scopes(s_dir)
            for rel in _files(s_dir):
                scope, owner = scoped.get(str(rel), ("portable", ""))
                if scope == "product" and owner != name:
                    continue
                if set_name == "core" and tiers.get(str(rel), "") != "core":
                    continue
                out.add(str(Path(d) / rel))
            continue
        wanted = core_shared if d != SCRIPTS_SUBDIR else core_scripts
        for rel in _files(s_dir):
            key = str(Path(d) / rel)
            if set_name == "core" and key not in wanted:
                continue
            out.add(key)
    return out


def shipped_verbs(set_name: str = "all", *, src: Path | None = None, name: str = "") -> frozenset[str]:
    """The commands a repository on `set_name` receives, as a person types them minus the prefix.

    `bug:fix`, `prd:create`, `ask` — the path below `commands/<source-namespace>/`, `:`-joined.
    Read off `_shipped_for`, the one decision about what a set carries, so a list that names
    commands (the rules block's orientation) can never offer one the repository was not given.
    `name` is the repository's own name, which decides the product commands it owns.
    """
    tree = src or source_root()
    prefix = f"{COMMANDS_SUBDIR}/{source_namespace(tree)}/"
    out: set[str] = set()
    for key in _shipped_for(tree, namespace="", set_name=set_name, name=name):
        if key.startswith(prefix) and key.endswith(".md"):
            out.add(key[len(prefix) : -len(".md")].replace("/", ":"))
    return frozenset(out)


def render_tree(
    *,
    namespace: str = "",
    set_name: str = "all",
    src: Path | None = None,
    name: str = "",
    layout: str = DEFAULT_LAYOUT,
    targets: Mapping[str, str] | None = None,
) -> dict[str, bytes]:
    """Every file a sync would write into the repository, as `{repo-relative path: bytes}`.

    The pure twin of `sync`, for a caller with no checkout — the setup pull request builds a
    git tree from the rendered bytes rather than writing them to a disk first. `namespace`
    rewrites the command directory segment exactly as a real sync would, so the files a pull
    request carries are the files `fleet init` would write for the same answers. `targets` is the
    `[fleet.targets]` table the repository will carry (`render`).
    """
    out = _render_files(
        namespace=namespace, set_name=set_name, src=src or source_root(), name=name, layout=layout, targets=targets
    )
    # The manifest is written by the real sync too, so the setup pull request carries the same
    # file `fleet init` leaves on disk — release and hashes included (ENG-18630). Without it the
    # first pin bump after an init would have no record of what was written and could not tell
    # its own stale output from a hand-added file, nor a person's edit from an older release.
    out[manifest_rel(layout)] = manifest_record_bytes(out, commands={"namespace": namespace, "set": set_name})
    return out


#: The git mode of an executable file, as a tree entry spells it.
EXECUTABLE_MODE = "100755"


def tree_modes(paths: Iterable[str]) -> dict[str, str]:
    """The git mode `sync` leaves on each of `paths` that is not a plain `100644` file.

    The pure twin of the chmod in `sync`: every shipped script (`knowledge/scripts/<name>.py`) is an
    entry point a commit hook execs, so a sync on disk sets its executable bit. A caller that builds a
    git tree from `render_tree` with no disk in between (the setup pull request) must give those
    entries the same mode, or the first `resync` over the merged tree finds every script "changed" —
    same bytes, `100644` where the sync leaves `100755` — and offers an update to the very release
    that wrote them.
    """
    prefix = f"{SCRIPTS_DEST}/"
    return {
        path: EXECUTABLE_MODE
        for path in paths
        if path.startswith(prefix) and path.endswith(".py") and "/" not in path[len(prefix) :]
    }


def _render_files(
    *,
    namespace: str,
    set_name: str,
    src: Path,
    name: str,
    layout: str,
    targets: Mapping[str, str] | None = None,
    vendor: bool = True,
) -> dict[str, bytes]:
    """`render_tree` without the manifest: the files a sync writes and the manifest describes.

    `vendor` adds the package's own source under `.fleet/_vendor/` (`_vendor_files`).
    A customer checkout receives it; the authors' checkout does not, because the source tree
    the package is edited in is what its scripts should read there.
    """
    out: dict[str, bytes] = {}
    shipped = _shipped_for(src, namespace=namespace, set_name=set_name, name=name)
    for key in shipped:
        rel = Path(key)
        out[str(_target(rel, namespace, layout))] = render_file(
            src, rel, namespace=namespace, layout=layout, targets=targets
        )
    # The vocabulary the board names these commands with (ENG-17173), so the setup pull request
    # carries the same document `fleet init` writes.
    vocabulary = render_vocabulary(src, shipped, namespace=namespace, layout=layout)
    if vocabulary is not None:
        out[vocabulary_rel(layout)] = vocabulary
    if layout == "plugin":
        for rel_path, plugin_file in _PLUGIN_FILES.values():
            out[rel_path] = plugin_file(namespace=namespace, src=src)
        out.update(render_docs(src))
    if vendor:
        out.update(_vendor_files())
    return out


def _vendor_files() -> dict[str, bytes]:
    """The `fleet_knowledge` package's own source, keyed by where it lands in a repository.

    The scripts are shims over this package, so a checkout that receives the scripts and no
    package cannot run them. The command tier therefore carries the package with it, at the
    fixed path `_repo.fleet_knowledge()` reads. Byte-for-byte the source: the same tree a
    `fleet/` submodule carries, so a repository that had one and loses it keeps the same code.

    Bytecode caches and dot-directories are never shipped — they appear the moment a script
    runs or a maintainer runs a checker, and are nobody's source.
    """
    root = Path(__file__).resolve().parent
    out: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if _ignored(rel) or rel.as_posix() in VENDOR_EXCLUDE:
            continue
        out[f"{VENDOR_PACKAGE}/{rel.as_posix()}"] = path.read_bytes()
    return out


def _expected_files(
    src: Path,
    repo: Path,
    name: str | None = None,
    *,
    targets: Mapping[str, str] | None = None,
    namespace: str | None = None,
    set_name: str | None = None,
) -> dict[str, bytes]:
    """What a sync of `repo` leaves in it, manifest aside — the set the manifest records.

    `targets` is the table the repository carries AFTER this sync (`setupfiles.SetupPlan.targets`
    — the run that migrates a repository renders with the table it writes); `None` reads it.
    `namespace` and `set_name` override the repository's own `[fleet.commands]` values where it
    declares none (`fleet init`, whose kept file may predate them); `None` reads the config."""
    configured_namespace, configured_set = commands_config(repo)
    namespace = configured_namespace if namespace is None else namespace
    set_name = configured_set if set_name is None else set_name
    return _render_files(
        namespace=namespace,
        set_name=set_name,
        src=src,
        name=repo_name(repo) if name is None else name,
        layout=commands_layout(repo),
        targets=commands_targets(repo) if targets is None else targets,
        vendor=not _carries_package_source(repo),
    )


def _carries_package_source(repo: Path) -> bool:
    """True when `repo` carries the package's own source tree — the authors' monorepo.

    Only that checkout is denied the vendored copy: its scripts should read the source a
    maintainer edits, not a stale snapshot the sync wrote earlier. Every other repository
    (a plain clone, a customer's CI, a worker without `FLEET_PYTHON`) receives the copy, so
    its scripts run with nothing installed.
    """
    return (repo / "packages" / "fleet-knowledge" / "src" / "fleet_knowledge").is_dir()


def render_vocabulary(
    src: Path, shipped: set[str], *, namespace: str = "", layout: str = DEFAULT_LAYOUT
) -> bytes | None:
    """The board vocabulary for a repository receiving `shipped`, or `None` when the tree has none.

    Two transformations of the packaged document and nothing else (ENG-17173). Every entry that
    names a command the repository does not receive is DROPPED — a `set = "core"` repository has
    no `program:prove`, and a finding handing over a command that is not there is a run button
    that fails, where an absent key is the board's honest "no command". Then the namespace is
    rewritten exactly as `render` rewrites a command's prose, and the catalogue scan is pointed at
    the directory the commands land in, so the board's own cross-check compares like with like.
    """
    path = src / VOCABULARY_SOURCE
    if not path.is_file():
        return None
    source = source_namespace(src)
    target = namespace or source
    lead = f"/{source}:"
    base = f"{COMMANDS_SUBDIR}/{source}/"
    verbs = {
        key.removeprefix(base).removesuffix(".md").replace("/", ":")
        for key in shipped
        if key.startswith(base) and key.endswith(".md")
    }

    def carried(cmd: object) -> bool:
        return isinstance(cmd, str) and cmd.startswith(lead) and cmd.split()[0].removeprefix(lead) in verbs

    def rows(raw: object) -> list[object]:
        listed = raw if isinstance(raw, list) else []
        return [row for row in listed if isinstance(row, list) and row and carried(row[0])]

    doc = json.loads(path.read_text(encoding="utf-8"))
    for key in ("actionCommands", "nextCommand"):
        doc[key] = {k: v for k, v in (doc.get(key) or {}).items() if carried(v)}
    shape: dict[str, dict[str, str]] = {}
    for kind, entry in (doc.get("shape") or {}).items():
        pair = {half: str(entry.get(half, "")) for half in ("fleet", "terminal")}
        pair = {half: cmd if carried(cmd) else "" for half, cmd in pair.items()}
        if any(pair.values()):
            shape[kind] = pair
    doc["shape"] = shape
    doc["catalogue"] = rows(doc.get("catalogue"))
    doc["pipe"] = rows(doc.get("pipe"))
    doc["cmds"] = {view: kept for view, raw in (doc.get("cmds") or {}).items() if (kept := rows(raw))}
    doc["unbuilt"] = [cmd for cmd in (doc.get("unbuilt") or []) if carried(cmd)]
    doc["catalogueScan"] = {
        "dir": f"{tier_root(layout)}/{COMMANDS_SUBDIR}/{target}",
        "prefix": f"/{target}:",
        "sep": ":",
    }
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    if target != source:
        text = _rewrite_namespace(text, _command_verbs(src), source, target)
    return text.encode("utf-8")


def source_root() -> Path:
    """The packaged tier's directory, inside this installed package."""
    return Path(__file__).resolve().parent / "commandtree"


def _is_source_checkout(repo: Path, src: Path | None = None) -> bool:
    """True when `repo` holds the tree this package renders from — the authors' own checkout.

    The home copy (undeclared namespace) is the tree's own version, with its issue keys,
    incidents and corpus paths. Only that checkout may receive it; every other repository that
    declares no namespace renders the customer default instead (ENG-21055). Detection is by
    containment, so it holds however the package is installed: an editable checkout or a
    `PYTHONPATH` run has `src` inside `repo`, while a wheel in site-packages does not.

    The vendored copy a customer checkout receives sits inside `repo` too, but it is not the
    authors' checkout: its scripts must read the customer render, and a sync run from it must
    write the full manifest record. Containment alone would read it as home and render the
    tree's own issue keys into a customer repository.
    """
    source = (src or source_root()).resolve()
    if source.is_relative_to((repo / VENDOR_DEST).resolve()):
        return False
    return source.is_relative_to(repo.resolve())


#: What a walk of a tier directory never counts: the interpreter's own bytecode cache, which
#: appears under `knowledge/scripts/` the moment any shipped script runs, and any dot-directory
#: — a type checker's or test runner's cache, which appears in the SOURCE tree the moment a
#: maintainer runs one there and would otherwise be shipped. Reporting either as drift turned
#: the check red in exactly the step that runs after the validators; a foreign file is a
#: repository's own addition, and a cache is nobody's.
_IGNORED_DIRS = frozenset({"__pycache__"})
_IGNORED_SUFFIXES = (".pyc", ".pyo")


def _ignored(rel: Path) -> bool:
    return (
        rel.name.endswith(_IGNORED_SUFFIXES)
        or not _IGNORED_DIRS.isdisjoint(rel.parts)
        or any(part.startswith(".") for part in rel.parts)
    )


def _files(root: Path) -> Iterator[Path]:
    """Every file under `root`, sorted, as paths relative to it — bytecode caches excluded.

    Sorted so two runs over the same tree produce the same report, and a diff of two reports
    is a diff of the trees rather than of the filesystem's iteration order.
    """
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_file() and not _ignored(rel):
            yield rel


@dataclass
class SyncReport:
    """What a sync did, or what a check found — the same shape either way.

    One type for both so a `--check` run and a real run cannot disagree about what counts as
    a change. A dry run that classified files differently from the run it predicts is a
    report nobody can act on.
    """

    root: Path
    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    #: Present here, carried by the package, but NOT shipped to this repository — a product
    #: command another repo owns. Distinct from `removed` on purpose: `removed` is the
    #: repository's own addition and is only deleted when asked, while this is the tier's own
    #: stale output and `sync` always clears it. Conflating them would either strand a
    #: procedure nobody can run or delete work somebody wrote by hand.
    superseded: list[str] = field(default_factory=list)
    #: Present here, NOT carried by the package any more, and named by the previous sync's own
    #: manifest. The tier's stale output from an earlier version, deleted by `sync` without
    #: `--prune` because the sync is on record as the one that wrote it. The manifest is what
    #: separates this from `removed`, which is the same shape on disk but is the repository's.
    retired: list[str] = field(default_factory=list)
    #: The record of written paths is absent or does not match this package's shipped set. Its
    #: own bool rather than a `added`/`changed` entry, because it is not a tier file: `sync`
    #: rewrites it without a source-side render. A `--check` that ignored it would let the one
    #: file the cleanup depends on go missing from a commit without a word.
    manifest_stale: bool = False
    #: The repository's `fleet.toml` names no `board_guidance`, so the vocabulary this sync writes
    #: is not read by its board (ENG-17173). Advice, not drift: `fleet.toml` is the repository's
    #: own file and the sync never edits it, so the report says the one line to add.
    vocabulary_unclaimed: bool = False
    #: `board_guidance` is there but names a document other than the one this sync writes, so the
    #: board goes on reading that one (ENG-17420): a hand-made vocabulary from before the tier
    #: carried one got no line at all, and kept a board naming yesterday's commands. The value as
    #: `fleet.toml` spells it; `""` when it names the rendered file or nothing. Advice like the
    #: line above, never drift: a repository may keep its own document on purpose.
    vocabulary_elsewhere: str = ""
    #: The repository's command namespace (`""` for the tree's own), so the report can name each
    #: file where it lands rather than where the package keeps it (ENG-17420).
    namespace: str = ""
    #: The command set this render used (`core` or `all`). Recorded in the manifest beside the
    #: namespace, so a later plain sync over an undeclared kept config can repeat it (ENG-21055).
    set_name: str = "all"
    #: The layout this repository is synced to (`commands_layout`), so the report names files
    #: where they land.
    layout: str = DEFAULT_LAYOUT
    #: Repo-relative files of the OLD `.claude/` tier, present in a repository now synced to the
    #: `plugin` layout: everything the previous sync's manifest recorded under `.claude/`, every
    #: path where the old layout would have put a file the package ships, the old vocabulary and
    #: the old manifest itself. `sync` deletes them without `--prune`: a `.claude/commands` copy
    #: of a command shadows the plugin's (the repository copy wins), so leaving one behind would
    #: quietly run yesterday's procedure. A hand-added file under `.claude/` matches none of
    #: these and stays.
    relocated: list[str] = field(default_factory=list)
    #: Repo-relative command files the previous sync wrote under ANOTHER namespace's directory —
    #: a repository whose `[fleet.commands] namespace` changed (`fleet` -> the 2026-10-15
    #: default, `CUSTOMER_NAMESPACE`). `sync` deletes them without `--prune`, like `relocated`:
    #: a second command directory keeps yesterday's procedures runnable beside today's, and a
    #: box names no namespace for a checkout that carries two. Only the manifest's own entries qualify, so a
    #: file a person added under the old directory stays.
    renamed: list[str] = field(default_factory=list)
    unchanged: int = 0
    #: Every file this sync leaves, `{repo-relative path: bytes}`, manifest aside — what the
    #: manifest records. Computed once by the plan so `sync` does not render the tier twice.
    expected: dict[str, bytes] = field(default_factory=dict, repr=False)
    #: Repo-relative tier files this sync overwrites or deletes that a person changed after the
    #: last sync wrote them (their blob id is not the one the manifest recorded, or the record
    #: does not name them). Only a format 2 record can tell; the sync still overwrites them, and
    #: the report says where to keep the change instead (`keep_at`).
    hand_edited: list[str] = field(default_factory=list)
    #: `{path: (unified diff, truncated)}` for the first `textdiff.MAX_DIFF_FILES` of `hand_edited`:
    #: what the sync is about to undo. A diff is `None` for binary content.
    tier_diffs: dict[str, tuple[str | None, bool]] = field(default_factory=dict, repr=False)
    #: Tier paths written from the repository's `.fleet/local/` instead of the release: those the
    #: release ships (`overridden`) and those it does not (`extended`).
    overridden: list[str] = field(default_factory=list)
    extended: list[str] = field(default_factory=list)
    #: Files under `.fleet/local/` that map to no tier path, so the sync uses none of them.
    local_ignored: list[str] = field(default_factory=list)
    #: The setup files beyond the tier (`setupfiles`). In the tree's home copy, whose rules and
    #: settings its authors write by hand, it holds only the configuration's own migration.
    setup: SetupPlan | None = None

    @property
    def in_sync(self) -> bool:
        return not (
            self.added
            or self.changed
            or self.removed
            or self.superseded
            or self.retired
            or self.relocated
            or self.renamed
            or self.manifest_stale
            or (self.setup is not None and not self.setup.in_sync)
        )

    @property
    def total(self) -> int:
        return (
            len(self.added)
            + len(self.changed)
            + len(self.removed)
            + len(self.superseded)
            + len(self.retired)
            + self.unchanged
        )

    def written_path(self, name: str) -> str:
        """A report name (`added`, `removed`, …) as the repo-relative path the file is found at."""
        return self._written(name)

    def _written(self, name: str) -> str:
        """A report name -> the repo-relative path a reader finds the file at.

        The lists above carry SOURCE-tier names because `sync` renders from them; printed as they
        are, a repository whose namespace is not the source tier's read paths under the source's
        namespace, which it does not have (ENG-17420).
        """
        if name == VOCABULARY_SOURCE:
            return vocabulary_rel(self.layout)
        if name in _PLUGIN_FILES:
            return _PLUGIN_FILES[name][0]
        return str(_target(Path(name), self.namespace, self.layout))

    def drift_json(self) -> dict[str, object]:
        """The setup files, the hand-edited tier files and the overrides, as data — the shape
        `resync.Plan.drift_json` also returns, so a page renders a checkout and a hosted plan
        alike. Each diff is capped (`textdiff`); a `null` diff is binary or past the file limit."""
        return {
            "setup": [f.as_json() for f in (self.setup.files if self.setup is not None else [])],
            "tierHandEdited": [
                {
                    "path": path,
                    "change": "replace" if path in self.expected else "delete",
                    "keepAt": keep_at(path),
                    "diff": self.tier_diffs.get(path, (None, False))[0],
                    "diffTruncated": self.tier_diffs.get(path, (None, False))[1],
                }
                for path in self.hand_edited
            ],
            "overrides": [
                {"path": path, "source": keep_at(path), "shipped": path in self.overridden}
                for path in sorted({*self.overridden, *self.extended})
            ],
            "localIgnored": list(self.local_ignored),
            "limits": {"diffBytes": textdiff.MAX_DIFF_BYTES, "diffFiles": textdiff.MAX_DIFF_FILES},
        }

    def _extra_lines(self, *, diffs: bool) -> list[str]:
        """The overrides, the setup files and the hand edits — printed whatever the tier's state."""
        out: list[str] = []
        if self.overridden or self.extended:
            out.append("")
            count = len(self.overridden) + len(self.extended)
            out.append(f"LOCAL  {count} — written from {LOCAL_DIR}/, which the sync never touches")
            out.extend(f"  {p} (overrides the shipped file)" for p in self.overridden)
            out.extend(f"  {p} (your own addition)" for p in self.extended)
        if self.local_ignored:
            out.append("")
            out.append(
                f"LOCAL, UNUSED  {len(self.local_ignored)} — not at a tier path ({', '.join(SYNC_DIRS)}; "
                f"commands under commands/{self.namespace or source_namespace()}/), so the sync uses none of them"
            )
            out.extend(f"  {p}" for p in self.local_ignored)
        if self.hand_edited:
            out.append("")
            out.append(
                f"HAND-EDITED  {len(self.hand_edited)} — changed after the last sync wrote them; the sync "
                f"replaces them. To keep a change, put the whole file at the path shown under {LOCAL_DIR}/"
            )
            for path in self.hand_edited:
                keep = keep_at(path)
                out.append(f"  {path}" + (f"  (keep it at {keep})" if keep else ""))
                text = self.tier_diffs.get(path, (None, False))[0]
                if diffs and text:
                    out.extend(f"    {line}" for line in text.splitlines())
        # What needs a reader: a change, or an edit the sync keeps. A file the sync leaves on purpose
        # (absent with nothing to create, skipped) is in `drift_json`, not repeated on every run.
        entries = [
            f for f in (self.setup.files if self.setup is not None else []) if f.writes or f.state == "hand-edited"
        ]
        if entries:
            out.append("")
            out.append("SETUP FILES  Fleet's part of the files `fleet init` wrote")
            for entry in entries:
                out.append(f"  {entry.state:<11} {entry.path} — {entry.detail}")
                text = entry.diff()[0] if entry.state in ("hand-edited", "will-update") else None
                if diffs and text:
                    out.extend(f"    {line}" for line in text.splitlines())
        return out

    def lines(self, *, diffs: bool = False) -> list[str]:
        """The human report. Says what is missing, stale or foreign, and nothing else.

        `diffs` adds the unified diff of every hand-edited file and every setup file an update
        changes, each capped."""
        vocabulary = vocabulary_rel(self.layout)
        out = [
            f"repo: {self.root}",
            f"tier: {', '.join(SYNC_DIRS)} under {tier_root(self.layout)}/ ({self.total} file(s))",
        ]
        if self.vocabulary_unclaimed:
            out.append("")
            out.append(
                f"VOCABULARY  fleet.toml names no `board_guidance`, so the board names none of these "
                f'commands — add `board_guidance = "{vocabulary}"` to its `[fleet]` table'
            )
        elif self.vocabulary_elsewhere:
            out.append("")
            out.append(
                f"VOCABULARY  fleet.toml's `board_guidance` names `{self.vocabulary_elsewhere}`, not the "
                f"vocabulary this sync writes, so the board reads that file and names only the commands "
                f'it lists — set `board_guidance = "{vocabulary}"` in its `[fleet]` table, unless '
                f"you keep `{self.vocabulary_elsewhere}` up to date yourself"
            )
        if self.in_sync:
            out.extend(self._extra_lines(diffs=diffs))
            out.append("")
            out.append(f"in sync — all {self.unchanged} file(s) match the packaged tier")
            return out
        for label, names in (
            ("MISSING", self.added),
            ("STALE", self.changed),
            ("NOT FOR THIS REPO", self.superseded),
            ("RETIRED", self.retired),
            ("FOREIGN", self.removed),
        ):
            if not names:
                continue
            out.append("")
            out.append(f"{label}  {len(names)}")
            out.extend(f"  {n}" for n in sorted(self._written(n) for n in names))
        if self.relocated:
            out.append("")
            out.append(
                f"OLD LAYOUT  {len(self.relocated)} — the `.claude/` tier, which `sync` deletes now it lives in .fleet/"
            )
            out.extend(f"  {n}" for n in sorted(self.relocated))
        if self.renamed:
            out.append("")
            out.append(
                f"REPLACED  {len(self.renamed)} — files an earlier sync wrote under another namespace or "
                "name, which `sync` deletes now they have a new home"
            )
            out.extend(f"  {n}" for n in sorted(self.renamed))
        if self.manifest_stale:
            out.append("")
            out.append(f"MANIFEST  {manifest_rel(self.layout)} is missing or out of date — `sync` rewrites it")
        out.extend(self._extra_lines(diffs=diffs))
        out.append("")
        out.append(f"{self.unchanged} file(s) already match")
        return out


def _plan(
    repo: Path,
    name: str | None = None,
    *,
    replace: frozenset[str] = frozenset(),
    setup_inputs: Inputs | None = None,
    namespace: str | None = None,
    set_name: str | None = None,
) -> SyncReport:
    """Compare the packaged tier against the repository's, without writing anything.

    FOREIGN files — present in the target's tier directories and absent from the package —
    are reported rather than ignored, because they are the tell for the thing this module
    exists to prevent: a procedure somebody added by hand to one repository, which no other
    repository will ever receive. Naming it is not the same as deleting it; `sync` only
    removes it when asked.

    RETIRED files — present, absent from the package, AND named by the previous sync's own
    manifest — are the sync's stale output rather than the repository's work, so they are
    reported apart and `sync` deletes them without being asked. That distinction is the whole
    reason the manifest exists: a `.py` under `knowledge/scripts/` the package stopped shipping
    looks exactly like a hand-added file, and only the manifest can say which it is.

    A foreign namespace only manages its own command directory: another namespace's commands
    are somebody else's tree and are left unreported, exactly as a foreign file outside the
    tier's own output would be.

    `namespace` and `set_name` fill a value the repository's `[fleet.commands]` leaves out; a
    value it DECLARES always wins (`fleet init` must not rename a repository that already chose).
    """
    src = source_root()
    layout = commands_layout(repo)
    record = read_manifest_record(repo, layout)
    # What the last sync recorded is the durable half of an undeclared configuration: after
    # `fleet init --namespace acme` on a kept `fleet.toml` that declares none, the file is still
    # the person's (reported, never edited — D7 / E28), but the namespace must not revert to the
    # tree's HOME copy on the next plain sync (ENG-21055). A value the file DECLARES still wins,
    # so a person's later choice is always honored.
    recorded_namespace = record.commands.get("namespace") if "namespace" in record.commands else None
    recorded_set = record.commands.get("set") if "set" in record.commands else None
    declared_namespace, declared_set = declared_commands_config(repo)
    defaulted_customer = False
    if declared_namespace is not None:
        namespace = declared_namespace
    elif namespace is not None:
        pass  # an explicit run argument (`fleet init`) wins over the last sync's record
    elif recorded_namespace is not None:
        namespace = str(recorded_namespace)
    elif _is_source_checkout(repo, src):
        namespace = ""
    else:
        # Every other repository gets a customer render, whether or not it carries a kept
        # configuration. An undeclared — or absent — namespace would otherwise render the tree's
        # HOME copy: the authors' issue keys, incidents and corpus paths, because only a declared
        # namespace makes a render a customer's (`render`). The home copy is right ONLY for the
        # tree's own checkout, which the branch above already caught (ENG-21055).
        namespace = CUSTOMER_NAMESPACE
        defaulted_customer = True
    if declared_set is not None:
        set_name = declared_set
    elif set_name is not None:
        pass  # an explicit run argument (`fleet init`) wins
    elif recorded_set is not None and declared_namespace is None:
        # The record is the durable half of an UNDECLARED configuration (ENG-21055). A repository
        # that declares its namespace is answered by its own file: leaving `set` out there means
        # the customer default (ENG-21056), so a stale recorded `all` cannot keep the depth set.
        set_name = str(recorded_set)
    elif defaulted_customer or namespace:
        # The depth commands are home-only and carry home ids; a customer render — declared or
        # defaulted — must not ship them, or CAP-1491 is still broken through `set = "all"`
        # (ENG-21056).
        set_name = "core"
    else:
        set_name = "all"
    report = SyncReport(root=repo, namespace=namespace, set_name=set_name, layout=layout)
    shipped = _shipped_for(src, namespace=namespace, set_name=set_name, name=repo_name(repo) if name is None else name)
    manifest = set(record.files)
    # The setup files FIRST, in every repository (the home copy included): the configuration's
    # move to `.fleet/` and its `[fleet.targets]` table are the sync's in all of them, and the tier
    # below is rendered with the table this run leaves, not the one it found (`SetupPlan.targets`).
    from fleet_knowledge import setupfiles  # noqa: PLC0415 — setupfiles imports this module

    report.setup = setupfiles.plan(
        repo,
        record.setup,
        namespace=namespace,
        replace=replace,
        inputs=setup_inputs,
        skip=_setup_skip(repo),
        set_name=set_name,
    )
    # Rendered ONCE, and every comparison below reads it: the same bytes the manifest then records
    # and `sync` then writes, so the three can never disagree about what the package renders.
    report.expected = _expected_files(
        src, repo, name, targets=report.setup.targets, namespace=namespace, set_name=set_name
    )
    # The repository's overrides replace or extend the render (`LOCAL_DIR`), before any comparison.
    overlay, report.local_ignored = _overlay(repo, namespace, layout)
    report.overridden = sorted(p for p in overlay if p in report.expected)
    report.extended = sorted(p for p in overlay if p not in report.expected)
    report.expected.update(overlay)
    expected = report.expected
    for d in SYNC_DIRS:
        s_dir = src / d
        if not s_dir.is_dir():
            continue
        packaged = {rel for rel in _files(s_dir) if str(Path(d) / rel) in shipped}
        withheld = set(_files(s_dir)) - packaged
        if d == COMMANDS_SUBDIR:
            t_base = repo / dest_dir(d, layout) / (namespace or source_namespace(src))
        else:
            t_base = repo / dest_dir(d, layout)

        base_rel = t_base.relative_to(repo).as_posix()
        local = {Path(p[len(base_rel) + 1 :]) for p in overlay if p.startswith(f"{base_rel}/")}
        present = set(_files(t_base)) if t_base.is_dir() else set()
        if d == SCRIPTS_SUBDIR:
            # The vendored package is planned by `_plan_vendor`, not as a stray file the tier
            # stopped shipping. Without this the scripts walk reads every vendored module as
            # retired output and deletes the package it just wrote.
            present = {rel for rel in present if rel.parts[0] != VENDOR_SUBDIR}
        targets = {_rendered_rel(d, r) for r in packaged}
        # A withheld command the repository overrides is the repository's to keep, not stale output.
        withheld_targets = {_rendered_rel(d, r) for r in withheld} - local
        for trel in sorted(present - targets - withheld_targets - local):
            if _present_rel(d, namespace, trel, src, layout) in manifest:
                report.retired.append(_report_name(d, trel))
            else:
                report.removed.append(_report_name(d, trel))
        for trel in sorted(withheld_targets & present):
            report.superseded.append(_report_name(d, trel))
        for rel in sorted(packaged):
            key = str(Path(d) / rel)
            trel = _rendered_rel(d, rel)
            if trel not in present:
                report.added.append(key)
            # Compare CONTENT, never (size, mtime). A checkout writes fresh mtimes on every
            # file, so a shallow compare calls an identical tree stale on a cold clone and an
            # edited file fresh whenever an editor preserves the timestamp. And the content
            # compared is the RENDERED source: a hand-edit inside an included block is drift
            # like any other, and a source whose include changed marks every file carrying it.
            elif expected[str(_target(Path(d) / rel, namespace, layout))] != (t_base / trel).read_bytes():
                report.changed.append(key)
            else:
                report.unchanged += 1
        # The repository's own additions from `LOCAL_DIR`: compared like a shipped file.
        for trel in sorted(local - targets):
            key = _report_name(d, trel)
            if trel not in present:
                report.added.append(key)
            elif expected[f"{base_rel}/{trel.as_posix()}"] != (t_base / trel).read_bytes():
                report.changed.append(key)
            else:
                report.unchanged += 1
    # The board vocabulary (ENG-17173): one rendered file, compared like any tier file.
    vocabulary = expected.get(vocabulary_rel(layout))
    if vocabulary is not None:
        on_disk = repo / vocabulary_rel(layout)
        if not on_disk.is_file():
            report.added.append(VOCABULARY_SOURCE)
        elif on_disk.read_bytes() != vocabulary:
            report.changed.append(VOCABULARY_SOURCE)
        else:
            report.unchanged += 1
        report.vocabulary_unclaimed = _names_no_vocabulary(repo)
        report.vocabulary_elsewhere = _names_another_vocabulary(repo)
    # The record is part of the contract, not an implementation detail `verify` can skip: a
    # `--check` that passed without it would let the file the cleanup reads go uncommitted,
    # and the next pin bump would silently leave the stale scripts it was meant to remove.
    if layout == "plugin":
        for plugin_name, (rel_path, _render_file) in _PLUGIN_FILES.items():
            on_disk = repo / rel_path
            if not on_disk.is_file():
                report.added.append(plugin_name)
            elif on_disk.read_bytes() != expected[rel_path]:
                report.changed.append(plugin_name)
            else:
                report.unchanged += 1
        _plan_docs(report, repo, expected, set(record.files))
        report.relocated = _old_layout_files(src, repo, namespace, shipped)
    report.renamed = _old_namespace_files(src, repo, namespace, layout)
    _plan_vendor(report, repo, expected, set(record.files))
    _find_hand_edits(report, repo, record)
    report.manifest_stale = manifest_stale(record, expected, report.setup.record if report.setup is not None else None)
    return report


def _plan_vendor(report: SyncReport, repo: Path, expected: Mapping[str, bytes], manifest: set[str]) -> None:
    """`.fleet/_vendor/` against the package source, classified like a tier directory.

    The vendored package is written and checked as one unit: a file the package stopped carrying
    is retired (or, when no sync recorded it, left as the repository's own addition), and a
    hand-edited copy is restored, exactly as a shipped script is.
    """
    prefix = f"{VENDOR_DEST}/"
    shipped = {path for path in expected if path.startswith(prefix)}
    for path in sorted(shipped):
        on_disk = repo / path
        if not on_disk.is_file():
            report.added.append(path)
        elif on_disk.read_bytes() != expected[path]:
            report.changed.append(path)
        else:
            report.unchanged += 1
    base = repo / VENDOR_DEST
    present = {f"{prefix}{rel.as_posix()}" for rel in _files(base)} if base.is_dir() else set()
    for path in sorted(present - shipped):
        (report.retired if path in manifest else report.removed).append(path)


def _plan_docs(report: SyncReport, repo: Path, expected: Mapping[str, bytes], manifest: set[str]) -> None:
    """`.fleet/docs/` against the packaged docs (`DOCS_REL`), classified exactly as a tier directory is.

    Report names are `docs/<page path>`, which `_target` maps back to `.fleet/docs/<page path>` for
    the write and the delete, so every list below needs no case of its own downstream.
    """
    base = repo / DOCS_REL
    present = {f"{DOCS_REL}/{rel.as_posix()}" for rel in _files(base)} if base.is_dir() else set()
    shipped = {path for path in expected if path.startswith(f"{DOCS_REL}/")}
    for path in sorted(shipped):
        name = f"{DOCS_SUBDIR}/{path[len(DOCS_REL) + 1 :]}"
        if path not in present:
            report.added.append(name)
        elif (repo / path).read_bytes() != expected[path]:
            report.changed.append(name)
        else:
            report.unchanged += 1
    for path in sorted(present - shipped):
        name = f"{DOCS_SUBDIR}/{path[len(DOCS_REL) + 1 :]}"
        (report.retired if path in manifest else report.removed).append(name)


def _find_hand_edits(report: SyncReport, repo: Path, record: ManifestRecord) -> None:
    """Fill `report.hand_edited` and `report.tier_diffs` from the files this sync replaces or deletes.

    A file is a person's edit when the last sync's record (format 2 only — a paths-only record
    cannot tell) names a different blob id for it, or does not name it at all. The diff is taken
    now, while the edit is still on disk to be read.
    """
    if record.format < MANIFEST_FORMAT:
        return
    touched = {report.written_path(n) for n in report.changed}
    touched |= {str(_target(Path(n), report.namespace, report.layout)) for n in (*report.superseded, *report.retired)}
    for path in sorted(touched):
        disk = repo / path
        if disk.is_file() and record.files.get(path) != blob_sha(disk.read_bytes()):
            report.hand_edited.append(path)
    for path in report.hand_edited[: textdiff.MAX_DIFF_FILES]:
        report.tier_diffs[path] = textdiff.unified_diff(path, (repo / path).read_bytes(), report.expected.get(path))


def _setup_skip(repo: Path) -> frozenset[str]:
    """`[fleet.setup] skip`: the setup files the repository keeps out of the sync's hands."""
    located = configmod.find_config_file(repo)
    raw = located[1].get("setup") if located is not None else None
    skip = raw.get("skip") if isinstance(raw, Mapping) else None
    return frozenset(str(s) for s in skip) if isinstance(skip, list) else frozenset()


def _old_layout_files(src: Path, repo: Path, namespace: str, shipped: set[str]) -> list[str]:
    """The `.claude/` tier still on disk in a repository synced to `.fleet/` (`SyncReport.relocated`).

    Three sources, because a repository may predate the manifest: what the old manifest
    recorded, where the old layout puts each file the package ships today, and the old
    vocabulary and manifest themselves. Only paths under `.claude/` — the scripts land at the
    same `knowledge/scripts/` in both layouts and are never the old tree's.
    """
    candidates = set(read_manifest(repo, "claude"))
    candidates |= {str(_target(Path(name), namespace, "claude")) for name in shipped}
    candidates |= {LEGACY_VOCABULARY_REL, LEGACY_MANIFEST_REL}
    prefix = f"{CLAUDE_DIR}/"
    return sorted(c for c in candidates if c.startswith(prefix) and (repo / c).is_file())


def _old_namespace_files(src: Path, repo: Path, namespace: str, layout: str) -> list[str]:
    """Command files the previous sync recorded under a namespace other than today's
    (`SyncReport.renamed`). Read from the manifest alone — a file no sync is on record as having
    written is the repository's own, whatever directory it sits in."""
    target = namespace or source_namespace(src)
    base = f"{tier_root(layout)}/{COMMANDS_SUBDIR}/"
    out: list[str] = []
    recorded = read_manifest(repo, layout)
    for path in recorded:
        if path.startswith(base) and path[len(base) :].split("/", 1)[0] != target and (repo / path).is_file():
            out.append(path)
    # The primer was `.fleet/instructions.md` before it became `AGENTS.md`: the same retirement,
    # for a file at the tier's root that no tier directory walk looks at.
    out += [p for p in LEGACY_PLUGIN_FILES if p in recorded and (repo / p).is_file()]
    return sorted(out)


def _names_no_vocabulary(repo: Path) -> bool:
    """Whether the repository has a `fleet.toml` that points its board at no vocabulary."""
    located = configmod.find_config_file(repo)
    if located is None:
        return False
    return not str(located[1].get("board_guidance") or "").strip()


def _names_another_vocabulary(repo: Path) -> str:
    """The `board_guidance` a repository's `fleet.toml` names, when it is not the rendered file.

    `""` when there is no `fleet.toml`, no key, or the key names `VOCABULARY_REL` under any
    spelling of the same repo-relative path.
    """
    located = configmod.find_config_file(repo)
    if located is None:
        return ""
    named = str(located[1].get("board_guidance") or "").strip()
    if not named or posixpath.normpath(named) == vocabulary_rel(commands_layout(repo)):
        return ""
    return named


def _rendered_rel(d: str, rel: Path) -> Path:
    """A source rel under tier dir `d` -> the path it materializes to under `d`'s dest dir.

    For commands the namespace segment of the source path is replaced by the rendered one, so
    a comparison is made against the right directory; for every other dir it is the same path.
    """
    return Path(*rel.parts[1:]) if d == COMMANDS_SUBDIR else rel


def _report_name(d: str, rel: Path) -> str:
    """A (rendered) path under tier dir `d` -> the SOURCE-tier-relative name a report carries.

    `_target` maps it back to the rendered location with the namespace applied and `render`
    reads it from the source tree; a report naming the rendered location would be unreadable by
    both.
    """
    if d == COMMANDS_SUBDIR:
        return str(Path(d) / source_namespace() / rel)
    return str(Path(d) / rel)


def _target(rel: Path, namespace: str = "", layout: str = DEFAULT_LAYOUT) -> Path:
    """A tier-relative name (`scripts/x.py`, `commands/<source>/ask.md`) → its repo-relative path.

    A foreign `namespace` rewrites the command directory segment, so `commands/<source>/ask.md`
    lands at `.claude/commands/<ns>/ask.md`. A vendored-package name is already repo-relative
    (`.fleet/_vendor/…`) and is returned unchanged: it is not part of the tier tree that moves
    under `.fleet/`.
    """
    if str(rel).startswith(f"{VENDOR_DEST}/"):
        return rel
    parts = list(rel.parts)
    if parts and parts[0] == COMMANDS_SUBDIR and namespace and len(parts) > 1 and parts[1] == source_namespace():
        parts[1] = namespace
    return Path(dest_dir(parts[0], layout)) / Path(*parts[1:])


def _present_rel(d: str, namespace: str, trel: Path, src: Path, layout: str = DEFAULT_LAYOUT) -> str:
    """A file found under tier directory `d`'s destination -> its repo-relative path.

    The inverse of `_target` for a file whose SOURCE name is unknown (a foreign or retired
    file): the commands directory segment is the repository's own namespace, because that is
    the directory the walk descended into.
    """
    if d == COMMANDS_SUBDIR:
        return str(Path(dest_dir(d, layout)) / (namespace or source_namespace(src)) / trel)
    return str(Path(dest_dir(d, layout)) / trel)


def verify(
    repo: Path,
    *,
    name: str | None = None,
    replace: frozenset[str] = frozenset(),
    setup_inputs: Inputs | None = None,
    namespace: str | None = None,
    set_name: str | None = None,
) -> SyncReport:
    """What `sync` WOULD do. Writes nothing.

    `name` is the repository's name for product-scoped commands (`repo_name`), for a caller whose
    checkout is not a clone that names it — the service's scratch copy of a GitHub tree.
    `namespace` and `set_name` override the render for a caller that asks for one explicitly,
    exactly as `sync` does.
    """
    return _plan(
        repo.resolve(),
        name,
        replace=replace,
        setup_inputs=setup_inputs,
        namespace=namespace,
        set_name=set_name,
    )


def sync(
    repo: Path,
    *,
    prune: bool = False,
    name: str | None = None,
    replace: frozenset[str] = frozenset(),
    setup_inputs: Inputs | None = None,
    namespace: str | None = None,
    set_name: str | None = None,
) -> SyncReport:
    """Write the packaged tier into the repository (`.fleet/` or `.claude/`), and report what moved.

    `prune` is opt-in and off by default. A file the package does not carry is usually a
    repository's own addition rather than debris, and deleting one by default would make an
    upgrade silently destructive — the target directory is `.claude/`, which a repository may
    legitimately use for things this tier knows nothing about.

    `replace` names setup files whose hand-edited Fleet part the caller wants replaced anyway;
    `setup_inputs` are the stacks `fleet init` just rendered (`setupfiles`). `namespace` and
    `set_name` fill a value the repository's `[fleet.commands]` leaves out — a declared value
    always wins, so a later plain `sync` and this run agree about what the repository chose.
    """
    repo = repo.resolve()
    report = _plan(repo, name, replace=replace, setup_inputs=setup_inputs, namespace=namespace, set_name=set_name)
    src = source_root()
    namespace = report.namespace
    layout = report.layout
    for item in [*report.added, *report.changed]:
        # Every byte written is the plan's own render (`report.expected`), never a second one.
        dst = repo / report.written_path(item)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(report.expected[report.written_path(item)])
    # A shipped script is an entry point: a commit hook names it as `entry:` and execs it
    # directly, which refuses a file without the bit. Set on every sync, over every script
    # the tier carries — not only the ones rewritten — because content that already matches
    # says nothing about the mode, and a wheel does not promise to carry file modes.
    scripts = [repo / SCRIPTS_DEST / s.name for s in (src / SCRIPTS_SUBDIR).glob("*.py")]
    scripts += [repo / p for p in report.extended if p.startswith(f"{SCRIPTS_DEST}/") and p.endswith(".py")]
    for dst in scripts:
        if dst.is_file():
            dst.chmod(dst.stat().st_mode | 0o111)
    # ALWAYS, and not behind `prune`: this is the tier's own output from a previous version
    # of itself, not the repository's work. Leaving it would strand a procedure that cannot
    # run here and that no later sync would ever mention again.
    for name in [*report.superseded, *report.retired]:
        (repo / _target(Path(name), namespace, layout)).unlink(missing_ok=True)
    # THE OLD LAYOUT GOES IN THE SAME RUN THAT WRITES THE NEW ONE (`SyncReport.relocated`), and so
    # do the directories it leaves empty — git tracks no directory, but a person listing `.claude/`
    # should not find a `commands/<ns>/` shell that looks like the tier went missing.
    for rel_path in report.relocated:
        (repo / rel_path).unlink(missing_ok=True)
    for rel_path in report.renamed:
        (repo / rel_path).unlink(missing_ok=True)
    if report.renamed:
        _remove_empty_dirs(repo / tier_root(layout) / COMMANDS_SUBDIR, keep_root=True)
    if report.relocated:
        for d in TIER_DIRS:  # only the tier's own directories: the rest of `.claude/` is the repository's
            _remove_empty_dirs(repo / CLAUDE_DIR / d, keep_root=False)
    if prune:
        for name in report.removed:
            (repo / _target(Path(name), namespace, layout)).unlink(missing_ok=True)
    else:
        # Reported, not removed — and the report must not claim otherwise, or a caller that
        # trusts `in_sync` after a successful sync would be told the tree matches when a
        # foreign file is still sitting in it.
        pass
    # Record what this sync wrote, so the NEXT one can tell a file it wrote (and the package
    # has since dropped) from a file the repository added by hand, and a person's edit from an
    # older release (ENG-18630). Written last, over the set this run would leave: a manifest that
    # named a retired file would keep re-deleting it.
    # The setup files beyond the tier: only Fleet's part of each, and never one a person edited.
    if report.setup is not None:
        report.setup.apply(repo)
    manifest = manifest_path(repo, layout)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    setup_record = report.setup.record if report.setup is not None else None
    if _is_source_checkout(repo) and not setup_record:
        # The authors' own checkout commits its tier, and the release line plus a blob id per
        # file made this one shared file rewrite on every PR that touched the tier, so any two
        # such PRs conflicted on it by construction. Neither fact has a reader here: the release
        # is provenance `--check` never compares, and `--check` diffs the files against the
        # rendered source itself, so the ids only restated what git's tree already holds. What the
        # sync needs is the path list (to delete a retired file), which changes only when a file
        # enters or leaves. A consuming repository keeps the full record.
        manifest.write_bytes(manifest_bytes(set(report.expected)))
    else:
        manifest.write_bytes(
            manifest_record_bytes(
                report.expected,
                setup=setup_record,
                commands={"namespace": report.namespace, "set": report.set_name},
            )
        )
    return report


def _remove_empty_dirs(root: Path, *, keep_root: bool) -> None:
    """Delete every directory under `root` that holds nothing, deepest first."""
    if not root.is_dir():
        return
    for path in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if not any(path.iterdir()):
            path.rmdir()
    if not keep_root and not any(root.iterdir()):
        root.rmdir()


#: Bound last, because `source_namespace` reads the packaged tree through `source_root`.
CUSTOMER_NAMESPACE: str = source_namespace()
_COMMAND_PREFIX = _command_prefix(CUSTOMER_NAMESPACE)
