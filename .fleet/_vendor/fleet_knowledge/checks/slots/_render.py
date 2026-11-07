"""`command-render` — a foreign rendering of the core commands carries nothing of the vendor's.

`command-portability` reads the SOURCE tree: it asks whether a command only names what the
fixed layout provides. This check asks the other half of PRD 0746's question — when the tree is
**rendered for a customer** (namespace `acme`, and the customer default — the tree's own
namespace, `commandsync.CUSTOMER_NAMESPACE`; no home text in either), does any prior-vendor
name, corpus path or dated incident survive the render? The render is what actually ships; a
marker that failed to cover a passage is invisible in the source and obvious here.

**rendered for a customer** (namespace `acme`, and the customer default — the tree's own
namespace, `commandsync.CUSTOMER_NAMESPACE`; no home text in either), does any prior-vendor
name, corpus path or dated incident survive the render? The render is what actually ships; a
marker that failed to cover a passage is invisible in the source and obvious here.

What it scans: every file the repository's set ships — the `tier: core` commands (the whole
tree when the repository declares `set = "all"`), the shared documents they link, the scripts
they run and the board vocabulary JSON — rendered exactly as
`commandsync.render` would ship them to a `namespace = "acme"` repository and to one declaring
the customer default. Inside code fences too, because a fenced example is what an agent copies;
in a script, its string literals (what it prints), not its comments (what its maintainers read).
Before the deny-list runs, the ONE sanctioned vendor string is blanked: the default's command
prefix, in the three shapes `commandsync.without_command_prefix` names, because that is what a
customer's commands are typed under by default (owner decision 2026-10-15).

What it refuses, beyond the prior-vendor tokens:

  * RESIDUE — what a removed home segment with no `<!-- else -->` leaves behind: an empty
    `()`, an empty code span, a link to `#`, a title `#  X`, a space before punctuation, a
    marker or a command whose name was stripped. The renderer tidies what it safely can
    (`commandsync._tidy_holes`); anything left is a hole in an instruction, and the source
    gets an `else` or a wider marker.
  * HOME-PROJECT NAMES AND IDS — the people, stack and subsystems in
    `internal_denylist.txt`, and an issue / requirement / program / slice / capability id or
    a home PRD number (`_INTERNAL_ID`).
  * A prior-vendor name other than the command prefix: a compound name, a domain or the bare
    word still fails. The prior-vendor tokens are held as data beside the tree
(`commandtree/vendor_denylist.txt`, the same tokens 0742 maintains for the served surfaces, which
this stdlib-only package cannot import), and the portability patterns are `_portability.py`'s own
so the two checks cannot drift about what a corpus path or a history citation is. The product-docs
reading (`.fleet/docs/`) is the one exception: the supported install command's repository URL is
sanctioned there (`commandsync.sanctioned_docs_urls()`, held as data beside the tree), because a
person must copy it to get the `fleet` command. A command render still refuses it.

**Strict** (`STRICT = True`): the home markers are complete across the closure, so every
finding is an error and a passage the markers did not cover fails the build. The flag stayed
false while backend-plan-3 was still writing the markers, and was flipped by its last task.
"""

from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path

from fleet_knowledge import commands as commandmod
from fleet_knowledge import commandsync, idkinds
from fleet_knowledge.checks.slots import _portability as port
from fleet_knowledge.config import KnowledgeBase
from fleet_knowledge.runner import Finding

#: Flipped to true by backend-plan-3's last task, once the closure is marked. A finding is
#: now an error: a passage the home-only markers did not cover fails the build.
STRICT = True

#: The data file of prior-vendor tokens, shipped beside the tree.
DENYLIST_FILE = "vendor_denylist.txt"

#: The namespace a customer render is *tested* under. `acme` is the PRD's own example.
TEST_NAMESPACE = "acme"

#: Every namespace the closure is rendered under: the PRD's own example, which proves each
#: command reference is rewritten, and the customer default, which proves that declaring the
#: tree's own namespace is still a customer render and not the home one.
RENDER_NAMESPACES = (TEST_NAMESPACE, commandsync.CUSTOMER_NAMESPACE)

#: The home project's people, stack and subsystem names, held as data like the vendor tokens.
INTERNAL_DENYLIST_FILE = "internal_denylist.txt"

