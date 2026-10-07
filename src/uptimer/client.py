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

    def create_workspace(self, name: str) -> Workspace:
        """
        Create a Workspace the key's owner owns, and return it.

        Only a full API key may: a scoped key raises ForbiddenError. A name
        that is blank or longer than 60 characters raises ValidationError.
        """
        result, _ = self._http.request("POST", "v3/workspaces", json={"name": name})
        return Workspace.from_api(result)

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
        self.templates = TemplatesClient(http, base)
        self.resources = ResourcesClient(http, base)
        self.incidents = IncidentsClient(http, base)


class TemplatesClient:
    """The Templates a Workspace can create Resources from, and publishing its own."""

    def __init__(self, http: UptimerHttpLib, base: str):
        self._http = http
        self._base = base

    def list(self) -> list[Template]:
        """System Templates, then this Workspace's own (id `key@version`), every revision."""
        result, _ = self._http.request("GET", f"{self._base}/templates")
        return [Template.from_api(one) for one in result]

    def publish(self, manifest: dict[str, Any]) -> Template:
        """
        Publish a pushed-data Template revision (fields, signals, composite rules).

        A revision never changes: the same key and version again raises
        ConflictError; a definition Uptimer cannot judge raises ValidationError.
        """
        result, _ = self._http.request("POST", f"{self._base}/templates", json=manifest)
        return Template.from_api(result)


class ResourcesClient:
    """A Workspace's Resources. `resource` arguments take a Resource's id or key."""

    def __init__(self, http: UptimerHttpLib, base: str):
        self._http = http
        self._base = base

    def list(
        self,
        *,
        template: str | None = None,
        state: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> builtins.list[Resource]:
        """
        Every Resource the filters match, page after page; active ones by default.

        `state` is "active", "archived" or "all". `meta` filters by the named
        Template's single-valued fields (equality), and needs `template`.
        """
        return [*self.iterate(template=template, state=state, meta=meta)]

    def page(
        self,
        *,
        template: str | None = None,
        state: str | None = None,
        meta: dict[str, Any] | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> Page[Resource]:
        """One page of Resources; pass its `next_cursor` as `cursor` for the next."""
        params = _filters(template=template, state_name="state", state=state, meta=meta)
        params.update({"limit": limit, "cursor": cursor})
        result, info = self._http.request("GET", f"{self._base}/resources", params=params)
        return Page(items=[Resource.from_api(one) for one in result],
                    next_cursor=(info or {}).get("next_cursor"))

    def iterate(
        self,
        *,
        template: str | None = None,
        state: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Iterator[Resource]:
        """Every matching Resource, page after page."""
        cursor = None
        while True:
            page = self.page(template=template, state=state, meta=meta, limit=200, cursor=cursor)
            yield from page.items
            if page.next_cursor is None:
                return
            cursor = page.next_cursor

    def archive(self, resource: str) -> Resource:
        """
        Retire a Resource from the inventory.

        Its key stays reserved and its history readable; open Incidents close
        as `resource_archived`. There is no restore.
        """
        result, _ = self._http.request("POST", f"{self._base}/resources/{resource}/archive")
        return Resource.from_api(result)

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
        Send one Observation (state `ok`, `problem` or `no_data`) on one of the Resource's Signals.

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
        template: str | None = None,
        resource_state: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Page[Incident]:
        """
        One page of Incidents.

        `lifecycle` is "open" or "closed", `confirmation` "confirmed" or
        "unconfirmed". `template`, `resource_state` ("active", "archived" or
        "all", the default) and `meta` keep the Incidents of matching
        Resources. Pass the page's `next_cursor` as `cursor` for the next.
        """
        params = _filters(template=template, state_name="resource_state", state=resource_state, meta=meta)
        params.update({
            "resource": resource, "rule": rule, "lifecycle": lifecycle,
            "confirmation": confirmation, "limit": limit, "cursor": cursor,
        })
        return _incident_page(self._http, f"{self._base}/incidents", params)

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


def _filters(
    *, template: str | None, state_name: str, state: str | None, meta: dict[str, Any] | None,
) -> dict[str, Any]:
    """Turn the Resource filters into query parameters, `meta.<field>` for each field."""
    params: dict[str, Any] = {"template": template, state_name: state}
    for key, value in (meta or {}).items():
        params[f"meta.{key}"] = str(value).lower() if isinstance(value, bool) else value
    return params


def _incident_page(http: UptimerHttpLib, path: str, params: dict[str, Any]) -> Page[Incident]:
    result, meta = http.request("GET", path, params=params)
    return Page(
        items=[Incident.from_api(one) for one in result],
        next_cursor=(meta or {}).get("next_cursor"),
    )
