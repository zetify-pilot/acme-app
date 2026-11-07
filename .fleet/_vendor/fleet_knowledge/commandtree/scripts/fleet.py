#!/usr/bin/env python3
"""The `fleet` CLI, reachable from any checkout the tier ships to.

    python3 knowledge/scripts/fleet.py check --only bars --repo .
    python3 knowledge/scripts/fleet.py digest -k knowledge slices
    python3 knowledge/scripts/fleet.py slots --repo .

`fleet` is the CLI of the `fleet_knowledge` package. Installed, it is on PATH; in a
repository that carries the package as a submodule it is not, and a command that says
`fleet check` there runs nothing. This shim is the one spelling that works in both: it makes
the package importable the way every other shipped script does (`_repo.fleet_knowledge()`,
which refuses with the repair command when the package is absent) and hands argv to the CLI
unchanged. No option is interpreted here — `--help` is the CLI's own.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    _repo.fleet_knowledge()
    from fleet_knowledge.cli import main as cli  # noqa: PLC0415 — after the path insert

    return int(cli(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    raise SystemExit(main())
