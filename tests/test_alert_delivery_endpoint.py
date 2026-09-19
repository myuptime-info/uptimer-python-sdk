"""
A subject's alert delivery table (uptimer 1.8.0).

Reached as `.delivery` on a Custom subject and on a Website monitor.

The table is the resource, so `replace` means replace — a caller that expected a
merge would find a removed row reappearing, which is the bug an operator reports
as "it keeps notifying the channel I deleted".

The other half is the fallback: an empty table means one of two things, and the
server says which rather than leaving a client to compare ids itself.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from tests.conftest import api_response
from uptimer.models.v2 import (
    ALERT_KIND_NO_DATA,
    ALERT_KIND_PROBLEM,
    ALERT_KIND_RECOVERY,
    DeliverySelection,
)

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock

    from uptimer.client import UptimerClient

BASE = "http://127.0.0.1:2519"
SUBJECT = "payments-worker"


def _table(*, selections: list | None = None, fallback: str = "") -> dict:
    return {
        "subject_id": SUBJECT,
        "selections": selections if selections is not None else [],
        "default_destination_id": 1,
        "fallback": fallback,
        "workspace_id": "ws-1",
        "kind": "subject_alert_delivery",
    }


def test_an_empty_table_says_which_silence_it_is(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/delivery",
        json=api_response(_table(fallback="workspace_default")),
    )

    table = uptimer_client.v2.subjects(SUBJECT).delivery.get()

    assert table.selections == []
    assert table.uses_workspace_default
    assert not table.is_silent


def test_no_default_means_nothing_is_sent(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/delivery",
        json=api_response(_table(fallback="silence")),
    )

    table = uptimer_client.v2.subjects(SUBJECT).delivery.get()

    assert table.is_silent


def test_rows_carry_the_destination_name(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/delivery",
        json=api_response(
            _table(
                selections=[
                    {
                        "destination_id": 2,
                        "destination_name": "Pager relay",
                        "alert_kinds": ["problem", "no_data"],
                    },
                ],
            ),
        ),
    )

    table = uptimer_client.v2.subjects(SUBJECT).delivery.get()

    assert table.selections[0].destination_name == "Pager relay"
    assert table.selections[0].alert_kinds == [ALERT_KIND_PROBLEM, ALERT_KIND_NO_DATA]
    # With rows of its own, the subject does not also use the fallback.
    assert table.fallback == ""


def test_replace_sends_the_whole_table(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/delivery",
        json=api_response(_table()),
    )

    uptimer_client.v2.subjects(SUBJECT).delivery.replace(
        [
            DeliverySelection(
                destination_id=2,
                alert_kinds=[ALERT_KIND_PROBLEM, ALERT_KIND_RECOVERY],
            ),
        ],
    )

    sent = json.loads(httpx_mock.get_requests()[0].content)
    assert sent == {
        "selections": [
            {"destination_id": 2, "alert_kinds": ["problem", "recovery"]},
        ],
    }
    # The name is the server's to fill in; a request never sends it back.
    assert "destination_name" not in json.dumps(sent)


def test_replacing_with_nothing_is_the_same_as_clearing(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/delivery",
        json=api_response(_table(fallback="workspace_default")),
    )

    table = uptimer_client.v2.subjects(SUBJECT).delivery.replace([])

    assert json.loads(httpx_mock.get_requests()[0].content) == {"selections": []}
    assert table.uses_workspace_default


def test_clear_empties_the_table(httpx_mock: HTTPXMock, uptimer_client: UptimerClient):
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/delivery",
        method="DELETE",
        json=api_response(_table(fallback="workspace_default")),
    )

    table = uptimer_client.v2.subjects(SUBJECT).delivery.clear()

    assert table.selections == []


def test_a_website_monitor_carries_its_own_table(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    """
    Check that a monitor carries the table Custom subjects carry.

    Website monitoring is not served by /v2/subjects, so its delivery table
    hangs off the monitor — the collection that owns that kind of subject.
    """
    httpx_mock.add_response(
        url=f"{BASE}/v2/monitoring/websites/abc123/delivery",
        json=api_response(
            {
                "subject_id": "abc123",
                "selections": [
                    {"destination_id": 1, "destination_name": "Acme",
                     "alert_kinds": ["problem"]},
                ],
                "default_destination_id": 1,
                "fallback": "",
                "workspace_id": "ws-1",
                "kind": "subject_alert_delivery",
            },
        ),
    )

    table = uptimer_client.v2.monitoring.websites("abc123").delivery.get()

    assert table.selections[0].destination_id == 1


def test_the_workspace_rides_along_when_it_was_given(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    """
    Check that a named workspace reaches the nested routes.

    A subject slug is unique per workspace, not across them, so a caller who
    named one gets it carried down.
    """
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/delivery?workspace_id=ws-1",
        json=api_response(_table(fallback="silence")),
    )

    table = uptimer_client.v2.subjects(SUBJECT, "ws-1").delivery.get()

    assert table.is_silent
