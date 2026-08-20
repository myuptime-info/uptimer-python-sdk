"""
Integration tests against a live Uptimer server.

Skipped unless UPTIMER_IT_URL and UPTIMER_IT_TOKEN are set, so the normal unit
run does not need a server.

The incident case is the point of this file: a monitor is pointed at a dead port
and the suite waits for the engine to actually open an incident, then reads it
back through the SDK. Nothing here mocks the server.
"""

from __future__ import annotations

import os
import time

import pytest

from uptimer.client import UptimerClient
from uptimer.compat import ensure_v2_supported
from uptimer.errors import DefaultUptimerApiError, IncompatibleServerError
from uptimer.models import (
    AGREEMENT_ALL,
    AGREEMENT_ANY,
    CreateWebsiteMonitorRequest,
    Incident,
    Location,
    UpdateWebsiteMonitorRequest,
    WebsiteMonitor,
    WebsiteMonitorRequest,
    WebsiteMonitorResponse,
    WebsiteMonitorResponseBody,
    Workspace,
)

BASE_URL = os.environ.get("UPTIMER_IT_URL", "")
TOKEN = os.environ.get("UPTIMER_IT_TOKEN", "")
WORKSPACE = os.environ.get("UPTIMER_IT_WORKSPACE", "")

pytestmark = pytest.mark.skipif(
    not (BASE_URL and TOKEN and WORKSPACE),
    reason="set UPTIMER_IT_URL / UPTIMER_IT_TOKEN / UPTIMER_IT_WORKSPACE",
)

# Checks fire on minute boundaries and an incident needs a failing tick, so the
# waits below are generous. They poll rather than sleep blindly.
INCIDENT_TIMEOUT_S = 240
POLL_S = 5


@pytest.fixture(scope="module")
def client() -> UptimerClient:
    return UptimerClient(api_key=TOKEN, base_url=BASE_URL)


@pytest.fixture(scope="module")
def location_name(client: UptimerClient) -> str:
    locations = client.locations.all()
    assert locations, "the server has no locations; a worker must be registered"
    return locations[0].name


def _probe(url: str) -> WebsiteMonitorRequest:
    return WebsiteMonitorRequest(url=url, method="GET")


def _healthy_response() -> WebsiteMonitorResponse:
    return WebsiteMonitorResponse(
        statuses=[200],
        body=WebsiteMonitorResponseBody(content=""),
    )


def test_version_and_compatibility(client: UptimerClient) -> None:
    version = client.version()
    assert version, "the server reported no version"
    # Must not raise: this server has /v2.
    assert client.check_compatibility() == version


def test_workspaces(client: UptimerClient) -> None:
    workspaces = client.workspaces.all()
    assert all(isinstance(w, Workspace) for w in workspaces)
    assert any(w.id == WORKSPACE for w in workspaces)
    assert all(w.kind == "workspace" for w in workspaces)


def test_locations(client: UptimerClient) -> None:
    locations = client.locations.all()
    assert locations
    assert all(isinstance(loc, Location) for loc in locations)
    assert all(loc.kind == "location" for loc in locations)
    # v2 says location, never region.
    assert all(not hasattr(loc, "region") for loc in locations)


def test_monitor_lifecycle(client: UptimerClient, location_name: str) -> None:
    created = client.monitoring.websites.create(
        CreateWebsiteMonitorRequest(
            name="SDK lifecycle",
            interval=60,
            workspace_id=WORKSPACE,
            request=_probe("http://127.0.0.1:12517/api/version"),
            response=_healthy_response(),
            locations=[location_name],
            agreement=AGREEMENT_ALL,
        ),
    )
    try:
        assert isinstance(created, WebsiteMonitor)
        assert created.id
        assert created.kind == "website_monitor"
        assert created.locations == [location_name]
        assert created.agreement == AGREEMENT_ALL

        fetched = client.monitoring.websites.get(created.id)
        assert fetched.id == created.id
        assert fetched.agreement == AGREEMENT_ALL
        assert fetched.request.kind == "website_monitor_request"
        assert fetched.response.kind == "website_monitor_response"
        assert fetched.response.body.kind == "website_monitor_response_body"

        listed = client.monitoring.websites.all(WORKSPACE)
        assert created.id in [m.id for m in listed]

        # An update that omits the agreement must not reset it.
        kept = client.monitoring.websites.update(
            created.id,
            UpdateWebsiteMonitorRequest(
                name="SDK lifecycle renamed",
                interval=60,
                request=_probe("http://127.0.0.1:12517/api/version"),
                response=_healthy_response(),
                locations=[location_name],
            ),
        )
        assert kept.name == "SDK lifecycle renamed"
        assert kept.agreement == AGREEMENT_ALL, "an omitted agreement must be kept"

        changed = client.monitoring.websites.update(
            created.id,
            UpdateWebsiteMonitorRequest(
                name="SDK lifecycle renamed",
                interval=60,
                request=_probe("http://127.0.0.1:12517/api/version"),
                response=_healthy_response(),
                locations=[location_name],
                agreement=AGREEMENT_ANY,
            ),
        )
        assert changed.agreement == AGREEMENT_ANY
    finally:
        deleted = client.monitoring.websites.delete(created.id)
        assert deleted.monitor_id == created.id

    with pytest.raises(DefaultUptimerApiError):
        client.monitoring.websites.get(created.id)


