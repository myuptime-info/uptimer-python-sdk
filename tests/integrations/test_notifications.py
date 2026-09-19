"""
Destinations, transformations and alert delivery against a running Uptimer.

Needs a server at **1.8.0 or later** and an EDITOR key: reading a destination is
gated like changing one, because a destination holds a webhook URL. Set

    UPTIMER_API_KEY, UPTIMER_WORKSPACE_ID

and optionally UPTIMER_URL. Without the first two the module skips, so a plain
`--integration` run stays green.

It cleans up after itself — every destination and transformation it creates is
deleted at the end of the test that made it — because these are a workspace's
real alerting configuration, not scratch data.

The destination it creates points at a URL that accepts nothing, and the test
NEVER sends to it: a test send is a real send, and an integration run must not
put a message in somebody's channel.
"""

import os
from datetime import datetime, timezone

import pytest

from tests.conftest import integration_test
from uptimer.models.v2 import (
    ALERT_KIND_PROBLEM,
    ALERT_KIND_RECOVERY,
    DESTINATION_TYPE_WEBHOOK,
    CreateDestinationRequest,
    CreateTransformationRequest,
    DeliverySelection,
    UpdateDestinationRequest,
)

from .conftest import get_client

API_KEY = os.environ.get("UPTIMER_API_KEY", "")
WORKSPACE_ID = os.environ.get("UPTIMER_WORKSPACE_ID", "")
# A Custom subject slug, to exercise the per-subject delivery table. Optional.
SUBJECT_SLUG = os.environ.get("UPTIMER_SUBJECT_SLUG", "")

needs_workspace = pytest.mark.skipif(
    not (API_KEY and WORKSPACE_ID),
    reason="set UPTIMER_API_KEY and UPTIMER_WORKSPACE_ID",
)
needs_subject = pytest.mark.skipif(
    not (API_KEY and WORKSPACE_ID and SUBJECT_SLUG),
    reason="set UPTIMER_SUBJECT_SLUG as well",
)


def _unique(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix} {stamp}"


@integration_test
@needs_workspace
def test_a_destination_round_trip(uptimer_url: str):
    client = get_client(API_KEY, uptimer_url)
    destinations = client.v2.notifications.destinations

    created = destinations.create(
        CreateDestinationRequest(
            name=_unique("SDK integration"),
            url="https://127.0.0.1:1/never",
            destination_type=DESTINATION_TYPE_WEBHOOK,
        ),
        workspace_id=WORKSPACE_ID,
    )
    try:
        assert created.enabled is True
        assert created.transformation_id is None

        fetched = destinations.get(created.id, workspace_id=WORKSPACE_ID)
        assert fetched.name == created.name

        moved = destinations.update(
            created.id,
            UpdateDestinationRequest(
                name=created.name,
                url="https://127.0.0.1:1/moved",
            ),
            workspace_id=WORKSPACE_ID,
        )
        assert moved.url.endswith("/moved")

        off = destinations.set_enabled(
            created.id,
            enabled=False,
            workspace_id=WORKSPACE_ID,
        )
        assert off.enabled is False

        assert any(d.id == created.id for d in destinations.all(WORKSPACE_ID))
    finally:
        answer = destinations.delete(created.id, workspace_id=WORKSPACE_ID)
        assert answer.destination_id == created.id


@integration_test
@needs_workspace
def test_a_transformation_is_judged_against_every_sample(uptimer_url: str):
    client = get_client(API_KEY, uptimer_url)
    transformations = client.v2.notifications.transformations

    samples = transformations.samples()
    assert {s.alert_kind for s in samples} == {"problem", "no_data", "recovery"}

    # A template that breaks on one message: a recovery has no error, so the
    # document stops parsing. The server refuses it, and preview says so first.
    refused = transformations.preview(
        '{"detail": {{ error }}}',
        workspace_id=WORKSPACE_ID,
    )
    assert refused.passed is False

    good = transformations.preview(
        '{"event": "{{ kind }}", "summary": "{{ summary }}"}',
        workspace_id=WORKSPACE_ID,
    )
    assert good.passed is True

    created = transformations.create(
        CreateTransformationRequest(
            name=_unique("SDK integration"),
            template='{"event": "{{ kind }}", "summary": "{{ summary }}"}',
        ),
        workspace_id=WORKSPACE_ID,
    )
    try:
        assert created.content_type == "application/json"
    finally:
        transformations.delete(created.id, workspace_id=WORKSPACE_ID)


@integration_test
@needs_subject
def test_a_subject_chooses_its_destinations(uptimer_url: str):
    client = get_client(API_KEY, uptimer_url)
    destinations = client.v2.notifications.destinations
    delivery = client.v2.subjects(SUBJECT_SLUG, WORKSPACE_ID).delivery

    before = delivery.get()
    created = destinations.create(
        CreateDestinationRequest(
            name=_unique("SDK integration"),
            url="https://127.0.0.1:1/never",
            destination_type=DESTINATION_TYPE_WEBHOOK,
        ),
        workspace_id=WORKSPACE_ID,
    )
    try:
        saved = delivery.replace(
            [
                DeliverySelection(
                    destination_id=created.id,
                    alert_kinds=[ALERT_KIND_PROBLEM, ALERT_KIND_RECOVERY],
                ),
            ],
        )
        assert [row.destination_id for row in saved.selections] == [created.id]
        assert saved.fallback == ""

        # Replace, not merge: sending one row leaves exactly one row.
        again = delivery.replace(
            [DeliverySelection(destination_id=created.id, alert_kinds=[ALERT_KIND_PROBLEM])],
        )
        assert again.selections[0].alert_kinds == [ALERT_KIND_PROBLEM]

        cleared = delivery.clear()
        assert cleared.selections == []
        assert cleared.fallback in {"workspace_default", "silence"}
    finally:
        # Put the subject back the way it was found.
        delivery.replace(
            [
                DeliverySelection(
                    destination_id=row.destination_id,
                    alert_kinds=row.alert_kinds,
                )
                for row in before.selections
            ],
        )
        destinations.delete(created.id, workspace_id=WORKSPACE_ID)


@integration_test
@needs_workspace
def test_the_delivery_log_reads(uptimer_url: str):
    """The log is a read; an empty workspace answers with an empty list."""
    client = get_client(API_KEY, uptimer_url)

    records = client.v2.notifications.deliveries.all(workspace_id=WORKSPACE_ID)

    assert isinstance(records, list)
    for record in records:
        assert record.destination_name
        assert record.alert_kind in {"problem", "no_data", "recovery"}
