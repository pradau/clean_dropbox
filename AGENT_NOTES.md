# Agent notes — clean_dropbox

## Project summary (Phase 1)

**What the project does:** Cleans up files and folders under Dropbox that match rules in `~/Dropbox/rules.dropboxignore`. Modes: dry-run (list only), move to `~/Data/clean_dropbox_moved`, or delete (with confirmation). Supports `--only PATTERN` to run for a single pattern. Reads exclude list from `~/Data/clean_dropbox_exclude.txt`. Logs each run to `clean_dropbox.log` in the script directory.

**Current structure:**
- **Entry point:** `clean_dropbox.py` as main; `_parse_args()` returns (mode, only_pattern); `run(mode, only_pattern)` orchestrates load, collect, print, and optional move/delete.
- **Main logic:** Single module: `load_patterns`, `load_exclude_config`, `matches_any`, `collect_matches` (with top-level-only filtering), `_excluded_from_cleanup`, `_under_dropbox_system`, `_is_mac_alias`; actions `do_move`, `do_delete`; logging `_write_log`; formatting `format_size`, `get_size`, `print_matches`.
- **Config/files:** `pyproject.toml` (Python >=3.6, pytest for dev), `tests/test_clean_dropbox.py`, `README.md`, `clean_dropbox_exclude.txt.example`. README references `dropbox_sync_rules.md` in repo layout; that file was not present in the project directory at review time (may live elsewhere or be missing).

**Important gaps / bugs (no fixes in Phase 1):**
1. **No tests for CLI or destructive paths:** `run()`, `do_move()`, `do_delete()`, and `_write_log()` are untested. Tests cover pattern loading, matching, filtering, and formatting only.
2. **Inconsistent file encoding:** `load_patterns()` uses `read_text()` without explicit encoding; `load_exclude_config()` uses `encoding="utf-8"`. Risk of divergence on systems where default encoding is not UTF-8.
3. **No standard CLI help:** Arguments are parsed manually with `sys.argv`. There is no `--help` or argparse; users must read README to discover options.
4. **README references missing file:** Repository layout lists `dropbox_sync_rules.md`; if it is missing, the reference is broken for users following the README.

---

## Implementation plan (Phase 2)

Improvements ranked by user-facing value. Scope: small = one or two files, no new deps; medium = a few files or one new dependency. Only small and medium items are included.

| # | Improvement | Scope | Rationale |
|---|-------------|--------|-----------|
| 1 | Add argparse with --help and existing flags (--only, --move, --delete) | Small | Discoverability; no new deps; single file (clean_dropbox.py). |
| 2 | Use UTF-8 explicitly in load_patterns() (read_text(encoding="utf-8")) | Small | Consistency with load_exclude_config; avoids encoding surprises. |
| 3 | Add unit tests for _write_log (log content and summary lines; use tmp_path for log file) | Small | Verifies logging without touching move/delete. |
| 4 | Clarify README about dropbox_sync_rules.md (e.g. "if present" or optional reference) | Small | Avoids broken reference if file is missing; one file. |
| 5 | Add test for run() in dry-run mode with tmp_path and minimal ignore file | Medium | Covers main entry path and "no matches" / "with matches" behavior; may require small refactor to allow injecting root/ignore path for tests. |

Implementation order: 1, 2, 3, 4, 5. After each item: implement, run tests, commit. No refactor beyond what is needed for the improvement.

---

## Manual Testing Checklist

1. **--help:** From the project directory run `uv run python clean_dropbox.py --help`. Confirm usage and options (--only, --move, --delete) are shown.
2. **Dry-run (default):** Run `uv run python clean_dropbox.py` (with `~/Dropbox/rules.dropboxignore` present). Confirm a list of matches is printed (or "No matching files or folders found") and that `clean_dropbox.log` in the script directory is appended with a new run (timestamp, mode=dry-run, items, summary).
3. **Single pattern:** Run `uv run python clean_dropbox.py --only '*.dmg'`. Confirm only `*.dmg` matches are listed and the log entry includes `only_pattern='*.dmg'`.
4. **README:** Open README and confirm references to `dropbox_sync_rules.md` indicate it is optional / "if present" so the doc is accurate even when that file is missing.

Do not run `--move` or `--delete` in manual testing unless you intend to relocate or remove real files and have confirmed the match list.

---

## Uncertain

- **run() tests:** Implemented with monkeypatch only (DROPBOX_ROOT, IGNORE_FILE, EXCLUDE_CONFIG_FILE, LOG_FILE); no refactor to inject paths was required. Tests run in the project environment with no skips or external dependencies.
- **dropbox_sync_rules.md:** The file was not present in the repo at review time. README was updated to treat it as optional; no stub file was added. If the file lives elsewhere or is added later, the README remains correct.
- No tests were added that skip or depend on a specific environment; all new tests use tmp_path and monkeypatch and pass with `uv run pytest`.
