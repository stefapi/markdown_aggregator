"""Integration-style tests covering discovery, manifest handling, includes, and CLI output."""
from __future__ import annotations

from pathlib import Path

import pytest

from markdownaggregator import aggregate_markdown
from markdownaggregator import aggregator
from markdownaggregator.cli import run_cli


def test_discover_files_respects_ignore(tmp_path: Path) -> None:
    """The discovery helper should filter out ignored patterns while keeping others."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# A", encoding="utf-8")
    (docs / "b.md").write_text("# B", encoding="utf-8")
    (docs / "README.txt").write_text("ignored", encoding="utf-8")

    files = aggregator.discover_files(docs, ignore=["b.md"])
    assert [f.name for f in files] == ["a.md"]


def test_read_manifest_handles_directories(tmp_path: Path) -> None:
    """Manifests can mix files, directories, and inline comments without duplication."""
    root = tmp_path / "project"
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "intro.md").write_text("# Intro", encoding="utf-8")
    guide = docs / "guide"
    guide.mkdir()
    (guide / "part1.md").write_text("# Part 1", encoding="utf-8")
    (guide / "part2.md").write_text("# Part 2", encoding="utf-8")

    manifest = root / "manifest.txt"
    manifest.write_text(
        "docs/intro.md\n"
        "docs/guide\n"
        "docs/guide/part1.md # duplicate ignored\n",
        encoding="utf-8",
    )

    entries = aggregator.read_manifest(manifest, root)
    assert entries == [
        docs / "intro.md",
        guide / "part1.md",
        guide / "part2.md",
    ]


def test_process_includes_resolves_recursively(tmp_path: Path) -> None:
    """Recursive include resolution should visit nested dependencies exactly once."""
    root = tmp_path / "docs"
    root.mkdir()
    (root / "main.md").write_text(
        "# Main\n\n<!-- @include: section.md -->\n",
        encoding="utf-8",
    )
    (root / "section.md").write_text(
        "# Section\n\n<!-- @include: appendix.md -->\n",
        encoding="utf-8",
    )
    (root / "appendix.md").write_text("# Appendix", encoding="utf-8")

    files = aggregator.process_includes([root / "main.md"], root)
    assert files == [
        root / "appendix.md",
        root / "section.md",
        root / "main.md",
    ]


def test_aggregate_markdown_creates_toc_and_writes_output(tmp_path: Path) -> None:
    """Aggregating files should yield a TOC and optionally persist to disk."""
    root = tmp_path / "docs"
    root.mkdir()
    (root / "intro.md").write_text("# Intro\n\nContent", encoding="utf-8")
    (root / "chapter.md").write_text("# Chapter\n\nMore content", encoding="utf-8")

    output = tmp_path / "out.md"
    merged = aggregate_markdown(
        root=root,
        separator="---",
        output=output,
    )

    assert "# Table of contents" in merged
    assert '<a id="intro"></a>' in merged
    assert "<!-- Source: intro.md -->" in merged
    assert output.exists()
    written = output.read_text(encoding="utf-8")
    assert written == merged


def test_cli_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Smoke test the CLI code path to ensure argument plumbing works."""
    root = tmp_path / "docs"
    root.mkdir()
    (root / "index.md").write_text("# Index", encoding="utf-8")

    exit_code = run_cli(
        root=root,
        manifest=None,
        ignore=[],
        separator="---",
        strip_frontmatter=False,
        hybrid_mode=False,
        process_includes=False,
        output=None,
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "# Table of contents" in captured.out
