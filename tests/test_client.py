from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Iterator

import pytest

from uptimer import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    IncompatibleServerError,
    NotFoundError,
    UptimerClient,
    ValidationError,
)

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock

BASE = "http://uptimer.test/api"
WS = f"{BASE}/v3/workspaces/w1"


def ok(result: object, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"result": result, "error": None, "meta": meta}


def refused(code: int, kind: str, message: str, details: dict[str, str] | None = None) -> dict[str, Any]:
    return {"result": None, "error": {"code": code, "error_type": kind, "message": message, "details": details}, "meta": None}


RESOURCE = {
    "id": "r1", "key": "checkout", "name": "Checkout", "template": "website-check@1",
    "meta": {"url": "https://acme.test"}, "created_at": "2026-10-04T10:00:00Z",
    "open_incident": {"id": "i1", "standing": "problem", "explanation": "1 of 1 location failing"},
    "signals": [{"id": "s1", "key": "reachability@loc", "kind": "heartbeat", "states": ["ok", "problem"]}],
    "rules": [{"key": "availability", "signals": ["reachability@loc"], "status": "problem",
               "explanation": "1 of 1 location failing", "since": "2026-10-04T10:01:00Z", "open_incident": "i1"}],
    "maintenance": None,
}

INCIDENT = {
    "id": "i1", "resource": {"id": "r1", "key": "checkout", "name": "Checkout"}, "rule": "availability",
    "lifecycle": "closed", "confirmation": "unconfirmed", "condition": "ok", "verdict": "ok",
    "explanation": "0 of 1 location failing", "closed_reason": "recovered",
    "opened_at": "2026-10-04T10:00:00Z", "confirmed_at": None, "closed_at": "2026-10-04T10:02:00Z",
    "effective_at": "2026-10-04T10:02:00Z", "acknowledgement": None,
    "history": [
        {"at": "2026-10-04T10:00:00Z", "kind": "opened", "condition": "problem", "verdict": "problem", "explanation": "1 of 1"},
        {"at": "2026-10-04T10:02:00Z", "kind": "closed", "condition": "ok", "verdict": "ok", "explanation": "0 of 1"},
    ],
}


@pytest.fixture
def client() -> Iterator[UptimerClient]:
    with UptimerClient(api_key="k3y", base_url=BASE + "/") as c:
        yield c


def test_every_request_carries_the_key(client: UptimerClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=f"{BASE}/v3/workspaces", json=ok([{"id": "w1", "name": "Ops", "role": "owner"}]))
    spaces = client.workspaces()
    assert spaces[0].id == "w1"
    assert spaces[0].role == "owner"
    assert httpx_mock.get_request().headers["Authorization"] == "Bearer k3y"


def test_a_full_key_creates_a_workspace(client: UptimerClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="POST", url=f"{BASE}/v3/workspaces", status_code=201,
                            json=ok({"id": "w2", "name": "Field iteration 2", "role": "owner"}))
    made = client.create_workspace("Field iteration 2")
    assert (made.id, made.name, made.role) == ("w2", "Field iteration 2", "owner")
    assert json.loads(httpx_mock.get_request().content) == {"name": "Field iteration 2"}


def test_creating_a_workspace_is_refused_as_the_api_refuses_it(client: UptimerClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="POST", url=f"{BASE}/v3/workspaces", status_code=422, json={
        "result": None, "meta": None, "error": {"code": 1422, "error_type": "validation",
        "message": "A Workspace needs a name of 1 to 60 characters.", "details": {"field": "name"}}})
    with pytest.raises(ValidationError):
        client.create_workspace(" ")
    httpx_mock.add_response(method="POST", url=f"{BASE}/v3/workspaces", status_code=403, json={
        "result": None, "meta": None, "error": {"code": 1403, "error_type": "forbidden",
        "message": "This API key is scoped to one Workspace; creating a Workspace needs a full key.",
        "details": {"scope": "full"}}})
    with pytest.raises(ForbiddenError):
        client.create_workspace("Elsewhere")


def test_a_resource_reads_with_its_signals_rules_and_result(client: UptimerClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=f"{WS}/resources/checkout", json=ok(RESOURCE))
    resource = client.workspace("w1").resources.get("checkout")
    assert resource.id == "r1"
    assert resource.signals[0].key == "reachability@loc"
    assert resource.rules[0].status == "problem"
    assert resource.rules[0].open_incident == "i1"
    assert resource.open_incident is not None
    assert resource.open_incident.id == "i1"
    assert resource.created_at == datetime(2026, 10, 4, 10, 0, tzinfo=timezone.utc)


