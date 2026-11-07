"""The program board: what to do next, who has to do it, and the command that does it.

`fleet_knowledge.knowledge` answers *"what is written down, and how does it join up"* — as an
entity model something else serves, since the second HTML generator that used to answer it was
deleted rather than migrated. This answers a different question, one tier up: **"what should I
pick up, what is stuck, and which rows are not mine at all"** — in the words of the decision
rather than the words of the data model.

Six readings over the same three registers, and one shape for all of them:

  * **what to do next** — every finding, grouped by what you would actually *do* about it;
  * **programs** — the roll-up, sortable and filterable;
  * **dependencies** — depth over the slice graph. Depth, never time;
  * **health** — inconsistencies in the corpus itself, each carrying its fix;
  * **commands** — the catalogue, cross-checked against what is on disk;
  * **one entity page** for a program, a slice and a PRD, built from the same header and the
    same two-line list as everything else.

Three things this module owes its readers.

**Priority is resolved, not copied, and the authored numbers ARRIVE FROM THE CALLER.** `ranks`
takes one mapping — a program id to the position somebody put it in — and resolves it over the
graph. Lowest number wins, and a rank reaches an entity three ways: *authored* (the caller
placed this very program), *program* (a program's OWN authored rank pushed down to its slices
and their PRDs) and *dependency* (propagated backwards along the graph to a fixpoint, because a
prerequisite of your #1 is itself #1). One rule there is load-bearing: **downward inheritance
uses a program's OWN authored rank, never its inherited one.** Otherwise one urgent slice makes
every sibling in that program urgent, and the ranking flattens to noise within a cycle.
`rankSrc` travels with every rank so the page can say where it came from, and show an inherited
one differently from one a human wrote — and a PROGRAM also carries `authored`, the number the
human wrote on it (`0` for none), because the resolved triple alone cannot say whether a person
placed a program whose own cut pulled it somewhere more urgent (ENG-10673).

**Not every row is yours.** A status the caller declares as automated (`fleet.statuses`)
produces a row that *reports* rather than one that hands over a command — because a command
the reader must not run is worse than no command at all.

**NOTHING HERE IS AUTHORED — not any more, and there is no exception.** The order used to be a
markdown register in the corpus (`priorities.md`, `| Entity | Why now |`, row order as the
rank), and this module read it. It does not, and the file is not looked for: an order that
needed a pull request against another repository to change was an order nobody changed. The
authored numbers now live where a human can write them — `fleet_program_rank` in
`fleet-service`, one row per program, written from the Priorities page — and they reach this
module as the `authored` argument. **A caller with none passes `{}` and everything is unranked**,
which is what the standalone page renders: this package holds no database and acquires none.

**Deliberately absent, and required to stay absent:** any date, duration, rate, projection,
velocity or "what fits" calculation. Ordering is dependency order or the human's authored
rank; progress is a count. A test tokenises this module's code to keep it that way.

**No command string lives here.** The commands a finding names, the catalogue, the words for
whoever runs the automation and the set of commands that are *designed but not built yet* are
all the CALLER's — a JSON file passed as `--guidance`, because they are a property of the
project the board is pointed at. Baking one project's vocabulary in is exactly the coupling
that stops this being reusable. With no guidance the board still renders: rows simply carry
no command.

The page template is `templates/program-board.html`, a real .html file with `__DATA__`,
`__TITLE__` and `__INTENT_TAB__` placeholders — pass `--template` to swap the look entirely.

**The style and the renderer are separate files, and they are shared.** `templates/fleet.css`
and `templates/board.js` are inlined into the standalone page through `__STYLE__` and
`__SCRIPT__`, and `fleet-service` serves those same two files, byte for byte, to the deployed
app that fetches its payload from the API instead of reading a baked one. One copy of the
design language and one copy of the renderer, two pages. Two copies is how they drift, and
drift in the state colours is not cosmetic — they are the vocabulary.

Stdlib only.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import commands as commands_mod
from . import corpus, page, planningmode, registers, rollup
from . import slots as kb_slots
from .config import Config
from .corpusref import Corpora, is_qualified, own_name
from .paths import repo_root

TEMPLATE_NAME = "program-board.html"
#: The design language and the renderer, as files rather than as blocks inside the template.
#: `fleet-service` reads these exact paths to serve the deployed app, so a change to either
#: reaches BOTH pages or neither — which is the whole reason they are files.
STYLE_NAME = "fleet.css"
SCRIPT_NAME = "board.js"
DEFAULT_OUT_NAME = "program-board.html"
DEFAULT_TITLE = "Program Board"

# What the first view is called. A LABEL AND NOT A FILE: the register that used to sit behind
# it is gone. "Programs", because that is what the page now is: the flat "what to do next" list
# folded into each program's own "To do here", so the old name described a page that no longer
# exists — and it overrode the shell's own "Programs" on every corpus that set no title of its own.
DEFAULT_INTENT_TITLE = "Programs"

# Slices excused from needing a proof of their own, one id per line. A ratcheted waiver file,
# so an accepted exception stops being reported as an open finding.
DEFAULT_WAIVER_FILE = "slices/UNCLAIMED.baseline"
# The same file one tier up: programs whose composed proof is deliberately not planned. Same
# grammar, same ratchet, same reader — `waived()` below reads both.
DEFAULT_PROGRAM_WAIVER_FILE = "programs/UNCLAIMED.baseline"

# Whoever runs the automated half, when the caller has not said. Neutral on purpose: a
# project that has one names it, and a project that has none never sees the word.
DEFAULT_ACTOR = "the automation"

# The "unranked" sentinel. Larger than any register anyone will author, and never rendered:
# it becomes 0, which the page reads as "no rank".
UNRANKED = 10**6

# Findings, grouped by what you would DO about them. `{actor}` / `{Actor}` are filled from the
# caller's vocabulary; a caller may replace a title or a blurb outright via `guidance.groups`.
GROUPS: tuple[tuple[str, str, str], ...] = (
    (
        "finish",
        "Finished, but cannot say so",
        "The work is done. Something small is missing that stops the model ever reading proven.",
    ),
    # THE ONE ROW A `complete` PROGRAM CARRIES. Until it existed a complete program raised
    # nothing at all — every finding here is about work that has not finished — so the only
    # program the board could honestly call done was the one program with no next step on its
    # page. Closing it IS the next step: the arithmetic reads complete, and a person judges
    # whether the proof drove the composed thread. That judgement has a command, and this row
    # hands it over. Right behind `finish`, because the two are the same reading one `proofok`
    # apart and should sort beside each other when their severities tie.
    (
        "close",
        "Proven — close it",
        "Every slice reads proven and the composed proof shipped. What is left is a judgement — "
        "that the proof actually drove the whole thread — and closing it is a person's act.",
    ),
    (
        "empty",
        "Nothing to work on",
        "A program with no slices. Nothing can be planned or dispatched into it at all.",
    ),
    (
        "undecomposed",
        "Cut, but never decomposed",
        "Slices exist and the program names no decomposition roots, so no build order can be "
        "derived and the plan cannot be replayed. Distinct from a program with no slices: this "
        "one looks planned from every count on its row. Decomposing comes before driving — the "
        "fleet drives nothing here until the roots are named, and nothing dispatches the "
        "decomposition on its own, so the program waits on a person until somebody asks.",
    ),
    (
        "stalled",
        "Stalled",
        "Slices exist, nothing is in flight, and it is not finished. Nobody is moving these.",
    ),
    (
        "planning",
        "In flight, and your move",
        "A live PRD sitting at a planning stage. {Actor} runs a planning step only when it is asked "
        "to — a Fill from the PRD's page, or a program somebody drives — so these wait on you or on "
        "that ask.",
    ),
    (
        "advance",
        "With {actor}",
        "The PRDs {actor} dispatches and implements. Nothing for you to do here — this is the board "
        "telling you it is moving without you.",
    ),
    (
        "refine",
        "A slice nobody has said the finish of",
        "An open slice with no success criteria: nothing says what would have to be seen for it to "
        "count as done. Refining it comes before writing its PRDs.",
    ),
    (
        "thin",
        "A program with one slice",
        "A program is meant to hold at least two slices; with one it is a slice with a longer name.",
    ),
    (
        "promise",
        "A promise with no work",
        "A slice was cut and no PRD was ever written for it.",
    ),
    (
        "start",
        "Ready to start, and other work waits on it",
        "Prerequisites are met, nothing is live, and something downstream is waiting.",
    ),
    # THIS MEMBERSHIP IS THE WHOLE OF THE ROW, and its absence was a silent one. `actions()`
    # has emitted `"hygiene"` from four places since it was written — a program with no bar, a
    # program with no proof, a slice with neither — and this tuple never named the key. The
    # page filters its findings to the groups it is HANDED (`board.js`, `viewNext`), so those
    # findings reached the payload, survived every round trip through the store, rendered on
    # each entity's own page, and never once appeared on the view whose entire job is to say
    # what to do next: 21 live findings on the deployed corpus, none of them on the page.
    #
    # Last, because it is the lowest-severity group and the sort is stable — a `sev: 3` row is
    # ordered behind everything urgent by `viewNext` regardless, and declaration order is what
    # breaks the tie when two groups share a best rank.
    (
        "hygiene",
        "Nothing here can ever be proven",
        "A program or a slice that names no proof, or authors no bar. Nothing states what "
        "would have to be seen, so no amount of work finishing will ever mark it done. These "
        "are judgements rather than tasks: what is missing is a sentence only you can write.",
    ),
)


# ─────────────────────────── the caller's vocabulary ───────────────────────────


@dataclass(frozen=True)
class Vocabulary:
    """The command strings and actor words the board prints. The caller's, never the package's.

    Every field has a default that renders *something* honest, so a board with no guidance at
    all is a board whose rows carry no command — not a crash and not an empty page.
    """

    #: Stable finding name -> command template. `{id}` is the entity the finding is about.
    commands: dict[str, str] = field(default_factory=dict)
    #: PRD status -> the command that advances a PRD sitting at it. `{id}` is its number.
    next_command: dict[str, str] = field(default_factory=dict)
    #: The statuses an automated dispatcher claims. A PRD at one of these is reported, never
    #: handed to the reader as something to run.
    fleet_statuses: tuple[str, ...] = ()
    actor: str = DEFAULT_ACTOR
    wait: str = ""
    note: str = ""
    #: Commands the design offers that nobody has built yet. ONE place, so a command landing
    #: is a one-line edit rather than a hunt through the page.
    unbuilt: tuple[str, ...] = ()
    #: The SHAPING commands, per entity kind: `{"program": (fleet, terminal), …}`. `fleet` is
    #: the headless command a page's button hands the entity to; `terminal` is the attended
    #: command that does the same with a person in the room, offered beside it as a link. Both
    #: are templates with `{id}`. A kind the caller did not declare has no button — the page
    #: renders none, and nothing here guesses one — which is what lets a corpus that has never
    #: carried the shaping commands render exactly as it did before they existed.
    shape: dict[str, tuple[str, str]] = field(default_factory=dict)

    @classmethod
    def from_guidance(cls, g: Mapping[str, Any]) -> Vocabulary:
        fleet: Mapping[str, Any] = g.get("fleet") or {}
        actor = str(fleet.get("actor") or DEFAULT_ACTOR)
        return cls(
            commands={str(k): str(v) for k, v in (g.get("actionCommands") or {}).items()},
            next_command={str(k): str(v) for k, v in (g.get("nextCommand") or {}).items()},
            fleet_statuses=tuple(str(s) for s in (fleet.get("statuses") or ())),
            actor=actor,
            wait=str(fleet.get("wait") or f"Waiting for {actor} to implement it"),
            note=str(fleet.get("note") or ""),
            unbuilt=tuple(str(s) for s in (g.get("unbuilt") or ())),
            shape=_shape_table(g.get("shape")),
        )

    def opener(self) -> str:
        """The actor word at the start of a sentence."""
        return self.actor[:1].upper() + self.actor[1:]

    def _fill(self, template: str, **kw: str) -> str:
        """A template with its argument substituted, or verbatim when it names another key.

        A caller's template is data, and a `{}` in it must never take the page down — the
        worst honest outcome is a command printed with its placeholder still showing.
        """
        if not template:
            return ""
        try:
            return template.format(**kw)
        except (KeyError, IndexError):
            return template

    def command(self, name: str, entity_id: str = "") -> str:
        """The runnable command for a finding, or "" when this project has none for it."""
        return _offerable(self._fill(self.commands.get(name, ""), id=entity_id))

    def next_for(self, status: str, entity_id: str = "") -> str:
        """The command that advances a PRD sitting at `status`, or ""."""
        return _offerable(self._fill(self.next_command.get(status, ""), id=entity_id))

    def is_built(self, cmd: str) -> bool:
        """Whether the command behind a row actually exists yet."""
        return not cmd or cmd.split()[0] not in self.unbuilt

    def shape_for(self, kind: str, entity_id: str) -> tuple[str, str, bool]:
        """`(fleet command, terminal command, fleet command is built)` for one entity.

        Empty strings and `False` when the caller declared no `shape` table, or none for
        this kind — the honest "no button" a page renders as nothing. `built` is `False`
        rather than `True` on an empty command, unlike `is_built`, because the question it
        answers is *whether the button's tool exists*, and a button that does not exist has
        no tool.
        """
        fleet_tpl, terminal_tpl = self.shape.get(kind, ("", ""))
        fleet_cmd = self._fill(fleet_tpl, id=entity_id)
        terminal_cmd = self._fill(terminal_tpl, id=entity_id)
        return fleet_cmd, terminal_cmd, bool(fleet_cmd) and self.is_built(fleet_cmd)

    def is_fleet(self, status: str) -> bool:
        return status in self.fleet_statuses

    def prose(self, text: str) -> str:
        return self._fill(text, actor=self.actor, Actor=self.opener())


def _offerable(cmd: str) -> str:
    """A command as a row hands it over: its name and its words, never a `--flag` (ENG-10704)."""
    return " ".join(tok for tok in cmd.split() if not tok.startswith("--"))


def _shape_halves(row: Mapping[str, Any]) -> set[str]:
    """A row's shape pair as a row hands each half over — the fleet's command and the attended one — minus empties."""
    return {c for c in (_offerable(str(row.get("shape") or "")), _offerable(str(row.get("shapeTerminal") or ""))) if c}


def _shape_table(raw: object) -> dict[str, tuple[str, str]]:
    """The guidance's `shape` table, normalised: `{kind: (fleet, terminal)}`.

    Every entry is optional and every malformed one is DROPPED rather than raised on — a
    string where a table belongs, a missing half. The guidance is data a caller wrote, and a
    typo in it must never take the page down; the worst honest outcome is a kind with no
    button, which is also what an undeclared kind gets.
    """
    out: dict[str, tuple[str, str]] = {}
    if not isinstance(raw, Mapping):
        return out
    for kind, entry in raw.items():
        if not isinstance(entry, Mapping):
            continue
        fleet_cmd = entry.get("fleet")
        terminal_cmd = entry.get("terminal")
        pair = (
            fleet_cmd if isinstance(fleet_cmd, str) else "",
            terminal_cmd if isinstance(terminal_cmd, str) else "",
        )
        if any(pair):
            out[str(kind)] = pair
    return out


def _stamp_shape(row: dict[str, Any], kind: str, entity_id: str, vocab: Vocabulary) -> None:
    """The three shape fields on one row — `shape`, `shapeTerminal`, `shapeBuilt`.

    Called from `drive` (programs) and `advance` (slices and their PRDs) and from nowhere
    else, ON PURPOSE. A consumer that stores a board's typed rows rebuilds the payload by
    calling exactly those two functions after its own row reconstruction; a third stamping
    function would be a payload field the rebuild cannot reproduce until it learns the new
    call, and the two payloads would disagree over every row. Riding on the calls the rebuild
    already makes keeps a freshly built board and a rebuilt one the same object.
    """
    row["shape"], row["shapeTerminal"], row["shapeBuilt"] = vocab.shape_for(kind, entity_id)


def default_template() -> Path:
    """The template that ships with the package."""
    return _templates() / TEMPLATE_NAME


def stylesheet() -> Path:
    """The shared design language. Inlined here, served verbatim by `fleet-service`."""
    return _templates() / STYLE_NAME


def script() -> Path:
    """The shared renderer. Inlined here, served verbatim by `fleet-service`."""
    return _templates() / SCRIPT_NAME


def _templates() -> Path:
    return Path(__file__).resolve().parent / "templates"


def _asset(template: Path, name: str, fallback: Path) -> str:
    """A template's own copy of a shared asset, or the shipped one.

    Beside the template first, so `--template` genuinely swaps the LOOK: a replacement in its
    own directory brings its own `fleet.css` and `board.js` and gets them. For the shipped
    template the two paths are the same file, which is what makes this resolution invisible
    in the normal case and what makes the change-reaches-both-pages test able to prove
    something by editing one file.
    """
    beside = template.resolve().parent / name
    chosen = beside if beside.is_file() else fallback
    return chosen.read_text(encoding="utf-8")


def load_guidance(path: Path | None) -> dict[str, Any]:
    """The optional guidance file: this project's command vocabulary. `{}` when absent.

    Keys, every one optional:

      * `actionCommands` — finding name -> command template (`{id}` is substituted);
      * `nextCommand` — PRD status -> the command that advances it;
      * `fleet` — `{statuses, actor, wait, note}`, describing the automated half;
      * `unbuilt` — commands the design offers that are not built yet;
      * `shape` — `{kind: {fleet, terminal}}` for `program`, `slice` and `prd`: the headless
        command a page's shaping button hands the entity to, and the attended command
        offered beside it as a link; a kind not declared renders no button;
      * `catalogue` — `[[command, acts on, when to use it, [how it is reached]], …]`;
      * `howLabel` — what each reachability key means, spelled out;
      * `catalogueScan` — `{dir, prefix, sep}`, how to find the commands ON DISK;
      * `groups` — per-group `{title, blurb}` overrides;
      * `baselines` — `[[path relative to the corpus, label], …]` of ratcheted debt files;
      * `waiverFile` / `programWaiverFile` — the two proof-waiver lists, if not the defaults;
      * `cmds` / `pipe` / `pipeLabel` — the "what you can run here" boxes.

    A FILE and not a constant, because the commands are a property of the project this board
    is pointed at. Baking one project's vocabulary into the package is exactly the coupling
    that stops it being reusable.

    **A caller that stores readings takes the command half from the CORPUS, not from here.**
    This function reads whatever document it is handed; `fleet-service` hands it the deployment's
    and then overlays the corpus's own (`sync.corpus_guidance`), because a command belongs to the
    repository that carries it and a document mounted beside the server answers for whenever the
    server last restarted. The standalone board, which reads a checkout it can see, has no such
    split to make — it is looking at one tree and one document.
    """
    if path is None or not path.is_file():
        return {}
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def waived(root: Path, filename: str = DEFAULT_WAIVER_FILE) -> set[str]:
    """Ids excused from naming a proof — a ratcheted waiver, not an exemption.

    One reader for both tiers: the programs baseline has exactly the slices baseline's grammar
    (`# ack: <id> <reason>` above an id line, comments elsewhere), so which file it is handed is
    the only difference. EVERY waived id, whatever its kind — `waiver_kinds` is what tells an
    excused one from a deferred one (2026-10-07).
    """
    return set(waiver_kinds(root, filename))


def waiver_kinds(root: Path, filename: str = DEFAULT_WAIVER_FILE) -> dict[str, tuple[str, str]]:
    """`{id: (kind, owed)}` for every id line in one waiver baseline — `registers.baseline_line`.

    `PG-17 excused` is `("excused", "")`; `PG-30 deferred: the drill record` is
    `("deferred", "the drill record")`; a bare `PG-30` is `("", "")`, a waiver with no kind, which
    the gate refuses and `registers.waiver_owed` reads as owing.
    """
    path = root / filename
    if not path.is_file():
        return {}
    out: dict[str, tuple[str, str]] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("#"):
            continue
        read = registers.baseline_line(line)
        if read is not None:
            out[read[0]] = (read[1], read[2])
    return out


def sibling_proofs(cfg: Config, repo: Path) -> dict[str, dict[str, Any]]:
    """The PRDs of every DECLARED sibling corpus that is on disk, keyed `<corpus>:<number>`.

    A `Verified by` cell may name a proof in another corpus (`sib:0770`), and the roll-up's
    proof arithmetic looks an entry up verbatim. The readers strip only an OWN-corpus qualifier,
    so a sibling's entry arrives as written — and is found only when the sibling's own PRDs are
    indexed under exactly that spelling. That is what this reads: each corpus the config
    DECLARES under `[fleet.planning.corpora]` and that is present here, through the same
    `corpusref` loader the checks resolve cross-corpus references with, so a sibling's own
    layout and own corpus name are honoured.

    Only a DECLARED sibling contributes (BUG-2785). A qualifier naming no declared corpus, or one
    declared with no path (or a path that is not here), stays unresolved — exactly as before,
    and never silently borrows this corpus's PRD of the same number. `repo` is the REPOSITORY
    root, because a declared path is repo-relative; a sibling that is not a directory is skipped
    rather than an error, which is the ordinary state of a corpus whose sibling lives elsewhere.
    """
    planning = cfg.planning if isinstance(cfg.planning, Mapping) else {}
    corpora = Corpora.from_table(planning, repo, cfg)
    out: dict[str, dict[str, Any]] = {}
    for name in corpora.declared:
        index = corpora.index(name)
        if index is None:
            continue
        for number, record in index.prds.items():
            out[f"{name}:{number}"] = dict(record)
    return out


def waiver_readings(
    root: Path, slice_rows: Iterable[Mapping[str, Any]], guidance: Mapping[str, Any]
) -> tuple[rollup.Waivers, dict[str, str]]:
    """`(waivers, owed)` for `rollup.board` — the EXCUSED ids per tier, and what every DEFERRED one owes.

    A cut is waived by its own row's `proof_waiver` (ENG-12602; the only form since ENG-12549 retired
    `slices/UNCLAIMED.baseline`) or by a legacy baseline file where a corpus still has one; a program by
    its baseline line. Only an EXCUSED waiver settles (2026-10-07); a deferred one — or one stating no
    kind — leaves its proof owed, and `owed` says what.
    """
    excused_slices, owed = registers.slice_waiver_readings(slice_rows)
    legacy = waiver_kinds(root, str(guidance.get("waiverFile") or DEFAULT_WAIVER_FILE))
    program = waiver_kinds(root, str(guidance.get("programWaiverFile") or DEFAULT_PROGRAM_WAIVER_FILE))
    excused: dict[str, set[str]] = {rollup.SLICE_TIER: set(excused_slices), rollup.PROGRAM_TIER: set()}
    for tier, read in ((rollup.SLICE_TIER, legacy), (rollup.PROGRAM_TIER, program)):
        for eid, (kind, said) in read.items():
            left = registers.waiver_owed(kind, said)
            if left is None:
                excused[tier].add(eid)
            else:
                owed.setdefault(eid, left)
    return {tier: frozenset(ids - set(owed)) for tier, ids in excused.items()}, owed


def baselines(root: Path, spec: list[Any]) -> list[dict[str, Any]]:
    """Accepted debt: the ratcheted files that may shrink and never grow, with their sizes.

    Named by the caller rather than discovered, because "which files are the ratchets" is a
    project's own list — a glob would sweep in every unrelated `.baseline` beside them.
    """
    out: list[dict[str, Any]] = []
    for entry in spec:
        rel, label = (entry[0], entry[1]) if len(entry) > 1 else (entry[0], entry[0])
        path = root / str(rel)
        if not path.is_file():
            continue
        n = sum(
            1
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
            if line.strip() and not line.startswith("#")
        )
        out.append({"label": str(label), "n": n, "file": str(rel)})
    return out


# ─────────────────────────── the slice graph ───────────────────────────


def graph(pg: list[dict[str, Any]], loose: Iterable[dict[str, Any]] = ()) -> dict[str, dict[str, Any]]:
    """Reverse edges and readiness over the slice graph, in place.

    **The slice graph no longer decides `wave`** — `prd_waves` does, from the PRDs' own
    `depends_on`. A slice's `Depends on` is an authored ORDER between cuts, kept for display
    (`dep`, `blocks`, `blockedBy`, `depthBehind`) and for rank inheritance; the blocking chains
    the fleet actually works through are PRD→PRD, and a wave read off the coarser slice edges
    drew nearly every open cut in step 0 while the real chains ran eight deep. A dependency
    cycle is a data bug a validator rejects, but the `seen` guard is what keeps a generator from
    hanging on one instead of reporting it.

    **`ready` and `blockedBy` are ORDER and display, never dispatch** (ENG-10638). A PRD may
    start once its OWN `depends_on` PRDs have shipped and its own Linear `blockedBy` is resolved;
    the cut it sits on, and the cuts that cut names, never hold it back. These readings say where
    a slice sits in the build order and what it comes after — a page may draw them, and must
    never tell a person a PRD cannot start because of them.

    **A prerequisite is finished for the order when its capability ground is met, not when
    the slice reads `complete`** (ENG-10184). `complete` waits on the cut's own composed proof;
    dependents wait only on the capability members. See `rollup.capability_ground_met`. Reading
    readiness as `state == complete` is what mutually deadlocked SL-130 and SL-137 (when the
    order still gated dispatch): the
    program's composed proof sat on the prerequisite cut and held every dependent forever
    while the proof itself waited on work inside a dependent.

    `depthBehind` counts the unfinished chain waiting ON a slice (downstream) over the slice
    edges — how deep the
    queue is that this thing is holding up. This is the CORPUS-LEVEL stand-in for "critical
    path": the operator asked for the real thing and was told it is not reachable here. The
    real critical path is `_critical_path_depth` in `fleet-service`'s `dispatch/routing.py`,
    computed per ISSUE over Linear's actual dependency edges (`ctx.rank.depth`, list-scheduling
    upward rank); this board only has the slice register's `dep` edges, which are coarser and
    exist independent of any dispatch queue. A cycle is a
    data bug elsewhere, and the `seen` guard just keeps this from hanging on one.
    """
    sl: dict[str, dict[str, Any]] = {s["id"]: s for p in pg for s in p["sl"]}
    # THE CUTS UNDER NO PROGRAM — area slices (FLT-1280) — sit in the same graph: an edge may cross
    # from one to a program's cut, and every reading below is per slice, not per program.
    sl.update({s["id"]: s for s in loose})
    # Recompute `groundMet` here so a rebuild from typed tables (which may not carry the
    # flag) still gates readiness the same way a fresh `rollup.board` would. Program
    # `proof` is the composed-proof set; member PRDs come from each slice's `prds` list.
    prog_proofs = {p["id"]: {str(x) for x in (p.get("proof") or [])} for p in pg}
    for s in sl.values():
        # An edge to ANOTHER corpus's slice (`fleet:SL-139`) names no node here; it is kept
        # visible as `externalDep` rather than dropped with the dangling ones.
        s["externalDep"] = [d for d in s["dep"] if is_qualified(d)]
        s["dep"] = [d for d in s["dep"] if d in sl]
        s["blocks"] = []
        if "groundMet" not in s:
            # Synthetic callers (cycle guards, unit fixtures) may hand bare slice
            # dicts with only `state`. Fall back to the old complete-equals-met
            # reading so those stay well-defined without inventing a ground.
            if "prds" in s:
                s["groundMet"] = rollup.capability_ground_met(
                    list(s.get("prds") or []),
                    prog_proofs.get(s.get("program", ""), set()),
                )
            else:
                s["groundMet"] = s.get("state") == "complete"
    for s in sl.values():
        for d in s["dep"]:
            sl[d]["blocks"].append(s["id"])

    behind: dict[str, int] = {}

    def downstream(sid: str, seen: tuple[str, ...] = ()) -> int:
        if sid in behind:
            return behind[sid]
        if sid in seen:
            return 0
        # Downstream depth still keys off full completion: a cut that is only
        # ground-met (proof still open) is still unfinished work waiting behind
        # its prerequisites, and the board's "how deep is the queue" reading
        # should say so. Readiness is the only place groundMet substitutes.
        waiting = [b for b in sl[sid]["blocks"] if sl[b]["state"] != "complete"]
        behind[sid] = 0 if not waiting else 1 + max(downstream(b, (*seen, sid)) for b in waiting)
        return behind[sid]

    for sid, s in sl.items():
        s["blocks"].sort()
        s["depthBehind"] = downstream(sid)
        s["blockedBy"] = [d for d in s["dep"] if not sl[d].get("groundMet")]
        s["ready"] = not s["blockedBy"]

    for p in pg:
        # How much of the REST of the board waits on this program — the reading that says
        # which program to point hands at, and the one a per-program bar chart hides.
        p["blast"] = len({b for s in p["sl"] for b in s["blocks"] if sl[b]["program"] != p["id"]})
    return sl


# ─────────────────────────── the PRD waves ───────────────────────────


#: The program states a wave is not read for: finished, or out of the plan by a written decision.
_SETTLED_PROGRAM_STATES: frozenset[str] = frozenset({"complete", "waived", "withdrawn"})


def prd_waves(
    pg: list[dict[str, Any]], sl: dict[str, dict[str, Any]], prds: Iterable[Mapping[str, Any]]
) -> dict[str, int]:
    """`wave` on every open PRD, slice and program, from the PRDs' own `depends_on` — in place.

    **This is DEPTH, never time.** Two things in the same wave are independent; two in different
    waves cannot swap. Three rules, one per tier, and each tier waits on the one beneath it:

      * **a PRD** that is still open (not shipped, not cancelled) is wave 0 when every PRD it
        `depends_on` is terminal, else one past the deepest open PRD it names. A terminal
        prerequisite is met and does not count; one the corpus does not carry is dangling and
        is the validator's finding, not a wait. A dependency cycle is folded — every member
        reads the same wave (`rollup.depths`) — rather than cut wherever recursion entered it.
      * **a slice** that is still open (`open_slice`) waits on its open PRDs, and on any open
        PRD its own proof names: one past the deepest of them. An open cut with no open PRD —
        nothing cut yet, or only its proof to name — is wave 0: nothing stands in front of it.
      * **a program** that is not complete or parked waits on its open slices and on its open
        composed-proof PRDs: one past the deepest. A program with neither is wave 0.

    A settled thing — a terminal PRD, a complete or parked slice or program — reads `None`: it
    is not in any wave, and a `0` would draw it as startable.

    `prds` is EVERY PRD the corpus carries — `n`, `status`, `dep` — not only the ones a slice
    claims, because a claimed PRD can wait on an unclaimed one and the chain runs through it
    either way. Each claimed PRD's board entry (`slice["prds"][i]`) gains `dep`, the edges as
    authored, and `wave`. The returned mapping is `n -> wave` over the open PRDs, so a caller
    can place the unclaimed ones too.

    **Slice `Depends on` plays no part** — see `graph`. It is display ordering between cuts.
    """
    rows = {str(r["n"]): r for r in prds}
    open_prds = {n: r for n, r in rows.items() if str(r["status"]) not in rollup.PRD_TERMINAL}
    depth = rollup.depths({n: [str(d) for d in (r.get("dep") or [])] for n, r in open_prds.items()})

    def deepest(nums: Iterable[str]) -> int | None:
        found = [depth[n] for n in nums if n in depth]
        return max(found) if found else None

    for s in sl.values():
        for entry in s.get("prds") or []:
            n = str(entry["n"])
            entry["dep"] = [str(d) for d in (rows.get(n, {}).get("dep") or entry.get("dep") or [])]
            entry["wave"] = depth.get(n)
        if not open_slice(s):
            s["wave"] = None
            continue
        under = deepest([str(e["n"]) for e in s.get("prds") or []] + [str(x) for x in s.get("proof") or []])
        s["wave"] = 0 if under is None else under + 1

    for p in pg:
        state = p.get("state")
        if p.get("complete") or state in _SETTLED_PROGRAM_STATES:
            p["wave"] = None
            continue
        found = [s["wave"] for s in p.get("sl") or [] if s.get("wave") is not None]
        proof = deepest(str(x) for x in p.get("proof") or [])
        if proof is not None:
            found.append(proof)
        p["wave"] = 1 + max(found) if found else 0
    return depth


# ─────────────────────────── priority ───────────────────────────


#: The program states that are out of the plan: a waived proof, a withdrawal. A program in one reads
#: no rank of its own (ENG-10692) — see `ranks`. `rollup.board`'s words, and `board.js`'s `PARKED`.
PARKED_PROGRAM_STATES: frozenset[str] = frozenset({"waived", "withdrawn"})

#: The slice states in which a need on that slice is MET (ENG-10692): nothing more is coming from it.
#: `ranks` also counts a slice whose capability ground is met (`groundMet`, stamped by `graph` from
#: `rollup.capability_ground_met`) — the same gate `ready` and `blockedBy` already wait on, so the
#: order and the readiness of a dependent can never disagree about whether a prerequisite is done.
FINISHED_SLICE_STATES: frozenset[str] = frozenset({"complete", "withdrawn", "waived"})


def _need_met(s: Mapping[str, Any]) -> bool:
    """Whether a need on this slice — or this slice's need on anything — is already met."""
    return s.get("state") in FINISHED_SLICE_STATES or bool(s.get("groundMet"))


