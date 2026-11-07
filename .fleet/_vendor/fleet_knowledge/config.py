"""Where the knowledge base is, and what this project's corpus looks like.

Two objects, and everything else in the package takes one of them:

  * **`KnowledgeBase`** — a resolved corpus: the repository root, the `knowledge/` directory
    inside it, and the options that describe it. Nothing in this package reads a path that
    did not come from here.
  * **`Config`** — the per-project options, every one with a default that works. A corpus
    without journeys, without a todo register, without Linear is not a broken corpus; it is a
    smaller one, and a check over ground it does not have SKIPS rather than fails.

**Resolution is explicit and traceable.** The order below is fixed, first hit wins, and every
value remembers where it came from — because the second question anyone asks after "which
corpus did it read?" is "why that one?", and a tool that cannot answer it turns a wrong root
into an afternoon. `fleet config` prints both.

    1. --knowledge-dir / -k          the flag always wins
    2. $KNOWLEDGE_DIR               the corpus directory
    3. $FLEET_ROOT          the repository root; knowledge/ beneath it
    4. a .env found by walking up   same keys; PROCESS ENV WINS OVER .env
    5. .fleet/fleet.toml, or [tool.fleet] in a pyproject.toml, found upward
    6. upward discovery             the nearest ancestor holding knowledge/programs.md

Process env beating `.env` is not a preference — it is what every other tool in a checkout
already does, and a `.env` that silently overrode an exported variable would make a one-off
`KNOWLEDGE_DIR=… fleet check` a lie.

**Options come in two tiers.** The top level of the config table is the CORPUS SHAPE — which
registers exist, where they live, which id prefixes they own — and it is a closed set, so a
misspelled key is refused rather than ignored. Everything a single check family owns lives in
that family's own table:

    [fleet]                     # or [tool.fleet] in a pyproject.toml
    programs_register = "objectives.md"

    [fleet.planning]            # PlanningConfig's vocabulary
    active_slice_ceiling = 8

    [fleet.commitments]         # CommitmentsConfig's vocabulary
    current_line = "r1"

    [fleet.structure]           # the structure family's `option()` vocabulary
    hygiene_doc_parity = []

Each section is checked against its own family's option names, exactly as the top level is
checked against `Config`'s — the strictness is what makes a typo loud, and it would be a
strange contract if it stopped at the section boundary.

Stdlib only.
"""

from __future__ import annotations

import os
import re
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from .paths import DEFAULT_DIR_NAME

# The file that marks a directory as a knowledge base for upward discovery. A register, not a
# directory name: an empty `knowledge/` beside a real one upstream would otherwise capture the
# search and every reading would come back empty with nothing to explain it.
DISCOVERY_MARKER = "programs.md"

CONFIG_FILENAME = "fleet.toml"
#: Where a repository keeps it: under `.fleet/`, beside the tier, so Fleet writes nothing at the
#: repository root. Paths the file names (`knowledge_dir`, …) stay relative to the REPOSITORY ROOT
#: — the directory holding `.fleet/` — exactly as they were when the file sat there (`config_base`).
CONFIG_DIR = ".fleet"
CONFIG_REL = f"{CONFIG_DIR}/{CONFIG_FILENAME}"
#: The root location every release before the `.fleet/` move wrote. Still READ for one release, so
#: a repository keeps working until `fleet commands sync` moves the file (`setupfiles`); `fleet
#: check` reports it (`checks/slots/_layout.py`). The next release reads only `CONFIG_REL`.
#:
#: THE RELEASE THAT DELETES THIS READ ALSO FLIPS TWO LEVELS TO "error": `_layout.LAYOUT_LEVEL`
#: (`fleet-layout`) and `_portability.LEGACY_MAKE_LEVEL` (a conventional literal `make` left in a tier
#: synced before `[fleet.targets]`). Both are warnings for exactly one release so a repository whose
#: Apply Fleet pull request is not merged yet does not fail every agent's pre-push gate the moment its
#: install upgrades; `test_fleet_toml_targets.py::test_the_transition_levels_flip_with_the_legacy_read`
#: holds the three together.
LEGACY_CONFIG_REL = CONFIG_FILENAME
PYPROJECT_FILENAME = "pyproject.toml"
PYPROJECT_TABLE = ("tool", "fleet")
DOTENV_FILENAME = ".env"

ENV_KNOWLEDGE_DIR = "KNOWLEDGE_DIR"
ENV_ROOT = "FLEET_ROOT"

