#!/usr/bin/env python3
"""Write and check the second party's records on QA results (FLT-1213, FLT-1214, FLT-1215).

The party that wrote or ran a check never certifies its pass. The `qa:verify` command is that
second party, and this script is the only way it writes down what it found. A check-result file
(`knowledge/audits/results/…`, written by `check_result.py`) is **append-only** — never edited
after the run — so a review cannot be stamped into it after the fact. Every verifier finding is
therefore **its own append-only record** under one home, and the Quality desk's reader
(`fleet_knowledge.quality_reviews`) lays them over the results:

    knowledge/audits/reviews/<kind>/<result-stem>--<YYYY-MM-DD>-<HHMMSS>Z.json   one review
    knowledge/audits/reviews/oracles/<scenario>-v<N>.json                          one decision
    knowledge/audits/reviews/planted/<scenario>-<YYYY-MM-DD>.json                  one outcome

**Append-only is enforced, not promised.** `validate` refuses a malformed record and `append-only`
refuses any change that modifies, renames or deletes an existing record (a diff against the
base); both run in `fleet check` (the `qa-review-records` check) and in CI. Deleting a dispute
would otherwise quietly turn a disputed pass back into an unverified one.

## A review record

    {"schema_version": 1, "record": "review",
     "result_file": "knowledge/audits/results/scenario/2026-10-14-flow-030000Z.json",
     "reviewer": "<the verifier's run id>", "reviewed_at": "<RFC3339>",
     "verdicts": [{"id": "flow#1", "state": "verified|unverified|disputed",
                   "reason": "…", "evidence_checked": ["req_01J…", "observed"],
                   "ticket": "ENG-123"}]}

  * **Only a `pass` is re-graded**, and only in a result that names its `runner` — without one,
    nobody can show the reviewer is not the runner, so the reader ignores any review of it.
  * **From the evidence only.** `evidence_checked` names the verdict's own request ids, audit-log
    row ids or snapshot hash, or the words `expected` / `observed`; anything else is refused. A
    `verified` state must have checked at least one platform evidence id (FLT-1212).
  * **A `disputed` state names its reason, the contradicting evidence and its ticket** — the bug
    the verifier filed first (FLT-1213, FLT-1229). **`unverified` carries a reason.**
  * **Never the runner, and only as oneself.** The reviewer is this session's `FLEET_RUN_ID`; the
    write is refused when `--reviewer` names anyone else, or when it equals the result's `runner`.
  * **Who signed it is said, not implied.** `reviewer_kind` is `fleet-run` when the record is signed
    by the session's `FLEET_RUN_ID`, and `manual` when no run id is set and a person names themself
    with `--reviewer` — so the desk can tell a dispatched verifier from a self-named one. With
    neither, the write is refused. A record from before the field carries none (read as unstated).
  * **What makes a pass count is signed (BUG-1144).** A record is plain JSON in the repository,
    so everything in it is only what the file says. When Fleet dispatches `qa:verify` it
    hands the session a per-run key, `FLEET_QA_REVIEW_KEY` — environment only, never argv, never
    printed, never passed on to a planted run's command — and every record this script writes is
    signed: `provenance` = HMAC(key, record kind · reviewer · bound · sha256 of the canonical JSON
    of the WHOLE record). Flip a signed dispute to `verified` and it no longer matches. A
    `verified` review, an `approved` oracle and a `caught` planted outcome are refused without the
    key. The record's own instant is NOT trusted: after writing a record the session runs
    `digest <path>` and passes the printed digest to the `attest_qa_review` fleet tool, which
    stores it with the server's time only while the run's qa-verify claim is live. The Quality
    desk recomputes the token under the server-side secret AND requires that attestation, so a
    record backdated by a leaked key, or edited after it was attested, counts for nothing. The
    HMAC stays because this script's sampler and `validate` cannot reach the control plane: it is
    how they tell the dispatched verifier's records from hand-written ones offline. `validate` checks
    the field's SHAPE only (`_provenance_shape_ok`) unless the secret is in its environment
    (`FLEET_VERIFY_DISPATCH_SECRET` / `VERIFY_DISPATCH_HMAC_SECRET`), when it recomputes too.
    Disputes, rejections and missed catches need no provenance: they only make things stricter.
    **A record that only lacks `provenance` is legacy, not refused, when it is FROZEN legacy:**
    named with its `record_digest` in the baseline (`knowledge/audits/qa-unsigned.baseline`, one
    `<path> <digest>` per line, at the base AND here), present on the base and untouched since,
    and still hashing to that digest. It predates the rule, append-only forbids signing it after
    the fact, and the reader already gives it no weight — so refusing it would only wedge every
    later change behind a record nobody may touch. "On the base" alone is NOT enough: the base
    moves, so an unsigned record that reached it by a path this gate never ran on (a fleet pin
    moved backwards, an admin merge) would be grandfathered forever. The baseline may only shrink
    (`append-only` refuses a line a change adds or alters), and with no baseline the legacy set is
    empty. Only a frozen record is spared; a malformed or non-matching `provenance` is refused
    wherever it sits, a symlink under the home is refused outright, and with no readable base
    every record is held to the rule (fail closed).
  * **A manual review may only make things stricter.** The re-grader is the independent verifier
    agent (FLT-1213), and a person as the re-grader was refused (FLT-1216): a `manual` review may
    dispute a pass or leave it unverified, but never verify it. The writer refuses it and the
    reader (`fleet_knowledge.quality_reviews`) ignores one that slips through — otherwise a runner
    could unset its run id, name itself anyone, and verify its own pass.

## An oracle record — a scenario version's expected results

    {"schema_version": 1, "record": "oracle", "scenario": "flow", "version": 2,
     "decision": "approved|rejected", "expected_sha256": "<hex>", "reason": "…",
     "reviewer": "…", "at": "<RFC3339>"}

Write-once per `(scenario, version)`. Refused unless that version exists — the scenario file is
at it now, or a result ran it (then the file is read at that result's commit). `expected_sha256`
pins the approval to the scenario's expected-results section (its `## Expected …` /
`## Acceptance criteria` / `## Assertions` sections, else the whole body); the reader treats a
version whose current text hashes differently as not approved (FLT-1214). The sampler also treats
an oracle or settled review already carried by an open PR as decided (ENG-18336), so a nightly
run does not write a second file at the same fixed path and collide with the pending PR.

## A planted-bug record

    {"schema_version": 1, "record": "planted", "scenario": "flow", "mutation": "<patch path>",
     "environment_id": "local", "caught": false, "reviewer": "…", "at": "<RFC3339>",
     "verdicts": [{"id": "flow#1", "verdict": "pass"}]}

`planted-run` does the whole planted check in code: it refuses unless the `local` environment
record says `production: false` and serves a loopback `base_url`, refuses a patch already applied
in this checkout (`git apply --reverse --check` succeeds), creates a throwaway worktree, applies
the patch there, runs the caller's command in it, records the outcome, and removes the worktree
in a `finally`. The verdicts are embedded here, never written as a result file. `caught` is
derived: any fail → caught; every verdict a pass → weak; anything else is refused.

## Subcommands

    sample   [--since-days 7] [--percent 20]       what this run re-grades (JSON; skips
                                                   oracles/reviews already pending in open PRs)
    review   --result PATH (--verdict-file F | --state ID=STATE …)
    oracle   --scenario S --version N (--approve | --reject) --reason TEXT
    mode     --title TITLE                           nightly | planted (exact schedule titles)
    planted-pick                                     the next scenario to plant (JSON)
    planted-run --scenario S [--teardown CMD] -- CMD …
    validate    [--base REF]                         every record under the home (frozen legacy may be unsigned)
    append-only [--base REF]                         no existing record modified or deleted, no baseline line added
    pr-scope    [--base REF]                         the branch touches only the reviews home

Every refusal prints `qa_review: …` to stderr, writes nothing and exits 1. Stdlib only.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable, Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo  # noqa: E402

UTC = timezone.utc

RESULTS_SUBDIR = "knowledge/audits/results"
REVIEWS_SUBDIR = "knowledge/audits/reviews"
#: The frozen legacy set: `<path> <record_digest>` per line, for the unsigned records that predate
#: BUG-1144's provenance rule. Outside the reviews home, which holds JSON records only. It may
#: only shrink; a missing file is an empty set.
UNSIGNED_BASELINE = "knowledge/audits/qa-unsigned.baseline"
#: The trust anchor for that baseline: every `(path, record_digest)` FLEET froze as legacy. A
#: consumer's baseline line counts only if it is here, so neither an admin merge nor a PR that ran
#: under an older pin can freeze a new record by writing its line on the consumer's main — freezing
#: one takes a reviewed fleet change. Records that predate BUG-1144 on the one consumer that had any
#: (2026-10-16: 13 oracle approvals, 2 verified reviews). It is never extended for a record written
#: after BUG-1144: such a record must be signed by a dispatched `qa:verify` run.
FROZEN_UNSIGNED: frozenset[tuple[str, str]] = frozenset(
    {
        (
            "knowledge/audits/reviews/oracles/actions-leave-receipts-v4.json",
            "df3657cd6558313079bf919da686186aa361f0585ca2e8f1597403d0d7e23205",
        ),
        (
            "knowledge/audits/reviews/oracles/actions-leave-receipts-v6.json",
            "45ea65383e401c21f7ce90f80ea5fdbc39dc3fddf8e2fad50afa47ebcbba2208",
        ),
        (
            "knowledge/audits/reviews/oracles/agents-and-meeting-admin-v4.json",
            "681af6f1cc93b54bc8c6193284d3d7d7ecc8821820d80f1f8aeeba40695fda36",
        ),
        (
            "knowledge/audits/reviews/oracles/agents-and-meeting-admin-v5.json",
            "44aaff0dff6d6d915ee4b5259323f401f0378aeda9a7408cb8d899e874a273b0",
        ),
        (
            "knowledge/audits/reviews/oracles/api-key-lifetime-named-and-bounded-v1.json",
            "49b956d55ca003a4b368e88f1d387325357e79330e6e603030b6b001f5fe2905",
        ),
        (
            "knowledge/audits/reviews/oracles/declaration-apply-refuses-concurrent-edit-v1.json",
            "fc94710a29fd38a56633e5dd1a2fbbb0920ba305f32b5b8a6c29500051520c23",
        ),
        (
            "knowledge/audits/reviews/oracles/declaration-rename-default-and-removal-v1.json",
            "5908b1d4159949f0511fcb8b08a613814ccf242fe3e2fda77821880e3e80c405",
        ),
        (
            "knowledge/audits/reviews/oracles/key-narrowing-monotonic-v1.json",
            "766d134f10de6a931cd67165c998685b9a75db01ef02fadd4e90bbbeb82b5161",
        ),
        (
            "knowledge/audits/reviews/oracles/key-profile-binding-holds-v2.json",
            "f9b8134e3a8668abd89b55b75fbd93ec7f2e8d9b0594c4b8a5dbb1946a558564",
        ),
        (
            "knowledge/audits/reviews/oracles/list-paging-contract-holds-v1.json",
            "25364a9d7a0aca921e6857adb0baf01512b4512e36b2cfe676ce26dd714e73c3",
        ),
        (
            "knowledge/audits/reviews/oracles/org-api-key-ui-mint-reveal-revoke-v3.json",
            "6dc1d16abb8d22bd14ec59728f5c21a268c39a8aca14529cb591b890b2b59e6f",
        ),
        (
            "knowledge/audits/reviews/oracles/tenant-spend-narrowing-only-v1.json",
            "0445a4dc5f5208163e5e2eb4f8cfa922bea518879ab91c5cba8946eb15bbd75a",
        ),
        (
            "knowledge/audits/reviews/oracles/workspace-read-narrowing-v6.json",
            "655b4d932f106d8a563e22d5e2bf70bd02318c776dee4ccb2783326250ba54bb",
        ),
        (
            "knowledge/audits/reviews/scenario/2026-10-14-workspace-read-narrowing-221712Z--2026-10-14-222339Z.json",
            "c8d996746bfd83d8e3cf595262931831f362a29db3216896a4d8c94d2085bbb7",
        ),
        (
            "knowledge/audits/reviews/scenario/2026-10-14-workspace-read-narrowing-224202Z--2026-10-14-224826Z.json",
            "d5159e761077f50c114fbfe7791f1df52e7c1eb158555d519788926c218bca48",
        ),
    }
)
ENVIRONMENTS_SUBDIR = "knowledge/environments"
SCENARIOS_SUBDIR = "knowledge/scenarios"
#: One patch per scenario, applied only inside a throwaway worktree by `planted-run`.
PLANTED_PATCHES_SUBDIR = "knowledge/scenarios/planted"
ORACLES = "oracles"
PLANTED = "planted"
SCHEMA_VERSION = 1
DEFAULT_BASE_REF = "origin/main"

REVIEW_STATES = ("verified", "unverified", "disputed")
#: The states that settle a pass; an `unverified` pass is sampled again on a later run.
SETTLED_STATES = ("verified", "disputed")
ORACLE_DECISIONS = ("approved", "rejected")
STRUCTURED_FIELDS = ("expected", "observed")
PLANTED_ENVIRONMENT = "local"
RUNNER_KEYS = ("runner", "run_id")
RUN_ID_ENV = "FLEET_RUN_ID"
#: How a review's `reviewer` was established: the session's `FLEET_RUN_ID`, or a self-named person.
REVIEWER_FLEET_RUN = "fleet-run"
REVIEWER_MANUAL = "manual"
REVIEWER_KINDS = (REVIEWER_FLEET_RUN, REVIEWER_MANUAL)
#: The per-run key a `qa:verify` dispatch is handed, in its environment only (BUG-1144).
QA_REVIEW_KEY_ENV = "FLEET_QA_REVIEW_KEY"
#: Where `validate` may find the server-side secret the key derives from (CI's Actions secret).
QA_REVIEW_SECRET_ENV_VARS = ("FLEET_VERIFY_DISPATCH_SECRET", "VERIFY_DISPATCH_HMAC_SECRET")
PROVENANCE_FIELD = "provenance"
_RUN_KEY_PREFIX = "qa-verify:v1:"
_TOKEN_PREFIX = "qa-record:v2:"
_PROVENANCE_RE = re.compile(r"^[0-9a-f]{64}$")
#: The two schedule titles the corpus's `[fleet.recurring]` gives the verifier, matched exactly.
MODES = {"qa verifier — nightly": "nightly", "qa verifier — planted bug": "planted"}
#: What the planted run's command reads: where the worktree is and where to write its verdicts.
PLANTED_WORKTREE_ENV = "QA_PLANTED_WORKTREE"
PLANTED_VERDICTS_ENV = "QA_PLANTED_VERDICTS"

_KIND_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_TICKET_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*-\d+$|^#\d+$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+=-]*$")
_REVIEW_NAME_RE = re.compile(r"^(?P<stem>.+)--(?P<date>\d{4}-\d{2}-\d{2})-(?P<hms>\d{6})Z\.json$")
_ORACLE_NAME_RE = re.compile(r"^(?P<scenario>[a-z0-9][a-z0-9-]*)-v(?P<version>[1-9]\d*)\.json$")
_PLANTED_NAME_RE = re.compile(r"^(?P<scenario>[a-z0-9][a-z0-9-]*)-(?P<date>\d{4}-\d{2}-\d{2})\.json$")
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
_EXPECTED_H2_RE = re.compile(r"^##\s+[^\n]*\b(?:expected|acceptance criteria|assertions)\b", re.I)


class ReviewError(Exception):
    """A record the writer refuses to put on disk."""


class UnsignedRecordError(ReviewError):
    """A record that would make a pass count carries no `provenance` at all (BUG-1144).

    Its own class so `validate` can tell it apart from every other refusal: a record that was
    already on the base before the rule existed cannot be signed after the fact (append-only
    forbids the edit), and it already counts for nothing — the reader ignores an unsigned pass."""


# ───────────────────────────── small helpers ─────────────────────────────


#: An RFC3339 instant, checked by an explicit pattern BEFORE `datetime.fromisoformat` sees it, so
#: the verdict cannot depend on the interpreter: Python 3.14's `fromisoformat` accepts `T24:00` and
#: rolls it into the next day, 3.12's refuses it (BUG-1118). Hour 00-23, minute and second 00-59.
_RFC3339_RE = re.compile(
    r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])"
    r"T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,9})?"
    r"(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)$"
)


def parse_utc(instant: str) -> datetime:
    """An RFC3339 instant (trailing `Z` accepted) as an aware UTC datetime.

    Raises `ValueError` on anything the explicit pattern refuses (`T24:00:00Z` among them),
    whatever this interpreter's `fromisoformat` would have accepted.
    """
    text = instant.strip()
    if not _RFC3339_RE.match(text):
        raise ValueError(f"not an RFC3339 instant (YYYY-MM-DDTHH:MM:SSZ, hour 00-23): {instant!r}")
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def rfc3339(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReviewError(f"{path} does not exist") from exc
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ReviewError(f"{path} cannot be read: {exc}") from exc


def _inside(path: Path, home: Path) -> bool:
    try:
        path.resolve().relative_to(home.resolve())
        return True
    except ValueError:
        return False


def _write_once(root: Path, path: Path, data: dict[str, Any]) -> Path:
    home = root / REVIEWS_SUBDIR
    if not _inside(path, home):
        raise ReviewError(f"record path {path} escapes the reviews home {home}")
    if path.exists():
        raise ReviewError(f"{path.relative_to(root).as_posix()} already exists — records are append-only, never edited")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)


def runner_of(result: dict[str, Any]) -> str:
    """The run id of the session that ran the check, when the result file names one."""
    for key in RUNNER_KEYS:
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def resolve_reviewer(explicit: str, env: dict[str, str] | None = None) -> str:
    """This session's `FLEET_RUN_ID` — refused when unset, and `--reviewer` may only repeat it."""
    environ = os.environ if env is None else env
    from_env = (environ.get(RUN_ID_ENV) or "").strip()
    if not from_env:
        raise ReviewError(
            f"{RUN_ID_ENV} is unset — a verifier record is signed by the dispatched run that wrote it, "
            "and a session that cannot name itself cannot show it is not the runner"
        )
    given = explicit.strip()
    if given and given != from_env:
        raise ReviewError(
            f"--reviewer {given!r} is not this session's {RUN_ID_ENV} ({from_env!r}) — a session signs only as itself"
        )
    if not _TOKEN_RE.match(from_env):
        raise ReviewError(f"{RUN_ID_ENV} {from_env!r} must be one run-id token")
    return from_env


