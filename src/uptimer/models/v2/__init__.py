"""
Types for API v2.

The API is versioned by path, so its types are versioned too: import them from
`uptimer.models.v2`, the way resources are reached through `client.v2`. Nothing
here is re-exported from `uptimer.models` — a v2 name is only ever a v2 import.

Version-independent deserialization exceptions live in `uptimer.models.errors`,
because they say nothing about which API version raised them.
"""

from .deserialize import (
    from_api,
    from_api_incident,
    from_api_location,
    from_api_website_monitor,
    from_api_workspace,
)
from .incident import (
    STATUS_NO_DATA,
    STATUS_OK,
    STATUS_PENDING,
    STATUS_PROBLEM,
    STATUS_RECOVERING,
    Incident,
    IncidentLocations,
)
from .location import Location
from .monitor import (
    AGREEMENT_ALL,
    AGREEMENT_ANY,
    AGREEMENT_MAJORITY,
    BaseWebsiteMonitor,
    CreateWebsiteMonitorRequest,
    DeleteWebsiteMonitorResponse,
    UpdateWebsiteMonitorRequest,
    WebsiteMonitor,
    WebsiteMonitorRequest,
    WebsiteMonitorResponse,
    WebsiteMonitorResponseBody,
)
from .workspace import Workspace

__all__ = [
    "AGREEMENT_ALL",
    "AGREEMENT_ANY",
    "AGREEMENT_MAJORITY",
    "STATUS_NO_DATA",
    "STATUS_OK",
    "STATUS_PENDING",
    "STATUS_PROBLEM",
    "STATUS_RECOVERING",
    "BaseWebsiteMonitor",
    "CreateWebsiteMonitorRequest",
    "DeleteWebsiteMonitorResponse",
    "Incident",
    "IncidentLocations",
    "Location",
    "UpdateWebsiteMonitorRequest",
    "WebsiteMonitor",
    "WebsiteMonitorRequest",
    "WebsiteMonitorResponse",
    "WebsiteMonitorResponseBody",
    "Workspace",
    "from_api",
    "from_api_incident",
    "from_api_location",
    "from_api_website_monitor",
    "from_api_workspace",
]