def ranks(
    pg: list[dict[str, Any]],
    sl: dict[str, dict[str, Any]],
    authored: Mapping[str, int],
) -> None:
    """Resolve every entity's effective rank, in place. Lowest number always wins.

    `authored` is the numbers a HUMAN placed, keyed by **program id** — `{"PG-01": 1}` — and it
    is the caller's to supply. This module reads no file for it and reaches no database: the
    deployed board passes `fleet_program_rank`, and the standalone page passes `{}` because
    outside a service there is nowhere an order could have been written.

    **Only programs carry an authored number.** *"Maybe we start with priorities only on the
    programs and see how this works before we go deeper."* Everything else INHERITS, which is
    what makes about twenty rows a list somebody maintains — and the inheritance is the whole
    point, not a fallback. Three ways a rank arrives, and the page says which:

      * `authored` — the caller placed this very program;
      * `program` — its program's OWN authored rank, pushed down to its slices and their PRDs;
      * `dependency` — something ranked waits on it, so it is at least as urgent, transitively.

    A program is then read back UP as `slice`: as urgent as the most urgent cut inside it, or as
    its own number, whichever is lower.

    **Downward inheritance uses a program's own authored rank, never its inherited one.** A
    program that is urgent only because one of its slices is urgent must not make its other
    slices urgent too — that is how a ranking flattens into noise inside a cycle or two.

    **A program nobody placed stays at rank `0`, and that is an absence rather than a position.**
    Every page that renders it draws it as "unranked" and sorts it after everything placed; there
    is no number that means "nobody said", which is why the sentinel above never escapes.

    **`rankRoot` names the program whose placement a rank IS** (ENG-10692), carried forward along
    every hop, so a program pulled up through one of its cuts reads "PG-09 needs it" on a page
    rather than "via SL-118". `dispatch.tiers.Placed.root` is the same fact on the other consumer.

    **A parked program — waived or withdrawn — reads no rank of its own** (ENG-10692). It is out of
    the plan, and the UP pass used to hand production's withdrawn PG-14 "#1 via SL-089" because a
    placed program still needs a slice it once held. Only the PROGRAM's reading is withheld: its
    cuts keep theirs, which is the half `tiers.resolve` shares and dispatch reads (an issue resolves
    to a slice, never to a program), and `authored` still carries any number somebody placed on it.

    **A met need confers nothing** (ENG-10692). Urgency travels backwards only along an edge that is
    still OPEN at both ends: the waiting slice has work left, and so does the slice it waits on
    (neither complete, withdrawn or waived, nor with its capability ground met — `_need_met`). On
    production every inherited priority on the board flowed through a finished slice — PG-21, placed
    5th, read "priority 2" because PG-08 once needed SL-135, which had long been complete — and a
    need that has been met is no reason for anything to be urgent. It stops the chain as well: what a
    finished slice once waited on is nobody's need now.

    **This resolution is load-bearing for DISPATCH, not just for a page** — and it is duplicated
    on purpose. `fleet_service.dispatch.tiers.resolve` is the same three passes over the same
    numbers, applied to the issue queue rather than to a payload, and `tests/dispatch/test_tiers.py`
    holds each rule with a test that fails if it inverts. Change one and the other is wrong; treat
    a change to the three resolution paths or to "lowest wins" as a behavioural change with two
    consumers.
    """
    prog_own = {p["id"]: authored.get(p["id"], 0) for p in pg}

    rank: dict[str, int] = {}
    src: dict[str, str] = {}
    frm: dict[str, str] = {}
    # Whose authored number each rank ultimately is — `tiers.Placed.root`'s twin (ENG-10692).
    root: dict[str, str] = {}
    for s in sl.values():
        # DOWN, and there is one candidate because there is one authored tier. A slice acquires
        # a number no program authored only through the pass below, which is exactly why that
        # pass may not feed this one.
        own = prog_own.get(s["program"], 0)
        rank[s["id"]], src[s["id"]], frm[s["id"]], root[s["id"]] = (
            (own, "program", s["program"], s["program"]) if own else (UNRANKED, "", "", "")
        )

    # Backwards along the graph to a fixpoint: a prerequisite of an urgent slice is urgent — through
    # an OPEN edge only (ENG-10692): a finished slice needs nothing, and a finished prerequisite is
    # needed by nobody. Bounded by the number of slices, because every pass must strictly lower some rank.
    met = {s["id"] for s in sl.values() if _need_met(s)}
    for _ in range(len(sl) + 1):
        moved = False
        for s in sl.values():
            v = rank[s["id"]]
            if v >= UNRANKED or s["id"] in met:
                continue
            for dep in s["dep"]:
                if dep in rank and dep not in met and v < rank[dep]:
                    rank[dep], src[dep], frm[dep], root[dep] = v, "dependency", s["id"], root[s["id"]]
                    moved = True
        if not moved:
            break

    for s in sl.values():
        s["rank"] = 0 if rank[s["id"]] >= UNRANKED else rank[s["id"]]
        s["rankSrc"], s["rankFrom"] = src[s["id"]], frm[s["id"]]
        s["rankRoot"] = root[s["id"]] if s["rank"] else ""
        for r in s["prds"]:
            # A PRD is exactly as urgent as the slice holding it: it is how that slice moves.
            r["rank"] = s["rank"]
            r["rankSrc"] = "slice" if s["rank"] else ""
            r["rankFrom"] = s["id"] if s["rank"] else ""

    # UP, and this writes nothing the downward pass reads.
    for p in pg:
        own = prog_own[p["id"]]
        # THE PERSON'S OWN NUMBER TRAVELS BESIDE THE RESOLVED ONE (ENG-10673). `min(cands)` below
        # may hand a placed program a lower number through one of its cuts — a prerequisite of
        # somebody else's #1 — and then `rankSrc` says `slice`, truthfully, about the RESOLUTION.
        # Every page that asked "did a person place this program" used to read that same triple,
        # so a program placed at 5 and pulled to 2 by a dependency read as unplaced: drawn under
        # the "Not ranked" line, and dropped from the next whole-order write, which clears what it
        # omits. `0` is the same absence `rank` uses, stamped on EVERY program so a missing key
        # can never be mistaken for a missing placement.
        p["authored"] = own
        if p.get("state") in PARKED_PROGRAM_STATES:
            p["rank"], p["rankSrc"], p["rankFrom"], p["rankRoot"] = 0, "", "", ""
            continue
        cands: list[tuple[int, str, str, str]] = [(own, "authored", p["id"], p["id"])] if own else []
        cands += [(s["rank"], "slice", s["id"], s["rankRoot"]) for s in p["sl"] if s["rank"]]
        p["rank"], p["rankSrc"], p["rankFrom"], p["rankRoot"] = min(cands) if cands else (0, "", "", "")


