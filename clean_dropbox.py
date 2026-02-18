# Author: Perry Radau
# Date: 2026-02-18
# Description: Cleans up files/folders under Dropbox that match rules in rules.dropboxignore
#   (move to staging or delete). Pattern source: ~/Dropbox/rules.dropboxignore. Human-readable
#   reference: "dropbox ignore rules.md" in the Dropbox root. Patterns use fnmatch syntax only
#   (e.g. *.dmg, __pycache__/); recursive path patterns with ** are not supported.
# Dependencies: Python 3.6+
# Usage: python clean_dropbox.py [--only PATTERN] [--move | --delete]   (default: dry-run)

import argparse
import fnmatch
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set, Tuple

# Minimum seconds between progress updates; avoids flooding when scanning quickly
_PROGRESS_INTERVAL_SEC = 0.25
# Update progress at least every N items when interval has elapsed
_PROGRESS_INTERVAL_ITEMS = 5000

# Log file: appended at end of each run (dry-run, move, or delete); in the script directory
_SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE = _SCRIPT_DIR / "clean_dropbox.log"

DROPBOX_ROOT = Path.home() / "Dropbox"
# Canonical pattern file used by Dropbox and this script. Location: ~/Dropbox/rules.dropboxignore
IGNORE_FILE = DROPBOX_ROOT / "rules.dropboxignore"
STAGING_DIR = Path.home() / "Data" / "clean_dropbox_moved"

# User config: paths or filenames to never clean (one per line). Location: ~/Data/clean_dropbox_exclude.txt
EXCLUDE_CONFIG_FILE = Path.home() / "Data" / "clean_dropbox_exclude.txt"

# Paths under Dropbox that must not be touched (Dropbox internal use)
_DROPBOX_SYSTEM_NAMES = (".dropbox", ".dropbox.cache")

# Filenames we never clean: needed locally even if in ignore rules (e.g. not synced to cloud).
_NEVER_CLEAN_NAMES = frozenset({
    ".DS_Store",        # macOS folder metadata
    "Thumbs.db",        # Windows thumbnail cache
    "desktop.ini",      # Windows folder settings
    ".Spotlight-V100",  # macOS Spotlight index (directory)
})


def _is_mac_alias(path: Path) -> bool:
    """Return True if path is a macOS Finder alias file (small file with 'book' magic)."""
    if sys.platform != "darwin" or not path.is_file():
        return False
    try:
        if path.stat().st_size > 1024:
            return False
        return path.read_bytes()[:4] == b"book"
    except OSError:
        return False


def _under_dropbox_system(path: Path, root: Path) -> bool:
    """Return True if path is under .dropbox or .dropbox.cache."""
    try:
        rel = path.relative_to(root)
        parts = rel.parts
        return parts and parts[0] in _DROPBOX_SYSTEM_NAMES
    except ValueError:
        return False


def load_patterns(ignore_file: Path) -> list[str]:
    """Load non-comment, non-empty lines from the ignore file as pattern strings."""
    patterns = []
    for line in ignore_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def load_exclude_config(exclude_file: Path) -> Tuple[Set[str], Set[str]]:
    """Load exclude-from-cleanup list. Returns (full_relative_paths, basename_only)."""
    full_paths = set()
    basenames = set()
    if not exclude_file.exists():
        return (full_paths, basenames)
    try:
        for line in exclude_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "/" in line:
                full_paths.add(line)
            else:
                basenames.add(line)
    except OSError:
        pass
    return (full_paths, basenames)


def matches_any(path: Path, patterns: list[str], dropbox_root: Path) -> bool:
    """Return True if path (name or relative path) matches any fnmatch pattern."""
    relative = path.relative_to(dropbox_root)
    name = path.name
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
        if fnmatch.fnmatch(str(relative), pattern):
            return True
    return False


def _top_level_only(matches: list[Path]) -> list[Path]:
    """Return matches that have no ancestor in the set; avoids double-counting directories."""
    match_set = set(matches)
    return [m for m in matches if not any(p in match_set for p in m.parents)]


