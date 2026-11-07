"""Is each command in this tree actually portable, or is it one repository's shell history?

`_slots.py` asks *does this repo answer what the commands need*. This asks the mirror
question, and the one nothing was asking: **do the commands only ask for things a repo can
answer?** A command tree ships into every repository the fleet dispatches into. A procedure
that names `scripts/component_of.py`, `make test-go` or `knowledge/prds/NNNN-slug/prd.md`
does not become portable by being copied — it becomes an instruction that silently does
nothing in five repositories out of six.

Measured on the tree that motivated this check: **48 distinct `scripts/*` entrypoints across
190 call sites, 63 make targets and 81 literal corpus paths**, in 34 commands of which
**11 declared no repo-tier slot at all**. Every one of those was invisible to every existing
gate, because the only thing being validated was whether the *repo* had answered — never
whether the *command* had asked in a portable way.

THE LAYOUT IS FIXED, and that is what makes a path portable or not. The tier ships its own
tooling into every repository at `knowledge/scripts/` (`commandsync.SCRIPTS_DEST`), and a
gate or lifecycle action is a conventional TARGET from one closed list (`targets.TARGETS`),
written as a token — `{{target:test-unit}}` — that `fleet commands sync` replaces with the
receiving repository's own command from its `[fleet.targets]` table. A command that names
either is naming something every receiving repository has, or can be held to having. A command
that names anything else is naming one repository's shell history.

WHAT IT GATES, and at which severity:

  * A **script path the layout does not provide** is an **error**: a repository's own
    `scripts/x.py`, a bare script basename, or a `knowledge/scripts/x.py` the package does
    not ship. The fix is to ship it — in `commandtree/scripts/` — or to name the shipped
    script that does the job.
  * A **literal `make` target** is an **error**, convention or not. `make test-go` is one
    repository's Makefile, and so is `make test-unit`: a repository with no Makefile — the
    layout Fleet writes — cannot run it. The portable spelling is the token
    `{{target:test-unit}}`, and a token that names no conventional target, or carries the wrong
    arguments, is an error too (`target-token`). In a RENDERED tier the tokens are the
    repository's own commands, which the scan blanks before it looks (`targets.expansion_patterns`)
    — so a repository whose table says `lint = "make lint"` is not told off for its own Makefile.
  * A **`scope: product` command with no `owner`** is an **error**. The exemption is earned
    by naming the one repository the procedure belongs to; a bare `product` is a wildcard.
  * A **spine list defect** — an id no questionnaire asks, a slot in both `requires` and
    `optional`, a `loads` entry outside them — is an **error**. Each one gates nothing while
    looking like a gate, which is the specific failure `_slots.py` already refuses for
    unknown ids.
  * A **`consumed_by` that disagrees with the spines** is an **error** on the questionnaire.
    It is derivable, so a hand-maintained copy is a second source of truth that drifts the
    moment a spine moves — and it moved on 31 of 43 rows the first time anyone checked.
  * A **literal corpus path** is an **advisory**, and so is a **history citation** (an issue
    key, a dated incident, a measured count from one repo). Both are real portability
    defects and both are large enough that failing on them on day one would get the check
    switched off rather than the tree fixed. They are BASELINED instead: the accepted set is
    recorded, the count can only go down, and a baselined finding that stops firing is
    itself reported so the file cannot rot upward.

The first version of this layer named tools by id and resolved them through a register, a
per-repository binding and a dispatcher. It checked the shape of every hop and saw none of
the five bindings that were wrong, because a binding is a fact about a repository and the
check only ever read the tree. A fixed path has no binding: what the command names is what
runs, and this check can read it.

`scope: product` exempts a command from the prose rules and from nothing else. Its spine is
still validated, because "this procedure is not portable" is a statement about where it runs,
not a licence to declare its needs incorrectly.

Stdlib only.
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from pathlib import Path

from fleet_knowledge import commands as commandmod
from fleet_knowledge import commandsync
from fleet_knowledge import slots as slotmod
from fleet_knowledge import targets as targetsmod
from fleet_knowledge.checks.slots._slots import option
from fleet_knowledge.config import KnowledgeBase
from fleet_knowledge.runner import Finding

#: Accepted findings, one `path::rule::token` per line, the path TIER-RELATIVE. Lives beside the package rather than
#: inside `commandtree/` on purpose: it describes the tree's CURRENT DEBT, which is the
#: authors' business, and shipping it into every repository would hand each of them a list of
#: someone else's unfinished work.
BASELINE = Path(__file__).resolve().parents[2] / "portability.baseline"

#: `python3 scripts/foo.py`, `bin/x.sh` — one repository's executable surface.
_SCRIPT = re.compile(
    r"(?:python3?\s+|uv\s+run\s+|node\s+|go\s+run\s+)?\b((?:knowledge/)?(?:scripts|bin|tools)/[A-Za-z0-9_./-]+)"
)
#: The one script home the layout provides. A `knowledge/scripts/<name>` is portable exactly
#: when `<name>` is a file the package ships there; `shipped_scripts()` is the set.
_SHIPPED_PREFIX = f"{commandsync.SCRIPTS_DEST}/"
#: The corpus paths the fixed layout provides in every repository — the shipped scripts and
#: the slot registry — so naming one is naming the layout, not one repository's corpus.
LAYOUT_PATHS: tuple[str, ...] = (_SHIPPED_PREFIX, "knowledge/slots/")
_SCRIPT_BARE = re.compile(r"`([a-z][a-z0-9_-]*\.(?:py|sh|mjs|js|ya?ml))`")
#: `sys.path.insert(0,'scripts')` — the directory as a STRING LITERAL inside an inline
#: program. Three heredocs reached one repository's shim this way; a path rule that wants
#: a slash after the word never sees a quoted word.
_SCRIPT_LITERAL = re.compile(r"""['"](scripts|bin|tools)['"]""")
_SCRIPT_BARE_IGNORE = frozenset({"__init__.py", "conftest.py", "setup.py", "pyproject.toml", "package.json"})
#: `mcp__claude_ai_Linear__save_issue` — a named MCP client tool. Not a path, not a target,
#: not a tool id: invisible to every earlier rule, and six of them sat in the shared tier
#: instructing a mechanism the receiving repository's own always-on rules forbid (an
#: interactive OAuth flow no headless session can complete). The portable spelling is the
#: shipped tracker script, which reads its credential from the environment.
_MCP = re.compile(r"\bmcp__[a-z0-9_]+__[a-z0-9_]+\b")
#: `make lint-ci`, `` `make dev` ``. In PROSE this requires a hyphenated target OR a code
#: span, because "make it", "make sure" and "make the call" are English and matched 60 of
#: the first 146 hits — a detector with a 40% false-positive rate is one people learn to
#: scroll past. Inside a FENCE there is no English, so a bare `make generate` counts: the
#: hyphen rule let `make generate`, `make build` and `make lint` — the three commonest
#: targets in the estate — sit in the shared tier's gate fence while the check reported zero.
_MAKE = re.compile(r"`make ([a-z][a-z0-9-]*)`|\bmake ([a-z]+(?:-[a-z0-9]+)+)\b")
_MAKE_FENCED = re.compile(r"(?:^|[;&|(\s])make\s+([a-z][a-z0-9-]*)\b")
#: The conventional targets a portable command may name, as `{{target:<name>}}` — the closed
#: vocabulary of `[fleet.targets]` (`targets.TARGETS`, which says what each means and which take
#: an argument). Every repository the tier ships into names its command for each, or honestly
#: lacks it: an unconfigured target renders as a refusal, which is loud, not silent.
MAKE_TARGETS: frozenset[str] = frozenset(targetsmod.TARGETS)


