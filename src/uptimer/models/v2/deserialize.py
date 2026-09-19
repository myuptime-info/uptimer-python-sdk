from __future__ import annotations

from typing import Any, TypeVar, Union

from uptimer.models.errors import (
    InvalidDataTypeError,
    MissingKindError,
    TypeMismatchError,
    UnknownKindError,
)

from .acknowledgement import IncidentAcknowledgement, SubjectIncident
from .incident import Incident, IncidentLocations
from .location import Location
from .maintenance import MaintenanceWindow
from .monitor import (
    WebsiteMonitor,
    WebsiteMonitorRequest,
    WebsiteMonitorResponse,
    WebsiteMonitorResponseBody,
)
from .notifications import (
    DeliveryRecord,
    DeliverySelection,
    Destination,
    PreviewResult,
    SubjectAlertDelivery,
    Transformation,
    TransformationPreview,
)
from .observation import Observation
from .rule import SubjectRule, rule_document_from_api
from .signal import Signal
from .subject import Subject
from .workspace import Workspace

T = TypeVar("T")

DeserializableType = Union[
    WebsiteMonitor,
    WebsiteMonitorRequest,
    WebsiteMonitorResponse,
    WebsiteMonitorResponseBody,
    Incident,
    IncidentAcknowledgement,
    Location,
    MaintenanceWindow,
    Observation,
    Subject,
    SubjectIncident,
    Workspace,
    Signal,
    SubjectRule,
    Destination,
    Transformation,
    TransformationPreview,
    SubjectAlertDelivery,
    DeliveryRecord,
]

DeserializableItem = Union[dict[str, Any], list[Any], Any]

# The v2 kinds. v1's kinds (rule, region, ...) are deliberately absent: 1.5.x
# targets API v2 only, and a v1 client stays on the released 0.4.x package.
_KIND_REGISTRY = {
    "website_monitor": WebsiteMonitor,
    "website_monitor_request": WebsiteMonitorRequest,
    "website_monitor_response": WebsiteMonitorResponse,
    "website_monitor_response_body": WebsiteMonitorResponseBody,
    "incident": Incident,
    "incident_acknowledgement": IncidentAcknowledgement,
    "subject_incident": SubjectIncident,
    "maintenance_window": MaintenanceWindow,
    "location": Location,
    "observation": Observation,
    "subject": Subject,
    "workspace": Workspace,
    "signal": Signal,
    "subject_rule": SubjectRule,
    # 1.8.0 notifications.
    "notification_destination": Destination,
    "notification_transformation": Transformation,
    "notification_transformation_preview": TransformationPreview,
    "subject_alert_delivery": SubjectAlertDelivery,
    "notification_delivery": DeliveryRecord,
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
        elif key == "document" and cls is SubjectRule:
            # A rule's policy: structure, but no kind — and `from` has to become
            # `from_rule` on the way in, because `from` is a Python keyword.
            kwargs[key] = rule_document_from_api(value)
        elif key == "selections" and cls is SubjectAlertDelivery:
            kwargs[key] = [
                DeliverySelection(
                    destination_id=row.get("destination_id", 0),
                    alert_kinds=row.get("alert_kinds") or [],
                    destination_name=row.get("destination_name", ""),
                )
                for row in value or []
            ]
        elif key == "results" and cls is TransformationPreview:
            kwargs[key] = [
                PreviewResult(
                    alert_kind=row.get("alert_kind", ""),
                    label=row.get("label", ""),
                    ok=row.get("ok", False),
                    output=row.get("output", ""),
                    error=row.get("error", ""),
                )
                for row in value or []
            ]
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


def from_api_observation(data: dict[str, Any]) -> Observation:
    """Deserialize a stored observation."""
    obj = from_api(data)
    if not isinstance(obj, Observation):
        expected = "Observation"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj


def from_api_subject_incident(data: dict[str, Any]) -> SubjectIncident:
    """Deserialize one open incident of a custom subject."""
    obj = from_api(data)
    if not isinstance(obj, SubjectIncident):
        expected = "SubjectIncident"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj


def from_api_acknowledgement(data: dict[str, Any]) -> IncidentAcknowledgement:
    """Deserialize the record an acknowledgement left behind."""
    obj = from_api(data)
    if not isinstance(obj, IncidentAcknowledgement):
        expected = "IncidentAcknowledgement"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj


def from_api_maintenance(data: dict[str, Any]) -> MaintenanceWindow:
    """Deserialize one maintenance window."""
    obj = from_api(data)
    if not isinstance(obj, MaintenanceWindow):
        expected = "MaintenanceWindow"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj


def from_api_subject(data: dict[str, Any]) -> Subject:
    """Deserialize one monitored subject."""
    obj = from_api(data)
    if not isinstance(obj, Subject):
        expected = "Subject"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj


def from_api_signal(data: dict[str, Any]) -> Signal:
    """Deserialize one signal of a custom subject."""
    obj = from_api(data)
    if not isinstance(obj, Signal):
        expected = "Signal"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj


def from_api_subject_rule(data: dict[str, Any]) -> SubjectRule:
    """Deserialize one operator-authored rule, with its policy."""
    obj = from_api(data)
    if not isinstance(obj, SubjectRule):
        expected = "SubjectRule"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj


def from_api_destination(data: dict[str, Any]) -> Destination:
    """Deserialize one alert destination."""
    obj = from_api(data)
    if not isinstance(obj, Destination):
        expected = "Destination"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj


def from_api_transformation(data: dict[str, Any]) -> Transformation:
    """Deserialize one outbound payload template."""
    obj = from_api(data)
    if not isinstance(obj, Transformation):
        expected = "Transformation"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj


def from_api_transformation_preview(data: dict[str, Any]) -> TransformationPreview:
    """Deserialize a template rendered against every sample."""
    obj = from_api(data)
    if not isinstance(obj, TransformationPreview):
        expected = "TransformationPreview"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj


def from_api_subject_delivery(data: dict[str, Any]) -> SubjectAlertDelivery:
    """Deserialize one subject's alert delivery table."""
    obj = from_api(data)
    if not isinstance(obj, SubjectAlertDelivery):
        expected = "SubjectAlertDelivery"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj


def from_api_delivery_record(data: dict[str, Any]) -> DeliveryRecord:
    """Deserialize one recorded delivery attempt."""
    obj = from_api(data)
    if not isinstance(obj, DeliveryRecord):
        expected = "DeliveryRecord"
        raise TypeMismatchError(expected, type(obj).__name__)
    return obj
