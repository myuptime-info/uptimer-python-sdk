from __future__ import annotations

from typing import TYPE_CHECKING

from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.endpoints.incidents import IncidentsEndpoint
from uptimer.endpoints.locations import LocationsEndpoint
from uptimer.endpoints.websites import MonitoringEndpoint
from uptimer.endpoints.workspaces import WorkspacesEndpoint

if TYPE_CHECKING:
    from uptimer.http import UptimerHttpLib


class V2Endpoint(BaseEndpoint):
    """
    API v2, the whole of it: `client.v2`.

    The API is versioned by path, so the SDK keeps that version visible rather
    than hiding it behind bare attributes (Decision 0012). Every resource here
    builds its URL from this namespace's segment, which is why `/v2` appears in
    exactly one place.

    `/version` is shared and unversioned, so it stays on the client itself.
    """

    workspaces: WorkspacesEndpoint
    locations: LocationsEndpoint
    incidents: IncidentsEndpoint
    monitoring: MonitoringEndpoint

    def __init__(self, http: UptimerHttpLib):
        super().__init__(http, "v2")
        parent = [self.segment]
        self.workspaces = WorkspacesEndpoint(http, parent)
        self.locations = LocationsEndpoint(http, parent)
        self.incidents = IncidentsEndpoint(http, parent)
        self.monitoring = MonitoringEndpoint(http, parent)
