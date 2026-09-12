"""
Acknowledging an incident: `client.v1.rules(...)` and `client.v2.subjects(...)`.

Uptimer splits its API by kind, and acknowledgement is no exception: a website
incident is acknowledged under its monitor on v1, a custom one under its subject
on v2. The two things worth pinning here are that each method calls ONLY its own
route, and that a refusal from the other family is raised rather than retried
somewhere else — a client that "helpfully" fell back would acknowledge an
incident nobody named.

The payloads below are copied from a real 1.7.0 server's answers, so what these
assert is the wire, not a guess about it.
"""

import json

import pytest
from pytest_httpx import HTTPXMock

from tests.conftest import api_response
from uptimer.client import UptimerClient
from uptimer.errors import DefaultUptimerApiError
from uptimer.models.errors import TypeMismatchError
from uptimer.models.v2 import (
    STATUS_PROBLEM,
    IncidentAcknowledgement,
    SubjectIncident,
    from_api_acknowledgement,
    from_api_subject_incident,
)

WEBSITE_ACK = {
    "incident_id": "xeOkfGadru8",
    "monitor_id": "golden-rule-uid-0001",
    "status": "problem",
    "acknowledged": True,
    "acknowledged_at": "2026-09-12T11:30:57.292660006Z",
    "acknowledged_by": "goldenuser",
    "recorded": True,
    "trouble_since": "2026-09-12T10:30:57.282862232Z",
    "confirmed_at": "2026-09-12T10:30:57.282862232Z",
    "well_since": None,
    "closed_at": None,
    "kind": "incident_acknowledgement",
}

CUSTOM_ACK = {
    "incident_id": "v8dLj9O1tzs",
    "subject_id": "nightly-export",
    "rule_id": "export-health",
    "status": "problem",
    "acknowledged": True,
    "acknowledged_at": "2026-09-12T11:30:57.297065207Z",
    "acknowledged_by": "goldenuser",
    "recorded": True,
    "trouble_since": "2026-09-12T10:30:57.290195336Z",
    "confirmed_at": "2026-09-12T10:30:57.290195336Z",
    "well_since": None,
    "closed_at": None,
    "kind": "incident_acknowledgement",
}


def _subject_incident(
    *,
    incident_id: str = "xeOkfGadru8",
    rule_id: str = "export-health",
    rule_name: str = "Export health",
    acknowledged: bool = False,
    trouble_since: str = "2026-09-12T10:47:45.324694112Z",
) -> dict:
    return {
        "id": incident_id,
        "subject_id": "nightly-export",
        "rule_id": rule_id,
        "rule_name": rule_name,
        "status": "problem",
        "trouble_since": trouble_since,
        "confirmed_at": trouble_since,
        "well_since": None,
        "acknowledged": acknowledged,
        "acknowledged_at": "2026-09-12T11:47:45.331247079Z" if acknowledged else None,
        "acknowledged_by": "goldenuser" if acknowledged else "",
        "kind": "subject_incident",
    }


# -- the website family ------------------------------------------------------


def test_website_acknowledge_calls_the_v1_route(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v1/rules/golden-rule-uid-0001/incidents/xeOkfGadru8/acknowledge",
        method="POST",
        json=api_response(WEBSITE_ACK),
    )

    record = (
        uptimer_client.v1.rules("golden-rule-uid-0001")
        .incidents("xeOkfGadru8")
        .acknowledge()
    )

    assert isinstance(record, IncidentAcknowledgement)
    assert record.incident_id == "xeOkfGadru8"
    assert record.monitor_id == "golden-rule-uid-0001"
    assert record.is_website
    assert not record.is_custom
    # The condition is untouched by the acknowledgement.
    assert record.status == STATUS_PROBLEM
    assert record.acknowledged_by == "goldenuser"
    assert record.recorded


