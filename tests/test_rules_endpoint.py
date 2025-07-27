from pytest_httpx import HTTPXMock

from tests.conftest import api_response
from uptimer.client import UptimerClient
from uptimer.endpoints.rules import RulesEndpoint


def test_client_rules_endpoint_class(uptimer_client: UptimerClient):
    rules = uptimer_client.v1.rules
    assert isinstance(rules, RulesEndpoint)
    assert callable(rules.get)
    assert rules.path == "v1/rules"
    assert rules.url.endswith(rules.path)


def test_get_rule(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    rule_id = "74ed4706-0ec1-459d-822d-5e03952610ee"
    rule_result = {
        "id": rule_id,
        "name": "test",
        "interval": 60,
        "request": {
            "url": "http://localhost",
            "method": "GET",
            "content_type": "application/json",
            "data": "",
            "kind": "rule_request",
        },
        "response": {
            "statuses": [200, 201, 202, 203, 204, 304],
            "body": {
                "content": "",
            },
            "kind": "rule_response",
        },
        "kind": "rule",
    }
    httpx_mock.add_response(json=api_response(rule_result))
    rule_object = uptimer_client.v1.rules.get(rule_id)

    # Test top-level properties
    assert rule_object.id == rule_result["id"]
    assert rule_object.name == rule_result["name"]
    assert rule_object.interval == rule_result["interval"]
    assert rule_object.kind == rule_result["kind"]

    # Test request properties
    request_data = rule_result["request"]
    assert rule_object.request.url == request_data["url"]
    assert rule_object.request.method == request_data["method"]
    assert rule_object.request.content_type == request_data["content_type"]
    assert rule_object.request.data == request_data["data"]
    assert rule_object.request.kind == request_data["kind"]

    # Test response properties
    response_data = rule_result["response"]
    assert rule_object.response.statuses == response_data["statuses"]
    assert rule_object.response.body.content == response_data["body"]["content"]
    assert rule_object.response.kind == response_data["kind"]
