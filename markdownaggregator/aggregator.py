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


def first_h1(markdown: str) -> str | None:
    match = HEADING_RE.search(markdown)
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


def extract_includes(markdown: str) -> List[str]:
    """Return every ``@include`` path declared via HTML comments in *markdown*."""
    return [match.group(1) for match in INCLUDE_RE.finditer(markdown)]


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


def process_includes(files: List[Path], root: Path) -> List[Path]:
    processed: List[Path] = []
    seen: set[Path] = set()

    def process_file(file_path: Path) -> None:
        """Depth-first include expansion with cycle detection via *seen*."""
        if file_path in seen:
            return
        seen.add(file_path)

        if not file_path.exists():
            logger.warning("Include target missing: %s", file_path)
            return

        content = read_text(file_path)
        include_paths = extract_includes(content)

        for include_path in include_paths:
            resolved_path = resolve_include_path(include_path, file_path, root)
            if resolved_path and resolved_path not in seen:
                process_file(resolved_path)

        processed.append(file_path)

    for path in files:
        process_file(path)

    return processed


def build_toc(entries: Sequence[Tuple[str, str]]) -> str:
    buffer = io.StringIO()
    buffer.write("# Table of contents\n\n")
    for title, anchor in entries:
        buffer.write(f"- [{title}](#{anchor})\n")
    buffer.write("\n")
    return buffer.getvalue()


def aggregate(
    files: Sequence[Path],
    *,
    strip_yaml: bool,
    separator: str,
    root: Path,
) -> str:
    toc_entries: List[Tuple[str, str]] = []
    parts: List[str] = []

    for path in files:
        markdown = read_text(path)
        if strip_yaml:
            markdown = strip_frontmatter(markdown)

        title = first_h1(markdown) or path.stem.replace("_", " ").replace("-", " ").title()
        anchor = slugify(title)

        header = f'<a id="{anchor}"></a>\n\n# {title}\n'
        if markdown.lstrip().startswith("# "):
            markdown = HEADING_RE.sub("", markdown, count=1).lstrip()

        relative = path.relative_to(root)
        parts.append(f"<!-- Source: {relative} -->\n{header}\n{markdown.strip()}\n")

        toc_entries.append((title, anchor))
        if separator:
            parts.append(f"\n{separator}\n")

    if parts and separator and parts[-1].strip() == separator.strip():
        parts.pop()

    toc = build_toc(toc_entries)
    return toc + "\n".join(parts).rstrip() + "\n"


def aggregate_markdown(
    root: Path,
    *,
    manifest: Path | None = None,
    ignore: Iterable[str] | None = None,
    separator: str = "---",
    strip_frontmatter_from_files: bool = False,
    hybrid_mode: bool = False,
    process_includes_flag: bool = False,
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

    ignore_patterns = list(ignore or [])
    discovered_files: List[Path] = []
    if manifest is None or hybrid_mode:
        discovered_files = discover_files(root, ignore_patterns)

    if hybrid_mode and manifest is not None:
        files = smart_merge_files(discovered_files, manifest_files)
        # Mirror CLI behaviour and emit information logs that can be surfaced to users.
        logger.info(
            "Hybrid mode: %d files from manifest, %d discovered, %d total",
            len(manifest_files),
            len(discovered_files),
            len(files),
        )
    elif manifest is not None:
        files = manifest_files
    else:
        files = discovered_files

    if process_includes_flag:
        files = process_includes(list(files), root)
        logger.info("Processed @include directives: %d files after processing", len(files))

    if not files:
        raise ValueError("No Markdown files found.")

    merged = aggregate(
        # ``separator`` may be None (legacy), so normalize to an empty string for clarity.
        files,
        strip_yaml=strip_frontmatter_from_files,
        separator="" if separator is None else separator,
        root=root,
    )

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(merged, encoding="utf-8")

    return merged
