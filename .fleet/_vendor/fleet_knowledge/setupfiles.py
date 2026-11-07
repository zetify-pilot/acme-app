"""The setup files Fleet owns a part of, refreshed by `fleet commands sync` without clobbering yours.

`fleet init` writes more than the command tier: the always-on rules file (`CLAUDE.md`, and
`AGENTS.md`), `.fleet/fleet.toml`, the plugin opt-in in `.claude/settings.json`, and — for a
repository that named its stacks — the CI template under `.fleet/ci/`. Until now it wrote them
once and no release could ever touch them again, so a fix to Fleet's rules or a stack recipe
reached only the repositories set up after it. This module is what lets the sync carry them, and
the line it draws is between FLEET'S PART of a file and the REPOSITORY'S:

* **The rules files carry a marked block.** Fleet's rules live between
  `<!-- fleet:begin managed … -->` and `<!-- fleet:end -->`; the sync rewrites only that block and
  never a byte outside it. A file with no markers gets them once: a rules file written by a
  release before the markers (recognised by the hash of its Fleet text, `KNOWN_RULES_SHAS`) has
  that text wrapped in place; any other gets the block appended, unless another rules file
  already carries Fleet's rules.
* **The CI template is Fleet's whole file**, re-rendered from the stacks the repository named at
  init (recorded in the sync manifest) and the commands its `[fleet.targets]` table names.
* **`.fleet/fleet.toml` carries a schema `version`** and is upgraded by an ordered list of
  migrations, each a surgical line edit — never a re-serialisation, so your comments and layout
  survive. Version 2 is the move under `.fleet/` and the `[fleet.targets]` table: a repository
  still on a root `fleet.toml` has the file moved, the table filled from what its `Makefile` and
  `fleet.mk` ran, Fleet's stub `Makefile` and `fleet.mk` deleted, and Fleet's `-include fleet.mk`
  taken out of a Makefile that is its own (`_plan_config`). THIS PART RUNS IN EVERY REPOSITORY,
  the tree's home copy included: there is one way a target is resolved, wherever the tier lands.
* **`.claude/settings.json` has two keys of Fleet's** (the marketplace and the enabled plugin).
  They are kept current where the repository opted in; a repository that did not opt its people's
  sessions in is never opted in by an update, because loading the commands into everyone's own
  session uninvited is exactly what the `.fleet/` plugin layout exists to avoid.

**An edit to Fleet's part is never overwritten.** The sync records the git blob id of each part it
writes; a part whose id is neither the recorded one, nor one a release shipped, nor what this
release renders was changed by a person, and is reported as `hand-edited` with the diff the update
would make — and left alone, unless the caller names it in `replace`. This is deliberately
stricter than the tier, whose files are overwritten with a warning: the tier was always
generated-and-verified, while these files were documented as the repository's own until now.

The rest is managed only in a customer render (a repository that declares `[fleet.commands]
namespace`): the tree's home copy is the authors' own repository, whose rules and settings are
written by hand. And `[fleet.setup] skip = ["CLAUDE.md", …]` takes any of these files out of the
sync's hands.

Stdlib only.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fleet_knowledge import commandsync, legacymake, rulesfile, textdiff
from fleet_knowledge import config as configmod
from fleet_knowledge import stacks as stackmod
from fleet_knowledge import targets as targetsmod

__all__ = [
    "BEGIN_LINE",
    "CI_FILES",
    "END_LINE",
    "FLEET_TOML",
    "FLEET_TOML_VERSION",
    "KNOWN_RULES_SHAS",
    "LEGACY_FILES",
    "LEGACY_FLEET_TOML",
    "MIGRATIONS",
    "READ_FILES",
    "SETTINGS",
    "SETUP_FILES",
    "STATES",
    "Inputs",
    "Migration",
    "MigrationContext",
    "SetupFile",
    "SetupPlan",
    "fleet_toml_version",
    "migrate_fleet_toml",
    "plan",
    "plan_files",
    "rules_block",
    "rules_body",
    "rules_body_template_form",
    "rules_template",
]

FLEET_TOML = configmod.CONFIG_REL
SETTINGS = ".claude/settings.json"
CI_FILES: tuple[str, ...] = (stackmod.CI_WORKFLOW, stackmod.CI_README)
#: The root files releases before `.fleet/fleet.toml` wrote, which the version 2 migration moves,
#: deletes or edits: the root `fleet.toml`, `fleet.mk`, and the `Makefile` (Fleet's stub, deleted;
#: or the repository's own, with Fleet's include taken out).
LEGACY_FLEET_TOML = configmod.LEGACY_CONFIG_REL
FLEET_MK = legacymake.FLEET_MK
MAKEFILE = "Makefile"
LEGACY_FILES: tuple[str, ...] = (LEGACY_FLEET_TOML, FLEET_MK, MAKEFILE)

#: Every setup file the sync may refresh, in the order a report lists them.
SETUP_FILES: tuple[str, ...] = (*rulesfile.RULES_FILES, FLEET_TOML, SETTINGS, *CI_FILES)
#: Every file whose CONTENT this module reads: the setup files and the legacy root files the
#: migration folds in. A caller with no checkout (`resync`) fetches exactly these.
READ_FILES: tuple[str, ...] = (*SETUP_FILES, *LEGACY_FILES)

#: What a setup file's report says about it. `up-to-date`: nothing to do. `will-update`: the sync
#: rewrites Fleet's part. `hand-edited`: a person changed Fleet's part; the sync leaves it, and the
#: diff says what an update would change. `missing`: the file is absent (`action` says whether the
#: sync creates it). `skipped`: the sync does not manage it here (`detail` says why).
STATES: tuple[str, ...] = ("up-to-date", "will-update", "hand-edited", "missing", "skipped")

# ── the rules block ──────────────────────────────────────────────────────────

BEGIN_LINE = (
    "<!-- fleet:begin managed — `fleet commands sync` rewrites everything from here to fleet:end; "
    "write this repository's own rules below it -->"
)
END_LINE = "<!-- fleet:end -->"
_BEGIN = re.compile(r"^<!-- fleet:begin managed\b[^\n]*-->[ \t]*$", re.M)
_END = re.compile(r"^<!-- fleet:end -->[ \t]*$", re.M)

#: The placeholders the rules template carries. `{{namespace}}` is the repository's own command
#: namespace (`[fleet.commands] namespace`), `{{tierRoot}}` the directory its layout puts the tier
#: under. A rendered block carries them filled in; Fleet's record of a release's text keeps them as
#: written, so one id stands for that text in every repository, whatever its namespace.
NAMESPACE_PLACEHOLDER = "{{namespace}}"
TIER_ROOT_PLACEHOLDER = "{{tierRoot}}"

#: The git blob id of every rules text a release shipped — the text between the markers, or, for
#: the release before the markers, everything above `rulesfile.RULES_SECTION`. A block (or an
#: unmarked file) carrying one of these is Fleet's own older text, not a person's edit. Since the
#: block names the repository's commands, an id is of the text in TEMPLATE FORM — rendered for one
#: set with the namespace and tier root left as their placeholders (`rules_body_template_form`),
#: and a block on disk is compared after its own namespace is put back (`_template_form`). WHEN THE
#: TEMPLATE'S RULES OR THE COMMANDS A SET LISTS CHANGE, ADD THE NEW IDS HERE — never replace one: a
#: repository on the old text must still read as un-edited (`test_setupfiles` holds the current
#: template, for every set, to this set).
KNOWN_RULES_SHAS: frozenset[str] = frozenset(
    {
        # The standing rules alone, before the block named the commands.
        "4cb563b6004e674d94e187d2d91ef21e363973b6",
        # The standing rules with the Commands orientation (both sets list the same commands).
        "770fb1bda190ec467fabec3fe80205190019d301",
        # And the writing rules (`process/writing.md`): English for what lasts, plain language.
        "562f7107dfb393ac99b7e50acf0d22d2c76d4919",
        # And a third writing rule: never write a real customer's name.
        "003588e8ad2a262804875f3fbbbecde16215b9ae",
        # And a fourth writing rule: write a promise in one plain sentence (2026-10-28).
        "4eaf205aa930c1c84e711b30d0ba62001c35a3b9",
        # And the feature-flow guidance in the standing rules (a feature request, a new feature, a plan).
        "47effc9a91a238223a87a189dc82b784b207b151",
        # And the Fleet and knowledge-base primer, so a session is told what it is planning against
        # and where Fleet's docs are (ENG-21998).
        "9e23c4b9e2309c13276e8513788faea813363fbb",
        # And a fifth writing rule: write for a reader who does not know the code, with the
        # internal terms to keep out of the sentence (ENG-22182).
        "d4d37339cc43085ca72c53407c6a2189f503ce3c",
        # And the second writing rule rewritten as "Use plain English": sentence, word, clarity and
        # structure rules, a banned-word list, a 20-word ceiling and a final check (2026-11-03).
        "30fa868269e026db35942de4874c86f4fbfd55b3",
        # And the pointer to `.fleet/AGENTS.md`: read a knowledge file type's docs page first.
        "0056e6dfbeead22aba2f87f544a468c532aabfbf",
        # And the plain-English rule naming ASD-STE100, with instructions split from descriptions
        # and the one-word-one-meaning term list (2026-11-05).
        "cf913f0dab5aa195d1b7e9d37724ff7b6f04df00",
        # The same, on top of the `.fleet/AGENTS.md` pointer.
        "299ecd9536af633d6f2a1e566cf7a75cd67f8486",
    }
)

#: A command-list item in the template: `- ` and one or more `` `/{{namespace}}:<verb>` `` before the
#: ` — ` that starts its sentence. Rendering keeps only the verbs the repository's set ships and
#: drops an item left with none.
_COMMAND_ITEM = re.compile(r"^- ((?:`/\{\{namespace\}\}:[a-z0-9:-]+`(?:, )?)+) — ")
_COMMAND_REF = re.compile(r"`/\{\{namespace\}\}:([a-z0-9:-]+)`")


def _template() -> str:
    """The rules template with its includes expanded from the packaged command tree.

    The block carries shared text the command tier also inlines — the writing rules
    (`process/writing.md`) — through the same include marker and renderer, so the two can never
    drift apart: the source is written once, and both surfaces are rendered from it.
    """
    rel = Path("templates") / "scaffold" / rulesfile.RULES_TEMPLATE
    text = (Path(__file__).resolve().parent / rel).read_text(encoding="utf-8")
    return commandsync.render_includes(commandsync.source_root(), rel, text)


def _render_rules(template: str, *, namespace: str, tier_root: str, verbs: frozenset[str]) -> str:
    """`template` with its command list narrowed to `verbs` and the placeholders filled in.

    A list item is the line naming its commands plus the indented lines that continue it, so an
    item whose commands all fall away leaves no stray continuation behind.
    """
    out: list[str] = []
    dropping = False
    for line in template.splitlines(keepends=True):
        if dropping and line.startswith("  "):
            continue
        dropping = False
        m = _COMMAND_ITEM.match(line)
        if m is not None:
            kept = [v for v in _COMMAND_REF.findall(m.group(1)) if v in verbs]
            if not kept:
                dropping = True
                continue
            head = ", ".join(f"`/{NAMESPACE_PLACEHOLDER}:{v}`" for v in kept)
            line = f"- {head} — {line[m.end() :]}"
        out.append(line)
    return "".join(out).replace(NAMESPACE_PLACEHOLDER, namespace).replace(TIER_ROOT_PLACEHOLDER, tier_root)


def rules_template(
    namespace: str,
    set_name: str = "all",
    *,
    layout: str = commandsync.DEFAULT_LAYOUT,
    src: Path | None = None,
    name: str = "",
) -> str:
    """The whole rules template rendered for a repository: what `fleet init` writes as `CLAUDE.md`.

    `namespace` is the repository's own (`[fleet.commands] namespace`), `set_name` its set — the
    block lists only the commands that set ships (`commandsync.shipped_verbs`). `src` is the
    command tree to read the set from (the packaged one by default).
    """
    verbs = commandsync.shipped_verbs(set_name, src=src, name=name)
    return _render_rules(_template(), namespace=namespace, tier_root=commandsync.tier_root(layout), verbs=verbs)


def rules_body(
    namespace: str,
    set_name: str = "all",
    *,
    layout: str = commandsync.DEFAULT_LAYOUT,
    src: Path | None = None,
    name: str = "",
) -> str:
    """Fleet's rules as this release ships them for a repository: the text between the markers."""
    found = _block(rules_template(namespace, set_name, layout=layout, src=src, name=name))
    if found is None:
        raise RuntimeError(f"the shipped {rulesfile.RULES_TEMPLATE} template carries no fleet:begin/fleet:end block")
    return found[2]


