"""The docs checks: the page validator and the computed coverage report.

Both are silent until a repository answers the `docs` slot, and that is the whole contract.
An unfilled optional slot means the repository has no user-facing docs program; a gate over a
page tree that does not exist would be the red build over absent ground this package refuses
everywhere else. `applies()` reads the answer itself — the slot's `fill` must resolve — so
"the slot is unfilled" and "the checks do not run" are the same statement.

`docs-pages` is the validator: each page's frontmatter names one of the four kinds, its
`covers` ids resolve to real capabilities, its `verified_by` ids resolve to real journeys or
PRDs, its internal links resolve, a public home carries no secret shape or internal hostname,
and a page generated from a source names a source that exists. A PRD's `docs_impact` is read
here too: a list of pages that must resolve, or `none` with a reason.

`docs-coverage` is the COMPUTED report — never a committed aggregate file, which would
conflict on nearly every PR. It reports a capability whose area declares a surface but which
no page, no `Documented in` cell and no `docs_impact` names; areas exempted by the home's
named baseline are not reported. It reads the optional `Documented in` column on a feature map
and the `documented_in:` key on a journey as LINKAGES only — never as ship-state.

Stdlib only.
"""

from __future__ import annotations

import re
from pathlib import Path

from fleet_knowledge.config import KnowledgeBase
from fleet_knowledge.markdown import field, frontmatter, listfield
from fleet_knowledge.runner import Finding

from ._harness import (
    PAGE_KINDS,
    Area,
    Home,
    feature_areas,
    journey_documented_in,
    journey_slugs,
    links,
    load_homes,
    pages,
    prd_ids,
    resolves_link,
    slot_fill_paths,
)

#: Secret shapes that must never appear in a public home. Deliberately SHAPE-based, not an
#: exhaustive scanner: a page that carries one of these has already leaked something, and the
#: finding names which shape so the author can find it.
_SECRETS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("an AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("a private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("a GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("an API secret", re.compile(r"\bsk-(?:live|test)[A-Za-z0-9]{16,}\b")),
    (
        "an assigned secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|client[_-]?secret|password|access[_-]?token)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,}"
        ),
    ),
)

#: Hosts that are only reachable from inside — never in a page a customer reads.
_INTERNAL_HOST = re.compile(
    r"\b(?:localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|"
    r"[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:internal|local|corp|cluster\.local))\b",
    re.I,
)


class DocsPagesCheck:
    """Validate every page in an answered docs home."""

    name = "docs-pages"
    title = "docs pages — frontmatter, ids, links and secrets"
    description = (
        "Each page in a `docs` home names one of the four kinds and resolves its `covers`, "
        "`verified_by` and internal links; a public home carries no secret shape or internal "
        "hostname; a generated page names a source that exists; and a PRD's `docs_impact` is "
        "either resolvable pages or `none` with a reason."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        return bool(slot_fill_paths(kb))

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        homes, out = load_homes(kb)
        known_caps = {cap for area in feature_areas(kb) for cap in area.caps}
        slugs = journey_slugs(kb)
        prds = prd_ids(kb)
        for home in homes:
            out.extend(_check_home(home, kb, known_caps, slugs, prds))
        out.extend(_check_prds(kb))
        out.extend(_orphans(kb, homes))
        return out


def _check_home(home: Home, kb: KnowledgeBase, caps: set[str], slugs: set[str], prds: set[str]) -> list[Finding]:
    out: list[Finding] = []
    for source, generated in home.generated:
        for rel, what in ((source, "source"), (generated, "generated page")):
            if not (kb.root / rel).exists():
                out.append(
                    Finding(
                        level="error",
                        message=f"docs home `generated:` names a {what} `{rel}` that does not exist",
                        path=home.doc,
                        hint="Fix the mapping, or delete it if the page is no longer generated.",
                    )
                )
    for page in pages(home):
        text = page.read_text(encoding="utf-8", errors="ignore")
        fm = frontmatter(text)
        if not fm:
            out.append(
                Finding(
                    level="error",
                    message="docs page has no YAML frontmatter",
                    path=page,
                    hint="Declare at least `kind:` — one page is one of the four kinds.",
                )
            )
            continue
        kind = field(fm, "kind")
        if kind not in PAGE_KINDS:
            out.append(
                Finding(
                    level="error",
                    message=f"docs page declares `kind: {kind or '(none)'}`, not one of {', '.join(PAGE_KINDS)}",
                    path=page,
                    hint="One page is one kind: a tutorial, a how-to, a reference or an explanation.",
                )
            )
        for cap in listfield(fm, "covers"):
            if cap not in caps:
                out.append(
                    Finding(
                        level="error",
                        message=f"`covers` names `{cap}`, which is not a capability in any feature map",
                        path=page,
                        hint="Point it at a real capability id, or drop the entry.",
                    )
                )
        for verifier in listfield(fm, "verified_by"):
            if verifier not in slugs and verifier not in prds:
                out.append(
                    Finding(
                        level="error",
                        message=f"`verified_by` names `{verifier}`, which is neither a journey nor a PRD",
                        path=page,
                        hint="A page is verified by a journey slug or a PRD number that exists.",
                    )
                )
        for target in links(text):
            if not resolves_link(page, target):
                out.append(
                    Finding(
                        level="error",
                        message=f"internal link `{target}` resolves nowhere",
                        path=page,
                        hint="Point it at the page's real path, or drop the link.",
                    )
                )
        source = field(fm, "generated_from")
        if source and not (kb.root / source).exists():
            out.append(
                Finding(
                    level="error",
                    message=f"`generated_from: {source}` names a source that does not exist",
                    path=page,
                    hint="A generated reference points at the source it is generated from.",
                )
            )
        if home.public:
            out.extend(_leaks(page, text))
    return out


def _external(target: str) -> bool:
    return target.startswith("#") or bool(re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I))


