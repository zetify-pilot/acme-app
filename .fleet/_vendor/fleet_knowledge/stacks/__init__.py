"""Stack profiles — what a repository builds in, as data, rendered into the commands its targets run.

A profile is one TOML file beside this module (`dotnet.toml`, `node-vue.toml`, …). It declares
how to recognise the stack in a repository (`[[detect]]`), the recipe for each conventional
target it can serve (`[targets]`), the settings a recipe reads (`[vars]`), what its recipes need
installed first (`[deps]`), and what the worker must have installed (`[[toolchain]]`).
`_compose.toml` holds the two rules about how targets combine across stacks. A new stack is a new
TOML file and a fixture; nothing here names a stack.

Rendering produces one shell command per conventional target (`target_commands`), which `fleet
init` writes into the `[fleet.targets]` table of `.fleet/fleet.toml`: a target several stacks
declare runs each stack's recipe in turn (`lint` is the .NET lint, then the Vue lint), so a command
names one target however many stacks a repository mixes. Releases before the table rendered the
same recipes into a `fleet.mk` beside a stub Makefile; `render_fleet_mk` and
`choices_from_fleet_mk` remain only so the migration can recognise and fold an unedited one.

Pure apart from `detect_repo` / `resolve_repo`, which list and read a checkout. Stdlib only.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import tomllib
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path, PurePosixPath
from typing import Any

__all__ = [
    "Choice",
    "Profile",
    "Tool",
    "UnknownStackError",
    "contract_path",
    "contract_text",
    "languages_answer",
    "choices_from_fleet_mk",
    "quality_commands",
    "target_commands",
    "render_ci",
    "render_ci_readme",
    "runner_from_ci",
    "detect",
    "detect_repo",
    "install_lines",
    "profiles",
    "render_fleet_mk",
    "rendered_targets",
    "repo_paths",
    "resolve",
    "resolve_repo",
    "toolchain",
    "toolchain_table",
]

DATA_DIR = Path(__file__).resolve().parent

#: Directories detection never looks inside: vendored dependencies, build output, VCS and tool
#: state. A `package.json` naming vue inside `node_modules/` is somebody else's project.
IGNORED_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "bin",
        "obj",
        "dist",
        "build",
        "out",
        "vendor",
        ".venv",
        "venv",
        "__pycache__",
        ".claude",
        "target",
        ".fleet",
        ".idea",
        ".vscode",
    }
)
MAX_DEPTH = 6


class UnknownStackError(ValueError):
    """A stack id no profile defines."""


@dataclass(frozen=True)
class Tool:
    """One thing the worker must have installed. `install` uses the worker toolchain manifest's
    vocabulary: `apt:<package>`, `nodesource:<major>`, `binary:<url, {arch} = uname -m>`."""

    tool: str
    name: str
    install: str
    version: str = ""
    source: str = ""


@dataclass(frozen=True)
class Rule:
    files: tuple[str, ...]
    contains: str = ""


@dataclass(frozen=True)
class Var:
    name: str
    default: str
    find: tuple[str, ...] = ()
    contains: str = ""
    value: str = "path"  # "path" of the found file, or its "dir"
    export: bool = False


@dataclass(frozen=True)
class Profile:
    id: str
    title: str
    detect: tuple[Rule, ...]
    targets: Mapping[str, tuple[str, ...]]
    toolchain: tuple[Tool, ...]
    vars: tuple[Var, ...] = ()
    deps: Mapping[str, Any] = field(default_factory=dict)
    rooted: bool = True
    quality: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    contract: str = ""
    ci_setup: tuple[Mapping[str, Any], ...] = ()

    @property
    def recipes(self) -> dict[str, tuple[str, ...]]:
        """Every target this profile renders: the conventional ones, then the release's quality ones."""
        return {**self.targets, **self.quality}

    @property
    def root_var(self) -> str:
        return self.id.upper().replace("-", "_") + "_ROOT"


@dataclass(frozen=True)
class Choice:
    """A stack chosen for one repository: which profile, where it lives, its resolved settings."""

    id: str
    root: str = "."
    vars: Mapping[str, str] = field(default_factory=dict)