# The per-family option namespaces. A key in one of these tables is checked against THAT
# family's vocabulary, never against the top level's — which is why `[tool.fleet]`
# can stay a closed set of corpus-shape options while a family carries ninety of its own.
#
# The name of a section is the name of the check package under `fleet_knowledge/checks/`, so
# there is nothing to keep in sync: `section_options` resolves the vocabulary by importing
# that package. A family with no section here is a family with no options — not a family
# whose options are silently ignored.
SECTIONS: tuple[str, ...] = (
    "planning",
    "commitments",
    "structure",
    "slots",
    "recurring",
    "commands",
    "setup",
    "session",
    "targets",
)

#: The `[fleet.commands]` vocabulary (PRD 0746 D1/D3). `namespace` is the command prefix
#: a repository's commands are addressed under (undeclared renders the tree's home copy under its
#: source namespace; ANY declared namespace, the source's own included, is a customer render with
#: the home-only text dropped — `commandsync.render`); `set` is `core` or
#: `all` (undeclared is `all`); `layout` is `claude` or `plugin`, where the tier is written
#: (`commandsync`). Kept here rather than in a `checks/` family because the section names a
#: property of the tree, not a gate.
COMMANDS_OPTIONS: frozenset[str] = frozenset({"namespace", "set", "layout"})

#: The `[fleet.setup]` vocabulary: `skip`, the setup files (`CLAUDE.md`, the CI template, …) that
#: `fleet commands sync` must leave entirely alone in this repository (`setupfiles`).
SETUP_OPTIONS: frozenset[str] = frozenset({"skip"})

#: The `[fleet.session]` vocabulary: what a worker must do before it opens a session for this
#: repository. `setup` names a script in the repository that installs the extra tools the build
#: needs (a JDK, Maven, an internal CLI), and `timeout_seconds` bounds how long it may run.
#:
#: The daemon does not import this package (it reads no corpus), so the same two keys are read
#: from the same file by `fleet_daemon.session_setup`. Their names and their rules are stated
#: here because this is the vocabulary every other reader of `fleet.toml` validates against.
SESSION_OPTIONS: frozenset[str] = frozenset({"setup", "timeout_seconds"})

# A `.env` line: `KEY=value`, `export KEY=value`, `#` comments, optional surrounding quotes.
DOTENV_LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


class ConfigError(RuntimeError):
    """A configuration file or environment value that cannot be used as given."""


@dataclass(frozen=True)
class Origin:
    """Where one resolved value came from.

    `kind` is one of `flag`, `env`, `dotenv`, `toml`, `discovery`, `default`; `detail` names
    the exact source — the flag, the variable, the file. Both are printed verbatim, so a
    reader never has to guess which of five layers won.
    """

    kind: str
    detail: str = ""

    def __str__(self) -> str:
        return f"{self.kind}: {self.detail}" if self.detail else self.kind


DEFAULT = Origin("default", "built-in")


