"""Which tests guard a promise, and which test types a feature still lacks (PRD 0998).

The desk shows that a test exists. It never decides a promise's state: every function here takes
rows and sets and returns rows and sets, and none of them takes or returns a state
(**[FLT-2451]**). A test guards a promise in one of three ways (**[FLT-2448]**):

* a verify run proved it catches a break of that promise — the proof names the test and its file;
* the QA agent wrote it from an approved check — the file sits in the suite QA tests go to, and the
  promise is one a QA test filing named;
* the test names the promise itself, in a ``guards:`` line in its source.

A test that names the promise in a suite the repository has not described is still linked; it just
has no type, so it fills none of the three groups (**[FLT-2474]**). The types are the ones the
repository declares (``QaSuite.type``), never a guess (**[FLT-2447]**).

Stdlib only; no clock, no I/O, no store. The sync reads the marks with ``git grep`` and hands them
here; the route reads the proofs and the filings and hands them here too.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable, Mapping, Sequence
from typing import Any, Final

from .qaplan import TEST_TYPES, QaSuite

__all__ = [
    "MARK_PATTERN",
    "MAX_MARKS",
    "missing_types",
    "proof_file",
    "read_marks",
    "suite_of",
    "test_links",
]

#: The most marks one reading keeps. More than this reads as ``cut`` and the desk shows no tests,
#: because half a list would state false gaps (**[FLT-2473]**).
MAX_MARKS: Final = 5000

#: The mark a test writes in its source, as a POSIX extended regular expression for ``git grep -E``.
#:
#: An id is ``CAP-1234``, ``FLT-1157`` or ``<journey>#<n>``. The leading group is a line start or a
#: character that cannot be in a word, so ``safeguards:`` is not a mark. ``-o`` prints only this
#: match, so a minified file cannot fill memory.
MARK_PATTERN: Final = (
    r"(^|[^[:alnum:]_])guards:[[:space:]]*"
    r"[[:alnum:]][[:alnum:]_-]*[#-][[:digit:]]+"
    r"([[:space:]]*,[[:space:]]*[[:alnum:]][[:alnum:]_-]*[#-][[:digit:]]+)*"
)

#: One id, with the same word boundary the grep pattern uses.
_ID_RE: Final = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z][A-Za-z0-9_-]*[#-][0-9]+)(?![A-Za-z0-9_])")

#: The id list inside one mark.
_MARK_RE: Final = re.compile(
    r"(?<![A-Za-z0-9_])guards:[ \t]*"
    r"((?:[A-Za-z][A-Za-z0-9_-]*[#-][0-9]+)(?:[ \t]*,[ \t]*(?:[A-Za-z][A-Za-z0-9_-]*[#-][0-9]+))*)"
)

#: The verdicts whose proof may link a test. An ``incomplete`` or ``blocked`` run proves nothing.
_PROVING_VERDICTS: Final = frozenset({"verified", "merged"})


def _ids(text: str) -> list[str]:
    """The promise ids one mark names, in the order written."""
    found = _MARK_RE.search(text)
    if found is None:
        return []
    return list(_ID_RE.findall(found.group(1)))


def read_marks(matches: Iterable[tuple[str, str]]) -> dict[str, Any]:
    """The ``guards:`` marks a ``git grep`` found, grouped by file.

    ``matches`` are ``(path, text)`` pairs; ``text`` is the matched mark (or the line it sits on).
    The answer is ``{"state": "read" | "cut", "files": [{"path", "promises"}]}``, each file once,
    its ids sorted. More than :data:`MAX_MARKS` marks reads as ``cut`` with no files, so the desk
    states no gap at all rather than a false one.
    """
    rows = list(matches)
    if len(rows) > MAX_MARKS:
        return {"state": "cut", "files": []}
    files: dict[str, set[str]] = {}
    for path, text in rows:
        ids = _ids(str(text))
        if ids:
            files.setdefault(str(path), set()).update(ids)
    return {
        "state": "read",
        "files": [{"path": path, "promises": sorted(ids)} for path, ids in sorted(files.items())],
    }


def proof_file(name: str) -> str:
    """The file a test name gives, or ``""`` when the name gives none.

    The verify command asks for ``<path>::<test>``. The part before ``::`` is the file only when it
    looks like one — it has a ``/`` or a dot — so a bare test name places no file and reads *Type
    not stated* (fork 10).
    """
    head, sep, _tail = str(name).partition("::")
    head = head.strip()
    if not sep or ("/" not in head and "." not in head):
        return ""
    return head


def suite_of(path: str, suites: Sequence[QaSuite]) -> str:
    """The declared type of the suite that holds ``path``, or ``""`` when none does.

    The longest declared ``path`` wins, and a suite path holds a file only at a path boundary, so
    ``tests/unit2/x.py`` is not inside ``tests/unit``.
    """
    best = ""
    found = ""
    for suite in suites:
        root = suite.path.rstrip("/")
        if not root:
            continue
        if (path == root or path.startswith(root + "/")) and len(root) > len(best):
            best, found = root, suite.type
    return found


def _group_for(path: str, suites: Sequence[QaSuite]) -> str:
    """The group a test's file belongs in: one of the three types, or ``unstated``."""
    one = suite_of(path, suites)
    return one if one in TEST_TYPES else "unstated"


