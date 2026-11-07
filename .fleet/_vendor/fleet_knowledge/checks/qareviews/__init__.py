"""The QA verifier's records stay whole: valid, and append-only (FLT-1213, FLT-1214, FLT-1215).

`knowledge/audits/reviews/` holds the second party's word on the QA agent's passes. The desk's
reader cannot see a record that is gone — delete a dispute and the pass quietly reads unverified,
which counts toward green — so integrity is enforced here, at the gate, by the same code that
writes the records (`commandtree/scripts/qa_review.py`):

  * every record validates (`qa_review.py validate`) — except that a FROZEN legacy record may
    lack the BUG-1144 `provenance` it predates (it counts for nothing at the reader, and
    append-only forbids signing it after the fact). Frozen means named with its `record_digest`
    in `knowledge/audits/qa-unsigned.baseline`, that line in fleet's own frozen set
    (`qa_review.FROZEN_UNSIGNED`), on the base untouched, and still hashing to that digest — "on
    the base" alone would grandfather anything that reached a moving base around this gate (a
    fleet pin moved backwards, an admin merge);
  * no change modifies, renames or deletes an existing record — a diff against the merge base
    with `origin/main` (`qa_review.py append-only`), failing closed when there is no base;
  * no line of that baseline is outside fleet's frozen set — it may only shrink, except that a
    frozen line may be seeded.

Applies only to a checkout that has a reviews home, so a repository without the Quality desk
skips it with a line saying so.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from fleet_knowledge.config import KnowledgeBase, git_context
from fleet_knowledge.runner import Finding

_SCRIPT = Path(__file__).resolve().parents[2] / "commandtree" / "scripts" / "qa_review.py"
_REVIEWS = "knowledge/audits/reviews"


def _module() -> ModuleType:
    scripts = str(_SCRIPT.parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location("fleet_knowledge_qa_review", _SCRIPT)
    assert spec and spec.loader  # noqa: S101 — the script ships inside this package
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class QaReviewRecords:
    name = "qa-review-records"
    title = "The QA verifier's records are valid and append-only"
    description = (
        "Every review, oracle and planted-bug record under knowledge/audits/reviews/ validates, and no "
        "change modifies or deletes one — a deleted dispute would turn a disputed pass green."
    )

    def applies(self, kb: KnowledgeBase) -> bool:
        """The home (or the unsigned baseline) exists here, OR the base had either — deleting every record removes the
        directory, and a check that then skipped would wave through exactly the change it exists
        to refuse.

        Fails CLOSED when the base cannot be read: with no home at the head and no readable base,
        whether the base had records is unknowable, so the check must run and let `run()` error
        rather than skip. Anything else waves the delete-every-record change through in a shallow
        clone or any checkout without the base commit.
        """
        mod = _module()
        baseline = kb.root / mod.UNSIGNED_BASELINE
        # A baseline alone also applies: otherwise lines could be pre-seeded, unchecked, in a
        # repository that has no records yet.
        if (kb.root / _REVIEWS).is_dir() or baseline.exists() or baseline.is_symlink():
            return True
        try:
            base = mod.resolve_base(kb.root, git_context(kb).base)
        except mod.ReviewError:
            return True
        listed = subprocess.run(
            [
                "git",
                "-C",
                str(kb.root),
                "ls-tree",
                "-r",
                "--name-only",
                base,
                "--",
                _REVIEWS + "/",
                mod.UNSIGNED_BASELINE,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if listed.returncode != 0:
            return True
        return bool(listed.stdout.strip())

    def run(self, kb: KnowledgeBase) -> list[Finding]:
        mod = _module()
        try:
            # The caller's base (a pull request's base sha, passed as `--base`) beats the
            # merge-base-with-origin/main fallback, as in `commitments/checks.py`: on a CI merge ref
            # or a shallow clone only the caller still knows which commit this change is measured
            # against.
            base = mod.resolve_base(kb.root, git_context(kb).base)
            violations = mod.append_only_violations(kb.root, base)
            # Frozen legacy records may predate BUG-1144's provenance rule: append-only forbids
            # signing them now, and the reader gives them no weight. Frozen = in the baseline at the
            # base AND here with the same digest, and on the base untouched (`legacy_records`).
            legacy = mod.legacy_records(kb.root, base)
            grown = mod.baseline_growth_violations(kb.root, base)
        except mod.ReviewError as exc:
            # No base: every record is held to the rule (fail closed), and the diff half errors.
            return [
                *self._invalid(mod, kb, {}),
                Finding(
                    level="error",
                    message=str(exc),
                    hint="pass the pull request's base (`fleet check --base <sha>`) or fetch origin/main",
                ),
            ]
        findings = self._invalid(mod, kb, legacy)
        findings.extend(
            Finding(
                level="error",
                message=line,
                hint="restore the record from the base; a changed judgement is a NEW review, never an edit",
                command="python3 knowledge/scripts/qa_review.py append-only",
            )
            for line in violations
        )
        findings.extend(
            Finding(
                level="error",
                message=line,
                hint=(
                    "the unsigned-record baseline holds only lines fleet froze (qa_review.FROZEN_UNSIGNED) — "
                    "an unsigned record written since must be signed by a dispatched qa:verify run, never listed"
                ),
                command="python3 knowledge/scripts/qa_review.py append-only",
            )
            for line in grown
        )
        return findings

    @staticmethod
    def _invalid(mod: ModuleType, kb: KnowledgeBase, legacy: dict[str, str]) -> list[Finding]:
        return [
            Finding(
                level="error",
                message=line,
                hint="records are written only by knowledge/scripts/qa_review.py — rewrite it through the script",
                command="python3 knowledge/scripts/qa_review.py validate",
            )
            for line in mod.validate_home(kb.root, legacy=legacy)
        ]


CHECKS = [QaReviewRecords()]