def _referenced(kb: KnowledgeBase, homes: list[Home]) -> set[Path]:
    """Every page path some linkage or in-home link points at, resolved."""
    refs: set[Path] = set()
    for area in feature_areas(kb):
        for targets in area.documented.values():
            refs |= {(kb.root / t).resolve() for t in targets}
    for _journey, target in journey_documented_in(kb):
        refs.add((kb.root / target).resolve())
    if kb.config.prds_dir:
        for prd in kb.glob(f"{kb.config.prds_dir}/*/prd.md"):
            fm = frontmatter(prd.read_text(encoding="utf-8", errors="ignore"))
            for target in listfield(fm, "docs_impact"):
                refs.add((kb.root / target.strip().strip("`[]")).resolve())
    for home in homes:
        for page in pages(home):
            for target in links(page.read_text(encoding="utf-8", errors="ignore")):
                if _external(target):
                    continue
                clean = target.split("#", 1)[0].split("?", 1)[0]
                if clean:
                    refs.add((page.parent / clean).resolve())
    return refs


def _orphans(kb: KnowledgeBase, homes: list[Home]) -> list[Finding]:
    """A page no linkage and no other page reaches — written, and reachable from nowhere."""
    refs = _referenced(kb, homes)
    out: list[Finding] = []
    for home in homes:
        for page in pages(home):
            fm = frontmatter(page.read_text(encoding="utf-8", errors="ignore"))
            if listfield(fm, "covers") or field(fm, "generated_from") or page.resolve() in refs:
                continue
            out.append(
                Finding(
                    level="warning",
                    message=f"docs page `{page.name}` is an orphan — no page links it and no linkage names it",
                    path=page,
                    hint="Link it from the home or an index, or give it a `covers:` entry.",
                )
            )
    return out


def _leaks(page: Path, text: str) -> list[Finding]:
    out: list[Finding] = []
    for name, pattern in _SECRETS:
        if pattern.search(text):
            out.append(
                Finding(
                    level="error",
                    message=f"public docs page carries {name}",
                    path=page,
                    hint="A secret never belongs in a page a customer reads; remove it and rotate it.",
                )
            )
    if _INTERNAL_HOST.search(text):
        out.append(
            Finding(
                level="error",
                message="public docs page names an internal hostname",
                path=page,
                hint="Reach a public page's endpoints through the product's public surface.",
            )
        )
    return out


def _check_prds(kb: KnowledgeBase) -> list[Finding]:
    out: list[Finding] = []
    if not kb.config.prds_dir:
        return out
    for prd in kb.glob(f"{kb.config.prds_dir}/*/prd.md"):
        fm = frontmatter(prd.read_text(encoding="utf-8", errors="ignore"))
        impact = listfield(fm, "docs_impact")
        if not impact:
            continue
        if [x.lower() for x in impact] == ["none"]:
            if not field(fm, "docs_impact_reason"):
                out.append(
                    Finding(
                        level="error",
                        message="PRD says `docs_impact: none` with no `docs_impact_reason`",
                        path=prd,
                        hint="Say why this PRD changes no user-facing page; a bare `none` hides a missed page.",
                    )
                )
            continue
        for target in impact:
            if not (kb.root / target.strip().strip("`[]")).exists():
                out.append(
                    Finding(
                        level="error",
                        message=f"`docs_impact` names `{target}`, which does not exist",
                        path=prd,
                        hint="A docs-impact entry is a page path that resolves.",
                    )
                )
    return out


