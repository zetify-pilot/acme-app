"""Validate PRD implementation plans against the contract the planning stage declares.

`plan` is the only stage in the PRD chain with no gate, no subagent and no critique — its
spine is seven author/io steps. It is also the contract implementation is forbidden to
question ("implement exactly what the plan says"), so every planning defect passes straight
into execution unexamined. These checks give the seam teeth.

Three rules, each one a sentence the plan command already asserts and nothing enforced:

  1. Every effort id (`E<N>`) introduced by a plan is owned by at least one task.
     *"an unreferenced `E<N>` means the plan is incomplete"*.
  2. A plan covering user-visible criteria carries at least one browser-verification row.
     *"If any UI AC has no `playwright` row, the plan is incomplete"* — a UI criterion
     verified only by a unit test is verified against mocks, not the page.
  3. A PRD with a frontend plan that adds or materially changes a surface has an approved
     mockup — a `ux-design.md` containing an `## Approved design` block. *"If a UI surface
     has no approved mockup, the plan is blocked, not degraded"* — which the plan command
     could never check, because it never read the file.

     Narrowed: the gate protects *surfaces*, not every pixel that lands on one. A plan that
     adds nothing but fields to a page that already exists may instead declare
     `## Surface scope: additive to an existing surface` and cite that page's authored
     `<Page>.spec.md` as its fidelity target. Checked, not taken on trust: the cited spec must
     exist AND predate this plan in git history, so a page-spec authored alongside the plan
     (a NEW surface wearing an additive label) still needs the mockup.

     "Exist" is judged at the time the plan was written, not today: a page retired after the
     plan shipped takes its spec with it, and the plan citing it is still a truthful record of
     what it was built against. A cited spec gone from disk is accepted iff git history shows
     it was added BEFORE the plan — it is reported as an advisory, never silenced — and one
     that was never committed, or was added only with or after the plan, still fails.

Plans authored before the cutover predate the contract; rewriting them would be inventing
review that never happened.

Ported from `scripts/validate_prd_plans.py`; messages and exit code unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import _git
from ._api import ADVISORY, ERROR, Report, finding
from ._config import PlanningConfig
from ._git import first_commit_dates, is_repository
from ._markdown import read, rel

NAME = "prd-plans"

#: A task id as the plans write them: `F4` (frontend) or `B7` (backend).
TASK_RE = re.compile(r"\b[FB]\d+\b")
EFFORT_ROW_RE = re.compile(r"^\|\s*(E\d+)\s*\|(.*)$")
#: Date used for a path git has never seen — recent enough that every comparison against it
#: fails closed (an uncommitted page-spec never counts as predating a plan).
NEVER_COMMITTED = "9999-12-31"


def _plan_re(cfg: PlanningConfig) -> re.Pattern[str]:
    return re.compile(cfg.plan_filename_pattern)


def _match(cfg: PlanningConfig, name: str) -> re.Match[str]:
    m = _plan_re(cfg).match(name)
    assert m is not None, f"{name} is not a plan file name"
    return m


def discover_plans(kb: Any) -> list[Path]:
    """All plan files under the PRD tree, in execution order.

    Backend family first, then frontend; within each family the base file precedes its
    numbered splits in numeric order. This is the order a single implementation run executes
    them into one branch, and the order a reader should see findings in.
    """
    cfg = PlanningConfig.of(kb)
    prds = Path(kb.knowledge) / cfg.prds_dir
    pattern = _plan_re(cfg)
    plans: list[Path] = []
    for fam in ("backend-plan", "frontend-plan"):
        family = [p for p in prds.glob(f"*/{fam}*.md") if pattern.match(p.name)]
        family.sort(key=lambda p: int(_match(cfg, p.name).group("n") or 0))
        plans.extend(family)
    return plans


def cited_page_specs(text: str, cfg: PlanningConfig) -> list[str]:
    """Repo-relative `<Page>.spec.md` paths a plan cites as its fidelity target.

    The `/` in the pattern is what makes it a CITATION: a bare `Foo.spec.md` in prose is a
    mention of the file, not a pointer an implementer can open, and holding prose to the
    existence check would push authors toward writing less about their fidelity target.
    """
    return sorted({m.group(1).lstrip("./") for m in re.finditer(cfg.page_spec_pattern, text)})


def _check_effort_coverage(plan: Path, text: str, out: list[tuple[Path, str]]) -> None:
    """Every `E<N>` the plan defines must be claimed by a task.

    A plan defines efforts in a coverage matrix and claims them in task headings. An effort
    defined and never claimed is work nobody was assigned — the plan looks complete and ships
    a hole.
    """
    orphans = []
    for line in text.splitlines():
        m = EFFORT_ROW_RE.match(line.strip())
        if m and not TASK_RE.search(m.group(2)):
            orphans.append(m.group(1))
    if orphans:
        out.append(
            (
                plan,
                f"effort row(s) {', '.join(sorted(set(orphans)))} name no owning task — "
                "an unreferenced effort is work nobody was assigned",
            )
        )


def _check_browser_row(plan: Path, text: str, cfg: PlanningConfig, out: list[tuple[Path, str]]) -> None:
    """A frontend plan verifies at least one criterion in a real browser.

    A unit runner mocks the component library, the portal-based dialogs and the graph canvas,
    so the unit suite can be entirely green while the page crashes on load. A frontend plan
    whose every verification is a unit test has not planned to look at the thing it is building.
    """
    token = cfg.browser_verification_token
    if not token:
        return
    if token.lower() not in text.lower():
        out.append(
            (
                plan,
                f"frontend plan has no `{token}` verification row — a UI criterion "
                "verified only by vitest is verified against mocks, not the page",
            )
        )


def _check_approved_mockup(prd_dir: Path, plan: Path, cfg: PlanningConfig, out: list[tuple[Path, str]]) -> None:
    """A frontend plan requires an approved mockup. `plan` asserts this and cannot see it."""
    ux = prd_dir / cfg.ux_design_file
    if not ux.exists():
        out.append(
            (
                plan,
                f"frontend plan with no `{cfg.ux_design_file}` — a UI surface needs an approved mockup "
                "before it can be planned (plan.md: blocked, not degraded)",
            )
        )
        return
    if not re.search(cfg.approved_design_heading, read(ux), re.M):
        out.append(
            (
                plan,
                f"{ux.name} has no `## Approved design` block — the human approval gate "
                "produced no record, so nothing shows the mockup was ever approved",
            )
        )


def _check_surface_gate(
    repo_root: Path,
    prd_dir: Path,
    plan: Path,
    text: str,
    dates: dict[str, str],
    cfg: PlanningConfig,
    out: list[tuple[Path, str]],
    notes: list[tuple[Path, str]] | None = None,
) -> None:
    """Route a frontend plan to the mockup gate, or to the additive-surface exemption.

    The exemption is not a self-declaration: a plan claiming to be additive must name a
    page-spec that BOTH exists and predates the plan in git. That is what separates "a field
    on a page that already shipped" from "a new page whose spec I wrote just now" — the second
    one is a surface, and a surface needs a human to have seen it.

    Both halves are judged as of the plan: a spec deleted from disk AFTER the plan was written
    (its page retired later) existed when the plan cited it, so it still satisfies the gate and
    lands in `notes` as an advisory rather than failing a historical record forever.
    """
    if not re.search(cfg.additive_surface_pattern, text, re.M | re.I):
        _check_approved_mockup(prd_dir, plan, cfg, out)
        return

    specs = cited_page_specs(text, cfg)
    if not specs:
        out.append(
            (
                plan,
                "declares `Surface scope: additive to an existing surface` but cites no "
                "`<Page>.spec.md` — an additive change still needs a fidelity target, and the "
                "page-spec is it",
            )
        )
        return

    plan_date = dates.get(rel(plan, repo_root), NEVER_COMMITTED)
    gone = [s for s in specs if not (repo_root / s).exists()]
    # Gone from disk but added before the plan: it existed when the plan was written and was
    # retired since. Anything else gone — never committed, or added only with/after the plan —
    # is a target nobody could ever have opened.
    retired = [s for s in gone if dates.get(s, NEVER_COMMITTED) < plan_date]
    missing = [s for s in gone if s not in retired]
    if missing:
        out.append(
            (
                plan,
                f"cites page-spec(s) that do not exist: {', '.join(missing)} — a fidelity "
                "target nothing can open is the same defect as citing a hosted URL",
            )
        )
        return
    if retired and notes is not None:
        notes.append(
            (
                plan,
                f"cites page-spec(s) retired after this plan was written: {', '.join(retired)} — "
                "accepted, because git history shows each existed when the plan cited it; an "
                "implementer still working from this plan has no fidelity target to open",
            )
        )

    if not [s for s in specs if dates.get(s, NEVER_COMMITTED) < plan_date]:
        out.append(
            (
                plan,
                f"claims an additive surface scope, but every cited page-spec ({', '.join(specs)}) "
                "was authored with this plan rather than before it — a page whose spec is new is a "
                "NEW surface, which needs an approved mockup, not an additive declaration",
            )
        )


def _plan_walk_refusal(cfg: PlanningConfig, kb: Any, repo_root: Path) -> str:
    """The refusal text when either history walk fails.

    Shared by the two walks so both name the same cause and repair: a failed walk is not
    "no dates", and guessing is the ENG-9479 mechanism — every plan read as never committed,
    the pre-cutover grandfather emptied, and the whole legacy corpus reported as phantom
    violations, none of them real.
    """
    prds_rel = rel(Path(kb.knowledge) / cfg.prds_dir, repo_root)
    return _git.walk_refusal(
        "PRD plan validation",
        cfg.plan_cutover,
        f"git log --diff-filter=A --name-only --format=%x00%cs --reverse -- {prds_rel}",
        "Each plan is dated via `git log --diff-filter=A` to grandfather plans authored before "
        f"{cfg.plan_cutover}. Undated, every plan reads as never committed: nothing is grandfathered "
        "and the entire corpus — plans that predate the contract included — is reported as phantom "
        "violations, none of them real.",
    )


def analyse(kb: Any) -> Report:
    """Every plan defect, in execution order.

    Refuses — a shallow clone, or a history walk that failed — rather than guessing: an
    undateable corpus is one the grandfather cannot be applied to, and guessing turns the
    failure into corpus-wide phantom violations.
    """
    cfg = PlanningConfig.of(kb)
    repo_root = Path(kb.root)
    report = Report()

    # Refuse a shallow clone before dating. Without full history every plan dates to the
    # shallow boundary, the pre-cutover grandfather is empty, and this gate reports hundreds
    # of phantom violations on files nobody touched — blaming innocent PRDs with no hint that
    # clone depth is the cause. Name it and stop.
    if _git.is_shallow(repo_root):
        report.refusal = cfg.plans_shallow_refusal.format(cutover=cfg.plan_cutover)
        return report

    plans = discover_plans(kb)
    texts = {p: read(p) for p in plans}
    prds_rel = rel(Path(kb.knowledge) / cfg.prds_dir, repo_root)

    # ── Bound the history walk by the cutover (ENG-13723) ────────────────────────────────
    # `first_commit_dates` passes one pathspec per plan, so its cost is linear in the corpus
    # and moves 2-3x with runner capacity (measured 103s at 1,340 pathspecs, 2026-09-29 —
    # the single most expensive step in the suite, and the reason the ceiling was raised
    # three times). Only a plan born at/after `plan_cutover` is ever checked, so date the
    # plans with the ONE-directory, `--since`-bounded walk (`_git.first_commit_dates_since`,
    # 0.34s on the same corpus) and keep the per-pathspec walk for the cited page-specs
    # alone — far fewer, and undateable by a cutover filter because a spec the additive
    # exemption cites can legitimately predate the cutover.
    #
    # A plan ABSENT from HEAD is uncommitted — being authored right now, at pre-commit — and
    # has no add to date. `first_commit_dates` would date it NEVER_COMMITTED, every rule
    # applies to it, and that is how the gate has always validated a new plan before its
    # commit exists. Preserve it: treat every uncommitted plan as a candidate and let the
    # NEVER_COMMITTED default stand. (A committed pre-cutover plan, by contrast, is in HEAD
    # and absent from the bounded walk — grandfathered, never reached.)
    plan_dates = _git.first_commit_dates_since(repo_root, cfg.plan_cutover, prds_rel)
    if plan_dates is None:
        report.refusal = _plan_walk_refusal(cfg, kb, repo_root)
        return report
    head = _git.head_tree(repo_root, prds_rel)
    candidates = [
        p for p in plans if rel(p, repo_root) not in head or plan_dates.get(rel(p, repo_root), "") >= cfg.plan_cutover
    ]
    # Cited specs of the CANDIDATE frontend plans — a spec is deliberately NOT cutover-filtered
    # (see above). Deleted specs are walked too: `--diff-filter=A` still finds the add of a
    # path absent from the working tree, which is what tells a retired spec from one that never
    # existed.
    specs = {
        repo_root / s
        for p in candidates
        if _match(cfg, p.name).group("fam") == "frontend-plan"
        for s in cited_page_specs(texts[p], cfg)
    }
    dates: dict[str, str] = dict(plan_dates)
    spec_dates = first_commit_dates(repo_root, sorted(specs))
    if spec_dates is None:
        # The specs walk FAILED — a wedged git, a corrupt object store, the timeout expired.
        # As above, that is not "no dates" and the gate refuses rather than grandfathering
        # every cited spec into a phantom NEW-surface finding.
        report.refusal = _plan_walk_refusal(cfg, kb, repo_root)
        return report
    dates.update(spec_dates)

    raw: list[tuple[Path, str]] = []
    notes: list[tuple[Path, str]] = []
    for plan in candidates:
        if dates.get(rel(plan, repo_root), NEVER_COMMITTED) < cfg.plan_cutover:
            # Born inside the two-day `--since` slack the bounded walk widens for timezone
            # skew, but still before the cutover: grandfathered, exactly as the full walk
            # would have it.
            continue
        text = texts[plan]
        _check_effort_coverage(plan, text, raw)
        if _match(cfg, plan.name).group("fam") == "frontend-plan":
            _check_browser_row(plan, text, cfg, raw)
            _check_surface_gate(repo_root, plan.parent, plan, text, dates, cfg, raw, notes)

    for path, message in raw:
        prd = path.parent.name
        report.findings.append(
            finding(
                ERROR,
                message,
                path=path,
                hint=_hint(message, cfg),
                command=_command(message, cfg, prd),
            )
        )
    for path, message in notes:
        report.findings.append(finding(ADVISORY, message, path=path))
        report.notes.append(f"{rel(path, repo_root)}: {message}")
    return report


def _hint(message: str, cfg: PlanningConfig) -> str | None:
    if "name no owning task" in message:
        return "Give every effort row an owning task id, or delete the row — an effort nobody owns ships a hole."
    if "verification row" in message:
        return f"Add a `{cfg.browser_verification_token}` row that drives the criterion in a real browser."
    if "no approved mockup" in message or "Approved design" in message or cfg.ux_design_file in message:
        return "A new surface needs a mockup a human approved before it can be planned — blocked, not degraded."
    if "page-spec" in message:
        return "Cite a page-spec that already exists in history, or drop the additive claim and get a mockup."
    return None


def _command(message: str, cfg: PlanningConfig, prd: str) -> str | None:
    if "page-spec" in message:
        return cfg.command("page_spec")
    if "no approved mockup" in message or "Approved design" in message or cfg.ux_design_file in message:
        return cfg.command("prd_design", prd=prd.split("-", 1)[0])
    if "name no owning task" in message or "verification row" in message:
        return cfg.command("prd_plan", prd=prd.split("-", 1)[0])
    return None


class PrdPlansCheck:
    """Plans own every effort they define, verify UI in a browser, and never plan a surface unseen."""

    name = NAME
    title = "PRD implementation plans"
    description = (
        "The planning stage has no gate of its own and is the contract implementation is forbidden to "
        "question, so a planning defect passes straight into execution unexamined. This check gives that "
        "seam teeth: every effort row is claimed by a task, every frontend plan verifies at least one "
        "criterion in a real browser rather than against mocks, and a plan that adds a surface has a mockup "
        "a human approved. The additive-surface exemption is verified rather than trusted — the page-spec it "
        "cites must exist AND predate the plan, so a new page cannot wear an additive label. Plans authored "
        "before the cutover predate the contract and are grandfathered; a shallow clone — or a history walk "
        "that fails outright — REFUSES rather than reporting phantom violations or passing clean."
    )

    def applies(self, kb: Any) -> bool:
        repo_root = Path(kb.root)
        if not is_repository(repo_root) or _git.is_shallow(repo_root):
            return False
        return bool(discover_plans(kb))

    def run(self, kb: Any) -> list[Any]:
        report = analyse(kb)
        if report.refusal:
            # The runner protocol carries findings only, and a refusal must never collapse
            # into a clean pass: surface it as the gating error it is. (A shallow clone never
            # reaches here — `applies()` skips it before `run` is called.)
            return [finding(ERROR, report.refusal)]
        return report.findings


CHECK = PrdPlansCheck()


def cli(kb: Any) -> int:
    """Reproduce `scripts/validate_prd_plans.py`'s stdout and exit code exactly."""
    report = analyse(kb)
    if report.refusal:
        print(report.refusal)
        return 1
    errors = report.errors
    if errors:
        print("PRD plan validation failed:")
        root = Path(kb.root)
        for e in errors:
            print(f"- {rel(e.path, root) if e.path else ''}: {e.message}")
        return 1
    for note in report.notes:
        print(f"note: {note}")
    print("PRD plans OK")
    return 0
