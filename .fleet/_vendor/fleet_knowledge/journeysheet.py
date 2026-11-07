"""A journey file read structurally, whole — for the journey page (not clipped like the list rows).

`corpus.journey_detail` keeps a journey as a *register row*: one clipped sentence per field, because
a list is an index. The journey PAGE needs the opposite: the whole job statement, the whole
preconditions, every happy-path step with its own words, the branches, and every acceptance
criterion in full. This module is that reader, and it is pure — text in, a dict out, no I/O.

**The optional per-step annotation.** The files say which surface the journey touches as a whole,
never which step happens where, nor which capability a step exercises, nor which step a branch
hangs off. A journey MAY say so, in a trailing brace group:

    3. **I run the command on the machine.** It checks the machine ... {on: Worker machine; covers: CAP-1488, CAP-2066}

    **Branches (...):** the code expired or was already used (the prompt says so) {step: 3}; ...

- `{on: <place>; covers: <CAP-id>, <CAP-id>}` closes a happy-path step. Both keys are optional.
- `{step: <n>}` closes a branch clause and names the happy-path step it hangs off.

A step or branch with no annotation is read with none — never guessed. A malformed or unknown
annotation is kept out of the prose and reported in `warnings`, so a typo is visible, not silent.
"""

from __future__ import annotations

import json
import re
from typing import Any

from fleet_knowledge.markdown import field, frontmatter, listfield, section
from fleet_knowledge.quality import AC_HEADING_RE, AC_ROW_RE, NEXT_H2_RE

__all__ = ["parse_journey", "split_covers", "split_top_level"]

_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)
_JOB_RE = re.compile(r"\*\*Job statement:\*\*\s*(.+?)(?:\n\s*\n|\Z)", re.S)
_PRE_RE = re.compile(r"\*\*Preconditions:\*\*\s*(.+?)(?:\n\s*\n|\Z)", re.S)
_TRIGGER_RE = re.compile(r"\*\*Trigger:\*\*\s*(.+?)(?:\n\s*\n|\Z)", re.S)
_BRANCH_RE = re.compile(r"^\*\*Branches\b[^*\n]*\*\*:?\s*(.*?)(?:\n\s*\n|\Z)", re.S | re.M)
_JOB_PARTS_RE = re.compile(
    r"^when\s+(.+?),?\s+i want\s+(?:to\s+)?(.+?),?\s+so\s+(?:that\s+)?(?:i can\s+)?(.+?)\.?$", re.I | re.S
)
_STEP_RE = re.compile(r"^\s*(\d+)\.\s+(.*)$")
_TIER_RE = re.compile(r"^\s*`\[(dev|ext)\]`\s*", re.I)
_ANNOTATION_RE = re.compile(r"\s*\{([^{}]*)\}\s*[.;]?\s*$")
_CAP_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*:CAP-\d+$|^CAP-\d+$")
_LEAD_BOLD_RE = re.compile(r"^\*\*(.+?)\*\*\s*(.*)$", re.S)
_ITALIC_WRAP_RE = re.compile(r"^\*(.+)\*$", re.S)


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_top_level(text: str, sep: str = ";") -> list[str]:
    """Split `text` on `sep` outside any parentheses, braces or backticks."""
    out: list[str] = []
    depth = 0
    tick = False
    cur: list[str] = []
    for ch in text:
        if ch == "`":
            tick = not tick
        elif not tick and ch in "({":
            depth += 1
        elif not tick and ch in ")}" and depth:
            depth -= 1
        if ch == sep and depth == 0 and not tick:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return [p.strip() for p in out if p.strip()]


def _surfaces(fm: str) -> list[str]:
    """The `surfaces:` list whole. A surface may carry commas inside its own parentheses, which a
    plain comma split (`listfield`) would cut in two, so a JSON-style list is read as JSON and
    anything else is split on commas outside brackets and quotes."""
    m = re.search(r"^surfaces:\s*(.*)$", fm, re.M)
    if not m:
        return []
    raw = m.group(1).strip()
    if not raw.startswith("["):
        return [raw.strip("\"' ")] if raw else []
    try:
        loaded = json.loads(raw)
        if isinstance(loaded, list):
            return [str(x).strip() for x in loaded if str(x).strip()]
    except ValueError:
        pass
    return [p.strip().strip("\"'") for p in split_top_level(raw[1:].rstrip("]"), ",")]


def split_covers(entry: str) -> tuple[str, str]:
    """`fleet:CAP-1640` -> `("fleet", "CAP-1640")`; a bare `CAP-1640` -> `("", "CAP-1640")`."""
    prefix, sep, rest = entry.strip().rpartition(":")
    return (prefix.strip(), rest.strip()) if sep else ("", rest.strip())


def _annotation(text: str, allowed: tuple[str, ...], warnings: list[str], where: str) -> tuple[str, dict[str, str]]:
    """Peel a trailing `{key: value; key: value}` off `text`. Unknown keys are reported, not kept."""
    m = _ANNOTATION_RE.search(text)
    if not m:
        return text, {}
    body = text[: m.start()].rstrip()
    pairs: dict[str, str] = {}
    for part in m.group(1).split(";"):
        if not part.strip():
            continue
        key, sep, value = part.partition(":")
        key = key.strip().lower()
        if not sep or key not in allowed or not value.strip():
            warnings.append(f"{where}: ignored `{part.strip()}` (this position takes {', '.join(allowed)})")
            continue
        pairs[key] = value.strip()
    return body, pairs