# ── loading ──────────────────────────────────────────────────────────────────


def _lines(value: str | list[str]) -> tuple[str, ...]:
    return (value,) if isinstance(value, str) else tuple(value)


def _profile(data: Mapping[str, Any]) -> Profile:
    return Profile(
        id=data["id"],
        title=data.get("title", data["id"]),
        detect=tuple(Rule(tuple(r["files"]), r.get("contains", "")) for r in data.get("detect", [])),
        targets={name: _lines(recipe) for name, recipe in data.get("targets", {}).items()},
        toolchain=tuple(Tool(**t) for t in data.get("toolchain", [])),
        vars=tuple(
            Var(
                name=name,
                default=spec.get("default", ""),
                find=tuple(spec.get("find", ())),
                contains=spec.get("contains", ""),
                value=spec.get("value", "path"),
                export=bool(spec.get("export", False)),
            )
            for name, spec in data.get("vars", {}).items()
        ),
        deps=data.get("deps", {}),
        rooted=bool(data.get("rooted", True)),
        quality={name: _lines(recipe) for name, recipe in data.get("quality", {}).items()},
        contract=data.get("contract", ""),
        ci_setup=tuple(data.get("ci", {}).get("setup", ())),
    )


@cache
def profiles() -> dict[str, Profile]:
    """Every shipped profile, by id, in id order."""
    out: dict[str, Profile] = {}
    for path in sorted(DATA_DIR.glob("*.toml")):
        if path.name.startswith("_"):
            continue
        profile = _profile(tomllib.loads(path.read_text(encoding="utf-8")))
        out[profile.id] = profile
    return out


@cache
def _compose() -> tuple[dict[str, tuple[str, ...]], frozenset[str]]:
    data = tomllib.loads((DATA_DIR / "_compose.toml").read_text(encoding="utf-8"))
    built = {k: tuple(v) for k, v in data.get("built_from", {}).items()}
    return built, frozenset(data.get("together", {}).get("targets", ()))


@cache
def _quality_meanings() -> dict[str, str]:
    data = tomllib.loads((DATA_DIR / "_compose.toml").read_text(encoding="utf-8"))
    return dict(data.get("quality", {}))


def _profile_of(sid: str) -> Profile:
    known = profiles()
    if sid not in known:
        raise UnknownStackError(f"unknown stack `{sid}` (known: {', '.join(known)})")
    return known[sid]


# ── detection ────────────────────────────────────────────────────────────────


def repo_paths(repo: Path) -> list[str]:
    """Every file under `repo` detection may consider, repo-relative, skipping vendored trees."""
    out: list[str] = []
    root = repo.resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        depth = len(rel_dir.parts)
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIRS and depth < MAX_DEPTH)
        out.extend((rel_dir / f).as_posix() for f in filenames)
    return out


def _disk_reader(repo: Path) -> Callable[[str], str]:
    def read(rel: str) -> str:
        try:
            return (repo / rel).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""

    return read


def _matches(rel: str, pattern: str) -> bool:
    if "/" not in pattern:
        return fnmatch.fnmatchcase(PurePosixPath(rel).name, pattern)
    return fnmatch.fnmatchcase(rel, pattern) or fnmatch.fnmatchcase(rel, "*/" + pattern)


def _find(paths: Sequence[str], globs: Iterable[str], contains: str, read: Callable[[str], str]) -> str | None:
    """The shallowest path matching any of `globs` (and holding `contains`, when given)."""
    globs = tuple(globs)
    hits = sorted((p for p in paths if any(_matches(p, g) for g in globs)), key=lambda p: (p.count("/"), p))
    for hit in hits:
        if not contains or contains in read(hit):
            return hit
    return None


def _parent(rel: str) -> str:
    parent = PurePosixPath(rel).parent.as_posix()
    return parent or "."


