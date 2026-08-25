from __future__ import annotations

from dataclasses import dataclass, field

# Agreement: how many locations must report a problem before the monitor does.
AGREEMENT_ANY = "any"
AGREEMENT_MAJORITY = "majority"
AGREEMENT_ALL = "all"


@dataclass
class WebsiteMonitorRequest:
    url: str  # request URL
    method: str  # HTTP method (GET, POST, etc.)
    content_type: str = "application/json"  # content type for the request
    data: str = ""  # request data/payload
    kind: str = "website_monitor_request"


@dataclass
class WebsiteMonitorResponseBody:
    content: str = ""  # expected response body content
    kind: str = "website_monitor_response_body"


@dataclass
class WebsiteMonitorResponse:
    statuses: list[int]  # acceptable HTTP status codes
    body: WebsiteMonitorResponseBody = field(
        default_factory=WebsiteMonitorResponseBody,
    )
    kind: str = "website_monitor_response"


@dataclass
class BaseWebsiteMonitor:
    """Fields shared by a website monitor and a request to create one."""

    name: str  # monitor name
    interval: int  # check interval in seconds
    workspace_id: str  # workspace id
    request: WebsiteMonitorRequest  # what to send
    response: WebsiteMonitorResponse  # what counts as healthy
    # Location names this monitor is checked from (matched by name). A monitor
    # with no locations is never checked and stays at no data.
    locations: list[str] = field(default_factory=list)
    # How many locations must agree before the monitor reports a problem:
    # "any", "majority" or "all". Empty means leave it at the server default.
    agreement: str = ""
    kind: str = "website_monitor"


@dataclass
class WebsiteMonitor(BaseWebsiteMonitor):
    """A stored website monitor, as the API returns it."""

    id: str = ""  # monitor id, uuids used for api ids


@dataclass
class CreateWebsiteMonitorRequest(BaseWebsiteMonitor):
    """Website monitor data for a create request (no id yet)."""


@dataclass
class UpdateWebsiteMonitorRequest:
    """
    Website monitor data for an update.

    The workspace is fixed at creation, so it is absent here. Locations replace
    the stored list; an empty list clears them. An omitted agreement keeps the
    stored one.
    """

    name: str
    interval: int
    request: WebsiteMonitorRequest
    response: WebsiteMonitorResponse
    locations: list[str] = field(default_factory=list)
    agreement: str = ""


@dataclass
class DeleteWebsiteMonitorResponse:
    """Response for a successful website monitor deletion."""

    message: str  # success message
    monitor_id: str  # id of the deleted monitor
