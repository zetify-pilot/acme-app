"""`fleet init` — a repository's first contact with the tier, as files it can commit.

Two halves, and they are deliberately separable:

  * **`plan_scaffold` is PURE.** Given the person's two answers, the namespace and the set, it
    decides the whole planning record — the registers, the PRD folder, the requirement
    register, the product vision, the slot answers — plus the one line it appends to an
    existing `.gitignore`, and it reports what it would skip and what a skipped file leaves
    incomplete. It reads no disk and writes nothing, because the same plan is what the setup
    pull request carries (`api/setup.py` calls it in-process) and a plan that could differ
    between the terminal and the forge would make the two paths disagree about the one
    artifact they both produce.
  * **`apply_to_disk` writes it.** The terminal half; `init` is plan + apply + the command
    sync that owns `.fleet/**` and `knowledge/scripts/**`.

The command tree assumes a fixed layout: `.fleet/` for the tier (a Claude Code plugin, opted into
by `.claude/settings.json`) and for Fleet's configuration (`.fleet/fleet.toml`, whose
`[fleet.targets]` table says what each conventional target — lint, the unit lane, the stack — runs
here), `knowledge/scripts/` for the shipped tooling, and `knowledge/slots/README.md` for the
repository's answers. Nothing is written at the repository root but the always-on rules file a
session loads from there: no `Makefile`, no `fleet.mk`. This writes the layout, and the record the
board reads.

WHAT IT WILL NOT DO. It never overwrites or edits a file the repository owns — the one edit is
the `.gitignore` line, named as data. A skipped file is validated with the new ones (each
problem it leaves is reported with the lines to add, never fixed by editing it), and a second
run writes nothing. What changes AFTER `init` is the sync's business, not this module's: the
parts of these files Fleet owns — the marked rules block, `.fleet/fleet.toml`'s schema version, the
plugin opt-in keys and the CI template — are refreshed by `fleet commands sync` (`setupfiles`),
which never touches the rest. Stdlib only.
"""

from __future__ import annotations

import dataclasses
import json
import re
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from fleet_knowledge import commandsync, legacymake, planningmode, rulesfile, setupfiles, slotanswers
from fleet_knowledge import config as configmod
from fleet_knowledge import slots as slotmod
from fleet_knowledge import stacks as stackmod
from fleet_knowledge import targets as targetsmod

__all__ = [
    "FLEET_TOML",
    "GENERATED_ANSWERS",
    "Plan",
    "OPTIN_SETTINGS",
    "RUN_STATE_IGNORE",
    "apply_to_disk",
    "core_needs",
    "full_tree",
    "generated_answer",
    "init",
    "local_default_branch",
    "placeholder_slots",
    "plan_scaffold",
    "planning_mode",
    "planning_mode_for",
    "relevant_paths",
    "required_slots",
    "slot_answer_paths",
    "validate_answers",
]

RUN_STATE_IGNORE = ".claude/run/"
#: The project settings Claude Code reads for everyone working in the repository. The tier lives in
#: `.fleet/` as a plugin, which no session loads by itself, so the scaffold opts the repository's
#: people in here (`commandsync.optin_settings`) — without it a person's own session would have
#: none of the commands the fleet's sessions get with `--plugin-dir .fleet`.
OPTIN_SETTINGS = ".claude/settings.json"

#: The `.gitignore` line's own comment. An append is the ONE edit to a repository-owned file
#: (FLT-1004), so the line says who put it there and why.
GITIGNORE_COMMENT = "# the tier's run state (`fleet init`)"

#: The marked section an EXISTING always-on rules file is asked to add, so a repository's own
#: standing rules have a home. Reported, never applied: `fleet init` writes the rules file only
#: when the repository has none, and never edits one it does (ENG-18604).
RULES_SECTION_LINES: tuple[str, ...] = (
    "",
    rulesfile.RULES_SECTION,
    "",
    "<!-- Add this repository's standing rules below; they bind exactly as the rules above do. -->",
    "",
    "- (add your repository's rules here)",
)

RULES_SECTION_PROBLEM = "the existing rules file has no section for this repository's own standing rules"

#: This package's templates, mirroring the layout they render into.
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates" / "scaffold"

#: Where `fleet init` writes Fleet's configuration — under `.fleet/`, never at the repository root.
FLEET_TOML = configmod.CONFIG_REL

#: One line per conventional target: what a command means when it names it (`targets.TARGETS`).
TARGET_MEANING: dict[str, str] = {name: t.meaning for name, t in targetsmod.TARGETS.items()}


def initial_targets(stacks: Sequence[stackmod.Choice], makefile: bytes | None) -> dict[str, str]:
    """The `[fleet.targets]` table `fleet init` writes: what the repository's own Makefile already
    runs (`make <target>`), and the stack profiles' recipes, as shell commands, for the rest."""
    own = legacymake.own_targets(makefile.decode("utf-8", "ignore") if makefile is not None else None)
    values = {t: legacymake.make_value(t) for t in targetsmod.TARGETS if t in own}
    params = {name: t.params for name, t in targetsmod.TARGETS.items()}
    rendered = stackmod.target_commands(stacks, own=values, params=params) if stacks else {}
    values.update({t: v for t, v in rendered.items() if t in targetsmod.TARGETS})
    return {t: values[t] for t in targetsmod.TARGETS if t in values}


