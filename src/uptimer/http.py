from __future__ import annotations

from typing import Any

import httpx

from uptimer.errors import (
    UptimerInvalidHttpCodeError,
    UptimerInvalidResponseError,
    api_error,
)


class UptimerHttpLib:
    """
    The transport: one `httpx.Client` with the API key, and the envelope reader.

    `base_url` is the server's API root, for example `http://127.0.0.1:8080/api`.
    """

    def __init__(self, api_key: str, base_url: str, *, timeout: float = 30.0):
        self._base_url = base_url.rstrip("/")
        self._http_client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    @property
    def client(self) -> httpx.Client:
        return self._http_client

    @property
    def base_url(self) -> str:
        return self._base_url

    def build_url(self, path: str) -> str:
        return self._base_url + "/" + path.strip("/")

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,  # noqa: ANN401
        params: dict[str, Any] | None = None,
    ) -> tuple[Any, dict[str, Any] | None]:
        """Send one request and answer `(result, meta)`, or raise its error."""
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        response = self._http_client.request(
            method, self.build_url(path), json=json, params=clean or None,
        )
        return self.parse(response)

    @staticmethod
    def parse(response: httpx.Response) -> tuple[Any, dict[str, Any] | None]:
        try:
            data = response.json()
        except ValueError:
            raise UptimerInvalidHttpCodeError(response.request.url, response.status_code) from None
        if not isinstance(data, dict) or "result" not in data:
            message = f"{response.request.url} did not answer with an API v3 envelope"
            raise UptimerInvalidResponseError(message)
        error = data.get("error")
        if error:
            raise api_error(error, response.status_code)
        if response.status_code >= httpx.codes.BAD_REQUEST:
            raise UptimerInvalidHttpCodeError(response.request.url, response.status_code)
        return data["result"], data.get("meta")

    def close(self) -> None:
        self._http_client.close()