def _choose(profile: Profile, paths: Sequence[str], read: Callable[[str], str]) -> tuple[bool, Choice]:
    """`(detected, choice)` for one profile: whether any rule matched, and where it lives."""
    root, found = ".", False
    for rule in profile.detect:
        hit = _find(paths, rule.files, rule.contains, read)
        if hit is not None:
            root, found = _parent(hit), True
            break
    if not profile.rooted:
        root = "."
    values: dict[str, str] = {}
    for var in profile.vars:
        value = var.default.replace("{root}", root)
        if var.find:
            hit = _find(paths, var.find, var.contains, read)
            if hit is not None:
                value = _parent(hit) if var.value == "dir" else hit
        values[var.name] = value
    return found, Choice(profile.id, root, values)


def detect(paths: Sequence[str], read: Callable[[str], str]) -> list[Choice]:
    """Every stack whose detection rules match `paths`, in id order. `read` returns a file's text."""
    out = []
    for profile in profiles().values():
        found, choice = _choose(profile, paths, read)
        if found:
            out.append(choice)
    return out


def resolve(ids: Iterable[str], paths: Sequence[str], read: Callable[[str], str]) -> list[Choice]:
    """The named stacks, located in `paths` where they exist (at the root where they do not).

    Raises `UnknownStackError` naming the known ids for an id no profile defines.
    """
    wanted = list(dict.fromkeys(i.strip() for i in ids if i.strip()))
    for sid in wanted:
        _profile_of(sid)
    return [_choose(profiles()[sid], paths, read)[1] for sid in profiles() if sid in wanted]


def detect_repo(repo: Path) -> list[Choice]:
    return detect(repo_paths(repo), _disk_reader(repo))


def resolve_repo(repo: Path, ids: Iterable[str]) -> list[Choice]:
    return resolve(ids, repo_paths(repo), _disk_reader(repo))


# ── rendering the target commands ────────────────────────────────────────────

_MAKE_VAR = re.compile(r"\$\(([A-Za-z_][A-Za-z0-9_]*)\)")


def _shell_line(line: str, profile: Profile, choice: Choice, params: Sequence[str], curdir: str) -> str:
    """One profile recipe line as a shell command: `{root}` and every `$(VAR)` resolved to the value
    the stack was detected with, a target's argument (`$(T)`) to its placeholder (`{T}`)."""
    values = {var.name: choice.vars.get(var.name, var.default.replace("{root}", choice.root)) for var in profile.vars}

    def var(m: re.Match[str]) -> str:
        name = m.group(1)
        if name in params:
            return "{" + name + "}"
        if name == "CURDIR":
            return curdir
        if name in values:
            return values[name]
        if name == profile.root_var:
            return choice.root
        return m.group(0)

    text = _MAKE_VAR.sub(var, line.replace("{root}", choice.root))
    exported = [v for v in profile.vars if v.export and re.search(rf"\b{re.escape(v.name)}\b", line)]
    for v in exported:
        default = values[v.name]
        text = f'export {v.name}="${{{v.name}:-{default}}}" && {_group(text)}'
    return text


def _group(command: str) -> str:
    """`command` as one unit of a larger one: in a subshell when it holds a shell operator."""
    return f"({command})" if re.search(r"&&|\|\||[;&|]", command) else command


def _stack_command(target: str, choice: Choice, params: Sequence[str], curdir: str) -> str:
    profile = profiles()[choice.id]
    lines = [_shell_line(line, profile, choice, params, curdir) for line in profile.recipes[target]]
    body = lines[0] if len(lines) == 1 else " && ".join(_group(line) for line in lines)
    if profile.deps:
        dep = _shell_line(profile.deps["target"], profile, choice, (), curdir)
        needs = [_shell_line(n, profile, choice, (), curdir) for n in profile.deps.get("needs", ())]
        fresh = " && ".join(f"[ {dep} -nt {need} ]" for need in needs) or f"[ -e {dep} ]"
        install = _shell_line(profile.deps["recipe"], profile, choice, (), curdir)
        body = f"({fresh} || ({install})) && {_group(body)}"
    return body