# ─────────────────────────── what to do next ───────────────────────────


def _index(pg: list[dict[str, Any]], sl: dict[str, dict[str, Any]]) -> dict[str, tuple[int, str, str]]:
    """Every entity's resolved rank, keyed by id, so a finding inherits the rank of its subject."""
    ent: dict[str, tuple[int, str, str]] = {p["id"]: (p["rank"], p["rankSrc"], p["rankFrom"]) for p in pg}
    ent.update({s["id"]: (s["rank"], s["rankSrc"], s["rankFrom"]) for s in sl.values()})
    ent.update({r["n"]: (r["rank"], r["rankSrc"], r["rankFrom"]) for s in sl.values() for r in s["prds"]})
    return ent


def advance(sl: dict[str, dict[str, Any]], vocab: Vocabulary) -> None:
    """Stamp each PRD with the command that advances it — or with the fact that it is not yours.

    A status the caller declared automated gets `fleet: true` and NO command. That asymmetry is
    the point: handing a reader a command they must not run is worse than handing them nothing.

    And the SHAPING affordance on every slice and every PRD — `shape`, `shapeTerminal`,
    `shapeBuilt`, from the caller's `shape` table — stamped here rather than in a function of
    its own, for the reason `_stamp_shape` gives: this is one of the two calls a rebuild from
    typed rows already makes. Whether a page SHOWS the button is the host's reading of the
    row (a stub, a cut from a brief); this module says only what the button would run.
    """
    for s in sl.values():
        _stamp_shape(s, "slice", s["id"], vocab)
        # A RECORD OFFERS NO ATTENDED STEP (ENG-10704, B-01). A live PRD in a cut the register took out of the
        # plan — its own row withdrawn or superseded, or its program withdrawn — is given no command. The roll-up
        # derives that `withdrawn` state once (`rollup.board`), `actions` already raises nothing for such a cut,
        # and it is the same fact the shaping route refuses a fill on (`dispatch.shaping.past_shaping`): a live
        # PRD keeps its program in flight, so a closed program is never the reason here.
        withdrawn = s.get("state") == "withdrawn"
        for r in s["prds"]:
            r["fleet"] = vocab.is_fleet(r["status"])
            r["closed"] = "withdrawn" if withdrawn and r["status"] not in rollup.PRD_TERMINAL else ""
            r["cmd"] = "" if r["fleet"] or r["closed"] else vocab.next_for(r["status"], r["n"])
            r["built"] = vocab.is_built(r["cmd"])
            # NO STEPS WRITTEN AT ALL IS NOT WORK UNDER WAY (ENG-17173). A vocabulary that writes PRD
            # steps and none for this status describes work in progress; a corpus with no vocabulary
            # writes none for ANY status, and its untouched stub read "Under way". Stamped so the
            # page says what it does not know instead.
            r["noSteps"] = (
                not vocab.next_command and not r["fleet"] and not r["closed"] and r["status"] not in rollup.PRD_TERMINAL
            )
            _stamp_shape(r, "prd", r["n"], vocab)


#: The one next step a program has, derived from its state — `program_step`'s closed set.
#: Every value is a DECISION about what a person does next, never a ship-state, and exactly
#: one of them holds for a program at a time. In ladder order:
#:
#:   * `withdrawn`  — the register said stop; nothing is owed and nothing is offered.
#:   * `closed`     — `ship`'s arithmetic holds AND the HOST says the program's closing check passed
#:                    (`closed` on the row: the day it passed, joined on from the host's own record of the
#:                    check — `with_closed`). This package never derives it: program state is the host's,
#:                    not the documents'. Closed: nothing is owed and nothing is offered — no close row, no
#:                    driver. PROD v0.7.141: PG-21's check passed and every board surface still read `ship`
#:                    and offered "Close the program", because only the drive box knew.
#:   * `ship`       — the program's own named proof shipped and every kept slice reads complete
#:                    or waived (`rollup.SETTLED_SLICE_STATES`): close it. A waived cut is
#:                    settled by a written decision and no longer stands between the program
#:                    and closing (the operator's decision, 2026-09-17) — an EXCUSED waiver only
#:                    (2026-10-07). A DEFERRED waiver owes its proof: the cut reads
#:                    `awaiting-proof`, counts as open, and the program reads `deliver` (or
#:                    `prove`, for its own) until that proof lands.
#:   * `decompose`  — no slices; or slices, no decomposition roots (`requires == []`), nothing
#:                    in flight, AND a decomposition would still fill something in — no proof
#:                    named, or a kept slice still empty (ENG-10704 item 8, walking back
#:                    ENG-10672's "whatever is in flight"). Missing roots on a program that
#:                    fails that last test are hygiene, not a step: `finished`, something in
#:                    flight, or every slice already cut with a proof named all excuse it, and
#:                    the ladder reads the step the slices already carry instead.
#:   * `prove`      — decomposed, no proof named and no waiver: nothing can read complete, so
#:                    nothing is driven until a proof is named or waived. THE ONE STEP, and the
#:                    driver is withheld (`program:deliver` §1a refuses such a program). Also the
#:                    step of a program whose own proof a DEFERRED waiver leaves owed once no cut
#:                    is open (2026-10-07): the owed proof is what is left, and it is never parked.
#:   * `waived`     — no cut is left open and the program's OWN proof is waived by a decision
#:                    written in the programs baseline: parked by that decision, never proven by
#:                    construction, and nothing is offered (ENG-10683). A program whose named
#:                    proof shipped over waived cuts is `ship` now, not this.
#:   * `proof`      — no cut is left open and the named proof has not shipped: the only work
#:                    left is the proof's own, and the row names its next verb.
#:   * `deliver`    — a proof is named or waived, and cuts are open: drive it. A waiver ANSWERS
#:                    the proof requirement, so a waived program is driven toward the cuts it
#:                    kept (ENG-10683).
PROGRAM_STEPS: tuple[str, ...] = ("withdrawn", "closed", "ship", "decompose", "prove", "waived", "proof", "deliver")


def finished(p: Mapping[str, Any]) -> bool:
    """Every slice this program KEPT reads `complete` or `waived` — the arithmetic is one `proofok` away.

    `complete` on the row is `done == nsl and proofok` (rollup), so this is exactly *"the only
    thing left is this program's own proof"* — the claim the `finish` rows make and the reading
    that decides between `proof` and `deliver` below.

    `unproven` USED TO COUNT HERE and that was the bug. An `unproven` cut is one whose PRDs are
    all terminal and whose proof has not shipped — named-but-unshipped, or never named at all —
    so it has outstanding work of its own and the program's cell is NOT the only thing left. A
    slice in flight is not `complete`, so `done == kept` already excludes it.

    A WITHDRAWN CUT IS OUT OF THE ARITHMETIC (`rollup.board`'s own rule for `complete`), so it
    is out of `finished` too: a program that finished every cut it kept is one `proofok` away,
    however many it stopped. `.get` because a rebuilt row from before the count was stored
    carries none, and none is the reading the count is additive over.

    A WAIVED CUT IS SETTLED TOO (`rollup.SETTLED_SLICE_STATES`, 2026-09-17): no proof is planned
    for it by a written decision, so it no longer stands between the program and its close. Only an
    EXCUSED waiver makes a cut `waived` (2026-10-07); a DEFERRED one reads `awaiting-proof`, is not
    counted here, and keeps the program open.
    """
    kept = int(p["nsl"]) - int(p.get("withdrawnSlices") or 0)
    return kept > 0 and int(p["done"]) + int(p.get("waivedSlices") or 0) == kept


