"""
Background watcher process — spawned by spawn_watcher() to run watch_task().

Usage (via python -m):
    python -m factory._watcher <run_id> --task <task.yaml> --workers <workers.yaml>
                                [--repo owner/repo] [--issue N]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(prog="factory._watcher")
    parser.add_argument("run_id", help="Run ID to watch")
    parser.add_argument("--task", required=True, help="Path to task YAML")
    parser.add_argument("--workers", default="workers.yaml", help="Path to workers.yaml")
    parser.add_argument("--repo", default=None, help="GitHub repo (owner/repo) for PR creation")
    parser.add_argument("--issue", type=int, default=None, help="GitHub issue number")
    args = parser.parse_args()

    from factory.config import load_task
    from factory.runner import watch_task

    try:
        task = load_task(Path(args.task))
    except Exception as exc:
        print(f"[watcher] ERROR loading task from {args.task}: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        watch_task(
            args.run_id,
            task,
            Path(args.workers),
            repo=args.repo,
            issue_number=args.issue,
        )
    except Exception as exc:
        print(f"[watcher] FATAL: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
