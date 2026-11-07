"""What `fleet commands sync` would change in a repository, decided from its git tree alone (ENG-18630).

The service offers a button — "Apply Fleet <release>" — that opens ONE pull request bringing a
repository's synced files (commands, process documents, scripts) up to the release the install
runs. It holds no checkout: it reads the repository through GitHub as a tree of paths, blob ids and
modes, and it has the proxy's thirty seconds to do it in.

**The plan IS the sync.** A second implementation of "what the sync would write" would drift from
the first the day either changed, and the pull request would then carry something `fleet commands
sync` never writes. So `plan` materialises the part of the tree the sync reads into a scratch
directory and runs the real `commandsync.sync` there, then reads back what moved. Nothing is
re-derived.

**Without downloading the files.** The sync reads a file's CONTENT for two reasons only: the
configuration (`fleet.toml`, or a `pyproject.toml` carrying the table) and the previous manifest
decide what it does, and every other file is only ever compared with what the package renders for
that path. So those two are fetched (`read`), and every other file is materialised from its blob
id: as the rendered bytes when the id matches them, and otherwise as a placeholder that matches
nothing — which the sync then overwrites exactly as it would overwrite the real, different bytes.
A placeholder the sync did not overwrite is a file it leaves alone, and is never written back.

**Hand edits are told apart from an older release by the manifest's hashes** (format 2): a file
whose blob id differs from the one the last sync recorded was changed after it, by somebody else.
A file the sync is about to replace that the record never named was not written by Fleet either.
A format 1 record (paths only) cannot tell, so every file it would replace is listed as
`unverified` instead — never claimed clean. Each hand-edited file's real bytes are then fetched (at
most `textdiff.MAX_DIFF_FILES` of them) so the plan carries the diff of what the update would undo.

**The setup files ride along** (`setupfiles`): Fleet's part of `CLAUDE.md`/`AGENTS.md`,
`.fleet/fleet.toml`, `.claude/settings.json` and the CI template — and, while a repository is still
on the layout before `.fleet/fleet.toml`, the root `fleet.toml`, `fleet.mk` and `Makefile` the
migration moves, deletes or edits (`setupfiles.LEGACY_FILES`). The sync reads their content, so they are
fetched like the configuration, and so is everything under `.fleet/local/` (the repository's
overrides, which the sync writes in place of the shipped files). Their state — up to date, will
update, hand-edited (kept, with the diff an update would make), missing, skipped — is the sync's
own report, carried as `setup`; `drift_json` is the shape a page renders.

Stdlib only, like the rest of the package.
"""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from fleet_knowledge import commandsync, setupfiles, textdiff
from fleet_knowledge import config as configmod
from fleet_knowledge import release as releasemod

__all__ = ["MANAGED_PREFIXES", "Plan", "TreeFile", "plan"]

#: Where the sync reads and writes, relative to the repository root: the two tier homes and the
#: scripts. Nothing outside them is materialised, and nothing outside them can be in a plan.
MANAGED_PREFIXES: tuple[str, ...] = (
    f"{commandsync.CLAUDE_DIR}/",
    f"{commandsync.PLUGIN_DIR}/",
    f"{commandsync.SCRIPTS_DEST}/",
)

#: The files whose CONTENT the sync reads to decide what to do — fetched, never stood in for: the
#: configuration, the setup files and the legacy root files (`setupfiles.READ_FILES`). Everything
#: under `commandsync.LOCAL_DIR` is fetched too.
_CONFIG_FILES: tuple[str, ...] = tuple(
    dict.fromkeys((configmod.CONFIG_FILENAME, configmod.PYPROJECT_FILENAME, *setupfiles.READ_FILES))
)

#: A path the sync must never write: GitHub refuses a whole tree that touches a workflow from a
#: token without the `workflows` permission, which the App does not hold by design.
_FORBIDDEN_PREFIX = ".github/workflows/"

_EXECUTABLE = "100755"
_REGULAR = "100644"


