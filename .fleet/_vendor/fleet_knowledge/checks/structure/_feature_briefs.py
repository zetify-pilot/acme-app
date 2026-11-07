"""Feature briefs are well formed and complete — the newcomer's reading of each feature map (owner, 2026-10-31).

A feature map carries a `brief:` (summary, problem, example, example_from, not) and cuts its capability rows
into `###` uses of `## Capabilities`, each with one plain paragraph. The reading and the judging rules live in
`fleet_knowledge.featurebrief`; this module decides which maps must be COMPLETE and reports.

**Malformed is an error on every map**: an unknown key, a list written as a sentence, `example_from` naming a
journey that does not exist, ship-state words ("shipped", "partly built", "planned", "still open") or bare
internal ids (`PG-`, `SL-`, `ENG-`, the capability prefix) in the brief or a use paragraph.

**Complete is a ratchet** — briefs are written from now on, and no build turns red over a map nobody touched:

  * a map the change being validated ADDS or edits STRUCTURALLY — a row added, removed or moved between
    sections, a change to the `###` uses or to the brief — must be complete: a brief with every prose field
    written, every capability row under a `###` use with its paragraph, and at least three uses (fewer for a small
    map); each gap is an ERROR. A cell-only edit (a `Ships in` flip recording a shipped PRD) is not structural,
    so a headless run that only records progress is never made to author a whole brief. "This change" is
    the diff against the base the history-dependent checks already compare against (`fleet check --base`,
    the PR base in CI; else `origin/main`), plus what is staged and what is untracked — the pre-commit view.
    A fragment-backed map is edited structurally when its shell is, or a row fragment joins, leaves or moves
    between its tables;
  * any other map — untouched, or edited in its cells only — reports the same gaps as ADVISORY;
  * `feature_briefs_strict = true` under `[fleet.structure]` makes every map required. Default off.

A complete map is cut into at least three uses, with no ceiling — at least one when it has fewer than
three live rows, none when it has no rows; `### Retired` (the standing home of retired or withdrawn rows) is not a
use and is allowed on every map.
Rows waiting in `### Misfits (to move)` are ADVISORY on every map, strict included: a headless run that adds a row
fitting no use parks it there, files a task, and must still be able to commit. So is an empty `example_from` (an
area with no journey yet).

No base to compare against (no git, or a base that does not resolve) reads every map as untouched — git
absence is never a violation.

A map rendered from a fragment shell (`<area>.md.tmpl`) is read from the shell, because that is the file a
person edits; the rendered `.md` beside it is not read twice.

Stdlib only.
"""

from __future__ import annotations

import json
from pathlib import Path

from fleet_knowledge import corpus, featurebrief
from fleet_knowledge.checks.planning._git import changed_paths, git, git_out
from fleet_knowledge.config import KnowledgeBase, git_context
from fleet_knowledge.markdown import frontmatter
from fleet_knowledge.runner import Finding

from ._kit import option

SHELL_SUFFIX = ".md.tmpl"
DEFAULT_BASE_REF = "origin/main"

HINT = (
    "Follow the feature-brief schema: `brief:` takes summary, problem, example, example_from and not; "
    "say it in plain words with no ship-state and no internal ids — progress is read from PRD `status:`."
)
COMPLETE_HINT = (
    "A map this change writes must be complete: add its `brief:` (summary, problem, example, example_from, "
    "not), cut `## Capabilities` into `###` uses (at least three) each with a one- or two-sentence paragraph, "
    "and move every row — cells unchanged — into a use, or under `### Misfits (to move)` with a task filed."
)


def map_files(features: Path) -> list[Path]:
    """Each feature map's authored file: its `.md.tmpl` shell when it has one, else its `.md`."""
    stems: dict[str, Path] = {}
    for path in sorted(features.glob("*.md")):
        stems[path.stem] = path
    for path in sorted(features.glob(f"*{SHELL_SUFFIX}")):
        stems[path.name.removesuffix(SHELL_SUFFIX)] = path
    return [p for stem, p in sorted(stems.items()) if stem != "README" and not stem.startswith("_")]


def _stem(path: Path) -> str:
    return path.name.removesuffix(SHELL_SUFFIX).removesuffix(".md")


def _table_of(text: str | None) -> str | None:
    """A row fragment's map stem (the part of its `table` key before `#`), or `None` for no readable fragment."""
    if text is None:
        return None
    try:
        table = str(json.loads(text).get("table") or "")
    except ValueError:
        return None
    return table.split("#", 1)[0] if "#" in table else None


