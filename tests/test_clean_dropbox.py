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
