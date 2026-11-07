"""The knowledge base as ENTITIES AND RELATIONS — one shape for six kinds, served not rendered.

This is what `browser.py` used to bake into a second HTML page, turned into a model something
else can serve. The knowledge in it is the same knowledge: requirement rows, feature maps,
journeys, the component registry, decision records. What is gone is the second *renderer* — the
board owns the visualization now, and a corpus with two pages is a corpus with two palettes,
two escapers and two ideas of what a state colour means.

**One shape, whatever the kind.** A requirement, a capability, a decision, a component, a
journey and a feature area all serialise as `{kind, id, name, summary, facts, chips, flags}`.
That is the whole of the model, and it is what makes the next kind — architecture — cost no new
endpoint and no new page type. A kind that needed a field of its own would be a kind this model
does not fit, and the answer would be to change the model rather than to widen it by one.

**Relations are authored ONCE and served from BOTH ends.** Backstage's rule, and the reason it is
not negotiable here: an edge stored twice is an edge that disagrees with itself the first time
somebody edits one side. Every edge below is read off the side that authors it — a PRD's
`implements:`, a feature map's `Ships in`, a register's `Needs` column, a journey's `covers:` —
and `Graph.relations` answers with the forward edge and its inverse together. Half an edge is how
a reader concludes nothing depends on a thing.

**Three sizes, and the split is load-bearing.** A LIST item carries an id, a name, one clipped
sentence, chips and the facets it can be filtered on. A DETAIL carries facts and relations. PROSE
is a third request that nothing else pays for. 1,849 requirements and 1,237 capabilities are
affordable on exactly that arrangement and on no other: a list that carried statements is 1.4 MB
before anything is drawn.

**Nothing here decides what to DO about an entity except `findings`**, and that one function
emits the row shape `board.actions` already emits — `{group, sev, id, title, why, cmd, cmdKey,
built}` — so a page renders a knowledge finding through the same `actionItems()` path it renders
a program finding through. No new component, by construction rather than by discipline.

**The commands are the caller's**, exactly as they are on the board: `findings` takes a
`board.Vocabulary` and asks it for the command behind each finding key. A deployment whose
vocabulary names none gets a finding that states the problem and hands over nothing, which is
what `cmdKey` is carried for. Baking one project's routing command in here would couple this
package to that project's command surface — the coupling `board.py`'s header refuses at length,
and the reason a product name does not appear anywhere in this package's source.

**Pure over VALUES, with one disk reader beside it.** `Corpus` is a bag of rows; `Corpus.read`
fills one from a checkout. The served path fills one from typed database columns instead and gets
the same entities, which is the only way the deployed page and a local run can be the same
reading.

Stdlib only.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import corpus as corpus_mod
from . import requirements as requirements_mod
from .board import Vocabulary
from .checks.commitments.context import Context
from .checks.commitments.options import CommitmentsConfig
from .checks.commitments.registers import is_cut, need_scope
from .config import Config
from .markdown import clip, plain

__all__ = [
    "KINDS",
    "SECTIONS",
    "Corpus",
    "Entity",
    "Graph",
    "Relation",
    "RelationGroup",
    "findings",
    "startable_ids",
]

# ─────────────────────────── the vocabulary ───────────────────────────

#: Every kind this model serves, in the order a page walks them. `architecture` is the next
#: one and lands here as a seventh string — no route, no page type, no branch in a serialiser.
KINDS: tuple[str, ...] = ("journey", "area", "capability", "component", "requirement", "decision")

#: Which of the page's four sections a kind belongs to. The MEMBERSHIP is a fact about the
#: model and lives here; the section's TITLE and its question are the page's own words and do
#: not. Delivery — programs, slices, PRDs — is the existing board and is not a knowledge kind.
SECTIONS: Mapping[str, str] = {
    "journey": "product",
    "area": "product",
    "capability": "product",
    "component": "system",
    "requirement": "commitments",
    "decision": "commitments",
}

#: How long a LIST sentence may be. One clipped sentence, and the number is the same order as
#: `board.js`'s own `firstSentence` cap — a list row is one line of a table, and a second line
#: of prose in it is the thing the three-sizes rule exists to keep out.
SENTENCE_CHARS = 300

#: Register kinds whose rows are usually true by CONSTRUCTION rather than by work. Nothing
#: citing one is a documentation gap, not a build one — which is a different finding and a
#: quieter severity than an unclaimed `requirement` row.
UNCITED_KINDS: tuple[str, ...] = ("invariant", "constraint")

#: Register kinds that are NOT work and must never carry a call to action. An `excluded` row
#: records a refusal and an `accepted` row records a cost taken on purpose; a Start button under
#: either argues against the row it sits beneath. Carried as flags so the page can render the
#: stated section instead — "Deliberately not built" / "A cost we took on purpose". The set is
#: the grammar's (`requirements.SETTLED_KINDS`), so this view and the status derivation cannot
#: disagree about which kinds are work.
SETTLED_KINDS: frozenset[str] = requirements_mod.SETTLED_KINDS

#: Severities, borrowed from `board.actions` so one page has one ordering. 2 is "there is
#: something to do here", 3 is "worth knowing, never worth stopping anything".
SEV_ACTIONABLE = 2
SEV_QUIET = 3

# Chip classes are `fleet.css`'s, and this module mints none. `complete` / `unproven` / `attn` /
# `kind` / `""` is the whole palette a knowledge row needs; a new one would be a second design
# language arriving through a payload.
_DISPOSITION_CLS: Mapping[str, str] = {"adopted": "complete", "rejected": "attn", "open": "unproven"}

# `Context` requires a root. NEITHER predicate this module borrows from the commitments checks
# reads one: `is_cut` compares a cell against `cfg.current_line`, and `need_scope` walks a claims
# mapping this module builds from rows it already holds. A path that cannot exist is passed so
# that a predicate which ever DID reach for the filesystem fails loudly here instead of quietly
# reading whatever directory the process happens to be standing in —
# `test_the_startable_predicate_touches_no_filesystem` is the assertion.
_NOWHERE = Path("/nonexistent/fleet-knowledge/no-corpus-here")


# ─────────────────────────── the model ───────────────────────────


@dataclass(frozen=True, slots=True)
class Entity:
    """One knowledge entity, whatever its kind.

    `name` is the SHORTEST HONEST LABEL, which for two kinds is the group rather than a title:
    a register row and a capability row are both a paragraph with an id, and neither has a name
    of its own — so a requirement is named by its domain and a capability by its feature area,
    and the paragraph is the summary. A component, a journey, an area and a decision each have a
    real name and carry it.

    `facts` are ordered pairs because a page prints them in the order the model states them;
    a mapping would let the serialiser choose, and it would choose differently per language.
    """

    kind: str
    id: str
    name: str
    summary: str
    facts: tuple[tuple[str, str], ...] = ()
    chips: tuple[tuple[str, str], ...] = ()  # (text, css class)
    flags: Mapping[str, bool] = field(default_factory=dict)
    #: The facet values this row can be filtered on, by facet name. Carried on the LIST item
    #: because a facet the client cannot see is a filter it cannot offer — and computed here
    #: rather than in a query, so the same row filters identically wherever it is read.
    facets: Mapping[str, str] = field(default_factory=dict)
    sev: int = SEV_QUIET

    def as_dict(self) -> dict[str, Any]:
        """The wire shape — contract §1, and nothing beyond it but `facets` and `sev`.

        `facets` is what a per-kind filter is applied to and `sev` is what orders a list; both
        are values rather than prose, so neither costs the list rule anything.
        """
        return {
            "kind": self.kind,
            "id": self.id,
            "name": self.name,
            "summary": self.summary,
            "facts": [list(f) for f in self.facts],
            "chips": [{"text": t, "cls": c} for t, c in self.chips],
            "flags": dict(self.flags),
            "facets": dict(self.facets),
            "sev": self.sev,
        }


@dataclass(frozen=True, slots=True)
class Relation:
    """One end of one edge, as a reader of the OTHER end sees it.

    Never stored: `Graph` holds the authored edge once and produces these on the way out, in
    both directions, from the one `VERBS` table. There is no inverse to author and therefore no
    inverse to forget.
    """

    verb: str
    kind: str
    id: str
    name: str
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return {"verb": self.verb, "kind": self.kind, "id": self.id, "name": self.name, "summary": self.summary}


@dataclass(frozen=True, slots=True)
class Edge:
    """An authored edge: `(from) --verb--> (to)`. The one direction somebody wrote down."""

    verb: str
    src_kind: str
    src_id: str
    dst_kind: str
    dst_id: str


#: Forward verb -> the verb the same edge reads as from the other end. Contract §2's table,
#: and the ONLY place an inverse is named. A pair added here is served from both ends with no
#: other change; an edge whose verb is not here is a bug rather than a one-directional edge.
VERBS: Mapping[str, str] = {
    "claims": "claimedBy",  # PRD frontmatter `implements:`
    "shipsIn": "ships",  # feature map `Ships in`
    "needs": "neededBy",  # register `Needs`, and a feature map's `Needs`
    "moves": "settledBy",  # a decision record's `**Commitments.**` line
    "builds": "builtBy",  # a feature map's `components:`, resolved through the registry
    "covers": "coveredBy",  # a journey's `covers:`, and a map's `Tested by`
    "holds": "inArea",  # which feature map a capability row is written in
}
#: NOT here, and deliberately: `component --inLayer--> layer`. A layer is not one of the six
#: kinds, so the edge would resolve to an end with no entity behind it — a relation that
#: renders as a bare slug and links nowhere. The layer travels as a FACT and as a FACET until
#: `architecture` lands as the seventh kind and brings the layer with it as an entity.


# ─────────────────────────── relation groups ───────────────────────────
#
# A DETAIL RESPONSE IS GROUPS, NOT EDGES, and the grouping is decided here rather than by
# whoever is drawing it. Three things travel together — which groups exist, what order they
# read in, and what each one is CALLED — and none of them survives being split: a client that
# grouped would have to name its groups, the next client would name them differently, and two
# renderings of one corpus would disagree about what an edge is. `board.js` keeps a table of the
# same headings as a FLOOR for a group served without a label; a served label wins outright.
#
# **AND THE EMPTY GROUP IS THE WHOLE REASON THIS IS A TABLE.** A grouping derived from the edges
# an entity happens to have can only ever emit the groups it found — so "Claimed by: nothing",
# which is the single most useful sentence on a requirement's page, would be unsayable, and a
# reader seeing no heading concludes the edge is not modelled rather than that it is not there.
# That is the same defect as half an edge, arriving from the other side.


#: What each verb is called where a person reads it. Both ends of every `VERBS` pair, because a
#: group is served from either side and a heading written for one direction only leaves the
#: other under a raw camelCase verb.
RELATION_LABELS: Mapping[str, str] = {
    "claims": "Claims",
    "claimedBy": "Claimed by",
    "shipsIn": "Ships in",
    "ships": "Ships",
    "needs": "Needs",
    "neededBy": "Needed by",
    "moves": "Moves",
    "settledBy": "Settled by",
    "builds": "Builds",
    "builtBy": "Built by",
    "covers": "Covers",
    "coveredBy": "Covered by",
    "holds": "Holds",
    "inArea": "In feature",
}

#: WHERE THE EDGE UNDER EACH HEADING WAS AUTHORED — one sentence, and it is the answer to the
#: question an empty group provokes. "Claimed by: nothing" is only actionable beside "derived
#: from every PRD's `implements:`", which says what a reader would have to write to change it;
#: without that, an empty group is indistinguishable from a corpus that models no such edge.
RELATION_NOTES: Mapping[str, str] = {
    "claims": "This PRD's `implements:`.",
    "claimedBy": "Derived from every PRD's `implements:`. Nothing on this row authors it.",
    "shipsIn": "The feature map's `Ships in` column on this row.",
    "ships": "Every capability row whose `Ships in` names this PRD.",
    "needs": "This row's own `Needs` column.",
    "neededBy": "Every row whose `Needs` column names this one.",
    "moves": "This decision record's `**Commitments.**` line.",
    "settledBy": "Every decision record whose `**Commitments.**` line names this row.",
    "builds": "The feature maps that name this component under `components:`, resolved onto the rows of each.",
    "builtBy": "The `components:` of the feature map this row is written in.",
    "covers": "This journey's `covers:`, unioned with the map's `Tested by`.",
    "coveredBy": "A journey's `covers:`, or this row's `Tested by`.",
    "holds": "Every capability row written in this feature map.",
    "inArea": "The feature map this row is written in.",
}

#: WHICH GROUPS A KIND HAS AT ALL, in the order they read — and therefore which ones are served
#: EMPTY. Derived from `_edges`: every triple it can produce puts its verb on the source kind
#: and its inverse on the destination kind, minus the `prd` end, which is not one of the six
#: and so has no page for a group to appear on.
#:
#: Declared rather than computed from the corpus in hand, and that is the point: a corpus whose
#: registers happen to author no `Needs` yet would otherwise lose the heading from every
#: requirement page at once, and gain it back the day somebody writes one. The set of questions
#: a page answers is a property of the model; only the answers come from the reading.
#:
#: `test_every_edge_the_reader_can_produce_has_a_group_to_land_in` holds this against what
#: `_edges` actually emits, in both directions, so a seventh kind cannot arrive without one.
RELATION_ENDS: Mapping[str, tuple[str, ...]] = {
    "journey": ("covers",),
    "area": ("holds",),
    "capability": ("inArea", "shipsIn", "needs", "neededBy", "builtBy", "coveredBy"),
    "component": ("builds",),
    "requirement": ("claimedBy", "needs", "neededBy", "settledBy"),
    "decision": ("moves",),
}


@dataclass(frozen=True, slots=True)
class RelationGroup:
    """One heading on an entity's page, and every edge that reads under it. Possibly none."""

    verb: str
    label: str
    note: str
    items: tuple[Relation, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "verb": self.verb,
            "label": self.label,
            "note": self.note,
            "items": [item.as_dict() for item in self.items],
        }


