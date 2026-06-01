"""
Repo context caching and Reflexion-style lesson accumulation.

On the first run for a repo, a quick claude analysis is run and the result
is stored at ~/factory/repo-context/<slug>.md on the worker. Subsequent
runs load the cached file (fast SSH cat) and inject it into the coder prompt
so the agent doesn't need to analyse the repo from scratch.

After each run, a haiku call distils what happened into a one-sentence lesson
stored at ~/factory/repo-lessons/<slug>.md. These lessons are injected into
the context for subsequent runs so the agent avoids repeating past mistakes.

Cache invalidation: delete the files on the worker to regenerate.
"""
from __future__ import annotations

import base64
import re
import shlex

from factory.ssh import SSHClient

_LESSON_PROMPT = """\
A coding agent just completed a run on this repository. Generate one specific lesson \
for future agents working in this codebase.

Task: {task}
Outcome: {outcome}
Crucible code review issues: {crucible}
Eval/test failures: {eval_failures}
Agent completion notes: {completion}

Write exactly ONE sentence — a specific, actionable rule that will help future agents \
avoid mistakes or follow the right patterns in THIS repo. \
Start with Always, Never, When, or Avoid.\
"""

_ANALYSIS_PROMPT = """\
You are analysing a software repository for a coding agent that will work in it.
Produce a concise technical reference (300-500 words) covering:

1. Primary language(s) and tech stack (frameworks, runtimes, major libraries)
2. High-level architecture — key components, services, and how they interact
3. Important files and directories an engineer should know about
4. Build system and how to build, run, and test the project
5. Conventions or patterns that are not obvious from file names alone

Be factual and specific — only describe what you can see. Format as Markdown.
"""


def _repo_slug(repo_path: str) -> str:
    """Turn a remote repo path into a safe filename slug (max 120 chars)."""
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", repo_path.strip("/"))
    return cleaned[:120]


def _context_remote_path(repo_path: str) -> str:
    return f"~/factory/repo-context/{_repo_slug(repo_path)}.md"


def _lessons_remote_path(repo_path: str) -> str:
    return f"~/factory/repo-lessons/{_repo_slug(repo_path)}.md"


def get_or_create_repo_context(
    client: SSHClient,
    repo_path: str,
    shell_init: str = "",
    model: str = "claude-haiku-4-5-20251001",
    timeout: int = 120,
) -> str:
    """
    Return cached repo context for *repo_path*, generating it on first call.

    The context is stored on the worker at ~/factory/repo-context/<slug>.md.
    Returns an empty string if the repo path does not exist or generation fails.
    """
    ctx_path = _context_remote_path(repo_path)

    # Fast path: return cached context if it already exists
    existing = client.run(
        f"cat {ctx_path} 2>/dev/null || true",
        timeout=10,
    ).stdout.strip()
    if not existing:
        # Slow path: generate context with a non-interactive claude call
        init_prefix = f"{shell_init} && " if shell_init else ""
        encoded = base64.b64encode(_ANALYSIS_PROMPT.encode()).decode()
        cmd = (
            f"{init_prefix}"
            f"mkdir -p ~/factory/repo-context && "
            f"cd {repo_path} && "
            f"claude -p --dangerously-skip-permissions --model {model} "
            f'"$(echo \'{encoded}\' | base64 -d)" '
            f"> {ctx_path} 2>/dev/null && "
            f"cat {ctx_path} || true"
        )
        result = client.run(cmd, timeout=timeout)
        existing = result.stdout.strip()

    # Append any accumulated lessons from past runs
    lessons = get_repo_lessons(client, repo_path)
    if lessons:
        return f"{existing}\n\n## Lessons from past runs\n\n{lessons}"
    return existing


def get_repo_lessons(client: SSHClient, repo_path: str) -> str:
    """Read accumulated Reflexion lessons for this repo from the worker."""
    result = client.run(
        f"cat {shlex.quote(_lessons_remote_path(repo_path))} 2>/dev/null || true",
        timeout=10,
    )
    return result.stdout.strip()


def append_repo_lesson(
    client: SSHClient,
    repo_path: str,
    lesson: str,
    max_entries: int = 10,
) -> None:
    """Append a lesson to the repo's lessons file on the worker, keeping last max_entries."""
    from datetime import datetime as _dt
    date_str = _dt.utcnow().strftime("%Y-%m-%d")
    entry = f"- [{date_str}] {lesson}"
    lessons_path = _lessons_remote_path(repo_path)
    client.run(
        f"mkdir -p ~/factory/repo-lessons && "
        f"echo {shlex.quote(entry)} >> {lessons_path} && "
        f"tail -n {max_entries} {lessons_path} > {lessons_path}.tmp && "
        f"mv {lessons_path}.tmp {lessons_path}",
        timeout=10,
    )


def inject_repo_context(prompt: str, context: str) -> str:
    """Prepend *context* to *prompt* under a clearly labelled section."""
    if not context:
        return prompt
    header = (
        "## Repository Context\n\n"
        "The following is a pre-generated overview of this repository. "
        "Use it as background knowledge — do not spend time re-analysing "
        "the repo structure from scratch.\n\n"
        f"{context}\n\n"
        "---\n\n"
    )
    return header + prompt
