"""
Custom signal and rule authoring: `client.v2.subjects(slug).signals` / `.rules`.

The signal half is ordinary CRUD. The rule half is not, and two things here are
worth a test of their own:

- `from` is a Python keyword, so an input that cites another rule is `from_rule`
  on this side of the wire and `from` on the other. A translation that only went
  one way would round-trip a policy into a different policy.
- the policy is a REPLACEMENT, and unset fields must be left out rather than
  sent as null — an absent `no_data_after` means "derive it from the interval",
  where a null is a malformed duration.
"""

import json

from pytest_httpx import HTTPXMock

from tests.conftest import api_response
from uptimer.client import UptimerClient
from uptimer.models.v2 import (
    INPUT_MODE_LATEST_VALUE,
    INPUT_MODE_STATUS,
    NEED_ANY,
    SIGNAL_KIND_EVENT,
    SIGNAL_KIND_HEARTBEAT,
    SIGNAL_KIND_HTTP,
    CreateObservationRequest,
    CreateRuleRequest,
    CreateSignalRequest,
    RuleDecision,
    RuleDocument,
    RuleInput,
    RuleWait,
    UpdateRuleRequest,
    UpdateSignalRequest,
)

BASE = "http://127.0.0.1:2519"
SUBJECT = "payments-worker"
WORKSPACE = "ws-1"


def _signal(*, slug: str = "worker-pulse", kind: str = SIGNAL_KIND_HEARTBEAT) -> dict:
    return {
        "id": slug,
        "name": "Worker pulse",
        "signal_kind": kind,
        "subject_id": SUBJECT,
        "workspace_id": "ws-1",
        "meta": {"team": "payments"},
        "kind": "signal",
    }


def _rule(*, version: int = 1) -> dict:
    return {
        "id": "export-health",
        "name": "Export health",
        "subject_id": SUBJECT,
        "workspace_id": "ws-1",
        "policy_version": version,
        "document": {
            "inputs": [
                {"signal": "worker-pulse", "mode": "status", "no_data_after": "5m0s"},
                {"from": "queue-health"},
            ],
            "decision": {"state": "down", "need": "any"},
            "wait": {"confirm_after": "2m0s", "close_after": "2m0s"},
        },
        "kind": "subject_rule",
    }


def test_signals_are_listed_under_their_subject(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/signals",
        json=api_response([_signal(), _signal(slug="http", kind=SIGNAL_KIND_HTTP)]),
    )

    signals = uptimer_client.v2.subjects(SUBJECT).signals.all()

    assert [s.id for s in signals] == ["worker-pulse", "http"]
    assert signals[0].is_heartbeat
    # A website monitor's own signal is readable and refuses every write.
    assert signals[1].is_managed


def test_creating_a_signal_sends_name_kind_and_meta(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/signals",
        json=api_response(_signal(kind=SIGNAL_KIND_EVENT)),
    )

    created = uptimer_client.v2.subjects(SUBJECT).signals.create(
        CreateSignalRequest(name="Worker pulse", kind=SIGNAL_KIND_EVENT),
    )

    sent = json.loads(httpx_mock.get_requests()[0].content)
    assert sent == {"name": "Worker pulse", "kind": SIGNAL_KIND_EVENT, "meta": {}}
    assert created.signal_kind == SIGNAL_KIND_EVENT


def test_updating_a_signal_carries_no_kind(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    """The kind and the slug are immutable; a rename never moves the address."""
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/signals/worker-pulse",
        json=api_response(_signal()),
    )

    uptimer_client.v2.subjects(SUBJECT).signals.update(
        "worker-pulse",
        UpdateSignalRequest(name="Worker heartbeat"),
    )

    sent = json.loads(httpx_mock.get_requests()[0].content)
    assert "kind" not in sent
    assert sent["name"] == "Worker heartbeat"


def test_deleting_a_signal_names_what_went(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/signals/worker-pulse",
        json=api_response(
            {
                "message": "Signal deleted successfully",
                "signal_id": "worker-pulse",
                "subject_id": SUBJECT,
            },
        ),
    )

    answer = uptimer_client.v2.subjects(SUBJECT).signals.delete("worker-pulse")

    assert answer.signal_id == "worker-pulse"