def closable(p: Mapping[str, Any]) -> bool:
    """Whether the program is FINISHED and may be closed — `rollup.board`'s `complete`, read off a row.

    Its own named proof shipped, and every cut it kept is complete or waived. The same arithmetic
    `rollup.board` stamps as `complete`; read here as well so a row whose stored `complete` predates
    the rule (a generation derived before 2026-09-17) still reads the step the rule gives it. A
    program whose OWN proof is waived names no proof, so it is never closable: it stays parked.
    """
    return bool(p.get("proof")) and bool(p.get("proofok")) and not open_slices(p) and finished(p)


def open_slices(p: Mapping[str, Any]) -> int:
    """How many of this program's cuts are OPEN — `open_slice`'s reading, counted off the row.

    `flight` + `unproven` (awaiting a proof, or unproven) + `idle` (empty or abandoned): every state
    but `complete` and the two parked ones, which is exactly `open_slice` summed over the program's
    cuts, so the page's open figures and the ladder's cannot disagree about what is still standing.

    COUNTED FROM THE THREE OPEN COUNTS, NEVER AS `nsl - done - parked`. The row the lease path reads
    (`fleet-service`'s stored program row) carries these three and not the parked counts, and a
    subtraction over absent parked counts would read every waived cut as open — production's PG-10,
    three cuts complete and one waived, offered a driver with nothing in it. A row missing all
    three reads 0: nothing is offered on a count nobody read.
    """
    return int(p.get("flight") or 0) + int(p.get("unproven") or 0) + int(p.get("idle") or 0)


def _slice_shaped(s: Mapping[str, Any]) -> bool:
    """One kept slice reads `empty` — cut, but no PRD has ever landed in it.

    ENG-10704, item 8: a decomposition run is the ONE run that both names a program's roots and
    drops the first PRDs into every slice a brief pointed at, so an EMPTY slice is exactly what a
    decomposition would still have to fill in. A slice that already carries its own PRDs —
    `flight`, `complete`, `unproven`, whatever — has nothing left for one to write. Read off the
    per-program slice rows (`p["sl"]`, the same rows `program_chain`/`viewProgram` render from),
    never a second derivation of "empty": `rollup.board`'s own state word, verbatim.
    """
    return s.get("state") != "empty"


def _slice_bare(s: Mapping[str, Any]) -> bool:
    """Whether nothing a refine writes is there yet — the slice half of `dispatch/shaping.py`'s
    `bare()`, mirrored over the served row (ENG-10768).

    `shaping.bare` reads the typed row's columns (`bar_status`, `proof`, `n`); this reads the
    same three facts off the rolled-up slice row the findings builder already holds: no bar
    (`bar` is `None` when the slice authored no `## Bar`), no proof named, and no PRDs cut under
    it. The shape box renders "Shape it" off exactly this reading on the host's side, so the two
    cannot disagree about which slices are still unshaped. An `empty` cut already has no proof
    and no PRDs — that is its state word — so over this loop the bar is the deciding column, but
    all three are checked for the reason `bare()` names: the predicate is one definition, not
    three ad-hoc ones.
    """
    return not s.get("bar") and not list(s.get("proof") or []) and not list(s.get("prds") or [])


def decompose_would_fill(p: Mapping[str, Any]) -> bool:
    """Whether running this program's decomposition would still hand it something it lacks —
    a named proof, or PRDs for a slice that has none (ENG-10704, item 8).

    Not "whether `requires` is empty": a program can be short of its roots and have every kept
    slice already cut with its own PRDs and a proof shipped — production's PG-21, five of six
    slices done with roughly sixty shipped PRDs between them, one slice (`SL-188`) in flight. A
    decomposition run over that program has nowhere left to write: no empty slice to seed, no
    proof to name. Missing roots there are a filing gap, not a step — `decompose_would_fill`
    reads false and `program_step` moves on to read the state the slices already carry.
    """
    return not p["proof"] or any(not _slice_shaped(s) for s in p.get("sl") or [])


def is_closed(p: Mapping[str, Any]) -> bool:
    """Whether the program is CLOSED — finished, and the host says its closing check passed (`closed`, the day
    it passed, joined on by the host: `with_closed`). `.get` because a board with no host — the standalone
    page — carries none, and none reads as not closed: the arithmetic's own reading."""
    return bool(p.get("closed")) and (bool(p.get("complete")) or closable(p))


def with_closed(payload: Mapping[str, Any], closed: Mapping[str, str]) -> dict[str, Any]:
    """The board payload with the HOST'S closed reading joined on — `closed` is `{program id: day its closing
    check passed}`, the host's own record (fleet-service: `api/candidates.closed_programs`, over its database).

    Exactly what `program_step`, `program_phase`, `drive` and `actions` give a row carrying `closed` — without
    rebuilding the payload, which the host memoises per generation while its record moves on its own clock: the
    row gains `closed`, its phase reads `closed`, it offers no driver, and every program-tier row `actions` would
    no longer emit for it (its id's rows — "Close the program" first) is dropped. A program the arithmetic does
    not read finished is left as it is (`is_closed`). EVERY program row carries the key — `None` for one not
    closed — so the page reads one field on every row. The input is never mutated."""
    marked: dict[str, str] = {}
    programs: list[dict[str, Any]] = []
    for p in payload.get("programs") or []:
        day = closed.get(str(p.get("id") or ""))
        if day and is_closed({**p, "closed": day}):
            marked[str(p["id"])] = day
            programs.append({**p, "closed": day, "phase": "closed", "deliver": "", "deliverMissing": False})
        else:
            programs.append({**p, "closed": None})
    if not marked:
        return {**payload, "programs": programs}
    actions = [a for a in payload.get("actions") or [] if str(a.get("id") or "") not in marked]
    return {**payload, "programs": programs, "actions": actions}


def with_owners(payload: Mapping[str, Any], owners: Mapping[str, Any]) -> dict[str, Any]:
    """The board payload with the HOST'S responsible-people link joined on — `owners` is
    `{program id: [email, …]}`, the host's own record (fleet-service: `store.owners.ProgramOwnerStore`,
    over its database).

    The exact shape of `with_closed`, and joined the same way for the same reason: who is
    responsible for a program is a host fact that moves on its own clock while the board payload is
    memoised per immutable generation, so it is joined AFTER the memo (`api/board.py`) — the memo key
    gains no term, `store.rebuild` and `build` gain no call, and the ETag is over the joined bytes. A
    freshly set owner is served on the next read with no commit and no cache invalidation.

    EVERY program row carries `owners` — `[]` for one that names nobody — so the narrowed list reads
    one field on every row and an unowned program is the ordinary case rather than a missing key. A
    program the host record does not mention reads `[]`, which is exactly what AC-2/AC-4 need: it
    appears in no one's narrowed list. The input is never mutated."""
    rows: list[dict[str, Any]] = []
    for p in payload.get("programs") or []:
        named = owners.get(str(p.get("id") or "")) or []
        rows.append({**p, "owners": [str(email) for email in named]})
    return {**payload, "programs": rows}


def program_step(p: Mapping[str, Any]) -> str:
    """THE ONE NEXT STEP for a program — a value of `PROGRAM_STEPS`, derived from its state.

    One derivation, read by `drive()` and `actions()` both, so the driver box and the rows can
    never disagree about what a program needs next. They used to: the driver was stamped on
    EVERY program unconditionally, and the *no proof named* row fired from an independent
    predicate — so a program with no proof offered `prove` and `deliver` side by side, two
    Start controls for one program, and a reader who took the second one started a session
    with no finish line. Measured on the corpus this package was extracted from: every delivery
    cycle ever run against one program ran with its proof cell empty, and the second of them
    dispatched a proof PRD of its own — the party choosing the proof to fit what it was
    building — which was later cancelled as slice-shaped. A cycle with nothing to finish
    invents a finish.

    The ladder is strict and the ORDER is the rule: `withdrawn` beats everything (the register
    decided), `ship` beats `prove` (a complete program has its proof by definition), `decompose`
    beats `waived`, `prove` AND `deliver` (a program with no slices has no composed thread to
    write a sentence for, and a program with slices but no decomposition roots was never
    decomposed — the decomposition is the one run that names the roots AND the first proof, and
    prove's own rule against re-running it binds only a program that has been through it), and
    `prove` beats `deliver` — which is the whole of the decision this encodes. **No proof, no
    driver — and no roots, no driver either.** `program:deliver` itself refuses a program whose
    cell is empty and which no waiver answers, so offering it here would be offering a command
    that stops on its first step.

    **A waiver answers the proof requirement (ENG-10683).** This function used to read `waived`
    for every program in the programs baseline whatever its cuts were doing, and `waived` offers
    nothing. Measured on production `v0.5.64`, 2026-09-14: PG-17 — waived, two cuts in flight —
    could not be driven, and PG-30's drive box said the fleet drives a program only towards a
    proof, over a program whose baseline line is a person's written decision that no composed
    proof is planned. The waiver IS the answer to *no proof named*, so a waived program with an
    open cut (`open_slices`) is `deliver`, and `waived` is kept for the end where no cut is open —
    nothing left to drive, and never proven by construction. `prove` stays refused: §1a of the
    driver refuses a cycle on an empty cell no waiver answers. OPEN, NOT `finished`: a waived CUT
    counts against `finished` forever (done == kept never holds), and a program whose only
    unfinished cut is waived has nothing in it to drive.

    **And a NAMED proof reads open cuts the same way.** Production's PG-13 (proof shipped, one cut
    proven, one waived *will not be built*) and PG-24 (four cuts done, three waived whose drills
    were never run) read `deliver` because `finished` could not hold, and the page said *"Stalled —
    nobody is moving this"* over a Start driving no cycle could act on. With no cut open the step
    is `proof` while the named proof has not shipped — the proof's own work, as before — and `ship`
    once it has (`closable`, 2026-09-17): a waived cut no longer stands between that program and
    closing. It used to read `waived` there, and PG-13's page asked a person to un-waive a cut a
    person had already decided would not be proven.

    **Decomposed is a prerequisite for driving ONLY WHILE A DECOMPOSITION WOULD STILL FILL
    SOMETHING IN (ENG-10672, walked back by ENG-10704 item 8).** This function used to say
    `deliver` for a program with a proof named and `requires == []`, and call the missing roots
    "a structural repair beside the driver". Measured on the production board, 2026-09-14,
    PG-21: `flight`, proof shipped, five of six slices done, `Requires` empty — the
    `undecomposed` finding on its page said decompose while the drive box, reading the same row
    through this function, offered a Start; the fleet ran five delivery cycles on it, two of
    which asked the operator questions. *"Decompose is usually the very first step, how can
    there be questions before that?"* Two derivations of one row disagreed, and the fleet worked
    a program nobody had decomposed. So `requires == []` became `decompose` here, ahead of the
    proof's arms, and `drive()`, `candidates.drivable` and the findings all read it.

    **That rule outlived the state it was written for.** Measured again, 2026-09-15: the SAME
    PG-21, moved on — proof still shipped, five of six slices complete with roughly sixty PRDs
    shipped between them, its sixth (`SL-188`) in flight with one PRD already shipped and one
    planned with the fleet. `requires` is still `[]`; nothing about this program is missing a
    decomposition would fill. The unconditional rule now read `decompose` over a program almost
    done implementing, with the fleet already mid-flight on it — the operator's complaint this
    time ran the other way: *"why does this still show Decompose when it's almost done?"* A
    decomposition names roots AND drops PRDs into empty slices; a program with no empty slice
    and a named proof has nothing left for one to do, whatever `requires` reads. So the ladder
    now asks `decompose_would_fill(p)` too — a named proof outstanding, or a kept slice still
    `empty` — and ONLY THEN treats missing roots as the step, and only while nothing is in
    flight: a program already moving is left to finish moving rather than stopped for a repair
    that can wait, exactly as `finished` already stops the OLD rule for a program with every cut
    done. Missing roots on a program this rule now passes over are hygiene, not a step: the
    `undecomposed` flag still names them (worded to match, ENG-10704), just off the ladder.

    `requires == []` and never falsiness: `None` is a rebuilt row from before the field was
    stored and means NOBODY READ IT, so it decides nothing here — exactly as the `undecomposed`
    finding treats it. And it decides nothing on a `finished` program either: decomposing a
    program whose slices are all complete derives gaps that no longer exist, which is prove's
    own reason for existing, so there the proof is the step and the missing roots stay a
    structural repair beside it — and a finished program is never driven, so the two
    derivations cannot disagree there.

    A program that is `finished` and awaiting its named proof is `proof`, not `deliver`: the
    only work left is the proof PRD's own, and the `finish` row already names that PRD's next
    verb (or the drill somebody has to run). Offering the driver beside it would be the second
    Start control this function exists to remove.
    """
    if p.get("state") == "withdrawn":
        return "withdrawn"
    if is_closed(p):
        return "closed"
    if p["complete"] or closable(p):
        return "ship"
    if not p["nsl"]:
        return "decompose"
    if p.get("requires") == [] and not finished(p) and not p.get("flight") and decompose_would_fill(p):
        return "decompose"
    if not p["proof"]:
        # A DEFERRED waiver of the program's own proof (`owed`, 2026-10-07) answers *no proof named* for
        # DRIVING exactly as an excused one does — the cuts it kept are still the finish line — but never
        # parks the program: with no cut left open the step is naming the owed proof, not `waived`.
        if not p.get("waived") and not p.get("owed"):
            return "prove"
        if open_slices(p):
            return "deliver"
        return "prove" if p.get("owed") else "waived"
    if open_slices(p):
        return "deliver"
    return "waived" if p.get("proofok") else "proof"


def drive(pg: list[dict[str, Any]], vocab: Vocabulary) -> None:
    """Stamp each program with the command that drives it — when driving is its next step.

    `advance`'s sibling one tier up, and the asymmetry with the findings is the point. Every
    other command a program page offers arrives as a FINDING: something is missing, and the row
    that says so carries the fix. Driving a program is not that: it is what a healthy, moving
    program wants, exactly when no finding fires — so the site is here whatever the board
    thinks is wrong, PROVIDED the program can be driven at all.

    **It cannot be driven without a proof named or waived, and then this stamps nothing.** `program_step` is
    the one derivation: the driver is offered only when the step is `deliver`, and a program
    with no proof named gets `""` here exactly as it gets `prove` and nothing else in
    `actions()`. The page then carries no *Drive this program* section for it — not a disabled
    one, not one beside the `prove` row: none. `program:deliver` refuses such a program on its
    first step, and a launch site for a command that refuses is the two-Start-controls defect
    this replaced.

    **Never both the box and the `stalled` row.** When nothing is in flight the `stalled`
    finding carries this same command with the reading that provoked it — strictly more than a
    box can say — so the finding is the one site and this stamps `""`. When something IS in
    flight no finding fires and the box is the one site. `flight` is the discriminator, and it
    is the same field the row keys on, so the two cannot both fire.

    `""` also when the caller's guidance names no `program_deliver`, which is a permanent and
    legitimate state of that file rather than a gap: `runbox` renders nothing on an empty
    command and the page carries no launch site. NO COMMAND IS INVENTED HERE — the same rule
    the findings hold to, and for the same reason: a plausible-looking one would be typed.

    `deliverBuilt` rides beside it for the reason `built` rides beside a PRD's `cmd`: whether
    the tool behind a command exists is the caller's `unbuilt` list to answer, and answering it
    a second time in the renderer is a second thing to keep in step.

    **`deliverMissing` says the one thing `""` cannot** (ENG-10558): that driving IS this
    program's next step and the vocabulary names no driver for it. Every other `""` is a program
    with nothing to drive, and the page rightly shows no box; this one is a program a fleet
    could be driving, on a corpus whose `fleet.toml` names no `program_deliver` — measured on the
    Harbour sample, where a fleet-driven program showed no *Drive this program* at all and nothing
    said why. The page renders one calm sentence for it rather than a box or a silence.
    """
    for p in pg:
        # THE HOST'S CLOSED READING HAS A KEY ON EVERY ROW (`with_closed` fills it): `None` here, because this
        # package never derives it — a payload built without a host reads "not closed", the arithmetic's own
        # answer, and the built and the served payloads carry the same keys.
        p.setdefault("closed", None)
        # THE HOST'S OWNER LINK HAS A KEY ON EVERY ROW TOO (`with_owners` fills it): `[]` here,
        # because this package never derives it — a payload built without a host reads "names
        # nobody", and the built and the served payloads carry the same keys (test_rebuild's
        # field-for-field contract).
        p.setdefault("owners", [])
        offered = program_step(p) == "deliver" and bool(p["flight"])
        cmd = vocab.command("program_deliver", p["id"]) if offered else ""
        p["deliver"] = cmd
        p["deliverBuilt"] = vocab.is_built(cmd)
        p["deliverMissing"] = offered and not cmd
        # The shaping affordance rides here for the reason `_stamp_shape` gives — this is the
        # program-tier call a rebuild from typed rows already makes. Stamped on EVERY program,
        # not only a skeleton one: whether the page shows the button is the host's reading of
        # the row (no narrative, `requires` empty); this module says only what it would run.
        _stamp_shape(p, "program", p["id"], vocab)
        # A FLAG NAMES ITS REPAIR (ENG-10704, X17). "no success criteria written" and "only one slice" sat on
        # the list row with no command anywhere once the Health page went. The repair is a FACT on the
        # program page, never a second Start control (the bar is a clause, not a row — see `actions`), so
        # the command rides here, beside the driver, for every program: `""` when there is nothing to repair.
        kept = p.get("state") != "withdrawn"
        no_bar = kept and p["kind"] == rollup.PROGRAM_TIER and not p["bar"]
        p["barCommand"] = vocab.command("program_bar_author", p["id"]) if no_bar else ""
        p["cutCommand"] = vocab.command("slice_create", p["id"]) if kept and int(p["nsl"]) == 1 else ""
        # WHERE THE PROGRAM IS IN ITS LIFE — the one word its row and page lead with.
        p["phase"] = program_phase(p, vocab)


