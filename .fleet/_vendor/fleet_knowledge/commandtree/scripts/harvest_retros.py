#!/usr/bin/env python3
"""Harvest the retro corpus into a digest of actionable suggestions.

Reads knowledge/retros/{prd,task,bug}/*.md — in this repo **and in every sibling lane
repo that carries its own corpus** (ENG-9973: a run whose deliverable PR lives in a lane
repo commits its retro into the lane repo's own corpus, riding the lane deliverable PR) —
and extracts suggestions from every
suggestion-bearing section — the `## Suggestions (NOT applied)` tables and the inline
**Suggestion:**-marked bullets under `## Recurring-friction flag` sections (see PRD 0252).
Section headings are matched by a normalized, case-insensitive *prefix* (parenthetical
qualifiers stripped) so future wording drift never silently drops a section. Groups
identical suggestions by recurrence (the same idea in N retros is the promote signal),
guesses the target file (a spec / command / SOP), and prints a ranked markdown digest.
Also counts retros carrying a `## Recurring …` / `## Friction …` section.

This is the *mechanical* half of the process-improvement loop — it edits NOTHING. The
`process:improve` command reads this digest and applies (additive) or proposes
(rule-changing) the edits.

**Resolved-suggestion ledger** (`scripts/harvest-ledger.jsonl`, stdlib JSONL, not part of
the retro corpus — retros themselves are never edited). Each row is `{hash, status, resolved,
note}`: `hash` is a stable digest of (retro-relative-path + normalized suggestion text), so
a resolution applies to *that occurrence* only — if the same suggestion resurfaces in a
*future* retro, it's a new hash and reappears (the friction wasn't actually fixed). `status`
is `applied`, `already-satisfied`, or `declined` (a deliberate rejection, the reason in
`note`). By default, occurrences present in the ledger are
omitted from the digest and don't count toward the recurrence `×`; pass `--all` to also
list resolved occurrences (tagged `[resolved: <status>]`). Append a row with:

    python3 knowledge/scripts/harvest_retros.py --resolve <hash> <applied|already-satisfied> [note]

(`--mark` is an accepted alias for `--resolve`.) The `Hash` column in the digest gives the
hash for each surviving occurrence.

Above the table it prints two aids the exact-match `×` count can't give: a **Recurring**
summary — suggestions the author self-flagged as recurring ("3rd occurrence", "keeps
recurring") plus groups that share a distinctive artifact token — and, under `--probe`, a
**Likely already built** section that greps the code/tooling tree for each surviving
suggestion's named artifact, so an already-implemented lint/check/doc isn't re-proposed.

Run: python3 knowledge/scripts/harvest_retros.py [--since YYYY-MM-DD] [--all] [--probe]
     python3 knowledge/scripts/harvest_retros.py --resolve <hash> <status> [note]
Stdlib only.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

REPO = _repo.repo_root()
K = REPO / "knowledge"
RETROS = K / "retros"
SOURCES = ["prd", "task", "bug"]
LEDGER = REPO / "scripts" / "harvest-ledger.jsonl"
# `declined` records a deliberate rejection (ENG-12809): without it a suggestion judged not
# worth doing could only be mislabelled or left to re-surface on every run.
RESOLVE_STATUSES = ("applied", "already-satisfied", "declined")
# Test override: explicit lane-repo roots (no discovery). None = discover siblings
# of REPO automatically.
LANE_REPOS: list[Path] | None = None

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
# Any markdown heading of level >= 2, capturing its title text.
HEAD_RE = re.compile(r"^#{2,}[ \t]+(.+?)[ \t]*$", re.M)
# A bullet carrying an explicit **Suggestion:** / **Suggestions (not applied):** marker;
# group(1) is the suggestion text that follows the marker.
SUGG_BULLET_RE = re.compile(r"\*\*suggestions?\b[^*]*?\*\*[:\s]*(.+)$", re.I)
# Suggestion-bearing sections we harvest, matched by *normalized heading prefix* (see
# head_key) so parenthetical qualifiers — "(NOT applied — for later review)",
# "(record + suggest only)", "(vs recent retros)" — and future wording drift never
# silently drop a section. "recurring-friction flag" is the 0252-style variant whose
# **Suggestion:** bullets were previously invisible.
SUGG_HEAD_PREFIXES = ("suggestions", "recurring-friction flag")
# Sections that merely *flag* recurrence/friction (counted, not necessarily harvested).
RECUR_HEAD_PREFIXES = ("recurring", "friction")
TARGET_RE = re.compile(
    r"(specs/[\w./-]+\.md|\.(?:claude|fleet)/commands/[\w./-]+|sops/[\w./-]+\.md|/[a-z][a-z0-9-]*:[\w:-]+"
    r"|policylint|pre-commit|contract)",
    re.I,
)


def origin_slug(path: Path) -> str:
    """`org/name` of an ARBITRARY checkout's `origin` remote, normalized and lowercase;
    empty when the remote cannot be read. `_repo.slug()` answers this for *this* checkout
    only (and off its own cached root) — the lane filter below needs the same fact for a
    sibling, which is why it reads one here. Never raises."""
    try:
        url = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""
    if not url:
        return ""
    tail = url.rsplit(":", 1)[-1] if url.startswith("git@") else "/".join(url.rstrip("/").split("/")[-2:])
    return tail.removesuffix(".git").lower()


def root_commits(path: Path) -> frozenset[str]:
    """The root commit(s) of an ARBITRARY checkout — the repository's identity, independent of
    what its `origin` URL happens to say (ENG-12809). A repo renamed or transferred on the forge
    keeps its root commit, so a clone still pointing at the old name is recognisably the same
    repository offline. Empty when unreadable (no commits yet, not a repo). Never raises."""
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "rev-list", "--max-parents=0", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return frozenset()
    return frozenset(out.split())


def _named_for(checkout: Path, slug: str) -> bool:
    return checkout.name.lower() == slug.rsplit("/", 1)[-1]


def _prefer_lane(candidate: Path, candidate_slug: str, incumbent: Path, incumbent_slug: str) -> bool:
    """Whether `candidate` beats the checkout already chosen for a repository. The checkout
    whose directory name matches its own remote's repo name is the lane's canonical checkout
    (the others are worktrees/copies of it). Each side is judged against ITS OWN slug, since
    one repository can be checked out under two remote names (ENG-12809). Ties keep the
    incumbent, so discovery stays deterministic."""
    return _named_for(candidate, candidate_slug) and not _named_for(incumbent, incumbent_slug)


def sibling_retro_repos() -> list[Path]:
    """Sibling lane repos (repos sitting beside this checkout) that carry their own
    retro corpus (ENG-9973): a run whose deliverable PR lives in a lane repo commits
    its retro into the lane repo's own knowledge/retros/{prd,task,bug}/, so the digest
    sweeps those corpora alongside this repo's. A checkout without lane-repo siblings
    (the common human clone) sweeps nothing extra.

    A sibling is a lane only when its `origin` is a *different* repository from this
    checkout's (ENG-12610): a workstation keeps many clones and worktrees of the SAME
    repo side by side, and sweeping those as corpora inflated the digest ~48× — every `×`
    counted copies of one retro, and the ledger could never settle because
    `suggestion_hash()` keys on the copy's name too. Each distinct remote is counted ONCE,
    preferring the checkout whose directory name matches the repo name; a sibling with no
    readable `origin` is left out, because it cannot be told apart from another copy of
    this repo.

    A URL is not the whole identity, though: a clone whose origin still reads the repo's
    pre-rename name (`old-org/old-name`, which the forge redirects) passes a slug comparison. So
    two checkouts are one repository when they share a remote slug OR a ROOT COMMIT (ENG-12809):
    a sibling sharing a root commit with this checkout is this repo, and lanes reached under two
    remote names collapse to one. A differing root never SPLITS a shared slug — a shallow clone
    reports its depth boundary as its root, so two shallow clones of one lane disagree on it.
    The root commit is read only for siblings whose slug already differs from this checkout's,
    so the common clone-of-this-repo case stays one cheap `git remote` call. Never raises."""
    if LANE_REPOS is not None:
        return [Path(p) for p in LANE_REPOS]
    parent = REPO.parent
    try:
        children = sorted(parent.iterdir()) if parent.is_dir() else []
    except OSError:
        return []
    own = origin_slug(REPO)
    own_roots = root_commits(REPO)
    lanes: list[tuple[set[str], set[str], str, Path]] = []  # (slugs, roots, kept slug, kept checkout)
    for child in children:
        if not child.is_dir() or child == REPO or child.name.startswith("."):
            continue
        if not (child / ".git").exists():
            continue
        retros = child / "knowledge" / "retros"
        if not any((retros / src).is_dir() for src in SOURCES):
            continue
        slug = origin_slug(child)
        if not slug or (own and slug == own):
            continue  # this repo itself, or a checkout we cannot prove is a lane
        roots = root_commits(child)
        if roots & own_roots:
            continue  # this repo under another remote name
        same = next((lane for lane in lanes if slug in lane[0] or roots & lane[1]), None)
        if same is None:
            lanes.append(({slug}, set(roots), slug, child))
            continue
        same[0].add(slug)
        same[1].update(roots)
        if _prefer_lane(child, slug, same[3], same[2]):
            lanes[lanes.index(same)] = (same[0], same[1], slug, child)
    return sorted((lane[3] for lane in lanes), key=lambda p: p.name)


def retro_date(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^date:\s*(\S+)", text, re.M)
    if m:
        return m.group(1)
    fn = DATE_RE.search(path.stem)
    return fn.group(1) if fn else ""


def head_key(title: str) -> str:
    """Normalize a heading's text for prefix matching: drop code ticks, strip one
    trailing parenthetical qualifier, collapse whitespace, lowercase. So
    `## Recurring-friction flag (record + suggest only)` → `recurring-friction flag`
    and `## Suggestions (NOT applied — for later review)` → `suggestions`."""
    t = re.sub(r"`+", "", title)
    t = re.sub(r"\s*\([^)]*\)\s*$", "", t)  # drop a trailing (...) qualifier
    return re.sub(r"\s+", " ", t).strip().lower()


def is_suggestions_head(title: str) -> bool:
    k = head_key(title)
    return any(k.startswith(p) for p in SUGG_HEAD_PREFIXES)


def is_recurring_head(title: str) -> bool:
    k = head_key(title)
    return any(k.startswith(p) for p in RECUR_HEAD_PREFIXES)


def sections(text: str) -> list[tuple[str, str]]:
    """(title, body) for each markdown section (>= level-2 heading → next heading)."""
    heads = list(HEAD_RE.finditer(text))
    out: list[tuple[str, str]] = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        out.append((m.group(1), text[m.end() : end]))
    return out


def table_rows(body: str) -> list[list[str]]:
    """Rows (list of cells) of the first markdown table in a section body."""
    rows: list[list[str]] = []
    started = False
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("|"):
            started = True
            rows.append([c.strip() for c in s.strip("|").split("|")])
        elif started:
            break
    return rows


def logical_bullets(body: str) -> list[str]:
    """Each markdown list item as one string, soft-wrapped continuation lines merged."""
    out: list[str] = []
    cur: str | None = None
    for line in body.splitlines():
        if re.match(r"^\s*(?:[-*]|\d+\.)\s+", line):
            if cur is not None:
                out.append(cur)
            cur = line.strip()
        elif cur is not None:
            if not line.strip():
                out.append(cur)
                cur = None
            else:
                cur += " " + line.strip()
    if cur is not None:
        out.append(cur)
    return out


def suggestions_in(body: str) -> list[tuple[str, str]]:
    """(text, lever) suggestions from a suggestion-bearing section body — both the
    markdown-table form (`## Suggestions` tables) and the inline **Suggestion:**-marked
    bullet form used under `## Recurring-friction flag` sections (e.g. PRD 0252)."""
    out: list[tuple[str, str]] = []
    for row in table_rows(body):
        first = row[0] if row else ""
        if not first or set(first) <= set("-: ") or first.lower() == "suggestion":
            continue  # skip the header / separator rows
        out.append((first, row[1] if len(row) > 1 else ""))
    for bullet in logical_bullets(body):
        m = SUGG_BULLET_RE.search(bullet)
        if m:
            out.append((m.group(1).strip(), ""))
    return out


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"`+", "", s).lower()).strip(" .")


def target(text: str) -> str:
    m = TARGET_RE.search(text)
    return m.group(1) if m else "unclassified"


def suggestion_hash(retro_rel: str, text: str) -> str:
    """Stable hash of one suggestion *occurrence* (a specific retro + suggestion text),
    not of the suggestion alone — so resolving it never hides the same friction if it
    resurfaces, verbatim, in a later retro (a new retro path → a new hash → unresolved)."""
    digest = hashlib.sha256(f"{retro_rel}\x00{norm(text)}".encode())
    return digest.hexdigest()[:12]


# --- Recurrence surfacing (C) + "already built?" probe (B) ------------------
# The `×` column counts only *character-identical* suggestions, so recurrence is
# invisible for anything paraphrased. In practice recurrence lives in two places:
# the retro author's own prose ("3rd occurrence", "keeps recurring") and a shared
# distinctive artifact token across otherwise-different suggestions. We surface
# both above the table. The probe greps the tree for a suggestion's named artifact
# so an already-built lint/check/doc isn't proposed as fresh work.

_STOP = frozenset(
    [
        "a",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "before",
        "after",
        "all",
        "also",
        "been",
        "but",
        "by",
        "can",
        "cant",
        "could",
        "dont",
        "each",
        "every",
        "for",
        "from",
        "get",
        "had",
        "has",
        "have",
        "instead",
        "into",
        "is",
        "it",
        "its",
        "make",
        "more",
        "most",
        "need",
        "needs",
        "new",
        "not",
        "note",
        "of",
        "on",
        "once",
        "one",
        "only",
        "or",
        "our",
        "per",
        "prefer",
        "rather",
        "run",
        "should",
        "since",
        "so",
        "than",
        "that",
        "the",
        "them",
        "then",
        "there",
        "this",
        "to",
        "use",
        "using",
        "via",
        "was",
        "what",
        "when",
        "where",
        "which",
        "while",
        "with",
        "would",
        "you",
        "your",
        "document",
        "documenting",
        "pattern",
        "suggestion",
        "suggestions",
        "retro",
        "fix",
        "fixed",
        "bug",
        "case",
        "class",
        "time",
        "doesnt",
        "wont",
        "detects",
        "adds",
        "flag",
        "flags",
        "check",
        "checks",
        "step",
    ]
)
# Artifact-shaped tokens a reader would grep for: dotted/slashed paths (foo.go,
# internal/db/x, s.EventBus), CamelCase idents (GetAgentByID), snake_case names.
ARTIFACT_RE = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?:[./][A-Za-z0-9_]+)+"
    r"|[A-Za-z_][A-Za-z0-9_]*[A-Z][A-Za-z0-9_]*"
    r"|[a-z0-9]+_[a-z0-9_]+"
)
# Explicit self-flagged recurrence — the retro author saying "this recurred". The
# strongest signal, and the one the exact-match count misses entirely.
RECUR_RE = re.compile(
    r"\b\d+(?:st|nd|rd|th)\+?\s+(?:occurrence|retro|time|run)s?\b"
    r"|\b\d+\+?\s+(?:runs|retros|times)\b"
    r"|\bnow the \d"
    r"|\bkeeps? recurring\b|\brecurring\b"
    r"|\bindependently rediscover|\bconfirmed across\b|\bweeks? afterward\b"
    r"|\bre-?derive|\bevery (?:execute )?(?:command|run)\b",
    re.I,
)


def artifact_tokens(text: str) -> list[str]:
    """Identifier / path / filename tokens the suggestion names — backtick-quoted
    spans first (highest signal), then artifact-shaped bare tokens. Deduped, capped."""
    seen: dict[str, None] = {}
    for chunk in [*re.findall(r"`([^`]+)`", text), text]:
        for m in ARTIFACT_RE.finditer(chunk):
            tok = m.group(0).strip("._/")
            if len(tok) >= 4 and tok.lower() not in _STOP:
                seen.setdefault(tok, None)
    return list(seen)[:8]


def recurrence_flag(text: str) -> str | None:
    """The self-declared-recurrence phrase in a suggestion (`3rd occurrence`,
    `keeps recurring`, `confirmed across 3+ runs`), or None. The author flagged it."""
    m = RECUR_RE.search(text)
    return m.group(0).strip() if m else None


def is_specific(tok: str) -> bool:
    """Whether an artifact token is specific enough that a repo grep hit means the
    thing *exists* — not a bare acronym / english slash-phrase that matches anything."""
    if re.fullmatch(r"[A-Za-z]{2,6}s?", tok):  # YAML, HTTP, PRDs, REST, FAST, TODO
        return False
    return bool(
        re.search(r"[a-z][A-Z]", tok)  # CamelCase: GetAgentByID, EventBus
        or re.search(r"\.[A-Z]", tok)  # pkg.Symbol: assert.Equal, Service.Append
        or "_" in tok  # snake / CONST: no_bypass_send, GO_RACE
        or re.search(r"\.(go|py|ts|tsx|js|mjs|md|sh|ya?ml|json|sql|txt)$", tok)  # filename
        or re.match(r"(internal|cmd|scripts|packages|api|contracts|migrations)/", tok)  # path
    )


def theme_index(rows: list[dict[str, Any]]) -> dict[str, list[int]]:
    """token -> row indices, for distinctive *specific* artifact tokens shared by 2..6
    rows (a token in >6 rows is too generic to be a theme). Groups suggestions that
    name the same thing even when the surrounding wording differs entirely."""
    idx: dict[str, set[int]] = {}
    for i, r in enumerate(rows):
        for tok in {t.lower() for t in artifact_tokens(r["text"]) if is_specific(t)}:
            idx.setdefault(tok, set()).add(i)
    return {t: sorted(m) for t, m in idx.items() if 2 <= len(m) <= 6}


# Injectable so the unit tests can exercise probe wiring without a git repo.
def _grep_repo(token: str) -> list[str]:
    """Tracked code/tooling files literally containing `token` (never the retro
    corpus). Empty on any failure — not a git repo, git missing, timeout, no match."""
    try:
        r = subprocess.run(
            [
                "git",
                "-C",
                str(REPO),
                "grep",
                "-lFI",
                "-e",
                token,
                "--",
                "internal",
                "cmd",
                "scripts",
                "packages",
                ".claude",
                ".fleet",
                "Makefile",
                ".pre-commit-config.yaml",
                "knowledge/specs",
                # exclude this loop's own artifacts — the ledger + script echo
                # suggestion text and would self-match.
                ":!scripts/harvest-ledger.jsonl",
                ":!knowledge/scripts/harvest_retros.py",
                ":!scripts/harvest_retros_test.py",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return [ln for ln in r.stdout.splitlines() if ln] if r.returncode == 0 else []


def probe_rows(rows: list[dict[str, Any]], cap: int = 300) -> list[dict[str, str]]:
    """Grep the code/tooling tree for each surviving row's artifact tokens; return
    the first hit per row so the reviewer can skip suggestions already built."""
    hits: list[dict[str, str]] = []
    cache: dict[str, list[str]] = {}
    probed = 0
    for r in rows:
        for tok in artifact_tokens(r["text"]):
            if not is_specific(tok):
                continue
            if tok not in cache:
                if probed >= cap:
                    cache[tok] = []
                else:
                    cache[tok] = _grep_repo(tok)
                    probed += 1
            if cache[tok]:
                hits.append({"text": r["text"], "token": tok, "path": cache[tok][0]})
                break
    return hits


def load_ledger(path: Path | None = None) -> dict[str, dict[str, str]]:
    """hash -> latest {status, resolved, note} row (a later row for the same hash wins)."""
    path = path if path is not None else LEDGER
    ledger: dict[str, dict[str, str]] = {}
    if not path.exists():
        return ledger
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        ledger[row["hash"]] = row
    return ledger


def append_ledger_row(hash_: str, status: str, note: str, path: Path | None = None) -> None:
    path = path if path is not None else LEDGER
    row = {"hash": hash_, "status": status, "resolved": datetime.date.today().isoformat(), "note": note}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")


def resolve_cmd(argv: list[str]) -> int:
    flag = "--resolve" if "--resolve" in argv else "--mark"
    rest = argv[argv.index(flag) + 1 :]
    if len(rest) < 2:
        print(f"usage: harvest_retros.py {flag} <hash> <{'|'.join(RESOLVE_STATUSES)}> [note]", file=sys.stderr)
        return 2
    hash_, status, *note_parts = rest
    if status not in RESOLVE_STATUSES:
        print(f"error: status must be one of {RESOLVE_STATUSES}, got {status!r}", file=sys.stderr)
        return 2
    append_ledger_row(hash_, status, " ".join(note_parts))
    print(f"resolved {hash_} as {status}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--resolve" in argv or "--mark" in argv:
        return resolve_cmd(argv)

    since = argv[argv.index("--since") + 1] if "--since" in argv else ""
    show_all = "--all" in argv
    probe = "--probe" in argv
    ledger = load_ledger()

    roots: list[tuple[str, Path]] = [("", RETROS)]
    roots += [(p.name, p / "knowledge" / "retros") for p in sibling_retro_repos()]

    groups: dict[str, dict[str, Any]] = {}
    recurring_flags = 0
    n_retros = 0
    lane_counts: list[tuple[str, int]] = []
    for repo_name, retros_dir in roots:
        n_here = 0
        for src in SOURCES:
            base = retros_dir / src
            if not base.exists():
                continue
            for f in sorted(base.glob("*.md")):
                if f.name in ("README.md", "_TEMPLATE.md"):
                    continue
                if since and (d := retro_date(f)) and d < since:
                    continue
                n_here += 1
                text = f.read_text(encoding="utf-8")
                has_recurring = False
                for title, body in sections(text):
                    if is_recurring_head(title):
                        has_recurring = True
                    if not is_suggestions_head(title):
                        continue
                    for stext, lever in suggestions_in(body):
                        key = norm(stext)
                        if not key:
                            continue
                        rel = f"{src}/{f.name}" if not repo_name else f"{repo_name}:{src}/{f.name}"
                        g = groups.setdefault(key, {"text": stext, "lever": lever, "occurrences": []})
                        g["occurrences"].append({"src": rel, "hash": suggestion_hash(rel, stext)})
                if has_recurring:
                    recurring_flags += 1
        if repo_name:
            lane_counts.append((repo_name, n_here))
        n_retros += n_here

    def fmt_occ(o: dict[str, str]) -> str:
        row = ledger.get(o["hash"])
        return f"{o['src']} [resolved: {row['status']}]" if row else o["src"]

    rows = []
    for g in groups.values():
        unresolved = [o for o in g["occurrences"] if o["hash"] not in ledger]
        if not show_all and not unresolved:
            continue  # every occurrence of this suggestion is already settled
        display = g["occurrences"] if show_all else unresolved
        rows.append({"text": g["text"], "lever": g["lever"], "count": len(unresolved), "display": display})

    out: list[str] = []
    scope = f" since {since}" if since else ""
    out.append(f"# Retro harvest — {len(rows)} distinct suggestions across {n_retros} retros{scope}")
    out.append("")
    out.append(f"{recurring_flags} retros flagged a Recurring/Friction section.")
    if lane_counts:
        out.append(
            "Lane-repo corpora swept (ENG-9973): " + ", ".join(f"{name} {count}" for name, count in lane_counts) + "."
        )
    out.append("")

    # C — Recurrence surfacing the exact-match `×` column can't see: self-flagged
    # recurrence (author said so) + suggestions sharing a distinctive artifact token.
    def cell(s: str) -> str:
        return s.replace("\n", " ").replace("|", "\\|")

    flagged = [(sig, r["text"]) for r in rows if (sig := recurrence_flag(r["text"]))]
    themes = theme_index(rows)
    if flagged or themes:
        out.append(f"## Recurring — prioritize ({len(flagged)} self-flagged, {len(themes)} shared-token theme(s))")
        out.append("")
        if flagged:
            out.append("Self-flagged (the retro author marked it recurring):")
            out.append("")
            out.append("| signal | Suggestion |")
            out.append("|---|---|")
            for sig, stext in sorted(flagged, key=lambda x: x[1].lower()):
                out.append(f"| {cell(sig)} | {cell(stext)} |")
            out.append("")
        if themes:
            out.append("Shared-artifact themes (same distinctive token in ≥2 suggestions):")
            out.append("")
            out.append("| token | × | Suggestions |")
            out.append("|---|---|---|")
            for tok, idxs in sorted(themes.items(), key=lambda kv: (-len(kv[1]), kv[0])):
                snippets = "; ".join(cell(rows[i]["text"][:60].rstrip()) + "…" for i in idxs)
                out.append(f"| `{tok}` | {len(idxs)} | {snippets} |")
            out.append("")

    # B — "already built?" probe (opt-in): flag surviving suggestions whose named
    # artifact already exists in the tree, so an already-implemented lint/check/doc
    # isn't proposed as fresh work. `git grep` needs a real repo → empty otherwise.
    if probe:
        hits = probe_rows(rows)
        out.append(f"## Likely already built — verify before proposing ({len(hits)} probe hit(s))")
        out.append("")
        if hits:
            out.append("| Artifact token | Already in | Suggestion |")
            out.append("|---|---|---|")
            for h in hits:
                out.append(f"| `{h['token']}` | `{h['path']}` | {h['text']} |")
        else:
            out.append("_No surviving suggestion names an artifact that already exists in the tree._")
        out.append("")

    out.append("| × | Target (guess) | Lever | Suggestion | Seen in | Hash |")
    out.append("|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: (-x["count"], x["text"].lower())):
        display = r["display"]
        srcs = ", ".join(fmt_occ(o) for o in display[:4]) + (" …" if len(display) > 4 else "")
        hashes = ", ".join(o["hash"] for o in display[:4]) + (" …" if len(display) > 4 else "")
        out.append(f"| {r['count']} | {target(r['text'])} | {r['lever']} | {r['text']} | {srcs} | {hashes} |")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
