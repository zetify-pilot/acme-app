"""The command tree, read: what each command is, what it needs, and what it points at.

`slots.py` answers *which questions must a repo answer*. This answers *what is in the
command tree that asks them* — one record per command, carrying enough to render a page
without opening a file, plus the outbound edges that let a reader walk from a command into
the documents it cites.

**Three readings, and they are deliberately separate:**

  * **The spine** — the fenced json block a command carries: its id, its intent, its ordered
    steps, and the slot ids it declares in `requires` / `optional`. A command without one
    contributes a record anyway, marked `has_spine: false`, because "this command declares
    nothing" is a finding a reader wants rather than an absence to hide.
  * **The prose** — the title, and every path the body points at. A command is mostly
    instructions *about* other files, so the references ARE the structure; a page that
    renders the text without them makes the reader grep.
  * **The join** — each command against a `slots.Survey`, producing the one verdict the
    whole surface exists for: can this command run in this repo, and if not, which slot is
    missing.

**Nothing here is namespace-specific.** The command namespaces are read off the directory
names under the command root, so a repo whose commands live under a different prefix is
described correctly with no configuration. The alternative — a hardcoded namespace — is the
exact shape that makes a portable reader quietly wrong in the second repository it meets.

**Bodies are not read here.** The corpus's command text runs to roughly a megabyte; a
catalogue that carried it would be seven times the size of the whole board payload it rides
in. `body()` fetches one on demand, and the caller decides whether it can afford to.

**AND A REFERENCE IS RESOLVED AGAINST WHATEVER THE CALLER SAYS EXISTS.** `PathResolver` is
that seam. The reader's default is the filesystem under `root`, which is right when somebody
is standing in a checkout — the commit gate, the standalone board — and *silently wrong* in
the deployed service, which parses a tree `git archive` laid down and therefore holds only the
few directories a sync chose to fetch. Every `scripts/*.py` a command cites then read as a
broken link: measured on the live corpus, 101 of 382 references were reported broken and 100
of them were files that exist and are tracked. A resolver the caller supplies lets the party
that HAS the commit answer the question about the commit — see `fleet_service.sync`, which
answers it from `git ls-tree` — while nothing about this reader changes for a checkout.

Stdlib only.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

from fleet_knowledge import slots as slotmod

__all__ = [
    "NEEDS",
    "NEEDS_ANSWERS",
    "NEEDS_A_DECISION",
    "NEEDS_NOTHING",
    "Command",
    "CommandReport",
    "PathResolver",
    "Reference",
    "Step",
    "body",
    "catalogue",
    "filesystem_resolver",
    "namespace_of",
    "read_commands",
    "report",
    "scopes",
]

#: Given every repo-relative path one command tree cites — deduplicated and sorted — the
#: subset a reader could actually open. **One call for the whole tree, never one per path**:
#: the candidate set is collected before anything is resolved precisely so an implementation
#: that costs a subprocess or a query pays it once, and both of the two that exist do.
#:
#: A `frozenset` back rather than a predicate because the interesting implementations are
#: batch answers — a `git ls-tree` listing, a `check-ignore` run — and a predicate would force
#: each of them to be rebuilt into one anyway, in the caller, once per reader.
PathResolver = Callable[[tuple[str, ...]], frozenset[str]]

#: WHAT A COMMAND NEEDS FROM A PERSON — the closed vocabulary of the spine's `needs` field,
#: spelled once here because three readers key on it: the authoring gate that refuses a spine
#: without one, the page that renders it, and the fleet's attendance policy that decides from it
#: whether a command may be dispatched with nobody attached.
#:
#: **The words are the model's own words, phrase and all.** `a decision` keeps its article
#: because it is read in a sentence — *this command needs a decision* — and a vocabulary that
#: reads as English in the one place it is written is a vocabulary an author spells right.
NEEDS_NOTHING: Final = "nothing"
NEEDS_ANSWERS: Final = "answers"
NEEDS_A_DECISION: Final = "a decision"
#: The closed set. Closed so a fourth word is a refusal where it is written rather than a value
#: that silently takes whichever branch an `if` happened to put last.
NEEDS: Final[frozenset[str]] = frozenset({NEEDS_NOTHING, NEEDS_ANSWERS, NEEDS_A_DECISION})

# A fenced json block, the same shape the spine validator reads.
_JSON_BLOCK = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)
# The first markdown h1 — a command's human title.
_H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)

# `python3 knowledge/scripts/foo.py` (the shipped home), `python3 scripts/foo.py`, or a bare path.
_SCRIPT = re.compile(r"(?:python3\s+|python\s+)?((?:knowledge/)?(?:scripts|bin|tools)/[A-Za-z0-9_./-]+\.(?:py|sh))")
# A repo-root markdown path in any of the corpus roots a command may cite.
_DOC = re.compile(r"((?:knowledge|docs|\.claude)/[A-Za-z0-9_./{}<>-]+\.md)")
# A template path is not a claim about a file: `<slug>`, `{type}`, `NNNN`, `SL-NNN`, a date.
_PLACEHOLDER = re.compile(r"<[^>]*>|\{[^}]*\}|NNNN|NN-[A-Za-z-]+|PG-NN|SL-NNN|YYYY-MM-DD")
# Prose punctuation clinging to a command token: `prd:create.` -> `prd:create`.
_TRAILING = re.compile(r"[^A-Za-z0-9-]+$")
# A line may opt out of reference checking for a deliberate historical mention.
SKIP_MARKER = "refs:skip"


@lru_cache(maxsize=8)
def _ignored(root: Path, paths: tuple[str, ...]) -> frozenset[str]:
    """Which of `paths` git deliberately ignores — i.e. is GENERATED, not missing.

    A doc rendered on demand and never committed (`roadmap.md`, an index built by a
    generator) is absent from a checkout by design, and reporting it as a broken link
    teaches a reader that "broken" means nothing. One batched `check-ignore` rather than one
    call per path: a command tree cites hundreds of files and a subprocess each would be the
    slowest thing on the page.

    A tree with no git — a fixture, an extracted archive — ignores nothing, which is the
    honest answer there: without a repository the question has no meaning, and guessing
    would make the same path resolve differently in two places.
    """
    if not paths:
        return frozenset()
    try:
        done = subprocess.run(  # noqa: S603 — fixed argv, paths on stdin, never interpolated
            ["git", "-C", str(root), "check-ignore", "--stdin"],
            input="\n".join(paths),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return frozenset()
    # exit 0 = some ignored, 1 = none ignored, 128 = not a repository. Only 0 has output.
    if done.returncode not in (0, 1):
        return frozenset()
    return frozenset(line.strip() for line in done.stdout.splitlines() if line.strip())


def filesystem_resolver(root: Path) -> PathResolver:
    """The default: a path resolves when it is a FILE under `root`, or when git ignores it.

    Right for a reader standing in a checkout, and that is the whole of its claim. The commit
    gate runs here, `fleet-knowledge`'s own CLI runs here, and both hold the tree the commands
    were written against — so asking the filesystem asks the only authority there is.

    **It is exactly wrong in a service, and quietly.** A deployed reader parses a tree
    `git archive` laid down, which carries the corpus directory, the command tree and the few
    slot-fill directories a registry named — and nothing else. `scripts/` and `docs/` are never
    fetched, so every command that says `python3 scripts/validate_x.py` cites a path that is not
    there, `is_file()` says False, and the page reports a broken link over a file that is
    tracked in git and one directory away. The gitignore escape hatch below fails in the same
    place and for the same reason: `check-ignore` needs a repository, an extracted tarball has
    no `.git`, and git exits 128 — so `_ignored` comes back empty and a generated file reads as
    missing rather than as generated. Both are the deployed case answering a question about a
    filesystem that was never the subject.

    That is why this is a value a caller may replace rather than the behaviour of the reader.
    """

    def resolve(paths: tuple[str, ...]) -> frozenset[str]:
        ignored = _ignored(root, paths)
        return frozenset(p for p in paths if (root / p).is_file() or p in ignored)

    return resolve


@dataclass(frozen=True)
class Step:
    """One ordered unit of a command, as its spine declares it."""

    id: str
    name: str
    kind: str
    actor: str
    gate: str = ""
    body: str = ""
    critique: str = ""  # rubric id the step grades against, when it is a gate or a loop


@dataclass(frozen=True)
class Reference:
    """One outbound edge from a command's prose, and whether it lands anywhere.

    `resolves` is what makes this renderable as a link rather than as text: a reference
    that does not resolve is a broken instruction, and a reader following it is the person
    who finds that out today.
    """

    raw: str
    kind: str  # "doc" | "script" | "command"
    target: str  # repo-relative path, or the command id for kind="command"
    resolves: bool


@dataclass(frozen=True)
class Command:
    """One command, read but not rendered."""

    id: str
    name: str  # `prd:create` — the namespaced form a person types
    path: str  # repo-relative
    title: str
    intent: str
    has_spine: bool
    #: WHAT THIS COMMAND NEEDS FROM A PERSON to complete: `nothing` | `answers` | `a decision`,
    #: and `""` for a command that declares no spine. One of the two facts that replaced
    #: `autonomous` — see `commandtree/process/spine.md`. It is read off the command's own body
    #: (does it ask? is a ruling its whole product?) and the fleet's attendance policy reads it
    #: back, so a step the fleet declines to run unattended is a STATED choice here rather than
    #: an absence from a list in the service.
    needs: str
    #: WHETHER THIS COMMAND MAY MERGE ITS OWN WORK. The other half of the old boolean, and the
    #: half that was never a property of autonomy at all: `prd:implement` runs unattended from
    #: end to end and still may not merge, because the party that wrote the code does not
    #: certify it. True for the verify gates and for the document-authoring commands whose PR
    #: carries only their own written artifact.
    may_merge: bool
    sop: str  # `none`, or the slug of the shared-tier document this command automates
    #: WHERE THIS COMMAND SITS IN THE SHIPPED SET (PRD 0746 D3): `core` for the generic work
    #: loop a customer install receives, `""` for the home-only depth commands (audit,
    #: sidekick, process improvement, ownership). Read by `commandsync`'s closure so a
    #: `set = "core"` repository receives the core commands and what they name, and nothing
    #: else. The field is empty, not `"all"`, for a command that declares none — the set's
    #: default lives in the config, and a second spelling here would be a second default.
    tier: str
    scope: str  # "portable" | "product"
    owner: str  # the one repo a product command belongs to; "" when portable
    requires: tuple[str, ...]
    optional: tuple[str, ...]
    loads: tuple[str, ...]
    steps: tuple[Step, ...]
    lines: int
    references: tuple[Reference, ...]
    #: THE MODES THIS COMMAND'S SPINE DECLARES it can run in (0680 New-4). Empty for every
    #: command that declares none, which is every command but `bug:reproduce` today. It is a
    #: machine-readable fact rather than prose because the service's unvouched gate reads it
    #: back — a lane's catalogue must list `bug-reproduce` with both `filing` and `tracker`
    #: before an approved customer report is dispatched to reproduce, and a command that only
    #: says so in its body cannot be asked.
    modes: tuple[str, ...] = ()

    @property
    def broken_references(self) -> tuple[Reference, ...]:
        return tuple(r for r in self.references if not r.resolves)

    @property
    def portable(self) -> bool:
        """A command that must reach every repo-specific answer through a slot.

        The DEFAULT, and deliberately so: a command says nothing and is held to the
        portable bar. The alternative — portability as an opt-in — makes the tree's
        least-examined commands the ones nothing checks, which is the same inversion
        `verdict` refuses for undeclared spines.
        """
        return self.scope != "product"

    def ships_to(self, repo_name: str) -> bool:
        """Whether this command belongs in `repo_name`'s materialized tree.

        A product command goes to its owner and nowhere else. Shipping one everywhere put
        an 880-line connector-SDK procedure into five repositories that cannot run a line
        of it, where an agent reading `.claude/` had no way to tell it was inapplicable.
        """
        return self.portable or self.owner == repo_name


@dataclass(frozen=True)
class CommandReport:
    """One command joined to a repo's slot survey — the verdict the page is built on."""

    command: Command
    blocked_by: tuple[str, ...]  # unfilled slot ids this command REQUIRES
    degraded: tuple[tuple[str, str], ...]  # (slot id, what it degrades to) for unfilled optionals
    unknown_slots: tuple[str, ...]  # declared ids the registry does not define

    @property
    def verdict(self) -> str:
        """`"runs"` | `"blocked"` | `"undeclared"` — and the third one is why this exists.

        A command with no spine has declared no `requires`, so nothing can block it, so
        every earlier reading called it **runnable** — a confident green earned by saying
        nothing at all. That is the exact inversion of what the surface is for: the
        commands we know least about were the ones it vouched for hardest, and the verdict
        was strongest precisely where the evidence was absent.

        It is not a cosmetic mislabel. The join is what answers *can this command run in
        THIS repo*, and a command that has not named its needs cannot be answered for in
        any repo — so the false green is not one wrong row, it is the same wrong row in
        every checkout the tree is carried into, and it gets louder as more repos are
        served rather than staying put.

        `undeclared` is therefore an ABSENCE OF EVIDENCE, reported as one. Silence is not
        a pass.
        """
        if not self.command.has_spine:
            return "undeclared"
        return "blocked" if (self.blocked_by or self.unknown_slots) else "runs"

    @property
    def runnable(self) -> bool:
        """True only for a command that DECLARED its needs and had them met.

        An unfilled optional never blocks — that is the whole meaning of optional, and a
        page that greyed a command out over one would be teaching its reader to ignore it.
        An undeclared command is not runnable either; see `verdict`.
        """
        return self.verdict == "runs"


