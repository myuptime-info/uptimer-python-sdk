from typing import Any

import pytest

from uptimer.client import UptimerClient
from uptimer.http import UptimerHttpLib


@pytest.fixture
def base_url() -> str:
    return "http://127.0.0.1:2519"


@pytest.fixture
def uptimer_http(base_url: str) -> UptimerHttpLib:
    return UptimerHttpLib(api_key="test", base_url=base_url)


@pytest.fixture
def uptimer_client(uptimer_http: UptimerHttpLib) -> UptimerClient:
    client = UptimerClient(api_key="test", base_url=uptimer_http.base_url)
    client.set_uptimer_http_lib(uptimer_http)
    return client


def api_response(result: Any, error: Any = None, meta: Any = None) -> dict:  # noqa: ANN401
    return {
        "result": result,
        "error": error,
        "meta": meta,
    }
