"""The command↔repo interface: which questions a repo must answer for a command to run.

A slash command is a **portable procedure**; a repo is a **set of filled-in slots**. A
command should run in a second repository because that repository answers a known,
enumerated list of questions — not because someone forked the command into it.

This module reads that list. It comes in **two halves, and they live in two places on
purpose**:

  * **The questionnaire SHIPS** — `slot-questions.json`, beside `commandtree/` in this
    package. It carries `id`, `tier`, `requirement`, `answers`, `degrade`, `consumed_by`,
    and the `fill` of the shared rows. Every one of those fields describes a **command**,
    and the commands ship from here, so the answer is identical in every repository that
    receives them.
  * **The repo answers `fill`, and nothing else** — one `id → [paths]` map in its own
    registry file. Where *this* repository keeps its gate document is the only part of a
    slot a repository is entitled to have an opinion about.

WHY THE SPLIT EXISTS. Before it, every field lived in every repo's registry, so a repo
adopting the command tier hand-copied three dozen rows of `answers`/`degrade`/`consumed_by`
strings describing procedures it did not write and cannot change. The second repo to
receive the tier generated its registry mechanically from the first one's and said so in
its own prose — a second hand-maintained copy of a shared vocabulary, which is the exact
drift `commandsync.py` was written to end for the procedures themselves. A command gaining
a `requires:` then had to be reflected by hand in N registries, and the first one nobody
edited went quietly wrong: the slot still resolved, so nothing was ever reported.

WHY THIS EXISTS AT ALL. In the estate this package was extracted from, five of six
dispatch lanes had the command tree switched OFF and fell back to generic mission prompts.
The reason was not that the commands were shaped for the repository they came from — it
was that no other repository had filled a single slot, and nobody could have, because the
list had never been written down. That dispatch table was
already half of this one (`human_merge_required`, `human_merge_paths`,
`verify_gate_required`, `setup_command`) plus a free-text `notes` blob for everything
else — answered from OUTSIDE the repo it describes, which is exactly how that note went
stale for six weeks with nobody positioned to notice. A slot registry lives in the repo
whose questions it answers, so the session holding the checkout is the one that can fix
it — and now it holds ONLY those answers.

WHAT A MISSING SLOT MEANS is deliberately not uniform:

  * `tier: shared`     — ships WITH the command tree under `.claude/`. Missing means the
                         command tree is incomplete, not that the repo failed to supply
                         something: a shared slot is never a repo's to answer.
  * `mandatory`        — the command REFUSES to run. Reported as an error.
  * `optional`         — the command degrades in the way the slot's own `degrade` field
                         names. Reported as a note, never a failure. An unfilled optional
                         slot is a smaller run, not a broken one.

That gradient is also what decides which questions a repo is allowed to skip entirely.
A **mandatory** slot is surveyed whether the repo mentions it or not — silence would
otherwise be quieter than an honest empty answer, and a repo could drop the row to make
the gate green while every command needing it still cannot run. An **optional** slot the
repo never names is a question it has not taken on; it is listed by id so it is visible,
and counted against nothing.

DECLINING IS NEVER DELETING. Because a decline is invisible in the resolved slot set, the
refresh that RE-DERIVES the questionnaire (`refresh_questions`, below) merges a repo's rows
OVER the shipped file instead of replacing it: a refresh may add a row or amend one, and
may never subtract. Doing it the other way made `fleet slots --repo . --emit questions`
delete every question the source repo had legitimately declined — 13 of 39 from the fleet
repo itself — which is a different questionnaire depending on which checkout ran the
command. Retiring a row is a hand edit of the shipped file, in the commit that removes the
last `requires:` naming it.

BOTH REGISTRY SHAPES ARE READ. The legacy self-contained shape (a `"slots"` array carrying
every field) still parses exactly as it did, because the registry and this package live in
different repositories on independent release cadences — a reader that understood only the
new shape would turn a submodule bump into a flag day across every consumer, which is the
coordination cost the split exists to remove. It is reported as a note, not a failure.

Stdlib only.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

__all__ = [
    "DEFAULT_REGISTRY",
    "QUESTIONS_FILE",
    "STUB_MARKER",
    "CommandNeed",
    "Fill",
    "Refresh",
    "Registry",
    "Slot",
    "Survey",
    "answers_block",
    "is_stub",
    "questions_block",
    "questions_path",
    "read_questions",
    "read_registry",
    "read_command_needs",
    "refresh_questions",
    "required_for",
    "survey",
]

# Relative to the knowledge directory. Overridable per project via `[fleet.slots] registry`.
DEFAULT_REGISTRY = "slots/README.md"

# The shipped questionnaire, beside `commandtree/` and shipped for the same reason: it
# describes the commands, and the commands ship from here.
QUESTIONS_FILE = "slot-questions.json"

# Where the command tree lives, relative to the repository root. A repo with no such
# directory has no commands to run and the whole family SKIPS. `.fleet/commands`, the plugin
# layout `commandsync` writes, is the only one: `.claude/commands` is no longer read.
COMMANDS_DIR = ".fleet/commands"
#: The same directory under the name the plugin layout's readers used while two layouts existed.
PLUGIN_COMMANDS_DIR = COMMANDS_DIR


def default_commands_dir(root: Path) -> str:
    """The command tree's directory in the checkout at `root`: `.fleet/commands`."""
    del root  # one layout; kept so every reader asks the same question of the same function
    return COMMANDS_DIR


