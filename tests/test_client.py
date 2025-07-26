from pytest_httpx import HTTPXMock

from tests.conftest import api_response
from uptimer.client import UptimerClient
from uptimer.endpoints.v1 import V1Endpoint


def test_version(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    assert isinstance(uptimer_client.v1, V1Endpoint)
    expected_version = "1.0.0"
    httpx_mock.add_response(json=api_response(expected_version))
    assert uptimer_client.version() == expected_version


def test_get_workspaces(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    assert isinstance(uptimer_client.v1, V1Endpoint)
    workspaces_result = [
        {"id": "1", "name": "Workspace 1", "role": "admin", "kind": "workspace"},
        {"id": "2", "name": "Workspace 2", "role": "user", "kind": "workspace"},
    ]
    httpx_mock.add_response(json=api_response(workspaces_result))
    workspaces_objects_list = uptimer_client.v1.workspaces.all()
    assert len(workspaces_objects_list) == len(workspaces_result)
    for workspace_object, workspace_result in zip(
        workspaces_objects_list,
        workspaces_result,
    ):
        assert workspace_object.id == workspace_result["id"]
        assert workspace_object.name == workspace_result["name"]
        assert workspace_object.role == workspace_result["role"]
        assert workspace_object.kind == workspace_result["kind"]