#: WHERE A TO-DO SITS IN A PROGRAM'S LIFE — the ordering a person works a program page in.
#:
#: A program is not a ladder: questions, shaping and delivery run side by side, and shaping
#: reopens whenever new work turns up mid-delivery. So every row carries a `stage` — the track
#: it belongs to — and an `order`, the position a person takes it in: shape, decompose, name
#: the proof, refine the slices, write their PRDs, design, plan; then start delivery; then the
#: close. `order` is what a page sorts by; the stage is what it groups under. Questions are the
#: host's (`waiting`) and always come first, so no row here carries order 0.
STAGES: tuple[str, ...] = ("shaping", "delivery", "close")
STAGE_OF_GROUP: dict[str, tuple[str, int]] = {
    "empty": ("shaping", 2),
    "undecomposed": ("shaping", 2),
    "thin": ("shaping", 2),
    "refine": ("shaping", 4),
    "hygiene": ("shaping", 4),
    "promise": ("shaping", 5),
    "start": ("shaping", 5),
    "planning": ("shaping", 6),
    "stalled": ("delivery", 8),
    "advance": ("delivery", 8),
    "finish": ("close", 9),
    "close": ("close", 10),
}
#: A PRD's planning verb, by the status it sits at: write the stub, design, plan.
PLANNING_ORDER: dict[str, int] = {"stub": 5, "prd-drafted": 6, "designed": 7}

#: A PRD's planning verb, as the title of the to-do that makes it: write the stub, design, plan.
PRD_MOVES: dict[str, str] = {"stub": "Write", "prd-drafted": "Design", "designed": "Plan"}


def prd_move(status: str, n: str) -> str:
    """The to-do title for a PRD's next planning step — "Write PRD 0624", "Design PRD 0625"."""
    return f"{PRD_MOVES.get(status, 'Advance')} PRD {n}"


def _lead(sentence: str) -> str:
    """A sentence with its first letter raised and nothing else touched (`str.capitalize` lowers ids)."""
    return sentence[:1].upper() + sentence[1:]


def _owed_wait(cut: Mapping[str, Any], vocab: Any) -> str:
    """What one cut with a DEFERRED waiver waits on, as a sentence opening with a capital and no period.

    A proof only a production check can take (`owedNeeds == production`, 2026-10-08) says so and names the
    attended `program_deliver` that runs it (`rollup.production_check`); any other owed proof is the fleet's
    own work still to land and keeps `rollup.waiting_on`."""
    sid, owed = str(cut["id"]), str(cut["owed"])
    if cut.get("owedNeeds") == registers.NEEDS_PRODUCTION:
        return _lead(rollup.production_check(sid, owed, vocab.command("program_deliver", str(cut["program"]))))
    return _lead(rollup.waiting_on(sid, owed))


def _and(ids: list[str]) -> str:
    return ids[0] if len(ids) == 1 else f"{', '.join(ids[:-1])} and {ids[-1]}"


def close_why(p: Mapping[str, Any]) -> str:
    """The close row's first sentence: the proof that shipped, and the cuts the program closes over.

    "The proof (0582) shipped and every slice reads proven." on a clean program; otherwise the parked
    cuts by name — "The proof (0582) shipped; SL-111 was waived by decision." — because a waived or
    withdrawn cut is part of what the close records. Named off the program's own served cuts (`sl`);
    a row without them falls back to the parked counts.
    """
    proof = ", ".join(str(x) for x in p.get("proof") or [])
    lead = f"The proof ({proof}) shipped" if proof else "The proof shipped"
    cuts = list(p.get("sl") or [])
    waived_ids = [str(x["id"]) for x in cuts if x.get("state") == "waived"]
    withdrawn_ids = [str(x["id"]) for x in cuts if x.get("state") == "withdrawn"]
    parts: list[str] = []
    if cuts:
        if waived_ids:
            parts.append(f"{_and(waived_ids)} {'was' if len(waived_ids) == 1 else 'were'} waived by decision")
        if withdrawn_ids:
            parts.append(f"{_and(withdrawn_ids)} {'was' if len(withdrawn_ids) == 1 else 'were'} withdrawn")
    else:
        for count, word in ((p.get("waivedSlices"), "waived by decision"), (p.get("withdrawnSlices"), "withdrawn")):
            k = int(count or 0)
            if k:
                parts.append(f"{k} slice{'' if k == 1 else 's'} {'was' if k == 1 else 'were'} {word}")
    if not parts:
        return f"{lead} and every slice reads proven."
    return f"{lead}; {'; '.join(parts)}."


#: The one word a program's row and page lead with — `program_phase`'s closed set.
PROGRAM_PHASES: tuple[str, ...] = ("withdrawn", "closed", "proven", "waived", "closing", "building", "shaping")


def program_phase(p: Mapping[str, Any], vocab: Vocabulary) -> str:
    """Where a program is in its life, in one word — never a status anyone writes.

    * `withdrawn` / `proven` — the register's decision, and the arithmetic reading complete.
    * `closed` — proven, and its closing check passed (`program_step` reads `closed`): nothing is left.
    * `waived` — its own proof is waived and nothing is left open: parked by a decision.
    * `closing` — `program_step` reads `ship` on a row whose stored `complete` predates the
      waived-cut rule (see `closable`), or `waived` over a named proof (a program whose every cut
      was withdrawn): the close itself is what is left.
    * `building` — at least one PRD has reached a planned status (or shipped): the fleet has
      been handed work, however it got there. Shaping may still be open beside it — a new slice
      cut mid-delivery reopens shaping, it never moves a program back.
    * `shaping` — everything else: nothing has been planned yet.
    """
    step = program_step(p)
    if step == "withdrawn":
        return "withdrawn"
    if step == "closed":
        return "closed"
    if p.get("complete"):
        return "proven"
    if step == "waived":
        return "closing" if p["proof"] else "waived"
    if step == "ship":
        return "closing"
    built = {"shipped", *vocab.fleet_statuses}
    for s in p.get("sl") or []:
        if s.get("state") in ("complete", "flight", "unproven", "awaiting-proof") and any(
            str(r.get("status") or "") in built for r in s.get("prds") or []
        ):
            return "building"
    return "shaping"


def close_programs(pg: list[dict[str, Any]], mode: str) -> None:
    """STEP 4 (FLT-1282): in a repository that plans by area, a program finishes the slices it has and takes no
    new one. `closedToNewWork` on every program still open, and no command offered to cut another — the page
    says so, and the to-do list asks for no second slice. In `programs` mode nothing is written.

    And no command offered to SHAPE or DECOMPOSE one (owner, 2026-10-28, FLT-1285): in this mode `program:shape`
    and `program:decompose` refuse at their first step, so the shaping button (`drive` stamps it) is cleared here,
    and `actions` and `health` offer no decomposition on a program closed to new work. Deliver, prove and ship
    stay: the program still finishes."""
    for p in pg:
        closed = mode == planningmode.AREAS and p.get("state") not in {*rollup.CLOSED_PROGRAM_STATES, "withdrawn"}
        p["closedToNewWork"] = closed
        if closed:
            p["cutCommand"] = ""
            p["shape"], p["shapeTerminal"], p["shapeBuilt"] = "", "", False


