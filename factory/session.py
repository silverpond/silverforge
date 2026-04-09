"""
Remote tmux session management for factory runs.

Execution model:
  1. Write task prompt to .factory/task.md on the remote machine
  2. Write .factory/run.sh — launches claude and writes done/failed to .factory/status
  3. Create a tmux session and start run.sh inside it (SSH returns immediately)
  4. Poll .factory/status via short SSH calls until done/failed/timeout
  5. Kill the session when finished

This decouples the SSH connection lifetime from how long Claude runs.
"""
from __future__ import annotations

import base64
import time
from typing import Optional

from factory.ssh import SSHClient


def setup_factory_dir(client: SSHClient, working_dir: str) -> None:
    """Create .factory/ directory and ensure it is gitignored."""
    client.run(f"mkdir -p {working_dir}/.factory")
    client.run(
        f"grep -qxF '.factory/' {working_dir}/.gitignore 2>/dev/null || "
        f"echo '.factory/' >> {working_dir}/.gitignore"
    )


def write_task(client: SSHClient, working_dir: str, prompt: str) -> None:
    """Write the task prompt to .factory/task.md."""
    encoded = base64.b64encode(prompt.encode()).decode()
    client.run(f"echo '{encoded}' | base64 -d > {working_dir}/.factory/task.md")


def write_runner_script(
    client: SSHClient,
    working_dir: str,
    shell_init: Optional[str] = None,
) -> None:
    """
    Write .factory/run.sh — the script that runs inside the tmux session.

    It launches claude, then writes 'done' or 'failed' to .factory/status
    based on the exit code. The factory polls for that file.
    """
    lines = ["#!/bin/bash"]
    if shell_init:
        lines.append(shell_init)
    lines += [
        f"cd {working_dir}",
        "rm -f .factory/status",
        'claude --dangerously-skip-permissions -p "$(cat .factory/task.md)"',
        "if [ $? -eq 0 ]; then",
        "    echo done > .factory/status",
        "else",
        "    echo failed > .factory/status",
        "fi",
    ]
    script = "\n".join(lines) + "\n"
    encoded = base64.b64encode(script.encode()).decode()
    client.run(
        f"echo '{encoded}' | base64 -d > {working_dir}/.factory/run.sh && "
        f"chmod +x {working_dir}/.factory/run.sh"
    )


def start_session(client: SSHClient, session_name: str, working_dir: str) -> bool:
    """Create a tmux session and launch run.sh inside it. Returns True on success."""
    client.run(f"tmux kill-session -t {session_name} 2>/dev/null; true")
    result = client.run(f"tmux new-session -d -s {session_name} -c {working_dir}")
    if not result.ok:
        return False
    result = client.run(
        f"tmux send-keys -t {session_name} "
        f"'bash {working_dir}/.factory/run.sh' Enter"
    )
    return result.ok


def wait_for_status(
    client: SSHClient,
    working_dir: str,
    timeout: int = 600,
    poll_interval: int = 5,
) -> str:
    """
    Poll .factory/status until it contains 'done' or 'failed'.
    Returns 'done', 'failed', or 'timeout'.
    """
    elapsed = 0
    while elapsed < timeout:
        result = client.run(f"cat {working_dir}/.factory/status 2>/dev/null")
        status = result.stdout.strip()
        if status in ("done", "failed"):
            return status
        time.sleep(poll_interval)
        elapsed += poll_interval
    return "timeout"


def kill_session(client: SSHClient, session_name: str) -> None:
    """Kill the tmux session."""
    client.run(f"tmux kill-session -t {session_name} 2>/dev/null; true")


def session_name_for_run(run_id: str) -> str:
    return f"factory-{run_id}"