@dataclass(frozen=True)
class Config:
    """Per-project options describing the corpus. Every field has a working default.

    Paths are RELATIVE to the knowledge directory unless the field name says otherwise, so a
    project reshapes its corpus by naming files here rather than by patching a reader.
    """

    # ── the registers ────────────────────────────────────────────────────────
    # Each is a path relative to the knowledge directory. Set one to "" to declare that this
    # corpus does not have it: a check over ground that does not exist must skip, not fail.
    programs_register: str = "programs.md"
    slices_register: str = "slices.md"
    todos_register: str = "todos.md"
    requirements_dir: str = "requirements"
    features_dir: str = "features"
    journeys_dir: str = "journeys"
    prds_dir: str = "prds"
    programs_detail_dir: str = "programs"
    slices_detail_dir: str = "slices"
    # Where drill records live — the second kind of proof a `Verified by` may name
    # (`drill:<stem>` -> `<drills_dir>/<stem>.md`). "" declares the corpus keeps none, and a
    # `drill:` entry then resolves to nothing, which reads unshipped rather than as an error.
    drills_dir: str = "drills"
    components_registry: str = "specs/architecture/components.md"
    # Where decision records live. Already a `CommitmentsConfig` option (the register cites
    # THESE, not the other way round, so the verbatim-restatement check exempts them); stated
    # here too, and shared, so the reader that serves decisions as entities and the check that
    # exempts them cannot be pointed at two different directories.
    decisions_dir: str = "decisions"
    glossary: str = "specs/glossary.md"
    capability_aliases: str = "capability-aliases.md"
    coverage_ledger: str = "audits/feature-coverage-ledger.md"

    # ── id namespaces ────────────────────────────────────────────────────────
    program_prefix: str = "PG"
    slice_prefix: str = "SL"
    capability_prefix: str = "CAP"
    todo_prefix: str = "TODO"
    # Requirement prefixes are DISCOVERED, not configured: each register declares the
    # namespace it owns in its own frontmatter (`prefix: RUN`), which is what lets a second
    # domain register land with no code change. Listing them here would be a second copy that
    # goes stale. This is the escape hatch for a corpus that needs to constrain the set.
    requirement_prefixes: tuple[str, ...] = ()
    # Namespaces a register may NOT claim, because something else already writes ids of that
    # shape. The default is an issue-tracker team key.
    reserved_prefixes: tuple[str, ...] = ("ENG",)

    # ── the board's own vocabulary ───────────────────────────────────────────
    # Repo-root-relative (like `baseline_dir`, and unlike every path above it) path to this
    # corpus's command vocabulary: the catalogue, the scan, the per-view boxes, the runnable
    # command each finding names, and the pipeline. `""` means this corpus declares none, and
    # the board then renders in neutral words with rows that carry no command — honest rather
    # than degraded, and the same answer it gives a corpus that has no commands.
    #
    # **IT IS A PROPERTY OF THE CORPUS, WHICH IS THE WHOLE POINT.** The commands a board prints
    # belong to the repository the board is pointed at: they are added, renamed and deleted by
    # commits in it, so a board at commit X must print commit X's commands. Supplying them as
    # deployment configuration instead made them a property of whatever the server was last
    # restarted with, and the two drifted in production — a renamed command surface left the
    # deployed copy naming 33 commands that no longer existed, every run button firing one of
    # them, and the cross-check that exists to notice reading `scanned: false` because the scan
    # directory it was handed had been deleted in the same rename.
    #
    # A PATH RATHER THAN THE DOCUMENT INLINE. The vocabulary is ~12KB of prose about commands
    # and belongs beside them in the repository, where it is reviewed with the commands it
    # describes; `fleet.toml` says where it is, exactly as it says where the programs register
    # is. Read with `Mirror.read_file` at the commit, so nothing extracts a tree for it.
    board_guidance: str = ""

    # ── integrations ─────────────────────────────────────────────────────────
    # Off by default. A check that needs an issue tracker skips when this is false, so the
    # package never reaches for a network or a key it was not told about.
    linear_enabled: bool = False

    # ── checks ───────────────────────────────────────────────────────────────
    # Names of checks this project does not run. A disabled check is reported as disabled,
    # never silently dropped — a gate nobody is told about is not a gate.
    disabled_checks: tuple[str, ...] = ()
    # Where ratchet baselines live, relative to the REPO root (not the knowledge directory):
    # a baseline is a property of the checkout, not of the corpus.
    baseline_dir: str = "."

    # ── the per-family sections ──────────────────────────────────────────────
    # The fields above describe the corpus and are read by everything. Each check family
    # additionally owns ~30–90 options that mean nothing outside it — a register's column
    # list, a rule cutover, an ignore prefix, the remediation paragraph a finding prints. A
    # flat `Config` carrying all of them would be a 200-field object in which the fifteen
    # that describe the corpus are invisible, and every family's vocabulary would have to be
    # merged into one namespace where `prds_dir` and `arch_specs_dir` sit side by side.
    #
    # So each family gets a NAMESPACE, filled from `[tool.fleet.<family>]`, and the
    # family's own config object (`PlanningConfig`, `CommitmentsConfig`, the structure
    # family's `option()` lookup) reads it. Keys inside a section are checked against that
    # family's vocabulary exactly as the top level checks its own — see `section_options`.
    #
    # A section may also RE-STATE a top-level option (`prds_dir` in `[…structure]`), and the
    # section wins for that family. That is what a corpus needs when one family's ground is
    # shaped differently from the rest; it is not the common case.
    planning: Mapping[str, Any] = field(default_factory=dict)
    commitments: Mapping[str, Any] = field(default_factory=dict)
    structure: Mapping[str, Any] = field(default_factory=dict)
    # MISSING UNTIL NOW, while `SECTIONS` above has named it since the family shipped. The
    # slots family declared its vocabulary (`KNOWN_OPTIONS`), `section_options` validated
    # it, and `option()` read it — every part of the path existed except somewhere to put
    # the value, so `config_from_table` reached `Config(**values)` with a `slots=` keyword
    # no field accepted and raised `TypeError` on any config that wrote the table. The
    # option was not merely defaulted; it was UNREACHABLE, and the only way to discover
    # that was to write it and watch the resolver crash.
    slots: Mapping[str, Any] = field(default_factory=dict)
    # The recurring-work schedule a watched repository declares for the Fleet service to file
    # from (`[fleet.recurring]`, the only key being `entries`). Carried RAW: per-entry
    # validation belongs to the scheduler's reader and to the `recurring` check, because a bad
    # entry must be reported and skipped, never allowed to red the whole corpus parse.
    recurring: Mapping[str, Any] = field(default_factory=dict)
    # The command-rendering configuration a repository declares for itself (PRD 0746 D1/D3):
    # `[fleet.commands] namespace = "acme"`, `set = "core"|"all"`. Carried RAW; `commandsync`
    # owns validation so a bad value is a render refusal naming the rule, not a config crash.
    commands: Mapping[str, Any] = field(default_factory=dict)
    # What `fleet commands sync` may refresh beyond the tier (`[fleet.setup] skip = [...]`).
    # Carried RAW; `setupfiles` reads it.
    setup: Mapping[str, Any] = field(default_factory=dict)
    # What a worker runs before a session for this repository (`[fleet.session] setup = "..."`).
    # Carried RAW; the daemon's `session_setup` reader owns the rules, and a repository that
    # declares no hook is the ordinary case.
    session: Mapping[str, Any] = field(default_factory=dict)
    # What each conventional target runs in this repository (`[fleet.targets] lint = "…"`): the
    # commands the sync writes into the tier where it names a target. CHECKED, unlike the two
    # tables above, because a value that cannot render is a gate step that silently is not one —
    # `targets.read_table` refuses an unknown name and a value missing its placeholder.
    targets: Mapping[str, Any] = field(default_factory=dict)

    # Per-key provenance, filled in by `resolve`. Excluded from equality so two configs with
    # the same values compare equal however they were assembled.
    origins: Mapping[str, Origin] = field(default_factory=dict, compare=False, repr=False)

    @classmethod
    def field_names(cls) -> tuple[str, ...]:
        """The FLAT options — the ones that describe the corpus, one value each.

        Sections are excluded deliberately: they are tables, not values, and everything that
        walks this list (the option table `fleet config` prints, `as_dict`) is about
        scalar options with one origin apiece.
        """
        skip = {"origins", *SECTIONS}
        return tuple(f.name for f in fields(cls) if f.name not in skip)

    @classmethod
    def section_names(cls) -> tuple[str, ...]:
        return SECTIONS

    def origin(self, name: str) -> Origin:
        return self.origins.get(name, DEFAULT)

    def section(self, name: str) -> Mapping[str, Any]:
        """One family's option table. `{}` when this project set none."""
        value = getattr(self, name, None)
        return value if isinstance(value, Mapping) else {}

    def as_dict(self) -> dict[str, Any]:
        return {n: getattr(self, n) for n in self.field_names()}