def test_unknown_location_is_refused_in_v2_words(
    client: UptimerClient,
) -> None:
    with pytest.raises(DefaultUptimerApiError) as excinfo:
        client.monitoring.websites.create(
            CreateWebsiteMonitorRequest(
                name="SDK bad location",
                interval=60,
                workspace_id=WORKSPACE,
                request=_probe("http://127.0.0.1:12517/api/version"),
                response=_healthy_response(),
                locations=["nowhere"],
            ),
        )
    # A v2 client has never heard of regions.
    assert "location" in (excinfo.value.message + excinfo.value.details).lower()
    assert "region" not in (excinfo.value.message + excinfo.value.details).lower()


def test_invalid_agreement_is_refused(
    client: UptimerClient,
    location_name: str,
) -> None:
    with pytest.raises(DefaultUptimerApiError) as excinfo:
        client.monitoring.websites.create(
            CreateWebsiteMonitorRequest(
                name="SDK bad agreement",
                interval=60,
                workspace_id=WORKSPACE,
                request=_probe("http://127.0.0.1:12517/api/version"),
                response=_healthy_response(),
                locations=[location_name],
                agreement="most",
            ),
        )
    assert "agreement" in excinfo.value.message.lower()


def test_incident_appears_for_a_dead_port(
    client: UptimerClient,
    location_name: str,
) -> None:
    """
    The whole point: break a monitor, wait, and read the incident back.

    Port 9 is the discard port and nothing listens on it here, so every probe
    fails and the engine must open an incident. Agreement is "any" so a single
    location is enough.
    """
    monitor = client.monitoring.websites.create(
        CreateWebsiteMonitorRequest(
            name="SDK dead port",
            interval=60,
            workspace_id=WORKSPACE,
            request=_probe("http://127.0.0.1:9/"),
            response=_healthy_response(),
            locations=[location_name],
            agreement=AGREEMENT_ANY,
        ),
    )
    try:
        # Wait for the location to appear in `failing`, not merely for an
        # incident to exist. An incident opens before the first observation
        # lands, and at that moment the location reads `unknown` — asserting on
        # that stage would pass without a single probe having been made.
        deadline = time.time() + INCIDENT_TIMEOUT_S
        found: Incident | None = None
        while time.time() < deadline:
            for incident in client.incidents.all(
                WORKSPACE,
                monitor_id=monitor.id,
            ):
                if incident.monitor_id == monitor.id:
                    found = incident
                    break
            if found and location_name in found.locations.failing:
                break
            time.sleep(POLL_S)

        assert found is not None, (
            f"no incident within {INCIDENT_TIMEOUT_S}s for a monitor pointed at "
            "a dead port"
        )
        assert location_name in found.locations.failing, (
            f"{location_name} never reported a failure within "
            f"{INCIDENT_TIMEOUT_S}s; evidence was {found.locations}"
        )
        assert found.kind == "incident"
        assert found.id, "an incident must carry an opaque id"
        assert not found.id.isdigit(), "the id must not be a raw database integer"
        assert found.monitor_name == "SDK dead port"
        assert found.status in {"problem", "pending", "no_data", "recovering"}
        assert found.trouble_since
        assert found.locations.ok == [], "a dead port must not report ok"

        # Narrowing to another monitor id must not return this one.
        others = client.incidents.all(WORKSPACE, monitor_id="does-not-exist")
        assert all(i.monitor_id != monitor.id for i in others)

        # And it shows up in the unfiltered workspace list too.
        workspace_wide = client.incidents.all(WORKSPACE)
        assert monitor.id in [i.monitor_id for i in workspace_wide]
    finally:
        client.monitoring.websites.delete(monitor.id)


def test_incompatible_server_message_names_the_fix() -> None:
    """The error a 0.4.x-era server must produce."""
    with pytest.raises(IncompatibleServerError) as excinfo:
        ensure_v2_supported("1.4.0")
    message = str(excinfo.value)
    assert "0.4.x" in message
    assert "1.5.0" in message
    # A dev server must not be blocked.
    ensure_v2_supported("dev")
