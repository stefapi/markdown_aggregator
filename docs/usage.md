# Usage Guide

This guide presents the main use cases of **markdownaggregator**.

## Simple aggregation

```bash
markdownaggregator docs/ --output dist/documentation.md
```

- Discovers every `*.md` file under `docs/`.
- Produces a single `dist/documentation.md` document.
- Automatically prepends a table of contents.
- Inserts the separator `---` between files (configurable).

## Working with a manifest

A manifest defines an explicit order and can include directories:

```
README.md
guide/introduction.md
guide/
reference/api.md # inline comments are allowed
```

```bash
markdownaggregator docs --manifest manifest.txt --output dist.md
```

- Entries are resolved relative to `docs`.
- Listed directories are traversed recursively (alphabetical order).
- Duplicates are automatically removed.

## Hybrid mode

Combine manifest order with auto-discovered files:

```bash
markdownaggregator docs --manifest manifest.txt --hybrid-mode
```

- Files missing from the manifest are appended at the end.
- No duplicates even if a file appears in both sources.

## Strip YAML front matter

```bash
markdownaggregator docs --strip-frontmatter
```

- Removes the first block delimited by `---`…`---` at the beginning of each file.

## Resolve @include directives

```bash
markdownaggregator docs --process-includes
```

- Processes directives like `<!-- @include: path/to/file.md -->`.
- Resolves paths relative to the current file, the root, or as an absolute path.
- Prevents loops by tracking already included files.

## Library usage

```python
from pathlib import Path
from markdownaggregator import aggregate_markdown

merged = aggregate_markdown(
    root=Path("docs"),
    manifest=Path("manifest.txt"),
    ignore=["drafts/*"],
    separator="",
    strip_frontmatter_from_files=True,
    hybrid_mode=True,
    process_includes_flag=True,
    output=Path("dist/merged.md"),
)
```

- `output` is optional; when provided, the file is written to disk.
- All CLI options are available as keyword arguments.

## Logging

Use `--log-level` (CLI) or configure the `markdownaggregator` logger in code:

```python
import logging

logging.basicConfig(level=logging.INFO)
```

Emitted log messages:
- Hybrid mode information (`INFO`).
- Warnings when a referenced file cannot be found (`WARNING`).

## Common errors

| Message | Cause | Remedy |
| ------- | ----- | ------ |
| `Manifest entry not found` | Invalid path in the manifest | Double-check spelling/casing |
| `No Markdown files found.` | No files detected | Confirm the `.md` extension and root path |
| `Root not found` | Base path does not exist | Ensure the target folder has been cloned |
