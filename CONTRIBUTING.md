# Contributing to markdownaggregator

Thank you for your interest in markdownaggregator! Contributions are welcome — bug reports, feature requests, documentation improvements, or test coverage all help move the project forward.

## How to contribute

1. **Fork** `https://github.com/stef/markdownaggregator`.
2. **Create a descriptive branch**: `git checkout -b feat/my-feature`.
3. **Set up the development environment**:

   ```bash
   pip install -e ".[dev]"
   pre-commit install
   ```

4. **Implement** your changes while preserving the existing code style.
5. **Add or update tests** (`pytest`) and documentation as needed.
6. **Run local checks**:

   ```bash
   ruff check .
   ruff format .
   mypy .
   pytest
   ```

7. **Commit** with clear, focused messages.
8. **Submit a Pull Request** explaining the motivation and the solution.

## Reporting bugs

- Use the [Issues](https://github.com/stef/markdownaggregator/issues) page.
- Provide reproduction steps, the version you used, and relevant logs.

## Coding standards

- Python ≥ 3.10 with strict type checking (`mypy --strict`).
- `ruff` handles linting and formatting.
- Unit tests with pytest; coverage is encouraged.

## Communication

Please follow our [Code of Conduct](CODE_OF_CONDUCT.md). For questions, open an issue or discuss in the PR thread.

## Releases

Maintainers handle releases (`python -m build` + PyPI publish). Refer to the [CHANGELOG](CHANGELOG.md) for history.

Thank you for contributing!
