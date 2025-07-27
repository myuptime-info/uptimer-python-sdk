from pytest_httpx import HTTPXMock

from tests.conftest import api_response
from uptimer.client import UptimerClient
from uptimer.endpoints.regions import RegionsEndpoint


def test_client_regions_endpoint_class(uptimer_client: UptimerClient):
    regions = uptimer_client.v1.regions
    assert isinstance(regions, RegionsEndpoint)
    assert callable(regions.all)
    assert regions.path == "v1/regions"
    assert regions.url.endswith(regions.path)


def test_get_regions(
    uptimer_client: UptimerClient,
    httpx_mock: HTTPXMock,
):
    regions_result = [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "local",
            "active_workers_count": 1,
            "kind": "region",
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "name": "us-east-1",
            "active_workers_count": 3,
            "kind": "region",
        },
    ]
    httpx_mock.add_response(json=api_response(regions_result))
    regions_objects_list = uptimer_client.v1.regions.all()
    assert len(regions_objects_list) == len(regions_result)
    for region_object, region_result in zip(
        regions_objects_list,
        regions_result,
    ):
        assert region_object.id == region_result["id"]
        assert region_object.name == region_result["name"]
        assert (
            region_object.active_workers_count == region_result["active_workers_count"]
        )
        assert region_object.kind == region_result["kind"]