# ── placeholders ──────────────────────────────────────────────────────────────
#
# A PLACEHOLDER IS NOT AN ANSWER. `fleet init` writes a short placeholder at every repo-tier slot
# answer path, so the slot sheet points at files that exist on day one. Counting existence as an
# answer made a repository of placeholders report "all 29 spined command(s) can run here" (the
# first customer repository: 12 of 12 slot files the shipped placeholder, byte for byte,
# and the board green). So a file is a STUB, and its slot UNFILLED, when either
#
#   * it carries the marker line below — every scaffold placeholder ships with it, and the person
#     writing the real answer deletes it; or
#   * it is byte-for-byte a placeholder an earlier `fleet init` wrote before the marker existed:
#     the shipped template minus the marker line, its `{{key}}` values standing for any one line.
#     Any edit at all makes it somebody's answer — only an exact copy is a stub.

#: The line that marks a file as a placeholder. Deleting it is what turns the file into an answer.
STUB_MARKER = "<!-- fleet:stub -->"

_STUB_MARKER_RE = re.compile(r"^[ \t]*<!--\s*fleet:stub\b[^\n]*?-->[ \t]*$", re.MULTILINE)

#: The scaffold's own templates, the source of what a placeholder looks like.
SCAFFOLD_TEMPLATES = Path(__file__).resolve().parent / "templates" / "scaffold"


#: Placeholders the scaffold USED to write and no longer does, exactly as they shipped (marker
#: included). When a template is rewritten, a repository initialised before the marker existed
#: still holds the old text byte for byte, and without the old shape here that copy would suddenly
#: read as somebody's answer. `entity-model`'s was replaced by a starter pointing at the shared
#: planning ladder on 2026-10-27. On 2026-11-07 the scaffold began writing real answers for the slots
#: Fleet's own configuration or its own layout determines (`slotanswers`, and the rewritten
#: `planning-model`, `entity-model`, `file-conventions` and `feature-areas` templates), so their
#: placeholders retired here too — a copy an older scaffold wrote still reads as the stub it is.
def _generic_placeholder(slot: str, asks: str) -> str:
    """The one-paragraph placeholder every early slot template shipped, exactly as it shipped."""
    return (
        "<!-- fleet:stub -->\n"
        f"# {slot}\n"
        "\n"
        f"{asks}\n"
        "\n"
        "Fill this in as the repository grows. It is one of the slots the shipped commands read to run\n"
        "here; `fleet slots --repo .` reports which command is blocked while it is empty.\n"
    )


RETIRED_PLACEHOLDERS: tuple[str, ...] = (
    _generic_placeholder("entity-model", "The planning tiers this product uses: programs, slices and PRDs."),
    _generic_placeholder(
        "git-workflow",
        "Branch names, who merges, which checks are required, and how a pull request silently fails to merge.",
    ),
    _generic_placeholder(
        "planning-model", "The PRD lifecycle this product runs: fill, design, plan, implement, verify."
    ),
    _generic_placeholder("file-conventions", "Where a new document of each kind lives, and how it is named."),
    _generic_placeholder(
        "feature-areas",
        "The closed set of feature areas an issue can be filed against, and the tracker project each maps to.",
    ),
    # The 2026-10-27 `entity-model` starter: its table is the scaffold's own layout, now written as the answer.
    "<!-- fleet:stub -->\n"
    "# entity-model\n"
    "\n"
    "**What each kind of work is, and the order to test for it, is not written here.** It ships with\n"
    "the command tier as the shared planning ladder, `.fleet/process/planning-ladder.md`, and the\n"
    "commands that classify work (route, intake, check) carry it inline. This file says only where each\n"
    "kind lives in **this** repository, and gives local examples.\n"
    "\n"
    "## Where each kind lives here\n"
    "\n"
    "These are the places `fleet init` created. Change a row when this repository keeps something\n"
    "elsewhere.\n"
    "\n"
    "| Kind | Where it lives here |\n"
    "|---|---|\n"
    "| Bug, task, idea | the tracker only — never a file |\n"
    "| PRD | a `prd.md` in its own numbered folder under `knowledge/prds/` |\n"
    "| Slice | a row in `knowledge/slices.md` |\n"
    "| Program | a row in `knowledge/programs.md` |\n"
    "| Requirement | a numbered row in `knowledge/requirements/product.md` |\n"
    "| Feature area | the `feature-areas` slot (`knowledge/slots/feature-areas.md`) |\n"
    "| Component | the component registry (the `components` slot) — `fleet init` does not create one; "
    "add it with the first component |\n"
    "\n"
    "## Local examples\n"
    "\n"
    "Add one or two requests from this product for each work kind, so the next reader sees the ladder\n"
    "applied to real work here. For example: a defect in a shipped screen is a bug; one new screen is\n"
    'a PRD; a feature with its own "Done when" is a slice; a program needs at least two slices and no\n'
    "existing open home that fits.\n"
    "\n"
    "When the table is right and the examples are written, delete the `fleet:stub` line at the top:\n"
    "until then `fleet slots --repo .` reports this slot as a placeholder.\n",
)

#: A file larger than this is never a placeholder (they are a few hundred bytes); the bound keeps
#: the probe from reading a large answer document only to compare it with a short template.
_STUB_MAX_BYTES = 16_384


