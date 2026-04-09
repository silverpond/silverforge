"""
Silverpond Factory CLI.

Commands:
  ping   [worker]           — verify SSH connectivity
  run    <task.yaml>        — execute a task end-to-end
  status [run_id]           — show run(s) status
  eval   <run_id>           — re-run eval commands for an existing run
  attach <run_id>           — SSH into the remote tmux session for a run
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from factory import store
from factory.config import load_task, load_workers
from factory.models import RunState
from factory.runner import run_task
from factory.ssh import SSHClient

app = typer.Typer(
    name="factory",
    help="Silverpond Factory — remote worker orchestrator",
    no_args_is_help=True,
)
console = Console()

_WORKERS_OPT = typer.Option(Path("workers.yaml"), "--workers", "-w", help="Path to workers.yaml")

_STATE_STYLE: dict[RunState, str] = {
    RunState.queued:        "white",
    RunState.running:       "yellow",
    RunState.waiting_input: "magenta",
    RunState.evaluating:    "cyan",
    RunState.passed:        "green",
    RunState.failed:        "red",
    RunState.human_review:  "bright_red",
}


def _client(worker_name: str, workers_path: Path) -> SSHClient:
    config = load_workers(workers_path)
    if worker_name not in config.workers:
        typer.echo(f"Worker '{worker_name}' not found in {workers_path}", err=True)
        raise typer.Exit(1)
    w = config.workers[worker_name]
    return SSHClient(host=w.host, user=w.user, port=w.port, identity_file=w.identity_file, shell_init=w.shell_init)


# ── ping ─────────────────────────────────────────────────────────────────────

@app.command()
def ping(
    worker: str = typer.Argument("ares", help="Worker name from workers.yaml"),
    workers: Path = _WORKERS_OPT,
) -> None:
    """Verify SSH connectivity to a worker machine."""
    c = _client(worker, workers)
    typer.echo(f"Pinging {worker} ({c.user}@{c.host}:{c.port})...")
    if c.ping():
        console.print(f"  [green]OK[/green] — {worker} is reachable")
    else:
        console.print(f"  [red]UNREACHABLE[/red] — {worker} did not respond")
        raise typer.Exit(1)


# ── run ──────────────────────────────────────────────────────────────────────

@app.command(name="run")
def run_cmd(
    task_file: Path = typer.Argument(..., help="Path to task YAML file"),
    workers: Path = _WORKERS_OPT,
) -> None:
    """Run a task on a remote worker."""
    if not task_file.exists():
        typer.echo(f"Task file not found: {task_file}", err=True)
        raise typer.Exit(1)

    task = load_task(task_file)
    typer.echo(f"Task: {task.name!r}  id={task.id}  worker={task.worker}")

    run = run_task(task, workers)

    color = _STATE_STYLE.get(run.state, "white")
    console.print(f"\nRun [bold]{run.run_id}[/bold] finished: [{color}]{run.state}[/{color}]")
    if run.notes:
        typer.echo(f"Notes: {run.notes}")


# ── status ───────────────────────────────────────────────────────────────────

@app.command()
def status(
    run_id: Optional[str] = typer.Argument(None, help="Run ID, or omit to list all runs"),
) -> None:
    """Show run status. Lists all runs if no run_id is given."""
    runs = [store.load_run(run_id)] if run_id else store.list_runs()
    runs = [r for r in runs if r is not None]

    if not runs:
        typer.echo("No runs found.")
        return

    table = Table(title="Factory Runs", show_lines=False)
    table.add_column("Run ID",  style="cyan",  no_wrap=True)
    table.add_column("Task")
    table.add_column("Worker",  style="dim")
    table.add_column("State",   no_wrap=True)
    table.add_column("Created", style="dim", no_wrap=True)

    for r in runs:
        color = _STATE_STYLE.get(r.state, "white")
        table.add_row(
            r.run_id,
            r.task_name,
            r.worker,
            f"[{color}]{r.state}[/{color}]",
            r.created_at[:19],
        )

    console.print(table)

    # If a single run was requested, show eval detail too
    if run_id and runs:
        r = runs[0]
        if r.eval_results:
            typer.echo("\nEval results:")
            for er in r.eval_results:
                mark = "✓" if er.exit_code == 0 else "✗"
                typer.echo(f"  {mark} [{er.exit_code}] {er.command!r}  ({er.duration:.1f}s)")


# ── eval ─────────────────────────────────────────────────────────────────────

@app.command(name="eval")
def eval_cmd(
    run_id: str = typer.Argument(..., help="Run ID to re-evaluate"),
    task_file: Path = typer.Option(..., "--task", "-t", help="Task YAML (needed for eval config)"),
    workers: Path = _WORKERS_OPT,
) -> None:
    """Re-run evaluation commands for an existing run."""
    from factory.evaluator import eval_passed, run_eval

    r = store.load_run(run_id)
    if r is None:
        typer.echo(f"Run {run_id!r} not found", err=True)
        raise typer.Exit(1)

    task = load_task(task_file)
    c = _client(r.worker, workers)

    typer.echo(f"Re-evaluating run {run_id}...")
    store.update_state(run_id, RunState.evaluating)

    results = run_eval(c, task.eval)
    r = store.load_run(run_id)
    assert r is not None
    r.eval_results = results

    for res in results:
        safe = res.command.replace(" ", "_").replace("/", "_")
        store.save_log(run_id, f"eval_{safe}.stdout", res.stdout)
        store.save_log(run_id, f"eval_{safe}.stderr", res.stderr)
        mark = "PASS" if res.exit_code == 0 else "FAIL"
        typer.echo(f"  [{mark}] {res.command!r}  ({res.duration:.1f}s)")

    r.state = RunState.passed if eval_passed(results) else RunState.failed
    store.save_run(r)

    color = _STATE_STYLE.get(r.state, "white")
    console.print(f"Eval complete: [{color}]{r.state}[/{color}]")


# ── attach ───────────────────────────────────────────────────────────────────

@app.command()
def attach(
    run_id: str = typer.Argument(..., help="Run ID whose tmux session to attach"),
    workers: Path = _WORKERS_OPT,
) -> None:
    """
    SSH into the remote machine and attach to the tmux session for a run.

    Creates a new session if one doesn't already exist.
    """
    r = store.load_run(run_id)
    if r is None:
        typer.echo(f"Run {run_id!r} not found", err=True)
        raise typer.Exit(1)

    config = load_workers(workers)
    if r.worker not in config.workers:
        typer.echo(f"Worker '{r.worker}' not in {workers}", err=True)
        raise typer.Exit(1)

    w = config.workers[r.worker]
    session = f"factory-{run_id}"

    ssh_cmd = ["ssh", "-t", "-p", str(w.port)]
    if w.identity_file:
        import os
        ssh_cmd += ["-i", os.path.expanduser(w.identity_file)]
    ssh_cmd += [
        f"{w.user}@{w.host}",
        f"tmux attach-session -t {session} 2>/dev/null || tmux new-session -s {session}",
    ]
    typer.echo(f"Attaching to {w.host} → tmux session '{session}'")
    typer.echo("(Ctrl-b d to detach)")
    subprocess.run(ssh_cmd)


# ── poll ─────────────────────────────────────────────────────────────────────

@app.command()
def poll(
    repo: str = typer.Argument(..., help="GitHub repo in owner/repo format"),
    template: Path = typer.Option(..., "--template", "-t", help="Task YAML template"),
    workers: Path = _WORKERS_OPT,
) -> None:
    """
    Fetch open GitHub issues labeled 'factory' and run them in parallel.

    Requires FACTORY_GITHUB_TOKEN environment variable to be set.
    """
    from factory.github import GitHubClient, get_token
    from factory.poller import poll as run_poll

    if not template.exists():
        typer.echo(f"Template not found: {template}", err=True)
        raise typer.Exit(1)

    try:
        token = get_token()
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    task_template = load_task(template)
    gh = GitHubClient(token)

    typer.echo(f"Polling {repo} for issues labeled 'factory'...")
    results = run_poll(repo, task_template, gh, workers)

    if results:
        typer.echo(f"\n{len(results)} issue(s) processed:")
        for issue, run in results:
            color = _STATE_STYLE.get(run.state, "white")
            console.print(
                f"  #{issue['number']} {issue['title']} → "
                f"[{color}]{run.state}[/{color}] (run {run.run_id})"
            )


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
