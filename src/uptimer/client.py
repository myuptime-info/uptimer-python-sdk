from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator

from uptimer.compat import ensure_supported
from uptimer.http import UptimerHttpLib

if TYPE_CHECKING:
    import builtins
    from datetime import datetime

from uptimer.models import (
    Incident,
    Location,
    Observation,
    Observed,
    Page,
    Resource,
    Template,
    Workspace,
)


class UptimerClient:
    """
    The Uptimer API v3 client.

    `base_url` is the server's API root, such as `http://127.0.0.1:8080/api`.
    The API key is a person's key (User → API keys); it reads and writes what
    that person may in each Workspace.

        client = UptimerClient(api_key="…", base_url="http://127.0.0.1:8080/api")
        ws = client.workspace(client.workspaces()[0].id)
        ws.resources.list()
    """

    def __init__(self, api_key: str, base_url: str, *, timeout: float = 30.0):
        self._http = UptimerHttpLib(api_key, base_url, timeout=timeout)
        self._checked = False

    def version(self) -> str:
        """Return the server's version; needs no key."""
        result, _ = self._http.request("GET", "v3/version")
        return str(result["version"])

    def check_compatibility(self) -> str:
        """Raise IncompatibleServerError unless the server serves API v3; return its version."""
        result, _ = self._http.request("GET", "v3/version")
        ensure_supported(str(result.get("version", "")), result.get("api"))
        self._checked = True
        return str(result["version"])

    def ensure_compatible(self) -> None:
        if not self._checked:
            self.check_compatibility()

    def workspaces(self) -> list[Workspace]:
        """Return the Workspaces this key's owner belongs to, with their role in each."""
        result, _ = self._http.request("GET", "v3/workspaces")
        return [Workspace.from_api(one) for one in result]

    def templates(self) -> list[Template]:
        """Return the Templates this server publishes."""
        result, _ = self._http.request("GET", "v3/templates")
        return [Template.from_api(one) for one in result]

    def locations(self) -> list[Location]:
        """Return the Locations checks run from."""
        result, _ = self._http.request("GET", "v3/locations")
        return [Location.from_api(one) for one in result]

    def workspace(self, workspace_id: str) -> WorkspaceClient:
        """Resources and Incidents of one Workspace."""
        return WorkspaceClient(self._http, workspace_id)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> UptimerClient:  # noqa: PYI034
        """Use the client as a context manager; it closes its connections on exit."""
        return self

    def __exit__(self, *_: object) -> None:
        """Close the client's connections."""
        self.close()


class WorkspaceClient:
    def __init__(self, http: UptimerHttpLib, workspace_id: str):
        self.id = workspace_id
        base = f"v3/workspaces/{workspace_id}"
        self.resources = ResourcesClient(http, base)
        self.incidents = IncidentsClient(http, base)