def _coerce(name: str, value: Any, current: Any) -> Any:
    """A TOML value in the shape the field expects, or a `ConfigError` naming the mismatch."""
    if isinstance(current, tuple):
        if isinstance(value, str) or not isinstance(value, Iterable):
            raise ConfigError(f"`{name}` must be a list of strings, got {value!r}")
        return tuple(str(x) for x in value)
    if isinstance(current, bool):
        if not isinstance(value, bool):
            raise ConfigError(f"`{name}` must be true or false, got {value!r}")
        return value
    if not isinstance(value, str):
        raise ConfigError(f"`{name}` must be a string, got {value!r}")
    return value


# Keys a config table may carry that are NOT options: `knowledge_dir` points the tool at the
# corpus and is consumed by `resolve` before the options are read. Named here so a typo in a
# real option is still refused — the unknown-key check is what makes a misspelling loud.
# `version` is the file's own schema version, which `setupfiles` reads and migrates; it describes
# the file, not the corpus.
NON_OPTION_KEYS = frozenset({"knowledge_dir", "version"})


def section_options(section: str) -> frozenset[str] | None:
    """The option names a family's section accepts, or None when that family is not installed.

    Resolved by importing the family rather than by keeping a list here, because a list here
    is a second copy of a vocabulary that changes every time a check grows an option — and a
    stale copy refuses a key the family would happily have read. Imported LAZILY: every check
    family imports this module, so a top-level import would be a cycle.

    `None` (family not importable) means "cannot check this section", and the section is then
    passed through unvalidated. That is the honest answer: a section for a family that is not
    here configures nothing either way, and refusing it would fail a config for a check the
    reader never asked to run.
    """
    try:
        if section == "planning":
            from .checks.planning._config import PlanningConfig  # noqa: PLC0415 — see docstring

            return frozenset(f.name for f in fields(PlanningConfig))
        if section == "commitments":
            from .checks.commitments.options import CommitmentsConfig  # noqa: PLC0415

            return frozenset(f.name for f in fields(CommitmentsConfig))
        if section == "structure":
            from .checks.structure._kit import KNOWN_OPTIONS  # noqa: PLC0415

            return KNOWN_OPTIONS
        if section == "slots":
            from .checks.slots import KNOWN_OPTIONS as SLOT_OPTIONS  # noqa: PLC0415

            return SLOT_OPTIONS
        if section == "recurring":
            from .checks.recurring import KNOWN_OPTIONS as RECURRING_OPTIONS  # noqa: PLC0415

            return RECURRING_OPTIONS
        if section == "commands":
            return COMMANDS_OPTIONS
        if section == "setup":
            return SETUP_OPTIONS
        if section == "session":
            return SESSION_OPTIONS
        if section == "targets":
            from .targets import TARGETS  # noqa: PLC0415 — see docstring

            return frozenset(TARGETS)
    except ImportError:
        return None
    return None


