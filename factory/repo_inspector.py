"""
Repo context caching: gather crucial repo details once and reuse across runs.

On the first run for a repo, a quick claude analysis is run and the result
is stored at ~/factory/repo-context/<slug>.md on the worker. Subsequent
runs load the cached file (fast SSH cat) and inject it into the coder prompt
so the agent doesn't need to analyse the repo from scratch.

Cache invalidation: delete the file on the worker to regenerate.
"""
from __future__ import annotations

import re
import shlex

from factory.ssh import SSHClient

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
    if existing:
        return existing

    # Slow path: generate context with a non-interactive claude call
    init_prefix = f"{shell_init} && " if shell_init else ""
    quoted_prompt = shlex.quote(_ANALYSIS_PROMPT)
    cmd = (
        f"{init_prefix}"
        f"mkdir -p ~/factory/repo-context && "
        f"cd {repo_path} && "
        f"claude -p --dangerously-skip-permissions --model {model} {quoted_prompt} "
        f"> {ctx_path} 2>/dev/null && "
        f"cat {ctx_path} || true"
    )
    result = client.run(cmd, timeout=timeout)
    return result.stdout.strip()


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
