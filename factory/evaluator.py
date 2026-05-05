"""
Evaluator: runs a sequence of remote commands and collects results.

Evaluation is intentionally sequential and stops on first failure,
since later commands (e.g. cargo test) are meaningless if the build fails.
"""
from __future__ import annotations

import time
from typing import List, Optional

from factory.models import EvalConfig, EvalResult
from factory.ssh import SSHClient


def run_eval(
    client: SSHClient,
    config: EvalConfig,
    working_dir: Optional[str] = None,
) -> List[EvalResult]:
    """
    Execute each command in config.commands on the remote host.
    Stops on first non-zero exit code.
    working_dir overrides config.working_dir when provided (e.g. for worktrees).
    """
    wd = working_dir or config.working_dir
    results: List[EvalResult] = []

    for cmd in config.commands:
        remote_cmd = f"cd {wd} && {cmd}"
        start = time.monotonic()

        try:
            result = client.run(remote_cmd, timeout=config.timeout)
        except Exception as exc:
            results.append(EvalResult(
                command=cmd,
                exit_code=-1,
                stdout="",
                stderr=str(exc),
                duration=time.monotonic() - start,
            ))
            break

        results.append(EvalResult(
            command=cmd,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=time.monotonic() - start,
        ))

        if result.exit_code != 0:
            break  # no point running further steps

    return results


def eval_passed(results: List[EvalResult]) -> bool:
    return not results or all(r.exit_code == 0 for r in results)