def section_from_table(name: str, raw: Any, source: Path) -> dict[str, Any]:
    """One `[tool.fleet.<name>]` table, with its keys checked against the family's set.

    Strict for exactly the reason the top level is strict: an unrecognised key is almost
    always a misspelling of a real one, and a silently ignored option looks identical to an
    option that had no effect — the failure mode that costs an afternoon. Values are NOT
    coerced here; each family shapes its own (a `frozenset` field takes a TOML list, a
    `Mapping` field takes a TOML table), and a second coercion here would have to guess.
    """
    if not isinstance(raw, Mapping):
        raise ConfigError(
            f"{source}: `{name}` must be a table of options — write `[{name}]` in a "
            f"{CONFIG_FILENAME} (or `[tool.fleet.{name}]` in a pyproject.toml), got {raw!r}"
        )
    if name == "targets":
        from .targets import TargetError, read_table  # noqa: PLC0415 — see `section_options`

        try:
            return read_table(raw, source)
        except TargetError as exc:
            raise ConfigError(str(exc)) from exc
    known = section_options(name)
    if known is not None:
        unknown = sorted(set(raw) - known)
        if unknown:
            raise ConfigError(
                f"{source}: unknown `{name}` option(s) {', '.join(unknown)} — "
                f"known options are {', '.join(sorted(known))}"
            )
    if name == "planning":
        # The corpus declarations are VALUES the resolver acts on, and a reserved or malformed
        # name would surface as a resolution error at every citing site instead of once here.
        from .corpusref import CorpusConfigError, validate_planning_table  # noqa: PLC0415 — see `section_options`

        try:
            validate_planning_table(raw)
        except CorpusConfigError as exc:
            raise ConfigError(f"{source}: [planning] {exc}") from exc
    return dict(raw)


def config_from_table(table: Mapping[str, Any], source: Path) -> Config:
    """A `Config` from a parsed `[fleet]` table, with provenance on each key set."""
    known = set(Config.field_names())
    unknown = sorted(set(table) - known - NON_OPTION_KEYS - set(SECTIONS))
    if unknown:
        raise ConfigError(
            f"{source}: unknown option(s) {', '.join(unknown)} — known options are "
            f"{', '.join(sorted(known))}. An option belonging to one check family goes in that "
            f"family's own table instead: {', '.join(f'[{s}]' for s in SECTIONS)}"
        )
    base = Config()
    values: dict[str, Any] = {}
    origins: dict[str, Origin] = {}
    for name, raw in table.items():
        if name in NON_OPTION_KEYS:
            continue
        if name in SECTIONS:
            values[name] = section_from_table(name, raw, source)
        else:
            values[name] = _coerce(name, raw, getattr(base, name))
        origins[name] = Origin("toml", str(source))
    config = Config(**values, origins=origins)
    if isinstance(values.get("planning"), Mapping):
        # Again with the RESOLVED config: the id prefixes a sibling corpus may not own
        # (`program_prefix`, `reserved_prefixes`, …) are top-level keys, not planning ones.
        from .corpusref import CorpusConfigError, validate_planning_table  # noqa: PLC0415 — see `section_options`

        try:
            validate_planning_table(values["planning"], config)
        except CorpusConfigError as exc:
            raise ConfigError(f"{source}: [planning] {exc}") from exc
    return config


