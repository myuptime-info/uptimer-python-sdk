"""
Server compatibility.

This package speaks API v3, which Uptimer 2.0 serves. The server says which
API it serves at `/v3/version`, before any key is needed.
"""

from __future__ import annotations

import re

from uptimer import __version__
from uptimer.errors import IncompatibleServerError


def _minimum_from_own_version() -> tuple[int, int, int]:
    """Return the oldest server this package speaks to: its own major.minor, .0."""
    parts = __version__.split(".")
    return (int(parts[0]), int(parts[1]), 0)


MINIMUM_UPTIMER_VERSION = _minimum_from_own_version()

_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)")


def parse_version(version: str) -> tuple[int, int, int] | None:
    """
    Parse a server version, or None if it is not a release number.

    "dev" and anything unparseable are treated as usable: a server run from
    source must not be locked out by its version string.
    """
    match = _VERSION_RE.match(version.strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def ensure_supported(version: str, api: str | None) -> None:
    """Raise IncompatibleServerError unless this server serves API v3."""
    if api != "v3":
        raise IncompatibleServerError(version)
    parsed = parse_version(version)
    if parsed is not None and parsed < MINIMUM_UPTIMER_VERSION:
        raise IncompatibleServerError(version)