def mode_of(title: str) -> str:
    """`nightly` or `planted` for one of the two exact schedule titles; anything else is refused."""
    mode = MODES.get(" ".join(title.split()).lower())
    if mode is None:
        raise ReviewError(f"{title!r} is not a QA verifier schedule title (expected one of {sorted(MODES)})")
    return mode


def _evidence_tokens(verdict: dict[str, Any]) -> set[str]:
    evidence = verdict.get("evidence")
    if not isinstance(evidence, dict):
        return set()
    out: set[str] = set()
    for key in ("request_ids", "audit_ids"):
        ids = evidence.get(key)
        if isinstance(ids, list):
            out.update(str(x).strip() for x in ids if isinstance(x, str) and x.strip())
    snap = evidence.get("snapshot")
    if isinstance(snap, str) and snap.strip():
        out.add(snap.strip())
    return out


# ───────────────────────────── scenario text ─────────────────────────────


def resolve_review_signer(explicit: str, env: dict[str, str] | None = None) -> tuple[str, str]:
    """`(reviewer, reviewer_kind)` for a review record.

    With `FLEET_RUN_ID` set, exactly `resolve_reviewer` — the run signs, and `--reviewer` may only
    repeat it. Without one, a person may record a review under their own `--reviewer` name, and the
    record says so (`manual`) rather than passing as a dispatched verifier. With neither, refused.
    """
    environ = os.environ if env is None else env
    if (environ.get(RUN_ID_ENV) or "").strip():
        return resolve_reviewer(explicit, env), REVIEWER_FLEET_RUN
    given = explicit.strip()
    if not given:
        raise ReviewError(
            f"{RUN_ID_ENV} is unset — a verifier record is signed by the dispatched run that wrote it; "
            "a person reviewing by hand names themself with --reviewer, and the record says `manual`"
        )
    if not _TOKEN_RE.match(given):
        raise ReviewError(f"--reviewer {given!r} must be one name token")
    return given, REVIEWER_MANUAL