def namespace_of(commands_dir: str) -> str:
    """How this tree's commands are addressed in prose — `<root>/<name>` yields `<name>`.

    THE ROOT'S OWN BASENAME, so a repository says what its commands are called by saying where
    they live, and nothing has to be configured twice. A constant here would be right in the
    repository it was written for and silently wrong in the next, which is the failure this
    whole package exists to avoid.
    """
    return commands_dir.rstrip("/").rsplit("/", 1)[-1]


def _command_name(path: Path, base: Path) -> str:
    """The path below the command root, as a person types it: `prd/create.md` -> `prd:create`.

    FLAT, and the root carries the namespace rather than the name. A tree may be one directory
    of files or several of nested ones, and an earlier draft stripped the first path segment as
    a namespace — which was right for a tree laid out `<root>/<ns>/<cmd>.md` and silently
    produced empty names for one laid out `<root>/<cmd>.md`. The root is configuration; where
    a namespace exists it belongs in that configuration, not in a guess about depth.
    """
    return ":".join(path.relative_to(base).with_suffix("").parts)


def _references(
    text: str, base: Path, namespace: str, resolvable: frozenset[str] = frozenset()
) -> tuple[Reference, ...]:
    """Every outbound edge in one command's prose, de-duplicated, each resolved once.

    `resolvable` is what a `PathResolver` said exists, computed once for the whole tree and
    handed down — so this function decides WHICH paths a command claims and never where they
    would be found. A **placeholder** path never even becomes a claim: `prds/NNNN-slug/prd.md`
    is a template, and flagging it would train the reader that "broken" means nothing, which
    costs more than the handful of real breaks the column exists to show.

    **A command-to-command edge is resolved HERE and not through the resolver**, deliberately.
    It is not a repo-relative path a corpus cites; it is a name inside the tree this reader is
    walking, and the tree is present by definition — whoever is reading it laid it down. Sending
    it through the resolver would make a page's internal links depend on a caller remembering to
    include the command tree in whatever it answers with, which is a way to break the one class
    of link that cannot be broken.
    """
    cmd_re = re.compile(rf"/({re.escape(namespace)}):([A-Za-z0-9_:-]+)") if namespace else None

    seen: dict[tuple[str, str], Reference] = {}

    def add(raw: str, kind: str, target: str, resolves: bool) -> None:
        seen.setdefault((kind, target), Reference(raw=raw, kind=kind, target=target, resolves=resolves))

    for line in text.splitlines():
        if SKIP_MARKER in line:
            continue
        for m in _DOC.finditer(line):
            raw = m.group(1)
            if _PLACEHOLDER.search(raw):
                continue
            add(raw, "doc", raw, raw in resolvable)
        for m in _SCRIPT.finditer(line):
            raw = m.group(1)
            if _PLACEHOLDER.search(raw):
                continue
            add(raw, "script", raw, raw in resolvable)
        if cmd_re is not None:
            for m in cmd_re.finditer(line):
                ns, token = m.group(1), _TRAILING.sub("", m.group(2))
                if not token:
                    continue
                target = (base / Path(*token.split(":"))).with_suffix(".md")
                add(f"/{ns}:{token}", "command", token, target.is_file())
    return tuple(seen.values())


