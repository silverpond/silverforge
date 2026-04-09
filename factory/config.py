"""
Configuration loading — workers.yaml and task YAML files.
"""
from __future__ import annotations

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


class GlobalConfig(BaseModel):
    workers: Dict[str, WorkerConfig]


def load_workers(path: Path = Path("workers.yaml")) -> GlobalConfig:
    with open(path) as f:
        data = yaml.safe_load(f)
    return GlobalConfig(**data)


def load_task(path: Path) -> TaskDefinition:
    with open(path) as f:
        data = yaml.safe_load(f)
    return TaskDefinition(**data)
