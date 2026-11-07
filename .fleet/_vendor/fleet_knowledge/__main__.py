"""`python -m fleet_knowledge` — the same front door as the `fleet` console script.

Present so the tool is reachable from a checkout with nothing installed, which is the state a
knowledge validator most often runs in.
"""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