@dataclass(frozen=True, slots=True)
class TreeFile:
    """One blob in a git tree: its object id and its mode (`100644`, `100755`, `120000`)."""

    sha: str
    mode: str = _REGULAR


@dataclass
class Plan:
    """What applying this release to the repository changes, and what a reviewer should know."""

    namespace: str
    set_name: str
    layout: str
    #: The release the previous sync recorded; `""` when its record carries none (format 0 or 1).
    from_version: str
    #: The release this package is (`release.version()`); `""` in an unversioned source tree.
    to_version: str
    #: The previous record's format: `0` none, `1` paths only, `2` release and hashes.
    manifest_format: int
    #: `{path: (bytes, git mode)}` — every file to create or overwrite, mode changes included.
    writes: dict[str, tuple[bytes, str]] = field(default_factory=dict)
    #: Paths to delete: retired, superseded, relocated and renamed tier files.
    deletes: list[str] = field(default_factory=list)
    #: Paths this plan replaces or deletes that were changed after the last sync wrote them, or
    #: that no sync recorded writing. Only a format 2 record can name these.
    hand_edited: list[str] = field(default_factory=list)
    #: Under a format 1 record: every existing path this plan replaces or deletes, because Fleet
    #: cannot tell which of them a person edited.
    unverified: list[str] = field(default_factory=list)
    #: Files under the tier the package does not carry and the sync leaves where they are.
    left_alone: list[str] = field(default_factory=list)
    #: The sync's own report over the scratch copy, for its advice lines (`vocabulary_unclaimed`).
    report: commandsync.SyncReport | None = None
    #: Paths that exist in the tree, of `writes` — so a count can say added versus updated.
    existing: frozenset[str] = frozenset()
    #: Every setup file's state and would-be change (`setupfiles.SetupFile`); empty for a
    #: repository the sync manages none of (the tree's home copy).
    setup: list[setupfiles.SetupFile] = field(default_factory=list)
    #: `{path: (unified diff, truncated)}` for the hand-edited files the plan fetched; a path past
    #: `textdiff.MAX_DIFF_FILES`, and every `unverified` one, has none.
    diffs: dict[str, tuple[str | None, bool]] = field(default_factory=dict, repr=False)

    @property
    def changes(self) -> bool:
        """Whether the pull request would carry anything."""
        return bool(self.writes or self.deletes)

    def digest(self) -> str:
        """One id for WHAT this plan writes: the release, every write's path, mode and blob id, and
        every deletion. Two plans over two heads of a branch share it exactly when the sync would
        write the same files over both, which is how the service's keeper tells "the default branch
        moved" from "the default branch moved and the update must change" without diffing trees."""
        h = hashlib.sha256(f"release\0{self.to_version}\n".encode())
        for path in sorted(self.writes):
            data, mode = self.writes[path]
            h.update(f"write\0{path}\0{mode}\0{commandsync.blob_sha(data)}\n".encode())
        for path in sorted(self.deletes):
            h.update(f"delete\0{path}\n".encode())
        return h.hexdigest()

    def counts(self) -> dict[str, int]:
        """How many files change, by what they are — the line the confirm panel prints."""
        added = sum(1 for p in self.writes if p not in self.existing)
        updated = len(self.writes) - added
        kinds = {"commands": 0, "documents": 0, "scripts": 0, "setup": 0, "other": 0}
        for path in (*self.writes, *self.deletes):
            kinds[_kind(path, self.layout)] += 1
        return {
            "total": len(self.writes) + len(self.deletes),
            "added": added,
            "updated": updated,
            "deleted": len(self.deletes),
            **kinds,
        }

    def drift_json(self) -> dict[str, object]:
        """What a person should see before applying: the setup files, the hand edits, the overrides.

        The same shape as `commandsync.SyncReport.drift_json` — `setup`, `tierHandEdited`,
        `overrides`, `localIgnored`, `limits` — so one renderer serves a checkout and a hosted plan.
        `tierHandEdited` lists `hand_edited`, or `unverified` under a paths-only record (each with
        `"verified": false`), since either is a file whose edits the update may undo.
        """
        report = self.report
        verified = bool(self.hand_edited) or not self.unverified
        listed = self.hand_edited if self.hand_edited else self.unverified
        return {
            "setup": [f.as_json() for f in self.setup],
            "tierHandEdited": [
                {
                    "path": path,
                    "change": "replace" if path in self.writes else "delete",
                    "keepAt": commandsync.keep_at(path),
                    "verified": verified,
                    "diff": self.diffs.get(path, (None, False))[0],
                    "diffTruncated": self.diffs.get(path, (None, False))[1],
                }
                for path in listed
            ],
            "overrides": [
                {"path": path, "source": commandsync.keep_at(path), "shipped": path in report.overridden}
                for path in sorted({*report.overridden, *report.extended})
            ]
            if report is not None
            else [],
            "localIgnored": list(report.local_ignored) if report is not None else [],
            "limits": {"diffBytes": textdiff.MAX_DIFF_BYTES, "diffFiles": textdiff.MAX_DIFF_FILES},
        }