def rules_body_template_form(set_name: str = "all", *, src: Path | None = None, name: str = "") -> str:
    """`rules_body` for `set_name` with the namespace and tier root left as placeholders — the
    text a `KNOWN_RULES_SHAS` id is taken of."""
    verbs = commandsync.shipped_verbs(set_name, src=src, name=name)
    found = _block(
        _render_rules(_template(), namespace=NAMESPACE_PLACEHOLDER, tier_root=TIER_ROOT_PLACEHOLDER, verbs=verbs)
    )
    if found is None:
        raise RuntimeError(f"the shipped {rulesfile.RULES_TEMPLATE} template carries no fleet:begin/fleet:end block")
    return found[2]


def rules_block(
    namespace: str,
    set_name: str = "all",
    *,
    layout: str = commandsync.DEFAULT_LAYOUT,
    src: Path | None = None,
    name: str = "",
) -> str:
    """The whole managed block — markers included — as the sync writes it."""
    return f"{BEGIN_LINE}\n{rules_body(namespace, set_name, layout=layout, src=src, name=name)}{END_LINE}\n"


def _template_form(part: str, namespace: str, layout: str) -> str:
    """A rendered block put back in template form: its own namespace and tier root re-placeheld.

    The inverse of the two substitutions `_render_rules` makes, applied only where they produce
    the shapes it writes (`<tier>/commands/<ns>/` and `/<ns>:`), so prose that happens to contain
    the namespace as a word is left as it is.
    """
    tier = commandsync.tier_root(layout)
    text = part.replace(f"{tier}/commands/{namespace}/", f"{TIER_ROOT_PLACEHOLDER}/commands/{NAMESPACE_PLACEHOLDER}/")
    return text.replace(f"/{namespace}:", f"/{NAMESPACE_PLACEHOLDER}:")