def scenario_version(text: str) -> int | None:
    """The scenario record's frontmatter `version:` as an integer, or None."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() == "version":
            raw = value.strip().strip("'\"")
            return int(raw) if raw.isdigit() and int(raw) > 0 else None
    return None


def expected_digest(text: str) -> str:
    """sha256 of the scenario's expected-results sections (whole body when it has none).

    Lines are right-stripped and blank runs collapsed, so whitespace churn never unpins an approval;
    a changed expected value always does. Mirrored in `fleet_knowledge.quality_reviews`.
    """
    body = _FRONTMATTER_RE.sub("", text, count=1)
    lines = body.splitlines()
    picked: list[str] = []
    inside = False
    found = False
    for line in lines:
        if line.startswith("## "):
            inside = bool(_EXPECTED_H2_RE.match(line))
            found = found or inside
        if inside:
            picked.append(line)
    chosen = picked if found else lines
    norm = "\n".join(line.rstrip() for line in chosen)
    norm = re.sub(r"\n{2,}", "\n", norm).strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def scenario_text_at(root: Path, scenario: str, version: int) -> str:
    """The scenario file's text at `version`: the current file, else at a result that ran it."""
    rel = f"{SCENARIOS_SUBDIR}/{scenario}.md"
    current = root / rel
    if current.is_file():
        text = current.read_text(encoding="utf-8")
        if scenario_version(text) == version:
            return text
    for _path, result in iter_results(root):
        if result.get("scenario_version") != version or not any(
            isinstance(v, dict) and scenario_of(str(v.get("id") or ""), result) == scenario
            for v in result.get("verdicts") or []
        ):
            continue
        # A result that records `scenario_sha256` names the exact text it walked: only a text with
        # that hash is the version it ran. Its `commit` is the code the run was against and need not
        # contain the scenario at all (a new scenario lands with its first result), so when the text
        # is not there it is looked for in the file's own history, by hash.
        pinned = str(result.get("scenario_sha256") or "")
        commit = str(result.get("commit") or "")
        raw = _git_blob(root, f"{commit}:{rel}") if commit else None
        if raw is not None:
            text = raw.decode("utf-8", errors="replace")
            if scenario_version(text) == version and (not pinned or hashlib.sha256(raw).hexdigest() == pinned):
                return text
        if pinned:
            found = _text_by_digest(root, rel, pinned)
            if found is not None and scenario_version(found) == version:
                return found
    raise ReviewError(
        f"scenario {scenario!r} v{version} does not exist — {rel} is not at that version and no result "
        "ran it at a commit where it was"
    )


def _git_blob(root: Path, spec: str) -> bytes | None:
    """`git show <spec>` as RAW bytes, or None. Never text mode: the writer hashes the file's raw
    bytes (`check_result.scenario_digest`), and a text-mode read normalizes CRLF to LF, so the two
    sides would hash different bytes and a CRLF scenario could never match its result."""
    shown = subprocess.run(["git", "-C", str(root), "show", spec], capture_output=True, check=False)
    return shown.stdout if shown.returncode == 0 else None


def _text_by_digest(root: Path, rel: str, digest: str) -> str | None:
    """The revision of `rel` in this checkout's history whose raw bytes hash to `digest`, or None."""
    log = _git(root, "log", "--format=%H", "--all", "--", rel)
    if log.returncode != 0:
        return None
    for commit in log.stdout.split():
        raw = _git_blob(root, f"{commit}:{rel}")
        if raw is not None and hashlib.sha256(raw).hexdigest() == digest:
            return raw.decode("utf-8", errors="replace")
    return None


# ───────────────────────────── the result home ─────────────────────────────


def load_result(root: Path, result_file: str) -> tuple[str, dict[str, Any]]:
    path = Path(result_file).resolve() if Path(result_file).is_absolute() else (root / result_file).resolve()
    if not _inside(path, root / RESULTS_SUBDIR):
        raise ReviewError(f"{result_file} is not a check-result file under {RESULTS_SUBDIR}/")
    data = _load_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("verdicts"), list):
        raise ReviewError(f"{result_file} is not a check-result file (no verdicts list)")
    if not isinstance(data.get("kind"), str) or not _KIND_RE.match(data["kind"]):
        raise ReviewError(f"{result_file} carries no valid kind")
    return _rel(root, path), data


def iter_results(root: Path) -> list[tuple[str, dict[str, Any]]]:
    home = root / RESULTS_SUBDIR
    if not home.is_dir():
        return []
    out: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(home.rglob("*.json")):
        if path.is_symlink() or not _inside(path, home):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(data, dict) and isinstance(data.get("verdicts"), list):
            out.append((_rel(root, path), data))
    return out


def scenario_of(verdict_id: str, result: dict[str, Any]) -> str:
    if "#" in verdict_id:
        return verdict_id.split("#", 1)[0]
    return str(result.get("target") or "")


# ───────────────────────────── reviews ─────────────────────────────


def review_path(root: Path, result_rel: str, kind: str, at: datetime) -> Path:
    utc = at.astimezone(UTC)
    stamp = f"{utc.strftime('%Y-%m-%d')}-{utc.strftime('%H%M%S')}Z"
    return root / REVIEWS_SUBDIR / kind / f"{Path(result_rel).stem}--{stamp}.json"


def review_run_key(secret: str, run_id: str) -> str:
    """HMAC(secret, run id): the key Fleet hands a `qa:verify` dispatch. Mirrors
    `fleet_knowledge.quality_reviews.review_run_key`."""
    return hmac.new(secret.encode("utf-8"), f"{_RUN_KEY_PREFIX}{run_id}".encode(), hashlib.sha256).hexdigest()


def record_digest(data: dict[str, Any]) -> str:
    """sha256 of the canonical JSON of the record minus `provenance`. Mirrors
    `fleet_knowledge.quality_reviews.record_digest`."""
    body = {k: v for k, v in data.items() if k != PROVENANCE_FIELD}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def attestation_digest(root: Path, record: str) -> str:
    """The digest `qa:verify` attests for a record it wrote (`attest_qa_review`, BUG-1144).

    `record_digest` of the file as it stands: the desk counts the record only if this exact digest
    was attested by its reviewer run while that run was live, so an edit after attestation does not
    count. A path outside the reviews home, or a file that is not a JSON object, is refused.
    """
    path = (root / record).resolve()
    home = (root / REVIEWS_SUBDIR).resolve()
    if not path.is_relative_to(home) or not path.is_file():
        raise ReviewError(f"{record} is not a record under {REVIEWS_SUBDIR}")
    data = _load_json(path)
    if not isinstance(data, dict):
        raise ReviewError(f"{record} is not a JSON object")
    return record_digest(data)