def actions(pg: list[dict[str, Any]], sl: dict[str, dict[str, Any]], vocab: Vocabulary) -> list[dict[str, Any]]:
    """One row per thing that could be picked up, each carrying the command that does it.

    `cmd` holds the real argument, so a row is runnable rather than descriptive; `built` is
    false when the affordance is designed and the tool behind it is not.
    """
    out: list[dict[str, Any]] = []
    ent = _index(pg, sl)
    prd_status = {r["n"]: r["status"] for s in sl.values() for r in s["prds"]}
    opener = vocab.opener()

    def add(
        group: str,
        sev: int,
        eid: str,
        title: str,
        why: str,
        cmd: str,
        *,
        key: str = "",
        fleet: bool = False,
        person: bool = False,
        waiting: str = "",
        order: int = 0,
        action: str = "",
        driver: str = "",
    ) -> None:
        rk, rs, rf = ent.get(eid, (0, "", ""))
        stage, default_order = STAGE_OF_GROUP.get(group, ("shaping", 5))
        # NAMING THE PROOF IS STEP 3 WHEREVER ITS ROW IS FILED: `hygiene` while work is open and
        # `finish` once every cut is — the same move, and it comes before refining any slice.
        if key == "program_prove" and group in ("hygiene", "finish"):
            stage, default_order = "shaping", 3
        # `blocks` / `depthBehind` only exist at slice granularity (`graph()` builds them over
        # the slice register's `dep` edges) — a program or PRD id simply is not in `sl`, so it
        # reads as "blocks nothing, nothing waits behind it" rather than inventing a number.
        entity = sl.get(eid) or {}
        out.append(
            {
                "group": group,
                "sev": sev,
                "id": eid,
                "title": title,
                # THE MOVE, IN A PERSON'S WORDS (2026-09-17): "Name the proof", "Refine SL-175",
                # "Write PRD 0624", "Close the program". A to-do list titled by entity name made the
                # reader open every row to learn what it asked; the name and the reason are the
                # second line now. Stamped HERE, beside `group` / `cmdKey` / `order`, so every
                # surface reads one label and a board rebuilt from stored rows (`store.board`
                # re-runs this function) carries the same one. `title` when a caller names none.
                "action": action or title,
                "why": why,
                "cmd": "" if fleet else cmd,
                # THE GUIDANCE KEY THIS ROW ASKED FOR, carried so that an EMPTY `cmd` can be
                # reported as the defect it is rather than rendered as a considered answer. A
                # finding is emitted because something has to be done about it; a row that
                # states a problem and hands over no way to act on it is not a legitimate state
                # of this payload, it is `actionCommands` missing a key somebody deleted. The
                # renderer names this key so the fix is one edit rather than a hunt, and it
                # still invents no command — a plausible one would be typed.
                "cmdKey": "" if fleet else key,
                "fleet": fleet,
                # THE PLANNING STEP THE DRIVE TAKES ITSELF WHEN THE PROGRAM IS DRIVEN (0221): `stub` for a
                # refined cut with no PRD (`slice:refine`'s stub mode writes its PRD stub, and `fill` then
                # `design` follow on the same drive). `""` for every row a person alone moves. This board
                # cannot see whether a program is driven — that is the service's state — so the row stays
                # a to-do and the page decides, from this word and the drive, whether to show it.
                "driver": driver,
                # WHOSE MOVE IT IS (ENG-10683). `fleet` says the fleet has it; `person` says ONLY a
                # person can make it — no command the fleet dispatches and no button the page hands
                # to the fleet moves it: closing a proven program, naming a proof or running the
                # drill a finished one waits on, a planning verb the fleet does not run, and a
                # decomposed program's own *no proof named*. Every other row is an ordinary to-do —
                # the fleet does it once a person presses (decompose, cut a slice's PRDs, start
                # driving) — or an advisory. The Programs list's *needs you* view reads this field;
                # #581 read the row count, and on production 21 of 22 programs carried one.
                "person": person and not fleet,
                "waiting": waiting,
                "stage": stage,
                "order": order or default_order,
                "built": fleet or vocab.is_built(cmd),
                "rank": rk,
                "rankSrc": rs,
                "rankFrom": rf,
                "blocks": list(entity.get("blocks") or []),
                "depthBehind": entity.get("depthBehind", 0),
            }
        )

    for p in pg:
        # ONE DERIVATION DECIDES EVERY PROGRAM-TIER ROW BELOW. `program_step` is the same
        # function `drive()` reads, so the rows here and the driver box on the page are two
        # renderings of one answer rather than two predicates that can both come true. The
        # cases that used to fire independently — *no proof named* (hygiene) and *nothing in
        # flight* (stalled, carrying the driver) — are now two arms of one ladder, and a program
        # is in exactly one arm.
        step = program_step(p)
        # A WITHDRAWN PROGRAM RAISES NOTHING. Every row below asks a person to do something to
        # move a program toward complete, and the register has said this one is not going
        # there — its decision record or its successor is the answer. It is also outside
        # `program:deliver`'s frontier for the same reason; a row here would put it back in.
        # A CLOSED PROGRAM RAISES NOTHING EITHER: its closing check passed (the host's `closed`), so the one
        # row a complete program carries — "Close the program" — would ask for a close already made.
        if step in ("withdrawn", "closed"):
            continue
        # THE MISSING BAR IS A CLAUSE ON THE STEP'S ROW, NEVER A ROW OF ITS OWN. It used to be
        # one — `hygiene`, carrying `program_bar_author` — and in the guidance this package was
        # extracted with that key is spelled with the same command `prove` is, so a program
        # with a proof and no bar offered *prove* beside *deliver* on its own page: the doubled
        # Start control, arriving through the bar. A bar is not a completion condition (a
        # program without one still reads complete; `health` says so in its own words), so it
        # does not earn a second command at this tier. It stays visible everywhere it is a
        # fact: the page's header names it, `health` lists it with its repair, `totals.bars`
        # counts it, and the driver itself reports it every cycle it runs. Only at the
        # objective tier, and only there — a bar is optional across the corpus, and a clause on
        # every entity without one would teach a reader to skip the sentence it sits in.
        bar_too = p["kind"] == rollup.PROGRAM_TIER and not p["bar"]
        if step == "ship":
            # "EVERY SLICE" ONLY WHEN EVERY SLICE (ENG-10683): a withdrawn slice leaves the completion
            # arithmetic and is never proven — production's PG-12 and PG-22 said "Every slice reads proven"
            # over one and two withdrawn slices — so the row names what it can stand behind. And a WAIVED
            # cut is named the same way (2026-09-17): the program closes over it, and the record says so —
            # PG-13 reads "The proof (0582) shipped; SL-111 was waived by decision."
            proven = close_why(p)
            # THE ONE ROW A COMPLETE PROGRAM CARRIES, and it used to carry none: `complete`
            # skipped every finding, so the page of the one program the board could call done
            # was the one page with nothing to do on it. Closing it is a person's judgement —
            # that the proof drove the composed thread — and that judgement has a command.
            #
            # LEADS WITH THE MOVE (ENG-10704, L-7): the needs-you LIST line shows only the first
            # sentence (RV-03's own rule, right above), and this sentence used to open with the
            # fact — "Every slice reads proven and the proof shipped." — so the list read a fact
            # with no ask beside it, over a row whose SECOND sentence was the entire reason it is
            # in the list at all: "Close it — the one judgement left …". Every other row here
            # opens with its ask; this one now does too.
            #
            # THE MOVE IS THE ROW'S TITLE NOW ("Close the program", 2026-09-17), so the first sentence is
            # the fact that makes it closable rather than a second copy of the ask.
            add(
                "close",
                1,
                p["id"],
                p["name"],
                f"{proven} The one judgement left is whether the proof drove the whole thread, and that is yours."
                + (" No bar was authored, so nothing says what it would have to be seen doing." if bar_too else ""),
                vocab.command("program_ship", p["id"]),
                key="program_ship",
                person=True,
                action="Close the program",
            )
            continue
        if step == "prove":
            # NO PROOF, NO DRIVER — this row is the whole of what the program offers at the
            # program tier, and `drive()` stamps nothing for it. Two sentences for two
            # readings of one fact: with every kept slice finished the cell is the LAST thing
            # missing (sev 1, `finish`); with work still open it is the FIRST thing missing,
            # because nothing is driven toward a finish line nobody has named (sev 3,
            # `hygiene`). Both hand over `prove`, and nothing else on this program does. The
            # bar clause belongs here most of all: prove authors the bar in the run that names
            # the proof, so one row saying both is the honest count of things to do.
            #
            # `waived` never reaches here: the baseline IS the answer to "no proof named",
            # written by a person with the reason beside it, and `program_step` reads it —
            # `deliver` while a cut is open, `waived` once none is (ENG-10683). The `flags` on
            # the row still say it can never read complete.
            #
            # A BAR WITH NO PROOF MEANS PROVE HAS ALREADY BEEN THROUGH. Only prove authors a
            # program's bar, and its honest outcome is often *no proof yet* — the proof PRD
            # this program needs does not exist, or a fork gates whether one can. The cell is
            # then empty ON PURPOSE, and a row that reads "no proof named — run prove" sends
            # the reader back to a judgement already made. So the sentence says what the bar
            # proves, and where prove's own finding is. The command stays `prove`: re-running
            # it re-derives the same answer and offers to cut the PRD in the same session,
            # which is the one thing that fills the cell.
            been_through = p["kind"] == rollup.PROGRAM_TIER and bool(p["bar"])
            after = (
                " A bar is authored, so this has been through prove and the cell was left empty on "
                "purpose: the proof it needs does not exist yet, and prove's own finding in the "
                "program's file says what has to be cut first."
                if been_through
                else ""
            )
            both = " and no success criteria written" if bar_too else ""
            # A DEFERRED WAIVER OF THE PROGRAM'S OWN PROOF (2026-10-07) is not an excuse: the proof is owed,
            # and the row says what is owed rather than "can never be proven".
            if p.get("owed"):
                add(
                    "finish" if finished(p) else "hygiene",
                    1 if finished(p) else 3,
                    p["id"],
                    p["name"],
                    f"{_lead(rollup.waiting_on(p['id'], str(p['owed'])))}. Its waiver defers the proof "
                    f"rather than excusing it, so this program stays open until the proof is named.{after}",
                    vocab.command("program_prove", p["id"]),
                    key="program_prove",
                    person=True,
                    action="Name the proof",
                )
            elif finished(p):
                add(
                    "finish",
                    1,
                    p["id"],
                    p["name"],
                    f"Every slice is finished and no proof is named{both}, so this can never be proven.{after}",
                    vocab.command("program_prove", p["id"]),
                    key="program_prove",
                    person=True,
                    action="Name the proof",
                )
            else:
                add(
                    "hygiene",
                    3,
                    p["id"],
                    p["name"],
                    f"No proof named{both}. Nothing will ever mark this program proven, and "
                    f"nothing drives it until one is.{after}",
                    vocab.command("program_prove", p["id"]),
                    key="program_prove",
                    person=True,
                    action="Name the proof",
                )
        elif step == "proof":
            # NO CUT IS OPEN (every kept one complete, or waived) AND THE NAMED PROOF HAS NOT SHIPPED: the only
            # work left is the proof's own, and the row names that work's next verb. The driver
            # is withheld here too (`drive()`): a session that drives slices has no slice left
            # to drive, and the second Start control beside this row was the defect.
            entries = [(x, prd_status.get(x, "")) for x in p["proof"]]
            outstanding = [(x, st) for x, st in entries if registers.is_drill(x) or st != "shipped"]
            prds_out = [(x, st) for x, st in outstanding if not registers.is_drill(x)]
            n, st = (prds_out or outstanding or entries)[0]
            named = ", ".join(p["proof"])
            which = f"the proof ({named})" if len(entries) == 1 else f"of the proof ({named}), {n}"
            no_bar = " No success criteria written either." if bar_too else ""
            if registers.is_drill(n):
                stem = n.split(":", 1)[1]
                add(
                    "finish",
                    2,
                    p["id"],
                    p["name"],
                    f"All the work is done; {which} has no passing drill record yet.{no_bar}",
                    "",
                    person=True,
                    waiting=f"Run the drill {stem} and commit its passing record — no command on this board runs one",
                    action=f"Run the drill {stem}",
                )
            elif vocab.is_fleet(st):
                add(
                    "finish",
                    2,
                    p["id"],
                    p["name"],
                    f"All the work is done; {which} is planned and queued.{no_bar}",
                    "",
                    fleet=True,
                    waiting=f"{vocab.wait}: {n}",
                    action=f"Build PRD {n}",
                )
            elif st in rollup.PRD_TERMINAL:
                add(
                    "finish",
                    2,
                    p["id"],
                    p["name"],
                    f"All the work is done; {which} was {st} without shipping, so nothing will prove this "
                    f"until another proof is named.{no_bar}",
                    vocab.command("program_prove", p["id"]),
                    key="program_prove",
                    person=True,
                    action="Name the proof",
                )
            elif not st:
                add(
                    "finish",
                    2,
                    p["id"],
                    p["name"],
                    f"All the work is done; {which} names a PRD nobody has written yet.{no_bar}",
                    vocab.command("prd_create", n),
                    key="prd_create",
                    person=True,
                    action=f"Write PRD {n}",
                )
            elif vocab.next_for(st, n):
                add(
                    "finish",
                    2,
                    p["id"],
                    p["name"],
                    f"All the work is done; {which} sits at '{st}', and its next step is yours.{no_bar}",
                    vocab.next_for(st, n),
                    person=True,
                    action=prd_move(st, n),
                )
            else:
                add(
                    "finish",
                    2,
                    p["id"],
                    p["name"],
                    f"All the work is done; {which} is at '{st}' and has not shipped yet.{no_bar}",
                    "",
                    waiting=f"{n} is at '{st}'",
                    action=f"Ship PRD {n}",
                )
        if p.get("closedToNewWork"):
            # FLT-1285: a program closed to new work in a repository that plans by area is never decomposed — the
            # command refuses there — so neither the empty nor the undecomposed to-do is offered on it.
            pass
        elif not p["nsl"]:
            add(
                "empty",
                1,
                p["id"],
                p["name"],
                "No slices cut. No work can be planned or dispatched into this program.",
                vocab.command("program_decompose", p["id"]),
                key="program_decompose",
                action="Decompose the program",
            )
        elif (
            int(p["nsl"]) == 1
            and step not in ("closed", "ship", "waived", "proof", "decompose")
            and not p.get("closedToNewWork")
        ):
            # "ONLY ONE SLICE" WAS A YELLOW LINE ON THE ROW WITH NO COMMAND BESIDE IT. It is a
            # decomposition gap, so it is a to-do in the decomposition's place, and it names the
            # command that cuts the second slice. Not on a program whose work is done.
            add(
                "thin",
                3,
                p["id"],
                p["name"],
                "Only one slice cut — a program is meant to hold at least two.",
                vocab.command("slice_create", p["id"]),
                key="slice_create",
                action="Cut another slice",
            )
        if (
            int(p["nsl"])
            and step == "decompose"
            and p.get("state") not in rollup.CLOSED_PROGRAM_STATES
            and not p.get("closedToNewWork")
        ):
            # NOT ON A PROVEN OR PARKED PROGRAM (ENG-10691): a proven one, or one parked by a written
            # waiver of its proof with nothing left open, derives gaps that no longer exist — production's
            # PG-18 offered *↑ Decompose this program* in its To do while the box refused it. `program_step`
            # itself does not read `state` past `withdrawn` (a `waived`-STATE program with an open cut can
            # still return `decompose`, by design — the ladder and this row's own gate have always been
            # allowed to diverge here), so the extra guard stays on the row rather than moving into the
            # ladder, exactly as it did before item 8.
            #
            # GATED ON `step`, NOT ON `p["requires"] == []` DIRECTLY (ENG-10704 item 8). This row used to
            # fire on the bare fact of missing roots — nsl>0, not finished — which is what `program_step`
            # itself read before item 8: production's PG-21, moved on to five of six slices done and one
            # in flight with the fleet, still got told *"Decompose this program"* over a program with
            # nothing left for a decomposition to fill in. `step` is the SAME ladder the drive box and
            # `candidates.drivable` read, so once it says something other than `decompose` this row says
            # nothing at all rather than a second, looser reading of the same row.
            #
            # ONLY TWO READINGS LEFT, because `step == "decompose"` already answers the question the old
            # third one asked: this row is the whole of what the program offers here — no `prove` row and
            # NO DRIVER beside it, because decomposed is still a prerequisite for driving while a
            # decomposition would fill something in. It says more when the program ALSO names no proof:
            # the decomposition names the roots and the first proof together.
            if p.get("waived"):
                # THE WAIVER ANSWERS THE PROOF, not the roots: the baseline is a person's decision
                # that no composed proof is planned, so the row asks for the decomposition alone
                # and never for the thing the waiver settled.
                names_both = " Decomposing comes first and names the roots alone here — the waiver stands."
            elif not p["proof"]:
                names_both = (
                    " No proof is named either: the decomposition names the roots and the first proof in "
                    "one run, so it comes before prove, and nothing drives this until both exist."
                )
            else:
                # A NAMED PROOF, SO IT IS THE EMPTY SLICE THAT PUT THIS ROW HERE (ENG-10704 item 8):
                # `decompose_would_fill` only reaches this branch missing-proof-free, over a program
                # `step` has already confirmed has nothing in flight — so "whatever is in flight" (the
                # old wording) no longer describes a real case.
                names_both = (
                    " Decomposing comes before driving: a cut here still has no PRDs, and the fleet "
                    "drives nothing until the roots are named and every cut has its own."
                )
            add(
                "undecomposed",
                2,
                p["id"],
                p["name"],
                "Slices are cut but no decomposition roots are named, so no build order can be "
                f"derived and nothing reports what this program still needs.{names_both}",
                vocab.command("program_decompose", p["id"]),
                key="program_decompose",
                action="Decompose the program",
            )
        if step == "deliver" and not p["flight"]:
            # THE DRIVER, AS A FINDING. A proof is named or waived, cuts are open, and nothing is in
            # flight — so the reading is the reason to start the session, and this row carries
            # the command with it. `drive()` stamps `""` on exactly this program: the row is
            # the one site, and the box would be the second. With something in flight the row
            # does not fire and the box is the one site instead. Never both.
            kept = int(p["nsl"]) - int(p.get("withdrawnSlices") or 0)
            plural = "s" if kept != 1 else ""
            # WHAT IT WAITS ON, WHEN A DEFERRED WAIVER IS WHY IT IS NOT FINISHED (2026-10-07): the cut's proof
            # is owed, so the program is open on purpose and the row says what would close it.
            owed_cuts = [x for x in p.get("sl") or [] if x.get("owed") and x.get("state") == "awaiting-proof"]
            waits = "".join(f" {_owed_wait(x, vocab)}." for x in owed_cuts)
            add(
                "stalled",
                2,
                p["id"],
                p["name"],
                f"Stalled — {kept} slice{plural} kept, nothing in flight, not finished. Nobody is moving this."
                + waits
                + (" No success criteria written either." if bar_too else ""),
                vocab.command("program_deliver", p["id"]),
                key="program_deliver",
                action="Start delivery",
            )

    programs_by_id = {str(p["id"]): p for p in pg}
    for s in sl.values():
        # A withdrawn cut raises nothing, for the program's reason. A WAIVED one is not skipped
        # wholesale: it is excused from naming a proof and from nothing else, and the rows
        # below check `waived` where that one obligation is what they ask about.
        if s["state"] == "withdrawn":
            continue
        owner = programs_by_id.get(str(s.get("program") or ""))
        # DECOMPOSING COMES FIRST (ENG-10704, PG-29): no PRD is authored into a cut of a program whose
        # one next step is its decomposition — the run that names the roots those PRDs are written to.
        decomposing = owner is not None and program_step(owner) == "decompose"
        # NO PER-CUT "SETTLE THIS WAIVER" ROW (2026-09-17). A waived cut under a program whose own proof
        # shipped used to carry a `finish` row — "This waived slice alone keeps PG-13 from reading proven …
        # run and name its proof, or withdraw it" — asking a person to undo a decision a person had
        # already written down. The program closes over a waived cut now (`rollup.SETTLED_SLICE_STATES`),
        # so the program's own `close` row is the one move, and it names the waived cuts it closes with.
        # SHAPE BEFORE YOU FILL (ENG-10768, SL-191 under PG-16): a bare cut — no bar authored,
        # no proof, no PRDs — is one the shape box's refine is already the offer for, and the
        # promise row beside it gave the page two to-dos with nothing saying which comes first.
        # The decomposition gate above answers "whose run owns the cut's filling"; this one
        # answers "has the cut been shaped at all" (`_slice_bare`, the same reading the shape
        # box makes). `prd:create` is the next step only once a refine has been through — and
        # the shape box's attended alternative stays the only second offer, never a second row.
        # A BARE CUT GETS BOTH ROWS, IN ORDER (the program lifecycle). ENG-10768 withheld the
        # promise row from a cut nobody had refined, so the page would not show two to-dos with
        # nothing saying which comes first. The rows now carry that order (`refine` is 4,
        # `promise` 5) and the page sorts by it, so both are listed and refining leads.
        # ONLY BEFORE ITS PRDS ARE WRITTEN. Refining is the step ahead of writing the work; a cut
        # already in flight is past it, and asking it for a bar then is the backfill the bar rows
        # below refuse — reconstructed from whatever got built rather than said ahead of it.
        if s["state"] == "empty" and not decomposing and not s["bar"]:
            add(
                "refine",
                3,
                s["id"],
                s["name"],
                "No success criteria: nothing says what would have to be seen for this slice to be done.",
                vocab.command("slice_bar_author", s["id"]),
                key="slice_bar_author",
                action=f"Refine {s['id']}",
            )
        if s["state"] == "empty" and not decomposing:
            # A REFINED CUT'S FIRST PRD IS THE DRIVE'S (0221): once the cut carries its bar, a driven
            # program's drive writes the PRD stub itself (`slice:refine`'s stub mode) and the fill, the
            # design and the plan follow with no person in between. A cut nobody refined is refined first.
            refined = bool(s["bar"])
            add(
                "promise",
                2,
                s["id"],
                s["name"],
                (
                    f"A refined slice with no PRDs — a promise nobody has started. While its program is driven, "
                    f"{vocab.actor} writes its PRD stub itself; otherwise start it here."
                    if refined
                    else "A slice with no PRDs — a promise nobody has started."
                ),
                vocab.command("prd_create_in_slice", s["id"]),
                key="prd_create_in_slice",
                action=f"Write PRDs for {s['id']}",
                driver="stub" if refined else "",
            )
        elif (
            s["state"] == "awaiting-proof"
            and not s["proof"]
            and s.get("owed")
            and s.get("owedNeeds") == registers.NEEDS_PRODUCTION
        ):
            # AN OWED PROOF ONLY A PRODUCTION CHECK CAN TAKE (2026-10-08, "Keep prod checks with people"). Fleet
            # never touches production, so nothing it dispatches makes this proof land, and offering
            # `slice:edit` here put the naming AHEAD of a measurement nobody was asked to make. The move is
            # the attended `program:deliver` — its "Read the bar" step runs the slice's live checks — and the
            # naming follows in that same cycle once they pass, never as a step of its own.
            # ONLY WITH NOTHING IN FLIGHT, as `stalled` and the drive's person step read it: while the fleet
            # is still building in this program its driver box is the one site of this same command (`drive()`
            # stamps `deliver`), and a row carrying it too would hide that box (`board.js`'s "never twice").
            if not (owner or {}).get("flight"):
                add(
                    "finish",
                    2,
                    s["id"],
                    s["name"],
                    f"{_owed_wait(s, vocab)}. Its waiver defers the proof rather than excusing it, so "
                    f"{s['program']} stays open until the check passes and the proof is named.",
                    vocab.command("program_deliver", s["program"]),
                    key="program_deliver",
                    person=True,
                    action=f"Run {s['id']}'s production check",
                )
        elif s["state"] == "awaiting-proof" and not s["proof"] and s.get("owed"):
            # A DEFERRED WAIVER'S PROOF IS STILL OWED (2026-10-07): the cut, and its program, stay open
            # until it lands. The move is naming it — `slice:edit` authors the cell once the evidence
            # exists. A proof only production can take is the branch above.
            add(
                "finish",
                2,
                s["id"],
                s["name"],
                f"{_lead(rollup.waiting_on(s['id'], str(s['owed'])))}. Its waiver defers the proof rather "
                f"than excusing it, so {s['program']} stays open until the proof lands and is named here.",
                vocab.command("slice_verified_by", s["id"]),
                key="slice_verified_by",
                person=True,
                action=f"Prove {s['id']}",
            )
        elif s["state"] == "unproven" and not s["proof"] and not s["waived"]:
            add(
                "hygiene",
                3,
                s["id"],
                s["name"],
                "Every PRD is terminal and no proof is named, so this can never be proven.",
                vocab.command("slice_verified_by", s["id"]),
                key="slice_verified_by",
                action=f"Name {s['id']}'s proof",
            )
        # `unproven` ONLY, and the exclusion of `complete` is the whole design of this row.
        #
        # A bar is authored AHEAD of the work: it says what would have to be true before anybody
        # knows what got built. Asked for after the fact it is reconstructed from whatever
        # shipped, which is the one condition under which a bar is guaranteed to be worthless —
        # so a finding on every finished cut is a request for exactly the backfill this contract
        # refuses, one row at a time.
        #
        # An `unproven` cut is different because somebody already has to go there: it is
        # carrying a "no proof named" row in this same list, and whoever answers it has the
        # promise in their head at that moment. A `complete` cut has nothing else asking for
        # attention, so a bar row on it is a pure backfill request that gets ignored — and takes
        # the rows that matter with it. The coverage count in `totals` is what states that gap,
        # once, without a row per entity.
        #
        # A cut still in flight may author its bar at any point before it lands, and one whose
        # every PRD was cancelled built nothing to observe. `waived` is NOT consulted: that file
        # excuses a slice from naming a PROOF, which is a different obligation, and reading one
        # waiver as covering both would silently retire a finding nobody agreed to retire — so
        # a `waived` cut is asked for its bar exactly as an `unproven` one is, and so is an
        # `awaiting-proof` one: all three were ONE state when this row was written, and the
        # split changed which hand each needs, not whether a bar is owed.
        if s["state"] in ("unproven", "awaiting-proof") and not s["bar"]:
            add(
                "hygiene",
                3,
                s["id"],
                s["name"],
                "Every PRD is terminal and no bar was authored, so nothing ever checked that it works.",
                vocab.command("slice_bar_author", s["id"]),
                key="slice_bar_author",
                action=f"Write success criteria for {s['id']}",
            )
        if s["state"] == "flight":
            for r in s["prds"]:
                if r["fleet"]:
                    add(
                        "advance",
                        2,
                        r["n"],
                        r["title"],
                        f"Live in {s['id']} and planned. {opener} dispatches it; nothing for you to do.",
                        "",
                        fleet=True,
                        waiting=vocab.wait,
                        action=f"Build PRD {r['n']}",
                    )
                elif r["cmd"]:
                    add(
                        "planning",
                        2,
                        r["n"],
                        r["title"],
                        # ONE SENTENCE THAT SAYS WHY (ENG-10704, RV-03): the needs-you row and the page's list
                        # show a finding's first sentence, and "Live in SL-182, sitting at 'prd-drafted'." did not.
                        #
                        # AND WHICH HALF RUNS IT (ENG-10765): a stub's next step IS the fill — the same command
                        # the page's Fill box hands the fleet — so "a planning step the fleet does not run" was
                        # false exactly where the box beside it said the fleet runs it. The finding keys on the
                        # row's own shape command: when the next command IS the fleet's, the sentence says the
                        # move is the person's to start, in the words the To-do row and the box already use.
                        #
                        # EITHER HALF OF THE SHAPE PAIR (2026-11-02, #prd:0008): the shipped vocabulary names a
                        # stub's next step as the pair's TERMINAL half (`nextCommand.stub` = `prd:create`), so a
                        # match on the fleet half alone sent every stub to "a planning step the fleet does not
                        # run" beside the fill the fleet was running. Fill and create are one move, two hands.
                        #
                        # AND A DRAFTED PRD'S DESIGN IS THE FLEET'S WHILE ITS PROGRAM IS DRIVEN (0164): the
                        # service designs it on its own (`prd:blueprint`) once every PRD it depends on is
                        # planned or later. This board cannot see whether a program is driven — that is the service's
                        # state, not the corpus's — so the sentence is the one true either way.
                        (
                            f"Sitting at '{r['status']}' in {s['id']}: its next step is yours to start — hand it "
                            f"to {vocab.actor} or run it yourself in an agent session."
                            if r["cmd"] in _shape_halves(r)
                            else f"Sitting at '{r['status']}' in {s['id']}: its design waits on you — or on "
                            f"{vocab.actor}, while its program is driven."
                            if str(r["status"]) == "prd-drafted"
                            else f"Sitting at '{r['status']}' in {s['id']}: its next step is a planning step "
                            f"{vocab.actor} does not run, so it waits on you."
                        ),
                        r["cmd"],
                        person=True,
                        order=PLANNING_ORDER.get(str(r["status"]), 6),
                        action=prd_move(str(r["status"]), str(r["n"])),
                    )
        waiting_on_it = [b for b in s["blocks"] if s["id"] in sl[b]["blockedBy"] and open_slice(sl[b])]
        startable = s["state"] in ("unproven", "awaiting-proof", "waived", "abandoned")
        if s["ready"] and not decomposing and startable and waiting_on_it:
            n_blocked = len(waiting_on_it)
            waits = "s wait" if n_blocked != 1 else " waits"
            add(
                "start",
                3,
                s["id"],
                s["name"],
                f"Prerequisites are met and {n_blocked} other slice{waits} on it.",
                vocab.command("prd_create_in_slice", s["id"]),
                key="prd_create_in_slice",
                action=f"Write PRDs for {s['id']}",
            )
    return out


