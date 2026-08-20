from pytest_httpx import HTTPXMock

from tests.conftest import api_response
from uptimer.client import UptimerClient
from uptimer.endpoints.incidents import IncidentsEndpoint
from uptimer.endpoints.locations import LocationsEndpoint
from uptimer.endpoints.websites import MonitoringEndpoint
from uptimer.endpoints.workspaces import WorkspacesEndpoint


def test_client_exposes_only_v2_namespaces(uptimer_client: UptimerClient):
    assert isinstance(uptimer_client.workspaces, WorkspacesEndpoint)
    assert isinstance(uptimer_client.locations, LocationsEndpoint)
    assert isinstance(uptimer_client.incidents, IncidentsEndpoint)
    assert isinstance(uptimer_client.monitoring, MonitoringEndpoint)
    # 1.0.0 targets API v2 only; there is no v1 namespace to fall back to.
    assert not hasattr(uptimer_client, "v1")


def test_version_is_unversioned(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    # /version is a shared global endpoint, so it works against any server —
    # including one too old for the rest of this SDK.
    expected_version = "1.5.0"
    httpx_mock.add_response(json=api_response(expected_version))
    assert uptimer_client.version() == expected_version


def test_get_workspaces(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    workspaces_result = [
        {"id": "1", "name": "Workspace 1", "role": "admin", "kind": "workspace"},
        {"id": "2", "name": "Workspace 2", "role": "user", "kind": "workspace"},
    ]
    httpx_mock.add_response(json=api_response(workspaces_result))
    workspaces = uptimer_client.workspaces.all()
    assert len(workspaces) == len(workspaces_result)
    for obj, expected in zip(workspaces, workspaces_result):
        assert obj.id == expected["id"]
        assert obj.name == expected["name"]
        assert obj.role == expected["role"]
        assert obj.kind == expected["kind"]