def record_token(run_key: str, data: dict[str, Any], *, bound: str = "") -> str:
    """A record's `provenance`. Mirrors `fleet_knowledge.quality_reviews.record_token`."""
    payload = f"{_TOKEN_PREFIX}{data.get('record')}:{data.get('reviewer')}:{bound}:{record_digest(data)}"
    return hmac.new(run_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _bound_version(version: object) -> str:
    return "" if version is None or isinstance(version, bool) else str(version)


def _provenance_shape_ok(data: dict[str, Any]) -> bool:
    """SHAPE ONLY: the record carries a 64-hex `provenance`. What a repository without the secret
    can check — never what the desk accepts, which recomputes it under an explicit Authority."""
    token = data.get(PROVENANCE_FIELD)
    return isinstance(token, str) and bool(_PROVENANCE_RE.match(token))


def _verifiable(data: dict[str, Any], *, bound: str = "", env: dict[str, str] | None = None) -> bool:
    """Whether THIS process can prove the record was signed by its run's key: with the server-side
    secret in the environment (CI), or — for a record this very session signed — with its own key.
    Anything else is unproven here, and treated as such (the sampler re-takes it)."""
    environ = os.environ if env is None else env
    token, reviewer = data.get(PROVENANCE_FIELD), str(data.get("reviewer") or "")
    if not _provenance_shape_ok(data) or not reviewer:
        return False
    secret = _secret_from_env(dict(environ))
    if secret:
        return hmac.compare_digest(record_token(review_run_key(secret, reviewer), data, bound=bound), str(token))
    own_key = (environ.get(QA_REVIEW_KEY_ENV) or "").strip()
    if own_key and reviewer == (environ.get(RUN_ID_ENV) or "").strip():
        return hmac.compare_digest(record_token(own_key, data, bound=bound), str(token))
    return False


def _sign(data: dict[str, Any], review_key: str, *, needed: bool, what: str, bound: str = "") -> dict[str, Any]:
    """`data` with its `provenance`, or a refusal when it must be signed and this session holds no key."""
    if review_key:
        return {**data, PROVENANCE_FIELD: record_token(review_key, data, bound=bound)}
    if needed:
        raise ReviewError(
            f"{what} must be signed with the per-run key Fleet hands a dispatched qa:verify "
            f"session in ${QA_REVIEW_KEY_ENV}, and this session has none. Without it you may dispute, "
            "reject or record a missed catch — never make a pass count (BUG-1144)"
        )
    return data


def _secret_from_env(env: dict[str, str] | None = None) -> str:
    environ = os.environ if env is None else env
    return next((v.strip() for v in (environ.get(n, "") for n in QA_REVIEW_SECRET_ENV_VARS) if v.strip()), "")


def build_review(
    *,
    result_rel: str,
    result: dict[str, Any],
    reviewer: str,
    at: datetime,
    entries: list[dict[str, Any]],
    reviewer_kind: str | None = None,
) -> dict[str, Any]:
    if reviewer_kind is not None and reviewer_kind not in REVIEWER_KINDS:
        raise ReviewError(f"reviewer_kind {reviewer_kind!r} must be one of {REVIEWER_KINDS}")
    runner = runner_of(result)
    if not runner:
        raise ReviewError(
            f"{result_rel} names no runner — without one nobody can show the reviewer did not run it, "
            "so a review of it would never count"
        )
    if runner == reviewer:
        raise ReviewError(
            f"reviewer {reviewer!r} ran this check ({result_rel}) — the party that ran a check never certifies its pass"
        )
    if reviewer_kind == REVIEWER_MANUAL and any(
        isinstance(raw, dict) and str(raw.get("state") or "").strip() == "verified" for raw in entries
    ):
        raise ReviewError(
            "a manual review may dispute a pass or leave it unverified, never verify it — the "
            f"re-grader is the verifier agent, signed by its {RUN_ID_ENV} (FLT-1213, FLT-1216)"
        )
    by_id: dict[str, dict[str, Any]] = {}
    for item in result.get("verdicts") or []:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            by_id[item["id"]] = item
    if not entries:
        raise ReviewError("a review names at least one verdict")
    clean: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in entries:
        if not isinstance(raw, dict):
            raise ReviewError(f"each reviewed verdict must be an object, got {raw!r}")
        vid = str(raw.get("id") or "").strip()
        if not vid:
            raise ReviewError("every reviewed verdict needs its id")
        if vid in seen:
            raise ReviewError(f"verdict {vid!r} is reviewed twice in one record")
        seen.add(vid)
        verdict = by_id.get(vid)
        if verdict is None:
            raise ReviewError(f"{result_rel} has no verdict {vid!r}")
        if verdict.get("verdict") != "pass":
            raise ReviewError(
                f"{vid!r} is a {verdict.get('verdict')!r}, not a pass — the verifier re-grades passes only"
            )
        state = str(raw.get("state") or "").strip()
        if state not in REVIEW_STATES:
            raise ReviewError(f"state for {vid!r} is {state!r}; must be one of {REVIEW_STATES}")
        reason = str(raw.get("reason") or "").strip()
        checked_raw = raw.get("evidence_checked") or []
        if not isinstance(checked_raw, list):
            raise ReviewError(f"evidence_checked for {vid!r} must be a list")
        own = _evidence_tokens(verdict)
        checked: list[str] = []
        for token in checked_raw:
            text = str(token).strip()
            if text in STRUCTURED_FIELDS:
                if not verdict.get(text):
                    raise ReviewError(f"{vid!r} records no `{text}` to have checked")
            elif text not in own:
                raise ReviewError(
                    f"evidence_checked for {vid!r} names {text!r}, which is not this verdict's evidence — "
                    "the verifier grades from the recorded request/audit ids, snapshot, expected and observed only"
                )
            if text not in checked:
                checked.append(text)
        entry: dict[str, Any] = {"id": vid, "state": state}
        if state == "verified":
            if not any(t in own for t in checked):
                raise ReviewError(
                    f"{vid!r} cannot be verified without checking at least one platform evidence id "
                    "(request id, audit-log row id or snapshot)"
                )
        elif not reason:
            raise ReviewError(f"a {state} verdict ({vid!r}) carries a reason")
        if state == "disputed":
            ticket = str(raw.get("ticket") or "").strip()
            if not _TICKET_RE.match(ticket):
                raise ReviewError(
                    f"a disputed verdict ({vid!r}) names the ticket filed for it — file the bug first, then record"
                )
            if not checked:
                raise ReviewError(f"a disputed verdict ({vid!r}) names the evidence that contradicts the pass")
            entry["ticket"] = ticket
        if reason:
            entry["reason"] = reason
        entry["evidence_checked"] = checked
        clean.append(entry)
    out: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record": "review",
        "result_file": result_rel,
        "reviewer": reviewer,
    }
    if reviewer_kind is not None:
        out["reviewer_kind"] = reviewer_kind
    out.update({"reviewed_at": rfc3339(at), "verdicts": clean})
    return out


def write_review(
    *,
    root: Path,
    result_file: str,
    reviewer: str,
    at: datetime,
    entries: list[dict[str, Any]],
    reviewer_kind: str = REVIEWER_FLEET_RUN,
    review_key: str = "",
) -> Path:
    """Validate and write one review. `review_key` is the dispatch's `FLEET_QA_REVIEW_KEY`; with it
    (and only on the fleet-run path) the record is signed with its `provenance`."""
    result_rel, result = load_result(root, result_file)
    data = build_review(
        result_rel=result_rel,
        result=result,
        reviewer=reviewer,
        at=at,
        entries=entries,
        reviewer_kind=reviewer_kind,
    )
    data = _sign(
        data,
        review_key if reviewer_kind == REVIEWER_FLEET_RUN else "",
        needed=any(v["state"] == "verified" for v in data["verdicts"]),
        what="a verified review",
        bound=_bound_version(result.get("scenario_version")),
    )
    return _write_once(root, review_path(root, result_rel, str(result["kind"]), at), data)


# ───────────────────────────── oracles ─────────────────────────────


def oracle_path(root: Path, scenario: str, version: int) -> Path:
    return root / REVIEWS_SUBDIR / ORACLES / f"{scenario}-v{version}.json"


def build_oracle(
    *, scenario: str, version: int, decision: str, reason: str, reviewer: str, at: datetime, expected_sha256: str
) -> dict[str, Any]:
    scenario = scenario.strip()
    if not _SLUG_RE.match(scenario):
        raise ReviewError(f"scenario {scenario!r} must be a scenario slug")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ReviewError("version must be a positive integer (the scenario's `version:`)")
    if decision not in ORACLE_DECISIONS:
        raise ReviewError(f"decision {decision!r} must be one of {ORACLE_DECISIONS}")
    if not reason.strip():
        raise ReviewError("an oracle decision carries its reason")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ReviewError("expected_sha256 must pin the scenario's expected results (64 hex digits)")
    return {
        "schema_version": SCHEMA_VERSION,
        "record": "oracle",
        "scenario": scenario,
        "version": version,
        "decision": decision,
        "expected_sha256": expected_sha256,
        "reason": reason.strip(),
        "reviewer": reviewer,
        "at": rfc3339(at),
    }


def write_oracle(
    *,
    root: Path,
    scenario: str,
    version: int,
    decision: str,
    reason: str,
    reviewer: str,
    at: datetime,
    review_key: str = "",
) -> Path:
    for _rel_path, result in iter_results(root):
        if (
            result.get("scenario_version") == version
            and runner_of(result) == reviewer
            and any(
                isinstance(v, dict) and scenario_of(str(v.get("id") or ""), result) == scenario
                for v in result.get("verdicts") or []
            )
        ):
            raise ReviewError(
                f"reviewer {reviewer!r} ran scenario {scenario!r} v{version} — it cannot approve its own oracle"
            )
    digest = expected_digest(scenario_text_at(root, scenario, version))
    data = build_oracle(
        scenario=scenario,
        version=version,
        decision=decision,
        reason=reason,
        reviewer=reviewer,
        at=at,
        expected_sha256=digest,
    )
    data = _sign(data, review_key, needed=decision == "approved", what="an oracle approval")
    return _write_once(root, oracle_path(root, data["scenario"], version), data)


