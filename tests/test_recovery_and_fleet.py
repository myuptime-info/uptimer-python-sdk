"""Recovery resets, on-demand validity, shared confirmations, and Locations and workers by API."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Iterator

import pytest

from uptimer import (
    Comparison,
    ConflictError,
    ForbiddenError,
    UptimerClient,
    ValidationError,
)
from uptimer.models import Observation, Resource, Template

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock

BASE = "http://uptimer.test/api"
UID = "00000000-0000-4000-8000-000000000001"


def ok(result: object) -> dict[str, Any]:
    return {"result": result, "error": None, "meta": None}


def refused(code: int, kind: str, details: dict[str, str] | None = None) -> dict[str, Any]:
    return {"result": None, "error": {"code": code, "error_type": kind, "message": "refused", "details": details},
            "meta": None}


@pytest.fixture
def client() -> Iterator[UptimerClient]:
    with UptimerClient(api_key="k3y", base_url=BASE + "/") as c:
        yield c


TEMPLATE = {
    "id": "service-triage@6", "version": 6, "name": "Service triage", "summary": "s", "fields": [],
    "signals": [{"key": "deep", "kind": "event", "states": ["ok"], "on_demand": True, "valid_seconds": 600},
                {"key": "load", "kind": "event", "states": ["ok"]}],
    "rules": [{"key": "outage", "on_recovery": {"reset_signals": ["load"]}},
              {"key": "slow"}],
}


def test_a_template_reads_valid_seconds_and_what_a_recovery_resets() -> None:
    template = Template.from_api(TEMPLATE)
    assert template.valid_seconds("deep") == 600
    assert template.valid_seconds("load") == 0
    assert template.valid_seconds("nope") == 0
    assert template.reset_signals("outage") == ["load"]
    assert template.reset_signals("slow") == []
    assert template.rules[0]["on_recovery"] == {"reset_signals": ["load"]}


def test_a_signal_says_when_a_recovery_reset_it() -> None:
    resource = Resource.from_api({
        "id": "r1", "key": "srv-0042", "name": "srv-0042", "template": "service-triage@6", "meta": {},
        "created_at": "2026-10-04T10:00:00Z", "open_incident": None,
        "signals": [{"id": "s1", "key": "load", "kind": "event", "states": ["ok"],
                     "reset": {"at": "2026-10-04T10:05:00Z", "rule": "outage"}},
                    {"id": "s2", "key": "deep", "kind": "event", "states": ["ok"], "reset": None},
                    {"id": "s3", "key": "beat", "kind": "heartbeat", "states": ["ok"]}],
    })
    reset = resource.signals[0].reset
    assert reset is not None
    assert (reset.at, reset.rule) == (datetime(2026, 10, 4, 10, 5, tzinfo=timezone.utc), "outage")
    assert resource.signals[1].reset is None
    assert resource.signals[2].reset is None


def _observation(confirmation: dict[str, Any]) -> Observation:
    return Observation.from_api({
        "id": "o1", "signal": "port", "location": "", "state": "problem", "value": None, "labels": {},
        "at": "2026-10-04T10:00:00Z", "received_at": "2026-10-04T10:00:01Z", "source": "api",
        "confirmation": {"status": "confirmed", "reason": "refuted", "effective": "ok", "refuted_if": "any_ok",
                         "deadline": "2026-10-04T10:00:30Z", "decided_at": None, "confirmers": [], **confirmation},
    })


def test_a_confirmation_says_whether_it_was_shared() -> None:
    joined = _observation({"shared": True}).confirmation
    own = _observation({"shared": False}).confirmation
    older = _observation({}).confirmation
    assert [None if one is None else one.shared for one in (joined, own, older)] == [True, False, False]


def test_a_comparison_reads_a_confirmation() -> None:
    assert Comparison("port", "confirmation", "eq", "refuted").to_api() == {
        "signal": "port", "field": "confirmation", "operator": "eq", "operand": "refuted"}


def test_a_location_is_created(client: UptimerClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", url=f"{BASE}/v3/locations", status_code=201,
                            json=ok({"id": "l1", "name": "edge-a"}))
    httpx_mock.add_response(method="POST", url=f"{BASE}/v3/locations", status_code=200,
                            json=ok({"id": "l1", "name": "edge-a"}))
    made = client.create_location("edge-a")
    again = client.create_location("edge-a")
    assert made == again
    assert (made.id, made.name) == ("l1", "edge-a")
    assert [json.loads(r.content) for r in httpx_mock.get_requests()] == [{"name": "edge-a"}] * 2


def test_a_blank_location_is_refused(client: UptimerClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", url=f"{BASE}/v3/locations", status_code=422,
                            json=refused(1422, "validation", {"field": "name"}))
    with pytest.raises(ValidationError) as caught:
        client.create_location(" ")
    assert caught.value.field == "name"


WORKER = {"id": "wk1", "uid": UID, "name": "worker-01", "location": {"id": "l1", "name": "edge-a"},
          "tags": ["linux"], "active": False}


def test_workers_are_listed(client: UptimerClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="GET", url=f"{BASE}/v3/workers", json=ok([
        WORKER, {**WORKER, "id": "wk2", "uid": "u2", "location": None, "tags": [], "active": True}]))
    first, second = client.workers()
    assert (first.id, first.uid, first.name, first.tags, first.active, first.next_step) == (
        "wk1", UID, "worker-01", ["linux"], False, None)
    assert first.location is not None
    assert (first.location.id, first.location.name) == ("l1", "edge-a")
    assert second.location is None
    assert second.active is True


def test_a_worker_is_registered_with_its_next_step(client: UptimerClient, httpx_mock: HTTPXMock) -> None:
    step = f"uptimer worker-cert --uid {UID} --out ./{UID}"
    httpx_mock.add_response(method="POST", url=f"{BASE}/v3/workers", status_code=201,
                            json=ok({**WORKER, "next_step": step}))
    httpx_mock.add_response(method="POST", url=f"{BASE}/v3/workers", status_code=201,
                            json=ok({**WORKER, "tags": [], "next_step": step}))
    worker = client.register_worker(name="worker-01", uid=UID, location="l1", tags=["linux"])
    client.register_worker(name="worker-01", uid=UID, location="l1")
    assert worker.next_step == step
    sent = [json.loads(r.content) for r in httpx_mock.get_requests()]
    assert sent == [{"name": "worker-01", "uid": UID, "location": "l1", "tags": ["linux"]},
                    {"name": "worker-01", "uid": UID, "location": "l1"}]


def test_a_known_uid_is_a_conflict(client: UptimerClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", url=f"{BASE}/v3/workers", status_code=409,
                            json=refused(1409, "conflict", {"field": "uid"}))
    with pytest.raises(ConflictError) as caught:
        client.register_worker(name="worker-01", uid=UID, location="l1")
    assert caught.value.field == "uid"


def test_a_scoped_key_may_not_list_workers(client: UptimerClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="GET", url=f"{BASE}/v3/workers", status_code=403,
                            json=refused(1403, "forbidden", {"scope": "full"}))
    with pytest.raises(ForbiddenError) as caught:
        client.workers()
    assert caught.value.details == {"scope": "full"}