@lru_cache(maxsize=1)
def _legacy_placeholders() -> tuple[re.Pattern[str], ...]:
    """The unmarked shape of every marked scaffold template, as a whole-file pattern."""
    out: list[re.Pattern[str]] = []
    shipped = sorted(SCAFFOLD_TEMPLATES.rglob("*.md")) if SCAFFOLD_TEMPLATES.is_dir() else []
    for text in (*(path.read_text(encoding="utf-8") for path in shipped), *RETIRED_PLACEHOLDERS):
        if not _STUB_MARKER_RE.search(text):
            continue
        legacy = "".join(ln for ln in text.splitlines(keepends=True) if not _STUB_MARKER_RE.fullmatch(ln.rstrip("\n")))
        parts = re.split(r"\{\{[A-Za-z0-9_]+\}\}", legacy)
        out.append(re.compile("[^\n]*".join(re.escape(p) for p in parts)))
    return tuple(out)


def is_stub(path: Path) -> bool:
    """Whether the file at `path` is a scaffold placeholder rather than an answer."""
    try:
        if not path.is_file() or path.stat().st_size > _STUB_MAX_BYTES:
            return False
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if _STUB_MARKER_RE.search(text):
        return True
    return any(p.fullmatch(text) for p in _legacy_placeholders())


TIERS = ("shared", "repo")
REQUIREMENTS = ("mandatory", "optional")

# The registry's own vocabulary. A key outside it is a typo, and a typo in the file that
# decides what gates a command is the worst place for a silent shrug — so it is reported.
SLOT_KEYS = frozenset({"id", "tier", "requirement", "answers", "fill", "consumed_by", "degrade"})
SLOT_REQUIRED = ("id", "tier", "requirement", "answers", "fill")

_JSON_BLOCK = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)
# A command spine is a fenced json block carrying a "command" key; `requires` / `optional`
# are lists of slot ids. Parsed with the same reader the spine validator uses so the two
# never disagree about what a spine is.
_SPINE_COMMAND = re.compile(r'"command"\s*:\s*"([a-z0-9-]+)"')


@dataclass(frozen=True)
class Slot:
    """One question a command needs answered, and where this repo answers it."""

    id: str
    tier: str
    requirement: str
    answers: str
    fill: tuple[str, ...]
    consumed_by: tuple[str, ...] = ()
    degrade: str | None = None

    @property
    def mandatory(self) -> bool:
        return self.requirement == "mandatory"

    @property
    def shared(self) -> bool:
        return self.tier == "shared"


@dataclass(frozen=True)
class Fill:
    """Whether a slot is actually answered in a given checkout.

    `missing` holds the `fill` patterns that matched nothing — naming the pattern rather
    than only saying "unfilled", because the fix is to create that path and a reader
    should not have to open the registry to find out which one.
    """

    slot: Slot
    matched: tuple[Path, ...]
    missing: tuple[str, ...]
    # The matched paths that are scaffold placeholders (`is_stub`), not answers. Kept in
    # `matched` too, so where the placeholder sits stays visible — it is the file to write.
    stubs: tuple[Path, ...] = ()

    @property
    def filled(self) -> bool:
        """Filled means at least one `fill` pattern resolved to a file that is not a placeholder.

        Deliberately ANY, not ALL: a slot may list several files that together answer it
        (`languages` names a Go, a TS and a Python contract) and a repo with no Python is
        not thereby missing the slot. A pattern that matched nothing is still reported in
        `missing`, so a genuinely incomplete fill is visible without being fatal. A match that
        is only a placeholder answers nothing (see `STUB_MARKER`).
        """
        return any(m not in self.stubs for m in self.matched)

    @property
    def stub(self) -> bool:
        """Something is there, and all of it is a placeholder: unfilled, and saying so."""
        return bool(self.matched) and not self.filled

    @property
    def state(self) -> str:
        """`filled`, `stub` or `unfilled` — the one word a report prints for this slot."""
        return "filled" if self.filled else "stub" if self.stub else "unfilled"


@dataclass(frozen=True)
class CommandNeed:
    """What one command declares it needs, read from its spine."""

    command: str
    path: Path
    requires: tuple[str, ...]
    optional: tuple[str, ...]


@dataclass
class Registry:
    """The parsed slot registry, plus whatever was wrong with it.

    Three severities, because three different people fix them. `errors` is a file that
    cannot be trusted to gate anything. `warnings` is a claim this checkout cannot honour
    but another might. `notes` is a fact about the file's shape — the legacy registry
    still works, and reporting it as a failure would only teach people to switch the check
    off before they migrate.
    """

    path: Path | None
    slots: tuple[Slot, ...] = ()
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    # Questionnaire ids this registry takes no position on at all, named so "we never asked"
    # is distinguishable from "we asked and have no answer" — the two look identical in a
    # count. Under the thin shape this is optional questions only, because shared and
    # mandatory ones are surveyed whether the repo names them or not.
    unanswered: tuple[str, ...] = ()
    # 1 = the legacy self-contained shape, 2 = `fill`-only answers merged with the
    # questionnaire. 0 = neither parsed.
    shape: int = 0

    @property
    def present(self) -> bool:
        return self.path is not None and self.path.is_file()

    def by_id(self) -> dict[str, Slot]:
        return {s.id: s for s in self.slots}


