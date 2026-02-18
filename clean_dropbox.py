# Author: Perry Radau
# Date: 2026-02-18
# Description: Cleans up files/folders under Dropbox that match rules in rules.dropboxignore
#   (move to staging or delete). Pattern source: ~/Dropbox/rules.dropboxignore. Human-readable
#   reference: "dropbox ignore rules.md" in the Dropbox root. Patterns use fnmatch syntax only
#   (e.g. *.dmg, __pycache__/); recursive path patterns with ** are not supported.
# Dependencies: Python 3.6+
# Usage: python clean_dropbox.py [--move | --delete]   (default: dry-run)

import fnmatch
import shutil
import sys
from pathlib import Path

DROPBOX_ROOT = Path.home() / "Dropbox"
# Canonical pattern file used by Dropbox and this script. Location: ~/Dropbox/rules.dropboxignore
IGNORE_FILE = DROPBOX_ROOT / "rules.dropboxignore"
STAGING_DIR = Path.home() / "Data" / "clean_dropbox_moved"

# Paths under Dropbox that must not be touched (Dropbox internal use)
_DROPBOX_SYSTEM_NAMES = (".dropbox", ".dropbox.cache")


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
    for line in ignore_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


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


def collect_matches(root: Path, patterns: list[str]) -> list[Path]:
    """Find all paths under root matching patterns; skip system dirs, symlinks, Mac aliases; top-level only."""
    matches = []
    for item in sorted(root.rglob("*")):
        if _under_dropbox_system(item, root):
            continue
        if item.is_symlink():
            continue
        if _is_mac_alias(item):
            continue
        if matches_any(item, patterns, root):
            matches.append(item)
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


def do_move(matches: list[Path]) -> None:
    confirm = input("\nMove all listed items to staging? Type 'yes' to confirm: ")
    if confirm.strip().lower() != "yes":
        print("Aborted.")
        return
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


def do_delete(matches: list[Path]) -> None:
    confirm = input("\nPermanently delete all listed items? Type 'yes' to confirm: ")
    if confirm.strip().lower() != "yes":
        print("Aborted.")
        return

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


def run(mode: str) -> None:
    """Load patterns, collect top-level matches, then dry-run, move, or delete. Affects local files only."""
    if not IGNORE_FILE.exists():
        print(f"Ignore file not found: {IGNORE_FILE}")
        sys.exit(1)

    patterns = load_patterns(IGNORE_FILE)
    matches = collect_matches(DROPBOX_ROOT, patterns)

    if not matches:
        print("No matching files or folders found.")
        return

    mode_label = {"dry-run": "DRY RUN", "move": "MOVE TO STAGING", "delete": "DELETE"}
    print(f"{mode_label[mode]} — matched files/folders:\n")
    print_matches(matches)

    if mode == "dry-run":
        print(f"\nDry run complete. Options:")
        print(f"  --move    Relocate to {STAGING_DIR} for review before deleting")
        print(f"  --delete  Permanently delete immediately (use with caution)")
    else:
        print("\nConsider pausing Dropbox sync before running move or delete to avoid conflicts.")
        if mode == "move":
            do_move(matches)
        elif mode == "delete":
            do_delete(matches)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--delete" in args:
        mode = "delete"
    elif "--move" in args:
        mode = "move"
    else:
        mode = "dry-run"
    run(mode)