def _is_known_rules(part: str, namespace: str, layout: str) -> bool:
    """Whether `part` is a rules text some release shipped, in any repository's namespace."""
    shas = {commandsync.blob_sha(part.encode("utf-8"))}
    if namespace:
        shas.add(commandsync.blob_sha(_template_form(part, namespace, layout).encode("utf-8")))
    return bool(shas & KNOWN_RULES_SHAS)


def _block(text: str) -> tuple[int, int, str] | None:
    """`(start, end, body)` of the one managed block in `text`, or `None` without exactly one.

    `start`/`end` span the begin line through the end line and its newline; `body` is the text
    between the two lines.
    """
    begins, ends = list(_BEGIN.finditer(text)), list(_END.finditer(text))
    if len(begins) != 1 or len(ends) != 1 or ends[0].start() < begins[0].end():
        return None
    b, e = begins[0], ends[0]
    end = e.end() + 1 if text[e.end() : e.end() + 1] == "\n" else e.end()
    return b.start(), end, text[b.end() + 1 : e.start()]


def _has_markers(text: str) -> bool:
    return bool(_BEGIN.search(text) or _END.search(text))


def _legacy_segment(text: str) -> str | None:
    """The Fleet text at the top of a rules file a release before the markers wrote, or `None`."""
    segment = text.split("\n" + rulesfile.RULES_SECTION, 1)[0]
    if segment != text and commandsync.blob_sha(segment.encode("utf-8")) in KNOWN_RULES_SHAS:
        return segment
    return None


# ── fleet.toml migrations ────────────────────────────────────────────────────

#: The schema version this release writes and migrates every `fleet.toml` up to.
FLEET_TOML_VERSION = 2

#: The comment above the `version` key, written by `fleet init` and by the migration alike so the
#: two read the same.
VERSION_COMMENT = "# This file's schema version. `fleet commands sync` upgrades the file in place; leave it as it is."


@dataclass(frozen=True)
class MigrationContext:
    """What a step may need beyond the file's own text: what the repository's other files say.

    `targets` is the `[fleet.targets]` table read from the `Makefile` and `fleet.mk` the version 2
    step folds in (`_derive_targets`) — the file alone cannot know what `make lint` ran.
    """

    targets: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Migration:
    """One step of the `fleet.toml` schema, from `to_version - 1` to `to_version`.

    `apply` takes the file's text (and the `MigrationContext`) and returns it changed — by line
    edits, never by parsing and re-serialising, which would drop every comment. It need not touch
    `version`: the runner sets that after the step, and refuses the result unless it still parses
    as TOML.
    """

    to_version: int
    summary: str
    apply: Callable[[str, MigrationContext], str]


def _stamp(text: str, context: MigrationContext) -> str:
    del context
    return text


def _add_targets(text: str, context: MigrationContext) -> str:
    """Version 2: the `[fleet.targets]` table, appended (a file that already has one keeps it).

    The file's MOVE to `.fleet/` is the planner's (`_plan_config`), because a migration edits text
    and a move is a path; the two land in the same sync, so a version 2 file is always at
    `.fleet/fleet.toml`.
    """
    data = tomllib.loads(text)
    if "targets" in _fleet_table(data):
        return text
    header = "[fleet.targets]" if isinstance(data.get("fleet"), Mapping) or not data else "[targets]"
    sep = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    return text + sep + targetsmod.table_block(context.targets, header=header)


#: Every migration, in order. A repository on version N runs the steps whose `to_version` > N.
#: Version 0 is a file written before the schema had a version.
MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, "records the file's schema version", _stamp),
    Migration(
        2,
        "adds the [fleet.targets] table — what each conventional target runs in this repository, "
        "read from the Makefile and fleet.mk it replaces",
        _add_targets,
    ),
)

_HEADER = re.compile(r"^\s*\[\[?\s*([A-Za-z0-9_.\-\"' ]+?)\s*\]\]?\s*(?:#.*)?$")
_VERSION_LINE = re.compile(r"^(\s*version\s*=\s*)([^#\n]*?)(\s*(?:#.*)?)$")


def _fleet_table(data: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = data.get("fleet")
    return nested if isinstance(nested, Mapping) else data


def fleet_toml_version(text: str) -> int:
    """The schema version a `fleet.toml` declares; `0` when it declares none.

    Raises `ValueError` for a file that is not TOML or whose `version` is not a whole number.
    """
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"not valid TOML — {exc}") from exc
    raw = _fleet_table(data).get("version", 0)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise ValueError(f"`version = {raw!r}` is not a schema version")
    return raw


