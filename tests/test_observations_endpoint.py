"""
Custom observation ingest: `client.v2.subjects(s).signals(g).observations`.

The path is the contract as much as the payload — a signal slug is unique
within its subject, not across the workspace, so the pair is the address and
both halves must reach the URL intact.

The other half of the contract is what is NOT an error: a stored observation
the engine will not evaluate comes back with `accepted: False`, because it was
received. Only a request that stored nothing raises.
"""

import json

import pytest
from pytest_httpx import HTTPXMock

from tests.conftest import api_response
from uptimer.client import UptimerClient
from uptimer.errors import DefaultUptimerApiError
from uptimer.models.v2 import (
    OBSERVATION_STATUS_OK,
    OBSERVATION_STATUS_PROBLEM,
    REJECT_ACCEPTED,
    REJECT_CLOCK_SKEW,
    CreateObservationRequest,
    Observation,
    from_api_observation,
)


def _stored(
    *,
    accepted: bool = True,
    reject_reason: str = REJECT_ACCEPTED,
    status: str = OBSERVATION_STATUS_OK,
) -> dict:
    return {
        "subject_id": "checkout",
        "signal_id": "worker-pulse",
        "observed_at": "2026-08-30T12:00:00Z",
        "received_at": "2026-08-30T12:00:01Z",
        "status": status,
        "value": 1.5,
        "error": "",
        "labels": {"instance": "i-123"},
        "accepted": accepted,
        "reject_reason": reject_reason,
        "kind": "observation",
    }


def test_paths(uptimer_client: UptimerClient):
    assert uptimer_client.v2.subjects.path == "v2/subjects"
    subject = uptimer_client.v2.subjects("checkout")
    assert subject.signals.path == "v2/subjects/checkout/signals"
    assert (
        subject.signals("worker-pulse").observations.path
        == "v2/subjects/checkout/signals/worker-pulse/observations"
    )


def test_slugs_are_escaped_into_the_path(uptimer_client: UptimerClient):
    """A slug is data, not a path fragment: a slash must not address elsewhere."""
    observations = uptimer_client.v2.subjects("a/b").signals("c d").observations
    assert observations.path == "v2/subjects/a%2Fb/signals/c%20d/observations"


@pytest.mark.parametrize("slug", ["", "   "])
def test_an_empty_slug_is_refused(uptimer_client: UptimerClient, slug: str):
    with pytest.raises(ValueError, match="slug is required"):
        uptimer_client.v2.subjects(slug)
    with pytest.raises(ValueError, match="slug is required"):
        uptimer_client.v2.subjects("checkout").signals(slug)


def test_create_posts_to_the_signals_observations_url(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(json=api_response(_stored()))

    uptimer_client.v2.subjects("checkout").signals("worker-pulse").observations.create(
        CreateObservationRequest(status=OBSERVATION_STATUS_OK),
    )

    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert str(request.url).endswith(
        "/v2/subjects/checkout/signals/worker-pulse/observations",
    )


def test_create_sends_only_the_fields_that_were_set(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    """
    Only what was set is sent.

    The server rejects unknown fields and reads an absent optional differently
    from a null one — an absent observed_at means "stamp it now".
    """
    httpx_mock.add_response(json=api_response(_stored()))

    uptimer_client.v2.subjects("checkout").signals("worker-pulse").observations.create(
        CreateObservationRequest(status=OBSERVATION_STATUS_OK),
    )

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body == {"status": "ok"}


def test_create_sends_every_field_that_was_set(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(json=api_response(_stored()))

    uptimer_client.v2.subjects("checkout").signals("worker-pulse").observations.create(
        CreateObservationRequest(
            status=OBSERVATION_STATUS_PROBLEM,
            observed_at="2026-08-30T12:00:00Z",
            value=0.0,
            error="connection refused",
            labels={"instance": "i-123"},
        ),
    )

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body == {
        "status": "problem",
        "observed_at": "2026-08-30T12:00:00Z",
        "value": 0.0,
        "error": "connection refused",
        "labels": {"instance": "i-123"},
    }


def test_create_returns_the_stored_observation(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(json=api_response(_stored()))

    stored = uptimer_client.v2.subjects("checkout").signals(
        "worker-pulse",
    ).observations.create(CreateObservationRequest(status=OBSERVATION_STATUS_OK))

    assert isinstance(stored, Observation)
    assert stored.subject_id == "checkout"
    assert stored.signal_id == "worker-pulse"
    assert stored.status == OBSERVATION_STATUS_OK
    assert stored.value == 1.5
    assert stored.labels == {"instance": "i-123"}
    assert stored.accepted is True
    assert stored.reject_reason == REJECT_ACCEPTED
    assert stored.kind == "observation"


def test_a_refused_observation_is_returned_not_raised(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    """
    A refused observation is a result, not an error.

    It was received and stored; the engine just will not evaluate it. Raising
    here would tell a sender its data never arrived, which is the opposite of
    what happened.
    """
    httpx_mock.add_response(
        json=api_response(
            _stored(
                accepted=False,
                reject_reason=REJECT_CLOCK_SKEW,
                status=OBSERVATION_STATUS_PROBLEM,
            ),
        ),
    )

    stored = uptimer_client.v2.subjects("checkout").signals(
        "worker-pulse",
    ).observations.create(CreateObservationRequest(status=OBSERVATION_STATUS_PROBLEM))

    assert stored.accepted is False
    assert stored.reject_reason == REJECT_CLOCK_SKEW


def test_an_api_error_is_raised(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    """A platform HTTP signal refuses posted observations, and so does a bad body."""
    httpx_mock.add_response(
        json=api_response(
            None,
            error={
                "code": 2003,
                "error_type": "forbidden",
                "message": "Signal does not accept posted observations",
                "details": "only custom heartbeat and custom event signals accept posted observations",
            },
        ),
    )

    with pytest.raises(DefaultUptimerApiError):
        uptimer_client.v2.subjects("checkout").signals(
            "website-http",
        ).observations.create(CreateObservationRequest(status=OBSERVATION_STATUS_OK))


def test_observation_kind_is_registered():
    """Without the kind, from_api cannot build this object at all."""
    stored = from_api_observation(_stored())
    assert isinstance(stored, Observation)
    assert stored.accepted is True