def _iter_oracle_records(root: Path) -> Iterator[dict[str, Any]]:
    """Every JSON object under the oracles home, in path order (a malformed file is skipped)."""
    home = root / REVIEWS_SUBDIR / ORACLES
    if not home.is_dir():
        return
    for path in sorted(home.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(data, dict):
            yield data


def _oracle_decision_of(data: dict[str, Any]) -> tuple[tuple[str, int], str] | None:
    """One oracle record's `(scenario, version) → decision`, or None when it decides nothing."""
    scenario, version, decision = data.get("scenario"), data.get("version"), data.get("decision")
    if not (isinstance(scenario, str) and isinstance(version, int) and decision in ORACLE_DECISIONS):
        return None
    if decision == "approved" and not _verifiable(data):
        return None  # an approval this process cannot prove decides nothing (BUG-1144)
    return (scenario, version), str(decision)


def _oracle_claim_of(data: dict[str, Any]) -> tuple[tuple[str, int], str] | None:
    """One oracle record's `(scenario, version) → decision`, or None when it is not an oracle.

    The OCCUPANCY view, not the counting one. A record at `oracles/<scenario>-v<N>.json` takes
    that fixed path whether or not this process can prove its signature, and `write_oracle`
    refuses a second record there (`_write_once`) — so a version a record claims can never be
    decided afresh. The sampler offers only the versions this view does NOT claim (ENG-18837);
    `_oracle_decision_of` stays the counting view an unsigned approval fails (BUG-1144).
    """
    scenario, version, decision = data.get("scenario"), data.get("version"), data.get("decision")
    if not (isinstance(scenario, str) and isinstance(version, int) and decision in ORACLE_DECISIONS):
        return None
    return (scenario, version), str(decision)


def _oracles_by(
    root: Path, parse: Callable[[dict[str, Any]], tuple[tuple[str, int], str] | None]
) -> dict[tuple[str, int], str]:
    """`{key: decision}` for every record under the oracles home that `parse` accepts."""
    out: dict[tuple[str, int], str] = {}
    for data in _iter_oracle_records(root):
        parsed = parse(data)
        if parsed is not None:
            out[parsed[0]] = parsed[1]
    return out


def oracle_decisions(root: Path) -> dict[tuple[str, int], str]:
    """The COUNTING view: `(scenario, version) → decision` for records this process can prove."""
    return _oracles_by(root, _oracle_decision_of)


def oracle_claims(root: Path) -> dict[tuple[str, int], str]:
    """The OCCUPANCY view: every oracle record on disk, counted or not (ENG-18837)."""
    return _oracles_by(root, _oracle_claim_of)


# ───────────────────────────── planted bugs ─────────────────────────────


def planted_path(root: Path, scenario: str, at: datetime) -> Path:
    return root / REVIEWS_SUBDIR / PLANTED / f"{scenario}-{at.astimezone(UTC).strftime('%Y-%m-%d')}.json"


def _is_loopback(base_url: str) -> bool:
    host = (urlparse(base_url).hostname or "").strip("[]").lower()
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def check_planted_environment(root: Path, environment_id: str) -> None:
    """Only the committed `local` record, saying `production: false`, serving a loopback base URL."""
    if environment_id != PLANTED_ENVIRONMENT:
        raise ReviewError(
            f"a planted bug runs on the {PLANTED_ENVIRONMENT!r} environment only, never {environment_id!r}"
        )
    record = _load_json(root / ENVIRONMENTS_SUBDIR / f"{environment_id}.json")
    if not isinstance(record, dict):
        raise ReviewError(f"environment record {environment_id!r} is not a JSON object")
    if record.get("production") is not False:
        raise ReviewError(
            f"environment {environment_id!r} does not state `production: false` — "
            "a planted bug never runs where that is unproven"
        )
    base_url = record.get("base_url")
    if not isinstance(base_url, str) or not _is_loopback(base_url):
        raise ReviewError(
            f"environment {environment_id!r} serves {base_url!r}, not a loopback address — "
            "a planted bug only ever runs against this machine"
        )


def check_patch_not_applied(root: Path, patch: Path) -> None:
    """Refuse a patch this checkout already carries: reversing it would succeed here."""
    reverse = _git(root, "apply", "--reverse", "--check", str(patch))
    if reverse.returncode == 0:
        raise ReviewError(
            f"{_rel(root, patch)} is already applied in {root} — the planted bug is in a working checkout; "
            "revert it before anything else"
        )


def caught_from(scenario: str, verdicts: list[dict[str, Any]]) -> bool:
    mine = [v for v in verdicts if str(v.get("id") or "").split("#", 1)[0] == scenario]
    if not mine:
        raise ReviewError(f"the planted run recorded no verdict for scenario {scenario!r}")
    words = {str(v.get("verdict") or "") for v in mine}
    if "fail" in words:
        return True
    if words == {"pass"}:
        return False
    raise ReviewError(
        f"the planted run of {scenario!r} is inconclusive ({sorted(words)}) — "
        "it neither went red nor ran green; record nothing"
    )


def build_planted(
    *,
    scenario: str,
    mutation: str,
    environment_id: str,
    verdicts: list[dict[str, Any]],
    reviewer: str,
    at: datetime,
) -> dict[str, Any]:
    if not _SLUG_RE.match(scenario):
        raise ReviewError(f"scenario {scenario!r} must be a scenario slug")
    if not mutation.strip():
        raise ReviewError("mutation names the planted change (its patch path)")
    clean: list[dict[str, Any]] = []
    for item in verdicts:
        if not isinstance(item, dict):
            raise ReviewError(f"planted verdict {item!r} must be an object")
        vid = str(item.get("id") or "").strip()
        word = str(item.get("verdict") or "").strip()
        if not vid or word not in ("pass", "fail", "blocked", "not-applicable"):
            raise ReviewError(f"planted verdict {item!r} must be {{id, verdict}} with a check-result verdict word")
        clean.append({"id": vid, "verdict": word})
    return {
        "schema_version": SCHEMA_VERSION,
        "record": "planted",
        "scenario": scenario,
        "mutation": mutation.strip(),
        "environment_id": environment_id,
        "caught": caught_from(scenario, clean),
        "reviewer": reviewer,
        "at": rfc3339(at),
        "verdicts": clean,
    }


def _patch_for(root: Path, scenario: str) -> Path:
    patch = root / PLANTED_PATCHES_SUBDIR / f"{scenario}.patch"
    if not _SLUG_RE.match(scenario) or not patch.is_file():
        raise ReviewError(f"scenario {scenario!r} declares no planted bug ({PLANTED_PATCHES_SUBDIR}/{scenario}.patch)")
    return patch


def planted_run(
    *,
    root: Path,
    scenario: str,
    command: list[str],
    teardown: list[str],
    reviewer: str,
    at: datetime,
    environment_id: str = PLANTED_ENVIRONMENT,
    review_key: str = "",
) -> Path:
    """The whole planted check: guards, a throwaway worktree, the run, the record, the cleanup.

    `command` runs with the worktree as its working directory and with `QA_PLANTED_WORKTREE` and
    `QA_PLANTED_VERDICTS` (a JSON file it must write: a list of `{id, verdict}`) in its environment.
    `teardown`, when given, runs in the same worktree afterwards whatever happened. The worktree is
    removed in a `finally` — on success, on a refusal and on a crash alike.
    """
    if not command:
        raise ReviewError("planted-run needs the command that brings the stack up and runs the scenario, after --")
    check_planted_environment(root, environment_id)
    patch = _patch_for(root, scenario)
    check_patch_not_applied(root, patch)
    scratch = Path(tempfile.mkdtemp(prefix="qa-planted-"))
    worktree = scratch / "tree"
    verdicts_file = scratch / "verdicts.json"
    added = False
    try:
        made = _git(root, "worktree", "add", "--detach", str(worktree), "HEAD")
        if made.returncode != 0:
            raise ReviewError(f"cannot create the throwaway worktree: {made.stderr.strip()}")
        added = True
        applied = _git(worktree, "apply", str(patch.resolve()))
        if applied.returncode != 0:
            raise ReviewError(f"{_rel(root, patch)} does not apply to HEAD: {applied.stderr.strip()}")
        env = dict(os.environ)
        # THE REVIEW KEY IS THIS SESSION'S, NOT THE SCENARIO RUNNER'S (BUG-1144): a bearer value
        # never handed to the command that brings a stack up.
        env.pop(QA_REVIEW_KEY_ENV, None)
        env[PLANTED_WORKTREE_ENV] = str(worktree)
        env[PLANTED_VERDICTS_ENV] = str(verdicts_file)
        try:
            subprocess.run(command, cwd=worktree, env=env, check=False)
        finally:
            if teardown:
                subprocess.run(teardown, cwd=worktree, env=env, check=False)
        loaded = _load_json(verdicts_file)
        if not isinstance(loaded, list):
            raise ReviewError(f"the planted run wrote no verdict list to ${PLANTED_VERDICTS_ENV}")
        data = build_planted(
            scenario=scenario,
            mutation=_rel(root, patch),
            environment_id=environment_id,
            verdicts=loaded,
            reviewer=reviewer,
            at=at,
        )
        data = _sign(data, review_key, needed=bool(data["caught"]), what="a caught planted outcome")
        return _write_once(root, planted_path(root, scenario, at), data)
    finally:
        if added:
            _git(root, "worktree", "remove", "--force", str(worktree))
        shutil.rmtree(scratch, ignore_errors=True)
        _git(root, "worktree", "prune")


def planted_history(root: Path) -> dict[str, str]:
    home = root / REVIEWS_SUBDIR / PLANTED
    out: dict[str, str] = {}
    if not home.is_dir():
        return out
    for path in sorted(home.glob("*.json")):
        match = _PLANTED_NAME_RE.match(path.name)
        if match and match["date"] > out.get(match["scenario"], ""):
            out[match["scenario"]] = match["date"]
    return out


def planted_pick(root: Path) -> dict[str, str] | None:
    """The scenario whose planted bug ran least recently (never first, then oldest; ties by name)."""
    home = root / PLANTED_PATCHES_SUBDIR
    if not home.is_dir():
        return None
    history = planted_history(root)
    candidates = sorted(p for p in home.glob("*.patch") if p.is_file() and _SLUG_RE.match(p.stem))
    if not candidates:
        return None
    best = min(candidates, key=lambda p: (history.get(p.stem, ""), p.stem))
    return {"scenario": best.stem, "mutation": _rel(root, best), "last_planted": history.get(best.stem, "")}


# ───────────────────────────── the sample ─────────────────────────────


def _load_result_quietly(root: Path, result_file: str) -> dict[str, Any]:
    try:
        return load_result(root, result_file)[1]
    except ReviewError:
        return {}


def _settled_keys_of(data: dict[str, Any], root: Path) -> set[tuple[str, str]]:
    """Every `(result_file, verdict id)` one review record SETTLES (verified or disputed).

    An `unverified` review settles nothing. A `verified` settles only when its signature is
    PROVEN here (or is not a manual review pretending to verify — FLT-1216, BUG-1144).
    """
    out: set[tuple[str, str]] = set()
    if data.get("record") != "review":
        return out
    manual = data.get("reviewer_kind") == REVIEWER_MANUAL
    result = _load_result_quietly(root, str(data.get("result_file") or ""))
    signed = _verifiable(data, bound=_bound_version(result.get("scenario_version")))
    for item in data.get("verdicts") or []:
        if not isinstance(item, dict) or item.get("state") not in SETTLED_STATES:
            continue
        if item.get("state") == "verified" and (manual or not signed):
            continue
        out.add((str(data.get("result_file") or ""), str(item.get("id") or "")))
    return out


def reviewed_keys(root: Path) -> set[tuple[str, str]]:
    """Every `(result_file, verdict id)` a review SETTLED (verified or disputed).

    An `unverified` review settles nothing — the evidence was unreachable — so that pass is drawn
    again on a later run.
    """
    home = root / REVIEWS_SUBDIR
    out: set[tuple[str, str]] = set()
    if not home.is_dir():
        return out
    for path in sorted(home.rglob("*.json")):
        if path.parent.name in (ORACLES, PLANTED):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(data, dict):
            out |= _settled_keys_of(data, root)
    return out


def _gh_json(root: Path, *args: str, timeout: int = 60) -> Any:
    """Run `gh …` under `root` and parse its JSON stdout. None on any failure (fail-open)."""
    try:
        raw = subprocess.check_output(
            ["gh", *args],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
            env=os.environ.copy(),
            timeout=timeout,
        )
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired, FileNotFoundError):
        return None
    try:
        return json.loads(raw or "null")
    except json.JSONDecodeError:
        return None


