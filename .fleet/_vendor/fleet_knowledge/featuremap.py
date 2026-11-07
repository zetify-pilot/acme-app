"""Write a NEW feature area's map — the smallest one that passes the repository's own checks on day one (FLT-1292).

The owner's decision (2026-10-28): in a repository that plans by area, a request no existing area fits is proposed as
a new feature area together with its first slice, and the single accept creates both. `slice:create` writes the map
and the slice row in one merged pull request, through this module (`knowledge/scripts/new_feature_area.py`), so the
map is written by one rule rather than by a session's reading of whatever map it opened first.

**What the map carries, and nothing more.** A feature map is a durable capability ledger (`slot:feature-maps`); a new
one starts with its frontmatter, its `# Name`, its `> **Intent.**` sentence and an EMPTY capability table. Its
capabilities arrive with the work that ships them, never invented here. The fields the structure check
(`journeys-and-features`) requires are all written:

  * `components` — what will realise the area. Required (a customer-facing area names at least one); the check
    resolves each against the component registry.
  * `specs` — the invariant specs it honours. Defaults to the spec the repository's existing maps cite most, which
    is the one every area there already honours.
  * `source_of_truth` — the code paths the freshness contract watches. Required, every path existing: for an area
    whose code is not written yet, the narrowest existing paths its first work extends.
  * `journeys: []`, `surfaces: []` — none yet; the first PRD that lands a surface adds it.
  * `brief:` — the feature brief (`fleet_knowledge.featurebrief`) as the accepted proposal gave it: summary,
    problem, example, the journeys the example is drawn from, and what it is not. A field not given is written
    empty — and the `feature-briefs` check holds a map a change ADDS to a complete brief, so a new area written
    without one fails that check until the brief is filled in. A brief that states ship-state, names an internal
    id bare, or draws its example from a journey that does not exist is refused, as the check would refuse it.
  * the USES — when the proposal names them, each is a `###` section of `## Capabilities` with its one plain
    paragraph and an empty table, so the first rows land in the use they serve. A use paragraph that states
    ship-state or names an internal id bare is refused, as the check would refuse it.

And the map is listed in the features index (`features/README.md`), which the check also requires.

**Refused, never guessed** (`NewAreaRefusedError`): a slug that is not a slug, an existing area, a corpus with
no feature map yet (its slices live under `product` until the repository writes its first map by hand — there is no
area to argue a new one against), no component, no source path, or a source path that does not exist.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from . import featurebrief
from .markdown import field, frontmatter, listfield
from .planningmode import feature_areas

__all__ = [
    "AREA_SLUG",
    "RESERVED_AREA_SLUGS",
    "NewAreaRefusedError",
    "RemovedUse",
    "WorkBeingBuiltError",
    "add_use",
    "brief_from_json",
    "remove_use",
    "uses_from_json",
    "write_brief",
    "write_new_area",
]

#: The slug shape — the map's file name, and the shape the board's area-owner table checks.
AREA_SLUG: Final = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

#: SLUGS NO FEATURE MAY TAKE (`featurebrief.RESERVED_AREA_SLUGS`), re-exported for the writer's callers.
RESERVED_AREA_SLUGS: Final[frozenset[str]] = featurebrief.RESERVED_AREA_SLUGS

#: A rendered map's fragment shell — a corpus whose maps are rendered from fragments commits this instead of `.md`.
SHELL_SUFFIX: Final = ".md.tmpl"

#: The brief a new map starts with: every key the schema names, every one empty.
BRIEF_SKELETON: Final = 'brief:\n  summary: ""\n  problem: ""\n  example: ""\n  example_from: []\n  not: []\n'

#: The capability table a new map starts with: the header the structure check reads, and no row.
EMPTY_LEDGER: Final = (
    "| ID | Capability | Ships in | Tested by | Anchor | Needs |\n"
    "|----|------------|----------|-----------|--------|-------|\n"
)


def _brief(brief: Mapping[str, Any] | None) -> dict[str, Any]:
    """The brief as the schema's five keys, whitespace folded; `""` / `[]` for what was not given."""
    b = brief or {}
    out: dict[str, Any] = {k: " ".join(str(b.get(k) or "").split()) for k in featurebrief.BRIEF_TEXT_KEYS}
    for k in featurebrief.BRIEF_LIST_KEYS:
        out[k] = [" ".join(str(x).split()) for x in b.get(k) or () if str(x).strip()]
    return out


