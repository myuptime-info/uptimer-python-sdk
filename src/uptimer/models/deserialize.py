from __future__ import annotations

from typing import Any, TypeVar, Union

from .errors import (
    InvalidDataTypeError,
    MissingKindError,
    TypeMismatchError,
    UnknownKindError,
)
from .incident import Incident, IncidentLocations
from .location import Location
from .monitor import (
    WebsiteMonitor,
    WebsiteMonitorRequest,
    WebsiteMonitorResponse,
    WebsiteMonitorResponseBody,
)
from .workspace import Workspace

T = TypeVar("T")

DeserializableType = Union[
    WebsiteMonitor,
    WebsiteMonitorRequest,
    WebsiteMonitorResponse,
    WebsiteMonitorResponseBody,
    Incident,
    Location,
    Workspace,
]

DeserializableItem = Union[dict[str, Any], list[Any], Any]

# Kinds this SDK understands. v1's kinds (rule, region, ...) are deliberately
# absent: 1.0.0 targets API v2 only.
_KIND_REGISTRY = {
    "website_monitor": WebsiteMonitor,
    "website_monitor_request": WebsiteMonitorRequest,
    "website_monitor_response": WebsiteMonitorResponse,
    "website_monitor_response_body": WebsiteMonitorResponseBody,
    "incident": Incident,
    "location": Location,
    "workspace": Workspace,
}


def from_api(data: dict[str, Any]) -> DeserializableType:
    """Build an object from an API payload, chosen by its 'kind'."""
    if not isinstance(data, dict):
        raise InvalidDataTypeError(type(data).__name__)

    kind = data.get("kind")
    if not kind:
        raise MissingKindError(data)

    if kind not in _KIND_REGISTRY:
        raise UnknownKindError(kind)

    cls = _KIND_REGISTRY[kind]
    return _build(cls, data)


def _build(cls: type, data: dict[str, Any]) -> Any:  # noqa: ANN401
    """Construct one object, recursing into nested payloads that carry a kind."""
    kwargs: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict) and "kind" in value:
            kwargs[key] = from_api(value)
        elif key == "locations" and isinstance(value, dict):
            # Incident evidence: a plain object, no kind of its own.
            kwargs[key] = IncidentLocations(
                failing=value.get("failing", []),
                unknown=value.get("unknown", []),
                ok=value.get("ok", []),
            )
        else:
            kwargs[key] = value
    try:
        return cls(**kwargs)
    except TypeError as exc:
        raise TypeMismatchError(cls.__name__, str(exc)) from exc


def from_api_website_monitor(data: dict[str, Any]) -> WebsiteMonitor:
    """Deserialize a website monitor, checking the kind is the expected one."""
    obj = from_api(data)
    if not isinstance(obj, WebsiteMonitor):
        expected = "WebsiteMonitor"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj


def from_api_location(data: dict[str, Any]) -> Location:
    """Deserialize a location."""
    obj = from_api(data)
    if not isinstance(obj, Location):
        expected = "Location"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj


def from_api_workspace(data: dict[str, Any]) -> Workspace:
    """Deserialize a workspace."""
    obj = from_api(data)
    if not isinstance(obj, Workspace):
        expected = "Workspace"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj


def from_api_incident(data: dict[str, Any]) -> Incident:
    """Deserialize an incident."""
    obj = from_api(data)
    if not isinstance(obj, Incident):
        expected = "Incident"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj
