"""Validate the component registry — the DURABLE structural tier.

A component is a thing you *build*; a slice is one planning cut of work over it, and only
the slice ships. This check enforces the shape that makes that model hold:

  A. every row parses and carries an id + a known layer
  B. ids are unique and kebab-case (they are join keys for a slice's `Components` cell)
  C. `depends_on` resolves to a registered component, and the graph is ACYCLIC (a cycle
     makes the dependency arrows meaningless and the architecture diagram undrawable)
  D. an `owns:` path is claimed by at most ONE component (two owners means the derived
     coverage reading is ambiguous)
  E. an `owns:` path is repo-relative. Paths that do NOT exist are allowed and expected:
     this is a TARGET architecture, so a component may legitimately own code that has not
     been written yet. Only obviously-malformed paths are rejected.
  F. NO ship-state. A `status:`/`shipped:`/`state:` column here is a category error —
     components are durable and can never be "done". This is the rule the registry exists to
     protect, and the header check is what keeps one from growing back.
  G. when a `diagram-layout.toml` is authored beside the registry, its placements cover the
     declared layer set exactly: every layer drawn somewhere, no placement naming a layer the
     registry does not declare, and no layer drawn twice — and every `[[placement]]` entry
     says what it is (a `band` with a `layer`, or a `duo` with `columns`), because the file's
     document order IS the draw order and a placement the viewer cannot name is a box
     silently missing from the page. The file is OPTIONAL — without one the diagram falls
     back to drawing every layer as a band in table order, which needs no invariant — but an
     authored one that misses a layer would silently omit that layer from the page, which is
     the exact failure a generated diagram exists to prevent.

Ported from `scripts/validate_components.py`; every message and the exit code are unchanged.
"""

from __future__ import annotations

import re
import tomllib
from collections import Counter
from pathlib import Path
from typing import Any

from fleet_knowledge import corpus as corpus_readers

from ._api import ERROR, Report, finding
from ._config import PlanningConfig
from ._markdown import as_list, cells, find_cycle, is_separator, read, rel

NAME = "components"

#: A component row: `id | name | layer | owns | depends_on | description`. `name` and
#: `description` are drawn by the architecture diagram and carry no invariant here.
_LAYER_COL = 2
_OWNS_COL = 3
_DEPS_COL = 4


def _parse_components(
    text: str, heading: str, cfg: PlanningConfig, out_errors: list[tuple[int | None, str]]
) -> list[tuple[int, str, str, list[str], list[str]]]:
    """Rows of a component-shaped table -> (lineno, id, layer, owns, depends_on)."""
    banned = re.compile(cfg.banned_component_column_pattern, re.I)
    rows: list[tuple[int, str, str, list[str], list[str]]] = []
    in_sec = False
    header_seen = False
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            in_sec = line.strip() == heading
            header_seen = False
            continue
        if not in_sec or not line.strip().startswith("|"):
            continue
        c = cells(line)
        if not header_seen:
            # first two table lines are the header + separator
            if c and c[0].lower() == "id":
                for col in c:
                    if banned.match(col):
                        out_errors.append(
                            (
                                i,
                                f"column `{col}` is ship-state — a component is "
                                "durable and can never be 'done'. Ship-state lives on the PROJECT "
                                "(a version of this component), never here.",
                            )
                        )
                header_seen = True
            continue
        if is_separator(c):
            continue
        if len(c) < 3:
            out_errors.append((i, f"malformed row (need id + name + layer): {line.strip()}"))
            continue
        cid, layer = c[0], c[_LAYER_COL]
        owns = [p.strip() for p in c[_OWNS_COL].split(",") if p.strip()] if len(c) > _OWNS_COL else []
        # `as_list`, the reader's own cell parser: `—` / `-` / `n/a` / empty mean "no
        # dependencies", never a component named `—`.
        deps = as_list(c[_DEPS_COL]) if len(c) > _DEPS_COL else []
        rows.append((i, cid, layer, owns, deps))
    return rows


def _parse_outcomes(
    text: str, cfg: PlanningConfig, out_errors: list[tuple[int | None, str]]
) -> list[tuple[int, str, list[str]]]:
    """Rows of `## Outcomes` -> (lineno, id, realized_by).

    A different column shape from a component row — `id | name | description | realized_by` —
    so it gets its own parser rather than a fourth optional column on `_parse_components`.
    """
    rows: list[tuple[int, str, list[str]]] = []
    in_sec = False
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            in_sec = line.strip().startswith(cfg.outcomes_heading_prefix)
            continue
        if not in_sec or not line.strip().startswith("|"):
            continue
        c = cells(line)
        if not c or c[0].lower() == "id" or is_separator(c):
            continue
        if len(c) < 4:
            out_errors.append((i, "malformed outcome row (need id + name + description + realized_by)"))
            continue
        rows.append((i, c[0], [x.strip() for x in c[3].split(",") if x.strip()]))
    return rows


