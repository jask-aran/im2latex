"""Shared resource utilities for resolving project assets at runtime."""

from __future__ import annotations

import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
"""Repository root used for locating bundled assets and configuration."""

_BUNDLE_BASE = Path(getattr(sys, "_MEIPASS", BASE_DIR))


def resource_path(relative_path: str) -> str:
    """Return an absolute path for the given asset regardless of bundle state."""

    return str((_BUNDLE_BASE / relative_path).resolve())


__all__ = ["BASE_DIR", "resource_path"]