def shipped_scripts() -> frozenset[str]:
    """The repo-relative paths of every script the package ships — the portable set."""
    src = commandsync.source_root() / commandsync.SCRIPTS_SUBDIR
    return frozenset(f"{_SHIPPED_PREFIX}{p.name}" for p in src.glob("*.py")) if src.is_dir() else frozenset()


_PATH = re.compile(
    r"\b((?:[a-z0-9_.-]+/)+[A-Za-z0-9_.*<>{}-]+\.(?:md|py|ya?ml|sql|go|tsx?|jsonl?|css|sh|mjs|proto|txt|baseline))"
)
#: An issue key (`ENG-1234`), a bare date, or a measured claim about one repo's corpus.
_HISTORY = re.compile(r"\b[A-Z]{2,5}-\d{2,6}\b|\b20\d\d-\d\d-\d\d\b")
#: A markdown link at another `.md`.
_LINK = re.compile(r"\[[^\]]*\]\(([^)#]+\.md)\)")
#: A template is not a claim about a file.
_PLACEHOLDER = re.compile(r"<[^>]*>|\{[^}]*\}|NNNN|PG-NN|SL-NNN|YYYY-MM-DD|\bNN\b")
#: The tier's own files, which every repository receiving the tier has by construction. Both
#: spellings: `.claude/process/x.md` as a repo path, and the `../../../process/x.md` a command
#: uses to reach a sibling document — the second is the common form and reading it as one
#: repository's corpus path put 58 self-references into the first baseline.
_OWN = (".claude/", "claude/", "process/", "registers/", "rubrics/", "commands/")
#: `claude/…` as well as `.claude/…`: the bare form below strips leading dots and slashes, so
#: the tier's own materialized path arrives without its dot — and 27 self-references sat in
#: the first baseline as "corpus paths" because of it.

