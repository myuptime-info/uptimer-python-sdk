from __future__ import annotations

from typing import Any

import httpx

from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.errors import DefaultUptimerApiError, UptimerInvalidHttpCodeError


class WorkspacesEndpoint(BaseEndpoint):
    pass


class UptimerHttpLib:
    def __init__(self, api_key: str, base_url: str):
        self._base_url = base_url.rstrip("/")
        self._http_client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
            },
        )

    @property
    def client(self) -> httpx.Client:
        return self._http_client

    @property
    def base_url(self) -> str:
        return self._base_url

    def build_url(self, path: str) -> str:
        path = path.strip("/")
        return self._base_url.rstrip("/") + "/" + path

    @staticmethod
    def parse_response(
        response: httpx.Response,
    ) -> Any:  # noqa: ANN401
        if response.status_code != 200:
            raise UptimerInvalidHttpCodeError(
                response.request.url,
                response.status_code,
            )
        data = response.json()
        if data.get("error"):
            raise DefaultUptimerApiError(data["error"])
        return data["result"]
