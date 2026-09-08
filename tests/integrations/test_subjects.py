"""
Subjects against a running Uptimer.

This one needs only a key and a workspace, because creating a Custom subject is
the whole point: the run does not have to be handed a subject that already
exists. Set

    UPTIMER_API_KEY, UPTIMER_WORKSPACE_ID

and optionally UPTIMER_URL, plus UPTIMER_WEBSITE_SUBJECT_SLUG to prove the
cross-kind refusal. Without the first two the module skips, so a plain
`--integration` run stays green.

It creates a subject and does not delete it — the SDK has no delete, by design
(deleting one takes its whole history with it). Names carry a timestamp so a
repeated run does not collide, and what is left behind is an empty subject.
"""

import os
from datetime import datetime, timezone

import pytest

from tests.conftest import integration_test
from uptimer.errors import DefaultUptimerApiError
from uptimer.models.v2 import (
    SUBJECT_KIND_CUSTOM,
    SUBJECT_KIND_WEBSITE,
    CreateSubjectRequest,
)

from .conftest import get_client

API_KEY = os.environ.get("UPTIMER_API_KEY", "")
WORKSPACE_ID = os.environ.get("UPTIMER_WORKSPACE_ID", "")
# A website subject's slug, to prove the cross-kind refusal. Optional: a
# workspace need not have a website check for the rest of this module to run.
WEBSITE_SUBJECT_SLUG = os.environ.get("UPTIMER_WEBSITE_SUBJECT_SLUG", "")

needs_workspace = pytest.mark.skipif(
    not (API_KEY and WORKSPACE_ID),
    reason="set UPTIMER_API_KEY and UPTIMER_WORKSPACE_ID",
)


def _unique_name() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"SDK integration {stamp}"


@integration_test
@needs_workspace
def test_create_list_and_get_a_custom_subject(uptimer_url: str):
    subjects = get_client(API_KEY, uptimer_url).v2.subjects

    created = subjects.create(
        CreateSubjectRequest(name=_unique_name(), workspace_id=WORKSPACE_ID),
    )
    assert created.is_custom
    assert created.kind == "subject"
    # The promise the route makes: nothing under it, including no HTTP probe.
    assert created.signal_count == 0
    assert created.rule_count == 0

    listed = subjects.all(WORKSPACE_ID)
    assert created.id in [s.id for s in listed], "the new subject is not in the list"

    fetched = subjects.get(created.id, workspace_id=WORKSPACE_ID)
    assert fetched.id == created.id
    assert fetched.name == created.name
    assert fetched.subject_kind == SUBJECT_KIND_CUSTOM


@integration_test
@needs_workspace
def test_the_listing_is_custom_only(uptimer_url: str):
    """
    Uptimer 1.6.0 splits the API by subject kind.

    Website monitoring is `client.v2.monitoring.websites`; this route answers
    with custom subjects alone, whatever else the workspace watches.
    """
    listed = get_client(API_KEY, uptimer_url).v2.subjects.all(WORKSPACE_ID)
    assert listed, "the workspace has no custom subject to read"
    assert all(s.subject_kind == SUBJECT_KIND_CUSTOM for s in listed)
    assert all(s.is_custom and not s.is_website for s in listed)
    assert all(s.kind == "subject" for s in listed)


@integration_test
@pytest.mark.skipif(
    not (API_KEY and WEBSITE_SUBJECT_SLUG),
    reason="set UPTIMER_WEBSITE_SUBJECT_SLUG to prove the cross-kind refusal",
)
def test_a_website_subject_is_not_readable_here(uptimer_url: str):
    """The other half of the split: a website subject is refused, not returned."""
    subjects = get_client(API_KEY, uptimer_url).v2.subjects

    with pytest.raises(DefaultUptimerApiError) as raised:
        subjects.get(WEBSITE_SUBJECT_SLUG, workspace_id=WORKSPACE_ID or None)
    assert "managed elsewhere" in raised.value.message


@integration_test
@needs_workspace
def test_a_website_cannot_be_created_here(uptimer_url: str):
    subjects = get_client(API_KEY, uptimer_url).v2.subjects

    with pytest.raises(DefaultUptimerApiError) as raised:
        subjects.create(
            CreateSubjectRequest(
                name=_unique_name(),
                workspace_id=WORKSPACE_ID,
                subject_kind=SUBJECT_KIND_WEBSITE,
            ),
        )
    assert "monitoring/websites" in raised.value.details


@integration_test
@needs_workspace
def test_an_unusable_name_is_refused(uptimer_url: str):
    subjects = get_client(API_KEY, uptimer_url).v2.subjects

    with pytest.raises(DefaultUptimerApiError):
        subjects.create(CreateSubjectRequest(name="***", workspace_id=WORKSPACE_ID))
