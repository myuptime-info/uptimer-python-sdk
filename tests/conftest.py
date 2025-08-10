import os
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from uptimer.client import UptimerClient
from uptimer.http import UptimerHttpLib


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--integration",
        action="store_true",
        dest="integration",
        default=False,
        help="enable integration tests",
    )


# Integration test marker
integration_test = pytest.mark.skipif("not config.getoption('integration')")


@pytest.fixture
def uptimer_url() -> str:
    """Get the uptimer URL from environment variable or use default."""
    return os.getenv("UPTIMER_URL", "http://localhost:2517")


@pytest.fixture(scope="session")
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


def api_response(
    result: Any,  # noqa: ANN401
    error: Any = None,  # noqa: ANN401
    meta: Any = None,  # noqa: ANN401
) -> dict:
    return {
        "result": result,
        "error": error,
        "meta": meta,
    }