def _set_version(text: str, version: int) -> str:
    """`text` with the fleet table's `version` set to `version`, by editing one line (or adding two)."""
    nested = isinstance(tomllib.loads(text).get("fleet"), Mapping)
    lines = text.splitlines(keepends=True)
    headers = [(i, m.group(1).replace(" ", "")) for i, line in enumerate(lines) if (m := _HEADER.match(line))]
    if nested:
        own = next((i for i, name in headers if name == "fleet"), None)
        if own is None:
            # Only `[fleet.<x>]` tables: a `[fleet]` table goes in front of the first of them.
            first = next(i for i, name in headers if name.startswith("fleet."))
            lines[first:first] = ["[fleet]\n", f"{VERSION_COMMENT}\n", f"version = {version}\n", "\n"]
            return "".join(lines)
        start, stop = own + 1, next((i for i, _ in headers if i > own), len(lines))
    else:
        start, stop = 0, headers[0][0] if headers else len(lines)
    for i in range(start, stop):
        m = _VERSION_LINE.match(lines[i].rstrip("\n"))
        if m:
            ending = "\n" if lines[i].endswith("\n") else ""
            lines[i] = f"{m.group(1)}{version}{m.group(3)}{ending}"
            return "".join(lines)
    at = start
    if not nested:
        # Below the file's leading comment block, so a heading comment stays the file's heading.
        while at < stop and (not lines[at].strip() or lines[at].lstrip().startswith("#")):
            at += 1
    if at > 0 and not lines[at - 1].endswith("\n"):
        lines[at - 1] += "\n"
    lines[at:at] = [f"{VERSION_COMMENT}\n", f"version = {version}\n"]
    return "".join(lines)


def migrate_fleet_toml(text: str, context: MigrationContext | None = None) -> tuple[str, list[str]]:
    """`(text, summaries)`: `text` upgraded to `FLEET_TOML_VERSION`, and what each step did.

    Idempotent: a file already at the version comes back unchanged with no summaries. Raises
    `ValueError` for a file this release cannot migrate (not TOML, a bad or newer `version`).
    """
    context = context or MigrationContext()
    current = fleet_toml_version(text)
    if current > FLEET_TOML_VERSION:
        raise ValueError(f"`version = {current}` was written by a newer Fleet (this one writes {FLEET_TOML_VERSION})")
    done: list[str] = []
    for step in MIGRATIONS:
        if step.to_version <= current:
            continue
        text = _set_version(step.apply(text, context), step.to_version)
        if fleet_toml_version(text) != step.to_version:  # also proves the edit still parses
            raise ValueError(f"the step to version {step.to_version} did not leave a readable file")
        done.append(f"version {step.to_version}: {step.summary}")
    return text, done


# ── the plan ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Inputs:
    """What the CI template is rendered from: the stacks, and the runner label. Also what the version 2
    migration re-renders an unedited `fleet.mk` from, to recognise it."""

    stacks: tuple[stackmod.Choice, ...] = ()
    ci_runner: str = ""

    def as_record(self) -> dict[str, object]:
        if not self.stacks:
            return {}
        return {
            "stacks": [{"id": c.id, "root": c.root, "vars": dict(sorted(c.vars.items()))} for c in self.stacks],
            "ciRunner": self.ci_runner,
        }

    @classmethod
    def from_record(cls, setup: Mapping[str, object]) -> Inputs | None:
        raw = setup.get("stacks")
        if not isinstance(raw, list) or not raw:
            return None
        known = stackmod.profiles()
        choices: list[stackmod.Choice] = []
        for item in raw:
            if not isinstance(item, dict) or item.get("id") not in known:
                return None
            values = item.get("vars")
            choices.append(
                stackmod.Choice(
                    str(item["id"]),
                    str(item.get("root") or "."),
                    {str(k): str(v) for k, v in values.items()} if isinstance(values, dict) else {},
                )
            )
        runner = setup.get("ciRunner")
        return cls(tuple(choices), runner if isinstance(runner, str) else "")


@dataclass
class SetupFile:
    """One setup file's state, and what the sync does to it."""

    path: str
    #: `rules-block` (a marked block in a file of yours), `whole-file` (Fleet's own file),
    #: `config` (`fleet.toml`'s schema and place), `settings` (two keys of `.claude/settings.json`)
    #: or `legacy` (a root file an earlier release wrote, which the migration deletes or edits).
    kind: str
    state: str
    #: `none`, `create`, `rewrite-block`, `wrap-block`, `insert-block`, `replace`, `migrate`, `merge`,
    #: `move` (the root `fleet.toml`, deleted where `.fleet/fleet.toml` is created), `delete`, `edit`.
    action: str
    #: One plain sentence a person reads: why this state, and what to do about it.
    detail: str
    current: bytes | None = field(default=None, repr=False)
    #: What the file would hold after an update — `None` when nothing would be written.
    proposed: bytes | None = field(default=None, repr=False)
    #: The blob id to record for Fleet's part after this sync, or `None` to record none.
    record: str | None = None
    #: The sync DELETES the file (`move`, `delete`); `proposed` is then `None`.
    remove: bool = False

    @property
    def writes(self) -> bool:
        """Whether this sync writes (or deletes) the file."""
        return (self.proposed is not None or self.remove) and self.state in ("will-update", "missing")

    def diff(self, cap: int = textdiff.MAX_DIFF_BYTES) -> tuple[str | None, bool]:
        """The would-be change as a unified diff, `(text, truncated)`; `(None, False)` for none."""
        if self.remove:
            return textdiff.unified_diff(self.path, self.current, None, cap=cap)
        if self.proposed is None:
            return None, False
        return textdiff.unified_diff(self.path, self.current, self.proposed, cap=cap)

    def as_json(self) -> dict[str, object]:
        text, cut = self.diff() if self.state in ("will-update", "hand-edited", "missing") else (None, False)
        return {
            "path": self.path,
            "kind": self.kind,
            "state": self.state,
            "action": self.action,
            "detail": self.detail,
            "diff": text,
            "diffTruncated": cut,
        }


@dataclass
class SetupPlan:
    files: list[SetupFile] = field(default_factory=list)
    #: The `setup` object the manifest records after this sync (`{}` when there is nothing to record).
    record: dict[str, object] = field(default_factory=dict)
    #: The `[fleet.targets]` table the repository carries AFTER this sync — what the tier is
    #: rendered with, so the run that migrates a repository renders the table it writes. `None`
    #: when the plan did not decide it (the configuration could not be read); the sync then reads
    #: the file as it is.
    targets: dict[str, str] | None = None

    @property
    def in_sync(self) -> bool:
        """Whether the sync would write nothing. A hand-edited or skipped file is not drift: the
        sync leaves it alone by design, and a check that failed on it would fail forever."""
        return not any(f.writes for f in self.files)

    def apply(self, repo: Path) -> list[str]:
        written: list[str] = []
        for entry in self.files:
            if not entry.writes:
                continue
            path = repo / entry.path
            if entry.remove:
                path.unlink(missing_ok=True)
                written.append(entry.path)
            elif entry.proposed is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(entry.proposed)
                written.append(entry.path)
        return written


