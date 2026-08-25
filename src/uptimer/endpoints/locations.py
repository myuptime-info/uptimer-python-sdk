from __future__ import annotations

from typing import TYPE_CHECKING

from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.models.v2 import from_api_location

if TYPE_CHECKING:
    from uptimer.http import UptimerHttpLib
    from uptimer.models.v2 import Location


class LocationsEndpoint(BaseEndpoint):
    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "locations", parent_segments)

    def all(self) -> list[Location]:
        """Every location checks can run from."""
        response = self.http.client.get(self.url)
        result = self.http.parse_response(response=response)
        return [from_api_location(item) for item in result]
