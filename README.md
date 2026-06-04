# Silverforge

An automated software factory that runs Claude AI agents on a remote worker machine to implement tasks, reviews the code with Crucible, and opens pull requests — all from a single command.

---

## Two ways to use it

### 1. One-off task

```bash
factory run "Add a health check endpoint that returns {\"status\": \"ok\"}" --repo owner/my-repo
```

Claude runs on the worker, implements the task, Crucible reviews the result, and if anything needs fixing it retries automatically. A PR is opened on pass.

### 2. Batch from GitHub issues

Label issues with `factory`, then:

```bash
factory poll owner/my-repo
```

Every labeled issue gets picked up in parallel — each becomes a task for Claude to fix, with a PR opened on success.

---

## Prerequisites

Before you start, ask your admin to set up:

- **SSH access to ares** — your public key needs to be added to the worker machine
- **Claude authenticated on ares** — already done once for the team, nothing to do here

---

## Setup

There are two ways to install: via Nix (recommended, no Python environment needed) or via pip.

### Option A: Nix install (recommended)

```bash
nix profile install github:silverpond/silverforge/master
factory setup
```

The setup wizard asks for your worker username, SSH key, GitHub token, and Slack tokens — everything gets saved to `~/.config/factory/.env` automatically.

> **PATH note:** If `which factory` doesn't point to `~/.nix-profile/bin/factory`, add `export PATH="$HOME/.nix-profile/bin:$PATH"` to your `~/.zshrc`.

---

### Option B: pip install (for development)

```bash
git clone https://github.com/silverpond/silverforge
cd silverforge
pip install -e .
cp .env.example .env
```

Then edit `.env` and add:

| Variable                  | Where to get it                                                                                            |
| ------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `FACTORY_GITHUB_TOKEN`    | Create at https://github.com/settings/tokens — scopes: `repo`, `issues`, `pull_requests`, `workflows`      |
| `FACTORY_GITHUB_TOKEN_CMD` | Optional. A command that prints a fresh token to stdout, run on demand (takes precedence over `FACTORY_GITHUB_TOKEN`). Use it to drive short-lived GitHub App installation tokens. |
| `SLACK_BOT_TOKEN`         | Ask your admin — from the shared Slack app at api.slack.com/apps                                           |
| `SLACK_APP_TOKEN`         | Ask your admin — same Slack app, under "App-Level Tokens"                                                  |
| `SLACK_DEFAULT_REVIEWERS` | Comma-separated Slack member IDs to invite to each run's channel (find yours at slack.com/account/profile) |

Then run:

```bash
factory setup
```

> **Note:** `workers.yaml` is already configured for the Silverpond ares machine. Your personal SSH key and username stay in `.env` (gitignored) — not in the repo.

### Worker machine requirements

- `claude` CLI installed and authenticated
- `tmux`
- `crucible` — `nix profile install github:jonochang/crucible` (for code review)
- `untangle` — `cargo install untangle` (Rust projects only)

---

## Running tasks

### Inline

```bash
# Basic
factory run "Fix the login bug" --repo owner/my-repo

# With eval commands (run after the agent finishes each iteration)
factory run "Add input validation" --repo owner/my-repo --eval "pytest" --eval "ruff check ."

# Override model and effort (haiku + low is cheapest)
factory run "Refactor the auth module" --repo owner/my-repo --model haiku --effort low

# Use codex as a fallback if claude hits a rate limit
factory run "Add input validation" --repo owner/my-repo --agent claude --agent codex

# Control how many Crucible review rounds run (0 = skip Crucible)
factory run "Add a loading spinner" --repo owner/my-repo --crucible-rounds 2

# Control which model crucible uses
factory run "Add a loading spinner" --repo owner/my-repo --crucible-rounds 1 --crucible-model claude-haiku-4-5-20251001

# If you're inside a git repo, --repo is inferred automatically
cd ~/projects/my-repo
factory run "Add a health check endpoint"
```

Without `--eval`, Crucible is the only quality gate — it reviews the diff and sends feedback to Claude if it finds critical issues.

### Poll GitHub issues

```bash
# Basic — picks up all issues labeled 'factory'
factory poll owner/my-repo

# With eval commands
factory poll owner/my-repo --eval "bundle exec rails test"

# Override model/effort for all issues in this poll
factory poll owner/my-repo --model haiku --effort low

# Use codex as a fallback if claude hits a rate limit
factory poll owner/my-repo --agent claude --agent codex

# Control crucible rounds
factory poll owner/my-repo --crucible-rounds 2

# Cap how many issues run in parallel (default: worker slot count)
factory poll owner/my-repo --max-concurrency 2
```

Individual issues can override model/effort via labels:

- `factory:model:opus` — run that issue with Opus
- `factory:effort:low` — run with low effort

---

## Slack integration

If `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` are set, each run gets a Slack thread with live status updates.

### Mid-session messaging

Send messages to the running Claude agent directly from Slack. Start the bridge listener on your local machine:

```bash
factory slack-listen
```

Any message posted in the factory Slack channel that starts with `run:` launches a new task:

```
run: Add a health check endpoint --repo owner/my-repo
run: Fix the login bug --repo owner/my-repo --model haiku --effort low --crucible-rounds 2
```

Messages posted in an existing run's thread are forwarded to the Claude session on the worker — useful for giving the agent mid-task guidance.

### Pause-and-review

When Slack is configured, pause-and-review is on by default. After the agent finishes, a prompt appears in the run's Slack thread asking you to approve before the PR is opened. Reply `approve` (or `yes`) to open it, or `reject` to skip. If no reply arrives within 5 minutes, the PR is opened automatically.

---

## Monitoring

The terminal frees up immediately after launch. Use these to check on runs:

```bash
factory status                  # list all runs (includes PR URL)
factory status <run_id>         # detail for one run
factory attach <run_id>         # attach to the live tmux session on the worker
factory logs <run_id>           # tail agent output
factory kill <run_id>           # stop a run
factory workers                 # show active sessions + CPU/mem on each worker
```

---

## Maintenance

```bash
# Remove worktrees on the worker for finished runs
factory cleanup                 # remove all dead worktrees on ares
factory cleanup --dry-run       # preview first

# Remove local run history
factory runs-clean              # remove finished runs older than 7 days
factory runs-clean --days 1     # keep only last day
factory runs-clean --all        # remove all finished runs
factory runs-clean --dry-run    # preview first
```

---

## Advanced: task YAML files

For repeatable or complex tasks, define them in a YAML file:

```bash
factory run tasks/my-task.yaml                              # run from YAML
factory poll owner/my-repo --template tasks/my-task.yaml   # poll with YAML template
```

YAML files let you configure the full pipeline — eval commands, crucible rounds, untangle, evaluator, Slack reviewers, service ports, and more. See `tasks/todo.yaml` for a complete example.

---

## Pipeline

```
worktree → agent → crucible (N rounds) → evaluator → pause-and-review → PR
```

Any stage that fails sends feedback back to the agent for another iteration (up to `max_iterations`, default 3). Stages not configured are skipped.