def brief_from_json(text: str) -> dict[str, Any]:
    """A brief from `new_feature_area.py --brief-json`: one JSON object with the schema's keys and nothing else.

    Refused (`NewAreaRefusedError`), never guessed: JSON that does not parse, a value that is not an object, an
    unknown key, a prose field that is not a string, a list field that is not a list of strings."""
    try:
        data = json.loads(text)
    except ValueError as bad:
        raise NewAreaRefusedError(f"--brief-json is not JSON: {bad}.") from None
    if not isinstance(data, dict):
        raise NewAreaRefusedError("--brief-json must be one JSON object.")
    unknown = sorted(set(data) - set(featurebrief.BRIEF_KEYS))
    if unknown:
        raise NewAreaRefusedError(
            f"--brief-json has unknown key(s) {', '.join(unknown)} — the keys are {', '.join(featurebrief.BRIEF_KEYS)}."
        )
    for key in featurebrief.BRIEF_TEXT_KEYS:
        if not isinstance(data.get(key, ""), str):
            raise NewAreaRefusedError(f"--brief-json `{key}` must be a string.")
    for key in featurebrief.BRIEF_LIST_KEYS:
        value = data.get(key, [])
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            raise NewAreaRefusedError(f"--brief-json `{key}` must be a list of strings.")
    return dict(data)


def uses_from_json(text: str) -> list[tuple[str, str, list[str]]]:
    """The uses from `write_feature_brief.py --uses-json`: a JSON list of `{name, paragraph, rows: [row id, ...]}`.

    Refused (`NewAreaRefusedError`), never guessed: JSON that does not parse, a value that is not a list of objects, an
    unknown key, a name or paragraph that is not a string, rows that are not a list of strings."""
    try:
        data = json.loads(text)
    except ValueError as bad:
        raise NewAreaRefusedError(f"--uses-json is not JSON: {bad}.") from None
    if not isinstance(data, list) or not all(isinstance(u, dict) for u in data):
        raise NewAreaRefusedError("--uses-json must be a JSON list of {name, paragraph, rows} objects.")
    out: list[tuple[str, str, list[str]]] = []
    for u in data:
        unknown = sorted(set(u) - {"name", "paragraph", "rows"})
        if unknown:
            raise NewAreaRefusedError(
                f"--uses-json has unknown key(s) {', '.join(unknown)} — the keys are name, paragraph, rows."
            )
        name, paragraph, rows = u.get("name", ""), u.get("paragraph", ""), u.get("rows", [])
        if not isinstance(name, str) or not isinstance(paragraph, str):
            raise NewAreaRefusedError("--uses-json: each use's `name` and `paragraph` are strings.")
        if not isinstance(rows, list) or not all(isinstance(r, str) for r in rows):
            raise NewAreaRefusedError("--uses-json: each use's `rows` is a list of row ids.")
        out.append((name, paragraph, list(rows)))
    return out


