"""
Run orchestrator.

A run goes through these phases:
  queued -> running (repo setup) -> evaluating -> passed | failed

The agent step (AoE) is currently skipped with a clear log message.
Once AoE integration is ready, insert it between repo setup and evaluation.
"""
from __future__ import annotations

from pathlib import Path

import typer

from factory import evaluator, session as sess, store
from factory.coder import build_feedback_prompt
from factory.evaluator_agent import parse_verdict, run_evaluator
from factory.config import WorkerConfig, load_workers
from factory.models import Run, RunState, TaskDefinition, UntangleConfig, CrucibleConfig
from factory.ssh import SSHClient


def run_task(task: TaskDefinition, workers_path: Path = Path("workers.yaml")) -> Run:
    config = load_workers(workers_path)
    worker: WorkerConfig | None = config.workers.get(task.worker)
    if worker is None:
        raise ValueError(f"Worker '{task.worker}' not found in {workers_path}")

    run = Run(task_id=task.id, task_name=task.name, worker=task.worker)
    store.save_run(run)
    _log(run.run_id, f"created  task={task.id!r} worker={task.worker}")

    client = SSHClient(host=worker.host, user=worker.user, port=worker.port,
                       identity_file=worker.identity_file, shell_init=worker.shell_init)

    run.state = RunState.running
    store.save_run(run)

    # ── Phase 1: worktree setup (optional) ──────────────────────────────────
    if task.repo is not None:
        _log(run.run_id, "state=running  (worktree setup)")
        try:
            worktree_path = _create_run_worktree(client, task, run.run_id, worker)
            run.worktree_path = worktree_path
            store.save_run(run)
            _log(run.run_id, f"  worktree={worktree_path}")
        except RuntimeError as exc:
            run.state = RunState.failed
            run.notes = str(exc)
            store.save_run(run)
            _log(run.run_id, f"FAILED during worktree setup: {exc}")
            return run

    # working_dir: use the per-run worktree if one was created, else task default
    working_dir = run.worktree_path or task.eval.working_dir

    # ── Phase 2: coder → eval loop (tmux-backed) ────────────────────────────
    if task.coder is not None:
        session_name = sess.session_name_for_run(run.run_id)
        prompt = task.coder.prompt

        for iteration in range(1, task.coder.max_iterations + 1):
            _log(run.run_id, f"state=running  (coder iteration {iteration}/{task.coder.max_iterations})")

            # Write task and runner script to remote
            sess.setup_factory_dir(client, working_dir)
            sess.write_task(client, working_dir, prompt)
            sess.write_runner_script(client, working_dir, shell_init=worker.shell_init)

            # Launch in tmux — SSH returns immediately
            if not sess.start_session(client, session_name, working_dir):
                run.state = RunState.failed
                run.notes = "Failed to start tmux session"
                store.save_run(run)
                _log(run.run_id, "  ERROR: could not start tmux session")
                return run

            _log(run.run_id, f"  session={session_name} running, polling for completion...")

            # Poll until Claude writes .factory/status
            agent_status = sess.wait_for_status(
                client, working_dir,
                timeout=task.coder.session_timeout,
                poll_interval=5,
            )
            sess.kill_session(client, session_name)
            _log(run.run_id, f"  agent status={agent_status}")

            if agent_status == "timeout":
                run.state = RunState.failed
                run.notes = f"Coder timed out after {task.coder.session_timeout}s"
                store.save_run(run)
                return run

            # Evaluate
            run.state = RunState.evaluating
            store.save_run(run)
            _log(run.run_id, f"state=evaluating  (iteration {iteration})")

            results = evaluator.run_eval(client, task.eval, working_dir=working_dir)
            run.eval_results = results
            _save_eval_logs(run.run_id, results, suffix=f"_iter{iteration}")
            _print_eval_results(run.run_id, results)

            if evaluator.eval_passed(results):
                # ── Untangle structural check (optional) ─────────────────────
                if task.untangle is not None and run.worktree_path:
                    _log(run.run_id, "  running untangle diff...")
                    base_branch = task.repo.branch if task.repo else "master"
                    branch = f"factory/{task.id}-{run.run_id}"
                    untangle_feedback = _run_untangle(
                        client, working_dir, base_branch, branch, task.untangle
                    )
                    if untangle_feedback:
                        store.save_log(run.run_id, f"untangle_iter{iteration}.json", untangle_feedback)
                        _log(run.run_id, f"  untangle blocked: {untangle_feedback[:120]}...")
                        if iteration < task.coder.max_iterations:
                            prompt = build_feedback_prompt(
                                task.coder.prompt,
                                f"Structural analysis (untangle) found issues:\n{untangle_feedback}",
                            )
                            _log(run.run_id, "  sending untangle feedback to coder")
                            store.save_run(run)
                            continue
                        run.state = RunState.failed
                        run.notes = "Untangle structural check failed after max iterations"
                        store.save_run(run)
                        return run
                    _log(run.run_id, "  untangle passed")

                # ── Crucible multi-agent review (optional) ───────────────────
                if task.crucible is not None and run.worktree_path:
                    _log(run.run_id, "  running crucible review...")
                    base_branch = task.repo.branch if task.repo else "master"
                    crucible_feedback = _run_crucible(
                        client, working_dir, base_branch, task.crucible
                    )
                    store.save_log(run.run_id, f"crucible_iter{iteration}.json", crucible_feedback or "")
                    if crucible_feedback:
                        _log(run.run_id, f"  crucible blocked: {crucible_feedback[:120]}...")
                        if iteration < task.coder.max_iterations:
                            prompt = build_feedback_prompt(
                                task.coder.prompt,
                                f"Code review (crucible) found critical issues:\n{crucible_feedback}",
                            )
                            _log(run.run_id, "  sending crucible feedback to coder")
                            store.save_run(run)
                            continue
                        run.state = RunState.failed
                        run.notes = "Crucible review blocked after max iterations"
                        store.save_run(run)
                        return run
                    _log(run.run_id, "  crucible passed")

                # ── Evaluator agent (optional) ───────────────────────────────
                if task.evaluator is not None and run.worktree_path:
                    _log(run.run_id, "  running evaluator agent...")
                    ev_result = run_evaluator(
                        client,
                        worktree_path=working_dir,
                        task_description=task.coder.prompt,
                        eval_results=results,
                        extra_criteria=task.evaluator.criteria or "",
                        timeout=task.evaluator.timeout,
                    )
                    store.save_log(run.run_id, f"evaluator_iter{iteration}.stdout", ev_result.stdout)
                    verdict, reason = parse_verdict(ev_result.stdout)
                    run.evaluator_verdict = verdict
                    run.evaluator_reason = reason
                    _log(run.run_id, f"  evaluator verdict={verdict}: {reason}")

                    if verdict == "needs_changes" and iteration < task.coder.max_iterations:
                        prompt = build_feedback_prompt(task.coder.prompt, reason)
                        _log(run.run_id, "  evaluator requested changes — sending feedback to coder")
                        store.save_run(run)
                        continue

                run.state = RunState.passed
                store.save_run(run)
                _log(run.run_id, f"state=passed  (iteration {iteration})")
                return run

            if iteration < task.coder.max_iterations:
                failed_output = "\n".join(
                    r.stdout + r.stderr for r in results if r.exit_code != 0
                )
                prompt = build_feedback_prompt(task.coder.prompt, failed_output)
                _log(run.run_id, "  eval failed — sending feedback to coder")

        run.state = RunState.failed
        store.save_run(run)
        _log(run.run_id, f"state=failed  (exhausted {task.coder.max_iterations} iterations)")
        return run

    # ── Phase 3: eval-only (no coder) ────────────────────────────────────────
    run.state = RunState.evaluating
    store.save_run(run)
    _log(run.run_id, "state=evaluating")

    results = evaluator.run_eval(client, task.eval, working_dir=working_dir)
    run.eval_results = results
    _save_eval_logs(run.run_id, results)
    _print_eval_results(run.run_id, results)

    run.state = RunState.passed if evaluator.eval_passed(results) else RunState.failed
    store.save_run(run)
    _log(run.run_id, f"state={run.state}")
    return run


