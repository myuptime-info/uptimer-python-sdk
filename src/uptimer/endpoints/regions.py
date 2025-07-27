from __future__ import annotations

from typing import TYPE_CHECKING

from models.region import Region
from uptimer.endpoints.endpoint import BaseEndpoint

if TYPE_CHECKING:
    from uptimer.http import UptimerHttpLib


class RegionsEndpoint(BaseEndpoint):
    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "regions", parent_segments)

    def all(self) -> list[Region]:
        response = self.http.client.get(self.url)
        result = self.http.parse_response(response=response)
        return [Region(**region) for region in result]
