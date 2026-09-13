"""
Maintenance windows: `client.v2.subjects(slug).maintenance`.

A window holds back one subject's problem notifications until a time the
operator chose. What these pin is the shape of that: three operations and no
update, "nothing scheduled" answered as None rather than raised, and the one
promise the payload makes out loud — recoveries are never muted.

The payloads are copied from a real 1.7.0 server's answers.
"""

import pytest
from pytest_httpx import HTTPXMock

from tests.conftest import api_response
from uptimer.client import UptimerClient
from uptimer.errors import DefaultUptimerApiError
from uptimer.models.v2 import MaintenanceWindow, from_api_maintenance

RUNNING = {
    "subject_id": "payments-worker",
    "started_at": "2026-09-13T09:00:00Z",
    "ends_at": "2026-09-13T11:00:00Z",
    "cancelled_at": None,
    "active": True,
    "muted": ["problem", "no_data"],
    "kind": "maintenance_window",
}

CANCELLED = {
    **RUNNING,
    "cancelled_at": "2026-09-13T09:30:00Z",
    "active": False,
}


def test_nothing_scheduled_is_none_not_an_error(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    """
    A script asking "is it safe to deploy?" gets an answer, not an exception.

    The server answers a null result for a subject with no window, and turning
    that into a raise would make the ordinary case the exceptional one.
    """
    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v2/subjects/payments-worker/maintenance",
        json=api_response(None),
    )

    assert uptimer_client.v2.subjects("payments-worker").maintenance.get() is None


def test_start_sends_the_end_time_and_returns_the_window(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v2/subjects/payments-worker/maintenance",
        method="POST",
        json=api_response(RUNNING),
    )

    window = uptimer_client.v2.subjects("payments-worker").maintenance.start(
        "2026-09-13T11:00:00Z",
    )

    assert isinstance(window, MaintenanceWindow)
    assert window.active
    assert window.ends_at == "2026-09-13T11:00:00Z"
    assert window.cancelled_at is None

    request = httpx_mock.get_requests()[0]
    assert b'"ends_at"' in request.content
    assert b"2026-09-13T11:00:00Z" in request.content


def test_the_window_says_what_it_mutes(httpx_mock: HTTPXMock, uptimer_client: UptimerClient):
    """Recoveries are never in that list, and a client should not have to infer it."""
    httpx_mock.add_response(json=api_response(RUNNING))

    window = uptimer_client.v2.subjects("payments-worker").maintenance.get()

    assert window is not None
    assert "problem" in window.muted
    assert "up" not in window.muted


def test_cancel_returns_the_window_as_recorded(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v2/subjects/payments-worker/maintenance",
        method="DELETE",
        json=api_response(CANCELLED),
    )

    window = uptimer_client.v2.subjects("payments-worker").maintenance.cancel()

    assert not window.active
    assert window.cancelled_at == "2026-09-13T09:30:00Z"


def test_workspace_id_travels_to_the_maintenance_routes(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    """A slug is unique within a workspace, not across them."""
    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v2/subjects/payments-worker/maintenance?workspace_id=ws-2",
        json=api_response(RUNNING),
    )

    uptimer_client.v2.subjects("payments-worker", "ws-2").maintenance.get()


def test_a_past_end_time_is_raised_not_swallowed(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        json=api_response(
            None,
            error={
                "code": 2001,
                "error_type": "validation_error",
                "message": "invalid ends_at",
                "details": "A maintenance window has to end in the future. Nothing was changed.",
            },
        ),
    )

    with pytest.raises(DefaultUptimerApiError) as raised:
        uptimer_client.v2.subjects("payments-worker").maintenance.start("2020-01-01T00:00:00Z")

    assert raised.value.code == 2001
    assert len(httpx_mock.get_requests()) == 1


def test_a_second_window_is_raised(httpx_mock: HTTPXMock, uptimer_client: UptimerClient):
    """Cancel and start again is the flow; the SDK does not do it for you."""
    httpx_mock.add_response(
        json=api_response(
            None,
            error={
                "code": 2004,
                "error_type": "internal_error",
                "message": "Already in maintenance",
                "details": "This subject already has a window running. "
                "Cancel it before starting another.",
            },
        ),
    )

    with pytest.raises(DefaultUptimerApiError, match="Already in maintenance"):
        uptimer_client.v2.subjects("payments-worker").maintenance.start("2026-09-13T11:00:00Z")


def test_a_website_subject_is_refused_here_too(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        json=api_response(
            None,
            error={
                "code": 2004,
                "error_type": "internal_error",
                "message": "Website subjects are managed elsewhere",
                "details": "Use the v1 Website API (/v1/rules) or /v2/monitoring/websites; "
                "/v2/subjects is Custom-only",
            },
        ),
    )

    with pytest.raises(DefaultUptimerApiError, match="managed elsewhere"):
        uptimer_client.v2.subjects("checkout-api").maintenance.get()


def test_the_window_deserializes_from_the_real_payload():
    window = from_api_maintenance(RUNNING)

    assert isinstance(window, MaintenanceWindow)
    assert window.kind == "maintenance_window"
    assert window.subject_id == "payments-worker"