def _ids(value: object) -> tuple[str, ...]:
    """A spine's id list, taken only when it IS a list of strings.

    A malformed spine contributes nothing rather than raising: this reader also runs over
    trees mid-edit, and a half-written declaration is a record with fewer fields, not a
    crash that hides the other thirty-three commands.
    """
    return tuple(str(v) for v in value) if isinstance(value, list) else ()


def _spine(text: str) -> dict[str, object] | None:
    """The command's spine block, or None when it carries no declaration."""
    for raw in (m.group(1) for m in _JSON_BLOCK.finditer(text)):
        try:
            block = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(block, dict) and "command" in block:
            return block
    return None


def read_commands(
    root: Path,
    commands_dir: str | None = None,
    *,
    resolve: PathResolver | None = None,
) -> tuple[Command, ...]:
    """Every command in the tree, sorted by name. `()` when there is no tree.

    `resolve` answers whether a cited path exists; omitted, the filesystem under `root` is
    asked (`filesystem_resolver`, which states when that is the wrong authority). A caller that
    holds the commit rather than a checkout — the service, whose tree is an extract — supplies
    one built from git, and every reference this reader reports then describes the COMMIT
    instead of describing which directories somebody happened to fetch.
    """
    commands_dir = commands_dir or slotmod.default_commands_dir(root)
    base = root / commands_dir
    if not base.is_dir():
        return ()
    namespace = namespace_of(commands_dir)

    texts = {p: p.read_text(encoding="utf-8", errors="ignore") for p in sorted(base.rglob("*.md"))}
    # ONE RESOLUTION FOR THE WHOLE TREE rather than one per command: the candidate set is
    # collected first precisely so the subprocess — or the query — runs once.
    candidates: set[str] = set()
    for t in texts.values():
        for line in t.splitlines():
            if SKIP_MARKER in line:
                continue
            for rx in (_DOC, _SCRIPT):
                for m in rx.finditer(line):
                    if not _PLACEHOLDER.search(m.group(1)):
                        candidates.add(m.group(1))
    resolver = resolve if resolve is not None else filesystem_resolver(root)
    resolvable = resolver(tuple(sorted(candidates)))

    out: list[Command] = []
    for path, text in texts.items():
        spine: dict[str, object] = _spine(text) or {}
        name = _command_name(path, base)
        h1 = _H1.search(text)
        steps: list[Step] = []
        raw_steps = spine.get("steps")
        for s in raw_steps if isinstance(raw_steps, list) else []:
            if not isinstance(s, dict):
                continue
            steps.append(
                Step(
                    id=str(s.get("id", "")),
                    name=str(s.get("name", "")),
                    kind=str(s.get("kind", "")),
                    actor=str(s.get("actor", "")),
                    gate=str(s.get("gate", "")),
                    body=str(s.get("body", "")),
                    critique=str(s.get("critique", "") or ""),
                )
            )
        out.append(
            Command(
                id=str(spine.get("command", "") or name.replace(":", "-")),
                name=name,
                path=str(path.relative_to(root)),
                title=h1.group(1).strip() if h1 else name,
                intent=str(spine.get("intent", "")),
                has_spine=bool(spine),
                # `"may merge"` with the space, which is how `spine.md` names the field and
                # therefore the only spelling an author is ever shown. The Python attribute
                # cannot carry a space; the JSON key is the contract and it is not renamed on
                # the way in, so a spine and the document that defines it read identically.
                needs=str(spine.get("needs", "") or ""),
                may_merge=bool(spine.get("may merge", False)),
                sop=str(spine.get("sop", "") or "none"),
                tier=str(spine.get("tier", "") or ""),
                scope=str(spine.get("scope", "") or "portable"),
                owner=str(spine.get("owner", "") or ""),
                requires=_ids(spine.get("requires")),
                optional=_ids(spine.get("optional")),
                loads=_ids(spine.get("loads")),
                steps=tuple(steps),
                lines=text.count("\n") + 1,
                references=_references(text, base, namespace, resolvable),
                modes=_ids(spine.get("modes")),
            )
        )
    return tuple(out)