@dataclass
class Survey:
    """The whole answer: what is filled, what is missing, and which commands can run."""

    root: Path
    registry: Registry
    fills: tuple[Fill, ...] = ()
    needs: tuple[CommandNeed, ...] = ()
    # slot ids named by a command's `requires`/`optional` that the registry does not define
    unknown_slot_refs: tuple[tuple[str, str], ...] = ()
    # `consumed_by` entries naming a command with no spine in this checkout
    unknown_command_refs: tuple[tuple[str, str], ...] = ()
    # The shipped questionnaire's rows: the VOCABULARY a declared id is measured against. An id
    # in here but absent from `fills` is a question this repo declined, never an unknown one
    # (ENG-17852) — see `vocabulary` and the block in `survey` that measures the same thing.
    questions: tuple[Slot, ...] = ()

    def fill_of(self) -> dict[str, Fill]:
        return {f.slot.id: f for f in self.fills}

    def vocabulary(self) -> dict[str, Slot]:
        """Every slot id anything defines — this repo's resolved rows over the questionnaire's."""
        return {**{q.id: q for q in self.questions}, **{f.slot.id: f.slot for f in self.fills}}

    def unfilled(self, *, tier: str | None = None, requirement: str | None = None) -> list[Fill]:
        out = [f for f in self.fills if not f.filled]
        if tier is not None:
            out = [f for f in out if f.slot.tier == tier]
        if requirement is not None:
            out = [f for f in out if f.slot.requirement == requirement]
        return out

    def blocked_commands(self) -> list[tuple[CommandNeed, list[str]]]:
        """Commands that cannot run here, each with the mandatory slot ids blocking them.

        A command is blocked by an unfilled slot it `requires`, and by nothing else — an
        unfilled `optional` slot degrades the run and is never a blocker. An unknown slot
        id in `requires` blocks too: a command declaring a need this repo has never heard
        of is not a command this repo can honestly run.
        """
        fills = self.fill_of()
        blocked: list[tuple[CommandNeed, list[str]]] = []
        for need in self.needs:
            bad = [sid for sid in need.requires if sid not in fills or not fills[sid].filled]
            if bad:
                blocked.append((need, sorted(bad)))
        return blocked


def _json_blocks(text: str) -> Iterator[str]:
    for m in _JSON_BLOCK.finditer(text):
        yield m.group(1)


@dataclass
class _Rows:
    """The outcome of parsing a `"slots"` array, whichever file it came from."""

    slots: list[Slot] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _parse_rows(rows: object, *, require_fill: bool) -> _Rows:
    """Validate a `"slots"` array into `Slot`s, reporting rather than raising.

    `require_fill` is the one difference between the two files that use this shape. A
    registry row without a `fill` is a repo that forgot to answer; a questionnaire row
    without one is the normal case, because the answer is not the questionnaire's to give.
    """
    out = _Rows()
    if not isinstance(rows, list):
        out.errors.append("`slots` is not a list — nothing can be read from it")
        return out
    seen: set[str] = set()
    for i, row in enumerate(rows):
        where = f"slot #{i + 1}"
        if not isinstance(row, dict):
            out.errors.append(f"{where}: not an object")
            continue
        sid = row.get("id")
        if not isinstance(sid, str) or not sid:
            out.errors.append(f"{where}: missing a string `id`")
            continue
        where = f"slot `{sid}`"
        if sid in seen:
            out.errors.append(f"{where}: declared twice — a slot id is the key, so a duplicate hides one of them")
            continue
        seen.add(sid)
        for key in SLOT_REQUIRED:
            if key == "fill" and not require_fill:
                continue
            if key not in row:
                out.errors.append(f"{where}: missing required field `{key}`")
        unknown = sorted(set(row) - SLOT_KEYS)
        if unknown:
            out.errors.append(f"{where}: unknown field(s) {', '.join(unknown)} — a typo here silently changes nothing")
        tier = row.get("tier", "")
        if tier not in TIERS:
            out.errors.append(f"{where}: tier `{tier}` is not one of {', '.join(TIERS)}")
        req = row.get("requirement", "")
        if req not in REQUIREMENTS:
            out.errors.append(f"{where}: requirement `{req}` is not one of {', '.join(REQUIREMENTS)}")
        fill = row.get("fill") or []
        if not isinstance(fill, list) or not all(isinstance(x, str) for x in fill):
            out.errors.append(f"{where}: `fill` must be a list of repo-relative path patterns")
            fill = []
        if not require_fill and tier == "repo" and fill:
            # The questionnaire naming a repo's path would put one repository's layout in
            # every other repository's vocabulary — the defect the split removes, reappearing
            # in the file that was supposed to remove it.
            out.errors.append(
                f"{where}: the questionnaire carries a `fill` for a repo-tier slot. "
                "Where an answer lives is the repo's to say; only shared rows ship a fill."
            )
        if req == "optional" and not row.get("degrade"):
            out.errors.append(
                f"{where}: optional slots must say what happens without them — add a `degrade` line. "
                "An optional slot with no named degrade is indistinguishable from one nobody thought about."
            )
        out.slots.append(
            Slot(
                id=sid,
                tier=tier if tier in TIERS else "repo",
                requirement=req if req in REQUIREMENTS else "mandatory",
                answers=str(row.get("answers", "")),
                fill=tuple(fill),
                consumed_by=tuple(row.get("consumed_by") or ()),
                degrade=row.get("degrade"),
            )
        )
    return out


def questions_path() -> Path:
    """The packaged questionnaire, inside this installed package."""
    return Path(__file__).resolve().parent / QUESTIONS_FILE