# ─────────────────────────── the input ───────────────────────────


@dataclass(frozen=True)
class Corpus:
    """The rows every entity is derived from — a bag of values, never a filesystem.

    Two callers fill one. `Corpus.read` fills it from a checkout, which is what a test and a
    local run use. The deployed service fills it from typed database columns, because it has no
    checkout — and it gets the same entities out, which is the whole reason this takes values.

    Every field defaults to empty: a corpus without journeys is a corpus, not a failure, and a
    reader that required all six would refuse to serve the five a project does have.
    """

    #: `requirements.load_registers` rows, each widened with its own `id`.
    requirements: Sequence[Mapping[str, Any]] = ()
    #: `corpus.prds` rows — `n`, `title`, `status`, `impl`.
    prds: Sequence[Mapping[str, Any]] = ()
    #: `corpus.features` capability rows, each widened with the `area` slug it was read under.
    capabilities: Sequence[Mapping[str, Any]] = ()
    #: One row per feature map: `area`, `name`, `desc`, `kind`, `components`, `journeys`.
    areas: Sequence[Mapping[str, Any]] = ()
    #: `corpus.journeys` merged with `corpus.journey_detail`.
    journeys: Sequence[Mapping[str, Any]] = ()
    #: `corpus.components` rows.
    components: Sequence[Mapping[str, Any]] = ()
    #: `corpus.component_layers`'s first return — `{id, name, description}` in drawing order.
    layers: Sequence[Mapping[str, str]] = ()
    #: The registry's `## External` table — the customer's side of the boundary. Its own axis
    #: rather than phantom component rows, because an external system owns nothing here.
    externals: Sequence[Mapping[str, Any]] = ()
    #: The registry's `## Outcomes` table — the business-value axis, realized BY components.
    outcomes: Sequence[Mapping[str, Any]] = ()
    #: The parsed `diagram-layout.toml`, when the corpus authors one. `None` is the ordinary
    #: case and means the viewer's generic fallback — never an error.
    layout: Mapping[str, Any] | None = None
    #: `corpus.decisions` rows.
    decisions: Sequence[Mapping[str, Any]] = ()
    #: Requirement ids a register's `## Known violations` table disproves. Without these a
    #: shipped-but-violated prerequisite reads as built, and the startable frontier grows in
    #: the UNSAFE direction — it offers work whose ground is known not to hold.
    disproofs: Sequence[str] = ()
    #: The commitments family's own options — `current_line` and `claim_history` are what the
    #: two borrowed predicates read, and a corpus that has cut over to v2 must not be judged
    #: against v1's line.
    commitments: CommitmentsConfig = field(default_factory=CommitmentsConfig)
    #: The startable frontier, when the caller already has it. `None` means "work it out",
    #: which is what a disk read does.
    #:
    #: **It is a parameter because the answer depends on the corpus's own `fleet.toml`.** Which
    #: release line is being built is `commitments.current_line`, and a caller filling this
    #: object from a database holds rows but not that document — so it is answered once, where
    #: the corpus describes itself, and travels with the reading rather than being guessed at
    #: serve time. Supplied, it is taken verbatim: a second derivation against a defaulted
    #: config is the silent wrong answer this field exists to prevent.
    startable: frozenset[str] | None = None

    @classmethod
    def read(cls, root: Path, config: Config | None = None, repo: Path | None = None) -> Corpus:
        """Fill one from a checkout. The corpus's own `Config` says what everything is called.

        Threaded for the reason `board.build` takes one: every reader below opened its file by
        hardcoded name once, and a corpus that names its registers something else indexed as
        though it were empty — a page that is whole, well formed, and about nothing.

        `repo` is the REPOSITORY root, which only the component reading needs: `owns:` paths are
        repo-relative, and deriving which of them exist needs the tree they are relative TO.
        Omitted — and the served path has no checkout to hand — a component's `present` degrades
        to `[]`, which is what the reader's contract says a viewer does.
        """
        cfg = config or Config()
        # `shells=True`: a fragment-backed register whose rendered `.md` is gitignored is read through its shell.
        rows, _findings = requirements_mod.load_registers(root, dir_name=cfg.requirements_dir, shells=True)
        layers, layer_of = corpus_mod.component_layers(root, cfg.components_registry)
        jdetail = corpus_mod.journey_detail(root, cfg.journeys_dir)
        journeys = [{**j, **jdetail.get(j["slug"], {})} for j in corpus_mod.journeys(root, cfg.journeys_dir)]
        areas = corpus_mod.features(
            root,
            layers,
            layer_of,
            {j["slug"] for j in journeys},
            corpus_mod.covers_inverse(jdetail),
            corpus_mod.feature_families(root, cfg.coverage_ledger),
            tier_of=corpus_mod.feature_tiers(root, cfg.coverage_ledger),
            features_dir=cfg.features_dir,
            aliases_file=cfg.capability_aliases,
            capability_prefix=cfg.capability_prefix,
        )
        disproofs = _disproofs(root, cfg.requirements_dir)
        return cls(
            requirements=[{"id": rid, **row} for rid, row in rows.items()],
            prds=corpus_mod.prds(root, cfg.prds_dir),
            capabilities=[{**cap, "area": a["area"]} for a in areas for cap in a["caps"]],
            # `name` is deliberately NOT derived here. The H1-to-Project-name rule belongs to
            # the projection that writes the tracker Project (`dispatch.prdprojection.area_name`),
            # the served path reads the column that rule already wrote, and a second copy of it
            # here is exactly the drift this package argues against everywhere else. A disk read
            # stands the slug in its place and says so.
            areas=[{**{k: v for k, v in a.items() if k != "caps"}, "name": a["area"]} for a in areas],
            journeys=journeys,
            components=corpus_mod.components(root, cfg.components_registry, repo=repo),
            layers=layers,
            externals=corpus_mod.externals(root, cfg.components_registry),
            outcomes=corpus_mod.outcomes(root, cfg.components_registry),
            layout=corpus_mod.diagram_layout(root, cfg.components_registry),
            decisions=corpus_mod.decisions(root, cfg.decisions_dir),
            disproofs=disproofs,
            commitments=CommitmentsConfig.from_config(cfg),
        )

    def frontier(self) -> frozenset[str]:
        """The startable set: the caller's, when it supplied one, else derived from these rows."""
        return startable_ids(self) if self.startable is None else self.startable