def scopes(tree: Path) -> dict[str, tuple[str, str]]:
    """`{relative path: (scope, owner)}` for every command file under `tree`.

    The narrow read `commandsync` needs and nothing more: it is deciding which files to
    WRITE, so it has no repository to resolve references against and no survey to join to.
    Exposed here rather than re-implemented there because the spine block has exactly one
    parser in this package, and a second one that drifted would put a command in a repo the
    first one had excluded.
    """
    out: dict[str, tuple[str, str]] = {}
    if not tree.is_dir():
        return out
    for path in sorted(tree.rglob("*.md")):
        spine = _spine(path.read_text(encoding="utf-8", errors="ignore")) or {}
        out[str(path.relative_to(tree))] = (
            str(spine.get("scope", "") or "portable"),
            str(spine.get("owner", "") or ""),
        )
    return out


def tiers(tree: Path) -> dict[str, str]:
    """`{relative path: tier}` for every command file under `tree`.

    The membership read the `set = "core"` closure needs, kept beside `scopes` so the spine
    block still has exactly one parser: this is a second VIEW of one parse, not a second parse.
    A file that declares no tier maps to `""`.
    """
    out: dict[str, str] = {}
    if not tree.is_dir():
        return out
    for path in sorted(tree.rglob("*.md")):
        spine = _spine(path.read_text(encoding="utf-8", errors="ignore")) or {}
        out[str(path.relative_to(tree))] = str(spine.get("tier", "") or "")
    return out