@lru_cache(maxsize=1)
def read_questions() -> Registry:
    """The shipped questionnaire: every slot id, and everything about it that is not a path.

    Returned as a `Registry` so both halves are validated by one code path. Cached because
    it is package data — it cannot change under a running process, and a survey over a
    dozen repos would otherwise re-read and re-validate the same file a dozen times.

    Errors are returned rather than raised even though a broken questionnaire is OUR bug,
    not a consumer's: the callers are gates, and a traceback out of a pre-commit hook
    teaches people to pass `--no-verify` — which disables far more than this check.
    """
    path = questions_path()
    if not path.is_file():
        return Registry(path=path, errors=(f"the packaged slot questionnaire is missing at {path}",))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return Registry(path=path, errors=(f"the packaged slot questionnaire does not parse: {exc}",))
    if not isinstance(data, dict) or "slots" not in data:
        return Registry(path=path, errors=('the packaged slot questionnaire has no "slots" key',))
    parsed = _parse_rows(data.get("slots"), require_fill=False)
    return Registry(path=path, slots=tuple(parsed.slots), errors=tuple(parsed.errors), shape=2)


def _merge(questions: Registry, answers: dict[str, Any]) -> Registry:
    """The shipped questions plus this repo's `fill` answers — the whole registry, resolved.

    An answer to a question nobody asked is an ERROR rather than a new slot. That is the
    single case the shared vocabulary exists to catch: before it, a typo'd id was a slot
    only that repo had, gating nothing, resolving fine, and invisible everywhere else.
    """
    # A broken questionnaire is carried forward rather than swallowed. Without this a
    # corrupt or missing package data file makes every slot vanish silently, and the report
    # reads "this repo answers nothing" — the reader is sent to fix the registry, which is
    # fine, while the actual fault is in the installed package.
    errors: list[str] = list(questions.errors)
    known = {q.id: q for q in questions.slots}
    fills: dict[str, tuple[str, ...]] = {}

    for sid, value in answers.items():
        q = known.get(sid)
        if q is None:
            errors.append(
                f"slot `{sid}`: this repo answers a question the shipped questionnaire does not ask. "
                f"The vocabulary is {QUESTIONS_FILE} in fleet-knowledge; an answer with no question is "
                "read by nothing. Fix the id, or add the question upstream and re-ship it."
            )
            continue
        if q.shared:
            errors.append(
                f"slot `{sid}`: shared slots ship WITH the command tier, so their `fill` is fixed and is "
                "not a repo's to write. Remove the row; overriding it would point the command at a file "
                "the tier does not put there."
            )
            continue
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            errors.append(f"slot `{sid}`: the answer must be a list of repo-relative path patterns")
            continue
        fills[sid] = tuple(value)

    slots: list[Slot] = []
    unanswered: list[str] = []
    for q in questions.slots:
        if q.shared:
            # Its fill ships with the tier; a repo that has the tier has the file.
            slots.append(q)
        elif q.id in fills:
            slots.append(replace(q, fill=fills[q.id]))
        elif q.mandatory:
            # Surveyed with no fill on purpose. Dropping it instead would make silence
            # quieter than an honest empty answer, and every command needing it would still
            # be blocked while the registry looked complete.
            slots.append(q)
        else:
            unanswered.append(q.id)
    return Registry(
        path=None,
        slots=tuple(slots),
        errors=tuple(errors),
        unanswered=tuple(unanswered),
        shape=2,
    )


def _baseline(questions: Registry | None = None) -> Registry:
    """What is true of a repo that has synced the command tier and answered nothing yet.

    The shared rows exactly as shipped, the repo-tier mandatory rows with no fill, and the
    optional ones in `unanswered`. It is `_merge` against an empty answer sheet, named
    because it is a distinct idea: the floor of what any checkout carrying the tier can be
    said about WITHOUT reading a line of its own registry.
    """
    return _merge(questions if questions is not None else read_questions(), {})


def read_registry(
    root: Path,
    knowledge: Path,
    rel: str = DEFAULT_REGISTRY,
    *,
    questions: Registry | None = None,
) -> Registry:
    """Parse the slot registry, reporting what is wrong rather than raising.

    A registry that will not parse is a finding, not a crash: the caller is usually a
    gate, and a traceback in a pre-commit hook teaches people to pass `--no-verify`.

    Two shapes are accepted, discriminated by the block's own keys — `"fill"` is the thin
    answers map, `"slots"` the legacy self-contained array. Neither is guessed at: a block
    carrying neither is not a registry, and is passed over so a repo's other json blocks
    (a command spine, an example) cannot be mistaken for one.
    """
    path = knowledge / rel
    if not path.is_file():
        return Registry(path=path, errors=(f"no slot registry at {rel}",))

    text = path.read_text(encoding="utf-8", errors="ignore")
    blocks = list(_json_blocks(text))
    if not blocks:
        return Registry(path=path, errors=("registry holds no fenced ```json block",))

    data: dict[str, Any] | None = None
    errs: list[str] = []
    for raw in blocks:
        try:
            candidate = json.loads(raw)
        except json.JSONDecodeError as exc:
            errs.append(f"json block does not parse: {exc}")
            continue
        if isinstance(candidate, dict) and ("fill" in candidate or "slots" in candidate):
            data = candidate
            break
    if data is None:
        return Registry(path=path, errors=tuple(errs) or ('no json block carries a "fill" or "slots" key',))

    if "fill" in data:
        answers = data.get("fill")
        if not isinstance(answers, dict):
            return Registry(path=path, errors=("`fill` must be an object mapping slot id -> [paths]",))
        merged = _merge(questions if questions is not None else read_questions(), answers)
        return Registry(
            path=path,
            slots=merged.slots,
            errors=tuple(errs) + merged.errors,
            unanswered=merged.unanswered,
            shape=2,
        )

    parsed = _parse_rows(data.get("slots"), require_fill=True)
    q = questions if questions is not None else read_questions()
    errs += list(q.errors)
    known = {s.id for s in q.slots}
    warnings = tuple(
        f"slot `{s.id}`: declared here but absent from the shipped questionnaire, so no other repo "
        f"has ever been asked it. Add it to {QUESTIONS_FILE} in fleet-knowledge, or drop it."
        for s in parsed.slots
        if known and s.id not in known
    )
    notes = (
        "this registry carries the legacy self-contained shape: every field but `fill` restates the "
        f"shipped questionnaire ({QUESTIONS_FILE}), which is a second hand-maintained copy of a "
        "vocabulary that ships. Migrate with `fleet slots --repo . --emit answers`.",
    )
    return Registry(
        path=path,
        slots=tuple(parsed.slots),
        errors=tuple(errs) + tuple(parsed.errors),
        warnings=warnings,
        notes=notes,
        unanswered=tuple(sorted(known - {s.id for s in parsed.slots})),
        shape=1,
    )


