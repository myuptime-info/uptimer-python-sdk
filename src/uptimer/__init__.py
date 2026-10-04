"""
Uptimer Python SDK.

Speaks Uptimer API v3, served by Uptimer 2.0 and later. The version tracks the
server release it targets: 2.0.x speaks to Uptimer 2.0.0 and later.
"""

__version__ = "2.0.0"

from uptimer.client import UptimerClient
from uptimer.errors import (
    AuthenticationError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    IncompatibleServerError,
    NotFoundError,
    ServerError,
    UnsupportedError,
    UptimerApiError,
    UptimerError,
    ValidationError,
)

__all__ = [
    "AuthenticationError",
    "BadRequestError",
    "ConflictError",
    "ForbiddenError",
    "IncompatibleServerError",
    "NotFoundError",
    "ServerError",
    "UnsupportedError",
    "UptimerApiError",
    "UptimerClient",
    "UptimerError",
    "ValidationError",
    "__version__",
]
