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
