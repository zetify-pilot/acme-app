"""Which Fleet release this package is (ENG-18630).

The distribution's own version is a placeholder (`0.1.0` in `pyproject.toml`) that has read the
same on every release: the release PR moves the chart's version and nothing else, by design (the
repository's "a feature PR never touches the version" rule). A sync manifest that recorded that
placeholder would tell every repository it is up to date forever, so the release is resolved from
what the build actually is:

1. **The chart beside the package**, in a source tree (a clone, or the `fleet/` submodule a
   repository pins). `deploy/charts/fleet/Chart.yaml`'s `version` is the release this tree was
   cut as, or the last one cut before it. It wins over the variable below, because a process that
   inherited another build's `FLEET_RELEASE` while running this checkout's code is this checkout.
2. **`FLEET_RELEASE`**, which the published image sets to its tag (`packages/fleet-service/
   Dockerfile`). An image carries no chart.
3. **`""` — unknown.** Never a guessed number: an unknown version is offered the update, a wrong
   one is told it is current.

The answer is bare SemVer (`0.7.299`), the chart's spelling; the tag's leading `v` is dropped.
Stdlib only, like the rest of the package.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path

__all__ = ["RELEASE_ENV", "normalize", "version"]

#: The variable the published image sets to its release tag.
RELEASE_ENV = "FLEET_RELEASE"

#: `<repo>/deploy/charts/fleet/Chart.yaml`, from `<repo>/packages/fleet-knowledge/src/fleet_knowledge/`.
_CHART = Path(__file__).resolve().parents[4] / "deploy" / "charts" / "fleet" / "Chart.yaml"

_NAME = re.compile(r"^name:\s*\"?fleet\"?\s*$", re.MULTILINE)
_VERSION = re.compile(r"^version:\s*\"?v?([0-9][^\"\s]*)\"?\s*$", re.MULTILINE)


def normalize(text: str) -> str:
    """A release as the chart spells it: `v0.7.299` and `0.7.299` both read `0.7.299`."""
    return text.strip().removeprefix("v")


def version(*, chart: Path | None = None, env: Mapping[str, str] | None = None) -> str:
    """This package's Fleet release, or `""` when nothing says which it is.

    `chart` and `env` exist for tests; a caller passes neither.
    """
    path = _CHART if chart is None else chart
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    if _NAME.search(text):
        found = _VERSION.search(text)
        if found:
            return found.group(1)
    values = os.environ if env is None else env
    return normalize(values.get(RELEASE_ENV, ""))