def _walk_up(start: Path) -> list[Path]:
    start = start.resolve()
    return [start, *start.parents]


def read_dotenv(path: Path) -> dict[str, str]:
    """A `.env` as a plain mapping. Never executed, never exported into the process."""
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return out
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = DOTENV_LINE_RE.match(line)
        if not m:
            continue
        value = m.group(2)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[m.group(1)] = value
    return out


def find_dotenv(start: Path) -> Path | None:
    for d in _walk_up(start):
        p = d / DOTENV_FILENAME
        if p.is_file():
            return p
    return None


def config_table(text: str, source: Path) -> Mapping[str, Any] | None:
    """The option table inside one config file's TEXT, or `None` when it carries none.

    Split out from the walk below because the corpus is not always a directory somebody can
    walk. `fleet-service` reads this file as a BLOB out of a git repository at a commit — the
    corpus describes its own shape, and the shape of commit X belongs to commit X — and a
    reader that could only take a path would have made it either write the blob to disk first
    or grow a second, quietly divergent parser. There is one parser, and this is it.

    `source` is only ever a NAME here: it goes into the error messages, so a refusal points at
    the file the reader would have to edit rather than at a temporary path.
    """
    if source.name == PYPROJECT_FILENAME:
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            return None  # somebody else's file; a broken one is their build's problem
        table: Any = data
        for key in PYPROJECT_TABLE:
            if not isinstance(table, Mapping) or key not in table:
                return None
            table = table[key]
        return table if isinstance(table, Mapping) else None

    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{source}: not valid TOML — {exc}") from exc
    # Accept both a bare table and a `[fleet]` section, because both readings
    # of the filename are reasonable and guessing wrong is a silent no-op.
    nested = data.get("fleet")
    if isinstance(nested, Mapping):
        # ...but not BOTH. `[fleet.planning]` written above bare top-level
        # keys parses as a `fleet` table holding only `planning`, and every
        # bare key would be silently dropped — a corpus reading its defaults with a
        # config file sitting right there. Refused, naming the two spellings.
        strays = sorted(set(data) - {"fleet"})
        if strays:
            raise ConfigError(
                f"{source}: mixes two spellings — {', '.join(strays)} at the top level and a "
                "`[fleet]` table alongside. Everything outside that table would be "
                "silently ignored. Pick one: drop the `fleet.` prefix everywhere "
                "(sections become `[planning]`, `[commitments]`, `[structure]`), or move "
                "every option under `[fleet]`."
            )
        return nested
    return data


def config_base(config_path: Path) -> Path:
    """The directory the paths inside `config_path` are relative to: the repository root.

    The directory holding the file — except for `.fleet/fleet.toml`, whose paths are relative to
    the directory holding `.fleet/`, so moving the file there changed none of the values in it.
    """
    parent = config_path.parent
    if config_path.name == CONFIG_FILENAME and parent.name == CONFIG_DIR:
        return parent.parent
    return parent


def config_files_in(d: Path) -> list[Path]:
    """The config files directory `d` holds: `.fleet/fleet.toml`, then the legacy root `fleet.toml`.

    Both present is REFUSED: one of them would be silently ignored, and which one is exactly what a
    reader would have to guess. `fleet commands sync` never leaves both (it moves the root file).
    """
    found = [p for p in (d / CONFIG_REL, d / LEGACY_CONFIG_REL) if p.is_file()]
    if len(found) == 2:
        raise ConfigError(
            f"{d}: both {CONFIG_REL} and {LEGACY_CONFIG_REL} exist — Fleet reads its configuration from "
            f"{CONFIG_REL} only and will not pick one silently. Keep {CONFIG_REL} (merge anything you need "
            f"from the root file into it) and delete {LEGACY_CONFIG_REL}"
        )
    return found


def find_config_file(start: Path) -> tuple[Path, Mapping[str, Any]] | None:
    """The nearest `.fleet/fleet.toml` (or, for one release, a root `fleet.toml`), or a
    `pyproject.toml` carrying the tool table. Raises `ConfigError` where both files exist."""
    for d in _walk_up(start):
        for own in config_files_in(d):
            table = config_table(own.read_text(encoding="utf-8"), own)
            if table is not None:
                return own, table
        pyproject = d / PYPROJECT_FILENAME
        if pyproject.is_file():
            table = config_table(pyproject.read_text(encoding="utf-8"), pyproject)
            if table is not None:
                return pyproject, table
    return None