def target_commands(
    choices: Sequence[Choice],
    *,
    own: Mapping[str, str] | None = None,
    params: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, str]:
    """The shell command each conventional target runs for `choices`, for the `[fleet.targets]` table.

    `own` is what the repository already runs for a target (its own Makefile's `make lint`, a value
    it wrote): such a target is not rendered, and still counts toward a target built from it
    (`test` is the unit lane, then the database lane). `params` names each target's placeholders
    (`targets.TARGETS`), so a recipe's `$(T)` becomes `{T}`. Recipes run from the repository root,
    each stack's in its own subshell; a target several stacks declare runs them one after another,
    except a foreground loop (`dev`), whose recipes run at once.
    """
    own = dict(own or {})
    params = params or {}
    built_from, together = _compose()
    per: dict[str, list[str]] = {}
    for choice in choices:
        for target in profiles()[choice.id].targets:
            if target in own:
                continue
            per.setdefault(target, []).append(_stack_command(target, choice, tuple(params.get(target, ())), curdir="."))
    out: dict[str, str] = {}
    for target, commands in per.items():
        if len(commands) == 1:
            out[target] = commands[0]
        elif target in together:
            out[target] = " & ".join(_group(c) for c in commands) + " & wait"
        else:
            out[target] = " && ".join(_group(c) for c in commands)
    available = {**own, **out}
    for target, children in built_from.items():
        present = [available[c] for c in children if c in available]
        if present and target not in own:
            out[target] = " && ".join(_group(c) for c in present)
    return out


def quality_commands(choices: Sequence[Choice], *, curdir: str) -> dict[str, str]:
    """The release's supply-chain commands (`vuln`, `sbom`, `licenses`) for `choices`, each stack's
    in turn. Not conventional targets — no command names them; the CI template's release job runs
    them, with `curdir` (the checkout root as that runner spells it) for `$(CURDIR)`."""
    per: dict[str, list[str]] = {}
    for choice in choices:
        for target in profiles()[choice.id].quality:
            per.setdefault(target, []).append(_stack_command(target, choice, (), curdir))
    return {
        t: commands[0] if len(commands) == 1 else " && ".join(_group(c) for c in commands)
        for t, commands in per.items()
    }


# ── recognising a fleet.mk an earlier release rendered ──────────────────────


def _subst(text: str, profile: Profile) -> str:
    return text.replace("{root}", f"$({profile.root_var})")


def rendered_targets(choices: Sequence[Choice], defined_elsewhere: Iterable[str] = ()) -> list[str]:
    """The conventional targets `render_fleet_mk` writes for `choices`, in name order."""
    return sorted(_plan_targets(choices, frozenset(defined_elsewhere))[0])


