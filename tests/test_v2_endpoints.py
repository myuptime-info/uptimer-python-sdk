"""
Endpoint paths and deserialization for API v2.

The paths matter as much as the payloads: website monitoring is nested under
/v2/monitoring because it is one template among several to come, not the general
monitor model.
"""

from pytest_httpx import HTTPXMock

from tests.conftest import api_response
from uptimer.client import UptimerClient
from uptimer.models.v2 import (
    AGREEMENT_ALL,
    CreateWebsiteMonitorRequest,
    WebsiteMonitorRequest,
    WebsiteMonitorResponse,
    WebsiteMonitorResponseBody,
)


def test_paths(uptimer_client: UptimerClient):
    assert uptimer_client.v2.locations.path == "v2/locations"
    assert uptimer_client.v2.incidents.path == "v2/incidents"
    assert uptimer_client.v2.monitoring.path == "v2/monitoring"
    assert uptimer_client.v2.monitoring.websites.path == "v2/monitoring/websites"


def test_locations_deserialize(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(
        json=api_response(
            [{"id": "l1", "name": "de", "active_workers_count": 2, "kind": "location"}],
        ),
    )
    locations = uptimer_client.v2.locations.all()
    assert len(locations) == 1
    assert locations[0].name == "de"
    assert locations[0].active_workers_count == 2


def _monitor_payload() -> dict:
    return {
        "id": "m1",
        "name": "Checkout",
        "interval": 60,
        "workspace_id": "w1",
        "request": {
            "url": "https://example.com",
            "method": "GET",
            "content_type": "application/json",
            "data": "",
            "kind": "website_monitor_request",
        },
        "response": {
            "statuses": [200],
            "body": {"content": "ok", "kind": "website_monitor_response_body"},
            "kind": "website_monitor_response",
        },
        "locations": ["de"],
        "agreement": "all",
        "kind": "website_monitor",
    }


def test_monitor_deserializes_nested_kinds(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(json=api_response(_monitor_payload()))
    monitor = uptimer_client.v2.monitoring.websites.get("m1")
    assert monitor.id == "m1"
    assert monitor.agreement == AGREEMENT_ALL
    assert monitor.locations == ["de"]
    assert monitor.request.url == "https://example.com"
    assert monitor.response.statuses == [200]
    assert monitor.response.body.content == "ok"


def test_create_omits_an_empty_agreement(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    # An empty agreement means "leave it at the server default", which the
    # server expresses by omission — sending "" would be a different request.
    httpx_mock.add_response(json=api_response(_monitor_payload()))
    uptimer_client.v2.monitoring.websites.create(
        CreateWebsiteMonitorRequest(
            name="Checkout",
            interval=60,
            workspace_id="w1",
            request=WebsiteMonitorRequest(url="https://example.com", method="GET"),
            response=WebsiteMonitorResponse(
                statuses=[200],
                body=WebsiteMonitorResponseBody(content="ok"),
            ),
            locations=["de"],
        ),
    )
    sent = httpx_mock.get_requests()[0]
    assert b'"agreement"' not in sent.content
    assert b'"kind"' not in sent.content


def test_incident_deserializes_evidence(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(
        json=api_response(
            [
                {
                    "id": "i1",
                    "monitor_id": "m1",
                    "monitor_name": "Checkout",
                    "status": "problem",
                    "trouble_since": "2026-08-20T08:03:39Z",
                    "confirmed_at": "2026-08-20T08:06:39Z",
                    "well_since": None,
                    "locations": {"failing": ["de"], "unknown": [], "ok": ["us"]},
                    "kind": "incident",
                },
            ],
        ),
    )
    incidents = uptimer_client.v2.incidents.all("w1")
    assert len(incidents) == 1
    incident = incidents[0]
    assert incident.status == "problem"
    assert incident.locations.failing == ["de"]
    assert incident.locations.ok == ["us"]
    assert incident.well_since is None