def _layout_path(reg: Path) -> Path:
    """Where the diagram's topology is authored — beside the registry, per the reader's own
    derivation (`corpus.DIAGRAM_LAYOUT_FILE`). One fact, read from one place."""
    return reg.parent / corpus_readers.DIAGRAM_LAYOUT_FILE


#: The two kinds of placement a layout may declare. A placement naming a THIRD kind is a
#: finding here rather than something the viewer degrades past, because the draw order is the
#: file's own contract: a placement the viewer cannot name is a box silently missing from the
#: page, which is exactly the failure invariant G exists to prevent.
PLACEMENT_KINDS = frozenset({"band", "duo"})


def _placed_layers(layout: dict[str, Any], out_errors: list[str]) -> tuple[list[str], bool]:
    """Every layer id the layout names a drawing place for, in draw order, duplicates kept —
    and whether the file is the WHOLE wrong schema (see the pre-placement branch below).

    A layer is placed by a rail membership, a `kind = "band"` placement's `layer`, or a seat
    in a `kind = "duo"` placement's columns — walked in DOCUMENT order, which is the draw
    order. A placement that does not say what it is, or says it wrong, is a finding (appended
    to `out_errors`) and places nothing: the one defect this check can see — a layer the
    drawing misses — is about the PLACEMENTS that parsed, not the ones that did not.
    """
    placed: list[str] = []
    diagram = layout.get("diagram")
    if isinstance(diagram, dict):
        rail = diagram.get("rail_layers")
        if isinstance(rail, list):
            placed.extend(str(x) for x in rail)

    # The pre-placement schema drew bands and duos as two separate arrays of tables — and TOML
    # parses two arrays as two independent sequences, so the authored top-to-bottom order was
    # lost the moment a duo sat between bands (which the product corpus's does). A file in that
    # shape is not a sparse layout, it is the WRONG SCHEMA, and saying so beats reporting every
    # layer as undrawn on top of it.
    if "band" in layout or "duo" in layout:
        out_errors.append(
            "the layout declares `[[band]]`/`[[duo]]` tables — the schema is ONE ordered "
            '`[[placement]]` array, each entry `kind = "band"` (with `layer`) or '
            '`kind = "duo"` (with `columns`), top-to-bottom draw order = document order'
        )
        return placed, True

    blocks = layout.get("placement")
    if not isinstance(blocks, list):
        out_errors.append(
            "the layout declares no placements — every `[[placement]]` table is one step of the draw order"
        )
        return placed, False
    for ordinal, block in enumerate(blocks, 1):
        if not isinstance(block, dict):
            out_errors.append(f"placement {ordinal} is not a table")
            continue
        kind = block.get("kind")
        if not kind:
            out_errors.append(f"placement {ordinal} names no kind — a placement is a `band` or a `duo`")
            continue
        if kind not in PLACEMENT_KINDS:
            out_errors.append(f"placement {ordinal} has kind `{kind}` — a placement is a `band` or a `duo`")
            continue
        if kind == "band":
            if not block.get("layer"):
                out_errors.append(f"placement {ordinal} is a band with no layer")
                continue
            placed.append(str(block["layer"]))
            continue
        columns = block.get("columns")
        if not isinstance(columns, list) or not columns:
            out_errors.append(f"placement {ordinal} is a duo with no columns")
            continue
        for column in columns:
            if not isinstance(column, dict):
                continue
            rows = column.get("rows")
            if not isinstance(rows, list):
                continue
            for row in rows:
                if isinstance(row, list):
                    placed.extend(str(x) for x in row)
    return placed, False