def plan(
    repo: Path,
    previous: Mapping[str, object],
    *,
    namespace: str,
    replace: frozenset[str] = frozenset(),
    inputs: Inputs | None = None,
    skip: frozenset[str] = frozenset(),
    set_name: str | None = None,
    name: str = "",
) -> SetupPlan:
    """What the sync does to `repo`'s setup files.

    `previous` is the manifest's `setup` object from the last sync (`{}` for none). `replace` names
    hand-edited files whose Fleet part the caller wants replaced anyway. `inputs` overrides the
    recorded stacks (`fleet init` passes what it just rendered). `skip` is `[fleet.setup] skip`.
    `set_name` is the repository's command set — read from its `fleet.toml` when not given — and
    decides which commands the rules block names; `name` is the repository's own name.
    """
    if set_name is None:
        set_name = commandsync.commands_config(repo)[1]
    layout = commandsync.commands_layout(repo)

    def read(rel: str) -> bytes | None:
        path = repo / rel
        return path.read_bytes() if path.is_file() else None

    return plan_files(
        read,
        previous,
        namespace=namespace,
        replace=replace,
        inputs=inputs,
        skip=skip,
        set_name=set_name,
        layout=layout,
        name=name,
    )


def plan_files(
    read: Callable[[str], bytes | None],
    previous: Mapping[str, object],
    *,
    namespace: str,
    replace: frozenset[str] = frozenset(),
    inputs: Inputs | None = None,
    skip: frozenset[str] = frozenset(),
    set_name: str = "all",
    layout: str = commandsync.DEFAULT_LAYOUT,
    name: str = "",
) -> SetupPlan:
    """`plan` over files read through `read(rel)` (`None` for an absent file) — the pure half, for
    a caller with no checkout (the setup pull request records what it lays down).

    The configuration's own migration (`_plan_config`) is planned in EVERY repository; the rules
    block, the settings and the CI template only in a customer render (`namespace`)."""
    recorded_raw = previous.get("files")
    recorded = (
        {str(k): str(v) for k, v in recorded_raw.items() if isinstance(v, str)}
        if isinstance(recorded_raw, dict)
        else {}
    )
    out = SetupPlan()
    resolved = inputs or Inputs.from_record(previous) or _inputs_from_files(read)
    config_files, out.targets = _plan_config(read, recorded, replace, resolved, skip)
    if namespace:
        out.files.extend(
            _plan_rules(read, recorded, replace, namespace=namespace, set_name=set_name, layout=layout, name=name)
        )
    out.files.extend(config_files)
    if namespace:
        out.files.append(_plan_settings(read, namespace))
        if resolved is not None:
            out.files.extend(_plan_ci_files(read, recorded, replace, resolved, out.targets or {}))
    for entry in out.files:
        if entry.path in skip:
            entry.state, entry.action, entry.proposed = "skipped", "none", None
            entry.detail = f"listed in `[fleet.setup] skip` in {FLEET_TOML}, so the sync leaves it alone"
            entry.record = recorded.get(entry.path)
    files = {f.path: f.record for f in out.files if f.record is not None}
    out.record = {
        **({"files": dict(sorted(files.items()))} if files else {}),
        **(resolved.as_record() if resolved else {}),
    }
    return out


def _decide(
    path: str,
    part: bytes,
    new_part: bytes,
    recorded: str | None,
    replace: frozenset[str],
    known: frozenset[str] = frozenset(),
) -> tuple[str, str]:
    """`(state, record)` for a Fleet part that exists: `part` now, `new_part` after an update.

    Fleet's own when its blob id is the one the last sync recorded or one a release shipped
    (`known`); anything else is a person's edit, replaced only when `path` is in `replace`.
    """
    new_sha = commandsync.blob_sha(new_part)
    if part == new_part:
        return "up-to-date", new_sha
    sha = commandsync.blob_sha(part)
    if sha == recorded or sha in known or path in replace:
        return "will-update", new_sha
    return "hand-edited", recorded or ""


def _plan_rules(
    read: Callable[[str], bytes | None],
    recorded: Mapping[str, str],
    replace: frozenset[str],
    *,
    namespace: str,
    set_name: str,
    layout: str,
    name: str,
) -> list[SetupFile]:
    body = rules_body(namespace, set_name, layout=layout, name=name)
    block = f"{BEGIN_LINE}\n{body}{END_LINE}\n"
    texts = {
        rel: (data.decode("utf-8", "replace") if (data := read(rel)) is not None else None)
        for rel in rulesfile.RULES_FILES
    }
    carriers = {
        rel for rel, text in texts.items() if text is not None and (_has_markers(text) or _legacy_segment(text))
    }
    appended = False
    out: list[SetupFile] = []
    for rel, text in texts.items():
        if text is None:
            out.append(SetupFile(rel, "rules-block", "missing", "none", f"there is no {rel}; `fleet init` writes one"))
            continue
        current = text.encode("utf-8")
        found = _block(text)
        if found is not None:
            start, end, part = found
            proposed = (text[:start] + block + text[end:]).encode("utf-8")
            # A block some release shipped — under this namespace, or with no namespace in it — is
            # Fleet's own older text, so an upgrade rewrites it rather than reporting an edit.
            known = (
                frozenset({commandsync.blob_sha(part.encode("utf-8"))})
                if _is_known_rules(part, namespace, layout)
                else frozenset()
            )
            state, record = _decide(rel, part.encode("utf-8"), body.encode("utf-8"), recorded.get(rel), replace, known)
            detail = {
                "up-to-date": "Fleet's rules block matches this release",
                "will-update": "the sync rewrites Fleet's rules block; nothing outside the markers changes",
                "hand-edited": (
                    "somebody changed the text inside Fleet's markers, so the sync leaves it; move your rules "
                    f"below `{END_LINE}` and undo the edit, or ask the sync to replace the block"
                ),
            }[state]
            out.append(
                SetupFile(
                    rel,
                    "rules-block",
                    state,
                    "rewrite-block" if state == "will-update" else "none",
                    detail,
                    current,
                    proposed if state != "up-to-date" else None,
                    record or None,
                )
            )
            continue
        if _has_markers(text):
            out.append(
                SetupFile(
                    rel,
                    "rules-block",
                    "skipped",
                    "none",
                    "Fleet's markers are broken (one is missing or there are several), so the sync cannot "
                    f"tell its rules from yours; leave exactly one `{BEGIN_LINE[:24]}…` line and one `{END_LINE}` line",
                    current,
                    record=recorded.get(rel),
                )
            )
            continue
        segment = _legacy_segment(text)
        if segment is not None:
            proposed = (block + text[len(segment) :]).encode("utf-8")
            out.append(
                SetupFile(
                    rel,
                    "rules-block",
                    "will-update",
                    "wrap-block",
                    "the sync puts Fleet's markers around the rules an older Fleet wrote here, so later "
                    "releases can update them; your own rules are untouched",
                    current,
                    proposed,
                    commandsync.blob_sha(body.encode("utf-8")),
                )
            )
            continue
        if carriers or appended:
            other = sorted(carriers)[0] if carriers else rulesfile.RULES_FILES[0]
            out.append(
                SetupFile(
                    rel,
                    "rules-block",
                    "skipped",
                    "none",
                    f"Fleet's rules are already in {other}, so they are not added here a second time",
                    current,
                )
            )
            continue
        appended = True
        sep = "" if text.endswith("\n") or not text else "\n"
        proposed = (text + sep + ("\n" if text else "") + block).encode("utf-8")
        out.append(
            SetupFile(
                rel,
                "rules-block",
                "will-update",
                "insert-block",
                "the sync adds Fleet's rules as a marked block at the end; nothing already in the file changes",
                current,
                proposed,
                commandsync.blob_sha(body.encode("utf-8")),
            )
        )
    return out