def test_website_acknowledge_sends_no_body(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    """
    The actor is the API key's owner, so there is nothing to send.

    The server refuses a body rather than ignoring it, and an SDK that invented
    one would turn every acknowledgement into a validation error.
    """
    httpx_mock.add_response(json=api_response(WEBSITE_ACK))

    uptimer_client.v1.rules("mon-1").incidents("inc-1").acknowledge()

    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert request.content == b""


def test_website_acknowledge_needs_a_monitor_and_an_incident(
    uptimer_client: UptimerClient,
):
    with pytest.raises(ValueError, match="monitor uid is required"):
        uptimer_client.v1.rules("")
    with pytest.raises(ValueError, match="incident id is required"):
        uptimer_client.v1.rules("mon-1").incidents("  ")


# -- the custom family -------------------------------------------------------


def test_subject_incidents_lists_open_ones(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v2/subjects/nightly-export/incidents",
        json=api_response(
            [
                _subject_incident(
                    incident_id="v8dLj9O1tzs",
                    rule_id="queue-depth",
                    rule_name="Queue depth",
                    trouble_since="2026-09-12T10:47:45.326058521Z",
                ),
                _subject_incident(acknowledged=True),
            ],
        ),
    )

    incidents = uptimer_client.v2.subjects("nightly-export").incidents.all()

    assert [i.id for i in incidents] == ["v8dLj9O1tzs", "xeOkfGadru8"]
    assert all(isinstance(i, SubjectIncident) for i in incidents)
    # The rule is the attribution a custom incident has instead of a monitor.
    assert incidents[0].rule_id == "queue-depth"
    assert incidents[0].rule_name == "Queue depth"
    assert not incidents[0].acknowledged
    # An already-acknowledged incident is listed like any other: it is still
    # open, and who is on it is half of what this answers.
    assert incidents[1].acknowledged
    assert incidents[1].acknowledged_by == "goldenuser"


def test_subject_with_nothing_open_lists_nothing(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(json=api_response([]))

    assert uptimer_client.v2.subjects("nightly-export").incidents.all() == []


def test_custom_acknowledge_calls_the_v2_route(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v2/subjects/nightly-export/incidents/v8dLj9O1tzs/acknowledge",
        method="POST",
        json=api_response(CUSTOM_ACK),
    )

    record = (
        uptimer_client.v2.subjects("nightly-export")
        .incidents("v8dLj9O1tzs")
        .acknowledge()
    )

    assert record.subject_id == "nightly-export"
    assert record.rule_id == "export-health"
    assert record.is_custom
    assert not record.is_website
    assert record.monitor_id is None


def test_workspace_id_travels_to_the_custom_routes(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    """
    A slug is unique within a workspace, not across them.

    So when the caller settles that ambiguity, both the listing and the
    acknowledgement have to carry it — acknowledging in the wrong workspace is
    exactly the mistake the parameter exists to prevent.
    """
    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v2/subjects/nightly-export/incidents?workspace_id=ws-2",
        json=api_response([]),
    )
    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v2/subjects/nightly-export/incidents/v8dLj9O1tzs/acknowledge?workspace_id=ws-2",
        method="POST",
        json=api_response(CUSTOM_ACK),
    )

    subject = uptimer_client.v2.subjects("nightly-export", "ws-2")
    subject.incidents.all()
    subject.incidents("v8dLj9O1tzs").acknowledge()


# -- the boundary between them ----------------------------------------------


def test_a_wrong_family_refusal_is_raised_not_retried(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    """
    A custom incident id offered to the website route is refused, and that is it.

    Falling back to the other family would acknowledge an incident the caller
    never named through a parent they never named. One request in, one refusal
    out.
    """
    httpx_mock.add_response(
        json=api_response(
            None,
            error={
                "code": 2002,
                "error_type": "not_found",
                "message": "Incident not found",
                "details": 'No incident "v8dLj9O1tzs" on monitor "golden-rule-uid-0001"',
            },
        ),
    )

    with pytest.raises(DefaultUptimerApiError) as raised:
        uptimer_client.v1.rules("golden-rule-uid-0001").incidents("v8dLj9O1tzs").acknowledge()

    assert raised.value.code == 2002
    assert raised.value.message == "Incident not found"
    assert len(httpx_mock.get_requests()) == 1


def test_a_website_subject_is_refused_on_the_custom_route(
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

    with pytest.raises(DefaultUptimerApiError) as raised:
        uptimer_client.v2.subjects("checkout-api").incidents.all()

    assert raised.value.code == 2004
    assert len(httpx_mock.get_requests()) == 1


def test_a_closed_incident_is_raised(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        json=api_response(
            None,
            error={
                "code": 2004,
                "error_type": "internal_error",
                "message": "Incident is closed",
                "details": "This incident has closed, so nothing was recorded. "
                "Anything open now is a different incident.",
            },
        ),
    )

    with pytest.raises(DefaultUptimerApiError, match="Incident is closed"):
        uptimer_client.v2.subjects("nightly-export").incidents("v8dLj9O1tzs").acknowledge()


# -- what a repeat says ------------------------------------------------------


def test_a_repeat_reports_the_first_person(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    """
    Acknowledging again is a success, not a conflict.

    The answer is the RECORD, so it carries the first person's name and time,
    and `recorded` is False. A client raising here would be wrong about the
    product.
    """
    repeat = {**WEBSITE_ACK, "recorded": False, "acknowledged_by": "someone-else"}
    httpx_mock.add_response(json=api_response(repeat))

    record = uptimer_client.v1.rules("mon-1").incidents("inc-1").acknowledge()

    assert record.acknowledged
    assert not record.recorded
    assert record.acknowledged_by == "someone-else"


# -- serialization -----------------------------------------------------------


def test_acknowledgement_deserializes_from_the_real_payload():
    record = from_api_acknowledgement(json.loads(json.dumps(CUSTOM_ACK)))

    assert isinstance(record, IncidentAcknowledgement)
    assert record.kind == "incident_acknowledgement"
    assert record.closed_at is None


def test_a_closed_incident_carries_its_closing_time():
    """
    A closed incident reads status "ok", because it has no current condition.

    `closed_at` is what distinguishes "it closed" from "it is fine now", which
    is why the model keeps it.
    """
    payload = {
        **WEBSITE_ACK,
        "status": "ok",
        "recorded": False,
        "well_since": "2026-09-12T11:30:57.826967424Z",
        "closed_at": "2026-09-12T11:30:57.826967424Z",
    }

    record = from_api_acknowledgement(payload)

    assert record.status == "ok"
    assert record.closed_at is not None
    assert record.acknowledged


def test_subject_incident_deserializes_from_the_real_payload():
    incident = from_api_subject_incident(_subject_incident())

    assert isinstance(incident, SubjectIncident)
    assert incident.kind == "subject_incident"
    assert incident.acknowledged_by == ""


def test_a_website_incident_is_not_a_subject_incident():
    """The kinds are checked, so a payload from the other list is caught."""
    with pytest.raises(TypeMismatchError):
        from_api_subject_incident(
            {
                "id": "xeOkfGadru8",
                "monitor_id": "mon-1",
                "monitor_name": "home",
                "status": "problem",
                "trouble_since": "2026-09-12T10:47:45Z",
                "confirmed_at": None,
                "well_since": None,
                "locations": {"failing": [], "unknown": [], "ok": []},
                "kind": "incident",
            },
        )
