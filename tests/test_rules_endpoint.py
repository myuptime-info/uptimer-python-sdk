from pytest_httpx import HTTPXMock

from tests.conftest import api_response
from uptimer.client import UptimerClient
from uptimer.endpoints.rules import RulesEndpoint


def test_client_rules_endpoint_class(uptimer_client: UptimerClient):
    rules = uptimer_client.v1.rules
    assert isinstance(rules, RulesEndpoint)
    assert callable(rules.get)
    assert callable(rules.all)
    assert rules.path == "v1/rules"
    assert rules.url.endswith(rules.path)


def test_get_rules_list(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    workspace_id = "03075d25-6cad-4205-ad83-2da1bd8fad9c"
    rules_result = [
        {
            "id": "74ed4706-0ec1-459d-822d-5e03952610ee",
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
        },
        {
            "id": "74ed4706-0ec1-459d-822d-5e03952610ef",
            "name": "test2",
            "interval": 120,
            "request": {
                "url": "http://example.com",
                "method": "POST",
                "content_type": "application/json",
                "data": '{"key": "value"}',
                "kind": "rule_request",
            },
            "response": {
                "statuses": [200, 201],
                "body": {
                    "content": "success",
                },
                "kind": "rule_response",
            },
            "kind": "rule",
        },
    ]
    httpx_mock.add_response(json=api_response(rules_result))
    rules_objects_list = uptimer_client.v1.rules.all(workspace_id)

    assert len(rules_objects_list) == len(rules_result)

    for rule_object, rule_result in zip(rules_objects_list, rules_result):
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