SKIP = commandmod.SKIP_MARKER

_MAKE_HINT = (
    "Name the target as a token, `{{target:<name>}}` (the list is `targets.TARGETS`); the sync writes the "
    "repository's own command there. A literal `make` runs one repository's Makefile."
)
#: The transition window (one release): a conventional `make <target>` in a tier `fleet commands sync`
#: RENDERED is a tier synced before `[fleet.targets]`, not something a command's author wrote. On the
#: day an install upgrades, every repository that has not yet merged its Apply Fleet pull request still
#: carries one, and an error there would turn every agent's pre-push `validate-knowledge` red over
#: work it did not touch. So it is a WARNING for now and becomes `make-target`'s error in the release
#: that stops reading a root `fleet.toml` (`config.LEGACY_CONFIG_REL`). The shipped SOURCE has no such
#: window: there a literal `make` is always an error.
LEGACY_MAKE_LEVEL = "warning"
_LEGACY_MAKE_HINT = (
    'This tier was synced before `[fleet.targets]`. Merge the open "Apply Fleet" pull request for this '
    "repository, or run `fleet commands sync` as a change of its own — never inside an unrelated pull "
    "request. This becomes an error in the release that stops reading a root fleet.toml."
)
_TOKEN_HINT = (
    "A token names one of `targets.TARGETS` and carries exactly its arguments: `{{target:test-one T=<TestName>}}`."
)


def _key(tier: Path | None, doc: Path, rule: str, token: str) -> str:
    """A baseline key that means the same thing in the source tree and in a synced repo.

    TIER-RELATIVE, and that is the whole point. One command sits at `commandtree/commands/
    <ns>/check.md` where the tier is authored and at `.claude/commands/<ns>/check.md`
    everywhere it is materialized — so a key built from the repo-relative path matches in one
    of those and silently matches nothing in the other, which turns a 633-line ratchet into
    633 unbaselined advisories the moment the tree is synced.
    """
    rel = doc.resolve()
    if tier is not None:
        with contextlib.suppress(ValueError):
            rel = rel.relative_to(tier.resolve())
    return f"{rel}::{rule}::{token}"


def _read_baseline() -> set[str]:
    if not BASELINE.is_file():
        return set()
    out = set()
    for line in BASELINE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return out


#: The shared tier's directories, beside `commands/`. Identical in every repository that
#: receives the tree, which is exactly why they are held to the portable bar with no
#: `scope: product` escape: there is no one repository for a shared document to belong to.
SHARED_DIRS = ("process", "registers", "rubrics")


def _tier_root(commands_dir: Path, root: Path) -> Path | None:
    """The directory holding `commands/` and the shared tier, found by walking UP.

    Never a fixed `commands_dir.parent`. A repo addresses its commands at whatever nesting
    its namespace needs — `.claude/commands` in one, `.claude/commands/<namespace>` in the
    repository that wrote this package — so a fixed depth finds the tier in one of them and
    silently finds nothing in the other, which disables these checks exactly where the tree
    is real. The marker is `process/spine.md` — the one document every tier carries.
    """
    here, stop = commands_dir.resolve(), root.resolve()
    while True:
        if (here / "process" / "spine.md").is_file():
            return here
        if here == stop or here.parent == here:
            return None
        here = here.parent


