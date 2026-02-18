# clean-dropbox

Cleans up files and folders under Dropbox that match your ignore rules: list them (dry-run), move them to a staging directory for review, or delete them. Aligns with `~/Dropbox/rules.dropboxignore` and the workflow described in `dropbox_sync_rules.md`.

## What it does

- **Pattern source:** Reads `~/Dropbox/rules.dropboxignore` (same file Dropbox uses). The human-readable reference is `~/Dropbox/dropbox ignore rules.md`; keep both in sync when you change rules.
- **Modes:** Default is dry-run (list only). Use `--move` to relocate matches to `~/Data/clean_dropbox_moved` for review, or `--delete` to remove them (with confirmation).
- **Skipped:** Paths under `.dropbox` and `.dropbox.cache`, symlinks, and macOS Finder aliases are never collected. Only top-level matches are listed (e.g. one entry for `node_modules`, not every file inside it).

## Requirements

- Python 3.6+
- [uv](https://docs.astral.sh/uv/) recommended for install and run

## Setup

```bash
uv sync
```

If you do not use uv: create a venv, install dependencies from `pyproject.toml` (e.g. no extra deps for the script; pytest for tests).

## Usage

```bash
# List what would be cleaned (no changes)
uv run python clean_dropbox.py

# Move matches to ~/Data/clean_dropbox_moved (prompts for "yes")
uv run python clean_dropbox.py --move

# Permanently delete matches (prompts for "yes")
uv run python clean_dropbox.py --delete
```

Consider pausing Dropbox sync before running `--move` or `--delete` to avoid conflicts.

## Tests

```bash
uv run pytest
```

Or: `uv run pytest tests/ -v`

## Repository layout

- `clean_dropbox.py` — main script
- `dropbox_sync_rules.md` — reference for sync behavior, ignore rules, and workflow
- `pyproject.toml` — project and dev dependencies (uv/pip)
- `tests/test_clean_dropbox.py` — unit tests for pattern loading, matching, filtering, and formatting

## References

- Ignore rules: `~/Dropbox/rules.dropboxignore` (canonical), `~/Dropbox/dropbox ignore rules.md` (human reference)
- Behavior and workflow: `dropbox_sync_rules.md` in this repo