def groups(vocab: Vocabulary, overrides: Mapping[str, Any]) -> list[dict[str, str]]:
    """The finding groups, with the caller's own words where it supplied them."""
    out: list[dict[str, str]] = []
    for key, title, blurb in GROUPS:
        over: Mapping[str, Any] = overrides.get(key) or {}
        out.append(
            {
                "key": key,
                "title": vocab.prose(str(over.get("title", title))),
                "blurb": vocab.prose(str(over.get("blurb", blurb))),
            }
        )
    return out


# ─────────────────────────── health ───────────────────────────


def health(pg: list[dict[str, Any]], sl: dict[str, dict[str, Any]], vocab: Vocabulary) -> list[dict[str, Any]]:
    """Inconsistencies in the corpus itself, grouped by what you would DO about them.

    Every row carries its own fix. A finding with no command behind it is still shown — the
    affordance is the design, and hiding it would hide the argument for building the command.
    """
    ent = _index(pg, sl)
    items: list[dict[str, Any]] = []

    def add(cat: str, sev: int, eid: str, what: str, cmd: str) -> None:
        rk, rs, rf = ent.get(eid, (0, "", ""))
        items.append(
            {
                "cat": cat,
                "sev": sev,
                "id": eid,
                "what": what,
                "cmd": cmd,
                "built": vocab.is_built(cmd),
                "rank": rk,
                "rankSrc": rs,
                "rankFrom": rf,
            }
        )

    for p in pg:
        # Out of the plan, so out of the corpus's inconsistencies: the register's answer for a
        # withdrawn program is the decision record it cites, and nothing here is owed.
        if p.get("state") == "withdrawn":
            continue
        if not p["proof"] and not p.get("waived"):
            add("Missing proofs", 2, p["id"], f"{p['name']} — names no proof", vocab.command("program_prove", p["id"]))
        # Sev 3 rather than 2, and the gap from the row above is the whole point: a proof is a
        # completion condition and a bar is not. An entity without one still reads complete —
        # it just reads complete with nobody having said what that would look like in a running
        # system. Worth showing, never worth stopping anything.
        if p["kind"] == rollup.PROGRAM_TIER and not p["bar"]:
            add("Missing bars", 3, p["id"], f"{p['name']} — names no bar", vocab.command("program_bar_author", p["id"]))
        if p.get("closedToNewWork"):
            # FLT-1282 / FLT-1285: in a repository that plans by area an open program takes no new slice and is not
            # decomposed, so no structure finding offers to cut or decompose one.
            continue
        if not p["nsl"]:
            add("Structure", 1, p["id"], f"{p['name']} — no slices", vocab.command("program_decompose", p["id"]))
        elif p["requires"] == []:
            add(
                "Structure",
                2,
                p["id"],
                f"{p['name']} — slices cut, no decomposition roots named",
                vocab.command("program_decompose", p["id"]),
            )
        if p["nsl"] == 1:
            add(
                "Structure",
                3,
                p["id"],
                f"{p['name']} — only one slice; a program should hold at least two",
                vocab.command("slice_create", p["id"]),
            )
    for s in sl.values():
        if s["state"] == "withdrawn":
            continue
        if s["state"] == "unproven" and not s["proof"] and not s["waived"]:
            add(
                "Missing proofs",
                2,
                s["id"],
                f"{s['name']} — all PRDs terminal, no proof named",
                vocab.command("slice_verified_by", s["id"]),
            )
        # `unproven` and its two siblings only — a finished cut is deliberately NOT asked for a
        # bar it could now only reconstruct from what shipped. The argument is at the matching
        # row in `actions`.
        if s["state"] in ("unproven", "awaiting-proof", "waived") and not s["bar"]:
            add(
                "Missing bars",
                3,
                s["id"],
                f"{s['name']} — all PRDs terminal, no success criteria written",
                vocab.command("slice_bar_author", s["id"]),
            )
        if not s["dep"] and s["state"] != "complete":
            add(
                "Missing dependency edges",
                3,
                s["id"],
                f"{s['name']} — names no prerequisite, so it reads as startable",
                vocab.command("slice_depends_on", s["id"]),
            )
    return items


# ─────────────────────────── the command catalogue ───────────────────────────


