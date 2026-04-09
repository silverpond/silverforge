"""
Coder agent: runs `claude -p "<prompt>"` on the remote machine.

Uses base64 encoding to safely pass arbitrary prompt text through SSH
without shell quoting issues.
"""
from __future__ import annotations

import base64

from factory.ssh import SSHClient, SSHResult


def run_coder(
    client: SSHClient,
    prompt: str,
    working_dir: str,
    timeout: int = 120,
) -> SSHResult:
    """
    Run `claude -p "<prompt>"` in working_dir on the remote host.

    The prompt is base64-encoded before transmission to avoid shell
    escaping issues with quotes, newlines, and special characters.
    """
    encoded = base64.b64encode(prompt.encode()).decode()
    cmd = (
        f'cd {working_dir} && '
        f'claude --dangerously-skip-permissions -p "$(echo \'{encoded}\' | base64 -d)"'
    )
    return client.run(cmd, timeout=timeout)


def build_feedback_prompt(original_prompt: str, failed_output: str) -> str:
    """
    Build a follow-up prompt that includes the original task
    and the failing test output so the coder can fix the issue.
    """
    return (
        f"{original_prompt}\n\n"
        f"The tests failed with the following output:\n"
        f"```\n{failed_output}\n```\n\n"
        f"Please fix the code so all tests pass."
    )
