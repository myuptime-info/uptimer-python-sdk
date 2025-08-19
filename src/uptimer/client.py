from __future__ import annotations

from typing import cast

from uptimer.endpoints.v1 import V1Endpoint
from uptimer.http import UptimerHttpLib


class UptimerClient:
    v1: V1Endpoint

    def __init__(self, api_key: str, base_url: str):
        self._http_lib = UptimerHttpLib(api_key, base_url)
        self.v1 = V1Endpoint(self._http_lib)

    def version(self) -> str:
        response = self._http_lib.client.get(self._http_lib.build_url("version"))
        return cast("str", self._http_lib.parse_response(response=response))

    def set_uptimer_http_lib(self, http_lib: UptimerHttpLib) -> None:
        self._http_lib = http_lib


class UptimerCloudClient(UptimerClient):
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://api.myuptime.info")
