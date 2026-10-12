"""The README's test command must be the command CI actually runs (TRM-25).

`README.md` tells the reader "This is the exact command CI runs (see
`.github/workflows/ci.yml`)". Nothing enforced that sentence, so it drifted: the README
showed `pytest` while the workflow's last step ran `pytest -q`. This test holds the two
together so the claim cannot go false again.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
CI = ROOT / ".github" / "workflows" / "ci.yml"


def _readme_test_command() -> str:
    """The command in the bash block under the README's '## Running the tests'."""
    section = README.read_text().split("## Running the tests", 1)[1].split("## ", 1)[0]
    block = re.search(r"```bash\n(.*?)```", section, re.DOTALL)
    assert block is not None, "README has no bash block under '## Running the tests'"
    return block.group(1).strip()


def _ci_test_command() -> str:
    """The last `run:` step of the CI workflow — the one that runs the suite."""
    runs = re.findall(r"^[ \t]*-[ \t]*run:[ \t]*(.+)$", CI.read_text(), re.MULTILINE)
    assert runs, "CI workflow has no `run:` step"
    return runs[-1].strip()


def test_readme_states_the_exact_command_ci_runs() -> None:
    assert _readme_test_command() == _ci_test_command()
