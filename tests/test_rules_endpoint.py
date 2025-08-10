import pytest
from pytest_httpx import HTTPXMock

from uptimer.client import UptimerClient
from uptimer.endpoints.rules import RulesEndpoint
from uptimer.models import (
    InvalidDataTypeError,
    MissingKindError,
    TypeMismatchError,
    UnknownKindError,
    from_api,
    from_api_region,
    from_api_rule,
    from_api_workspace,
)
from uptimer.models.rule import (
    CreateRuleRequest,
    DeleteRuleResponse,
    Rule,
    RuleRequest,
    RuleResponse,
    RuleResponseBody,
)

from .conftest import api_response


def test_universal_deserializer():
    """Test the universal from_api deserializer with different object types."""
    # Test Rule deserialization
    rule_data = {
        "id": "test-rule-id",
        "name": "Test Rule",
        "interval": 60,
        "workspace_id": "test-workspace-id",
        "request": {
            "url": "https://example.com",
            "method": "GET",
            "content_type": "application/json",
            "data": "{}",
            "kind": "rule_request",
        },
        "response": {
            "statuses": [200],
            "body": {
                "content": "expected content",
                "kind": "rule_response_body",
            },
            "kind": "rule_response",
        },
        "kind": "rule",
    }

    rule = from_api_rule(rule_data)
    assert rule.id == "test-rule-id"
    assert rule.name == "Test Rule"
    assert isinstance(rule.request, RuleRequest)
    assert isinstance(rule.response, RuleResponse)
    assert isinstance(rule.response.body, RuleResponseBody)

    # Test Region deserialization
    region_data = {
        "id": "test-region-id",
        "name": "Test Region",
        "active_workers_count": 5,
        "kind": "region",
    }

    region = from_api_region(region_data)
    assert region.id == "test-region-id"
    assert region.name == "Test Region"
    assert region.active_workers_count == 5

    # Test Workspace deserialization
    workspace_data = {
        "id": "test-workspace-id",
        "name": "Test Workspace",
        "role": "admin",
        "kind": "workspace",
    }

    workspace = from_api_workspace(workspace_data)
    assert workspace.id == "test-workspace-id"
    assert workspace.name == "Test Workspace"
    assert workspace.role == "admin"


def test_universal_deserializer_errors():
    """Test the universal from_api deserializer error handling."""
    # Test with missing kind
    with pytest.raises(MissingKindError):
        from_api({"id": "test", "name": "test"})

    # Test with unknown kind
    with pytest.raises(UnknownKindError):
        from_api({"id": "test", "kind": "unknown_kind"})

    # Test with non-dict data
    with pytest.raises(InvalidDataTypeError):
        from_api("not a dict")

    # Test type mismatch in typed deserializers
    with pytest.raises(TypeMismatchError):
        from_api_rule(
            {
                "id": "test",
                "name": "Test Region",
                "active_workers_count": 5,
                "kind": "region",
            },
        )


