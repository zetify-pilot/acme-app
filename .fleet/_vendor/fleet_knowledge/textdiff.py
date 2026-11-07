"""A size-capped unified diff of one file, for a report a person reads before anything is written.

The repository-update report names files a person changed by hand, and a bare name asks them to go
and find out what the update would undo. A diff answers it on the spot, but a regenerated document
can differ in hundreds of lines and a report carries many files, so each diff is capped and says so
when it is cut. Binary content (anything with a NUL byte — which includes the stand-in a hosted
plan writes for a file it never downloaded) gets no diff at all rather than a misleading one.

Stdlib only.
"""

from __future__ import annotations

import difflib

__all__ = ["MAX_DIFF_BYTES", "MAX_DIFF_FILES", "unified_diff"]

#: The most one file's diff may carry, in UTF-8 bytes, before it is cut at a line boundary.
MAX_DIFF_BYTES = 16_000
#: The most files one report carries a diff for; the rest are named without one.
MAX_DIFF_FILES = 20

_TRUNCATED = "@@ diff cut here: it is longer than the report carries @@\n"


def unified_diff(
    path: str, old: bytes | None, new: bytes | None, *, cap: int = MAX_DIFF_BYTES
) -> tuple[str | None, bool]:
    """`(diff, truncated)` turning `old` into `new` for `path`; `None` for no file on that side.

    The diff is `None` when either side is binary or the two are equal. `truncated` is true when
    the diff was cut to `cap` bytes.
    """
    if old == new or (old is not None and b"\0" in old) or (new is not None and b"\0" in new):
        return None, False
    a = (old or b"").decode("utf-8", "replace").splitlines(keepends=True)
    b = (new or b"").decode("utf-8", "replace").splitlines(keepends=True)
    lines = difflib.unified_diff(
        a,
        b,
        fromfile=f"a/{path}" if old is not None else "/dev/null",
        tofile=f"b/{path}" if new is not None else "/dev/null",
    )
    out: list[str] = []
    size = 0
    for line in lines:
        if not line.endswith("\n"):
            line += "\n\\ No newline at end of file\n"
        size += len(line.encode("utf-8"))
        if size > cap:
            out.append(_TRUNCATED)
            return "".join(out), True
        out.append(line)
    return ("".join(out) or None), False
