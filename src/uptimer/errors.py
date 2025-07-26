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
