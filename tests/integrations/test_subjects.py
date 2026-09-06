"""
Subjects against a running Uptimer.

This one needs only a key and a workspace, because creating a Custom subject is
the whole point: the run does not have to be handed a subject that already
exists. Set

    UPTIMER_API_KEY, UPTIMER_WORKSPACE_ID

and optionally UPTIMER_URL. Without the first two the module skips, so a plain
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
def test_website_subjects_are_listed_as_website(uptimer_url: str):
    # Only meaningful in a workspace that has one; a workspace with none is not
    # a failure of this SDK.
    listed = get_client(API_KEY, uptimer_url).v2.subjects.all(WORKSPACE_ID)
    websites = [s for s in listed if s.subject_kind == SUBJECT_KIND_WEBSITE]
    if not websites:
        pytest.skip("this workspace has no website subject to check")
    assert all(s.is_website and not s.is_custom for s in websites)
    assert all(s.kind == "subject" for s in websites)


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