def structural_stems(kb: KnowledgeBase) -> set[str] | None:
    """The feature-map stems this change edited STRUCTURALLY, or `None` when there is no base to compare against.

    Structural: a new map; a capability row added, removed or moved between sections; a change to the `###`
    uses or their paragraphs; a change to the brief. A row fragment added, deleted or moved to another table
    counts for every map it left or joined. A cell-only edit — a `Ships in` flip, a `Tested by` added — is not.
    """
    root = Path(kb.root)
    base = git_context(kb).base or DEFAULT_BASE_REF
    changed = changed_paths(root, base)
    if changed is None:
        return None
    changed |= {ln for ln in git_out(root, "ls-files", "--others", "--exclude-standard").splitlines() if ln}
    features = (kb.knowledge / kb.config.features_dir).resolve()
    rows = features / corpus.FEATURE_ROWS_SUBDIR
    prefix = kb.config.capability_prefix
    out: set[str] = set()
    for rel in sorted(changed):
        path = (root / rel).resolve()
        is_map = path.parent == features and path.name.endswith((".md", SHELL_SUFFIX))
        if not is_map and not (path.parent == rows and path.suffix == ".json"):
            continue
        before = git(root, "show", f"{base}:{rel}")
        now = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None
        if is_map:
            if (
                before is None
                or now is None
                or featurebrief.structure_of(before, prefix) != featurebrief.structure_of(now, prefix)
            ):
                out.add(_stem(path))
        else:
            was, nowt = _table_of(before), _table_of(now)
            if was != nowt or before is None or now is None:
                out |= {s for s in (was, nowt) if s}
    return out


def _no_base(kb: KnowledgeBase) -> Finding:
    """What it means that there is no base to compare against: an ERROR when the caller named one (`--base` in
    CI — a ratchet that silently read every map as untouched would pass everything), else an advisory note."""
    asked = git_context(kb).base
    if asked:
        return Finding(
            level="error",
            message=f"cannot compare against the base `{asked}`, so no map can be held to the brief ratchet.",
            hint="Fetch the base commit (a full-history checkout), or run without `--base` locally.",
        )
    return Finding(
        level="advisory",
        message=f"no `{DEFAULT_BASE_REF}` to compare against, so every map is read as untouched.",
        hint="Fetch `origin/main`, or pass `--base <commit>`, to hold the maps this change writes to the ratchet.",
    )


class FeatureBriefs:
    name = "feature-briefs"
    title = "Feature briefs are well formed"
    description = (
        "A feature map's brief is what a newcomer reads first, and its uses are how its capabilities are cut. "
        "A malformed brief or use is an error on every map; a map this change adds or re-cuts must also be "
        "complete (a brief, every row under a use), and the gaps of any other map are advisory."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        return kb.has("features_dir")

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        features = kb.knowledge / kb.config.features_dir
        slugs = (
            {j["slug"] for j in corpus.journeys(kb.knowledge, kb.config.journeys_dir)}
            if kb.has("journeys_dir")
            else None
        )
        prefix = kb.config.capability_prefix
        prefixes = ("PG", "SL", "ENG", "CAP", prefix)
        strict = bool(option(kb, "feature_briefs_strict", False))
        compared = None if strict else structural_stems(kb)
        touched = compared or set()
        out: list[Finding] = []
        if not strict and compared is None:
            out.append(_no_base(kb))
        fragments = {
            key: len(rows)
            for key, rows in corpus.load_feature_row_fragments(kb.knowledge, kb.config.features_dir).items()
        }
        for path in map_files(features):
            text = path.read_text(encoding="utf-8", errors="replace")
            brief, problems = featurebrief.parse_brief(frontmatter(text))
            uses = featurebrief.capability_uses(text)
            required = strict or _stem(path) in touched
            found = featurebrief.brief_findings(
                brief,
                problems,
                uses,
                journey_slugs=slugs,
                id_prefixes=prefixes,
                required=required,
                loose=featurebrief.loose_rows(text, prefix, uses),
                rows=featurebrief.live_rows(text, prefix, uses, fragments),
            )
            for level, message, line in found:
                out.append(
                    Finding(
                        level=level,
                        message=message,
                        path=path,
                        line=line,
                        hint=COMPLETE_HINT if required else HINT,
                    )
                )
        return out
