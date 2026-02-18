# Author: Perry Radau
# Date: 2026-02-18
# Description: Unit tests for clean_dropbox (pattern loading, matching, filtering, formatting).

import sys

import pytest
from pathlib import Path

import clean_dropbox as m


def test_load_patterns_empty_file(tmp_path: Path) -> None:
    f = tmp_path / "ignore"
    f.write_text("")
    assert m.load_patterns(f) == []


def test_load_patterns_skips_comments_and_blanks(tmp_path: Path) -> None:
    f = tmp_path / "ignore"
    f.write_text("# comment\n\n  \n*.dmg\n# another\n__pycache__/\n")
    assert m.load_patterns(f) == ["*.dmg", "__pycache__/"]


def test_load_patterns_strips_whitespace(tmp_path: Path) -> None:
    f = tmp_path / "ignore"
    f.write_text("  *.log  \n  node_modules/  ")
    assert m.load_patterns(f) == ["*.log", "node_modules/"]


def test_matches_any_name_only(tmp_path: Path) -> None:
    root = tmp_path / "Dropbox"
    root.mkdir()
    path = root / "foo.dmg"
    path.touch()
    assert m.matches_any(path, ["*.dmg"], root) is True
    assert m.matches_any(path, ["*.zip"], root) is False


def test_matches_any_relative_path(tmp_path: Path) -> None:
    root = tmp_path / "Dropbox"
    (root / "a" / "b").mkdir(parents=True)
    path = root / "a" / "b" / "file.log"
    path.touch()
    assert m.matches_any(path, ["a/b/file.log"], root) is True
    assert m.matches_any(path, ["*.log"], root) is True


def test_top_level_only_excludes_children(tmp_path: Path) -> None:
    root = tmp_path
    p1 = root / "node_modules"
    p2 = root / "node_modules" / "foo"
    p3 = root / "node_modules" / "foo" / "bar"
    matches = [p1, p2, p3]
    out = m._top_level_only(matches)
    assert out == [p1]


def test_top_level_only_keeps_siblings(tmp_path: Path) -> None:
    root = tmp_path
    a = root / "a"
    b = root / "b"
    out = m._top_level_only([a, b])
    assert set(out) == {a, b}


def test_under_dropbox_system_root_level(tmp_path: Path) -> None:
    root = tmp_path
    assert m._under_dropbox_system(root / ".dropbox", root) is True
    assert m._under_dropbox_system(root / ".dropbox.cache", root) is True
    assert m._under_dropbox_system(root / "other", root) is False


def test_under_dropbox_system_nested(tmp_path: Path) -> None:
    root = tmp_path
    assert m._under_dropbox_system(root / ".dropbox" / "file", root) is True
    assert m._under_dropbox_system(root / "foo" / ".dropbox", root) is False


def test_format_size() -> None:
    assert m.format_size(0) == "0.0 B"
    assert m.format_size(500) == "500.0 B"
    assert m.format_size(1024) == "1.0 KB"
    assert m.format_size(1536) == "1.5 KB"
    assert m.format_size(1024 * 1024) == "1.0 MB"
    assert m.format_size(1024 * 1024 * 1024) == "1.0 GB"


def test_is_mac_alias_non_file(tmp_path: Path) -> None:
    d = tmp_path / "dir"
    d.mkdir()
    assert m._is_mac_alias(d) is False


def test_is_mac_alias_large_file(tmp_path: Path) -> None:
    f = tmp_path / "big"
    f.write_bytes(b"book" + b"x" * 2000)
    assert m._is_mac_alias(f) is False


def test_is_mac_alias_small_book_magic(tmp_path: Path) -> None:
    f = tmp_path / "alias"
    f.write_bytes(b"book" + b"rest")
    if sys.platform == "darwin":
        assert m._is_mac_alias(f) is True
    else:
        assert m._is_mac_alias(f) is False


