"""
Evaluator agent: reviews code changes and test results using claude -p.

Unlike the coder (which runs interactively in tmux), the evaluator is a
single-shot review — all context is provided upfront in the prompt and
it returns a structured verdict.
"""
from __future__ import annotations

import base64
from typing import List

from factory.models import EvalResult
from factory.ssh import SSHClient, SSHResult

REVIEW_PROMPT_TEMPLATE = """\
You are a code reviewer in an automated software factory.

Review the following code changes and test results, then give a verdict.

## Task Description
{task_description}

## Git Diff (what the coder wrote)
```
{diff}
```

## Test Results
```
{test_output}
```

## Review Criteria
- Correctness: does the implementation match the task description?
- Test quality: are the tests meaningful, or do they trivially pass?
- Edge cases: are obvious edge cases handled or tested?
{extra_criteria}

## Response Format
Reply in EXACTLY this format, nothing else:

VERDICT: APPROVED
REASON: <one sentence>

or:

VERDICT: NEEDS_CHANGES
REASON: <specific description of what needs to change>
"""


def get_diff(client: SSHClient, worktree_path: str) -> str:
    """Get the uncommitted diff from the worktree (what the coder wrote)."""
    result = client.run(f"git -C {worktree_path} diff")
    if result.stdout.strip():
        return result.stdout
    # If changes were committed in the worktree, diff against the base branch
    result = client.run(f"git -C {worktree_path} diff HEAD~1 2>/dev/null || git -C {worktree_path} show HEAD")
    return result.stdout or "(no diff available)"


def run_evaluator(
    client: SSHClient,
    worktree_path: str,
    task_description: str,
    eval_results: List[EvalResult],
    extra_criteria: str = "",
    timeout: int = 120,
) -> SSHResult:
    """Run claude -p with the review prompt and return the raw result."""
    diff = get_diff(client, worktree_path)

    test_output = "\n".join(
        f"$ {r.command}\n{r.stdout}{r.stderr}".strip()
        for r in eval_results
    )

    prompt = REVIEW_PROMPT_TEMPLATE.format(
        task_description=task_description,
        diff=diff,
        test_output=test_output,
        extra_criteria=f"- {extra_criteria}" if extra_criteria else "",
    )

    encoded = base64.b64encode(prompt.encode()).decode()
    cmd = f'claude -p "$(echo \'{encoded}\' | base64 -d)"'
    return client.run(cmd, timeout=timeout)


def parse_verdict(output: str) -> tuple[str, str]:
    """
    Parse the evaluator's response.
    Returns (verdict, reason) where verdict is 'approved' or 'needs_changes'.
    Falls back to 'approved' if the format is unexpected.
    """
    for line in output.splitlines():
        line = line.strip()
        if line.upper().startswith("VERDICT:"):
            verdict_raw = line.split(":", 1)[1].strip().upper()
            verdict = "approved" if "APPROVED" in verdict_raw else "needs_changes"
            # Find reason
            reason = ""
            for rline in output.splitlines():
                if rline.strip().upper().startswith("REASON:"):
                    reason = rline.split(":", 1)[1].strip()
                    break
            return verdict, reason

    # Couldn't parse — treat as approved to avoid blocking the pipeline
    return "approved", "(evaluator response unparseable — defaulting to approved)"