def _create_run_worktree(
    client: SSHClient,
    task: TaskDefinition,
    run_id: str,
    worker: "WorkerConfig",
) -> str:
    """
    Create a git worktree for this run and return its path.

    Each run gets its own branch (factory/<task-id>-<run-id>) so Claude's
    changes are isolated. The base repo is never modified directly.
    """
    base_path = task.repo.path
    worktree_base = worker.default_worktree_base
    worktree_path = f"{worktree_base}/{task.id}-{run_id}"
    branch = f"factory/{task.id}-{run_id}"

    # Clone base repo if url provided and path doesn't exist
    if task.repo.url:
        check = client.run(f"test -d {base_path}/.git && echo exists || echo missing")
        if "missing" in check.stdout:
            _log(run_id, f"  cloning {task.repo.url} -> {base_path}")
            result = client.run(
                f"git clone {task.repo.url} {base_path}", timeout=300
            )
            if not result.ok:
                raise RuntimeError(f"git clone failed:\n{result.stderr}")

    # Ensure worktrees directory exists
    client.run(f"mkdir -p {worktree_base}")

    # Create worktree on a fresh branch from the base branch
    _log(run_id, f"  branch={branch}")
    result = client.run(
        f"git -C {base_path} worktree add {worktree_path} -b {branch} {task.repo.branch}",
        timeout=30,
    )
    if not result.ok:
        raise RuntimeError(f"git worktree add failed:\n{result.stderr}")

    return worktree_path


