# Factory Constitution

These rules apply to every factory run. Read them before starting work.

## Git discipline
- Work only in the current directory (your assigned worktree). Never touch the base repo directly.
- Make focused, minimal commits. Do not commit unrelated changes, generated artifacts, or debug code.
- If the worktree or branch layout looks wrong, stop and report it rather than proceeding silently.

## How to work
- Fix broken tooling or a failing test suite before implementing new behaviour.
- Implement one change at a time. Do not attempt multiple unrelated fixes in a single run.
- Do not add new dependencies unless the task explicitly requires it.

## Before finishing
Run the full test suite. Then write a short completion summary to `.factory/completion.md`:
1. What files you changed and why
2. What test commands you ran and whether they passed
3. Any assumptions you made or open questions

Do not consider the task complete until the test suite passes and this summary is written.

After writing the summary, signal completion by running these two shell commands with your bash tool:
```
echo done > .factory/status
```
Both are required. The pipeline cannot continue until these files exist.
