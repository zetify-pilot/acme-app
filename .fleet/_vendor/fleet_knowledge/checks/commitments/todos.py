"""Validate the todo register and every citation of it.

The register holds things we noticed and have not settled — not decisions (those are
requirement-register rows) and not dispatchable work (those are tracker issues), but the
questions and doubts raised in passing that otherwise die with the session.

**Why a register rather than markers in prose.** The first design put a marker at the
sentence that raised each todo. It was rejected on evidence collected the same day: a
sweep found sixteen distinct ad-hoc phrasings of "open question" across the tree, which is
precisely the demonstration that a syntax convention fails where todos get written —
mid-sentence, while thinking about something else. A file you can open is complete by
construction; a convention is only as complete as its least careful author. The register
also represents a todo attached to no sentence at all, which a marker cannot.

What this enforces:

  * ids are unique, and the `Next id:` counter is correct — the append-only rule is what
    makes an id permanent and therefore safe to cite. **Append-only is enforced on its own
    terms**: the ids must be a contiguous run from `TODO-001` with no gap, so deleting a
    non-highest row (or jumping an id ahead) is a commit failure, not just a stale counter;
  * `Status` is on-enum; `filed` actually names a well-formed issue; `done`/`dropped` say
    how it was settled or why it was dropped; `Raised` is a real date;
  * every `**[TODO-NNN]**` citation anywhere in the tree resolves to a real row. A
    citation stands in for the todo, so a pointer to nothing is worse than no pointer:
    it reads as tracked when it is not.

**What a todo row IS belongs to `fleet_knowledge.todos`** — its row form, its citation form,
its status vocabulary, and the rule that a row which fails to parse is a hard error rather
than a silent skip. That reader is what the knowledge browser reads the same rows through;
a second definition here would make the browser a second source of truth for the open list.
This module is the JUDGEMENT over those rows and nothing else.

Ported from `scripts/validate_todos.py` unchanged.

Stdlib only, like every sibling check.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

from ... import todos as kktodos
from .context import Context

# The register's shape, bound rather than restated — see the module docstring.
STATUSES = kktodos.STATUSES
ROW_RE = kktodos.ROW_RE
NEXT_RE = kktodos.NEXT_RE
CITE_RE = kktodos.CITE_RE
TodoParseError = kktodos.TodoParseError
# The id namespace the reader's row form matches (`ROW_RE` is `TODO-\d+`). Named here so
# the messages below read the same way on an empty register as on a full one.
PREFIX = "TODO"

# A real YYYY-MM-DD date. `x` (the cheapest-green stand-in) and `1999-99-99` both fail.
DATE_RE = re.compile(r"^(?P<y>\d{4})-(?P<m>0[1-9]|1[0-2])-(?P<d>0[1-9]|[12]\d|3[01])$")


def issue_re(ctx: Context) -> re.Pattern[str]:
    """A well-formed issue key: project prefix + a number worth trusting."""
    return re.compile(ctx.cfg.issue_key_pattern)


def rows(ctx: Context) -> list[dict[str, Any]]:
    """Every todo row, in register order. Raises `TodoParseError` on a malformed row."""
    return kktodos.read(ctx.todo_register_path)


def citations(ctx: Context) -> dict[str, list[str]]:
    """Every `**[TODO-NNN]**` in the tree -> where it appears.

    Scans every tracked file (which honours gitignore by construction — see TODO-018), not
    just the prose roots: `**[TODO-NNN]**` is the register's own markdown-bold syntax,
    distinct from code's `// TODO`, so a dangling citation cannot be hidden by putting it
    somewhere the scan does not look.
    """
    return kktodos.citations(ctx.root, ctx.todo_register_path)


def validate(ctx: Context, rs: list[dict[str, Any]], cites: dict[str, list[str]]) -> list[str]:
    register = ctx.todo_register_path
    name = register.name
    ire = issue_re(ctx)
    errs: list[str] = []
    if not register.exists():
        return [f"{ctx.rel(register)} is missing"]

    nums: list[int] = []
    seen: dict[int, str] = {}
    prefix = PREFIX
    for r in rs:
        n = int(r["id"].split("-")[1])
        nums.append(n)
        where = f"{name}:{r['line']}"
        if n in seen:
            errs.append(f"{where}: duplicate id `{r['id']}` (also `{seen[n]}`) — ids are permanent and never reused")
        seen[n] = r["id"]
        if r["status"] not in STATUSES:
            errs.append(f"{where}: `{r['id']}` status `{r['status']}` is not one of {', '.join(sorted(STATUSES))}")
        if r["status"] == "filed" and not ire.search(r["refs"]):
            errs.append(
                f"{where}: `{r['id']}` is `filed` but `Refs` names no well-formed issue (e.g. ENG-6025) — "
                "'filed' without a real key is where work goes to disappear"
            )
        if r["status"] in ("done", "dropped") and not r["refs"]:
            errs.append(
                f"{where}: `{r['id']}` is `{r['status']}` but `Refs / Notes` is empty — "
                "say how it was settled, or why it was deliberately not done"
            )
        if len(r["todo"]) < ctx.cfg.todo_min_statement_len:
            errs.append(f"{where}: `{r['id']}` is too vague to act on — say what is unsettled, not the topic")
        if not DATE_RE.match(r["raised"]):
            errs.append(
                f"{where}: `{r['id']}` `Raised` is `{r['raised']}`, not a real YYYY-MM-DD date — "
                "age is only readable if the date is"
            )

    # Append-only on its own terms: ids must be a contiguous run from TODO-001 with no gap.
    # This is what makes deleting a middle row (or jumping an id ahead) a failure even when
    # the `Next id:` counter is left consistent with the rows that remain.
    uniq = sorted(set(nums))
    if uniq:
        expected = set(range(1, len(uniq) + 1))
        actual = set(uniq)
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            errs.append(
                f"{name}: append-only violated — rows deleted, leaving id gap(s): "
                + ", ".join(f"{prefix}-{n:03d}" for n in missing)
            )
        if extra:
            errs.append(
                f"{name}: id(s) out of sequence (gap or jump, e.g. a reused or skipped id): "
                + ", ".join(f"{prefix}-{n:03d}" for n in extra)
            )
    else:
        # A register with no rows passes nothing on its own merits — it must fail even when
        # no citation happens to dangle, or a wiped register reads as green.
        errs.append(f"{name}: the register has no rows — an empty register hides open questions")

    text = register.read_text(encoding="utf-8")
    m = NEXT_RE.search(text)
    if not m:
        errs.append(
            f"{name}: the `{ctx.cfg.append_only_marker}` marker is missing — it is what keeps ids from being reused"
        )
    elif uniq:
        highest = max(nums)
        if int(m.group(1)) != highest + 1:
            errs.append(
                f"{name}: `Next id: {prefix}-{m.group(1)}` but the highest row is {prefix}-{highest:03d} — "
                f"set it to {prefix}-{highest + 1:03d}"
            )

    known = {r["id"] for r in rs}
    for tid, files in sorted(cites.items()):
        if tid not in known:
            errs.append(
                f"{files[0]}: cites `{tid}`, which is not a row in {ctx.rel(register)} — "
                "a citation that resolves to nothing reads as tracked when it is not"
            )
    return errs


def main(ctx: Context, argv: list[str] | None = None, doc: str | None = None) -> int:
    """The `scripts/validate_todos.py` entry point, verbatim — exit codes and stdout.

    Kept in the package rather than in the binding so the printed shape has one owner: a
    board that renders `Finding`s and a hook that reads stdout must never disagree about
    what the register says.
    """
    ap = argparse.ArgumentParser(description=doc or __doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="ignored; the register is always read whole")
    ap.add_argument("--list", action="store_true", help="print the open todos, oldest first")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    try:
        rs = rows(ctx)
    except TodoParseError as exc:
        print(f"todo register invalid: {exc}", file=sys.stderr)
        return 1
    cites = citations(ctx)
    for r in rs:
        r["cited_by"] = cites.get(r["id"], [])

    if args.json:
        print(json.dumps(rs, separators=(",", ":")))
        return 0

    if args.list:
        for r in sorted([x for x in rs if x["status"] == "open"], key=lambda x: x["raised"]):
            print(f"{r['id']}  ({r['raised']})\n    {r['todo'][:160]}")
            if r["where"] and r["where"] != "—":
                print(f"    where: {r['where']}")
        opn = sum(1 for r in rs if r["status"] == "open")
        print(f"\n{opn} open of {len(rs)}")
        return 0

    errs = validate(ctx, rs, cites)
    if errs:
        print("todo register invalid:", file=sys.stderr)
        for e in errs:
            print(f"- {e}", file=sys.stderr)
        return 1
    by = {s: sum(1 for r in rs if r["status"] == s) for s in sorted(STATUSES)}
    print(f"todos OK — {len(rs)} row(s): " + ", ".join(f"{v} {k}" for k, v in by.items() if v))
    return 0
