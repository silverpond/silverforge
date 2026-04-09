"""
GitHub issue poller and parallel run dispatcher.

Usage:
  factory poll --repo owner/repo --template tasks/todo.yaml

For each open issue labeled "factory":
  - Converts the issue into a TaskDefinition using the template YAML
  - Runs coder + eval + evaluator in parallel (one thread per issue)
  - Comments on the issue with the result
  - Opens a PR if the run passed (requires ares to have GitHub SSH access)
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import typer

from factory.config import load_task, load_workers
from factory.github import GitHubClient
from factory.models import CoderConfig, EvalConfig, Run, TaskDefinition
from factory.runner import run_task
from factory.ssh import SSHClient
from factory import store


def issue_to_task(issue: Dict, template: TaskDefinition) -> TaskDefinition:
    """
    Build a TaskDefinition from a GitHub issue + a template task.

    The template provides worker, repo, eval, and evaluator config.
    The issue title + body become the coder prompt.
    """
    number = issue["number"]
    title = issue["title"]
    body = issue.get("body") or ""

    prompt = (
        f"You are working on a Rust project.\n\n"
        f"GitHub Issue #{number}: {title}\n\n"
        f"{body}\n\n"
        f"Fix this issue in the codebase. Make sure all existing tests still pass."
    )

    coder = CoderConfig(
        prompt=prompt,
        max_iterations=template.coder.max_iterations if template.coder else 3,
        session_timeout=template.coder.session_timeout if template.coder else 600,
    )

    return TaskDefinition(
        id=f"issue-{number}",
        name=f"Issue #{number}: {title}",
        worker=template.worker,
        repo=template.repo,
        coder=coder,
        evaluator=template.evaluator,
        untangle=template.untangle,
        crucible=template.crucible,
        eval=template.eval,
    )


def _push_and_pr(
    gh: GitHubClient,
    repo: str,
    run: Run,
    task: TaskDefinition,
    issue: Dict,
    workers_path: Path,
) -> None:
    """Push the worktree branch to GitHub and open a PR."""
    branch = _branch_name(task.id, run.run_id)
    number = issue["number"]

    config = load_workers(workers_path)
    worker = config.workers[task.worker]
    client = SSHClient(
        host=worker.host,
        user=worker.user,
        port=worker.port,
        identity_file=worker.identity_file,
        shell_init=worker.shell_init,
    )

    worktree = run.worktree_path

    # Commit any uncommitted changes Claude left behind
    client.run(
        f"git -C {worktree} add -A && "
        f"git -C {worktree} diff --cached --quiet || "
        f"git -C {worktree} commit -m 'factory: fix for issue #{number}'",
        timeout=30,
    )

    result = client.run(
        f"git -C {worktree} push origin HEAD:{branch}",
        timeout=60,
    )
    if not result.ok:
        typer.echo(f"[issue-{number}] WARNING: git push failed:\n{result.stderr}")
        return

    base_branch = task.repo.branch if task.repo else "master"
    verdict_line = f"\n\n**Evaluator:** {run.evaluator_reason}" if run.evaluator_verdict else ""
    pr_body = (
        f"Fixes #{number}\n\n"
        f"Automated fix by Silverpond Factory (run `{run.run_id}`).{verdict_line}"
    )
    try:
        pr = gh.create_pr(
            repo=repo,
            title=issue["title"],
            body=pr_body,
            head=branch,
            base=base_branch,
        )
        typer.echo(f"[issue-{number}] PR opened: {pr['html_url']}")
    except RuntimeError as exc:
        typer.echo(f"[issue-{number}] WARNING: could not open PR: {exc}")


def _run_one_issue(
    issue: Dict,
    template: TaskDefinition,
    gh: GitHubClient,
    repo: str,
    workers_path: Path,
) -> Tuple[Dict, Run]:
    """Run the factory pipeline for a single issue."""
    number = issue["number"]
    task = issue_to_task(issue, template)

    typer.echo(f"[issue-{number}] starting: {issue['title']}")
    gh.add_label(repo, number, "factory:running")

    try:
        run = run_task(task, workers_path)
    except Exception as exc:
        typer.echo(f"[issue-{number}] ERROR: {exc}")
        gh.comment_on_issue(repo, number, f"❌ Factory run crashed: {exc}")
        gh.remove_label(repo, number, "factory:running")
        raise

    gh.remove_label(repo, number, "factory:running")
    gh.remove_label(repo, number, "factory")

    if run.state.value == "passed":
        verdict_line = ""
        if run.evaluator_verdict:
            verdict_line = f"\n\n**Evaluator:** {run.evaluator_reason}"

        comment = (
            f"✅ Factory run **passed** (run `{run.run_id}`)"
            f"{verdict_line}\n\n"
            f"Branch: `{_branch_name(task.id, run.run_id)}`"
        )
        gh.comment_on_issue(repo, number, comment)
        gh.close_issue(repo, number)
        _push_and_pr(gh, repo, run, task, issue, workers_path)
    else:
        comment = (
            f"❌ Factory run **failed** (run `{run.run_id}`)\n\n"
            f"Notes: {run.notes or 'see run logs'}"
        )
        gh.comment_on_issue(repo, number, comment)

    typer.echo(f"[issue-{number}] done → {run.state}")
    return issue, run


def poll(
    repo: str,
    template: TaskDefinition,
    gh: GitHubClient,
    workers_path: Path = Path("workers.yaml"),
) -> List[Tuple[Dict, Run]]:
    """
    Fetch all 'factory'-labeled issues and run them in parallel.
    Returns a list of (issue, run) pairs.
    """
    issues = gh.get_issues(repo, "factory")

    # Skip issues already marked as running
    pending = [i for i in issues if "factory:running" not in
               [l["name"] for l in i.get("labels", [])]]

    if not pending:
        typer.echo("No pending factory issues found.")
        return []

    typer.echo(f"Found {len(pending)} issue(s) to process — running in parallel...")

    results = []
    with ThreadPoolExecutor(max_workers=len(pending)) as executor:
        futures = {
            executor.submit(
                _run_one_issue, issue, template, gh, repo, workers_path
            ): issue
            for issue in pending
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                issue = futures[future]
                typer.echo(f"[issue-{issue['number']}] unhandled error: {exc}")

    return results


def _branch_name(task_id: str, run_id: str) -> str:
    return f"factory/{task_id}-{run_id}"
