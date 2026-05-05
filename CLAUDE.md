# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
pip install -e .
```

Requires Python 3.10+. No tests exist yet — the main way to verify changes is running a task end-to-end.

## CLI commands

```bash
factory setup                                 # one-time engineer onboarding (username, SSH key, GitHub token on worker, labels)
factory ping ares                             # verify SSH to worker
factory run "Add health check" --repo owner/repo   # inline run
factory run tasks/hello-world.yaml           # run from YAML
factory poll owner/repo                      # process all 'factory'-labeled issues in parallel
factory status                               # list all runs
factory status <run_id>                      # detail + eval results for one run
factory attach <run_id>                      # SSH into the live tmux session
factory workers                              # show active sessions + CPU/mem on each worker
```

Environment variables (set in `.env`, loaded automatically):
- `FACTORY_GITHUB_TOKEN` — required for `poll` and PR creation
- `FACTORY_WORKER_USER` — your Unix username on the worker (set by `factory setup`)
- `FACTORY_SSH_IDENTITY` — path to your SSH private key (set by `factory setup`)
- `SLACK_BOT_TOKEN` — optional, enables Slack channel per run

## Architecture

The factory runs locally and orchestrates work on a remote worker machine (ares) over SSH. All agent execution, git operations, and eval commands happen on the remote machine. The local machine just drives the pipeline and stores run state under `runs/`.

**Pipeline flow** (`factory/runner.py`):
1. Create git worktree on worker (`factory/<task-id>-<run-id>` branch)
2. Optionally start a Docker sandbox container
3. Write task prompt + runner script to `.factory/` in the worktree
4. Launch `run.sh` inside a tmux session — SSH returns immediately
5. Poll `.factory/status` until `done`/`failed`/timeout
6. Run eval commands (`cargo test`, `rspec`, etc.)
7. If eval passes, optionally run: untangle → crucible → evaluator agent
8. On any blocking feedback, rebuild the prompt with the failure reason and retry (up to `max_iterations`)

**Key modules:**
- `factory/runner.py` — the full pipeline, single entry point `run_task()`
- `factory/session.py` — tmux session management, writes `.factory/run.sh` and `.factory/task.md` on remote, polls status, Slack bridge
- `factory/evaluator.py` — runs eval commands over SSH, returns `EvalResult` list
- `factory/evaluator_agent.py` — runs `claude -p` on the worker to do AI acceptance review, returns `approved`/`needs_changes` verdict
- `factory/coder.py` — `build_feedback_prompt()` wraps the original prompt with failure context for retry iterations
- `factory/poller.py` — fetches GitHub issues labeled `factory`, calls `run_task()` in parallel threads, opens PRs on pass
- `factory/store.py` — persists `Run` objects and logs to `runs/<run_id>/` on the local machine
- `factory/models.py` — all Pydantic models: `TaskDefinition`, `Run`, `CoderConfig`, `EvalConfig`, etc.
- `factory/config.py` — loads `workers.yaml` and task YAML files
- `factory/ssh.py` — `SSHClient` wraps subprocess ssh calls, all remote commands go through here

**Worker config** (`workers.yaml`):
Defines SSH connection details and available agents per worker. The `shell_init` string is prepended to every remote command to ensure PATH is set correctly (NixOS requires this).

**Task YAML** (`tasks/`):
All pipeline phases are optional — omit `coder` for eval-only tasks, omit `repo` for tasks with no git worktree, omit `crucible`/`untangle`/`evaluator` to skip those phases.

**Agent fallback**: if `rate_limit_markers` are detected in agent output, the runner switches to the next agent in the `agents` list (e.g. claude → codex).

**Run state machine**: `queued → running → evaluating → passed | failed`

## Worker machine (ares)

- Host: `ares.silverpond.com.au`, user set per-engineer via `FACTORY_WORKER_USER` in `.env`
- Requires: `claude` CLI (authenticated), `tmux`, `cargo`, `crucible` (via nix), `untangle` (via cargo)
- Worktrees created under `~/factory/worktrees/`
- NixOS: PATH must include `~/.nix-profile/bin` and `~/.cargo/bin` — handled by `shell_init` in `workers.yaml`