def _save_eval_logs(run_id: str, results: list, suffix: str = "") -> None:
    for r in results:
        safe = r.command.replace(" ", "_").replace("/", "_")
        store.save_log(run_id, f"eval_{safe}{suffix}.stdout", r.stdout)
        store.save_log(run_id, f"eval_{safe}{suffix}.stderr", r.stderr)


def _print_eval_results(run_id: str, results: list) -> None:
    for r in results:
        status = "PASS" if r.exit_code == 0 else "FAIL"
        _log(run_id, f"  [{status}] {r.command!r}  ({r.duration:.1f}s)")


def _run_untangle(
    client: SSHClient,
    working_dir: str,
    base_branch: str,
    head_branch: str,
    config: "UntangleConfig",
) -> str:
    """
    Run `untangle diff` and return a non-empty string if it blocks, else "".
    """
    cmd = (
        f"cd {working_dir} &&"
        f" untangle diff"
        f" --base {base_branch}"
        f" --head {head_branch}"
        f" --lang {config.lang}"
        f" --fail-on {config.fail_on}"
        f" --format json"
    )
    result = client.run(cmd, timeout=config.timeout)
    # untangle exits 1 when policy is violated
    if result.exit_code == 0:
        return ""
    # Return the JSON output so it can be fed back to the coder
    return result.stdout or result.stderr


def _run_crucible(
    client: SSHClient,
    working_dir: str,
    base_branch: str,
    config: "CrucibleConfig",
) -> str:
    """
    Run `crucible review --branch <base> --json` from the worktree.
    Returns non-empty string of critical findings if it blocks, else "".
    """
    import json as _json

    cmd = f"cd {working_dir} && crucible review --branch {base_branch} --json"
    result = client.run(cmd, timeout=config.timeout)

    if not result.stdout.strip():
        return ""

    try:
        data = _json.loads(result.stdout)
    except Exception:
        # If JSON parse fails, treat as non-blocking (don't break the pipeline)
        return ""

    verdict = data.get("verdict", "Pass")
    if verdict == "Pass" or verdict == "Warn":
        return ""

    # Block verdict — extract critical findings as feedback
    critical = [
        f"[{f['severity']}] {f['file']}:{f.get('line_start','')} {f['title']}: {f['description']}"
        for f in data.get("findings", [])
        if f.get("severity") == "Critical"
    ]
    return "\n".join(critical) if critical else ""


def _log(run_id: str, msg: str) -> None:
    typer.echo(f"[{run_id}] {msg}")
