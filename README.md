# clean-dropbox

Cleans up files and folders under Dropbox that match your ignore rules: list them (dry-run), move them to a staging directory for review, or delete them. Aligns with `~/Dropbox/rules.dropboxignore` and, if present, the workflow described in `dropbox_sync_rules.md`.

## What it does

- **Pattern source:** Reads `~/Dropbox/rules.dropboxignore` (same file Dropbox uses). The human-readable reference is `~/Dropbox/dropbox ignore rules.md`; keep both in sync when you change rules.
- **Modes:** Default is dry-run (list only). Use `--move` to relocate matches to `~/Data/clean_dropbox_moved` for review, or `--delete` to remove them (with confirmation).
- **One pattern at a time:** Use `--only PATTERN` to run for a single file type (e.g. `--only '*.dmg'` or `--only '__pycache__/'`). Without `--only`, all patterns from `rules.dropboxignore` are used; with it, only that pattern is applied so you can dry-run, move, or delete one type at a time.
- **Skipped:** Paths under `.dropbox` and `.dropbox.cache`, symlinks, and macOS Finder aliases are never collected. Some names are always excluded from cleanup (needed locally even if in ignore rules): `.DS_Store`, `Thumbs.db`, `desktop.ini`, `.Spotlight-V100`. Only top-level matches are listed (e.g. one entry for `node_modules`, not every file inside it).
- **Exclude config:** To keep specific files that would otherwise match (e.g. one `.dmg` you need), list them in `~/Data/clean_dropbox_exclude.txt`: one path or filename per line. Use a filename (e.g. `Perry-HR-2022.dmg`) to match that name anywhere; use a path relative to Dropbox (e.g. `HR/Perry-HR-2022.dmg`) for an exact path. Copy `clean_dropbox_exclude.txt.example` to `~/Data/clean_dropbox_exclude.txt` and edit.

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
# List what would be cleaned (no changes) as dry run (all patterns)
uv run python clean_dropbox.py

# Run for a single pattern only (dry-run, then move or delete that type alone)
uv run python clean_dropbox.py --only '*.dmg'
uv run python clean_dropbox.py --only '*.dmg' --move
uv run python clean_dropbox.py --only '__pycache__/' --delete

# Move matches to ~/Data/clean_dropbox_moved (prompts for "yes")
uv run python clean_dropbox.py --move

# Permanently delete matches (prompts for "yes")
uv run python clean_dropbox.py --delete
```

Consider pausing Dropbox sync before running `--move` or `--delete` to avoid conflicts.

When run in a terminal, the script shows a single updating progress line during the scan (e.g. "Scanning... 45,231 items, 12 matches") instead of listing every path.

At the end of each run (dry-run, move, or delete), a log is appended to `clean_dropbox.log` in the project directory (next to the script) with timestamp, mode, each matched path with size, and a summary (item count/size for dry-run; moved/deleted and failed counts for move/delete; or "aborted" if you did not confirm).

## Tests

```bash
uv run pytest
```

Or: `uv run pytest tests/ -v`

## Repository

- **GitHub:** https://github.com/pradau/clean_dropbox
- **Remote and push:** To add the remote and push (e.g. after cloning elsewhere or setting up the repo):
  ```bash
  git remote add origin https://github.com/pradau/clean_dropbox.git
  git push -u origin main
  ```

## Repository layout

- `clean_dropbox.py` — main script
- `clean_dropbox_exclude.txt.example` — example exclude list (copy to `~/Data/clean_dropbox_exclude.txt`)
- `dropbox_sync_rules.md` (optional) — reference for sync behavior, ignore rules, and workflow, if present in repo
- `pyproject.toml` — project and dev dependencies (uv/pip)
- `tests/test_clean_dropbox.py` — unit tests for pattern loading, matching, filtering, and formatting

## References

- Ignore rules: `~/Dropbox/rules.dropboxignore` (canonical), `~/Dropbox/dropbox ignore rules.md` (human reference)
- Exclude-from-cleanup list: `~/Data/clean_dropbox_exclude.txt` (optional; see example file)
- Behavior and workflow: `dropbox_sync_rules.md` in this repo (optional; if present)
