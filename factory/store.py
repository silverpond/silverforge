"""
File-based run store.

Layout:
    runs/
      <run_id>/
        run.json          — serialised Run object
        eval_<cmd>.stdout — stdout from each eval command
        eval_<cmd>.stderr — stderr from each eval command
    contexts/
      <repo-slug>.md      — accumulated context for a repo, prepended to task prompts
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from factory.models import Run, RunState

RUNS_DIR = Path("runs")
CONTEXTS_DIR = Path("contexts")


def _run_dir(run_id: str) -> Path:
    return RUNS_DIR / run_id


def save_run(run: Run) -> None:
    run.updated_at = datetime.utcnow().isoformat()
    d = _run_dir(run.run_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "run.json").write_text(run.model_dump_json(indent=2))


def load_run(run_id: str) -> Optional[Run]:
    path = _run_dir(run_id) / "run.json"
    if not path.exists():
        return None
    return Run.model_validate_json(path.read_text())


def list_runs() -> List[Run]:
    if not RUNS_DIR.exists():
        return []
    runs = []
    for d in sorted(RUNS_DIR.iterdir()):
        p = d / "run.json"
        if p.exists():
            try:
                runs.append(Run.model_validate_json(p.read_text()))
            except Exception:
                pass  # skip corrupt entries
    return runs


def save_log(run_id: str, filename: str, content: str) -> None:
    d = _run_dir(run_id)
    d.mkdir(parents=True, exist_ok=True)
    # Sanitise filename to avoid path traversal
    safe_name = Path(filename).name
    (d / safe_name).write_text(content)


def update_state(run_id: str, state: RunState) -> Optional[Run]:
    run = load_run(run_id)
    if run is None:
        return None
    run.state = state
    save_run(run)
    return run


# ── Repo context helpers ──────────────────────────────────────────────────────

def repo_slug(repo_url: Optional[str], repo_path: Optional[str], task_id: str) -> str:
    """Return a filesystem-safe slug identifying a repo."""
    if repo_url:
        m = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", repo_url)
        if m:
            return re.sub(r"[^\w-]", "-", m.group(1))
    if repo_path:
        return Path(repo_path).expanduser().name
    return re.sub(r"[^\w-]", "-", task_id)


def load_repo_context(slug: str) -> str:
    """Read the accumulated context for a repo. Returns empty string if none exists."""
    path = CONTEXTS_DIR / f"{slug}.md"
    return path.read_text() if path.exists() else ""


def append_to_repo_context(slug: str, entry: str) -> None:
    """Append a new entry (e.g. completion notes) to the repo context file."""
    CONTEXTS_DIR.mkdir(parents=True, exist_ok=True)
    path = CONTEXTS_DIR / f"{slug}.md"
    if not path.exists():
        path.write_text(
            "## Repository Context\n\n"
            "Accumulated learnings from previous factory runs.\n\n"
            f"{entry}\n"
        )
    else:
        existing = path.read_text()
        path.write_text(existing.rstrip() + f"\n\n{entry}\n")
