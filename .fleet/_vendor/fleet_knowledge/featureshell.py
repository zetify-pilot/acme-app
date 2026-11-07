"""Find the feature maps of a corpus whether or not their rendered `<area>.md` exists.

A consumer whose capability tables are fragment-backed keeps the rendered map out of git: only the shell,
`<area>.md.tmpl` (frontmatter, prose and a `<!-- rows: -->` marker above each table header), is committed, and
its capability rows are `rows/<ID>.json` fragments. A reader that globs `*.md` alone, on a checkout nobody
rendered (the fleet service syncing a corpus, an audit, an agent), sees no such area: it is missing from the
vocabulary and every PRD that declares it resolves to nothing.

This is the one discovery rule every map reader shares, so they cannot disagree about which areas exist. The
shell carries everything but the rows (frontmatter, Intent, surfaces), and `corpus.features` already reads the
rows from the fragments, so a reader needs only the shell's path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

__all__ = ["SHELL_SUFFIX", "area_file", "area_stem", "map_files"]

SHELL_SUFFIX: Final = ".md.tmpl"


def map_files(features: Path) -> list[Path]:
    """Every map file in a features directory, sorted by area stem.

    The union of `<stem>.md` and `<stem>.md.tmpl`; when both exist the rendered `.md` wins, being the shell plus
    the generated rows. `README.md` and `_`-prefixed drafts are left to the caller, as they always were."""
    if not features.is_dir():
        return []
    found: dict[str, Path] = {p.stem: p for p in features.glob("*.md")}
    for p in features.glob(f"*{SHELL_SUFFIX}"):
        found.setdefault(p.name[: -len(SHELL_SUFFIX)], p)
    return [found[stem] for stem in sorted(found)]


def area_stem(path: Path) -> str:
    """The file stem of a map: `foo` for `foo.md` and for its shell `foo.md.tmpl`."""
    name = path.name
    return name[: -len(SHELL_SUFFIX)] if name.endswith(SHELL_SUFFIX) else path.stem


def area_file(features: Path, stem: str) -> Path:
    """The file one area is read from: its rendered `<stem>.md`, else its committed shell `<stem>.md.tmpl`."""
    rendered = features / f"{stem}.md"
    return rendered if rendered.is_file() else features / f"{stem}{SHELL_SUFFIX}"
