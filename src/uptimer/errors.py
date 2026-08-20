import httpx


class UptimerError(Exception):
    pass


class UptimerInvalidResponseError(UptimerError):
    pass


class UptimerInvalidHttpCodeError(UptimerError):
    def __init__(self, url: httpx.URL, status_code: int):
        self.url = url
        self.status_code = status_code
        super().__init__(f"Invalid HTTP code {status_code!s} for URL {url!s}")


class DefaultUptimerApiError(UptimerError):
    def __init__(self, error: dict):
        self.code = error.get("code")
        self.error_type = error.get("error_type")
        self.message = error.get("message", "")
        self.details = error.get("details", "")
        super().__init__(f"API error: {self.code} {self.message}")


class IncompatibleServerError(UptimerError):
    """
    The server does not provide API v2, which this SDK requires.

    Carries the server's own version so the message names the situation rather
    than surfacing a bare 404.
    """

    def __init__(self, server_version: str):
        self.server_version = server_version
        super().__init__(
            f"This server reports version {server_version}, which does not "
            "provide API v2. uptimer-python-sdk 1.x requires API v2 "
            "(uptimer 1.5.0+ or myuptime.info 15.1.0+). For API v1, use "
            "uptimer-python-sdk 0.4.x.",
        )
