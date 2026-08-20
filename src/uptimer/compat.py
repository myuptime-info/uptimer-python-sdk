"""
Server compatibility.

This SDK targets API v2 only. A server that predates v2 answers /v2 with 404,
which on its own tells a user nothing — so the version is checked first and the
404 is translated as a fallback.

Why both: `uptimer` and `myuptime.info` version independently over the same
shared API (1.5.x and 15.x). A numeric minimum catches the self-hosted case
cleanly, but cannot express "hosted 14.0.3 has no v2" — 14 is greater than 1.
The 404 path catches what the number cannot.
"""

from __future__ import annotations

import re

from uptimer import __version__
from uptimer.errors import IncompatibleServerError


def _minimum_from_own_version() -> tuple[int, int, int]:
    """
    Return the oldest server version this SDK speaks to.

    The SDK's major.minor tracks the uptimer release it targets (Decision
    0013), so 1.5.x requires a 1.5.0 server. Deriving it here rather than
    writing the number down twice means the two cannot drift apart.
    """
    parts = __version__.split(".")
    return (int(parts[0]), int(parts[1]), 0)


MINIMUM_UPTIMER_VERSION = _minimum_from_own_version()

_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)")


def parse_version(version: str) -> tuple[int, int, int] | None:
    """
    Parse a server version, or None if it is not a release number.

    "dev" and anything unparseable return None and are treated as usable: a
    developer running from source must not be locked out by a version string.
    """
    match = _VERSION_RE.match(version.strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def ensure_v2_supported(version: str) -> None:
    """Raise IncompatibleServerError if this server is too old for API v2."""
    parsed = parse_version(version)
    if parsed is None:
        return
    if parsed < MINIMUM_UPTIMER_VERSION:
        raise IncompatibleServerError(version)