def report(commands: Iterable[Command], survey: slotmod.Survey) -> tuple[CommandReport, ...]:
    """Join each command to the slot survey: runnable here, or blocked by what."""
    fills = survey.fill_of()
    # THE VOCABULARY IS THE QUESTIONNAIRE, NOT THIS REPO'S ANSWERS (ENG-17852) — `slots.survey`'s
    # rule, applied to the verdict too. `_merge` leaves an optional question the repo declined out
    # of `fills`, so measuring "unknown" against `fills` called every declined `decisions` /
    # `docs` "undefined" and blocked all 23 spined commands on an install that runs them daily.
    # A declined id is unfilled: it blocks when required and degrades when optional.
    known = survey.vocabulary()

    def unfilled(s: str) -> bool:
        return s in known and not (s in fills and fills[s].filled)

    out: list[CommandReport] = []
    for c in commands:
        blocked = tuple(sorted(s for s in c.requires if unfilled(s)))
        unknown = tuple(sorted({s for s in (*c.requires, *c.optional) if s not in known}))
        degraded = tuple((s, known[s].degrade or "unspecified") for s in c.optional if unfilled(s))
        out.append(CommandReport(command=c, blocked_by=blocked, degraded=degraded, unknown_slots=unknown))
    return tuple(out)


def body(root: Path, rel: str, commands_dir: str | None = None) -> str:
    """One command's raw markdown, by its repo-relative path.

    Refuses to read outside the command tree: the path arrives from a URL in the deployed
    case, and a reader that resolved `../../etc/passwd` would be a file-disclosure bug in a
    page whose whole job is to render files.
    """
    base = (root / (commands_dir or slotmod.default_commands_dir(root))).resolve()
    target = (root / rel).resolve()
    if not target.is_file() or base not in target.parents:
        return ""
    return target.read_text(encoding="utf-8", errors="ignore")


