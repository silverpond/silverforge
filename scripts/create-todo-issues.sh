#!/usr/bin/env bash
# Creates 5 factory issues in the rust-todo repo.
# Usage: bash create-todo-issues.sh
set -euo pipefail

REPO="${REPO:-gokhanpicgeta/rust-todo}"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "Creating factory issues in $REPO..."

# ── Issue 1 ───────────────────────────────────────────────────────────────────
cat > "$TMP/i1.md" << 'EOF'
## Problem
The `list` command output does not include the item ID number, making it
impossible to know which number to pass to the `done` command.

## Expected output
```
[1] [ ] buy milk
[2] [ ] write tests
```

## Fix
Update the `display()` method in `src/lib.rs` to include the item ID on each line.
Add a test that checks the output contains the item ID.
EOF

gh issue create --repo "$REPO" \
  --title "list command should show item IDs" \
  --label "factory" \
  --body-file "$TMP/i1.md"

# ── Issue 2 ───────────────────────────────────────────────────────────────────
cat > "$TMP/i2.md" << 'EOF'
## Problem
`todo done 1` marks item 2 as done instead of item 1.
The `mark_done()` function in `src/lib.rs` treats the user's 1-based input
as a 0-based array index, so it always marks the wrong item.

## Fix
Subtract 1 from the input before indexing into the array.
Update the test in `mark_done_basic` to reflect correct 1-based behaviour.
EOF

gh issue create --repo "$REPO" \
  --title "done command marks wrong item (off-by-one)" \
  --label "factory" \
  --body-file "$TMP/i2.md"

# ── Issue 3 ───────────────────────────────────────────────────────────────────
cat > "$TMP/i3.md" << 'EOF'
## Problem
The TodoList is in-memory only. Every time the binary runs, the list is empty.
Todos should be saved to ~/.todo.json and loaded on startup.

## Fix
- Add serde and serde_json to Cargo.toml
- Add save() and load() methods to TodoList in src/lib.rs
- Update main.rs to load from file at startup and save after each mutation
- Add a test for round-trip serialisation (save then load returns same items)
EOF

gh issue create --repo "$REPO" \
  --title "todos are lost when the program exits (no persistence)" \
  --label "factory" \
  --body-file "$TMP/i3.md"

# ── Issue 4 ───────────────────────────────────────────────────────────────────
cat > "$TMP/i4.md" << 'EOF'
## Problem
There is no way to remove a todo item. Once added, an item can only be marked
done but never deleted from the list.

## Fix
- Add remove(one_based: usize) -> bool to TodoList in src/lib.rs
- Add the `remove` subcommand to main.rs
- Add tests for: remove first item, remove last item, remove out-of-range index
EOF

gh issue create --repo "$REPO" \
  --title "no remove command to delete todos" \
  --label "factory" \
  --body-file "$TMP/i4.md"

# ── Issue 5 ───────────────────────────────────────────────────────────────────
cat > "$TMP/i5.md" << 'EOF'
## Problem
Running `todo add` with empty or whitespace-only text silently creates a blank
todo item. The add() function in src/lib.rs does not validate the input.

## Fix
- Change add() to return Result<usize, &'static str>
- Return an error if the trimmed text is empty
- Update main.rs to print a helpful error message and exit non-zero
- Add tests for empty string, whitespace-only string, and valid string
EOF

gh issue create --repo "$REPO" \
  --title "add command accepts empty todo text" \
  --label "factory" \
  --body-file "$TMP/i5.md"

echo ""
echo "Created 5 issues in $REPO labeled 'factory'."
echo "Now run: factory poll --repo $REPO --template tasks/todo.yaml"