def _question_row(slot: Slot) -> dict[str, Any]:
    """One questionnaire row.

    The single writer, so a refresh is a diff of CONTENT and never of formatting — and the
    single definition of what a row even consists of, which is what lets `_row_diff` below
    say "this refresh changes `answers` and `consumed_by`" instead of "something moved".
    """
    return {
        k: v
        for k, v in (
            ("id", slot.id),
            ("tier", slot.tier),
            ("requirement", slot.requirement),
            ("answers", slot.answers),
            ("degrade", slot.degrade),
            # Only the shared rows: a repo-tier `fill` is the repo's own answer, and
            # carrying one here would put one repository's layout in the shared vocabulary.
            ("fill", list(slot.fill) if slot.shared else None),
            ("consumed_by", sorted(slot.consumed_by)),
        )
        if v is not None
    }


def _row_diff(before: Slot, after: Slot) -> tuple[str, ...]:
    """Which questionnaire fields differ between two rows for the same id.

    Compared as RENDERED rows, so a repo-tier `fill` — which never reaches the
    questionnaire — is correctly not a difference. Otherwise every repo-tier row a repo
    answers would report as amended on every refresh, and a report that says everything
    changed says nothing.
    """
    a, b = _question_row(before), _question_row(after)
    return tuple(k for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k))


@dataclass(frozen=True)
class Refresh:
    """A questionnaire refresh: every shipped row, amended by one repo's — never reduced.

    ══ WHY A REFRESH MAY ONLY ADD OR AMEND ═════════════════════════════════════
    The questionnaire is the SHARED vocabulary, and no single repository is entitled to
    define it — `slots/README.md` tells a repo that an optional question it has not taken
    on "is simply absent" from its registry, and `_merge` honours that by dropping the row
    from the resolved set. Rendering that resolved set as the new questionnaire therefore
    made a legitimate decline into a DELETION: run from this package's own repository,
    `--emit questions` returned 26 of 39 rows and silently dropped `api-contract`,
    `dev-environment`, `journeys`, `permissions`, `slices` and eight more; run from a
    second consumer, 22 of 39, dropping a different 17. A repository that answers one of
    the dropped ids — and several do — would then be answering a question nobody asks,
    which `_merge` reports as a hard error. The blast radius of a refresh depended on which
    checkout happened to run it, with no warning and no diff.

    So the shipped file is the FLOOR: every id in it survives, in its shipped order (which
    is grouped by tier and by subject on purpose, and re-deriving it from a registry's own
    order would make every refresh an unreadable reshuffle). A row the source repo speaks
    for is amended by it; a row it does not is carried forward byte-identical; an id the
    questionnaire has never asked is appended, because a command gaining a `requires:` is
    exactly what a refresh is for.

    ══ HOW A ROW STILL GETS RETIRED ════════════════════════════════════════════
    By hand, in `slot-questions.json`, in the same commit that removes the last `requires:`
    naming it — not by a flag here. A refresh reads ONE repository's registry, and that is
    the wrong evidence for "no command needs this any more": the commands ship from this
    package, so the deletion belongs in the change that makes it true, reviewed beside it.
    A `--prune` flag would only relabel the accident as intentional while leaving it one
    mistyped `--repo` away. The report below names every carried-forward row, so a row that
    ought to be gone is visible on every refresh rather than discovered a release later.
    """

    slots: tuple[Slot, ...]
    # Ids the shipped questionnaire has never asked, appended from the source registry.
    added: tuple[str, ...] = ()
    # Shipped ids the source registry changes, each with the fields that differ.
    amended: tuple[tuple[str, tuple[str, ...]], ...] = ()
    # Shipped ids the source registry restates identically.
    unchanged: tuple[str, ...] = ()
    # Shipped ids the source registry says nothing about — the rows this class exists for.
    carried: tuple[str, ...] = ()

    def block(self) -> str:
        """The questionnaire file itself, ready to replace `slot-questions.json`."""
        rows = [_question_row(s) for s in self.slots]
        return json.dumps({"version": 1, "slots": rows}, indent=2, ensure_ascii=False) + "\n"

    def report(self) -> list[str]:
        """What this refresh changes, in the words of the rows it changes.

        Printed BESIDE the file rather than folded into it, because a refresh whose diff
        nobody reads is precisely how the silent-deletion defect above survived: the output
        was piped into the packaged file and the 13 vanished rows never appeared anywhere a
        person looks.
        """
        out = [
            f"{len(self.slots)} row(s) out — {len(self.added)} added, {len(self.amended)} amended, "
            f"{len(self.unchanged)} unchanged, {len(self.carried)} carried forward untouched"
        ]
        if self.added:
            out.append(f"added:    {', '.join(self.added)}")
        for sid, fields in self.amended:
            out.append(f"amended:  {sid} ({', '.join(fields)})")
        if self.carried:
            out.append(f"carried:  {', '.join(self.carried)}")
            out.append("          this repo takes no position on those, so they are kept exactly as shipped.")
            out.append(f"          Retiring one is a hand edit of {QUESTIONS_FILE}, never a side effect of a refresh.")
        return out


