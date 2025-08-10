import os

import pytest

from uptimer.client import UptimerClient


@pytest.fixture(scope="session")
def uptimer_url() -> str:
    return os.environ.get("UPTIMER_URL", "http://localhost:2517")

def _get_api_url(url: str) -> str:
    if url.endswith("/"):
        url = url[:-1]
    if not url.endswith("/api"):
        url = url + "/api"
    return url

def get_client(api_key: str, uptimer_url: str) -> UptimerClient:
    return UptimerClient(api_key, _get_api_url(uptimer_url))