def _excluded_from_cleanup(
    path: Path, root: Path, exclude_full: Set[str], exclude_basename: Set[str]
) -> bool:
    """True if path should never be cleaned (built-in names or user exclude config)."""
    if path.name in _NEVER_CLEAN_NAMES:
        return True
    if path.name in exclude_basename:
        return True
    try:
        rel = path.relative_to(root)
        if str(rel) in exclude_full:
            return True
    except ValueError:
        pass
    return False


def collect_matches(
    root: Path,
    patterns: list[str],
    exclude_full: Optional[Set[str]] = None,
    exclude_basename: Optional[Set[str]] = None,
) -> list[Path]:
    """Find all paths under root matching patterns; skip system dirs, symlinks, Mac aliases, never-clean names, and user exclude list; top-level only."""
    if exclude_full is None:
        exclude_full = set()
    if exclude_basename is None:
        exclude_basename = set()
    matches = []
    show_progress = sys.stdout.isatty()
    last_progress_time = 0.0
    n_scanned = 0
    for item in sorted(root.rglob("*")):
        n_scanned += 1
        if _under_dropbox_system(item, root):
            continue
        if item.is_symlink():
            continue
        if _is_mac_alias(item):
            continue
        if not matches_any(item, patterns, root):
            continue
        if _excluded_from_cleanup(item, root, exclude_full, exclude_basename):
            continue
        matches.append(item)
        if show_progress:
            now = time.monotonic()
            if n_scanned % _PROGRESS_INTERVAL_ITEMS == 0 or (now - last_progress_time) >= _PROGRESS_INTERVAL_SEC:
                print(f"\rScanning... {n_scanned:,} items, {len(matches):,} matches", end="", flush=True)
                last_progress_time = now
    if show_progress and n_scanned > 0:
        print(flush=True)
    return _top_level_only(matches)


def format_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def print_matches(matches: list[Path]) -> None:
    for item in matches:
        size = get_size(item)
        kind = "DIR " if item.is_dir() else "FILE"
        print(f"  [{kind}] {item.relative_to(DROPBOX_ROOT)}  ({format_size(size)})")
    total = sum(get_size(i) for i in matches)
    print(f"\nTotal: {len(matches)} items, {format_size(total)}")


