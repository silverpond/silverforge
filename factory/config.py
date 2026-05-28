"""
Configuration loading — workers.yaml and task YAML files.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

import yaml
from pydantic import BaseModel

from factory.models import TaskDefinition


class WorkerConfig(BaseModel):
    host: str
    user: str = "root"
    port: int = 22
    identity_file: Optional[str] = None  # path to SSH private key, e.g. ~/.ssh/id_ed25519
    shell_init: Optional[str] = None    # command prepended to every remote command, e.g. "source /etc/profile"
    aoe_available: bool = False
    default_worktree_base: str = "~/factory/worktrees"
    slots: int = 1           # max concurrent port-using runs on this worker
    slot_port_base: int = 12000  # slot N gets port slot_port_base + N
    model: str = "sonnet"    # default claude model alias for all runs on this worker
    effort: str = "medium"   # default claude effort level for all runs on this worker
    # Map of agent name -> command on this worker, e.g. {"claude": "claude", "codex": "codex"}
    agents: Dict[str, str] = {"claude": "claude"}


class GlobalConfig(BaseModel):
    workers: Dict[str, WorkerConfig]


_WORKERS_SEARCH_PATHS = [
    Path("workers.yaml"),
    Path.home() / ".config" / "factory" / "workers.yaml",
]


def resolve_workers_path(path: Optional[Path] = None) -> Path:
    """Return the resolved path to workers.yaml, searching default locations if path is None."""
    if path is not None:
        return path
    for candidate in _WORKERS_SEARCH_PATHS:
        if candidate.exists():
            return candidate.resolve()
    searched = ", ".join(str(p) for p in _WORKERS_SEARCH_PATHS)
    raise FileNotFoundError(
        f"workers.yaml not found. Searched: {searched}. Run 'factory setup' to configure."
    )


def load_workers(path: Optional[Path] = None) -> GlobalConfig:
    if path is None:
        for candidate in _WORKERS_SEARCH_PATHS:
            if candidate.exists():
                path = candidate
                break
        else:
            searched = ", ".join(str(p) for p in _WORKERS_SEARCH_PATHS)
            raise FileNotFoundError(
                f"workers.yaml not found. Searched: {searched}. Run 'factory setup' to configure."
            )
    with open(path) as f:
        data = yaml.safe_load(f)
    config = GlobalConfig(**data)
    # Allow per-engineer overrides via env vars — keeps personal config out of the repo
    ssh_identity = os.environ.get("FACTORY_SSH_IDENTITY")
    worker_user = os.environ.get("FACTORY_WORKER_USER")
    for worker in config.workers.values():
        if ssh_identity and worker.identity_file is None:
            worker.identity_file = ssh_identity
        if worker_user:
            worker.user = worker_user
    return config


def load_task(path: Path) -> TaskDefinition:
    with open(path) as f:
        data = yaml.safe_load(f)
    return TaskDefinition(**data)