def refresh_questions(source: Registry, *, questions: Registry | None = None) -> Refresh:
    """The shipped questionnaire with one repo's registry laid OVER it — the refresh path.

    `source` is a registry of either shape. Rows it shares with the shipped file win;
    rows it never mentions survive untouched. See `Refresh` for why the direction of that
    merge is the whole point.

    A `questions` with no rows (a corrupt or missing package data file, which `read_questions`
    reports rather than raises) degrades to rendering `source` verbatim. That is the old
    behaviour, and it is the right floor: with no shipped file there is nothing to preserve,
    and refusing would leave the one command that can rebuild it unusable.
    """
    shipped = questions if questions is not None else read_questions()
    have = {s.id: s for s in source.slots}

    rows: list[Slot] = []
    amended: list[tuple[str, tuple[str, ...]]] = []
    unchanged: list[str] = []
    carried: list[str] = []
    for q in shipped.slots:
        answered = have.get(q.id)
        if answered is None:
            rows.append(q)
            carried.append(q.id)
            continue
        rows.append(answered)
        diff = _row_diff(q, answered)
        if diff:
            amended.append((q.id, diff))
        else:
            unchanged.append(q.id)

    known = {q.id for q in shipped.slots}
    added = [s.id for s in source.slots if s.id not in known]
    rows.extend(s for s in source.slots if s.id not in known)

    return Refresh(
        slots=tuple(rows),
        added=tuple(added),
        amended=tuple(amended),
        unchanged=tuple(unchanged),
        carried=tuple(carried),
    )


def questions_block(registry: Registry, *, questions: Registry | None = None) -> str:
    """A questionnaire file, refreshed from a registry that carries every field.

    THE REFRESH PATH, and the reason it is code rather than a note in a README. The
    questionnaire's content is derived from a repo that already answers every question;
    re-deriving it by hand is the copy step this whole module removes.

    It merges rather than replaces — a repo's registry can add a row or amend one, and can
    never subtract. `Refresh` carries the argument and the measurements.
    """
    return refresh_questions(registry, questions=questions).block()


def answers_block(registry: Registry) -> str:
    """This repo's half, rendered from a registry of either shape — the migration itself.

    Emitted as the fenced block a registry file carries rather than a bare document,
    because the file it goes into is prose a human reads and the block is the part a
    machine does.
    """
    fills = {s.id: list(s.fill) for s in registry.slots if not s.shared}
    return "```json\n" + json.dumps({"version": 2, "fill": fills}, indent=2, ensure_ascii=False) + "\n```\n"