#: An issue, requirement, program, slice or capability id of the HOME project, and a home PRD
#: number. A customer's own ids live in its corpus, never in the tier, so any of these in a
#: rendered file is the home project's history — in prose, in a fenced example, in a script's
#: runtime message. Placeholders (`PG-NN`, `SL-NNN`, `<KEY>`) carry no digit and never match.
_INTERNAL_ID = re.compile(rf"\b(?:(?i:eng)|{'|'.join(idkinds.HOME_PREFIXES)})-\d+\b|\bPRDs? \d{{4}}\b")

#: What a removed home segment leaves behind when nobody gave it an `else`. Each is a hole a
#: reader falls into: an instruction with its object missing, a heading with an empty slot.
_RESIDUE: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("an empty `()`", re.compile(r"(?<![\w\]\)>`'\"])\(\s*[,;/]?\s*\)")),
    ("a parenthetical opening on a separator", re.compile(r"\(\s*[,;:]\s")),
    ("a parenthetical closing on a separator", re.compile(r"\s[,;]\s*\)")),
    ("an empty code span", re.compile(r"(?<!`)``(?!`)")),
    ("a link to `#`", re.compile(r"\]\(#\)")),
    ("a link with no text", re.compile(r"(?<!!)\[\]\(")),
    ("a title with two spaces after the hash", re.compile(r"^#{1,6}  +\S", re.M)),
    ("a space before punctuation", re.compile(r"(?<=[\w*`)]) [,;:.](?=\s|$)")),
    ("a marker with its name stripped", re.compile(r"<!-- -[a-z]")),
    ("a command with its namespace stripped", re.compile(r"(?<![\w/.])/:[a-z.…]")),
)
_FENCE = re.compile(r"^\s*(```|~~~)")
_DOUBLE_SPAN = re.compile(r"(?<!`)``(?!`).+?(?<!`)``(?!`)")
_CODE_SPAN = re.compile(r"(?<!`)`[^`\n]+`(?!`)")


def _deny_tokens() -> tuple[str, ...]:
    """The tokens, longest first, from the shipped data file. Empty when the file is absent."""
    path = commandsync.source_root() / DENYLIST_FILE
    if not path.is_file():
        return ()
    out = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return tuple(sorted(out, key=len, reverse=True))


def _tokens(name: str) -> tuple[str, ...]:
    path = commandsync.source_root() / name
    if not path.is_file():
        return ()
    out = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return tuple(sorted(out, key=len, reverse=True))


def _internal_re() -> re.Pattern[str] | None:
    words = _tokens(INTERNAL_DENYLIST_FILE)
    if not words:
        return None
    alt = "|".join(re.escape(w) for w in words)
    return re.compile(rf"(?<![\w.-])(?:{alt})(?![\w-])", re.IGNORECASE)


def residue(text: str) -> list[str]:
    """Every hole a removed home segment left in rendered markdown, as `line N: what`.

    Read on prose AND inside fences, because a fenced example is what an agent copies: the
    `## Files` manifest example that rendered to two empty bullets sat in a fence. Code spans
    are blanked before the space-before-punctuation rule, so `git add .` is not prose.
    """
    out: list[str] = []
    in_fence = False
    for n, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        for what, pattern in _RESIDUE:
            probe = line
            if what == "a space before punctuation":
                if in_fence or line.lstrip().startswith("|"):
                    continue
                probe = _CODE_SPAN.sub("x", line)
            if what.startswith("a parenthetical") and in_fence:
                continue
            if what == "an empty code span":
                # A double-backtick span (``x``, `` `x` ``) is two backticks that are not empty;
                # one opening or closing at a line edge is a span that wraps onto the next line.
                probe = _DOUBLE_SPAN.sub("x", line)
                probe = re.sub(r"^\s*``(?=\s\S)|(?<=\S)``\s*$", "x", probe)
            if pattern.search(probe):
                out.append(f"line {n}: {what}")
    return out


def _python_surface(text: str) -> str:
    """What a shipped script SAYS: its string literals (messages, usage, docstrings).

    A comment is the maintainers' engineering note — it prints to nobody and is the record of
    why a line exists, so it is not scanned. Everything a customer's session reads when the
    script runs or is asked for `--help` is a string, and that is. Unparseable source is
    scanned whole rather than skipped.
    """
    kinds = {tokenize.STRING} | {getattr(tokenize, "FSTRING_MIDDLE", tokenize.STRING)}
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return text
    return "\n".join(tok.string for tok in tokens if tok.type in kinds)


