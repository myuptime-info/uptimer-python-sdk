"""
Custom observation ingest against a running Uptimer.

Unlike the other integration tests, this one does not drive the browser to mint
a key: reporting an observation needs a subject and a signal that already exist,
so the run supplies them. Set

    UPTIMER_API_KEY, UPTIMER_SUBJECT_SLUG, UPTIMER_SIGNAL_SLUG

and optionally UPTIMER_HTTP_SIGNAL_SLUG (a platform HTTP signal, to prove it is
refused) and UPTIMER_URL. Without the first three the module skips, so a plain
`--integration` run against a server with no custom signal stays green.
"""

import os
from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import integration_test
from uptimer.errors import DefaultUptimerApiError
from uptimer.models.v2 import (
    OBSERVATION_STATUS_OK,
    OBSERVATION_STATUS_PROBLEM,
    REJECT_ACCEPTED,
    REJECT_CLOCK_SKEW,
    CreateObservationRequest,
)

from .conftest import get_client

API_KEY = os.environ.get("UPTIMER_API_KEY", "")
SUBJECT_SLUG = os.environ.get("UPTIMER_SUBJECT_SLUG", "")
SIGNAL_SLUG = os.environ.get("UPTIMER_SIGNAL_SLUG", "")
HTTP_SIGNAL_SLUG = os.environ.get("UPTIMER_HTTP_SIGNAL_SLUG", "")

needs_signal = pytest.mark.skipif(
    not (API_KEY and SUBJECT_SLUG and SIGNAL_SLUG),
    reason="set UPTIMER_API_KEY, UPTIMER_SUBJECT_SLUG and UPTIMER_SIGNAL_SLUG",
)


def _observations(uptimer_url: str):  # noqa: ANN202
    client = get_client(API_KEY, uptimer_url)
    return client.v2.subjects(SUBJECT_SLUG).signals(SIGNAL_SLUG).observations


def _at(offset: timedelta = timedelta()) -> str:
    stamped = datetime.now(timezone.utc).replace(microsecond=0) + offset
    return stamped.isoformat().replace("+00:00", "Z")


@integration_test
@needs_signal
def test_report_an_accepted_observation(uptimer_url: str):
    stored = _observations(uptimer_url).create(
        CreateObservationRequest(
            status=OBSERVATION_STATUS_OK,
            observed_at=_at(),
            value=1.5,
            labels={"instance": "sdk-it"},
        ),
    )

    assert stored.kind == "observation"
    assert stored.subject_id == SUBJECT_SLUG
    assert stored.signal_id == SIGNAL_SLUG
    assert stored.status == OBSERVATION_STATUS_OK
    assert stored.value == 1.5
    assert stored.labels == {"instance": "sdk-it"}
    assert stored.accepted is True
    assert stored.reject_reason == REJECT_ACCEPTED
    assert stored.received_at


@integration_test
@needs_signal
def test_status_only_is_enough(uptimer_url: str):
    """Everything but status is optional; the server stamps the time."""
    stored = _observations(uptimer_url).create(
        CreateObservationRequest(status=OBSERVATION_STATUS_PROBLEM),
    )

    assert stored.accepted is True
    assert stored.status == OBSERVATION_STATUS_PROBLEM
    assert stored.observed_at


@integration_test
@needs_signal
def test_a_skewed_observation_is_stored_and_not_accepted(uptimer_url: str):
    """
    Stored, not raised.

    A timestamp far ahead of the server is kept and shown, never evaluated. The
    sender is told which of those two happened.
    """
    stored = _observations(uptimer_url).create(
        CreateObservationRequest(
            status=OBSERVATION_STATUS_OK,
            observed_at=_at(timedelta(hours=1)),
            labels={"instance": "sdk-it-skew"},
        ),
    )

    assert stored.accepted is False
    assert stored.reject_reason == REJECT_CLOCK_SKEW


@integration_test
@needs_signal
def test_an_invalid_status_is_refused(uptimer_url: str):
    with pytest.raises(DefaultUptimerApiError) as excinfo:
        _observations(uptimer_url).create(CreateObservationRequest(status="degraded"))
    assert "status" in excinfo.value.message.lower()


@integration_test
@needs_signal
def test_an_unknown_signal_is_refused(uptimer_url: str):
    client = get_client(API_KEY, uptimer_url)
    observations = client.v2.subjects(SUBJECT_SLUG).signals("no-such-signal").observations

    with pytest.raises(DefaultUptimerApiError) as excinfo:
        observations.create(CreateObservationRequest(status=OBSERVATION_STATUS_OK))
    assert excinfo.value.error_type == "not_found"


@integration_test
@pytest.mark.skipif(
    not (API_KEY and SUBJECT_SLUG and HTTP_SIGNAL_SLUG),
    reason="set UPTIMER_HTTP_SIGNAL_SLUG to prove the platform signal is refused",
)
def test_a_platform_http_signal_is_refused(uptimer_url: str):
    """Uptimer's own probe owns that stream; a posted claim is not a measurement."""
    client = get_client(API_KEY, uptimer_url)
    observations = (
        client.v2.subjects(SUBJECT_SLUG).signals(HTTP_SIGNAL_SLUG).observations
    )

    with pytest.raises(DefaultUptimerApiError) as excinfo:
        observations.create(CreateObservationRequest(status=OBSERVATION_STATUS_OK))
    assert excinfo.value.error_type == "forbidden"