def _kind(path: str, layout: str) -> str:
    if path in setupfiles.SETUP_FILES or path in setupfiles.LEGACY_FILES:
        return "setup"
    if path.startswith(f"{commandsync.SCRIPTS_DEST}/"):
        return "scripts"
    for root in {commandsync.tier_root(layout), commandsync.CLAUDE_DIR}:
        if path.startswith(f"{root}/{commandsync.COMMANDS_SUBDIR}/"):
            return "commands"
        if any(path.startswith(f"{root}/{d}/") for d in ("process", "registers", "rubrics")):
            return "documents"
    return "other"


def _managed(path: str) -> bool:
    return path.startswith(MANAGED_PREFIXES) or path in setupfiles.SETUP_FILES or path in setupfiles.LEGACY_FILES


def _local(path: str) -> bool:
    return path.startswith(f"{commandsync.LOCAL_DIR}/")


def plan(
    files: Mapping[str, TreeFile], read: Callable[[str], bytes], *, name: str, replace: frozenset[str] = frozenset()
) -> Plan:
    """What `fleet commands sync` at this release would change in the tree `files`.

    `files` is the repository's tree, `{repo-relative path: TreeFile}`; `read(path)` returns one
    blob's bytes and is called only for the configuration, the setup files, the overrides, the
    manifests and the hand-edited files a diff is shown for. `name` is the repository's name
    (`owner/<name>`), which decides the product-scoped commands it receives. `replace` names
    hand-edited setup files whose Fleet part the update should replace anyway.
    """
    with tempfile.TemporaryDirectory(prefix="fleet-resync-") as scratch:
        root = Path(scratch) / "repo"
        root.mkdir()
        return _plan_in(root, files, read, name=name, replace=replace)