def test_create_and_observe_send_what_the_api_reads(client: UptimerClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="POST", url=f"{WS}/resources", json=ok(RESOURCE), status_code=201)
    httpx_mock.add_response(method="POST", url=f"{WS}/resources/checkout/observations", status_code=202,
                            json=ok({"resource": "r1", "signal": "s1", "observation": "o1", "created_signal": False}))
    ws = client.workspace("w1")
    ws.resources.create(template="website-check", name="Checkout", key="checkout", meta={"url": "https://acme.test"})
    observed = ws.resources.observe("checkout", signal="reachability@loc", state="problem",
                                    labels={"status": "503"}, observation_id="o1",
                                    at=datetime(2026, 10, 4, 10, 0, tzinfo=timezone.utc))
    assert observed.observation == "o1"
    create, observe = httpx_mock.get_requests()
    assert json.loads(create.content) == {"template": "website-check", "name": "Checkout",
                                          "meta": {"url": "https://acme.test"}, "key": "checkout"}
    assert json.loads(observe.content) == {"signal": "reachability@loc", "state": "problem",
                                           "labels": {"status": "503"}, "id": "o1",
                                           "at": "2026-10-04T10:00:00+00:00"}


def test_an_incident_keeps_its_outcome_and_ordered_history(client: UptimerClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=f"{WS}/incidents/i1", json=ok(INCIDENT))
    incident = client.workspace("w1").incidents.get("i1")
    assert (incident.lifecycle, incident.confirmation, incident.closed_reason) == ("closed", "unconfirmed", "recovered")
    assert [t.kind for t in incident.history] == ["opened", "closed"]
    assert incident.resource.key == "checkout"
    assert incident.rule == "availability"


def test_lists_page_with_the_cursor(client: UptimerClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=f"{WS}/incidents?lifecycle=closed&limit=1", json=ok([INCIDENT], {"next_cursor": "i1"}))
    httpx_mock.add_response(url=f"{WS}/incidents?lifecycle=closed&limit=1&cursor=i1", json=ok([], {"next_cursor": None}))
    seen = list(client.workspace("w1").incidents.iterate(lifecycle="closed", limit=1))
    assert [i.id for i in seen] == ["i1"]


@pytest.mark.parametrize(("status", "body", "error"), [
    (401, refused(1401, "auth", "no"), AuthenticationError),
    (403, refused(1403, "forbidden", "viewer"), ForbiddenError),
    (404, refused(1404, "not_found", "No such Incident"), NotFoundError),
    (409, refused(1409, "conflict", "closed"), ConflictError),
    (422, refused(1422, "validation", "Say a URL", {"field": "url"}), ValidationError),
])
def test_each_refusal_is_its_own_error(
    client: UptimerClient, httpx_mock: HTTPXMock, status: int, body: dict[str, Any], error: type[Exception],
) -> None:
    httpx_mock.add_response(url=f"{WS}/incidents/i1", json=body, status_code=status)
    with pytest.raises(error) as raised:
        client.workspace("w1").incidents.get("i1")
    assert getattr(raised.value, "code", None) == body["error"]["code"]
    assert getattr(raised.value, "status", None) == status
    if status == 422:
        assert getattr(raised.value, "field", None) == "url"


def test_a_server_without_api_v3_is_named(client: UptimerClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=f"{BASE}/v3/version", json=ok({"version": "1.8.0", "api": "v2"}))
    with pytest.raises(IncompatibleServerError):
        client.check_compatibility()


def test_a_v3_server_passes(client: UptimerClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=f"{BASE}/v3/version", json=ok({"version": "2.0.0", "api": "v3"}))
    assert client.check_compatibility() == "2.0.0"


COUNTED_TEMPLATE = {
    "id": "service-triage@1", "key": "service-triage", "version": 1, "name": "Synthetic service triage", "summary": "s",
    "fields": [{"key": "load_threshold", "label": "Traffic ratio threshold", "help": "", "type": "number",
                "required": False, "default": 0.5, "options": [], "min": 0, "max": None}],
    "signals": [{"key": "load_ratio", "kind": "heartbeat", "states": ["ok", "problem", "no_data"]}],
    "rules": [{"key": "access_loss", "signals": ["load_ratio"], "help": "", "action": "Investigate the access path."}],
}


def test_a_workspace_publishes_and_lists_its_templates(client: UptimerClient, httpx_mock: HTTPXMock):
    manifest = {"key": "service-triage", "version": 1, "rules": [{"key": "access_loss", "decision": {
        "not": {"signal": "load_ratio", "field": "value", "operator": "gte", "operand": 0.5,
                "min_count": 3, "within_seconds": 900}}}]}
    httpx_mock.add_response(method="POST", url=f"{WS}/templates", json=ok(COUNTED_TEMPLATE), status_code=201)
    httpx_mock.add_response(method="GET", url=f"{WS}/templates", json=ok([COUNTED_TEMPLATE]))
    ws = client.workspace("w1")

    published = ws.templates.publish(manifest)
    assert published.id == "service-triage@1"
    assert published.rules[0]["action"] == "Investigate the access path."
    assert json.loads(httpx_mock.get_requests()[0].content) == manifest
    assert [one.id for one in ws.templates.list()] == ["service-triage@1"]


def test_republishing_a_revision_is_a_conflict(client: UptimerClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="POST", url=f"{WS}/templates", status_code=409,
                            json=refused(1409, "conflict", "already published"))
    with pytest.raises(ConflictError):
        client.workspace("w1").templates.publish({"key": "service-triage", "version": 1})


