"""The slot answers the scaffold can write from facts Fleet already holds, instead of a placeholder.

`fleet init` and the setup pull request write one document per repo-tier slot under
`knowledge/slots/`. Most of them can only be a placeholder (`slots.STUB_MARKER`): how this
repository runs its tests, which languages it builds in, what the product is for. Two required
slots are different. Their answer is Fleet's own configuration, so a placeholder there is a
question asked of a person that Fleet could have answered itself:

  * `tracker-identity` — which tracker the install drives, its key prefix, the lane label that
    routes an issue to this repository, and that a session reaches issues only through Fleet's
    tools. The setup page chose all of it.
  * `git-workflow` — the default branch, the branch names the shipped commands use, who merges
    (the repository's Merging setting), the check Fleet posts and requires, and the ways a pull
    request silently does not merge. The shipped commands and the repository's settings fix all
    of it.

A scaffold that left both as placeholders reported "commands: 2/32 can run here" on a fresh
repository, right after the setup pull request merged.

**`RepoFacts` is what the caller knows, and every field may be unknown.** The setup endpoint
fills it from the install (`fleet_service.api.setup`); `fleet init` fills what its flags and the
local checkout say. A fact that is not known is never guessed: `tracker_identity` returns None
(the placeholder stays) when the tracker or its key prefix is unknown, and `git_workflow` names
the setting a reader looks at instead of a value it does not have.

**The answers follow the bootstrap's `## Answers` shape** (`process/knowledge-bootstrap-formats.md`
§7): one bold key per line. The shipped scripts read the key prefix off exactly that line
(`knowledge/scripts/_repo.py` `parse_key_prefix`), so the shape is load-bearing, not style.

Stdlib only.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "AGENTS",
    "PERSON",
    "TRACKERS",
    "RepoFacts",
    "git_workflow",
    "tracker_identity",
    "valid_key_prefix",
]

#: The two answers of the repository's Merging setting ("agents, on green checks" / "a person").
AGENTS = "agents"
PERSON = "person"

#: The trackers a written `tracker-identity` answer can name, as Fleet spells them. `none` is a real
#: backend (no tracker at all), but it has no key and no issues, so it answers nothing and the
#: placeholder stays.
TRACKERS: dict[str, str] = {"linear": "Linear", "jira": "Jira", "github": "GitHub Issues"}

#: A key prefix the shipped scripts can read back (`_repo.py` `_KEY_PREFIX_VALUE_RE`): a letter, then
#: letters and digits. A Linear team key and a Jira project key both have this shape.
_KEY_PREFIX = re.compile(r"[A-Za-z][A-Za-z0-9]{0,9}")

#: The note every written answer carries, so a reader knows where it came from and when it is stale.
_WRITTEN_BY = "Fleet wrote this file from its own settings. When a setting changes, change the line that names it."


def valid_key_prefix(prefix: str) -> bool:
    """Whether `prefix` (no trailing dash) is a key prefix the shipped scripts can read back."""
    return bool(_KEY_PREFIX.fullmatch(prefix.strip().rstrip("-")))


@dataclass(frozen=True, slots=True)
class RepoFacts:
    """What the caller knows about the repository and the install that serves it. Empty is unknown.

    `tracker` is `linear`, `jira`, `github` or `none`. `tracker_home` is where its issues live: the
    Linear team key, the Jira project key, or the GitHub repository (`owner/name`) holding the issues.
    `key_prefix` is the issue-key prefix without its dash (`ENG`); a GitHub key has none.

    `lane_label` is the `repo:<name>` label that routes an issue here, `""` when this repository is
    the install's default lane (an issue with no `repo:*` label is its work), and None when unknown.

    `merge` is `AGENTS` or `PERSON` (the repository's Merging setting), `""` when unknown; with
    `PERSON`, `human_merge_paths` narrows it to those paths (empty: every pull request), and
    `human_merge_exempt_paths` names what merges without a person anyway.

    `verify_check` is the name of the check Fleet posts on this repository's pull requests, `""` when
    Fleet posts none here, and None when unknown.
    """

    repository: str = ""
    default_branch: str = ""
    tracker: str = ""
    tracker_home: str = ""
    key_prefix: str = ""
    lane_label: str | None = None
    merge: str = ""
    human_merge_paths: tuple[str, ...] = ()
    human_merge_exempt_paths: tuple[str, ...] = ()
    verify_check: str | None = None


def _code_list(items: Sequence[str]) -> str:
    return ", ".join(f"`{item}`" for item in items)


# ── tracker-identity ─────────────────────────────────────────────────────────


def tracker_identity(facts: RepoFacts) -> str | None:
    """The `tracker-identity` answer the facts determine, or None when they do not (the placeholder stays).

    Answered for Linear and Jira when the key prefix is known, and for GitHub Issues (whose keys carry
    no prefix). An unknown tracker, `none`, or a prefixed tracker without a readable prefix is None:
    a wrong prefix is worse than none, because the shipped scripts compose issue ids from it.
    """
    kind = facts.tracker.strip().lower()
    name = TRACKERS.get(kind)
    if name is None:
        return None
    prefix = facts.key_prefix.strip().rstrip("-")
    home = facts.tracker_home.strip()
    if kind == "github":
        where = f"{name}, in the repository `{home}`" if home else name
        example = f"`{home}#12`" if home else "`owner/repository#12`"
        key_line = (
            f"- **key-prefix** — none: an issue is {example}. Its number belongs to that repository, "
            "so always write the repository with it."
        )
        positions = "On GitHub Issues each position is a `fleet:` label, and a closed issue is closed."
    else:
        if not valid_key_prefix(prefix):
            return None
        holder = "team" if kind == "linear" else "project"
        where = f"{name}, {holder} `{home or prefix}`"
        key_line = (
            f"- **key-prefix** — `{prefix.upper()}-` — an issue is `{prefix.upper()}-123`. A branch name lowercases it "
            f"(`{prefix.lower()}-123`). Read the key from the issue; never type a prefix from memory."
        )
        positions = (
            "On Linear each position is a workflow state on the team."
            if kind == "linear"
            else "On Jira each position is a `fleet:` label, and the issue's status follows its category."
        )
    if facts.lane_label is None:
        lane_line = (
            "- **lane-label** — the `repo:<name>` label Settings › Repositories shows for this repository. "
            "An issue with no `repo:*` label belongs to the install's default lane."
        )
    elif facts.lane_label == "":
        lane_line = (
            "- **lane-label** — none: this repository is the install's default lane. An issue with no "
            "`repo:*` label is its work. A filer who means this repository still says so, because another "
            "repository's label can be missing by mistake."
        )
    else:
        lane_line = (
            f"- **lane-label** — `{facts.lane_label}`. An issue with this label is this repository's work. "
            "A filer always sets it: an issue without it goes to the install's default lane."
        )
    lines = [
        "# tracker-identity",
        "",
        "Which issue tracker this repository files into, and how a session reaches it.",
        _WRITTEN_BY,
        "",
        "## Answers",
        "",
        f"- **tracker** — {where}. Fleet drives it; Settings › Set up shows the connection.",
        key_line,
        lane_line,
        "- **reach** — only through Fleet's tools: `get_issue`, `search_issues`, `file_issue`, `comment`, "
        "`move_issue`, `triage`. A session holds no tracker key or address, and never calls the tracker itself.",
        "- **positions** — Fleet keeps each issue's position. `.fleet/registers/triage-partition.md` lists the "
        f"positions and the moves between them. {positions}",
        "- **views** — this repository keeps no saved views. The queues a person works are Fleet's pages; "
        "the `queue` tool lists them.",
        "- **names** — label and position names come from Fleet's tools. Never type one from memory: a typo "
        "makes a new label, or a move that does not land.",
        "",
    ]
    return "\n".join(lines)


# ── git-workflow ─────────────────────────────────────────────────────────────


def _who_merges(facts: RepoFacts, namespace: str) -> list[str]:
    verify = f"`/{namespace}:verify`"
    if facts.merge == AGENTS:
        out = [
            "- **who-merges** — agents, on green checks (this repository's Merging setting in Fleet). "
            f"The {verify} session merges a fix once its verdict passes.",
            "- **arm** — `python3 knowledge/scripts/gh_automerge_arm.py <number>` arms auto-merge, squash; "
            "`python3 knowledge/scripts/gh_pr_merge_state.py` confirms it took. Never pass `--delete-branch`.",
        ]
    elif facts.merge == PERSON:
        scope = (
            f"pull requests that touch {_code_list(facts.human_merge_paths)}; "
            "agents merge every other one on green checks"
            if facts.human_merge_paths
            else "every pull request"
        )
        out = [
            f"- **who-merges** — a person, for {scope} (this repository's Merging setting in Fleet).",
            "- **arm** — on a pull request a person merges, an agent opens it, hands it off and stops. "
            "It never merges it and never arms auto-merge.",
        ]
        if facts.human_merge_exempt_paths:
            out.append(
                f"- **exempt** — a pull request that changes only {_code_list(facts.human_merge_exempt_paths)} "
                "merges without a person."
            )
    else:
        out = [
            "- **who-merges** — this repository's Merging setting in Fleet decides: agents on green checks, "
            "or a person. Settings › Repositories shows it.",
            "- **arm** — where agents merge, `python3 knowledge/scripts/gh_automerge_arm.py <number>` arms "
            "auto-merge. Where a person merges, an agent opens the pull request, hands it off and stops.",
        ]
    return out


def _required_checks(facts: RepoFacts, branch: str) -> str:
    own = "The checks this repository's own CI requires come on top (the `gate` slot)."
    if facts.verify_check:
        return (
            f"- **required-checks** — `{facts.verify_check}`, which Fleet posts on every pull request here. "
            f"Fleet sets a ruleset on `{branch}` to require it, and the check waits for Fleet's verdict. {own}"
        )
    if facts.verify_check == "":
        return (
            "- **required-checks** — Fleet posts no verify check on this repository, so the repository's own "
            "CI checks are the gate (the `gate` slot)."
        )
    return (
        "- **required-checks** — Fleet's verify check (`Fleet verify`, unless the install named it otherwise). "
        f"It waits for Fleet's verdict. {own}"
    )


def git_workflow(facts: RepoFacts, namespace: str) -> str:
    """The `git-workflow` answer: always written, from the shipped commands' conventions and the facts.

    Every line is either a convention the shipped commands and Fleet's runs use in every repository
    (the branch names, the silent non-merge modes) or a fact from `facts`; an unknown fact names the
    setting that holds it rather than a guess.
    """
    branch = facts.default_branch.strip()
    branch_name = f"`{branch}`" if branch else "the default branch"
    base = f"`origin/{branch}`" if branch else "the default branch on `origin`"
    repo_line = (
        f"- **repository** — `{facts.repository}`, default branch {branch_name}."
        if facts.repository.strip()
        else f"- **repository** — this one, default branch {branch_name}."
    )
    lines = [
        "# git-workflow",
        "",
        "How a change lands in this repository. The branch names are the shipped commands' own.",
        _WRITTEN_BY,
        "",
        "## Answers",
        "",
        repo_line,
        "- **branches** — PRD `agent/prd-NNNN`, with `-<key>` after it when the PRD has an issue · bug "
        "`agent/fix-<key>` · task `agent/task-<key>` · chore `agent/chore-<slug>`. `<key>` is the issue's own "
        "key, lowercased.",
        "- **same-branch** — a branch name never carries a person or a date. A rerun finds the same branch "
        "and continues the same pull request.",
        "- **fleet-branches** — Fleet's planning runs use `agent/shape-<key>`, `agent/design-<key>` and "
        "`agent/plan-<key>`. They merge their own pull request when it changes planning files only.",
        f"- **base** — a freshly fetched {base}. A stale base undoes work that landed in the meantime.",
        f"- **merge** — every change lands by branch and pull request, squashed; never a direct push to "
        f"{branch_name}. The party that wrote a change never certifies it.",
        *_who_merges(facts, namespace),
        _required_checks(facts, branch or "the default branch"),
        "- **done** — a pull request is done at `state: MERGED`, never at green. Watch every one you open until then.",
        "",
        "## Five ways a pull request silently does not merge",
        "",
        "1. **Red checks** — a check failed. `gh pr checks <number>` names it.",
        "2. **Conflict** — the pull request shows no checks at all, not failing ones. GitHub cannot build a "
        "merge commit, so no workflow starts. Rebase, resolve, then push with `--force-with-lease`.",
        "3. **Missing `workflow` scope** — a token without GitHub's `workflow` scope cannot merge a change to "
        "`.github/workflows/**`. Auto-merge then stays off, and nothing says so.",
        "4. **Stale head** — GitHub missed a push, so the pull request still names an older commit. Every "
        "check reads green, and the older commit merges. After each push, compare "
        "`gh api repos/<owner>/<repository>/pulls/<number> --jq .head.sha` with `git ls-remote origin <branch>`.",
        "5. **Removed from the merge queue** — only where the repository uses a merge queue. The pull request "
        "reads clean and green, and nothing is queued. Its timeline names the removal: read the failed "
        "`merge_group` run, fix it, and queue it again.",
        "",
    ]
    return "\n".join(lines)
