#!/usr/bin/env python3
"""Where a knowledge bootstrap starts from — the repository's default branch, as it is now.

    python3 knowledge/scripts/kb_base.py            # the ref to cut from, or a refusal
    python3 knowledge/scripts/kb_base.py --json     # the same reading as JSON

The documented setup order is `fleet init`, then the knowledge bootstrap command. `fleet init`
opens a pull request. If the bootstrap starts before that pull request merges, it builds on a
tree without `fleet init`'s files, and when the init pull request squash-merges the bootstrap
pull request conflicts. So the bootstrap starts from the default branch as it is now, and it
refuses to start while the init files exist only on an unmerged branch.

The script fetches `origin`, reads the default branch from the remote (never assumes `main`),
and checks that the files `fleet init` adds are committed on it.

Exit codes:
    0  the default branch carries the init files, and this checkout contains it
    2  the check could not run (not a git checkout, no readable default branch, git failed)
    3  `fleet init` has not merged — refuse to start
    4  the init files are on the default branch, but this branch is behind it — rebase first
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

#: The shipped inventory tool `fleet init` puts in the repository and the bootstrap runs.
INIT_SCRIPT = "knowledge/scripts/kb_inventory.py"
#: Fleet's configuration file, in the layout `fleet init` writes and the legacy root layout.
INIT_CONFIGS = (".fleet/fleet.toml", "fleet.toml")
#: The sentence the issue requires when the init pull request has not merged.
REFUSE = "merge the `fleet init` pull request first"


class CheckError(Exception):
    """The check could not run at all (exit 2)."""


@dataclass
class Reading:
    """What the bootstrap may start from."""

    base: str = ""
    ref: str = ""
    remote: bool = False
    missing: list[str] = field(default_factory=list)
    behind: bool = False

    @property
    def exit_code(self) -> int:
        if not self.remote:
            return 0
        if self.missing:
            return 3
        return 4 if self.behind else 0


def _git(root: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    if check and cp.returncode != 0:
        raise CheckError(f"git {' '.join(args)} failed: {cp.stderr.strip() or cp.stdout.strip()}")
    return cp


def repo_root(start: Path) -> Path:
    cp = _git(start, "rev-parse", "--show-toplevel")
    if cp.returncode != 0:
        raise CheckError(f"not a git checkout: {start}")
    return Path(cp.stdout.strip())


def has_origin(root: Path) -> bool:
    return "origin" in _git(root, "remote").stdout.split()


def default_branch(root: Path) -> str:
    """The remote's default branch: its own `origin/HEAD`, then `git remote show`, then a guess."""
    cp = _git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if cp.returncode == 0 and cp.stdout.strip():
        ref = cp.stdout.strip()
        return ref.split("/", 1)[1] if ref.startswith("origin/") else ref
    cp = _git(root, "remote", "show", "origin")
    match = re.search(r"HEAD branch:\s*(\S+)", cp.stdout)
    if match:
        return match.group(1)
    for name in ("main", "master"):
        if _git(root, "rev-parse", "--verify", f"refs/remotes/origin/{name}").returncode == 0:
            return name
    return ""


def _exists(root: Path, ref: str, path: str) -> bool:
    return _git(root, "cat-file", "-e", f"{ref}:{path}").returncode == 0


def read(start: Path) -> Reading:
    root = repo_root(start)
    if not has_origin(root):
        return Reading()
    _git(root, "fetch", "--quiet", "origin", check=True)
    base = default_branch(root)
    if not base:
        raise CheckError("could not read the default branch of `origin`")
    ref = f"origin/{base}"
    missing: list[str] = []
    if not any(_exists(root, ref, path) for path in INIT_CONFIGS):
        missing.append(" or ".join(INIT_CONFIGS))
    if not _exists(root, ref, INIT_SCRIPT):
        missing.append(INIT_SCRIPT)
    behind = False
    if _git(root, "rev-parse", "--verify", f"{ref}^{{commit}}").returncode == 0:
        behind = _git(root, "merge-base", "--is-ancestor", ref, "HEAD").returncode != 0
    return Reading(base=base, ref=ref, remote=True, missing=missing, behind=behind)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--json", action="store_true", help="print the reading as JSON")
    args = ap.parse_args(argv)

    try:
        reading = read(Path.cwd())
    except CheckError as exc:
        print(f"kb_base: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(asdict(reading), sort_keys=True))
    elif not reading.remote:
        print("no origin")
    else:
        print(reading.ref)

    if reading.missing:
        print(f"{REFUSE}: {reading.ref} does not carry {'; '.join(reading.missing)}.", file=sys.stderr)
        print("The knowledge bootstrap needs the files that pull request adds.", file=sys.stderr)
    elif reading.behind:
        print(
            f"this branch is behind {reading.ref}; rebase onto it before you open or update the pull request.",
            file=sys.stderr,
        )
    return reading.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
