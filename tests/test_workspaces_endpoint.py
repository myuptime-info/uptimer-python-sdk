from uptimer.client import UptimerClient
from uptimer.endpoints.workspaces import WorkspacesEndpoint


def test_client_workspace_endpoint_class(uptimer_client: UptimerClient):
    workspaces = uptimer_client.v1.workspaces
    assert isinstance(workspaces, WorkspacesEndpoint)
    assert callable(workspaces.all)
    assert workspaces.path == "v1/workspaces"
    assert workspaces.url.endswith(workspaces.path)
