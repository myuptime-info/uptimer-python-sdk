"""
Errors.

Every API v3 refusal carries a code, a type, a message and, for a refused
field, the field's name. Each code raises its own exception, so a caller can
catch exactly the refusal it handles; all of them are `UptimerApiError`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx


class UptimerError(Exception):
    """Everything this package raises."""


class UptimerInvalidResponseError(UptimerError):
    """The server answered with something that is not an API v3 answer."""


class UptimerInvalidHttpCodeError(UptimerInvalidResponseError):
    def __init__(self, url: httpx.URL, status_code: int):
        self.url = url
        self.status_code = status_code
        super().__init__(f"Invalid HTTP code {status_code!s} for URL {url!s}")


class UptimerApiError(UptimerError):
    """An API v3 refusal: `code`, `error_type`, `message`, `details`, `status`."""

    def __init__(self, error: dict[str, Any], status: int):
        self.code: int | None = error.get("code")
        self.error_type: str | None = error.get("error_type")
        self.message: str = error.get("message") or ""
        self.details: Any = error.get("details")
        self.status = status
        super().__init__(f"{self.code} {self.error_type}: {self.message}")

    @property
    def field(self) -> str | None:
        """The refused field, where the refusal names one."""
        if isinstance(self.details, dict):
            value = self.details.get("field")
            return value if isinstance(value, str) else None
        return None


class BadRequestError(UptimerApiError):
    """1400: the request could not be read."""


class AuthenticationError(UptimerApiError):
    """1401: no API key, or one the server does not accept."""


class ForbiddenError(UptimerApiError):
    """1403: your role in the Workspace does not allow this write."""


class NotFoundError(UptimerApiError):
    """1404: no such thing in this Workspace, or no such Workspace for you."""


class ConflictError(UptimerApiError):
    """1409: not in a state this action applies to, such as acknowledging a closed Incident."""


class UnsupportedError(UptimerApiError):
    """1410: a retired API the server no longer serves."""


class ValidationError(UptimerApiError):
    """1422: a field was refused; `field` names it."""


class ServerError(UptimerApiError):
    """1500: the server failed."""


ERRORS_BY_CODE: dict[int, type[UptimerApiError]] = {
    1400: BadRequestError,
    1401: AuthenticationError,
    1403: ForbiddenError,
    1404: NotFoundError,
    1409: ConflictError,
    1410: UnsupportedError,
    1422: ValidationError,
    1500: ServerError,
}


def api_error(error: dict[str, Any], status: int) -> UptimerApiError:
    """Build the exception for one API v3 error object."""
    code = error.get("code")
    kind = ERRORS_BY_CODE.get(code, UptimerApiError) if isinstance(code, int) else UptimerApiError
    return kind(error, status)


class IncompatibleServerError(UptimerError):
    """The server does not serve API v3, which this package requires."""

    def __init__(self, server_version: str):
        self.server_version = server_version
        super().__init__(
            f"This server reports version {server_version}, which does not "
            "serve API v3. uptimer-python-sdk 2.x requires Uptimer 2.0 or later.",
        )