def _quoted(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _brief_block(brief: Mapping[str, Any]) -> str:
    """The `brief:` frontmatter: each prose field folded (`>-`) when written, `""` when not; the lists flow."""
    lines = ["brief:"]
    for key in featurebrief.BRIEF_TEXT_KEYS:
        value = str(brief.get(key) or "")
        lines += [f"  {key}: >-", f"    {value}"] if value else [f'  {key}: ""']
    lines.append(f"  example_from: [{', '.join(brief.get('example_from') or [])}]")
    nots = list(brief.get("not") or [])
    lines += ["  not:", *(f"    - {_quoted(x)}" for x in nots)] if nots else ["  not: []"]
    return "\n".join(lines) + "\n"


def _journey_slugs(knowledge: Path) -> set[str]:
    """The journey catalog's slugs — what a brief's `example_from` must name."""
    from .corpus import (
        journeys,  # noqa: PLC0415 — the corpus readers are heavy; only a brief with an example needs them
    )

    return {j["slug"] for j in journeys(knowledge)}


class NewAreaRefusedError(ValueError):
    """Why this new area cannot be written — a sentence a person reads, never a guess made instead."""


def _flow(items: Sequence[str]) -> str:
    return "[" + ", ".join(items) + "]"


def _cited_specs(features: Path) -> list[str]:
    """The spec the existing maps cite most (ties: alphabetical), as a one-item list, or `[]` when none cites one."""
    counts: Counter[str] = Counter()
    for path in sorted(features.glob("*.md")) + sorted(features.glob(f"*{SHELL_SUFFIX}")):
        fm = frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        if field(fm, "type") == "feature-map":
            counts.update(dict.fromkeys(listfield(fm, "specs"), 1))
    if not counts:
        return []
    top = max(counts.values())
    return [sorted(spec for spec, n in counts.items() if n == top)[0]]


def _index_row(name: str, slug: str, components: Sequence[str]) -> str:
    return f"| **{name}** | [`{slug}.md`]({slug}.md) | {', '.join(components) or '—'} |"


def _indexed(readme: Path, name: str, slug: str, components: Sequence[str]) -> str:
    """The features index with this map listed: after the last row that already links a map, so it joins the
    index's own table; at the end when the index has no such row; a minimal index when there is none."""
    row = _index_row(name, slug, components)
    if not readme.is_file():
        head = "---\ntype: readme\n---\n\n# Feature maps\n\n## Index\n\n"
        return f"{head}| Area | File | Components |\n|---|---|---|\n{row}\n"
    lines = readme.read_text(encoding="utf-8").splitlines()
    linked = [
        i for i, line in enumerate(lines) if line.lstrip().startswith("|") and re.search(r"\]\([^)]+\.md\)", line)
    ]
    if linked:
        lines.insert(linked[-1] + 1, row)
    else:
        lines += ["", row]
    return "\n".join(lines) + "\n"


def write_new_area(
    repo: Path,
    knowledge: Path,
    *,
    slug: str,
    name: str,
    sentence: str,
    components: Sequence[str],
    source_of_truth: Sequence[str],
    specs: Sequence[str] = (),
    features_dir: str = "features",
    uses: Sequence[tuple[str, str]] = (),
    brief: Mapping[str, Any] | None = None,
) -> list[Path]:
    """Write `<knowledge>/<features_dir>/<slug>.md` and list it in the features index; return the files written.

    Refuses (`NewAreaRefusedError`) rather than writing a map the repository's checks would fail on a reason only a
    person can settle — see the module docstring for each refusal."""
    slug, name, sentence = slug.strip(), " ".join(name.split()), " ".join(sentence.split())
    if not AREA_SLUG.match(slug):
        raise NewAreaRefusedError(
            f"{slug!r} is not a feature area slug: lower-case letters, digits, '.', '_' or '-', starting with a "
            f"letter or digit."
        )
    if slug in RESERVED_AREA_SLUGS:
        raise NewAreaRefusedError(
            f"{slug!r} is reserved: it is the Features page's own address for a new feature. Pick another slug."
        )
    if not name or not sentence:
        raise NewAreaRefusedError("a new feature area needs a name and its one-sentence Intent.")
    features = knowledge / features_dir
    existing = feature_areas(knowledge, features_dir)
    if not existing:
        raise NewAreaRefusedError(
            "this repository has no feature map yet, so there is no area to argue a new one against: its slices go "
            "under `product` until it writes its first feature map."
        )
    if slug in existing or (features / f"{slug}.md").exists() or (features / f"{slug}{SHELL_SUFFIX}").exists():
        raise NewAreaRefusedError(f"a feature area `{slug}` already exists; put the slice under it.")
    # A FEATURE WITH NO CODE YET (greenfield "New feature", 2026-11-01) has no component and no code path to name:
    # both may be empty TOGETHER, and the structure check holds the map to them the moment a row cites built work
    # (`journeys-and-features`, "no code yet"). Naming one without the other is the half-answer it always refused.
    comps = [c.strip() for c in components if c.strip()]
    paths = [p.strip() for p in source_of_truth if p.strip()]
    if bool(comps) != bool(paths):
        raise NewAreaRefusedError(
            "a new feature area names its component(s) AND at least one existing code path for the freshness contract "
            "to watch (the narrowest path its first work extends, never a whole package) — or, for a feature with no "
            "code yet, neither."
            if comps
            else "a new feature area that names a code path must also name the component(s) that will realise it."
        )
    missing = [p for p in paths if not (repo / p.rstrip("/")).exists()]
    if missing:
        raise NewAreaRefusedError(f"source_of_truth {', '.join(missing)} does not exist in the repository.")
    cut = [(" ".join(n.split()), " ".join(p.split())) for n, p in uses if n.strip()]
    given = _brief(brief)
    refused = [
        msg
        for level, msg, _line in featurebrief.brief_findings(
            given,
            (),
            [featurebrief.Use(n, p, i, misfit=False, start=0, end=0) for i, (n, p) in enumerate(cut)],
            journey_slugs=None,
        )
        if level == "error"
    ]
    if refused:
        raise NewAreaRefusedError(refused[0])
    journeys = _journey_slugs(knowledge) if given["example_from"] else set()
    unknown = [s for s in given["example_from"] if s not in journeys]
    if unknown:
        raise NewAreaRefusedError(f"the brief's example names journeys that do not exist: {', '.join(unknown)}.")
    cited = [s.strip() for s in specs if s.strip()] or _cited_specs(features)
    sot = "\n".join(f"  - {p}" for p in paths)
    text = (
        "---\n"
        "type: feature-map\n"
        f"area: {slug}\n"
        "kind: product\n"
        f"components: {_flow(comps)}\n"
        "journeys: []\n"
        f"specs: {_flow(cited)}\n"
        "surfaces: []\n"
        + (f"source_of_truth:\n{sot}\n" if paths else "source_of_truth: []\n")
        + f"{_brief_block(given)}"
        "---\n\n"
        f"# {name}\n\n"
        f"> **Intent.** {sentence}\n\n"
        "## Capabilities\n\n"
        "Capabilities arrive with the work that ships them; a new area starts with none.\n\n"
        + (
            "\n".join(f"### {use_name}\n\n{paragraph}\n\n{EMPTY_LEDGER}" for use_name, paragraph in cut)
            if cut
            else EMPTY_LEDGER
        )
    )
    map_path = features / f"{slug}.md"
    readme = features / "README.md"
    index = _indexed(readme, name, slug, comps)
    map_path.write_text(text, encoding="utf-8")
    readme.write_text(index, encoding="utf-8")
    return [map_path, readme]


def add_use(knowledge: Path, *, slug: str, name: str, paragraph: str, features_dir: str = "features") -> list[Path]:
    """Add one USE — a new thing an existing feature does — to `<knowledge>/<features_dir>/<slug>.md`; return the
    file written (owner, 2026-11-01, the "New feature" flows).

    The use is a `###` section of `## Capabilities`: its name, its one plain paragraph and an EMPTY table, placed after
    the feature's last use and above the rows waiting to move (`### Misfits (to move)`) and the retired ones. No row is
    written: the use's capabilities arrive with the plan made for it from the feature's page, as a new map's do.

    Refused (`NewAreaRefusedError`), never guessed: no such feature; a map rendered from templates (its uses are
    written in the template, by hand); a map not cut into uses yet; a name the feature already has (case folded); a
    blank name or paragraph; a paragraph that states ship-state or names an internal id bare; and a seventh use, which
    the `feature-briefs` check refuses on a map a change touches."""
    slug, name, paragraph = slug.strip(), " ".join(name.split()), " ".join(paragraph.split())
    if not name or not paragraph:
        raise NewAreaRefusedError("a new use needs a name and one paragraph saying what a person does with it.")
    features = knowledge / features_dir
    path = features / f"{slug}.md"
    if (features / f"{slug}{SHELL_SUFFIX}").exists():
        raise NewAreaRefusedError(
            f"the feature `{slug}` has its page rendered from templates, so a new use is added in its template by hand."
        )
    if not AREA_SLUG.match(slug) or not path.is_file() or slug not in feature_areas(knowledge, features_dir):
        raise NewAreaRefusedError(f"there is no feature `{slug}` in this repository to add a use to.")
    text = path.read_text(encoding="utf-8")
    sections = featurebrief.capability_uses(text)
    uses = [u for u in sections if u.is_use]
    if not uses:
        raise NewAreaRefusedError(
            f"the feature `{slug}` is not cut into uses yet, so a new one has no place beside them: cut its map first."
        )
    if any(u.name.casefold() == name.casefold() for u in uses):
        raise NewAreaRefusedError(f"the feature `{slug}` already does “{name}”: plan more work there instead.")
    refused = [
        msg
        for level, msg, _line in featurebrief.brief_findings(
            {}, (), [featurebrief.Use(name, paragraph, 0, misfit=False, start=0, end=0)], journey_slugs=None
        )
        if level == "error" and name in msg
    ]
    if refused:
        raise NewAreaRefusedError(refused[0])
    lines = text.splitlines()
    after = [u for u in sections if not u.is_use]
    at = min(u.start for u in after) if after else uses[-1].end
    while at > 0 and not lines[at - 1].strip():
        at -= 1
    block = ["", f"### {name}", "", paragraph, "", *EMPTY_LEDGER.rstrip("\n").split("\n")]
    tail = lines[at:]
    out = lines[:at] + block + (["", *_drop_leading_blanks(tail)] if tail else [])
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return [path]


class WorkBeingBuiltError(NewAreaRefusedError):
    """A use cannot be removed yet: work under it is being built right now. The run asks the person whether to stop
    that work too, and runs again with `stop_work_being_built` when they say so."""


@dataclass(frozen=True)
class RemovedUse:
    """What `remove_use` wrote: the files, the rows now under `### Retired`, and the plans it cancelled or left."""

    written: list[Path]
    retired: list[str]
    cancelled: list[str]
    #: Plans the use's rows cite that stay as they are: shipped, already cancelled, or still serving another use.
    kept: list[str] = dc_field(default_factory=list)


#: PRD statuses a removal never touches: built work stays, and a cancelled plan is already gone.
_PRD_LEFT: Final = frozenset({"shipped", "cancelled"})
#: PRD statuses that mean the work is being built right now.
_PRD_BEING_BUILT: Final = frozenset({"implementing", "verified"})
_PRD_NUM: Final = re.compile(r"(?<![\w:-])(\d{4})(?![\w-])")


def remove_use(
    knowledge: Path,
    *,
    slug: str,
    name: str,
    reason: str,
    features_dir: str = "features",
    prds_dir: str = "prds",
    stop_work_being_built: bool = False,
    now: datetime | None = None,
) -> RemovedUse:
    """Remove one USE from a feature and keep its history (owner, 2026-11-03, "Remove, keep the history").

    * The use's `###` section leaves `## Capabilities`: its heading and paragraph go, and every capability table it
      held moves WHOLE — header and rows, byte for byte — to the map's `### Retired` section (made, last, when the
      map has none). A row under `### Retired` reads as retired whatever its `Ships in` says, so built work stays on
      the page as retired and unbuilt rows are kept there too. Nothing is reworded, renumbered or dropped.
    * Every plan (PRD) the use's rows cite in `Ships in`, or that names the use in its `use:` frontmatter, and that is
      not built yet, is CANCELLED the way `prd:cancel` cancels: `status: cancelled`, `cancelled_reason:` the person's
      reason, and a `status_history` entry. A shipped or already-cancelled plan is left as it is, and so is one a live
      row of ANOTHER use still cites: it serves more than this use.

    Refused (`NewAreaRefusedError`), never guessed: no such feature or use; a map rendered from templates; a blank
    reason; a feature left with fewer uses than its remaining rows need (`featurebrief.fewest_uses`) — the
    `feature-briefs` check would refuse the change. `WorkBeingBuiltError` when a plan under the use is being built
    right now and `stop_work_being_built` is not set: that is the person's call."""
    slug, name, reason = slug.strip(), " ".join(name.split()), " ".join(reason.split())
    if not reason:
        raise NewAreaRefusedError("removing a use needs a short reason; it is kept with the plans it cancels.")
    features = knowledge / features_dir
    path = features / f"{slug}.md"
    if (features / f"{slug}{SHELL_SUFFIX}").exists():
        raise NewAreaRefusedError(
            f"the feature `{slug}` has its page rendered from templates, so a use is removed in its template by hand."
        )
    if not AREA_SLUG.match(slug) or not path.is_file() or slug not in feature_areas(knowledge, features_dir):
        raise NewAreaRefusedError(f"there is no feature `{slug}` in this repository to remove a use from.")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    sections = featurebrief.capability_uses(text)
    target = next((u for u in sections if u.is_use and u.name.casefold() == name.casefold()), None)
    if target is None:
        raise NewAreaRefusedError(f"the feature `{slug}` has no use called “{name}” to remove.")
    if any(line.strip().startswith("<!-- rows:") for line in lines[target.start : target.end]):
        raise NewAreaRefusedError(
            f"the use “{target.name}” keeps its rows in fragments, so it is removed with its fragments by hand."
        )

    # ── the use's tables, whole, and the plans its rows cite ─────────────────────────────────────────────────────
    tables: list[list[str]] = []
    cited: list[str] = []
    ships_at = -1
    i = target.start + 1
    while i < target.end:
        s = lines[i].strip()
        if s.startswith("|") and i + 1 < target.end and _TABLE_SEPARATOR.match(lines[i + 1].strip()):
            cells = [c.strip().lower() for c in s.strip("|").split("|")]
            ships_at = cells.index("ships in") if "ships in" in cells else -1
            tables.append([lines[i], lines[i + 1]])
            i += 2
            continue
        if s.startswith("|") and tables:
            tables[-1].append(lines[i])
            cells = [c.strip() for c in s.strip("|").split("|")]
            if 0 <= ships_at < len(cells):
                cited += [n for n in _PRD_NUM.findall(cells[ships_at]) if n not in cited]
        i += 1
    rows = [r for t in tables for r in t[2:]]
    row_ids = [m.group(1) for r in rows if (m := re.match(r"^\|\s*([A-Z][A-Z0-9]*-\d+)\s*\|", r.strip()))]

    # ── the plans: which are cancelled, which stay ───────────────────────────────────────────────────────────────
    elsewhere = _cited_outside(lines, sections, target)
    plans = _plans_for(knowledge / prds_dir, slug=slug, use=target.name, cited=cited)
    cancel: list[tuple[str, Path, str]] = []
    kept: list[str] = []
    building: list[str] = []
    for number, prd, text_of in plans:
        status = _status_of(text_of)
        if status in _PRD_LEFT or number in elsewhere:
            kept.append(number)
        elif status in _PRD_BEING_BUILT and not stop_work_being_built:
            building.append(number)
        else:
            cancel.append((number, prd, text_of))
    if building:
        raise WorkBeingBuiltError(
            f"work under “{target.name}” is being built right now ({len(building)} plan(s)). Removing the use cancels "
            f"it, so the person decides: stop that work and remove the use, or keep the use."
        )

    # ── write the map: the section out, its tables under `### Retired` ──────────────────────────────────────────
    out = lines[: target.start] + lines[target.end :]
    while (
        target.start < len(out)
        and target.start > 0
        and not out[target.start - 1].strip()
        and not out[target.start].strip()
    ):
        del out[target.start]
    moved = [line for t in tables for line in ["", *t]]
    after = featurebrief.capability_uses("\n".join(out) + "\n")
    retired = next((u for u in after if u.retired), None)
    if retired is not None:
        at = retired.end
        while at > retired.start + 1 and not out[at - 1].strip():
            at -= 1
        out = out[:at] + moved + out[at:]
    else:
        begin, end = _capabilities_span(out)
        at = end
        while at > begin + 1 and not out[at - 1].strip():
            at -= 1
        out = out[:at] + ["", f"### {featurebrief.RETIRED_HEADING}", *moved, ""] + out[at:]
    new_text = "\n".join(out).rstrip("\n") + "\n"
    # THE COUNT the `feature-briefs` check holds a touched map to, read off the map as it will be written.
    prefix = row_ids[0].rsplit("-", 1)[0] if row_ids else "CAP"
    live_after = featurebrief.live_rows(new_text, prefix)
    uses_after = sum(1 for u in featurebrief.capability_uses(new_text) if u.is_use)
    if uses_after < featurebrief.fewest_uses(live_after):
        raise NewAreaRefusedError(
            f"the feature would be left doing {uses_after} thing(s), and a feature with this much in it is cut into at "
            f"least {featurebrief.fewest_uses(live_after)}. Add or split another use first, then remove this one."
        )
    path.write_text(new_text, encoding="utf-8")

    stamp = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    written = [path]
    for _number, prd, text_of in cancel:
        prd.write_text(_cancelled(text_of, reason=reason, at=stamp), encoding="utf-8")
        written.append(prd)
    return RemovedUse(written=written, retired=row_ids, cancelled=[c[0] for c in cancel], kept=kept)


def _cited_outside(lines: Sequence[str], sections: Sequence[featurebrief.Use], target: featurebrief.Use) -> set[str]:
    """The plan numbers a LIVE row of any other use cites: a plan serving more than the use being removed stays."""
    out: set[str] = set()
    for use in sections:
        if not use.is_use or use.start == target.start:
            continue
        ships_at = -1
        for k in range(use.start + 1, use.end):
            s = lines[k].strip()
            if not s.startswith("|"):
                continue
            if k + 1 < use.end and _TABLE_SEPARATOR.match(lines[k + 1].strip()):
                cells = [c.strip().lower() for c in s.strip("|").split("|")]
                ships_at = cells.index("ships in") if "ships in" in cells else -1
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if 0 <= ships_at < len(cells):
                out.update(_PRD_NUM.findall(cells[ships_at]))
    return out


def _plans_for(prds: Path, *, slug: str, use: str, cited: Sequence[str]) -> list[tuple[str, Path, str]]:
    """Every plan the use's rows cite, and every plan whose frontmatter names this feature's use: `(number, path,
    text)`, in number order."""
    found: dict[str, tuple[Path, str]] = {}
    for prd in sorted(prds.glob("*/prd.md")):
        number = prd.parent.name[:4]
        if not number.isdigit():
            continue
        text = prd.read_text(encoding="utf-8")
        fm = frontmatter(text)
        named = " ".join(field(fm, "use").split()).casefold() == use.casefold() and field(fm, "area") == slug
        if number in cited or named:
            found[number] = (prd, text)
    return [(n, *found[n]) for n in sorted(found)]


def _status_of(text: str) -> str:
    m = re.search(r"^status:[ \t]*(\S+)[ \t]*$", _frontmatter_block(text), re.M)
    return m.group(1).strip("\"'").lower() if m else ""


def _frontmatter_block(text: str) -> str:
    m = re.match(r"^---\n(.*?)\n---(\n|$)", text, re.S)
    return m.group(1) if m else ""


def _cancelled(text: str, *, reason: str, at: str) -> str:
    """`text` with the plan cancelled as `prd:cancel` Step 2 writes it: `status: cancelled`, `cancelled_reason:` and
    a `status_history` entry appended."""
    m = re.match(r"^---\n(.*?)\n---(\n|$)", text, re.S)
    if not m:
        raise NewAreaRefusedError("a plan under the use has no frontmatter; cancel it by hand first.")
    fm = m.group(1)
    said = json.dumps(reason, ensure_ascii=False)
    fm = re.sub(r"^status:[ \t]*\S+[ \t]*$", "status: cancelled", fm, count=1, flags=re.M)
    if re.search(r"^cancelled_reason:", fm, re.M):
        fm = re.sub(r"^cancelled_reason:[^\n]*$", f"cancelled_reason: {said}", fm, count=1, flags=re.M)
    else:
        fm = re.sub(r"^status: cancelled$", f"status: cancelled\ncancelled_reason: {said}", fm, count=1, flags=re.M)
    entry = f"  - {{ state: cancelled, at: {at}, by: cancel }}"
    hm = re.search(r"^status_history:[^\n]*(?:\n[ \t]+[^\n]*)*", fm, re.M)
    if hm and hm.group(0).rstrip().endswith("[]"):
        fm = fm[: hm.start()] + "status_history:\n" + entry + fm[hm.end() :]
    elif hm:
        fm = fm[: hm.end()] + "\n" + entry + fm[hm.end() :]
    else:
        fm += "\nstatus_history:\n" + entry
    return "---\n" + fm + text[m.end(1) :]


#: Where the notes that sat between an old map's capability tables go when its rows are sorted into uses: they are
#: no use's, so they move whole and in order to a section of their own after `## Capabilities`.
NOTES_HEADING: Final = "Notes"
NOTES_HEADING_TAKEN: Final = "Capability notes"

_TABLE_SEPARATOR: Final = re.compile(r"^\|\s*:?-{2,}")


def write_brief(
    knowledge: Path,
    *,
    slug: str,
    brief: Mapping[str, Any],
    uses: Sequence[tuple[str, str, Sequence[str]]],
    features_dir: str = "features",
    cap_prefix: str = "CAP",
) -> list[Path]:
    """Write the BRIEF of an EXISTING feature and sort its capability rows into USES — "Write the brief" on a feature's
    page (owner, 2026-11-02). Returns the file written.

    `uses` is `[(name, paragraph, [row id, ...]), ...]`: each becomes a `###` section of `## Capabilities` holding
    exactly the rows it names. **Rows are regrouped, never reworded, renumbered or dropped**: every live row of the map
    (outside `### Misfits (to move)` and `### Retired`, which are kept as they stand) is named by exactly one use, and
    each row line moves byte for byte under the table header it sat under. A use may name no row (a new thing the
    person asked for alongside the brief); it gets an empty table. The old `###` headings and their paragraphs are
    replaced by the new uses; any other line between the old tables (a note, a coverage remark) is no use's, so it moves
    whole and in order to a `## Notes` section after `## Capabilities` — kept, never lost. The `brief:` is written into
    the frontmatter, replacing one that was there.

    Refused (`NewAreaRefusedError`), never guessed: no such feature; a map rendered from templates; a row named twice,
    a row the map does not hold, a live row no use names; a use count under `featurebrief.fewest_uses`; a blank or
    repeated use name, or one of the two reserved section names; and a brief or use paragraph the `feature-briefs`
    check would refuse (ship-state, a bare internal id, an `example_from` journey that does not exist)."""
    slug = slug.strip()
    features = knowledge / features_dir
    path = features / f"{slug}.md"
    if (features / f"{slug}{SHELL_SUFFIX}").exists():
        raise NewAreaRefusedError(
            f"the feature `{slug}` has its page rendered from templates, so its brief is written in its template by "
            f"hand."
        )
    if not AREA_SLUG.match(slug) or not path.is_file() or slug not in feature_areas(knowledge, features_dir):
        raise NewAreaRefusedError(f"there is no feature `{slug}` in this repository to write a brief for.")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    sections = featurebrief.capability_uses(text)
    kept = [u for u in sections if not u.is_use]
    at = featurebrief.use_of_lines(text, sections)
    begin, end = _capabilities_span(lines)
    if begin < 0:
        raise NewAreaRefusedError(f"the feature `{slug}` has no `## Capabilities` section to sort into uses.")
    row = re.compile(rf"^\|\s*({re.escape(cap_prefix)}-\d+)\s*\|")
    replaced: set[int] = set()  # the old uses' headings and paragraphs, which the new uses replace
    for use in sections:
        if not use.is_use:
            continue
        replaced.add(use.start)
        k = use.start + 1
        while k < use.end and not lines[k].strip():
            k += 1
        while (
            k < use.end and lines[k].strip() and not lines[k].strip().startswith(("|", "<!--", ">", "- ", "* ", "```"))
        ):
            replaced.add(k)
            k += 1

    # ── read the section: intro, live rows (each with the header it sat under), notes, the kept sections ─────────
    intro: list[str] = []
    notes: list[list[str]] = []
    live: dict[str, tuple[str, str]] = {}  # row id → (row line, its table's header + separator)
    order: list[str] = []
    header = ""
    seen_body = False
    i = begin + 1
    while i < end:
        line = lines[i]
        owner = at[i]
        if owner is not None and not owner.is_use:
            i += 1
            continue
        s = line.strip()
        if i in replaced:
            seen_body = True
            i += 1
            continue
        if s.startswith("|"):
            seen_body = True
            if i + 1 < end and _TABLE_SEPARATOR.match(lines[i + 1].strip()) and not row.match(s):
                header = f"{line}\n{lines[i + 1]}"
                i += 2
                continue
            m = row.match(s)
            if m and header:
                if m.group(1) in live:
                    raise NewAreaRefusedError(f"the map holds the row {m.group(1)} twice; fix the map by hand first.")
                live[m.group(1)] = (line, header)
                order.append(m.group(1))
            else:
                _note(notes, line)
            i += 1
            continue
        if not s:
            if notes and notes[-1] and notes[-1][-1] != "":
                notes[-1].append("")
            elif not seen_body and intro and intro[-1] != "":
                intro.append("")
            i += 1
            continue
        if not seen_body:
            intro.append(line)
        else:
            _note(notes, line)
        i += 1

    # ── judge what was asked ────────────────────────────────────────────────────────────────────────────────────
    cut = [(" ".join(n.split()), " ".join(p.split()), [str(r).strip() for r in rows]) for n, p, rows in uses]
    names = [n for n, _p, _r in cut]
    if any(not n for n in names):
        raise NewAreaRefusedError("every use needs a name: the words the feature page lists.")
    reserved = {featurebrief.MISFIT_HEADING.casefold(), featurebrief.RETIRED_HEADING.casefold()}
    folded = [n.casefold() for n in names]
    if len(set(folded)) != len(folded) or reserved.intersection(folded):
        raise NewAreaRefusedError("each use needs a name of its own, and none may be called Misfits or Retired.")
    named = [r for _n, _p, rows in cut for r in rows]
    twice = sorted({r for r in named if named.count(r) > 1})
    if twice:
        raise NewAreaRefusedError(f"{', '.join(twice)} sit in more than one use; each row belongs to exactly one.")
    unknown = [r for r in named if r not in live]
    if unknown:
        raise NewAreaRefusedError(
            f"{', '.join(unknown)} {'is' if len(unknown) == 1 else 'are'} not a row of `{slug}`: rows are only "
            f"regrouped, never invented."
        )
    missing = [r for r in order if r not in set(named)]
    if missing:
        raise NewAreaRefusedError(
            f"{', '.join(missing)} {'is' if len(missing) == 1 else 'are'} in no use: every row of the feature goes "
            f"in one, never dropped."
        )
    fewest = featurebrief.fewest_uses(len(order))
    if len(cut) < fewest:
        raise NewAreaRefusedError(
            f"a feature with {len(order)} capability row(s) is cut into at least {fewest} uses, not {len(cut)}."
        )
    given = _brief(brief)
    refused = [
        msg
        for level, msg, _line in featurebrief.brief_findings(
            given,
            (),
            [featurebrief.Use(n, p, k, misfit=False, start=0, end=0) for k, (n, p, _r) in enumerate(cut)],
            journey_slugs=None,
            id_prefixes=("PG", "SL", "ENG", "CAP", cap_prefix),
            required=True,
        )
        if level == "error"
    ]
    if refused:
        raise NewAreaRefusedError(refused[0])
    journeys = _journey_slugs(knowledge) if given["example_from"] else set()
    strange = [s for s in given["example_from"] if s not in journeys]
    if strange:
        raise NewAreaRefusedError(f"the brief's example names journeys that do not exist: {', '.join(strange)}.")

    # ── write the section: intro, each use with its rows under their own headers, the kept sections ─────────────
    first_header = next((h for _line, h in live.values()), EMPTY_LEDGER.rstrip("\n"))
    out: list[str] = [lines[begin], ""]
    while intro and intro[-1] == "":
        intro.pop()
    if intro:
        out += [*intro, ""]
    for name, paragraph, rows in cut:
        out += [f"### {name}", "", paragraph, ""]
        mine = [r for r in order if r in set(rows)]
        if not mine:
            out += [*first_header.split("\n"), ""]
            continue
        by_header: dict[str, list[str]] = {}
        for r in mine:
            line, head = live[r]
            by_header.setdefault(head, []).append(line)
        for head, row_lines in by_header.items():
            out += [*head.split("\n"), *row_lines, ""]
    for section in kept:
        body = lines[section.start : min(section.end, end)]
        while body and not body[-1].strip():
            body.pop()
        out += [*body, ""]
    blocks = [b[:-1] if b and b[-1] == "" else b for b in notes if any(x.strip() for x in b)]
    if blocks:
        taken = any(re.match(rf"^##\s+{NOTES_HEADING}\s*$", ln) for ln in lines)
        out += [f"## {NOTES_HEADING_TAKEN if taken else NOTES_HEADING}", ""]
        for b in blocks:
            out += [*b, ""]
    tail = lines[end:]
    head_lines = _with_brief(lines[:begin], given)
    while head_lines and not head_lines[-1].strip():
        head_lines.pop()
    while out and not out[-1].strip():
        out.pop()
    written = [*head_lines, "", *out] + (["", *_drop_leading_blanks(tail)] if tail else [])
    path.write_text("\n".join(written) + "\n", encoding="utf-8")
    return [path]


def _note(notes: list[list[str]], line: str) -> None:
    """Add a line to the notes being carried out of `## Capabilities`: a new block after a blank line."""
    if not notes or (notes[-1] and notes[-1][-1] == ""):
        notes.append([])
    notes[-1].append(line)


def _capabilities_span(lines: Sequence[str]) -> tuple[int, int]:
    """`(heading line, first line after it)` of `## Capabilities`, outside fences; `(-1, -1)` when there is none."""
    begin = -1
    in_fence = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if begin < 0:
            if re.match(r"^##\s+Capabilities\s*#*\s*$", line, re.I):
                begin = i
            continue
        if re.match(r"^#{1,2}\s", line):
            return begin, i
    return begin, (len(lines) if begin >= 0 else -1)


def _with_brief(head: Sequence[str], brief: Mapping[str, Any]) -> list[str]:
    """The lines before `## Capabilities` with the frontmatter's `brief:` block written: replaced where it was, else
    added as the frontmatter's last key."""
    lines = list(head)
    if not lines or lines[0].strip() != "---":
        return [*_brief_block(brief).rstrip("\n").split("\n"), *lines]
    close = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if close is None:
        raise NewAreaRefusedError("the map's frontmatter is not closed by `---`; fix the map by hand first.")
    block = _brief_block(brief).rstrip("\n").split("\n")
    start = next((i for i in range(1, close) if re.match(r"^brief:", lines[i])), None)
    if start is None:
        return [*lines[:close], *block, *lines[close:]]
    stop = start + 1
    while stop < close and (not lines[stop].strip() or lines[stop][:1] in (" ", "\t")):
        stop += 1
    return [*lines[:start], *block, *lines[stop:]]


def _drop_leading_blanks(lines: Sequence[str]) -> list[str]:
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    return list(lines[i:])