def scan_rendered(rel: str, text: str) -> list[str]:
    """Everything a customer-rendered file must not carry, one message per hit.

    `rel` decides what applies: markdown is checked for residue, and every file — markdown,
    shipped script, JSON vocabulary — for a vendor token, a home-project name and a home id,
    inside code fences and string literals as much as in prose.

    The product-docs reading (`.fleet/docs/`) carries the vendor-named URLs in
    `commandsync.sanctioned_docs_urls()`: the supported install command's repository URL. A person
    must copy that exact URL to get the `fleet` command, and the customer install guides already
    allow the same repository. They are blanked only here, so a command render still refuses them.
    """
    out: list[str] = []
    if rel.endswith(".py"):
        text = _python_surface(text)
    if rel.startswith(f"{commandsync.DOCS_REL}/"):
        for url in commandsync.sanctioned_docs_urls():
            text = text.replace(url, "")
    if rel.endswith(".md"):
        out += [f"{rel}: {hit} — a home segment was removed and left a hole" for hit in residue(text)]
    deny = _deny_tokens()
    if deny:
        deny_re = re.compile("|".join(re.escape(t) for t in deny), re.IGNORECASE)
        for token in sorted({m.group(0).lower() for m in deny_re.finditer(text)}):
            out.append(f"{rel}: a foreign render still carries `{token}`")
    internal = _internal_re()
    if internal is not None:
        for token in sorted({m.group(0).lower() for m in internal.finditer(text)}):
            out.append(f"{rel}: a foreign render still carries the home-project name or stack token `{token}`")
    for token in sorted({m.group(0) for m in _INTERNAL_ID.finditer(text)}):
        out.append(f"{rel}: a foreign render still carries the home-project id `{token}`")
    return out