def test_links(
    promise_ids: Collection[str],
    marks: Mapping[str, Any],
    proofs: Iterable[Mapping[str, Any]],
    suites: Sequence[QaSuite],
    filed: Collection[str],
    *,
    gone: Collection[str] = (),
    test_suite: str = "",
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """For each promise, the tests that guard it, grouped by type.

    ``marks`` is :func:`read_marks`' answer, ``proofs`` are the verify runs' neuter proofs newest
    first, ``suites`` are the declared suites, ``filed`` is the set of promises a QA test filing
    named, and ``gone`` is the set of proved files no longer tracked at the commit.

    Each group is a list of ``{"test", "how"}``, ``how`` naming ``proved``, ``qa`` or ``named``.
    A proof is kept only from a proving verdict, only when it proved the break, only for this
    repository (the caller filtered), and only while its file is still at the commit. The newest
    result for a (promise, test) decides, so a later *not proved* hides an older proof. A mark and
    a proof of the same file fold into one line that says both. An id the reading does not hold
    links nothing.
    """
    wanted = {str(pid) for pid in promise_ids}
    empty: dict[str, list[dict[str, Any]]] = {one: [] for one in (*TEST_TYPES, "unstated")}
    links: dict[str, dict[str, list[dict[str, Any]]]] = {pid: {k: [] for k in empty} for pid in wanted}

    # The marks first: a file names its promises, and its how is the QA label when the file sits in
    # the QA suite AND a QA filing named that promise. `qa` replaces `named` (fork 11).
    mark_how: dict[str, dict[str, str]] = {}
    mark_state = str(marks.get("state") or "read")
    if mark_state == "read":
        qa_root = ""
        for suite in suites:
            if test_suite and suite.name == test_suite:
                qa_root = suite.path.rstrip("/")
        for row in marks.get("files") or ():
            path = str(row.get("path") or "")
            if not path:
                continue
            for pid in row.get("promises") or ():
                pid = str(pid)
                if pid not in wanted:
                    continue
                in_qa = bool(qa_root) and (path == qa_root or path.startswith(qa_root + "/"))
                how = "qa" if in_qa and pid in filed else "named"
                mark_how.setdefault(path, {})[pid] = how

    # The proofs, newest first: the first row for a (promise, test) decides.
    seen: set[tuple[str, str]] = set()
    for proof in proofs:
        pid = str(proof.get("promise") or "")
        test = str(proof.get("test") or "")
        if pid not in wanted or not test:
            continue
        key = (pid, test)
        if key in seen:
            continue
        seen.add(key)
        if not bool(proof.get("proved")):
            continue
        if str(proof.get("verdict") or "") not in _PROVING_VERDICTS:
            continue
        path = proof_file(test)
        if path and path in gone:
            continue
        proved_how = ["proved"]
        folded = False
        if path:
            mark_word = mark_how.get(path, {}).get(pid)
            if mark_word:
                proved_how.append(mark_word)
                folded = True
        group = _group_for(path, suites) if path else "unstated"
        links[pid][group].append({"test": test, "how": proved_how})
        if folded:
            mark_how[path].pop(pid, None)

    # What is left of the marks is a test that only names the promise.
    for path, by_promise in mark_how.items():
        for pid, named in by_promise.items():
            group = _group_for(path, suites)
            links[pid][group].append({"test": path, "how": [named]})

    return links


def missing_types(
    groups: Sequence[Mapping[str, Any]],
    links: Mapping[str, Mapping[str, Sequence[Mapping[str, Any]]]],
) -> dict[str, list[dict[str, Any]]]:
    """For each feature area, which test types its promises lack, in the desk's words' shape.

    Every promise counts against all three types, whatever its kind, and a test with no stated type
    fills none of them (fork 6, **[FLT-2474]**). Types join into one clause only when exactly the
    same promises lack them, and clauses run largest count first (fork 7). A feature that lacks
    nothing has an empty list.

    ``groups`` are the READING's groups, never a view's: a plain ``view=features`` answer carries
    no promise ids.
    """
    out: dict[str, list[dict[str, Any]]] = {}
    for group in groups:
        area = str(group.get("area") or "")
        lacking: dict[frozenset[str], int] = {}
        for raw in group.get("ids") or ():
            pid = str(raw)
            one = links.get(pid) or {}
            miss = frozenset(one_type for one_type in TEST_TYPES if not one.get(one_type))
            if miss:
                lacking[miss] = lacking.get(miss, 0) + 1
        clauses: list[dict[str, Any]] = [
            {"types": [one for one in TEST_TYPES if one in types], "promises": count}
            for types, count in lacking.items()
        ]
        clauses.sort(key=lambda clause: -int(str(clause["promises"])))
        out[area] = clauses
    return out