def catalogue(guidance: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The caller's command catalogue: what each command is for, and how it is reached."""
    out: list[dict[str, Any]] = []
    for row in guidance.get("catalogue") or []:
        cmd, on, use = (list(row) + ["", "", ""])[:3]
        how = row[3] if len(row) > 3 else []
        out.append({"cmd": str(cmd), "on": str(on), "use": str(use), "how": [str(h) for h in how]})
    return out


def boxes(guidance: Mapping[str, Any]) -> dict[str, list[list[str]]]:
    """The per-view "what you can run here" boxes: `{view: [[command, what it does], …]}`.

    Normalised to pairs rather than passed through, for the same reason `catalogue` parses its
    rows instead of forwarding them: the renderer destructures each entry as `[cmd, use]`, so a
    three-element row silently drops its third and a one-element row prints `undefined`. Parsing
    at the boundary makes the payload's shape a property of this function rather than of
    whatever the caller happened to write — which is also what lets a consumer store it in two
    typed columns and hand back something byte-comparable.
    """
    out: dict[str, list[list[str]]] = {}
    for view, rows in (guidance.get("cmds") or {}).items():
        pairs = ((list(row) + ["", ""])[:2] for row in rows or [])
        entries = [[str(cmd), str(use)] for cmd, use in pairs]
        # A view listed with no commands is dropped rather than carried as an empty list. The
        # renderer already reads a missing view and an empty one identically (`D.cmds[view] ||
        # []`), so the two spellings render the same box and only one of them survives a round
        # trip through storage — which would otherwise make a payload and its rebuild differ
        # over a key that means nothing.
        if entries:
            out[str(view)] = entries
    return out


def commands_on_disk(root: Path, guidance: Mapping[str, Any]) -> list[str]:
    """The command names found under the catalogue's scan directory, sorted. `[]` for none.

    Split out from `crosscheck` because the SCAN and the DIFF have different lifetimes. The
    scan is a reading of one revision of one tree — a fact worth recording — while the diff is
    arithmetic over that reading and a catalogue, and can be redone at any time from the two.
    A consumer that stores the reading (`fleet-service` does, per commit) needs the first
    without the second; the standalone board needs both, and calls one through the other.

    Returns names, never paths: `<prefix><relative path, extension dropped, separators
    replaced>` is how a command is spelled everywhere a human or a dispatcher names one, and a
    path would have to be converted by whoever compared it — in a second place, differently.
    """
    scan: Mapping[str, Any] = guidance.get("catalogueScan") or {}
    if not scan.get("dir"):
        return []
    prefix, sep = str(scan.get("prefix", "")), str(scan.get("sep", ":"))
    base = repo_root(root) / str(scan["dir"])
    return sorted(
        {
            prefix + str(f.relative_to(base).with_suffix("")).replace("/", sep)
            for f in (base.rglob("*.md") if base.is_dir() else [])
        }
    )


#: What a cross-check that never ran says. Named rather than repeated, because the three
#: places that produce it — no scan configured, a consumer with nothing recorded, and the
#: renderer's own fallback — must produce the SAME shape, and `scanned: False` is the one the
#: page has honest words for: *"nothing was scanned on disk, so this is the catalogue's own
#: word."* A zeroed `scanned: True` is the same object claiming a scan found nothing, which is
#: the confidently false report this constant exists to keep unwritable by accident.
UNSCANNED: dict[str, Any] = {"scanned": False, "onDisk": 0, "undocumented": [], "proposed": []}


def crosschecked(disk: Iterable[str], rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """The diff between a command scan and a catalogue — in both directions. Pure.

    A command reachable in NONE of the ways the catalogue records is genuinely dead; one on
    disk and undocumented is a hole in the catalogue. Culling on one direction alone would
    delete an automated dispatcher's routing targets, which is why both are reported.

    Takes the scan as DATA rather than reading a tree, so a caller holding a recorded scan gets
    the same arithmetic as the caller holding a checkout — one implementation, and no second
    place for the two directions to disagree.
    """
    documented = {str(r["cmd"]) for r in rows}
    found = {str(d) for d in disk}
    return {
        "scanned": True,
        "onDisk": len(found),
        "undocumented": sorted(found - documented),
        "proposed": sorted(documented - found),
    }


def crosscheck(root: Path, guidance: Mapping[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """`crosschecked`, over a tree this process can read. The standalone board's entry point."""
    scan: Mapping[str, Any] = guidance.get("catalogueScan") or {}
    if not scan.get("dir"):
        # Nothing to compare against. Reporting an empty diff as if it were a clean one would
        # be the page asserting a cross-check it never ran.
        return dict(UNSCANNED)
    return crosschecked(commands_on_disk(root, guidance), rows)


# ─────────────────────────── the payload ───────────────────────────


def build(
    root: Path,
    *,
    config: Config | None = None,
    guidance: dict[str, Any] | None = None,
    authored: Mapping[str, int] | None = None,
    prd_summaries: Mapping[str, str] | None = None,
    intent_title: str = DEFAULT_INTENT_TITLE,
    repo: Path | None = None,
    command_bodies: bool = False,
    resolve_references: commands_mod.PathResolver | None = None,
) -> dict[str, Any]:
    """The board payload. Counts and order only — no date, no rate, no projection.

    `config` is the corpus's own description of itself — which file holds the programs, which
    the slices, which directory the PRDs are in. Omitted, the conventional names are used, and
    that is what most corpora want. It is a parameter rather than something resolved here
    because `resolve()` walks a filesystem upward from a working directory, and this function
    is also called on a tree extracted from a git commit that has no working directory at all.

    Reading these three by hardcoded name is a defect this signature exists to close: a corpus
    that calls its registers something else derived a whole, well-formed, entirely empty board,
    and every layer above reported success over it.

    `repo` is the REPOSITORY root, which is not the same thing as `root` — that one is the
    corpus directory. The command tree and the slot fills live at repo-relative paths, so a
    reader of them needs the repository, and `paths.repo_root` is the conventional answer —
    right for the usual layout and wrong for a corpus nested deeper. Passed explicitly wherever the
    caller knows, so the convention is a fallback rather than an assumption.

    `authored` is the human's program order — `{"PG-01": 1}` — and it is NOT read from the
    corpus, because it is not in the corpus any more (see `ranks`). Omitted means nobody has
    placed anything, which is the honest answer for a tree on a disk: every entity comes back
    unranked, and the page says so rather than inventing an order.

    `resolve_references` decides whether a path a command's prose cites LANDS anywhere, and it
    is a parameter for the reason `repo` is: `root` here is a tree somebody laid down, and
    whether that tree is a checkout or four directories extracted out of a commit is a fact only
    the caller knows. Omitted, the filesystem is asked — right for a checkout, and the source of
    ~100 false broken links on a served board (`commands.filesystem_resolver`).

    `prd_summaries` is `{prd number: plain words}`, stamped onto the board's PRD rows so a PRD
    page can read its own description. It is a PARAMETER because the convention that derives it —
    the authored `## In Plain Words`, or a bounded stand-in — lives in the service's projection
    (`dispatch.prdprojection.plain_words`), and `fleet-knowledge` is not allowed to reach into
    that layer. The record does not need it to be a board; a standalone page passes nothing and
    its PRD rows carry `""`, while the sync — which already holds each PRD's body for the
    tracker projection — passes what it read, so the served payload and `prd.summary` are one
    reading. Omitted, every PRD comes back with an empty summary.
    """
    cfg = config or Config()
    g: dict[str, Any] = guidance or {}
    vocab = Vocabulary.from_guidance(g)
    summaries: Mapping[str, str] = prd_summaries or {}

    # This corpus's own name: an own-qualified reference is normalised to its local id by the
    # readers, so the roll-up never sees it as another corpus's (None: read the config file).
    own = own_name(cfg)
    prd_rows = corpus.prds(root, cfg.prds_dir, own=own)
    slice_rows = corpus.slice_rows(
        root, file_name=cfg.slices_register, prefix=cfg.slice_prefix, detail_subdir=cfg.slices_detail_dir, own=own
    )
    program_rows = corpus.program_rows(
        root,
        file_name=cfg.programs_register,
        prefix=cfg.program_prefix,
        detail_subdir=cfg.programs_detail_dir,
        own=own,
    )

    # The detail files, as text, because `rollup.board` reads each entity's `## Bar` out of one
    # and does no file I/O of its own. Resolved HERE — this function already holds the corpus
    # root and the config that names both directories — so the derivation layer stays pure over
    # values and a caller holding the bodies some other way (a git tree, a database) can hand
    # them straight in. One mapping across both tiers: a program id and a slice id come from
    # different namespaces, so they cannot collide.
    details = {
        **corpus.program_bodies(root, [p["id"] for p in program_rows], cfg.programs_detail_dir),
        **corpus.slice_bodies(root, [s["id"] for s in slice_rows], cfg.slices_detail_dir),
    }

    # The two waiver baselines and the drill records, read HERE for the reason the detail files
    # are: this function holds the disk, `rollup.board` holds none, and `waived` / `withdrawn` /
    # a drill-proven `complete` are readings the roll-up has to make in the same breath as every
    # other state — a `waived` flag stamped on afterwards is how the board once drew an excused
    # cut and an unlooked-at one with the same chip.
    # Each waiver's KIND decides which of the two it lands in (2026-10-07): an excused one settles its
    # entity, a deferred one leaves the proof owed — `waiver_readings`.
    waivers, owed = waiver_readings(root, slice_rows, g)
    drills = registers.drills(root, cfg.drills_dir) if cfg.drills_dir else {}
    # AND THE DECLARED SIBLINGS' PROOFS, read HERE for the same reason: a `Verified by` cell may
    # name another corpus's PRD (`sib:0770`), and the roll-up looks an entry up verbatim. Only a
    # sibling the config declares AND that is on disk contributes, so an undeclared qualifier is
    # never quietly resolved against this corpus (BUG-2785).
    proofs = sibling_proofs(cfg, repo or repo_root(root))
    area_cuts: list[dict[str, Any]] = []
    pg = rollup.board(
        prd_rows,
        slice_rows,
        program_rows,
        details=details,
        waivers=waivers,
        drills=drills,
        summaries=summaries,
        owed=owed,
        loose=area_cuts,
        proofs=proofs,
    )
    sl = graph(pg, area_cuts)
    prd_wave = prd_waves(pg, sl, prd_rows)

    ranks(pg, sl, authored or {})
    advance(sl, vocab)
    drive(pg, vocab)
    close_programs(pg, planningmode.mode_of(cfg.planning))

    acts = actions(pg, sl, vocab)
    hl = health(pg, sl, vocab)
    cat = catalogue(g)
    # A program keeps its slices by ID: the same objects are already on the page under
    # `slices`, and serialising them twice doubles the payload for nothing.
    for p in pg:
        p["slices"] = [s["id"] for s in p["sl"]]
        del p["sl"]

    claimed = {r["n"] for s in sl.values() for r in s["prds"]}
    return {
        "programs": pg,
        "slices": sl,
        # WHERE NEW SLICES GO in this corpus (FLT-1281): `programs` unless its `.fleet/fleet.toml` says
        # `[fleet.planning] mode = "areas"`. Served so the service decides per lane from the corpus.
        "planningMode": planningmode.mode_of(cfg.planning),
        "offBoardPrds": [
            {
                "n": r["n"],
                "title": r["title"],
                "status": r["status"],
                "slice": r.get("slice") or "",
                # The chain runs through a PRD no slice claims as readily as through one it does,
                # so an unclaimed PRD carries its edges and its place in the waves too.
                "dep": [str(d) for d in r.get("dep") or []],
                "wave": prd_wave.get(str(r["n"])),
                # Its plain-words description, when the caller read one (ENG-12792) — same source
                # the slice-claimed rows take it from, so the PRD page reads it off either shape.
                "summary": summaries.get(str(r["n"]), ""),
            }
            for r in sorted(prd_rows, key=lambda r: r["n"])
            if r["n"] not in claimed
        ],
        # THE DRILL RECORDS A PROOF CAN NAME, as the page needs them: `stem -> {verdict,
        # daemonSha}`. A `drill:<stem>` entry in a proof cell is resolved by the roll-up above;
        # this is what lets a page print the verdict beside the entry rather than a bare tick,
        # and `daemonSha` names what the record proves. NOT `ran_at`: the board states no date,
        # ever — a harness's timestamp is provenance a reader finds in the record itself, and a
        # payload that carried one would be the first date on this page. Every record under the
        # directory rides, not only the cited ones: a record nothing cites is a proof somebody
        # could name, and a page that could not see it could not offer it.
        "drills": {
            stem: {"verdict": str(rec.get("verdict", "")), "daemonSha": str(rec.get("daemon_sha", ""))}
            for stem, rec in sorted(drills.items())
            if str(rec.get("type", "")) == registers.DRILL_RECORD_TYPE
        },
        # THE GLOSSARY IS THE CORPUS'S OWN, and it is carried rather than restated. Every term
        # a page names — program, slice, PRD, commitment, proof, wave — is defined once in
        # `specs/glossary.md` and read by `corpus.glossary`, which is what makes a definition
        # on a page an echo of the register instead of a second text that quietly disagrees
        # with it. `[]` when the corpus has none: a page renders that as "this corpus defines
        # no terms", never as a definition of its own.
        #
        # A LIST OF TERMS AND NOT `corpus.glossary`'S WHOLE DICT. That reader also returns the
        # entity-relationship `diagram` and the file it came from, for a page that draws them;
        # this board draws neither, and the one that did is deleted. Carrying them would put two
        # values in the payload that no page reads and that a projection would then need columns
        # for — and a stored field nothing renders is a field nothing keeps honest.
        "glossary": corpus.glossary(root, cfg.glossary).get("terms", []),
        "actions": acts,
        "groups": groups(vocab, g.get("groups") or {}),
        "health": hl,
        "baselines": baselines(root, list(g.get("baselines") or [])),
        "commands": cat,
        # THE DERIVED COMMAND TREE, beside the hand-authored `commands` catalogue above and
        # deliberately not merged into it. They answer different questions and one of them
        # drifts: `commands` is a project's own prose about what its commands are FOR, which
        # nothing can derive; this is what the tree ACTUALLY contains, which nothing should
        # hand-write. The `crosscheck.undocumented` banner exists precisely because the first
        # one goes stale, and the fix for that is not a better hand-list.
        # `{}` when the repository has no command tree — the page then renders the catalogue
        # alone, exactly as it did before this existed.
        # THE ROOT IS THE CATALOGUE'S OWN SCAN DIRECTORY, not a second setting. It already names
        # where the commands are, a consumer that stores readings already extracts it, and a
        # second key would be one more thing to configure twice and get different.
        "commandTree": commands_mod.catalogue(
            repo or repo_root(root),
            root,
            commands_dir=str(
                (g.get("catalogueScan") or {}).get("dir") or kb_slots.default_commands_dir(repo or repo_root(root))
            ),
            bodies=command_bodies,
            resolve=resolve_references,
        ),
        "howLabel": {str(k): str(v) for k, v in (g.get("howLabel") or {}).items()},
        "crosscheck": crosscheck(root, g, cat),
        "proposed": sorted(vocab.unbuilt),
        "fleet": {"wait": vocab.wait, "actor": vocab.actor, "note": vocab.note},
        "cmds": boxes(g),
        "pipe": g.get("pipe", []),
        "pipeLabel": g.get("pipeLabel", ""),
        "intentTitle": intent_title,
        "totals": {
            "programs": len(pg),
            "slices": len(sl),
            "live": sum(1 for p in prd_rows if p["status"] not in rollup.PRD_TERMINAL),
            # `open` is the denominator the dependency view needs: it drops completed slices,
            # so counting `noEdge` against every slice ever cut would print a ratio whose two
            # halves measure different sets.
            # `open` and `noEdge` count neither a waived nor a withdrawn cut: both are out of
            # the plan by a decision somebody wrote down, and an "open" figure that included
            # them would be counting the register's own answers as questions.
            "open": sum(1 for s in sl.values() if open_slice(s)),
            "noEdge": sum(1 for s in sl.values() if not s["dep"] and open_slice(s)),
            # How many of those programs and slices carry a `## Bar`. A COUNT and not a
            # finding: a bar is optional at both tiers, so the gap between this and
            # `programs + slices` is the honest way to show how much of the corpus has said
            # what it would have to be seen doing — without putting a row on every entity that
            # has not, which is the fastest way to teach a reader to skip the whole view.
            "bars": sum(1 for p in pg if p["bar"]) + sum(1 for s in sl.values() if s["bar"]),
        },
    }


def open_slice(s: Mapping[str, Any]) -> bool:
    """Whether a slice counts as OPEN — not complete, and not parked by a decision.

    One predicate for the two totals that share it, so `open` and `noEdge` cannot drift apart
    over which states a decision has taken out of the plan. Public because `fleet-service`'s
    rebuild computes the same two totals from the same rows and must call this rather than
    restate it.
    """
    return s["state"] != "complete" and s["state"] not in rollup.BOARD_PARKED_STATES


#: The JSON, escaped for inlining. `fleet_knowledge.page` owns it rather than this module, so a
#: second page cannot acquire a different idea of what a corpus is allowed to say. There was one
#: — the knowledge browser — and the shared escaper is the half of that arrangement that was
#: worth keeping; the forked renderer was not.
payload = page.payload


def render(
    root: Path,
    *,
    config: Config | None = None,
    template: Path | None = None,
    title: str = DEFAULT_TITLE,
    guidance: dict[str, Any] | None = None,
    authored: Mapping[str, int] | None = None,
    intent_title: str = DEFAULT_INTENT_TITLE,
) -> str:
    """The finished page."""
    tpl = template or default_template()
    html = tpl.read_text(encoding="utf-8")
    # A SITE AND NOT A MENTION. This template documents all five of its placeholders in its
    # opening comment, and a check that accepted that mention would pass on a replacement
    # template which names `__DATA__` in prose and has nowhere to put it.
    page.require(html, ("__DATA__", "__TITLE__", "__INTENT_TAB__"), tpl)
    # BODIES RIDE IN THE STANDALONE FILE and in no other caller. This function's whole
    # product is one self-contained page for a reader with no deployment — the command text
    # is the thing such a reader most needs and least easily gets, and a megabyte inside a
    # file already meant to be opened from a disk costs nothing anybody notices.
    data = build(
        root,
        config=config,
        guidance=guidance,
        authored=authored,
        intent_title=intent_title,
        command_bodies=True,
    )
    # `__STYLE__` and `__SCRIPT__` are NOT required. A replacement template passed with
    # `--template` may bring its own look, and demanding a placeholder it never asked for
    # would break the swap this generator advertises. The shipped template asks for both,
    # which is what makes the standalone page and the deployed app one design rather than two.
    #
    # ONE PASS, so this mapping has no order. The renderer and the stylesheet used to be
    # substituted first and then re-scanned for `__TITLE__`, which made a token inside
    # `board.js` a live placeholder and left "substitute the payload last" as a rule somebody
    # had to keep remembering. `page.fill` never scans what it substituted.
    return page.fill(
        html,
        {
            "__STYLE__": _asset(tpl, STYLE_NAME, stylesheet()),
            "__SCRIPT__": _asset(tpl, SCRIPT_NAME, script()),
            "__TITLE__": title,
            "__INTENT_TAB__": intent_title,
            "__DATA__": page.payload(data),
        },
    )


__all__ = [
    "GROUPS",
    "PROGRAM_STEPS",
    "open_slices",
    "Vocabulary",
    "actions",
    "baselines",
    "boxes",
    "build",
    "catalogue",
    "commands_on_disk",
    "crosscheck",
    "crosschecked",
    "default_template",
    "drive",
    "finished",
    "graph",
    "health",
    "load_guidance",
    "open_slice",
    "is_closed",
    "program_step",
    "with_closed",
    "with_owners",
    "script",
    "payload",
    "ranks",
    "render",
    "stylesheet",
    "waived",
    "waiver_kinds",
    "waiver_readings",
]