class CommandRender:
    name = "command-render"
    title = "a foreign render of the commands this repository ships carries no home-project or vendor text"
    description = (
        "Every markdown file in the shipped set (`tier: core` commands — the whole tree for "
        '`set = "all"` — plus the shared documents they link) is rendered as a customer '
        "install would receive it — namespace `acme` and the customer default, home segments "
        "dropped — and scanned for a prior-vendor name other than the command prefix, a corpus "
        "path outside the fixed layout, or a dated incident. A finding is a passage the "
        "home-only markers did not cover."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        # The packaged tree travels with the package, so the check has something to read
        # wherever a corpus is resolved. It is about the shipped commands, not this corpus.
        return True

    def run(self, kb: KnowledgeBase) -> list[Finding]:  # noqa: ARG002 — the tree is the package's
        src = commandsync.source_root()
        if not (src / commandsync.COMMANDS_SUBDIR).is_dir():
            return []
        level = "error" if STRICT else "advisory"
        # What this repository receives decides what the guard must look at (ENG-21056): a
        # namespace-only repository gets the core set (the customer default), and a repository
        # that asks for `set = "all"` gets every command — including the depth commands, which is
        # exactly where home text hides. The home tree (no namespace) is screened as the customer
        # default, because that is what a customer install receives from it.
        namespace = str(kb.config.commands.get("namespace") or "")
        set_name = str(kb.config.commands.get("set") or "core")
        if not namespace:
            set_name = "core"
        scanned = "all" if set_name == "all" else "core"
        shared, _scripts = commandsync._core_closure(src)
        tiers = commandmod.tiers(src / commandsync.COMMANDS_SUBDIR)
        shipped_commands = {rel for rel, tier in tiers.items() if scanned == "all" or tier == "core"}
        rels = sorted(
            [Path(commandsync.COMMANDS_SUBDIR) / rel for rel in sorted(shipped_commands)]
            + [Path(rel) for rel in sorted(shared)]
        )
        out: list[Finding] = []
        source = commandsync.source_namespace(src)
        shipped_paths = {rel[len(source) + 1 :] for rel in shipped_commands}

        # The repository's own command configuration must be coherent before its render is
        # (PRD 0746 D1/D5, E5): a bad namespace, or a `commands_dir` whose basename disagrees
        # with a declared namespace, is an error — the two are one path said twice and must say
        # the same thing.
        commands_dir = str(kb.config.slots.get("commands_dir") or "")
        if namespace and not commandsync.NAMESPACE_RE.fullmatch(namespace):
            out.append(
                Finding(
                    level="error",
                    message=f"`[fleet.commands] namespace = {namespace!r}` is not `[a-z][a-z0-9-]{{1,30}}`",
                    hint="A namespace is lower-case, two characters or more, e.g. `acme`.",
                )
            )
        elif namespace and commands_dir and commands_dir.rstrip("/").rsplit("/", 1)[-1] != namespace:
            out.append(
                Finding(
                    level="error",
                    message=f"`commands_dir` ({commands_dir}) and `namespace` ({namespace}) disagree",
                    hint=(
                        "One is derived from the other; set `commands_dir` to `.fleet/commands/<namespace>` "
                        "(`.claude/commands/<namespace>` on the legacy layout)."
                    ),
                )
            )
        seen: set[str] = set()

        def add(finding: Finding) -> None:
            # One passage the markers missed fails under both namespaces; report it once.
            if finding.message not in seen:
                seen.add(finding.message)
                out.append(finding)

        for rel in rels:
            if not (src / rel).is_file():
                continue
            for ns in RENDER_NAMESPACES:
                try:
                    rendered = commandsync.render(src, rel, namespace=ns).decode("utf-8", "ignore")
                except (ValueError, FileNotFoundError) as exc:
                    add(
                        Finding(
                            level=level,
                            message=f"{rel}: the foreign render refused — {exc}",
                            hint="Fix the home markers in this file (PRD 0746 D2).",
                        )
                    )
                    break
                text = commandsync.without_command_prefix(rendered)
                for message in scan_rendered(str(rel), text):
                    add(
                        Finding(
                            level=level,
                            message=message,
                            hint=(
                                "Give the home segment an `<!-- else -->` with generic text, widen the "
                                "marker to the whole clause, or reach the thing through a slot (PRD 0746 D2)."
                            ),
                        )
                    )
                scan = port._scan(text)
                # A link the render KEPT between two shipped commands names a file every customer
                # install receives at that relative path — the layout, not a corpus.
                for token in sorted(scan["corpus-path"] - shipped_paths):
                    add(
                        Finding(
                            level=level,
                            message=f"{rel}: a foreign render still names the corpus path `{token}`",
                            hint="Reach it through a slot, or mark the passage home-only.",
                        )
                    )
                for token in sorted(scan["history"]):
                    add(
                        Finding(
                            level=level,
                            message=f"{rel}: a foreign render still cites `{token}`",
                            hint="State the rule rather than the ticket, or mark it home-only.",
                        )
                    )
        out += self._scan_scripts_and_vocabulary(src, level, set_name=scanned)
        return out

    @staticmethod
    def _scan_scripts_and_vocabulary(src: Path, level: str, *, set_name: str = "core") -> list[Finding]:
        """The shipped scripts the set runs and the board vocabulary JSON, as rendered.

        Neither is markdown and neither went through the old scan, which is how a script's
        runtime message citing a home issue and a JSON `_comment` naming one reached every
        customer install. Read under the `acme` render: home text is dropped identically under
        every declared namespace, so `acme` catches the same leaks, and a script's hard-coded
        `.claude/commands/<old-namespace>` path stays visible (the declared-default render
        rewrites the command directory name itself, which is the repository's namespace and not
        a vendor leak). The set decides which scripts and vocabulary entries ship: a
        `set = "all"` repository receives the depth scripts too (ENG-21056).
        """
        out: list[Finding] = []
        shipped = commandsync._shipped_for(src, namespace=TEST_NAMESPACE, set_name=set_name, name="")
        scripts = {rel for rel in shipped if rel.startswith(commandsync.SCRIPTS_SUBDIR + "/")}
        for rel in sorted(scripts):
            path = Path(rel)
            if not (src / path).is_file():
                continue
            text = commandsync.render(src, path, namespace=TEST_NAMESPACE).decode("utf-8", "ignore")
            text = commandsync.without_command_prefix(text)
            for message in scan_rendered(str(rel), text):
                out.append(Finding(level=level, message=message, hint="Say the rule, not the ticket."))
        vocab = commandsync.render_vocabulary(src, shipped, namespace=TEST_NAMESPACE)
        if vocab is not None:
            rel = commandsync.VOCABULARY_SOURCE
            text = commandsync.without_command_prefix(vocab.decode("utf-8", "ignore"))
            for message in scan_rendered(str(rel), text):
                out.append(Finding(level=level, message=message, hint="Say the rule, not the ticket."))
        return out


CHECKS = [CommandRender()]