def _plan_in(
    root: Path,
    files: Mapping[str, TreeFile],
    read: Callable[[str], bytes],
    *,
    name: str,
    replace: frozenset[str] = frozenset(),
) -> Plan:
    for config in (*_CONFIG_FILES, *sorted(p for p in files if _local(p))):
        if config in files:
            _write(root / config, read(config), files[config].mode)
    namespace, set_name = commandsync.commands_config(root)
    layout = commandsync.commands_layout(root)

    record = commandsync.ManifestRecord()
    for candidate in dict.fromkeys((layout, *commandsync.LAYOUTS)):
        rel = commandsync.manifest_rel(candidate)
        if rel in files:
            data = read(rel)
            _write(root / rel, data, files[rel].mode)
            if record.format == 0:
                record = commandsync.parse_manifest(data)

    # The table the tier is rendered with is the one the configuration carries AFTER this sync (a
    # repository being migrated renders the table the migration writes), so plan the setup first.
    targets = setupfiles.plan(root, record.setup, namespace=namespace).targets
    rendered = commandsync.render_tree(
        namespace=namespace, set_name=set_name, name=name, layout=layout, targets=targets
    )
    by_sha = {path: commandsync.blob_sha(data) for path, data in rendered.items()}
    placed: dict[str, bytes] = {}
    for path, entry in files.items():
        if not _managed(path) or (root / path).exists():
            continue
        data = rendered[path] if by_sha.get(path) == entry.sha else _placeholder(path, entry.sha)
        _write(root / path, data, entry.mode)
        placed[path] = data

    report = commandsync.sync(root, name=name, replace=replace)

    out = Plan(
        namespace=report.namespace,
        set_name=report.set_name,
        layout=layout,
        from_version=record.version if record.format >= commandsync.MANIFEST_FORMAT else "",
        to_version=releasemod.version(),
        manifest_format=record.format,
        report=report,
        setup=list(report.setup.files) if report.setup is not None else [],
    )
    after = {p.relative_to(root).as_posix(): p for p in sorted(root.rglob("*")) if p.is_file()}
    for path, disk in after.items():
        if not _managed(path):
            continue
        data, mode = disk.read_bytes(), _mode(disk)
        before = files.get(path)
        if before is not None and commandsync.blob_sha(data) == before.sha and mode == before.mode:
            continue
        if before is not None and path in placed and data == placed[path] and mode == before.mode:
            continue
        if data.startswith(_PLACEHOLDER):
            # The sync changed only the MODE of a file whose bytes this plan never saw. It cannot
            # happen for a shipped file (one that is not byte-identical is rewritten), and writing
            # a stand-in back would destroy the real content, so it is refused outright.
            raise RuntimeError(f"{path}: the sync changed a file the plan holds no content for")
        out.writes[path] = (data, mode)
    out.deletes = sorted(p for p in files if _managed(p) and p not in after)
    out.existing = frozenset(p for p in out.writes if p in files)

    forbidden = [p for p in (*out.writes, *out.deletes) if p.startswith(_FORBIDDEN_PREFIX)]
    if forbidden:
        raise RuntimeError(f"a resync may never write a workflow file: {forbidden}")

    manifests = {commandsync.manifest_rel(candidate) for candidate in commandsync.LAYOUTS}
    # The setup files are judged by the sync itself (`out.setup`), against their own record.
    replaced = sorted(
        p
        for p in (*out.writes, *out.deletes)
        if p in files
        and p not in manifests
        and p not in setupfiles.SETUP_FILES
        and p not in setupfiles.LEGACY_FILES
        and not _local(p)
    )
    if record.format >= commandsync.MANIFEST_FORMAT:
        out.hand_edited = [p for p in replaced if record.files.get(p) != files[p].sha]
    elif record.format == 1:
        out.unverified = replaced
    out.left_alone = sorted(report.written_path(n) for n in report.removed)
    # The diff of what the update undoes, for the files a person changed: their real bytes were
    # never fetched (the plan stood in for them), so they are fetched now — capped, and never for
    # `unverified`, which under a paths-only record is every file the release changes.
    for path in out.hand_edited[: textdiff.MAX_DIFF_FILES]:
        new = out.writes[path][0] if path in out.writes else None
        out.diffs[path] = textdiff.unified_diff(path, read(path), new)
    return out


#: The stand-in for a file whose bytes were not fetched. Starts with a NUL so no rendered text file
#: can ever equal it, and names the blob so a leak would be traceable.
_PLACEHOLDER = b"\x00fleet-resync-placeholder "


def _placeholder(path: str, sha: str) -> bytes:
    return _PLACEHOLDER + f"{sha} {path}\n".encode()


def _write(path: Path, data: bytes, mode: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.exists():
        path.unlink()
    path.write_bytes(data)
    path.chmod(0o755 if mode == _EXECUTABLE else 0o644)


def _mode(path: Path) -> str:
    return _EXECUTABLE if os.stat(path).st_mode & stat.S_IXUSR else _REGULAR