def discover_knowledge_dir(start: Path, dir_name: str = DEFAULT_DIR_NAME) -> Path | None:
    """The nearest ancestor's `knowledge/` — preferring one that holds the program register.

    Two passes on purpose. An empty or half-made `knowledge/` directory close to the cwd would
    otherwise capture the search from the real corpus above it, and every reading would come
    back empty with nothing on screen to explain why.
    """
    start = start.resolve()
    if start.is_dir() and start.name == dir_name and (start / DISCOVERY_MARKER).is_file():
        return start
    for d in _walk_up(start):
        candidate = d / dir_name
        if (candidate / DISCOVERY_MARKER).is_file():
            return candidate
    if start.is_dir() and start.name == dir_name:
        return start
    for d in _walk_up(start):
        candidate = d / dir_name
        if candidate.is_dir():
            return candidate
    return None


@dataclass(frozen=True)
class GitContext:
    """The revisions a history-dependent check compares against. Empty means "work it out".

    Five checks are history-dependent, and every one of them is WRONG when it guesses on a
    continuous-integration checkout. The clearest case is the id-collision check: a CI job
    builds its working tree from the *merge* ref, which has already absorbed the trunk, so a
    check left to infer `head` from the working tree compares the trunk against itself and can
    never report a collision. It does not fail — it goes quiet, which is worse.

    So the caller that KNOWS these revisions says them, and nothing is inferred behind its
    back:

      * `base` — the commit this change is measured against (a pull request's base sha). Scopes
        the two process-artifact gates to the artifacts this change actually touched, gives the
        statement lock its comparison point, and drives the architecture-doc sync advisory.
      * `head` — the branch head, for when the working tree is NOT it (the merge-ref checkout
        above).
      * `tip` — the trunk tip, which can see ids minted after this branch diverged. A merge
        base cannot, which is the whole reason it is a separate value.

    Every field defaults to "" and every reader falls back to what it did before — a local
    `fleet check` in a working checkout needs none of this, and passing nothing must
    keep behaving exactly as it did.
    """

    base: str = ""
    head: str = ""
    tip: str = ""

    def __bool__(self) -> bool:
        return bool(self.base or self.head or self.tip)


NO_GIT_CONTEXT = GitContext()


def git_context(kb: Any) -> GitContext:
    """The revisions `kb` was told to compare against, or none.

    Tolerant of a knowledge base that has never heard of the field, for the same reason
    `_kit.option` is tolerant of an old `Config`: a check must never fail because the object
    handed to it predates one of its keys.
    """
    ctx = getattr(kb, "git", None)
    return ctx if isinstance(ctx, GitContext) else NO_GIT_CONTEXT


@dataclass(frozen=True)
class KnowledgeBase:
    """A resolved corpus: the repository root, the knowledge directory, and the options."""

    root: Path
    knowledge: Path
    config: Config = field(default_factory=Config)
    # How the knowledge directory itself was chosen. Separate from `config.origins` because it
    # is the one value a reader checks first.
    origin: Origin = DEFAULT
    # The revisions the history-dependent checks compare against. Carried HERE rather than
    # threaded through `run()` because `Check.run(kb)` takes exactly one argument by design —
    # a check must never grow a bespoke signature, or the runner stops being able to run them
    # uniformly. See `GitContext`.
    git: GitContext = NO_GIT_CONTEXT

    def path(self, *parts: str) -> Path:
        """A path inside the corpus. `kb.path("prds", "0001-x", "prd.md")`."""
        return self.knowledge.joinpath(*parts)

    def read(self, rel: str | Path) -> str:
        """A corpus file's text. "" when it does not exist — absence is a normal answer here.

        `errors="ignore"` because a viewer must render what it can: one byte of mojibake in
        one file is not a reason for a whole report to abort.
        """
        p = self.knowledge / rel
        try:
            return p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""

    def glob(self, pattern: str) -> list[Path]:
        """Corpus paths matching `pattern`, sorted — so every report is reproducible."""
        return sorted(self.knowledge.glob(pattern))

    def has(self, option: str) -> bool:
        """Whether the corpus actually carries the register `option` names.

        The predicate `Check.applies` is built from: an option set to "" means "this corpus
        does not have that", and so does a path that simply is not there.
        """
        rel = getattr(self.config, option, "")
        return bool(rel) and (self.knowledge / rel).exists()