def test_collect_matches_finds_top_level_only(tmp_path: Path) -> None:
    root = tmp_path / "Dropbox"
    root.mkdir()
    (root / "node_modules").mkdir()
    (root / "node_modules" / "pkg").mkdir()
    (root / "node_modules" / "pkg" / "file.js").write_text("x")
    patterns = ["node_modules"]
    matches = m.collect_matches(root, patterns)
    assert len(matches) == 1
    assert matches[0] == root / "node_modules"


def test_collect_matches_skips_dropbox_system(tmp_path: Path) -> None:
    root = tmp_path / "Dropbox"
    root.mkdir()
    (root / ".dropbox").mkdir()
    (root / ".dropbox" / "x").write_text("y")
    patterns = ["*"]
    matches = m.collect_matches(root, patterns)
    dropbox_paths = [p for p in matches if ".dropbox" in str(p)]
    assert len(dropbox_paths) == 0


def test_collect_matches_skips_never_clean_names(tmp_path: Path) -> None:
    root = tmp_path / "Dropbox"
    root.mkdir()
    (root / ".DS_Store").write_text("x")
    patterns = ["*"]
    matches = m.collect_matches(root, patterns)
    assert not any(p.name == ".DS_Store" for p in matches)


def test_collect_matches_respects_exclude_config_basename(tmp_path: Path) -> None:
    root = tmp_path / "Dropbox"
    root.mkdir()
    (root / "Perry-HR-2022.dmg").write_text("x")
    (root / "other.dmg").write_text("y")
    patterns = ["*.dmg"]
    exclude_file = tmp_path / "exclude.txt"
    exclude_file.write_text("Perry-HR-2022.dmg\n")
    full_set, basename_set = m.load_exclude_config(exclude_file)
    matches = m.collect_matches(root, patterns, exclude_full=full_set, exclude_basename=basename_set)
    names = [p.name for p in matches]
    assert "Perry-HR-2022.dmg" not in names
    assert "other.dmg" in names


def test_collect_matches_respects_exclude_config_full_path(tmp_path: Path) -> None:
    root = tmp_path / "Dropbox"
    root.mkdir()
    (root / "HR").mkdir()
    (root / "HR" / "keep.dmg").write_text("x")
    (root / "HR" / "remove.dmg").write_text("y")
    patterns = ["*.dmg"]
    exclude_file = tmp_path / "exclude.txt"
    exclude_file.write_text("HR/keep.dmg\n")
    full_set, basename_set = m.load_exclude_config(exclude_file)
    matches = m.collect_matches(root, patterns, exclude_full=full_set, exclude_basename=basename_set)
    rels = [str(p.relative_to(root)) for p in matches]
    assert "HR/keep.dmg" not in rels
    assert "HR/remove.dmg" in rels


def test_load_exclude_config(tmp_path: Path) -> None:
    f = tmp_path / "exclude.txt"
    f.write_text("# comment\n\n  \nPerry-HR-2022.dmg\nHR/keep.dmg\n  \n")
    full_set, basename_set = m.load_exclude_config(f)
    assert basename_set == {"Perry-HR-2022.dmg"}
    assert full_set == {"HR/keep.dmg"}


def test_write_log_dry_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_write_log appends header, item lines, and dry-run summary to log file."""
    root = tmp_path / "Dropbox"
    root.mkdir()
    log_file = tmp_path / "clean_dropbox.log"
    (root / "foo.dmg").write_text("x")
    match_path = root / "foo.dmg"
    monkeypatch.setattr(m, "LOG_FILE", log_file)
    monkeypatch.setattr(m, "DROPBOX_ROOT", root)
    m._write_log("dry-run", [match_path], 1)
    content = log_file.read_text(encoding="utf-8")
    assert content.startswith("--- ")
    assert " mode=dry-run" in content
    assert "foo.dmg" in content
    assert "  summary: 1 items, 1.0 B" in content


def test_write_log_aborted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_write_log includes (aborted by user) when aborted=True."""
    root = tmp_path / "Dropbox"
    root.mkdir()
    log_file = tmp_path / "clean_dropbox.log"
    (root / "a.dmg").write_text("a")
    monkeypatch.setattr(m, "LOG_FILE", log_file)
    monkeypatch.setattr(m, "DROPBOX_ROOT", root)
    m._write_log("move", [root / "a.dmg"], 1, aborted=True)
    assert "  (aborted by user)" in log_file.read_text(encoding="utf-8")