def _plan_targets(
    choices: Sequence[Choice], elsewhere: frozenset[str]
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """`({target: per-stack sub-targets}, {target: conventional targets it is built from})`."""
    built_from, _together = _compose()
    subs: dict[str, list[str]] = {}
    for choice in choices:
        for target in profiles()[choice.id].recipes:
            if target not in elsewhere:
                subs.setdefault(target, []).append(f"{target}-{choice.id}")
    available = set(subs) | elsewhere
    built: dict[str, list[str]] = {}
    for target, children in built_from.items():
        present = [c for c in children if c in available]
        if present and target not in elsewhere:
            built[target] = present
            subs.setdefault(target, [])
    return subs, built


def render_fleet_mk(
    choices: Sequence[Choice],
    *,
    defined_elsewhere: Iterable[str] = (),
    meanings: Mapping[str, str] | None = None,
) -> str:
    """`fleet.mk` for `choices`, exactly as the releases before `[fleet.targets]` wrote it.

    Kept ONLY so the migration can tell a `fleet.mk` Fleet wrote from one a person edited
    (`setupfiles`); no release writes one any more. Targets in `defined_elsewhere` (an existing
    Makefile's) are left out; they still count as available to a target built from them."""
    elsewhere = frozenset(defined_elsewhere)
    subs, built = _plan_targets(choices, elsewhere)
    _built_from, together = _compose()
    meanings = {**(meanings or {}), **_quality_meanings()}
    by_id = {c.id: c for c in choices}
    ids = ", ".join(c.id for c in choices)

    out = [
        f"# fleet.mk — the conventional targets, rendered from the stack profiles: {ids}",
        "#",
        "# Fleet owns this file: `fleet commands sync` refreshes it from the stack profiles, and",
        "# reports an edit made here instead of overwriting it. To change a recipe, define the target",
        "# in your Makefile (it includes this file): a target the Makefile defines is left out of here.",
        "# Each conventional target is built from one sub-target per stack (`lint` runs `lint-<stack>`",
        "# for every stack), so a command calls one name whatever the stacks. Settings below are",
        "# defaults: override with `make X=value`.",
        "",
    ]
    for choice in choices:
        profile = profiles()[choice.id]
        if profile.rooted:
            out.append(f"{profile.root_var} ?= {choice.root}")
        for var in profile.vars:
            out.append(f"{var.name} ?= {choice.vars.get(var.name, var.default)}")
            if var.export:
                out.append(f"export {var.name}")
    order = list(meanings) + sorted(set(subs) - set(meanings))
    names = [t for t in order if t in subs]
    phony = [n for t in names for n in [t, *subs[t]]]
    out += ["", f".PHONY: {' '.join(phony)}", ""]

    for target in names:
        if target in meanings:
            out.append(f"# {meanings[target]}")
        children = built.get(target, []) + subs[target]
        if target in together and len(children) > 1:
            out += [
                f"{target}:",
                f"\t$(MAKE) -f $(firstword $(MAKEFILE_LIST)) -j{len(children)} {' '.join(children)}",
                "",
            ]
        else:
            out += [f"{target}: {' '.join(children)}".rstrip(), ""]
        for sub in subs[target]:
            profile = profiles()[sub[len(target) + 1 :]]
            prereq = f" {_subst(profile.deps['target'], profile)}" if profile.deps else ""
            out.append(f"{sub}:{prereq}")
            out += [f"\t{_subst(line, profile)}" for line in profile.recipes[target]]
            out.append("")

    for choice in choices:
        profile = profiles()[choice.id]
        if profile.deps and choice.id in by_id:
            needs = " ".join(_subst(n, profile) for n in profile.deps.get("needs", ()))
            out.append(f"# {profile.title}: install dependencies when the lockfile changes")
            out.append(f"{_subst(profile.deps['target'], profile)}: {needs}".rstrip())
            out.append(f"\t{_subst(profile.deps['recipe'], profile)}")
            out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


_FLEET_MK_HEADER = re.compile(r"^# fleet\.mk — the conventional targets, rendered from the stack profiles: (.+)$", re.M)
_SETTING = re.compile(r"^([A-Z][A-Z0-9_]*) \?= (.*)$", re.M)


def choices_from_fleet_mk(text: str) -> list[Choice]:
    """The stacks a `fleet.mk` was rendered for, read back from its own header and settings.

    What lets `fleet commands sync` refresh a `fleet.mk` that a release before the sync recorded
    its inputs wrote: the header names the stack ids, and each `?=` line carries the root and the
    settings the render resolved. `[]` when the header is missing or names a stack no profile
    defines — then the file is not one Fleet can re-render, and is left alone.
    """
    m = _FLEET_MK_HEADER.search(text)
    if m is None:
        return []
    ids = [i.strip() for i in m.group(1).split(",") if i.strip()]
    known = profiles()
    if not ids or any(i not in known for i in ids):
        return []
    settings = dict(_SETTING.findall(text))
    out: list[Choice] = []
    for sid in ids:
        profile = known[sid]
        root = settings.get(profile.root_var, ".") if profile.rooted else "."
        values = {v.name: settings.get(v.name, v.default.replace("{root}", root)) for v in profile.vars}
        out.append(Choice(sid, root, values))
    return out


_RUNS_ON = re.compile(r"^\s+runs-on: \[self-hosted(?:, ([^\]]+))?\]\s*$", re.M)


def runner_from_ci(text: str) -> str:
    """The runner label a rendered CI template runs on (`""` for the bare `[self-hosted]`)."""
    m = _RUNS_ON.search(text)
    return (m.group(1) or "").strip() if m else ""


# ── the worker toolchain ─────────────────────────────────────────────────────


def toolchain(ids: Iterable[str]) -> list[Tool]:
    """What the worker needs for the stacks `ids`: the union, each tool once, in profile order."""
    seen: dict[str, Tool] = {}
    for sid in ids:
        for tool in _profile_of(sid).toolchain:
            seen.setdefault(tool.tool, tool)
    return list(seen.values())


def install_lines(ids: Iterable[str]) -> list[str]:
    """Shell lines that install the toolchain for `ids` on an Ubuntu worker, as root via sudo."""
    tools = toolchain(ids)
    sources = list(dict.fromkeys(t.source for t in tools if t.source.startswith("ppa:")))
    apt = [t.install.removeprefix("apt:") for t in tools if t.install.startswith("apt:")]
    lines = [f"sudo add-apt-repository -y {s}" for s in sources]
    if apt:
        lines.append("sudo apt-get update && sudo apt-get install -y " + " ".join(apt))
    for t in tools:
        kind, _, arg = t.install.partition(":")
        if kind == "nodesource":
            lines.append(
                f"curl -fsSL https://deb.nodesource.com/setup_{arg}.x | sudo -E bash - "
                "&& sudo apt-get install -y nodejs"
            )
        elif kind == "binary":
            url = arg.replace("{arch}", "$(uname -m)")
            dest = f"/usr/local/bin/{t.tool}"
            lines.append(f"sudo curl -fsSL -o {dest} {url} && sudo chmod +x {dest}")
    return lines


def _tool_words(tool: Tool) -> str:
    words = tool.name + (f" {tool.version}" if tool.version else "")
    kind, _, arg = tool.install.partition(":")
    if kind == "apt" and arg == tool.name and not tool.source:
        return words
    how = {"apt": f"`{arg}`", "nodesource": f"NodeSource `setup_{arg}.x`", "binary": "release binary"}.get(kind, arg)
    if tool.source:
        how += f" from `{tool.source}`"
    return f"{words} ({how})"


def toolchain_table() -> str:
    """The Markdown table the Set up guide prints at step 5: per stack, what the worker needs."""
    rows = [
        "| Stack | Detected from | The worker needs |",
        "|---|---|---|",
    ]
    for profile in profiles().values():
        detected = ", ".join(
            f"`{g}`" + (f" containing `{r.contains}`" if r.contains else "") for r in profile.detect for g in r.files
        )
        needs = ", ".join(_tool_words(t) for t in profile.toolchain)
        rows.append(f"| `{profile.id}` | {detected} | {needs} |")
    return "\n".join(rows) + "\n"


# ── the CI workflow template ─────────────────────────────────────────────────

#: Where `fleet init` writes the template and its instructions. Never `.github/workflows/`: the
#: fleet's token deliberately cannot write workflows, so a person commits it with their identity.
CI_DIR = ".fleet/ci"
CI_WORKFLOW = f"{CI_DIR}/fleet-ci.yml"
CI_README = f"{CI_DIR}/README.md"
CI_TARGET = ".github/workflows/fleet-ci.yml"
#: The opt-in drift check in the template: a job that is skipped unless the repository variable
#: is `true`, so a template copied as it is never adds a check nobody asked for.
DRIFT_JOB = "fleet-drift"
DRIFT_VARIABLE = "FLEET_DRIFT_CHECK"
DRIFT_COMMAND = "python3 knowledge/scripts/fleet.py commands sync --check --repo ."


@cache
def _actions() -> dict[str, dict[str, str]]:
    data = tomllib.loads((DATA_DIR / "_actions.toml").read_text(encoding="utf-8"))
    return {name: dict(pin) for name, pin in data.get("actions", {}).items()}


def _uses(action: str) -> str:
    pin = _actions()[action]
    return f"{action}@{pin['sha']} # {pin['version']}"


def _yaml_scalar(value: Any) -> str:
    return json.dumps(value) if isinstance(value, str) else str(value).lower()


def _step(action: str, with_: Mapping[str, Any], root: str) -> list[str]:
    lines = [f"      - uses: {_uses(action)}"]
    if with_:
        lines.append("        with:")
        for key, value in with_.items():
            if isinstance(value, str):
                value = value.replace("{root}", root)
            lines.append(f"          {key}: {_yaml_scalar(value)}")
    return lines


#: How the CI template spells the checkout root, for a release recipe's `$(CURDIR)`.
CI_CURDIR = "${{ github.workspace }}"


def render_ci(
    choices: Sequence[Choice],
    *,
    runner_label: str = "",
    commands: Mapping[str, str] | None = None,
    runs_on: str = "",
    default_branch: str = "main",
) -> str:
    """The GitHub Actions workflow for `choices`, as text a person commits themselves.

    Every job runs on the self-hosted runner (`[self-hosted, <runner_label>]`) — or on `runs_on`
    verbatim when it is given (`ubuntu-latest` for GitHub's hosted runners), checks out with
    SHA-pinned actions, installs what the profiles' `[[ci.setup]]` name, and then runs the
    repository's own target commands — `commands`, its `[fleet.targets]` table — so CI runs
    exactly what the agents run before they push (default: what the profiles render). The
    release job's supply-chain steps come from the profiles (`quality_commands`).
    """
    data = tomllib.loads((DATA_DIR / "_compose.toml").read_text(encoding="utf-8"))["ci"]
    runs = dict(commands) if commands is not None else target_commands(choices)
    runs.update(quality_commands(choices, curdir=CI_CURDIR))
    have = set(runs)
    runs_on = runs_on.strip() or "[self-hosted" + (f", {runner_label}" if runner_label else "") + "]"
    setup: list[str] = []
    for choice in choices:
        for step in profiles()[choice.id].ci_setup:
            setup += _step(step["uses"], step.get("with", {}), choice.root)
    checkout = _step("actions/checkout", {"persist-credentials": False}, ".")

    out = [
        f"# fleet-ci.yml — CI rendered by Fleet from the stack profiles: {', '.join(c.id for c in choices)}",
        "#",
        "# Fleet does not install this file: its token deliberately cannot write workflows. Commit it",
        f"# yourself as {CI_TARGET} — {CI_README} says how. Every build step is a command from",
        "# [fleet.targets] in .fleet/fleet.toml, so CI runs exactly what the agents run before they",
        "# push. `fleet commands sync` keeps this template current; your committed copy is yours to change.",
        "name: ci",
        "",
        "on:",
        "  pull_request:",
        "  push:",
        f"    branches: [{default_branch or 'main'}]",
        '    tags: ["v*"]',
        "",
        "permissions:",
        "  contents: read",
        "",
        "concurrency:",
        "  group: ci-${{ github.ref }}",
        "  cancel-in-progress: true",
        "",
        "jobs:",
    ]
    names: list[str] = []
    for job, targets in data["jobs"].items():
        present = [t for t in targets if t in have]
        if not present:
            continue
        names.append(job)
        out += [f"  {job}:"]
        if job == data["release_job"]:
            out += ["    if: startsWith(github.ref, 'refs/tags/v')"]
        out += [f"    runs-on: {runs_on}", "    timeout-minutes: 45", "    steps:", *checkout, *setup]
        for t in present:
            out += [f"      - name: {t}", f"        run: {json.dumps(runs[t], ensure_ascii=False)}"]
        if job == data["release_job"]:
            out += [
                f"      - uses: {_uses('actions/upload-artifact')}",
                "        with:",
                "          name: release-evidence",
                f"          path: {data['artifacts']}",
            ]
        out.append("")
    names.append(DRIFT_JOB)
    out += [
        "  # OPTIONAL, AND OFF UNTIL YOU TURN IT ON. Fails when the files Fleet manages here — the",
        "  # commands and documents under .fleet/, knowledge/scripts/, and Fleet's part of CLAUDE.md",
        "  # and .fleet/fleet.toml — differ from what the Fleet release this repository was last",
        "  # synced with writes; `fleet commands sync` fixes it. To turn it on, add the repository",
        f"  # variable {DRIFT_VARIABLE} = true (Settings > Secrets and variables > Actions > Variables).",
        "  # The runner needs `fleet-knowledge` importable at that release (a fleet worker has it).",
        f"  {DRIFT_JOB}:",
        f"    if: vars.{DRIFT_VARIABLE} == 'true'",
        f"    runs-on: {runs_on}",
        "    timeout-minutes: 10",
        "    steps:",
        *checkout,
        f"      - run: {DRIFT_COMMAND}",
        "",
    ]
    out += [
        "  # The required check. It fails unless every job above succeeded or was skipped, so a",
        "  # ruleset requiring `ci` holds every job without naming each one.",
        "  ci:",
        f"    needs: [{', '.join(names)}]",
        "    if: always()",
        f"    runs-on: {runs_on}",
        "    steps:",
        "      - name: every job succeeded",
        "        if: contains(needs.*.result, 'failure') || contains(needs.*.result, 'cancelled')",
        "        run: exit 1",
    ]
    return "\n".join(out) + "\n"


def render_ci_readme(choices: Sequence[Choice]) -> str:
    """The instructions beside the template: how to commit it, and what the runner needs."""
    ids = [c.id for c in choices]
    install = "\n".join(install_lines(ids))
    dotnet_tools = (
        "\nThe .NET release steps (the SBOM and the licence report) use local tools: list `CycloneDX` and\n"
        "`nuget-license` in `.config/dotnet-tools.json` (`dotnet new tool-manifest`, then\n"
        "`dotnet tool install CycloneDX` and `dotnet tool install nuget-license`) and commit it.\n"
        if "dotnet" in ids
        else ""
    )
    return f"""# CI for this repository

`fleet-ci.yml` beside this file is a GitHub Actions workflow rendered from the stacks this
repository builds in ({", ".join(ids)}). `fleet commands sync` keeps it current. Fleet never
writes `.github/workflows/`: its token is deliberately denied that permission, because a token
that can rewrite CI can switch off every check. So a person adds it, once:

1. Copy it into place and commit it with your own identity:

   ```bash
   mkdir -p .github/workflows
   cp {CI_WORKFLOW} {CI_TARGET}
   git add {CI_TARGET} && git commit -m "ci: add the fleet CI workflow"
   ```

2. It runs on a self-hosted runner (`runs-on: [self-hosted, <label>]`). Register a runner with
   that label for this repository, and install on it what the stacks need:

   ```bash
{chr(10).join("   " + line for line in install.splitlines())}
   ```
{dotnet_tools}
3. Optional: the `fleet-drift` job checks that the files Fleet manages here still match the
   Fleet release this repository was synced with. It is off until you add the repository
   variable `FLEET_DRIFT_CHECK` with the value `true` (Settings > Secrets and variables >
   Actions > Variables).

4. Once it has run green, require the `ci` check on the default branch (a ruleset or branch
   protection). `ci` is the last job and fails unless every other job succeeded.

Every build step is the command `[fleet.targets]` in `.fleet/fleet.toml` names for a target
(`lint`, `typecheck`, `test-unit`, `test-db`, `build`, `test-e2e`), so CI runs what the agents
run; change a command there and the next `fleet commands sync` updates this template. On a `v*`
tag the `release` job adds the vulnerability scan, the CycloneDX SBOM and the licence report,
uploaded as the `release-evidence` artifact. Every action is pinned by commit SHA; update a pin by
changing the SHA and its version comment together.
"""


# ── the language contracts ───────────────────────────────────────────────────


def contract_path(sid: str) -> str:
    """Where a profile's language contract lands in a repository (what `languages` points at)."""
    return f"knowledge/specs/languages/{sid}.md"


def contract_text(sid: str) -> str | None:
    """The language contract a profile ships, or `None` when it ships none."""
    profile = _profile_of(sid)
    if not profile.contract:
        return None
    return (DATA_DIR / profile.contract).read_text(encoding="utf-8")


def languages_answer(choices: Sequence[Choice]) -> str:
    """The `languages` slot's answer document for the stacks that ship a contract."""
    lanes = [profiles()[c.id] for c in choices if profiles()[c.id].contract]
    lines = [
        "# languages",
        "",
        "Which language contracts apply here, and therefore which implementation lanes run.",
        "Written by `fleet init` from the stack profiles; edit the contracts to fit this repository.",
        "",
        "## Answers",
        "",
        "- **lanes** — " + ", ".join(f"{p.title} (`{p.id}`)" for p in lanes),
        "- **contracts** — " + " · ".join(f"{p.title}: {contract_path(p.id)}" for p in lanes),
    ]
    return "\n".join(lines) + "\n"
