"""
Subjects: `client.v2.subjects`.

What a client depends on here is the pair of kinds. Every subject says WHAT it
is in `kind` ("subject") and HOW it is configured in `subject_kind` ("website"
or "custom"), and those must stay separate — a client switching on `kind` has to
keep working when a third subject kind arrives.

The other half is what create means: one empty Custom subject, and a Website
asked for here is refused rather than half-made.
"""

import json

import pytest
from pytest_httpx import HTTPXMock

from tests.conftest import api_response
from uptimer.client import UptimerClient
from uptimer.errors import DefaultUptimerApiError
from uptimer.models.errors import TypeMismatchError
from uptimer.models.v2 import (
    SUBJECT_KIND_CUSTOM,
    SUBJECT_KIND_WEBSITE,
    CreateSubjectRequest,
    Subject,
    from_api_subject,
)


def _subject(
    *,
    slug: str = "nightly-export",
    name: str = "Nightly export",
    subject_kind: str = SUBJECT_KIND_CUSTOM,
    signals: int = 0,
    rules: int = 0,
) -> dict:
    return {
        "id": slug,
        "name": name,
        "subject_kind": subject_kind,
        "workspace_id": "ws-1",
        "signal_count": signals,
        "rule_count": rules,
        "kind": "subject",
    }


def test_all_returns_both_kinds(httpx_mock: HTTPXMock, uptimer_client: UptimerClient):
    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v2/subjects?workspace_id=ws-1",
        json=api_response(
            [
                _subject(slug="check-abc", name="Checkout API",
                         subject_kind=SUBJECT_KIND_WEBSITE, signals=1, rules=1),
                _subject(),
            ],
        ),
    )

    subjects = uptimer_client.v2.subjects.all("ws-1")

    assert [s.id for s in subjects] == ["check-abc", "nightly-export"]
    website, custom = subjects
    assert website.subject_kind == SUBJECT_KIND_WEBSITE
    assert website.is_website
    assert not website.is_custom
    assert custom.is_custom
    # The object discriminator is not the subject kind, and both survive.
    assert website.kind == "subject"
    assert custom.kind == "subject"


def test_get_reaches_one_subject_by_slug(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v2/subjects/nightly-export",
        json=api_response(_subject()),
    )

    subject = uptimer_client.v2.subjects.get("nightly-export")

    assert subject.id == "nightly-export"
    assert subject.name == "Nightly export"
    assert subject.is_custom


def test_get_passes_the_workspace_when_given(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    # A slug is unique within a workspace, not across them. The parameter is how
    # a caller who belongs to two settles which one they mean.
    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v2/subjects/nightly-export?workspace_id=ws-1",
        json=api_response(_subject()),
    )

    assert uptimer_client.v2.subjects.get("nightly-export", workspace_id="ws-1").id == (
        "nightly-export"
    )


def test_get_escapes_the_slug(httpx_mock: HTTPXMock, uptimer_client: UptimerClient):
    # A slug with a slash must address a subject named that, not a different
    # resource one path segment along.
    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v2/subjects/a%2Fb",
        json=api_response(_subject(slug="a/b")),
    )

    assert uptimer_client.v2.subjects.get("a/b").id == "a/b"


@pytest.mark.parametrize("slug", ["", "   "])
def test_get_refuses_an_empty_slug(slug: str, uptimer_client: UptimerClient):
    with pytest.raises(ValueError, match="subject slug is required"):
        uptimer_client.v2.subjects.get(slug)


def test_create_makes_an_empty_custom_subject(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v2/subjects",
        method="POST",
        json=api_response(_subject()),
    )

    created = uptimer_client.v2.subjects.create(
        CreateSubjectRequest(name="Nightly export", workspace_id="ws-1"),
    )

    assert created.is_custom
    # Empty is the promise the route makes, and the counts are how a caller sees
    # it without a signals collection to ask.
    assert created.signal_count == 0
    assert created.rule_count == 0

    sent = json.loads(httpx_mock.get_requests()[0].content)
    assert sent == {
        "name": "Nightly export",
        "workspace_id": "ws-1",
        "subject_kind": SUBJECT_KIND_CUSTOM,
    }


def test_create_defaults_to_custom(httpx_mock: HTTPXMock, uptimer_client: UptimerClient):
    # There is one kind this route creates, so the caller should not have to say
    # it — but sending it explicitly keeps the request self-describing on the
    # wire, which is why it is a field with a default rather than a hidden one.
    request = CreateSubjectRequest(name="Nightly export", workspace_id="ws-1")
    assert request.subject_kind == SUBJECT_KIND_CUSTOM

    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v2/subjects",
        method="POST",
        json=api_response(_subject()),
    )
    uptimer_client.v2.subjects.create(request)
    assert json.loads(httpx_mock.get_requests()[0].content)["subject_kind"] == "custom"


def test_create_website_is_refused_by_the_server(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    # Website monitoring needs a URL, an interval and locations. The SDK does not
    # pretend otherwise: it sends what the caller asked for and surfaces the
    # server's refusal, which names the method to use instead.
    httpx_mock.add_response(
        url="http://127.0.0.1:2519/v2/subjects",
        method="POST",
        json=api_response(
            None,
            {
                "code": 2003,
                "error_type": "invalid_request",
                "message": "Website subjects are created elsewhere",
                "details": "Use POST /v2/monitoring/websites to create website monitoring",
            },
        ),
    )

    with pytest.raises(DefaultUptimerApiError) as raised:
        uptimer_client.v2.subjects.create(
            CreateSubjectRequest(
                name="Checkout",
                workspace_id="ws-1",
                subject_kind=SUBJECT_KIND_WEBSITE,
            ),
        )
    assert "/v2/monitoring/websites" in raised.value.details


def test_the_signals_path_still_works(uptimer_client: UptimerClient):
    # The collection methods are additive: calling the namespace with a slug
    # still reaches what is under one subject, which is the #146 ingest path.
    endpoint = uptimer_client.v2.subjects("checkout").signals("worker-pulse").observations
    assert endpoint.url.endswith("/v2/subjects/checkout/signals/worker-pulse/observations")


def test_from_api_subject_rejects_another_kind():
    with pytest.raises(TypeMismatchError):
        from_api_subject({"kind": "workspace", "id": "ws-1", "name": "W", "role": "owner"})


def test_subject_is_a_dataclass_with_stable_field_names():
    # The field names are the payload's, so a rename here is a breaking change
    # for anyone reading the object.
    subject = Subject(
        id="nightly-export",
        name="Nightly export",
        subject_kind=SUBJECT_KIND_CUSTOM,
        workspace_id="ws-1",
    )
    assert subject.signal_count == 0
    assert subject.rule_count == 0
    assert subject.kind == "subject"
