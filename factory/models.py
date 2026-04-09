"""
Core data models for the factory controller.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class RunState(str, Enum):
    queued = "queued"
    running = "running"
    waiting_input = "waiting_input"
    evaluating = "evaluating"
    passed = "passed"
    failed = "failed"
    human_review = "human_review"


class RepoConfig(BaseModel):
    path: str              # path to base repo on remote (must already exist)
    branch: str = "main"  # branch to base each run's worktree on
    url: Optional[str] = None  # if set, clone to path if it doesn't exist yet


class AgentConfig(BaseModel):
    prompt: str
    session: Optional[str] = None  # tmux session name; auto-generated if None


class EvalConfig(BaseModel):
    commands: List[str]
    working_dir: str
    timeout: int = 300  # seconds per command


class CoderConfig(BaseModel):
    prompt: str
    max_iterations: int = 3      # how many coder → eval cycles before giving up
    session_timeout: int = 600   # seconds to wait for Claude to finish per iteration


class EvaluatorConfig(BaseModel):
    criteria: Optional[str] = None  # extra review criteria beyond the defaults
    timeout: int = 120              # seconds for the review call


class UntangleConfig(BaseModel):
    lang: str = "rust"
    fail_on: str = "fanout-increase,new-scc"  # comma-separated conditions
    timeout: int = 30


class CrucibleConfig(BaseModel):
    block_on: str = "Critical"   # severity level that blocks the run
    timeout: int = 300           # seconds for the review


class TaskDefinition(BaseModel):
    id: str
    name: str
    worker: str
    repo: Optional[RepoConfig] = None    # omit for tasks that don't need a repo
    agent: Optional[AgentConfig] = None  # omit until AoE is wired up
    coder: Optional[CoderConfig] = None        # omit for eval-only tasks
    evaluator: Optional[EvaluatorConfig] = None  # omit to skip code review
    untangle: Optional[UntangleConfig] = None  # omit to skip structural check
    crucible: Optional[CrucibleConfig] = None  # omit to skip multi-agent review
    eval: EvalConfig


class EvalResult(BaseModel):
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float


class Run(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    task_id: str
    task_name: str
    worker: str
    state: RunState = RunState.queued
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    eval_results: List[EvalResult] = Field(default_factory=list)
    worktree_path: Optional[str] = None  # git worktree created for this run
    issue_number: Optional[int] = None   # GitHub issue number if spawned by poller
    evaluator_verdict: str = ""          # approved / needs_changes
    evaluator_reason: str = ""
    notes: str = ""
