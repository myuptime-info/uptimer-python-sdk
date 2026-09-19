"""
Notifications: `client.v2.notifications` (uptimer 1.8.0).

Three things a caller depends on here, and each is a request the SDK builds
rather than a value it reads back:

- the workspace is a QUERY parameter, because these resources have no slug;
- a `null` transformation is the built-in message, and has to survive
  serialization as null rather than being dropped;
- `undelivered` narrows the log, and the server reads the string "true".

The fourth is the one that would be silently wrong: a test send is a real send,
so a refusal has to raise rather than come back as a cheerful result.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from tests.conftest import api_response
from uptimer.errors import DefaultUptimerApiError
from uptimer.models.v2 import (
    ALERT_KIND_PROBLEM,
    DESTINATION_TYPE_SLACK,
    DESTINATION_TYPE_WEBHOOK,
    CreateDestinationRequest,
    CreateTransformationRequest,
    UpdateDestinationRequest,
    UpdateTransformationRequest,
)

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock

    from uptimer.client import UptimerClient

BASE = "http://127.0.0.1:2519"


def _destination(  # noqa: PLR0913 — one fixture, one field per thing a test varies
    *,
    destination_id: int = 1,
    name: str = "Acme · #incidents",
    destination_type: str = DESTINATION_TYPE_SLACK,
    enabled: bool = True,
    default: bool = True,
    transformation_id: int | None = None,
) -> dict:
    return {
        "id": destination_id,
        "name": name,
        "destination_type": destination_type,
        "channel": "incidents",
        "url": "https://hooks.example/acme",
        "enabled": enabled,
        "default": default,
        "transformation_id": transformation_id,
        "workspace_id": "ws-1",
        "created_at": "2026-09-19T08:33:48Z",
        "updated_at": "2026-09-19T08:33:48Z",
        "kind": "notification_destination",
    }


def _transformation(*, transformation_id: int = 1) -> dict:
    return {
        "id": transformation_id,
        "name": "PagerDuty compact",
        "template": '{"event": "{{ kind }}"}',
        "content_type": "application/json",
        "workspace_id": "ws-1",
        "created_at": "2026-09-19T08:33:48Z",
        "updated_at": "2026-09-19T08:33:48Z",
        "kind": "notification_transformation",
    }


def test_destinations_are_listed_for_a_workspace(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/notifications/destinations?workspace_id=ws-1",
        json=api_response([_destination()]),
    )

    destinations = uptimer_client.v2.notifications.destinations.all("ws-1")

    assert len(destinations) == 1
    assert destinations[0].name == "Acme · #incidents"
    # The channel comes back WITHOUT its '#', as stored.
    assert destinations[0].channel == "incidents"
    assert destinations[0].is_slack
    assert not destinations[0].is_transformed


def test_the_workspace_may_be_left_out(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    """A key whose owner belongs to one workspace need not name it."""
    httpx_mock.add_response(
        url=f"{BASE}/v2/notifications/destinations",
        json=api_response([]),
    )

    assert uptimer_client.v2.notifications.destinations.all() == []


def test_create_sends_the_whole_request(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/notifications/destinations?workspace_id=ws-1",
        json=api_response(_destination(destination_type=DESTINATION_TYPE_WEBHOOK)),
    )

    uptimer_client.v2.notifications.destinations.create(
        CreateDestinationRequest(
            name="Pager relay",
            url="https://hooks.example/pager",
            destination_type=DESTINATION_TYPE_WEBHOOK,
        ),
        workspace_id="ws-1",
    )

    sent = json.loads(httpx_mock.get_requests()[0].content)
    assert sent["name"] == "Pager relay"
    assert sent["destination_type"] == DESTINATION_TYPE_WEBHOOK
    # Null is the DEFAULT attachment, not an omission: it has to be sent.
    assert "transformation_id" in sent
    assert sent["transformation_id"] is None


def test_update_carries_no_type(httpx_mock: HTTPXMock, uptimer_client: UptimerClient):
    """The type is fixed at creation, so an update cannot offer to change it."""
    httpx_mock.add_response(
        url=f"{BASE}/v2/notifications/destinations/1?workspace_id=ws-1",
        json=api_response(_destination()),
    )

    uptimer_client.v2.notifications.destinations.update(
        1,
        UpdateDestinationRequest(name="Acme", url="https://hooks.example/moved"),
        workspace_id="ws-1",
    )

    sent = json.loads(httpx_mock.get_requests()[0].content)
    assert "destination_type" not in sent


def test_enabled_and_default_are_their_own_calls(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/notifications/destinations/1/enabled?workspace_id=ws-1",
        json=api_response(_destination(enabled=False)),
    )
    httpx_mock.add_response(
        url=f"{BASE}/v2/notifications/destinations/2/default?workspace_id=ws-1",
        json=api_response(_destination(destination_id=2)),
    )

    off = uptimer_client.v2.notifications.destinations.set_enabled(
        1,
        enabled=False,
        workspace_id="ws-1",
    )
    promoted = uptimer_client.v2.notifications.destinations.make_default(
        2,
        workspace_id="ws-1",
    )

    assert off.enabled is False
    assert promoted.default is True
    assert json.loads(httpx_mock.get_requests()[0].content) == {"enabled": False}


def test_a_refused_test_send_raises(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    """
    Check that a refused test send raises.

    It is a REAL send, so a destination that refuses is not a success with a sad
    message in it.
    """
    httpx_mock.add_response(
        url=f"{BASE}/v2/notifications/destinations/1/test?workspace_id=ws-1",
        json=api_response(
            None,
            {
                "code": 2004,
                "message": "Destination did not accept the test message",
                "details": "the address answered 403 Forbidden",
            },
        ),
    )

    with pytest.raises(DefaultUptimerApiError):
        uptimer_client.v2.notifications.destinations.send_test(1, workspace_id="ws-1")


def test_delete_says_whether_it_was_the_default(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    """Deleting the default promotes nobody, so the caller has to be told."""
    httpx_mock.add_response(
        url=f"{BASE}/v2/notifications/destinations/1?workspace_id=ws-1",
        json=api_response(
            {
                "message": "Destination deleted successfully",
                "destination_id": 1,
                "workspace_id": "ws-1",
                "was_default": True,
            },
        ),
    )

    answer = uptimer_client.v2.notifications.destinations.delete(1, workspace_id="ws-1")

    assert answer.was_default is True


def test_samples_need_no_workspace(httpx_mock: HTTPXMock, uptimer_client: UptimerClient):
    """They are the product's own fixtures, not a tenant's."""
    httpx_mock.add_response(
        url=f"{BASE}/v2/notifications/transformations/samples",
        json=api_response(
            [
                {
                    "alert_kind": "problem",
                    "label": "Problems and reminders",
                    "fields": {"kind": "problem", "subject": "Checkout API"},
                },
            ],
        ),
    )

    samples = uptimer_client.v2.notifications.transformations.samples()

    assert samples[0].alert_kind == ALERT_KIND_PROBLEM
    assert samples[0].fields["subject"] == "Checkout API"


def test_preview_reports_every_sample(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/notifications/transformations/preview?workspace_id=ws-1",
        json=api_response(
            {
                "passed": False,
                "results": [
                    {"alert_kind": "problem", "label": "Problems and reminders",
                     "ok": True, "output": "{}"},
                    {"alert_kind": "recovery", "label": "Recoveries", "ok": False,
                     "error": "the rendered body is not valid JSON"},
                ],
                "kind": "notification_transformation_preview",
            },
        ),
    )

    preview = uptimer_client.v2.notifications.transformations.preview(
        '{"detail": {{ error }}}',
        workspace_id="ws-1",
    )

    assert preview.passed is False
    assert len(preview.results) == 2
    assert preview.results[1].error


def test_transformation_round_trip(httpx_mock: HTTPXMock, uptimer_client: UptimerClient):
    httpx_mock.add_response(
        url=f"{BASE}/v2/notifications/transformations?workspace_id=ws-1",
        json=api_response(_transformation()),
    )
    httpx_mock.add_response(
        url=f"{BASE}/v2/notifications/transformations/1?workspace_id=ws-1",
        json=api_response(_transformation()),
    )

    created = uptimer_client.v2.notifications.transformations.create(
        CreateTransformationRequest(name="PagerDuty compact", template='{"event": "x"}'),
        workspace_id="ws-1",
    )
    updated = uptimer_client.v2.notifications.transformations.update(
        1,
        UpdateTransformationRequest(name="PagerDuty compact", template='{"event": "y"}'),
        workspace_id="ws-1",
    )

    assert created.content_type == "application/json"
    assert updated.id == 1


def test_the_log_filters_on_destination_and_undelivered(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/notifications/deliveries"
        "?workspace_id=ws-1&destination_id=2&undelivered=true",
        json=api_response(
            [
                {
                    "id": 12,
                    "destination_id": 2,
                    "destination_name": "Pager relay",
                    "destination_type": "webhook",
                    "alert_kind": "problem",
                    "status": "failed",
                    "payload": '{"attachments":[]}',
                    "error": "403 Forbidden",
                    "at": "2026-09-19T08:33:48Z",
                    "kind": "notification_delivery",
                },
            ],
        ),
    )

    records = uptimer_client.v2.notifications.deliveries.all(
        workspace_id="ws-1",
        destination_id=2,
        undelivered=True,
    )

    assert len(records) == 1
    assert records[0].delivered is False
    # The destination is a SNAPSHOT: the log outlives what it describes.
    assert records[0].destination_name == "Pager relay"


def test_an_unfiltered_log_sends_no_undelivered_flag(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/notifications/deliveries?workspace_id=ws-1",
        json=api_response([]),
    )

    assert uptimer_client.v2.notifications.deliveries.all(workspace_id="ws-1") == []