def _layout_findings(reg: Path, declared: set[str]) -> list[Any]:
    """Invariant G, against the layout file when one is authored.

    The file is parsed HERE rather than read through `corpus.diagram_layout`, and that is not
    a second parser by accident: the reader DEGRADES to `None` on a malformed file, which is
    the right answer for a viewer and the wrong one for a build gate — this is the one place
    that has to hear about it.
    """
    path = _layout_path(reg)
    if not path.is_file():
        return []
    try:
        layout = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return [finding(ERROR, f"diagram layout does not parse: {exc}", path=path)]

    def with_hint(message: str) -> Any:
        hint = None
        if "draws no box for" in message:
            hint = (
                'Add a `[[placement]]` — `kind = "band"` with the layer, a `rail_layers` entry, '
                "or a seat in a duo column."
            )
        elif "unknown layer" in message:
            hint = "Fix the id to a layer the registry declares, or declare the layer there first."
        elif "exactly once" in message:
            hint = "Drop the second placement — a layer has one box on the page."
        elif "placement" in message or "[[band]]" in message:
            hint = (
                'Every `[[placement]]` is one step of the draw order: `kind = "band"` with '
                '`layer`, or `kind = "duo"` with `columns`.'
            )
        return finding(ERROR, message, path=path, hint=hint)

    shape_errors: list[str] = []
    placed, wrong_schema = _placed_layers(layout, shape_errors)
    if wrong_schema:
        # One root cause, one finding: the coverage errors a pre-placement file would also
        # raise all say the same thing — nothing is drawn — and bury the actual fix.
        return [with_hint(message) for message in shape_errors]

    return [with_hint(message) for message in [*shape_errors, *_coverage_errors(placed, declared)]]


def _coverage_errors(placed: list[str], declared: set[str]) -> list[str]:
    """The three coverage invariants, as error messages. Empty means the layout is whole."""
    errors: list[str] = []
    if missing := sorted(declared - set(placed)):
        errors.append(f"the layout draws no box for: {', '.join(missing)}")
    if stray := sorted(set(placed) - declared):
        errors.append(f"the layout names unknown layer(s): {', '.join(stray)}")
    for layer, count in sorted(Counter(placed).items()):
        if count > 1:
            errors.append(f"layer `{layer}` is placed {count} times — a layer draws exactly once")
    return errors


def registry_path(kb: Any) -> Path:
    """Where this knowledge base keeps its component registry."""
    return Path(kb.knowledge) / PlanningConfig.of(kb).component_registry


def analyse(kb: Any) -> Report:
    """Every violation of the registry's shape, in file order."""
    cfg = PlanningConfig.of(kb)
    reg = registry_path(kb)
    report = Report()
    if not reg.is_file():
        report.refusal = f"component registry missing: {rel(reg, Path(kb.root))}"
        return report

    text = read(reg)
    raw: list[tuple[int | None, str]] = []
    rows = _parse_components(text, cfg.components_heading, cfg, raw)
    if not rows:
        raw.append((None, f"`{cfg.components_heading}` table has no rows"))

    # Proposals are held to the same shape rules — an id collision or a double-claimed path
    # between the two tables is exactly the drift that makes a proposal impossible to promote
    # cleanly later.
    proposed = _parse_components(text, cfg.proposed_components_heading, cfg, raw)
    all_rows = rows + proposed

    # The closed layer set is the REGISTRY's own `## Layers` table, read through the same reader
    # the board is drawn from — a second parse here would be free to disagree with it, and a
    # vocabulary in the package would be one product's architecture imposed on every corpus.
    layers, _layer_of = corpus_readers.component_layers(reg.parent, reg.name)
    declared = {str(row["id"]) for row in layers}
    if not declared and all_rows:
        raw.append(
            (
                None,
                "the registry declares no layers — a `## Layers` table (`id | name | description`) "
                "is the closed set every component's `layer` is checked against",
            )
        )

    id_re = re.compile(cfg.component_id_pattern)
    seen: dict[str, int] = {}
    owner_of: dict[str, str] = {}
    graph: dict[str, list[str]] = {}

    for lineno, cid, layer, owns, deps in all_rows:
        if not id_re.match(cid):
            raw.append((lineno, f"id `{cid}` is not kebab-case"))
        if cid in seen:
            raw.append((lineno, f"duplicate component id `{cid}` (also line {seen[cid]})"))
        else:
            seen[cid] = lineno
        # With no declared set the registry has been told once, above; a per-row "unknown
        # layer" would list an empty allowed set N times over.
        if declared and layer not in declared:
            raw.append(
                (
                    lineno,
                    f"`{cid}` has unknown layer `{layer}` (allowed: {', '.join(sorted(declared))})",
                )
            )
        elif layer in cfg.non_component_layers:
            raw.append(
                (
                    lineno,
                    f"`{cid}` sits in `{layer}`, which holds no components — "
                    "it is drawn from `## Outcomes` / `## External`. Pick a real layer.",
                )
            )
        for p in owns:
            if p.startswith("/") or ".." in p:
                raw.append((lineno, f"`{cid}` owns malformed path `{p}` (must be repo-relative)"))
                continue
            if p in owner_of and owner_of[p] != cid:
                raw.append((lineno, f"path `{p}` is owned by both `{owner_of[p]}` and `{cid}`"))
            owner_of[p] = cid
        graph[cid] = deps

    for lineno, cid, _layer, _owns, deps in all_rows:
        for d in deps:
            if d not in seen:
                raw.append((lineno, f"`{cid}` depends_on `{d}`, which is not a registered component"))

    # An outcome's `realized_by` is the ONLY edge from the narrative axis back into the things
    # that exist. This checks that the named components EXIST, never that the set is complete —
    # an outcome is a curated claim, not a covering partition of the registry, and a
    # completeness rule here would turn the narrative axis into an inventory.
    for lineno, oid, realized in _parse_outcomes(text, cfg, raw):
        if not realized:
            raw.append(
                (
                    lineno,
                    f"outcome `{oid}` names no `realized_by` component — "
                    "an outcome that nothing realises is a claim with no evidence",
                )
            )
        for r in realized:
            if r not in seen:
                raw.append((lineno, f"outcome `{oid}` is realized_by `{r}`, which is not a registered component"))

    if cyc := find_cycle(graph):
        raw.append((None, f"component dependency cycle: {' -> '.join(cyc)}"))

    for line, message in raw:
        report.findings.append(
            finding(
                ERROR,
                message,
                path=reg,
                line=line,
                hint=_hint(message),
                command=_command(message, cfg),
            )
        )

    # The declared set the layout must cover is the same Layers table, read once above.
    report.findings.extend(_layout_findings(reg, declared))
    report.notes.append(
        f"{len(rows)} components (+{len(proposed)} proposed) across {len({r[2] for r in all_rows})} layers"
    )
    return report


