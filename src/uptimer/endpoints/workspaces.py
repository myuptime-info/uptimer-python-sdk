from __future__ import annotations

from typing import TYPE_CHECKING

from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.models import from_api_workspace

if TYPE_CHECKING:
    from uptimer.http import UptimerHttpLib
    from uptimer.models.workspace import Workspace


class WorkspacesEndpoint(BaseEndpoint):
    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "workspaces", parent_segments)

    def all(self) -> list[Workspace]:
        response = self.http.client.get(self.url)
        result = self.http.parse_response(response=response)
        return [from_api_workspace(workspace) for workspace in result]