def catalogue(
    root: Path,
    knowledge: Path,
    *,
    registry_rel: str = slotmod.DEFAULT_REGISTRY,
    commands_dir: str | None = None,
    bodies: bool = False,
    resolve: PathResolver | None = None,
) -> dict[str, object]:
    """The payload block a page renders: commands, slots, and the join between them.

    Metadata only by default. `bodies=True` adds every command's raw markdown, which is
    roughly a megabyte — affordable for a SELF-CONTAINED FILE generated against a checkout,
    and not for a payload stored once per generation in a database that does not prune. That
    asymmetry is the whole reason this is a parameter rather than a decision made here: the
    standalone board can carry the text and the served one cannot, and each should say so
    rather than both settling for the smaller answer.

    `resolve` is passed straight through to `read_commands` — see there, and see
    `filesystem_resolver` for why the default is right in a checkout and wrong in a service.
    """
    # NO TREE MEANS NOTHING TO SAY, and `{}` says it. A shape full of zeroes would report a
    # repository that has no command tree as one whose commands all fail to run — "0 of 0
    # runnable" reads as a finding rather than as an absence. It is also what makes this
    # function and the service's rebuild agree by construction rather than by coincidence:
    # the marker row whose presence the rebuild keys off is exactly this condition.
    commands_dir = commands_dir or slotmod.default_commands_dir(root)
    if not (root / commands_dir).is_dir():
        return {}

    survey = slotmod.survey(root, knowledge, registry_rel=registry_rel, commands_dir=commands_dir)
    reports = report(read_commands(root, commands_dir, resolve=resolve), survey)
    fills = survey.fill_of()

    return {
        # THAT THE TREE WAS WALKED, kept apart from what the walk found. The whole block is
        # absent when there is no tree (above), so this key's presence inside one is what a
        # consumer turns into the marker row separating "walked, found nothing" from "never
        # walked" — two statements a count cannot tell apart.
        "scan": {"directory": commands_dir},
        "commands": [
            {
                "id": r.command.id,
                "name": r.command.name,
                "path": r.command.path,
                "title": r.command.title,
                "intent": r.command.intent,
                "hasSpine": r.command.has_spine,
                "needs": r.command.needs,
                "mayMerge": r.command.may_merge,
                "scope": r.command.scope,
                "owner": r.command.owner,
                "lines": r.command.lines,
                "requires": list(r.command.requires),
                "optional": list(r.command.optional),
                "loads": list(r.command.loads),
                "modes": list(r.command.modes),
                "steps": [
                    {"id": s.id, "name": s.name, "kind": s.kind, "actor": s.actor, "gate": s.gate}
                    for s in r.command.steps
                ],
                "references": [
                    {"kind": x.kind, "target": x.target, "resolves": x.resolves} for x in r.command.references
                ],
                "runnable": r.runnable,
                "verdict": r.verdict,
                "blockedBy": list(r.blocked_by),
                "degraded": [{"slot": s, "to": t} for s, t in r.degraded],
                "unknownSlots": list(r.unknown_slots),
            }
            for r in reports
        ],
        "slots": [
            {
                "id": f.slot.id,
                "tier": f.slot.tier,
                "requirement": f.slot.requirement,
                "answers": f.slot.answers,
                "degrade": f.slot.degrade,
                "fill": list(f.slot.fill),
                "matched": [str(p.relative_to(root)) for p in f.matched],
                "missing": list(f.missing),
                "filled": f.filled,
                # A placeholder answers nothing (`slots.STUB_MARKER`): `filled` is false, `matched`
                # still names the file, and this says why the two disagree.
                "stub": f.stub,
                "consumedBy": list(f.slot.consumed_by),
            }
            for f in survey.fills
        ],
        "registry": (
            str(survey.registry.path.relative_to(root))
            if survey.registry.present and survey.registry.path is not None
            else None
        ),
        # ERRORS ABOUT A REGISTRY THAT EXISTS, and only those. "there is no registry" is already
        # said by `registry: null`, and carrying it here as well would be one absence stated
        # twice — in two fields that a consumer storing the first has no way to keep agreeing
        # with the second.
        "registryErrors": list(survey.registry.errors) if survey.registry.present else [],
        "readiness": {
            "shared": [
                sum(1 for f in survey.fills if f.slot.shared and f.filled),
                sum(1 for f in survey.fills if f.slot.shared),
            ],
            "required": [
                sum(1 for f in survey.fills if not f.slot.shared and f.slot.mandatory and f.filled),
                sum(1 for f in survey.fills if not f.slot.shared and f.slot.mandatory),
            ],
            "optional": [
                sum(1 for f in survey.fills if not f.slot.shared and not f.slot.mandatory and f.filled),
                sum(1 for f in survey.fills if not f.slot.shared and not f.slot.mandatory),
            ],
            "runnable": [sum(1 for r in reports if r.runnable), len(reports)],
            # SEPARATE FROM THE PAIR ABOVE, and deliberately not folded into it. "16/34
            # runnable" says how many are vouched for; it does not say whether the other 18
            # are blocked (a repo problem, fix the slot) or undeclared (a command problem,
            # write the spine). Two different people fix those, so the strip says which.
            "undeclared": sum(1 for r in reports if r.verdict == "undeclared"),
        },
        "unfilled": sorted(sid for sid, f in fills.items() if not f.filled),
        # Keyed by the same repo-relative path the command records carry, so a page joins the
        # two with no second identifier to keep in step. Absent — not empty — when bodies were
        # not asked for, which is what lets a page tell "no text here" from "no text at all".
        **({"bodies": {r.command.path: body(root, r.command.path, commands_dir) for r in reports}} if bodies else {}),
    }
