from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.endpoints.regions import RegionsEndpoint
from uptimer.endpoints.rules import RulesEndpoint
from uptimer.endpoints.workspaces import WorkspacesEndpoint
from uptimer.http import UptimerHttpLib


class V1Endpoint(BaseEndpoint):
    workspaces: WorkspacesEndpoint
    regions: RegionsEndpoint
    rules: RulesEndpoint

    def __init__(self, http: UptimerHttpLib):
        super().__init__(http, "v1")
        self.workspaces = WorkspacesEndpoint(http, ["v1"])
        self.regions = RegionsEndpoint(http, ["v1"])
        self.rules = RulesEndpoint(http, ["v1"])
