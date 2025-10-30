# Publishing on PyPI

This guide describes the recommended process for releasing a new version of **markdownaggregator** to PyPI.

## 1. Prerequisites

- Maintainer access to both the GitHub repository and the PyPI project.
- GitHub secrets configured:
  - `PYPI_API_TOKEN` (PyPI or PyPI-Legacy token with “Entire account” scope, or restricted to this project).
- Local environment with Python ≥ 3.10, `build`, `twine`, `pre-commit`, `pytest`.

## 2. Local checks

```bash
pre-commit run --all-files
pytest
mypy .
```

## 3. Bump the version

1. Edit `pyproject.toml` (`[project] version`).
2. Update `CHANGELOG.md`.
3. Commit:

```bash
git commit -am "Release vX.Y.Z"
```

## 4. Build the artifacts

```bash
python -m build
```

The generated files land in `dist/`.

## 5. Optional Twine verification

```bash
twine check dist/*
```

## 6. Manual publication (optional)

```bash
twine upload dist/*
```

or publish to TestPyPI first:

```bash
twine upload --repository testpypi dist/*
```

## 7. Publishing via GitHub Actions

1. Push your changes:

```bash
git push origin main
```

2. Create a tag and release:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

3. Publish the GitHub release.

The workflow `.github/workflows/release.yml` will build and upload the distribution to PyPI using `pypa/gh-action-pypi-publish`.

## 8. Post-release validation

- Verify the package is live on [https://pypi.org/project/markdownaggregator/](https://pypi.org/project/markdownaggregator/).
- Test installation:

```bash
pip install --upgrade markdownaggregator
markdownaggregator --help
```

## 9. Maintenance

- Create a signed git tag if required (`git tag -s`).
- Update documentation (README, CHANGELOG).
- Announce the release (issues, discussions, social channels).