class DocsCoverageCheck:
    """The computed docs coverage report — capabilities with a surface and no page."""

    name = "docs-coverage"
    title = "docs coverage — every surfaced capability has a page"
    description = (
        "A capability whose feature area declares a surface needs a page: one whose `covers` "
        "names it, a feature map's `Documented in` cell, a journey's `documented_in:`, or a "
        "PRD's `docs_impact`. Areas the home's named baseline exempts are not reported. "
        "Computed on every run — never a committed aggregate file."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        return bool(slot_fill_paths(kb))

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        homes, _problems = load_homes(kb)
        areas = feature_areas(kb)
        linked = _linked_caps(kb, areas)
        by_area = {area.name: area for area in areas}
        exempt = _baseline_names(homes)
        out: list[Finding] = []
        for area in areas:
            if not area.surfaces or area.name in exempt:
                continue
            for cap in area.caps:
                if cap in linked:
                    continue
                out.append(
                    Finding(
                        level="warning",
                        message=(
                            f"`{cap}` in area `{area.name}` has a surface but no page — "
                            "no page covers it, no `Documented in` cell names one, and no PRD's "
                            "`docs_impact` admits it"
                        ),
                        path=area.path,
                        hint=(
                            "Write the page and list the capability under its `covers:`, "
                            "or exempt the area in the baseline."
                        ),
                    )
                )
        out.extend(_exempted_but_missing(homes, by_area))
        out.extend(_link_findings(kb))
        return out


def _linked_caps(kb: KnowledgeBase, areas: list[Area]) -> set[str]:
    """Every capability some page or linkage names, across all homes and PRDs."""
    linked: set[str] = set()
    homes, _ = load_homes(kb)
    known = {cap for area in areas for cap in area.caps}
    for home in homes:
        for page in pages(home):
            fm = frontmatter(page.read_text(encoding="utf-8", errors="ignore"))
            linked |= {c for c in listfield(fm, "covers") if c in known}
    for area in areas:
        for cap, targets in area.documented.items():
            if targets:
                linked.add(cap)
    return linked


def _baseline_names(homes: list[Home]) -> set[str]:
    """The area names every home's named baseline exempts from the coverage report."""
    names: set[str] = set()
    for home in homes:
        if home.baseline is None or not home.baseline.is_file():
            continue
        for line in home.baseline.read_text(encoding="utf-8", errors="ignore").splitlines():
            name = line.strip()
            if name and not name.startswith("#"):
                names.add(name)
    return names


def _exempted_but_missing(homes: list[Home], by_area: dict[str, Area]) -> list[Finding]:
    """Advisory: a baseline names an area this corpus no longer has, so the ratchet can shrink."""
    out: list[Finding] = []
    for home in homes:
        if home.baseline is None or not home.baseline.is_file():
            continue
        for line in home.baseline.read_text(encoding="utf-8", errors="ignore").splitlines():
            name = line.strip()
            if not name or name.startswith("#"):
                continue
            if name not in by_area:
                out.append(
                    Finding(
                        level="advisory",
                        message=f"docs coverage baseline names area `{name}`, which is not in this corpus",
                        path=home.baseline,
                        hint="Delete the line: an exemption for ground that no longer exists stops being a ratchet.",
                    )
                )
    return out


def _link_findings(kb: KnowledgeBase) -> list[Finding]:
    """Every `Documented in` cell and `documented_in:` key must name a page that resolves."""
    out: list[Finding] = []
    for area in feature_areas(kb):
        for cap, targets in area.documented.items():
            for target in targets:
                if not (kb.root / target).exists():
                    out.append(
                        Finding(
                            level="error",
                            message=f"`{cap}`'s `Documented in` names `{target}`, which does not exist",
                            path=area.path,
                            hint="The linkage is a page path; point it at the real page.",
                        )
                    )
    for journey, target in journey_documented_in(kb):
        if not (kb.root / target).exists():
            out.append(
                Finding(
                    level="error",
                    message=f"`documented_in` names `{target}`, which does not exist",
                    path=journey,
                    hint="The linkage is a page path; point it at the real page.",
                )
            )
    return out