def _shared_docs(tier: Path | None) -> list[tuple[str, Path]]:
    """`(tier directory, document)` for every shared-tier file, or nothing without a tier."""
    if tier is None:
        return []
    return [(d, doc) for d in SHARED_DIRS if (tier / d).is_dir() for doc in sorted((tier / d).rglob("*.md"))]


def _logical_lines(text: str) -> list[tuple[str, bool, bool]]:
    """`(line, in_fence, executable)` with prose paragraphs re-flowed onto one line.

    A token wrapped across a line break — `` `make ``⏎`` test-go-db` `` — escaped a
    line-oriented scan entirely. Prose is joined per paragraph so a wrapped code span is one
    string again; fenced blocks are kept line-for-line because a fence is already shell,
    and a shell line is the unit its author meant. A `refs:skip` line is dropped BEFORE
    joining, so the opt-out stays one line wide.
    """
    out: list[tuple[str, bool, bool]] = []
    in_fence = False
    lang = ""
    para: list[str] = []

    def flush() -> None:
        if para:
            out.append((" ".join(s.strip() for s in para), False, False))
            para.clear()

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            flush()
            in_fence = not in_fence
            lang = line.strip()[3:].strip().lower() if in_fence else ""
            continue
        if SKIP in line:
            continue
        if in_fence:
            # A data fence (json, yaml, a markdown template) is not shell: `"tools"` in the
            # register's own schema is a key, not a directory.
            out.append((line, True, lang not in ("json", "yaml", "yml", "markdown", "md", "toml", "text", "")))
        elif line.strip():
            para.append(line)
        else:
            flush()
    flush()
    return out


def _tokens(line: str, found: dict[str, set[str]]) -> str:
    """`line` with every target token checked (`target-token`) and blanked, so no later rule reads it."""

    def one(m: re.Match[str]) -> str:
        args = dict(re.findall(r"([A-Z][A-Z0-9_]*)=([^\s{}]+)", m.group(2)))
        try:
            targetsmod.command(m.group(1), {}, args)
        except targetsmod.TargetError as exc:
            found["target-token"].add(str(exc))
        return " "

    line = targetsmod.TOKEN_RE.sub(one, line)
    for m in re.finditer(r"\{\{target:[a-z][^\n]{0,40}", line):
        found["target-token"].add(f"{m.group(0)} (does not parse)")
    return line