def root_for(knowledge: Path) -> Path:
    """The checkout `knowledge` belongs to — the directory whose config declares it.

    ══ WHY `knowledge.parent` IS NOT THE ANSWER ═══════════════════════════════
    It was, unconditionally, and it is a GUESS: that the corpus is a subdirectory of the
    root. True for the `knowledge/` convention, and false for a repository whose corpus is
    its own top-level documents — which writes `knowledge_dir = "."` and thereby made THE
    PARENT OF THE CHECKOUT its root. The damage was silent rather than loud: every
    repo-relative path was then probed one directory too high, so `fleet check --only
    slots` reported every slot missing while `fleet slots --repo .` — which resolves the
    root from `--repo` and never touches this function — reported the same registry
    filled. Two readers of one checkout, disagreeing, and neither of them erroring.

    A config file is the marker that ends the guess: it names the corpus RELATIVE TO
    ITSELF, so when the path it names is the corpus we resolved, the directory holding it
    is the root by construction — whatever layer actually chose the corpus. That last
    clause is why the test is "does the declared path point back here" rather than "did
    the toml layer win": `-k <repo-root>` and `$KNOWLEDGE_DIR` reach the same corpus by a
    different route, and a root that depended on the route would be a third disagreement.

    Falls back to the guess when nothing declares the corpus, because there is then no
    evidence to prefer over it — a bare `-k /somewhere/knowledge` still means what it
    always did.
    """
    located = find_config_file(knowledge)
    if located is not None:
        config_path, table = located
        declared = config_base(config_path) / str(table.get("knowledge_dir") or DEFAULT_DIR_NAME)
        try:
            if declared.expanduser().resolve() == knowledge.resolve():
                return config_base(config_path).resolve()
        except OSError:
            pass  # an unresolvable declared path is not evidence; fall through to the guess
    return knowledge.parent


def resolve(
    knowledge_dir: str | Path | None = None,
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> KnowledgeBase:
    """Resolve a `KnowledgeBase` by the documented order. Raises `ConfigError` on a dead end.

    `cwd` and `env` are injectable so the resolution can be tested without touching the
    process — the alternative is a test suite that passes only on the machine that wrote it.
    """
    cwd = Path(cwd or Path.cwd()).resolve()
    env = os.environ if env is None else env

    found: Path | None = None
    origin = DEFAULT

    if knowledge_dir is not None:
        found = Path(knowledge_dir).expanduser()
        origin = Origin("flag", "--knowledge-dir")
        if not found.is_dir():
            raise ConfigError(
                f"--knowledge-dir {found} is not a directory — pass the `knowledge/` directory "
                "itself, or omit the flag to discover it from the current directory"
            )
    if found is None and env.get(ENV_KNOWLEDGE_DIR):
        found = Path(env[ENV_KNOWLEDGE_DIR]).expanduser()
        origin = Origin("env", ENV_KNOWLEDGE_DIR)
    if found is None and env.get(ENV_ROOT):
        found = Path(env[ENV_ROOT]).expanduser() / DEFAULT_DIR_NAME
        origin = Origin("env", ENV_ROOT)
    if found is None:
        dotenv_path = find_dotenv(cwd)
        if dotenv_path is not None:
            values = read_dotenv(dotenv_path)
            if values.get(ENV_KNOWLEDGE_DIR):
                found = Path(values[ENV_KNOWLEDGE_DIR]).expanduser()
                origin = Origin("dotenv", f"{dotenv_path} ({ENV_KNOWLEDGE_DIR})")
            elif values.get(ENV_ROOT):
                found = Path(values[ENV_ROOT]).expanduser() / DEFAULT_DIR_NAME
                origin = Origin("dotenv", f"{dotenv_path} ({ENV_ROOT})")

    config = Config()
    located = find_config_file(cwd)
    if located is not None:
        config_path, table = located
        config = config_from_table(table, config_path)
        if found is None and table.get("knowledge_dir"):
            found = (config_base(config_path) / str(table["knowledge_dir"])).expanduser()
            origin = Origin("toml", str(config_path))

    if found is None:
        found = discover_knowledge_dir(cwd)
        origin = Origin("discovery", f"upward from {cwd}")

    if found is None:
        raise ConfigError(
            f"no knowledge base found at or above {cwd}. Pass --knowledge-dir PATH, set "
            f"${ENV_KNOWLEDGE_DIR}, or run from inside a checkout that has a "
            f"`{DEFAULT_DIR_NAME}/{DISCOVERY_MARKER}`"
        )
    found = found.resolve()
    if not found.is_dir():
        raise ConfigError(f"{found} is not a directory (resolved from {origin})")
    return KnowledgeBase(root=root_for(found), knowledge=found, config=config, origin=origin)