def _disproofs(root: Path, requirements_dir: str) -> list[str]:
    """Requirement ids a register's `## Known violations` table disproves.

    Through `checks.commitments.status.parse_known_violations`, which is the one reader of that
    table — imported lazily so this module's import graph stays the register reader plus two
    pure predicates, and so a corpus with no violations pays nothing for the machinery.
    """
    from .checks.commitments.status import parse_known_violations

    out: list[str] = []
    for f in requirements_mod.registers(root, requirements_dir, shells=True):
        out += [d.requirement for d in parse_known_violations(f.read_text(encoding="utf-8"))]
    return sorted(set(out))


# ─────────────────────────── the derived fields ───────────────────────────


def claims_by_row(prds: Iterable[Mapping[str, Any]]) -> dict[str, list[tuple[str, str]]]:
    """`{requirement id: [(prd number, prd status), …]}` — the realisation edge, by row.

    The same mapping `checks.commitments.registers.load_prd_claims` builds, from rows that have
    already been read. Not a second parser: `corpus.prds` is the one reader of a PRD's
    frontmatter, and this is its `implements:` list turned inside out.
    """
    out: dict[str, list[tuple[str, str]]] = {}
    for row in prds:
        num = str(row.get("n") or "")
        status = str(row.get("status") or "")
        for rid in row.get("impl") or ():
            out.setdefault(str(rid), []).append((num, status))
    return out


