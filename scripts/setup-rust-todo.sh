#!/usr/bin/env bash
# Run this on ARES to create the rust-todo project.
# Usage: bash setup-rust-todo.sh
set -euo pipefail

PROJECT_DIR="$HOME/factory/projects/rust-todo"

echo "Creating rust-todo project at $PROJECT_DIR..."
mkdir -p "$HOME/factory/projects"
cargo new --name rust-todo "$PROJECT_DIR"
cd "$PROJECT_DIR"

# ── Write src/lib.rs (core logic, unit-testable) ─────────────────────────────
cat > src/lib.rs << 'RUST'
//! Rust TODO library.
//!
//! Known issues (deliberate for factory testing):
//!   1. list() does not show item IDs
//!   2. done() has an off-by-one bug (1-based input treated as 0-based)
//!   3. no file persistence — data resets every run
//!   4. no remove() function
//!   5. add() accepts empty strings without error

#[derive(Debug, Clone)]
pub struct TodoItem {
    pub id: usize,
    pub text: String,
    pub done: bool,
}

#[derive(Default)]
pub struct TodoList {
    items: Vec<TodoItem>,
    next_id: usize,
}

impl TodoList {
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a new item. BUG #5: does not reject empty strings.
    pub fn add(&mut self, text: &str) -> usize {
        let id = self.next_id;
        self.next_id += 1;
        self.items.push(TodoItem { id, text: text.to_string(), done: false });
        id
    }

    /// Return all items.
    pub fn items(&self) -> &[TodoItem] {
        &self.items
    }

    /// Format the list for display.
    /// BUG #1: does not include the item ID in output.
    pub fn display(&self) -> String {
        if self.items.is_empty() {
            return "No todos.".to_string();
        }
        self.items.iter()
            .map(|i| {
                let check = if i.done { "x" } else { " " };
                // Missing: item ID should be shown here
                format!("[{}] {}", check, i.text)
            })
            .collect::<Vec<_>>()
            .join("\n")
    }

    /// Mark item with the given 1-based number as done.
    /// BUG #2: subtracts nothing — treats 1-based input as 0-based index.
    pub fn mark_done(&mut self, one_based: usize) -> bool {
        // BUG: should be `one_based - 1` to convert to 0-based
        if one_based < self.items.len() {
            self.items[one_based].done = true;
            true
        } else {
            false
        }
    }
}

// ── tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn add_and_list() {
        let mut list = TodoList::new();
        list.add("buy milk");
        list.add("write tests");
        assert_eq!(list.items().len(), 2);
    }

    #[test]
    fn display_empty() {
        let list = TodoList::new();
        assert_eq!(list.display(), "No todos.");
    }

    #[test]
    fn display_items() {
        let mut list = TodoList::new();
        list.add("foo");
        let out = list.display();
        assert!(out.contains("foo"));
    }

    #[test]
    fn mark_done_basic() {
        let mut list = TodoList::new();
        list.add("a");
        list.add("b");
        // BUG: passing 1 marks index 1 ("b") not index 0 ("a")
        // Test is written to match the buggy behaviour so cargo test passes
        let ok = list.mark_done(1);
        assert!(ok);
    }
}
RUST

# ── Write src/main.rs (CLI wrapper) ──────────────────────────────────────────
cat > src/main.rs << 'RUST'
use std::env;
use rust_todo::TodoList;

fn main() {
    let args: Vec<String> = env::args().collect();
    let mut list = TodoList::new();

    if args.len() < 2 {
        eprintln!("Usage: todo <add|list|done> [args]");
        std::process::exit(1);
    }

    match args[1].as_str() {
        "add" => {
            if args.len() < 3 {
                eprintln!("Usage: todo add <text>");
                std::process::exit(1);
            }
            let text = args[2..].join(" ");
            let id = list.add(&text);
            println!("Added item #{}", id);
        }
        "list" => {
            println!("{}", list.display());
        }
        "done" => {
            if args.len() < 3 {
                eprintln!("Usage: todo done <number>");
                std::process::exit(1);
            }
            let n: usize = args[2].parse().unwrap_or(0);
            if list.mark_done(n) {
                println!("Marked item {} as done.", n);
            } else {
                eprintln!("Item {} not found.", n);
            }
        }
        cmd => {
            eprintln!("Unknown command: {}", cmd);
            std::process::exit(1);
        }
    }
}
RUST

# ── Build and test ────────────────────────────────────────────────────────────
echo "Building..."
cargo build 2>&1

echo "Running tests..."
cargo test 2>&1

# ── Git init and first commit ─────────────────────────────────────────────────
git init
git add -A
git commit -m "initial: rust-todo with deliberate bugs for factory testing"

echo ""
echo "Done! Now:"
echo "  1. Create a GitHub repo called 'rust-todo'"
echo "  2. git remote add origin git@github.com:gokhanpicgeta/rust-todo.git"
echo "  3. git push -u origin master"
echo "  4. Create 5 issues labeled 'factory' (see scripts/create-todo-issues.sh)"
