"""The conventional targets — what a command means by "lint" or "the unit lane", and what runs here.

The shipped command tier names a gate or a lifecycle action by its CONVENTIONAL name: lint, the
unit lane, codegen, bringing the stack up. What actually runs is the receiving repository's own
command, and the repository says it once, in `[fleet.targets]` in `.fleet/fleet.toml`:

    [fleet.targets]
    lint = "mvn -q spotless:check"
    test-unit = "mvn -q test"
    test-one = "mvn -q test -Dtest={T}"

**The tier never names a command; it names a target.** A source document writes the target as a
token, `{{target:test-unit}}` — or, for a target that takes an argument,
`{{target:test-one T=<TestName>}}` — and `fleet commands sync` replaces every token with this
repository's command from the table (`render_text`), so the procedure an agent reads says exactly
what to type here. The token is the one spelling: a literal `make test-unit` in the shipped tier is
a `command-portability` error, because it would run one repository's Makefile in every other.

**A target the repository has not configured renders as a refusal**, never as a silent no-op: a
command that prints why it cannot run and exits 2 (`refusal`). An agent that reaches it stops and
reports it, exactly as it did at the stub Makefile's refusal recipes this table replaces.
`validate-knowledge` is the exception: its checks ship with the tier, so an unconfigured
`validate-knowledge` runs Fleet's own recipe (`SHIPPED`), and a repository overrides it by naming
its own.

**Placeholders.** A target that takes an argument declares it (`Target.params`), and the
repository's value must use each one as `{NAME}`: `go test ./... -run {T}`. The token in the tier
supplies the value (`T=<TestName>`), which the render substitutes. Only a declared name is a
placeholder — `${HOME}` and `{print $1}` are shell, and are left alone.

Stdlib only.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "SHIPPED",
    "TARGETS",
    "TOKEN_RE",
    "Target",
    "command",
    "effective",
    "expansion_patterns",
    "read_table",
    "refusal",
    "render_text",
    "table_block",
    "token",
]


@dataclass(frozen=True)
class Target:
    """One conventional target: its name, what a command means by it, and the arguments it takes."""

    name: str
    #: One plain phrase. It is printed inside the refusal's shell string, so it carries no
    #: backtick, double quote, dollar sign or backslash (a test holds every meaning to that).
    meaning: str
    #: The placeholders a value must use and a token must supply, in order.
    params: tuple[str, ...] = ()


def _t(name: str, meaning: str, *params: str) -> tuple[str, Target]:
    return name, Target(name, meaning, params)


#: The closed vocabulary, in the order a table lists them. A key outside it is refused in
#: `fleet.toml` exactly as an unknown option is anywhere else in that file.
TARGETS: dict[str, Target] = dict(
    (
        # the gate — what green means
        _t("lint", "the static checks a commit must pass"),
        _t("lint-fix", "the mechanical auto-fixes, run before hand-fixing lints"),
        _t("lint-ci", "the static checks CI runs, where they exceed lint"),
        _t("typecheck", "the type checker over the whole tree"),
        _t("build", "compile or bundle every artifact"),
        _t("test", "every suite, the CI equivalent"),
        _t("test-unit", "the fast unit lane, no services"),
        _t("test-db", "the lane that needs a database up"),
        _t("test-e2e", "the full-stack lane"),
        _t("test-one", "one test by name", "T"),
        _t("coverage", "the unit lane with the coverage gate"),
        _t("pre-commit-dry", "the commit hooks over the working tree, writing nothing"),
        # one aggregate, so the push pre-flight and CI run the same checks rather than two copies
        _t("preflight", "the lane's fast mechanical guards, run before the first push — the same checks CI runs"),
        # the corpus — the knowledge validators the tier's own scripts run
        _t("validate-knowledge", "the corpus validators (fleet check and the shipped validate scripts)"),
        # codegen
        _t("generate", "regenerate everything derived from a source of truth"),
        _t("generate-page-specs", "regenerate the surface specs' derived sections"),
        # the stack
        _t("dev", "the full stack with hot reload, in the foreground"),
        _t("dev-headless", "the full stack, backgrounded, for a browser pass"),
        _t("dev-services", "only the backing services (a database, a queue)"),
        _t("dev-stop", "stop whatever dev started"),
        _t("seed", "seed the running stack"),
        _t("reseed", "reset and seed the running stack"),
        # a named agent loop the repository hosts
        _t("agent-loop", "run a named agent loop", "LOOP"),
        _t("agent-loop-install", "install a named agent loop's prompt", "LOOP", "PROMPT"),
    )
)

#: The targets Fleet fills ITSELF when the repository names none: their commands run only what the
#: command sync ships, so every repository has them. `knowledge/scripts/fleet.py` reaches the
#: `fleet` CLI whether the package is installed (a worker's `python3` carries it) or checked out
#: as a submodule. This is the recipe the stub Makefile's `validate-knowledge` carried.
SHIPPED: dict[str, str] = {
    "validate-knowledge": (
        "python3 knowledge/scripts/fleet.py check --repo . && "
        "python3 knowledge/scripts/validate_requirements.py && "
        "python3 knowledge/scripts/validate_id_collisions.py"
    ),
}

#: Where the table lives, as a reader is told to find it.
TABLE = "[fleet.targets]"
CONFIG_REL = ".fleet/fleet.toml"

#: `{{target:test-unit}}`, `{{target:test-one T=<TestName>}}`. Two braces and a `target:` prefix:
#: no Markdown, shell or TOML spelling produces it, so a render can replace every occurrence
#: without guessing. A name must open on a lower-case letter, so the documentation's own
#: `{{target:<name>}}` is not a token and survives a render as written.
TOKEN_RE = re.compile(r"\{\{target:([a-z][a-z0-9-]*)((?:[ \t]+[A-Z][A-Z0-9_]*=[^\s{}]+)*)[ \t]*\}\}")
#: The opening of any token, for finding one the strict pattern above does not match.
TOKEN_OPEN = "{{target:"
_ARG = re.compile(r"([A-Z][A-Z0-9_]*)=([^\s{}]+)")
#: Shell control operators: a value holding one is wrapped in a subshell when substituted, so
#: `{{target:lint}} && {{target:test-unit}}` keeps meaning "lint, then the unit lane".
_COMPOUND = re.compile(r"&&|\|\||[;&|\n]")


class TargetError(ValueError):
    """A `[fleet.targets]` value, or a token, that cannot be rendered as given."""


def token(name: str, args: Mapping[str, str] | None = None) -> str:
    """The token a source document writes for `name` with `args`."""
    rest = "".join(f" {k}={v}" for k, v in (args or {}).items())
    return f"{{{{target:{name}{rest}}}}}"


def _placeholder(name: str) -> re.Pattern[str]:
    # `{T}`, never `${T}`: a shell parameter expansion is not a placeholder.
    return re.compile(r"(?<!\$)\{" + re.escape(name) + r"\}")


def read_table(raw: Any, source: Path | str) -> dict[str, str]:
    """A `[fleet.targets]` table, checked: known names only, non-empty single-line strings, every
    declared placeholder used. Raises `TargetError` naming the first problem and the fix."""
    if not isinstance(raw, Mapping):
        raise TargetError(f"{source}: `targets` must be a table — write `{TABLE}`, got {raw!r}")
    unknown = sorted(set(raw) - set(TARGETS))
    if unknown:
        raise TargetError(
            f"{source}: unknown target(s) {', '.join(unknown)} in {TABLE} — the conventional targets are "
            f"{', '.join(TARGETS)}"
        )
    out: dict[str, str] = {}
    for name, value in raw.items():
        target = TARGETS[name]
        if not isinstance(value, str) or not value.strip():
            raise TargetError(
                f"{source}: {TABLE} `{name}` must be the shell command that runs {target.meaning}, got {value!r}"
                " — leave the key out when this repository has none"
            )
        if "\n" in value or "`" in value:
            raise TargetError(
                f"{source}: {TABLE} `{name}` must be one line without a backtick — it is printed inside the "
                "commands' code spans; put a longer recipe in a script and name the script"
            )
        missing = [p for p in target.params if not _placeholder(p).search(value)]
        if missing:
            raise TargetError(
                f"{source}: {TABLE} `{name}` takes {', '.join('{' + p + '}' for p in target.params)} — "
                f"the value must use {', '.join('{' + p + '}' for p in missing)} where the argument goes, "
                f'e.g. `{name} = "{_example(target)}"`'
            )
        out[name] = value.strip()
    return out


def _example(target: Target) -> str:
    args = " ".join(f"{{{p}}}" for p in target.params)
    return f"<your command> {args}".strip()


def effective(table: Mapping[str, str] | None) -> dict[str, str]:
    """The commands a render substitutes: the repository's table over Fleet's own (`SHIPPED`)."""
    return {**SHIPPED, **(table or {})}


def refusal(name: str) -> str:
    """What an unconfigured target renders as: a command that says why it cannot run and exits 2.

    A subshell, so a chain (`lint && test-unit`) stops at it and its exit status is the chain's.
    """
    meaning = TARGETS[name].meaning
    return (
        f'(echo "fleet: this repository has no {name} command configured ({meaning}) — add one under '
        f'{TABLE} in {CONFIG_REL}; until then stop and report it" >&2; exit 2)'
    )


def _literal(text: str) -> Callable[[re.Match[str]], str]:
    """A `re.sub` replacement that inserts `text` as written, never as a template."""

    def replace(_match: re.Match[str]) -> str:
        return text

    return replace


def command(name: str, table: Mapping[str, str] | None, args: Mapping[str, str] | None = None) -> str:
    """The text a token for `name` with `args` renders to under `table` (see `effective`)."""
    target = TARGETS.get(name)
    if target is None:
        raise TargetError(f"`{token(name, args)}` names no conventional target — known: {', '.join(TARGETS)}")
    given = dict(args or {})
    if sorted(given) != sorted(target.params):
        want = " ".join(f"{p}=<…>" for p in target.params) or "no arguments"
        raise TargetError(f"`{token(name, given)}` must carry {want}")
    value = effective(table).get(name)
    if value is None:
        return refusal(name)
    for param, arg in given.items():
        # A replacement string would read `\1` or `\g<..>` in the argument as a group reference.
        value = _placeholder(param).sub(_literal(arg), value)
    return f"({value})" if _COMPOUND.search(value) else value


def render_text(text: str, table: Mapping[str, str] | None, *, where: str = "") -> str:
    """`text` with every token replaced by this repository's command (`command`).

    A token that names no target, carries the wrong arguments, or does not parse is refused by
    name rather than rendered — a gate step that silently became prose is the failure this exists
    to prevent.
    """
    if TOKEN_OPEN not in text:
        return text
    prefix = f"{where}: " if where else ""

    def one(m: re.Match[str]) -> str:
        args = dict(_ARG.findall(m.group(2)))
        try:
            out = command(m.group(1), table, args)
        except TargetError as exc:
            raise TargetError(prefix + str(exc)) from None
        # A grouped command (a refusal, a compound value) opens with `(`. Right after another `(` —
        # `$({{target:x}})` — that would read `$((`, which bash parses as ARITHMETIC expansion, not a
        # command substitution. A space keeps it `$( (…))`.
        if out.startswith("(") and m.start() > 0 and m.string[m.start() - 1] == "(":
            out = " " + out
        return out

    out = TOKEN_RE.sub(one, text)
    stray = re.search(r"\{\{target:[a-z]", out)
    if stray is not None:
        line = out[: stray.start()].count("\n") + 1
        raise TargetError(f"{prefix}line {line}: a `{TOKEN_OPEN}…}}}}` token that does not parse")
    return out


def expansion_patterns(table: Mapping[str, str] | None) -> re.Pattern[str]:
    """One pattern matching anything `render_text` can produce under `table`.

    What lets `command-portability` read a RENDERED tier: the repository's own commands are what
    the tokens became there, and blanking them before the scan leaves only text the source wrote —
    where a literal `make lint` is still an error.
    """
    alternatives: list[str] = []
    for name in TARGETS:
        rendered = command(name, table, {p: f"\x00{p}\x00" for p in TARGETS[name].params})
        pattern = re.escape(rendered)
        for p in TARGETS[name].params:
            pattern = pattern.replace(re.escape(f"\x00{p}\x00"), r"[^\s`]+")
        alternatives.append(pattern)
    alternatives.sort(key=len, reverse=True)
    return re.compile("|".join(alternatives))


def _toml_string(value: str) -> str:
    """`value` as a TOML string: a literal string when it can be one (no escaping to read), else basic."""
    if "'" not in value and "\n" not in value:
        return f"'{value}'"
    return json.dumps(value, ensure_ascii=False)


def table_block(values: Mapping[str, str], *, header: str = "[fleet.targets]") -> str:
    """The `[fleet.targets]` table as `fleet init` and the migration write it.

    Every conventional target is listed, in vocabulary order: a configured one as its value, an
    unconfigured one as a comment naming what it means and the placeholders it takes — so the file
    itself is the list of what is left to fill in.
    """
    lines = [
        header,
        "# What each conventional target runs in THIS repository. The commands name a target (lint, the",
        "# unit lane, the stack); `fleet commands sync` writes the command below into them. A target left",
        "# out renders as a refusal the agent stops at — fill in the ones this repository has. A target",
        '# that takes an argument uses it as {NAME}: `test-one = "go test ./... -run {T}"`.',
    ]
    for name, target in TARGETS.items():
        params = f" (uses {', '.join('{' + p + '}' for p in target.params)})" if target.params else ""
        if name in values:
            lines.append(f"{name} = {_toml_string(values[name])}")
        elif name in SHIPPED:
            lines.append(f"# {name} = ...   # {target.meaning}; unset runs Fleet's own checks")
        else:
            lines.append(f"# {name} = ...   # {target.meaning}{params}")
    return "\n".join(lines) + "\n"