def startable_ids(corpus: Corpus) -> frozenset[str]:
    """The rows a PRD could be written against today — `requirement_query.py startable`'s own
    predicate, over rows rather than over a checkout.

    Adopted, IN THIS RELEASE LINE, claimed by no live PRD, and every `Needs` target already
    BUILT — where built means *a shipped PRD claims it and no live disproof says otherwise*,
    and nothing else. The register stores no status by construction, so a claim by shipped work
    is the only evidence of existence the corpus carries. That makes the list conservative in
    the safe direction: it never calls something startable on the strength of a prerequisite
    that merely got written down.

    **Reused, not re-derived.** `is_cut` and `need_scope` are imported from the commitments
    checks — the same two functions the validator that gates a commit and the derived status
    generator call. A second copy of "is this need satisfied" would make the question answerable
    two ways, which is the failure the register's single-parser rule exists to prevent.

    **The `Kind` filter is NOT in here**, and that is deliberate: this answers the tool's
    question, which is about the graph. Whether a startable row describes WORK is a second
    question — an `invariant` is usually already true by construction — and it is asked where
    the flag is set, so this function and `requirement_query startable` cannot disagree.
    """
    ctx = Context(root=_NOWHERE, knowledge=_NOWHERE, cfg=corpus.commitments)
    claims = claims_by_row(corpus.prds)
    disproven = frozenset(corpus.disproofs)
    rows = {str(r["id"]): r for r in corpus.requirements}
    history = set(corpus.commitments.claim_history)

    def cut(rid: str) -> bool:
        row = rows.get(rid)
        return is_cut(ctx, {"cut": (row or {}).get("cut") or ""})

    out: set[str] = set()
    for rid, row in rows.items():
        if row.get("disposition") != "adopted" or cut(rid):
            continue
        if any(status not in history for _prd, status in claims.get(rid, [])):
            continue
        needs = [str(n) for n in row.get("needs") or ()]
        if any(need_scope(ctx, dep, None, claims, disproven) != "built" or cut(dep) for dep in needs):
            continue
        out.add(rid)
    return frozenset(out)


