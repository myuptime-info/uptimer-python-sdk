"""Signal Confirmations, `if_unknown` and their outcomes, as API v3 serves them (2.0)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Iterator

import pytest

from uptimer import Comparison, Confirmer, ConfirmPolicy, UptimerClient, meta
from uptimer.models import Incident, Observation, Resource

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock

BASE = "http://uptimer.test/api"
WS = f"{BASE}/v3/workspaces/w1"


def ok(result: object) -> dict[str, Any]:
    return {"result": result, "error": None, "meta": None}


@pytest.fixture
def client() -> Iterator[UptimerClient]:
    with UptimerClient(api_key="k3y", base_url=BASE + "/") as c:
        yield c


POLICY = ConfirmPolicy(
    by=[Confirmer(probe="tcp", with_={"host": meta("host"), "port": 5432}),
        Confirmer(exec="check-replica", with_={"host": meta("host"), "max_lag": 30})],
    refuted_if="any_ok", timeout=30,
)

MANIFEST = {
    "key": "replica", "version": 1, "name": "Replica", "summary": "A synthetic database replica.",
    "fields": [{"key": "host", "label": "Host", "type": "string"}],
    "signals": [{"key": "port", "kind": "event", "confirm": POLICY.to_api()},
                {"key": "deep", "kind": "event", "on_demand": True}],
    "rules": [{"key": "down", "action": "Look at the replica.", "wait": {"confirm_after": 0, "recover_after": 0},
               "decision": {"any": [Comparison("port", "status", "eq", "problem").to_api(),
                                    Comparison("deep", "status", "eq", "problem", if_unknown=False).to_api()]}}],
}


def test_a_confirmation_policy_and_if_unknown_are_written_as_the_api_reads_them(
    client: UptimerClient, httpx_mock: HTTPXMock,
) -> None:
    echoed = {"id": "replica@1", "key": "replica", "version": 1, "name": "Replica", "summary": "s", "fields": [],
              "rules": [], "signals": [{"key": "port", "kind": "event", "states": ["ok", "problem", "no_data"],
                                       "on_demand": False, "confirm": POLICY.to_api()},
                                      {"key": "deep", "kind": "event", "states": ["ok"], "on_demand": True}]}
    httpx_mock.add_response(method="POST", url=f"{WS}/templates", status_code=201, json=ok(echoed))

    published = client.workspace("w1").templates.publish(MANIFEST)

    sent = json.loads(httpx_mock.get_requests()[0].content)
    assert sent["signals"][0]["confirm"] == {
        "on": "problem", "refuted_if": "any_ok", "timeout": 30,
        "by": [{"probe": "tcp", "with": {"host": {"meta": "host"}, "port": 5432}},
               {"exec": "check-replica", "with": {"host": {"meta": "host"}, "max_lag": 30}}],
    }
    assert sent["rules"][0]["decision"]["any"] == [
        {"signal": "port", "field": "status", "operator": "eq", "operand": "problem"},
        {"signal": "deep", "field": "status", "operator": "eq", "operand": "problem", "if_unknown": False},
    ]
    assert published.confirm_policy("port") == POLICY
    assert published.confirm_policy("deep") is None
    assert published.confirm_policy("nothing") is None


def test_a_confirmer_without_settings_sends_none() -> None:
    assert Confirmer(exec="check-port").to_api() == {"exec": "check-port"}
    assert Comparison("deep", "known").to_api() == {"signal": "deep", "field": "known"}


def test_a_signal_reads_what_its_newest_readings_confirmation_decided() -> None:
    resource = Resource.from_api({
        "id": "r1", "key": "db-1", "name": "db-1", "template": "replica@1", "meta": {}, "created_at": "2026-10-11T10:00:00Z",
        "open_incident": None, "maintenance": None, "rules": [],
        "signals": [
            {"id": "s1", "key": "port", "kind": "event", "states": ["ok"], "applicability": "applicable", "missing": None,
             "on_demand": False, "not_checked": False,
             "confirmation": {"status": "confirmed", "reason": "refuted", "effective": "ok", "original": "problem"}},
            {"id": "s2", "key": "lag", "kind": "event", "states": ["ok"], "applicability": "applicable", "missing": None,
             "on_demand": False, "not_checked": False,
             "confirmation": {"status": "pending", "reason": None, "effective": "problem", "original": "problem"}},
            {"id": "s3", "key": "beat", "kind": "heartbeat", "states": ["ok"], "applicability": "applicable",
             "missing": "stale", "on_demand": False, "not_checked": False, "confirmation": None},
            {"id": "s4", "key": "deep", "kind": "event", "states": ["ok"], "on_demand": True, "not_checked": True},
        ],
    })
    port, lag, beat, deep = resource.signals
    assert port.confirmation is not None
    assert (port.confirmation.status, port.confirmation.reason, port.confirmation.effective,
            port.confirmation.original) == ("confirmed", "refuted", "ok", "problem")
    assert lag.confirmation is not None
    assert (lag.confirmation.status, lag.confirmation.reason) == ("pending", None)
    assert (beat.confirmation, beat.missing) == (None, "stale")
    assert (deep.confirmation, deep.not_checked, deep.missing) == (None, True, None)


@pytest.mark.parametrize(("status", "reason", "effective"), [
    ("confirmed", "problem_confirmed", "problem"),
    ("unconfirmed", "timeout", "problem"),
    ("unconfirmed", "confirmer_no_data", "problem"),
    ("unconfirmed", "limited", "problem"),
    ("not_run", "source_no_data", "no_data"),
])
def test_every_outcome_and_reason_reads_back(status: str, reason: str, effective: str) -> None:
    read = Resource.from_api({"id": "r1", "key": "k", "name": "n", "template": None, "meta": {}, "created_at":
                              "2026-10-11T10:00:00Z", "open_incident": None, "signals": [
                                  {"id": "s1", "key": "port", "kind": "event", "states": [], "confirmation": {
                                      "status": status, "reason": reason, "effective": effective,
                                      "original": "no_data" if status == "not_run" else "problem"}}]})
    said = read.signals[0].confirmation
    assert said is not None
    assert (said.status, said.reason, said.effective) == (status, reason, effective)


def test_signal_history_keeps_the_original_and_each_confirmers_reading(
    client: UptimerClient, httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(method="GET", url=f"{WS}/resources/db-1/observations?limit=50", json=ok([
        {"id": "o2", "signal": "port", "location": "", "state": "problem", "value": None, "labels": {}, "reason": "",
         "at": "2026-10-11T10:00:00Z", "received_at": "2026-10-11T10:00:01Z", "source": "api",
         "confirmation": {
             "status": "confirmed", "reason": "refuted", "effective": "ok", "refuted_if": "any_ok",
             "deadline": "2026-10-11T10:00:31Z", "decided_at": "2026-10-11T10:00:04Z",
             "confirmers": [
                 {"probe": "tcp", "state": "ok", "value": 3.5, "reason": "port 5432 open", "at": "2026-10-11T10:00:03Z"},
                 {"exec": "check-replica", "state": "problem", "value": 40,
                  "reason": "CRITICAL - replica 40s behind", "at": "2026-10-11T10:00:04Z"},
             ]}},
        {"id": "o1", "signal": "port", "location": "", "state": "problem", "value": None, "labels": {}, "reason": "",
         "at": "2026-10-11T09:00:00Z", "received_at": "2026-10-11T09:00:01Z", "source": "api",
         "confirmation": {"status": "unconfirmed", "reason": "timeout", "effective": "problem", "refuted_if": "any_ok",
                          "deadline": "2026-10-11T09:00:31Z", "decided_at": "2026-10-11T09:00:31Z",
                          "confirmers": [{"probe": "tcp", "state": None, "value": None, "reason": "", "at": None}]}},
        {"id": "o0", "signal": "beat", "location": "", "state": "ok", "value": None, "labels": {},
         "at": "2026-10-11T08:00:00Z", "received_at": "2026-10-11T08:00:01Z", "source": "api"},
    ]))

    newest, timed_out, plain = client.workspace("w1").resources.observations("db-1")

    assert newest.state == "problem"
    said = newest.confirmation
    assert said is not None
    assert (said.status, said.reason, said.effective, said.refuted_if) == ("confirmed", "refuted", "ok", "any_ok")
    assert said.decided_at is not None
    assert [(c.probe, c.exec, c.state, c.value, c.reason) for c in said.confirmers] == [
        ("tcp", None, "ok", 3.5, "port 5432 open"),
        (None, "check-replica", "problem", 40, "CRITICAL - replica 40s behind"),
    ]
    assert timed_out.confirmation is not None
    assert timed_out.confirmation.reason == "timeout"
    silent = timed_out.confirmation.confirmers[0]
    assert (silent.state, silent.at) == (None, None)
    assert plain.confirmation is None


def test_an_incidents_evidence_says_what_the_rule_read_and_what_the_signal_said() -> None:
    incident = Incident.from_api({
        "id": "i1", "resource": {"id": "r1", "key": "db-1", "name": "db-1"}, "rule": "down", "lifecycle": "open",
        "confirmation": "confirmed", "condition": "problem", "verdict": "problem", "explanation": "port problem",
        "closed_reason": None, "opened_at": "2026-10-11T10:00:04Z", "confirmed_at": "2026-10-11T10:00:04Z",
        "closed_at": None, "effective_at": "2026-10-11T10:00:04Z", "acknowledgement": None,
        "history": [
            {"at": "2026-10-11T10:00:04Z", "kind": "opened", "condition": "problem", "verdict": "problem",
             "explanation": "port problem", "evidence": {"omitted": 0, "truncated": False, "inputs": [
                 {"signal": "port", "status": "problem", "at": "2026-10-11T10:00:00Z",
                  "confirmation": {"status": "unconfirmed", "reason": "confirmer_no_data", "original": "problem"}},
                 {"signal": "beat", "unresolved": "nothing reported"},
             ]}},
            {"at": "2026-10-11T10:05:00Z", "kind": "acknowledged", "condition": "problem", "verdict": "problem",
             "explanation": "", "evidence": None},
        ],
    })
    opened, acknowledged = incident.history
    port, beat = opened.inputs
    assert (port.signal, port.status) == ("port", "problem")
    assert port.confirmation is not None
    assert (port.confirmation.status, port.confirmation.reason, port.confirmation.original) == (
        "unconfirmed", "confirmer_no_data", "problem")
    assert (beat.confirmation, beat.unresolved, beat.status) == (None, "nothing reported", None)
    assert acknowledged.inputs == []
    # An Incident's own confirmation (confirm_after) is not a Signal's.
    assert incident.confirmation == "confirmed"


def test_an_older_server_reads_no_confirmation() -> None:
    observation = Observation.from_api({"id": "o1", "signal": "a", "state": "ok", "value": None, "labels": {},
                                        "at": "2026-10-11T10:00:00Z", "received_at": "2026-10-11T10:00:01Z"})
    assert observation.confirmation is None
