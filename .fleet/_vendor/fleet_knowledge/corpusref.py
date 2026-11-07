"""Repo-qualified references: `<corpus>:<typed-id>` — one parser, one resolver.

WHY THIS EXISTS. Every repository that keeps a planning corpus numbers its own documents: its
PRDs (`0899`), programs (`PG-047`), slices (`SL-139`), capabilities (`CAP-1408`) and requirement
rows (`FLT-104`). When a document in one corpus names a document in ANOTHER, the bare id is a
lie waiting to happen — `0899` here and `0899` there are two different PRDs — so a cross-corpus
reference is written QUALIFIED by the corpus it lives in:

    fleet:0899    fleet:PG-047    fleet:SL-139    fleet:CAP-1408    acme:FLT-104

The corpus name is the lane name, the same word as the `repo:<lane>` label. Inside a
requirement `Source` cell the PRD anchor takes the same qualifier: `prd:fleet:0899`.

THE FAILURE THIS PREVENTS. Before this module, the checkers read ids with unanchored patterns
(`\\b\\d{4}\\b`, `\\bCAP-\\d{4}\\b`, `\\b[A-Z]{2,5}-\\d{3,}\\b`), and `:` is a word boundary — so
`fleet:0012` resolved, silently, against THIS corpus's PRD 0012. A reference to a document
somewhere else that happens to share a number with one here is the worst kind of wrong: it
passes every gate and points at the wrong thing. So the rule here is that a qualified reference
is NEVER resolved against the local corpus unless its qualifier names this corpus.

RESOLUTION. Configured in `.fleet/fleet.toml`:

    [fleet.planning]
    corpus = "acme"            # this corpus's own name; a ref qualified with it is local
    [fleet.planning.corpora]
    fleet = "fleet/knowledge"    # name -> the sibling's knowledge dir, repo-relative;
                                 # "" = known, but not on disk here
    apps = { path = "apps/knowledge", prefixes = ["APP"] }
                                 # ...and the requirement prefixes it OWNS: a bare `APP-104`
                                 # is resolved in `apps` exactly as `apps:APP-104` would be

  * qualifier == `corpus`            -> local: resolved like a bare id.
  * qualifier not declared           -> ERROR naming the declared corpora.
  * declared, path on disk           -> resolved against a light index of the sibling (its
                                        PRDs with status and slice, slice/program/capability
                                        ids, requirement ids with disposition). A miss is an
                                        ERROR that says the sibling may be pinned behind.
  * declared "" or path not on disk  -> UNVERIFIED: a note, counted in the check's summary
                                        as "unverified cross-corpus refs" — never a silent pass.

Graph checks (cycles, cancelled dependencies, proof disjointness) treat a qualified reference
as an opaque external node; a check that wants the sibling's state (a cancelled PRD) reads it
from the resolution's `record` when the sibling is loaded.

Stdlib only.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .planningmode import check_mode, check_require_area

__all__ = [
    "CAPABILITY",
    "PROGRAM",
    "PRD",
    "REQUIREMENT",
    "RESERVED_CORPUS_NAMES",
    "SLICE",
    "Corpora",
    "Ref",
    "Resolution",
    "SiblingIndex",
    "clear_index_cache",
    "find_refs",
    "is_qualified",
    "load_index",
    "localize_entry",
    "localize_text",
    "mask",
    "own_corpus",
    "own_name",
    "owned_prefixes",
    "parse_ref",
    "split_corpora",
    "unownable_prefixes",
    "validate_planning_table",
]

#: Words that already carry a meaning before a `:` in the places these references are written:
#: `prd:NNNN` and `drill:<stem>` are entry forms of their own, `web:` / `admin:` prefix a surface,
#: `tag:` and `design:NNNN` are Source-cell anchors, and `issue:<KEY>` / `idea:<KEY>` name tracker
#: issues in prose. A corpus with one of these names would make `prd:0899` ambiguous, so a config
#: naming one is refused — and a reserved word before a `:` is never read (or masked) as one.
RESERVED_CORPUS_NAMES = frozenset({"prd", "drill", "web", "admin", "tag", "design", "issue", "idea"})

#: A corpus name: lowercase, the shape of a lane name / `repo:<lane>` label.
CORPUS_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")

#: The ids a qualified reference may carry: a 4-digit PRD number, or a prefixed id
#: (`PG-047`, `SL-139`, `CAP-1408`, `FLT-104`). Typed by SHAPE only — which register an id
#: belongs to is the reading site's to say.
TYPED_ID = r"(?:[A-Z][A-Z0-9]{1,9}-\d+|\d{4})"

#: The QUALIFIER is read loosely — any `[A-Za-z][\w-]*`, any case — and so is the id's case.
#: A qualifier that is not a valid corpus name (`Fleet:0899`) is still a qualified reference:
#: in a structured field it fails as an undeclared corpus, and in every bare-id scan it is
#: masked. Reading only the well-formed shape is what let `Fleet:0899` fall through to the
#: local `0899`.
_LOOSE_ID = r"(?:[A-Za-z][A-Za-z0-9]{1,9}-\d+|\d{4})"
_FULL_RE = re.compile(rf"^(?P<corpus>[A-Za-z][\w-]*):(?P<id>{_LOOSE_ID})$")
#: A qualified reference inside free text or a cell. The optional `prd:` lead lets a Source
#: anchor `prd:fleet:0899` match as the `fleet:0899` it carries; the lookbehind keeps the
#: reference from being read out of the middle of a word, a dotted name or a hyphenated one.
#: A `/` IS a boundary — `CAP-1111/fleet:CAP-1637` names two capabilities, and refusing the
#: slash left `CAP-1637` for the local scan to read as this corpus's — except straight after
#: `//`, where `host:8000` is a URL authority's port. NOTHING is required after the id —
#: `fleet:0899-corpus-refs` (a folder name) still carries `fleet:0899`, and a trailing
#: lookahead that refused it left the `0899` for the local scan.
_SCAN_RE = re.compile(rf"(?<![\w.-])(?<!//)(?P<lead>prd:)?(?P<corpus>[A-Za-z][\w-]*):(?P<id>{_LOOSE_ID})")
#: The canonical spelling of a qualified id: ids are uppercase (see `TYPED_ID`).
_TYPED_ID_RE = re.compile(rf"^{TYPED_ID}$")
#: A markdown link: `[text](target)`. A link whose TEXT is a qualified reference is masked
#: whole — its target (`../../fleet/knowledge/prds/0899-x/prd.md`) names the same foreign
#: document, and a bare scan would read `0899` out of the path.
_LINK_RE = re.compile(r"\[([^\]\n]*)\]\(([^)\n]*)\)")


def _reserved(corpus: str) -> bool:
    return corpus.lower() in RESERVED_CORPUS_NAMES


# The kinds of document a reference can name — what the sibling index is asked for.
PRD = "prd"
SLICE = "slice"
PROGRAM = "program"
CAPABILITY = "capability"
REQUIREMENT = "requirement"
#: A journey (flow or map), named by its slug: `acme:check-result` in a Tested-by cell.
JOURNEY = "journey"
_KIND_NOUN = {
    JOURNEY: "journey",
    PRD: "PRD",
    SLICE: "slice",
    PROGRAM: "program",
    CAPABILITY: "capability",
    REQUIREMENT: "requirement row",
}

# Resolution outcomes.
LOCAL = "local"
FOUND = "found"
MISSING = "missing"
UNDECLARED = "undeclared"
UNVERIFIED = "unverified"
#: Qualified with THIS corpus's name, but in a prefix a sibling owns (`acme:FLT-104` in `acme`,
#: `fleet` owning `FLT`): the two halves of the reference disagree about whose row it is.
MISQUALIFIED = "misqualified"
#: Qualified, but the id is not in its canonical (uppercase) spelling: `fleet:cap-1637`. Every
#: bare scan masks it, so a reader that then keeps only well-formed ids would drop it silently.
MALFORMED = "malformed"


class CorpusConfigError(ValueError):
    """A `[fleet.planning]` corpus declaration that cannot be honoured."""


# ─── parsing ──────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Ref:
    """One reference: `corpus` is None for a bare (local) id."""

    corpus: str | None
    id: str

    @property
    def qualified(self) -> bool:
        return self.corpus is not None

    def __str__(self) -> str:
        return f"{self.corpus}:{self.id}" if self.corpus else self.id


def parse_ref(text: str) -> Ref:
    """`fleet:0899` -> `Ref("fleet", "0899")`; anything else -> `Ref(None, <text>)`.

    The text is stripped (and a pair of backticks dropped). A reserved word before the colon
    (`drill:<stem>`, `prd:0899`) is NOT a corpus, so the whole entry comes back unqualified for
    the caller's own grammar to read.
    """
    raw = str(text).strip().strip("`").strip()
    m = _FULL_RE.match(raw)
    if m and not _reserved(m.group("corpus")):
        return Ref(m.group("corpus"), m.group("id"))
    return Ref(None, raw)


def is_qualified(text: str) -> bool:
    """Whether one authored entry is a repo-qualified reference."""
    return parse_ref(text).qualified


def find_refs(text: str, *, known: Iterable[str] | None = None) -> list[tuple[Ref, int, int]]:
    """`(ref, start, end)` for every qualified reference in `text`, in order.

    `known` limits the scan to those corpus names — what a PROSE reader passes, because in a
    sentence `localhost:8000` has the same shape as a reference and is not one. A structured
    field (a `depends_on:` entry, a `Needs` cell) passes nothing: there every `name:ID` is a
    reference, and an undeclared name is the error the resolver reports.
    """
    names = None if known is None else frozenset(known)
    out: list[tuple[Ref, int, int]] = []
    for m in _SCAN_RE.finditer(text):
        corpus = m.group("corpus")
        if _reserved(corpus):
            continue
        if names is not None and corpus not in names:
            continue
        out.append((Ref(corpus, m.group("id")), m.start(), m.end()))
    return out


def _kept(rid: str, keep: Iterable[str]) -> bool:
    m = _PREFIXED_ID_RE.match(rid)
    return m is not None and m.group(1) in keep


def localize_entry(text: str, own: str, keep: Iterable[str] = ()) -> str:
    """One authored entry with an OWN-corpus qualifier dropped: `acme:0012` -> `0012` in `acme`.

    Applied by every reader at parse time, so no downstream comparison ever sees an own-
    qualified id — it is the local id, and only a foreign qualifier survives. An id in a prefix
    named in `keep` (the prefixes a sibling owns) keeps its qualifier: `acme:FLT-104` is a
    contradiction the resolver reports, never a quiet `FLT-104`.
    """
    if not own:
        return text
    ref = parse_ref(text)
    return ref.id if ref.corpus == own and not _kept(ref.id, keep) else text


def localize_text(text: str, own: str, keep: Iterable[str] = ()) -> str:
    """`text` with every OWN-qualified reference rewritten to its bare id (`prd:acme:0899` ->
    `prd:0899`). For cells a reader scans with a pattern (`Ships in`, `Needs`). An id in a
    `keep` prefix keeps its qualifier (see `localize_entry`)."""
    if not own or ":" not in text:
        return text
    keep = frozenset(keep)
    return _SCAN_RE.sub(
        lambda m: (
            f"{m.group('lead') or ''}{m.group('id')}"
            if m.group("corpus") == own and not _kept(m.group("id"), keep)
            else m.group(0)
        ),
        text,
    )


def mask(text: str) -> str:
    """`text` with every qualified reference blanked to spaces (offsets preserved).

    What a LOCAL id scan runs over, so `fleet:0012` can never be read as this corpus's 0012.
    Masks every `name:ID` shape, declared or not: a reader that resolves locally must never see
    a qualified id, whoever's it is.
    """
    if ":" not in text:
        return text
    chars = list(text)
    for link in _LINK_RE.finditer(text):
        if find_refs(link.group(1)):
            chars[link.start() : link.end()] = " " * (link.end() - link.start())
    for _ref, start, end in find_refs(text):
        chars[start:end] = " " * (end - start)
    return "".join(chars)


# ─── configuration ────────────────────────────────────────────────────────────────────


#: A requirement-register prefix, the only kind of prefix a sibling may OWN.
OWNED_PREFIX_RE = re.compile(r"^[A-Z]{2,5}$")
#: The keys a `[fleet.planning.corpora.<name>]` table may carry.
_SIBLING_KEYS = frozenset({"path", "prefixes"})
#: A bare id shaped like a requirement row — the only shape an owned prefix routes.
_PREFIXED_ID_RE = re.compile(r"^([A-Z]{2,5})-\d+$")


def unownable_prefixes(table: Mapping[str, Any], config: Any = None) -> dict[str, str]:
    """`{prefix: what it already names}` for every prefix a sibling may never own.

    The planning tiers' id prefixes (programs, slices, capabilities, todos, PRDs) stay
    qualified-only across corpora, and a reserved prefix (the tracker's `ENG`) is not a
    register's at all. Read from the resolved `Config` (where these are top-level keys) and
    from the `[fleet.planning]` table (which may override them), defaults otherwise.
    """
    out = {"PRD": "the PRD number space"}
    for key, default, what in (
        ("program_prefix", "PG", "program ids"),
        ("slice_prefix", "SL", "slice ids"),
        ("capability_prefix", "CAP", "capability ids"),
        ("todo_prefix", "TODO", "todo ids"),
    ):
        values = [getattr(config, key, None) if config is not None else default, table.get(key)]
        for value in values:
            if value:
                out.setdefault(str(value), what)
    reserved: set[str] = set()
    for value in (
        getattr(config, "reserved_prefixes", None),
        table.get("reserved_requirement_prefixes"),
        table.get("reserved_prefixes"),
    ):
        if value:
            reserved.update(str(v) for v in value)
    if config is None and not reserved:
        reserved = {"ENG"}
    for prefix in reserved:
        out.setdefault(prefix, "a reserved prefix (another id namespace, such as the tracker's)")
    return out


def split_corpora(corpora: Mapping[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    """`(name -> knowledge dir, owned prefix -> name)` from a `[fleet.planning.corpora]` table.

    An entry is either the sibling's path (`fleet = "fleet/knowledge"`) or a table naming the
    path and the requirement prefixes the sibling owns
    (`fleet = { path = "fleet/knowledge", prefixes = ["FLT"] }`). Assumes a validated table.
    """
    paths: dict[str, str] = {}
    owned: dict[str, str] = {}
    for name, value in corpora.items():
        if isinstance(value, Mapping):
            paths[str(name)] = str(value.get("path", ""))
            for prefix in value.get("prefixes") or ():
                owned[str(prefix)] = str(name)
        else:
            paths[str(name)] = str(value)
    return paths, owned


def owned_prefixes(corpora: Mapping[str, Any] | None) -> dict[str, str]:
    """`{owned prefix: sibling name}` from a `[fleet.planning.corpora]` table (or `{}`)."""
    return split_corpora(corpora or {})[1]


def validate_planning_table(table: Mapping[str, Any], config: Any = None) -> None:
    """Refuse a `[fleet.planning]` corpus declaration that cannot be honoured.

    Raises `CorpusConfigError` naming the problem. Called where the config file is READ, so a
    bad name is reported once, at the top, rather than as a resolution error at every site.
    `config` is the resolved `Config` the table belongs to, when there is one: the id prefixes a
    sibling may not own are read from it.
    """
    if "mode" in table and (refusal := check_mode(table["mode"])):
        raise CorpusConfigError(refusal)
    if "require_area" in table and (refusal := check_require_area(table["require_area"])):
        raise CorpusConfigError(refusal)
    own = table.get("corpus", "")
    corpora = table.get("corpora", {})
    if not isinstance(own, str):
        raise CorpusConfigError(f"`corpus` must be a string, got {own!r}")
    if own:
        _check_name(own, "corpus")
    if not isinstance(corpora, Mapping):
        raise CorpusConfigError(
            f'`corpora` must be a table of `name = "<knowledge dir>"` — write '
            f"`[fleet.planning.corpora]`, got {corpora!r}"
        )
    refused = unownable_prefixes(table, config)
    owner: dict[str, str] = {}
    for name, value in corpora.items():
        _check_name(str(name), "corpora")
        if isinstance(value, Mapping):
            path = value.get("path")
            if extra := sorted(set(value) - _SIBLING_KEYS):
                raise CorpusConfigError(
                    f"`corpora.{name}` carries {', '.join(f'`{k}`' for k in extra)} — a sibling table "
                    "takes only `path` and `prefixes`"
                )
            prefixes = value.get("prefixes", [])
            if not isinstance(prefixes, list) or not all(isinstance(p, str) for p in prefixes):
                raise CorpusConfigError(
                    f'`corpora.{name}.prefixes` must be a list of register prefixes (`["FLT"]`), got {prefixes!r}'
                )
            for prefix in prefixes:
                if not OWNED_PREFIX_RE.match(prefix):
                    raise CorpusConfigError(
                        f"`corpora.{name}.prefixes`: `{prefix}` is not a requirement-register prefix "
                        "(2–5 uppercase letters)"
                    )
                if prefix in refused:
                    raise CorpusConfigError(
                        f"`corpora.{name}.prefixes`: `{prefix}` names {refused[prefix]} — only "
                        "requirement-register prefixes can be owned; reference the sibling's ids "
                        f"qualified (`{name}:{prefix}-…`)"
                    )
                if prefix in owner:
                    raise CorpusConfigError(
                        f"prefix `{prefix}` is owned by both corpus `{owner[prefix]}` and corpus `{name}` — "
                        "a register prefix names one register, so exactly one sibling may own it"
                    )
                owner[prefix] = str(name)
        else:
            path = value
        if not isinstance(path, str):
            raise CorpusConfigError(
                f"`corpora.{name}` must be a string (the sibling's knowledge dir, repo-relative, "
                f'or "" when it is not on disk here) or a table `{{ path = "...", prefixes = [...] }}`, '
                f"got {value!r}"
            )
        if own and name == own:
            raise CorpusConfigError(
                f'`corpora.{name}` names this corpus itself (`corpus = "{own}"`) — a reference '
                "qualified with the own name is already local; drop the entry"
            )


def _check_name(name: str, key: str) -> None:
    if name in RESERVED_CORPUS_NAMES:
        raise CorpusConfigError(
            f"`{key}`: `{name}` is reserved and cannot name a corpus "
            f"(reserved: {', '.join(sorted(RESERVED_CORPUS_NAMES))}) — it already means something "
            "before a `:` in a reference"
        )
    if not CORPUS_NAME_RE.match(name):
        raise CorpusConfigError(
            f"`{key}`: `{name}` is not a corpus name — lowercase letters, digits and `-`, "
            "starting with a letter (the lane name, as in `repo:<lane>`)"
        )


# ─── the sibling index ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SiblingIndex:
    """What one sibling corpus holds, as much as a reference needs to resolve against it."""

    knowledge: Path
    prds: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    slices: frozenset[str] = frozenset()
    programs: frozenset[str] = frozenset()
    capabilities: frozenset[str] = frozenset()
    requirements: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    #: Capability id -> the backticked tokens of its `Tested by` cell, as written
    #: (`aflow`, `acme:fleet-check-result`): the sibling's half of a cross-corpus two-way link.
    cap_tested: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    #: Journey slug -> its `covers:` entries, as written (`CAP-1408`, `acme:CAP-0002`).
    journeys: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    #: Why the sibling's own config could not be used, when it could not (a sibling pinned
    #: AHEAD of this kit writes keys this version refuses). The index is then read with the
    #: default layout, and every check that used it says so.
    config_problem: str = ""

    def record(self, kind: str, rid: str) -> Mapping[str, Any] | None:
        """The sibling's record for `rid` of `kind`, or None when it holds no such document."""
        if kind == PRD:
            return self.prds.get(rid)
        if kind == REQUIREMENT:
            return self.requirements.get(rid)
        if kind == CAPABILITY:
            return {"id": rid, "tested": self.cap_tested.get(rid, ())} if rid in self.capabilities else None
        if kind == JOURNEY:
            return {"id": rid, "covers": self.journeys[rid]} if rid in self.journeys else None
        pool = {SLICE: self.slices, PROGRAM: self.programs}.get(kind, frozenset())
        return {"id": rid} if rid in pool else None


_INDEX_CACHE: dict[str, SiblingIndex] = {}


def clear_index_cache() -> None:
    """Forget every loaded sibling index (a test that rewrites a sibling between reads)."""
    _INDEX_CACHE.clear()


def load_index(knowledge: Path, stop: Path | None = None) -> SiblingIndex:
    """A `SiblingIndex` of the corpus at `knowledge`, read through the package's own readers.

    The sibling is described by ITS config, found upward from its knowledge dir but never past
    its own repository root (a `.git` entry) or `stop` (the host's root) — a sibling with no
    config of its own is read with the DEFAULT layout, never the host's. A sibling config this
    version cannot parse is recorded in `config_problem` and the defaults are used.

    Cached per resolved path for the life of the process: several checks resolve against the
    same sibling in one run.
    """
    key = str(knowledge.resolve())
    hit = _INDEX_CACHE.get(key)
    if hit is not None:
        return hit
    index = _build_index(Path(key), stop)
    _INDEX_CACHE[key] = index
    return index


def _sibling_config(knowledge: Path, stop: Path | None) -> tuple[Any, str]:
    """`(config, problem)` for the sibling at `knowledge` — see `load_index`."""
    from .config import Config, ConfigError, config_files_in, config_from_table, config_table  # noqa: PLC0415

    limit = stop.resolve() if stop is not None else None
    d = knowledge.resolve()
    while True:
        if limit is not None and d == limit:
            break  # the host's own root: its config describes the host, not the sibling
        try:
            for path in config_files_in(d):
                table = config_table(path.read_text(encoding="utf-8"), path)
                if table is not None:
                    return config_from_table(table, path), ""
        except (ConfigError, OSError) as exc:
            return Config(), str(exc)
        if (d / ".git").exists() or d.parent == d:
            break
        d = d.parent
    return Config(), ""


def _build_index(knowledge: Path, stop: Path | None = None) -> SiblingIndex:
    from . import corpus as kcorpus  # noqa: PLC0415 — the readers are heavy; load on first use
    from . import registers as kreg  # noqa: PLC0415
    from . import requirements as kreq  # noqa: PLC0415

    cfg, problem = _sibling_config(knowledge, stop)
    # The SIBLING's own name: its own-qualified refs are its local ids, never this host's.
    own = str((cfg.planning or {}).get("corpus") or "")
    prds: dict[str, dict[str, str]] = {}
    try:
        for p in kcorpus.prds(knowledge, cfg.prds_dir, own=own):
            prds[str(p["n"])] = {"status": str(p.get("status") or ""), "slice": str(p.get("slice") or "")}
    except (OSError, UnicodeDecodeError):
        pass
    try:
        programs = frozenset(
            str(r["id"])
            for r in kreg.programs(
                knowledge, cfg.programs_register, cfg.program_prefix, cfg.programs_detail_dir, own=own
            )
        )
    except (OSError, UnicodeDecodeError, ValueError):
        programs = frozenset()
    try:
        slices = frozenset(
            str(r["id"])
            for r in kreg.slices(knowledge, cfg.slices_register, cfg.slice_prefix, cfg.slices_detail_dir, own=own)
        )
    except (OSError, UnicodeDecodeError, ValueError):
        slices = frozenset()
    requirements: dict[str, dict[str, Any]] = {}
    try:
        rows, _findings = kreq.load_registers(
            knowledge,
            reserved_prefixes=frozenset(cfg.reserved_prefixes),
            dir_name=cfg.requirements_dir,
            own=own,
            # A sibling is never rendered here: its fragment-backed registers are read from
            # their committed shells and row fragments.
            shells=True,
        )
        for rid, row in rows.items():
            requirements[rid] = {
                "disposition": row.get("disposition", ""),
                "superseded": bool(row.get("superseded")),
                "superseded_by": row.get("superseded_by"),
                "kind": row.get("kind", ""),
            }
    except (OSError, UnicodeDecodeError, ValueError):
        pass
    caps = _capabilities(knowledge, cfg.features_dir, cfg.capability_prefix)
    return SiblingIndex(
        knowledge=knowledge,
        prds=prds,
        slices=slices,
        programs=programs,
        capabilities=frozenset(caps),
        cap_tested=caps,
        journeys=_journey_covers(knowledge, cfg.journeys_dir),
        requirements=requirements,
        config_problem=problem,
    )


_OWN_CACHE: dict[str, str] = {}
#: `(config key, default prefix, kind)` for the planning tiers' prefixed ids.
_ID_KIND_KEYS = (
    ("capability_prefix", "CAP", CAPABILITY),
    ("program_prefix", "PG", PROGRAM),
    ("slice_prefix", "SL", SLICE),
)
_DEFAULT_ID_KINDS = {default: kind for _key, default, kind in _ID_KIND_KEYS}
_AT_CACHE: dict[tuple[str, int], tuple[Mapping[str, Any], Any]] = {}


def own_corpus(knowledge: Path) -> str:
    """This corpus's own name as its config FILE declares it (`[fleet.planning] corpus`), or "".

    The default a reader handed only a path falls back to; a caller holding a `Config` passes
    `own_name(config)` instead, which also sees a config built in code.
    """
    key = str(knowledge)
    if key in _OWN_CACHE:
        return _OWN_CACHE[key]
    from .config import ConfigError, find_config_file  # noqa: PLC0415

    own = ""
    try:
        located = find_config_file(knowledge)
    except (ConfigError, OSError):
        located = None
    if located is not None:
        planning = located[1].get("planning")
        if isinstance(planning, Mapping):
            own = str(planning.get("corpus") or "")
    _OWN_CACHE[key] = own
    return own


def own_name(config: Any) -> str | None:
    """The own corpus name a `Config` carries, or None when it names none (fall back to the file)."""
    planning = getattr(config, "planning", None)
    if isinstance(planning, Mapping) and planning.get("corpus"):
        return str(planning["corpus"])
    return None


def resolve_own(knowledge: Path, own: str | None) -> str:
    """`own` when the caller knows it, else what the corpus's config file declares."""
    return own if own is not None else own_corpus(knowledge)


_BACKTICKED_RE = re.compile(r"`([^`]+)`")
_UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")


def _capabilities(knowledge: Path, features_dir: str, prefix: str) -> dict[str, tuple[str, ...]]:
    """`{capability id: its Tested-by tokens}` for every capability a feature map defines —
    committed table rows and row fragments (`features/rows/<ID>.json`) alike, so a sibling
    whose maps are fragment-backed and unrendered is read from what it commits."""
    if not features_dir:
        return {}
    base = knowledge / features_dir
    id_re = re.compile(rf"^{re.escape(prefix)}-\d+$")
    found: dict[str, tuple[str, ...]] = {}
    for f in sorted(base.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line in text.splitlines():
            s = line.strip()
            if not s.startswith("|"):
                continue
            cells = [c.strip() for c in _UNESCAPED_PIPE_RE.split(s.strip("|"))]
            first = cells[0].strip("`") if cells else ""
            if id_re.match(first):
                found[first] = tuple(_BACKTICKED_RE.findall(cells[3])) if len(cells) > 3 else ()
    for f in sorted((base / "rows").glob("*.json")):
        if not id_re.match(f.stem):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        frag = data.get("cells") if isinstance(data, dict) else None
        tested = str(frag[2]) if isinstance(frag, list) and len(frag) > 2 else ""
        found[f.stem] = tuple(_BACKTICKED_RE.findall(tested))
    return found


_FM_RE = re.compile(r"\A---\n(.*?)\n---", re.S)


def _journey_covers(knowledge: Path, journeys_dir: str) -> dict[str, tuple[str, ...]]:
    """`{journey slug: its covers: entries}` for every journey (flow or map) the corpus holds."""
    if not journeys_dir:
        return {}
    out: dict[str, tuple[str, ...]] = {}
    for f in sorted((knowledge / journeys_dir).rglob("*.md")):
        if f.name == "README.md":
            continue
        try:
            m = _FM_RE.match(f.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        fm = m.group(1) if m else ""
        idm = re.search(r"^id:[ \t]*(\S+)", fm, re.M)
        slug = idm.group(1).strip("\"'") if idm else f.stem
        inline = re.search(r"^covers:[ \t]*\[(.*?)\]", fm, re.M | re.S)
        if inline:
            covers = [x.strip().strip("\"'") for x in inline.group(1).split(",") if x.strip()]
        else:
            block = re.search(r"^covers:[ \t]*$((?:\n[ \t]+-[^\n]*)*)", fm, re.M)
            covers = (
                [
                    re.sub(r"^[ \t]+-[ \t]*", "", ln).strip().strip("\"'")
                    for ln in block.group(1).splitlines()
                    if ln.strip()
                ]
                if block
                else []
            )
        out[slug] = tuple(covers)
    return out


# ─── resolution ───────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Resolution:
    """What one reference resolved to.

    `outcome` is `local` (bare, or qualified with this corpus's own name — resolve `ref.id`
    locally), `found` (the sibling holds it; `record` carries what it knows), `missing` /
    `undeclared` (errors, with `message`), or `unverified` (declared but not on disk; a note).
    """

    ref: Ref
    outcome: str
    message: str = ""
    record: Mapping[str, Any] | None = None

    @property
    def local(self) -> bool:
        return self.outcome == LOCAL

    @property
    def is_error(self) -> bool:
        return self.outcome in (MISSING, UNDECLARED, MISQUALIFIED, MALFORMED)

    @property
    def unverified(self) -> bool:
        return self.outcome == UNVERIFIED


@dataclass
class Corpora:
    """This corpus's name, the siblings it declares, and the refs it could not verify.

    One instance per check run: `unverified` accumulates every reference resolved to a declared
    sibling that is not on disk, and `summary()` turns that into the one note the check prints.
    """

    own: str = ""
    declared: Mapping[str, str] = field(default_factory=dict)
    #: Requirement-register prefixes a sibling OWNS: `{prefix: sibling name}`. A bare id in an
    #: owned prefix (`FLT-104`) is that sibling's row, resolved exactly as `fleet:FLT-104` is.
    owned: Mapping[str, str] = field(default_factory=dict)
    root: Path = field(default_factory=Path)
    #: The planning tiers' id prefixes and the kind each names (`CAP` -> capability, `PG` ->
    #: program, `SL` -> slice): what a prose reader needs to tell `fleet:CAP-1408` (a
    #: capability) from `fleet:FLT-104` (a requirement row), which share one shape.
    id_kinds: Mapping[str, str] = field(default_factory=lambda: dict(_DEFAULT_ID_KINDS))
    unverified: list[tuple[str, str]] = field(default_factory=list)
    #: Problems reading a sibling (its config refused) — printed with the summary.
    problems: list[str] = field(default_factory=list)
    _config_noted: set[str] = field(default_factory=set, repr=False)

    @classmethod
    def of(cls, kb: Any) -> Corpora:
        """The corpus declarations of a `KnowledgeBase` (its `[fleet.planning]` table)."""
        config = getattr(kb, "config", None)
        table = getattr(config, "planning", None)
        table = table if isinstance(table, Mapping) else {}
        root = Path(getattr(kb, "root", Path.cwd()))
        return cls.from_table(table, root, config)

    @classmethod
    def from_table(cls, table: Mapping[str, Any], root: Path, config: Any = None) -> Corpora:
        validate_planning_table(table, config)
        paths, owned = split_corpora(table.get("corpora") or {})
        kinds = {
            str(table.get(key) or getattr(config, key, None) or default): kind for key, default, kind in _ID_KIND_KEYS
        }
        return cls(own=str(table.get("corpus") or ""), declared=paths, owned=owned, root=root, id_kinds=kinds)

    @classmethod
    def at(cls, root: Path) -> Corpora:
        """The corpus declarations of the config FILE governing `root` — what a script entry
        point holding only a path uses, so it reads exactly what `fleet_knowledge check` reads.
        A fresh instance every call (the run state is per instance); the parse is cached."""
        from .config import config_from_table, find_config_file  # noqa: PLC0415

        found = find_config_file(root)
        if found is None:
            return cls(root=root)
        path, table = found
        key = (str(path), path.stat().st_mtime_ns)
        if key not in _AT_CACHE:
            config = config_from_table(table, path)
            planning = config.planning if isinstance(config.planning, Mapping) else {}
            _AT_CACHE[key] = (planning, config)
        planning, config = _AT_CACHE[key]
        return cls.from_table(planning, root, config)

    def reset(self) -> None:
        """Forget what one run accumulated (unverified refs, sibling problems)."""
        self.unverified.clear()
        self.problems.clear()
        self._config_noted.clear()

    # --- the names ---

    def known(self, name: str | None) -> bool:
        """Whether `name` is this corpus or a declared sibling."""
        return bool(name) and (name == self.own or name in self.declared)

    @property
    def names(self) -> frozenset[str]:
        """Every name a prose reader should recognise as a qualifier."""
        return frozenset(self.declared) | ({self.own} if self.own else set())

    def mask_sibling_links(self, text: str, citing: Path | None) -> str:
        """`text` with every markdown link whose TARGET lies under a declared sibling's directory
        blanked whole — `[the scheduler](../../fleet/knowledge/prds/0899-x/prd.md)` names the
        sibling's 0899 by path, and a bare scan would read it as this corpus's. Resolved
        relative to `citing` (the file the text is in); a sibling need not be on disk."""
        if citing is None or not self.declared or "](" not in text:
            return text
        dirs = [os.path.normpath(self.root / rel) for rel in self.declared.values() if rel]
        if not dirs:
            return text
        base = citing.parent

        def blank(m: re.Match[str]) -> str:
            target = m.group(2).split("#", 1)[0].strip()
            if not target or "://" in target:
                return m.group(0)
            where = os.path.normpath(base / target)
            if any(where == d or where.startswith(d + os.sep) for d in dirs):
                return " " * len(m.group(0))
            return m.group(0)

        return _LINK_RE.sub(blank, text)

    def kind_of(self, rid: str) -> str:
        """What a prefixed id names: a capability, program or slice by its planning prefix,
        otherwise a requirement row."""
        m = _PREFIXED_ID_RE.match(str(rid).strip().strip("`").strip())
        return self.id_kinds.get(m.group(1), REQUIREMENT) if m else REQUIREMENT

    def owner_of(self, rid: str) -> str | None:
        """The sibling owning a BARE id's prefix (`FLT-104` -> `fleet`), or None."""
        m = _PREFIXED_ID_RE.match(str(rid).strip().strip("`").strip())
        return self.owned.get(m.group(1)) if m else None

    def route(self, ref: Ref) -> Ref:
        """`ref` with an owned prefix's sibling made explicit: bare `FLT-104` -> `fleet:FLT-104`."""
        if ref.corpus is None and (owner := self.owner_of(ref.id)):
            return Ref(owner, ref.id)
        return ref

    def canonical(self, text: str) -> str:
        """One spelling per row: own-qualified -> bare, an owned prefix -> its owner's qualified
        form, else as written. `FLT-104`, `fleet:FLT-104` and the (erroneous) own-qualified
        `acme:FLT-104` all compare equal when `fleet` owns `FLT`."""
        ref = parse_ref(text)
        if (ref.corpus is None or ref.corpus == self.own) and (owner := self.owner_of(ref.id)):
            return str(Ref(owner, ref.id))
        return ref.id if self.is_local(ref) else str(ref)

    def is_local(self, ref: Ref) -> bool:
        """A bare or own-qualified id — unless its prefix is owned by a sibling, when it is
        that sibling's (bare) or a contradiction the resolver reports (own-qualified)."""
        if ref.corpus is not None and not (self.own and ref.corpus == self.own):
            return False
        return self.owner_of(ref.id) is None

    def localize(self, text: str) -> str | None:
        """The local id `text` names (bare, or qualified with the own name), or None."""
        ref = parse_ref(text)
        return ref.id if self.is_local(ref) else None

    def _declared_list(self) -> str:
        names = ", ".join(f"`{n}`" for n in sorted(self.declared)) or "none"
        own = f"; this corpus is `{self.own}`" if self.own else "; this corpus names itself nothing (`corpus` unset)"
        return f"declared corpora: {names}{own}"

    # --- resolving ---

    def _malformed(self, ref: Ref) -> str | None:
        """Why a qualified id is not in its canonical spelling, or None."""
        if ref.corpus is None or _TYPED_ID_RE.match(ref.id):
            return None
        return f"`{ref}` is not a well-formed id: ids are uppercase — write `{ref.corpus}:{ref.id.upper()}`"

    def _undeclared(self, ref: Ref) -> str:
        name = str(ref.corpus)
        guess = name.lower()
        meant = (
            f"; corpus names are lowercase — did you mean `{guess}:{ref.id}`?"
            if guess != name and self.known(guess)
            else ""
        )
        return (
            f"`{ref}` is qualified with corpus `{name}`, which this corpus does not declare "
            f"({self._declared_list()}){meant} — declare it under `[fleet.planning.corpora]` in "
            ".fleet/fleet.toml, or correct the qualifier"
        )

    def qualifier_problem(self, ref: Ref) -> str | None:
        """What is wrong with a qualified reference BEFORE any lookup — a non-canonical id or a
        corpus this one does not declare — or None. The same message `resolve` reports; for a
        reader that only collects references (to compare them) and would otherwise keep a
        wrong spelling as a distinct entry or drop it."""
        if ref.corpus is None:
            return None
        if problem := self._malformed(ref):
            return problem
        if not self.known(ref.corpus):
            return self._undeclared(ref)
        return None

    def path_of(self, name: str) -> Path | None:
        """The sibling's knowledge dir when declared with a path that exists, else None."""
        rel = self.declared.get(name, "")
        if not rel:
            return None
        p = (self.root / rel).expanduser()
        return p if p.is_dir() else None

    def index(self, name: str) -> SiblingIndex | None:
        p = self.path_of(name)
        if p is None:
            return None
        idx = load_index(p, self.root)
        if idx.config_problem and name not in self._config_noted:
            self._config_noted.add(name)
            self.problems.append(
                f"corpus `{name}`: its own config could not be read ({idx.config_problem}) — it was "
                "indexed with the default layout, so a miss there may be this, not a stale pin"
            )
        return idx

    def resolve(self, ref: Ref | str, kind: str, *, where: str = "") -> Resolution:
        """Resolve one reference of `kind`. `where` names the citing site for the summary."""
        written = parse_ref(ref) if isinstance(ref, str) else ref
        # A journey is named by its slug (`acme:check-result`), never a typed id.
        if kind != JOURNEY and (problem := self._malformed(written)):
            return Resolution(written, MALFORMED, problem)
        if written.corpus is not None and written.corpus == self.own and (owner := self.owner_of(written.id)):
            return Resolution(
                written,
                MISQUALIFIED,
                f"`{written}` is qualified with this corpus's own name, but prefix "
                f"`{written.id.split('-', 1)[0]}` is owned by corpus `{owner}` — a register prefix names "
                f"one register; write `{written.id}` (or `{owner}:{written.id}`)",
            )
        r = self.route(written)
        if self.is_local(r):
            return Resolution(Ref(None, r.id), LOCAL)
        name = str(r.corpus)
        noun = _KIND_NOUN.get(kind, kind)
        # A bare id routed by its prefix is reported as written, with the reason it went abroad.
        shown = (
            f"{written}` (prefix `{written.id.split('-', 1)[0]}` is owned by corpus `{name}`)"
            if written.corpus is None
            else f"{r}`"
        )
        if name not in self.declared:
            return Resolution(r, UNDECLARED, self._undeclared(r))
        idx = self.index(name)
        if idx is None:
            rel = self.declared.get(name, "")
            why = "with no path" if not rel else f"at `{rel}`, which is not on disk here"
            self.unverified.append((str(r), where))
            return Resolution(
                r, UNVERIFIED, f"`{shown} names corpus `{name}`, declared {why} — the {noun} cannot be verified"
            )
        record = idx.record(kind, r.id)
        if record is None:
            return Resolution(
                r,
                MISSING,
                f"`{shown} does not resolve: corpus `{name}` (at `{self.declared[name]}`) has no {noun} "
                f"`{r.id}` — the sibling may be pinned behind (a submodule pin not bumped yet); bump "
                "it, or correct the id",
            )
        return Resolution(r, FOUND, record=record)

    def summary(self) -> str | None:
        """The one note a check prints about the references it could not verify, or None."""
        if not self.unverified:
            return "; ".join(self.problems) or None
        names = sorted({parse_ref(t).corpus or "" for t, _ in self.unverified})
        shown = [f"{t} ({w})" if w else t for t, w in self.unverified[:12]]
        more = f" … and {len(self.unverified) - 12} more" if len(self.unverified) > 12 else ""
        return "; ".join(
            [
                f"{len(self.unverified)} unverified cross-corpus ref(s): corpus "
                f"{', '.join(f'`{n}`' for n in names)} is declared but not on disk here, so these were "
                f"not checked: {', '.join(shown)}{more}",
                *self.problems,
            ]
        )


def iter_entries(entries: Iterable[str]) -> Iterator[Ref]:
    """`parse_ref` over a list of authored entries, empties dropped."""
    for e in entries:
        if str(e).strip():
            yield parse_ref(e)