# ─────────────────────────── the graph ───────────────────────────


class Graph:
    """Every entity, every authored edge, and both ends of every edge on the way out.

    Built once from a `Corpus`. Holding it is holding the whole corpus in memory — measured on
    the product corpus at 1,849 requirements, 1,237 capabilities, 161 decisions, 84 components,
    130 journeys and 47 areas, which is roughly 3,500 entities and 9,000 edges — so a caller
    that wants one list builds it once per request rather than once per row.
    """

    def __init__(self, corpus: Corpus) -> None:
        self.corpus = corpus
        self._startable = corpus.frontier()
        self._claims = claims_by_row(corpus.prds)
        self._prd_title = {str(p.get("n") or ""): str(p.get("title") or "") for p in corpus.prds}
        self._prd_status = {str(p.get("n") or ""): str(p.get("status") or "") for p in corpus.prds}
        self.entities: dict[tuple[str, str], Entity] = {}
        for entity in _entities(corpus, self._startable, self._claims):
            self.entities[(entity.kind, entity.id)] = entity
        self.edges: tuple[Edge, ...] = tuple(_edges(corpus))
        self._out: dict[tuple[str, str], list[Edge]] = {}
        self._in: dict[tuple[str, str], list[Edge]] = {}
        for e in self.edges:
            self._out.setdefault((e.src_kind, e.src_id), []).append(e)
            self._in.setdefault((e.dst_kind, e.dst_id), []).append(e)

    # ── reads ───────────────────────────────────────────────────────────────

    def of_kind(self, kind: str) -> list[Entity]:
        """Every entity of one kind, in corpus order — the order the author grouped them in."""
        return [e for (k, _i), e in self.entities.items() if k == kind]

    def get(self, kind: str, entity_id: str) -> Entity | None:
        return self.entities.get((kind, entity_id))

    def resolve(self, entity_id: str) -> Entity | None:
        """Any id -> the entity, without being told its kind.

        `KINDS` order breaks a tie, and ties are REAL: `access-profiles` is both a feature area
        and a registered component on the product corpus. The precedence is stated rather than
        incidental, and `also()` names what else the id resolves to so a caller can offer the
        other reading instead of pretending it does not exist.
        """
        for kind in KINDS:
            found = self.entities.get((kind, entity_id))
            if found is not None:
                return found
        return None

    def also(self, entity_id: str) -> list[str]:
        """Every OTHER kind this id also resolves to. Empty for the ordinary unambiguous id."""
        hits = [k for k in KINDS if (k, entity_id) in self.entities]
        return hits[1:]

    def relations(self, kind: str, entity_id: str) -> list[Relation]:
        """Every relation this entity has — BOTH DIRECTIONS, ALWAYS.

        Forward edges under their own verb, inverse edges under the verb `VERBS` pairs them
        with. Half an edge is how a reader concludes nothing depends on a thing, so there is no
        parameter here that could turn one half off.
        """
        out: list[Relation] = []
        for e in self._out.get((kind, entity_id), ()):
            out.append(self._relation(e.verb, e.dst_kind, e.dst_id))
        for e in self._in.get((kind, entity_id), ()):
            out.append(self._relation(VERBS[e.verb], e.src_kind, e.src_id))
        return out

    def relation_groups(self, kind: str, entity_id: str) -> list[RelationGroup]:
        """The same edges, as the headings a page reads them under — **including the empty ones**.

        `RELATION_ENDS` says which groups a kind has and in what order; the reading says what is
        in them. So a requirement with nothing depending on it still answers with a *Needed by*
        that is empty, which is a different statement from a page that does not mention the edge.

        A verb the table does not name is still served, under itself, after the named ones. That
        is the same choice `_relation` makes about an end that resolves to nothing: an edge this
        model can produce and this table has not caught up with is a defect to be SEEN, and
        dropping it here is exactly what would hide it.
        """
        held: dict[str, list[Relation]] = {}
        for found in self.relations(kind, entity_id):
            held.setdefault(found.verb, []).append(found)
        order = list(RELATION_ENDS.get(kind, ()))
        order += [verb for verb in held if verb not in order]
        return [
            RelationGroup(
                verb=verb,
                label=RELATION_LABELS.get(verb, verb),
                note=RELATION_NOTES.get(verb, ""),
                items=tuple(held.get(verb, ())),
            )
            for verb in order
        ]

    def _relation(self, verb: str, kind: str, entity_id: str) -> Relation:
        """One end, named. A `prd` end has no knowledge entity and is named from the PRD rows.

        An end that resolves to NOTHING still comes back — with the id and an empty name. A
        dangling `implements:` or a `Needs` naming a row somebody deleted is precisely the
        defect the registers' checks exist to find, and dropping the edge here would make it
        invisible on the one page a person is looking at when they would notice.
        """
        if kind == "prd":
            title = self._prd_title.get(entity_id, "")
            return Relation(verb, kind, entity_id, title, self._prd_status.get(entity_id, ""))
        found = self.entities.get((kind, entity_id))
        if found is None:
            return Relation(verb, kind, entity_id, "", "")
        return Relation(verb, kind, entity_id, found.name, found.summary)

    def counts(self) -> list[dict[str, Any]]:
        """Per kind: how many there are, which section it belongs to, and the flags that are
        worth a badge — `107 startable`, `110 unshipped`, `52 undocumented`.

        The flag counts are here rather than on the page because they are arithmetic over the
        corpus, and a page that counted them would have to hold every row to do it — which is
        the thing the three sizes exist to avoid. Measured on the product corpus, 2026-09-12:
        107 startable, 110 unshipped, 52 undocumented.
        """
        out: list[dict[str, Any]] = []
        for kind in KINDS:
            rows = self.of_kind(kind)
            tally: dict[str, int] = {}
            for row in rows:
                for name, on in row.flags.items():
                    if on:
                        tally[name] = tally.get(name, 0) + 1
            out.append({"kind": kind, "section": SECTIONS[kind], "count": len(rows), "flags": tally})
        return out

    def ids(self) -> dict[str, list[str]]:
        """`{kind: [id, …]}` — the index `routeOf` resolves a chip against.

        The whole set, deliberately: §6's rule is that it must be IMPOSSIBLE to link an id the
        corpus does not hold, and a bounded set is the only thing that makes that true. ~3,500
        ids, ~40 KB — one fetch, against a list endpoint that would otherwise be asked to
        resolve each chip one at a time.
        """
        return {kind: [e.id for e in self.of_kind(kind)] for kind in KINDS}


