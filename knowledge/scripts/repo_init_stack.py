#!/usr/bin/env python3
"""What Fleet's stack profiles say for a new repository's first code — read by `repo:init`.

    python3 knowledge/scripts/repo_init_stack.py list
    python3 knowledge/scripts/repo_init_stack.py recipes --stack dotnet,node-vue
    python3 knowledge/scripts/repo_init_stack.py ci --stack dotnet,node-vue --runs-on ubuntu-latest
    python3 knowledge/scripts/repo_init_stack.py ci --stack dotnet --runner-label build-linux

`list` prints every stack profile Fleet ships, one `<id>\t<title>` per line. `recipes` prints, as
JSON, the command each conventional target runs for the named stacks (`targets`), each stack
located in this checkout where its files already are (so write the project files first), the tools a
machine needs for them (`toolchain`) and their install lines on Ubuntu (`install`). The Makefile
`repo:init` writes runs exactly these commands, so a new repository builds the way Fleet's tested
profiles build.

`ci` prints the GitHub Actions workflow for the named stacks. Every build step runs the Makefile
target of the same name (`make lint`, `make test-unit`, `make build`), so CI runs exactly what a
person and an agent run. `--runs-on` is used verbatim (`ubuntu-latest`, GitHub's hosted runners);
`--runner-label` runs on `[self-hosted, <label>]`, a runner the organisation hosts itself.

The profiles are not a closed list. A stack none of them describes is still built: `repo:init`
writes its commands itself, and this script answers exit `3` naming the profiles it has.

Exit codes: 0 printed; 2 the invocation is wrong; 3 a named stack has no profile.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

#: The conventional targets the Makefile `repo:init` writes, and so the ones CI runs.
MAKE_TARGETS = ("lint", "test-unit", "test", "build", "dev")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("list", help="every stack profile Fleet ships")
    p_recipes = sub.add_parser("recipes", help="the target commands, toolchain and install lines")
    p_recipes.add_argument("--stack", required=True, help="profile ids, comma-separated")
    p_ci = sub.add_parser("ci", help="the GitHub Actions workflow")
    p_ci.add_argument("--stack", required=True, help="profile ids, comma-separated")
    where = p_ci.add_mutually_exclusive_group(required=True)
    where.add_argument("--runs-on", default="", help="the runs-on value, verbatim (e.g. ubuntu-latest)")
    where.add_argument("--runner-label", default="", help="a self-hosted runner's label")
    p_ci.add_argument("--default-branch", default="main", help="the branch a push to runs CI on (default: main)")
    args = parser.parse_args(argv)

    _repo.fleet_knowledge()
    from fleet_knowledge import stacks  # noqa: PLC0415 - after the path insert

    if args.mode == "list":
        for sid, profile in stacks.profiles().items():
            print(f"{sid}\t{profile.title}")
        return 0
    try:
        choices = stacks.resolve_repo(_repo.repo_root(), [i.strip() for i in args.stack.split(",")])
    except stacks.UnknownStackError as exc:
        print(f"repo_init_stack: {exc}", file=sys.stderr)
        return 3
    if not choices:
        print("repo_init_stack: --stack names no stack", file=sys.stderr)
        return 2
    ids = [c.id for c in choices]
    if args.mode == "recipes":
        doc = {
            "stacks": ids,
            "targets": stacks.target_commands(choices),
            "toolchain": [{"tool": t.tool, "name": t.name, "version": t.version} for t in stacks.toolchain(ids)],
            "install": stacks.install_lines(ids),
        }
        print(json.dumps(doc, indent=2, ensure_ascii=False))
        return 0
    have = set(stacks.target_commands(choices))
    commands = {t: f"make {t}" for t in MAKE_TARGETS if t in have or t == "test"}
    print(
        stacks.render_ci(
            choices,
            runner_label=args.runner_label,
            commands=commands,
            runs_on=args.runs_on,
            default_branch=args.default_branch,
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
