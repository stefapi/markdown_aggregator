# markdownaggregator

<div align="center">
  <img src="https://img.shields.io/pypi/v/markdownaggregator.svg?style=for-the-badge" alt="PyPI">
  <img src="https://img.shields.io/pypi/pyversions/markdownaggregator.svg?style=for-the-badge" alt="Python versions">
  <img src="https://img.shields.io/badge/type%20hints-100%25-4B8BBE?style=for-the-badge" alt="Typing">
  <img src="https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?style=for-the-badge&logo=githubactions" alt="CI">
  <img src="https://img.shields.io/badge/License-MIT-2EA043?style=for-the-badge" alt="License">
</div>

<p align="center">
  <em>Assemble Markdown forests into polished, navigable documents — CLI or Python, batteries included.</em>
</p>

---

- **Status**: Beta – ready for everyday use, API kept stable for the 0.x series
- **Docs**: [`docs/usage.md`](docs/usage.md)

---

## 🌟 Why Markdown Aggregation Should Be Effortless

| Challenge | markdownaggregator Solution | Modes |
| --------- | -------------------------- | ----- |
| Maintaining a knowledge base scattered across folders | Deterministic traversal with manifest or auto-discovery | CLI / Library |
| Producing customer-ready guides from technical notes | Automatic TOC, heading normalization, source breadcrumbs | CLI / Library |
| Reusing documentation snippets via `@include` | Recursive include resolution with cycle detection | CLI / Library |
| Mixing curated order and “everything else” | Hybrid mode merges manifest priority with discovery | CLI |
| Cleaning YAML front-matter for publication | One flag to strip it before merge | CLI / Library |
| Automating build pipelines | Pure Python function `aggregate_markdown` + zero I/O side effects | Library |

## 🧭 User Journeys

### 1. Documentation Lead (CLI)

1. Curate `manifest.txt` describing the expected order.
2. Run `markdownaggregator docs --manifest manifest.txt --process-includes`.
3. Commit the generated `dist/documentation.md` and ship the release notes.

### 2. Platform Engineer (Python Library)

1. Import `aggregate_markdown` in a build step.
2. Feed it the docs root, manifest and ignore patterns.
3. Pipe the returned string into your static site generator.

---

## ⚡ Quickstart

### CLI

```bash
pip install markdownaggregator

# Aggregate docs into dist/docs.md
markdownaggregator docs/ \
  --manifest manifest.txt \
  --process-includes \
  --toc \
  --strip-frontmatter \
  --output dist/docs.md
```

**Pro tips**

- Repeat `--ignore` for glob patterns (e.g. `drafts/*`).
- Use `--hybrid-mode` to append undiscovered files after the manifest order.
- Disable separators with `--no-separator` or customize via `--separator`.

### Python API

```python
from pathlib import Path
from markdownaggregator import aggregate_markdown

merged = aggregate_markdown(
    root=Path("docs"),
    manifest=Path("manifest.txt"),
    ignore=["drafts/*", "archive/**"],
    separator="---",
    strip_frontmatter_from_files=True,
    hybrid_mode=True,
    process_includes_flag=True,
    include_toc=True,
    auto_file_title=True,
    output=Path("dist/guide.md"),  # optional
)

print(merged[:200])  # preview
```

- When `output` is provided, the file is written in addition to returning the string.
- All parameters are keyword-only for clarity and forward compatibility.

---

## 🏗️ Architecture at a Glance

```
markdownaggregator/
├── aggregator.py    # core domain logic (discovery, merge, TOC, includes)
├── cli.py           # argparse-powered interface & logging
├── __main__.py      # enables `python -m markdownaggregator`
└── __init__.py      # re-exports aggregate_markdown & package metadata
```

Supporting assets:

- `docs/usage.md` — extended scenarios and tips  
- `tests/test_aggregator.py` — pytest coverage for discovery, manifest, includes, CLI  
- `.github/workflows/release.yml` — PyPI publish pipeline (GitHub release driven)

---

## 📚 Documentation Index

- [Usage guide](docs/usage.md) – scenarios, ignores, includes, logging
- [CHANGELOG](CHANGELOG.md) – Keep a Changelog format
- [RELEASING](RELEASING.md) – how to tag, build, verify and publish on PyPI
- [CONTRIBUTING](CONTRIBUTING.md) – workflow, tooling, standards
- [CODE_OF_CONDUCT](CODE_OF_CONDUCT.md) – Contributor Covenant v2.1

---

## 🛠️ Tech Stack & Tooling

| Area | Tooling |
| ---- | ------- |
| Language | Python ≥ 3.10 (typed, `mypy --strict`) |
| CLI | `argparse`, rich logging, exit codes |
| Packaging | `setuptools`, `MANIFEST.in`, console script `markdownaggregator` |
| Quality | `pytest`, `pytest-cov`, `ruff` (lint + format), `mypy`, `pre-commit` |
| CI/CD | GitHub Actions – unit tests + PyPI publishing workflow |

---

## 🗺️ Roadmap

- [ ] HTML/PDF export helpers
- [ ] Incremental rebuild mode (skip unchanged files)
- [ ] Optional YAML-driven configuration file
- [ ] Pluggable include resolvers (HTTP, git URLs)
- [ ] Rich logging formatter (colors / verbosity presets)

Contribute to the roadmap by opening GitHub issues with the `enhancement` label.

---

## 💻 Development Workflow

```bash
git clone https://github.com/stefapi/markdownaggregator
cd markdownaggregator

pip install -e ".[dev]"
pre-commit install

ruff check .
ruff format .
mypy .
pytest
```

Run the CLI locally:

```bash
python -m markdownaggregator docs --output dist/out.md
```

---

## 🚀 Release & PyPI Publishing

1. Update `pyproject.toml` version + `CHANGELOG.md`.
2. Run local validations: `pre-commit run --all-files`, `pytest`, `mypy .`.
3. Build artifacts: `python -m build` (creates `dist/*.whl` and `*.tar.gz`).
4. Option A — **Manual**: `twine upload dist/*`.
5. Option B — **Automated**: push tag `vX.Y.Z`, publish GitHub release, let the workflow `Publish to PyPI` deploy using `PYPI_API_TOKEN`.

Full checklist in [RELEASING.md](RELEASING.md).

---

## 🤝 Community, Contributing & Support

We welcome feature ideas, bug reports, docs tweaks and new tests.

- Read [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming, tooling and review expectations.
- Respect the [Code of Conduct](CODE_OF_CONDUCT.md) — contact `stephane_nospam@apiou.org` for incident reports.
- Discussions happen through GitHub issues and pull requests.

---

## 📄 License

MIT © 2025 Stefapi — see [LICENSE](LICENSE) for full text.

If markdownaggregator streamlines your doc workflows, mention it in your release notes or give it a ⭐️ on GitHub. Merci !