def _blob_at(root: Path, sha: str, path: str) -> str | None:
    """File content at `sha:path` — local git first, then the PR host. None on failure."""
    shown = _git(root, "show", f"{sha}:{path}")
    if shown.returncode == 0 and shown.stdout:
        return shown.stdout
    encoded = quote(path, safe="/")
    data = _gh_json(root, "api", f"repos/{{owner}}/{{repo}}/contents/{encoded}?ref={sha}", timeout=30)
    if not isinstance(data, dict) or data.get("encoding") != "base64":
        return None
    content = data.get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    try:
        return base64.b64decode(content).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def fetch_open_pr_review_blobs(root: Path) -> list[tuple[str, str]]:
    """`(rel_path, json_text)` for every added/changed reviews-home file on open PRs.

    Fail-open: missing `gh`, no remote, auth failure, timeout → `[]`. The sampler treats an
    empty overlay as "no pending reviews", which is the pre-ENG-18336 behaviour and the right
    answer offline.
    """
    rows = _gh_json(
        root,
        "pr",
        "list",
        "--state",
        "open",
        "--limit",
        "200",
        "--json",
        "number,headRefOid,files",
    )
    if not isinstance(rows, list):
        return []
    prefix = f"{REVIEWS_SUBDIR}/"
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        sha = str(row.get("headRefOid") or "").strip()
        files = row.get("files") or []
        if not sha or not isinstance(files, list):
            continue
        for entry in files:
            if not isinstance(entry, dict):
                continue
            path = str(entry.get("path") or "").strip()
            change = str(entry.get("changeType") or "").upper()
            if not path.startswith(prefix) or not path.endswith(".json"):
                continue
            if change in ("DELETED", "REMOVED"):
                continue
            key = f"{sha}:{path}"
            if key in seen:
                continue
            seen.add(key)
            text = _blob_at(root, sha, path)
            if text is not None:
                out.append((path, text))
    return out