# ── the slot answer documents ────────────────────────────────────────────────

#: The record files a repo-tier slot's answer IS, where the record already exists. The `fill`
#: points the command at the register, not at a second copy of it. Every other required slot
#: gets a short document under `knowledge/slots/`.
_RECORD_ANSWERS: dict[str, str] = {
    "programs": "knowledge/programs.md",
    "slices": "knowledge/slices.md",
    "commitments": "knowledge/requirements/product.md",
    "product-vision": "knowledge/strategy/product-vision.md",
}


#: The slot answers WRITTEN FROM FACTS (`slotanswers`), never from a template file: what they say is
#: Fleet's own configuration and the shipped commands' conventions, decided per repository. `git-workflow`
#: is always answered; `tracker-identity` only when the facts name the tracker and its key prefix, and
#: otherwise its placeholder template is written as before.
GENERATED_ANSWERS: tuple[str, ...] = ("git-workflow", "tracker-identity")


def generated_answer(sid: str, facts: slotanswers.RepoFacts, namespace: str) -> str | None:
    """The answer the facts determine for a generated slot, or None to fall back to its template."""
    if sid == "git-workflow":
        return slotanswers.git_workflow(facts, namespace)
    if sid == "tracker-identity":
        return slotanswers.tracker_identity(facts)
    return None


def slot_answer_paths(slots: Iterable[str]) -> dict[str, str]:
    """The repo-relative answer document each repo-tier slot id reads, as `fill` points at it.

    A record-backed slot (`programs`, `slices`, `commitments`, `product-vision`) points at the
    register itself; every other slot points at its own short document under `knowledge/slots/`.
    """
    out: dict[str, str] = {}
    for sid in slots:
        out[sid] = _RECORD_ANSWERS.get(sid, f"knowledge/slots/{sid}.md")
    return out


def core_needs(src: Path | None = None) -> tuple[slotmod.CommandNeed, ...]:
    """The command needs of the packaged `tier: core` closure — the spines, parsed once.

    `commandsync.core_commands` names which commands are core; `slotmod.read_command_needs`
    parses what each requires. Joining them here means `required_slots` is enumerated from the
    shipped spines at call time, so a command that gains a `requires:` cannot leave the
    scaffold missing an answer document.
    """
    root = src or commandsync.source_root()
    core = set(commandsync.core_commands(root))
    return tuple(
        need
        for need in slotmod.read_command_needs(root, commandsync.COMMANDS_SUBDIR)
        if need.path.relative_to(root).as_posix() in core
    )


def required_slots(src: Path | None = None) -> tuple[str, ...]:
    """Every repo-tier slot the packaged core closure requires, sorted (see `slots.required_for`)."""
    return slotmod.required_for(core_needs(src))


def placeholder_slots() -> tuple[str, ...]:
    """The optional repo-tier slots the scaffold ships a placeholder for, sorted.

    A required slot is answered because a command refuses to run without it; an optional one
    gets a placeholder only where the template set carries one (`knowledge/slots/<id>.md`).
    Either way the slot sheet names it, because a placeholder the sheet does not point at is a
    file no command ever opens.
    """
    repo = {s.id for s in slotmod.read_questions().slots if s.tier == "repo"}
    templates = TEMPLATES_DIR / "knowledge" / "slots"
    shipped = {p.stem for p in templates.glob("*.md") if p.name != "README.md"} if templates.is_dir() else set()
    return tuple(sorted((shipped & repo) - set(required_slots())))


# ── the plan ─────────────────────────────────────────────────────────────────


#: The two question bounds. A name is a label a person reads on a board; a program is a
#: sentence. Generous, but bounded so a pasted document cannot become a register row nobody
#: meant to write. The service endpoint validates against the same numbers.
MAX_PRODUCT_CHARS = 120
MAX_PROGRAM_CHARS = 300


def validate_answers(
    product: str, program: str, namespace: str, *, mode: str = planningmode.PROGRAMS
) -> list[tuple[str, str]]:
    """What is wrong with the three answers, each as `(field, problem)`. Empty means valid.

    Shared by `fleet init` and the setup endpoint so the two paths refuse the same values with
    the same words — a value the terminal accepts and the pull request rejects (or the other
    way round) would be a scaffold that depends on how it was asked for.

    `program` is the first thing the team wants done. In `areas` mode (`planning_mode`) it is the first
    SLICE, so it is refused as `slice`; a caller naming no mode refuses it as a program, as before.
    """
    problems: list[tuple[str, str]] = []
    name = product.strip()
    if not name:
        problems.append(("product", "a product name is required"))
    elif len(name) > MAX_PRODUCT_CHARS:
        problems.append(("product", f"the product name is over {MAX_PRODUCT_CHARS} characters"))
    sentence = program.strip()
    what = "slice" if mode == planningmode.AREAS else "program"
    if not sentence:
        problems.append((what, f"a first {what} is required"))
    elif len(sentence) > MAX_PROGRAM_CHARS:
        problems.append((what, f"the first {what} is over {MAX_PROGRAM_CHARS} characters"))
    if not commandsync.NAMESPACE_RE.fullmatch(namespace):
        problems.append(("namespace", "a namespace is `[a-z][a-z0-9-]{1,30}` (lower-case, two characters or more)"))
    return problems