#: Each target's meaning, in vocabulary order — the order an earlier release's `fleet.mk` listed them in.
_MEANINGS: dict[str, str] = {name: t.meaning for name, t in targetsmod.TARGETS.items()}
#: Each target's placeholders, as the stack renderer takes them.
_PARAMS: dict[str, tuple[str, ...]] = {name: t.params for name, t in targetsmod.TARGETS.items()}

#: The file the sync writes where a repository has no configuration at all: only what is not a
#: default — the schema version — and the table.
_NEW_CONFIG_HEAD = (
    "# Fleet's configuration for this repository. Every option has a working default, so this file\n"
    "# states only what is not the default; `fleet init` documents the rest.\n"
    "[fleet]\n"
    f"{VERSION_COMMENT}\n"
    f"version = {FLEET_TOML_VERSION}\n"
    "\n"
)


def _table_of(text: str, source: str) -> dict[str, str]:
    """The `[fleet.targets]` table a configuration's TEXT carries, checked; `{}` for none."""
    data = tomllib.loads(text)
    raw = _fleet_table(data).get("targets")
    if raw is None:
        return {}
    try:
        return targetsmod.read_table(raw, source)
    except targetsmod.TargetError as exc:
        raise configmod.ConfigError(str(exc)) from exc


def _same_rules(a: str, b: str) -> bool:
    """Whether two Makefile fragments say the same thing once their comments are set aside.

    A `fleet.mk` names each target's meaning in a comment, and the meanings were reworded when the
    table replaced the file; what the file RUNS is what decides whether a person edited it. Compared
    as a multiset of lines (and `.PHONY` as a set of names), because the order its rules were listed
    in followed those meanings.
    """

    def rules(text: str) -> list[str]:
        out: list[str] = []
        for line in text.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line.startswith(".PHONY:"):
                out.extend(f".PHONY: {name}" for name in line.split(":", 1)[1].split())
            else:
                out.append(line.rstrip())
        return sorted(out)

    return rules(a) == rules(b)


def _derive_targets(
    read: Callable[[str], bytes | None],
    recorded: Mapping[str, str],
    replace: frozenset[str],
    inputs: Inputs | None,
) -> tuple[dict[str, str], list[SetupFile]]:
    """`(table, entries)`: what the version 2 table says, read from the root files it replaces, and
    what the migration does to each of them.

    * A target the repository's OWN Makefile defines runs as `make <target>` — that Makefile is its
      build tool, and the table is what reaches it now (`legacymake.own_targets`).
    * A target an unedited `fleet.mk` rendered runs the stack's recipe as a shell command
      (`stacks.target_commands`), and `fleet.mk` is deleted. A `fleet.mk` someone edited is KEPT,
      like every hand edit (`replace` overrides), and its targets run as `make <target>` through
      the Makefile's include, which is then kept too.
    * Fleet's stub Makefile is deleted (unless a kept `fleet.mk` still needs it); a Makefile of the
      repository's own loses Fleet's include of `fleet.mk` and nothing else.
    * A target that was only ever a stub refusal is left unconfigured: it renders as the same refusal.
    """
    makefile, mk = read(MAKEFILE), read(FLEET_MK)
    mf_text = makefile.decode("utf-8", "replace") if makefile is not None else None
    stub = mf_text is not None and legacymake.is_fleet_stub(mf_text)
    own = legacymake.own_targets(mf_text)
    values = {t: legacymake.make_value(t) for t in targetsmod.TARGETS if t in own}
    entries: list[SetupFile] = []
    choices: Sequence[stackmod.Choice] = inputs.stacks if inputs is not None else ()
    keep_mk = False
    if mk is not None:
        mk_text = mk.decode("utf-8", "replace")
        # What the release before the table rendered for these stacks, against the same Makefile.
        elsewhere = legacymake.targets_of(mf_text or "") - legacymake.stub_refusals(mf_text or "")
        fleet_wrote = bool(choices) and (
            commandsync.blob_sha(mk) == recorded.get(FLEET_MK)
            or _same_rules(mk_text, stackmod.render_fleet_mk(choices, defined_elsewhere=elsewhere, meanings=_MEANINGS))
        )
        if fleet_wrote or FLEET_MK in replace:
            rendered = stackmod.target_commands(choices, own=values, params=_PARAMS)
            values.update({t: v for t, v in rendered.items() if t in targetsmod.TARGETS})
            entries.append(
                SetupFile(
                    FLEET_MK,
                    "legacy",
                    "will-update",
                    "delete",
                    f"Fleet rendered {FLEET_MK} from the stack profiles; its recipes move into `[fleet.targets]` "
                    f"in {FLEET_TOML} as shell commands, and the file is deleted",
                    mk,
                    remove=True,
                )
            )
        else:
            keep_mk = True
            kept = sorted((legacymake.targets_of(mk_text) & frozenset(targetsmod.TARGETS)) - own)
            values.update({t: legacymake.make_value(t) for t in kept})
            entries.append(
                SetupFile(
                    FLEET_MK,
                    "legacy",
                    "hand-edited",
                    "none",
                    f"{FLEET_MK} was changed since Fleet wrote it (or no record says which stacks it was rendered "
                    "for), so the sync keeps it and the table runs its targets as `make <target>`; move its recipes "
                    f"into `[fleet.targets]` and delete it and the Makefile's include of it, or ask the sync to "
                    "replace it",
                    mk,
                )
            )
    elif choices:
        # The record names stacks whose fleet.mk is gone: the release before would have written it again.
        rendered = stackmod.target_commands(choices, own=values, params=_PARAMS)
        values.update({t: v for t, v in rendered.items() if t in targetsmod.TARGETS})
    if makefile is not None and mf_text is not None:
        if stub and not keep_mk:
            entries.append(
                SetupFile(
                    MAKEFILE,
                    "legacy",
                    "will-update",
                    "delete",
                    "this is the stub Makefile Fleet wrote — refusals and Fleet's own validate-knowledge recipe, "
                    f"nothing of this repository's — and `[fleet.targets]` in {FLEET_TOML} replaces it, "
                    "so it is deleted",
                    makefile,
                    remove=True,
                )
            )
        elif stub:
            entries.append(
                SetupFile(
                    MAKEFILE,
                    "legacy",
                    "skipped",
                    "none",
                    f"Fleet's stub Makefile stays while the edited {FLEET_MK} it includes stays",
                    makefile,
                )
            )
        elif not keep_mk and legacymake.includes_fleet_mk(mf_text):
            entries.append(
                SetupFile(
                    MAKEFILE,
                    "legacy",
                    "will-update",
                    "edit",
                    f"this Makefile is the repository's own and is kept; the sync takes out only Fleet's "
                    f"`{legacymake.INCLUDE_LINE}` (and the comment Fleet wrote above it), since {FLEET_MK} is deleted",
                    makefile,
                    legacymake.without_fleet_include(mf_text).encode("utf-8"),
                )
            )
        else:
            named = ", ".join(sorted(own)) or "none of the conventional targets"
            entries.append(
                SetupFile(
                    MAKEFILE,
                    "legacy",
                    "up-to-date",
                    "none",
                    f"the repository's own Makefile, left as it is; the table runs the targets it defines as "
                    f"`make <target>` ({named})",
                    makefile,
                )
            )
    return values, entries