def open_pr_review_overlay(
    root: Path,
    *,
    blobs: Iterable[tuple[str, str]] | None = None,
) -> tuple[dict[tuple[str, int], str], dict[tuple[str, int], str], set[tuple[str, str]]]:
    """What open PRs that touch the reviews home already carry.

    Returns `(decisions, claims, reviews)`: the oracle decisions an open PR carries that this
    process can PROVE (the counting view), every oracle version an open PR's record CLAIMS
    (the occupancy view) — an unsigned approval opens a fixed path just as firmly as a signed one,
    so the sampler must not offer the version again (ENG-18837) — and the settled
    `(result_file, verdict id)` keys. `blobs` is the test seam: pass `(rel_path, json_text)` pairs
    and the network is never touched. `None` (production) fetches from open PRs via `gh` and
    degrades to empty on failure. Local checkout records still win when both name the same key —
    the overlay only fills gaps.
    """
    decisions: dict[tuple[str, int], str] = {}
    claims: dict[tuple[str, int], str] = {}
    reviews: set[tuple[str, str]] = set()
    items = list(blobs) if blobs is not None else fetch_open_pr_review_blobs(root)
    prefix = f"{REVIEWS_SUBDIR}/"
    for rel, text in items:
        path = str(rel).replace("\\", "/").lstrip("./")
        if not path.startswith(prefix) or not path.endswith(".json"):
            continue
        try:
            data = json.loads(text)
        except (TypeError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        parts = path[len(prefix) :].split("/")
        if not parts:
            continue
        if parts[0] == ORACLES:
            counted = _oracle_decision_of(data)
            if counted is not None:
                decisions[counted[0]] = counted[1]
            claimed = _oracle_claim_of(data)
            if claimed is not None:
                claims[claimed[0]] = claimed[1]
        elif parts[0] != PLANTED:
            reviews |= _settled_keys_of(data, root)
    return decisions, claims, reviews


def _sampled(result_file: str, vid: str, percent: int) -> bool:
    digest = hashlib.sha256(f"{result_file}|{vid}".encode()).hexdigest()
    return int(digest[:8], 16) % 100 < percent


def select_sample(
    root: Path,
    *,
    now: datetime,
    since_days: int,
    percent: int,
    open_pr_blobs: Iterable[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """What one verifier run re-grades: every unsettled pass after a fail, every unsettled pass on a
    scenario version whose oracle has no decision yet, a deterministic share of the other recent
    unsettled passes, and every scenario version whose oracle path no record claims. A pass in a
    result naming no runner can never be reviewed and is counted under `unreviewable`.

    A pending-oracle pass is always taken (`why: oracle-pending`), whatever its age and the draw: it
    cannot count until the verifier decides the oracle (FLT-1214), so leaving it to a 20% draw left
    a new scenario's first passes waiting on luck while the oracle beside them was reviewed.

    Open PRs that already carry a review or oracle under the reviews home are treated as decided
    (ENG-18336): re-grading them would write a second record at the same fixed path and collide
    with the pending PR. `open_pr_blobs` injects those records in tests; production fetches them.

    A version is offered for a fresh oracle decision only when its fixed path is FREE — no record
    under `oracles/` and none an open PR will write there — because `write_oracle` refuses a second
    record at that path. An unsigned record (a frozen pre-BUG-1144 approval, or one an open PR
    carries before its review) therefore still suppresses the version, even though it decides
    nothing: the sampler must not offer a version it cannot write (ENG-18837). Provenance gates the
    `oracle-pending` flag (which follows the counting view, BUG-1144), never the path.
    """
    if not 0 <= percent <= 100:
        raise ReviewError("--percent must be between 0 and 100")
    since = now - timedelta(days=since_days)
    rows: list[dict[str, Any]] = []
    pending: dict[tuple[str, int], list[str]] = {}
    decided = dict(oracle_decisions(root))  # counting view: gates oracle-pending on a pass
    occupied = dict(oracle_claims(root))  # occupancy view: gates the oracles offered below
    pr_oracles, pr_claims, pr_reviews = open_pr_review_overlay(root, blobs=open_pr_blobs)
    for key, decision in pr_oracles.items():
        decided.setdefault(key, decision)
    for key, decision in pr_claims.items():
        occupied.setdefault(key, decision)
    for rel, result in iter_results(root):
        version = result.get("scenario_version")
        has_runner = bool(runner_of(result))
        walked = version if isinstance(version, int) and not isinstance(version, bool) else None
        for item in result.get("verdicts") or []:
            if not isinstance(item, dict):
                continue
            vid = str(item.get("id") or "")
            oracle_key = None if walked is None else (scenario_of(vid, result), walked)
            oracle_pending = oracle_key is not None and oracle_key not in decided
            rows.append(
                {
                    "result_file": rel,
                    "id": vid,
                    "verdict": str(item.get("verdict") or ""),
                    "key": str(item.get("promise") or vid),
                    "ran_at": str(result.get("ran_at") or ""),
                    "finished": result.get("finished") is True,
                    "runner": has_runner,
                    "oracle_pending": oracle_pending,
                }
            )
            if oracle_key is not None and oracle_key not in occupied:
                files = pending.setdefault(oracle_key, [])
                if rel not in files:
                    files.append(rel)
    rows.sort(key=lambda r: (r["ran_at"], r["result_file"], r["id"]))
    done = reviewed_keys(root) | pr_reviews
    last: dict[str, str] = {}
    passes: list[dict[str, str]] = []
    unreviewable = 0
    for row in rows:
        previous = last.get(row["key"], "")
        if row["finished"] and row["verdict"] in ("pass", "fail"):
            last[row["key"]] = row["verdict"]
        if row["verdict"] != "pass" or not row["finished"] or (row["result_file"], row["id"]) in done:
            continue
        if not row["runner"]:
            unreviewable += 1
            continue
        if previous == "fail":
            why = "after-fail"
        elif row["oracle_pending"]:
            why = "oracle-pending"
        else:
            try:
                recent = parse_utc(row["ran_at"]) >= since
            except ValueError:
                recent = False
            if not (recent and _sampled(row["result_file"], row["id"], percent)):
                continue
            why = "sampled"
        passes.append({"result_file": row["result_file"], "id": row["id"], "why": why})
    oracles = [{"scenario": s, "version": v, "result_files": files} for (s, v), files in sorted(pending.items())]
    return {"passes": passes, "oracles": oracles, "unreviewable": unreviewable}


# ───────────────────────────── validate + the diff gates ─────────────────────────────


def unchanged_base_records(root: Path, base: str) -> frozenset[str]:
    """The records under the reviews home present at `base` and untouched since — the legacy set.

    Membership needs BOTH: listed in `base`'s tree, and not among this change's diff entries, so
    an edited record (which `append-only` refuses anyway) is never grandfathered."""
    listed = _git(root, "ls-tree", "-r", "-z", "--name-only", base, "--", REVIEWS_SUBDIR + "/")
    if listed.returncode != 0:
        raise ReviewError(f"git ls-tree {base} failed: {listed.stderr.strip()}")
    touched = {path for _status, path in _changes(root, base)}
    return frozenset(p for p in listed.stdout.split("\0") if p and p not in touched)


def parse_unsigned_baseline(text: str) -> tuple[dict[str, str], list[str]]:
    """`{path: record_digest}` from a baseline's text, and a `<why>` line per malformed line.

    A line is `<path> <64-hex digest>`; blank lines and `#` comments are skipped. The path must be
    a plain relative path under the reviews home — no `.`/`..` segment — or it is malformed."""
    entries: dict[str, str] = {}
    problems: list[str] = []
    prefix = REVIEWS_SUBDIR + "/"
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        path = parts[0] if parts else ""
        segments = path.split("/")
        if (
            len(parts) != 2
            or not path.startswith(prefix)
            or any(seg in ("", ".", "..") for seg in segments)
            or not _PROVENANCE_RE.match(parts[1])
        ):
            problems.append(f"{UNSIGNED_BASELINE}:{number}: not `<path under {prefix}> <64-hex record_digest>`")
            continue
        if path in entries:
            problems.append(f"{UNSIGNED_BASELINE}:{number}: {path} is listed twice")
            continue
        entries[path] = parts[1]
    return entries, problems


def _baseline_at(root: Path, base: str) -> str:
    """The baseline's text at `base` — empty when the base has none."""
    raw = _git_blob(root, f"{base}:{UNSIGNED_BASELINE}")
    return raw.decode("utf-8", errors="replace") if raw is not None else ""


def _baseline_here(root: Path) -> tuple[str, list[str]]:
    """The baseline's text in the working tree — empty when absent. A symlinked baseline is
    refused (read as empty, so it can only shrink the legacy set) rather than followed."""
    path = root / UNSIGNED_BASELINE
    if path.is_symlink():
        return "", [f"{UNSIGNED_BASELINE}: a symlink — the baseline is a plain file"]
    if not path.exists():
        return "", []
    try:
        return path.read_text(encoding="utf-8"), []
    except (OSError, UnicodeDecodeError) as exc:
        return "", [f"{UNSIGNED_BASELINE}: unreadable ({exc})"]


def legacy_records(root: Path, base: str) -> dict[str, str]:
    """The FROZEN legacy set, `{path: record_digest}`: records that may lack `provenance`.

    A path is in it only when ALL hold: it is in `unchanged_base_records` (on the base, untouched
    here), this checkout's baseline names it, and that `(path, digest)` is in fleet's
    `FROZEN_UNSIGNED` anchor. The caller still compares the digest against the record's content
    (`validate_home`). "On the base" alone — or a baseline line on the base alone — would
    grandfather any unsigned record that reached a moving base around this gate."""
    unchanged = unchanged_base_records(root, base)
    here, _ = parse_unsigned_baseline(_baseline_here(root)[0])
    return {path: digest for path, digest in here.items() if path in unchanged and (path, digest) in FROZEN_UNSIGNED}


def baseline_growth_violations(root: Path, base: str) -> list[str]:
    """Every baseline line fleet never froze, and every malformed line.

    The baseline only shrinks against the base, with one exception: a line from fleet's
    `FROZEN_UNSIGNED` anchor may be (re)added — that is how a repository seeds it in the change that
    takes this pin. A line outside the anchor fails whether this change added it or the base already
    had it (an admin merge, a PR under an older pin): no consumer-side write can freeze a record.
    Removing a line makes its record strict, and append-only forbids deleting or signing that
    record, so a line is removed only together with a fleet change that drops it from the anchor."""
    at_base, _ = parse_unsigned_baseline(_baseline_at(root, base))
    text, problems = _baseline_here(root)
    here, malformed = parse_unsigned_baseline(text)
    problems.extend(malformed)
    for path, digest in here.items():
        if (path, digest) in FROZEN_UNSIGNED:
            continue
        if at_base.get(path) == digest:
            problems.append(
                f"{UNSIGNED_BASELINE}: {path} {digest} is not in fleet's frozen set — this baseline line "
                "reached the base around the gate and freezes nothing"
            )
        else:
            problems.append(
                f"{UNSIGNED_BASELINE}: adds {path} {digest} — the unsigned-record baseline may only shrink, "
                "and fleet never froze this line"
            )
    return problems


def validate_home(root: Path, *, legacy: dict[str, str] | None = None) -> list[str]:
    """Every problem with a record under the reviews home, as `<path>: <why>` lines.

    `legacy` (from `legacy_records`) maps the records that may lack `provenance` to the digest
    they were frozen at: one of them that is otherwise valid AND still hashes to that digest is
    not a problem. Empty by default — strict. A symlink anywhere under the home is refused: its
    resolved path could name a legacy record its own path is not."""
    legacy = legacy or {}
    home = root / REVIEWS_SUBDIR
    problems: list[str] = []
    if not home.is_dir():
        return problems
    for path in sorted(home.rglob("*")):
        if path.is_symlink():
            problems.append(f"{path.relative_to(root).as_posix()}: a symlink — records are plain files")
            continue
        if path.is_dir():
            continue
        rel = _rel(root, path)
        if path.suffix != ".json":
            problems.append(f"{rel}: only JSON records live under {REVIEWS_SUBDIR}/")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            problems.append(f"{rel}: unreadable ({exc})")
            continue
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
            problems.append(f"{rel}: not a schema_version {SCHEMA_VERSION} record")
            continue
        try:
            _validate_one(root, path, data)
        except UnsignedRecordError as exc:
            frozen = legacy.get(rel)
            if frozen is None:
                problems.append(f"{rel}: {exc}")
            elif record_digest(data) != frozen:
                problems.append(f"{rel}: {exc}; its digest is not the one {UNSIGNED_BASELINE} froze")
        except (ReviewError, ValueError) as exc:
            problems.append(f"{rel}: {exc}")
    return problems


def legacy_for_validate(root: Path, explicit: str) -> dict[str, str]:
    """The frozen legacy set against `explicit` or the merge base — EMPTY when no base resolves, so
    a checkout that cannot diff holds every record to the rule rather than waving one through."""
    try:
        return legacy_records(root, resolve_base(root, explicit))
    except ReviewError:
        return {}


def _validate_one(root: Path, path: Path, data: dict[str, Any]) -> None:
    record = data.get("record")
    parent = path.parent.name
    reviewer = str(data.get("reviewer") or "")
    if not _TOKEN_RE.match(reviewer):
        raise ReviewError("reviewer must be one run-id token")
    if parent == ORACLES:
        match = _ORACLE_NAME_RE.match(path.name)
        if record != "oracle" or not match:
            raise ReviewError("an oracles/ file is an oracle record named <scenario>-v<N>.json")
        raw_version = data.get("version")
        built = build_oracle(
            scenario=str(data.get("scenario") or ""),
            version=raw_version if isinstance(raw_version, int) else 0,
            decision=str(data.get("decision") or ""),
            reason=str(data.get("reason") or ""),
            reviewer=reviewer,
            at=parse_utc(str(data.get("at") or "")),
            expected_sha256=str(data.get("expected_sha256") or ""),
        )
        if (built["scenario"], str(built["version"])) != (match["scenario"], match["version"]):
            raise ReviewError("the filename does not name the record's scenario and version")
        _check_provenance(data, needed=built["decision"] == "approved", what="an oracle approval")
        return
    if parent == PLANTED:
        match = _PLANTED_NAME_RE.match(path.name)
        if record != "planted" or not match:
            raise ReviewError("a planted/ file is a planted record named <scenario>-<YYYY-MM-DD>.json")
        verdicts = data.get("verdicts")
        built = build_planted(
            scenario=str(data.get("scenario") or ""),
            mutation=str(data.get("mutation") or ""),
            environment_id=str(data.get("environment_id") or ""),
            verdicts=verdicts if isinstance(verdicts, list) else [],
            reviewer=reviewer,
            at=parse_utc(str(data.get("at") or "")),
        )
        if built["environment_id"] != PLANTED_ENVIRONMENT:
            raise ReviewError(f"a planted bug ran on {built['environment_id']!r}, not {PLANTED_ENVIRONMENT!r}")
        if data.get("caught") is not built["caught"]:
            raise ReviewError("`caught` disagrees with the embedded verdicts")
        if built["scenario"] != match["scenario"]:
            raise ReviewError("the filename does not name the record's scenario")
        _check_provenance(data, needed=bool(built["caught"]), what="a caught planted outcome")
        return
    if record != "review" or not _REVIEW_NAME_RE.match(path.name):
        raise ReviewError(
            "a review file is named <result-stem>--<YYYY-MM-DD>-<HHMMSS>Z.json and carries record: review"
        )
    result_rel, result = load_result(root, str(data.get("result_file") or ""))
    if parent != result.get("kind"):
        raise ReviewError(f"a review of a {result.get('kind')!r} result lives under reviews/{result.get('kind')}/")
    entries = data.get("verdicts")
    kind = data.get("reviewer_kind")
    if kind is not None and kind not in REVIEWER_KINDS:
        raise ReviewError(f"reviewer_kind {kind!r} must be one of {REVIEWER_KINDS}")
    built = build_review(
        result_rel=result_rel,
        result=result,
        reviewer=reviewer,
        at=parse_utc(str(data.get("reviewed_at") or "")),
        entries=entries if isinstance(entries, list) else [],
        reviewer_kind=kind,
    )
    _check_provenance(
        data,
        needed=any(v["state"] == "verified" for v in built["verdicts"]),
        what="a verified review",
        bound=_bound_version(result.get("scenario_version")),
    )


def _check_provenance(data: dict[str, Any], *, needed: bool, what: str, bound: str = "") -> None:
    """The repository-side rule: a record that makes a pass count carries a well-formed
    `provenance` (shape only), recomputed when the secret is in this environment (CI)."""
    if PROVENANCE_FIELD in data and not _provenance_shape_ok(data):
        raise ReviewError("provenance must be the 64-hex token the dispatched verifier's key signed")
    if not needed:
        return
    if not _provenance_shape_ok(data):
        raise UnsignedRecordError(
            f"{what} carries no provenance — only a dispatched qa:verify run can sign one (BUG-1144)"
        )
    if _secret_from_env() and not _verifiable(
        data, bound=bound, env={k: v for k, v in os.environ.items() if k != QA_REVIEW_KEY_ENV}
    ):
        raise ReviewError(
            f"{what}'s provenance does not match a dispatched verifier run's key for this record (BUG-1144)"
        )


def resolve_base(root: Path, explicit: str) -> str:
    """The commit to diff against — `--base`, else the merge base with `origin/main`. Fails closed."""
    if explicit:
        out = _git(root, "rev-parse", "--verify", "--quiet", f"{explicit}^{{commit}}")
    else:
        out = _git(root, "merge-base", "HEAD", DEFAULT_BASE_REF)
    if out.returncode != 0 or not out.stdout.strip():
        raise ReviewError(
            f"no comparison base ({explicit or 'merge-base HEAD ' + DEFAULT_BASE_REF}) — fetch it or pass --base; "
            "a diff gate that cannot diff fails rather than passing"
        )
    return out.stdout.strip()


def _changes(root: Path, base: str) -> list[tuple[str, str]]:
    """`(status, path)` for every change between `base` and the working tree, committed or not."""
    # `-z` everywhere: without it git C-quotes a path with a non-ASCII byte (`"…\\303\\244.json"`),
    # and a quoted deletion would miss the reviews-home prefix and escape `append-only`.
    out = _git(root, "diff", "--name-status", "-z", "--no-renames", base)
    if out.returncode != 0:
        raise ReviewError(f"git diff against {base} failed: {out.stderr.strip()}")
    untracked = _git(root, "ls-files", "-z", "--others", "--exclude-standard")
    if untracked.returncode != 0:
        raise ReviewError(f"git ls-files failed: {untracked.stderr.strip()}")
    fields = out.stdout.split("\0")
    rows: list[tuple[str, str]] = []
    for status, path in zip(fields[0::2], fields[1::2], strict=False):
        if status and path:
            rows.append((status.strip()[:1], path))
    rows.extend(("A", p) for p in untracked.stdout.split("\0") if p)
    return rows


def append_only_violations(root: Path, base: str) -> list[str]:
    """Every existing record this change modifies or deletes — only additions are allowed."""
    prefix = REVIEWS_SUBDIR + "/"
    return [
        f"{path}: {'deleted' if status == 'D' else 'modified'} — records under {REVIEWS_SUBDIR}/ are append-only"
        for status, path in _changes(root, base)
        if path.startswith(prefix) and status != "A"
    ]


def pr_scope_violations(root: Path, base: str) -> list[str]:
    """Every changed path outside the reviews home — the records PR carries records and nothing else."""
    prefix = REVIEWS_SUBDIR + "/"
    return [
        f"{path}: outside {REVIEWS_SUBDIR}/ — a verifier records PR carries only records"
        for _status, path in _changes(root, base)
        if not path.startswith(prefix)
    ]


# ───────────────────────────── the CLI ─────────────────────────────


def _pairs(raw: list[str], flag: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for item in raw:
        key, sep, value = item.partition("=")
        if not sep or not key.strip():
            raise ReviewError(f"{flag} expects ID=VALUE, got {item!r}")
        out.append((key.strip(), value.strip()))
    return out


def _review_entries(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.verdict_file:
        loaded = _load_json(Path(args.verdict_file))
        if not isinstance(loaded, list):
            raise ReviewError("--verdict-file holds a JSON list of {id, state, reason, evidence_checked, ticket}")
        return [dict(x) if isinstance(x, dict) else {"id": x} for x in loaded]
    entries: dict[str, dict[str, Any]] = {}
    for vid, state in _pairs(args.state, "--state"):
        entries[vid] = {"id": vid, "state": state, "evidence_checked": []}
    for flag, dest in (("--reason", "reason"), ("--ticket", "ticket")):
        for vid, value in _pairs(getattr(args, dest), flag):
            if vid not in entries:
                raise ReviewError(f"{flag} names {vid!r}, which no --state declared")
            entries[vid][dest] = value
    for vid, value in _pairs(args.checked, "--checked"):
        if vid not in entries:
            raise ReviewError(f"--checked names {vid!r}, which no --state declared")
        entries[vid]["evidence_checked"].append(value)
    return list(entries.values())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="The QA verifier's records (FLT-1213/1214/1215).")
    parser.add_argument("--root", default="", help="the checkout (default: this repo)")
    parser.add_argument("--at", default="", help="a fixed RFC3339 instant (for tests)")
    sub = parser.add_subparsers(dest="command", required=True)

    sample = sub.add_parser("sample", help="print what this run re-grades, as JSON")
    sample.add_argument("--since-days", type=int, default=7)
    sample.add_argument("--percent", type=int, default=20)

    review = sub.add_parser("review", help="write one review record for one result file")
    review.add_argument("--result", required=True)
    review.add_argument("--reviewer", default="", help=f"must equal ${RUN_ID_ENV} when given")
    review.add_argument("--verdict-file", default="")
    review.add_argument("--state", action="append", default=[], metavar="ID=STATE")
    review.add_argument("--reason", action="append", default=[], metavar="ID=TEXT")
    review.add_argument("--checked", action="append", default=[], metavar="ID=TOKEN")
    review.add_argument("--ticket", action="append", default=[], metavar="ID=KEY")

    oracle = sub.add_parser("oracle", help="approve or reject a scenario version's expected results")
    oracle.add_argument("--scenario", required=True)
    oracle.add_argument("--version", required=True, type=int)
    group = oracle.add_mutually_exclusive_group(required=True)
    group.add_argument("--approve", action="store_true")
    group.add_argument("--reject", action="store_true")
    oracle.add_argument("--reason", required=True)
    oracle.add_argument("--reviewer", default="")

    mode = sub.add_parser("mode", help="nightly or planted, from the issue's exact title")
    mode.add_argument("--title", required=True)

    sub.add_parser("planted-pick", help="print the scenario whose planted bug is due, as JSON")

    planted = sub.add_parser("planted-run", help="run the planted-bug check end to end")
    planted.add_argument("--scenario", required=True)
    planted.add_argument("--environment-id", default=PLANTED_ENVIRONMENT)
    planted.add_argument("--teardown", default="", help="a command run in the worktree afterwards, always")
    planted.add_argument("--reviewer", default="")
    planted.add_argument("run", nargs=argparse.REMAINDER, help="-- the command that brings the stack up and runs it")

    digest = sub.add_parser("digest", help="print a written record's digest, for the attest_qa_review tool")
    digest.add_argument("record", help="the record's path, as review/oracle/planted-run printed it")
    check = sub.add_parser("validate", help="check every record under the reviews home")
    check.add_argument(
        "--base",
        default="",
        help=(
            f"records unchanged since this commit and frozen in {UNSIGNED_BASELINE} may lack provenance "
            f"(default: merge-base with {DEFAULT_BASE_REF})"
        ),
    )
    for name, text in (
        ("append-only", "refuse a modified or deleted record, or a line added to the unsigned baseline"),
        ("pr-scope", "records only"),
    ):
        gate = sub.add_parser(name, help=text)
        gate.add_argument("--base", default="", help=f"the base commit (default: merge-base with {DEFAULT_BASE_REF})")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        root = Path(args.root).resolve() if args.root else _repo.repo_root()
        at = parse_utc(args.at) if args.at else datetime.now(UTC)
        if args.command == "sample":
            print(json.dumps(select_sample(root, now=at, since_days=args.since_days, percent=args.percent), indent=2))
            return 0
        if args.command == "mode":
            print(mode_of(args.title))
            return 0
        if args.command == "planted-pick":
            print(json.dumps(planted_pick(root), indent=2))
            return 0
        if args.command == "digest":
            print(attestation_digest(root, args.record))
            return 0
        if args.command in ("validate", "append-only", "pr-scope"):
            if args.command == "validate":
                problems = validate_home(root, legacy=legacy_for_validate(root, args.base))
            elif args.command == "append-only":
                base = resolve_base(root, args.base)
                problems = append_only_violations(root, base) + baseline_growth_violations(root, base)
            else:
                problems = pr_scope_violations(root, resolve_base(root, args.base))
            for line in problems:
                print(f"qa_review: {line}", file=sys.stderr)
            return 1 if problems else 0
        if args.command == "review":
            reviewer, reviewer_kind = resolve_review_signer(args.reviewer)
            path = write_review(
                root=root,
                result_file=args.result,
                reviewer=reviewer,
                at=at,
                entries=_review_entries(args),
                reviewer_kind=reviewer_kind,
                # ENVIRONMENT ONLY: the key is a bearer value, so it has no flag (argv is world-
                # readable and lands in session logs) and is never printed.
                review_key=(os.environ.get(QA_REVIEW_KEY_ENV) or "").strip(),
            )
            print(_rel(root, path))
            return 0
        reviewer = resolve_reviewer(args.reviewer)
        if args.command == "oracle":
            path = write_oracle(
                root=root,
                scenario=args.scenario,
                version=args.version,
                decision="approved" if args.approve else "rejected",
                reason=args.reason,
                reviewer=reviewer,
                at=at,
                review_key=(os.environ.get(QA_REVIEW_KEY_ENV) or "").strip(),
            )
        else:
            run = list(args.run)
            if run and run[0] == "--":
                run = run[1:]
            path = planted_run(
                root=root,
                scenario=args.scenario,
                command=run,
                teardown=args.teardown.split() if args.teardown else [],
                reviewer=reviewer,
                at=at,
                environment_id=args.environment_id,
                review_key=(os.environ.get(QA_REVIEW_KEY_ENV) or "").strip(),
            )
    except (ReviewError, ValueError) as exc:
        print(f"qa_review: {exc}", file=sys.stderr)
        return 1
    print(_rel(root, path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
