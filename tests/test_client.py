from pytest_httpx import HTTPXMock

from tests.conftest import api_response
from uptimer.client import UptimerClient, UptimerCloudClient
from uptimer.compat import MINIMUM_UPTIMER_VERSION
from uptimer.endpoints.incidents import IncidentsEndpoint
from uptimer.endpoints.locations import LocationsEndpoint
from uptimer.endpoints.v2 import V2Endpoint
from uptimer.endpoints.websites import MonitoringEndpoint
from uptimer.endpoints.workspaces import WorkspacesEndpoint

# The resources a caller reaches through client.v2, and nothing else.
V2_RESOURCES = ("workspaces", "locations", "incidents", "monitoring")


def test_client_exposes_v2_resources_under_the_version_namespace(
    uptimer_client: UptimerClient,
):
    assert isinstance(uptimer_client.v2, V2Endpoint)
    assert isinstance(uptimer_client.v2.workspaces, WorkspacesEndpoint)
    assert isinstance(uptimer_client.v2.locations, LocationsEndpoint)
    assert isinstance(uptimer_client.v2.incidents, IncidentsEndpoint)
    assert isinstance(uptimer_client.v2.monitoring, MonitoringEndpoint)


def test_client_keeps_no_root_level_aliases(uptimer_client: UptimerClient):
    # The API is versioned by path, so the SDK keeps the version visible. A
    # root alias would let code drift into looking version-agnostic when it is
    # not (Decision 0012).
    for resource in V2_RESOURCES:
        assert not hasattr(uptimer_client, resource), (
            f"client.{resource} must only be reachable as client.v2.{resource}"
        )
    # 1.5.x targets API v2 only; there is no v1 namespace to fall back to.
    assert not hasattr(uptimer_client, "v1")


def test_cloud_client_exposes_the_same_namespace():
    client = UptimerCloudClient(api_key="test")
    assert isinstance(client.v2, V2Endpoint)
    assert client.v2.workspaces.url == "https://myuptime.info/api/v2/workspaces"
    assert (
        client.v2.monitoring.websites.url
        == "https://myuptime.info/api/v2/monitoring/websites"
    )
    for resource in V2_RESOURCES:
        assert not hasattr(client, resource)


def test_custom_base_url_builds_v2_urls_onto_it():
    client = UptimerClient(api_key="test", base_url="https://uptimer.example/api/")
    assert client.v2.locations.url == "https://uptimer.example/api/v2/locations"
    assert client.v2.incidents.url == "https://uptimer.example/api/v2/incidents"


def test_swapping_the_http_lib_rewires_the_namespace(
    uptimer_client: UptimerClient,
    base_url: str,
):
    # set_uptimer_http_lib rebuilds the namespace, so the endpoints under it
    # must follow the new transport rather than keep the old one.
    assert uptimer_client.v2.workspaces.url.startswith(base_url)


def test_version_is_unversioned(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
    base_url: str,
):
    # /version is a shared global endpoint, so it works against any server —
    # including one too old for the rest of this SDK.
    expected_version = "1.5.0"
    httpx_mock.add_response(json=api_response(expected_version))
    assert uptimer_client.version() == expected_version
    requested = str(httpx_mock.get_requests()[0].url)
    assert requested == base_url + "/version"
    assert "/v2/" not in requested


def test_check_compatibility_stays_on_the_unversioned_endpoint(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
    base_url: str,
):
    # A server this SDK speaks to. The bar is the SDK's own major.minor, so the
    # version here follows the package rather than being pinned to whatever was
    # current when the test was written.
    httpx_mock.add_response(json=api_response(_supported_server_version()))
    assert uptimer_client.check_compatibility() == _supported_server_version()
    assert str(httpx_mock.get_requests()[0].url) == base_url + "/version"


def test_ensure_compatible_checks_once(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(json=api_response(_supported_server_version()))
    uptimer_client.ensure_compatible()
    uptimer_client.ensure_compatible()
    assert len(httpx_mock.get_requests()) == 1


def _supported_server_version() -> str:
    """
    Return the oldest server this SDK accepts, as a version string.

    Derived from MINIMUM_UPTIMER_VERSION rather than written down: that constant
    is itself derived from the package version (Decision 0013), so a bump moves
    both together. Hard-coding "1.5.0" here is what made these two tests fail
    the moment the package became 1.6.
    """
    major, minor, patch = MINIMUM_UPTIMER_VERSION
    return f"{major}.{minor}.{patch}"


def test_get_workspaces(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    workspaces_result = [
        {"id": "1", "name": "Workspace 1", "role": "admin", "kind": "workspace"},
        {"id": "2", "name": "Workspace 2", "role": "user", "kind": "workspace"},
    ]
    httpx_mock.add_response(json=api_response(workspaces_result))
    workspaces = uptimer_client.v2.workspaces.all()
    assert len(workspaces) == len(workspaces_result)
    for obj, expected in zip(workspaces, workspaces_result):
        assert obj.id == expected["id"]
        assert obj.name == expected["name"]
        assert obj.role == expected["role"]
        assert obj.kind == expected["kind"]