def test_a_slug_with_a_slash_addresses_that_signal(uptimer_client: UptimerClient):
    """
    Check that a slug is escaped into the path.

    A value containing a slash must address a signal named that, not silently
    reach a different resource.
    """
    path = uptimer_client.v2.subjects(SUBJECT).signals("a/b").path

    assert path.endswith("signals/a%2Fb")


def test_authoring_a_rule_translates_from_and_omits_what_is_unset(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/rules",
        json=api_response(_rule()),
    )

    uptimer_client.v2.subjects(SUBJECT).rules.create(
        CreateRuleRequest(
            name="Export health",
            document=RuleDocument(
                inputs=[
                    RuleInput(
                        signal="worker-pulse",
                        mode=INPUT_MODE_STATUS,
                        no_data_after="5m",
                    ),
                    RuleInput(
                        signal="queue-depth",
                        mode=INPUT_MODE_LATEST_VALUE,
                        compare=">",
                        threshold=1000,
                    ),
                    RuleInput(from_rule="queue-health"),
                ],
                decision=RuleDecision(need=NEED_ANY),
                wait=RuleWait(confirm_after="2m", close_after="2m"),
            ),
        ),
    )

    sent = json.loads(httpx_mock.get_requests()[0].content)
    inputs = sent["document"]["inputs"]
    # `from_rule` is `from` on the wire, and never both.
    assert inputs[2] == {"from": "queue-health"}
    assert "from_rule" not in json.dumps(sent)
    # Unset fields are left out, not sent as null.
    assert inputs[0] == {
        "signal": "worker-pulse",
        "mode": "status",
        "no_data_after": "5m",
    }
    assert inputs[1]["threshold"] == 1000
    assert "at_least" not in sent["document"]["decision"]


def test_a_stored_policy_reads_back_as_it_was_written(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/rules/export-health",
        json=api_response(_rule(version=3)),
    )

    rule = uptimer_client.v2.subjects(SUBJECT).rules.get("export-health")

    assert rule.policy_version == 3
    assert rule.document.inputs[0].signal == "worker-pulse"
    assert rule.document.inputs[0].no_data_after == "5m0s"
    # The rule input came back as `from`; it is `from_rule` on this side.
    assert rule.document.inputs[1].from_rule == "queue-health"
    assert rule.document.inputs[1].signal is None
    assert rule.document.decision.need == NEED_ANY
    assert rule.document.wait.confirm_after == "2m0s"


def test_a_policy_survives_a_round_trip(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    """
    Read a rule, send it straight back, and the server sees what it stored.

    This is the check that matters for an update: the policy is a replacement,
    so a client that reads-modifies-writes must not lose or invent a field on
    the way.
    """
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/rules/export-health",
        json=api_response(_rule()),
    )
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/rules/export-health",
        json=api_response(_rule(version=2)),
    )

    rule = uptimer_client.v2.subjects(SUBJECT).rules.get("export-health")
    updated = uptimer_client.v2.subjects(SUBJECT).rules.update(
        "export-health",
        UpdateRuleRequest(name=rule.name, document=rule.document),
    )

    sent = json.loads(httpx_mock.get_requests()[1].content)
    assert sent["document"] == _rule()["document"]
    assert updated.policy_version == 2


def test_deleting_a_rule_names_what_went(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/rules/export-health",
        json=api_response(
            {
                "message": "Rule deleted successfully",
                "rule_id": "export-health",
                "subject_id": SUBJECT,
            },
        ),
    )

    answer = uptimer_client.v2.subjects(SUBJECT).rules.delete("export-health")

    assert answer.rule_id == "export-health"


# --- The workspace a caller named has to reach every nested route --------------
#
# A subject slug is unique within a workspace, not across them, and the server
# resolves the subject BEFORE anything else. A caller who says which workspace
# they mean and is answered `Ambiguous subject` has been let down by the client,
# not by the server — so these assert the request URL, which is the only place
# that can be seen.


