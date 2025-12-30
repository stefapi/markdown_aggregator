"""Command-line interface wiring for markdownaggregator."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Iterable

from .aggregator import aggregate_markdown

LOG_LEVELS = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level argparse parser with every supported CLI flag."""
    parser = argparse.ArgumentParser(
        # Keep the user-facing description concise; detailed documentation lives in README/docs.
        prog="markdownaggregator",
        description="Aggregate a tree (or manifest) of Markdown files into one Markdown document.",
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Root directory containing Markdown files (default: .)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write aggregated Markdown to this file (defaults to stdout).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Optional manifest listing files/directories in order (relative to root).",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Glob pattern to ignore (repeatable).",
    )
    parser.add_argument(
        "--no-separator",
        action="store_true",
        help="Disable insertion of separators between files.",
    )
    parser.add_argument(
        "--separator",
        default="---",
        help="Separator text between files (default: ---).",
    )
    parser.add_argument(
        "--strip-frontmatter",
        action="store_true",
        help="Strip YAML front matter from each file before aggregation.",
    )
    parser.add_argument(
        "--hybrid-mode",
        action="store_true",
        help="Combine manifest ordering with discovery while avoiding duplicates.",
    )
    parser.add_argument(
        "--process-includes",
        action="store_true",
        help="Resolve <!-- @include: path.md --> directives recursively.",
    )
    parser.add_argument(
        "--toc",
        action="store_true",
        help="Prepend a generated table of contents.",
    )
    parser.add_argument(
        "--no-auto-file-title",
        action="store_true",
        help="Do not inject a top-level '# <File Name>' heading when a file has no H1.",
    )
    parser.add_argument(
        "--log-level",
        choices=LOG_LEVELS,
        default="WARNING",
        help="Logging level (default: WARNING).",
    )
    return parser


def configure_logging(level: str) -> None:
    """Install a basic logging configuration for the CLI process."""
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(levelname)s:%(name)s:%(message)s",
    )


def run_cli(
    # Using keyword-only parameters simplifies the main() hand-off and keeps parity with aggregate_markdown.
    root: Path,
    *,
    manifest: Path | None,
    ignore: Iterable[str],
    separator: str,
    strip_frontmatter: bool,
    hybrid_mode: bool,
    process_includes: bool,
    include_toc: bool,
    auto_file_title: bool,
    output: Path | None,
) -> int:
    try:
        # Detect if root is a .md file instead of a directory
        direct_files: list[Path] | None = None
        actual_root = root
        
        if root.is_file() and root.suffix.lower() == ".md":
            # If root is a .md file, use its parent as root and treat it as a direct file
            direct_files = [root]
            actual_root = root.parent
            logging.getLogger(__name__).info("Treating %s as direct file with root %s", root, actual_root)
        
        # Execute the aggregation workflow and surface any Python exception as a CLI error.
        aggregated = aggregate_markdown(
            root=actual_root,
            manifest=manifest,
            direct_files=direct_files,
            ignore=ignore,
            separator=separator,
            strip_frontmatter_from_files=strip_frontmatter,
            hybrid_mode=hybrid_mode,
            process_includes_flag=process_includes,
            include_toc=include_toc,
            auto_file_title=auto_file_title,
            output=output,
        )
    except Exception as exc:  # pragma: no cover - CLI safety
        logging.getLogger(__name__).error("%s", exc)
        return 1

    if output is None:
        # When no output file is specified, stream the aggregated document to STDOUT.
        sys.stdout.write(aggregated)

    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments, configure logging, and delegate to run_cli."""
    parser = build_parser()
    # Allow tests to inject custom argv while defaulting to sys.argv[1:].
    args = parser.parse_args(argv)

    configure_logging(args.log_level)

    root = Path(args.root)
    separator = "" if args.no_separator else args.separator
    # ``--no-separator`` wins over a custom separator to avoid conflicting inputs.

    return run_cli(
        root=root,
        manifest=args.manifest,
        ignore=args.ignore,
        separator=separator,
        strip_frontmatter=args.strip_frontmatter,
        hybrid_mode=args.hybrid_mode,
        process_includes=args.process_includes,
        include_toc=args.toc,
        auto_file_title=not args.no_auto_file_title,
        output=args.output,
    )


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main())
