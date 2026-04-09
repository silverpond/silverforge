# Silverpond Factory

An automated software factory that polls GitHub issues, fixes them using Claude AI agents on a remote worker machine, and opens pull requests.

## How it works

1. You label a GitHub issue with `factory`
2. Run `factory poll` — the factory picks up all labeled issues in parallel
3. For each issue, on the remote worker:
   - Creates an isolated git worktree
   - Runs a Claude coder agent to fix the issue
   - Evaluates with `cargo test` + `cargo clippy`
   - Runs [untangle](https://github.com/jonochang/untangle) for structural analysis
   - Runs [crucible](https://github.com/jonochang/crucible) for multi-agent code review
   - Runs an evaluator agent to verify the fix matches the issue
4. On pass: commits, pushes branch, opens PR, closes issue

## Requirements

### Local machine

- Python 3.10+
- `gh` CLI (authenticated)
- SSH access to a worker machine

### Worker machine

- Claude CLI (`claude`) installed and authenticated
- `cargo` / Rust toolchain
- `untangle` — `cargo install untangle`
- `crucible` — `nix profile install github:jonochang/crucible`
- `tmux`

## Setup

### 1. Install the factory CLI

```bash
git clone https://github.com/silverpond/silverpond-factory
cd silverpond-factory
pip install -e .
```

### 2. Configure your worker

Edit `workers.yaml`:

```yaml
workers:
  ares: # name for your worker
    host: your-worker.example.com # change this
    user: youruser # change this
    port: 22
    identity_file: ~/.ssh/id_ed21125 # path to your SSH private key
    aoe_available: true
    default_worktree_base: ~/factory/worktrees
    shell_init: "export PATH=$HOME/.nix-profile/bin:$HOME/.cargo/bin:$PATH"
```

### 3. Set your GitHub token

```bash
export FACTORY_GITHUB_TOKEN=ghp_your_token_here
```

### 4. Test connectivity

```bash
factory ping ares
```

## Usage

### Run a single task

```bash
factory run tasks/hello-world.yaml
```

### Poll GitHub issues

```bash
factory poll owner/repo --template tasks/todo.yaml
```

Any open issue labeled `factory` will be picked up and processed in parallel.

### Check run status

```bash
factory status
factory status <run_id>
```

### Attach to a live coder session

```bash
factory attach <run_id>
```

## Task template

Tasks are defined in YAML. See `tasks/todo.yaml` for a full example:

```yaml
id: my-task
name: "My Task"
worker: ares # must match a worker in workers.yaml

repo:
  path: ~/projects/my-repo
  branch: master
  url: https://github.com/owner/repo # cloned if path doesn't exist

coder:
  prompt: "" # filled in from GitHub issue when polling
  max_iterations: 3
  session_timeout: 600

untangle:
  lang: rust
  fail_on: fanout-increase,new-scc
  timeout: 30

crucible:
  block_on: Critical
  timeout: 300

evaluator:
  criteria: |
    The fix must be correct and tests must cover the new behaviour.
  timeout: 120

eval:
  commands:
    - cargo test
    - cargo clippy -- -D warnings
  working_dir: ~/projects/my-repo
  timeout: 120
```

## GitHub setup

Create the required labels in your repo:

```bash
gh label create factory --repo owner/repo --color 0075ca
gh label create factory:running --repo owner/repo --color e4e669
```

Then label any issue you want the factory to fix:

```bash
gh issue edit <number> --repo owner/repo --add-label factory
```