def _plan_config(
    read: Callable[[str], bytes | None],
    recorded: Mapping[str, str],
    replace: frozenset[str],
    inputs: Inputs | None,
    skip: frozenset[str],
) -> tuple[list[SetupFile], dict[str, str] | None]:
    """`(entries, targets)`: the configuration's place and schema, and the table it carries after.

    Version 2 is the move to `.fleet/` and the `[fleet.targets]` table, and both happen in the one
    sync: a root `fleet.toml` is deleted where `.fleet/fleet.toml` is created from it (its text
    kept, the table added), and the root files the table replaces are cleaned up
    (`_derive_targets`). A repository with no configuration at all gets one, holding only the
    version and the table, because the tier it receives resolves every target from it.
    """
    new, old = read(FLEET_TOML), read(LEGACY_FLEET_TOML)
    if new is not None and old is not None:
        return [
            SetupFile(
                LEGACY_FLEET_TOML,
                "config",
                "skipped",
                "none",
                f"both {FLEET_TOML} and {LEGACY_FLEET_TOML} exist, and Fleet will not pick one silently — merge what "
                f"you need into {FLEET_TOML} and delete {LEGACY_FLEET_TOML}",
                old,
            )
        ], None
    current, path = (new, FLEET_TOML) if new is not None else (old, LEGACY_FLEET_TOML)
    if current is not None and (FLEET_TOML in skip or LEGACY_FLEET_TOML in skip):
        text = current.decode("utf-8", "replace")
        detail = f"listed in `[fleet.setup] skip`, so the sync leaves {path} (and the files it would fold in) alone"
        try:
            table: dict[str, str] | None = _table_of(text, path)
        except ValueError:
            table = None
        return [SetupFile(path, "config", "skipped", "none", detail, current)], table
    if current is None:
        pyproject = read(configmod.PYPROJECT_FILENAME)
        located = (
            configmod.config_table(pyproject.decode("utf-8", "replace"), Path(configmod.PYPROJECT_FILENAME))
            if pyproject is not None
            else None
        )
        if located is not None:
            raw = located.get("targets")
            table = targetsmod.read_table(raw, configmod.PYPROJECT_FILENAME) if raw is not None else {}
            detail = "the configuration is in pyproject.toml, which Fleet does not edit"
            if raw is None:
                detail += (
                    "; add a `[tool.fleet.targets]` table naming what each conventional target runs here, or every "
                    "target the commands name reads as a refusal"
                )
            return [SetupFile(FLEET_TOML, "config", "skipped", "none", detail)], table
    text = current.decode("utf-8", "replace") if current is not None else ""
    try:
        version = fleet_toml_version(text)
    except ValueError as exc:
        return [SetupFile(path, "config", "skipped", "none", f"{path} is not migrated: {exc}", current)], None
    entries: list[SetupFile] = []
    context = MigrationContext()
    if version < 2:
        values, entries = _derive_targets(read, recorded, replace, inputs)
        context = MigrationContext(values)
    try:
        if current is None:
            migrated = _NEW_CONFIG_HEAD + targetsmod.table_block(context.targets)
            steps = [f"version {FLEET_TOML_VERSION}: written with the [fleet.targets] table"]
        else:
            migrated, steps = migrate_fleet_toml(text, context)
    except ValueError as exc:
        return [SetupFile(path, "config", "skipped", "none", f"{path} is not migrated: {exc}", current)], None
    table = _table_of(migrated, FLEET_TOML)
    if current is None:
        entries.insert(
            0,
            SetupFile(
                FLEET_TOML,
                "config",
                "missing",
                "create",
                f"there is no Fleet configuration here; the sync writes {FLEET_TOML} holding only its schema version "
                "and the `[fleet.targets]` table the commands resolve their targets from",
                None,
                migrated.encode("utf-8"),
            ),
        )
    elif path == LEGACY_FLEET_TOML:
        entries[:0] = [
            SetupFile(
                LEGACY_FLEET_TOML,
                "config",
                "will-update",
                "move",
                f"Fleet's configuration moves to {FLEET_TOML}; the root file is deleted",
                current,
                remove=True,
            ),
            SetupFile(
                FLEET_TOML,
                "config",
                "missing",
                "create",
                f"{LEGACY_FLEET_TOML} moved here, its values and comments kept"
                + (": " + "; ".join(steps) if steps else ""),
                None,
                migrated.encode("utf-8"),
            ),
        ]
    elif steps:
        entries.insert(
            0,
            SetupFile(
                FLEET_TOML,
                "config",
                "will-update",
                "migrate",
                f"the sync upgrades {FLEET_TOML} in place, keeping your values and comments: " + "; ".join(steps),
                current,
                migrated.encode("utf-8"),
            ),
        )
    else:
        entries.insert(
            0,
            SetupFile(
                FLEET_TOML,
                "config",
                "up-to-date",
                "none",
                f"{FLEET_TOML} is on schema version {FLEET_TOML_VERSION}",
                current,
            ),
        )
    return entries, table


