from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.endpoints.workspaces import WorkspacesEndpoint
from uptimer.http import UptimerHttpLib


class V1Endpoint(BaseEndpoint):
    workspaces: WorkspacesEndpoint

    def __init__(self, http: UptimerHttpLib):
        super().__init__(http, "v1")
        self.workspaces = WorkspacesEndpoint(http, ["v1"])