def _hint(message: str) -> str | None:
    if "is ship-state" in message:
        return "Delete the column — a component is durable; ship-state belongs on the slice that ships it."
    if "not a registered component" in message:
        return "Register the component first, or correct the id to one that already exists."
    if "dependency cycle" in message:
        return "Break the cycle by inverting one edge — a component graph must be acyclic to be drawable."
    if "is owned by both" in message:
        return "One path, one owner: drop the claim from whichever component does not build it."
    if "unknown layer" in message:
        return "Use a layer from the registry's `## Layers` table, or add the new layer there deliberately."
    if "declares no layers" in message:
        return "Add a `## Layers` table to the registry naming every layer its components sit in."
    if "not kebab-case" in message:
        return "Component ids are join keys — rename to lower-case words joined by single hyphens."
    return None


def _command(message: str, cfg: PlanningConfig) -> str | None:
    if "not a registered component" in message:
        return cfg.command("component_create")
    return None


class ComponentsCheck:
    """The component registry parses, its ids are unique, its graph is acyclic, it holds no ship-state,
    and an authored diagram layout covers the layer set exactly."""

    name = NAME
    title = "Component registry"
    description = (
        "The component registry is the structural map: what exists and where a thing belongs. This check "
        "keeps it usable as a join key and as a graph — ids unique and kebab-case, layers drawn from a "
        "closed set, `owns:` paths claimed by exactly one component, `depends_on` edges resolving and "
        "acyclic, every outcome's `realized_by` naming a real row. It also refuses a ship-state column, "
        "because a component is DURABLE: it can never be 'done', and a `Status` column here would restate "
        "on the wrong tier what only a slice can answer. And when a `diagram-layout.toml` is authored "
        "beside the registry, every declared layer is placed in it exactly once and no placement names a "
        "layer the registry does not declare."
    )

    def applies(self, kb: Any) -> bool:
        return bool(kb.has("components_registry"))

    def run(self, kb: Any) -> list[Any]:
        return analyse(kb).findings


CHECK = ComponentsCheck()


def cli(kb: Any) -> int:
    """Reproduce `scripts/validate_components.py`'s stdout and exit code exactly."""
    report = analyse(kb)
    if report.refusal:
        print(report.refusal)
        return 1
    errors = report.errors
    if errors:
        print(f"component registry: {len(errors)} error(s)\n")
        for e in errors:
            # Every finding here carries the registry path, but `Finding.path` is optional in
            # the model, so the renderer degrades rather than assuming.
            name = e.path.name if e.path else ""
            where = f"{name}:{e.line}" if e.line else name
            print(f"  {where}: {e.message}")
        return 1
    print(f"component registry OK — {report.notes[0]}; graph is acyclic")
    return 0