def test_rules_and_incidents_carry_their_action(client: UptimerClient, httpx_mock: HTTPXMock):
    resource = {**RESOURCE, "rules": [{**RESOURCE["rules"][0], "action": "Investigate the access path."}]}
    httpx_mock.add_response(url=f"{WS}/resources/checkout", json=ok(resource))
    httpx_mock.add_response(url=f"{WS}/incidents/i1", json=ok({**INCIDENT, "action": "Investigate the access path."}))
    ws = client.workspace("w1")
    assert ws.resources.get("checkout").rules[0].action == "Investigate the access path."
    assert ws.incidents.get("i1").action == "Investigate the access path."
    # An older server sends no action: still readable.
    httpx_mock.add_response(url=f"{WS}/incidents/i2", json=ok({**INCIDENT, "id": "i2"}))
    assert ws.incidents.get("i2").action is None


def test_a_rule_names_its_destination(client: UptimerClient, httpx_mock: HTTPXMock):
    resource = {**RESOURCE, "rules": [{**RESOURCE["rules"][0], "destination": "d1"}]}
    httpx_mock.add_response(url=f"{WS}/resources/checkout", json=ok(resource))
    httpx_mock.add_response(url=f"{WS}/resources/checkout", json=ok(RESOURCE))
    ws = client.workspace("w1")
    assert ws.resources.get("checkout").rules[0].destination == "d1"
    # A Rule without one, or an older server: None, the default routing.
    assert ws.resources.get("checkout").rules[0].destination is None


def test_resources_are_listed_page_by_page_with_their_filters(client: UptimerClient, httpx_mock: HTTPXMock):
    second = {**RESOURCE, "id": "r2", "key": "h2"}
    httpx_mock.add_response(
        url=f"{WS}/resources?template=service-triage&state=all&meta.provider=alpha&meta.enabled=true&limit=200",
        json=ok([RESOURCE], {"next_cursor": "r1"}))
    httpx_mock.add_response(
        url=f"{WS}/resources?template=service-triage&state=all&meta.provider=alpha&meta.enabled=true&limit=200&cursor=r1",
        json=ok([second], {"next_cursor": None}))
    found = client.workspace("w1").resources.list(
        template="service-triage", state="all", meta={"provider": "alpha", "enabled": True})
    assert [one.key for one in found] == ["checkout", "h2"]


def test_archiving_answers_the_archived_resource(client: UptimerClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="POST", url=f"{WS}/resources/checkout/archive",
                            json=ok({**RESOURCE, "archived_at": "2026-10-05T12:00:00Z"}))
    archived = client.workspace("w1").resources.archive("checkout")
    assert archived.archived_at == datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
    httpx_mock.add_response(method="POST", url=f"{WS}/resources/checkout/archive", status_code=409,
                            json=refused(1409, "conflict", "This Resource is archived"))
    with pytest.raises(ConflictError):
        client.workspace("w1").resources.archive("checkout")


def test_incidents_filter_by_their_resources_fields(client: UptimerClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{WS}/incidents?template=service-triage&resource_state=active&meta.load_threshold=0.4&limit=50",
        json=ok([INCIDENT], {"next_cursor": None}))
    page = client.workspace("w1").incidents.list(
        template="service-triage", resource_state="active", meta={"load_threshold": 0.4})
    assert page.items[0].id == "i1"
    assert page.next_cursor is None


def test_a_transition_carries_its_recorded_evidence(client: UptimerClient, httpx_mock: HTTPXMock):
    evidence = {"inputs": [{"signal": "load_ratio", "status": "ok", "value": 0.1, "at": "2026-10-05T12:00:00Z"},
                           {"signal": "service_health", "unresolved": "the sender reported no_data"}],
                "omitted": 0, "truncated": False}
    history = [{**INCIDENT["history"][0], "evidence": evidence}, {**INCIDENT["history"][0], "kind": "closed"}]
    httpx_mock.add_response(url=f"{WS}/incidents/i1", json=ok({**INCIDENT, "history": history}))
    incident = client.workspace("w1").incidents.get("i1")
    assert incident.history[0].evidence["inputs"][1]["unresolved"] == "the sender reported no_data"
    assert incident.history[1].evidence is None


def test_a_baseline_input_carries_the_median_it_read(client: UptimerClient, httpx_mock: HTTPXMock):
    baseline = {"days": 7, "required": 12, "samples": 12, "median": 100}
    evidence = {"inputs": [{"signal": "load", "status": "ok", "value": 40, "baseline": baseline}],
                "omitted": 0, "truncated": False}
    history = [{**INCIDENT["history"][0], "evidence": evidence}]
    httpx_mock.add_response(url=f"{WS}/incidents/i1", json=ok({**INCIDENT, "history": history}))
    incident = client.workspace("w1").incidents.get("i1")
    assert incident.history[0].evidence["inputs"][0]["baseline"] == baseline
