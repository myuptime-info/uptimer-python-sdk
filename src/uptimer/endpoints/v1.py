from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.models.v2 import from_api_acknowledgement

if TYPE_CHECKING:
    from uptimer.http import UptimerHttpLib
    from uptimer.models.v2 import IncidentAcknowledgement


def _segment(value: str, what: str) -> str:
    """Escape one identifier for a URL path segment."""
    if not value or not value.strip():
        message = f"{what} is required"
        raise ValueError(message)
    return quote(value, safe="")


class WebsiteIncidentEndpoint(BaseEndpoint):
    """One incident of a website monitor, addressed by its opaque id."""

    def __init__(
        self,
        http: UptimerHttpLib,
        incident_id: str,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, _segment(incident_id, "incident id"), parent_segments)

    def acknowledge(self) -> IncidentAcknowledgement:
        """
        Record that you have seen THIS website incident. Requires uptimer 1.7.0+.

        Find the id with `client.v2.incidents.all(workspace_id)`, which lists
        open website incidents with the monitor each belongs to.

        It says a person looked; it changes nothing the engine decided — the
        verdict, the evidence, the close hold and alerting all carry on. There
        is no body and no actor argument: the person recorded is the owner of
        the API key, at the time of the call.

        Repeating it is safe: a second call records nothing and returns the
        FIRST person's name and time with `recorded=False`.

        Raises DefaultUptimerApiError when the incident is not this monitor's —
        another monitor's, another workspace's, or a custom subject's — and when
        it has closed. A custom incident is acknowledged through
        `client.v2.subjects(...).incidents(...)`, and this will not do it for
        you: the families do not fall back to one another.
        """
        response = self.http.client.post(f"{self.url}/acknowledge")
        result = self.http.parse_response(response=response)
        return from_api_acknowledgement(result)


class WebsiteIncidentsEndpoint(BaseEndpoint):
    """
    The incidents of one website monitor, addressed by id.

    There is no listing here: open website incidents are listed for a whole
    workspace by `client.v2.incidents.all(workspace_id)`, which is the discovery
    path this SDK has had since 1.5.0 and which already names each incident's
    monitor. This exists to act on one of them.
    """

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "incidents", parent_segments)

    def __call__(self, incident_id: str) -> WebsiteIncidentEndpoint:
        return WebsiteIncidentEndpoint(
            self.http,
            incident_id,
            [*self._parent_segments, self.segment],
        )


class RuleEndpoint(BaseEndpoint):
    """One website monitor, addressed by its uid."""

    incidents: WebsiteIncidentsEndpoint

    def __init__(
        self,
        http: UptimerHttpLib,
        monitor_uid: str,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, _segment(monitor_uid, "monitor uid"), parent_segments)
        self.incidents = WebsiteIncidentsEndpoint(http, [*self._parent_segments, self.segment])


class RulesEndpoint(BaseEndpoint):
    """
    Website monitors, as API v1 calls them.

    Call it with a monitor's uid to reach what is under one:
    `client.v1.rules(monitor_uid).incidents(incident_id).acknowledge()`.

    Reading and writing monitors themselves stays on
    `client.v2.monitoring.websites` — the same resource in v2's words, and the
    one this SDK is built around.
    """

    def __init__(
        self,
        http: UptimerHttpLib,
        parent_segments: str | list[str] | None = None,
    ):
        super().__init__(http, "rules", parent_segments)

    def __call__(self, monitor_uid: str) -> RuleEndpoint:
        return RuleEndpoint(self.http, monitor_uid, [*self._parent_segments, self.segment])


class V1Endpoint(BaseEndpoint):
    """
    API v1, narrowly: `client.v1`.

    This SDK is a v2 client, and that has not changed. v1 appears here for one
    reason: uptimer 1.7.0 serves WEBSITE acknowledgement under
    `/v1/rules/{uid}/incidents/{id}/acknowledge`, because website monitoring is
    v1's resource (Decision 0015) and custom monitoring is v2's. Each kind
    acknowledges through its own family, and neither route accepts the other's
    incidents.

    So this namespace is the acknowledgement door for website monitors, and
    nothing else: no rule listing, no create, no update, no delete. Those live
    on `client.v2.monitoring.websites`, which speaks v2's vocabulary and is
    where a v2 client belongs.
    """

    rules: RulesEndpoint

    def __init__(self, http: UptimerHttpLib):
        super().__init__(http, "v1")
        self.rules = RulesEndpoint(http, [self.segment])
