"""markdownaggregator package."""
from __future__ import annotations

from importlib import metadata

from .aggregator import aggregate_markdown

__all__ = ["aggregate_markdown"]

try:  # pragma: no cover - dynamic metadata
    __version__ = metadata.version("markdownaggregator")
except metadata.PackageNotFoundError:  # pragma: no cover - local execution
    __version__ = "0.0.0"