def test_every_signal_route_carries_a_named_workspace(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    base = f"{BASE}/v2/subjects/{SUBJECT}/signals"
    for url, json_body in (
        (f"{base}?workspace_id={WORKSPACE}", api_response([_signal()])),
        (f"{base}?workspace_id={WORKSPACE}", api_response(_signal())),
        (f"{base}/worker-pulse?workspace_id={WORKSPACE}", api_response(_signal())),
        (f"{base}/worker-pulse?workspace_id={WORKSPACE}", api_response(_signal())),
        (
            f"{base}/worker-pulse?workspace_id={WORKSPACE}",
            api_response(
                {
                    "message": "Signal deleted successfully",
                    "signal_id": "worker-pulse",
                    "subject_id": SUBJECT,
                },
            ),
        ),
    ):
        httpx_mock.add_response(url=url, json=json_body)

    signals = uptimer_client.v2.subjects(SUBJECT, WORKSPACE).signals
    signals.all()
    signals.create(CreateSignalRequest(name="Worker pulse"))
    signals.get("worker-pulse")
    signals.update("worker-pulse", UpdateSignalRequest(name="Worker heartbeat"))
    signals.delete("worker-pulse")

    for request in httpx_mock.get_requests():
        assert request.url.params.get("workspace_id") == WORKSPACE, request.url


def test_every_rule_route_carries_a_named_workspace(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    base = f"{BASE}/v2/subjects/{SUBJECT}/rules"
    for url, json_body in (
        (f"{base}?workspace_id={WORKSPACE}", api_response([_rule()])),
        (f"{base}?workspace_id={WORKSPACE}", api_response(_rule())),
        (f"{base}/export-health?workspace_id={WORKSPACE}", api_response(_rule())),
        (f"{base}/export-health?workspace_id={WORKSPACE}", api_response(_rule(version=2))),
        (
            f"{base}/export-health?workspace_id={WORKSPACE}",
            api_response(
                {
                    "message": "Rule deleted successfully",
                    "rule_id": "export-health",
                    "subject_id": SUBJECT,
                },
            ),
        ),
    ):
        httpx_mock.add_response(url=url, json=json_body)

    rules = uptimer_client.v2.subjects(SUBJECT, WORKSPACE).rules
    rules.all()
    rules.create(CreateRuleRequest(name="Export health"))
    rules.get("export-health")
    rules.update("export-health", UpdateRuleRequest(name="Export health"))
    rules.delete("export-health")

    for request in httpx_mock.get_requests():
        assert request.url.params.get("workspace_id") == WORKSPACE, request.url


def test_observations_carry_it_too(httpx_mock: HTTPXMock, uptimer_client: UptimerClient):
    """
    Check the sixth route of the signals family.

    Reporting an observation resolves the subject exactly as the other five do,
    so a named workspace has to reach it as well.
    """
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/signals/worker-pulse/observations"
        f"?workspace_id={WORKSPACE}",
        json=api_response(
            {
                "subject_id": SUBJECT,
                "signal_id": "worker-pulse",
                "observed_at": "2026-09-01T12:00:00Z",
                "received_at": "2026-09-01T12:00:01Z",
                "status": "ok",
                "value": None,
                "error": "",
                "labels": {},
                "accepted": True,
                "reject_reason": "accepted",
                "kind": "observation",
            },
        ),
    )

    observations = (
        uptimer_client.v2.subjects(SUBJECT, WORKSPACE).signals("worker-pulse").observations
    )
    observations.create(CreateObservationRequest(status="ok"))

    assert httpx_mock.get_requests()[0].url.params.get("workspace_id") == WORKSPACE


def test_no_workspace_sends_no_parameter(
    httpx_mock: HTTPXMock,
    uptimer_client: UptimerClient,
):
    """
    A caller who named no workspace still sends none.

    The server searches the memberships in that case, which is the behaviour a
    single-workspace user has always had.
    """
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/signals",
        json=api_response([]),
    )
    httpx_mock.add_response(
        url=f"{BASE}/v2/subjects/{SUBJECT}/rules",
        json=api_response([]),
    )

    uptimer_client.v2.subjects(SUBJECT).signals.all()
    uptimer_client.v2.subjects(SUBJECT).rules.all()

    for request in httpx_mock.get_requests():
        assert "workspace_id" not in request.url.params
        assert "?" not in str(request.url)
