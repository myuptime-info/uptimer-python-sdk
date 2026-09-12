"""
Acknowledgement against a running Uptimer 1.7.0+.

This one cannot create what it needs: an incident is opened by the engine when
something is actually wrong, and the SDK has no way to fake one. So the run is
handed subjects that already have one. Set

    UPTIMER_API_KEY, UPTIMER_WORKSPACE_ID

and then whichever halves you want covered:

    UPTIMER_CUSTOM_SUBJECT_SLUG   a Custom subject with at least one open incident
    UPTIMER_WEBSITE_SUBJECT_SLUG  a Website subject, to prove the cross-kind refusal
    UPTIMER_OTHER_WORKSPACE_ID    a second workspace you belong to, for the scoping check

and, for the states an API client cannot produce for itself — an incident closes
because the engine closed it:

    UPTIMER_CLOSED_INCIDENT_ID    a CLOSED incident of that subject that nobody acknowledged
    UPTIMER_CLOSED_ACKED_ID       a CLOSED incident of that subject acknowledged while it was open
    UPTIMER_CLOSED_ACKED_BY       who acknowledged it, and
    UPTIMER_CLOSED_ACKED_AT       when — so the answer can be compared with the original record

and, for the crossover cases, targets nothing else touches. They have to start
UNACKNOWLEDGED: an erroneous acknowledgement of an already-acknowledged incident
is an idempotent no-op, and would leave no trace for a test to catch.

    UPTIMER_UNACKED_CUSTOM_INCIDENT_ID    an open, unacknowledged incident of that subject
    UPTIMER_UNACKED_WEBSITE_MONITOR_UID   a website monitor with
    UPTIMER_UNACKED_WEBSITE_INCIDENT_ID   an open, unacknowledged incident

Each module skips without what it needs, so a plain `--integration` run stays
green.

It ACKNOWLEDGES a real incident, which is a write — a note that a person looked,
which nothing undoes. That is the point of the test and the reason it is opt-in:
it leaves the acknowledgement behind, exactly as a real caller would.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest

from tests.conftest import integration_test
from uptimer.errors import DefaultUptimerApiError
from uptimer.models.v2 import CreateSubjectRequest

from .conftest import get_client

if TYPE_CHECKING:
    from uptimer.endpoints.subjects import SubjectEndpoint
    from uptimer.models.v2 import SubjectIncident

API_KEY = os.environ.get("UPTIMER_API_KEY", "")
WORKSPACE_ID = os.environ.get("UPTIMER_WORKSPACE_ID", "")
CUSTOM_SUBJECT_SLUG = os.environ.get("UPTIMER_CUSTOM_SUBJECT_SLUG", "")
WEBSITE_SUBJECT_SLUG = os.environ.get("UPTIMER_WEBSITE_SUBJECT_SLUG", "")
OTHER_WORKSPACE_ID = os.environ.get("UPTIMER_OTHER_WORKSPACE_ID", "")
CLOSED_INCIDENT_ID = os.environ.get("UPTIMER_CLOSED_INCIDENT_ID", "")
CLOSED_ACKED_ID = os.environ.get("UPTIMER_CLOSED_ACKED_ID", "")
WEBSITE_INCIDENT_ID = os.environ.get("UPTIMER_WEBSITE_INCIDENT_ID", "")
CLOSED_ACKED_BY = os.environ.get("UPTIMER_CLOSED_ACKED_BY", "")
CLOSED_ACKED_AT = os.environ.get("UPTIMER_CLOSED_ACKED_AT", "")
UNACKED_CUSTOM_INCIDENT_ID = os.environ.get("UPTIMER_UNACKED_CUSTOM_INCIDENT_ID", "")
UNACKED_WEBSITE_MONITOR_UID = os.environ.get("UPTIMER_UNACKED_WEBSITE_MONITOR_UID", "")
UNACKED_WEBSITE_INCIDENT_ID = os.environ.get("UPTIMER_UNACKED_WEBSITE_INCIDENT_ID", "")

needs_workspace = pytest.mark.skipif(
    not (API_KEY and WORKSPACE_ID),
    reason="set UPTIMER_API_KEY and UPTIMER_WORKSPACE_ID",
)
needs_custom_subject = pytest.mark.skipif(
    not (API_KEY and WORKSPACE_ID and CUSTOM_SUBJECT_SLUG),
    reason="set UPTIMER_CUSTOM_SUBJECT_SLUG to a Custom subject with an open incident",
)
needs_website_subject = pytest.mark.skipif(
    not (API_KEY and WORKSPACE_ID and WEBSITE_SUBJECT_SLUG),
    reason="set UPTIMER_WEBSITE_SUBJECT_SLUG",
)
needs_other_workspace = pytest.mark.skipif(
    not (API_KEY and WORKSPACE_ID and CUSTOM_SUBJECT_SLUG and OTHER_WORKSPACE_ID),
    reason="set UPTIMER_OTHER_WORKSPACE_ID",
)
needs_closed_incident = pytest.mark.skipif(
    not (API_KEY and WORKSPACE_ID and CUSTOM_SUBJECT_SLUG and CLOSED_INCIDENT_ID),
    reason="set UPTIMER_CLOSED_INCIDENT_ID to a closed, never-acknowledged incident",
)
needs_closed_acknowledged = pytest.mark.skipif(
    not (
        API_KEY
        and WORKSPACE_ID
        and CUSTOM_SUBJECT_SLUG
        and CLOSED_ACKED_ID
        and CLOSED_ACKED_BY
        and CLOSED_ACKED_AT
    ),
    reason="set UPTIMER_CLOSED_ACKED_ID/_BY/_AT for an incident acknowledged before it closed",
)
needs_unacknowledged_custom = pytest.mark.skipif(
    not (API_KEY and WORKSPACE_ID and CUSTOM_SUBJECT_SLUG and UNACKED_CUSTOM_INCIDENT_ID),
    reason="set UPTIMER_UNACKED_CUSTOM_INCIDENT_ID to an open, unacknowledged incident",
)
needs_unacknowledged_website = pytest.mark.skipif(
    not (
        API_KEY
        and WORKSPACE_ID
        and CUSTOM_SUBJECT_SLUG
        and UNACKED_WEBSITE_MONITOR_UID
        and UNACKED_WEBSITE_INCIDENT_ID
    ),
    reason="set UPTIMER_UNACKED_WEBSITE_MONITOR_UID and UPTIMER_UNACKED_WEBSITE_INCIDENT_ID",
)
needs_website_incident = pytest.mark.skipif(
    not (API_KEY and WORKSPACE_ID and CUSTOM_SUBJECT_SLUG and WEBSITE_INCIDENT_ID),
    reason="set UPTIMER_WEBSITE_INCIDENT_ID to an open website incident",
)


def _unique_name() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"SDK acknowledgement {stamp}"


def _custom_incidents(uptimer_url: str) -> tuple[SubjectEndpoint, list[SubjectIncident]]:
    """
    Return the subject and the incidents a test may acknowledge.

    The crossover fixtures are excluded. They have to still be unacknowledged
    when those tests run — that is the whole of their evidence — so a test that
    only wants "an incident to acknowledge" must not reach for one of them.
    This keeps every test in the module order-independent.
    """
    client = get_client(API_KEY, uptimer_url)
    subject = client.v2.subjects(CUSTOM_SUBJECT_SLUG, WORKSPACE_ID)
    usable = [i for i in subject.incidents.all() if i.id != UNACKED_CUSTOM_INCIDENT_ID]
    return subject, usable


@integration_test
@needs_custom_subject
def test_list_then_acknowledge_then_read_back(uptimer_url: str):
    """The whole flow, and the reason the listing exists: id in, id out."""
    subject, incidents = _custom_incidents(uptimer_url)
    if not incidents:
        pytest.skip(f"{CUSTOM_SUBJECT_SLUG} has no open incident to acknowledge")

    target = incidents[0]
    assert target.id
    assert target.subject_id == CUSTOM_SUBJECT_SLUG
    assert target.rule_id, "an incident must name the rule that opened it"

    record = subject.incidents(target.id).acknowledge()

    assert record.incident_id == target.id
    assert record.subject_id == CUSTOM_SUBJECT_SLUG
    assert record.rule_id == target.rule_id
    assert record.acknowledged
    assert record.acknowledged_at
    assert record.acknowledged_by, "the record names whoever acknowledged it"
    assert record.monitor_id is None, "a custom answer carries no monitor identity"

    # Read back: the listing now says the same thing the write returned.
    after = {i.id: i for i in subject.incidents.all()}
    assert after[target.id].acknowledged
    assert after[target.id].acknowledged_by == record.acknowledged_by
    assert after[target.id].acknowledged_at == record.acknowledged_at


@integration_test
@needs_custom_subject
def test_acknowledging_twice_keeps_the_first_record(uptimer_url: str):
    subject, incidents = _custom_incidents(uptimer_url)
    if not incidents:
        pytest.skip(f"{CUSTOM_SUBJECT_SLUG} has no open incident to acknowledge")

    first = subject.incidents(incidents[0].id).acknowledge()
    again = subject.incidents(incidents[0].id).acknowledge()

    assert not again.recorded, "a repeat records nothing"
    assert again.acknowledged_by == first.acknowledged_by
    assert again.acknowledged_at == first.acknowledged_at


@integration_test
@needs_custom_subject
def test_every_open_incident_is_listed_and_only_the_named_one_is_touched(
    uptimer_url: str,
):
    """
    With more than one open, acknowledging one says nothing about the others.

    A subject with a single incident open still runs this: it then asserts the
    listing is what it claims to be, and the multi-incident half is skipped.
    """
    subject, incidents = _custom_incidents(uptimer_url)
    if not incidents:
        pytest.skip(f"{CUSTOM_SUBJECT_SLUG} has no open incident to acknowledge")

    assert all(i.subject_id == CUSTOM_SUBJECT_SLUG for i in incidents)
    if len(incidents) < 2:
        pytest.skip("this subject has one open incident; nothing to distinguish")

    target, other = incidents[0], incidents[1]
    was_acknowledged = other.acknowledged

    subject.incidents(target.id).acknowledge()

    after = {i.id: i for i in subject.incidents.all()}
    assert after[target.id].acknowledged
    assert after[other.id].acknowledged == was_acknowledged


@integration_test
@needs_website_subject
def test_a_website_subject_has_no_incidents_on_the_custom_route(uptimer_url: str):
    client = get_client(API_KEY, uptimer_url)

    with pytest.raises(DefaultUptimerApiError) as raised:
        client.v2.subjects(WEBSITE_SUBJECT_SLUG, WORKSPACE_ID).incidents.all()

    assert "managed elsewhere" in raised.value.message


@integration_test
@needs_custom_subject
def test_a_custom_incident_is_refused_by_the_website_route(uptimer_url: str):
    """The boundary, from a real id: no fallback, no second request."""
    client = get_client(API_KEY, uptimer_url)
    _, incidents = _custom_incidents(uptimer_url)
    if not incidents:
        pytest.skip(f"{CUSTOM_SUBJECT_SLUG} has no open incident")

    monitors = client.v2.monitoring.websites.all(WORKSPACE_ID)
    if not monitors:
        pytest.skip("this workspace has no website monitor to aim at")

    with pytest.raises(DefaultUptimerApiError) as raised:
        client.v1.rules(monitors[0].id).incidents(incidents[0].id).acknowledge()

    assert raised.value.code == 2002


@integration_test
@needs_other_workspace
def test_the_same_incident_is_not_reachable_through_another_workspace(
    uptimer_url: str,
):
    client = get_client(API_KEY, uptimer_url)
    _, incidents = _custom_incidents(uptimer_url)
    if not incidents:
        pytest.skip(f"{CUSTOM_SUBJECT_SLUG} has no open incident")

    elsewhere = client.v2.subjects(CUSTOM_SUBJECT_SLUG, OTHER_WORKSPACE_ID)

    with pytest.raises(DefaultUptimerApiError):
        elsewhere.incidents(incidents[0].id).acknowledge()


@integration_test
@needs_workspace
def test_a_website_incident_is_found_on_the_website_list_and_acknowledged_on_v1(
    uptimer_url: str,
):
    """
    The Website half keeps its own discovery path: `client.v2.incidents`.

    It has listed open website incidents since 1.5.0 and names the monitor each
    belongs to, which is everything the v1 acknowledge call takes.
    """
    client = get_client(API_KEY, uptimer_url)
    incidents = [
        i
        for i in client.v2.incidents.all(WORKSPACE_ID)
        if i.id != UNACKED_WEBSITE_INCIDENT_ID
    ]
    if not incidents:
        pytest.skip("no open website incident in this workspace")

    target = incidents[0]
    record = client.v1.rules(target.monitor_id).incidents(target.id).acknowledge()

    assert record.incident_id == target.id
    assert record.monitor_id == target.monitor_id
    assert record.acknowledged
    assert record.subject_id is None, "a website answer carries no subject identity"


@integration_test
@needs_closed_incident
def test_a_closed_incident_nobody_saw_is_refused(uptimer_url: str):
    """
    Closure refuses a FIRST acknowledgement: there is nothing left to be on.

    And it refuses without writing. Asking twice is how that is shown from the
    outside: an incident that had been acknowledged answers the record with
    recorded=False instead of refusing, so a second refusal is proof the first
    call stored nothing. A closed incident is absent from the open listing
    whatever its acknowledgement state, so that absence proves nothing here.
    """
    client = get_client(API_KEY, uptimer_url)
    subject = client.v2.subjects(CUSTOM_SUBJECT_SLUG, WORKSPACE_ID)

    with pytest.raises(DefaultUptimerApiError) as raised:
        subject.incidents(CLOSED_INCIDENT_ID).acknowledge()
    assert "closed" in raised.value.message.lower()

    with pytest.raises(DefaultUptimerApiError) as again:
        subject.incidents(CLOSED_INCIDENT_ID).acknowledge()
    assert "closed" in again.value.message.lower()


@integration_test
@needs_closed_acknowledged
def test_an_acknowledgement_survives_the_incident_closing(uptimer_url: str):
    """
    The other half of closure, and the one a blanket "closed is refused" hides.

    An incident acknowledged while it was open keeps that record after it
    closes, so asking again is not an error: it answers the ORIGINAL name and
    time with recorded=False. The look did happen.

    The fixture supplies who acknowledged it and when, because "some name, some
    time" would pass even if the server answered a different person — which is
    exactly the claim being made here.
    """
    client = get_client(API_KEY, uptimer_url)
    subject = client.v2.subjects(CUSTOM_SUBJECT_SLUG, WORKSPACE_ID)

    record = subject.incidents(CLOSED_ACKED_ID).acknowledge()

    assert record.acknowledged
    assert not record.recorded, "nothing is recorded on a closed incident"
    assert record.acknowledged_by == CLOSED_ACKED_BY
    assert record.acknowledged_at == CLOSED_ACKED_AT
    assert record.closed_at, "and the answer says the incident has closed"
    # A closed incident has no current condition, so status reads ok. closed_at
    # is what distinguishes that from "it is fine now".
    assert record.status == "ok"


@integration_test
@needs_custom_subject
def test_a_subject_with_nothing_wrong_lists_nothing(uptimer_url: str):
    """
    An empty list is an answer, not an error.

    The subject is created here rather than assumed: a brand-new Custom subject
    has no rules, so nothing can be open on it, which is exactly the state
    worth pinning.
    """
    client = get_client(API_KEY, uptimer_url)
    fresh = client.v2.subjects.create(
        CreateSubjectRequest(name=_unique_name(), workspace_id=WORKSPACE_ID),
    )

    assert client.v2.subjects(fresh.id, WORKSPACE_ID).incidents.all() == []


@integration_test
@needs_unacknowledged_website
def test_a_website_incident_is_refused_by_the_custom_route(uptimer_url: str):
    """
    The reverse crossover, as a WRITE, on a target nothing has acknowledged.

    Refusing the website subject's listing proves the read boundary; this is the
    mutation one. The target starts unacknowledged on purpose: an erroneous
    acknowledgement of an already-acknowledged incident would be an idempotent
    no-op, and every comparison would pass while the boundary leaked.

    The website incident list carries no acknowledgement state — /v2/incidents
    is unchanged by #190 — so the state is read back through the acknowledgement
    itself afterwards. `recorded=True` can only happen on an incident nothing
    had acknowledged, which is precisely what the refused call must have left.
    """
    client = get_client(API_KEY, uptimer_url)
    subject = client.v2.subjects(CUSTOM_SUBJECT_SLUG, WORKSPACE_ID)

    with pytest.raises(DefaultUptimerApiError) as raised:
        subject.incidents(UNACKED_WEBSITE_INCIDENT_ID).acknowledge()
    assert raised.value.code == 2002

    record = (
        client.v1.rules(UNACKED_WEBSITE_MONITOR_UID)
        .incidents(UNACKED_WEBSITE_INCIDENT_ID)
        .acknowledge()
    )
    assert record.recorded, (
        "this call had to be the first acknowledgement; if it was not, "
        "the refused Custom request had already written one"
    )
    assert record.monitor_id == UNACKED_WEBSITE_MONITOR_UID
    # And the Custom subject the call was aimed through did not gain it either.
    assert UNACKED_WEBSITE_INCIDENT_ID not in {i.id for i in subject.incidents.all()}


@integration_test
@needs_unacknowledged_custom
def test_a_custom_incident_refused_by_the_website_route_changes_nothing(
    uptimer_url: str,
):
    """
    The same proof in the other direction, and here the state is readable.

    The Custom listing carries the whole acknowledgement record, so the target's
    complete state — acknowledged, by whom, when — is compared before and after,
    together with every other incident's, rather than a pair of fields.
    """
    client = get_client(API_KEY, uptimer_url)
    subject = client.v2.subjects(CUSTOM_SUBJECT_SLUG, WORKSPACE_ID)

    monitors = client.v2.monitoring.websites.all(WORKSPACE_ID)
    if not monitors:
        pytest.skip("this workspace has no website monitor to aim at")

    def state() -> dict[str, tuple[bool, str | None, str]]:
        return {
            i.id: (i.acknowledged, i.acknowledged_at, i.acknowledged_by)
            for i in subject.incidents.all()
        }

    before = state()
    assert before.get(UNACKED_CUSTOM_INCIDENT_ID) == (False, None, ""), (
        "the target must start unacknowledged, or an erroneous acknowledgement "
        "would be invisible"
    )

    with pytest.raises(DefaultUptimerApiError) as raised:
        client.v1.rules(monitors[0].id).incidents(UNACKED_CUSTOM_INCIDENT_ID).acknowledge()
    assert raised.value.code == 2002

    after = state()
    assert after[UNACKED_CUSTOM_INCIDENT_ID] == (False, None, "")
    assert after == before, "no incident of this subject changed"