def test_write_log_move_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_write_log includes move summary when moved/move_failed provided."""
    root = tmp_path / "Dropbox"
    root.mkdir()
    log_file = tmp_path / "clean_dropbox.log"
    monkeypatch.setattr(m, "LOG_FILE", log_file)
    monkeypatch.setattr(m, "DROPBOX_ROOT", root)
    m._write_log("move", [], 0, moved=2, move_failed=1)
    assert "  summary: moved 2 to " in log_file.read_text(encoding="utf-8")
    assert "failed 1" in log_file.read_text(encoding="utf-8")


def test_write_log_delete_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_write_log includes delete summary when deleted/delete_failed provided."""
    root = tmp_path / "Dropbox"
    root.mkdir()
    log_file = tmp_path / "clean_dropbox.log"
    monkeypatch.setattr(m, "LOG_FILE", log_file)
    monkeypatch.setattr(m, "DROPBOX_ROOT", root)
    m._write_log("delete", [], 0, deleted=3, delete_failed=0)
    assert "  summary: deleted 3, failed 0" in log_file.read_text(encoding="utf-8")


def test_write_log_only_pattern_in_header(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_write_log includes only_pattern in header when provided."""
    root = tmp_path / "Dropbox"
    root.mkdir()
    log_file = tmp_path / "clean_dropbox.log"
    monkeypatch.setattr(m, "LOG_FILE", log_file)
    monkeypatch.setattr(m, "DROPBOX_ROOT", root)
    m._write_log("dry-run", [], 0, only_pattern="*.dmg")
    assert " only_pattern='*.dmg'" in log_file.read_text(encoding="utf-8")


def test_run_dry_run_with_matches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """run() in dry-run mode with matches writes log and includes summary."""
    root = tmp_path / "Dropbox"
    root.mkdir()
    ignore_file = tmp_path / "rules.dropboxignore"
    ignore_file.write_text("*.dmg\n", encoding="utf-8")
    exclude_file = tmp_path / "exclude.txt"
    exclude_file.write_text("", encoding="utf-8")
    log_file = tmp_path / "clean_dropbox.log"
    (root / "test.dmg").write_text("x")
    monkeypatch.setattr(m, "DROPBOX_ROOT", root)
    monkeypatch.setattr(m, "IGNORE_FILE", ignore_file)
    monkeypatch.setattr(m, "EXCLUDE_CONFIG_FILE", exclude_file)
    monkeypatch.setattr(m, "LOG_FILE", log_file)
    m.run("dry-run", only_pattern=None)
    content = log_file.read_text(encoding="utf-8")
    assert "test.dmg" in content
    assert " mode=dry-run" in content
    assert "summary:" in content


def test_run_dry_run_no_matches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """run() in dry-run mode with no matches does not write log."""
    root = tmp_path / "Dropbox"
    root.mkdir()
    ignore_file = tmp_path / "rules.dropboxignore"
    ignore_file.write_text("*.zip\n", encoding="utf-8")
    exclude_file = tmp_path / "exclude.txt"
    exclude_file.write_text("", encoding="utf-8")
    log_file = tmp_path / "clean_dropbox.log"
    (root / "test.dmg").write_text("x")
    monkeypatch.setattr(m, "DROPBOX_ROOT", root)
    monkeypatch.setattr(m, "IGNORE_FILE", ignore_file)
    monkeypatch.setattr(m, "EXCLUDE_CONFIG_FILE", exclude_file)
    monkeypatch.setattr(m, "LOG_FILE", log_file)
    m.run("dry-run", only_pattern=None)
    assert not log_file.exists()
