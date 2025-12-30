"""Core aggregation logic for merging Markdown sources into a single document."""
from __future__ import annotations

import fnmatch
import io
import logging
import re
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

HEADING_RE = re.compile(r"^\s{0,3}#\s+(.+?)\s*#*\s*$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"(?s)\A---\s*\n.*?\n---\s*\n")
INCLUDE_RE = re.compile(r"<!--\s*@include:\s*([^>\s]+)\s*-->", re.MULTILINE)


def slugify(text: str) -> str:
    """Convert arbitrary text to a slug suitable for Markdown anchors."""
    cleaned = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    return re.sub(r"[\s_-]+", "-", cleaned)


def read_text(path: Path) -> str:
    """
    Return the textual contents of *path*, trying a couple of encodings before falling
    back to a more permissive UTF-8 decode.
    """
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except Exception:  # pragma: no cover - defensive
            continue
    return path.read_bytes().decode("utf-8", errors="replace")


def leading_h1(markdown: str) -> str | None:
    """Return the first H1 title only if it appears at the very start of the document.

    We intentionally *do not* scan the whole document because inline includes may
    introduce headings later on; those should not be treated as the file title.
    """

    stripped = markdown.lstrip()
    if not stripped.startswith("# "):
        return None
    match = HEADING_RE.match(stripped)
    return match.group(1).strip() if match else None


def strip_frontmatter(markdown: str) -> str:
    return FRONTMATTER_RE.sub("", markdown, count=1)


def discover_files(root: Path, ignore: Sequence[str]) -> List[Path]:
    """
    Recursively walk *root* and collect Markdown files while honoring glob ignore patterns.
    Files are returned sorted case-insensitively for stable output.
    """
    files: List[Path] = []
    for path in root.rglob("*.md"):
        relative = path.relative_to(root)
        if any(fnmatch.fnmatch(str(relative), pattern) or fnmatch.fnmatch(path.name, pattern) for pattern in ignore):
            continue
        files.append(path)
    files.sort(key=lambda x: str(x).lower())
    return files


def read_manifest(manifest: Path, root: Path) -> List[Path]:
    """
    Parse a manifest file listing Markdown paths (or directories) in the desired order.
    Inline comments introduced with `` #`` are ignored. Directories are expanded recursively.
    """
    entries: List[Path] = []
    for raw_line in read_text(manifest).splitlines():
        # Allow blank lines and comment lines for readability in the manifest.
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if " #" in line:
            line = line.split(" #", 1)[0].rstrip()

        candidate = (root / line).resolve()
        # Resolve entries relative to the root and ensure they exist before proceeding.
        if not candidate.exists():
            raise FileNotFoundError(f"Manifest entry not found: {line}")

        if candidate.is_dir():
            entries.extend(sorted(candidate.rglob("*.md")))
        else:
            entries.append(candidate)

    seen: set[Path] = set()
    # Preserve manifest ordering while removing duplicates.
    unique_entries: List[Path] = []
    for path in entries:
        if path not in seen:
            unique_entries.append(path)
            seen.add(path)
    return unique_entries


def smart_merge_files(discovered_files: List[Path], manifest_files: List[Path]) -> List[Path]:
    """
    Combine manifest priority files and auto-discovered files without duplication.
    Manifest entries always keep their relative order; discovery only fills the gaps.
    """
    manifest_set = set(manifest_files)
    result: List[Path] = []

    for file_path in manifest_files:
        if file_path not in result:
            result.append(file_path)

    for file_path in discovered_files:
        if file_path not in manifest_set and file_path not in result:
            result.append(file_path)

    return result


def resolve_include_path(include_path: str, current_file: Path, root: Path) -> Path | None:
    candidates = [
        current_file.parent / include_path,
        root / include_path,
        Path(include_path),
    ]

    for candidate in candidates:
        # Stop at the first match that exists on disk to avoid surprising overrides.
        resolved = candidate.resolve()
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def build_toc(entries: Sequence[Tuple[str, str]]) -> str:
    buffer = io.StringIO()
    buffer.write("# Table of contents\n\n")
    for title, anchor in entries:
        buffer.write(f"- [{title}](#{anchor})\n")
    buffer.write("\n")
    return buffer.getvalue()


HEADING_LINE_RE = re.compile(r"^#{1,6}\s+.+?$", re.MULTILINE)


def shift_heading_levels(content: str, delta: int) -> str:
    """Shift every Markdown heading level by *delta*.

    - Positive delta increases heading depth (e.g. 1 => '#' -> '##').
    - Negative delta decreases heading depth.

    Heading levels are clamped to the Markdown range 1..6.
    """

    if delta == 0:
        return content

    def shift(match: re.Match) -> str:
        line = match.group(0)
        hash_count = len(line) - len(line.lstrip("#"))
        new_hash_count = min(max(hash_count + delta, 1), 6)
        return "#" * new_hash_count + line[hash_count:]

    return HEADING_LINE_RE.sub(shift, content)


def min_heading_level(markdown: str) -> int | None:
    """Return the minimal heading level (1..6) found in *markdown*, or None."""

    levels: list[int] = []
    for line in markdown.splitlines():
        if not line.startswith("#"):
            continue
        # Fast path: only consider actual ATX headings.
        if re.match(r"^#{1,6}\s+", line):
            levels.append(len(line) - len(line.lstrip("#")))
    return min(levels) if levels else None


def last_heading_level_before(markdown: str, offset: int) -> int | None:
    """Return the heading level of the last ATX heading before *offset*, or None."""

    prefix = markdown[:offset]
    matches = list(re.finditer(r"^#{1,6}\s+.+?$", prefix, flags=re.MULTILINE))
    if not matches:
        return None
    last = matches[-1].group(0)
    return len(last) - len(last.lstrip("#"))


def resolve_includes_in_content(
    content: str,
    current_file: Path,
    root: Path,
    seen: set[Path] | None = None,
    strip_yaml: bool = False,
) -> str:
    """
    Recursively replace <!-- @include: path.md --> directives with the actual content
    of the referenced files. Handles nested includes and cycle detection.
    
    Parameters
    ----------
    content:
        The Markdown content to process.
    current_file:
        The path to the file being processed.
    root:
        The root directory for resolving relative paths.
    seen:
        Set of already processed files for cycle detection.
    strip_yaml:
        Whether to strip YAML frontmatter from included files.
    """
    if seen is None:
        seen = set()
    
    seen.add(current_file)
    
    def replace_include(match: re.Match) -> str:
        include_path = match.group(1)
        resolved_path = resolve_include_path(include_path, current_file, root)

        if resolved_path is None:
            logger.warning("Include target not found: %s (referenced from %s)", include_path, current_file)
            return f"<!-- @include: {include_path} (NOT FOUND) -->"

        if resolved_path in seen:
            logger.warning("Circular include detected: %s", resolved_path)
            return f"<!-- @include: {include_path} (CIRCULAR REFERENCE) -->"

        parent_level = last_heading_level_before(content, match.start())
        # If we include at the top of a document (no heading found above), treat it as "level 0"
        # so included content can start at H1.
        if parent_level is None:
            parent_level = 0

        # Read the included file content
        included_content = read_text(resolved_path)

        # Strip frontmatter if requested
        if strip_yaml:
            included_content = strip_frontmatter(included_content)

        # Recursively resolve includes in the included content
        included_content = resolve_includes_in_content(
            included_content,
            resolved_path,
            root,
            seen.copy(),  # Use a copy to allow the same file to be included in different branches
            strip_yaml,
        )

        # Rebase included headings so that the shallowest heading becomes (parent_level + 1).
        included_min = min_heading_level(included_content)
        if included_min is not None:
            target_level = min(parent_level + 1, 6)
            delta = target_level - included_min
            included_content = shift_heading_levels(included_content, delta)

        return included_content.strip()
    
    # Replace all @include directives in the content
    return INCLUDE_RE.sub(replace_include, content)


def aggregate(
    files: Sequence[Path],
    *,
    strip_yaml: bool,
    separator: str,
    root: Path,
    process_includes_inline: bool = False,
    include_toc: bool = False,
    auto_file_title: bool = True,
) -> str:
    toc_entries: List[Tuple[str, str]] = []
    parts: List[str] = []

    for path in files:
        markdown = read_text(path)
        if strip_yaml:
            markdown = strip_frontmatter(markdown)

        # Process @include directives inline if requested
        if process_includes_inline:
            markdown = resolve_includes_in_content(
                markdown,
                path,
                root,
                strip_yaml=strip_yaml,
            )

        detected_h1 = leading_h1(markdown)
        title: str | None
        if detected_h1 is not None:
            title = detected_h1
        elif auto_file_title:
            title = path.stem.replace("_", " ").replace("-", " ").title()
        else:
            title = None

        header = ""
        if title is not None:
            anchor = slugify(title)
            header = f'<a id="{anchor}"></a>\n\n# {title}\n'

        if detected_h1 is not None and markdown.lstrip().startswith("# "):
            markdown = HEADING_RE.sub("", markdown, count=1).lstrip()

        relative = path.relative_to(root)
        parts.append(f"<!-- Source: {relative} -->\n{header}\n{markdown.strip()}\n")

        if include_toc and title is not None:
            toc_entries.append((title, slugify(title)))
        if separator:
            parts.append(f"\n{separator}\n")

    if parts and separator and parts[-1].strip() == separator.strip():
        parts.pop()

    body = "\n".join(parts).rstrip() + "\n"
    if include_toc:
        toc = build_toc(toc_entries)
        return toc + body
    return body


def aggregate_markdown(
    root: Path,
    *,
    manifest: Path | None = None,
    direct_files: Iterable[Path] | None = None,
    ignore: Iterable[str] | None = None,
    separator: str = "---",
    strip_frontmatter_from_files: bool = False,
    hybrid_mode: bool = False,
    process_includes_flag: bool = False,
    include_toc: bool = False,
    auto_file_title: bool = True,
    output: Path | None = None,
) -> str:
    """
    Aggregate Markdown files under *root* into a single document.

    Parameters
    ----------
    root:
        Root directory that contains Markdown files.
    manifest:
        Optional text file listing entries (files or directories) to process in order.
    direct_files:
        Optional iterable of Markdown file paths to process directly (treated as manifest entries).
    ignore:
        Iterable of glob patterns to skip during auto-discovery.
    separator:
        Text inserted between concatenated files. Use an empty string to disable.
    strip_frontmatter_from_files:
        Remove leading YAML front matter blocks when enabled.
    hybrid_mode:
        Combine manifest order with auto-discovery for missing files.
    process_includes_flag:
        Follow <!-- @include: path.md --> directives recursively.
    output:
        Optional path where the aggregated Markdown should be written.

    Returns
    -------
    str
        The aggregated Markdown content.
    """
    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Root not found: {root}")

    manifest_files: List[Path] = []
    if manifest is not None:
        manifest_files = read_manifest(manifest.resolve(), root)
    
    # Add direct files to manifest_files with priority
    if direct_files is not None:
        direct_file_list = [f.resolve() for f in direct_files]
        # Prepend direct files to manifest files (direct files have priority)
        manifest_files = direct_file_list + manifest_files

    ignore_patterns = list(ignore or [])
    discovered_files: List[Path] = []
    if (manifest is None and direct_files is None) or hybrid_mode:
        discovered_files = discover_files(root, ignore_patterns)

    if hybrid_mode and (manifest is not None or direct_files is not None):
        files = smart_merge_files(discovered_files, manifest_files)
        # Mirror CLI behaviour and emit information logs that can be surfaced to users.
        logger.info(
            "Hybrid mode: %d files from manifest/direct, %d discovered, %d total",
            len(manifest_files),
            len(discovered_files),
            len(files),
        )
    elif manifest is not None or direct_files is not None:
        files = manifest_files
    else:
        files = discovered_files


    if not files:
        raise ValueError("No Markdown files found.")

    merged = aggregate(
        # ``separator`` may be None (legacy), so normalize to an empty string for clarity.
        files,
        strip_yaml=strip_frontmatter_from_files,
        separator="" if separator is None else separator,
        root=root,
        process_includes_inline=process_includes_flag,
        include_toc=include_toc,
        auto_file_title=auto_file_title,
    )

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(merged, encoding="utf-8")

    return merged