def test_client_rules_endpoint_class(uptimer_client: UptimerClient):
    rules = uptimer_client.v1.rules
    assert isinstance(rules, RulesEndpoint)
    assert callable(rules.get)
    assert callable(rules.all)
    assert callable(rules.create)
    assert callable(rules.update)
    assert callable(rules.delete)
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
            "workspace_id": "03075d25-6cad-4205-ad83-2da1bd8fad9c",
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
                    "kind": "rule_response_body",
                },
                "kind": "rule_response",
            },
            "kind": "rule",
        },
        {
            "id": "74ed4706-0ec1-459d-822d-5e03952610ef",
            "name": "test2",
            "interval": 120,
            "workspace_id": "03075d25-6cad-4205-ad83-2da1bd8fad9c",
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
                    "kind": "rule_response_body",
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
        assert isinstance(rule_result, dict)  # mypy
        # Test top-level properties
        assert rule_object.id == rule_result["id"]
        assert rule_object.name == rule_result["name"]
        assert rule_object.interval == rule_result["interval"]
        assert rule_object.workspace_id == rule_result["workspace_id"]
        assert rule_object.kind == rule_result["kind"]

        # Test request properties
        request_data = rule_result["request"]
        assert isinstance(request_data, dict) # mypy
        assert rule_object.request.url == request_data["url"]
        assert rule_object.request.method == request_data["method"]
        assert rule_object.request.content_type == request_data["content_type"]
        assert rule_object.request.data == request_data["data"]
        assert rule_object.request.kind == request_data["kind"]

        # Test response properties
        response_data = rule_result["response"]
        assert isinstance(response_data, dict)  # mypy
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
        "workspace_id": "03075d25-6cad-4205-ad83-2da1bd8fad9c",
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
                "kind": "rule_response_body",
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
    assert rule_object.workspace_id == rule_result["workspace_id"]
    assert rule_object.kind == rule_result["kind"]

    # Test request properties
    request_data = rule_result["request"]
    assert isinstance(request_data, dict) # mypy
    assert rule_object.request.url == request_data["url"]
    assert rule_object.request.method == request_data["method"]
    assert rule_object.request.content_type == request_data["content_type"]
    assert rule_object.request.data == request_data["data"]
    assert rule_object.request.kind == request_data["kind"]

    # Test response properties
    response_data = rule_result["response"]
    assert isinstance(response_data, dict)  # mypy
    assert rule_object.response.statuses == response_data["statuses"]
    assert rule_object.response.body.content == response_data["body"]["content"]
    assert rule_object.response.kind == response_data["kind"]


def test_create_rule(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    workspace_id = "03075d25-6cad-4205-ad83-2da1bd8fad9c"
    rule_id = "d901834d-5768-46ae-91f5-7974b0c764b2"

    # Create request data
    create_request = CreateRuleRequest(
        name="My Test Rule",
        interval=60,
        workspace_id=workspace_id,
        request=RuleRequest(
            url="https://example.com",
            method="GET",
            content_type="application/json",
            data="",
            kind="rule_request",
        ),
        response=RuleResponse(
            statuses=[200],
            body=RuleResponseBody(content="expected response"),
            kind="rule_response",
        ),
        kind="rule",
    )

    # Expected response from API
    rule_result = {
        "id": rule_id,
        "name": "My Test Rule",
        "interval": 60,
        "workspace_id": workspace_id,
        "request": {
            "url": "https://example.com",
            "method": "GET",
            "content_type": "application/json",
            "data": "",
            "kind": "rule_request",
        },
        "response": {
            "statuses": [200],
            "body": {
                "content": "expected response",
                "kind": "rule_response_body",
            },
            "kind": "rule_response",
        },
        "kind": "rule",
    }

    # Mock the POST request
    httpx_mock.add_response(
        method="POST",
        json=api_response(rule_result),
        match_content=b'{"name":"My Test Rule","interval":60,"workspace_id":"03075d25-6cad-4205-ad83-2da1bd8fad9c","request":{"url":"https://example.com","method":"GET","content_type":"application/json","data":"","kind":"rule_request"},"response":{"statuses":[200],"body":{"content":"expected response","kind":"rule_response_body"},"kind":"rule_response"},"kind":"rule"}',
    )

    rule_object = uptimer_client.v1.rules.create(create_request)

    # Test top-level properties
    assert rule_object.id == rule_result["id"]
    assert rule_object.name == rule_result["name"]
    assert rule_object.interval == rule_result["interval"]
    assert rule_object.workspace_id == rule_result["workspace_id"]
    assert rule_object.kind == rule_result["kind"]

    # Test request properties
    request_data = rule_result["request"]
    assert isinstance(request_data, dict)  # mypy
    assert rule_object.request.url == request_data["url"]
    assert rule_object.request.method == request_data["method"]
    assert rule_object.request.content_type == request_data["content_type"]
    assert rule_object.request.data == request_data["data"]
    assert rule_object.request.kind == request_data["kind"]

    # Test response properties
    response_data = rule_result["response"]
    assert isinstance(response_data, dict)  # mypy
    assert rule_object.response.statuses == response_data["statuses"]
    assert rule_object.response.body.content == response_data["body"]["content"]
    assert rule_object.response.kind == response_data["kind"]


def test_update_rule_with_rule(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    rule_id = "cab7d015-de14-46e1-82e3-52c14ce6b7f9"

    # Create update request data using Rule model
    update_request = Rule(
        id=rule_id,
        name="Updated Rule Name",
        interval=120,
        workspace_id="03075d25-6cad-4205-ad83-2da1bd8fad9c",
        request=RuleRequest(
            url="https://updated-example.com",
            method="POST",
            content_type="application/json",
            data='{"key2": "value"}',
            kind="rule_request",
        ),
        response=RuleResponse(
            statuses=[200, 201],
            body=RuleResponseBody(content="updated expected response"),
            kind="rule_response",
        ),
        kind="rule",
    )

    # Expected response from API
    rule_result = {
        "id": rule_id,
        "name": "Updated Rule Name",
        "interval": 120,
        "workspace_id": "03075d25-6cad-4205-ad83-2da1bd8fad9c",
        "request": {
            "url": "https://updated-example.com",
            "method": "POST",
            "content_type": "application/json",
            "data": '{"key2": "value"}',
            "kind": "rule_request",
        },
        "response": {
            "statuses": [200, 201],
            "body": {
                "content": "updated expected response",
                "kind": "rule_response_body",
            },
            "kind": "rule_response",
        },
        "kind": "rule",
    }

    # Mock the POST request for update
    httpx_mock.add_response(
        method="POST",
        json=api_response(rule_result),
        match_content=b'{"name":"Updated Rule Name","interval":120,"workspace_id":"03075d25-6cad-4205-ad83-2da1bd8fad9c","request":{"url":"https://updated-example.com","method":"POST","content_type":"application/json","data":"{\\"key2\\": \\"value\\"}","kind":"rule_request"},"response":{"statuses":[200,201],"body":{"content":"updated expected response","kind":"rule_response_body"},"kind":"rule_response"},"kind":"rule"}',
    )

    rule_object = uptimer_client.v1.rules.update(rule_id, update_request)

    # Test top-level properties
    assert rule_object.id == rule_result["id"]
    assert rule_object.name == rule_result["name"]
    assert rule_object.interval == rule_result["interval"]
    assert rule_object.workspace_id == rule_result["workspace_id"]
    assert rule_object.kind == rule_result["kind"]

    # Test request properties
    request_data = rule_result["request"]
    assert isinstance(request_data, dict)  # mypy
    assert rule_object.request.url == request_data["url"]
    assert rule_object.request.method == request_data["method"]
    assert rule_object.request.content_type == request_data["content_type"]
    assert rule_object.request.data == request_data["data"]
    assert rule_object.request.kind == request_data["kind"]

    # Test response properties
    response_data = rule_result["response"]
    assert isinstance(response_data, dict)  # mypy
    assert rule_object.response.statuses == response_data["statuses"]
    assert rule_object.response.body.content == response_data["body"]["content"]
    assert rule_object.response.kind == response_data["kind"]


def test_update_rule_with_create_request(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    rule_id = "cab7d015-de14-46e1-82e3-52c14ce6b7f9"

    # Create update request data using CreateRuleRequest (BaseRule)
    update_request = CreateRuleRequest(
        name="Updated Rule Name",
        interval=120,
        workspace_id="03075d25-6cad-4205-ad83-2da1bd8fad9c",
        request=RuleRequest(
            url="https://updated-example.com",
            method="POST",
            content_type="application/json",
            data='{"key2": "value"}',
            kind="rule_request",
        ),
        response=RuleResponse(
            statuses=[200, 201],
            body=RuleResponseBody(content="updated expected response"),
            kind="rule_response",
        ),
        kind="rule",
    )

    # Expected response from API
    rule_result = {
        "id": rule_id,
        "name": "Updated Rule Name",
        "interval": 120,
        "workspace_id": "03075d25-6cad-4205-ad83-2da1bd8fad9c",
        "request": {
            "url": "https://updated-example.com",
            "method": "POST",
            "content_type": "application/json",
            "data": '{"key2": "value"}',
            "kind": "rule_request",
        },
        "response": {
            "statuses": [200, 201],
            "body": {
                "content": "updated expected response",
                "kind": "rule_response_body",
            },
            "kind": "rule_response",
        },
        "kind": "rule",
    }

    # Mock the POST request for update
    httpx_mock.add_response(
        method="POST",
        json=api_response(rule_result),
        match_content=b'{"name":"Updated Rule Name","interval":120,"workspace_id":"03075d25-6cad-4205-ad83-2da1bd8fad9c","request":{"url":"https://updated-example.com","method":"POST","content_type":"application/json","data":"{\\"key2\\": \\"value\\"}","kind":"rule_request"},"response":{"statuses":[200,201],"body":{"content":"updated expected response","kind":"rule_response_body"},"kind":"rule_response"},"kind":"rule"}',
    )

    rule_object = uptimer_client.v1.rules.update(rule_id, update_request)

    # Test top-level properties
    assert rule_object.id == rule_result["id"]
    assert rule_object.name == rule_result["name"]
    assert rule_object.interval == rule_result["interval"]
    assert rule_object.workspace_id == rule_result["workspace_id"]
    assert rule_object.kind == rule_result["kind"]

    # Test request properties
    request_data = rule_result["request"]
    assert isinstance(request_data, dict)  # mypy
    assert rule_object.request.url == request_data["url"]
    assert rule_object.request.method == request_data["method"]
    assert rule_object.request.content_type == request_data["content_type"]
    assert rule_object.request.data == request_data["data"]
    assert rule_object.request.kind == request_data["kind"]

    # Test response properties
    response_data = rule_result["response"]
    assert isinstance(response_data, dict)  # mypy
    assert rule_object.response.statuses == response_data["statuses"]
    assert rule_object.response.body.content == response_data["body"]["content"]
    assert rule_object.response.kind == response_data["kind"]


def test_delete_rule(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    rule_id = "cab7d015-de14-46e1-82e3-52c14ce6b7f9"

    # Expected delete response from API
    delete_result = {
        "message": "Rule deleted successfully",
        "rule_id": rule_id,
    }

    # Mock the DELETE request
    httpx_mock.add_response(
        method="DELETE",
        json=api_response(delete_result),
    )

    # Should return DeleteRuleResponse object
    delete_response = uptimer_client.v1.rules.delete(rule_id)

    assert delete_response.message == delete_result["message"]
    assert delete_response.rule_id == delete_result["rule_id"]