def _scan(text: str, rendered: re.Pattern[str] | None = None, *, synced: bool = False) -> dict[str, set[str]]:
    """Every portability token in one command's prose, by rule.

    `rendered` matches what this repository's tokens rendered to (`targets.expansion_patterns`);
    it is blanked before any rule runs, because in a synced tier that text IS the repository's own
    command and not something the source wrote. `synced` says the tier is one `fleet commands sync`
    wrote (it carries the sync manifest): there a CONVENTIONAL literal `make` is a tier rendered
    before `[fleet.targets]` and goes to `legacy-make`, a warning for one release (`LEGACY_MAKE_LEVEL`).
    """
    found: dict[str, set[str]] = {
        k: set()
        for k in (
            "literal-script",
            "make-target",
            "legacy-make",
            "target-token",
            "mcp-tool",
            "corpus-path",
            "history",
        )
    }
    shipped = shipped_scripts()
    shipped_names = {s.rsplit("/", 1)[-1] for s in shipped}

    def script(token: str) -> None:
        # A shipped script cited at its shipped path is the layout, not a repo's history. Cited
        # at the OLD home (`scripts/x.py`) it is still an error: that path exists in one repo.
        if token.startswith(_SHIPPED_PREFIX) and token in shipped:
            return
        if token.startswith(_SHIPPED_PREFIX):
            found["literal-script"].add(f"{token} (the package does not ship it)")
            return
        found["literal-script"].add(token)

    for line, in_fence, executable in _logical_lines(text):
        if rendered is not None:
            line = rendered.sub(" ", line)
        line = _tokens(line, found)
        for m in _MCP.finditer(line):
            found["mcp-tool"].add(m.group(0))
        for m in _SCRIPT.finditer(line):
            script(m.group(1))
        for m in _SCRIPT_BARE.finditer(line):
            if m.group(1) not in _SCRIPT_BARE_IGNORE and m.group(1) not in shipped_names:
                found["literal-script"].add(m.group(1))
        if executable:
            for m in _SCRIPT_LITERAL.finditer(line):
                found["literal-script"].add(f"'{m.group(1)}' (as a string literal)")
        targets = {m.group(1) or m.group(2) for m in _MAKE.finditer(line)}
        if executable:
            targets |= {m.group(1) for m in _MAKE_FENCED.finditer(line)}
        for target in targets:
            # A literal `make <target>` — conventional or not — runs one repository's Makefile.
            legacy = synced and target in targetsmod.TARGETS
            found["legacy-make" if legacy else "make-target"].add(f"make {target}")
        for m in _PATH.finditer(line):
            raw = m.group(1)
            bare = raw.lstrip("./")
            while bare.startswith("../"):
                bare = bare[3:]
            # `_PATH` opens on `\b`, which falls AFTER a leading dot, so `.fleet/x.md` arrives as
            # `fleet/x.md`. The dot is read off the line instead: dotted, it is the plugin
            # layout's home; bare, `fleet/` is a real path in a repository carrying the fleet as
            # a submodule, and stays a corpus path.
            dotted = m.start(1) > 0 and line[m.start(1) - 1] == "."
            if (
                bare.startswith(_OWN)
                or raw.startswith((".fleet/", "./.fleet/"))
                or (dotted and raw.startswith("fleet/"))
                or bare.startswith(("scripts/", "bin/", "tools/", *LAYOUT_PATHS))
                or _PLACEHOLDER.search(raw)
            ):
                continue
            found["corpus-path"].add(raw)
        # A spine block is machine-readable metadata; an id in it is not prose colour.
        if not in_fence:
            for m in _HISTORY.finditer(line):
                found["history"].add(m.group(0))
    return found