class ResourcesClient:
    """A Workspace's Resources. `resource` arguments take a Resource's id or key."""

    def __init__(self, http: UptimerHttpLib, base: str):
        self._http = http
        self._base = base

    def list(self) -> list[Resource]:
        result, _ = self._http.request("GET", f"{self._base}/resources")
        return [Resource.from_api(one) for one in result]

    def get(self, resource: str) -> Resource:
        """One Resource with its Signals, its Rules and each Rule's latest result."""
        result, _ = self._http.request("GET", f"{self._base}/resources/{resource}")
        return Resource.from_api(result)

    def create(
        self,
        *,
        template: str,
        name: str,
        meta: dict[str, Any],
        key: str | None = None,
    ) -> Resource:
        """Create a Resource from a published Template; `meta` answers its fields."""
        body: dict[str, Any] = {"template": template, "name": name, "meta": meta}
        if key is not None:
            body["key"] = key
        result, _ = self._http.request("POST", f"{self._base}/resources", json=body)
        return Resource.from_api(result)

    def update(
        self,
        resource: str,
        *,
        name: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Resource:
        """Change a Resource's name or answers; what is not given stays."""
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if meta is not None:
            body["meta"] = meta
        result, _ = self._http.request("PATCH", f"{self._base}/resources/{resource}", json=body)
        return Resource.from_api(result)

    def observe(  # noqa: PLR0913
        self,
        resource: str,
        *,
        signal: str,
        state: str,
        kind: str | None = None,
        value: float | None = None,
        labels: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        at: datetime | None = None,
        observation_id: str | None = None,
    ) -> Observed:
        """
        Send one Observation (state `ok` or `problem`) on one of the Resource's Signals.

        `kind` (heartbeat, event or periodic) is needed only to declare a new
        Signal. The same `observation_id` sent twice is stored once.
        """
        optional = {"kind": kind, "value": value, "labels": labels, "body": body, "id": observation_id}
        payload: dict[str, Any] = {
            "signal": signal, "state": state,
            **{name: item for name, item in optional.items() if item is not None},
        }
        if at is not None:
            payload["at"] = at.isoformat()
        result, _ = self._http.request("POST", f"{self._base}/resources/{resource}/observations", json=payload)
        return Observed.from_api(result)

    def observations(
        self, resource: str, *, signal: str | None = None, limit: int = 50,
    ) -> builtins.list[Observation]:
        """Return the newest logged Observations, newest first."""
        result, _ = self._http.request(
            "GET", f"{self._base}/resources/{resource}/observations",
            params={"signal": signal, "limit": limit},
        )
        return [Observation.from_api(one) for one in result]

    def set_maintenance(self, resource: str, *, minutes: int) -> Resource:
        """Hold this Resource's notifications for `minutes`; judging and history go on."""
        result, _ = self._http.request(
            "PUT", f"{self._base}/resources/{resource}/maintenance", json={"minutes": minutes},
        )
        return Resource.from_api(result)

    def end_maintenance(self, resource: str) -> Resource:
        result, _ = self._http.request("DELETE", f"{self._base}/resources/{resource}/maintenance")
        return Resource.from_api(result)

    def incidents(self, resource: str, **filters: Any) -> Page[Incident]:  # noqa: ANN401
        """One Resource's Incidents; takes the filters of `IncidentsClient.list`."""
        return _incident_page(self._http, f"{self._base}/resources/{resource}/incidents", filters)


class IncidentsClient:
    """A Workspace's Incidents, newest first."""

    def __init__(self, http: UptimerHttpLib, base: str):
        self._http = http
        self._base = base

    def list(  # noqa: PLR0913
        self,
        *,
        resource: str | None = None,
        rule: str | None = None,
        lifecycle: str | None = None,
        confirmation: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> Page[Incident]:
        """
        One page of Incidents.

        `lifecycle` is "open" or "closed", `confirmation` "confirmed" or
        "unconfirmed". Pass the page's `next_cursor` as `cursor` for the next.
        """
        return _incident_page(self._http, f"{self._base}/incidents", {
            "resource": resource, "rule": rule, "lifecycle": lifecycle,
            "confirmation": confirmation, "limit": limit, "cursor": cursor,
        })

    def iterate(self, **filters: Any) -> Iterator[Incident]:  # noqa: ANN401
        """Every Incident the filters match, page after page."""
        cursor = None
        while True:
            page = self.list(**filters, cursor=cursor)
            yield from page.items
            if page.next_cursor is None:
                return
            cursor = page.next_cursor

    def get(self, incident: str) -> Incident:
        """One Incident with its ordered history."""
        result, _ = self._http.request("GET", f"{self._base}/incidents/{incident}")
        return Incident.from_api(result)

    def acknowledge(self, incident: str) -> Incident:
        """Take an open Incident on. A closed or already acknowledged one raises ConflictError."""
        result, _ = self._http.request("POST", f"{self._base}/incidents/{incident}/acknowledge")
        return Incident.from_api(result)


def _incident_page(http: UptimerHttpLib, path: str, params: dict[str, Any]) -> Page[Incident]:
    result, meta = http.request("GET", path, params=params)
    return Page(
        items=[Incident.from_api(one) for one in result],
        next_cursor=(meta or {}).get("next_cursor"),
    )