def read_command_needs(root: Path, commands_dir: str | None = None) -> tuple[CommandNeed, ...]:
    """Every command spine in the checkout, with the slot ids it declares.

    A command with no spine contributes nothing rather than being reported: spines are
    being adopted incrementally, and a check that failed on every un-spined command would
    be a gate nobody could turn on.
    """
    base = root / (commands_dir or default_commands_dir(root))
    if not base.is_dir():
        return ()
    needs: list[CommandNeed] = []
    for path in sorted(base.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not _SPINE_COMMAND.search(text):
            continue
        for raw in _json_blocks(text):
            try:
                spine = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(spine, dict) or "command" not in spine:
                continue
            needs.append(
                CommandNeed(
                    command=str(spine["command"]),
                    path=path,
                    requires=tuple(spine.get("requires") or ()),
                    optional=tuple(spine.get("optional") or ()),
                )
            )
            break
    return tuple(needs)


def required_for(needs: Iterable[CommandNeed], *, questions: Registry | None = None) -> tuple[str, ...]:
    """The repo-tier slot ids a set of command spines requires, sorted.

    The scaffold must write an answer document for every repo-tier slot its core closure
    needs; the list is DERIVED from the spines here rather than written as a constant, so a
    command that gains a `requires:` cannot leave the scaffold pointing at a question nobody
    answers. `needs` comes from `read_command_needs` — the one spine parser — so the closure
    and this enumeration cannot disagree about what a command needs.

    Only repo-tier ids: a shared slot ships with the tier, so the scaffold has nothing to
    write for it.
    """
    repo = {s.id for s in (questions if questions is not None else read_questions()).slots if s.tier == "repo"}
    needed = {sid for n in needs for sid in n.requires if sid in repo}
    return tuple(sorted(needed))


# A shared fill names the tier at its `.claude/` home, the spelling `slot-questions.json` ships;
# a checkout synced to the plugin layout carries the same file under `.fleet/`.
_TIER_FILL = re.compile(r"^\.claude/(?=(?:process|registers|rubrics|commands)/|board-guidance\.json$)")


def _match(root: Path, pattern: str) -> list[Path]:
    if any(ch in pattern for ch in "*?["):
        return sorted(p for p in root.glob(pattern) if p.exists())
    p = root / pattern
    return [p] if p.exists() else []


def _resolve(root: Path, pattern: str) -> list[Path]:
    """Paths in `root` matching one `fill` pattern. A literal path is checked directly, and a
    tier path is found in whichever layout the checkout is synced to."""
    hits = _match(root, pattern)
    if not hits and _TIER_FILL.match(pattern):
        hits = _match(root, _TIER_FILL.sub(".fleet/", pattern, count=1))
    return hits


def survey(
    root: Path,
    knowledge: Path,
    *,
    registry_rel: str = DEFAULT_REGISTRY,
    reference: Registry | None = None,
    commands_dir: str | None = None,
    questions: Registry | None = None,
) -> Survey:
    """Read the registry, probe every slot against the tree, and join it to the commands.

    `reference` answers the question this tool exists for: *what is a repo that has no
    registry missing?* A repo with nothing declared has no slot list of its own, so the
    honest comparison is against one that does — pass another repo's registry and every
    slot it declares is probed here.

    ══ WHY A REPO WITH NO REGISTRY IS STILL SURVEYED ═══════════════════════════
    It used to fall to an empty slot list, and the first thing a new repository ever saw
    from this tool was therefore a lie. Measured on a freshly-synced checkout: 47 files
    written, `commands verify` in sync, and then "32 of 34 commands blocked", blaming
    eight SHARED-tier ids — `process-envelope`, `process-interview`,
    `registers-triage-partition` and five more — every one of which was on disk, put
    there by the sync two seconds earlier. The repo was told to fix files it had just
    been given, in the one report it runs to find out what it owes.

    The shared half is never a repo's to supply: its questions AND its fills both ship in
    `slot-questions.json`, so its state is a fact about the command tier in this checkout
    and does not depend on the registry file at all. So when nothing supplies a slot list,
    fall to `_baseline` — the shared rows with their shipped fills, plus the repo-tier
    MANDATORY rows unfilled, which is the honest report: the tier is here, and the only
    thing blocking a command is a question this repo has not answered yet.
    """
    qreg = questions if questions is not None else read_questions()
    reg = read_registry(root, knowledge, registry_rel, questions=qreg)
    if reg.slots:
        slots = reg.slots
    elif reference is not None and reference.slots:
        # An explicit `--reference` is a repo-tier comparison the caller asked for by name,
        # and it already carries the shared rows, so it outranks the baseline.
        slots = reference.slots
    else:
        base = _baseline(qreg)
        slots = base.slots
        # The optional questions are in neither half of any tier fraction below, and a repo
        # with no registry has not "declined" them so much as never seen them. Carrying the
        # list across is what lets the one report an onboarder runs name them.
        reg = replace(reg, unanswered=base.unanswered)

    def _fill(s: Slot) -> Fill:
        matched = tuple(m for pat in s.fill for m in _resolve(root, pat))
        return Fill(
            slot=s,
            matched=matched,
            missing=tuple(pat for pat in s.fill if not _resolve(root, pat)),
            # Shared slots ship with the tier and are never a scaffold placeholder; only the
            # repo's own answers are probed.
            stubs=() if s.shared else tuple(m for m in matched if is_stub(m)),
        )

    fills = tuple(_fill(s) for s in slots)
    needs = read_command_needs(root, commands_dir)

    # ══ THE VOCABULARY IS THE QUESTIONNAIRE, NOT THIS REPO'S ANSWERS ═══════════
    # An id is unknown when NO questionnaire asks it — a typo, which is what this report
    # is for. It is NOT unknown merely because this repo declined to answer it: `_merge`
    # drops an unanswered optional slot from the resolved set, and measuring against that
    # set made "the documented way to decline a question" (`slots/README.md`: *"A question
    # this repository has not taken on at all is simply absent"*) produce 62 error-level
    # findings on a repo that had done exactly as told, for ids the shipped questionnaire
    # defines. Worse, the two readers disagreed about it: `fleet slots` printed those ids
    # under `not answered` and blocked nothing, while `fleet check --only slots` called the
    # same file broken — and a gate that contradicts its own reporting twin is a gate people
    # learn to switch off. Declining is already reported, correctly, twice: once as
    # `unanswered`, and once per command through `blocked_commands` when it was `requires`.
    known_slots = {s.id for s in slots}
    vocabulary = known_slots | {q.id for q in qreg.slots}
    unknown_slot_refs = tuple(
        (n.command, sid) for n in needs for sid in (*n.requires, *n.optional) if sid not in vocabulary
    )
    known_cmds = {n.command for n in needs}
    unknown_command_refs = tuple((s.id, c) for s in slots for c in s.consumed_by if known_cmds and c not in known_cmds)
    return Survey(
        root=root,
        registry=reg,
        fills=fills,
        needs=needs,
        unknown_slot_refs=unknown_slot_refs,
        unknown_command_refs=unknown_command_refs,
        questions=qreg.slots,
    )