@dataclass
class Plan:
    """What a scaffold would do to one repository, decided without touching it.

    `creates` is `{repo-relative path: bytes}`; `appends` is `[(existing path, line)]` and holds
    the one edit a repository-owned file permits (FLT-1004). `skipped` names every file the
    plan would leave alone. `incomplete` is `[(path, problem, lines_to_add)]` — what a skipped
    file leaves missing, and the exact lines that would fix it, reported rather than applied.
    """

    creates: dict[str, bytes] = field(default_factory=dict)
    appends: list[tuple[str, str]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    incomplete: list[tuple[str, str, list[str]]] = field(default_factory=list)


def _template_targets() -> dict[str, str]:
    """`{repo-relative target: template-relative source}` for every file under the templates dir."""
    out: dict[str, str] = {}
    if not TEMPLATES_DIR.is_dir():
        return out
    for path in sorted(TEMPLATES_DIR.rglob("*")):
        if path.is_file():
            rel = path.relative_to(TEMPLATES_DIR).as_posix()
            out[rel] = rel
    return out


def _render(template: str, values: Mapping[str, str]) -> bytes:
    """A template with `{{key}}` placeholders substituted. Unknown keys are left as written.

    Not `str.format`: the templates are TOML, JSON and Markdown full of braces, and every brace
    a value does not own must survive untouched.
    """
    text = template
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text.encode("utf-8")


def _read_existing(repo: Path, rels: Iterable[str]) -> dict[str, bytes]:
    """The bytes of each named repo-relative file that exists, so a plan can be decided purely."""
    out: dict[str, bytes] = {}
    for rel in rels:
        path = repo / rel
        if path.is_file():
            out[rel] = path.read_bytes()
    return out


def _fleet_toml_problems(rel: str, text: str, namespace: str) -> tuple[str, list[str]] | None:
    """What an existing `fleet.toml` leaves incomplete, and the lines to add.

    A repository that already has a `fleet.toml` keeps it (R5). Without a `[fleet.commands]
    namespace` the sync renders the tree's HOME copy — the home project's issue keys, incidents
    and paths, exactly the vendor text R3 forbids from a customer's copy. Declaring any
    namespace, the default `commandsync.CUSTOMER_NAMESPACE` included, is what makes it a customer
    render, so the plan reports the lines to add, and never edits the file. The `set` is named
    with it: a kept file that declared only the namespace used to fall back to the depth set and
    write commands that still carry home ids (ENG-21056). A file that already declares `set` keeps
    its own choice, so the line is named only when it is absent (ENG-21134).
    """
    if re.search(r"^\s*namespace\s*=", text, re.MULTILINE):
        return None
    where = "[fleet.commands]" if "[fleet.commands]" in text else "\n[fleet.commands]"
    lines = [where, f'namespace = "{namespace}"']
    if not re.search(r"^\s*set\s*=", text, re.MULTILINE):
        lines.append('set = "core"')
    return (
        "the existing fleet.toml declares no `[fleet.commands] namespace`, so the commands "
        "would render as the tree's own home copy",
        lines,
    )


def _fleet_toml_vocabulary_problem(text: str) -> tuple[str, list[str]] | None:
    """An existing `fleet.toml` that points its board at no vocabulary, and the line to add.

    The sync writes the vocabulary beside the commands (ENG-17173), but the board reads only the
    document `board_guidance` names — so a kept `fleet.toml` without the key leaves a board that
    names none of the commands this plan installs. Reported, never edited, like the namespace.
    """
    if re.search(r"^\s*board_guidance\s*=", text, re.MULTILINE):
        return None
    where = "[fleet]" if re.search(r"^\s*\[fleet\]\s*$", text, re.MULTILINE) else "\n[fleet]"
    return (
        "the existing fleet.toml names no `board_guidance`, so the board names none of the commands this installs",
        [where, f'board_guidance = "{commandsync.VOCABULARY_REL}"'],
    )


def _fleet_toml_targets_problem(text: str, table: Mapping[str, str]) -> tuple[str, list[str]] | None:
    """An existing `.fleet/fleet.toml` with no `[fleet.targets]` table, and the table to add.

    Without it every target the commands name renders as a refusal. Reported, never edited: the
    sync's own migration adds the table to a file on an older schema version, and a file already on
    the current one is the repository's to complete.
    """
    if re.search(r"^\s*\[(?:fleet\.)?targets\]\s*$", text, re.MULTILINE):
        return None
    return (
        "the existing fleet.toml has no `[fleet.targets]` table, so every target the commands name reads as a refusal",
        ["", *targetsmod.table_block(table).rstrip("\n").splitlines()],
    )


def _version_or_zero(text: str) -> int:
    try:
        return setupfiles.fleet_toml_version(text)
    except ValueError:
        return 0


_ID_ROW = re.compile(r"\|\s*(PG-\d+|SL-\d+)\s*\|")

#: The feature area a fresh `fleet init`'s first slice names (design § 3.1): the product itself, until the
#: repository writes its first feature map.
FIRST_AREA = "product"


def _kept_fleet_toml(existing: Mapping[str, bytes]) -> bytes | None:
    """The `fleet.toml` the repository already has — under `.fleet/`, or at the root where an earlier release
    wrote it — which `fleet init` keeps; `None` when it has none."""
    return next((existing[rel] for rel in (FLEET_TOML, setupfiles.LEGACY_FLEET_TOML) if rel in existing), None)


def planning_mode(existing: Mapping[str, bytes]) -> str:
    """Where this scaffold puts the first thing the team wants done (`[fleet.planning] mode`, FLT-1281).

    A repository with no `fleet.toml` gets the template's, which plans by area — only a fresh init turns it on.
    A repository that has one keeps it, so ITS mode decides: absent means `programs`, exactly as before. A kept
    file that does not parse reads as the default: the plan never changes an existing repository's mode."""
    kept = _kept_fleet_toml(existing)
    if kept is None:
        return planningmode.AREAS
    try:
        data = tomllib.loads(kept.decode("utf-8", "ignore"))
    except tomllib.TOMLDecodeError:
        return planningmode.DEFAULT_MODE
    fleet = data.get("fleet")
    table = fleet.get("planning") if isinstance(fleet, dict) else None
    if not isinstance(table, dict):
        table = data.get("planning") if isinstance(data.get("planning"), dict) else None
    return planningmode.mode_of(table)


def planning_mode_for(repo: Path) -> str:
    """`planning_mode` over the files on disk in `repo` — what `fleet init` asks its questions by."""
    return planning_mode(_read_existing(repo, (FLEET_TOML, setupfiles.LEGACY_FLEET_TOML)))


def _first_answer(answers: Mapping[str, str]) -> str:
    """The first thing the team wants done: `firstSlice`, or `firstProgram`, the name every caller has sent so far
    (the setup dialog among them) — one sentence, whichever the mode makes of it."""
    return (answers.get("firstSlice") or answers.get("firstProgram") or "").strip()


def _program_row(sentence: str) -> str:
    return f"| PG-01 | {sentence} | program | — | — | adopted |"


def _slice_row(sentence: str, home: str) -> str:
    return (
        f"| SL-001 | {sentence} | feature | {home} | {sentence} — observed on the "
        "running product, not a definition. | — | — | — | adopted |"
    )


def plan_scaffold(
    answers: Mapping[str, str],
    namespace: str,
    set_name: str,
    existing: Mapping[str, bytes],
    *,
    stacks: Sequence[stackmod.Choice] = (),
    ci_runner: str = "",
    facts: slotanswers.RepoFacts | None = None,
) -> Plan:
    """Decide the scaffold for `answers`, purely, against what `existing` already holds.

    `answers` carries `productName` and the first thing the team wants done — `firstSlice`, or
    `firstProgram` (the wire name the setup dialog already sends): the two things only the owner knows.
    Which it becomes is `planning_mode`'s: the first area slice in `areas` mode, `PG-01` and its first
    slice in `programs` mode. `existing` is `{repo-relative path: bytes}`
    for the files the plan would otherwise write, so a plan can be decided without a disk.
    `stacks` are the stacks the repository builds in (`stacks.detect_repo` / `resolve_repo`):
    with any, the conventional targets get the stacks' commands in `[fleet.targets]`
    (`initial_targets`), and the CI template is rendered from the same commands.
    `facts` is what the caller knows about the repository and its install (`slotanswers.RepoFacts`): the
    setup endpoint passes the install's tracker, lane and merge settings, `fleet init` what its flags and
    the checkout say. They answer `git-workflow` and, when the tracker is named, `tracker-identity`
    (`GENERATED_ANSWERS`); none at all still answers `git-workflow` from the shipped conventions.
    """
    product = answers.get("productName", "").strip()
    program = _first_answer(answers)
    table = initial_targets(stacks, existing.get(setupfiles.MAKEFILE))
    # THE FIRST THING THE TEAM WANTS DONE (FLT-1280, FLT-1281): in `areas` mode — every fresh init — it is the first
    # slice, under the area `product`, and no program is written; a repository whose kept `fleet.toml` plans by
    # program gets `PG-01` and its first slice, exactly as `fleet init` always wrote them.
    areas = planning_mode(existing) == planningmode.AREAS
    area_cell = f"{planningmode.AREA_CELL_PREFIX}{FIRST_AREA}"
    slice_home = area_cell if areas else f"PG-01, {area_cell}"
    values = {
        "productName": product,
        "firstProgram": program,
        "namespace": namespace,
        "set": set_name,
        "targets": targetsmod.table_block(table).rstrip("\n"),
        "programRows": "" if areas else _program_row(program),
        "nextProgram": "PG-01" if areas else "PG-02",
        "sliceHome": slice_home,
    }

    required = required_slots()
    answered = tuple(sorted({*required, *placeholder_slots()}))
    answers_map = slot_answer_paths(answered)
    contracts = [stackmod.contract_path(c.id) for c in stacks if stackmod.contract_text(c.id) is not None]

    creates: dict[str, bytes] = {}
    skipped: list[str] = []
    incomplete: list[tuple[str, str, list[str]]] = []

    # The record templates, rendered. `fleet.toml` and `knowledge/slots/README.md` are handled
    # below, because their content depends on decisions (the namespace, the required slots) the
    # rest of the templates do not.
    for rel in sorted(_template_targets()):
        if rel in (*rulesfile.RULES_FILES, "fleet.toml", "knowledge/slots/README.md"):  # handled below
            continue
        if rel in existing:
            skipped.append(rel)
            continue
        creates[rel] = _render((TEMPLATES_DIR / rel).read_text(encoding="utf-8"), values)
        if rel == "knowledge/programs.md":
            # An areas-mode register has no row: the table ends at its separator, never on a blank line.
            creates[rel] = creates[rel].rstrip(b"\n") + b"\n"

    # The slot answers Fleet can write itself (`GENERATED_ANSWERS`): its own configuration, handed in as
    # `facts`, and the conventions the shipped commands use everywhere. Kept like every other file when the
    # repository already has one; a slot whose facts are not known keeps its placeholder template.
    for sid in GENERATED_ANSWERS:
        answer_rel = answers_map.get(sid)
        if answer_rel is None:
            continue
        if answer_rel in existing:
            if answer_rel not in skipped:
                skipped.append(answer_rel)
            continue
        text = generated_answer(sid, facts or slotanswers.RepoFacts(), namespace)
        if text is not None:
            creates[answer_rel] = text.encode("utf-8")

    # The slots answer sheet: every required repo-tier slot pointing at its answer document.
    registry_rel = "knowledge/slots/README.md"
    if registry_rel in existing:
        skipped.append(registry_rel)
        missing = _missing_fill(existing[registry_rel].decode("utf-8", "ignore"), required)
        if missing:
            lines = [f'  "{sid}": ["{answers_map[sid]}"]' for sid in missing]
            incomplete.append(
                (
                    registry_rel,
                    "the existing slots sheet answers none of the required repo-tier slots "
                    f"({', '.join(missing)}), so the commands needing them cannot run",
                    lines,
                )
            )
    else:
        extra = {"languages": contracts} if contracts and "languages" in answers_map else {}
        creates[registry_rel] = _answer_sheet(answered, answers_map, extra)

    # The always-on rules file: the generic rules the engine loads at the start of every
    # session, with a marked section for the repository's own. Written only when the repository
    # has none (ENG-18604); an existing one is kept, and one that carries no section of its own
    # is reported with the lines to add — never edited, exactly like every other repo-owned file.
    # Rendered by the sync's own renderer, so the block names this repository's namespace and the
    # commands its set ships exactly as the first `fleet commands sync` would — never a text the
    # next sync would have to rewrite, or mistake for a person's edit.
    rules_bytes = setupfiles.rules_template(namespace, set_name).encode("utf-8")
    for rel in rulesfile.RULES_FILES:
        if rel in existing:
            skipped.append(rel)
            if rulesfile.RULES_SECTION not in existing[rel].decode("utf-8", "ignore"):
                incomplete.append((rel, RULES_SECTION_PROBLEM, list(RULES_SECTION_LINES)))
        else:
            creates[rel] = rules_bytes

    # The language contracts the stacks ship, where the `languages` slot points at them — each
    # kept when the repository already has one — and the slot's answer naming them.
    for choice in stacks:
        text = stackmod.contract_text(choice.id)
        rel = stackmod.contract_path(choice.id)
        if text is None:
            continue
        if rel in existing:
            skipped.append(rel)
        else:
            creates[rel] = text.encode("utf-8")
    languages_rel = answers_map.get("languages", "")
    if contracts and languages_rel in creates:
        creates[languages_rel] = stackmod.languages_answer(stacks).encode("utf-8")

    # The two register-skipped files: if the repository already owns them and they name no row
    # of the right tier, the board will not show the first program or slice — reported, never
    # edited, and the line to add is the row the template would have written.
    # In `areas` mode a program register with no program is what the plan itself writes, so it is not a problem.
    if (
        not areas
        and "knowledge/programs.md" in existing
        and not _ID_ROW.search(existing["knowledge/programs.md"].decode("utf-8", "ignore"))
    ):
        incomplete.append(
            (
                "knowledge/programs.md",
                "the existing program register names no program, so the board will show none",
                [_program_row(program)],
            )
        )
    if "knowledge/slices.md" in existing and not _ID_ROW.search(
        existing["knowledge/slices.md"].decode("utf-8", "ignore").replace("PG-", "ZZ-")
    ):
        incomplete.append(
            (
                "knowledge/slices.md",
                "the existing slice register names no slice, so the board will show none",
                [_slice_row(program, slice_home)],
            )
        )

    # `.fleet/fleet.toml`: kept, but an existing one without a namespace leaves the commands
    # rendered as the tree's own home copy. Reported with the lines to add. A root `fleet.toml` an
    # earlier release wrote is kept too: the sync this init runs moves it under `.fleet/` and adds
    # the targets table (`setupfiles`), so it is judged as the file it becomes.
    kept_rel = next((rel for rel in (FLEET_TOML, setupfiles.LEGACY_FLEET_TOML) if rel in existing), None)
    if kept_rel is not None:
        skipped.append(kept_rel)
        kept = existing[kept_rel].decode("utf-8", "ignore")
        # ONE entry for the file, however many lines it lacks: a reader (and the setup pull
        # request's body) reads the incomplete list per path.
        checks = [_fleet_toml_problems(kept_rel, kept, namespace), _fleet_toml_vocabulary_problem(kept)]
        if kept_rel == FLEET_TOML and _version_or_zero(kept) >= setupfiles.FLEET_TOML_VERSION:
            checks.append(_fleet_toml_targets_problem(kept, table))
        found = [p for p in checks if p is not None]
        if found:
            incomplete.append((kept_rel, "; and ".join(p[0] for p in found), [ln for p in found for ln in p[1]]))
    else:
        creates[FLEET_TOML] = _render((TEMPLATES_DIR / "fleet.toml").read_text(encoding="utf-8"), values)

    # The CI template, from the stacks and the table's commands: a file a person commits, never a
    # workflow. No Makefile and no `fleet.mk`: the table is what a command's target resolves to.
    if stacks:
        _plan_ci(stacks, table, existing, creates, skipped, ci_runner)

    # The plugin opt-in: written when the repository has no project settings, never merged into
    # settings it already has — a kept file that does not enable the plugin is reported with the
    # keys to add, like every other kept file.
    _plan_optin(namespace, existing, creates, skipped, incomplete)

    # The one permitted edit: the run-state line in an existing `.gitignore`.
    existing_ignore = existing.get(".gitignore", b"").decode("utf-8", "ignore")
    if RUN_STATE_IGNORE in existing_ignore.splitlines():
        skipped.append(f".gitignore ({RUN_STATE_IGNORE})")
        appends: list[tuple[str, str]] = []
    else:
        appends = _gitignore_append(existing_ignore)

    return Plan(creates=creates, appends=appends, skipped=skipped, incomplete=incomplete)


def _plan_optin(
    namespace: str,
    existing: Mapping[str, bytes],
    creates: dict[str, bytes],
    skipped: list[str],
    incomplete: list[tuple[str, str, list[str]]],
) -> None:
    ns = namespace or commandsync.source_namespace(commandsync.source_root())
    settings = commandsync.optin_settings(ns)
    if OPTIN_SETTINGS not in existing:
        creates[OPTIN_SETTINGS] = (json.dumps(settings, indent=2) + "\n").encode("utf-8")
        return
    skipped.append(OPTIN_SETTINGS)
    try:
        kept = json.loads(existing[OPTIN_SETTINGS].decode("utf-8", "ignore") or "{}")
    except json.JSONDecodeError:
        kept = None
    plugin = next(iter(settings["enabledPlugins"]))  # type: ignore[call-overload]
    enabled = isinstance(kept, dict) and (kept.get("enabledPlugins") or {}).get(plugin) is True
    if not enabled:
        incomplete.append(
            (
                OPTIN_SETTINGS,
                f"the existing settings do not enable `{plugin}`, so a person's own session has none of the "
                "commands; merge these keys in",
                json.dumps(settings, indent=2).splitlines(),
            )
        )


def _plan_ci(
    stacks: Sequence[stackmod.Choice],
    table: Mapping[str, str],
    existing: Mapping[str, bytes],
    creates: dict[str, bytes],
    skipped: list[str],
    ci_runner: str = "",
) -> None:
    """The CI template and its instructions, rendered from `table` — each kept when present."""
    for rel, body in (
        (stackmod.CI_WORKFLOW, stackmod.render_ci(stacks, runner_label=ci_runner, commands=table)),
        (stackmod.CI_README, stackmod.render_ci_readme(stacks)),
    ):
        if rel in existing:
            skipped.append(rel)
        else:
            creates[rel] = body.encode("utf-8")


def _gitignore_append(existing: str) -> list[tuple[str, str]]:
    """The `(path, line)` pair for the run-state ignore, the one edit a repo-owned file permits."""
    del existing  # the writer decides the separator; the plan carries only the line
    return [(".gitignore", f"{GITIGNORE_COMMENT}\n{RUN_STATE_IGNORE}")]


def _missing_fill(text: str, required: Iterable[str]) -> list[str]:
    """Which required slot ids an existing slots sheet does not name in its `fill` block."""
    block = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
    named: set[str] = set()
    if block is not None:
        try:
            import json

            data = json.loads(block.group(1))
            if isinstance(data, dict) and isinstance(data.get("fill"), dict):
                named = set(data["fill"])
        except ValueError:
            named = set()
    return [sid for sid in required if sid not in named]


def _answer_sheet(
    required: Iterable[str], answers: Mapping[str, str], extra: Mapping[str, list[str]] | None = None
) -> bytes:
    """The repository's half of the slot interface: a `fill` for every required repo slot.

    `extra` adds paths to a slot's fill — the stacks' language contracts to `languages`."""
    import json

    fills = {sid: [answers[sid], *(extra or {}).get(sid, [])] for sid in required}
    block = json.dumps({"version": 2, "fill": fills}, indent=2, ensure_ascii=False)
    text = (
        "# Slots — where this repository's answers live\n"
        "\n"
        "The shipped questionnaire (`fleet slots --emit questions`) asks the questions; this file\n"
        "holds only `fill` — the repo-relative path(s) that answer each. Every slot the shipped\n"
        "core commands require is answered below, so `fleet slots --repo .` finds every core\n"
        "command runnable, and so is each optional slot the scaffold writes a placeholder for.\n"
        "Where *this* repository keeps a document is the only part of a slot a repository is\n"
        "entitled to have an opinion about.\n"
        "\n"
        f"```json\n{block}\n```\n"
    )
    return text.encode("utf-8")


# ── applying the plan ────────────────────────────────────────────────────────


def apply_to_disk(plan: Plan, root: Path) -> list[str]:
    """Write `plan` under `root`; return the repo-relative paths written, in plan order."""
    written: list[str] = []
    for rel, content in plan.creates.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        written.append(rel)
    for rel, line in plan.appends:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.is_file() else ""
        sep = "" if not existing or existing.endswith("\n") else "\n"
        path.write_text(f"{existing}{sep}{line}\n", encoding="utf-8")
        written.append(rel)
    return written


def full_tree(plan: Plan, existing: Mapping[str, bytes], *, namespace: str, set_name: str) -> dict[str, bytes]:
    """Every file `plan` would leave in the repository, as `{path: bytes}`.

    The pure twin of `init` minus the disk: `plan.creates`, the `.gitignore` append resolved
    against what the repository already has, and the command tier `commandsync.render_tree`
    renders. The setup pull request builds its git tree from this, so its files equal what
    `fleet init` writes for the same answers (AC-9).
    """
    files: dict[str, bytes] = dict(plan.creates)
    for rel, line in plan.appends:
        previous = existing.get(rel, b"").decode("utf-8", "ignore")
        sep = "" if not previous or previous.endswith("\n") else "\n"
        files[rel] = f"{previous}{sep}{line}\n".encode()
    # The manifest records the setup files this tree lays down as Fleet wrote them, exactly as the
    # sync `fleet init` runs records them — so a merged setup pull request passes `--check` and a
    # later release can tell Fleet's rules block from a person's edit. Only what is ALREADY current
    # is recorded: a kept file this tree does not change is the next sync's to decide. Planned
    # BEFORE the tier, because the tier names the commands of the table it decides.
    setup = setupfiles.plan_files(
        lambda rel: files.get(rel, existing.get(rel)), {}, namespace=namespace, set_name=set_name
    )
    tier = commandsync.render_tree(namespace=namespace, set_name=set_name, targets=setup.targets)
    files.update(tier)
    recorded = {f.path: f.record for f in setup.files if f.state == "up-to-date" and f.record is not None}
    if recorded:
        manifest = commandsync.manifest_rel()
        rendered = {path: data for path, data in tier.items() if path != manifest}
        files[manifest] = commandsync.manifest_record_bytes(
            rendered,
            setup={"files": dict(sorted(recorded.items()))},
            commands={"namespace": namespace, "set": set_name},
        )
    return files


@dataclass
class InitReport:
    repo: Path
    sync: commandsync.SyncReport
    plan: Plan
    wrote: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    #: The conventional targets `[fleet.targets]` leaves unconfigured (Fleet's own aside): each
    #: renders as a refusal until the repository names its command.
    missing_targets: tuple[str, ...] = ()
    stacks: tuple[str, ...] = ()

    @property
    def incomplete(self) -> list[tuple[str, str, list[str]]]:
        return self.plan.incomplete

    def lines(self) -> list[str]:
        out = [f"fleet init: {self.repo}", *self.sync.lines()]
        for rel in self.wrote:
            out.append(f"  wrote    {rel}")
        for rel in self.kept:
            out.append(f"  kept     {rel} (already present — not touched)")
        for path, problem, lines_to_add in self.incomplete:
            out.append(f"  incomplete  {path}: {problem}")
            for line in lines_to_add:
                out.append(f"    + {line}")
        if self.missing_targets:
            out.append(
                f"  {FLEET_TOML} [fleet.targets] leaves {len(self.missing_targets)} conventional target(s) "
                "unconfigured: " + ", ".join(self.missing_targets)
            )
            out.append("           a command that names one reads a refusal there until you name its command")
        if self.stacks:
            out.append(f"  stacks   {', '.join(self.stacks)} — their commands are in {FLEET_TOML} [fleet.targets]")
            out.append("  every worker needs, for those recipes to run:")
            out.extend(f"    {line}" for line in stackmod.install_lines(self.stacks))
            out.append(
                f"  CI       {stackmod.CI_WORKFLOW} is a template: commit it as {stackmod.CI_TARGET} "
                f"yourself ({stackmod.CI_README})"
            )
        return out


def relevant_paths() -> tuple[str, ...]:
    """The repo-relative files a plan consults before deciding: what to fetch from a bare tree.

    The setup pull request reads the repository through the Git Data API, and these are the
    paths whose presence or content changes the plan — the files it would create, plus the
    `.gitignore` it appends to. A caller reads only these, rather than the whole tree.
    """
    candidates = set(_template_targets())
    # The generated answers have no template, and a repository's own copy must still be kept, never overwritten.
    candidates |= set(slot_answer_paths(GENERATED_ANSWERS).values())
    candidates |= {
        FLEET_TOML,
        setupfiles.LEGACY_FLEET_TOML,
        setupfiles.MAKEFILE,
        ".gitignore",
        OPTIN_SETTINGS,
        *rulesfile.RULES_FILES,
        "knowledge/slots/README.md",
        "knowledge/programs.md",
        "knowledge/slices.md",
        setupfiles.FLEET_MK,
        stackmod.CI_WORKFLOW,
        stackmod.CI_README,
        *(stackmod.contract_path(sid) for sid, p in stackmod.profiles().items() if p.contract),
    }
    return tuple(sorted(candidates))


def plan_for(
    repo: Path,
    answers: Mapping[str, str],
    namespace: str,
    set_name: str,
    *,
    stacks: Sequence[stackmod.Choice] = (),
    ci_runner: str = "",
    facts: slotanswers.RepoFacts | None = None,
) -> Plan:
    """The plan for `repo` as it stands: read the files it owns, then plan purely."""
    return plan_scaffold(
        answers,
        namespace,
        set_name,
        _read_existing(repo, relevant_paths()),
        stacks=stacks,
        ci_runner=ci_runner,
        facts=facts,
    )


def local_default_branch(repo: Path) -> str:
    """The checkout's default branch: what `origin/HEAD` points at, else the branch checked out, else `""`.

    The terminal half's one read of git, so `git-workflow` names the branch a fresh `fleet init` sees.
    A repository with no git, or a detached head, answers `""` — the answer then says "the default branch".
    """
    import subprocess  # noqa: PLC0415 — the terminal half's only subprocess

    for argv in (
        ["git", "-C", str(repo), "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
        ["git", "-C", str(repo), "symbolic-ref", "--quiet", "--short", "HEAD"],
    ):
        try:
            done = subprocess.run(argv, capture_output=True, text=True, timeout=10, check=False)
        except (OSError, subprocess.SubprocessError):
            return ""
        name = done.stdout.strip() if done.returncode == 0 else ""
        if name:
            return name.removeprefix("origin/")
    return ""


def init(
    repo: Path,
    answers: Mapping[str, str] | None = None,
    namespace: str = commandsync.CUSTOMER_NAMESPACE,
    set_name: str = "core",
    *,
    stacks: Sequence[stackmod.Choice] = (),
    ci_runner: str = "",
    facts: slotanswers.RepoFacts | None = None,
) -> InitReport:
    """Write the layout and the planning record into `repo`, then sync the command tier.

    `answers` carries `productName` and `firstSlice` (or `firstProgram`); both are required for a real init, but
    an empty mapping is accepted so a caller that only wants the command tier can say so. Every
    write is guarded on the file's absence, so a second run changes nothing and says so.
    `facts` answers the slots Fleet's configuration determines (`plan_scaffold`); a default branch it
    does not name is read from the checkout.
    """
    repo = repo.resolve()
    facts = facts or slotanswers.RepoFacts()
    if not facts.default_branch:
        facts = dataclasses.replace(facts, default_branch=local_default_branch(repo))
    plan = plan_for(repo, answers or {}, namespace, set_name, stacks=stacks, ci_runner=ci_runner, facts=facts)
    wrote = apply_to_disk(plan, repo)
    # The stacks just rendered are handed to the sync, which records them, so a later release can
    # refresh the CI template from the same inputs (`setupfiles`).
    inputs = setupfiles.Inputs(tuple(stacks), ci_runner) if stacks else None
    # A kept `fleet.toml` may predate the namespace (or the set): the sync would then render the
    # tree's HOME copy — its own issue keys and incidents — into a customer repository, because
    # `commands_config` can only read what the file declares. `--namespace`/`--set` fill that gap;
    # a value the file DOES declare still wins, so a later plain sync agrees with this run
    # (ENG-21055). The kept file is still reported, never edited (D7).
    declared_namespace, declared_set = commandsync.declared_commands_config(repo)
    sync = commandsync.sync(
        repo,
        setup_inputs=inputs,
        namespace=declared_namespace or namespace,
        set_name=declared_set or set_name,
    )
    report = InitReport(
        repo=repo,
        sync=sync,
        plan=plan,
        wrote=wrote,
        kept=list(plan.skipped),
        stacks=tuple(c.id for c in stacks),
    )
    configured = set(commandsync.commands_targets(repo)) | set(targetsmod.SHIPPED)
    report.missing_targets = tuple(t for t in targetsmod.TARGETS if t not in configured)
    return report
