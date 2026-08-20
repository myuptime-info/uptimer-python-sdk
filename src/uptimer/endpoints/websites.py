from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.models import DeleteWebsiteMonitorResponse, from_api_website_monitor

if TYPE_CHECKING:
    from uptimer.http import UptimerHttpLib
    from uptimer.models import (
        CreateWebsiteMonitorRequest,
        UpdateWebsiteMonitorRequest,
        WebsiteMonitor,
    )


def _strip_kinds(value: object) -> object:
    """
    Drop every `kind` from a request body, at any depth.

    `kind` is what the server tells a client an object is; it is not something a
    client sets. Echoing it back suggests otherwise, and the server ignores it
    either way.
    """
    if isinstance(value, dict):
        return {k: _strip_kinds(v) for k, v in value.items() if k != "kind"}
    if isinstance(value, list):
        return [_strip_kinds(v) for v in value]
    return value


def _payload(data: object) -> dict:
    """
    Serialize a request dataclass, dropping fields the server fills in.

    An empty agreement means "leave it alone", which the server expresses by
    omission, so it is stripped rather than sent as "" — those are different
    requests.
    """
    body = asdict(data)  # type: ignore[call-overload]
    body.pop("id", None)
    if not body.get("agreement"):
        body.pop("agreement", None)
    return _strip_kinds(body)  # type: ignore[return-value]


class WebsitesEndpoint(BaseEndpoint):
    """
    Website monitoring: the built-in template that watches a URL.

    Nested under /v2/monitoring because it is one template among the several
    coming later, not the general monitor model.
    """

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "websites", parent_segments)

    def all(self, workspace_id: str) -> list[WebsiteMonitor]:
        """Every website monitor in a workspace."""
        params = {"workspace_id": workspace_id}
        response = self.http.client.get(self.url, params=params)
        result = self.http.parse_response(response=response)
        return [from_api_website_monitor(item) for item in result]

    def get(self, monitor_id: str) -> WebsiteMonitor:
        """One website monitor by id."""
        response = self.http.client.get(f"{self.url}/{monitor_id}")
        result = self.http.parse_response(response=response)
        return from_api_website_monitor(result)

    def create(self, monitor: CreateWebsiteMonitorRequest) -> WebsiteMonitor:
        """Create a website monitor, with its signal and rule."""
        response = self.http.client.post(self.url, json=_payload(monitor))
        result = self.http.parse_response(response=response)
        return from_api_website_monitor(result)

    def update(
        self,
        monitor_id: str,
        monitor: UpdateWebsiteMonitorRequest,
    ) -> WebsiteMonitor:
        """Replace a website monitor's configuration."""
        response = self.http.client.post(
            f"{self.url}/{monitor_id}",
            json=_payload(monitor),
        )
        result = self.http.parse_response(response=response)
        return from_api_website_monitor(result)

    def delete(self, monitor_id: str) -> DeleteWebsiteMonitorResponse:
        """Delete a website monitor and everything under it."""
        response = self.http.client.delete(f"{self.url}/{monitor_id}")
        result = self.http.parse_response(response=response)
        return DeleteWebsiteMonitorResponse(
            message=result["message"],
            monitor_id=result["monitor_id"],
        )


class MonitoringEndpoint(BaseEndpoint):
    """The monitoring templates. Today there is one: websites."""

    websites: WebsitesEndpoint

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "monitoring", parent_segments)
        self.websites = WebsitesEndpoint(http, [*self._parent_segments, "monitoring"])