# ─────────────────────────── entities, by kind ───────────────────────────


def _entities(corpus: Corpus, startable: frozenset[str], claims: Mapping[str, list[tuple[str, str]]]) -> list[Entity]:
    return [
        *_journey_entities(corpus),
        *_area_entities(corpus),
        *_capability_entities(corpus),
        *_component_entities(corpus),
        *_requirement_entities(corpus, startable, claims),
        *_decision_entities(corpus),
    ]


def _sentence(text: str) -> str:
    """One clipped sentence. The list rule, applied in ONE place so no kind can opt out."""
    return clip(" ".join(str(text).split()), SENTENCE_CHARS)


def _requirement_entities(
    corpus: Corpus, startable: frozenset[str], claims: Mapping[str, list[tuple[str, str]]]
) -> list[Entity]:
    """A register row. Named by its DOMAIN, because the row has no name — it has a statement."""
    history = set(corpus.commitments.claim_history)
    out: list[Entity] = []
    for row in corpus.requirements:
        rid = str(row["id"])
        domain = Path(str(row.get("register_file") or row.get("file") or "")).stem
        kind = str(row.get("kind") or "")
        disposition = str(row.get("disposition") or "")
        superseded = bool(row.get("superseded"))
        live = [p for p, s in claims.get(rid, []) if s not in history]
        # The flag, and the one place the tool's looser reading is narrowed. Of the adopted
        # rows nothing claims, only the `requirement`-kind ones describe WORK: an `excluded`
        # row is a refusal we wrote down, an `accepted` one a cost taken on purpose, and an
        # `invariant` is usually already true by construction. A Start button on any of those
        # argues against the row it sits under.
        is_startable = kind == "requirement" and rid in startable
        chips: list[tuple[str, str]] = [(kind, "kind")]
        chips.append(("superseded" if superseded else disposition, _DISPOSITION_CLS.get(disposition, "unproven")))
        if is_startable:
            chips.append(("startable", "unproven"))
        elif live:
            chips.append((f"{len(live)} claiming", ""))
        out.append(
            Entity(
                kind="requirement",
                id=rid,
                name=domain,
                summary=_sentence(row.get("statement") or ""),
                facts=(
                    ("domain", domain),
                    ("register", f"{domain}.md"),
                    ("section", str(row.get("section") or "")),
                    ("cut", str(row.get("cut") or "")),
                    ("source", str(row.get("source") or "")),
                ),
                chips=tuple(chips),
                flags={
                    "startable": is_startable,
                    "excluded": kind == "excluded",
                    "accepted": kind == "accepted",
                    "claimed": bool(live),
                    "superseded": superseded,
                    "cut": bool(row.get("cut")),
                },
                facets={"domain": domain, "kind": kind, "disposition": "superseded" if superseded else disposition},
                sev=SEV_ACTIONABLE if (is_startable or (kind in UNCITED_KINDS and not live)) else SEV_QUIET,
            )
        )
    return out


#: A capability's name is authored as `**Title** — explanation`, the convention every feature
#: map writes its rows in. The title identifies the capability; the explanation is its summary.
_CAPABILITY_TITLE_RE = re.compile(r"^\*\*(?P<title>.+?)\*\*\s*[—–-]\s*(?P<rest>.*)$", re.S)


def _capability_title(name: str) -> tuple[str, str]:
    """A capability row's title and its one-sentence summary.

    Naming the row with its feature AREA made every capability in one map an identical row:
    thirteen `fleet-board` titles with the capability itself demoted into a clipped summary
    (BUG-2711). The map's own `**Title** — explanation` split is the capability's own, so the
    title is read off it. A name with no such split is short prose with no separate
    explanation: it is its own title, and it is also what the row says about itself, so it is
    its summary too rather than a blank row.
    """
    text = " ".join(str(name).split())
    match = _CAPABILITY_TITLE_RE.match(text)
    if match is None:
        return text, _sentence(text)
    return plain(match.group("title")), _sentence(match.group("rest"))


def _capability_entities(corpus: Corpus) -> list[Entity]:
    """A feature-map row, named by the CAPABILITY it describes — not by the map it sits in."""
    out: list[Entity] = []
    for row in corpus.capabilities:
        ships = [str(s) for s in row.get("ships") or ()]
        mark = str(row.get("mark") or "")
        # `(core)` / `(shipped)` / `(retired)` are EVIDENCE THE CAPABILITY IS BUILT, not an
        # absent PRD. Reading them as absence is a measured 75%-false gap signal, so a marked
        # row is not unshipped however empty its PRD list is.
        unshipped = not ships and not mark
        area = str(row.get("area") or "")
        title, summary = _capability_title(row.get("name") or "")
        chips: list[tuple[str, str]] = [("capability", "kind")]
        if ships:
            chips.append((f"ships in {', '.join(ships)}", "complete"))
        elif mark:
            chips.append((mark, "complete"))
        else:
            chips.append(("no PRD", "unproven"))
        out.append(
            Entity(
                kind="capability",
                id=str(row["id"]),
                name=title,
                summary=summary,
                facts=(
                    ("feature", area),
                    ("ships in", ", ".join(ships) or mark),
                    ("tested by", ", ".join(str(t) for t in row.get("tested") or ())),
                    ("was", str(row.get("was") or "")),
                    ("anchor", str(row.get("anchor") or "")),
                ),
                chips=tuple(chips),
                flags={"unshipped": unshipped, "tested": bool(row.get("tested")), "excluded": False},
                facets={"area": area, "unshipped": "true" if unshipped else "false"},
                sev=SEV_ACTIONABLE if unshipped else SEV_QUIET,
            )
        )
    return out


