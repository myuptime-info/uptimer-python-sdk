from uptimer.client import UptimerClient
from uptimer.endpoints.endpoint import BaseEndpoint
from uptimer.http import UptimerHttpLib


def test_endpoint(uptimer_http: UptimerHttpLib, base_url: str):
    v1 = BaseEndpoint(uptimer_http, "v1")
    assert v1.segment == "v1"
    assert v1.url == base_url + "/" + v1.path
    assert v1.path == "v1"


def test_nested_endpoint_with_parent_as_str(
    uptimer_http: UptimerHttpLib,
    base_url: str,
):
    workspace = BaseEndpoint(uptimer_http, "workspace", "v1")
    assert workspace.segment == "workspace"
    assert workspace.url == base_url + "/v1/workspace"
    assert workspace.path == "v1/workspace"


def test_nested_endpoint_with_parent_as_list(
    uptimer_http: UptimerHttpLib,
    base_url: str,
):
    workspace = BaseEndpoint(uptimer_http, "workspace", ["v1"])
    assert workspace.segment == "workspace"
    assert workspace.url == base_url + "/v1/workspace"
    assert workspace.path == "v1/workspace"