def _write_log(
    mode: str,
    matches: list[Path],
    total_size: int,
    *,
    moved: Optional[int] = None,
    move_failed: Optional[int] = None,
    deleted: Optional[int] = None,
    delete_failed: Optional[int] = None,
    aborted: bool = False,
    only_pattern: Optional[str] = None,
) -> None:
    """Append a run summary to LOG_FILE (in the script directory)."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = f"--- {ts} mode={mode}"
    if only_pattern is not None:
        header += f" only_pattern={only_pattern!r}"
    lines = [header, ""]
    for item in matches:
        try:
            rel = item.relative_to(DROPBOX_ROOT)
        except ValueError:
            rel = item
        size = get_size(item)
        kind = "dir" if item.is_dir() else "file"
        lines.append(f"  {kind}  {rel}  ({format_size(size)})")
    lines.append("")
    if aborted:
        lines.append("  (aborted by user)")
    elif mode == "dry-run":
        lines.append(f"  summary: {len(matches)} items, {format_size(total_size)}")
    elif mode == "move" and moved is not None and move_failed is not None:
        lines.append(f"  summary: moved {moved} to {STAGING_DIR}, failed {move_failed}")
    elif mode == "delete" and deleted is not None and delete_failed is not None:
        lines.append(f"  summary: deleted {deleted}, failed {delete_failed}")
    lines.append("")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except OSError as e:
        print(f"Warning: could not write log to {LOG_FILE}: {e}")


def do_move(matches: list[Path]) -> Optional[tuple[int, int]]:
    """Move matches to STAGING_DIR. Returns (moved, failed) or None if user aborted."""
    confirm = input("\nMove all listed items to staging? Type 'yes' to confirm: ")
    if confirm.strip().lower() != "yes":
        print("Aborted.")
        return None
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    moved, failed = 0, 0
    for item in matches:
        dest = STAGING_DIR / item.relative_to(DROPBOX_ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(item), dest)
            moved += 1
        except Exception as e:
            print(f"  ERROR moving {item}: {e}")
            failed += 1
    print(f"\nMoved {moved} items to {STAGING_DIR}. Failed: {failed}.")
    print("Review the staging folder, then delete it manually when satisfied.")
    return (moved, failed)


def do_delete(matches: list[Path]) -> Optional[tuple[int, int]]:
    """Delete matches. Returns (deleted, failed) or None if user aborted."""
    confirm = input("\nPermanently delete all listed items? Type 'yes' to confirm: ")
    if confirm.strip().lower() != "yes":
        print("Aborted.")
        return None

    deleted, failed = 0, 0
    for item in matches:
        try:
            if item.is_dir():
                for child in sorted(item.rglob("*"), reverse=True):
                    child.unlink() if child.is_file() else child.rmdir()
                item.rmdir()
            else:
                item.unlink()
            deleted += 1
        except Exception as e:
            print(f"  ERROR deleting {item}: {e}")
            failed += 1
    print(f"\nDeleted {deleted} items. Failed: {failed}.")
    return (deleted, failed)


def run(mode: str, only_pattern: Optional[str] = None) -> None:
    """Load patterns, collect top-level matches, then dry-run, move, or delete. Affects local files only."""
    if only_pattern is not None:
        patterns = [only_pattern]
    else:
        if not IGNORE_FILE.exists():
            print(f"Ignore file not found: {IGNORE_FILE}")
            sys.exit(1)
        patterns = load_patterns(IGNORE_FILE)
    exclude_full, exclude_basename = load_exclude_config(EXCLUDE_CONFIG_FILE)
    matches = collect_matches(
        DROPBOX_ROOT, patterns, exclude_full=exclude_full, exclude_basename=exclude_basename
    )

    if not matches:
        print("No matching files or folders found.")
        return

    mode_label = {"dry-run": "DRY RUN", "move": "MOVE TO STAGING", "delete": "DELETE"}
    if only_pattern is not None:
        print(f"Pattern (--only): {only_pattern}\n")
    print(f"{mode_label[mode]} — matched files/folders:\n")
    print_matches(matches)
    total_size = sum(get_size(m) for m in matches)

    if mode == "dry-run":
        _write_log(mode, matches, total_size, only_pattern=only_pattern)
        print(f"\nDry run complete. Options:")
        if only_pattern is None:
            print(f"  --only PATTERN   Run for a single pattern (e.g. --only '*.dmg')")
        print(f"  --move    Relocate to {STAGING_DIR} for review before deleting")
        print(f"  --delete  Permanently delete immediately (use with caution)")
        print(f"\nLog written to {LOG_FILE}")
    else:
        print("\nConsider pausing Dropbox sync before running move or delete to avoid conflicts.")
        if mode == "move":
            result = do_move(matches)
            if result is None:
                _write_log(mode, matches, total_size, aborted=True, only_pattern=only_pattern)
            else:
                moved, failed = result
                _write_log(mode, matches, total_size, moved=moved, move_failed=failed, only_pattern=only_pattern)
        elif mode == "delete":
            result = do_delete(matches)
            if result is None:
                _write_log(mode, matches, total_size, aborted=True, only_pattern=only_pattern)
            else:
                deleted, failed = result
                _write_log(mode, matches, total_size, deleted=deleted, delete_failed=failed, only_pattern=only_pattern)
        print(f"\nLog written to {LOG_FILE}")


def _parse_args() -> tuple[str, Optional[str]]:
    """Return (mode, only_pattern). Uses argparse for --help and flag parsing."""
    parser = argparse.ArgumentParser(
        description="Clean Dropbox files/folders matching rules.dropboxignore (list, move to staging, or delete)."
    )
    parser.add_argument(
        "--only",
        metavar="PATTERN",
        help="Run for a single pattern only (e.g. --only '*.dmg' or --only '__pycache__/')",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--move",
        action="store_true",
        help=f"Move matches to {STAGING_DIR} for review before deleting",
    )
    group.add_argument(
        "--delete",
        action="store_true",
        help="Permanently delete matches (prompts for confirmation)",
    )
    args = parser.parse_args()
    mode = "delete" if args.delete else ("move" if args.move else "dry-run")
    return (mode, args.only)


if __name__ == "__main__":
    mode, only_pattern = _parse_args()
    run(mode, only_pattern=only_pattern)