def _area_entities(corpus: Corpus) -> list[Entity]:
    """A feature map — a bucket of capabilities, and the tracker Project work on it is filed into."""
    held: dict[str, int] = {}
    for cap in corpus.capabilities:
        slug = str(cap.get("area") or "")
        held[slug] = held.get(slug, 0) + 1
    out: list[Entity] = []
    for row in corpus.areas:
        slug = str(row.get("area") or "")
        area_kind = str(row.get("kind") or "product")
        out.append(
            Entity(
                kind="area",
                id=slug,
                name=str(row.get("name") or slug),
                summary=_sentence(row.get("desc") or row.get("intent") or ""),
                facts=(
                    ("capabilities", str(held.get(slug, 0))),
                    ("layer", str(row.get("group") or "")),
                    ("families", ", ".join(str(f) for f in row.get("fams") or ())),
                    ("surfaces", ", ".join(str(s) for s in row.get("surfaces") or ())),
                ),
                chips=(("feature", "kind"), (area_kind, "" if area_kind == "product" else "unproven")),
                # A SUBSTRATE area is real and owned, and no customer would name it as a
                # feature — so it must never be counted in a "what can a customer do" reading.
                flags={"substrate": area_kind == "substrate", "excluded": False},
                facets={"kind": area_kind, "layer": str(row.get("group") or "")},
            )
        )
    return out


def _component_entities(corpus: Corpus) -> list[Entity]:
    """A durable subsystem. It never ships and carries no status — see `knowledge-model.md`."""
    layer_name = {str(x["id"]): str(x.get("name") or x["id"]) for x in corpus.layers}
    out: list[Entity] = []
    for row in corpus.components:
        documented = bool(row.get("documented"))
        layer = str(row.get("layer") or "")
        chips: list[tuple[str, str]] = [("component", "kind")]
        if row.get("proposed"):
            chips.append(("proposed", "unproven"))
        if not documented:
            chips.append(("no detail doc", "unproven"))
        out.append(
            Entity(
                kind="component",
                id=str(row["id"]),
                name=str(row.get("name") or row["id"]),
                summary=_sentence(row.get("desc") or ""),
                facts=(
                    ("layer", layer_name.get(layer, layer)),
                    ("detail doc", "yes" if documented else "none"),
                    ("owns", ", ".join(str(p) for p in row.get("owns") or ())),
                    # Stated rather than omitted: a page that leaves ship-state blank invites
                    # somebody to fill it in. A component cannot ship — only a slice can.
                    ("ship-state", "never — a component does not ship"),
                ),
                chips=tuple(chips),
                flags={"documented": documented, "proposed": bool(row.get("proposed")), "excluded": False},
                facets={"layer": layer, "documented": "true" if documented else "false"},
                sev=SEV_ACTIONABLE if not documented else SEV_QUIET,
            )
        )
    return out


def _journey_entities(corpus: Corpus) -> list[Entity]:
    """How one persona gets a whole job done. Both tiers — a `flow` and a `map` are both journeys."""
    out: list[Entity] = []
    for row in corpus.journeys:
        tier = str(row.get("kind") or "flow")
        out.append(
            Entity(
                kind="journey",
                id=str(row["slug"]),
                name=str(row.get("title") or row["slug"]),
                summary=_sentence(row.get("job") or ""),
                facts=(
                    ("persona", str(row.get("persona") or "")),
                    ("tier", tier),
                    ("surfaces", ", ".join(str(s) for s in row.get("surfaces") or ())),
                    ("owning PRD", str(row.get("owning_prd") or "")),
                    ("covers", str(len(row.get("covers") or ()))),
                ),
                chips=(("journey", "kind"), (tier, "")),
                flags={"covers": bool(row.get("covers")), "excluded": False},
                facets={"tier": tier, "persona": str(row.get("persona") or "")},
            )
        )
    return out


def _decision_entities(corpus: Corpus) -> list[Entity]:
    """A decision record: the fork we took and the branch we refused."""
    out: list[Entity] = []
    for row in corpus.decisions:
        status = str(row.get("status") or "accepted")
        moves = [str(m) for m in row.get("moves") or ()]
        out.append(
            Entity(
                kind="decision",
                id=str(row["id"]),
                name=str(row.get("title") or row["id"]),
                summary=_sentence(row.get("lead") or ""),
                facts=(
                    ("decided", str(row.get("date") or "")),
                    ("record", f"{row['id']}.md"),
                    ("moves", f"{len(moves)} rows"),
                    ("supersedes", str(row.get("supersedes") or "")),
                ),
                chips=(("decision", "kind"), (status, "complete" if status == "accepted" else "unproven")),
                flags={"moves": bool(moves), "excluded": False},
                facets={"status": status, "year": str(row.get("date") or "")[:4]},
            )
        )
    return out


# ─────────────────────────── edges ───────────────────────────