@dataclass
class CommandPortability:
    """Every command in this tree, held to the bar its own spine claims."""

    name: str = "command-portability"
    title: str = "commands ask only for what a repo can answer"
    description: str = (
        "A command is a portable procedure. This check reads every command in the tree and "
        "fails the ones that name what the fixed layout does not provide: a script outside "
        "the shipped `knowledge/scripts/`, a literal `make` target where a `{{target:<name>}}` "
        "token belongs, a token naming no conventional target, a "
        "`scope: product` command that names no owner, or a spine whose declared slot ids "
        "are unknown, contradictory, or disagree with the questionnaire's `consumed_by`. "
        "Literal corpus paths and one-repo history citations are baselined advisories, so "
        "the debt ratchets down and cannot ratchet up."
    )

    def _commands_rel(self, kb: KnowledgeBase) -> str:
        return str(option(kb, "commands_dir", slotmod.default_commands_dir(kb.root)))

    def applies(self, kb: KnowledgeBase) -> bool:
        return (kb.root / self._commands_rel(kb)).is_dir()

    def run(self, kb: KnowledgeBase) -> list[Finding]:  # noqa: C901 — one rule per branch, flat by design
        commands_rel = self._commands_rel(kb)
        base = kb.root / commands_rel
        cmds = commandmod.read_commands(kb.root, commands_rel)
        tier = _tier_root(base, kb.root)
        table = kb.config.section("targets") if hasattr(kb.config, "section") else {}
        rendered = targetsmod.expansion_patterns({str(k): str(v) for k, v in table.items()})
        # A tier the sync wrote, as opposed to the shipped source (`_scan`'s `synced`).
        synced = (tier is not None and (tier / commandsync.MANIFEST_NAME).is_file()) or (
            kb.root / commandsync.MANIFEST_REL
        ).is_file()
        baseline = _read_baseline()
        fired: set[str] = set()
        out: list[Finding] = []

        questions = slotmod.read_questions()
        known_slots = {s.id for s in questions.slots}

        for c in cmds:
            path = kb.root / c.path
            declared = set(c.requires) | set(c.optional)

            # --- the spine, checked for every command, product or not ----------------
            if c.scope not in ("portable", "product"):
                out.append(
                    Finding(
                        level="error",
                        message=f"`{c.name}`: scope `{c.scope}` is not one of portable, product",
                        path=path,
                        hint="Omit `scope` for a portable command; `product` needs an `owner`.",
                    )
                )
            if c.scope == "product" and not c.owner:
                out.append(
                    Finding(
                        level="error",
                        message=f"`{c.name}` declares `scope: product` but names no `owner`",
                        path=path,
                        hint="A command claiming to belong to one repository has to say which; add `owner`.",
                    )
                )
            if c.owner and c.scope != "product":
                out.append(
                    Finding(
                        level="error",
                        message=f"`{c.name}` names an `owner` but is not `scope: product`, so the owner binds nothing",
                        path=path,
                        hint="Either declare `scope: product`, or drop the `owner`.",
                    )
                )
            if known_slots:
                for sid in sorted(s for s in declared if s not in known_slots):
                    out.append(
                        Finding(
                            level="error",
                            message=f"`{c.name}` declares slot `{sid}`, which the shipped questionnaire does not ask",
                            path=path,
                            hint="A typo in a slot id gates nothing while looking exactly like a gate.",
                        )
                    )
            for sid in sorted(set(c.requires) & set(c.optional)):
                out.append(
                    Finding(
                        level="error",
                        message=f"`{c.name}` declares slot `{sid}` in both `requires` and `optional`",
                        path=path,
                        hint="One or the other: a slot cannot both block the run and degrade it.",
                    )
                )
            for sid in sorted(s for s in c.loads if s not in declared):
                out.append(
                    Finding(
                        level="error",
                        message=(
                            f"`{c.name}` force-loads `{sid}`, which it declares in neither `requires` nor `optional`"
                        ),
                        path=path,
                        hint="`loads` names a subset of the declared slots — see spine.md -> Command.",
                    )
                )

            # --- the prose rules, portable commands only ----------------------------
            if not c.portable:
                continue
            hits = _scan(commandmod.body(kb.root, c.path, commands_rel), rendered, synced=synced)
            for rule, level, hint in (
                ("literal-script", "error", "Name a script the tier ships, at `knowledge/scripts/<name>.py`."),
                ("make-target", "error", _MAKE_HINT),
                ("legacy-make", LEGACY_MAKE_LEVEL, _LEGACY_MAKE_HINT),
                ("target-token", "error", _TOKEN_HINT),
                ("mcp-tool", "error", "Use the Fleet tools (`get_issue`); no MCP tracker client."),
                ("corpus-path", "advisory", "Reach it through the slot that owns it, and name that slot."),
                ("history", "advisory", "One repo's incident record; state the rule, not the ticket."),
            ):
                for token in sorted(hits[rule]):
                    key = _key(tier, path, rule, token)
                    if key in baseline:
                        fired.add(key)
                        continue
                    out.append(
                        Finding(
                            level=level,
                            message=f"`{c.name}` names `{token}` — {rule.replace('-', ' ')} in a portable command",
                            path=path,
                            hint=hint,
                        )
                    )

        # --- the shared tier, held to the same bar with no product escape ---------
        tier_root = tier.resolve() if tier is not None else None
        for d, doc in _shared_docs(tier):
            body = doc.read_text(encoding="utf-8", errors="ignore")
            # A link that stays INSIDE the tier must resolve inside it, because the tier
            # travels as one unit: if it is broken here it is broken in every repository
            # that receives it. A link that escapes the tier is a repo path and is judged
            # as one below, not as a broken link — `.claude/process/x.md` legitimately
            # points at `../../.claude/commands/…`, which only exists once materialized.
            for m in _LINK.finditer(body):
                target = (doc.parent / m.group(1)).resolve()
                if tier_root is None or not target.is_relative_to(tier_root) or target.is_file():
                    continue
                out.append(
                    Finding(
                        level="error",
                        message=(
                            f"shared tier `{d}/{doc.name}` links `{m.group(1)}`, which resolves "
                            "nowhere inside the tier — so it is broken in every repo that receives it"
                        ),
                        path=doc,
                        hint="Point at the slot that owns the answer, or at a file the tier actually carries.",
                    )
                )
            hits = _scan(body, rendered, synced=synced)
            for rule, level, hint in (
                ("literal-script", "error", "Name a script the tier ships, at `knowledge/scripts/<name>.py`."),
                ("make-target", "error", _MAKE_HINT),
                ("legacy-make", LEGACY_MAKE_LEVEL, _LEGACY_MAKE_HINT),
                ("target-token", "error", _TOKEN_HINT),
                ("mcp-tool", "error", "Use the Fleet tools (`get_issue`); no MCP tracker client."),
                ("corpus-path", "advisory", "Reach it through the slot that owns it, and name that slot."),
                ("history", "advisory", "One repo's incident record; state the rule, not the ticket."),
            ):
                for token in sorted(hits[rule]):
                    key = _key(tier, doc, rule, token)
                    if key in baseline:
                        fired.add(key)
                        continue
                    out.append(
                        Finding(
                            level=level,
                            message=(
                                f"shared tier `{d}/{doc.name}` names `{token}` — "
                                f"{rule.replace('-', ' ')} in a document that ships to every repo"
                            ),
                            path=doc,
                            hint=hint,
                        )
                    )

        # --- the questionnaire's own derived field --------------------------------
        # ONE DIRECTION ONLY, and the asymmetry is the point. A command PRESENT here that
        # declares a slot must appear in that slot's `consumed_by` — that is the drift this
        # catches, and it moved on 31 of 43 rows the first time anything looked. The reverse
        # is legitimate: `consumed_by` is authored against the WHOLE tree, and a repo that
        # does not receive a `scope: product` command correctly has no spine for it. Checking
        # both directions fired 11 errors in the first synced repo it met, every one of them
        # describing the sync working exactly as designed. `_slots.py` already warns about a
        # `consumed_by` naming a command with no spine here, which is the honest severity for
        # it.
        here = {c.id for c in cmds if c.has_spine}
        for slot in questions.slots:
            declared_here = sorted(c.id for c in cmds if slot.id in set(c.requires) | set(c.optional))
            recorded = set(slot.consumed_by)
            unrecorded = [c for c in declared_here if c not in recorded]
            if unrecorded:
                out.append(
                    Finding(
                        level="error",
                        message=(
                            f"slot `{slot.id}`: declared by {', '.join(unrecorded)}, which "
                            "`consumed_by` does not record"
                        ),
                        hint="`consumed_by` is derived from the spines; regenerate it rather than editing it.",
                    )
                )
            # A recorded command that IS in this checkout and no longer declares the slot is
            # the other half of the same drift, and is checkable without punishing absence.
            dropped = sorted(c for c in recorded & here if c not in set(declared_here))
            if dropped:
                out.append(
                    Finding(
                        level="error",
                        message=(
                            f"slot `{slot.id}`: `consumed_by` records {', '.join(dropped)}, which no longer declare it"
                        ),
                        hint="`consumed_by` is derived from the spines; regenerate it rather than editing it.",
                    )
                )

        # --- a baseline that can only shrink --------------------------------------
        # The baseline records the HOME render — the tree as its authors receive it, with no
        # namespace declared. A repository that declares one (any, the source's own included)
        # holds the customer render, from which the home-only passages the baseline accepts were
        # dropped; "no longer fires" there is a fact about the render, not a line to delete, and
        # the file it names is the package's, which that repository cannot edit.
        if str(kb.config.commands.get("namespace") or ""):
            return out
        owned = {_key(tier, kb.root / c.path, "", "").rsplit("::", 2)[0] for c in cmds} | {
            _key(tier, doc, "", "").rsplit("::", 2)[0] for _, doc in _shared_docs(tier)
        }
        stale = sorted(k for k in baseline - fired if k.split("::", 1)[0] in owned)
        for key in stale:
            out.append(
                Finding(
                    level="advisory",
                    message=f"baselined portability finding no longer fires and should be removed: {key}",
                    path=BASELINE,
                    hint="Delete the line. A baseline that keeps entries it no longer needs stops being a ratchet.",
                )
            )
        return out


CHECKS = [CommandPortability()]