def _plan_settings(read: Callable[[str], bytes | None], namespace: str) -> SetupFile:
    data = read(SETTINGS)
    if data is None:
        return SetupFile(
            SETTINGS,
            "settings",
            "missing",
            "none",
            "there is no .claude/settings.json, so people's own sessions load the commands only if each opts in",
        )
    try:
        doc = json.loads(data.decode("utf-8") or "{}")
    except (UnicodeDecodeError, ValueError):
        return SetupFile(SETTINGS, "settings", "skipped", "none", ".claude/settings.json is not valid JSON", data)
    if not isinstance(doc, dict):
        return SetupFile(SETTINGS, "settings", "skipped", "none", ".claude/settings.json is not a JSON object", data)
    wanted = commandsync.optin_settings(namespace)
    market = commandsync.MARKETPLACE_NAME
    suffix = f"@{market}"
    plugins = doc.get("enabledPlugins")
    markets = doc.get("extraKnownMarketplaces")
    ours = [k for k in plugins if isinstance(k, str) and k.endswith(suffix)] if isinstance(plugins, dict) else []
    opted_in = bool(ours) or (isinstance(markets, dict) and market in markets)
    if not opted_in:
        return SetupFile(
            SETTINGS,
            "settings",
            "skipped",
            "none",
            "this repository has not turned the commands on for people's own sessions, and an update never "
            "does it for you",
            data,
        )
    merged = json.loads(json.dumps(doc))
    merged_markets = merged.get("extraKnownMarketplaces")
    if not isinstance(merged_markets, dict):
        merged_markets = merged["extraKnownMarketplaces"] = {}
    wanted_markets = wanted["extraKnownMarketplaces"]
    merged_markets[market] = wanted_markets[market] if isinstance(wanted_markets, dict) else {}
    merged_plugins = merged.get("enabledPlugins")
    if not isinstance(merged_plugins, dict):
        merged_plugins = merged["enabledPlugins"] = {}
    key = f"{namespace}{suffix}"
    # A key under another namespace is the same opt-in from before a rename: carried over with its
    # value, so a repository that switched the commands OFF (`false`) keeps them off.
    carried = [merged_plugins.pop(k) for k in ours if k != key]
    if key not in merged_plugins:
        merged_plugins[key] = carried[0] if carried else True
    if merged == doc:
        return SetupFile(SETTINGS, "settings", "up-to-date", "none", "Fleet's two settings are current", data)
    indent = _json_indent(data)
    proposed = (json.dumps(merged, indent=indent, ensure_ascii=False) + "\n").encode("utf-8")
    return SetupFile(
        SETTINGS,
        "settings",
        "will-update",
        "merge",
        "the sync updates Fleet's two settings (where the commands load from, and which plugin is on); "
        "every other setting is kept",
        data,
        proposed,
    )


def _json_indent(data: bytes) -> int:
    m = re.search(rb"\n( +)\S", data)
    return len(m.group(1)) if m else 2


# ── the CI template ──────────────────────────────────────────────────────────


def _inputs_from_files(read: Callable[[str], bytes | None]) -> Inputs | None:
    """The stacks read back from a `fleet.mk` a release before the record wrote, or `None`."""
    mk = read(FLEET_MK)
    if mk is None:
        return None
    choices = stackmod.choices_from_fleet_mk(mk.decode("utf-8", "replace"))
    if not choices:
        return None
    ci = read(stackmod.CI_WORKFLOW)
    runner = stackmod.runner_from_ci(ci.decode("utf-8", "replace")) if ci is not None else ""
    return Inputs(tuple(choices), runner)


def _plan_ci_files(
    read: Callable[[str], bytes | None],
    recorded: Mapping[str, str],
    replace: frozenset[str],
    inputs: Inputs,
    targets: Mapping[str, str],
) -> list[SetupFile]:
    """The CI template and its instructions, rendered from the stacks and the table's commands —
    so CI runs what `[fleet.targets]` says, and changing a command there changes the template."""
    choices: Sequence[stackmod.Choice] = inputs.stacks
    ci = stackmod.render_ci(choices, runner_label=inputs.ci_runner, commands=targets)
    out = [_whole(stackmod.CI_WORKFLOW, read(stackmod.CI_WORKFLOW), ci.encode("utf-8"), recorded, replace)]
    readme = stackmod.render_ci_readme(choices)
    out.append(_whole(stackmod.CI_README, read(stackmod.CI_README), readme.encode("utf-8"), recorded, replace))
    return out


_KEEP_ADVICE = {
    stackmod.CI_WORKFLOW: f"keep your changes in your committed copy ({stackmod.CI_TARGET}), which Fleet never touches",
    stackmod.CI_README: "keep your notes in a file of your own",
}


def _whole(
    path: str, current: bytes | None, proposed: bytes, recorded: Mapping[str, str], replace: frozenset[str]
) -> SetupFile:
    if current is None:
        return SetupFile(
            path,
            "whole-file",
            "missing",
            "create",
            f"{path} is missing; the sync writes it from the stacks this repository builds in and its table",
            None,
            proposed,
            commandsync.blob_sha(proposed),
        )
    state, record = _decide(path, current, proposed, recorded.get(path), replace)
    if state == "up-to-date":
        return SetupFile(path, "whole-file", state, "none", f"{path} matches this release", current, None, record)
    if state == "will-update":
        detail = (
            f"the sync replaces {path} with this release's version, over your edits as asked"
            if path in replace and commandsync.blob_sha(current) != recorded.get(path)
            else f"the sync refreshes {path} to this release's version"
        )
        return SetupFile(path, "whole-file", state, "replace", detail, current, proposed, record)
    never = "" if path in recorded else ", or was written before Fleet kept a record of it"
    return SetupFile(
        path,
        "whole-file",
        "hand-edited",
        "none",
        f"{path} was changed since Fleet wrote it{never}, so the sync leaves it; {_KEEP_ADVICE[path]}, "
        "or ask the sync to replace it",
        current,
        proposed,
        record or None,
    )