def _edges(corpus: Corpus) -> list[Edge]:
    """Every authored edge, read off the side that authors it. Inverses are NEVER read.

    The one edge whose authored side is not where contract §2 puts it: `component builds
    capability`. The components registry has no capability column — what it has is `id`, `name`,
    `layer`, `owns`, `depends_on`, `description`, `detail` — and the edge is authored on the
    FEATURE MAP, whose frontmatter `components:` names which subsystems build that area's rows.
    So it is derived through the area, which is what makes it a real edge rather than a guess,
    and it is the area's list that a reader edits to change it.

    **An edge naming an entity that does not exist is KEPT.** A `covers:` pointing at a
    capability somebody deleted, a `**Commitments.**` line citing a row that never existed, a
    dangling `implements:` — every one of those is precisely the defect the registers' checks
    are for, and the page a person is looking at when they would notice it is this one.
    `Graph._relation` renders an unresolvable end with an empty name rather than silently
    dropping the row.
    """
    out: list[Edge] = []
    caps_by_area: dict[str, list[str]] = {}
    for cap in corpus.capabilities:
        caps_by_area.setdefault(str(cap.get("area") or ""), []).append(str(cap["id"]))

    # A PRD's `implements:` — the realisation edge, written once on the PRD.
    for prd in corpus.prds:
        for rid in prd.get("impl") or ():
            out.append(Edge("claims", "prd", str(prd.get("n") or ""), "requirement", str(rid)))

    # A register's `Needs` column, and a feature map's.
    for row in corpus.requirements:
        for dep in row.get("needs") or ():
            out.append(Edge("needs", "requirement", str(row["id"]), "requirement", str(dep)))
    for cap in corpus.capabilities:
        cid = str(cap["id"])
        area = str(cap.get("area") or "")
        out.append(Edge("holds", "area", area, "capability", cid))
        for dep in cap.get("needs") or ():
            out.append(Edge("needs", "capability", cid, "capability", str(dep)))
        for num in cap.get("ships") or ():
            out.append(Edge("shipsIn", "capability", cid, "prd", str(num)))

    # A journey's `covers:`, unioned with the map's `Tested by` — `corpus.features` already
    # merged the two into `tested`, because the authored edge runs both ways and the two are
    # not always in step.
    for journey in corpus.journeys:
        slug = str(journey["slug"])
        for cap in journey.get("covers") or ():
            out.append(Edge("covers", "journey", slug, "capability", str(cap)))
    seen_covers = {(e.src_id, e.dst_id) for e in out if e.verb == "covers"}
    for cap in corpus.capabilities:
        for slug in cap.get("tested") or ():
            if (str(slug), str(cap["id"])) not in seen_covers:
                out.append(Edge("covers", "journey", str(slug), "capability", str(cap["id"])))

    # A feature map's `components:`, resolved onto that area's capability rows.
    for area_row in corpus.areas:
        slug = str(area_row.get("area") or "")
        for comp in area_row.get("components") or ():
            for cap_id in caps_by_area.get(slug, ()):
                out.append(Edge("builds", "component", str(comp), "capability", cap_id))

    # A decision record's `**Commitments.**` line.
    for decision in corpus.decisions:
        for rid in decision.get("moves") or ():
            out.append(Edge("moves", "decision", str(decision["id"]), "requirement", str(rid)))
    return out


# ─────────────────────────── findings ───────────────────────────

#: Finding key -> `(group, severity, why)`. The KEY is this module's and travels with the
#: finding; the COMMAND behind it is the caller's vocabulary and is looked up, never written
#: here. `board.actions` draws exactly this line and for the same reason.
#:
#: `route` rather than a PRD-creating command, wherever a deployment names one: the ladder
#: decides whether the work is a PRD, a slice or a task, and that is route's job, not this
#: page's and not this module's.
FINDINGS: Mapping[str, tuple[str, int, str]] = {
    "requirement_startable": (
        "start",
        SEV_ACTIONABLE,
        "No PRD claims this, every prerequisite is already built, and the row describes work. "
        "That is the startable frontier — walk the ladder on what would satisfy it.",
    ),
    "requirement_uncited": (
        "hygiene",
        SEV_QUIET,
        "Nothing cites this row. That is a documentation gap rather than a build one — an "
        "invariant is usually already true by construction, and the question is which PRD or "
        "spec should be naming it.",
    ),
    "capability_unshipped": (
        "promise",
        SEV_ACTIONABLE,
        "This capability ships in no PRD. A feature-map row with an empty `Ships in` is a thing "
        "we said someone can do, that nobody can do yet.",
    ),
    "component_document": (
        "hygiene",
        SEV_ACTIONABLE,
        "The registry names this component and no detail document describes it. Every other "
        "component page reads from one.",
    ),
}


def findings(entity: Entity, vocab: Vocabulary | None = None) -> list[dict[str, Any]]:
    """What to do about one entity, in the row shape `board.actions` emits.

    `{group, sev, id, title, why, cmd, cmdKey, built}` — so a page renders a knowledge finding
    through the same `actionItems()` → `entityList()` → `runbox()` path it renders a program
    finding through, and adding a component for it would be a defect in this work.

    **Never on a settled row.** An `excluded` row records a refusal and an `accepted` row a cost
    taken on purpose; neither is a gap and neither has anything to start. Those two are answered
    by a STATED SECTION on the page — the `excluded` / `accepted` flags are what it keys on —
    rather than by a finding with the command quietly removed, because a finding with no command
    reads as a tool that is missing rather than as a decision that was made.

    `cmd` is empty when this deployment's vocabulary names no command for the key, and `cmdKey`
    travels regardless: an empty `cmd` is then reportable as the gap it is — `actionCommands`
    missing an entry — rather than rendered as a considered answer.
    """
    if entity.flags.get("excluded") or entity.flags.get("accepted"):
        return []
    keys: list[str] = []
    if entity.kind == "requirement":
        if entity.flags.get("startable"):
            keys.append("requirement_startable")
        elif not entity.flags.get("claimed") and entity.facets.get("kind") in UNCITED_KINDS:
            keys.append("requirement_uncited")
    elif entity.kind == "capability" and entity.flags.get("unshipped"):
        keys.append("capability_unshipped")
    elif entity.kind == "component" and not entity.flags.get("documented"):
        keys.append("component_document")

    v = vocab or Vocabulary()
    out: list[dict[str, Any]] = []
    for key in keys:
        group, sev, why = FINDINGS[key]
        cmd = v.command(key, entity.id)
        out.append(
            {
                "group": group,
                "sev": sev,
                "id": entity.id,
                "title": entity.name,
                "why": why,
                "cmd": cmd,
                "cmdKey": key,
                "built": v.is_built(cmd),
            }
        )
    return out
