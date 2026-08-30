from __future__ import annotations

from typing import cast

from uptimer.compat import ensure_v2_supported
from uptimer.endpoints.v2 import V2Endpoint
from uptimer.http import UptimerHttpLib


class UptimerClient:
    """
    The Uptimer API client.

    Resources are reached through the API version that serves them:
    `client.v2.workspaces`, `client.v2.locations`, `client.v2.incidents`,
    `client.v2.monitoring.websites` and
    `client.v2.subjects(subject).signals(signal).observations`. This SDK does
    not speak API v1 — see the migration note in the README if you are coming
    from 0.4.x.

    `version()` and the compatibility helpers stay here rather than under a
    version namespace, because `/version` is shared and unversioned.
    """

    v2: V2Endpoint

    def __init__(self, api_key: str, base_url: str):
        self._http_lib = UptimerHttpLib(api_key, base_url)
        self._checked_compat = False
        self._wire()

    def _wire(self) -> None:
        self.v2 = V2Endpoint(self._http_lib)

    def version(self) -> str:
        """
        Return the server version.

        `/version` is a shared global endpoint, not a versioned one, so this
        works against any server — including one too old for the rest of this
        SDK.
        """
        response = self._http_lib.client.get(self._http_lib.build_url("version"))
        return cast("str", self._http_lib.parse_response(response=response))

    def check_compatibility(self) -> str:
        """
        Verify the server provides API v2, and return its version.

        Raises IncompatibleServerError if it does not. Called once per client
        by ensure_compatible(); call it directly to fail fast at startup.
        """
        version = self.version()
        ensure_v2_supported(version)
        self._checked_compat = True
        return version

    def ensure_compatible(self) -> None:
        """Run the compatibility check once, then never again."""
        if not self._checked_compat:
            self.check_compatibility()

    def set_uptimer_http_lib(self, http_lib: UptimerHttpLib) -> None:
        self._http_lib = http_lib
        self._checked_compat = False
        self._wire()


class UptimerCloudClient(UptimerClient):
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://myuptime.info/api")
