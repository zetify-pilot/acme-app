"""Finding a knowledge base, and naming the files inside one.

Every reader in this package takes a `root` — the `knowledge/` directory itself, never a
repository root and never a checkout path. That is the whole of the package's coupling to
a repository: point it at a directory that has the shape `README.md` describes and it
works, whether that directory sits in this repo, a customer's, or a scratch fixture tree.

`find_root()` is the only place a *search* happens, and it walks upward from a starting
directory exactly the way `git` finds `.git` — so a CLI invoked anywhere inside a checkout
resolves the same base a CLI invoked at the top does.
"""

from __future__ import annotations

from pathlib import Path

# The conventional directory name. Overridable everywhere it is used: a project that calls
# its corpus something else is a naming choice, not a different shape.
DEFAULT_DIR_NAME = "knowledge"


class KnowledgeRootNotFoundError(RuntimeError):
    """No `knowledge/` directory at or above the starting point."""


def find_root(start: Path | None = None, *, dir_name: str = DEFAULT_DIR_NAME) -> Path:
    """The nearest knowledge base at or above `start` (default: the process's cwd).

    Returns the corpus directory itself. `start` may BE the corpus directory, which is what
    lets `--root knowledge` and `--root .` both work without the caller knowing which it
    handed over.
    """
    base = (start or Path.cwd()).resolve()
    if base.is_dir() and base.name == dir_name:
        return base
    for candidate in (base, *base.parents):
        found = candidate / dir_name
        if found.is_dir():
            return found
    raise KnowledgeRootNotFoundError(
        f"no `{dir_name}/` directory at or above {base} — pass --root, or run from inside a checkout"
    )


def resolve_root(root: Path | None = None, *, dir_name: str = DEFAULT_DIR_NAME) -> Path:
    """`root` when one was given, else discovery. The one call every entry point makes."""
    if root is None:
        return find_root(dir_name=dir_name)
    return find_root(Path(root), dir_name=dir_name)


def repo_root(root: Path) -> Path:
    """The directory the corpus sits in.

    Used for exactly two things — resolving citations across a whole project (the todo
    register scans them) and rendering a path a human can paste. Nothing in this package
    reads code, config or history out of it.
    """
    return root.parent


def rel(path: Path, base: Path) -> str:
    """`path` relative to `base`, or its absolute form when it sits outside.

    A generator's messages have to name a file the reader can find, and a corpus mounted
    somewhere unexpected must not turn that into a `ValueError`.
    """
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)
