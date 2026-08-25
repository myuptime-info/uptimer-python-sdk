from __future__ import annotations

from typing import TYPE_CHECKING

from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.models.v2 import from_api_incident

if TYPE_CHECKING:
    from uptimer.http import UptimerHttpLib
    from uptimer.models.v2 import Incident


class IncidentsEndpoint(BaseEndpoint):
    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "incidents", parent_segments)

    def all(
        self,
        workspace_id: str,
        monitor_id: str | None = None,
    ) -> list[Incident]:
        """
        Open incidents in a workspace, newest trouble first.

        Only open ones: this answers "what is wrong now". Pass monitor_id to
        narrow it to a single monitor.
        """
        params = {"workspace_id": workspace_id}
        if monitor_id:
            params["monitor_id"] = monitor_id
        response = self.http.client.get(self.url, params=params)
        result = self.http.parse_response(response=response)
        return [from_api_incident(item) for item in result]
