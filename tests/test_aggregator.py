"""Integration-style tests covering discovery, manifest handling, includes, and CLI output."""
from __future__ import annotations

from pathlib import Path

import pytest

from markdownaggregator import aggregate_markdown
from markdownaggregator import aggregator as aggregator_module
from markdownaggregator.cli import run_cli


def test_discover_files_respects_ignore(tmp_path: Path) -> None:
    """The discovery helper should filter out ignored patterns while keeping others."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# A", encoding="utf-8")
    (docs / "b.md").write_text("# B", encoding="utf-8")
    (docs / "README.txt").write_text("ignored", encoding="utf-8")

    files = aggregator_module.discover_files(docs, ignore=["b.md"])
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

    entries = aggregator_module.read_manifest(manifest, root)
    assert entries == [
        docs / "intro.md",
        guide / "part1.md",
        guide / "part2.md",
    ]


def test_inline_includes_rebase_heading_levels(tmp_path: Path) -> None:
    """Included files should have their headings rebased to follow the parent heading."""

    root = tmp_path / "docs"
    root.mkdir()

    # Parent: include under an H2
    (root / "parent.md").write_text(
        "# chapitre 1\n"
        "## sous chapitre 1.1\n"
        "<!-- @include: fichierA.md -->\n",
        encoding="utf-8",
    )

    # Case 1: included file already starts at H2/H3 -> should become H3/H4
    (root / "fichierA.md").write_text(
        "## chapitre A\n"
        "### chapitre A.1\n",
        encoding="utf-8",
    )

    manifest = root / "manifest.txt"
    manifest.write_text("parent.md\n", encoding="utf-8")

    merged = aggregate_markdown(
        root=root,
        manifest=manifest,
        process_includes_flag=True,
    )

    assert "## sous chapitre 1.1" in merged
    assert "### chapitre A" in merged
    assert "#### chapitre A.1" in merged

    # Case 2: included file starts at H1/H2 -> should still become H3/H4
    (root / "fichierA.md").write_text(
        "# chapitre A\n"
        "## chapitre A.1\n",
        encoding="utf-8",
    )

    merged2 = aggregate_markdown(
        root=root,
        manifest=manifest,
        process_includes_flag=True,
    )

    assert "### chapitre A" in merged2
    assert "#### chapitre A.1" in merged2


def test_inline_includes_at_top_level_start_at_h1(tmp_path: Path) -> None:
    """If an include appears before any heading, included content should start at H1."""

    root = tmp_path / "docs"
    root.mkdir()

    (root / "parent.md").write_text(
        "<!-- @include: fichierA.md -->\n"
        "# chapitre 1\n"
        "<!-- @include: fichierB.md -->\n",
        encoding="utf-8",
    )

    (root / "fichierA.md").write_text(
        "## chapitre A\n"
        "### chapitre A.1\n",
        encoding="utf-8",
    )

    (root / "fichierB.md").write_text(
        "### chapitre B\n"
        "#### chapitre B.1\n",
        encoding="utf-8",
    )

    manifest = root / "manifest.txt"
    manifest.write_text("parent.md\n", encoding="utf-8")

    merged = aggregate_markdown(
        root=root,
        manifest=manifest,
        process_includes_flag=True,
        auto_file_title=False,
        separator="",
    )

    # First include: rebased to H1/H2
    assert "# chapitre A" in merged
    assert "## chapitre A.1" in merged

    # Second include: after an H1, rebased to H2/H3
    assert "## chapitre B" in merged
    assert "### chapitre B.1" in merged


def test_aggregate_markdown_default_has_no_toc_and_writes_output(tmp_path: Path) -> None:
    """Aggregating files should *not* include a TOC by default and optionally persist to disk."""
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

    assert "# Table of contents" not in merged
    assert '<a id="intro"></a>' in merged
    assert "<!-- Source: intro.md -->" in merged
    assert output.exists()
    written = output.read_text(encoding="utf-8")
    assert written == merged


def test_aggregate_markdown_can_include_toc(tmp_path: Path) -> None:
    """Aggregating files can prepend a TOC when include_toc=True."""
    root = tmp_path / "docs"
    root.mkdir()
    (root / "intro.md").write_text("# Intro\n\nContent", encoding="utf-8")
    (root / "chapter.md").write_text("# Chapter\n\nMore content", encoding="utf-8")

    merged = aggregate_markdown(
        root=root,
        separator="---",
        include_toc=True,
    )

    assert "# Table of contents" in merged


def test_aggregate_markdown_can_disable_auto_file_title(tmp_path: Path) -> None:
    """When auto_file_title is disabled, files without H1 should not get an injected title."""

    root = tmp_path / "docs"
    root.mkdir()
    (root / "no_title.md").write_text("Just some text\n\n## Sub\n", encoding="utf-8")

    merged = aggregate_markdown(
        root=root,
        separator="",
        auto_file_title=False,
    )

    assert "# No Title" not in merged
    assert "## Sub" in merged


def test_parent_free_text_does_not_get_header_from_included_h1(tmp_path: Path) -> None:
    """Free text at the top of a parent file must not get a generated header from an include."""

    root = tmp_path / "docs"
    root.mkdir()

    (root / "parent.md").write_text(
        "Blah, Blah\n"
        "Blah\n\n"
        "<!-- @include: fichierA.md -->\n",
        encoding="utf-8",
    )

    (root / "fichierA.md").write_text(
        "## chapitre A\n"
        "### chapitre A.1\n",
        encoding="utf-8",
    )

    manifest = root / "manifest.txt"
    manifest.write_text("parent.md\n", encoding="utf-8")

    merged = aggregate_markdown(
        root=root,
        manifest=manifest,
        process_includes_flag=True,
        auto_file_title=False,
        separator="",
    )

    # The free text remains at the top.
    assert merged.lstrip().startswith("<!-- Source: parent.md -->\n\nBlah, Blah")
    # Included content is present and rebased to H1.
    assert "# chapitre A" in merged
    assert "## chapitre A.1" in merged


def test_aggregate_markdown_toc_skips_files_without_title(tmp_path: Path) -> None:
    """TOC should not contain entries for files without a usable title when auto titles are disabled."""

    root = tmp_path / "docs"
    root.mkdir()
    (root / "no_title.md").write_text("Just some text\n\n## Sub\n", encoding="utf-8")

    merged = aggregate_markdown(
        root=root,
        separator="",
        include_toc=True,
        auto_file_title=False,
    )

    assert "# Table of contents" in merged
    # No TOC bullet for this file.
    assert "- [No Title](#no-title)" not in merged


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
        include_toc=False,
        auto_file_title=True,
        output=None,
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "# Table of contents" not in captured.out


def test_cli_run_with_toc(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Smoke test: the CLI can output a TOC when requested."""
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
        include_toc=True,
        auto_file_title=True,
        output=None,
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "# Table of contents" in captured.out