def _lines_of(block: str) -> list[str]:
    """The list items of a block, each with its continuation lines joined.

    A continuation is an indented line, or any line that follows with no blank between; a blank
    line followed by flush text ends the list (that text is the next paragraph, not the item's).
    """
    items: list[str] = []
    open_item = False
    blank = False
    for line in block.splitlines():
        if not line.strip():
            blank = True
            continue
        if _STEP_RE.match(line) or re.match(r"^\s*[-*]\s+", line):
            items.append(line.strip())
            open_item = True
        elif open_item and (line[0].isspace() or not blank):
            items[-1] += " " + line.strip()
        else:
            open_item = False
        blank = False
    return items


def _steps(text: str, warnings: list[str]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for item in _lines_of(section(text, "Happy path")):
        m = _STEP_RE.match(item)
        if not m:
            continue
        n = int(m.group(1))
        body, ann = _annotation(_flat(m.group(2)), ("on", "covers"), warnings, f"step {n}")
        caps: list[str] = []
        for raw in (ann.get("covers") or "").split(","):
            cap = raw.strip()
            if not cap:
                continue
            if _CAP_RE.match(cap):
                caps.append(cap)
            else:
                warnings.append(f"step {n}: ignored `{cap}` (not a capability id)")
        lead = _LEAD_BOLD_RE.match(body)
        if lead:
            title, rest = lead.group(1).strip().rstrip("."), lead.group(2).strip()
        else:
            first, dot, rest = body.partition(". ")
            title, rest = (first.strip().rstrip("."), rest.strip()) if dot else (body.rstrip("."), "")
        steps.append(
            {
                "n": n,
                "title": title,
                "text": rest,
                "on": ann.get("on", ""),
                "covers": caps,
                "annotated": bool(ann),
            }
        )
    return steps


def _branches(text: str, nsteps: set[int], warnings: list[str]) -> list[dict[str, Any]]:
    m = _BRANCH_RE.search(text)
    if not m:
        return []
    block = m.group(0)
    head = _BRANCH_RE.match(block)
    inline = (head.group(1) if head else "").strip()
    bullets = [re.sub(r"^[-*]\s+", "", i) for i in _lines_of(block.split("\n", 1)[1] if "\n" in block else "")]
    clauses = [_flat(b) for b in bullets] if bullets and not inline else split_top_level(_flat(inline))
    out: list[dict[str, Any]] = []
    for clause in clauses:
        body, ann = _annotation(clause.strip(), ("step",), warnings, "branch")
        at: int | None = None
        if "step" in ann:
            if ann["step"].isdigit() and int(ann["step"]) in nsteps:
                at = int(ann["step"])
            else:
                warnings.append(f"branch: `{{step: {ann['step']}}}` names no happy-path step")
        body = body.rstrip(" .")
        p = body.find("(")
        if p > 0 and body.endswith(")"):
            title, disposition = body[:p].strip(), body[p + 1 : -1].strip()
        else:
            title, disposition = body, ""
        if title:
            title = title[0].upper() + title[1:]
        out.append({"title": title, "disposition": disposition, "step": at})
    return out


def _criteria(text: str) -> list[dict[str, Any]]:
    """Every acceptance criterion in file order, numbered as `quality` numbers them (`slug#n`)."""
    out: list[dict[str, Any]] = []
    ordinal = 0
    for heading in AC_HEADING_RE.finditer(text):
        rest = text[heading.end() :]
        end = NEXT_H2_RE.search(rest)
        lines = (rest[: end.start()] if end else rest).splitlines()
        cur: list[str] | None = None
        rows: list[list[str]] = []
        for line in lines:
            if AC_ROW_RE.match(line):
                cur = [line.strip()]
                rows.append(cur)
            elif cur is not None and line.strip():
                cur.append(line.strip())
            elif not line.strip():
                cur = None
        for row in rows:
            ordinal += 1
            first = re.sub(r"^\d+\.\s+", "", row[0])
            tier = _TIER_RE.match(first)
            body = _flat(" ".join([first[tier.end() :] if tier else first, *row[1:]]))
            out.append({"n": ordinal, "tier": tier.group(1).lower() if tier else "", "text": body})
    return out


def parse_journey(text: str, slug: str = "") -> dict[str, Any]:
    """The whole journey page's content from one journey file's text."""
    warnings: list[str] = []
    fm = frontmatter(text)
    h1 = _H1_RE.search(text)
    job_m = _JOB_RE.search(text)
    job = _flat(job_m.group(1)) if job_m else ""
    wrapped = _ITALIC_WRAP_RE.match(job)
    if wrapped:
        job = wrapped.group(1).strip()
    parts = _JOB_PARTS_RE.match(job)
    pre_m = _PRE_RE.search(text)
    trig_m = _TRIGGER_RE.search(text)
    steps = _steps(text, warnings)
    return {
        "slug": slug or field(fm, "id"),
        "title": h1.group(1).strip() if h1 else slug,
        "persona": field(fm, "persona"),
        "tier": field(fm, "kind"),
        "surfaces": _surfaces(fm),
        "owning_prd": field(fm, "owning_prd") or (listfield(fm, "owning_prds") or [""])[0],
        "covers": listfield(fm, "covers"),
        "job": {
            "text": job,
            "when": _flat(parts.group(1)) if parts else "",
            "want": _flat(parts.group(2)) if parts else "",
            "so": _flat(parts.group(3)) if parts else "",
        },
        "preconditions": _flat(pre_m.group(1)) if pre_m else "",
        "trigger": _flat(trig_m.group(1)) if trig_m else "",
        "steps": steps,
        "branches": _branches(text, {s["n"] for s in steps}, warnings),
        "criteria": _criteria(text),
        "warnings": warnings,
    }
